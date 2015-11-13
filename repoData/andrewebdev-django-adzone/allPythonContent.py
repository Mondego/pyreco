__FILENAME__ = admin
# -*- coding: utf-8 -*-

# © Copyright 2009 Andre Engelbrecht. All Rights Reserved.
# This script is licensed under the BSD Open Source Licence
# Please see the text file LICENCE for more information
# If this script is distributed, it must be accompanied by the Licence

import csv

from django.contrib import admin
from django.http import HttpResponse
from adzone.models import *


class AdvertiserAdmin(admin.ModelAdmin):
    search_fields = ['company_name', 'website']
    list_display = ['company_name', 'website', 'user']
    raw_id_fields = ['user']


class AdCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ['title']}
    list_display = ['title', 'slug']


class AdZoneAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'description']


class AdBaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'url', 'advertiser', 'since', 'updated', 'start_showing', 'stop_showing']
    list_filter = ['updated', 'start_showing', 'stop_showing', 'since', 'updated']
    search_fields = ['title', 'url']
    raw_id_fields = ['advertiser']


class AdClickAdmin(admin.ModelAdmin):
    search_fields = ['ad', 'source_ip']
    list_display = ['ad', 'click_date', 'source_ip']
    list_filter = ['click_date']
    date_hierarchy = 'click_date'
    actions = ['download_clicks']

    def download_clicks(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="clicks.csv"'
        writer = csv.writer(response)
        writer.writerow(('Title',
                         'Advertised URL',
                         'Source IP',
                         'Timestamp',
                         'Advertiser ID',
                         'Advertiser name',
                         'Zone'))
        queryset = queryset.select_related('ad', 'ad__advertiser')
        for impression in queryset:
            writer.writerow((impression.ad.title,
                             impression.ad.url,
                             impression.source_ip,
                             impression.click_date.isoformat(),
                             impression.ad.advertiser.pk,
                             impression.ad.advertiser.company_name,
                             impression.ad.zone.title))
        return response
    download_clicks.short_description = "Download selected Ad Clicks"

    def queryset(self, request):
        qs = super(AdClickAdmin, self).queryset(request)
        return qs.select_related('ad').only('ad__title',
                                            'click_date',
                                            'source_ip')


class AdImpressionAdmin(admin.ModelAdmin):
    search_fields = ['ad', 'source_ip']
    list_display = ['ad', 'impression_date', 'source_ip']
    list_filter = ['impression_date']
    date_hierarchy = 'impression_date'
    actions = ['download_impressions']

    def queryset(self, request):
        qs = super(AdImpressionAdmin, self).queryset(request)
        return qs.select_related('ad').only('ad__title',
                                            'impression_date',
                                            'source_ip')

    def download_impressions(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="impressions.csv"'
        writer = csv.writer(response)
        writer.writerow(('Title',
                         'Advertised URL',
                         'Source IP',
                         'Timestamp',
                         'Advertiser ID',
                         'Advertiser name',
                         'Zone'))
        queryset = queryset.select_related('ad', 'ad__advertiser')
        for impression in queryset:
            writer.writerow((impression.ad.title,
                             impression.ad.url,
                             impression.source_ip,
                             impression.impression_date.isoformat(),
                             impression.ad.advertiser.pk,
                             impression.ad.advertiser.company_name,
                             impression.ad.zone.title))
        return response
    download_impressions.short_description = "Download selected Ad Impressions"


class TextAdAdmin(AdBaseAdmin):
    search_fields = ['title', 'url', 'content']


admin.site.register(Advertiser, AdvertiserAdmin)
admin.site.register(AdCategory, AdCategoryAdmin)
admin.site.register(AdZone, AdZoneAdmin)
admin.site.register(TextAd, TextAdAdmin)
admin.site.register(BannerAd, AdBaseAdmin)
admin.site.register(AdClick, AdClickAdmin)
admin.site.register(AdImpression, AdImpressionAdmin)

########NEW FILE########
__FILENAME__ = context_processors
def get_source_ip(request):
    if request.META.has_key('REMOTE_ADDR'):
        return {'from_ip': request.META.get('REMOTE_ADDR')}
    else:
        return {}

########NEW FILE########
__FILENAME__ = managers
import datetime

from django.contrib.sites.models import Site

from django.db import models
try:
    from django.utils.timezone import now
except ImportError:
    now = datetime.datetime.now


class AdManager(models.Manager):
    """ A Custom Manager for ads """

    def get_random_ad(self, ad_zone, ad_category=None):
        """
        Returns a random advert that belongs for the specified ``ad_category``
        and ``ad_zone``.
        If ``ad_category`` is None, the ad will be category independent.
        """
        qs = self.get_query_set().filter(start_showing__lte=now(),
                                         stop_showing__gte=now(),
                                         zone__slug=ad_zone,
                                         sites=Site.objects.get_current().pk
                                         ).select_related('textad',
                                                          'bannerad')
        if ad_category:
            qs = qs.filter(category__slug=ad_category)
        try:
            ad = qs.order_by('?')[0]
        except IndexError:
            return None
        return ad

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Advertiser'
        db.create_table('adzone_advertiser', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('company_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('website', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('adzone', ['Advertiser'])

        # Adding model 'AdCategory'
        db.create_table('adzone_adcategory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('adzone', ['AdCategory'])

        # Adding model 'AdZone'
        db.create_table('adzone_adzone', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('adzone', ['AdZone'])

        # Adding model 'AdBase'
        db.create_table('adzone_adbase', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('since', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('advertiser', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['adzone.Advertiser'])),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['adzone.AdCategory'])),
            ('zone', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['adzone.AdZone'])),
        ))
        db.send_create_signal('adzone', ['AdBase'])

        # Adding model 'AdImpression'
        db.create_table('adzone_adimpression', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('impression_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('source_ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15, null=True, blank=True)),
            ('ad', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['adzone.AdBase'])),
        ))
        db.send_create_signal('adzone', ['AdImpression'])

        # Adding model 'AdClick'
        db.create_table('adzone_adclick', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('click_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('source_ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15, null=True, blank=True)),
            ('ad', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['adzone.AdBase'])),
        ))
        db.send_create_signal('adzone', ['AdClick'])

        # Adding model 'TextAd'
        db.create_table('adzone_textad', (
            ('adbase_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['adzone.AdBase'], unique=True, primary_key=True)),
            ('content', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('adzone', ['TextAd'])

        # Adding model 'BannerAd'
        db.create_table('adzone_bannerad', (
            ('adbase_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['adzone.AdBase'], unique=True, primary_key=True)),
            ('content', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
        ))
        db.send_create_signal('adzone', ['BannerAd'])


    def backwards(self, orm):
        # Deleting model 'Advertiser'
        db.delete_table('adzone_advertiser')

        # Deleting model 'AdCategory'
        db.delete_table('adzone_adcategory')

        # Deleting model 'AdZone'
        db.delete_table('adzone_adzone')

        # Deleting model 'AdBase'
        db.delete_table('adzone_adbase')

        # Deleting model 'AdImpression'
        db.delete_table('adzone_adimpression')

        # Deleting model 'AdClick'
        db.delete_table('adzone_adclick')

        # Deleting model 'TextAd'
        db.delete_table('adzone_textad')

        # Deleting model 'BannerAd'
        db.delete_table('adzone_bannerad')


    models = {
        'adzone.adbase': {
            'Meta': {'object_name': 'AdBase'},
            'advertiser': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.Advertiser']"}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdCategory']"}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'since': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'zone': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdZone']"})
        },
        'adzone.adcategory': {
            'Meta': {'ordering': "('title',)", 'object_name': 'AdCategory'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'adzone.adclick': {
            'Meta': {'object_name': 'AdClick'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdBase']"}),
            'click_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'source_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'adzone.adimpression': {
            'Meta': {'object_name': 'AdImpression'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdBase']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'impression_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'source_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'adzone.advertiser': {
            'Meta': {'ordering': "('company_name',)", 'object_name': 'Advertiser'},
            'company_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'website': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'adzone.adzone': {
            'Meta': {'ordering': "('title',)", 'object_name': 'AdZone'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'adzone.bannerad': {
            'Meta': {'object_name': 'BannerAd', '_ormbases': ['adzone.AdBase']},
            'adbase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['adzone.AdBase']", 'unique': 'True', 'primary_key': 'True'}),
            'content': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        'adzone.textad': {
            'Meta': {'object_name': 'TextAd', '_ormbases': ['adzone.AdBase']},
            'adbase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['adzone.AdBase']", 'unique': 'True', 'primary_key': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {})
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
        }
    }

    complete_apps = ['adzone']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_adbase_start_showing__add_field_adbase_stop_showing
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

# Use a datetime a few days before the max to that timezone changes don't
# cause an OverflowError.
MAX_DATETIME = datetime.datetime.max - datetime.timedelta(days=2)
try:
    from django.utils.timezone import now, make_aware, utc
except ImportError:
    now = datetime.datetime.now
else:
    MAX_DATETIME = make_aware(MAX_DATETIME, utc)


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'AdBase.start_showing'
        db.add_column('adzone_adbase', 'start_showing',
                      self.gf('django.db.models.fields.DateTimeField')(default=now),
                      keep_default=False)

        # Adding field 'AdBase.stop_showing'
        db.add_column('adzone_adbase', 'stop_showing',
                      self.gf('django.db.models.fields.DateTimeField')(default=MAX_DATETIME),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'AdBase.start_showing'
        db.delete_column('adzone_adbase', 'start_showing')

        # Deleting field 'AdBase.stop_showing'
        db.delete_column('adzone_adbase', 'stop_showing')


    models = {
        'adzone.adbase': {
            'Meta': {'object_name': 'AdBase'},
            'advertiser': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.Advertiser']"}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdCategory']"}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'since': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'start_showing': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'stop_showing': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(9999, 12, 29, 0, 0)'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'zone': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdZone']"})
        },
        'adzone.adcategory': {
            'Meta': {'ordering': "('title',)", 'object_name': 'AdCategory'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'adzone.adclick': {
            'Meta': {'object_name': 'AdClick'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdBase']"}),
            'click_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'source_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'adzone.adimpression': {
            'Meta': {'object_name': 'AdImpression'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdBase']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'impression_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'source_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'adzone.advertiser': {
            'Meta': {'ordering': "('company_name',)", 'object_name': 'Advertiser'},
            'company_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'website': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'adzone.adzone': {
            'Meta': {'ordering': "('title',)", 'object_name': 'AdZone'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'adzone.bannerad': {
            'Meta': {'object_name': 'BannerAd', '_ormbases': ['adzone.AdBase']},
            'adbase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['adzone.AdBase']", 'unique': 'True', 'primary_key': 'True'}),
            'content': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        'adzone.textad': {
            'Meta': {'object_name': 'TextAd', '_ormbases': ['adzone.AdBase']},
            'adbase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['adzone.AdBase']", 'unique': 'True', 'primary_key': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {})
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
        }
    }

    complete_apps = ['adzone']
########NEW FILE########
__FILENAME__ = 0003_copy_enabled
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

try:
    from django.utils.timezone import now
except ImportError:
    now = datetime.datetime.now

class Migration(DataMigration):

    def forwards(self, orm):
        # The AdBase objects currently *all* start showing at "now"-ish
        # and stop showing at max_dt. So we just need to update the disabled
        # ads to stop showing "now"-ish.
        AdBase = orm['adzone.adbase']
        ads_disabled = AdBase.objects.filter(enabled=False)
        ads_disabled.update(stop_showing=now())

    def backwards(self, orm):
        "Write your backwards methods here."
        AdBase = orm['adzone.adbase']
        ads_enabled = AdBase.objects.filter(start_showing__lte=now(),
                                            stop_showing__gte=now())
        ads_enabled.update(enabled=True)
        ads_disabled = (AdBase.objects.filter(start_showing__gte=now()) |
                        AdBase.objects.filter(stop_showing__lte=now()))
        ads_disabled.update(enabled=False)

    models = {
        'adzone.adbase': {
            'Meta': {'object_name': 'AdBase'},
            'advertiser': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.Advertiser']"}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdCategory']"}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'since': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'start_showing': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'stop_showing': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(9999, 12, 29, 0, 0)'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'zone': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdZone']"})
        },
        'adzone.adcategory': {
            'Meta': {'ordering': "('title',)", 'object_name': 'AdCategory'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'adzone.adclick': {
            'Meta': {'object_name': 'AdClick'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdBase']"}),
            'click_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'source_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'adzone.adimpression': {
            'Meta': {'object_name': 'AdImpression'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdBase']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'impression_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'source_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'adzone.advertiser': {
            'Meta': {'ordering': "('company_name',)", 'object_name': 'Advertiser'},
            'company_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'website': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'adzone.adzone': {
            'Meta': {'ordering': "('title',)", 'object_name': 'AdZone'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'adzone.bannerad': {
            'Meta': {'object_name': 'BannerAd', '_ormbases': ['adzone.AdBase']},
            'adbase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['adzone.AdBase']", 'unique': 'True', 'primary_key': 'True'}),
            'content': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        'adzone.textad': {
            'Meta': {'object_name': 'TextAd', '_ormbases': ['adzone.AdBase']},
            'adbase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['adzone.AdBase']", 'unique': 'True', 'primary_key': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {})
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
        }
    }

    complete_apps = ['adzone']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0004_auto__del_field_adbase_enabled
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'AdBase.enabled'
        db.delete_column('adzone_adbase', 'enabled')


    def backwards(self, orm):
        # Adding field 'AdBase.enabled'
        db.add_column('adzone_adbase', 'enabled',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    models = {
        'adzone.adbase': {
            'Meta': {'object_name': 'AdBase'},
            'advertiser': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.Advertiser']"}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdCategory']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'since': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'start_showing': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'stop_showing': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(9999, 12, 29, 0, 0)'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'zone': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdZone']"})
        },
        'adzone.adcategory': {
            'Meta': {'ordering': "('title',)", 'object_name': 'AdCategory'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'adzone.adclick': {
            'Meta': {'object_name': 'AdClick'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdBase']"}),
            'click_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'source_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'adzone.adimpression': {
            'Meta': {'object_name': 'AdImpression'},
            'ad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['adzone.AdBase']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'impression_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'source_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'})
        },
        'adzone.advertiser': {
            'Meta': {'ordering': "('company_name',)", 'object_name': 'Advertiser'},
            'company_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'website': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'adzone.adzone': {
            'Meta': {'ordering': "('title',)", 'object_name': 'AdZone'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'adzone.bannerad': {
            'Meta': {'object_name': 'BannerAd', '_ormbases': ['adzone.AdBase']},
            'adbase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['adzone.AdBase']", 'unique': 'True', 'primary_key': 'True'}),
            'content': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        'adzone.textad': {
            'Meta': {'object_name': 'TextAd', '_ormbases': ['adzone.AdBase']},
            'adbase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['adzone.AdBase']", 'unique': 'True', 'primary_key': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {})
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
        }
    }

    complete_apps = ['adzone']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

# © Copyright 2009 Andre Engelbrecht. All Rights Reserved.
# This script is licensed under the BSD Open Source Licence
# Please see the text file LICENCE for more information
# If this script is distributed, it must be accompanied by the Licence

import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from adzone.managers import AdManager

from django.contrib.sites.models import Site

# Use a datetime a few days before the max to that timezone changes don't
# cause an OverflowError.
MAX_DATETIME = datetime.datetime.max - datetime.timedelta(days=2)
try:
    from django.utils.timezone import now, make_aware, utc
except ImportError:
    now = datetime.datetime.now
else:
    MAX_DATETIME = make_aware(MAX_DATETIME, utc)


class Advertiser(models.Model):
    """ A Model for our Advertiser.  """
    company_name = models.CharField(
        verbose_name=_(u'Company Name'), max_length=255)
    website = models.URLField(verbose_name=_(u'Company Site'))
    user = models.ForeignKey(User)

    class Meta:
        verbose_name = _(u'Ad Provider')
        verbose_name_plural = _(u'Advertisers')
        ordering = ('company_name',)

    def __unicode__(self):
        return self.company_name

    def get_website_url(self):
        return self.website


class AdCategory(models.Model):
    """ a Model to hold the different Categories for adverts """
    title = models.CharField(verbose_name=_(u'Title'), max_length=255)
    slug = models.SlugField(verbose_name=_(u'Slug'), unique=True)
    description = models.TextField(verbose_name=_(u'Description'))

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ('title',)

    def __unicode__(self):
        return self.title


class AdZone(models.Model):
    """ a Model that describes the attributes and behaviours of ad zones """
    title = models.CharField(verbose_name=_(u'Title'), max_length=255)
    slug = models.SlugField(verbose_name=_(u'Slug'))
    description = models.TextField(verbose_name=_(u'Description'))

    class Meta:
        verbose_name = 'Zone'
        verbose_name_plural = 'Zones'
        ordering = ('title',)

    def __unicode__(self):
        return self.title


class AdBase(models.Model):
    """
    This is our base model, from which all ads will inherit.
    The manager methods for this model will determine which ads to
    display return etc.
    """
    title = models.CharField(verbose_name=_(u'Title'), max_length=255)
    url = models.URLField(verbose_name=_(u'Advertised URL'))
    since = models.DateTimeField(verbose_name=_(u'Since'), auto_now_add=True)
    updated = models.DateTimeField(verbose_name=_(u'Updated'), auto_now=True)

    start_showing = models.DateTimeField(verbose_name=_(u'Start showing'),
                                         default=now)
    stop_showing = models.DateTimeField(verbose_name=_(u'Stop showing'),
                                        default=MAX_DATETIME)

    # Relations
    advertiser = models.ForeignKey(Advertiser, verbose_name=_("Ad Provider"))
    category = models.ForeignKey(AdCategory,
                                 verbose_name=_("Category"),
                                 blank=True,
                                 null=True)
    zone = models.ForeignKey(AdZone, verbose_name=_("Zone"))

    # Our Custom Manager
    objects = AdManager()

    sites = models.ManyToManyField(Site, verbose_name=(u"Sites"))

    class Meta:
        verbose_name = _('Ad Base')
        verbose_name_plural = _('Ad Bases')

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ('adzone_ad_view', [self.id])


class AdImpression(models.Model):
    """
    The AdImpression Model will record every time the ad is loaded on a page
    """
    impression_date = models.DateTimeField(
        verbose_name=_(u'When'), auto_now_add=True)
    source_ip = models.IPAddressField(
        verbose_name=_(u'Who'), null=True, blank=True)
    ad = models.ForeignKey(AdBase)

    class Meta:
        verbose_name = _('Ad Impression')
        verbose_name_plural = _('Ad Impressions')


class AdClick(models.Model):
    """
    The AdClick model will record every click that a add gets
    """
    click_date = models.DateTimeField(
        verbose_name=_(u'When'), auto_now_add=True)
    source_ip = models.IPAddressField(
        verbose_name=_(u'Who'), null=True, blank=True)
    ad = models.ForeignKey(AdBase)

    class Meta:
        verbose_name = _('Ad Click')
        verbose_name_plural = _('Ad Clicks')


# Example Ad Types
class TextAd(AdBase):
    """ A most basic, text based advert """
    content = models.TextField(verbose_name=_(u'Content'))


class BannerAd(AdBase):
    """ A standard banner Ad """
    content = models.ImageField(
        verbose_name=_(u'Content'), upload_to="adzone/bannerads/")

########NEW FILE########
__FILENAME__ = adzone_tags
# -*- coding: utf-8 -*-

# © Copyright 2009 Andre Engelbrecht. All Rights Reserved.
# This script is licensed under the BSD Open Source Licence
# Please see the text file LICENCE for more information
# If this script is distributed, it must be accompanied by the Licence

from datetime import datetime
from django import template
from adzone.models import AdBase, AdImpression

register = template.Library()


@register.inclusion_tag('adzone/ad_tag.html', takes_context=True)
def random_zone_ad(context, ad_zone):
    """
    Returns a random advert for ``ad_zone``.
    The advert returned is independent of the category

    In order for the impression to be saved add the following
    to the TEMPLATE_CONTEXT_PROCESSORS:

    'adzone.context_processors.get_source_ip'

    Tag usage:
    {% load adzone_tags %}
    {% random_zone_ad 'zone_slug' %}

    """
    to_return = {}

    # Retrieve a random ad for the zone
    ad = AdBase.objects.get_random_ad(ad_zone)
    to_return['ad'] = ad

    # Record a impression for the ad
    if context.has_key('from_ip') and ad:
        from_ip = context.get('from_ip')
        try:
            impression = AdImpression(
                ad=ad, impression_date=datetime.now(), source_ip=from_ip)
            impression.save()
        except:
            pass
    return to_return


@register.inclusion_tag('adzone/ad_tag.html', takes_context=True)
def random_category_ad(context, ad_zone, ad_category):
    """
    Returns a random advert from the specified category.

    Usage:
    {% load adzone_tags %}
    {% random_category_ad 'zone_slug' 'my_category_slug' %}

    """
    to_return = {}

    # Retrieve a random ad for the category and zone
    ad = AdBase.objects.get_random_ad(ad_zone, ad_category)
    to_return['ad'] = ad

    # Record a impression for the ad
    if context.has_key('from_ip') and ad:
        from_ip = context.get('from_ip')
        try:
            impression = AdImpression(
                ad=ad, impression_date=datetime.now(), source_ip=from_ip)
            impression.save()
        except:
            pass
    return to_return

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.contrib.auth.models import User
from django.template import Template
from django.template.response import SimpleTemplateResponse
from django.utils import timezone

from adzone.models import Advertiser, AdCategory, AdZone, AdBase
from adzone.models import AdImpression, AdClick
from adzone.managers import AdManager
from adzone.templatetags.adzone_tags import random_zone_ad, random_category_ad


# Helper functions to help setting up the tests
user = lambda: User.objects.create_user('test', 'test@example.com', 'secret')


def datenow():
    return timezone.now()


def create_objects():
    """ Simple helper to create advertiser, category and zone """
    advertiser = Advertiser.objects.create(
        company_name='Advertiser Name 1',
        website='http://example.com/', user=user())

    category = AdCategory.objects.create(
        title='Internet Services',
        slug='internet-services',
        description='All internet based services')

    adzone = AdZone.objects.create(
        title='Sidebar',
        slug='sidebar',
        description='Sidebar Zone Description')

    return advertiser, category, adzone


def create_advert():
    """ Simple helper to create a single ad """
    advertiser, category, zone = create_objects()
    ad = AdBase.objects.create(
        title='Ad Title',
        url='www.example.com',
        advertiser=advertiser,
        category=category,
        zone=zone,
    )
    return ad


# Now follows the actual tests
class AdvertiserTestCase(TestCase):

    def test_model(self):
        Advertiser(
            company_name='Advertiser Name 1',
            website='http://example.com/',
            user=user())

    def test_get_website_url(self):
        advertiser = Advertiser(
            company_name='Advertiser Name 1',
            website='http://example.com/',
            user=user())

        self.assertEqual(
            'http://example.com/',
            advertiser.get_website_url())


class AdCategoryTestCase(TestCase):

    def test_model(self):
        AdCategory(
            title='Internet Services',
            slug='internet-services',
            description='All internet based services')


class AdZoneTestCase(TestCase):

    def test_model(self):
        AdZone(
            title='Ad Zone Title',
            slug='adzone',
            description='Ad Zone Description')


class AdBaseTestCase(TestCase):

    urls = 'adzone.urls'

    def test_model(self):
        advertiser, category, zone = create_objects()
        AdBase(
            title='Ad Title',
            url='www.example.com',
            advertiser=advertiser,
            category=category,
            zone=zone
        )

    def test_unicode(self):
        advert = create_advert()
        self.assertEqual('Ad Title', str(advert))

    def test_absolute_url(self):
        advert = create_advert()
        self.assertEqual('/view/1/', advert.get_absolute_url())


class AdManagerTestCase(TestCase):

    def setUp(self):
        # Create two categories and two adverts
        advertiser, category, zone = create_objects()
        category2 = AdCategory.objects.create(
            title='Category 2',
            slug='category-2',
            description='Category 2 description'
        )
        AdBase.objects.create(
            title='Ad Title',
            url='www.example.com',
            advertiser=advertiser,
            category=category,
            zone=zone
        )
        AdBase.objects.create(
            title='Ad 2 Title',
            url='www.example2.com',
            advertiser=advertiser,
            category=category2,
            zone=zone
        )

    def test_manager_exists(self):
        AdManager

    def test_get_random_ad(self):
        advert = AdBase.objects.get_random_ad('sidebar')
        self.assertIn(advert.id, [1, 2])

    def test_get_random_ad_by_category(self):
        advert = AdBase.objects.get_random_ad('sidebar',
                                              ad_category='category-2')
        self.assertIn(advert.id, [2])


class AdImpressionTestCase(TestCase):

    def test_model(self):
        advert = create_advert()
        AdImpression(
            impression_date=datenow(),
            source_ip='127.0.0.1',
            ad=advert,
        )


class AdClickTestCase(TestCase):

    def test_model(self):
        advert = create_advert()
        AdClick(
            click_date=datenow(),
            source_ip='127.0.0.1',
            ad=advert,
        )


class TemplateTagsTestCase(TestCase):

    def test_random_zone_ad_creates_impression(self):
        create_advert()
        random_zone_ad({'from_ip': '127.0.0.1'}, 'sidebar')
        self.assertEqual(AdImpression.objects.all().count(), 1)

    def test_random_zone_ad_renders(self):
        template = Template("{% load adzone_tags %}{% random_zone_ad 'sidebar' %}")
        response = SimpleTemplateResponse(template)
        response.render()
        self.assertTrue(response.is_rendered)

    def test_random_category_ad_creates_impression(self):
        create_advert()
        random_category_ad(
            {'from_ip': '127.0.0.1'}, 'sidebar', 'internet-services')
        self.assertEqual(AdImpression.objects.all().count(), 1)

    def test_random_category_ad_renders(self):
        template = Template("{% load adzone_tags %}{% random_category_ad 'sidebar' 'internet-services' %}")
        response = SimpleTemplateResponse(template)
        response.render()
        self.assertTrue(response.is_rendered)


class AdViewTestCase(TestCase):

    urls = 'adzone.urls'

    def test_request_redirects(self):
        create_advert()
        response = self.client.get('/view/1/')
        self.assertEqual(response.status_code, 302)

    def test_request_redirect_chain(self):
        create_advert()
        response = self.client.get('/view/1/', follow=True)
        chain = [('http://www.example.com', 302), ]
        self.assertEqual(response.redirect_chain, chain)

    def test_request_creates_click(self):
        create_advert()
        self.client.get('/view/1/')  # dont need response for this test
        self.assertEqual(AdClick.objects.filter(ad__id=1).count(), 1)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from adzone.views import ad_view

urlpatterns = patterns('',
    url(r'^view/(?P<id>[\d]+)/$', ad_view, name='adzone_ad_view'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

# © Copyright 2009 Andre Engelbrecht. All Rights Reserved.
# This script is licensed under the BSD Open Source Licence
# Please see the text file LICENCE for more information
# If this script is distributed, it must be accompanied by the Licence

from datetime import datetime

from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect

from adzone.models import AdBase, AdClick


def ad_view(request, id):
    """ Record the click in the database, then redirect to ad url """
    ad = get_object_or_404(AdBase, id=id)

    click = AdClick.objects.create(
        ad=ad,
        click_date=datetime.now(),
        source_ip=request.META.get('REMOTE_ADDR', '')
    )
    click.save()

    redirect_url = ad.url
    if not redirect_url.startswith('http://'):
        # Add http:// to the url so that the browser redirects correctly
        redirect_url = 'http://' + redirect_url

    return HttpResponseRedirect(redirect_url)

########NEW FILE########
