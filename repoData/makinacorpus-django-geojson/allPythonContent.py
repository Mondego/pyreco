__FILENAME__ = fields
from django.forms.widgets import HiddenInput
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import (ValidationError,
                                    ImproperlyConfigured)
try:
    from leaflet.forms.widgets import LeafletWidget
    HAS_LEAFLET = True
except:
    import warnings
    warnings.warn('`django-leaflet` is not available.')
    HAS_LEAFLET = False
try:
    from jsonfield.fields import JSONField, JSONFormField
except ImportError:
    class Missing(object):
        def __init__(self, *args, **kwargs):
            err_msg = '`jsonfield` dependency missing. See README.'
            raise ImproperlyConfigured(err_msg)

    JSONField = Missing
    JSONFormField = Missing


class GeoJSONValidator(object):
    def __init__(self, geom_type):
        self.geom_type = geom_type

    def __call__(self, value):
        err_msg = None
        geom_type = value.get('type') or ''
        if self.geom_type == 'GEOMETRY':
            is_geometry = geom_type in (
                "Point", "MultiPoint", "LineString", "MultiLineString",
                "Polygon", "MultiPolygon", "GeometryCollection"
            )
            if not is_geometry:
                err_msg = u'%s is not a valid GeoJSON geometry type' % geom_type
        else:
            if self.geom_type.lower() != geom_type.lower():
                err_msg = u'%s does not match geometry type' % geom_type

        if err_msg:
            raise ValidationError(err_msg)


class GeoJSONFormField(JSONFormField):
    widget = LeafletWidget if HAS_LEAFLET else HiddenInput

    def __init__(self, *args, **kwargs):
        geom_type = kwargs.pop('geom_type')
        kwargs.setdefault('validators', [GeoJSONValidator(geom_type)])
        super(GeoJSONFormField, self).__init__(*args, **kwargs)


class GeoJSONField(JSONField):
    description = _("Geometry as GeoJSON")
    form_class = GeoJSONFormField
    dim = 2
    geom_type = 'GEOMETRY'

    def formfield(self, **kwargs):
        kwargs.setdefault('geom_type', self.geom_type)
        return super(GeoJSONField, self).formfield(**kwargs)


class GeometryField(GeoJSONField):
    pass


class GeometryCollectionField(GeometryField):
    geom_type = 'GEOMETRYCOLLECTION'


class PointField(GeometryField):
    geom_type = 'POINT'


class MultiPointField(GeometryField):
    geom_type = 'MULTIPOINT'


class LineStringField(GeometryField):
    geom_type = 'LINESTRING'


class MultiLineStringField(GeometryField):
    geom_type = 'MULTILINESTRING'


class PolygonField(GeometryField):
    geom_type = 'POLYGON'


class MultiPolygonField(GeoJSONField):
    geom_type = 'MULTIPOLYGON'


try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^djgeojson\.fields\.(GeoJSONField|GeometryField|GeometryCollectionField|PointField|MultiPointField|LineStringField|MultiLineStringField|PolygonField|MultiPolygonField)"])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = http
from django.http import HttpResponse


class HttpJSONResponse(HttpResponse):
    def __init__(self, **kwargs):
        kwargs['content_type'] = 'application/json'
        super(HttpJSONResponse, self).__init__(**kwargs)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = serializers
"""

    This code mainly comes from @glenrobertson's django-geoson-tiles at:
    https://github.com/glenrobertson/django-geojson-tiles/

    Itself, adapted from @jeffkistler's geojson serializer at: https://gist.github.com/967274
"""
try:
    from cStringIO import StringIO
except ImportError:
    from six import StringIO  # NOQA
import json
import logging

from six import string_types, iteritems

from django.db.models.base import Model
from django.db.models.query import QuerySet, ValuesQuerySet
from django.forms.models import model_to_dict
from django.core.serializers.python import (_get_model,
                                            Serializer as PythonSerializer,
                                            Deserializer as PythonDeserializer)
from django.core.serializers.json import DjangoJSONEncoder
from django.core.serializers.base import SerializationError, DeserializationError
from django.utils.encoding import smart_text
from django.contrib.gis.geos import WKBWriter
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.db.models.fields import GeometryField

from . import GEOJSON_DEFAULT_SRID
from .fields import GeoJSONField


logger = logging.getLogger(__name__)


def hasattr_lazy(obj, name):
    if isinstance(obj, dict):
        return name in obj
    return name in dir(obj)


class DjangoGeoJSONEncoder(DjangoJSONEncoder):

    def default(self, o):
        if isinstance(o, GEOSGeometry):
            return json.loads(o.geojson)
        else:
            return super(DjangoGeoJSONEncoder, self).default(o)


class Serializer(PythonSerializer):
    def start_serialization(self):
        self.feature_collection = {"type": "FeatureCollection", "features": []}
        if self.crs is not False:
            self.feature_collection["crs"] = self.get_crs()

        bbox = self.options.pop('bbox', None)
        if bbox:
            self.feature_collection["bbox"] = bbox

        self._current = None

    def get_crs(self):
        crs = {}
        crs["type"] = "link"
        properties = {}
        properties["href"] = "http://spatialreference.org/ref/epsg/%s/" % (str(self.srid))
        properties["type"] = "proj4"
        crs["properties"] = properties
        return crs

    def start_object(self, obj):
        self._current = {"type": "Feature", "properties": {}}

        # Try to determine the primary key from the obj
        # self.primary_key can be a function (callable on obj), or a string
        # if self.primary_key is not set, use obj.pk if obj is a Model
        # otherwise the primary key will not be used
        primary_key = None
        if self.primary_key and hasattr(self.primary_key, '__call__'):
            primary_key = self.primary_key(obj)
        elif self.primary_key and isinstance(self.primary_key, string_types):
            if isinstance(obj, Model):
                primary_key = getattr(obj, self.primary_key)
            else:
                primary_key = obj[self.primary_key]
        elif isinstance(obj, Model):
            primary_key = obj.pk

        if primary_key:
            self._current['id'] = primary_key

    def end_object(self, obj):
        # Add extra properties from dynamic attributes
        extras = []
        if isinstance(self.properties, dict):
            extras = [field for field, name in self.properties.items()
                      if name not in self._current['properties']]
        elif isinstance(self.properties, list):
            extras = [field for field in self.properties
                      if field not in self._current['properties']]

        for field in extras:
            if hasattr_lazy(obj, field):
                self.handle_field(obj, field)

        # Add extra-info for deserializing
        if hasattr(obj, '_meta'):
            self._current['properties']['model'] = smart_text(obj._meta)

        # If geometry not in model fields, may be a dynamic attribute
        if 'geometry' not in self._current:
            if hasattr_lazy(obj, self.geometry_field):
                geometry = getattr(obj, self.geometry_field)
                self._handle_geom(geometry)
            else:
                logger.warn("No GeometryField found in object")

        self.feature_collection["features"].append(self._current)
        self._current = None

    def end_serialization(self):
        self.options.pop('stream', None)
        self.options.pop('properties', None)
        self.options.pop('primary_key', None)
        self.options.pop('geometry_field', None)
        self.options.pop('use_natural_keys', None)
        self.options.pop('crs', None)
        self.options.pop('srid', None)
        self.options.pop('force2d', None)
        self.options.pop('simplify', None)
        self.options.pop('bbox', None)
        self.options.pop('bbox_auto', None)

        # Optional float precision control
        precision = self.options.pop('precision', None)
        floatrepr = json.encoder.FLOAT_REPR
        if precision is not None:
            # Monkey patch for float precision!
            json.encoder.FLOAT_REPR = lambda o: format(o, '.%sf' % precision)

        json.dump(self.feature_collection, self.stream, cls=DjangoGeoJSONEncoder, **self.options)

        json.encoder.FLOAT_REPR = floatrepr  # Restore

    def _handle_geom(self, value):
        """ Geometry processing (in place), depending on options """
        if value is None:
            geometry = None
        elif isinstance(value, dict) and 'type' in value:
            geometry = value
        else:
            if isinstance(value, GEOSGeometry):
                geometry = value
            else:
                try:
                    # this will handle string representations (e.g. ewkt, bwkt)
                    geometry = GEOSGeometry(value)
                except ValueError:
                    # if the geometry couldn't be parsed.
                    # we can't generate valid geojson
                    error_msg = 'The field ["%s", "%s"] could not be parsed as a valid geometry' % (
                        self.geometry_field, value
                    )
                    raise SerializationError(error_msg)

            # Optional force 2D
            if self.options.get('force2d'):
                wkb_w = WKBWriter()
                wkb_w.outdim = 2
                geometry = GEOSGeometry(wkb_w.write(geometry), srid=geometry.srid)
            # Optional geometry simplification
            simplify = self.options.get('simplify')
            if simplify is not None:
                geometry = geometry.simplify(tolerance=simplify, preserve_topology=True)
            # Optional geometry reprojection
            if geometry.srid and geometry.srid != self.srid:
                geometry.transform(self.srid)
            # Optional bbox
            if self.options.get('bbox_auto'):
                self._current['bbox'] = geometry.extent

        self._current['geometry'] = geometry

    def handle_field(self, obj, field_name):
        if isinstance(obj, Model):
            value = getattr(obj, field_name)
        elif isinstance(obj, dict):
            value = obj[field_name]
        else:
            # Only supports dicts and models, not lists (e.g. values_list)
            return

        if field_name == self.geometry_field:
            self._handle_geom(value)

        elif self.properties and field_name in self.properties:
            # set the field name to the key's value mapping in self.properties
            if isinstance(self.properties, dict):
                property_name = self.properties[field_name]
                self._current['properties'][property_name] = value
            else:
                self._current['properties'][field_name] = value

        elif not self.properties:
            self._current['properties'][field_name] = value

    def getvalue(self):
        if callable(getattr(self.stream, 'getvalue', None)):
            return self.stream.getvalue()

    def handle_fk_field(self, obj, field):
        related = getattr(obj, field.name)
        if related is not None:
            if self.use_natural_keys and hasattr(related, 'natural_key'):
                related = related.natural_key()
            else:
                if field.rel.field_name == related._meta.pk.name:
                    # Related to remote object via primary key
                    related = related._get_pk_val()
                else:
                    # Related to remote object via other field
                    related = smart_text(getattr(related, field.rel.field_name), strings_only=True)
        self._current['properties'][field.name] = related

    def handle_m2m_field(self, obj, field):
        if field.rel.through._meta.auto_created:
            if self.use_natural_keys and hasattr(field.rel.to, 'natural_key'):
                m2m_value = lambda value: value.natural_key()
            else:
                m2m_value = lambda value: smart_text(value._get_pk_val(), strings_only=True)
            self._current['properties'][field.name] = [m2m_value(related)
                                                       for related in getattr(obj, field.name).iterator()]

    def handle_reverse_field(self, obj, field, field_name):
        if self.use_natural_keys and hasattr(field.model, 'natural_key'):
            reverse_value = lambda value: value.natural_key()
        else:
            reverse_value = lambda value: smart_text(value._get_pk_val(), strings_only=True)
        values = [reverse_value(related) for related in getattr(obj, field_name).iterator()]
        self._current['properties'][field_name] = values

    def serialize_object_list(self, objects):
        if len(objects) == 0:
            return

        # Transform to list of dicts instead of objects
        if not isinstance(objects[0], dict):
            values = []
            for obj in objects:
                objdict = model_to_dict(obj)
                # In case geometry is not a DB field
                if self.geometry_field not in objdict:
                    objdict[self.geometry_field] = getattr(obj, self.geometry_field)
                values.append(objdict)
            objects = values

        self.serialize_values_queryset(objects)

    def serialize_values_queryset(self, queryset):
        for obj in queryset:
            self.start_object(obj)

            # handle the geometry field
            self.handle_field(obj, self.geometry_field)

            for field_name in obj:
                if field_name not in obj:
                    continue
                if self.properties is None or field_name in self.properties:
                    self.handle_field(obj, field_name)

            self.end_object(obj)

    def serialize_queryset(self, queryset):
        opts = queryset.model._meta
        local_fields = opts.local_fields
        many_to_many_fields = opts.many_to_many
        reversed_fields = [obj.field for obj in opts.get_all_related_objects()]
        reversed_fields += [obj.field for obj in opts.get_all_related_many_to_many_objects()]

        # populate each queryset obj as a feature
        for obj in queryset:
            self.start_object(obj)

            # handle the geometry field
            self.handle_field(obj, self.geometry_field)

            # handle the property fields
            for field in local_fields:
                # don't include the pk in the properties
                # as it is in the id of the feature
                # except if explicitly listed in properties
                if field.name == opts.pk.name and \
                        (self.properties is None or 'id' not in self.properties):
                    continue
                # ignore other geometries
                if isinstance(field, GeometryField):
                    continue

                if field.serialize or field.primary_key:
                    if field.rel is None:
                        if self.properties is None or field.attname in self.properties:
                            self.handle_field(obj, field.name)
                    else:
                        if self.properties is None or field.attname[:-3] in self.properties:
                            self.handle_fk_field(obj, field)

            for field in many_to_many_fields:
                if field.serialize:
                    if self.properties is None or field.attname in self.properties:
                        self.handle_m2m_field(obj, field)

            for field in reversed_fields:
                if field.serialize:
                    field_name = field.rel.related_name or opts.object_name.lower()
                    if self.properties is None or field_name in self.properties:
                        self.handle_reverse_field(obj, field, field_name)
            self.end_object(obj)

    def serialize(self, queryset, **options):
        """
        Serialize a queryset.
        """
        self.options = options

        self.stream = options.get("stream", StringIO())
        self.primary_key = options.get("primary_key", None)
        self.properties = options.get("properties")
        self.geometry_field = options.get("geometry_field", "geom")
        self.use_natural_keys = options.get("use_natural_keys", False)
        self.bbox = options.get("bbox", None)
        self.bbox_auto = options.get("bbox_auto", None)
        self.srid = options.get("srid", GEOJSON_DEFAULT_SRID)
        self.crs = options.get("crs", True)

        self.start_serialization()

        if isinstance(queryset, ValuesQuerySet):
            self.serialize_values_queryset(queryset)

        elif isinstance(queryset, list):
            self.serialize_object_list(queryset)

        elif isinstance(queryset, QuerySet):
            self.serialize_queryset(queryset)

        self.end_serialization()
        return self.getvalue()


def Deserializer(stream_or_string, **options):
    """
    Deserialize a stream or string of JSON data.
    """

    geometry_field = options.get("geometry_field", "geom")

    def FeatureToPython(dictobj):
        properties = dictobj['properties']
        model_name = options.get("model_name") or properties.pop('model')
        # Deserialize concrete fields only (bypass dynamic properties)
        model = _get_model(model_name)
        field_names = [f.name for f in model._meta.fields]
        fields = {}
        for k, v in iteritems(properties):
            if k in field_names:
                fields[k] = v
        obj = {
            "model": model_name,
            "pk": dictobj.get('id') or properties.get('id'),
            "fields": fields
        }
        if isinstance(model._meta.get_field(geometry_field), GeoJSONField):
            obj['fields'][geometry_field] = dictobj['geometry']
        else:
            shape = GEOSGeometry(json.dumps(dictobj['geometry']))
            obj['fields'][geometry_field] = shape.wkt
        return obj

    if isinstance(stream_or_string, string_types):
        stream = StringIO(stream_or_string)
    else:
        stream = stream_or_string
    try:
        collection = json.load(stream)
        objects = [FeatureToPython(f) for f in collection['features']]
        for obj in PythonDeserializer(objects, **options):
            yield obj
    except GeneratorExit:
        raise
    except Exception as e:
        # Map to deserializer error
        raise DeserializationError(repr(e))

########NEW FILE########
__FILENAME__ = geojson_tags
import json
import re

from six import string_types

from django import template
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db.models.fields import GeometryField

from .. import GEOJSON_DEFAULT_SRID
from ..serializers import Serializer, DjangoGeoJSONEncoder


register = template.Library()


@register.filter
def geojsonfeature(source, params=''):
    """
    :params: A string with the following optional tokens:
             "properties:field:srid"
    """
    parse = re.search(r'(?P<properties>((\w+)(,\w+)*)?)(:(?P<field>(\w+)?))?(:(?P<srid>(\d+)?))?', params)
    if parse:
        parse = parse.groupdict()
    else:
        parse = {}

    geometry_field = parse.get('field') or 'geom'
    properties = parse.get('properties', '').split(',')
    srid = parse.get('srid') or GEOJSON_DEFAULT_SRID

    if source is None or isinstance(source, string_types):
        return 'null'

    if isinstance(source, (GEOSGeometry, GeometryField)):
        encoder = DjangoGeoJSONEncoder()
        if source.srid != srid:
            source.transform(srid)
        feature = {"type": "Feature", "properties": {}}
        feature['geometry'] = encoder.default(source)
        return json.dumps(feature)

    serializer = Serializer()

    if not hasattr(source, '__iter__'):
        source = [source]

    return serializer.serialize(source, properties=properties,
                                geometry_field=geometry_field, srid=srid)

########NEW FILE########
__FILENAME__ = tests
import json

from django.test import TestCase
from django.conf import settings
from django.core import serializers
from django.core.exceptions import ValidationError
from django.contrib.gis.db import models
from django.contrib.gis.geos import LineString, Point, GeometryCollection
from django.utils.encoding import smart_text

from .templatetags.geojson_tags import geojsonfeature
from .serializers import Serializer
from .views import GeoJSONLayerView, TiledGeoJSONLayerView
from .fields import GeoJSONField, GeoJSONFormField, GeoJSONValidator


settings.SERIALIZATION_MODULES = {'geojson': 'djgeojson.serializers'}


class PictureMixin(object):

    @property
    def picture(self):
        return 'image.png'


class Route(PictureMixin, models.Model):
    name = models.CharField(max_length=20)
    geom = models.LineStringField(spatial_index=False, srid=4326)
    countries = models.ManyToManyField('Country')

    def natural_key(self):
        return self.name

    @property
    def upper_name(self):
        return self.name.upper()

    objects = models.GeoManager()


class Sign(models.Model):
    label = models.CharField(max_length=20)
    route = models.ForeignKey(Route, related_name='signs')

    def natural_key(self):
        return self.label

    @property
    def geom(self):
        return self.route.geom.centroid


class Country(models.Model):
    label = models.CharField(max_length=20)
    geom = models.PolygonField(spatial_index=False, srid=4326)
    objects = models.GeoManager()

    def natural_key(self):
        return self.label


class GeoJsonDeSerializerTest(TestCase):

    def test_basic(self):
        input_geojson = """
        {"type": "FeatureCollection",
         "features": [
            { "type": "Feature",
                "properties": {"model": "djgeojson.route", "name": "green", "upper_name": "RED"},
                "id": 1,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [0.0, 0.0],
                        [1.0, 1.0]
                    ]
                }
            },
            { "type": "Feature",
                "properties": {"model": "djgeojson.route", "name": "blue"},
                "id": 2,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [0.0, 0.0],
                        [1.0, 1.0]
                    ]
                }
            }
        ]}"""

        # Deserialize into a list of objects
        objects = list(serializers.deserialize('geojson', input_geojson))

        # Were three objects deserialized?
        self.assertEqual(len(objects), 2)

        # Did the objects deserialize correctly?
        self.assertEqual(objects[1].object.name, "blue")
        self.assertEqual(objects[0].object.upper_name, "GREEN")
        self.assertEqual(objects[0].object.geom,
                         LineString((0.0, 0.0), (1.0, 1.0)))

    def test_with_model_name_passed_as_argument(self):
        input_geojson = """
        {"type": "FeatureCollection",
         "features": [
            { "type": "Feature",
                "properties": {"name": "bleh"},
                "id": 24,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [1, 2],
                        [42, 3]
                    ]
                }
            }
        ]}"""

        my_object = list(serializers.deserialize(
            'geojson', input_geojson, model_name='djgeojson.route'))[0].object

        self.assertEqual(my_object.name, "bleh")


class GeoJsonSerializerTest(TestCase):

    def test_basic(self):
        # Stuff to serialize
        route1 = Route.objects.create(
            name='green', geom="LINESTRING (0 0, 1 1)")
        route2 = Route.objects.create(
            name='blue', geom="LINESTRING (0 0, 1 1)")
        route3 = Route.objects.create(name='red', geom="LINESTRING (0 0, 1 1)")

        actual_geojson = json.loads(serializers.serialize(
            'geojson', Route.objects.all(), properties=['name']))
        self.assertEqual(
            actual_geojson, {"crs": {"type": "link", "properties": {"href": "http://spatialreference.org/ref/epsg/4326/", "type": "proj4"}}, "type": "FeatureCollection", "features": [{"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"model": "djgeojson.route", "name": "green"}, "id": route1.pk}, {"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"model": "djgeojson.route", "name": "blue"}, "id": route2.pk}, {"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"model": "djgeojson.route", "name": "red"}, "id": route3.pk}]})
        actual_geojson_with_prop = json.loads(
            serializers.serialize(
                'geojson', Route.objects.all(),
                properties=['name', 'upper_name', 'picture']))
        self.assertEqual(actual_geojson_with_prop,
                         {"crs": {"type": "link", "properties": {"href": "http://spatialreference.org/ref/epsg/4326/", "type": "proj4"}}, "type": "FeatureCollection", "features": [{"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"picture": "image.png", "model": "djgeojson.route", "upper_name": "GREEN", "name": "green"}, "id": route1.pk}, {"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"picture": "image.png", "model": "djgeojson.route", "upper_name": "BLUE", "name": "blue"}, "id": route2.pk}, {"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"picture": "image.png", "model": "djgeojson.route", "upper_name": "RED", "name": "red"}, "id": route3.pk}]})

    def test_precision(self):
        serializer = Serializer()
        features = json.loads(serializer.serialize(
            [{'geom': 'SRID=2154;POINT (1 1)'}], precision=2, crs=False))
        self.assertEqual(
            features, {"type": "FeatureCollection", "features": [{"geometry": {"type": "Point", "coordinates": [-1.36, -5.98]}, "type": "Feature", "properties": {}}]})

    def test_simplify(self):
        serializer = Serializer()
        features = json.loads(serializer.serialize(
            [{'geom': 'SRID=4326;LINESTRING (1 1, 1.5 1, 2 3, 3 3)'}], simplify=0.5, crs=False))
        self.assertEqual(
            features, {"type": "FeatureCollection", "features": [{"geometry": {"type": "LineString", "coordinates": [[1.0, 1.0], [2.0, 3.0], [3.0, 3.0]]}, "type": "Feature", "properties": {}}]})

    def test_force2d(self):
        serializer = Serializer()
        features2d = json.loads(serializer.serialize(
            [{'geom': 'SRID=4326;POINT Z (1 2 3)'}],
            force2d=True, crs=False))
        self.assertEqual(
            features2d, {"type": "FeatureCollection", "features": [{"geometry": {"type": "Point", "coordinates": [1.0, 2.0]}, "type": "Feature", "properties": {}}]})

    def test_pk_property(self):
        route = Route.objects.create(name='red', geom="LINESTRING (0 0, 1 1)")
        serializer = Serializer()
        features2d = json.loads(serializer.serialize(
            Route.objects.all(), properties=['id'], crs=False))
        self.assertEqual(
            features2d, {"type": "FeatureCollection", "features": [{"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"model": "djgeojson.route", "id": route.pk}, "id": route.pk}]})

    def test_geometry_property(self):
        class Basket(models.Model):

            @property
            def geom(self):
                return GeometryCollection(LineString((3, 4, 5), (6, 7, 8)), Point(1, 2, 3), srid=4326)

        serializer = Serializer()
        features = json.loads(
            serializer.serialize([Basket()], crs=False, force2d=True))
        expected_content = {"type": "FeatureCollection", "features": [{"geometry": {"type": "GeometryCollection", "geometries": [{"type": "LineString", "coordinates": [[3.0, 4.0], [6.0, 7.0]]}, {"type": "Point", "coordinates": [1.0, 2.0]}]}, "type": "Feature", "properties": {"id": None}}]}
        self.assertEqual(features, expected_content)

    def test_none_geometry(self):
        class Empty(models.Model):
            geom = None
        serializer = Serializer()
        features = json.loads(serializer.serialize([Empty()], crs=False))
        self.assertEqual(
            features, {
                "type": "FeatureCollection",
                "features": [{
                    "geometry": None,
                    "type": "Feature",
                    "properties": {"id": None}}]
            })

    def test_bbox_auto(self):
        serializer = Serializer()
        features = json.loads(serializer.serialize([{'geom': 'SRID=4326;LINESTRING (1 1, 3 3)'}],
                                                   bbox_auto=True, crs=False))
        self.assertEqual(
            features, {
                "type": "FeatureCollection",
                "features": [{
                    "geometry": {"type": "LineString", "coordinates": [[1.0, 1.0], [3.0, 3.0]]},
                    "type": "Feature",
                    "properties": {},
                    "bbox": [1.0, 1.0, 3.0, 3.0]
                }]
            })


class ForeignKeyTest(TestCase):

    def setUp(self):
        self.route = Route.objects.create(
            name='green', geom="LINESTRING (0 0, 1 1)")
        Sign(label='A', route=self.route).save()

    def test_serialize_foreign(self):
        serializer = Serializer()
        features = json.loads(serializer.serialize(Sign.objects.all(), properties=['route']))
        self.assertEqual(
            features, {"crs": {"type": "link", "properties": {"href": "http://spatialreference.org/ref/epsg/4326/", "type": "proj4"}}, "type": "FeatureCollection", "features": [{"geometry": {"type": "Point", "coordinates": [0.5, 0.5]}, "type": "Feature", "properties": {"route": 1, "model": "djgeojson.sign"}, "id": self.route.pk}]})

    def test_serialize_foreign_natural(self):
        serializer = Serializer()
        features = json.loads(serializer.serialize(
            Sign.objects.all(), use_natural_keys=True, properties=['route']))
        self.assertEqual(
            features, {"crs": {"type": "link", "properties": {"href": "http://spatialreference.org/ref/epsg/4326/", "type": "proj4"}}, "type": "FeatureCollection", "features": [{"geometry": {"type": "Point", "coordinates": [0.5, 0.5]}, "type": "Feature", "properties": {"route": "green", "model": "djgeojson.sign"}, "id": self.route.pk}]})


class ManyToManyTest(TestCase):

    def setUp(self):
        country1 = Country(label='C1', geom="POLYGON ((0 0,1 1,0 2,0 0))")
        country1.save()
        country2 = Country(label='C2', geom="POLYGON ((0 0,1 1,0 2,0 0))")
        country2.save()

        self.route1 = Route.objects.create(
            name='green', geom="LINESTRING (0 0, 1 1)")
        self.route2 = Route.objects.create(
            name='blue', geom="LINESTRING (0 0, 1 1)")
        self.route2.countries.add(country1)
        self.route3 = Route.objects.create(
            name='red', geom="LINESTRING (0 0, 1 1)")
        self.route3.countries.add(country1)
        self.route3.countries.add(country2)

    def test_serialize_manytomany(self):
        serializer = Serializer()
        features = json.loads(serializer.serialize(
            Route.objects.all(), properties=['countries']))
        self.assertEqual(
            features, {"crs": {"type": "link", "properties": {"href": "http://spatialreference.org/ref/epsg/4326/", "type": "proj4"}}, "type": "FeatureCollection", "features": [{"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"model": "djgeojson.route", "countries": []}, "id": self.route1.pk}, {"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"model": "djgeojson.route", "countries": [1]}, "id": self.route2.pk}, {"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"model": "djgeojson.route", "countries": [1, 2]}, "id": self.route3.pk}]})

    def test_serialize_manytomany_natural(self):
        serializer = Serializer()
        features = json.loads(serializer.serialize(
            Route.objects.all(), use_natural_keys=True, properties=['countries']))
        self.assertEqual(
            features, {"crs": {"type": "link", "properties": {"href": "http://spatialreference.org/ref/epsg/4326/", "type": "proj4"}}, "type": "FeatureCollection", "features": [{"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"model": "djgeojson.route", "countries": []}, "id": self.route1.pk}, {"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"model": "djgeojson.route", "countries": ["C1"]}, "id": self.route2.pk}, {"geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}, "type": "Feature", "properties": {"model": "djgeojson.route", "countries": ["C1", "C2"]}, "id": self.route3.pk}]})


class ReverseForeignkeyTest(TestCase):

    def setUp(self):
        self.route = Route(name='green', geom="LINESTRING (0 0, 1 1)")
        self.route.save()
        self.sign1 = Sign.objects.create(label='A', route=self.route)
        self.sign2 = Sign.objects.create(label='B', route=self.route)
        self.sign3 = Sign.objects.create(label='C', route=self.route)

    def test_relation_set(self):
        self.assertEqual(len(self.route.signs.all()), 3)

    def test_serialize_reverse(self):
        serializer = Serializer()
        features = json.loads(serializer.serialize(
            Route.objects.all(), properties=['signs']))
        self.assertEqual(
            features, {
                "crs": {
                    "type": "link", "properties": {
                        "href": "http://spatialreference.org/ref/epsg/4326/",
                        "type": "proj4"
                    }
                },
                "type": "FeatureCollection",
                "features": [{
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[0.0, 0.0], [1.0, 1.0]]
                    },
                    "type": "Feature",
                    "properties": {
                        "model": "djgeojson.route",
                        "signs": [
                            self.sign1.pk,
                            self.sign2.pk,
                            self.sign3.pk]},
                    "id": self.route.pk
                }]
            })

    def test_serialize_reverse_natural(self):
        serializer = Serializer()
        features = json.loads(serializer.serialize(
            Route.objects.all(), use_natural_keys=True, properties=['signs']))
        self.assertEqual(
            features, {
                "crs": {
                    "type": "link",
                    "properties": {
                        "href": "http://spatialreference.org/ref/epsg/4326/",
                        "type": "proj4"
                    }
                },
                "type": "FeatureCollection",
                "features": [{
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                    "type": "Feature",
                    "properties": {
                        "model": "djgeojson.route",
                        "signs": ["A", "B", "C"]},
                    "id": self.route.pk
                }]
            })


class GeoJsonTemplateTagTest(TestCase):

    def setUp(self):
        self.route1 = Route.objects.create(name='green',
                                           geom="LINESTRING (0 0, 1 1)")
        self.route2 = Route.objects.create(name='blue',
                                           geom="LINESTRING (0 0, 1 1)")
        self.route3 = Route.objects.create(name='red',
                                           geom="LINESTRING (0 0, 1 1)")

    def test_templatetag_renders_single_object(self):
        feature = json.loads(geojsonfeature(self.route1))
        self.assertEqual(
            feature, {
                "crs": {
                    "type": "link",
                    "properties": {
                        "href": "http://spatialreference.org/ref/epsg/4326/",
                        "type": "proj4"
                    }
                },
                "type": "FeatureCollection",
                "features": [{
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                    "type": "Feature", "properties": {}}]
            })

    def test_templatetag_renders_queryset(self):
        feature = json.loads(geojsonfeature(Route.objects.all()))
        self.assertEqual(
            feature, {
                "crs": {
                    "type": "link", "properties": {
                        "href": "http://spatialreference.org/ref/epsg/4326/",
                        "type": "proj4"
                    }
                },
                "type": "FeatureCollection",
                "features": [
                    {
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[0.0, 0.0], [1.0, 1.0]]
                        },
                        "type": "Feature",
                        "properties": {
                            "model": "djgeojson.route"
                        },
                        "id": self.route1.pk
                    },
                    {
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[0.0, 0.0], [1.0, 1.0]]
                        },
                        "type": "Feature",
                        "properties": {"model": "djgeojson.route"},
                        "id": self.route2.pk
                    },
                    {
                        "geometry": {"type": "LineString",
                                     "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                        "type": "Feature",
                        "properties": {"model": "djgeojson.route"},
                        "id": self.route3.pk
                    }
                ]
            })

    def test_template_renders_geometry(self):
        feature = json.loads(geojsonfeature(self.route1.geom))
        self.assertEqual(
            feature, {
                "geometry": {"type": "LineString",
                             "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                "type": "Feature", "properties": {}
            })

    def test_property_can_be_specified(self):
        features = json.loads(geojsonfeature(self.route1,
                                             "name"))
        feature = features['features'][0]
        self.assertEqual(feature['properties']['name'],
                         self.route1.name)

    def test_several_properties_can_be_specified(self):
        features = json.loads(geojsonfeature(self.route1,
                                             "name,id"))
        feature = features['features'][0]
        self.assertEqual(feature['properties'],
                         {'name': self.route1.name,
                          'id': self.route1.id})

    def test_srid_can_be_specified(self):
        feature = json.loads(geojsonfeature(self.route1.geom, "::2154"))
        self.assertEqual(feature['geometry']['coordinates'],
                         [[253531.1305237495, 909838.9305578759],
                          [406035.7627716485, 1052023.2925472297]])

    def test_geom_field_name_can_be_specified(self):
        features = json.loads(geojsonfeature(self.route1, ":geom"))
        feature = features['features'][0]
        self.assertEqual(feature['geometry']['coordinates'],
                         [[0.0, 0.0], [1.0, 1.0]])

    def test_geom_field_raises_attributeerror_if_unknown(self):
        self.assertRaises(AttributeError, geojsonfeature, self.route1, ":geo")


class ViewsTest(TestCase):

    def setUp(self):
        self.route = Route(name='green', geom="LINESTRING (0 0, 1 1)")
        self.route.save()

    def test_view_default_options(self):
        view = GeoJSONLayerView(model=Route)
        view.object_list = []
        response = view.render_to_response(context={})
        geojson = json.loads(smart_text(response.content))
        self.assertEqual(geojson['features'][0]['geometry']['coordinates'],
                         [[0.0, 0.0], [1.0, 1.0]])

    def test_view_can_control_properties(self):
        klass = type('FullGeoJSON', (GeoJSONLayerView,),
                     {'properties': ['name']})
        view = klass(model=Route)
        view.object_list = []
        response = view.render_to_response(context={})
        geojson = json.loads(smart_text(response.content))
        self.assertEqual(geojson['features'][0]['properties']['name'],
                         'green')


class TileEnvelopTest(TestCase):
    def setUp(self):
        self.view = TiledGeoJSONLayerView()

    def test_raises_error_if_not_spherical_mercator(self):
        self.view.tile_srid = 2154
        self.assertRaises(AssertionError, self.view.tile_coord, 0, 0, 0)

    def test_origin_is_north_west_for_tile_0(self):
        self.assertEqual((-180.0, 85.0511287798066),
                         self.view.tile_coord(0, 0, 0))

    def test_origin_is_center_for_middle_tile(self):
        self.assertEqual((0, 0), self.view.tile_coord(8, 8, 4))


class TiledGeoJSONViewTest(TestCase):
    def setUp(self):
        self.view = TiledGeoJSONLayerView(model=Route)
        self.r1 = Route.objects.create(geom=LineString((0, 1), (10, 1)))
        self.r2 = Route.objects.create(geom=LineString((0, -1), (-10, -1)))

    def test_view_is_serialized_as_geojson(self):
        self.view.args = [4, 8, 7]
        response = self.view.render_to_response(context={})
        geojson = json.loads(smart_text(response.content))
        self.assertEqual(geojson['features'][0]['geometry']['coordinates'],
                         [[0.0, 1.0], [10.0, 1.0]])

    def test_view_trims_to_geometries_boundaries(self):
        self.view.args = [8, 128, 127]
        response = self.view.render_to_response(context={})
        geojson = json.loads(smart_text(response.content))
        self.assertEqual(geojson['features'][0]['geometry']['coordinates'],
                         [[0.0, 1.0], [1.40625, 1.0]])

    def test_geometries_trim_can_be_disabled(self):
        self.view.args = [8, 128, 127]
        self.view.trim_to_boundary = False
        response = self.view.render_to_response(context={})
        geojson = json.loads(smart_text(response.content))
        self.assertEqual(geojson['features'][0]['geometry']['coordinates'],
                         [[0.0, 1.0], [10.0, 1.0]])

    def test_tile_extent_is_provided_in_collection(self):
        self.view.args = [8, 128, 127]
        response = self.view.render_to_response(context={})
        geojson = json.loads(smart_text(response.content))
        self.assertEqual(geojson['bbox'],
                         [0.0, 0.0, 1.40625, 1.4061088354351565])

    def test_url_parameters_are_converted_to_int(self):
        self.view.args = ['0', '0', '0']
        self.assertEqual(2, len(self.view.get_queryset()))

    def test_zoom_0_queryset_contains_all(self):
        self.view.args = [0, 0, 0]
        self.assertEqual(2, len(self.view.get_queryset()))

    def test_zoom_4_filters_by_tile_extent(self):
        self.view.args = [4, 8, 7]
        self.assertEqual([self.r1], list(self.view.get_queryset()))

    def test_some_tiles_have_empty_queryset(self):
        self.view.args = [4, 6, 8]
        self.assertEqual(0, len(self.view.get_queryset()))

    def test_simplification_depends_on_zoom_level(self):
        self.view.simplifications = {6: 100}
        self.view.args = [6, 8, 4]
        self.view.get_queryset()
        self.assertEqual(self.view.simplify, 100)

    def test_simplification_is_default_if_not_specified(self):
        self.view.simplifications = {}
        self.view.args = [0, 8, 4]
        self.view.get_queryset()
        self.assertEqual(self.view.simplify, None)

    def test_simplification_takes_the_closest_upper_level(self):
        self.view.simplifications = {3: 100, 6: 200}
        self.view.args = [4, 8, 4]
        self.view.get_queryset()
        self.assertEqual(self.view.simplify, 200)


class Address(models.Model):
    geom = GeoJSONField()


class ModelFieldTest(TestCase):
    def setUp(self):
        self.address = Address()
        self.address.geom = {'type': 'Point', 'coordinates': [0, 0]}
        self.address.save()

    def test_models_can_have_geojson_fields(self):
        saved = Address.objects.get(id=self.address.id)
        self.assertDictEqual(saved.geom, self.address.geom)

    def test_default_form_field_is_geojsonfield(self):
        field = self.address._meta.get_field('geom').formfield()
        self.assertTrue(isinstance(field, GeoJSONFormField))

    def test_default_form_field_has_geojson_validator(self):
        field = self.address._meta.get_field('geom').formfield()
        validator = field.validators[0]
        self.assertTrue(isinstance(validator, GeoJSONValidator))

    def test_form_field_raises_if_invalid_type(self):
        field = self.address._meta.get_field('geom').formfield()
        self.assertRaises(ValidationError, field.clean,
                          {'type': 'FeatureCollection', 'foo': 'bar'})

    def test_form_field_raises_if_type_missing(self):
        field = self.address._meta.get_field('geom').formfield()
        self.assertRaises(ValidationError, field.clean,
                          {'foo': 'bar'})

    def test_field_can_be_serialized(self):
        serializer = Serializer()
        geojson = serializer.serialize(Address.objects.all(), crs=False)
        features = json.loads(geojson)
        self.assertEqual(
            features, {
                u'type': u'FeatureCollection',
                u'features': [{
                    u'id': self.address.id,
                    u'type': u'Feature',
                    u'geometry': {u'type': u'Point', u'coordinates': [0, 0]},
                    u'properties': {
                        u'model': u'djgeojson.address'
                    }
                }]
            })

    def test_field_can_be_deserialized(self):
        input_geojson = """
        {"type": "FeatureCollection",
         "features": [
            { "type": "Feature",
                "properties": {"model": "djgeojson.address"},
                "id": 1,
                "geometry": {
                    "type": "Point",
                    "coordinates": [0.0, 0.0]
                }
            }
        ]}"""
        objects = list(serializers.deserialize('geojson', input_geojson))
        self.assertEqual(objects[0].object.geom,
                         {'type': 'Point', 'coordinates': [0, 0]})


class GeoJSONValidatorTest(TestCase):
    def test_validator_raises_if_missing_type(self):
        validator = GeoJSONValidator('GEOMETRY')
        self.assertRaises(ValidationError, validator, {'foo': 'bar'})

    def test_validator_raises_if_type_is_wrong(self):
        validator = GeoJSONValidator('GEOMETRY')
        self.assertRaises(ValidationError, validator,
                          {'type': 'FeatureCollection',
                           'features': []})

    def test_validator_succeeds_if_type_matches(self):
        validator = GeoJSONValidator('POINT')
        self.assertIsNone(validator({'type': 'Point', 'coords': [0, 0]}))

    def test_validator_succeeds_if_type_is_generic(self):
        validator = GeoJSONValidator('GEOMETRY')
        self.assertIsNone(validator({'type': 'Point', 'coords': [0, 0]}))
        self.assertIsNone(validator({'type': 'LineString', 'coords': [0, 0]}))
        self.assertIsNone(validator({'type': 'Polygon', 'coords': [0, 0]}))

    def test_validator_fails_if_type_does_not_match(self):
        validator = GeoJSONValidator('POINT')
        self.assertRaises(ValidationError, validator,
                          {'type': 'LineString', 'coords': [0, 0]})

########NEW FILE########
__FILENAME__ = views
import math

from django.views.generic import ListView
from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from django.contrib.gis.geos.geometry import Polygon
from django.contrib.gis.db.models import PointField

from .http import HttpJSONResponse
from .serializers import Serializer as GeoJSONSerializer
from . import GEOJSON_DEFAULT_SRID


class GeoJSONResponseMixin(object):
    """
    A mixin that can be used to render a GeoJSON response.
    """
    response_class = HttpJSONResponse
    """ Select fields for properties """
    properties = []
    """ Limit float precision """
    precision = None
    """ Simplify geometries """
    simplify = None
    """ Change projection of geometries """
    srid = GEOJSON_DEFAULT_SRID
    """ Geometry field to serialize """
    geometry_field = 'geom'
    """ Force 2D """
    force2d = False
    """ bbox """
    bbox = None
    """ bbox auto """
    bbox_auto = False

    def render_to_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.
        """
        serializer = GeoJSONSerializer()
        response = self.response_class(**response_kwargs)
        queryset = self.get_queryset()
        options = dict(properties=self.properties,
                       precision=self.precision,
                       simplify=self.simplify,
                       srid=self.srid,
                       geometry_field=self.geometry_field,
                       force2d=self.force2d,
                       bbox=self.bbox,
                       bbox_auto=self.bbox_auto)
        serializer.serialize(queryset, stream=response, ensure_ascii=False,
                             **options)
        return response


class GeoJSONLayerView(GeoJSONResponseMixin, ListView):
    """
    A generic view to serve a model as a layer.
    """
    @method_decorator(gzip_page)
    def dispatch(self, *args, **kwargs):
        return super(GeoJSONLayerView, self).dispatch(*args, **kwargs)


class TiledGeoJSONLayerView(GeoJSONLayerView):
    width = 256
    height = 256
    tile_srid = 3857
    trim_to_boundary = True
    """Simplify geometries by zoom level (dict <int:float>)"""
    simplifications = None

    def tile_coord(self, xtile, ytile, zoom):
        """
        This returns the NW-corner of the square. Use the function
        with xtile+1 and/or ytile+1 to get the other corners.
        With xtile+0.5 & ytile+0.5 it will return the center of the tile.
        http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Tile_numbers_to_lon..2Flat._2
        """
        assert self.tile_srid == 3857, 'Custom tile projection not supported yet'
        n = 2.0 ** zoom
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return (lon_deg, lat_deg)

    def get_queryset(self):
        """
        Inspired by Glen Roberton's django-geojson-tiles view
        """
        self.z, self.x, self.y = map(int, self.args[:3])
        nw = self.tile_coord(self.x, self.y, self.z)
        se = self.tile_coord(self.x + 1, self.y + 1, self.z)
        bbox = Polygon((nw, (se[0], nw[1]),
                       se, (nw[0], se[1]), nw))
        qs = super(TiledGeoJSONLayerView, self).get_queryset()
        qs = qs.filter(**{
            '%s__intersects' % self.geometry_field: bbox
        })
        self.bbox = bbox.extent

        # Simplification dict by zoom level
        simplifications = self.simplifications or {}
        z = self.z
        self.simplify = simplifications.get(z)
        while self.simplify is None and z < 32:
            z += 1
            self.simplify = simplifications.get(z)

        # Won't trim point geometries to a boundary
        model_field = qs.model._meta.get_field(self.geometry_field)
        self.trim_to_boundary = (self.trim_to_boundary and
                                 not isinstance(model_field, PointField))
        if self.trim_to_boundary:
            qs = qs.intersection(bbox)
            self.geometry_field = 'intersection'

        return qs

########NEW FILE########
__FILENAME__ = quicktest
import os
import sys
import argparse
from django.conf import settings


class QuickDjangoTest(object):
    """
    A quick way to run the Django test suite without a fully-configured project.

    Example usage:

        >>> QuickDjangoTest('app1', 'app2')

    Based on a script published by Lukasz Dziedzia at:
    http://stackoverflow.com/questions/3841725/how-to-launch-tests-for-django-reusable-app
    """
    DIRNAME = os.path.dirname(__file__)
    INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.admin',
    )

    def __init__(self, *args, **kwargs):
        self.apps = args
        self.run_tests()

    def run_tests(self):
        """
        Fire up the Django test suite developed for version 1.2
        """
        settings.configure(
            DATABASES={
                'default': {
                    'ENGINE': 'django.contrib.gis.db.backends.spatialite',
                    'NAME': os.path.join(self.DIRNAME, 'database.db'),
                    'USER': '',
                    'PASSWORD': '',
                    'HOST': '',
                    'PORT': '',
                }
            },
            INSTALLED_APPS=self.INSTALLED_APPS + self.apps,
        )
        from django.test.simple import DjangoTestSuiteRunner
        failures = DjangoTestSuiteRunner().run_tests(self.apps, verbosity=1)
        if failures:  # pragma: no cover
            sys.exit(failures)

if __name__ == '__main__':
    """
    What do when the user hits this file from the shell.

    Example usage:

        $ python quicktest.py app1 app2

    """
    parser = argparse.ArgumentParser(
        usage="[args]",
        description="Run Django tests on the provided applications."
    )
    parser.add_argument('apps', nargs='+', type=str)
    args = parser.parse_args()
    QuickDjangoTest(*args.apps)

########NEW FILE########
