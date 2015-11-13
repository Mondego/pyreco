__FILENAME__ = operation_tracker
import functools
import time
import inspect
import os
import SocketServer

import django
from django.conf import settings

import pymongo
import pymongo.collection
import pymongo.cursor

__all__ = ['queries', 'inserts', 'updates', 'removes', 'install_tracker',
           'uninstall_tracker', 'reset']


_original_methods = {
    'insert': pymongo.collection.Collection.insert,
    'update': pymongo.collection.Collection.update,
    'remove': pymongo.collection.Collection.remove,
    'refresh': pymongo.cursor.Cursor._refresh,
}

queries = []
inserts = []
updates = []
removes = []

WANT_STACK_TRACE = getattr(settings, 'DEBUG_TOOLBAR_MONGO_STACKTRACES', True)
def _get_stacktrace():
    if WANT_STACK_TRACE:
        try:
            stack = inspect.stack()
        except IndexError:
            # this is a work around because python's inspect.stack() sometimes fail
            # when jinja templates are on the stack
            return [(
                "",
                0,
                "Error retrieving stack",
                "Could not retrieve stack. IndexError exception occured in inspect.stack(). "
                "This error might occur when jinja2 templates is on the stack.",
            )]

        return _tidy_stacktrace(reversed(stack))
    else:
        return []


# Wrap Cursor._refresh for getting queries
@functools.wraps(_original_methods['insert'])
def _insert(collection_self, doc_or_docs, manipulate=True,
           safe=False, check_keys=True, **kwargs):
    start_time = time.time()
    result = _original_methods['insert'](
        collection_self,
        doc_or_docs,
        manipulate=manipulate,
        safe=safe,
        check_keys=check_keys,
        **kwargs
    )
    total_time = (time.time() - start_time) * 1000

    __traceback_hide__ = True
    inserts.append({
        'document': doc_or_docs,
        'safe': safe,
        'time': total_time,
        'stack_trace': _get_stacktrace(),
    })
    return result

# Wrap Cursor._refresh for getting queries
@functools.wraps(_original_methods['update'])
def _update(collection_self, spec, document, upsert=False,
           maniuplate=False, safe=False, multi=False, **kwargs):
    start_time = time.time()
    result = _original_methods['update'](
        collection_self,
        spec,
        document,
        upsert=upsert,
        safe=safe,
        multi=multi,
        **kwargs
    )
    total_time = (time.time() - start_time) * 1000

    __traceback_hide__ = True
    updates.append({
        'document': document,
        'upsert': upsert,
        'multi': multi,
        'spec': spec,
        'safe': safe,
        'time': total_time,
        'stack_trace': _get_stacktrace(),
    })
    return result

# Wrap Cursor._refresh for getting queries
@functools.wraps(_original_methods['remove'])
def _remove(collection_self, spec_or_id, safe=False, **kwargs):
    start_time = time.time()
    result = _original_methods['remove'](
        collection_self,
        spec_or_id,
        safe=safe,
        **kwargs
    )
    total_time = (time.time() - start_time) * 1000

    __traceback_hide__ = True
    removes.append({
        'spec_or_id': spec_or_id,
        'safe': safe,
        'time': total_time,
        'stack_trace': _get_stacktrace(),
    })
    return result

# Wrap Cursor._refresh for getting queries
@functools.wraps(_original_methods['refresh'])
def _cursor_refresh(cursor_self):
    # Look up __ private instance variables
    def privar(name):
        return getattr(cursor_self, '_Cursor__{0}'.format(name))

    # NOTE: See pymongo/cursor.py+557 [_refresh()] and
    # pymongo/message.py for where information is stored

    is_getmore = privar('id') is not None
    # Time the actual query
    start_time = time.time()
    result = _original_methods['refresh'](cursor_self)
    total_time = (time.time() - start_time) * 1000

    query_son = privar('query_spec')()

    __traceback_hide__ = True
    query_data = {
        'time': total_time,
        'operation': 'find',
        'stack_trace': _get_stacktrace(),
    }

    if is_getmore:
        # getMore not query - move on
        query_data['cursor'] = id(cursor_self)
        query_data['operation'] = 'getmore'
        queries.append(query_data)
        return result

    # Collection in format <db_name>.<collection_name>
    collection_name = privar('collection')
    query_data['collection'] = collection_name.full_name.split('.')[1]

    if query_data['collection'] == '$cmd':
        # The query can be embedded within $query in some cases
        query_son = query_son.get("$query", query_son)

        query_data['operation'] = 'command'
        # Handle count as a special case
        if 'count' in query_son:
            # Information is in a different format to a standar query
            query_data['collection'] = query_son['count']
            query_data['operation'] = 'count'
            query_data['skip'] = query_son.get('skip')
            query_data['limit'] = abs(query_son.get('limit', 0))
            query_data['query'] = query_son['query']
        elif 'aggregate' in query_son:
            query_data['collection'] = query_son['aggregate']
            query_data['operation'] = 'aggregate'
            query_data['query'] = query_son['pipeline']
            query_data['skip'] = 0
            query_data['limit'] = None
    else:
        # Normal Query
        query_data['skip'] = privar('skip')
        query_data['limit'] = abs(privar('limit') or 0)
        query_data['query'] = query_son.get('$query') or query_son
        query_data['ordering'] = _get_ordering(query_son)
        query_data['cursor'] = id(cursor_self)

    queries.append(query_data)

    return result

def install_tracker():
    if pymongo.collection.Collection.insert != _insert:
        pymongo.collection.Collection.insert = _insert
    if pymongo.collection.Collection.update != _update:
        pymongo.collection.Collection.update = _update
    if pymongo.collection.Collection.remove != _remove:
        pymongo.collection.Collection.remove = _remove
    if pymongo.cursor.Cursor._refresh != _cursor_refresh:
        pymongo.cursor.Cursor._refresh = _cursor_refresh

def uninstall_tracker():
    if pymongo.collection.Collection.insert == _insert:
        pymongo.collection.Collection.insert = _original_methods['insert']
    if pymongo.collection.Collection.update == _update:
        pymongo.collection.Collection.update = _original_methods['update']
    if pymongo.collection.Collection.remove == _remove:
        pymongo.collection.Collection.remove = _original_methods['remove']
    if pymongo.cursor.Cursor._refresh == _cursor_refresh:
        pymongo.cursor.Cursor._refresh = _original_methods['cursor_refresh']

def reset():
    global queries, inserts, updates, removes
    queries = []
    inserts = []
    updates = []
    removes = []

def _get_ordering(son):
    """Helper function to extract formatted ordering from dict.
    """
    def fmt(field, direction):
        return '{0}{1}'.format({-1: '-', 1: '+'}[direction], field)

    if '$orderby' in son:
        return ', '.join(fmt(f, d) for f, d in son['$orderby'].items())

# Taken from Django Debug Toolbar 0.8.6
def _tidy_stacktrace(stack):
    """
    Clean up stacktrace and remove all entries that:
    1. Are part of Django (except contrib apps)
    2. Are part of SocketServer (used by Django's dev server)
    3. Are the last entry (which is part of our stacktracing code)

    ``stack`` should be a list of frame tuples from ``inspect.stack()``
    """
    django_path = os.path.realpath(os.path.dirname(django.__file__))
    django_path = os.path.normpath(os.path.join(django_path, '..'))
    socketserver_path = os.path.realpath(os.path.dirname(SocketServer.__file__))
    pymongo_path = os.path.realpath(os.path.dirname(pymongo.__file__))

    trace = []
    for frame, path, line_no, func_name, text in (f[:5] for f in stack):
        s_path = os.path.realpath(path)
        # Support hiding of frames -- used in various utilities that provide
        # inspection.
        if '__traceback_hide__' in frame.f_locals:
            continue
        if getattr(settings, 'DEBUG_TOOLBAR_CONFIG', {}).get('HIDE_DJANGO_SQL', True) \
            and django_path in s_path and not 'django/contrib' in s_path:
            continue
        if socketserver_path in s_path:
            continue
        if pymongo_path in s_path:
            continue
        if not text:
            text = ''
        else:
            text = (''.join(text)).strip()
        trace.append((path, line_no, func_name, text))
    return trace


########NEW FILE########
__FILENAME__ = panel
from django.template import Template, Context
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from debug_toolbar.panels import DebugPanel

import operation_tracker

_NAV_SUBTITLE_TPL = u'''
{% for o, n, t in operations %}
    {{ n }} {{ o }}{{ n|pluralize }} in {{ t }}ms<br/>

    {% if forloop.last and forloop.counter0 %}
        {{ count }} operation{{ count|pluralize }} in {{ time }}ms
    {% endif %}
{% endfor %}
'''

class MongoDebugPanel(DebugPanel):
    """Panel that shows information about MongoDB operations.
    """
    name = 'MongoDB'
    has_content = True

    def __init__(self, *args, **kwargs):
        super(MongoDebugPanel, self).__init__(*args, **kwargs)
        operation_tracker.install_tracker()

    def process_request(self, request):
        operation_tracker.reset()

    def nav_title(self):
        return 'MongoDB'

    def nav_subtitle(self):
        fun = lambda x, y: (x, len(y), '%.2f' % sum(z['time'] for z in y))
        ctx = {'operations': [], 'count': 0, 'time': 0}

        if operation_tracker.queries:
            ctx['operations'].append(fun('read', operation_tracker.queries))
            ctx['count'] += len(operation_tracker.queries)
            ctx['time'] += sum(x['time'] for x in operation_tracker.queries)

        if operation_tracker.inserts:
            ctx['operations'].append(fun('insert', operation_tracker.inserts))
            ctx['count'] += len(operation_tracker.inserts)
            ctx['time'] += sum(x['time'] for x in operation_tracker.inserts)

        if operation_tracker.updates:
            ctx['operations'].append(fun('update', operation_tracker.updates))
            ctx['count'] += len(operation_tracker.updates)
            ctx['time'] += sum(x['time'] for x in operation_tracker.updates)

        if operation_tracker.removes:
            ctx['operations'].append(fun('remove', operation_tracker.removes))
            ctx['count'] += len(operation_tracker.removes)
            ctx['time'] += sum(x['time'] for x in operation_tracker.removes)

        ctx['time'] = '%.2f' % ctx['time']

        return mark_safe(Template(_NAV_SUBTITLE_TPL).render(Context(ctx)))

    def title(self):
        return 'MongoDB Operations'

    def url(self):
        return ''

    def content(self):
        context = self.context.copy()
        context['queries'] = operation_tracker.queries
        context['inserts'] = operation_tracker.inserts
        context['updates'] = operation_tracker.updates
        context['removes'] = operation_tracker.removes
        return render_to_string('mongo-panel.html', context)



########NEW FILE########
__FILENAME__ = mongo_debug_tags
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

import pprint
import os

register = template.Library()

@register.filter
def format_stack_trace(value):
    stack_trace = []
    fmt = (
        '<span class="path">{0}/</span>'
        '<span class="file">{1}</span> in <span class="func">{3}</span>'
        '(<span class="lineno">{2}</span>) <span class="code">{4}</span>'
    )
    for frame in value:
        params = map(escape, frame[0].rsplit('/', 1) + list(frame[1:]))
        stack_trace.append(fmt.format(*params))
    return mark_safe('\n'.join(stack_trace))

@register.filter
def embolden_file(path):
    head, tail = os.path.split(escape(path))
    return mark_safe(os.sep.join([head, '<strong>{0}</strong>'.format(tail)]))

@register.filter
def format_dict(value, width=60):
    return pprint.pformat(value, width=int(width))

@register.filter
def highlight(value, language):
    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import HtmlFormatter
    except ImportError:
        return value
    # Can't use class-based colouring because the debug toolbar's css rules
    # are more specific so take precedence
    formatter = HtmlFormatter(style='friendly', nowrap=True, noclasses=True)
    return highlight(value, get_lexer_by_name(language), formatter)

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

import sys
sys.path.insert(0, '..')

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
import os

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'example.db',
    }
}

SECRET_KEY = 'u=0tir)ob&3%uw3h4&&$%!!kffw$h*!_ia46f)qz%2rxnkhak&'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates'),
)

INSTALLED_APPS = (
    'debug_toolbar',
    'debug_toolbar_mongo',
)

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar_mongo.panel.MongoDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
)

ROOT_URLCONF = 'example.urls'

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: True,
}

INTERNAL_IPS = ('127.0.0.1',)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'views.index', name='index'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response

import pymongo

conn = pymongo.Connection()
db = conn.debug_test

def index(request):
    #list(db.test.find({'name': 'test'}))
    db.test.find({'name': 'test'}).count()
    db.test.find({'name': 'test'}).count()
    list(db.test.find({'name': 'test', 'age': {'$lt': 134234}}).skip(1))
    db.test.find({'name': 'test'}).count()
    db.test.find({'name': 'test'}).skip(1).count(with_limit_and_skip=True)
    list(db.test.find({'name': 'test'}).sort('name'))
    sort_fields = [('name', pymongo.DESCENDING), ('date', pymongo.ASCENDING)]
    list(db.test.find({'name': 'test'}).sort(sort_fields))
    list(db.test.find({
        '$or': [
            {
                'age': {'$lt': 50, '$gt': 18},
                'paying': True,
            },
            {
                'name': 'King of the world',
                'paying': False,
            }
        ]
    }))
    db.test.insert({'name': 'test'})
    db.test.insert({'name': 'test2'}, safe=True)
    db.test.update({'name': 'test2'}, {'age': 1}, upsert=True)
    db.test.remove({'name': 'test1'})
    return render_to_response('index.html')


########NEW FILE########
