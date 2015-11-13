__FILENAME__ = nose_plugin
# -*- coding: utf-8 -*-

from nose.plugins import Plugin


# http://readthedocs.org/docs/nose/en/latest/plugins/interface.html
class DDFSetup(Plugin):
    "python manage.py test --with-ddf-setup"
    name = 'ddf-setup'
    enabled = True

    _error_message = None

    def begin(self):
        "Called before any tests are collected or run. Use this to perform any setup needed before testing begins."
        try:
            import ddf_setup
        except ImportError as e:
            self._error_message = str(e)

    def report(self, stream):
        """Called after all error output has been printed. Print your
        plugin's report to the provided stream. Return None to allow
        other plugins to print reports, any other value to stop them.

        :param stream: stream object; send your output here
        :type stream: file-like object
        """
        if self._error_message:
            stream.write('\nDDF Setup error: %s\n' % self._error_message)

########NEW FILE########
__FILENAME__ = ddf
# -*- coding: utf-8 -*-

import inspect
import logging
import sys
import six

from django.core.files import File
from django.db.models import Field
from django.utils.importlib import import_module

from django_dynamic_fixture.django_helper import get_related_model, \
    field_has_choices, field_has_default_value, get_fields_from_model, \
    print_field_values, get_many_to_many_fields_from_model, \
    get_unique_model_name, get_unique_field_name, is_model_abstract, \
    field_is_a_parent_link, get_field_by_name_or_raise, get_app_name_of_model, \
    is_model_class, is_relationship_field, is_file_field, is_key_field, \
    model_has_the_field, enable_auto_now, disable_auto_now, enable_auto_now_add, disable_auto_now_add


LOGGER = logging.getLogger('DDFLog')
_LOADED_DDF_SETUP_MODULES = [] # control to avoid a ddf_setup module be loaded more than one time.
_PRE_SAVE = {} # receivers to be executed before saving a instance;
_POST_SAVE = {} # receivers to be executed after saving a instance;


class UnsupportedFieldError(Exception):
    "DynamicFixture does not support this field."


class InvalidCopierExpressionError(Exception):
    "The specified expression used in a Copier is invalid."


class InvalidConfigurationError(Exception):
    "The specified configuration for the field can not be applied or it is bugged."


class InvalidManyToManyConfigurationError(Exception):
    "M2M attribute configuration must be a number or a list of DynamicFixture or model instances."


class BadDataError(Exception):
    "The data passed to a field has some problem (not unique or invalid) or a required attribute is in ignore list."


class InvalidModelError(Exception):
    "Invalid Model: The class is not a model or it is abstract."


class InvalidDDFSetupError(Exception):
    "ddf_setup.py has execution errors"


class InvalidReceiverError(Exception):
    "Receiver is not a function that receive only the instance as parameter."


class PendingField(Exception):
    "Internal exception to control pending fields when using Copier."


def set_pre_save_receiver(model_class, callback_function):
    """
    :model_class: a model_class can have only one receiver. Do not complicate yourself.
    :callback_function must be a function that receive the instance as unique parameter.
    """
    if not is_model_class(model_class) or not inspect.isfunction(callback_function) or len(inspect.getargspec(callback_function).args) != 1:
        raise InvalidReceiverError(model_class)
    _PRE_SAVE[model_class] = callback_function


def set_post_save_receiver(model_class, callback_function):
    """
    :model_class: a model_class can have only one receiver. Do not complicate yourself.
    :callback_function must be a function that receive the instance as unique parameter.
    """
    if not is_model_class(model_class) or not inspect.isfunction(callback_function) or len(inspect.getargspec(callback_function).args) != 1:
        raise(InvalidReceiverError(model_class))
    _POST_SAVE[model_class] = callback_function


class DataFixture(object):
    """
    Responsibility: return a valid data for a Django Field, according to its type, model class, constraints etc.

    You must create a separated method to generate data for an specific field. For a field called 'MyField',
    the method must be:

    def myfield_config(self, field, key): return 'some value'

    :field: Field object.
    :key: string that represents a unique name for a Field, considering app, model and field names.
    """

    def _field_fixture_template(self, field_class):
        return '%s_config' % (field_class.__name__.lower(),)

    def _field_fixture_factory(self, field_class):
        try:
            fixture = self._field_fixture_template(field_class)
            getattr(self, fixture)
            return fixture
        except AttributeError:
            if len(field_class.__bases__) > 0:
                # Pick the first parent class that inherits Field (or use the first parent class)
                field_subclasses = (cls for cls in field_class.__bases__ if issubclass(cls, Field))
                parent_class = next(field_subclasses, field_class.__bases__[0])
                return self._field_fixture_factory(parent_class)
            else:
                return None

    def generate_data(self, field):
        "Get a unique and valid data for the field."
        config = self._field_fixture_factory(field.__class__)
        is_supported_field = config != None
        if is_supported_field:
            key = get_unique_field_name(field)
            data = eval('self.%s(field, "%s")' % (config, key,))
        else:
            if field.null:
                data = None # a workaround for versatility
            else:
                raise(UnsupportedFieldError(get_unique_field_name(field)))
        return data


class Copier(object):
    """
    Wrapper of an expression in the format 'field' or 'field.field' or 'field.field.field' etc
    This expression will be interpreted to copy the value of the specified field to the current field.
    Example of usage: G(MyModel, x=C('y.z')) => the value 'z' of field 'y' will be copied to field 'x'.
    """
    def __init__(self, expression):
        self.expression = expression

    def __str__(self):
        return u"C('%s')" % self.expression

    def immediate_field_name(self, instance):
        model_class = instance.__class__
        field_name = self.expression.split('.')[0]
        get_field_by_name_or_raise(model_class, field_name)
        return field_name

    def eval_expression(self, instance):
        try:
            current_instance = instance
            fields = self.expression.split('.')
            for field in fields:
                current_instance = getattr(current_instance, field)
            return current_instance
        except Exception as e:
            six.reraise(InvalidCopierExpressionError, InvalidCopierExpressionError(self.expression, e), sys.exc_info()[2])


class DDFLibrary(object):
    instance = None
    DEFAULT_KEY = 'ddf_default'

    def __init__(self):
        self.configs = {} # {Model: {name: config}}"

    def __str__(self):
        return '\n'.join(['%s = %s' % (key, value) for key, value in self.configs.items()])

    @classmethod
    def get_instance(cls):
        if not cls.instance:
            cls.instance = DDFLibrary()
        return cls.instance

    def add_configuration(self, model_class, kwargs, name=None):
        if name in [None, True]:
            name = self.DEFAULT_KEY
        model_class_config = self.configs.setdefault(model_class, {})
        model_class_config[name] = kwargs

    def get_configuration(self, model_class, name=None):
        if name is None:
            name = self.DEFAULT_KEY
        # copy is important because this dict will be updated every time in the algorithm.
        config = self.configs.get(model_class, {})
        if name != self.DEFAULT_KEY and name not in config.keys():
            raise InvalidConfigurationError('There is no shelved configuration for model %s with the name "%s"' % (get_unique_model_name(model_class), name))
        return config.get(name, {}).copy() # default configuration never raises an error

    def clear(self):
        "Remove all shelved configurations of the library."
        self.configs = {}

    def clear_configuration(self, model_class):
        "Remove from the library an specific configuration of a model."
        if model_class in self.configs.keys():
            del self.configs[model_class]


class DynamicFixture(object):
    """
    Responsibility: create a valid model instance according to the given configuration.
    """

    _DDF_CONFIGS = ['fill_nullable_fields', 'ignore_fields', 'data_fixture', 'number_of_laps', 'use_library',
                    'validate_models', 'validate_args', 'print_errors']

    def __init__(self, data_fixture, fill_nullable_fields=True, ignore_fields=[], number_of_laps=1, use_library=False,
                 validate_models=False, validate_args=False, print_errors=True, model_path=[], debug_mode=False, **kwargs):
        """
        :data_fixture: algorithm to fill field data.
        :fill_nullable_fields: flag to decide if nullable fields must be filled with data.
        :ignore_fields: list of field names that must not be filled with data.
        :number_of_laps: number of laps for each cyclic dependency.
        :use_library: flag to decide if DDF library will be used to load default fixtures.
        :validate_models: flag to decide if the model_instance.full_clean() must be called before saving the object.
        :validate_args: flag to enable field name validation of custom fixtures.
        :print_errors: flag to determine if the model data must be printed to console on errors. For some scripts is interesting to disable it.
        :model_path: internal variable used to control the cycles of dependencies.
        """
        # custom config of fixtures
        self.data_fixture = data_fixture
        self.fill_nullable_fields = fill_nullable_fields
        self.ignore_fields = ignore_fields
        self.number_of_laps = number_of_laps
        self.use_library = use_library
        # other ddfs configs
        self.validate_models = validate_models
        self.validate_args = validate_args
        self.print_errors = print_errors
        # internal logic
        self.model_path = model_path
        self.pending_fields = []
        self.fields_processed = []
        self.debug_mode = debug_mode
        self.kwargs = kwargs
        self.fields_to_disable_auto_now = []
        self.fields_to_disable_auto_now_add = []

    def __str__(self):
        return u'F(%s)' % (u', '.join(u'%s=%s' % (key, value) for key, value in self.kwargs.items()))

    def __eq__(self, that):
        return self.kwargs == that.kwargs

    def _get_data_from_custom_dynamic_fixture(self, field, fixture, persist_dependencies):
        "return data of a Dynamic Fixture: field=F(...)"
        next_model = get_related_model(field)
        if persist_dependencies:
            data = fixture.get(next_model)
        else:
            data = fixture.new(next_model, persist_dependencies=persist_dependencies)
        return data

    def _get_data_from_custom_copier(self, instance, field, fixture):
        "return data of a Copier: field=C(...)"
        field_name = fixture.immediate_field_name(instance)
        if field_name in self.fields_processed:
            data = fixture.eval_expression(instance)
        else:
            self.pending_fields.append(field.name)
            raise PendingField('%s' % field.name)
        return data

    def _get_data_from_data_fixture(self, field, fixture):
        "return data of a Data Fixture: field=DataFixture()"
        next_model = get_related_model(field)
        return fixture.generate_data(next_model)

    def _get_data_from_a_custom_function(self, field, fixture):
        "return data of a custom function: field=lambda field: field.name"
        data = fixture(field)
        return data

    def _get_data_from_static_data(self, field, fixture):
        "return date from a static value: field=3"
        if hasattr(field, 'auto_now_add') and field.auto_now_add:
            self.fields_to_disable_auto_now_add.append(field)
        if hasattr(field, 'auto_now') and field.auto_now:
            self.fields_to_disable_auto_now.append(field)
        return fixture

    def _process_field_with_customized_fixture(self, instance, field, fixture, persist_dependencies):
        "Set a custom value to a field."
        if isinstance(fixture, DynamicFixture): # DynamicFixture (F)
            data = self._get_data_from_custom_dynamic_fixture(field, fixture, persist_dependencies)
        elif isinstance(fixture, Copier): # Copier (C)
            data = self._get_data_from_custom_copier(instance, field, fixture)
        elif isinstance(fixture, DataFixture): # DataFixture
            data = self._get_data_from_data_fixture(field, fixture)
        elif callable(fixture): # callable with the field as parameters
            data = self._get_data_from_a_custom_function(field, fixture)
        else: # attribute value
            data = self._get_data_from_static_data(field, fixture)
        return data

    def _process_foreign_key(self, model_class, field, persist_dependencies):
        "Returns auto-generated value for a field ForeignKey or OneToOneField."
        if field_is_a_parent_link(field):
            return None
        next_model = get_related_model(field)
        occurrences = self.model_path.count(next_model)
        if occurrences >= self.number_of_laps:
            data = None
        else:
            next_model_path = self.model_path[:]
            next_model_path.append(model_class)
            if model_class == next_model: # self reference
                # propagate ignored_fields only for self references
                ignore_fields = self.ignore_fields
            else:
                ignore_fields = []
            # need a new DynamicFixture to control the cycles and ignored fields.
            fixture = DynamicFixture(data_fixture=self.data_fixture,
                                     fill_nullable_fields=self.fill_nullable_fields,
                                     ignore_fields=ignore_fields,
                                     number_of_laps=self.number_of_laps,
                                     use_library=self.use_library,
                                     validate_models=self.validate_models,
                                     validate_args=self.validate_args,
                                     print_errors=self.print_errors,
                                     model_path=next_model_path)
            if persist_dependencies:
                data = fixture.get(next_model)
            else:
                data = fixture.new(next_model, persist_dependencies=persist_dependencies)
        return data

    def _process_field_with_default_fixture(self, field, model_class, persist_dependencies):
        "The field has no custom value, so the default behavior of the tool is applied."
        if field.null and not self.fill_nullable_fields:
            return None
        if field_has_default_value(field):
            if callable(field.default):
                data = field.default() # datetime default can receive a function: datetime.now
            else:
                data = field.default
        elif field_has_choices(field):
            data = field.flatchoices[0][0] # key of the first choice
        elif is_relationship_field(field):
            data = self._process_foreign_key(model_class, field, persist_dependencies)
        else:
            data = self.data_fixture.generate_data(field)
        return data

    def set_data_for_a_field(self, model_class, instance, field, persist_dependencies=True, **kwargs):
        if field.name in kwargs:
            config = kwargs[field.name]
            try:
                data = self._process_field_with_customized_fixture(instance, field, config, persist_dependencies)
            except PendingField:
                return # ignore this field for a while.
            except Exception as e:
                six.reraise(InvalidConfigurationError, InvalidConfigurationError(get_unique_field_name(field), e), sys.exc_info()[2])
        else:
            data = self._process_field_with_default_fixture(field, model_class, persist_dependencies)

        if is_file_field(field) and data:
            django_file = data
            if isinstance(django_file, File):
                setattr(instance, field.name, data.name) # set the attribute
                if django_file.file.mode != 'rb':
                    django_file.file.close() # this file may be open in another mode, for example, in a+b
                    opened_file = open(django_file.file.name, 'rb') # to save the file it must be open in rb mode
                    django_file.file = opened_file # we update the reference to the rb mode opened file
                getattr(instance, field.name).save(django_file.name, django_file) # save the file into the file storage system
                django_file.close()
            else: # string (saving just a name in the file, without saving the file to the storage file system
                setattr(instance, field.name, data) # Model.field = data
        else:
            if self.debug_mode:
                LOGGER.debug('%s.%s = %s' % (get_unique_model_name(model_class), field.name, data))
            setattr(instance, field.name, data) # Model.field = data
        self.fields_processed.append(field.name)

    def _validate_kwargs(self, model_class, kwargs):
        "validate all kwargs match Model.fields."
        for field_name in kwargs.keys():
            if field_name in self._DDF_CONFIGS:
                continue
            if not model_has_the_field(model_class, field_name):
                raise InvalidConfigurationError('Field "%s" does not exist.' % field_name)

    def _configure_params(self, model_class, shelve, named_shelve, **kwargs):
        """
        1) validate kwargs
        2) load default fixture from DDF library. Store default fixture in DDF library.
        3) Load fixtures defined in F attributes.
        """
        if self.validate_args:
            self._validate_kwargs(model_class, kwargs)
        library = DDFLibrary.get_instance()
        if shelve: # shelving before use_library property: do not twist two different configurations (anti-pattern)
            for field_name in kwargs.keys():
                if field_name in self._DDF_CONFIGS:
                    continue
                field = get_field_by_name_or_raise(model_class, field_name)
                fixture = kwargs[field_name]
                if field.unique and not (isinstance(fixture, (DynamicFixture, Copier, DataFixture)) or callable(fixture)):
                    raise InvalidConfigurationError('It is not possible to store static values for fields with unique=True (%s)' % get_unique_field_name(field))
            library.add_configuration(model_class, kwargs, name=shelve)
        if self.use_library:
            # load ddf_setup.py of the model application
            app_name = get_app_name_of_model(model_class)
            if app_name not in _LOADED_DDF_SETUP_MODULES:
                full_module_name = '%s.tests.ddf_setup' % app_name
                try:
                    _LOADED_DDF_SETUP_MODULES.append(app_name)
                    import_module(full_module_name)
                except ImportError:
                    pass # ignoring if module does not exist
                except Exception as e:
                    six.reraise(InvalidDDFSetupError, InvalidDDFSetupError(e), sys.exc_info()[2])
            configuration_default = library.get_configuration(model_class, name=DDFLibrary.DEFAULT_KEY)
            configuration_custom = library.get_configuration(model_class, name=named_shelve)
            configuration = {}
            configuration.update(configuration_default) # always use default configuration
            configuration.update(configuration_custom) # override default configuration
            configuration.update(kwargs) # override shelved configuration with current configuration
        else:
            configuration = kwargs
        configuration.update(self.kwargs) # Used by F: kwargs are passed by constructor, not by get.
        return configuration

    def new(self, model_class, shelve=False, named_shelve=None, persist_dependencies=True, **kwargs):
        """
        Create an instance filled with data without persist it.
        1) validate all kwargs match Model.fields.
        2) validate model is a model.Model class.
        3) Iterate model fields: for each field, fill it with data.

        :shelve: the current configuration will be stored in the DDF library. It can be True or a string (named shelve).
        :named_shelve: restore configuration saved in DDF library with a name.
        :persist_dependencies: tell if internal dependencies will be saved in the database or not.
        """
        if self.debug_mode:
            LOGGER.debug('>>> [%s] Generating instance.' % get_unique_model_name(model_class))
        configuration = self._configure_params(model_class, shelve, named_shelve, **kwargs)
        instance = model_class()
        if not is_model_class(instance):
            raise InvalidModelError(get_unique_model_name(model_class))
        for field in get_fields_from_model(model_class):
            if is_key_field(field) and 'id' not in configuration: continue
            if field.name in self.ignore_fields: continue
            self.set_data_for_a_field(model_class, instance, field, persist_dependencies=persist_dependencies, **configuration)
        number_of_pending_fields = len(self.pending_fields)
        # For Copier fixtures: dealing with pending fields that need to receive values of another fields.
        i = 0
        while self.pending_fields != []:
            field_name = self.pending_fields.pop(0)
            field = get_field_by_name_or_raise(model_class, field_name)
            self.set_data_for_a_field(model_class, instance, field, persist_dependencies=persist_dependencies, **configuration)
            i += 1
            if i > 2 * number_of_pending_fields: # dealing with infinite loop too.
                raise InvalidConfigurationError(get_unique_field_name(field), u'Cyclic dependency of Copiers.')
        if self.debug_mode:
            LOGGER.debug('<<< [%s] Instance created.' % get_unique_model_name(model_class))
        return instance

    def _process_many_to_many_field(self, field, manytomany_field, fixture, instance):
        """
        Set ManyToManyField fields with or without 'trough' option.

        :field: model field.
        :manytomany_field: ManyRelatedManager of the field.
        :fixture: value passed by user.
        """
        next_model = get_related_model(field)
        if isinstance(fixture, int):
            amount = fixture
            for _ in range(amount):
                next_instance = self.get(next_model)
                self._create_manytomany_relationship(manytomany_field, instance, next_instance)
        elif isinstance(fixture, (list, tuple)):
            items = fixture
            for item in items:
                if isinstance(item, DynamicFixture):
                    next_instance = item.get(next_model, **item.kwargs) # need to pass F.kwargs recursively.
                else:
                    next_instance = item

                self._create_manytomany_relationship(manytomany_field, instance, next_instance)
        else:
            raise InvalidManyToManyConfigurationError('Field: %s' % field.name, str(fixture))

    def _create_manytomany_relationship(self, manytomany_field, instance, next_instance):
        try:
            manytomany_field.add(next_instance)
        except AttributeError:
            next_instance.save()

            # Create an instance of the "through" model using the current data fixture
            through_model = manytomany_field.through
            through_instance = DynamicFixture(data_fixture=self.data_fixture) \
                    .get(through_model, **{
                        manytomany_field.source_field_name: instance,
                        manytomany_field.target_field_name: next_instance
                    })

    def _save_the_instance(self, instance):
        for field in self.fields_to_disable_auto_now:
            disable_auto_now(field)
        for field in self.fields_to_disable_auto_now_add:
            disable_auto_now_add(field)
        instance.save()
        for field in self.fields_to_disable_auto_now:
            enable_auto_now(field)
        for field in self.fields_to_disable_auto_now_add:
            enable_auto_now_add(field)

    def get(self, model_class, shelve=False, named_shelve=None, **kwargs):
        """
        Create an instance with data and persist it.

        :shelve: the current configuration will be stored in the DDF library.
        :named_shelve: restore configuration saved in DDF library with a name.
        """
        instance = self.new(model_class, shelve=shelve, named_shelve=named_shelve, **kwargs)
        if is_model_abstract(model_class):
            raise InvalidModelError(get_unique_model_name(model_class))
        try:
            if self.validate_models:
                instance.full_clean()
            if model_class in _PRE_SAVE:
                try:
                    _PRE_SAVE[model_class](instance)
                except Exception as e:
                    six.reraise(InvalidReceiverError, InvalidReceiverError(e), sys.exc_info()[2])
            self._save_the_instance(instance)
            if model_class in _POST_SAVE:
                try:
                    _POST_SAVE[model_class](instance)
                except Exception as e:
                    six.reraise(InvalidReceiverError, InvalidReceiverError(e), sys.exc_info()[2])
        except Exception as e:
            if self.print_errors:
                print_field_values(instance)
            six.reraise(BadDataError, BadDataError(get_unique_model_name(model_class), e), sys.exc_info()[2])
        self.fields_processed = [] # TODO: need more tests for M2M and Copier
        self.pending_fields = []
        for field in get_many_to_many_fields_from_model(model_class):
            if field.name in kwargs.keys(): # TODO: library
                manytomany_field = getattr(instance, field.name)
                fixture = kwargs[field.name]
                try:
                    self._process_many_to_many_field(field, manytomany_field, fixture, instance)
                except InvalidManyToManyConfigurationError as e:
                    six.reraise(InvalidManyToManyConfigurationError, e, sys.exc_info()[2])
                except Exception as e:
                    six.reraise(InvalidManyToManyConfigurationError, InvalidManyToManyConfigurationError(get_unique_field_name(field), e), sys.exc_info()[2])
        return instance

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-

from django.conf import settings


DATABASE_ENGINE = settings.DATABASES['default']['ENGINE']

SQLITE3 = 'sqlite3'
POSTGRES = 'postgresql'
MYSQL = 'mysql'
ORACLE = 'oracle'
SQLSERVER = 'pyodbc'


def skip_for_database(database):
    def main_decorator(testcase_function):
        def wrapper(*args, **kwargs):
            if database not in DATABASE_ENGINE:
                testcase_function(*args, **kwargs)
        return wrapper
    return main_decorator


def only_for_database(database):
    def main_decorator(testcase_function):
        def wrapper(*args, **kwargs):
            if database in DATABASE_ENGINE:
                testcase_function(*args, **kwargs)
        return wrapper
    return main_decorator

########NEW FILE########
__FILENAME__ = django_helper
# -*- coding: utf-8 -*-

"""
Module to wrap dirty stuff of django core.
"""
from django.db import models
from django.db.models import Model, ForeignKey, OneToOneField, FileField
from django.db.models.fields import NOT_PROVIDED, AutoField, FieldDoesNotExist
from django.db.models.base import ModelBase
from django.db.models.query import QuerySet


# Apps
def get_apps(application_labels=[], exclude_application_labels=[]):
    """
    - if not @application_labels and not @exclude_application_labels, it returns all applications.
    - if @application_labels is not None, it returns just these applications,
    except applications with label in exclude_application_labels.
    """
    if application_labels:
        applications = []
        for app_label in application_labels:
            applications.append(models.get_app(app_label))
    else:
        applications = models.get_apps()
    if exclude_application_labels:
        for app_label in exclude_application_labels:
            if app_label:
                applications.remove(models.get_app(app_label))
    return applications


def get_app_name(app):
    """
    app is the object returned by get_apps method
    """
    return app.__name__.split('.')[0]


def get_models_of_an_app(app):
    """
    app is the object returned by get_apps method
    """
    return models.get_models(app)


# Models
def get_app_name_of_model(model_class):
    return model_class.__module__.split('.')[0]


def get_model_name(model_class):
    "Example: ModelName"
    return model_class.__name__


def get_unique_model_name(model_class):
    "Example: app.packages.ModelName"
    return model_class.__module__ + '.' + model_class.__name__


def get_fields_from_model(model_class):
    "Returns all fields, including inherited fields but ignoring M2M fields."
    return model_class._meta.fields


def get_local_fields(model):
    "Returns all local fields!?"
    return model._meta.local_fields


def get_many_to_many_fields_from_model(model_class):
    "Return only M2M fields, including inherited ones?"
    return model_class._meta.many_to_many
    #_meta.local_many_to_many


def get_all_fields_of_model(model_class):
    fields1 = get_fields_from_model(model_class)
    fields2 = get_many_to_many_fields_from_model(model_class)
    fields1.extend(fields2)
    return fields1


def get_field_names_of_model(model_class):
    "Get field names, including inherited fields, except M2M fields."
    fields = get_fields_from_model(model_class)
    return [field.name for field in fields]


def get_field_by_name_or_raise(model_class, field_name):
    "Get field by name, including inherited fields and M2M fields."
    return model_class._meta.get_field_by_name(field_name)[0]


def is_model_class(instance_or_model_class):
    "True if model_class is a Django Model."
    return isinstance(instance_or_model_class, Model) or instance_or_model_class.__class__ == ModelBase


def is_model_abstract(model):
    "True if abstract is True in Meta class"
    return model._meta.abstract


def is_model_managed(model):
    "True if managed is True in Meta class"
    return model._meta.managed


def model_has_the_field(model_class, field_name):
    ""
    try:
        get_field_by_name_or_raise(model_class, field_name)
        return True
    except FieldDoesNotExist:
        return False


# Fields
def get_unique_field_name(field):
    if hasattr(field, 'model'):
        return get_unique_model_name(field.model) + '.' + field.name
    return field.name


def get_related_model(field):
    return field.rel.to


def field_is_a_parent_link(field):
    # FIXME
    #return hasattr(field, 'rel') and hasattr(field.rel, 'parent_link') and field.rel.parent_link
    return hasattr(field, 'parent_link') and field.parent_link


def field_has_choices(field):
    """field.choices may be a tee, which we can't count without converting
    it to a list, or it may be a large database queryset, in which case we
    don't want to convert it to a list. We only care if the list is empty
    or not, so just try to access the first element and return True if that
    doesn't throw an exception."""
    for i in field.choices:
        return True
    return False


def field_has_default_value(field):
    return field.default != NOT_PROVIDED


def field_is_unique(field):
    return field.unique


def is_key_field(field):
    return isinstance(field, AutoField)


def is_relationship_field(field):
    return isinstance(field, (ForeignKey, OneToOneField))


def is_file_field(field):
    return isinstance(field, FileField)


def print_field_values_of_a_model(model_instance):
    "Print values from all fields of a model instance."
    if model_instance == None:
        print('\n:: Model Unknown: None')
    else:
        print('\n:: Model %s (%s)' % (get_unique_model_name(model_instance.__class__), model_instance.pk))
        for field in get_fields_from_model(model_instance.__class__):
            print('%s: %s' % (field.name, getattr(model_instance, field.name)))
        if model_instance.pk is not None:
            for field in get_many_to_many_fields_from_model(model_instance.__class__):
                print('%s: %s' % (field.name, getattr(model_instance, field.name).all()))


def print_field_values(model_instance_or_list_of_model_instances_or_queryset):
    "Print values from all fields of a model instance or a list of model instances."
    if isinstance(model_instance_or_list_of_model_instances_or_queryset, (list, tuple, QuerySet)):
        for model_instance in model_instance_or_list_of_model_instances_or_queryset:
            print_field_values_of_a_model(model_instance)
    else:
        model_instance = model_instance_or_list_of_model_instances_or_queryset
        print_field_values_of_a_model(model_instance)


def enable_auto_now(field):
    if hasattr(field, 'auto_now'):
        field.auto_now = True

def disable_auto_now(field):
    if hasattr(field, 'auto_now'):
        field.auto_now = False

def enable_auto_now_add(field):
    if hasattr(field, 'auto_now_add'):
        field.auto_now_add = True

def disable_auto_now_add(field):
    if hasattr(field, 'auto_now_add'):
        field.auto_now_add = False

########NEW FILE########
__FILENAME__ = fdf
# -*- coding: utf-8 -*-

import os
import tempfile

from shutil import rmtree, copy2
from django.core.files import File

from django.test import TestCase
from django.conf import settings
from django.core.files.storage import FileSystemStorage


TEMP_PATH = tempfile.gettempdir() or os.environ.get('TEMP')
TEMP_PATH_DDF = os.path.join(TEMP_PATH, 'DDF_TEMP')


class CustomFileSystemStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        super(CustomFileSystemStorage, self).\
        __init__(location=TEMP_PATH_DDF, *args, **kwargs)


class FileSystemDjangoTestCase(TestCase):
    TEAR_DOWN_ENABLED = True

    def setUp(self):
        self.fdf_setup()

    def tearDown(self):
        self.fdf_teardown()

    def _pre_setup(self):
        super(FileSystemDjangoTestCase, self)._pre_setup()
        self.fdf_setup()

    def _post_teardown(self):
        "Try to remove all files and directories created by the test."
        super(FileSystemDjangoTestCase, self)._post_teardown()
        self.fdf_teardown()

    def fdf_setup(self):
        self.directories = []
        self.files = {}
        setattr(settings, 'DEFAULT_FILE_STORAGE', 'django_dynamic_fixture.fdf.CustomFileSystemStorage')

    def fdf_teardown(self):
        if self.TEAR_DOWN_ENABLED:
            while self.files:
                self.remove_temp_file(next(iter(self.files.keys())))
            while self.directories:
                self.remove_temp_directory(self.directories[0])
            if os.path.exists(TEMP_PATH_DDF):
                rmtree(TEMP_PATH_DDF)

    def create_temp_directory(self, prefix='file_system_test_case_dir_'):
        "Create a temporary directory and returns the directory pathname."
        directory = tempfile.mkdtemp(prefix=prefix)
        self.directories.append(directory)
        return directory

    def remove_temp_directory(self, directory_pathname):
        "Remove a directory."
        rmtree(directory_pathname)
        if directory_pathname in self.directories:
            try:
                self.directories.remove(directory_pathname)
            except WindowsError:
                pass

    def create_temp_file(self, directory=None, prefix='file_system_test_case_file_', suffix='.tmp'):
        """
        Create a temporary file with a option prefix and suffix in a temporary or custom directory.
        Returns the filepath
        """
        tmp_file = tempfile.mkstemp(prefix=prefix, dir=directory, suffix=suffix)
        file_obj = os.fdopen(tmp_file[0])
        self.files[tmp_file[1]] = file_obj
        return tmp_file[1]

    def create_temp_file_with_name(self, directory, name):
        "Create a temporary file with a specified name."
        filepath = os.path.join(directory, name)
        file_obj = open(filepath, 'wb')
        file_obj.close()
        self.files[filepath] = file_obj
        return filepath

    def rename_temp_file(self, filepath, name):
        "Rename an existent file. 'name' is not a file path, so it must not include the directory path name."
        directory = self.get_directory_of_the_file(filepath)
        new_filepath = os.path.join(directory, name)
        os.rename(filepath, new_filepath)
        if filepath in self.files.keys():
            self.files.pop(filepath)
        self.files[new_filepath] = open(new_filepath, 'a+b')
        self.files[new_filepath].close()
        return new_filepath

    def remove_temp_file(self, filepath):
        "Remove a file."
        if filepath in self.files.keys():
            fileobj = self.files.pop(filepath)
            fileobj.close()
        if os.path.exists(filepath):
            try:
                os.unlink(filepath)
            except WindowsError:
                pass

    def copy_file_to_dir(self, filepath, directory):
        "Copy a file to a specified directory."
        copy2(filepath, directory)
        return self.get_filepath(directory, self.get_filename(filepath))

    def add_text_to_file(self, filepath, content):
        "Add text to an existent file."
        file = open(filepath, 'a')
        file.write(content)
        file.close()

    def get_directory_of_the_file(self, filepath):
        "Get the directory path name of a file."
        return os.path.dirname(filepath)

    def get_filename(self, filepath):
        "Get the filename of a file."
        return os.path.basename(filepath)

    def get_filepath(self, directory, filename):
        "Get the file path of a file with a defined name in a directory."
        return os.path.join(directory, filename)

    def get_content_of_file(self, filepath):
        "Returns the content of a file."
        file = open(filepath, 'r')
        content = file.read()
        file.close()
        return content

    def create_django_file_with_temp_file(self, name, content=None, dir=None, prefix='file_system_test_case_file_', suffix='.tmp'):
        "Create and returns a django.core.files.File"
        file = open(self.create_temp_file(directory=dir, prefix=prefix, suffix=suffix), 'w')
        file.close()
        django_file = File(file, name=name)
        self.files[django_file.file.name] = open(django_file.file.name, 'a+b')
        if content:
            self.files[django_file.file.name].write(content)
        self.files[django_file.file.name].close()
        return django_file

    def create_django_file_using_file(self, filepath):
        "Create and returns a django.core.files.File"
        new_filepath = self.copy_file_to_dir(filepath, self.create_temp_directory())
        the_file = open(new_filepath, 'rb')
        django_file = File(the_file, name=os.path.basename(new_filepath))
        self.files[django_file.file.name] = the_file
        #self.files[django_file.file.name].close()
        return django_file

    def assertFileExists(self, filepath):
        self.assertTrue(os.path.exists(filepath), msg='%s does not exist' % filepath)

    def assertFileDoesNotExists(self, filepath):
        self.assertFalse(os.path.exists(filepath), msg='%s exist' % filepath)

    def assertDirectoryExists(self, directory):
        "@directory must be the directory path"
        self.assertTrue(os.path.exists(directory), msg='%s does not exist' % directory)

    def assertDirectoryDoesNotExists(self, directory):
        "@directory must be the directory path"
        self.assertFalse(os.path.exists(directory), msg='%s exist' % directory)

    def assertDirectoryContainsFile(self, directory, filename):
        filepath = os.path.join(directory, filename)
        self.assertFileExists(filepath)

    def assertDirectoryDoesNotContainsFile(self, directory, filename):
        filepath = os.path.join(directory, filename)
        self.assertFileDoesNotExists(filepath)

    def assertFilesHaveEqualLastModificationTimestamps(self, filepath1, filepath2):
        self.assertEquals(0, os.path.getmtime(filepath1) - os.path.getmtime(filepath2))

    def assertFilesHaveNotEqualLastModificationTimestamps(self, filepath1, filepath2):
        self.assertNotEquals(0, os.path.getmtime(filepath1) - os.path.getmtime(filepath2))

    def assertNumberOfFiles(self, directory, number_of_files):
        filenames = [filename for filename in os.listdir(directory) if os.path.isfile(os.path.join(directory, filename))]
        self.assertEquals(number_of_files, len(filenames), msg='[%s] %s' % (len(filenames), filenames))

########NEW FILE########
__FILENAME__ = random_fixture
# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
from decimal import Decimal
import random
import string
import six

try:
    from django.utils.timezone import now
except ImportError:
    now = datetime.now

from django_dynamic_fixture.ddf import DataFixture


class RandomDataFixture(DataFixture):
    def random_string(self, n):
        return u''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))

    # NUMBERS
    def integerfield_config(self, field, key, start=1, end=10 ** 6):
        return random.randint(start, end)

    def smallintegerfield_config(self, field, key):
        # Values from -32768 to 32767 are safe in all databases supported by Django.
        return self.integerfield_config(field, key, -2 ** 15, 2 ** 15 - 1)

    def positiveintegerfield_config(self, field, key):
        return self.integerfield_config(field, key)

    def positivesmallintegerfield_config(self, field, key):
        # Values up to 32767 are safe in all databases supported by Django.
        return self.integerfield_config(field, key, end=2 ** 15 - 1)

    def bigintegerfield_config(self, field, key):
        return self.integerfield_config(field, key)

    def floatfield_config(self, field, key):
        return float(self.integerfield_config(field, key))

    def decimalfield_config(self, field, key):
        data = self.integerfield_config(field, key)
        number_of_digits = field.max_digits - field.decimal_places
        max_value = 10 ** number_of_digits
        data = data % max_value
        return Decimal(str(data))

    # STRINGS
    def charfield_config(self, field, key):
        if field.max_length:
            length = field.max_length
        else:
            length = 10
        return self.random_string(length)

    def textfield_config(self, field, key):
        return self.charfield_config(field, key)

    def slugfield_config(self, field, key):
        return self.charfield_config(field, key)

    def commaseparatedintegerfield_config(self, field, key):
        return six.text_type(random.randint(1, field.max_length)) #FIXME:

    # BOOLEAN
    def booleanfield_config(self, field, key):
        return random.randint(0, 1) == 0

    def nullbooleanfield_config(self, field, key):
        values = {0: None, 1: False, 2: True}
        return values[random.randint(0, 2)]

    # DATE/TIME RELATED
    def datefield_config(self, field, key):
        return date.today() - timedelta(days=random.randint(1, 36500))

    def timefield_config(self, field, key):
        return now() - timedelta(seconds=random.randint(1, 36500))

    def datetimefield_config(self, field, key):
        return now() - timedelta(seconds=random.randint(1, 36500))

    # FORMATTED STRINGS
    def emailfield_config(self, field, key):
        return u'a%s@dynamicfixture.com' % self.random_string(10)

    def urlfield_config(self, field, key):
        return u'http://dynamicfixture%s.com' % self.random_string(10)

    def ipaddressfield_config(self, field, key):
        a = random.randint(1, 255)
        b = random.randint(1, 255)
        c = random.randint(1, 255)
        d = random.randint(1, 255)
        return u'%s.%s.%s.%s' % (a, b, c, d)

    def xmlfield_config(self, field, key):
        return u'<a>%s</a>' % self.random_string(5)

    # FILES
    def filepathfield_config(self, field, key):
        return self.random_string(10)

    def filefield_config(self, field, key):
        return self.random_string(10)

    def imagefield_config(self, field, key):
        return self.random_string(10)


########NEW FILE########
__FILENAME__ = sequential_fixture
# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
from decimal import Decimal
import threading
import six

from django_dynamic_fixture.ddf import DataFixture
from django_dynamic_fixture.django_helper import field_is_unique

try:
    from django.utils.timezone import now
except ImportError:
    now = datetime.now


class AutoDataFiller(object):
    """
    Responsibility: generate a unique and sequential value for each key.
    """

    def __init__(self):
        self.__data_controller_map = {} # key => counter
        self.__locks = {} # key => lock

    # synchronized by key
    def next(self, key):
        if key not in self.__data_controller_map:
            self.__data_controller_map[key] = 0
            self.__locks[key] = threading.RLock()
        self.__locks[key].acquire()
        self.__data_controller_map[key] += 1
        value = self.__data_controller_map[key]
        self.__locks[key].release()
        return value

    def current(self, key):
        if key not in self.__data_controller_map:
            self.next(key)
        return self.__data_controller_map[key]


class SequentialDataFixture(DataFixture):

    def __init__(self):
        self.filler = AutoDataFiller()

    def get_value(self, field, key):
        return self.filler.next(key)

    # NUMBERS
    def integerfield_config(self, field, key):
        return self.get_value(field, key)

    def smallintegerfield_config(self, field, key):
        return self.integerfield_config(field, key)

    def positiveintegerfield_config(self, field, key):
        return self.integerfield_config(field, key)

    def positivesmallintegerfield_config(self, field, key):
        return self.integerfield_config(field, key)

    def bigintegerfield_config(self, field, key):
        return self.integerfield_config(field, key)

    def floatfield_config(self, field, key):
        return float(self.get_value(field, key))

    def decimalfield_config(self, field, key):
        data = self.get_value(field, key)
        number_of_digits = field.max_digits - field.decimal_places
        max_value = 10 ** number_of_digits
        data = data % max_value
        return Decimal(str(data))

    # STRINGS
    def charfield_config(self, field, key):
        data = self.get_value(field, key)
        if field.max_length:
            max_value = (10 ** field.max_length) - 1
            data = six.text_type(data % max_value)
            data = data[:field.max_length]
        else:
            data = six.text_type(data)
        return data

    def textfield_config(self, field, key):
        return self.charfield_config(field, key)

    def slugfield_config(self, field, key):
        return self.charfield_config(field, key)

    def commaseparatedintegerfield_config(self, field, key):
        return self.charfield_config(field, key)

    # BOOLEAN
    def booleanfield_config(self, field, key):
        return False

    def nullbooleanfield_config(self, field, key):
        return None

    # DATE/TIME RELATED
    def datefield_config(self, field, key):
        data = self.get_value(field, key)
        return date.today() - timedelta(days=data)

    def timefield_config(self, field, key):
        data = self.get_value(field, key)
        return now() - timedelta(seconds=data)

    def datetimefield_config(self, field, key):
        data = self.get_value(field, key)
        return now() - timedelta(seconds=data)

    # FORMATTED STRINGS
    def emailfield_config(self, field, key):
        return u'a%s@dynamicfixture.com' % self.get_value(field, key)

    def urlfield_config(self, field, key):
        return u'http://dynamicfixture%s.com' % self.get_value(field, key)

    def ipaddressfield_config(self, field, key):
        # TODO: better workaround (this suppose ip field is not unique)
        data = self.get_value(field, key)
        a = '1'
        b = '1'
        c = '1'
        d = data % 256
        return u'%s.%s.%s.%s' % (a, b, c, str(d))

    def xmlfield_config(self, field, key):
        return u'<a>%s</a>' % self.get_value(field, key)

    # FILES
    def filepathfield_config(self, field, key):
        return six.text_type(self.get_value(field, key))

    def filefield_config(self, field, key):
        return six.text_type(self.get_value(field, key))

    def imagefield_config(self, field, key):
        return six.text_type(self.get_value(field, key))


class GlobalSequentialDataFixture(SequentialDataFixture):
    def get_value(self, field, key):
        return self.filler.next('ddf-global-key')


class StaticSequentialDataFixture(SequentialDataFixture):
    def get_value(self, field, key):
        if field_is_unique(field):
            return self.filler.next(key)
        else:
            return self.filler.current(key)

########NEW FILE########
__FILENAME__ = abstract_test_generic_fixture
# -*- coding: utf-8 -*-

from django.db import models

from datetime import datetime, date
from decimal import Decimal
import six
from six.moves import xrange


class DataFixtureTestCase(object):
    def setUp(self):
        self.fixture = None

    def test_numbers(self):
        self.assertTrue(isinstance(self.fixture.generate_data(models.IntegerField()), int))
        self.assertTrue(isinstance(self.fixture.generate_data(models.SmallIntegerField()), int))
        self.assertTrue(isinstance(self.fixture.generate_data(models.PositiveIntegerField()), int))
        self.assertTrue(isinstance(self.fixture.generate_data(models.PositiveSmallIntegerField()), int))
        self.assertTrue(isinstance(self.fixture.generate_data(models.BigIntegerField()), int))
        self.assertTrue(isinstance(self.fixture.generate_data(models.FloatField()), float))
        self.assertTrue(isinstance(self.fixture.generate_data(models.DecimalField(max_digits=1, decimal_places=1)), Decimal))

    def test_it_must_deal_with_decimal_max_digits(self):
        # value 10 must be a problem, need to restart the counter: 10.0 has 3 digits
        for _ in xrange(11):
            self.assertTrue(isinstance(self.fixture.generate_data(models.DecimalField(max_digits=1, decimal_places=1)), Decimal))
            self.assertTrue(isinstance(self.fixture.generate_data(models.DecimalField(max_digits=2, decimal_places=1)), Decimal))

    def test_strings(self):
        self.assertTrue(isinstance(self.fixture.generate_data(models.CharField(max_length=1)), six.text_type))
        self.assertTrue(isinstance(self.fixture.generate_data(models.TextField()), six.text_type))
        self.assertTrue(isinstance(self.fixture.generate_data(models.SlugField(max_length=1)), six.text_type))
        self.assertTrue(isinstance(self.fixture.generate_data(models.CommaSeparatedIntegerField(max_length=1)), six.text_type))

    def test_new_truncate_strings_to_max_length(self):
        for _ in range(12): # truncate start after the 10 object
            self.assertTrue(isinstance(self.fixture.generate_data(models.CharField(max_length=1)), six.text_type))

    def test_boolean(self):
        self.assertTrue(isinstance(self.fixture.generate_data(models.BooleanField()), bool))
        value = self.fixture.generate_data(models.NullBooleanField())
        self.assertTrue(isinstance(value, bool) or value == None)

    def test_date_time_related(self):
        self.assertTrue(isinstance(self.fixture.generate_data(models.DateField()), date))
        self.assertTrue(isinstance(self.fixture.generate_data(models.TimeField()), datetime))
        self.assertTrue(isinstance(self.fixture.generate_data(models.DateTimeField()), datetime))

    def test_formatted_strings(self):
        self.assertTrue(isinstance(self.fixture.generate_data(models.EmailField(max_length=100)), six.text_type))
        self.assertTrue(isinstance(self.fixture.generate_data(models.URLField(max_length=100)), six.text_type))
        self.assertTrue(isinstance(self.fixture.generate_data(models.IPAddressField(max_length=100)), six.text_type))

    def test_files(self):
        self.assertTrue(isinstance(self.fixture.generate_data(models.FilePathField(max_length=100)), six.text_type))
        self.assertTrue(isinstance(self.fixture.generate_data(models.FileField()), six.text_type))
        try:
            import pil
            # just test it if the PIL package is installed
            self.assertTrue(isinstance(self.fixture.generate_data(models.ImageField(max_length=100)), six.text_type))
        except ImportError:
            pass


########NEW FILE########
__FILENAME__ = test_random_fixture
# -*- coding: utf-8 -*-

from django.test import TestCase

from django_dynamic_fixture.fixture_algorithms.tests.abstract_test_generic_fixture import DataFixtureTestCase
from django_dynamic_fixture.fixture_algorithms.random_fixture import RandomDataFixture


class RandomDataFixtureTestCase(TestCase, DataFixtureTestCase):
    def setUp(self):
        self.fixture = RandomDataFixture()

########NEW FILE########
__FILENAME__ = test_sequential_fixture
# -*- coding: utf-8 -*-
from django.db import models

from django.test import TestCase

from django_dynamic_fixture.fixture_algorithms.tests.abstract_test_generic_fixture import DataFixtureTestCase
from django_dynamic_fixture.fixture_algorithms.sequential_fixture import SequentialDataFixture, StaticSequentialDataFixture


class SequentialDataFixtureTestCase(TestCase, DataFixtureTestCase):
    def setUp(self):
        self.fixture = SequentialDataFixture()

    def test_it_must_fill_integer_fields_sequencially_by_attribute(self):
        self.assertEquals(1, self.fixture.generate_data(models.IntegerField()))
        field = models.IntegerField()
        field.name = 'x'
        self.assertEquals(1, self.fixture.generate_data(field))
        self.assertEquals(2, self.fixture.generate_data(field))

    def test_it_must_fill_string_with_sequences_of_numbers_by_attribute(self):
        self.assertEquals('1', self.fixture.generate_data(models.CharField(max_length=1)))
        field = models.CharField(max_length=1)
        field.name = 'x'
        self.assertEquals('1', self.fixture.generate_data(field))
        self.assertEquals('2', self.fixture.generate_data(field))


class StaticSequentialDataFixtureTestCase(TestCase, DataFixtureTestCase):
    def setUp(self):
        self.fixture = StaticSequentialDataFixture()

    def test_it_must_fill_fields_sequencially_by_attribute_if_field_is_unique(self):
        field = models.IntegerField(unique=True)
        field.name = 'x'
        self.assertEquals(1, self.fixture.generate_data(field))
        self.assertEquals(2, self.fixture.generate_data(field))

    def test_it_must_fill_fields_with_static_value_by_attribute_if_field_is_not_unique(self):
        field = models.IntegerField(unique=False)
        field.name = 'x'
        self.assertEquals(1, self.fixture.generate_data(field))
        self.assertEquals(1, self.fixture.generate_data(field))


########NEW FILE########
__FILENAME__ = test_unique_random_fixture
# -*- coding: utf-8 -*-
from warnings import catch_warnings

from django.db import models
from django.test import TestCase

from django_dynamic_fixture.fixture_algorithms.tests.abstract_test_generic_fixture import DataFixtureTestCase
from django_dynamic_fixture.fixture_algorithms.unique_random_fixture import \
    UniqueRandomDataFixture
from six.moves import xrange


class RandomDataFixtureTestCase(TestCase, DataFixtureTestCase):
    def setUp(self):
        self.fixture = UniqueRandomDataFixture()

    def test_generated_strings_are_unique(self):
        results = set()
        for _ in xrange(self.fixture.OBJECT_COUNT):
            results.add(
                self.fixture.generate_data(models.CharField(max_length=10))
            )
        self.assertEqual(len(results), self.fixture.OBJECT_COUNT)

    def test_generated_signed_integers_are_unique(self):
        results = set()
        prev = 0
        for _ in xrange(self.fixture.OBJECT_COUNT):
            integer = self.fixture.generate_data(models.IntegerField())
            results.add(integer)
            self.assertTrue(abs(integer) > abs(prev))
            prev = integer
        self.assertEqual(len(results), self.fixture.OBJECT_COUNT)

    def test_generated_unsigned_integers_are_unique(self):
        results = set()
        prev = 0
        for _ in xrange(self.fixture.OBJECT_COUNT):
            integer = self.fixture.generate_data(models.PositiveIntegerField())
            results.add(integer)
            self.assertTrue(integer > prev)
            prev = integer
        self.assertEqual(len(results), self.fixture.OBJECT_COUNT)

    def test_warning(self):
        with catch_warnings(record=True) as w:
            for _ in xrange(self.fixture.OBJECT_COUNT + 1):
                self.fixture.generate_data(models.CharField(max_length=10))
            warning = w[-1]
            self.assertTrue(issubclass(warning.category, RuntimeWarning))
            expected_message = (
                self.fixture.WARNING_MESSAGE_TMPL % self.fixture.OBJECT_COUNT
            )
            self.assertTrue(expected_message in str(warning.message))

########NEW FILE########
__FILENAME__ = unique_random_fixture
# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
from decimal import Decimal
from itertools import chain
import random
import socket
import string
import struct
from warnings import warn
import six

from django_dynamic_fixture.ddf import DataFixture
from django_dynamic_fixture.fixture_algorithms.sequential_fixture import \
    AutoDataFiller
from six.moves import xrange

try:
    from django.utils.timezone import now
except ImportError:
    now = datetime.now


class UniqueRandomDataFixture(DataFixture):

    DEFAULT_LENGTH = 10
    OBJECT_COUNT = 512
    WARNING_MESSAGE_TMPL = (
        'Maximum number of objects (%d) is exceeded in '
        'unique_random_fixture. Uniqueness is not guaranteed.'
    )

    def __init__(self):
        self.filler = AutoDataFiller()

    def get_counter(self, field, key):
        result = self.filler.next(key)
        if result > self.OBJECT_COUNT:
            warn(self.WARNING_MESSAGE_TMPL % self.OBJECT_COUNT, RuntimeWarning)
        return result

    def random_string(self, field, key, n=None):
        counter = six.text_type(self.get_counter(field, key))
        length = n or self.DEFAULT_LENGTH
        result = counter
        result += u''.join(
            random.choice(string.ascii_letters)
            for _ in xrange(length - len(counter))
        )
        return result

    def random_integer(self, field, key, signed=True):
        counter = self.get_counter(field, key) - 1
        counter %= self.OBJECT_COUNT
        if not signed:
            MAX_INT = 2 ** 16
            multiplier = MAX_INT // self.OBJECT_COUNT
            return random.randrange(
                multiplier * counter + 1, multiplier * (counter + 1)
            )

        MAX_SIGNED_INT = 2 ** 15
        multiplier = MAX_SIGNED_INT // self.OBJECT_COUNT
        positive_range = range(
            multiplier * counter + 1, multiplier * (counter + 1)
        )
        negative_range = range(
            (-multiplier) * (counter + 1), (-multiplier) * counter
        )
        return random.choice(list(chain(positive_range, negative_range)))

    # NUMBERS
    def integerfield_config(self, field, key):
        return self.random_integer(field, key)

    def smallintegerfield_config(self, field, key):
        return self.random_integer(field, key)

    def bigintegerfield_config(self, field, key):
        return self.random_integer(field, key)

    def positiveintegerfield_config(self, field, key):
        return self.random_integer(field, key, signed=False)

    def positivesmallintegerfield_config(self, field, key):
        return self.random_integer(field, key, signed=False)

    def floatfield_config(self, field, key):
        return float(self.random_integer(field, key)) + random.random()

    def decimalfield_config(self, field, key):
        number_of_digits = field.max_digits - field.decimal_places
        max_value = 10 ** number_of_digits
        value = self.random_integer(field, key) % max_value
        value = float(value) + random.random()
        return Decimal(str(value))

    # STRINGS
    def charfield_config(self, field, key):
        return self.random_string(field, key, field.max_length)

    def textfield_config(self, field, key):
        return self.charfield_config(field, key)

    def slugfield_config(self, field, key):
        return self.charfield_config(field, key)

    def commaseparatedintegerfield_config(self, field, key):
        return self.charfield_config(field, key)

    # BOOLEAN
    def booleanfield_config(self, field, key):
        counter = self.get_counter(field, key)
        if counter == 1:
            return True
        elif counter == 2:
            return False
        return random.choice((True, False))

    def nullbooleanfield_config(self, field, key):
        counter = self.get_counter(field, key)
        if counter == 1:
            return None
        elif counter == 2:
            return True
        elif counter == 3:
            return False
        return random.choice((None, True, False))

    # DATE/TIME RELATED
    def datefield_config(self, field, key):
        integer = self.random_integer(field, key, signed=False)
        return date.today() - timedelta(days=integer)

    def timefield_config(self, field, key):
        integer = self.random_integer(field, key, signed=False)
        return now() - timedelta(seconds=integer)

    def datetimefield_config(self, field, key):
        integer = self.random_integer(field, key, signed=False)
        return now() - timedelta(seconds=integer)

    # FORMATTED STRINGS
    def emailfield_config(self, field, key):
        return u'a%s@dynamicfixture.com' % self.random_string(field, key)

    def urlfield_config(self, field, key):
        return u'http://dynamicfixture%s.com' % self.random_string(field, key)

    def ipaddressfield_config(self, field, key):
        MAX_IP = 2 ** 32 - 1

        integer = self.random_integer(field, key, signed=False)
        integer %= MAX_IP
        return six.text_type(socket.inet_ntoa(struct.pack('!L', integer)))

    def xmlfield_config(self, field, key):
        return u'<a>%s</a>' % self.random_string(field, key)

    # FILES
    def filepathfield_config(self, field, key):
        return self.random_string(field, key)

    def filefield_config(self, field, key):
        return self.random_string(field, key)

    def imagefield_config(self, field, key):
        return self.random_string(field, key)

########NEW FILE########
__FILENAME__ = global_settings
# -*- coding: utf-8 -*-

"""
Module that contains wrappers and shortcuts.
This is the facade of all features of DDF.
"""
import sys

from django.conf import settings
from django.core.urlresolvers import get_mod_func
from django.utils.importlib import import_module
import six

from django_dynamic_fixture.fixture_algorithms.sequential_fixture import SequentialDataFixture, StaticSequentialDataFixture, GlobalSequentialDataFixture
from django_dynamic_fixture.fixture_algorithms.random_fixture import RandomDataFixture


class DDFImproperlyConfigured(Exception):
    "DDF is improperly configured. Some global settings has bad value in django settings."


def get_boolean_config(config_name, default=False):
    try:
        if hasattr(settings, config_name) and getattr(settings, config_name) not in [True, False]:
            # to educate users to use this property correctly.
            raise DDFImproperlyConfigured()
        return getattr(settings, config_name) if hasattr(settings, config_name) else default
    except DDFImproperlyConfigured:
        six.reraise(DDFImproperlyConfigured, DDFImproperlyConfigured("%s (%s) must be True or False." % (config_name, getattr(settings, config_name))), sys.exc_info()[2])


# DDF_DEFAULT_DATA_FIXTURE default = 'sequential'
# It must be 'sequential', 'static_sequential', 'global_sequential', 'random' or 'path.to.CustomDataFixtureClass'
try:
    INTERNAL_DATA_FIXTURES = {'sequential': SequentialDataFixture(),
                              'static_sequential': StaticSequentialDataFixture(),
                              'global_sequential': GlobalSequentialDataFixture(),
                              'random': RandomDataFixture()}
    if hasattr(settings, 'DDF_DEFAULT_DATA_FIXTURE'):
        if settings.DDF_DEFAULT_DATA_FIXTURE in INTERNAL_DATA_FIXTURES.keys():
            DDF_DEFAULT_DATA_FIXTURE = INTERNAL_DATA_FIXTURES[settings.DDF_DEFAULT_DATA_FIXTURE]
        else:
            # path.to.CustomDataFixtureClass
            mod_name, obj_name = get_mod_func(settings.DDF_DEFAULT_DATA_FIXTURE)
            module = import_module(mod_name)
            custom_data_fixture = getattr(module, obj_name)
            DDF_DEFAULT_DATA_FIXTURE = custom_data_fixture()
    else:
        DDF_DEFAULT_DATA_FIXTURE = INTERNAL_DATA_FIXTURES['sequential']
except:
    six.reraise(DDFImproperlyConfigured, DDFImproperlyConfigured("DDF_DEFAULT_DATA_FIXTURE (%s) must be 'sequential', 'static_sequential', 'global_sequential', 'random' or 'path.to.CustomDataFixtureClass'." % settings.DDF_DEFAULT_DATA_FIXTURE), sys.exc_info()[2])


# DDF_IGNORE_FIELDS default = []
try:
    DDF_IGNORE_FIELDS = list(settings.DDF_IGNORE_FIELDS) if hasattr(settings, 'DDF_IGNORE_FIELDS') else []
except Exception as e:
    six.reraise(DDFImproperlyConfigured, DDFImproperlyConfigured("DDF_IGNORE_FIELDS (%s) must be a list of strings" % settings.DDF_IGNORE_FIELDS), sys.exc_info()[2])


# DDF_NUMBER_OF_LAPS default = 1
try:
    DDF_NUMBER_OF_LAPS = int(settings.DDF_NUMBER_OF_LAPS) if hasattr(settings, 'DDF_NUMBER_OF_LAPS') else 1
except Exception as e:
    six.reraise(DDFImproperlyConfigured, DDFImproperlyConfigured("DDF_NUMBER_OF_LAPS (%s) must be a integer number." % settings.DDF_NUMBER_OF_LAPS), sys.exc_info()[2])


DDF_FILL_NULLABLE_FIELDS = get_boolean_config('DDF_FILL_NULLABLE_FIELDS', default=True)
DDF_VALIDATE_MODELS = get_boolean_config('DDF_VALIDATE_MODELS', default=False)
DDF_VALIDATE_ARGS = get_boolean_config('DDF_VALIDATE_ARGS', default=False)
DDF_USE_LIBRARY = get_boolean_config('DDF_USE_LIBRARY', default=False)
DDF_DEBUG_MODE = get_boolean_config('DDF_DEBUG_MODE', default=False)


########NEW FILE########
__FILENAME__ = models
from django.conf import settings

import_models = getattr(settings, 'IMPORT_DDF_MODELS', False)

if settings.IMPORT_DDF_MODELS:
    from django_dynamic_fixture.models_test import *

########NEW FILE########
__FILENAME__ = models_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


class EmptyModel(models.Model):
    pass


class ModelWithNumbers(models.Model):
    #id is a models.AutoField()
    integer = models.IntegerField(null=True, unique=True)
    smallinteger = models.SmallIntegerField(null=True, unique=True)
    positiveinteger = models.PositiveIntegerField(null=True, unique=True)
    positivesmallinteger = models.PositiveSmallIntegerField(null=True, unique=True)
    biginteger = models.BigIntegerField(null=True, unique=True)
    float = models.FloatField(null=True, unique=True)
    decimal = models.DecimalField(max_digits=2, decimal_places=1, null=True, unique=False)

    class Meta:
        verbose_name = 'Numbers'


class ModelWithStrings(models.Model):
    string = models.CharField(max_length=1, null=True, unique=True)
    text = models.TextField(null=True, unique=True)
    slug = models.SlugField(null=True, unique=True)
    commaseparated = models.CommaSeparatedIntegerField(max_length=100, null=True, unique=True)

    class Meta:
        verbose_name = 'Strings'


class ModelWithBooleans(models.Model):
    boolean = models.BooleanField()
    nullboolean = models.NullBooleanField()

    class Meta:
        verbose_name = 'Booleans'


class ModelWithDateTimes(models.Model):
    date = models.DateField(null=True, unique=True)
    datetime = models.DateTimeField(null=True, unique=True)
    time = models.TimeField(null=True, unique=True)

    class Meta:
        verbose_name = 'DateTimes'


class ModelWithFieldsWithCustomValidation(models.Model):
    email = models.EmailField(null=True, unique=True)
    url = models.URLField(null=True, unique=True)
    ip = models.IPAddressField(null=True, unique=False)

    class Meta:
        verbose_name = 'Custom validation'


class ModelWithFileFields(models.Model):
    filepath = models.FilePathField(unique=True, blank=True)
    file = models.FileField(upload_to='.')

    try:
        import pil
        # just test it if the PIL package is installed
        image = models.ImageField(upload_to='.')
    except ImportError:
        pass

    class Meta:
        verbose_name = 'File fields'


class ModelWithDefaultValues(models.Model):
    integer_with_default = models.IntegerField(null=True, default=3)
    string_with_choices = models.CharField(max_length=5, null=True, choices=(('a', 'A'), ('b', 'B')))
    string_with_choices_and_default = models.CharField(max_length=5, null=True, default='b', choices=(('a', 'A'), ('b', 'B')))
    string_with_optgroup_choices = models.CharField(max_length=5, null=True, choices=(('group1', (('a', 'A'), ('b', 'B'))), ('group2', (('c', 'C'), ('d', 'D')))))
    foreign_key_with_default = models.ForeignKey(EmptyModel, null=True, default=None)

    class Meta:
        verbose_name = 'Default values'


class ModelForNullable(models.Model):
    nullable = models.IntegerField(null=True)
    not_nullable = models.IntegerField(null=False)

    class Meta:
        verbose_name = 'Nullable'


class ModelForIgnoreList2(models.Model):
    nullable = models.IntegerField(null=True)

    class Meta:
        verbose_name = 'Ignore list 2'


class ModelForIgnoreList(models.Model):
    required = models.IntegerField(null=False)
    required_with_default = models.IntegerField(null=False, default=1)
    not_required = models.IntegerField(null=True)
    not_required_with_default = models.IntegerField(null=True, default=1)
    self_reference = models.ForeignKey('ModelForIgnoreList', null=True)
    different_reference = models.ForeignKey(ModelForIgnoreList2, null=True)

    class Meta:
        verbose_name = 'Ignore list'


class ModelRelated(models.Model):
    selfforeignkey = models.ForeignKey('self', null=True)
    integer = models.IntegerField(null=True)
    integer_b = models.IntegerField(null=True)

    class Meta:
        verbose_name = 'Related'


class ModelRelatedThrough(models.Model):
    related = models.ForeignKey('ModelRelated')
    relationship = models.ForeignKey('ModelWithRelationships')


def default_fk_value():
    try:
        return ModelRelated.objects.get(id=1)
    except ModelRelated.DoesNotExist:
        return None


class ModelWithRelationships(models.Model):
    # relationship
    selfforeignkey = models.ForeignKey('self', null=True)
    foreignkey = models.ForeignKey('ModelRelated', related_name='fk', null=True)
    onetoone = models.OneToOneField('ModelRelated', related_name='o2o', null=True)
    manytomany = models.ManyToManyField('ModelRelated', related_name='m2m')
    manytomany_through = models.ManyToManyField('ModelRelated', related_name='m2m_through', through=ModelRelatedThrough)

    foreignkey_with_default = models.ForeignKey('ModelRelated', related_name='fk2', null=True, default=default_fk_value)

    integer = models.IntegerField(null=True)
    integer_b = models.IntegerField(null=True)
    # generic field
    # TODO

    class Meta:
        verbose_name = 'Relationships'


class ModelWithCyclicDependency(models.Model):
    d = models.ForeignKey('ModelWithCyclicDependency2', null=True)

    class Meta:
        verbose_name = 'Cyclic dependency'


class ModelWithCyclicDependency2(models.Model):
    c = models.ForeignKey(ModelWithCyclicDependency, null=True)

    class Meta:
        verbose_name = 'Cyclic dependency 2'


class ModelAbstract(models.Model):
    integer = models.IntegerField(null=True, unique=True)
    class Meta:
        abstract = True
        verbose_name = 'Abstract'


class ModelParent(ModelAbstract):
    class Meta:
        verbose_name = 'Parent'


class ModelChild(ModelParent):
    class Meta:
        verbose_name = 'Child'


class ModelChildWithCustomParentLink(ModelParent):
    my_custom_ref = models.OneToOneField(ModelParent, parent_link=True, related_name='my_custom_ref_x')

    class Meta:
        verbose_name = 'Custom child'


class ModelWithRefToParent(models.Model):
    parent = models.ForeignKey(ModelParent)

    class Meta:
        verbose_name = 'Child with parent'


class CustomDjangoField(models.IntegerField):
    pass


class CustomDjangoFieldMixin(object):
    pass


class CustomDjangoFieldMultipleInheritance(CustomDjangoFieldMixin, models.IntegerField):
    pass


class NewField(models.Field):
    pass


class ModelWithCustomFields(models.Model):
    x = CustomDjangoField(null=False)
    y = NewField(null=True)

    class Meta:
        verbose_name = 'Custom fields'


class ModelWithCustomFieldsMultipleInheritance(models.Model):
    x = CustomDjangoFieldMultipleInheritance(null=False)
    y = NewField(null=True)

    class Meta:
        verbose_name = 'Custom fields with multiple inheritance'


class ModelWithUnsupportedField(models.Model):
    z = NewField(null=False)

    class Meta:
        verbose_name = 'Unsupported field'


class ModelWithValidators(models.Model):
    field_validator = models.CharField(max_length=3, validators=[RegexValidator(regex=r'ok')])
    clean_validator = models.CharField(max_length=3)

    class Meta:
        verbose_name = 'Validators'

    def clean(self):
        if self.clean_validator != 'ok':
            raise ValidationError('ops')


class ModelWithAutoDateTimes(models.Model):
    auto_now_add = models.DateField(auto_now_add=True)
    auto_now = models.DateField(auto_now=True)
    manytomany = models.ManyToManyField('ModelWithAutoDateTimes', related_name='m2m')

    class Meta:
        verbose_name = 'Auto DateTime'


class ModelForCopy2(models.Model):
    int_e = models.IntegerField()

    class Meta:
        verbose_name = 'Copy 2'


class ModelForCopy(models.Model):
    int_a = models.IntegerField()
    int_b = models.IntegerField(null=None)
    int_c = models.IntegerField()
    int_d = models.IntegerField()
    e = models.ForeignKey(ModelForCopy2)

    class Meta:
        verbose_name = 'Copy'


class ModelForLibrary2(models.Model):
    integer = models.IntegerField(null=True)
    integer_unique = models.IntegerField(null=True, unique=True)

    class Meta:
        verbose_name = 'Library 2'


class ModelForLibrary(models.Model):
    integer = models.IntegerField(null=True)
    integer_unique = models.IntegerField(null=True, unique=True)
    selfforeignkey = models.ForeignKey('self', null=True)
    foreignkey = models.ForeignKey('ModelForLibrary2', related_name='fk', null=True)

    class Meta:
        verbose_name = 'Library'


class ModelForDDFSetup(models.Model):
    integer = models.IntegerField(null=True)

    class Meta:
        verbose_name = 'DDF setup'


class ModelWithClean(models.Model):
    integer = models.IntegerField()

    class Meta:
        verbose_name = 'Clean'

    def clean(self):
        if self.integer != 9999: # just for testing
            raise ValidationError('integer is not 9999')


class ModelForSignals(models.Model):
    class Meta:
        verbose_name = 'Signals'


class ModelForSignals2(models.Model):
    class Meta:
        verbose_name = 'Signals 2'

########NEW FILE########
__FILENAME__ = test_ddf
# -*- coding: utf-8 -*-

from django.test import TestCase

from django_dynamic_fixture.models_test import *
from django_dynamic_fixture.ddf import *
from django_dynamic_fixture.ddf import _PRE_SAVE, _POST_SAVE
from django_dynamic_fixture.fixture_algorithms.sequential_fixture import SequentialDataFixture

from datetime import datetime, date
from decimal import Decimal


data_fixture = SequentialDataFixture()


class DDFTestCase(TestCase):
    def setUp(self):
        self.ddf = DynamicFixture(data_fixture)
        DDFLibrary.get_instance().clear()
        _PRE_SAVE.clear()
        _POST_SAVE.clear()


class NewCreateAModelInstanceTest(DDFTestCase):
    def test_new_create_a_non_saved_instance_of_the_model(self):
        instance = self.ddf.new(EmptyModel)
        self.assertTrue(isinstance(instance, EmptyModel))
        self.assertEquals(None, instance.id)


class GetDealWithPrimaryKeyTest(DDFTestCase):
    def test_get_use_database_id_by_default(self):
        instance = self.ddf.get(EmptyModel)
        self.assertNotEquals(None, instance.id)
        self.assertNotEquals(None, instance.pk)

    def test_get_use_given_id(self):
        instance = self.ddf.new(EmptyModel, id=99998)
        self.assertEquals(99998, instance.id)
        self.assertEquals(99998, instance.pk)


class NewFullFillAttributesWithAutoDataTest(DDFTestCase):
    def test_new_fill_number_fields_with_numbers(self):
        instance = self.ddf.new(ModelWithNumbers)
        self.assertTrue(isinstance(instance.integer, int))
        self.assertTrue(isinstance(instance.smallinteger, int))
        self.assertTrue(isinstance(instance.positiveinteger, int))
        self.assertTrue(isinstance(instance.positivesmallinteger, int))
        self.assertTrue(isinstance(instance.biginteger, int))
        self.assertTrue(isinstance(instance.float, float))

    def test_new_fill_string_fields_with_text_type_strings(self):
        instance = self.ddf.new(ModelWithStrings)
        self.assertTrue(isinstance(instance.string, six.text_type))
        self.assertTrue(isinstance(instance.text, six.text_type))
        self.assertTrue(isinstance(instance.slug, six.text_type))
        self.assertTrue(isinstance(instance.commaseparated, six.text_type))

    def test_new_fill_boolean_fields_with_False_and_None(self):
        instance = self.ddf.new(ModelWithBooleans)
        self.assertEquals(False, instance.boolean)
        self.assertEquals(None, instance.nullboolean)

    def test_new_fill_time_related_fields_with_current_values(self):
        instance = self.ddf.new(ModelWithDateTimes)
        self.assertTrue(date.today() >= instance.date)
        self.assertTrue(datetime.now() >= instance.time)
        self.assertTrue(datetime.now() >= instance.datetime)

    def test_new_fill_formatted_strings_fields_with_basic_values(self):
        instance = self.ddf.new(ModelWithFieldsWithCustomValidation)
        self.assertTrue(isinstance(instance.email, six.text_type))
        self.assertTrue(isinstance(instance.url, six.text_type))
        self.assertTrue(isinstance(instance.ip, six.text_type))

    def test_new_fill_file_fields_with_basic_strings(self):
        instance = self.ddf.new(ModelWithFileFields)
        self.assertTrue(isinstance(instance.filepath, six.text_type))
        self.assertTrue(isinstance(instance.file.path, six.text_type))
        try:
            import pil
            # just test it if the PIL package is installed
            self.assertTrue(isinstance(instance.image, str))
        except ImportError:
            pass


class NewFullFillAttributesWithDefaultDataTest(DDFTestCase):
    def test_fill_field_with_default_data(self):
        instance = self.ddf.new(ModelWithDefaultValues)
        self.assertEquals(3, instance.integer_with_default)

    def test_fill_field_with_possible_choices(self):
        instance = self.ddf.new(ModelWithDefaultValues)
        self.assertEquals('a', instance.string_with_choices)

    def test_fill_field_with_default_value_even_if_field_is_foreign_key(self):
        instance = self.ddf.new(ModelWithDefaultValues)
        self.assertEquals(None, instance.foreign_key_with_default)

    def test_fill_field_with_default_data_and_choices_must_consider_default_data_instead_choices(self):
        instance = self.ddf.new(ModelWithDefaultValues)
        self.assertEquals('b', instance.string_with_choices_and_default)

    def test_fill_field_with_possible_optgroup_choices(self):
        instance = self.ddf.new(ModelWithDefaultValues)
        self.assertEquals('a', instance.string_with_optgroup_choices)


class NewFullFillAttributesWithCustomDataTest(DDFTestCase):
    def test_fields_are_filled_with_custom_attributes(self):
        self.assertEquals(9, self.ddf.new(ModelWithNumbers, integer=9).integer)
        self.assertEquals('7', self.ddf.new(ModelWithStrings, string='7').string)
        self.assertEquals(True, self.ddf.new(ModelWithBooleans, boolean=True).boolean)

    def test_decimal_can_be_filled_by_an_string(self):
        self.ddf.get(ModelWithNumbers, decimal='9.5')
        self.assertEquals(Decimal('9.5'), ModelWithNumbers.objects.latest('id').decimal)

    def test_fields_can_be_filled_by_functions(self):
        instance = self.ddf.new(ModelWithStrings, string=lambda field: field.name)
        self.assertEquals('string', instance.string)

    def test_invalid_configuration_raise_an_error(self):
        self.assertRaises(InvalidConfigurationError, self.ddf.new, ModelWithNumbers, integer=lambda x: ''.invalidmethod())

    def test_bad_data_raise_an_error(self):
        self.ddf.get(ModelWithNumbers, integer=50000)
        self.assertRaises(BadDataError, self.ddf.get, ModelWithNumbers, integer=50000)


class NewIgnoringNullableFieldsTest(DDFTestCase):
    def test_new_do_not_fill_nullable_fields_if_we_do_not_want_to(self):
        self.ddf = DynamicFixture(data_fixture, fill_nullable_fields=False)
        instance = self.ddf.new(ModelForNullable)
        self.assertNotEquals(None, instance.not_nullable)
        self.assertEquals(None, instance.nullable)


class NewIgnoreFieldsInIgnoreListTest(DDFTestCase):
    def test_new_do_not_fill_ignored_fields(self):
        self.ddf = DynamicFixture(data_fixture, ignore_fields=['not_required', 'not_required_with_default'])
        instance = self.ddf.new(ModelForIgnoreList)
        self.assertEquals(None, instance.not_required)
        self.assertNotEquals(None, instance.not_required_with_default)
        # not ignored fields
        self.assertNotEquals(None, instance.required)
        self.assertNotEquals(None, instance.required_with_default)

    def test_get_raise_an_error_if_a_required_field_is_in_ignore_list(self):
        self.ddf = DynamicFixture(data_fixture, ignore_fields=['required', 'required_with_default'])
        self.assertRaises(BadDataError, self.ddf.get, ModelForIgnoreList)

    def test_ignore_fields_are_propagated_to_self_references(self):
        self.ddf = DynamicFixture(data_fixture, ignore_fields=['not_required', 'nullable'])
        instance = self.ddf.new(ModelForIgnoreList)
        self.assertEquals(None, instance.not_required)
        self.assertEquals(None, instance.self_reference.not_required)

    def test_ignore_fields_are_not_propagated_to_different_references(self):
        self.ddf = DynamicFixture(data_fixture, ignore_fields=['not_required', 'nullable'])
        instance = self.ddf.new(ModelForIgnoreList)
        self.assertNotEquals(None, instance.different_reference.nullable)


class NewAlsoCreatesRelatedObjectsTest(DDFTestCase):
    def test_new_fill_foreignkey_fields(self):
        instance = self.ddf.new(ModelWithRelationships)
        self.assertTrue(isinstance(instance.foreignkey, ModelRelated))

    def test_new_fill_onetoone_fields(self):
        instance = self.ddf.new(ModelWithRelationships)
        self.assertTrue(isinstance(instance.onetoone, ModelRelated))

    def test_new_deal_with_default_values(self):
        instance = self.ddf.new(ModelWithRelationships)
        self.assertTrue(isinstance(instance.foreignkey_with_default, ModelRelated))

#        TODO
#    def test_new_fill_genericrelations_fields(self):
#        instance = self.ddf.new(ModelWithRelationships)
#        self.assertTrue(isinstance(instance.foreignkey, ModelRelated))


class NewCanCreatesCustomizedRelatedObjectsTest(DDFTestCase):
    def test_customizing_nullable_fields_for_related_objects(self):
        instance = self.ddf.new(ModelWithRelationships, selfforeignkey=DynamicFixture(data_fixture, fill_nullable_fields=False))
        self.assertTrue(isinstance(instance.integer, int))
        self.assertEquals(None, instance.selfforeignkey.integer)


class NewDealWithSelfReferencesTest(DDFTestCase):
    def test_new_create_by_default_only_1_lap_in_cycle(self):
        instance = self.ddf.new(ModelWithRelationships)
        self.assertNotEquals(None, instance.selfforeignkey) # 1 cycle
        self.assertEquals(None, instance.selfforeignkey.selfforeignkey) # 2 cycles

    def test_new_create_n_laps_in_cycle(self):
        self.ddf = DynamicFixture(data_fixture, number_of_laps=2)
        instance = self.ddf.new(ModelWithRelationships)
        self.assertNotEquals(None, instance.selfforeignkey) # 1 cycle
        self.assertNotEquals(None, instance.selfforeignkey.selfforeignkey) # 2 cycles
        self.assertEquals(None, instance.selfforeignkey.selfforeignkey.selfforeignkey) # 3 cycles


class GetFullFilledModelInstanceAndPersistTest(DDFTestCase):
    def test_get_create_and_save_a_full_filled_instance_of_the_model(self):
        instance = self.ddf.get(ModelWithRelationships)
        self.assertTrue(isinstance(instance, ModelWithRelationships))
        self.assertNotEquals(None, instance.id)
        # checking unique problems
        another_instance = self.ddf.get(ModelWithRelationships)
        self.assertTrue(isinstance(another_instance, ModelWithRelationships))
        self.assertNotEquals(None, another_instance.id)

    def test_get_create_and_save_related_fields(self):
        instance = self.ddf.get(ModelWithRelationships)
        self.assertNotEquals(None, instance.selfforeignkey)
        self.assertNotEquals(None, instance.foreignkey)
        self.assertNotEquals(None, instance.onetoone)


class ManyToManyRelationshipTest(DDFTestCase):
    def test_new_ignore_many_to_many_configuratios(self):
        instance = self.ddf.new(ModelWithRelationships, manytomany=3)
        instance.save()
        self.assertEquals(0, instance.manytomany.all().count())

    def test_get_ignore_many_to_many_configuratios(self):
        instance = self.ddf.get(ModelWithRelationships, manytomany=3)
        self.assertEquals(3, instance.manytomany.all().count())

    def test_many_to_many_configuratios_accept_list_of_dynamic_filters(self):
        instance = self.ddf.get(ModelWithRelationships, manytomany=[DynamicFixture(data_fixture, integer=1000), DynamicFixture(data_fixture, integer=1001)])
        self.assertEquals(2, instance.manytomany.all().count())
        self.assertEquals(1000, instance.manytomany.all()[0].integer)
        self.assertEquals(1001, instance.manytomany.all()[1].integer)

    def test_many_to_many_configuratios_accept_list_of_instances(self):
        b1 = self.ddf.get(ModelRelated, integer=1000)
        b2 = self.ddf.get(ModelRelated, integer=1001)
        instance = self.ddf.get(ModelWithRelationships, manytomany=[b1, b2])
        self.assertEquals(2, instance.manytomany.all().count())
        self.assertEquals(1000, instance.manytomany.all()[0].integer)
        self.assertEquals(1001, instance.manytomany.all()[1].integer)

    def test_invalid_many_to_many_configuration(self):
        self.assertRaises(InvalidManyToManyConfigurationError, self.ddf.get, ModelWithRelationships, manytomany='a')

    def test_many_to_many_through(self):
        b1 = self.ddf.get(ModelRelated, integer=1000)
        b2 = self.ddf.get(ModelRelated, integer=1001)
        instance = self.ddf.get(ModelWithRelationships, manytomany_through=[b1, b2])
        self.assertEquals(2, instance.manytomany_through.all().count())
        self.assertEquals(1000, instance.manytomany_through.all()[0].integer)
        self.assertEquals(1001, instance.manytomany_through.all()[1].integer)


class NewDealWithCyclicDependenciesTest(DDFTestCase):
    def test_new_create_by_default_only_1_lap_in_cycle(self):
        c = self.ddf.new(ModelWithCyclicDependency)
        self.assertNotEquals(None, c.d) # 1 cycle
        self.assertEquals(None, c.d.c) # 2 cycles

    def test_new_create_n_laps_in_cycle(self):
        self.ddf = DynamicFixture(data_fixture, number_of_laps=2)
        c = self.ddf.new(ModelWithCyclicDependency)
        self.assertNotEquals(None, c.d)
        self.assertNotEquals(None, c.d.c) # 1 cycle
        self.assertNotEquals(None, c.d.c.d) # 2 cycles
        self.assertEquals(None, c.d.c.d.c) # 3 cycles


class NewDealWithInheritanceTest(DDFTestCase):
    def test_new_must_not_raise_an_error_if_model_is_abstract(self):
        self.ddf.new(ModelAbstract) # it does not raise an exceptions

    def test_get_must_raise_an_error_if_model_is_abstract(self):
        self.assertRaises(InvalidModelError, self.ddf.get, ModelAbstract)

    def test_get_must_fill_parent_fields_too(self):
        instance = self.ddf.get(ModelParent)
        self.assertTrue(isinstance(instance.integer, int))
        self.assertEquals(1, ModelParent.objects.count())

    def test_get_must_fill_grandparent_fields_too(self):
        instance = self.ddf.get(ModelChild)
        self.assertTrue(isinstance(instance.integer, int))
        self.assertEquals(1, ModelParent.objects.count())
        self.assertEquals(1, ModelChild.objects.count())

    def test_get_must_ignore_parent_link_attributes_but_the_parent_object_must_be_created(self):
        instance = self.ddf.get(ModelChildWithCustomParentLink)
        self.assertTrue(isinstance(instance.integer, int))
        self.assertEquals(1, instance.my_custom_ref.id)
        self.assertEquals(1, ModelParent.objects.count())
        self.assertEquals(1, ModelChildWithCustomParentLink.objects.count())

    # TODO: need to check these tests. Here we are trying to simulate a bug with parent_link attribute
    def test_get_0(self):
        instance = self.ddf.get(ModelWithRefToParent)
        self.assertEquals(1, ModelWithRefToParent.objects.count())
        self.assertEquals(1, ModelParent.objects.count())
        self.assertTrue(isinstance(instance.parent, ModelParent))

    def test_get_1(self):
        instance = self.ddf.get(ModelWithRefToParent, parent=self.ddf.get(ModelChild))
        self.assertEquals(1, ModelWithRefToParent.objects.count())
        self.assertEquals(1, ModelParent.objects.count())
        self.assertEquals(1, ModelChild.objects.count())
        self.assertTrue(isinstance(instance.parent, ModelChild))

    def test_get_2(self):
        instance = self.ddf.get(ModelWithRefToParent, parent=self.ddf.get(ModelChildWithCustomParentLink))
        self.assertEquals(1, ModelWithRefToParent.objects.count())
        self.assertEquals(1, ModelParent.objects.count())
        self.assertEquals(1, ModelChildWithCustomParentLink.objects.count())
        self.assertTrue(isinstance(instance.parent, ModelChildWithCustomParentLink))


class CustomFieldsTest(DDFTestCase):
    def test_new_field_that_extends_django_field_must_be_supported(self):
        instance = self.ddf.new(ModelWithCustomFields)
        self.assertEquals(1, instance.x)

    def test_unsupported_field_is_filled_with_null_if_it_is_possible(self):
        instance = self.ddf.new(ModelWithCustomFields)
        self.assertEquals(None, instance.y)

    def test_unsupported_field_raise_an_error_if_it_does_not_accept_null_value(self):
        self.assertRaises(UnsupportedFieldError, self.ddf.new, ModelWithUnsupportedField)

    def test_new_field_that_double_inherits_django_field_must_be_supported(self):
        instance = self.ddf.new(ModelWithCustomFieldsMultipleInheritance)
        self.assertEquals(1, instance.x)


class ModelValidatorsTest(DDFTestCase):
    def test_it_must_create_if_validation_is_disabled(self):
        instance = self.ddf.get(ModelWithValidators, field_validator='nok', clean_validator='nok')
        self.ddf.validate_models = False
        self.assertEquals('nok', instance.field_validator)
        self.assertEquals('nok', instance.clean_validator)

    def test_it_must_create_if_there_is_no_validation_errors(self):
        instance = self.ddf.get(ModelWithValidators, field_validator='ok', clean_validator='ok')
        self.ddf.validate_models = True
        self.assertEquals('ok', instance.field_validator)
        self.assertEquals('ok', instance.clean_validator)

    def test_it_must_raise_a_bad_data_error_if_data_is_not_valid(self):
        self.ddf.validate_models = True
        self.ddf.get(ModelWithValidators, field_validator='nok', clean_validator='ok')
        self.assertRaises(BadDataError, self.ddf.get, ModelWithValidators, field_validator='ok', clean_validator='nok')


class ConfigurationValidatorTest(DDFTestCase):
    def test_it_must_raise_a_bad_data_error_if_data_is_not_valid(self):
        self.ddf.validate_args = True
        self.assertRaises(InvalidConfigurationError, self.ddf.get, EmptyModel, unexistent_field='x')


class DisableAutoGeneratedDateTimesTest(DDFTestCase):
    def test_auto_generated_datetimes_must_be_respected_if_nothing_is_specified(self):
        instance = self.ddf.get(ModelWithAutoDateTimes)
        self.assertEquals(datetime.today().date(), instance.auto_now_add)
        self.assertEquals(datetime.today().date(), instance.auto_now)

    def test_it_must_ignore_auto_generated_datetime_if_a_custom_value_is_provided(self):
        instance = self.ddf.get(ModelWithAutoDateTimes, auto_now_add=date(2000, 12, 31))
        self.assertEquals(date(2000, 12, 31), instance.auto_now_add)

        instance = self.ddf.get(ModelWithAutoDateTimes, auto_now=date(2000, 12, 31))
        self.assertEquals(date(2000, 12, 31), instance.auto_now)

    def test_checking_if_implementation_works_for_m2m_fields_too(self):
        instance = self.ddf.get(ModelWithAutoDateTimes, manytomany=[DynamicFixture(data_fixture, auto_now_add=date(2000, 12, 31))])
        self.assertEquals(date(2000, 12, 31), instance.manytomany.all()[0].auto_now_add)

        instance = self.ddf.get(ModelWithAutoDateTimes, manytomany=[DynamicFixture(data_fixture, auto_now=date(2000, 12, 31))])
        self.assertEquals(date(2000, 12, 31), instance.manytomany.all()[0].auto_now)



class CopyTest(DDFTestCase):
    def test_it_should_copy_from_model_fields(self):
        instance = self.ddf.get(ModelForCopy, int_a=Copier('int_b'), int_b=3)
        self.assertEquals(3, instance.int_a)

    def test_simple_scenario(self):
        instance = self.ddf.get(ModelForCopy, int_b=Copier('int_a'))
        self.assertEquals(instance.int_b, instance.int_a)

    def test_order_of_attributes_must_be_superfluous(self):
        instance = self.ddf.get(ModelForCopy, int_a=Copier('int_b'))
        self.assertEquals(instance.int_a, instance.int_b)

    def test_it_should_deal_with_multiple_copiers(self):
        instance = self.ddf.get(ModelForCopy, int_a=Copier('int_b'), int_c=Copier('int_d'))
        self.assertEquals(instance.int_a, instance.int_b)
        self.assertEquals(instance.int_c, instance.int_d)

    def test_multiple_copiers_can_depend_of_one_field(self):
        instance = self.ddf.get(ModelForCopy, int_a=Copier('int_c'), int_b=Copier('int_c'))
        self.assertEquals(instance.int_a, instance.int_c)
        self.assertEquals(instance.int_b, instance.int_c)

    def test_it_should_deal_with_dependent_copiers(self):
        instance = self.ddf.get(ModelForCopy, int_a=Copier('int_b'), int_b=Copier('int_c'))
        self.assertEquals(instance.int_a, instance.int_b)
        self.assertEquals(instance.int_b, instance.int_c)

    def test_it_should_deal_with_relationships(self):
        instance = self.ddf.get(ModelForCopy, int_a=Copier('e.int_e'))
        self.assertEquals(instance.int_a, instance.e.int_e)

        instance = self.ddf.get(ModelForCopy, int_a=Copier('e.int_e'), e=DynamicFixture(data_fixture, int_e=5))
        self.assertEquals(5, instance.int_a)

    def test_it_should_raise_a_bad_data_error_if_value_is_invalid(self):
        self.assertRaises(BadDataError, self.ddf.get, ModelForCopy, int_a=Copier('int_b'), int_b=None)

    def test_it_should_raise_a_invalid_configuration_error_if_expression_is_bugged(self):
        self.assertRaises(InvalidConfigurationError, self.ddf.get, ModelForCopy, int_a=Copier('invalid_field'))
        self.assertRaises(InvalidConfigurationError, self.ddf.get, ModelForCopy, int_a=Copier('int_b.invalid_field'))

    def test_it_should_raise_a_invalid_configuration_error_if_copier_has_cyclic_dependency(self):
        self.assertRaises(InvalidConfigurationError, self.ddf.get, ModelForCopy, int_a=Copier('int_b'), int_b=Copier('int_a'))


class ShelveAndLibraryTest(DDFTestCase):
    def test_shelve_store_the_current_configuration_as_default_configuration(self):
        self.ddf.use_library = False
        instance = self.ddf.get(ModelForLibrary, integer=1000, shelve=True)
        self.assertEquals(1000, instance.integer)
        self.ddf.use_library = True
        instance = self.ddf.get(ModelForLibrary)
        self.assertEquals(1000, instance.integer)

    def test_do_not_use_library_if_the_programmer_do_not_want_to(self):
        self.ddf.use_library = False
        self.ddf.get(ModelForLibrary, integer=1000, shelve=True)
        self.ddf.use_library = False
        instance = self.ddf.get(ModelForLibrary)
        self.assertNotEquals(1000, instance.integer)

    def test_shelve_may_be_overrided(self):
        self.ddf.use_library = False
        self.ddf.get(ModelForLibrary, integer=1000, shelve=True)
        self.ddf.get(ModelForLibrary, integer=1001, shelve=True)
        self.ddf.use_library = True
        instance = self.ddf.get(ModelForLibrary)
        self.assertEquals(1001, instance.integer)

    def test_it_must_NOT_raise_an_error_if_user_try_to_use_a_not_saved_default_configuration(self):
        self.ddf.use_library = True
        self.ddf.get(ModelForLibrary)

    def test_it_must_raise_an_error_if_try_to_set_a_static_value_to_a_field_with_unicity(self):
        self.assertRaises(InvalidConfigurationError, self.ddf.get, ModelForLibrary, integer_unique=1000, shelve=True)

    def test_it_must_accept_dynamic_values_for_fields_with_unicity(self):
        self.ddf.get(ModelForLibrary, integer_unique=lambda field: 1000, shelve=True)

    def test_it_must_NOT_propagate_shelve_for_internal_dependencies(self):
        self.ddf.get(ModelForLibrary, foreignkey=DynamicFixture(data_fixture, integer=1000), shelve=True)
        instance = self.ddf.get(ModelForLibrary2)
        self.assertNotEquals(1000, instance.integer)

    def test_it_must_propagate_use_library_for_internal_dependencies(self):
        self.ddf.use_library = True
        self.ddf.get(ModelForLibrary, integer=1000, shelve=True)
        self.ddf.get(ModelForLibrary2, integer=1000, shelve=True)
        instance = self.ddf.get(ModelForLibrary)
        self.assertEquals(1000, instance.foreignkey.integer)

#    def test_shelve_must_store_ddf_configs_too(self):
#        self.ddf.use_library = True
#        self.ddf.fill_nullable_fields = False
#        self.ddf.get(ModelForLibrary, shelve=True)
#        self.ddf.fill_nullable_fields = True
#        instance = self.ddf.get(ModelForLibrary)
#        self.assertEquals(None, instance.integer)
#
#    def test_shelved_ddf_configs_must_NOT_be_propagated_to_another_models(self):
#        self.ddf.use_library = True
#        self.ddf.fill_nullable_fields = False
#        self.ddf.get(ModelForLibrary, shelve=True)
#        self.ddf.fill_nullable_fields = True
#        instance = self.ddf.get(ModelForLibrary)
#        self.assertEquals(None, instance.integer)
#        self.assertEquals(None, instance.foreignkey.integer)


class NamedShelveAndLibraryTest(DDFTestCase):
    def test_a_model_can_have_named_configurations(self):
        self.ddf.use_library = True
        self.ddf.get(ModelForLibrary, integer=1000, shelve='a name')
        instance = self.ddf.get(ModelForLibrary, named_shelve='a name')
        self.assertEquals(1000, instance.integer)

    def test_named_shelves_must_not_be_used_if_not_explicity_specified(self):
        self.ddf.use_library = True
        self.ddf.get(ModelForLibrary, integer=1000, shelve='a name')
        instance = self.ddf.get(ModelForLibrary)
        self.assertNotEquals(1000, instance.integer)

    def test_use_library_must_be_enable_to_use_named_shelves(self):
        self.ddf.use_library = False
        self.ddf.get(ModelForLibrary, integer=1000, shelve='a name')
        instance = self.ddf.get(ModelForLibrary, named_shelve='a name')
        self.assertNotEquals(1000, instance.integer)

    def test_a_model_can_have_many_named_shelved_configurations(self):
        self.ddf.get(ModelForLibrary, integer=1000, shelve='a name')
        self.ddf.get(ModelForLibrary, integer=1001, shelve='a name 2')

        self.ddf.use_library = True
        instance = self.ddf.get(ModelForLibrary, named_shelve='a name')
        self.assertEquals(1000, instance.integer)

        instance = self.ddf.get(ModelForLibrary, named_shelve='a name 2')
        self.assertEquals(1001, instance.integer)

    def test_it_must_raise_an_error_if_user_try_to_use_a_not_saved_configuration(self):
        self.ddf.use_library = True
        self.assertRaises(InvalidConfigurationError, self.ddf.get, ModelForLibrary, named_shelve='a name')

    def test_default_shelve_and_named_shelve_must_work_together(self):
        # regression test
        self.ddf.get(ModelForLibrary, integer=1000, shelve='a name')
        self.ddf.get(ModelForLibrary, integer=1001, shelve=True)
        self.ddf.get(ModelForLibrary, integer=1002, shelve='a name2')
        self.ddf.use_library = True
        instance = self.ddf.get(ModelForLibrary, named_shelve='a name')
        self.assertEquals(1000, instance.integer)
        instance = self.ddf.get(ModelForLibrary)
        self.assertEquals(1001, instance.integer)
        instance = self.ddf.get(ModelForLibrary, named_shelve='a name2')
        self.assertEquals(1002, instance.integer)

    def test_default_shelve_and_named_shelve_must_work_together_for_different_models(self):
        # regression test
        self.ddf.get(ModelForLibrary, integer=1000, shelve='a name')
        self.ddf.get(ModelForLibrary, integer=1001, shelve=True)
        self.ddf.get(ModelForLibrary, integer=1002, shelve='a name2')
        self.ddf.get(ModelForLibrary2, integer=2000, shelve='a name')
        self.ddf.get(ModelForLibrary2, integer=2001, shelve=True)
        self.ddf.get(ModelForLibrary2, integer=2002, shelve='a name2')
        self.ddf.use_library = True
        instance = self.ddf.get(ModelForLibrary, named_shelve='a name')
        self.assertEquals(1000, instance.integer)
        instance = self.ddf.get(ModelForLibrary)
        self.assertEquals(1001, instance.integer)
        instance = self.ddf.get(ModelForLibrary, named_shelve='a name2')
        self.assertEquals(1002, instance.integer)

        instance = self.ddf.get(ModelForLibrary2, named_shelve='a name')
        self.assertEquals(2000, instance.integer)
        instance = self.ddf.get(ModelForLibrary2)
        self.assertEquals(2001, instance.integer)
        instance = self.ddf.get(ModelForLibrary2, named_shelve='a name2')
        self.assertEquals(2002, instance.integer)


class DDFLibraryTest(TestCase):
    def setUp(self):
        self.lib = DDFLibrary()

    def test_add_and_get_configuration_without_string_name(self):
        self.lib.add_configuration(ModelForLibrary, {'a': 1})
        self.assertEquals({'a': 1}, self.lib.get_configuration(ModelForLibrary))
        self.assertEquals({'a': 1}, self.lib.get_configuration(ModelForLibrary, name=DDFLibrary.DEFAULT_KEY))
        self.assertEquals({'a': 1}, self.lib.get_configuration(ModelForLibrary, name=None))

        self.lib.add_configuration(ModelForLibrary, {'a': 2}, name=None)
        self.assertEquals({'a': 2}, self.lib.get_configuration(ModelForLibrary))
        self.assertEquals({'a': 2}, self.lib.get_configuration(ModelForLibrary, name=DDFLibrary.DEFAULT_KEY))
        self.assertEquals({'a': 2}, self.lib.get_configuration(ModelForLibrary, name=None))

        self.lib.add_configuration(ModelForLibrary, {'a': 3}, name=True)
        self.assertEquals({'a': 3}, self.lib.get_configuration(ModelForLibrary))
        self.assertEquals({'a': 3}, self.lib.get_configuration(ModelForLibrary, name=DDFLibrary.DEFAULT_KEY))
        self.assertEquals({'a': 3}, self.lib.get_configuration(ModelForLibrary, name=None))

    def test_add_and_get_configuration_with_name(self):
        self.lib.add_configuration(ModelForLibrary, {'a': 1}, name='x')
        self.assertEquals({'a': 1}, self.lib.get_configuration(ModelForLibrary, name='x'))

    def test_clear_config(self):
        self.lib.clear_configuration(ModelForLibrary) # run ok if empty
        self.lib.add_configuration(ModelForLibrary, {'a': 1})
        self.lib.add_configuration(ModelForLibrary, {'a': 2}, name='x')
        self.lib.add_configuration(ModelForLibrary2, {'a': 3})
        self.lib.clear_configuration(ModelForLibrary)
        self.assertEquals({}, self.lib.get_configuration(ModelForLibrary))
        self.assertRaises(Exception, self.lib.get_configuration, ModelForLibrary, name='x')
        self.assertEquals({'a': 3}, self.lib.get_configuration(ModelForLibrary2))

    def test_clear(self):
        self.lib.add_configuration(ModelForLibrary, {'a': 1})
        self.lib.add_configuration(ModelForLibrary, {'a': 2}, name='x')
        self.lib.add_configuration(ModelForLibrary2, {'a': 3})
        self.lib.add_configuration(ModelForLibrary2, {'a': 4}, name='x')
        self.lib.clear()
        self.assertEquals({}, self.lib.get_configuration(ModelForLibrary))
        self.assertRaises(Exception, self.lib.get_configuration, ModelForLibrary, name='x')
        self.assertEquals({}, self.lib.get_configuration(ModelForLibrary2))
        self.assertRaises(Exception, self.lib.get_configuration, ModelForLibrary2, name='x')


class ModelWithCustomValidationTest(DDFTestCase):
    def test_ddf_can_not_create_instance_of_models_with_custom_validations(self):
        self.ddf.validate_models = True
        self.assertRaises(BadDataError, self.ddf.get, ModelWithClean)
        self.ddf.get(ModelWithClean, integer=9999) # this does not raise an exception


class PreSaveTest(DDFTestCase):
    def test_set_pre_save_receiver(self):
        def callback_function(instance):
            pass
        set_pre_save_receiver(ModelForSignals, callback_function)
        callback_function = lambda x: x
        set_pre_save_receiver(ModelForSignals, callback_function)

    def test_pre_save_receiver_must_raise_an_error_if_first_parameter_is_not_a_model_class(self):
        callback_function = lambda x: x
        self.assertRaises(InvalidReceiverError, set_pre_save_receiver, str, callback_function)

    def test_pre_save_receiver_must_raise_an_error_if_it_is_not_a_function(self):
        self.assertRaises(InvalidReceiverError, set_pre_save_receiver, ModelForSignals, '')

    def test_pre_save_receiver_must_raise_an_error_if_it_is_not_an_only_one_argument_function(self):
        callback_function = lambda x, y: x
        self.assertRaises(InvalidReceiverError, set_pre_save_receiver, ModelForSignals, callback_function)

    def test_pre_save_receiver_must_be_executed_before_saving(self):
        def callback_function(instance):
            if instance.id is not None:
                raise Exception('ops, instance already saved')
            self.ddf.get(ModelForSignals2)
        set_pre_save_receiver(ModelForSignals, callback_function)
        self.ddf.get(ModelForSignals)
        self.assertEquals(1, ModelForSignals2.objects.count())

    def test_bugged_pre_save_receiver_must_raise_an_error(self):
        def callback_function(instance):
            raise Exception('ops')
        set_pre_save_receiver(ModelForSignals, callback_function)
        self.assertRaises(BadDataError, self.ddf.get, ModelForSignals)


class PostSaveTest(DDFTestCase):
    def test_set_post_save_receiver(self):
        def callback_function(instance):
            pass
        set_post_save_receiver(ModelForSignals, callback_function)
        callback_function = lambda x: x
        set_post_save_receiver(ModelForSignals, callback_function)

    def test_post_save_receiver_must_raise_an_error_if_first_parameter_is_not_a_model_class(self):
        callback_function = lambda x: x
        self.assertRaises(InvalidReceiverError, set_post_save_receiver, str, callback_function)

    def test_post_save_receiver_must_raise_an_error_if_it_is_not_a_function(self):
        self.assertRaises(InvalidReceiverError, set_post_save_receiver, ModelForSignals, '')

    def test_post_save_receiver_must_raise_an_error_if_it_is_not_an_only_one_argument_function(self):
        callback_function = lambda x, y: x
        self.assertRaises(InvalidReceiverError, set_post_save_receiver, ModelForSignals, callback_function)

    def test_pre_save_receiver_must_be_executed_before_saving(self):
        def callback_function(instance):
            if instance.id is None:
                raise Exception('ops, instance not saved')
            self.ddf.get(ModelForSignals2)
        set_post_save_receiver(ModelForSignals, callback_function)
        self.ddf.get(ModelForSignals)
        self.assertEquals(1, ModelForSignals2.objects.count())

    def test_bugged_post_save_receiver_must_raise_an_error(self):
        def callback_function(instance):
            raise Exception('ops')
        set_post_save_receiver(ModelForSignals, callback_function)
        self.assertRaises(BadDataError, self.ddf.get, ModelForSignals)


class ExceptionsLayoutMessagesTest(DDFTestCase):
    def test_UnsupportedFieldError(self):
        try:
            self.ddf.new(ModelWithUnsupportedField)
            self.fail()
        except UnsupportedFieldError as e:
            self.assertEquals("""django_dynamic_fixture.models_test.ModelWithUnsupportedField.z""",
                              str(e))

    def test_BadDataError(self):
        self.ddf = DynamicFixture(data_fixture, ignore_fields=['required', 'required_with_default'])
        try:
            self.ddf.get(ModelForIgnoreList)
            self.fail()
        except BadDataError as e:
            self.assertEquals("""('django_dynamic_fixture.models_test.ModelForIgnoreList', IntegrityError('django_dynamic_fixture_modelforignorelist.required may not be NULL',))""",
                              str(e))

    def test_InvalidConfigurationError(self):
        try:
            self.ddf.new(ModelWithNumbers, integer=lambda x: ''.invalidmethod())
            self.fail()
        except InvalidConfigurationError as e:
            self.assertEquals("""('django_dynamic_fixture.models_test.ModelWithNumbers.integer', AttributeError("'str' object has no attribute 'invalidmethod'",))""",
                              str(e))

    def test_InvalidManyToManyConfigurationError(self):
        try:
            self.ddf.get(ModelWithRelationships, manytomany='a')
            self.fail()
        except InvalidManyToManyConfigurationError as e:
            self.assertEquals("""('Field: manytomany', 'a')""",
                              str(e))

    def test_InvalidModelError(self):
        try:
            self.ddf.get(ModelAbstract)
            self.fail()
        except InvalidModelError as e:
            self.assertEquals("""django_dynamic_fixture.models_test.ModelAbstract""",
                              str(e))

    def test_InvalidModelError_for_common_object(self):
        class MyClass(object): pass
        try:
            self.ddf.new(MyClass)
            self.fail()
        except InvalidModelError as e:
            self.assertEquals("""django_dynamic_fixture.tests.test_ddf.MyClass""",
                              str(e))


class SanityTest(DDFTestCase):
    def test_create_lots_of_models_to_verify_data_unicity_errors(self):
        for i in range(1000):
            self.ddf.get(ModelWithNumbers)

########NEW FILE########
__FILENAME__ = test_decorators
# -*- coding: utf-8 -*-
from unittest import TestCase

from django.conf import settings

from django_dynamic_fixture import decorators


class SkipForDatabaseTest(TestCase):
    def setUp(self):
        self.it_was_executed = False

    def tearDown(self):
        # It is important to do not break others tests: global and shared variable
        decorators.DATABASE_ENGINE = settings.DATABASES['default']['ENGINE']

    @decorators.only_for_database(decorators.POSTGRES)
    def method_postgres(self):
        self.it_was_executed = True

    def test_annotated_method_only_for_postgres(self):
        decorators.DATABASE_ENGINE = decorators.SQLITE3
        self.method_postgres()
        self.assertEquals(False, self.it_was_executed)

        decorators.DATABASE_ENGINE = decorators.POSTGRES
        self.method_postgres()
        self.assertEquals(True, self.it_was_executed)


class OnlyForDatabaseTest(TestCase):
    def setUp(self):
        self.it_was_executed = False

    def tearDown(self):
        # It is important to do not break others tests: global and shared variable
        decorators.DATABASE_ENGINE = settings.DATABASES['default']['ENGINE']

    @decorators.skip_for_database(decorators.SQLITE3)
    def method_sqlite3(self):
        self.it_was_executed = True

    def test_annotated_method_skip_for_sqlite3(self):
        decorators.DATABASE_ENGINE = decorators.SQLITE3
        self.method_sqlite3()
        self.assertEquals(False, self.it_was_executed)

        decorators.DATABASE_ENGINE = decorators.POSTGRES
        self.method_sqlite3()
        self.assertEquals(True, self.it_was_executed)

########NEW FILE########
__FILENAME__ = test_django_helper
# -*- coding: utf-8 -*-

from django.test import TestCase
from django.db import models

from django_dynamic_fixture import N, G
from django_dynamic_fixture.models_test import *
from django_dynamic_fixture.django_helper import *


class DjangoHelperAppsTest(TestCase):
    def test_get_apps_must_return_all_installed_apps(self):
        self.assertEquals(1, len(get_apps()))

    def test_get_apps_may_be_filtered_by_app_names(self):
        self.assertEquals(1, len(get_apps(application_labels=['django_dynamic_fixture'])))

    def test_get_apps_may_ignore_some_apps(self):
        self.assertEquals(0, len(get_apps(exclude_application_labels=['django_dynamic_fixture'])))

    def test_app_name_must_be_valid(self):
        self.assertRaises(Exception, get_apps, application_labels=['x'])
        self.assertRaises(Exception, get_apps, exclude_application_labels=['x'])

    def test_get_app_name_must(self):
        self.assertEquals('django_dynamic_fixture', get_app_name(get_apps()[0]))

    def test_get_models_of_an_app_must(self):
        models_ddf = get_models_of_an_app(get_apps()[0])
        self.assertTrue(len(models_ddf) > 0)
        self.assertTrue(ModelWithNumbers in models_ddf)


class DjangoHelperModelsTest(TestCase):
    def test_get_model_name(self):
        class MyModel_test_get_model_name(models.Model): pass
        self.assertEquals('MyModel_test_get_model_name', get_model_name(MyModel_test_get_model_name))

    def test_get_unique_model_name(self):
        class MyModel_test_get_unique_model_name(models.Model): pass
        self.assertEquals('django_dynamic_fixture.tests.test_django_helper.MyModel_test_get_unique_model_name',
                          get_unique_model_name(MyModel_test_get_unique_model_name))

    def test_get_fields_from_model(self):
        class Model4GetFields_test_get_fields_from_model(models.Model):
            integer = models.IntegerField()
        fields = get_fields_from_model(Model4GetFields_test_get_fields_from_model)
        self.assertTrue(get_field_by_name_or_raise(Model4GetFields_test_get_fields_from_model, 'id') in fields)
        self.assertTrue(get_field_by_name_or_raise(Model4GetFields_test_get_fields_from_model, 'integer') in fields)

    def test_get_local_fields(self):
        class ModelForGetLocalFields_test_get_local_fields(models.Model):
            integer = models.IntegerField()
        fields = get_local_fields(ModelForGetLocalFields_test_get_local_fields)
        self.assertTrue(get_field_by_name_or_raise(ModelForGetLocalFields_test_get_local_fields, 'id') in fields)
        self.assertTrue(get_field_by_name_or_raise(ModelForGetLocalFields_test_get_local_fields, 'integer') in fields)

    def test_get_field_names_of_model(self):
        class Model4GetFieldNames_test_get_field_names_of_model(models.Model):
            smallinteger = models.SmallIntegerField()
        fields = get_field_names_of_model(Model4GetFieldNames_test_get_field_names_of_model)
        self.assertTrue('smallinteger' in fields)
        self.assertTrue('unknown' not in fields)

    def test_get_many_to_many_fields_from_model(self):
        class ModelRelated_test_get_many_to_many_fields_from_model(models.Model): pass
        class ModelWithM2M_test_get_many_to_many_fields_from_model(models.Model):
            manytomany = models.ManyToManyField('ModelRelated_test_get_many_to_many_fields_from_model', related_name='m2m')
        fields = get_many_to_many_fields_from_model(ModelWithM2M_test_get_many_to_many_fields_from_model)
        self.assertTrue(get_field_by_name_or_raise(ModelWithM2M_test_get_many_to_many_fields_from_model, 'manytomany') in fields)
        self.assertTrue(get_field_by_name_or_raise(ModelWithM2M_test_get_many_to_many_fields_from_model, 'id') not in fields)

    def test_is_model_class(self):
        class MyModel_test_is_model_class(models.Model): pass
        self.assertEquals(True, is_model_class(MyModel_test_is_model_class))
        class X(object): pass
        self.assertEquals(False, is_model_class(X))

    def test_is_model_abstract(self):
        class AbstractModel_test_is_model_abstract(models.Model):
            class Meta:
                abstract = True
        self.assertEquals(True, is_model_abstract(AbstractModel_test_is_model_abstract))

        class ConcreteModel_test_is_model_abstract(models.Model):
            class Meta:
                abstract = False
        self.assertEquals(False, is_model_abstract(ConcreteModel_test_is_model_abstract))

    def test_is_model_managed(self):
        class NotManagedModel_test_is_model_managed(models.Model):
            class Meta:
                managed = False
        self.assertEquals(False, is_model_managed(NotManagedModel_test_is_model_managed))

        class ManagedModel_test_is_model_managed(models.Model):
            class Meta:
                managed = True
        self.assertEquals(True, is_model_managed(ManagedModel_test_is_model_managed))

    def test_model_has_the_field(self):
        class ModelWithWithoutFields_test_model_has_the_field(models.Model):
            integer = models.IntegerField()
            selfforeignkey = models.ForeignKey('self', null=True)
            manytomany = models.ManyToManyField('self', related_name='m2m')
        self.assertEquals(True, model_has_the_field(ModelWithWithoutFields_test_model_has_the_field, 'integer'))
        self.assertEquals(True, model_has_the_field(ModelWithWithoutFields_test_model_has_the_field, 'selfforeignkey'))
        self.assertEquals(True, model_has_the_field(ModelWithWithoutFields_test_model_has_the_field, 'manytomany'))
        self.assertEquals(False, model_has_the_field(ModelWithWithoutFields_test_model_has_the_field, 'x'))


class DjangoHelperFieldsTest(TestCase):
    def test_get_unique_field_name(self):
        class Model4GetUniqueFieldName_test_get_unique_field_name(models.Model):
            integer = models.IntegerField()
        field = get_field_by_name_or_raise(Model4GetUniqueFieldName_test_get_unique_field_name, 'integer')
        self.assertEquals('django_dynamic_fixture.tests.test_django_helper.Model4GetUniqueFieldName_test_get_unique_field_name.integer', get_unique_field_name(field))

    def test_get_related_model(self):
        class ModelRelated_test_get_related_model(models.Model): pass
        class Model4GetRelatedModel_test_get_related_model(models.Model):
            fk = models.ForeignKey(ModelRelated_test_get_related_model)
        self.assertEquals(ModelRelated_test_get_related_model,
                          get_related_model(get_field_by_name_or_raise(Model4GetRelatedModel_test_get_related_model, 'fk')))

    def test_field_is_a_parent_link(self):
        class ModelParent_test_get_related_model(models.Model): pass
        class Model4FieldIsParentLink_test_get_related_model(ModelParent):
            o2o_with_parent_link = models.OneToOneField(ModelParent_test_get_related_model, parent_link=True, related_name='my_custom_ref_x')
        class Model4FieldIsParentLink2(ModelParent):
            o2o_without_parent_link = models.OneToOneField(ModelParent_test_get_related_model, parent_link=False, related_name='my_custom_ref_y')
        # FIXME
        #self.assertEquals(True, field_is_a_parent_link(get_field_by_name_or_raise(Model4FieldIsParentLink, 'o2o_with_parent_link')))
        self.assertEquals(False, field_is_a_parent_link(get_field_by_name_or_raise(Model4FieldIsParentLink2, 'o2o_without_parent_link')))

    def test_field_has_choices(self):
        class Model4FieldHasChoices_test_get_related_model(models.Model):
            with_choices = models.IntegerField(choices=((1, 1), (2, 2)))
            without_choices = models.IntegerField()
        self.assertEquals(True, field_has_choices(get_field_by_name_or_raise(Model4FieldHasChoices_test_get_related_model, 'with_choices')))
        self.assertEquals(False, field_has_choices(get_field_by_name_or_raise(Model4FieldHasChoices_test_get_related_model, 'without_choices')))

    def test_field_has_default_value(self):
        class Model4FieldHasDefault_test_field_has_default_value(models.Model):
            with_default = models.IntegerField(default=1)
            without_default = models.IntegerField()
        self.assertEquals(True, field_has_default_value(get_field_by_name_or_raise(Model4FieldHasDefault_test_field_has_default_value, 'with_default')))
        self.assertEquals(False, field_has_default_value(get_field_by_name_or_raise(Model4FieldHasDefault_test_field_has_default_value, 'without_default')))

    def test_field_is_unique(self):
        class Model4FieldMustBeUnique_test_field_is_unique(models.Model):
            unique = models.IntegerField(unique=True)
            not_unique = models.IntegerField()
        self.assertEquals(True, field_is_unique(get_field_by_name_or_raise(Model4FieldMustBeUnique_test_field_is_unique, 'unique')))
        self.assertEquals(False, field_is_unique(get_field_by_name_or_raise(Model4FieldMustBeUnique_test_field_is_unique, 'not_unique')))

    def test_is_key_field(self):
        class ModelForKeyField_test_is_key_field(models.Model):
            integer = models.IntegerField()
        self.assertEquals(True, is_key_field(get_field_by_name_or_raise(ModelForKeyField_test_is_key_field, 'id')))
        self.assertEquals(False, is_key_field(get_field_by_name_or_raise(ModelForKeyField_test_is_key_field, 'integer')))

    def test_is_relationship_field(self):
        class ModelForRelationshipField_test_is_relationship_field(models.Model):
            fk = models.ForeignKey('self')
            one2one = models.OneToOneField('self')
        self.assertEquals(True, is_relationship_field(get_field_by_name_or_raise(ModelForRelationshipField_test_is_relationship_field, 'fk')))
        self.assertEquals(True, is_relationship_field(get_field_by_name_or_raise(ModelForRelationshipField_test_is_relationship_field, 'one2one')))
        self.assertEquals(False, is_relationship_field(get_field_by_name_or_raise(ModelForRelationshipField_test_is_relationship_field, 'id')))

    def test_is_file_field(self):
        class ModelForFileField_test_is_file_field(models.Model):
            filefield = models.FileField()
        self.assertEquals(True, is_file_field(get_field_by_name_or_raise(ModelForFileField_test_is_file_field, 'filefield')))
        self.assertEquals(False, is_file_field(get_field_by_name_or_raise(ModelForFileField_test_is_file_field, 'id')))


class PrintFieldValuesTest(TestCase):
    def test_model_not_saved_do_not_raise_an_exception(self):
        instance = N(ModelWithNumbers)
        print_field_values(instance)

    def test_model_saved_do_not_raise_an_exception(self):
        instance = G(ModelWithNumbers)
        print_field_values(instance)

    def test_print_accept_list_of_models_too(self):
        instances = G(ModelWithNumbers, n=2)
        print_field_values(instances)
        print_field_values([G(ModelWithNumbers), G(ModelWithNumbers)])

    def test_print_accept_a_queryset_too(self):
        G(ModelWithNumbers, n=2)
        print_field_values(ModelWithNumbers.objects.all())


########NEW FILE########
__FILENAME__ = test_fdf
# -*- coding: utf-8 -*-
from django_dynamic_fixture.fdf import *
from django.core.files import File


class FileSystemDjangoTestCaseDealWithDirectoriesTest(FileSystemDjangoTestCase):

    def test_create_temp_directory_must_create_an_empty_directory(self):
        directory = self.create_temp_directory()
        self.assertDirectoryExists(directory)
        self.assertNumberOfFiles(directory, 0)

    def test_remove_temp_directory(self):
        directory = self.create_temp_directory()
        self.remove_temp_directory(directory)
        self.assertDirectoryDoesNotExists(directory)

    def test_remove_temp_directory_must_remove_directories_created_out_of_the_testcase_too(self):
        directory = tempfile.mkdtemp()
        self.remove_temp_directory(directory)
        self.assertDirectoryDoesNotExists(directory)

    def test_remove_temp_directory_must_remove_their_files_too(self):
        directory = self.create_temp_directory()
        self.create_temp_file_with_name(directory, 'x.txt')
        self.remove_temp_directory(directory)
        self.assertDirectoryDoesNotExists(directory)


class FileSystemDjangoTestCaseDealWithTemporaryFilesTest(FileSystemDjangoTestCase):

    def test_create_temp_file_must_create_a_temporary_file_in_an_arbitrary_directory(self):
        filepath = self.create_temp_file()
        self.assertFileExists(filepath)

        directory = self.get_directory_of_the_file(filepath)
        filename = self.get_filename(filepath)
        self.assertDirectoryContainsFile(directory, filename)

    def test_create_temp_file_must_create_an_empty_temporary_file(self):
        filepath = self.create_temp_file()
        self.assertEquals('', self.get_content_of_file(filepath))

    def test_create_temp_file_must_is_ready_to_add_content_to_it(self):
        filepath = self.create_temp_file()
        self.add_text_to_file(filepath, 'abc')
        self.assertEquals('abc', self.get_content_of_file(filepath))


class FileSystemDjangoTestCaseDealWithSpecificTemporaryFilesTest(FileSystemDjangoTestCase):

    def test_create_temp_file_with_name_must_create_a_file_in_an_specific_directory_with_an_specific_name(self):
        directory = self.create_temp_directory()
        filepath = self.create_temp_file_with_name(directory, 'x.txt')
        self.assertFileExists(filepath)

        self.assertEquals(directory, self.get_directory_of_the_file(filepath))
        self.assertEquals('x.txt', self.get_filename(filepath))
        self.assertDirectoryContainsFile(directory, self.get_filename(filepath))
        self.assertNumberOfFiles(directory, 1)

    def test_create_temp_file_with_name_must_create_an_empty_file(self):
        directory = self.create_temp_directory()
        filepath = self.create_temp_file_with_name(directory, 'x.txt')
        self.assertEquals('', self.get_content_of_file(filepath))

    def test_create_temp_file_with_name_is_ready_to_add_content_to_it(self):
        directory = self.create_temp_directory()
        filepath = self.create_temp_file_with_name(directory, 'x.txt')
        self.add_text_to_file(filepath, 'abc')
        self.assertEquals('abc', self.get_content_of_file(filepath))


class FileSystemDjangoTestCaseCanRenameFilesTest(FileSystemDjangoTestCase):

    def test_rename_file_must_preserve_the_directory(self):
        directory = self.create_temp_directory()
        old_filepath = self.create_temp_file_with_name(directory, 'x.txt')
        old_filename = self.get_filename(old_filepath)

        new_filepath = self.rename_temp_file(old_filepath, 'y.txt')
        self.assertFileExists(new_filepath)
        self.assertFileDoesNotExists(old_filepath)

        new_filename = self.get_filename(new_filepath)
        self.assertDirectoryContainsFile(directory, new_filename)
        self.assertDirectoryDoesNotContainsFile(directory, old_filename)

    def test_rename_file_must_preserve_the_file_content(self):
        directory = self.create_temp_directory()
        old_filepath = self.create_temp_file_with_name(directory, 'x.txt')
        self.add_text_to_file(old_filepath, 'abc')

        new_filepath = self.rename_temp_file(old_filepath, 'y.txt')

        self.assertEquals('abc', self.get_content_of_file(new_filepath))


class FileSystemDjangoTestCaseCanRemoveFilesTest(FileSystemDjangoTestCase):

    def test_remove_file(self):
        filepath = self.create_temp_file()
        self.remove_temp_file(filepath)
        self.assertFileDoesNotExists(filepath)

    def test_remove_file_must_remove_files_with_custom_name_too(self):
        directory = self.create_temp_directory()
        filepath = self.create_temp_file_with_name(directory, 'x.txt')
        self.remove_temp_file(filepath)
        self.assertFileDoesNotExists(filepath)

    def test_remove_file_must_remove_files_with_data_too(self):
        filepath = self.create_temp_file()
        self.add_text_to_file(filepath, 'abc')
        self.remove_temp_file(filepath)
        self.assertFileDoesNotExists(filepath)


class FileSystemDjangoTestCaseCanCopyFilesTest(FileSystemDjangoTestCase):

    def test_copy_file_to_dir_must_not_remove_original_file(self):
        directory = self.create_temp_directory()
        filepath = self.create_temp_file()

        new_filepath = self.copy_file_to_dir(filepath, directory)

        self.assertFileExists(new_filepath)
        self.assertFileExists(filepath)

    def test_copy_file_to_dir_must_preserve_file_content(self):
        directory = self.create_temp_directory()
        filepath = self.create_temp_file()
        self.add_text_to_file(filepath, 'abc')

        new_filepath = self.copy_file_to_dir(filepath, directory)
        self.assertEquals('abc', self.get_content_of_file(new_filepath))


class FileSystemDjangoTestCaseDealWithDjangoFileFieldTest(FileSystemDjangoTestCase):

    def test_django_file_must_create_a_django_file_object(self):
        django_file = self.create_django_file_with_temp_file('x.txt')
        self.assertTrue(isinstance(django_file, File))
        self.assertEquals('x.txt', django_file.name)

    def test_django_file_must_create_a_temporary_file_ready_to_add_content(self):
        django_file = self.create_django_file_with_temp_file('x.txt')
        filepath = django_file.file.name

        self.add_text_to_file(filepath, 'abc')

        self.assertEquals('abc', self.get_content_of_file(filepath))


class FileSystemDjangoTestCaseTearDownTest(FileSystemDjangoTestCase):

    def test_teardown_must_delete_all_created_files_in_tests(self):
        directory = self.create_temp_directory()
        filepath1 = self.create_temp_file()
        filepath2 = self.create_temp_file_with_name(directory, 'x.txt')

        self.fdf_teardown()

        self.assertFileDoesNotExists(filepath1)
        self.assertFileDoesNotExists(filepath2)

    def test_teardown_must_delete_files_with_content_too(self):
        filepath = self.create_temp_file()
        self.add_text_to_file(filepath, 'abc')

        self.fdf_teardown()

        self.assertFileDoesNotExists(filepath)

    def test_teardown_must_delete_all_created_directories_in_tests(self):
        directory = self.create_temp_directory()

        self.fdf_teardown()

        self.assertDirectoryDoesNotExists(directory)


class FileSystemDjangoTestCaseTearDownFrameworkConfigurationTest(FileSystemDjangoTestCase):

    def tearDown(self):
        super(FileSystemDjangoTestCaseTearDownFrameworkConfigurationTest, self).tearDown()

        self.assertFileDoesNotExists(self.filepath1)
        self.assertFileDoesNotExists(self.filepath2)
        self.assertDirectoryDoesNotExists(self.directory)

    def test_creating_directory_and_files_for_the_testcase(self):
        self.directory = self.create_temp_directory()
        self.filepath1 = self.create_temp_file()
        self.filepath2 = self.create_temp_file_with_name(self.directory, 'x.txt')

########NEW FILE########
__FILENAME__ = test_global_settings
# -*- coding: utf-8 -*-

from django import conf

from django.test import TestCase

from django_dynamic_fixture import global_settings
from django_dynamic_fixture.fixture_algorithms.sequential_fixture import SequentialDataFixture, \
    StaticSequentialDataFixture
from django_dynamic_fixture.fixture_algorithms.random_fixture import RandomDataFixture
from six.moves import reload_module


class AbstractGlobalSettingsTestCase(TestCase):
    def tearDown(self):
        if hasattr(conf.settings, 'DDF_DEFAULT_DATA_FIXTURE'): del conf.settings.DDF_DEFAULT_DATA_FIXTURE
        if hasattr(conf.settings, 'DDF_FILL_NULLABLE_FIELDS'): del conf.settings.DDF_FILL_NULLABLE_FIELDS
        if hasattr(conf.settings, 'DDF_IGNORE_FIELDS'): del conf.settings.DDF_IGNORE_FIELDS
        if hasattr(conf.settings, 'DDF_NUMBER_OF_LAPS'): del conf.settings.DDF_NUMBER_OF_LAPS
        if hasattr(conf.settings, 'DDF_VALIDATE_MODELS'): del conf.settings.DDF_VALIDATE_MODELS
        reload_module(conf)


class CustomDataFixture(object): pass

class DDF_DEFAULT_DATA_FIXTURE_TestCase(AbstractGlobalSettingsTestCase):
    def test_not_configured_must_load_default_value(self):
        reload_module(global_settings)
        self.assertEquals(SequentialDataFixture, type(global_settings.DDF_DEFAULT_DATA_FIXTURE))

    def test_may_be_an_internal_data_fixture_nick_name(self):
        conf.settings.DDF_DEFAULT_DATA_FIXTURE = 'sequential'
        reload_module(global_settings)
        self.assertEquals(SequentialDataFixture, type(global_settings.DDF_DEFAULT_DATA_FIXTURE))

        conf.settings.DDF_DEFAULT_DATA_FIXTURE = 'random'
        reload_module(global_settings)
        self.assertEquals(RandomDataFixture, type(global_settings.DDF_DEFAULT_DATA_FIXTURE))

        conf.settings.DDF_DEFAULT_DATA_FIXTURE = 'static_sequential'
        reload_module(global_settings)
        self.assertEquals(StaticSequentialDataFixture, type(global_settings.DDF_DEFAULT_DATA_FIXTURE))

    def test_may_be_a_path_to_a_custom_data_fixture(self):
        conf.settings.DDF_DEFAULT_DATA_FIXTURE = 'django_dynamic_fixture.tests.test_global_settings.CustomDataFixture'
        reload_module(global_settings)
        self.assertEquals(CustomDataFixture, type(global_settings.DDF_DEFAULT_DATA_FIXTURE))

    def test_if_path_can_not_be_found_it_will_raise_an_exception(self):
        conf.settings.DDF_DEFAULT_DATA_FIXTURE = 'unknown_path.CustomDataFixture'
        self.assertRaises(Exception, reload_module, global_settings)


class DDF_FILL_NULLABLE_FIELDS_TestCase(AbstractGlobalSettingsTestCase):
    def test_not_configured_must_load_default_value(self):
        reload_module(global_settings)
        self.assertEquals(True, global_settings.DDF_FILL_NULLABLE_FIELDS)

    def test_must_be_a_boolean(self):
        conf.settings.DDF_FILL_NULLABLE_FIELDS = False
        reload_module(global_settings)
        self.assertEquals(False, global_settings.DDF_FILL_NULLABLE_FIELDS)

    def test_must_raise_an_exception_if_it_is_not_a_boolean(self):
        conf.settings.DDF_FILL_NULLABLE_FIELDS = 'x'
        self.assertRaises(Exception, reload_module, global_settings)


class DDF_IGNORE_FIELDS_TestCase(AbstractGlobalSettingsTestCase):
    def test_not_configured_must_load_default_value(self):
        reload_module(global_settings)
        self.assertEquals([], global_settings.DDF_IGNORE_FIELDS)

    def test_must_be_a_list_of_strings(self):
        conf.settings.DDF_IGNORE_FIELDS = ['x']
        reload_module(global_settings)
        self.assertEquals(['x'], global_settings.DDF_IGNORE_FIELDS)

    def test_must_raise_an_exception_if_it_is_not_an_list_of_strings(self):
        conf.settings.DDF_IGNORE_FIELDS = None
        self.assertRaises(Exception, reload_module, global_settings)


class DDF_NUMBER_OF_LAPS_TestCase(AbstractGlobalSettingsTestCase):
    def test_not_configured_must_load_default_value(self):
        reload_module(global_settings)
        self.assertEquals(1, global_settings.DDF_NUMBER_OF_LAPS)

    def test_must_be_an_integer(self):
        conf.settings.DDF_NUMBER_OF_LAPS = 2
        reload_module(global_settings)
        self.assertEquals(2, global_settings.DDF_NUMBER_OF_LAPS)

    def test_must_raise_an_exception_if_it_is_not_an_integer(self):
        conf.settings.DDF_NUMBER_OF_LAPS = None
        self.assertRaises(Exception, reload_module, global_settings)


class DDF_VALIDATE_MODELS_TestCase(AbstractGlobalSettingsTestCase):
    def test_not_configured_must_load_default_value(self):
        reload_module(global_settings)
        self.assertEquals(False, global_settings.DDF_VALIDATE_MODELS)

    def test_must_be_a_boolean(self):
        conf.settings.DDF_VALIDATE_MODELS = False
        reload_module(global_settings)
        self.assertEquals(False, global_settings.DDF_VALIDATE_MODELS)

    def test_must_raise_an_exception_if_it_is_not_a_boolean(self):
        conf.settings.DDF_VALIDATE_MODELS = 'x'
        self.assertRaises(Exception, reload_module, global_settings)


class DDF_USE_LIBRARY_TestCase(AbstractGlobalSettingsTestCase):
    def test_not_configured_must_load_default_value(self):
        reload_module(global_settings)
        self.assertEquals(False, global_settings.DDF_USE_LIBRARY)

    def test_must_be_a_boolean(self):
        conf.settings.DDF_USE_LIBRARY = False
        reload_module(global_settings)
        self.assertEquals(False, global_settings.DDF_USE_LIBRARY)

    def test_must_raise_an_exception_if_it_is_not_a_boolean(self):
        conf.settings.DDF_USE_LIBRARY = 'x'
        self.assertRaises(Exception, reload_module, global_settings)

########NEW FILE########
__FILENAME__ = test_wrappers
# -*- coding: utf-8 -*-

from django.test import TestCase

from django_dynamic_fixture.models_test import EmptyModel, ModelWithRelationships, ModelForLibrary
from django_dynamic_fixture import N, G, F, C, P, look_up_alias, PRE_SAVE, POST_SAVE


class NShortcutTest(TestCase):
    def test_shortcut_N(self):
        instance = N(EmptyModel)
        self.assertEquals(None, instance.id)


class GShortcutTest(TestCase):
    def test_shortcut_G(self):
        instance = G(EmptyModel)
        self.assertNotEquals(None, instance.id)


class PShortcutTest(TestCase):
    def test_accept_model_instance(self):
        P(N(EmptyModel))
        P(G(EmptyModel))

    def test_accepts_list(self):
        P([N(EmptyModel), G(EmptyModel)])

    def test_accepts_tuple(self):
        P((N(EmptyModel), G(EmptyModel)))

    def test_accepts_queryset(self):
        P(EmptyModel.objects.all())


class FShortcutTest(TestCase):
    def test_fk(self):
        instance = G(ModelWithRelationships, integer=1000, foreignkey=F(integer=1001))
        self.assertEquals(1000, instance.integer)
        self.assertEquals(1001, instance.foreignkey.integer)

    def test_self_fk(self):
        instance = G(ModelWithRelationships, integer=1000, selfforeignkey=F(integer=1001))
        self.assertEquals(1000, instance.integer)
        self.assertEquals(1001, instance.selfforeignkey.integer)

    def test_o2o(self):
        instance = G(ModelWithRelationships, integer=1000, onetoone=F(integer=1001))
        self.assertEquals(1000, instance.integer)
        self.assertEquals(1001, instance.onetoone.integer)

    def test_m2m_with_one_element(self):
        instance = G(ModelWithRelationships, integer=1000, manytomany=[F(integer=1001)])
        self.assertEquals(1000, instance.integer)
        self.assertEquals(1001, instance.manytomany.all()[0].integer)

    def test_m2m_with_many_elements(self):
        instance = G(ModelWithRelationships, integer=1000, manytomany=[F(integer=1001), F(integer=1002)])
        self.assertEquals(1000, instance.integer)
        self.assertEquals(1001, instance.manytomany.all()[0].integer)
        self.assertEquals(1002, instance.manytomany.all()[1].integer)

    def test_full_example(self):
        instance = G(ModelWithRelationships, integer=1000,
                     foreignkey=F(integer=1001),
                     selfforeignkey=F(integer=1002),
                     onetoone=F(integer=1003),
                     manytomany=[F(integer=1004), F(integer=1005), F(selfforeignkey=F(integer=1006))])
        self.assertEquals(1000, instance.integer)
        self.assertEquals(1001, instance.foreignkey.integer)
        self.assertEquals(1002, instance.selfforeignkey.integer)
        self.assertEquals(1003, instance.onetoone.integer)
        self.assertEquals(1004, instance.manytomany.all()[0].integer)
        self.assertEquals(1005, instance.manytomany.all()[1].integer)
        self.assertEquals(1006, instance.manytomany.all()[2].selfforeignkey.integer)

    def test_using_look_up_alias(self):
        instance = G(ModelWithRelationships, integer=1000,
                     foreignkey__integer=1001,
                     selfforeignkey__integer=1002,
                     onetoone__integer=1003,
                     manytomany=[F(integer=1004), F(integer=1005), F(selfforeignkey__integer=1006)])
        self.assertEquals(1000, instance.integer)
        self.assertEquals(1001, instance.foreignkey.integer)
        self.assertEquals(1002, instance.selfforeignkey.integer)
        self.assertEquals(1003, instance.onetoone.integer)
        self.assertEquals(1004, instance.manytomany.all()[0].integer)
        self.assertEquals(1005, instance.manytomany.all()[1].integer)
        self.assertEquals(1006, instance.manytomany.all()[2].selfforeignkey.integer)


class CShortcutTest(TestCase):
    def test_copying_from_the_same_model(self):
        instance = G(ModelWithRelationships, integer=C('integer_b'))
        self.assertEquals(instance.integer, instance.integer_b)

    def test_copying_from_a_fk(self):
        instance = G(ModelWithRelationships, integer=C('foreignkey.integer'))
        self.assertEquals(instance.integer, instance.foreignkey.integer)

    def test_copying_from_a_one2one(self):
        instance = G(ModelWithRelationships, integer=C('onetoone.integer'))
        self.assertEquals(instance.integer, instance.onetoone.integer)

    def test_copying_from_a_self_fk(self):
        instance = G(ModelWithRelationships, integer=C('selfforeignkey.integer_b'))
        self.assertEquals(instance.integer, instance.selfforeignkey.integer_b)

    def test_copying_inside_fk(self):
        instance = G(ModelWithRelationships, selfforeignkey=F(integer=C('selfforeignkey.integer_b')))
        self.assertEquals(instance.selfforeignkey.integer, instance.selfforeignkey.selfforeignkey.integer_b)

    def test_copying_inside_many_to_many(self):
        instance = G(ModelWithRelationships, manytomany=[F(integer=C('integer_b'))])
        instance1 = instance.manytomany.all()[0]
        self.assertEquals(instance1.integer, instance1.integer_b)


class ShelveAndLibraryTest(TestCase):
    def test_shelve(self):
        instance = G(ModelForLibrary, integer=1000, shelve=True)
        self.assertEquals(1000, instance.integer)

        instance = G(ModelForLibrary, use_library=False)
        self.assertNotEquals(1000, instance.integer)

        instance = G(ModelForLibrary, use_library=True)
        self.assertEquals(1000, instance.integer)

        instance = G(ModelForLibrary, integer=1001, use_library=True)
        self.assertEquals(1001, instance.integer)


class CreatingMultipleObjectsTest(TestCase):
    def test_new(self):
        self.assertEquals([], N(EmptyModel, n=0))
        self.assertEquals([], N(EmptyModel, n= -1))
        self.assertTrue(isinstance(N(EmptyModel), EmptyModel)) # default is 1
        self.assertTrue(isinstance(N(EmptyModel, n=1), EmptyModel))
        self.assertEquals(2, len(N(EmptyModel, n=2)))

    def test_get(self):
        self.assertEquals([], G(EmptyModel, n=0))
        self.assertEquals([], G(EmptyModel, n= -1))
        self.assertTrue(isinstance(G(EmptyModel), EmptyModel)) # default is 1
        self.assertTrue(isinstance(G(EmptyModel, n=1), EmptyModel))
        self.assertEquals(2, len(G(EmptyModel, n=2)))


class LookUpSeparatorTest(TestCase):
    def test_look_up_alias_with_just_one_parameter(self):
        self.assertEquals({'a': 1}, look_up_alias(a=1))
        self.assertEquals({'a': F()}, look_up_alias(a=F()))
        self.assertEquals({'a_b': 1}, look_up_alias(a_b=1))
        self.assertEquals({'a': F(b=1)}, look_up_alias(a__b=1))
        self.assertEquals({'a_b': F(c=1)}, look_up_alias(a_b__c=1))
        self.assertEquals({'a': F(b=F(c=1))}, look_up_alias(a__b__c=1))
        self.assertEquals({'a_b': F(c_d=F(e_f=1))}, look_up_alias(a_b__c_d__e_f=1))

    def test_look_up_alias_with_many_parameters(self):
        self.assertEquals({'a': 1, 'b': 2}, look_up_alias(a=1, b=2))
        self.assertEquals({'a': 1, 'b_c': 2}, look_up_alias(a=1, b_c=2))
        self.assertEquals({'a': 1, 'b': F(c=2)}, look_up_alias(a=1, b__c=2))
        self.assertEquals({'a': F(b=1), 'c': F(d=2)}, look_up_alias(a__b=1, c__d=2))


class PreAndPostSaveTest(TestCase):
    def test_pre_save(self):
        PRE_SAVE(EmptyModel, lambda x: x)

    def test_post_save(self):
        POST_SAVE(EmptyModel, lambda x: x)


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line()

########NEW FILE########
__FILENAME__ = count_queries_on_save
# -*- coding: utf-8 -*-

from django_dynamic_fixture import new

from django.conf import settings
from django.db import connection
from django import db
from django_dynamic_fixture.django_helper import get_models_of_an_app, is_model_managed, get_unique_model_name, get_apps


class Report(object):
    def __init__(self):
        self.data = []
        self.errors = []

    def add_record(self, app, model, queries_insert, queries_update):
        self.data.append((app, model, queries_insert, queries_update))

    def add_error(self, msg):
        self.errors.append(msg)

    def export_csv(self, order_by_quantity_queries=False):
        if order_by_quantity_queries:
            self.data.sort(key=lambda t: t[2], reverse=True)
        print 'APP.MODEL;QUERIES ON INSERT;QUERIES ON UPDATE'
        for app, model, queries_insert, queries_update in self.data:
            print '%s;%s;%s' % (get_unique_model_name(model), queries_insert, queries_update)

        for err in self.errors:
            print err


class CountQueriesOnSave(object):
    def __init__(self):
        self.report = Report()

    def count_queries_for_model(self, app, model):
        try:
            model_instance = new(model, print_errors=False)
        except Exception as e:
            self.report.add_error('- Could not prepare %s: %s' % (get_unique_model_name(model), str(e)))
            return

        db.reset_queries()
        try:
            model_instance.save()
        except Exception as e:
            self.report.add_error('- Could not insert %s: %s' % (get_unique_model_name(model), str(e)))
            return
        queries_insert = len(connection.queries)

        db.reset_queries()
        try:
            model_instance.save()
        except Exception as e:
            self.report.add_error('- Could not update %s: %s' % (get_unique_model_name(model), str(e)))
            return
        queries_update = len(connection.queries)

        self.report.add_record(app, model, queries_insert, queries_update)

    def execute(self, app_labels=[], exclude_app_labels=[]):
        settings.DEBUG = True
        apps = get_apps(application_labels=app_labels, exclude_application_labels=exclude_app_labels)
        for app in apps:
            models = get_models_of_an_app(app)
            for model in models:
                if not is_model_managed(model):
                    continue
                self.count_queries_for_model(app, model)
        return self.report

########NEW FILE########
__FILENAME__ = count_queries_on_save
# -*- coding: utf-8 -*-

from optparse import make_option

from django.core.management.base import AppCommand
from queries.count_queries_on_save import CountQueriesOnSave


class Command(AppCommand):
    help = """
    Default Usage:
    manage.py count_queries_on_save
    manage.py count_queries_on_save --settings=my_settings

    = Specifying apps:
    manage.py count_queries_on_save [APP_NAMES]+
    Usage:
    manage.py count_queries_on_save app1 app2
    manage.py count_queries_on_save app1 app2
    
    = Skipping apps:
    manage.py count_queries_on_save --skip=[APP_NAME,]+
    Usage:
    manage.py count_queries_on_save --skip=app1
    manage.py count_queries_on_save --skip=app1,app2
    manage.py count_queries_on_save app1 app2 --skip=app2
    """
    args = '<app_name app_name ...> --skip=APP1,APP2'
    option_list = AppCommand.option_list + (
        make_option('--skip', '-s', dest='skip-apps', default='',
                    help='Skip applications. Separate application labels by commas.'),
    )

    def handle(self, *args, **options):
        script = CountQueriesOnSave()
        app_labels = args
        exclude_app_labels = options['skip-apps'].split(',')
        report = script.execute(app_labels, exclude_app_labels)
        report.export_csv(order_by_quantity_queries=True)

########NEW FILE########
__FILENAME__ = nose_plugin
# -*- coding: utf-8 -*-

from django.db import connection

from nose.plugins import Plugin


# http://readthedocs.org/docs/nose/en/latest/plugins/interface.html
class Queries(Plugin):
    "python manage.py test --with-queries"
    name = 'queries'
    enabled = True
    _queries_by_test_methods = []

    def configure(self, options, conf):
        """
        Called after the command line has been parsed, with the parsed options and the config container. 
        Here, implement any config storage or changes to state or operation that are set by command line options.
        DO NOT return a value from this method unless you want to stop all other plugins from being configured.
        """
        Plugin.configure(self, options, conf)
        connection.use_debug_cursor = True

    def beforeTest(self, test):
        "Called before the test is run (before startTest)."
        self.initial_amount_of_queries = len(connection.queries)

    def afterTest(self, test):
        "Called after the test has been run and the result recorded (after stopTest)."
        self.final_amount_of_queries = len(connection.queries)
        self._queries_by_test_methods.append((test, self.final_amount_of_queries - self.initial_amount_of_queries))

    def report(self, stream):
        """Called after all error output has been printed. Print your
        plugin's report to the provided stream. Return None to allow
        other plugins to print reports, any other value to stop them.

        :param stream: stream object; send your output here
        :type stream: file-like object
        """
        stream.write('\nREPORT OF AMOUNT OF QUERIES BY TEST:\n')
        for x in self._queries_by_test_methods:
            testcase = x[0]
            queries = x[1]
            stream.write('\n%s: %s' % (testcase, queries))
        stream.write('\n')

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import logging
import os
import sys
from os.path import dirname, abspath
from optparse import OptionParser

logging.getLogger('ddf').addHandler(logging.StreamHandler())

sys.path.insert(0, dirname(abspath(__file__)))

from django.conf import settings

if not settings.configured:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django_nose import NoseTestSuiteRunner

# Django-Nose must import test_models to avoid 'no such table' problem
from django_dynamic_fixture import models_test


def runtests(*test_args, **kwargs):
    kwargs.setdefault('interactive', False)
    test_runner = NoseTestSuiteRunner(**kwargs)
    failures = test_runner.run_tests(test_args)
    sys.exit(failures)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--verbosity', dest='verbosity', action='store', default=2, type=int)
    parser.add_options(NoseTestSuiteRunner.options)
    (options, args) = parser.parse_args()

    runtests(*args, **options.__dict__)


########NEW FILE########
__FILENAME__ = settings

IMPORT_DDF_MODELS = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

SECRET_KEY = 'ddf-secret-key'

INSTALLED_APPS = (
    'queries',
    'django_coverage',
    'django_nose',
    'django_dynamic_fixture',
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_PLUGINS = ['queries.Queries', 'ddf_setup.DDFSetup']

# Tell nose to measure coverage on the 'foo' and 'bar' apps
NOSE_ARGS = [
    # '--with-coverage',
    '--cover-html',
    '--cover-package=django_dynamic_fixture',
    '--cover-tests',
    '--cover-erase',
    ]

# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
# EMAIL_FILE_PATH = '/tmp/invest-messages'  # change this to a proper location
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# python manage.py test --with-coverage --cover-inclusive --cover-html --cover-package=django_dynamic_fixture.* --with-queries --with-ddf-setup

########NEW FILE########
