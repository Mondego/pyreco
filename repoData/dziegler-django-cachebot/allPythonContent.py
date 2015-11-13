__FILENAME__ = admin
from django.contrib import admin
from cachebot.models import CacheBotSignals

admin.site.register(CacheBotSignals)

########NEW FILE########
__FILENAME__ = dummy
"Dummy cache backend"

from django.core.cache.backends import dummy

from cachebot.logger import CacheLogDecorator

@CacheLogDecorator
class DummyCache(dummy.DummyCache):
    
    def append(self, **kwargs):
        pass
    
    def prepend(self, **kwargs):
        pass

    def replace(self, **kwargs):
        pass
        
    def smart_incr(self, **kwargs):
        pass
    
    def smart_decr(self, **kwargs):
        pass
########NEW FILE########
__FILENAME__ = memcached
from threading import local

from django.core.cache.backends import memcached

from cachebot.logger import CacheLogDecorator

@CacheLogDecorator
class BaseMemcachedCache(memcached.BaseMemcachedCache):
        
    def _get_memcache_timeout(self, timeout):
        if timeout is None:
            timeout = self.default_timeout
        return timeout
    
    def append(self, key, value, version=None):
        key = self.make_key(key, version=version)
        self._cache.append(key, value)
    
    def prepend(self, key, value, version=None):
        key = self.make_key(key, version=version)
        self._cache.prepend(key, value)
    
    def smart_incr(self, key, delta=1, default=0, **kwargs):
        try:
            return self.incr(key, delta=1)
        except ValueError:
            val = default + delta
            self.add(key, val, **kwargs)
            return val

    def smart_decr(self, key, delta=1, default=0, **kwargs):
        try:
            return self.incr(key, delta=1)
        except ValueError:
            val = default - delta
            self.add(key, val, **kwargs)
            return val
    
    def replace(self, key, value, timeout=0, version=None):
        key = self.make_key(key, version=version)
        return self._cache.replace(key, value, self._get_memcache_timeout(timeout))


class MemcachedCache(BaseMemcachedCache):
    "An implementation of a cache binding using python-memcached"
    def __init__(self, server, params):
        import memcache
        super(MemcachedCache, self).__init__(server, params,
                                             library=memcache,
                                             value_not_found_exception=ValueError)

class PyLibMCCache(BaseMemcachedCache):
    "An implementation of a cache binding using pylibmc"
    def __init__(self, server, params):
        import pylibmc
        self._local = local()
        super(PyLibMCCache, self).__init__(server, params,
                                           library=pylibmc,
                                           value_not_found_exception=pylibmc.NotFound)

    @property
    def _cache(self):
        # PylibMC uses cache options as the 'behaviors' attribute.
        # It also needs to use threadlocals, because some versions of
        # PylibMC don't play well with the GIL.
        client = getattr(self._local, 'client', None)
        if client:
            return client

        client = self._lib.Client(self._servers)
        if self._options:
            client.behaviors = self._options

        self._local.client = client

        return client
########NEW FILE########
__FILENAME__ = conf
import os

from django.conf import settings

CACHE_SECONDS = getattr(settings, 'CACHE_SECONDS', 0)
CACHEBOT_CACHE_GET = getattr(settings, 'CACHEBOT_CACHE_GET', True)
CACHEBOT_CACHE_ALL = getattr(settings, 'CACHEBOT_CACHE_ALL', False)
CACHEBOT_TABLE_BLACKLIST = getattr(settings, 'CACHEBOT_TABLE_BLACKLIST', ('django_session', 'django_content_type', 'south_migrationhistory'))
CACHEBOT_ENABLE_LOG = getattr(settings, 'CACHEBOT_ENABLE_LOG', False)
CACHEBOT_LOG = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'cachebot.log')
CACHEBOT_DEBUG_RESULTS = getattr(settings, 'CACHEBOT_DEBUG_RESULTS', False)
CACHE_INVALIDATION_TIMEOUT = getattr(settings, 'CACHE_INVALIDATION_TIMEOUT', 5)
RUNNING_TESTS = getattr(settings, 'RUNNING_TESTS', False)
if RUNNING_TESTS:
    CACHEBOT_DEBUG_RESULTS = True
    CACHE_INVALIDATION_TIMEOUT = 1

########NEW FILE########
__FILENAME__ = logger
import logging
import threading
from time import time

from django.template import Template, Context
from django.utils.translation import ugettext as _

from cachebot import conf

cachebot_log = logging.getLogger(__name__)

LOG_FUNCS = ('append', 'prepend', 'replace', 'add', 'get', 'set', 'delete', 'get_many', 'incr', 'set_many', 'delete_many')

def CacheLogDecorator(klass):
    orig_init = klass.__init__
    
    def __init__(self, *args, **kwargs):
        self._logger = CacheLogger()
        orig_init(self, *args, **kwargs)
    
    if conf.CACHEBOT_ENABLE_LOG:
        for func in LOG_FUNCS:
            setattr(klass, func, logged_func(getattr(klass, func)))
    
    klass.__init__ = __init__
    return klass
    
class CacheLogger(threading.local):

    def __init__(self):
        self.reset()

    def reset(self, **kwargs):
        self.log = []


class CacheLogInstance(object):

    def __init__(self, name, key, end, hit=None):
        self.name = name
        self.key = key
        self.time = end
        self.hit = hit
    
    def __repr__(self):
        return ' - '.join((self.name, str(self.key)))
    
def logged_func(func):
    def inner(instance, key, *args, **kwargs):
        t = time()
        val = func(instance, key, *args, **kwargs)
        
        if conf.CACHEBOT_ENABLE_LOG:
            end = 1000 * (time() - t)
            hit = None
            if func.func_name == 'get':
                hit = val != None
            elif func.func_name == 'get_many':
                hit = bool(val)
            log = CacheLogInstance(func.func_name, key, end, hit=hit)
            instance._logger.log.append(log)
            cachebot_log.debug(str(log))

        return val
    return inner

try:
    from debug_toolbar.panels import DebugPanel
    
    class CachePanel(DebugPanel):

        name = 'Cache'
        has_content = True

        def nav_title(self):
            return _('Cache')

        def title(self):
            return _('Cache Queries')

        def nav_subtitle(self):
            from django.core.cache import cache
            # Aggregate stats.
            stats = {'hit': 0, 'miss': 0, 'time': 0}
            for log in cache._logger.log:
                if hasattr(log, 'hit'):
                    stats[log.hit and 'hit' or 'miss'] += 1
                stats['time'] += log.time

            # No ngettext, too many combos!
            stats['time'] = round(stats['time'], 2)
            return _('%(hit)s hits, %(miss)s misses in %(time)sms') % stats

        def content(self):
            from django.core.cache import cache
            context = {'logs': cache._logger.log}
            return Template(template).render(Context(context))

        def url(self):
            return ''

        def process_request(self, request):
            from django.core.cache import cache
            cache._logger.reset()
            


    template = """
    <style type="text/css">
      #djDebugCacheTable tr.hit.djDebugOdd { background-color: #d7f3bc; }
      #djDebugCacheTable tr.hit.djDebugEven { background-color: #c7fcd3; }
    </style>
    <table id="djDebugCacheTable">
      <thead>
        <tr>
          <th>{{ _('Time (ms)') }}</th>
          <th>{{ _('Method') }}</th>
          <th>{{ _('Key') }}</th>
        </tr>
      </thead>
      <tbody>
        {% for log in logs %}
          {% if log.hit %}
          <tr class="hit {% cycle 'djDebugOdd' 'djDebugEven' %}">
          {% else %}
          <tr class="{% cycle 'djDebugOdd' 'djDebugEven' %}">
          {% endif %}
            <td>{{ log.time|floatformat:"2" }}</td>
            <td class="{{ log.name }} method">{{ log.name }}</td>
            <td>{{ log.key }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
    """
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = flush_cache
#!/usr/bin/env python
# encoding: utf-8

from django.core.management.base import BaseCommand
from cachebot.utils import flush_cache

class Command(BaseCommand):
    """
    Empty the cache
    """
    help = 'Empty the cache'
    
    def handle(self, *args, **options):
        
        flush_cache(hard=True)
########NEW FILE########
__FILENAME__ = managers
from django.db.models import Manager

from cachebot import conf
from cachebot.queryset import CachedQuerySet

class CacheBotManager(Manager):

    def __init__(self, cache_all=conf.CACHEBOT_CACHE_ALL, cache_get=conf.CACHEBOT_CACHE_GET, **kwargs):
        super(CacheBotManager, self).__init__(**kwargs)
        self.cache_all = cache_all
        if cache_all:
            self.cache_get = True
        else:
            self.cache_get = cache_get

    def get_query_set(self):
        qs = CachedQuerySet(self.model, using=self.db)
        if self.cache_all:
            return qs.cache()
        else:
            return qs

    def cache(self, *args):
        return self.get_query_set().cache(*args)

    def select_reverse(self, *args, **kwargs):
        return self.get_query_set().select_reverse(*args, **kwargs)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django import dispatch

from cachebot import conf

class CacheBotSignals(models.Model):
    table_name = models.CharField(max_length=100)
    accessor_path = models.CharField(max_length=100)
    lookup_type = models.CharField(max_length=20)
    exclude = models.BooleanField(default=False)
    
    class Meta:
        ordering = ('table_name','accessor_path','lookup_type','exclude')
    
    def __unicode__(self):
        return u".".join((self.table_name,self.accessor_path,self.lookup_type,str(self.exclude)))
    
class CacheBotException(Exception):
    pass

post_update = dispatch.Signal(providing_args=["sender", "queryset"])

if conf.CACHEBOT_ENABLE_LOG:
    from django.core.signals import request_finished
    from django.core.cache import cache
    
    request_finished.connect(cache._logger.reset)

if conf.RUNNING_TESTS:
    from cachebot.test_models import *
########NEW FILE########
__FILENAME__ = monkey
def patch_manager():
    from django.db import models    
    from cachebot.managers import CacheBotManager
    models.Manager = CacheBotManager

def patch_queryset():
    from django.db.models import query
    from cachebot.queryset import CachedQuerySet
    query.QuerySet = CachedQuerySet

def patch_all(manager=True, queryset=True):
    if manager:
        patch_manager()
    if queryset:
        patch_queryset()

########NEW FILE########
__FILENAME__ = queryset
from itertools import chain

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, FieldError
from django.db import connection
from django.db.models import get_models
from django.db.models.query import QuerySet, ValuesQuerySet
from django.db.models.fields.related import ForeignRelatedObjectsDescriptor, ReverseManyRelatedObjectsDescriptor, ManyRelatedObjectsDescriptor
from django.db.models.sql.constants import LOOKUP_SEP
from django.db.models.sql.where import WhereNode
from django.utils.hashcompat import md5_constructor

from cachebot import conf
from cachebot.models import post_update
from cachebot.signals import cache_signals
from cachebot.utils import get_invalidation_key, get_values, set_value

class CacheBot(object):
    
    def __init__(self, queryset, extra_args=''):
        # have to call clone for some reason
        self.queryset = queryset._clone()
        if isinstance(self.queryset, ValuesQuerySet):
            self.parent_class = ValuesQuerySet
        else:
            self.parent_class = QuerySet
        self.result_key = queryset.get_cache_key(extra_args)

        
    def __iter__(self):
        cache_query = getattr(self.queryset, '_cache_query', False)
        
        if cache_query:
            results = cache.get(self.result_key)
            if results is not None:
                for obj in results:
                    if conf.CACHEBOT_DEBUG_RESULTS:
                        set_value(obj, 'from_cache', True)
                    yield obj
                raise StopIteration
        
        results = []
        pk_name = self.queryset.model._meta.pk.name   
        self.queryset._fill_select_reverse_cache()
        
        reversemapping_keys = self.queryset._reversemapping.keys()
        reversemapping_keys.sort()
        
        for obj in self.parent_class.iterator(self.queryset):    
            for related_name in reversemapping_keys:
                reversemap = self.queryset._target_maps[related_name]
                related_split = related_name.split(LOOKUP_SEP)
                for related_obj, related_field in self._nested_select_reverse(obj, related_split):
                    val = reversemap.get(get_values(related_obj, pk_name),[])
                    set_value(related_obj, related_field, val)
                        
            if cache_query:
                results.append(obj)
            if conf.CACHEBOT_DEBUG_RESULTS:
                set_value(obj, 'from_cache', False)
            yield obj
            
        if cache_query:
            self.cache_results(results)
    
    def _nested_select_reverse(self, obj, related_split):
        related_field = related_split.pop(0)
        try:
            related_obj = getattr(obj, related_field)
            if hasattr(related_obj, '__iter__'):
                for related_obj_ in related_obj:                    
                    for nested_obj, related_field in self._nested_select_reverse(related_obj_, related_split):
                        yield nested_obj, related_field
            else:
                for nested_obj, related_field in self._nested_select_reverse(related_obj, related_split):
                    yield nested_obj, related_field
        except AttributeError:
            yield obj, related_field
    
    def _is_valid_flush_path(self, accessor_path):
        if not self.queryset._flush_fields:
            return True
        elif (accessor_path in self.queryset._flush_fields) or (accessor_path+'_id' in self.queryset._flush_fields):
            return True
        else:
            return False
    
    def _register_signal(self, model_class, accessor_path, lookup_type, negate, params):
        cache_signals.register(model_class, accessor_path, lookup_type, negate=negate)
        return get_invalidation_key(
            model_class._meta.db_table, 
            accessor_path = accessor_path, 
            lookup_type = lookup_type, 
            negate = negate, 
            value = params)
    
    def cache_results(self, results):
        """
        Create invalidation signals for these results in the form of CacheBotSignals.
        A CacheBotSignal stores a model and it's accessor path to self.queryset.model.
        """
        # cache the results   
        invalidation_dict = {}
        if cache.add(self.result_key, results, conf.CACHE_SECONDS):
            
            invalidation_dict.update(dict([(key, self.result_key) for key in self.get_invalidation_keys(results)]))
    
            for child, negate in self.queryset._get_where_clause(self.queryset.query.where):     
                constraint, lookup_type, value_annotation, params = child                
                for model_class, accessor_path in self._get_join_paths(constraint.alias, constraint.col):
                    if self._is_valid_flush_path(accessor_path):  
                        invalidation_key = self._register_signal(model_class, accessor_path, lookup_type, negate, params)
                        invalidation_dict[invalidation_key] = self.result_key
                            
                    for join_tuple in self.queryset.query.join_map.keys():
                        if join_tuple[0] == model_class._meta.db_table and self._is_valid_flush_path(accessor_path): 
                            model_klass, m2m = self.queryset._get_model_class_from_table(join_tuple[1]) 
                            invalidation_key = self._register_signal(model_klass, join_tuple[3], lookup_type, negate, params)
                            invalidation_dict[invalidation_key] = self.result_key
            
            # need to add and append to prevent race conditions
            # replace this with batch operations later
            for flush_key, flush_list in invalidation_dict.iteritems():
                added = cache.add(flush_key, self.result_key, 0)
                if not added:
                    cache.append(flush_key, ',%s' % self.result_key)
    
    def _get_join_paths(self, table_alias, accessor_path):
        model_class, m2m = self.queryset._get_model_class_from_table(table_alias) 
        if m2m: 
            accessor_path = model_class._meta.pk.attname
            
        yield model_class, accessor_path

        for join_tuple in self.queryset.query.join_map.keys():
            if join_tuple[0] and join_tuple[1] == table_alias:
                for model_class, join_accessor_path in self._get_join_paths(join_tuple[0], join_tuple[2]):
                    if join_accessor_path == model_class._meta.pk.attname:
                        for attname, related in self.queryset._get_reverse_relations(model_class):
                            join_accessor_path = attname
                            yield model_class, LOOKUP_SEP.join((join_accessor_path, accessor_path))
                    elif join_accessor_path.split(LOOKUP_SEP)[-1] == 'id':
                        accessor_path_split = join_accessor_path.split(LOOKUP_SEP) 
                        join_accessor_path = LOOKUP_SEP.join(accessor_path_split[:-1])
                        yield model_class, LOOKUP_SEP.join((join_accessor_path, accessor_path))
                    elif join_accessor_path.endswith('_id'):
                        join_accessor_path = join_accessor_path[:-3]
                        yield model_class, LOOKUP_SEP.join((join_accessor_path, accessor_path))
                    else:
                        yield model_class, LOOKUP_SEP.join((join_accessor_path, accessor_path))
                

    def get_invalidation_keys(self, results):
        """
        Iterates through a list of results, and returns an invalidation key for each result. If the
        query spans multiple tables, also return invalidation keys of any related rows.
        """
        related_fields = self.queryset._related_fields
        for obj in results:
            for field, model_class in related_fields.iteritems():
                pk_name = model_class._meta.pk.attname
                cache_signals.register(model_class, pk_name, 'exact')
                for value in get_values(obj, field):
                    invalidation_key = get_invalidation_key(
                        model_class._meta.db_table, 
                        accessor_path = pk_name, 
                        value = value)
                    yield invalidation_key
        
        
class CachedQuerySetMixin(object):              
    
    def get_cache_key(self, extra_args='', version=None):
        """Cache key used to identify this query"""
        query, params = self.query.get_compiler(using=self.db).as_sql()
        query_string = (query % params).strip().encode("utf-8")
        base_key = md5_constructor('.'.join((query_string, extra_args))).hexdigest()
        return cache.make_key('.'.join((self.model._meta.db_table, 'cachebot.results', base_key)), version=version)
    
    def _get_model_class_from_table(self, table):
        """Helper method that accepts a table name and returns the Django model class it belongs to"""
        try:
            model_class = [m for m in get_models() if connection.introspection.table_name_converter(m._meta.db_table) in map(connection.introspection.table_name_converter,[table])][0] 
            m2m = False 
        except IndexError:
            try: 
                # this is a many to many field 
                model_class = [f.rel.to for m in get_models() for f in m._meta.local_many_to_many if f.m2m_db_table() == table][0] 
                m2m = True 
            except IndexError: 
                # this is an inner join 
                table = self.query.alias_map[table][0]
                return self._get_model_class_from_table(table)
        return model_class, m2m 

    @property
    def _related_fields(self):
        """Returns the primary key accessor name and model class for any table this query spans."""
        model_class, m2m = self._get_model_class_from_table(self.model._meta.db_table) 
        related_fields = {
            self.model._meta.pk.attname: model_class
        }
        for attname, model_class in self._get_related_models(self.model):
            related_fields[attname] = model_class
        return related_fields
    
    def _get_related_models(self, parent_model):
        """
        A recursive function that looks at what tables this query spans, and
        finds that table's primary key accessor name and model class.
        """
        related_models = set()
        rev_reversemapping = dict([(v,k) for k,v in self._reversemapping.iteritems()])
        if rev_reversemapping:
            for attname, related in self._get_reverse_relations(parent_model):
                related_models.add((rev_reversemapping[attname], related.model))

        for field in parent_model._meta.fields:
            if field.rel and field.rel.to._meta.db_table in self.query.tables and field.rel.to != parent_model:
                related_models.add((field.attname, field.rel.to))
        
        for attname, model_class in related_models:
            yield attname, model_class
            if attname.endswith("_id"):
                attname = attname[:-3]
                for join_attname, model_klass in self._get_related_models(model_class):
                    yield LOOKUP_SEP.join((attname,join_attname)), model_klass
    
    def _get_reverse_relations(self, model_class):
        for related in chain(model_class._meta.get_all_related_objects(), model_class._meta.get_all_related_many_to_many_objects()):
            if related.opts.db_table in self.query.tables and related.model != model_class:
                related_name = related.get_accessor_name()
                yield related_name, related
                if related.model != related.parent_model:
                    for attname, join_related in self._get_reverse_relations(related.model):
                        yield LOOKUP_SEP.join((related_name + '_cache', attname)), join_related
                
    def _base_clone(self, queryset, klass=None, setup=False, **kwargs):
        """
        Clones a CachedQuerySet. If caching and this is a ValuesQuerySet, automatically add any
        related foreign relations to the select fields so we can invalidate this query.
        """
        cache_query = kwargs.get('_cache_query', getattr(self, '_cache_query', False))
        kwargs['_cache_query'] = cache_query
        if not hasattr(self, '_reversemapping'):
            self._reversemapping = {}

        if cache_query and isinstance(queryset, ValuesQuerySet):
            fields = kwargs.get('_fields', getattr(self,'_fields', ()))
            if fields:
                fields = list(fields)
            else:
                fields = [f.attname for f in self.model._meta.fields]
            
            for related_field in self._related_fields.keys():
                if related_field not in fields and self._is_valid_field(related_field):
                    fields.append(related_field)
                    setup = True
            kwargs['_fields'] = tuple(fields)
        
        if cache_query:
            reversemapping = {}
            for attname, related in self._get_reverse_relations(self.model):
                reversemapping[attname + '_cache'] = attname
            kwargs['_reversemapping'] = reversemapping
        if isinstance(queryset, ValuesQuerySet):
            parent_class = ValuesQuerySet
        else:
            parent_class = QuerySet
        clone = parent_class._clone(self, klass=klass, setup=setup, **kwargs)
        if not hasattr(clone, '_cache_query'):
            clone._cache_query = getattr(self, '_cache_query', False)
        if not hasattr(clone, '_reversemapping'):
            clone._reversemapping = getattr(self, '_reversemapping', {})
        if not hasattr(clone, '_target_maps'):
            clone._target_maps = getattr(self, '_target_maps', {})
        if not hasattr(clone, '_flush_fields'):
            clone._flush_fields = getattr(self, '_flush_fields', ())
            
        return clone
    
    def _is_valid_field(self, field, allow_m2m=True):
        """A hackish way to figure out if this is a field or reverse foreign relation"""
        try:
            self.query.setup_joins(field.split(LOOKUP_SEP), self.query.get_meta(), self.query.get_initial_alias(), False, allow_m2m, True)
            return True
        except FieldError:
            return False
    
    def _get_select_reverse_model(self, model_class, lookup_args):
        model_arg = lookup_args.pop(0)
        try:
            descriptor = getattr(model_class, model_arg)
        except AttributeError:
            # for nested reverse relations
            descriptor = getattr(model_class, self._reversemapping[model_arg])
        if lookup_args:
            if isinstance(descriptor, ForeignRelatedObjectsDescriptor):
                return self._get_select_reverse_model(descriptor.related.model, lookup_args)
            elif isinstance(descriptor, ReverseManyRelatedObjectsDescriptor):
                return self._get_select_reverse_model(descriptor.field.rel.to, lookup_args)
            elif isinstance(descriptor, ManyRelatedObjectsDescriptor):
                return self._get_select_reverse_model(descriptor.related.model, lookup_args)
        else:
            return model_class, model_arg
            
    def _fill_select_reverse_cache(self):
        reversemapping = getattr(self, '_reversemapping', {})
        target_maps = {}
        if reversemapping:
            if isinstance(self, ValuesQuerySet):
                pk_name = self.model._meta.pk.name
                queryset = self._clone().values(pk_name)
            else:
                queryset = self._clone()
            
            # Need to clear any limits on this query because of http://code.djangoproject.com/ticket/10099
            queryset.query.clear_limits()
            
            # we need to iterate through these in a certain order
            reversemapping_keys = self._reversemapping.keys()
            reversemapping_keys.sort()
            
            for key in reversemapping_keys:
                target_map= {}
                val = self._reversemapping[key]

                model_class, model_arg = self._get_select_reverse_model(self.model, val.split(LOOKUP_SEP))
                if hasattr(model_class,  key):
                    raise ImproperlyConfigured,  "Model %s already has an attribute %s" % (model_class,  key)  
                    
                descriptor = getattr(model_class,  model_arg)
                if isinstance(descriptor, ForeignRelatedObjectsDescriptor):
                    rel = descriptor.related
                    related_queryset = rel.model.objects.filter(**{rel.field.name+'__in':queryset}).all()
                    for item in related_queryset.iterator():
                        target_map.setdefault(getattr(item, rel.field.get_attname()), []).append(item)
                elif isinstance(descriptor, ReverseManyRelatedObjectsDescriptor):
                    field = descriptor.field
                    related_queryset = field.rel.to.objects.filter(**{field.rel.related_name +'__in':queryset}).all().extra( \
                                select={'main_id': field.m2m_db_table() + '.' + field.m2m_column_name()})
                    for item in related_queryset.iterator():
                        target_map.setdefault(getattr(item, 'main_id'), []).append(item)
                elif isinstance(descriptor, ManyRelatedObjectsDescriptor):
                    rel = descriptor.related
                    related_queryset = rel.model.objects.filter(**{rel.field.name +'__in':queryset}).all().extra( \
                                select={'main_id': rel.field.m2m_db_table() + '.' + rel.field.m2m_column_name()}) 
                    for item in related_queryset.iterator():
                        target_map.setdefault(getattr(item, 'main_id'), []).append(item)
                else:
                    raise ImproperlyConfigured, "Unsupported mapping %s %s" % (val, descriptor)
                target_maps[key]=target_map
        self._target_maps = target_maps   

    def _get_where_clause(self, node):
        for child in node.children:
            if isinstance(child, WhereNode):
                for child_node, negated in self._get_where_clause(child):
                    yield child_node, negated
            else:
                yield child, node.negated

    def select_reverse(self, *reversemapping, **kwargs):
        """
        Like select_related, but follows reverse and m2m foreign relations. Example usage:
        
        article_list = Article.objects.select_reverse('book_set')

        for article in article_list:
            # these will return the same queryset
            print article.book_set_cache
            print article.book_set.all() 
        
        If there are N Articles belonging to K Books, this will return N + K results. The actual
        reversed book queryset would be cached in article_list._target_maps['book_set_cache']
        
        Nested queries are also supported:
        
        article_list = Article.objects.select_reverse('book_set','book_set__publisher_set')

        for article in article_list:
            
            # these will return the same queryset
            for book in article.book_set_cache:
                print book.publisher_set_cache
                print book.publisher_set.all()
            
            # these will return the same queryset
            for book in article.book_set.all():
                print book.publisher_set_cache
                print book.publisher_set.all()
             
        
        This could probably be better, because it does a SQL query for each reverse or m2m foreign
        relation in select_reverse, i.e. 
        
        Article.objects.select_reverse('book_set','author_set')
        
        will be 3 SQL queries. This is a lot better than the alternative of a separate SQL query
        for each article in article_list, but it'd be nice to be able to do the whole thing in 1.
        
        Based off django-selectreverse: http://code.google.com/p/django-selectreverse/
        """
        _reversemapping = dict([(key +'_cache', key) for key in reversemapping])
        return self._clone(_reversemapping=_reversemapping, **kwargs)
        
    def values(self, *fields):
        return self._clone(klass=CachedValuesQuerySet, setup=True, _fields=fields)
    
    def cache(self, *flush_fields):
        """
        Cache this queryset. If this is a query over reverse foreign relations, those fields will automatically
        be added to select_reverse, because we need them for invalidation. Do not cache queries on
        tables in CACHEBOT_TABLE_BLACKLIST
        """
        _cache_query = self.model._meta.db_table not in conf.CACHEBOT_TABLE_BLACKLIST
        return self._clone(setup=True, _cache_query=_cache_query, _flush_fields=flush_fields)
    
    def get(self, *args, **kwargs):
        if self.model.objects.cache_get:
            return super(CachedQuerySetMixin, self.cache()).get(*args, **kwargs)
        else:
            return super(CachedQuerySetMixin, self).get(*args, **kwargs)
    
        
class CachedQuerySet(CachedQuerySetMixin, QuerySet):
    
    def __init__(self, *args, **kwargs):
        super(CachedQuerySet, self).__init__(*args, **kwargs)
        self._reversemapping = {}
    
    def iterator(self):    
        for obj in CacheBot(self):
            yield obj
        raise StopIteration
    
    def _clone(self, klass=None, setup=False, **kwargs):
        return self._base_clone(self, klass=klass, setup=setup, **kwargs)
    
    def update(self, **kwargs):
        post_update.send(sender=self.model, queryset=self)
        return super(CachedQuerySet, self).update(**kwargs)    
    
    
class CachedValuesQuerySet(CachedQuerySetMixin, ValuesQuerySet):
    
    def __init__(self, *args, **kwargs):
        super(CachedValuesQuerySet, self).__init__(*args, **kwargs)
        self._reversemapping = {}
        
    def iterator(self):      
        for obj in CacheBot(self):
            yield obj
        raise StopIteration
    
    def _clone(self, klass=None, setup=False, **kwargs):
        return self._base_clone(self, klass=klass, setup=setup, **kwargs)
    
    def update(self, **kwargs):
        post_update.send(sender=self.model, queryset=self)
        return super(CachedQuerySet, self).update(**kwargs)  


########NEW FILE########
__FILENAME__ = signals
from django.core.cache import cache
from django.core.signals import request_finished, request_started
from django.db.models.signals import post_save, pre_delete
from django.utils.http import urlquote
from django.utils.hashcompat import md5_constructor

from cachebot import conf
from cachebot.models import CacheBotSignals, post_update
from cachebot.utils import get_invalidation_key, get_values

if conf.CACHEBOT_ENABLE_LOG:
    request_finished.connect(cache._logger.reset)
    
class CacheSignals(object):
    """
    An object that handles installed cache signals. Keep a local copy of the signals
    so we don't hammer memcache
    """
    
    __shared_state = dict(
        ready = False,
        local_signals = dict()
    )
    
    def __init__(self):
        self.__dict__ = self.__shared_state
 
    def get_lookup_key(self, model_class, version=None):
        return cache.make_key('.'.join(('cachesignals', model_class._meta.db_table)), version=version)
    
    def get_local_signals(self, model_class):
        accessor_set = self.local_signals.get(model_class._meta.db_table)
        if not accessor_set:
            accessor_set = set()
        return accessor_set
    
    def get_global_signals(self, model_class):
        lookup_key = self.get_lookup_key(model_class)
        accessor_set = cache.get(lookup_key)
        if not accessor_set:
            accessor_set = set()
        self.local_signals[model_class._meta.db_table] = accessor_set
        return accessor_set
    
    def set_signals(self, model_class, accessor_set):
        lookup_key = self.get_lookup_key(model_class)
        self.local_signals[model_class._meta.db_table] = accessor_set
        cache.set(lookup_key, accessor_set, 0)
        
    def register(self, model_class, accessor_path, lookup_type, negate=False):
        path_tuple = (accessor_path, lookup_type, negate)
        if path_tuple not in self.get_local_signals(model_class):
            # not in local cache, check the global cache
            accessor_set = self.get_global_signals(model_class)
            if path_tuple not in accessor_set:
                # can't use get_or_create here
                try:               
                    CacheBotSignals.objects.filter(
                        table_name=model_class._meta.db_table,
                        accessor_path=accessor_path,
                        lookup_type=lookup_type,
                        exclude=negate
                    )[0]
                except IndexError:
                    CacheBotSignals.objects.create(
                        table_name=model_class._meta.db_table,
                        accessor_path=accessor_path,
                        lookup_type=lookup_type,
                        exclude=negate
                    )
                accessor_set.add(path_tuple)
                self.set_signals(model_class, accessor_set)

cache_signals = CacheSignals()

def load_cache_signals(version=None, **kwargs):
    """On startup, sync signals with registered models"""
    if not cache_signals.ready:
        results = CacheBotSignals.objects.all()
        tables = [r.table_name for r in results]
        mapping = cache.get_many(tables)
        for result in results:
            key = cache.make_key(u'.'.join(('cachesignals', result.table_name)), version=version)
            accessor_set = mapping.get(key) or set()
            accessor_set.add((result.accessor_path, result.lookup_type, result.exclude))
            mapping[key] = accessor_set
        cache.set_many(mapping, 0)
        cache_signals.ready = True
request_started.connect(load_cache_signals)


### INVALIDATION FUNCTIONS ###
def post_update_cachebot(sender, queryset, **kwargs):
    invalidate_cache(sender, queryset)
post_update.connect(post_update_cachebot)

def post_save_cachebot(sender, instance, **kwargs):
    invalidate_cache(sender, (instance,))
post_save.connect(post_save_cachebot)

def pre_delete_cachebot(sender, instance, **kwargs):
    invalidate_cache(sender, (instance,))
pre_delete.connect(pre_delete_cachebot)

def invalidate_object(instance):
    invalidate_cache(type(instance), (instance,))

def invalidate_cache(model_class, objects, **extra_keys):
    """
    Flushes the cache of any cached objects associated with this instance.

    Explicitly set a None value instead of just deleting so we don't have any race
    conditions where:
        Thread 1 -> Cache miss, get object from DB
        Thread 2 -> Object saved, deleted from cache
        Thread 1 -> Store (stale) object fetched from DB in cache
    Five second should be more than enough time to prevent this from happening for
    a web app.
    """
    invalidation_dict = {}
    accessor_set = cache_signals.get_global_signals(model_class)
    for obj in objects:
        for (accessor_path, lookup_type, negate) in accessor_set:
            if lookup_type != 'exact' or negate:
                invalidation_key = get_invalidation_key(
                    model_class._meta.db_table, 
                    accessor_path = accessor_path, 
                    negate = negate,
                    value = '')
                invalidation_dict[invalidation_key] = None
            else:
                for value in get_values(obj, accessor_path):
                    invalidation_key = get_invalidation_key(
                        model_class._meta.db_table, 
                        accessor_path = accessor_path, 
                        negate = negate,
                        value = value)
                    invalidation_dict[invalidation_key] = None
    
    if invalidation_dict:
        invalidation_dict.update(cache.get_many(invalidation_dict.keys()))

        cache_keys = set()
        for obj_key, cache_key_list in invalidation_dict.iteritems():
            if cache_key_list:
                cache_keys.update(cache_key_list.split(','))
        
        if cache_keys:
            cache.set_many(dict([(key, None) for key in cache_keys]), conf.CACHE_INVALIDATION_TIMEOUT)
        invalidation_dict.update(extra_keys)
        cache.delete_many(invalidation_dict.keys())
        
def invalidate_template_cache(fragment_name, *variables):
    args = md5_constructor(u':'.join(map(urlquote, variables)).encode('utf-8')).hexdigest()
    cache_key = 'template.cache.%s.%s' % (fragment_name, args)
    cache.delete(cache_key)



########NEW FILE########
__FILENAME__ = base_tests
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models.query import ValuesQuerySet
from django.db.models import Q
from django.test import TestCase

from cachebot.models import FirstModel, SecondModel, ThirdModel, GenericModel, ManyModel
from cachebot.utils import flush_cache

class BaseTestCase(TestCase):
    
    def tearDown(self):
        super(BaseTestCase, self).tearDown()
        cache._logger.reset()
    
    def setUp(self):
        super(BaseTestCase, self).setUp()
        flush_cache(hard=False)

class BasicCacheTests(BaseTestCase):
    
    def setUp(self):
        super(BasicCacheTests, self).setUp()
        self.append_cache = False
        self.firstmodel = FirstModel.objects.create(text="test1")
        self.secondmodel = SecondModel.objects.create(text="test2", obj=self.firstmodel)
        self.thirdmodel = ThirdModel.objects.create(text="test3", obj=self.secondmodel)
        ctype = ContentType.objects.get_for_model(self.secondmodel)
        self.genericmodel = GenericModel.objects.create(text="test4", content_type=ctype, object_id=self.secondmodel.id)
        self.manymodel = ManyModel.objects.create(text='test5')
        self.manymodel.firstmodel.add(self.firstmodel)
        self.manymodel.thirdmodel.add(self.thirdmodel)
        self.manager = ThirdModel.objects
        self.func = self.manager.cache().filter
        self.obj = self.thirdmodel
        self.kwargs = {'id':self.obj.id}
     
    def _test_cache_lookup(self, from_cache=False):
        try:
            if self.append_cache:
                results = self.func(**self.kwargs).cache()
            else:
                results = self.func(**self.kwargs)
        except (self.obj.DoesNotExist, self.obj.MultipleObjectsReturned):
            self.assertEqual(from_cache, False)
            return
        
        if isinstance(results, ValuesQuerySet):        
            if hasattr(results,'__iter__'):
                for obj in results:
                    self.assertEqual(obj['from_cache'], from_cache)
            else:
                self.assertEqual(results['from_cache'], from_cache)
        else:
            if hasattr(results,'__iter__'):
                for obj in results:
                    self.assertEqual(obj.from_cache, from_cache)
            else:
                self.assertEqual(results.from_cache, from_cache)
        return results

    def _test_lookup(self):
        self._test_cache_lookup(from_cache=False)
        results = self._test_cache_lookup(from_cache=True)
        return results
    
    def test_lookup(self):
        self._test_lookup()

    def test_save_signal(self, obj=None):
        if obj is None:
            obj = self.obj
        self._test_lookup()
        obj.text = "jedi"
        obj.save()
        self._test_cache_lookup(from_cache=False)
    
    def test_delete_signal(self, obj=None):
        if obj is None:
            obj = self.obj
        self._test_lookup()
        obj.delete()
        self._test_cache_lookup(from_cache=False)
    
    def test_new_obj(self, obj=None, kwargs=None):
        if obj is None:
            obj = self.obj
        if kwargs is None:
            self.kwargs = {'text':obj.text}
        else:
            self.kwargs = kwargs
        self._test_lookup()
        new_obj = obj.__class__(text=obj.text)
        if hasattr(new_obj,'obj_id'):
            new_obj.obj = obj.obj
        if hasattr(new_obj,'firstmodel_id'):
            new_obj.firstmodel = obj.firstmodel
        if hasattr(new_obj,'secondmodel_id'):
            new_obj.secondmodel = obj.secondmodel
        if hasattr(new_obj,'content_type_id'):
            new_obj.content_type_id = obj.content_type_id
            new_obj.object_id = obj.object_id
        new_obj.save()
        self._test_cache_lookup(from_cache=False)
    

class FieldCacheTests(BasicCacheTests):
    
    def setUp(self):
        BasicCacheTests.setUp(self)
        self.kwargs = {'text':self.obj.text}
    
    
class GenericCacheTests(BasicCacheTests):
    
    def setUp(self):
        BasicCacheTests.setUp(self)
        self.manager = GenericModel.objects
        self.func = self.manager.cache().filter
        self.obj = self.genericmodel
        
        
class RelatedCacheTests(BasicCacheTests):

    def setUp(self):
        BasicCacheTests.setUp(self)
        self.func = self.manager.cache().filter
        self.kwargs = {'obj':self.secondmodel}

    def test_related_save_signal(self):
        self.test_save_signal(obj=self.obj.obj)

    def test_related_delete_signal(self):
        self.test_delete_signal(obj=self.obj.obj)

    def test_related_new_obj(self):
        if hasattr(self.obj, 'obj'):
            kwargs = {'obj__text':self.obj.obj.text}
            self.test_new_obj(obj=self.obj.obj, kwargs=kwargs)


class RelatedIDCacheTests(RelatedCacheTests):

    def setUp(self):
        RelatedCacheTests.setUp(self)
        self.kwargs = {'obj__id':self.secondmodel.id}


class RelatedFieldCacheTests(RelatedCacheTests):

    def setUp(self):
        RelatedCacheTests.setUp(self)
        self.kwargs = {'obj__text':self.secondmodel.text}
           
              
class ExtraRelatedCacheTests(RelatedCacheTests):

    def setUp(self):
        RelatedCacheTests.setUp(self)
        self.func = self.manager.cache().filter
        self.kwargs = {'obj__obj':self.firstmodel}
        
    def test_extra_related_save_signal(self):
        self.test_save_signal(obj=self.obj.obj.obj)

    def test_extra_related_delete_signal(self):
        self.test_delete_signal(obj=self.obj.obj.obj)
    
    def test_extra_related_new_obj(self):
        if hasattr(self.obj, 'obj') and hasattr(self.obj.obj, 'obj') :
            kwargs = {'obj__obj__text':self.obj.obj.obj.text}
            self.test_new_obj(obj=self.obj.obj.obj, kwargs=kwargs)


class ExtraRelatedIDCacheTests(ExtraRelatedCacheTests):

    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.kwargs = {'obj__obj__id':self.firstmodel.id}


class ExtraRelatedFieldCacheTests(ExtraRelatedCacheTests):

    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.kwargs = {'obj__obj__text':self.firstmodel.text}

   
class ExtraRelatedAppendCacheTests(ExtraRelatedCacheTests):

    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.append_cache = True


class SelectiveCacheTests(ExtraRelatedCacheTests):

    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.append_cache = True
        self.func = self.manager.cache('obj__obj').filter


class SelectiveCacheIDTests(ExtraRelatedCacheTests):

    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.append_cache = True
        self.func = self.manager.cache('obj__obj_id').filter
        

class ComplexQueryCacheTests(ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)

    def _test_cache_lookup(self, from_cache=False):
        try:
            if self.append_cache:
                results = self.func(Q(obj__obj__id=self.firstmodel.id)|Q(obj__obj__text='blah blah blah')).cache()
            else:
                results = self.func(Q(obj__obj__id=self.firstmodel.id)|Q(obj__obj__text='blah blah blah'))
        except (self.obj.DoesNotExist, self.obj.MultipleObjectsReturned):
            self.assertEqual(from_cache, False)
            return
        
        if isinstance(results, ValuesQuerySet):        
            if hasattr(results,'__iter__'):
                for obj in results:
                    self.assertEqual(obj['from_cache'], from_cache)
            else:
                self.assertEqual(results['from_cache'], from_cache)
        else:
            if hasattr(results,'__iter__'):
                for obj in results:
                    self.assertEqual(obj.from_cache, from_cache)
            else:
                self.assertEqual(results.from_cache, from_cache)
        return results
    
    def _test_lookup(self):
        self._test_cache_lookup(from_cache=False)
        results = self._test_cache_lookup(from_cache=True)
        return results
    
    def test_lookup(self):
        self._test_lookup()
    
    def test_extra_related_new_obj(self):
        pass
            
########NEW FILE########
__FILENAME__ = manager_tests
import time

from django.db import connection
from django.conf import settings

from cachebot import conf
from cachebot.models import FirstModel
from cachebot.tests.base_tests import BaseTestCase, BasicCacheTests, FieldCacheTests, RelatedCacheTests, ExtraRelatedCacheTests

class GetBasicCacheTests(BasicCacheTests):
    
    def setUp(self):
        BasicCacheTests.setUp(self)
        self.func = self.manager.get


class GetRelatedCacheTests(RelatedCacheTests):
    
    def setUp(self):
        RelatedCacheTests.setUp(self)
        self.func = self.manager.get


class GetExtraRelatedCacheTests(ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.func = self.manager.get


class GetOrCreateCacheTests(BaseTestCase):

    def test_get_then_create(self):
        self.assertRaises(FirstModel.DoesNotExist, FirstModel.objects.get, **{'text':'new'})
        FirstModel.objects.create(text='new')
        time.sleep(conf.CACHE_INVALIDATION_TIMEOUT)
        obj = FirstModel.objects.get(text='new')
        self.assertEqual(obj.from_cache,False)
        obj = FirstModel.objects.get(text='new')
        self.assertEqual(obj.from_cache,True)
    
    def test_get_or_create(self):
        obj, created = FirstModel.objects.get_or_create(text='new')
        self.assertEqual(created, True)
        time.sleep(conf.CACHE_INVALIDATION_TIMEOUT)
        obj = FirstModel.objects.get(text='new')
        self.assertEqual(obj.from_cache,False)
        obj = FirstModel.objects.get(text='new')
        self.assertEqual(obj.from_cache,True)

class SelectRelatedCacheTests(ExtraRelatedCacheTests):

    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.func = self.manager.select_related().cache().filter
        self.obj = self.thirdmodel
        self.kwargs = {'id':self.obj.id}

class ExcludeCacheTests(BasicCacheTests):
    
    def setUp(self):
        BasicCacheTests.setUp(self)
        self.obj = self.thirdmodel
        self.kwargs = {'id':self.obj.id+1}
        self.func = self.manager.cache().exclude


class ExcludeFieldCacheTests(FieldCacheTests):
    
    def setUp(self):
        FieldCacheTests.setUp(self)
        self.kwargs = {'text':'this text is not in any model'}
        self.func = self.manager.cache().exclude
        

class ExtraRelatedExcludeCacheTests(ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.kwargs = {'obj__obj':self.obj.obj.obj.id+1}
        self.func = self.manager.cache().exclude


class ExcludeAndFilterCacheTests(BasicCacheTests):
    
    def setUp(self):
        BasicCacheTests.setUp(self)
        self.obj = self.thirdmodel
        self.kwargs = {'id':self.obj.id+1}
        self.func = self.manager.cache().filter(id=self.obj.id).exclude


class ExcludeAndFilterFieldCacheTests(FieldCacheTests):
    
    def setUp(self):
        FieldCacheTests.setUp(self)
        self.kwargs = {'text':'this text is not in any model'}
        self.func = self.manager.cache().filter(text=self.obj.text).exclude
        
        
class ExtraRelatedExcludeAndFilterCacheTests(ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.kwargs = {'obj__obj':self.obj.obj.obj.id+1}
        self.func = self.manager.cache().filter(obj__obj=self.obj.obj.obj).exclude
       
       
class RangeCacheTests(ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.kwargs = {'obj__obj__in':[self.firstmodel]}
        
        
class NestedQuerysetCacheTests(ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        queryset = FirstModel.objects.all()
        self.kwargs = {'obj__obj__in':queryset}

# disable these tests 
        
class CountCacheTests(BasicCacheTests):
    
    def setUp(self):
        settings.DEBUG = True
        BasicCacheTests.setUp(self)
        # call count to create any CacheBotSignals first
        self.func(**self.kwargs).count()
    
    def test_lookup(self, count=1):
        return
        connection.queries = []
        self.assertEqual(self.func(**self.kwargs).count(), count)
        self.assertEqual(len(connection.queries), 1)
        self.assertEqual(self.func(**self.kwargs).count(), count)
        self.assertEqual(len(connection.queries), 1)
        
    
    def test_save_signal(self, obj=None):
        return
        if obj is None:
            obj = self.obj
        self.test_lookup(count=1)
        obj.save()
        self.test_lookup(count=1)
    
    def test_delete_signal(self, obj=None):
        return
        if obj is None:
            obj = self.obj
        self.test_lookup(count=1)
        obj.delete()
        self.test_lookup(count=0)

class ExtraRelatedCountCacheTests(ExtraRelatedCacheTests):
    
    def setUp(self):
        settings.DEBUG = True
        ExtraRelatedCacheTests.setUp(self)
        # call count to create any CacheBotSignals first
        self.func(**self.kwargs).count()
        
    def test_related_save_signal(self):
        return
        self.test_save_signal(obj=self.obj.obj)
    
    def test_related_delete_signal(self):
        return
        self.test_delete_signal(obj=self.obj.obj)
    
    def test_extra_related_save_signal(self):
        return
        self.test_save_signal(obj=self.obj.obj.obj)
    
    def test_extra_related_delete_signal(self):
        return
        self.test_delete_signal(obj=self.obj.obj.obj)
        
    
########NEW FILE########
__FILENAME__ = many_to_many_tests
from cachebot.models import ManyModel
from cachebot.tests.base_tests import BasicCacheTests, RelatedCacheTests

class BasicManyToManyCacheTests(BasicCacheTests):
    
    def setUp(self):
        BasicCacheTests.setUp(self)
        self.manager = ManyModel.objects
        self.func = self.manager.cache().filter
        self.obj = self.manymodel
        self.related_obj = self.firstmodel
        self.kwargs = {'id':self.obj.id}
        
    def test_lookup(self):
        self._test_lookup()

class RelatedManyToManyCacheTests(RelatedCacheTests):
    
    def setUp(self):
        RelatedCacheTests.setUp(self)
        self.manager = ManyModel.objects
        self.func = self.manager.cache().filter
        self.obj = self.manymodel
        self.related_obj = self.firstmodel
        self.kwargs = {'firstmodel':self.related_obj}
    
    def test_related_save_signal(self):
        # these will fail until we get many to many signals
        pass
    
    def test_related_delete_signal(self):
        self._test_lookup()
        obj = self.related_obj
        obj.text = "mind"
        obj.delete()
        self._test_cache_lookup(from_cache=False)
    

########NEW FILE########
__FILENAME__ = no_cache_tests
from cachebot import conf
from cachebot.models import FirstModel, NoCacheModel
from cachebot.tests.base_tests import BaseTestCase

class BlacklistCacheTests(BaseTestCase):
    
    def tearDown(self):
        super(BaseTestCase, self).tearDown()
        conf.CACHEBOT_TABLE_BLACKLIST = self._CACHEBOT_TABLE_BLACKLIST
    
    def setUp(self):
        BaseTestCase.setUp(self)
        self.obj = FirstModel.objects.create(text="test")
        self.func = FirstModel.objects.get
        self._CACHEBOT_TABLE_BLACKLIST = conf.CACHEBOT_TABLE_BLACKLIST
        conf.CACHEBOT_TABLE_BLACKLIST += (FirstModel._meta.db_table,)
        
    def test_lookup_not_in_cache(self):
        obj = self.func(id=self.obj.id)
        self.assertFalse(obj.from_cache)
        obj = self.func(id=self.obj.id)
        self.assertFalse(obj.from_cache)

class CacheGetFalseCacheTests(BlacklistCacheTests):
    
    def setUp(self):
        BlacklistCacheTests.setUp(self)
        self.obj = NoCacheModel.objects.create(text="test")
        self.func = NoCacheModel.objects.get
    
########NEW FILE########
__FILENAME__ = reverse_lookup_tests
from cachebot.models import FirstModel
from cachebot.tests.base_tests import RelatedCacheTests, ExtraRelatedCacheTests

class ReverseRelatedCacheTests(RelatedCacheTests):
    
    def setUp(self):
        RelatedCacheTests.setUp(self)
        self.manager = FirstModel.objects
        self.func = self.manager.cache().filter
        self.obj = self.secondmodel
        self.kwargs = {'secondmodel':self.obj}

    def test_related_new_obj(self):
        kwargs = {'secondmodel__text':self.secondmodel.text}
        self.test_new_obj(obj=self.secondmodel, kwargs=kwargs)


class ReverseExtraRelatedCacheTests(ReverseRelatedCacheTests, ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.manager = FirstModel.objects
        self.func = self.manager.cache().filter
        self.obj = self.thirdmodel
        self.kwargs = {'secondmodel__thirdmodel':self.obj}
    
    def test_extra_related_new_obj(self):
        kwargs = {'secondmodel__thirdmodel__text':self.thirdmodel.text}
        self.test_new_obj(obj=self.thirdmodel, kwargs=kwargs)


class ReverseRelatedValuesCacheTests(ReverseRelatedCacheTests, RelatedCacheTests):
    
    def setUp(self):
        RelatedCacheTests.setUp(self)
        self.manager = FirstModel.objects
        self.func = self.manager.cache().values().filter
        self.obj = self.secondmodel
        self.kwargs = {'secondmodel':self.obj}


class ReverseExtraRelatedValuesCacheTests(ReverseExtraRelatedCacheTests, ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.manager = FirstModel.objects
        self.func = self.manager.cache().values().filter
        self.obj = self.thirdmodel
        self.kwargs = {'secondmodel__thirdmodel':self.obj}
    

class ReverseExtraRelatedExcludeCacheTests(ReverseRelatedCacheTests, ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.manager = FirstModel.objects
        self.func = self.manager.cache().exclude(secondmodel__thirdmodel__id=500).filter
        self.obj = self.thirdmodel
        self.kwargs = {'secondmodel__thirdmodel':self.obj}
    
    def test_extra_related_new_obj(self):
        pass



########NEW FILE########
__FILENAME__ = values_tests
from cachebot.models import ThirdModel
from cachebot.tests.base_tests import BasicCacheTests, RelatedCacheTests, ExtraRelatedCacheTests

class ValuesBasicCacheTests1(BasicCacheTests):
    
    def setUp(self):
        BasicCacheTests.setUp(self)
        self.manager = ThirdModel.objects.cache().values()
        self.func = self.manager.filter


class ValuesBasicCacheTests2(BasicCacheTests):
    
    def setUp(self):
        BasicCacheTests.setUp(self)
        self.manager = ThirdModel.objects.values().cache()
        self.func = self.manager.filter


class ValuesBasicCacheTests3(BasicCacheTests):
    
    def setUp(self):
        BasicCacheTests.setUp(self)
        self.manager = ThirdModel.objects.cache().values('text')
        self.func = self.manager.filter


class ValuesBasicCacheTests4(BasicCacheTests):
    
    def setUp(self):
        BasicCacheTests.setUp(self)
        self.manager = ThirdModel.objects.values('text').cache()
        self.func = self.manager.filter
        

class ValuesBasicCacheTests5(BasicCacheTests):
    
    def setUp(self):
        BasicCacheTests.setUp(self)
        self.manager = ThirdModel.objects.values('text')
        self.func = self.manager.filter
        self.append_cache = True
        
        
class ValuesRelatedCacheTests1(RelatedCacheTests):
    
    def setUp(self):
        RelatedCacheTests.setUp(self)
        self.manager = ThirdModel.objects.cache().values()
        self.func = self.manager.filter


class ValuesRelatedCacheTests2(RelatedCacheTests):
    
    def setUp(self):
        RelatedCacheTests.setUp(self)
        self.manager = ThirdModel.objects.values().cache()
        self.func = self.manager.filter


class ValuesRelatedCacheTests3(RelatedCacheTests):
    
    def setUp(self):
        RelatedCacheTests.setUp(self)
        self.manager = ThirdModel.objects.cache().values('text','obj__text')
        self.func = self.manager.filter


class ValuesRelatedCacheTests4(RelatedCacheTests):
    
    def setUp(self):
        RelatedCacheTests.setUp(self)
        self.manager = ThirdModel.objects.values('text','obj__text').cache()
        self.func = self.manager.filter


class ValuesRelatedCacheTests5(RelatedCacheTests):
    
    def setUp(self):
        RelatedCacheTests.setUp(self)
        self.manager = ThirdModel.objects.values('text','obj__text')
        self.func = self.manager.filter
        self.append_cache = True
        
        
class ValuesExtraRelatedCacheTests1(ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.manager = ThirdModel.objects.cache().values()
        self.func = self.manager.filter
        

class ValuesExtraRelatedCacheTests2(ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.manager = ThirdModel.objects.values().cache()
        self.func = self.manager.filter


class ValuesExtraRelatedCacheTests3(ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.manager = ThirdModel.objects.cache().values('obj__text','obj__obj__text')
        self.func = self.manager.filter


class ValuesExtraRelatedCacheTests4(ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.manager = ThirdModel.objects.values('obj__text','obj__obj__text').cache()
        self.func = self.manager.filter


class ValuesExtraRelatedAppendCacheTests4(ExtraRelatedCacheTests):
    
    def setUp(self):
        ExtraRelatedCacheTests.setUp(self)
        self.manager = ThirdModel.objects.values('text','obj__text','obj__obj__text')
        self.func = self.manager.filter
        self.append_cache = True


########NEW FILE########
__FILENAME__ = test_models
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from cachebot.managers import CacheBotManager

class UniqueModel(models.Model):
    text = models.CharField(max_length=50, unique=True)
    objects = CacheBotManager(cache_get=True)
    
class NoCacheModel(models.Model):
    text = models.CharField(max_length=50)
    objects = CacheBotManager(cache_get=False)

class FirstModel(models.Model):
    text = models.CharField(max_length=50)
    objects = CacheBotManager(cache_get=True)

class SecondModel(models.Model):
    text = models.CharField(max_length=50)
    obj = models.ForeignKey(FirstModel)
    objects = CacheBotManager(cache_get=True)

class ThirdModel(models.Model):
    text = models.CharField(max_length=50)
    obj = models.ForeignKey(SecondModel)
    objects = CacheBotManager(cache_get=True)

class ManyModel(models.Model):
    text = models.CharField(max_length=50)
    firstmodel = models.ManyToManyField(FirstModel)
    thirdmodel = models.ManyToManyField(ThirdModel)
    objects = CacheBotManager(cache_get=True)

class GenericModel(models.Model):
    text = models.CharField(max_length=50)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    obj = generic.GenericForeignKey('content_type', 'object_id')
    objects = CacheBotManager(cache_get=True)

########NEW FILE########
__FILENAME__ = utils
from time import time

from django.core.cache import cache
from django.utils.hashcompat import md5_constructor
from django.db.models.sql.constants import LOOKUP_SEP
from django.db.models.base import ModelBase
from django.db.models.query_utils import QueryWrapper
from django.core.exceptions import ObjectDoesNotExist

def set_value(obj, key, value):
    """Helper method to handle setting values in a CachedQuerySet or ValuesQuerySet object"""
    try:
        obj[key] = value
    except TypeError:
        setattr(obj, key, value)

def get_invalidation_key(table_alias, accessor_path='', lookup_type='exact', negate=False, value='', version=None):
    """
    An invalidation key is associated with a set of cached queries. A blank accessor_path
    will create an invalidation key for this entire table instead of a specific row
    """
    
    # punt on this problem for now
    if isinstance(value, QueryWrapper) or lookup_type != 'exact' or negate:
        value = ''
        
    if hasattr(value, '__iter__'):
        if len(value) == 1:
            value = value[0]
        else:
            value = ''

    base_key = md5_constructor('.'.join((accessor_path, unicode(value))).encode('utf-8')).hexdigest()
    return cache.make_key('.'.join((table_alias, 'cachebot.invalidation', base_key)), version=version)

def get_values(instance, accessor_path):
    accessor_split = accessor_path.split(LOOKUP_SEP)
    if isinstance(instance, dict):
        try:
            yield instance[accessor_path]
            raise StopIteration
        except KeyError:
            # maybe this is a nested reverse relation
            accessor = accessor_split.pop(0)
            try:
                instance = instance[accessor]
            except KeyError:
                instance = instance[accessor + '_cache']
    
    for value in _get_nested_value(instance, accessor_split):
        if value is None:
            continue
        if isinstance(value.__class__, ModelBase):
            value = getattr(value, 'pk')
        yield value
    raise StopIteration

def _get_nested_value(instance, accessor_split):
    accessor = accessor_split.pop(0)
    try:
        value = getattr(instance, accessor)
    except AttributeError:
        if not instance:
            yield None
            raise StopIteration
        
        raise_error = True
        for modifier in ('_cache', '_id'):  
            if accessor.endswith(modifier):
                accessor = accessor[:-len(modifier)]
                try:
                    value = getattr(instance, accessor)
                    raise_error = False
                    break
                except AttributeError:
                    pass
                    
        if raise_error:
            yield None
            raise StopIteration

    if hasattr(value, 'select_reverse'):
        # check if a cached version of this reverse relation exists
        if hasattr(value, accessor + '_cache'):
            value = getattr(instance, accessor + '_cache')
        else:
            value = value.all()
    
    if hasattr(value, '__iter__'):
        if accessor_split:
            for obj in value:
                for nested_val in _get_nested_value(obj, accessor_split):
                    yield nested_val
        else:
            for nested_val in value:
                yield nested_val
    else:    
        if accessor_split:
            for nested_val in _get_nested_value(value, accessor_split):
                yield nested_val
        else:
            yield value
    raise StopIteration

def get_many_by_key(cache_key_f, item_keys, version=None):
    """
    For a series of item keys and a function that maps these keys to cache keys,
    get all the items from the cache if they are available there.
    
    Return a dictionary mapping the item keys to the objects retrieved from the
    cache.  Any items not found in the cache are not returned.
    """
    cache_key_to_item_key = {}
    for item_key in item_keys:
        cache_key = cache.make_key(cache_key_f(item_key), version=version)
        cache_key_to_item_key[cache_key] = item_key

    # request from cache
    from_cache = cache.get_many(cache_key_to_item_key.keys())

    results = {}
    for cache_key, value in from_cache.iteritems():
        item_key = cache_key_to_item_key[cache_key]
        results[item_key] = value
    return results

def fetch_objects(cache_key_f, get_database_f, item_keys):
    """
    For a series of item keys and two functions, get these items from the cache
    or from the database (individually so that the queries are cached).
    
    cache_key_f: function to convert an item_key to a cache key
    get_database_f: function to get an item from the database
    
    Returns a dictionary mapping item_keys to objects.  If the object
    does not exist in the database, ignore it.
    """
    item_key_to_item = get_many_by_key(cache_key_f, item_keys)
    
    for item_key in item_keys:
        if item_key not in item_key_to_item:
            # failed to get the item from the cache
            try:
                # have to get each item individually to cache the query
                item = get_database_f(item_key)
                item_key_to_item[item_key] = item
            except ObjectDoesNotExist:
                pass
    
    return item_key_to_item

def fetch_instances(model, field, values):
    """
    For a series of item keys, attempt to get the model from the cache,
    if that doesn't work, query the database.
    
    The point of all this is to do a single memcache query and then individual database queries
    for the remaining items. It would be nice to do a single database query for the remaining
    items, but it does not appear that cachebot supports this.
    """
    cache_key_f = lambda value: model.objects.filter((field, value)).get_cache_key()
    # since the filter query returns a list, it seems we need a list here to keep the types the same
    get_database_f = lambda value: [model.objects.get((field, value))]
    
    item_key_to_object = fetch_objects(cache_key_f, get_database_f, values)
    
    # remove the list surrounding each value by grabbing the first entry
    for k, v in item_key_to_object.items():
        if len(v) > 0:
            item_key_to_object[k] = v[0]
        else:
            del item_key_to_object[k] # this happens when cachebot has cached a result of [] for the query
        
    return item_key_to_object

def flush_cache(hard=True):
    from cachebot.models import CacheBotSignals
    from cachebot.signals import cache_signals

    CacheBotSignals.objects.all().delete()
    cache_signals.local_signals = {}
    if hard:
        cache.clear()
    else:
        cache.version = int(time()*10000)

########NEW FILE########
