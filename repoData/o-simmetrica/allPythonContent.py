__FILENAME__ = app
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import yaml
import re
import argparse

from collections import OrderedDict

from flask import Flask, Response, request, render_template
from simmetrica import Simmetrica

parser = argparse.ArgumentParser(
    description='Starts Simmetrica web application'
)
parser.add_argument(
    '--debug',
    '-d',
    default=False,
    help='Run the app in debug mode',
    action='store_true'
)
parser.add_argument(
    '--config',
    '-c',
    default='config.yml',
    help='Run with the specified config file (default: config.yml)'
)
parser.add_argument(
    '--redis_host',
    '-rh',
    default=None,
    help='Connect to redis on the specified host'
)
parser.add_argument(
    '--redis_port',
    '-rp',
    default=None,
    help='Connect to redis on the specified port'
)
parser.add_argument(
    '--redis_db',
    '-rd',
    default=None,
    help='Connect to the specified db in redis'
)

parser.add_argument(
    '--redis_password',
    '-ra',
    default=None,
    help='Authorization password of redis'
)

args = parser.parse_args()

app = Flask(__name__)
simmetrica = Simmetrica(
    args.redis_host,
    args.redis_port,
    args.redis_db,
    args.redis_password
)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/push/<event>')
def push(event):
    increment = request.args.get('increment') or Simmetrica.DEFAULT_INCREMENT
    now = int(request.args.get('now')) if request.args.get('now') else None
    simmetrica.push(event, increment, now)
    return 'ok'


@app.route('/query/<event>/<int:start>/<int:end>')
def query(event, start, end):
    resolution = request.args.get('resolution') or Simmetrica.DEFAULT_RESOLUTION
    result = simmetrica.query(event, start, end, resolution)
    response = json.dumps(OrderedDict(result))
    return Response(response, status=200, mimetype='application/json')


@app.route('/graph')
def graph():
    stream = file(args.config)
    config = yaml.load(stream)
    result = []
    now = simmetrica.get_current_timestamp()
    for section in config['graphs']:
        timespan_as_seconds = get_seconds_from_relative_time(section.get('timespan', '1 day'))
        events = []
        for event in section['events']:
            data = simmetrica.query(event['name'], now - timespan_as_seconds, now, section.get('resolution', Simmetrica.DEFAULT_RESOLUTION))
            series = [dict(x=timestamp, y=int(value)) for timestamp, value in data]
            events.append(dict(
                name=event['name'],
                title=event.get('title', event['name']),
                data=series
            ))
        result.append(dict(
            title=section.get('title'),
            colorscheme=section.get('colorscheme', 'colorwheel'),
            type=section.get('type', 'area'),
            interpolation=section.get('interpolation', 'cardinal'),
            resolution=section.get('resolution', Simmetrica.DEFAULT_RESOLUTION),
            size=section.get('size', 'M'),
            offset=section.get('offset', 'value'),
            events=events,
            identifier='graph-' + str(id(events))
        ))
    response = json.dumps(result, indent=2)
    return Response(response, status=200, mimetype='application/json')

unit_multipliers = {
    'minute': 60,
    'hour': 3600,
    'day': 86400,
    'week': 86400 * 7,
    'month': 86400 * 30,
    'year': 86400 * 365
}


def get_seconds_from_relative_time(string):
    for unit in unit_multipliers.keys():
        if string.endswith(unit):
            match = re.match(r"(\d+)+\s(\w+)", string)
            if match:
                return unit_multipliers[unit] * int(match.group(1))
    else:
        raise ValueError("Invalid unit '%s'" % string)

if __name__ == '__main__':
    app.run(debug=args.debug)

########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from simmetrica import Simmetrica

parser = argparse.ArgumentParser(
    description='Starts Simmetrica commandline interface'
)

redis_arg_parser = argparse.ArgumentParser(add_help=False)
redis_arg_parser.add_argument(
    '--redis_host',
    '-rh',
    default=None,
    help='Connect to redis on the specified host'
)
redis_arg_parser.add_argument(
    '--redis_port',
    '-rp',
    default=None,
    help='Connect to redis on the specified port'
)
redis_arg_parser.add_argument(
    '--redis_db',
    '-rd',
    default=None,
    help='Connect to the specified db in redis'
)

redis_arg_parser.add_argument(
    '--redis_password',
    '-ra',
    default=None,
    help='Authorization password of redis'
)

subparsers = parser.add_subparsers(dest='subparser_name')

push_parser = subparsers.add_parser('push', parents=[redis_arg_parser])
push_parser.add_argument('event')
push_parser.add_argument(
    '--increment',
    default=Simmetrica.DEFAULT_INCREMENT,
    type=int
)
push_parser.add_argument('--now', type=int)

query_parser = subparsers.add_parser('query', parents=[redis_arg_parser])
query_parser.add_argument('event')
query_parser.add_argument('start', type=int)
query_parser.add_argument('end', type=int)
query_parser.add_argument(
    '--resolution',
    default='5min',
    choices=Simmetrica.resolutions
)

args = parser.parse_args()

simmetrica = Simmetrica(
    args.redis_host,
    args.redis_port,
    args.redis_db,
    args.redis_password
)

if args.subparser_name == 'push':
    simmetrica.push(args.event, args.increment, args.now)
    print 'ok'

if args.subparser_name == 'query':
    results = simmetrica.query(
        args.event,
        args.start,
        args.end,
        args.resolution
    )
    for timestamp, value in results:
        print timestamp, value

########NEW FILE########
__FILENAME__ = simmetrica
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

from redis import StrictRedis


class Simmetrica(object):

    DEFAULT_INCREMENT = 1
    DEFAULT_RESOLUTION = '5min'
    DEFAULT_REDIS_HOST = 'localhost'
    DEFAULT_REDIS_PORT = 6379
    DEFAULT_REDIS_DB = 0
    DEFAULT_REDIS_PASSWORD = None

    resolutions = {
        'min': 60,
        '5min': 300,
        '15min': 900,
        'hour': 3600,
        'day': 86400,
        'week': 86400 * 7,
        'month': 86400 * 30,
        'year': 86400 * 365
    }

    def __init__(self, host=None, port=None, db=None, password=None):
        self.backend = StrictRedis(
            host=host or self.DEFAULT_REDIS_HOST,
            port=int(port or self.DEFAULT_REDIS_PORT),
            db=db or self.DEFAULT_REDIS_DB,
            password=password or self.DEFAULT_REDIS_PASSWORD
        )

    def push(self, event, increment=DEFAULT_INCREMENT, now=None):
        pipe = self.backend.pipeline()
        for resolution, timestamp in self.get_timestamps_for_push(now):
            key = self.get_event_key(event, resolution)
            pipe.hincrby(key, timestamp, increment)
        return pipe.execute()

    def query(self, event, start, end, resolution=DEFAULT_RESOLUTION):
        key = self.get_event_key(event, resolution)
        timestamps = self.get_timestamps_for_query(
            start, end, self.resolutions[resolution])
        values = self.backend.hmget(key, timestamps)
        for timestamp, value in zip(timestamps, values):
            yield timestamp, value or 0

    def get_timestamps_for_query(self, start, end, resolution):
        return range(self.round_time(start, resolution),
                     self.round_time(end, resolution),
                     resolution)

    def get_timestamps_for_push(self, now):
        now = now or self.get_current_timestamp()
        for resolution, timestamp in self.resolutions.items():
            yield resolution, self.round_time(now, timestamp)

    def round_time(self, time, resolution):
        return int(time - (time % resolution))

    def get_event_key(self, event, resolution):
        return 'simmetrica:{0}:{1}'.format(event, resolution)

    def get_current_timestamp(self):
        return int(time.time())

########NEW FILE########
__FILENAME__ = tests
import mock
import unittest
import sys

from simmetrica import Simmetrica


class TestSimmetrica(unittest.TestCase):

    def test_push(self):
        with mock.patch('simmetrica.StrictRedis') as StrictRedis:
            simmetrica = Simmetrica()
            hincrby = StrictRedis.return_value.pipeline.return_value.hincrby
            simmetrica.push('foo')
            self.assertTrue(hincrby.called)

    def test_get_timestamps_for_query(self):
        simmetrica = Simmetrica()
        timestamps = simmetrica.get_timestamps_for_query(1363707480, 1363707780, 60)
        self.assertEqual(timestamps, [1363707480, 1363707540, 1363707600, 1363707660, 1363707720])

    def test_get_timestamps_for_push(self):
        simmetrica = Simmetrica()
        timestamps = list(simmetrica.get_timestamps_for_push(1363707716))
        self.assertEqual(timestamps, [('week', 1363219200), ('hour', 1363705200), ('min', 1363707660), ('month', 1363392000), ('5min', 1363707600), ('year', 1356048000), ('day', 1363651200), ('15min', 1363707000)])

    def test_round_time(self):
        simmetrica = Simmetrica()
        rounded_time = simmetrica.round_time(1363599249, 3600)
        self.assertEqual(rounded_time, 1363597200)

    def test_get_event_key(self):
        simmetrica = Simmetrica()
        key = simmetrica.get_event_key('foo', '5min')
        self.assertEqual('simmetrica:foo:5min', key)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
