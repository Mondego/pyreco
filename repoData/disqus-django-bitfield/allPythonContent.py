__FILENAME__ = admin
from django.db.models import F
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin import FieldListFilter
from django.contrib.admin.options import IncorrectLookupParameters

from bitfield import Bit
from bitfield.compat import bitor


class BitFieldListFilter(FieldListFilter):
    """
    BitField list filter.
    """

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg = field_path
        self.lookup_val = int(request.GET.get(self.lookup_kwarg, 0))
        self.flags = field.flags
        self.labels = field.labels
        super(BitFieldListFilter, self).__init__(
            field, request, params, model, model_admin, field_path)

    def queryset(self, request, queryset):
        filter = dict((p, bitor(F(p), v)) for p, v in self.used_parameters.iteritems())
        try:
            return queryset.filter(**filter)
        except ValidationError as e:
            raise IncorrectLookupParameters(e)

    def expected_parameters(self):
        return [self.lookup_kwarg]

    def choices(self, cl):
        yield {
            'selected': self.lookup_val == 0,
            'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
            'display': _('All'),
        }
        for number, flag in enumerate(self.flags):
            bit_mask = Bit(number).mask
            yield {
                'selected': self.lookup_val == bit_mask,
                'query_string': cl.get_query_string({self.lookup_kwarg: bit_mask}),
                'display': self.labels[number],
            }

########NEW FILE########
__FILENAME__ = compat
__all__ = ('bitand', 'bitor')

try:
    from django.db.models.expressions import ExpressionNode
    ExpressionNode.BITAND  # noqa
    del ExpressionNode
except AttributeError:
    # Django < 1.5
    def bitand(a, b):
        return a & b

    def bitor(a, b):
        return a | b
else:
    def bitand(a, b):
        return a.bitand(b)

    def bitor(a, b):
        return a.bitor(b)

########NEW FILE########
__FILENAME__ = forms
from django.forms import CheckboxSelectMultiple, IntegerField, ValidationError
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

from bitfield.types import BitHandler


class BitFieldCheckboxSelectMultiple(CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if isinstance(value, BitHandler):
            value = [k for k, v in value if v]
        return super(BitFieldCheckboxSelectMultiple, self).render(
            name, value, attrs=attrs, choices=enumerate(choices))

    def _has_changed(self, initial, data):
        if initial is None:
            initial = []
        if data is None:
            data = []
        if initial != data:
            return True
        initial_set = set([force_text(value) for value in initial])
        data_set = set([force_text(value) for value in data])
        return data_set != initial_set


class BitFormField(IntegerField):
    def __init__(self, choices=(), widget=BitFieldCheckboxSelectMultiple, *args, **kwargs):
        self.widget = widget
        super(BitFormField, self).__init__(widget=widget, *args, **kwargs)
        self.choices = self.widget.choices = choices

    def clean(self, value):
        if not value:
            return 0

        # Assume an iterable which contains an item per flag that's enabled
        result = BitHandler(0, [k for k, v in self.choices])
        for k in value:
            try:
                setattr(result, str(k), True)
            except AttributeError:
                raise ValidationError('Unknown choice: %r' % (k,))
        return int(result)

########NEW FILE########
__FILENAME__ = models
from django.db.models import signals
from django.db.models.sql.expressions import SQLEvaluator
from django.db.models.fields import Field, BigIntegerField
from django.db.models.fields.subclassing import Creator
try:
    from django.db.models.fields.subclassing import SubfieldBase
except ImportError:
    # django 1.2
    from django.db.models.fields.subclassing import LegacyConnection as SubfieldBase  # NOQA

import six

from bitfield.forms import BitFormField
from bitfield.query import BitQueryLookupWrapper
from bitfield.types import BitHandler, Bit

# Count binary capacity. Truncate "0b" prefix from binary form.
# Twice faster than bin(i)[2:] or math.floor(math.log(i))
MAX_FLAG_COUNT = int(len(bin(BigIntegerField.MAX_BIGINT)) - 2)


class BitFieldFlags(object):
    def __init__(self, flags):
        if len(flags) > MAX_FLAG_COUNT:
            raise ValueError('Too many flags')
        self._flags = flags

    def __repr__(self):
        return repr(self._flags)

    def __iter__(self):
        for flag in self._flags:
            yield flag

    def __getattr__(self, key):
        if key not in self._flags:
            raise AttributeError
        return Bit(self._flags.index(key))

    def iteritems(self):
        for flag in self._flags:
            yield flag, Bit(self._flags.index(flag))

    def iterkeys(self):
        for flag in self._flags:
            yield flag

    def itervalues(self):
        for flag in self._flags:
            yield Bit(self._flags.index(flag))

    def items(self):
        return list(self.iteritems())

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())


class BitFieldCreator(Creator):
    """
    Descriptor for BitFields.  Checks to make sure that all flags of the
    instance match the class.  This is to handle the case when caching
    an older version of the instance and a newer version of the class is
    available (usually during deploys).
    """
    def __get__(self, obj, type=None):
        if obj is None:
            return BitFieldFlags(self.field.flags)
        retval = obj.__dict__[self.field.name]
        if self.field.__class__ is BitField:
            # Update flags from class in case they've changed.
            retval._keys = self.field.flags
        return retval


class BitFieldMeta(SubfieldBase):
    """
    Modified SubFieldBase to use our contribute_to_class method (instead of
    monkey-patching make_contrib).  This uses our BitFieldCreator descriptor
    in place of the default.

    NOTE: If we find ourselves needing custom descriptors for fields, we could
    make this generic.
    """
    def __new__(cls, name, bases, attrs):
        def contribute_to_class(self, cls, name):
            BigIntegerField.contribute_to_class(self, cls, name)
            setattr(cls, self.name, BitFieldCreator(self))

        new_class = super(BitFieldMeta, cls).__new__(cls, name, bases, attrs)
        new_class.contribute_to_class = contribute_to_class
        return new_class


class BitField(six.with_metaclass(BitFieldMeta, BigIntegerField)):
    def __init__(self, flags, default=None, *args, **kwargs):
        if isinstance(flags, dict):
            # Get only integer keys in correct range
            valid_keys = (k for k in flags.keys() if isinstance(k, int) and (0 <= k < MAX_FLAG_COUNT))
            if not valid_keys:
                raise ValueError('Wrong keys or empty dictionary')
            # Fill list with values from dict or with empty values
            flags = [flags.get(i, '') for i in range(max(valid_keys) + 1)]

        if len(flags) > MAX_FLAG_COUNT:
            raise ValueError('Too many flags')

        flags = list(flags)
        labels = []
        for num, flag in enumerate(flags):
            if isinstance(flag, (tuple, list)):
                flags[num] = flag[0]
                labels.append(flag[1])
            else:
                labels.append(flag)

        if isinstance(default, (list, tuple, set, frozenset)):
            new_value = 0
            for flag in default:
                new_value |= Bit(flags.index(flag))
            default = new_value

        BigIntegerField.__init__(self, default=default, *args, **kwargs)
        self.flags = flags
        self.labels = labels

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.BigIntegerField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)

    def formfield(self, form_class=BitFormField, **kwargs):
        choices = [(k, self.labels[self.flags.index(k)]) for k in self.flags]
        return Field.formfield(self, form_class, choices=choices, **kwargs)

    def pre_save(self, instance, add):
        value = getattr(instance, self.attname)
        return value

    def get_prep_value(self, value):
        if isinstance(value, (BitHandler, Bit)):
            value = value.mask
        return int(value)

    # def get_db_prep_save(self, value, connection):
    #     if isinstance(value, Bit):
    #         return BitQuerySaveWrapper(self.model._meta.db_table, self.name, value)
    #     return super(BitField, self).get_db_prep_save(value, connection=connection)

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        if isinstance(value, SQLEvaluator) and isinstance(value.expression, Bit):
            value = value.expression
        if isinstance(value, (BitHandler, Bit)):
            return BitQueryLookupWrapper(self.model._meta.db_table, self.db_column or self.name, value)
        return BigIntegerField.get_db_prep_lookup(self, lookup_type=lookup_type, value=value,
                                                  connection=connection, prepared=prepared)

    def get_prep_lookup(self, lookup_type, value):
        if isinstance(value, SQLEvaluator) and isinstance(value.expression, Bit):
            value = value.expression
        if isinstance(value, Bit):
            if lookup_type in ('exact',):
                return value
            raise TypeError('Lookup type %r not supported with `Bit` type.' % lookup_type)
        return BigIntegerField.get_prep_lookup(self, lookup_type, value)

    def to_python(self, value):
        if isinstance(value, Bit):
            value = value.mask
        if not isinstance(value, BitHandler):
            # Regression for #1425: fix bad data that was created resulting
            # in negative values for flags.  Compute the value that would
            # have been visible ot the application to preserve compatibility.
            if isinstance(value, six.integer_types) and value < 0:
                new_value = 0
                for bit_number, _ in enumerate(self.flags):
                    new_value |= (value & (2 ** bit_number))
                value = new_value

            value = BitHandler(value, self.flags, self.labels)
        else:
            # Ensure flags are consistent for unpickling
            value._keys = self.flags
        return value


class CompositeBitFieldWrapper(object):
    def __init__(self, fields):
        self.fields = fields

    def __getattr__(self, attr):
        if attr == 'fields':
            return super(CompositeBitFieldWrapper, self).__getattr__(attr)

        for field in self.fields:
            if hasattr(field, attr):
                return getattr(field, attr)
        raise AttributeError('%s is not a valid flag' % attr)

    def __hasattr__(self, attr):
        if attr == 'fields':
            return super(CompositeBitFieldWrapper, self).__hasattr__(attr)

        for field in self.fields:
            if hasattr(field, attr):
                return True
        return False

    def __setattr__(self, attr, value):
        if attr == 'fields':
            super(CompositeBitFieldWrapper, self).__setattr__(attr, value)
            return

        for field in self.fields:
            if hasattr(field, attr):
                setattr(field, attr, value)
                return
        raise AttributeError('%s is not a valid flag' % attr)


class CompositeBitField(object):
    def __init__(self, fields):
        self.fields = fields

    def contribute_to_class(self, cls, name):
        self.name = name
        self.model = cls
        cls._meta.add_virtual_field(self)

        signals.class_prepared.connect(self.validate_fields, sender=cls)

        setattr(cls, name, self)

    def validate_fields(self, sender, **kwargs):
        cls = sender
        model_fields = dict([
            (f.name, f) for f in cls._meta.fields if f.name in self.fields])
        all_flags = sum([model_fields[f].flags for f in self.fields], [])
        if len(all_flags) != len(set(all_flags)):
            raise ValueError('BitField flags must be unique.')

    def __get__(self, instance, instance_type=None):
        fields = [getattr(instance, f) for f in self.fields]
        return CompositeBitFieldWrapper(fields)

    def __set__(self, *args, **kwargs):
        raise NotImplementedError('CompositeBitField cannot be set.')

########NEW FILE########
__FILENAME__ = query
class BitQueryLookupWrapper(object):
    def __init__(self, alias, column, bit):
        self.table_alias = alias
        self.column = column
        self.bit = bit

    def as_sql(self, qn, connection=None):
        """
        Create the proper SQL fragment. This inserts something like
        "(T0.flags & value) != 0".

        This will be called by Where.as_sql()
        """
        if self.bit:
            return ("(%s.%s | %d)" % (qn(self.table_alias), qn(self.column), self.bit.mask),
                    [])
        return ("(%s.%s & %d)" % (qn(self.table_alias), qn(self.column), self.bit.mask),
                [])


class BitQuerySaveWrapper(BitQueryLookupWrapper):
    def as_sql(self, qn, connection):
        """
        Create the proper SQL fragment. This inserts something like
        "(T0.flags & value) != 0".

        This will be called by Where.as_sql()
        """
        engine = connection.settings_dict['ENGINE'].rsplit('.', -1)[-1]
        if engine.startswith('postgres'):
            XOR_OPERATOR = '#'
        elif engine.startswith('sqlite'):
            raise NotImplementedError
        else:
            XOR_OPERATOR = '^'

        if self.bit:
            return ("%s.%s | %d" % (qn(self.table_alias), qn(self.column), self.bit.mask),
                    [])
        return ("%s.%s %s %d" % (qn(self.table_alias), qn(self.column), XOR_OPERATOR, self.bit.mask),
                [])

########NEW FILE########
__FILENAME__ = forms
from django import forms
from bitfield.tests.models import BitFieldTestModel, CompositeBitFieldTestModel

class BitFieldTestModelForm(forms.ModelForm):
    
    class Meta:
        model = BitFieldTestModel

########NEW FILE########
__FILENAME__ = models
from django.db import models

from bitfield import BitField, CompositeBitField


class BitFieldTestModel(models.Model):
    flags = BitField(flags=(
        'FLAG_0',
        'FLAG_1',
        'FLAG_2',
        'FLAG_3',
    ), default=3, db_column='another_name')


class CompositeBitFieldTestModel(models.Model):
    flags_1 = BitField(flags=(
        'FLAG_0',
        'FLAG_1',
        'FLAG_2',
        'FLAG_3',
    ), default=0)
    flags_2 = BitField(flags=(
        'FLAG_4',
        'FLAG_5',
        'FLAG_6',
        'FLAG_7',
    ), default=0)
    flags = CompositeBitField((
        'flags_1',
        'flags_2',
    ))

########NEW FILE########
__FILENAME__ = tests
import pickle

from django.db import connection, models
from django.db.models import F
from django.test import TestCase

from bitfield import BitHandler, Bit, BitField
from bitfield.tests import BitFieldTestModel, CompositeBitFieldTestModel, BitFieldTestModelForm
from bitfield.compat import bitand, bitor

try:
    from django.db.models.base import simple_class_factory  # noqa
except ImportError:
    # Django 1.5 muffed up the base class which breaks the pickle tests
    # Note, it's fixed again in 1.6.
    from django.db.models import base
    _model_unpickle = base.model_unpickle

    def simple_class_factory(model, attrs):
        return model

    def model_unpickle(model, attrs, factory):
        return _model_unpickle(model, attrs)
    setattr(base, 'simple_class_factory', simple_class_factory)
    setattr(base, 'model_unpickle', model_unpickle)


class BitHandlerTest(TestCase):
    def test_defaults(self):
        bithandler = BitHandler(0, ('FLAG_0', 'FLAG_1', 'FLAG_2', 'FLAG_3'))
        # Default value of 0.
        self.assertEquals(int(bithandler), 0)
        # Test bit numbers.
        self.assertEquals(int(bithandler.FLAG_0.number), 0)
        self.assertEquals(int(bithandler.FLAG_1.number), 1)
        self.assertEquals(int(bithandler.FLAG_2.number), 2)
        self.assertEquals(int(bithandler.FLAG_3.number), 3)
        # Negative test non-existant key.
        self.assertRaises(AttributeError, lambda: bithandler.FLAG_4)
        # Test bool().
        self.assertEquals(bool(bithandler.FLAG_0), False)
        self.assertEquals(bool(bithandler.FLAG_1), False)
        self.assertEquals(bool(bithandler.FLAG_2), False)
        self.assertEquals(bool(bithandler.FLAG_3), False)

    def test_nonzero_default(self):
        bithandler = BitHandler(1, ('FLAG_0', 'FLAG_1', 'FLAG_2', 'FLAG_3'))
        self.assertEquals(bool(bithandler.FLAG_0), True)
        self.assertEquals(bool(bithandler.FLAG_1), False)
        self.assertEquals(bool(bithandler.FLAG_2), False)
        self.assertEquals(bool(bithandler.FLAG_3), False)

        bithandler = BitHandler(2, ('FLAG_0', 'FLAG_1', 'FLAG_2', 'FLAG_3'))
        self.assertEquals(bool(bithandler.FLAG_0), False)
        self.assertEquals(bool(bithandler.FLAG_1), True)
        self.assertEquals(bool(bithandler.FLAG_2), False)
        self.assertEquals(bool(bithandler.FLAG_3), False)

        bithandler = BitHandler(3, ('FLAG_0', 'FLAG_1', 'FLAG_2', 'FLAG_3'))
        self.assertEquals(bool(bithandler.FLAG_0), True)
        self.assertEquals(bool(bithandler.FLAG_1), True)
        self.assertEquals(bool(bithandler.FLAG_2), False)
        self.assertEquals(bool(bithandler.FLAG_3), False)

        bithandler = BitHandler(4, ('FLAG_0', 'FLAG_1', 'FLAG_2', 'FLAG_3'))
        self.assertEquals(bool(bithandler.FLAG_0), False)
        self.assertEquals(bool(bithandler.FLAG_1), False)
        self.assertEquals(bool(bithandler.FLAG_2), True)
        self.assertEquals(bool(bithandler.FLAG_3), False)

    def test_mutation(self):
        bithandler = BitHandler(0, ('FLAG_0', 'FLAG_1', 'FLAG_2', 'FLAG_3'))
        self.assertEquals(bool(bithandler.FLAG_0), False)
        self.assertEquals(bool(bithandler.FLAG_1), False)
        self.assertEquals(bool(bithandler.FLAG_2), False)
        self.assertEquals(bool(bithandler.FLAG_3), False)

        bithandler = BitHandler(bithandler | 1, bithandler._keys)
        self.assertEquals(bool(bithandler.FLAG_0), True)
        self.assertEquals(bool(bithandler.FLAG_1), False)
        self.assertEquals(bool(bithandler.FLAG_2), False)
        self.assertEquals(bool(bithandler.FLAG_3), False)

        bithandler ^= 3
        self.assertEquals(int(bithandler), 2)

        self.assertEquals(bool(bithandler & 1), False)

        bithandler.FLAG_0 = False
        self.assertEquals(bithandler.FLAG_0, False)

        bithandler.FLAG_1 = True
        self.assertEquals(bithandler.FLAG_0, False)
        self.assertEquals(bithandler.FLAG_1, True)

        bithandler.FLAG_2 = False
        self.assertEquals(bithandler.FLAG_0, False)
        self.assertEquals(bithandler.FLAG_1, True)
        self.assertEquals(bithandler.FLAG_2, False)


class BitTest(TestCase):
    def test_int(self):
        bit = Bit(0)
        self.assertEquals(int(bit), 1)
        self.assertEquals(bool(bit), True)
        self.assertFalse(not bit)

    def test_comparison(self):
        self.assertEquals(Bit(0), Bit(0))
        self.assertNotEquals(Bit(1), Bit(0))
        self.assertNotEquals(Bit(0, 0), Bit(0, 1))
        self.assertEquals(Bit(0, 1), Bit(0, 1))
        self.assertEquals(Bit(0), 1)

    def test_and(self):
        self.assertEquals(1 & Bit(2), 0)
        self.assertEquals(1 & Bit(0), 1)
        self.assertEquals(1 & ~Bit(0), 0)
        self.assertEquals(Bit(0) & Bit(2), 0)
        self.assertEquals(Bit(0) & Bit(0), 1)
        self.assertEquals(Bit(0) & ~Bit(0), 0)

    def test_or(self):
        self.assertEquals(1 | Bit(2), 5)
        self.assertEquals(1 | Bit(5), 33)
        self.assertEquals(1 | ~Bit(2), -5)
        self.assertEquals(Bit(0) | Bit(2), 5)
        self.assertEquals(Bit(0) | Bit(5), 33)
        self.assertEquals(Bit(0) | ~Bit(2), -5)

    def test_xor(self):
        self.assertEquals(1 ^ Bit(2), 5)
        self.assertEquals(1 ^ Bit(0), 0)
        self.assertEquals(1 ^ Bit(1), 3)
        self.assertEquals(1 ^ Bit(5), 33)
        self.assertEquals(1 ^ ~Bit(2), -6)
        self.assertEquals(Bit(0) ^ Bit(2), 5)
        self.assertEquals(Bit(0) ^ Bit(0), 0)
        self.assertEquals(Bit(0) ^ Bit(1), 3)
        self.assertEquals(Bit(0) ^ Bit(5), 33)
        self.assertEquals(Bit(0) ^ ~Bit(2), -6)


class BitFieldTest(TestCase):
    def test_basic(self):
        # Create instance and make sure flags are working properly.
        instance = BitFieldTestModel.objects.create(flags=1)
        self.assertTrue(instance.flags.FLAG_0)
        self.assertFalse(instance.flags.FLAG_1)
        self.assertFalse(instance.flags.FLAG_2)
        self.assertFalse(instance.flags.FLAG_3)

    def test_regression_1425(self):
        # Creating new instances shouldn't allow negative values.
        instance = BitFieldTestModel.objects.create(flags=-1)
        self.assertEqual(instance.flags._value, 15)
        self.assertTrue(instance.flags.FLAG_0)
        self.assertTrue(instance.flags.FLAG_1)
        self.assertTrue(instance.flags.FLAG_2)
        self.assertTrue(instance.flags.FLAG_3)

        cursor = connection.cursor()
        flags_field = BitFieldTestModel._meta.get_field_by_name('flags')[0]
        flags_db_column = flags_field.db_column or flags_field.name
        cursor.execute("INSERT INTO %s (%s) VALUES (-1)" % (BitFieldTestModel._meta.db_table, flags_db_column))
        # There should only be the one row we inserted through the cursor.
        instance = BitFieldTestModel.objects.get(flags=-1)
        self.assertTrue(instance.flags.FLAG_0)
        self.assertTrue(instance.flags.FLAG_1)
        self.assertTrue(instance.flags.FLAG_2)
        self.assertTrue(instance.flags.FLAG_3)
        instance.save()

        self.assertEqual(BitFieldTestModel.objects.filter(flags=15).count(), 2)
        self.assertEqual(BitFieldTestModel.objects.filter(flags__lt=0).count(), 0)

    def test_select(self):
        BitFieldTestModel.objects.create(flags=3)
        self.assertTrue(BitFieldTestModel.objects.filter(flags=BitFieldTestModel.flags.FLAG_1).exists())
        self.assertTrue(BitFieldTestModel.objects.filter(flags=BitFieldTestModel.flags.FLAG_0).exists())
        self.assertFalse(BitFieldTestModel.objects.exclude(flags=BitFieldTestModel.flags.FLAG_0).exists())
        self.assertFalse(BitFieldTestModel.objects.exclude(flags=BitFieldTestModel.flags.FLAG_1).exists())

    def test_update(self):
        instance = BitFieldTestModel.objects.create(flags=0)
        self.assertFalse(instance.flags.FLAG_0)

        BitFieldTestModel.objects.filter(pk=instance.pk).update(flags=bitor(F('flags'), BitFieldTestModel.flags.FLAG_1))
        instance = BitFieldTestModel.objects.get(pk=instance.pk)
        self.assertTrue(instance.flags.FLAG_1)

        BitFieldTestModel.objects.filter(pk=instance.pk).update(flags=bitor(F('flags'), ((~BitFieldTestModel.flags.FLAG_0 | BitFieldTestModel.flags.FLAG_3))))
        instance = BitFieldTestModel.objects.get(pk=instance.pk)
        self.assertFalse(instance.flags.FLAG_0)
        self.assertTrue(instance.flags.FLAG_1)
        self.assertTrue(instance.flags.FLAG_3)
        self.assertFalse(BitFieldTestModel.objects.filter(flags=BitFieldTestModel.flags.FLAG_0).exists())

        BitFieldTestModel.objects.filter(pk=instance.pk).update(flags=bitand(F('flags'), ~BitFieldTestModel.flags.FLAG_3))
        instance = BitFieldTestModel.objects.get(pk=instance.pk)
        self.assertFalse(instance.flags.FLAG_0)
        self.assertTrue(instance.flags.FLAG_1)
        self.assertFalse(instance.flags.FLAG_3)

    def test_update_with_handler(self):
        instance = BitFieldTestModel.objects.create(flags=0)
        self.assertFalse(instance.flags.FLAG_0)

        instance.flags.FLAG_1 = True

        BitFieldTestModel.objects.filter(pk=instance.pk).update(flags=bitor(F('flags'), instance.flags))
        instance = BitFieldTestModel.objects.get(pk=instance.pk)
        self.assertTrue(instance.flags.FLAG_1)

    def test_negate(self):
        BitFieldTestModel.objects.create(flags=BitFieldTestModel.flags.FLAG_0 | BitFieldTestModel.flags.FLAG_1)
        BitFieldTestModel.objects.create(flags=BitFieldTestModel.flags.FLAG_1)
        self.assertEqual(BitFieldTestModel.objects.filter(flags=~BitFieldTestModel.flags.FLAG_0).count(), 1)
        self.assertEqual(BitFieldTestModel.objects.filter(flags=~BitFieldTestModel.flags.FLAG_1).count(), 0)
        self.assertEqual(BitFieldTestModel.objects.filter(flags=~BitFieldTestModel.flags.FLAG_2).count(), 2)

    def test_default_value(self):
        instance = BitFieldTestModel.objects.create()
        self.assertTrue(instance.flags.FLAG_0)
        self.assertTrue(instance.flags.FLAG_1)
        self.assertFalse(instance.flags.FLAG_2)
        self.assertFalse(instance.flags.FLAG_3)

    def test_binary_capacity(self):
        import math
        from django.db.models.fields import BigIntegerField
        # Local maximum value, slow canonical algorithm
        MAX_COUNT = int(math.floor(math.log(BigIntegerField.MAX_BIGINT, 2)))

        # Big flags list
        flags = ['f' + str(i) for i in range(100)]

        try:
            BitField(flags=flags[:MAX_COUNT])
        except ValueError:
            self.fail("It should work well with these flags")

        self.assertRaises(ValueError, BitField, flags=flags[:(MAX_COUNT + 1)])

    def test_dictionary_init(self):
        flags = {
            0: 'zero',
            1: 'first',
            10: 'tenth',
            2: 'second',

            'wrongkey': 'wrongkey',
            100: 'bigkey',
            -100: 'smallkey',
        }

        try:
            bf = BitField(flags)
        except ValueError:
            self.fail("It should work well with these flags")

        self.assertEquals(bf.flags, ['zero', 'first', 'second', '', '', '', '', '', '', '', 'tenth'])
        self.assertRaises(ValueError, BitField, flags={})
        self.assertRaises(ValueError, BitField, flags={'wrongkey': 'wrongkey'})
        self.assertRaises(ValueError, BitField, flags={'1': 'non_int_key'})

    def test_defaults_as_key_names(self):
        class TestModel(models.Model):
            flags = BitField(flags=(
                'FLAG_0',
                'FLAG_1',
                'FLAG_2',
                'FLAG_3',
            ), default=('FLAG_1', 'FLAG_2'))
        field = TestModel._meta.get_field('flags')
        self.assertEquals(field.default, TestModel.flags.FLAG_1 | TestModel.flags.FLAG_2)


class BitFieldSerializationTest(TestCase):
    def test_can_unserialize_bithandler(self):
        data = b"cdjango.db.models.base\nmodel_unpickle\np0\n(cbitfield.tests.models\nBitFieldTestModel\np1\n(lp2\ncdjango.db.models.base\nsimple_class_factory\np3\ntp4\nRp5\n(dp6\nS'flags'\np7\nccopy_reg\n_reconstructor\np8\n(cbitfield.types\nBitHandler\np9\nc__builtin__\nobject\np10\nNtp11\nRp12\n(dp13\nS'_value'\np14\nI1\nsS'_keys'\np15\n(S'FLAG_0'\np16\nS'FLAG_1'\np17\nS'FLAG_2'\np18\nS'FLAG_3'\np19\ntp20\nsbsS'_state'\np21\ng8\n(cdjango.db.models.base\nModelState\np22\ng10\nNtp23\nRp24\n(dp25\nS'adding'\np26\nI00\nsS'db'\np27\nS'default'\np28\nsbsS'id'\np29\nI1\nsb."

        inst = pickle.loads(data)
        self.assertTrue(inst.flags.FLAG_0)
        self.assertFalse(inst.flags.FLAG_1)

    def test_pickle_integration(self):
        inst = BitFieldTestModel.objects.create(flags=1)
        data = pickle.dumps(inst)
        inst = pickle.loads(data)
        self.assertEquals(type(inst.flags), BitHandler)
        self.assertEquals(int(inst.flags), 1)

    def test_added_field(self):
        data = b"cdjango.db.models.base\nmodel_unpickle\np0\n(cbitfield.tests.models\nBitFieldTestModel\np1\n(lp2\ncdjango.db.models.base\nsimple_class_factory\np3\ntp4\nRp5\n(dp6\nS'flags'\np7\nccopy_reg\n_reconstructor\np8\n(cbitfield.types\nBitHandler\np9\nc__builtin__\nobject\np10\nNtp11\nRp12\n(dp13\nS'_value'\np14\nI1\nsS'_keys'\np15\n(S'FLAG_0'\np16\nS'FLAG_1'\np17\nS'FLAG_2'\np18\ntp19\nsbsS'_state'\np20\ng8\n(cdjango.db.models.base\nModelState\np21\ng10\nNtp22\nRp23\n(dp24\nS'adding'\np25\nI00\nsS'db'\np27\nS'default'\np27\nsbsS'id'\np28\nI1\nsb."

        inst = pickle.loads(data)
        self.assertTrue('FLAG_3' in inst.flags.keys())


class CompositeBitFieldTest(TestCase):
    def test_get_flag(self):
        inst = CompositeBitFieldTestModel()
        self.assertEqual(inst.flags.FLAG_0, inst.flags_1.FLAG_0)
        self.assertEqual(inst.flags.FLAG_4, inst.flags_2.FLAG_4)
        self.assertRaises(AttributeError, lambda: inst.flags.flag_NA)

    def test_set_flag(self):
        inst = CompositeBitFieldTestModel()

        flag_0_original = bool(inst.flags.FLAG_0)
        self.assertEqual(bool(inst.flags_1.FLAG_0), flag_0_original)
        flag_4_original = bool(inst.flags.FLAG_4)
        self.assertEqual(bool(inst.flags_2.FLAG_4), flag_4_original)

        # flip flags' bits
        inst.flags.FLAG_0 = not flag_0_original
        inst.flags.FLAG_4 = not flag_4_original

        # check to make sure the bit flips took effect
        self.assertNotEqual(bool(inst.flags.FLAG_0), flag_0_original)
        self.assertNotEqual(bool(inst.flags_1.FLAG_0), flag_0_original)
        self.assertNotEqual(bool(inst.flags.FLAG_4), flag_4_original)
        self.assertNotEqual(bool(inst.flags_2.FLAG_4), flag_4_original)

        def set_flag():
            inst.flags.flag_NA = False
        self.assertRaises(AttributeError, set_flag)

    def test_hasattr(self):
        inst = CompositeBitFieldTestModel()
        self.assertEqual(hasattr(inst.flags, 'flag_0'),
            hasattr(inst.flags_1, 'flag_0'))
        self.assertEqual(hasattr(inst.flags, 'flag_4'),
            hasattr(inst.flags_2, 'flag_4'))


class BitFormFieldTest(TestCase):
    def test_form_new_invalid(self):
        invalid_data_dicts = [
            {'flags': ['FLAG_0', 'FLAG_FLAG']},
            {'flags': ['FLAG_4']},
            {'flags': [1, 2]}
        ]
        for invalid_data in invalid_data_dicts:
            form = BitFieldTestModelForm(data=invalid_data)
            self.assertFalse(form.is_valid())

    def test_form_new(self):
        data_dicts = [
            {'flags': ['FLAG_0', 'FLAG_1']},
            {'flags': ['FLAG_3']},
            {'flags': []},
            {}
        ]
        for data in data_dicts:
            form = BitFieldTestModelForm(data=data)
            self.failUnless(form.is_valid())
            instance = form.save()
            flags = data['flags'] if 'flags' in data else []
            for k in BitFieldTestModel.flags:
                self.assertEquals(bool(getattr(instance.flags, k)), k in flags)

    def test_form_update(self):
        instance = BitFieldTestModel.objects.create(flags=0)
        for k in BitFieldTestModel.flags:
            self.assertFalse(bool(getattr(instance.flags, k)))

        data = {'flags': ['FLAG_0', 'FLAG_1']}
        form = BitFieldTestModelForm(data=data, instance=instance)
        self.failUnless(form.is_valid())
        instance = form.save()
        for k in BitFieldTestModel.flags:
            self.assertEquals(bool(getattr(instance.flags, k)), k in data['flags'])

        data = {'flags': ['FLAG_2', 'FLAG_3']}
        form = BitFieldTestModelForm(data=data, instance=instance)
        self.failUnless(form.is_valid())
        instance = form.save()
        for k in BitFieldTestModel.flags:
            self.assertEquals(bool(getattr(instance.flags, k)), k in data['flags'])

        data = {'flags': []}
        form = BitFieldTestModelForm(data=data, instance=instance)
        self.failUnless(form.is_valid())
        instance = form.save()
        for k in BitFieldTestModel.flags:
            self.assertFalse(bool(getattr(instance.flags, k)))

########NEW FILE########
__FILENAME__ = types
class Bit(object):
    """
    Represents a single Bit.
    """
    def __init__(self, number, is_set=True):
        self.number = number
        self.is_set = bool(is_set)
        self.mask = 2 ** int(number)
        self.children = []
        if not self.is_set:
            self.mask = ~self.mask

    def __repr__(self):
        return '<%s: number=%d, is_set=%s>' % (self.__class__.__name__, self.number, self.is_set)

    # def __str__(self):
    #     if self.is_set:
    #         return 'Yes'
    #     return 'No'

    def __int__(self):
        return self.mask

    def __bool__(self):
        return self.is_set

    __nonzero__ = __bool__

    def __eq__(self, value):
        if isinstance(value, Bit):
            return value.number == self.number and value.is_set == self.is_set
        elif isinstance(value, bool):
            return value == self.is_set
        elif isinstance(value, int):
            return value == self.mask
        return value == self.is_set

    def __ne__(self, value):
        return not self == value

    def __coerce__(self, value):
        return (self.is_set, bool(value))

    def __invert__(self):
        return self.__class__(self.number, not self.is_set)

    def __and__(self, value):
        if isinstance(value, Bit):
            value = value.mask
        return value & self.mask

    def __rand__(self, value):
        if isinstance(value, Bit):
            value = value.mask
        return self.mask & value

    def __or__(self, value):
        if isinstance(value, Bit):
            value = value.mask
        return value | self.mask

    def __ror__(self, value):
        if isinstance(value, Bit):
            value = value.mask
        return self.mask | value

    def __lshift__(self, value):
        if isinstance(value, Bit):
            value = value.mask
        return value << self.mask

    def __rlshift__(self, value):
        if isinstance(value, Bit):
            value = value.mask
        return self.mask << value

    def __rshift__(self, value):
        if isinstance(value, Bit):
            value = value.mask
        return value >> self.mask

    def __rrshift__(self, value):
        if isinstance(value, Bit):
            value = value.mask
        return self.mask >> value

    def __xor__(self, value):
        if isinstance(value, Bit):
            value = value.mask
        return value ^ self.mask

    def __rxor__(self, value):
        if isinstance(value, Bit):
            value = value.mask
        return self.mask ^ value

    def __sentry__(self):
        return repr(self)

    def evaluate(self, evaluator, qn, connection):
        return self.mask, []

    def prepare(self, evaluator, query, allow_joins):
        return evaluator.prepare_node(self, query, allow_joins)


class BitHandler(object):
    """
    Represents an array of bits, each as a ``Bit`` object.
    """
    def __init__(self, value, keys, labels=None):
        # TODO: change to bitarray?
        if value:
            self._value = int(value)
        else:
            self._value = 0
        self._keys = keys
        self._labels = labels is not None and labels or keys

    def __eq__(self, other):
        if not isinstance(other, BitHandler):
            return False
        return self._value == other._value

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, ', '.join('%s=%s' % (k, self.get_bit(n).is_set) for n, k in enumerate(self._keys)),)

    def __str__(self):
        return str(self._value)

    def __int__(self):
        return self._value

    def __bool__(self):
        return bool(self._value)

    __nonzero__ = __bool__

    def __and__(self, value):
        return BitHandler(self._value & int(value), self._keys)

    def __or__(self, value):
        return BitHandler(self._value | int(value), self._keys)

    def __add__(self, value):
        return BitHandler(self._value + int(value), self._keys)

    def __sub__(self, value):
        return BitHandler(self._value - int(value), self._keys)

    def __lshift__(self, value):
        return BitHandler(self._value << int(value), self._keys)

    def __rshift__(self, value):
        return BitHandler(self._value >> int(value), self._keys)

    def __xor__(self, value):
        return BitHandler(self._value ^ int(value), self._keys)

    def __contains__(self, key):
        bit_number = self._keys.index(key)
        return bool(self.get_bit(bit_number))

    def __getattr__(self, key):
        if key.startswith('_'):
            return object.__getattribute__(self, key)
        if key not in self._keys:
            raise AttributeError('%s is not a valid flag' % key)
        return self.get_bit(self._keys.index(key))

    def __setattr__(self, key, value):
        if key.startswith('_'):
            return object.__setattr__(self, key, value)
        if key not in self._keys:
            raise AttributeError('%s is not a valid flag' % key)
        self.set_bit(self._keys.index(key), value)

    def __iter__(self):
        return self.iteritems()

    def __sentry__(self):
        return repr(self)

    def _get_mask(self):
        return self._value
    mask = property(_get_mask)

    def evaluate(self, evaluator, qn, connection):
        return self.mask, []

    def get_bit(self, bit_number):
        mask = 2 ** int(bit_number)
        return Bit(bit_number, self._value & mask != 0)

    def set_bit(self, bit_number, true_or_false):
        mask = 2 ** int(bit_number)
        if true_or_false:
            self._value |= mask
        else:
            self._value &= (~mask)
        return Bit(bit_number, self._value & mask != 0)

    def keys(self):
        return self._keys

    def iterkeys(self):
        return iter(self._keys)

    def items(self):
        return list(self.iteritems())

    def iteritems(self):
        for k in self._keys:
            yield (k, getattr(self, k).is_set)

    def get_label(self, flag):
        if isinstance(flag, basestring):
            flag = self._keys.index(flag)
        if isinstance(flag, Bit):
            flag = flag.number
        return self._labels[flag]

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys
from optparse import OptionParser

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'bitfield_test',
                'USER': 'postgres',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'bitfield',
            'bitfield.tests',
        ],
        ROOT_URLCONF='',
        DEBUG=False,
    )


from django_nose import NoseTestSuiteRunner


def runtests(*test_args, **kwargs):
    if 'south' in settings.INSTALLED_APPS:
        from south.management.commands import patch_for_test_db_setup
        patch_for_test_db_setup()

    if not test_args:
        test_args = ['bitfield']

    test_runner = NoseTestSuiteRunner(**kwargs)

    failures = test_runner.run_tests(test_args)
    sys.exit(failures)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--verbosity', dest='verbosity', action='store', default=1, type=int)
    parser.add_options(NoseTestSuiteRunner.options)
    (options, args) = parser.parse_args()

    runtests(*args, **options.__dict__)

########NEW FILE########
