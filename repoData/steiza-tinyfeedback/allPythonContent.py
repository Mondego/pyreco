__FILENAME__ = helper
import platform
import subprocess
import time
import urllib
from twisted.web.client import getPage


PORT = 8000
HOST = '127.0.0.1'


def send_once(component, data_dict):
    url = 'http://%s:%s/data/%s' % (HOST, PORT, component)

    try:
        urllib.urlopen(url, data=urllib.urlencode(data_dict))

    except IOError:
        # Failed to send, just keep going
        pass


def send_once_using_twisted(component, data_dict):
    url = 'http://%s:%s/data/%s' % (HOST, PORT, component)

    d = getPage(
            str(url),
            method='POST',
            postdata=urllib.urlencode(data_dict),
            headers={'Content-Type':'application/x-www-form-urlencoded'},
            timeout=10,
            )

    # swallow errors
    d.addErrback(lambda x: None)


def tail_monitor(component, log_filename, line_callback_func, data_arg={},
        format_data_callback_func=None, interval=60):

    url = 'http://%s:%s/data/%s' % (HOST, PORT, component)

    initial_data = data_arg
    current_data = data_arg.copy()

    if is_osx():
        arguments = '-F'
    else:
        arguments = '--follow=name'

    tail_process = subprocess.Popen(['tail', arguments, log_filename],
            stdout=subprocess.PIPE)

    last_update = time.time()

    while True:
        line = tail_process.stdout.readline()

        if line.strip() == '':
            time.sleep(1)
        else:
            line_callback_func(current_data, line)

        current_time = time.time()

        if current_time - last_update >= interval:
            last_update = current_time

            if format_data_callback_func:
                current_data = format_data_callback_func(current_data)

            # Don't send empty data
            if current_data != {}:
                try:
                    urllib.urlopen(url, data=urllib.urlencode(current_data))

                except IOError:
                    # Failed to send, just keep going
                    pass

                current_data = initial_data.copy()


def is_osx():
    return (platform.system() == 'Darwin')

########NEW FILE########
__FILENAME__ = redis_model
import re
import time

import simplejson
from twisted.internet import defer, protocol, reactor
import txredisapi


class Graph(object):
    '''
    tinyfeedback:usernames - all the usernames we know about
    tinyfeedback:graph:<username>:all_graphs - dictionary of graphs by title
    '''

    def __init__(self, host):
        self.__host = host

    @defer.inlineCallbacks
    def connect(self, poolsize=None):
        if not poolsize:
            poolsize = 10

        self.__redis = yield txredisapi.ConnectionPool(self.__host, poolsize=poolsize)

    @defer.inlineCallbacks
    def add_username(self, username):
        key = 'tinyfeedback:usernames'
        yield self.__redis.sadd(key, username)

    @defer.inlineCallbacks
    def remove_username(self, username):
        key = 'tinyfeedback:usernames'
        yield self.__redis.srem(key, username)

    @defer.inlineCallbacks
    def get_graphs_per_user(self):
        user_key = 'tinyfeedback:usernames'
        usernames = yield self.__redis.smembers(user_key)

        keys = ['tinyfeedback:graph:%s:all_graphs' % each_username for \
                each_username in usernames]

        user_graphs = yield self.__redis.mget(keys)

        graphs_per_user = []
        for i, each_username in enumerate(usernames):
            if not user_graphs[i]:
                num_graphs = 0
            else:
                num_graphs = len(simplejson.loads(user_graphs[i]))

            graphs_per_user.append((each_username, num_graphs))

        # Sort usernames by the number of graphs they have
        graphs_per_user.sort(cmp=lambda x, y: y[1] - x[1])

        defer.returnValue(graphs_per_user)

    @defer.inlineCallbacks
    def get_graphs(self, username):
        key = 'tinyfeedback:graph:%s:all_graphs' % username

        graphs = yield self.__redis.get(key)

        if not graphs:
            defer.returnValue({})

        else:
            defer.returnValue(simplejson.loads(graphs))

    @defer.inlineCallbacks
    def remove_graph(self, username, title):
        key = 'tinyfeedback:graph:%s:all_graphs' % username

        while True:
            try:
                transaction = yield self.__redis.multi(key)

                graphs = yield self.__redis.get(key)

                if graphs:
                    graphs = simplejson.loads(graphs)

                if not graphs or title not in graphs:
                    yield transaction.discard()
                    break

                removed_ordering = graphs[title]['ordering']

                del graphs[title]

                # Reorder the remaining graphs
                for each in graphs.itervalues():
                    if each['ordering'] > removed_ordering:
                        each['ordering'] -= 1

                yield transaction.set(key, simplejson.dumps(graphs))

                yield transaction.commit()
                break

            except txredisapi.WatchError:
                continue

    @defer.inlineCallbacks
    def update_graph(self, username, title, timescale, fields, graph_type):
        key = 'tinyfeedback:graph:%s:all_graphs' % username

        fields.sort()

        while True:
            try:
                transaction = yield self.__redis.multi(key)

                graphs = yield self.__redis.get(key)

                if not graphs:
                    graphs = {}
                else:
                    graphs = simplejson.loads(graphs)

                if title not in graphs:
                    # Find the next ordering
                    if len(graphs) == 0:
                        max_ordering = 0
                    elif len(graphs) == 1:
                        max_ordering = graphs.values()[0]['ordering'] + 1
                    else:
                        max_ordering = max( [each['ordering'] for each in \
                                graphs.itervalues()] ) + 1

                    graphs[title] = {'ordering': max_ordering}

                graphs[title]['timescale'] = timescale
                graphs[title]['fields'] = fields
                graphs[title]['graph_type'] = graph_type

                yield transaction.set(key, simplejson.dumps(graphs))

                yield transaction.commit()
                break

            except txredisapi.WatchError:
                continue

    @defer.inlineCallbacks
    def update_ordering(self, username, new_ordering):
        key = 'tinyfeedback:graph:%s:all_graphs' % username

        while True:
            try:
                transaction = yield self.__redis.multi(key)

                graphs = yield self.__redis.get(key)

                if not graphs:
                    graphs = {}
                else:
                    graphs = simplejson.loads(graphs)

                for index, title in enumerate(new_ordering):
                    if title in graphs:
                        graphs[title]['ordering'] = index

                yield transaction.set(key, simplejson.dumps(graphs))

                yield transaction.commit()
                break

            except txredisapi.WatchError:
                continue


class Data(object):
    '''
    tinyfeedback:data:list_components - all components
    tinyfeedback:data:component:<component>:list_metrics - all metrics for a component
    tinyfeedback:data:component:<component>:metric:<metric>:<timescale> - data
    '''

    def __init__(self, host):
        self.__host = host
        self.__update_metric_limit = defer.DeferredSemaphore(25)

    @defer.inlineCallbacks
    def connect(self, poolsize=None):
        if not poolsize:
            poolsize = 100

        self.__redis = yield txredisapi.ConnectionPool(self.__host, poolsize=poolsize)

    @defer.inlineCallbacks
    def get_components(self):
        components = yield self.__redis.get('tinyfeedback:data:list_components')

        if not components:
            defer.returnValue([])
        else:
            defer.returnValue(simplejson.loads(components))

    @defer.inlineCallbacks
    def delete_metrics_older_than_a_week(self, component):
        keys = ['tinyfeedback:data:list_components',
                'tinyfeedback:data:component:%s:list_metrics' % component,
                ]

        while True:
            try:
                transaction = yield self.__redis.multi(keys)

                components, metrics = yield self.__redis.mget(keys)

                if not components:
                    components = []
                else:
                    components = simplejson.loads(components)

                if not metrics:
                    metrics = []
                else:
                    metrics = simplejson.loads(metrics)

                if component not in components or len(metrics) == 0:
                    yield transaction.discard()
                    break

                current_time_slot = int(time.time()) / 60 * 60
                metric_changed = False

                for each_metric in metrics:
                    metric_keys = ['tinyfeedback:data:component:%s:metric:%s:6h' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:36h' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:1w' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:1m' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:6m' % (component, each_metric),
                            ]

                    info_6h = yield self.__redis.get(metric_keys[0])

                    if not info_6h:
                        continue

                    info_6h = simplejson.loads(info_6h)

                    if current_time_slot - info_6h['last_updated'] > \
                            (7 * 24 * 60 * 60):

                        metric_changed = True
                        metrics.remove(each_metric)

                        for each_key in metric_keys:
                            yield transaction.delete(each_key)

                if metric_changed:
                    yield transaction.set(keys[1], simplejson.dumps(metrics))

                    if len(metrics) == 0:
                        components.remove(component)
                        yield transaction.set(keys[0], simplejson.dumps(components))

                yield transaction.commit()
                break

            except txredisapi.WatchError:
                continue

    @defer.inlineCallbacks
    def get_metrics(self, component):
        key = 'tinyfeedback:data:component:%s:list_metrics' % component
        metrics = yield self.__redis.get(key)

        if not metrics:
            defer.returnValue([])
        else:
            defer.returnValue(simplejson.loads(metrics))

    @defer.inlineCallbacks
    def get_data(self, component, metric, timescale):
        key = 'tinyfeedback:data:component:%s:metric:%s:%s' % (component, metric, timescale)

        keys = ['tinyfeedback:data:list_components',
                'tinyfeedback:data:component:%s:list_metrics' % component,
                'tinyfeedback:data:component:%s:metric:%s:6h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:36h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1w' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1m' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:6m' % (component, metric),
                ]

        data = None

        while True:
            try:
                transaction = yield self.__redis.multi(keys)

                info_6h = yield self.__redis.get(keys[2])

                if not info_6h:
                    if timescale in ['6h', '1m', '6m']:
                        yield transaction.discard()
                        defer.returnValue([0] * 360)
                    elif timescale == '36h':
                        yield transaction.discard()
                        defer.returnValue([0] * 432)
                    elif timescale == '1w':
                        yield transaction.discard()
                        defer.returnValue([0] * 336)
                else:
                    info_6h = simplejson.loads(info_6h)

                current_time_slot = int(time.time()) / 60 * 60
                time_since_update = current_time_slot - info_6h['last_updated']

                # If we haven't updated in over 10 minutes, do a long roll up
                if time_since_update / 60 > 10:
                    yield self.__do_long_roll_up(keys, transaction, time_since_update,
                            info_6h)

                    info_6h['last_updated'] = current_time_slot
                    yield transaction.set(keys[2], simplejson.dumps(info_6h))

                # Otherwise do the normal roll up
                elif time_since_update > 0:
                    while current_time_slot > info_6h['last_updated']:
                        info_6h['updates_since_last_roll_up'] += 1
                        info_6h['last_updated'] += 60
                        info_6h['data'].append(0)

                        if info_6h['updates_since_last_roll_up'] >= 10:
                            yield self.__do_roll_up(keys, transaction, info_6h)

                            info_6h['updates_since_last_roll_up'] -= 10

                    # Truncate data to the most recent values
                    info_6h['data'] = info_6h['data'][-360:]

                    info_6h['last_updated'] = current_time_slot
                    yield transaction.set(keys[2], simplejson.dumps(info_6h))

                yield transaction.commit()
                break

            except txredisapi.WatchError:
                continue

        data = yield self.__redis.get(key)

        if not data:
            if timescale in ['6h', '1m', '6m']:
                defer.returnValue([0] * 360)
            elif timescale == '36h':
                defer.returnValue([0] * 432)
            elif timescale == '1w':
                defer.returnValue([0] * 336)
        else:
            data = simplejson.loads(data)
            defer.returnValue(data['data'])

    @defer.inlineCallbacks
    def delete_data(self, component, metric=None):
        keys = ['tinyfeedback:data:list_components',
                'tinyfeedback:data:component:%s:list_metrics' % component,
                ]

        while True:
            try:
                transaction = yield self.__redis.multi(keys)

                components, metrics = yield self.__redis.mget(keys)

                if not components:
                    components = []
                else:
                    components = simplejson.loads(components)

                if not metrics:
                    metrics = []
                else:
                    metrics = simplejson.loads(metrics)

                # If the requested object does not exist, we are done
                if component not in components or \
                        (metric and metric not in metrics):

                    yield transaction.discard()
                    break

                # If the metric is not specified, grab all metrics
                if not metric:
                    metrics_to_delete = metrics
                else:
                    metrics_to_delete = [metric]

                # Delete the data
                for each_metric in metrics_to_delete:
                    metric_keys = [
                            'tinyfeedback:data:component:%s:metric:%s:6h' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:36h' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:1w' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:1m' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:6m' % (component, each_metric),
                            ]

                    for each_key in metric_keys:
                        yield transaction.delete(each_key)

                # If a metric was specified, just remove it
                if metric:
                    metrics.remove(each_metric)
                    yield transaction.set(keys[1], simplejson.dumps(metrics))

                    if len(metrics) == 0:
                        components.remove(component)
                        yield transaction.set(keys[0], simplejson.dumps(components))

                # Otherwise delete the component
                else:
                    components.remove(component)
                    yield transaction.set(keys[0], simplejson.dumps(components))
                    yield transaction.delete(keys[1])

                yield transaction.commit()

                break

            except txredisapi.WatchError:
                continue

    @defer.inlineCallbacks
    def update_metric(self, component, metric, value):
        # Make sure values are sane
        if not re.match('^[A-Za-z0-9_\.:-]+$', component):
            raise ValueError('Bad component: %s (must only contain A-Z, a-z, 0-9, _, -, :, and .)' % component)

        if not re.match('^[A-Za-z0-9_\.:-]+$', metric):
            raise ValueError('Bad metric: %s (must only contain A-Z, a-z, 0-9, _, -, :, and .)' % metric)

        yield self.__update_metric_limit.acquire()

        component = component[:128]
        metric = metric[:128]
        value = int(value)

        # Now we can actually update
        keys = ['tinyfeedback:data:list_components',
                'tinyfeedback:data:component:%s:list_metrics' % component,
                'tinyfeedback:data:component:%s:metric:%s:6h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:36h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1w' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1m' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:6m' % (component, metric),
                ]

        while True:
            try:
                transaction = yield self.__redis.multi(keys)

                components, metrics = yield self.__redis.mget(keys[:2])
                info_6h = yield self.__redis.get(keys[2])

                # Make sure component is listed
                if not components:
                    components = [component]
                    yield transaction.set(keys[0], simplejson.dumps(components))

                else:
                    components = simplejson.loads(components)
                    if component not in components:
                        components.append(component)
                        components.sort()
                        yield transaction.set(keys[0],
                                simplejson.dumps(components))

                # Make sure metric is listed
                if not metrics:
                    metrics = [metric]
                    yield transaction.set(keys[1], simplejson.dumps(metrics))

                else:
                    metrics = simplejson.loads(metrics)
                    if metric not in metrics:
                        metrics.append(metric)
                        metrics.sort()
                        yield transaction.set(keys[1],
                                simplejson.dumps(metrics))

                # Now we're actually ready to deal with the data
                current_time_slot = int(time.time()) / 60 * 60

                if not info_6h:
                    info_6h = {'data': [0] * 360, # Every 1 min
                            'updates_since_last_roll_up': 0,
                            'last_updated': current_time_slot,
                            }

                else:
                    info_6h = simplejson.loads(info_6h)

                time_since_update = current_time_slot - info_6h['last_updated']

                # If we haven't updated in over 10 minutes, do a long roll up
                if time_since_update / 60 > 10:
                    yield self.__do_long_roll_up(keys, transaction,
                            time_since_update, info_6h)

                # Otherwise do the normal roll up
                else:
                    while current_time_slot > info_6h['last_updated']:
                        info_6h['updates_since_last_roll_up'] += 1
                        info_6h['last_updated'] += 60
                        info_6h['data'].append(0)

                        if info_6h['updates_since_last_roll_up'] >= 10:
                            # Make sure the value is set before roll up
                            if current_time_slot == info_6h['last_updated']:
                                info_6h['data'][-1] = value

                            yield self.__do_roll_up(keys, transaction, info_6h)

                            info_6h['updates_since_last_roll_up'] -= 10

                    # Truncate data to the most recent values
                    info_6h['data'] = info_6h['data'][-360:]

                # At last, update the value
                info_6h['data'][-1] = value
                info_6h['last_updated'] = current_time_slot

                yield transaction.set(keys[2], simplejson.dumps(info_6h))

                yield transaction.commit()
                break

            except txredisapi.WatchError:
                continue

        yield self.__update_metric_limit.release()

    @defer.inlineCallbacks
    def __load_long_data(self, keys, transaction):
        info_36h, info_1w, info_1m, info_6m = yield self.__redis.mget(keys[3:])

        # Makes sure the data is loaded
        if not info_36h:
            info_36h = {'data': [0] * 432, # Every 5 min
                    'updates_since_last_roll_up': 0,
                    }

            yield transaction.set(keys[3], simplejson.dumps(info_36h))
        else:
            info_36h = simplejson.loads(info_36h)

        if not info_1w:
            info_1w = {'data': [0] * 336, # Every 30 min
                    'updates_since_last_roll_up': 0,
                    }

            yield transaction.set(keys[4], simplejson.dumps(info_1w))
        else:
            info_1w = simplejson.loads(info_1w)

        if not info_1m:
            info_1m = {'data': [0] * 360, # Every 2 hours
                    'updates_since_last_roll_up': 0,
                    }

            yield transaction.set(keys[5], simplejson.dumps(info_1m))
        else:
            info_1m = simplejson.loads(info_1m)

        if not info_6m:
            info_6m = {'data': [0] * 360, # Every 12 hours
                    }

            yield transaction.set(keys[6], simplejson.dumps(info_6m))
        else:
            info_6m = simplejson.loads(info_6m)

        defer.returnValue((info_36h, info_1w, info_1m, info_6m))

    @defer.inlineCallbacks
    def __do_roll_up(self, keys, transaction, info_6h):
        info_36h, info_1w, info_1m, info_6m = yield self.__load_long_data(
                keys, transaction)

        # Roll up for 36h
        subset = info_6h['data'][-10:]
        min_value = min(subset)
        max_value = max(subset)

        if subset.index(min_value) < subset.index(max_value):
            info_36h['data'].extend([min_value, max_value])
        else:
            info_36h['data'].extend([max_value, min_value])

        info_36h['updates_since_last_roll_up'] += 2
        info_36h['data'] = info_36h['data'][2:]

        # Roll up for 1w
        if info_36h['updates_since_last_roll_up'] >= 12:
            info_36h['updates_since_last_roll_up'] -= 12

            subset = info_36h['data'][-12:]
            min_value = min(subset)
            max_value = max(subset)

            if subset.index(min_value) < subset.index(max_value):
                info_1w['data'].extend([min_value, max_value])
            else:
                info_1w['data'].extend([max_value, min_value])

            info_1w['updates_since_last_roll_up'] += 2
            info_1w['data'] = info_1w['data'][2:]

        # Roll up for 1m
        if info_1w['updates_since_last_roll_up'] >= 8:
            info_1w['updates_since_last_roll_up'] -= 8

            subset = info_1w['data'][-8:]
            min_value = min(subset)
            max_value = max(subset)

            if subset.index(min_value) < subset.index(max_value):
                info_1m['data'].extend([min_value, max_value])
            else:
                info_1m['data'].extend([max_value, min_value])

            info_1m['updates_since_last_roll_up'] += 2
            info_1m['data'] = info_1m['data'][2:]

        # Roll up for 6m
        if info_1m['updates_since_last_roll_up'] >= 12:
            info_1m['updates_since_last_roll_up'] -= 12

            subset = info_1m['data'][-12:]
            min_value = min(subset)
            max_value = max(subset)

            if subset.index(min_value) < subset.index(max_value):
                info_6m['data'].extend([min_value, max_value])
            else:
                info_6m['data'].extend([max_value, min_value])

            info_6m['data'] = info_6m['data'][2:]

        yield transaction.set(keys[3], simplejson.dumps(info_36h))
        yield transaction.set(keys[4], simplejson.dumps(info_1w))
        yield transaction.set(keys[5], simplejson.dumps(info_1m))
        yield transaction.set(keys[6], simplejson.dumps(info_6m))

    @defer.inlineCallbacks
    def __do_long_roll_up(self, keys, transaction, time_since_update, info_6h):
        info_36h, info_1w, info_1m, info_6m = yield self.__load_long_data(
                keys, transaction)

        # Roll up for 6h
        needed_updates = time_since_update / 60
        needed_updates_floor = min(needed_updates, 360)
        info_6h['data'].extend([0] * needed_updates_floor)
        info_6h['data'] = info_6h['data'][-360:]
        info_6h['updates_since_last_roll_up'] += needed_updates

        needed_updates = info_6h['updates_since_last_roll_up'] / 10
        info_6h['updates_since_last_roll_up'] %= 10

        yield transaction.set(keys[2], simplejson.dumps(info_6h))

        # Roll up for 36h
        if needed_updates > 0:
            needed_updates_floor = min(needed_updates, 432 / 2)
            info_36h['data'].extend([0] * 2 * needed_updates_floor)
            info_36h['data'] = info_36h['data'][-432:]
            info_36h['updates_since_last_roll_up'] += needed_updates

            needed_updates = info_36h['updates_since_last_roll_up'] / 12
            info_36h['updates_since_last_roll_up'] %= 12

            yield transaction.set(keys[3], simplejson.dumps(info_36h))

        # Roll up for 1w
        if needed_updates > 0:
            needed_updates_floor = min(needed_updates, 336 / 2)
            info_1w['data'].extend([0] * 2 * needed_updates_floor)
            info_1w['data'] = info_1w['data'][-336:]
            info_1w['updates_since_last_roll_up'] += needed_updates

            needed_updates = info_1w['updates_since_last_roll_up'] / 8
            info_1w['updates_since_last_roll_up'] %= 8

            yield transaction.set(keys[4], simplejson.dumps(info_1w))

        # Roll up for 1m
        if needed_updates > 0:
            needed_updates_floor = min(needed_updates, 360 / 2)
            info_1m['data'].extend([0] * 2 * needed_updates_floor)
            info_1m['data'] = info_1m['data'][-360:]
            info_1m['updates_since_last_roll_up'] += needed_updates

            needed_updates = info_1m['updates_since_last_roll_up'] / 12
            info_1m['updates_since_last_roll_up'] %= 12

            yield transaction.set(keys[5], simplejson.dumps(info_1m))

        # Roll up for 6m
        if needed_updates > 0:
            needed_updates_floor = min(needed_updates, 360 / 2)
            info_6m['data'].extend([0] * 2 * needed_updates_floor)
            info_6m['data'] = info_6m['data'][-360:]

            yield transaction.set(keys[6], simplejson.dumps(info_6m))

########NEW FILE########
__FILENAME__ = webserver
# Here's some curl commands you might want to run:
#   curl -F 'key1=1' -F 'key2=2' http://127.0.0.1:8000/data/component1
#   curl -X DELETE http://127.0.0.1:8000/data/component1/key1

import datetime
import cgi
import logging
import logging.handlers
import os
import time
import urllib
import re

import mako.template
import mako.lookup
import simplejson
from twisted.internet import defer, reactor, threads
from twisted.internet.task import deferLater
from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.static import File
import txroutes

import redis_model


def straighten_out_request(f):
    # The twisted request dictionary return values as lists, this un-does that

    def wrapped_f(*args, **kwargs):
        start = time.time()

        if 'request' in kwargs:
            request_dict = kwargs['request'].args
        else:
            request_dict = args[1].args

        new_request_dict = {}
        for k, v in request_dict.iteritems():
            new_request_dict[k] = v[0]

        if 'request' in kwargs:
            kwargs['request'].args = new_request_dict
        else:
            args[1].args = new_request_dict

        ret = f(*args, **kwargs)

        took = time.time() - start

        if took > 0.5:
            args[0]._log.warn('%s took %f to complete', f, took)

        return ret

    return wrapped_f


class Controller(object):

    def __init__(self, redis_model_data, redis_model_graph, log):
        self.__redis_model_data = redis_model_data
        self.__redis_model_graph = redis_model_graph
        self._log = log

        self.timescales = ['6h', '36h', '1w', '1m', '6m']
        self.graph_types = ['line', 'stacked']

        # Set up template lookup directory
        self.__template_lookup = mako.lookup.TemplateLookup(
                directories=[os.path.join(os.path.dirname(__file__),
                    'templates')], input_encoding='utf-8')

    # User-visible pages
    @straighten_out_request
    def get_index(self, request):
        username = request.getCookie('username')

        if 'edit' in request.args:
            edit = request.args['edit']
        else:
            edit = None

        self.__finish_get_index(request, username, edit)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_get_index(self, request, username, edit):
        components = yield self.__redis_model_data.get_components()

        # Look up custom graphs for this user
        if username is not None:
            graphs = yield self.__redis_model_graph.get_graphs(username)
        else:
            graphs = {}

        graph_data = [None] * len(graphs)

        for title, each_graph in graphs.iteritems():
            graph_data[each_graph['ordering']] = yield self.__get_graph_details(
                    title, each_graph)

        template = self.__template_lookup.get_template('index.mako')

        ret = template.render(components=components, username=username,
                dashboard_username=username, edit=edit, graphs=graph_data,
                cgi=cgi).encode('utf8')

        request.write(ret)
        request.finish()

    def get_dashboards(self, request):
        username = request.getCookie('username')
        self.__finish_get_dashboards(request, username)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_get_dashboards(self, request, username):
        graphs_per_user = yield self.__redis_model_graph.get_graphs_per_user()

        template = self.__template_lookup.get_template('dashboards.mako')

        page = template.render(username=username,
                graphs_per_user=graphs_per_user).encode('utf8')

        request.write(page)
        request.finish()

    def get_user_dashboards(self, request, dashboard_username):
        username = request.getCookie('username')
        self.__finish_get_user_dashboards(request, dashboard_username,
                username)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_get_user_dashboards(self, request, dashboard_username,
            username):

        graphs = yield self.__redis_model_graph.get_graphs(dashboard_username)

        graph_data = [None] * len(graphs)

        for title, each_graph in graphs.iteritems():
            graph_data[each_graph['ordering']] = yield self.__get_graph_details(
                    title, each_graph)

        template = self.__template_lookup.get_template('index.mako')

        ret = template.render(components=[], username=username,
                dashboard_username=dashboard_username, edit=None,
                graphs=graph_data, cgi=cgi).encode('utf8')

        request.write(ret)
        request.finish()

    def delete_user(self, request, dashboard_username):
        self.__finish_delete_user(request, dashboard_username)
        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_delete_user(self, request, dashboard_username):
        yield self.__redis_model_graph.remove_username(dashboard_username)
        request.write('OK')
        request.finish()

    @straighten_out_request
    def get_component(self, request, component):
        if request.args.get('delete_older_than_a_week', None) is not None:
            self.__redis_model_data.delete_metrics_older_than_a_week(component)

            request_args = request.args
            del request_args['delete_older_than_a_week']

            redirect = '/view/%s' % component.encode('utf8')
            if len(request_args) > 0:
                redirect += '?%s' % urllib.urlencode(request_args)

            request.setResponseCode(303)
            request.redirect(redirect)
            return ''

        username = request.getCookie('username')

        timescale = request.args.get('ts', '6h')
        if timescale not in self.timescales:
            timescale = '6h'

        self.__finish_get_component(request, component, username, timescale)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_get_component(self, request, component, username, timescale):
        metrics = yield self.__redis_model_data.get_metrics(component)
        metric_data = []

        for each_metric in metrics:
            data = yield self.__redis_model_data.get_data(component,
                    each_metric, timescale)

            # HACK: if the last value is 0, set it the previous value so sparkline doesn't drop off to 0
            if data[-1] == 0:
                data[-1] = data[-2]

            current = data[-1]
            minimum = min(data)
            maximum = max(data)

            metric_data.append((each_metric, data, current, minimum, maximum))

        template = self.__template_lookup.get_template('component.mako')

        ret = template.render(component=component, metrics=metric_data,
                username=username, timescale=timescale,
                timescales=self.timescales, cgi=cgi).encode('utf8')

        request.write(ret)
        request.finish()

    @straighten_out_request
    def get_edit(self, request):
        username = request.getCookie('username')

        title = request.args.get('title', '')
        title = urllib.unquote_plus(title.replace('$2F', '%2F'))
        request.args['title'] = title

        if 'delete' in request.args and title != '':
            self.__redis_model_graph.remove_graph(username, title)

            request.setResponseCode(303)
            request.redirect('/')
            return ''

        self.__finish_get_edit(request, username, title)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_get_edit(self, request, username, title):
        data_sources = {}

        components = yield self.__redis_model_data.get_components()

        for each_component in components:
            metrics = yield self.__redis_model_data.get_metrics(each_component)
            metrics.sort()

            data_sources[each_component] = metrics

        graphs = yield self.__redis_model_graph.get_graphs(username)
        if title and title in graphs:
            fields = graphs[title]['fields']
            active_components = [each.split('|')[0] for each in fields]

        else:
            fields = []
            active_components = []

        graph_type = request.args.get('graph_type', '')

        template = self.__template_lookup.get_template('edit.mako')

        ret = template.render(kwargs=request.args, fields=fields,
                data_sources=data_sources, active_components=active_components,
                username=username, timescales=self.timescales,
                graph_types=self.graph_types, cgi=cgi).encode('utf8')

        request.write(ret)
        request.finish()

    @straighten_out_request
    def post_edit(self, request):
        username = request.getCookie('username')

        if request.args['title'] == '':
            request.args['error'] = 'no_title'
            redirect = '/edit?%s' % urllib.urlencode(request.args)

            request.setResponseCode(303)
            request.redirect(redirect)
            return ''

        elif len(request.args) == 3:
            request.args['error'] = 'no_fields'
            redirect = '/edit?%s' % urllib.urlencode(request.args)

            request.setResponseCode(303)
            request.redirect(redirect)
            return ''

        title = request.args['title']
        timescale = request.args['timescale']
        graph_type = request.args['graph_type']

        keys = request.args.keys()
        index = keys.index('title')
        del keys[index]

        index = keys.index('graph_type')
        del keys[index]

        index = keys.index('timescale')
        del keys[index]

        # Make sure any wildcards are correctly formatted
        for each_key in keys:
            if '|' not in each_key:
                request.args['error'] = 'bad_wildcard_filter'
                redirect = '/edit?%s' % urllib.urlencode(request.args)

                request.setResponseCode(303)
                request.redirect(redirect)
                return ''

        self.__finish_post_edit(request, username, title, timescale, keys,
                graph_type)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_post_edit(self, request, username, title, timescale, keys,
            graph_type):

        yield self.__redis_model_graph.update_graph(username, title, timescale,
                keys, graph_type)

        request.setResponseCode(303)
        request.redirect('/')
        request.finish()

    @straighten_out_request
    def get_graph(self, request, graph_username, title):
        self._log.debug('get graph %s %s', graph_username, title)

        username = request.getCookie('username')

        # HACK: routes can't handle URLs with %2F in them ('/')
        # so replace '$2F' with '%2F' as we unquote the title
        title = urllib.unquote_plus(title.replace('$2F', '%2F'))

        graph_type = request.args.get('graph_type', '')
        timescale = request.args.get('timescale', '')
        force_max_value = float(request.args.get('max', 0))

        for each in [graph_type, timescale]:
            if each == '':
                request.setResponseCode(400)
                return ''

        self.__finish_get_graph(request, username, graph_username, title,
                graph_type, timescale, force_max_value)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_get_graph(self, request, username, graph_username, title,
            graph_type, timescale, force_max_value):

        graphs = yield self.__redis_model_graph.get_graphs(graph_username)

        graph_details = yield self.__get_graph_details(title, graphs[title],
                graph_type, timescale)

        template = self.__template_lookup.get_template('graph.mako')

        ret = template.render(username=username, graph_username=graph_username,
                title=title, graph_type=graph_type, graph=[graph_details],
                force_max_value=force_max_value).encode('utf8')

        request.write(ret)
        request.finish()

    # AJAX calls to manipulate user state
    @straighten_out_request
    def post_graph_ordering(self, request):
        new_ordering = request.args.get('new_ordering', '')
        username = request.getCookie('username')

        if new_ordering == '':
            request.setResponseCode(400)
            return ''

        new_ordering = simplejson.loads(new_ordering)

        self.__finish_post_graph_ordering(request, username, new_ordering)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_post_graph_ordering(self, request, username, new_ordering):
        yield self.__redis_model_graph.update_ordering(username, new_ordering)

        request.write('')
        request.finish()

    @straighten_out_request
    def post_add_graph_from_other_user(self, request):
        username = request.getCookie('username')

        graph_username = request.args.get('graph_username', '')
        title = request.args.get('title', '')
        timescale = request.args.get('timescale', None)
        graph_type = request.args.get('graph_type', None)

        if graph_username == '' or title == '':
            request.setResponseCode(400)
            return ''

        self.__finish_post_add_graph_from_other_user(request, username,
                graph_username, title, timescale, graph_type)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_post_add_graph_from_other_user(self, request, username,
            graph_username, title, timescale, graph_type):

        graphs = yield self.__redis_model_graph.get_graphs(graph_username)

        if title in graphs:
            if not timescale:
                timescale = graphs[title]['timescale']
            if not graph_type:
                graph_type = graphs[title]['graph_type']

            yield self.__redis_model_graph.update_graph(username, title,
                    timescale, graphs[title]['fields'], graph_type)

        request.setResponseCode(303)
        request.redirect('/')
        request.finish()

    # API for dealing with data
    @straighten_out_request
    def post_data(self, request, component):
        self._log.debug('posting data for %s %s', component, request.args)

        deferreds = []

        for metric, value in request.args.iteritems():
            deferred = self.__redis_model_data.update_metric(component, metric,
                    int(value))

            deferreds.append(deferred)

        defer_list = defer.DeferredList(deferreds, consumeErrors=True)
        defer_list.addCallback(self.__finish_post_data, request)

        return NOT_DONE_YET

    def __finish_post_data(self, responses, request):
        errors = []
        for (success, exception) in responses:
            if not success:
                errors.append(exception.value.message)

        if errors:
            request.setResponseCode(400)
            request.write(simplejson.dumps(errors))
        else:
            request.write('OK')

        request.finish()

    @straighten_out_request
    def get_data(self, request, component, metric):
        timescale = request.args.get('ts', '6h')

        if timescale not in self.timescales:
            timescale = '6h'

        self.__finish_get_data(request, component, metric, timescale)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_get_data(self, request, component, metric, timescale):
        data = yield self.__redis_model_data.get_data(component, metric,
                timescale)

        request.write(simplejson.dumps(data))
        request.finish()

    @straighten_out_request
    def delete_data(self, request, component, metric=None):
        self.__finish_delete_data(request, component, metric)
        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_delete_data(self, request, component, metric):
        yield self.__redis_model_data.delete_data(component, metric)
        request.write('OK')
        request.finish()

    # Dealing with login
    @straighten_out_request
    def post_login(self, request):
        if request.args.get('username', None) is None:
            request.setResponseCode(400)
            request.redirect('/')
            return ''

        username = request.args['username'].lower()

        # Record that this user exists
        self.__redis_model_graph.add_username(username)

        # Save the username as a cookie
        current_utc_time = datetime.datetime.utcnow()
        current_utc_time += datetime.timedelta(days=365)
        expires_str = current_utc_time.strftime('%a, %d-%b-%Y %H:%M:%S GMT')

        request.addCookie('username', username, expires=expires_str)

        referer = request.getHeader('Referer')
        if referer is None:
            referer = '/'

        request.setResponseCode(303)
        request.redirect(referer)
        return ''

    @straighten_out_request
    def get_logout(self, request):
        username = request.getCookie('username')

        request.addCookie('username', username, max_age=0)

        referer = request.getHeader('Referer')
        if referer is None:
            referer = '/'

        request.setResponseCode(303)
        request.redirect(referer)
        return ''

    # Helpers
    @defer.inlineCallbacks
    def __get_graph_details(self, title, graph, graph_type=None,
            timescale=None):

        if not graph_type or graph_type not in self.graph_types:
            graph_type = graph['graph_type']

        if not timescale or timescale not in self.timescales:
            timescale = graph['timescale']

        fields = graph['fields']
        fields.sort() # TODO: migrate graphs so fields are already sorted

        time_per_data_point = 60*1000

        if timescale == '36h':
            time_per_data_point = 5*60*1000
        elif timescale == '1w':
            time_per_data_point = 30*60*1000
        elif timescale == '1m':
            time_per_data_point = 2*60*60*1000
        elif timescale == '6m':
            time_per_data_point = 12*60*60*1000

        line_names = []
        data_rows = []

        for each_field in fields:
            component, metric = each_field.split('|')[:2]

            # Handle wildcard components
            matching_components = []
            if '*' in component:
                component_re = component.replace('*', '[a-zA-Z0-9_\.:-]*')
                component_re = '^%s$' % component_re

                components = yield self.__redis_model_data.get_components()

                for each_component in components:
                    if re.match(component_re, each_component):
                        matching_components.append(each_component)

            else:
                matching_components = [component]


            for each_component in matching_components:
                metrics = yield self.__redis_model_data.get_metrics(
                        each_component)

                # Handle wildcard metrics
                matching_metrics = []
                if '*' in metric:
                    metric_re = metric.replace('*', '[a-zA-Z0-9_\.:-]*')
                else:
                    metric_re = metric

                metric_re = '^%s$' % metric_re

                for each_metric in metrics:
                    if re.match(metric_re, each_metric):
                        matching_metrics.append(each_metric)

                if len(matching_metrics) == 0:
                    line_name = '%s: %s - NO DATA' % (each_component, metric)

                    if line_name not in line_names:
                        line_names.append(line_name.encode('utf8'))

                        data = yield self.__redis_model_data.get_data(
                                each_component, metric, timescale)

                        data_rows.append(data)

                else:
                    for each_metric in matching_metrics:
                        line_name = '%s: %s' % (each_component, each_metric)

                        if line_name not in line_names:
                            line_names.append(line_name.encode('utf8'))

                            data = yield self.__redis_model_data.get_data(
                                    each_component, each_metric, timescale)

                            data_rows.append(data)

        # d3 wants time in ms
        current_time_slot = (int(time.time()) / 60 * 60) * 1000

        if len(data_rows) > 0:
            length = max([len(row) for row in data_rows])

            if graph_type == 'stacked':
                max_value = max([sum(column) for column in zip(*data_rows)])
            else:
                max_value = max([max(row) for row in data_rows])
        else:
            length = 0
            max_value = 0

        # HACK: routes can't handle URLs with %2F in them ('/')
        # so replace '%2F' with '$2F' as we quote the title
        title_urlencoded = urllib.quote_plus(title).replace('%2F', '$2F')

        defer.returnValue((title, title_urlencoded, graph_type,
                urllib.quote_plus(graph_type), timescale,
                time_per_data_point, line_names, data_rows, current_time_slot,
                length, max_value))


def set_up_server(port, log_path, log_level):
    # Set up logging
    log = logging.getLogger('tinyfeedback')
    level = getattr(logging, log_level, logging.INFO)
    log.setLevel(level)

    if log_path != '':
        dir_path = os.path.dirname(log_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, 0755)

        handler = logging.handlers.RotatingFileHandler(log_path,
                maxBytes=100*1024*1024, backupCount=5)

    else:
        handler = logging.StreamHandler()

    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log.addHandler(handler)

    # Connect to redis
    redis_model_data = redis_model.Data('127.0.0.1')
    redis_model_data.connect()

    redis_model_graph = redis_model.Graph('127.0.0.1')
    redis_model_graph.connect()

    # Set up the webserver
    controller = Controller(redis_model_data, redis_model_graph, log)

    dispatcher = txroutes.Dispatcher()

    # User-visible pages
    dispatcher.connect('get_index', '/', controller=controller,
            action='get_index', conditions=dict(method=['GET']))

    dispatcher.connect('get_dashboards', '/dashboards', controller=controller,
            action='get_dashboards', conditions=dict(method=['GET']))

    dispatcher.connect('get_user_dashboards', '/dashboards/{dashboard_username}',
            controller=controller, action='get_user_dashboards',
            conditions=dict(method=['GET']))

    dispatcher.connect('delete_user', '/dashboards/{dashboard_username}',
            controller=controller, action='delete_user',
            conditions=dict(method=['DELETE']))

    dispatcher.connect('get_component', '/view/:component',
            controller=controller, action='get_component',
            conditions=dict(method=['GET']))

    dispatcher.connect('get_edit', '/edit', controller=controller,
            action='get_edit', conditions=dict(method=['GET']))

    dispatcher.connect('post_edit', '/edit', controller=controller,
            action='post_edit', conditions=dict(method=['POST']))

    dispatcher.connect('get_graph', '/graph/{graph_username}/{title}',
            controller=controller, action='get_graph',
            conditions=dict(method=['GET']))

    # AJAX calls to manipulate user state
    dispatcher.connect('post_graph_ordering', '/graph_ordering',
            controller=controller, action='post_graph_ordering',
            conditions=dict(method=['POST']))

    dispatcher.connect('post_add_graph_from_other_user', '/add_graph',
            controller=controller, action='post_add_graph_from_other_user',
            conditions=dict(method=['POST']))

    # API for dealing with data
    dispatcher.connect('post_data', '/data/:component', controller=controller,
            action='post_data', conditions=dict(method=['POST']))

    dispatcher.connect('get_data', '/data/:component/:metric',
            controller=controller, action='get_data',
            conditions=dict(method=['GET']))

    dispatcher.connect('delete_data', '/data/:component',
            controller=controller, action='delete_data',
            conditions=dict(method=['DELETE']))

    dispatcher.connect('delete_data', '/data/:component/:metric',
            controller=controller, action='delete_data',
            conditions=dict(method=['DELETE']))

    # Dealing with login
    dispatcher.connect('post_login', '/login', controller=controller,
            action='post_login', conditions=dict(method=['POST']))

    dispatcher.connect('get_logout', '/logout', controller=controller,
            action='get_logout', conditions=dict(method=['GET']))

    static_path = os.path.join(os.path.dirname(__file__), 'static')

    dispatcher.putChild('static', File(static_path))

    factory = Site(dispatcher)
    reactor.listenTCP(port, factory)

    log.info('tiny feedback running on port %d', port)

    reactor.run()

########NEW FILE########
