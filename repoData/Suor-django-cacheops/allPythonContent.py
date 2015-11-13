__FILENAME__ = bench
#!/usr/bin/env python
import os, time, gc, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

verbosity = 1
interactive = False
fixtures = ['basic']


from operator import itemgetter
from profilehooks import profile

HEADER_TEMPLATE = '==================== %-20s ===================='


def run_benchmarks(tests):
    for name, test in tests:
        if 'h' in flags:
            print HEADER_TEMPLATE % name
        time = bench_test(test)
        print('%-18s time: %.2fms' % (name, time * 1000))

def bench_test(test):
    prepared = None
    if 'prepare_once' in test:
        prepared = test['prepare_once']()
        if 'h' in flags:
                print '-' * 62

    if 'p' in flags:
        test['run'] = profile(test['run'])

    total = 0
    n = 1
    while total < 2:
        gc.disable()
        durations = [bench_once(test, prepared) for i in range(n)]
        gc.enable()

        if '1' in flags:
            break

        total = sum(d for _, d in durations)
        n *= 2

    return min(d for d, _ in durations)

def bench_once(test, prepared=None):
    zero_start = time.time()
    if 'prepare' in test:
        prepared = test['prepare']()
        if 'h' in flags:
            print '-' * 62
    start = time.time()
    if prepared is None:
        test['run']()
    else:
        test['run'](prepared)
    now = time.time()
    return now - start, now - zero_start

from django.db import connection
from django.core.management import call_command

# Create a test database.
db_name = connection.creation.create_test_db(verbosity=verbosity, autoclobber=not interactive)
# Import the fixture data into the test database.
call_command('loaddata', *fixtures, **{'verbosity': verbosity})


flags = ''.join(arg[1:] for arg in sys.argv[1:] if arg.startswith('-'))
args = [arg for arg in sys.argv[1:] if not arg.startswith('-')]
selector = args[0] if args else None

from tests.bench import TESTS
try:
    if selector:
        tests = [(name, test) for name, test in TESTS if selector in name]
    else:
        tests = TESTS
    run_benchmarks(tests)
except KeyboardInterrupt:
    pass

connection.creation.destroy_test_db(db_name, verbosity=verbosity)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
from copy import deepcopy
from functools import wraps
import warnings
import redis

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .funcy import memoize


profile_defaults = {
    'ops': (),
    'local_get': False,
    'db_agnostic': True,
}
profiles = {
    'just_enable': {},
    'all': {'ops': ('get', 'fetch', 'count')},
    'get': {'ops': ('get',)},
    'count': {'ops': ('count',)},
}
for key in profiles:
    profiles[key] = dict(profile_defaults, **profiles[key])


STRICT_STRINGIFY = getattr(settings, 'CACHEOPS_STRICT_STRINGIFY', False)
DEGRADE_ON_FAILURE = getattr(settings, 'CACHEOPS_DEGRADE_ON_FAILURE', False)

def handle_connection_failure(func):
    if not DEGRADE_ON_FAILURE:
        return func

    @wraps(func)
    def _inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.ConnectionError as e:
            warnings.warn("The cacheops cache is unreachable! Error: %s" % e, RuntimeWarning)

    return _inner

class SafeRedis(redis.StrictRedis):
    get = handle_connection_failure(redis.StrictRedis.get)


# Connecting to redis
try:
    redis_conf = settings.CACHEOPS_REDIS
except AttributeError:
    raise ImproperlyConfigured('You must specify non-empty CACHEOPS_REDIS setting to use cacheops')

redis_client = (SafeRedis if DEGRADE_ON_FAILURE else redis.StrictRedis)(**redis_conf)


@memoize
def prepare_profiles():
    """
    Prepares a dict 'app.model' -> profile, for use in model_profile()
    """
    if hasattr(settings, 'CACHEOPS_PROFILES'):
        profiles.update(settings.CACHEOPS_PROFILES)

    model_profiles = {}
    ops = getattr(settings, 'CACHEOPS', {})
    for app_model, profile in ops.items():
        profile_name, timeout = profile[:2]

        try:
            model_profiles[app_model] = mp = deepcopy(profiles[profile_name])
        except KeyError:
            raise ImproperlyConfigured('Unknown cacheops profile "%s"' % profile_name)

        if len(profile) > 2:
            mp.update(profile[2])
        mp['timeout'] = timeout
        mp['ops'] = set(mp['ops'])

    return model_profiles

@memoize
def model_profile(model):
    """
    Returns cacheops profile for a model
    """
    model_profiles = prepare_profiles()

    app = model._meta.app_label
    # module_name is fallback for Django 1.5-
    model_name = getattr(model._meta, 'model_name', None) or model._meta.module_name
    app_model = '%s.%s' % (app, model_name)
    for guess in (app_model, '%s.*' % app, '*.*'):
        if guess in model_profiles:
            return model_profiles[guess]
    else:
        return None

########NEW FILE########
__FILENAME__ = cross
import six, hashlib

# simplejson is slow in python 3 and json supports sort_keys
if six.PY2:
    import simplejson as json
else:
    import json

if six.PY2:
    md5 = hashlib.md5
else:
    class md5:
        def __init__(self, s=None):
            self.md5 = hashlib.md5()
            if s is not None:
                self.update(s)

        def update(self, s):
            return self.md5.update(s.encode('utf-8'))

        def hexdigest(self):
            return self.md5.hexdigest()

########NEW FILE########
__FILENAME__ = funcy
from functools import wraps


class cached_property(object):
    """
    Decorator that converts a method with a single self argument into a
    property cached on the instance.

    NOTE: implementation borrowed from Django.
    NOTE: we use fget, fset and fdel attributes to mimic @property.
    """
    fset = fdel = None

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, instance, type=None):
        if instance is None:
            return self
        res = instance.__dict__[self.fget.__name__] = self.fget(instance)
        return res


def memoize(func):
    cache = {}

    @wraps(func)
    def wrapper(*args):
        try:
            return cache[args]
        except KeyError:
            cache[args] = func(*args)
            return cache[args]

    return wrapper



########NEW FILE########
__FILENAME__ = invalidation
# -*- coding: utf-8 -*-
import simplejson as json

from cacheops.conf import redis_client, handle_connection_failure
from cacheops.funcy import memoize
from cacheops.utils import get_model_name, non_proxy, load_script, NON_SERIALIZABLE_FIELDS


__all__ = ('invalidate_obj', 'invalidate_model', 'invalidate_all')


@handle_connection_failure
def invalidate_obj(obj):
    """
    Invalidates caches that can possibly be influenced by object
    """
    model = non_proxy(obj.__class__)
    load_script('invalidate')(args=[
        get_model_name(model),
        serialize_object(model, obj)
    ])

@handle_connection_failure
def invalidate_model(model):
    """
    Invalidates all caches for given model.
    NOTE: This is a heavy artilery which uses redis KEYS request,
          which could be relatively slow on large datasets.
    """
    model = non_proxy(model)
    conjs_keys = redis_client.keys('conj:%s:*' % get_model_name(model))
    if conjs_keys:
        cache_keys = redis_client.sunion(conjs_keys)
        redis_client.delete(*(list(cache_keys) + conjs_keys))

@handle_connection_failure
def invalidate_all():
    redis_client.flushdb()


### ORM instance serialization

@memoize
def serializable_fields(model):
    return tuple(f for f in model._meta.fields
                   if not isinstance(f, NON_SERIALIZABLE_FIELDS))

def serialize_object(model, obj):
    obj_dict = dict(
        (field.attname, field.get_prep_value(getattr(obj, field.attname)))
        for field in serializable_fields(model)
    )
    return json.dumps(obj_dict, default=str)

########NEW FILE########
__FILENAME__ = jinja2
# -*- coding: utf-8 -*-
from __future__ import absolute_import

from jinja2 import nodes
from jinja2.ext import Extension

import cacheops
from cacheops.utils import carefully_strip_whitespace


class CacheopsExtension(Extension):
    tags = ['cached_as', 'cached']

    def parse(self, parser):
        lineno = parser.stream.current.lineno
        tag_name = parser.stream.current.value
        tag_location = '%s:%s' % (parser.name, lineno)

        parser.stream.next()
        args, kwargs = self.parse_args(parser)
        args = [nodes.Const(tag_name), nodes.Const(tag_location)] + args

        block_call = self.call_method('handle_tag', args, kwargs)
        body = parser.parse_statements(['name:end%s' % tag_name], drop_needle=True)

        return nodes.CallBlock(block_call, [], [], body).set_lineno(lineno)


    def handle_tag(self, tag_name, tag_location, *args, **kwargs):
        caller = kwargs.pop('caller')

        cacheops_decorator = getattr(cacheops, tag_name)
        kwargs.setdefault('extra', '')
        if isinstance(kwargs['extra'], tuple):
            kwargs['extra'] += (tag_location,)
        else:
            kwargs['extra'] = str(kwargs['extra']) + tag_location

        @cacheops_decorator(*args, **kwargs)
        def _handle_tag():
            content = caller()
            # TODO: make this cache preparation configurable
            return carefully_strip_whitespace(content)

        return _handle_tag()


    def parse_args(self, parser):
        args = []
        kwargs = []
        require_comma = False

        while parser.stream.current.type != 'block_end':
            if require_comma:
                parser.stream.expect('comma')

            if parser.stream.current.type == 'name' and parser.stream.look().type == 'assign':
                key = parser.stream.current.value
                parser.stream.skip(2)
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=value.lineno))
            else:
                if kwargs:
                    parser.fail('Invalid argument syntax for CacheopsExtension tag',
                                parser.stream.current.lineno)
                args.append(parser.parse_expression())

            require_comma = True

        return args, kwargs

cache = CacheopsExtension

########NEW FILE########
__FILENAME__ = cleanfilecache
import os

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from cacheops.simple import file_cache, FILE_CACHE_DIR


class Command(BaseCommand):
    help = 'Clean filebased cache'

    def handle(self, **options):
        os.system('find %s -type f \! -iname "\." -mmin +0 -delete' % FILE_CACHE_DIR)

########NEW FILE########
__FILENAME__ = invalidate
# -*- coding: utf-8 -*-
from django.core.management.base import LabelCommand, CommandError
from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_app, get_model, get_models

from cacheops.invalidation import *


class Command(LabelCommand):
    help = 'Invalidates cache for entire app, model or particular instance'
    args = '(all | <app> | <app>.<model> | <app>.<model>.<pk>) +'
    label = 'app or model or object'

    def handle_label(self, label, pk=None, **options):
        if label == 'all':
            self.handle_all()
        else:
            app_n_model = label.split('.')
            if len(app_n_model) == 1:
                self.handle_app(app_n_model[0])
            elif len(app_n_model) == 2:
                self.handle_model(*app_n_model)
            elif len(app_n_model) == 3:
                self.handle_obj(*app_n_model)
            else:
                raise CommandError('Wrong model/app name syntax: %s\nType <app_name> or <app_name>.<model_name>' % label)

    def handle_all(self):
        invalidate_all()

    def handle_app(self, app_name):
        try:
            app = get_app(app_name)
        except ImproperlyConfigured as e:
            raise CommandError(e)

        for model in get_models(app, include_auto_created=True):
            invalidate_model(model)

    def handle_model(self, app_name, model_name):
        model = get_model(app_name, model_name)
        if model is None:
            raise CommandError('Unknown model: %s.%s' % (app_name, model_name))
        invalidate_model(model)

    def handle_obj(self, app_name, model_name, obj_pk):
        model = get_model(app_name, model_name)
        if model is None:
            raise CommandError('Unknown model: %s.%s' % (app_name, model_name))
        try:
            obj = model.objects.get(pk=obj_pk)
        except model.DoesNotExist:
            raise CommandError('No %s.%s with pk = %s' % (app_name, model_name, obj_pk))
        invalidate_obj(obj)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = query
# -*- coding: utf-8 -*-
import sys
try:
    import cPickle as pickle
except ImportError:
    import pickle
from functools import wraps
import simplejson as json

from cacheops import cross
from cacheops.cross import json

import django
from django.core.exceptions import ImproperlyConfigured
from django.contrib.contenttypes.generic import GenericRel
from django.db.models import Manager, Model
from django.db.models.query import QuerySet, ValuesQuerySet, ValuesListQuerySet, DateQuerySet
from django.db.models.signals import pre_save, post_save, post_delete, m2m_changed

try:
    from django.db.models.query import MAX_GET_RESULTS
except ImportError:
    MAX_GET_RESULTS = None

from .funcy import cached_property
from cacheops.conf import model_profile, redis_client, handle_connection_failure, STRICT_STRINGIFY
from cacheops.utils import monkey_mix, dnf, get_model_name, non_proxy, stamp_fields, load_script
from cacheops.invalidation import invalidate_obj, invalidate_model


__all__ = ('cached_as', 'install_cacheops')

_old_objs = {}
_local_get_cache = {}


@handle_connection_failure
def cache_thing(model, cache_key, data, cond_dnf=[[]], timeout=None):
    """
    Writes data to cache and creates appropriate invalidators.
    """
    model = non_proxy(model)

    if timeout is None:
        profile = model_profile(model)
        timeout = profile['timeout']

    pickled_data = pickle.dumps(data, -1)
    load_script('cache_thing')(
        keys=[cache_key],
        args=[
            pickled_data,
            get_model_name(model),
            json.dumps(cond_dnf, default=str),
            timeout,
            # Invalidator timeout should be larger than timeout of any key it references
            # So we take timeout from profile which is our upper limit
            # Add few extra seconds to be extra safe
            model._cacheprofile['timeout'] + 10
        ]
    )


def cached_as(sample, extra=None, timeout=None):
    """
    Caches results of a function and invalidates them same way as given queryset.
    NOTE: Ignores queryset cached ops settings, just caches.
    """
    # If we unexpectedly get list instead of queryset return identity decorator.
    # Paginator could do this when page.object_list is empty.
    # TODO: think of better way doing this.
    if isinstance(sample, (list, tuple)):
        return lambda func: func
    elif isinstance(sample, Model):
        queryset = sample.__class__.objects.inplace().filter(pk=sample.pk)
    elif isinstance(sample, type) and issubclass(sample, Model):
        queryset = sample.objects.all()
    else:
        queryset = sample

    queryset._require_cacheprofile()
    if timeout and timeout > queryset._cacheprofile['timeout']:
        raise NotImplementedError('timeout override should be smaller than default')

    def decorator(func):
        if extra:
            key_extra = extra
        else:
            key_extra = '%s.%s' % (func.__module__, func.__name__)
        cache_key = queryset._cache_key(extra=key_extra)

        @wraps(func)
        def wrapper(*args):
            # NOTE: These args must not effect function result.
            #       I'm keeping them to cache view functions.
            cache_data = redis_client.get(cache_key)
            if cache_data is not None:
                return pickle.loads(cache_data)

            result = func(*args)
            queryset._cache_results(cache_key, result, timeout)
            return result

        return wrapper
    return decorator


def _stringify_query():
    """
    Serializes query object, so that it can be used to create cache key.
    We can't just do pickle because order of keys in dicts is arbitrary,
    we can use str(query) which compiles it to SQL, but it's too slow,
    so we use json.dumps with sort_keys=True and object hooks.

    NOTE: I like this function no more than you, it's messy
          and pretty hard linked to django internals.
          I just don't have nicer solution for now.

          Probably the best way out of it is optimizing SQL generation,
          which would be valuable by itself. The problem with it is that
          any significant optimization will most likely require a major
          refactor of sql.Query class, which is a substantial part of ORM.
    """
    from datetime import datetime, date, time
    from decimal import Decimal
    from django.db.models.expressions import ExpressionNode, F
    from django.db.models.fields import Field
    from django.db.models.fields.related import ManyToOneRel, OneToOneRel
    from django.db.models.sql.where import Constraint, WhereNode, ExtraWhere, \
                                           EverythingNode, NothingNode
    from django.db.models.sql import Query
    from django.db.models.sql.aggregates import Aggregate
    from django.db.models.sql.datastructures import Date
    from django.db.models.sql.expressions import SQLEvaluator

    attrs = {}

    # Try to not require geo libs
    try:
        from django.contrib.gis.db.models.sql.where import GeoWhereNode
    except ImportError:
        GeoWhereNode = WhereNode

    # A new things in Django 1.6
    try:
        from django.db.models.sql.where import EmptyWhere, SubqueryConstraint
        attrs[EmptyWhere] = ()
        attrs[SubqueryConstraint] = ('alias', 'columns', 'targets', 'query_object')
    except ImportError:
        pass

    # RawValue removed in Django 1.7
    try:
        from django.db.models.sql.datastructures import RawValue
        attrs[RawValue] = ('value',)
    except ImportError:
        pass

    attrs[WhereNode] = attrs[GeoWhereNode] = attrs[ExpressionNode] \
        = ('connector', 'negated', 'children')
    attrs[SQLEvaluator] = ('expression',)
    attrs[ExtraWhere] = ('sqls', 'params')
    attrs[Aggregate] = ('source', 'is_summary', 'col', 'extra')
    attrs[Date] = ('col', 'lookup_type')
    attrs[F] = ('name',)
    attrs[ManyToOneRel] = attrs[OneToOneRel] = attrs[GenericRel] = ('field',)
    attrs[EverythingNode] = attrs[NothingNode] = ()

    q = Query(None)
    q_keys = q.__dict__.keys()
    q_ignored = ['join_map', 'dupe_avoidance', '_extra_select_cache', '_aggregate_select_cache',
                 'used_aliases']
    attrs[Query] = tuple(sorted( set(q_keys) - set(q_ignored) ))

    try:
        for k, v in attrs.items():
            attrs[k] = map(intern, v)
    except NameError:
        # No intern() in Python 3
        pass

    def encode_object(obj):
        if isinstance(obj, set):
            return sorted(obj)
        elif isinstance(obj, type):
            return '%s.%s' % (obj.__module__, obj.__name__)
        elif hasattr(obj, '__uniq_key__'):
            return (obj.__class__, obj.__uniq_key__())
        elif isinstance(obj, (datetime, date, time, Decimal)):
            return str(obj)
        elif isinstance(obj, Constraint):
            return (obj.alias, obj.col)
        elif isinstance(obj, Field):
            return (obj.model, obj.name)
        elif obj.__class__ in attrs:
            return (obj.__class__, [getattr(obj, attr) for attr in attrs[obj.__class__]])
        elif isinstance(obj, QuerySet):
            return (obj.__class__, obj.query)
        elif isinstance(obj, Aggregate):
            return (obj.__class__, [getattr(obj, attr) for attr in attrs[Aggregate]])
        elif isinstance(obj, Query):
            # for custom subclasses of Query
            return (obj.__class__, [getattr(obj, attr) for attr in attrs[Query]])
        # Fall back for unknown objects
        elif not STRICT_STRINGIFY and hasattr(obj, '__dict__'):
            return (obj.__class__, obj.__dict__)
        else:
            raise TypeError("Can't stringify %s" % repr(obj))

    def stringify_query(query):
        # HACK: Catch TypeError and reraise it as ValueError
        #       since django hides it and behave weird when gets a TypeError in Queryset.iterator()
        try:
            return json.dumps(query, default=encode_object, skipkeys=True,
                                     sort_keys=True, separators=(',',':'))
        except TypeError as e:
            raise ValueError(*e.args)

    return stringify_query
stringify_query = _stringify_query()


class QuerySetMixin(object):
    @cached_property
    def _cacheprofile(self):
        profile = model_profile(self.model)
        if profile:
            self._cacheconf = profile.copy()
            self._cacheconf['write_only'] = False
        return profile

    @cached_property
    def _cloning(self):
        return 1000

    def get_or_create(self, **kwargs):
        """
        Disabling cache for get or create
        TODO: check whether we can use cache (or write_only) here without causing problems
        """
        return self.nocache()._no_monkey.get_or_create(self, **kwargs)

    def _require_cacheprofile(self):
        if self._cacheprofile is None:
            raise ImproperlyConfigured(
                'Cacheops is not enabled for %s model.\n'
                'If you don\'t want to cache anything by default you can "just_enable" it.'
                    % get_model_name(self.model))

    def _cache_key(self, extra=''):
        """
        Compute a cache key for this queryset
        """
        md5 = cross.md5()
        md5.update('%s.%s' % (self.__class__.__module__, self.__class__.__name__))
        md5.update(stamp_fields(self.model)) # Protect from field list changes in model
        md5.update(stringify_query(self.query))
        # If query results differ depending on database
        if self._cacheprofile and not self._cacheprofile['db_agnostic']:
            md5.update(self.db)
        if extra:
            md5.update(str(extra))
        # 'flat' attribute changes results formatting for ValuesQuerySet
        if hasattr(self, 'flat'):
            md5.update(str(self.flat))

        return 'q:%s' % md5.hexdigest()

    def _cache_results(self, cache_key, results, timeout=None):
        cond_dnf = dnf(self)
        cache_thing(self.model, cache_key, results, cond_dnf, timeout or self._cacheconf['timeout'])

    def cache(self, ops=None, timeout=None, write_only=None):
        """
        Enables caching for given ops
            ops        - a subset of ['get', 'fetch', 'count'],
                         ops caching to be turned on, all enabled by default
            timeout    - override default cache timeout
            write_only - don't try fetching from cache, still write result there

        NOTE: you actually can disable caching by omiting corresponding ops,
              .cache(ops=[]) disables caching for this queryset.
        """
        self._require_cacheprofile()
        if timeout and timeout > self._cacheprofile['timeout']:
            raise NotImplementedError('timeout override should be smaller than default')

        if ops is None:
            ops = ['get', 'fetch', 'count']
        if isinstance(ops, str):
            ops = [ops]
        self._cacheconf['ops'] = set(ops)

        if timeout is not None:
            self._cacheconf['timeout'] = timeout
        if write_only is not None:
            self._cacheconf['write_only'] = write_only

        return self

    def nocache(self, clone=False):
        """
        Convinience method, turns off caching for this queryset
        """
        # cache profile not present means caching is not enabled for this model
        if self._cacheprofile is None:
            return self
        else:
            return self.cache(ops=[])

    def cloning(self, cloning=1000):
        self._cloning = cloning
        return self

    def inplace(self):
        return self.cloning(0)

    def _clone(self, klass=None, setup=False, **kwargs):
        if self._cloning:
            return self.clone(klass, setup, **kwargs)
        elif klass is not None:
            # HACK: monkey patch self.query.clone for single call
            #       to return itself instead of cloning
            original_query_clone = self.query.clone
            def query_clone():
                self.query.clone = original_query_clone
                return self.query
            self.query.clone = query_clone
            return self.clone(klass, setup, **kwargs)
        else:
            self.__dict__.update(kwargs)
            return self

    def clone(self, klass=None, setup=False, **kwargs):
        kwargs.setdefault('_cacheprofile', self._cacheprofile)
        if hasattr(self, '_cacheconf'):
            kwargs.setdefault('_cacheconf', self._cacheconf)

        clone = self._no_monkey._clone(self, klass, setup, **kwargs)
        clone._cloning = self._cloning - 1 if self._cloning else 0
        return clone

    def iterator(self):
        # TODO: do not cache empty queries in Django 1.6
        superiter = self._no_monkey.iterator
        cache_this = self._cacheprofile and 'fetch' in self._cacheconf['ops']

        if cache_this:
            cache_key = self._cache_key()
            if not self._cacheconf['write_only']:
                # Trying get data from cache
                cache_data = redis_client.get(cache_key)
                if cache_data is not None:
                    results = pickle.loads(cache_data)
                    for obj in results:
                        yield obj
                    raise StopIteration

        # Cache miss - fallback to overriden implementation
        results = []
        for obj in superiter(self):
            if cache_this:
                results.append(obj)
            yield obj

        if cache_this:
            self._cache_results(cache_key, results)
        raise StopIteration

    def count(self):
        if self._cacheprofile and 'count' in self._cacheconf['ops']:
            # Optmization borrowed from overriden method:
            # if queryset cache is already filled just return its len
            # NOTE: there is no self._iter in Django 1.6+, so we use getattr() for compatibility
            if self._result_cache is not None and not getattr(self, '_iter', None):
                return len(self._result_cache)
            return cached_as(self, extra='count')(self._no_monkey.count)(self)
        else:
            return self._no_monkey.count(self)

    def get(self, *args, **kwargs):
        # .get() uses the same .iterator() method to fetch data,
        # so here we add 'fetch' to ops
        if self._cacheprofile and 'get' in self._cacheconf['ops']:
            # NOTE: local_get=True enables caching of simple gets in local memory,
            #       which is very fast, but not invalidated.
            # Don't bother with Q-objects, select_related and previous filters,
            # simple gets - thats what we are really up to here.
            if self._cacheprofile['local_get']    \
                and not args                      \
                and not self.query.select_related \
                and not self.query.where.children:
                # NOTE: We use simpler way to generate a cache key to cut costs.
                #       Some day it could produce same key for diffrent requests.
                key = (self.__class__, self.model) + tuple(sorted(kwargs.items()))
                try:
                    return _local_get_cache[key]
                except KeyError:
                    _local_get_cache[key] = self._no_monkey.get(self, *args, **kwargs)
                    return _local_get_cache[key]
                except TypeError:
                    pass # If some arg is unhashable we can't save it to dict key,
                         # we just skip local cache in that case

            if 'fetch' in self._cacheconf['ops']:
                qs = self
            else:
                qs = self._clone().cache()
        else:
            qs = self

        return qs._no_monkey.get(qs, *args, **kwargs)


class ManagerMixin(object):
    def _install_cacheops(self, cls):
        cls._cacheprofile = model_profile(cls)
        if cls._cacheprofile is not None and cls not in _old_objs:
            # Set up signals
            pre_save.connect(self._pre_save, sender=cls)
            post_save.connect(self._post_save, sender=cls)
            post_delete.connect(self._post_delete, sender=cls)
            _old_objs[cls] = {}

            # Install auto-created models as their module attributes to make them picklable
            module = sys.modules[cls.__module__]
            if not hasattr(module, cls.__name__):
                setattr(module, cls.__name__, cls)

    def contribute_to_class(self, cls, name):
        self._no_monkey.contribute_to_class(self, cls, name)
        self._install_cacheops(cls)

    def _pre_save(self, sender, instance, **kwargs):
        if instance.pk is not None:
            try:
                _old_objs[sender][instance.pk] = sender.objects.get(pk=instance.pk)
            except sender.DoesNotExist:
                pass

    def _post_save(self, sender, instance, **kwargs):
        """
        Invokes invalidations for both old and new versions of saved object
        """
        old = _old_objs[sender].pop(instance.pk, None)
        if old:
            invalidate_obj(old)
        invalidate_obj(instance)

        # Enabled cache_on_save makes us write saved object to cache.
        # Later it can be retrieved with .get(<cache_on_save_field>=<value>)
        # <cache_on_save_field> is pk unless specified.
        # This sweet trick saves a db request and helps with slave lag.
        cache_on_save = instance._cacheprofile.get('cache_on_save')
        if cache_on_save:
            # HACK: We get this object "from field" so it can contain
            #       some undesirable attributes or other objects attached.
            #       RelatedField accessors do that, for example.
            #
            #       So we strip down any _*_cache attrs before saving
            #       and later reassign them
            # Stripping up undesirable attributes
            unwanted_attrs = [k for k in instance.__dict__.keys()
                                if k.startswith('_') and k.endswith('_cache')]
            unwanted_dict = dict((k, instance.__dict__[k]) for k in unwanted_attrs)
            for k in unwanted_attrs:
                del instance.__dict__[k]

            key = 'pk' if cache_on_save is True else cache_on_save
            # Django doesn't allow filters like related_id = 1337.
            # So we just hacky strip _id from end of a key
            # TODO: make it right, _meta.get_field() should help
            filter_key = key[:-3] if key.endswith('_id') else key

            cond = {filter_key: getattr(instance, key)}
            qs = sender.objects.inplace().filter(**cond).order_by()
            if MAX_GET_RESULTS:
                qs = qs[:MAX_GET_RESULTS + 1]
            qs._cache_results(qs._cache_key(), [instance])

            # Reverting stripped attributes
            instance.__dict__.update(unwanted_dict)

    def _post_delete(self, sender, instance, **kwargs):
        """
        Invalidation upon object deletion.
        """
        # NOTE: this will behave wrong if someone changed object fields
        #       before deletion (why anyone will do that?)
        invalidate_obj(instance)

    # Django 1.5- compatability
    if django.VERSION < (1, 6):
        def get_queryset(self):
            return self.get_query_set()

    def inplace(self):
        return self.get_queryset().inplace()

    def get(self, *args, **kwargs):
        return self.get_queryset().inplace().get(*args, **kwargs)

    def cache(self, *args, **kwargs):
        return self.get_queryset().cache(*args, **kwargs)

    def nocache(self, *args, **kwargs):
        return self.get_queryset().nocache(*args, **kwargs)


def invalidate_m2m(sender=None, instance=None, model=None, action=None, pk_set=None, **kwargs):
    """
    Invoke invalidation on m2m changes.
    """
    if action in ('post_add', 'post_remove', 'post_clear'):
        invalidate_model(sender) # NOTE: this is harsh, but what's the alternative?
        invalidate_obj(instance)
        # TODO: more granular invalidation for referenced models
        invalidate_model(model)


installed = False

def install_cacheops():
    """
    Installs cacheops by numerous monkey patches
    """
    global installed
    if installed:
        return # just return for now, second call is probably done due cycle imports
    installed = True

    monkey_mix(Manager, ManagerMixin)
    monkey_mix(QuerySet, QuerySetMixin)
    QuerySet._cacheprofile = QuerySetMixin._cacheprofile
    QuerySet._cloning = QuerySetMixin._cloning
    monkey_mix(ValuesQuerySet, QuerySetMixin, ['iterator'])
    monkey_mix(ValuesListQuerySet, QuerySetMixin, ['iterator'])
    monkey_mix(DateQuerySet, QuerySetMixin, ['iterator'])

    # Install profile and signal handlers for any earlier created models
    from django.db.models import get_models
    for model in get_models(include_auto_created=True):
        model._default_manager._install_cacheops(model)

    # Turn off caching in admin
    from django.conf import settings
    if 'django.contrib.admin' in settings.INSTALLED_APPS:
        from django.contrib.admin.options import ModelAdmin
        def ModelAdmin_queryset(self, request):
            return o_ModelAdmin_queryset(self, request).nocache()
        o_ModelAdmin_queryset = ModelAdmin.queryset
        ModelAdmin.queryset = ModelAdmin_queryset

    # bind m2m changed handler
    m2m_changed.connect(invalidate_m2m)

########NEW FILE########
__FILENAME__ = simple
# -*- coding: utf-8 -*-
try:
    import cPickle as pickle
except ImportError:
    import pickle
from functools import wraps
import os, time

from django.conf import settings

from cacheops import cross
from cacheops.conf import redis_client


__all__ = ('cache', 'cached', 'file_cache', 'CacheMiss')


class CacheMiss(Exception):
    pass


class BaseCache(object):
    """
    Simple cache with time-based invalidation
    """
    def cached(self, extra=None, timeout=None):
        """
        A decorator for caching function calls
        """
        def decorator(func):
            def get_cache_key(*args, **kwargs):
                # Calculating cache key based on func and arguments
                md5 = cross.md5()
                md5.update('%s.%s' % (func.__module__, func.__name__))
                # TODO: make it more civilized
                if extra is not None:
                    if isinstance(extra, (list, tuple)):
                        md5.update(':'.join(map(str, extra)))
                    else:
                        md5.update(str(extra))
                if args:
                    md5.update(repr(args))
                if kwargs:
                    md5.update(repr(sorted(kwargs.items())))

                return 'c:%s' % md5.hexdigest()

            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = get_cache_key(*args, **kwargs)
                try:
                    result = self.get(cache_key)
                except CacheMiss:
                    result = func(*args, **kwargs)
                    self.set(cache_key, result, timeout)

                return result

            def invalidate(*args, **kwargs):
                cache_key = get_cache_key(*args, **kwargs)
                self.delete(cache_key)
            wrapper.invalidate = invalidate

            return wrapper
        return decorator


class RedisCache(BaseCache):
    def __init__(self, conn):
        self.conn = conn

    def get(self, cache_key):
        data = self.conn.get(cache_key)
        if data is None:
            raise CacheMiss
        return pickle.loads(data)

    def set(self, cache_key, data, timeout=None):
        pickled_data = pickle.dumps(data, -1)
        if timeout is not None:
            self.conn.setex(cache_key, timeout, pickled_data)
        else:
            self.conn.set(cache_key, pickled_data)

    def delete(self, cache_key):
        self.conn.delete(cache_key)

cache = RedisCache(redis_client)
cached = cache.cached


FILE_CACHE_DIR = getattr(settings, 'FILE_CACHE_DIR', '/tmp/cacheops_file_cache')
FILE_CACHE_TIMEOUT = getattr(settings, 'FILE_CACHE_TIMEOUT', 60*60*24*30)

class FileCache(BaseCache):
    """
    A file cache which fixes bugs and misdesign in django default one.
    Uses mtimes in the future to designate expire time. This makes unnecessary
    reading stale files.
    """
    def __init__(self, path, timeout=FILE_CACHE_TIMEOUT):
        self._dir = path
        self._default_timeout = timeout

    def _key_to_filename(self, key):
        """
        Returns a filename corresponding to cache key
        """
        digest = cross.md5(key).hexdigest()
        return os.path.join(self._dir, digest[-2:], digest[:-2])

    def get(self, key):
        filename = self._key_to_filename(key)
        try:
            # Remove file if it's stale
            if time.time() >= os.stat(filename).st_mtime:
                self.delete(filename)
                raise CacheMiss

            with open(filename, 'rb') as f:
                return pickle.load(f)
        except (IOError, OSError, EOFError, pickle.PickleError):
            raise CacheMiss

    def set(self, key, data, timeout=None):
        filename = self._key_to_filename(key)
        dirname = os.path.dirname(filename)

        if timeout is None:
            timeout = self._default_timeout

        try:
            if not os.path.exists(dirname):
                os.makedirs(dirname)

            # Use open with exclusive rights to prevent data corruption
            f = os.open(filename, os.O_EXCL | os.O_WRONLY | os.O_CREAT)
            try:
                os.write(f, pickle.dumps(data, pickle.HIGHEST_PROTOCOL))
            finally:
                os.close(f)

            # Set mtime to expire time
            os.utime(filename, (0, time.time() + timeout))
        except (IOError, OSError):
            pass

    def delete(self, fname):
        try:
            os.remove(fname)
            # Trying to remove directory in case it's empty
            dirname = os.path.dirname(fname)
            os.rmdir(dirname)
        except (IOError, OSError):
            pass

file_cache = FileCache(FILE_CACHE_DIR)

########NEW FILE########
__FILENAME__ = cacheops
from __future__ import absolute_import
import inspect

from django.template.base import TagHelperNode, parse_bits
from django.template import Library


register = Library()


def tag_helper(func):
    name = func.__name__
    params, varargs, varkw, defaults = inspect.getargspec(func)

    class HelperNode(TagHelperNode):
        def __init__(self, takes_context, args, kwargs, nodelist=None):
            super(HelperNode, self).__init__(takes_context, args, kwargs)
            self.nodelist = nodelist

        def render(self, context):
            args, kwargs = self.get_resolved_arguments(context)
            return func(context, self.nodelist, *args, **kwargs)

    def _compile(parser, token):
        # content
        nodelist = parser.parse(('end' + name,))
        parser.delete_first_token()

        # args
        bits = token.split_contents()[1:]
        args, kwargs = parse_bits(parser, bits, params[2:], varargs, varkw, defaults,
                                  takes_context=None, name=name)
        return HelperNode(False, args, kwargs, nodelist)

    register.tag(name=name, compile_function=_compile)
    return func


import cacheops
from cacheops.utils import carefully_strip_whitespace

@tag_helper
def cached(context, nodelist, timeout, fragment_name, *extra):
    @cacheops.cached(timeout=timeout, extra=(fragment_name,) + extra)
    def _handle_tag():
        # TODO: make this cache preparation configurable
        return carefully_strip_whitespace(nodelist.render(context))

    return _handle_tag()

@tag_helper
def cached_as(context, nodelist, queryset, timeout, fragment_name, *extra):
    @cacheops.cached_as(queryset, timeout=timeout, extra=(fragment_name,) + extra)
    def _handle_tag():
        # TODO: make this cache preparation configurable
        return carefully_strip_whitespace(nodelist.render(context))

    return _handle_tag()

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from operator import concat, itemgetter
from itertools import product
import inspect

try:
    from itertools import imap
except ImportError:
    # Use Python 2 map/filter here for now
    imap = map
    map = lambda f, seq: list(imap(f, seq))
    ifilter = filter
    filter = lambda f, seq: list(ifilter(f, seq))
    from functools import reduce
import six
from cacheops import cross
from cacheops.conf import redis_client
from cacheops.funcy import memoize

import django
from django.db import models
from django.db.models.query import QuerySet
from django.db.models.sql import AND, OR
from django.db.models.sql.query import Query, ExtraWhere
from django.db.models.sql.where import EverythingNode, NothingNode
from django.db.models.sql.expressions import SQLEvaluator
# A new thing in Django 1.6
try:
    from django.db.models.sql.where import SubqueryConstraint
except ImportError:
    class SubqueryConstraint(object):
        pass


LONG_DISJUNCTION = 8


def non_proxy(model):
    while model._meta.proxy:
        # Every proxy model has exactly one non abstract parent model
        model = next(b for b in model.__bases__
                       if issubclass(b, models.Model) and not b._meta.abstract)
    return model


if django.VERSION < (1, 6):
    def get_model_name(model):
        return '%s.%s' % (model._meta.app_label, model._meta.module_name)
else:
    def get_model_name(model):
        return '%s.%s' % (model._meta.app_label, model._meta.model_name)


class MonkeyProxy(object):
    def __init__(self, cls):
        monkey_bases = tuple(b._no_monkey for b in cls.__bases__ if hasattr(b, '_no_monkey'))
        for monkey_base in monkey_bases:
            for name, value in monkey_base.__dict__.items():
                setattr(self, name, value)


def monkey_mix(cls, mixin, methods=None):
    """
    Mixes a mixin into existing class.
    Does not use actual multi-inheritance mixins, just monkey patches methods.
    Mixin methods can call copies of original ones stored in `_no_monkey` proxy:

    class SomeMixin(object):
        def do_smth(self, arg):
            ... do smth else before
            self._no_monkey.do_smth(self, arg)
            ... do smth else after
    """
    assert '_no_monkey' not in cls.__dict__, 'Multiple monkey mix not supported'
    cls._no_monkey = MonkeyProxy(cls)

    if methods is None:
        # NOTE: there no such thing as unbound method in Python 3, it uses naked functions,
        #       so we use some six based altering here
        isboundmethod = inspect.isfunction if six.PY3 else inspect.ismethod
        methods = inspect.getmembers(mixin, isboundmethod)
    else:
        methods = [(m, getattr(mixin, m)) for m in methods]

    for name, method in methods:
        if hasattr(cls, name):
            setattr(cls._no_monkey, name, getattr(cls, name))
        # NOTE: remember, there is no bound methods in Python 3
        setattr(cls, name, six.get_unbound_function(method))


NON_SERIALIZABLE_FIELDS = (
    models.FileField,
    models.TextField, # One should not filter by long text equality
)
if hasattr(models, 'BinaryField'):
    NON_SERIALIZABLE_FIELDS += (models.BinaryField,) # Not possible to filter by it


def dnf(qs):
    """
    Converts sql condition tree to DNF.

    Any negations, conditions with lookups other than __exact or __in,
    conditions on joined models and subrequests are ignored.
    __in is converted into = or = or = ...
    """
    SOME = object()

    def negate(el):
        return SOME if el is SOME else \
               (el[0], el[1], not el[2])

    def strip_negates(conj):
        return [term[:2] for term in conj if term is not SOME and term[2]]

    def _dnf(where):
        if isinstance(where, tuple):
            constraint, lookup, annotation, value = where
            if constraint.alias != alias or isinstance(value, (QuerySet, Query, SQLEvaluator)):
                return [[SOME]]
            elif lookup == 'exact':
                if isinstance(constraint.field, NON_SERIALIZABLE_FIELDS):
                    return [[SOME]]
                else:
                    # attribute, value, negation
                    return [[(attname_of(model, constraint.col), value, True)]]
            elif lookup == 'isnull':
                return [[(attname_of(model, constraint.col), None, value)]]
            elif lookup == 'in' and len(value) < LONG_DISJUNCTION:
                return [[(attname_of(model, constraint.col), v, True)] for v in value]
            else:
                return [[SOME]]
        elif isinstance(where, EverythingNode):
            return [[]]
        elif isinstance(where, NothingNode):
            return []
        elif isinstance(where, (ExtraWhere, SubqueryConstraint)):
            return [[SOME]]
        elif len(where) == 0:
            return [[]]
        else:
            chilren_dnfs = map(_dnf, where.children)

            if len(chilren_dnfs) == 0:
                return [[]]
            elif len(chilren_dnfs) == 1:
                result = chilren_dnfs[0]
            else:
                # Just unite children joined with OR
                if where.connector == OR:
                    result = reduce(concat, chilren_dnfs)
                # Use Cartesian product to AND children
                else:
                    result = [reduce(concat, p) for p in product(*chilren_dnfs)]

            # Negating and expanding brackets
            if where.negated:
                result = [map(negate, p) for p in product(*result)]

            return result

    where = qs.query.where
    model = qs.model
    alias = model._meta.db_table

    result = _dnf(where)
    # Cutting out negative terms and negation itself
    result = [strip_negates(conj) for conj in result]
    # Any empty conjunction eats up the rest
    # NOTE: a more elaborate DNF reduction is not really needed,
    #       just keep your querysets sane.
    if not all(result):
        return [[]]
    return map(sorted, result)


def attname_of(model, col, cache={}):
    if model not in cache:
        cache[model] = dict((f.db_column, f.attname) for f in model._meta.fields)
    return cache[model].get(col, col)


@memoize
def stamp_fields(model):
    """
    Returns serialized description of model fields.
    """
    stamp = str([(f.name, f.attname, f.db_column, f.__class__) for f in model._meta.fields])
    return cross.md5(stamp).hexdigest()


### Lua script loader

import os.path

@memoize
def load_script(name):
    filename = os.path.join(os.path.dirname(__file__), 'lua/%s.lua' % name)
    with open(filename) as f:
        code = f.read()
    return redis_client.register_script(code)


### Whitespace handling for template tags

import re
from django.utils.safestring import mark_safe

NEWLINE_BETWEEN_TAGS = mark_safe('>\n<')
SPACE_BETWEEN_TAGS = mark_safe('> <')

def carefully_strip_whitespace(text):
    text = re.sub(r'>\s*\n\s*<', NEWLINE_BETWEEN_TAGS, text)
    text = re.sub(r'>\s{2,}<', SPACE_BETWEEN_TAGS, text)
    return text

########NEW FILE########
__FILENAME__ = fakecacheops
import redis
from django.db.models import Manager
from django.db.models.query import QuerySet
from django.conf import settings


# Connecting to redis
try:
    redis_conf = settings.CACHEOPS_REDIS
except AttributeError:
    raise ImproperlyConfigured('You must specify non-empty CACHEOPS_REDIS setting to use cacheops')

redis_client = redis.StrictRedis(**redis_conf)


# query
QuerySet._cache_key = lambda self, extra=None: None
Manager.nocache = lambda self: self
Manager.cache = lambda self: self
Manager.inplace = lambda self: self


# invalidation
def invalidate_obj(obj):
    pass

def invalidate_model(model):
    pass


# substitute cacheops
import sys
sys.modules['cacheops'] = sys.modules['fakecacheops']
sys.modules['cacheops.conf'] = sys.modules['fakecacheops']

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

from django.core.management import call_command
call_command(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python
import os, sys, re
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

import django
from django.core.management import call_command

names_prefix = 'tests.tests' if django.VERSION >= (1, 6) else 'tests'
names = next((a for a in sys.argv[1:] if not a.startswith('-')), None)

if names and re.search(r'^\d+$', names):
    names = names_prefix + '.IssueTests.test_' + names
elif names and not names.startswith('tests.'):
    names = names_prefix + '.' + names
else:
    names = names_prefix

call_command('test', names, failfast='-x' in sys.argv)

########NEW FILE########
__FILENAME__ = bench
from cacheops import invalidate_obj, invalidate_model
from cacheops.conf import redis_client
from .models import Category, Post, Extra


get_key = Category.objects.filter(pk=1).order_by()._cache_key()
def invalidate_get():
    redis_client.delete(get_key)

def do_get():
    Category.objects.cache().get(pk=1)

def do_get_no_cache():
    Category.objects.nocache().get(pk=1)


count_key = Category.objects.all()._cache_key(extra='count')
def invalidate_count():
    redis_client.delete(count_key)

def do_count():
    Category.objects.cache().count()

def do_count_no_cache():
    Category.objects.nocache().count()


fetch_qs = Category.objects.all()
fetch_key = fetch_qs._cache_key()

def invalidate_fetch():
    redis_client.delete(fetch_key)

def do_fetch():
    list(Category.objects.cache().all())

def do_fetch_no_cache():
    list(Category.objects.nocache().all())

def do_fetch_construct():
    Category.objects.all()

def do_fetch_cache_key():
    fetch_qs._cache_key()

filter_qs = Category.objects.filter(pk=1)
def do_filter_cache_key():
    filter_qs._cache_key()


def do_common_construct():
    return Category.objects.filter(pk=1).exclude(title__contains='Hi').order_by('title')[:20]

def do_common_inplace():
    return Category.objects.inplace() \
                   .filter(pk=1).exclude(title__contains='Hi').order_by('title')[:20]

common_qs = do_common_construct()
def do_common_cache_key():
    common_qs._cache_key()


def prepare_obj():
    return Category.objects.cache().get(pk=1)

def do_invalidate_obj(obj):
    invalidate_obj(obj)

def do_save_obj(obj):
    obj.save()


### Complex queryset

from django.db.models import Q

def do_complex_construct():
    return Post.objects.filter(id__gt=1, title='Hi').exclude(category__in=[10, 20]) \
                       .filter(Q(id__range=(10, 20)) | ~Q(title__contains='abc'))

def do_complex_inplace():
    return Post.objects.inplace()                                                   \
                       .filter(id__gt=1, title='Hi').exclude(category__in=[10, 20]) \
                       .filter(Q(id__range=(10, 20)) | ~Q(title__contains='abc'))

complex_qs = do_complex_construct()
def do_complex_cache_key():
    return complex_qs._cache_key()


### More invalidation

def prepare_cache():
    def _variants(*args, **kwargs):
        qs = Extra.objects.cache().filter(*args, **kwargs)
        qs.count()
        list(qs)
        list(qs[:2])
        list(qs.values())

    _variants(pk=1)
    _variants(post=1)
    _variants(tag=5)
    _variants(to_tag=10)

    _variants(pk=1, post=1)
    _variants(pk=1, tag=5)
    _variants(post=1, tag=5)

    _variants(pk=1, post=1, tag=5)
    _variants(pk=1, post=1, to_tag=10)

    _variants(Q(pk=1) | Q(tag=5))
    _variants(Q(pk=1) | Q(tag=1))
    _variants(Q(pk=1) | Q(tag=2))
    _variants(Q(pk=1) | Q(tag=3))
    _variants(Q(pk=1) | Q(tag=4))

    return Extra.objects.cache().get(pk=1)

def do_invalidate_model(obj):
    invalidate_model(obj.__class__)


TESTS = [
    ('get_no_cache', {'run': do_get_no_cache}),
    ('get_hit',  {'prepare_once': do_get, 'run': do_get}),
    ('get_miss', {'prepare': invalidate_get, 'run': do_get}),

    ('count_no_cache', {'run': do_count_no_cache}),
    ('count_hit',  {'prepare_once': do_count, 'run': do_count}),
    ('count_miss', {'prepare': invalidate_count, 'run': do_count}),

    ('fetch_construct',  {'run': do_fetch_construct}),
    ('fetch_no_cache',  {'run': do_fetch_no_cache}),
    ('fetch_hit',  {'prepare_once': do_fetch, 'run': do_fetch}),
    ('fetch_miss', {'prepare': invalidate_fetch, 'run': do_fetch}),
    ('fetch_cache_key', {'run': do_fetch_cache_key}),

    ('filter_cache_key', {'run': do_filter_cache_key}),
    ('common_construct',  {'run': do_common_construct}),
    ('common_inplace',  {'run': do_common_inplace}),
    ('common_cache_key', {'run': do_common_cache_key}),

    ('invalidate_obj', {'prepare': prepare_obj, 'run': do_invalidate_obj}),
    ('save_obj', {'prepare': prepare_obj, 'run': do_save_obj}),

    ('complex_construct', {'run': do_complex_construct}),
    ('complex_inplace', {'run': do_complex_inplace}),
    ('complex_cache_key', {'run': do_complex_cache_key}),

    ('big_invalidate', {'prepare': prepare_cache, 'run': do_invalidate_obj}),
    ('model_invalidate', {'prepare': prepare_cache, 'run': do_invalidate_model}),
]

########NEW FILE########
__FILENAME__ = models
import six
from datetime import date, datetime, time

from django.db import models
from django.db.models.query import QuerySet
from django.db.models import sql
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User


### For basic tests and bench

class Category(models.Model):
    title = models.CharField(max_length=128)

    def __unicode__(self):
        return self.title

class Post(models.Model):
    title = models.CharField(max_length=128)
    category = models.ForeignKey(Category)
    visible = models.BooleanField(default=True)

    def __unicode__(self):
        return self.title

class Extra(models.Model):
    post = models.OneToOneField(Post)
    tag = models.IntegerField(db_column='custom_column_name', unique=True)
    to_tag = models.ForeignKey('self', to_field='tag', null=True)

    def __unicode__(self):
        return 'Extra(post_id=%s, tag=%s)' % (self.post_id, self.tag)


### Specific and custom fields

class CustomValue(object):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

class CustomField(six.with_metaclass(models.SubfieldBase, models.Field)):
    def db_type(self, connection):
        return 'text'

    def to_python(self, value):
        if isinstance(value, CustomValue):
            return value
        return CustomValue(value)

    def get_prep_value(self, value):
        return value.value

class CustomWhere(sql.where.WhereNode):
    pass

class CustomQuery(sql.Query):
    pass

class CustomManager(models.Manager):
    def get_query_set(self):
        q = CustomQuery(self.model, CustomWhere)
        return QuerySet(self.model, q)
    get_queryset = get_query_set


class IntegerArrayField(six.with_metaclass(models.SubfieldBase, models.Field)):
    def db_type(self, connection):
        return 'text'

    def to_python(self, value):
        if isinstance(value, list):
            return value
        return map(int, value.split(','))

    def get_prep_value(self, value):
        return ','.join(map(str, value))


class Weird(models.Model):
    date_field = models.DateField(default=date(2000, 1, 1))
    datetime_field = models.DateTimeField(default=datetime(2000, 1, 1, 10, 10))
    time_field = models.TimeField(default=time(10, 10))
    list_field = IntegerArrayField(default=lambda: [])
    custom_field = CustomField(default=CustomValue('default'))

    objects = models.Manager()
    customs = CustomManager()

# 16
class Profile(models.Model):
    user = models.ForeignKey(User)
    tag = models.IntegerField()


# Proxy model
class Video(models.Model):
    title = models.CharField(max_length=128)

class VideoProxy(Video):
    class Meta:
        proxy = True


# Multi-table inheritance
class Media(models.Model):
    name = models.CharField(max_length=128)

class Movie(Media):
    year = models.IntegerField()


# Decimals
class Point(models.Model):
    x = models.DecimalField(decimal_places=6, max_digits=8, blank=True, default=0.0)



# 29
class Label(models.Model):
    text = models.CharField(max_length=127, blank=True, default='')

class MachineBrand(models.Model):
    labels = models.ManyToManyField(Label)


# local_get
class Local(models.Model):
    tag = models.IntegerField(null=True)


# 44
class Photo(models.Model):
    liked_user = models.ManyToManyField(User, through="PhotoLike")

class PhotoLike(models.Model):
    user = models.ForeignKey(User)
    photo = models.ForeignKey(Photo)
    timestamp = models.DateTimeField(auto_now_add=True)


# 45
class CacheOnSaveModel(models.Model):
    title = models.CharField(max_length=32)


# 47
class DbAgnostic(models.Model):
    pass

class DbBinded(models.Model):
    pass


# 62
class Product(models.Model):
    name = models.CharField(max_length=32)

class ProductReview(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', null=True)
    status = models.IntegerField()


# 70
class GenericContainer(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    name = models.CharField(max_length=30)

class Contained(models.Model):
    name = models.CharField(max_length=30)
    containers = generic.GenericRelation(GenericContainer)

########NEW FILE########
__FILENAME__ = settings
import os

INSTALLED_APPS = [
    'cacheops' if os.environ.get('CACHEOPS') != 'FAKE' else 'fakecacheops',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'tests',
]

AUTH_PROFILE_MODULE = 'tests.UserProfile'

# Django replaces this, but it still wants it. *shrugs*
DATABASE_ENGINE = 'django.db.backends.sqlite3',
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'sqlite.db'
    },
    'slave': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'sqlite.db'
    }
}

CACHEOPS_REDIS = {
    'host': 'localhost',
    'port': 6379,
    'db': 13,
    'socket_timeout': 3,
}
CACHEOPS = {
    'tests.local': ('just_enable', 60*60, {'local_get': True}),
    'tests.cacheonsavemodel': ('just_enable', 60*60, {'cache_on_save': True}),
    'tests.dbbinded': ('just_enable', 60*60, {'db_agnostic': False}),
    'tests.issue': ('all', 60*60),
    'tests.genericcontainer': ('all', 60*60),
    '*.*': ('just_enable', 60*60),
}

# We need to catch any changes in django
CACHEOPS_STRICT_STRINGIFY = True

SECRET_KEY = 'abc'

########NEW FILE########
__FILENAME__ = tests
import os, re, copy
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import django
from django.test import TestCase
from django.contrib.auth.models import User
from django.template import Context, Template

from cacheops import invalidate_all, invalidate_model, invalidate_obj, cached
from .models import *


class BaseTestCase(TestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()
        invalidate_all()


class BasicTests(BaseTestCase):
    fixtures = ['basic']

    def test_it_works(self):
        with self.assertNumQueries(1):
            cnt1 = Category.objects.cache().count()
            cnt2 = Category.objects.cache().count()
            self.assertEqual(cnt1, cnt2)

    def test_empty(self):
        with self.assertNumQueries(0):
            list(Category.objects.cache().filter(id__in=[]))

    def test_exact(self):
        list(Category.objects.filter(pk=1).cache())
        with self.assertNumQueries(0):
            list(Category.objects.filter(pk__exact=1).cache())

    def test_some(self):
        # Ignoring SOME condition lead to wrong DNF for this queryset,
        # which leads to no invalidation
        list(Category.objects.exclude(pk__in=range(10), pk__isnull=False).cache())
        c = Category.objects.get(pk=1)
        c.save()
        with self.assertNumQueries(1):
            list(Category.objects.exclude(pk__in=range(10), pk__isnull=False).cache())

    def test_invalidation(self):
        post = Post.objects.cache().get(pk=1)
        post.title += ' changed'
        post.save()

        with self.assertNumQueries(1):
            changed_post = Post.objects.cache().get(pk=1)
            self.assertEqual(post.title, changed_post.title)

    def test_invalidate_by_foreign_key(self):
        posts = list(Post.objects.cache().filter(category=1))
        Post.objects.create(title='New Post', category_id=1)

        with self.assertNumQueries(1):
            changed_posts = list(Post.objects.cache().filter(category=1))
            self.assertEqual(len(changed_posts), len(posts) + 1)

    def test_invalidate_by_one_to_one(self):
        extras = list(Extra.objects.cache().filter(post=3))
        Extra.objects.create(post_id=3, tag=0)

        with self.assertNumQueries(1):
            changed_extras = list(Extra.objects.cache().filter(post=3))
            self.assertEqual(len(changed_extras), len(extras) + 1)

    def test_invalidate_by_boolean(self):
        count = Post.objects.cache().filter(visible=True).count()

        post = Post.objects.get(pk=1, visible=True)
        post.visible = False
        post.save()

        with self.assertNumQueries(1):
            new_count = Post.objects.cache().filter(visible=True).count()
            self.assertEqual(new_count, count - 1)

    def test_db_column(self):
        e = Extra.objects.cache().get(tag=5)
        e.save()

    def test_fk_to_db_column(self):
        e = Extra.objects.cache().get(to_tag__tag=5)
        e.save()

        with self.assertNumQueries(1):
            Extra.objects.cache().get(to_tag=5)

    def test_expressions(self):
        from django.db.models import F
        queries = (
            {'tag': F('tag')},
            {'tag': F('to_tag')},
            {'tag': F('to_tag') * 2},
            {'tag': F('to_tag') + (F('tag') / 2)},
        )
        if hasattr(F, 'bitor'):
            queries += (
                {'tag': F('tag').bitor(5)},
                {'tag': F('to_tag').bitor(5)},
                {'tag': F('tag').bitor(5) + 1},
                {'tag': F('tag').bitor(5) * F('to_tag').bitor(5)}
            )
        count = len(queries)
        for c in (count, 0):
            with self.assertNumQueries(c):
                for q in queries:
                    Extra.objects.cache().filter(**q).count()

    def test_combine(self):
        qs = Post.objects.filter(pk__in=[1, 2]) & Post.objects.all()
        self.assertEqual(list(qs.cache()), list(qs))

        qs = Post.objects.filter(pk__in=[1, 2]) | Post.objects.none()
        self.assertEqual(list(qs.cache()), list(qs))


from datetime import date, datetime, time

class WeirdTests(BaseTestCase):
    def _template(self, field, value, invalidation=True):
        qs = Weird.objects.cache().filter(**{field: value})
        count = qs.count()

        Weird.objects.create(**{field: value})

        if invalidation:
            with self.assertNumQueries(1):
                self.assertEqual(qs.count(), count + 1)

    def test_date(self):
        self._template('date_field', date.today())

    def test_datetime(self):
        self._template('datetime_field', datetime.now())

    def test_time(self):
        self._template('time_field', time(10, 30))

    def test_list(self):
        self._template('list_field', [1, 2])

    def test_custom(self):
        self._template('custom_field', CustomValue('some'))

    def test_weird_custom(self):
        class WeirdCustom(CustomValue):
            def __str__(self):
                return 'other'
        self._template('custom_field', WeirdCustom('some'))

    def test_custom_query(self):
        import cacheops.query
        try:
            cacheops.query.STRICT_STRINGIFY = False
            list(Weird.customs.cache())
        finally:
            cacheops.query.STRICT_STRINGIFY = True


class TemplateTests(BaseTestCase):
    @unittest.skipIf(django.VERSION < (1, 4), "not supported Django prior to 1.4")
    def test_cached(self):
        counts = {'a': 0, 'b': 0}
        def inc_a():
            counts['a'] += 1
            return ''
        def inc_b():
            counts['b'] += 1
            return ''

        t = Template("""
            {% load cacheops %}
            {% cached 60 'a' %}.a{{ a }}{% endcached %}
            {% cached 60 'a' %}.a{{ a }}{% endcached %}
            {% cached 60 'a' 'variant' %}.a{{ a }}{% endcached %}
            {% cached timeout=60 fragment_name='b' %}.b{{ b }}{% endcached %}
        """)

        s = t.render(Context({'a': inc_a, 'b': inc_b}))
        self.assertEqual(re.sub(r'\s+', '', s), '.a.a.a.b')
        self.assertEqual(counts, {'a': 2, 'b': 1})

    @unittest.skipIf(django.VERSION < (1, 4), "not supported Django prior to 1.4")
    def test_cached_as(self):
        counts = {'a': 0}
        def inc_a():
            counts['a'] += 1
            return ''

        qs = Post.objects.all()

        t = Template("""
            {% load cacheops %}
            {% cached_as qs 0 'a' %}.a{{ a }}{% endcached_as %}
            {% cached_as qs timeout=60 fragment_name='a' %}.a{{ a }}{% endcached_as %}
            {% cached_as qs fragment_name='a' timeout=60 %}.a{{ a }}{% endcached_as %}
        """)

        s = t.render(Context({'a': inc_a, 'qs': qs}))
        self.assertEqual(re.sub(r'\s+', '', s), '.a.a.a')
        self.assertEqual(counts['a'], 1)

        t.render(Context({'a': inc_a, 'qs': qs}))
        self.assertEqual(counts['a'], 1)

        invalidate_model(Post)
        t.render(Context({'a': inc_a, 'qs': qs}))
        self.assertEqual(counts['a'], 2)


class IssueTests(BaseTestCase):
    fixtures = ['basic']

    def setUp(self):
        user = User.objects.create(username='Suor')
        Profile.objects.create(pk=2, user=user, tag=10)
        super(IssueTests, self).setUp()

    def test_16(self):
        p = Profile.objects.cache().get(user__id__exact=1)
        p.save()

        with self.assertNumQueries(1):
            Profile.objects.cache().get(user=1)

    def test_29(self):
        MachineBrand.objects.exclude(labels__in=[1, 2, 3]).cache().count()

    def test_39(self):
        list(Point.objects.filter(x=7).cache())

    def test_45(self):
        m = CacheOnSaveModel(title="test")
        m.save()

        with self.assertNumQueries(0):
            CacheOnSaveModel.objects.cache().get(pk=m.pk)

    def test_54(self):
        qs = Category.objects.all()
        list(qs) # force load objects to quesryset cache
        qs.count()

    def test_56(self):
        Post.objects.exclude(extra__in=[1, 2]).cache().count()

    def test_57(self):
        list(Post.objects.filter(category__in=Category.objects.nocache()).cache())

    def test_58(self):
        list(Post.objects.cache().none())

    def test_62(self):
        # setup
        product = Product.objects.create(name='62')
        ProductReview.objects.create(product=product, status=0)
        ProductReview.objects.create(product=None, status=0)

        # Test related manager filtering works, .get() will throw MultipleObjectsReturned if not
        # The bug is related manager not respected when .get() is called
        product.reviews.get(status=0)

    def test_70(self):
        Contained(name="aaa").save()
        contained_obj = Contained.objects.get(name="aaa")
        GenericContainer(content_object=contained_obj, name="bbb").save()

        qs = Contained.objects.cache().filter(containers__name="bbb")
        list(qs)

    def test_82(self):
        list(copy.deepcopy(Post.objects.all()).cache())


@unittest.skipIf(not os.environ.get('LONG'), "Too long")
class LongTests(BaseTestCase):
    fixtures = ['basic']

    def test_big_invalidation(self):
        for x in range(8000):
            list(Category.objects.cache().exclude(pk=x))

        c = Category.objects.get(pk=1)
        invalidate_obj(c) # lua unpack() fails with 8000 keys, workaround works


class LocalGetTests(BaseTestCase):
    def setUp(self):
        Local.objects.create(pk=1)
        super(LocalGetTests, self).setUp()

    def test_unhashable_args(self):
        Local.objects.cache().get(pk__in=[1, 2])


class ManyToManyTests(BaseTestCase):
    def setUp(self):
        self.suor = User.objects.create(username='Suor')
        self.peterdds = User.objects.create(username='peterdds')
        self.photo = Photo.objects.create()
        PhotoLike.objects.create(user=self.suor, photo=self.photo)
        super(ManyToManyTests, self).setUp()

    @unittest.expectedFailure
    def test_44(self):
        make_query = lambda: list(self.photo.liked_user.order_by('id').cache())
        self.assertEqual(make_query(), [self.suor])

        # query cache won't be invalidated on this create, since PhotoLike is through model
        PhotoLike.objects.create(user=self.peterdds, photo=self.photo)
        self.assertEqual(make_query(), [self.suor, self.peterdds])

    def test_44_workaround(self):
        make_query = lambda: list(self.photo.liked_user.order_by('id').cache())
        self.assertEqual(make_query(), [self.suor])

        PhotoLike.objects.create(user=self.peterdds, photo=self.photo)
        invalidate_obj(self.peterdds)
        self.assertEqual(make_query(), [self.suor, self.peterdds])

# Tests for proxy models, see #30
class ProxyTests(BaseTestCase):
    def test_30(self):
        proxies = list(VideoProxy.objects.cache())
        Video.objects.create(title='Pulp Fiction')

        with self.assertNumQueries(1):
            list(VideoProxy.objects.cache())

    def test_30_reversed(self):
        proxies = list(Video.objects.cache())
        VideoProxy.objects.create(title='Pulp Fiction')

        with self.assertNumQueries(1):
            list(Video.objects.cache())

    @unittest.expectedFailure
    def test_interchange(self):
        proxies = list(Video.objects.cache())

        with self.assertNumQueries(0):
            list(VideoProxy.objects.cache())


class MultitableInheritanceTests(BaseTestCase):
    @unittest.expectedFailure
    def test_sub_added(self):
        media_count = Media.objects.cache().count()
        Movie.objects.create(name="Matrix", year=1999)

        with self.assertNumQueries(1):
            self.assertEqual(Media.objects.cache().count(), media_count + 1)

    @unittest.expectedFailure
    def test_base_changed(self):
        matrix = Movie.objects.create(name="Matrix", year=1999)
        list(Movie.objects.cache())

        media = Media.objects.get(pk=matrix.pk)
        media.name = "Matrix (original)"
        media.save()

        with self.assertNumQueries(1):
            list(Movie.objects.cache())


class SimpleCacheTests(BaseTestCase):
    def test_cached(self):
        calls = [0]

        @cached(timeout=100)
        def get_calls(x):
            calls[0] += 1
            return calls[0]

        self.assertEqual(get_calls(1), 1)
        self.assertEqual(get_calls(1), 1)
        self.assertEqual(get_calls(2), 2)
        get_calls.invalidate(2)
        self.assertEqual(get_calls(2), 3)


class DbAgnosticTests(BaseTestCase):
    @unittest.skipIf(django.VERSION < (1, 4), "not supported Django prior to 1.4")
    def test_db_agnostic_by_default(self):
        list(DbAgnostic.objects.cache())

        with self.assertNumQueries(0, using='slave'):
            list(DbAgnostic.objects.cache().using('slave'))

    @unittest.skipIf(django.VERSION < (1, 4), "not supported Django prior to 1.4")
    def test_db_agnostic_disabled(self):
        list(DbBinded.objects.cache())

        with self.assertNumQueries(1, using='slave'):
            list(DbBinded.objects.cache().using('slave'))

########NEW FILE########
