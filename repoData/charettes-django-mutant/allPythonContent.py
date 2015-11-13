__FILENAME__ = models
from __future__ import unicode_literals

from django.db.models import fields
from django.utils.translation import ugettext_lazy as _

from ...models.field import FieldDefinition


class _BooleanMeta:
    defined_field_category = _('Boolean')


class BooleanFieldDefinition(FieldDefinition):
    class Meta(_BooleanMeta):
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.BooleanField


class NullBooleanFieldDefinition(FieldDefinition):
    class Meta(_BooleanMeta):
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.NullBooleanField

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals

import sys
# TODO: Remove when support for Python 2.6 is dropped
if sys.version_info >= (2, 7):
    from unittest import skipIf
else:
    from django.utils.unittest import skipIf

from django.db import connection
from django.utils.translation import ugettext_lazy as _
import south

from mutant.test.testcases import FieldDefinitionTestMixin
from mutant.tests.utils import BaseModelDefinitionTestCase

from .models import BooleanFieldDefinition, NullBooleanFieldDefinition


class BooleanFieldDefinitionTestMixin(FieldDefinitionTestMixin):
    field_definition_category = _('Boolean')

    @skipIf(
        connection.settings_dict['ENGINE'] == 'django.db.backends.sqlite3' and
        south.__version__ in ('0.8.1', '0.8.2', '0.8.3', '0.8.4'),
        "This version of South doesn't escape added column default value correctly on SQLite3."
    )
    def test_create_with_default(self):
        super(BooleanFieldDefinitionTestMixin, self).test_create_with_default()


class BooleanFieldDefinitionTest(BooleanFieldDefinitionTestMixin,
                                 BaseModelDefinitionTestCase):
    field_definition_cls = BooleanFieldDefinition
    field_definition_init_kwargs = {'default': True}
    field_values = (False, True)


class NullBooleanFieldDefinitionTest(BooleanFieldDefinitionTestMixin,
                                     BaseModelDefinitionTestCase):
    field_definition_cls = NullBooleanFieldDefinition
    field_values = (True, None)

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.db.models import fields
from django.utils.translation import ugettext_lazy as _

from ...db.fields.python import DirectoryPathField, RegExpStringField
from ...models.field.managers import FieldDefinitionManager

from ..text.models import CharFieldDefinition


path_help_text = _('The absolute filesystem path to a directory from which '
                   'this field should get its choices.')
match_help_text = _('A regular expression used to filter filenames.')
recursive_help_text = _('Specifies whether all subdirectories of '
                        'path should be included')

class FilePathFieldDefinition(CharFieldDefinition):
    path = DirectoryPathField(_('path'), max_length=100,
                              help_text=path_help_text)
    match = RegExpStringField(_('match'), max_length=100,
                              blank=True, null=True, help_text=match_help_text)
    recursive = fields.BooleanField(_('recursive'), default=False,
                                    help_text=recursive_help_text)

    objects = FieldDefinitionManager()

    class Meta:
        app_label = 'mutant'
        defined_field_class = fields.FilePathField
        defined_field_options = ('path', 'match', 'recursive')
        defined_field_category = _('File')

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals

import os
import sys

from django.utils.translation import ugettext_lazy as _

from mutant.test import testcases
from mutant.tests.utils import BaseModelDefinitionTestCase

from . import models


PACKAGE_PATH = os.path.dirname(sys.modules[__name__].__file__)
MODULE_PATH = os.path.abspath(sys.modules[__name__].__file__)
MODELS_MODULE_PATH = os.path.abspath(models.__file__)


class FilePathFieldDefinitionTest(testcases.FieldDefinitionTestMixin,
                                  BaseModelDefinitionTestCase):
    field_definition_category = _('File')
    field_definition_cls = models.FilePathFieldDefinition
    field_definition_init_kwargs = {'path': PACKAGE_PATH}
    field_values = (MODULE_PATH, MODELS_MODULE_PATH)

    def test_formfield(self):
        self.field.match = r'\.pyc?$'
        self.field.save()
        formfield = self.field.construct().formfield()
        self.assertTrue(formfield.valid_value(MODULE_PATH))
        invalid_path = os.path.abspath(testcases.__file__)
        self.assertFalse(formfield.valid_value(invalid_path))

########NEW FILE########
__FILENAME__ = field
from __future__ import unicode_literals

from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _

from mutant.models import FieldDefinition, FieldDefinitionManager


srid_help_text = _('Spatial Reference System Identity')
spatial_index_help_text = _('Creates a spatial index for the given '
                            'geometry field.')
dim_help_text = _('Coordinate dimension.')
geography_help_text = _('Creates a database column of type geography, '
                        'rather than geometry.')


class GeometryFieldDefinition(FieldDefinition):
    DIM_2D = 2
    DIM_3D = 3
    DIM_CHOICES = (
        (DIM_2D, _('Two-dimensional')),
        (DIM_3D, _('Three-dimensional')),
    )

    srid = models.IntegerField(_('SRID'), default=4326,
                               help_text=srid_help_text)
    spatial_index = models.BooleanField(_('spatial index'), default=True,
                                        help_text=spatial_index_help_text)
    dim = models.PositiveSmallIntegerField(_('coordinate dimension'),
                                           choices=DIM_CHOICES, default=2,
                                           help_text=dim_help_text)
    geography = models.BooleanField(_('geography'), default=False,
                                    help_text=geography_help_text)

    objects = FieldDefinitionManager()

    class Meta:
        app_label = 'mutant'
        defined_field_options = ('srid', 'spatial_index', 'dim', 'geography')
        defined_field_category = _('Geometry')
        defined_field_class = models.GeometryField


class PointFieldDefinition(GeometryFieldDefinition):
    class Meta:
        app_label = 'mutant'
        proxy = True
        defined_field_class = models.PointField


class LineStringFieldDefinition(GeometryFieldDefinition):
    class Meta:
        app_label = 'mutant'
        proxy = True
        defined_field_class = models.LineStringField


class PolygonFieldDefinition(GeometryFieldDefinition):
    class Meta:
        app_label = 'mutant'
        proxy = True
        defined_field_class = models.PolygonField


class MultiPointFieldDefinition(GeometryFieldDefinition):
    class Meta:
        app_label = 'mutant'
        proxy = True
        defined_field_class = models.MultiPointField


class MultiLineStringFieldDefinition(GeometryFieldDefinition):
    class Meta:
        app_label = 'mutant'
        proxy = True
        defined_field_class = models.MultiLineStringField


class MultiPolygonFieldDefinition(GeometryFieldDefinition):
    class Meta:
        app_label = 'mutant'
        proxy = True
        defined_field_class = models.MultiPolygonField


class GeometryCollectionFieldDefinition(GeometryFieldDefinition):
    class Meta:
        app_label = 'mutant'
        proxy = True
        defined_field_class = models.GeometryCollectionField

########NEW FILE########
__FILENAME__ = model
from __future__ import unicode_literals

from django.contrib.gis.db import models


class GeoModel(models.Model):
    """
    A model to be used as a BaseDefinition on ModelDefinition instance with
    GeometryFieldDefinition instances.
    """
    objects = models.GeoManager()

    class Meta:
        abstract = True

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals

import sys
# TODO: Remove when support for Python 2.6 is dropped
if sys.version_info >= (2, 7):
    from unittest import expectedFailure
else:
    from django.utils.unittest import expectedFailure

from django.contrib.gis.geos import (GeometryCollection, LineString, Point,
    Polygon, MultiLineString, MultiPoint, MultiPolygon)
from django.utils.translation import ugettext_lazy as _

from mutant.models import BaseDefinition
from mutant.test.testcases import FieldDefinitionTestMixin
from mutant.tests.utils import BaseModelDefinitionTestCase

from .models import (GeoModel, GeometryFieldDefinition,
    GeometryCollectionFieldDefinition, LineStringFieldDefinition,
    PointFieldDefinition, PolygonFieldDefinition,
    MultiLineStringFieldDefinition, MultiPointFieldDefinition,
    MultiPolygonFieldDefinition)


class GeometryFieldDefinitionTestMixin(FieldDefinitionTestMixin):
    field_definition_category = _('Geometry')

    def setUp(self):
        super(GeometryFieldDefinitionTestMixin, self).setUp()
        BaseDefinition.objects.create(model_def=self.model_def, base=GeoModel)


class GeometryFieldDefinitionTest(GeometryFieldDefinitionTestMixin,
                                  BaseModelDefinitionTestCase):
    field_definition_cls = GeometryFieldDefinition
    field_values = (
        LineString((1, 2), (3, 4), (5, 6), (7, 8), (9, 10)),
        Polygon(
            ((0.0, 0.0), (18, 50.0), (47.0, 55.0), (50.0, 0.0), (0.0, 0.0))
        )
    )


class PointFieldDefinitionTest(GeometryFieldDefinitionTestMixin,
                               BaseModelDefinitionTestCase):
    field_definition_cls = PointFieldDefinition
    field_values = (Point(5, 23), Point(13, 37))


class LineStringFieldDefinitionTest(GeometryFieldDefinitionTestMixin,
                                    BaseModelDefinitionTestCase):
    field_definition_cls = LineStringFieldDefinition
    field_values = (
        LineString((0, 0), (0, 50), (50, 50), (50, 0), (0, 0)),
        LineString((1, 2), (3, 4), (5, 6), (7, 8), (9, 10))
    )


class PolygonFieldDefinitionTest(GeometryFieldDefinitionTestMixin,
                                 BaseModelDefinitionTestCase):
    field_definition_cls = PolygonFieldDefinition
    field_values = (
        Polygon(
            ((0.0, 0.0), (0.0, 50.0), (50.0, 50.0), (50.0, 0.0), (0.0, 0.0))
        ),
        Polygon(
            ((0.0, 0.0), (18, 50.0), (47.0, 55.0), (50.0, 0.0), (0.0, 0.0))
        ),
    )


class MultiLineStringFieldDefinitionTest(GeometryFieldDefinitionTestMixin,
                                         BaseModelDefinitionTestCase):
    field_definition_cls = MultiLineStringFieldDefinition
    field_values = (
        MultiLineString(
            LineString((0, 0), (0, 50), (50, 50), (50, 0), (0, 0)),
            LineString((1, 2), (3, 4), (5, 6), (7, 8), (9, 10)),
        ),
        MultiLineString(
            LineString((13, 7), (18, 50), (50, 50), (50, 27), (110, 0)),
            LineString((1, 2), (3, 4), (5, 6), (7, 8), (9, 10)),
            LineString((0, 0), (0, 50), (50, 50), (50, 0), (0, 0)),
        ),
    )


class MultiPointFieldDefinitionTest(GeometryFieldDefinitionTestMixin,
                                    BaseModelDefinitionTestCase):
    field_definition_cls = MultiPointFieldDefinition
    field_values = (
        MultiPoint(Point(0, 0), Point(1, 1)),
        MultiPoint(Point(5, 23), Point(13, 37), Point(13, 58)),
    )


class MultiPolygonFieldDefinitionTest(GeometryFieldDefinitionTestMixin,
                                      BaseModelDefinitionTestCase):
    field_definition_cls = MultiPolygonFieldDefinition
    field_values = (
        MultiPolygon(
            Polygon(
                ((0.0, 0.0), (0.0, 50.0), (50.0, 50.0), (50.0, 0.0), (0.0, 0.0))
            ),
            Polygon(
                ((0.0, 0.0), (18, 50.0), (47.0, 55.0), (50.0, 0.0), (0.0, 0.0))
            ),
        ),
        MultiPolygon(
            Polygon(
                ((0.0, 0.0), (0.0, 50.0), (50.0, 50.0), (50.0, 0.0), (0.0, 0.0))
            ),
            Polygon(
                ((0.0, 0.0), (18, 50.0), (47.0, 55.0), (50.0, 0.0), (0.0, 0.0))
            ),
            Polygon(
                ((0.0, 0.0), (0.0, 50.0), (50.0, 51.0), (50.0, 45), (0.0, 0.0))
            ),
        ),
    )


class GeometryCollectionFieldDefinitionTest(GeometryFieldDefinitionTestMixin,
                                            BaseModelDefinitionTestCase):
    field_definition_cls = GeometryCollectionFieldDefinition
    field_values = (
        GeometryCollection(
            Point(0, 0),
            Polygon(
                ((0.0, 0.0), (18, 50.0), (47.0, 55.0), (50.0, 0.0), (0.0, 0.0))
            ),
        ),
        GeometryCollection(
            LineString((1, 2), (3, 4), (5, 6), (7, 8), (9, 10)),
            Polygon(
                ((0.0, 0.0), (18, 50.0), (47.0, 55.0), (50.0, 0.0), (0.0, 0.0))
            ),
            Point(5, 23),
            Point(13, 37),
        ),
    )

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.db.models import fields
from django.utils.translation import ugettext_lazy as _

from ...models.field import FieldDefinition, FieldDefinitionManager


class _NumericMeta:
    defined_field_category = _('Numeric')


class SmallIntegerFieldDefinition(FieldDefinition):
    class Meta(_NumericMeta):
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.SmallIntegerField


class PositiveSmallIntegerFieldDefinition(FieldDefinition):
    class Meta(_NumericMeta):
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.PositiveSmallIntegerField


class IntegerFieldDefinition(FieldDefinition):
    class Meta(_NumericMeta):
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.IntegerField


class PositiveIntegerFieldDefinition(FieldDefinition):
    class Meta(_NumericMeta):
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.PositiveIntegerField


class BigIntegerFieldDefinition(FieldDefinition):
    class Meta(_NumericMeta):
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.BigIntegerField


class FloatFieldDefinition(FieldDefinition):
    class Meta(_NumericMeta):
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.FloatField


max_digits_help_text = _('The maximum number of digits allowed in the number. '
                         'Note that this number must be greater than or equal '
                         'to ``decimal_places``, if it exists.')
decimal_places_help_text = _('The number of decimal places to store '
                             'with the number.')

class DecimalFieldDefinition(FieldDefinition):
    max_digits = fields.PositiveSmallIntegerField(_('max digits'),
                                                  help_text=max_digits_help_text)
    decimal_places = fields.PositiveSmallIntegerField(_('decimal_places'),
                                                      help_text=decimal_places_help_text)

    objects = FieldDefinitionManager()

    class Meta(_NumericMeta):
        app_label = 'mutant'
        defined_field_class = fields.DecimalField
        defined_field_options = ('max_digits', 'decimal_places',)

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals

from decimal import Decimal

from django.utils.translation import ugettext_lazy as _

from mutant.test.testcases import FieldDefinitionTestMixin
from mutant.tests.utils import BaseModelDefinitionTestCase

from .models import (BigIntegerFieldDefinition, DecimalFieldDefinition,
    FloatFieldDefinition, IntegerFieldDefinition,
    PositiveIntegerFieldDefinition, PositiveSmallIntegerFieldDefinition,
    SmallIntegerFieldDefinition)


class NumericFieldDefinitionTestMixin(FieldDefinitionTestMixin):
    field_definition_category = _('Numeric')


class SmallIntegerFieldDefinitionTest(NumericFieldDefinitionTestMixin,
                                      BaseModelDefinitionTestCase):
    field_definition_cls = SmallIntegerFieldDefinition
    field_definition_init_kwargs = {'default': 0}
    field_values = (-134, 245)


class PositiveSmallIntegerFieldDefinitionTest(NumericFieldDefinitionTestMixin,
                                              BaseModelDefinitionTestCase):
    field_definition_cls = PositiveSmallIntegerFieldDefinition
    field_definition_init_kwargs = {'default': 0}
    field_values = (135, 346)


class IntegerFieldDefinitionTest(NumericFieldDefinitionTestMixin,
                                 BaseModelDefinitionTestCase):
    field_definition_cls = IntegerFieldDefinition
    field_definition_init_kwargs = {'default': 0}
    field_values = (44323423, -4223423)


class PositiveIntegerFieldDefinitionTest(NumericFieldDefinitionTestMixin,
                                         BaseModelDefinitionTestCase):
    field_definition_cls = PositiveIntegerFieldDefinition
    field_definition_init_kwargs = {'default': 0}
    field_values = (44323423, 443234234)


class BigIntegerFieldDefinitionTest(NumericFieldDefinitionTestMixin,
                                    BaseModelDefinitionTestCase):
    field_definition_cls = BigIntegerFieldDefinition
    field_definition_init_kwargs = {'default': 0}
    field_values = (443234234324, 443234234998)


class FloatFieldDefinitionTest(NumericFieldDefinitionTestMixin,
                               BaseModelDefinitionTestCase):
    field_definition_cls = FloatFieldDefinition
    field_definition_init_kwargs = {'default': 0}
    field_values = (1234567.84950, 18360935.1854195)


class DecimalFieldDefinitionTest(NumericFieldDefinitionTestMixin,
                                 BaseModelDefinitionTestCase):
    field_definition_cls = DecimalFieldDefinition
    field_definition_init_kwargs = {
        'default': 0,
        'max_digits': 15,
        'decimal_places': 7
    }
    field_values = (
        Decimal('1234567.84950'),
        Decimal('18360935.1854195'),
    )

########NEW FILE########
__FILENAME__ = managers
from __future__ import unicode_literals

from ...managers import FilteredQuerysetManager
from ...models import FieldDefinitionManager


class ForeignKeyDefinitionManager(FilteredQuerysetManager,
                                  FieldDefinitionManager):
    pass

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import deletion, fields
from django.utils.translation import ugettext_lazy as _
from picklefield.fields import PickledObjectField

from ...db.fields import PythonIdentifierField
from ...db.models import MutableModel
from ...models import FieldDefinition, FieldDefinitionManager, ModelDefinition

from .managers import ForeignKeyDefinitionManager


related_name_help_text = _('The name to use for the relation from the '
                           'related object back to this one.')

class RelatedFieldDefinition(FieldDefinition):
    to = fields.related.ForeignKey(ContentType, verbose_name=_('to'),
                                   related_name='+')
    related_name = PythonIdentifierField(_('related name'),
                                         blank=True, null=True,
                                         help_text=related_name_help_text)

    objects = FieldDefinitionManager()

    class Meta:
        app_label = 'mutant'
        abstract = True
        defined_field_options = ('related_name',)
        defined_field_category = _('Related')

    def clone(self):
        clone = super(RelatedFieldDefinition, self).clone()
        clone.to = self.to
        return clone

    @property
    def is_recursive_relationship(self):
        """
        Whether or not `to` points to this field's model definition
        """
        try:
            model_def = self.model_def
        except ModelDefinition.DoesNotExist:
            return False
        else:
            return self.to_id == model_def.contenttype_ptr_id

    @property
    def to_model_class_is_mutable(self):
        to_model_class = self.to.model_class()
        if to_model_class is None:
            try:
                getattr(self.to, 'modeldefinition')
            except ModelDefinition.DoesNotExist:
                return False
            else:
                return True
        else:
            return issubclass(to_model_class, MutableModel)

    @property
    def to_model_class(self):
        if self.to_model_class_is_mutable:
            return self.to.modeldefinition.model_class()
        else:
            return self.to.model_class()

    def clean(self):
        if (None not in (self.related_name, self.to_id) and
            not self.to_model_class_is_mutable):
            msg = _('Cannot assign a related manager to non-mutable model')
            raise ValidationError({'related_name': [msg]})

    def get_field_options(self, **overrides):
        options = super(RelatedFieldDefinition, self).get_field_options(**overrides)
        if self.to_model_class_is_mutable:
            if self.is_recursive_relationship:
                options['to'] = fields.related.RECURSIVE_RELATIONSHIP_CONSTANT
            else:
                model_def = self.to.modeldefinition
                options['to'] = "%s.%s" % (
                    model_def.app_label, model_def.object_name
                )
        else:
            opts = self.to._meta
            options.update(
                to="%s.%s" % (opts.app_label, opts.object_name),
                related_name='+'
            )
        return options

    def _south_ready_field_instance(self):
        """
        South add_column choke when passing 'self' or 'app.Model' to `to` kwarg,
        so we have to create a special version for it.
        """
        cls = self.get_field_class()
        options = self.get_field_options()
        options['to'] = self.to.model_class()
        return cls(**options)

    def save(self, *args, **kwargs):
        save = super(RelatedFieldDefinition, self).save()
        if self.to_model_class_is_mutable:
            self.to_model_class.mark_as_obsolete()
        return save


to_field_help_text = _('The field on the related object that the '
                       'relation is to.')
on_delete_help_text = _('Behavior when an object referenced by this field '
                        'is deleted')


class SET(object):
    def __init__(self, value):
        self.value = value
        self.callable = callable(self.value)

    def __call__(self, collector, field, sub_objs, using):
        value = self.value
        if self.callable:
            value = value()
        collector.add_field_update(field, value, sub_objs)

    def deconstruct(self):
        return ("%s.%s" % (self.__module__, self.__name__), (self.value,), {})

SET_NULL = SET(None)


class ForeignKeyDefinition(RelatedFieldDefinition):
    ON_DELETE_CASCADE = 'CASCADE'
    ON_DELETE_PROTECT = 'PROTECT'
    ON_DELETE_SET_NULL = 'SET_NULL'
    ON_DELETE_SET_DEFAULT = 'SET_DEFAULT'
    ON_DELETE_SET_VALUE = 'SET_VALUE'
    ON_DELETE_DO_NOTHING = 'DO_NOTHING'

    ON_DELETE_CHOICES = (
        (ON_DELETE_CASCADE, _('CASCADE')),
        (ON_DELETE_PROTECT, _('PROTECT')),
        (ON_DELETE_SET_NULL, _('SET_NULL')),
        (ON_DELETE_SET_DEFAULT, _('SET_DEFAULT')),
        (ON_DELETE_SET_VALUE, _('SET(VALUE)')),
        (ON_DELETE_DO_NOTHING, _('DO_NOTHING')),
    )

    to_field = PythonIdentifierField(_('to field'), blank=True, null=True,
                                     help_text=to_field_help_text)
    one_to_one = fields.BooleanField(editable=False, default=False)
    on_delete = fields.CharField(_('on delete'), blank=True, null=True,
                                 max_length=11, choices=ON_DELETE_CHOICES,
                                 default=ON_DELETE_CASCADE,
                                 help_text=on_delete_help_text)
    on_delete_set_value = PickledObjectField(_('on delete set value'), null=True)

    objects = ForeignKeyDefinitionManager(one_to_one=False)

    class Meta:
        app_label = 'mutant'
        defined_field_class = fields.related.ForeignKey
        defined_field_options = ('to_field',)

    def clean(self):
        try:
            super(ForeignKeyDefinition, self).clean()
        except ValidationError as e:
            messages = e.message_dict
        else:
            messages = {}
        if self.on_delete == self.ON_DELETE_SET_NULL:
            if not self.null:
                msg = _("This field can't be null")
                messages['on_delete'] = [msg]
        elif (self.on_delete == self.ON_DELETE_SET_DEFAULT and
              self.default == fields.NOT_PROVIDED):
            msg = _('This field has no default value')
            messages['on_delete'] = [msg]
        elif (self.on_delete == self.ON_DELETE_SET_VALUE and
              self.on_delete_set_value is None):
            msg = _('You must specify a value to set on deletion')
            messages['on_delete'] = [msg]
        if messages:
            raise ValidationError(messages)

    def get_field_options(self, **overrides):
        options = super(ForeignKeyDefinition, self).get_field_options(**overrides)
        if self.on_delete == self.ON_DELETE_SET_VALUE:
            on_delete = SET(self.on_delete_set_value)
        elif self.on_delete == self.ON_DELETE_SET_NULL:
            on_delete = SET_NULL
        else:
            on_delete = getattr(deletion, self.on_delete, None)
        options['on_delete'] = on_delete
        return options


class OneToOneFieldDefinition(ForeignKeyDefinition):
    objects = ForeignKeyDefinitionManager(one_to_one=True)

    class Meta:
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.related.OneToOneField

    def save(self, *args, **kwargs):
        self.one_to_one = True
        return super(OneToOneFieldDefinition, self).save(*args, **kwargs)


through_help_text = _('Intermediary model')

db_table_help_text = _('The name of the table to create for storing the '
                       'many-to-many data')


class ManyToManyFieldDefinition(RelatedFieldDefinition):
    symmetrical = fields.NullBooleanField(_('symmetrical'))
    through = fields.related.ForeignKey(ContentType, blank=True, null=True,
                                        related_name='+',
                                        help_text=through_help_text)
    # TODO: This should not be a SlugField
    db_table = fields.SlugField(max_length=30, blank=True, null=True,
                                help_text=db_table_help_text)

    class Meta:
        app_label = 'mutant'
        defined_field_class = fields.related.ManyToManyField
        defined_field_options = ('symmetrical', 'db_table')

    def clean(self):
        try:
            super(ManyToManyFieldDefinition, self).clean()
        except ValidationError as e:
            messages = e.message_dict
        else:
            messages = {}

        if (self.symmetrical is not None and
            not self.is_recursive_relationship):
            msg = _("The relationship can only be symmetrical or not if it's "
                    "recursive, i. e. it points to 'self'")
            messages['symmetrical'] = [msg]

        if self.through:
            if self.db_table:
                msg = _('Cannot specify a db_table if an intermediate '
                        'model is used.')
                messages['db_table'] = [msg]

            if self.symmetrical:
                msg = _('Many-to-many fields with intermediate model cannot '
                        'be symmetrical.')
                messages.setdefault('symmetrical', []).append(msg)

            seen_from, seen_to = 0, 0
            to_model = self.to.model_class()
            through_class = self.through.model_class()
            from_model = self.model_def.cached_model
            for field in through_class._meta.fields:
                rel_to = getattr(field.rel, 'to', None)
                if rel_to == from_model:
                    seen_from += 1
                elif rel_to == to_model:
                    seen_to += 1
            if self.is_recursive_relationship():
                if seen_from > 2:
                    msg = _('Intermediary model %s has more than two foreign '
                            'keys to %s, which is ambiguous and is not permitted.')
                    formated_msg = msg % (through_class._meta.object_name,
                                          from_model._meta.object_name)
                    messages.setdefault('through', []).append(formated_msg)
            else:
                msg = _('Intermediary model %s has more than one foreign key '
                        ' to %s, which is ambiguous and is not permitted.')
                if seen_from > 1:
                    formated_msg = msg % (through_class._meta.object_name,
                                          from_model._meta.object_name)
                    messages.setdefault('through', []).append(formated_msg)
                if seen_to > 1:
                    formated_msg = msg % (through_class._meta.object_name,
                                          to_model._meta.object_name)
                    messages.setdefault('through', []).append(formated_msg)

        if messages:
            raise ValidationError(messages)

    def get_field_options(self, **overrides):
        options = super(ManyToManyFieldDefinition, self).get_field_options(**overrides)
        if self.through:
            options['through'] = self.through.model_class()
        return options

    def get_bound_field(self):
        opts = self.model_def.model_class(force_create=True)._meta
        for field in opts.many_to_many:
            if getattr(field, self.FIELD_DEFINITION_PK_ATTR, None) == self.pk:
                return field

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db.models.deletion import ProtectedError
from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import ugettext_lazy as _

from mutant.models import ModelDefinition
from mutant.test.testcases import FieldDefinitionTestMixin
from mutant.tests.utils import BaseModelDefinitionTestCase
from mutant.utils import app_cache_restorer

from .models import ForeignKeyDefinition


class RelatedFieldDefinitionTestMixin(FieldDefinitionTestMixin):
    field_definition_category = _('Related')

    def setUp(self):
        self.field_definition_init_kwargs = {
            'to': ContentType.objects.get_for_model(ContentType),
            'null': True
        }
        super(RelatedFieldDefinitionTestMixin, self).setUp()

    def test_field_clean(self):
        # Refs charettes/django-mutant#5
        try:
            self.field_definition_cls(related_name='related').clean()
        except Exception as e:
            if not isinstance(e, ValidationError):
                self.fail('`clean` method should only raise `ValidationError`')


class ForeignKeyDefinitionTest(RelatedFieldDefinitionTestMixin,
                               BaseModelDefinitionTestCase):
    manual_transaction = True
    field_definition_cls = ForeignKeyDefinition

    def setUp(self):
        self.field_values = (
            ContentType.objects.get_for_model(ContentType),
            ContentType.objects.get_for_model(ModelDefinition),
        )
        super(ForeignKeyDefinitionTest, self).setUp()

    def prepare_default_value(self, value):
        return value.pk

    def test_field_deletion(self):
        def is_related_object_of_ct(model_class):
            related_objs = ContentType._meta.get_all_related_objects(
                include_hidden=True
            )
            return any(
                related_obj.model == model_class for related_obj in related_objs
            )
        self.assertTrue(is_related_object_of_ct(self.model_def.model_class()))
        super(ForeignKeyDefinitionTest, self).test_field_deletion()
        self.assertFalse(is_related_object_of_ct(self.model_def.model_class()))

    def test_foreign_key_between_mutable_models(self):
        first_model_def = self.model_def
        second_model_def = ModelDefinition.objects.create(
            app_label='app', object_name='SecondModel'
        )
        FirstModel = first_model_def.model_class()
        SecondModel = second_model_def.model_class()
        second = SecondModel.objects.create()
        ForeignKeyDefinition.objects.create(
            model_def=first_model_def,
            name='second',
            null=True,
            to=second_model_def,
            related_name='first_set'
        )
        self.assertTrue(second.is_obsolete())
        # Make sure dependencies were set correctly
        self.assertSetEqual(
            SecondModel._dependencies,
            set([(ModelDefinition, first_model_def.pk)])
        )
        second = SecondModel.objects.get()
        first = FirstModel.objects.create(second=second)
        # Make sure related managers are correctly assigned
        self.assertEqual(second.first_set.get(), first)
        # Make sure we can filter by a related field
        self.assertEqual(SecondModel.objects.get(first_set=first), second)
        ForeignKeyDefinition.objects.create(
            model_def=second_model_def,
            name='first',
            null=True,
            to=first_model_def,
            related_name='second_set'
        )
        self.assertTrue(first.is_obsolete())
        # Make sure dependencies were set correctly
        self.assertSetEqual(
            FirstModel._dependencies,
            set([(ModelDefinition, second_model_def.pk)])
        )
        self.assertSetEqual(
            SecondModel._dependencies,
            set([(ModelDefinition, first_model_def.pk)])
        )
        second.first = first
        self.assertRaisesMessage(
            ValidationError, 'Cannot save an obsolete model', second.save
        )
        second = SecondModel.objects.get()
        first = FirstModel.objects.get()
        second.first = first
        second.save()
        # Make sure related managers are correctly assigned
        self.assertEqual(first.second_set.get(), second)
        # Make sure we can filter by a related field
        self.assertEqual(FirstModel.objects.get(second_set=second), first)
        second_model_def.delete()

    def test_recursive_relationship(self):
        fk = ForeignKeyDefinition.objects.create(
            model_def=self.model_def, name='f1', null=True, blank=True,
            to=self.model_def
        )
        self.assertTrue(fk.is_recursive_relationship)
        Model = self.model_def.model_class()
        self.assertEqual(Model._meta.get_field('f1').rel.to, Model)
        obj1 = Model.objects.create()
        obj2 = Model.objects.create(f1=obj1)
        obj1.f1 = obj2
        obj1.save()

    def test_fixture_loading(self):
        with app_cache_restorer():
            call_command(
                'loaddata', 'test_fk_to_loading.json',
                verbosity=0, commit=False
            )
        to_model_def = ModelDefinition.objects.get_by_natural_key(
            'app', 'tomodel'
        )
        to_model_class = to_model_def.model_class()
        # Make sure the origin's model class was created
        self.assertTrue(hasattr(to_model_class, 'froms'))
        from_model_class = to_model_class.froms.related.model
        try:
            fk_field = from_model_class._meta.get_field('fk')
        except FieldDoesNotExist:
            self.fail('The fk field should be created')
        to_model_class = to_model_def.model_class()
        self.assertEqual(fk_field.rel.to, to_model_class)
        to_instance = to_model_class.objects.create()
        from_instance = from_model_class.objects.create(fk=to_instance)
        self.assertEqual(to_instance.froms.get(), from_instance)
        to_instance.delete()
        with self.assertRaises(from_model_class.DoesNotExist):
            from_model_class.objects.get(pk=from_instance.pk)


class ForeignKeyDefinitionOnDeleteTest(BaseModelDefinitionTestCase):
    def test_protect(self):
        ForeignKeyDefinition.objects.create(
            model_def=self.model_def, name='f1', null=True,
            to=self.model_def.model_ct,
            on_delete=ForeignKeyDefinition.ON_DELETE_PROTECT
        )
        Model = self.model_def.model_class()
        obj = Model.objects.create()
        Model.objects.create(f1=obj)
        self.assertRaises(ProtectedError, obj.delete)

    def test_set_null(self):
        fk = ForeignKeyDefinition(
            model_def=self.model_def, name='f1', to=self.model_def.model_ct,
            on_delete=ForeignKeyDefinition.ON_DELETE_SET_NULL
        )
        self.assertRaises(ValidationError, fk.clean)
        fk.null = True
        fk.save()
        Model = self.model_def.model_class()
        obj1 = Model.objects.create()
        obj2 = Model.objects.create(f1=obj1)
        obj1.delete()
        self.assertIsNone(Model.objects.get(pk=obj2.pk).f1)

    def test_set_default(self):
        Model = self.model_def.model_class()
        default = Model.objects.create().pk
        fk = ForeignKeyDefinition.objects.create(
            model_def=self.model_def, name='f1', null=True,
            to=self.model_def.model_ct,
            on_delete=ForeignKeyDefinition.ON_DELETE_SET_DEFAULT
        )
        self.assertRaises(ValidationError, fk.clean)
        fk.default = default
        fk.save()
        obj1 = Model.objects.create()
        obj2 = Model.objects.create(f1=obj1)
        obj1.delete()
        self.assertEqual(Model.objects.get(pk=obj2.pk).f1.pk, default)

    def test_set_value(self):
        Model = self.model_def.model_class()
        default = Model.objects.create().pk
        fk = ForeignKeyDefinition.objects.create(
            model_def=self.model_def, name='f1', null=True,
            to=self.model_def.model_ct,
            on_delete=ForeignKeyDefinition.ON_DELETE_SET_VALUE
        )
        self.assertRaises(ValidationError, fk.clean)
        fk.on_delete_set_value = default
        fk.save()
        obj1 = Model.objects.create()
        obj2 = Model.objects.create(f1=obj1)
        obj1.delete()
        self.assertEqual(Model.objects.get(pk=obj2.pk).f1.pk, default)


#class ManyToManyFieldDefinitionTest(RelatedFieldDefinitionTestMixin,
#                                    BaseModelDefinitionTestCase):
#    field_definition_cls = ManyToManyFieldDefinition
#
#    def setUp(self):
#        self.field_values = (
#            [ContentType.objects.get_for_model(ContentType)],
#            [ContentType.objects.get_for_model(ModelDefinition),
#             ContentType.objects.get_for_model(ContentType)]
#        )
#        super(ManyToManyFieldDefinitionTest, self).setUp()
#
#    def get_field_value(self, instance, name='field'):
#        value = super(RelatedFieldDefinitionTestMixin, self).get_field_value(instance, name)
#        return list(value.all())
#
#    def test_field_renaming(self):
#        # TODO: investigate why this fails
#        return
#        value = self.field_values[0]
#        Model = self.model_def.model_class()
#
#        instance = Model.objects.create()
#        instance.field = value
#
#        self.field.name = 'renamed_field'
#        self.field.save()
#
#        instance = Model.objects.get()
#        self.assertEqual(instance.renamed_field.all(), value)
#
#        self.assertFalse(hasattr(Model, 'field'))
#
#        instance = Model.objects.create()
#        instance.renamed_field = value
#
#    def test_field_default(self):
#        # TODO: Investigate why this fails
#        pass
#
#    def test_model_save(self):
#        # TODO: Investigate why this fails
#        pass
#
#    def test_field_unique(self):
#        # TODO: Investigate why this fails
#        pass
#
#    def test_field_deletion(self):
#        # TODO: Investigate why this fails
#        pass
#
#    def test_field_symmetrical(self):
#        m2m = ManyToManyFieldDefinition(model_def=self.model_def, name='objs')
#        ct_ct = ContentType.objects.get_for_model(ContentType)
#        m2m.to = ct_ct
#
#        with self.assertRaises(ValidationError):
#            m2m.symmetrical = True
#            m2m.clean()
#
#        with self.assertRaises(ValidationError):
#            m2m.symmetrical = False
#            m2m.clean()
#
#        m2m.to = self.model_def.model_ct
#
#        # Make sure `symetrical=True` works
##        m2m.symmetrical = True
##        m2m.clean()
##        m2m.save()
##        
##        Model = self.model_def.model_class()
##        first_object = Model.objects.create()
##        second_object = Model.objects.create()
##        
##        first_object.objs.add(second_object)
##        self.assertIn(first_object, second_object.objs.all())
#
#        # Makes sure non-symmetrical works
#        m2m.symmetrical = False
#        m2m.clean()
#        m2m.save()
#
#        Model = self.model_def.model_class()
#        first_object = Model.objects.create()
#        second_object = Model.objects.create()
#
#        first_object.objs.add(second_object)
#        self.assertNotIn(first_object, second_object.objs.all())
#
#        first_object.objs.clear()

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.db.models import fields
from django.utils.translation import ugettext_lazy as _

from ...models import FieldDefinition, FieldDefinitionManager


auto_now_help_text = _('Automatically set the field to now every time the '
                       'object is saved.')
auto_now_add_help_text = _('Automatically set the field to now when the '
                           'object is first created.')

class DateFieldDefinition(FieldDefinition):
    auto_now = fields.BooleanField(_('auto now'), default=False,
                                   help_text=auto_now_help_text)
    auto_now_add = fields.BooleanField(_('auto now add'), default=False,
                                       help_text=auto_now_add_help_text)

    objects = FieldDefinitionManager()

    class Meta:
        app_label = 'mutant'
        defined_field_class = fields.DateField
        defined_field_options = ('auto_now', 'auto_now_add',)
        defined_field_category = _('Temporal')


class TimeFieldDefinition(DateFieldDefinition):
    class Meta:
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.TimeField


class DateTimeFieldDefinition(DateFieldDefinition):
    class Meta:
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.DateTimeField

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals

import datetime
import warnings

from django.test.utils import override_settings
from django.utils.timezone import make_aware, utc
from django.utils.translation import ugettext_lazy as _

from mutant.test.testcases import FieldDefinitionTestMixin
from mutant.tests.utils import BaseModelDefinitionTestCase

from .models import (DateFieldDefinition, DateTimeFieldDefinition,
    TimeFieldDefinition)


class TemporalFieldDefinitionTestMixin(FieldDefinitionTestMixin):
    field_definition_category = _('Temporal')


class DateFieldDefinitionTest(TemporalFieldDefinitionTestMixin,
                              BaseModelDefinitionTestCase):
    field_definition_cls = DateFieldDefinition
    field_definition_init_kwargs = {'default': datetime.date(1990, 8, 31)}
    field_values = (
        datetime.date.today(),
        datetime.date(1988, 5, 15)
    )


@override_settings(USE_TZ=False)
class NaiveDateTimeFieldDefinitionTest(TemporalFieldDefinitionTestMixin,
                                       BaseModelDefinitionTestCase):
    field_definition_cls = DateTimeFieldDefinition
    field_definition_init_kwargs = {
        'default': datetime.datetime(1990, 8, 31, 23, 46)
    }
    field_values = (
        datetime.datetime(2020, 11, 15, 15, 34),
        datetime.datetime(1988, 5, 15, 15, 30)
    )


@override_settings(USE_TZ=True)
class AwareDateTimeFieldDefinitionTest(TemporalFieldDefinitionTestMixin,
                                       BaseModelDefinitionTestCase):
    field_definition_cls = DateTimeFieldDefinition
    field_definition_init_kwargs = {
        'default': make_aware(datetime.datetime(1990, 8, 31, 23, 46), utc)
    }
    field_values = (
        make_aware(datetime.datetime(2020, 11, 15, 15, 34), utc),
        make_aware(datetime.datetime(1988, 5, 15, 15, 30), utc)
    )

    def test_create_with_naive_default(self):
        """Makes sure creating a DateTimeField with a naive default while
        timezone support is turned on correctly raise a warning instead
        of throwing an exception. refs #23"""
        naive_default = datetime.datetime(1990, 8, 31, 23, 46)
        with warnings.catch_warnings(record=True) as messages:
            DateTimeFieldDefinition.objects.create_with_default(
                model_def=self.model_def,
                name='field_created_with_naive_default',
                default=naive_default
            )
        self.assertEqual(len(messages), 1)
        self.assertIn('received a naive datetime', messages[0].message.args[0])


class TimeFieldDefinitionTest(TemporalFieldDefinitionTestMixin,
                              BaseModelDefinitionTestCase):
    field_definition_cls = TimeFieldDefinition
    field_definition_init_kwargs = {'default': datetime.time(1, 1)}
    field_values = (
        datetime.time(1, 58, 37),
        datetime.time(17, 56)
    )

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.db.models import fields
from django.utils.translation import ugettext_lazy as _

from ...models.field import FieldDefinition
from ...models.field.managers import FieldDefinitionManager


class CharFieldDefinition(FieldDefinition):
    max_length = fields.PositiveSmallIntegerField(
        _('max length'), blank=True, null=True
    )

    objects = FieldDefinitionManager()

    class Meta:
        app_label = 'mutant'
        defined_field_class = fields.CharField
        defined_field_options = ('max_length',)
        defined_field_description = _('String')
        defined_field_category = _('Text')


class TextFieldDefinition(CharFieldDefinition):
    class Meta:
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.TextField

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
# TODO: Remove when support for Python 2.6 is dropped
if sys.version_info >= (2, 7):
    from unittest import skipIf, skipUnless
else:
    from django.utils.unittest import skipIf, skipUnless

from django.db import connection
from django.db.utils import DatabaseError
from django.utils.translation import ugettext_lazy as _
import south

from mutant.test.testcases import FieldDefinitionTestMixin
from mutant.tests.utils import BaseModelDefinitionTestCase

from .models import CharFieldDefinition, TextFieldDefinition


class TextFieldDefinitionTestMixin(FieldDefinitionTestMixin):
    field_definition_category = _('Text')


class CharFieldDefinitionTest(TextFieldDefinitionTestMixin,
                              BaseModelDefinitionTestCase):
    field_definition_cls = CharFieldDefinition
    field_definition_init_kwargs = {'max_length': 255}
    field_values = ('Raptor Jesus', 'Nirvana')

    @skipUnless(
        connection.settings_dict['ENGINE'] != 'django.db.backends.sqlite3',
        "SQLite3 doesn't enforce CHAR length"
    )
    def test_field_max_length(self):
        self.field.max_length = 24
        self.field.save()
        Model = self.model_def.model_class()
        with self.assertRaises(DatabaseError):
            Model.objects.create(field='Simon' * 5)


class TextFieldDefinitionTest(TextFieldDefinitionTestMixin,
                              BaseModelDefinitionTestCase):
    field_definition_cls = TextFieldDefinition
    field_values = (
        """
        J'ai caché
        Mieux que partout ailleurs
        Au grand jardin de mon coeur
        Une petite fleur
        Cette fleur
        Plus jolie q'un bouquet
        Elle garde en secret
        Tous mes rêves d'enfant
        L'amour de mes parents
        Et tous ces clairs matins
        Fait d'heureux souvenirs lointains
        """,
        """
        Quand la vie
        Par moments me trahi
        Tu restes mon bonheur
        Petite fleur

        Sur mes vingt ans
        Je m'arrête un moment
        Pour respirer
        Le parfum que j'ai tant aimé

        Dans mon coeur
        Tu fleuriras toujours
        Au grand jardin d'amour
        Petite fleur
        """,
    )

    @skipIf(
        connection.settings_dict['ENGINE'] == 'django.db.backends.sqlite3' and
        south.__version__ in ('0.8.1', '0.8.2', '0.8.3', '0.8.4'),
        "This version of South doesn't escape added column default value correctly on SQLite3."
    )
    def test_create_with_default(self):
        super(TextFieldDefinitionTest, self).test_create_with_default()

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db.models import fields
from django.utils.translation import ugettext_lazy as _

from ..text.models import CharFieldDefinition
from ...models import FieldDefinitionManager


class _WebMeta:
    defined_field_category = _('Web')


class EmailFieldDefinition(CharFieldDefinition):
    class Meta(_WebMeta):
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.EmailField


class URLFieldDefinition(CharFieldDefinition):
    class Meta(_WebMeta):
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.URLField


class SlugFieldDefinition(CharFieldDefinition):
    class Meta(_WebMeta):
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.SlugField
        defined_field_description = _('slug')


class IPAddressFieldDefinition(CharFieldDefinition):
    class Meta(_WebMeta):
        app_label = 'mutant'
        proxy = True
        defined_field_class = fields.IPAddressField


protocol_help_text = _('Limits valid inputs to the specified protocol.')
unpack_ipv4_help_text = _('Unpacks IPv4 mapped addresses like '
                          '``::ffff::192.0.2.1`` to ``192.0.2.1``')

class GenericIPAddressFieldDefinition(CharFieldDefinition):
    PROTOCOL_BOTH = 'both'
    PROTOCOL_IPV4 = 'IPv4'
    PROTOCOL_IPV6 = 'IPv6'

    PROTOCOL_CHOICES = (
        (PROTOCOL_BOTH, _('both')),
        (PROTOCOL_IPV4, _('IPv4')),
        (PROTOCOL_IPV6, _('IPv6'))
    )

    protocol = fields.CharField(
        _('protocol'), max_length=4,
        choices=PROTOCOL_CHOICES, default=PROTOCOL_BOTH
    )
    unpack_ipv4 = fields.BooleanField(_('unpack ipv4'), default=False)

    objects = FieldDefinitionManager()

    class Meta(_WebMeta):
        app_label = 'mutant'
        defined_field_class = fields.GenericIPAddressField
        defined_field_options = ('protocol', 'unpack_ipv4',)
        defined_field_description = _('generic IP address')

    def clean(self):
        if self.unpack_ipv4 and self.procotol != 'both':
            msg = _("Can only be used when ``protocol`` is set to 'both'.")
            raise ValidationError({'unpack_ipv4': msg})

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from mutant.test.testcases import FieldDefinitionTestMixin
from mutant.tests.utils import BaseModelDefinitionTestCase

from .models import (EmailFieldDefinition, GenericIPAddressFieldDefinition,
    IPAddressFieldDefinition, SlugFieldDefinition, URLFieldDefinition)


class WebFieldDefinitionTestMixin(FieldDefinitionTestMixin):
    field_definition_category = _('Web')


class EmailFieldDefinitionTest(WebFieldDefinitionTestMixin,
                               BaseModelDefinitionTestCase):
    field_definition_cls = EmailFieldDefinition
    field_values = ('guido@python.org', 'god@heaven.com')


class IPAddressFieldDefinitionTest(WebFieldDefinitionTestMixin,
                                   BaseModelDefinitionTestCase):
    field_definition_cls = IPAddressFieldDefinition
    field_definition_init_kwargs = {'default': '192.168.1.1'}
    field_values = ('127.0.0.1', '82.94.164.162')


class SlugFieldDefinitionTest(WebFieldDefinitionTestMixin,
                              BaseModelDefinitionTestCase):
    field_definition_cls = SlugFieldDefinition
    field_values = (
        'an-awesome-slug_-_-',
        '2012-4-7-so-late'
    )


class URLFieldDefinitionTest(WebFieldDefinitionTestMixin,
                             BaseModelDefinitionTestCase):
    field_definition_cls = URLFieldDefinition
    field_values = (
        'https://github.com/charettes/django-mutant',
        'http://travis-ci.org/#!/charettes/django-mutant',
    )


class GenericIPAddressFieldDefinitionTest(WebFieldDefinitionTestMixin,
                                          BaseModelDefinitionTestCase):
    field_definition_cls = GenericIPAddressFieldDefinition
    field_values = (
        '127.0.0.1',
        '2001:db8:85a3::8a2e:370:7334'
    )

########NEW FILE########
__FILENAME__ = deletion
from __future__ import unicode_literals

from django.db.models.deletion import CASCADE


def CASCADE_MARK_ORIGIN(collector, field, sub_objs, using):
    """
    Custom on_delete handler which sets  _cascade_deletion_origin on the _state
    of the  all relating objects that will deleted.
    We use this handler on ModelDefinitionAttribute.model_def, so when we delete
    a ModelDefinition we can skip field_definition_post_delete and
    base_definition_post_delete and avoid an incremental columns deletion before
    the entire table is dropped.
    """
    CASCADE(collector, field, sub_objs, using)
    if sub_objs:
        for obj in sub_objs:
            obj._state._cascade_deletion_origin = field.name

########NEW FILE########
__FILENAME__ = generic
from __future__ import unicode_literals

import warnings

import django
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from polymodels.fields import PolymorphicTypeField

from ... import forms


class FieldDefinitionTypeField(PolymorphicTypeField):
    def __init__(self, *args, **kwargs):
        super(FieldDefinitionTypeField, self).__init__(
            'mutant.FieldDefinition', *args, **kwargs
        )

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.FieldDefinitionTypeField}
        defaults.update(kwargs)
        return super(FieldDefinitionTypeField, self).formfield(**kwargs)


# TODO: Remove when support for Django 1.5 is dropped.
if django.VERSION < (1, 7):
    class ProxyAwareGenericForeignKey(GenericForeignKey):
        """
        Basically a GenericForeignKey that saves the actual ContentType of the
        object even if it's a proxy Model.
        """
        if django.VERSION >= (1, 6):
            def __init__(self, *args, **kwargs):
                warnings.warn(
                    '`ProxyAwareGenericForeignKey` is deprecated on Django >= '
                    '1.6. Use `GenericForeignKey` with the '
                    '`for_concrete_model=False` kwarg instead.',
                    DeprecationWarning, stacklevel=2
                )
                super(ProxyAwareGenericForeignKey, self).__init__(*args, **kwargs)

        def get_content_type(self, obj=None, **kwargs):
            if obj:
                return ContentType.objects.db_manager(obj._state.db).get_for_model(
                    obj.__class__, for_concrete_model=False
                )
            else:
                return super(ProxyAwareGenericForeignKey, self).get_content_type(obj, **kwargs)

########NEW FILE########
__FILENAME__ = introspection_rules
from south.modelsinspector import add_introspection_rules


add_introspection_rules([], ['^mutant\.db\.fields\.generic\.FieldDefinitionTypeField'])
add_introspection_rules([], ['^mutant\.db\.fields\.python\.PythonIdentifierField'])
add_introspection_rules([], ['^mutant\.db\.fields\.python\.RegExpStringField'])
add_introspection_rules([], ['^mutant\.db\.fields\.python\.DirectoryPathField'])
add_introspection_rules([], ['^mutant\.db\.fields\.translation\.LazilyTranslatedField'])

########NEW FILE########
__FILENAME__ = python
from __future__ import unicode_literals

import os
import re

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.fields import CharField
from django.utils.translation import ugettext_lazy as _

from ...validators import validate_python_identifier


class DirectoryPathField(CharField):
    def validate(self, value, model_instance):
        if not os.path.exists(value):
            raise ValidationError(_("Specified path doesn't exist"))
        elif not os.path.isdir(value):
            raise ValidationError(_("Specified path isn't a directory"))


class RegExpStringField(CharField):
    def to_python(self, value):
        value = super(RegExpStringField, self).to_python(value)
        if value is None:
            return
        try:
            re.compile(value)
        except Exception as e:
            raise ValidationError(_(e))
        else:
            return value


class PythonIdentifierField(CharField):
    __metaclass__ = models.SubfieldBase

    default_validators = [validate_python_identifier]
    description = _('Python identifier')

    def __init__(self, *args, **kwargs):
        defaults = {'max_length': 255}
        defaults.update(kwargs)
        super(PythonIdentifierField, self).__init__(*args, **defaults)

    def to_python(self, value):
        value = super(PythonIdentifierField, self).to_python(value)
        if value is not None:
            return str(value)

########NEW FILE########
__FILENAME__ = related
from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.db.models import fields
from django.db.models.signals import class_prepared

from ...models import ModelDefinition
from django.db.models.fields import FieldDoesNotExist


class ModelClassAttributeDescriptor(object):
    """
    Provide an access to an attribute of  a model definition's underlying
    model class. Useful for defining an accessor to a manager.
    """
    def __init__(self, model_def_name, attr_name):
        self.model_def_name = model_def_name
        self.attr_name = attr_name

    def __validate(self, **kwargs):
        opts = self.model._meta
        try:
            field = opts.get_field(self.model_def_name)
        except FieldDoesNotExist:
            raise ImproperlyConfigured("%s.%s.%s refers to an inexistent field "
                                       "'%s'" % (opts.app_label, opts.object_name,
                                                 self.name, self.model_def_name))
        else:
            if (not isinstance(field, fields.related.ForeignKey) or
                not issubclass(field.rel.to, ModelDefinition)):
                raise ImproperlyConfigured("%s.%s.%s must refer to a ForeignKey "
                                           "to `ModelDefinition`"
                                           % (opts.app_label, opts.object_name,
                                              self.name))
        setattr(self.model, self.name, self)

    def contribute_to_class(self, cls, name):
        self.model = cls
        self.name = name
        class_prepared.connect(self.__validate, cls, weak=True)

    def __get__(self, instance, instance_type=None):
        if instance:
            try:
                model_def = getattr(instance, self.model_def_name)
            except ModelDefinition.DoesNotExist:
                pass
            else:
                if model_def is not None:
                    return getattr(model_def.model_class(), self.attr_name)
            raise AttributeError("Can't access attribute '%s' of the "
                                 "model defined by '%s' since it doesn't exist."
                                 % (self.attr_name, self.model_def_name))
        else:
            return self

    def __set__(self, instance, value):
        raise AttributeError("Can't set attribute")

########NEW FILE########
__FILENAME__ = translation
from __future__ import unicode_literals

import django
from django.db.models.fields import TextField
from django.utils.encoding import smart_unicode
from django.utils.functional import Promise
from django.utils.translation import ugettext_lazy as _


if django.VERSION[0:2] > (1, 4):
    _delegate_bytes = '_delegate_bytes'
    _delegate_text = '_delegate_text'
else:
    _delegate_bytes = '_delegate_str'
    _delegate_text = '_delegate_unicode'

def _is_gettext_promise(value):
    return isinstance(value, Promise) and (getattr(value, _delegate_bytes) or
                                           getattr(value, _delegate_text))


class LazilyTranslatedField(TextField):
    def to_python(self, value):
        if value is None or _is_gettext_promise(value):
            return value
        return _(smart_unicode(value))

    def get_prep_value(self, value):
        if value is None:
            return value
        elif _is_gettext_promise(value):
            value = smart_unicode(value._proxy____args[0])
        return smart_unicode(value)

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .. import logger
from ..state import handler as state_handler


class MutableModel(models.Model):
    """Abstract class used to identify models that we're created by a
    definition."""

    class Meta:
        abstract = True

    @classmethod
    def definition(cls):
        definition_cls, definition_pk = cls._definition
        return definition_cls.objects.get(pk=definition_pk)

    @classmethod
    def checksum(cls):
        return cls._checksum

    @classmethod
    def is_obsolete(cls):
        return (
            cls._is_obsolete or
            cls._checksum != state_handler.get_checksum(cls._definition[1])
        )

    @classmethod
    def mark_as_obsolete(cls, origin=None):
        cls._is_obsolete = True
        logger.debug(
            "Marking model %s and it dependencies (%s) as obsolete.",
            cls, cls._dependencies
        )
        if origin is None:
            origin = cls._definition
        for definition_cls, definition_pk in cls._dependencies:
            if (definition_cls, definition_pk) == origin:
                continue
            try:
                definition = definition_cls.objects.get(pk=definition_pk)
            except definition_cls.DoesNotExist:
                pass
            else:
                definition.model_class().mark_as_obsolete(origin)

    def clean(self):
        if self.is_obsolete():
            raise ValidationError('Obsolete definition')
        return super(MutableModel, self).clean()

    def save(self, *args, **kwargs):
        if self.is_obsolete():
            msg = _('Cannot save an obsolete model')
            raise ValidationError(msg)
        return super(MutableModel, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_obsolete():
            msg = _('Cannot delete an obsolete model')
            raise ValidationError(msg)
        return super(MutableModel, self).delete(*args, **kwargs)

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import smart_text

from .utils import choices_from_dict, group_item_getter, LazyObject


class LazyFieldDefinitionQueryset(LazyObject):
    def __init__(self, queryset, models):
        super(LazyFieldDefinitionQueryset, self).__init__()
        self.__dict__.update(queryset=queryset, models=models)

    def _setup(self):
        queryset = self.__dict__.get('queryset')
        models = self.__dict__.get('models')
        self._wrapped = queryset.filter(
            pk__in=[ct.pk for ct in ContentType.objects.get_for_models(
                *models, for_concrete_models=False
            ).values()]
        )


class LazyFieldDefinitionGroupedChoices(LazyObject):
    def __init__(self, queryset, empty_label, label_from_instance):
        super(LazyFieldDefinitionGroupedChoices, self).__init__()
        self.__dict__.update(
            queryset=queryset, empty_label=empty_label,
            label_from_instance=label_from_instance
        )

    def _setup(self):
        queryset = self.__dict__.get('queryset')
        label_from_instance = self.__dict__.get('label_from_instance')
        empty_label = self.__dict__.get('empty_label')
        definition_choices = []
        for content_type in queryset:
            definition = content_type.model_class()
            category = definition.get_field_category()
            definition_choices.append({
                'group': smart_text(category) if category else None,
                'value': content_type.pk,
                'label': label_from_instance(content_type),
            })
        choices = list(
            choices_from_dict(
                sorted(definition_choices, key=group_item_getter)
            )
        )
        if empty_label is not None:
            choices.insert(0, ('', self.empty_label))
        self._wrapped = choices


class FieldDefinitionTypeField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        self.field_definitions = kwargs.pop('field_definitions', [])
        self.group_by_category = kwargs.pop('group_by_category', False)
        super(FieldDefinitionTypeField, self).__init__(*args, **kwargs)

    def _get_field_definitions(self):
        return self._field_definitions

    def _set_field_definitions(self, definitions):
        for definition in definitions:
            from mutant.models import FieldDefinition
            if not issubclass(definition, FieldDefinition):
                raise TypeError(
                    "%r is not a subclass of `FieldDefinition`" % definition
                )
        self._field_definitions = definitions

    field_definitions = property(_get_field_definitions, _set_field_definitions)

    def _get_queryset(self):
        queryset = super(FieldDefinitionTypeField, self)._get_queryset()
        if self.field_definitions:
            return LazyFieldDefinitionQueryset(queryset, self.field_definitions)
        return queryset

    queryset = property(_get_queryset, forms.ModelChoiceField._set_queryset)

    def _get_choices(self):
        if self.group_by_category:
            return LazyFieldDefinitionGroupedChoices(
                self.queryset, self.empty_label, self.label_from_instance
            )
        return super(FieldDefinitionTypeField, self)._get_choices()

    choices = property(_get_choices, forms.ModelChoiceField._set_queryset)

    def label_from_instance(self, obj):
        return smart_text(obj.model_class().get_field_description())

########NEW FILE########
__FILENAME__ = hacks
from __future__ import unicode_literals


def patch_model_option_verbose_name_raw():
    """
    Until #17763 and all the permission name length issues are fixed we patch
    the `verbose_name_raw` method to return a truncated string in order to
    avoid DatabaseError.
    """
    from django.db.models.options import Options
    verbose_name_raw = Options.verbose_name_raw.fget
    if hasattr(verbose_name_raw, '_patched'):
        return

    def _get_verbose_name_raw(self):
        name = verbose_name_raw(self)
        if len(name) >= 40:
            name = "%s..." % name[0:36]
        return name
    _get_verbose_name_raw.patched = True
    Options.verbose_name_raw = property(_get_verbose_name_raw)

########NEW FILE########
__FILENAME__ = dumpdata
from __future__ import unicode_literals

from django.core.management.commands.dumpdata import Command as BaseCommand

from ...models import ModelDefinition


class Command(BaseCommand):
    """
    `dumpdata` command override that makes sure to load all required mutable
    models in the cache prior to dumping.
    """

    def handle(self, *app_labels, **options):
        model_defs = ModelDefinition.objects.all()

        # Filter out non needed model definitions when some are specified.
        if app_labels:
            model_defs = model_defs.filter(
                app_label__in=set(
                    app_label.split('.')[0] for app_label in app_labels
                )
            )

        # Generate model class associated with model classes.
        for model_def in model_defs:
            model_def.model_class()

        return super(Command, self).handle(*app_labels, **options)

########NEW FILE########
__FILENAME__ = loaddata
from __future__ import unicode_literals

from django.core.management.commands.loaddata import Command
from django.core.serializers import python as python_serializer
from django.core.serializers.base import DeserializationError

from ...models import ModelDefinition


# Monkey patch `_get_model` to attempt loading a matching model definition
# when no existing model is found.
_python_serializer_get_model = python_serializer._get_model


def _get_model(model_identifier):
    try:
        return _python_serializer_get_model(model_identifier)
    except DeserializationError as e:
        try:
            model_def = ModelDefinition.objects.get_by_natural_key(
                *model_identifier.split('.')
            )
        except ModelDefinition.DoesNotExist:
            raise e
        return model_def.model_class()

python_serializer._get_model = _get_model

########NEW FILE########
__FILENAME__ = managers
from __future__ import unicode_literals
import warnings

import django
from django.db import models


class FilteredQuerysetManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        super(FilteredQuerysetManager, self).__init__()

    def get_queryset(self):
        qs = super(FilteredQuerysetManager, self).get_queryset()
        return qs.filter(*self.args, **self.kwargs)

    if django.VERSION < (1, 8):
        if django.VERSION >= (1, 6):
            def get_query_set(self):
                warnings.warn(
                    "`FilteredQuerysetManager.get_query_set` is deprecated, "
                    "use `get_queryset` instead",
                    DeprecationWarning if django.VERSION >= (1, 7)
                        else PendingDeprecationWarning,
                    stacklevel=2
                )
                return FilteredQuerysetManager.get_queryset(self)
        else:
            def get_query_set(self):
                qs = super(FilteredQuerysetManager, self).get_query_set()
                return qs.filter(*self.args, **self.kwargs)

########NEW FILE########
__FILENAME__ = managers
from __future__ import unicode_literals

import warnings

import django
from django.db import models
from polymodels.managers import PolymorphicManager, PolymorphicQuerySet

from ...utils import choices_from_dict


class FieldDefinitionQuerySet(PolymorphicQuerySet):
    def create_with_default(self, default, **kwargs):
        obj = self.model(**kwargs)
        obj._state._creation_default_value = default
        self._for_write = True
        obj.save(force_insert=True, using=self.db)
        return obj


class FieldDefinitionManager(PolymorphicManager):
    def get_queryset(self):
        return FieldDefinitionQuerySet(self.model, using=self._db)

    if django.VERSION < (1, 8):
        def get_query_set(self):
            if django.VERSION >= (1, 6):
                warnings.warn(
                    "`FieldDefinitionManager.get_query_set` is deprecated, "
                    "use `get_queryset` instead.",
                    DeprecationWarning if django.VERSION >= (1, 7)
                        else PendingDeprecationWarning,
                    stacklevel=2
                )
            return FieldDefinitionManager.get_queryset(self)

    def get_by_natural_key(self, app_label, model, name):
        qs = self.select_subclasses()
        return qs.get(model_def__app_label=app_label,
                      model_def__model=model, name=name)

    def names(self):
        qs = self.get_queryset()
        return qs.order_by('name').values_list('name', flat=True)

    def create_with_default(self, default, **kwargs):
        qs = self.get_queryset()
        return qs.create_with_default(default, **kwargs)


class FieldDefinitionChoiceQuerySet(models.query.QuerySet):
    def construct(self):
        # Here we don't use .values() since it's raw output from the database
        # and values are not prepared correctly.
        choices = (
           {'group': choice.group,
            'label': choice.label,
            'value': choice.value}
           for choice in self.only('group', 'value', 'label')
        )
        return tuple(choices_from_dict(choices))


class FieldDefinitionChoiceManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return FieldDefinitionChoiceQuerySet(self.model, using=self._db)

    if django.VERSION < (1, 8):
        def get_query_set(self):
            if django.VERSION >= (1, 6):
                warnings.warn(
                    "`FieldDefinitionChoiceManager.get_query_set` is"
                    "deprecated, use `get_queryset` instead.",
                    DeprecationWarning if django.VERSION >= (1, 7)
                        else PendingDeprecationWarning,
                    stacklevel=2
                )
            return FieldDefinitionChoiceManager.get_queryset(self)

    def construct(self):
        return self.get_queryset().construct()

########NEW FILE########
__FILENAME__ = managers
from __future__ import unicode_literals

from django.db import models


class ModelDefinitionManager(models.Manager):
    use_for_related_fields = True

    def get_by_natural_key(self, app_label, model):
        return self.get(app_label=app_label, model=model)

########NEW FILE########
__FILENAME__ = ordered
from __future__ import unicode_literals

from django.db import models
from django.db.models.aggregates import Max


class OrderedModel(models.Model):
    order = models.PositiveIntegerField(editable=False)

    class Meta:
        abstract = True
        ordering = ['order']

    def get_ordering_queryset(self):
        return self._default_manager.all()

    def save(self, *args, **kwargs):
        if self.order is None:
            max_order = self.get_ordering_queryset().aggregate(
                Max('order')
            ).get('order__max')
            self.order = 0 if max_order is None else max_order + 1
        return super(OrderedModel, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = settings
from __future__ import unicode_literals

from django.conf import settings
from django.core.cache import DEFAULT_CACHE_ALIAS


STATE_HANDLER = getattr(
    settings, 'MUTANT_STATE_HANDLER',
    'mutant.state.handlers.memory.MemoryStateHandler'
)

STATE_CACHE_ALIAS = getattr(
    settings, 'MUTANT_STATE_CACHE_ALIAS', DEFAULT_CACHE_ALIAS
)

STATE_PUBSUB = getattr(
    settings, 'MUTANT_STATE_PUBSUB', (
        'mutant.state.handlers.pubsub.engines.Redis', {}
    )
)

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal


mutable_class_prepared = Signal(providing_args=['class', 'definition'])
########NEW FILE########
__FILENAME__ = cache
from __future__ import unicode_literals

from django.core.cache import get_cache

from ...settings import STATE_CACHE_ALIAS


class CacheStateHandler(object):
    """State handlers that relies on cache to store and retrieve the current
    checksum of a definition."""

    def __init__(self):
        self.cache = get_cache(STATE_CACHE_ALIAS)

    def get_cache_key(self, definition_pk):
        return "mutant-%s" % definition_pk

    def get_checksum(self, definition_pk):
        cache_key = self.get_cache_key(definition_pk)
        return self.cache.get(cache_key)

    def set_checksum(self, definition_pk, checksum):
        cache_key = self.get_cache_key(definition_pk)
        return self.cache.set(cache_key, checksum)

    def clear_checksum(self, definition_pk):
        cache_key = self.get_cache_key(definition_pk)
        return self.cache.delete(cache_key)

########NEW FILE########
__FILENAME__ = memory
from __future__ import unicode_literals

from threading import RLock


class MemoryStateHandler(object):
    """State handler that relies on a lock and an in-memory map of definition
    pk and their associated checksums to maintain the current state of mutable
    models."""

    checksums = {}
    lock = RLock()

    def get_checksum(self, definition_pk):
        return self.checksums.get(definition_pk)

    def set_checksum(self, definition_pk, checksum):
        with self.lock:
            self.checksums[definition_pk] = checksum

    def clear_checksum(self, definition_pk):
        with self.lock:
            try:
                del self.checksums[definition_pk]
            except KeyError:
                pass

########NEW FILE########
__FILENAME__ = engines
from __future__ import unicode_literals

import json

from threading import Thread


class Redis(Thread):
    channel = 'mutant-state'

    def __init__(self, callback, **options):
        import redis
        super(Redis, self).__init__(name='mutant-state-pubsub-redis-engine')
        self.callback = callback
        self.connection = redis.StrictRedis(**options)
        self.pubsub = self.connection.pubsub()

    def run(self):
        self.pubsub.subscribe(self.channel)
        for event in self.pubsub.listen():
            if event['type'] == 'message':
                args = json.loads(event['data'])
                self.callback(*args)

    def publish(self, *args):
        message = json.dumps(args)
        self.connection.publish(self.channel, message)

    def join(self, timeout=None):
        self.pubsub.unsubscribe(self.channel)
        return super(Redis, self).join(timeout)

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals

from threading import local

from django.utils.module_loading import import_by_path


class HandlerProxy(object):
    def __init__(self, path):
        self._handlers = local()
        self.path = path

    def __getattribute__(self, name):
        get = super(HandlerProxy, self).__getattribute__
        try:
            return get(name)
        except AttributeError:
            pass
        handlers = get('_handlers')
        path = get('path')
        try:
            handler = getattr(handlers, path)
        except AttributeError:
            handler = import_by_path(path, 'MUTANT_STATE_HANDLER ')()
            setattr(handlers, path, handler)
        return getattr(handler, name)

########NEW FILE########
__FILENAME__ = testcases
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.db import connections, router, transaction
from django.db.utils import DEFAULT_DB_ALIAS, IntegrityError
from django.test.testcases import TestCase
from south.db import dbs as south_dbs

from ..models.model import ModelDefinition


class DDLTestCase(TestCase):
    """
    A class that behaves like `TestCase` if all connections support DDL
    transactions or like `TransactionTestCase` if it's not the case.
    """
    manual_transaction = False

    def connections_have_ddl_transactions(self):
        """
        Returns True if all implied connections have DDL transactions support.
        """
        db_names = connections if getattr(self, 'multi_db', False) else [DEFAULT_DB_ALIAS]
        return all(south_dbs[name].has_ddl_transactions for name in db_names)

    def _fixture_setup(self):
        if (not self.manual_transaction and
            self.connections_have_ddl_transactions()):
            return super(DDLTestCase, self)._fixture_setup()
        else:
            return super(TestCase, self)._fixture_setup()

    def _fixture_teardown(self):
        if (not self.manual_transaction and
            self.connections_have_ddl_transactions()):
            return super(DDLTestCase, self)._fixture_teardown()
        else:
            return super(TestCase, self)._fixture_teardown()


class ModelDefinitionDDLTestCase(DDLTestCase):
    def tearDown(self):
        if (self.manual_transaction or
            not self.connections_have_ddl_transactions()):
            # Remove all the extra tables since `TransactionTestCase` only
            # truncate data on teardown.
            ModelDefinition.objects.all().delete()
        ContentType.objects.clear_cache()


class FieldDefinitionTestMixin(object):
    field_definition_init_kwargs = {}
    field_values = ()

    def setUp(self):
        super(FieldDefinitionTestMixin, self).setUp()
        with self.assertChecksumChange():
            self.field = self.field_definition_cls._default_manager.create(
                model_def=self.model_def, name='field',
                **self.field_definition_init_kwargs
            )

    def get_field_value(self, instance, name='field'):
        return getattr(instance, name)

    def prepare_default_value(self, value):
        return value

    def test_field_default(self):
        default = self.prepare_default_value(self.field_values[0])
        field = self.field
        # Default value should be valid
        with self.assertChecksumChange():
            field.default = default
            field.full_clean()
            field.save()
        # Default value should be assigned correctly
        model_class = self.model_def.model_class()
        instance = model_class.objects.create()
        field_value = self.get_field_value(instance)
        created_default = self.prepare_default_value(field_value)
        self.assertEqual(created_default, default)

    def test_create_with_default(self):
        """Makes sure a field definition manager is attached to the model and
        `create_with_default` works correctly."""
        model_class = self.model_def.model_class()
        field_value = self.field_values[0]
        instance = model_class.objects.create(field=field_value)
        # Add the field with a default.
        create_default = self.prepare_default_value(field_value)
        options = dict(**self.field_definition_init_kwargs)
        options['default'] = create_default
        with self.assertChecksumChange():
            self.field_definition_cls._default_manager.create_with_default(
                model_def=self.model_def, name='field_created_with_default',
                **options
            )
        created_value = self.prepare_default_value(
            model_class.objects.get(pk=instance.pk).field_created_with_default
        )
        self.assertEqual(created_value, create_default)

    def test_model_save(self):
        first_value, second_value = self.field_values
        # Assigning a value should work
        model_class = self.model_def.model_class()
        instance = model_class.objects.create(field=first_value)
        self.assertEqual(self.get_field_value(instance), first_value)
        # Assigning a new one should also work
        instance.field = second_value
        instance.save()
        instance = model_class.objects.get()
        self.assertEqual(self.get_field_value(instance), second_value)

    def test_field_renaming(self):
        value = self.field_values[0]
        model_class = self.model_def.model_class()
        # Renaming a field should update its column name
        model_class.objects.create(field=value)
        opts = model_class._meta
        original_column_name = opts.get_field('field').get_attname_column()[1]
        with self.assertChecksumChange():
            self.field.name = 'renamed_field'
            self.field.save()
        opts = model_class._meta
        new_column_name = opts.get_field('renamed_field').get_attname_column()[1]
        self.assertModelTablesColumnDoesntExists(
            model_class, original_column_name
        )
        self.assertModelTablesColumnExists(
            model_class, new_column_name
        )
        # Old data should be accessible by the new field name
        instance = model_class.objects.get()
        self.assertEqual(self.get_field_value(instance, 'renamed_field'), value)
        # The old field shouldn't be accessible anymore
        msg = "'field' is an invalid keyword argument for this function"
        self.assertRaisesMessage(TypeError, msg, model_class, field=value)
        # It should be possible to create objects using the new field name
        model_class.objects.create(renamed_field=value)

    def test_field_deletion(self):
        value = self.field_values[0]
        model_class = self.model_def.model_class()
        model_class.objects.create(field=value)
        # Deleting a field should delete the associated column
        opts = model_class._meta
        field_column_name = opts.get_field('field').get_attname_column()[1]
        with self.assertChecksumChange():
            self.field.delete()
        self.assertModelTablesColumnDoesntExists(model_class, field_column_name)
        # The deleted field shouldn't be accessible anymore
        msg = "'field' is an invalid keyword argument for this function"
        self.assertRaisesMessage(TypeError, msg, model_class, field=value)

    def test_field_unique(self):
        value = self.field_values[0]
        model_class = self.model_def.model_class()
        with self.assertChecksumChange():
            self.field.unique = True
            self.field.save()
        model_class.objects.create(field=value)
        write_db = router.db_for_write(model_class)
        connection = connections[write_db]
        # TODO: Convert this to `atomic` once support for Django < 1.6 is dropped
        sid = transaction.savepoint(using=write_db)
        try:
            model_class.objects.create(field=value)
        except IntegrityError:
            pass
        else:
            self.fail("One shouldn't be able to save duplicate entries in a unique field")
        finally:
            connection.needs_rollback = False
            transaction.savepoint_rollback(sid, using=write_db)

    def test_field_cloning(self):
        with self.assertChecksumChange():
            clone = self.field.clone()
            clone.name = 'field_clone'
            clone.model_def = self.model_def
            clone.save(force_insert=True)

    def test_field_definition_category(self):
        self.assertEqual(
            self.field_definition_cls.get_field_category(),
            self.field_definition_category
        )

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals

from django.core.signals import request_started
from django.db import reset_queries


try:
    from django.test.utils import CaptureQueriesContext
except ImportError:
    # TODO: Remove when support for Django < 1.6 is dropped
    class CaptureQueriesContext(object):
        """
        Context manager that captures queries executed by the specified connection.
        """
        def __init__(self, connection):
            self.connection = connection

        def __iter__(self):
            return iter(self.captured_queries)

        def __getitem__(self, index):
            return self.captured_queries[index]

        def __len__(self):
            return len(self.captured_queries)

        @property
        def captured_queries(self):
            return self.connection.queries[self.initial_queries:self.final_queries]

        def __enter__(self):
            self.use_debug_cursor = self.connection.use_debug_cursor
            self.connection.use_debug_cursor = True
            self.initial_queries = len(self.connection.queries)
            self.final_queries = None
            request_started.disconnect(reset_queries)
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.connection.use_debug_cursor = self.use_debug_cursor
            request_started.connect(reset_queries)
            if exc_type is not None:
                return
            self.final_queries = len(self.connection.queries)

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from mutant.models import FieldDefinition
from mutant.db.fields import FieldDefinitionTypeField


class CustomFieldDefinition(FieldDefinition):
    class Meta:
        app_label = 'mutant'
        defined_field_category = _('Custom category')
        defined_field_description = _('Custom description')


class FieldDefinitionModel(models.Model):
    field_type = FieldDefinitionTypeField()

    class Meta:
        app_label = 'mutant'

########NEW FILE########
__FILENAME__ = runners
from __future__ import unicode_literals

import logging
from optparse import make_option

from django.conf import settings
try:
    from django.test.runner import DiscoverRunner
except ImportError:
    try:
        from discover_runner import DiscoverRunner
    except ImportError:
        raise ImportError(
            'django-discover-runner must be installed in order to use '
            '`MutantTestSuiteRunner` under Django < 1.6'
        )

from mutant import logger


class MutantTestSuiteRunner(DiscoverRunner):
    option_list = (
        make_option('-l', '--logger-level',
            dest='logger_level',
            help='Set the level of the `mutant` logger.'),
    )

    def __init__(self, logger_level, **kwargs):
        super(MutantTestSuiteRunner, self).__init__(**kwargs)
        if logger_level:
            logger.setLevel(logger_level)
            logger.addHandler(logging.StreamHandler())

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        if not test_labels:
            test_labels = [
                "%s.tests" % app for app in settings.INSTALLED_APPS
                if app.startswith('mutant') or app in ('south', 'polymodels')
            ]
        return super(MutantTestSuiteRunner, self).build_suite(
            test_labels, extra_tests=None, **kwargs
        )

########NEW FILE########
__FILENAME__ = postgis
from __future__ import unicode_literals

from .postgresql_psycopg2 import *


DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'

INSTALLED_APPS.extend([
    'django.contrib.gis',
    'mutant.contrib.geo',
])

COVERAGE_MODULE_EXCLUDES.remove('mutant.contrib.geo')
########NEW FILE########
__FILENAME__ = postgresql_psycopg2
from __future__ import unicode_literals

from . import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'mutant',
    }
}
########NEW FILE########
__FILENAME__ = sqlite3
from __future__ import unicode_literals

from . import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}
########NEW FILE########
__FILENAME__ = test_commands
from __future__ import unicode_literals

import json
from StringIO import StringIO
from tempfile import NamedTemporaryFile

from django.core.management import call_command
from django.core.serializers.json import Serializer as JSONSerializer

from mutant.models import ModelDefinition
from mutant.test.testcases import ModelDefinitionDDLTestCase
from mutant.utils import remove_from_app_cache
from django.core.serializers.base import DeserializationError


class DataCommandTestCase(ModelDefinitionDDLTestCase):
    def setUp(self):
        self.model_def = ModelDefinition.objects.create(
            app_label='mutant', object_name='Model'
        )
        self.model_cls = self.model_def.model_class()

    def tearDown(self):
        if self.model_def.pk:
            self.model_def.delete()


class DumpDataTestCase(DataCommandTestCase):
    def dump_model_data(self):
        # Make sure to remove the model from the app cache because we're
        # actually testing it's correctly loaded.
        output = StringIO()
        remove_from_app_cache(self.model_cls)
        call_command(
            'dumpdata', str(self.model_def), stdout=output, commit=False
        )
        output.seek(0)
        return json.load(output)

    def test_dump_mutable_models(self):
        """
        Make sure mutable models instances are dumped when calling `dumpdata`.
        """
        self.assertEqual(self.dump_model_data(), [])
        instance = self.model_cls.objects.create()
        self.assertEqual(
            self.dump_model_data(), [{
                'pk': instance.pk,
                'model': str(self.model_def).lower(),
                'fields': {}
            }]
        )


class LoadDataTestCase(DataCommandTestCase):
    def setUp(self):
        super(LoadDataTestCase, self).setUp()
        self.serializer = JSONSerializer()

    def test_load_mutable_models(self):
        """
        Makes sure mutable models instances are correctly loaded when calling
        `loaddata`.
        """
        instance = self.model_cls(pk=1)
        # Make sure to remove the model from the app cache because we're
        # actually testing it's correctly loaded.
        remove_from_app_cache(self.model_cls)
        with NamedTemporaryFile(suffix='.json') as stream:
            self.serializer.serialize([instance], stream=stream)
            stream.seek(0)
            call_command(
                'loaddata', stream.name, stdout=StringIO(), commit=False
            )
        self.assertTrue(self.model_cls.objects.filter(pk=instance.pk).exists())

    def test_invalid_model_idenfitier_raises(self):
        """
        Makes sure an invalid model identifier raises the correct exception.
        """
        instance = self.model_cls(pk=1)
        with NamedTemporaryFile(suffix='.json') as stream:
            self.serializer.serialize([instance], stream=stream)
            stream.seek(0)
            self.model_def.delete()
            with self.assertRaisesMessage(
                    DeserializationError, "Invalid model identifier: 'mutant.model'"):
                call_command(
                    'loaddata', stream.name, stdout=StringIO()
                )

########NEW FILE########
__FILENAME__ = test_fields
from __future__ import unicode_literals

import sys
# TODO: Remove when support for Python 2.6 is dropped
if sys.version_info >= (2, 7):
    from unittest import TestCase
else:
    from django.utils.unittest import TestCase

from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.translation import ugettext_lazy as _

from mutant.db.fields.related import ModelClassAttributeDescriptor
from mutant.db.fields.translation import LazilyTranslatedField
from mutant.models import ModelDefinition

from .utils import BaseModelDefinitionTestCase


class LazilyTranslatedFieldTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.field = LazilyTranslatedField()
        return super(LazilyTranslatedFieldTest, cls).setUpClass()

    def test_to_python(self):
        self.assertIsNone(self.field.to_python(None))
        self.assertEqual(self.field.to_python(_('hello')), _('hello'))
        self.assertEqual(self.field.to_python('hello'), _('hello'))
        self.assertEqual(self.field.to_python('hello'), _('hello'))
        self.assertEqual(self.field.to_python(1), _('1'))

    def test_get_prep_value(self):
        self.assertIsNone(self.field.get_prep_value(None))
        self.assertEqual(self.field.get_prep_value(_('hello')), 'hello')
        self.assertEqual(self.field.get_prep_value('hello'), 'hello')
        self.assertEqual(self.field.get_prep_value('hello'), 'hello')
        self.assertEqual(self.field.get_prep_value(1), '1')


class ModelWithModelDefinitionReference(models.Model):
    model_def = models.OneToOneField(ModelDefinition, related_name='+')
    model_objects = ModelClassAttributeDescriptor('model_def', 'objects')

    nullable_model_def = models.ForeignKey(
        ModelDefinition, related_name='+', null=True
    )
    nullable_objects = ModelClassAttributeDescriptor(
        'nullable_model_def', 'objects'
    )

    class Meta:
        app_label = 'mutant'


class ModelDefinitionReferenceTest(BaseModelDefinitionTestCase):
    def test_manager_name_clash(self):
        # Inexistent field
        with self.assertRaises(ImproperlyConfigured):
            class InexistentModelDefField(models.Model):
                objs = ModelClassAttributeDescriptor('model_def', 'objects')
        # Non-FK field
        with self.assertRaises(ImproperlyConfigured):
            class NonFKModelDefField(models.Model):
                name = models.CharField(max_length=100)
                objs = ModelClassAttributeDescriptor('name', 'objects')
        # FK not pointing to ModelDefinition
        with self.assertRaises(ImproperlyConfigured):
            class NonModelDefFKField(models.Model):
                model_def = models.ForeignKey('self')
                objs = ModelClassAttributeDescriptor('model_def', 'objects')

    def test_manager_descriptor(self):
        obj = ModelWithModelDefinitionReference()
        # Not nullable field definition should raise
        with self.assertRaises(AttributeError):
            obj.model_objects
        # Nullable field definition should raise
        with self.assertRaises(AttributeError):
            obj.nullable_objects
        # Assigning an existing model def should allow manager retrieval
        obj.model_def = self.model_def
        self.assertIsInstance(obj.model_objects, models.Manager)
        # Assigning an existing model def should allow manager retrieval
        obj.nullable_model_def = self.model_def
        self.assertIsInstance(obj.nullable_objects, models.Manager)
        # Making sure we've got the right model
        Model = self.model_def.model_class()
        Model.objects.create()
        self.assertEqual(obj.model_objects.count(), 1)
        self.assertEqual(obj.nullable_objects.count(), 1)

########NEW FILE########
__FILENAME__ = test_field_defs
from __future__ import unicode_literals

import sys
import warnings
# TODO: Remove when support for Python 2.6 is dropped
if sys.version_info >= (2, 7):
    from unittest import TestCase
else:
    from django.utils.unittest import TestCase

from django.core.exceptions import ValidationError

from mutant.contrib.numeric.models import IntegerFieldDefinition
from mutant.contrib.text.models import CharFieldDefinition
from mutant.models.field import (FieldDefinition, FieldDefinitionChoice,
    NOT_PROVIDED)
from mutant.tests.utils import BaseModelDefinitionTestCase


class FieldDefinitionInheritanceTest(BaseModelDefinitionTestCase):
    def test_proxy_inheritance(self):
        obj = CharFieldDefinition.objects.create(name='caca',
                                                  max_length=25,
                                                  model_def=self.model_def)
        save_obj = self.model_def.fielddefinitions.select_subclasses().get()
        self.assertEqual(obj, save_obj)
        Model = self.model_def.model_class()
        Model.objects.create(caca="NO WAY")


class FieldDefinitionDeclarationTest(TestCase):
    def test_delete_override(self):
        """
        Make sure a warning is raised when declaring a `FieldDefinition`
        subclass that override the `delete` method.
        """
        with self.assertRaises(TypeError):
            with warnings.catch_warnings(record=True) as catched_warnings:
                class CustomFieldDefinition(FieldDefinition):
                    def delete(self, *args, **kwargs):
                        pass

                class CustomFieldDefinitionProxy(CustomFieldDefinition):
                    class Meta:
                        proxy = True

                    def delete(self, *args, **kwargs):
                        pass

        self.assertIn('Avoid overriding the `delete` method on '
                      '`FieldDefinition` subclass `CustomFieldDefinition`',
                      catched_warnings[0].message.args[0])


def module_level_pickable_default():
    module_level_pickable_default.incr += 1
    return module_level_pickable_default.incr
module_level_pickable_default.incr = 0


class FieldDefaultTest(BaseModelDefinitionTestCase):
    def test_clean(self):
        field = IntegerFieldDefinition(name='field', model_def=self.model_def)
        # Field cleaning should work when a default value isn't provided
        field.clean()
        with self.assertRaises(ValidationError):
            field.default = 'invalid'
            field.clean()
        field.default = module_level_pickable_default
        field.clean()
        field.save()
        Model = self.model_def.model_class()
        self.assertEqual(Model.objects.create().field,
                         module_level_pickable_default.incr)
        field.default = NOT_PROVIDED
        field.save()
        with self.assertRaises(ValidationError):
            obj = Model()
            obj.field
            obj.full_clean()

    def test_create_with_default(self):
        Model = self.model_def.model_class()
        Model.objects.create()
        IntegerFieldDefinition.objects.create_with_default(1337, name='field',
                                                           model_def=self.model_def)
        before = Model.objects.get()
        self.assertEqual(before.field, 1337)
        self.assertFalse(Model().field)


class FieldDefinitionChoiceTest(BaseModelDefinitionTestCase):
    def test_simple_choices(self):
        field_def = CharFieldDefinition.objects.create(name='gender',
                                                       max_length=1,
                                                       model_def=self.model_def)
        male_choice = FieldDefinitionChoice(field_def=field_def,
                                            value='Male', label='Male')
        # Value is longer than the max_length
        self.assertRaises(ValidationError, male_choice.clean)
        # A length of 1 should work
        male_choice.value = 'M'
        male_choice.full_clean()
        male_choice.save()
        # Cleaning should raise validation error when passed invalid choice
        Model = self.model_def.model_class()
        obj = Model(gender='T')
        self.assertRaises(ValidationError, obj.full_clean)
        # Create another allowed choice
        female_choice = FieldDefinitionChoice(field_def=field_def,
                                              value='F', label='Female')
        female_choice.value = 'F'
        female_choice.full_clean()
        female_choice.save()
        # It should now be possible to create valid objects with this choice
        obj = Model(gender='F')
        obj.full_clean()
        # Make sure choices are correctly set
        choices = Model._meta.get_field('gender').get_choices(include_blank=False)
        self.assertEqual(choices, [('M', 'Male'), ('F', 'Female')])

    def test_grouped_choices(self):
        field_def = CharFieldDefinition.objects.create(name='media',
                                                       max_length=5,
                                                       model_def=self.model_def)
        # Create Audio choices
        FieldDefinitionChoice.objects.create(field_def=field_def, group='Audio',
                                             value='vinyl', label='Vinyl')
        FieldDefinitionChoice.objects.create(field_def=field_def, group='Audio',
                                             value='cd', label='CD')
        # Create Video choices
        FieldDefinitionChoice.objects.create(field_def=field_def, group='Video',
                                             value='vhs', label='VHS Tape')
        FieldDefinitionChoice.objects.create(field_def=field_def, group='Video',
                                             value='dvd', label='DVD')
        # Create Unknown choices
        FieldDefinitionChoice.objects.create(field_def=field_def,
                                             value='unknown', label='Unknown')
        # Make sure choices are correctly created
        Model = self.model_def.model_class()
        choices = Model._meta.get_field('media').get_choices(include_blank=False)
        expected_choices = [
            ('Audio', (
                    ('vinyl', 'Vinyl'),
                    ('cd', 'CD'),
                )
             ),
            ('Video', (
                    ('vhs', 'VHS Tape'),
                    ('dvd', 'DVD'),
                )
             ),
            ('unknown', 'Unknown')
        ]
        self.assertEqual(choices, expected_choices)


class FieldDefinitionManagerTest(BaseModelDefinitionTestCase):
    def test_natural_key(self):
        fd = CharFieldDefinition.objects.create(name='name', max_length=5,
                                                model_def=self.model_def)
        natural_key = fd.natural_key()
        self.assertEqual(
            FieldDefinition.objects.get_by_natural_key(*natural_key), fd
        )

########NEW FILE########
__FILENAME__ = test_forms
from __future__ import unicode_literals

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test.testcases import TestCase
from django.utils.translation import ugettext

from mutant.forms import FieldDefinitionTypeField
from mutant.models.field import FieldDefinition

from .models import CustomFieldDefinition, FieldDefinitionModel


class FieldDefinitionTypeFieldTests(TestCase):
    def setUp(self):
        self.field_definition_ct = FieldDefinition.get_content_type()
        self.custom_field_ct = CustomFieldDefinition.get_content_type()
        self.content_type_ct = ContentType.objects.get_for_model(ContentType)
        self.field_types = ContentType.objects.filter(
            **FieldDefinition.subclasses_lookup('pk')
        )
        ContentType.objects.clear_cache()

    def test_invalid_field_definitions(self):
        with self.assertRaisesMessage(
            TypeError, 'is not a subclass of `FieldDefinition`'):
            FieldDefinitionTypeField(
                self.field_types, field_definitions=[FieldDefinitionTypeField]
            )

    def test_valid_value(self):
        with self.assertNumQueries(0):
            field = FieldDefinitionTypeField(self.field_types)
        self.assertEqual(
            field.to_python(self.field_definition_ct.pk),
            self.field_definition_ct
        )
        self.assertEqual(
            field.to_python(self.custom_field_ct.pk),
            self.custom_field_ct
        )
        with self.assertRaises(ValidationError):
            field.to_python(self.content_type_ct.pk)

    def test_field_definitions_valid_value(self):
        with self.assertNumQueries(0):
            field = FieldDefinitionTypeField(
                self.field_types, field_definitions=[CustomFieldDefinition]
            )
        with self.assertRaises(ValidationError):
            field.to_python(self.field_definition_ct.pk)
        self.assertEqual(
            field.to_python(self.custom_field_ct.pk),
            self.custom_field_ct
        )
        with self.assertRaises(ValidationError):
            field.to_python(self.content_type_ct.pk)

    def test_form_validation(self):
        with self.assertNumQueries(0):
            class CustomModelForm(forms.Form):
                field_type = FieldDefinitionTypeField(self.field_types)
        custom_field_ct = CustomFieldDefinition.get_content_type()
        form = CustomModelForm({'field_type': self.custom_field_ct.pk})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['field_type'], custom_field_ct)

    def test_model_form_validation(self):
        form_cls = forms.models.modelform_factory(
            FieldDefinitionModel, fields=['field_type']
        )

        form = form_cls({'field_type': self.field_definition_ct.pk})
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data['field_type'], self.field_definition_ct
        )

        form = form_cls({'field_type': self.custom_field_ct.pk})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['field_type'], self.custom_field_ct)

        form = form_cls({'field_type': self.content_type_ct.pk})
        self.assertFalse(form.is_valid())

    def test_choices(self):
        with self.assertNumQueries(0):
            field = FieldDefinitionTypeField(
                ContentType.objects.filter(pk__in=[
                    self.field_definition_ct.pk, self.custom_field_ct.pk
                ]).order_by('pk'), group_by_category=False, empty_label='Empty'
            )
        self.assertEqual(
            list(field.choices), [
                ('', 'Empty'),
                (self.field_definition_ct.pk, 'None'),
                (self.custom_field_ct.pk, ugettext('Custom description'))
            ]
        )

    def test_group_by_category_choices(self):
        with self.assertNumQueries(0):
            field = FieldDefinitionTypeField(
                ContentType.objects.filter(pk__in=[
                    self.field_definition_ct.pk, self.custom_field_ct.pk
                ]).order_by('pk'), group_by_category=True, empty_label=None
            )
        self.assertEqual(
            list(field.choices), [
                (self.field_definition_ct.pk, 'None'),
                (ugettext('Custom category'), (
                    (self.custom_field_ct.pk, ugettext('Custom description')),
                ))
            ]
        )

########NEW FILE########
__FILENAME__ = test_model_defs
from __future__ import unicode_literals

import pickle

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connections, models, router
from django.db.utils import IntegrityError
from django.utils.translation import ugettext_lazy as _

from mutant.contrib.text.models import CharFieldDefinition
from mutant.contrib.related.models import ForeignKeyDefinition
from mutant.db.models import MutableModel
from mutant.models.model import (ModelDefinition, OrderingFieldDefinition,
    UniqueTogetherDefinition, BaseDefinition, MutableModelProxy)
from mutant.test.utils import CaptureQueriesContext
from mutant.utils import clear_opts_related_cache

from .utils import BaseModelDefinitionTestCase


try:
    from test.test_support import captured_stderr
except ImportError:
    # python 2.6 doesn't provide this helper
    from contextlib import contextmanager
    import StringIO
    import sys

    @contextmanager
    def captured_stderr():
        stderr = sys.stderr
        try:
            sys.stderr = StringIO.StringIO()
            yield sys.stderr
        finally:
            sys.stderr = stderr


class Mixin(object):
    def method(self):
        return 'Mixin'


class ConcreteModel(models.Model):
    concrete_model_field = models.NullBooleanField()

    class Meta:
        app_label = 'mutant'


class ProxyModel(ConcreteModel):
    class Meta:
        proxy = True


class AbstractModel(models.Model):
    abstract_model_field = models.CharField(max_length=5)

    class Meta:
        abstract = True

    def method(self):
        return 'AbstractModel'


class AbstractConcreteModelSubclass(ConcreteModel):
    abstract_concrete_model_subclass_field = models.CharField(max_length=5)

    class Meta:
        abstract = True


class ModelSubclassWithTextField(models.Model):
    abstract_model_field = models.TextField()
    second_field = models.NullBooleanField()

    class Meta:
        abstract = True


class ModelDefinitionTest(BaseModelDefinitionTestCase):
    def test_model_class_creation_cache(self):
        existing_model_class = self.model_def.model_class()
        self.assertEqual(existing_model_class, self.model_def.model_class())
        self.assertNotEqual(
            self.model_def.model_class(force_create=True), existing_model_class
        )

    def test_force_create_checksum(self):
        """Recreating a model with no changes shouldn't change it's checksum"""
        with self.assertChecksumDoesntChange():
            self.model_def.model_class(force_create=True)

    def test_repr(self):
        """Make sure ModelDefinition objects are always repr()-able."""
        repr(self.model_def)
        repr(ModelDefinition())

    def get_model_db_table_name(self, model_def):
        model_class = model_def.model_class()
        return router.db_for_write(model_class), model_class._meta.db_table

    def test_app_label_rename(self):
        db, table_name = self.get_model_db_table_name(self.model_def)

        with self.assertChecksumChange():
            self.model_def.app_label = 'myapp'
            self.model_def.save(update_fields=['app_label'])

        self.assertTableDoesntExists(db, table_name)
        db, table_name = self.get_model_db_table_name(self.model_def)
        self.assertTableExists(db, table_name)

    def test_object_name_rename(self):
        db, table_name = self.get_model_db_table_name(self.model_def)

        with self.assertChecksumChange():
            self.model_def.object_name = 'MyModel'
            self.model_def.save(update_fields=['object_name', 'model'])

        self.assertTableDoesntExists(db, table_name)
        db, table_name = self.get_model_db_table_name(self.model_def)
        self.assertTableExists(db, table_name)

    def test_db_table_change(self):
        """Asserts that the `db_table` field is correctly handled."""
        db, table_name = self.get_model_db_table_name(self.model_def)

        with self.assertChecksumChange():
            self.model_def.db_table = 'test_db_table'
            self.model_def.save(update_fields=['db_table'])

        self.assertTableDoesntExists(db, table_name)
        self.assertTableExists(db, 'test_db_table')

        with self.assertChecksumChange():
            self.model_def.db_table = None
            self.model_def.save(update_fields=['db_table'])

        self.assertTableDoesntExists(db, 'test_db_table')
        self.assertTableExists(db, table_name)

    def test_fixture_loading(self):
        """Make model and field definitions can be loaded from fixtures."""
        call_command(
            'loaddata', 'fixture_loading_test', verbosity=0, commit=False
        )
        self.assertTrue(
            ModelDefinition.objects.filter(
                app_label='myfixtureapp', object_name='MyFixtureModel'
            ).exists()
        )
        model_def = ModelDefinition.objects.get(
            app_label='myfixtureapp', object_name='MyFixtureModel'
        )
        MyFixtureModel = model_def.model_class()
        self.assertModelTablesExist(MyFixtureModel)
        # Makes sure concrete field definition subclasses are created...
        self.assertTrue(
            model_def.fielddefinitions.filter(
                name='fixture_charfield'
            ).exists()
        )
        # and their column is created.
        self.assertModelTablesColumnExists(MyFixtureModel, 'fixture_charfieldcolumn')
        # Makes sure proxy field definition subclasses are created...
        self.assertTrue(
            model_def.fielddefinitions.filter(
                name='fixture_integerfield'
            ).exists()
        )
        # and their column is created.
        self.assertModelTablesColumnExists(MyFixtureModel, 'fixture_integerfieldcolumn')

    def test_verbose_name(self):
        model_class = self.model_def.model_class()

        self.assertEqual(model_class._meta.verbose_name, 'model')

        with self.assertChecksumChange():
            self.model_def.verbose_name = 'MyModel'
            self.model_def.save(update_fields=['verbose_name'])

        self.assertEqual(
            model_class._meta.verbose_name, self.model_def.verbose_name
        )

    def test_verbose_name_plural(self):
        model_class = self.model_def.model_class()

        self.assertEqual(model_class._meta.verbose_name_plural, 'models')

        with self.assertChecksumChange():
            self.model_def.verbose_name_plural = 'MyModels'
            self.model_def.save(update_fields=['verbose_name_plural'])

        self.assertEqual(
            model_class._meta.verbose_name_plural,
            self.model_def.verbose_name_plural
        )

    def test_multiple_model_definition(self):
        """Make sure multiple model definition can coexist."""
        other_model_def = ModelDefinition.objects.create(
            app_label='app', object_name='OtherModel'
        )
        self.assertNotEqual(
            other_model_def.model_class(), self.model_def.model_class()
        )
        self.assertNotEqual(other_model_def.model_ct, self.model_def.model_ct)

    def test_natural_key(self):
        natural_key = self.model_def.natural_key()
        self.assertEqual(
            ModelDefinition.objects.get_by_natural_key(*natural_key),
            self.model_def
        )

    def test_deletion(self):
        # Add a an extra field to make sure no alter statements are issued
        with self.assertChecksumChange():
            CharFieldDefinition.objects.create(
                model_def=self.model_def,
                name='field',
                max_length=10
            )
        # Add a base with a field to make sure no alter statements are issued
        with self.assertChecksumChange():
            BaseDefinition.objects.create(
                model_def=self.model_def,
                base=AbstractModel
            )
        model_cls = self.model_def.model_class()
        self.assertModelTablesExist(model_cls)
        db, table_name = self.get_model_db_table_name(self.model_def)
        connection = connections[db]
        with CaptureQueriesContext(connection) as captured_queries:
            self.model_def.delete()
        # Ensure no ALTER queries were issued during deletion of model_def,
        # that is, check that the columns were not deleted on table one at a
        # time before the entire table was dropped.
        self.assertFalse(
            any('ALTER' in query['sql'] for query in captured_queries)
        )
        self.assertTableDoesntExists(db, table_name)

    def test_model_management(self):
        """Make sure no DDL is executed when a model is marked as managed."""
        model_def = self.model_def
        CharFieldDefinition.objects.create(
            model_def=model_def,
            name='field',
            max_length=10
        )
        model_cls = model_def.model_class()
        model_cls.objects.create(field='test')
        # Mark the existing model definition as `managed`.
        model_def.managed = True
        model_def.save()
        # Deleting a managed model shouldn't issue a DROP TABLE.
        db, table_name = self.get_model_db_table_name(self.model_def)
        model_def.delete()
        self.assertTableExists(db, table_name)
        # Attach a new model definition to the existing table
        new_model_def = ModelDefinition.objects.create(
            app_label=model_def.app_label,
            object_name=model_def.object_name,
            managed=True,
            fields=(CharFieldDefinition(name='field', max_length=10),)
        )
        # Make sure old data can be retrieved
        self.assertEqual(1, new_model_def.model_class().objects.count())
        # Mark the new model as unmanaged to make sure it's associated
        # table is deleted on tear down.
        new_model_def.managed = False
        new_model_def.save()


class ModelDefinitionManagerTest(BaseModelDefinitionTestCase):
    def test_fields_creation(self):
        char_field = CharFieldDefinition(name='name', max_length=10)
        ct_ct = ContentType.objects.get_for_model(ContentType)
        fk_field = ForeignKeyDefinition(name='ct', to=ct_ct)
        model_def = ModelDefinition.objects.create(
            app_label='app', object_name='OtherModel',
            fields=[char_field, fk_field]
        )
        model_cls = model_def.model_class()
        db = router.db_for_write(model_cls)
        table = model_cls._meta.db_table
        column = model_cls._meta.get_field('name').get_attname_column()[1]
        # Make sure column was created
        self.assertColumnExists(db, table, column)
        # Make sure field definitions were created
        self.assertIsNotNone(char_field.pk)
        self.assertIsNotNone(fk_field.pk)

    def test_bases_creation(self):
        mixin_base = BaseDefinition(base=Mixin)
        abstract_base = BaseDefinition(base=AbstractModel)
        abstract_concrete_base = BaseDefinition(
            base=AbstractConcreteModelSubclass
        )
        model_def = ModelDefinition.objects.create(
            app_label='app', object_name='OtherModel',
            bases=[mixin_base, abstract_base, abstract_concrete_base],
        )
        model = model_def.model_class()
        self.assertModelTablesColumnDoesntExists(model, 'id')
        self.assertModelTablesColumnExists(model, 'concretemodel_ptr_id')
        self.assertModelTablesColumnExists(model, 'abstract_model_field')
        self.assertModelTablesColumnDoesntExists(model, 'concrete_model_field')
        self.assertModelTablesColumnExists(
            model, 'abstract_concrete_model_subclass_field'
        )

    def test_primary_key_override(self):
        field = CharFieldDefinition(
            name='name', max_length=32, primary_key=True
        )
        model_def = ModelDefinition.objects.create(
            fields=[field], app_label='app', object_name='OtherModel'
        )
        self.assertEqual(model_def.model_class()._meta.pk.name, field.name)

    def test_get_or_create(self):
        """
        Make sure bases and fields defaults are reaching the model initializer.
        """
        field = CharFieldDefinition(name='name', max_length=32)
        base = BaseDefinition(base=AbstractModel)
        ModelDefinition.objects.get_or_create(
            app_label='app', object_name='OtherModel',
            defaults={'bases': [base], 'fields': [field]}
        )
        self.assertIsNotNone(field.pk)
        self.assertIsNotNone(base.pk)


class ModelValidationTest(BaseModelDefinitionTestCase):
    def test_installed_app_override_failure(self):
        """
        Make sure we can't save a model definition with an app_label of
        an installed app.
        """
        self.model_def.app_label = 'mutant'
        self.assertRaises(ValidationError, self.model_def.clean)


class MutableModelProxyTest(BaseModelDefinitionTestCase):
    def test_pickling(self):
        """Make sure `MutableModelProxy` instances can be pickled correctly.
        This is required for mutable model inheritance."""
        proxy = self.model_def.model_class()
        pickled = pickle.dumps(proxy)
        self.assertEqual(pickle.loads(pickled), proxy)
        self.assertEqual(pickle.loads(pickled), proxy.model)

    def test_type_checks(self):
        proxy = self.model_def.model_class()
        self.assertTrue(issubclass(proxy, models.Model))
        self.assertTrue(issubclass(proxy, MutableModel))
        self.assertFalse(issubclass(proxy, MutableModelProxyTest))
        self.assertIsInstance(proxy, models.base.ModelBase)
        self.assertIsInstance(proxy, MutableModelProxy)
        self.assertFalse(isinstance(proxy, MutableModelProxyTest))

    def test_instance_checks(self):
        proxy = self.model_def.model_class()
        instance = proxy()
        self.assertIsInstance(instance, proxy)
        self.assertIsInstance(instance, proxy.model)

    def test_contains(self):
        proxy = self.model_def.model_class()
        self.assertIn(proxy, set([proxy.model]))
        self.assertIn(proxy.model, set([proxy]))

    def test_proxy_interactions(self):
        CharFieldDefinition.objects.create(
            model_def=self.model_def, name="name", max_length=10
        )
        proxy = self.model_def.model_class()
        # Attribute access
        sergei = proxy.objects.create(name='Sergei')
        # Callable access
        halak = proxy(name='Halak')
        halak.save()
        self.assertEqual(
            "<class 'mutant.apps.app.models.Model'>", unicode(proxy)
        )
        self.assertEqual(sergei, proxy.objects.get(name='Sergei'))

        class A(object):
            class_model = proxy

            def __init__(self, model):
                self.model = model

        a = A(proxy)

        self.assertEqual(proxy, a.model)
        self.assertEqual(proxy, A.class_model)

        a.model = proxy  # Assign a proxy
        a.model = a.model  # Assign a Model
        a.model = 4

    def test_definition_deletion(self):
        CharFieldDefinition.objects.create(model_def=self.model_def,
                                           name="name", max_length=10)

        Model = self.model_def.model_class()
        db = router.db_for_write(Model)
        instance = Model.objects.create(name="Quebec")
        table_name = Model._meta.db_table
        self.model_def.delete()
        self.assertTableDoesntExists(db, table_name)

        with self.assertRaises(AttributeError):
            Model(name="name")

        with self.assertRaises(AttributeError):
            Model.objects.all()

        with self.assertRaises(ValidationError):
            instance.clean()

        with self.assertRaises(ValidationError):
            instance.save()

        with self.assertRaises(ValidationError):
            instance.delete()

    def test_refreshing_safeguard(self):
        """Make sure model refreshing that occurs when a model class is
        obsolete doesn't hang when a model class in the app_cache points to
        the obsolete one thus triggering a chain of refreshing indirectly
        caused by `ModelDefinition._opts.get_all_related_objects`."""
        proxy = self.model_def.model_class()
        model = proxy.model
        # Create a FK pointing to a  model class that will become obsolete
        fk = models.ForeignKey(to=proxy)
        fk.contribute_to_class(model, 'fk')
        model.mark_as_obsolete()
        # Clear up the related cache of ModelDefiniton to make sure
        # _fill_related_objects_cache` is called.
        clear_opts_related_cache(ModelDefinition)
        self.assertTrue(model.is_obsolete())
        # Trigger model refreshing to make sure the `refreshing` safe guard works
        self.assertFalse(proxy.is_obsolete())
        # Cleanup the FK to avoid test pollution.
        model._meta.local_fields.remove(fk)


class OrderingDefinitionTest(BaseModelDefinitionTestCase):
    def setUp(self):
        super(OrderingDefinitionTest, self).setUp()
        with self.assertChecksumChange():
            self.f1 = CharFieldDefinition.objects.create(
                model_def=self.model_def, name='f1', max_length=25
            )
        ct_ct = ContentType.objects.get_for_model(ContentType)
        with self.assertChecksumChange():
            self.f2 = ForeignKeyDefinition.objects.create(
                model_def=self.model_def, null=True, name='f2', to=ct_ct
            )

    def test_clean(self):
        ordering = OrderingFieldDefinition(model_def=self.model_def)
        # Random
        ordering.lookup = '?'
        ordering.clean()
        # By f1
        ordering.lookup = 'f1'
        ordering.clean()
        # By f2 app label
        ordering.lookup = 'f2__app_label'
        ordering.clean()
        # Inexistent field
        with self.assertRaises(ValidationError):
            ordering.lookup = 'inexistent_field'
            ordering.clean()
        # Inexistent field of an existent field
        with self.assertRaises(ValidationError):
            ordering.lookup = 'f2__higgs_boson'
            ordering.clean()

    def test_simple_ordering(self):
        Model = self.model_def.model_class()
        model_ct = ContentType.objects.get_for_model(Model)  # app
        ct_ct = ContentType.objects.get_for_model(ContentType)  # contenttypes
        Model.objects.create(f1='Simon', f2=ct_ct)
        Model.objects.create(f1='Alexander', f2=model_ct)
        # Instances should be sorted by id
        self.assertSequenceEqual(
            Model.objects.values_list('f1', flat=True), ('Simon', 'Alexander')
        )
        # Instances should be sorted by f1 and not id
        with self.assertChecksumChange():
            f1_ordering = OrderingFieldDefinition.objects.create(
                model_def=self.model_def, lookup='f1'
            )
        self.assertSequenceEqual(
            Model.objects.values_list('f1', flat=True), ('Alexander', 'Simon')
        )
        # Swap the ordering to descending
        with self.assertChecksumChange():
            f1_ordering.descending = True
            f1_ordering.save()
        self.assertSequenceEqual(
            Model.objects.values_list('f1', flat=True), ('Simon', 'Alexander')
        )
        with self.assertChecksumChange():
            f1_ordering.delete()
        # Order by f2__app_label
        with self.assertChecksumChange():
            f2_ordering = OrderingFieldDefinition.objects.create(
                model_def=self.model_def, lookup='f2__app_label'
            )
        self.assertSequenceEqual(
            Model.objects.values_list('f1', flat=True), ('Alexander', 'Simon')
        )
        # Swap the ordering to descending
        with self.assertChecksumChange():
            f2_ordering.descending = True
            f2_ordering.save()
        self.assertSequenceEqual(
            Model.objects.values_list('f1', flat=True), ('Simon', 'Alexander')
        )
        with self.assertChecksumChange():
            f2_ordering.delete()

    def test_multiple_ordering(self):
        Model = self.model_def.model_class()
        model_ct = ContentType.objects.get_for_model(Model)  # app
        ct_ct = ContentType.objects.get_for_model(ContentType)  # contenttypes
        Model.objects.create(f1='Simon', f2=ct_ct)
        Model.objects.create(f1='Alexander', f2=model_ct)
        Model.objects.create(f1='Julia', f2=ct_ct)
        Model.objects.create(f1='Alexander', f2=ct_ct)
        # Orderings
        with self.assertChecksumChange():
            f1_ordering = OrderingFieldDefinition.objects.create(
                model_def=self.model_def, lookup='f1'
            )
        with self.assertChecksumChange():
            f2_ordering = OrderingFieldDefinition.objects.create(
                model_def=self.model_def, lookup='f2__app_label'
            )
        self.assertSequenceEqual(
            Model.objects.values_list('f1', 'f2__app_label'), (
                ('Alexander', 'app'),
                ('Alexander', 'contenttypes'),
                ('Julia', 'contenttypes'),
                ('Simon', 'contenttypes')
            )
        )
        # Swap the ordering to descending
        with self.assertChecksumChange():
            f2_ordering.descending = True
            f2_ordering.save()
        self.assertSequenceEqual(
            Model.objects.values_list('f1', 'f2__app_label'), (
                ('Alexander', 'contenttypes'),
                ('Alexander', 'app'),
                ('Julia', 'contenttypes'),
                ('Simon', 'contenttypes')
            )
        )
        # Swap order
        f1_ordering.order, f2_ordering.order = f2_ordering.order, f1_ordering.order
        with self.assertChecksumChange():
            f1_ordering.save()
            f2_ordering.save()
        self.assertSequenceEqual(
            Model.objects.values_list('f1', 'f2__app_label'), (
                ('Alexander', 'contenttypes'),
                ('Julia', 'contenttypes'),
                ('Simon', 'contenttypes'),
                ('Alexander', 'app')
            )
        )
        # Swap the ordering to descending
        with self.assertChecksumChange():
            f1_ordering.descending = True
            f1_ordering.save()
        self.assertSequenceEqual(
            Model.objects.values_list('f1', 'f2__app_label'), (
                ('Simon', 'contenttypes'),
                ('Julia', 'contenttypes'),
                ('Alexander', 'contenttypes'),
                ('Alexander', 'app')
            )
        )
        with self.assertChecksumChange():
            f1_ordering.delete()
        with self.assertChecksumChange():
            f2_ordering.delete()


class UniqueTogetherDefinitionTest(BaseModelDefinitionTestCase):
    def setUp(self):
        super(UniqueTogetherDefinitionTest, self).setUp()
        with self.assertChecksumChange():
            self.f1 = CharFieldDefinition.objects.create(
                model_def=self.model_def, name='f1', max_length=25
            )
        with self.assertChecksumChange():
            self.f2 = CharFieldDefinition.objects.create(
                model_def=self.model_def, name='f2', max_length=25
            )
        with self.assertChecksumChange():
            self.ut = UniqueTogetherDefinition.objects.create(
                model_def=self.model_def
            )
        self.model_class = self.model_def.model_class()

    def test_repr(self):
        """Make sure UniqueTogetherDefinition objects are always
        repr()-able."""
        repr(self.ut)
        repr(UniqueTogetherDefinition())

    def test_clean(self):
        """Make sure we can't create a unique key with two fields of two
        different models"""
        other_model_def = ModelDefinition.objects.create(
            app_label='app', object_name='OtherModel'
        )
        with self.assertChecksumChange(other_model_def):
            f2 = CharFieldDefinition.objects.create(
                model_def=other_model_def, name='f2', max_length=25
            )
        self.ut.field_defs = (self.f1, f2)
        self.assertRaises(ValidationError, self.ut.clean)
        other_model_def.delete()

    def test_db_column(self):
        """Make sure a unique index creation works correctly when using a
        custom `db_column`. This is needed for unique FK's columns."""
        self.f2.db_column = 'f2_column'
        self.f2.save()
        self.ut.field_defs = (self.f1, self.f2)
        self.f2.db_column = 'f2'
        self.f2.save()
        self.ut.delete()

    def test_cannot_create_unique(self):
        """Creating a unique key on a table with duplicate rows
        shouldn't work"""
        self.model_class.objects.create(f1='a', f2='b')
        self.model_class.objects.create(f1='a', f2='b')
        with captured_stderr():
            with self.assertRaises(IntegrityError):
                self.ut.field_defs = (self.f1, self.f2)

    def test_cannot_insert_duplicate_row(self):
        """Inserting a duplicate rows shouldn't work."""
        self.model_class.objects.create(f1='a', f2='b')
        self.ut.field_defs = (self.f1, self.f2)
        with captured_stderr():
            with self.assertRaises(IntegrityError):
                self.model_class.objects.create(f1='a', f2='b')

    def test_cannot_remove_unique(self):
        """Removing a unique constraint that cause duplicate rows shouldn't
        work."""
        self.ut.field_defs = (self.f1, self.f2)
        self.model_class.objects.create(f1='a', f2='b')
        self.model_class.objects.create(f1='a', f2='c')
        with captured_stderr():
            with self.assertRaises(IntegrityError):
                self.ut.field_defs.remove(self.f2)

    def test_clear_removes_unique(self):
        """
        Removing a unique constraint should relax duplicate row
        validation
        """
        self.model_class.objects.create(f1='a', f2='b')
        self.ut.field_defs = self.f1, self.f2
        self.ut.field_defs.clear()
        self.model_class.objects.create(f1='a', f2='b')


class BaseDefinitionTest(BaseModelDefinitionTestCase):
    def test_clean(self):
        bd = BaseDefinition(model_def=self.model_def)
        # Base must be a class
        bd.base = BaseDefinitionTest.test_clean
        self.assertRaisesMessage(
            ValidationError, _('Base must be a class.'), bd.clean
        )
        # Subclasses of MutableModel are valid bases
        bd.base = ModelDefinition.objects.create(
            app_label='app', object_name='AnotherModel'
        ).model_class()
        try:
            bd.clean()
        except ValidationError:
            self.fail('MutableModel subclasses are valid bases.')
        # But model definition can't be bases of themselves
        bd.base = self.model_def.model_class()
        self.assertRaisesMessage(
            ValidationError,
            _("A model definition can't be a base of itself."),
            bd.clean
        )
        # Mixin objets are valid bases
        bd.base = Mixin
        try:
            bd.clean()
        except ValidationError:
            self.fail('Mixin objets are valid bases.')
        # Abstract model subclasses are valid bases
        bd.base = AbstractModel
        try:
            bd.clean()
        except ValidationError:
            self.fail('Abstract Model are valid bases')
        # Proxy model are not valid bases
        bd.base = ProxyModel
        self.assertRaisesMessage(
            ValidationError, _("Base can't be a proxy model."), bd.clean
        )

    def test_mutable_model_base(self):
        another_model_def = ModelDefinition.objects.create(
            app_label='app', object_name='AnotherModel'
        )
        AnotherModel = another_model_def.model_class()
        auto_pk_column = AnotherModel._meta.pk.get_attname_column()[1]
        self.assertModelTablesColumnExists(AnotherModel, auto_pk_column)
        with self.assertChecksumChange():
            CharFieldDefinition.objects.create(
                model_def=self.model_def, name='f1', max_length=25
            )
        with self.assertChecksumChange(another_model_def):
            base_definition = BaseDefinition(model_def=another_model_def)
            base_definition.base = self.model_def.model_class()
            base_definition.save()
        self.assertModelTablesColumnDoesntExists(AnotherModel, auto_pk_column)
        another_model = AnotherModel.objects.create(f1='Martinal')
        self.assertTrue(AnotherModel.objects.exists())
        with self.assertChecksumChange():
            with self.assertChecksumChange(another_model_def):
                CharFieldDefinition.objects.create(
                    model_def=self.model_def, name='f2', max_length=25,
                    null=True
                )
        another_model = AnotherModel.objects.get(pk=another_model.pk)
        self.assertIsNone(another_model.f2)
        another_model.f2 = 'Placebo'
        another_model.save()

    def test_base_inheritance(self):
        model_class = self.model_def.model_class()
        with self.assertChecksumChange():
            BaseDefinition.objects.create(
                model_def=self.model_def, base=Mixin
            )
        self.assertTrue(issubclass(model_class, Mixin))
        with self.assertChecksumChange():
            BaseDefinition.objects.create(
                model_def=self.model_def, base=AbstractModel
            )
        self.assertTrue(
            issubclass(model_class, Mixin) and
            issubclass(model_class, AbstractModel)
        )

    def test_base_ordering(self):
        model_class = self.model_def.model_class()
        with self.assertChecksumChange():
            mixin_base_def = BaseDefinition.objects.create(
                model_def=self.model_def, base=Mixin
            )
        with self.assertChecksumChange():
            abstract_base_def = BaseDefinition.objects.create(
                model_def=self.model_def, base=AbstractModel
            )
        instance = model_class()
        self.assertEqual('Mixin', instance.method())
        with self.assertChecksumChange():
            mixin_base_def.order = abstract_base_def.order + 1
            mixin_base_def.save(update_fields=['order'])
        instance = model_class()
        self.assertEqual('AbstractModel', instance.method())
        with self.assertChecksumChange():
            abstract_base_def.order = mixin_base_def.order + 1
            abstract_base_def.save(update_fields=['order'])
        instance = model_class()
        self.assertEqual('Mixin', instance.method())

    def test_abstract_field_inherited(self):
        with self.assertChecksumChange():
            bd = BaseDefinition.objects.create(
                model_def=self.model_def, base=AbstractModel
            )
        model_class = self.model_def.model_class()
        model_class.objects.create(abstract_model_field='value')
        # Test column alteration and addition by replacing the base with
        # a new one with a field with the same name and a second field.
        with self.assertChecksumChange():
            bd.base = ModelSubclassWithTextField
            bd.save()
        model_class.objects.get(abstract_model_field='value')
        # The original CharField should be replaced by a TextField with no
        # max_length and a second field should be added
        model_class.objects.create(
            abstract_model_field='another one bites the dust',
            second_field=True
        )
        # Test column deletion by deleting the base
        # This should cause the model to loose all it's fields and the table
        # to loose all it's columns
        with self.assertChecksumChange():
            bd.delete()
        self.assertEqual(
            list(model_class.objects.values_list()), list(
                model_class.objects.values_list('pk')
            )
        )
        self.assertModelTablesColumnDoesntExists(model_class, 'field')

########NEW FILE########
__FILENAME__ = test_state
from __future__ import unicode_literals

import sys
from threading import Thread
import time

# TODO: Remove when support for Python 2.6 is dropped
if sys.version_info >= (2, 7):
    from unittest import skipUnless
else:
    from django.utils.unittest import skipUnless

from mutant.state import handler as state_handler
from mutant.state.handlers.pubsub import engines as pubsub_engines

from .utils import BaseModelDefinitionTestCase

try:
    import redis
except ImportError:
    redis_installed = False
else:
    redis_installed = True


class StateHandlerTestMixin(object):
    def setUp(self):
        super(StateHandlerTestMixin, self).setUp()
        self._state_handler = state_handler.path
        state_handler.path = self.handler_path

    def tearDown(self):
        state_handler.path = self._state_handler
        super(StateHandlerTestMixin, self).tearDown()

    def test_basic_interaction(self):
        self.assertIsNone(state_handler.get_checksum(0))
        checksum = '397fc6229a59429ee114441b780fe7a2'
        state_handler.set_checksum(0, checksum)
        self.assertEqual(state_handler.get_checksum(0), checksum)
        state_handler.clear_checksum(0)
        self.assertIsNone(state_handler.get_checksum(0))


class ChecksumGetter(Thread):
    """Class used to fetch a checksum from a another thread since state
    handler instances are thread local."""

    def __init__(self, definition_pk, *args, **kwargs):
        super(ChecksumGetter, self).__init__(*args, **kwargs)
        self.definition_pk = definition_pk
        self.checksum = None

    def run(self):
        self.checksum = state_handler.get_checksum(self.definition_pk)


class MemoryHandlerTest(StateHandlerTestMixin, BaseModelDefinitionTestCase):
    handler_path = 'mutant.state.handlers.memory.MemoryStateHandler'

    def test_checksum_persistence(self):
        """Make sure checksums are shared between threads."""
        checksum = '397fc6229a59429ee114441b780fe7a2'
        state_handler.set_checksum(0, checksum)
        getter = ChecksumGetter(0)
        getter.start()
        getter.join()
        self.assertEqual(getter.checksum, checksum)
        state_handler.clear_checksum(0)
        getter = ChecksumGetter(0)
        getter.start()
        getter.join()
        self.assertIsNone(getter.checksum)


class CacheHandlerTest(StateHandlerTestMixin, BaseModelDefinitionTestCase):
    handler_path = 'mutant.state.handlers.cache.CacheStateHandler'


@skipUnless(redis_installed, 'This state handler requires redis to be installed.')
class PubsubHandlerTest(MemoryHandlerTest):
    handler_path = 'mutant.state.handlers.pubsub.PubSubStateHandler'

    def test_obsolesence_do_not_clear_checksum(self):
        messages = []

        def add_message(*args):
            messages.append(args)
        engine = pubsub_engines.Redis(add_message)
        model_class = self.model_def.model_class()
        engine.start()
        time.sleep(1)  # Give it some time to subscribe
        model_class.mark_as_obsolete()
        engine.join()
        self.assertEqual(len(messages), 0)

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals

from contextlib import contextmanager

from django.db import connections

from mutant.models.model import ModelDefinition
from mutant.test.testcases import ModelDefinitionDDLTestCase
from mutant.utils import allow_migrate


def table_columns_iterator(db, table_name):
    connection = connections[db]
    cursor = connection.cursor()
    description = connection.introspection.get_table_description(cursor, table_name)
    return (row[0] for row in description)


class BaseModelDefinitionTestCase(ModelDefinitionDDLTestCase):
    def setUp(self):
        self.model_def = ModelDefinition.objects.create(
            app_label='app',
            object_name='Model'
        )

    @contextmanager
    def assertChecksumChange(self, model_def=None):
        model_def = model_def or self.model_def
        checksum = model_def.model_class().checksum()
        yield
        self.assertNotEqual(
            model_def.model_class().checksum(), checksum,
            "Checksum of model %s should have changed." % model_def
        )

    @contextmanager
    def assertChecksumDoesntChange(self, model_def=None):
        try:
            with self.assertChecksumChange(model_def):
                yield
        except AssertionError:
            pass
        else:
            model_class = (model_def or self.model_def).model_class()
            self.fail(
                "Checksum of model %s shouldn't have changed." % model_class
            )

    def assertTableExists(self, db, table):
        tables = connections[db].introspection.table_names()
        msg = "Table '%s.%s' doesn't exist, existing tables are %s"
        self.assertTrue(table in tables, msg % (db, table, tables))

    def assertTableDoesntExists(self, db, table):
        self.assertRaises(AssertionError, self.assertTableExists, db, table)

    def assertModelTablesExist(self, model):
        table = model._meta.db_table
        for db in allow_migrate(model):
            self.assertTableExists(db, table)

    def assertModelTablesDontExist(self, model):
        table = model._meta.db_table
        for db in allow_migrate(model):
            self.assertTableDoesntExists(db, table)

    def assertColumnExists(self, db, table, column):
        columns = tuple(table_columns_iterator(db, table))
        data = {
            'db': db,
            'table': table,
            'column': column,
            'columns': columns
        }
        self.assertIn(column, columns,
                      "Column '%(db)s.%(table)s.%(column)s' doesn't exist, "
                      "%(db)s.'%(table)s's columns are %(columns)s" % data)

    def assertColumnDoesntExists(self, db, table, column):
        self.assertRaises(
            AssertionError, self.assertColumnExists, db, table, column
        )

    def assertModelTablesColumnExists(self, model, column):
        table = model._meta.db_table
        for db in allow_migrate(model):
            self.assertColumnExists(db, table, column)

    def assertModelTablesColumnDoesntExists(self, model, column):
        table = model._meta.db_table
        for db in allow_migrate(model):
            self.assertColumnDoesntExists(db, table, column)

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals

import operator

from contextlib import contextmanager
from copy import deepcopy
from itertools import groupby
import imp
from operator import itemgetter

import django
from django.db import connections, router
from django.db.models.loading import cache as app_cache
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_unicode
from django.utils.functional import lazy, LazyObject, new_method_proxy


# TODO: Remove `allow_syncdb` alternative when support for 1.6 is dropped
if django.VERSION >= (1, 7):
    def allow_migrate(model):
        for db in connections:
            if router.allow_migrate(db, model):
                yield db
else:
    def allow_migrate(model):
        for db in connections:
            if router.allow_syncdb(db, model):
                yield db


NOT_PROVIDED = object()


def popattr(obj, attr, default=NOT_PROVIDED):
    """
    Useful for retrieving an object attr and removing it if it's part of it's
    dict while allowing retrieving from subclass.
    i.e.
    class A:
        a = 'a'
    class B(A):
        b = 'b'
    >>> popattr(B, 'a', None)
    'a'
    >>> A.a
    'a'
    """
    val = getattr(obj, attr, default)
    try:
        delattr(obj, attr)
    except AttributeError:
        if default is NOT_PROVIDED:
            raise
    return val


def _string_format(string, *args, **kwargs):
    if args:
        return string % tuple(force_unicode(s) for s in args)
    elif kwargs:
        return string % dict((k, force_unicode(v)) for k, v in kwargs.iteritems())
lazy_string_format = lazy(_string_format, unicode)


def get_db_table(app_label, model):
    return "mutant_%s_%s" % (app_label, model)


@contextmanager
def app_cache_lock():
    try:
        imp.acquire_lock()
        yield
    finally:
        imp.release_lock()


def remove_from_app_cache(model_class):
    opts = model_class._meta
    app_label, model_name = opts.app_label, opts.object_name.lower()
    with app_cache_lock():
        app_models = app_cache.app_models.get(app_label, False)
        if app_models:
            model = app_models.pop(model_name, False)
            if model:
                app_cache._get_models_cache.clear()
                return model


def _app_cache_deepcopy(obj):
    """
    An helper that correctly deepcopy model cache state
    """
    if isinstance(obj, dict):
        return dict((_app_cache_deepcopy(key), _app_cache_deepcopy(val))
                    for key, val in obj.iteritems())
    elif isinstance(obj, list):
        return list(_app_cache_deepcopy(val) for val in obj)
    elif isinstance(obj, SortedDict):
        return deepcopy(obj)
    return obj


@contextmanager
def app_cache_restorer():
    """
    A context manager that restore model cache state as it was before
    entering context.
    """
    state = _app_cache_deepcopy(app_cache.__dict__)
    try:
        yield state
    finally:
        with app_cache_lock():
            app_cache.__dict__ = state


group_item_getter = itemgetter('group')


def choices_from_dict(choices):
    for grp, choices in groupby(choices, key=group_item_getter):
        if grp is None:
            for choice in choices:
                yield (choice['value'], choice['label'])
        else:
            yield (grp, tuple((choice['value'], choice['label'])
                                for choice in choices))


# TODO: Remove when support for 1.5 is dropped
if django.VERSION >= (1, 6):  # pragma: no cover
    def model_name(opts):
        return opts.model_name
else:  # pragma: no cover
    def model_name(opts):
        return opts.module_name


_opts_related_cache_attrs = [
    '_related_objects_cache', '_related_objects_proxy_cache',
    '_related_many_to_many_cache', '_name_map'
]


def clear_opts_related_cache(model_class):
    """
    Clear the specified model opts related cache
    """
    opts = model_class._meta
    for attr in _opts_related_cache_attrs:
        try:
            delattr(opts, attr)
        except AttributeError:
            pass

# TODO: Remove when support for 1.5 is dropped
if django.VERSION < (1, 6):
    class LazyObject(LazyObject):
        # Dictionary methods support
        __getitem__ = new_method_proxy(operator.getitem)
        __setitem__ = new_method_proxy(operator.setitem)
        __delitem__ = new_method_proxy(operator.delitem)

        __len__ = new_method_proxy(len)
        __contains__ = new_method_proxy(operator.contains)

########NEW FILE########
__FILENAME__ = validators
from __future__ import unicode_literals

import re

from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _


python_identifier_re = re.compile(r'^[a-z_][\w_]*$', re.IGNORECASE)
validate_python_identifier = RegexValidator(python_identifier_re,
                                            _('Enter a valid python identifier.'),
                                            'invalid')

python_object_path_re = re.compile(r'^[a-z_]+(\.[\w_]+)*$', re.IGNORECASE)
validate_python_object_path = RegexValidator(python_object_path_re,
                                             _('Enter a valid python object path.'),
                                             'invalid')

########NEW FILE########
