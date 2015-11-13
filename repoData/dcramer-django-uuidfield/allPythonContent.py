__FILENAME__ = runtests
#!/usr/bin/env python
import sys
from django.conf import settings
from optparse import OptionParser

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='django.db.backends.postgresql_psycopg2',
        DATABASE_NAME='uuidfield_test',
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'uuidfield_test',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'uuidfield',
            'uuidfield.tests',
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
        test_args = ['uuidfield']

    kwargs.setdefault('interactive', False)

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
__FILENAME__ = runtests_sqlite
#!/usr/bin/env python
import sys
from django.conf import settings
from optparse import OptionParser

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='django.db.backends.sqlite3',
        DATABASE_NAME='uuidfield_test',
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'uuidfield_test',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'uuidfield',
            'uuidfield.tests',
        ],
        ROOT_URLCONF='',
        DEBUG=False,
    )

from django_nose import NoseTestSuiteRunner


from runtests import runtests

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--verbosity', dest='verbosity', action='store', default=1, type=int)
    parser.add_options(NoseTestSuiteRunner.options)
    (options, args) = parser.parse_args()

    runtests(*args, **options.__dict__)

########NEW FILE########
__FILENAME__ = fields
import uuid

from django import forms
from django.db.models import Field, SubfieldBase
try:
    from django.utils.encoding import smart_unicode
except ImportError:
    from django.utils.encoding import smart_text as smart_unicode

try:
    # psycopg2 needs us to register the uuid type
    import psycopg2.extras
    psycopg2.extras.register_uuid()
except (ImportError, AttributeError):
    pass


class StringUUID(uuid.UUID):
    def __init__(self, *args, **kwargs):
        # get around UUID's immutable setter
        object.__setattr__(self, 'hyphenate', kwargs.pop('hyphenate', False))

        super(StringUUID, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return unicode(str(self))

    def __str__(self):
        if self.hyphenate:
            return super(StringUUID, self).__str__()

        return self.hex

    def __len__(self):
        return len(self.__unicode__())


class UUIDField(Field):
    """
    A field which stores a UUID value in hex format. This may also have
    the Boolean attribute 'auto' which will set the value on initial save to a
    new UUID value (calculated using the UUID1 method). Note that while all
    UUIDs are expected to be unique we enforce this with a DB constraint.
    """
    # TODO: support binary storage types
    __metaclass__ = SubfieldBase

    def __init__(self, version=4, node=None, clock_seq=None,
            namespace=None, name=None, auto=False, hyphenate=False, *args, **kwargs):
        assert version in (1, 3, 4, 5), "UUID version %s is not supported." % version
        self.auto = auto
        self.version = version
        self.hyphenate = hyphenate
        # We store UUIDs in hex format, which is fixed at 32 characters.
        kwargs['max_length'] = 32
        if auto:
            # Do not let the user edit UUIDs if they are auto-assigned.
            kwargs['editable'] = False
            kwargs['blank'] = True
            kwargs['unique'] = True
        if version == 1:
            self.node, self.clock_seq = node, clock_seq
        elif version in (3, 5):
            self.namespace, self.name = namespace, name
        super(UUIDField, self).__init__(*args, **kwargs)

    def _create_uuid(self):
        if self.version == 1:
            args = (self.node, self.clock_seq)
        elif self.version in (3, 5):
            error = None
            if self.name is None:
                error_attr = 'name'
            elif self.namespace is None:
                error_attr = 'namespace'
            if error is not None:
                raise ValueError("The %s parameter of %s needs to be set." %
                                 (error_attr, self))
            if not isinstance(self.namespace, uuid.UUID):
                raise ValueError("The name parameter of %s must be an "
                                 "UUID instance." % self)
            args = (self.namespace, self.name)
        else:
            args = ()
        return getattr(uuid, 'uuid%s' % self.version)(*args)

    def db_type(self, connection=None):
        """
        Return the special uuid data type on Postgres databases.
        """
        if connection and 'postgres' in connection.vendor:
            return 'uuid'
        return 'char(%s)' % self.max_length

    def pre_save(self, model_instance, add):
        """
        This is used to ensure that we auto-set values if required.
        See CharField.pre_save
        """
        value = getattr(model_instance, self.attname, None)
        if self.auto and add and not value:
            # Assign a new value for this attribute if required.
            uuid = self._create_uuid()
            setattr(model_instance, self.attname, uuid)
            value = uuid.hex
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        """
        Casts uuid.UUID values into the format expected by the back end
        """
        if isinstance(value, uuid.UUID):
            value = str(value)
        if isinstance(value, str):
            if '-' in value:
                return value.replace('-', '')
        return value

    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        if val is None:
            data = ''
        else:
            data = unicode(val)
        return data

    def to_python(self, value):
        """
        Returns a ``StringUUID`` instance from the value returned by the
        database. This doesn't use uuid.UUID directly for backwards
        compatibility, as ``StringUUID`` implements ``__unicode__`` with
        ``uuid.UUID.hex()``.
        """
        if not value:
            return None
        # attempt to parse a UUID including cases in which value is a UUID
        # instance already to be able to get our StringUUID in.
        return StringUUID(smart_unicode(value), hyphenate=self.hyphenate)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.CharField,
            'max_length': self.max_length,
        }
        defaults.update(kwargs)
        return super(UUIDField, self).formfield(**defaults)

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], [r"^uuidfield\.fields\.UUIDField"])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = models
import uuid
from django.db import models
from uuidfield import UUIDField


class AutoUUIDField(models.Model):
    uuid = UUIDField(auto=True)


class HyphenatedUUIDField(models.Model):
    uuid = UUIDField(auto=True, hyphenate=True)
    name = models.CharField(max_length=16)


class ManualUUIDField(models.Model):
    uuid = UUIDField(auto=False)


class NamespaceUUIDField(models.Model):
    uuid = UUIDField(auto=True, namespace=uuid.NAMESPACE_URL, version=5)


class BrokenNamespaceUUIDField(models.Model):
    uuid = UUIDField(auto=True, namespace='lala', version=5)

########NEW FILE########
__FILENAME__ = tests
import uuid

from django.db import connection, IntegrityError
from django.test import TestCase

from uuidfield.tests.models import (AutoUUIDField, ManualUUIDField,
    NamespaceUUIDField, BrokenNamespaceUUIDField, HyphenatedUUIDField)


class UUIDFieldTestCase(TestCase):

    def test_auto_uuid4(self):
        obj = AutoUUIDField.objects.create()
        self.assertTrue(obj.uuid)
        self.assertEquals(len(obj.uuid), 32)
        self.assertTrue(isinstance(obj.uuid, uuid.UUID))
        self.assertEquals(obj.uuid.version, 4)

    def test_raises_exception(self):
        self.assertRaises(IntegrityError, ManualUUIDField.objects.create)

    def test_manual(self):
        obj = ManualUUIDField.objects.create(uuid=uuid.uuid4())
        self.assertTrue(obj)
        self.assertEquals(len(obj.uuid), 32)
        self.assertTrue(isinstance(obj.uuid, uuid.UUID))
        self.assertEquals(obj.uuid.version, 4)

    def test_namespace(self):
        obj = NamespaceUUIDField.objects.create()
        self.assertTrue(obj)
        self.assertEquals(len(obj.uuid), 32)
        self.assertTrue(isinstance(obj.uuid, uuid.UUID))
        self.assertEquals(obj.uuid.version, 5)

    def test_broken_namespace(self):
        self.assertRaises(ValueError, BrokenNamespaceUUIDField.objects.create)

    def test_hyphenated(self):
        obj = HyphenatedUUIDField.objects.create(name='test')
        uuid = obj.uuid

        self.assertTrue('-' in unicode(uuid))
        self.assertTrue('-' in str(uuid))

        self.assertEquals(len(uuid), 36)

        # ensure the hyphens don't affect re-saving object
        obj.name = 'shoe'
        obj.save()

        obj = HyphenatedUUIDField.objects.get(uuid=obj.uuid)

        self.assertTrue(obj.uuid, uuid)
        self.assertTrue(obj.name, 'shoe')

    def test_can_use_hyphenated_uuids_in_filter_and_get(self):
        obj = AutoUUIDField.objects.create()
        obj_uuid = uuid.UUID(str(obj.uuid))
        self.assertTrue('-' in unicode(obj_uuid))
        self.assertTrue('-' in str(obj_uuid))
        inserted_obj = AutoUUIDField.objects.get(uuid=obj_uuid)
        filtered_obj = AutoUUIDField.objects.filter(uuid=obj_uuid)[0]
        self.assertEqual(inserted_obj.uuid, obj_uuid)
        self.assertEqual(filtered_obj.uuid, obj_uuid)

########NEW FILE########
