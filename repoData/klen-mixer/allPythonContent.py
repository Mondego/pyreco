__FILENAME__ = conf
""" Sphinx configuration. """
# -*- coding: utf-8 -*-

import os
import sys
import datetime

from mixer import __version__ as release

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = u'Mixer'
copyright = u'%s, Kirill Klenov' % datetime.datetime.now().year
version = '.'.join(release.split('.')[:2])
exclude_patterns = ['_build']
autodoc_member_order = 'bysource'
html_use_modindex = False
html_show_sphinx = False
htmlhelp_basename = 'Mixerdoc'
latex_documents = [
    ('index', 'Mixer.tex', u'Mixer Documentation',
        u'Kirill Klenov', 'manual'),
]
latex_use_modindex = False
latex_use_parts = True
man_pages = [
    ('index', 'mixer', u'Mixer Documentation',
     [u'Kirill Klenov'], 1)
]
pygments_style = 'tango'
html_theme = 'default'
html_theme_options = {}

# lint_ignore=W0622

########NEW FILE########
__FILENAME__ = auto
""" Automatic backend selection. """

from importlib import import_module

from .main import ProxyMixer
from . import _compat as _


class MixerProxy(object):

    """ Load mixer for class automaticly.

    ::

        from mixer.auto import mixer

        django_model_instance = mixer.blend('django.app.models.Model')
        sqlalchemy_model_instance = mixer.blend('sqlalchemy.app.models.Model')
        mongo_model_instance = mixer.blend('mongoengine.app.models.Model')

    """

    __store__ = dict()

    @classmethod
    def cycle(cls, count=5):
        """ Generate a lot instances.

        :return MetaMixer:

        """
        return ProxyMixer(cls, count)

    @classmethod
    def blend(cls, model, **params):
        """ Get a mixer class for model.

        :return instance:

        """
        scheme = cls.__load_cls(model)
        backend = cls.__store__.get(scheme)

        if not backend:

            if cls.__is_django_model(scheme):
                from .backend.django import mixer as backend

            elif cls.__is_sqlalchemy_model(scheme):
                from .backend.sqlalchemy import mixer as backend

            elif cls.__is_mongoengine_model(scheme):
                from .backend.mongoengine import mixer as backend

            cls.__store__[scheme] = backend

        return backend.blend(scheme, **params)

    @staticmethod
    def __load_cls(cls_type):
        if isinstance(cls_type, _.string_types):
            mod, cls_type = cls_type.rsplit('.', 1)
            mod = import_module(mod)
            cls_type = getattr(mod, cls_type)
        return cls_type

    @staticmethod
    def __is_django_model(model):
        try:
            from django.db.models import Model
            return issubclass(model, Model)
        except ImportError:
            return False

    @staticmethod
    def __is_sqlalchemy_model(model):
        return bool(getattr(model, '__mapper__', False))

    @staticmethod
    def __is_mongoengine_model(model):
        try:
            from mongoengine.base.document import BaseDocument
            return issubclass(model, BaseDocument)
        except ImportError:
            return False


mixer = MixerProxy()

########NEW FILE########
__FILENAME__ = django
""" Django support. """
from __future__ import absolute_import

import datetime
import decimal
from os import path

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (
    GenericForeignKey, GenericRelation)
from django import VERSION
from django.core.files.base import ContentFile

from .. import generators as g, mix_types as t
from .. import _compat as _
from ..main import (
    SKIP_VALUE, TypeMixerMeta as BaseTypeMixerMeta, TypeMixer as BaseTypeMixer,
    GenFactory as BaseFactory, Mixer as BaseMixer, _Deffered)


get_contentfile = ContentFile

if VERSION < (1, 4):
    get_contentfile = lambda content, name: ContentFile(content)


MOCK_FILE = path.abspath(path.join(
    path.dirname(path.dirname(__file__)), 'resources', 'file.txt'
))
MOCK_IMAGE = path.abspath(path.join(
    path.dirname(path.dirname(__file__)), 'resources', 'image.jpg'
))


def get_file(filepath=MOCK_FILE, **kwargs):
    """ Generate a content file.

    :return ContentFile:

    """
    with open(filepath, 'rb') as f:
        name = path.basename(filepath)
        return get_contentfile(f.read(), name)


def get_image(filepath=MOCK_IMAGE):
    """ Generate a content image.

    :return ContentFile:

    """
    return get_file(filepath)


def get_relation(_pylama_scheme=None, _pylama_typemixer=None, **params):
    """ Function description. """
    scheme = _pylama_scheme.related.parent_model

    if scheme is ContentType:
        choices = [m for m in models.get_models() if m is not ContentType]
        return ContentType.objects.get_for_model(g.get_choice(choices))

    return TypeMixer(
        scheme,
        mixer=_pylama_typemixer._TypeMixer__mixer,
        factory=_pylama_typemixer._TypeMixer__factory,
        fake=_pylama_typemixer._TypeMixer__fake,
    ).blend(**params)


class GenFactory(BaseFactory):

    """ Map a django classes to simple types. """

    types = {
        models.IntegerField: int,
        (models.CharField, models.SlugField): str,
        models.BigIntegerField: t.BigInteger,
        models.BooleanField: bool,
        models.DateField: datetime.date,
        models.DateTimeField: datetime.datetime,
        models.DecimalField: decimal.Decimal,
        models.EmailField: t.EmailString,
        models.FloatField: float,
        models.IPAddressField: t.IP4String,
        (models.AutoField, models.PositiveIntegerField): t.PositiveInteger,
        models.PositiveSmallIntegerField: t.PositiveSmallInteger,
        models.SmallIntegerField: t.SmallInteger,
        models.TextField: t.Text,
        models.TimeField: datetime.time,
        models.URLField: t.URL,
    }

    generators = {
        models.FileField: get_file,
        models.ImageField: get_image,
        models.ForeignKey: get_relation,
        models.OneToOneField: get_relation,
        models.ManyToManyField: get_relation,
    }


class TypeMixerMeta(BaseTypeMixerMeta):

    """ Load django models from strings. """

    def __new__(mcs, name, bases, params):
        """ Associate Scheme with Django models.

        Cache Django models.

        :return mixer.backend.django.TypeMixer: A generated class.

        """
        params['models_cache'] = dict()
        cls = super(TypeMixerMeta, mcs).__new__(mcs, name, bases, params)
        cls.__update_cache()
        return cls

    def __load_cls(cls, cls_type):

        if isinstance(cls_type, _.string_types):
            if '.' in cls_type:
                app_label, model_name = cls_type.split(".")
                return models.get_model(app_label, model_name)

            else:
                try:
                    if cls_type not in cls.models_cache:
                        cls.__update_cache()

                    return cls.models_cache[cls_type]
                except KeyError:
                    raise ValueError('Model "%s" not found.' % cls_type)

        return cls_type

    def __update_cache(cls):
        for app_models in models.loading.cache.app_models.values():
            for name, model in app_models.items():
                cls.models_cache[name] = model


class TypeMixer(_.with_metaclass(TypeMixerMeta, BaseTypeMixer)):

    """ TypeMixer for Django. """

    __metaclass__ = TypeMixerMeta

    factory = GenFactory

    def postprocess(self, target, postprocess_values):
        """ Fill postprocess_values. """
        for name, deffered in postprocess_values:
            if not type(deffered.scheme) is GenericForeignKey:
                continue

            value = self.__get_value(deffered.value)
            setattr(target, name, value)

        if self.__mixer:
            target = self.__mixer.postprocess(target)

        for name, deffered in postprocess_values:

            if type(deffered.scheme) is GenericForeignKey or not target.pk:
                continue

            value = self.__get_value(deffered.value)

            # # If the ManyToMany relation has an intermediary model,
            # # the add and remove methods do not exist.
            if not deffered.scheme.rel.through._meta.auto_created and self.__mixer: # noqa
                self.__mixer.blend(
                    deffered.scheme.rel.through, **{
                        deffered.scheme.m2m_field_name(): target,
                        deffered.scheme.m2m_reverse_field_name(): value})
                continue

            if not isinstance(value, (list, tuple)):
                value = [value]

            setattr(target, name, value)

        return target

    def get_value(self, field_name, field_value):
        """ Set value to generated instance.

        :return : None or (name, value) for later use

        """
        field = self.__fields.get(field_name)

        if field and (field.scheme in self.__scheme._meta.local_many_to_many or
                      type(field.scheme) is GenericForeignKey):
            return field_name, _Deffered(field_value, field.scheme)

        return super(TypeMixer, self).get_value(field_name, field_value)

    @staticmethod
    def get_default(field):
        """ Get default value from field.

        :return value: A default value or SKIP_VALUE

        """
        if not field.scheme.has_default():
            return SKIP_VALUE

        return field.scheme.get_default()

    def gen_select(self, field_name, select):
        """ Select exists value from database.

        :param field_name: Name of field for generation.

        :return : None or (name, value) for later use

        """
        field = self.__fields.get(field_name)
        if not field:
            return super(TypeMixer, self).gen_select(field_name, select)

        try:
            return field.name, field.scheme.rel.to.objects.filter(
                **select.params).order_by('?')[0]

        except Exception:
            raise Exception(
                "Cannot find a value for the field: '{0}'".format(field_name))

    def gen_field(self, field):
        """ Generate value by field.

        :param relation: Instance of :class:`Field`

        :return : None or (name, value) for later use

        """
        if isinstance(field.scheme, GenericForeignKey):
            return field.name, SKIP_VALUE

        if field.params and not field.scheme:
            raise ValueError('Invalid relation %s' % field.name)

        return super(TypeMixer, self).gen_field(field)

    def make_generator(self, field, fname=None, fake=False, args=None, kwargs=None): # noqa
        """ Make values generator for field.

        :param field: A mixer field
        :param fname: Field name
        :param fake: Force fake data

        :return generator:

        """
        args = [] if args is None else args
        kwargs = {} if kwargs is None else kwargs

        fcls = type(field)
        stype = self.__factory.cls_to_simple(fcls)

        if fcls is models.CommaSeparatedIntegerField:
            return g.gen_choices(
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 0], field.max_length)

        if field and field.choices:
            choices, _ = list(zip(*field.choices))
            return g.gen_choice(choices)

        if stype in (str, t.Text):
            kwargs['length'] = field.max_length

        elif stype is decimal.Decimal:
            kwargs['i'] = field.max_digits - field.decimal_places
            kwargs['d'] = field.decimal_places

        elif isinstance(field, models.fields.related.RelatedField):
            kwargs.update({'_pylama_typemixer': self, '_pylama_scheme': field})

        return super(TypeMixer, self).make_generator(
            fcls, field_name=fname, fake=fake, args=[], kwargs=kwargs)

    @staticmethod
    def is_unique(field):
        """ Return True is field's value should be a unique.

        :return bool:

        """
        return field.scheme.unique

    @staticmethod
    def is_required(field):
        """ Return True is field's value should be defined.

        :return bool:

        """
        if field.params:
            return True

        if field.scheme.null and field.scheme.blank:
            return False

        if field.scheme.auto_created:
            return False

        if isinstance(field.scheme, models.ManyToManyField):
            return False

        if isinstance(field.scheme, GenericRelation):
            return False

        return True

    def guard(self, **filters):
        """ Look objects in database.

        :returns: A finded object or False

        """
        qs = self.__scheme.objects.filter(**filters)
        count = qs.count()

        if count == 1:
            return qs.get()

        if count:
            return list(qs)

        return False

    def __load_fields(self):

        for field in self.__scheme._meta.virtual_fields:
            yield field.name, t.Field(field, field.name)

        for field in self.__scheme._meta.fields:

            if isinstance(field, models.AutoField)\
                    and self.__mixer and self.__mixer.params.get('commit'):
                continue

            yield field.name, t.Field(field, field.name)

        for field in self.__scheme._meta.local_many_to_many:
            yield field.name, t.Field(field, field.name)


class Mixer(BaseMixer):

    """ Integration with Django. """

    type_mixer_cls = TypeMixer

    def __init__(self, commit=True, **params):
        """Initialize Mixer instance.

        :param commit: (True) Save object to database.

        """
        super(Mixer, self).__init__(**params)
        self.params['commit'] = commit

    def postprocess(self, target):
        """ Save objects in db.

        :return value: A generated value

        """
        if self.params.get('commit'):
            target.save()

        return target


# Default mixer
mixer = Mixer()

# pylama:ignore=E1120

########NEW FILE########
__FILENAME__ = flask
""" Module integrate the Mixer to Flask application.

See example: ::

    from mixer.backend.flask import mixer

    mixer.init_app(flask_app)

    user = mixer.blend('path.to.models.User')

"""
from __future__ import absolute_import

from .sqlalchemy import TypeMixer, Mixer as BaseMixer


class Mixer(BaseMixer):

    """ Init application. """

    type_mixer_cls = TypeMixer

    def __init__(self, app=None, commit=True, **kwargs):
        """ Initialize the SQLAlchemy Mixer.

        :param fake: (True) Generate fake data instead of random data.
        :param app: Flask application
        :param commit: (True) Commit instance to session after creation.

        """
        super(Mixer, self).__init__(**kwargs)
        self.params['commit'] = commit
        if app:
            self.init_app(app)

    def init_app(self, app):
        """ Init application.

        This callback can be used to initialize an application for the
        use with this mixer setup.

        :param app: Flask application

        """
        assert app.extensions and app.extensions[
            'sqlalchemy'], "Flask-SQLAlchemy must be inialized before Mixer."
        db = app.extensions['sqlalchemy'].db
        self.params['session'] = db.session

        # register extension with app
        app.extensions['mixer'] = self


# Default mixer
mixer = Mixer(commit=True)

# lint_ignore=W0201

########NEW FILE########
__FILENAME__ = mongoengine
""" Support for Mongoengine ODM.

.. note:: Support for Mongoengine_ is in early development.

::

    from mixer.backend.mongoengine import mixer

    class User(Document):
        created_at = DateTimeField(default=datetime.datetime.now)
        email = EmailField(required=True)
        first_name = StringField(max_length=50)
        last_name = StringField(max_length=50)

    class Post(Document):
        title = StringField(max_length=120, required=True)
        author = ReferenceField(User)
        tags = ListField(StringField(max_length=30))

    post = mixer.blend(Post, author__username='foo')

"""
from __future__ import absolute_import

import datetime
import decimal

from bson import ObjectId
from mongoengine import (
    BooleanField,
    DateTimeField,
    DecimalField,
    Document,
    EmailField,
    EmbeddedDocumentField,
    FloatField,
    GenericReferenceField,
    GeoPointField,
    IntField,
    LineStringField,
    ListField,
    ObjectIdField,
    PointField,
    PolygonField,
    ReferenceField,
    StringField,
    URLField,
    UUIDField,
)

from .. import mix_types as t, generators as g, fakers as f
from ..main import (
    SKIP_VALUE, TypeMixer as BaseTypeMixer, GenFactory as BaseFactory,
    Mixer as BaseMixer,
)


def get_objectid(**kwargs):
    """ Create a new ObjectId instance.

    :return ObjectId:

    """
    return ObjectId()


def get_pointfield(**kwargs):
    """ Get a Point structure.

    :return dict:

    """
    return dict(type='Point', coordinates=f.get_coordinates())


def get_linestring(length=5, **kwargs):
    """ Get a LineString structure.

    :return dict:

    """
    return dict(
        type='LineString',
        coordinates=[f.get_coordinates() for _ in range(length)])


def get_polygon(length=5, **kwargs):
    """ Get a Poligon structure.

    :return dict:

    """
    lines = []
    for _ in range(length):
        line = get_linestring()['coordinates']
        if lines:
            line.insert(0, lines[-1][-1])

        lines.append(line)

    if lines:
        lines[0].insert(0, lines[-1][-1])

    return dict(type='Poligon', coordinates=lines)


def get_generic_reference(_pylama_typemixer=None, **params):
    """ Choose a GenericRelation. """
    meta = type(_pylama_typemixer)
    scheme = g.get_choice([
        m for (_, m, _, _) in meta.mixers.keys()
        if issubclass(m, Document) and m is not _pylama_typemixer._TypeMixer__scheme # noqa
    ])
    return TypeMixer(
        scheme,
        mixer=_pylama_typemixer._TypeMixer__mixer,
        factory=_pylama_typemixer._TypeMixer__factory,
        fake=_pylama_typemixer._TypeMixer__fake,
    ).blend(**params)


class GenFactory(BaseFactory):

    """ Map a mongoengine classes to simple types. """

    types = {
        BooleanField: bool,
        DateTimeField: datetime.datetime,
        DecimalField: decimal.Decimal,
        EmailField: t.EmailString,
        FloatField: float,
        IntField: int,
        StringField: str,
        URLField: t.URL,
        UUIDField: t.UUID,
    }

    generators = {
        GenericReferenceField: get_generic_reference,
        GeoPointField: f.get_coordinates,
        LineStringField: get_linestring,
        ObjectIdField: get_objectid,
        PointField: get_pointfield,
        PolygonField: get_polygon,
    }


class TypeMixer(BaseTypeMixer):

    """ TypeMixer for Mongoengine. """

    factory = GenFactory

    def make_generator(self, me_field, field_name=None, fake=None, args=None, kwargs=None): # noqa
        """ Make values generator for field.

        :param me_field: Mongoengine field's instance
        :param field_name: Field name
        :param fake: Force fake data

        :return generator:

        """
        ftype = type(me_field)
        args = [] if args is None else args
        kwargs = {} if kwargs is None else kwargs

        if me_field.choices:
            if isinstance(me_field.choices[0], tuple):
                choices, _ = list(zip(*me_field.choices))
            else:
                choices = list(me_field.choices)

            return g.gen_choice(choices)

        if ftype is StringField:
            kwargs['length'] = me_field.max_length

        elif ftype is ListField:
            gen = self.make_generator(me_field.field, kwargs=kwargs)
            return g.loop(lambda: [next(gen) for _ in range(3)])()

        elif isinstance(me_field, (EmbeddedDocumentField, ReferenceField)):
            ftype = me_field.document_type

        elif ftype is GenericReferenceField:
            kwargs.update({'_pylama_typemixer': self})

        elif ftype is DecimalField:
            sign, (ii,), dd = me_field.precision.as_tuple()
            kwargs['d'] = abs(dd)
            kwargs['positive'] = not sign
            kwargs['i'] = ii + 1

        return super(TypeMixer, self).make_generator(
            ftype, field_name=field_name, fake=fake, args=args, kwargs=kwargs)

    @staticmethod
    def get_default(field):
        """ Get default value from field.

        :return value: A default value or NO_VALUE

        """
        if not field.scheme.default:
            return SKIP_VALUE

        if callable(field.scheme.default):
            return field.scheme.default()

        return field.scheme.default

    @staticmethod
    def is_unique(field):
        """ Return True is field's value should be a unique.

        :return bool:

        """
        return field.scheme.unique

    @staticmethod
    def is_required(field):
        """ Return True is field's value should be defined.

        :return bool:

        """
        if isinstance(field.scheme, ReferenceField):
            return True

        return field.scheme.required or isinstance(field.scheme, ObjectIdField)

    def __load_fields(self):
        for fname, field in self.__scheme._fields.items():

            yield fname, t.Field(field, fname)


class Mixer(BaseMixer):

    """ Mixer class for mongoengine.

    Default mixer (desnt save a generated instances to db)
    ::

        from mixer.backend.mongoengine import mixer

        user = mixer.blend(User)

    You can initialize the Mixer by manual:
    ::
        from mixer.backend.mongoengine import Mixer

        mixer = Mixer(commit=True)
        user = mixer.blend(User)

    """

    type_mixer_cls = TypeMixer

    def __init__(self, commit=True, **params):
        """ Initialize the Mongoengine Mixer.

        :param fake: (True) Generate fake data instead of random data.
        :param commit: (True) Save object to Mongo DB.

        """
        super(Mixer, self).__init__(**params)
        self.params['commit'] = commit

    def postprocess(self, target):
        """ Save instance to DB.

        :return instance:

        """
        if self.params.get('commit') and isinstance(target, Document):
            target.save()

        return target


mixer = Mixer()


# lint_ignore=W0212

########NEW FILE########
__FILENAME__ = peewee
""" Support for Peewee ODM.

::

    from mixer.backend.peewee import mixer

"""
from __future__ import absolute_import

from peewee import * # noqa
import datetime
import decimal

from .. import mix_types as t
from ..main import (
    TypeMixer as BaseTypeMixer, Mixer as BaseMixer, SKIP_VALUE,
    GenFactory as BaseFactory)


def get_relation(_pylama_scheme=None, _pylama_typemixer=None, **params):
    """ Function description. """
    scheme = _pylama_scheme.rel_model

    return TypeMixer(
        scheme,
        mixer=_pylama_typemixer._TypeMixer__mixer,
        factory=_pylama_typemixer._TypeMixer__factory,
        fake=_pylama_typemixer._TypeMixer__fake,
    ).blend(**params)


def get_blob(**kwargs):
    """ Generate value for BlobField. """
    raise NotImplementedError


class GenFactory(BaseFactory):

    """ Map a peewee classes to simple types. """

    types = {
        PrimaryKeyField: t.PositiveInteger,
        IntegerField: int,
        BigIntegerField: t.BigInteger,
        (FloatField, DoubleField): float,
        DecimalField: decimal.Decimal,
        CharField: str,
        TextField: t.Text,
        DateTimeField: datetime.datetime,
        DateField: datetime.date,
        TimeField: datetime.time,
        BooleanField: bool,
        # BlobField: None,
    }

    generators = {
        BlobField: get_blob,
        ForeignKeyField: get_relation,
    }


class TypeMixer(BaseTypeMixer):

    """ TypeMixer for Pony ORM. """

    factory = GenFactory

    def __load_fields(self):
        for name, field in self.__scheme._meta.get_sorted_fields():
            yield name, t.Field(field, name)

    def populate_target(self, values):
        """ Populate target. """
        return self.__scheme(**dict(values))

    def gen_field(self, field):
        """ Function description. """
        if isinstance(field.scheme, PrimaryKeyField)\
                and self.__mixer and self.__mixer.params.get('commit'):
            return field.name, SKIP_VALUE
        return super(TypeMixer, self).gen_field(field)

    def is_required(self, field):
        """ Return True is field's value should be defined.

        :return bool:

        """
        return not field.scheme.null

    def is_unique(self, field):
        """ Return True is field's value should be a unique.

        :return bool:

        """
        return field.scheme.unique

    @staticmethod
    def get_default(field):
        """ Get default value from field.

        :return value:

        """
        return field.scheme.default is None and SKIP_VALUE or field.scheme.default # noqa

    def make_generator(self, field, field_name=None, fake=False, args=None, kwargs=None): # noqa
        """ Make values generator for column.

        :param column: SqlAlchemy column
        :param field_name: Field name
        :param fake: Force fake data

        :return generator:

        """
        args = [] if args is None else args
        kwargs = {} if kwargs is None else kwargs

        if isinstance(field, ForeignKeyField):
            kwargs.update({'_pylama_typemixer': self, '_pylama_scheme': field})

        return super(TypeMixer, self).make_generator(
            type(field), field_name=field_name, fake=fake, args=args,
            kwargs=kwargs)


class Mixer(BaseMixer):

    """ Integration with Pony ORM. """

    type_mixer_cls = TypeMixer

    def postprocess(self, target):
        """ Save objects in db.

        :return value: A generated value

        """
        if self.params.get('commit'):
            target.save()

        return target


# Default Pony mixer
mixer = Mixer()

########NEW FILE########
__FILENAME__ = pony
""" Support for Pony ODM.

::

    from mixer.backend.pony import mixer
"""
from __future__ import absolute_import

from pony.orm import commit

from .. import mix_types as t
from ..main import TypeMixer as BaseTypeMixer, Mixer as BaseMixer, SKIP_VALUE


class TypeMixer(BaseTypeMixer):

    """ TypeMixer for Pony ORM. """

    def __load_fields(self):
        for attr in self.__scheme._attrs_:
            yield attr.column, t.Field(attr, attr.column)

    def populate_target(self, values):
        """ Populate target. """
        return self.__scheme(**dict(values))

    def is_required(self, field):
        """ Return True is field's value should be defined.

        :return bool:

        """
        return field.scheme.is_required and not field.scheme.is_pk

    def is_unique(self, field):
        """ Return True is field's value should be a unique.

        :return bool:

        """
        return field.scheme.is_unique

    @staticmethod
    def get_default(field):
        """ Get default value from field.

        :return value:

        """
        return field.scheme.default is None and SKIP_VALUE or field.scheme.default # noqa

    def make_generator(self, field, field_name=None, fake=False, args=None, kwargs=None): # noqa
        """ Make values generator for column.

        :param column: SqlAlchemy column
        :param field_name: Field name
        :param fake: Force fake data

        :return generator:

        """
        py_type = field.py_type
        return super(TypeMixer, self).make_generator(
            py_type, field_name=field_name, fake=fake, args=args,
            kwargs=kwargs)


class Mixer(BaseMixer):

    """ Integration with Pony ORM. """

    type_mixer_cls = TypeMixer

    def postprocess(self, target):
        """ Save objects in db.

        :return value: A generated value

        """
        if self.params.get('commit'):
            commit()

        return target


# Default Pony mixer
mixer = Mixer()

########NEW FILE########
__FILENAME__ = sqlalchemy
""" SQLAlchemy support. """
from __future__ import absolute_import

import datetime

import decimal
from sqlalchemy import func
# from sqlalchemy.orm.interfaces import MANYTOONE
from sqlalchemy.orm.relationships import RelationshipProperty
from sqlalchemy.types import (
    BIGINT, BOOLEAN, BigInteger, Boolean, CHAR, DATE, DATETIME, DECIMAL, Date,
    DateTime, FLOAT, Float, INT, INTEGER, Integer, NCHAR, NVARCHAR, NUMERIC,
    Numeric, SMALLINT, SmallInteger, String, TEXT, TIME, Text, Time, Unicode,
    UnicodeText, VARCHAR, Enum)

from .. import mix_types as t, generators as g
from ..main import (
    SKIP_VALUE, LOGGER, TypeMixer as BaseTypeMixer, GenFactory as BaseFactory,
    Mixer as BaseMixer, _Deffered)


class GenFactory(BaseFactory):

    """ Map a sqlalchemy classes to simple types. """

    types = {
        (String, VARCHAR, Unicode, NVARCHAR, NCHAR, CHAR): str,
        (Text, UnicodeText, TEXT): t.Text,
        (Boolean, BOOLEAN): bool,
        (Date, DATE): datetime.date,
        (DateTime, DATETIME): datetime.datetime,
        (Time, TIME): datetime.time,
        (DECIMAL, Numeric, NUMERIC): decimal.Decimal,
        (Float, FLOAT): float,
        (Integer, INTEGER, INT): int,
        (BigInteger, BIGINT): t.BigInteger,
        (SmallInteger, SMALLINT): t.SmallInteger,
    }


class TypeMixer(BaseTypeMixer):

    """ TypeMixer for SQLAlchemy. """

    factory = GenFactory

    def __init__(self, cls, **params):
        """ Init TypeMixer and save the mapper. """
        super(TypeMixer, self).__init__(cls, **params)
        self.mapper = self.__scheme._sa_class_manager.mapper

    def postprocess(self, target, postprocess_values):
        """ Fill postprocess values. """
        for name, deffered in postprocess_values:
            value = deffered.value
            setattr(target, name, value)

            col = deffered.scheme.local_remote_pairs[0][0]
            setattr(
                target, col.name,
                deffered.scheme.mapper.identity_key_from_instance(value)[1][0])

        if self.__mixer:
            target = self.__mixer.postprocess(target)

        return target

    @staticmethod
    def get_default(field):
        """ Get default value from field.

        :return value: A default value or NO_VALUE

        """
        column = field.scheme

        if isinstance(column, RelationshipProperty):
            column = column.local_remote_pairs[0][0]

        if not column.default:
            return SKIP_VALUE

        if column.default.is_callable:
            return column.default.arg(None)

        return getattr(column.default, 'arg', SKIP_VALUE)

    def gen_select(self, field_name, select):
        """ Select exists value from database.

        :param field_name: Name of field for generation.

        :return : None or (name, value) for later use

        """
        if not self.__mixer or not self.__mixer.params.get('session'):
            return field_name, SKIP_VALUE

        relation = self.mapper.get_property(field_name)
        session = self.__mixer.params.get('session')
        value = session.query(
            relation.mapper.class_
        ).filter(*select.choices).order_by(func.random()).first()
        return self.get_value(field_name, value)

    @staticmethod
    def is_unique(field):
        """ Return True is field's value should be a unique.

        :return bool:

        """
        scheme = field.scheme

        if isinstance(scheme, RelationshipProperty):
            scheme = scheme.local_remote_pairs[0][0]

        return scheme.unique

    @staticmethod
    def is_required(field):
        """ Return True is field's value should be defined.

        :return bool:

        """
        column = field.scheme
        if isinstance(column, RelationshipProperty):
            column = column.local_remote_pairs[0][0]

        return (
            bool(field.params)
            or not column.nullable
            and not (column.autoincrement and column.primary_key))

    def get_value(self, field_name, field_value):
        """ Get `value` as `field_name`.

        :return : None or (name, value) for later use

        """
        field = self.__fields.get(field_name)
        if field and isinstance(field.scheme, RelationshipProperty):
            return field_name, _Deffered(field_value, field.scheme)

        return super(TypeMixer, self).get_value(field_name, field_value)

    def make_generator(self, column, field_name=None, fake=False, args=None, kwargs=None): # noqa
        """ Make values generator for column.

        :param column: SqlAlchemy column
        :param field_name: Field name
        :param fake: Force fake data

        :return generator:

        """
        args = [] if args is None else args
        kwargs = {} if kwargs is None else kwargs

        if isinstance(column, RelationshipProperty):
            gen = g.loop(TypeMixer(
                column.mapper.class_, mixer=self.__mixer, fake=self.__fake,
                factory=self.__factory).blend)(**kwargs)
            return gen

        ftype = type(column.type)
        stype = self.factory.cls_to_simple(ftype)

        if stype is str:
            kwargs['length'] = column.type.length

        if ftype is Enum:
            return g.gen_choice(column.type.enums)

        return super(TypeMixer, self).make_generator(
            stype, field_name=field_name, fake=fake, args=args, kwargs=kwargs)

    def __load_fields(self):
        """ Prepare SQLALchemyTypeMixer.

        Select columns and relations for data generation.

        """
        mapper = self.__scheme._sa_class_manager.mapper
        relations = set()
        if hasattr(mapper, 'relationships'):
            for rel in mapper.relationships:
                relations |= rel.local_columns
                yield rel.key, t.Field(rel, rel.key)

        for column in mapper.columns:
            if column not in relations:
                yield column.name, t.Field(column, column.name)


class Mixer(BaseMixer):

    """ Integration with SQLAlchemy. """

    type_mixer_cls = TypeMixer

    def __init__(self, session=None, commit=True, **params):
        """Initialize the SQLAlchemy Mixer.

        :param fake: (True) Generate fake data instead of random data.
        :param session: SQLAlchemy session. Using for commits.
        :param commit: (True) Commit instance to session after creation.

        """
        super(Mixer, self).__init__(**params)
        self.params['session'] = session
        self.params['commit'] = bool(session) and commit

    def postprocess(self, target):
        """ Save objects in db.

        :return value: A generated value

        """
        if self.params.get('commit'):
            session = self.params.get('session')
            if not session:
                LOGGER.warn("'commit' set true but session not initialized.")
            else:
                session.add(target)
                session.commit()

        return target


# Default mixer
mixer = Mixer()

# lint_ignore=W0212,E1002

########NEW FILE########
__FILENAME__ = factory
""" Mixer factories. """

import datetime
import decimal

from . import _compat as _, generators as g, mix_types as t, fakers as f


class GenFactoryMeta(type):

    """ Precache generators. """

    def __new__(mcs, name, bases, params):
        generators = dict()
        fakers = dict()
        types = dict()

        for cls in bases:
            if isinstance(cls, GenFactoryMeta):
                generators.update(cls.generators)
                fakers.update(cls.fakers)
                types.update(cls.types)

        fakers.update(params.get('fakers', dict()))
        types.update(params.get('types', dict()))

        types = dict(mcs.__flat_keys(types))

        if types:
            for atype, btype in types.items():
                factory = generators.get(btype)
                if factory:
                    generators[atype] = factory

        generators.update(params.get('generators', dict()))
        generators = dict(mcs.__flat_keys(generators))

        params['generators'] = generators
        params['fakers'] = fakers
        params['types'] = types

        return super(GenFactoryMeta, mcs).__new__(mcs, name, bases, params)

    @staticmethod
    def __flat_keys(d):
        for key, value in d.items():
            if isinstance(key, (tuple, list)):
                for k in key:
                    yield k, value
                continue
            yield key, value


class GenFactory(_.with_metaclass(GenFactoryMeta)):

    """ Make generators for types. """

    generators = {
        bool: g.get_boolean,
        float: g.get_float,
        int: g.get_integer,
        str: g.get_string,
        list: g.get_list,
        set: lambda **kwargs: set(g.get_list()),
        tuple: lambda **kwargs: tuple(g.get_list()),
        dict: lambda **kwargs: dict(zip(g.get_list(), g.get_list())),
        datetime.date: g.get_date,
        datetime.datetime: g.get_datetime,
        datetime.time: g.get_time,
        decimal.Decimal: g.get_decimal,
        t.BigInteger: g.get_big_integer,
        t.EmailString: f.get_email,
        t.HostnameString: f.get_hostname,
        t.IP4String: f.get_ip4,
        t.NullOrBoolean: g.get_null_or_boolean,
        t.PositiveDecimal: g.get_positive_decimal,
        t.PositiveInteger: g.get_positive_integer,
        t.SmallInteger: g.get_small_integer,
        t.Text: f.get_lorem,
        t.URL: f.get_url,
        t.UUID: f.get_uuid,
        type(None): '',
    }

    fakers = {
        ('address', str): f.get_address,
        ('body', str): f.get_lorem,
        ('category', str): f.get_genre,
        ('city', str): f.get_city,
        ('company', str): f.get_company,
        ('content', str): f.get_lorem,
        ('country', str): f.get_country,
        ('description', str): f.get_lorem,
        ('domain', str): f.get_hostname,
        ('email', str): f.get_email,
        ('first_name', str): f.get_firstname,
        ('firstname', str): f.get_firstname,
        ('genre', str): f.get_genre,
        ('last_name', str): f.get_lastname,
        ('lastname', str): f.get_lastname,
        ('lat', float): f.get_latlon,
        ('latitude', float): f.get_latlon,
        ('login', str): f.get_username,
        ('lon', float): f.get_latlon,
        ('longitude', float): f.get_latlon,
        ('name', str): f.get_name,
        ('phone', str): f.get_phone,
        ('slug', str): f.get_slug,
        ('street', str): f.get_street,
        ('title', str): f.get_short_lorem,
        ('url', t.URL): f.get_url,
        ('username', str): f.get_username,
        ('percent', int): g.get_percent,
        ('percent', decimal.Decimal): g.get_percent_decimal,
    }

    types = {
        _.string_types: str,
        _.integer_types: int,
    }

    @classmethod
    def cls_to_simple(cls, fcls):
        """ Translate class to one of simple base types.

        :return type: A simple type for generation

        """
        return cls.types.get(fcls) or (
            fcls if fcls in cls.generators
            else None
        )

    @staticmethod
    def name_to_simple(fname):
        """ Translate name to one of simple base names.

        :return str:

        """
        fname = fname or ''
        return fname.lower().strip()

    @classmethod
    def gen_maker(cls, fcls, fname=None, fake=False):
        """ Make a generator based on class and name.

        :return generator:

        """
        simple = cls.cls_to_simple(fcls)
        func = cls.generators.get(fcls) or cls.generators.get(simple)

        if fname and fake and (fname, simple) in cls.fakers:
            fname = cls.name_to_simple(fname)
            func = cls.fakers.get((fname, simple)) or func

        return g.loop(func) if func is not None else False

########NEW FILE########
__FILENAME__ = fakers
""" Generate fake data.

Functions for generation some kind of fake datas. You can use ``mixer.fakers``
by manual, like this:

::

    from mixer import fakers as f

    name = f.get_name()
    country = f.get_country()

    url_gen = f.gen_url()(hostname=True)
    urls = [next(url_gen) for _ in range(10)]


Or you can using shortcut from :class:`mixer.main.Mixer` like this:

::

    mixer.f.get_city()  # -> Moscow

"""

from . import generators as g
import random
import uuid
import decimal

DEFAULT_NAME_MASK = "{firstname} {lastname}"
DEFAULT_USERNAME_MASK_CHOICES = (
    '{one}{num}', '{one}_{two}', '{one}.{two}', '{two}{one}{num}')

FIRSTNAMES = (
    "Alice", "Adams", "Allen", "Anderson", "Baker", "Barbara", "Betty",
    "Brown", "Bob", "Campbell", "Carol", "Carter", "Clark", "Collins", "Davis",
    "Deborah", "Donna", "Dorothy", "Edwards", "Elizabeth", "Evans", "Garcia",
    "Gonzalez", "Green", "Hall", "Harris", "Helen", "Hernandez", "Hill",
    "Jackson", "Jennifer", "Johnson", "Jones", "Karen", "Kimberly", "King",
    "Laura", "Lee", "Lewis", "Linda", "Lisa", "Lopez", "Margaret", "Maria",
    "Martin", "Martinez", "Mary", "Michelle", "Miller", "Mitchell", "Moore",
    "Nancy", "Nelson", "Parker", "Patricia", "Perez", "Phillips", "Roberts",
    "Robinson", "Rodriguez", "Ruth", "Sandra", "Sarah", "Scott", "Sharon",
    "Smith", "Susan", "Taylor", "Thomas", "Thompson", "Turner", "Walker",
    "White", "Williams", "Wilson", "Wright", "Young",
)

LASTNAMES = (
    "Allen", "Anderson", "Angelo", "Baker", "Bell", "Boulstridge", "Bungard",
    "Bursnell", "Cabrera", "Carlisle", "Carlisle", "Cart", "Chaisty", "Clark",
    "Clayworth", "Colchester", "Cooper", "Darlington", "Davis", "Denial",
    "Derby", "Dissanayake", "Domville", "Dorchester", "Dua", "Dudley",
    "Dundee", "Dundee", "Durham", "Edeson", "Galashiels", "Galashiels",
    "Galashiels", "Garrott", "Gaspar", "Gauge", "Gelson", "Gloucester",
    "Happer", "Harris", "Harrison", "Harrow", "Hawa", "Helling",
    "Hollingberry", "Howsham", "Huddersfield", "Husher", "Ipswich", "James",
    "Khambaita", "Kilmarnok", "King", "Kinlan", "Le", "Leatherby", "Lee",
    "Leicester", "Lerwick", "Lerwick", "Lerwick", "Lincoln", "Llandrindod",
    "Llandrindod", "Llandudno", "Llandudno", "Llandudno", "Llandudno",
    "Llandudno", "London", "Lowsley", "Mardling", "Martin", "McCalman",
    "McKiddie", "McQuillen", "Meath", "Mitchell", "Moore", "Morgan", "Morris",
    "Mustow", "Nana", "Newcastle", "Newport", "Norwich", "Norwich", "Oldham",
    "Parker", "Patel", "Pepall", "Perdue", "Phillips", "Ravensdale", "Rukin",
    "Selvaratnam", "Shelsher", "Shrewsbury", "Silsbury", "Smih", "Southway",
    "Sunderland", "Swansea", "Swansea", "Swansea", "Swansea", "Swansea",
    "Taunton", "Upadhyad", "Valji", "Virji", "Wadd", "Wakefield", "Walsall",
    "Ward", "Watson", "Weild", "Wigan", "Witte", "Wolverhampton", "York",
)

COUNTRIES = (
    "Afghanistan", "Algeria", "Argentina", "Canada", "Colombia", "Ghana",
    "Iraq", "Kenya", "Malaysia", "Morocco", "Mozambique", "Nepal", "Peru",
    "Poland", "Sudan", "Uganda", "Ukraine", "Uzbekistan", "Venezuela", "Yemen",
    'Bangladesh', 'Brazil', 'Burma', 'China', 'Egypt', 'Ethiopia', 'France',
    'Germany', 'India', 'Indonesia', 'Iran', 'Italy', 'Japan', 'Mexico',
    'Nigeria', 'Pakistan', 'Philippines', 'Russia', 'South Africa', 'Spain',
    'Tanzania', 'Thailand', 'Turkey', 'United Kingdom', 'United States',
    'Vietnam',
)

COUNTRY_CODES = (
    'cn', 'in', 'id', 'de', 'el', 'en', 'es', 'fr', 'it', 'pt', 'ru', 'ua'
)

CITY_PREFIXIES = ("North", "East", "West", "South", "New", "Lake", "Port")

CITY_SUFFIXIES = (
    "town", "ton", "land", "ville", "berg", "burgh", "borough", "bury", "view",
    "port", "mouth", "stad", "furt", "chester", "mouth", "fort", "haven",
    "side", "shire"
)

CITIES = (
    "Los Angeles", "Bangkok", "Beijing", "Bogota", "Buenos Aires", "Cairo",
    "Delhi", "Dhaka", "Guangzhou", "Istanbul", "Jakarta", "Karachi", "Kolkata",
    "Lagos", "London", "Manila", "Mexico City", "Moscow", "Mumbai",
    "New York City", "Osaka", "Rio de Janeiro", "Sao Paulo", "Seoul",
    "Shanghai", "Tianjin", "Tokyo"
)

LOREM_CHOICES = (
    "alias", "consequatur", "aut", "perferendis", "sit", "voluptatem",
    "accusantium", "doloremque", "aperiam", "eaque", "ipsa", "quae", "ab",
    "illo", "inventore", "veritatis", "et", "quasi", "architecto", "beatae",
    "vitae", "dicta", "sunt", "explicabo", "aspernatur", "aut", "odit", "aut",
    "fugit", "sed", "quia", "consequuntur", "magni", "dolores", "eos", "qui",
    "ratione", "voluptatem", "sequi", "nesciunt", "neque", "dolorem", "ipsum",
    "quia", "dolor", "sit", "amet", "consectetur", "adipisci", "velit", "sed",
    "quia", "non", "numquam", "eius", "modi", "tempora", "incidunt", "ut",
    "labore", "et", "dolore", "magnam", "aliquam", "quaerat", "voluptatem",
    "ut", "enim", "ad", "minima", "veniam", "quis", "nostrum",
    "exercitationem", "ullam", "corporis", "nemo", "enim", "ipsam",
    "voluptatem", "quia", "voluptas", "sit", "suscipit", "laboriosam", "nisi",
    "ut", "aliquid", "ex", "ea", "commodi", "consequatur", "quis", "autem",
    "vel", "eum", "iure", "reprehenderit", "qui", "in", "ea", "voluptate",
    "velit", "esse", "quam", "nihil", "molestiae", "et", "iusto", "odio",
    "dignissimos", "ducimus", "qui", "blanditiis", "praesentium", "laudantium",
    "totam", "rem", "voluptatum", "deleniti", "atque", "corrupti", "quos",
    "dolores", "et", "quas", "molestias", "excepturi", "sint", "occaecati",
    "cupiditate", "non", "provident", "sed", "ut", "perspiciatis", "unde",
    "omnis", "iste", "natus", "error", "similique", "sunt", "in", "culpa",
    "qui", "officia", "deserunt", "mollitia", "animi", "id", "est", "laborum",
    "et", "dolorum", "fuga", "et", "harum", "quidem", "rerum", "facilis",
    "est", "et", "expedita", "distinctio", "nam", "libero", "tempore", "cum",
    "soluta", "nobis", "est", "eligendi", "optio", "cumque", "nihil",
    "impedit", "quo", "porro", "quisquam", "est", "qui", "minus", "id", "quod",
    "placeat", "facere", "possimus", "omnis", "voluptas", "assumenda", "est",
    "omnis", "dolor", "repellendus", "temporibus", "autem", "quibusdam", "et",
    "aut", "consequatur", "vel", "illum", "qui", "dolorem", "eum", "fugiat",
    "quo", "voluptas", "nulla", "pariatur", "at", "vero", "eos", "et",
    "accusamus", "officiis", "debitis", "aut", "rerum", "necessitatibus",
    "saepe", "eveniet", "ut", "et", "voluptates", "repudiandae", "sint", "et",
    "molestiae", "non", "recusandae", "itaque", "earum", "rerum", "hic",
    "tenetur", "a", "sapiente", "delectus", "ut", "aut", "reiciendis",
    "voluptatibus", "maiores", "doloribus", "asperiores", "repellat", "maxime",
)


HOSTNAMES = (
    "facebook", "google", "youtube", "yahoo", "baidu", "wikipedia", "amazon",
    "qq", "live", "taobao", "blogspot", "linkedin", "twitter", "bing",
    "yandex", "vk", "msn", "ebay", "163", "wordpress", "ask", "weibo", "mail",
    "microsoft", "hao123", "tumblr", "xvideos", "googleusercontent", "fc2"
)

HOSTZONES = (
    "aero", "asia", "biz", "cat", "com", "coop", "info", "int", "jobs", "mobi",
    "museum", "name", "net", "org", "post", "pro", "tel", "travel", "xxx",
    "edu", "gov", "mil", "eu", "ee", "dk", "ch", "bg", "vn", "tw", "tr", "tm",
    "su", "si", "sh", "se", "pt", "ar", "pl", "pe", "nz", "my", "gr", "pm",
    "re", "tf", "wf", "yt", "fi", "br", "ac") + COUNTRY_CODES

USERNAMES = (
    "admin", "akholic", "ass", "bear", "bee", "beep", "blood", "bone", "boots",
    "boss", "boy", "boyscouts", "briefs", "candy", "cat", "cave", "climb",
    "cookie", "cop", "crunching", "daddy", "diller", "dog", "fancy", "gamer",
    "garlic", "gnu", "hot", "jack", "job", "kicker", "kitty", "lemin", "lol",
    "lover", "low", "mix", "mom", "monkey", "nasty", "new", "nut", "nutjob",
    "owner", "park", "peppermint", "pitch", "poor", "potato", "prune",
    "raider", "raiser", "ride", "root", "scull", "shattered", "show", "sleep",
    "sneak", "spamalot", "star", "table", "test", "tips", "user", "ustink",
    "weak"
) + tuple([n.lower() for n in FIRSTNAMES])

GENRES = (
    'general', 'pop', 'dance', 'traditional', 'rock', 'alternative', 'rap',
    'country', 'jazz', 'gospel', 'latin', 'reggae', 'comedy', 'historical',
    'action', 'animation', 'documentary', 'family', 'adventure', 'fantasy',
    'drama', 'crime', 'horror', 'music', 'mystery', 'romance', 'sport',
    'thriller', 'war', 'western', 'fiction', 'epic', 'tragedy', 'parody',
    'pastoral', 'culture', 'art', 'dance', 'drugs', 'social'
)

COMPANY_SYFFIXES = ('LLC', 'Group', 'LTD', 'PLC', 'LLP', 'Corp', 'Inc', 'DBA')

GEOCOORD_MASK = decimal.Decimal('.000001')

STREET_SUFFIXES = (
    'Alley', 'Avenue', 'Branch', 'Bridge', 'Brook', 'Brooks', 'Burg', 'Burgs',
    'Bypass', 'Camp', 'Canyon', 'Cape', 'Causeway', 'Center', 'Centers',
    'Circle', 'Circles', 'Cliff', 'Cliffs', 'Club', 'Common', 'Corner',
    'Corners', 'Course', 'Court', 'Courts', 'Cove', 'Coves', 'Creek',
    'Crescent', 'Crest', 'Crossing', 'Crossroad', 'Curve', 'Dale', 'Dam',
    'Divide', 'Drive', 'Drive', 'Drives', 'Estate', 'Estates', 'Expressway',
    'Extension', 'Extensions', 'Fall', 'Falls', 'Ferry', 'Field', 'Fields',
    'Flat', 'Flats', 'Ford', 'Fords', 'Forest', 'Forge', 'Forges', 'Fork',
    'Forks', 'Fort', 'Freeway', 'Garden', 'Gardens', 'Gateway', 'Glen',
    'Glens', 'Green', 'Greens', 'Grove', 'Groves', 'Harbor', 'Harbors',
    'Haven', 'Heights', 'Highway', 'Hill', 'Hills', 'Hollow', 'Inlet', 'Inlet',
    'Island', 'Island', 'Islands', 'Islands', 'Isle', 'Isle', 'Junction',
    'Junctions', 'Key', 'Keys', 'Knoll', 'Knolls', 'Lake', 'Lakes', 'Land',
    'Landing', 'Lane', 'Light', 'Lights', 'Loaf', 'Lock', 'Locks', 'Locks',
    'Lodge', 'Lodge', 'Loop', 'Mall', 'Manor', 'Manors', 'Meadow', 'Meadows',
    'Mews', 'Mill', 'Mills', 'Mission', 'Mission', 'Motorway', 'Mount',
    'Mountain', 'Mountain', 'Mountains', 'Mountains', 'Neck', 'Orchard',
    'Oval', 'Overpass', 'Park', 'Parks', 'Parkway', 'Parkways', 'Pass',
    'Passage', 'Path', 'Pike', 'Pine', 'Pines', 'Place', 'Plain', 'Plains',
    'Plains', 'Plaza', 'Plaza', 'Point', 'Points', 'Port', 'Ports', 'Ports',
    'Prairie', 'Prairie', 'Radial', 'Ramp', 'Ranch', 'Rapid', 'Rapids', 'Rest',
    'Ridge', 'Ridges', 'River', 'Road', 'Roads', 'Route', 'Row', 'Rue', 'Run',
    'Shoal', 'Shoals', 'Shore', 'Shores', 'Skyway', 'Spring', 'Springs',
    'Springs', 'Spur', 'Spurs', 'Square', 'Squares', 'Station', 'Stravenue',
    'Stream', 'Street', 'Streets', 'Summit', 'Terrace', 'Throughway', 'Trace',
    'Track', 'Trafficway', 'Trail', 'Trail', 'Tunnel', 'Turnpike', 'Underpass',
    'Union', 'Unions', 'Valley', 'Valleys', 'Via', 'Viaduct', 'View', 'Views',
    'Village', 'Villages', 'Ville', 'Vista', 'Walk', 'Walks', 'Wall', 'Way',
    'Ways', 'Well', 'Wells')


def get_firstname(**kwargs):
    """ Get a first name.

    :return str:

    ::

        print get_firstname()  # -> Johnson

    """
    return g.get_choice(FIRSTNAMES)

#: Generator's fabric for :meth:`mixer.fakers.get_firstname`
gen_firstname = g.loop(get_firstname)


def get_lastname(**kwargs):
    """ Get a last name.

    :return str:

    ::

        print get_lastname()  # -> Gaspar

    """
    return g.get_choice(LASTNAMES)

#: Generator's fabric for :meth:`mixer.fakers.get_lastname`
gen_lastname = g.loop(get_lastname)


def get_name(mask=DEFAULT_NAME_MASK, length=100, **kwargs):
    """ Get a full name.

    :return str:

    ::

        print get_name()  # -> Barbara Clayworth

    """
    name = mask.format(firstname=get_firstname(), lastname=get_lastname())
    return name[:length]

#: Generator's fabric for :meth:`mixer.fakers.get_lastname`
gen_name = g.loop(get_name)


def get_country(**kwargs):
    """ Get a country.

    :return str:

    ::

        print get_country()  # -> Italy

    """
    return g.get_choice(COUNTRIES)

#: Generator's fabric for :meth:`mixer.fakers.get_country`
gen_country = g.loop(get_country)


def get_country_code():
    """ Get a country code.

    :return str:

    ::

        print get_country_code()  # -> ru

    """
    return g.get_choice(COUNTRY_CODES)

gen_country_code = g.loop(get_country_code)


def get_city(**kwargs):
    """ Get a city.

    :return str:

    ::

        print get_city()  # -> North Carter

    """
    prf, sfx, city = g.get_choice(CITY_PREFIXIES), g.get_choice(CITY_SUFFIXIES), g.get_choice(CITIES) #noqa

    return g.get_choice((
        city,
        "{0} {1}".format(prf, city),
        "{0} {1}".format(prf, get_firstname()),
        "{0} {1}".format(get_lastname(), sfx),
    ))

#: Generator's fabric for :meth:`mixer.fakers.get_city`
gen_city = g.loop(get_city)


def get_lorem(length=None, **kwargs):
    """ Get a text (based on lorem ipsum.

    :return str:

    ::

        print get_lorem()  # -> atque rerum et aut reiciendis...

    """
    lorem = ' '.join(g.get_choices(LOREM_CHOICES))
    if length:
        lorem = lorem[:length]
        lorem, _ = lorem.rsplit(' ', 1)
    return lorem

#: Generator's fabric for :meth:`mixer.fakers.get_lorem`
gen_lorem = g.loop(get_lorem)


def get_short_lorem(length=64, **kwargs):
    """ Get a small text (based on lorem ipsum.

    :return str:

    ::

        print get_short_lorem()  # -> atque rerum et aut reiciendis

    """
    lorem = g.get_choice(LOREM_CHOICES)
    while True:
        choice = g.get_choice(LOREM_CHOICES)
        if len(lorem + choice) > length - 1:
            return lorem
        lorem += ' ' + choice

#: Generator's fabric for :meth:`mixer.fakers.get_short_lorem`
gen_short_lorem = g.loop(get_short_lorem)


def get_slug(length=64, **kwargs):
    """ Get a part of URL using human-readable words.

    :returns: Generated string

    ::

        print get_slug()  # -> atque-rerum-et-aut-reiciendis

    """
    return get_short_lorem(length, **kwargs).replace(' ', '-')

#: Generator's fabric for :meth:`mixer.fakers.get_slug`
gen_slug = g.loop(get_slug)


def get_numerify(template='', symbol='#', **kwargs):
    """ Generate number string from templates.

    :return str:

    ::

        print get_numerify('####-##')  # -> 2345-23

    """
    return ''.join(
        (str(random.randint(0, 10)) if c == '#' else c)
        for c in template
    )

#: Generator's fabric for :meth:`mixer.fakers.get_numerify`
gen_numerify = g.loop(get_numerify)


def get_username(length=100, choices=DEFAULT_USERNAME_MASK_CHOICES, **kwargs):
    """ Get a username.

    :return str:

    ::

        print get_username()  # -> boss1985

    """
    gen = g.gen_choice(USERNAMES)
    params = dict(
        one=next(gen),
        two=next(gen),
        num=g.get_integer(low=1900, high=2020),
    )
    mask = g.get_choice(choices)
    username = mask.format(**params)
    return username[:length]

#: Generator's fabric for :meth:`mixer.fakers.get_username`
gen_username = g.loop(get_username)


def get_simple_username(**kwargs):
    """ Get a simplest username.

    :return str:

    ::

        print get_username()  # -> boss1985

    """
    return get_username(choices=(
        '{one}', '{one}{num}'
    ))

#: Generator's fabric for :meth:`mixer.fakers.get_simple_username`
gen_simple_username = g.loop(get_simple_username)


def get_hostname(host=None, zone=None, **kwargs):
    """ Get a hostname.

    :return str:

    ::

        print get_hostname()  # -> twitter.az

    """
    params = dict(
        host=host or g.get_choice(HOSTNAMES),
        zone=zone or g.get_choice(HOSTZONES)
    )
    return g.get_choice((
        '{host}.{zone}'.format(**params),
        'www.{host}.{zone}'.format(**params)
    ))

#: Generator's fabric for :meth:`mixer.fakers.get_hostname`
gen_hostname = g.loop(get_hostname)


def get_email(username=None, host=None, zone=None, **kwargs):
    """ Get a email.

    :param username: set the username or get it by random if none
    :param host: set the host or get it by random if none
    :param zone: set the zone or get it by random if none

    :return str:

    ::

        print get_email()  # -> team.cool@microsoft.de

    """
    hostname = get_hostname(host, zone)
    if hostname.startswith('www.'):
        hostname = hostname[4:]
    return '{0}@{1}'.format(username or get_username(), hostname)

#: Generator's fabric for :meth:`mixer.fakers.get_email`
gen_email = g.loop(get_email)


def get_ip4(**kwargs):
    """ Get IP4 address.

    :return str:

    ::

        print get_ip4()  # 192.168.1.1

    """
    gen = g.gen_positive_integer(256)
    return '{0}.{1}.{2}.{3}'.format(
        next(gen), next(gen), next(gen), next(gen),
    )

#: Generator's fabric for :meth:`mixer.fakers.get_ip4`
gen_ip4 = g.loop(get_ip4)


def get_url(hostname=None, **kwargs):
    """ Get a URL.

    :return str:

    """
    if hostname is None:
        hostname = get_hostname()

    parts = [hostname]

    parts += g.get_choices(LOREM_CHOICES, g.get_integer(1, 3))

    return '/'.join(parts)

#: Generator's fabric for :meth:`mixer.fakers.get_url`
gen_url = g.loop(get_url)


def get_uuid(**kwargs):
    """ Get a UUID.

    :return str:

    """
    return str(uuid.uuid1())

#: Generator's fabric for :meth:`mixer.fakers.get_uuid`
gen_uuid = g.loop(get_uuid)


def get_phone(template='###-###-###', **kwargs):
    """ Get a phone number.

    :param template: A template for number.
    :return str:

    """
    return get_numerify(template)

#: Generator's fabric for :meth:`mixer.fakers.get_phone`
gen_phone = g.loop(get_phone)


def get_company():
    """ Get a company name.

    :return str:

    """
    return '%s %s' % (get_lastname(), g.get_choice(COMPANY_SYFFIXES))

#: Generator's fabric for :meth:`mixer.fakers.get_company`
gen_company = g.loop(get_company)


def get_latlon():
    """ Get a value simular to latitude (longitude).

    :return float:

    ::

        print get_latlon()  # -> 137.60858

    """
    return float(
        decimal.Decimal(str(g.get_float(-180, 180))).quantize(GEOCOORD_MASK))

#: Generator's fabric for :meth:`mixer.fakers.get_latlon`
gen_latlon = g.loop(get_latlon)


def get_coordinates():
    """ Get a geographic coordinates.

    :return [float, float]:

    ::

        print get_coordinates()  # -> [116.256223, 43.790918]

    """
    return [get_latlon(), get_latlon()]

#: Generator's fabric for :meth:`mixer.fakers.get_coordinates`
gen_coordinates = g.loop(get_coordinates)


def get_genre():
    """ Return random genre.

    :returns: A choosen genre
    ::

        print get_genre()  # -> 'pop'

    """
    return g.get_choice(GENRES)


#: Generator's fabric for :meth:`mixer.fakers.get_genre`
gen_genre = g.loop(get_genre)


def get_street():
    """ Generate street name. """
    params = dict(
        first_name=get_firstname(),
        last_name=get_lastname(),
        suffix=g.get_choice(STREET_SUFFIXES),
    )

    return g.get_choice((
        '{first_name} {suffix}'.format(**params),
        '{last_name} {suffix}'.format(**params)
    ))

#: Generator's fabric for :meth:`mixer.fakers.get_street`
gen_street = g.loop(get_street)


def get_address():
    """ Generate address. """
    params = dict(
        street=get_street(),
        number1=g.get_small_positive_integer(high=99),
        number2=g.get_integer(high=999, low=100),
    )

    return g.get_choice((
        '{number1} {street}'.format(**params),
        '{number1} {street} Apt. {number2}'.format(**params),
        '{number1} {street} Suite. {number2}'.format(**params)
    ))

#: Generator's fabric for :meth:`mixer.fakers.get_address`
gen_address = g.loop(get_address)

########NEW FILE########
__FILENAME__ = generators
""" Generate random data.

Functions for generation some kind of random datas. You can use
``mixer.generators`` by manual, like this:

::

    from mixer import generators as g

    price = g.get_positive_integer()
    date = g.get_date()

Or you can using shortcut from :class:`mixer.main.Mixer` like this:

::

    mixer.g.get_integer()  # -> 143

"""
import datetime
import random
import decimal
from types import FunctionType, MethodType
from functools import wraps

DEFAULT_STRING_LENGTH = 8
DEFAULT_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'  # noqa
DEFAULT_DATE = datetime.date.today()


def loop(get_func):
    """ Make generator from function.

    :return function: Generator's fabric

    ::

        def get_more(start=1):
            return start + 1

        # Generator's fabric
        f = loop(get_one)

        # Get generator
        g = f(2)

        print [next(g), next(g)]  # -> [3, 3]

    """
    if not isinstance(get_func, (FunctionType, MethodType)):
        r = get_func
        get_func = lambda **kwargs: r

    @wraps(get_func)
    def wrapper(*args, **kwargs):
        while True:
            yield get_func(*args, **kwargs)

    return wrapper


def get_choice(choices=None, **kwargs):
    """ Get a random element from collection.

    :param choices: A collection

    :return value: A random element

    ::

        print get_choice([1, 2, 3])  # -> 1 or 2 or 3

    """
    if not choices:
        return None

    return random.choice(choices)

#: Generator's fabric for :meth:`mixer.generators.get_choice`
gen_choice = loop(get_choice)


def get_choices(choices=None, length=None, **kwargs):
    """ Get a lot of random elements from collection.

    :param choices: A collection
    :param length: Number of elements. By default len(collection).

    :return tuple:

    ::

        print get_choices([1, 2, 3], 2)  # -> [1, 1] or [2, 1] and etc...

    """
    gen = gen_choice(choices)
    if length is None:
        length = len(choices)
    return tuple(next(gen) for _ in range(length))

#: Generator's fabric for :meth:`mixer.generators.get_choices`
gen_choices = loop(get_choices)


def get_date(min_date=(1900, 1, 1), max_date=(2020, 12, 31), **kwargs):
    """ Get a random date.

    :param mix_date: date or date's tuple from
    :param max_date: date or date's tuple to

    :return date:

    ::

        print get_date()  # -> date(1989, 06, 06)

        print get_date((1979, 01, 01), (1981, 01, 01))  # -> date(1980, 04, 03)

    """
    if isinstance(min_date, datetime.date):
        min_date = datetime.datetime(*min_date.timetuple()[:-4])

    if isinstance(max_date, datetime.date):
        max_date = datetime.datetime(*max_date.timetuple()[:-4])

    random_datetime = get_datetime(min_date, max_date)
    return random_datetime.date()

#: Generator's fabric for :meth:`mixer.generators.get_date`
gen_date = loop(get_date)


def get_time(min_time=(0, 0, 0), max_time=(23, 59, 59), **kwargs):
    """ Get a random time.

    :param min_time: `datetime.time` or time's tuple from
    :param max_time: `datetime.time` or time's tuple to

    :return time:

    ::

        print get_time()  # -> time(15, 00)

    """
    if not isinstance(min_time, datetime.time):
        min_time = datetime.time(*min_time)

    if not isinstance(max_time, datetime.time):
        max_time = datetime.time(*max_time)

    random_datetime = get_datetime(
        datetime.datetime.combine(DEFAULT_DATE, min_time),
        datetime.datetime.combine(DEFAULT_DATE, max_time)
    )
    return random_datetime.time()

#: Generator's fabric for :meth:`mixer.generators.get_time`
gen_time = loop(get_time)


def get_datetime(min_datetime=(1900, 1, 1, 0, 0, 0),
                 max_datetime=(2020, 12, 31, 23, 59, 59), **kwargs):
    """ Get a random datetime.

    :param low: datetime or datetime's tuple from
    :param hight: datetime or datetime's tuple to

    :return datetime:

    ::

        print get_datetime()  # -> datetime(1989, 06, 06, 15, 00)

    """
    if not isinstance(min_datetime, datetime.datetime):
        min_datetime = datetime.datetime(*min_datetime)

    if not isinstance(max_datetime, datetime.datetime):
        max_datetime = datetime.datetime(*max_datetime)

    delta = max_datetime - min_datetime
    delta = (delta.days * 24 * 60 * 60 + delta.seconds)
    delta = get_integer(0, delta)

    return min_datetime + datetime.timedelta(seconds=delta)

#: Generator's fabric for :meth:`mixer.generators.get_datetime`
gen_datetime = loop(get_datetime)


def get_integer(low=-2147483647, high=2147483647, **kwargs):
    """ Get a random integer.

    :param low: min value
    :param hight: max value

    :return int:

    ::

        print get_integer()  # -> 4242

    """
    return random.randint(low, high)

#: Generator's fabric for :meth:`mixer.generators.get_integer`
gen_integer = loop(get_integer)


def get_big_integer(**kwargs):
    """ Get a big integer.

    Get integer from -9223372036854775808 to 9223372036854775807.

    :return int:

    ::

        print get_big_integer()  # -> 42424242424242424242424242424242

    """
    return get_integer(low=-9223372036854775808, high=9223372036854775807)

#: Generator's fabric for :meth:`mixer.generators.get_big_integer`
gen_big_integer = loop(get_big_integer)


def get_small_integer(**kwargs):
    """ Get a small integer.

    Get integer from -32768 to 32768.

    :return int:

    ::

        print get_small_integer()  # -> 42

    """
    return get_integer(low=-32768, high=32768)

#: Generator's fabric for :meth:`mixer.generators.get_small_integer`
gen_small_integer = loop(get_small_integer)


def get_positive_integer(high=4294967294, **kwargs):
    """ Get a positive integer.

    :param hight: max value

    :return int:

    ::

        print get_positive_integer()  # -> 42

    """
    return get_integer(low=0, high=high)

#: Generator's fabric for :meth:`mixer.generators.get_positive_integer`
gen_positive_integer = loop(get_positive_integer)


def get_small_positive_integer(high=65536, **kwargs):
    """ Get a small positive integer.

    :return int:

    ::

        print get_small_positive_integer()  # -> 42

    """
    return get_integer(low=0, high=high)

#: Generator's fabric for :meth:`mixer.generators.get_small_positive_integer`
gen_small_positive_integer = loop(get_small_positive_integer)


def get_float(low=-1e10, high=1e10, **kwargs):
    """ Get a random float.

    :return float:

    ::

        print get_float()  # -> 42.42

    """
    return random.uniform(low, high)

#: Generator's fabric for :meth:`mixer.generators.get_float`
gen_float = loop(get_float)


def get_boolean(**kwargs):
    """ Get True or False.

    :return bool:

    ::

        print get_boolean()  # -> True

    """
    return get_choice((True, False))

#: Generator's fabric for :meth:`mixer.generators.get_boolean`
gen_boolean = loop(get_boolean)


def get_null_or_boolean(**kwargs):
    """ Get True, False or None.

    :return bool:

    ::

        print get_null_or_boolean()  # -> None

    """
    return get_choice((True, False, None))

#: Generator's fabric for :meth:`mixer.generators.get_null_or_boolean`
gen_null_or_boolean = loop(get_null_or_boolean)


def get_string(length=DEFAULT_STRING_LENGTH, chars=DEFAULT_CHARS, **kwargs):
    """ Get a random string.

    :return str:

    ::

        print get_string(5)  # -> eK4Jg
        print get_string(5, '01')  # -> 00110

    """
    return ''.join(get_choices(chars, length))

#: Generator's fabric for :meth:`mixer.generators.get_string`
gen_string = loop(get_string)


def get_decimal(i=4, d=2, positive=False, **kwargs):
    """ Get a random decimal.

    :return str:

    ::

        print get_decimal()  # -> decimal.Decimal('42.42')

    """
    i = 10 ** i
    d = 10 ** d
    return decimal.Decimal(
        "{0}.{1}".format(
            get_integer(low=0 if positive else (-i + 1), high=i - 1),
            get_positive_integer(high=d - 1)
        )
    )

#: Generator's fabric for :meth:`mixer.generators.get_decimal`
gen_decimal = loop(get_decimal)


def get_positive_decimal(**kwargs):
    """ Get a positive decimal.

    :return str:

    ::

        print get_positive_decimal()  # -> decimal.Decimal('42.42')

    """
    return get_decimal(positive=True, **kwargs)

#: Generator's fabric for :meth:`mixer.generators.get_positive_decimal`
gen_positive_decimal = loop(get_positive_decimal)


def get_object(**kwargs):
    """ Generate random object.

    :return:

    """
    getter = get_choice(
        (get_integer, get_datetime, get_boolean, get_string))
    return getter()


def get_list(**kwargs):
    """ Generate list of objects.

    :return list:

    ::

        print get_list()  # -> [1, 'sdff', True]

    """
    length = get_small_positive_integer(10)
    return [get_object() for _ in range(length)]

#: Generator's fabric for :meth:`mixer.generators.get_list`
gen_list = loop(get_list)


def get_percent(**kwargs):
    """ Return random value from 0 to 100. """
    return get_integer(low=0, high=100)

#: Generator's fabric for :meth:`mixer.generators.get_percent`
gen_percent = loop(get_percent)


def get_percent_decimal(**kwargs):
    """ Return random value from 0.01 to 1.00. """
    return decimal.Decimal(
        "0.%d" % get_positive_integer(99)
    ) + decimal.Decimal('0.01')

#: Generator's fabric for :meth:`mixer.generators.get_percent_decimal`
gen_percent_decimal = loop(get_percent_decimal)

########NEW FILE########
__FILENAME__ = main
""" Base for custom backends.

mixer.main
~~~~~~~~~~

This module implements the objects generation.

:copyright: 2013 by Kirill Klenov.
:license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import, unicode_literals

import warnings
from types import GeneratorType

import logging
from collections import defaultdict
from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module

from . import generators as g, fakers as f, mix_types as t, _compat as _
from .factory import GenFactory


try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict # noqa


SKIP_VALUE = object()

LOGLEVEL = logging.WARN
LOGGER = logging.getLogger('mixer')
if not LOGGER.handlers and not LOGGER.root.handlers:
    LOGGER.addHandler(logging.StreamHandler())


class _Deffered(object):

    """ Post process value. """

    def __init__(self, value, scheme=None):
        self.value = value
        self.scheme = scheme


class TypeMixerMeta(type):

    """ Cache type mixers by scheme. """

    mixers = dict()

    def __call__(cls, cls_type, mixer=None, factory=None, fake=True):
        backup = cls_type
        try:
            cls_type = cls.__load_cls(cls_type)
            assert cls_type
        except (AttributeError, AssertionError):
            raise ValueError('Invalid scheme: %s' % backup)

        key = (mixer, cls_type, fake, factory)
        if key not in cls.mixers:
            cls.mixers[key] = super(TypeMixerMeta, cls).__call__(
                cls_type, mixer=mixer, factory=factory, fake=fake)

        return cls.mixers[key]

    @staticmethod
    def __load_cls(cls_type):
        if isinstance(cls_type, _.string_types):
            mod, cls_type = cls_type.rsplit('.', 1)
            mod = import_module(mod)
            cls_type = getattr(mod, cls_type)
        return cls_type


class TypeMixer(_.with_metaclass(TypeMixerMeta)):

    """ Generate models. """

    factory = GenFactory

    FAKE = property(lambda s: Mixer.FAKE)
    MIX = property(lambda s: Mixer.MIX)
    RANDOM = property(lambda s: Mixer.RANDOM)
    SELECT = property(lambda s: Mixer.SELECT)
    SKIP = property(lambda s: Mixer.SKIP)

    def __init__(self, cls, mixer=None, factory=None, fake=True):
        self.middlewares = []
        self.__factory = factory or self.factory
        self.__fake = fake
        self.__gen_values = defaultdict(set)
        self.__generators = dict()
        self.__mixer = mixer
        self.__scheme = cls

        self.__fields = OrderedDict(self.__load_fields())

    def __repr__(self):
        return "<TypeMixer {0}>".format(self.__scheme)

    def blend(self, **values):
        """ Generate instance.

        :param **values: Predefined fields
        :return value: a generated value

        """
        defaults = deepcopy(self.__fields)

        # Prepare relations
        for key, params in values.items():
            if '__' in key:
                name, value = key.split('__', 1)
                if name not in defaults:
                    defaults[name] = t.Field(None, name)
                defaults[name].params.update({value: params})
                continue
            defaults[key] = params

        values = dict(
            value.gen_value(self, name, value)
            if isinstance(value, t.ServiceValue)
            else self.get_value(name, value)
            for name, value in defaults.items()
        )

        # Parse MIX and SKIP values
        candidates = list(
            (name, value & values if isinstance(value, t.Mix) else value)
            for name, value in values.items()
            if value is not SKIP_VALUE
        )

        values = list()
        postprocess_values = list()
        for name, value in candidates:
            if isinstance(value, _Deffered):
                postprocess_values.append((name, value))
            else:
                values.append((name, value))

        target = self.populate_target(values)

        # Run registered middlewares
        for middleware in self.middlewares:
            target = middleware(target)

        target = self.postprocess(target, postprocess_values)

        LOGGER.info('Blended: %s [%s]', target, self.__scheme) # noqa
        return target

    def postprocess(self, target, postprocess_values):
        """ Run postprocess code. """
        if self.__mixer:
            target = self.__mixer.postprocess(target)

        for name, deffered in postprocess_values:
            setattr(target, name, deffered.value)

        return target

    def populate_target(self, values):
        """ Populate target with values. """
        target = self.__scheme()
        for name, value in values:
            setattr(target, name, value)
        return target

    def get_value(self, name, value):
        """ Parse field value.

        :return : (name, value) or None

        """
        value = self.__get_value(value)
        return name, value

    def gen_field(self, field):
        """ Generate value by field.

        :param field: Instance of :class:`Field`

        :return : None or (name, value) for later use

        """
        default = self.get_default(field)

        if default is not SKIP_VALUE:
            return self.get_value(field.name, default)

        if not self.is_required(field):
            return field.name, SKIP_VALUE

        unique = self.is_unique(field)
        return self.gen_value(field.name, field, unique=unique)

    def gen_random(self, field_name, random):
        """ Generate random value of field with `field_name`.

        :param field_name: Name of field for generation.
        :param random: Instance of :class:`~mixer.main.Random`.

        :return : None or (name, value) for later use

        """
        if not random.scheme:
            random = deepcopy(self.__fields.get(field_name))

        elif not isinstance(random.scheme, type):
            return self.get_value(
                field_name, g.get_choice(random.choices))

        return self.gen_value(field_name, random, fake=False)

    gen_select = gen_random

    def gen_fake(self, field_name, fake):
        """ Generate fake value of field with `field_name`.

        :param field_name: Name of field for generation.
        :param fake: Instance of :class:`~mixer.main.Fake`.

        :return : None or (name, value) for later use

        """
        if not fake.scheme:
            fake = deepcopy(self.__fields.get(field_name))

        return self.gen_value(field_name, fake, fake=True)

    def gen_value(self, field_name, field, fake=None, unique=False):
        """ Generate values from basic types.

        :return : None or (name, value) for later use

        """
        fake = self.__fake if fake is None else fake
        if field:
            gen = self.get_generator(field, field_name, fake=fake)
        else:
            gen = self.__factory.gen_maker(type(field))()

        try:
            value = next(gen)
        except ValueError:
            value = None

        if unique and value is not SKIP_VALUE:
            counter = 0
            while value in self.__gen_values[field_name]:
                value = next(gen)
                counter += 1
                if counter > 100:
                    raise RuntimeError(
                        "Cannot generate a unique value for %s" % field_name
                    )
            self.__gen_values[field_name].add(value)

        return self.get_value(field_name, value)

    def get_generator(self, field, field_name=None, fake=None):
        """ Get generator for field and cache it.

        :param field: Field for looking a generator
        :param field_name: Name of field for generation
        :param fake: Generate fake data instead of random data.

        :return generator:

        """
        if fake is None:
            fake = self.__fake

        if field.params:
            return self.make_generator(
                field.scheme, field_name, fake, kwargs=field.params)

        key = (field.scheme, field_name, fake)

        if key not in self.__generators:
            self.__generators[key] = self.make_generator(
                field.scheme, field_name, fake, kwargs=field.params)

        return self.__generators[key]

    def make_generator(self, scheme, field_name=None, fake=None, args=None, kwargs=None): # noqa
        """ Make generator for class.

        :param field_class: Class for looking a generator
        :param scheme: Scheme for generation
        :param fake: Generate fake data instead of random data.

        :return generator:

        """
        args = [] if args is None else args
        kwargs = {} if kwargs is None else kwargs

        fabric = self.__factory.gen_maker(scheme, field_name, fake)
        if not fabric:
            return g.loop(self.__class__(
                scheme, mixer=self.__mixer, fake=self.__fake,
                factory=self.__factory).blend)(**kwargs)

        return fabric(*args, **kwargs)

    def register(self, field_name, func, fake=None):
        """ Register function as generator for field.

        :param field_name: Name of field for generation
        :param func: Function for data generation
        :param fake: Generate fake data instead of random data.

        ::

            class Scheme:
                id = str

            def func():
                return 'ID'

            mixer = TypeMixer(Scheme)
            mixer.register('id', func)

            test = mixer.blend()
            test.id == 'id'

        """
        if fake is None:
            fake = self.__fake

        field = self.__fields.get(field_name)
        if field:
            key = (field.scheme, field_name, fake)
            self.__generators[key] = g.loop(func)()

    @staticmethod
    def is_unique(field):
        """ Return True is field's value should be a unique.

        :return bool:

        """
        return False

    @staticmethod
    def is_required(field):
        """ Return True is field's value should be defined.

        :return bool:

        """
        return True

    @staticmethod
    def get_default(field):
        """ Get default value from field.

        :return value:

        """
        return SKIP_VALUE

    @staticmethod
    def guard(**filters):
        """ Look objects in storage.

        :returns: False

        """
        return False

    def __load_fields(self):
        """ Find scheme's fields. """
        for fname in dir(self.__scheme):
            if fname.startswith('_'):
                continue
            prop = getattr(self.__scheme, fname)
            yield fname, t.Field(prop, fname)

    def __get_value(self, value):
        if isinstance(value, GeneratorType):
            return self.__get_value(next(value))

        if callable(value) and not isinstance(value, t.Mix):
            return self.__get_value(value())

        return value


class ProxyMixer:

    """ A Mixer proxy. Using for generate a few objects.

    ::

        mixer.cycle(5).blend(somemodel)

    """

    def __init__(self, mixer, count=5, guards=None):
        self.count = count
        self.mixer = mixer
        self.guards = guards

    def blend(self, scheme, **values):
        """ Call :meth:`Mixer.blend` a few times. And stack results to list.

        :returns: A list of generated objects.

        """
        result = []

        if self.guards:
            return self.mixer._guard(scheme, self.guards, **values) # noqa

        for _ in range(self.count):
            result.append(
                self.mixer.blend(scheme, **values)
            )
        return result

    def __getattr__(self, name):
        raise AttributeError('Use "cycle" only for "blend"')


# Support depricated attributes
class _MetaMixer(type):

    F = property(lambda cls: f)
    FAKE = property(lambda cls: t.Fake())
    G = property(lambda cls: g)
    MIX = property(lambda cls: t.Mix())
    RANDOM = property(lambda cls: t.Random())
    SELECT = property(lambda cls: t.Select())
    SKIP = property(lambda cls: SKIP_VALUE)


class Mixer(_.with_metaclass(_MetaMixer)):

    """ This class is used for integration to one or more applications.

    :param fake: (True) Generate fake data instead of random data.
    :param factory: (:class:`~mixer.main.GenFactory`) Fabric of generators
                        for types values

    ::

        class SomeScheme:
            score = int
            name = str

        mixer = Mixer()
        instance = mixer.blend(SomeScheme)
        print instance.name  # Some like: 'Mike Douglass'

        mixer = Mixer(fake=False)
        instance = mixer.blend(SomeScheme)
        print instance.name  # Some like: 'AKJfdjh3'

    """

    def __getattr__(self, name):
        if name in ['f', 'g', 'fake', 'random', 'mix', 'select']:
            warnings.warn('"mixer.%s" is depricated, use "mixer.%s" instead.'
                          % (name, name.upper()), stacklevel=2)
            name = name.upper()
            return getattr(self, name)
        raise AttributeError("Attribute %s not found." % name)

    @property
    def SKIP(self, *args, **kwargs):
        """ Skip field generation.

        ::
            # Don't generate field 'somefield'
            mixer.blend(SomeScheme, somefield=mixer.skip)

        :returns: SKIP_VALUE

        """
        return SKIP_VALUE

    @property
    def FAKE(self, *args, **kwargs):
        """ Force a fake values. See :class:`~mixer.main.Fake`.

        :returns: Fake object

        """
        return self.__class__.FAKE

    @property
    def RANDOM(self, *args, **kwargs):
        """ Force a random values. See :class:`~mixer.main.Random`.

        :returns: Random object

        """
        return self.__class__.RANDOM

    @property
    def SELECT(self, *args, **kwargs):
        """ Select a data from databases. See :class:`~mixer.main.Select`.

        :returns: Select object

        """
        return self.__class__.SELECT

    @property
    def MIX(self, *args, **kwargs):
        """ Point to a mixed object from future. See :class:`~mixer.main.Mix`.

        :returns: Mix object

        """
        return self.__class__.MIX

    @property
    def F(self):
        """ Shortcut to :mod:`mixer.fakers`.

        ::

            mixer.F.get_name()  # -> Pier Lombardin

        :returns: fakers module

        """
        return self.__class__.F

    @property
    def G(self):
        """ Shortcut to :mod:`mixer.generators`.

        ::

            mixer.G.get_date()  # -> datetime.date(1984, 12, 12)

        :returns: generators module

        """
        return self.__class__.G

    # generator's controller class
    type_mixer_cls = TypeMixer

    def __init__(self, fake=True, factory=None, loglevel=LOGLEVEL,
                 silence=False, **params):
        """Initialize Mixer instance.

        :param fake: (True) Generate fake data instead of random data.
        :param loglevel: ('WARN') Set level for logging
        :param silence: (False) Don't raise any errors if creation was falsed
        :param factory: (:class:`~mixer.main.GenFactory`) A class for
                          generation values for types

        """
        self.params = params
        self.__init_params__(fake=fake, loglevel=loglevel, silence=silence)
        self.__factory = factory

    def __init_params__(self, **params):
        self.params.update(params)
        LOGGER.setLevel(self.params.get('loglevel'))

    def __repr__(self):
        return "<Mixer [{0}]>".format(
            'fake' if self.params.get('fake') else 'rand')

    def blend(self, scheme, **values):
        """Generate instance of `scheme`.

        :param scheme: Scheme class for generation or string with class path.
        :param values: Keyword params with predefined values
        :return value: A generated instance

        ::

            mixer = Mixer()

            mixer.blend(SomeSheme, active=True)
            print scheme.active  # True

            mixer.blend('module.SomeSheme', active=True)
            print scheme.active  # True

        """
        type_mixer = self.get_typemixer(scheme)
        try:
            return type_mixer.blend(**values)
        except Exception as e:
            if self.params.get('silence'):
                return None
            raise type(e)('Mixer (%s): %s' % (scheme, e))

    def get_typemixer(self, scheme):
        """ Return cached typemixer instance.

        :return TypeMixer:

        """
        return self.type_mixer_cls(
            scheme, mixer=self,
            fake=self.params.get('fake'), factory=self.__factory)

    @staticmethod
    def postprocess(target):
        """ Post processing a generated value.

        :return target:

        """
        return target

    @staticmethod # noqa
    def sequence(*args):
        """ Create sequence for predefined values.

        It makes a infinity loop with given function where does increment the
        counter on each iteration.

        :param *args: If method get more one arguments, them make generator
                      from arguments (loop on arguments). If that get one
                      argument and this equal a function, method makes
                      a generator from them. If argument is equal string it
                      should be using as format string.

                      By default function is equal 'lambda x: x'.

        :returns: A generator

        Mixer can uses a generators.
        ::

            gen = (name for name in ['test0', 'test1', 'test2'])
            for counter in range(3):
                mixer.blend(Scheme, name=gen)

        Mixer.sequence is a helper for create generators more easy.

        Generate values from sequence:
        ::

            for _ in range(3):
                mixer.blend(Scheme, name=mixer.sequence('john', 'mike'))


        Make a generator from function:
        ::

            for counter in range(3):
                mixer.blend(Scheme, name=mixer.sequence(
                    lambda c: 'test%s' % c
                ))


        Short format is a python formating string
        ::

            for counter in range(3):
                mixer.blend(Scheme, name=mixer.sequence('test{0}'))

        """
        if len(args) > 1:
            def gen():
                while True:
                    for o in args:
                        yield o
            return gen()

        func = args and args[0] or None
        if isinstance(func, _.string_types):
            func = func.format

        elif func is None:
            func = lambda x: x

        def gen2():
            counter = 0
            while True:
                yield func(counter)
                counter += 1
        return gen2()

    def cycle(self, count=5):
        """ Generate a few objects. Syntastic sugar for cycles.

        :param count: List of objects or integer.
        :returns: ProxyMixer

        ::

            users = mixer.cycle(5).blend('somemodule.User')

            profiles = mixer.cycle(5).blend(
                'somemodule.Profile', user=(user for user in users)

            apples = mixer.cycle(10).blend(
                Apple, title=mixer.sequence('apple_{0}')

        """
        return ProxyMixer(self, count)

    def middleware(self, scheme):
        """ Middleware decorator.

        You can add middleware layers to process generation: ::

        ::

            from mixer.backend.django import mixer

            # Register middleware to model
            @mixer.middleware('auth.user')
            def encrypt_password(user):
                user.set_password('test')
                return user


        You can add several middlewares.
        Each middleware should get one argument (generated value) and return
        them.

        """
        type_mixer = self.type_mixer_cls(
            scheme, mixer=self, fake=self.params.get('fake'),
            factory=self.__factory)

        def wrapper(middleware):
            type_mixer.middlewares.append(middleware)

        return wrapper

    def register(self, scheme, **params):
        """ Manualy register a function as value's generator for class.field.

        :param scheme: Scheme class for generation or string with class path.
        :param params: dict of generators for fields. Keys are field's names.
                        Values is function without argument or objects.

        ::

            class Scheme:
                id = str
                title = str

            def func():
                return 'ID'

            mixer.register(Scheme, {
                'id': func
                'title': 'Always same'
            })

            test = mixer.blend(Scheme)
            test.id == 'ID'
            test.title == 'Always same'

        """
        fake = self.params.get('fake')
        type_mixer = self.type_mixer_cls(
            scheme, mixer=self, fake=fake, factory=self.__factory)

        for field_name, func in params.items():
            type_mixer.register(field_name, func, fake=fake)

            # Double register for RANDOM
            if fake:
                type_mixer.register(field_name, func, fake=False)

    @contextmanager
    def ctx(self, **params):
        """ Redifine params for current mixer on context.

        ::

            with mixer.ctx(commit=False):
                hole = mixer.blend(Hole)
                self.assertTrue(hole)
                self.assertFalse(Hole.objects.count())

        """
        _params = deepcopy(self.params)
        try:
            self.__init_params__(**params)
            yield self
        finally:
            self.__init_params__(**_params)

    def guard(self, **guards):
        """ Abstract method. In some backends used for prevent object creation.

        :returns: A Proxy to mixer

        """
        return ProxyMixer(self, count=1, guards=guards)

    def _guard(self, scheme, guards, **values):
        type_mixer = self.get_typemixer(scheme)
        seek = type_mixer.guard(**guards)
        if seek:
            LOGGER.info('Finded: %s [%s]', seek, type(seek)) # noqa
            return seek

        guards.update(values)
        return self.blend(scheme, **guards)


# Default mixer
mixer = Mixer()

########NEW FILE########
__FILENAME__ = mix_types
""" Mixer types. """

from copy import deepcopy


class BigInteger:

    """ Type for big integers. """

    pass


class EmailString:

    """ Type for emails. """

    pass


class HostnameString:

    """ Type for hostnames. """

    pass


class IP4String:

    """ Type for IP4 addresses. """

    pass


class NullOrBoolean:

    """ Type for None or boolean values. """

    pass


class PositiveDecimal:

    """ Type for positive decimals. """

    pass


class PositiveInteger:

    """ Type for positive integers. """

    pass


class PositiveSmallInteger:

    """ Type for positive small integers. """

    pass


class SmallInteger:

    """ Type for small integers. """

    pass


class Text:

    """ Type for texts. """

    pass


class URL:

    """ Type for URLs. """

    pass


class UUID:

    """ Type for UUIDs. """

    pass


class Mix(object):

    """ Virtual link on the mixed object.

    ::

        mixer = Mixer()

        # here `mixer.MIX` points on a generated `User` instance
        user = mixer.blend(User, username=mixer.MIX.first_name)

        # here `mixer.MIX` points on a generated `Message.author` instance
        message = mixer.blend(Message, author__name=mixer.MIX.login)

        # Mixer mix can get a function
        message = mixer.blend(Message, title=mixer.MIX.author(
            lambda author: 'Author: %s' % author.name
        ))

    """

    def __init__(self, value=None, parent=None):
        self.__value = value
        self.__parent = parent
        self.__func = None

    def __getattr__(self, value):
        return Mix(value, self if self.__value else None)

    def __call__(self, func):
        self.__func = func
        return self

    def __and__(self, values):
        if self.__parent:
            values = self.__parent & values
        if isinstance(values, dict):
            value = values[self.__value]
        else:
            value = getattr(values, self.__value)
        if self.__func:
            return self.__func(value)
        return value

    def __str__(self):
        return '%s/%s' % (self.__value, str(self.__parent or ''))

    def __repr__(self):
        return '<Mix %s>' % str(self)


class ServiceValue(object):

    """ Abstract class for mixer values. """

    def __init__(self, scheme=None, *choices, **params):
        self.scheme = scheme
        self.choices = choices
        self.params = params

    @classmethod
    def __call__(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def gen_value(self, type_mixer, name, field):
        """ Abstract method for value generation. """
        raise NotImplementedError


class Field(ServiceValue):

    """ Set field values.

    By default the mixer generates random or fake a field values by types
    of them. But you can set some values by manual.

    ::

        # Generate a User model
        mixer.blend(User)

        # Generate with some values
        mixer.blend(User, name='John Connor')

    .. note:: Value may be a callable or instance of generator.

    ::

        # Value may be callable
        client = mixer.blend(Client, username=lambda:'callable_value')
        assert client.username == 'callable_value'

        # Value may be a generator
        clients = mixer.cycle(4).blend(
            Client, username=(name for name in ('Piter', 'John')))


    .. seealso:: :class:`mixer.main.Fake`, :class:`mixer.main.Random`,
                 :class:`mixer.main.Select`,
                 :meth:`mixer.main.Mixer.sequence`

    """

    def __init__(self, scheme, name, **params):
        self.name = name
        super(Field, self).__init__(scheme, **params)

    def __deepcopy__(self, memo):
        return Field(self.scheme, self.name, **deepcopy(self.params))

    def gen_value(self, type_mixer, name, field):
        """ Call :meth:`TypeMixer.gen_field`.

        :return value: A generated value

        """
        return type_mixer.gen_field(field)


# Service classes
class Fake(ServiceValue):

    """ Force a `fake` value.

    If you initialized a :class:`~mixer.main.Mixer` with `fake=False` you can
    force a `fake` value for field with this attribute (mixer.FAKE).

    ::

         mixer = Mixer(fake=False)
         user = mixer.blend(User)
         print user.name  # Some like: Fdjw4das

         user = mixer.blend(User, name=mixer.FAKE)
         print user.name  # Some like: Bob Marley

    You can setup a field type for generation of fake value: ::

         user = mixer.blend(User, score=mixer.FAKE(str))
         print user.score  # Some like: Bob Marley

    .. note:: This is also usefull on ORM model generation for filling a fields
              with default values (or null).

    ::

        from mixer.backend.django import mixer

        user = mixer.blend('auth.User', first_name=mixer.FAKE)
        print user.first_name  # Some like: John

    """

    def gen_value(self, type_mixer, name, fake):
        """ Call :meth:`TypeMixer.gen_fake`.

        :return value: A generated value

        """
        return type_mixer.gen_fake(name, fake)


class Random(ServiceValue):

    """ Force a `random` value.

    If you initialized a :class:`~mixer.main.Mixer` by default mixer try to
    fill fields with `fake` data. You can user `mixer.RANDOM` for prevent this
    behaviour for a custom fields.

    ::

         mixer = Mixer()
         user = mixer.blend(User)
         print user.name  # Some like: Bob Marley

         user = mixer.blend(User, name=mixer.RANDOM)
         print user.name  # Some like: Fdjw4das

    You can setup a field type for generation of fake value: ::

         user = mixer.blend(User, score=mixer.RANDOM(str))
         print user.score  # Some like: Fdjw4das

    Or you can get random value from choices: ::

        user = mixer.blend(User, name=mixer.RANDOM('john', 'mike'))
         print user.name  # mike or john

    .. note:: This is also usefull on ORM model generation for randomize fields
              with default values (or null).

    ::

        from mixer.backend.django import mixer

        mixer.blend('auth.User', first_name=mixer.RANDOM)
        print user.first_name  # Some like: Fdjw4das

    """

    def __init__(self, scheme=None, *choices, **params):
        super(Random, self).__init__(scheme, *choices, **params)
        if scheme is not None:
            self.choices += scheme,

    def gen_value(self, type_mixer, name, random):
        """ Call :meth:`TypeMixer.gen_random`.

        :return value: A generated value

        """
        return type_mixer.gen_random(name, random)


class Select(Random):

    """ Select values from database.

    When you generate some ORM models you can set value for related fields
    from database (select by random).

    Example for Django (select user from exists): ::

        from mixer.backend.django import mixer

        mixer.generate(Role, user=mixer.SELECT)


    You can setup a Django or SQLAlchemy filters with `mixer.SELECT`: ::

        from mixer.backend.django import mixer

        mixer.generate(Role, user=mixer.SELECT(
            username='test'
        ))

    """

    def gen_value(self, type_mixer, name, field):
        """ Call :meth:`TypeMixer.gen_random`.

        :return value: A generated value

        """
        return type_mixer.gen_select(name, field)

########NEW FILE########
__FILENAME__ = _compat
""" Compatibility.

    Some py2/py3 compatibility support based on a stripped down
    version of six so we don't have to depend on a specific version
    of it.

    :copyright: (c) 2014 by Armin Ronacher.
    :license: BSD
"""
import sys

PY2 = sys.version_info[0] == 2
_identity = lambda x: x


if not PY2:
    text_type = str
    string_types = (str,)
    integer_types = (int, )

    iterkeys = lambda d: iter(d.keys())
    itervalues = lambda d: iter(d.values())
    iteritems = lambda d: iter(d.items())

    from io import StringIO

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    implements_to_string = _identity

else:
    text_type = unicode
    string_types = (str, unicode)
    integer_types = (int, long)

    iterkeys = lambda d: d.iterkeys()
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()

    from cStringIO import StringIO

    exec('def reraise(tp, value, tb=None):\n raise tp, value, tb')

    def implements_to_string(cls):
        cls.__unicode__ = cls.__str__
        cls.__str__ = lambda x: x.__unicode__().encode('utf-8')
        return cls


def with_metaclass(meta, *bases):
    # This requires a bit of explanation: the basic idea is to make a
    # dummy metaclass for one level of class instantiation that replaces
    # itself with the actual metaclass.  Because of internal type checks
    # we also need to make sure that we downgrade the custom metaclass
    # for one level to something closer to type (that's why __call__ and
    # __init__ comes back from type etc.).
    #
    # This has the advantage over six.with_metaclass in that it does not
    # introduce dummy classes into the final MRO.
    class metaclass(meta):
        __call__ = type.__call__
        __init__ = type.__init__
        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)
    return metaclass('temporary_class', None, {})


# Certain versions of pypy have a bug where clearing the exception stack
# breaks the __exit__ function in a very peculiar way.  This is currently
# true for pypy 2.2.1 for instance.  The second level of exception blocks
# is necessary because pypy seems to forget to check if an exception
# happend until the next bytecode instruction?
BROKEN_PYPY_CTXMGR_EXIT = False
if hasattr(sys, 'pypy_version_info'):
    class _Mgr(object):
        def __enter__(self):
            return self
        def __exit__(self, *args):
            sys.exc_clear()
    try:
        try:
            with _Mgr():
                raise AssertionError()
        except:
            raise
    except TypeError:
        BROKEN_PYPY_CTXMGR_EXIT = True
    except AssertionError:
        pass

########NEW FILE########
__FILENAME__ = models
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.django_app.settings')

from django.conf import settings
from django.contrib.contenttypes import generic, models as ct_models

from django.db import models
from django.contrib.auth.models import User


class Customer(User):
    name = models.CharField(max_length=100)


class Rabbit(models.Model):
    title = models.CharField(max_length=16)
    username = models.CharField(max_length=16, unique=True)
    active = models.BooleanField()
    email = models.EmailField()
    text = models.TextField(max_length=512)

    created_at = models.DateField()
    updated_at = models.DateTimeField()

    opened_at = models.TimeField()
    percent = models.FloatField()
    money = models.IntegerField()
    ip = models.IPAddressField()
    picture = models.FileField(upload_to=settings.TMPDIR)

    some_field = models.CommaSeparatedIntegerField(max_length=12)
    funny = models.NullBooleanField(null=False, blank=False)
    slug = models.SlugField()
    speed = models.DecimalField(max_digits=3, decimal_places=1)

    url = models.URLField(null=True, blank=True, default='')

    content_type = models.ForeignKey(ct_models.ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    one2one = models.OneToOneField('django_app.Simple')

    def save(self, **kwargs):
        """ Custom save. """

        if not self.created_at:
            import datetime
            self.created_at = datetime.datetime.now()

        return super(Rabbit, self).save(**kwargs)


class Hole(models.Model):
    title = models.CharField(max_length=16)
    size = models.SmallIntegerField()
    owner = models.ForeignKey(Rabbit)
    rabbits = generic.GenericRelation(Rabbit, related_name='holes')
    # wtf = models.ForeignKey('self')


class Hat(models.Model):
    color = models.CharField(max_length=50, choices=(
        ('RD', 'red'),
        ('GRN', 'green'),
        ('BL', 'blue'),
    ))
    brend = models.CharField(max_length=10, default='wood')
    owner = models.ForeignKey(Rabbit, null=True, blank=True)


class Silk(models.Model):
    color = models.CharField(max_length=20)
    hat = models.ForeignKey(Hat)


class Door(models.Model):
    hole = models.ForeignKey(Hole)
    owner = models.ForeignKey(Rabbit, null=True, blank=True)
    size = models.PositiveIntegerField()


class Number(models.Model):
    doors = models.ManyToManyField(Door)
    wtf = models.ManyToManyField('self')


class ColorNumber(Number):
    color = models.CharField(max_length=20)


class Client(models.Model):
    username = models.CharField(max_length=20)
    city = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    score = models.IntegerField(default=50)


class Message(models.Model):
    content = models.TextField()
    client = models.ForeignKey(Client)


class Tag(models.Model):
    title = models.CharField(max_length=20)
    customer = models.ForeignKey(Customer, blank=True, null=True)
    messages = models.ManyToManyField(Message, null=True, blank=True)


class PointB(models.Model):
    pass


class PointA(models.Model):
    other = models.ManyToManyField("django_app.PointB",
                                   through="django_app.Through")


class Through(models.Model):
    pointas = models.ForeignKey(PointA)
    pointbs = models.ForeignKey(PointB)


class Simple(models.Model):
    value = models.IntegerField()

########NEW FILE########
__FILENAME__ = settings
import tempfile

TMPDIR = tempfile.mkdtemp()

ROOT_URLCONF = 'tests.django_app.urls'

SECRET_KEY = 'KeepMeSecret'

DEBUG=True

MEDIA_ROOT=TMPDIR

DATABASES={
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'USER': '',
        'PASSWORD': '',
        'TEST_CHARSET': 'utf8',
    }
}

INSTALLED_APPS=(
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'tests.django_app',
)

########NEW FILE########
__FILENAME__ = urls

########NEW FILE########
__FILENAME__ = test_auto
from __future__ import absolute_import

try:
    from unittest2 import TestCase
except ImportError:
    from unittest import TestCase


class MixerTestAuto(TestCase):

    def test_main(self):
        from mixer.auto import mixer

        self.assertTrue(mixer)

    def test_django(self):
        from django.core.management import call_command
        from mixer.auto import mixer

        from .django_app.models import Rabbit

        call_command('syncdb', interactive=False)

        rabbit = mixer.blend(Rabbit)
        self.assertTrue(rabbit)

        rabbit = mixer.blend('tests.django_app.models.Rabbit')
        self.assertTrue(rabbit)

        rabbits = mixer.cycle(2).blend(Rabbit)
        self.assertTrue(all(rabbits))

        call_command('flush', interactive=False)

    def test_sqlalchemy(self):
        from mixer.auto import mixer

        from .test_sqlalchemy import User

        user = mixer.blend(User)
        self.assertTrue(user)

        user = mixer.blend('tests.test_sqlalchemy.User')
        self.assertTrue(user)

        users = mixer.cycle(2).blend(User)
        self.assertTrue(all(users))

    def test_mongoengine(self):
        from mixer.backend.mongoengine import mixer as m
        m.params['commit'] = False

        from mixer.auto import mixer

        from .test_mongoengine import User

        user = mixer.blend(User)
        self.assertTrue(user)

        user = mixer.blend('tests.test_mongoengine.User')
        self.assertTrue(user)

        users = mixer.cycle(2).blend(User)
        self.assertTrue(all(users))

########NEW FILE########
__FILENAME__ = test_django
from __future__ import absolute_import

import datetime

import pytest
from django.core.management import call_command

from .django_app.models import (
    Rabbit, models, Hole, Door, Customer, Simple, Client)
from mixer.backend.django import Mixer


@pytest.fixture(autouse=True)
def mixer(request):
    call_command('syncdb', interactive=False, verbosity=0)
    request.addfinalizer(lambda: call_command(
        'flush', interactive=False, verbosity=0))
    return Mixer()


def test_base():
    from mixer.backend.django import mixer

    simple = mixer.blend('django_app.simple')
    assert isinstance(simple.value, int)


def test_fields(mixer):
    rabbit = mixer.blend('django_app.rabbit')

    assert isinstance(rabbit, Rabbit)
    assert rabbit.id
    assert rabbit.pk
    assert rabbit.pk == 1
    assert len(rabbit.title) <= 16
    assert isinstance(rabbit.active, bool)
    assert isinstance(rabbit.created_at, datetime.date)
    assert isinstance(rabbit.updated_at, datetime.datetime)
    assert isinstance(rabbit.opened_at, datetime.time)
    assert '@' in rabbit.email
    assert rabbit.speed
    assert rabbit.text
    assert len(rabbit.text) <= 512
    assert rabbit.picture.read() == b'pylama\n'

    rabbit = mixer.blend('rabbit')
    assert rabbit


def test_random_fields():
    mixer = Mixer(fake=False)

    hat = mixer.blend('django_app.hat', color=mixer.RANDOM)
    assert hat.color in ('RD', 'GRN', 'BL')


def test_custom(mixer):
    mixer.register(
        Rabbit,
        title=lambda: 'Mr. Rabbit',
        speed=lambda: mixer.G.get_small_positive_integer(99))

    rabbit = mixer.blend(Rabbit, speed=mixer.RANDOM)
    assert isinstance(rabbit.speed, int)
    assert rabbit.title == 'Mr. Rabbit'

    from mixer.backend.django import GenFactory

    def getter(*args, **kwargs):
        return "Always same"

    class MyFactory(GenFactory):
        generators = {models.CharField: getter}

    fabric = MyFactory.gen_maker(models.CharField)
    assert next(fabric()) == "Always same"

    mixer = Mixer(factory=MyFactory, fake=False)
    assert mixer._Mixer__factory == MyFactory

    test = mixer.blend(Rabbit)
    assert test.title == "Always same"

    @mixer.middleware('auth.user')
    def encrypt_password(user): # noqa
        user.set_password(user.password)
        return user

    user = mixer.blend('auth.User', password='test')
    assert user.check_password('test')

    user = user.__class__.objects.get(pk=user.pk)
    assert user.check_password('test')


def test_select(mixer):
    mixer.cycle(3).blend(Rabbit)
    hole = mixer.blend(Hole, rabbit=mixer.SELECT)
    assert not hole.rabbit

    rabbits = Rabbit.objects.all()
    hole = mixer.blend(Hole, owner=mixer.SELECT)
    assert hole.owner in rabbits

    rabbit = rabbits[0]
    hole = mixer.blend(Hole, owner=mixer.SELECT(email=rabbit.email))
    assert hole.owner == rabbit


def test_relation(mixer):
    hat = mixer.blend('django_app.hat')
    assert not hat.owner

    silk = mixer.blend('django_app.silk')
    assert not silk.hat.owner

    silk = mixer.blend('django_app.silk', hat__owner__title='booble')
    assert silk.hat.owner
    assert silk.hat.owner.title == 'booble'

    door = mixer.blend('django_app.door', hole__title='flash', hole__size=244)
    assert door.hole.owner
    assert door.hole.title == 'flash'
    assert door.hole.size == 244

    door = mixer.blend('django_app.door')
    assert door.hole.title != 'flash'

    num = mixer.blend('django_app.number', doors=[door])
    assert num.doors.get() == door

    num = mixer.blend('django_app.number')
    assert num.doors.count() == 0

    num = mixer.blend('django_app.number', doors__size=42)
    assert num.doors.all()[0].size == 42

    tag = mixer.blend('django_app.tag', customer=mixer.RANDOM)
    assert tag.customer


def test_many_to_many_through(mixer):
    pointa = mixer.blend('django_app.pointa', other=mixer.RANDOM)
    assert pointa.other.all()

    pointb = mixer.blend('pointb')
    pointa = mixer.blend('pointa', other=pointb)
    assert list(pointa.other.all()) == [pointb]


def test_random(mixer):
    user = mixer.blend(
        'auth.User', username=mixer.RANDOM('mixer', 'its', 'fun'))
    assert user.username in ('mixer', 'its', 'fun')

    rabbit = mixer.blend(Rabbit, url=mixer.RANDOM)
    assert '/' in rabbit.url


def test_mix(mixer):
    test = mixer.blend(Rabbit, title=mixer.MIX.username)
    assert test.title == test.username

    test = Rabbit.objects.get(pk=test.pk)
    assert test.title == test.username

    test = mixer.blend(Hole, title=mixer.MIX.owner.title)
    assert test.title == test.owner.title

    test = mixer.blend(Door, hole__title=mixer.MIX.owner.title)
    assert test.hole.title == test.hole.owner.title

    test = mixer.blend(Door, hole__title=mixer.MIX.owner.username(
        lambda t: t + 's hole'
    ))
    assert test.hole.owner.username in test.hole.title
    assert 's hole' in test.hole.title

    test = mixer.blend(Door, owner=mixer.MIX.hole.owner)
    assert test.owner == test.hole.owner


def test_contrib(mixer):
    from django.db import connection
    _ = connection.connection.total_changes
    assert mixer.blend('auth.user')
    assert connection.connection.total_changes - _ == 1

    _ = connection.connection.total_changes
    assert mixer.blend(Customer)
    assert connection.connection.total_changes - _ == 2


def test_invalid_scheme(mixer):
    with pytest.raises(ValueError):
        mixer.blend('django_app.Unknown')


def test_invalid_relation(mixer):
    with pytest.raises(ValueError) as e:
        mixer.blend('django_app.Hole', unknown__test=1)
    assert str(e.value).startswith('Mixer (django_app.Hole):')


def test_ctx(mixer):

    with mixer.ctx(commit=False):
        hole = mixer.blend(Hole)
        assert hole
        assert not Hole.objects.count()

    with mixer.ctx(commit=True):
        hole = mixer.blend(Hole)
        assert hole
        assert Hole.objects.count()


def test_skip(mixer):
    rabbit = mixer.blend(Rabbit, created_at=mixer.SKIP, title=mixer.SKIP)
    assert rabbit.created_at
    assert not rabbit.title


def test_guard(mixer):
    r1 = mixer.guard(username='maxi').blend(Rabbit)
    r2 = mixer.guard(username='maxi').blend(Rabbit)
    assert r1
    assert r1 == r2


def test_generic(mixer):
    rabbit = mixer.blend(Rabbit)
    assert rabbit.content_type
    assert rabbit.content_type.model_class()

    obj = mixer.blend(Simple)
    with mixer.ctx(loglevel='DEBUG'):
        rabbit = mixer.blend(Rabbit, content_object=obj)
    assert rabbit.content_object == obj
    assert rabbit.object_id == obj.pk
    assert rabbit.content_type.model_class() == Simple


def test_deffered(mixer):
    simples = mixer.cycle(3).blend(Simple)
    rabbits = mixer.cycle(3).blend(
        Rabbit, content_object=(s for s in simples)
    )
    assert rabbits

    rabbit = rabbits[0]
    rabbit = rabbit.__class__.objects.get(pk=rabbit.pk)
    assert rabbit.content_object


def test_unique(mixer):
    for _ in range(100):
        mixer.blend(Client)

########NEW FILE########
__FILENAME__ = test_flask
from __future__ import absolute_import

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy, _SessionSignalEvents


try:
    from unittest2 import TestCase
except ImportError:
    from unittest import TestCase

# Monkey patching for flask-sqlalchemy <= 1.0 (disable events)
_SessionSignalEvents.session_signal_before_commit = staticmethod(lambda s: s)
_SessionSignalEvents.session_signal_after_commit = staticmethod(lambda s: s)


db = SQLAlchemy()

usermessages = db.Table(
    'users_usermessages',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('message_id', db.Integer, db.ForeignKey('message.id'))
)


class Profile(db.Model):
    __tablename__ = 'profile'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    user = db.relationship("User", uselist=False, backref="profile")


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.SmallInteger, default=50, nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)
    username = db.Column(db.String(20), nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey(
        'profile.id'), nullable=False)

    messages = db.relationship(
        "Message", secondary=usermessages, backref="users")


class Role(db.Model):
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)

    user = db.relation(User)


class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)


class Node(db.Model):
    __tablename__ = 'node'
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('node.id'))
    children = db.relation(
        'Node',
        cascade='all',
        backref=db.backref('parent', remote_side='Node.id'))


class MixerTestFlask(TestCase):

    def setUp(self):
        from flask import Flask

        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        db.init_app(self.app)

    def test_base(self):
        from mixer.backend.flask import Mixer

        mixer = Mixer(commit=True)
        mixer.init_app(self.app)

        with self.app.test_request_context():
            db.create_all()

            node = mixer.blend('tests.test_flask.Node')
            self.assertTrue(node.id)
            self.assertFalse(node.parent)

            role = mixer.blend('tests.test_flask.Role')
            self.assertTrue(role.user)
            self.assertEqual(role.user_id, role.user.id)

            user = mixer.blend(User)
            self.assertTrue(user.id)
            self.assertTrue(user.username)
            self.assertEqual(user.score, 50)
            self.assertTrue(user.created_at)
            self.assertTrue(user.profile)
            self.assertEqual(user.profile.user, user)

            user = mixer.blend(User, username='test')
            self.assertEqual(user.username, 'test')

            role = mixer.blend(
                'tests.test_flask.Role', user__username='test2')
            self.assertEqual(role.user.username, 'test2')

            users = User.query.all()
            role = mixer.blend('tests.test_flask.Role', user=mixer.SELECT)
            self.assertTrue(role.user in users)

            role = mixer.blend('tests.test_flask.Role', user=mixer.RANDOM)
            self.assertTrue(role.user)

            profile = mixer.blend('tests.test_flask.Profile')
            user = mixer.blend(User, profile=profile)
            self.assertEqual(user.profile, profile)

            user = mixer.blend(User, score=mixer.RANDOM)
            self.assertNotEqual(user.score, 50)

            user = mixer.blend(User, username=lambda: 'callable_value')
            self.assertEqual(user.username, 'callable_value')

    def test_default_mixer(self):
        from mixer.backend.flask import mixer

        test = mixer.blend(User)
        self.assertTrue(test.username)

# lint_ignore=F0401

########NEW FILE########
__FILENAME__ = test_main
""" Test mixer base functionality. """
import datetime

import pytest
from decimal import Decimal

from mixer.main import Mixer, TypeMixer


class Test:

    """ Model scheme for base tests. """

    one = int
    two = int
    name = str
    title = str
    body = str
    price = Decimal
    choices = list
    parts = set
    scheme = dict


def test_generators():
    """ Test random generators. """
    from mixer import generators as g

    test = next(g.gen_choice((1, 2, 3)))
    assert test in (1, 2, 3)

    test = next(g.gen_date())
    assert isinstance(test, datetime.date)

    min_date, max_date = (2010, 1, 1), (2011, 1, 1)
    test = next(g.gen_date(min_date, max_date))
    assert 2010 <= test.year <= 2011

    test = next(g.gen_date(
        datetime.date(*min_date), datetime.date(*max_date)))
    assert 2010 <= test.year <= 2011

    test = next(g.gen_time())
    assert isinstance(test, datetime.time)

    min_time, max_time = (14, 30), (15, 30)
    test = next(g.gen_time(min_time, max_time))
    assert 14 <= test.hour <= 15

    test = next(g.gen_time(
        datetime.time(*min_time), datetime.time(*max_time)))
    assert 14 <= test.hour <= 15

    test = next(g.gen_datetime())
    assert isinstance(test, datetime.datetime)

    test = next(g.gen_integer())
    assert -2147483647 <= test < 2147483647

    test = next(g.gen_big_integer())
    assert -9223372036854775808 <= test < 9223372036854775808

    test = next(g.gen_small_integer())
    assert -32768 <= test < 32768

    test = next(g.gen_positive_integer())
    assert test >= 0

    test = next(g.gen_small_positive_integer())
    assert test >= 0

    test = next(g.gen_float())
    assert test

    test = next(g.gen_boolean())
    assert test in (True, False)

    test = next(g.gen_string())
    assert test

    test = next(g.gen_decimal())
    assert test

    test = next(g.gen_positive_decimal())
    assert test

    test = next(g.gen_positive_decimal(i=2))
    assert test < 100

    test = next(g.gen_percent())
    assert 0 <= test <= 100

    test = next(g.gen_percent_decimal())
    assert Decimal('0.01') <= test <= Decimal('1.00')


def test_fakers():
    """ Test default fakers. """
    from mixer import fakers as f

    test = next(f.gen_name())
    assert test

    test = next(f.gen_city())
    assert test

    test = next(f.gen_lorem(length=30))
    assert len(test) <= 30

    test = next(f.gen_numerify('##-####'))
    assert test

    test = next(f.gen_username(length=50))
    assert test

    test = next(f.gen_simple_username(length=50))
    assert test

    test = next(f.gen_hostname())
    assert test

    test = next(f.gen_email())
    assert test

    test = next(f.gen_email(host='gmail'))
    assert 'gmail' in test

    test = next(f.gen_ip4())
    assert '.' in test

    test = next(f.gen_url())
    assert '/' in test

    test = next(f.gen_uuid())
    assert '-' in test

    test = next(f.gen_phone())
    assert '-' in test

    test = next(f.gen_company())
    assert test

    test = next(f.gen_latlon())
    assert test

    test = next(f.gen_coordinates())
    assert test

    test = next(f.gen_city())
    assert test

    test = next(f.gen_genre())
    assert test

    test = next(f.gen_short_lorem())
    assert test

    test = next(f.gen_slug())
    assert test

    test = next(f.gen_street())
    assert test

    test = next(f.gen_address())
    assert test


def test_factory():
    """ Test base generator's factory. """
    from mixer.main import GenFactory

    g = GenFactory()
    test = g.gen_maker(int)()
    assert -2147483647 <= next(test) < 2147483647

    test = g.gen_maker(bool)()
    assert next(test) in (True, False)


def test_typemixer_meta():
    """ Tests that typemixer is a singleton for current class. """
    mixer1 = TypeMixer(Test)
    mixer2 = TypeMixer(Test, fake=False)
    mixer3 = TypeMixer(Test, fake=False)

    assert mixer1 is not mixer2
    assert mixer2 is mixer3


def test_typemixer():

    class Scheme:
        id = int
        name = str
        money = int
        male = bool
        prop = Test

    mixer = TypeMixer(Scheme)
    test = mixer.blend(prop__two=2, prop__one=1, prop__name='sigil', name='RJ')
    assert test.male in (True, False)
    assert test.name == 'RJ'
    assert test.prop.two == 2
    assert test.prop.name == 'sigil'

    test = mixer.blend(prop__two=4, unknown=lambda: '?')
    assert test.prop.two == 4
    assert test.unknown == '?'


def test_fake():
    from mixer.main import mixer

    test = mixer.blend(Test, name=mixer.FAKE, title=mixer.FAKE)
    assert ' ' in test.name
    assert ' ' in test.title

    test = mixer.blend(Test, name=mixer.FAKE(bool))
    assert test.name in (True, False)


def test_random():
    from mixer._compat import string_types

    mixer = TypeMixer(Test)
    test = mixer.blend(name=mixer.RANDOM)
    assert isinstance(test.name, string_types)
    assert ' ' not in test.name

    test = mixer.blend(name=mixer.RANDOM(int))
    assert isinstance(test.name, int)

    names = ['john_', 'kenn_', 'lenny_']
    test = mixer.blend(name=mixer.RANDOM(*names))
    assert test.name in names


def test_mix():
    from mixer.main import mixer

    lama = type('One', tuple(), dict(
        two=int,
        one=type('Two', tuple(), dict(two=2.1))
    ))
    mix = mixer.MIX.one.two
    assert mix & lama == 2.1

    test = mixer.blend(lama, one__two=2.1)
    assert test.one.two == 2.1
    assert test.two != test.one.two

    test = mixer.blend(lama, one__two=2.1, two=mixer.MIX.one.two)
    assert test.two == test.one.two


def test_mixer():
    mixer = Mixer()

    assert Mixer.SKIP == mixer.SKIP
    try:
        Mixer.SKIP = 111
        raise AssertionError('test are failed')
    except AttributeError:
        pass
    try:
        mixer.SKIP = 111
        raise AssertionError('test are failed')
    except AttributeError:
        pass

    gen = ('test{0}'.format(i) for i in range(500))
    test = mixer.blend('tests.test_main.Test', name=gen)
    assert test.name == 'test0'

    name_gen = mixer.sequence(lambda c: 'test' + str(c))
    test = mixer.blend(Test, name=name_gen)
    test = mixer.blend(Test, name=name_gen)
    test = mixer.blend(Test, name=name_gen)
    assert test.name == 'test2'

    name_gen = mixer.sequence('test{0}')
    test = mixer.blend(Test, name=name_gen)
    test = mixer.blend(Test, name=name_gen)
    assert test.name == 'test1'

    name_gen = mixer.sequence()
    test = mixer.blend(Test, name=name_gen)
    test = mixer.blend(Test, name=name_gen)
    assert test.name == 1

    mixer.register('tests.test_main.Test',
                   name='Michel', one=lambda: 'ID', unknown="No error here")
    test = mixer.blend(Test)
    assert test.one == 'ID'
    assert test.name == 'Michel'


def test_mixer_cycle():
    mixer = Mixer()
    test = mixer.cycle(3).blend(Test)
    assert len(test) == 3
    assert test[0].__class__ == Test

    test = mixer.cycle(3).blend(Test, name=mixer.sequence('lama{0}'))
    assert test[2].name == 'lama2'


def test_mixer_default():
    from mixer.main import mixer

    test = mixer.blend(Test)
    assert test.name


def test_invalid_scheme():
    from mixer.main import mixer

    with pytest.raises(ValueError):
        mixer.blend('tests.test_main.Unknown')


def test_sequence():
    from mixer.main import mixer

    gen = mixer.sequence()
    assert next(gen) == 0
    assert next(gen) == 1

    gen = mixer.sequence('test - {0}')
    assert next(gen) == 'test - 0'
    assert next(gen) == 'test - 1'

    gen = mixer.sequence(lambda c: c + 2)
    assert next(gen) == 2
    assert next(gen) == 3

    gen = mixer.sequence(4, 3)
    assert next(gen) == 4
    assert next(gen) == 3
    assert next(gen) == 4


def test_custom():
    mixer = Mixer()

    @mixer.middleware(Test)
    def postprocess(x): # noqa
        x.name += ' Done'
        return x

    mixer.register(
        Test,
        name='Mike',
        one=mixer.G.get_float,
        body=lambda: mixer.G.get_datetime((1980, 1, 1)),
    )

    test = mixer.blend(Test)
    assert test.name == 'Mike Done'
    assert isinstance(test.one, float)
    assert test.body >= datetime.datetime(1980, 1, 1)

    from mixer.main import GenFactory

    class MyFactory(GenFactory):
        generators = {str: lambda: "Always same"}

    mixer = Mixer(factory=MyFactory, fake=False)
    test = mixer.blend(Test)
    assert test.name == "Always same"


def test_ctx():
    from mixer.main import LOGGER

    mixer = Mixer()
    level = LOGGER.level

    with mixer.ctx(loglevel='INFO'):
        mixer.blend(Test)
        assert LOGGER.level != level

    assert LOGGER.level == level


def test_silence():
    mixer = Mixer()

    @mixer.middleware(Test)
    def falsed(test): # noqa
        raise Exception('Unhandled')

    with pytest.raises(Exception):
        mixer.blend(Test)

    with mixer.ctx(silence=True):
        mixer.blend(Test)


def test_guard():
    mixer = Mixer()
    test = mixer.guard().blend(Test)
    assert test


def test_skip():
    mixer = Mixer()
    test = mixer.blend(Test, one=mixer.SKIP)
    assert test.one is not mixer.SKIP
    assert test.one is int

########NEW FILE########
__FILENAME__ = test_mongoengine
from __future__ import absolute_import
from mongoengine import *
import datetime


class User(Document):
    created_at = DateTimeField(default=datetime.datetime.now)
    email = EmailField(required=True)
    first_name = StringField(max_length=50)
    last_name = StringField(max_length=50)


class Comment(EmbeddedDocument):
    content = StringField()
    name = StringField(max_length=120)


class Post(Document):
    title = StringField(max_length=120, required=True)
    author = ReferenceField(User)
    category = StringField(choices=(
        ('S', 'Super'), ('M', 'Medium')), required=True)
    size = StringField(
        max_length=3, choices=('S', 'M', 'L', 'XL', 'XXL'), required=True)
    tags = ListField(StringField(max_length=30))
    comments = ListField(EmbeddedDocumentField(Comment))
    rating = DecimalField(precision=4, required=True)
    url = URLField(required=True)
    uuid = UUIDField(required=True)
    place = PointField()

    meta = {'allow_inheritance': True}


class Bookmark(Document):
    user = ReferenceField(User)
    bookmark = GenericReferenceField()


def test_generators():
    from mixer.backend.mongoengine import get_polygon

    polygon = get_polygon()
    assert polygon['coordinates']


def test_base():
    from mixer.backend.mongoengine import Mixer

    mixer = Mixer(commit=False)
    assert mixer

    now = datetime.datetime.now()

    user = mixer.blend(User)
    assert user.id
    assert user.email
    assert user.created_at
    assert user.created_at >= now


def test_typemixer():
    from mixer.backend.mongoengine import TypeMixer

    tm = TypeMixer(Post)
    post = tm.blend(comments=tm.RANDOM, place=tm.RANDOM)
    assert post.id
    assert post.title
    assert post.tags == []
    assert post.comments
    assert post.comments[0]
    assert isinstance(post.comments[0], Comment)
    assert post.author
    assert post.author.email
    assert post.rating
    assert post.category in ('S', 'M')
    assert '/' in post.url
    assert '-' in post.uuid
    assert 'coordinates' in post.place


def test_relation():
    from mixer.backend.mongoengine import Mixer

    mixer = Mixer(commit=False)

    post = mixer.blend(
        'tests.test_mongoengine.Post', author__username='foo')
    assert post.author.username == 'foo'

    bookmark = mixer.blend(Bookmark)
    assert not bookmark.bookmark

    bookmark = mixer.blend(Bookmark, bookmark=mixer.RANDOM)
    assert bookmark.bookmark


# pylama:ignore=W0401,W0614

########NEW FILE########
__FILENAME__ = test_peewee
from peewee import *


db = SqliteDatabase(':memory:')


class Person(Model):
    name = CharField()
    birthday = DateField()
    is_relative = BooleanField()

    class Meta:
        database = db


class Pet(Model):
    owner = ForeignKeyField(Person, related_name='pets')
    name = CharField()
    animal_type = CharField()

    class Meta:
        database = db


Person.create_table()
Pet.create_table()


def test_backend():
    from mixer.backend.peewee import mixer
    assert mixer


def test_mixer():
    from mixer.backend.peewee import mixer

    person = mixer.blend(Person)
    assert person.name
    assert person.id
    assert person.birthday

    pet = mixer.blend(Pet)
    assert pet.name
    assert pet.animal_type
    assert pet.owner

    with mixer.ctx(commit=True):
        person = mixer.blend(Person)
        assert person.id == 1

########NEW FILE########
__FILENAME__ = test_pony
import sys

import pytest
from decimal import Decimal
from datetime import datetime

pytestmark = pytest.mark.skipif(
    sys.version_info > (2, 8), reason='Pony doesnt support python3')

try:

    from pony.orm import * # noqa

    db = Database("sqlite", ":memory:", create_db=True)

    class Customer(db.Entity):
        address = Required(unicode)
        country = Required(unicode)
        email = Required(unicode, unique=True)
        name = Required(unicode)
        password = Required(unicode)

        cart_items = Set("CartItem")
        orders = Set("Order")

    class Product(db.Entity):
        id = PrimaryKey(int, auto=True)
        name = Required(unicode)
        categories = Set("Category")
        description = Optional(unicode)
        picture = Optional(buffer)
        price = Required(Decimal)
        quantity = Required(int)
        cart_items = Set("CartItem")
        order_items = Set("OrderItem")

    class CartItem(db.Entity):
        quantity = Required(int)
        customer = Required(Customer)
        product = Required(Product)

    class OrderItem(db.Entity):
        quantity = Required(int, default=1)
        price = Required(Decimal)
        order = Required("Order")
        product = Required(Product)
        PrimaryKey(order, product)

    class Order(db.Entity):
        id = PrimaryKey(int, auto=True)
        state = Required(unicode)
        date_created = Required(datetime)
        date_shipped = Optional(datetime)
        date_delivered = Optional(datetime)
        total_price = Required(Decimal)
        customer = Required(Customer)
        items = Set(OrderItem)

    class Category(db.Entity):
        name = Required(unicode, unique=True)
        products = Set(Product)

    db.generate_mapping(create_tables=True)

    def test_backend():
        from mixer.backend.pony import mixer
        assert mixer

    @db_session
    def test_mixer():
        from mixer.backend.pony import mixer

        customer = mixer.blend(Customer)
        assert customer.name
        assert customer.email

        product = mixer.blend(Product)
        assert product.price

        order = mixer.blend(Order)
        assert order.customer

        orderitem = mixer.blend(OrderItem, product=product)
        assert orderitem.quantity == 1
        assert orderitem.order

        order = mixer.blend(Order, customer__name='John Snow')
        assert order.customer.name == 'John Snow'

        with mixer.ctx(commit=True):
            order = mixer.blend(Order)
            assert order.id

except ImportError:
    pass

########NEW FILE########
__FILENAME__ = test_sqlalchemy
from __future__ import absolute_import

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    SmallInteger,
    String,
    create_engine,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relation, sessionmaker, relationship, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from random import randrange
import pytest


ENGINE = create_engine('sqlite:///:memory:')
BASE = declarative_base()
SESSION = scoped_session(sessionmaker(bind=ENGINE))


class Profile(BASE):
    __tablename__ = 'profile'

    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False)

    user = relationship("User", uselist=False, backref="profile")


class User(BASE):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(10), nullable=False)
    role = Column(String(10), default='client', nullable=False)
    score = Column(SmallInteger, default=50, nullable=False)
    updated_at = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    enum = Column(Enum('one', 'two'), nullable=False)
    random = Column(Integer, default=lambda: randrange(993, 995))

    profile_id = Column(Integer, ForeignKey('profile.id'), nullable=False)


class Role(BASE):
    __tablename__ = 'role'

    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)

    user = relation(User)


BASE.metadata.create_all(ENGINE)


@pytest.fixture
def session():
    return SESSION()


def test_typemixer():
    from mixer.backend.sqlalchemy import TypeMixer

    mixer = TypeMixer(User)
    user = mixer.blend()
    assert user
    assert not user.id
    assert user.name
    assert 993 <= user.random < 995
    assert user.score == 50
    assert 2 < len(user.name) <= 10
    assert user.role == 'client'
    assert user.updated_at is None
    assert user.profile
    assert user.profile.user == user
    assert user.enum in ('one', 'two')

    user = mixer.blend(name='John', updated_at=mixer.RANDOM)
    assert user.name == 'John'
    assert user.updated_at in (True, False)

    mixer = TypeMixer('tests.test_sqlalchemy.Role')
    role = mixer.blend()
    assert role.user
    assert role.user_id == role.user.id


def test_mixer(session):
    from mixer.backend.sqlalchemy import Mixer

    mixer = Mixer(session=session, commit=True)
    role = mixer.blend('tests.test_sqlalchemy.Role')
    assert role and role.user

    role = mixer.blend(Role, user__name='test2')
    assert role.user.name == 'test2'

    profile = mixer.blend('tests.test_sqlalchemy.Profile')
    user = mixer.blend(User, profile__name='test')
    assert user.profile.name == 'test'

    user = mixer.blend(User, profile=profile)
    assert user.profile == profile

    user = mixer.blend(User, score=mixer.RANDOM)
    assert user.score != 50

    user = mixer.blend(User, username=lambda: 'callable_value')
    assert user.username == 'callable_value'


def test_select(session):
    from mixer.backend.sqlalchemy import Mixer

    mixer = Mixer(session=session, commit=True)

    users = session.query(User).all()
    role = mixer.blend(Role, user=mixer.SELECT)
    assert role.user in users

    user = users.pop()
    role = mixer.blend(Role, user=mixer.SELECT(User.id == user.id))
    assert user == role.user


def test_random():
    from mixer.backend.sqlalchemy import mixer

    values = ('mixer', 'is', 'fun')
    user = mixer.blend(User, name=mixer.RANDOM(*values))
    assert user.name in values


def test_default_mixer():
    from mixer.backend.sqlalchemy import mixer

    test = mixer.blend(User)
    assert test.name

########NEW FILE########
