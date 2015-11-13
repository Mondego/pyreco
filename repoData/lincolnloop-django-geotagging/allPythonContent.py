__FILENAME__ = options
import re

from django import forms
from django.contrib.gis.forms import GeometryField
from django.contrib.gis.gdal import OGRException

from geotagging.fixes.gis.admin.options import GeoGenericStackedInline
from geotagging.models import Geotag


class GeotagsAdminForm(forms.ModelForm):
    """Custom form to use for inline admin widget"""
    catchall = forms.CharField(widget=forms.Textarea, required=False)
    line = GeometryField(widget=forms.HiddenInput, null=True, required=False, 
                         geom_type='LINESTRING', srid=4326)
    polygon = GeometryField(widget=forms.HiddenInput, null=True, required=False,
                            geom_type='POLYGON', srid=4326)
    
    
    def full_clean(self):
        """
        Sets geom based on catchall value and erases any other geoms
        """
        if '%s-catchall' % self.prefix in self.data:
            value = self.data['%s-catchall' % self.prefix]
            self.data['%s-point' % self.prefix] = ''
            self.data['%s-line' % self.prefix] = ''
            self.data['%s-polygon' % self.prefix] = ''
            if re.search('POINT\((.*)\)', value):
                self.data['%s-point' % self.prefix] = value
            elif re.search('LINESTRING\((.*)\)', value):
                self.data['%s-line' % self.prefix] = value
            elif re.search('POLYGON\((.*)\)', value):
                self.data['%s-polygon' % self.prefix] = value
        super(GeotagsAdminForm, self).full_clean()
    
    def __init__(self, *args, **kwargs):
        super(GeotagsAdminForm, self).__init__(*args, **kwargs)
        
        # Prefill catchall field if geotag already exists
        if self.instance:
            found = False
            # get SRID of map widget
            srid = self.fields['point'].widget.params['srid']
            # get srid of geom in model
            for geom_type in ('point', 'line', 'polygon'):
                geom = getattr(self.instance, geom_type)
                if geom:
                    db_field = geom
                    found = True
                    break
            if not found:
                return
                
            # Transforming the geometry to the projection used on the
            # OpenLayers map.
            if db_field.srid != srid: 
                try:
                    ogr = db_field.ogr
                    ogr.transform(srid)
                    wkt = ogr.wkt
                except OGRException:
                    wkt = ''
            else:
                wkt = db_field.wkt
            self.fields['catchall'].initial = wkt



class GeotagsInline(GeoGenericStackedInline):
    """
    A single inline form for use in the admin
    """
    map_template = 'geotagging/admin/openlayer_multiwidget.html'
    # inject Open Street map if GDAL works
    from django.contrib.gis import gdal
    if gdal.HAS_GDAL:
        map_template = 'geotagging/admin/osm_multiwidget.html'
    template = 'geotagging/admin/edit_inline/geotagging_inline.html'
    model = Geotag
    max_num = 1
    form = GeotagsAdminForm

    
    def get_formset(self, request, obj=None, **kwargs):
        """
        Hacks up the form so we can remove some geometries that OpenLayers
        can't handle.
        """
        fset = super(GeotagsInline, self).get_formset(request, 
                                                      obj=None, **kwargs)
        # put catchall on top so the javascript can access it
        fset.form.base_fields.keyOrder.reverse()
        fset.form.base_fields['point'].label = "Geotag"
        # these fields aren't easily editable via openlayers
        for field in ('geometry_collection', 'multilinestring'):
            fset.form.Meta.exclude.append(field)
            del(fset.form.base_fields[field])
        return fset

########NEW FILE########
__FILENAME__ = options
from django.contrib.admin.options import BaseModelAdmin, InlineModelAdmin, \
                                         StackedInline, TabularInline
from geotagging.fixes.gis.admin.widgets import OpenLayersWidgetFixed as OpenLayersWidget

from django.contrib.gis.gdal import OGRGeomType
from django.contrib.gis.db import models

from django.contrib.contenttypes.generic import GenericInlineModelAdmin, \
                                    GenericStackedInline, GenericTabularInline

class GeoBaseModelAdmin(BaseModelAdmin):
    """
    The administration options class for Geographic models. Map settings
    may be overloaded from their defaults to create custom maps.
    """
    # The default map settings that may be overloaded -- still subject
    # to API changes.
    default_lon = 0
    default_lat = 0
    default_zoom = 4
    display_wkt = False
    display_srid = False
    extra_js = []
    num_zoom = 18
    max_zoom = False
    min_zoom = False
    units = False
    max_resolution = False
    max_extent = False
    modifiable = True
    mouse_position = True
    scale_text = True
    layerswitcher = True
    scrollable = True
    map_width = 600
    map_height = 400
    map_srid = 4326
    map_template = 'gis/admin/openlayers.html'
    openlayers_url = 'http://openlayers.org/api/2.8/OpenLayers.js'
    wms_url = 'http://labs.metacarta.com/wms/vmap0'
    wms_layer = 'basic'
    wms_name = 'OpenLayers WMS'
    debug = False
    widget = OpenLayersWidget
    # inject Open Street map if GDAL works
    from django.contrib.gis import gdal
    if gdal.HAS_GDAL:
        map_template = 'gis/admin/osm.html'
        extra_js = ['http://openstreetmap.org/openlayers/OpenStreetMap.js']
        num_zoom = 20
        map_srid = 900913
        max_extent = '-20037508,-20037508,20037508,20037508'
        max_resolution = 156543.0339
        units = 'm'


    def formfield_for_dbfield(self, db_field, **kwargs):
        """
        Overloaded from ModelAdmin so that an OpenLayersWidget is used
        for viewing/editing GeometryFields.
        """
        if isinstance(db_field, models.GeometryField):
            # Setting the widget with the newly defined widget.
            kwargs['widget'] = self.get_map_widget(db_field)
            return db_field.formfield(**kwargs)
        else:
            return super(GeoBaseModelAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    def get_map_widget(self, db_field):
        """
        Returns a subclass of the OpenLayersWidget (or whatever was specified
        in the `widget` attribute) using the settings from the attributes set 
        in this class.
        """
        is_collection = db_field._geom in ('MULTIPOINT', 'MULTILINESTRING', 'MULTIPOLYGON', 'GEOMETRYCOLLECTION')
        if is_collection:
            if db_field._geom == 'GEOMETRYCOLLECTION': collection_type = 'Any'
            else: collection_type = OGRGeomType(db_field._geom.replace('MULTI', ''))
        else:
            collection_type = 'None'

        class OLMap(self.widget):
            template = self.map_template
            geom_type = db_field._geom
            params = {'default_lon' : self.default_lon,
                      'default_lat' : self.default_lat,
                      'default_zoom' : self.default_zoom,
                      'display_wkt' : self.debug or self.display_wkt,
                      'geom_type' : OGRGeomType(db_field._geom),
                      'field_name' : db_field.name,
                      'is_collection' : is_collection,
                      'scrollable' : self.scrollable,
                      'layerswitcher' : self.layerswitcher,
                      'collection_type' : collection_type,
                      'is_linestring' : db_field._geom in ('LINESTRING', 'MULTILINESTRING'),
                      'is_polygon' : db_field._geom in ('POLYGON', 'MULTIPOLYGON'),
                      'is_point' : db_field._geom in ('POINT', 'MULTIPOINT'),
                      'num_zoom' : self.num_zoom,
                      'max_zoom' : self.max_zoom,
                      'min_zoom' : self.min_zoom,
                      'units' : self.units, #likely shoud get from object
                      'max_resolution' : self.max_resolution,
                      'max_extent' : self.max_extent,
                      'modifiable' : self.modifiable,
                      'mouse_position' : self.mouse_position,
                      'scale_text' : self.scale_text,
                      'map_width' : self.map_width,
                      'map_height' : self.map_height,
                      'srid' : self.map_srid,
                      'display_srid' : self.display_srid,
                      'wms_url' : self.wms_url,
                      'wms_layer' : self.wms_layer,
                      'wms_name' : self.wms_name,
                      'debug' : self.debug,
                      }
        return OLMap

# Using the Beta OSM in the admin requires the following:
#  (1) The Google Maps Mercator projection needs to be added
#      to your `spatial_ref_sys` table.  You'll need at least GDAL 1.5:
#      >>> from django.contrib.gis.gdal import SpatialReference
#      >>> from django.contrib.gis.utils import add_postgis_srs
#      >>> add_postgis_srs(SpatialReference(900913)) # Adding the Google Projection 


#inlines
class GeoInlineModelAdmin(InlineModelAdmin, GeoBaseModelAdmin):
    def _media(self):
        "Injects OpenLayers JavaScript into the admin."
        media = super(GeoInlineModelAdmin, self)._media()
        media.add_js([self.openlayers_url])
        media.add_js(self.extra_js)
        return media
    media = property(_media)

class GeoStackedInline(StackedInline, GeoInlineModelAdmin):
    pass
class GeoTabularInline(TabularInline, GeoInlineModelAdmin):
    map_width = 300
    map_height = 200
    
#generic inlines
class GeoGenericInlineModelAdmin(GenericInlineModelAdmin, GeoInlineModelAdmin):
    pass
        
class GeoGenericStackedInline(GenericStackedInline, GeoGenericInlineModelAdmin):
    pass
class GeoGenericTablularInline(GenericTabularInline, GeoGenericInlineModelAdmin):
    map_width = 300
    map_height = 200

########NEW FILE########
__FILENAME__ = widgets
from django.conf import settings
from django.contrib.gis.admin.widgets import OpenLayersWidget
from django.contrib.gis.geos import GEOSGeometry, GEOSException
from django.contrib.gis.gdal import OGRException
from django.template import loader, Context
from django.utils import translation

# Creating a template context that contains Django settings
# values needed by admin map templates.
geo_context = Context({'ADMIN_MEDIA_PREFIX' : settings.ADMIN_MEDIA_PREFIX,
                       'LANGUAGE_BIDI' : translation.get_language_bidi(),
                       })

class OpenLayersWidgetFixed(OpenLayersWidget):
    """
    Renders an OpenLayers map using the WKT of the geometry.
    """
    def render(self, name, value, attrs=None):
        attrs['field_name'] = name
        # Update the template parameters with any attributes passed in.
        if attrs: self.params.update(attrs)
        # Defaulting the WKT value to a blank string -- this
        # will be tested in the JavaScript and the appropriate
        # interfaace will be constructed.
        self.params['wkt'] = ''

        # If a string reaches here (via a validation error on another
        # field) then just reconstruct the Geometry.
        if isinstance(value, basestring):
            try:
                value = GEOSGeometry(value)
            except (GEOSException, ValueError):
                value = None

        if value and value.geom_type.upper() != self.geom_type:
            value = None

        # Constructing the dictionary of the map options.
        self.params['map_options'] = self.map_options()

        # Constructing the JavaScript module name using the ID of
        # the GeometryField (passed in via the `attrs` keyword).
        js_safe_field_name = self.params['field_name'].replace('-', '__')
        self.params['module'] = 'geodjango_%s' % js_safe_field_name

        if value:
            # Transforming the geometry to the projection used on the
            # OpenLayers map.
            srid = self.params['srid']
            if value.srid != srid: 
                try:
                    ogr = value.ogr
                    ogr.transform(srid)
                    wkt = ogr.wkt
                except OGRException:
                    wkt = ''
            else:
                wkt = value.wkt
               
            # Setting the parameter WKT with that of the transformed
            # geometry.
            self.params['wkt'] = wkt
        return loader.render_to_string(self.template, self.params,
                                       context_instance=geo_context)
########NEW FILE########
__FILENAME__ = managers
"""
Custom managers for Django models registered with the geotagging
application.
"""
from django.db import models

from geotagging.models import Geotag

class ModelGeotagManager(models.Manager):
    """
    A manager for retrieving tags for a particular model.
    """
    # TODO: when does this actually get called and what should be here?
    pass


class GeotagDescriptor(object):
    """
    A descriptor which provides access to a ``ModelGeotagManager`` for
    model classes and simple retrieval, updating and deletion of tags
    for model instances.
    """
    def __get__(self, instance, owner):
        if not instance:
            tag_manager = ModelGeotagManager()
            tag_manager.model = owner
            return tag_manager
        else:
            return Geotag.objects.get_for_object(instance)

    def __set__(self, instance, value):
        Geotag.objects.update_geotag(instance, value)

    def __delete__(self, instance):
        Geotag.objects.update_geotag(instance, None)

########NEW FILE########
__FILENAME__ = models
from django.contrib.gis.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from django.db import connection

HAS_GEOGRAPHY = False
try:
    # You need Django 1.2 and PostGIS > 1.5
    # http://code.djangoproject.com/wiki/GeoDjango1.2#PostGISGeographySupport 
    if connection.ops.geography:
        HAS_GEOGRAPHY = True
except AttributeError:
    pass
    
def field_kwargs(verbose_name):
    """
    Build kwargs for field based on the availability of geography fields
    """
    kwargs = {
        'blank': True,
        'null': True,
        'verbose_name': _(verbose_name),
    }
    if HAS_GEOGRAPHY:
        kwargs['geography'] = True
    return kwargs

class GeotagManager(models.GeoManager):
    def get_for_object(self, obj):
        """
        Returns the Geotag associated with the given object or None.
        """
        ctype = ContentType.objects.get_for_model(obj)
        try:
            return self.get(content_type=ctype, object_id=obj.pk)
        except ObjectDoesNotExist:
            pass
        return None
        
    def update_geotag(self, obj, geotag):
        """
        Updates the geotag associated with an object
        """
        geotag_obj = self.get_for_object(obj)
        if not geotag_obj and not geotag:
        # you are trying to delete a geotag that does not exist. do nothing
            return 
        if not geotag_obj:
            ctype = ContentType.objects.get_for_model(obj)
            geotag_obj = self.create(content_type=ctype, object_id=obj.pk)
        if not geotag:
            geotag_obj.delete()
        else:
            old_geotag_geom = geotag_obj.get_geom()
            if old_geotag_geom:
                old_field_name = old_geotag_geom.geom_type.lower()
                setattr(geotag_obj, old_field_name, None)
            field_name = geotag.geom_type.lower()
            setattr(geotag_obj, field_name, geotag)
            geotag_obj.save()
        
        

class Geotag(models.Model):
    """
    A simple wrapper around the GeoDjango field types
    """

    # Content-object field
    content_type = models.ForeignKey(ContentType,
                                 related_name="content_type_set_for_%(class)s")
    object_id = models.PositiveIntegerField(_('object ID'), max_length=50)
    tagged_obj = generic.GenericForeignKey(ct_field="content_type", 
                                           fk_field="object_id")
    
    point = models.PointField(**field_kwargs('point'))
    multilinestring = models.MultiLineStringField(**field_kwargs('multi-line'))
    line = models.LineStringField(**field_kwargs('line'))
    polygon = models.PolygonField(**field_kwargs('polygon'))
    geometry_collection = models.GeometryCollectionField(
                                        **field_kwargs('geometry collection'))
    
    objects = GeotagManager()
    
    def get_geom(self):
        """Returns the geometry in use or None"""
        for geom_type in ('point', 'line', 'multilinestring', 
                          'polygon', 'geometry_collection'):
            geom = getattr(self, geom_type)
            if geom:
                return geom
        return None


########NEW FILE########
__FILENAME__ = geotagging_tags
from django import template
from django.conf import settings
from django.contrib.gis.measure import D
from django.db import models
from django.db.models import Q

from geotagging.models import Geotag, HAS_GEOGRAPHY

register = template.Library()

class GetGeotagsNode(template.Node):
    def __init__(self, geom, asvar=None, miles=5):
        self.geom = geom
        self.asvar = asvar
        self.distance = D(mi=miles)
        
    def render(self, context):
        try:
            geom = template.resolve_variable(self.geom, context)
        except template.VariableDoesNotExist:
            return ""
            
        # spheroid will result in more accurate results, but at the cost of
        # performance: http://code.djangoproject.com/ticket/6715
        if HAS_GEOGRAPHY:
            objects = Geotag.objects.filter(
                        Q(point__distance_lte=(geom, self.distance)) |
                        Q(line__distance_lte=(geom, self.distance)) |
                        Q(multilinestring__distance_lte=(geom, self.distance)) |
                        Q(polygon__distance_lte=(geom, self.distance)))
        else:
            if geom.geom_type != 'Point':
                raise template.TemplateSyntaxError("Geotagging Error: This database does not support non-Point geometry distance lookups.")
            else:
                objects = Geotag.objects.filter(point__distance_lte=(geom, 
                                                                 self.distance))
        context[self.asvar] = objects
        return ""

@register.tag
def get_objects_nearby(parser, token):
    """
    Populates a context variable with a list of :model:`geotagging.Geotag` objects
    that are within a given distance of a map geometry (point, line, polygon).
    Example::
    
        {% get_objects_nearby obj.point as nearby_objects %}
        
    This will find all objects tagged within 5 miles of ``obj.point``. To
    search within a different radius, use the following format::
        
        {% get_objects_nearby obj.point within 10 as nearby_objects %}
    
    This will find all objects tagged within 10 miles of ``obj.point``.
    
    *Note: Distances queries are approximate and may vary slightly from
    true measurements.*
    
    """
    
    bits = token.split_contents()
    item = bits[1]
    args = {}
    
    if len(bits) < 4:
        raise template.TemplateSyntaxError("%r tag takes at least 4 arguments" % bits[0])

    biter = iter(bits[2:])
    for bit in biter:
        if bit == "as":
            args["asvar"] = biter.next()
        elif bit == "within":
            args["miles"] = biter.next()
        else:
            raise template.TemplateSyntaxError("%r tag got an unknown argument: %r" % (bits[0], bit))
    
    return GetGeotagsNode(item, **args)

########NEW FILE########
__FILENAME__ = model_tests
from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point, Polygon

from geotagging.models import Geotag
from geotagging import register, AlreadyRegistered

class ModelTest(TestCase):
    
    def setUp(self):
        try:
            register(User)
        except AlreadyRegistered:
            pass
        self.obj = User.objects.create(username='user')
        self.point = Point(5, 5)
        self.poly = Polygon(((0, 0), (0, 10), (10, 10), (0, 10), (0, 0)),
                               ((4, 4), (4, 6), (6, 6), (6, 4), (4, 4)))
        
    def testEmptyGeotag(self):
        "Empty geotag returns none"
        self.assertEqual(self.obj.geotag, None)
    
    def testSetGeotag(self):
        "Geotag can be set on the object"
        self.obj.geotag = self.point
        self.assertEqual(self.obj.geotag.point, self.point)
        geotag = Geotag.objects.get_for_object(self.obj)
        self.assertEqual(geotag.point, self.point)
    
    def testChangeGeotag(self):
        "Geotag can be changed on the object"
        self.obj.geotag = self.point
        self.obj.geotag = self.poly
        self.assertEqual(self.obj.geotag.polygon, self.poly)
        geotag = Geotag.objects.get_for_object(self.obj)
        self.assertEqual(geotag.point, None)
        self.assertEqual(geotag.polygon, self.poly)
    
    def testGetGeomGeotag(self):
        "Geotag can find the right geom"
        self.obj.geotag = self.poly
        self.assertEqual(self.obj.geotag.get_geom(), self.poly)
        
    def testDeleteGeotag(self):
        "Geotag can be removed from the object"
        self.obj.geotag = None
        self.assertEqual(self.obj.geotag, None)
        geotag = Geotag.objects.get_for_object(self.obj)
        self.assertEqual(geotag, None)
        
########NEW FILE########
__FILENAME__ = tag_tests
from django import template
from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point, LineString

from geotagging.models import Geotag, HAS_GEOGRAPHY

class TagTestCase(TestCase):
    """Helper class with some tag helper functions"""
    
    def installTagLibrary(self, library):
        template.libraries[library] = __import__(library)
        
    def renderTemplate(self, tstr, **context):
        tmpl = template.Template(tstr)
        cntxt = template.Context(context)
        return tmpl.render(cntxt)

class OutputTagTest(TagTestCase):
    
    def setUp(self):
        self.installTagLibrary('geotagging.templatetags.geotagging_tags')
        denver_user = User.objects.create(username='denver')
        dia_user = User.objects.create(username='dia')
        aa_user = User.objects.create(username='annarbor')
	self.line = LineString((-104.552299, 38.128626), (-103.211191, 40.715081))
        self.denver = Geotag.objects.create(tagged_obj=denver_user,
                            point=Point(-104.9847034, 39.739153600000002))
        dia = Geotag.objects.create(tagged_obj=dia_user,
                            point=Point(-104.673856, 39.849511999999997))
        aa = Geotag.objects.create(tagged_obj=aa_user,
                            point=Point(-83.726329399999997, 42.2708716))
        
    def testOutput(self):
        "get_objects_nearby tag has no output"
        tmpl = "{% load geotagging_tags %}"\
                   "{% get_objects_nearby obj.point as nearby_objs %}"
        o = self.renderTemplate(tmpl, obj=self.denver)
        self.assertEqual(o.strip(), "")
        
    def testAsVar(self):
        tmpl = "{% load geotagging_tags %}"\
                   "{% get_objects_nearby obj.point as nearby_objs %}"\
                   "{{ nearby_objs|length }}"
        o = self.renderTemplate(tmpl, obj=self.denver)
        self.assertEqual(o.strip(), "1")

    def testShortDistance(self):
        # DIA is about 18 miles from downtown Denver
        short_tmpl = "{% load geotagging_tags %}"\
                   "{% get_objects_nearby obj.point as nearby_objs within 17 %}"\
                   "{{ nearby_objs|length }}"
        o = self.renderTemplate(short_tmpl, obj=self.denver)
        self.assertEqual(o.strip(), "1")
        long_tmpl = short_tmpl.replace("17", "19")
        o = self.renderTemplate(long_tmpl, obj=self.denver)
        self.assertEqual(o.strip(), "2")

    def testLongDistance(self):
        # Ann Arbor is about 1122 miles from Denver
        short_tmpl = "{% load geotagging_tags %}"\
                   "{% get_objects_nearby obj.point within 1115 as nearby_objs %}"\
                   "{{ nearby_objs|length }}"
        o = self.renderTemplate(short_tmpl, obj=self.denver)
        self.assertEqual(o.strip(), "2")
        long_tmpl = short_tmpl.replace("1115", "1125")
        o = self.renderTemplate(long_tmpl, obj=self.denver)
        self.assertEqual(o.strip(), "3")
        
    def testNonPoint(self):
        hit_tmpl = "{% load geotagging_tags %}"\
                   "{% get_objects_nearby line within 50 as nearby_objs %}"\
                   "{{ nearby_objs|length }}"
        miss_tmpl = hit_tmpl.replace("50", "10")
        
        if HAS_GEOGRAPHY:
            hit = self.renderTemplate(hit_tmpl, line=self.line)
            self.assertEqual(hit.strip(), "1")
            miss = self.renderTemplate(miss_tmpl, line=self.line)
            self.assertEqual(miss.strip(), "0")
        else:
            try:
                hit = self.renderTemplate(hit_tmpl, line=self.line)
                # the previous line should always render an exception
                self.assertEqual(True, False)
            except template.TemplateSyntaxError, e:
                self.assertEqual(e.args[0], 'Geotagging Error: This database does not support non-Point geometry distance lookups.')
        
class SyntaxTagTest(TestCase):
    
    def getNode(self, strng):
        from geotagging.templatetags.geotagging_tags import get_objects_nearby
        return get_objects_nearby(None, template.Token(template.TOKEN_BLOCK, 
                                                       strng))
        
    def assertNodeException(self, strng):
        self.assertRaises(template.TemplateSyntaxError, 
                          self.getNode, strng)

    def testInvalidSyntax(self):
        self.assertNodeException("get_objects_nearby as")
        self.assertNodeException("get_objects_nearby notas objects_nearby")

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from geotagging.views import kml_feed, kml_feed_map, kml_feeds_map
from geotagging.views import neighborhood_monitoring, kml_neighborhood_feed


urlpatterns = patterns('',

    # KML feeds
    url(r'^kml_feed/(?P<geotag_field_name>point|line|polygon)/$',kml_feed,
        name="geotagging-kml_feed"),
    url(r'^kml_feed/(?P<geotag_field_name>point|line|polygon)/(?P<content_type_name>[a-z ]+)/$',
        kml_feed,
        name="geotagging-kml_feed_per_contenttype"),

    # KML Feeds visualiser
    url(r'^kml_feeds_map/all/$', kml_feeds_map,
        name="geotagging-kml_feeds_map"),
    url(r'^kml_feeds_map/all/(?P<content_type_name>[a-z]+)/$', kml_feeds_map,
        name="geotagging-kml_feeds_map_per_contenttype"),

    url(r'^kml_feed_map/(?P<geotag_field_name>[a-z]+)/$', kml_feed_map,
        name="geotagging-kml_feed_map"),
    url(r'^kml_feed_map/(?P<geotag_field_name>[a-z]+)/(?P<content_type_name>[a-z ]+)/$', kml_feed_map,
        name="geotagging-kml_feed_map_per_contenttype"),

    # neighborhood monitoring
    url(r'^neighborhood_monitoring/(?P<distance_lt_km>\d*)/$',
        neighborhood_monitoring,
        name="geotagging-neighborhood_monitoring"),
    url(r'^kml_neighborhood_feed/(?P<distance_lt_km>\d*)/$',
        kml_neighborhood_feed,
        name="geotagging-kml_neighborhood_feed"),
)

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.measure import D
from django.contrib.gis.shortcuts import render_to_kml
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic.simple import direct_to_template


from geotagging.models import Geotag

def kml_feed(request, template="geotagging/geotagging.kml",
             geotag_field_name=None, content_type_name=None,
             object_id=None):
    """
    Return a KML feed of a particular geotag type : point, line, polygon
    This feed can be restricted by content_type and object_id.
    """
    if geotag_field_name:
        kw = str('%s__isnull' % geotag_field_name)
        geotagging = Geotag.objects.filter(**{kw:False})
    if content_type_name:
        geotagging = geotagging.objects.filter(content_type__name=content_type_name)
    if object_id:
        geotagging = geotagging.filter(object_id=object_id)
    context = RequestContext(request, {
        'places' : geotagging.kml(),
    })
    return render_to_kml(template,context_instance=context)

def kml_feed_map(request,template="geotagging/view_kml_feed.html",
                 geotag_field_name=None, content_type_name=None):
    """
    Direct the user to a template with all the required parameters to render
    the KML feed on a google map.
    """
    if content_type_name:
        kml_feed = reverse("geotagging-kml_feed_per_contenttype",
                           kwargs={
                            "geotag_field_name" : geotag_class_name,
                            "content_type_name" : content_type_name,
                            })
    else:
        kml_feed = reverse("geotagging-kml_feed",kwargs={"geotag_class_name":geotag_class_name})


    extra_context = {
        "kml_feed" : kml_feed
    }
    return direct_to_template(request,template=template,extra_context=extra_context)

def kml_feeds_map(request,template="geotagging/view_kml_feeds.html",
                 content_type_name=None):
    """
    Direct the user to a template with all the required parameters to render
    the KML feeds (point, line, polygon) on a google map.
    """
    if content_type_name:
        kml_feed_point = reverse("geotagging-kml_feed_per_contenttype",
                           kwargs={
                            "geotag_class_name" : "point",
                            "content_type_name" : content_type_name,
                            })
        kml_feed_line = reverse("geotagging-kml_feed_per_contenttype",
                           kwargs={
                            "geotag_class_name" : "line",
                            "content_type_name" : content_type_name,
                            })
        kml_feed_polygon = reverse("geotagging-kml_feed_per_contenttype",
                           kwargs={
                            "geotag_class_name" : "polygon",
                            "content_type_name" : content_type_name,
                            })
    else:
        kml_feed_point = reverse("geotagging-kml_feed",kwargs={"geotag_class_name": "point"})
        kml_feed_line = reverse("geotagging-kml_feed",kwargs={"geotag_class_name": "line"})
        kml_feed_polygon = reverse("geotagging-kml_feed",kwargs={"geotag_class_name": "polygon"})


    extra_context = {
        "kml_feed_point" : kml_feed_point,
        "kml_feed_line" : kml_feed_line,
        "kml_feed_polygon" : kml_feed_polygon
    }
    return direct_to_template(request,template=template,extra_context=extra_context)



def kml_neighborhood_feed(request, template="geotagging/geotagging.kml",
             distance_lt_km=None ,content_type_name=None,
             object_id=None):
    """
    Return a KML feed of all the geotagging in a around the user. This view takes
    an argument called `distance_lt_km` which is the radius of the permeter your
    are searching in. This feed can be restricted based on the content type of
    the element you want to get.
    """
    from django.contrib.gis.utils import GeoIP
    gip=GeoIP()
    if request.META["REMOTE_ADDR"] != "127.0.0.1":
        user_ip = request.META["REMOTE_ADDR"]
    else:
        user_ip = "populous.com"
    user_location_pnt = gip.geos(user_ip)

    criteria_pnt = {
        "point__distance_lt" : (user_location_pnt,
                                D(km=float(distance_lt_km))
                                )
            }
    if content_type_name:
        criteria_pnt["content_type__name"]==content_type_name

    geotagging = Point.objects.filter(**criteria_pnt)

    context = RequestContext(request, {
        'places' : geotagging.kml(),

    })
    return render_to_kml(template,context_instance=context)

def neighborhood_monitoring(request,
                          template="geotagging/view_neighborhood_monitoring.html",
                          content_type_name=None, distance_lt_km=None):
    """
    Direct the user to a template that is able to render the `kml_neighborhood_feed`
    on a google map. This feed can be restricted based on the content type of
    the element you want to get.
    """
    if distance_lt_km == None:
        distance_lt_km = 10
    gip=GeoIP()
    if request.META["REMOTE_ADDR"] != "127.0.0.1":
        user_ip = request.META["REMOTE_ADDR"]
    else:
        user_ip = "populous.com"
    user_location_pnt = gip.geos(user_ip)

    kml_feed = reverse("geotagging-kml_neighborhood_feed",
                       kwargs={"distance_lt_km":distance_lt_km})
    criteria_pnt = {
        "point__distance_lt" : (user_location_pnt,
                                D(km=float(distance_lt_km))
                                )
            }
    geotag_points = Point.objects.filter(**criteria_pnt).distance(user_location_pnt).order_by("-distance")
    context = RequestContext(request, {
        "user_ip" : user_ip,
        "user_location_pnt" : user_location_pnt,
        "geotag_points" : geotag_points,
        "user_city" : gip.city(user_ip),
        "kml_feed" : kml_feed,
    })
    return render_to_response(template,context_instance=context)

########NEW FILE########
