__FILENAME__ = admin
from django.contrib import admin
from tastypie.models import ApiAccess
from django.contrib.gis.admin import OSMGeoAdmin
from boundaryservice.models import BoundarySet, Boundary


class ApiAccessAdmin(admin.ModelAdmin):
    pass

admin.site.register(ApiAccess, ApiAccessAdmin)


class BoundarySetAdmin(admin.ModelAdmin):
    list_filter = ('authority', 'domain')

admin.site.register(BoundarySet, BoundarySetAdmin)


class BoundaryAdmin(OSMGeoAdmin):
    list_display = ('kind', 'name', 'external_id')
    list_display_links = ('name', 'external_id')
    list_filter = ('kind',)

admin.site.register(Boundary, BoundaryAdmin)

########NEW FILE########
__FILENAME__ = authentication
from django.contrib.auth.models import User

from tastypie.authentication import ApiKeyAuthentication


class NoOpApiKeyAuthentication(ApiKeyAuthentication):
    """
    Allows all users access to all objects, but ensures ApiKeys are properly
    processed for throttling.
    """
    def is_authenticated(self, request, **kwargs):

        username = request.GET.get('username') or request.POST.get('username')
        api_key = request.GET.get('api_key') or request.POST.get('api_key')

        if not username:
            return True

        try:
            user = User.objects.get(username=username)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return self._unauthorized()

        request.user = user

        return self.get_key(user, api_key)

    def _get_anonymous_identifier(self, request):
        return 'anonymous_%s' % request.META.get('REMOTE_ADDR', 'noaddr')

    def get_identifier(self, request):
        return request.REQUEST.get(
            'username', self._get_anonymous_identifier(request))

########NEW FILE########
__FILENAME__ = fields
"""
Custom model fields.
"""
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

class ListField(models.TextField):
    """
    Store a list of values in a Model field.
    """
    __metaclass__ = models.SubfieldBase
 
    def __init__(self, *args, **kwargs):
        self.separator = kwargs.pop('separator', ',')
        super(ListField, self).__init__(*args, **kwargs)
 
    def to_python(self, value):
        if not value: return

        if isinstance(value, list):
            return value

        return value.split(self.separator)
 
    def get_prep_value(self, value):
        if not value: return

        if not isinstance(value, list) and not isinstance(value, tuple):
            raise ValueError('Value for ListField must be either a list or tuple.')

        return self.separator.join([unicode(s) for s in value])
 
    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)

        return self.get_prep_value(value)

class JSONField(models.TextField):
    """
    Store arbitrary JSON in a Model field.
    """
    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        """
        Convert string value to JSON after its loaded from the database.
        """
        if value == "":
            return None

        try:
            if isinstance(value, basestring):
                return json.loads(value)
        except ValueError:
            pass

        return value

    def get_prep_value(self, value):
        """
        Convert our JSON object to a string before being saved.
        """
        if value == "":
            return None

        if isinstance(value, dict) or isinstance(value, list):
            value = json.dumps(value, cls=DjangoJSONEncoder)

        return super(JSONField, self).get_prep_value(value)

    def value_to_string(self, obj):
        """
        Called by the serializer.
        """
        value = self._get_val_from_obj(obj)

        return self.get_db_prep_value(value)

try:
    from south.modelsinspector import add_introspection_rules

    add_introspection_rules([], ["^boundaryservice\.fields\.JSONField"])

    add_introspection_rules([
        (
            [ListField],
            [],
            {
                "separator": ["separator", {"default": ","}],
            },
        ),
    ], ["^boundaryservice\.fields\.ListField"])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = loadshapefiles
import logging
log = logging.getLogger('boundaries.api.load_shapefiles')
from optparse import make_option
import os, os.path
import sys

from zipfile import ZipFile
from tempfile import mkdtemp

from django.conf import settings
from django.contrib.gis.gdal import (CoordTransform, DataSource, OGRGeometry,
                                     OGRGeomType)
from django.core.management.base import BaseCommand
from django.db import connections, DEFAULT_DB_ALIAS, transaction

from boundaryservice.models import BoundarySet, Boundary

DEFAULT_SHAPEFILES_DIR = getattr(settings, 'SHAPEFILES_DIR', 'data/shapefiles')
GEOMETRY_COLUMN = 'shape'


class Command(BaseCommand):
    help = 'Import boundaries described by shapefiles.'
    option_list = BaseCommand.option_list + (
        make_option('-c', '--clear', action='store_true', dest='clear',
            help='Clear all jurisdictions in the DB.'),
        make_option('-d', '--data-dir', action='store', dest='data_dir',
            default=DEFAULT_SHAPEFILES_DIR,
            help='Load shapefiles from this directory'),
        make_option('-e', '--except', action='store', dest='except',
                    default=False,
                    help='Don\'t load these kinds of Areas, comma-delimited.'),
        make_option('-o', '--only', action='store', dest='only',
                    default=False,
                    help='Only load these kinds of Areas, comma-delimited.'),
        make_option('-u', '--database', action='store', dest='database',
                    default=DEFAULT_DB_ALIAS,
                    help='Specify a database to load shape data into.'),
    )

    def get_version(self):
        return '0.1'

    def handle(self, *args, **options):
        # Load configuration
        sys.path.append(options['data_dir'])
        from definitions import SHAPEFILES

        if options['only']:
            only = options['only'].upper().split(',')
            # TODO: stripping whitespace here because optparse doesn't handle 
            # it correctly
            sources = [s for s in SHAPEFILES
                       if s.replace(' ', '').upper() in only]
        elif options['except']:
            exceptions = options['except'].upper().split(',')
            # See above
            sources = [s for s in SHAPEFILES
                       if s.replace(' ', '').upper() not in exceptions]
        else:
            sources = [s for s in SHAPEFILES]

        for kind, config in SHAPEFILES.items():
            if kind not in sources:
                log.info('Skipping %s.' % kind)
                continue

            log.info('Processing %s.' % kind)

            self.load_set(kind, config, options)

    @transaction.commit_on_success
    def load_set(self, kind, config, options):
        log.info('Processing %s.' % kind)

        if options['clear']:
            bset = None

            try:
                bset = BoundarySet.objects.get(name=kind)

                if bset:
                    log.info('Clearing old %s.' % kind)
                    bset.boundaries.all().delete()
                    bset.delete()

                    log.info('Loading new %s.' % kind)
            except BoundarySet.DoesNotExist:
                log.info('No existing boundary set of kind [%s] so nothing to '
                         'delete' % kind)

        path = os.path.join(options['data_dir'], config['file'])
        datasources = create_datasources(path)

        layer = datasources[0][0]

        # Create BoundarySet
        log.info("Creating BoundarySet: %s" % kind)
        bset = BoundarySet.objects.create(
            name=kind,
            singular=config['singular'],
            kind_first=config['kind_first'],
            authority=config['authority'],
            domain=config['domain'],
            last_updated=config['last_updated'],
            href=config['href'],
            notes=config['notes'],
            count=0,
            metadata_fields=layer.fields
        )
        log.info("Created with slug %s and id %s" % (bset.slug, bset.id))
        
        for datasource in datasources:
            log.info("Loading %s from %s" % (kind, datasource.name))
            # Assume only a single-layer in shapefile
            if datasource.layer_count > 1:
                log.warn('%s shapefile [%s] has multiple layers, using first.'
                         % (datasource.name, kind))
            layer = datasource[0]
            self.add_boundaries_for_layer(config, layer, bset,
                                          options['database'])
        # sync this with reality
        bset.count = Boundary.objects.filter(set=bset).count()
        bset.save()
        log.info('%s count: %i' % (kind, bset.count))

    def polygon_to_multipolygon(self, geom):
        """
        Convert polygons to multipolygons so all features are homogenous in the
        database.
        """
        if geom.__class__.__name__ == 'Polygon':
            g = OGRGeometry(OGRGeomType('MultiPolygon'))
            g.add(geom)
            return g
        elif geom.__class__.__name__ == 'MultiPolygon':
            return geom
        else:
            raise ValueError('Geom is neither Polygon nor MultiPolygon.')

    def add_boundaries_for_layer(self, config, layer, bset, database):
        # Get spatial reference system for the postgis geometry field
        geometry_field = Boundary._meta.get_field_by_name(GEOMETRY_COLUMN)[0]
        SpatialRefSys = connections[database].ops.spatial_ref_sys()
        db_srs = SpatialRefSys.objects.using(database).get(
            srid=geometry_field.srid).srs

        if 'srid' in config and config['srid']:
            layer_srs = SpatialRefSys.objects.get(srid=config['srid']).srs
        else:
            layer_srs = layer.srs

        # Simplification can be configured but default is to create simplified
        # geometry field by collapsing points within 1/1000th of a degree.
        # For reference, Chicago is at approx. 42 degrees latitude this works
        # out to a margin of roughly 80 meters latitude and 112 meters
        # longitude for Chicago area.
        simplification = config.get('simplification', 0.0001)

        # Create a convertor to turn the source data into
        transformer = CoordTransform(layer_srs, db_srs)

        for feature in layer:
            log.debug("Processing boundary %s" % feature)
            # Transform the geometry to the correct SRS
            geometry = self.polygon_to_multipolygon(feature.geom)
            geometry.transform(transformer)

            # Preserve topology prevents a shape from ever crossing over
            # itself.
            simple_geometry = geometry.geos.simplify(simplification,
                                                     preserve_topology=True)

            # Conversion may force multipolygons back to being polygons
            simple_geometry = self.polygon_to_multipolygon(simple_geometry.ogr)

            # Extract metadata into a dictionary
            metadata = {}

            for field in layer.fields:

                # Decode string fields using encoding specified in definitions
                # config
                if config['encoding'] != '':
                    try:
                        metadata[field] = feature.get(field).decode(
                            config['encoding'])
                    # Only strings will be decoded, get value in normal way if
                    # int etc.
                    except AttributeError:
                        metadata[field] = feature.get(field)
                else:
                    metadata[field] = feature.get(field)

            external_id = config['ider'](feature)
            feature_name = config['namer'](feature)

            # If encoding is specified, decode id and feature name
            if config['encoding'] != '':
                external_id = external_id.decode(config['encoding'])
                feature_name = feature_name.decode(config['encoding'])

            if config['kind_first']:
                display_name = '%s %s' % (config['singular'], feature_name)
            else:
                display_name = '%s %s' % (feature_name, config['singular'])

            Boundary.objects.create(
                set=bset,
                kind=config['singular'],
                external_id=external_id,
                name=feature_name,
                display_name=display_name,
                metadata=metadata,
                shape=geometry.wkt,
                simple_shape=simple_geometry.wkt,
                centroid=geometry.geos.centroid)

def create_datasources(path):
    if path.endswith('.zip'):
        path = temp_shapefile_from_zip(path)

    if path.endswith('.shp'):
        return [DataSource(path)]

    # assume it's a directory...
    sources = []
    for fn in os.listdir(path):
        fn = os.path.join(path,fn)
        if fn.endswith('.zip'):
            fn = temp_shapefile_from_zip(fn)
        if fn.endswith('.shp'):
            sources.append(DataSource(fn))
    return sources

def temp_shapefile_from_zip(zip_path):
    """
    Given a path to a ZIP file, unpack it into a temp dir and return the path
    to the shapefile that was in there.  Doesn't clean up after itself unless
    there was an error.

    If you want to cleanup later, you can derive the temp dir from this path.
    """
    log.info("Creating temporary SHP file from %s" % zip_path)
    zf = ZipFile(zip_path)
    tempdir = mkdtemp()
    shape_path = None
    # Copy the zipped files to a temporary directory, preserving names.
    for name in zf.namelist():
        data = zf.read(name)
        outfile = os.path.join(tempdir, name)
        if name.endswith('.shp'):
            shape_path = outfile
        f = open(outfile, 'w')
        f.write(data)
        f.close()

    if shape_path is None:
        log.warn("No shapefile, cleaning up")
        # Clean up after ourselves.
        for file in os.listdir(tempdir):
            os.unlink(os.path.join(tempdir, file))
        os.rmdir(tempdir)
        raise ValueError("No shapefile found in zip")

    return shape_path

########NEW FILE########
__FILENAME__ = startshapedefinitions
import logging 
log = logging.getLogger('boundaries.api.load_shapefiles')
from optparse import make_option
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

DEFAULT_SHAPEFILES_DIR = getattr(settings, 'SHAPEFILES_DIR', 'data/shapefiles')

class Command(BaseCommand):
    """
    Create a new definitions.py file to configure shapefiles to be loaded into the database.
    
    Fails if the file already exists. Requires that the SHAPEFILES_DIR setting is configured.
    
    You can force the creation of a new file by adding the `-f` or `--force`` flag.
    
    Example usage::
    
        $ python manage.py startshapedefinitions
    
    """
    help = 'Create a new definitions.py file to configure shapefiles to be loaded into the database.'
    custom_options = (
        make_option('-f', '--force',
            action='store_true', dest='force',
            help='Force the creation of a new definitions.py, even if it already exists.'
        ),
        make_option('-d', '--data-dir', action='store', dest='data_dir', 
            default=DEFAULT_SHAPEFILES_DIR,
            help='Load shapefiles from this directory'
        ),
    )
    option_list = BaseCommand.option_list + custom_options
    
    def handle(self, *args, **options):
        if not os.path.exists(options['data_dir']):
            raise CommandError("The shapefiles directory '%s' does not exist. Create it or specify a different directory." % options['data_dir'])
        def_path = os.path.join(options['data_dir'], "definitions.py")
        if os.path.exists(def_path) and not options.get("force"):
            raise CommandError("%s already exists." % def_path)
        outfile = open(def_path, "w")
        outfile.write(BOILERPLATE)
        outfile.close()
        logging.info('Created definitions.py in %s' % options['data_dir'])

BOILERPLATE = """from datetime import date

from boundaryservice import utils

SHAPEFILES = {
    # This key should be the plural name of the boundaries in this set
    'City Council Districts': {
        # Path to a shapefile, relative to /data/shapefiles
        'file': 'city_council_districts/Council Districts.shp',
        # Generic singular name for an boundary of from this set
        'singular': 'City Council District',
        # Should the singular name come first when creating canonical identifiers for this set?
        'kind_first': False,
        # Function which each feature wall be passed to in order to extract its "external_id" property
        # The utils module contains several generic functions for doing this
        'ider': utils.simple_namer(['DISTRICT']),
        # Function which each feature will be passed to in order to extract its "name" property
        'namer': utils.simple_namer(['NAME']),
        # Authority that is responsible for the accuracy of this data
        'authority': 'Tyler GIS Department',
        # Geographic extents which the boundary set encompasses
        'domain': 'Tyler',
        # Last time the source was checked for new data
        'last_updated': date(2011, 5, 14),
        # A url to the source of the data
        'href': 'http://www.smithcountymapsite.org/webshare/data.html',
        # Notes identifying any pecularities about the data, such as columns that were deleted or files which were merged
        'notes': '',
        # Encoding of the text fields in the shapefile, i.e. 'utf-8'. If this is left empty 'ascii' is assumed
        'encoding': '',
        # SRID of the geometry data in the shapefile if it can not be inferred from an accompanying .prj file
        # This is normally not necessary and can be left undefined or set to an empty string to maintain the default behavior
        'srid': '',
        # Simplification tolerance to use when creating the simple_geometry
        # column for this shapefile, larger numbers create polygons with fewer
        # points.
        'simplification': 0.0001,
    }
}
"""

########NEW FILE########
__FILENAME__ = models
import re
from django.contrib.gis.db import models
from boundaryservice.fields import ListField, JSONField
from boundaryservice.utils import get_site_url_root


class SluggedModel(models.Model):
    """
    Extend this class to get a slug field and slug generated from a model
    field. We call the 'get_slug_text', '__unicode__' or '__str__'
    methods (in that order) on save() to get text to slugify. The slug may
    have numbers appended to make sure the slug is unique.
    """
    slug = models.SlugField(max_length=256)
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        self.unique_slug()  
        if self.slug == '': raise ValueError, "Slug may not be blank [%s]" % str(self)
        super(SluggedModel,self).save(*args, **kwargs)

    def unique_slug(self):
        """
        Customized unique_slug function
        """
        if not getattr(self, "slug"): # if it's already got a slug, do nothing.
            from django.template.defaultfilters import slugify
            if hasattr(self,'get_slug_text') and callable(self.get_slug_text):
                slug_txt = self.get_slug_text()
            elif hasattr(self,'__unicode__'):
                slug_txt = unicode(self)
            elif hasattr(self,'__str__'):
                slug_txt = str(self)
            else:
                return
            original_slug = slugify(slug_txt)
            queryset = self.__class__._default_manager.all()
            if not queryset.filter(slug=original_slug).count():
                setattr(self, "slug", original_slug)
            else:
                slug = ''
                next = 2
                while not slug or queryset.filter(slug=slug).count():
                    slug = original_slug
                    end = '-%s' % next
                    if len(slug) + len(end) > 256:
                        slug = slug[:200-len(end)]
                    slug = '%s%s' % (slug, end)
                    next += 1
                setattr(self, "slug", slug)
    
    def fully_qualified_url(self):
        return get_site_url_root() + self.get_absolute_url()


class BoundarySet(SluggedModel):
    """
    A set of related boundaries, such as all Wards or Neighborhoods.
    """
    name = models.CharField(max_length=64, unique=True,
        help_text='Category of boundaries, e.g. "Community Areas".')
    singular = models.CharField(max_length=64,
        help_text='Name of a single boundary, e.g. "Community Area".')
    kind_first = models.BooleanField(
        help_text='If true, boundary display names will be "kind name" (e.g. Austin Community Area), otherwise "name kind" (e.g. 43rd Precinct).')
    authority = models.CharField(max_length=256,
        help_text='The entity responsible for this data\'s accuracy, e.g. "City of Chicago".')
    domain = models.CharField(max_length=256,
        help_text='The area that this BoundarySet covers, e.g. "Chicago" or "Illinois".')
    last_updated = models.DateField(
        help_text='The last time this data was updated from its authority (but not necessarily the date it is current as of).')
    href = models.URLField(blank=True,
        help_text='The url this data was found at, if any.')
    notes = models.TextField(blank=True,
        help_text='Notes about loading this data, including any transformations that were applied to it.')
    count = models.IntegerField(
        help_text='Total number of features in this boundary set.')
    metadata_fields = ListField(separator='|', blank=True,
        help_text='What, if any, metadata fields were loaded from the original dataset.')

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        """
        Print plural names.
        """
        return unicode(self.name)


class Boundary(SluggedModel):
    """
    A boundary object, such as a Ward or Neighborhood.
    """
    set = models.ForeignKey(BoundarySet, related_name='boundaries',
        help_text='Category of boundaries that this boundary belongs, e.g. "Community Areas".')
    kind = models.CharField(max_length=64,
        help_text='A copy of BoundarySet\'s "singular" value for purposes of slugging and inspection.')
    external_id = models.CharField(max_length=64,
        help_text='The boundaries\' unique id in the source dataset, or a generated one.')
    name = models.CharField(max_length=192, db_index=True,
        help_text='The name of this boundary, e.g. "Austin".')
    display_name = models.CharField(max_length=256,
        help_text='The name and kind of the field to be used for display purposes.')
    metadata = JSONField(blank=True,
        help_text='The complete contents of the attribute table for this boundary from the source shapefile, structured as json.')
    shape = models.MultiPolygonField(srid=4269,
        help_text='The geometry of this boundary in EPSG:4269 projection.')
    simple_shape = models.MultiPolygonField(srid=4269,
        help_text='The geometry of this boundary in EPSG:4269 projection and simplified to 0.0001 tolerance.')
    centroid = models.PointField(srid=4269,
        null=True,
        help_text='The centroid (weighted center) of this boundary in EPSG:4269 projection.')
    
    objects = models.GeoManager()

    class Meta:
        ordering = ('kind', 'display_name')
        verbose_name_plural = 'boundaries'

    def __unicode__(self):
        """
        Print names are formatted like "Austin Community Area"
        and will slug like "austin-community-area".
        """
        return unicode(self.display_name)

########NEW FILE########
__FILENAME__ = resources
import re

from django.conf import settings
from django.contrib.gis.measure import D
from tastypie import fields
from tastypie.serializers import Serializer
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from django.contrib.gis.geos import Polygon

from boundaryservice.authentication import NoOpApiKeyAuthentication
from boundaryservice.models import BoundarySet, Boundary
from boundaryservice.tastyhacks import SluggedResource
from boundaryservice.throttle import AnonymousThrottle

if getattr(settings, 'BOUNDARY_SERVICE_THROTTLE', False):
    throttle_cls = AnonymousThrottle(**settings.BOUNDARY_SERVICE_THROTTLE)
else:
    throttle_cls = False


class BoundarySetResource(SluggedResource):
    boundaries = fields.ToManyField(
        'boundaryservice.resources.BoundaryResource', 'boundaries')

    class Meta:
        queryset = BoundarySet.objects.all()
        serializer = Serializer(
            formats=['json', 'jsonp'],
            content_types={
                'json': 'application/json',
                'jsonp': 'text/javascript'})
        resource_name = 'boundary-set'
        excludes = ['id', 'singular', 'kind_first']
        allowed_methods = ['get']
        authentication = NoOpApiKeyAuthentication()
        throttle = throttle_cls


class BoundaryResource(SluggedResource):
    set = fields.ForeignKey(BoundarySetResource, 'set')

    class Meta:
        queryset = Boundary.objects.all()
        serializer = Serializer(
            formats=['json', 'jsonp'],
            content_types={
                'json': 'application/json',
                'jsonp': 'text/javascript'})
        resource_name = 'boundary'
        excludes = ['id', 'display_name']
        allowed_methods = ['get']
        authentication = NoOpApiKeyAuthentication()
        throttle = throttle_cls
        filtering = {
            "slug": ALL
        }

    def alter_list_data_to_serialize(self, request, data):
        """
        Allow the selection of simple, full or no shapes
        using a query parameter.
        """
        shape_type = request.GET.get('shape_type', 'simple')

        for obj in data['objects']:
            if shape_type != 'simple':
                del obj.data['simple_shape']

            if shape_type != 'full':
                del obj.data['shape']

        return data

    def alter_detail_data_to_serialize(self, request, bundle):
        """
        Allow the selection of simple, full or no shapes
        using a query parameter.
        """
        shape_type = request.GET.get('shape_type', 'simple')

        if shape_type != 'simple':
            del bundle.data['simple_shape']

        if shape_type != 'full':
            del bundle.data['shape']

        return bundle

    def build_filters(self, filters=None):
        """
        Override build_filters to support geoqueries.
        """
        if filters is None:
            filters = {}

        orm_filters = super(BoundaryResource, self).build_filters(filters)

        if 'sets' in filters:
            sets = filters['sets'].split(',')

            orm_filters.update({'set__slug__in': sets})

        if 'contains' in filters:
            lat, lon = filters['contains'].split(',')
            wkt_pt = 'POINT(%s %s)' % (lon, lat)

            orm_filters.update({'shape__contains': wkt_pt})

        if 'near' in filters:
            lat, lon, range = filters['near'].split(',')
            wkt_pt = 'POINT(%s %s)' % (lon, lat)
            numeral = re.match('([0-9]+)', range).group(1)
            unit = range[len(numeral):]
            numeral = int(numeral)
            kwargs = {unit: numeral}

            orm_filters.update({'shape__distance_lte': (wkt_pt, D(**kwargs))})

        if 'intersects' in filters:
            slug = filters['intersects']
            bounds = Boundary.objects.get(slug=slug)

            orm_filters.update({'shape__intersects': bounds.shape})

        if 'bbox' in filters:
            xmin, ymin, xmax, ymax = filters['bbox'].split(",")
            bbox = (xmin, ymin, xmax, ymax)
            bbox = Polygon.from_bbox(bbox)

            orm_filters.update({'shape__intersects': bbox})

        return orm_filters

########NEW FILE########
__FILENAME__ = tastyhacks
import json

from django.conf.urls.defaults import url
from django.contrib.gis.db.models import GeometryField

from tastypie.bundle import Bundle
from tastypie.fields import ApiField, CharField
from tastypie.resources import ModelResource
from tastypie.utils import trailing_slash

from boundaryservice.fields import ListField, JSONField

class ListApiField(ApiField):
    """
    Custom ApiField for dealing with data from custom ListFields.
    """
    dehydrated_type = 'list'
    help_text = 'Delimited list of items.'
    
    def dehydrate(self, obj):
        return self.convert(super(ListApiField, self).dehydrate(obj))
    
    def convert(self, value):
        if value is None:
            return None
        
        return value

class JSONApiField(ApiField):
    """
    Custom ApiField for dealing with data from custom JSONFields.
    """
    dehydrated_type = 'json'
    help_text = 'JSON structured data.'
    
    def dehydrate(self, obj):
        return self.convert(super(JSONApiField, self).dehydrate(obj))
    
    def convert(self, value):
        if value is None:
            return None
        
        return value

class GeometryApiField(ApiField):
    """
    Custom ApiField for dealing with data from GeometryFields (by serializing them as GeoJSON) .
    """
    dehydrated_type = 'geometry'
    help_text = 'Geometry data.'
    
    def dehydrate(self, obj):
        return self.convert(super(GeometryApiField, self).dehydrate(obj))
    
    def convert(self, value):
        if value is None:
            return None

        if isinstance(value, dict):
            return value

        # Get ready-made geojson serialization and then convert it _back_ to a Python object
        # so that Tastypie can serialize it as part of the bundle
        return json.loads(value.geojson)


class SluggedResource(ModelResource):
    """
    ModelResource subclass that handles looking up models by slugs rather than IDs.
    """
    def override_urls(self):
        """
        Add slug-based url pattern.
        """
        return [
            url(r"^(?P<resource_name>%s)/schema%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_schema'), name="api_get_schema"),
            url(r"^(?P<resource_name>%s)/(?P<slug>[\w\d_.-]+)/$" % self._meta.resource_name, self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
            ]

    def get_resource_uri(self, bundle_or_obj=None):
        """
        Override URI generation to use slugs.
        """
        # If there's no bundle_or_obj, something newer
        # versions of tastypie will try, just go with
        # the default method.
        if not bundle_or_obj:
            return super(ModelResource, self).get_resource_uri(bundle_or_obj)
        
        kwargs = {
            'resource_name': self._meta.resource_name,
        }
        
        if isinstance(bundle_or_obj, Bundle):
            kwargs['slug'] = bundle_or_obj.obj.slug
        else:
            kwargs['slug'] = bundle_or_obj.slug
        
        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name
        
        return self._build_reverse_url("api_dispatch_detail", kwargs=kwargs)

    @classmethod
    def api_field_from_django_field(cls, f, default=CharField):
        """
        Overrides default field handling to support custom ListField and JSONField.
        """
        if isinstance(f, ListField):
            return ListApiField
        elif isinstance(f, JSONField):
            return JSONApiField
        elif isinstance(f, GeometryField):
            return GeometryApiField
    
        return super(SluggedResource, cls).api_field_from_django_field(f, default)

########NEW FILE########
__FILENAME__ = throttle
from tastypie.throttle import CacheThrottle

class AnonymousThrottle(CacheThrottle):
    """
    Anonymous users are throttled, but those with a valid API key are not.
    """
    def should_be_throttled(self, identifier, **kwargs):
        if not identifier.startswith('anonymous_'):
            return False

        return super(AnonymousThrottle, self).should_be_throttled(identifier, **kwargs)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include 
from tastypie.api import Api

from boundaryservice.resources import BoundarySetResource, BoundaryResource
from boundaryservice.views import external_id_redirects

v1_api = Api(api_name='1.0')
v1_api.register(BoundarySetResource())
v1_api.register(BoundaryResource())

urlpatterns = patterns('',
    (r'^(?P<api_name>1.0)/(?P<resource_name>boundary-set)/(?P<slug>[\w\d_.-]+)/(?P<external_id>[\w\d_.-]+)$', external_id_redirects),
    (r'', include(v1_api.urls)),
)

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings

def get_site_url_root():
    domain = getattr(settings, 'MY_SITE_DOMAIN', 'localhost')
    protocol = getattr(settings, 'MY_SITE_PROTOCOL', 'http')
    port     = getattr(settings, 'MY_SITE_PORT', '')
    url = '%s://%s' % (protocol, domain)
    if port:
        url += ':%s' % port
    return url

#
# Utility methods for transforming shapefile columns into useful representations
#

class static_namer():
    """
    Name features with a single, static name.
    """
    def __init__(self, name):
        self.name = name
    
    def __call__(self, feature):
        return self.name


class index_namer():
    """
    Name features with a static prefix, plus an iterating value.
    """
    def __init__(self, prefix):
        self.prefix = prefix
        self.i = 0
    
    def __call__(self, feature):
        out = '%s%i' % (self.prefix, self.i)
        self.i += 1
        return out


class simple_namer():
    """
    Name features with a joined combination of attributes, optionally passing 
    the result through a normalizing function.
    """
    def __init__(self, attribute_names, seperator=' ', normalizer=None):
        self.attribute_names = attribute_names
        self.seperator = seperator
        self.normalizer = normalizer

    def __call__(self, feature):
        attribute_values = map(str, map(feature.get, self.attribute_names))
        name = self.seperator.join(attribute_values).strip()
        
        if self.normalizer:
            normed = self.normalizer(name)
            if not normed:
                raise ValueError('Failed to normalize \"%s\".' % name)
            else:
                name = normed
        
        return name


########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse, resolve
from django.http import Http404
from django.shortcuts import get_object_or_404

from boundaryservice.models import Boundary

def external_id_redirects(request, api_name, resource_name, slug, external_id):
    """
    Fake-redirects /boundary-set/slug/external_id paths to the proper canonical boundary path.
    """
    if resource_name != 'boundary-set':
        raise Http404 

    boundary = get_object_or_404(Boundary, set__slug=slug, external_id=external_id)
    
    # This bit of hacky code allows to execute the resource view as the canonical url were hit, but without redirecting
    # Note that the resource will still have correct, canonical 'resource_uri' attribute attached
    canonical_url = reverse('api_dispatch_detail', kwargs={'api_name': api_name, 'resource_name': 'boundary', 'slug': boundary.slug})
    view, args, kwargs = resolve(canonical_url)

    return view(request, *args, **kwargs)


########NEW FILE########
