__FILENAME__ = client
import threading

import zmq 

class _RemoteMethod:
    def __init__(self, socket, name):
        self.socket = socket
        self.name = name

    def __call__(self, *args, **kwargs):
        self.socket.send_pyobj((self.name, args, kwargs))
        return self.socket.recv_pyobj()

class Aggregator(object):
    def __init__(self):
        self.context = zmq.Context()
        self.data_socket = self.context.socket(zmq.PUB)
        self.data_socket.connect ("tcp://localhost:5556")
        self.control_socket = self.context.socket(zmq.REQ)
        self.control_socket.connect("tcp://localhost:5557")
    
    def insert(self, tags, values):
        self.insert_all([(tags, values)])
        
    def insert_all(self, items):
        self.data_socket.send_pyobj(items)
        
        
    def __getattr__(self, name):
        return _RemoteMethod(self.control_socket, name)
    
    def ping(self):
        self.data_socket.send_pyobj(None)


_local = threading.local()

def get_client():
    try:
        return _local.aggregator
    except AttributeError:
        _local.aggregator = Aggregator()
        return _local.aggregator

########NEW FILE########
__FILENAME__ = server
#!/bin/env python
import argparse
from threading import Thread

import zmq
from zmq.eventloop import ioloop

class Aggregator(object):
    def __init__(self):
        self.data = {}

    
    def insert(self, tags, values):
        key = frozenset(tags.items())
        try:
            rec = self.data[key]
        except KeyError:
            rec = self.data[key] = values.copy()
        else:
            for i, v in values.iteritems():
                rec[i] += v

        

    def select(self, group_by=[], where={}):
        if not group_by and not where:
            return [dict(list(k)+v.items()) for k,v in self.data.iteritems()]
        a = Aggregator()
        for k, v in self.data.iteritems():
            matched = 0
            for key_k, key_v in k:
                try:
                    if where[key_k] == key_v:
                        matched += 1
                    else:
                        break
                except KeyError:
                    pass
            if matched < len(where):
                continue
            a.insert(dict((kk, vv) for kk,vv in k if kk in group_by),
                     v)
        return a.select()

    def clear(self):
        self.data = {}


def ctl(aggregator):
    context = zmq.Context.instance()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5557")
    while True:
        cmd, args, kwargs = socket.recv_pyobj()
        ret = getattr(aggregator, cmd)(*args, **kwargs)
        socket.send_pyobj(ret)

def main():
    parser = argparse.ArgumentParser(description='Run aggregation daemon')
    parser.add_argument('--host', dest='host', action='store',
                        default='127.0.0.1',
                        help='The IP address/hostname to listen on')
    parser.add_argument('--port', dest='port', action='store', type=int,
                        default='5556',
                        help='The port to listen on')
    


    args = parser.parse_args()
    context = zmq.Context.instance()
    socket = context.socket(zmq.SUB)
    socket.bind("tcp://%s:%d"%(args.host, args.port))
    socket.setsockopt(zmq.SUBSCRIBE,'')
    a = Aggregator()
    statthread = Thread(target=ctl, args=(a,))
    statthread.daemon = True
    statthread.start()
        
    while True:
        q = socket.recv_pyobj()
        for l in q:
            a.insert(*l)
            

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = instrument
from datetime import datetime

from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.datastructures import EmptyResultSet
from django.db.models.sql.constants import MULTI
from django.db import connection

from aggregate.client import get_client

from profiler import _get_current_view

def execute_sql(self, *args, **kwargs):
    client = get_client()
    if client is None:
        return self.__execute_sql(*args, **kwargs)
    try:
        q, params = self.as_sql()
        if not q:
            raise EmptyResultSet
    except EmptyResultSet:
        if kwargs.get('result_type', MULTI) == MULTI:
            return iter([])
        else:
            return
    start = datetime.now()
    try:
        return self.__execute_sql(*args, **kwargs)
    finally:
        d = (datetime.now() - start)
        client.insert({'query' : q, 'view' : _get_current_view(), 'type' : 'sql'},
                      {'time' : 0.0 + d.seconds * 1000 + d.microseconds/1000, 'count' : 1})

INSTRUMENTED = False



if not INSTRUMENTED:
    SQLCompiler.__execute_sql = SQLCompiler.execute_sql
    SQLCompiler.execute_sql = execute_sql
    INSTRUMENTED = True

########NEW FILE########
__FILENAME__ = middleware
from datetime import datetime
import inspect

import statprof

from django.db import connection
from django.core.cache import cache
from django.conf import settings


from aggregate.client import get_client

from profiler import _set_current_view

class ProfilerMiddleware(object):

    def process_view(self, request, view_func, view_args, view_kwargs):
        if inspect.ismethod(view_func):
            view_name = view_func.im_class.__module__+ '.' + view_func.im_class.__name__ + view_func.__name__
        else:
            view_name = view_func.__module__ + '.' + view_func.__name__
        
        _set_current_view(view_name)

    
    def process_response(self, request, response):
        _set_current_view(None)
        return response


class StatProfMiddleware(object):

    def process_request(self, request):
        statprof.reset(getattr(settings, 'LIVEPROFILER_STATPROF_FREQUENCY', 100))
        statprof.start()
    
    def process_response(self, request, response):
        statprof.stop()
        client = get_client()
        total_samples = statprof.state.sample_count
        if total_samples == 0:
            return response
        secs_per_sample = statprof.state.accumulated_time / total_samples

        client.insert_all([(
                    {'file' : c.key.filename,
                     'lineno' : c.key.lineno,
                     'function' : c.key.name,
                     'type' : 'python'},
                    {'self_nsamples' : c.self_sample_count,
                     'cum_nsamples' : c.cum_sample_count,
                     'tot_nsamples' : total_samples,
                     'cum_time' : c.cum_sample_count * secs_per_sample,
                     'self_time' : c.self_sample_count * secs_per_sample
                     })
                           for c in statprof.CallData.all_calls.itervalues()])



        return response

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

from profiler.instrument import *

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns(
    'profiler.views',
    url(r'^$', 'global_stats', name='profiler_global_stats'),
    url(r'^by_view/$', 'stats_by_view', name='profiler_stats_by_view'),
    url(r'^code/$', 'python_stats', name='profiler_python_stats'),
    url(r'^reset/$', 'reset', name='profiler_reset'),
    )


########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.core.cache import cache
from django.contrib.auth.decorators import user_passes_test
from django.core.urlresolvers import reverse
from django.utils import simplejson

from aggregate.client import get_client

@user_passes_test(lambda u:u.is_superuser)
def global_stats(request):
    stats = get_client().select(group_by=['query'], where={'type':'sql'})
    for s in stats:
        s['average_time'] = s['time'] / s['count']
    return render_to_response('profiler/index.html',
                              {'queries' : stats},
                              context_instance=RequestContext(request))

@user_passes_test(lambda u:u.is_superuser)
def stats_by_view(request):
    stats = get_client().select(group_by=['view','query'], where={'type':'sql'})
    grouped = {}
    for r in stats:
        if r['view'] not in grouped:
            grouped[r['view']] = {'queries' : [], 
                                  'count' : 0,
                                  'time' : 0,
                                  'average_time' : 0}
        grouped[r['view']]['queries'].append(r)
        grouped[r['view']]['count'] += r['count']
        grouped[r['view']]['time'] += r['time']
        r['average_time'] = r['time'] / r['count'] 
        grouped[r['view']]['average_time'] += r['average_time']
        
    maxtime = 0
    for r in stats:
        if r['average_time'] > maxtime:
            maxtime = r['average_time']
    for r in stats:
        r['normtime'] = (0.0+r['average_time'])/maxtime
           
    return render_to_response('profiler/by_view.html',
                              {'queries' : grouped,
                               'stats' :simplejson.dumps(stats)},
                              context_instance=RequestContext(request))

@user_passes_test(lambda u:u.is_superuser)
def reset(request):
    next = request.GET.get('next') or request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('profiler_global_stats')
    if request.method == 'POST':
        get_client().clear()
        return HttpResponseRedirect(next)
    return render_to_response('profiler/reset.html',
                              {'next' : next},
                              context_instance=RequestContext(request))



@user_passes_test(lambda u:u.is_superuser)
def python_stats(request):
    stats = get_client().select(group_by=['file','lineno'], where={'type':'python'})
    return render_to_response('profiler/code.html',
                              {'stats' : stats},
                              context_instance=RequestContext(request))

########NEW FILE########
