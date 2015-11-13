__FILENAME__ = fields
# rest_framework_gis/fields.py

try:
    import simplejson as json
except ImportError:
    import json

from django.contrib.gis.geos import GEOSGeometry, GEOSException
from django.contrib.gis.gdal import OGRException
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from rest_framework.fields import WritableField


class GeometryField(WritableField):
    """
    A field to handle GeoDjango Geometry fields
    """
    type_name = 'GeometryField'

    def to_native(self, value):
        if isinstance(value, dict) or value is None:
            return value

        # Get GeoDjango geojson serialization and then convert it _back_ to
        # a Python object
        return json.loads(value.geojson)

    def from_native(self, value):
        if value == '' or value is None:
            return value

        if isinstance(value, dict):
            value = json.dumps(value)

        try:
            return GEOSGeometry(value)
        except (ValueError, GEOSException, OGRException, TypeError) as e:
            raise ValidationError(_('Invalid format: string or unicode input unrecognized as WKT EWKT, and HEXEWKB.'))

        return value
########NEW FILE########
__FILENAME__ = filters
from django.db.models import Q
from django.core.exceptions import ImproperlyConfigured
from django.contrib.gis.geos import Polygon
from django.contrib.gis import forms

from rest_framework.filters import BaseFilterBackend
from rest_framework.exceptions import ParseError

try:
    from django_filters import Filter
except ImportError:
    raise ImproperlyConfigured(
        'restframework-gis filters depend on package "django-filter" '
        'which is missing. Install with "pip install django-filter".'
    )


class InBBOXFilter(BaseFilterBackend):

    bbox_param = 'in_bbox'  # The URL query parameter which contains the bbox.

    def get_filter_bbox(self, request):
        bbox_string = request.QUERY_PARAMS.get(self.bbox_param, None)
        if not bbox_string:
            return None

        try:
            p1x, p1y, p2x, p2y = (float(n) for n in bbox_string.split(','))
        except ValueError:
            raise ParseError("Not valid bbox string in parameter %s."
                             % self.bbox_param)

        x = Polygon.from_bbox((p1x, p1y, p2x, p2y))
        return x

    def filter_queryset(self, request, queryset, view):
        filter_field = getattr(view, 'bbox_filter_field', None)
        include_overlapping = getattr(view, 'bbox_filter_include_overlapping', False)
        if include_overlapping:
            geoDjango_filter = 'bboverlaps'
        else:
            geoDjango_filter = 'contained'

        if not filter_field:
            return queryset

        bbox = self.get_filter_bbox(request)
        if not bbox:
            return queryset
        return queryset.filter(Q(**{'%s__%s' % (filter_field, geoDjango_filter): bbox}))


class GeometryFilter(Filter):
    field_class = forms.GeometryField


from .filterset import *

########NEW FILE########
__FILENAME__ = filterset
from django.contrib.gis.db import models
from django.contrib.gis.db.models.sql.query import ALL_TERMS

from django_filters import FilterSet

from .filters import GeometryFilter

class GeoFilterSet(FilterSet):
    GEOFILTER_FOR_DBFIELD_DEFAULTS = {
        models.GeometryField: {
            'filter_class': GeometryFilter
        },
    }

    def __new__(cls, *args, **kwargs):
        cls.filter_overrides.update(cls.GEOFILTER_FOR_DBFIELD_DEFAULTS)
        cls.LOOKUP_TYPES = sorted(ALL_TERMS)
        return super(GeoFilterSet, cls).__new__(cls)

########NEW FILE########
__FILENAME__ = parsers
# rest_framework_gis/parsers.py
########NEW FILE########
__FILENAME__ = serializers
# rest_framework_gis/serializers.py
from django.contrib.gis.db import models
from django.core.exceptions import ImproperlyConfigured
from django.contrib.gis.db.models.fields import GeometryField as django_GeometryField

from rest_framework.serializers import ModelSerializer, ModelSerializerOptions

from .fields import GeometryField


class MapGeometryField(dict):
    def __getitem__(self, key):
        if issubclass(key, django_GeometryField):
            return GeometryField
        return super(MapGeometryField, self).__getitem__(key)
    

class GeoModelSerializer(ModelSerializer):
    """
    A subclass of DFR ModelSerializer that adds support
    for GeoDjango fields to be serialized as GeoJSON
    compatible data
    """
    field_mapping = MapGeometryField(ModelSerializer.field_mapping)


class GeoFeatureModelSerializerOptions(ModelSerializerOptions):
    """
        Options for GeoFeatureModelSerializer
    """
    def __init__(self, meta):
        super(GeoFeatureModelSerializerOptions, self).__init__(meta)
        self.geo_field = getattr(meta, 'geo_field', None)
        # id field defaults to primary key of the model
        self.id_field = getattr(meta, 'id_field', meta.model._meta.pk.name)


class GeoFeatureModelSerializer(GeoModelSerializer):
    """
    A subclass of GeoModelSerializer 
    that outputs geojson-ready data as
    features and feature collections
    """
    _options_class = GeoFeatureModelSerializerOptions


    def __init__(self, *args, **kwargs):
        super(GeoFeatureModelSerializer, self).__init__(*args, **kwargs)
        if self.opts.geo_field is None:
            raise ImproperlyConfigured("You must define a 'geo_field'.")
        else:
            # TODO: make sure the geo_field is a GeoDjango geometry field
            # make sure geo_field is included in fields
            if self.opts.exclude:
                if self.opts.geo_field in self.opts.exclude:
                    raise ImproperlyConfigured("You cannot exclude your 'geo_field'.")
            if self.opts.fields:
                if self.opts.geo_field not in self.opts.fields:
                    self.opts.fields = self.opts.fields + (self.opts.geo_field, )
                    self.fields = self.get_fields()        

    def to_native(self, obj):
        """
        Serialize objects -> primitives.
        """
        ret = self._dict_class()
        ret.fields = {}
        if self.opts.id_field is not False:
            ret["id"] = ""
        ret["type"] = "Feature"
        ret["geometry"] = {}
        ret["properties"] = self._dict_class()
        
        for field_name, field in self.fields.items():
            field.initialize(parent=self, field_name=field_name)
            key = self.get_field_key(field_name)
            value = field.field_to_native(obj, field_name)
            
            if self.opts.id_field is not False and field_name == self.opts.id_field:
                ret["id"] = value
            elif field_name == self.opts.geo_field:
                ret["geometry"] = value
            else:
                ret["properties"][key] = value
            
            ret.fields[key] = field
            
        return ret  
 
    def _format_data(self):
        """
        Add GeoJSON compatible formatting to a serialized queryset list
        """
        _data = super(GeoFeatureModelSerializer, self).data
        if isinstance(_data, list):
            self._formatted_data = {}
            self._formatted_data["type"] = "FeatureCollection"
            self._formatted_data["features"] = _data
        else:
            self._formatted_data = _data

        return self._formatted_data

    @property
    def data(self):
        """
        Returns the serialized data on the serializer.
        """
        return self._format_data()

    def from_native(self, data, files):
        """
        Override the parent method to first remove the GeoJSON formatting
        """
        if 'features' in data:
            _unformatted_data = []
            features = data['features']
            for feature in features:
                _dict = feature["properties"]
                geom = { self.opts.geo_field: feature["geometry"] }
                _dict.update(geom)
                _unformatted_data.append(_dict)
        elif 'properties' in data:
            _dict = data["properties"]
            geom = { self.opts.geo_field: data["geometry"] }
            _dict.update(geom)
            _unformatted_data = _dict
        else:
            _unformatted_data = data
        
        data = _unformatted_data
        
        instance = super(GeoFeatureModelSerializer, self).from_native(data, files)
        if not self._errors:
            return self.full_clean(instance)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.conf import settings

GEODJANGO_IMPROVED_WIDGETS = 'olwidget' in settings.INSTALLED_APPS

if GEODJANGO_IMPROVED_WIDGETS:
    from olwidget.admin import GeoModelAdmin
else:
    from django.contrib.gis.admin import ModelAdmin as GeoModelAdmin

from .models import Location


class LocationAdmin(GeoModelAdmin):
    list_display = ('name', 'geometry')


admin.site.register(Location, LocationAdmin)
########NEW FILE########
__FILENAME__ = models
from django.contrib.gis.db import models
from django.utils.text import slugify


__all__ = ['Location']


class Location(models.Model):
    name = models.CharField(max_length=32)
    slug = models.SlugField(max_length=128, unique=True, blank=True)
    geometry = models.GeometryField()
    
    objects = models.GeoManager()
    
    def __unicode__(self):
        return self.name
    
    def _generate_slug(self):
        if self.slug == '' or self.slug is None:
            self.slug = slugify(unicode(self.name))
    
    def clean(self):
        self._generate_slug()
    
    def save(self, *args, **kwargs):
        self._generate_slug()
        super(Location, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = serializers
from rest_framework import pagination, serializers
from rest_framework_gis import serializers as gis_serializers

from .models import *


__all__ = [
    'LocationGeoSerializer',
    'PaginatedLocationGeoSerializer',
    'LocationGeoFeatureSerializer',
    'LocationGeoFeatureSlugSerializer',
    'LocationGeoFeatureFalseIDSerializer',
    'PaginatedLocationGeoFeatureSerializer',
]

  
class LocationGeoSerializer(gis_serializers.GeoModelSerializer):
    """ location geo serializer  """
    
    details = serializers.HyperlinkedIdentityField(view_name='api_location_details')
    
    class Meta:
        model = Location
        geo_field = 'geometry'


class PaginatedLocationGeoSerializer(pagination.PaginationSerializer):
    
    class Meta:
        object_serializer_class = LocationGeoSerializer


class LocationGeoFeatureSerializer(gis_serializers.GeoFeatureModelSerializer):
    """ location geo serializer  """
    
    details = serializers.HyperlinkedIdentityField(view_name='api_geojson_location_details')
    fancy_name = serializers.SerializerMethodField('get_fancy_name')
    
    def get_fancy_name(self, obj):
        return u'Kool %s' % obj.name
    
    class Meta:
        model = Location
        geo_field = 'geometry'


class LocationGeoFeatureSlugSerializer(LocationGeoFeatureSerializer):
    """ use slug as id attribute  """
    
    class Meta:
        model = Location
        geo_field = 'geometry'
        id_field = 'slug'


class LocationGeoFeatureFalseIDSerializer(LocationGeoFeatureSerializer):
    """ id attribute set as False """
    
    class Meta:
        model = Location
        geo_field = 'geometry'
        id_field = False


class PaginatedLocationGeoFeatureSerializer(pagination.PaginationSerializer):
    
    class Meta:
        object_serializer_class = LocationGeoFeatureSerializer
########NEW FILE########
__FILENAME__ = tests
"""
unit tests for restframework_gis
"""

try:
    import simplejson as json
except ImportError:
    import json


import urllib
from django.test import TestCase
from django.contrib.gis.geos import GEOSGeometry, Polygon
from django.core.urlresolvers import reverse

from .models import Location


class TestRestFrameworkGis(TestCase):
    
    def setUp(self):
        self.location_list_url = reverse('api_location_list')
        self.geojson_location_list_url = reverse('api_geojson_location_list')
        self.location_contained_in_bbox_list_url = reverse('api_geojson_location_list_contained_in_bbox_filter')
        self.location_overlaps_bbox_list_url = reverse('api_geojson_location_list_overlaps_bbox_filter')
        self.geos_error_message = 'Invalid format: string or unicode input unrecognized as WKT EWKT, and HEXEWKB.'
        self.geojson_contained_in_geometry = reverse('api_geojson_contained_in_geometry')
        
    def test_get_location_list(self):
        response = self.client.get(self.location_list_url)
        self.assertEqual(response.status_code, 200)
    
    def test_post_location_list_geojson(self):
        self.assertEqual(Location.objects.count(), 0)
        
        data = {
            "name": "geojson input test",
            "geometry": {
                "type": "GeometryCollection", 
                "geometries": [
                    {
                        "type": "Point", 
                        "coordinates": [
                            12.492324113849, 
                            41.890307434153
                        ]
                    }
                ]
            }
        }
        
        response = self.client.post(self.location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 1)
        
        data = {
            "name": "geojson input test2",
            "geometry": {
                "type": "Point", 
                "coordinates": [
                    12.492324113849, 
                    41.890307434153
                ]
            }
        }
        response = self.client.post(self.location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 2)
    
    def test_post_location_list_geojson_as_multipartformdata(self):
        """ emulate sending geojson string in webform """
        self.assertEqual(Location.objects.count(), 0)
        
        data = {
            "name": "geojson input test",
            "geometry": json.dumps({
                "type": "GeometryCollection", 
                "geometries": [
                    {
                        "type": "Point", 
                        "coordinates": [
                            12.492324113849, 
                            41.890307434153
                        ]
                    }
                ]
            })
        }
        
        response = self.client.post(self.location_list_url, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 1)
    
    def test_post_location_list_WKT(self):
        self.assertEqual(Location.objects.count(), 0)
        
        data = {
            'name': 'WKT input test',
            'geometry': 'POINT (12.492324113849 41.890307434153)'
        }
        response = self.client.post(self.location_list_url, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 1)
    
    def test_post_location_list_WKT_as_json(self):
        self.assertEqual(Location.objects.count(), 0)
        
        data = {
            'name': 'WKT input test',
            'geometry': 'POINT (12.492324113849 41.890307434153)'
        }
        response = self.client.post(self.location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 1)
    
    def test_post_location_list_empty_geometry(self):
        data = { 'name': 'empty input test' }
        response = self.client.post(self.location_list_url, data)
        self.assertEqual(response.data['geometry'][0], 'This field is required.')
        
        data = { 'name': 'empty input test', 'geometry': '' }
        response = self.client.post(self.location_list_url, data)
        self.assertEqual(response.data['geometry'][0], 'This field is required.')
        
        data = { 'name': 'empty input test' }
        response = self.client.post(self.location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.data['geometry'][0], 'This field is required.')
        
        data = { 'name': 'empty input test', 'geometry': '' }
        response = self.client.post(self.location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.data['geometry'][0], 'This field is required.')
    
    def test_post_location_list_invalid_WKT(self):        
        data = {
            'name': 'WKT wrong input test',
            'geometry': 'I AM OBVIOUSLY WRONG'
        }
        response = self.client.post(self.location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Location.objects.count(), 0)
        self.assertEqual(response.data['geometry'][0], self.geos_error_message)
        
        # repeat as multipart form data
        response = self.client.post(self.location_list_url, data)
        self.assertEqual(response.data['geometry'][0], self.geos_error_message)
        
        data = {
            'name': 'I AM MODERATELY WRONG',
            'geometry': 'POINT (12.492324113849, 41.890307434153)'
        }
        response = self.client.post(self.location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.data['geometry'][0], self.geos_error_message)
        
        # repeat as multipart form data
        response = self.client.post(self.location_list_url, data)
        self.assertEqual(response.data['geometry'][0], self.geos_error_message)
    
    def test_post_location_list_invalid_geojson(self):
        data = {
            "name": "quite wrong",
            "geometry": {
                "type": "ARRRR", 
                "dasdas": [
                    {
                        "STtype": "PTUAMAoint", 
                        "NNAare":"rgon"
                    }
                ]
            }
        }
        response = self.client.post(self.location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.data['geometry'][0], self.geos_error_message)
        
        data = {
            "name": "very wrong",
            "geometry": ['a', 'b', 'c']
        }
        response = self.client.post(self.location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.data['geometry'][0], self.geos_error_message)
        
        data = {
            "name": "very wrong",
            "geometry": False
        }
        response = self.client.post(self.location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.data['geometry'][0], self.geos_error_message)
        
        data = {
            "name": "very wrong",
            "geometry": { "value": { "nested": ["yo"] } }
        }
        response = self.client.post(self.location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.data['geometry'][0], self.geos_error_message)
    
    def test_geojson_format(self):
        """ test geojson format """
        location = Location.objects.create(name='geojson test', geometry='POINT (10.1 10.1)')
        
        url = reverse('api_geojson_location_details', args=[location.id])
        response = self.client.get(url)
        self.assertEqual(response.data['type'], "Feature")
        self.assertEqual(response.data['properties']['name'], "geojson test")
        self.assertEqual(response.data['properties']['fancy_name'], "Kool geojson test")
        self.assertEqual(response.data['geometry']['type'], "Point")
        self.assertEqual(json.dumps(response.data['geometry']['coordinates']), "[10.1, 10.1]")
    
    def test_geojson_id_attribute(self):
        location = Location.objects.create(name='geojson test', geometry='POINT (10.1 10.1)')
        
        url = reverse('api_geojson_location_details', args=[location.id])
        response = self.client.get(url)
        self.assertEqual(response.data['id'], location.id)
    
    def test_geojson_id_attribute_slug(self):
        location = Location.objects.create(name='geojson test', geometry='POINT (10.1 10.1)')
        
        url = reverse('api_geojson_location_slug_details', args=[location.slug])
        response = self.client.get(url)
        self.assertEqual(response.data['id'], location.slug)
    
    def test_geojson_false_id_attribute_slug(self):
        location = Location.objects.create(name='geojson test', geometry='POINT (10.1 10.1)')
        
        url = reverse('api_geojson_location_falseid_details', args=[location.id])
        response = self.client.get(url)
        with self.assertRaises(KeyError):
            response.data['id']
    
    def test_post_geojson_location_list(self):
        self.assertEqual(Location.objects.count(), 0)
        
        data = {
            "type": "Feature", 
            "properties": {
                "name": "point?",
                "details": "ignore this"
            }, 
            "geometry": {
                "type": "Point", 
                "coordinates": [
                    10.1, 
                    10.1
                ]
            }
        }
        
        response = self.client.post(self.geojson_location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 1)
        
        url = reverse('api_geojson_location_details', args=[Location.objects.order_by('-id')[0].id])
        response = self.client.get(url)
        self.assertEqual(response.data['properties']['name'], "point?")
        self.assertEqual(response.data['geometry']['type'], "Point")
        self.assertEqual(json.dumps(response.data['geometry']['coordinates']), "[10.1, 10.1]")
        self.assertNotEqual(response.data['properties']['details'], "ignore this")
    
    def test_post_invalid_geojson_location_list(self):
        data = {
            "type": "Feature", 
            "properties": {
                "details": "ignore this"
            }, 
            "geometry": {
                "type": "Point", 
                "coordinates": [
                    10.1, 
                    10.1
                ]
            }
        }
        
        response = self.client.post(self.geojson_location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Location.objects.count(), 0)
        self.assertEqual(response.data['name'][0], "This field is required.")
        
        data = {
            "type": "Feature", 
            "properties": {
                "name": "point?",
            }, 
            "geometry": {
                "type": "Point", 
                "WRONG": {}
            }
        }
        response = self.client.post(self.geojson_location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Location.objects.count(), 0)
        self.assertEqual(response.data['geometry'][0], self.geos_error_message)
    
    def test_post_geojson_location_list_WKT(self):
        self.assertEqual(Location.objects.count(), 0)
        
        data = {
            "type": "Feature", 
            "properties": {
                "name": "point?",
            }, 
            "geometry": "POINT (10.1 10.1)"
        }
        
        response = self.client.post(self.geojson_location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 1)
        
        url = reverse('api_geojson_location_details', args=[Location.objects.order_by('-id')[0].id])
        response = self.client.get(url)
        self.assertEqual(response.data['properties']['name'], "point?")
        self.assertEqual(response.data['geometry']['type'], "Point")
        self.assertEqual(json.dumps(response.data['geometry']['coordinates']), "[10.1, 10.1]")
    
    def test_geofeatured_model_serializer_compatible_with_geomodel_serializer(self):
        self.assertEqual(Location.objects.count(), 0)
        
        data = {
            "name": "geojson input test",
            "geometry": {
                "type": "GeometryCollection", 
                "geometries": [
                    {
                        "type": "Point", 
                        "coordinates": [
                            12.492324113849, 
                            41.890307434153
                        ]
                    }
                ]
            }
        }
        
        response = self.client.post(self.geojson_location_list_url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 1)
    
    def test_geofeatured_model_post_as_multipartformdata(self):
        """ emulate sending geojson string in webform """
        self.assertEqual(Location.objects.count(), 0)
        
        data = {
            "name": "geojson input test",
            "geometry": json.dumps({
                "type": "Point", 
                "coordinates": [
                    12.492324113849, 
                    41.890307434153
                ]
            })
        }
        
        response = self.client.post(self.location_list_url, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 1)
        self.assertEqual(response.data['geometry']['type'], "Point")
        
    def test_inBBOXFilter_filtering(self):
        """
        Checks that the inBBOXFilter returns only objects strictly contained
        in the bounding box given by the in_bbox URL parameter
        """
        self.assertEqual(Location.objects.count(), 0)
        
        # Bounding box
        xmin = 0
        ymin = 0
        xmax = 10
        ymax = 10
        
        url_params = '?in_bbox=%d,%d,%d,%d&format=json' % (xmin, ymin, xmax, ymax)
        
        # Square with bottom left at (1,1), top right at (9,9)
        isContained = Location()
        isContained.name = 'isContained'
        isContained.geometry = Polygon(((1,1),(9,1),(9,9),(1,9),(1,1)))
        isContained.save()
        
        isEqualToBounds = Location()
        isEqualToBounds.name = 'isEqualToBounds'
        isEqualToBounds.geometry = Polygon(((0,0),(10,0),(10,10),(0,10),(0,0)))
        isEqualToBounds.save()
        
        # Rectangle with bottom left at (-1,1), top right at (5,5)
        overlaps = Location()
        overlaps.name = 'overlaps'
        overlaps.geometry = Polygon(((-1,1),(5,1),(5,5),(-1,5),(-1,1)))
        overlaps.save()
        
        # Rectangle with bottom left at (-3,-3), top right at (-1,2)
        nonIntersecting = Location()
        nonIntersecting.name = 'nonIntersecting'
        nonIntersecting.geometry = Polygon(((-3,-3),(-1,-3),(-1,2),(-3,2),(-3,-3)))
        nonIntersecting.save()
        
        # Make sure we only get back the ones strictly contained in the bounding box
        response = self.client.get(self.location_contained_in_bbox_list_url + url_params)
        self.assertEqual(len(response.data['features']), 2)
        for result in response.data['features']:
            self.assertEqual(result['properties']['name'] in ('isContained', 'isEqualToBounds'), True)
        
        # Make sure we get overlapping results for the view which allows bounding box overlaps.
        response = self.client.get(self.location_overlaps_bbox_list_url + url_params)
        self.assertEqual(len(response.data['features']), 3)
        for result in response.data['features']:
            self.assertEqual(result['properties']['name'] in ('isContained', 'isEqualToBounds', 'overlaps'), True)

    def test_GeometryField_filtering(self):
        """ Checks that the GeometryField allows sane filtering. """
        self.assertEqual(Location.objects.count(), 0)

        treasure_island_geojson = """{
            "type": "Polygon",
            "coordinates": [
                [
                    [
                        -122.44640350341795,
                        37.86103094116189
                    ],
                    [
                        -122.44262695312501,
                        37.85506751416839
                    ],
                    [
                        -122.43481636047363,
                        37.853305500228025
                    ],
                    [
                        -122.42975234985352,
                        37.854660899304704
                    ],
                    [
                        -122.41953849792479,
                        37.852627791344894
                    ],
                    [
                        -122.41807937622069,
                        37.853305500228025
                    ],
                    [
                        -122.41868019104004,
                        37.86211514878027
                    ],
                    [
                        -122.42391586303711,
                        37.870584971740065
                    ],
                    [
                        -122.43035316467285,
                        37.8723465726078
                    ],
                    [
                        -122.43515968322752,
                        37.86963639998042
                    ],
                    [
                        -122.43953704833984,
                        37.86882332875222
                    ],
                    [
                        -122.44640350341795,
                        37.86103094116189
                    ]
                ]
            ]
        }"""
        
        treasure_island_geom = GEOSGeometry(treasure_island_geojson)
        treasure_island = Location()
        treasure_island.name = "Treasure Island"
        treasure_island.geometry = treasure_island_geom
        treasure_island.full_clean()
        treasure_island.save()

        ggpark_geojson = """{
            "type": "Polygon",
            "coordinates": [
                [
                    [
                        -122.5111198425293,
                        37.77125750792944
                    ],
                    [
                        -122.51026153564452,
                        37.76447260365713
                    ],
                    [
                        -122.45309829711913,
                        37.76677954095475
                    ],
                    [
                        -122.45481491088867,
                        37.77424266859531
                    ],
                    [
                        -122.5111198425293,
                        37.77125750792944
                    ]
                ]
            ]
        }"""
        ggpark_geom = GEOSGeometry(ggpark_geojson)
        ggpark = Location()
        ggpark.name = "Golden Gate Park"
        ggpark.geometry = ggpark_geom
        ggpark.save()

        point_inside_ggpark_geojson = """{ "type": "Point", "coordinates": [ -122.49034881591797, 37.76949349270407 ] }"""

        url_params = "?contains_properly=%s" % urllib.quote(point_inside_ggpark_geojson)

        response = self.client.get(self.geojson_contained_in_geometry + url_params)
        self.assertEqual(len(response.data), 1)
        
        geometry_response = GEOSGeometry(json.dumps(response.data[0]['geometry']))

        self.assertTrue(geometry_response.equals_exact(ggpark_geom))
        self.assertEqual(response.data[0]['name'], ggpark.name)
        
        # try without any param, should return both
        response = self.client.get(self.geojson_contained_in_geometry)
        self.assertEqual(len(response.data), 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url


urlpatterns = patterns('django_restframework_gis_tests.views',
    url(r'^$', 'location_list', name='api_location_list'),
    url(r'^(?P<pk>[0-9]+)/$', 'location_details', name='api_location_details'),
    
    # geojson
    url(r'^geojson/$', 'geojson_location_list', name='api_geojson_location_list'),
    url(r'^geojson/(?P<pk>[0-9]+)/$', 'geojson_location_details', name='api_geojson_location_details'),
    url(r'^geojson/(?P<slug>[-\w]+)/$', 'geojson_location_slug_details', name='api_geojson_location_slug_details'),
    url(r'^geojson-falseid/(?P<pk>[0-9]+)/$', 'geojson_location_falseid_details', name='api_geojson_location_falseid_details'),
    
    # Filters
    url(r'^filters/contained_in_bbox$', 'geojson_location_contained_in_bbox_list', name='api_geojson_location_list_contained_in_bbox_filter'),
    url(r'^filters/overlaps_bbox$', 'geojson_location_overlaps_bbox_list', name='api_geojson_location_list_overlaps_bbox_filter'),
    url(r'^filters/contained_in_geometry$', 'geojson_contained_in_geometry', name='api_geojson_contained_in_geometry'),
)

########NEW FILE########
__FILENAME__ = views
from rest_framework import generics
from rest_framework.filters import DjangoFilterBackend

from .models import *
from .serializers import *
from rest_framework_gis.filters import *


class LocationList(generics.ListCreateAPIView):
    model = Location
    serializer_class = LocationGeoSerializer
    pagination_serializer_class = PaginatedLocationGeoSerializer
    paginate_by_param = 'limit'
    paginate_by = 40
    
location_list = LocationList.as_view()
    
    
class LocationDetails(generics.RetrieveUpdateDestroyAPIView):
    model = Location
    serializer_class = LocationGeoSerializer

location_details = LocationDetails.as_view()


class GeojsonLocationList(generics.ListCreateAPIView):
    model = Location
    serializer_class = LocationGeoFeatureSerializer
    pagination_serializer_class = PaginatedLocationGeoFeatureSerializer
    paginate_by_param = 'limit'
    paginate_by = 40
    
geojson_location_list = GeojsonLocationList.as_view()


class GeojsonLocationContainedInBBoxList(generics.ListAPIView):
    model = Location
    serializer_class = LocationGeoFeatureSerializer
    queryset = Location.objects.all()
    bbox_filter_field = 'geometry'
    filter_backends = (InBBOXFilter,)

geojson_location_contained_in_bbox_list = GeojsonLocationContainedInBBoxList.as_view()


class GeojsonLocationOverlapsBBoxList(GeojsonLocationContainedInBBoxList):
    bbox_filter_include_overlapping = True

geojson_location_overlaps_bbox_list = GeojsonLocationOverlapsBBoxList.as_view()


class GeojsonLocationDetails(generics.RetrieveUpdateDestroyAPIView):
    model = Location
    serializer_class = LocationGeoFeatureSerializer

geojson_location_details = GeojsonLocationDetails.as_view()


class GeojsonLocationSlugDetails(generics.RetrieveUpdateDestroyAPIView):
    model = Location
    lookup_field = 'slug'
    serializer_class = LocationGeoFeatureSlugSerializer

geojson_location_slug_details = GeojsonLocationSlugDetails.as_view()


class GeojsonLocationFalseIDDetails(generics.RetrieveUpdateDestroyAPIView):
    model = Location
    serializer_class = LocationGeoFeatureFalseIDSerializer

geojson_location_falseid_details = GeojsonLocationFalseIDDetails.as_view()


class LocationFilter(GeoFilterSet):
    contains_properly = GeometryFilter(name='geometry', lookup_type='contains_properly')

    class Meta:
        model = Location


class GeojsonLocationContainedInGeometry(generics.ListAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationGeoSerializer
    filter_class = LocationFilter

    filter_backends = (DjangoFilterBackend,)

geojson_contained_in_geometry = GeojsonLocationContainedInGeometry.as_view()

########NEW FILE########
__FILENAME__ = local_settings.example
from settings import *

# RENAME THIS FILE local_settings.py IF YOU NEED TO CUSTOMIZE SOME SETTINGS
# BUT DO NOT COMMIT

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.contrib.gis.db.backends.postgis',
#        'NAME': 'django_restframework_gis',
#        'USER': 'postgres',
#        'PASSWORD': 'password',
#        'HOST': '127.0.0.1',
#        'PORT': '5433'
#    },
#}
#
#INSTALLED_APPS = (
#    'django.contrib.auth',
#    'django.contrib.contenttypes',
#    'django.contrib.sessions',
#    'django.contrib.messages',
#    'django.contrib.staticfiles',
#    'django.contrib.gis',
#    
#    # geodjango widgets
#    'olwidget',
#    
#    # admin
#    #'grappelli',
#    'django.contrib.admin',
#    
#    # rest framework
#    'rest_framework',
#    'rest_framework_gis',
#    
#    # test app
#    'django_restframework_gis_tests'
#)
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    try:
        import local_settings
        settings_module = 'local_settings'
    except ImportError:
        settings_module = 'settings'
    
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys
from os.path import abspath, dirname, join as pjoin
from django.conf import settings

try:
    from . import local_settings
except ImportError:
    from . import settings as local_settings


def runtests(test_labels=None, verbosity=1, interactive=True, failfast=True):
    here = abspath(dirname(__file__))
    root = pjoin(here, os.pardir)
    sys.path[0:0] = [root, here]
    labels = ['rest_framework', 'rest_framework_gis', 'django_restframework_gis_tests']
    test_labels = test_labels or labels
    if not settings.configured:
        settings.configure(
            DATABASES=local_settings.DATABASES,
            INSTALLED_APPS=labels,
            SECRET_KEY=local_settings.SECRET_KEY,
            ROOT_URLCONF=local_settings.ROOT_URLCONF
        )
    from django.test.utils import get_runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=verbosity, interactive=interactive, failfast=failfast)
    return test_runner.run_tests(['django_restframework_gis_tests'])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Runs the test suite for django-restframework-gis.')
    parser.add_argument(
        'test_labels',
        nargs='*',
        help='Test labels.',
    )
    parser.add_argument(
        '--noinput',
        dest='interactive',
        action='store_false',
        default=True,
        help='Do not prompt the user for input of any kind.',
    )
    parser.add_argument(
        '--failfast',
        dest='failfast',
        action='store_true',
        default=False,
        help='Stop running the test suite after first failed test.',
    )
    args = parser.parse_args()
    failures = runtests(
        test_labels=args.test_labels,
        verbosity=1,
        interactive=args.interactive,
        failfast=args.failfast
    )
    if failures:
        sys.exit(bool(failures))

########NEW FILE########
__FILENAME__ = settings
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'django_restframework_gis',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': '',
        'PORT': ''
    },
}

SECRET_KEY = 'fn)t*+$)ugeyip6-#txyy$5wf2ervc0d2n#h)qb)y5@ly$t*@w'

INSTALLED_APPS = (
    # rest framework
    'rest_framework',
    'rest_framework_gis',
    
    # test app
    'django_restframework_gis_tests'
)

ROOT_URLCONF = 'urls'

TIME_ZONE = 'Europe/Rome'
LANGUAGE_CODE = 'en-gb'
USE_TZ = True
USE_I18N = False
USE_L10N = False
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
MEDIA_ROOT = '%s/media/' % SITE_ROOT
MEDIA_URL = '/media/'
STATIC_ROOT = '%s/static/' % SITE_ROOT
STATIC_URL = '/static/'
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()


urlpatterns = patterns('',    
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    
    url(r'', include('django_restframework_gis_tests.urls')),
    
    url(r'^static/(?P<path>.*)$', 'django.contrib.staticfiles.views.serve'),
)

########NEW FILE########
