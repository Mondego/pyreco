__FILENAME__ = fields
import copy
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import ugettext_lazy as _
try:
    from django.utils import six
except ImportError:
    import six

try:
    import json
except ImportError:
    from django.utils import simplejson as json

from django.forms import fields
try:
    from django.forms.utils import ValidationError
except ImportError:
    from django.forms.util import ValidationError

from .subclassing import SubfieldBase


class JSONFormFieldBase(object):

    def to_python(self, value):
        if isinstance(value, six.string_types):
            try:
                return json.loads(value, **self.load_kwargs)
            except ValueError:
                raise ValidationError(_("Enter valid JSON"))
        return value

    def clean(self, value):

        if not value and not self.required:
            return None

        # Trap cleaning errors & bubble them up as JSON errors
        try:
            return super(JSONFormFieldBase, self).clean(value)
        except TypeError:
            raise ValidationError(_("Enter valid JSON"))


class JSONFormField(JSONFormFieldBase, fields.Field):
    pass

class JSONCharFormField(JSONFormFieldBase, fields.CharField):
    pass


class JSONFieldBase(six.with_metaclass(SubfieldBase, models.Field)):

    def __init__(self, *args, **kwargs):
        self.dump_kwargs = kwargs.pop('dump_kwargs', {
            'cls': DjangoJSONEncoder,
            'separators': (',', ':')
        })
        self.load_kwargs = kwargs.pop('load_kwargs', {})

        super(JSONFieldBase, self).__init__(*args, **kwargs)

    def pre_init(self, value, obj):
        """Convert a string value to JSON only if it needs to be deserialized.

        SubfieldBase meteaclass has been modified to call this method instead of
        to_python so that we can check the obj state and determine if it needs to be
        deserialized"""

        if obj._state.adding:
            # Make sure the primary key actually exists on the object before
            # checking if it's empty. This is a special case for South datamigrations
            # see: https://github.com/bradjasper/django-jsonfield/issues/52
            if not hasattr(obj, "pk") or obj.pk is not None:
                if isinstance(value, six.string_types):
                    try:
                        return json.loads(value, **self.load_kwargs)
                    except ValueError:
                        raise ValidationError(_("Enter valid JSON"))

        return value

    def to_python(self, value):
        """The SubfieldBase metaclass calls pre_init instead of to_python, however to_python
        is still necessary for Django's deserializer"""
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        """Convert JSON object to a string"""
        if self.null and value is None:
            return None
        return json.dumps(value, **self.dump_kwargs)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value, None)

    def value_from_object(self, obj):
        value = super(JSONFieldBase, self).value_from_object(obj)
        if self.null and value is None:
            return None
        return self.dumps_for_display(value)

    def dumps_for_display(self, value):
        return json.dumps(value, **self.dump_kwargs)

    def formfield(self, **kwargs):

        if "form_class" not in kwargs:
            kwargs["form_class"] = self.form_class

        field = super(JSONFieldBase, self).formfield(**kwargs)

        if isinstance(field, JSONFormFieldBase):
            field.load_kwargs = self.load_kwargs

        if not field.help_text:
            field.help_text = "Enter valid JSON"

        return field

    def get_default(self):
        """
        Returns the default value for this field.

        The default implementation on models.Field calls force_unicode
        on the default, which means you can't set arbitrary Python
        objects as the default. To fix this, we just return the value
        without calling force_unicode on it. Note that if you set a
        callable as a default, the field will still call it. It will
        *not* try to pickle and encode it.

        """
        if self.has_default():
            if callable(self.default):
                return self.default()
            return copy.deepcopy(self.default)
        # If the field doesn't have a default, then we punt to models.Field.
        return super(JSONFieldBase, self).get_default()

    def db_type(self, connection):
        if connection.vendor == 'postgresql' and connection.pg_version >= 90300:
            return 'json'
        else:
            return super(JSONFieldBase, self).db_type(connection)

class JSONField(JSONFieldBase, models.TextField):
    """JSONField is a generic textfield that serializes/unserializes JSON objects"""
    form_class = JSONFormField

    def dumps_for_display(self, value):
        kwargs = { "indent": 2 }
        kwargs.update(self.dump_kwargs)
        return json.dumps(value, **kwargs)


class JSONCharField(JSONFieldBase, models.CharField):
    """JSONCharField is a generic textfield that serializes/unserializes JSON objects,
    stored in the database like a CharField, which enables it to be used
    e.g. in unique keys"""
    form_class = JSONCharFormField


try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^jsonfield\.fields\.(JSONField|JSONCharField)"])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = models
# Django needs this to see it as a project

########NEW FILE########
__FILENAME__ = subclassing
## This file was copied from django.db.models.fields.subclassing so that we could
## change the Creator.__set__ behavior. Read the comment below for full details.

"""
Convenience routines for creating non-trivial Field subclasses, as well as
backwards compatibility utilities.

Add SubfieldBase as the __metaclass__ for your Field subclass, implement
to_python() and the other necessary methods and everything will work seamlessly.
"""

class SubfieldBase(type):
    """
    A metaclass for custom Field subclasses. This ensures the model's attribute
    has the descriptor protocol attached to it.
    """
    def __new__(cls, name, bases, attrs):
        new_class = super(SubfieldBase, cls).__new__(cls, name, bases, attrs)
        new_class.contribute_to_class = make_contrib(
            new_class, attrs.get('contribute_to_class')
        )
        return new_class

class Creator(object):
    """
    A placeholder class that provides a way to set the attribute on the model.
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, obj, type=None):
        if obj is None:
            raise AttributeError('Can only be accessed via an instance.')
        return obj.__dict__[self.field.name]

    def __set__(self, obj, value):
        # Usually this would call to_python, but we've changed it to pre_init
        # so that we can tell which state we're in. By passing an obj,
        # we can definitively tell if a value has already been deserialized
        # More: https://github.com/bradjasper/django-jsonfield/issues/33
        obj.__dict__[self.field.name] = self.field.pre_init(value, obj)


def make_contrib(superclass, func=None):
    """
    Returns a suitable contribute_to_class() method for the Field subclass.

    If 'func' is passed in, it is the existing contribute_to_class() method on
    the subclass and it is called before anything else. It is assumed in this
    case that the existing contribute_to_class() calls all the necessary
    superclass methods.
    """
    def contribute_to_class(self, cls, name):
        if func:
            func(self, cls, name)
        else:
            super(superclass, self).contribute_to_class(cls, name)
        setattr(cls, self.name, Creator(self))

    return contribute_to_class

########NEW FILE########
__FILENAME__ = tests
from decimal import Decimal
from django.core.serializers import deserialize, serialize
from django.core.serializers.base import DeserializationError
from django.db import models
from django.test import TestCase
from django.utils import simplejson as json

from .fields import JSONField, JSONCharField
from django.forms.util import ValidationError

from collections import OrderedDict

class JsonModel(models.Model):
    json = JSONField()
    default_json = JSONField(default={"check":12})
    complex_default_json = JSONField(default=[{"checkcheck": 1212}])
    empty_default = JSONField(default={})

class JsonCharModel(models.Model):
    json = JSONCharField(max_length=100)
    default_json = JSONCharField(max_length=100, default={"check":34})

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, complex):
            return {
                '__complex__': True,
                'real': obj.real,
                'imag': obj.imag,
            }

        return json.JSONEncoder.default(self, obj)

def as_complex(dct):
    if '__complex__' in dct:
        return complex(dct['real'], dct['imag'])
    return dct

class JSONModelCustomEncoders(models.Model):
    # A JSON field that can store complex numbers
    json = JSONField(
        dump_kwargs={'cls': ComplexEncoder, "indent": 4},
        load_kwargs={'object_hook': as_complex},
    )

class JSONFieldTest(TestCase):
    """JSONField Wrapper Tests"""

    json_model = JsonModel

    def test_json_field_create(self):
        """Test saving a JSON object in our JSONField"""
        json_obj = {
            "item_1": "this is a json blah",
            "blergh": "hey, hey, hey"}

        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_string_in_json_field(self):
        """Test saving an ordinary Python string in our JSONField"""
        json_obj = 'blah blah'
        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_float_in_json_field(self):
        """Test saving a Python float in our JSONField"""
        json_obj = 1.23
        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_int_in_json_field(self):
        """Test saving a Python integer in our JSONField"""
        json_obj = 1234567
        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_decimal_in_json_field(self):
        """Test saving a Python Decimal in our JSONField"""
        json_obj = Decimal(12.34)
        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        # here we must know to convert the returned string back to Decimal,
        # since json does not support that format
        self.assertEqual(Decimal(new_obj.json), json_obj)

    def test_json_field_modify(self):
        """Test modifying a JSON object in our JSONField"""
        json_obj_1 = {'a': 1, 'b': 2}
        json_obj_2 = {'a': 3, 'b': 4}

        obj = self.json_model.objects.create(json=json_obj_1)
        self.assertEqual(obj.json, json_obj_1)
        obj.json = json_obj_2

        self.assertEqual(obj.json, json_obj_2)
        obj.save()
        self.assertEqual(obj.json, json_obj_2)

        self.assertTrue(obj)

    def test_json_field_load(self):
        """Test loading a JSON object from the DB"""
        json_obj_1 = {'a': 1, 'b': 2}
        obj = self.json_model.objects.create(json=json_obj_1)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj_1)

    def test_json_list(self):
        """Test storing a JSON list"""
        json_obj = ["my", "list", "of", 1, "objs", {"hello": "there"}]

        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)
        self.assertEqual(new_obj.json, json_obj)

    def test_empty_objects(self):
        """Test storing empty objects"""
        for json_obj in [{}, [], 0, '', False]:
            obj = self.json_model.objects.create(json=json_obj)
            new_obj = self.json_model.objects.get(id=obj.id)
            self.assertEqual(json_obj, obj.json)
            self.assertEqual(json_obj, new_obj.json)

    def test_custom_encoder(self):
        """Test encoder_cls and object_hook"""
        value = 1 + 3j  # A complex number

        obj = JSONModelCustomEncoders.objects.create(json=value)
        new_obj = JSONModelCustomEncoders.objects.get(pk=obj.pk)
        self.assertEqual(value, new_obj.json)

    def test_django_serializers(self):
        """Test serializing/deserializing jsonfield data"""
        for json_obj in [{}, [], 0, '', False, {'key': 'value', 'num': 42,
                                                'ary': list(range(5)),
                                                'dict': {'k': 'v'}}]:
            obj = self.json_model.objects.create(json=json_obj)
            new_obj = self.json_model.objects.get(id=obj.id)
            self.assert_(new_obj)

        queryset = self.json_model.objects.all()
        ser = serialize('json', queryset)
        for dobj in deserialize('json', ser):
            obj = dobj.object
            pulled = self.json_model.objects.get(id=obj.pk)
            self.assertEqual(obj.json, pulled.json)

    def test_default_parameters(self):
        """Test providing a default value to the model"""
        model = JsonModel()
        model.json = {"check": 12}
        self.assertEqual(model.json, {"check": 12})
        self.assertEqual(type(model.json), dict)

        self.assertEqual(model.default_json, {"check": 12})
        self.assertEqual(type(model.default_json), dict)

    def test_invalid_json(self):
        # invalid json data {] in the json and default_json fields
        ser = '[{"pk": 1, "model": "jsonfield.jsoncharmodel", ' \
            '"fields": {"json": "{]", "default_json": "{]"}}]'
        with self.assertRaises(DeserializationError) as cm:
            next(deserialize('json', ser))
        inner = cm.exception.args[0]
        self.assertTrue(isinstance(inner, ValidationError))
        self.assertEqual('Enter valid JSON', inner.messages[0])

    def test_integer_in_string_in_json_field(self):
        """Test saving the Python string '123' in our JSONField"""
        json_obj = '123'
        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_boolean_in_string_in_json_field(self):
        """Test saving the Python string 'true' in our JSONField"""
        json_obj = 'true'
        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)


    def test_pass_by_reference_pollution(self):
        """Make sure the default parameter is copied rather than passed by reference"""
        model = JsonModel()
        model.default_json["check"] = 144
        model.complex_default_json[0]["checkcheck"] = 144
        self.assertEqual(model.default_json["check"], 144)
        self.assertEqual(model.complex_default_json[0]["checkcheck"], 144)

        # Make sure when we create a new model, it resets to the default value
        # and not to what we just set it to (it would be if it were passed by reference)
        model = JsonModel()
        self.assertEqual(model.default_json["check"], 12)
        self.assertEqual(model.complex_default_json[0]["checkcheck"], 1212)

    def test_normal_regex_filter(self):
        """Make sure JSON model can filter regex"""

        JsonModel.objects.create(json={"boom": "town"})
        JsonModel.objects.create(json={"move": "town"})
        JsonModel.objects.create(json={"save": "town"})

        self.assertEqual(JsonModel.objects.count(), 3)

        self.assertEqual(JsonModel.objects.filter(json__regex=r"boom").count(), 1)
        self.assertEqual(JsonModel.objects.filter(json__regex=r"town").count(), 3)

    def test_save_blank_object(self):
        """Test that JSON model can save a blank object as none"""

        model = JsonModel()
        self.assertEqual(model.empty_default, {})

        model.save()
        self.assertEqual(model.empty_default, {})

        model1 = JsonModel(empty_default={"hey": "now"})
        self.assertEqual(model1.empty_default, {"hey": "now"})

        model1.save()
        self.assertEqual(model1.empty_default, {"hey": "now"})



class JSONCharFieldTest(JSONFieldTest):
    json_model = JsonCharModel


class OrderedJsonModel(models.Model):
    json = JSONField(load_kwargs={'object_pairs_hook': OrderedDict})


class OrderedDictSerializationTest(TestCase):
    ordered_dict = OrderedDict([
        ('number', [1, 2, 3, 4]),
        ('notes', True),
    ])
    expected_key_order = ['number', 'notes']

    def test_ordered_dict_differs_from_normal_dict(self):
        self.assertEqual(list(self.ordered_dict.keys()), self.expected_key_order)
        self.assertNotEqual(dict(self.ordered_dict).keys(), self.expected_key_order)

    def test_default_behaviour_loses_sort_order(self):
        mod = JsonModel.objects.create(json=self.ordered_dict)
        self.assertEqual(list(mod.json.keys()), self.expected_key_order)
        mod_from_db = JsonModel.objects.get(id=mod.id)

        # mod_from_db lost ordering information during json.loads()
        self.assertNotEqual(mod_from_db.json.keys(), self.expected_key_order)

    def test_load_kwargs_hook_does_not_lose_sort_order(self):
        mod = OrderedJsonModel.objects.create(json=self.ordered_dict)
        self.assertEqual(list(mod.json.keys()), self.expected_key_order)
        mod_from_db = OrderedJsonModel.objects.get(id=mod.id)
        self.assertEqual(list(mod_from_db.json.keys()), self.expected_key_order)

########NEW FILE########
