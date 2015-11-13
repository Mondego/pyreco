__FILENAME__ = autofixtures
# -*- coding: utf-8 -*-
import autofixture
import string
from datetime import datetime
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.utils import timezone
from autofixture import AutoFixture
from autofixture import generators


class UserFixture(AutoFixture):
    '''
    :class:`UserFixture` is automatically used by default to create new
    ``User`` instances. It uses the following values to assure that you can
    use the generated instances without any modification:

    * ``username`` only contains chars that are allowed by django's auth forms.
    * ``email`` is unique.
    * ``first_name`` and ``last_name`` are single, random words of the lorem
      ipsum text.
    * ``is_staff`` and ``is_superuser`` are always ``False``.
    * ``is_active`` is always ``True``.
    * ``date_joined`` and ``last_login`` are always in the past and it is
      assured that ``date_joined`` will be lower than ``last_login``.
    '''
    class Values(object):
        username = generators.StringGenerator(chars=
            string.ascii_letters + string.digits + '_')
        first_name = generators.LoremWordGenerator(1)
        last_name = generators.LoremWordGenerator(1)
        password = staticmethod(lambda: make_password(None))
        is_active = True
        # don't generate admin users
        is_staff = False
        is_superuser = False
        date_joined = generators.DateTimeGenerator(max_date=timezone.now())
        last_login = generators.DateTimeGenerator(max_date=timezone.now())

    # don't follow permissions and groups
    follow_m2m = False

    def __init__(self, *args, **kwargs):
        '''
        By default the password is set to an unusable value, this makes it
        impossible to login with the generated users. If you want to use for
        example ``autofixture.create_one('auth.User')`` in your unittests to have
        a user instance which you can use to login with the testing client you
        can provide a ``username`` and a ``password`` argument. Then you can do
        something like::

            autofixture.create_one('auth.User', username='foo', password='bar`)
            self.client.login(username='foo', password='bar')
        '''
        self.username = kwargs.pop('username', None)
        self.password = kwargs.pop('password', None)
        super(UserFixture, self).__init__(*args, **kwargs)
        if self.username:
            self.field_values['username'] = generators.StaticGenerator(
                self.username)

    def unique_email(self, model, instance):
        if User.objects.filter(email=instance.email):
            raise autofixture.InvalidConstraint(('email',))

    def prepare_class(self):
        self.add_constraint(self.unique_email)

    def post_process_instance(self, instance, commit):
        # make sure user's last login was not before he joined
        changed = False
        if instance.last_login < instance.date_joined:
            instance.last_login = instance.date_joined
            changed = True
        if self.password:
            instance.set_password(self.password)
            changed = True
        if changed and commit:
            instance.save()
        return instance


autofixture.register(User, UserFixture, fail_silently=True)

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
import inspect
import warnings
from django.db import models
from django.db.models import fields, ImageField
from django.db.models.fields import related
from django.contrib.contenttypes.generic import GenericRelation
from django.utils.datastructures import SortedDict
from django.utils.six import with_metaclass
import autofixture
from autofixture import constraints, generators, signals
from autofixture.values import Values



class CreateInstanceError(Exception):
    pass


class Link(object):
    '''
    Handles logic of following or generating foreignkeys and m2m relations.
    '''
    def __init__(self, fields=None, default=None):
        self.fields = {}
        self.subfields = {}
        self.default = default

        fields = fields or {}
        if fields is True:
            fields = {'ALL': None}
        if not isinstance(fields, dict):
            fields = dict([(v, None) for v in fields])
        for field, value in fields.items():
            try:
                fieldname, subfield = field.split('__', 1)
                self.subfields.setdefault(fieldname, {})[subfield] = value
            except ValueError:
                self.fields[field] = value

    def __getitem__(self, key):
        return self.fields.get(key,
            self.fields.get('ALL', self.default))

    def __iter__(self):
        for field in self.fields:
            yield field
        for key, value in self.subfields.items():
            yield '%s__%s' % (key, value)

    def __contains__(self, value):
        if 'ALL' in self.fields:
            return True
        if value in self.fields:
            return True
        return False

    def get_deep_links(self, field):
        if 'ALL' in self.fields:
            fields = {'ALL': self.fields['ALL']}
        else:
            fields = self.subfields.get(field, {})
            if 'ALL' in fields:
                fields = {'ALL': fields['ALL']}
        return Link(fields, default=self.default)


class AutoFixtureMetaclass(type):
    def __new__(mcs, name, bases, attrs):
        values = Values()
        for base in bases[::-1]:
            values += base.field_values
        values += Values(attrs.pop('Values', {}))
        values += attrs.get('field_values', Values())
        attrs['field_values'] = values
        return super(AutoFixtureMetaclass, mcs).__new__(mcs, name, bases, attrs)


class AutoFixtureBase(object):
    '''
    .. We don't support the following fields yet:

        * ``XMLField``
        * ``FileField``

        Patches are welcome.
    '''
    class IGNORE_FIELD(object):
        pass

    overwrite_defaults = False
    follow_fk = True
    generate_fk = False
    follow_m2m = {'ALL': (1,5)}
    generate_m2m = False

    none_p = 0.2
    tries = 1000

    field_to_generator = SortedDict((
        (fields.BooleanField, generators.BooleanGenerator),
        (fields.NullBooleanField, generators.NullBooleanGenerator),
        (fields.DateTimeField, generators.DateTimeGenerator),
        (fields.DateField, generators.DateGenerator),
        (fields.PositiveSmallIntegerField, generators.PositiveSmallIntegerGenerator),
        (fields.PositiveIntegerField, generators.PositiveIntegerGenerator),
        (fields.SmallIntegerField, generators.SmallIntegerGenerator),
        (fields.IntegerField, generators.IntegerGenerator),
        (fields.FloatField, generators.FloatGenerator),
        (fields.IPAddressField, generators.IPAddressGenerator),
        (fields.TextField, generators.LoremGenerator),
        (fields.TimeField, generators.TimeGenerator),
        (ImageField, generators.ImageGenerator),
    ))

    field_values = Values()

    default_constraints = [
        constraints.unique_constraint,
        constraints.unique_together_constraint]

    def __init__(self, model,
            field_values=None, none_p=None, overwrite_defaults=None,
            constraints=None, follow_fk=None, generate_fk=None,
            follow_m2m=None, generate_m2m=None):
        '''
        Parameters:
            ``model``: A model class which is used to create the test data.

            ``field_values``: A dictionary with field names of ``model`` as
            keys. Values may be static values that are assigned to the field,
            a ``Generator`` instance that generates a value on the fly or a
            callable which takes no arguments and returns the wanted value.

            ``none_p``: The chance (between 0 and 1, 1 equals 100%) to
            assign ``None`` to nullable fields.

            ``overwrite_defaults``: All default values of fields are preserved
            by default. If set to ``True``, default values will be treated
            like any other field.

            ``constraints``: A list of callables. The constraints are used to
            verify if the created model instance may be used. The callable
            gets the actual model as first and the instance as second
            parameter. The instance is not populated yet at this moment.  The
            callable may raise an :exc:`InvalidConstraint` exception to
            indicate which fields violate the constraint.

            ``follow_fk``: A boolean value indicating if foreign keys should be
            set to random, already existing, instances of the related model.

            ``generate_fk``: A boolean which indicates if related models should
            also be created with random values. The *follow_fk* parameter will
            be ignored if *generate_fk* is set to ``True``.

            ``follow_m2m``: A tuple containing minium and maximum of model
            instances that are assigned to ``ManyToManyField``. No new
            instances will be created. Default is (1, 5).  You can ignore
            ``ManyToManyField`` fields by setting this parameter to ``False``.

            ``generate_m2m``: A tuple containing minimum and maximum number of
            model instance that are newly created and assigned to the
            ``ManyToManyField``. Default is ``False`` which disables the
            generation of new related instances. The value of ``follow_m2m``
            will be ignored if this parameter is set.
        '''
        self.model = model
        self.field_values = Values(self.__class__.field_values)
        self.field_values += Values(field_values)
        self.constraints = constraints or []
        if none_p is not None:
            self.none_p = none_p
        if overwrite_defaults is not None:
            self.overwrite_defaults = overwrite_defaults

        if follow_fk is not None:
            self.follow_fk = follow_fk
        if not isinstance(self.follow_fk, Link):
            self.follow_fk = Link(self.follow_fk)

        if generate_fk is not None:
            self.generate_fk = generate_fk
        if not isinstance(self.generate_fk, Link):
            self.generate_fk = Link(self.generate_fk)

        if follow_m2m is not None:
            if not isinstance(follow_m2m, dict):
                if follow_m2m:
                    follow_m2m = Link({'ALL': follow_m2m})
                else:
                    follow_m2m = Link(False)
            self.follow_m2m = follow_m2m
        if not isinstance(self.follow_m2m, Link):
            self.follow_m2m = Link(self.follow_m2m)

        if generate_m2m is not None:
            if not isinstance(generate_m2m, dict):
                if generate_m2m:
                    generate_m2m = Link({'ALL': generate_m2m})
                else:
                    generate_m2m = Link(False)
            self.generate_m2m = generate_m2m
        if not isinstance(self.generate_m2m, Link):
            self.generate_m2m = Link(self.generate_m2m)

        for constraint in self.default_constraints:
            self.add_constraint(constraint)

        self._field_generators = {}

        self.prepare_class()

    def prepare_class(self):
        '''
        This method is called after the :meth:`__init__` method. It has no
        semantic by default.
        '''
        pass

    def add_field_value(self, name, value):
        '''
        Pass a *value* that should be assigned to the field called *name*.
        Thats the same as specifying it in the *field_values* argument of the
        :meth:`constructor <autofixture.base.AutoFixture.__init__>`.
        '''
        self.field_values[name] = value

    def add_constraint(self, constraint):
        '''
        Add a *constraint* to the autofixture.
        '''
        self.constraints.append(constraint)

    def get_generator(self, field):
        '''
        Return a value generator based on the field instance that is passed to
        this method. This function may return ``None`` which means that the
        specified field will be ignored (e.g. if no matching generator was
        found).
        '''
        if isinstance(field, fields.AutoField):
            return None
        if isinstance(field, related.OneToOneField) and field.primary_key:
            return None
        if (
            field.default is not fields.NOT_PROVIDED and
            not self.overwrite_defaults and
            field.name not in self.field_values):
                return None
        kwargs = {}

        if field.name in self.field_values:
            value = self.field_values[field.name]
            if isinstance(value, generators.Generator):
                return value
            elif isinstance(value, AutoFixture):
                return generators.InstanceGenerator(autofixture=value)
            elif callable(value):
                return generators.CallableGenerator(value=value)
            return generators.StaticGenerator(value=value)

        if field.null:
            kwargs['empty_p'] = self.none_p
        if field.choices:
            return generators.ChoicesGenerator(choices=field.choices, **kwargs)
        if isinstance(field, related.ForeignKey):
            # if generate_fk is set, follow_fk is ignored.
            is_self_fk = (field.rel.to().__class__ == self.model)
            if field.name in self.generate_fk and not is_self_fk:
                return generators.InstanceGenerator(
                    autofixture.get(
                        field.rel.to,
                        follow_fk=self.follow_fk.get_deep_links(field.name),
                        generate_fk=self.generate_fk.get_deep_links(field.name)),
                    limit_choices_to=field.rel.limit_choices_to)
            if field.name in self.follow_fk:
                selected = generators.InstanceSelector(
                    field.rel.to,
                    limit_choices_to=field.rel.limit_choices_to)
                if selected.get_value() is not None:
                    return selected
            if field.blank or field.null:
                return generators.NoneGenerator()
            if is_self_fk and not field.null:
                raise CreateInstanceError(
                    u'Cannot resolve self referencing field "%s" to "%s" without null=True' % (
                        field.name,
                        '%s.%s' % (
                            field.rel.to._meta.app_label,
                            field.rel.to._meta.object_name,
                        )
                ))
            raise CreateInstanceError(
                u'Cannot resolve ForeignKey "%s" to "%s". Provide either '
                u'"follow_fk" or "generate_fk" parameters.' % (
                    field.name,
                    '%s.%s' % (
                        field.rel.to._meta.app_label,
                        field.rel.to._meta.object_name,
                    )
            ))
        if isinstance(field, related.ManyToManyField):
            if field.name in self.generate_m2m:
                min_count, max_count = self.generate_m2m[field.name]
                return generators.MultipleInstanceGenerator(
                    autofixture.get(field.rel.to),
                    limit_choices_to=field.rel.limit_choices_to,
                    min_count=min_count,
                    max_count=max_count,
                    **kwargs)
            if field.name in self.follow_m2m:
                min_count, max_count = self.follow_m2m[field.name]
                return generators.InstanceSelector(
                    field.rel.to,
                    limit_choices_to=field.rel.limit_choices_to,
                    min_count=min_count,
                    max_count=max_count,
                    **kwargs)
            if field.blank or field.null:
                return generators.StaticGenerator([])
            raise CreateInstanceError(
                u'Cannot assign instances of "%s" to ManyToManyField "%s". '
                u'Provide either "follow_m2m" or "generate_m2m" argument.' % (
                    '%s.%s' % (
                        field.rel.to._meta.app_label,
                        field.rel.to._meta.object_name,
                    ),
                    field.name,
            ))
        if isinstance(field, fields.FilePathField):
            return generators.FilePathGenerator(
                path=field.path, match=field.match, recursive=field.recursive,
                max_length=field.max_length, **kwargs)
        if isinstance(field, fields.CharField):
            if isinstance(field, fields.SlugField):
                generator = generators.SlugGenerator
            elif isinstance(field, fields.EmailField):
                return generators.EmailGenerator(
                    max_length=min(field.max_length, 30))
            elif isinstance(field, fields.URLField):
                return generators.URLGenerator(
                    max_length=min(field.max_length, 25))
            elif field.max_length > 15:
                return generators.LoremSentenceGenerator(
                    common=False,
                    max_length=field.max_length)
            else:
                generator = generators.StringGenerator
            return generator(max_length=field.max_length)
        if isinstance(field, fields.DecimalField):
            return generators.DecimalGenerator(
                decimal_places=field.decimal_places,
                max_digits=field.max_digits)
        if hasattr(fields, 'BigIntegerField'):
            if isinstance(field, fields.BigIntegerField):
                return generators.IntegerGenerator(
                    min_value=-field.MAX_BIGINT - 1,
                    max_value=field.MAX_BIGINT,
                    **kwargs)
        if isinstance(field, ImageField):
            return generators.ImageGenerator(**kwargs)
        for field_class, generator in self.field_to_generator.items():
            if isinstance(field, field_class):
                return generator(**kwargs)
        return None

    def get_value(self, field):
        '''
        Return a random value that can be assigned to the passed *field*
        instance.
        '''
        if field not in self._field_generators:
            self._field_generators[field] = self.get_generator(field)
        generator = self._field_generators[field]
        if generator is None:
            return self.IGNORE_FIELD
        value = generator()
        return value

    def process_field(self, instance, field):
        value = self.get_value(field)
        if value is self.IGNORE_FIELD:
            return
        setattr(instance, field.name, value)

    def process_m2m(self, instance, field):
        # check django's version number to determine how intermediary models
        # are checked if they are auto created or not.
        auto_created_through_model = False
        through = field.rel.through
        auto_created_through_model = through._meta.auto_created

        if auto_created_through_model:
            return self.process_field(instance, field)
        # if m2m relation has intermediary model:
        #   * only generate relation if 'generate_m2m' is given
        #   * first generate intermediary model and assign a newly created
        #     related model to the foreignkey
        kwargs = {}
        if field.name in self.generate_m2m:
            # get fk to related model on intermediary model
            related_fks = [fk
                for fk in through._meta.fields
                if isinstance(fk, related.ForeignKey) and \
                    fk.rel.to is field.rel.to]
            self_fks = [fk
                for fk in through._meta.fields
                if isinstance(fk, related.ForeignKey) and \
                    fk.rel.to is self.model]
            assert len(related_fks) == 1
            assert len(self_fks) == 1
            related_fk = related_fks[0]
            self_fk = self_fks[0]
            min_count, max_count = self.generate_m2m[field.name]
            intermediary_model = generators.MultipleInstanceGenerator(
                AutoFixture(
                    through,
                    field_values={
                        self_fk.name: instance,
                        related_fk.name: generators.InstanceGenerator(
                            AutoFixture(field.rel.to))
                    }),
                min_count=min_count,
                max_count=max_count,
                **kwargs).generate()

    def check_constrains(self, instance):
        '''
        Return fieldnames which need recalculation.
        '''
        recalc_fields = []
        for constraint in self.constraints:
            try:
                constraint(self.model, instance)
            except constraints.InvalidConstraint as e:
                recalc_fields.extend(e.fields)
        return recalc_fields

    def post_process_instance(self, instance, commit):
        '''
        Overwrite this method to modify the created *instance* before it gets
        returned by the :meth:`create` or :meth:`create_one`.
        It gets the generated *instance* and must return the modified
        instance. The *commit* parameter indicates the *commit* value that the
        user passed into the :meth:`create` method. It defaults to ``True``
        and should be respected, which means if it is set to ``False``, the
        *instance* should not be saved.
        '''
        return instance

    def pre_process_instance(self, instance):
        '''
        Same as :meth:`post_process_instance`, but it is being called before
        saving an *instance*.
        '''
        return instance

    def create_one(self, commit=True):
        '''
        Create and return one model instance. If *commit* is ``False`` the
        instance will not be saved and many to many relations will not be
        processed.

        Subclasses that override ``create_one`` can specify arbitrary keyword
        arguments. They will be passed through by the
        :meth:`autofixture.base.AutoFixture.create` method and the helper
        functions :func:`autofixture.create` and
        :func:`autofixture.create_one`.

        May raise :exc:`CreateInstanceError` if constraints are not satisfied.
        '''
        tries = self.tries
        instance = self.model()
        process = instance._meta.fields
        while process and tries > 0:
            for field in process:
                self.process_field(instance, field)
            process = self.check_constrains(instance)
            tries -= 1
        if tries == 0:
            raise CreateInstanceError(
                u'Cannot solve constraints for "%s", tried %d times. '
                u'Please check value generators or model constraints. '
                u'At least the following fields are involved: %s' % (
                    '%s.%s' % (
                        self.model._meta.app_label,
                        self.model._meta.object_name),
                    self.tries,
                    ', '.join([field.name for field in process]),
            ))

        instance = self.pre_process_instance(instance)

        if commit:
            instance.save()

            #to handle particular case of GenericRelation
            #in Django pre 1.6 it appears in .many_to_many
            many_to_many = [f for f in instance._meta.many_to_many
                            if not isinstance(f, GenericRelation)]
            for field in many_to_many:
                self.process_m2m(instance, field)
        signals.instance_created.send(
            sender=self,
            model=self.model,
            instance=instance,
            committed=commit)

        post_process_kwargs = {}
        if 'commit' in inspect.getargspec(self.post_process_instance).args:
            post_process_kwargs['commit'] = commit
        else:
            warnings.warn(
                "Subclasses of AutoFixture need to provide a `commit` "
                "argument for post_process_instance methods", DeprecationWarning)
        return self.post_process_instance(instance, **post_process_kwargs)

    def create(self, count=1, commit=True, **kwargs):
        '''
        Create and return ``count`` model instances. If *commit* is ``False``
        the instances will not be saved and many to many relations will not be
        processed.

        May raise ``CreateInstanceError`` if constraints are not satisfied.

        The method internally calls :meth:`create_one` to generate instances.
        '''
        object_list = []
        for i in range(count):
            instance = self.create_one(commit=commit, **kwargs)
            object_list.append(instance)
        return object_list

    def iter(self, count=1, commit=True):
        for i in range(count):
            yield self.create_one(commit=commit)

    def __iter__(self):
        yield self.create_one()


class AutoFixture(with_metaclass(AutoFixtureMetaclass, AutoFixtureBase)):
    pass

########NEW FILE########
__FILENAME__ = constraints
# -*- coding: utf-8 -*-


class InvalidConstraint(Exception):
    def __init__(self, fields, *args, **kwargs):
        self.fields = fields
        super(InvalidConstraint, self).__init__(*args, **kwargs)


def unique_constraint(model, instance):
    error_fields = []
    for field in instance._meta.fields:
        if field.unique and not field.primary_key:
            check = {field.name: getattr(instance, field.name)}
            unique = not bool(model._default_manager.filter(**check))
            if not unique:
                error_fields.append(field)
    if error_fields:
        raise InvalidConstraint(error_fields)


def unique_together_constraint(model, instance):
    error_fields = []
    if instance._meta.unique_together:
        for unique_fields in instance._meta.unique_together:
            check = {}
            for field_name in unique_fields:
                if not instance._meta.get_field_by_name(field_name)[0].primary_key:
                    check[field_name] = getattr(instance, field_name)
            unique = not bool(model._default_manager.filter(**check))
            if not unique:
                error_fields.extend(
                    [instance._meta.get_field_by_name(field_name)[0]
                        for field_name in unique_fields])
    if error_fields:
        raise InvalidConstraint(error_fields)

########NEW FILE########
__FILENAME__ = generators
# -*- coding: utf-8 -*-
import datetime
import os
import random
import re
import string
import sys
from decimal import Decimal


if sys.version_info[0] < 3:
    str_ = unicode
else:
    str_ = str


# backporting os.path.relpath, only availabe in python >= 2.6
try:
    relpath = os.path.relpath
except AttributeError:
    def relpath(path, start=os.curdir):
        """Return a relative version of a path"""

        if not path:
            raise ValueError("no path specified")

        start_list = os.path.abspath(start).split(os.path.sep)
        path_list = os.path.abspath(path).split(os.path.sep)

        # Work out how much of the filepath is shared by start and path.
        i = len(os.path.commonprefix([start_list, path_list]))

        rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
        if not rel_list:
            return os.curdir
        return os.path.join(*rel_list)


class Generator(object):
    coerce_type = staticmethod(lambda x: x)
    empty_value = None
    empty_p = 0

    def __init__(self, empty_p=None, coerce=None):
        if empty_p is not None:
            self.empty_p = empty_p
        if coerce:
            self.coerce_type = coerce

    def coerce(self, value):
        return self.coerce_type(value)

    def generate(self):
        raise NotImplementedError

    def get_value(self):
        if random.random() < self.empty_p:
            return self.empty_value
        value = self.generate()
        return self.coerce(value)

    def __call__(self):
        return self.get_value()


class StaticGenerator(Generator):
    def __init__(self, value, *args, **kwargs):
        self.value = value
        super(StaticGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        return self.value


class CallableGenerator(Generator):
    def __init__(self, value, args=None, kwargs=None, *xargs, **xkwargs):
        self.value = value
        self.args = args or ()
        self.kwargs = kwargs or {}
        super(CallableGenerator, self).__init__(*xargs, **xkwargs)

    def generate(self):
        return self.value(*self.args, **self.kwargs)


class NoneGenerator(Generator):
    def generate(self):
        return self.empty_value


class StringGenerator(Generator):
    coerce_type = str_
    singleline_chars = string.ascii_letters + u' '
    multiline_chars = singleline_chars + u'\n'

    def __init__(self, chars=None, multiline=False, min_length=1, max_length=1000, *args, **kwargs):
        assert min_length >= 0
        assert max_length >= 0
        self.min_length = min_length
        self.max_length = max_length
        if chars is None:
            if multiline:
                self.chars = self.multiline_chars
            else:
                self.chars = self.singleline_chars
        else:
            self.chars = chars
        super(StringGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        length = random.randint(self.min_length, self.max_length)
        value = u''
        for x in range(length):
            value += random.choice(self.chars)
        return value


class SlugGenerator(StringGenerator):
    def __init__(self, chars=None, *args, **kwargs):
        if chars is None:
            chars = string.ascii_lowercase + string.digits + '-'
        super(SlugGenerator, self).__init__(chars, multiline=False, *args, **kwargs)


class LoremGenerator(Generator):
    coerce_type = str_
    common = True
    count = 3
    method = 'b'

    def __init__(self, count=None, method=None, common=None, max_length=None, *args, **kwargs):
        if count is not None:
            self.count = count
        if method is not None:
            self.method = method
        if common is not None:
            self.common = common
        self.max_length = max_length
        super(LoremGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        from django.contrib.webdesign.lorem_ipsum import paragraphs, sentence, \
            words
        if self.method == 'w':
            lorem = words(self.count, common=self.common)
        elif self.method == 's':
            lorem = u' '.join([sentence()
                for i in range(self.count)])
        else:
            paras = paragraphs(self.count, common=self.common)
            if self.method == 'p':
                paras = ['<p>%s</p>' % p for p in paras]
            lorem = u'\n\n'.join(paras)
        if self.max_length:
            length = random.randint(round(self.max_length / 10), self.max_length)
            lorem = lorem[:max(1, length)]
        return lorem.strip()

class LoremSentenceGenerator(LoremGenerator):
    method = 's'

class LoremHTMLGenerator(LoremGenerator):
    method = 'p'

class LoremWordGenerator(LoremGenerator):
    count = 7
    method = 'w'


class IntegerGenerator(Generator):
    coerce_type = int
    min_value = - 10 ** 5
    max_value = 10 ** 5

    def __init__(self, min_value=None, max_value=None, *args, **kwargs):
        if min_value is not None:
            self.min_value = min_value
        if max_value is not None:
            self.max_value = max_value
        super(IntegerGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        value = random.randint(self.min_value, self.max_value)
        return value


class SmallIntegerGenerator(IntegerGenerator):
    min_value = -2 ** 7
    max_value = 2 ** 7 - 1


class PositiveIntegerGenerator(IntegerGenerator):
    min_value = 0


class PositiveSmallIntegerGenerator(SmallIntegerGenerator):
    min_value = 0


class FloatGenerator(IntegerGenerator):
    coerce_type = float
    decimal_digits = 1

    def __init__(self, decimal_digits=None, *args, **kwargs):
        if decimal_digits is not None:
            self.decimal_digits = decimal_digits
        super(IntegerGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        value = super(FloatGenerator, self).generate()
        value = float(value)
        if self.decimal_digits:
            digits = random.randint(1, 10 ^ self.decimal_digits) - 1
            digits = float(digits)
            value = value + digits / (10 ^ self.decimal_digits)
        return value


class ChoicesGenerator(Generator):
    def __init__(self, choices=(), values=(), *args, **kwargs):
        assert len(choices) or len(values)
        self.choices = list(choices)
        if not values:
            self.values = [k for k, v in self.choices]
        else:
            self.values = list(values)
        super(ChoicesGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        return random.choice(self.values)


class BooleanGenerator(ChoicesGenerator):
    def __init__(self, none=False, *args, **kwargs):
        values = (True, False)
        if none:
            values = values + (None,)
        super(BooleanGenerator, self).__init__(values=values, *args, **kwargs)


class NullBooleanGenerator(BooleanGenerator):
    def __init__(self, none=True, *args, **kwargs):
        super(NullBooleanGenerator, self).__init__(none=none, *args, **kwargs)


class DateTimeGenerator(Generator):
    def __init__(self, min_date=None, max_date=None, *args, **kwargs):
        from django.utils import timezone
        if min_date is not None:
            self.min_date = min_date
        else:
            self.min_date = timezone.now() - datetime.timedelta(365 * 5)
        if max_date is not None:
            self.max_date = max_date
        else:
            self.max_date = timezone.now() + datetime.timedelta(365 * 1)
        assert self.min_date < self.max_date
        super(DateTimeGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        diff = self.max_date - self.min_date
        seconds = random.randint(0, diff.days * 3600 * 24 + diff.seconds)
        return self.min_date + datetime.timedelta(seconds=seconds)


class DateGenerator(Generator):
    min_date = datetime.date.today() - datetime.timedelta(365 * 5)
    max_date = datetime.date.today() + datetime.timedelta(365 * 1)

    def __init__(self, min_date=None, max_date=None, *args, **kwargs):
        if min_date is not None:
            self.min_date = min_date
        if max_date is not None:
            self.max_date = max_date
        assert self.min_date < self.max_date
        super(DateGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        diff = self.max_date - self.min_date
        days = random.randint(0, diff.days)
        date = self.min_date + datetime.timedelta(days=days)
        return date
        return datetime.date(date.year, date.month, date.day)


class DecimalGenerator(Generator):
    coerce_type = Decimal

    max_digits = 24
    decimal_places = 10

    def __init__(self, max_digits=None, decimal_places=None, *args, **kwargs):
        if max_digits is not None:
            self.max_digits = max_digits
        if decimal_places is not None:
            self.decimal_places = decimal_places
        super(DecimalGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        maxint = 10 ** self.max_digits - 1
        value = (
            Decimal(random.randint(-maxint, maxint)) /
            10 ** self.decimal_places)
        return value


class FirstNameGenerator(Generator):
    """ Generates a first name, either male or female """

    male = [
        'Abraham', 'Adam', 'Anthony', 'Brian', 'Bill', 'Ben', 'Calvin',
        'David', 'Daniel', 'George', 'Henry', 'Isaac', 'Ian', 'Jonathan',
        'Jeremy', 'Jacob', 'John', 'Jerry', 'Joseph', 'James', 'Larry',
        'Michael', 'Mark', 'Paul', 'Peter', 'Phillip', 'Stephen', 'Tony',
        'Titus', 'Trevor', 'Timothy', 'Victor', 'Vincent', 'Winston', 'Walt']
    female = [
        'Abbie', 'Anna', 'Alice', 'Beth', 'Carrie', 'Christina', 'Danielle',
        'Emma', 'Emily', 'Esther', 'Felicia', 'Grace', 'Gloria', 'Helen',
        'Irene', 'Joanne', 'Joyce', 'Jessica', 'Kathy', 'Katie', 'Kelly',
        'Linda', 'Lydia', 'Mandy', 'Mary', 'Olivia', 'Priscilla',
        'Rebecca', 'Rachel', 'Susan', 'Sarah', 'Stacey', 'Vivian']

    def __init__(self, gender=None):
        self.gender = gender
        self.all = self.male + self.female

    def generate(self):
        if self.gender == 'm':
            return random.choice(self.male)
        elif self.gender == 'f':
            return random.choice(self.female)
        else:
            return random.choice(self.all)


class LastNameGenerator(Generator):
    """ Generates a last name """

    surname = [
        'Smith', 'Walker', 'Conroy', 'Stevens', 'Jones', 'Armstrong',
        'Johnson', 'White', 'Stone', 'Strong', 'Olson', 'Lee', 'Forrest',
        'Baker', 'Portman', 'Davis', 'Clark', 'Brown', 'Roberts', 'Ellis',
        'Jackson', 'Marshall', 'Wang', 'Chen', 'Chou', 'Tang', 'Huang', 'Liu',
        'Shih', 'Su', 'Song', 'Yang', 'Chan', 'Tsai', 'Wong', 'Hsu', 'Cheng',
        'Chang', 'Wu', 'Lin', 'Yu', 'Yao', 'Kang', 'Park', 'Kim', 'Choi',
        'Ahn', 'Mujuni']

    def generate(self):
        return random.choice(self.surname)


class EmailGenerator(StringGenerator):
    chars = string.ascii_lowercase

    def __init__(self, chars=None, max_length=30, tlds=None, static_domain=None, *args, **kwargs):
        assert max_length >= 6
        if chars is not None:
            self.chars = chars
        self.tlds = tlds
        self.static_domain = static_domain
        super(EmailGenerator, self).__init__(self.chars, max_length=max_length, *args, **kwargs)

    def generate(self):
        maxl = self.max_length - 2

        if self.static_domain is None:
            if self.tlds:
                tld = random.choice(self.tlds)
            elif maxl > 4:
                tld = StringGenerator(self.chars, min_length=3, max_length=3).generate()
            maxl -= len(tld)
            assert maxl >= 2
        else:
            maxl -= len(self.static_domain)

        name = StringGenerator(self.chars, min_length=1, max_length=maxl-1).generate()
        maxl -= len(name)

        if self.static_domain is None:
            domain = StringGenerator(self.chars, min_length=1, max_length=maxl).generate()
            return '%s@%s.%s' % (name, domain, tld)
        else:
            return '%s@%s' % (name, self.static_domain)


class URLGenerator(StringGenerator):
    chars = string.ascii_lowercase
    protocol = 'http'
    tlds = ()

    def __init__(self, chars=None, max_length=30, protocol=None, tlds=None,
        *args, **kwargs):
        if chars is not None:
            self.chars = chars
        if protocol is not None:
            self.protocol = protocol
        if tlds is not None:
            self.tlds = tlds
        assert max_length > (
            len(self.protocol) + len('://') +
            1 + len('.') +
            max([2] + [len(tld) for tld in self.tlds if tld]))
        super(URLGenerator, self).__init__(
            chars=self.chars, max_length=max_length, *args, **kwargs)

    def generate(self):
        maxl = self.max_length - len(self.protocol) - 4 # len(://) + len(.)
        if self.tlds:
            tld = random.choice(self.tlds)
            maxl -= len(tld)
        else:
            tld_max_length = 3 if maxl >= 5 else 2
            tld = StringGenerator(self.chars,
                min_length=2, max_length=tld_max_length).generate()
            maxl -= len(tld)
        domain = StringGenerator(chars=self.chars, max_length=maxl).generate()
        return u'%s://%s.%s' % (self.protocol, domain, tld)


class IPAddressGenerator(Generator):
    coerce_type = str_

    def generate(self):
        return '.'.join([str_(part) for part in [
            IntegerGenerator(min_value=1, max_value=254).generate(),
            IntegerGenerator(min_value=0, max_value=254).generate(),
            IntegerGenerator(min_value=0, max_value=254).generate(),
            IntegerGenerator(min_value=1, max_value=254).generate(),
        ]])


class TimeGenerator(Generator):
    coerce_type = str_

    def generate(self):
        return u'%02d:%02d:%02d' % (
            random.randint(0,23),
            random.randint(0,59),
            random.randint(0,59),
        )


class FilePathGenerator(Generator):
    coerce_type = str_

    def __init__(self, path, match=None, recursive=False, max_length=None, *args, **kwargs):
        self.path = path
        self.match = match
        self.recursive = recursive
        self.max_length = max_length
        super(FilePathGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        filenames = []
        if self.match:
            match_re = re.compile(self.match)
        if self.recursive:
            for root, dirs, files in os.walk(self.path):
                for f in files:
                    if self.match is None or self.match_re.search(f):
                        f = os.path.join(root, f)
                        filenames.append(f)
        else:
            try:
                for f in os.listdir(self.path):
                    full_file = os.path.join(self.path, f)
                    if os.path.isfile(full_file) and \
                        (self.match is None or match_re.search(f)):
                        filenames.append(full_file)
            except OSError:
                pass
        if self.max_length:
            filenames = [fn for fn in filenames if len(fn) <= self.max_length]
        return random.choice(filenames)


class MediaFilePathGenerator(FilePathGenerator):
    '''
    Generates a valid filename of an existing file from a subdirectory of
    ``settings.MEDIA_ROOT``. The returned filename is relative to
    ``MEDIA_ROOT``.
    '''
    def __init__(self, path='', *args, **kwargs):
        from django.conf import settings
        path = os.path.join(settings.MEDIA_ROOT, path)
        super(MediaFilePathGenerator, self).__init__(path, *args, **kwargs)

    def generate(self):
        from django.conf import settings
        filename = super(MediaFilePathGenerator, self).generate()
        filename = relpath(filename, settings.MEDIA_ROOT)
        return filename


class InstanceGenerator(Generator):
    '''
    Naive support for ``limit_choices_to``. It assignes specified value to
    field for dict items that have one of the following form::

        fieldname: value
        fieldname__exact: value
        fieldname__iexact: value
    '''
    def __init__(self, autofixture, limit_choices_to=None, *args, **kwargs):
        self.autofixture = autofixture
        limit_choices_to = limit_choices_to or {}
        for lookup, value in limit_choices_to.items():
            bits = lookup.split('__')
            if len(bits) == 1 or \
                len(bits) == 2 and bits[1] in ('exact', 'iexact'):
                self.autofixture.add_field_value(bits[0], StaticGenerator(value))
        super(InstanceGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        return self.autofixture.create()[0]


class MultipleInstanceGenerator(InstanceGenerator):
    empty_value = []

    def __init__(self, *args, **kwargs):
        self.min_count = kwargs.pop('min_count', 1)
        self.max_count = kwargs.pop('max_count', 10)
        super(MultipleInstanceGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        instances = []
        for i in range(random.randint(self.min_count, self.max_count)):
            instances.append(
                super(MultipleInstanceGenerator, self).generate())
        return instances


class InstanceSelector(Generator):
    '''
    Select one or more instances from a queryset.
    '''
    empty_value = []

    def __init__(self, queryset, min_count=None, max_count=None, fallback=None,
        limit_choices_to=None, *args, **kwargs):
        from django.db.models.query import QuerySet
        if not isinstance(queryset, QuerySet):
            queryset = queryset._default_manager.all()
        limit_choices_to = limit_choices_to or {}
        self.queryset = queryset.filter(**limit_choices_to)
        self.fallback = fallback
        self.min_count = min_count
        self.max_count = max_count
        super(InstanceSelector, self).__init__(*args, **kwargs)

    def generate(self):
        if self.max_count is None:
            try:
                return self.queryset.order_by('?')[0]
            except IndexError:
                return self.fallback
        else:
            min_count = self.min_count or 0
            count = random.randint(min_count, self.max_count)
            return self.queryset.order_by('?')[:count]

class WeightedGenerator(Generator):
    """
    Takes a list of generator objects and integer weights, of the following form:
    [(generator, weight), (generator, weight),...]
    and returns a value from a generator chosen randomly by weight.
    """

    def __init__(self, choices):
        self.choices = choices

    def weighted_choice(self, choices):
        total = sum(w for c, w in choices)
        r = random.uniform(0, total)
        upto = 0
        for c, w in choices:
          if upto + w > r:
             return c
          upto += w

    def generate(self):
        return self.weighted_choice(self.choices).generate()

class ImageGenerator(Generator):
    '''
    Generates a valid palceholder image and saves it to the ``settings.MEDIA_ROOT``
    The returned filename is relative to ``MEDIA_ROOT``.
    '''

    default_sizes = (
        (100,100),
        (200,300),
        (400,600),
    )

    filename = '{width}x{height}-{suffix}.png'

    def __init__(self, width=None, height=None, sizes=None, path='_autofixture', *args, **kwargs):
        self.width = width
        self.height = height
        self.sizes = list(sizes or self.default_sizes)
        if self.width and self.height:
            self.sizes.append((width, height))
        self.path = path
        super(ImageGenerator, self).__init__(*args, **kwargs)

    def generate(self):
        import uuid
        from django.conf import settings
        from placeholder import PlaceHolderImage

        width, height = random.choice(self.sizes)

        # Ensure that _autofixture folder exists.
        if not os.path.isdir(os.path.join(settings.MEDIA_ROOT, self.path)):
            os.makedirs(os.path.join(settings.MEDIA_ROOT, self.path))

        i = 0
        filename = self.filename.format(width=width, height=height, suffix=i)
        filepath = os.path.join(settings.MEDIA_ROOT, self.path, filename)

        while os.path.exists(filepath):
            i += 1
            filename = self.filename.format(width=width, height=height, suffix=i)
            filepath = os.path.join(settings.MEDIA_ROOT, self.path, filename)

        img = PlaceHolderImage(width=width, height=height, path=filepath)
        img.save_image()

        return relpath(filepath, settings.MEDIA_ROOT)

########NEW FILE########
__FILENAME__ = loadtestdata
# -*- coding: utf-8 -*-
'''
Use the ``loadtestdata`` command like this::

    django-admin.py loadtestdata [options] app.Model:# [app.Model:# ...]

Its nearly self explanatory. Supply names of models, prefixed with their app
name. After that, place a colon and tell the command how many objects you want
to create. Here is an example of how to create three categories and twenty
entries for you blogging app::

    django-admin.py loadtestdata blog.Category:3 blog.Entry:20

Voila! You have ready to use testing data populated to your database. The
model fields are filled with data by producing randomly generated values
depending on the type of the field. E.g. text fields are filled with lorem
ipsum dummies, date fields are populated with random dates from the last
years etc.

There are a few command line options available. Mainly to control the
behavior of related fields. If foreingkey or many to many fields should be
populated with existing data or if the related models are also generated on
the fly. Please have a look at the help page of the command for more
information::

    django-admin.py help loadtestdata
'''
from django.utils.encoding import smart_text
import autofixture
from django.db import models
from django.core.management.base import BaseCommand, CommandError
from django.utils.importlib import import_module
from autofixture import signals
from optparse import make_option

try:
    from django.db.transaction import atomic
# For django 1.5 and earlier
except ImportError:
    from django.db.transaction import commit_on_success as atomic


class Command(BaseCommand):
    help = (
        u'Create random model instances for testing purposes.'
    )
    args = 'app.Model:# [app.Model:# ...]'

    option_list = BaseCommand.option_list + (
        make_option('-d', '--overwrite-defaults', action='store_true',
            dest='overwrite_defaults', default=None, help=
                u'Generate values for fields with default values. Default is '
                u'to use default values.'),
        make_option('--no-follow-fk', action='store_true', dest='no_follow_fk',
            default=None, help=
                u'Ignore foreignkeys while creating model instances.'),
        make_option('--generate-fk', action='store', dest='generate_fk',
            default=None, help=
                u'Do not use already existing instances for ForeignKey '
                u'relations. Create new instances instead. You can specify a '
                u'comma sperated list of field names or ALL to indicate that '
                u'all foreignkeys should be generated automatically.'),
        make_option('--no-follow-m2m', action='store_true',
            dest='no_follow_m2m', default=None, help=
                u'Ignore many to many fields while creating model '
                u'instances.'),
        make_option('--follow-m2m', action='store', dest='follow_m2m',
            default=None, help=
                u'Specify minimum and maximum number of instances that are '
                u'assigned to a m2m relation. Use two, colon separated '
                u'numbers in the form of: min,max. Default is 1,5.\n'
                u'You can limit following of many to many relations to '
                u'specific fields using the following format:\n'
                u'field1:min:max,field2:min:max ...'),
        make_option('--generate-m2m', action='store', dest='generate_m2m',
            default=None, help=
                u'Specify minimum and maximum number of instances that are '
                u'newly created and assigned to a m2m relation. Use two, '
                u'colon separated numbers in the form of: min:max. Default is '
                u'to not generate many to many related models automatically. '
                u'You can select specific of many to many fields which are '
                u'automatically generated. Use the following format:\n'
                u'field1:min:max,field2:min:max ...'),
        make_option('-u', '--use', action='store', dest='use',
            default='', help=
                u'Specify a autofixture subclass that is used to create the '
                u'test data. E.g. myapp.autofixtures.MyAutoFixture'),
    )

    def format_output(self, obj):
        output = smart_text(obj)
        if len(output) > 50:
            output = u'{0} ...'.format(output[:50])
        return output

    def print_instance(self, sender, model, instance, **kwargs):
        if self.verbosity < 1:
            return
        print('{0}(pk={1}): {2}'.format(
            '.'.join((
                model._meta.app_label,
                model._meta.object_name)),
            smart_text(instance.pk),
            self.format_output(instance),
        ))
        if self.verbosity < 2:
            return
        for field in instance._meta.fields:
            if isinstance(field, models.ForeignKey):
                obj = getattr(instance, field.name)
                if isinstance(obj, models.Model):
                    print('|   {0} (pk={1}): {2}'.format(
                        field.name,
                        obj.pk,
                        self.format_output(obj)))
        for field in instance._meta.many_to_many:
            qs = getattr(instance, field.name).all()
            if qs.count():
                print('|   {0} (count={1}):'.format(
                    field.name,
                    qs.count()))
                for obj in qs:
                    print('|   |   (pk={0}): {1}'.format(
                        obj.pk,
                        self.format_output(obj)))

    @atomic
    def handle(self, *attrs, **options):
        from django.db.models import get_model

        error_option = None
        #
        # follow options
        #
        if options['no_follow_fk'] is None:
            follow_fk = None
        else:
            follow_fk = False
        if options['no_follow_m2m'] is None:
            follow_m2m = None
            # this is the only chance for the follow_m2m options to be parsed
            if options['follow_m2m']:
                try:
                    value = options['follow_m2m'].split(',')
                    if len(value) == 1 and value[0].count(':') == 1:
                        follow_m2m = [int(i) for i in value[0].split(':')]
                    else:
                        follow_m2m = {}
                        for field in value:
                            key, minval, maxval = field.split(':')
                            follow_m2m[key] = int(minval), int(maxval)
                except ValueError:
                    error_option = '--follow-m2m={0}'.format(options['follow_m2m'])
        else:
            follow_m2m = False
        #
        # generation options
        #
        if options['generate_fk'] is None:
            generate_fk = None
        else:
            generate_fk = options['generate_fk'].split(',')
        generate_m2m = None
        if options['generate_m2m']:
            try:
                value = [v for v in options['generate_m2m'].split(',') if v]
                if len(value) == 1 and value[0].count(':') == 1:
                    generate_m2m = [int(i) for i in value[0].split(':')]
                else:
                    generate_m2m = {}
                    for field in value:
                        key, minval, maxval = field.split(':')
                        generate_m2m[key] = int(minval), int(maxval)
            except ValueError:
                error_option = '--generate-m2m={0}'.format(options['generate_m2m'])

        if error_option:
            raise CommandError(
                u'Invalid option {0}\n'
                u'Expected: {1}=field:min:max,field2:min:max... (min and max must be numbers)'.format(
                    error_option,
                    error_option.split('=', 1)[0]))

        use = options['use']
        if use:
            use = use.split('.')
            use = getattr(import_module('.'.join(use[:-1])), use[-1])

        overwrite_defaults = options['overwrite_defaults']
        self.verbosity = int(options['verbosity'])

        models = []
        for attr in attrs:
            try:
                app_label, model_label = attr.split('.')
                model_label, count = model_label.split(':')
                count = int(count)
            except ValueError:
                raise CommandError(
                    u'Invalid argument: {0}\n'
                    u'Expected: app_label.ModelName:count '
                    u'(count must be a number)'.format(attr))
            model = get_model(app_label, model_label)
            if not model:
                raise CommandError(
                    u'Unknown model: {0}.{1}'.format(app_label, model_label))
            models.append((model, count))

        signals.instance_created.connect(
            self.print_instance)

        autofixture.autodiscover()

        kwargs = {
            'overwrite_defaults': overwrite_defaults,
            'follow_fk': follow_fk,
            'generate_fk': generate_fk,
            'follow_m2m': follow_m2m,
            'generate_m2m': generate_m2m,
        }

        for model, count in models:
            if use:
                fixture = use(model, **kwargs)
                fixture.create(count)
            else:
                autofixture.create(model, count, **kwargs)


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-
from django.dispatch import Signal


instance_created = Signal(providing_args=['model', 'instance', 'committed'])

########NEW FILE########
__FILENAME__ = values
from django.utils.six import with_metaclass


class ValuesMetaclass(type):
    def __new__(mcs, name, bases, attrs):
        parent_value_attrs = {}
        # left most base class overwrites righter base classes
        for base in bases[::-1]:
            if hasattr(base, '_value_attrs'):
                parent_value_attrs.update(base._value_attrs)
        defined_value_attrs = {}
        for key in attrs:
            if not key.startswith('__'):
                defined_value_attrs[key] = attrs[key]

        for key in defined_value_attrs:
            del attrs[key]

        attrs['_value_attrs'] = {}
        attrs['_value_attrs'].update(parent_value_attrs)
        attrs['_value_attrs'].update(defined_value_attrs)
        return super(ValuesMetaclass, mcs).__new__(mcs, name, bases, attrs)


class ValuesBase(dict):
    def __init__(self, *parents, **values):
        self.update(self._value_attrs)
        for parent in parents:
            if parent is None:
                continue
            if isinstance(parent, dict):
                self.update(parent)
            else:
                for attr in dir(parent):
                    if not attr.startswith('__'):
                        self[attr] = getattr(parent, attr)
        self.update(**values)

    def __add__(self, other):
        return self.__class__(self, other)

    def __radd__(self, other):
        return self.__class__(other, self)

    def __iadd__(self, other):
        self.update(other)
        return self


class Values(with_metaclass(ValuesMetaclass, ValuesBase)):
    pass

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import os
from datetime import datetime
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

filepath = os.path.dirname(os.path.abspath(__file__))

def y2k():
    return datetime(2000, 1, 1)


class SimpleModel(models.Model):
    name = models.CharField(max_length=50)


class OtherSimpleModel(models.Model):
    name = models.CharField(max_length=50)


class DeepLinkModel1(models.Model):
    related = models.ForeignKey('SimpleModel')
    related2 = models.ForeignKey('SimpleModel',
        related_name='deeplinkmodel1_rel2',
        null=True, blank=True)

class DeepLinkModel2(models.Model):
    related = models.ForeignKey('DeepLinkModel1')


class NullableFKModel(models.Model):
    m2m = models.ManyToManyField('SimpleModel', null=True, blank=True)


class BasicModel(models.Model):
    chars = models.CharField(max_length=50)
    shortchars = models.CharField(max_length=2)
    blankchars = models.CharField(max_length=100, blank=True)
    nullchars = models.CharField(max_length=100, blank=True, null=True)
    slugfield = models.SlugField()
    textfield = models.TextField()
    blankfloatfield = models.FloatField(null=True, blank=True)
    floatfield = models.FloatField()

    defaultint = models.IntegerField(default=1)
    intfield = models.IntegerField()
    pintfield = models.PositiveIntegerField()
    sintfield = models.SmallIntegerField()
    psintfield = models.PositiveSmallIntegerField()


    STRING_CHOICES = (
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
    )
    choicefield = models.CharField(choices=STRING_CHOICES, max_length=1)

    datefield = models.DateField()
    datetimefield = models.DateTimeField()
    defaultdatetime = models.DateTimeField(default=y2k)
    timefield = models.TimeField()

    decimalfield = models.DecimalField(max_digits=10, decimal_places=4)

    emailfield = models.EmailField()
    ipaddressfield = models.IPAddressField()
    urlfield = models.URLField()
    rfilepathfield = models.FilePathField(path=filepath, recursive=True)
    filepathfield = models.FilePathField(path=filepath)
    mfilepathfield = models.FilePathField(path=filepath, match=r'^.+\.py$')
    imgfield = models.ImageField(upload_to='_autofixtures')

class UniqueTestModel(models.Model):
    CHOICES = [(i,i) for i in range(10)]

    choice1 = models.PositiveIntegerField(choices=CHOICES, unique=True)


class UniqueTogetherTestModel(models.Model):
    CHOICES = [(i,i) for i in range(10)]

    choice1 = models.PositiveIntegerField(choices=CHOICES)
    choice2 = models.PositiveIntegerField(choices=CHOICES)

    class Meta:
        unique_together = ('choice1', 'choice2')


class RelatedModel(models.Model):
    related = models.ForeignKey(BasicModel, related_name='rel1')
    limitedfk = models.ForeignKey(SimpleModel,
        limit_choices_to={'name__exact': 'foo'}, related_name='rel2',
        null=True, blank=True)


class O2OModel(models.Model):
    o2o = models.OneToOneField(SimpleModel)


class InheritModel(SimpleModel):
    extrafloatfield = models.FloatField()


class InheritUniqueTogetherModel(SimpleModel):
    extrafloatfield = models.FloatField()

    class Meta:
        unique_together = ('extrafloatfield', 'simplemodel_ptr')


class SelfReferencingModel(models.Model):
    parent_self = models.ForeignKey('self', blank=True, null=True)


class SelfReferencingModelNoNull(models.Model):
    parent_self = models.ForeignKey('self')


class M2MModel(models.Model):
    m2m = models.ManyToManyField(SimpleModel, related_name='m2m_rel1')
    secondm2m = models.ManyToManyField(OtherSimpleModel, related_name='m2m_rel2',
        null=True, blank=True)

class ThroughModel(models.Model):
    simple = models.ForeignKey('SimpleModel')
    other = models.ForeignKey('M2MModelThrough')

class M2MModelThrough(models.Model):
    m2m = models.ManyToManyField(SimpleModel, related_name='m2mthrough_rel1',
        through=ThroughModel)

class GFKModel(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

class GRModel(models.Model):
    gr = generic.GenericRelation('GFKModel')
########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
from django.contrib import admin
from autofixture_tests.sample_app.models import Post


admin.site.register(Post)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=50)


class Post(models.Model):
    name = models.CharField(max_length=50)
    text = models.TextField()
    author = models.ForeignKey(Author)
    categories = models.ManyToManyField(Category, null=True, blank=True)

    def __unicode__(self):
        return '%s: %s' % (self.name, self.text)

########NEW FILE########
__FILENAME__ = settings
import os
import warnings


warnings.simplefilter('always')

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

# Set in order to catch timezone aware vs unaware comparisons
USE_TZ = True

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '0'

ROOT_URLCONF = 'autofixture_tests.urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',

    'autofixture',
    'autofixture_tests',
    'autofixture_tests.tests',
    'autofixture_tests.sample_app',
)


import django
if django.VERSION < (1, 6):
    TEST_RUNNER = 'discover_runner.DiscoverRunner'

########NEW FILE########
__FILENAME__ = test_autodiscover
from django.contrib.auth.models import User
from django.test import TestCase
import autofixture


autofixture.autodiscover()


class AutodiscoverTestCase(TestCase):
    def test_builtin_fixtures(self):
        from autofixture.autofixtures import UserFixture
        self.assertEqual(autofixture.REGISTRY, {
            User: UserFixture,
        })

########NEW FILE########
__FILENAME__ = test_base
# -*- coding: utf-8 -*-
import sys
import autofixture
from decimal import Decimal
from datetime import date, datetime
from django.test import TestCase
from autofixture import generators
from autofixture.base import AutoFixture, CreateInstanceError,  Link
from autofixture.values import Values
from ..models import y2k
from ..models import (
    SimpleModel, OtherSimpleModel, DeepLinkModel1, DeepLinkModel2,
    NullableFKModel, BasicModel, UniqueTestModel, UniqueTogetherTestModel,
    RelatedModel, O2OModel, InheritModel, InheritUniqueTogetherModel,
    M2MModel, ThroughModel, M2MModelThrough, SelfReferencingModel,
    SelfReferencingModelNoNull, GFKModel, GRModel)


if sys.version_info[0] < 3:
    str_ = unicode
else:
    str_ = str


class SimpleAutoFixture(AutoFixture):
    field_values = {
        'name': generators.StaticGenerator('foo'),
    }


class BasicValueFixtureBase(AutoFixture):
    field_values = Values(blankchars='bar')


class BasicValueFixture(BasicValueFixtureBase):
    class Values:
        chars = 'foo'
        shortchars = staticmethod(lambda: 'a')
        intfield = generators.IntegerGenerator(min_value=1, max_value=13)

    field_values = {
        'nullchars': 'spam',
    }


class TestBasicModel(TestCase):
    def assertEqualOr(self, first, second, fallback):
        if first != second and not fallback:
            self.fail()

    def test_create(self):
        filler = AutoFixture(BasicModel)
        filler.create(10)
        self.assertEqual(BasicModel.objects.count(), 10)

    def test_constraints(self):
        filler = AutoFixture(
            BasicModel,
            overwrite_defaults=False)
        for obj in filler.create(100):
            self.assertTrue(len(obj.chars) > 0)
            self.assertEqual(type(obj.chars), str_)
            self.assertTrue(len(obj.shortchars) <= 2)
            self.assertEqual(type(obj.shortchars), str_)
            self.assertTrue(type(obj.blankchars), str_)
            self.assertEqualOr(type(obj.nullchars), str_, None)
            self.assertEqual(type(obj.slugfield), str_)
            self.assertEqual(type(obj.defaultint), int)
            self.assertEqual(obj.defaultint, 1)
            self.assertEqual(type(obj.intfield), int)
            self.assertEqual(type(obj.sintfield), int)
            self.assertEqual(type(obj.pintfield), int)
            self.assertEqual(type(obj.psintfield), int)
            self.assertEqual(type(obj.datefield), date)
            self.assertEqual(type(obj.datetimefield), datetime)
            self.assertEqual(type(obj.defaultdatetime), datetime)
            self.assertEqual(obj.defaultdatetime, y2k())
            self.assertEqual(type(obj.decimalfield), Decimal)
            self.assertTrue('@' in obj.emailfield)
            self.assertTrue('.' in obj.emailfield)
            self.assertTrue(' ' not in obj.emailfield)
            self.assertTrue(obj.ipaddressfield.count('.'), 3)
            self.assertTrue(len(obj.ipaddressfield) >= 7)
        self.assertEqual(BasicModel.objects.count(), 100)

    def test_field_values(self):
        int_value = 1
        char_values = (u'a', u'b')
        filler = AutoFixture(
            BasicModel,
            field_values={
                'intfield': 1,
                'chars': generators.ChoicesGenerator(values=char_values),
                'shortchars': lambda: u'ab',
            })
        for obj in filler.create(100):
            self.assertEqual(obj.intfield, int_value)
            self.assertTrue(obj.chars in char_values)
            self.assertEqual(obj.shortchars, u'ab')

    def test_field_values_overwrite_defaults(self):
        fixture = AutoFixture(
            BasicModel,
            field_values={
                'defaultint': 42,
            })
        obj = fixture.create(1)[0]
        self.assertEqual(obj.defaultint, 42)


class TestRelations(TestCase):
    def test_generate_foreignkeys(self):
        filler = AutoFixture(
            RelatedModel,
            generate_fk=True)
        for obj in filler.create(100):
            self.assertEqual(obj.related.__class__, BasicModel)
            self.assertEqual(obj.limitedfk.name, 'foo')

    def test_deep_generate_foreignkeys(self):
        filler = AutoFixture(
            DeepLinkModel2,
            generate_fk=True)
        for obj in filler.create(10):
            self.assertEqual(obj.related.__class__, DeepLinkModel1)
            self.assertEqual(obj.related.related.__class__, SimpleModel)
            self.assertEqual(obj.related.related2.__class__, SimpleModel)

    def test_deep_generate_foreignkeys2(self):
        filler = AutoFixture(
            DeepLinkModel2,
            follow_fk=False,
            generate_fk=('related', 'related__related'))
        for obj in filler.create(10):
            self.assertEqual(obj.related.__class__, DeepLinkModel1)
            self.assertEqual(obj.related.related.__class__, SimpleModel)
            self.assertEqual(obj.related.related2, None)

    def test_generate_only_some_foreignkeys(self):
        filler = AutoFixture(
            RelatedModel,
            generate_fk=('related',))
        for obj in filler.create(100):
            self.assertEqual(obj.related.__class__, BasicModel)
            self.assertEqual(obj.limitedfk, None)

    def test_follow_foreignkeys(self):
        related = AutoFixture(BasicModel).create()[0]
        self.assertEqual(BasicModel.objects.count(), 1)

        simple = SimpleModel.objects.create(name='foo')
        simple2 = SimpleModel.objects.create(name='bar')

        filler = AutoFixture(
            RelatedModel,
            follow_fk=True)
        for obj in filler.create(100):
            self.assertEqual(obj.related, related)
            self.assertEqual(obj.limitedfk, simple)

    def test_follow_only_some_foreignkeys(self):
        related = AutoFixture(BasicModel).create()[0]
        self.assertEqual(BasicModel.objects.count(), 1)

        simple = SimpleModel.objects.create(name='foo')
        simple2 = SimpleModel.objects.create(name='bar')

        filler = AutoFixture(
            RelatedModel,
            follow_fk=('related',))
        for obj in filler.create(100):
            self.assertEqual(obj.related, related)
            self.assertEqual(obj.limitedfk, None)

    def test_follow_fk_for_o2o(self):
        # OneToOneField is the same as a ForeignKey with unique=True
        filler = AutoFixture(O2OModel, follow_fk=True)

        simple = SimpleModel.objects.create()
        obj = filler.create()[0]
        self.assertEqual(obj.o2o, simple)

        self.assertRaises(CreateInstanceError, filler.create)

    def test_generate_fk_for_o2o(self):
        # OneToOneField is the same as a ForeignKey with unique=True
        filler = AutoFixture(O2OModel, generate_fk=True)

        all_o2o = set()
        for obj in filler.create(10):
            all_o2o.add(obj.o2o)

        self.assertEqual(set(SimpleModel.objects.all()), all_o2o)

    def test_follow_m2m(self):
        related = AutoFixture(SimpleModel).create()[0]
        self.assertEqual(SimpleModel.objects.count(), 1)

        filler = AutoFixture(
            M2MModel,
            follow_m2m=(2, 10))
        for obj in filler.create(10):
            self.assertEqual(list(obj.m2m.all()), [related])

    def test_follow_only_some_m2m(self):
        related = AutoFixture(SimpleModel).create()[0]
        self.assertEqual(SimpleModel.objects.count(), 1)
        other_related = AutoFixture(OtherSimpleModel).create()[0]
        self.assertEqual(OtherSimpleModel.objects.count(), 1)

        filler = AutoFixture(
            M2MModel,
            none_p=0,
            follow_m2m={
                'm2m': (2, 10),
            })
        for obj in filler.create(10):
            self.assertEqual(list(obj.m2m.all()), [related])
            self.assertEqual(list(obj.secondm2m.all()), [])

    def test_generate_m2m(self):
        filler = AutoFixture(
            M2MModel,
            none_p=0,
            generate_m2m=(1, 5))
        all_m2m = set()
        all_secondm2m = set()
        for obj in filler.create(10):
            self.assertTrue(1 <= obj.m2m.count() <= 5)
            self.assertTrue(1 <= obj.secondm2m.count() <= 5)
            all_m2m.update(obj.m2m.all())
            all_secondm2m.update(obj.secondm2m.all())
        self.assertEqual(SimpleModel.objects.count(), len(all_m2m))
        self.assertEqual(OtherSimpleModel.objects.count(), len(all_secondm2m))

    def test_generate_only_some_m2m(self):
        filler = AutoFixture(
            M2MModel,
            none_p=0,
            generate_m2m={
                'm2m': (1, 5),
            })
        all_m2m = set()
        all_secondm2m = set()
        for obj in filler.create(10):
            self.assertTrue(1 <= obj.m2m.count() <= 5)
            self.assertEqual(0, obj.secondm2m.count())
            all_m2m.update(obj.m2m.all())
            all_secondm2m.update(obj.secondm2m.all())
        self.assertEqual(SimpleModel.objects.count(), len(all_m2m))
        self.assertEqual(OtherSimpleModel.objects.count(), len(all_secondm2m))

    def test_generate_m2m_with_intermediary_model(self):
        filler = AutoFixture(
            M2MModelThrough,
            generate_m2m=(1, 5))
        all_m2m = set()
        for obj in filler.create(10):
            self.assertTrue(1 <= obj.m2m.count() <= 5)
            all_m2m.update(obj.m2m.all())
        self.assertEqual(SimpleModel.objects.count(), len(all_m2m))

    def test_generate_fk_to_self(self):
        ''' When a model with a reference to itself is encountered, If NULL is allowed
            don't generate a new instance of itself as a foreign key, so as not to reach
            pythons recursion limit
        '''
        filler = AutoFixture(SelfReferencingModel, generate_fk=True)
        model = filler.create_one()
        self.assertEqual(model.parent_self, None)
        self.assertEqual(SelfReferencingModel.objects.count(), 1)

    def test_generate_fk_to_self_no_null(self):
        ''' Throw an exception when a model is encountered which references itself but
            does not allow NULL values to be set.
        '''
        filler = AutoFixture(SelfReferencingModelNoNull, generate_fk=True)
        self.assertRaises(CreateInstanceError, filler.create_one)

    def test_generate_fk_to_self_follow(self):
        filler = AutoFixture(SelfReferencingModel, follow_fk=True)
        first = filler.create_one()
        self.assertEqual(SelfReferencingModel.objects.count(), 1)

        filler = AutoFixture(SelfReferencingModel, follow_fk=True)
        second = filler.create_one()
        self.assertEqual(SelfReferencingModel.objects.count(), 2)
        self.assertEqual(second.parent_self, first)


class TestInheritModel(TestCase):
    def test_inheritence_model(self):
        filler = AutoFixture(InheritModel)
        filler.create(10)
        self.assertEqual(InheritModel.objects.count(), 10)

    def test_inheritence_unique_together_model(self):
        filler = AutoFixture(InheritUniqueTogetherModel)
        filler.create(10)
        self.assertEqual(InheritUniqueTogetherModel.objects.count(), 10)


class TestUniqueConstraints(TestCase):
    def test_unique_field(self):
        filler = AutoFixture(UniqueTestModel)
        count = len(filler.model._meta.
            get_field_by_name('choice1')[0].choices)
        for obj in filler.create(count):
            pass

    def test_unique_together(self):
        filler = AutoFixture(UniqueTogetherTestModel)
        count1 = len(filler.model._meta.
            get_field_by_name('choice1')[0].choices)
        count2 = len(filler.model._meta.
            get_field_by_name('choice2')[0].choices)
        for obj in filler.create(count1 * count2):
            pass


class TestGenerators(TestCase):
    def test_instance_selector(self):
        AutoFixture(SimpleModel).create(10)

        result = generators.InstanceSelector(SimpleModel).generate()
        self.assertEqual(result.__class__, SimpleModel)

        for i in range(10):
            result = generators.InstanceSelector(
                SimpleModel, max_count=10).generate()
            self.assertTrue(0 <= len(result) <= 10)
            for obj in result:
                self.assertEqual(obj.__class__, SimpleModel)
        for i in range(10):
            result = generators.InstanceSelector(
                SimpleModel, min_count=5, max_count=10).generate()
            self.assertTrue(5 <= len(result) <= 10)
            for obj in result:
                self.assertEqual(obj.__class__, SimpleModel)
        for i in range(10):
            result = generators.InstanceSelector(
                SimpleModel, min_count=20, max_count=100).generate()
            # cannot return more instances than available
            self.assertEqual(len(result), 10)
            for obj in result:
                self.assertEqual(obj.__class__, SimpleModel)

        # works also with queryset as argument
        result = generators.InstanceSelector(SimpleModel.objects.all()).generate()
        self.assertEqual(result.__class__, SimpleModel)


class TestLinkClass(TestCase):
    def test_flat_link(self):
        link = Link(('foo', 'bar'))
        self.assertTrue('foo' in link)
        self.assertTrue('bar' in link)
        self.assertFalse('spam' in link)

        self.assertEqual(link['foo'], None)
        self.assertEqual(link['spam'], None)

    def test_nested_links(self):
        link = Link(('foo', 'foo__bar', 'spam__ALL'))
        self.assertTrue('foo' in link)
        self.assertFalse('spam' in link)
        self.assertFalse('egg' in link)

        foolink = link.get_deep_links('foo')
        self.assertTrue('bar' in foolink)
        self.assertFalse('egg' in foolink)

        spamlink = link.get_deep_links('spam')
        self.assertTrue('bar' in spamlink)
        self.assertTrue('egg' in spamlink)

    def test_links_with_value(self):
        link = Link({'foo': 1, 'spam__egg': 2}, default=0)
        self.assertTrue('foo' in link)
        self.assertEqual(link['foo'], 1)
        self.assertFalse('spam' in link)
        self.assertEqual(link['spam'], 0)

        spamlink = link.get_deep_links('spam')
        self.assertTrue('egg' in spamlink)
        self.assertEqual(spamlink['bar'], 0)
        self.assertEqual(spamlink['egg'], 2)

    def test_always_true_link(self):
        link = Link(True)
        self.assertTrue('field' in link)
        self.assertTrue('any' in link)

        link = link.get_deep_links('field')
        self.assertTrue('field' in link)
        self.assertTrue('any' in link)

        link = Link(('ALL',))
        self.assertTrue('field' in link)
        self.assertTrue('any' in link)

        link = link.get_deep_links('field')
        self.assertTrue('field' in link)
        self.assertTrue('any' in link)

    def test_inherit_always_true_value(self):
        link = Link({'ALL': 1})
        self.assertEqual(link['foo'], 1)

        sublink = link.get_deep_links('foo')
        self.assertEqual(sublink['bar'], 1)


class TestRegistry(TestCase):
    def setUp(self):
        self.original_registry = autofixture.REGISTRY
        autofixture.REGISTRY = {}

    def tearDown(self):
        autofixture.REGISTRY = self.original_registry

    def test_registration(self):
        autofixture.register(SimpleModel, SimpleAutoFixture)
        self.assertTrue(SimpleModel in autofixture.REGISTRY)
        self.assertEqual(autofixture.REGISTRY[SimpleModel], SimpleAutoFixture)

    def test_unregister(self):
        autofixture.register(SimpleModel, SimpleAutoFixture)
        self.assertTrue(SimpleModel in autofixture.REGISTRY)
        self.assertEqual(autofixture.REGISTRY[SimpleModel], SimpleAutoFixture)

        autofixture.unregister(SimpleModel)
        self.assertFalse(SimpleModel in autofixture.REGISTRY)

    def test_create(self):
        autofixture.register(SimpleModel, SimpleAutoFixture)
        for obj in autofixture.create(SimpleModel, 10):
            self.assertEqual(obj.name, 'foo')
        obj = autofixture.create_one(SimpleModel)
        self.assertEqual(obj.name, 'foo')

    def test_overwrite_attributes(self):
        autofixture.register(SimpleModel, SimpleAutoFixture)
        for obj in autofixture.create(
                SimpleModel, 10, field_values={'name': 'bar'}):
            self.assertEqual(obj.name, 'bar')
        obj = autofixture.create_one(
            SimpleModel, field_values={'name': 'bar'})
        self.assertEqual(obj.name, 'bar')

    def test_registered_fixture_is_used_for_fk(self):
        class BasicModelFixture(AutoFixture):
            field_values={'chars': 'Hello World!'}

        autofixture.register(BasicModel, BasicModelFixture)

        fixture = AutoFixture(RelatedModel, generate_fk=['related'])
        obj = fixture.create_one()
        self.assertTrue(obj)
        self.assertEqual(obj.related.chars, 'Hello World!')

    def test_registered_fixture_is_used_for_m2m(self):
        class SimpleModelFixture(AutoFixture):
            field_values={'name': 'Jon Doe'}

        autofixture.register(SimpleModel, SimpleModelFixture)

        fixture = AutoFixture(M2MModel, generate_m2m={'m2m': (5,5)})
        obj = fixture.create_one()
        self.assertTrue(obj)

        self.assertEqual(obj.m2m.count(), 5)
        self.assertEqual(
            list(obj.m2m.values_list('name', flat=True)),
            ['Jon Doe'] * 5)


class TestAutofixtureAPI(TestCase):
    def setUp(self):
        self.original_registry = autofixture.REGISTRY
        autofixture.REGISTRY = {}

    def tearDown(self):
        autofixture.REGISTRY = self.original_registry

    def test_values_class(self):
        autofixture.register(BasicModel, BasicValueFixture)
        for obj in autofixture.create(BasicModel, 10):
            self.assertEqual(obj.chars, 'foo')
            self.assertEqual(obj.shortchars, 'a')
            self.assertEqual(obj.blankchars, 'bar')
            self.assertEqual(obj.nullchars, 'spam')
            self.assertTrue(1 <= obj.intfield <= 13)


class TestManagementCommand(TestCase):
    def setUp(self):
        from autofixture.management.commands.loadtestdata import Command
        self.command = Command()
        self.options = {
            'overwrite_defaults': None,
            'no_follow_fk': None,
            'no_follow_m2m': None,
            'generate_fk': None,
            'follow_m2m': None,
            'generate_m2m': None,
            'verbosity': '0',
            'use': '',
        }
        self.original_registry = autofixture.REGISTRY
        autofixture.REGISTRY = {}

    def tearDown(self):
        autofixture.REGISTRY = self.original_registry

    def test_basic(self):
        models = ()
        # empty attributes are allowed
        self.command.handle(*models, **self.options)
        self.assertEqual(SimpleModel.objects.count(), 0)

        models = ('autofixture_tests.SimpleModel:1',)
        self.command.handle(*models, **self.options)
        self.assertEqual(SimpleModel.objects.count(), 1)

        models = ('autofixture_tests.SimpleModel:5',)
        self.command.handle(*models, **self.options)
        self.assertEqual(SimpleModel.objects.count(), 6)

    def test_generate_fk(self):
        models = ('autofixture_tests.DeepLinkModel2:1',)
        self.options['generate_fk'] = 'related,related__related'
        self.command.handle(*models, **self.options)
        obj = DeepLinkModel2.objects.get()
        self.assertTrue(obj.related)
        self.assertTrue(obj.related.related)
        self.assertEqual(obj.related.related2, obj.related.related)

    def test_generate_fk_with_no_follow(self):
        models = ('autofixture_tests.DeepLinkModel2:1',)
        self.options['generate_fk'] = 'related,related__related'
        self.options['no_follow_fk'] = True
        self.command.handle(*models, **self.options)
        obj = DeepLinkModel2.objects.get()
        self.assertTrue(obj.related)
        self.assertTrue(obj.related.related)
        self.assertEqual(obj.related.related2, None)

    def test_generate_fk_with_ALL(self):
        models = ('autofixture_tests.DeepLinkModel2:1',)
        self.options['generate_fk'] = 'ALL'
        self.command.handle(*models, **self.options)
        obj = DeepLinkModel2.objects.get()
        self.assertTrue(obj.related)
        self.assertTrue(obj.related.related)
        self.assertTrue(obj.related.related2)
        self.assertTrue(obj.related.related != obj.related.related2)

    def test_no_follow_m2m(self):
        AutoFixture(SimpleModel).create(1)

        models = ('autofixture_tests.NullableFKModel:1',)
        self.options['no_follow_m2m'] = True
        self.command.handle(*models, **self.options)
        obj = NullableFKModel.objects.get()
        self.assertEqual(obj.m2m.count(), 0)

    def test_follow_m2m(self):
        AutoFixture(SimpleModel).create(10)
        AutoFixture(OtherSimpleModel).create(10)

        models = ('autofixture_tests.M2MModel:25',)
        self.options['follow_m2m'] = 'm2m:3:3,secondm2m:0:10'
        self.command.handle(*models, **self.options)

        for obj in M2MModel.objects.all():
            self.assertEqual(obj.m2m.count(), 3)
            self.assertTrue(0 <= obj.secondm2m.count() <= 10)

    def test_generate_m2m(self):
        models = ('autofixture_tests.M2MModel:10',)
        self.options['generate_m2m'] = 'm2m:1:1,secondm2m:2:5'
        self.command.handle(*models, **self.options)

        all_m2m, all_secondm2m = set(), set()
        for obj in M2MModel.objects.all():
            self.assertEqual(obj.m2m.count(), 1)
            self.assertTrue(
                2 <= obj.secondm2m.count() <= 5 or
                obj.secondm2m.count() == 0)
            all_m2m.update(obj.m2m.all())
            all_secondm2m.update(obj.secondm2m.all())
        self.assertEqual(all_m2m, set(SimpleModel.objects.all()))
        self.assertEqual(all_secondm2m, set(OtherSimpleModel.objects.all()))

    def test_using_registry(self):
        autofixture.register(SimpleModel, SimpleAutoFixture)
        models = ('autofixture_tests.SimpleModel:10',)
        self.command.handle(*models, **self.options)
        for obj in SimpleModel.objects.all():
            self.assertEqual(obj.name, 'foo')

    def test_use_option(self):
        self.options['use'] = 'autofixture_tests.tests.test_base.SimpleAutoFixture'
        models = ('autofixture_tests.SimpleModel:10',)
        self.command.handle(*models, **self.options)
        for obj in SimpleModel.objects.all():
            self.assertEqual(obj.name, 'foo')


class TestGenericRelations(TestCase):
    def assertNotRaises(self, exc_type, func, msg=None,
            args=None, kwargs=None):
        args = args or []
        kwargs = kwargs or {}
        try:
            func(*args, **kwargs)
        except exc_type as exc:
            if msg is not None and exc.message != msg:
                return
            self.fail('{} failed with {}'.format(func, exc))

    def test_process_gr(self):
        """Tests the bug when GenericRelation field being processed
        by autofixture.base.AutoFixtureBase#process_m2m
        and through table appears as None.
        """
        count = 10
        fixture = AutoFixture(GRModel)
        self.assertNotRaises(AttributeError, fixture.create,
            msg="'NoneType' object has no attribute '_meta'", args=[count])
        self.assertEqual(GRModel.objects.count(), count)


class TestShortcuts(TestCase):
    def test_commit_kwarg(self):
        instances = autofixture.create(BasicModel, 3, commit=False)
        self.assertEqual([i.pk for i in instances], [None] * 3)

        instance = autofixture.create_one(BasicModel, commit=False)
        self.assertEqual(instance.pk, None)


class TestPreProcess(TestCase):
    def test_pre_process_instance_not_yet_saved(self):
        self_ = self
        class TestAutoFixture(AutoFixture):
            def pre_process_instance(self, instance):
                self_.assertIsNone(instance.pk)
                return instance

        TestAutoFixture(BasicModel).create_one()

        self.assertEqual(BasicModel.objects.count(), 1)

    def test_pre_process_has_effect(self):
        expected_string = generators.LoremGenerator(max_length=50)()

        class TestAutoFixture(AutoFixture):
            def pre_process_instance(self, instance):
                instance.name = expected_string
                return instance

        instance = TestAutoFixture(SimpleModel).create_one()
        self.assertEqual(instance.name, expected_string)

########NEW FILE########
__FILENAME__ = test_generator
import os
import shutil
from operator import truediv

from django import forms
from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from django.test.utils import override_settings
from PIL import Image

from autofixture import generators


class FilePathTests(TestCase):
    def test_media_path_generator(self):
        generate = generators.MediaFilePathGenerator(recursive=True)
        for i in range(10):
            path = generate()
            self.assertTrue(len(path) > 0)
            self.assertFalse(path.startswith('/'))
            media_path = os.path.join(settings.MEDIA_ROOT, path)
            self.assertTrue(os.path.exists(media_path))
            self.assertTrue(os.path.isfile(media_path))

    def test_media_path_generator_in_subdirectory(self):
        generate = generators.MediaFilePathGenerator(path='textfiles')
        for i in range(10):
            path = generate()
            self.assertTrue(path.startswith('textfiles/'))
            self.assertTrue(path.endswith('.txt'))


class DateTimeTests(TestCase):
    @override_settings(USE_TZ=True)
    def test_is_datetime_timezone_aware(self):
        generate = generators.DateTimeGenerator()
        date_time = generate()
        self.assertTrue(timezone.is_aware(date_time))

    @override_settings(USE_TZ=False)
    def test_is_datetime_timezone_not_aware(self):
        generate = generators.DateTimeGenerator()
        date_time = generate()
        self.assertFalse(timezone.is_aware(date_time))


class EmailForm(forms.Form):
    email = forms.EmailField()


class EmailGeneratorTests(TestCase):
    def test_email(self):
        generate = generators.EmailGenerator()
        form = EmailForm({'email': generate()})
        self.assertTrue(form.is_valid())

    def test_email_with_static_domain(self):
        generate = generators.EmailGenerator(static_domain='djangoproject.com')
        email = generate()
        self.assertTrue(email.endswith('djangoproject.com'))
        email = generate()
        self.assertTrue(email.endswith('djangoproject.com'))


class WeightedGeneratorTests(TestCase):
    def test_simple_weights(self):
        results = {"Red": 0, "Blue": 0}
        choices = [(generators.StaticGenerator("Red"), 50),
                   (generators.StaticGenerator("Blue"), 50)]
        generate = generators.WeightedGenerator(choices)

        runs = 10000

        for i in range(runs):
            results[generate()] += 1

        MARGIN = 0.025

        self.assertTrue(0.5 - MARGIN < truediv(results["Red"], runs) < 0.5 + MARGIN)
        self.assertTrue(0.5 - MARGIN < truediv(results["Blue"], runs) < 0.5 + MARGIN)

    def test_complex_weights(self):
        results = {"frosh": 0, "soph": 0, "jr": 0, "sr": 0}
        choices = [(generators.StaticGenerator("frosh"), 35),
                   (generators.StaticGenerator("soph"), 20),
                   (generators.StaticGenerator("jr"), 30),
                   (generators.StaticGenerator("sr"), 15)]
        generate = generators.WeightedGenerator(choices)

        runs = 10000

        for i in range(runs):
            results[generate()] += 1

        MARGIN = 0.025

        self.assertTrue(0.35 - MARGIN < truediv(results["frosh"], runs) < 0.35 + MARGIN, results["frosh"] / 1.0 * runs)
        self.assertTrue(0.20 - MARGIN < truediv(results["soph"], runs) < 0.20 + MARGIN)
        self.assertTrue(0.30 - MARGIN < truediv(results["jr"], runs) < 0.30 + MARGIN)
        self.assertTrue(0.15 - MARGIN < truediv(results["sr"], runs) < 0.15 + MARGIN)


class ImageGeneratorTests(TestCase):
    def setUp(self):
        self.cleanup_dirs = ['_autofixture']

    def tearDown(self):
        for path in self.cleanup_dirs:
            img_folder = os.path.join(settings.MEDIA_ROOT, path)
            if os.path.exists(img_folder):
                shutil.rmtree(img_folder)

    def test_image_generator(self):
        generate = generators.ImageGenerator()
        media_file = generate()

        file_path = os.path.join(settings.MEDIA_ROOT, media_file)
        self.assertTrue(os.path.exists(file_path))

        image = Image.open(file_path)
        self.assertTrue(image.size in generators.ImageGenerator.default_sizes)

    def test_width_height(self):
        media_file = generators.ImageGenerator(125, 225).generate()
        file_path = os.path.join(settings.MEDIA_ROOT, media_file)
        self.assertTrue(os.path.exists(file_path))

        image = Image.open(file_path)
        self.assertTrue(image.size, (125, 225))

    def test_filenames_dont_clash(self):
        media_file = generators.ImageGenerator(100, 100).generate()
        file_path1 = os.path.join(settings.MEDIA_ROOT, media_file)
        self.assertTrue(os.path.exists(file_path1))

        media_file = generators.ImageGenerator(100, 100).generate()
        file_path2 = os.path.join(settings.MEDIA_ROOT, media_file)
        self.assertTrue(os.path.exists(file_path2))

        self.assertNotEqual(file_path1, file_path2)

    def test_path(self):
        self.cleanup_dirs.append('mycustompath/withdirs')

        media_file = generators.ImageGenerator(path='mycustompath/withdirs').generate()
        file_path = os.path.join(settings.MEDIA_ROOT, media_file)
        self.assertTrue(os.path.exists(file_path))

        self.assertTrue(media_file.startswith('mycustompath/withdirs/'))
        self.assertTrue('_autofixture' not in media_file)

########NEW FILE########
__FILENAME__ = test_user_fixture
from django.contrib.auth.hashers import is_password_usable
from django.contrib.auth.models import User
from django.test import TestCase
import autofixture


autofixture.autodiscover()


class UserFixtureTest(TestCase):
    def test_discover(self):
        self.assertTrue(User in autofixture.REGISTRY)

    def test_basic(self):
        user = autofixture.create_one(User)
        self.assertTrue(user.username)
        self.assertFalse(is_password_usable(user.password))

    def test_password_setting(self):
        user = autofixture.create_one(User, password='known')
        self.assertTrue(user.username)
        self.assertTrue(is_password_usable(user.password))
        self.assertTrue(user.check_password('known'))

        loaded_user = User.objects.get()
        self.assertEqual(loaded_user.password, user.password)
        self.assertTrue(loaded_user.check_password('known'))

#    def test_commit(self):
#        user = autofixture.create_one(User, commit=False)
#        self.assertEqual(user.pk, None)

########NEW FILE########
__FILENAME__ = test_values
from django.test import TestCase
from autofixture.values import Values


class ValuesTests(TestCase):
    def test_init(self):
        values = Values({'a': 1, 'c': 4}, a=2, b=3)
        self.assertEqual(values['a'], 2)
        self.assertEqual(values['b'], 3)
        self.assertEqual(values['c'], 4)

        values = Values(values)
        self.assertEqual(values['a'], 2)
        self.assertEqual(values['b'], 3)
        self.assertEqual(values['c'], 4)

        class Data:
            a = 1
            b = 3
            _c = 4
        values = Values(Data, a=2)
        self.assertEqual(values['a'], 2)
        self.assertEqual(values['b'], 3)
        self.assertEqual(values['_c'], 4)

        values = Values(Data(), a=2)
        self.assertEqual(values['a'], 2)
        self.assertEqual(values['b'], 3)
        self.assertEqual(values['_c'], 4)

        values = Values(Values(a=1, c=4), a=2, b=3)
        self.assertEqual(values['a'], 2)
        self.assertEqual(values['b'], 3)
        self.assertEqual(values['c'], 4)

    def test_add_operation(self):
        values = Values(a=1, b=3)
        values = values + {'a': 2, 'c': 4}
        self.assertEqual(values['a'], 2)
        self.assertEqual(values['b'], 3)
        self.assertEqual(values['c'], 4)

    def test_radd_operation(self):
        values = Values(a=1, b=3)
        values = {'a': 2, 'c': 4} + values
        self.assertEqual(values['a'], 1)
        self.assertEqual(values['b'], 3)
        self.assertEqual(values['c'], 4)

    def test_iadd_operation(self):
        values = Values(a=1, b=3)
        values += {'a': 2, 'c': 4}
        self.assertEqual(values['a'], 2)
        self.assertEqual(values['b'], 3)
        self.assertEqual(values['c'], 4)

    def test_subclassing(self):
        class AB(Values):
            a = 1
            b = 2

        values = AB()
        self.assertEqual(values['a'], 1)
        self.assertEqual(values['b'], 2)
        self.assertRaises(KeyError, values.__getitem__, 'c')
        self.assertRaises(AttributeError, getattr, values, 'a')
        self.assertRaises(AttributeError, getattr, values, 'b')
        self.assertRaises(AttributeError, getattr, values, 'c')

        values = AB(b=3, c=4)
        self.assertEqual(values['a'], 1)
        self.assertEqual(values['b'], 3)
        self.assertEqual(values['c'], 4)

        values += {'a': 2}
        self.assertEqual(values['a'], 2)
        self.assertEqual(values['b'], 3)
        self.assertEqual(values['c'], 4)

    def test_sub_subclassing(self):
        class AB(Values):
            a = 1
            b = 2

        class ABCD(AB):
            c = 3
            d = 4

        values = ABCD(a=2, c=4)
        self.assertEqual(values['a'], 2)
        self.assertEqual(values['b'], 2)
        self.assertEqual(values['c'], 4)
        self.assertEqual(values['d'], 4)

    def test_multiple_inheritance(self):
        class A(Values):
            a = 1

        class AB(Values):
            a = 2
            b = 3

        class ABC(A, AB):
            c = 4

        values = ABC()
        self.assertEqual(values['a'], 1)
        self.assertEqual(values['b'], 3)
        self.assertEqual(values['c'], 4)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings
from django.http import HttpResponse


admin.autodiscover()

def handle404(request):
    return HttpResponse('404')
def handle500(request):
    return HttpResponse('500')

handler404 = 'autofixture_tests.urls.handle404'
handler500 = 'autofixture_tests.urls.handle500'


urlpatterns = patterns('',
    url(r'^media/(.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    url(r'^admin/', include(admin.site.urls), name="admin"),
)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-autofixture documentation build configuration file, created by
# sphinx-quickstart on Mon Mar  8 22:17:43 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import re
import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

PROJECT_PATH = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, PROJECT_PATH)

from django.conf import settings
settings.configure(DATABASES={
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
})

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-autofixture'
copyright = u'2013, Gregor Müllegger'

def get_release(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_path = os.path.join(PROJECT_PATH, package, '__init__.py')
    init_py = open(init_path).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)

# The full version, including alpha/beta/rc tags.
release = get_release('autofixture')

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '.'.join(release.split('.')[:2])

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

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
#html_static_path = ['_static']

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-autofixturedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-autofixture.tex', u'django-autofixture Documentation',
   u'Gregor Müllegger', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = fabfile
# -*- coding: utf-8 -*-
import os
from fabric.api import abort, cd, local, env, run, settings, sudo


#################
# Documentation #
#################

def packagedocs():
    builddocs('html')
    try:
        os.mkdir('dist')
    except OSError:
        pass
    with cd('docs/_build/html'):
        local('find -print | zip docs.zip -@')
    local('mv docs/_build/html/docs.zip dist')

def builddocs(output='html'):
    with cd('docs'):
        local('make %s' % output, capture=False)

def opendocs(where='index', how='default'):
    '''
    Rebuild documentation and opens it in your browser.

    Use the first argument to specify how it should be opened:

        `d` or `default`: Open in new tab or new window, using the default
        method of your browser.

        `t` or `tab`: Open documentation in new tab.

        `n`, `w` or `window`: Open documentation in new window.
    '''
    import webbrowser
    docs_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'docs')
    index = os.path.join(docs_dir, '_build/html/%s.html' % where)
    builddocs('html')
    url = 'file://%s' % os.path.abspath(index)
    if how in ('d', 'default'):
        webbrowser.open(url)
    elif how in ('t', 'tab'):
        webbrowser.open_new_tab(url)
    elif how in ('n', 'w', 'window'):
        webbrowser.open_new(url)

docs = opendocs

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "autofixture_tests.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import argparse
import os, sys


os.environ['DJANGO_SETTINGS_MODULE'] = 'autofixture_tests.settings'


# Adding current directory to ``sys.path``.
parent = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, parent)


def runtests(*argv):
    argv = list(argv) or [
        'autofixture',
        'autofixture_tests',
    ]
    opts = argparser.parse_args(argv)

    if opts.coverage:
        from coverage import coverage
        test_coverage = coverage(
            branch=True,
            source=['autofixture'])
        test_coverage.start()

    # Run tests.
    from django.core.management import execute_from_command_line
    execute_from_command_line([sys.argv[0], 'test'] + opts.appname)

    if opts.coverage:
        test_coverage.stop()

        # Report coverage to commandline.
        test_coverage.report(file=sys.stdout)


argparser = argparse.ArgumentParser(description='Process some integers.')
argparser.add_argument('appname', nargs='*')
argparser.add_argument('--no-coverage', dest='coverage', action='store_const',
    const=False, default=True, help='Do not collect coverage data.')


if __name__ == '__main__':
    runtests(*sys.argv[1:])


########NEW FILE########
