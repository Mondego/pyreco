__FILENAME__ = admin
from django.contrib.admin.views.main import *
from django.contrib.admin import ModelAdmin
from djangosphinx.models import SphinxQuerySet

class SphinxModelAdmin(ModelAdmin):
    index = None
    weights = None
    # This is a hack
    search_fields = ['pk']
    actions = None
    
    def queryset(self, request):
        return SphinxQuerySet(
            model=self.model,
            index=self.index,
        )
    
    def get_changelist(self, request, **kwargs):
        return SphinxChangeList

class SphinxChangeList(ChangeList):
    def get_query_set(self):
        qs = self.root_query_set
        lookup_params = self.params.copy() # a dictionary of the query string
        for i in (ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR):
            if i in lookup_params:
                del lookup_params[i]
        for key, value in lookup_params.items():
            if not isinstance(key, str):
                # 'key' will be used as a keyword argument later, so Python
                # requires it to be a string.
                del lookup_params[key]
                lookup_params[smart_str(key)] = value

            # if key ends with __in, split parameter into separate values
            if key.endswith('__in'):
                lookup_params[key] = value.split(',')

        # Apply lookup parameters from the query string.
        try:
            qs = qs.filter(**lookup_params)
        # Naked except! Because we don't have any other way of validating "params".
        # They might be invalid if the keyword arguments are incorrect, or if the
        # values are not in the correct type, so we might get FieldError, ValueError,
        # ValicationError, or ? from a custom field that raises yet something else 
        # when handed impossible data.
        except:
            raise IncorrectLookupParameters

        # Use select_related() if one of the list_display options is a field
        # with a relationship and the provided queryset doesn't already have
        # select_related defined.
        if not qs._select_related:
            if self.list_select_related:
                qs = qs.select_related()
            else:
                for field_name in self.list_display:
                    try:
                        f = self.lookup_opts.get_field(field_name)
                    except models.FieldDoesNotExist:
                        pass
                    else:
                        if isinstance(f.rel, models.ManyToOneRel):
                            qs = qs.select_related()
                            break

        # Set ordering.
        if self.order_field:
            qs = qs.order_by('%s%s' % ((self.order_type == 'desc' and '-' or ''), self.order_field))

        if self.query:
            qs = qs.query(self.query)

        if not (lookup_params or self.query):
            # We don't show bare result sets in Sphinx
            return qs.none()

        return qs
    
    def get_results(self, request):
        paginator = Paginator(self.query_set, self.list_per_page)
        # Get the number of objects, with admin filters applied.
        result_count = paginator.count

        multi_page = result_count > self.list_per_page

        # Get the list of objects to display on this page.
        try:
            result_list = paginator.page(self.page_num+1).object_list
        except InvalidPage:
            result_list = ()

        self.full_result_count = result_count
        self.result_count = result_count
        self.result_list = result_list
        self.can_show_all = False
        self.multi_page = multi_page
        self.paginator = paginator
########NEW FILE########
__FILENAME__ = current
from djangosphinx.constants import *

try:
    from sphinxapi import *
except ImportError, exc:
    name = 'djangosphinx.apis.api%d' % (SPHINX_API_VERSION,)
    sphinxapi = __import__(name)
    for name in name.split('.')[1:]:
        sphinxapi = getattr(sphinxapi, name)
    for attr in dir(sphinxapi):
        globals()[attr] = getattr(sphinxapi, attr)

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python

import os, sys, os.path, warnings

# Add the project to the python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Set our settings module
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    raise ValueError('`DJANGO_SETTINGS_MODULE` was not set. Please use DJANGO_SETTINGS_MODULE=project.settings <command> --config sphinx.py.')

from django.conf import settings

assert getattr(settings, 'SPHINX_ROOT', None) is not None, "You must specify `SPHINX_ROOT` in your settings."

from django.template import RequestContext

if 'coffin' in settings.INSTALLED_APPS:
    import jinja2
    from coffin import shortcuts
else:
    from django import shortcuts
    
def render_to_string(template, context, request=None):
    if request:
        context_instance = RequestContext(request)
    else:
        context_instance = None
    return shortcuts.render_to_string(template, context, context_instance)

def relative_path(*args):
    return os.path.abspath(os.path.join(settings.SPHINX_ROOT, *args))

context = {
    'SPHINX_HOST': getattr(settings, 'SPHINX_HOST', '127.0.0.1'),
    'SPHINX_PORT': getattr(settings, 'SPHINX_PORT', '3312'),
    'relative_path': relative_path,
}
if getattr(settings, 'DATABASES', None):
    context.update({
        'DATABASE_HOST': settings.DATABASES['default']['HOST'],
        'DATABASE_PASSWORD': settings.DATABASES['default']['PASSWORD'],
        'DATABASE_USER': settings.DATABASES['default']['USER'],
        'DATABASE_PORT': settings.DATABASES['default']['PORT'],
        'DATABASE_NAME': settings.DATABASES['default']['NAME'],
    })
else:
    context.update({
        'DATABASE_HOST': settings.DATABASE_HOST,
        'DATABASE_PASSWORD': settings.DATABASE_PASSWORD,
        'DATABASE_USER': settings.DATABASE_USER,
        'DATABASE_PORT': settings.DATABASE_PORT,
        'DATABASE_NAME': settings.DATABASE_NAME,
    })

print render_to_string(getattr(settings, 'SPHINX_CONFIG_TEMPLATE', 'conf/sphinx.conf'), context)

########NEW FILE########
__FILENAME__ = constants
from django.conf import settings

__all__ = ('SPHINX_API_VERSION',)

# 0x113 = 1.19
# 0x107 = 1.17
SPHINX_API_VERSION = getattr(settings, 'SPHINX_API_VERSION', 0x107)
########NEW FILE########
__FILENAME__ = generate_sphinx_config
from django.core.management.base import AppCommand
from django.db import models

from djangosphinx.models import SphinxModelManager

class Command(AppCommand):
    help = "Prints generic configuration for any models which use a standard SphinxSearch manager."

    output_transaction = True

    def handle_app(self, app, **options):
        from djangosphinx.utils.config import generate_config_for_model
        model_classes = [getattr(app, n) for n in dir(app) if hasattr(getattr(app, n), '_meta')]
        found = 0
        for model in model_classes:
            indexes = getattr(model, '__sphinx_indexes__', [])
            for index in indexes:
                found += 1
                print generate_config_for_model(model, index)
        if found == 0:
            print "Unable to find any models in application which use standard SphinxSearch configuration."
        #return u'\n'.join(sql_create(app, self.style)).encode('utf-8')

########NEW FILE########
__FILENAME__ = manager
from models import *
import warnings

warnings.warn('`djangosphinx.manager` is deprecated. Please use `djangosphinx.models` instead.', DeprecationWarning)

########NEW FILE########
__FILENAME__ = models
import select
import socket
import time
import struct
import warnings
import operator
import apis.current as sphinxapi
import logging
import re
try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal # for Python 2.3

from django.db.models.query import QuerySet, Q
from django.conf import settings

__all__ = ('SearchError', 'ConnectionError', 'SphinxSearch', 'SphinxRelation', 'SphinxQuerySet')

from django.contrib.contenttypes.models import ContentType
from datetime import datetime, date

# server settings
SPHINX_SERVER           = getattr(settings, 'SPHINX_SERVER', 'localhost')
SPHINX_PORT             = int(getattr(settings, 'SPHINX_PORT', 3312))

# These require search API 275 (Sphinx 0.9.8)
SPHINX_RETRIES          = int(getattr(settings, 'SPHINX_RETRIES', 0))
SPHINX_RETRIES_DELAY    = int(getattr(settings, 'SPHINX_RETRIES_DELAY', 5))

MAX_INT = int(2**31-1)

EMPTY_RESULT_SET = dict(
    matches=[],
    total=0,
    total_found=0,
    words=[],
    attrs=[],
)

UNDEFINED = object()

class SearchError(Exception): pass
class ConnectionError(Exception): pass

class SphinxProxy(object):
    """
    Acts exactly like a normal instance of an object except that
    it will handle any special sphinx attributes in a `_sphinx` class.
    
    If there is no `sphinx` attribute on the instance, it will also
    add a proxy wrapper to `_sphinx` under that name as well.
    """
    __slots__ = ('__dict__', '__instance__', '_sphinx', 'sphinx')

    def __init__(self, instance, attributes):
        object.__setattr__(self, '__instance__', instance)
        object.__setattr__(self, '_sphinx', attributes)

    def _get_current_object(self):
        """
        Return the current object.  This is useful if you want the real object
        behind the proxy at a time for performance reasons or because you want
        to pass the object into a different context.
        """
        return self.__instance__
    _current_object = property(_get_current_object)

    def __dict__(self):
        try:
            return self._current_object.__dict__
        except RuntimeError:
            return AttributeError('__dict__')
    __dict__ = property(__dict__)

    def __repr__(self):
        try:
            obj = self._current_object
        except RuntimeError:
            return '<%s unbound>' % self.__class__.__name__
        return repr(obj)

    def __nonzero__(self):
        try:
            return bool(self._current_object)
        except RuntimeError:
            return False

    def __unicode__(self):
        try:
            return unicode(self._current_object)
        except RuntimeError:
            return repr(self)

    def __dir__(self):
        try:
            return dir(self._current_object)
        except RuntimeError:
            return []

    # def __getattribute__(self, name):
    #     if not hasattr(self._current_object, 'sphinx') and name == 'sphinx':
    #         name = '_sphinx'
    #     if name == '_sphinx':
    #         return object.__getattribute__(self, name)
    #     print object.__getattribute__(self, '_current_object')
    #     return getattr(object.__getattribute__(self, '_current_object'), name)

    def __getattr__(self, name, value=UNDEFINED):
        if not hasattr(self._current_object, 'sphinx') and name == 'sphinx':
            name = '_sphinx'
        if name == '_sphinx':
            return getattr(self, '_sphinx', value)
        if value == UNDEFINED:
            return getattr(self._current_object, name)
        return getattr(self._current_object, name, value)

    def __setattr__(self, name, value):
        if name == '_sphinx':
            return object.__setattr__(self, '_sphinx', value)
        elif name == 'sphinx':
            if not hasattr(self._current_object, 'sphinx'):
                return object.__setattr__(self, '_sphinx', value)
        return setattr(self._current_object, name, value)

    def __setitem__(self, key, value):
        self._current_object[key] = value

    def __delitem__(self, key):
        del self._current_object[key]

    def __setslice__(self, i, j, seq):
        self._current_object[i:j] = seq

    def __delslice__(self, i, j):
        del self._current_object[i:j]

    __delattr__ = lambda x, n: delattr(x._current_object, n)
    __str__ = lambda x: str(x._current_object)
    __unicode__ = lambda x: unicode(x._current_object)
    __lt__ = lambda x, o: x._current_object < o
    __le__ = lambda x, o: x._current_object <= o
    __eq__ = lambda x, o: x._current_object == o
    __ne__ = lambda x, o: x._current_object != o
    __gt__ = lambda x, o: x._current_object > o
    __ge__ = lambda x, o: x._current_object >= o
    __cmp__ = lambda x, o: cmp(x._current_object, o)
    __hash__ = lambda x: hash(x._current_object)
    # attributes are currently not callable
    # __call__ = lambda x, *a, **kw: x._current_object(*a, **kw)
    __len__ = lambda x: len(x._current_object)
    __getitem__ = lambda x, i: x._current_object[i]
    __iter__ = lambda x: iter(x._current_object)
    __contains__ = lambda x, i: i in x._current_object
    __getslice__ = lambda x, i, j: x._current_object[i:j]
    __add__ = lambda x, o: x._current_object + o
    __sub__ = lambda x, o: x._current_object - o
    __mul__ = lambda x, o: x._current_object * o
    __floordiv__ = lambda x, o: x._current_object // o
    __mod__ = lambda x, o: x._current_object % o
    __divmod__ = lambda x, o: x._current_object.__divmod__(o)
    __pow__ = lambda x, o: x._current_object ** o
    __lshift__ = lambda x, o: x._current_object << o
    __rshift__ = lambda x, o: x._current_object >> o
    __and__ = lambda x, o: x._current_object & o
    __xor__ = lambda x, o: x._current_object ^ o
    __or__ = lambda x, o: x._current_object | o
    __div__ = lambda x, o: x._current_object.__div__(o)
    __truediv__ = lambda x, o: x._current_object.__truediv__(o)
    __neg__ = lambda x: -(x._current_object)
    __pos__ = lambda x: +(x._current_object)
    __abs__ = lambda x: abs(x._current_object)
    __invert__ = lambda x: ~(x._current_object)
    __complex__ = lambda x: complex(x._current_object)
    __int__ = lambda x: int(x._current_object)
    __long__ = lambda x: long(x._current_object)
    __float__ = lambda x: float(x._current_object)
    __oct__ = lambda x: oct(x._current_object)
    __hex__ = lambda x: hex(x._current_object)
    __index__ = lambda x: x._current_object.__index__()
    __coerce__ = lambda x, o: x.__coerce__(x, o)
    __enter__ = lambda x: x.__enter__()
    __exit__ = lambda x, *a, **kw: x.__exit__(*a, **kw)

def to_sphinx(value):
    "Convert a value into a sphinx query value"
    if isinstance(value, date) or isinstance(value, datetime):
        return int(time.mktime(value.timetuple()))
    elif isinstance(value, decimal.Decimal) or isinstance(value, float):
        return float(value)
    return int(value)

class SphinxQuerySet(object):
    available_kwargs = ('rankmode', 'mode', 'weights', 'maxmatches', 'passages', 'passages_opts')
    
    def __init__(self, model=None, using=None, **kwargs):
        self._select_related        = False
        self._select_related_args   = {}
        self._select_related_fields = []
        self._filters               = {}
        self._excludes              = {}
        self._extra                 = {}
        self._query                 = ''
        self.__metadata             = None
        self._offset                = 0
        self._limit                 = 20

        self._groupby               = None
        self._sort                  = None
        self._weights               = [1, 100]

        self._passages              = False
        self._passages_opts         = {}
        self._maxmatches            = 1000
        self._result_cache          = None
        self._mode                  = sphinxapi.SPH_MATCH_ALL
        self._rankmode              = getattr(sphinxapi, 'SPH_RANK_PROXIMITY_BM25', None)
        self.model                  = model
        self._anchor                = {}
        self.__metadata             = {}
        
        self.using                  = using
        
        options = self._format_options(**kwargs)
        for key, value in options.iteritems():
            setattr(self, key, value)

        if model:
            self._index             = kwargs.get('index', model._meta.db_table)
        else:
            self._index             = kwargs.get('index')

    def __repr__(self):
        if self._result_cache is not None:
            return repr(self._get_data())
        else:
            return '<%s instance>' % (self.__class__.__name__,)

    def __len__(self):
        return self.count()
        
    def __iter__(self):
        return iter(self._get_data())
    
    def __getitem__(self, k):
        if not isinstance(k, (slice, int, long)):
            raise TypeError
        assert (not isinstance(k, slice) and (k >= 0)) \
            or (isinstance(k, slice) and (k.start is None or k.start >= 0) and (k.stop is None or k.stop >= 0)), \
            "Negative indexing is not supported."
        if self._result_cache is not None:
            # Check to see if this is a portion of an already existing result cache
            if type(k) == slice:
                start = k.start
                stop = k.stop-k.start
                if start < self._offset or k.stop > self._limit:
                    self._result_cache = None
                else:
                    start = start-self._offset
                    return self._get_data()[start:k.stop]
            else:
                if k not in range(self._offset, self._limit+self._offset):
                    self._result_cache = None
                else:
                    return self._get_data()[k-self._offset]
        if type(k) == slice:
            self._offset = k.start
            self._limit = k.stop-k.start
            return self._get_data()
        else:
            self._offset = k
            self._limit = 1
            return self._get_data()[0]

    def _format_options(self, **kwargs):
        kwargs['rankmode'] = getattr(sphinxapi, kwargs.get('rankmode', 'SPH_RANK_NONE'), None)
        kwargs['mode'] = getattr(sphinxapi, kwargs.get('mode', 'SPH_MATCH_ALL'), sphinxapi.SPH_MATCH_ALL)

        kwargs = dict([('_%s' % (key,), value) for key, value in kwargs.iteritems() if key in self.available_kwargs])
        return kwargs

    def get_query_set(self, model):
        qs = model._default_manager
        if self.using:
            qs = qs.db_manager(self.using)
        return qs.all()

    def set_options(self, **kwargs):
        kwargs = self._format_options(**kwargs)
        return self._clone(**kwargs)

    def query(self, string):
        return self._clone(_query=unicode(string).encode('utf-8'))

    def group_by(self, attribute, func, groupsort='@group desc'):
        return self._clone(_groupby=attribute, _groupfunc=func, _groupsort=groupsort)

    def rank_none(self):
        warnings.warn('`rank_none()` is deprecated. Use `set_options(rankmode=None)` instead.', DeprecationWarning)
        return self._clone(_rankmode=sphinxapi.SPH_RANK_NONE)

    def mode(self, mode):
        warnings.warn('`mode()` is deprecated. Use `set_options(mode='')` instead.', DeprecationWarning)
        return self._clone(_mode=mode)

    def weights(self, weights):
        warnings.warn('`mode()` is deprecated. Use `set_options(weights=[])` instead.', DeprecationWarning)
        return self._clone(_weights=weights)

    def on_index(self, index):
        warnings.warn('`mode()` is deprecated. Use `set_options(on_index=foo)` instead.', DeprecationWarning)
        return self._clone(_index=index)

    # only works on attributes
    def filter(self, **kwargs):
        filters = self._filters.copy()
        for k,v in kwargs.iteritems():
            if hasattr(v, '__iter__'):
                v = list(v)
            elif not (isinstance(v, list) or isinstance(v, tuple)):
                 v = [v,]
            filters.setdefault(k, []).extend(map(to_sphinx, v))
        return self._clone(_filters=filters)

    def geoanchor(self, lat_attr, lng_attr, lat, lng):
        assert sphinxapi.VER_COMMAND_SEARCH >= 0x113, "You must upgrade sphinxapi to version 0.98 to use Geo Anchoring."
        return self._clone(_anchor=(lat_attr, lng_attr, float(lat), float(lng)))

    # this actually does nothing, its just a passthru to
    # keep things looking/working generally the same
    def all(self):
        return self
    
    def none(self):
        c = EmptySphinxQuerySet()
        c.__dict__.update(self.__dict__.copy())
        return c
        
    # only works on attributes
    def exclude(self, **kwargs):
        filters = self._excludes.copy()
        for k,v in kwargs.iteritems():
            if hasattr(v, 'next'):
                v = list(v)
            elif not (isinstance(v, list) or isinstance(v, tuple)):
                 v = [v,]
            filters.setdefault(k, []).extend(map(to_sphinx, v))
        return self._clone(_excludes=filters)

    def escape(self, value):
        return re.sub(r"([=\(\)|\-!@~\"&/\\\^\$\=])", r"\\\1", value)

    # you cannot order by @weight (it always orders in descending)
    # keywords are @id, @weight, @rank, and @relevance
    def order_by(self, *args, **kwargs):
        mode = kwargs.pop('mode', sphinxapi.SPH_SORT_EXTENDED)
        if mode == sphinxapi.SPH_SORT_EXTENDED:
            sort_by = []
            for arg in args:
                sort = 'ASC'
                if arg[0] == '-':
                    arg = arg[1:]
                    sort = 'DESC'
                if arg == 'id':
                    arg = '@id'
                sort_by.append('%s %s' % (arg, sort))
        else:
            sort_by = args
        if sort_by:
            return self._clone(_sort=(mode, ', '.join(sort_by)))
        return self
                    
    # pass these thru on the queryset and let django handle it
    def select_related(self, *args, **kwargs):
        _args = self._select_related_fields[:]
        _args.extend(args)
        _kwargs = self._select_related_args.copy()
        _kwargs.update(kwargs)
        
        return self._clone(
            _select_related=True,
            _select_related_fields=_args,
            _select_related_args=_kwargs,
        )
    
    def extra(self, **kwargs):
        extra = self._extra.copy()
        extra.update(kwargs)
        return self._clone(_extra=extra)

    def count(self):
        return min(self._sphinx.get('total_found', 0), self._maxmatches)

    def reset(self):
        return self.__class__(self.model, self._index)

    # Internal methods
    def _get_sphinx_client(self):
        client = sphinxapi.SphinxClient()
        client.SetServer(SPHINX_SERVER, SPHINX_PORT)
        return client

    def _clone(self, **kwargs):
        # Clones the queryset passing any changed args
        c = self.__class__()
        c.__dict__.update(self.__dict__.copy())
        for k, v in kwargs.iteritems():
            setattr(c, k, v)
        return c
    
    def _sphinx(self):
        if not self.__metadata:
            # We have to force execution if this is accessed beforehand
            self._get_data()
        return self.__metadata
    _sphinx = property(_sphinx)

    def _get_data(self):
        assert(self._index)
        # need to find a way to make this work yet
        if self._result_cache is None:
            self._result_cache = list(self._get_results())
        return self._result_cache

    def _get_sphinx_results(self):
        assert(self._offset + self._limit <= self._maxmatches)

        client = self._get_sphinx_client()

        params = []

        if self._sort:
            params.append('sort=%s' % (self._sort,))
            client.SetSortMode(*self._sort)
        
        if isinstance(self._weights, dict):
            client.SetFieldWeights(self._weights)
        else:
            # assume its a list
            client.SetWeights(map(int, self._weights))
        params.append('weights=%s' % (self._weights,))

        params.append('matchmode=%s' % (self._mode,))
        client.SetMatchMode(self._mode)
        
        def _handle_filters(filter_list, exclude=False):
            for name, values in filter_list.iteritems():
                parts = len(name.split('__'))
                if parts > 2:
                    raise NotImplementedError, 'Related object and/or multiple field lookups not supported'
                elif parts == 2:
                    # The float handling for __gt and __lt is kind of ugly..
                    name, lookup = name.split('__', 1)
                    is_float = isinstance(values[0], float)
                    if lookup in ('gt', 'gte'):
                        value = values[0]
                        if lookup == 'gt':
                            if is_float:
                                value += (1.0/MAX_INT)
                            else:
                                value += 1
                        _max = MAX_INT
                        if is_float:
                            _max = float(_max)
                        args = (name, value, _max, exclude)
                    elif lookup in ('lt', 'lte'):
                        value = values[0]
                        if lookup == 'lt':
                            if is_float:
                                value -= (1.0/MAX_INT)
                            else:
                                value -= 1
                        _max = -MAX_INT
                        if is_float:
                            _max = float(_max)
                        args = (name, _max, value, exclude)
                    elif lookup == 'in':
                        args = (name, values, exclude)
                    elif lookup == 'range':
                        args = (name, values[0], values[1], exclude)
                    else:
                        raise NotImplementedError, 'Related object and/or field lookup "%s" not supported' % lookup
                    if is_float:
                        client.SetFilterFloatRange(*args)
                    elif not exclude and self.model and name == self.model._meta.pk.column:
                        client.SetIDRange(*args[1:3])
                    elif lookup == 'in':
                        client.SetFilter(name, values, exclude)
                    else:
                        client.SetFilterRange(*args)
                else:
                    client.SetFilter(name, values, exclude)

        # Include filters
        if self._filters:
            params.append('filters=%s' % (self._filters,))
            _handle_filters(self._filters)

        # Exclude filters
        if self._excludes:
            params.append('excludes=%s' % (self._excludes,))
            _handle_filters(self._excludes, True)
        
        if self._groupby:
            params.append('groupby=%s' % (self._groupby,))
            client.SetGroupBy(self._groupby, self._groupfunc, self._groupsort)

        if self._anchor:
            params.append('geoanchor=%s' % (self._anchor,))
            client.SetGeoAnchor(*self._anchor)

        if self._rankmode:
            params.append('rankmode=%s' % (self._rankmode,))
            client.SetRankingMode(self._rankmode)

        if not self._limit > 0:
            # Fix for Sphinx throwing an assertion error when you pass it an empty limiter
            return EMPTY_RESULT_SET
        
        if sphinxapi.VER_COMMAND_SEARCH >= 0x113:
            client.SetRetries(SPHINX_RETRIES, SPHINX_RETRIES_DELAY)
        
        client.SetLimits(int(self._offset), int(self._limit), int(self._maxmatches))
        
        # To avoid modifying the Sphinx API, we solve unicode indexes here
        if isinstance(self._index, unicode):
            self._index = self._index.encode('utf-8')
        
        results = client.Query(self._query, self._index)
        
        # The Sphinx API doesn't raise exceptions

        if not results:
            if client.GetLastError():
                raise SearchError, client.GetLastError()
            elif client.GetLastWarning():
                raise SearchError, client.GetLastWarning()
            else:
                results = EMPTY_RESULT_SET
        elif not results['matches']:
            results = EMPTY_RESULT_SET
        
        logging.debug('Found %s results for search query %s on %s with params: %s', results['total'], self._query, self._index, ', '.join(params))
        
        return results
    
    def get(self, **kwargs):
        """Hack to support ModelAdmin"""
        queryset = self.model._default_manager
        if self._select_related:
            queryset = queryset.select_related(*self._select_related_fields, **self._select_related_args)
        if self._extra:
            queryset = queryset.extra(**self._extra)
        return queryset.get(**kwargs)

    def _get_results(self):
        results = self._get_sphinx_results()
        if not results:
            results = EMPTY_RESULT_SET
        self.__metadata = {
            'total': results['total'],
            'total_found': results['total_found'],
            'words': results['words'],
        }
        if results['matches'] and self._passages:
            # We need to do some initial work for passages
            # XXX: The passages implementation has a potential gotcha if your id
            # column is not actually your primary key
            words = ' '.join([w['word'] for w in results['words']])
            
        if self.model:
            if results['matches']:
                queryset = self.get_query_set(self.model)
                if self._select_related:
                    queryset = queryset.select_related(*self._select_related_fields, **self._select_related_args)
                if self._extra:
                    queryset = queryset.extra(**self._extra)

                # django-sphinx supports the compositepks branch
                # as well as custom id columns in your sphinx configuration
                # but all primary key columns still need to be present in the field list
                pks = getattr(self.model._meta, 'pks', [self.model._meta.pk])
                if results['matches'][0]['attrs'].get(pks[0].column):
                    
                    # XXX: Sometimes attrs is empty and we cannot have custom primary key attributes
                    for r in results['matches']:
                        r['id'] = ', '.join([unicode(r['attrs'][p.column]) for p in pks])
            
                    # Join our Q objects to get a where clause which
                    # matches all primary keys, even across multiple columns
                    q = reduce(operator.or_, [reduce(operator.and_, [Q(**{p.name: r['attrs'][p.column]}) for p in pks]) for r in results['matches']])
                    queryset = queryset.filter(q)
                else:
                    for r in results['matches']:
                        r['id'] = unicode(r['id'])
                    queryset = queryset.filter(pk__in=[r['id'] for r in results['matches']])
                queryset = dict([(', '.join([unicode(getattr(o, p.attname)) for p in pks]), o) for o in queryset])

                if self._passages:
                    # TODO: clean this up
                    for r in results['matches']:
                        if r['id'] in queryset:
                            r['passages'] = self._get_passages(queryset[r['id']], results['fields'], words)
                
                results = [SphinxProxy(queryset[r['id']], r) for r in results['matches'] if r['id'] in queryset]
            else:
                results = []
        else:
            "We did a query without a model, lets see if there's a content_type"
            results['attrs'] = dict(results['attrs'])
            if 'content_type' in results['attrs']:
                "Now we have to do one query per content_type"
                objcache = {}
                for r in results['matches']:
                    ct = r['attrs']['content_type']
                    r['id'] = unicode(r['id'])
                    objcache.setdefault(ct, {})[r['id']] = None
                for ct in objcache:
                    model_class = ContentType.objects.get(pk=ct).model_class()
                    pks = getattr(model_class._meta, 'pks', [model_class._meta.pk])
                    
                    if results['matches'][0]['attrs'].get(pks[0].column):
                        for r in results['matches']:
                            if r['attrs']['content_type'] == ct:
                                val = ', '.join([unicode(r['attrs'][p.column]) for p in pks])
                                objcache[ct][r['id']] = r['id'] = val
                    
                        q = reduce(operator.or_, [reduce(operator.and_, [Q(**{p.name: r['attrs'][p.column]}) for p in pks]) for r in results['matches'] if r['attrs']['content_type'] == ct])
                        queryset = self.get_query_set(model_class).filter(q)
                    else:
                        queryset = self.get_query_set(model_class).filter(pk__in=[r['id'] for r in results['matches'] if r['attrs']['content_type'] == ct])

                    for o in queryset:
                        objcache[ct][', '.join([unicode(getattr(o, p.name)) for p in pks])] = o
                
                if self._passages:
                    for r in results['matches']:
                        ct = r['attrs']['content_type']
                        if r['id'] in objcache[ct]:
                            r['passages'] = self._get_passages(objcache[ct][r['id']], results['fields'], words)
                results = [SphinxProxy(objcache[r['attrs']['content_type']][r['id']], r) for r in results['matches'] if r['id'] in objcache[r['attrs']['content_type']]]
            else:
                results = results['matches']
        self._result_cache = results
        return results

    def _get_passages(self, instance, fields, words):
        client = self._get_sphinx_client()

        docs = [getattr(instance, f) for f in fields]
        if isinstance(self._passages_opts, dict):
            opts = self._passages_opts
        else:
            opts = {}
        if isinstance(self._index, unicode):
            self._index = self._index.encode('utf-8')
        passages_list = client.BuildExcerpts(docs, self._index, words, opts)
        
        passages = {}
        c = 0
        for f in fields:
            passages[f] = passages_list[c]
            c += 1
        return passages

class EmptySphinxQuerySet(SphinxQuerySet):
    def _get_sphinx_results(self):
        return None

class SphinxModelManager(object):
    def __init__(self, model, **kwargs):
        self.model = model
        self._index = kwargs.pop('index', model._meta.db_table)
        self._kwargs = kwargs
    
    def _get_query_set(self):
        return SphinxQuerySet(self.model, index=self._index, **self._kwargs)
    
    def get_index(self):
        return self._index
    
    def all(self):
        return self._get_query_set()
    
    def none(self):
        return self._get_query_set().none()
    
    def filter(self, **kwargs):
        return self._get_query_set().filter(**kwargs)
    
    def query(self, *args, **kwargs):
        return self._get_query_set().query(*args, **kwargs)

    def on_index(self, *args, **kwargs):
        return self._get_query_set().on_index(*args, **kwargs)

    def geoanchor(self, *args, **kwargs):
        return self._get_query_set().geoanchor(*args, **kwargs)

class SphinxInstanceManager(object):
    """Collection of tools useful for objects which are in a Sphinx index."""
    # TODO: deletion support
    def __init__(self, instance, index):
        self._instance = instance
        self._index = index
        
    def update(self, **kwargs):
        assert sphinxapi.VER_COMMAND_SEARCH >= 0x113, "You must upgrade sphinxapi to version 0.98 to use UpdateAttributes."
        sphinxapi.UpdateAttributes(self._index, kwargs.keys(), dict(self.instance.pk, map(to_sphinx, kwargs.values())))

class SphinxSearch(object):
    def __init__(self, index=None, using=None, **kwargs):
        self._kwargs = kwargs
        self._sphinx = None
        self._index = index
        self.model = None
        self.using = using
    
    def __call__(self, index, **kwargs):
        warnings.warn('For non-model searches use a SphinxQuerySet instance.', DeprecationWarning)
        return SphinxQuerySet(index=index, using=self.using, **kwargs)
    
    def __get__(self, instance, model, **kwargs):
        if instance:
            return SphinxInstanceManager(instance, self._index)
        return self._sphinx
    
    def get_query_set(self):
        """Override this method to change the QuerySet used for config generation."""
        return self.model._default_manager.all()
    
    def contribute_to_class(self, model, name, **kwargs):
        if self._index is None:
            self._index = model._meta.db_table
        self._sphinx = SphinxModelManager(model, index=self._index, **self._kwargs)
        self.model = model
        if getattr(model, '__sphinx_indexes__', None) is None:
            setattr(model, '__sphinx_indexes__', [self._index])
        else:
            model.__sphinx_indexes__.append(self._index)
        setattr(model, name, self._sphinx)

class SphinxRelationProxy(SphinxProxy):
    def count(self):
        return min(self._sphinx['attrs']['@count'], self._maxmatches)
    
class SphinxRelation(SphinxSearch):
    """
    Adds "related model" support to django-sphinx --
    http://code.google.com/p/django-sphinx/
    http://www.sphinxsearch.com/
    
    Example --
    
    class MySearch(SphinxSearch):
        myrelatedobject = SphinxRelation(RelatedModel)
        anotherone = SphinxRelation(AnotherModel)
        ...
    
    class MyModel(models.Model):
        search = MySearch('index')
    
    """
    def __init__(self, model=None, attr=None, sort='@count desc', **kwargs):
        if model:
            self._related_model = model
            self._related_attr = attr or model.__name__.lower()
            self._related_sort = sort
        super(SphinxRelation, self).__init__(**kwargs)
        
    def __get__(self, instance, instance_model, **kwargs):
        self._mode = instance._mode
        self._rankmode = instance._rankmode
        self._index = instance._index
        self._query = instance._query
        self._filters = instance._filters
        self._excludes = instance._excludes
        self.model = self._related_model
        self._groupby = self._related_attr
        self._groupsort = self._related_sort
        self._groupfunc = sphinxapi.SPH_GROUPBY_ATTR
        return self

    def _get_results(self):
        results = self._get_sphinx_results()
        if not results or not results['matches']:
            # No matches so lets create a dummy result set
            results = EMPTY_RESULT_SET
        elif self.model:
            ids = []
            for r in results['matches']:
                value = r['attrs']['@groupby']
                if isinstance(value, (int, long)):
                    ids.append(value)
                else:
                    ids.extend()
            qs = self.get_query_set(self.model).filter(pk__in=set(ids))
            if self._select_related:
                qs = qs.select_related(*self._select_related_fields,
                                       **self._select_related_args)
            if self._extra:
                qs = qs.extra(**self._extra)
            queryset = dict([(o.id, o) for o in qs])
            results = [ SphinxRelationProxy(queryset[k['attrs']['@groupby']], k) \
                        for k in results['matches'] \
                        if k['attrs']['@groupby'] in queryset ]
        self.__metadata = {
            'total': results['total'],
            'total_found': results['total_found'],
            'words': results['words'],
        }
        self._result_cache = results
        return results

    def _sphinx(self):
        if not self.__metadata:
            # We have to force execution if this is accessed beforehand
            self._get_data()
        return self.__metadata
    _sphinx = property(_sphinx)

########NEW FILE########
__FILENAME__ = config
from django.conf import settings
from django.template import Template, Context

from django.db import models
from django.contrib.contenttypes.models import ContentType

import os.path

import djangosphinx.apis.current as sphinxapi

__all__ = ('generate_config_for_model', 'generate_config_for_models')

def _get_database_engine():
    if settings.DATABASE_ENGINE == 'mysql':
        return settings.DATABASE_ENGINE
    elif settings.DATABASE_ENGINE.startswith('postgresql'):
        return 'pgsql'
    raise ValueError, "Only MySQL and PostgreSQL engines are supported by Sphinx."

def _get_template(name):
    paths = (
        os.path.join(os.path.dirname(__file__), '../apis/api%s/templates/' % (sphinxapi.VER_COMMAND_SEARCH,)),
        os.path.join(os.path.dirname(__file__), '../templates/'),
    )
    for path in paths:
        try:
            fp = open(path + name, 'r')
        except IOError:
            continue
        try:
            t = Template(fp.read())
            return t
        finally:
            fp.close()
    raise ValueError, "Template matching name does not exist: %s." % (name,)

def _is_sourcable_field(field):
    # We can use float fields in 0.98
    if sphinxapi.VER_COMMAND_SEARCH >= 0x113 and (isinstance(field, models.FloatField) or isinstance(field, models.DecimalField)):
        return True
    elif isinstance(field, models.ForeignKey):
        return True
    elif isinstance(field, models.IntegerField) and field.choices:
        return True
    elif not field.rel:
        return True
    return False

# No trailing slashes on paths
DEFAULT_SPHINX_PARAMS = {
    'database_engine': _get_database_engine(),
    'database_host': settings.DATABASE_HOST,
    'database_port': settings.DATABASE_PORT,
    'database_name': settings.DATABASE_NAME,
    'database_user': settings.DATABASE_USER,
    'database_password': settings.DATABASE_PASSWORD,
    'log_file': '/var/log/sphinx/searchd.log',
    'data_path': '/var/data',
}

def get_index_context(index):
    params = DEFAULT_SPHINX_PARAMS
    params.update({
        'index_name': index,
        'source_name': index,
    })

    return params

def get_source_context(tables, index, valid_fields):
    params = DEFAULT_SPHINX_PARAMS
    params.update({
        'tables': tables,
        'source_name': index,
        'index_name': index,
        'database_engine': _get_database_engine(),
        'field_names': [f[1] for f in valid_fields],
        'group_columns': [f[1] for f in valid_fields if f[2] or isinstance(f[0], models.BooleanField) or isinstance(f[0], models.IntegerField)],
        'date_columns': [f[1] for f in valid_fields if issubclass(f[0], models.DateTimeField) or issubclass(f[0], models.DateField)],
        'float_columns': [f[1] for f in valid_fields if isinstance(f[0], models.FloatField) or isinstance(f[0], models.DecimalField)],
    })
    try:
        from django.contrib.gis.db.models import PointField
        params.update({
            'gis_columns': [f.column for f in valid_fields if isinstance(f, PointField)],
            'srid': getattr(settings, 'GIS_SRID', 4326), # reasonable lat/lng default
        })
        if params['database_engine'] == 'pgsql' and params['gis_columns']:
            params['field_names'].extend(["radians(ST_X(ST_Transform(%(field_name)s, %(srid)s))) AS %(field_name)s_longitude, radians(ST_Y(ST_Transform(%(field_name)s, %(srid)s))) AS %(field_name)s_latitude" % {'field_name': f, 'srid': params['srid']} for f in params['gis_columns']])
    except ImportError:
        # GIS not supported
        pass
    return params

# Generate for single models

def generate_config_for_model(model_class, index=None, sphinx_params={}):
    """
    Generates a sample configuration including an index and source for
    the given model which includes all attributes and date fields.
    """
    return generate_source_for_model(model_class, index, sphinx_params) + "\n\n" + generate_index_for_model(model_class, index, sphinx_params)

def generate_index_for_model(model_class, index=None, sphinx_params={}):
    """Generates a source configmration for a model."""
    t = _get_template('index.conf')
    
    if index is None:
        index = model_class._meta.db_table
    
    params = get_index_context(index)
    params.update(sphinx_params)
    
    c = Context(params)
    
    return t.render(c)

def generate_source_for_model(model_class, index=None, sphinx_params={}):
    """Generates a source configmration for a model."""
    t = _get_template('source.conf')

    def _the_tuple(f):
        return (f.__class__, f.column, getattr(f.rel, 'to', None), f.choices)

    valid_fields = [_the_tuple(f) for f in model_class._meta.fields if _is_sourcable_field(f)]
    
    table = model_class._meta.db_table
    
    if index is None:
        index = table
        
    params = get_source_context([table], index, valid_fields)
    params.update({
        'table_name': table,
        'primary_key': model_class._meta.pk.column,
    })
    params.update(sphinx_params)

    c = Context(params)
    
    return t.render(c)
    
# Generate for multiple models (search UNIONs)

def generate_config_for_models(model_classes, index=None, sphinx_params={}):
    """
    Generates a sample configuration including an index and source for
    the given model which includes all attributes and date fields.
    """
    return generate_source_for_models(model_classes, index, sphinx_params) + "\n\n" + generate_index_for_models(model_classes, index, sphinx_params)

def generate_index_for_models(model_classes, index=None, sphinx_params={}):
    """Generates a source configmration for a model."""
    t = _get_template('index-multiple.conf')
    
    if index is None:
        index = '_'.join(m._meta.db_table for m in model_classes)
    
    params = get_index_context(index)
    params.update(sphinx_params)
    
    c = Context(params)
    
    return t.render(c)

def generate_source_for_models(model_classes, index=None, sphinx_params={}):
    """Generates a source configmration for a model."""
    t = _get_template('source-multiple.conf')
    
    # We need to loop through each model and find only the fields that exist *exactly* the
    # same across models.
    def _the_tuple(f):
        return (f.__class__, f.column, getattr(f.rel, 'to', None), f.choices)
    
    valid_fields = [_the_tuple(f) for f in model_classes[0]._meta.fields if _is_sourcable_field(f)]
    for model_class in model_classes[1:]:
        valid_fields = [_the_tuple(f) for f in model_class._meta.fields if _the_tuple(f) in valid_fields]
    
    tables = []
    for model_class in model_classes:
        tables.append((model_class._meta.db_table, ContentType.objects.get_for_model(model_class)))
    
    if index is None:
        index = '_'.join(m._meta.db_table for m in model_classes)
    
    params = get_source_context(tables, index, valid_fields)
    params.update(sphinx_params)

    c = Context(params)
    
    return t.render(c)
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-sphinx documentation build configuration file, created by
# sphinx-quickstart on Mon Sep 14 22:31:42 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-sphinx'
copyright = u'2009, David Cramer'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.1.1'
# The full version, including alpha/beta/rc tags.
release = '2.1.1'

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
html_static_path = ['_static']

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
htmlhelp_basename = 'django-sphinxdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-sphinx.tex', u'django-sphinx Documentation',
   u'David Cramer', 'manual'),
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
# Django settings for sphinxtest project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'mysql'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'sphinxtest'             # Or path to database file if using sqlite3.
DATABASE_USER = 'sphinxtest'             # Not used with sqlite3.
DATABASE_PASSWORD = 'sphinxtest'         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

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
SECRET_KEY = 'e-9mk4k#jf-u5aj!*6nzt@2f*mm3wgk15k+*f%%1l6hc!t**ai'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
)

ROOT_URLCONF = 'sphinxtest.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'sphinxtest.tests',
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from djangosphinx import SphinxSearch

import datetime

class Group(models.Model):
    name = models.CharField(max_length=32)

class Document(models.Model):
    group       = models.ForeignKey(Group)
    date_added  = models.DateTimeField(default=datetime.datetime.now)
    title       = models.CharField(max_length=32)
    content     = models.TextField()
    
    search      = SphinxSearch(index="test")
    
    class Meta:
        db_table = 'documents'
########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:
    # (r'^sphinxtest/', include('sphinxtest.foo.urls')),

    # Uncomment this for admin:
#     (r'^admin/', include('django.contrib.admin.urls')),
)

########NEW FILE########
