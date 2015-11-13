__FILENAME__ = adform
"""
Django ModelForms compatible class to provide database driven form structure.

Django's ModelForms provides a way to automatically generate forms from django
Models (which are representations of database tables and relationships).
We need the ability to describe the details (such as the widget type) for
multiple fields across several forms.

Our model for this consists of a 'category' with one or more fields. Each
field then has zero or more field values, where the value corresponds to a
value submitted via one of our forms.

The model for the 'ad', which is what the field values are for, has several
fields. None of those fields except for 'title' will be part of the generated
forms.
"""

from django.utils.datastructures import SortedDict
from django.forms.util import ErrorList
from django.utils.translation import ugettext as _
from django.forms import BaseForm
from django import forms

import re

from classifieds.conf import settings
from classifieds.models import Field, FieldValue
from classifieds.utils import fields_for_ad, field_list, strip

__all__ = ('AdForm',)


class AdForm(BaseForm):
    def __init__(self, data=None, files=None, instance=None, auto_id='id_%s',
                 prefix=None, initial=None, error_class=ErrorList,
                 label_suffix=':', empty_permitted=False):

        if not instance:
            raise NotImplementedError("Ad instance must be provided")

        self.instance = instance
        object_data = self.instance.fields_dict()
        self.declared_fields = SortedDict()
        self.base_fields = fields_for_ad(self.instance)

        # if initial was provided, it should override the values from instance
        if initial is not None:
            object_data.update(initial)

        BaseForm.__init__(self, data, files, auto_id, prefix, object_data,
                          error_class, label_suffix, empty_permitted)

    def save(self, commit=True):
        if not commit:
            raise NotImplementedError("AdForm.save must commit it's changes.")

        if self.errors:
            raise ValueError(_(u"The ad could not be updated because the data didn't validate."))

        cleaned_data = self.cleaned_data

        # save fieldvalues for self.instance
        fields = field_list(self.instance)

        for field in fields:
            if field.enable_wysiwyg:
                value = unicode(strip(cleaned_data[field.name]))
            else:
                value = unicode(cleaned_data[field.name])

            # strip words in settings.FORBIDDEN_WORDS
            for word in settings.FORBIDDEN_WORDS:
                value = value.replace(word, '')

            # The title is stored directly in the ad,
            # unlike all other editable fields.
            if field.name == 'title':
                self.instance.title = value
                self.instance.save()
            else:
                # Check to see if field.fieldvalue_set has a value with
                # ad=self.instance
                try:
                    # if it does, update
                    fv = field.fieldvalue_set.get(ad=self.instance)
                except FieldValue.DoesNotExist:
                    # otherwise, create a new one
                    fv = field.fieldvalue_set.create(ad=self.instance)

                # XXX some ugly price fixing
                if field.name.endswith('price'):
                    m = re.match('^\$?(\d{1,3},?(\d{3},?)*\d{3}(\.\d{0,2})?|\d{1,3}(\.\d{0,2})?|\.\d{1,2}?)$', value)
                    value = m.group(1)
                    value.replace(',', '')
                    value = '%.2f' % float(value)

                fv.value = value
                fv.save()

        return self.instance

########NEW FILE########
__FILENAME__ = admin
"""
"""

from django.contrib import admin

import models


class AdFieldInline(admin.StackedInline):
    model = models.FieldValue


class AdAdmin(admin.ModelAdmin):
    list_filter = ('active', 'category',)
    list_display = ('title', 'category', 'expires_on',)
    search_fields = ('title',)
    inlines = [AdFieldInline]


class CategoryFieldInline(admin.StackedInline):
    model = models.Field


class CategoryAdmin(admin.ModelAdmin):
    inlines = [CategoryFieldInline]
    prepopulated_fields = {'slug': ('name',)}


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('ad', 'amount', 'paid', 'paid_on',)

    def paid(self):
        return self.instance.paid

    def paid_on(self):
        return self.instance.paid_on


admin.site.register(models.Payment, PaymentAdmin)
admin.site.register(models.Ad, AdAdmin)
admin.site.register(models.Category, CategoryAdmin)
admin.site.register([models.Field, models.FieldValue, models.Pricing,
                     models.PricingOptions, models.ImageFormat])

########NEW FILE########
__FILENAME__ = settings

from django.conf import settings

def setting(name, default):
   return getattr(settings, 'CLASSIFIEDS_' + name, default)
 

NOTICE_ENABLED = setting('NOTICE_ENABLED', False)

# (in number of days)
NOTICE_POSTING_NEW = setting('NOTICE_POSTING_NEW', 1)
NOTICE_POSTING_EXPIRES = setting('NOTICE_POSTING_EXPIRES', 1)

FROM_EMAIL = setting('FROM_EMAIL', 'john@pledge4code.com')

ADS_PER_PAGE = setting('ADS_PER_PAGE', 5)

FORBIDDEN_WORDS = setting('FORBIDDEN_WORDS', [])

########NEW FILE########
__FILENAME__ = cron
"""
  $Id$
"""

from django.template import Context, loader
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User

from django.core.mail import send_mass_mail

from django.contrib.sites.models import Site

from classifieds.models import Ad
from classifieds.conf.settings import FROM_EMAIL, NOTICE_POSTING_NEW, NOTICE_POSTING_EXPIRES

import datetime


def run():
    yesterday = datetime.datetime.today() - datetime.timedelta(days=NOTICE_POSTING_NEW)
    postings = Ad.objects.filter(created_on__gt=yesterday)

    # get subscriber list
    subscribers = User.objects.filter(userprofile__receives_new_posting_notices=True)

    emails = []

    for subscriber in subscribers:
        # 1. render context to email template
        email_template = loader.get_template('classifieds/email/newpostings.txt')
        context = Context({'postings': postings, 'user': subscriber,
                           'site': Site.objects.get_current()})
        email_contents = email_template.render(context)
        emails.append((_('New ads posted on ') + Site.objects.get_current().name,
                       email_contents,
                       FROM_EMAIL,
                       [subscriber.email],))

    # 2. send emails
    send_mass_mail(emails)

    tomorrow = datetime.datetime.today() + datetime.timedelta(days=NOTICE_POSTING_EXPIRES)
    expiring_postings = Ad.objects.filter(expires_on__lt=tomorrow)
    emails = []

    for posting in expiring_postings:
        # 1. render context to email template
        email_template = loader.get_template('classifieds/email/expiring.txt')
        context = Context({'posting': posting, 'user': posting.user,
                           'site': Site.objects.get_current()})
        email_contents = email_template.render(context)
        emails.append((_('Your ad on ') + Site.objects.get_current().name + _(' is about to expire.'),
                       email_contents,
                       FROM_EMAIL,
                       [posting.user.email],))

    # 2. send emails
    send_mass_mail(emails)

    # delete old ads
    yesterday = datetime.datetime.today() - datetime.timedelta(days=NOTICE_POSTING_EXPIRES)
    Ad.objects.filter(expires_on__lt=yesterday).delete()

if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = fields

from django.forms import CharField, ValidationError
from django.forms.fields import EMPTY_VALUES

import re, string

class TinyMCEField(CharField):
    def clean(self, value):
        "Validates max_length and min_length. Returns a Unicode object."
        if value in EMPTY_VALUES:
            return u''
        
        stripped_value = re.sub(r'<.*?>', '', value)
        stripped_value = string.replace(stripped_value, '&nbsp;', ' ')
        stripped_value = string.replace(stripped_value, '&lt;', '<')
        stripped_value = string.replace(stripped_value, '&gt;', '>')
        stripped_value = string.replace(stripped_value, '&amp;', '&')
        stripped_value = string.replace(stripped_value, '\n', '')
        stripped_value = string.replace(stripped_value, '\r', '')
        
        value_length = len(stripped_value)
        value_length -= 1
        if self.max_length is not None and value_length > self.max_length:
            raise ValidationError(self.error_messages['max_length'] % {'max': self.max_length, 'length': value_length})
        if self.min_length is not None and value_length < self.min_length:
            raise ValidationError(self.error_messages['min_length'] % {'min': self.min_length, 'length': value_length})
        
        return value

########NEW FILE########
__FILENAME__ = misc
"""
"""

from django import forms
from django.utils.translation import ugettext as _
from classifieds.models import Pricing, PricingOptions


# TODO make inlineformset class for ad images


class CheckoutForm(forms.Form):
    # construct form from Pricing and PricingOptions models
    pricing = forms.ModelChoiceField(queryset=Pricing.objects.all(),
                                     widget=forms.RadioSelect,
                                     empty_label=None)
    pricing_options = forms.ModelMultipleChoiceField(queryset=PricingOptions.objects.all(),
                                                     widget=forms.CheckboxSelectMultiple,
                                                     required=False)


class SubscribeForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email_address = forms.EmailField()
    #interested_in = forms.MultipleChoiceField(choices=[(category.name, category.name) for category in Category.objects.all()], widget=forms.CheckboxSelectMultiple)
    #comments = forms.CharField(widget=forms.Textarea)

    def clean_captcha(self):
        # TODO check captcha
        return ''

    def clean_email_address(self):
        email = self.cleaned_data["email_address"]

        if User.objects.filter(email=email).count() > 0:
            raise forms.ValidationError(_(u"The e-mail address you entered has already been registered."))

        return email

########NEW FILE########
__FILENAME__ = widgets

from django.forms import Textarea

class TinyMCEWidget(Textarea):
    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault('attrs',{})
        if 'class' not in attrs:
            attrs['class'] = 'tinymce'
        else:
            attrs['class'] += ' tinymce'
        
        super(TinyMCEWidget, self).__init__(*args, **kwargs)
    
    class Media:
        js = ('js/tiny_mce/tiny_mce.js','js/tinymce_forms.js',)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ImageFormat'
        db.create_table('classifieds_imageformat', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('format', self.gf('django.db.models.fields.CharField')(max_length=10)),
        ))
        db.send_create_signal('classifieds', ['ImageFormat'])

        # Adding model 'Category'
        db.create_table('classifieds_category', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'])),
            ('template_prefix', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('enable_contact_form_upload', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('contact_form_upload_max_size', self.gf('django.db.models.fields.IntegerField')(default=1048576)),
            ('contact_form_upload_file_extensions', self.gf('django.db.models.fields.CharField')(default='txt,doc,odf,pdf', max_length=200)),
            ('images_max_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('images_max_width', self.gf('django.db.models.fields.IntegerField')(default=1024)),
            ('images_max_height', self.gf('django.db.models.fields.IntegerField')(default=1024)),
            ('images_max_size', self.gf('django.db.models.fields.IntegerField')(default=1048576)),
            ('description', self.gf('django.db.models.fields.TextField')(default='')),
            ('sortby_fields', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('sort_order', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal('classifieds', ['Category'])

        # Adding M2M table for field images_allowed_formats on 'Category'
        db.create_table('classifieds_category_images_allowed_formats', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('category', models.ForeignKey(orm['classifieds.category'], null=False)),
            ('imageformat', models.ForeignKey(orm['classifieds.imageformat'], null=False))
        ))
        db.create_unique('classifieds_category_images_allowed_formats', ['category_id', 'imageformat_id'])

        # Adding model 'Subcategory'
        db.create_table('classifieds_subcategory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['classifieds.Category'])),
        ))
        db.send_create_signal('classifieds', ['Subcategory'])

        # Adding model 'Field'
        db.create_table('classifieds_field', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['classifieds.Category'], null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('field_type', self.gf('django.db.models.fields.IntegerField')()),
            ('help_text', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('max_length', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('enable_counter', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('enable_wysiwyg', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('required', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('options', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('classifieds', ['Field'])

        # Adding model 'Ad'
        db.create_table('classifieds_ad', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['classifieds.Category'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('expires_on', self.gf('django.db.models.fields.DateTimeField')()),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('classifieds', ['Ad'])

        # Adding model 'AdImage'
        db.create_table('classifieds_adimage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ad', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['classifieds.Ad'])),
            ('full_photo', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('thumb_photo', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('classifieds', ['AdImage'])

        # Adding model 'FieldValue'
        db.create_table('classifieds_fieldvalue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('field', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['classifieds.Field'])),
            ('ad', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['classifieds.Ad'])),
            ('value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('classifieds', ['FieldValue'])

        # Adding model 'Pricing'
        db.create_table('classifieds_pricing', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('length', self.gf('django.db.models.fields.IntegerField')()),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=9, decimal_places=2)),
        ))
        db.send_create_signal('classifieds', ['Pricing'])

        # Adding model 'PricingOptions'
        db.create_table('classifieds_pricingoptions', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.IntegerField')()),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=9, decimal_places=2)),
        ))
        db.send_create_signal('classifieds', ['PricingOptions'])

        # Adding model 'ZipCode'
        db.create_table('classifieds_zipcode', (
            ('zipcode', self.gf('django.db.models.fields.IntegerField')(primary_key=True)),
            ('latitude', self.gf('django.db.models.fields.FloatField')()),
            ('longitude', self.gf('django.db.models.fields.FloatField')()),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=2)),
        ))
        db.send_create_signal('classifieds', ['ZipCode'])

        # Adding model 'SiteSetting'
        db.create_table('classifieds_sitesetting', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('classifieds', ['SiteSetting'])

        # Adding model 'Payment'
        db.create_table('classifieds_payment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ad', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['classifieds.Ad'])),
            ('paid', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('paid_on', self.gf('django.db.models.fields.DateTimeField')()),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=9, decimal_places=2)),
            ('pricing', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['classifieds.Pricing'])),
        ))
        db.send_create_signal('classifieds', ['Payment'])

        # Adding M2M table for field options on 'Payment'
        db.create_table('classifieds_payment_options', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('payment', models.ForeignKey(orm['classifieds.payment'], null=False)),
            ('pricingoptions', models.ForeignKey(orm['classifieds.pricingoptions'], null=False))
        ))
        db.create_unique('classifieds_payment_options', ['payment_id', 'pricingoptions_id'])

        # Adding model 'UserProfile'
        db.create_table('classifieds_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
            ('receives_new_posting_notices', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('receives_newsletter', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('state', self.gf('django.contrib.localflavor.us.models.USStateField')(max_length=2, blank=True)),
            ('zipcode', self.gf('django.db.models.fields.CharField')(max_length=10, blank=True)),
            ('phone', self.gf('django.contrib.localflavor.us.models.PhoneNumberField')(default='', max_length=20, blank=True)),
        ))
        db.send_create_signal('classifieds', ['UserProfile'])


    def backwards(self, orm):
        
        # Deleting model 'ImageFormat'
        db.delete_table('classifieds_imageformat')

        # Deleting model 'Category'
        db.delete_table('classifieds_category')

        # Removing M2M table for field images_allowed_formats on 'Category'
        db.delete_table('classifieds_category_images_allowed_formats')

        # Deleting model 'Subcategory'
        db.delete_table('classifieds_subcategory')

        # Deleting model 'Field'
        db.delete_table('classifieds_field')

        # Deleting model 'Ad'
        db.delete_table('classifieds_ad')

        # Deleting model 'AdImage'
        db.delete_table('classifieds_adimage')

        # Deleting model 'FieldValue'
        db.delete_table('classifieds_fieldvalue')

        # Deleting model 'Pricing'
        db.delete_table('classifieds_pricing')

        # Deleting model 'PricingOptions'
        db.delete_table('classifieds_pricingoptions')

        # Deleting model 'ZipCode'
        db.delete_table('classifieds_zipcode')

        # Deleting model 'SiteSetting'
        db.delete_table('classifieds_sitesetting')

        # Deleting model 'Payment'
        db.delete_table('classifieds_payment')

        # Removing M2M table for field options on 'Payment'
        db.delete_table('classifieds_payment_options')

        # Deleting model 'UserProfile'
        db.delete_table('classifieds_userprofile')


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
        'classifieds.ad': {
            'Meta': {'object_name': 'Ad'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'expires_on': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'classifieds.adimage': {
            'Meta': {'object_name': 'AdImage'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Ad']"}),
            'full_photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'thumb_photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'})
        },
        'classifieds.category': {
            'Meta': {'object_name': 'Category'},
            'contact_form_upload_file_extensions': ('django.db.models.fields.CharField', [], {'default': "'txt,doc,odf,pdf'", 'max_length': '200'}),
            'contact_form_upload_max_size': ('django.db.models.fields.IntegerField', [], {'default': '1048576'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'enable_contact_form_upload': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'images_allowed_formats': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['classifieds.ImageFormat']", 'symmetrical': 'False', 'blank': 'True'}),
            'images_max_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'images_max_height': ('django.db.models.fields.IntegerField', [], {'default': '1024'}),
            'images_max_size': ('django.db.models.fields.IntegerField', [], {'default': '1048576'}),
            'images_max_width': ('django.db.models.fields.IntegerField', [], {'default': '1024'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'sort_order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'sortby_fields': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'template_prefix': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        },
        'classifieds.field': {
            'Meta': {'object_name': 'Field'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Category']", 'null': 'True', 'blank': 'True'}),
            'enable_counter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'enable_wysiwyg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'field_type': ('django.db.models.fields.IntegerField', [], {}),
            'help_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'options': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'classifieds.fieldvalue': {
            'Meta': {'object_name': 'FieldValue'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Ad']"}),
            'field': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Field']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'classifieds.imageformat': {
            'Meta': {'object_name': 'ImageFormat'},
            'format': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'classifieds.payment': {
            'Meta': {'object_name': 'Payment'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Ad']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'options': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['classifieds.PricingOptions']", 'symmetrical': 'False'}),
            'paid': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'paid_on': ('django.db.models.fields.DateTimeField', [], {}),
            'pricing': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Pricing']"})
        },
        'classifieds.pricing': {
            'Meta': {'ordering': "['price']", 'object_name': 'Pricing'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'length': ('django.db.models.fields.IntegerField', [], {}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'})
        },
        'classifieds.pricingoptions': {
            'Meta': {'ordering': "['price']", 'object_name': 'PricingOptions'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.IntegerField', [], {}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'})
        },
        'classifieds.sitesetting': {
            'Meta': {'object_name': 'SiteSetting'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'classifieds.subcategory': {
            'Meta': {'object_name': 'Subcategory'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Category']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'classifieds.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'phone': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'default': "''", 'max_length': '20', 'blank': 'True'}),
            'receives_new_posting_notices': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'receives_newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.contrib.localflavor.us.models.USStateField', [], {'max_length': '2', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'zipcode': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'})
        },
        'classifieds.zipcode': {
            'Meta': {'object_name': 'ZipCode'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'latitude': ('django.db.models.fields.FloatField', [], {}),
            'longitude': ('django.db.models.fields.FloatField', [], {}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'zipcode': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['classifieds']

########NEW FILE########
__FILENAME__ = 0002_auto__del_subcategory__del_sitesetting__chg_field_payment_paid_on
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'Subcategory'
        db.delete_table('classifieds_subcategory')

        # Deleting model 'SiteSetting'
        db.delete_table('classifieds_sitesetting')

        # Changing field 'Payment.paid_on'
        db.alter_column('classifieds_payment', 'paid_on', self.gf('django.db.models.fields.DateTimeField')(null=True))


    def backwards(self, orm):
        
        # Adding model 'Subcategory'
        db.create_table('classifieds_subcategory', (
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['classifieds.Category'])),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('classifieds', ['Subcategory'])

        # Adding model 'SiteSetting'
        db.create_table('classifieds_sitesetting', (
            ('description', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'])),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('classifieds', ['SiteSetting'])

        # User chose to not deal with backwards NULL issues for 'Payment.paid_on'
        raise RuntimeError("Cannot reverse this migration. 'Payment.paid_on' and its values cannot be restored.")


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
        'classifieds.ad': {
            'Meta': {'object_name': 'Ad'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'expires_on': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'classifieds.adimage': {
            'Meta': {'object_name': 'AdImage'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Ad']"}),
            'full_photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'thumb_photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'})
        },
        'classifieds.category': {
            'Meta': {'object_name': 'Category'},
            'contact_form_upload_file_extensions': ('django.db.models.fields.CharField', [], {'default': "'txt,doc,odf,pdf'", 'max_length': '200'}),
            'contact_form_upload_max_size': ('django.db.models.fields.IntegerField', [], {'default': '1048576'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'enable_contact_form_upload': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'images_allowed_formats': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['classifieds.ImageFormat']", 'symmetrical': 'False', 'blank': 'True'}),
            'images_max_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'images_max_height': ('django.db.models.fields.IntegerField', [], {'default': '1024'}),
            'images_max_size': ('django.db.models.fields.IntegerField', [], {'default': '1048576'}),
            'images_max_width': ('django.db.models.fields.IntegerField', [], {'default': '1024'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'sort_order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'sortby_fields': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'template_prefix': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        },
        'classifieds.field': {
            'Meta': {'object_name': 'Field'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Category']", 'null': 'True', 'blank': 'True'}),
            'enable_counter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'enable_wysiwyg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'field_type': ('django.db.models.fields.IntegerField', [], {}),
            'help_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'options': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'classifieds.fieldvalue': {
            'Meta': {'object_name': 'FieldValue'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Ad']"}),
            'field': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Field']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'classifieds.imageformat': {
            'Meta': {'object_name': 'ImageFormat'},
            'format': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'classifieds.payment': {
            'Meta': {'object_name': 'Payment'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Ad']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'options': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['classifieds.PricingOptions']", 'symmetrical': 'False'}),
            'paid': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'paid_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'pricing': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Pricing']"})
        },
        'classifieds.pricing': {
            'Meta': {'ordering': "['price']", 'object_name': 'Pricing'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'length': ('django.db.models.fields.IntegerField', [], {}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'})
        },
        'classifieds.pricingoptions': {
            'Meta': {'ordering': "['price']", 'object_name': 'PricingOptions'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.IntegerField', [], {}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'})
        },
        'classifieds.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'address': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'phone': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'default': "''", 'max_length': '20', 'blank': 'True'}),
            'receives_new_posting_notices': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'receives_newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.contrib.localflavor.us.models.USStateField', [], {'default': "''", 'max_length': '2', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'zipcode': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10', 'blank': 'True'})
        },
        'classifieds.zipcode': {
            'Meta': {'object_name': 'ZipCode'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'latitude': ('django.db.models.fields.FloatField', [], {}),
            'longitude': ('django.db.models.fields.FloatField', [], {}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'zipcode': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['classifieds']

########NEW FILE########
__FILENAME__ = 0003_auto__del_field_adimage_thumb_photo__chg_field_adimage_full_photo
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'AdImage.thumb_photo'
        db.delete_column('classifieds_adimage', 'thumb_photo')

        # Changing field 'AdImage.full_photo'
        db.alter_column('classifieds_adimage', 'full_photo', self.gf('sorl.thumbnail.fields.ImageField')(max_length=100))


    def backwards(self, orm):
        
        # Adding field 'AdImage.thumb_photo'
        db.add_column('classifieds_adimage', 'thumb_photo', self.gf('django.db.models.fields.files.ImageField')(default='', max_length=100, blank=True), keep_default=False)

        # Changing field 'AdImage.full_photo'
        db.alter_column('classifieds_adimage', 'full_photo', self.gf('django.db.models.fields.files.ImageField')(max_length=100))


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
        'classifieds.ad': {
            'Meta': {'object_name': 'Ad'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'expires_on': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'classifieds.adimage': {
            'Meta': {'object_name': 'AdImage'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Ad']"}),
            'full_photo': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'classifieds.category': {
            'Meta': {'object_name': 'Category'},
            'contact_form_upload_file_extensions': ('django.db.models.fields.CharField', [], {'default': "'txt,doc,odf,pdf'", 'max_length': '200'}),
            'contact_form_upload_max_size': ('django.db.models.fields.IntegerField', [], {'default': '1048576'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'enable_contact_form_upload': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'images_allowed_formats': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['classifieds.ImageFormat']", 'symmetrical': 'False', 'blank': 'True'}),
            'images_max_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'images_max_height': ('django.db.models.fields.IntegerField', [], {'default': '1024'}),
            'images_max_size': ('django.db.models.fields.IntegerField', [], {'default': '1048576'}),
            'images_max_width': ('django.db.models.fields.IntegerField', [], {'default': '1024'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'sort_order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'sortby_fields': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'template_prefix': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        },
        'classifieds.field': {
            'Meta': {'object_name': 'Field'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Category']", 'null': 'True', 'blank': 'True'}),
            'enable_counter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'enable_wysiwyg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'field_type': ('django.db.models.fields.IntegerField', [], {}),
            'help_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'options': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'classifieds.fieldvalue': {
            'Meta': {'object_name': 'FieldValue'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Ad']"}),
            'field': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Field']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'classifieds.imageformat': {
            'Meta': {'object_name': 'ImageFormat'},
            'format': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'classifieds.payment': {
            'Meta': {'object_name': 'Payment'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Ad']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'options': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['classifieds.PricingOptions']", 'symmetrical': 'False'}),
            'paid': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'paid_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'pricing': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['classifieds.Pricing']"})
        },
        'classifieds.pricing': {
            'Meta': {'ordering': "['price']", 'object_name': 'Pricing'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'length': ('django.db.models.fields.IntegerField', [], {}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'})
        },
        'classifieds.pricingoptions': {
            'Meta': {'ordering': "['price']", 'object_name': 'PricingOptions'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.IntegerField', [], {}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'})
        },
        'classifieds.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'address': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'phone': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'default': "''", 'max_length': '20', 'blank': 'True'}),
            'receives_new_posting_notices': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'receives_newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.contrib.localflavor.us.models.USStateField', [], {'default': "''", 'max_length': '2', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'zipcode': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10', 'blank': 'True'})
        },
        'classifieds.zipcode': {
            'Meta': {'object_name': 'ZipCode'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'latitude': ('django.db.models.fields.FloatField', [], {}),
            'longitude': ('django.db.models.fields.FloatField', [], {}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'zipcode': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['classifieds']

########NEW FILE########
__FILENAME__ = models
"""
"""

from django.db import models
from django.contrib.sites.models import Site
from django.contrib.auth.models import User

# next four lines are for sending the payment email
from django.template import Context, loader
from django.utils.translation import ugettext as _
from django.core.mail import send_mail

from sorl.thumbnail import ImageField

from classifieds.conf import settings

import datetime


class ImageFormat(models.Model):
    format = models.CharField(max_length=10)

    def __unicode__(self):
        return self.format


class Category(models.Model):
    site = models.ForeignKey(Site)
    template_prefix = models.CharField(max_length=200, blank=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField()
    enable_contact_form_upload = models.BooleanField(default=False)
    contact_form_upload_max_size = models.IntegerField(default=2 ** 20)
    contact_form_upload_file_extensions = models.CharField(max_length=200,
                                                     default="txt,doc,odf,pdf")
    images_max_count = models.IntegerField(default=0)
    images_max_width = models.IntegerField(help_text=_(u'Maximum width in pixels.'),
                                           default=1024)
    images_max_height = models.IntegerField(help_text=_(u'Maximum height in pixels.'),
                                            default=1024)
    images_max_size = models.IntegerField(help_text=_(u'Maximum size in bytes.'),
                                          default=2 ** 20)
    images_allowed_formats = models.ManyToManyField(ImageFormat, blank=True)
    description = models.TextField(default='')
    sortby_fields = models.CharField(max_length=200,
                                     help_text=_(u'A comma separated list of field names that should show up as sorting options.'),
                                     blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return self.name + u' Category'

    class Meta:
        verbose_name_plural = u'categories'


class Field(models.Model):
    BOOLEAN_FIELD = 1
    CHAR_FIELD = 2
    DATE_FIELD = 3
    DATETIME_FIELD = 4
    EMAIL_FIELD = 5
    FILE_FIELD = 6
    FLOAT_FIELD = 7
    IMAGE_FIELD = 8
    INTEGER_FIELD = 9
    TIME_FIELD = 10
    URL_FIELD = 11
    TEXT_FIELD = 12
    SELECT_FIELD = 13
    FIELD_CHOICES = (
     (BOOLEAN_FIELD, 'Checkbox'),
     (CHAR_FIELD, 'Text Input (one line)'),
     (DATE_FIELD, 'Date Selector'),
     (DATETIME_FIELD, 'Date and Time Selector'),
     (EMAIL_FIELD, 'Email Address'),
     (FILE_FIELD, 'File Upload'),
     (FLOAT_FIELD, 'Decimal Number'),
     (IMAGE_FIELD, 'Image Upload'),
     (INTEGER_FIELD, 'Integer Number'),
     (TIME_FIELD, 'Time Selector'),
     (URL_FIELD, 'URL Input'),
     (TEXT_FIELD, 'Text Input (multi-line)'),
     (SELECT_FIELD, 'Dropdown List of Options'),
    )
    category = models.ForeignKey(Category, null=True, blank=True)
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=200)
    field_type = models.IntegerField(choices=FIELD_CHOICES)
    help_text = models.TextField(blank=True)
    max_length = models.IntegerField(null=True, blank=True)
    enable_counter = models.BooleanField(help_text=_(u'This enabled the javascript counter script for text fields.'))
    enable_wysiwyg = models.BooleanField(help_text=_(u'This enables the text formatting javascript widget for text fields.'))
    required = models.BooleanField()
    options = models.TextField(help_text=_(u'A comma separated list of options [only for the dropdown list field]'),
                               blank=True)

    def __unicode__(self):
        return self.name + u' field for ' + self.category.name


class Ad(models.Model):
    category = models.ForeignKey(Category)
    user = models.ForeignKey(User)
    created_on = models.DateTimeField(auto_now_add=True)
    expires_on = models.DateTimeField()
    # active means that the ad was actually created
    active = models.BooleanField()
    title = models.CharField(max_length=255)

    @models.permalink
    def get_absolute_url(self):
        return ('classifieds_browse_ad_view', (self.pk,))

    def __unicode__(self):
        return u'Ad #' + unicode(self.pk) + ' titled "' + self.title + u'" in category ' + self.category.name

    def expired(self):
        if self.expires_on <= datetime.datetime.now():
            return True
        else:
            return False

    def fields(self):
        fields_list = []
        fields = list(self.category.field_set.all())
        fields += list(Field.objects.filter(category=None))

        for field in fields:
            try:
                fields_list.append((field, field.fieldvalue_set.get(ad=self),))
            except FieldValue.DoesNotExist:
                pass  # If no value is associated with that field, skip it.

        return fields_list

    def field(self, name):
        if name == 'title':
            return self.title
        else:
            return FieldValue.objects.get(field__name=name, ad=self).value

    def fields_dict(self):
        fields_dict = {}
        fields_dict['title'] = self.title

        for key, value in self.fields():
            fields_dict[key.name] = value.value

        return fields_dict

    def is_featured(self):
        for payment in self.payment_set.all():
            if payment.paid_on <= datetime.datetime.now() and \
               payment.paid_on + datetime.timedelta(days=payment.pricing.length) >= datetime.datetime.now():
                for option in payment.options.all():
                    if option.name == PricingOptions.FEATURED_LISTING:
                        return True

        return False


class AdImage(models.Model):
    ad = models.ForeignKey(Ad)
    full_photo = ImageField(upload_to='uploads/', blank=True)


class FieldValue(models.Model):
    field = models.ForeignKey(Field)
    ad = models.ForeignKey(Ad)
    value = models.TextField()

    def __unicode__(self):
        return self.value


class Pricing(models.Model):
    length = models.IntegerField(help_text=_(u'Period being payed for in days'))
    price = models.DecimalField(max_digits=9, decimal_places=2)

    def __unicode__(self):
        return u'$' + unicode(self.price) + u' for ' + str(self.length) + u' days'

    class Meta:
        ordering = ['price']
        verbose_name_plural = u'prices'


class PricingOptions(models.Model):
    FEATURED_LISTING = 1
    PRICING_OPTIONS = (
      (FEATURED_LISTING, u'Featured Listing'),
    )
    name = models.IntegerField(choices=PRICING_OPTIONS)
    price = models.DecimalField(max_digits=9, decimal_places=2)

    def __unicode__(self):
        pricing = {}
        pricing.update(self.PRICING_OPTIONS)
        return u'%s for $%s' % (pricing[int(self.name)], self.price,)

    class Meta:
        ordering = ['price']
        verbose_name_plural = u'options'


class ZipCode(models.Model):
    zipcode = models.IntegerField(primary_key=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    city = models.CharField(max_length=30)
    state = models.CharField(max_length=2)

    def nearby(self, radius):
        radius = float(radius)
        rangeFactor = 0.014457
        # bounding box
        objs = self.get_queryset().filter(latitude__gte=self.latitude - (radius * rangeFactor),
                                          latitude__lte=self.latitude + (radius * rangeFactor),
                                          longitude__gte=self.longitude - (radius * rangeFactor),
                                          longitude__lte=self.longitude + (radius * rangeFactor))

        # if there are any results left, use GetDistance stored function to finish
        if objs.count() > 0:
            objs = objs.extra(where=['GetDistance(%s,%s,latitude,longitude) <= %s'],
                              params=[self.latitude, self.longitude, radius])

        return objs

    def __unicode__(self):
        return _(u'Zip: %s, City: %s, State: %s') % (unicode(self.zipcode),
                                                     self.city, self.state,)


class Payment(models.Model):
    ad = models.ForeignKey(Ad)
    paid = models.BooleanField(default=False)
    paid_on = models.DateTimeField(null=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    pricing = models.ForeignKey(Pricing)
    options = models.ManyToManyField(PricingOptions)

    def complete(self, amount=0.0):
        # clear payment
        if self.amount != amount:
            return False

        self.paid = True
        self.paid_on = datetime.datetime.now()
        self.save()

        # update ad
        self.ad.expires_on += datetime.timedelta(days=payment.pricing.length)
        self.ad.created_on = datetime.datetime.now()
        self.ad.active = True
        self.ad.save()

        # send email for payment
        # 1. render context to email template
        email_template = loader.get_template('classifieds/email/payment.txt')
        context = Context({'payment': self})
        email_contents = email_template.render(context)

        # 2. send email
        send_mail(_('Your payment has been processed.'),
                  email_contents, settings.FROM_EMAIL,
                  [self.ad.user.email], fail_silently=False)


from django.contrib.localflavor.us.models import USStateField, PhoneNumberField


class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    receives_new_posting_notices = models.BooleanField(default=False)
    receives_newsletter = models.BooleanField(default=False)
    address = models.CharField(max_length=100, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    state = USStateField(blank=True, default='')
    zipcode = models.CharField(max_length=10, blank=True, default='')
    phone = PhoneNumberField(blank=True, default='')

########NEW FILE########
__FILENAME__ = search
"""
"""

from django import forms
from django.contrib.localflavor.us import forms as us_forms
from django.utils.translation import ugettext as _

from classifieds.models import *


class PriceRangeForm(forms.Form):
    """
    A price range form.  It operates on
    forms that have the fields bottom_price
    and top_price
    """
    lowest = forms.DecimalField(label="Minimum Price", decimal_places=2)
    highest = forms.DecimalField(label="Maximum Price", decimal_places=2)

    def filter(self, qs):
        """
        Returns a new QuerySet with items in the given price range.
        Remember to validate this form (call is_valid()) before calling this
        function.
        """
        if not self.is_empty():
            range = (float(self.data["lowest"]), float(self.data["highest"]))
            fvs = FieldValue.objects.filter(field__name="price",
                                            value__range=range)
            validAds = [fv.ad.pk for fv in fvs]
            return qs.filter(pk__in=validAds)
        else:
            return qs

    @staticmethod
    def create(fieldList, fieldsLeft, response=None):
        if "price" in fieldsLeft:
            fieldsLeft.remove("price")
            if response != None:
                return PriceRangeForm({'lowest': response['lowest'][0],
                                       'highest': response['highest'][0]})
            else:
                return PriceRangeForm()
        else:
            return None

    def is_empty(self):
        return not ('lowest' in self.data and \
                    self.data["lowest"] != "" and \
                    'highest' in self.data and \
                    self.data["highest"] != "")


class ZipCodeForm(forms.Form):
    """
    A zip code form.  This operates on forms that have a zip_code field.
    """
    zip_code = us_forms.USZipCodeField(required=False, label=_("Zip Code"))
    zip_range = forms.DecimalField(required=False, label=_("Range (miles)"),
                                   initial="1")

    def filter(self, qs):
        """
        Returns a new QuerySet with only items in the given zip code.
        Remember to validate this form before calling this function.
        """
        if not self.is_empty():
            zip_code = self.cleaned_data['zip_code']
            radius = self.cleaned_data['zip_range']
            zipcodeObj = ZipCode.objects.get(zipcode=zip_code)
            zipcodes = [zipcode.zipcode for zipcode in zipcodeOb.nearby(radius)]

            fvs = FieldValue.objects.filter(field__name="zip_code")
            fvs = fvs.filter(value__in=list(zipcodes))

            validAds = [fv.ad.pk for fv in fvs]

            return qs.filter(pk__in=validAds)
        else:
            return qs

    @staticmethod
    def create(fields, fieldsLeft, response=None):
        """
        Creates a new ZipCodeForm if the given fieldsLeft list contains
        'zip_code'.  Pass a dictionary (i.e. from response.GET
        or response.POST) that contains a 'zip_code' key if you want
        to initialize this form.
        """
        if 'zip_code' in fieldsLeft:
            fieldsLeft.remove('zip_code')
            if response != None:
                return ZipCodeForm({'zip_code': response['zip_code'][0],
                                    'zip_range': response['zip_range'][0]})
            else:
                return ZipCodeForm()
        else:
            return None

    def is_empty(self):
        return not ('zip_code' in self.data and \
                    self.data["zip_code"] != "" and \
                    'zip_range' in self.data and \
                    self.data["zip_range"] != "")


class MultiForm(forms.Form):
    """
    A multiselect keyword search form.  This allows users
    to pick multiple fields to search in, and enter keywords
    to find in those fields.
    """
    keywords = forms.CharField(label='Keywords:', required=False)
    #criteria = forms.MultipleChoiceField(required=False,label='Other Criteria',choices=(("Fake Choice","1")))

    def is_empty(self):
        return not ('keywords' in self.data and self.data["keywords"] != "")
        # and self.data.has_key("criteria") and self.data["criteria"] != "")

    def filter(self, qs):
        """
        Returns a new QuerySet containing only items with at least
        one attribute that matches the user's keywords.
        """
        if not self.is_empty():
            # Create a set of all field value IDs
            allAdIDs = set()

            if 'title' in self.fieldNames:
                ad_title_qs = Ad.objects.filter(title__search=self.cleaned_data["keywords"])
                allAdIDs |= set([val.pk for val in ad_title_qs])

            fvs = set(FieldValue.objects.filter(value__search=self.cleaned_data["keywords"]))

            # Join the current set with this set
            allAdIDs |= set([val.ad.pk for val in fvs])

            return qs.filter(pk__in=list(allAdIDs))
        else:
            return qs

    @staticmethod
    def create(fields, fieldsLeft, response=None):
        """
        This creates a MultiForm from the given field list and,
        optionally, a response.  NOTE: It DOES NOT remove
        the fields it uses from fieldsLeft.
        """
        inits = {"keywords": [""]}  # ,"criteria":[]}
        if response != None:
            inits.update(response)

        inits["keywords"] = inits["keywords"][0]

        x = MultiForm(inits)
        x.fieldNames = fieldsLeft
        #x.fields["criteria"].choices=[(field.name,field.label)
        #  for field in fields if field.name in fieldsLeft]
        return x


class SelectForm(forms.Form):
    def is_empty(self):
        empty = True
        for field in self.fields.keys():
            if field in self.data and \
               self.data[field] != "" and \
               self.data[field] != [] and \
               self.data[field] != ['']:
                empty = False

        return empty

    def is_valid(self):
        # XXX ?
        return True

    def filter(self, qs):
        # filter search results
        if not self.is_empty():
            allAdIDs = set()

            for field in self.fields.keys():
                if field in self.data and \
                   self.data[field] != "" and \
                   self.data[field] != [] and \
                   self.data[field] != ['']:
                    if type(self.data[field]) == type([]):
                        fvs = set(FieldValue.objects.filter(field__name=field,
                                                            value__in=self.data[field]))
                    else:
                        fvs = set(FieldValue.objects.filter(field__name=field,
                                                            value=self.data[field]))

                    # Join the current set with this set
                    allAdIDs |= set([val.ad.pk for val in fvs])

            return qs.filter(pk__in=list(allAdIDs))

        return qs

    @staticmethod
    def create(fields, response=None):
        inits = {}
        if response:
            inits.update(response)

        x = SelectForm(inits)
        x.fields.update(fields)

        return x

searchForms = (PriceRangeForm, ZipCodeForm, MultiForm)

########NEW FILE########
__FILENAME__ = signals
"""
"""

from django.db.models.signals import post_save
from django.contrib.auth.models import User

from paypal.standard.ipn.signals import payment_was_successful

from classifieds.models import Payment, UserProfile


def create_profile(sender, **kw):
    user = kw["instance"]
    if kw["created"]:
        profile = UserProfile(user=user)
        profile.save()


def make_payment(sender, **kwargs):
    payment = Payment.objects.get(pk=sender.item_number)
    payment.complete(amount=sender.mc_gross)


post_save.connect(create_profile, sender=User, dispatch_uid="users-profilecreation-signal")
payment_was_successful.connect(make_payment)

########NEW FILE########
__FILENAME__ = sitemaps
"""
"""
from django.contrib.sitemaps import Sitemap
from django.core.urlresolvers import reverse

from classifieds.models import Ad

import datetime


class AdSitemap(Sitemap):
    changefreq = 'monthly'

    def items(self):
        return Ad.objects.filter(active=True,
                                 expires_on__gt=datetime.datetime.now())

    def location(self, item):
        return reverse('classifieds_browse_ad_view', args=[item.pk])

    def lastmod(self, item):
        return item.created_on


sitemaps = {'ads': AdSitemap}

########NEW FILE########
__FILENAME__ = classifieds
"""
"""

from django import template


register = template.Library()

# TODO thumbnail related tags (show first thumbnail, show all thumbnails,
# get count of thumbnails), ad location output tag


@register.inclusion_tag('classifieds/utils/post_ad_progress.html')
def post_ad_progress(step):
    return {'step': step}

########NEW FILE########
__FILENAME__ = extras
"""
"""

from django import template
from django.template.defaultfilters import stringfilter

import string


register = template.Library()


@stringfilter
def sortname(value):
    value = value.replace('type', '_type')
    value = value.replace('job', 'job_')
    value = value.replace('id', 'ad_id')
    words = value.split('_')
    return string.join(words).title()


register.filter('sortname', sortname)

########NEW FILE########
__FILENAME__ = test_utils
from django.test import TestCase


class TestUtils(TestCase):
    pass

########NEW FILE########
__FILENAME__ = test_browse
from django.test import TestCase
from django.core.urlresolvers import reverse

from classifieds.tests.test_views import FancyTestCase


class TestAdBrowsing(FancyTestCase):
    fixtures = ['users', 'categories', 'ads']

    def setUp(self):
        self.client.login(username='user', password='user')

    def test_view_ad_must_be_active(self):
        response = self.get('classifieds_browse_ad_view', pk=1)
        self.assertEqual(response.status_code, 404)

    def test_cant_view_expired_ad_when_logged_out(self):
        self.client.logout()
        response = self.get('classifieds_browse_ad_view', pk=2)
        self.assertEqual(response.status_code, 404)

    def test_cant_view_expiered_ad_of_another_user(self):
        self.client.logout()
        self.client.login(username='other_user', password='user')
        response = self.get('classifieds_browse_ad_view', pk=2)
        self.assertEqual(response.status_code, 404)

    def test_can_view_own_expired_ad(self):
        response = self.get('classifieds_browse_ad_view', pk=2)
        self.assertEqual(response.status_code, 200)

    def test_unauthed_user_can_view_active_ad(self):
        self.client.logout()
        response = self.get('classifieds_browse_ad_view', pk=18)
        self.assertEqual(response.status_code, 200)

    def test_authed_user_can_view_active_ad(self):
        response = self.get('classifieds_browse_ad_view', pk=18)
        self.assertEqual(response.status_code, 200)

    def test_category_overview_uses_template(self):
        response = self.get('classifieds_browse_categories')
        self.assertTemplateUsed(response, 'classifieds/category_overview.html')

########NEW FILE########
__FILENAME__ = test_create
from django.test import TestCase
from django.core.urlresolvers import reverse

from classifieds.tests.test_views import FancyTestCase


class TestAdCreation(FancyTestCase):
    fixtures = ['users', 'categories']

    def setUp(self):
        self.client.login(username='user', password='user')

    def test_create_ad_redirects_users_to_select_category(self):
        response = self.get('classifieds_create_ad')
        self.assertRedirects(response,
                             reverse('classifieds_create_ad_select_category'))

    def test_create_ad_renders_pricing_template_for_unauthenticated_users(self):
        self.client.logout()
        response = self.get('classifieds_create_ad')
        self.assertTemplateUsed(response, 'classifieds/index.html')

    def test_select_category_has_categories_context(self):
        response = self.get('classifieds_create_ad_select_category')
        self.assertIn('categories', response.context)

    def test_select_category_has_create_type_context(self):
        response = self.get('classifieds_create_ad_select_category')
        self.assertEqual(response.context['type'], 'create')

    def test_select_category_renders_correct_template(self):
        response = self.get('classifieds_create_ad_select_category')
        self.assertTemplateUsed(response, 'classifieds/category_choice.html')

    def test_create_in_category_creates_inactive_ad(self):
        response = self.get('classifieds_create_ad_in_category', slug='test')
        from classifieds.models import Ad
        ad = Ad.objects.get()  # There can be only one... right now anyway
        self.assertFalse(ad.active)

    def test_create_in_category_redirects_to_ad_edit(self):
        response = self.get('classifieds_create_ad_in_category', slug='test')
        from classifieds.models import Ad
        ad = Ad.objects.get()  # There can be only one... right now anyway
        self.assertRedirects(response, reverse('classifieds_create_ad_edit',
                                               kwargs={'pk': ad.pk}))


class TestAdCreationEditing(FancyTestCase):
    fixtures = ['users', 'categories', 'ads']

    def setUp(self):
        self.client.login(username='user', password='user')

    def test_ad_edit_nonauthed_user_cant_edit_ad(self):
        self.client.logout()
        response = self.get('classifieds_create_ad_edit', pk=1)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('auth_login'),
                              response['Location'])

    def test_ad_edit_other_user_cant_edit_ad(self):
        self.client.logout()
        self.client.login(username='other_user', password='user')
        response = self.get('classifieds_create_ad_edit', pk=1)
        self.assertEqual(response.status_code, 404)

    def test_ad_edit_has_form_context(self):
        response = self.get('classifieds_create_ad_edit', pk=1)
        self.assertIn('form', response.context)
        self.assertIn('imagesformset', response.context)

    def test_ad_edit_has_custom_fields(self):
        response = self.get("classifieds_create_ad_edit", pk=1)
        self.assertIn('Test Field', response.context['form'].fields.keys())

    def test_ad_edit_save_redirects_to_preview(self):
        params = {'adimage_set-TOTAL_FORMS': u'3',
                  'adimage_set-INITIAL_FORMS': u'0',
                  'adimage_set-MAX_NUM_FORMS': u'3',
                  'title': 'Test Title',
                  'Test Field': '2011-08-22 08:00:00'}
        response = self.client.post(reverse("classifieds_create_ad_edit",
                                    kwargs=dict(pk=1)), params)
        self.assertRedirects(response, reverse("classifieds_create_ad_preview",
                                               kwargs=dict(pk=1)))

    def test_ad_edit_save_saves_title(self):
        params = {'adimage_set-TOTAL_FORMS': u'3',
                  'adimage_set-INITIAL_FORMS': u'0',
                  'adimage_set-MAX_NUM_FORMS': u'3',
                  'title': 'Test Title',
                  'Test Field': '2011-08-22 08:00:00'}
        response = self.client.post(reverse("classifieds_create_ad_edit",
                                    kwargs=dict(pk=1)), params)
        from classifieds.models import Ad
        self.assertEqual(Ad.objects.get(pk=1).title, 'Test Title')

    def test_ad_edit_save_saves_custom_field(self):
        params = {'adimage_set-TOTAL_FORMS': u'3',
                  'adimage_set-INITIAL_FORMS': u'0',
                  'adimage_set-MAX_NUM_FORMS': u'3',
                  'title': 'Test Title',
                  'Test Field': '2011-08-22 08:00:00'}
        response = self.client.post(reverse("classifieds_create_ad_edit",
                                    kwargs=dict(pk=1)), params)
        from classifieds.models import Ad
        self.assertEqual(Ad.objects.get(pk=1).field('Test Field'),
                         '2011-08-22 08:00:00')

    def test_ad_preview_nonauthed_user_cant_see_ad(self):
        self.client.logout()
        response = self.get('classifieds_create_ad_preview', pk=1)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('auth_login'),
                              response['Location'])

    def test_ad_preview_other_user_cant_see_ad(self):
        self.client.logout()
        self.client.login(username='other_user', password='user')
        response = self.get('classifieds_create_ad_preview', pk=1)
        self.assertEqual(response.status_code, 404)

########NEW FILE########
__FILENAME__ = test_manage
from django.test import TestCase
from django.core.urlresolvers import reverse

from classifieds.tests.test_views import FancyTestCase


class TestAdManage(FancyTestCase):
    fixtures = ['users', 'categories', 'ads']

    def setUp(self):
        self.client.login(username='user', password='user')

    def test_manage_view_all_requires_login(self):
        self.client.logout()
        response = self.get('classifieds_manage_view_all')
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('auth_login'), response['Location'])

    def test_manage_delete_requires_login(self):
        self.client.logout()
        response = self.post('classifieds_manage_ad_delete', pk=18)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('auth_login'), response['Location'])

    def test_manage_delete_requires_post_to_complete(self):
        response = self.get('classifieds_manage_ad_delete', pk=18)
        from classifieds.models import Ad
        self.assertEqual(Ad.objects.filter(pk=18).count(), 1)

    def test_manage_delete_get_renders_confirmation_template(self):
        response = self.get('classifieds_manage_ad_delete', pk=18)
        self.assertTemplateUsed(response, 'classifieds/ad_confirm_delete.html')

    def test_manage_delete_post_deletes_ad(self):
        response = self.post('classifieds_manage_ad_delete', pk=18)
        from classifieds.models import Ad
        self.assertEqual(Ad.objects.filter(pk=18).count(), 0)

    def test_manage_edit_has_form_in_context(self):
        response = self.get('classifieds_manage_ad_edit', pk=18)
        self.assertIn('form', response.context)
        self.assertIn('imagesformset', response.context)

    def test_manage_edit_save_redirects_to_view_all(self):
        params = {'adimage_set-TOTAL_FORMS': u'3',
                  'adimage_set-INITIAL_FORMS': u'0',
                  'adimage_set-MAX_NUM_FORMS': u'3',
                  'title': 'Test Title',
                  'Test Field': '2011-08-22 08:00:00'}
        response = self.client.post(reverse("classifieds_manage_ad_edit",
                                    kwargs=dict(pk=18)), params)
        self.assertRedirects(response, reverse("classifieds_manage_view_all"))

    def test_manage_edit_save_saves_title(self):
        params = {'adimage_set-TOTAL_FORMS': u'3',
                  'adimage_set-INITIAL_FORMS': u'0',
                  'adimage_set-MAX_NUM_FORMS': u'3',
                  'title': 'Test Title',
                  'Test Field': '2011-08-22 08:00:00'}
        response = self.client.post(reverse("classifieds_manage_ad_edit",
                                    kwargs=dict(pk=18)), params)
        from classifieds.models import Ad
        self.assertEqual(Ad.objects.get(pk=18).title, 'Test Title')

    def test_ad_edit_save_saves_custom_field(self):
        params = {'adimage_set-TOTAL_FORMS': u'3',
                  'adimage_set-INITIAL_FORMS': u'0',
                  'adimage_set-MAX_NUM_FORMS': u'3',
                  'title': 'Test Title',
                  'Test Field': '2011-08-22 08:00:00'}
        response = self.client.post(reverse("classifieds_manage_ad_edit",
                                    kwargs=dict(pk=18)), params)
        from classifieds.models import Ad
        self.assertEqual(Ad.objects.get(pk=18).field('Test Field'),
                         '2011-08-22 08:00:00')

########NEW FILE########
__FILENAME__ = urls
"""
"""
from django.conf.urls.defaults import *

from classifieds.views import AdEditView, AdCreationEditView
from classifieds.views.manage import AdDeleteView


# nested urls
base_urlpatterns = patterns('classifieds.views',
    url(r'^$', 'browse.category_overview',
        name='classifieds_browse_categories'),

    url(r'^post/$', 'create.first_post', name='classifieds_create_ad'),
    url(r'^create/$', 'create.select_category',
        name='classifieds_create_ad_select_category'),
    url(r'^create/(?P<slug>[-\w]+)/$', 'create.create_in_category',
        name='classifieds_create_ad_in_category'),
    url(r'^create/edit/(?P<pk>[0-9]+)/$', AdCreationEditView.as_view(),
        name='classifieds_create_ad_edit'),
    url(r'^create/preview/(?P<pk>[0-9]+)/$', 'create.preview',
        name='classifieds_create_ad_preview'),

    url(r'^search/(?P<slug>[-\w]+)/$', 'browse.search_in_category',
        name='classifieds_browse_category_search'),
    url(r'^search/results/(?P<slug>[-\w]+)/$', 'browse.search_results',
        name='classifieds_browse_search_results'),
    url(r'^(?P<pk>[0-9]+)/$', 'browse.view',
        name='classifieds_browse_ad_view'),
)

# local-based urls coming soon
urlpatterns = base_urlpatterns

# top-level urls
urlpatterns += patterns('classifieds.views',
    url(r'^mine/$', 'manage.mine', name='classifieds_manage_view_all'),
    url(r'^edit/(?P<pk>[0-9]+)/$', AdEditView.as_view(),
        name='classifieds_manage_ad_edit'),
    url(r'^delete/(?P<pk>[0-9]+)/$', AdDeleteView.as_view(),
        name='classifieds_manage_ad_delete'),

    (r'^new/(?P<pk>[0-9]+)/$', 'payment.view_bought'),
    (r'^checkout/(?P<pk>[0-9]+)$', 'payment.checkout'),
    (r'^pricing$', 'payment.pricing'),

    (r'^contact/(?P<pk>[0-9]+)$', 'contact.contact_seller'),
)


from sitemaps import sitemaps


urlpatterns += patterns('',
    (r'^ipn/$', 'paypal.standard.ipn.views.ipn'),
    (r'^sitemap.xml$', 'django.contrib.sitemaps.views.sitemap',
     {'sitemaps': sitemaps}),
)

########NEW FILE########
__FILENAME__ = utils
"""
"""

from PIL import Image
import HTMLParser
import string
import re
import os.path

from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext as _
from django.core.paginator import Paginator, InvalidPage
from django.template.loader import get_template
from django.template import TemplateDoesNotExist, RequestContext
from django.forms import ValidationError

from django import forms
from django.http import HttpResponse
from django.forms.fields import EMPTY_VALUES

from classifieds.conf import settings
from classifieds.search import SelectForm, searchForms
from classifieds.models import Ad, Field, Category, Pricing, PricingOptions


def category_template_name(category, page):
    return os.path.join(u'classifieds/category',
                        category.template_prefix, page)


def render_category_page(request, category, page, context):
    template_name = category_template_name(category, page)
    try:
        template = get_template(template_name)
    except TemplateDoesNotExist:
        template = get_template('classifieds/category/base/%s' % page)

    context = RequestContext(request, context)
    return HttpResponse(template.render(context))


def clean_adimageformset(self):
    max_size = self.instance.category.images_max_size
    for form in self.forms:
        try:
            if not hasattr(form.cleaned_data['full_photo'], 'file'):
                continue
        except:
            continue

        if form.cleaned_data['full_photo'].size > max_size:
            raise forms.ValidationError(_(u'Maximum image size is %s KB') % \
                    str(max_size / 1024))

        im = Image.open(form.cleaned_data['full_photo'].file)
        allowed = self.instance.catoegy.images_allowed_formats
        if allowed_formats.filter(format=im.format).count() == 0:
            raise forms.ValidationError(
                    _(u'Your image must be in one of the following formats: ')\
                    + ', '.join(allowed_formats.values_list('format',
                                                            flat=True)))


def context_sortable(request, ads, perpage=settings.ADS_PER_PAGE):
    order = '-'
    sort = 'expires_on'
    page = 1

    if 'perpage' in request.GET and request.GET['perpage'] != '':
        perpage = int(request.GET['perpage'])

    if 'order' in request.GET and request.GET['order'] != '':
        if request.GET['order'] == 'desc':
            order = '-'
        elif request.GET['order'] == 'asc':
            order = ''

    if 'page' in request.GET:
        page = int(request.GET['page'])

    if 'sort' in request.GET and request.GET['sort'] != '':
        sort = request.GET['sort']

    if sort in ['created_on', 'expires_on', 'category', 'title']:
        ads_sorted = ads.extra(select={'featured': """SELECT 1
FROM `classifieds_payment_options`
LEFT JOIN `classifieds_payment` ON `classifieds_payment_options`.`payment_id` = `classifieds_payment`.`id`
LEFT JOIN `classifieds_pricing` ON `classifieds_pricing`.`id` = `classifieds_payment`.`pricing_id`
LEFT JOIN `classifieds_pricingoptions` ON `classifieds_payment_options`.`pricingoptions_id` = `classifieds_pricingoptions`.`id`
WHERE `classifieds_pricingoptions`.`name` = %s
AND `classifieds_payment`.`ad_id` = `classifieds_ad`.`id`
AND `classifieds_payment`.`paid` =1
AND `classifieds_payment`.`paid_on` < NOW()
AND DATE_ADD( `classifieds_payment`.`paid_on` , INTERVAL `classifieds_pricing`.`length`
DAY ) > NOW()"""}, select_params=[PricingOptions.FEATURED_LISTING]).extra(order_by=['-featured', order + sort])
    else:
        ads_sorted = ads.extra(select=SortedDict([('fvorder', 'select value from classifieds_fieldvalue LEFT JOIN classifieds_field on classifieds_fieldvalue.field_id = classifieds_field.id where classifieds_field.name = %s and classifieds_fieldvalue.ad_id = classifieds_ad.id'), ('featured', """SELECT 1
FROM `classifieds_payment_options`
LEFT JOIN `classifieds_payment` ON `classifieds_payment_options`.`payment_id` = `classifieds_payment`.`id`
LEFT JOIN `classifieds_pricing` ON `classifieds_pricing`.`id` = `classifieds_payment`.`pricing_id`
LEFT JOIN `classifieds_pricingoptions` ON `classifieds_payment_options`.`pricingoptions_id` = `classifieds_pricingoptions`.`id`
WHERE `classifieds_pricingoptions`.`name` = %s
AND `classifieds_payment`.`ad_id` = `classifieds_ad`.`id`
AND `classifieds_payment`.`paid` =1
AND `classifieds_payment`.`paid_on` < NOW()
AND DATE_ADD( `classifieds_payment`.`paid_on` , INTERVAL `classifieds_pricing`.`length`
DAY ) > NOW()""")]), select_params=[sort, PricingOptions.FEATURED_LISTING]).extra(order_by=['-featured', order + 'fvorder'])

    pager = Paginator(ads_sorted, perpage)

    try:
        page = pager.page(page)
    except InvalidPage:
        page = {'object_list': False}

    can_sortby_list = []
    sortby_list = ['created_on']
    for category in Category.objects.filter(ad__in=ads.values('pk').query).distinct():
        can_sortby_list += category.sortby_fields.split(',')

    for category in Category.objects.filter(ad__in=ads.values('pk').query).distinct():
        for fieldname, in category.field_set.values_list('name'):
            if fieldname not in sortby_list and fieldname in can_sortby_list:
                sortby_list.append(fieldname)

    for fieldname, in Field.objects.filter(category=None).values_list('name'):
        if fieldname not in sortby_list and fieldname in can_sortby_list:
            sortby_list.append(fieldname)

    return {'page': page, 'sortfields': sortby_list, 'no_results': False,
            'perpage': perpage}


def prepare_sforms(fields, fields_left, post=None):
    sforms = []
    select_fields = {}
    for field in fields:
        if field.field_type == Field.SELECT_FIELD:  # is select field
            # add select field
            options = field.options.split(',')
            choices = zip(options, options)
            choices.insert(0, ('', 'Any',))
            form_field = forms.ChoiceField(label=field.label, required=False, help_text=field.help_text + u'\nHold ctrl or command on Mac for multiple selections.', choices=choices, widget=forms.SelectMultiple)
            # remove this field from fields_list
            fields_left.remove(field.name)
            select_fields[field.name] = form_field

    sforms.append(SelectForm.create(select_fields, post))

    for sf in searchForms:
        f = sf.create(fields, fields_left, post)
        if f is not None:
            sforms.append(f)

    return sforms


class StrippingParser(HTMLParser.HTMLParser):
    # These are the HTML tags that we will leave intact
    valid_tags = ('b', 'i', 'br', 'p', 'strong', 'h1', 'h2', 'h3', 'em',
                  'span', 'ul', 'ol', 'li')

    from htmlentitydefs import entitydefs  # replace entitydefs from sgmllib

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.result = ""
        self.endTagList = []

    def handle_data(self, data):
        if data:
            self.result = self.result + data

    def handle_charref(self, name):
        self.result = "%s&#%s;" % (self.result, name)

    def handle_entityref(self, name):
        if name in self.entitydefs:
            x = ';'
        else:
            # this breaks unstandard entities that end with ';'
            x = ''
            self.result = "%s&%s%s" % (self.result, name, x)

    def handle_starttag(self, tag, attrs):
        """ Delete all tags except for legal ones """
        if tag in self.valid_tags:
            self.result = self.result + '<' + tag
            for k, v in attrs:
                if string.lower(k[0:2]) != 'on' and \
                   string.lower(v[0:10]) != 'javascript':
                    self.result = '%s %s="%s"' % (self.result, k, v)

            endTag = '</%s>' % tag
            self.endTagList.insert(0, endTag)
            self.result = self.result + '>'

    def handle_endtag(self, tag):
        if tag in self.valid_tags:
            self.result = "%s</%s>" % (self.result, tag)
            remTag = '</%s>' % tag
            self.endTagList.remove(remTag)

    def cleanup(self):
        """ Append missing closing tags """
        for j in range(len(self.endTagList)):
            self.result = self.result + self.endTagList[j]


def strip(s):
    """ Strip illegal HTML tags from string s """
    parser = StrippingParser()
    parser.feed(s)
    parser.close()
    parser.cleanup()
    return parser.result


class TinyMCEWidget(forms.Textarea):
    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault('attrs', {})
        if 'class' not in attrs:
            attrs['class'] = 'tinymce'
        else:
            attrs['class'] += ' tinymce'

        super(TinyMCEWidget, self).__init__(*args, **kwargs)

    class Media:
        js = ('js/tiny_mce/tiny_mce.js', 'js/tinymce_forms.js',)


class TinyMCEField(forms.CharField):
    def clean(self, value):
        """Validates max_length and min_length. Returns a Unicode object."""
        if value in EMPTY_VALUES:
            return u''

        stripped_value = re.sub(r'<.*?>', '', value)
        stripped_value = string.replace(stripped_value, '&nbsp;', ' ')
        stripped_value = string.replace(stripped_value, '&lt;', '<')
        stripped_value = string.replace(stripped_value, '&gt;', '>')
        stripped_value = string.replace(stripped_value, '&amp;', '&')
        stripped_value = string.replace(stripped_value, '\n', '')
        stripped_value = string.replace(stripped_value, '\r', '')

        value_length = len(stripped_value)
        value_length -= 1
        if self.max_length is not None and value_length > self.max_length:
            raise forms.ValidationError(self.error_messages['max_length'] % {'max': self.max_length, 'length': value_length})
        if self.min_length is not None and value_length < self.min_length:
            raise forms.ValidationError(self.error_messages['min_length'] % {'min': self.min_length, 'length': value_length})

        return value


def field_list(instance):
    class MockField:
        def __init__(self, name, field_type, label, required, help_text, enable_wysiwyg, max_length):
            self.name = name
            self.field_type = field_type
            self.label = label
            self.required = required
            self.help_text = help_text
            self.enable_wysiwyg = enable_wysiwyg
            self.max_length = max_length

    title_field = MockField('title', Field.CHAR_FIELD, _('Title'), True, '', False, 100)

    fields = [title_field]  # all ads have titles
    fields += list(instance.category.field_set.all())
    fields += list(Field.objects.filter(category=None))
    return fields


def fields_for_ad(instance):
    # generate a sorted dict of fields corresponding to the Field model
    # for the Ad instance
    fields_dict = SortedDict()
    fields = field_list(instance)
    # this really, really should be refactored
    for field in fields:
        if field.field_type == Field.BOOLEAN_FIELD:
            fields_dict[field.name] = forms.BooleanField(label=field.label, required=False, help_text=field.help_text)
        elif field.field_type == Field.CHAR_FIELD:
            widget = forms.TextInput
            fields_dict[field.name] = forms.CharField(label=field.label, required=field.required, max_length=field.max_length, help_text=field.help_text, widget=widget)
        elif field.field_type == Field.DATE_FIELD:
            fields_dict[field.name] = forms.DateField(label=field.label, required=field.required, help_text=field.help_text)
        elif field.field_type == Field.DATETIME_FIELD:
            fields_dict[field.name] = forms.DateTimeField(label=field.label, required=field.required, help_text=field.help_text)
        elif field.field_type == Field.EMAIL_FIELD:
            fields_dict[field.name] = forms.EmailField(label=field.label, required=field.required, help_text=field.help_text)
        elif field.field_type == Field.FLOAT_FIELD:
            fields_dict[field.name] = forms.FloatField(label=field.label, required=field.required, help_text=field.help_text)
        elif field.field_type == Field.INTEGER_FIELD:
            fields_dict[field.name] = forms.IntegerField(label=field.label, required=field.required, help_text=field.help_text)
        elif field.field_type == Field.TIME_FIELD:
            fields_dict[field.name] = forms.TimeField(label=field.label, required=field.required, help_text=field.help_text)
        elif field.field_type == Field.URL_FIELD:
            fields_dict[field.name] = forms.URLField(label=field.label, required=field.required, help_text=field.help_text)
        elif field.field_type == Field.SELECT_FIELD:
            options = field.options.split(',')
            fields_dict[field.name] = forms.ChoiceField(label=field.label, required=field.required, help_text=field.help_text, choices=zip(options, options))
        elif field.field_type == Field.TEXT_FIELD:
            if field.enable_wysiwyg:
                widget = TinyMCEWidget
                field_type = TinyMCEField
            else:
                widget = forms.Textarea
                field_type = forms.CharField

            fields_dict[field.name] = field_type(label=field.label,
                                                 required=field.required,
                                                 help_text=field.help_text,
                                                 max_length=field.max_length,
                                                 widget=widget)
        else:
            raise NotImplementedError(u'Unknown field type "%s"' % field.get_field_type_display())

    return fields_dict

########NEW FILE########
__FILENAME__ = browse
import datetime

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django import forms
from django.http import Http404

from classifieds.models import Category, Ad, Field
from classifieds.utils import context_sortable, render_category_page, \
                              prepare_sforms


def category_overview(request):
    context = {}
    context['categories'] = Category.objects.order_by('sort_order')
    return render_to_response('classifieds/category_overview.html', context,
                              context_instance=RequestContext(request))


def view(request, pk):
    # find the ad, if available
    ad = get_object_or_404(Ad, pk=pk, active=True)

    # only show an expired ad if this user owns it
    if ad.expires_on < datetime.datetime.now() and ad.user != request.user:
        raise Http404

    return render_category_page(request, ad.category, 'view.html', {'ad': ad})


def search_in_category(request, slug):
    # reset the search params, if present
    try:
        del request.session['search']
    except KeyError:
        pass

    return search_results(request, slug)


def search_results(request, slug):
    category = get_object_or_404(Category, slug=slug)
    fields = list(category.field_set.all())
    fields += list(Field.objects.filter(category=None))
    fieldsLeft = [field.name for field in fields]

    if request.method == "POST" or 'search' in request.session:
        ads = category.ad_set.filter(active=True,
                                     expires_on__gt=datetime.datetime.now())
        # A request dictionary with keys defined for all
        # fields in the category.
        post = {}
        if 'search' in request.session:
            post.update(request.session['search'])
        else:
            post.update(request.POST)

        sforms = prepare_sforms(fields, fieldsLeft, post)

        isValid = True

        for f in sforms:
            # TODO: this assumes the form is not required
            # (it's a search form after all)
            if not f.is_valid() and not f.is_empty():
                isValid = False

        if isValid:
            if request.method == 'POST':
                request.session['search'] = {}
                request.session['search'].update(request.POST)
                return redirect('classifieds_browse_search_results', slug=slug)

            for f in sforms:
                ads = f.filter(ads)

            if ads.count() == 0:
                return render_to_response('classifieds/list.html',
                                          {'no_results': True,
                                           'category': category},
                                          context_instance=RequestContext(request))
            else:
                context = context_sortable(request, ads)
                context['category'] = category
                return render_to_response('classifieds/list.html', context,
                                          context_instance=RequestContext(request))
    else:
        sforms = prepare_sforms(fields, fieldsLeft)

    return render_to_response('classifieds/search.html',
                              {'forms': sforms, 'category': category},
                              context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = contact
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from classifieds.models import Ad


def contact_seller(request, pk):
    ad = get_object_or_404(Ad, pk=pk)
    # TODO contact form here

########NEW FILE########
__FILENAME__ = create
import datetime

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.utils.translation import ugettext as _

from classifieds.models import Ad, Category, Pricing
from classifieds.utils import render_category_page


def first_post(request):
    if request.user.is_authenticated() and request.user.is_active:
        return redirect('classifieds_create_ad_select_category')
    else:
        return render_to_response('classifieds/index.html',
                                  {'prices': Pricing.objects.all()},
                                  context_instance=RequestContext(request))


@login_required
def select_category(request):
    """
    List the categories available and send the user to the create_in_category
    view.
    """
    return render_to_response('classifieds/category_choice.html',
                              {'categories': Category.objects.all(),
                               'type': 'create'},
                              context_instance=RequestContext(request))


@login_required
def create_in_category(request, slug):
    # validate category slug
    category = get_object_or_404(Category, slug=slug)

    ad = Ad.objects.create(category=category, user=request.user,
                           expires_on=datetime.datetime.now(), active=False)
    ad.save()
    return redirect('classifieds_create_ad_edit', pk=ad.pk)


@login_required
def preview(request, pk):
    ad = get_object_or_404(Ad, pk=pk, user=request.user)

    if ad.active:
        return redirect('classifieds_browse_ad_view', pk=pk)

    return render_category_page(request, ad.category, 'preview.html',
                                {'ad': ad, 'create': True})

########NEW FILE########
__FILENAME__ = manage
from django.shortcuts import render_to_response, redirect
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.template import RequestContext
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.views.generic import DeleteView


from classifieds.models import Ad
from classifieds.utils import context_sortable


@login_required
def mine(request):
    ads = Ad.objects.filter(user=request.user, active=True)
    context = context_sortable(request, ads)
    context['sortfields'] = ['id', 'category', 'created_on']
    return render_to_response('classifieds/manage.html', context,
                              context_instance=RequestContext(request))


class AdDeleteView(DeleteView):
    model = Ad

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(AdDeleteView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return redirect('classifieds_manage_view_all')

    def delete(self, request, *args, **kwargs):
        response = super(AdDeleteView, self).delete(request, *args, **kwargs)

        # create status message
        messages.success(request, _(u'Ad deleted.'))

        return response

    def get_object(self, queryset=None):
        obj = super(AdDeleteView, self).get_object(queryset)

        if not obj.user == self.request.user:
            raise Http404

        return obj

########NEW FILE########
__FILENAME__ = payment
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.template import Context, loader, RequestContext
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.conf import settings

from paypal.standard.forms import PayPalPaymentsForm

from classifieds.models import Ad, Pricing, PricingOptions, Payment
from classifieds.forms.misc import CheckoutForm
from classifieds.conf import settings as app_settings
from classifieds import views


@login_required
def checkout(request, pk):
    ad = get_object_or_404(Ad, pk=pk)
    form = CheckoutForm(request.POST or None)
    if form.is_valid():
        total = 0
        pricing = form.cleaned_data["pricing"]
        total += pricing.price
        pricing_options = []
        for option in form.cleaned_data["pricing_options"]:
            pricing_options.append(option)
            total += option.price

        # create Payment object
        payment = Payment.objects.create(ad=ad, pricing=pricing, amount=total)
        for option in pricing_options:
            payment.options.add(option)

        payment.save()

        # send email when done
        # 1. render context to email template
        email_template = loader.get_template('classifieds/email/posting.txt')
        context = Context({'ad': ad})
        email_contents = email_template.render(context)

        # 2. send email
        send_mail(_('Your ad will be posted shortly.'),
                  email_contents,
                  app_settings.FROM_EMAIL,
                  [ad.user.email],
                  fail_silently=False)

        item_name = _('Your ad on ') + Site.objects.get_current().name
        paypal_values = {'amount': total,
                         'item_name': item_name,
                         'item_number': payment.pk,
                         'quantity': 1}

        if settings.DEBUG:
            paypal_form = PayPalPaymentsForm(initial=paypal_values).sandbox()
        else:
            paypal_form = PayPalPaymentsForm(initial=paypal_values).render()

        return render_to_response('classifieds/paypal.html',
                                  {'form': paypal_form},
                                  context_instance=RequestContext(request))

    return render_to_response('classifieds/checkout.html',
                              {'ad': ad, 'form': form},
                              context_instance=RequestContext(request))


def pricing(request):
    return render_to_response('classifieds/pricing.js',
                              {'prices': Pricing.objects.all(),
                               'options': PricingOptions.objects.all()},
                              context_instance=RequestContext(request))


@login_required
def view_bought(request, pk):
    messages.success(_("""Your ad has been successfully posted.
    Thank You for Your Order!"""))
    return views.browse.view(request, pk)

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
# Django settings for project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
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
TIME_ZONE = 'US/Pacific'

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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

STATIC_URL = '/static/'
STATIC_ROOT = ''

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)
# Make this unique, and don't share it with anybody.
SECRET_KEY = 'n&#xnm25j6wb1cw5e#7bp5ok1ti*rf9vi51e)h0&dnt8(+076n'

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

ROOT_URLCONF = 'project.urls'

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
    'django.contrib.admin',

    'classifieds',

    # Additional apps
    'paypal.standard.ipn',
    'registration',
    'profiles',
    'django.contrib.humanize',
    'south',
    'sorl.thumbnail',

    'django_nose'
)

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

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}

AUTH_PROFILE_MODULE = 'classifieds.UserProfile'

LOGIN_REDIRECT_URL = '/registration/welcome/'
LOGIN_URL = '/registration/login/'
LOGOUT_URL = '/registration/logout/'

ACCOUNT_ACTIVATION_DAYS = 1

EMAIL_HOST = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_HOST_USER = ''
EMAIL_USE_TLS = True

RECAPTCHA_PUB_KEY = "your public key"
RECAPTCHA_PRIVATE_KEY = "your private key"

PAYPAL_RECEIVER_EMAIL = ''

TEST_RUNNER = "django_nose.NoseTestSuiteRunner"

try:
    from settings_local import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),

    # add-on apps.
    (r'^registration/', include('registration.urls')),
    (r'^profiles/', include('profiles.urls'), {'success_url': '/profiles/edit/'}),

    # our views (included from the app)
    (r'', include('classifieds.urls')),
)

########NEW FILE########
