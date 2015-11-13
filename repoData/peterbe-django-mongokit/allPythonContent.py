__FILENAME__ = document
import sys
import re
from mongokit.document import DocumentProperties
try:
    from mongokit.connection import CallableMixin
except ImportError:
    # mongokit < 0.6
    from mongokit.document import CallableMixin
from mongokit import Document
from django.db.models import signals
model_names = []

from shortcut import connection


class _PK(object):
    attname = '_id'


class _Meta(object):
    def __init__(self, model_name, verbose_name, verbose_name_plural,
                 module_name=None,
                 app_label=None,
                 ):
        self.model_name = model_name
        self.verbose_name = (
            verbose_name and verbose_name or
            re.sub('([a-z])([A-Z])', r'\1 \2', model_name)
        )
        self.verbose_name_plural = (verbose_name_plural or
                                    self.verbose_name + 's')
        self.module_name = module_name
        self.app_label = app_label
        self.pk = _PK()  # needed for haystack
        model_names.append((model_name, self.verbose_name))

    def __repr__(self):
        return "<Meta %s %r, %r>" % (self.model_name,
                                     self.verbose_name,
                                     self.verbose_name_plural)


class DjangoDocumentMetaClass(DocumentProperties):
    def __new__(cls, name, bases, attrs):
        new_class = (super(DjangoDocumentMetaClass, cls)
                     .__new__(cls, name, bases, attrs))

        if CallableMixin in bases:
            # When you register models in the views for example it will
            # register all the models again but then they'll be subclasses of
            # mongokit's CallableMixin.
            # When this is the case we don't want to bother registering any
            # meta stuff about them so exit here
            return new_class

        meta = attrs.pop('Meta', None)

        if meta and getattr(meta, 'abstract', False):
            # No need to attach more meta crap
            return new_class

        verbose_name = meta and getattr(meta, 'verbose_name', None) or None
        verbose_name_plural = (meta and
                               getattr(meta, 'verbose_name_plural', None)
                               or None)
        meta = _Meta(name, verbose_name, verbose_name_plural)

        model_module = sys.modules[new_class.__module__]
        try:
            meta.app_label = model_module.__name__.split('.')[-2]
        except IndexError:
            meta.app_label = model_module.__name__

        new_class._meta = meta
        return new_class


class DjangoDocument(Document):
    class Meta:
        abstract = True

    __metaclass__ = DjangoDocumentMetaClass

    ## XX Are these needed?
    def _get_pk_val(self, meta=None):
        if not meta:
            meta = self._meta
        return str(self[meta.pk.attname])

    def _set_pk_val(self, value):
        raise ValueError("You can't set the ObjectId")

    pk = property(_get_pk_val, _set_pk_val)

    def delete(self):
        signals.pre_delete.send(sender=self.__class__, instance=self)
        super(DjangoDocument, self).delete()
        signals.post_delete.send(sender=self.__class__, instance=self)

    def save(self, *args, **kwargs):
        signals.pre_save.send(sender=self.__class__, instance=self)

        _id_before = '_id' in self and self['_id'] or None
        super(DjangoDocument, self).save(*args, **kwargs)
        _id_after = '_id' in self and self['_id'] or None

        signals.post_save.send(sender=self.__class__, instance=self,
                               created=bool(not _id_before and _id_after))

########NEW FILE########
__FILENAME__ = fields

from django.forms.fields import CharField, ValidationError
from django.forms.widgets import TextInput, Textarea

from django.utils import simplejson


class JsonField(CharField):

    widget = Textarea

    def to_python(self, value):
        """
        Validates that the input can be converted to a datetime. Returns a
        Python datetime.datetime object.
        """
        if not value:
            return {}

        try:
            return simplejson.loads(value)
        except ValueError, e:
            raise ValidationError(str(e))


class JsonListField(CharField):

    widget = TextInput

    def to_python(self, value):
        """
        Validates that the input can be converted to a datetime. Returns a
        Python datetime.datetime object.
        """
        if not value:
            return []

        try:
            return simplejson.loads(value)
        except ValueError, e:
            raise ValidationError(str(e))

########NEW FILE########
__FILENAME__ = forms
import datetime
from django import forms
from django.utils import simplejson

from django.utils.datastructures import SortedDict
from django.forms.util import ErrorList
from django.forms.forms import BaseForm, get_declared_fields

from fields import JsonField, JsonListField


def save_instance(form, instance, fields=None, fail_message='saved',
                  commit=True, exclude=None):
    if form.errors:
        raise ValueError("The %s could not be %s because the data didn't"
                " validate." % ('object', fail_message))

    cleaned_data = form.cleaned_data

    for field_name, field_type in instance.structure.items():
        if fields and field_name not in fields:
            continue
        if exclude and field_name in exclude:
            continue

        instance[field_name] = cleaned_data[field_name]

    if commit:
        instance.save(validate=True)

    return instance


def get_field_type_from_document(instance, field_name):

    field_type = instance.structure[field_name]
    if isinstance(field_type, list):
        field_type = list
    if isinstance(field_type, dict):
        field_type = dict

    return field_type


def value_from_document(instance, field_name):

    field_type = get_field_type_from_document(instance, field_name)

    # Refactor this into a class for each data type.
    if field_type in [list, dict]:
        return simplejson.dumps(instance[field_name])

    return instance[field_name]


def document_to_dict(instance, fields=None, exclude=None):
    """
    Returns a dict containing the data in ``instance`` suitable for passing as
    a Form's ``initial`` keyword argument.

    ``fields`` is an optional list of field names. If provided, only the named
    fields will be included in the returned dict.

    ``exclude`` is an optional list of field names. If provided, the named
    fields will be excluded from the returned dict, even if they are listed in
    the ``fields`` argument.
    """
    # avoid a circular import
    structure = instance.structure

    data = {}
    for field_name in structure.keys():
        if fields and not field_name in fields:
            continue
        if exclude and field_name in exclude:
            continue
        data[field_name] = value_from_document(instance, field_name)

    return data


def get_default_form_field_types(document, field_name, field_type):
    default_form_field_types = {
            bool: forms.BooleanField,
            int: forms.IntegerField,
            float: forms.FloatField,
            str: forms.CharField,
            unicode: forms.CharField,
            datetime.datetime: forms.DateTimeField,
            datetime.date: forms.DateField,
            datetime.time: forms.TimeField,
            list: JsonListField,
            dict: JsonField,
    }
    return default_form_field_types[field_type]


def formfield_for_document_field(document, field_name,
                                 form_class=forms.CharField,
                                 **kwargs):

    field_type = get_field_type_from_document(document, field_name)
    FormField = get_default_form_field_types(document, field_name, field_type)

    defaults = {
        'required': field_name in document.required_fields,
    }
    if field_type == list:
        defaults['initial'] = '[]'
    if field_type == dict:
        defaults['initial'] = '{}'

    if field_name in document.default_values:
        default_value = document.default_values[field_name]
        if callable(default_value):
            default_value = default_value()
        defaults['initial'] = default_value

    defaults.update(kwargs)
    formfield = FormField(**defaults)
    return formfield


def fields_for_document(document, fields=None, exclude=None,
        formfield_callback=None):
    """
    Returns a ``SortedDict`` containing form fields for the given model.

    ``fields`` is an optional list of field names. If provided, only the named
    fields will be included in the returned fields.

    ``exclude`` is an optional list of field names. If provided, the named
    fields will be excluded from the returned fields, even if they are listed
    in the ``fields`` argument.
    """
    field_list = []
    structure = document.structure
    for field_name, field_type in structure.items():
        if fields and not field_name in fields:
            continue
        if exclude and field_name in exclude:
            continue

        form_field = None
        if formfield_callback:
            form_field = formfield_callback(document, field_name)
        if not form_field:
            form_field = formfield_for_document_field(document, field_name)
        if form_field:
            field_list.append((field_name, form_field))

    field_dict = SortedDict(field_list)
    if fields:
        field_dict = SortedDict([(f, field_dict.get(f))
                for f in fields
                if (not exclude) or (exclude and f not in exclude)])
    return field_dict


class DocumentFormOptions(object):
    def __init__(self, options=None):

        try:
            self.document = getattr(options, 'document')
        except AttributeError:
            raise AttributeError("DocumentForm must specify a document class.")

        try:
            self.document.collection
        except AttributeError:
            pass
        else:
            raise TypeError("Document must not be bound to a collection.")

        self.fields = getattr(options, 'fields', None)
        self.exclude = getattr(options, 'exclude', None)


class DocumentFormMetaclass(type):
    def __new__(cls, name, bases, attrs):
        formfield_callback = attrs.pop('formfield_callback', None)
        try:
            parents = [b for b in bases if issubclass(b, DocumentForm)]
        except NameError:
            # We are defining ModelForm itself.
            parents = None
        declared_fields = get_declared_fields(bases, attrs, False)
        new_class = super(DocumentFormMetaclass, cls).__new__(cls, name, bases,
                attrs)
        if not parents:
            return new_class

        opts = new_class._meta = DocumentFormOptions(
            getattr(new_class, 'Meta', None)
        )
        if opts.document:
            # If a model is defined, extract form fields from it.
            fields = fields_for_document(opts.document, opts.fields,
                                      opts.exclude, formfield_callback)
            # Override default model fields with any custom declared ones
            # (plus, include all the other declared fields).
            fields.update(declared_fields)
        else:
            fields = declared_fields
        new_class.declared_fields = declared_fields
        new_class.base_fields = fields
        return new_class


class BaseDocumentForm(BaseForm):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None,
                 collection=None):

        opts = self._meta
        if instance is None:
            # if we didn't get an instance, instantiate a new one
            if collection is None:
                raise TypeError("Collection must be supplied for an unbound "
                        "DocumentForm")
            self.instance = opts.document(collection=collection)
            object_data = {}
        else:
            self.instance = instance
            try:
                self.instance.collection
            except AttributeError:
                raise AssertionError("Instance must be bound to a collection.")

            object_data = document_to_dict(instance, opts.fields, opts.exclude)
        # if initial was provided, it should override the values from instance
        if initial is not None:
            object_data.update(initial)
        super(BaseDocumentForm, self).__init__(
            data, files, auto_id, prefix, object_data,
            error_class, label_suffix, empty_permitted
        )

    def save(self, commit=True):
        if self.instance.get('_id', None) is None:
            fail_message = 'created'
        else:
            fail_message = 'changed'
        return save_instance(self, self.instance, self._meta.fields,
                             fail_message, commit, exclude=self._meta.exclude)

    save.alters_data = True


class DocumentForm(BaseDocumentForm):
    __metaclass__ = DocumentFormMetaclass


def documentform_factory(document, form=DocumentForm,
        fields=None, exclude=None,
        formfield_callback=None):
    # Create the inner Meta class. FIXME: ideally, we should be able to
    # construct a ModelForm without creating and passing in a temporary
    # inner class.

    # Build up a list of attributes that the Meta object will have.

    try:
        document.collection
    except AttributeError:
        pass
    else:
        raise TypeError("Document must not be bound.")

    attrs = {'document': document}
    if fields is not None:
        attrs['fields'] = fields
    if exclude is not None:
        attrs['exclude'] = exclude

    # If parent form class already has an inner Meta, the Meta we're
    # creating needs to inherit from the parent's inner meta.
    parent = (object,)
    if hasattr(form, 'Meta'):
        parent = (form.Meta, object)
    Meta = type('Meta', parent, attrs)

    # Give this new form class a reasonable name.
    class_name = '%sForm' % document.__name__

    # Class attributes for the new form class.
    form_class_attrs = {
        'Meta': Meta,
        'formfield_callback': formfield_callback
    }

    return DocumentFormMetaclass(class_name, (form,), form_class_attrs)

########NEW FILE########
__FILENAME__ = base
"""
MongoKit (MongoDB) backend for Django.
"""

from mongokit import Connection

from django.db.backends import (
    BaseDatabaseOperations,
    BaseDatabaseClient,
    BaseDatabaseIntrospection,
    BaseDatabaseWrapper,
    BaseDatabaseFeatures,
    BaseDatabaseValidation
)
from django.db.backends.creation import BaseDatabaseCreation
from django.conf import settings

TEST_DATABASE_PREFIX = 'test_'


class UnsupportedConnectionOperation(Exception):
    pass


def complain(*args, **kwargs):
    raise UnsupportedConnectionOperation("ARGS=%s" % unicode(args))


def ignore(*args, **kwargs):
    pass


class DatabaseError(Exception):
    pass


class IntegrityError(DatabaseError):
    pass


class DatabaseOperations(BaseDatabaseOperations):

    def quote_name(self, name):
        return '<%s>' % name

    def sql_flush(self, *args, **kwargs):
        # deliberately do nothing as this doesn't apply to us
        return [True]  # pretend that we did something


class DatabaseClient(BaseDatabaseClient):
    runshell = complain


class DatabaseIntrospection(BaseDatabaseIntrospection):
    def get_table_list(self, cursor):
        return []
    get_table_description = complain
    get_relations = complain
    get_indexes = complain


class DatabaseCreation(BaseDatabaseCreation):
    def create_test_db(self, verbosity=1, autoclobber=False):
        # No need to create databases in mongoDB :)
        # but we can make sure that if the database existed is emptied

        if self.connection.settings_dict.get('TEST_NAME'):
            test_database_name = self.connection.settings_dict['TEST_NAME']
        elif 'NAME' in self.connection.settings_dict:
            test_database_name = (TEST_DATABASE_PREFIX +
                                  self.connection.settings_dict['NAME'])
        elif 'DATABASE_NAME' in self.connection.settings_dict:
            if (self.connection.settings_dict['DATABASE_NAME']
                .startswith(TEST_DATABASE_PREFIX)):
                # already been set up
                # must be because this is called from a setUp() instead of
                # something formal.
                # suspect this Django 1.1
                test_database_name = (self.connection
                                      .settings_dict['DATABASE_NAME'])
            else:
                test_database_name = TEST_DATABASE_PREFIX + \
                  self.connection.settings_dict['DATABASE_NAME']
        else:
            raise ValueError("Name for test database not defined")

        # This is important. Here we change the settings so that all other code
        # things that the chosen database is now the test database. This means
        # that nothing needs to change in the test code for working with
        # connections, databases and collections. It will appear the same as
        # when working with non-test code.
        try:
            settings.DATABASES['mongodb']['NAME'] = test_database_name
        except AttributeError:
            settings.MONGO_DATABASE_NAME = test_database_name

        settings.DATABASE_SUPPORTS_TRANSACTIONS = False  # MongoDB :)

        # In this phase it will only drop the database if it already existed
        # which could potentially happen if the test database was created but
        # was never dropped at the end of the tests
        self._drop_database(test_database_name)
        # if it didn't exist it will automatically be created by the
        # mongokit conncetion

    def destroy_test_db(self, old_database_name, verbosity=1):
        """
        Destroy a test database, prompting the user for confirmation if the
        database already exists. Returns the name of the test database created.
        """
        if verbosity >= 1:
            print "Destroying test database '%s'..." % self.connection.alias
        if 'DATABASE_NAME' in self.connection.settings_dict:
            # Django <1.2
            test_database_name = settings.MONGO_DATABASE_NAME
        else:
            test_database_name = self.connection.settings_dict['NAME']
        self._drop_database(test_database_name)

        try:
            settings.DATABASES['mongodb']['NAME'] = old_database_name
        except AttributeError:
            # Django <1.2
            settings.MONGO_DATABASE_NAME = old_database_name

    def _drop_database(self, database_name):
        if not database_name.startswith(TEST_DATABASE_PREFIX):
            # paranoia
            raise DatabaseError(
                "Suspicous! Can't delete database (%r) unless it's "
                "prefixed by %s" %
                (database_name, TEST_DATABASE_PREFIX)
            )
        if database_name in self.connection.connection.database_names():
            # needs to be dropped
            self.connection.connection.drop_database(database_name)


class DatabaseFeatures(BaseDatabaseFeatures):
    def __init__(self, connection):
        super(DatabaseFeatures, self).__init__(connection)

    @property
    def supports_transactions(self):
        return False

class DatabaseWrapper(BaseDatabaseWrapper):
    operators = {}
    _commit = ignore
    _rollback = ignore

    autocommit = None  # ignore

    def __init__(self, settings_dict, alias=None, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(
            settings_dict,
            alias=alias,
            *args,
            **kwargs
        )

        if settings_dict['HOST']:
            kwargs['host'] = settings_dict['HOST']
        if settings_dict['PORT']:
            kwargs['port'] = int(settings_dict['PORT'])
        if 'OPTIONS' in settings_dict:
            kwargs.update(settings_dict['OPTIONS'])
        self.connection = ConnectionWrapper(**kwargs)

        try:
            self.features = DatabaseFeatures(self.connection)
        except TypeError:
            # Django < 1.3
            self.features = BaseDatabaseFeatures()

        try:
            self.ops = DatabaseOperations(self.connection)
        except TypeError:
            # Django < 1.4
            self.ops = DatabaseOperations()

        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        try:
            self.validation = BaseDatabaseValidation(self)
        except TypeError:
            # Django < 1.2
            self.validation = BaseDatabaseValidation()

        settings_dict['SUPPORTS_TRANSACTIONS'] = False
        self.settings_dict = settings_dict
        self.alias = alias and alias or settings_dict['DATABASE_NAME']

        # transaction related attributes
        self.transaction_state = None

    def close(self):
        pass


class ConnectionWrapper(Connection):
    # Need to pretend we care about autocommit
    # BaseDatabaseCreation (in django/db/backends/creation.py) needs to
    # set autocommit
    autocommit = True  # Needed attribute but its value is ignored

    def __init__(self, *args, **kwargs):
        super(ConnectionWrapper, self).__init__(*args, **kwargs)

    def __repr__(self):
        return ('ConnectionWrapper: ' +
                super(ConnectionWrapper, self).__repr__())

########NEW FILE########
__FILENAME__ = shortcut
from django.conf import settings
try:
    from django.db import connections
    from django.db.utils import ConnectionDoesNotExist

    __django_12__ = True
except ImportError:
    __django_12__ = False


if __django_12__:
    try:
        connection = connections['mongodb'].connection
    except ConnectionDoesNotExist:
        # Need to raise a better error
        print connections.databases
        raise
else:
    # because this is Django <1.2 doesn't load all the engines so we have to
    # do it manually.
    # Since with Django <1.2 we have to first define a normal backend engine
    # like sqlite so then the base backend for mongodb is never called
    from django.db import load_backend
    backend = load_backend('django_mongokit.mongodb')
    connection = backend.DatabaseWrapper({
        'DATABASE_HOST': getattr(settings, 'MONGO_DATABASE_HOST', None),
        'DATABASE_NAME': settings.MONGO_DATABASE_NAME,
        'DATABASE_OPTIONS': getattr(settings, 'MONGO_DATABASE_OPTIONS', None),
        'DATABASE_PASSWORD': getattr(settings, 'MONGO_DATABASE_PASSWORD',
                                     None),
        'DATABASE_PORT': getattr(settings, 'MONGO_DATABASE_PORT', None),
        'DATABASE_USER': getattr(settings, 'MONGO_DATABASE_USER', None),
        'TIME_ZONE': settings.TIME_ZONE,
    })
    connection = connection.connection


# The reason this is a function rather than an instance is that you're supposed
# to get the database object every time by calling this function. If you define
# it as a instance (as we do with the connection) the database name cannot be
# different once everything has been imported and loaded.
# When you run tests Django will set everything up so that a test database is
# prepared and that changes settings.DATABASES automatically.
# The net effect is that the way the tests are run nothing needs to be done
# differently as long as you use get_database()
def get_database(this_connection=connection):
    if __django_12__:
        return this_connection[settings.DATABASES['mongodb']['NAME']]
    else:
        return this_connection[settings.MONGO_DATABASE_NAME]


def get_version():
    import os
    f = os.path.join(os.path.dirname(__file__), 'version.txt')
    return open(f).read()

########NEW FILE########
__FILENAME__ = tests
import os
import unittest
from document import DjangoDocument


class Talk(DjangoDocument):
    structure = {'topic': unicode}


class CrazyOne(DjangoDocument):
    class Meta:
        verbose_name = u"Crazy One"
    structure = {'name': unicode}


class CrazyTwo(DjangoDocument):
    class Meta:
        verbose_name = u"Crazy Two"
        verbose_name_plural = u"Crazies Two"
    structure = {'names': unicode}


class LighteningTalk(Talk):
    structure = {'has_slides': bool}
    default_values = {'has_slides': True}


class DocumentTest(unittest.TestCase):

    def setUp(self):
        from shortcut import connection
        connection.register([Talk, CrazyOne, CrazyTwo, LighteningTalk])

        self.connection = connection
        self.database = connection['django_mongokit_test_database']

    def tearDown(self):
        self.connection.drop_database('django_mongokit_test_database')

    def test_meta_creation(self):
        """the class Talk define above should have been given an attribute
        '_meta' by the metaclass that registers it"""
        klass = Talk
        self.assertTrue(klass._meta)
        self.assertFalse(hasattr(klass._meta, 'abstract'))
        self.assertEqual(klass._meta.verbose_name, u"Talk")
        self.assertEqual(klass._meta.verbose_name_plural, u"Talks")
        self.assertEqual(klass._meta.app_label, u"__main__")  # test runner
        self.assertEqual(klass._meta.model_name, u"Talk")

        self.assertEqual(klass._meta.pk.attname, '_id')

        repr_ = repr(klass._meta)
        # <Meta Talk: 'Talk', 'Talks'>
        self.assertEqual(repr_.count('Talk'), 3)
        self.assertEqual(repr_.count('Talks'), 1)

    def test_meta_creation_overwriting_verbose_name(self):
        klass = CrazyOne
        self.assertTrue(klass._meta)
        self.assertEqual(klass._meta.verbose_name, u"Crazy One")
        self.assertEqual(klass._meta.verbose_name_plural, u"Crazy Ones")
        self.assertEqual(klass._meta.model_name, u"CrazyOne")

    def test_meta_creation_overwriting_verbose_name_and_plural(self):
        klass = CrazyTwo
        self.assertTrue(klass._meta)
        self.assertEqual(klass._meta.verbose_name, u"Crazy Two")
        self.assertEqual(klass._meta.verbose_name_plural, u"Crazies Two")
        self.assertEqual(klass._meta.model_name, u"CrazyTwo")

    def test_subclassed_document(self):
        klass = LighteningTalk
        self.assertTrue(klass._meta)
        self.assertEqual(klass._meta.verbose_name, u"Lightening Talk")
        self.assertEqual(klass._meta.verbose_name_plural, u"Lightening Talks")
        self.assertEqual(klass._meta.model_name, u"LighteningTalk")

    def test_pk_shortcut(self):
        # create an instance an expect to get the ID as a string
        collection = self.database.talks
        talk = collection.Talk()
        self.assertRaises(KeyError, lambda t: t.pk, talk)
        talk['topic'] = u"Something"
        talk.save()
        self.assertTrue(talk['_id'])
        self.assertTrue(talk.pk)
        self.assertTrue(isinstance(talk.pk, str))
        self.assertEqual(talk.pk, str(talk['_id']))

        def setter(inst, forced_id):
            inst.pk = forced_id  # will fail
        self.assertRaises(ValueError, setter, talk, 'bla')

    def test_signals(self):
        _fired = []

        def trigger_pre_delete(sender, instance, **__):
            if sender is LighteningTalk:
                if isinstance(instance, LighteningTalk):
                    _fired.append('pre_delete')

        def trigger_post_delete(sender, instance, **__):
            if sender is LighteningTalk:
                if isinstance(instance, LighteningTalk):
                    _fired.append('post_delete')

        def trigger_pre_save(sender, instance, raw=None, **__):
            if sender is LighteningTalk:
                if isinstance(instance, LighteningTalk):
                    if not getattr(instance, '_id', None):
                        _fired.append('pre_save')

        def trigger_post_save(sender, instance, raw=None, created=False, **__):
            assert created in (True, False), "created is supposed to be a bool"
            if sender is LighteningTalk:
                if isinstance(instance, LighteningTalk):
                    if created:
                        _fired.append('post_save created')
                    else:
                        _fired.append('post_save not created')
                    if '_id' in instance:
                        _fired.append('post_save')

        from django.db.models import signals
        signals.pre_delete.connect(trigger_pre_delete, sender=LighteningTalk)
        signals.post_delete.connect(trigger_post_delete, sender=LighteningTalk)

        signals.pre_save.connect(trigger_pre_save, sender=LighteningTalk)
        signals.post_save.connect(trigger_post_save, sender=LighteningTalk)

        collection = self.database.talks
        talk = collection.LighteningTalk()

        talk['topic'] = u"Bla"
        talk.save()

        self.assertTrue('pre_save' in _fired)
        self.assertTrue('post_save' in _fired)
        self.assertTrue('post_save created' in _fired)
        self.assertTrue('post_save not created' not in _fired)

        talk.delete()
        self.assertTrue('pre_delete' in _fired)
        self.assertTrue('post_delete' in _fired)

        talk['topic'] = u"Different"
        talk.save()
        self.assertTrue('post_save not created' in _fired)


class ShortcutTestCase(unittest.TestCase):

    def test_get_database(self):
        from shortcut import get_database, connection
        db = get_database()
        self.assertEqual(db.connection, connection)

        db = get_database(connection)
        self.assertEqual(db.connection, connection)

    def test_get_version(self):
        from shortcut import get_version
        version = get_version()
        self.assertEqual(
            version,
            open(os.path.join(os.path.dirname(__file__),
                'version.txt')).read()
        )


class MongoDBBaseTestCase(unittest.TestCase):

    def test_load_backend(self):
        try:
            from django.db import connections
        except ImportError:
            # Django <1.2
            return  # :(
        self.assertTrue('mongodb' in connections)
        from django.db.utils import load_backend
        backend = load_backend('django_mongokit.mongodb')
        self.assertTrue(backend is not None)

    def test_database_wrapper(self):
        try:
            from django.db import connections
        except ImportError:
            # Django <1.2
            return  # :(
        connection = connections['mongodb']
        self.assertTrue(hasattr(connection, 'connection'))  # stupid name!
        # needed attribute
        self.assertTrue(hasattr(connection.connection, 'autocommit'))

    def test_create_test_database(self):
        from django.conf import settings
        try:
            assert 'mongodb' in settings.DATABASES
        except AttributeError:
            # Django <1.2
            return  # :(
        old_database_name = settings.DATABASES['mongodb']['NAME']
        assert 'test_' not in old_database_name
        # pretend we're the Django 'test' command

        from django.db import connections
        connection = connections['mongodb']

        connection.creation.create_test_db()
        test_database_name = settings.DATABASES['mongodb']['NAME']
        self.assertTrue('test_' in test_database_name)

        from mongokit import Connection
        con = Connection()
        # the test database isn't created till it's needed
        self.assertTrue(test_database_name not in con.database_names())

        # creates it
        db = con[settings.DATABASES['mongodb']['NAME']]
        coll = db.test_collection_name
        # do a query on the collection to force the database to be created
        list(coll.find())
        test_database_name = settings.DATABASES['mongodb']['NAME']
        self.assertTrue(test_database_name in con.database_names())

        connection.creation.destroy_test_db(old_database_name)
        self.assertTrue('test_' not in settings.DATABASES['mongodb']['NAME'])
        self.assertTrue(test_database_name not in con.database_names())

        # this should work even though it doesn't need to do anything
        connection.close()

    def test_create_test_database_by_specific_bad_name(self):
        from django.conf import settings
        try:
            assert 'mongodb' in settings.DATABASES
        except AttributeError:
            # Django <1.2
            return
        settings.DATABASES['mongodb']['TEST_NAME'] = "muststartwith__test_"
        from django.db import connections
        connection = connections['mongodb']

        # why doesn't this work?!?!
        #from mongodb.base import DatabaseError
        #self.assertRaises(DatabaseError, connection.creation.create_test_db)
        self.assertRaises(Exception, connection.creation.create_test_db)

    def test_create_test_database_by_specific_good_name(self):
        from django.conf import settings
        try:
            assert 'mongodb' in settings.DATABASES
        except AttributeError:
            # Django <1.2
            return
        settings.DATABASES['mongodb']['TEST_NAME'] = "test_mustard"
        old_database_name = settings.DATABASES['mongodb']['NAME']
        from django.db import connections
        connection = connections['mongodb']

        connection.creation.create_test_db()
        test_database_name = settings.DATABASES['mongodb']['NAME']
        self.assertTrue('test_' in test_database_name)

        from mongokit import Connection
        con = Connection()
        # the test database isn't created till it's needed
        self.assertTrue(test_database_name not in con.database_names())

        # creates it
        db = con[settings.DATABASES['mongodb']['NAME']]
        coll = db.test_collection_name
        # do a query on the collection to force the database to be created
        list(coll.find())
        test_database_name = settings.DATABASES['mongodb']['NAME']
        self.assertTrue(test_database_name in con.database_names())

        connection.creation.destroy_test_db(old_database_name)
        self.assertTrue('test_mustard' not in
                        settings.DATABASES['mongodb']['NAME'])
        self.assertTrue(test_database_name not in con.database_names())

#
# DocumentForm tests follow
#
import datetime
from django_mongokit.forms import DocumentForm
from django_mongokit.forms import fields as mongokit_fields
from django import forms


class DetailedTalk(DjangoDocument):
    """
    A detailed talk document for testing automated form creation.
    """
    structure = {
        'created_on': datetime.datetime,
        'topic': unicode,
        'when': datetime.datetime,
        'tags': list,
        'duration': float,
    }

    default_values = {
        'created_on': datetime.datetime.utcnow
    }

    required_fields = ['topic', 'when', 'duration']


class BasicTalkForm(DocumentForm):
    """
    A basic form, without customized behavior.
    """
    class Meta:
        document = DetailedTalk


class BasicDocumentFormTest(unittest.TestCase):
    "Test the basic form construction without customization"

    def setUp(self):
        from shortcut import connection
        self.connection = connection
        self.database = self.connection['django_mongokit_test_database']

        self.now = datetime.datetime.utcnow()
        self.form = BasicTalkForm(collection=self.database.test_collection)

    def tearDown(self):
        self.connection.drop_database('django_mongokit_test_database')

    def test_all_fields_created(self):
        "Test all fields created for basic form, in no particular order."
        self.assertEquals(set(self.form.fields.keys()),
                set(['created_on', 'topic', 'when', 'tags', 'duration']))
        self.assertEquals(self.form.fields['created_on'].__class__,
                forms.fields.DateTimeField)
        self.assertEquals(self.form.fields['topic'].__class__,
                forms.fields.CharField)
        self.assertEquals(self.form.fields['when'].__class__,
                forms.fields.DateTimeField)
        self.assertEquals(self.form.fields['tags'].__class__,
                mongokit_fields.JsonListField)
        self.assertEquals(self.form.fields['duration'].__class__,
                forms.fields.FloatField)

    def test_required_set_correctly(self):
        "Test required set correctly for basic form."
        for field_name, field in self.form.fields.items():
            if field_name in DetailedTalk.required_fields:
                self.assertTrue(
                    field.required,
                    "%s should be required" % field_name
                )
            else:
                self.assertEquals(
                    field.required,
                    False,
                    "%s should not be required" % field_name
                )

    def test_initial_values_set_correctly(self):
        "Test the default value for created_on was set for basic form."
        self.assertEquals(self.form.fields['created_on'].initial.ctime(),
                self.now.ctime())

    def test_submit_with_good_values(self):
        "Test saving a basic form with good values."
        posted_form = BasicTalkForm({
            'topic': 'science!',
            'when': '3/10/2010',
            'tags': '["science", "brains", "sf"]',  # JSON
            'duration': '45',
        }, collection=self.database.test_collection)

        self.assertTrue(posted_form.is_valid())
        obj = posted_form.save()
        self.assertEquals(obj['topic'], 'science!')
        self.assertEquals(obj['when'], datetime.datetime(2010, 3, 10, 0, 0))
        self.assertEquals(obj['tags'], ['science', 'brains', 'sf'])
        self.assertEquals(obj['duration'], 45)

    def test_submit_form_with_invalid_json(self):
        "Test saving a basic form with bad JSON."
        posted_form = BasicTalkForm({
            'topic': 'science!',
            'when': '3/10/2010',
            'tags': '["science", "brains", "sf"',  # INVALID JSON
            'duration': '45',
        }, collection=self.database.test_collection)

        self.assertEquals(posted_form.is_valid(), False)
        self.assertTrue(posted_form.errors['tags'])
        self.assertTrue(posted_form.errors['tags'][0].startswith(
                u'Expecting '))

    def test_submit_empty_form(self):
        "Test submitting an empty basic form shows proper errors."
        posted_form = BasicTalkForm({
            'topic': '',
            'when': '',
            'tags': '',
            'duration': '',
        }, collection=self.database.test_collection)

        self.assertEquals(posted_form.is_valid(), False)
        # In order of form specification.
        self.assertEquals(posted_form.errors.keys(),
                ['topic', 'duration', 'when'])
        self.assertEquals(posted_form.errors.values(), [
                [u'This field is required.'],
                [u'This field is required.'],
                [u'This field is required.']])


class DetailedTalkForm(DocumentForm):
    """
    A form that customizes a field and some custom validation tags.
    """
    tags = forms.CharField(max_length=250, required=True)

    def clean_tags(self):
        value = self.cleaned_data['tags']
        return [tag.strip() for tag in value.split(',')]

    def clean_when(self):
        w = self.cleaned_data['when']
        when = datetime.datetime(w.year, w.month, w.day, 0, 0, 0)
        return when

    class Meta:
        document = DetailedTalk
        fields = ['topic', 'when', 'tags', 'duration']


class CustomizedDocumentFormTest(unittest.TestCase):
    "Test form customization"
    def setUp(self):
        from shortcut import connection
        self.connection = connection
        self.database = self.connection['django_mongokit_test_database']
        self.form = DetailedTalkForm(collection=self.database.test_collection)

    def tearDown(self):
        self.connection.drop_database('django_mongokit_test_database')

    def test_all_fields_created(self):
        "Test that fields are created in order specified in form."
        self.assertEquals(self.form.fields.keys(),
                ['topic', 'when', 'tags', 'duration'])
        self.assertEquals([fld.__class__ for fld in self.form.fields.values()],
                [forms.fields.CharField, forms.fields.DateTimeField,
                forms.fields.CharField, forms.fields.FloatField])

    def test_required_set_correctly(self):
        "Test that required values set correctly, even when overridden."
        self.assertEquals(self.form.fields['topic'].required, True)
        self.assertEquals(self.form.fields['when'].required, True)
        self.assertEquals(self.form.fields['tags'].required, True)
        self.assertEquals(self.form.fields['duration'].required, True)

    def test_submit_form_with_correct_values(self):
        "Test custom form submit."
        posted_form = DetailedTalkForm({
            'topic': 'science!',
            'when': '3/10/2010',
            'tags': 'science, brains, sf',  # Comma Separated List
            'duration': '45',
        }, collection=self.database.test_collection)

        self.assertTrue(posted_form.is_valid())
        obj = posted_form.save()
        self.assertEquals(obj['topic'], 'science!')
        self.assertEquals(obj['when'], datetime.datetime(2010, 3, 10, 0, 0))
        self.assertEquals(obj['tags'], ['science', 'brains', 'sf'])
        self.assertEquals(obj['duration'], 45)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_settings
# Django settings for exampleproject project.
import os

HERE = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'example-sqlite3.db',    # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    },
    'mongodb': {
        'ENGINE': 'django_mongokit.mongodb',
        'NAME': 'example',
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    },
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
# Needed to set this to False for the tests to pass [gabesmed]
USE_I18N = False

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '7o!nbm=a=j-%6m3vhd&m*8%&u-rdr)b(t%ksei)d+w$$(xb=2+'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'exampleproject.urls'

TEMPLATE_DIRS = (
    os.path.join(HERE, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'exampleapp',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
)

########NEW FILE########
__FILENAME__ = test_settings_django11
# Django settings for exampleproject project.
import os

HERE = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'example-sqlite3.db'

MONGO_DATABASE_NAME = 'example'


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
SECRET_KEY = '7o!nbm=a=j-%6m3vhd&m*8%&u-rdr)b(t%ksei)d+w$$(xb=2+'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
)

ROOT_URLCONF = 'exampleproject.urls'

TEMPLATE_DIRS = (
    os.path.join(HERE, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'exampleapp',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
)


########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

import views

urlpatterns = patterns('',
    url(r'^$', views.run, name='run'),
)

########NEW FILE########
__FILENAME__ = views
#-*- coding: iso-8859-1 -*

import datetime
import random
from cStringIO import StringIO
from time import time, sleep
try:
    from bson import ObjectId
except ImportError:  # old pymongo
    from pymongo.objectid import ObjectId
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.timezone import utc

from exampleproject.exampleapp.models import Talk
from exampleproject.exampleapp_sql.models import Talk as sql_Talk

from django_mongokit import get_database

def run(request):
    how_many = int(request.GET.get('how_many', 1))

    TESTS = (('mongokit', _create_talks, _edit_talks, _delete_talks,
              settings.DATABASES['mongodb']['ENGINE']),
             ('sql', _create_talks_sql, _edit_talks_sql, _delete_talks_sql,
              settings.DATABASES['default']['ENGINE']),
             )

    response = StringIO()

    for label, creator, editor, deletor, engine in TESTS:
        total = 0.0
        print >>response, label, engine

        t0=time()
        ids = creator(how_many)
        t1=time()
        total += t1-t0
        print >>response, "Creating", how_many, "talks took", t1-t0, "seconds"

        # give it a rest so that the database can internall index all the IDs
        sleep(1)

        t0=time()
        editor(ids)
        t1=time()
        total += t1-t0
        print >>response, "Editing", how_many, "talks took", t1-t0, "seconds"

        # give it a rest so that the database can internall index all the IDs
        sleep(1)

        t0=time()
        deletor(ids)
        t1=time()
        total += t1-t0
        print >>response, "Deleting", how_many, "talks took", t1-t0, "seconds"


        print >>response, "IN TOTAL", total, "seconds"
        print >>response, "\n"

    return HttpResponse(response.getvalue(), mimetype='text/plain')

def __random_topic():
    return random.choice(
        (u'No talks added yet',
         u"I'm working on a branch of django-mongokit that I thought you'd like to know about.",
         u'I want to learn Gaelic.',
         u"I'm well, thank you.",
         u' (Kaw uhn KEU-ra shin KAW-la root uh CHOO-nik mee uhn-royer?)',
         u'Chah beh shin KEU-ra, sheh shin moe CHYEH-luh uh vah EEN-tchuh!',
         u'STUH LUH-oom BRISS-kaht-chun goo MAWR',
         u"Suas Leis a' Ghàidhlig! Up with Gaelic!",
         u"Tha mi ag iarraidh briosgaid!",
        ))

def __random_when():
    return datetime.datetime(random.randint(2000, 2010),
                             random.randint(1, 12),
                             random.randint(1, 28),
                             0, 0, 0).replace(tzinfo=utc)

def __random_tags():
    tags = [u'one', u'two', u'three', u'four', u'five', u'six',
            u'seven', u'eight', u'nine', u'ten']
    random.shuffle(tags)
    return tags[:random.randint(0, 3)]

def __random_duration():
    return round(random.random()*10, 1)


def _create_talks(how_many):
    # 1 Create 1,000 talks
    collection = get_database()[Talk.collection_name]
    ids = set()
    for i in range(how_many):
        talk = collection.Talk()
        talk.topic = __random_topic()
        talk.when = __random_when()
        talk.tags = __random_tags()
        talk.duration = __random_duration()
        talk.save()
        ids.add(talk.pk)
    return ids

def _edit_talks(ids):
    collection = get_database()[Talk.collection_name]
    for id_ in ids:
        talk = collection.Talk.one({'_id': ObjectId(id_)})
        talk.topic += "extra"
        talk.save()

def _delete_talks(ids):
    collection = get_database()[Talk.collection_name]
    for id_ in ids:
        talk = collection.Talk.one({'_id': ObjectId(id_)})
        talk.delete()



def _create_talks_sql(how_many):
    # 1 Create 1,000 talks
    ids = set()
    for i in range(how_many):
        topic = __random_topic()
        when = __random_when()
        tags = __random_tags()
        duration = __random_duration()
        talk = sql_Talk.objects.create(topic=topic, when=when, tags=tags, duration=duration)
        ids.add(talk.pk)
    return ids

def _delete_talks_sql(ids):
    for id_ in ids:
        talk = sql_Talk.objects.get(pk=id_)
        talk.delete()

def _edit_talks_sql(ids):
    for id_ in ids:
        talk = sql_Talk.objects.get(pk=id_)
        talk.topic += "extra"
        talk.save()

########NEW FILE########
__FILENAME__ = forms
import datetime

from django import forms

from django_mongokit.forms import DocumentForm
from models import Talk


class TalkForm(DocumentForm):

    tags = forms.CharField(max_length=250)

    def clean_tags(self):
        value = self.cleaned_data['tags']
        return [tag.strip() for tag in value.split(',')]

    def clean_when(self):
        w = self.cleaned_data['when']
        when = datetime.datetime(w.year, w.month, w.day, 0, 0, 0)
        return when

    class Meta:
        document = Talk
        fields = ['topic', 'when', 'tags', 'duration']

########NEW FILE########
__FILENAME__ = models
import datetime
from django_mongokit import connection
from django_mongokit.document import DjangoDocument


# Create your models here.
class Talk(DjangoDocument):
    collection_name = 'talks'
    structure = {
        'topic': unicode,
        'when': datetime.datetime,
        'tags': list,
        'duration': float,
    }

    required_fields = ['topic', 'when', 'duration']

    use_dot_notation = True

connection.register([Talk])

########NEW FILE########
__FILENAME__ = django11
from django.template import Library, Node
register = Library()


class DumbNode(Node):
    def render(self, context):
        return ''


@register.tag
def csrf_token(parser, token):
    return DumbNode()

########NEW FILE########
__FILENAME__ = tests
from django.core.urlresolvers import reverse
import datetime
from django.test import TestCase
from django.conf import settings

from django_mongokit import get_database
from models import Talk

try:
    from django.db import connections
    __django_12__ = True
except ImportError:
    __django_12__ = False


class ExampleTest(TestCase):

    def setUp(self):
        if not __django_12__:
            # Ugly but necessary
            from django.db import load_backend
            backend = load_backend('django_mongokit.mongodb')

            def get(key):
                return getattr(settings, key, None)
            self.connection = backend.DatabaseWrapper({
                'DATABASE_HOST': get('MONGO_DATABASE_HOST'),
                'DATABASE_NAME': settings.MONGO_DATABASE_NAME,
                'DATABASE_OPTIONS': get('MONGO_DATABASE_OPTIONS'),
                'DATABASE_PASSWORD': get('MONGO_DATABASE_PASSWORD'),
                'DATABASE_PORT': get('MONGO_DATABASE_PORT'),
                'DATABASE_USER': get('MONGO_DATABASE_USER'),
                'TIME_ZONE': settings.TIME_ZONE,
            })
            self.old_database_name = settings.MONGO_DATABASE_NAME
            self.connection.creation.create_test_db()

        db = get_database()
        assert 'test_' in db.name, db.name

    def tearDown(self):
        for name in get_database().collection_names():
            if name not in ('system.indexes',):
                get_database().drop_collection(name)

        # because we have to manually control the creation and destruction of
        # databases in Django <1.2, I'll destroy the database here
        if not __django_12__:
            self.connection.creation.destroy_test_db(self.old_database_name)

    def test_creating_talk_basic(self):
        """test to create a Talk instance"""
        collection = get_database()[Talk.collection_name]
        talk = collection.Talk()
        talk.topic = u"Bla"
        talk.when = datetime.datetime.now()
        talk.tags = [u"foo", u"bar"]
        talk.duration = 5.5
        talk.validate()
        talk.save()

        self.assertTrue(talk['_id'])
        self.assertEqual(talk.duration, 5.5)

    def test_homepage(self):
        """rendering the homepage will show talks and will make it possible to
        add more talks and delete existing ones"""
        response = self.client.get(reverse('homepage'))
        self.assertTrue(response.status_code, 200)
        self.assertTrue('No talks added yet' in response.content)

        data = {'topic': '',
                'when': '2010-12-31',
                'duration': '1.0',
                'tags': ' foo , bar, ,'}
        response = self.client.post(reverse('homepage'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('class="errorlist"' in response.content)
        self.assertTrue('This field is required' in response.content)

        data['topic'] = 'My Topic'
        response = self.client.post(reverse('homepage'), data)
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('homepage'))
        self.assertTrue(response.status_code, 200)
        self.assertTrue('My Topic' in response.content)
        self.assertTrue('31 December 2010' in response.content)
        self.assertTrue('Tags: foo, bar' in response.content)

        collection = get_database()[Talk.collection_name]
        talk = collection.Talk.one()
        assert talk.topic == u"My Topic"
        delete_url = reverse('delete_talk', args=[str(talk._id)])
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('homepage'))
        self.assertTrue(response.status_code, 200)
        self.assertTrue('My Topic' not in response.content)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url
import views


urlpatterns = patterns('',
        url(r'^$', views.homepage, name='homepage'),
        url(r'^delete/(?P<_id>[\w-]+)$', views.delete_talk, name='delete_talk'),
)

########NEW FILE########
__FILENAME__ = views
try:
    from bson import ObjectId
except ImportError:  # old pymongo
    from pymongo.objectid import ObjectId
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext

from django_mongokit import get_database

from models import Talk
from forms import TalkForm


def homepage(request):

    collection = get_database()[Talk.collection_name]
    talks = collection.Talk.find()
    talks.sort('when', -1)
    talks_count = talks.count()

    if request.method == "POST":
        form = TalkForm(request.POST, collection=collection)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('homepage'))
    else:
        form = TalkForm(collection=collection)

    return render_to_response(
        "exampleapp/home.html", {
            'talks': talks,
            'form': form,
            'talks_count': talks_count,
        },
        context_instance=RequestContext(request)
    )


def delete_talk(request, _id):
    collection = get_database()[Talk.collection_name]
    talk = collection.Talk.one({"_id": ObjectId(_id)})
    talk.delete()
    return HttpResponseRedirect(reverse("homepage"))

########NEW FILE########
__FILENAME__ = forms
from django import forms

class TalkForm(forms.Form):
    topic = forms.CharField(max_length=250)
    when = forms.DateField()
    tags = forms.CharField(max_length=250)
    duration = forms.FloatField()
    
    def clean_tags(self):
        tags = self.cleaned_data['tags']
        return [x.strip() for x in tags.split(',') if x.strip()]
########NEW FILE########
__FILENAME__ = models
import datetime
from django.db import models

class ArrayField(models.CharField):
    
    __metaclass__ = models.SubfieldBase
    
    
    description = "basic field for storing string arrays"
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 200
        super(ArrayField, self).__init__(*args, **kwargs)
        
    def to_python(self, value):
        if isinstance(value, list):
            return value
        
        return value.split('|')
    
    def get_prep_value(self, value):
        return '|'.join(value)
    

# Create your models here.
class Talk(models.Model):
    topic = models.CharField(max_length=200)
    when = models.DateTimeField()
    tags = ArrayField(max_length=200)
    duration = models.FloatField()
    
    

########NEW FILE########
__FILENAME__ = tests
import datetime
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.db import connections
from django.conf import settings
from django.utils.timezone import utc

from models import Talk


class ExampleTest(TestCase):

    def setUp(self):
        self.connection = connections['mongodb'].connection
        self.database = self.connection[settings.DATABASES['mongodb']['NAME']]

    def tearDown(self):
        for name in self.database.collection_names():
            if name not in ('system.indexes',):
                self.database.drop_collection(name)


    def test_creating_talk_basic(self):
        """test to create a Talk instance"""
        talk = Talk.objects.create(topic=u"Bla",
                                   when=datetime.datetime.utcnow().replace(tzinfo=utc),
                                   tags=[u"foo", u"bar"],
                                   duration=5.5,
                                   )

        self.assertTrue(talk.id)
        self.assertEqual(talk.duration, 5.5)

    def test_homepage(self):
        """rendering the homepage will show talks and will make it possible to
        add more talks and delete existing ones"""
        response = self.client.get(reverse('sql:homepage'))
        self.assertTrue(response.status_code, 200)
        self.assertTrue('No talks added yet' in response.content)

        data = {'topic': '',
                'when': '2010-12-31',
                'duration':'1.0',
                'tags': ' foo , bar, ,'}
        response = self.client.post(reverse('sql:homepage'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('class="errorlist"' in response.content)
        self.assertTrue('This field is required' in response.content)

        data['topic'] = 'My Topic'
        response = self.client.post(reverse('sql:homepage'), data)
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('sql:homepage'))
        self.assertTrue(response.status_code, 200)
        self.assertTrue('My Topic' in response.content)
        self.assertTrue('31 December 2010' in response.content)
        self.assertTrue('Tags: foo, bar' in response.content)

        talk = Talk.objects.all()[0]
        assert talk.topic == u"My Topic"
        delete_url = reverse('sql:delete_talk', args=[talk.pk])
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('sql:homepage'))
        self.assertTrue(response.status_code, 200)
        self.assertTrue('My Topic' not in response.content)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

import views

urlpatterns = patterns('',
        url(r'^$', views.homepage, name='homepage'),
        url(r'^delete/(?P<_id>[\w-]+)$', views.delete_talk, name='delete_talk'),
)

########NEW FILE########
__FILENAME__ = views
import datetime
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.timezone import utc

from models import Talk
from forms import TalkForm


def homepage(request):
    talks = Talk.objects.all().order_by('-when')
    if request.method == "POST":
        form = TalkForm(request.POST)
        if form.is_valid():
            topic = form.cleaned_data['topic']
            w = form.cleaned_data['when']
            when = (datetime.datetime(w.year, w.month, w.day, 0, 0, 0)
                    .replace(tzinfo=utc))
            tags = form.cleaned_data['tags']
            duration = form.cleaned_data['duration']
            talk = Talk.objects.create(topic=topic, when=when,
                                       tags=tags, duration=duration)
            return HttpResponseRedirect(reverse('homepage'))
    else:
        form = TalkForm()
    return render_to_response("exampleapp/home.html",
                              {'talks': talks, 'form': form},
                              context_instance=RequestContext(request))


def delete_talk(request, _id):
    Talk.objects.filter(pk=_id).delete()
    return HttpResponseRedirect(reverse("homepage"))

########NEW FILE########
__FILENAME__ = settings
# Django settings for exampleproject2 project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG
DEBUG_PROPAGATE_EXCEPTIONS = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'example-sqlite3.db',
    },
    'mongodb': {
        'ENGINE': 'django_mongokit.mongodb',
        'NAME': 'example',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    },
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
USE_TZ = True
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '7st0sdv&amp;7yw*eh)zmaz8#t48nr$&amp;ql#ow=$0l^#b_b&amp;$9c*$4c'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'exampleproject.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'exampleproject.wsgi.application'

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
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'exampleproject.exampleapp',
    'exampleproject.exampleapp_sql',
    'exampleproject.benchmarker',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    (r'^exampleapp/', include('exampleproject.exampleapp.urls')),
    (r'^exampleapp_sql/', include('exampleproject.exampleapp_sql.urls', namespace='sql',
                                  app_name='exampleapp_sql')),
    (r'^benchmarker/', include('exampleproject.benchmarker.urls')),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for exampleproject2 project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exampleproject2.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exampleproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
