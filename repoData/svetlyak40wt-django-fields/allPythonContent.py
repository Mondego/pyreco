__FILENAME__ = fields
import binascii
import datetime
import string
import sys
import warnings

from django import forms
from django.forms import fields
from django.db import models
from django.conf import settings
from django.utils.encoding import smart_str, force_unicode
from django.utils.translation import ugettext_lazy as _
from Crypto import Random
from Crypto.Random import random

if hasattr(settings, 'USE_CPICKLE'):
    warnings.warn(
        "The USE_CPICKLE options is now obsolete. cPickle will always "
        "be used unless it cannot be found or DEBUG=True",
        DeprecationWarning,
    )

if settings.DEBUG:
    import pickle
else:
    try:
        import cPickle as pickle
    except:
        import pickle

class BaseEncryptedField(models.Field):
    '''This code is based on the djangosnippet #1095
       You can find the original at http://www.djangosnippets.org/snippets/1095/'''

    def __init__(self, *args, **kwargs):
        self.cipher_type = kwargs.pop('cipher', 'AES')
        self.block_type = kwargs.pop('block_type', None)
        self.secret_key = kwargs.pop('secret_key', settings.SECRET_KEY)
        self.secret_key = self.secret_key[:32]

        if self.block_type is None:
            warnings.warn(
                "Default usage of pycrypto's AES block type defaults has been "
                "deprecated and will be removed in 0.3.0 (default will become "
                "MODE_CBC). Please specify a secure block_type, such as CBC.",
                DeprecationWarning,
            )
        try:
            imp = __import__('Crypto.Cipher', globals(), locals(), [self.cipher_type], -1)
        except:
            imp = __import__('Crypto.Cipher', globals(), locals(), [self.cipher_type])
        self.cipher_object = getattr(imp, self.cipher_type)
        if self.block_type:
            self.prefix = '$%s$%s$' % (self.cipher_type, self.block_type)
            self.iv = Random.new().read(self.cipher_object.block_size)
            self.cipher = self.cipher_object.new(
                self.secret_key,
                getattr(self.cipher_object, self.block_type),
                self.iv)
        else:
            self.cipher = self.cipher_object.new(self.secret_key)
            self.prefix = '$%s$' % self.cipher_type

        max_length = kwargs.get('max_length', 40)
        self.unencrypted_length = max_length
        # always add at least 2 to the max_length:
        #     one for the null byte, one for padding
        max_length += 2
        mod = max_length % self.cipher.block_size
        if mod > 0:
            max_length += self.cipher.block_size - mod
        kwargs['max_length'] = max_length * 2 + len(self.prefix)

        models.Field.__init__(self, *args, **kwargs)

    def _is_encrypted(self, value):
        return isinstance(value, basestring) and value.startswith(self.prefix)

    def _get_padding(self, value):
        # We always want at least 2 chars of padding (including zero byte),
        # so we could have up to block_size + 1 chars.
        mod = (len(value) + 2) % self.cipher.block_size
        return self.cipher.block_size - mod + 2

    def to_python(self, value):
        if self._is_encrypted(value):
            if self.block_type:
                self.iv = binascii.a2b_hex(value[len(self.prefix):])[:len(self.iv)]
                self.cipher = self.cipher_object.new(
                    self.secret_key,
                    getattr(self.cipher_object, self.block_type),
                    self.iv)
                decrypt_value = binascii.a2b_hex(value[len(self.prefix):])[len(self.iv):]
            else:
                decrypt_value = binascii.a2b_hex(value[len(self.prefix):])
            return force_unicode(
                self.cipher.decrypt(decrypt_value).split('\0')[0]
            )
        return value

    def get_db_prep_value(self, value, connection=None, prepared=False):
        if value is None:
            return None

        value = smart_str(value)

        if not self._is_encrypted(value):
            padding = self._get_padding(value)
            if padding > 0:
                value += "\0" + ''.join([
                    random.choice(string.printable)
                    for index in range(padding-1)
                ])
            if self.block_type:
                self.cipher = self.cipher_object.new(
                    self.secret_key,
                    getattr(self.cipher_object, self.block_type),
                    self.iv)
                value = self.prefix + binascii.b2a_hex(self.iv + self.cipher.encrypt(value))
            else:
                value = self.prefix + binascii.b2a_hex(self.cipher.encrypt(value))
        return value


class EncryptedTextField(BaseEncryptedField):
    __metaclass__ = models.SubfieldBase

    def get_internal_type(self):
        return 'TextField'

    def formfield(self, **kwargs):
        defaults = {'widget': forms.Textarea}
        defaults.update(kwargs)
        return super(EncryptedTextField, self).formfield(**defaults)


class EncryptedCharField(BaseEncryptedField):
    __metaclass__ = models.SubfieldBase

    def get_internal_type(self):
        return "CharField"

    def formfield(self, **kwargs):
        defaults = {'max_length': self.max_length}
        defaults.update(kwargs)
        return super(EncryptedCharField, self).formfield(**defaults)

    def get_db_prep_value(self, value, connection=None, prepared=False):
        if value is not None and not self._is_encrypted(value):
            if len(value) > self.unencrypted_length:
                raise ValueError(
                    "Field value longer than max allowed: " +
                    str(len(value)) + " > " + str(self.unencrypted_length)
                )
        return super(EncryptedCharField, self).get_db_prep_value(
            value,
            connection=connection,
            prepared=prepared,
        )


class BaseEncryptedDateField(BaseEncryptedField):
    # Do NOT define a __metaclass__ for this - it's an abstract parent
    # for EncryptedDateField and EncryptedDateTimeField.
    # If you try to inherit from a class with a __metaclass__, you'll
    # get a very opaque infinite recursion in contribute_to_class.

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = self.max_raw_length
        super(BaseEncryptedDateField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'CharField'

    def formfield(self, **kwargs):
        defaults = {'widget': self.form_widget, 'form_class': self.form_field}
        defaults.update(kwargs)
        return super(BaseEncryptedDateField, self).formfield(**defaults)

    def to_python(self, value):
        # value is either a date or a string in the format "YYYY:MM:DD"

        if value in fields.EMPTY_VALUES:
            date_value = value
        else:
            if isinstance(value, self.date_class):
                date_value = value
            else:
                date_text = super(BaseEncryptedDateField, self).to_python(value)
                date_value = self.date_class(*map(int, date_text.split(':')))
        return date_value

    def get_db_prep_value(self, value, connection=None, prepared=False):
        # value is a date_class.
        # We need to convert it to a string in the format "YYYY:MM:DD"
        if value:
            date_text = value.strftime(self.save_format)
        else:
            date_text = None
        return super(BaseEncryptedDateField, self).get_db_prep_value(
            date_text,
            connection=connection,
            prepared=prepared
        )


class EncryptedDateField(BaseEncryptedDateField):
    __metaclass__ = models.SubfieldBase
    form_widget = forms.DateInput
    form_field = forms.DateField
    save_format = "%Y:%m:%d"
    date_class = datetime.date
    max_raw_length = 10  # YYYY:MM:DD


class EncryptedDateTimeField(BaseEncryptedDateField):
    # FIXME:  This doesn't handle time zones, but Python doesn't really either.
    __metaclass__ = models.SubfieldBase
    form_widget = forms.DateTimeInput
    form_field = forms.DateTimeField
    save_format = "%Y:%m:%d:%H:%M:%S:%f"
    date_class = datetime.datetime
    max_raw_length = 26  # YYYY:MM:DD:hh:mm:ss:micros


class BaseEncryptedNumberField(BaseEncryptedField):
    # Do NOT define a __metaclass__ for this - it's abstract.
    # See BaseEncryptedDateField for full explanation.
    def __init__(self, *args, **kwargs):
        if self.max_raw_length:
            kwargs['max_length'] = self.max_raw_length
        super(BaseEncryptedNumberField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'CharField'

    def to_python(self, value):
        # value is either an int or a string of an integer
        if isinstance(value, self.number_type) or value == '':
            number = value
        else:
            number_text = super(BaseEncryptedNumberField, self).to_python(value)
            number = self.number_type(number_text)
        return number

    # def get_prep_value(self, value):
    def get_db_prep_value(self, value, connection=None, prepared=False):
        number_text = self.format_string % value
        return super(BaseEncryptedNumberField, self).get_db_prep_value(
            number_text,
            connection=connection,
            prepared=prepared,
        )


class EncryptedIntField(BaseEncryptedNumberField):
    __metaclass__ = models.SubfieldBase
    max_raw_length = len(str(-sys.maxint - 1))
    number_type = int
    format_string = "%d"


class EncryptedLongField(BaseEncryptedNumberField):
    __metaclass__ = models.SubfieldBase
    max_raw_length = None  # no limit
    number_type = long
    format_string = "%d"

    def get_internal_type(self):
        return 'TextField'


class EncryptedFloatField(BaseEncryptedNumberField):
    __metaclass__ = models.SubfieldBase
    max_raw_length = 150  # arbitrary, but should be sufficient
    number_type = float
    # If this format is too long for some architectures, change it.
    format_string = "%0.66f"


class PickleField(models.TextField):
    __metaclass__ = models.SubfieldBase

    editable = False
    serialize = False

    def get_db_prep_value(self, value, connection=None, prepared=False):
        return pickle.dumps(value)

    def to_python(self, value):
        if not isinstance(value, basestring):
            return value

        # Tries to convert unicode objects to string, cause loads pickle from
        # unicode excepts ugly ``KeyError: '\x00'``.
        try:
            return pickle.loads(smart_str(value))
        # If pickle could not loads from string it's means that it's Python
        # string saved to PickleField.
        except ValueError:
            return value
        except EOFError:
            return value


class EncryptedUSPhoneNumberField(BaseEncryptedField):
    __metaclass__ = models.SubfieldBase

    def get_internal_type(self):
        return "CharField"

    def formfield(self, **kwargs):
        try:
            from localflavor.us.forms import USPhoneNumberField            
        except ImportError:
            from django.contrib.localflavor.us.forms import USPhoneNumberField

        defaults = {'form_class': USPhoneNumberField}
        defaults.update(kwargs)
        return super(EncryptedUSPhoneNumberField, self).formfield(**defaults)


class EncryptedUSSocialSecurityNumberField(BaseEncryptedField):
    __metaclass__ = models.SubfieldBase

    def get_internal_type(self):
        return "CharField"

    def formfield(self, **kwargs):
        try:
            from localflavor.us.forms import USSocialSecurityNumberField
        except ImportError:
            from django.contrib.localflavor.us.forms import USSocialSecurityNumberField            

        defaults = {'form_class': USSocialSecurityNumberField}
        defaults.update(kwargs)
        return super(EncryptedUSSocialSecurityNumberField, self).formfield(**defaults)

class EncryptedEmailField(BaseEncryptedField):
    __metaclass__ = models.SubfieldBase
    description = _("E-mail address")

    def get_internal_type(self):
        return "CharField"

    def formfield(self, **kwargs):
        from django.forms import EmailField
        defaults = {'form_class': EmailField, 'max_length': self.unencrypted_length}
        defaults.update(kwargs)
        return super(EncryptedEmailField, self).formfield(**defaults)


try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([
        (
            [
                BaseEncryptedField, EncryptedDateField, BaseEncryptedDateField, EncryptedCharField, EncryptedTextField,
                EncryptedFloatField, EncryptedDateTimeField, BaseEncryptedNumberField, EncryptedIntField, EncryptedLongField,
                EncryptedUSPhoneNumberField, EncryptedEmailField,
            ],
            [],
            {
                'cipher': ('cipher_type', {}),
                'block_type': ('block_type', {}),
            },
        ),
    ], ["^django_fields\.fields\..+?Field"])
    add_introspection_rules([], ["^django_fields\.fields\.PickleField"])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

import re
from django.db import models


class PrivateFieldsMetaclass(models.base.ModelBase):
    """Metaclass to set right default db_column values
    for mangled private fields.

    For example, python transforms field __secret_state of the model
    Machine, to the _Machine__secret_state and you don't want
    database column has this ugly name. There are two possibilities:

    * to specify column name via arguments to django Field class, or…
    * to use this PrivateFieldsMetaclass which will say django:
      "Hey, for this field `_Machine__secret_state` use db_column
      `secret_state`, please!"

    """
    def __new__(cls, name, bases, attrs):
        super_new = super(PrivateFieldsMetaclass, cls).__new__

        prefix = '_' + name + '__'
        for key, value in attrs.iteritems():
            if key.startswith(prefix) and hasattr(value, 'db_column') and value.db_column is None:
                value.db_column = key[len(prefix):]

        result = super_new(cls, name, bases, attrs)
        return result


class ModelWithPrivateFields(models.Model):
    """This abstract base class allows you to use "private" fields in django models for better encapsulation.

    It does two things:

    * adds a one more item into the Django's internal name map for the model class;
    * mangles constructor kwargs so that short names could be used.

    The first thing needs to make `filter`, `get` and other methods accept short field names.
    For example, let you want to use this class:

        class TestModel(ModelWithPrivateFields):
            __state = models.CharField(max_length=255, editable=False)

    Then you will not be able to execute `TestModel.objects.filter(state='blah')` and
    Django will not allow you to run `TestModel.objects.filter(_TestModel__state='blah')`
    because it will see `__` in the param and try to make join using missing field `_TestModel`.

    Monkey patching of the `init_name_map` method, resolves this problem.

    Another obstacle is that you can't pass short field names into the class's constructor like that:
    `obj = TestModel(state='blah')`, because Django does not know about `state` attribute, but is
    aware of `_TestModel__state`. That is why `PrivateFieldsMetaclass` mangles such keyword attributes
    in the `__init__` method.

    """
    __metaclass__ = PrivateFieldsMetaclass

    def __init__(self, *args, **kwargs):
        new_kwargs = {}
        prefix = '_' + self.__class__.__name__ + '__'

        field_names = set(f.name for f in self._meta.fields)

        for key, value in kwargs.iteritems():
            if prefix + key in field_names:
                key = prefix + key
            new_kwargs[key] = value

        _init_name_map_orig = self._meta.init_name_map

        def init_name_map(self):
            cache = _init_name_map_orig()

            for key, value in cache.items():
                match = re.match(r'^_.+__(.*)', key)
                if match is not None:
                    cache[match.group(1)] = value
            return cache
        init_name_map.patched = True

        if not getattr(self._meta.init_name_map, 'patched', False):
            self._meta.init_name_map = type(_init_name_map_orig)(init_name_map, type(self._meta))

        super(ModelWithPrivateFields, self).__init__(*args, **new_kwargs)

    class Meta:
        abstract = True


########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import datetime
import string
import sys
import unittest

from django.db import connection
from django.db import models

from .fields import (
    EncryptedCharField, EncryptedDateField,
    EncryptedDateTimeField, EncryptedIntField,
    EncryptedLongField, EncryptedFloatField, PickleField,
    EncryptedUSPhoneNumberField, EncryptedUSSocialSecurityNumberField,
    EncryptedEmailField,
)

from .models import ModelWithPrivateFields


class EncObject(models.Model):
    max_password = 20
    password = EncryptedCharField(max_length=max_password, null=True)


class EncDate(models.Model):
    important_date = EncryptedDateField()


class EncDateTime(models.Model):
    important_datetime = EncryptedDateTimeField()
    # important_datetime = EncryptedDateField()


class EncInt(models.Model):
    important_number = EncryptedIntField()


class EncLong(models.Model):
    important_number = EncryptedLongField()


class EncFloat(models.Model):
    important_number = EncryptedFloatField()


class PickleObject(models.Model):
    name = models.CharField(max_length=16)
    data = PickleField()


class EmailObject(models.Model):
    max_email = 255
    email = EncryptedEmailField()


class USPhoneNumberField(models.Model):
    phone = EncryptedUSPhoneNumberField()

class USSocialSecurityNumberField(models.Model):
    ssn = EncryptedUSSocialSecurityNumberField()

class CipherEncObject(models.Model):
    max_password = 20
    password = EncryptedCharField(
        max_length=max_password,
        block_type = 'MODE_CBC')

class EncryptTests(unittest.TestCase):

    def setUp(self):
        EncObject.objects.all().delete()

    def test_encryption(self):
        """
        Test that the database values are actually encrypted.
        """
        password = 'this is a password!!'  # 20 chars
        obj = EncObject(password = password)
        obj.save()
        # The value from the retrieved object should be the same...
        obj = EncObject.objects.get(id=obj.id)
        self.assertEqual(password, obj.password)
        # ...but the value in the database should not
        encrypted_password = self._get_encrypted_password(obj.id)
        self.assertNotEqual(encrypted_password, password)
        self.assertTrue(encrypted_password.startswith('$AES$'))

    def test_encryption_w_cipher(self):
        """
        Test that the database values are actually encrypted when using
        non-default cipher types.
        """
        password = 'this is a password!!'  # 20 chars
        obj = CipherEncObject(password = password)
        obj.save()
        # The value from the retrieved object should be the same...
        obj = CipherEncObject.objects.get(id=obj.id)
        self.assertEqual(password, obj.password)
        # ...but the value in the database should not
        encrypted_password = self._get_encrypted_password_cipher(obj.id)
        self.assertNotEqual(encrypted_password, password)
        self.assertTrue(encrypted_password.startswith('$AES$MODE_CBC$'))

    def test_multiple_encryption_w_cipher(self):
        """
        Test that a single field can be reused without error.
        """
        password = 'this is a password!!'
        obj = CipherEncObject(password=password)
        obj.save()
        obj = CipherEncObject.objects.get(id=obj.id)
        self.assertEqual(password, obj.password)

        password = 'another password!!'
        obj = CipherEncObject(password=password)
        obj.save()
        obj = CipherEncObject.objects.get(id=obj.id)
        self.assertEqual(password, obj.password)

    def test_max_field_length(self):
        password = 'a' * EncObject.max_password
        obj = EncObject(password = password)
        obj.save()
        obj = EncObject.objects.get(id=obj.id)
        self.assertEqual(password, obj.password)

    def test_field_too_long(self):
        password = 'a' * (EncObject.max_password + 1)
        obj = EncObject(password = password)
        self.assertRaises(Exception, obj.save)

    def test_UTF8(self):
        password = u'совершенно секретно'
        obj = EncObject(password = password)
        obj.save()
        obj = EncObject.objects.get(id=obj.id)
        self.assertEqual(password, obj.password)

    def test_consistent_encryption(self):
        """
        The same password should not encrypt the same way twice.
        Check different lengths.
        """
        # NOTE:  This may fail occasionally because the randomly-generated padding could be the same for both values.
        # A 14-char string will only have 1 char of padding.  There's a 1/len(string.printable) chance of getting the
        # same value twice.
        for pwd_length in range(1,21):  # 1-20 inclusive
            enc_pwd_1, enc_pwd_2 = self._get_two_passwords(pwd_length)
            self.assertNotEqual(enc_pwd_1, enc_pwd_2)

    def test_minimum_padding(self):
        """
        There should always be at least two chars of padding.
        """
        enc_field = EncryptedCharField()
        for pwd_length in range(1,21):  # 1-20 inclusive
            password = 'a' * pwd_length  # 'a', 'aa', ...
            self.assertTrue(enc_field._get_padding(password) >= 2)

    def test_none_value(self):
        """
        A value of None should be passed through without encryption.
        """
        obj = EncObject(password=None)
        obj.save()
        obj = EncObject.objects.get(id=obj.id)
        self.assertEqual(obj.password, None)
        encrypted_text = self._get_encrypted_password(obj.id)
        self.assertEqual(encrypted_text, None)

    ### Utility methods for tests ###

    def _get_encrypted_password(self, id):
        cursor = connection.cursor()
        cursor.execute("select password from django_fields_encobject where id = %s", [id,])
        passwords = map(lambda x: x[0], cursor.fetchall())
        self.assertEqual(len(passwords), 1)  # only one
        return passwords[0]

    def _get_encrypted_password_cipher(self, id):
        cursor = connection.cursor()
        cursor.execute("select password from django_fields_cipherencobject where id = %s", [id,])
        passwords = map(lambda x: x[0], cursor.fetchall())
        self.assertEqual(len(passwords), 1)  # only one
        return passwords[0]

    def _get_two_passwords(self, pwd_length):
        password = 'a' * pwd_length  # 'a', 'aa', ...
        obj_1 = EncObject(password = password)
        obj_1.save()
        obj_2 = EncObject(password = password)
        obj_2.save()
        # The encrypted values in the database should be different.
        # There's a chance they'll be the same, but it's small.
        enc_pwd_1 = self._get_encrypted_password(obj_1.id)
        enc_pwd_2 = self._get_encrypted_password(obj_2.id)
        return enc_pwd_1, enc_pwd_2


class DateEncryptTests(unittest.TestCase):
    def setUp(self):
        EncDate.objects.all().delete()

    def test_BC_date(self):
        # datetime.MINYEAR is 1 -- so much for history
        func = lambda: datetime.date(0, 1, 1)
        self.assertRaises(ValueError, func)

    def test_date_encryption(self):
        today = datetime.date.today()
        obj = EncDate(important_date=today)
        obj.save()
        # The date from the retrieved object should be the same...
        obj = EncDate.objects.get(id=obj.id)
        self.assertEqual(today, obj.important_date)
        # ...but the value in the database should not
        important_date = self._get_encrypted_date(obj.id)
        self.assertTrue(important_date.startswith('$AES$'))
        self.assertNotEqual(important_date, today)

    def test_date_time_encryption(self):
        now = datetime.datetime.now()
        obj = EncDateTime(important_datetime=now)
        obj.save()
        # The datetime from the retrieved object should be the same...
        obj = EncDateTime.objects.get(id=obj.id)
        self.assertEqual(now, obj.important_datetime)
        # ...but the value in the database should not
        important_datetime = self._get_encrypted_datetime(obj.id)
        self.assertTrue(important_datetime.startswith('$AES$'))
        self.assertNotEqual(important_datetime, now)

    ### Utility methods for tests ###

    def _get_encrypted_date(self, id):
        cursor = connection.cursor()
        cursor.execute("select important_date from django_fields_encdate where id = %s", [id,])
        important_dates = map(lambda x: x[0], cursor.fetchall())
        self.assertEqual(len(important_dates), 1)  # only one
        return important_dates[0]

    def _get_encrypted_datetime(self, id):
        cursor = connection.cursor()
        cursor.execute("select important_datetime from django_fields_encdatetime where id = %s", [id,])
        important_datetimes = map(lambda x: x[0], cursor.fetchall())
        self.assertEqual(len(important_datetimes), 1)  # only one
        return important_datetimes[0]


class NumberEncryptTests(unittest.TestCase):
    def setUp(self):
        EncInt.objects.all().delete()
        EncLong.objects.all().delete()
        EncFloat.objects.all().delete()

    def test_int_encryption(self):
        self._test_number_encryption(EncInt, 'int', sys.maxint)

    def test_min_int_encryption(self):
        self._test_number_encryption(EncInt, 'int', -sys.maxint - 1)

    def test_long_encryption(self):
        self._test_number_encryption(EncLong, 'long', long(sys.maxint) * 100L)

    def test_float_encryption(self):
        value = 123.456 + sys.maxint
        self._test_number_encryption(EncFloat, 'float', value)

    def test_one_third_float_encryption(self):
        value = sys.maxint + (1.0 / 3.0)
        self._test_number_encryption(EncFloat, 'float', value)

    def _test_number_encryption(self, number_class, type_name, value):
        obj = number_class(important_number=value)
        obj.save()
        # The int from the retrieved object should be the same...
        obj = number_class.objects.get(id=obj.id)
        self.assertEqual(value, obj.important_number)
        # ...but the value in the database should not
        number = self._get_encrypted_number(type_name, obj.id)
        self.assertTrue(number.startswith('$AES$'))
        self.assertNotEqual(number, value)

    def _get_encrypted_number(self, type_name, id):
        cursor = connection.cursor()
        sql = "select important_number from django_fields_enc%s where id = %%s" % (type_name,)
        cursor.execute(sql, [id,])
        important_numbers = map(lambda x: x[0], cursor.fetchall())
        self.assertEqual(len(important_numbers), 1)  # only one
        return important_numbers[0]


class TestPickleField(unittest.TestCase):
    def setUp(self):
        PickleObject.objects.all().delete()

    def test_not_string_data(self):
        items = [
            'Item 1', 'Item 2', 'Item 3', 'Item 4', 'Item 5'
        ]

        obj = PickleObject.objects.create(name='default', data=items)
        self.assertEqual(PickleObject.objects.count(), 1)

        self.assertEqual(obj.data, items)

        obj = PickleObject.objects.get(name='default')
        self.assertEqual(obj.data, items)

    def test_string_and_unicode_data(self):
        DATA = (
            ('string', 'Simple string'),
            ('unicode', u'Simple unicode string'),
        )

        for name, data in DATA:
            obj = PickleObject.objects.create(name=name, data=data)
            self.assertEqual(obj.data, data)

        self.assertEqual(PickleObject.objects.count(), 2)

        for name, data in DATA:
            obj = PickleObject.objects.get(name=name)
            self.assertEqual(obj.data, data)

    def test_empty_string(self):
        value = ''

        obj = PickleObject.objects.create(name='default', data=value)
        self.assertEqual(PickleObject.objects.count(), 1)

        self.assertEqual(obj.data, value)


class EncryptEmailTests(unittest.TestCase):

    def setUp(self):
        EmailObject.objects.all().delete()

    def test_encryption(self):
        """
        Test that the database values are actually encrypted.
        """
        email = 'test@example.com'  # 16 chars
        obj = EmailObject(email = email)
        obj.save()
        # The value from the retrieved object should be the same...
        obj = EmailObject.objects.get(id=obj.id)
        self.assertEqual(email, obj.email)
        # ...but the value in the database should not
        encrypted_email = self._get_encrypted_email(obj.id)
        self.assertNotEqual(encrypted_email, email)
        self.assertTrue(encrypted_email.startswith('$AES$'))

    def test_max_field_length(self):
        email = 'a' * EmailObject.max_email
        obj = EmailObject(email = email)
        obj.save()
        obj = EmailObject.objects.get(id=obj.id)
        self.assertEqual(email, obj.email)

    def test_UTF8(self):
        email = u'совершенно@секретно.com'
        obj = EmailObject(email = email)
        obj.save()
        obj = EmailObject.objects.get(id=obj.id)
        self.assertEqual(email, obj.email)

    def test_consistent_encryption(self):
        """
        The same password should not encrypt the same way twice.
        Check different lengths.
        """
        # NOTE:  This may fail occasionally because the randomly-generated padding could be the same for both values.
        # A 14-char string will only have 1 char of padding.  There's a 1/len(string.printable) chance of getting the
        # same value twice.
        for email_length in range(1,21):  # 1-20 inclusive
            enc_email_1, enc_email_2 = self._get_two_emails(email_length)
            self.assertNotEqual(enc_email_1, enc_email_2)

    def test_minimum_padding(self):
        """
        There should always be at least two chars of padding.
        """
        enc_field = EncryptedCharField()
        for pwd_length in range(1,21):  # 1-20 inclusive
            email = 'a' * pwd_length  # 'a', 'aa', ...
            self.assertTrue(enc_field._get_padding(email) >= 2)

    ### Utility methods for tests ###

    def _get_encrypted_email(self, id):
        cursor = connection.cursor()
        cursor.execute("select email from django_fields_emailobject where id = %s", [id,])
        emails = map(lambda x: x[0], cursor.fetchall())
        self.assertEqual(len(emails), 1)  # only one
        return emails[0]

    def _get_two_emails(self, email_length):
        email = 'a' * email_length  # 'a', 'aa', ...
        obj_1 = EmailObject(email = email)
        obj_1.save()
        obj_2 = EmailObject(email = email)
        obj_2.save()
        # The encrypted values in the database should be different.
        # There's a chance they'll be the same, but it's small.
        enc_email_1 = self._get_encrypted_email(obj_1.id)
        enc_email_2 = self._get_encrypted_email(obj_2.id)
        return enc_email_1, enc_email_2


class TestModelWithPrivateFields(ModelWithPrivateFields):
    """This model is for the unittests against ModelWithPrivateFields.
    """
    __state = models.CharField(max_length=255, editable=False)
    __state_changed_at = models.DateTimeField(editable=False, blank=True, null=True)

    def get_state(self):
        return self.__state

    def set_state(self, value):
        self.__state = value
        self.__state_changed_at = datetime.datetime.now()

    state = property(get_state, set_state)
    del get_state, set_state



class PrivateFieldsTests(unittest.TestCase):
    def test_private_fields(self):
        obj1 = TestModelWithPrivateFields(state='blah')

        self.assert_(obj1._TestModelWithPrivateFields__state_changed_at is None)
        obj1.save()

        obj2 = TestModelWithPrivateFields.objects.create(state='minor')
        self.assert_(obj2._TestModelWithPrivateFields__state_changed_at is None)

        self.assertEqual(1, TestModelWithPrivateFields.objects.filter(state='blah').count())
        self.assertEqual(2, TestModelWithPrivateFields.objects.all().count())

        obj1.state = 'blah2' # this has a side effect:
        self.assert_(obj1._TestModelWithPrivateFields__state_changed_at is not None)
        obj1.save()

        sql = unicode(TestModelWithPrivateFields.objects.filter(state='blah').query)
        self.assert_('_TestModelWithPrivateFields__' not in sql, '_TestModelWithPrivateFields__ is in the "' + sql + '"')



########NEW FILE########
__FILENAME__ = admin
from example.blog.models import EncObject
from django.contrib import admin

admin.site.register(EncObject)

########NEW FILE########
__FILENAME__ = models
from django_fields.tests import EncObject

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
# Django settings for example project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = dict(
    default = dict(
        ENGINE = 'django.db.backends.sqlite3',
        NAME = 'test.sqlite',
    )
)

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
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '=r521(6qmkk#uus#gpiml@5+26@_qcj^tmk0%12byrd6=qh954'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'example.urls'

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
    'django_fields',
    'django_nose',
    'example.blog',
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^example/', include('example.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = virtualenv
#!/usr/bin/env python
"""Create a "virtual" Python installation
"""

# If you change the version here, change it in setup.py 
# and docs/conf.py as well.
virtualenv_version = "1.6.4"

import base64
import sys
import os
import optparse
import re
import shutil
import logging
import tempfile
import zlib
import errno
import distutils.sysconfig
try:
    import subprocess
except ImportError:
    if sys.version_info <= (2, 3):
        print('ERROR: %s' % sys.exc_info()[1])
        print('ERROR: this script requires Python 2.4 or greater; or at least the subprocess module.')
        print('If you copy subprocess.py from a newer version of Python this script will probably work')
        sys.exit(101)
    else:
        raise
try:
    set
except NameError:
    from sets import Set as set
try:
    basestring
except NameError:
    basestring = str

join = os.path.join
py_version = 'python%s.%s' % (sys.version_info[0], sys.version_info[1])

is_jython = sys.platform.startswith('java')
is_pypy = hasattr(sys, 'pypy_version_info')
is_win  = (sys.platform == 'win32')
abiflags = getattr(sys, 'abiflags', '')

if is_pypy:
    expected_exe = 'pypy'
elif is_jython:
    expected_exe = 'jython'
else:
    expected_exe = 'python'


REQUIRED_MODULES = ['os', 'posix', 'posixpath', 'nt', 'ntpath', 'genericpath',
                    'fnmatch', 'locale', 'encodings', 'codecs',
                    'stat', 'UserDict', 'readline', 'copy_reg', 'types',
                    're', 'sre', 'sre_parse', 'sre_constants', 'sre_compile',
                    'zlib']

REQUIRED_FILES = ['lib-dynload', 'config']

majver, minver = sys.version_info[:2]
if majver == 2:
    if minver >= 6:
        REQUIRED_MODULES.extend(['warnings', 'linecache', '_abcoll', 'abc'])
    if minver >= 7:
        REQUIRED_MODULES.extend(['_weakrefset'])
    if minver <= 3:
        REQUIRED_MODULES.extend(['sets', '__future__'])
elif majver == 3:
    # Some extra modules are needed for Python 3, but different ones
    # for different versions.
    REQUIRED_MODULES.extend(['_abcoll', 'warnings', 'linecache', 'abc', 'io',
                             '_weakrefset', 'copyreg', 'tempfile', 'random',
                             '__future__', 'collections', 'keyword', 'tarfile',
                             'shutil', 'struct', 'copy'])
    if minver >= 2:
        REQUIRED_FILES[-1] = 'config-%s' % majver
    if minver == 3:
        # The whole list of 3.3 modules is reproduced below - the current
        # uncommented ones are required for 3.3 as of now, but more may be
        # added as 3.3 development continues.
        REQUIRED_MODULES.extend([
            #"aifc",
            #"antigravity",
            #"argparse",
            #"ast",
            #"asynchat",
            #"asyncore",
            "base64",
            #"bdb",
            #"binhex",
            "bisect",
            #"calendar",
            #"cgi",
            #"cgitb",
            #"chunk",
            #"cmd",
            #"codeop",
            #"code",
            #"colorsys",
            #"_compat_pickle",
            #"compileall",
            #"concurrent",
            #"configparser",
            #"contextlib",
            #"cProfile",
            #"crypt",
            #"csv",
            #"ctypes",
            #"curses",
            #"datetime",
            #"dbm",
            #"decimal",
            #"difflib",
            #"dis",
            #"doctest",
            #"dummy_threading",
            "_dummy_thread",
            #"email",
            #"filecmp",
            #"fileinput",
            #"formatter",
            #"fractions",
            #"ftplib",
            #"functools",
            #"getopt",
            #"getpass",
            #"gettext",
            #"glob",
            #"gzip",
            "hashlib",
            "heapq",
            "hmac",
            #"html",
            #"http",
            #"idlelib",
            #"imaplib",
            #"imghdr",
            #"importlib",
            #"inspect",
            #"json",
            #"lib2to3",
            #"logging",
            #"macpath",
            #"macurl2path",
            #"mailbox",
            #"mailcap",
            #"_markupbase",
            #"mimetypes",
            #"modulefinder",
            #"multiprocessing",
            #"netrc",
            #"nntplib",
            #"nturl2path",
            #"numbers",
            #"opcode",
            #"optparse",
            #"os2emxpath",
            #"pdb",
            #"pickle",
            #"pickletools",
            #"pipes",
            #"pkgutil",
            #"platform",
            #"plat-linux2",
            #"plistlib",
            #"poplib",
            #"pprint",
            #"profile",
            #"pstats",
            #"pty",
            #"pyclbr",
            #"py_compile",
            #"pydoc_data",
            #"pydoc",
            #"_pyio",
            #"queue",
            #"quopri",
            "reprlib",
            "rlcompleter",
            #"runpy",
            #"sched",
            #"shelve",
            #"shlex",
            #"smtpd",
            #"smtplib",
            #"sndhdr",
            #"socket",
            #"socketserver",
            #"sqlite3",
            #"ssl",
            #"stringprep",
            #"string",
            #"_strptime",
            #"subprocess",
            #"sunau",
            #"symbol",
            #"symtable",
            #"sysconfig",
            #"tabnanny",
            #"telnetlib",
            #"test",
            #"textwrap",
            #"this",
            #"_threading_local",
            #"threading",
            #"timeit",
            #"tkinter",
            #"tokenize",
            #"token",
            #"traceback",
            #"trace",
            #"tty",
            #"turtledemo",
            #"turtle",
            #"unittest",
            #"urllib",
            #"uuid",
            #"uu",
            #"wave",
            "weakref",
            #"webbrowser",
            #"wsgiref",
            #"xdrlib",
            #"xml",
            #"xmlrpc",
            #"zipfile",
        ])

if is_pypy:
    # these are needed to correctly display the exceptions that may happen
    # during the bootstrap
    REQUIRED_MODULES.extend(['traceback', 'linecache'])

class Logger(object):

    """
    Logging object for use in command-line script.  Allows ranges of
    levels, to avoid some redundancy of displayed information.
    """

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    NOTIFY = (logging.INFO+logging.WARN)/2
    WARN = WARNING = logging.WARN
    ERROR = logging.ERROR
    FATAL = logging.FATAL

    LEVELS = [DEBUG, INFO, NOTIFY, WARN, ERROR, FATAL]

    def __init__(self, consumers):
        self.consumers = consumers
        self.indent = 0
        self.in_progress = None
        self.in_progress_hanging = False

    def debug(self, msg, *args, **kw):
        self.log(self.DEBUG, msg, *args, **kw)
    def info(self, msg, *args, **kw):
        self.log(self.INFO, msg, *args, **kw)
    def notify(self, msg, *args, **kw):
        self.log(self.NOTIFY, msg, *args, **kw)
    def warn(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def error(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def fatal(self, msg, *args, **kw):
        self.log(self.FATAL, msg, *args, **kw)
    def log(self, level, msg, *args, **kw):
        if args:
            if kw:
                raise TypeError(
                    "You may give positional or keyword arguments, not both")
        args = args or kw
        rendered = None
        for consumer_level, consumer in self.consumers:
            if self.level_matches(level, consumer_level):
                if (self.in_progress_hanging
                    and consumer in (sys.stdout, sys.stderr)):
                    self.in_progress_hanging = False
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                if rendered is None:
                    if args:
                        rendered = msg % args
                    else:
                        rendered = msg
                    rendered = ' '*self.indent + rendered
                if hasattr(consumer, 'write'):
                    consumer.write(rendered+'\n')
                else:
                    consumer(rendered)

    def start_progress(self, msg):
        assert not self.in_progress, (
            "Tried to start_progress(%r) while in_progress %r"
            % (msg, self.in_progress))
        if self.level_matches(self.NOTIFY, self._stdout_level()):
            sys.stdout.write(msg)
            sys.stdout.flush()
            self.in_progress_hanging = True
        else:
            self.in_progress_hanging = False
        self.in_progress = msg

    def end_progress(self, msg='done.'):
        assert self.in_progress, (
            "Tried to end_progress without start_progress")
        if self.stdout_level_matches(self.NOTIFY):
            if not self.in_progress_hanging:
                # Some message has been printed out since start_progress
                sys.stdout.write('...' + self.in_progress + msg + '\n')
                sys.stdout.flush()
            else:
                sys.stdout.write(msg + '\n')
                sys.stdout.flush()
        self.in_progress = None
        self.in_progress_hanging = False

    def show_progress(self):
        """If we are in a progress scope, and no log messages have been
        shown, write out another '.'"""
        if self.in_progress_hanging:
            sys.stdout.write('.')
            sys.stdout.flush()

    def stdout_level_matches(self, level):
        """Returns true if a message at this level will go to stdout"""
        return self.level_matches(level, self._stdout_level())

    def _stdout_level(self):
        """Returns the level that stdout runs at"""
        for level, consumer in self.consumers:
            if consumer is sys.stdout:
                return level
        return self.FATAL

    def level_matches(self, level, consumer_level):
        """
        >>> l = Logger([])
        >>> l.level_matches(3, 4)
        False
        >>> l.level_matches(3, 2)
        True
        >>> l.level_matches(slice(None, 3), 3)
        False
        >>> l.level_matches(slice(None, 3), 2)
        True
        >>> l.level_matches(slice(1, 3), 1)
        True
        >>> l.level_matches(slice(2, 3), 1)
        False
        """
        if isinstance(level, slice):
            start, stop = level.start, level.stop
            if start is not None and start > consumer_level:
                return False
            if stop is not None and stop <= consumer_level:
                return False
            return True
        else:
            return level >= consumer_level

    #@classmethod
    def level_for_integer(cls, level):
        levels = cls.LEVELS
        if level < 0:
            return levels[0]
        if level >= len(levels):
            return levels[-1]
        return levels[level]

    level_for_integer = classmethod(level_for_integer)

# create a silent logger just to prevent this from being undefined
# will be overridden with requested verbosity main() is called.
logger = Logger([(Logger.LEVELS[-1], sys.stdout)])

def mkdir(path):
    if not os.path.exists(path):
        logger.info('Creating %s', path)
        os.makedirs(path)
    else:
        logger.info('Directory %s already exists', path)

def copyfileordir(src, dest):
    if os.path.isdir(src):
        shutil.copytree(src, dest, True)
    else:
        shutil.copy2(src, dest)

def copyfile(src, dest, symlink=True):
    if not os.path.exists(src):
        # Some bad symlink in the src
        logger.warn('Cannot find file %s (bad symlink)', src)
        return
    if os.path.exists(dest):
        logger.debug('File %s already exists', dest)
        return
    if not os.path.exists(os.path.dirname(dest)):
        logger.info('Creating parent directories for %s' % os.path.dirname(dest))
        os.makedirs(os.path.dirname(dest))
    if not os.path.islink(src):
        srcpath = os.path.abspath(src)
    else:
        srcpath = os.readlink(src)
    if symlink and hasattr(os, 'symlink'):
        logger.info('Symlinking %s', dest)
        try:
            os.symlink(srcpath, dest)
        except (OSError, NotImplementedError):
            logger.info('Symlinking failed, copying to %s', dest)
            copyfileordir(src, dest)
    else:
        logger.info('Copying to %s', dest)
        copyfileordir(src, dest)

def writefile(dest, content, overwrite=True):
    if not os.path.exists(dest):
        logger.info('Writing %s', dest)
        f = open(dest, 'wb')
        f.write(content.encode('utf-8'))
        f.close()
        return
    else:
        f = open(dest, 'rb')
        c = f.read()
        f.close()
        if c != content:
            if not overwrite:
                logger.notify('File %s exists with different content; not overwriting', dest)
                return
            logger.notify('Overwriting %s with new content', dest)
            f = open(dest, 'wb')
            f.write(content.encode('utf-8'))
            f.close()
        else:
            logger.info('Content %s already in place', dest)

def rmtree(dir):
    if os.path.exists(dir):
        logger.notify('Deleting tree %s', dir)
        shutil.rmtree(dir)
    else:
        logger.info('Do not need to delete %s; already gone', dir)

def make_exe(fn):
    if hasattr(os, 'chmod'):
        oldmode = os.stat(fn).st_mode & 0xFFF # 0o7777
        newmode = (oldmode | 0x16D) & 0xFFF # 0o555, 0o7777
        os.chmod(fn, newmode)
        logger.info('Changed mode of %s to %s', fn, oct(newmode))

def _find_file(filename, dirs):
    for dir in dirs:
        if os.path.exists(join(dir, filename)):
            return join(dir, filename)
    return filename

def _install_req(py_executable, unzip=False, distribute=False,
                 search_dirs=None, never_download=False):

    if search_dirs is None:
        search_dirs = file_search_dirs()

    if not distribute:
        setup_fn = 'setuptools-0.6c11-py%s.egg' % sys.version[:3]
        project_name = 'setuptools'
        bootstrap_script = EZ_SETUP_PY
        source = None
    else:
        setup_fn = None
        source = 'distribute-0.6.19.tar.gz'
        project_name = 'distribute'
        bootstrap_script = DISTRIBUTE_SETUP_PY

        # If we are running under -p, we need to remove the current
        # directory from sys.path temporarily here, so that we
        # definitely get the pkg_resources from the site directory of
        # the interpreter we are running under, not the one
        # virtualenv.py is installed under (which might lead to py2/py3
        # incompatibility issues)
        _prev_sys_path = sys.path
        if os.environ.get('VIRTUALENV_INTERPRETER_RUNNING'):
            sys.path = sys.path[1:]

        try:
            try:
                # check if the global Python has distribute installed or plain
                # setuptools
                import pkg_resources
                if not hasattr(pkg_resources, '_distribute'):
                    location = os.path.dirname(pkg_resources.__file__)
                    logger.notify("A globally installed setuptools was found (in %s)" % location)
                    logger.notify("Use the --no-site-packages option to use distribute in "
                                  "the virtualenv.")
            except ImportError:
                pass
        finally:
            sys.path = _prev_sys_path

    if setup_fn is not None:
        setup_fn = _find_file(setup_fn, search_dirs)

    if source is not None:
        source = _find_file(source, search_dirs)

    if is_jython and os._name == 'nt':
        # Jython's .bat sys.executable can't handle a command line
        # argument with newlines
        fd, ez_setup = tempfile.mkstemp('.py')
        os.write(fd, bootstrap_script)
        os.close(fd)
        cmd = [py_executable, ez_setup]
    else:
        cmd = [py_executable, '-c', bootstrap_script]
    if unzip:
        cmd.append('--always-unzip')
    env = {}
    remove_from_env = []
    if logger.stdout_level_matches(logger.DEBUG):
        cmd.append('-v')

    old_chdir = os.getcwd()
    if setup_fn is not None and os.path.exists(setup_fn):
        logger.info('Using existing %s egg: %s' % (project_name, setup_fn))
        cmd.append(setup_fn)
        if os.environ.get('PYTHONPATH'):
            env['PYTHONPATH'] = setup_fn + os.path.pathsep + os.environ['PYTHONPATH']
        else:
            env['PYTHONPATH'] = setup_fn
    else:
        # the source is found, let's chdir
        if source is not None and os.path.exists(source):
            logger.info('Using existing %s egg: %s' % (project_name, source))
            os.chdir(os.path.dirname(source))
            # in this case, we want to be sure that PYTHONPATH is unset (not
            # just empty, really unset), else CPython tries to import the
            # site.py that it's in virtualenv_support
            remove_from_env.append('PYTHONPATH')
        else:
            if never_download:
                logger.fatal("Can't find any local distributions of %s to install "
                             "and --never-download is set.  Either re-run virtualenv "
                             "without the --never-download option, or place a %s "
                             "distribution (%s) in one of these "
                             "locations: %r" % (project_name, project_name, 
                                                setup_fn or source,
                                                search_dirs))
                sys.exit(1)

            logger.info('No %s egg found; downloading' % project_name)
        cmd.extend(['--always-copy', '-U', project_name])
    logger.start_progress('Installing %s...' % project_name)
    logger.indent += 2
    cwd = None
    if project_name == 'distribute':
        env['DONT_PATCH_SETUPTOOLS'] = 'true'

    def _filter_ez_setup(line):
        return filter_ez_setup(line, project_name)

    if not os.access(os.getcwd(), os.W_OK):
        cwd = tempfile.mkdtemp()
        if source is not None and os.path.exists(source):
            # the current working dir is hostile, let's copy the
            # tarball to a temp dir
            target = os.path.join(cwd, os.path.split(source)[-1])
            shutil.copy(source, target)
    try:
        call_subprocess(cmd, show_stdout=False,
                        filter_stdout=_filter_ez_setup,
                        extra_env=env,
                        remove_from_env=remove_from_env,
                        cwd=cwd)
    finally:
        logger.indent -= 2
        logger.end_progress()
        if os.getcwd() != old_chdir:
            os.chdir(old_chdir)
        if is_jython and os._name == 'nt':
            os.remove(ez_setup)

def file_search_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = ['.', here,
            join(here, 'virtualenv_support')]
    if os.path.splitext(os.path.dirname(__file__))[0] != 'virtualenv':
        # Probably some boot script; just in case virtualenv is installed...
        try:
            import virtualenv
        except ImportError:
            pass
        else:
            dirs.append(os.path.join(os.path.dirname(virtualenv.__file__), 'virtualenv_support'))
    return [d for d in dirs if os.path.isdir(d)]

def install_setuptools(py_executable, unzip=False,
                       search_dirs=None, never_download=False):
    _install_req(py_executable, unzip, 
                 search_dirs=search_dirs, never_download=never_download)

def install_distribute(py_executable, unzip=False, 
                       search_dirs=None, never_download=False):
    _install_req(py_executable, unzip, distribute=True, 
                 search_dirs=search_dirs, never_download=never_download)

_pip_re = re.compile(r'^pip-.*(zip|tar.gz|tar.bz2|tgz|tbz)$', re.I)
def install_pip(py_executable, search_dirs=None, never_download=False):    
    if search_dirs is None:
        search_dirs = file_search_dirs()

    filenames = []
    for dir in search_dirs:
        filenames.extend([join(dir, fn) for fn in os.listdir(dir)
                          if _pip_re.search(fn)])
    filenames = [(os.path.basename(filename).lower(), i, filename) for i, filename in enumerate(filenames)]
    filenames.sort()
    filenames = [filename for basename, i, filename in filenames]
    if not filenames:
        filename = 'pip'
    else:
        filename = filenames[-1]
    easy_install_script = 'easy_install'
    if sys.platform == 'win32':
        easy_install_script = 'easy_install-script.py'
    cmd = [py_executable, join(os.path.dirname(py_executable), easy_install_script), filename]
    if filename == 'pip':
        if never_download:
            logger.fatal("Can't find any local distributions of pip to install "
                         "and --never-download is set.  Either re-run virtualenv "
                         "without the --never-download option, or place a pip "
                         "source distribution (zip/tar.gz/tar.bz2) in one of these "
                         "locations: %r" % search_dirs)
            sys.exit(1)
        logger.info('Installing pip from network...')
    else:
        logger.info('Installing existing %s distribution: %s' % (
                os.path.basename(filename), filename))
    logger.start_progress('Installing pip...')
    logger.indent += 2
    def _filter_setup(line):
        return filter_ez_setup(line, 'pip')
    try:
        call_subprocess(cmd, show_stdout=False,
                        filter_stdout=_filter_setup)
    finally:
        logger.indent -= 2
        logger.end_progress()

def filter_ez_setup(line, project_name='setuptools'):
    if not line.strip():
        return Logger.DEBUG
    if project_name == 'distribute':
        for prefix in ('Extracting', 'Now working', 'Installing', 'Before',
                       'Scanning', 'Setuptools', 'Egg', 'Already',
                       'running', 'writing', 'reading', 'installing',
                       'creating', 'copying', 'byte-compiling', 'removing',
                       'Processing'):
            if line.startswith(prefix):
                return Logger.DEBUG
        return Logger.DEBUG
    for prefix in ['Reading ', 'Best match', 'Processing setuptools',
                   'Copying setuptools', 'Adding setuptools',
                   'Installing ', 'Installed ']:
        if line.startswith(prefix):
            return Logger.DEBUG
    return Logger.INFO

def main():
    parser = optparse.OptionParser(
        version=virtualenv_version,
        usage="%prog [OPTIONS] DEST_DIR")

    parser.add_option(
        '-v', '--verbose',
        action='count',
        dest='verbose',
        default=0,
        help="Increase verbosity")

    parser.add_option(
        '-q', '--quiet',
        action='count',
        dest='quiet',
        default=0,
        help='Decrease verbosity')

    parser.add_option(
        '-p', '--python',
        dest='python',
        metavar='PYTHON_EXE',
        help='The Python interpreter to use, e.g., --python=python2.5 will use the python2.5 '
        'interpreter to create the new environment.  The default is the interpreter that '
        'virtualenv was installed with (%s)' % sys.executable)

    parser.add_option(
        '--clear',
        dest='clear',
        action='store_true',
        help="Clear out the non-root install and start from scratch")

    parser.add_option(
        '--no-site-packages',
        dest='no_site_packages',
        action='store_true',
        help="Don't give access to the global site-packages dir to the "
             "virtual environment")

    parser.add_option(
        '--unzip-setuptools',
        dest='unzip_setuptools',
        action='store_true',
        help="Unzip Setuptools or Distribute when installing it")

    parser.add_option(
        '--relocatable',
        dest='relocatable',
        action='store_true',
        help='Make an EXISTING virtualenv environment relocatable.  '
        'This fixes up scripts and makes all .pth files relative')

    parser.add_option(
        '--distribute',
        dest='use_distribute',
        action='store_true',
        help='Use Distribute instead of Setuptools. Set environ variable '
        'VIRTUALENV_USE_DISTRIBUTE to make it the default ')

    default_search_dirs = file_search_dirs()
    parser.add_option(
        '--extra-search-dir',
        dest="search_dirs",
        action="append",
        default=default_search_dirs,
        help="Directory to look for setuptools/distribute/pip distributions in. "
        "You can add any number of additional --extra-search-dir paths.")

    parser.add_option(
        '--never-download',
        dest="never_download",
        action="store_true",
        help="Never download anything from the network.  Instead, virtualenv will fail "
        "if local distributions of setuptools/distribute/pip are not present.")

    parser.add_option(
        '--prompt=',
        dest='prompt',
        help='Provides an alternative prompt prefix for this environment')

    if 'extend_parser' in globals():
        extend_parser(parser)

    options, args = parser.parse_args()

    global logger

    if 'adjust_options' in globals():
        adjust_options(options, args)

    verbosity = options.verbose - options.quiet
    logger = Logger([(Logger.level_for_integer(2-verbosity), sys.stdout)])

    if options.python and not os.environ.get('VIRTUALENV_INTERPRETER_RUNNING'):
        env = os.environ.copy()
        interpreter = resolve_interpreter(options.python)
        if interpreter == sys.executable:
            logger.warn('Already using interpreter %s' % interpreter)
        else:
            logger.notify('Running virtualenv with interpreter %s' % interpreter)
            env['VIRTUALENV_INTERPRETER_RUNNING'] = 'true'
            file = __file__
            if file.endswith('.pyc'):
                file = file[:-1]
            popen = subprocess.Popen([interpreter, file] + sys.argv[1:], env=env)
            raise SystemExit(popen.wait())

    if not args:
        print('You must provide a DEST_DIR')
        parser.print_help()
        sys.exit(2)
    if len(args) > 1:
        print('There must be only one argument: DEST_DIR (you gave %s)' % (
            ' '.join(args)))
        parser.print_help()
        sys.exit(2)

    home_dir = args[0]

    if os.environ.get('WORKING_ENV'):
        logger.fatal('ERROR: you cannot run virtualenv while in a workingenv')
        logger.fatal('Please deactivate your workingenv, then re-run this script')
        sys.exit(3)

    if 'PYTHONHOME' in os.environ:
        logger.warn('PYTHONHOME is set.  You *must* activate the virtualenv before using it')
        del os.environ['PYTHONHOME']

    if options.relocatable:
        make_environment_relocatable(home_dir)
        return

    create_environment(home_dir, site_packages=not options.no_site_packages, clear=options.clear,
                       unzip_setuptools=options.unzip_setuptools,
                       use_distribute=options.use_distribute or majver > 2,
                       prompt=options.prompt,
                       search_dirs=options.search_dirs,
                       never_download=options.never_download)
    if 'after_install' in globals():
        after_install(options, home_dir)

def call_subprocess(cmd, show_stdout=True,
                    filter_stdout=None, cwd=None,
                    raise_on_returncode=True, extra_env=None,
                    remove_from_env=None):
    cmd_parts = []
    for part in cmd:
        if len(part) > 45:
            part = part[:20]+"..."+part[-20:]
        if ' ' in part or '\n' in part or '"' in part or "'" in part:
            part = '"%s"' % part.replace('"', '\\"')
        cmd_parts.append(part)
    cmd_desc = ' '.join(cmd_parts)
    if show_stdout:
        stdout = None
    else:
        stdout = subprocess.PIPE
    logger.debug("Running command %s" % cmd_desc)
    if extra_env or remove_from_env:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        if remove_from_env:
            for varname in remove_from_env:
                env.pop(varname, None)
    else:
        env = None
    try:
        proc = subprocess.Popen(
            cmd, stderr=subprocess.STDOUT, stdin=None, stdout=stdout,
            cwd=cwd, env=env)
    except Exception:
        e = sys.exc_info()[1]
        logger.fatal(
            "Error %s while executing command %s" % (e, cmd_desc))
        raise
    all_output = []
    if stdout is not None:
        stdout = proc.stdout
        encoding = sys.getdefaultencoding()
        while 1:
            line = stdout.readline().decode(encoding)
            if not line:
                break
            line = line.rstrip()
            all_output.append(line)
            if filter_stdout:
                level = filter_stdout(line)
                if isinstance(level, tuple):
                    level, line = level
                logger.log(level, line)
                if not logger.stdout_level_matches(level):
                    logger.show_progress()
            else:
                logger.info(line)
    else:
        proc.communicate()
    proc.wait()
    if proc.returncode:
        if raise_on_returncode:
            if all_output:
                logger.notify('Complete output from command %s:' % cmd_desc)
                logger.notify('\n'.join(all_output) + '\n----------------------------------------')
            raise OSError(
                "Command %s failed with error code %s"
                % (cmd_desc, proc.returncode))
        else:
            logger.warn(
                "Command %s had error code %s"
                % (cmd_desc, proc.returncode))


def create_environment(home_dir, site_packages=True, clear=False,
                       unzip_setuptools=False, use_distribute=False,
                       prompt=None, search_dirs=None, never_download=False):
    """
    Creates a new environment in ``home_dir``.

    If ``site_packages`` is true (the default) then the global
    ``site-packages/`` directory will be on the path.

    If ``clear`` is true (default False) then the environment will
    first be cleared.
    """
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)

    py_executable = os.path.abspath(install_python(
        home_dir, lib_dir, inc_dir, bin_dir,
        site_packages=site_packages, clear=clear))

    install_distutils(home_dir)

    if use_distribute or os.environ.get('VIRTUALENV_USE_DISTRIBUTE'):
        install_distribute(py_executable, unzip=unzip_setuptools, 
                           search_dirs=search_dirs, never_download=never_download)
    else:
        install_setuptools(py_executable, unzip=unzip_setuptools, 
                           search_dirs=search_dirs, never_download=never_download)

    install_pip(py_executable, search_dirs=search_dirs, never_download=never_download)

    install_activate(home_dir, bin_dir, prompt)

def path_locations(home_dir):
    """Return the path locations for the environment (where libraries are,
    where scripts go, etc)"""
    # XXX: We'd use distutils.sysconfig.get_python_inc/lib but its
    # prefix arg is broken: http://bugs.python.org/issue3386
    if sys.platform == 'win32':
        # Windows has lots of problems with executables with spaces in
        # the name; this function will remove them (using the ~1
        # format):
        mkdir(home_dir)
        if ' ' in home_dir:
            try:
                import win32api
            except ImportError:
                print('Error: the path "%s" has a space in it' % home_dir)
                print('To handle these kinds of paths, the win32api module must be installed:')
                print('  http://sourceforge.net/projects/pywin32/')
                sys.exit(3)
            home_dir = win32api.GetShortPathName(home_dir)
        lib_dir = join(home_dir, 'Lib')
        inc_dir = join(home_dir, 'Include')
        bin_dir = join(home_dir, 'Scripts')
    elif is_jython:
        lib_dir = join(home_dir, 'Lib')
        inc_dir = join(home_dir, 'Include')
        bin_dir = join(home_dir, 'bin')
    elif is_pypy:
        lib_dir = home_dir
        inc_dir = join(home_dir, 'include')
        bin_dir = join(home_dir, 'bin')
    else:
        lib_dir = join(home_dir, 'lib', py_version)
        inc_dir = join(home_dir, 'include', py_version + abiflags)
        bin_dir = join(home_dir, 'bin')
    return home_dir, lib_dir, inc_dir, bin_dir


def change_prefix(filename, dst_prefix):
    prefixes = [sys.prefix]

    if sys.platform == "darwin":
        prefixes.extend((
            os.path.join("/Library/Python", sys.version[:3], "site-packages"),
            os.path.join(sys.prefix, "Extras", "lib", "python"),
            os.path.join("~", "Library", "Python", sys.version[:3], "site-packages")))

    if hasattr(sys, 'real_prefix'):
        prefixes.append(sys.real_prefix)
    prefixes = list(map(os.path.abspath, prefixes))
    filename = os.path.abspath(filename)
    for src_prefix in prefixes:
        if filename.startswith(src_prefix):
            _, relpath = filename.split(src_prefix, 1)
            assert relpath[0] == os.sep
            relpath = relpath[1:]
            return join(dst_prefix, relpath)
    assert False, "Filename %s does not start with any of these prefixes: %s" % \
        (filename, prefixes)

def copy_required_modules(dst_prefix):
    import imp
    for modname in REQUIRED_MODULES:
        if modname in sys.builtin_module_names:
            logger.info("Ignoring built-in bootstrap module: %s" % modname)
            continue
        try:
            f, filename, _ = imp.find_module(modname)
        except ImportError:
            logger.info("Cannot import bootstrap module: %s" % modname)
        else:
            if f is not None:
                f.close()
            dst_filename = change_prefix(filename, dst_prefix)
            copyfile(filename, dst_filename)
            if filename.endswith('.pyc'):
                pyfile = filename[:-1]
                if os.path.exists(pyfile):
                    copyfile(pyfile, dst_filename[:-1])


def install_python(home_dir, lib_dir, inc_dir, bin_dir, site_packages, clear):
    """Install just the base environment, no distutils patches etc"""
    if sys.executable.startswith(bin_dir):
        print('Please use the *system* python to run this script')
        return

    if clear:
        rmtree(lib_dir)
        ## FIXME: why not delete it?
        ## Maybe it should delete everything with #!/path/to/venv/python in it
        logger.notify('Not deleting %s', bin_dir)

    if hasattr(sys, 'real_prefix'):
        logger.notify('Using real prefix %r' % sys.real_prefix)
        prefix = sys.real_prefix
    else:
        prefix = sys.prefix
    mkdir(lib_dir)
    fix_lib64(lib_dir)
    fix_local_scheme(home_dir)
    stdlib_dirs = [os.path.dirname(os.__file__)]
    if sys.platform == 'win32':
        stdlib_dirs.append(join(os.path.dirname(stdlib_dirs[0]), 'DLLs'))
    elif sys.platform == 'darwin':
        stdlib_dirs.append(join(stdlib_dirs[0], 'site-packages'))
    if hasattr(os, 'symlink'):
        logger.info('Symlinking Python bootstrap modules')
    else:
        logger.info('Copying Python bootstrap modules')
    logger.indent += 2
    try:
        # copy required files...
        for stdlib_dir in stdlib_dirs:
            if not os.path.isdir(stdlib_dir):
                continue
            for fn in os.listdir(stdlib_dir):
                bn = os.path.splitext(fn)[0]
                if fn != 'site-packages' and bn in REQUIRED_FILES:
                    copyfile(join(stdlib_dir, fn), join(lib_dir, fn))
        # ...and modules
        copy_required_modules(home_dir)
    finally:
        logger.indent -= 2
    mkdir(join(lib_dir, 'site-packages'))
    import site
    site_filename = site.__file__
    if site_filename.endswith('.pyc'):
        site_filename = site_filename[:-1]
    elif site_filename.endswith('$py.class'):
        site_filename = site_filename.replace('$py.class', '.py')
    site_filename_dst = change_prefix(site_filename, home_dir)
    site_dir = os.path.dirname(site_filename_dst)
    writefile(site_filename_dst, SITE_PY)
    writefile(join(site_dir, 'orig-prefix.txt'), prefix)
    site_packages_filename = join(site_dir, 'no-global-site-packages.txt')
    if not site_packages:
        writefile(site_packages_filename, '')
    else:
        if os.path.exists(site_packages_filename):
            logger.info('Deleting %s' % site_packages_filename)
            os.unlink(site_packages_filename)

    if is_pypy or is_win:
        stdinc_dir = join(prefix, 'include')
    else:
        stdinc_dir = join(prefix, 'include', py_version + abiflags)
    if os.path.exists(stdinc_dir):
        copyfile(stdinc_dir, inc_dir)
    else:
        logger.debug('No include dir %s' % stdinc_dir)

    # pypy never uses exec_prefix, just ignore it
    if sys.exec_prefix != prefix and not is_pypy:
        if sys.platform == 'win32':
            exec_dir = join(sys.exec_prefix, 'lib')
        elif is_jython:
            exec_dir = join(sys.exec_prefix, 'Lib')
        else:
            exec_dir = join(sys.exec_prefix, 'lib', py_version)
        for fn in os.listdir(exec_dir):
            copyfile(join(exec_dir, fn), join(lib_dir, fn))

    if is_jython:
        # Jython has either jython-dev.jar and javalib/ dir, or just
        # jython.jar
        for name in 'jython-dev.jar', 'javalib', 'jython.jar':
            src = join(prefix, name)
            if os.path.exists(src):
                copyfile(src, join(home_dir, name))
        # XXX: registry should always exist after Jython 2.5rc1
        src = join(prefix, 'registry')
        if os.path.exists(src):
            copyfile(src, join(home_dir, 'registry'), symlink=False)
        copyfile(join(prefix, 'cachedir'), join(home_dir, 'cachedir'),
                 symlink=False)

    mkdir(bin_dir)
    py_executable = join(bin_dir, os.path.basename(sys.executable))
    if 'Python.framework' in prefix:
        if re.search(r'/Python(?:-32|-64)*$', py_executable):
            # The name of the python executable is not quite what
            # we want, rename it.
            py_executable = os.path.join(
                    os.path.dirname(py_executable), 'python')

    logger.notify('New %s executable in %s', expected_exe, py_executable)
    if sys.executable != py_executable:
        ## FIXME: could I just hard link?
        executable = sys.executable
        if sys.platform == 'cygwin' and os.path.exists(executable + '.exe'):
            # Cygwin misreports sys.executable sometimes
            executable += '.exe'
            py_executable += '.exe'
            logger.info('Executable actually exists in %s' % executable)
        shutil.copyfile(executable, py_executable)
        make_exe(py_executable)
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
            if os.path.exists(pythonw):
                logger.info('Also created pythonw.exe')
                shutil.copyfile(pythonw, os.path.join(os.path.dirname(py_executable), 'pythonw.exe'))
        if is_pypy:
            # make a symlink python --> pypy-c
            python_executable = os.path.join(os.path.dirname(py_executable), 'python')
            logger.info('Also created executable %s' % python_executable)
            copyfile(py_executable, python_executable)

    if os.path.splitext(os.path.basename(py_executable))[0] != expected_exe:
        secondary_exe = os.path.join(os.path.dirname(py_executable),
                                     expected_exe)
        py_executable_ext = os.path.splitext(py_executable)[1]
        if py_executable_ext == '.exe':
            # python2.4 gives an extension of '.4' :P
            secondary_exe += py_executable_ext
        if os.path.exists(secondary_exe):
            logger.warn('Not overwriting existing %s script %s (you must use %s)'
                        % (expected_exe, secondary_exe, py_executable))
        else:
            logger.notify('Also creating executable in %s' % secondary_exe)
            shutil.copyfile(sys.executable, secondary_exe)
            make_exe(secondary_exe)

    if 'Python.framework' in prefix:
        logger.debug('MacOSX Python framework detected')

        # Make sure we use the the embedded interpreter inside
        # the framework, even if sys.executable points to
        # the stub executable in ${sys.prefix}/bin
        # See http://groups.google.com/group/python-virtualenv/
        #                              browse_thread/thread/17cab2f85da75951
        original_python = os.path.join(
            prefix, 'Resources/Python.app/Contents/MacOS/Python')
        shutil.copy(original_python, py_executable)

        # Copy the framework's dylib into the virtual
        # environment
        virtual_lib = os.path.join(home_dir, '.Python')

        if os.path.exists(virtual_lib):
            os.unlink(virtual_lib)
        copyfile(
            os.path.join(prefix, 'Python'),
            virtual_lib)

        # And then change the install_name of the copied python executable
        try:
            call_subprocess(
                ["install_name_tool", "-change",
                 os.path.join(prefix, 'Python'),
                 '@executable_path/../.Python',
                 py_executable])
        except:
            logger.fatal(
                "Could not call install_name_tool -- you must have Apple's development tools installed")
            raise

        # Some tools depend on pythonX.Y being present
        py_executable_version = '%s.%s' % (
            sys.version_info[0], sys.version_info[1])
        if not py_executable.endswith(py_executable_version):
            # symlinking pythonX.Y > python
            pth = py_executable + '%s.%s' % (
                    sys.version_info[0], sys.version_info[1])
            if os.path.exists(pth):
                os.unlink(pth)
            os.symlink('python', pth)
        else:
            # reverse symlinking python -> pythonX.Y (with --python)
            pth = join(bin_dir, 'python')
            if os.path.exists(pth):
                os.unlink(pth)
            os.symlink(os.path.basename(py_executable), pth)

    if sys.platform == 'win32' and ' ' in py_executable:
        # There's a bug with subprocess on Windows when using a first
        # argument that has a space in it.  Instead we have to quote
        # the value:
        py_executable = '"%s"' % py_executable
    cmd = [py_executable, '-c', 'import sys; print(sys.prefix)']
    logger.info('Testing executable with %s %s "%s"' % tuple(cmd))
    try:
        proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE)
        proc_stdout, proc_stderr = proc.communicate()
    except OSError:
        e = sys.exc_info()[1]
        if e.errno == errno.EACCES:
            logger.fatal('ERROR: The executable %s could not be run: %s' % (py_executable, e))
            sys.exit(100)
        else:
          raise e

    proc_stdout = proc_stdout.strip().decode(sys.getdefaultencoding())
    proc_stdout = os.path.normcase(os.path.abspath(proc_stdout))
    if proc_stdout != os.path.normcase(os.path.abspath(home_dir)):
        logger.fatal(
            'ERROR: The executable %s is not functioning' % py_executable)
        logger.fatal(
            'ERROR: It thinks sys.prefix is %r (should be %r)'
            % (proc_stdout, os.path.normcase(os.path.abspath(home_dir))))
        logger.fatal(
            'ERROR: virtualenv is not compatible with this system or executable')
        if sys.platform == 'win32':
            logger.fatal(
                'Note: some Windows users have reported this error when they installed Python for "Only this user".  The problem may be resolvable if you install Python "For all users".  (See https://bugs.launchpad.net/virtualenv/+bug/352844)')
        sys.exit(100)
    else:
        logger.info('Got sys.prefix result: %r' % proc_stdout)

    pydistutils = os.path.expanduser('~/.pydistutils.cfg')
    if os.path.exists(pydistutils):
        logger.notify('Please make sure you remove any previous custom paths from '
                      'your %s file.' % pydistutils)
    ## FIXME: really this should be calculated earlier
    return py_executable

def install_activate(home_dir, bin_dir, prompt=None):
    if sys.platform == 'win32' or is_jython and os._name == 'nt':
        files = {'activate.bat': ACTIVATE_BAT,
                 'deactivate.bat': DEACTIVATE_BAT}
        if os.environ.get('OS') == 'Windows_NT' and os.environ.get('OSTYPE') == 'cygwin':
            files['activate'] = ACTIVATE_SH
    else:
        files = {'activate': ACTIVATE_SH}

        # suppling activate.fish in addition to, not instead of, the
        # bash script support.
        files['activate.fish'] = ACTIVATE_FISH

        # same for csh/tcsh support...
        files['activate.csh'] = ACTIVATE_CSH



    files['activate_this.py'] = ACTIVATE_THIS
    vname = os.path.basename(os.path.abspath(home_dir))
    for name, content in files.items():
        content = content.replace('__VIRTUAL_PROMPT__', prompt or '')
        content = content.replace('__VIRTUAL_WINPROMPT__', prompt or '(%s)' % vname)
        content = content.replace('__VIRTUAL_ENV__', os.path.abspath(home_dir))
        content = content.replace('__VIRTUAL_NAME__', vname)
        content = content.replace('__BIN_NAME__', os.path.basename(bin_dir))
        writefile(os.path.join(bin_dir, name), content)

def install_distutils(home_dir):
    distutils_path = change_prefix(distutils.__path__[0], home_dir)
    mkdir(distutils_path)
    ## FIXME: maybe this prefix setting should only be put in place if
    ## there's a local distutils.cfg with a prefix setting?
    home_dir = os.path.abspath(home_dir)
    ## FIXME: this is breaking things, removing for now:
    #distutils_cfg = DISTUTILS_CFG + "\n[install]\nprefix=%s\n" % home_dir
    writefile(os.path.join(distutils_path, '__init__.py'), DISTUTILS_INIT)
    writefile(os.path.join(distutils_path, 'distutils.cfg'), DISTUTILS_CFG, overwrite=False)

def fix_local_scheme(home_dir):
    """
    Platforms that use the "posix_local" install scheme (like Ubuntu with
    Python 2.7) need to be given an additional "local" location, sigh.
    """
    try:
        import sysconfig
    except ImportError:
        pass
    else:
        if sysconfig._get_default_scheme() == 'posix_local':
            local_path = os.path.join(home_dir, 'local')
            if not os.path.exists(local_path):
                os.symlink(os.path.abspath(home_dir), local_path)

def fix_lib64(lib_dir):
    """
    Some platforms (particularly Gentoo on x64) put things in lib64/pythonX.Y
    instead of lib/pythonX.Y.  If this is such a platform we'll just create a
    symlink so lib64 points to lib
    """
    if [p for p in distutils.sysconfig.get_config_vars().values()
        if isinstance(p, basestring) and 'lib64' in p]:
        logger.debug('This system uses lib64; symlinking lib64 to lib')
        assert os.path.basename(lib_dir) == 'python%s' % sys.version[:3], (
            "Unexpected python lib dir: %r" % lib_dir)
        lib_parent = os.path.dirname(lib_dir)
        assert os.path.basename(lib_parent) == 'lib', (
            "Unexpected parent dir: %r" % lib_parent)
        copyfile(lib_parent, os.path.join(os.path.dirname(lib_parent), 'lib64'))

def resolve_interpreter(exe):
    """
    If the executable given isn't an absolute path, search $PATH for the interpreter
    """
    if os.path.abspath(exe) != exe:
        paths = os.environ.get('PATH', '').split(os.pathsep)
        for path in paths:
            if os.path.exists(os.path.join(path, exe)):
                exe = os.path.join(path, exe)
                break
    if not os.path.exists(exe):
        logger.fatal('The executable %s (from --python=%s) does not exist' % (exe, exe))
        raise SystemExit(3)
    if not is_executable(exe):
        logger.fatal('The executable %s (from --python=%s) is not executable' % (exe, exe))
        raise SystemExit(3)
    return exe

def is_executable(exe):
    """Checks a file is executable"""
    return os.access(exe, os.X_OK)

############################################################
## Relocating the environment:

def make_environment_relocatable(home_dir):
    """
    Makes the already-existing environment use relative paths, and takes out
    the #!-based environment selection in scripts.
    """
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)
    activate_this = os.path.join(bin_dir, 'activate_this.py')
    if not os.path.exists(activate_this):
        logger.fatal(
            'The environment doesn\'t have a file %s -- please re-run virtualenv '
            'on this environment to update it' % activate_this)
    fixup_scripts(home_dir)
    fixup_pth_and_egg_link(home_dir)
    ## FIXME: need to fix up distutils.cfg

OK_ABS_SCRIPTS = ['python', 'python%s' % sys.version[:3],
                  'activate', 'activate.bat', 'activate_this.py']

def fixup_scripts(home_dir):
    # This is what we expect at the top of scripts:
    shebang = '#!%s/bin/python' % os.path.normcase(os.path.abspath(home_dir))
    # This is what we'll put:
    new_shebang = '#!/usr/bin/env python%s' % sys.version[:3]
    activate = "import os; activate_this=os.path.join(os.path.dirname(__file__), 'activate_this.py'); execfile(activate_this, dict(__file__=activate_this)); del os, activate_this"
    if sys.platform == 'win32':
        bin_suffix = 'Scripts'
    else:
        bin_suffix = 'bin'
    bin_dir = os.path.join(home_dir, bin_suffix)
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)
    for filename in os.listdir(bin_dir):
        filename = os.path.join(bin_dir, filename)
        if not os.path.isfile(filename):
            # ignore subdirs, e.g. .svn ones.
            continue
        f = open(filename, 'rb')
        lines = f.readlines()
        f.close()
        if not lines:
            logger.warn('Script %s is an empty file' % filename)
            continue
        if not lines[0].strip().startswith(shebang):
            if os.path.basename(filename) in OK_ABS_SCRIPTS:
                logger.debug('Cannot make script %s relative' % filename)
            elif lines[0].strip() == new_shebang:
                logger.info('Script %s has already been made relative' % filename)
            else:
                logger.warn('Script %s cannot be made relative (it\'s not a normal script that starts with %s)'
                            % (filename, shebang))
            continue
        logger.notify('Making script %s relative' % filename)
        lines = [new_shebang+'\n', activate+'\n'] + lines[1:]
        f = open(filename, 'wb')
        f.writelines(lines)
        f.close()

def fixup_pth_and_egg_link(home_dir, sys_path=None):
    """Makes .pth and .egg-link files use relative paths"""
    home_dir = os.path.normcase(os.path.abspath(home_dir))
    if sys_path is None:
        sys_path = sys.path
    for path in sys_path:
        if not path:
            path = '.'
        if not os.path.isdir(path):
            continue
        path = os.path.normcase(os.path.abspath(path))
        if not path.startswith(home_dir):
            logger.debug('Skipping system (non-environment) directory %s' % path)
            continue
        for filename in os.listdir(path):
            filename = os.path.join(path, filename)
            if filename.endswith('.pth'):
                if not os.access(filename, os.W_OK):
                    logger.warn('Cannot write .pth file %s, skipping' % filename)
                else:
                    fixup_pth_file(filename)
            if filename.endswith('.egg-link'):
                if not os.access(filename, os.W_OK):
                    logger.warn('Cannot write .egg-link file %s, skipping' % filename)
                else:
                    fixup_egg_link(filename)

def fixup_pth_file(filename):
    lines = []
    prev_lines = []
    f = open(filename)
    prev_lines = f.readlines()
    f.close()
    for line in prev_lines:
        line = line.strip()
        if (not line or line.startswith('#') or line.startswith('import ')
            or os.path.abspath(line) != line):
            lines.append(line)
        else:
            new_value = make_relative_path(filename, line)
            if line != new_value:
                logger.debug('Rewriting path %s as %s (in %s)' % (line, new_value, filename))
            lines.append(new_value)
    if lines == prev_lines:
        logger.info('No changes to .pth file %s' % filename)
        return
    logger.notify('Making paths in .pth file %s relative' % filename)
    f = open(filename, 'w')
    f.write('\n'.join(lines) + '\n')
    f.close()

def fixup_egg_link(filename):
    f = open(filename)
    link = f.read().strip()
    f.close()
    if os.path.abspath(link) != link:
        logger.debug('Link in %s already relative' % filename)
        return
    new_link = make_relative_path(filename, link)
    logger.notify('Rewriting link %s in %s as %s' % (link, filename, new_link))
    f = open(filename, 'w')
    f.write(new_link)
    f.close()

def make_relative_path(source, dest, dest_is_directory=True):
    """
    Make a filename relative, where the filename is dest, and it is
    being referred to from the filename source.

        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/usr/share/another-place/src/Directory')
        '../another-place/src/Directory'
        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/home/user/src/Directory')
        '../../../home/user/src/Directory'
        >>> make_relative_path('/usr/share/a-file.pth', '/usr/share/')
        './'
    """
    source = os.path.dirname(source)
    if not dest_is_directory:
        dest_filename = os.path.basename(dest)
        dest = os.path.dirname(dest)
    dest = os.path.normpath(os.path.abspath(dest))
    source = os.path.normpath(os.path.abspath(source))
    dest_parts = dest.strip(os.path.sep).split(os.path.sep)
    source_parts = source.strip(os.path.sep).split(os.path.sep)
    while dest_parts and source_parts and dest_parts[0] == source_parts[0]:
        dest_parts.pop(0)
        source_parts.pop(0)
    full_parts = ['..']*len(source_parts) + dest_parts
    if not dest_is_directory:
        full_parts.append(dest_filename)
    if not full_parts:
        # Special case for the current directory (otherwise it'd be '')
        return './'
    return os.path.sep.join(full_parts)



############################################################
## Bootstrap script creation:

def create_bootstrap_script(extra_text, python_version=''):
    """
    Creates a bootstrap script, which is like this script but with
    extend_parser, adjust_options, and after_install hooks.

    This returns a string that (written to disk of course) can be used
    as a bootstrap script with your own customizations.  The script
    will be the standard virtualenv.py script, with your extra text
    added (your extra text should be Python code).

    If you include these functions, they will be called:

    ``extend_parser(optparse_parser)``:
        You can add or remove options from the parser here.

    ``adjust_options(options, args)``:
        You can change options here, or change the args (if you accept
        different kinds of arguments, be sure you modify ``args`` so it is
        only ``[DEST_DIR]``).

    ``after_install(options, home_dir)``:

        After everything is installed, this function is called.  This
        is probably the function you are most likely to use.  An
        example would be::

            def after_install(options, home_dir):
                subprocess.call([join(home_dir, 'bin', 'easy_install'),
                                 'MyPackage'])
                subprocess.call([join(home_dir, 'bin', 'my-package-script'),
                                 'setup', home_dir])

        This example immediately installs a package, and runs a setup
        script from that package.

    If you provide something like ``python_version='2.4'`` then the
    script will start with ``#!/usr/bin/env python2.4`` instead of
    ``#!/usr/bin/env python``.  You can use this when the script must
    be run with a particular Python version.
    """
    filename = __file__
    if filename.endswith('.pyc'):
        filename = filename[:-1]
    f = open(filename, 'rb')
    content = f.read()
    f.close()
    py_exe = 'python%s' % python_version
    content = (('#!/usr/bin/env %s\n' % py_exe)
               + '## WARNING: This file is generated\n'
               + content)
    return content.replace('##EXT' 'END##', extra_text)

##EXTEND##

def convert(s):
    b = base64.b64decode(s.encode('ascii'))
    return zlib.decompress(b).decode('utf-8')
    
##file site.py
SITE_PY = convert("""
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
""")

##file ez_setup.py
EZ_SETUP_PY = convert("""
eJzNWmtv49a1/a5fwSgwJGE0NN8PDzRFmkyBAYrcIo8CFx5XPk+LHYpUSWoctch/v+ucQ1KkZDrt
RT6UwcQ2ebjPfq6195G+/upwanZlMZvP538sy6ZuKnKwatEcD01Z5rWVFXVD8pw0GRbNPkrrVB6t
Z1I0VlNax1qM16qnlXUg7DN5EovaPLQPp7X192PdYAHLj1xYzS6rZzLLhXql2UEI2QuLZ5VgTVmd
rOes2VlZs7ZIwS3CuX5BbajWNuXBKqXZqZN/dzebWbhkVe4t8c+tvm9l+0NZNUrL7VlLvW58a7m6
sqwS/zhCHYtY9UGwTGbM+iKqGk5Qe59fXavfsYqXz0VeEj7bZ1VVVmurrLR3SGGRvBFVQRrRLzpb
utabMqzipVWXFj1Z9fFwyE9Z8TRTxpLDoSoPVaZeLw8qCNoPj4+XFjw+2rPZT8pN2q9Mb6wkCqs6
4vdamcKq7KDNa6OqtTw8VYQP42irZJi1zqtP9ey7D3/65uc//7T964cffvz4P99bG2vu2BFz3Xn/
6Ocf/qz8qh7tmuZwd3t7OB0y2ySXXVZPt21S1Lc39S3+63e7nVs3ahe79e/9nf8wm+15uOWkIRD4
Lx2xxfmNt9icum8PJ8/2bfH0tLizFknieYzI1HG90OFJkNA0jWgsvZBFImJksX5FStBJoXFKEhI4
vghCx5OUJqEQvnTTwI39kNEJKd5YlzAK4zhMeUIinkgWBE7skJQ7sRd7PE1fl9LrEsAAknA3SrlH
RRS5kvgeiUToiUAm3pRF/lgXSn2XOZLFfpqSyA/jNI1DRngqQ+JEbvKqlF4XPyEJw10eCcY9zwti
6capjDmJolQSNiElGOsSeU4QEi8QPBCuoCyOpXD8lJBARDIW4atSzn5h1CNuEkKPhBMmJfW4C30c
n/rUZcHLUthFvlBfejQM/ZRHiGss44DwOHU9CCKpk0xYxC7zBfZwweHJKOYe96QUbuA4qR8F0iPB
RKSZ64yVYXCHR2jIfeJ4YRSEEeLDXD9xHBI7qfO6mF6bMOZ4ETFKaeLEscfClIQ+SQLfJyHnk54x
YsJODBdBRFgCX6YxS9IwjD0RiiREOgqasPh1MVGvTSJQSURIJ4KDPCaiwA0gzYORcPhEtAEqY994
lAiCGnZ9jvdRRl4iYkpCGhJoxMXrYs6R4pGfypQ6EBawwAvS2PEDLpgnmMO8yUi5Y99EAUsD6VMZ
kxhZ6AuW+MKhHsIdByn1XhfT+4ZKknqu41COMHHUBCQJzn0EPgqcJJoQc4Ez0nGigMqIEI/G3IFa
8GyAxHYSN2beVKAucCZyIzf1hGB+KINYIGpuxHhEXA9SvXhKygXOSDcBQAF8uUSqEC9MWQop0uUx
jRM5gVbsAmeEI3gcRInH0jShksbwdOIgex3EPHangu2Pg0SokG4kOYdhYRi6QRK4LAZ+8TRJo3BK
ygVaUYemru8SRqjvOXAGcC6WQcBCAEXsylel9BYhSST2jHggqfRRUVSmQcQcuAqoJ6YSJhhblCi0
BvD7HuM0ZbFHmQwAX14kvYTIKbQKxxYJkUqeOFAHBYmMlb4ApocxAIMnbjQV6XBsEZHAKi7BKm7s
uELAuTHIKaQMhEeiKZQJL2KUcF9GAISAMUKS2A2QONyPKWPc5yGfkBKNLULBJGD5xHUjMFGSBLEH
EWDMMEhR2lPAGV2wGwsjIsOYwr/oHlANkQNDgsBHgYVkChuisUXUkwmJQw9kD9ilPkjaQai5CCVa
idCfkBJfwJ2DGMmUcOaTyA1F6LohyhAtRQIInMyX+IIJSCLTMAALcGC5I2kUM+lKD2HAI2+qAuKx
RQE4lgBvJVoGFGDgB67rSi4S38W/eEqX5KIbclQv5KXwSMrBHyoFAeCJ76jGynldSm8Ro8RPgA3o
OYLEZ47KWWQbnM3ALJM0kIwtcmPPjQFyCHTKmRs6YeqQMKG+QJ2n4VSk07FF0J0FDpoZV3mYBmkk
AiapcBLYypypSKcXyIAkQ2MHbvWThEdAJyKEEwG8WOQHU/1dK6W3SAqE1hchcWPqegxhYmHg0hjc
C+YXU0ySjvmIEZSNKxVqEk9wAJOb+mC2mIaphx4HUn6dDSYCjDf1rKlOd2bg2pF6l2e0m7fQu8/E
L0xg1Pio73xQI1G7Fg+H62ZcSGv7heQZun2xxa0ldNoWmAfXlhoAVnfagExa3X01M3bjgXmoLp5h
tmgwLigR+kV7J34xdzHfdcsgp1351aaXct+JfjjLUxfmLkyD79+r6aRuuKgw1y1HK9Q1Vya1FrTz
4Q2mMIIxjH9lWcu/lHWd0Xww/mGkw9/7P6zmV8JuejNHj1ajv5Q+4pesWXrmfoXgVoV2l3HoxXCo
F7Xj1eZimFv3am0pqcVmMNCtMSluMapuytpmxwq/mWTqX+AiJ6eNG87aIGFs/ObYlHv4gWG6PGEU
Lfhtb/bgpEDN9XvyGbHE8PwFriLKQXCeMu1Amp0Z5x9bpR+telcec66mWWJ8PZTWTebFcU9FZTU7
0lgYhHvBWpaagAvlXUti6u2VOhZcvyKsx5EjHi010i6fdxnbdbsLaK2OJow8a3G7WNlQ0njpUW2p
5AyOMXaiGh2QPGeYuek5EwRfIyNNgmuVixL+yCtB+OmsPvb4KAfqabfr7dqzCS2mabXU0qjQqrQO
0ScWrCx4bXzTqXEgSBTlVHhElVXWZAhd8TQ4zzARb+0vC6HPE8zZCDd6wallrnz44vmI0rI9bBCt
MH2WU5VH7CSMKqbOiLUXdU2ehDngOBfd46POl4pktbB+PNWN2H/4RfmrMIEoLNLgnjnZIFRBizJe
paAyxpx62F2G6p/PpN4aFIL9G2tx+Py0rURdHism6oVCGLX9vuTHXNTqlGQAoJePTU2g6jjyoHXb
cnVGEpVym3PRDOqy9dhFCXZlt74otDMGdEViw7OiapbOWm0yALkWqPud3g1Pd2h3zLdtA7PVwLxR
MkyAAOyXskYO0g9fQPj+pQ6Qhg5pH13vMBJtt8m1nJ81fr+Zv2ldtXrXyh6qMBbwV7Py27KQecaa
QRxgokFOBstluVzduw9DYhgmxX9KBPOfdufCmCiF5fvNTb3qy7wrb33K+akYc8GckWLRqGrrqwdw
ok72dPm0J3mqkI5FgSy3rb/kAsnTLb+Sp8pLVTmwScCWTkOZVXWzBmGoSllAwqnLCuvtzwPlF/aF
vE/Fp2L57bGqIA1IbwTcVBeUtgKhndNc2KR6qu+dh9fp7MWwfpchZzN6VBT7fdn8qQRwD3KI1PWs
LcR8/OZ6WKv3F5X+oF75Gk7RXFB+HtHpMHsNr75UxL83uapSR6aOWPW7FyhUFy05U4CVl8w0IBos
jQ1ZY86DdUPxX0qpBpDViX9Hqb/FqOqe2vWaTg3KP54ZcoIFS8N9HfUpCmHNkeRnI1pKGdNG94FC
BWahHjJrh3zMTdJ23enGGkDX25sanfZNrRrt+bAWLg68TeJD7pAplM+sN+OGsCZfBLTfoAE3FPD3
MiuWHWF0S424umJKnO6Kvwd3d420Qp/uddRd3dRLI3Z1p4rhmy9lphLoIIhix06dui+2EXqrS6ci
hyDljbrzUl4+jVap1lvFZfyuurDSfiZVsVR+fvv7XebzkBYrW3CuX8ryG50S6nOSpfgiCvUHzDlA
2dlO5AfV5X002TboNPpUQSui8l99krNUrpgB5dcWoGqmbu1RzoWAI/EK6lD1uQBd8awglmB4rWv9
9hDWNSjbs3ZLoHHb0Zx3hMq8y2Z7NlsCEcWd8rAWsydsp5orXgrDNTuEF0o0z2X1ud10bR0MYZS0
Ie2ncAopNErcAEwVisADTPfoegEknyuxrZxKtAQ0NMBe/Z5RRFKsr1JmALpX7ZPOsrWqpqvX0D/o
ZG0yNUe2bVIuxOGd+bG86LTG2dnBsKa6eq63uKAyXXItPtj4WR5Esbxa9rX1A1r82+cqawA+iDH8
q5trYPjntfog8FlFT3UArFJlCGhkZVUddXLk4kKYjvswPVTP3Qi9vsPE7mo/VJsauWGArcaP5Wqs
sUERbY3BivX8mc7hTjywtR1m6O5fwuinRsC7SwjABnd6F5aXtViuriCibu600OHzls060IKCufql
g63Zv3Mp/t4j05foQb6spxj7zLkfX/uIVHPsB3RL7aqOIF5qnS8+en6tbzajQo/VVxLPa14fJ/Rc
7lx3WeOhYTQz6Jip0hhMCqzc72GoPWoLu8Mb0o5f3dXGSLs4BxdoP6/eqLOVh5VO02exqHRaC0vR
+G+mirJU+fmCq5Ta1xyCRccC897nZW+WyGsxiMawF7e329Zb2621wQDo2I7tLv7jrv9/AfAaXNUU
TOsyF6jViUG46+NBJqZXv+rRK7Evv2i81ZEw33DQ8y6YowH05r+BuxfN92SX3RbVP8bNymDOGnY7
16PfvzG+4ecrzfzkjPZya/H/ScnXyqwX/JtSrrL5pbrryu1hPKFrZzsrJD6sUuyPwDGdKerJyxmq
dvmdHNCrrzU/+2W0pQ6gSvPl/Mertmi+7hBlDhB80kRUqcNeJCGapHNCz1cvCFwsf0A/Ne++jGMf
TuOJcm6+ZnP9TRR7tWjHreOhZ6huiKnPAP2zfmqpIqHHLG/emnNhyHxSs+JJYfIwj6t2AlLdVneO
3Is9u0R33ef+Wv2pVizPfbUW0rGhps1FRRfnZ/2xsnr3oT2Slh2tvngsLXu6M0OgIen7ufrjprrD
vzXQAgNE22ualqzbyAb97uvl6qF/2a5hcU+eBzVWzOdmVjA0PXQMQoAhsulmBv39oU13134SjSlb
dX85nKW3umfYbtu8713Sylhb2i3v2qaoc8C7S2P3pME8uIGedi1IxXbL+adi+P2fT8Xy/m+/PrxZ
/TrXDcpqOMjotwdo9AJmg8r1N7BySygc+Gp+XaYdJhpV8f/7Oy3Y1s330l09YBDTjnyjn5qHGF7x
6O7hZfMXz21OyLZB6lUfOGAGMzo/bjaL7VaV7Ha76D/1yJVEqKmr+L2nCbH7+959wDtv38JZplQG
BDaonX65d/fwEjNqlDjLVIvM9X+XVxF7
""")

##file distribute_setup.py
DISTRIBUTE_SETUP_PY = convert("""
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
""")

##file activate.sh
ACTIVATE_SH = convert("""
eJytVU1v4jAQPW9+xTT0ANVS1GsrDlRFAqmFqmG72m0rY5IJsRRslDiktNr/vuMQ8tFQpNU2B4I9
H36eeW/SglkgYvBFiLBKYg0LhCRGD1KhA7BjlUQuwkLIHne12HCNNpz5kVrBgsfBmdWCrUrA5VIq
DVEiQWjwRISuDreW5eE+CtodeLeAnhZEGKMGFXqAciMiJVcoNWx4JPgixDjzEj48QVeCfcqmtzfs
cfww+zG4ZfeD2ciGF7gCHaDMPM1jtvuHXAsPfF2rSGeOxV4iDY5GUGb3xVEYv2aj6WQ0vRseAlMY
G5DKsAawwnQUXt2LQOYlzZoYByqhonqoqfxZf4BLD97i4DukgXADCPgGgdOLTK5arYxZB1xnrc9T
EQFcHoZEAa1gSQioo/TPV5FZrDlxJA+NzwF+Ek1UonOzFnKZp6k5mgLBqSkuuAGXS4whJb5xz/xs
wXCHjiVerAk5eh9Kfz1wqOldtVv9dkbscfjgjKeTA8XPrtaNauX5rInOxaHuOReNtpFjo1/OxdFG
5eY9hJ3L3jqcPJbATggXAemDLZX0MNZRYjSDH7C1wMHQh73DyYfTu8a0F9v+6D8W6XNnF1GEIXW/
JrSKPOtnW1YFat9mrLJkzLbyIlTvYzV0RGXcaTBfVLx7jF2PJ2wyuBsydpm7VSVa4C4Zb6pFO2TR
huypCEPwuQjNftUrNl6GsYZzuFrrLdC9iJjQ3omAPBbcI2lsU77tUD43kw1NPZhTrnZWzuQKLomx
Rd4OXM1ByExVVkmoTwfBJ7Lt10Iq1Kgo23Bmd8Ib1KrGbsbO4Pp2yO4fpnf3s6MnZiwuiJuls1/L
Pu4yUCvhpA+vZaJvWWDTr0yFYYyVnHMqCEq+QniuYX225xmnzRENjbXACF3wkCYNVZ1mBwxoR9Iw
WAo3/36oSOTfgjwEEQKt15e9Xpqm52+oaXxszmnE9GLl65RH2OMmS6+u5acKxDmlPgj2eT5/gQOX
LLK0j1y0Uwbmn438VZkVpqlfNKa/YET/53j+99G8H8tUhr9ZSXs2
""")

##file activate.fish
ACTIVATE_FISH = convert("""
eJydVm1v4jgQ/s6vmA1wBxUE7X2stJVYlVWR2lK13d6d9laRk0yIr8HmbIe0++tvnIQQB9pbXT5A
Ys/LM55nZtyHx5RrSHiGsMm1gRAh1xhDwU0Kng8hFzMWGb5jBv2E69SDs0TJDdj3MxilxmzPZzP7
pVPMMl+q9bjXh1eZQ8SEkAZULoAbiLnCyGSvvV6SC7IoBcS4Nw0wjcFbvJDcjiuTswzFDpiIQaHJ
lQAjQUi1YRmUboC2uZJig8J4PaCnT5IaDcgsbm/CjinOwgx1KcUTMEhhTgV4g2B1fRk8Le8fv86v
g7v545UHpZB9rKnp+gXsMhxLunIIpwVQxP/l9c/Hq9Xt1epm4R27bva6AJqN92G4YhbMG2i+LB+u
grv71c3dY7B6WtzfLy9bePbp0taDTXSwJQJszUnnp0y57mvpPcrF7ZODyhswtd59+/jdgw+fwBNS
xLSscksUPIDqwwNmCez3PpxGeyBYg6HE0YdcWBxcKczYzuVJi5Wu915vn5oWePCCoPUZBN5B7IgV
MCi54ZDLG7TUZ0HweXkb3M5vFmSpFm/gthhBx0UrveoPpv9AJ9unIbQYdUoe21bKg2q48sPFGVwu
H+afrxd1qvclaNlRFyh1EQ2sSccEuNAGWQwysfVpz1tPajUqbqJUnEcIJkWo6OXDaodK8ZiLdbmM
L1wb+9H0D+pcyPSrX5u5kgWSygRYXCnJUi/KKcuU4cqsAyTKZBiissLc7NFwizvjxtieKBVCIdWz
fzilzPaYyljZN0cGN1v7NnaIPNCGmVy3GKuJaQ6iVjE1Qfm+36hglErwmnAD8hu0dDy4uICBA8ZV
pQr/q/+O0KFW2kjelu9Dgb9SDBsWV4F4x5CswgS0zBVlk5tDMP5bVtUGpslbm81Lu2sdKq7uNMGh
MVQ4fy9xhogC1lS5guhISa0DlBWv0O8odT6/LP+4WZzDV6FzIkEqC0uolGZSZoMnlpxplmD2euaT
O4hkTpPnbztDccey0bhjDaBIqaWQa0uwEtQEwtyU56i4fq54F9IE3ORR6mKriODM4XOYZwaVYLYz
7SPbKkz4i7VkB6/Ot1upDE3znNqYKpM8raa0Bx8vfvntJ32UENsM4aI6gJL+jJwhxhh3jVIDOcpi
m0r2hmEtS8XXXNBk71QCDXTBNhhPiHX2LtHkrVIlhoEshH/EZgdq53Eirqs5iFKMnkOmqZTtr3Xq
djvPTWZT4S3NT5aVLgurMPUWI07BRVYqkQrmtCKohNY8qu9EdACoT6ki0a66XxVF4f9AQ3W38yO5
mWmZmIIpnDFrbXakvKWeZhLwhvrbUH8fahhqD0YUcBDJjEBMQwiznE4y5QbHrbhHBOnUAYzb2tVN
jJa65e+eE2Ya30E2GurxUP8ssA6e/wOnvo3V78d3vTcvMB3n7l3iX1JXWqk=
""")

##file activate.csh
ACTIVATE_CSH = convert("""
eJx9U11vmzAUffevOCVRu+UB9pws29Kl0iq1aVWllaZlcgxciiViItsQdb9+xiQp+dh4QOB7Pu49
XHqY59IgkwVhVRmLmFAZSrGRNkdgykonhFiqSCRW1sJSmJg8wCDT5QrucRCyHn6WFRKhVGmhKwVp
kUpNiS3emup3TY6XIn7DVNQyJUwlrgthJD6n/iCNv72uhCzCpFx9CRkThRQGKe08cWXJ9db/yh/u
pvzl9mn+PLnjj5P5D1yM8QmXlzBkSdXwZ0H/BBc0mEo5FE5qI2jKhclHOOvy9HD/OO/6YO1mX9vx
sY0H/tPIV0dtqel0V7iZvWyNg8XFcBA0ToEqVeqOdNUEQFvN41SumAv32VtJrakQNSmLWmgp4oJM
yDoBHgoydtoEAs47r5wHHnUal5vbJ8oOI+9wI86vb2d8Nrm/4Xy4RZ8R85E4uTZPB5EZPnTaaAGu
E59J8BE2J8XgrkbLeXMlVoQxznEYFYY8uFFdxsKQRx90Giwx9vSueHP1YNaUSFG4vTaErNSYuBOF
lXiVyXa9Sy3JdClEyK1dD6Nos9mEf8iKlOpmqSNTZnYjNEWiUYn2pKNB3ttcLJ3HmYYXy6Un76f7
r8rRsC1TpTJj7f19m5sUf/V3Ir+x/yjtLu8KjLX/CmN/AcVGUUo=
""")

##file activate.bat
ACTIVATE_BAT = convert("""
eJyFUkEKgzAQvAfyhz0YaL9QEWpRqlSjWGspFPZQTevFHOr/adQaU1GaUzI7Mzu7ZF89XhKkEJS8
qxaKMMsvboQ+LxxE44VICSW1gEa2UFaibqoS0iyJ0xw2lIA6nX5AHCu1jpRsv5KRjknkac9VLVug
sX9mtzxIeJDE/mg4OGp47qoLo3NHX2jsMB3AiDht5hryAUOEifoTdCXbSh7V0My2NMq/Xbh5MEjU
ZT63gpgNT9lKOJ/CtHsvT99re3pX303kydn4HeyOeAg5cjf2EW1D6HOPkg9NGKhu
""")

##file deactivate.bat
DEACTIVATE_BAT = convert("""
eJxzSE3OyFfIT0vj4spMU0hJTcvMS01RiPf3cYkP8wwKCXX0iQ8I8vcNCFHQ4FIAguLUEgWIgK0q
FlWqXJpcICVYpGzx2BAZ4uHv5+Hv6wq1BWINXBTdKriEKkI1DhW2QAfhttcxxANiFZCBbglQSJUL
i2dASrm4rFz9XLgAwJNbyQ==
""")

##file distutils-init.py
DISTUTILS_INIT = convert("""
eJytV92L4zYQf/dfMU0ottuse7RvC6FQrg8Lxz2Ugz4si9HacqKuIxlJ2ST313dG8odkO9d7aGBB
luZLv/nNjFacOqUtKJMIvzK3cXlhWgp5MDBsqK5SNYftsBAGpLLA4F1oe2Ytl+9wUvW55TswCi4c
KibhbFDSglXQCFmDPXIwtm7FawLRbwtPzg2T9gf4gupKv4GS0N262w7V0NvpbCy8cvTo3eAus6C5
ETU3ICQZX1hFTw/dzR6V/AW1RCN4/XAtbsVXqIXmlVX6liS4lOzEYY9QFB2zx6LfoSNjz1a0pqT9
QOIfJWQ2E888NEVZNqLlZZnvIB0NpHkimlFdKn2iRRY7yGG/CCJb6Iz280d34SFXBS2yEYPNF0Q7
yM7oCjpWvbEDQmnhRwOs6zjThpKE8HogwRAgraqYFZgGZvzmzVh+mgz9vskT3hruwyjdFcqyENJw
bbMPO5jdzonxK68QKT7B57CMRRG5shRSWDTX3dI8LzRndZbnSWL1zfvriUmK4TcGWSnZiEPCrxXv
bM+sP7VW2is2WgWXCO3sAu3Rzysz3FiNCA8WPyM4gb1JAAmCiyTZbhFjWx3h9SzauuRXC9MFoVbc
yNTCm1QXOOIfIn/g1kGMhDUBN72hI5XCBQtIXQw8UEEdma6Jaz4vJIJ51Orc15hzzmu6TdFp3ogr
Aof0c98tsw1SiaiWotHffk3XYCkqdToxWRfTFXqgpg2khcLluOHMVC0zZhLKIomesfSreUNNgbXi
Ky9VRzwzkBneNoGQyyvGjbsFQqOZvpWIjqH281lJ/jireFgR3cPzSyTGWzQpDNIU+03Fs4XKLkhp
/n0uFnuF6VphB44b3uWRneSbBoMSioqE8oeF0JY+qTvYfEK+bPLYdoR4McfYQ7wMZj39q0kfP8q+
FfsymO0GzNlPh644Jje06ulqHpOEQqdJUfoidI2O4CWx4qOglLye6RrFQirpCRXvhoRqXH3sYdVJ
AItvc+VUsLO2v2hVAWrNIfVGtkG351cUMNncbh/WdowtSPtCdkzYFv6mwYc9o2Jt68ud6wectBr8
hYAulPSlgzH44YbV3ikjrulEaNJxt+/H3wZ7bXSXje/YY4tfVVrVmUstaDwwOBLMg6iduDB0lMVC
UyzYx7Ab4kjCqdViEJmDcdk/SKbgsjYXgfMznUWcrtS4z4fmJ/XOM1LPk/iIpqass5XwNbdnLb1Y
8h3ERXSWZI6rZJxKs1LBqVH65w0Oy4ra0CBYxEeuOMbDmV5GI6E0Ha/wgVTtkX0+OXvqsD02CKLf
XHbeft85D7tTCMYy2Njp4DJP7gWJr6paVWXZ1+/6YXLv/iE0M90FktiI7yFJD9e7SOLhEkkaMTUO
azq9i2woBNR0/0eoF1HFMf0H8ChxH/jgcB34GZIz3Qn4/vid+VEamQrOVqAPTrOfmD4MPdVh09tb
8dLLjvh/61lEP4yW5vJaH4vHcevG8agXvzPGoOhhXNncpTr99PTHx6e/UvffFLaxUSjuSeP286Dw
gtEMcW1xKr/he4/6IQ6FUXP+0gkioHY5iwC9Eyx3HKO7af0zPPe+XyLn7fAY78k4aiR387bCr5XT
5C4rFgwLGfMvJuAMew==
""")

##file distutils.cfg
DISTUTILS_CFG = convert("""
eJxNj00KwkAMhfc9xYNuxe4Ft57AjYiUtDO1wXSmNJnK3N5pdSEEAu8nH6lxHVlRhtDHMPATA4uH
xJ4EFmGbvfJiicSHFRzUSISMY6hq3GLCRLnIvSTnEefN0FIjw5tF0Hkk9Q5dRunBsVoyFi24aaLg
9FDOlL0FPGluf4QjcInLlxd6f6rqkgPu/5nHLg0cXCscXoozRrP51DRT3j9QNl99AP53T2Q=
""")

##file activate_this.py
ACTIVATE_THIS = convert("""
eJyNUlGL2zAMfvevEBlHEujSsXsL9GGDvW1jD3sZpQQ3Ua7aJXawnbT595Ocpe0dO5ghseVP+vRJ
VpIkn2cYPZknwAvWLXWYhRP5Sk4baKgOWRWNqtpdgTyH2Y5wpq5Tug406YAgKEzkwqg7NBPwR86a
Hk0olPopaK0NHJHzYQPnE5rI0o8+yBUwiBfyQcT8mMPJGiAT0A0O+b8BY4MKJ7zPcSSzHaKrSpJE
qeDmUgGvVbPCS41DgO+6xy/OWbfAThMn/OQ9ukDWRCSLiKzk1yrLjWapq6NnvHUoHXQ4bYPdrsVX
4lQMc/q6ZW975nmSK+oH6wL42a9H65U6aha342Mh0UVDzrD87C1bH73s16R5zsStkBZDp0NrXQ+7
HaRnMo8f06UBnljKoOtn/YT+LtdvSyaT/BtIv9KR60nF9f3qmuYKO4//T9ItJMsjPfgUHqKwCZ3n
xu/Lx8M/UvCLTxW7VULHxB1PRRbrYfvWNY5S8it008jOjcleaMqVBDnUXcWULV2YK9JEQ92OfC96
1Tv4ZicZZZ7GpuEpZbbeQ7DxquVx5hdqoyFSSmXwfC90f1Dc7hjFs/tK99I0fpkI8zSLy4tSy+sI
3vMWehjQNJmE5VePlZbL61nzX3S93ZcfDqznnkb9AZ3GWJU=
""")

if __name__ == '__main__':
    main()

## TODO:
## Copy python.exe.manifest
## Monkeypatch distutils.sysconfig

########NEW FILE########
