__FILENAME__ = admin
# -*- coding: utf-8 -*-
from django import forms
from django.core.urlresolvers import reverse
from crm.models import *
from accounting.models import *
from accounting.views import *
from django.utils.translation import ugettext as _
from django.contrib import admin
from django.http import HttpResponse
from django.http import HttpResponseRedirect

class AccountingPeriodBooking(admin.TabularInline):
   model = Booking
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('fromAccount', 'toAccount', 'description', 'amount', 'bookingDate', 'staff', 'bookingReference',)
      }),
   )
   allow_add = True

class OptionBooking(admin.ModelAdmin):
   list_display = ('fromAccount', 'toAccount', 'amount', 'bookingDate', 'staff')
   fieldsets = ((_('Basic'), {'fields' : ('fromAccount', 'toAccount', 'amount', 'bookingDate', 'staff', 'description', 'bookingReference', 'accountingPeriod')}),)
   save_as = True

   def save_model(self, request, obj, form, change):
      if (change == True):
        obj.lastmodifiedby = request.user
      else:
        obj.lastmodifiedby = request.user
        obj.staff = request.user
      obj.save()
      
class AccountForm(forms.ModelForm):
    """ AccountForm is used to overwrite the clean method of the 
    original form and to add an additional checks to the model"""
    class Meta:
        model = Account
        
    def clean(self):
        super(AccountForm, self).clean()
        errors = []
        if (self.cleaned_data['isopenreliabilitiesaccount']):
          openliabilitiesaccount = Account.objects.filter(isopenreliabilitiesaccount=True)
          if (self.cleaned_data['accountType'] != "L" ):
            errors.append(_('The open liabilites account must be a liabities account'))
          elif openliabilitiesaccount:
            errors.append(_('There may only be one open liablities account in the system'))
	if (self.cleaned_data['isopeninterestaccount']):
	  openinterestaccounts = Account.objects.filter(isopeninterestaccount=True)
	  if (self.cleaned_data['accountType']  != "A" ):
            errors.append(_('The open intrests account must be an asset account'))
	  elif openinterestaccounts:
            errors.append(_('There may only be one open intrests account in the system'))
	if (self.cleaned_data['isACustomerPaymentAccount']):
	  if (self.cleaned_data['accountType']  != "A" ):
            errors.append(_('A customer payment account must be an asset account'))
	if (self.cleaned_data['isProductInventoryActiva']):
	  if (self.cleaned_data['accountType']  != "A" ):
            errors.append(_('A product inventory account must be an asset account'))
        if len(errors) > 0:
	   raise forms.ValidationError(errors)   
	return self.cleaned_data
   
class OptionAccount(admin.ModelAdmin):
   list_display = ('accountNumber', 'accountType', 'title', 'isopenreliabilitiesaccount', 'isopeninterestaccount', 'isProductInventoryActiva', 'isACustomerPaymentAccount', 'value')
   list_display_links = ('accountNumber', 'accountType', 'title', 'value')
   fieldsets = ((_('Basic'), {'fields': ('accountNumber', 'accountType', 'title', 'description', 'originalAmount', 'isopenreliabilitiesaccount', 'isopeninterestaccount', 'isProductInventoryActiva', 'isACustomerPaymentAccount')}),)
   save_as = True
   
   form = AccountForm

class AccountingPeriodForm(forms.ModelForm):
    """ AccountingPeriodForm is used to overwrite the clean method of the 
    original form and to add an additional check to the model"""
    class Meta:
        model = AccountingPeriod
        
    def clean(self):
        super(AccountingPeriodForm, self).clean()
        errors = []
        try: 
           if self.cleaned_data['begin'] > self.cleaned_data['end']:
              errors.append(_('The begin date cannot be later than the end date.'))
        except KeyError:
           errors.append(_('The begin and the end date may not be empty'))
        if errors:
	   raise forms.ValidationError(errors)
	return self.cleaned_data

class OptionAccountingPeriod(admin.ModelAdmin):
   list_display = ('title', 'begin', 'end')
   list_display_links = ('title', 'begin', 'end')
   fieldsets = (
      (_('Basics'), {
         'fields': ('title', 'begin', 'end')
      }),
   )
   inlines = [AccountingPeriodBooking, ]
   save_as = True
   
   form = AccountingPeriodForm
   
   def save_formset(self, request, form, formset, change):
    instances = formset.save(commit=False)
    for instance in instances :
      if (change == True):
        instance.lastmodifiedby = request.user
      else:
        instance.lastmodifiedby = request.user
        instance.staff = request.user
      instance.save()
   
   def createBalanceSheet(self, request, queryset):
      for obj in queryset:
	 response = exportPDF(self, request, obj, "balanceSheet", "/admin/accounting/accountingperiod/")
         return response
   createBalanceSheet.short_description = _("Create PDF of Balance Sheet")
   
   def createProfitLossStatement(self, request, queryset):
      for obj in queryset:
	 response = exportPDF(self, request, obj, "profitLossStatement", "/admin/accounting/accountingperiod/")
         return response
   createProfitLossStatement.short_description = _("Create PDF of Profit Loss Statement Sheet")
   
   actions = ['createBalanceSheet', 'createProfitLossStatement']
            
class OptionProductCategorie(admin.ModelAdmin):
   list_display = ('title', 'profitAccount', 'lossAccount')
   list_display_links = ('title', 'profitAccount', 'lossAccount')
   fieldsets = (
      (_('Basics'), {
         'fields': ('title', 'profitAccount', 'lossAccount')
      }),
   )
   save_as = True
   
admin.site.register(Account, OptionAccount)
admin.site.register(Booking, OptionBooking)
admin.site.register(ProductCategorie, OptionProductCategorie)
admin.site.register(AccountingPeriod, OptionAccountingPeriod)

########NEW FILE########
__FILENAME__ = accountTypeChoices
# -*- coding: utf-8 -*

from django.utils.translation import ugettext as _

ACCOUNTTYPECHOICES = (
    ('E', _('Earnings')),
    ('S', _('Spendings')),
    ('L', _('Liabilities')),
    ('A', _('Assets')),
)
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'AccountingPeriod'
        db.create_table('accounting_accountingperiod', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('begin', self.gf('django.db.models.fields.DateField')()),
            ('end', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('accounting', ['AccountingPeriod'])

        # Adding model 'Account'
        db.create_table('accounting_account', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('accountNumber', self.gf('django.db.models.fields.IntegerField')()),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('accountType', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('isopenreliabilitiesaccount', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('isopeninterestaccount', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('isProductInventoryActiva', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('isACustomerPaymentAccount', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('accounting', ['Account'])

        # Adding model 'ProductCategorie'
        db.create_table('accounting_productcategorie', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('profitAccount', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_profit_account', to=orm['accounting.Account'])),
            ('lossAccount', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_loss_account', to=orm['accounting.Account'])),
        ))
        db.send_create_signal('accounting', ['ProductCategorie'])

        # Adding model 'Booking'
        db.create_table('accounting_booking', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('fromAccount', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_booking_fromaccount', to=orm['accounting.Account'])),
            ('toAccount', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_booking_toaccount', to=orm['accounting.Account'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=2)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=120, null=True, blank=True)),
            ('bookingReference', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Invoice'], null=True, blank=True)),
            ('bookingDate', self.gf('django.db.models.fields.DateTimeField')()),
            ('accountingPeriod', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounting.AccountingPeriod'])),
            ('staff', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_booking_refstaff', blank=True, to=orm['auth.User'])),
            ('dateofcreation', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('lastmodification', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('lastmodifiedby', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_booking_lstmodified', blank=True, to=orm['auth.User'])),
        ))
        db.send_create_signal('accounting', ['Booking'])


    def backwards(self, orm):
        # Deleting model 'AccountingPeriod'
        db.delete_table('accounting_accountingperiod')

        # Deleting model 'Account'
        db.delete_table('accounting_account')

        # Deleting model 'ProductCategorie'
        db.delete_table('accounting_productcategorie')

        # Deleting model 'Booking'
        db.delete_table('accounting_booking')


    models = {
        'accounting.account': {
            'Meta': {'ordering': "['accountNumber']", 'object_name': 'Account'},
            'accountNumber': ('django.db.models.fields.IntegerField', [], {}),
            'accountType': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isACustomerPaymentAccount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'isProductInventoryActiva': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'isopeninterestaccount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'isopenreliabilitiesaccount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'accounting.accountingperiod': {
            'Meta': {'object_name': 'AccountingPeriod'},
            'begin': ('django.db.models.fields.DateField', [], {}),
            'end': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'accounting.booking': {
            'Meta': {'object_name': 'Booking'},
            'accountingPeriod': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['accounting.AccountingPeriod']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
            'bookingDate': ('django.db.models.fields.DateTimeField', [], {}),
            'bookingReference': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Invoice']", 'null': 'True', 'blank': 'True'}),
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '120', 'null': 'True', 'blank': 'True'}),
            'fromAccount': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_booking_fromaccount'", 'to': "orm['accounting.Account']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_booking_lstmodified'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'staff': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_booking_refstaff'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'toAccount': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_booking_toaccount'", 'to': "orm['accounting.Account']"})
        },
        'accounting.productcategorie': {
            'Meta': {'object_name': 'ProductCategorie'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lossAccount': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_loss_account'", 'to': "orm['accounting.Account']"}),
            'profitAccount': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_profit_account'", 'to': "orm['accounting.Account']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'crm.contact': {
            'Meta': {'object_name': 'Contact'},
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        },
        'crm.contract': {
            'Meta': {'object_name': 'Contract'},
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'defaultSupplier': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Supplier']", 'null': 'True', 'blank': 'True'}),
            'defaultcurrency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Currency']"}),
            'defaultcustomer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Customer']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_contractlstmodified'", 'to': "orm['auth.User']"}),
            'staff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'db_relcontractstaff'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'crm.currency': {
            'Meta': {'object_name': 'Currency'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rounding': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'shortName': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        'crm.customer': {
            'Meta': {'object_name': 'Customer', '_ormbases': ['crm.Contact']},
            'contact_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.Contact']", 'unique': 'True', 'primary_key': 'True'}),
            'defaultCustomerBillingCycle': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.CustomerBillingCycle']"}),
            'ismemberof': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['crm.CustomerGroup']", 'null': 'True', 'blank': 'True'})
        },
        'crm.customerbillingcycle': {
            'Meta': {'object_name': 'CustomerBillingCycle'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'timeToPaymentDate': ('django.db.models.fields.IntegerField', [], {})
        },
        'crm.customergroup': {
            'Meta': {'object_name': 'CustomerGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        },
        'crm.invoice': {
            'Meta': {'object_name': 'Invoice', '_ormbases': ['crm.SalesContract']},
            'derivatedFromQuote': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Quote']", 'null': 'True', 'blank': 'True'}),
            'payableuntil': ('django.db.models.fields.DateField', [], {}),
            'paymentBankReference': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'salescontract_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.SalesContract']", 'unique': 'True', 'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.quote': {
            'Meta': {'object_name': 'Quote', '_ormbases': ['crm.SalesContract']},
            'salescontract_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.SalesContract']", 'unique': 'True', 'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'validuntil': ('django.db.models.fields.DateField', [], {})
        },
        'crm.salescontract': {
            'Meta': {'object_name': 'SalesContract'},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contract']"}),
            'currency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Currency']"}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Customer']"}),
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'discount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'externalReference': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastCalculatedPrice': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '17', 'decimal_places': '2', 'blank': 'True'}),
            'lastCalculatedTax': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '17', 'decimal_places': '2', 'blank': 'True'}),
            'lastPricingDate': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'blank': "'True'", 'related_name': "'db_lstscmodified'", 'null': 'True', 'to': "orm['auth.User']"}),
            'staff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'db_relscstaff'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'crm.supplier': {
            'Meta': {'object_name': 'Supplier', '_ormbases': ['crm.Contact']},
            'contact_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.Contact']", 'unique': 'True', 'primary_key': 'True'}),
            'offersShipmentToCustomers': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['accounting']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_account_description__add_field_account_originalAmount
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Account.description'
        db.add_column('accounting_account', 'description',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Account.originalAmount'
        db.add_column('accounting_account', 'originalAmount',
                      self.gf('django.db.models.fields.DecimalField')(default=0.0, max_digits=20, decimal_places=2),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Account.description'
        db.delete_column('accounting_account', 'description')

        # Deleting field 'Account.originalAmount'
        db.delete_column('accounting_account', 'originalAmount')


    models = {
        'accounting.account': {
            'Meta': {'ordering': "['accountNumber']", 'object_name': 'Account'},
            'accountNumber': ('django.db.models.fields.IntegerField', [], {}),
            'accountType': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isACustomerPaymentAccount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'isProductInventoryActiva': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'isopeninterestaccount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'isopenreliabilitiesaccount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'originalAmount': ('django.db.models.fields.DecimalField', [], {'default': '0.0', 'max_digits': '20', 'decimal_places': '2'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'accounting.accountingperiod': {
            'Meta': {'object_name': 'AccountingPeriod'},
            'begin': ('django.db.models.fields.DateField', [], {}),
            'end': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'accounting.booking': {
            'Meta': {'object_name': 'Booking'},
            'accountingPeriod': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['accounting.AccountingPeriod']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
            'bookingDate': ('django.db.models.fields.DateTimeField', [], {}),
            'bookingReference': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Invoice']", 'null': 'True', 'blank': 'True'}),
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '120', 'null': 'True', 'blank': 'True'}),
            'fromAccount': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_booking_fromaccount'", 'to': "orm['accounting.Account']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_booking_lstmodified'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'staff': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_booking_refstaff'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'toAccount': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_booking_toaccount'", 'to': "orm['accounting.Account']"})
        },
        'accounting.productcategorie': {
            'Meta': {'object_name': 'ProductCategorie'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lossAccount': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_loss_account'", 'to': "orm['accounting.Account']"}),
            'profitAccount': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_profit_account'", 'to': "orm['accounting.Account']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'crm.contact': {
            'Meta': {'object_name': 'Contact'},
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        },
        'crm.contract': {
            'Meta': {'object_name': 'Contract'},
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'defaultSupplier': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Supplier']", 'null': 'True', 'blank': 'True'}),
            'defaultcurrency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Currency']"}),
            'defaultcustomer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Customer']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_contractlstmodified'", 'to': "orm['auth.User']"}),
            'staff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'db_relcontractstaff'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'crm.currency': {
            'Meta': {'object_name': 'Currency'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rounding': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'shortName': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        'crm.customer': {
            'Meta': {'object_name': 'Customer', '_ormbases': ['crm.Contact']},
            'contact_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.Contact']", 'unique': 'True', 'primary_key': 'True'}),
            'defaultCustomerBillingCycle': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.CustomerBillingCycle']"}),
            'ismemberof': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['crm.CustomerGroup']", 'null': 'True', 'blank': 'True'})
        },
        'crm.customerbillingcycle': {
            'Meta': {'object_name': 'CustomerBillingCycle'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'timeToPaymentDate': ('django.db.models.fields.IntegerField', [], {})
        },
        'crm.customergroup': {
            'Meta': {'object_name': 'CustomerGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        },
        'crm.invoice': {
            'Meta': {'object_name': 'Invoice', '_ormbases': ['crm.SalesContract']},
            'derivatedFromQuote': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Quote']", 'null': 'True', 'blank': 'True'}),
            'payableuntil': ('django.db.models.fields.DateField', [], {}),
            'paymentBankReference': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'salescontract_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.SalesContract']", 'unique': 'True', 'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.quote': {
            'Meta': {'object_name': 'Quote', '_ormbases': ['crm.SalesContract']},
            'salescontract_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.SalesContract']", 'unique': 'True', 'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'validuntil': ('django.db.models.fields.DateField', [], {})
        },
        'crm.salescontract': {
            'Meta': {'object_name': 'SalesContract'},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contract']"}),
            'currency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Currency']"}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Customer']"}),
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'discount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'externalReference': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastCalculatedPrice': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '17', 'decimal_places': '2', 'blank': 'True'}),
            'lastCalculatedTax': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '17', 'decimal_places': '2', 'blank': 'True'}),
            'lastPricingDate': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'blank': "'True'", 'related_name': "'db_lstscmodified'", 'null': 'True', 'to': "orm['auth.User']"}),
            'staff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'db_relscstaff'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'crm.supplier': {
            'Meta': {'object_name': 'Supplier', '_ormbases': ['crm.Contact']},
            'contact_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.Contact']", 'unique': 'True', 'primary_key': 'True'}),
            'offersShipmentToCustomers': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['accounting']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

from subprocess import *
from const.accountTypeChoices import *
from crm.models import Contract
from crm.exceptions import TemplateSetMissing
from crm.exceptions import UserExtensionMissing
from django.db import models
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext as _
from django.db.models import signals
from xml.dom.minidom import Document
from datetime import *
import settings
import djangoUserExtension

   
class AccountingPeriod(models.Model):
  title =  models.CharField(max_length=200, verbose_name=_("Title")) # For example "Year 2009", "1st Quarter 2009"
  begin = models.DateField(verbose_name=_("Begin"))
  end = models.DateField(verbose_name=_("End"))
  
  @staticmethod
  def getCurrentValidAccountingPeriod():
    """Returns the accounting period that is currently valid. Valid is an accountingPeriod when the current date
       lies between begin and end of the accountingPeriod

    Args:
      no arguments

    Returns:
      accoutingPeriod (AccoutingPeriod)
          
    Raises:
      NoFeasableAccountingPeriodFound when there is no valid accounting Period"""
    currentValidAccountingPeriod = None
    for accountingPeriod in AccountingPeriod.objects.all():
      if accountingPeriod.begin < date.today() and accountingPeriod.end > date.today():
        return accountingPeriod
    if currentValidAccountingPeriod == None:
      raise NoFeasableAccountingPeriodFound()
  
  def createPDF(self, raisedbyuser, whatToCreate):
    userExtension = djangoUserExtension.models.UserExtension.objects.filter(user=raisedbyuser.id)
    if (len(userExtension) == 0):
      raise UserExtensionMissing(_("During BalanceSheet PDF Export"))
    doc = Document()
    if (whatToCreate == "balanceSheet"):
      main = doc.createElement("koalixaccountingbalacesheet")
      out = open(settings.PDF_OUTPUT_ROOT+"balancesheet_"+str(self.id)+".xml", "w")
    else:
      main = doc.createElement("koalixaccountingprofitlossstatement")
      out = open(settings.PDF_OUTPUT_ROOT+"profitlossstatement_"+str(self.id)+".xml", "w")
    accountingPeriodName = doc.createElement("accountingPeriodName")
    accountingPeriodName.appendChild(doc.createTextNode(self.__unicode__()))
    main.appendChild(accountingPeriodName)
    organisiationname = doc.createElement("organisiationname")
    organisiationname.appendChild(doc.createTextNode(settings.MEDIA_ROOT+userExtension[0].defaultTemplateSet.organisationname))
    main.appendChild(organisiationname)
    accountingPeriodTo = doc.createElement("accountingPeriodTo")
    accountingPeriodTo.appendChild(doc.createTextNode(self.end.year.__str__()))
    main.appendChild(accountingPeriodTo)
    accountingPeriodFrom = doc.createElement("accountingPeriodFrom")
    accountingPeriodFrom.appendChild(doc.createTextNode(self.begin.year.__str__()))
    main.appendChild(accountingPeriodFrom)
    headerPicture = doc.createElement("headerpicture")
    headerPicture.appendChild(doc.createTextNode(settings.MEDIA_ROOT+userExtension[0].defaultTemplateSet.logo.path))
    main.appendChild(headerPicture)
    accountNumber = doc.createElement("AccountNumber")
    accounts = Account.objects.all()
    overallValueBalance = 0
    overallValueProfitLoss = 0
    for account in list(accounts) :
        currentValue = account.valueNow(self)
        if (currentValue != 0):
          currentAccountElement = doc.createElement("Account")
          accountNumber = doc.createElement("AccountNumber")
          accountNumber.appendChild(doc.createTextNode(account.accountNumber.__str__()))
          currentValueElement = doc.createElement("currentValue")
          currentValueElement.appendChild(doc.createTextNode(currentValue.__str__()))
          accountNameElement = doc.createElement("accountName")
          accountNameElement.appendChild(doc.createTextNode(account.title))
          currentAccountElement.setAttribute("accountType", account.accountType.__str__())
          currentAccountElement.appendChild(accountNumber)
          currentAccountElement.appendChild(accountNameElement)
          currentAccountElement.appendChild(currentValueElement)
          main.appendChild(currentAccountElement)
          if account.accountType == "A":
            overallValueBalance = overallValueBalance + currentValue;
          if account.accountType == "L":
            overallValueBalance = overallValueBalance - currentValue;
          if account.accountType == "E":
            overallValueProfitLoss = overallValueProfitLoss + currentValue;
          if account.accountType == "S":
            overallValueProfitLoss = overallValueProfitLoss - currentValue;
    totalProfitLoss = doc.createElement("TotalProfitLoss")
    totalProfitLoss.appendChild(doc.createTextNode(overallValueProfitLoss.__str__()))
    main.appendChild(totalProfitLoss)
    totalBalance = doc.createElement("TotalBalance")
    totalBalance.appendChild(doc.createTextNode(overallValueBalance.__str__()))
    main.appendChild(totalBalance)
    doc.appendChild(main)
    out.write(doc.toxml("utf-8"))
    out.close()
    if (whatToCreate == "balanceSheet"):
      check_output(['/usr/bin/fop', '-c', userExtension[0].defaultTemplateSet.fopConfigurationFile.path, '-xml', settings.PDF_OUTPUT_ROOT+'balancesheet_'+str(self.id)+'.xml', '-xsl', userExtension[0].defaultTemplateSet.balancesheetXSLFile.xslfile.path, '-pdf', settings.PDF_OUTPUT_ROOT+'balancesheet_'+str(self.id)+'.pdf'], stderr=STDOUT)
      return settings.PDF_OUTPUT_ROOT+"balancesheet_"+str(self.id)+".pdf"  
    else:
       check_output(['/usr/bin/fop', '-c', userExtension[0].defaultTemplateSet.fopConfigurationFile.path, '-xml', settings.PDF_OUTPUT_ROOT+'profitlossstatement_'+str(self.id)+'.xml', '-xsl', userExtension[0].defaultTemplateSet.profitLossStatementXSLFile.xslfile.path, '-pdf', settings.PDF_OUTPUT_ROOT+'profitlossstatement_'+str(self.id)+'.pdf'], stderr=STDOUT)
       return settings.PDF_OUTPUT_ROOT+"profitlossstatement_"+str(self.id)+".pdf" 
    
  
  def __unicode__(self):
      return  self.title

# TODO: def createNewAccountingPeriod() Neues Geschäftsjahr erstellen
   
  class Meta:
     app_label = "accounting"
     verbose_name = _('Accounting Period')
     verbose_name_plural = _('Accounting Periods')
            
class Account(models.Model):
   accountNumber = models.IntegerField(verbose_name=_("Account Number"))
   title = models.CharField(verbose_name=_("Account Title"), max_length=50)
   accountType = models.CharField(verbose_name=_("Account Type"), max_length=1, choices=ACCOUNTTYPECHOICES)
   description = models.TextField(verbose_name = _("Description"),null=True, blank=True) 
   originalAmount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_("Original Amount"), default=0.00) 
   isopenreliabilitiesaccount = models.BooleanField(verbose_name=_("Is The Open Liabilities Account"))
   isopeninterestaccount = models.BooleanField(verbose_name=_("Is The Open Interests Account"))
   isProductInventoryActiva = models.BooleanField(verbose_name=_("Is a Product Inventory Account"))
   isACustomerPaymentAccount = models.BooleanField(verbose_name=_("Is a Customer Payment Account"))
   
   def value(self):
      sum = self.allBookings(fromAccount = False) - self.allBookings(fromAccount = True)
      if (self.accountType == 'P' or self.accountType == 'E'):
        sum = 0 - sum
      return sum
      
   def valueNow(self, accountingPeriod):
      sum = self.allBookingsInAccountingPeriod(fromAccount = False, accountingPeriod = accountingPeriod) - self.allBookingsInAccountingPeriod(fromAccount = True, accountingPeriod = accountingPeriod)
      return sum
      
   def allBookings(self, fromAccount):
      sum = 0
      if (fromAccount == True):
         bookings = Booking.objects.filter(fromAccount=self.id)
      else:
         bookings = Booking.objects.filter(toAccount=self.id)
      
      for booking in list(bookings):
         sum = sum + booking.amount
         
      return sum

   def allBookingsInAccountingPeriod(self, fromAccount, accountingPeriod):
      sum = 0
      if (fromAccount == True):
         bookings = Booking.objects.filter(fromAccount=self.id, accountingPeriod=accountingPeriod.id)
      else:
         bookings = Booking.objects.filter(toAccount=self.id, accountingPeriod=accountingPeriod.id)
      
      for booking in list(bookings):
         sum = sum + booking.amount
         
      return sum
      
   def __unicode__(self):
      return  self.accountNumber.__str__()  + " " + self.title
      
   class Meta:
      app_label = "accounting"
      verbose_name = _('Account')
      verbose_name_plural = _('Account')
      ordering = ['accountNumber']
      
class ProductCategorie(models.Model):
   title = models.CharField(verbose_name=_("Product Categorie Title"), max_length=50)
   profitAccount = models.ForeignKey(Account, verbose_name=_("Profit Account"), limit_choices_to={"accountType" : "E"}, related_name="db_profit_account")
   lossAccount = models.ForeignKey(Account, verbose_name=_("Loss Account"),  limit_choices_to={"accountType" : "S"}, related_name="db_loss_account")
   
   class Meta:
      app_label = "accounting"
      verbose_name = _('Product Categorie')
      verbose_name_plural = _('Product Categories')
   def __unicode__(self):
      return  self.title

class Booking(models.Model):
   fromAccount = models.ForeignKey(Account, verbose_name=_("From Account"), related_name="db_booking_fromaccount")
   toAccount = models.ForeignKey(Account, verbose_name=_("To Account"), related_name="db_booking_toaccount")
   amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_("Amount"))
   description = models.CharField(verbose_name=_("Description"), max_length=120, null=True, blank=True)
   bookingReference = models.ForeignKey('crm.Invoice', verbose_name=_("Booking Reference"), null=True, blank=True)
   bookingDate = models.DateTimeField(verbose_name = _("Booking at"))
   accountingPeriod = models.ForeignKey(AccountingPeriod, verbose_name=_("AccountingPeriod"))
   staff = models.ForeignKey('auth.User', limit_choices_to={'is_staff': True}, blank=True, verbose_name = _("Reference Staff"), related_name="db_booking_refstaff")
   dateofcreation = models.DateTimeField(verbose_name = _("Created at"), auto_now=True)
   lastmodification = models.DateTimeField(verbose_name = _("Last modified"), auto_now_add=True)
   lastmodifiedby = models.ForeignKey('auth.User', limit_choices_to={'is_staff': True}, blank=True, verbose_name = _("Last modified by"), related_name="db_booking_lstmodified")
   
   def __unicode__(self):
      return  self.fromAccount.__str__()  + " " + self.toAccount.__str__()  + " " + self.amount.__str__() 
      
   class Meta:
      app_label = "accounting"
      verbose_name = _('Booking')
      verbose_name_plural = _('Bookings')
      
      

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from os import path
from accounting.models import *
from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from subprocess import *

def exportPDF(callingModelAdmin, request, whereToCreateFrom, whatToCreate, redirectTo):
  """This method exports PDFs provided by different Models in the accounting application

      Args:
        callingModelAdmin (ModelAdmin):  The calling ModelAdmin must be provided for error message response.
        request: The request User is required to get the Calling User TemplateSets and to know where to save the error message
        whereToCreateFrom (Model):  The model from which a PDF should be exported
        whatToCreate (str): What document Type that has to be
        redirectTo (str): String that describes to where the method sould redirect in case of an error

      Returns:
            HTTpResponse with a PDF when successful
            HTTpResponseRedirect when not successful
            
      Raises:
        raises Http404 exception if anything goes wrong"""
  try:
    pdf = whereToCreateFrom.createPDF(request.user, whatToCreate)
    response = HttpResponse(FileWrapper(file(pdf)), mimetype='application/pdf')
    response['Content-Length'] = path.getsize(pdf) 
  except (TemplateSetMissing, UserExtensionMissing, CalledProcessError), e:
    if type(e) == UserExtensionMissing:
      response = HttpResponseRedirect(redirectTo)
      callingModelAdmin.message_user(request, _("User Extension Missing"))
    elif type(e) == TemplateSetMissing:
      response = HttpResponseRedirect(redirectTo)
      callingModelAdmin.message_user(request, _("Templateset Missing"))
    elif type(e) ==CalledProcessError:
      response = HttpResponseRedirect(redirectTo)
      callingModelAdmin.message_user(request, e.output)
    else:
      raise Http404
  return response 

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
import os
from django import forms
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.core.context_processors import csrf
from datetime import date
from crm.models import *
from crm.views import *
from accounting.models import Booking
from plugin import *
from django.utils.translation import ugettext as _
from django.contrib import admin
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.core.servers.basehttp import FileWrapper
from django.template import RequestContext
from django.contrib.admin import helpers

   
class ContractPostalAddress(admin.StackedInline):
   model = PostalAddressForContract
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('prefix', 'prename', 'name', 'addressline1', 'addressline2', 'addressline3', 'addressline4', 'zipcode', 'town', 'state', 'country', 'purpose')
      }),
   )
   allow_add = True
   
class ContractPhoneAddress(admin.TabularInline):
   model = PhoneAddressForContract
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('phone', 'purpose',)
      }),
   )
   allow_add = True
   
class ContractEmailAddress(admin.TabularInline):
   model = EmailAddressForContract
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('email', 'purpose',)
      }),
   )
   allow_add = True

class PurchaseOrderPostalAddress(admin.StackedInline):
   model = PostalAddressForPurchaseOrder
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('prefix', 'prename', 'name', 'addressline1', 'addressline2', 'addressline3', 'addressline4', 'zipcode', 'town', 'state', 'country', 'purpose')
      }),
   )
   allow_add = True
   
class PurchaseOrderPhoneAddress(admin.TabularInline):
   model = PhoneAddressForPurchaseOrder
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('phone', 'purpose',)
      }),
   )
   allow_add = True
   
class PurchaseOrderEmailAddress(admin.TabularInline):
   model = EmailAddressForPurchaseOrder
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('email', 'purpose',)
      }),
   )
   allow_add = True

class SalesContractPostalAddress(admin.StackedInline):
   model = PostalAddressForSalesContract
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('prefix', 'prename', 'name', 'addressline1', 'addressline2', 'addressline3', 'addressline4', 'zipcode', 'town', 'state', 'country', 'purpose')
      }),
   )
   allow_add = True
   
class SalesContractPhoneAddress(admin.TabularInline):
   model = PhoneAddressForSalesContract
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('phone', 'purpose',)
      }),
   )
   allow_add = True
   
class SalesContractEmailAddress(admin.TabularInline):
   model = EmailAddressForSalesContract
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('email', 'purpose',)
      }),
   )
   allow_add = True

class SalesContractInlinePosition(admin.TabularInline):
    model = SalesContractPosition
    extra = 1
    classes = ('collapse-open',)
    fieldsets = (
        ('', {
            'fields': ('positionNumber', 'quantity', 'unit', 'product', 'description', 'discount', 'overwriteProductPrice', 'positionPricePerUnit', 'sentOn', 'supplier')
        }),
    )
    allow_add = True


class InlineQuote(admin.TabularInline):
   model = Quote
   classes = ('collapse-open')
   extra = 1
   readonly_fields = ('description', 'contract', 'customer', 'validuntil', 'status', 'lastPricingDate', 'lastCalculatedPrice', 'lastCalculatedTax', )
   fieldsets = (
      (_('Basics'), {
         'fields': ('description', 'contract', 'customer', 'validuntil', 'status')
      }),
      (_('Advanced (not editable)'), {
         'classes': ('collapse',),
         'fields': ('lastPricingDate', 'lastCalculatedPrice', 'lastCalculatedTax',)
      }),
   )
   allow_add = False
   
class InlineInvoice(admin.TabularInline):
   model = Invoice
   classes = ('collapse-open')
   extra = 1
   readonly_fields = ('lastPricingDate', 'lastCalculatedPrice', 'lastCalculatedTax', 'description', 'contract', 'customer', 'payableuntil', 'status' )
   fieldsets = (
      (_('Basics'), {
         'fields': ('description', 'contract', 'customer', 'payableuntil', 'status'),
      }),
      (_('Advanced (not editable)'), {
         'classes': ('collapse',),
         'fields': ('lastPricingDate', 'lastCalculatedPrice', 'lastCalculatedTax',)
      }),
   )
   
   allow_add = False
   
class InlinePurchaseOrder(admin.TabularInline):
   model = PurchaseOrder
   classes = ('collapse-open')
   extra = 1
   readonly_fields = ('description', 'contract', 'supplier', 'externalReference', 'status', 'lastPricingDate', 'lastCalculatedPrice' )
   fieldsets = (
      (_('Basics'), {
         'fields': ('description', 'contract', 'supplier', 'externalReference', 'status')
      }),
      (_('Advanced (not editable)'), {
         'classes': ('collapse',),
         'fields': ('lastPricingDate', 'lastCalculatedPrice')
      }),
   )
   allow_add = False

class OptionContract(admin.ModelAdmin):
   list_display = ('id', 'description', 'defaultcustomer', 'defaultSupplier', 'staff', 'defaultcurrency')
   list_display_links = ('id','description', 'defaultcustomer', 'defaultSupplier', 'defaultcurrency')       
   list_filter    = ('defaultcustomer', 'defaultSupplier', 'staff', 'defaultcurrency')
   ordering       = ('id', 'defaultcustomer', 'defaultcurrency')
   search_fields  = ('id','contract', 'defaultcurrency__description')
   fieldsets = (
      (_('Basics'), {
         'fields': ('description', 'defaultcustomer', 'staff','defaultSupplier', 'defaultcurrency')
      }),
   )
   inlines = [ContractPostalAddress, ContractPhoneAddress, ContractEmailAddress, InlineQuote, InlineInvoice, InlinePurchaseOrder]
   pluginProcessor = PluginProcessor()
   inlines.extend(pluginProcessor.getPluginAdditions("contractInlines"))

   def createPurchaseOrder(self, request, queryset):
      for obj in queryset:
         purchaseorder = obj.createPurchaseOrder()
         self.message_user(request, _("PurchaseOrder created"))
         response = HttpResponseRedirect('/admin/crm/purchaseorder/'+str(purchaseorder.id))
      return response
   createPurchaseOrder.short_description = _("Create Purchaseorder")
   
   def createQuote(self, request, queryset):
      for obj in queryset:
         quote = obj.createQuote()
         self.message_user(request, _("Quote created"))
         response = HttpResponseRedirect('/admin/crm/quote/'+str(quote.id))
      return response
   createQuote.short_description = _("Create Quote")
   
   def createInvoice(self, request, queryset):
      for obj in queryset:
         invoice = obj.createInvoice()
         self.message_user(request, _("Invoice created"))
         response = HttpResponseRedirect('/admin/crm/invoice/'+str(invoice.id))
      return response
   createInvoice.short_description = _("Create Invoice")
    
   def save_model(self, request, obj, form, change):
     if (change == True):
       obj.lastmodifiedby = request.user
     else:
       obj.lastmodifiedby = request.user
       obj.staff = request.user
     obj.save()
      
   actions = ['createQuote', 'createInvoice', 'createPurchaseOrder']
   pluginProcessor = PluginProcessor()
   actions.extend(pluginProcessor.getPluginAdditions("contractActions"))


class PurchaseOrderInlinePosition(admin.TabularInline):
    model = PurchaseOrderPosition
    extra = 1
    classes = ('collapse-open',)
    fieldsets = (
        ('', {
            'fields': ('positionNumber', 'quantity', 'unit', 'product', 'description', 'discount', 'overwriteProductPrice', 'positionPricePerUnit', 'sentOn', 'supplier')
        }),
    )
    allow_add = True
    
class InlineBookings(admin.TabularInline):
   model = Booking
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('fromAccount', 'toAccount', 'description', 'amount', 'bookingDate', 'staff', 'bookingReference',)
      }),
   )
   allow_add = False

class OptionInvoice(admin.ModelAdmin):
   list_display = ('id', 'description', 'contract', 'customer', 'payableuntil', 'status', 'currency', 'staff',  'lastCalculatedPrice', 'lastPricingDate', 'lastmodification', 'lastmodifiedby')
   list_display_links = ('id','contract','customer')       
   list_filter    = ('customer', 'contract', 'staff', 'status', 'currency', 'lastmodification')
   ordering       = ('contract', 'customer', 'currency')
   search_fields  = ('contract__id', 'customer__name', 'currency__description')
   fieldsets = (
      (_('Basics'), {
         'fields': ('contract', 'description', 'customer', 'currency', 'payableuntil', 'status')
      }),
   )
   save_as = True
   inlines = [SalesContractInlinePosition, SalesContractPostalAddress, SalesContractPhoneAddress, SalesContractEmailAddress, InlineBookings]
   pluginProcessor = PluginProcessor()
   inlines.extend(pluginProcessor.getPluginAdditions("invoiceInlines"))
   
   def response_add(self, request, new_object):
        obj = self.after_saving_model_and_related_inlines(request, new_object)
        return super(OptionInvoice, self).response_add(request, obj)
   
   def response_change(self, request, new_object):
        obj = self.after_saving_model_and_related_inlines(request, new_object)
        return super(OptionInvoice, self).response_add(request, obj)
      
   def after_saving_model_and_related_inlines(self, request, obj):
     try:
       obj.recalculatePrices(date.today())
       self.message_user(request, "Successfully calculated Prices")
     except Product.NoPriceFound as e : 
       self.message_user(request, "Unsuccessfull in updating the Prices "+ e.__str__())
     return obj
      
   def save_model(self, request, obj, form, change):
     if (change == True):
       obj.lastmodifiedby = request.user
     else:
       obj.lastmodifiedby = request.user
       obj.staff = request.user
     obj.save()
      
   def recalculatePrices(self, request, queryset):
     try:
        for obj in queryset:
            obj.recalculatePrices(date.today())
        self.message_user(request, "Successfully recalculated Prices")
     except Product.NoPriceFound as e : 
        self.message_user(request, "Unsuccessfull in updating the Prices "+ e.__str__())
        return;
   recalculatePrices.short_description = _("Recalculate Prices")
         
   def createInvoicePDF(self, request, queryset):
     for obj in queryset:
       response = exportPDF(self, request, obj, "invoice", "/admin/crm/invoice/")
       return response
   createInvoicePDF.short_description = _("Create PDF of Invoice")
   
   def createDeliveryOrderPDF(self, request, queryset):
      for obj in queryset:
        response = exportPDF(self, request, obj, "deliveryorder", "/admin/crm/invoice/")
        return response
   createDeliveryOrderPDF.short_description = _("Create PDF of Delivery Order")
         
   def registerInvoiceInAccounting(self, request, queryset):
      for obj in queryset:
         obj.registerinvoiceinaccounting(request)
         self.message_user(request, _("Successfully registered Invoice in the Accounting"))
   registerInvoiceInAccounting.short_description = _("Register Invoice in Accounting")
   
   #def unregisterInvoiceInAccounting(self, request, queryset):
      #for obj in queryset:
         #obj.createPDF(deliveryorder=True)
         #self.message_user(request, _("Successfully unregistered Invoice in the Accounting"))
   #unregisterInvoiceInAccounting.short_description = _("Unregister Invoice in Accounting")
   
   def registerPaymentInAccounting(self, request, queryset):
     form = None
     if request.POST.get('post'):
        if 'cancel' in request.POST:
            self.message_user(request, _("Canceled registeration of payment in the accounting"))
            return 
        elif 'register' in request.POST:
            form = self.SeriesForm(request.POST)
            if form.is_valid():
                series = form.cleaned_data['series']
                for x in queryset:
                  y = Link(series = series, comic = x)
                  y.save()
                self.message_user(request, _("Successfully registered Payment in the Accounting"))
                return HttpResponseRedirect(request.get_full_path())
     else:
        c = {'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME, 'queryset': queryset, 'form': form, 'path':request.get_full_path()}
        c.update(csrf(request))
        return render_to_response('admin/crm/registerPayment.html', c, context_instance=RequestContext(request))

   registerPaymentInAccounting.short_description = _("Register Payment in Accounting")
   
   actions = ['recalculatePrices', 'createDeliveryOrderPDF', 'createInvoicePDF', 'registerInvoiceInAccounting', 'unregisterInvoiceInAccounting', 'registerPaymentInAccounting']
   pluginProcessor = PluginProcessor()
   actions.extend(pluginProcessor.getPluginAdditions("invoiceActions"))


class OptionQuote(admin.ModelAdmin):
   list_display = ('id', 'description', 'contract', 'customer', 'currency', 'validuntil', 'status', 'staff', 'lastmodifiedby', 'lastCalculatedPrice', 'lastPricingDate', 'lastmodification')
   list_display_links = ('id','contract','customer', 'currency')        
   list_filter    = ('customer', 'contract', 'currency', 'staff', 'status', 'lastmodification')
   ordering       = ('contract', 'customer', 'currency')
   search_fields  = ('contract__id', 'customer__name', 'currency__description')

   fieldsets = (
      (_('Basics'), {
         'fields': ('contract', 'description', 'customer', 'currency', 'validuntil', 'staff','status')
      }),
   )
   save_as = True
   inlines = [SalesContractInlinePosition, SalesContractPostalAddress, SalesContractPhoneAddress, SalesContractEmailAddress]
   pluginProcessor = PluginProcessor()
   inlines.extend(pluginProcessor.getPluginAdditions("quoteInlines"))
   
   def response_add(self, request, new_object):
        obj = self.after_saving_model_and_related_inlines(request, new_object)
        return super(OptionQuote, self).response_add(request, obj)
         
   def response_change(self, request, new_object):
        obj = self.after_saving_model_and_related_inlines(request, new_object)
        return super(OptionQuote, self).response_change(request, obj)

   def after_saving_model_and_related_inlines(self, request, obj):
     try:
       obj.recalculatePrices(date.today())
       self.message_user(request, "Successfully calculated Prices")
     except Product.NoPriceFound as e : 
       self.message_user(request, "Unsuccessfull in updating the Prices "+ e.__str__())
     return obj
   
   def save_model(self, request, obj, form, change):
     if (change == True):
       obj.lastmodifiedby = request.user
     else:
       obj.lastmodifiedby = request.user
       obj.staff = request.user
     obj.save()

   def recalculatePrices(self, request, queryset):
     try:
        for obj in queryset:
           obj.recalculatePrices(date.today())
           self.message_user(request, _("Successfully recalculated Prices"))
     except Product.NoPriceFound as e : 
        self.message_user(request, _("Unsuccessfull in updating the Prices ")+ e.__str__())
        return;
   recalculatePrices.short_description = _("Recalculate Prices")

   def createInvoice(self, request, queryset):
      for obj in queryset:
         invoice = obj.createInvoice()
         self.message_user(request, _("Invoice created"))
         response = HttpResponseRedirect('/admin/crm/invoice/'+str(invoice.id))
      return response
   createInvoice.short_description = _("Create Invoice")
         
   def createQuotePDF(self, request, queryset):
      for obj in queryset:
        response = exportPDF(self, request, obj, "quote", "/admin/crm/quote/")
        return response
   createQuotePDF.short_description = _("Create PDF of Quote")
         
   def createPurchaseConfirmationPDF(self, request, queryset):
      for obj in queryset:
       response = exportPDF(self, request, obj, "purchaseconfirmation", "/admin/crm/quote/")
       return response
   createPurchaseConfirmationPDF.short_description = _("Create PDF of Purchase Confirmation")

   actions = ['recalculatePrices', 'createInvoice', 'createQuotePDF', 'createPurchaseConfirmationPDF']
   pluginProcessor = PluginProcessor()
   inlines.extend(pluginProcessor.getPluginAdditions("quoteActions"))

class OptionPurchaseOrder(admin.ModelAdmin):
   list_display = ('id', 'description', 'contract', 'supplier', 'status', 'currency', 'staff', 'lastmodifiedby', 'lastCalculatedPrice', 'lastPricingDate', 'lastmodification')
   list_display_links = ('id','contract','supplier', )        
   list_filter    = ('supplier', 'contract', 'staff', 'status', 'currency', 'lastmodification')
   ordering       = ('contract', 'supplier', 'currency')
   search_fields  = ('contract__id', 'supplier__name', 'currency_description')

   fieldsets = (
      (_('Basics'), {
         'fields': ('contract', 'description', 'supplier', 'currency', 'status')
      }),
   )
   
   def save_model(self, request, obj, form, change):
     if (change == True):
       obj.lastmodifiedby = request.user
     else:
       obj.lastmodifiedby = request.user
       obj.staff = request.user
     obj.save()
         
   def createPurchseOrderPDF(self, request, queryset):
      for obj in queryset:
       response = exportPDF(self, request, obj, "purchaseorder", "/admin/crm/purchaseorder/")
       return response
   createPurchseOrderPDF.short_description = _("Create PDF of Purchase Order")
   
   actions = ['createPurchseOrderPDF']
   pluginProcessor = PluginProcessor()
   actions.extend(pluginProcessor.getPluginAdditions("purchaseOrderActions"))
   
   save_as = True
   inlines = [PurchaseOrderInlinePosition, PurchaseOrderPostalAddress, PurchaseOrderPhoneAddress, PurchaseOrderEmailAddress]
   pluginProcessor = PluginProcessor()
   inlines.extend(pluginProcessor.getPluginAdditions("purchaseOrderInlines"))

class ProductPrice(admin.TabularInline):
   model = Price
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('', {
         'fields': ('price', 'validfrom', 'validuntil', 'unit', 'customerGroup', 'currency')
      }),
   )
   allow_add = True
   
class ProductUnitTransform(admin.TabularInline):
   model = UnitTransform
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('', {
         'fields': ('fromUnit', 'toUnit', 'factor', )
      }),
   )
   allow_add = True

class OptionProduct(admin.ModelAdmin):
   list_display = ('productNumber', 'title','defaultunit', 'tax', 'accoutingProductCategorie')
   list_display_links = ('productNumber',)
   fieldsets = (
      (_('Basics'), {
         'fields': ('productNumber', 'title', 'description', 'defaultunit', 'tax', 'accoutingProductCategorie')
      }),)
   inlines = [ProductPrice, ProductUnitTransform]
   
class ContactPostalAddress(admin.StackedInline):
   model = PostalAddressForContact
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('prefix', 'prename', 'name', 'addressline1', 'addressline2', 'addressline3', 'addressline4', 'zipcode', 'town', 'state', 'country', 'purpose')
      }),
   )
   allow_add = True
   
class ContactPhoneAddress(admin.TabularInline):
   model = PhoneAddressForContact
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('phone', 'purpose',)
      }),
   )
   allow_add = True
   
class ContactEmailAddress(admin.TabularInline):
   model = EmailAddressForContact
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('email', 'purpose',)
      }),
   )
   allow_add = True

class OptionCustomer(admin.ModelAdmin):
   list_display = ('id', 'name', 'defaultCustomerBillingCycle', )
   fieldsets = (('', {'fields': ('name', 'defaultCustomerBillingCycle', 'ismemberof',)}),)
   allow_add = True   
   ordering       = ('id', 'name')
   search_fields  = ('id', 'name')
   inlines = [ContactPostalAddress, ContactPhoneAddress, ContactEmailAddress]
   pluginProcessor = PluginProcessor()
   inlines.extend(pluginProcessor.getPluginAdditions("customerInline"))

   def createContract(self, request, queryset):
      for obj in queryset:
         contract = obj.createContract(request)
         response = HttpResponseRedirect('/admin/crm/contract/'+str(contract.id))
      return response
   createContract.short_description = _("Create Contract")
   
   def createQuote(self, request, queryset):
      for obj in queryset:
         quote = obj.createQuote()
         response = HttpResponseRedirect('/admin/crm/quote/'+str(quote.id))
      return response
   createQuote.short_description = _("Create Quote")
   
   def createInvoice(self, request, queryset):
      for obj in queryset:
         invoice = obj.createInvoice()
         response = HttpResponseRedirect('/admin/crm/invoice/'+str(invoice.id))
      return response
   createInvoice.short_description = _("Create Invoice")
   
   def save_model(self, request, obj, form, change):
     if (change == True):
       obj.lastmodifiedby = request.user
     else:
       obj.lastmodifiedby = request.user
       obj.staff = request.user
     obj.save()
   actions = ['createContract', 'createInvoice', 'createQuote']
   pluginProcessor = PluginProcessor()
   inlines.extend(pluginProcessor.getPluginAdditions("customerActions"))

class OptionCustomerGroup(admin.ModelAdmin):
   list_display = ('id', 'name' )
   fieldsets = (('', {'fields': ('name',)}),)
   allow_add = True

class OptionSupplier(admin.ModelAdmin):
   list_display = ('id', 'name')
   fieldsets = (('', {'fields': ('name',)}),)
   inlines = [ContactPostalAddress, ContactPhoneAddress, ContactEmailAddress]
   allow_add = True
   
   def save_model(self, request, obj, form, change):
     if (change == True):
       obj.lastmodifiedby = request.user
     else:
       obj.lastmodifiedby = request.user
       obj.staff = request.user
     obj.save()
   
class OptionUnit(admin.ModelAdmin):
   list_display = ('id', 'description', 'shortName', 'isAFractionOf', 'fractionFactorToNextHigherUnit')
   fieldsets = (('', {'fields': ('description', 'shortName', 'isAFractionOf', 'fractionFactorToNextHigherUnit')}),)
   allow_add = True
      
class OptionCurrency(admin.ModelAdmin):
   list_display = ('id', 'description', 'shortName', 'rounding')
   fieldsets = (('', {'fields': ('description', 'shortName', 'rounding')}),)
   allow_add = True
   
class OptionTax(admin.ModelAdmin):
   list_display = ('id', 'taxrate', 'name', 'accountActiva', 'accountPassiva')
   fieldsets = (('', {'fields': ('taxrate', 'name', 'accountActiva', 'accountPassiva')}),)
   allow_add = True
   
class OptionCustomerBillingCycle(admin.ModelAdmin):
   list_display = ('id', 'timeToPaymentDate', 'name')
   fieldsets = (('', {'fields': ('timeToPaymentDate', 'name',)}),)
   allow_add = True

 
admin.site.register(Customer, OptionCustomer)
admin.site.register(CustomerGroup, OptionCustomerGroup)
admin.site.register(Supplier, OptionSupplier)
admin.site.register(Quote, OptionQuote)
admin.site.register(Invoice, OptionInvoice)
admin.site.register(Unit, OptionUnit)
admin.site.register(Currency, OptionCurrency)
admin.site.register(Tax, OptionTax)
admin.site.register(CustomerBillingCycle, OptionCustomerBillingCycle)
admin.site.register(Contract, OptionContract)
admin.site.register(PurchaseOrder, OptionPurchaseOrder)
admin.site.register(Product, OptionProduct)

########NEW FILE########
__FILENAME__ = country
# -*- coding: utf-8 -*

from django.utils.translation import ugettext as _

COUNTRIES = (
    ('AF', 'AFG', '004', _('Afghanistan')),
    ('AX', 'ALA', '248', _('Aland Islands')),
    ('AL', 'ALB', '008', _('Albania')),
    ('DZ', 'DZA', '012', _('Algeria')),
    ('AS', 'ASM', '016', _('American Samoa')),
    ('AD', 'AND', '020', _('Andorra')),
    ('AO', 'AGO', '024', _('Angola')),
    ('AI', 'AIA', '660', _('Anguilla')),
    ('AQ', 'ATA', '010', _('Antarctica')),
    ('AG', 'ATG', '028', _('Antigua and Barbuda')),
    ('AR', 'ARG', '032', _('Argentina')),
    ('AM', 'ARM', '051', _('Armenia')),
    ('AW', 'ABW', '533', _('Aruba')),
    ('AU', 'AUS', '036', _('Australia')),
    ('AT', 'AUT', '040', _('Austria')),
    ('AZ', 'AZE', '031', _('Azerbaijan')),
    ('BS', 'BHS', '044', _('the Bahamas')),
    ('BH', 'BHR', '048', _('Bahrain')),
    ('BD', 'BGD', '050', _('Bangladesh')),
    ('BB', 'BRB', '052', _('Barbados')),
    ('BY', 'BLR', '112', _('Belarus')),
    ('BE', 'BEL', '056', _('Belgium')),
    ('BZ', 'BLZ', '084', _('Belize')),
    ('BJ', 'BEN', '204', _('Benin')),
    ('BM', 'BMU', '060', _('Bermuda')),
    ('BT', 'BTN', '064', _('Bhutan')),
    ('BO', 'BOL', '068', _('Bolivia')),
    ('BA', 'BIH', '070', _('Bosnia and Herzegovina')),
    ('BW', 'BWA', '072', _('Botswana')),
    ('BV', 'BVT', '074', _('Bouvet Island')),
    ('BR', 'BRA', '076', _('Brazil')),
    ('IO', 'IOT', '086', _('British Indian Ocean Territory')),
    ('BN', 'BRN', '096', _('Brunei Darussalam')),
    ('BG', 'BGR', '100', _('Bulgaria')),
    ('BF', 'BFA', '854', _('Burkina Faso')),
    ('BI', 'BDI', '108', _('Burundi')),
    ('KH', 'KHM', '116', _('Cambodia')),
    ('CM', 'CMR', '120', _('Cameroon')),
    ('CA', 'CAN', '124', _('Canada')),
    ('CV', 'CPV', '132', _('Cape Verde')),
    ('KY', 'CYM', '136', _('Cayman Islands')),
    ('CF', 'CAF', '140', _('Central African Republic')),
    ('TD', 'TCD', '148', _('Chad')),
    ('CL', 'CHL', '152', _('Chile')),
    ('CN', 'CHN', '156', _('China')),
    ('CX', 'CXR', '162', _('Christmas Island')),
    ('CC', 'CCK', '166', _('Cocos (Keeling) Islands')),
    ('CO', 'COL', '170', _('Colombia')),
    ('KM', 'COM', '174', _('Comoros')),
    ('CG', 'COG', '178', _('Congo')),
    ('CD', 'COD', '180', _('Democratic Republic of the Congo')),
    ('CK', 'COK', '184', _('Cook Islands')),
    ('CR', 'CRI', '188', _('Costa Rica')),
    ('CI', 'CIV', '384', _('Cote d\'Ivoire')),
    ('HR', 'HRV', '191', _('Croatia')),
    ('CU', 'CUB', '192', _('Cuba')),
    ('CY', 'CYP', '196', _('Cyprus')),
    ('CZ', 'CZE', '203', _('Czech Republic')),
    ('DK', 'DNK', '208', _('Denmark')),
    ('DJ', 'DJI', '262', _('Djibouti')),
    ('DM', 'DMA', '212', _('Dominica')),
    ('DO', 'DOM', '214', _('Dominican Republic')),
    ('EC', 'ECU', '218', _('Ecuador')),
    ('EG', 'EGY', '818', _('Egypt')),
    ('SV', 'SLV', '222', _('El Salvador')),
    ('GQ', 'GNQ', '226', _('Equatorial Guinea')),
    ('ER', 'ERI', '232', _('Eritrea')),
    ('EE', 'EST', '233', _('Estonia')),
    ('ET', 'ETH', '231', _('Ethiopia')),
    ('FK', 'FLK', '238', _('Falkland Islands (Malvinas)')),
    ('FO', 'FRO', '234', _('Faroe Islands')),
    ('FJ', 'FJI', '242', _('Fiji')),
    ('FI', 'FIN', '246', _('Finland')),
    ('FR', 'FRA', '250', _('France')),
    ('GF', 'GUF', '254', _('French Guiana')),
    ('PF', 'PYF', '258', _('French Polynesia')),
    ('TF', 'ATF', '260', _('French Southern and Antarctic Lands')),
    ('GA', 'GAB', '266', _('Gabon')),
    ('GM', 'GMB', '270', _('Gambia')),
    ('GE', 'GEO', '268', _('Georgia')),
    ('DE', 'DEU', '276', _('Germany')),
    ('GH', 'GHA', '288', _('Ghana')),
    ('GI', 'GIB', '292', _('Gibraltar')),
    ('GR', 'GRC', '300', _('Greece')),
    ('GL', 'GRL', '304', _('Greenland')),
    ('GD', 'GRD', '308', _('Grenada')), 
    ('GP', 'GLP', '312', _('Guadeloupe')),
    ('GU', 'GUM', '316', _('Guam')),
    ('GT', 'GTM', '320', _('Guatemala')),
    ('GG', 'GGY', '831', _('Guernsey')),
    ('GN', 'GIN', '324', _('Guinea')),
    ('GW', 'GNB', '624', _('Guinea-Bissau')),
    ('GY', 'GUY', '328', _('Guyana')),
    ('HT', 'HTI', '332', _('Haiti')),
    ('HM', 'HMD', '334', _('Heard Island and McDonald Islands')),
    ('VA', 'VAT', '336', _('Vatican City Holy See')),
    ('HN', 'HND', '340', _('Honduras')),
    ('HK', 'HKG', '344', _('Hong Kong')),
    ('HU', 'HUN', '348', _('Hungary')),
    ('IS', 'ISL', '352', _('Iceland')),
    ('IN', 'IND', '356', _('India')),
    ('ID', 'IDN', '360', _('Indonesia')),
    ('IR', 'IRN', '364', _('Iran')),
    ('IQ', 'IRQ', '368', _('Iraq')),
    ('IE', 'IRL', '372', _('Ireland')),
    ('IM', 'IMN', '833', _('Isle of Man')),
    ('IL', 'ISR', '376', _('Israel')),
    ('IT', 'ITA', '380', _('Italy')),
    ('JM', 'JAM', '388', _('Jamaica')),
    ('JP', 'JPN', '392', _('Japan')),
    ('JE', 'JEY', '832', _('Jersey')),
    ('JO', 'JOR', '400', _('Jordan')),
    ('KZ', 'KAZ', '398', _('Kazakhstan')),
    ('KE', 'KEN', '404', _('Kenya')),
    ('KI', 'KIR', '296', _('Kiribati')),
    ('KP', 'PRK', '408', _('North Korea')),
    ('KR', 'KOR', '410', _('South Korea')),
    ('KW', 'KWT', '414', _('Kuwait')),
    ('KG', 'KGZ', '417', _('Kyrgyzstan')),
    ('LA', 'LAO', '418', _('Laos Lao')),
    ('LV', 'LVA', '428', _('Latvia')),
    ('LB', 'LBN', '422', _('Lebanon')),
    ('LS', 'LSO', '426', _('Lesotho')),
    ('LR', 'LBR', '430', _('Liberia')),
    ('LY', 'LBY', '434', _('Libya Libyan Arab Jamahiriya')),
    ('LI', 'LIE', '438', _('Liechtenstein')),
    ('LT', 'LTU', '440', _('Lithuania')),
    ('LU', 'LUX', '442', _('Luxembourg')),
    ('MO', 'MAC', '446', _('Macau Macao')),
    ('MK', 'MKD', '807', _('Macedonia')),
    ('MG', 'MDG', '450', _('Madagascar')),
    ('MW', 'MWI', '454', _('Malawi')),
    ('MY', 'MYS', '458', _('Malaysia')),
    ('MV', 'MDV', '462', _('Maldives')),
    ('ML', 'MLI', '466', _('Mali')),
    ('MT', 'MLT', '470', _('Malta')),
    ('MH', 'MHL', '584', _('Marshall Islands')),
    ('MQ', 'MTQ', '474', _('Martinique')),
    ('MR', 'MRT', '478', _('Mauritania')),
    ('MU', 'MUS', '480', _('Mauritius')),
    ('YT', 'MYT', '175', _('Mayotte')),
    ('MX', 'MEX', '484', _('Mexico')),
    ('FM', 'FSM', '583', _('Micronesia')),
    ('MD', 'MDA', '498', _('Moldova')),
    ('MC', 'MCO', '492', _('Monaco')),
    ('MN', 'MNG', '496', _('Mongolia')),
    ('ME', 'MNE', '499', _('Montenegro')),
    ('MS', 'MSR', '500', _('Montserrat')),
    ('MA', 'MAR', '504', _('Morocco')),
    ('MZ', 'MOZ', '508', _('Mozambique')),
    ('MM', 'MMR', '104', _('Myanmar')),
    ('NA', 'NAM', '516', _('Namibia')),
    ('NR', 'NRU', '520', _('Nauru')),
    ('NP', 'NPL', '524', _('Nepal')),
    ('NL', 'NLD', '528', _('Netherlands')),
    ('AN', 'ANT', '530', _('Netherlands Antilles')),
    ('NC', 'NCL', '540', _('New Caledonia')),
    ('NZ', 'NZL', '554', _('New Zealand')),
    ('NI', 'NIC', '558', _('Nicaragua')),
    ('NE', 'NER', '562', _('Niger')),
    ('NG', 'NGA', '566', _('Nigeria')),
    ('NU', 'NIU', '570', _('Niue')),
    ('NF', 'NFK', '574', _('Norfolk Island Norfolk Island')),
    ('MP', 'MNP', '580', _('Northern Mariana Islands')),
    ('NO', 'NOR', '578', _('Norway')),
    ('OM', 'OMN', '512', _('Oman')),
    ('PK', 'PAK', '586', _('Pakistan')),
    ('PW', 'PLW', '585', _('Palau')),
    ('PS', 'PSE', '275', _('Palestinian Territory')),
    ('PA', 'PAN', '591', _('Panama')),
    ('PG', 'PNG', '598', _('Papua New Guinea')),
    ('PY', 'PRY', '600', _('Paraguay')),
    ('PE', 'PER', '604', _('Peru')),
    ('PH', 'PHL', '608', _('Philippines')),
    ('PN', 'PCN', '612', _('Pitcairn Islands')),
    ('PL', 'POL', '616', _('Poland')),
    ('PT', 'PRT', '620', _('Portugal')),
    ('PR', 'PRI', '630', _('Puerto Rico')),
    ('QA', 'QAT', '634', _('Qatar')),
    ('RE', 'REU', '638', _('Reunion')),
    ('RO', 'ROU', '642', _('Romania')),
    ('RU', 'RUS', '643', _('Russia')),
    ('RW', 'RWA', '646', _('Rwanda')),
    ('SH', 'SHN', '654', _('Saint Helena')),
    ('KN', 'KNA', '659', _('Saint Kitts and Nevis')),
    ('LC', 'LCA', '662', _('Saint Lucia')),
    ('PM', 'SPM', '666', _('Saint Pierre and Miquelon')),
    ('VC', 'VCT', '670', _('Saint Vincent and the Grenadines')),
    ('WS', 'WSM', '882', _('Samoa')),
    ('SM', 'SMR', '674', _('San Marino')),
    ('ST', 'STP', '678', _('Sao Tome and Principe')),
    ('SA', 'SAU', '682', _('Saudi Arabia')),
    ('SN', 'SEN', '686', _('Senegal')),
    ('RS', 'SRB', '688', _('Serbia')),
    ('SC', 'SYC', '690', _('Seychelles')),
    ('SL', 'SLE', '694', _('Sierra Leone')),
    ('SG', 'SGP', '702', _('Singapore')),
    ('SK', 'SVK', '703', _('Slovakia')),
    ('SI', 'SVN', '705', _('Slovenia')),
    ('SB', 'SLB', '090', _('Solomon Islands')),
    ('SO', 'SOM', '706', _('Somalia')),
    ('ZA', 'ZAF', '710', _('South Africa')),
    ('GS', 'SGS', '239', _('South Georgia and the South Sandwich Islands')),
    ('ES', 'ESP', '724', _('Spain')),
    ('LK', 'LKA', '144', _('Sri Lanka')),
    ('SD', 'SDN', '736', _('Sudan')),
    ('SR', 'SUR', '740', _('Suriname')),
    ('SJ', 'SJM', '744', _('Svalbard and Jan Mayen')),
    ('SZ', 'SWZ', '748', _('Swaziland')),
    ('SE', 'SWE', '752', _('Sweden')),
    ('CH', 'CHE', '756', _('Switzerland')),
    ('SY', 'SYR', '760', _('Syria')),
    ('TW', 'TWN', '158', _('Taiwan')),
    ('TJ', 'TJK', '762', _('Tajikistan')),
    ('TZ', 'TZA', '834', _('Tanzania')),
    ('TH', 'THA', '764', _('Thailand')),
    ('TL', 'TLS', '626', _('East Timor')),
    ('TG', 'TGO', '768', _('Togo')),
    ('TK', 'TKL', '772', _('Tokelau')),
    ('TO', 'TON', '776', _('Tonga')),
    ('TT', 'TTO', '780', _('Trinidad and Tobago')),
    ('TN', 'TUN', '788', _('Tunisia')),
    ('TR', 'TUR', '792', _('Turkey')),
    ('TM', 'TKM', '795', _('Turkmenistan')),
    ('TC', 'TCA', '796', _('Turks and Caicos Islands')),
    ('TV', 'TUV', '798', _('Tuvalu')),
    ('UG', 'UGA', '800', _('Uganda')),
    ('UA', 'UKR', '804', _('Ukraine')),
    ('AE', 'ARE', '784', _('United Arab Emirates')),
    ('GB', 'GBR', '826', _('United Kingdom')),
    ('US', 'USA', '840', _('United States')),
    ('UM', 'UMI', '581', _('United States Minor Outlying Islands')),
    ('UY', 'URY', '858', _('Uruguay')),
    ('UZ', 'UZB', '860', _('Uzbekistan')),
    ('VU', 'VUT', '548', _('Vanuatu')),
    ('VE', 'VEN', '862', _('Venezuela')),
    ('VN', 'VNM', '704', _('Vietnam Viet Nam')),
    ('VG', 'VGB', '092', _('British Virgin Islands')),
    ('VI', 'VIR', '850', _('United States Virgin Islands')),
    ('WF', 'WLF', '876', _('Wallis and Futuna')),
    ('EH', 'ESH', '732', _('Western Sahara')),
    ('YE', 'YEM', '887', _('Yemen')),
    ('ZM', 'ZMB', '894', _('Zambia')),
    ('ZW', 'ZWE', '716', _('Zimbabwe')),
)
########NEW FILE########
__FILENAME__ = postaladdressprefix
# -*- coding: utf-8 -*

from django.utils.translation import ugettext as _

POSTALADDRESSPREFIX = (
    ('F', _('Company')),
    ('W', _('Mrs')),
    ('H', _('Mr')),
    ('G', _('Ms')),
)
########NEW FILE########
__FILENAME__ = purpose
# -*- coding: utf-8 -*

from django.utils.translation import ugettext as _

PURPOSESADDRESSINCONTRACT = (
    ('D', _('Delivery Address')),
    ('B', _('Billing Address')),
    ('C', _('Contact Address')),
)

PURPOSESADDRESSINCUSTOMER = (
    ('H', _('Private')),
    ('O', _('Business')),
    ('P', _('Mobile Private')),
    ('B', _('Mobile Business')),
)
########NEW FILE########
__FILENAME__ = status
# -*- coding: utf-8 -*

from django.utils.translation import ugettext as _

INVOICESTATUS = (
    ('P', _('Payed')),
    ('C', _('Invoice created')),
    ('I', _('Invoice sent')),
    ('F', _('First reminder sent')),
    ('R', _('Second reminder sent')),
    ('U', _('Customer cant pay')),
    ('D', _('Deleted')),
)

QUOTESTATUS = (
    ('S', _('Success')),
    ('I', _('Quote created')),
    ('Q', _('Quote sent')),
    ('F', _('First reminder sent')),
    ('R', _('Second reminder sent')),
    ('D', _('Deleted')),
)

PURCHASEORDERSTATUS = (
    ('O', _('Ordered')),
    ('D', _('Delayed')),
    ('Y', _('Delivered')),
    ('I', _('Invoice registered')),
    ('P', _('Invoice payed')),
)

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-

class TemplateSetMissing(Exception):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)
    
class UserExtensionMissing(Exception):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)
        
########NEW FILE########
__FILENAME__ = koalixcrm_install_defaulttemplates
# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from shutil import copy
from os import path
from os import mkdir
from django.core.management.base import BaseCommand, CommandError
import djangoUserExtension
import crm
from django.contrib.auth.models import User
from filebrowser.fields import FileBrowseField
from filebrowser.settings import DIRECTORY
from filebrowser.settings import MEDIA_ROOT
from settings import PROJECT_ROOT

DEFAULT_FILE = 'dashboard.py'

class Command(BaseCommand):
    help = ('This Command is going to install the default Templates, given by the koalixcrm base installation, in your django instance. Be sure you first run syncdb')
    args = '[]'
    label = 'application name'

    def handle(self, **options):
      invoicetemplate = 'invoice.xsl'
      quotetemplate = 'quote.xsl'
      deliveryordertemplate = 'deliveryorder.xsl'
      purchaseordertemplate = 'purchaseorder.xsl'
      purchaseconfirmationtemplate = 'purchaseconfirmation.xsl'
      balancesheettemplate = 'balancesheet.xsl'
      profitlossstatementtemplate = 'profitlossstatement.xsl'
      listoftemplatefiles = {'invoice' : invoicetemplate, 
      'quote' : quotetemplate,
      'deliveryorder' : deliveryordertemplate,
      'purchaseconfirmation' : purchaseconfirmationtemplate,
      'purchaseorder' : purchaseordertemplate,
      'balancesheet' : balancesheettemplate,
      'profitlossstatement' : profitlossstatementtemplate,
      }
      
      configfile = 'fontconfig.xml'
      dejavusansfile = 'dejavusans-bold.xml'
      dejavusansboldfile = 'dejavusans.xml'
      logo = 'logo.jpg'
      copy('templatefiles/generic/'+configfile, MEDIA_ROOT+DIRECTORY+'templatefiles/'+configfile)
      copy('templatefiles/generic/'+logo, MEDIA_ROOT+DIRECTORY+'templatefiles/'+logo)
      copy('templatefiles/generic/'+dejavusansfile, MEDIA_ROOT+DIRECTORY+'templatefiles/'+dejavusansfile)
      copy('templatefiles/generic/'+dejavusansboldfile, MEDIA_ROOT+DIRECTORY+'templatefiles/'+dejavusansboldfile)
      listofadditionalfiles = ('dejavusans-bold.xml', 'dejavusans.xml', )
      if path.exists('templatefiles'):
        templateset = djangoUserExtension.models.TemplateSet()
        templateset.title = 'defaultTemplateSet'
        if (path.exists(MEDIA_ROOT+DIRECTORY+'templatefiles') == False):
          mkdir(MEDIA_ROOT+DIRECTORY+'templatefiles')
        for template in listoftemplatefiles:
          if path.exists(PROJECT_ROOT+'templatefiles/en/'+listoftemplatefiles[template]):
            copy('templatefiles/en/'+listoftemplatefiles[template], MEDIA_ROOT+DIRECTORY+'templatefiles/'+listoftemplatefiles[template])
            xslfile = djangoUserExtension.models.XSLFile()
            xslfile.title = template
            xslfile.xslfile = DIRECTORY+'templatefiles/'+listoftemplatefiles[template]
            xslfile.save()
            if template == 'invoice' :
              templateset.invoiceXSLFile = xslfile
            elif template == 'quote' :
              templateset.quoteXSLFile = xslfile
            elif template == 'purchaseconfirmation' :
              templateset.purchaseconfirmationXSLFile = xslfile
            elif template == 'purchaseorder' :
              templateset.purchaseorderXSLFile = xslfile
            elif template == 'deliveryorder' :
              templateset.deilveryorderXSLFile = xslfile
            elif template == 'profitlossstatement' :
              templateset.profitLossStatementXSLFile = xslfile
            elif template == 'balancesheet' :
              templateset.balancesheetXSLFile = xslfile
            print(listoftemplatefiles[template])
          else:
            print(listoftemplatefiles)
            print(listoftemplatefiles[template])
            print(template)
            print(MEDIA_ROOT+DIRECTORY+'templatefiles/'+listoftemplatefiles[template])
            raise FileNotFoundException
        templateset.logo = DIRECTORY+'templatefiles/'+logo
        templateset.bankingaccountref = "xx-xxxxxx-x"
        templateset.addresser = _("John Smit, Sample Company, 8976 Smallville")
        templateset.fopConfigurationFile = DIRECTORY+'templatefiles/'+configfile
        templateset.headerTextsalesorders = _("According to your wishes the contract consists of the following positions:")
        templateset.footerTextsalesorders = _("Thank you for your interest in our company \n Best regards")
        templateset.headerTextpurchaseorders = _("We would like to order the following positions:")
        templateset.footerTextpurchaseorders = _("Best regards")
        templateset.pagefooterleft = _("Sample Company")
        templateset.pagefootermiddle = _("Sample Address")
        templateset.save()
        currency = crm.models.Currency()
        currency.description = "US Dollar"
        currency.shortName = "USD"
        currency.rounding = "0.10"
        currency.save()
        userExtension = djangoUserExtension.models.UserExtension()
        userExtension.defaultTemplateSet = templateset
        userExtension.defaultCurrency = currency
        userExtension.user = User.objects.all()[0]
        userExtension.save()
        postaladdress = djangoUserExtension.models.UserExtensionPostalAddress()
        postaladdress.purpose = 'H'
        postaladdress.name = "John"
        postaladdress.prename = "Smith"
        postaladdress.addressline1 = "Ave 1"
        postaladdress.zipcode = 899887
        postaladdress.town = "Smallville"
        postaladdress.userExtension = userExtension
        postaladdress.save()
        phoneaddress = djangoUserExtension.models.UserExtensionPhoneAddress()
        phoneaddress.phone = "1293847"
        phoneaddress.purpose = 'H'
        phoneaddress.userExtension = userExtension
        phoneaddress.save()
        emailaddress = djangoUserExtension.models.UserExtensionEmailAddress()
        emailaddress.email = "john.smith@smallville.com"
        emailaddress.purpose = 'H'
        emailaddress.userExtension = userExtension
        emailaddress.save()
            
        for additionalfile in listofadditionalfiles:
          if path.exists('templatefiles'+additionalfile):
            shutil.copy('templatefiles'+additionalfile, DIRECTORY+'templatefiles/')
       

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Currency'
        db.create_table('crm_currency', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('shortName', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('rounding', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
        ))
        db.send_create_signal('crm', ['Currency'])

        # Adding model 'PostalAddress'
        db.create_table('crm_postaladdress', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('prefix', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('prename', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('addressline1', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('addressline2', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('addressline3', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('addressline4', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('zipcode', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('town', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True)),
        ))
        db.send_create_signal('crm', ['PostalAddress'])

        # Adding model 'PhoneAddress'
        db.create_table('crm_phoneaddress', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal('crm', ['PhoneAddress'])

        # Adding model 'EmailAddress'
        db.create_table('crm_emailaddress', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=200)),
        ))
        db.send_create_signal('crm', ['EmailAddress'])

        # Adding model 'Contact'
        db.create_table('crm_contact', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('dateofcreation', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('lastmodification', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('lastmodifiedby', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], blank=True)),
        ))
        db.send_create_signal('crm', ['Contact'])

        # Adding model 'CustomerBillingCycle'
        db.create_table('crm_customerbillingcycle', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('timeToPaymentDate', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('crm', ['CustomerBillingCycle'])

        # Adding model 'CustomerGroup'
        db.create_table('crm_customergroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=300)),
        ))
        db.send_create_signal('crm', ['CustomerGroup'])

        # Adding model 'Customer'
        db.create_table('crm_customer', (
            ('contact_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.Contact'], unique=True, primary_key=True)),
            ('defaultCustomerBillingCycle', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.CustomerBillingCycle'])),
        ))
        db.send_create_signal('crm', ['Customer'])

        # Adding M2M table for field ismemberof on 'Customer'
        db.create_table('crm_customer_ismemberof', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('customer', models.ForeignKey(orm['crm.customer'], null=False)),
            ('customergroup', models.ForeignKey(orm['crm.customergroup'], null=False))
        ))
        db.create_unique('crm_customer_ismemberof', ['customer_id', 'customergroup_id'])

        # Adding model 'Supplier'
        db.create_table('crm_supplier', (
            ('contact_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.Contact'], unique=True, primary_key=True)),
            ('offersShipmentToCustomers', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('crm', ['Supplier'])

        # Adding model 'Contract'
        db.create_table('crm_contract', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('staff', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='db_relcontractstaff', null=True, to=orm['auth.User'])),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('defaultcustomer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Customer'], null=True, blank=True)),
            ('defaultSupplier', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Supplier'], null=True, blank=True)),
            ('defaultcurrency', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Currency'])),
            ('dateofcreation', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('lastmodification', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('lastmodifiedby', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_contractlstmodified', to=orm['auth.User'])),
        ))
        db.send_create_signal('crm', ['Contract'])

        # Adding model 'PurchaseOrder'
        db.create_table('crm_purchaseorder', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Contract'])),
            ('externalReference', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('supplier', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Supplier'])),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('lastPricingDate', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('lastCalculatedPrice', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=17, decimal_places=2, blank=True)),
            ('lastCalculatedTax', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=17, decimal_places=2, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('staff', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='db_relpostaff', null=True, to=orm['auth.User'])),
            ('currency', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Currency'])),
            ('dateofcreation', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('lastmodification', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('lastmodifiedby', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_polstmodified', to=orm['auth.User'])),
        ))
        db.send_create_signal('crm', ['PurchaseOrder'])

        # Adding model 'SalesContract'
        db.create_table('crm_salescontract', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Contract'])),
            ('externalReference', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('discount', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('lastPricingDate', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('lastCalculatedPrice', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=17, decimal_places=2, blank=True)),
            ('lastCalculatedTax', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=17, decimal_places=2, blank=True)),
            ('customer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Customer'])),
            ('staff', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='db_relscstaff', null=True, to=orm['auth.User'])),
            ('currency', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Currency'])),
            ('dateofcreation', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('lastmodification', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('lastmodifiedby', self.gf('django.db.models.fields.related.ForeignKey')(blank='True', related_name='db_lstscmodified', null=True, to=orm['auth.User'])),
        ))
        db.send_create_signal('crm', ['SalesContract'])

        # Adding model 'Quote'
        db.create_table('crm_quote', (
            ('salescontract_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.SalesContract'], unique=True, primary_key=True)),
            ('validuntil', self.gf('django.db.models.fields.DateField')()),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=1)),
        ))
        db.send_create_signal('crm', ['Quote'])

        # Adding model 'Invoice'
        db.create_table('crm_invoice', (
            ('salescontract_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.SalesContract'], unique=True, primary_key=True)),
            ('payableuntil', self.gf('django.db.models.fields.DateField')()),
            ('derivatedFromQuote', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Quote'], null=True, blank=True)),
            ('paymentBankReference', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=1)),
        ))
        db.send_create_signal('crm', ['Invoice'])

        # Adding model 'Unit'
        db.create_table('crm_unit', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('shortName', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('isAFractionOf', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Unit'], null=True, blank=True)),
            ('fractionFactorToNextHigherUnit', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('crm', ['Unit'])

        # Adding model 'Tax'
        db.create_table('crm_tax', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('taxrate', self.gf('django.db.models.fields.DecimalField')(max_digits=5, decimal_places=2)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('accountActiva', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='db_relaccountactiva', null=True, to=orm['accounting.Account'])),
            ('accountPassiva', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='db_relaccountpassiva', null=True, to=orm['accounting.Account'])),
        ))
        db.send_create_signal('crm', ['Tax'])

        # Adding model 'Product'
        db.create_table('crm_product', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('productNumber', self.gf('django.db.models.fields.IntegerField')()),
            ('defaultunit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Unit'])),
            ('dateofcreation', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('lastmodification', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('lastmodifiedby', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank='True')),
            ('tax', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Tax'])),
            ('accoutingProductCategorie', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounting.ProductCategorie'], null=True, blank='True')),
        ))
        db.send_create_signal('crm', ['Product'])

        # Adding model 'UnitTransform'
        db.create_table('crm_unittransform', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('fromUnit', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_reltransfromfromunit', to=orm['crm.Unit'])),
            ('toUnit', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_reltransfromtounit', to=orm['crm.Unit'])),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Product'])),
            ('factor', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('crm', ['UnitTransform'])

        # Adding model 'CustomerGroupTransform'
        db.create_table('crm_customergrouptransform', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('fromCustomerGroup', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_reltransfromfromcustomergroup', to=orm['crm.CustomerGroup'])),
            ('toCustomerGroup', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_reltransfromtocustomergroup', to=orm['crm.CustomerGroup'])),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Product'])),
            ('factor', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('crm', ['CustomerGroupTransform'])

        # Adding model 'Price'
        db.create_table('crm_price', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Product'])),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Unit'])),
            ('currency', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Currency'])),
            ('customerGroup', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.CustomerGroup'], null=True, blank=True)),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=17, decimal_places=2)),
            ('validfrom', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('validuntil', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
        ))
        db.send_create_signal('crm', ['Price'])

        # Adding model 'Position'
        db.create_table('crm_position', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('positionNumber', self.gf('django.db.models.fields.IntegerField')()),
            ('quantity', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=3)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('discount', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Product'], null=True, blank=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Unit'], null=True, blank=True)),
            ('sentOn', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('supplier', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Supplier'], null=True, blank=True)),
            ('shipmentID', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('overwriteProductPrice', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('positionPricePerUnit', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=17, decimal_places=2, blank=True)),
            ('lastPricingDate', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('lastCalculatedPrice', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=17, decimal_places=2, blank=True)),
            ('lastCalculatedTax', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=17, decimal_places=2, blank=True)),
        ))
        db.send_create_signal('crm', ['Position'])

        # Adding model 'SalesContractPosition'
        db.create_table('crm_salescontractposition', (
            ('position_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.Position'], unique=True, primary_key=True)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.SalesContract'])),
        ))
        db.send_create_signal('crm', ['SalesContractPosition'])

        # Adding model 'PurchaseOrderPosition'
        db.create_table('crm_purchaseorderposition', (
            ('position_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.Position'], unique=True, primary_key=True)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.PurchaseOrder'])),
        ))
        db.send_create_signal('crm', ['PurchaseOrderPosition'])

        # Adding model 'PhoneAddressForContact'
        db.create_table('crm_phoneaddressforcontact', (
            ('phoneaddress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.PhoneAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Contact'])),
        ))
        db.send_create_signal('crm', ['PhoneAddressForContact'])

        # Adding model 'EmailAddressForContact'
        db.create_table('crm_emailaddressforcontact', (
            ('emailaddress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.EmailAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Contact'])),
        ))
        db.send_create_signal('crm', ['EmailAddressForContact'])

        # Adding model 'PostalAddressForContact'
        db.create_table('crm_postaladdressforcontact', (
            ('postaladdress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.PostalAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Contact'])),
        ))
        db.send_create_signal('crm', ['PostalAddressForContact'])

        # Adding model 'PostalAddressForContract'
        db.create_table('crm_postaladdressforcontract', (
            ('postaladdress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.PostalAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Contract'])),
        ))
        db.send_create_signal('crm', ['PostalAddressForContract'])

        # Adding model 'PostalAddressForPurchaseOrder'
        db.create_table('crm_postaladdressforpurchaseorder', (
            ('postaladdress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.PostalAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.PurchaseOrder'])),
        ))
        db.send_create_signal('crm', ['PostalAddressForPurchaseOrder'])

        # Adding model 'PostalAddressForSalesContract'
        db.create_table('crm_postaladdressforsalescontract', (
            ('postaladdress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.PostalAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.SalesContract'])),
        ))
        db.send_create_signal('crm', ['PostalAddressForSalesContract'])

        # Adding model 'PhoneAddressForContract'
        db.create_table('crm_phoneaddressforcontract', (
            ('phoneaddress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.PhoneAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Contract'])),
        ))
        db.send_create_signal('crm', ['PhoneAddressForContract'])

        # Adding model 'PhoneAddressForSalesContract'
        db.create_table('crm_phoneaddressforsalescontract', (
            ('phoneaddress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.PhoneAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.SalesContract'])),
        ))
        db.send_create_signal('crm', ['PhoneAddressForSalesContract'])

        # Adding model 'PhoneAddressForPurchaseOrder'
        db.create_table('crm_phoneaddressforpurchaseorder', (
            ('phoneaddress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.PhoneAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.PurchaseOrder'])),
        ))
        db.send_create_signal('crm', ['PhoneAddressForPurchaseOrder'])

        # Adding model 'EmailAddressForContract'
        db.create_table('crm_emailaddressforcontract', (
            ('emailaddress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.EmailAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Contract'])),
        ))
        db.send_create_signal('crm', ['EmailAddressForContract'])

        # Adding model 'EmailAddressForSalesContract'
        db.create_table('crm_emailaddressforsalescontract', (
            ('emailaddress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.EmailAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.SalesContract'])),
        ))
        db.send_create_signal('crm', ['EmailAddressForSalesContract'])

        # Adding model 'EmailAddressForPurchaseOrder'
        db.create_table('crm_emailaddressforpurchaseorder', (
            ('emailaddress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.EmailAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.PurchaseOrder'])),
        ))
        db.send_create_signal('crm', ['EmailAddressForPurchaseOrder'])


    def backwards(self, orm):
        # Deleting model 'Currency'
        db.delete_table('crm_currency')

        # Deleting model 'PostalAddress'
        db.delete_table('crm_postaladdress')

        # Deleting model 'PhoneAddress'
        db.delete_table('crm_phoneaddress')

        # Deleting model 'EmailAddress'
        db.delete_table('crm_emailaddress')

        # Deleting model 'Contact'
        db.delete_table('crm_contact')

        # Deleting model 'CustomerBillingCycle'
        db.delete_table('crm_customerbillingcycle')

        # Deleting model 'CustomerGroup'
        db.delete_table('crm_customergroup')

        # Deleting model 'Customer'
        db.delete_table('crm_customer')

        # Removing M2M table for field ismemberof on 'Customer'
        db.delete_table('crm_customer_ismemberof')

        # Deleting model 'Supplier'
        db.delete_table('crm_supplier')

        # Deleting model 'Contract'
        db.delete_table('crm_contract')

        # Deleting model 'PurchaseOrder'
        db.delete_table('crm_purchaseorder')

        # Deleting model 'SalesContract'
        db.delete_table('crm_salescontract')

        # Deleting model 'Quote'
        db.delete_table('crm_quote')

        # Deleting model 'Invoice'
        db.delete_table('crm_invoice')

        # Deleting model 'Unit'
        db.delete_table('crm_unit')

        # Deleting model 'Tax'
        db.delete_table('crm_tax')

        # Deleting model 'Product'
        db.delete_table('crm_product')

        # Deleting model 'UnitTransform'
        db.delete_table('crm_unittransform')

        # Deleting model 'CustomerGroupTransform'
        db.delete_table('crm_customergrouptransform')

        # Deleting model 'Price'
        db.delete_table('crm_price')

        # Deleting model 'Position'
        db.delete_table('crm_position')

        # Deleting model 'SalesContractPosition'
        db.delete_table('crm_salescontractposition')

        # Deleting model 'PurchaseOrderPosition'
        db.delete_table('crm_purchaseorderposition')

        # Deleting model 'PhoneAddressForContact'
        db.delete_table('crm_phoneaddressforcontact')

        # Deleting model 'EmailAddressForContact'
        db.delete_table('crm_emailaddressforcontact')

        # Deleting model 'PostalAddressForContact'
        db.delete_table('crm_postaladdressforcontact')

        # Deleting model 'PostalAddressForContract'
        db.delete_table('crm_postaladdressforcontract')

        # Deleting model 'PostalAddressForPurchaseOrder'
        db.delete_table('crm_postaladdressforpurchaseorder')

        # Deleting model 'PostalAddressForSalesContract'
        db.delete_table('crm_postaladdressforsalescontract')

        # Deleting model 'PhoneAddressForContract'
        db.delete_table('crm_phoneaddressforcontract')

        # Deleting model 'PhoneAddressForSalesContract'
        db.delete_table('crm_phoneaddressforsalescontract')

        # Deleting model 'PhoneAddressForPurchaseOrder'
        db.delete_table('crm_phoneaddressforpurchaseorder')

        # Deleting model 'EmailAddressForContract'
        db.delete_table('crm_emailaddressforcontract')

        # Deleting model 'EmailAddressForSalesContract'
        db.delete_table('crm_emailaddressforsalescontract')

        # Deleting model 'EmailAddressForPurchaseOrder'
        db.delete_table('crm_emailaddressforpurchaseorder')


    models = {
        'accounting.account': {
            'Meta': {'ordering': "['accountNumber']", 'object_name': 'Account'},
            'accountNumber': ('django.db.models.fields.IntegerField', [], {}),
            'accountType': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isACustomerPaymentAccount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'isProductInventoryActiva': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'isopeninterestaccount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'isopenreliabilitiesaccount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'accounting.productcategorie': {
            'Meta': {'object_name': 'ProductCategorie'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lossAccount': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_loss_account'", 'to': "orm['accounting.Account']"}),
            'profitAccount': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_profit_account'", 'to': "orm['accounting.Account']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'crm.contact': {
            'Meta': {'object_name': 'Contact'},
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        },
        'crm.contract': {
            'Meta': {'object_name': 'Contract'},
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'defaultSupplier': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Supplier']", 'null': 'True', 'blank': 'True'}),
            'defaultcurrency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Currency']"}),
            'defaultcustomer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Customer']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_contractlstmodified'", 'to': "orm['auth.User']"}),
            'staff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'db_relcontractstaff'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'crm.currency': {
            'Meta': {'object_name': 'Currency'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rounding': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'shortName': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        'crm.customer': {
            'Meta': {'object_name': 'Customer', '_ormbases': ['crm.Contact']},
            'contact_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.Contact']", 'unique': 'True', 'primary_key': 'True'}),
            'defaultCustomerBillingCycle': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.CustomerBillingCycle']"}),
            'ismemberof': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['crm.CustomerGroup']", 'null': 'True', 'blank': 'True'})
        },
        'crm.customerbillingcycle': {
            'Meta': {'object_name': 'CustomerBillingCycle'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'timeToPaymentDate': ('django.db.models.fields.IntegerField', [], {})
        },
        'crm.customergroup': {
            'Meta': {'object_name': 'CustomerGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        },
        'crm.customergrouptransform': {
            'Meta': {'object_name': 'CustomerGroupTransform'},
            'factor': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'fromCustomerGroup': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltransfromfromcustomergroup'", 'to': "orm['crm.CustomerGroup']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Product']"}),
            'toCustomerGroup': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltransfromtocustomergroup'", 'to': "orm['crm.CustomerGroup']"})
        },
        'crm.emailaddress': {
            'Meta': {'object_name': 'EmailAddress'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'crm.emailaddressforcontact': {
            'Meta': {'object_name': 'EmailAddressForContact', '_ormbases': ['crm.EmailAddress']},
            'emailaddress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.EmailAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contact']"}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.emailaddressforcontract': {
            'Meta': {'object_name': 'EmailAddressForContract', '_ormbases': ['crm.EmailAddress']},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contract']"}),
            'emailaddress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.EmailAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.emailaddressforpurchaseorder': {
            'Meta': {'object_name': 'EmailAddressForPurchaseOrder', '_ormbases': ['crm.EmailAddress']},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.PurchaseOrder']"}),
            'emailaddress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.EmailAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.emailaddressforsalescontract': {
            'Meta': {'object_name': 'EmailAddressForSalesContract', '_ormbases': ['crm.EmailAddress']},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.SalesContract']"}),
            'emailaddress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.EmailAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.invoice': {
            'Meta': {'object_name': 'Invoice', '_ormbases': ['crm.SalesContract']},
            'derivatedFromQuote': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Quote']", 'null': 'True', 'blank': 'True'}),
            'payableuntil': ('django.db.models.fields.DateField', [], {}),
            'paymentBankReference': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'salescontract_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.SalesContract']", 'unique': 'True', 'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.phoneaddress': {
            'Meta': {'object_name': 'PhoneAddress'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'crm.phoneaddressforcontact': {
            'Meta': {'object_name': 'PhoneAddressForContact', '_ormbases': ['crm.PhoneAddress']},
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contact']"}),
            'phoneaddress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.PhoneAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.phoneaddressforcontract': {
            'Meta': {'object_name': 'PhoneAddressForContract', '_ormbases': ['crm.PhoneAddress']},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contract']"}),
            'phoneaddress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.PhoneAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.phoneaddressforpurchaseorder': {
            'Meta': {'object_name': 'PhoneAddressForPurchaseOrder', '_ormbases': ['crm.PhoneAddress']},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.PurchaseOrder']"}),
            'phoneaddress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.PhoneAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.phoneaddressforsalescontract': {
            'Meta': {'object_name': 'PhoneAddressForSalesContract', '_ormbases': ['crm.PhoneAddress']},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.SalesContract']"}),
            'phoneaddress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.PhoneAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.position': {
            'Meta': {'object_name': 'Position'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'discount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastCalculatedPrice': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '17', 'decimal_places': '2', 'blank': 'True'}),
            'lastCalculatedTax': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '17', 'decimal_places': '2', 'blank': 'True'}),
            'lastPricingDate': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'overwriteProductPrice': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'positionNumber': ('django.db.models.fields.IntegerField', [], {}),
            'positionPricePerUnit': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '17', 'decimal_places': '2', 'blank': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Product']", 'null': 'True', 'blank': 'True'}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '3'}),
            'sentOn': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'shipmentID': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'supplier': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Supplier']", 'null': 'True', 'blank': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Unit']", 'null': 'True', 'blank': 'True'})
        },
        'crm.postaladdress': {
            'Meta': {'object_name': 'PostalAddress'},
            'addressline1': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'addressline2': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'addressline3': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'addressline4': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'prefix': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'prename': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'town': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'zipcode': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'crm.postaladdressforcontact': {
            'Meta': {'object_name': 'PostalAddressForContact', '_ormbases': ['crm.PostalAddress']},
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contact']"}),
            'postaladdress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.PostalAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.postaladdressforcontract': {
            'Meta': {'object_name': 'PostalAddressForContract', '_ormbases': ['crm.PostalAddress']},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contract']"}),
            'postaladdress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.PostalAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.postaladdressforpurchaseorder': {
            'Meta': {'object_name': 'PostalAddressForPurchaseOrder', '_ormbases': ['crm.PostalAddress']},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.PurchaseOrder']"}),
            'postaladdress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.PostalAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.postaladdressforsalescontract': {
            'Meta': {'object_name': 'PostalAddressForSalesContract', '_ormbases': ['crm.PostalAddress']},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.SalesContract']"}),
            'postaladdress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.PostalAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'crm.price': {
            'Meta': {'object_name': 'Price'},
            'currency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Currency']"}),
            'customerGroup': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.CustomerGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '17', 'decimal_places': '2'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Product']"}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Unit']"}),
            'validfrom': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'validuntil': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'})
        },
        'crm.product': {
            'Meta': {'object_name': 'Product'},
            'accoutingProductCategorie': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['accounting.ProductCategorie']", 'null': 'True', 'blank': "'True'"}),
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'defaultunit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Unit']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': "'True'"}),
            'productNumber': ('django.db.models.fields.IntegerField', [], {}),
            'tax': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Tax']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'crm.purchaseorder': {
            'Meta': {'object_name': 'PurchaseOrder'},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contract']"}),
            'currency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Currency']"}),
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'externalReference': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastCalculatedPrice': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '17', 'decimal_places': '2', 'blank': 'True'}),
            'lastCalculatedTax': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '17', 'decimal_places': '2', 'blank': 'True'}),
            'lastPricingDate': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_polstmodified'", 'to': "orm['auth.User']"}),
            'staff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'db_relpostaff'", 'null': 'True', 'to': "orm['auth.User']"}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'supplier': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Supplier']"})
        },
        'crm.purchaseorderposition': {
            'Meta': {'object_name': 'PurchaseOrderPosition', '_ormbases': ['crm.Position']},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.PurchaseOrder']"}),
            'position_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.Position']", 'unique': 'True', 'primary_key': 'True'})
        },
        'crm.quote': {
            'Meta': {'object_name': 'Quote', '_ormbases': ['crm.SalesContract']},
            'salescontract_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.SalesContract']", 'unique': 'True', 'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'validuntil': ('django.db.models.fields.DateField', [], {})
        },
        'crm.salescontract': {
            'Meta': {'object_name': 'SalesContract'},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contract']"}),
            'currency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Currency']"}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Customer']"}),
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'discount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'externalReference': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastCalculatedPrice': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '17', 'decimal_places': '2', 'blank': 'True'}),
            'lastCalculatedTax': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '17', 'decimal_places': '2', 'blank': 'True'}),
            'lastPricingDate': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'blank': "'True'", 'related_name': "'db_lstscmodified'", 'null': 'True', 'to': "orm['auth.User']"}),
            'staff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'db_relscstaff'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'crm.salescontractposition': {
            'Meta': {'object_name': 'SalesContractPosition', '_ormbases': ['crm.Position']},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.SalesContract']"}),
            'position_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.Position']", 'unique': 'True', 'primary_key': 'True'})
        },
        'crm.supplier': {
            'Meta': {'object_name': 'Supplier', '_ormbases': ['crm.Contact']},
            'contact_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.Contact']", 'unique': 'True', 'primary_key': 'True'}),
            'offersShipmentToCustomers': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'crm.tax': {
            'Meta': {'object_name': 'Tax'},
            'accountActiva': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'db_relaccountactiva'", 'null': 'True', 'to': "orm['accounting.Account']"}),
            'accountPassiva': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'db_relaccountpassiva'", 'null': 'True', 'to': "orm['accounting.Account']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'taxrate': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'})
        },
        'crm.unit': {
            'Meta': {'object_name': 'Unit'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'fractionFactorToNextHigherUnit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isAFractionOf': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Unit']", 'null': 'True', 'blank': 'True'}),
            'shortName': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        'crm.unittransform': {
            'Meta': {'object_name': 'UnitTransform'},
            'factor': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'fromUnit': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltransfromfromunit'", 'to': "orm['crm.Unit']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Product']"}),
            'toUnit': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltransfromtounit'", 'to': "orm['crm.Unit']"})
        }
    }

    complete_apps = ['crm']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

from django.db import models
from const.country import *
from const.postaladdressprefix import *
from const.purpose import *
from const.status import *
from datetime import *
from django.utils.translation import ugettext as _
from decimal import Decimal
from django.core import serializers
from exceptions import TemplateSetMissing
from exceptions import UserExtensionMissing
import djangoUserExtension
from django.contrib import auth
from lxml import etree
import accounting 
import settings
import copy
from subprocess import *

class Currency (models.Model):
  description = models.CharField(verbose_name = _("Description"), max_length=100)
  shortName = models.CharField(verbose_name = _("Displayed Name After Price In The Position"), max_length=3)
  rounding = models.DecimalField(max_digits=5, decimal_places=2, verbose_name = _("Rounding"), blank=True, null=True)

  def __unicode__(self):
    return  self.shortName
  
  class Meta:
    app_label = "crm"
    verbose_name = _('Currency')
    verbose_name_plural = _('Currency') 
   
class PostalAddress(models.Model):
   prefix = models.CharField(max_length=1, choices=POSTALADDRESSPREFIX, verbose_name = _("Prefix"), blank=True, null=True)
   name = models.CharField(max_length=100, verbose_name = _("Name"), blank=True, null=True)
   prename = models.CharField(max_length=100, verbose_name = _("Prename"), blank=True, null=True)
   addressline1 = models.CharField(max_length=200, verbose_name = _("Addressline 1"), blank=True, null=True)
   addressline2 = models.CharField(max_length=200, verbose_name = _("Addressline 2"), blank=True, null=True)
   addressline3 = models.CharField(max_length=200, verbose_name = _("Addressline 3"), blank=True, null=True)
   addressline4 = models.CharField(max_length=200, verbose_name = _("Addressline 4"), blank=True, null=True)
   zipcode = models.IntegerField(verbose_name = _("Zipcode"), blank=True, null=True)
   town = models.CharField(max_length=100, verbose_name = _("City"), blank=True, null=True)
   state = models.CharField(max_length=100, verbose_name = _("State"), blank=True, null=True)
   country = models.CharField(max_length=2, choices=[(x[0], x[3]) for x in COUNTRIES], verbose_name = _("Country"), blank=True, null=True)

   class Meta:
      app_label = "crm"
      verbose_name = _('Postal Address')
      verbose_name_plural = _('Postal Address')

class PhoneAddress(models.Model):
   phone = models.CharField(max_length=20, verbose_name = _("Phone Number"))

   class Meta:
      app_label = "crm"
      verbose_name = _('Phone Address')
      verbose_name_plural = _('Phone Address')

class EmailAddress(models.Model):
   email = models.EmailField(max_length=200, verbose_name = _("Email Address"))

   class Meta:
      app_label = "crm"
      verbose_name = _('Email Address')
      verbose_name_plural = _('Email Address')

class Contact(models.Model):
   name = models.CharField(max_length=300, verbose_name = _("Name"))
   dateofcreation = models.DateTimeField(verbose_name = _("Created at"), auto_now=True)
   lastmodification = models.DateTimeField(verbose_name = _("Last modified"), auto_now_add=True)
   lastmodifiedby = models.ForeignKey('auth.User', limit_choices_to={'is_staff': True}, blank=True, verbose_name = _("Last modified by"), editable=True)

   class Meta:
      app_label = "crm"
      verbose_name = _('Contact')
      verbose_name_plural = _('Contact')

class CustomerBillingCycle(models.Model):
   name = models.CharField(max_length=300, verbose_name = _("Name"))
   timeToPaymentDate = models.IntegerField(verbose_name = _("Days To Payment Date"))
   class Meta:
      app_label = "crm"
      verbose_name = _('Customer Billing Cycle')
      verbose_name_plural = _('Customer Billing Cycle')

   def __unicode__(self):
      return str(self.id) + ' ' + self.name

class CustomerGroup(models.Model):
   name = models.CharField(max_length=300)
      
   def __unicode__(self):
      return str(self.id) + ' ' + self.name
      
   class Meta:
      app_label = "crm"
      verbose_name = _('Customer Group')
      verbose_name_plural = _('Customer Groups')

class Customer(Contact):
   defaultCustomerBillingCycle = models.ForeignKey('CustomerBillingCycle', verbose_name= _('Default Billing Cycle'))
   ismemberof = models.ManyToManyField(CustomerGroup, verbose_name = _('Is member of'), blank=True, null=True)
   
   def createContract(self, request):
      contract = Contract()
      contract.defaultcustomer = self
      contract.defaultcurrency = djangoUserExtension.models.UserExtension.objects.filter(user=request.user.id)[0].defaultCurrency
      contract.lastmodifiedby = request.user
      contract.staff = request.user
      contract.save()
      return contract
   
   def createInvoice(self):
      contract = self.createContract()
      invoice = contract.createInvoice()
      return invoice
      
   def createQuote(self):
      contract = self.createContract()
      quote = contract.createQuote()
      return quote

   def isInGroup(self, customerGroup):
      for customerGroupMembership in self.ismemberof.all():
         if (customerGroupMembership.id == customerGroup.id):
            return 1
      return 0
   
   class Meta:
      app_label = "crm"
      verbose_name = _('Customer')
      verbose_name_plural = _('Customers')

   def __unicode__(self):
      return str(self.id) + ' ' + self.name

class Supplier(Contact):
   offersShipmentToCustomers = models.BooleanField(verbose_name=_("Offers Shipment to Customer"))
   class Meta:
      app_label = "crm"
      verbose_name = _('Supplier')
      verbose_name_plural = _('Supplier')

   def __unicode__(self):
      return str(self.id) + ' ' + self.name

class Contract(models.Model):
   staff = models.ForeignKey('auth.User', limit_choices_to={'is_staff': True}, blank=True, verbose_name = _("Staff"), related_name="db_relcontractstaff", null=True)
   description = models.TextField(verbose_name = _("Description"))
   defaultcustomer = models.ForeignKey(Customer, verbose_name = _("Default Customer"), null=True, blank=True)
   defaultSupplier = models.ForeignKey(Supplier, verbose_name = _("Default Supplier"), null=True, blank=True)
   defaultcurrency = models.ForeignKey(Currency, verbose_name=_("Default Currency"), blank=False, null=False)
   dateofcreation = models.DateTimeField(verbose_name = _("Created at"), auto_now=True)
   lastmodification = models.DateTimeField(verbose_name = _("Last modified"), auto_now_add=True)
   lastmodifiedby = models.ForeignKey('auth.User', limit_choices_to={'is_staff': True}, verbose_name = _("Last modified by"), related_name="db_contractlstmodified")

   class Meta:
      app_label = "crm"
      verbose_name = _('Contract')
      verbose_name_plural = _('Contracts')
      
   def createInvoice(self):
      invoice = Invoice()
      invoice.contract = self
      invoice.discount = 0
      invoice.staff = self.staff
      invoice.customer = self.defaultcustomer
      invoice.status = 'C'
      invoice.currency = self.defaultcurrency
      invoice.payableuntil = date.today()+timedelta(days=self.defaultcustomer.defaultCustomerBillingCycle.timeToPaymentDate)
      invoice.dateofcreation = date.today().__str__()
      invoice.save()
      return invoice
      
   def createQuote(self):
      quote = Quote()
      quote.contract = self
      quote.discount = 0
      quote.staff = self.staff
      quote.customer = self.defaultcustomer
      quote.status = 'C'
      quote.currency = self.defaultcurrency
      quote.validuntil = date.today().__str__()
      quote.dateofcreation = date.today().__str__()
      quote.save()
      return quote
      
   def createPurchaseOrder(self):
      purchaseorder = PurchaseOrder()
      purchaseorder.contract = self
      purchaseorder.description = self.description
      purchaseorder.discount = 0
      purchaseorder.currency = self.defaultcurrency
      purchaseorder.supplier = self.defaultSupplier
      purchaseorder.status = 'C'
      purchaseorder.dateofcreation = date.today().__str__()
# TODO: today is not correct it has to be replaced
      purchaseorder.save()
      return purchaseorder

   def __unicode__(self):
      return _("Contract") + " " + str(self.id)

class PurchaseOrder(models.Model):
  contract = models.ForeignKey(Contract, verbose_name = _("Contract"))
  externalReference = models.CharField(verbose_name = _("External Reference"), max_length=100, blank=True, null=True)
  supplier = models.ForeignKey(Supplier, verbose_name = _("Supplier"))
  description = models.CharField(verbose_name=_("Description"), max_length=100, blank=True, null=True)
  lastPricingDate = models.DateField(verbose_name = _("Last Pricing Date"), blank=True, null=True)
  lastCalculatedPrice = models.DecimalField(max_digits=17, decimal_places=2, verbose_name=_("Last Calculted Price With Tax"), blank=True, null=True)
  lastCalculatedTax = models.DecimalField(max_digits=17, decimal_places=2, verbose_name=_("Last Calculted Tax"), blank=True, null=True)
  status = models.CharField(max_length=1, choices=PURCHASEORDERSTATUS)
  staff = models.ForeignKey('auth.User', limit_choices_to={'is_staff': True}, blank=True, verbose_name = _("Staff"), related_name="db_relpostaff", null=True)
  currency = models.ForeignKey(Currency, verbose_name=_("Currency"), blank=False, null=False)
  dateofcreation = models.DateTimeField(verbose_name = _("Created at"), auto_now=True)
  lastmodification = models.DateTimeField(verbose_name = _("Last modified"), auto_now_add=True)
  lastmodifiedby = models.ForeignKey('auth.User', limit_choices_to={'is_staff': True}, verbose_name = _("Last modified by"), related_name="db_polstmodified")
   
  def recalculatePrices(self, pricingDate):
    price = 0
    tax = 0
    try:
        positions = PurchaseOrderPosition.objects.filter(contract=self.id)
        if type(positions) == PurchaseOrderPosition:
          if type(self.discount) == Decimal:
              price = int(positions.recalculatePrices(pricingDate, self.customer, self.currency)*(1-self.discount/100)/self.currency.rounding)*self.currency.rounding
              tax = int(positions.recalculateTax(self.currency)*(1-self.discount/100)/self.currency.rounding)*self.currency.rounding
          else:
              price = positions.recalculatePrices(pricingDate, self.customer, self.currency)
              tax = positions.recalculateTax(self.currency)
        else:
          for position in positions:
              if type(self.discount) == Decimal:
                price += int(position.recalculatePrices(pricingDate, self.customer, self.currency)*(1-self.discount/100)/self.currency.rounding)*self.currency.rounding
                tax += int(position.recalculateTax(self.currency)*(1-self.discount/100)/self.currency.rounding)*self.currency.rounding
              else:
                price += position.recalculatePrices(pricingDate, self.customer, self.currency)
                tax += position.recalculateTax(self.currency)
        self.lastCalculatedPrice = price
        self.lastCalculatedTax = tax
        self.lastPricingDate = pricingDate
        self.save()
        return 1
    except Quote.DoesNotExist, e:  
        print "ERROR "+e.__str__()
        print "Der Fehler trat beim File: "+ self.sourcefile +" / Cell: "+listOfLines[0][listOfLines[0].find("cell ")+4:listOfLines[0].find("(cellType ")-1]+" auf!"
        exit()
        return 0
         
  def createPDF(self, whatToExport):
    XMLSerializer = serializers.get_serializer("xml")
    xml_serializer = XMLSerializer()
    out = open(settings.PDF_OUTPUT_ROOT+"purchaseorder_"+str(self.id)+".xml", "w")
    objectsToSerialize = list(PurchaseOrder.objects.filter(id=self.id)) 
    objectsToSerialize += list(Contact.objects.filter(id=self.supplier.id))
    objectsToSerialize += list(Currency.objects.filter(id=self.currency.id))
    objectsToSerialize += list(PurchaseOrderPosition.objects.filter(contract=self.id))
    for position in list(PurchaseOrderPosition.objects.filter(contract=self.id)):
      objectsToSerialize += list(Position.objects.filter(id=position.id))
      objectsToSerialize += list(Product.objects.filter(id=position.product.id))
      objectsToSerialize += list(Unit.objects.filter(id=position.unit.id))
    objectsToSerialize += list(auth.models.User.objects.filter(id=self.staff.id))
    userExtension = djangoUserExtension.models.UserExtension.objects.filter(user=self.staff.id)
    if (len(userExtension) == 0):
      raise UserExtensionMissing(_("During PurchaseOrder PDF Export"))
    phoneAddress = djangoUserExtension.models.UserExtensionPhoneAddress.objects.filter(userExtension=userExtension[0].id)
    objectsToSerialize += list(userExtension)
    objectsToSerialize += list(phoneAddress)
    templateset = djangoUserExtension.models.TemplateSet.objects.filter(id=userExtension[0].defaultTemplateSet.id)
    if (len(templateset) == 0):
      raise TemplateSetMissing(_("During PurchaseOrder PDF Export"))
    objectsToSerialize += list(templateset)
    objectsToSerialize += list(auth.models.User.objects.filter(id=self.lastmodifiedby.id))
    objectsToSerialize += list(PostalAddressForContact.objects.filter(person=self.supplier.id))
    for address in list(PostalAddressForContact.objects.filter(person=self.supplier.id)):
        objectsToSerialize += list(PostalAddress.objects.filter(id=address.id))
    xml_serializer.serialize(objectsToSerialize, stream=out, indent=3)
    out.close()
    check_output(['/usr/bin/fop', '-c', userExtension[0].defaultTemplateSet.fopConfigurationFile.path, '-xml', settings.PDF_OUTPUT_ROOT+'purchaseorder_'+str(self.id)+'.xml', '-xsl', userExtension[0].defaultTemplateSet.purchaseorderXSLFile.xslfile.path, '-pdf', settings.PDF_OUTPUT_ROOT+'purchaseorder_'+str(self.id)+'.pdf'], stderr=STDOUT)
    return settings.PDF_OUTPUT_ROOT+"purchaseorder_"+str(self.id)+".pdf"   

  class Meta:
    app_label = "crm"
    verbose_name = _('Purchase Order')
    verbose_name_plural = _('Purchase Order')

  def __unicode__(self):
    return _("Purchase Order")+ ": " + str(self.id) + " "+ _("from Contract") + ": " + str(self.contract.id) 

class SalesContract(models.Model):
   contract = models.ForeignKey(Contract, verbose_name=_('Contract'))
   externalReference = models.CharField(verbose_name = _("External Reference"), max_length=100, blank=True)
   discount = models.DecimalField(max_digits=5, decimal_places=2, verbose_name = _("Discount"), blank=True, null=True)
   description = models.CharField(verbose_name=_("Description"), max_length=100, blank=True, null=True)
   lastPricingDate = models.DateField(verbose_name = _("Last Pricing Date"), blank=True, null=True)
   lastCalculatedPrice = models.DecimalField(max_digits=17, decimal_places=2, verbose_name=_("Last Calculted Price With Tax"), blank=True, null=True)
   lastCalculatedTax = models.DecimalField(max_digits=17, decimal_places=2, verbose_name=_("Last Calculted Tax"), blank=True, null=True)
   customer = models.ForeignKey(Customer, verbose_name = _("Customer"))
   staff = models.ForeignKey('auth.User', limit_choices_to={'is_staff': True}, blank=True, verbose_name = _("Staff"), related_name="db_relscstaff", null=True)
   currency = models.ForeignKey(Currency, verbose_name=_("Currency"), blank=False, null=False)
   dateofcreation = models.DateTimeField(verbose_name = _("Created at"), auto_now=True)
   lastmodification = models.DateTimeField(verbose_name = _("Last modified"), auto_now_add=True)
   lastmodifiedby = models.ForeignKey('auth.User', limit_choices_to={'is_staff': True}, verbose_name = _("Last modified by"), related_name="db_lstscmodified", null=True, blank="True")
      
   def recalculatePrices(self, pricingDate):
      price = 0
      tax = 0
      try:
         positions = SalesContractPosition.objects.filter(contract=self.id)
         if type(positions) == SalesContractPosition:
            if type(self.discount) == Decimal:
               price = int(positions.recalculatePrices(pricingDate, self.customer, selof.currency)*(1-self.discount/100)/self.currency.rounding)*self.currency.rounding
               tax = int(positions.recalculateTax(self.currency)*(1-self.discount/100)/self.currency.rounding)*self.currency.rounding
            else:
               price = positions.recalculatePrices(pricingDate, self.customer, self.currency)
               tax = positions.recalculateTax(self.currency)
         else:
            for position in positions:
               price += position.recalculatePrices(pricingDate, self.customer, self.currency)
               tax += position.recalculateTax(self.currency)
            if type(self.discount) == Decimal:
               price = int(price*(1-self.discount/100)/self.currency.rounding)*self.currency.rounding
               tax = int(tax*(1-self.discount/100)/self.currency.rounding)*self.currency.rounding

         self.lastCalculatedPrice = price
         self.lastCalculatedTax = tax
         self.lastPricingDate = pricingDate
         self.save()
         return 1
      except Quote.DoesNotExist:  
         return 0

   class Meta:
      app_label = "crm"
      verbose_name = _('Sales Contract')
      verbose_name_plural = _('Sales Contracts')

   def __unicode__(self):
      return _("Sales Contract")+ ": " + str(self.id) + " "+_("from Contract")+": " + str(self.contract.id) 
      
class Quote(SalesContract):
   validuntil = models.DateField(verbose_name = _("Valid until"))
   status = models.CharField(max_length=1, choices=QUOTESTATUS, verbose_name=_('Status'))

   def createInvoice(self):
      invoice = Invoice()
      invoice.contract = self.contract
      invoice.description = self.description
      invoice.discount = self.discount
      invoice.customer = self.customer
      invoice.staff = self.staff
      invoice.status = 'C'
      invoice.derivatedFromQuote = self
      invoice.currency = self.currency
      invoice.payableuntil = date.today()+timedelta(days=self.customer.defaultCustomerBillingCycle.timeToPaymentDate)
      invoice.dateofcreation = date.today().__str__()
      invoice.customerBillingCycle = self.customer.defaultCustomerBillingCycle
      invoice.save()
      try:
         quotePositions = SalesContractPosition.objects.filter(contract=self.id)
         for quotePosition in list(quotePositions):
            invoicePosition = SalesContractPosition()
            invoicePosition.product = quotePosition.product 
            invoicePosition.positionNumber = quotePosition.positionNumber 
            invoicePosition.quantity = quotePosition.quantity 
            invoicePosition.description = quotePosition.description 
            invoicePosition.discount = quotePosition.discount 
            invoicePosition.product = quotePosition.product 
            invoicePosition.unit = quotePosition.unit 
            invoicePosition.sentOn = quotePosition.sentOn 
            invoicePosition.supplier = quotePosition.supplier 
            invoicePosition.shipmentID = quotePosition.shipmentID 
            invoicePosition.overwriteProductPrice = quotePosition.overwriteProductPrice 
            invoicePosition.positionPricePerUnit = quotePosition.positionPricePerUnit 
            invoicePosition.lastPricingDate = quotePosition.lastPricingDate 
            invoicePosition.lastCalculatedPrice = quotePosition.lastCalculatedPrice 
            invoicePosition.lastCalculatedTax = quotePosition.lastCalculatedTax 
            invoicePosition.contract = invoice 
            invoicePosition.save()
         return invoice
      except Quote.DoesNotExist:  
         return

   def createPDF(self, whatToExport):
     XMLSerializer = serializers.get_serializer("xml")
     xml_serializer = XMLSerializer()
     out = open(settings.PDF_OUTPUT_ROOT+"quote_"+str(self.id)+".xml", "w")
     objectsToSerialize = list(Quote.objects.filter(id=self.id)) 
     objectsToSerialize += list(SalesContract.objects.filter(id=self.id)) 
     objectsToSerialize += list(Contact.objects.filter(id=self.customer.id))
     objectsToSerialize += list(Currency.objects.filter(id=self.currency.id))
     objectsToSerialize += list(SalesContractPosition.objects.filter(contract=self.id))
     for position in list(SalesContractPosition.objects.filter(contract=self.id)):
         objectsToSerialize += list(Position.objects.filter(id=position.id))
         objectsToSerialize += list(Product.objects.filter(id=position.product.id))
         objectsToSerialize += list(Unit.objects.filter(id=position.unit.id))
     objectsToSerialize += list(auth.models.User.objects.filter(id=self.staff.id))
     userExtension = djangoUserExtension.models.UserExtension.objects.filter(user=self.staff.id)
     if (len(userExtension) == 0):
      raise UserExtensionMissing(_("During Quote PDF Export"))
     phoneAddress = djangoUserExtension.models.UserExtensionPhoneAddress.objects.filter(userExtension=userExtension[0].id)
     objectsToSerialize += list(userExtension)
     objectsToSerialize += list(PhoneAddress.objects.filter(id=phoneAddress[0].id))
     templateset = djangoUserExtension.models.TemplateSet.objects.filter(id=userExtension[0].defaultTemplateSet.id)
     if (len(templateset) == 0):
      raise TemplateSetMissing(_("During Quote PDF Export"))
     objectsToSerialize += list(templateset)
     objectsToSerialize += list(auth.models.User.objects.filter(id=self.lastmodifiedby.id))
     objectsToSerialize += list(PostalAddressForContact.objects.filter(person=self.customer.id))
     for address in list(PostalAddressForContact.objects.filter(person=self.customer.id)):
         objectsToSerialize += list(PostalAddress.objects.filter(id=address.id))
     xml_serializer.serialize(objectsToSerialize, stream=out, indent=3)
     out.close()
     xml = etree.parse(settings.PDF_OUTPUT_ROOT+"quote_"+str(self.id)+".xml")
     rootelement = xml.getroot()
     projectroot = etree.SubElement(rootelement, "projectroot")
     projectroot.text = settings.PROJECT_ROOT
     xml.write(settings.PDF_OUTPUT_ROOT+"quote_"+str(self.id)+".xml")
     if (whatToExport == "quote"):
        check_output(['/usr/bin/fop', '-c', userExtension[0].defaultTemplateSet.fopConfigurationFile.path, '-xml', settings.PDF_OUTPUT_ROOT+'quote_'+str(self.id)+'.xml', '-xsl', userExtension[0].defaultTemplateSet.quoteXSLFile.xslfile.path, '-pdf', settings.PDF_OUTPUT_ROOT+'quote_'+str(self.id)+'.pdf'], stderr=STDOUT)
        return settings.PDF_OUTPUT_ROOT+"quote_"+str(self.id)+".pdf"
     else:
        check_output(['/usr/bin/fop', '-c', userExtension[0].defaultTemplateSet.fopConfigurationFile.path, '-xml', settings.PDF_OUTPUT_ROOT+'quote_'+str(self.id)+'.xml', '-xsl', userExtension[0].defaultTemplateSet.purchaseconfirmationXSLFile.xslfile.path, '-pdf', settings.PDF_OUTPUT_ROOT+'purchaseconfirmation_'+str(self.id)+'.pdf'], stderr=STDOUT)
        return settings.PDF_OUTPUT_ROOT+"purchaseconfirmation_"+str(self.id)+".pdf"  
     
   def __unicode__(self):
      return _("Quote")+ ": " + str(self.id) + " "+_("from Contract")+": " + str(self.contract.id) 
      
   class Meta:
      app_label = "crm"
      verbose_name = _('Quote')
      verbose_name_plural = _('Quotes')

class Invoice(SalesContract):
   payableuntil = models.DateField(verbose_name = _("To pay until"))
   derivatedFromQuote = models.ForeignKey(Quote, blank=True, null=True)
   paymentBankReference = models.CharField(verbose_name = _("Payment Bank Reference"), max_length=100, blank=True, null=True)
   status = models.CharField(max_length=1, choices=INVOICESTATUS) 
   
   def registerinvoiceinaccounting(self, request):
      dictprices = dict()
      dicttax = dict()
      exists = False
      currentValidAccountingPeriod = accounting.models.AccountingPeriod.getCurrentValidAccountingPeriod()
      activaaccount = accounting.models.Account.objects.filter(isopeninterestaccount=True)
      for position in list(SalesContractPosition.objects.filter(contract=self.id)):
        profitaccount = position.product.accoutingProductCategorie.profitAccount
        dictprices[profitaccount] = position.lastCalculatedPrice
        dicttax[profitaccount] = position.lastCalculatedTax
         
      for booking in accounting.models.Booking.objects.filter(accountingPeriod=currentValidAccountingPeriod):
        if booking.bookingReference == self:
          raise InvoiceAlreadyRegistered()
        for profitaccount, amount in dictprices.iteritems():
          booking = accounting.models.Booking()
          booking.toAccount = activaaccount[0]
          booking.fromAccount = profitaccount
          booking.bookingReference = self
          booking.accountingPeriod = currentValidAccountingPeriod
          booking.bookingDate = date.today().__str__()
          booking.staff = request.user
          booking.amount = amount
          booking.lastmodifiedby = request.user
          booking.save()
      
   def registerpaymentinaccounting(self, request, paymentaccount, amount, date):
      activaaccount = accounting.Account.objects.filter(isopeninterestaccount=True)
      booking = accounting.Booking()
      booking.toAccount = activaaccount
      booking.fromAccount = paymentaccount
      booking.bookingDate = date.today().__str__()
      booking.bookingReference = self
      booking.accountingPeriod = accounting.models.AccountingPeriod.objects.all()[0]
      booking.amount = self.lastCalculatedPrice
      booking.staff = request.user
      booking.lastmodifiedby = request.user
      booking.save()

   def createPDF(self, whatToExport):
     XMLSerializer = serializers.get_serializer("xml")
     xml_serializer = XMLSerializer()
     out = open(settings.PDF_OUTPUT_ROOT+"invoice_"+str(self.id)+".xml", "w")
     objectsToSerialize = list(Invoice.objects.filter(id=self.id)) 
     objectsToSerialize += list(SalesContract.objects.filter(id=self.id)) 
     objectsToSerialize += list(Contact.objects.filter(id=self.customer.id))
     objectsToSerialize += list(Currency.objects.filter(id=self.currency.id))
     objectsToSerialize += list(SalesContractPosition.objects.filter(contract=self.id))
     for position in list(SalesContractPosition.objects.filter(contract=self.id)):
         objectsToSerialize += list(Position.objects.filter(id=position.id))
         objectsToSerialize += list(Product.objects.filter(id=position.product.id))
         objectsToSerialize += list(Unit.objects.filter(id=position.unit.id))
     objectsToSerialize += list(auth.models.User.objects.filter(id=self.staff.id))
     userExtension = djangoUserExtension.models.UserExtension.objects.filter(user=self.staff.id)
     if (len(userExtension) == 0):
      raise UserExtensionMissing(_("During Invoice PDF Export"))
     phoneAddress = djangoUserExtension.models.UserExtensionPhoneAddress.objects.filter(userExtension=userExtension[0].id)
     objectsToSerialize += list(userExtension)
     objectsToSerialize += list(PhoneAddress.objects.filter(id=phoneAddress[0].id))
     templateset = djangoUserExtension.models.TemplateSet.objects.filter(id=userExtension[0].defaultTemplateSet.id)
     if (len(templateset) == 0):
      raise TemplateSetMissing(_("During Invoice PDF Export"))
     objectsToSerialize += list(templateset)
     objectsToSerialize += list(auth.models.User.objects.filter(id=self.lastmodifiedby.id))
     objectsToSerialize += list(PostalAddressForContact.objects.filter(person=self.customer.id))
     for address in list(PostalAddressForContact.objects.filter(person=self.customer.id)):
         objectsToSerialize += list(PostalAddress.objects.filter(id=address.id))
     xml_serializer.serialize(objectsToSerialize, stream=out, indent=3)
     out.close()
     xml = etree.parse(settings.PDF_OUTPUT_ROOT+"invoice_"+str(self.id)+".xml")
     rootelement = xml.getroot()
     projectroot = etree.SubElement(rootelement, "projectroot")
     projectroot.text = settings.PROJECT_ROOT
     xml.write(settings.PDF_OUTPUT_ROOT+"invoice_"+str(self.id)+".xml")
     if (whatToExport == "invoice"):
        check_output(['/usr/bin/fop', '-c', userExtension[0].defaultTemplateSet.fopConfigurationFile.path, '-xml', settings.PDF_OUTPUT_ROOT+'invoice_'+str(self.id)+'.xml', '-xsl', userExtension[0].defaultTemplateSet.invoiceXSLFile.xslfile.path, '-pdf', settings.PDF_OUTPUT_ROOT+'invoice_'+str(self.id)+'.pdf'], stderr=STDOUT)
        return settings.PDF_OUTPUT_ROOT+"invoice_"+str(self.id)+".pdf"
     else:
        check_output(['/usr/bin/fop', '-c', userExtension[0].defaultTemplateSet.fopConfigurationFile.path, '-xml', settings.PDF_OUTPUT_ROOT+'invoice_'+str(self.id)+'.xml', '-xsl', userExtension[0].defaultTemplateSet.deilveryorderXSLFile.xslfile.path, '-pdf', settings.PDF_OUTPUT_ROOT+'deliveryorder_'+str(self.id)+'.pdf'], stderr=STDOUT)
        return settings.PDF_OUTPUT_ROOT+"deliveryorder_"+str(self.id)+".pdf"  

#  TODO: def registerPayment(self, amount, registerpaymentinaccounting):
   def __unicode__(self):
      return _("Invoice")+ ": " + str(self.id) + " "+_("from Contract")+": " + str(self.contract.id) 
      
   class Meta:
      app_label = "crm"
      verbose_name = _('Invoice')
      verbose_name_plural = _('Invoices') 
   
class Unit(models.Model):
   description = models.CharField(verbose_name = _("Description"), max_length=100)
   shortName = models.CharField(verbose_name = _("Displayed Name After Quantity In The Position"), max_length=3)
   isAFractionOf = models.ForeignKey('self', blank=True, null=True, verbose_name = _("Is A Fraction Of"))
   fractionFactorToNextHigherUnit = models.IntegerField(verbose_name = _("Factor Between This And Next Higher Unit"), blank=True, null=True)

   def __unicode__(self):
      return  self.shortName

   class Meta:
      app_label = "crm"
      verbose_name = _('Unit')
      verbose_name_plural = _('Units') 

class Tax(models.Model):
   taxrate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name = _("Taxrate in Percentage"))
   name = models.CharField(verbose_name = _("Taxname"), max_length=100)
   accountActiva = models.ForeignKey('accounting.Account', verbose_name=_("Activa Account"), related_name="db_relaccountactiva", null=True, blank=True)
   accountPassiva = models.ForeignKey('accounting.Account', verbose_name=_("Passiva Account"), related_name="db_relaccountpassiva", null=True, blank=True)

   def getTaxRate(self):
      return self.taxrate;

   def __unicode__(self):
      return  self.name

   class Meta:
      app_label = "crm"
      verbose_name = _('Tax')
      verbose_name_plural = _('Taxes') 
      
	
class Product(models.Model):
   description = models.TextField(verbose_name = _("Description"),null=True, blank=True) 
   title = models.CharField(verbose_name = _("Title"), max_length=200)
   productNumber = models.IntegerField(verbose_name = _("Product Number"))
   defaultunit = models.ForeignKey(Unit, verbose_name = _("Unit"))
   dateofcreation = models.DateTimeField(verbose_name = _("Created at"), auto_now=True)
   lastmodification = models.DateTimeField(verbose_name = _("Last modified"), auto_now_add=True)
   lastmodifiedby = models.ForeignKey('auth.User', limit_choices_to={'is_staff': True}, verbose_name = _("Last modified by"), null=True, blank="True")
   tax = models.ForeignKey(Tax, blank=False)
   accoutingProductCategorie = models.ForeignKey('accounting.ProductCategorie', verbose_name=_("Accounting Product Categorie"), null=True, blank="True")

   def getPrice(self, date, unit, customer, currency):
      prices = Price.objects.filter(product=self.id)
      unitTransforms = UnitTransform.objects.filter(product=self.id)
      customerGroupTransforms = CustomerGroupTransform.objects.filter(product=self.id)
      validpriceslist = list()
      for price in list(prices):
         for customerGroup in CustomerGroup.objects.filter(customer=customer):
            if price.matchesDateUnitCustomerGroupCurrency(date, unit, customerGroup, currency):
               validpriceslist.append(price.price);
            else:
               for customerGroupTransform in customerGroupTransforms:
                  if price.matchesDateUnitCustomerGroupCurrency(date, unit, customerGroupTransfrom.transform(customerGroup), currency):
                     validpriceslist.append(price.price*customerGroup.factor);
                  else:
                     for unitTransfrom in list(unitTransforms):
                        if price.matchesDateUnitCustomerGroupCurrency(date, unitTransfrom.transfrom(unit).transform(unitTransfrom), customerGroupTransfrom.transform(customerGroup), currency):
                           validpriceslist.append(price.price*customerGroupTransform.factor*unitTransform.factor);
      if (len(validpriceslist) >0):
         lowestprice = validpriceslist[0]
         for price in validpriceslist:
            if (price < lowestprice):
               lowestprice = price
         return lowestprice
      else:           
         raise Product.NoPriceFound(customer, unit, date, self)

   def getTaxRate(self):
      return self.tax.getTaxRate();

   def __unicode__(self):
      return str(self.productNumber) + ' ' + self.title

   class Meta:
      app_label = "crm"
      verbose_name = _('Product')
      verbose_name_plural = _('Products')
      
   class NoPriceFound(Exception):
     def __init__(self, customer, unit, date, product):
       self.customer = customer
       self.unit = unit
       self.date = date
       self.product = product
       return 
     def __str__ (self):
       return _("There is no Price for this product")+": "+ self.product.__unicode__() + _("that matches the date")+": "+self.date.__str__() +" ,"+ _("customer")+ ": " +self.customer.__unicode__()+_(" and unit")+":"+ self.unit.__unicode__()

      
class UnitTransform(models.Model):
   fromUnit = models.ForeignKey('Unit', verbose_name = _("From Unit"), related_name="db_reltransfromfromunit")
   toUnit = models.ForeignKey('Unit', verbose_name = _("To Unit"), related_name="db_reltransfromtounit")
   product = models.ForeignKey('Product', verbose_name = _("Product"))
   factor = models.IntegerField(verbose_name = _("Factor between From and To Unit"), blank=True, null=True)

   def transform(self, unit):
      if (self.fromUnit == unit):
         return self.toUnit
      else:
         return unit
         
   def __unicode__(self):
      return  "From " + self.fromUnit.shortName + " to " + self.toUnit.shortName

   class Meta:
      app_label = "crm"
      verbose_name = _('Unit Transfrom')
      verbose_name_plural = _('Unit Transfroms') 
           
class CustomerGroupTransform(models.Model):
   fromCustomerGroup = models.ForeignKey('CustomerGroup', verbose_name = _("From Unit"), related_name="db_reltransfromfromcustomergroup")
   toCustomerGroup = models.ForeignKey('CustomerGroup', verbose_name = _("To Unit"), related_name="db_reltransfromtocustomergroup")
   product = models.ForeignKey('Product', verbose_name = _("Product"))
   factor = models.IntegerField(verbose_name = _("Factor between From and To Customer Group"), blank=True, null=True)

   def transform(self, customerGroup):
      if (self.fromCustomerGroup == customerGroup):
         return self.toCustomerGroup
      else:
         return unit
         
   def __unicode__(self):
      return  "From " + self.fromCustomerGroup.name + " to " + self.toCustomerGroup.name

   class Meta:
      app_label = "crm"
      verbose_name = _('Customer Group Price Transfrom')
      verbose_name_plural = _('Customer Group Price Transfroms') 
           
class Price(models.Model):
   product = models.ForeignKey(Product, verbose_name = _("Product"))
   unit = models.ForeignKey(Unit, blank=False, verbose_name= _("Unit"))
   currency = models.ForeignKey(Currency, blank=False, null=False, verbose_name=('Currency'))
   customerGroup = models.ForeignKey(CustomerGroup, blank=True, null=True, verbose_name = _("Customer Group"))
   price = models.DecimalField(max_digits=17, decimal_places=2, verbose_name = _("Price Per Unit"))
   validfrom = models.DateField(verbose_name = _("Valid from"), blank=True, null=True)
   validuntil = models.DateField(verbose_name = _("Valid until"), blank=True, null=True)

   def matchesDateUnitCustomerGroupCurrency(self, date, unit, customerGroup, currency):
      if self.validfrom == None:
        if self.validuntil == None:
          if self.customerGroup == None:
            if (unit == self.unit) & (self.currency == currency):
              return 1
          else:
            if (unit == self.unit) & (self.customerGroup == customerGroup) & (self.currency == currency): 
              return 1
        elif self.customerGroup == None:
          if ((date - self.validuntil).days < 0) & (unit == self.unit) & (self.currency == currency):
            return 1
        else:
          if ((date - self.validuntil).days < 0) & (unit == self.unit) & (self.customerGroup == customerGroup) & (self.currency == currency):
            return 1
      elif self.validuntil == None:
        if self.customerGroup == None:
          if ((self.validfrom - date).days < 0) & (unit == self.unit) & (self.currency == currency):
            return 1
        else:
          if ((self.validfrom - date).days < 0) & (unit == self.unit) & (self.customerGroup == customerGroup) & (self.currency == currency):
            return 1
      elif self.customerGroup == None:
        if ((self.validfrom - date).days < 0) & (self.validuntil== None) & (unit == self.unit) & (self.customerGroup == None) & (self.currency == currency):
          return 1
      else:
        if ((self.validfrom - date).days < 0) & ((date - self.validuntil).days < 0) & (unit == self.unit) & (self.customerGroup == customerGroup) & (self.currency == currency):
          return 1

   class Meta:
      app_label = "crm"
      verbose_name = _('Price')
      verbose_name_plural = _('Prices')

class Position(models.Model):
   positionNumber = models.IntegerField(verbose_name = _("Position Number"))
   quantity = models.DecimalField(verbose_name = _("Quantity"), decimal_places=3, max_digits=10)
   description = models.TextField(verbose_name = _("Description"), blank=True, null=True)
   discount = models.DecimalField(max_digits=5, decimal_places=2, verbose_name = _("Discount"), blank=True, null=True)
   product = models.ForeignKey(Product, verbose_name = _("Product"), blank=True, null=True)
   unit = models.ForeignKey(Unit, verbose_name = _("Unit"), blank=True, null=True)
   sentOn = models.DateField(verbose_name = _("Shipment on"), blank=True, null=True)
   supplier = models.ForeignKey(Supplier, verbose_name = _("Shipment Supplier"), limit_choices_to = {'offersShipmentToCustomers': True}, blank=True, null=True)
   shipmentID = models.CharField(max_length=100, verbose_name = _("Shipment ID"), blank=True, null=True)
   overwriteProductPrice = models.BooleanField(verbose_name=_('Overwrite Product Price'))
   positionPricePerUnit = models.DecimalField(verbose_name=_("Price Per Unit"), max_digits=17, decimal_places=2, blank=True, null=True)
   lastPricingDate = models.DateField(verbose_name = _("Last Pricing Date"), blank=True, null=True)
   lastCalculatedPrice = models.DecimalField(max_digits=17, decimal_places=2, verbose_name=_("Last Calculted Price"), blank=True, null=True)
   lastCalculatedTax = models.DecimalField(max_digits=17, decimal_places=2, verbose_name=_("Last Calculted Tax"), blank=True, null=True)

   def recalculatePrices(self, pricingDate, customer, currency):
     if self.overwriteProductPrice == False:
       self.positionPricePerUnit = self.product.getPrice(pricingDate, self.unit, customer, currency)
     if type(self.discount) == Decimal:
       self.lastCalculatedPrice = int(self.positionPricePerUnit*self.quantity*(1-self.discount/100)/currency.rounding)*currency.rounding
     else:
       self.lastCalculatedPrice = self.positionPricePerUnit*self.quantity
     self.lastPricingDate = pricingDate
     self.save()
     return self.lastCalculatedPrice
     
   def recalculateTax(self, currency):
     if type(self.discount) == Decimal:
       self.lastCalculatedTax = int(self.product.getTaxRate()/100*self.positionPricePerUnit*self.quantity*(1-self.discount/100)/currency.rounding)*currency.rounding
     else:
       self.lastCalculatedTax = self.product.getTaxRate()/100*self.positionPricePerUnit*self.quantity
     self.save()
     return self.lastCalculatedTax
     
   def __unicode__(self):
      return _("Position")+ ": " + str(self.id)

   class Meta:
      app_label = "crm"
      verbose_name = _('Position')
      verbose_name_plural = _('Positions')

class SalesContractPosition(Position):
   contract = models.ForeignKey(SalesContract, verbose_name = _("Contract"))
   
   class Meta:
      app_label = "crm"
      verbose_name = _('Salescontract Position')
      verbose_name_plural = _('Salescontract Positions')
      
   def __unicode__(self):
      return _("Salescontract Position")+ ": " + str(self.id)


class PurchaseOrderPosition(Position):
   contract = models.ForeignKey(PurchaseOrder, verbose_name = _("Contract"))
   
   class Meta:
      app_label = "crm"
      verbose_name = _('Purchaseorder Position')
      verbose_name_plural = _('Purchaseorder Positions')
      
   def __unicode__(self):
      return _("Purchaseorder Position")+ ": " + str(self.id)

class PhoneAddressForContact(PhoneAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINCUSTOMER)
   person = models.ForeignKey(Contact)

   class Meta:
      app_label = "crm"
      verbose_name = _('Phone Address For Contact')
      verbose_name_plural = _('Phone Address For Contact')

   def __unicode__(self):
      return str(self.phone)

class EmailAddressForContact(EmailAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINCUSTOMER)
   person = models.ForeignKey(Contact)

   class Meta:
      app_label = "crm"
      verbose_name = _('Email Address For Contact')
      verbose_name_plural = _('Email Address For Contact')

   def __unicode__(self):
      return str(self.email)

class PostalAddressForContact(PostalAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINCUSTOMER)
   person = models.ForeignKey(Contact)

   class Meta:
      app_label = "crm"
      verbose_name = _('Postal Address For Contact')
      verbose_name_plural = _('Postal Address For Contact')

   def __unicode__(self):
      return self.prename + ' ' + self.name + ' ' + self.addressline1
   
class PostalAddressForContract(PostalAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINCONTRACT)
   contract = models.ForeignKey(Contract)

   class Meta:
      app_label = "crm"
      verbose_name = _('Postal Address For Contracts')
      verbose_name_plural = _('Postal Address For Contracts')

   def __unicode__(self):
      return self.prename + ' ' + self.name + ' ' + self.addressline1
   
class PostalAddressForPurchaseOrder(PostalAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINCONTRACT)
   contract = models.ForeignKey(PurchaseOrder)

   class Meta:
      app_label = "crm"
      verbose_name = _('Postal Address For Contracts')
      verbose_name_plural = _('Postal Address For Contracts')

   def __unicode__(self):
      return self.prename + ' ' + self.name + ' ' + self.addressline1
   
class PostalAddressForSalesContract(PostalAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINCONTRACT)
   contract = models.ForeignKey(SalesContract)

   class Meta:
      app_label = "crm"
      verbose_name = _('Postal Address For Contracts')
      verbose_name_plural = _('Postal Address For Contracts')

   def __unicode__(self):
      return self.prename + ' ' + self.name + ' ' + self.addressline1

class PhoneAddressForContract(PhoneAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINCONTRACT)
   contract = models.ForeignKey(Contract)

   class Meta:
      app_label = "crm"
      verbose_name = _('Phone Address For Contracts')
      verbose_name_plural = _('Phone Address For Contracts')

   def __unicode__(self):
      return str(self.phone)

class PhoneAddressForSalesContract(PhoneAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINCONTRACT)
   contract = models.ForeignKey(SalesContract)

   class Meta:
      app_label = "crm"
      verbose_name = _('Phone Address For Contracts')
      verbose_name_plural = _('Phone Address For Contracts')

   def __unicode__(self):
      return str(self.phone)

class PhoneAddressForPurchaseOrder(PhoneAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINCONTRACT)
   contract = models.ForeignKey(PurchaseOrder)

   class Meta:
      app_label = "crm"
      verbose_name = _('Phone Address For Contracts')
      verbose_name_plural = _('Phone Address For Contracts')

   def __unicode__(self):
      return str(self.phone)

class EmailAddressForContract(EmailAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINCONTRACT) 
   contract = models.ForeignKey(Contract)

   class Meta:
      app_label = "crm"
      verbose_name = _('Email Address For Contracts')
      verbose_name_plural = _('Email Address For Contracts')

   def __unicode__(self):
      return str(self.email)

class EmailAddressForSalesContract(EmailAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINCONTRACT) 
   contract = models.ForeignKey(SalesContract)

   class Meta:
      app_label = "crm"
      verbose_name = _('Email Address For Contracts')
      verbose_name_plural = _('Email Address For Contracts')

   def __unicode__(self):
      return str(self.email)

class EmailAddressForPurchaseOrder(EmailAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINCONTRACT) 
   contract = models.ForeignKey(PurchaseOrder)

   class Meta:
      app_label = "crm"
      verbose_name = _('Email Address For Contracts')
      verbose_name_plural = _('Email Address For Contracts')

   def __unicode__(self):
      return str(self.email)
    

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from os import path
from django.http import Http404
from crm.models import *
from django.http import HttpResponse
from exceptions import TemplateSetMissing
from exceptions import UserExtensionMissing
from django.core.servers.basehttp import FileWrapper
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
from subprocess import *

def exportPDF(callingModelAdmin, request, whereToCreateFrom, whatToCreate, redirectTo):
  """This method exports PDFs provided by different Models in the crm application

      Args:
        callingModelAdmin (ModelAdmin):  The calling ModelAdmin must be provided for error message response.
        request: The request User is to know where to save the error message
        whereToCreateFrom (Model):  The model from which a PDF should be exported
        whatToCreate (str): What document Type that has to be
        redirectTo (str): String that describes to where the method sould redirect in case of an error

      Returns:
            HTTpResponse with a PDF when successful
            HTTpResponseRedirect when not successful
            
      Raises:
        raises Http404 exception if anything goes wrong"""
  try:
    pdf = whereToCreateFrom.createPDF(whatToCreate)
    response = HttpResponse(FileWrapper(file(pdf)), mimetype='application/pdf')
    response['Content-Length'] = path.getsize(pdf) 
  except (TemplateSetMissing, UserExtensionMissing, CalledProcessError), e:
    if type(e) == UserExtensionMissing:
      response = HttpResponseRedirect(redirectTo)
      callingModelAdmin.message_user(request, _("User Extension Missing"))
    elif type(e) == TemplateSetMissing:
      response = HttpResponseRedirect(redirectTo)
      callingModelAdmin.message_user(request, _("Templateset Missing"))
    elif type(e) ==CalledProcessError:
      response = HttpResponseRedirect(redirectTo)
      callingModelAdmin.message_user(request, e.output)
    else:
      raise Http404
  return response 
   
def selectaddress(invoiceid):
  invoice = Invoice.objects.get(id=invoiceid)
  address = invoice.contract
  

  
   
########NEW FILE########
__FILENAME__ = dashboard
"""
This file was generated with the customdashboard management command and
contains the class for the main dashboard.

To activate your index dashboard add the following to your settings.py::
    GRAPPELLI_INDEX_DASHBOARD = 'koalixcrm.dashboard.CustomIndexDashboard'
"""

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from grappelli.dashboard import modules, Dashboard
from grappelli.dashboard.utils import get_admin_site_name


class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard for koalixcrm
    """
    
    def init_with_context(self, context):
        site_name = get_admin_site_name(context)
        
        # append a group for "Administration" & "Applications"
        self.children.append(modules.Group(
            _('Group: Administration & Applications'),
            column=1,
            collapsible=False,
            children = [
                modules.AppList(
                    _('Administration'),
                    column=1,
                    collapsible=True,
                    css_classes=('collapse closed',),
                    models=('django.contrib.*',),
                ),
                modules.AppList(
                    _('Applications'),
                    column=1,
                    collapsible=False,
                    exclude=('django.contrib.*',),
                )
            ]
        ))
        
       
        # append an app list module for "Administration"
        self.children.append(modules.ModelList(
            _('ModelList: Administration'),
            column=1,
            collapsible=False,
            models=('django.contrib.*',),
        ))
        
        # append another link list module for "support".
        self.children.append(modules.LinkList(
            _('Media Management'),
            column=2,
            children=[
                {
                    'title': _('FileBrowser'),
                    'url': '/admin/filebrowser/browse/',
                    'external': False,
                },
            ]
        ))
        
        # append another link list module for "support".
        self.children.append(modules.LinkList(
            _('Support'),
            column=2,
            children=[
                {
                    'title': _('koalixcrm documentation'),
                    'url': 'http://docs.koalix.org/',
                    'external': True,
                },
                {
                    'title': _('koalixcrm "koalixcrm-user" mailing list'),
                    'url': 'http://groups.google.com/group/koalixcrm-users',
                    'external': True,
                },
            ]
        ))
        
        # append a feed module
        self.children.append(modules.Feed(
            title=_('Latest koalixcrm News'),
            column=2,
            feed_url='http://www.koalix.org/projects/koalixcrm/news.atom',
            limit=5
        ))
        
        # append a recent actions module
        self.children.append(modules.RecentActions(
            _('Recent Actions'),
            limit=5,
            collapsible=False,
            column=3,
        ))


########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.contrib import admin
from djangoUserExtension.models import *

class InlineUserExtensionPostalAddress(admin.StackedInline):
   model = UserExtensionPostalAddress
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      (_('Basics'), {
         'fields': ('prefix', 'prename', 'name', 'addressline1', 'addressline2', 'addressline3', 'addressline4', 'zipcode', 'town', 'state', 'country', 'purpose')
      }),
   )
   allow_add = True
   
class InlineUserExtensionPhoneAddress(admin.StackedInline):
   model = UserExtensionPhoneAddress
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      (_('Basics'), {
         'fields': ('phone', 'purpose',)
      }),
   )
   allow_add = True
   
class InlineUserExtensionEmailAddress(admin.StackedInline):
   model = UserExtensionEmailAddress
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      (_('Basics'), {
         'fields': ('email', 'purpose',)
      }),
   )
   allow_add = True
   
class OptionUserExtension(admin.ModelAdmin):
   list_display = ('id', 'user', 'defaultTemplateSet', 'defaultCurrency')
   list_display_links = ('id', 'user')       
   list_filter    = ('user', 'defaultTemplateSet',)
   ordering       = ('id', )
   search_fields  = ('id','user')
   fieldsets = (
      (_('Basics'), {
         'fields': ('user', 'defaultTemplateSet', 'defaultCurrency')
      }),
   )
   save_as = True
   inlines = [InlineUserExtensionPostalAddress, InlineUserExtensionPhoneAddress, InlineUserExtensionEmailAddress]
   
class OptionTemplateSet(admin.ModelAdmin):
   list_display = ('id', 'title')
   list_display_links = ('id', 'title')
   ordering       = ('id',)
   search_fields  = ('id', 'title', 'organisationname', 'invoiceXSLFile', 'quoteXSLFile', 'purchaseconfirmationXSLFile',
   'deilveryorderXSLFile', 'profitLossStatementXSLFile', 'balancesheetXSLFile', 'purchaseorderXSLFile',
   'logo', 'footerTextsalesorders', 'headerTextsalesorders', 
   'headerTextpurchaseorders', 'footerTextpurchaseorders', 'pagefooterleft', 'pagefootermiddle', 'bankingaccountref', 'addresser'
   )
   fieldsets = (
      (_('Basics'), {
         'fields': ('title', 'organisationname', 'invoiceXSLFile', 'quoteXSLFile', 'purchaseconfirmationXSLFile',
   'deilveryorderXSLFile', 'profitLossStatementXSLFile', 'balancesheetXSLFile', 'purchaseorderXSLFile', 
   'logo', 'fopConfigurationFile', 'footerTextsalesorders', 'headerTextsalesorders', 
   'headerTextpurchaseorders', 'footerTextpurchaseorders', 'pagefooterleft', 'pagefootermiddle', 'bankingaccountref', 'addresser')
      }),
   )
   
class OptionXSLFile(admin.ModelAdmin):
   list_display = ('id', 'title')
   list_display_links = ('id', 'title')
   ordering       = ('id',)
   fieldsets = (
      (_('Basics'), {
         'fields': ('title', 'xslfile',)
      }),
   )
   allow_add = True
   
   

admin.site.register(UserExtension, OptionUserExtension)
admin.site.register(TemplateSet, OptionTemplateSet)
admin.site.register(XSLFile, OptionXSLFile)
########NEW FILE########
__FILENAME__ = purpose
# -*- coding: utf-8 -*

from django.utils.translation import ugettext as _

PURPOSESADDRESSINUSEREXTENTION = (
    ('H', _('Private')),
    ('O', _('Business')),
    ('P', _('Mobile Private')),
    ('B', _('Mobile Business')),
)
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'XSLFile'
        db.create_table('djangoUserExtension_xslfile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('xslfile', self.gf('filebrowser.fields.FileBrowseField')(max_length=200)),
        ))
        db.send_create_signal('djangoUserExtension', ['XSLFile'])

        # Adding model 'UserExtension'
        db.create_table('djangoUserExtension_userextension', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('defaultTemplateSet', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djangoUserExtension.TemplateSet'])),
            ('defaultCurrency', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Currency'])),
        ))
        db.send_create_signal('djangoUserExtension', ['UserExtension'])

        # Adding model 'TemplateSet'
        db.create_table('djangoUserExtension_templateset', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('organisationname', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('invoiceXSLFile', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_reltemplateinvoice', to=orm['djangoUserExtension.XSLFile'])),
            ('quoteXSLFile', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_reltemplatequote', to=orm['djangoUserExtension.XSLFile'])),
            ('purchaseconfirmationXSLFile', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_reltemplatepurchaseorder', to=orm['djangoUserExtension.XSLFile'])),
            ('deilveryorderXSLFile', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_reltemplatedeliveryorder', to=orm['djangoUserExtension.XSLFile'])),
            ('profitLossStatementXSLFile', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_reltemplateprofitlossstatement', to=orm['djangoUserExtension.XSLFile'])),
            ('balancesheetXSLFile', self.gf('django.db.models.fields.related.ForeignKey')(related_name='db_reltemplatebalancesheet', to=orm['djangoUserExtension.XSLFile'])),
            ('logo', self.gf('filebrowser.fields.FileBrowseField')(max_length=200, null=True, blank=True)),
            ('bankingaccountref', self.gf('django.db.models.fields.CharField')(max_length=60, null=True, blank=True)),
            ('addresser', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('fopConfigurationFile', self.gf('filebrowser.fields.FileBrowseField')(max_length=200, null=True, blank=True)),
            ('footerTextsalesorders', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('headerTextsalesorders', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('headerTextpurchaseorders', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('footerTextpurchaseorders', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('pagefooterleft', self.gf('django.db.models.fields.CharField')(max_length=40, null=True, blank=True)),
            ('pagefootermiddle', self.gf('django.db.models.fields.CharField')(max_length=40, null=True, blank=True)),
        ))
        db.send_create_signal('djangoUserExtension', ['TemplateSet'])

        # Adding model 'UserExtensionPostalAddress'
        db.create_table('djangoUserExtension_userextensionpostaladdress', (
            ('postaladdress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.PostalAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('userExtension', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djangoUserExtension.UserExtension'])),
        ))
        db.send_create_signal('djangoUserExtension', ['UserExtensionPostalAddress'])

        # Adding model 'UserExtensionPhoneAddress'
        db.create_table('djangoUserExtension_userextensionphoneaddress', (
            ('phoneaddress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.PhoneAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('userExtension', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djangoUserExtension.UserExtension'])),
        ))
        db.send_create_signal('djangoUserExtension', ['UserExtensionPhoneAddress'])

        # Adding model 'UserExtensionEmailAddress'
        db.create_table('djangoUserExtension_userextensionemailaddress', (
            ('emailaddress_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.EmailAddress'], unique=True, primary_key=True)),
            ('purpose', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('userExtension', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djangoUserExtension.UserExtension'])),
        ))
        db.send_create_signal('djangoUserExtension', ['UserExtensionEmailAddress'])


    def backwards(self, orm):
        # Deleting model 'XSLFile'
        db.delete_table('djangoUserExtension_xslfile')

        # Deleting model 'UserExtension'
        db.delete_table('djangoUserExtension_userextension')

        # Deleting model 'TemplateSet'
        db.delete_table('djangoUserExtension_templateset')

        # Deleting model 'UserExtensionPostalAddress'
        db.delete_table('djangoUserExtension_userextensionpostaladdress')

        # Deleting model 'UserExtensionPhoneAddress'
        db.delete_table('djangoUserExtension_userextensionphoneaddress')

        # Deleting model 'UserExtensionEmailAddress'
        db.delete_table('djangoUserExtension_userextensionemailaddress')


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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'crm.currency': {
            'Meta': {'object_name': 'Currency'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rounding': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'shortName': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        'crm.emailaddress': {
            'Meta': {'object_name': 'EmailAddress'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'crm.phoneaddress': {
            'Meta': {'object_name': 'PhoneAddress'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'crm.postaladdress': {
            'Meta': {'object_name': 'PostalAddress'},
            'addressline1': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'addressline2': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'addressline3': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'addressline4': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'prefix': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'prename': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'town': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'zipcode': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'djangoUserExtension.templateset': {
            'Meta': {'object_name': 'TemplateSet'},
            'addresser': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'balancesheetXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplatebalancesheet'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'bankingaccountref': ('django.db.models.fields.CharField', [], {'max_length': '60', 'null': 'True', 'blank': 'True'}),
            'deilveryorderXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplatedeliveryorder'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'footerTextpurchaseorders': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'footerTextsalesorders': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'fopConfigurationFile': ('filebrowser.fields.FileBrowseField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'headerTextpurchaseorders': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'headerTextsalesorders': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoiceXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplateinvoice'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'logo': ('filebrowser.fields.FileBrowseField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'organisationname': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pagefooterleft': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'pagefootermiddle': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'profitLossStatementXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplateprofitlossstatement'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'purchaseconfirmationXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplatepurchaseorder'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'quoteXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplatequote'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'djangoUserExtension.userextension': {
            'Meta': {'object_name': 'UserExtension'},
            'defaultCurrency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Currency']"}),
            'defaultTemplateSet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangoUserExtension.TemplateSet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djangoUserExtension.userextensionemailaddress': {
            'Meta': {'object_name': 'UserExtensionEmailAddress', '_ormbases': ['crm.EmailAddress']},
            'emailaddress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.EmailAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'userExtension': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangoUserExtension.UserExtension']"})
        },
        'djangoUserExtension.userextensionphoneaddress': {
            'Meta': {'object_name': 'UserExtensionPhoneAddress', '_ormbases': ['crm.PhoneAddress']},
            'phoneaddress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.PhoneAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'userExtension': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangoUserExtension.UserExtension']"})
        },
        'djangoUserExtension.userextensionpostaladdress': {
            'Meta': {'object_name': 'UserExtensionPostalAddress', '_ormbases': ['crm.PostalAddress']},
            'postaladdress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.PostalAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'userExtension': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangoUserExtension.UserExtension']"})
        },
        'djangoUserExtension.xslfile': {
            'Meta': {'object_name': 'XSLFile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'xslfile': ('filebrowser.fields.FileBrowseField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['djangoUserExtension']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_templateset_purchaseorderXSLFile
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'TemplateSet.purchaseorderXSLFile'
        db.add_column('djangoUserExtension_templateset', 'purchaseorderXSLFile',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, related_name='db_reltemplatepurchaseorder', to=orm['djangoUserExtension.XSLFile']),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'TemplateSet.purchaseorderXSLFile'
        db.delete_column('djangoUserExtension_templateset', 'purchaseorderXSLFile_id')


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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'crm.currency': {
            'Meta': {'object_name': 'Currency'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rounding': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'shortName': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        'crm.emailaddress': {
            'Meta': {'object_name': 'EmailAddress'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'crm.phoneaddress': {
            'Meta': {'object_name': 'PhoneAddress'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'crm.postaladdress': {
            'Meta': {'object_name': 'PostalAddress'},
            'addressline1': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'addressline2': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'addressline3': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'addressline4': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'prefix': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'prename': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'town': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'zipcode': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'djangoUserExtension.templateset': {
            'Meta': {'object_name': 'TemplateSet'},
            'addresser': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'balancesheetXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplatebalancesheet'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'bankingaccountref': ('django.db.models.fields.CharField', [], {'max_length': '60', 'null': 'True', 'blank': 'True'}),
            'deilveryorderXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplatedeliveryorder'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'footerTextpurchaseorders': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'footerTextsalesorders': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'fopConfigurationFile': ('filebrowser.fields.FileBrowseField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'headerTextpurchaseorders': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'headerTextsalesorders': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoiceXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplateinvoice'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'logo': ('filebrowser.fields.FileBrowseField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'organisationname': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pagefooterleft': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'pagefootermiddle': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'profitLossStatementXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplateprofitlossstatement'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'purchaseconfirmationXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplatepurchaseconfirmation'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'purchaseorderXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplatepurchaseorder'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'quoteXSLFile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_reltemplatequote'", 'to': "orm['djangoUserExtension.XSLFile']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'djangoUserExtension.userextension': {
            'Meta': {'object_name': 'UserExtension'},
            'defaultCurrency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Currency']"}),
            'defaultTemplateSet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangoUserExtension.TemplateSet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djangoUserExtension.userextensionemailaddress': {
            'Meta': {'object_name': 'UserExtensionEmailAddress', '_ormbases': ['crm.EmailAddress']},
            'emailaddress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.EmailAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'userExtension': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangoUserExtension.UserExtension']"})
        },
        'djangoUserExtension.userextensionphoneaddress': {
            'Meta': {'object_name': 'UserExtensionPhoneAddress', '_ormbases': ['crm.PhoneAddress']},
            'phoneaddress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.PhoneAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'userExtension': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangoUserExtension.UserExtension']"})
        },
        'djangoUserExtension.userextensionpostaladdress': {
            'Meta': {'object_name': 'UserExtensionPostalAddress', '_ormbases': ['crm.PostalAddress']},
            'postaladdress_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.PostalAddress']", 'unique': 'True', 'primary_key': 'True'}),
            'purpose': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'userExtension': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangoUserExtension.UserExtension']"})
        },
        'djangoUserExtension.xslfile': {
            'Meta': {'object_name': 'XSLFile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'xslfile': ('filebrowser.fields.FileBrowseField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['djangoUserExtension']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.db import models
from filebrowser.fields import FileBrowseField
from const.purpose import *
from crm import models as crmmodels
   
class XSLFile(models.Model):
   title = models.CharField(verbose_name = _("Title"), max_length=100, blank=True, null=True)
   xslfile = FileBrowseField(verbose_name=_("XSL File"), max_length=200)
   
   class Meta:
      app_label = "djangoUserExtension"
      #app_label_koalix = _('Djang User Extention')
      verbose_name = _('XSL File')
      verbose_name_plural = _('XSL Files')
      
   def __unicode__(self):
      return str(self.id) + ' ' + self.title
      
class UserExtension(models.Model):
   user = models.ForeignKey('auth.User')
   defaultTemplateSet = models.ForeignKey('TemplateSet')
   defaultCurrency = models.ForeignKey('crm.Currency')
   
   class Meta:
      app_label = "djangoUserExtension"
      #app_label_koalix = _('Djang User Extention')
      verbose_name = _('User Extention')
      verbose_name_plural = _('User Extentions')
      
   def __unicode__(self):
      return str(self.id) + ' ' + self.user.__unicode__()
      
class TemplateSet(models.Model):
   organisationname = models.CharField(verbose_name = _("Name of the Organisation"), max_length=200)
   title = models.CharField(verbose_name = _("Title"), max_length=100)
   invoiceXSLFile = models.ForeignKey(XSLFile, verbose_name=_("XSL File for Invoice"), related_name="db_reltemplateinvoice")
   quoteXSLFile = models.ForeignKey(XSLFile, verbose_name=_("XSL File for Quote"), related_name="db_reltemplatequote")
   purchaseorderXSLFile = models.ForeignKey(XSLFile, verbose_name=_("XSL File for Purchaseorder"), related_name="db_reltemplatepurchaseorder")
   purchaseconfirmationXSLFile = models.ForeignKey(XSLFile, verbose_name=_("XSL File for Purchase Confirmation"), related_name="db_reltemplatepurchaseconfirmation")
   deilveryorderXSLFile = models.ForeignKey(XSLFile, verbose_name=_("XSL File for Deilvery Order"), related_name="db_reltemplatedeliveryorder")
   profitLossStatementXSLFile = models.ForeignKey(XSLFile, verbose_name=_("XSL File for Profit Loss Statement"), related_name="db_reltemplateprofitlossstatement")
   balancesheetXSLFile = models.ForeignKey(XSLFile, verbose_name=_("XSL File for Balancesheet"), related_name="db_reltemplatebalancesheet")
   logo = FileBrowseField(verbose_name=_("Logo for the PDF generation"), blank=True, null=True, max_length=200)
   bankingaccountref = models.CharField(max_length=60, verbose_name=_("Reference to Banking Account"), blank=True, null=True)
   addresser = models.CharField(max_length=200, verbose_name=_("Addresser"), blank=True, null=True)
   fopConfigurationFile = FileBrowseField(verbose_name=_("FOP Configuration File"), blank=True, null=True, max_length=200)
   footerTextsalesorders = models.TextField(verbose_name=_("Footer Text On Salesorders"), blank=True, null=True)
   headerTextsalesorders = models.TextField(verbose_name=_("Header Text On Salesorders"), blank=True, null=True)
   headerTextpurchaseorders = models.TextField(verbose_name=_("Header Text On Purchaseorders"), blank=True, null=True)
   footerTextpurchaseorders = models.TextField(verbose_name=_("Footer Text On Purchaseorders"), blank=True, null=True)
   pagefooterleft = models.CharField(max_length=40, verbose_name=_("Page Footer Left"), blank=True, null=True)
   pagefootermiddle = models.CharField(max_length=40, verbose_name=_("Page Footer Middle"), blank=True, null=True)
      
   class Meta:
      app_label = "djangoUserExtension"
      #app_label_koalix = _('Djang User Extention')
      verbose_name = _('Templateset')
      verbose_name_plural = _('Templatesets')
      
   def __unicode__(self):
      return str(self.id) + ' ' + self.title
   

class UserExtensionPostalAddress(crmmodels.PostalAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINUSEREXTENTION)
   userExtension = models.ForeignKey(UserExtension)
   
   def __unicode__(self):
      return self.name + ' ' + self.prename
   
   class Meta:
      app_label = "djangoUserExtension"
      #app_label_koalix = _('Djang User Extention')
      verbose_name = _('Postal Address for User Extention')
      verbose_name_plural = _('Postal Address for User Extention')
   
class UserExtensionPhoneAddress(crmmodels.PhoneAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINUSEREXTENTION)
   userExtension = models.ForeignKey(UserExtension)
   
   def __unicode__(self):
      return self.phone
   
   class Meta:
      app_label = "djangoUserExtension"
      #app_label_koalix = _('Djang User Extention')
      verbose_name = _('Phonenumber for User Extention')
      verbose_name_plural = _('Phonenumber for User Extention')

class UserExtensionEmailAddress(crmmodels.EmailAddress):
   purpose = models.CharField(verbose_name=_("Purpose"), max_length=1, choices=PURPOSESADDRESSINUSEREXTENTION)
   userExtension = models.ForeignKey(UserExtension)
   
   def __unicode__(self):
      return self.email
   
   class Meta:
      app_label = "djangoUserExtension"
      #app_label_koalix = _('Djang User Extention')
      verbose_name = _('Email Address for User Extention')
      verbose_name_plural = _('Email Address for User Extention')

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# koalixcrm documentation build configuration file, created by
# sphinx-quickstart on Mon Jan 10 23:22:04 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'koalixcrm'
copyright = u'2011, Aaron Riedener'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = 'Alpha'
# The full version, including alpha/beta/rc tags.
release = '1.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = []

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
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
html_static_path = ['.static']

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'koalixcrmdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'koalixcrm.tex', u'koalixcrm Documentation',
   u'Aaron Riedener', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/python
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
__FILENAME__ = plugin
# -*- coding: utf-8 -*-
import os
import sys
from settings import *

class PluginProcessor(object):
  def converttorelativestring(self, pluginmodule, nameofinline):
    output = []
    if len(nameofinline) != 0:
      output.append(pluginmodule.__name__ + "." + nameofinline[0])
      return output
    else:
      return []
  
  def getAllPlugins(self):
    allpluginmodules = []
    for plugin in KOALIXCRM_PLUGINS:
      temp = __import__(plugin+".admin")
      allpluginmodules.append(sys.modules[plugin+".admin"]);
    return allpluginmodules
    
  def getPluginAdditions(self, additionname):
    listofAdditions = []
    allpluginmodules = self.getAllPlugins()
    for pluginmodule in allpluginmodules:
      try:
        listofAdditions.extend(getattr(pluginmodule.KoalixcrmPluginInterface, additionname))
      except AttributeError:
        continue
    return listofAdditions
    
  def resolve_name(self,name, package, level):
    """Return the absolute name of the module to be imported."""
    if not hasattr(package, 'rindex'):
        raise ValueError("'package' not set to a string")
    dot = len(package)
    for x in xrange(level, 1, -1):
        try:
            dot = package.rindex('.', 0, dot)
        except ValueError:
            raise ValueError("attempted relative import beyond top-level "
                              "package")
    return "%s.%s" % (package[:dot], name)

  def import_module(self, name, package=None):
    """Import a module.

    The 'package' argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    """
    if name.startswith('.'):
      if not package:
	raise TypeError("relative imports require the 'package' argument")
      level = 0
      for character in name:
	if character != '.':
	  break
	level += 1
      name = resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]

  def load_plugins(self):
    for plugin_name in settings.KOALIXCRM_PLUGINS:
	if plugin_name :
	    continue
	self.load_app(app_name, True)
    if name.startswith('.'):
      if not package:
	raise TypeError("relative imports require the 'package' argument")
      level = 0
      for character in name:
	if character != '.':
	  break
	level += 1
      name = resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]
########NEW FILE########
__FILENAME__ = settings.default
# -*- coding: utf-8 -*-
# Django settings for koalixcrm project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'koalixcrm',                      # Or path to database file if using sqlite3.
        'USER': 'koalixcrm',                      # Not used with sqlite3.
        'PASSWORD': 'koalix5crm1234',                  # Not used with sqlite3.
        'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

TIME_ZONE = 'Europe/Zurich'

LANGUAGE_CODE = 'en'

LANGUAGES = (
  ('de', 'German'),
  ('en', 'English'),
)
LOCALE_PATHS = ('crm/locale', 'accounting/locale', 'subscriptions/locale', 'djangoUserExtension/locale')

SITE_ID = 1
USE_I18N = True
USE_L10N = True
MEDIA_ROOT = '/var/www/koalixcrm/media/'
PROJECT_ROOT = '/var/www/koalixcrm/'
MEDIA_URL = '/media/'
PDF_OUTPUT_ROOT = '/var/www/koalixcrm/media/pdf/'

STATIC_ROOT = '/var/www/koalixcrm//static/'

STATIC_URL = '/static/'

ADMIN_MEDIA_PREFIX = STATIC_URL + "grappelli/"
LOGIN_REDIRECT_URL = '/admin/'

SECRET_KEY = '+d37i!a)&736a^mxykah*l#68)^$4(6ikgbx%4(+1$l98(ktv*'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.request',
    'django.core.context_processors.i18n',
    'django.contrib.messages.context_processors.messages',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

GRAPPELLI_INDEX_DASHBOARD = 'dashboard.CustomIndexDashboard'

TEMPLATE_DIRS = (
    '/var/www/koalixcrm/templates'
)

KOALIXCRM_PLUGINS = (
    'subscriptions',
)

INSTALLED_APPS = (
    'grappelli.dashboard',
    'grappelli',
    'filebrowser',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounting',
    'djangoUserExtension',
    'crm',
    'subscriptions',
    'django.contrib.admin',
    'south'
)

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
import os
from django import forms
from django.core.urlresolvers import reverse
from datetime import date
from crm import models as crmmodels
from django.utils.translation import ugettext as _
from django.contrib import admin
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.core.servers.basehttp import FileWrapper
from subscriptions.models import *
 

class AdminSubscriptionEvent(admin.TabularInline):
   model = SubscriptionEvent
   extra = 1
   classes = ('collapse-open',)
   fieldsets = (
      ('Basics', {
         'fields': ('eventdate', 'event',)
      }),
   )
   allow_add = True

class InlineSubscription(admin.TabularInline):
   model = Subscription
   extra = 1
   classes = ('collapse-open',)
   readonly_fields = ('contract', 'subscriptiontype')
   fieldsets = (
      (_('Basics'), {
         'fields': ( 'contract', 'subscriptiontype'  )
      }),
   )
   allow_add = False
   
class OptionSubscription(admin.ModelAdmin):
   list_display = ('id', 'contract', 'subscriptiontype' , )  
   ordering       = ('id', 'contract', 'subscriptiontype')
   search_fields  = ('id', 'contract', )
   fieldsets = (
      (_('Basics'), {
         'fields': ('contract', 'subscriptiontype' ,  )
      }),
   )
   inlines = [AdminSubscriptionEvent]
   
   def createInvoice(self, request, queryset):
      for obj in queryset:
         invoice = obj.createInvoice()
         response = HttpResponseRedirect('/admin/crm/invoice/'+str(invoice.id))
      return response
      
   def createQuote(self, request, queryset):
      for obj in queryset:
         invoice = obj.createInvoice()
         response = HttpResponseRedirect('/admin/crm/invoice/'+str(invoice.id))
      return response
      
   def save_model(self, request, obj, form, change):
     if (change == True):
       obj.lastmodifiedby = request.user
     else:
       obj.lastmodifiedby = request.user
       obj.staff = request.user
     obj.save()
   createInvoice.short_description = _("Create Invoice")

   actions = ['createSubscriptionPDF', 'createInvoice']

class OptionSubscriptionType(admin.ModelAdmin):
   list_display = ('id', 'title','defaultunit', 'tax', 'accoutingProductCategorie')
   list_display_links = ('id', )       
   list_filter    = ('title', )
   ordering       = ('id', 'title',)
   search_fields  = ('id', 'title')
   fieldsets = (
      (_('Basics'), {
         'fields': ('productNumber', 'title', 'description', 'defaultunit', 'tax', 'accoutingProductCategorie', 'cancelationPeriod', 'automaticContractExtension', 'automaticContractExtensionReminder', 'minimumDuration', 'paymentIntervall', 'contractDocument')
      }),
   )
   
def createSubscription(a, request, queryset):
  for contract in queryset:
      subscription = Subscription()
      subscription.createSubscriptionFromContract(crmmodels.Contract.objects.get(id=contract.id))
      response = HttpResponseRedirect('/admin/subscriptions/'+str(subscription.id))
  return response  
createSubscription.short_description = _("Create Subscription")
   
class KoalixcrmPluginInterface(object):
  contractInlines = [InlineSubscription]
  contractActions = [createSubscription]
  invoiceInlines = []
  invoiceActions = []
  quoteInlines = []
  quoteActions = []
  customerInlines = []
  customerActions = []
   
admin.site.register(Subscription, OptionSubscription)
admin.site.register(SubscriptionType, OptionSubscriptionType)
########NEW FILE########
__FILENAME__ = events
# -*- coding: utf-8 -*

from django.utils.translation import ugettext as _

SUBSCRITIONEVENTS = (
    ('O', _('Offered')),
    ('C', _('Canceled')),
    ('S', _('Signed')),
)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Subscription'
        db.create_table('subscriptions_subscription', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Contract'])),
            ('subscriptiontype', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['subscriptions.SubscriptionType'], null=True)),
        ))
        db.send_create_signal('subscriptions', ['Subscription'])

        # Adding model 'SubscriptionEvent'
        db.create_table('subscriptions_subscriptionevent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subscriptions', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['subscriptions.Subscription'])),
            ('eventdate', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('event', self.gf('django.db.models.fields.CharField')(max_length=1)),
        ))
        db.send_create_signal('subscriptions', ['SubscriptionEvent'])

        # Adding model 'SubscriptionType'
        db.create_table('subscriptions_subscriptiontype', (
            ('product_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['crm.Product'], unique=True, primary_key=True)),
            ('cancelationPeriod', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('automaticContractExtension', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('automaticContractExtensionReminder', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('minimumDuration', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('paymentIntervall', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('contractDocument', self.gf('filebrowser.fields.FileBrowseField')(max_length=200, null=True, blank=True)),
        ))
        db.send_create_signal('subscriptions', ['SubscriptionType'])


    def backwards(self, orm):
        # Deleting model 'Subscription'
        db.delete_table('subscriptions_subscription')

        # Deleting model 'SubscriptionEvent'
        db.delete_table('subscriptions_subscriptionevent')

        # Deleting model 'SubscriptionType'
        db.delete_table('subscriptions_subscriptiontype')


    models = {
        'accounting.account': {
            'Meta': {'ordering': "['accountNumber']", 'object_name': 'Account'},
            'accountNumber': ('django.db.models.fields.IntegerField', [], {}),
            'accountType': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isACustomerPaymentAccount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'isProductInventoryActiva': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'isopeninterestaccount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'isopenreliabilitiesaccount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'originalAmount': ('django.db.models.fields.DecimalField', [], {'default': '0.0', 'max_digits': '20', 'decimal_places': '2'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'accounting.productcategorie': {
            'Meta': {'object_name': 'ProductCategorie'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lossAccount': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_loss_account'", 'to': "orm['accounting.Account']"}),
            'profitAccount': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_profit_account'", 'to': "orm['accounting.Account']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'crm.contact': {
            'Meta': {'object_name': 'Contact'},
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        },
        'crm.contract': {
            'Meta': {'object_name': 'Contract'},
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'defaultSupplier': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Supplier']", 'null': 'True', 'blank': 'True'}),
            'defaultcurrency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Currency']"}),
            'defaultcustomer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Customer']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'db_contractlstmodified'", 'to': "orm['auth.User']"}),
            'staff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'db_relcontractstaff'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'crm.currency': {
            'Meta': {'object_name': 'Currency'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rounding': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'shortName': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        'crm.customer': {
            'Meta': {'object_name': 'Customer', '_ormbases': ['crm.Contact']},
            'contact_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.Contact']", 'unique': 'True', 'primary_key': 'True'}),
            'defaultCustomerBillingCycle': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.CustomerBillingCycle']"}),
            'ismemberof': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['crm.CustomerGroup']", 'null': 'True', 'blank': 'True'})
        },
        'crm.customerbillingcycle': {
            'Meta': {'object_name': 'CustomerBillingCycle'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'timeToPaymentDate': ('django.db.models.fields.IntegerField', [], {})
        },
        'crm.customergroup': {
            'Meta': {'object_name': 'CustomerGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        },
        'crm.product': {
            'Meta': {'object_name': 'Product'},
            'accoutingProductCategorie': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['accounting.ProductCategorie']", 'null': 'True', 'blank': "'True'"}),
            'dateofcreation': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'defaultunit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Unit']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastmodification': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'lastmodifiedby': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': "'True'"}),
            'productNumber': ('django.db.models.fields.IntegerField', [], {}),
            'tax': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Tax']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'crm.supplier': {
            'Meta': {'object_name': 'Supplier', '_ormbases': ['crm.Contact']},
            'contact_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.Contact']", 'unique': 'True', 'primary_key': 'True'}),
            'offersShipmentToCustomers': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'crm.tax': {
            'Meta': {'object_name': 'Tax'},
            'accountActiva': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'db_relaccountactiva'", 'null': 'True', 'to': "orm['accounting.Account']"}),
            'accountPassiva': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'db_relaccountpassiva'", 'null': 'True', 'to': "orm['accounting.Account']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'taxrate': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'})
        },
        'crm.unit': {
            'Meta': {'object_name': 'Unit'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'fractionFactorToNextHigherUnit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isAFractionOf': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Unit']", 'null': 'True', 'blank': 'True'}),
            'shortName': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        'subscriptions.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contract']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subscriptiontype': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscriptions.SubscriptionType']", 'null': 'True'})
        },
        'subscriptions.subscriptionevent': {
            'Meta': {'object_name': 'SubscriptionEvent'},
            'event': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'eventdate': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subscriptions': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscriptions.Subscription']"})
        },
        'subscriptions.subscriptiontype': {
            'Meta': {'object_name': 'SubscriptionType', '_ormbases': ['crm.Product']},
            'automaticContractExtension': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'automaticContractExtensionReminder': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cancelationPeriod': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'contractDocument': ('filebrowser.fields.FileBrowseField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'minimumDuration': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'paymentIntervall': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'product_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['crm.Product']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['subscriptions']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext as _
from filebrowser.fields import FileBrowseField
from const.events import *
from datetime import *
from crm import models as crmmodels

class Subscription(models.Model):
  contract = models.ForeignKey(crmmodels.Contract, verbose_name=_('Subscription Type'))
  subscriptiontype = models.ForeignKey('SubscriptionType', verbose_name=_('Subscription Type'), null=True)
  
  def createSubscriptionFromContract(self, contract):
    self.contract = contract
    self.save()
    return self
  
  def createQuote(self):
    quote = Quote()
    quote.contract = self.contract
    quote.discount = 0
    quote.staff = self.contract.staff
    quote.customer = self.contract.defaultcustomer
    quote.status = 'C'
    quote.currency = self.contract.defaultcurrency
    quote.validuntil = date.today().__str__()
    quote.dateofcreation = date.today().__str__()
    quote.save()
    return quote
    
  def createInvoice(self):
    invoice = crmmodels.Invoice()
    invoice.contract = self.contract
    invoice.discount = 0
    invoice.staff = self.contract.staff
    invoice.customer = self.contract.defaultcustomer
    invoice.status = 'C'
    invoice.currency = self.contract.defaultcurrency
    invoice.payableuntil = date.today()+timedelta(days=self.contract.defaultcustomer.defaultCustomerBillingCycle.timeToPaymentDate)
    invoice.dateofcreation = date.today().__str__()
    invoice.save()
    return invoice
  
  class Meta:
     app_label = "subscriptions"
     #app_label_koalix = _("Subscriptions")
     verbose_name = _('Subscription')
     verbose_name_plural = _('Subscriptions')
  
class SubscriptionEvent(models.Model):
  subscriptions =  models.ForeignKey('Subscription', verbose_name= _('Subscription'))
  eventdate = models.DateField(verbose_name = _("Event Date"), blank=True, null=True)
  event = models.CharField(max_length=1, choices=SUBSCRITIONEVENTS, verbose_name=_('Event'))
    
  def __unicode__(self):
    return  self.event
   
  class Meta:
     app_label = "subscriptions"
     #app_label_koalix = _("Subscriptions")
     verbose_name = _('Subscription Event')
     verbose_name_plural = _('Subscription Events')

  
class SubscriptionType(crmmodels.Product):
  cancelationPeriod = models.IntegerField(verbose_name = _("Cancelation Period (months)"), blank=True, null=True)
  automaticContractExtension = models.IntegerField(verbose_name = _("Automatic Contract Extension (months)"), blank=True, null=True)
  automaticContractExtensionReminder = models.IntegerField(verbose_name = _("Automatic Contract Extensoin Reminder (days)"), blank=True, null=True)
  minimumDuration = models.IntegerField(verbose_name = _("Minimum Contract Duration"), blank=True, null=True)
  paymentIntervall = models.IntegerField(verbose_name = _("Payment Intervall (days)"), blank=True, null=True)
  contractDocument = FileBrowseField(verbose_name=_("Contract Documents"), blank=True, null=True, max_length=200)
   
  class Meta:
     app_label = "subscriptions"
     #app_label_koalix = _("Subscriptions")
     verbose_name = _('Subscription Type')
     verbose_name_plural = _('Subscription Types')
  
########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = urls.default
# -*- coding: utf-8 -*-
from crm.models import *
from django.conf.urls.defaults import *
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
from filebrowser.sites import site
admin.autodiscover()

urlpatterns = patterns('',
    (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/var/www/koalixcrm/media'}),
    (r'^$', 'django.views.generic.simple.redirect_to', {'url': '/admin'}),
    (r'^grappelli/', include('grappelli.urls')),
    (r'^admin/filebrowser/', include(site.urls)),
    (r'^admin/', include(admin.site.urls)),
)
urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
