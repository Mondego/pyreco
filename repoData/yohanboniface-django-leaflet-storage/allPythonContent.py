__FILENAME__ = admin
from django.contrib.gis import admin
from .models import Map, DataLayer, Pictogram, TileLayer, Licence


class TileLayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'rank', )
    list_editable = ('rank', )

admin.site.register(Map, admin.OSMGeoAdmin)
admin.site.register(DataLayer)
admin.site.register(Pictogram)
admin.site.register(TileLayer, TileLayerAdmin)
admin.site.register(Licence)

########NEW FILE########
__FILENAME__ = decorators
from functools import wraps

from django.core.urlresolvers import reverse_lazy
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.conf import settings

from .views import simple_json_response
from .models import Map


LOGIN_URL = getattr(settings, "LOGIN_URL", "login")
LOGIN_URL = reverse_lazy(LOGIN_URL) if not LOGIN_URL.startswith("/") else LOGIN_URL


def login_required_if_not_anonymous_allowed(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if (not getattr(settings, "LEAFLET_STORAGE_ALLOW_ANONYMOUS", False)
                and not request.user.is_authenticated()):
            return simple_json_response(login_required=str(LOGIN_URL))
        return view_func(request, *args, **kwargs)
    return wrapper


def map_permissions_check(view_func):
    """
    Used for URLs dealing with the map.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        map_inst = get_object_or_404(Map, pk=kwargs['map_id'])
        user = request.user
        kwargs['map_inst'] = map_inst  # Avoid rerequesting the map in the view
        if map_inst.edit_status >= map_inst.EDITORS:
            can_edit = map_inst.can_edit(user=user, request=request)
            if not can_edit:
                if not user.is_authenticated():
                    return simple_json_response(login_required=str(LOGIN_URL))
                else:
                    return HttpResponseForbidden('Action not allowed for user.')
        return view_func(request, *args, **kwargs)
    return wrapper


def jsonize_view(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        response_kwargs = {}
        if hasattr(response, 'rendered_content'):
            response_kwargs['html'] = response.rendered_content
        if response.has_header('location'):
            response_kwargs['redirect'] = response['location']
        return simple_json_response(**response_kwargs)
    return wrapper

########NEW FILE########
__FILENAME__ = fields
import simplejson

from django.db import models
from django.conf import settings


class DictField(models.TextField):
    """
    A very simple field to store JSON in db.
    """

    __metaclass__ = models.SubfieldBase

    def get_prep_value(self, value):
        return simplejson.dumps(value)

    def to_python(self, value):
        if not value:
            value = {}
        if isinstance(value, basestring):
            return simplejson.loads(value)
        else:
            return value

if "south" in settings.INSTALLED_APPS:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^leaflet_storage\.fields\.DictField"])

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-

from django import forms
from django.contrib.gis.geos import Point
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import slugify
from django.conf import settings
from django.forms.util import ErrorList

from .models import Map, DataLayer

DEFAULT_LATITUDE = settings.LEAFLET_LATITUDE if hasattr(settings, "LEAFLET_LATITUDE") else 51
DEFAULT_LONGITUDE = settings.LEAFLET_LONGITUDE if hasattr(settings, "LEAFLET_LONGITUDE") else 2
DEFAULT_CENTER = Point(DEFAULT_LONGITUDE, DEFAULT_LATITUDE)


class FlatErrorList(ErrorList):
    def __unicode__(self):
        return self.flat()

    def flat(self):
        if not self:
            return u''
        return u' — '.join([e for e in self])


class UpdateMapPermissionsForm(forms.ModelForm):

    class Meta:
        model = Map
        fields = ('edit_status', 'editors', 'share_status')


class AnonymousMapPermissionsForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(AnonymousMapPermissionsForm, self).__init__(*args, **kwargs)
        full_secret_link = "%s%s" % (settings.SITE_URL, self.instance.get_anonymous_edit_url())
        help_text = _('Secret edit link is %s') % full_secret_link
        self.fields['edit_status'].help_text = _(help_text)

    STATUS = (
        (Map.ANONYMOUS, _('Everyone can edit')),
        (Map.OWNER, _('Only editable with secret edit link'))
    )

    edit_status = forms.ChoiceField(STATUS)

    class Meta:
        model = Map
        fields = ('edit_status', )


class DataLayerForm(forms.ModelForm):

    class Meta:
        model = DataLayer
        fields = ('geojson', 'name', 'display_on_load')


class MapSettingsForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(MapSettingsForm, self).__init__(*args, **kwargs)
        self.fields["slug"].required = False

    def clean_slug(self):
        slug = self.cleaned_data.get('slug', None)
        name = self.cleaned_data.get('name', None)
        if not slug and name:
            # If name is empty, don't do nothing, validation will raise
            # later on the process because name is required
            self.cleaned_data['slug'] = slugify(name) or "map"
            return self.cleaned_data['slug'][:50]
        else:
            return ""

    def clean_center(self):
        if not self.cleaned_data['center']:
            point = DEFAULT_CENTER
            self.cleaned_data['center'] = point
        return self.cleaned_data['center']

    class Meta:
        fields = ('settings', 'name', 'center', 'slug')
        model = Map

########NEW FILE########
__FILENAME__ = storagei18n
import io
import os

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string


class Command(BaseCommand):

    def handle(self, *args, **options):
        for code, name in settings.LANGUAGES:
            print "Processing", name
            path = finders.find('storage/src/locale/{code}.json'.format(code=code))
            if not path:
                print "No file at", path, "Skipping"
            else:
                with io.open(path, "r", encoding="utf-8") as f:
                    print "Found file", path
                    self.render(code, f.read())

    def render(self, code, json):
        path = os.path.join(
            settings.STATIC_ROOT,
            "storage/src/locale/",
            "{code}.js".format(code=code)
        )
        with io.open(path, "w", encoding="utf-8") as f:
            content = render_to_string('leaflet_storage/locale.js', {
                "locale": json,
                "locale_code": code
            })
            print "Exporting to", path
            f.write(content)
########NEW FILE########
__FILENAME__ = managers
from django.contrib.gis.db import models


class PublicManager(models.GeoManager):

    def get_query_set(self):
        return super(PublicManager, self).get_query_set().filter(share_status=self.model.PUBLIC)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Licence'
        db.create_table('leaflet_storage_licence', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('details', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal('leaflet_storage', ['Licence'])

        # Adding model 'TileLayer'
        db.create_table('leaflet_storage_tilelayer', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('url_template', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('minZoom', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('maxZoom', self.gf('django.db.models.fields.IntegerField')(default=18)),
            ('attribution', self.gf('django.db.models.fields.CharField')(max_length=300)),
        ))
        db.send_create_signal('leaflet_storage', ['TileLayer'])

        # Adding model 'Map'
        db.create_table('leaflet_storage_map', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('center', self.gf('django.contrib.gis.db.models.fields.PointField')(geography=True)),
            ('zoom', self.gf('django.db.models.fields.IntegerField')(default=7)),
            ('locate', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('licence', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.Licence'], on_delete=models.SET_DEFAULT)),
            ('modified_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(related_name='owned_maps', to=orm['auth.User'])),
            ('edit_status', self.gf('django.db.models.fields.SmallIntegerField')(default=3)),
        ))
        db.send_create_signal('leaflet_storage', ['Map'])

        # Adding M2M table for field editors on 'Map'
        db.create_table('leaflet_storage_map_editors', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('map', models.ForeignKey(orm['leaflet_storage.map'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('leaflet_storage_map_editors', ['map_id', 'user_id'])

        # Adding model 'MapToTileLayer'
        db.create_table('leaflet_storage_maptotilelayer', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('tilelayer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.TileLayer'])),
            ('map', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.Map'])),
            ('rank', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('leaflet_storage', ['MapToTileLayer'])

        # Adding model 'Pictogram'
        db.create_table('leaflet_storage_pictogram', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('attribution', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('pictogram', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
        ))
        db.send_create_signal('leaflet_storage', ['Pictogram'])

        # Adding model 'Category'
        db.create_table('leaflet_storage_category', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('map', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.Map'])),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('color', self.gf('django.db.models.fields.CharField')(default='DarkBlue', max_length=32)),
            ('pictogram', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.Pictogram'], null=True, blank=True)),
            ('icon_class', self.gf('django.db.models.fields.CharField')(default='Default', max_length=32)),
            ('display_on_load', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('rank', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('leaflet_storage', ['Category'])

        # Adding model 'Marker'
        db.create_table('leaflet_storage_marker', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('color', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.Category'])),
            ('latlng', self.gf('django.contrib.gis.db.models.fields.PointField')(geography=True)),
        ))
        db.send_create_signal('leaflet_storage', ['Marker'])

        # Adding model 'Polyline'
        db.create_table('leaflet_storage_polyline', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('color', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.Category'])),
            ('latlng', self.gf('django.contrib.gis.db.models.fields.LineStringField')(geography=True)),
        ))
        db.send_create_signal('leaflet_storage', ['Polyline'])

        # Adding model 'Polygon'
        db.create_table('leaflet_storage_polygon', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('color', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.Category'])),
            ('latlng', self.gf('django.contrib.gis.db.models.fields.PolygonField')(geography=True)),
        ))
        db.send_create_signal('leaflet_storage', ['Polygon'])


    def backwards(self, orm):
        # Deleting model 'Licence'
        db.delete_table('leaflet_storage_licence')

        # Deleting model 'TileLayer'
        db.delete_table('leaflet_storage_tilelayer')

        # Deleting model 'Map'
        db.delete_table('leaflet_storage_map')

        # Removing M2M table for field editors on 'Map'
        db.delete_table('leaflet_storage_map_editors')

        # Deleting model 'MapToTileLayer'
        db.delete_table('leaflet_storage_maptotilelayer')

        # Deleting model 'Pictogram'
        db.delete_table('leaflet_storage_pictogram')

        # Deleting model 'Category'
        db.delete_table('leaflet_storage_category')

        # Deleting model 'Marker'
        db.delete_table('leaflet_storage_marker')

        # Deleting model 'Polyline'
        db.delete_table('leaflet_storage_polyline')

        # Deleting model 'Polygon'
        db.delete_table('leaflet_storage_polygon')


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
        'leaflet_storage.category': {
            'Meta': {'ordering': "['rank']", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'DarkBlue'", 'max_length': '32'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'default': "'Default'", 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.licence': {
            'Meta': {'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.map': {
            'Meta': {'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'owned_maps'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['leaflet_storage.TileLayer']", 'through': "orm['leaflet_storage.MapToTileLayer']", 'symmetrical': 'False'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        'leaflet_storage.maptotilelayer': {
            'Meta': {'ordering': "['rank', 'tilelayer__name']", 'object_name': 'MapToTileLayer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.TileLayer']"})
        },
        'leaflet_storage.marker': {
            'Meta': {'object_name': 'Marker'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.pictogram': {
            'Meta': {'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        'leaflet_storage.polygon': {
            'Meta': {'object_name': 'Polygon'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.polyline': {
            'Meta': {'object_name': 'Polyline'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.tilelayer': {
            'Meta': {'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_map_settings
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Map.settings'
        db.add_column('leaflet_storage_map', 'settings',
                      self.gf('leaflet_storage.fields.DictField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Map.settings'
        db.delete_column('leaflet_storage_map', 'settings')


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
        'leaflet_storage.category': {
            'Meta': {'ordering': "['rank']", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'DarkBlue'", 'max_length': '32'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'default': "'Default'", 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.licence': {
            'Meta': {'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.map': {
            'Meta': {'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'owned_maps'", 'to': "orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['leaflet_storage.TileLayer']", 'through': "orm['leaflet_storage.MapToTileLayer']", 'symmetrical': 'False'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        'leaflet_storage.maptotilelayer': {
            'Meta': {'ordering': "['rank', 'tilelayer__name']", 'object_name': 'MapToTileLayer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.TileLayer']"})
        },
        'leaflet_storage.marker': {
            'Meta': {'object_name': 'Marker'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.pictogram': {
            'Meta': {'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        'leaflet_storage.polygon': {
            'Meta': {'object_name': 'Polygon'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.polyline': {
            'Meta': {'object_name': 'Polyline'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.tilelayer': {
            'Meta': {'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_polyline_options__add_field_category_options__add_fiel
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Polyline.options'
        db.add_column('leaflet_storage_polyline', 'options',
                      self.gf('leaflet_storage.fields.DictField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Category.options'
        db.add_column('leaflet_storage_category', 'options',
                      self.gf('leaflet_storage.fields.DictField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Polygon.options'
        db.add_column('leaflet_storage_polygon', 'options',
                      self.gf('leaflet_storage.fields.DictField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Marker.options'
        db.add_column('leaflet_storage_marker', 'options',
                      self.gf('leaflet_storage.fields.DictField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Polyline.options'
        db.delete_column('leaflet_storage_polyline', 'options')

        # Deleting field 'Category.options'
        db.delete_column('leaflet_storage_category', 'options')

        # Deleting field 'Polygon.options'
        db.delete_column('leaflet_storage_polygon', 'options')

        # Deleting field 'Marker.options'
        db.delete_column('leaflet_storage_marker', 'options')


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
        'leaflet_storage.category': {
            'Meta': {'ordering': "['rank']", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'DarkBlue'", 'max_length': '32'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'default': "'Default'", 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.licence': {
            'Meta': {'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.map': {
            'Meta': {'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'owned_maps'", 'to': "orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['leaflet_storage.TileLayer']", 'through': "orm['leaflet_storage.MapToTileLayer']", 'symmetrical': 'False'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        'leaflet_storage.maptotilelayer': {
            'Meta': {'ordering': "['rank', 'tilelayer__name']", 'object_name': 'MapToTileLayer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.TileLayer']"})
        },
        'leaflet_storage.marker': {
            'Meta': {'object_name': 'Marker'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.pictogram': {
            'Meta': {'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        'leaflet_storage.polygon': {
            'Meta': {'object_name': 'Polygon'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.polyline': {
            'Meta': {'object_name': 'Polyline'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.tilelayer': {
            'Meta': {'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0004_migrate_color_to_options
# -*- coding: utf-8 -*-
from south.v2 import DataMigration


class Migration(DataMigration):

    def forwards(self, orm):
        for obj in orm['leaflet_storage.Polyline'].objects.filter(color__isnull=False):
            obj.options['color'] = obj.color
            obj.save()

        for obj in orm['leaflet_storage.Polygon'].objects.filter(color__isnull=False):
            obj.options['color'] = obj.color
            obj.save()

        for obj in orm['leaflet_storage.Marker'].objects.filter(color__isnull=False):
            obj.options['color'] = obj.color
            obj.save()

        for obj in orm['leaflet_storage.Category'].objects.filter(color__isnull=False):
            obj.options['color'] = obj.color
            obj.save()

    def backwards(self, orm):
        for obj in orm['leaflet_storage.Polyline'].objects.all():
            if "color" in obj.options:
                obj.color = obj.options['color']
                obj.save()

        for obj in orm['leaflet_storage.Polygon'].objects.all():
            if "color" in obj.options:
                obj.color = obj.options['color']
                obj.save()

        for obj in orm['leaflet_storage.Marker'].objects.all():
            if "color" in obj.options:
                obj.color = obj.options['color']
                obj.save()

        for obj in orm['leaflet_storage.Category'].objects.all():
            if "color" in obj.options:
                obj.color = obj.options['color']
                obj.save()

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
        'leaflet_storage.category': {
            'Meta': {'ordering': "['rank']", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'DarkBlue'", 'max_length': '32'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'default': "'Default'", 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.licence': {
            'Meta': {'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.map': {
            'Meta': {'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'owned_maps'", 'to': "orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['leaflet_storage.TileLayer']", 'through': "orm['leaflet_storage.MapToTileLayer']", 'symmetrical': 'False'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        'leaflet_storage.maptotilelayer': {
            'Meta': {'ordering': "['rank', 'tilelayer__name']", 'object_name': 'MapToTileLayer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.TileLayer']"})
        },
        'leaflet_storage.marker': {
            'Meta': {'object_name': 'Marker'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.pictogram': {
            'Meta': {'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        'leaflet_storage.polygon': {
            'Meta': {'object_name': 'Polygon'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.polyline': {
            'Meta': {'object_name': 'Polyline'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.tilelayer': {
            'Meta': {'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0005_auto__del_field_polyline_color__del_field_category_color__del_field_po
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Polyline.color'
        db.delete_column('leaflet_storage_polyline', 'color')

        # Deleting field 'Category.color'
        db.delete_column('leaflet_storage_category', 'color')

        # Deleting field 'Polygon.color'
        db.delete_column('leaflet_storage_polygon', 'color')

        # Deleting field 'Marker.color'
        db.delete_column('leaflet_storage_marker', 'color')


    def backwards(self, orm):
        # Adding field 'Polyline.color'
        db.add_column('leaflet_storage_polyline', 'color',
                      self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Category.color'
        db.add_column('leaflet_storage_category', 'color',
                      self.gf('django.db.models.fields.CharField')(default='DarkBlue', max_length=32),
                      keep_default=False)

        # Adding field 'Polygon.color'
        db.add_column('leaflet_storage_polygon', 'color',
                      self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Marker.color'
        db.add_column('leaflet_storage_marker', 'color',
                      self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True),
                      keep_default=False)


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
        'leaflet_storage.category': {
            'Meta': {'ordering': "['rank']", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'default': "'Default'", 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.licence': {
            'Meta': {'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.map': {
            'Meta': {'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'owned_maps'", 'to': "orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['leaflet_storage.TileLayer']", 'through': "orm['leaflet_storage.MapToTileLayer']", 'symmetrical': 'False'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        'leaflet_storage.maptotilelayer': {
            'Meta': {'ordering': "['rank', 'tilelayer__name']", 'object_name': 'MapToTileLayer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.TileLayer']"})
        },
        'leaflet_storage.marker': {
            'Meta': {'object_name': 'Marker'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.pictogram': {
            'Meta': {'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        'leaflet_storage.polygon': {
            'Meta': {'object_name': 'Polygon'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.polyline': {
            'Meta': {'object_name': 'Polyline'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.tilelayer': {
            'Meta': {'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0006_auto__del_field_category_rank
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Category.rank'
        db.delete_column('leaflet_storage_category', 'rank')


    def backwards(self, orm):
        # Adding field 'Category.rank'
        db.add_column('leaflet_storage_category', 'rank',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)


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
        'leaflet_storage.category': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'default': "'Default'", 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'owned_maps'", 'to': "orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['leaflet_storage.TileLayer']", 'through': "orm['leaflet_storage.MapToTileLayer']", 'symmetrical': 'False'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        'leaflet_storage.maptotilelayer': {
            'Meta': {'ordering': "['rank', 'tilelayer__name']", 'object_name': 'MapToTileLayer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.TileLayer']"})
        },
        'leaflet_storage.marker': {
            'Meta': {'object_name': 'Marker'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        'leaflet_storage.polygon': {
            'Meta': {'object_name': 'Polygon'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.polyline': {
            'Meta': {'object_name': 'Polyline'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0007_auto__chg_field_category_icon_class__add_field_marker_pictogram__add_f
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Category.icon_class'
        db.alter_column('leaflet_storage_category', 'icon_class', self.gf('django.db.models.fields.CharField')(max_length=32, null=True))
        # Adding field 'Marker.pictogram'
        db.add_column('leaflet_storage_marker', 'pictogram',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.Pictogram'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Marker.icon_class'
        db.add_column('leaflet_storage_marker', 'icon_class',
                      self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):

        # Changing field 'Category.icon_class'
        db.alter_column('leaflet_storage_category', 'icon_class', self.gf('django.db.models.fields.CharField')(max_length=32))
        # Deleting field 'Marker.pictogram'
        db.delete_column('leaflet_storage_marker', 'pictogram_id')

        # Deleting field 'Marker.icon_class'
        db.delete_column('leaflet_storage_marker', 'icon_class')


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
        'leaflet_storage.category': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'owned_maps'", 'to': "orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['leaflet_storage.TileLayer']", 'through': "orm['leaflet_storage.MapToTileLayer']", 'symmetrical': 'False'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        'leaflet_storage.maptotilelayer': {
            'Meta': {'ordering': "['rank', 'tilelayer__name']", 'object_name': 'MapToTileLayer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.TileLayer']"})
        },
        'leaflet_storage.marker': {
            'Meta': {'object_name': 'Marker'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        'leaflet_storage.polygon': {
            'Meta': {'object_name': 'Polygon'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.polyline': {
            'Meta': {'object_name': 'Polyline'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0008_auto__chg_field_map_owner
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Map.owner'
        db.alter_column('leaflet_storage_map', 'owner_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['auth.User']))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Map.owner'
        raise RuntimeError("Cannot reverse this migration. 'Map.owner' and its values cannot be restored.")

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
        'leaflet_storage.category': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_maps'", 'null': 'True', 'to': "orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['leaflet_storage.TileLayer']", 'through': "orm['leaflet_storage.MapToTileLayer']", 'symmetrical': 'False'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        'leaflet_storage.maptotilelayer': {
            'Meta': {'ordering': "['rank', 'tilelayer__name']", 'object_name': 'MapToTileLayer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Map']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.TileLayer']"})
        },
        'leaflet_storage.marker': {
            'Meta': {'object_name': 'Marker'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        'leaflet_storage.polygon': {
            'Meta': {'object_name': 'Polygon'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.polyline': {
            'Meta': {'object_name': 'Polyline'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0009_auto__add_field_tilelayer_rank
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'TileLayer.rank'
        db.add_column(u'leaflet_storage_tilelayer', 'rank',
                      self.gf('django.db.models.fields.SmallIntegerField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'TileLayer.rank'
        db.delete_column(u'leaflet_storage_tilelayer', 'rank')


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
        u'leaflet_storage.category': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_maps'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayers': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['leaflet_storage.TileLayer']", 'through': u"orm['leaflet_storage.MapToTileLayer']", 'symmetrical': 'False'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        u'leaflet_storage.maptotilelayer': {
            'Meta': {'ordering': "['rank', 'tilelayer__name']", 'object_name': 'MapToTileLayer'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.TileLayer']"})
        },
        u'leaflet_storage.marker': {
            'Meta': {'object_name': 'Marker'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        u'leaflet_storage.polygon': {
            'Meta': {'object_name': 'Polygon'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.polyline': {
            'Meta': {'object_name': 'Polyline'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0010_rename_category_to_datalayer
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Renaming model 'Category' to 'DataLayer'
        db.rename_table(u'leaflet_storage_category', u'leaflet_storage_datalayer')
        db.send_create_signal(u'leaflet_storage', ['DataLayer'])

        # Renaming fields '.category_id' to '.datalayer_id'
        db.rename_column(u'leaflet_storage_polyline', 'category_id', 'datalayer_id')
        db.rename_column(u'leaflet_storage_polygon', 'category_id', 'datalayer_id')
        db.rename_column(u'leaflet_storage_marker', 'category_id', 'datalayer_id')

    def backwards(self, orm):
        # Renaming model 'Category' to 'DataLayer'
        db.rename_table(u'leaflet_storage_datalayer', u'leaflet_storage_category')
        db.send_create_signal(u'leaflet_storage', ['Category'])

        # Renaming fields '.category_id' to '.datalayer_id'
        db.rename_column(u'leaflet_storage_polyline', 'datalayer_id', 'category_id')
        db.rename_column(u'leaflet_storage_polygon', 'datalayer_id', 'category_id')
        db.rename_column(u'leaflet_storage_marker', 'datalayer_id', 'category_id')

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
        u'leaflet_storage.datalayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'DataLayer'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_maps'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayers': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['leaflet_storage.TileLayer']", 'through': u"orm['leaflet_storage.MapToTileLayer']", 'symmetrical': 'False'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        u'leaflet_storage.maptotilelayer': {
            'Meta': {'ordering': "['rank', 'tilelayer__name']", 'object_name': 'MapToTileLayer'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.TileLayer']"})
        },
        u'leaflet_storage.marker': {
            'Meta': {'object_name': 'Marker'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        u'leaflet_storage.polygon': {
            'Meta': {'object_name': 'Polygon'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.polyline': {
            'Meta': {'object_name': 'Polyline'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('rank', 'name')", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']

########NEW FILE########
__FILENAME__ = 0011_auto__add_field_map_tilelayer
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Map.tilelayer'
        db.add_column(u'leaflet_storage_map', 'tilelayer',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='maps', null=True, to=orm['leaflet_storage.TileLayer']),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Map.tilelayer'
        db.delete_column(u'leaflet_storage_map', 'tilelayer_id')


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
        u'leaflet_storage.datalayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'DataLayer'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_maps'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'maps'", 'null': 'True', 'to': u"orm['leaflet_storage.TileLayer']"}),
            'tilelayers': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'old_map_relations'", 'symmetrical': 'False', 'through': u"orm['leaflet_storage.MapToTileLayer']", 'to': u"orm['leaflet_storage.TileLayer']"}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        u'leaflet_storage.maptotilelayer': {
            'Meta': {'ordering': "['rank', 'tilelayer__name']", 'object_name': 'MapToTileLayer'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.TileLayer']"})
        },
        u'leaflet_storage.marker': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Marker'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        u'leaflet_storage.polygon': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Polygon'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.polyline': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Polyline'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('rank', 'name')", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0012_migrate_tilelayer
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Remember to use orm['appname.ModelName'] rather than "from appname.models..."
        for obj in orm['leaflet_storage.Map'].objects.order_by('pk'):
            try:
                tilelayer = obj.tilelayers.all()[0]
            except:
                tilelayer = orm['leaflet_storage.TileLayer'].get_default()
            obj.tilelayer = tilelayer
            obj.save()

    def backwards(self, orm):
        "Write your backwards methods here."
        for obj in orm['leaflet_storage.Map'].objects.all():
            orm['leaflet_storage.MapToTileLayer'].objects.create(
                map=obj,
                tilelayer=obj.tilelayer or orm['leaflet_storage.TileLayer'].get_default()
            )

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
        u'leaflet_storage.datalayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'DataLayer'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_maps'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'maps'", 'null': 'True', 'to': u"orm['leaflet_storage.TileLayer']"}),
            'tilelayers': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'old_map_relations'", 'symmetrical': 'False', 'through': u"orm['leaflet_storage.MapToTileLayer']", 'to': u"orm['leaflet_storage.TileLayer']"}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        u'leaflet_storage.maptotilelayer': {
            'Meta': {'ordering': "['rank', 'tilelayer__name']", 'object_name': 'MapToTileLayer'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.TileLayer']"})
        },
        u'leaflet_storage.marker': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Marker'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        u'leaflet_storage.polygon': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Polygon'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.polyline': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Polyline'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('rank', 'name')", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0013_auto__del_maptotilelayer
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'MapToTileLayer'
        db.delete_table(u'leaflet_storage_maptotilelayer')


    def backwards(self, orm):
        # Adding model 'MapToTileLayer'
        db.create_table(u'leaflet_storage_maptotilelayer', (
            ('map', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.Map'])),
            ('tilelayer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.TileLayer'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('rank', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'leaflet_storage', ['MapToTileLayer'])


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
        u'leaflet_storage.datalayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'DataLayer'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_maps'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'maps'", 'null': 'True', 'to': u"orm['leaflet_storage.TileLayer']"}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        u'leaflet_storage.marker': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Marker'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        u'leaflet_storage.polygon': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Polygon'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.polyline': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Polyline'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('rank', 'name')", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0014_auto__add_field_datalayer_geojson
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'DataLayer.geojson'
        db.add_column(u'leaflet_storage_datalayer', 'geojson',
                      self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'DataLayer.geojson'
        db.delete_column(u'leaflet_storage_datalayer', 'geojson')


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
        u'leaflet_storage.datalayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'DataLayer'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'geojson': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_maps'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'maps'", 'null': 'True', 'to': u"orm['leaflet_storage.TileLayer']"}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        u'leaflet_storage.marker': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Marker'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        u'leaflet_storage.polygon': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Polygon'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.polyline': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Polyline'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('rank', 'name')", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0015_create_geojson_file
# -*- coding: utf-8 -*-
import simplejson

from south.v2 import DataMigration
from django.core.files.base import ContentFile
from leaflet_storage.models import DataLayer

class Migration(DataMigration):

    def forwards(self, orm):
        for obj in DataLayer.objects.order_by('pk'):
            if not obj.geojson:
                obj.geojson.save(None, ContentFile(simplejson.dumps(obj.to_geojson())))
                obj.save()

    def backwards(self, orm):
        "Write your backwards methods here."

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
        u'leaflet_storage.datalayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'DataLayer'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'geojson': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_maps'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'maps'", 'null': 'True', 'to': u"orm['leaflet_storage.TileLayer']"}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        u'leaflet_storage.marker': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Marker'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'pictogram': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Pictogram']", 'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        u'leaflet_storage.polygon': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Polygon'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.PolygonField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.polyline': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Polyline'},
            'datalayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.DataLayer']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latlng': ('django.contrib.gis.db.models.fields.LineStringField', [], {'geography': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('rank', 'name')", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0016_auto__del_polyline__del_marker__del_polygon__del_field_datalayer_icon_
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'Polyline'
        db.delete_table(u'leaflet_storage_polyline')

        # Deleting model 'Marker'
        db.delete_table(u'leaflet_storage_marker')

        # Deleting model 'Polygon'
        db.delete_table(u'leaflet_storage_polygon')

        # Deleting field 'DataLayer.icon_class'
        db.delete_column(u'leaflet_storage_datalayer', 'icon_class')

        # Deleting field 'DataLayer.pictogram'
        db.delete_column(u'leaflet_storage_datalayer', 'pictogram_id')


    def backwards(self, orm):
        # Adding model 'Polyline'
        db.create_table(u'leaflet_storage_polyline', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('datalayer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.DataLayer'])),
            ('latlng', self.gf('django.contrib.gis.db.models.fields.LineStringField')(geography=True)),
            ('options', self.gf('leaflet_storage.fields.DictField')(null=True, blank=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'leaflet_storage', ['Polyline'])

        # Adding model 'Marker'
        db.create_table(u'leaflet_storage_marker', (
            ('icon_class', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('datalayer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.DataLayer'])),
            ('pictogram', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.Pictogram'], null=True, blank=True)),
            ('latlng', self.gf('django.contrib.gis.db.models.fields.PointField')(geography=True)),
            ('options', self.gf('leaflet_storage.fields.DictField')(null=True, blank=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal(u'leaflet_storage', ['Marker'])

        # Adding model 'Polygon'
        db.create_table(u'leaflet_storage_polygon', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('datalayer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.DataLayer'])),
            ('latlng', self.gf('django.contrib.gis.db.models.fields.PolygonField')(geography=True)),
            ('options', self.gf('leaflet_storage.fields.DictField')(null=True, blank=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'leaflet_storage', ['Polygon'])

        # Adding field 'DataLayer.icon_class'
        db.add_column(u'leaflet_storage_datalayer', 'icon_class',
                      self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True),
                      keep_default=False)

        # Adding field 'DataLayer.pictogram'
        db.add_column(u'leaflet_storage_datalayer', 'pictogram',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leaflet_storage.Pictogram'], null=True, blank=True),
                      keep_default=False)


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
        u'leaflet_storage.datalayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'DataLayer'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'geojson': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'options': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'})
        },
        u'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_maps'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'maps'", 'null': 'True', 'to': u"orm['leaflet_storage.TileLayer']"}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        u'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        u'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('rank', 'name')", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0017_auto__del_field_datalayer_options
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'DataLayer.options'
        db.delete_column(u'leaflet_storage_datalayer', 'options')


    def backwards(self, orm):
        # Adding field 'DataLayer.options'
        db.add_column(u'leaflet_storage_datalayer', 'options',
                      self.gf('leaflet_storage.fields.DictField')(null=True, blank=True),
                      keep_default=False)


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
        u'leaflet_storage.datalayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'DataLayer'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'geojson': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_maps'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'maps'", 'null': 'True', 'to': u"orm['leaflet_storage.TileLayer']"}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        u'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        u'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('rank', 'name')", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0018_auto__add_field_map_share_status
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Map.share_status'
        db.add_column(u'leaflet_storage_map', 'share_status',
                      self.gf('django.db.models.fields.SmallIntegerField')(default=1),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Map.share_status'
        db.delete_column(u'leaflet_storage_map', 'share_status')


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
        u'leaflet_storage.datalayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'DataLayer'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'geojson': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_maps'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'share_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'maps'", 'null': 'True', 'to': u"orm['leaflet_storage.TileLayer']"}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        u'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        u'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('rank', 'name')", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
########NEW FILE########
__FILENAME__ = 0019_map_settings_to_geojson
# -*- coding: utf-8 -*-
import simplejson

from south.v2 import DataMigration
from leaflet_storage.models import Map


class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."

        def geojson(m):
            settings = m.settings
            if not "properties" in settings:
                settings["properties"] = dict(m.settings)
                settings['properties']['zoom'] = m.zoom
                settings['properties']['name'] = m.name
                settings['properties']['description'] = m.description
                if m.tilelayer:
                    settings['properties']['tilelayer'] = m.tilelayer.json
                if m.licence:
                    settings['properties']['licence'] = m.licence.json
            if not "geometry" in settings:
                settings["geometry"] = simplejson.loads(m.center.geojson)
            return settings

        for m in Map.objects.order_by('modified_at'):
            m.settings = geojson(m)
            m.save()

    def backwards(self, orm):
        "Write your backwards methods here."

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
        u'leaflet_storage.datalayer': {
            'Meta': {'ordering': "('name',)", 'object_name': 'DataLayer'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_on_load': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'geojson': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.licence': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Licence'},
            'details': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'leaflet_storage.map': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Map'},
            'center': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edit_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'editors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['leaflet_storage.Licence']", 'on_delete': 'models.SET_DEFAULT'}),
            'locate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_maps'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'settings': ('leaflet_storage.fields.DictField', [], {'null': 'True', 'blank': 'True'}),
            'share_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tilelayer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'maps'", 'null': 'True', 'to': u"orm['leaflet_storage.TileLayer']"}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '7'})
        },
        u'leaflet_storage.pictogram': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Pictogram'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pictogram': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        },
        u'leaflet_storage.tilelayer': {
            'Meta': {'ordering': "('rank', 'name')", 'object_name': 'TileLayer'},
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxZoom': ('django.db.models.fields.IntegerField', [], {'default': '18'}),
            'minZoom': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'url_template': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['leaflet_storage']
    symmetrical = True

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

import os

from django.contrib.gis.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.utils.translation import ugettext, ugettext_lazy as _
from django.core.signing import Signer
from django.contrib import messages
from django.template.defaultfilters import slugify
from django.core.files.base import File

from .fields import DictField
from .managers import PublicManager


class NamedModel(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("name"))

    class Meta:
        abstract = True
        ordering = ('name', )

    def __unicode__(self):
        return self.name


class Licence(NamedModel):
    """
    The licence one map is published on.
    """
    details = models.URLField(
        verbose_name=_('details'),
        help_text=_('Link to a page where the licence is detailed.')
    )

    @classmethod
    def get_default(cls):
        """
        Returns a default Licence, creates it if it doesn't exist.
        Needed to prevent a licence deletion from deleting all the linked
        maps.
        """
        return cls.objects.get_or_create(
            # can't use ugettext_lazy for database storage, see #13965
            name=getattr(settings, "LEAFLET_STORAGE_DEFAULT_LICENCE_NAME", ugettext('No licence set'))
        )[0]

    @property
    def json(self):
        return {
            'name': self.name,
            'url': self.details
        }


class TileLayer(NamedModel):
    url_template = models.CharField(
        max_length=200,
        help_text=_("URL template using OSM tile format")
    )
    minZoom = models.IntegerField(default=0)
    maxZoom = models.IntegerField(default=18)
    attribution = models.CharField(max_length=300)
    rank = models.SmallIntegerField(
        blank=True,
        null=True,
        help_text=_('Order of the tilelayers in the edit box')
    )

    @property
    def json(self):
        return dict((field.name, getattr(self, field.name)) for field in self._meta.fields)

    @classmethod
    def get_default(cls):
        """
        Returns the default tile layer (used for a map when no layer is set).
        """
        return cls.objects.order_by('rank')[0]  # FIXME, make it administrable

    @classmethod
    def get_list(cls, selected=None):
        l = []
        for t in cls.objects.all():
            fields = t.json
            if selected and selected.pk == t.pk:
                fields['selected'] = True
            l.append(fields)
        return l

    class Meta:
        ordering = ('rank', 'name', )


class Map(NamedModel):
    """
    A single thematical map.
    """
    ANONYMOUS = 1
    EDITORS = 2
    OWNER = 3
    PUBLIC = 1
    OPEN = 2
    PRIVATE = 3
    EDIT_STATUS = (
        (ANONYMOUS, _('Everyone can edit')),
        (EDITORS, _('Only editors can edit')),
        (OWNER, _('Only owner can edit')),
    )
    SHARE_STATUS = (
        (PUBLIC, _('everyone (public)')),
        (OPEN, _('anyone with link')),
        (PRIVATE, _('editors only')),
    )
    slug = models.SlugField(db_index=True)
    description = models.TextField(blank=True, null=True, verbose_name=_("description"))
    center = models.PointField(geography=True, verbose_name=_("center"))
    zoom = models.IntegerField(default=7, verbose_name=_("zoom"))
    locate = models.BooleanField(default=False, verbose_name=_("locate"), help_text=_("Locate user on load?"))
    licence = models.ForeignKey(
        Licence,
        help_text=_("Choose the map licence."),
        verbose_name=_('licence'),
        on_delete=models.SET_DEFAULT,
        default=Licence.get_default
    )
    modified_at = models.DateTimeField(auto_now=True)
    tilelayer = models.ForeignKey(TileLayer, blank=True, null=True, related_name="maps",  verbose_name=_("background"))
    owner = models.ForeignKey(User, blank=True, null=True, related_name="owned_maps", verbose_name=_("owner"))
    editors = models.ManyToManyField(User, blank=True, verbose_name=_("editors"))
    edit_status = models.SmallIntegerField(choices=EDIT_STATUS, default=OWNER, verbose_name=_("edit status"))
    share_status = models.SmallIntegerField(choices=SHARE_STATUS, default=PUBLIC, verbose_name=_("share status"))
    settings = DictField(blank=True, null=True, verbose_name=_("settings"))

    objects = models.GeoManager()
    public = PublicManager()

    def get_absolute_url(self):
        return reverse("map", kwargs={'slug': self.slug or "map", 'pk': self.pk})

    def get_anonymous_edit_url(self):
        signer = Signer()
        signature = signer.sign(self.pk)
        return reverse('map_anonymous_edit_url', kwargs={'signature': signature})

    def is_anonymous_owner(self, request):
        if self.owner:
            # edit cookies are only valid while map hasn't owner
            return False
        key, value = self.signed_cookie_elements
        try:
            has_anonymous_cookie = int(request.get_signed_cookie(key, False)) == value
        except ValueError:
            has_anonymous_cookie = False
        return has_anonymous_cookie

    def can_edit(self, user=None, request=None):
        """
        Define if a user can edit or not the instance, according to his account
        or the request.
        """
        can = False
        if request and not self.owner:
            if (getattr(settings, "LEAFLET_STORAGE_ALLOW_ANONYMOUS", False)
                    and self.is_anonymous_owner(request)):
                can = True
                if user and user.is_authenticated():
                    # if user is authenticated, attach as owner
                    self.owner = user
                    self.save()
                    msg = _("Your anonymous map has been attached to your account %s" % user)
                    messages.info(request, msg)
        elif self.edit_status == self.ANONYMOUS:
            can = True
        elif not user.is_authenticated():
            pass
        elif user == self.owner:
            can = True
        elif self.edit_status == self.EDITORS and user in self.editors.all():
            can = True
        return can

    def can_view(self, request):
        if self.owner is None:
            can = True
        elif self.share_status in [self.PUBLIC, self.OPEN]:
            can = True
        elif request.user == self.owner:
            can = True
        else:
            can = not (self.share_status == self.PRIVATE and request.user not in self.editors.all())
        return can

    @property
    def signed_cookie_elements(self):
        return ('anonymous_owner|%s' % self.pk, self.pk)

    def get_tilelayer(self):
        return self.tilelayer or TileLayer.get_default()

    def clone(self, **kwargs):
        new = self.__class__.objects.get(pk=self.pk)
        new.pk = None
        new.name = u"%s %s" % (_("Clone of"), self.name)
        if "owner" in kwargs:
            # can be None in case of anonymous cloning
            new.owner = kwargs["owner"]
        new.save()
        for editor in self.editors.all():
            new.editors.add(editor)
        for datalayer in self.datalayer_set.all():
            datalayer.clone(map_inst=new)
        return new


class Pictogram(NamedModel):
    """
    An image added to an icon of the map.
    """
    attribution = models.CharField(max_length=300)
    pictogram = models.ImageField(upload_to="pictogram")

    @property
    def json(self):
        return {
            "id": self.pk,
            "attribution": self.attribution,
            "name": self.name,
            "src": self.pictogram.url
        }


class DataLayer(NamedModel):
    """
    Layer to store Features in.
    """
    def upload_to(instance, filename):
        path = ["datalayer", str(instance.map.pk)[-1]]
        if len(str(instance.map.pk)) > 1:
            path.append(str(instance.map.pk)[-2])
        path.append(str(instance.map.pk))
        path.append("%s.geojson" % (slugify(instance.name)[:50] or "untitled"))
        return os.path.join(*path)
    map = models.ForeignKey(Map)
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("description")
    )
    geojson = models.FileField(upload_to=upload_to, blank=True, null=True)
    display_on_load = models.BooleanField(
        default=False,
        verbose_name=_("display on load"),
        help_text=_("Display this layer on load.")
    )

    @property
    def metadata(self):
        return {
            "name": self.name,
            "id": self.pk,
            "displayOnLoad": self.display_on_load
        }

    def clone(self, map_inst=None):
        new = self.__class__.objects.get(pk=self.pk)
        new.pk = None
        if map_inst:
            new.map = map_inst
        new.geojson = File(new.geojson.file.file)
        new.save()
        return new

########NEW FILE########
__FILENAME__ = leaflet_storage_tags
from django.utils import simplejson
from django import template
from django.conf import settings

from ..models import DataLayer, TileLayer
from ..views import _urls_for_js

register = template.Library()


@register.inclusion_tag('leaflet_storage/css.html')
def leaflet_storage_css():
    return {
        "STATIC_URL": settings.STATIC_URL
    }


@register.inclusion_tag('leaflet_storage/js.html')
def leaflet_storage_js(locale=None):
    return {
        "STATIC_URL": settings.STATIC_URL,
        "locale": locale
    }


@register.inclusion_tag('leaflet_storage/map_fragment.html')
def map_fragment(map_instance, **kwargs):
    layers = DataLayer.objects.filter(map=map_instance)
    datalayer_data = [c.metadata for c in layers]
    tilelayers = TileLayer.get_list()  # TODO: no need to all
    map_settings = map_instance.settings
    if not "properties" in map_settings:
        map_settings['properties'] = {}
    map_settings['properties'].update({
        'tilelayers': tilelayers,
        'datalayers': datalayer_data,
        'urls': _urls_for_js(),
        'STATIC_URL': settings.STATIC_URL,
        "allowEdit": False,
        'hash': False,
        'attributionControl': False,
        'scrollWheelZoom': False,
        'datalayersControl': False,
        'zoomControl': False,
        'storageAttributionControl': False,
        'moreControl': False,
        'scaleControl': False,
        'miniMap': False,
        'storage_id': map_instance.pk,
        'onLoadPanel': "none",
        'captionBar': False,
        'default_iconUrl': "%sstorage/src/img/marker.png" % settings.STATIC_URL,
    })
    map_settings['properties'].update(kwargs)
    return {
        "map_settings": simplejson.dumps(map_settings),
        "map": map_instance
    }


@register.simple_tag
def tilelayer_preview(tilelayer):
    """
    Return an <img> tag with a tile of the tilelayer.
    """
    output = '<img src="{src}" alt="{alt}" title="{title}" />'
    url = tilelayer.url_template.format(s="a", z=9, x=265, y=181)
    output = output.format(src=url, alt=tilelayer.name, title=tilelayer.name)
    return output


@register.filter
def notag(s):
    return s.replace('<', '&lt;')

########NEW FILE########
__FILENAME__ = base
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import simplejson
from django.core.urlresolvers import reverse

import factory

from leaflet_storage.models import Map, TileLayer, Licence, DataLayer
from leaflet_storage.forms import DEFAULT_CENTER


class LicenceFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Licence
    name = "WTFPL"


class TileLayerFactory(factory.DjangoModelFactory):
    FACTORY_FOR = TileLayer
    name = "Test zoom layer"
    url_template = "http://{s}.test.org/{z}/{x}/{y}.png"
    attribution = "Test layer attribution"


class UserFactory(factory.DjangoModelFactory):
    FACTORY_FOR = User
    username = 'Joe'
    email = factory.LazyAttribute(lambda a: '{0}@example.com'.format(a.username).lower())

    @classmethod
    def _prepare(cls, create, **kwargs):
        password = kwargs.pop('password', None)
        user = super(UserFactory, cls)._prepare(create, **kwargs)
        if password:
            user.set_password(password)
            if create:
                user.save()
        return user


class MapFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Map
    name = "test map"
    slug = "test-map"
    center = DEFAULT_CENTER
    settings = {
        'geometry': {
            'coordinates': [13.447265624999998, 48.94415123418794],
            'type': 'Point'
        },
        'properties': {
            'datalayersControl': True,
            'description': 'Which is just the Danube, at the end, I mean, JUST THE DANUBE',
            'displayCaptionOnLoad': False,
            'displayDataBrowserOnLoad': False,
            'displayPopupFooter': False,
            'licence': '',
            'miniMap': False,
            'moreControl': True,
            'name': 'Cruising on the Donau',
            'scaleControl': True,
            'tilelayer': {
                'attribution': u'\xa9 OSM Contributors - tiles OpenRiverboatMap',
                'maxZoom': 18,
                'minZoom': 0,
                'url_template': 'http://{s}.layers.openstreetmap.fr/openriverboatmap/{z}/{x}/{y}.png'
            },
            'tilelayersControl': True,
            'zoom': 7,
            'zoomControl': True
        },
        'type': 'Feature'
    }

    licence = factory.SubFactory(LicenceFactory)
    owner = factory.SubFactory(UserFactory)


class DataLayerFactory(factory.DjangoModelFactory):
    FACTORY_FOR = DataLayer
    map = factory.SubFactory(MapFactory)
    name = "test datalayer"
    description = "test description"
    display_on_load = True
    geojson = factory.django.FileField(data="""{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[13.68896484375,48.55297816440071]},"properties":{"_storage_options":{"color":"DarkCyan","iconClass":"Ball"},"name":"Here","description":"Da place anonymous again 755"}}],"_storage":{"displayOnLoad":true,"name":"Donau","id":926}}""")


class BaseFeatureFactory(factory.DjangoModelFactory):
    ABSTRACT_FACTORY = True
    name = "test feature"
    description = "test description"
    datalayer = factory.SubFactory(DataLayerFactory)


class BaseTest(TestCase):
    """
    Provide miminal data need in tests.
    """

    def setUp(self):
        self.user = UserFactory(password="123123")
        self.licence = LicenceFactory()
        self.map = MapFactory(owner=self.user, licence=self.licence)
        self.datalayer = DataLayerFactory(map=self.map)
        self.tilelayer = TileLayerFactory()

    def tearDown(self):
        self.user.delete()
        self.map.delete()
        self.datalayer.delete()

    def assertLoginRequired(self, response):
        self.assertEqual(response.status_code, 200)
        json = simplejson.loads(response.content)
        self.assertIn("login_required", json)
        redirect_url = reverse('login')
        self.assertEqual(json['login_required'], redirect_url)

    def assertHasForm(self, response):
        self.assertEqual(response.status_code, 200)
        json = simplejson.loads(response.content)
        self.assertIn("html", json)
        self.assertIn("form", json['html'])

########NEW FILE########
__FILENAME__ = test_base_models
from django.contrib.auth.models import AnonymousUser

from leaflet_storage.models import Map, DataLayer
from .base import BaseTest, UserFactory, DataLayerFactory, MapFactory


class MapModel(BaseTest):

    def test_anonymous_can_edit_if_status_anonymous(self):
        anonymous = AnonymousUser()
        self.map.edit_status = self.map.ANONYMOUS
        self.map.save()
        self.assertTrue(self.map.can_edit(anonymous))

    def test_anonymous_cannot_edit_if_not_status_anonymous(self):
        anonymous = AnonymousUser()
        self.map.edit_status = self.map.OWNER
        self.map.save()
        self.assertFalse(self.map.can_edit(anonymous))

    def test_non_editors_can_edit_if_status_anonymous(self):
        lambda_user = UserFactory(username="John", password="123123")
        self.map.edit_status = self.map.ANONYMOUS
        self.map.save()
        self.assertTrue(self.map.can_edit(lambda_user))

    def test_non_editors_cannot_edit_if_not_status_anonymous(self):
        lambda_user = UserFactory(username="John", password="123123")
        self.map.edit_status = self.map.OWNER
        self.map.save()
        self.assertFalse(self.map.can_edit(lambda_user))

    def test_editors_cannot_edit_if_status_owner(self):
        editor = UserFactory(username="John", password="123123")
        self.map.edit_status = self.map.OWNER
        self.map.save()
        self.assertFalse(self.map.can_edit(editor))

    def test_editors_can_edit_if_status_editors(self):
        editor = UserFactory(username="John", password="123123")
        self.map.edit_status = self.map.EDITORS
        self.map.editors.add(editor)
        self.map.save()
        self.assertTrue(self.map.can_edit(editor))

    def test_clone_should_return_new_instance(self):
        clone = self.map.clone()
        self.assertNotEqual(self.map.pk, clone.pk)
        self.assertEqual(u"Clone of " + self.map.name, clone.name)
        self.assertEqual(self.map.settings, clone.settings)
        self.assertEqual(self.map.center, clone.center)
        self.assertEqual(self.map.zoom, clone.zoom)
        self.assertEqual(self.map.licence, clone.licence)
        self.assertEqual(self.map.tilelayer, clone.tilelayer)

    def test_clone_should_keep_editors(self):
        editor = UserFactory(username="Mark")
        self.map.editors.add(editor)
        clone = self.map.clone()
        self.assertNotEqual(self.map.pk, clone.pk)
        self.assertIn(editor, self.map.editors.all())
        self.assertIn(editor, clone.editors.all())

    def test_clone_should_update_owner_if_passer(self):
        new_owner = UserFactory(username="Mark")
        clone = self.map.clone(owner=new_owner)
        self.assertNotEqual(self.map.pk, clone.pk)
        self.assertNotEqual(self.map.owner, clone.owner)
        self.assertEqual(new_owner, clone.owner)

    def test_clone_should_clone_datalayers_and_features_too(self):
        clone = self.map.clone()
        self.assertNotEqual(self.map.pk, clone.pk)
        self.assertEqual(self.map.datalayer_set.count(), 1)
        datalayer = clone.datalayer_set.all()[0]
        self.assertIn(self.datalayer, self.map.datalayer_set.all())
        self.assertNotEqual(self.datalayer.pk, datalayer.pk)
        self.assertEqual(self.datalayer.name, datalayer.name)
        self.assertIsNotNone(datalayer.geojson)
        self.assertNotEqual(datalayer.geojson.path, self.datalayer.geojson.path)

    def test_publicmanager_should_get_only_public_maps(self):
        self.map.share_status = self.map.PUBLIC
        open_map = MapFactory(owner=self.user, licence=self.licence, share_status=Map.OPEN)
        private_map = MapFactory(owner=self.user, licence=self.licence, share_status=Map.PRIVATE)
        self.assertIn(self.map, Map.public.all())
        self.assertNotIn(open_map, Map.public.all())
        self.assertNotIn(private_map, Map.public.all())


class LicenceModel(BaseTest):

    def test_licence_delete_should_not_remove_linked_maps(self):
        self.licence.delete()
        self.assertEqual(Map.objects.filter(pk=self.map.pk).count(), 1)
        self.assertEqual(DataLayer.objects.filter(pk=self.datalayer.pk).count(), 1)


class DataLayerModel(BaseTest):

    def test_datalayers_should_be_ordered_by_name(self):
        c4 = DataLayerFactory(map=self.map, name="eeeeeee")
        c1 = DataLayerFactory(map=self.map, name="1111111")
        c3 = DataLayerFactory(map=self.map, name="ccccccc")
        c2 = DataLayerFactory(map=self.map, name="aaaaaaa")
        self.assertEqual(
            list(self.map.datalayer_set.all()),
            [c1, c2, c3, c4, self.datalayer]
        )

    def test_clone_should_return_new_instance(self):
        clone = self.datalayer.clone()
        self.assertNotEqual(self.datalayer.pk, clone.pk)
        self.assertEqual(self.datalayer.name, clone.name)
        self.assertEqual(self.datalayer.map, clone.map)

    def test_clone_should_update_map_if_passed(self):
        new_map = MapFactory(owner=self.user, licence=self.licence)
        clone = self.datalayer.clone(map_inst=new_map)
        self.assertNotEqual(self.datalayer.pk, clone.pk)
        self.assertEqual(self.datalayer.name, clone.name)
        self.assertNotEqual(self.datalayer.map, clone.map)
        self.assertEqual(new_map, clone.map)

    def test_clone_should_clone_geojson_too(self):
        clone = self.datalayer.clone()
        self.assertNotEqual(self.datalayer.pk, clone.pk)
        self.assertIsNotNone(clone.geojson)
        self.assertNotEqual(clone.geojson.path, self.datalayer.geojson.path)

    def test_upload_to_should_split_map_id(self):
        self.map.pk = 302
        self.datalayer.name = "a name"
        self.assertEqual(
            DataLayer.upload_to(self.datalayer, None),
            "datalayer/2/0/302/a-name.geojson"
        )

    def test_upload_to_should_never_has_empty_name(self):
        self.map.pk = 1
        self.datalayer.name = ""
        self.assertEqual(
            DataLayer.upload_to(self.datalayer, None),
            "datalayer/1/1/untitled.geojson"
        )

    def test_upload_to_should_cut_too_long_name(self):
        self.map.pk = 1
        self.datalayer.name = "name" * 20
        self.assertEqual(
            DataLayer.upload_to(self.datalayer, None),
            "datalayer/1/1/namenamenamenamenamenamenamenamenamenamenamenamena.geojson"
        )
########NEW FILE########
__FILENAME__ = test_fields
from leaflet_storage.models import Map
from .base import BaseTest


class DictFieldTest(BaseTest):

    def test_can_use_dict(self):
        d = {'locateControl': True}
        self.map.settings = d
        self.map.save()
        self.assertEqual(
            Map.objects.get(pk=self.map.pk).settings,
            d
        )

    def test_can_set_item(self):
        d = {'locateControl': True}
        self.map.settings = d
        self.map.save()
        map_inst = Map.objects.get(pk=self.map.pk)
        map_inst.settings['color'] = 'DarkGreen'
        self.assertEqual(
            map_inst.settings['locateControl'],
            True
        )

    def test_should_return_a_dict_if_none(self):
        self.map.settings = None
        self.map.save()
        self.assertEqual(
            Map.objects.get(pk=self.map.pk).settings,
            {}
        )

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding:utf-8 -*-

from django.test import TestCase

from leaflet_storage.utils import smart_decode


class SmartDecodeTests(TestCase):

    def test_should_return_unicode(self):
        self.assertTrue(isinstance(smart_decode('test'), unicode))
        self.assertTrue(isinstance(smart_decode(u'test'), unicode))

    def test_should_convert_utf8(self):
        self.assertEqual(smart_decode('é'), u"é")

########NEW FILE########
__FILENAME__ = test_views
# -*- coding: utf-8 -*-
from django.utils import simplejson
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.core.signing import get_cookie_signer

from leaflet_storage.models import Map, DataLayer

from .base import (MapFactory, UserFactory, BaseTest)


@override_settings(LEAFLET_STORAGE_ALLOW_ANONYMOUS=False)
class MapViews(BaseTest):

    def test_create(self):
        url = reverse('map_create')
        # POST only mendatory fields
        name = 'test-map-with-new-name'
        post_data = {
            'name': name,
            'center': '{"type":"Point","coordinates":[13.447265624999998,48.94415123418794]}',
            'settings': '{"type":"Feature","geometry":{"type":"Point","coordinates":[5.0592041015625,52.05924589011585]},"properties":{"tilelayer":{"maxZoom":20,"url_template":"http://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png","minZoom":0,"attribution":"HOT and friends"},"licence":"","description":"","name":"test enrhûmé","tilelayersControl":true,"displayDataBrowserOnLoad":false,"displayPopupFooter":true,"displayCaptionOnLoad":false,"miniMap":true,"moreControl":true,"scaleControl":true,"zoomControl":true,"datalayersControl":true,"zoom":8}}'
        }
        self.client.login(username=self.user.username, password="123123")
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        json = simplejson.loads(response.content)
        created_map = Map.objects.latest('pk')
        self.assertEqual(json['id'], created_map.pk)
        self.assertEqual(created_map.name, name)

    def test_update(self):
        url = reverse('map_update', kwargs={'map_id': self.map.pk})
        # POST only mendatory fields
        new_name = 'new map name'
        post_data = {
            'name': new_name,
            'center': '{"type":"Point","coordinates":[13.447265624999998,48.94415123418794]}',
            'settings': '{"type":"Feature","geometry":{"type":"Point","coordinates":[5.0592041015625,52.05924589011585]},"properties":{"tilelayer":{"maxZoom":20,"url_template":"http://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png","minZoom":0,"attribution":"HOT and friends"},"licence":"","description":"","name":"test enrhûmé","tilelayersControl":true,"displayDataBrowserOnLoad":false,"displayPopupFooter":true,"displayCaptionOnLoad":false,"miniMap":true,"moreControl":true,"scaleControl":true,"zoomControl":true,"datalayersControl":true,"zoom":8}}'
        }
        self.client.login(username=self.user.username, password="123123")
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        json = simplejson.loads(response.content)
        self.assertNotIn("html", json)
        updated_map = Map.objects.get(pk=self.map.pk)
        self.assertEqual(json['id'], updated_map.pk)
        self.assertEqual(updated_map.name, new_name)

    def test_delete(self):
        url = reverse('map_delete', args=(self.map.pk, ))
        self.client.login(username=self.user.username, password="123123")
        response = self.client.post(url, {}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Map.objects.filter(pk=self.map.pk).count(), 0)
        self.assertEqual(DataLayer.objects.filter(pk=self.datalayer.pk).count(), 0)
        # Check that user has not been impacted
        self.assertEqual(User.objects.filter(pk=self.user.pk).count(), 1)
        # Test response is a json
        json = simplejson.loads(response.content)
        self.assertIn("redirect", json)

    def test_short_url_should_redirect_to_canonical(self):
        url = reverse('map_short_url', kwargs={'pk': self.map.pk})
        canonical = reverse('map', kwargs={'pk': self.map.pk, 'slug': self.map.slug})
        response = self.client.get(url)
        self.assertRedirects(response, canonical, status_code=301)

    def test_old_url_should_redirect_to_canonical(self):
        url = reverse(
            'map_old_url',
            kwargs={'username': self.map.owner.username, 'slug': self.map.slug}
        )
        canonical = reverse('map', kwargs={'pk': self.map.pk, 'slug': self.map.slug})
        response = self.client.get(url)
        self.assertRedirects(response, canonical, status_code=301)

    def test_clone_map_should_create_a_new_instance(self):
        self.assertEqual(Map.objects.count(), 1)
        url = reverse('map_clone', kwargs={'map_id': self.map.pk})
        self.client.login(username=self.user.username, password="123123")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Map.objects.count(), 2)
        clone = Map.objects.latest('pk')
        self.assertNotEqual(clone.pk, self.map.pk)
        self.assertEqual(clone.name, u"Clone of " + self.map.name)

    def test_clone_map_should_not_be_possible_if_user_is_not_allowed(self):
        self.assertEqual(Map.objects.count(), 1)
        url = reverse('map_clone', kwargs={'map_id': self.map.pk})
        self.map.edit_status = self.map.OWNER
        self.map.save()
        response = self.client.post(url)
        self.assertLoginRequired(response)
        other_user = UserFactory(username="Bob", password="123123")
        self.client.login(username=other_user.username, password="123123")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.map.edit_status = self.map.ANONYMOUS
        self.map.save()
        self.client.logout()
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Map.objects.count(), 1)

    def test_clone_should_set_cloner_as_owner(self):
        url = reverse('map_clone', kwargs={'map_id': self.map.pk})
        other_user = UserFactory(username="Bob", password="123123")
        self.map.edit_status = self.map.EDITORS
        self.map.editors.add(other_user)
        self.map.save()
        self.client.login(username=other_user.username, password="123123")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Map.objects.count(), 2)
        clone = Map.objects.latest('pk')
        self.assertNotEqual(clone.pk, self.map.pk)
        self.assertEqual(clone.name, u"Clone of " + self.map.name)
        self.assertEqual(clone.owner, other_user)

    def test_map_creation_should_allow_unicode_names(self):
        url = reverse('map_create')
        # POST only mendatory fields
        name = u'Академический'
        post_data = {
            'name': name,
            'center': '{"type":"Point","coordinates":[13.447265624999998,48.94415123418794]}',
            'settings': '{"type":"Feature","geometry":{"type":"Point","coordinates":[5.0592041015625,52.05924589011585]},"properties":{"tilelayer":{"maxZoom":20,"url_template":"http://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png","minZoom":0,"attribution":"HOT and friends"},"licence":"","description":"","name":"test enrhûmé","tilelayersControl":true,"displayDataBrowserOnLoad":false,"displayPopupFooter":true,"displayCaptionOnLoad":false,"miniMap":true,"moreControl":true,"scaleControl":true,"zoomControl":true,"datalayersControl":true,"zoom":8}}'
        }
        self.client.login(username=self.user.username, password="123123")
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        json = simplejson.loads(response.content)
        created_map = Map.objects.latest('pk')
        self.assertEqual(json['id'], created_map.pk)
        self.assertEqual(created_map.name, name)
        # Lower case of the russian original name
        # self.assertEqual(created_map.slug, u"академический")
        # for now we fallback to "map", see unicode_name branch
        self.assertEqual(created_map.slug, u"map")

    def test_anonymous_can_access_map_with_share_status_public(self):
        url = reverse('map', args=(self.map.slug, self.map.pk))
        self.map.share_status = self.map.PUBLIC
        self.map.save()
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_anonymous_can_access_map_with_share_status_open(self):
        url = reverse('map', args=(self.map.slug, self.map.pk))
        self.map.share_status = self.map.OPEN
        self.map.save()
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_anonymous_cannot_access_map_with_share_status_private(self):
        url = reverse('map', args=(self.map.slug, self.map.pk))
        self.map.share_status = self.map.PRIVATE
        self.map.save()
        response = self.client.get(url)
        self.assertEquals(response.status_code, 403)

    def test_owner_can_access_map_with_share_status_private(self):
        url = reverse('map', args=(self.map.slug, self.map.pk))
        self.map.share_status = self.map.PRIVATE
        self.map.save()
        self.client.login(username=self.user.username, password="123123")
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_editors_can_access_map_with_share_status_private(self):
        url = reverse('map', args=(self.map.slug, self.map.pk))
        self.map.share_status = self.map.PRIVATE
        other_user = UserFactory(username="Bob", password="123123")
        self.map.editors.add(other_user)
        self.map.save()
        self.client.login(username=other_user.username, password="123123")
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_non_editor_cannot_access_map_with_share_status_private(self):
        url = reverse('map', args=(self.map.slug, self.map.pk))
        self.map.share_status = self.map.PRIVATE
        other_user = UserFactory(username="Bob", password="123123")
        self.map.save()
        self.client.login(username=other_user.username, password="123123")
        response = self.client.get(url)
        self.assertEquals(response.status_code, 403)


@override_settings(LEAFLET_STORAGE_ALLOW_ANONYMOUS=True)
class AnonymousMapViews(BaseTest):

    def setUp(self):
        super(AnonymousMapViews, self).setUp()
        self.anonymous_map = MapFactory(
            name="an-anonymous-map",
            owner=None,
        )
        key, value = self.anonymous_map.signed_cookie_elements
        self.anonymous_cookie_key = key
        self.anonymous_cookie_value = get_cookie_signer(salt=key).sign(value)

    def test_create(self):
        url = reverse('map_create')
        # POST only mendatory fields
        name = 'test-map-with-new-name'
        post_data = {
            'name': name,
            'center': '{"type":"Point","coordinates":[13.447265624999998,48.94415123418794]}',
            'settings': '{"type":"Feature","geometry":{"type":"Point","coordinates":[5.0592041015625,52.05924589011585]},"properties":{"tilelayer":{"maxZoom":20,"url_template":"http://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png","minZoom":0,"attribution":"HOT and friends"},"licence":"","description":"","name":"test enrhûmé","tilelayersControl":true,"displayDataBrowserOnLoad":false,"displayPopupFooter":true,"displayCaptionOnLoad":false,"miniMap":true,"moreControl":true,"scaleControl":true,"zoomControl":true,"datalayersControl":true,"zoom":8}}'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        json = simplejson.loads(response.content)
        created_map = Map.objects.latest('pk')
        self.assertEqual(json['id'], created_map.pk)
        self.assertEqual(created_map.name, name)
        key, value = created_map.signed_cookie_elements
        self.assertIn(key, self.client.cookies)

    def test_update_no_cookie(self):
        url = reverse('map_update', kwargs={'map_id': self.anonymous_map.pk})
        # POST only mendatory fields
        new_name = 'new map name'
        post_data = {
            'name': new_name,
            'center': '{"type":"Point","coordinates":[13.447265624999998,48.94415123418794]}',
            'settings': '{"type":"Feature","geometry":{"type":"Point","coordinates":[5.0592041015625,52.05924589011585]},"properties":{"tilelayer":{"maxZoom":20,"url_template":"http://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png","minZoom":0,"attribution":"HOT and friends"},"licence":"","description":"","name":"test enrhûmé","tilelayersControl":true,"displayDataBrowserOnLoad":false,"displayPopupFooter":true,"displayCaptionOnLoad":false,"miniMap":true,"moreControl":true,"scaleControl":true,"zoomControl":true,"datalayersControl":true,"zoom":8}}'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        json = simplejson.loads(response.content)
        self.assertNotIn("id", json)
        self.assertIn("login_required", json)

    def test_update_with_cookie(self):
        url = reverse('map_update', kwargs={'map_id': self.anonymous_map.pk})
        self.client.cookies[self.anonymous_cookie_key] = self.anonymous_cookie_value
        # POST only mendatory fields
        new_name = 'new map name'
        post_data = {
            'name': new_name,
            'center': '{"type":"Point","coordinates":[13.447265624999998,48.94415123418794]}',
            'settings': '{"type":"Feature","geometry":{"type":"Point","coordinates":[5.0592041015625,52.05924589011585]},"properties":{"tilelayer":{"maxZoom":20,"url_template":"http://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png","minZoom":0,"attribution":"HOT and friends"},"licence":"","description":"","name":"test enrhûmé","tilelayersControl":true,"displayDataBrowserOnLoad":false,"displayPopupFooter":true,"displayCaptionOnLoad":false,"miniMap":true,"moreControl":true,"scaleControl":true,"zoomControl":true,"datalayersControl":true,"zoom":8}}'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        json = simplejson.loads(response.content)
        updated_map = Map.objects.get(pk=self.anonymous_map.pk)
        self.assertEqual(json['id'], updated_map.pk)

    def test_anonymous_edit_url(self):
        url = self.anonymous_map.get_anonymous_edit_url()
        canonical = reverse(
            'map',
            kwargs={'pk': self.anonymous_map.pk, 'slug': self.anonymous_map.slug}
        )
        response = self.client.get(url)
        self.assertRedirects(response, canonical, status_code=302)
        key, value = self.anonymous_map.signed_cookie_elements
        self.assertIn(key, self.client.cookies)

    def test_bad_anonymous_edit_url_should_return_403(self):
        url = self.anonymous_map.get_anonymous_edit_url()
        url = reverse(
            'map_anonymous_edit_url',
            kwargs={'signature': "%s:badsignature" % self.anonymous_map.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_with_cookie_is_attached_as_owner(self):
        url = reverse('map_update', kwargs={'map_id': self.anonymous_map.pk})
        self.client.cookies[self.anonymous_cookie_key] = self.anonymous_cookie_value
        self.client.login(username=self.user.username, password="123123")
        self.assertEqual(self.anonymous_map.owner, None)
        # POST only mendatory fields
        new_name = 'new map name for authenticated user'
        post_data = {
            'name': new_name,
            'center': '{"type":"Point","coordinates":[13.447265624999998,48.94415123418794]}',
            'settings': '{"type":"Feature","geometry":{"type":"Point","coordinates":[5.0592041015625,52.05924589011585]},"properties":{"tilelayer":{"maxZoom":20,"url_template":"http://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png","minZoom":0,"attribution":"HOT and friends"},"licence":"","description":"","name":"test enrhûmé","tilelayersControl":true,"displayDataBrowserOnLoad":false,"displayPopupFooter":true,"displayCaptionOnLoad":false,"miniMap":true,"moreControl":true,"scaleControl":true,"zoomControl":true,"datalayersControl":true,"zoom":8}}'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        json = simplejson.loads(response.content)
        updated_map = Map.objects.get(pk=self.anonymous_map.pk)
        self.assertEqual(json['id'], updated_map.pk)
        self.assertEqual(updated_map.owner.pk, self.user.pk)

    def test_clone_map_should_not_be_possible_if_user_is_not_allowed(self):
        self.assertEqual(Map.objects.count(), 2)
        url = reverse('map_clone', kwargs={'map_id': self.map.pk})
        self.map.edit_status = self.map.OWNER
        self.map.save()
        response = self.client.get(url)
        self.assertLoginRequired(response)
        other_user = UserFactory(username="Bob", password="123123")
        self.client.login(username=other_user.username, password="123123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Map.objects.count(), 2)

    def test_clone_map_should_be_possible_if_edit_status_is_anonymous(self):
        self.assertEqual(Map.objects.count(), 2)
        url = reverse('map_clone', kwargs={'map_id': self.map.pk})
        self.map.edit_status = self.map.ANONYMOUS
        self.map.save()
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Map.objects.count(), 3)
        clone = Map.objects.latest('pk')
        self.assertNotEqual(clone.pk, self.map.pk)
        self.assertEqual(clone.name, u"Clone of " + self.map.name)
        self.assertEqual(clone.owner, None)

    def test_anyone_can_access_anonymous_map(self):
        url = reverse('map', args=(self.map.slug, self.map.pk))
        self.map.share_status = self.map.PUBLIC
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.map.share_status = self.map.OPEN
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.map.share_status = self.map.PRIVATE
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)


@override_settings(LEAFLET_STORAGE_ALLOW_ANONYMOUS=False)
class ViewsPermissionsTest(BaseTest):

    def setUp(self):
        super(ViewsPermissionsTest, self).setUp()
        self.other_user = UserFactory(username="Bob", password="123123")

    def check_url_permissions(self, url):
        # GET anonymous
        response = self.client.get(url)
        self.assertLoginRequired(response)
        # POST anonymous
        response = self.client.post(url, {})
        self.assertLoginRequired(response)
        # GET with wrong permissions
        self.client.login(username=self.other_user.username, password="123123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        # POST with wrong permissions
        self.client.login(username=self.other_user.username, password="123123")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 403)


@override_settings(LEAFLET_STORAGE_ALLOW_ANONYMOUS=False)
class MapViewsPermissions(ViewsPermissionsTest):

    def test_map_create_permissions(self):
        url = reverse('map_create')
        # POST anonymous
        response = self.client.post(url, {})
        self.assertLoginRequired(response)

    def test_map_update_permissions(self):
        url = reverse('map_update', kwargs={'map_id': self.map.pk})
        self.check_url_permissions(url)

    def test_only_owner_can_delete(self):
        self.map.editors.add(self.other_user)
        url = reverse('map_delete', kwargs={'map_id': self.map.pk})
        self.client.login(username=self.other_user.username, password="123123")
        response = self.client.post(url, {}, follow=True)
        self.assertEqual(response.status_code, 403)


class DataLayerViews(BaseTest):

    def test_get(self):
        url = reverse('datalayer_view', args=(self.datalayer.pk, ))
        response = self.client.get(url)
        self.assertIsNotNone(response['Etag'])
        self.assertIsNotNone(response['Last-Modified'])
        self.assertIsNotNone(response['Cache-Control'])
        self.assertNotIn('Content-Encoding', response)
        json = simplejson.loads(response.content)
        self.assertIn('_storage', json)
        self.assertIn('features', json)
        self.assertEquals(json['type'], 'FeatureCollection')

    def test_update(self):
        url = reverse('datalayer_update', args=(self.map.pk, self.datalayer.pk))
        self.client.login(username=self.user.username, password="123123")
        name = "new name"
        post_data = {
            "name": name,
            "display_on_load": True,
            "geojson": '{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[-3.1640625,53.014783245859235],[-3.1640625,51.86292391360244],[-0.50537109375,51.385495069223204],[1.16455078125,52.38901106223456],[-0.41748046875,53.91728101547621],[-2.109375,53.85252660044951],[-3.1640625,53.014783245859235]]]},"properties":{"_storage_options":{},"name":"Ho god, sounds like a polygouine"}},{"type":"Feature","geometry":{"type":"LineString","coordinates":[[1.8017578124999998,51.16556659836182],[-0.48339843749999994,49.710272582105695],[-3.1640625,50.0923932109388],[-5.60302734375,51.998410382390325]]},"properties":{"_storage_options":{},"name":"Light line"}},{"type":"Feature","geometry":{"type":"Point","coordinates":[0.63720703125,51.15178610143037]},"properties":{"_storage_options":{},"name":"marker he"}}],"_storage":{"displayOnLoad":true,"name":"new name","id":1668,"remoteData":{},"color":"LightSeaGreen","description":"test"}}'
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        modified_datalayer = DataLayer.objects.get(pk=self.datalayer.pk)
        self.assertEqual(modified_datalayer.name, name)
        # Test response is a json
        json = simplejson.loads(response.content)
        self.assertIn("id", json)
        self.assertEqual(self.datalayer.pk, json['id'])

    def test_should_not_be_possible_to_update_with_wrong_map_id_in_url(self):
        other_map = MapFactory(owner=self.user)
        url = reverse('datalayer_update', args=(other_map.pk, self.datalayer.pk))
        self.client.login(username=self.user.username, password="123123")
        name = "new name"
        post_data = {
            "name": name,
            "display_on_load": True,
            "geojson": '{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[-3.1640625,53.014783245859235],[-3.1640625,51.86292391360244],[-0.50537109375,51.385495069223204],[1.16455078125,52.38901106223456],[-0.41748046875,53.91728101547621],[-2.109375,53.85252660044951],[-3.1640625,53.014783245859235]]]},"properties":{"_storage_options":{},"name":"Ho god, sounds like a polygouine"}},{"type":"Feature","geometry":{"type":"LineString","coordinates":[[1.8017578124999998,51.16556659836182],[-0.48339843749999994,49.710272582105695],[-3.1640625,50.0923932109388],[-5.60302734375,51.998410382390325]]},"properties":{"_storage_options":{},"name":"Light line"}},{"type":"Feature","geometry":{"type":"Point","coordinates":[0.63720703125,51.15178610143037]},"properties":{"_storage_options":{},"name":"marker he"}}],"_storage":{"displayOnLoad":true,"name":"new name","id":1668,"remoteData":{},"color":"LightSeaGreen","description":"test"}}'
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 403)
        modified_datalayer = DataLayer.objects.get(pk=self.datalayer.pk)
        self.assertEqual(modified_datalayer.name, self.datalayer.name)

    def test_delete(self):
        url = reverse('datalayer_delete', args=(self.map.pk, self.datalayer.pk))
        self.client.login(username=self.user.username, password="123123")
        response = self.client.post(url, {}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(DataLayer.objects.filter(pk=self.datalayer.pk).count(), 0)
        # Check that map has not been impacted
        self.assertEqual(Map.objects.filter(pk=self.map.pk).count(), 1)
        # Test response is a json
        json = simplejson.loads(response.content)
        self.assertIn("info", json)

    def test_should_not_be_possible_to_delete_with_wrong_map_id_in_url(self):
        other_map = MapFactory(owner=self.user)
        url = reverse('datalayer_delete', args=(other_map.pk, self.datalayer.pk))
        self.client.login(username=self.user.username, password="123123")
        response = self.client.post(url, {}, follow=True)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(DataLayer.objects.filter(pk=self.datalayer.pk).count(), 1)

    def test_get_gzipped(self):
        url = reverse('datalayer_view', args=(self.datalayer.pk, ))
        response = self.client.get(url, HTTP_ACCEPT_ENCODING="gzip")
        self.assertIsNotNone(response['Etag'])
        self.assertIsNotNone(response['Last-Modified'])
        self.assertIsNotNone(response['Cache-Control'])
        self.assertIn('Content-Encoding', response)
        self.assertEquals(response['Content-Encoding'], 'gzip')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.contrib.auth.views import login
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache, cache_control

from . import views
from .decorators import jsonize_view, map_permissions_check,\
    login_required_if_not_anonymous_allowed
from .utils import decorated_patterns

urlpatterns = patterns('',
    url(r'^login/$', jsonize_view(login), name='login'),
    url(r'^login/popup/end/$', views.LoginPopupEnd.as_view(), name='login_popup_end'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^map/(?P<pk>\d+)/geojson/$', views.MapViewGeoJSON.as_view(), name='map_geojson'),
    url(r'^map/(?P<username>[-_\w]+)/(?P<slug>[-_\w]+)/$', views.MapOldUrl.as_view(), name='map_old_url'),
    url(r'^map/anonymous-edit/(?P<signature>.+)$', views.MapAnonymousEditUrl.as_view(), name='map_anonymous_edit_url'),
    url(r'^m/(?P<pk>\d+)/$', views.MapShortUrl.as_view(), name='map_short_url'),
    url(r'^pictogram/json/$', views.PictogramJSONList.as_view(), name='pictogram_list_json'),
)
urlpatterns += decorated_patterns('', [cache_control(must_revalidate=True), ],
    url(r'^datalayer/(?P<pk>[\d]+)/$', views.DataLayerView.as_view(), name='datalayer_view'),
)
urlpatterns += decorated_patterns('', [ensure_csrf_cookie, ],
    url(r'^map/(?P<slug>[-_\w]+)_(?P<pk>\d+)$', views.MapView.as_view(), name='map'),
    url(r'^map/new/$', views.MapNew.as_view(), name='map_new'),
)
urlpatterns += decorated_patterns('', [login_required_if_not_anonymous_allowed, never_cache, ],
    url(r'^map/create/$', views.MapCreate.as_view(), name='map_create'),
)
urlpatterns += decorated_patterns('', [map_permissions_check, never_cache, ],
    url(r'^map/(?P<map_id>[\d]+)/update/settings/$', views.MapUpdate.as_view(), name='map_update'),
    url(r'^map/(?P<map_id>[\d]+)/update/permissions/$', views.UpdateMapPermissions.as_view(), name='map_update_permissions'),
    url(r'^map/(?P<map_id>[\d]+)/update/delete/$', views.MapDelete.as_view(), name='map_delete'),
    url(r'^map/(?P<map_id>[\d]+)/update/clone/$', views.MapClone.as_view(), name='map_clone'),
    url(r'^map/(?P<map_id>[\d]+)/datalayer/create/$', views.DataLayerCreate.as_view(), name='datalayer_create'),
    url(r'^map/(?P<map_id>[\d]+)/datalayer/update/(?P<pk>\d+)/$', views.DataLayerUpdate.as_view(), name='datalayer_update'),
    url(r'^map/(?P<map_id>[\d]+)/datalayer/delete/(?P<pk>\d+)/$', views.DataLayerDelete.as_view(), name='datalayer_delete'),
)

########NEW FILE########
__FILENAME__ = utils
import gzip

from django.core.urlresolvers import get_resolver
from django.core.urlresolvers import RegexURLPattern, RegexURLResolver
from django.conf.urls import patterns


def get_uri_template(urlname, args=None, prefix=""):
    '''
    Utility function to return an URI Template from a named URL in django
    Copied from django-digitalpaper.

    Restrictions:
    - Only supports named urls! i.e. url(... name="toto")
    - Only support one namespace level
    - Only returns the first URL possibility.
    - Supports multiple pattern possibilities (i.e., patterns with
      non-capturing parenthesis in them) by trying to find a pattern
      whose optional parameters match those you specified (a parameter
      is considered optional if it doesn't appear in every pattern possibility)
    '''
    def _convert(template, args=None):
        """URI template converter"""
        if not args:
            args = []
        paths = template % dict([p, "{%s}" % p] for p in args)
        return u'%s/%s' % (prefix, paths)

    resolver = get_resolver(None)
    parts = urlname.split(':')
    if len(parts) > 1 and parts[0] in resolver.namespace_dict:
        namespace = parts[0]
        urlname = parts[1]
        nprefix, resolver = resolver.namespace_dict[namespace]
        prefix = prefix + '/' + nprefix.rstrip('/')
    possibilities = resolver.reverse_dict.getlist(urlname)
    for tmp in possibilities:
        possibility, pattern = tmp[:2]
        if not args:
            # If not args are specified, we only consider the first pattern
            # django gives us
            result, params = possibility[0]
            return _convert(result, params)
        else:
            # If there are optionnal arguments passed, use them to try to find
            # the correct pattern.
            # First, we need to build a list with all the arguments
            seen_params = []
            for result, params in possibility:
                seen_params.append(params)
            # Then build a set to find the common ones, and use it to build the
            # list of all the expected params
            common_params = reduce(lambda x, y: set(x) & set(y), seen_params)
            expected_params = sorted(common_params.union(args))
            # Then loop again over the pattern possibilities and return
            # the first one that strictly match expected params
            for result, params in possibility:
                if sorted(params) == expected_params:
                    return _convert(result, params)
    return None


class DecoratedURLPattern(RegexURLPattern):

    def resolve(self, *args, **kwargs):
        result = RegexURLPattern.resolve(self, *args, **kwargs)
        if result:
            for func in self._decorate_with:
                result.func = func(result.func)
        return result


def decorated_patterns(prefix, func, *args):
    """
    Utility function to decorate a group of url in urls.py

    Taken from http://djangosnippets.org/snippets/532/ + comments
    See also http://friendpaste.com/6afByRiBB9CMwPft3a6lym

    Example:
    urlpatterns = patterns('',
        url(r'^language/(?P<lang_code>[a-z]+)$', 'ops.common.views.change_language', name='change_language'),

        ) + decorated_patterns('', login_required, url(r'^', include('cms.urls')),
    )
    """
    result = patterns(prefix, *args)

    def decorate(result, func):
        for p in result:
            if isinstance(p, RegexURLPattern):
                p.__class__ = DecoratedURLPattern
                if not hasattr(p, "_decorate_with"):
                    setattr(p, "_decorate_with", [])
                p._decorate_with.append(func)
            elif isinstance(p, RegexURLResolver):
                for pp in p.url_patterns:
                    if isinstance(pp, RegexURLPattern):
                        pp.__class__ = DecoratedURLPattern
                        if not hasattr(pp, "_decorate_with"):
                            setattr(pp, "_decorate_with", [])
                        pp._decorate_with.append(func)
    if func:
        if isinstance(func, (list, tuple)):
            for f in func:
                decorate(result, f)
        else:
            decorate(result, func)

    return result


def smart_decode(s):
    """Convert a str to unicode when you cannot be sure of its encoding."""
    if isinstance(s, unicode):
        return s
    attempts = [
        ('utf-8', 'strict', ),
        ('latin-1', 'strict', ),
        ('utf-8', 'replace', ),
    ]
    for args in attempts:
        try:
            s = s.decode(*args)
        except:
            continue
        else:
            break
    return s


def gzip_file(from_path, to_path):
    with open(from_path, 'rb') as f_in:
        with gzip.open(to_path, 'wb') as f_out:
            f_out.writelines(f_in)

########NEW FILE########
__FILENAME__ = views
# -*- coding:utf-8 -*-

import os
import hashlib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as do_logout
from django.contrib.auth.models import User
from django.core.signing import Signer, BadSignature
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseRedirect, CompatibleStreamingHttpResponse)
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.translation import ugettext as _
from django.views.generic import View
from django.views.generic import DetailView
from django.views.generic.detail import BaseDetailView
from django.views.generic.list import ListView
from django.views.generic.base import TemplateView, RedirectView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.utils.http import http_date
from django.middleware.gzip import re_accepts_gzip

from .models import Map, DataLayer, TileLayer, Pictogram, Licence
from .utils import get_uri_template, gzip_file
from .forms import (DataLayerForm, UpdateMapPermissionsForm, MapSettingsForm,
                    AnonymousMapPermissionsForm, DEFAULT_LATITUDE,
                    DEFAULT_LONGITUDE, FlatErrorList)


# ############## #
#     Utils      #
# ############## #

def _urls_for_js(urls=None):
    """
    Return templated URLs prepared for javascript.
    """
    if urls is None:
        # prevent circular import
        from .urls import urlpatterns
        urls = [url.name for url in urlpatterns if getattr(url, 'name', None)]
    urls = dict(zip(urls, [get_uri_template(url) for url in urls]))
    urls.update(getattr(settings, 'LEAFLET_STORAGE_EXTRA_URLS', {}))
    return urls


def render_to_json(templates, response_kwargs, context, request):
    """
    Generate a JSON HttpResponse with rendered template HTML.
    """
    html = render_to_string(
        templates,
        response_kwargs,
        RequestContext(request, context)
    )
    _json = simplejson.dumps({
        "html": html
    })
    return HttpResponse(_json)


def simple_json_response(**kwargs):
    return HttpResponse(simplejson.dumps(kwargs))


# ############## #
#      Map       #
# ############## #


class FormLessEditMixin(object):
    http_method_names = [u'post', ]

    def form_invalid(self, form):
        return simple_json_response(errors=form.errors, error=unicode(form.errors))

    def get_form(self, form_class):
        kwargs = self.get_form_kwargs()
        kwargs['error_class'] = FlatErrorList
        return form_class(**kwargs)


class MapDetailMixin(object):

    model = Map

    def get_context_data(self, **kwargs):
        context = super(MapDetailMixin, self).get_context_data(**kwargs)
        properties = {}
        properties['datalayers'] = self.get_datalayers()
        properties['urls'] = _urls_for_js()
        properties['tilelayers'] = self.get_tilelayers()
        if self.get_short_url():
            properties['shortUrl'] = self.get_short_url()

        if settings.USE_I18N:
            locale = settings.LANGUAGE_CODE
            # Check attr in case the middleware is not active
            if hasattr(self.request, "LANGUAGE_CODE"):
                locale = self.request.LANGUAGE_CODE
            properties['locale'] = locale
            context['locale'] = locale
        properties['allowEdit'] = self.is_edit_allowed()
        properties["default_iconUrl"] = "%sstorage/src/img/marker.png" % settings.STATIC_URL
        properties['storage_id'] = self.get_storage_id()
        properties['licences'] = dict((l.name, l.json) for l in Licence.objects.all())
        # if properties['locateOnLoad']:
        #     properties['locate'] = {
        #         'setView': True,
        #         'enableHighAccuracy': True,
        #         'timeout': 3000
        #     }
        map_settings = self.get_geojson()
        if not "properties" in map_settings:
            map_settings['properties'] = {}
        map_settings['properties'].update(properties)
        context['map_settings'] = simplejson.dumps(map_settings, indent=settings.DEBUG)
        return context

    def get_tilelayers(self):
        return TileLayer.get_list(selected=TileLayer.get_default())

    def get_datalayers(self):
        return []

    def is_edit_allowed(self):
        return True

    def get_storage_id(self):
        return None

    def get_geojson(self):
        return {
            "geometry": {
                "coordinates": [DEFAULT_LONGITUDE, DEFAULT_LATITUDE],
                "type": "Point"
            }
        }

    def get_short_url(self):
        return None


class MapView(MapDetailMixin, DetailView):

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.can_view(request):
            return HttpResponseForbidden('Forbidden')
        return super(MapView, self).get(request, *args, **kwargs)

    def get_datalayers(self):
        datalayers = DataLayer.objects.filter(map=self.object)  # TODO manage state
        return [l.metadata for l in datalayers]

    def get_tilelayers(self):
        return TileLayer.get_list(selected=self.object.get_tilelayer())

    def is_edit_allowed(self):
        if self.request.user.is_authenticated():
            allow_edit = self.object.can_edit(self.request.user, self.request)
        else:
            # Default to True: display buttons for anonymous, they can
            # login from action process
            allow_edit = True
        return allow_edit

    def get_storage_id(self):
        return self.object.pk

    def get_short_url(self):
        shortUrl = None
        if hasattr(settings, 'SHORT_SITE_URL'):
            short_url_name = getattr(settings, 'MAP_SHORT_URL_NAME', 'map_short_url')
            short_path = reverse_lazy(short_url_name, kwargs={'pk': self.object.pk})
            shortUrl = "%s%s" % (settings.SHORT_SITE_URL, short_path)
        return shortUrl

    def get_geojson(self):
        settings = self.object.settings
        if not "properties" in settings:
            settings['properties'] = {}
        if self.object.owner:
            settings['properties']['author'] = {
                'name': self.object.owner.get_username(),
                'link': reverse('user_maps', args=(self.object.owner.get_username(), ))
            }
        return settings


class MapViewGeoJSON(MapView):

    def render_to_response(self, context, *args, **kwargs):
        return HttpResponse(context['map_settings'])


class MapNew(MapDetailMixin, TemplateView):
    template_name = "leaflet_storage/map_detail.html"


class MapCreate(FormLessEditMixin, CreateView):
    model = Map
    form_class = MapSettingsForm

    def form_valid(self, form):
        if self.request.user.is_authenticated():
            form.instance.owner = self.request.user
        self.object = form.save()
        if not self.request.user.is_authenticated():
            anonymous_url = "%s%s" % (
                settings.SITE_URL,
                self.object.get_anonymous_edit_url()
            )
            msg = _(
                "Your map has been created! If you want to edit this map from "
                "another computer, please use this link: %(anonymous_url)s"
                % {"anonymous_url": anonymous_url}
            )
        else:
            msg = _("Congratulations, your map has been created!")
        response = simple_json_response(
            id=self.object.pk,
            url=self.object.get_absolute_url(),
            info=msg
        )
        if not self.request.user.is_authenticated():
            key, value = self.object.signed_cookie_elements
            response.set_signed_cookie(key, value)
        return response


class MapUpdate(FormLessEditMixin, UpdateView):
    model = Map
    form_class = MapSettingsForm
    pk_url_kwarg = 'map_id'

    def form_valid(self, form):
        self.object.settings = form.cleaned_data["settings"]
        self.object.save()
        return simple_json_response(
            id=self.object.pk,
            url=self.object.get_absolute_url(),
            info=_("Map has been updated!")
        )


class UpdateMapPermissions(UpdateView):
    template_name = "leaflet_storage/map_update_permissions.html"
    model = Map
    pk_url_kwarg = 'map_id'

    def get_form_class(self):
        if self.object.owner:
            return UpdateMapPermissionsForm
        else:
            return AnonymousMapPermissionsForm

    def get_form(self, form_class):
        form = super(UpdateMapPermissions, self).get_form(form_class)
        user = self.request.user
        if self.object.owner and not user == self.object.owner:
            del form.fields['edit_status']
            del form.fields['share_status']
        return form

    def form_valid(self, form):
        self.object = form.save()
        return simple_json_response(info=_("Map editors updated with success!"))

    def render_to_response(self, context, **response_kwargs):
        return render_to_json(self.get_template_names(), response_kwargs, context, self.request)


class MapDelete(DeleteView):
    model = Map
    pk_url_kwarg = "map_id"

    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        if not self.request.user == self.object.owner:
            return HttpResponseForbidden(_('Only its owner can delete the map.'))
        self.object.delete()
        return simple_json_response(redirect="/")


class MapClone(View):

    def post(self, *args, **kwargs):
        if not getattr(settings, "LEAFLET_STORAGE_ALLOW_ANONYMOUS", False) \
           and not self.request.user.is_authenticated():
            return HttpResponseForbidden('Forbidden')
        owner = self.request.user if self.request.user.is_authenticated() else None
        self.object = kwargs['map_inst'].clone(owner=owner)
        response = simple_json_response(redirect=self.object.get_absolute_url())
        if not self.request.user.is_authenticated():
            key, value = self.object.signed_cookie_elements
            response.set_signed_cookie(key, value)
            anonymous_url = "%s%s" % (
                settings.SITE_URL,
                self.object.get_anonymous_edit_url()
            )
            msg = _(
                "Your map has been cloned! If you want to edit this map from "
                "another computer, please use this link: %(anonymous_url)s"
                % {"anonymous_url": anonymous_url}
            )
        else:
            msg = _("Congratulations, your map has been cloned!")
        messages.info(self.request, msg)
        return response


class MapShortUrl(RedirectView):
    query_string = True

    def get_redirect_url(self, **kwargs):
        map_inst = get_object_or_404(Map, pk=kwargs['pk'])
        url = map_inst.get_absolute_url()
        if self.query_string:
            args = self.request.META.get('QUERY_STRING', '')
            if args:
                url = "%s?%s" % (url, args)
        return url


class MapOldUrl(RedirectView):
    """
    Handle map URLs from before anonymous allowing.
    """
    query_string = True

    def get_redirect_url(self, **kwargs):
        owner = get_object_or_404(User, username=self.kwargs['username'])
        map_inst = get_object_or_404(Map, slug=self.kwargs['slug'], owner=owner)
        url = map_inst.get_absolute_url()
        if self.query_string:
            args = self.request.META.get('QUERY_STRING', '')
            if args:
                url = "%s?%s" % (url, args)
        return url


class MapAnonymousEditUrl(RedirectView):

    def get(self, request, *args, **kwargs):
        signer = Signer()
        try:
            pk = signer.unsign(self.kwargs['signature'])
        except BadSignature:
            return HttpResponseForbidden('Bad Signature')
        else:
            map_inst = get_object_or_404(Map, pk=pk)
            url = map_inst.get_absolute_url()
            response = HttpResponseRedirect(url)
            if not map_inst.owner:
                key, value = map_inst.signed_cookie_elements
                response.set_signed_cookie(key, value)
            return response


# ############## #
#    DataLayer   #
# ############## #

class DataLayerView(BaseDetailView):
    model = DataLayer

    def render_to_response(self, context, **response_kwargs):
        path = self.object.geojson.path
        statobj = os.stat(path)
        response = None
        ext = '.gz'

        ae = self.request.META.get('HTTP_ACCEPT_ENCODING', '')
        if re_accepts_gzip.search(ae) and getattr(settings, 'LEAFLET_STORAGE_GZIP', True):
            gzip_path = "{path}{ext}".format(path=path, ext=ext)
            up_to_date = True
            if not os.path.exists(gzip_path):
                up_to_date = False
            else:
                gzip_statobj = os.stat(gzip_path)
                if statobj.st_mtime > gzip_statobj.st_mtime:
                    up_to_date = False
            if not up_to_date:
                gzip_file(path, gzip_path)
            path = gzip_path

        if getattr(settings, 'LEAFLET_STORAGE_ACCEL_REDIRECT', False):
            response = HttpResponse()
            response['X-Accel-Redirect'] = path
        elif getattr(settings, 'LEAFLET_STORAGE_X_SEND_FILE', False):
            response = HttpResponse()
            response['X-Sendfile'] = path
        else:
            # TODO IMS
            response = CompatibleStreamingHttpResponse(
                open(path, 'rb'),
                content_type='application/json'
            )
            response["Last-Modified"] = http_date(statobj.st_mtime)
            response['ETag'] = '"%s"' % hashlib.md5(response.content).hexdigest()
            response['Content-Length'] = str(len(response.content))
            if path.endswith(ext):
                response['Content-Encoding'] = 'gzip'
        return response


class DataLayerCreate(FormLessEditMixin, CreateView):
    model = DataLayer
    form_class = DataLayerForm

    def form_valid(self, form):
        form.instance.map = self.kwargs['map_inst']
        self.object = form.save()
        return simple_json_response(**self.object.metadata)


class DataLayerUpdate(FormLessEditMixin, UpdateView):
    model = DataLayer
    form_class = DataLayerForm

    def form_valid(self, form):
        if self.object.map != self.kwargs['map_inst']:
            return HttpResponseForbidden('Route to nowhere')
        self.object = form.save()
        return simple_json_response(**self.object.metadata)


class DataLayerDelete(DeleteView):
    model = DataLayer

    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        if self.object.map != self.kwargs['map_inst']:
            return HttpResponseForbidden('Route to nowhere')
        self.object.delete()
        return simple_json_response(info=_("Layer successfully deleted."))


# ############## #
#     Picto      #
# ############## #

class PictogramJSONList(ListView):
    model = Pictogram

    def render_to_response(self, context, **response_kwargs):
        content = [p.json for p in Pictogram.objects.all()]
        return simple_json_response(pictogram_list=content)


# ############## #
#     Generic    #
# ############## #

def logout(request):
    do_logout(request)
    return simple_json_response(redirect="/")


class LoginPopupEnd(TemplateView):
    """
    End of a loggin process in popup.
    Basically close the popup.
    """
    template_name = "leaflet_storage/login_popup_end.html"

########NEW FILE########
