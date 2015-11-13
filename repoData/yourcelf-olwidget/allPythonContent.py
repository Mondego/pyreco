__FILENAME__ = admin
"""
Example to use olwidget for mapping in the django admin site::

    from olwidget import admin
    from myapp import SomeGeoModel

    admin.site.register(SomeGeoModel, admin.GeoModelAdmin)

If you want to use custom OLWidget options to change the look and feel of the
map, just subclass GeoModelAdmin, and define "options", for example::

    class CustomGeoAdmin(admin.GeoModelAdmin):
        options = {
            'layers': ['google.hybrid'],
            'overlayStyle': {
                'fillColor': '#ffff00',
                'strokeWidth': 5,
            },
            'defaultLon': -72,
            'defaultLat': 44,
            'defaultZoom': 4,
        }

    admin.site.register(SomeGeoModel, CustomGeoAdmin)

A complete list of options is in the olwidget documentation.
"""

from django.contrib.admin import ModelAdmin
from django.contrib.gis.geos import GeometryCollection
from django.contrib.admin.options import csrf_protect_m
from django.utils.encoding import force_unicode

from olwidget.forms import apply_maps_to_modelform_fields, fix_initial_data, fix_cleaned_data
from olwidget.widgets import InfoMap
from olwidget.utils import DEFAULT_PROJ

__all__ = ('GeoModelAdmin',)

class GeoModelAdmin(ModelAdmin):
    options = None
    map_template = "olwidget/admin_olwidget.html"
    list_map = None
    list_map_options = None
    maps = None
    change_list_template = "admin/olwidget_change_list.html"
    default_field_class = None

    def get_form(self, *args, **kwargs):
        """
        Get a ModelForm with our own `__init__` and `clean` methods.  However,
        we need to allow ModelForm's metaclass_factory to run unimpeded, so
        dynamically override the methods rather than subclassing.
        """
        # Get the vanilla modelform class
        ModelForm = super(GeoModelAdmin, self).get_form(*args, **kwargs)

        # enclose klass.__init__
        orig_init = ModelForm.__init__
        def new_init(self, *args, **kwargs):
            orig_init(self, *args, **kwargs)
            fix_initial_data(self.initial, self.initial_data_keymap)

        # enclose klass.clean
        orig_clean = ModelForm.clean
        def new_clean(self):
            orig_clean(self)
            fix_cleaned_data(self.cleaned_data, self.initial_data_keymap)
            return self.cleaned_data

        # Override methods
        ModelForm.__init__ = new_init
        ModelForm.clean = new_clean

        # Rearrange fields
        ModelForm.initial_data_keymap = apply_maps_to_modelform_fields(
                ModelForm.base_fields, self.maps, self.options,
                self.map_template,
                default_field_class=self.default_field_class)
        return ModelForm

    def get_changelist_map(self, cl, request=None):
        """
        Display a map in the admin changelist, with info popups
        """
        if self.list_map:
            info = []
            if request:
                qs = cl.get_query_set(request)
            else:
                qs = cl.get_query_set()
            for obj in qs:
                # Transform the fields into one projection.
                geoms = []
                for field in self.list_map:
                    geom = getattr(obj, field)
                    if geom:
                        if callable(geom):
                            geom = geom()
                        geoms.append(geom)
                for geom in geoms:
                    geom.transform(int(DEFAULT_PROJ))

                if geoms:
                    info.append((
                        GeometryCollection(geoms, srid=int(DEFAULT_PROJ)),
                        "<a href='%s'>%s</a>" % (
                            cl.url_for_result(obj),
                            force_unicode(obj)
                        )
                    ))

            return InfoMap(info, options=self.list_map_options)
        return None

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        template_response = super(GeoModelAdmin, self).changelist_view(
                request, extra_context)
        if hasattr(template_response, 'context_data') and \
                'cl' in template_response.context_data:
            map_ = self.get_changelist_map(
                    template_response.context_data['cl'], request)
            if map_:
                template_response.context_data['media'] += map_.media
                template_response.context_data['map'] = map_
        return template_response

########NEW FILE########
__FILENAME__ = fields
from django import forms

from olwidget.widgets import Map, EditableLayer, InfoLayer

from django.contrib.gis.forms.fields import GeometryField

class MapField(forms.fields.Field):
    """
    Container field for map fields.  Similar to MultiValueField, but with
    greater autonomy of component fields.  Values are never "compressed" or
    "decompressed", and component fields are consulted for their validation.
    Example:

        MapField([EditableLayerField(), InfoLayerField()], options={...})

    """
    def __init__(self, fields=None, options=None, layer_names=None, 
            template=None, **kwargs):
        # create map widget enclosing vector layers and options
        if not fields:
            fields = [EditableLayerField()]
        layers = [field.widget for field in fields]
        self.fields = fields
        kwargs['widget'] = kwargs.get('widget', 
                Map(layers, options, template, layer_names))
        super(MapField, self).__init__(**kwargs)

    def clean(self, value):
        """
        Return an array with the value from each layer.
        """
        return [f.clean(v) for v,f in zip(value, self.fields)]

class EditableLayerField(GeometryField):
    """
    Equivalent to:

    GeometryField(widget=EditableLayer(options={...}))
    """
    def __init__(self, options=None, **kwargs):
        kwargs['widget'] = kwargs.get('widget', EditableLayer(options))
        super(EditableLayerField, self).__init__(**kwargs)

class InfoLayerField(forms.fields.CharField):
    """
    Equivalent to:

    forms.CharField(widget=InfoLayer(info=[...], options={...}), 
            required=False)
    """
    def __init__(self, info, options=None, **kwargs):
        kwargs['widget'] = kwargs.get('widget', InfoLayer(info, options))
        kwargs['required'] = False
        super(InfoLayerField, self).__init__(**kwargs)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.gis.forms.fields import GeometryField

from olwidget.widgets import Map, BaseVectorLayer, EditableLayer
from olwidget.fields import MapField
from olwidget import utils

__all__ = ('MapModelForm', )

class BaseMapModelForm(forms.models.BaseModelForm):
    """
    ModelForm type that uses olwidget maps for geometry fields.  Multiple
    fields can be edited in a single map -- to do this, specify a property
    "maps" of the inner Meta class which lists fields and map options:

    class MyMapModelForm(MapModelForm):
        class Meta:
            model = MyModel
            maps = (
                (('geom1', 'geom2'), {'layers': ['google.streets]}), 
                (('geom3',), None), 
                ...
            ) 
    """
    def __init__(self, *args, **kwargs):
        super(BaseMapModelForm, self).__init__(*args, **kwargs)
        fix_initial_data(self.initial, self.initial_data_keymap)

    def clean(self):
        super(BaseMapModelForm, self).clean()
        fix_cleaned_data(self.cleaned_data, self.initial_data_keymap)
        return self.cleaned_data

class MapModelFormOptions(forms.models.ModelFormOptions):
    def __init__(self, options=None):
        super(MapModelFormOptions, self).__init__(options)
        self.maps = getattr(options, 'maps', None)
        if not self.maps:
            self.maps = getattr(options, 'options', None)
        self.default_field_class = getattr(options, 'default_field_class', None)
        self.template = getattr(options, 'template', None)

class MapModelFormMetaclass(type):
    """ 
    Metaclass for map-containing ModelForm widgets.  The implementation is
    mostly copied from django's ModelFormMetaclass, but we change the
    hard-coded parent class name and add our map field processing parts.
    """
    def __new__(mcs, name, bases, attrs):
        formfield_callback = attrs.pop('formfield_callback',
                lambda f, **kwargs: f.formfield(**kwargs))
        try:
            parents = [b for b in bases if issubclass(b, MapModelForm)]
        except NameError:
            # We are defining MapModelForm itself.
            parents = None
        declared_fields = forms.models.get_declared_fields(bases, attrs, False)
        new_class = super(MapModelFormMetaclass, mcs).__new__(mcs, name, bases,
                attrs)
        if not parents:
            return new_class

        if 'media' not in attrs:
            new_class.media = forms.widgets.media_property(new_class)
        opts = new_class._meta = MapModelFormOptions(
                getattr(new_class, 'Meta', None))
        if opts.model:
            # If a model is defined, extract form fields from it.
            fields = forms.models.fields_for_model(opts.model, opts.fields,
                                      opts.exclude, opts.widgets, 
                                      formfield_callback)

            # Override default model fields with any custom declared ones
            # (plus, include all the other declared fields).
            fields.update(declared_fields)
        else:
            fields = declared_fields

        # Transform base fields by extracting types mentioned in 'maps'
        initial_data_keymap = apply_maps_to_modelform_fields(
                fields, opts.maps, default_field_class=opts.default_field_class,
                default_template=opts.template)

        new_class.initial_data_keymap = initial_data_keymap
        new_class.declared_fields = declared_fields
        new_class.base_fields = fields
        return new_class

class MapModelForm(BaseMapModelForm):
    __metaclass__ = MapModelFormMetaclass

def fix_initial_data(initial, initial_data_keymap):
    """ 
    Take a dict like this as `initial`:
    { 'key1': 'val1', 'key2': 'val2', 'key3': 'val3'}
    and a dict like this as `initial_data_keymap`:
    { 'newkey1': ['key1', 'key2'], 'newkey2': ['key3']}
    and remap the initial dict to have this form:
    { 'newkey1': ['val1', 'val2'], 'newkey2': ['val3']}

    Used for rearranging initial data in fields to match declared maps.
    """
    if initial:
        for dest, sources in initial_data_keymap.iteritems():
            data = [initial.pop(s, None) for s in sources]
            initial[dest] = data
    return initial

def fix_cleaned_data(cleaned_data, initial_data_keymap):
    for group, keys in initial_data_keymap.iteritems():
        if cleaned_data.has_key(group):
            vals = cleaned_data.pop(group)
            if isinstance(vals, (list, tuple)):
                for key, val in zip(keys, vals):
                    cleaned_data[key] = val
            else:
                cleaned_data[keys[0]] = vals
    return cleaned_data

def apply_maps_to_modelform_fields(fields, maps, default_options=None, 
                                   default_template=None, default_field_class=None):
    """
    Rearranges fields to match those defined in ``maps``.  ``maps`` is a list
    of [field_list, options_dict] pairs.  For each pair, a new map field is
    created that contans all the fields in ``field_list``.
    """
    if default_field_class is None:
        default_field_class = MapField
    map_field_names = (name for name,field in fields.iteritems() if isinstance(field, (MapField, GeometryField)))
    if not maps:
        maps = [((name,),) for name in map_field_names]
    elif isinstance(maps, dict):
        maps = [[tuple(map_field_names), maps]]

    default_options = utils.get_options(default_options)
    initial_data_keymap = {}

    for map_definition in maps:
        field_list = map_definition[0]
        if len(map_definition) > 1:
            options = map_definition[1]
        else:
            options = {}
        if len(map_definition) > 2:
            template = map_definition[2]
        else:
            template = default_template
        
        map_name = "_".join(field_list)
        layer_fields = []
        names = []
        min_pos = 65535 # arbitrarily high number for field ordering
        initial = []
        for field_name in field_list:
            min_pos = min(min_pos, fields.keyOrder.index(field_name))
            field = fields.pop(field_name)
            initial.append(field_name)
            if not isinstance(field.widget, (Map, BaseVectorLayer)):
                field.widget = EditableLayer(
                        options=utils.options_for_field(field))
            layer_fields.append(field)
            names.append(field_name)

        if isinstance(field, MapField):
            map_field = field
        else:
            map_opts = {}
            map_opts.update(default_options)
            map_opts.update(options or {})
            map_field = default_field_class(layer_fields, map_opts, layer_names=names,
                label=", ".join(forms.forms.pretty_name(f) for f in field_list),
                template=template)
        fields.insert(min_pos, map_name, map_field)
        initial_data_keymap[map_name] = initial
    return initial_data_keymap


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

from django import forms
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point

from olwidget.fields import MapField, EditableLayerField, InfoLayerField
from olwidget.widgets import EditableMap, InfoMap
from olwidget.forms import MapModelForm


# Simple geo model for testing
class MyModel(models.Model):
    # extra non-geom fields are to test ordering
    koan = models.CharField(max_length=140, blank=True)
    start = models.PointField()
    love = models.CharField(max_length=1, blank=True)
    route = models.LineStringField()
    death = models.BooleanField()
    end = models.PointField(blank=True, null=True)

    objects = models.GeoManager()

#
# form for testing
#

class MyModelForm(MapModelForm):
    class Meta:
        model = MyModel
        maps = (
            (('start', 'end'), {'layers': ['google.streets']}),
            (('route',), None),
        )

# Required=false form
class RequirednessForm(forms.Form):
    optional = MapField(
            fields=[EditableLayerField(required=False, options={
                'geometry': 'point',
                'name': 'optional',
            })],
            options={
                'overlay_style': {'fill_color': '#00ff00'},
            })
    required = MapField(
            fields=[EditableLayerField(required=True, options={
                'geometry': 'point',
                'name': 'required',
            })],
            options={
                'overlay_style': {'fill_color': '#00ff00'},
            })
    unspecified = MapField(
            fields=[EditableLayerField({
                'geometry': 'point',
                'name': 'unspecified',
            })],
            options={
                'overlay_style': {'fill_color': '#00ff00'},
            })

#
# MapModelForm with single set of options.  The two should be equivalent.
#
class SingleStyleMapModelForm(MapModelForm):
    class Meta:
        model = MyModel
        options = {'layers': ['google.streets']}

class SingleStyleMapModelFormEquivalent(MapModelForm):
    class Meta:
        model = MyModel
        maps = ((('start', 'route', 'end'), {'layers': ['google.streets']}),)

class CustomTemplateMapModelForm(MapModelForm):
    class Meta:
        model = MyModel
        template = "olwidget/test_map_template.html"

class MixedTemplateMapModelForm(MapModelForm):
    class Meta:
        model = MyModel
        template = 'olwidget/multi_layer_map.html'
        maps = (
            (('start',), {}, 'olwidget/test_map_template.html'),
            (('end',), {}, 'olwidget/test_map_template.html'),
        )

#
# tests
#

class TestForm(TestCase):
    def test_single_form(self):
        class MySingleForm(forms.Form):
            char = forms.CharField(max_length=10, required=False)
            field = forms.CharField(widget=EditableMap({"name": "Fun times"}))

        form = MySingleForm({'field': 1})
        #print(form)
        self.assertTrue(form.is_bound)
        self.assertTrue(form.is_valid())
        #print(form.media)
        self.assertNotEqual(form.media, '')

        form = MySingleForm({'notafield': 1})
        #print(form)
        self.assertTrue(form.fields['field'].required)
        self.assertTrue(form.is_bound)
        self.assertFalse(form.is_valid())

    def test_multi_form(self):
        class MyMultiForm(forms.Form):
            mymap = MapField((
                EditableLayerField({'name': 'Fun'}),
                InfoLayerField([[Point(0, 0, srid=4326), "that"]]),
                EditableLayerField(),
            ))

        form = MyMultiForm({'mymap_0': "POINT(0 0)", 'mymap_2': "POINT(1 1)"})

        self.assertTrue(form.is_bound)
        self.assertEqual(form.errors, {})
        self.assertTrue(form.is_valid())


        form = MyMultiForm({'mymap_0': 0})
        self.assertTrue(form.is_bound)
        self.assertFalse(form.is_valid())

    def test_info_map(self):
        # Just ensure that no errors arise from construction and rendering
        mymap = InfoMap([[Point(0, 0, srid=4326), "that"]], {"name": "frata"})
        unicode(mymap)
        #print(mymap)

    def test_modelform_empty(self):
        form = MyModelForm()
        unicode(form)

    def test_modelform_valid(self):
        form = MyModelForm({'start': "SRID=4326;POINT(0 0)", 
            'route': "SRID=4326;LINESTRING(0 0,1 1)"})
        self.assertTrue(form.is_bound)
        self.assertTrue(form.is_valid())
        # check order of keys
        self.assertEqual(form.fields.keys(), 
            ['koan', 'start_end', 'love', 'route', 'death']
        )
        form.save()
        #print(form)

    def test_modelform_invalid(self):
        class MyOtherModelForm(MapModelForm):
            class Meta:
                model = MyModel

        form = MyModelForm({'start': 1})
        self.assertTrue(form.is_bound)
        self.assertFalse(form.is_valid())

        form = MyOtherModelForm()
        #print(form)
        unicode(form)

    def test_modelform_initial(self):
        form = MyModelForm(instance=MyModel.objects.create(start="SRID=4326;POINT(0 0)", route="SRID=4326;LINESTRING(0 0,1 1)"))
        unicode(form)

    def test_info_modelform(self):
        class MyInfoModelForm(MapModelForm):
            start = MapField([
                EditableLayerField({'name': 'start'}),
                InfoLayerField([[Point(0, 0, srid=4326), "Of interest"]]),
            ])
            class Meta:
                model = MyModel

        instance = MyModel.objects.create(start="SRID=4326;POINT(0 0)",
                route="SRID=4326;LINESTRING(0 0,1 1)")
        form = MyInfoModelForm({
                'start': "SRID=4326;POINT(0 0)",
                'route': "SRID=4326;LINESTRING(0 0,1 1)",
                'death': False,
            }, instance=instance)
        self.assertEqual(form.fields.keys(),
            ['koan', 'start', 'love', 'route', 'death', 'end'])
        self.assertEquals(form.errors, {})
        form.save()

    def test_custom_form(self):
        class MixedForm(forms.Form):
            stuff = MapField([
                InfoLayerField([["SRID=4326;POINT(0 0)", "Origin"]]),
                EditableLayerField({'geometry': 'point'}),
            ])
        unicode(MixedForm())

    def test_has_changed(self):
        vals = {
                'start': "SRID=4326;POINT(0 0)",
                'route': "SRID=4326;LINESTRING(0 0,1 1)",
        }
        instance = MyModel.objects.create(**vals)
        form = MyModelForm(vals, instance=instance)
        self.assertFalse(form.has_changed())
        
        form = MyModelForm({
            'start': "SRID=4326;POINT(0 0.1)",
            'route': "SRID=4326;LINESTRING(0 0,1 1)",
        }, instance=instance)
        self.assertTrue(form.has_changed())

    def test_single_style_option_form(self):
        f1 = SingleStyleMapModelForm()
        f2 = SingleStyleMapModelFormEquivalent()

        self.assertEquals(unicode(f1.media), unicode(f2.media))
        self.assertEquals(unicode(f1), unicode(f2))

    def test_required(self):
        form = RequirednessForm({
            'optional': None,
            'required': None,
            'unspecified': None,
        })
        #print form.fields['optional'].required
        self.assertFalse(form.is_valid())

        form = RequirednessForm({
            'optional': None,
            'required': "SRID=4326;POINT(0 0)",
            'unspecified': "SRID=4326;POINT(0 0)",
        })
        self.assertTrue(form.is_valid())

    def test_custom_template_map_model_form(self):
        form = CustomTemplateMapModelForm()
        for field in ('start', 'route', 'end'):
            self.assertEquals(unicode(form[field]), u'<h1>Boogah!</h1>\n')

    def test_mixed_template_map_model_form(self):
        form = MixedTemplateMapModelForm()
        for field in ('start', 'end'):
            self.assertEquals(unicode(form[field]), u'<h1>Boogah!</h1>\n')
        self.assertNotEquals(unicode(form['route']), u'<h1>Boogah!</h1>\n')


########NEW FILE########
__FILENAME__ = utils
import re

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry

DEFAULT_PROJ = "4326"
DEFAULT_OPTIONS = getattr(settings, 'OLWIDGET_DEFAULT_OPTIONS', {})

def get_options(o):
    options = DEFAULT_OPTIONS.copy()
    options.update(o or {})
    return options

def get_custom_layer_types():
    return getattr(settings, 'OLWIDGET_CUSTOM_LAYER_TYPES', {})

def url_join(*args):
    return reduce(_reduce_url_parts, args)
    
def _reduce_url_parts(a, b):
    b = b or ""
    if a and a[-1] == "/":
        return a + b
    a = a or ""
    return a + "/" + b

def translate_options(options):
    translated = {}
    for key, value in options.iteritems():
        new_key = _separated_lowercase_to_lower_camelcase(key)
        # recurse
        if isinstance(value, dict):
            translated[new_key] = translate_options(value)
        else:
            translated[new_key] = value
    return translated

def _separated_lowercase_to_lower_camelcase(input_):
    return re.sub('_\w', lambda match: match.group(0)[-1].upper(), input_)


def get_ewkt(value, srid=None):
    if srid is None:
        if hasattr(value, 'srid'):
            srid = value.srid
        else:
            srid = DEFAULT_PROJ
    return _add_srid(_get_wkt(value, srid), srid)

def get_geos(value, srid=DEFAULT_PROJ):
    geos = None
    if value:
        if isinstance(value, GEOSGeometry):
            geos = value
        elif isinstance(value, basestring):
            match = _ewkt_re.match(value)
            if match:
                geos = GEOSGeometry(match.group('wkt'), match.group('srid'))
            else:
                geos = GEOSGeometry(value, srid)
    if geos and geos.srid and int(srid) != geos.srid:
        geos.transform(int(srid))
    return geos

def collection_ewkt(fields, srid=DEFAULT_PROJ):
    return _add_srid(_collection_wkt(fields, srid), srid)

_ewkt_re = re.compile("^SRID=(?P<srid>\d+);(?P<wkt>.+)$", re.I)
def _get_wkt(value, srid):
    """
    `value` is either a WKT string or a geometry field.  Returns WKT in the
    projection for the given SRID.
    """
    geos = get_geos(value, srid)
    wkt = ''
    if geos:
        wkt = geos.wkt 
    return wkt

def _collection_wkt(fields, srid):
    """ Returns WKT for the given list of geometry fields. """

    if not fields:
        return ""

    if len(fields) == 1:
        return _get_wkt(fields[0], srid)

    return "GEOMETRYCOLLECTION(%s)" % \
            ",".join(_get_wkt(field, srid) for field in fields)

def _add_srid(wkt, srid):
    """
    Returns EWKT (WKT with a specified SRID) for the given wkt and SRID
    (default 4326). 
    """
    if wkt:
        return "SRID=%s;%s" % (srid, wkt)
    return ""

def options_for_field(db_field):
    is_collection = db_field.geom_type in ('MULTIPOINT', 'MULTILINESTRING', 
            'MULTIPOLYGON', 'GEOMETRYCOLLECTION', 'GEOMETRY')
    if db_field.geom_type == 'GEOMETRYCOLLECTION':
        geometry = ['polygon', 'point', 'linestring']
    else:
        if db_field.geom_type in ('MULTIPOINT', 'POINT'):
            geometry = 'point'
        elif db_field.geom_type in ('POLYGON', 'MULTIPOLYGON'):
            geometry = 'polygon'
        elif db_field.geom_type in ('LINESTRING', 'MULTILINESTRING'):
            geometry = 'linestring'
        else:
            # fallback: allow all types.
            geometry = ['polygon', 'point', 'linestring']

    return { 'geometry': geometry, 'isCollection': is_collection, }

########NEW FILE########
__FILENAME__ = widgets
import json
import copy

from django.template.loader import render_to_string
from django.conf import settings
from django import forms
from django.utils.safestring import mark_safe

from olwidget import utils

# Default settings for paths and API URLs.  These can all be overridden by
# specifying a value in settings.py

setattr(settings, "OLWIDGET_STATIC_URL",
    getattr(settings,
        "OLWIDGET_STATIC_URL",
        utils.url_join(settings.STATIC_URL, "olwidget")))

api_defaults = {
    'GOOGLE_API_KEY': "",
    'YAHOO_APP_ID': "",
    'CLOUDMADE_API_KEY': "",
    'GOOGLE_API': "//maps.google.com/maps/api/js?v=3&sensor=false",
    'YAHOO_API': "http://api.maps.yahoo.com/ajaxymap?v=3.0",
    'OSM_API': "//openstreetmap.org/openlayers/OpenStreetMap.js",
    'OL_API': "http://openlayers.org/api/2.11/OpenLayers.js",
    'MS_VE_API' : "//ecn.dev.virtualearth.net/mapcontrol/mapcontrol.ashx?v=6.2&s=1",
    'CLOUDMADE_API': utils.url_join(settings.OLWIDGET_STATIC_URL, "js/cloudmade.js"),
    'OLWIDGET_JS': utils.url_join(settings.OLWIDGET_STATIC_URL, "js/olwidget.js"),
    'OLWIDGET_CSS': utils.url_join(settings.OLWIDGET_STATIC_URL, "css/olwidget.css"),
}

for key, default in api_defaults.iteritems():
    if not hasattr(settings, key):
        setattr(settings, key, default)


#
# Map widget
#

class Map(forms.Widget):
    """
    ``Map`` is a container widget for layers.  The constructor takes a list of
    vector layer instances, a dictionary of options for the map, a template
    to customize rendering, and a list of names for the layer fields.
    """

    default_template = 'olwidget/multi_layer_map.html'

    def __init__(self, vector_layers=None, options=None, template=None,
            layer_names=None):
        self.vector_layers = VectorLayerList()
        for layer in vector_layers:
            self.vector_layers.append(layer)
        self.layer_names = layer_names
        self.options = utils.get_options(options)
        # Though this layer is the olwidget.js default, it must be explicitly
        # set so {{ form.media }} knows to include osm.
        self.options['layers'] = self.options.get('layers', ['osm.mapnik'])
        self.custom_layer_types = utils.get_custom_layer_types()
        self.template = template or self.default_template
        super(Map, self).__init__()

    def render(self, name, value, attrs=None):
        if value is None:
            values = [None for i in range(len(self.vector_layers))]
        elif not isinstance(value, (list, tuple)):
            values = [value]
        else:
            values = value
        attrs = attrs or {}
        # Get an arbitrary unique ID if we weren't handed one (e.g. widget used
        # outside of a form).
        map_id = attrs.get('id', "id_%s" % id(self))

        layer_js = []
        layer_html = []
        layer_names = self._get_layer_names(name)
        value_count = 0
        for i, layer in enumerate(self.vector_layers):
            if layer.editable:
                value = values[value_count]
                value_count += 1
            else:
                value = None
            lyr_name = layer_names[i]
            id_ = "%s_%s" % (map_id, lyr_name)
            # Use "prepare" rather than "render" to get both js and html
            (js, html) = layer.prepare(lyr_name, value, attrs={'id': id_ })
            layer_js.append(js)
            layer_html.append(html)

        context = {
            'id': map_id,
            'layer_js': layer_js,
            'layer_html': layer_html,
            'map_opts': json.dumps(utils.translate_options(self.options)),
            'setup_custom_layer_types': self._custom_layer_types_js(),
            'STATIC_URL': settings.STATIC_URL,
        }
        context.update(self.get_extra_context())
        return render_to_string(self.template, context)

    def get_extra_context(self):
        """Hook that subclasses can override to add extra data for use
        by the javascript in self.template. This is invoked by
        self.render().

        Return value should be a dictionary where keys are strings and
        values are valid javascript, eg. JSON-encoded data.  You'll
        also want to override the template to make use of the provided
        data.
        """
        return {}

    def value_from_datadict(self, data, files, name):
        """ Return an array of all layers' values. """
        return [vl.value_from_datadict(data, files, lyr_name) for vl, lyr_name in zip(self.vector_layers, self._get_layer_names(name))]

    def _custom_layer_types_js(self):
        layer_types_js = ""
        for typename in self.custom_layer_types:
            js_def = self.custom_layer_types[typename]
            layer_types_js += "olwidget.%s = {map: function() { return new %s }};" % (typename, js_def)
        return layer_types_js

    def _get_layer_names(self, name):
        """ 
        If the user gave us a layer_names parameter, use that.  Otherwise,
        construct names based on ``name``. 
        """
        n = len(self.vector_layers)
        if self.layer_names and len(self.layer_names) == n:
            return self.layer_names

        singleton = len(self.vector_layers.editable) == 1
        self.layer_names = []
        for i,layer in enumerate(self.vector_layers):
            if singleton and layer.editable:
                self.layer_names.append("%s" % name)
            else:
                self.layer_names.append("%s_%i" % (name, i))
        return self.layer_names

    def _has_changed(self, initial, data):
        if (initial is None) or (not isinstance(initial, (tuple, list))):
            initial = [u''] * len(data)
        for widget, initial, data in zip(self.vector_layers, initial, data):
            if utils.get_geos(initial) != utils.get_geos(data):
                return True
        return False

    def _media(self):
        js = set()
        # collect scripts necessary for various base layers
        for layer in self.options['layers']:
            if layer.startswith("osm."):
                js.add(settings.OSM_API)
            elif layer.startswith("google."):
                GOOGLE_API_URL = settings.GOOGLE_API
                if settings.GOOGLE_API_KEY:
                    GOOGLE_API_URL += "&key=%s" % settings.GOOGLE_API_KEY
                js.add(GOOGLE_API_URL)
            elif layer.startswith("yahoo."):
                js.add(settings.YAHOO_API + "&appid=%s" % settings.YAHOO_APP_ID)
            elif layer.startswith("ve."):
                js.add(settings.MS_VE_API)
            elif layer.startswith("cloudmade."):
                js.add(settings.CLOUDMADE_API + "#" + settings.CLOUDMADE_API_KEY)
        js = [settings.OL_API, settings.OLWIDGET_JS] + list(js)
        return forms.Media(css={'all': (settings.OLWIDGET_CSS,)}, js=js)
    media = property(_media)

    def __unicode__(self):
        return self.render(None, None)

    def __deepcopy__(self, memo):
        obj = super(Map, self).__deepcopy__(memo)
        obj.vector_layers = copy.deepcopy(self.vector_layers)
        return obj

class VectorLayerList(list):
    def __init__(self, *args, **kwargs):
        super(VectorLayerList, self).__init__(*args, **kwargs)
        self.editable = []

    def append(self, obj):
        super(VectorLayerList, self).append(obj)
        if getattr(obj, "editable", False):
            self.editable.append(obj)

    def remove(self, obj):
        super(VectorLayerList, self).remove(obj)
        if getattr(obj, "editable", False):
            self.editable.remove(obj)

    def __deepcopy__(self, memo):
        obj = VectorLayerList()
        for thing in self:
            obj.append(copy.deepcopy(thing))
        return obj

#
# Layer widgets
#

class BaseVectorLayer(forms.Widget):
    editable = False
    def prepare(self, name, value, attrs=None):
        """
        Given the name, value and attrs, prepare both html and javascript
        components to handle this layer.  Should return (javascript, html)
        tuple.
        """
        raise NotImplementedError

    def render(self, name, value, attrs=None):
        """
        Return just the javascript component of this widget.  To also get the
        HTML component, call ``prepare``.
        """
        (javascript, html) = self.prepare(name, value, attrs)
        return javascript

    def get_extra_context(self):
        """Hook that subclasses can override to add extra data for use
        by the javascript in self.template. This should be invoked by
        self.prepare().

        Note that the base class itself doesn't invoke this, but
        subclasses which render templates typically do.  You'll also
        want to override relevant templates to make use of the
        provided data.
        """
        return {}

    def __unicode__(self):
        return self.render(None, None)

class InfoLayer(BaseVectorLayer):
    """
    A wrapper for the javscript olwidget.InfoLayer() type.  Takes an an array
    [geometry, html] pairs, where the html will be the contents of a popup
    displayed over the geometry, and an optional options dict.  Intended for
    use as a sub-widget for a ``Map`` widget.
    """
    default_template = 'olwidget/info_layer.html'

    def __init__(self, info=None, options=None, template=None):
        self.info = info or []
        self.options = options or {}
        self.template = template or self.default_template
        super(InfoLayer, self).__init__()

    def prepare(self, name, value, attrs=None):
        wkt_array = []
        for geom, attr in self.info:
            wkt = utils.get_ewkt(geom)
            if isinstance(attr, dict):
                wkt_array.append([wkt, utils.translate_options(attr)])
            else:
                wkt_array.append([wkt, attr])
        info_json = json.dumps(wkt_array)

        if name and not self.options.has_key('name'):
            self.options['name'] = forms.forms.pretty_name(name)

        context = {
            'info_array': info_json,
            'options': json.dumps(utils.translate_options(self.options)),
            'STATIC_URL': settings.STATIC_URL,
        }
        context.update(self.get_extra_context())
        js = mark_safe(render_to_string(self.template, context))
        html = ""
        return (js, html)

class EditableLayer(BaseVectorLayer):
    """
    A wrapper for the javascript olwidget.EditableLayer() type.  Intended for
    use as a sub-widget for the Map widget.
    """
    default_template = "olwidget/editable_layer.html"
    editable = True

    def __init__(self, options=None, template=None):
        self.options = options or {}
        self.template = template or self.default_template
        super(EditableLayer, self).__init__()

    def prepare(self, name, value, attrs=None):
        if not attrs:
            attrs = {}
        if name and not self.options.has_key('name'):
            self.options['name'] = forms.forms.pretty_name(name)
        attrs['id'] = attrs.get('id', "id_%s" % id(self))

        wkt = utils.get_ewkt(value)
        context = {
            'id': attrs['id'],
            'options': json.dumps(utils.translate_options(self.options)),
            'STATIC_URL': settings.STATIC_URL,
        }
        context.update(self.get_extra_context())
        js = mark_safe(render_to_string(self.template, context))
        html = mark_safe(forms.Textarea().render(name, wkt, attrs))
        return (js, html)

#
# Convenience single layer widgets for use in non-MapField fields.
#

class BaseSingleLayerMap(Map):
    """
    Base type for single-layer maps, for convenience and backwards
    compatibility.
    """
    def value_from_datadict(self, data, files, name):
        val = super(BaseSingleLayerMap, self).value_from_datadict(
                data, files, name)
        return val[0]

class EditableMap(BaseSingleLayerMap):
    """
    Convenience Map widget with a single editable layer.  Usage:

        forms.CharField(widget=EditableMap(options={}))

    """
    def __init__(self, options=None, **kwargs):
        super(EditableMap, self).__init__([EditableLayer()], options, **kwargs)
        
class InfoMap(BaseSingleLayerMap):
    """
    Convenience Map widget with a single info layer.
    """
    def __init__(self, info, options=None, **kwargs):
        super(InfoMap, self).__init__([InfoLayer(info)], options, **kwargs)

class MapDisplay(EditableMap):
    """
    Convenience Map widget for a single non-editable layer, with no popups.
    """
    def __init__(self, fields=None, options=None, **kwargs):
        options = utils.get_options(options)
        options['editable'] = False
        super(MapDisplay, self).__init__(options, **kwargs)
        if fields:
            self.wkt = utils.collection_ewkt(fields)
        else:
            self.wkt = ""

    def __unicode__(self):
        return self.render(None, [self.wkt])


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
# Django settings for test_project project.

import os
SETTINGS_ROOT = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG
POSTGIS_TEMPLATE = "template_postgis"

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'olwidget_dev',
        'USER': 'django_dev',
        'PASSWORD': 'django_dev',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(SETTINGS_ROOT, "media/")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'
STATIC_URL = MEDIA_URL

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'j2i1*i)uh*-&cdn^+0*i3^cw9gx-^jrc2&yfn!o-xy)$ij154j'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'test_project.urls'

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
    'django.contrib.admin',
    'django.contrib.gis',

    'testolwidget',
    'olwidget'
)

GOOGLE_API_KEY = "ABQIAAAARaukg-vCnyMKCmf7W1mdOhQCULP4XOMyhPd8d_NrQQEO8sT8XBTLlWMmpTlKIHpKhd2GXLaZc6gHJA" # localhost:8000
#GOOGLE_API_KEY = "ABQIAAAARaukg-vCnyMKCmf7W1mdOhTUM1TfCWCpQbByeYgbUi08Ugq4ShQ2qaNvdgbJz36kf2mKYgbUTR6R7A" # 18.85.23.189:8000
YAHOO_APP_ID = "JNrvOMXV34Ft.LUs2zzCI9yVPrIX1KDJ1tiNHFam9mLWl64qgtbSjenTP.ua1UWbPCbp0w6r.A--" # olwidget documentation

OLWIDGET_DEFAULT_OPTIONS = {
    'layers': ['osm.mapnik'],
}

########NEW FILE########
__FILENAME__ = admin
from django import forms
from django.contrib import admin
from olwidget.admin import GeoModelAdmin

from testolwidget.models import Country, EnergyVortex, AlienActivity, Tree, Nullable, GoogProjModel

# Default map
#admin.site.register(Country, GeoModelAdmin)
from django import forms
from olwidget.fields import MapField, EditableLayerField, InfoLayerField

class TestAdminForm(forms.ModelForm):
    boundary = MapField([
        EditableLayerField({'geometry': 'polygon', 'name': 'boundary', 'is_collection': True}),
        InfoLayerField([["SRID=4326;POINT (0 0)", "Of Interest"]], {"name": "Test"}),
    ], { 'overlay_style': { 'fill_color': '#00ff00' }}, 
    template="olwidget/admin_olwidget.html")

    def clean(self):
        self.cleaned_data['boundary'] = self.cleaned_data['boundary'][0]
        return self.cleaned_data

    class Meta:
        model = Country

class CountryAdmin(GeoModelAdmin):
    form = TestAdminForm

admin.site.register(Country, CountryAdmin)


# Custom multi-layer map with a few options.
class EnergyVortexAdmin(GeoModelAdmin):
    options = {
        'layers': ['osm.osmarender', 'osm.mapnik', 'yahoo.map'],
        'overlay_style': {
            'fill_color': '#ff9c00',
            'stroke_color': '#ff9c00',
            'fill_opacity': 0.7,
            'stroke_width': 4,
         },
         'default_lon': -111.7578,
         'default_lat': 34.87,
         'default_zoom': 15,
         'hide_textarea': False,
    }
    maps = (
        (('nexus', 'lines_of_force'), None),
    )
admin.site.register(EnergyVortex, EnergyVortexAdmin)

# Cluster changelist map
class TreeAdmin(GeoModelAdmin):
    list_map_options = {
        'cluster': True,
        'cluster_display': 'list',
        'map_div_style': { 'width': '300px', 'height': '200px', },
        'default_zoom': 15,
    }
    list_map = ['location']
    maps = (
        (('location', 'root_spread'), {
            'default_lon': -71.08717,
            'default_lat': 42.36088,
            'default_zoom': 18,
        }),
    )
admin.site.register(Tree, TreeAdmin)

# Mixing default options and per-map options, also using changelist map
class AlienActivityAdmin(GeoModelAdmin):
    options = {
        'default_lon': -104.5185,
        'default_lat': 33.3944,
        'default_zoom': 12,
    }
    maps = (
        (('landings',), { 
            'overlay_style': { 
                'fill_color': '#00ff00',
                'stroke_color': '#00ff00',
            },
        }),
        (('strange_lights', 'chemtrails'), { 
            'overlay_style': {
                'fill_color': '#ffffff',
                'stroke_color': '#ccffcc',
                'stroke_width': 4,
            },
            'layers': ['osm.mapnik'],
        }),
    )
    list_map_options = {
        'cluster': True,
        'cluster_display': 'list',
        'map_div_style': { 'width': '300px', 'height': '200px' },
    }
    list_map = ['landings']
admin.site.register(AlienActivity, AlienActivityAdmin)

class NullableAdmin(GeoModelAdmin):
    list_map_options = {
        'cluster': True,
        'cluster_display': 'list',
        'map_div_style': { 'width': '300px', 'height': '200px' },
    }
    list_map = ['location']
admin.site.register(Nullable, NullableAdmin)

class GoogProjAdmin(GeoModelAdmin):
    options = {
        'map_options': {
            'projection': 'EPSG:900913',
            'display_projection': 'EPSG:900913',
        },
        'hide_textarea': False,
    }
admin.site.register(GoogProjModel, GoogProjAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.conf import settings

from olwidget.forms import MapModelForm
from olwidget.fields import MapField, EditableLayerField, InfoLayerField

from testolwidget.models import Tree, Country

class AlienActivityForm(forms.Form):
    """ Example of olwidget in a custom form. """
    incident_name = forms.CharField()
    # Old style single field invocation
    landings = MapField([EditableLayerField({
            'geometry': 'point',
            'is_collection': True,
            'overlay_style': {
                'external_graphic': settings.MEDIA_URL+"alien.png",
                'graphic_width': 21,
                'graphic_height': 25,
            },
            'name': 'Landings',
        })])
    # Define a map to edit two geometry fields
    other_stuff = MapField([
            EditableLayerField({'geometry': ['point', 'linestring', 'polygon'],
                'is_collection': True, 'name': "Strange lights",
                'overlay_style': {
                    'fill_color': '#FFFF00',
                    'stroke_color': '#FFFF00',
                    'stroke_width': 6,
                }
            }),
            EditableLayerField({'geometry': 'linestring',
                'is_collection': True, 'name': "Chemtrails",
                'overlay_style': {
                    'fill_color': '#ffffff',
                    'stroke_color': '#ffffff',
                    'stroke_width': 6,
                },
            }),
        ])

class CustomTreeForm(MapModelForm):
    # set options for individual geometry fields by explicitly declaring the
    # field type.  If not declared, defaults will be used.
    location = EditableLayerField({
        'overlay_style': {
            'stroke_color': '#ffff00',
        }})
    class Meta:
        model = Tree
        # Define a single map to edit two geometry fields, with options.
        maps = (
            (('root_spread', 'location'), {
                'layers': ['google.streets', 'osm.mapnik'],
                'overlay_style': {
                    'fill_color': 'brown',
                    'fill_opacity': 0.2,
                    'stroke_color': 'green',
                }
            }),
        )

class DefaultTreeForm(MapModelForm):
    class Meta:
        model = Tree

class MixedForm(forms.Form):
    capitals = MapField([
        InfoLayerField([[c.boundary, c.about] for c in Country.objects.all()],
            {
                'overlay_style': {
                    'fill_opacity': 0,
                    'stroke_color': "white",
                    'stroke_width': 6,
                }, 
                'name': "Country boundaries",
            }),
        EditableLayerField({
            'geometry': 'point',
            'name': "Country capitals",
            'is_collection': True,
        }),
        ], {'layers': ['google.satellite']})

########NEW FILE########
__FILENAME__ = models
from django.contrib.gis.db import models

class Country(models.Model):
    name = models.CharField(max_length=255)
    boundary = models.MultiPolygonField()
    about = models.TextField()

    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = u"Countries"

class EnergyVortex(models.Model):
    name = models.CharField(max_length=255)
    nexus = models.PointField()
    lines_of_force = models.MultiLineStringField()

    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = u"Energy vortices"

class AlienActivity(models.Model):
    incident_name = models.CharField(max_length=255)
    landings = models.MultiPointField()
    strange_lights = models.GeometryCollectionField()
    chemtrails = models.MultiLineStringField()

    objects = models.GeoManager()

    class Meta:
        verbose_name_plural = u"Alien activities"

    def __unicode__(self):
        return self.incident_name

class Tree(models.Model):
    location = models.PointField()
    root_spread = models.PolygonField()
    species = models.CharField(max_length=255)

    objects = models.GeoManager()

    def __unicode__(self):
        return self.species

class Nullable(models.Model):
    location = models.PointField(null=True, blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return str(self.location)

class GoogProjModel(models.Model):
    point = models.PointField(srid='900913')
    objects = models.GeoManager()



########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.gis.geos import GEOSGeometry

from testolwidget.models import GoogProjModel

class TestGoogProjAdmin(TestCase):
    def setUp(self):
        u = User.objects.create(username='admin', is_superuser=True, is_staff=True)
        u.set_password('admin')
        u.save()

    def test_edit(self):
        c = self.client
        self.assertTrue(c.login(username='admin', password='admin'))
        r = c.post('/admin/testolwidget/googprojmodel/add/', {
            "point": 'SRID=900913;POINT(10 10)'
        }, follow=True)
        self.assertEquals(r.status_code, 200)

        self.assertEquals(len(GoogProjModel.objects.all()), 1)
        a = GEOSGeometry("SRID=900913;POINT(10 10)")
        b = GoogProjModel.objects.all()[0].point
        # Floating point comparison -- ensure distance is miniscule.
        self.assertTrue(a.distance(b) < 1.0e-9)


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

def build_pattern(name, action="show"):
    return url("^%s/(?P<object_id>\d+)/%s$" % (name, action),
            "%s_%s" % (action, name),
            name="%s_%s" % (action, name))

urlpatterns = patterns('testolwidget.views',
    build_pattern("alienactivity", "show"),
    build_pattern("alienactivity", "edit"),
    build_pattern("tree", "show"),
    build_pattern("tree", "edit"),
    build_pattern("tree_custom", "edit"),
    url("^capitals/edit$", "edit_capitals", name="edit_capitals"),
    url("^countries$", "show_countries", name="show_countries"),
    url("^$", "index", name="index"),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.conf import settings

from olwidget.widgets import Map, EditableLayer, InfoLayer, InfoMap

from testolwidget.models import *
from testolwidget.forms import AlienActivityForm, CustomTreeForm, \
        DefaultTreeForm, MixedForm

def edit_alienactivity(request, object_id):
    obj = get_object_or_404(AlienActivity, id=object_id)
    form = AlienActivityForm(request.POST or None, initial={
        'incident_name': obj.incident_name,
        'landings': obj.landings,
        'other_stuff': [obj.strange_lights, obj.chemtrails],
    })
    if form.is_valid():
        try:
            obj.landings = form.cleaned_data['landings'][0]
            obj.strange_lights = form.cleaned_data['other_stuff'][0]
            obj.chemtrails = form.cleaned_data['other_stuff'][1]
            obj.incident_name = form.cleaned_data['incident_name']
            obj.save()
            return HttpResponseRedirect(
                    reverse("show_alienactivity", args=[obj.id]))
        except ValueError:
            raise
    return render_to_response("testolwidget/edit_obj.html", {
        'obj': obj, 'form': form,
    }, context_instance=RequestContext(request))


def show_alienactivity(request, object_id):
    obj = get_object_or_404(AlienActivity, id=object_id)
    return render_to_response("testolwidget/show_obj.html", {
        'obj': obj, 'map': Map([
                InfoLayer([[obj.landings, 
                    "%s landings" % obj.incident_name]], {
                        'overlay_style': {
                            'external_graphic': settings.MEDIA_URL+"alien.png",
                            'graphic_width': 21,
                            'graphic_height': 25,
                            'fill_color': '#00FF00',
                            'stroke_color': '#008800',
                        }, 'name': "Landings"
                    }),
                InfoLayer([[obj.strange_lights, 
                    "%s strange lights" % obj.incident_name]], {
                        'overlay_style': {
                            'fill_color': '#FFFF00',
                            'stroke_color': '#FFFF00',
                            'stroke_width': 6,
                        }, 'name': "Strange lights",
                    }),
                InfoLayer([[obj.chemtrails, 
                    "%s chemtrails" % obj.incident_name]], {
                        'overlay_style': {
                            'fill_color': '#ffffff',
                            'stroke_color': '#ffffff',
                            'stroke_width': 6,
                        }, 'name': "Chemtrails",
                    })
            ], {'layers': ['osm.mapnik', 'google.physical']}),
        'edit_link': reverse("edit_alienactivity", args=[obj.id])
    }, context_instance=RequestContext(request))

def edit_tree(request, object_id):
    return do_edit_tree(request, object_id, DefaultTreeForm)

def edit_tree_custom(request, object_id):
    return do_edit_tree(request, object_id, CustomTreeForm)

def do_edit_tree(request, object_id, Form):
    obj = get_object_or_404(Tree, id=object_id)
    form = Form(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse("show_tree", args=[obj.id]))
    return render_to_response("testolwidget/edit_obj.html", {
            'obj': obj, 'form': form,
        }, context_instance=RequestContext(request))

def show_tree(request, object_id):
    obj = get_object_or_404(Tree, id=object_id)
    # Use the convenience 1-layer map type
    map_ = InfoMap([
            [obj.root_spread, "Root spread"],
            [obj.location, "Trunk center"],
        ])
    return render_to_response("testolwidget/show_obj.html", {
            'obj': obj, 'map': map_, 
            'edit_link': reverse("edit_tree", args=[obj.id]),
        }, context_instance=RequestContext(request))

def edit_capitals(request):
    return render_to_response("testolwidget/edit_obj.html", {
        'obj': "Capitals",
        'form': MixedForm(),
    }, context_instance=RequestContext(request))


def show_countries(request):
    info = []
    colors = ["red", "green", "blue", "peach"]
    for i,country in enumerate(Country.objects.all()):
        info.append((country.boundary, {
            'html': country.about,
            'style': {
                # TODO: 4-color map algorithm.  Just kidding.
                'fill_color': colors[i]
            },
        }))
    map_ = InfoMap(info)
    return render_to_response("testolwidget/show_obj.html", {
        'obj': "Countries", "map": map_, 
        "edit_link": "/admin/testolwidget/country/",
    }, context_instance=RequestContext(request))

def index(request):
    return render_to_response("testolwidget/index.html", {
            'map': Map([ 
                EditableLayer({
                    'geometry': ['point', 'linestring', 'polygon'],
                    'is_collection': True,
                }),
            ], {
                'default_lat': 42.360836996182,
                'default_lon': -71.087611985694,
                'default_zoom': 10,
                'layers': ['osm.mapnik', 'google.physical'],
            }), 
        }, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
     (r'^admin/', include(admin.site.urls)),
     (r'', include('testolwidget.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
            (r'^%s/(?P<path>.*)$' % settings.MEDIA_URL[1:-1],
                'django.views.static.serve',
                {'document_root': settings.MEDIA_ROOT}),
    )


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# olwidget documentation build configuration file, created by
# sphinx-quickstart on Sun Jan 22 12:34:30 2012.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'olwidget'
copyright = u'2012, Charlie DeTar'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.4'
# The full version, including alpha/beta/rc tags.
release = '0.48'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'mynature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['.']

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
html_static_path = ['_static']

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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'olwidgetdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'olwidget.tex', u'olwidget Documentation',
   u'Charlie DeTar', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'olwidget', u'olwidget Documentation',
     [u'Charlie DeTar'], 1)
]

########NEW FILE########
