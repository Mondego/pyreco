__FILENAME__ = admin
from django.contrib import admin

from .models import Query, Stack, Sample


class QueryAdmin(admin.ModelAdmin):
    list_display = ('hash', 'created_dt',)
    list_filter = ('created_dt', 'query_type',)
    readonly_fields = ('created_dt',)


class StackAdmin(admin.ModelAdmin):
    list_display = ('hash', 'created_dt',)
    list_filter = ('created_dt',)
    readonly_fields = ('created_dt',)


class SampleAdmin(admin.ModelAdmin):
    list_display = ('created_dt',)
    list_filter = ('created_dt',)
    readonly_fields = ('created_dt',)

    
admin.site.register(Query, QueryAdmin)
admin.site.register(Stack, StackAdmin)
admin.site.register(Sample, SampleAdmin)


########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Query'
        db.create_table('djangosampler_query', (
            ('hash', self.gf('django.db.models.fields.CharField')(max_length=32, primary_key=True)),
            ('query', self.gf('django.db.models.fields.TextField')()),
            ('total_duration', self.gf('django.db.models.fields.FloatField')(default=0)),
            ('total_cost', self.gf('django.db.models.fields.FloatField')(default=0)),
            ('count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('query_type', self.gf('django.db.models.fields.CharField')(max_length=32, db_index=True)),
        ))
        db.send_create_signal('djangosampler', ['Query'])

        # Adding model 'Stack'
        db.create_table('djangosampler_stack', (
            ('hash', self.gf('django.db.models.fields.CharField')(max_length=32, primary_key=True)),
            ('stack', self.gf('django.db.models.fields.TextField')()),
            ('total_duration', self.gf('django.db.models.fields.FloatField')(default=0)),
            ('total_cost', self.gf('django.db.models.fields.FloatField')(default=0)),
            ('count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('query', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djangosampler.Query'])),
        ))
        db.send_create_signal('djangosampler', ['Stack'])

        # Adding model 'Sample'
        db.create_table('djangosampler_sample', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('query', self.gf('django.db.models.fields.TextField')()),
            ('duration', self.gf('django.db.models.fields.FloatField')()),
            ('cost', self.gf('django.db.models.fields.FloatField')()),
            ('stack', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djangosampler.Stack'])),
            ('params', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('djangosampler', ['Sample'])


    def backwards(self, orm):
        
        # Deleting model 'Query'
        db.delete_table('djangosampler_query')

        # Deleting model 'Stack'
        db.delete_table('djangosampler_stack')

        # Deleting model 'Sample'
        db.delete_table('djangosampler_sample')


    models = {
        'djangosampler.query': {
            'Meta': {'object_name': 'Query'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'query_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'db_index': 'True'}),
            'total_cost': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'total_duration': ('django.db.models.fields.FloatField', [], {'default': '0'})
        },
        'djangosampler.sample': {
            'Meta': {'object_name': 'Sample'},
            'cost': ('django.db.models.fields.FloatField', [], {}),
            'duration': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangosampler.Stack']"})
        },
        'djangosampler.stack': {
            'Meta': {'object_name': 'Stack'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'query': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangosampler.Query']"}),
            'stack': ('django.db.models.fields.TextField', [], {}),
            'total_cost': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'total_duration': ('django.db.models.fields.FloatField', [], {'default': '0'})
        }
    }

    complete_apps = ['djangosampler']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_sample_cre__add_field_query_cre__add_field_stack_cre
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Sample.created_dt'
        db.add_column('djangosampler_sample', 'created_dt', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now), keep_default=False)

        # Adding field 'Query.created_dt'
        db.add_column('djangosampler_query', 'created_dt', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now), keep_default=False)

        # Adding field 'Stack.created_dt'
        db.add_column('djangosampler_stack', 'created_dt', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Sample.created_dt'
        db.delete_column('djangosampler_sample', 'created_dt')

        # Deleting field 'Query.created_dt'
        db.delete_column('djangosampler_query', 'created_dt')

        # Deleting field 'Stack.created_dt'
        db.delete_column('djangosampler_stack', 'created_dt')


    models = {
        'djangosampler.query': {
            'Meta': {'object_name': 'Query'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created_dt': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'query_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'db_index': 'True'}),
            'total_cost': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'total_duration': ('django.db.models.fields.FloatField', [], {'default': '0'})
        },
        'djangosampler.sample': {
            'Meta': {'object_name': 'Sample'},
            'cost': ('django.db.models.fields.FloatField', [], {}),
            'created_dt': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'duration': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangosampler.Stack']"})
        },
        'djangosampler.stack': {
            'Meta': {'object_name': 'Stack'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created_dt': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'query': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangosampler.Query']"}),
            'stack': ('django.db.models.fields.TextField', [], {}),
            'total_cost': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'total_duration': ('django.db.models.fields.FloatField', [], {'default': '0'})
        }
    }

    complete_apps = ['djangosampler']

########NEW FILE########
__FILENAME__ = 0003_auto
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding index on 'Query', fields ['created_dt']
        db.create_index('djangosampler_query', ['created_dt'])


    def backwards(self, orm):
        
        # Removing index on 'Query', fields ['created_dt']
        db.delete_index('djangosampler_query', ['created_dt'])


    models = {
        'djangosampler.query': {
            'Meta': {'object_name': 'Query'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created_dt': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'query_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'db_index': 'True'}),
            'total_cost': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'total_duration': ('django.db.models.fields.FloatField', [], {'default': '0'})
        },
        'djangosampler.sample': {
            'Meta': {'object_name': 'Sample'},
            'cost': ('django.db.models.fields.FloatField', [], {}),
            'created_dt': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'duration': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangosampler.Stack']"})
        },
        'djangosampler.stack': {
            'Meta': {'object_name': 'Stack'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created_dt': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'query': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangosampler.Query']"}),
            'stack': ('django.db.models.fields.TextField', [], {}),
            'total_cost': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'total_duration': ('django.db.models.fields.FloatField', [], {'default': '0'})
        }
    }

    complete_apps = ['djangosampler']

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django.db import models


class Query(models.Model):
    """
    A query. This is the highest level of grouping.
    """
    hash = models.CharField(primary_key=True, max_length=32)
    query = models.TextField()
    total_duration = models.FloatField(default=0)
    total_cost = models.FloatField(default=0)
    count = models.IntegerField(default=0)
    query_type = models.CharField(db_index=True, max_length=32)
    created_dt = models.DateTimeField(
            default=datetime.now, editable=False, db_index=True)

    class Meta:
        verbose_name_plural = 'queries'

    def __unicode__(self):
        return self.hash

    def get_hash_for_date(self, hash_date):
        '''
        Gets a hash for the same query but on a different date.
        '''
        return hash((hash_date, self.query_type, self.query))

class Stack(models.Model):
    """
    A stack for a set of queries.
    """
    hash = models.CharField(primary_key=True, max_length=32)
    stack = models.TextField()
    total_duration = models.FloatField(default=0)
    total_cost = models.FloatField(default=0)
    count = models.IntegerField(default=0)
    query = models.ForeignKey('Query')
    created_dt = models.DateTimeField(default=datetime.now, editable=False)

    def last_stack_line(self):
        return self.stack.split('\n')[-1]

    def __unicode__(self):
        return self.hash


class Sample(models.Model):
    """
    A sampled query.
    """
    query = models.TextField()
    duration = models.FloatField()
    cost = models.FloatField()
    stack = models.ForeignKey('Stack')
    params = models.TextField()
    created_dt = models.DateTimeField(default=datetime.now, editable=False)

    @property
    def duration_ms(self):
        return self.duration * 1000.0

    def __unicode__(self):
        return unicode(self.created_dt)


########NEW FILE########
__FILENAME__ = celery_task
from time import time

from celery.signals import task_prerun, task_postrun

from djangosampler.sampler import should_sample, sample

task_start_times = {}

def task_prerun_handler(task_id, task, args, kwargs, **kwds):
    task_start_times[task_id] = time()

def task_postrun_handler(task_id, task, args, kwargs, retval, **kwds):
    duration = time() - task_start_times[task_id]
    del task_start_times[task_id]

    if not should_sample(duration):
        return

    sample('celery', str(task), duration, [args, kwargs])

class Celery(object):
    '''Plugin that hooks into Celery's signals to provide sampling of task
    duration.
    '''

    @staticmethod
    def install():
        task_prerun.connect(task_prerun_handler)
        task_postrun.connect(task_postrun_handler)


########NEW FILE########
__FILENAME__ = mongo
import time

from djangosampler.sampler import should_sample, sample

import pymongo

# Read preferences that are regarded as "slave reads"
slave_prefs = (pymongo.ReadPreference.SECONDARY_PREFERRED,
        pymongo.ReadPreference.SECONDARY)

class Mongo(object):
    '''Plugin that patches pyMongo to sample queries.
    '''
    @staticmethod
    def parameterise_dict(d):
        new_d = {}
        for k, v in d.items():
            if isinstance(v, dict):
                new_d[k] = Mongo.parameterise_dict(v)
            else:
                new_d[k] = '*'
        return new_d

    @staticmethod
    def get_insert_query(collection, *args, **kwargs):
        return '%s.insert(...)' % collection.name, 'mongo'

    @staticmethod
    def get_update_query(collection, spec, document, upsert=False, *args, **kwargs):
        safe_spec = Mongo.parameterise_dict(spec)
        update_method = upsert and 'upsert' or 'update'
        query = '%s.%s(%s)' % (collection.name, update_method, repr(safe_spec))
        return query, 'mongo'

    @staticmethod
    def get_remove_query(collection, spec_or_id, safe=False, **kwargs):
        if isinstance(spec_or_id, dict):
            safe_spec = Mongo.parameterise_dict(spec_or_id)
        else:
            safe_spec = { '_id': spec_or_id }

        return '%s.remove(%s)' % (collection.name, repr(safe_spec)), 'mongo'
    
    @staticmethod
    def privar(cursor, name):
        return getattr(cursor, '_Cursor__{0}'.format(name))

    @staticmethod
    def pre_refresh(cursor):
        cursor._is_getmore = Mongo.privar(cursor, 'id') is not None
        cursor._slave_okay = Mongo.privar(cursor, 'slave_okay')
        cursor._read_preference = Mongo.privar(cursor, 'read_preference')

    @staticmethod
    def get_refresh_query(cursor):
        query_son = Mongo.privar(cursor, 'query_spec')()

        # In db_name.collection_name format
        collection_name = Mongo.privar(cursor, 'collection').full_name 
        collection_name = collection_name.split('.')[1]

        query_spec = {}

        ordering = None
        if collection_name == '$cmd':
            command = 'command'
            # Handle count as a special case
            if 'count' in query_son:
                # Information is in a different format to a standard query
                collection_name = query_son['count']
                command = 'count'
                query_spec['query'] = query_son['query']
        else:
            # Normal Query
            if cursor._is_getmore:
                command = 'cursor_more'
            else:
                command = 'query'
            if '$query' in query_son:
                query_spec['query'] = query_son['$query']
            else:
                query_spec['query'] = query_son

            def fmt(field, direction):
                return '{0}{1}'.format({-1: '-', 1: '+'}[direction], field)

            if '$orderby' in query_son:
                ordering = ', '.join(fmt(f, d) 
                        for f, d in query_son['$orderby'].items())

        query_spec = Mongo.parameterise_dict(query_spec)
        if ordering:
            query_spec['ordering'] = ordering
        query_type = 'mongo'
        if cursor._slave_okay or cursor._read_preference in (slave_prefs):
            query_type = 'mongo slave'
        query = "%s.%s(%s)" % (collection_name, command, repr(query_spec))
        return query, query_type

    @staticmethod
    def make_wrapper(name, method):
        sampling_method = getattr(Mongo, 'get_%s_query' % name)
        pre_invoke = getattr(Mongo, 'pre_%s' % name, None)
        def sampler(*args, **kwargs):
            start = time.time()
            try:
                if pre_invoke:
                    pre_invoke(*args, **kwargs)
                return method(*args, **kwargs)
            finally:
                stop = time.time()
                if should_sample(stop - start):
                    query, query_type = sampling_method(*args, **kwargs)
                    if query:
                        sample(query_type, query, stop - start, [args, kwargs])

        return sampler

    @staticmethod
    def install():
        wrapped_methods = {
            'insert': pymongo.collection.Collection.insert,
            'update': pymongo.collection.Collection.update,
            'remove': pymongo.collection.Collection.remove,
            'refresh': pymongo.cursor.Cursor._refresh,
        }

        for name, method in wrapped_methods.items():
            setattr(
                method.im_class, 
                method.im_func.func_name, 
                Mongo.make_wrapper(name, method))

########NEW FILE########
__FILENAME__ = request
from time import time

from django.conf import settings

from djangosampler.sampler import should_sample, sample

class SamplingMiddleware(object):
    request_start_times = {}
    request_view_calls = {}

    def process_request(self, request):
        self.request_start_times[request] = time()

    def process_response(self, request, response):
        duration = time() - self.request_start_times.pop(request)
        
        view_fallback = {
            'function': request.path,
            'args': [],
            'kwargs': {},
        }
        view_call = self.request_view_calls.pop(request, view_fallback)

        if should_sample(duration):
            sample('request', 
                   view_call['function'], 
                   duration, 
                   [view_call['args'], view_call['kwargs']])

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        self.request_view_calls[request] = {
            'function': view_func.func_name,
            'args': view_args,
            'kwargs': view_kwargs,
        }
        return None


class Request(object):
    '''Plugin that uses Django's Request signals to provide sampling
    of requests.
    '''

    @staticmethod
    def install():
        settings.MIDDLEWARE_CLASSES = \
            ('djangosampler.plugins.request.SamplingMiddleware', ) + \
            tuple(settings.MIDDLEWARE_CLASSES)

########NEW FILE########
__FILENAME__ = sql
import json
from time import time

from django.db import connection

from djangosampler.sampler import should_sample, sample
from djangosampler.models import Sample

class Sql(object):
    '''Plugin that patches Django's cursors to use a sampling cursor.
    '''

    @staticmethod
    def install():
        from django.db.backends  import BaseDatabaseWrapper
        old_cursor = BaseDatabaseWrapper.cursor

        def cursor(self):
            new_cursor = old_cursor(self)
            return SamplingCursorWrapper(new_cursor, self)

        setattr(BaseDatabaseWrapper.cursor.im_class, 'cursor', cursor)

    @staticmethod
    def get_query_view_addons():
        return { 'sql': Sql.query_view_addon }

    @staticmethod
    def query_view_addon(query, stacks):
        sample_query = Sample.objects.filter(stack=stacks[0])[0]
        # Get an explain plain
        cursor = None
        explain = 'Unavailable'
        try:
            cursor = connection.cursor()
            raw_query = sample_query.query
            params = json.loads(sample_query.params)
            cursor.execute('EXPLAIN %s' % raw_query, params)
            explain = 'EXPLAIN %s\n\n' % (raw_query % tuple(params))
            row = cursor.fetchone()
            explain += "Select type:   %s\n" % row[1]
            explain += "Table:         %s\n" % row[2]
            explain += "Type:          %s\n" % row[3]
            explain += "Possible keys: %s\n" % row[4]
            explain += "Key:           %s\n" % row[5]
            explain += "Key length:    %s\n" % row[6]
            explain += "Ref:           %s\n" % row[7]
            explain += "Rows:          %s\n" % row[8]
            explain += "Extra:         %s\n" % row[9]

        except Exception:
            pass
        finally:
            if cursor:
                cursor.close()

        return """
            <h3>Example Explain</h3>
            <pre>%s</pre>
        """ % explain


class SamplingCursorWrapper(object):
    """A cursor wrapper that will sample a % of SQL queries.
    """
    def __init__(self, cursor, db):
        self.cursor = cursor
        self.db = db

    def log_sql(self, sql, time, params):
        if not should_sample(time):
            return
        sample('sql', sql, time, params)

    def execute(self, sql, params=()):
        start = time()
        try:
            return self.cursor.execute(sql, params)
        finally:
            stop = time()
            self.log_sql(sql, stop - start, params)

    def executemany(self, sql, param_list):
        start = time()
        try:
            return self.cursor.executemany(sql, param_list)
        finally:
            stop = time()
            self.log_sql(sql, stop - start, param_list)

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

    def __iter__(self):
        return iter(self.cursor)


########NEW FILE########
__FILENAME__ = sampler
from datetime import datetime
from time import time
import json
import random
import traceback

from django.conf import settings
from django.db.models import F
from django.db.utils import DatabaseError
from django.utils.encoding import force_unicode

from models import Query, Sample, Stack

USE_COST = getattr(settings, 'DJANGO_SAMPLER_USE_COST', False)
FREQ = float(getattr(settings, 'DJANGO_SAMPLER_FREQ', 0))
BASE_TIME = float(getattr(settings, 'DJANGO_SAMPLER_BASE_TIME', 0.005))

def _get_tidy_stacktrace():
    """Gets a tidy stacktrace. The tail of the stack is removed to exclude
    sampler internals. Will return a tuple of the stack printed cleanly and
    a boolean indicating whether the stack contains traces from the sampler
    itself (indicates the sampler being sampled).
    """
    stack = traceback.extract_stack()
    tidy_stack = []
    sampler_in_stack = False
    for trace in stack[:-3]:
        if 'djangosampler' in trace[0] and '/sampler.py' in trace[0]:
            sampler_in_stack = True

        tidy_stack.append("%s:%s (%s): %s" % trace)

    return "\n".join(tidy_stack), sampler_in_stack

def _calculate_bias(time):
    bias = time / BASE_TIME
    if FREQ * bias > 1:
        bias = 1 / FREQ
    return bias

def _calculate_cost(time):
    if USE_COST:
        bias = _calculate_bias(time)
        cost = time / bias
        return cost
    else:
        return 0.0

def _json_params(params):
    try:
        return json.dumps([force_unicode(x) for x in params])
    except TypeError:
        return ''

def should_sample(time):
    '''Determines if a sample should be taken. The probability of this will
    be multiplied by the time if cost-based sampling is enabled.
    '''
    if not FREQ:
        return False

    if USE_COST:
        bias = _calculate_bias(time)
        return random.random() > 1 - FREQ * bias
    else:
        return random.random() < FREQ


def drop_exceptions(fn):
    '''Decorator that makes the given method drop any exceptions that fall out of
    it. This is useful when doing sampling as it ensures that the sampler cannot
    cause a breakage.
    '''
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except:
            pass
    return wrapped

@drop_exceptions
def sample(query_type, query, time, params):
    '''Main method that records the given query.

    The params argument will be
    recorded alongside individual samples as a JSON object. It is a suitable
    place to store things like SQL parameters.
    '''
    stack, recursed = _get_tidy_stacktrace()
    if recursed:
        # Don't log the sampler being sampled
        return

    # The same stack may create different queries - so we have to include the
    # query in the stack hash to ensure that it is unique for every query
    date_now = datetime.now().date()
    stack_hash = hash((date_now, tuple(stack), query))

    query_hash = hash((date_now, query_type, query))
    try:
        query_model, _ = Query.objects.get_or_create(
                hash=query_hash, defaults={
                    'query_type': query_type, 'query': query
                })
    except DatabaseError:
        # This is likely because the database hasn't been created yet.
        # We can exit here - we don't want to cause the world to break
        return

    try:
        stack_model, _ = Stack.objects.get_or_create(
                hash=stack_hash,
                defaults={'stack': stack, 'query': query_model})
    except DatabaseError:
        # This is likely because the database hasn't been created yet.
        # We can exit here - we don't want to cause the world to break
        return

    cost = _calculate_cost(time)
    params = _json_params(params)

    try:
        Sample.objects.create(
                query=query, params=params, duration=time, cost=cost,
                stack=stack_model)
    except DatabaseError:
        # This is likely because the database hasn't been created yet.
        # We can exit here - we don't want to cause the world to break
        return

    # Update the stack total times
    Stack.objects.filter(hash=stack_hash).update(
            total_duration=F('total_duration') + time,
            total_cost=F('total_cost') + cost,
            count=F('count') + 1)

    # Update the query total times
    Query.objects.filter(hash=query_hash).update(
            total_duration=F('total_duration') + time,
            total_cost=F('total_cost') + cost,
            count=F('count') + 1)

class sampling:
    def __init__(self, sample_type, sample_key, params=()):
        self.sample_type = sample_type
        self.sample_key = sample_key
        self.params = params

    def __enter__(self):
        self.start_time = time()
        return self

    def __exit__(self, type, value, traceback):
        end_time = time()
        duration = end_time - self.start_time

        if should_sample(duration):
            sample(self.sample_type, self.sample_key, duration, self.params)

        return False

########NEW FILE########
__FILENAME__ = tests
from test_sampler import *
from test_plugins import *

########NEW FILE########
__FILENAME__ = test_plugins
from django.conf import settings
from django.test import TestCase

from plugins import install_plugins

class DummyPlugin(object):
    @staticmethod
    def install():
        DummyPlugin.install_called = True

    


class TestPlugins(TestCase):
    def setUp(self):
        DummyPlugin.install_called = False
        DummyPlugin.tag_trace_called = None

    def test_install_plugins(self):
        settings.DJANGO_SAMPLER_PLUGINS = ('djangosampler.test_plugins.DummyPlugin', )
        install_plugins()

        self.assertTrue(DummyPlugin.install_called)

########NEW FILE########
__FILENAME__ = test_sampler
from time import sleep

from django.conf import settings
from django.test import TestCase

import sampler
import models

class TestSampler(TestCase):
    def test_calculate_cost(self):
        settings.DJANGO_SAMPLER_USE_COST = None
        self.assertEquals(0.0, sampler._calculate_cost(1))

    def test_sample(self):
        settings.DJANGO_SAMPLER_USE_COST = True
        sampler.sample('sql', 'SELECT 1', 1, [])

        query = models.Query.objects.get()
        self.assertEquals('sql', query.query_type)
        self.assertEquals('SELECT 1', query.query)

class TestSamplingContextManager(TestCase):
    def test_with(self):
        sampler.FREQ = 1

        with sampler.sampling('bob', 'baz', ('foo', 'foobar')):
            sleep(0.01)

        query = models.Query.objects.get()
        self.assertEquals('bob', query.query_type)
        self.assertEquals('baz', query.query)
        self.assertTrue(query.total_duration >= 0.01)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns('',
    url(r'^queries/(?P<query_type>[\w ]+)/(?P<date_string>[-\w\d]+)/(?P<sort>(-|\w)+)/(?P<offset>\d+)/$', views.queries, name='queries'),
    url(r'^query/(?P<query_hash>[-0-9]+)/$', views.query, name='query'),

    url(r'^$', views.index, name='index'),
)

########NEW FILE########
__FILENAME__ = views
from datetime import datetime, timedelta
from math import ceil

from django.contrib.admin.views.decorators import staff_member_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from models import Query, Sample, Stack
from plugins import get_view_addons

PAGE_SIZE = 20


@staff_member_required
def queries(request, query_type, date_string, offset=0, sort='total_duration'):
    start_date = datetime.strptime(date_string, '%Y-%m-%d') 
    end_date = start_date + timedelta(days=1)

    start_offset = int(offset)
    query_qs = Query.objects.filter(query_type=query_type,
            created_dt__gte=start_date, created_dt__lt=end_date)

    total_queries = query_qs.count()
    queries = query_qs.order_by(sort)
    queries = queries.reverse()
    queries = queries[start_offset:start_offset+PAGE_SIZE]
    queries = list(queries)
    end_offset = start_offset + len(queries)

    for query in queries:
        query.url = reverse('query', kwargs={'query_hash': query.hash})

    current_page = 1 + start_offset / PAGE_SIZE
    max_pages = int(ceil(total_queries / float(PAGE_SIZE)))
    pages = xrange(max(1, current_page - 5), 1 + min(max_pages, current_page + 5))

    pages = list([{ 
            'number': page, 
            'url': reverse('queries', kwargs={
                'date_string': date_string,
                'query_type': query_type,
                'offset': PAGE_SIZE * (page - 1), 
                'sort': sort
            })
        }
        for page in pages
    ])

    def get_sort_url(field):
        if field == sort:
            field = '-%s' % field
        return reverse('queries', kwargs={
            'date_string': date_string,
            'query_type': query_type,
            'offset': 0, 
            'sort': field
        })

    by_count_url = get_sort_url('count')
    by_duration_url = get_sort_url('total_duration')
    by_cost_url = get_sort_url('total_cost')

    query_types = _get_query_types(date_string)
    date_links = _get_date_links(start_date, query_type)

    return render_to_response('djangosampler/queries.html', 
            {
                'by_count_url': by_count_url,
                'by_duration_url': by_duration_url,
                'by_cost_url': by_cost_url,
                'query_types': query_types,
                'start_offset': start_offset,
                'end_offset': end_offset,
                'total_queries': total_queries,
                'pages': pages,
                'current_page': current_page,
                'queries': queries,
                'date_links': date_links,
                'current_date': date_string,
                'current_query_type': query_type,
            },
            context_instance=RequestContext(request))

@staff_member_required
def query(request, query_hash):
    query = Query.objects.get(hash=query_hash)

    stacks = Stack.objects.filter(query=query)
    stacks = stacks.order_by('-total_cost')
    stacks = list(stacks)

    sample = Sample.objects.filter(stack=stacks[0])[0]

    extra = ""
    for addon in get_view_addons(query.query_type):
        extra += addon(query, stacks)

    recent_queries = []
    start_date = query.created_dt.date()
    for day in xrange(-7, 7):
        recent_date = start_date + timedelta(days=day)
        recent_query_hash = query.get_hash_for_date(recent_date)
        try:
            recent_query = Query.objects.get(hash=recent_query_hash)
        except Query.DoesNotExist:
            recent_query = None
        recent_queries.append((recent_date, recent_query))


    date_string = query.created_dt.strftime('%Y-%m-%d')
    back_link = reverse('queries',
        kwargs={
            'date_string': date_string,
            'query_type': query.query_type, 
            'sort': 'total_duration', 
            'offset': 0
    })

    return render_to_response('djangosampler/query.html', 
            locals(),
            context_instance=RequestContext(request))

@staff_member_required
def index(request):
    current_date = datetime.now().strftime('%Y-%m-%d')
    query_types = _get_query_types(current_date)
    # don't fail if this is the first time things have been run
    query_type = query_types[0]['name'] if query_types else None
    return HttpResponseRedirect(reverse('queries',
        kwargs={
            'date_string': current_date,
            'query_type': query_type, 
            'sort': 'total_duration', 
            'offset': 0
    }))

def _get_query_types(date_string):

    query_type_names = Query.objects.values_list('query_type', flat=True).distinct()
    query_objs = []
    for query_type in query_type_names:
        query_obj = {}
        query_obj['name'] = query_type
        query_obj['friendly_name'] = query_type.capitalize()
        query_obj['url'] = reverse('queries',
            kwargs={
                'date_string': date_string,
                'query_type': query_type,
                'sort': 'total_duration', 
                'offset': 0
        })
        query_objs.append(query_obj)
    return query_objs


def _get_date_links(current_date, query_type):
    # Want full week before and after the current date
    date_links = []
    for day in xrange(-7, 8):
        date_value = current_date + timedelta(days=day)
        date_link = {}
        date_link['friendly_name'] = date_value.strftime('%Y-%m-%d')
        date_link['url'] = reverse('queries',
            kwargs={
                'date_string': date_link['friendly_name'],
                'query_type': query_type,
                'sort': 'total_duration', 
                'offset': 0
        })
        date_links.append(date_link)

    return date_links



########NEW FILE########
__FILENAME__ = run_tests
# Script lovingly influenced by the Pinax test running script
import optparse
import os
import sys

from django.conf import settings
from django.core.management import call_command

def setup_test_environment():
    os.environ['PYTHONPATH'] = os.path.abspath(__file__)
    
    settings.configure(**{
        "DATABASES": {
            "default": {
                "ENGINE": "sqlite3",
            },
        },
        "INSTALLED_APPS": ("djangosampler", ),
    })


def main():
    
    usage = "%prog [options]"
    parser = optparse.OptionParser(usage=usage)
    
    parser.add_option("-v", "--verbosity",
        action = "store",
        dest = "verbosity",
        default = "0",
        type = "choice",
        choices = ["0", "1", "2"],
        help = "verbosity level; 0=minimal output, 1=normal output, 2=all output",
    )
    parser.add_option("--coverage",
        action = "store_true",
        dest = "coverage",
        default = False,
        help = "hook in coverage during test suite run and save out results",
    )
    
    options, _ = parser.parse_args()
    
    if options.coverage:
        try:
            import coverage
        except ImportError:
            sys.stderr.write("coverage is not installed.\n")
            sys.exit(1)
        else:
            cov = coverage.coverage(auto_data=True)
            cov.start()
    else:
        cov = None
    
    setup_test_environment()
    
    call_command("test", verbosity=int(options.verbosity))
    
    if cov:
        cov.stop()
        cov.save()


if __name__ == "__main__":
    main()

########NEW FILE########
