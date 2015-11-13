__FILENAME__ = base
import geojson
from geojson.mapping import to_mapping


class GeoJSON(dict):

    def __init__(self, iterable=(), **extra):
        super(GeoJSON, self).__init__(iterable)
        self["type"] = getattr(self, "type", type(self).__name__)
        self.update(extra)

    def __repr__(self):
        return geojson.dumps(self, sort_keys=True)

    __str__ = __repr__

    def __setattr__(self, name, value):
        """
        Permit dictionary items to be set like object attributes
        """
        self[name] = value

    def __getattr__(self, name):
        """
        Permit dictionary items to be retrieved like object attributes
        """
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __delattr__(self, name):
        """
        Permit dictionary items to be deleted like object attributes
        """
        del self[name]

    @property
    def __geo_interface__(self):
        if self.type != "GeoJSON":
            return self

    @classmethod
    def to_instance(cls, ob, default=None, strict=False):
        """Encode a GeoJSON dict into an GeoJSON object.

        Assumes the caller knows that the dict should satisfy a GeoJSON type.
        """
        if ob is None and default is not None:
            instance = default()
        elif isinstance(ob, GeoJSON):
            instance = ob
        else:
            mapping = to_mapping(ob)
            d = dict((str(k), mapping[k]) for k in mapping)
            try:
                type_ = d.pop("type")
                geojson_factory = getattr(geojson.factory, type_)
                if not issubclass(geojson_factory, GeoJSON):
                    raise TypeError("""\
                    Not a valid GeoJSON type:
                    %r (geojson_factory: %r, cls: %r)
                    """ % (type_, geojson_factory, cls))
                instance = geojson_factory(**d)
            except (AttributeError, KeyError) as invalid:
                if not strict:
                    instance = ob
                else:
                    msg = "Cannot coerce %r into a valid GeoJSON structure: %s"
                    msg %= (ob, invalid)
                    raise ValueError(msg)
        return instance

########NEW FILE########
__FILENAME__ = codec
try:
    import simplejson as json
except ImportError:
    import json

import geojson
import geojson.factory
from geojson.mapping import to_mapping


class GeoJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        return geojson.factory.GeoJSON.to_instance(obj)


# Wrap the functions from json, providing encoder, decoders, and
# object creation hooks.
# Here the defaults are set to only permit valid JSON as per RFC 4267

def _enforce_strict_numbers(obj):
    if isinstance(obj, (int, float)):
        raise ValueError("Number %r is not JSON compliant" % obj)


def dump(obj, fp, cls=GeoJSONEncoder, allow_nan=False, **kwargs):
    return json.dump(to_mapping(obj),
                     fp, cls=cls, allow_nan=allow_nan, **kwargs)


def dumps(obj, cls=GeoJSONEncoder, allow_nan=False, **kwargs):
    return json.dumps(to_mapping(obj),
                      cls=cls, allow_nan=allow_nan, **kwargs)


def load(fp,
         cls=json.JSONDecoder,
         parse_constant=_enforce_strict_numbers,
         object_hook=geojson.base.GeoJSON.to_instance,
         **kwargs):
    return json.load(fp,
                     cls=cls, object_hook=object_hook,
                     parse_constant=parse_constant,
                     **kwargs)


def loads(s,
          cls=json.JSONDecoder,
          parse_constant=_enforce_strict_numbers,
          object_hook=geojson.base.GeoJSON.to_instance,
          **kwargs):
    return json.loads(s,
                      cls=cls, object_hook=object_hook,
                      parse_constant=parse_constant,
                      **kwargs)


# Backwards compatibility
PyGFPEncoder = GeoJSONEncoder

########NEW FILE########
__FILENAME__ = coords
"""Coordinate utility functions."""

def coords(obj):
    """Yield all coordinate coordinate tuples from a geometry or feature."""
    if isinstance(obj, (tuple, list)):
        coordinates = obj
    elif 'geometry' in obj:
        coordinates = obj['geometry']['coordinates']
    else:
        coordinates = obj.get('coordinates', obj)
    for e in coordinates:
        if isinstance(e, (float, int)):
            yield tuple(coordinates)
            break
        else:
            for f in coords(e):
                yield f

def map_coords(func, obj):
    """Return coordinates, mapped pair-wise using the provided function."""
    if obj['type'] == 'Point':
        coordinates = tuple(map(func, obj['coordinates']))
    elif obj['type'] in ['LineString', 'MultiPoint']:
        coordinates = [tuple(map(func, c)) for c in obj['coordinates']]
    elif obj['type'] in ['MultiLineString', 'Polygon']:
        coordinates = [[
            tuple(map(func, c)) for c in curve]
                for curve in obj['coordinates']]
    elif obj['type'] == 'MultiPolygon':
        coordinates = [[[
            tuple(map(func, c)) for c in curve]
                for curve in part]
                    for part in obj['coordinates']]
    else:
        raise ValueError("Invalid geometry object %s" % repr(obj))
    return {'type': obj['type'], 'coordinates': coordinates}

########NEW FILE########
__FILENAME__ = crs
from geojson.base import GeoJSON


class CoordinateReferenceSystem(GeoJSON):

    def __init__(self, properties=None, **extra):
        super(CoordinateReferenceSystem, self).__init__(**extra)
        self["properties"] = properties or {}


class Named(CoordinateReferenceSystem):

    def __init__(self, properties=None, **extra):
        super(Named, self).__init__(properties=properties, **extra)
        self["type"] = "name"

    def __repr__(self):
        return super(Named, self).__repr__()


class Linked(CoordinateReferenceSystem):

    def __init__(self, properties=None, **extra):
        super(Linked, self).__init__(properties=properties, **extra)
        self["type"] = "link"


class Default(object):

    """GeoJSON default, long/lat WGS84, is not serialized."""

########NEW FILE########
__FILENAME__ = examples

class SimpleWebFeature(object):

    """
    A simple, Atom-ish, single geometry (WGS84) GIS feature.
    """

    def __init__(self, id=None, geometry=None, title=None, summary=None,
                 link=None):
        """Initialize."""
        self.id = id
        self.geometry = geometry
        self.properties = {}
        self.properties['title'] = title
        self.properties['summary'] = summary
        self.properties['link'] = link

    def as_dict(self):
        return {
            "type": "Feature",
            "id": self.id,
            "properties": self.properties,
            "geometry": self.geometry
            }

    __geo_interface__ = property(as_dict)


def createSimpleWebFeature(o):
    """Create an instance of SimpleWebFeature from a dict, o. If o does not
    match a Python feature object, simply return o. This function serves as a
    json decoder hook. See coding.load()."""
    try:
        id = o['id']
        g = o['geometry']
        p = o['properties']
        return SimpleWebFeature(str(id), {
            'type': str(g.get('type')),
            'coordinates': g.get('coordinates', [])},
            title=p.get('title'),
            summary=p.get('summary'),
            link=str(p.get('link')))
    except (KeyError, TypeError):
        pass
    return o

########NEW FILE########
__FILENAME__ = factory
from geojson.geometry import Point, LineString, Polygon
from geojson.geometry import MultiLineString, MultiPoint, MultiPolygon
from geojson.geometry import GeometryCollection
from geojson.feature import Feature, FeatureCollection
from geojson.base import GeoJSON
from geojson.crs import Named, Linked

name = Named
link = Linked

########NEW FILE########
__FILENAME__ = feature
"""
SimpleWebFeature is a working example of a class that satisfies the Python geo
interface.
"""

from geojson.base import GeoJSON


class Feature(GeoJSON):

    """A (WGS84) GIS Feature."""

    def __init__(self, id=None, geometry=None, properties=None, **extra):
        super(Feature, self).__init__(**extra)
        self["id"] = id
        if geometry:
            self["geometry"] = self.to_instance(geometry, strict=True)
        else:
            self["geometry"] = None
        self["properties"] = properties or {}


class FeatureCollection(GeoJSON):

    """A collection of Features."""

    def __init__(self, features, **extra):
        super(FeatureCollection, self).__init__(**extra)
        self["features"] = features

########NEW FILE########
__FILENAME__ = geometry
from decimal import Decimal

from geojson.base import GeoJSON


class Geometry(GeoJSON):

    """A (WGS84) GIS geometry."""

    def __init__(self, coordinates=None, crs=None, **extra):
        super(Geometry, self).__init__(**extra)
        self["coordinates"] = coordinates or []
        self.clean_coordinates(self["coordinates"])
        if crs:
            self["crs"] = self.to_instance(crs, strict=True)

    def clean_coordinates(self, coords):
        for coord in coords:
            if isinstance(coord, (list, tuple)):
                self.clean_coordinates(coord)
            elif not isinstance(coord, (float, int, Decimal)):
                raise ValueError("%r is not JSON compliant number", coord)


class GeometryCollection(GeoJSON):

    """A collection of (WGS84) GIS geometries."""

    def __init__(self, geometries=None, **extra):
        super(GeometryCollection, self).__init__(**extra)
        self["geometries"] = geometries or []


# Marker classes.

class Point(Geometry):
    pass


class MultiPoint(Geometry):
    pass


class LineString(MultiPoint):
    pass


class MultiLineString(Geometry):
    pass


class Polygon(Geometry):
    pass


class MultiPolygon(Geometry):
    pass


class Default(object):
    """GeoJSON default."""

########NEW FILE########
__FILENAME__ = mapping
from collections import MutableMapping
try:
    import simplejson as json
except ImportError:
    import json

import geojson


mapping_base = MutableMapping


GEO_INTERFACE_MARKER = "__geo_interface__"


def is_mapping(obj):
    return isinstance(obj, MutableMapping)


def to_mapping(obj):
    mapping = getattr(obj, GEO_INTERFACE_MARKER, None)

    if mapping is not None:
        return mapping

    if is_mapping(obj):
        return obj

    if isinstance(obj, geojson.GeoJSON):
        return dict(obj)

    return json.loads(json.dumps(obj))

########NEW FILE########
__FILENAME__ = test_base
"""
Tests for geojson/base.py
"""

import unittest

import geojson


class OperatorOverloadingTestCase(unittest.TestCase):
    """
    Tests for operator overloading
    """

    def setUp(self):
        self.coords = (12, -5)
        self.point = geojson.Point(self.coords)

    def test_setattr(self):
        new_coords = (27, 42)
        self.point.coordinates = new_coords
        self.assertEqual(self.point['coordinates'], new_coords)

    def test_getattr(self):
        self.assertEqual(self.point['coordinates'], self.point.coordinates)

    def test_delattr(self):
        del self.point.coordinates
        self.assertFalse(hasattr(self.point, 'coordinates'))

########NEW FILE########
__FILENAME__ = test_coords
import unittest

import geojson
from geojson.coords import coords, map_coords


class CoordsTestCase(unittest.TestCase):
    def test_point(self):
        itr = coords(geojson.Point((-115.81, 37.24)))
        self.assertEqual(next(itr), (-115.81, 37.24))

    def test_dict(self):
        itr = coords({'type': 'Point', 'coordinates': [-115.81, 37.24]})
        self.assertEqual(next(itr), (-115.81, 37.24))

    def test_point_feature(self):
        itr = coords(geojson.Feature(geometry=geojson.Point((-115.81, 37.24))))
        self.assertEqual(next(itr), (-115.81, 37.24))

    def test_multipolygon(self):
        g = geojson.MultiPolygon([
            ([(3.78, 9.28), (-130.91, 1.52), (35.12, 72.234), (3.78, 9.28)],),
            ([(23.18, -34.29), (-1.31, -4.61), (3.41, 77.91), (23.18, -34.29)],)])
        itr = coords(g)
        pairs = list(itr)
        self.assertEqual(pairs[0], (3.78, 9.28))
        self.assertEqual(pairs[-1], (23.18, -34.29))

    def test_map_point(self):
        result = map_coords(lambda x: x, geojson.Point((-115.81, 37.24)))
        self.assertEqual(result['type'], 'Point')
        self.assertEqual(result['coordinates'], (-115.81, 37.24))

    def test_map_linestring(self):
        g = geojson.LineString(
            [(3.78, 9.28), (-130.91, 1.52), (35.12, 72.234), (3.78, 9.28)])
        result = map_coords(lambda x: x, g)
        self.assertEqual(result['type'], 'LineString')
        self.assertEqual(result['coordinates'][0], (3.78, 9.28))
        self.assertEqual(result['coordinates'][-1], (3.78, 9.28))

    def test_map_polygon(self):
        g = geojson.Polygon([
            [(3.78, 9.28), (-130.91, 1.52), (35.12, 72.234), (3.78, 9.28)],])
        result = map_coords(lambda x: x, g)
        self.assertEqual(result['type'], 'Polygon')
        self.assertEqual(result['coordinates'][0][0], (3.78, 9.28))
        self.assertEqual(result['coordinates'][0][-1], (3.78, 9.28))

    def test_map_multipolygon(self):
        g = geojson.MultiPolygon([
            ([(3.78, 9.28), (-130.91, 1.52), (35.12, 72.234), (3.78, 9.28)],),
            ([(23.18, -34.29), (-1.31, -4.61), (3.41, 77.91), (23.18, -34.29)],)])
        result = map_coords(lambda x: x, g)
        self.assertEqual(result['type'], 'MultiPolygon')
        self.assertEqual(result['coordinates'][0][0][0], (3.78, 9.28))
        self.assertEqual(result['coordinates'][-1][-1][-1], (23.18, -34.29))

########NEW FILE########
__FILENAME__ = test_crs
import unittest

import geojson


class CRSTest(unittest.TestCase):

    def setUp(self):
        self.crs = geojson.crs.Named(
            properties = {
                "name": "urn:ogc:def:crs:EPSG::3785",
            }
        )

    def test_crs_repr(self):
        actual = repr(self.crs)
        expected = '{"properties": {"name": "urn:ogc:def:crs:EPSG::3785"}, ' \
                   '"type": "name"}'
        self.assertEqual(actual, expected)

    def test_crs_encode(self):
        actual = geojson.dumps(self.crs, sort_keys=True)
        expected = '{"properties": {"name": "urn:ogc:def:crs:EPSG::3785"}, ' \
                   '"type": "name"}'
        self.assertEqual(actual, expected)

    def test_crs_decode(self):
        dumped = geojson.dumps(self.crs)
        actual = geojson.loads(dumped)
        self.assertEqual(actual, self.crs)
########NEW FILE########
__FILENAME__ = test_features
import unittest

import geojson


class FeaturesTest(unittest.TestCase):
    def test_protocol(self):
        """
        A dictionary can satisfy the protocol
        """
        f = {
          'type': 'Feature',
          'id': '1',
          'geometry': {'type': 'Point', 'coordinates': [53, -4]},
          'properties': {'title': 'Dict 1'},
        }

        json = geojson.dumps(f, sort_keys=True)
        self.assertEqual(json, '{"geometry": {"coordinates": [53, -4], "type": "Point"}, "id": "1", "properties": {"title": "Dict 1"}, "type": "Feature"}')

        o = geojson.loads(json)
        output = geojson.dumps(o, sort_keys=True)
        self.assertEqual(output, '{"geometry": {"coordinates": [53, -4], "type": "Point"}, "id": "1", "properties": {"title": "Dict 1"}, "type": "Feature"}')

    def test_feature_class(self):
        """
        Test the Feature class
        """

        from geojson.examples import SimpleWebFeature
        feature = SimpleWebFeature(
            id='1',
            geometry={'type': 'Point', 'coordinates': [53, -4]},
            title='Feature 1', summary='The first feature',
            link='http://example.org/features/1'
        )

        # It satisfies the feature protocol
        self.assertEqual(feature.id, '1')
        self.assertEqual(feature.properties['title'], 'Feature 1')
        self.assertEqual(feature.properties['summary'], 'The first feature')
        self.assertEqual(feature.properties['link'], 'http://example.org/features/1')
        self.assertEqual(geojson.dumps(feature.geometry, sort_keys=True), '{"coordinates": [53, -4], "type": "Point"}')

        # Encoding
        self.assertEqual(geojson.dumps(feature, sort_keys=True), '{"geometry": {"coordinates": [53, -4], "type": "Point"}, "id": "1", "properties": {"link": "http://example.org/features/1", "summary": "The first feature", "title": "Feature 1"}, "type": "Feature"}')

        # Decoding
        factory = geojson.examples.createSimpleWebFeature 
        json = '{"geometry": {"type": "Point", "coordinates": [53, -4]}, "id": "1", "properties": {"summary": "The first feature", "link": "http://example.org/features/1", "title": "Feature 1"}}'
        feature = geojson.loads(json, object_hook=factory, encoding="utf-8")
        self.assertEqual(repr(type(feature)), "<class 'geojson.examples.SimpleWebFeature'>")
        self.assertEqual(feature.id, '1')
        self.assertEqual(feature.properties['title'], 'Feature 1')
        self.assertEqual(feature.properties['summary'], 'The first feature')
        self.assertEqual(feature.properties['link'], 'http://example.org/features/1')
        self.assertEqual(geojson.dumps(feature.geometry, sort_keys=True), '{"coordinates": [53, -4], "type": "Point"}')

    def test_geo_interface(self):
        class Thingy(object):
            def __init__(self, id, title, x, y):
                self.id = id
                self.title = title
                self.x = x
                self.y = y

            @property
            def __geo_interface__(self):
               return {"id": self.id, "properties": {"title": self.title}, "geometry": {"type": "Point", "coordinates": (self.x, self.y)}}

        ob = Thingy('1', 'thingy one', -106, 40)
        self.assertEqual(geojson.dumps(ob.__geo_interface__['geometry'], sort_keys=True), '{"coordinates": [-106, 40], "type": "Point"}')
        self.assertEqual(geojson.dumps(ob, sort_keys=True), '{"geometry": {"coordinates": [-106, 40], "type": "Point"}, "id": "1", "properties": {"title": "thingy one"}}')

########NEW FILE########
__FILENAME__ = test_geo_interface
"""
Encoding/decoding custom objects with __geo_interface__
"""
import unittest

import geojson


class EncodingDecodingTest(unittest.TestCase):

    def setUp(self):
        class Restaurant(object):
            """
            Basic Restaurant class
            """
            def __init__(self, name, latlng):
                super(Restaurant, self).__init__()
                self.name = name
                self.latlng = latlng

        class Restaurant1(Restaurant):
            """
            Extends Restaurant with __geo_interface__ returning dict
            """
            @property
            def __geo_interface__(self):
                return {'type': "Point", 'coordinates': self.latlng}

        class Restaurant2(Restaurant):
            """
            Extends Restaurant with __geo_interface__ returning another
            __geo_interface__ object
            """
            @property
            def __geo_interface__(self):
                return geojson.Point(self.latlng)

        class RestaurantFeature1(Restaurant):
            """
            Extends Restaurant with __geo_interface__ returning dict
            """
            @property
            def __geo_interface__(self):
                return {
                    'geometry': {
                        'type': "Point",
                        'coordinates': self.latlng,
                    },
                    'id': None,
                    'type': "Feature",
                    'properties': {
                        'name': self.name,
                    },
                }

        class RestaurantFeature2(Restaurant):
            """
            Extends Restaurant with __geo_interface__ returning another
            __geo_interface__ object
            """
            @property
            def __geo_interface__(self):
                return geojson.Feature(
                    geometry=geojson.Point(self.latlng),
                    properties={'name': self.name})

        self.name = "In N Out Burger"
        self.latlng = [-54, 4]

        self.restaurant_nogeo = Restaurant(self.name, self.latlng)

        self.restaurant1 = Restaurant1(self.name, self.latlng)
        self.restaurant2 = Restaurant2(self.name, self.latlng)

        self.restaurant_str = (
            '{'
                '"coordinates": [-54, 4], '
                '"type": "Point"'
            '}'
        )

        self.restaurant_feature1 = RestaurantFeature1(self.name, self.latlng)
        self.restaurant_feature2 = RestaurantFeature2(self.name, self.latlng)

        self.restaurant_feature_str = (
            '{'
                '"geometry": {'
                    '"coordinates": [-54, 4], '
                    '"type": "Point"'
                '}, '
                '"id": null, '
                '"properties": {"name": "In N Out Burger"}, '
                '"type": "Feature"'
            '}'
        )


    def test_encode(self):
        """
        Ensure objects that implement __geo_interface__ can be encoded into
        GeoJSON strings
        """
        actual = geojson.dumps(self.restaurant1, sort_keys=True)
        self.assertEqual(actual, self.restaurant_str)

        actual = geojson.dumps(self.restaurant2, sort_keys=True)
        self.assertEqual(actual, self.restaurant_str)

        # Classes that don't implement geo interface should raise TypeError
        self.assertRaises(
            TypeError, geojson.dumps, self.restaurant_nogeo, sort_keys=True)

    def test_encode_nested(self):
        """
        Ensure nested objects that implement __geo_interface__ can be encoded
        into GeoJSON strings
        """
        actual = geojson.dumps(self.restaurant_feature1, sort_keys=True)
        self.assertEqual(actual, self.restaurant_feature_str)

        actual = geojson.dumps(self.restaurant_feature2, sort_keys=True)
        self.assertEqual(actual, self.restaurant_feature_str)

    def test_decode(self):
        """
        Ensure a GeoJSON string can be decoded into GeoJSON objects
        """
        actual = geojson.loads(self.restaurant_str)
        expected = self.restaurant1.__geo_interface__
        self.assertEqual(expected, actual)

    def test_decode_nested(self):
        """
        Ensure a GeoJSON string can be decoded into nested GeoJSON objects
        """
        actual = geojson.loads(self.restaurant_feature_str)
        expected = self.restaurant_feature1.__geo_interface__
        self.assertEqual(expected, actual)

        nested = expected['geometry']
        expected = self.restaurant1.__geo_interface__
        self.assertEqual(nested, expected)

########NEW FILE########
__FILENAME__ = test_null_geometries
import unittest

import geojson


class NullGeometriesTest(unittest.TestCase):

    def test_null_geometry_explicit(self):
        feature = geojson.Feature(
            id=12,
            geometry=None,
            properties={'foo': 'bar'}
        )
        actual = geojson.dumps(feature, sort_keys=True)
        expected = ('{"geometry": null, "id": 12, "properties": {"foo": '
                    '"bar"}, "type": "Feature"}')
        self.assertEqual(actual, expected)

    def test_null_geometry_implicit(self):
        feature = geojson.Feature(
            id=12,
            properties={'foo': 'bar'}
        )
        actual = geojson.dumps(feature, sort_keys=True)
        expected = ('{"geometry": null, "id": 12, "properties": {"foo": '
                    '"bar"}, "type": "Feature"}')
        self.assertEqual(actual, expected)

########NEW FILE########
__FILENAME__ = test_strict_json
"""
GeoJSON produces and consumes only strict JSON. NAN and Infinity are not
permissible values according to the JSON specification.
"""
import unittest

import geojson


class StrictJsonTest(unittest.TestCase):
    def test_encode_nan(self):
        """
        Ensure Error is raised when encoding nan
        """
        unstrict = {
            "type": "Point",
            "coordinates": (float("nan"), 1.0),
        }
        self.assertRaises(ValueError, geojson.dumps, unstrict)

    def test_encode_inf(self):
        """
        Ensure Error is raised when encoding inf or -inf
        """
        unstrict = {
            "type": "Point",
            "coordinates": (float("inf"), 1.0),
        }
        self.assertRaises(ValueError, geojson.dumps, unstrict)

        unstrict = {
            "type": "Point",
            "coordinates": (float("-inf"), 1.0),
        }
        self.assertRaises(ValueError, geojson.dumps, unstrict)

    def test_decode_nan(self):
        """
        Ensure Error is raised when decoding NaN
        """
        unstrict = '{"type": "Point", "coordinates": [1.0, NaN]}'
        self.assertRaises(ValueError, geojson.loads, unstrict)

    def test_decode_inf(self):
        """
        Ensure Error is raised when decoding Infinity or -Infinity
        """
        unstrict = '{"type": "Point", "coordinates": [1.0, Infinity]}'
        self.assertRaises(ValueError, geojson.loads, unstrict)

        unstrict = '{"type": "Point", "coordinates": [1.0, -Infinity]}'
        self.assertRaises(ValueError, geojson.loads, unstrict)

########NEW FILE########
