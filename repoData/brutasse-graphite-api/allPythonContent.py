__FILENAME__ = conf
#!/usr/bin/env python3
# coding: utf-8

import os
import re
import sys

from sphinx.ext import autodoc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

extensions = [
    'sphinx.ext.autodoc',
]

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

project = 'Graphite-API'
copyright = u'2014, Bruno Renié'

version = '1.0.1'
release = '1.0.1'

exclude_patterns = ['_build']

pygments_style = 'sphinx'

html_theme = 'default'

htmlhelp_basename = 'Graphite-APIdoc'

latex_elements = {
}

latex_documents = [
    ('index', 'Graphite-API.tex', 'Graphite-API Documentation',
     'Bruno Renié', 'manual'),
]

man_pages = [
    ('index', 'graphite-api', 'Graphite-API Documentation',
     ['Bruno Renié'], 1)
]

texinfo_documents = [
    ('index', 'Graphite-API', 'Graphite-API Documentation',
     'Bruno Renié', 'Graphite-API', 'One line description of project.',
     'Miscellaneous'),
]


class RenderFunctionDocumenter(autodoc.FunctionDocumenter):
    priority = 10

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return autodoc.FunctionDocumenter.can_document_member(
            member, membername, isattr, parent
        ) and parent.name == 'graphite_api.functions'

    def format_args(self):
        args = super(RenderFunctionDocumenter, self).format_args()
        if args is not None:
            return re.sub('requestContext, ', '', args)


def setup(app):
    app.add_autodocumenter(RenderFunctionDocumenter)

add_module_names = False


class Mock(object):
    __all__ = []

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Mock()

    @classmethod
    def __getattr__(cls, name):
        if name in ('__file__', '__path__'):
            return '/dev/null'
        elif name[0] == name[0].upper():
            mockType = type(name, (), {})
            mockType.__module__ = __name__
            return mockType
        else:
            return Mock()

for mod_name in ['cairocffi']:
    sys.modules[mod_name] = Mock()

########NEW FILE########
__FILENAME__ = app
import csv
import json
import math
import pytz
import shutil
import six
import tempfile

from collections import defaultdict
from datetime import datetime
from io import StringIO, BytesIO

from flask import Flask, jsonify
from structlog import get_logger

from .config import configure
from .encoders import JSONEncoder
from .render.attime import parseATTime
from .render.datalib import fetchData, TimeSeries
from .render.glyph import GraphTypes
from .render.grammar import grammar
from .utils import RequestParams

logger = get_logger()


class Graphite(Flask):
    @property
    def store(self):
        return self.config['GRAPHITE']['store']

    @property
    def searcher(self):
        return self.config['GRAPHITE']['searcher']

    @property
    def functions(self):
        return self.config['GRAPHITE']['functions']

    @property
    def logger(self):
        # Flask has its own logger that doesn't get any handler if we use
        # dictconfig(). Replace it with our structlog logger.
        return logger


app = Graphite(__name__)
try:
    configure(app)
except Exception:
    import traceback
    print(traceback.format_exc())
    raise

methods = ('GET', 'POST')


# No-op routes, non-essential for creating dashboards
@app.route('/dashboard/find', methods=methods)
def dashboard_find():
    return jsonify({'dashboards': []})


@app.route('/dashboard/load/<name>', methods=methods)
def dashboard_load(name):
    return jsonify(
        {'error': "Dashboard '{0}' does not exist.".format(name)}), 404


@app.route('/events/get_data', methods=methods)
def events():
    return json.dumps([]), 200, {'Content-Type': 'application/json'}


# API calls that actually do something
@app.route('/metrics/search', methods=methods)
def metrics_search():
    errors = {}
    try:
        max_results = int(RequestParams.get('max_results', 25))
    except ValueError:
        errors['max_results'] = 'must be an integer.'
    if 'query' not in RequestParams:
        errors['query'] = 'this parameter is required.'
    if errors:
        return jsonify({'errors': errors}), 400
    results = sorted(app.searcher.search(
        query=RequestParams['query'],
        max_results=max_results,
    ), key=lambda result: result['path'] or '')
    return jsonify({'metrics': results})


@app.route('/metrics/find', methods=methods)
def metrics_find():
    errors = {}
    from_time = None
    until_time = None
    wildcards = False

    try:
        wildcards = bool(int(RequestParams.get('wildcards', 0)))
    except ValueError:
        errors['wildcards'] = 'must be 0 or 1.'

    try:
        from_time = int(RequestParams.get('from', 0))
    except ValueError:
        errors['from'] = 'must be an epoch timestamp.'
    try:
        until_time = int(RequestParams.get('until', 0))
    except ValueError:
        errors['until'] = 'must be an epoch timestamp.'

    format = RequestParams.get('format', 'treejson')
    if format not in ['treejson', 'completer']:
        errors['format'] = 'unrecognized format: "{0}".'.format(format)

    if 'query' not in RequestParams:
        errors['query'] = 'this parameter is required.'

    if errors:
        return jsonify({'errors': errors}), 400

    query = RequestParams['query']
    matches = sorted(
        app.store.find(query, from_time, until_time),
        key=lambda node: node.name
    )

    base_path = query.rsplit('.', 1)[0] + '.' if '.' in query else ''

    if format == 'treejson':
        data = tree_json(matches, base_path, wildcards=wildcards)
        return (
            json.dumps(data),
            200,
            {'Content-Type': 'application/json'}
        )

    results = []
    for node in matches:
        node_info = {
            'path': node.path,
            'name': node.name,
            'is_leaf': int(node.is_leaf),  # XXX Y was this cast to str
        }
        if not node.is_leaf:
            node_info['path'] += '.'
        results.append(node_info)

    if len(results) > 1 and wildcards:
        results.append({'name': '*'})

    return jsonify({'metrics': results})


@app.route('/metrics/expand', methods=methods)
def metrics_expand():
    errors = {}
    try:
        group_by_expr = bool(int(RequestParams.get('groupByExpr', 0)))
    except ValueError:
        errors['groupByExpr'] = 'must be 0 or 1.'
    try:
        leaves_only = bool(int(RequestParams.get('leavesOnly', 0)))
    except ValueError:
        errors['leavesOnly'] = 'must be 0 or 1.'

    if 'query' not in RequestParams:
        errors['query'] = 'this parameter is required.'
    if errors:
        return jsonify({'errors': errors}), 400

    results = defaultdict(set)
    for query in RequestParams.getlist('query'):
        for node in app.store.find(query):
            if node.is_leaf or not leaves_only:
                results[query].add(node.path)

    if group_by_expr:
        for query, matches in results.items():
            results[query] = sorted(matches)
    else:
        new_results = set()
        for value in results.values():
            new_results = new_results.union(value)
        results = sorted(new_results)

    return jsonify({'results': results})


def prune_datapoints(series, max_datapoints, start, end):
    time_range = end - start
    points = time_range // series.step
    if max_datapoints < points:
        values_per_point = int(
            math.ceil(float(points) / float(max_datapoints))
        )
        seconds_per_point = values_per_point * series.step
        nudge = (
            seconds_per_point
            + (series.start % series.step)
            - (series.start % seconds_per_point)
        )
        series.start += nudge
        values_to_lose = nudge // series.step
        del series[:values_to_lose-1]
        series.consolidate(values_per_point)
        step = seconds_per_point
    else:
        step = series.step

    timestamps = range(series.start, series.end + series.step, step)
    datapoints = zip(series, timestamps)
    return {'target': series.name, 'datapoints': datapoints}


def recurse(query, index):
    """
    Recursively walk across paths, adding leaves to the index as they're found.
    """
    for node in app.store.find(query):
        if node.is_leaf:
            index.add(node.path)
        else:
            recurse('{0}.*'.format(node.path), index)


@app.route('/index', methods=['POST', 'PUT'])
def build_index():
    index = set()
    recurse('*', index)
    with tempfile.NamedTemporaryFile(delete=False) as index_file:
        index_file.write('\n'.join(sorted(index)).encode('utf-8'))
    shutil.move(index_file.name, app.searcher.index_path)
    app.searcher.reload()
    return jsonify({'success': True, 'entries': len(index)}), 200


@app.route('/render', methods=methods)
def render():
    errors = {}
    graph_options = {
        'width': 600,
        'height': 300,
    }
    request_options = {}
    graph_type = RequestParams.get('graphType', 'line')
    try:
        graph_class = GraphTypes[graph_type]
        request_options['graphType'] = graph_type
        request_options['graphClass'] = graph_class
    except KeyError:
        errors['graphType'] = (
            "Invalid graphType '{0}', must be one of '{1}'.".format(
                graph_type, "', '".join(sorted(GraphTypes.keys()))))
    request_options['pieMode'] = RequestParams.get('pieMode', 'average')
    targets = RequestParams.getlist('target')
    if not len(targets):
        errors['target'] = 'This parameter is required.'
    request_options['targets'] = targets

    if 'rawData' in RequestParams:
        request_options['format'] = 'raw'
    if 'format' in RequestParams:
        request_options['format'] = RequestParams['format']
        if 'jsonp' in RequestParams:
            request_options['jsonp'] = RequestParams['jsonp']
    if 'maxDataPoints' in RequestParams:
        try:
            request_options['maxDataPoints'] = int(
                float(RequestParams['maxDataPoints']))
        except ValueError:
            errors['maxDataPoints'] = 'Must be an integer.'

    if errors:
        return jsonify({'errors': errors}), 400

    for opt in graph_class.customizable:
        if opt in RequestParams:
            value = RequestParams[opt]
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    if value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    elif value.lower() == 'default' or not value:
                        continue
            graph_options[opt] = value

    tzinfo = pytz.timezone(app.config['TIME_ZONE'])
    tz = RequestParams.get('tz')
    if tz:
        try:
            tzinfo = pytz.timezone(tz)
        except pytz.UnknownTimeZoneError:
            errors['tz'] = "Unknown timezone: '{0}'.".format(tz)
    request_options['tzinfo'] = tzinfo

    until_time = parseATTime(RequestParams.get('until', 'now'), tzinfo)
    from_time = parseATTime(RequestParams.get('from', '-1d'), tzinfo)

    start_time = min(from_time, until_time)
    end_time = max(from_time, until_time)
    if start_time == end_time:
        errors['from'] = errors['until'] = 'Invalid empty time range'

    request_options['startTime'] = start_time
    request_options['endTime'] = end_time

    if errors:
        return jsonify({'errors': errors}), 400

    # Done with options.

    headers = {
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    context = {
        'startTime': request_options['startTime'],
        'endTime': request_options['endTime'],
        'data': [],
    }

    if request_options['graphType'] == 'pie':
        for target in request_options['targets']:
            if ':' in target:
                name, value = target.split(':', 1)
                try:
                    value = float(value)
                except ValueError:
                    errors['target'] = "Invalid target: '{0}'.".format(target)
                context['data'].append((name, value))
            else:
                series_list = evaluateTarget(context, target)

                for series in series_list:
                    func = app.functions[request_options['pieMode']]
                    context['data'].append((series.name,
                                            func(context, series) or 0))

        if errors:
            return jsonify({'errors': errors}), 400

    else:  # graphType == 'line'
        for target in request_options['targets']:
            if not target.strip():
                continue
            series_list = evaluateTarget(context, target)
            context['data'].extend(series_list)

        request_options['format'] = request_options.get('format')

        if request_options['format'] == 'csv':
            response = BytesIO() if six.PY2 else StringIO()
            writer = csv.writer(response, dialect='excel')
            for series in context['data']:
                for index, value in enumerate(series):
                    ts = datetime.fromtimestamp(
                        series.start + index * series.step,
                        request_options['tzinfo']
                    )
                    writer.writerow((series.name,
                                     ts.strftime("%Y-%m-%d %H:%M:%S"), value))
            response.seek(0)
            headers['Content-Type'] = 'text/csv'
            return response.read(), 200, headers

        if request_options['format'] == 'json':
            series_data = []
            if 'maxDataPoints' in request_options and any(context['data']):
                start_time = min([s.start for s in context['data']])
                end_time = max([s.end for s in context['data']])
                for series in context['data']:
                    series_data.append(prune_datapoints(
                        series, request_options['maxDataPoints'],
                        start_time, end_time))
            else:
                for series in context['data']:
                    timestamps = range(series.start, series.end + series.step,
                                       series.step)
                    datapoints = zip(series, timestamps)
                    series_data.append({'target': series.name,
                                        'datapoints': datapoints})

            rendered = json.dumps(series_data, cls=JSONEncoder)

            if 'jsonp' in request_options:
                headers['Content-Type'] = 'text/javascript'
                return ('{0}({1})'.format(request_options['jsonp'],
                                          rendered), 200,
                        headers)
            else:
                headers['Content-Type'] = 'application/json'
                return rendered, 200, headers

        if request_options['format'] == 'raw':
            response = StringIO()
            for series in context['data']:
                response.write(u"%s,%d,%d,%d|" % (
                    series.name, series.start, series.end, series.step))
                response.write(u','.join(map(str, series)))
                response.write(u'\n')
            response.seek(0)
            headers['Content-Type'] = 'text/plain'
            return response.read(), 200, headers

        if request_options['format'] == 'svg':
            graph_options['outputFormat'] = 'svg'

    graph_options['data'] = context['data']
    image = doImageRender(request_options['graphClass'], graph_options)

    use_svg = graph_options.get('outputFormat') == 'svg'

    if use_svg and 'jsonp' in request_options:
        headers['Content-Type'] = 'text/javascript'
        return ('{0}({1})'.format(request_options['jsonp'],
                                  json.dumps(image.decode('utf-8'))),
                200, headers)
    else:
        ctype = 'image/svg+xml' if use_svg else 'image/png'
        headers['Content-Type'] = ctype
        return image, 200, headers


def evaluateTarget(requestContext, target):
    tokens = grammar.parseString(target)
    result = evaluateTokens(requestContext, tokens)

    if isinstance(result, TimeSeries):
        return [result]  # we have to return a list of TimeSeries objects

    return result


def evaluateTokens(requestContext, tokens):
    if tokens.expression:
        return evaluateTokens(requestContext, tokens.expression)

    elif tokens.pathExpression:
        return fetchData(requestContext, tokens.pathExpression)

    elif tokens.call:
        func = app.functions[tokens.call.funcname]
        args = [evaluateTokens(requestContext,
                               arg) for arg in tokens.call.args]
        kwargs = dict([(kwarg.argname,
                        evaluateTokens(requestContext, kwarg.args[0]))
                       for kwarg in tokens.call.kwargs])
        return func(requestContext, *args, **kwargs)

    elif tokens.number:
        if tokens.number.integer:
            return int(tokens.number.integer)
        elif tokens.number.float:
            return float(tokens.number.float)
        elif tokens.number.scientific:
            return float(tokens.number.scientific[0])

    elif tokens.string:
        return tokens.string[1:-1]

    elif tokens.boolean:
        return tokens.boolean[0] == 'true'


def tree_json(nodes, base_path, wildcards=False):
    results = []

    branchNode = {
        'allowChildren': 1,
        'expandable': 1,
        'leaf': 0,
    }
    leafNode = {
        'allowChildren': 0,
        'expandable': 0,
        'leaf': 1,
    }

    # Add a wildcard node if appropriate
    if len(nodes) > 1 and wildcards:
        wildcardNode = {'text': '*', 'id': base_path + '*'}

        if any(not n.is_leaf for n in nodes):
            wildcardNode.update(branchNode)

        else:
            wildcardNode.update(leafNode)

        results.append(wildcardNode)

    found = set()
    results_leaf = []
    results_branch = []
    for node in nodes:  # Now let's add the matching children
        if node.name in found:
            continue

        found.add(node.name)
        resultNode = {
            'text': str(node.name),
            'id': base_path + str(node.name),
        }

        if node.is_leaf:
            resultNode.update(leafNode)
            results_leaf.append(resultNode)
        else:
            resultNode.update(branchNode)
            results_branch.append(resultNode)

    results.extend(results_branch)
    results.extend(results_leaf)
    return results


def doImageRender(graphClass, graphOptions):
    pngData = BytesIO()
    img = graphClass(**graphOptions)
    img.output(pngData)
    imageData = pngData.getvalue()
    pngData.close()
    return imageData

########NEW FILE########
__FILENAME__ = config
import logging
import os
import structlog
import warnings
import yaml

from importlib import import_module
from structlog.processors import (format_exc_info, JSONRenderer,
                                  KeyValueRenderer)

from .middleware import CORS, TrailingSlash
from .search import IndexSearcher
from .storage import Store
from . import DEBUG

try:
    from logging.config import dictConfig
except ImportError:
    from logutils.dictconfig import dictConfig

if DEBUG:
    processors = (format_exc_info, KeyValueRenderer())
else:
    processors = (format_exc_info, JSONRenderer())

logger = structlog.get_logger()

default_conf = {
    'search_index': '/srv/graphite/index',
    'finders': [
        'graphite_api.finders.whisper.WhisperFinder',
    ],
    'functions': [
        'graphite_api.functions.SeriesFunctions',
        'graphite_api.functions.PieFunctions',
    ],
    'whisper': {
        'directories': [
            '/srv/graphite/whisper',
        ],
    },
    'time_zone': 'UTC',
}


# attributes of a classical log record
NON_EXTRA = set(['module', 'filename', 'levelno', 'exc_text', 'pathname',
                 'lineno', 'msg', 'funcName', 'relativeCreated',
                 'levelname', 'msecs', 'threadName', 'name', 'created',
                 'process', 'processName', 'thread'])


class StructlogFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        self._bound = structlog.BoundLoggerBase(None, processors, {})

    def format(self, record):
        if not record.name.startswith('graphite_api'):
            kw = dict(((k, v) for k, v in record.__dict__.items()
                       if k not in NON_EXTRA))
            kw['logger'] = record.name
            return self._bound._process_event(
                record.levelname.lower(), record.getMessage(), kw)[0]
        return record.getMessage()


def load_by_path(path):
    module, klass = path.rsplit('.', 1)
    finder = import_module(module)
    return getattr(finder, klass)


def configure(app):
    config_file = os.environ.get('GRAPHITE_API_CONFIG',
                                 '/etc/graphite-api.yaml')
    if os.path.exists(config_file):
        with open(config_file) as f:
            config = yaml.safe_load(f)
            config['path'] = config_file
    else:
        warnings.warn("Unable to find configuration file at {0}, using "
                      "default config.".format(config_file))
        config = {}

    configure_logging(config)

    for key, value in list(default_conf.items()):
        config.setdefault(key, value)

    loaded_config = {'functions': {}, 'finders': []}
    for functions in config['functions']:
        loaded_config['functions'].update(load_by_path(functions))

    finders = []
    for finder in config['finders']:
        finders.append(load_by_path(finder)(config))
    loaded_config['store'] = Store(finders)
    loaded_config['searcher'] = IndexSearcher(config['search_index'])
    app.config['GRAPHITE'] = loaded_config
    app.config['TIME_ZONE'] = config['time_zone']

    if 'sentry_dsn' in config:
        try:
            from raven.contrib.flask import Sentry
        except ImportError:
            warnings.warn("'sentry_dsn' is provided in the configuration the "
                          "sentry client is not installed. Please `pip "
                          "install raven[flask]`.")
        else:
            Sentry(app, dsn=config['sentry_dsn'])
    app.wsgi_app = TrailingSlash(CORS(app.wsgi_app,
                                      config.get('allowed_origins')))


def configure_logging(config):
    structlog.configure(processors=processors,
                        logger_factory=structlog.stdlib.LoggerFactory(),
                        wrapper_class=structlog.stdlib.BoundLogger,
                        cache_logger_on_first_use=True)
    config.setdefault('logging', {})
    config['logging'].setdefault('version', 1)
    config['logging'].setdefault('handlers', {})
    config['logging'].setdefault('formatters', {})
    config['logging'].setdefault('loggers', {})
    config['logging']['handlers'].setdefault('raw', {
        'level': 'DEBUG',
        'class': 'logging.StreamHandler',
        'formatter': 'raw',
    })
    config['logging']['loggers'].setdefault('root', {
        'handlers': ['raw'],
        'level': 'DEBUG',
        'propagate': False,
    })
    config['logging']['loggers'].setdefault('graphite_api', {
        'handlers': ['raw'],
        'level': 'DEBUG',
    })
    config['logging']['formatters']['raw'] = {'()': StructlogFormatter}
    dictConfig(config['logging'])
    if 'path' in config:
        logger.info("loading configuration", path=config['path'])
    else:
        logger.info("loading default configuration")

########NEW FILE########
__FILENAME__ = encoders
import json


class JSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode generators.
    """
    def default(self, o):
        if hasattr(o, 'tolist'):
            return o.tolist()
        elif hasattr(o, '__getitem__'):
            try:
                return dict(o)
            except:
                pass
        elif hasattr(o, '__iter__'):
            return [i for i in o]
        return super(JSONEncoder, self).default(o)

########NEW FILE########
__FILENAME__ = whisper
from __future__ import absolute_import

import gzip
import os.path
import time

from ..intervals import Interval, IntervalSet
from ..node import BranchNode, LeafNode
from .._vendor import whisper

from . import fs_to_metric, get_real_metric_path, match_entries


class WhisperFinder(object):
    def __init__(self, config):
        self.directories = config['whisper']['directories']

    def find_nodes(self, query):
        clean_pattern = query.pattern.replace('\\', '')
        pattern_parts = clean_pattern.split('.')

        for root_dir in self.directories:
            if not os.path.isdir(root_dir):
                os.makedirs(root_dir)
            for absolute_path in self._find_paths(root_dir, pattern_parts):
                if os.path.basename(absolute_path).startswith('.'):
                    continue

                relative_path = absolute_path[len(root_dir):].lstrip('/')
                metric_path = fs_to_metric(relative_path)
                real_metric_path = get_real_metric_path(absolute_path,
                                                        metric_path)

                metric_path_parts = metric_path.split('.')
                for field_index in find_escaped_pattern_fields(query.pattern):
                    metric_path_parts[field_index] = pattern_parts[
                        field_index].replace('\\', '')
                metric_path = '.'.join(metric_path_parts)

                # Now we construct and yield an appropriate Node object
                if os.path.isdir(absolute_path):
                    yield BranchNode(metric_path)

                elif os.path.isfile(absolute_path):
                    if absolute_path.endswith('.wsp'):
                        reader = WhisperReader(absolute_path, real_metric_path)
                        yield LeafNode(metric_path, reader)

                    elif absolute_path.endswith('.wsp.gz'):
                        reader = GzippedWhisperReader(absolute_path,
                                                      real_metric_path)
                        yield LeafNode(metric_path, reader)

    def _find_paths(self, current_dir, patterns):
        """Recursively generates absolute paths whose components
        underneath current_dir match the corresponding pattern in
        patterns"""
        pattern = patterns[0]
        patterns = patterns[1:]
        entries = os.listdir(current_dir)

        subdirs = [e for e in entries
                   if os.path.isdir(os.path.join(current_dir, e))]
        matching_subdirs = match_entries(subdirs, pattern)

        if patterns:  # we've still got more directories to traverse
            for subdir in matching_subdirs:

                absolute_path = os.path.join(current_dir, subdir)
                for match in self._find_paths(absolute_path, patterns):
                    yield match

        else:  # we've got the last pattern
            files = [e for e in entries
                     if os.path.isfile(os.path.join(current_dir, e))]
            matching_files = match_entries(files, pattern + '.*')

            for _basename in matching_files + matching_subdirs:
                yield os.path.join(current_dir, _basename)


class WhisperReader(object):
    __slots__ = ('fs_path', 'real_metric_path')

    def __init__(self, fs_path, real_metric_path):
        self.fs_path = fs_path
        self.real_metric_path = real_metric_path

    def get_intervals(self):
        start = time.time() - whisper.info(self.fs_path)['maxRetention']
        end = max(os.stat(self.fs_path).st_mtime, start)
        return IntervalSet([Interval(start, end)])

    def fetch(self, startTime, endTime):
        data = whisper.fetch(self.fs_path, startTime, endTime)
        if not data:
            return None

        time_info, values = data
        start, end, step = time_info
        return time_info, values


class GzippedWhisperReader(WhisperReader):
    def get_intervals(self):
        fh = gzip.GzipFile(self.fs_path, 'rb')
        try:
            info = whisper.__readHeader(fh)  # evil, but necessary.
        finally:
            fh.close()

        start = time.time() - info['maxRetention']
        end = max(os.stat(self.fs_path).st_mtime, start)
        return IntervalSet([Interval(start, end)])

    def fetch(self, startTime, endTime):
        fh = gzip.GzipFile(self.fs_path, 'rb')
        try:
            return whisper.file_fetch(fh, startTime, endTime)
        finally:
            fh.close()


def find_escaped_pattern_fields(pattern_string):
    pattern_parts = pattern_string.split('.')
    for index, part in enumerate(pattern_parts):
        if is_escaped_pattern(part):
            yield index


def is_escaped_pattern(s):
    for symbol in '*?[{':
        i = s.find(symbol)
        if i > 0:
            if s[i-1] == '\\':
                return True
    return False

########NEW FILE########
__FILENAME__ = functions
# coding: utf-8
# Copyright 2008 Orbitz WorldWide
# Copyright 2014 Bruno Renié
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import defaultdict
from datetime import datetime, timedelta
from functools import partial
from operator import is_not, itemgetter

import math
import re
import random
import six

from six.moves import zip, map, reduce

from .render.attime import parseTimeOffset
from .render.glyph import format_units
from .render.datalib import TimeSeries
from .utils import to_seconds, epoch

NAN = float('NaN')
INF = float('inf')
MINUTE = 60
HOUR = MINUTE * 60
DAY = HOUR * 24


# Utility functions
not_none = partial(is_not, None)


def safeSum(values):
    return sum(filter(not_none, values))


def safeDiff(values):
    safeValues = list(filter(not_none, values))
    if safeValues:
        values = list(map(lambda x: -x, safeValues[1:]))
        values.insert(0, safeValues[0])
        return sum(values)


def safeLen(values):
    return len(list(filter(not_none, values)))


def safeDiv(a, b):
    if a is None:
        return None
    if b in (0, None):
        return None
    return float(a) / float(b)


def safeMul(*factors):
    if None in factors:
        return

    product = 1
    for factor in factors:
        product *= float(factor)
    return product


def safeSubtract(a, b):
    if a is None or b is None:
        return None
    return float(a) - float(b)


def safeAvg(a):
    return safeDiv(safeSum(a), safeLen(a))


def safeStdDev(a):
    sm = safeSum(a)
    ln = safeLen(a)
    avg = safeDiv(sm, ln)
    sum = 0
    for val in filter(not_none, a):
        sum = sum + (val - avg) * (val - avg)
    return math.sqrt(sum/ln)


def safeLast(values):
    for v in reversed(values):
        if v is not None:
            return v


def safeMin(values):
    safeValues = [v for v in values if v is not None]
    if safeValues:
        return min(safeValues)


def safeMax(values):
    safeValues = [v for v in values if v is not None]
    if safeValues:
        return max(safeValues)


def safeMap(function, values):
    safeValues = [v for v in values if v is not None]
    if safeValues:
        return [function(x) for x in values]


def safeAbs(value):
    if value is None:
        return None
    return abs(value)


# Greatest common divisor
def gcd(a, b):
    if b == 0:
        return a
    return gcd(b, a % b)


# Least common multiple
def lcm(a, b):
    if a == b:
        return a
    if a < b:
        a, b = b, a  # ensure a > b
    return a / gcd(a, b) * b


def normalize(seriesLists):
    seriesList = reduce(lambda L1, L2: L1+L2, seriesLists)
    step = reduce(lcm, [s.step for s in seriesList])
    for s in seriesList:
        s.consolidate(step // s.step)
    start = min([s.start for s in seriesList])
    end = max([s.end for s in seriesList])
    end -= (end - start) % step
    return seriesList, start, end, step


def formatPathExpressions(seriesList):
    """
    Returns a comma-separated list of unique path expressions.
    """
    pathExpressions = sorted(set([s.pathExpression for s in seriesList]))
    return ','.join(pathExpressions)

# Series Functions

# NOTE: Some of the functions below use izip, which may be problematic.
# izip stops when it hits the end of the shortest series
# in practice this *shouldn't* matter because all series will cover
# the same interval, despite having possibly different steps...


def sumSeries(requestContext, *seriesLists):
    """
    Short form: sum()

    This will add metrics together and return the sum at each datapoint. (See
    integral for a sum over time)

    Example::

        &target=sum(company.server.application*.requestsHandled)

    This would show the sum of all requests handled per minute (provided
    requestsHandled are collected once a minute).     If metrics with different
    retention rates are combined, the coarsest metric is graphed, and the sum
    of the other metrics is averaged for the metrics with finer retention
    rates.

    """

    seriesList, start, end, step = normalize(seriesLists)
    name = "sumSeries(%s)" % formatPathExpressions(seriesList)
    values = (safeSum(row) for row in zip(*seriesList))
    series = TimeSeries(name, start, end, step, values)
    series.pathExpression = name
    return [series]


def sumSeriesWithWildcards(requestContext, seriesList, *positions):
    """
    Call sumSeries after inserting wildcards at the given position(s).

    Example::

        &target=sumSeriesWithWildcards(host.cpu-[0-7].cpu-{user,system}.value,
                                       1)

    This would be the equivalent of::

        &target=sumSeries(host.*.cpu-user.value)&target=sumSeries(
            host.*.cpu-system.value)

    """
    newSeries = {}
    newNames = list()

    for series in seriesList:
        newname = '.'.join(map(lambda x: x[1],
                               filter(lambda i: i[0] not in positions,
                                      enumerate(series.name.split('.')))))
        if newname in newSeries:
            newSeries[newname] = sumSeries(requestContext,
                                           (series, newSeries[newname]))[0]
        else:
            newSeries[newname] = series
            newNames.append(newname)
        newSeries[newname].name = newname

    return [newSeries[name] for name in newNames]


def averageSeriesWithWildcards(requestContext, seriesList, *positions):
    """
    Call averageSeries after inserting wildcards at the given position(s).

    Example::

        &target=averageSeriesWithWildcards(
            host.cpu-[0-7].cpu-{user,system}.value, 1)

    This would be the equivalent of::

        &target=averageSeries(host.*.cpu-user.value)&target=averageSeries(
            host.*.cpu-system.value)

    """
    matchedList = defaultdict(list)
    for series in seriesList:
        newname = '.'.join(map(lambda x: x[1],
                               filter(lambda i: i[0] not in positions,
                                      enumerate(series.name.split('.')))))
        matchedList[newname].append(series)
    result = []
    for name in matchedList:
        [series] = averageSeries(requestContext, (matchedList[name]))
        series.name = name
        result.append(series)
    return result


def diffSeries(requestContext, *seriesLists):
    """
    Can take two or more metrics.
    Subtracts parameters 2 through n from parameter 1.

    Example::

        &target=diffSeries(service.connections.total,
                           service.connections.failed)

    """
    seriesList, start, end, step = normalize(seriesLists)
    name = "diffSeries(%s)" % formatPathExpressions(seriesList)
    values = (safeDiff(row) for row in zip(*seriesList))
    series = TimeSeries(name, start, end, step, values)
    series.pathExpression = name
    return [series]


def averageSeries(requestContext, *seriesLists):
    """
    Short Alias: avg()

    Takes one metric or a wildcard seriesList.
    Draws the average value of all metrics passed at each time.

    Example::

        &target=averageSeries(company.server.*.threads.busy)

    """
    seriesList, start, end, step = normalize(seriesLists)
    name = "averageSeries(%s)" % formatPathExpressions(seriesList)
    values = (safeDiv(safeSum(row), safeLen(row)) for row in zip(*seriesList))
    series = TimeSeries(name, start, end, step, values)
    series.pathExpression = name
    return [series]


def stddevSeries(requestContext, *seriesLists):
    """

    Takes one metric or a wildcard seriesList.
    Draws the standard deviation of all metrics passed at each time.

    Example::

        &target=stddevSeries(company.server.*.threads.busy)

    """
    seriesList, start, end, step = normalize(seriesLists)
    name = "stddevSeries(%s)" % formatPathExpressions(seriesList)
    values = (safeStdDev(row) for row in zip(*seriesList))
    series = TimeSeries(name, start, end, step, values)
    series.pathExpression = name
    return [series]


def minSeries(requestContext, *seriesLists):
    """
    Takes one metric or a wildcard seriesList.
    For each datapoint from each metric passed in, pick the minimum value and
    graph it.

    Example::

        &target=minSeries(Server*.connections.total)
    """
    seriesList, start, end, step = normalize(seriesLists)
    name = "minSeries(%s)" % formatPathExpressions(seriesList)
    values = (safeMin(row) for row in zip(*seriesList))
    series = TimeSeries(name, start, end, step, values)
    series.pathExpression = name
    return [series]


def maxSeries(requestContext, *seriesLists):
    """
    Takes one metric or a wildcard seriesList. For each datapoint from each
    metric passed in, pick the maximum value and graph it.

    Example::

        &target=maxSeries(Server*.connections.total)

    """
    seriesList, start, end, step = normalize(seriesLists)
    name = "maxSeries(%s)" % formatPathExpressions(seriesList)
    values = (safeMax(row) for row in zip(*seriesList))
    series = TimeSeries(name, start, end, step, values)
    series.pathExpression = name
    return [series]


def rangeOfSeries(requestContext, *seriesLists):
    """
    Takes a wildcard seriesList.
    Distills down a set of inputs into the range of the series

    Example::

        &target=rangeOfSeries(Server*.connections.total)

    """
    seriesList, start, end, step = normalize(seriesLists)
    name = "rangeOfSeries(%s)" % formatPathExpressions(seriesList)
    values = (safeSubtract(max(row),
                           min(row)) for row in zip(*seriesList))
    series = TimeSeries(name, start, end, step, values)
    series.pathExpression = name
    return [series]


def percentileOfSeries(requestContext, seriesList, n, interpolate=False):
    """
    percentileOfSeries returns a single series which is composed of the
    n-percentile values taken across a wildcard series at each point.
    Unless `interpolate` is set to True, percentile values are actual values
    contained in one of the supplied series.
    """
    if n <= 0:
        raise ValueError(
            'The requested percent is required to be greater than 0')

    name = 'percentilesOfSeries(%s,%g)' % (seriesList[0].pathExpression, n)
    start, end, step = normalize([seriesList])[1:]
    values = [_getPercentile(row, n, interpolate) for row in zip(*seriesList)]
    resultSeries = TimeSeries(name, start, end, step, values)
    resultSeries.pathExpression = name
    return [resultSeries]


def keepLastValue(requestContext, seriesList, limit=INF):
    """
    Takes one metric or a wildcard seriesList, and optionally a limit to the
    number of 'None' values to skip over. Continues the line with the last
    received value when gaps ('None' values) appear in your data, rather than
    breaking your line.

    Example::

        &target=keepLastValue(Server01.connections.handled)
        &target=keepLastValue(Server01.connections.handled, 10)

    """
    for series in seriesList:
        series.name = "keepLastValue(%s)" % (series.name)
        series.pathExpression = series.name
        consecutiveNones = 0
        for i, value in enumerate(series):
            series[i] = value

            # No 'keeping' can be done on the first value because we have no
            # idea what came before it.
            if i == 0:
                continue

            if value is None:
                consecutiveNones += 1
            else:
                if 0 < consecutiveNones <= limit:
                    # If a non-None value is seen before the limit of Nones is
                    # hit, backfill all the missing datapoints with the last
                    # known value.
                    for index in range(i - consecutiveNones, i):
                        series[index] = series[i - consecutiveNones - 1]

                consecutiveNones = 0

        # If the series ends with some None values, try to backfill a bit to
        # cover it.
        if 0 < consecutiveNones < limit:
            for index in range(len(series) - consecutiveNones, len(series)):
                series[index] = series[len(series) - consecutiveNones - 1]

    return seriesList


def asPercent(requestContext, seriesList, total=None):
    """

    Calculates a percentage of the total of a wildcard series. If `total` is
    specified, each series will be calculated as a percentage of that total.
    If `total` is not specified, the sum of all points in the wildcard series
    will be used instead.

    The `total` parameter may be a single series or a numeric value.

    Example::

        &target=asPercent(Server01.connections.{failed,succeeded},
                          Server01.connections.attempted)
        &target=asPercent(apache01.threads.busy,1500)
        &target=asPercent(Server01.cpu.*.jiffies)

    """

    normalize([seriesList])

    if total is None:
        totalValues = [safeSum(row) for row in zip(*seriesList)]
        totalText = None  # series.pathExpression
    elif isinstance(total, list):
        if len(total) != 1:
            raise ValueError(
                "asPercent second argument must reference exactly 1 series")
        normalize([seriesList, total])
        totalValues = total[0]
        totalText = totalValues.name
    else:
        totalValues = [total] * len(seriesList[0])
        totalText = str(total)

    resultList = []
    for series in seriesList:
        resultValues = [safeMul(safeDiv(val, totalVal), 100.0)
                        for val, totalVal in zip(series, totalValues)]

        name = "asPercent(%s, %s)" % (series.name,
                                      totalText or series.pathExpression)
        resultSeries = TimeSeries(name, series.start, series.end, series.step,
                                  resultValues)
        resultSeries.pathExpression = name
        resultList.append(resultSeries)

    return resultList


def divideSeries(requestContext, dividendSeriesList, divisorSeriesList):
    """
    Takes a dividend metric and a divisor metric and draws the division result.
    A constant may *not* be passed. To divide by a constant, use the scale()
    function (which is essentially a multiplication operation) and use the
    inverse of the dividend. (Division by 8 = multiplication by 1/8 or 0.125)

    Example::

        &target=divideSeries(Series.dividends,Series.divisors)


    """
    if len(divisorSeriesList) != 1:
        raise ValueError(
            "divideSeries second argument must reference exactly 1 series")

    [divisorSeries] = divisorSeriesList
    results = []

    for dividendSeries in dividendSeriesList:
        name = "divideSeries(%s,%s)" % (dividendSeries.name,
                                        divisorSeries.name)
        bothSeries = (dividendSeries, divisorSeries)
        step = reduce(lcm, [s.step for s in bothSeries])

        for s in bothSeries:
            s.consolidate(step / s.step)

        start = min([s.start for s in bothSeries])
        end = max([s.end for s in bothSeries])
        end -= (end - start) % step

        values = (safeDiv(v1, v2) for v1, v2 in zip(*bothSeries))

        quotientSeries = TimeSeries(name, start, end, step, values)
        quotientSeries.pathExpression = name
        results.append(quotientSeries)

    return results


def multiplySeries(requestContext, *seriesLists):
    """
    Takes two or more series and multiplies their points. A constant may not be
    used. To multiply by a constant, use the scale() function.

    Example::

        &target=multiplySeries(Series.dividends,Series.divisors)


    """

    seriesList, start, end, step = normalize(seriesLists)

    if len(seriesList) == 1:
        return seriesList

    name = "multiplySeries(%s)" % ','.join([s.name for s in seriesList])
    product = map(lambda x: safeMul(*x), zip(*seriesList))
    resultSeries = TimeSeries(name, start, end, step, product)
    resultSeries.pathExpression = name
    return [resultSeries]


def weightedAverage(requestContext, seriesListAvg, seriesListWeight, node):
    """
    Takes a series of average values and a series of weights and
    produces a weighted average for all values.

    The corresponding values should share a node as defined
    by the node parameter, 0-indexed.

    Example::

        &target=weightedAverage(*.transactions.mean,*.transactions.count,0)

    """

    sortedSeries = {}

    for seriesAvg, seriesWeight in zip(seriesListAvg, seriesListWeight):
        key = seriesAvg.name.split(".")[node]
        sortedSeries.setdefault(key, {})
        sortedSeries[key]['avg'] = seriesAvg

        key = seriesWeight.name.split(".")[node]
        sortedSeries.setdefault(key, {})
        sortedSeries[key]['weight'] = seriesWeight

    productList = []

    for key in sortedSeries:
        if 'weight' not in sortedSeries[key]:
            continue
        if 'avg' not in sortedSeries[key]:
            continue

        seriesWeight = sortedSeries[key]['weight']
        seriesAvg = sortedSeries[key]['avg']

        productValues = [safeMul(val1, val2)
                         for val1, val2 in zip(seriesAvg, seriesWeight)]
        name = 'product(%s,%s)' % (seriesWeight.name, seriesAvg.name)
        productSeries = TimeSeries(name, seriesAvg.start, seriesAvg.end,
                                   seriesAvg.step, productValues)
        productSeries.pathExpression = name
        productList.append(productSeries)

    [sumProducts] = sumSeries(requestContext, productList)
    [sumWeights] = sumSeries(requestContext, seriesListWeight)

    resultValues = [safeDiv(val1, val2)
                    for val1, val2 in zip(sumProducts, sumWeights)]
    name = "weightedAverage(%s, %s)" % (
        ','.join(set(s.pathExpression for s in seriesListAvg)),
        ','.join(set(s.pathExpression for s in seriesListWeight)))
    resultSeries = TimeSeries(name, sumProducts.start, sumProducts.end,
                              sumProducts.step, resultValues)
    resultSeries.pathExpression = name
    return resultSeries


def movingMedian(requestContext, seriesList, windowSize):
    """
    Graphs the moving median of a metric (or metrics) over a fixed number of
    past points, or a time interval.

    Takes one metric or a wildcard seriesList followed by a number N of
    datapoints or a quoted string with a length of time like '1hour' or '5min'
    (See ``from / until`` in the render\_api_ for examples of time formats).
    Graphs the median of the preceeding datapoints for each point on the
    graph. All previous datapoints are set to None at the beginning of the
    graph.

    Example::

        &target=movingMedian(Server.instance01.threads.busy,10)
        &target=movingMedian(Server.instance*.threads.idle,'5min')

    """
    windowInterval = None
    if isinstance(windowSize, six.string_types):
        delta = parseTimeOffset(windowSize)
        windowInterval = to_seconds(delta)

    if windowInterval:
        bootstrapSeconds = windowInterval
    else:
        bootstrapSeconds = max([s.step for s in seriesList]) * int(windowSize)

    bootstrapList = _fetchWithBootstrap(requestContext, seriesList,
                                        seconds=bootstrapSeconds)
    result = []

    for bootstrap, series in zip(bootstrapList, seriesList):
        if windowInterval:
            windowPoints = windowInterval // series.step
        else:
            windowPoints = int(windowSize)

        if isinstance(windowSize, six.string_types):
            newName = 'movingMedian(%s,"%s")' % (series.name, windowSize)
        else:
            newName = "movingMedian(%s,%d)" % (series.name, windowPoints)
        newSeries = TimeSeries(newName, series.start, series.end, series.step,
                               [])
        newSeries.pathExpression = newName

        offset = len(bootstrap) - len(series)
        for i in range(len(series)):
            window = bootstrap[i + offset - windowPoints:i + offset]
            nonNull = [v for v in window if v is not None]
            if nonNull:
                m_index = len(nonNull) // 2
                newSeries.append(sorted(nonNull)[m_index])
            else:
                newSeries.append(None)
        result.append(newSeries)

    return result


def scale(requestContext, seriesList, factor):
    """
    Takes one metric or a wildcard seriesList followed by a constant, and
    multiplies the datapoint by the constant provided at each point.

    Example::

        &target=scale(Server.instance01.threads.busy,10)
        &target=scale(Server.instance*.threads.busy,10)

    """
    for series in seriesList:
        series.name = "scale(%s,%g)" % (series.name, float(factor))
        series.pathExpression = series.name
        for i, value in enumerate(series):
            series[i] = safeMul(value, factor)
    return seriesList


def invert(requestContext, seriesList):
    """
    Takes one metric or a wildcard seriesList, and inverts each datapoint
    (i.e. 1/x).

    Example::

        &target=invert(Server.instance01.threads.busy)

    """
    for series in seriesList:
        series.name = "invert(%s)" % (series.name)
        for i, value in enumerate(series):
            series[i] = safeDiv(1, value)
    return seriesList


def scaleToSeconds(requestContext, seriesList, seconds):
    """
    Takes one metric or a wildcard seriesList and returns "value per seconds"
    where seconds is a last argument to this functions.

    Useful in conjunction with derivative or integral function if you want
    to normalize its result to a known resolution for arbitrary retentions
    """

    for series in seriesList:
        series.name = "scaleToSeconds(%s,%d)" % (series.name, seconds)
        series.pathExpression = series.name
        for i, value in enumerate(series):
            factor = seconds * 1.0 / series.step
            series[i] = safeMul(value, factor)
    return seriesList


def absolute(requestContext, seriesList):
    """
    Takes one metric or a wildcard seriesList and applies the mathematical abs
    function to each datapoint transforming it to its absolute value.

    Example::

        &target=absolute(Server.instance01.threads.busy)
        &target=absolute(Server.instance*.threads.busy)
    """
    for series in seriesList:
        series.name = "absolute(%s)" % (series.name)
        series.pathExpression = series.name
        for i, value in enumerate(series):
            series[i] = safeAbs(value)
    return seriesList


def offset(requestContext, seriesList, factor):
    """
    Takes one metric or a wildcard seriesList followed by a constant, and adds
    the constant to each datapoint.

    Example::

        &target=offset(Server.instance01.threads.busy,10)

    """
    for series in seriesList:
        series.name = "offset(%s,%g)" % (series.name, float(factor))
        series.pathExpression = series.name
        for i, value in enumerate(series):
            if value is not None:
                series[i] = value + factor
    return seriesList


def offsetToZero(requestContext, seriesList):
    """
    Offsets a metric or wildcard seriesList by subtracting the minimum
    value in the series from each datapoint.

    Useful to compare different series where the values in each series
    may be higher or lower on average but you're only interested in the
    relative difference.

    An example use case is for comparing different round trip time
    results. When measuring RTT (like pinging a server), different
    devices may come back with consistently different results due to
    network latency which will be different depending on how many
    network hops between the probe and the device. To compare different
    devices in the same graph, the network latency to each has to be
    factored out of the results. This is a shortcut that takes the
    fastest response (lowest number in the series) and sets that to zero
    and then offsets all of the other datapoints in that series by that
    amount. This makes the assumption that the lowest response is the
    fastest the device can respond, of course the more datapoints that
    are in the series the more accurate this assumption is.

    Example::

        &target=offsetToZero(Server.instance01.responseTime)
        &target=offsetToZero(Server.instance*.responseTime)

    """
    for series in seriesList:
        series.name = "offsetToZero(%s)" % (series.name)
        minimum = safeMin(series)
        for i, value in enumerate(series):
            if value is not None:
                series[i] = value - minimum
    return seriesList


def movingAverage(requestContext, seriesList, windowSize):
    """
    Graphs the moving average of a metric (or metrics) over a fixed number of
    past points, or a time interval.

    Takes one metric or a wildcard seriesList followed by a number N of
    datapoints or a quoted string with a length of time like '1hour' or '5min'
    (See ``from / until`` in the render\_api_ for examples of time formats).
    Graphs the average of the preceeding datapoints for each point on the
    graph. All previous datapoints are set to None at the beginning of the
    graph.

    Example::

        &target=movingAverage(Server.instance01.threads.busy,10)
        &target=movingAverage(Server.instance*.threads.idle,'5min')

    """
    windowInterval = None
    if isinstance(windowSize, six.string_types):
        delta = parseTimeOffset(windowSize)
        windowInterval = to_seconds(delta)

    if windowInterval:
        bootstrapSeconds = windowInterval
    else:
        bootstrapSeconds = max([s.step for s in seriesList]) * int(windowSize)

    bootstrapList = _fetchWithBootstrap(requestContext, seriesList,
                                        seconds=bootstrapSeconds)
    result = []

    for bootstrap, series in zip(bootstrapList, seriesList):
        if windowInterval:
            windowPoints = windowInterval // series.step
        else:
            windowPoints = int(windowSize)

        if isinstance(windowSize, six.string_types):
            newName = 'movingAverage(%s,"%s")' % (series.name, windowSize)
        else:
            newName = "movingAverage(%s,%s)" % (series.name, windowSize)
        newSeries = TimeSeries(newName, series.start, series.end, series.step,
                               [])
        newSeries.pathExpression = newName

        offset = len(bootstrap) - len(series)
        for i in range(len(series)):
            window = bootstrap[i + offset - windowPoints:i + offset]
            newSeries.append(safeAvg(window))

        result.append(newSeries)

    return result


def cumulative(requestContext, seriesList):
    """
    Takes one metric or a wildcard seriesList, and an optional function.

    Valid functions are 'sum', 'average', 'min', and 'max'

    Sets the consolidation function to 'sum' for the given metric seriesList.

    Alias for :func:`consolidateBy(series, 'sum')
    <graphite.render.functions.consolidateBy>`

    Example::

        &target=cumulative(Sales.widgets.largeBlue)

    """
    return consolidateBy(requestContext, seriesList, 'sum')


def consolidateBy(requestContext, seriesList, consolidationFunc):
    """
    Takes one metric or a wildcard seriesList and a consolidation function
    name.

    Valid function names are 'sum', 'average', 'min', and 'max'

    When a graph is drawn where width of the graph size in pixels is smaller
    than the number of datapoints to be graphed, Graphite consolidates the
    values to to prevent line overlap. The consolidateBy() function changes
    the consolidation function from the default of 'average' to one of 'sum',
    'max', or 'min'. This is especially useful in sales graphs, where
    fractional values make no sense and a 'sum' of consolidated values is
    appropriate.

    Example::

        &target=consolidateBy(Sales.widgets.largeBlue, 'sum')
        &target=consolidateBy(Servers.web01.sda1.free_space, 'max')

    """
    for series in seriesList:
        # datalib will throw an exception, so it's not necessary to validate
        # here
        series.consolidationFunc = consolidationFunc
        series.name = 'consolidateBy(%s,"%s")' % (series.name,
                                                  series.consolidationFunc)
        series.pathExpression = series.name
    return seriesList


def derivative(requestContext, seriesList):
    """
    This is the opposite of the integral function. This is useful for taking a
    running total metric and calculating the delta between subsequent data
    points.

    This function does not normalize for periods of time, as a true derivative
    would. Instead see the perSecond() function to calculate a rate of change
    over time.

    Example::

        &target=derivative(company.server.application01.ifconfig.TXPackets)

    Each time you run ifconfig, the RX and TXPackets are higher (assuming there
    is network traffic.) By applying the derivative function, you can get an
    idea of the packets per minute sent or received, even though you're only
    recording the total.
    """
    results = []
    for series in seriesList:
        newValues = []
        prev = None
        for val in series:
            if None in (prev, val):
                newValues.append(None)
                prev = val
                continue
            newValues.append(val - prev)
            prev = val
        newName = "derivative(%s)" % series.name
        newSeries = TimeSeries(newName, series.start, series.end, series.step,
                               newValues)
        newSeries.pathExpression = newName
        results.append(newSeries)
    return results


def perSecond(requestContext, seriesList, maxValue=None):
    """
    Derivative adjusted for the series time interval
    This is useful for taking a running total metric and showing how many
    requests per second were handled.

    Example::

        &target=perSecond(company.server.application01.ifconfig.TXPackets)

    Each time you run ifconfig, the RX and TXPackets are higher (assuming there
    is network traffic.) By applying the derivative function, you can get an
    idea of the packets per minute sent or received, even though you're only
    recording the total.
    """
    results = []
    for series in seriesList:
        newValues = []
        prev = None
        for val in series:
            step = series.step
            if None in (prev, val):
                newValues.append(None)
                prev = val
                continue

            diff = val - prev
            if diff >= 0:
                newValues.append(diff / step)
            elif maxValue is not None and maxValue >= val:
                newValues.append(((maxValue - prev) + val + 1) / step)
            else:
                newValues.append(None)

            prev = val
        newName = "perSecond(%s)" % series.name
        newSeries = TimeSeries(newName, series.start, series.end, series.step,
                               newValues)
        newSeries.pathExpression = newName
        results.append(newSeries)
    return results


def integral(requestContext, seriesList):
    """
    This will show the sum over time, sort of like a continuous addition
    function. Useful for finding totals or trends in metrics that are
    collected per minute.

    Example::

        &target=integral(company.sales.perMinute)

    This would start at zero on the left side of the graph, adding the sales
    each minute, and show the total sales for the time period selected at the
    right side, (time now, or the time specified by '&until=').
    """
    results = []
    for series in seriesList:
        newValues = []
        current = 0.0
        for val in series:
            if val is None:
                newValues.append(None)
            else:
                current += val
                newValues.append(current)
        newName = "integral(%s)" % series.name
        newSeries = TimeSeries(newName, series.start, series.end, series.step,
                               newValues)
        newSeries.pathExpression = newName
        results.append(newSeries)
    return results


def nonNegativeDerivative(requestContext, seriesList, maxValue=None):
    """
    Same as the derivative function above, but ignores datapoints that trend
    down. Useful for counters that increase for a long time, then wrap or
    reset. (Such as if a network interface is destroyed and recreated by
    unloading and re-loading a kernel module, common with USB / WiFi cards.

    Example::

        &target=nonNegativederivative(
            company.server.application01.ifconfig.TXPackets)

    """
    results = []

    for series in seriesList:
        newValues = []
        prev = None

        for val in series:
            if None in (prev, val):
                newValues.append(None)
                prev = val
                continue

            diff = val - prev
            if diff >= 0:
                newValues.append(diff)
            elif maxValue is not None and maxValue >= val:
                newValues.append((maxValue - prev) + val + 1)
            else:
                newValues.append(None)

            prev = val

        newName = "nonNegativeDerivative(%s)" % series.name
        newSeries = TimeSeries(newName, series.start, series.end, series.step,
                               newValues)
        newSeries.pathExpression = newName
        results.append(newSeries)

    return results


def stacked(requestContext, seriesLists, stackName='__DEFAULT__'):
    """
    Takes one metric or a wildcard seriesList and change them so they are
    stacked. This is a way of stacking just a couple of metrics without having
    to use the stacked area mode (that stacks everything). By means of this a
    mixed stacked and non stacked graph can be made

    It can also take an optional argument with a name of the stack, in case
    there is more than one, e.g. for input and output metrics.

    Example::

        &target=stacked(company.server.application01.ifconfig.TXPackets, 'tx')

    """
    if 'totalStack' in requestContext:
        totalStack = requestContext['totalStack'].get(stackName, [])
    else:
        requestContext['totalStack'] = {}
        totalStack = []
    results = []
    for series in seriesLists:
        newValues = []
        for i in range(len(series)):
            if len(totalStack) <= i:
                totalStack.append(0)

            if series[i] is not None:
                totalStack[i] += series[i]
                newValues.append(totalStack[i])
            else:
                newValues.append(None)

        # Work-around for the case when legend is set
        if stackName == '__DEFAULT__':
            newName = "stacked(%s)" % series.name
        else:
            newName = series.name

        newSeries = TimeSeries(newName, series.start, series.end, series.step,
                               newValues)
        newSeries.options['stacked'] = True
        newSeries.pathExpression = newName
        results.append(newSeries)
    requestContext['totalStack'][stackName] = totalStack
    return results


def areaBetween(requestContext, *seriesLists):
    """
    Draws the area in between the two series in seriesList.

    Examples::

        &target=areaBetween(collectd.db1.load.load-relative.shortterm,
                            collectd.db2.load.load-relative.shortterm)

        &target=areaBetween(collectd.db*.load.load-relative.shortterm)
    """
    if len(seriesLists) == 1:
        [seriesLists] = seriesLists
    assert len(seriesLists) == 2, ("areaBetween series argument must "
                                   "reference *exactly* 2 series")
    lower, upper = seriesLists
    if len(lower) == 1:
        [lower] = lower
    if len(upper) == 1:
        [upper] = upper
    lower.options['stacked'] = True
    lower.options['invisible'] = True

    upper.options['stacked'] = True
    lower.name = upper.name = "areaBetween(%s)" % upper.pathExpression
    return [lower, upper]


def aliasSub(requestContext, seriesList, search, replace):
    """
    Runs series names through a regex search/replace.

   Example::

        &target=aliasSub(ip.*TCP*,"^.*TCP(\d+)","\\1")
    """
    try:
        seriesList.name = re.sub(search, replace, seriesList.name)
    except AttributeError:
        for series in seriesList:
            series.name = re.sub(search, replace, series.name)
    return seriesList


def alias(requestContext, seriesList, newName):
    """
    Takes one metric or a wildcard seriesList and a string in quotes.
    Prints the string instead of the metric name in the legend.

    Example::

        &target=alias(Sales.widgets.largeBlue,"Large Blue Widgets")

    """
    try:
        seriesList.name = newName
    except AttributeError:
        for series in seriesList:
            series.name = newName
    return seriesList


def cactiStyle(requestContext, seriesList, system=None):
    """
    Takes a series list and modifies the aliases to provide column aligned
    output with Current, Max, and Min values in the style of cacti. Optonally
    takes a "system" value to apply unit formatting in the same style as the
    Y-axis.
    NOTE: column alignment only works with monospace fonts such as terminus.

    Example::

        &target=cactiStyle(ganglia.*.net.bytes_out,"si")

    """
    if system:
        fmt = lambda x: "%.2f%s" % format_units(x, system=system)
    else:
        fmt = lambda x: "%.2f" % x
    nameLen = max([0] + [len(series.name) for series in seriesList])
    lastLen = max([0] + [len(fmt(int(safeLast(series) or 3)))
                         for series in seriesList]) + 3
    maxLen = max([0] + [len(fmt(int(safeMax(series) or 3)))
                        for series in seriesList]) + 3
    minLen = max([0] + [len(fmt(int(safeMin(series) or 3)))
                        for series in seriesList]) + 3
    for series in seriesList:
        last = safeLast(series)
        maximum = safeMax(series)
        minimum = safeMin(series)
        if last is None:
            last = NAN
        else:
            last = fmt(float(last))

        if maximum is None:
            maximum = NAN
        else:
            maximum = fmt(float(maximum))
        if minimum is None:
            minimum = NAN
        else:
            minimum = fmt(float(minimum))

        series.name = "%*s Current:%*s Max:%*s Min:%*s " % (
            -nameLen, series.name, -lastLen, last,
            -maxLen, maximum, -minLen, minimum)
    return seriesList


def aliasByNode(requestContext, seriesList, *nodes):
    """
    Takes a seriesList and applies an alias derived from one or more "node"
    portion/s of the target name. Node indices are 0 indexed.

    Example::

        &target=aliasByNode(ganglia.*.cpu.load5,1)

    """
    for series in seriesList:
        metric_pieces = re.search('(?:.*\()?(?P<name>[-\w*\.]+)(?:,|\)?.*)?',
                                  series.name).groups()[0].split('.')
        series.name = '.'.join(metric_pieces[n] for n in nodes)
    return seriesList


def aliasByMetric(requestContext, seriesList):
    """
    Takes a seriesList and applies an alias derived from the base metric name.

    Example::

        &target=aliasByMetric(carbon.agents.graphite.creates)

    """
    for series in seriesList:
        series.name = series.name.split('.')[-1]
    return seriesList


def legendValue(requestContext, seriesList, *valueTypes):
    """
    Takes one metric or a wildcard seriesList and a string in quotes.
    Appends a value to the metric name in the legend. Currently one or several
    of: `last`, `avg`, `total`, `min`, `max`. The last argument can be `si`
    (default) or `binary`, in that case values will be formatted in the
    corresponding system.

    Example::

        &target=legendValue(Sales.widgets.largeBlue, 'avg', 'max', 'si')

    """
    valueFuncs = {
        'avg': lambda s: safeDiv(safeSum(s), safeLen(s)),
        'total': safeSum,
        'min': safeMin,
        'max': safeMax,
        'last': safeLast,
    }
    system = None
    if valueTypes[-1] in ('si', 'binary'):
        system = valueTypes[-1]
        valueTypes = valueTypes[:-1]
    for valueType in valueTypes:
        valueFunc = valueFuncs.get(valueType, lambda s: '(?)')
        if system is None:
            for series in seriesList:
                series.name += " (%s: %s)" % (valueType, valueFunc(series))
        else:
            for series in seriesList:
                value = valueFunc(series)
                formatted = None
                if value is not None:
                    formatted = "%.2f%s" % format_units(abs(value),
                                                        system=system)
                series.name = "%-20s%-5s%-10s" % (series.name, valueType,
                                                  formatted)
    return seriesList


def alpha(requestContext, seriesList, alpha):
    """
    Assigns the given alpha transparency setting to the series. Takes a float
    value between 0 and 1.
    """
    for series in seriesList:
        series.options['alpha'] = alpha
    return seriesList


def color(requestContext, seriesList, theColor):
    """
    Assigns the given color to the seriesList

    Example::

        &target=color(collectd.hostname.cpu.0.user, 'green')
        &target=color(collectd.hostname.cpu.0.system, 'ff0000')
        &target=color(collectd.hostname.cpu.0.idle, 'gray')
        &target=color(collectd.hostname.cpu.0.idle, '6464ffaa')

    """
    for series in seriesList:
        series.color = theColor
    return seriesList


def substr(requestContext, seriesList, start=0, stop=0):
    """
    Takes one metric or a wildcard seriesList followed by 1 or 2 integers.
    Assume that the metric name is a list or array, with each element
    separated by dots. Prints n - length elements of the array (if only one
    integer n is passed) or n - m elements of the array (if two integers n and
    m are passed). The list starts with element 0 and ends with element
    (length - 1).

    Example::

        &target=substr(carbon.agents.hostname.avgUpdateTime,2,4)

    The label would be printed as "hostname.avgUpdateTime".

    """
    for series in seriesList:
        left = series.name.rfind('(') + 1
        right = series.name.find(')')
        if right < 0:
            right = len(series.name)+1
        cleanName = series.name[left:right:].split('.')
        if int(stop) == 0:
            series.name = '.'.join(cleanName[int(start)::])
        else:
            series.name = '.'.join(cleanName[int(start):int(stop):])

        # substr(func(a.b,'c'),1) becomes b instead of b,'c'
        series.name = re.sub(',.*$', '', series.name)
    return seriesList


def logarithm(requestContext, seriesList, base=10):
    """
    Takes one metric or a wildcard seriesList, a base, and draws the y-axis in
    logarithmic format. If base is omitted, the function defaults to base 10.

    Example::

        &target=log(carbon.agents.hostname.avgUpdateTime,2)

    """
    results = []
    for series in seriesList:
        newValues = []
        for val in series:
            if val is None:
                newValues.append(None)
            elif val <= 0:
                newValues.append(None)
            else:
                newValues.append(math.log(val, base))
        newName = "log(%s, %s)" % (series.name, base)
        newSeries = TimeSeries(newName, series.start, series.end, series.step,
                               newValues)
        newSeries.pathExpression = newName
        results.append(newSeries)
    return results


def maximumAbove(requestContext, seriesList, n):
    """
    Takes one metric or a wildcard seriesList followed by a constant n.
    Draws only the metrics with a maximum value above n.

    Example::

        &target=maximumAbove(system.interface.eth*.packetsSent,1000)

    This would only display interfaces which sent more than 1000 packets/min.
    """
    results = []
    for series in seriesList:
        if max(series) > n:
            results.append(series)
    return results


def minimumAbove(requestContext, seriesList, n):
    """
    Takes one metric or a wildcard seriesList followed by a constant n.
    Draws only the metrics with a minimum value above n.

    Example::

        &target=minimumAbove(system.interface.eth*.packetsSent,1000)

    This would only display interfaces which sent more than 1000 packets/min.
    """
    results = []
    for series in seriesList:
        if min(series) > n:
            results.append(series)
    return results


def maximumBelow(requestContext, seriesList, n):
    """
    Takes one metric or a wildcard seriesList followed by a constant n.
    Draws only the metrics with a maximum value below n.

    Example::

        &target=maximumBelow(system.interface.eth*.packetsSent,1000)

    This would only display interfaces which sent less than 1000 packets/min.
    """

    result = []
    for series in seriesList:
        if max(series) <= n:
            result.append(series)
    return result


def highestCurrent(requestContext, seriesList, n=1):
    """
    Takes one metric or a wildcard seriesList followed by an integer N.
    Out of all metrics passed, draws only the N metrics with the highest value
    at the end of the time period specified.

    Example::

        &target=highestCurrent(server*.instance*.threads.busy,5)

    Draws the 5 servers with the highest busy threads.

    """
    return sorted(seriesList, key=safeLast)[-n:]


def highestMax(requestContext, seriesList, n=1):
    """
    Takes one metric or a wildcard seriesList followed by an integer N.

    Out of all metrics passed, draws only the N metrics with the highest
    maximum value in the time period specified.

    Example::

        &target=highestMax(server*.instance*.threads.busy,5)

    Draws the top 5 servers who have had the most busy threads during the time
    period specified.

    """
    result_list = sorted(seriesList, key=lambda s: max(s))[-n:]
    return sorted(result_list, key=lambda s: max(s), reverse=True)


def lowestCurrent(requestContext, seriesList, n=1):
    """
    Takes one metric or a wildcard seriesList followed by an integer N.
    Out of all metrics passed, draws only the N metrics with the lowest value
    at the end of the time period specified.

    Example::

        &target=lowestCurrent(server*.instance*.threads.busy,5)

    Draws the 5 servers with the least busy threads right now.

    """
    return sorted(seriesList, key=safeLast)[:n]


def currentAbove(requestContext, seriesList, n):
    """
    Takes one metric or a wildcard seriesList followed by an integer N.
    Out of all metrics passed, draws only the metrics whose value is above N
    at the end of the time period specified.

    Example::

        &target=currentAbove(server*.instance*.threads.busy,50)

    Draws the servers with more than 50 busy threads.

    """
    return [series for series in seriesList if safeLast(series) >= n]


def currentBelow(requestContext, seriesList, n):
    """
    Takes one metric or a wildcard seriesList followed by an integer N.
    Out of all metrics passed, draws only the    metrics whose value is below N
    at the end of the time period specified.

    Example::

        &target=currentBelow(server*.instance*.threads.busy,3)

    Draws the servers with less than 3 busy threads.

    """
    return [series for series in seriesList if safeLast(series) <= n]


def highestAverage(requestContext, seriesList, n=1):
    """
    Takes one metric or a wildcard seriesList followed by an integer N.
    Out of all metrics passed, draws only the top N metrics with the highest
    average value for the time period specified.

    Example::

        &target=highestAverage(server*.instance*.threads.busy,5)

    Draws the top 5 servers with the highest average value.

    """
    return sorted(seriesList, key=safeAvg)[-n:]


def lowestAverage(requestContext, seriesList, n=1):
    """
    Takes one metric or a wildcard seriesList followed by an integer N.
    Out of all metrics passed, draws only the bottom N metrics with the lowest
    average value for the time period specified.

    Example::

        &target=lowestAverage(server*.instance*.threads.busy,5)

    Draws the bottom 5 servers with the lowest average value.

    """
    return sorted(seriesList, key=safeAvg)[:n]


def averageAbove(requestContext, seriesList, n):
    """
    Takes one metric or a wildcard seriesList followed by an integer N.
    Out of all metrics passed, draws only the metrics with an average value
    above N for the time period specified.

    Example::

        &target=averageAbove(server*.instance*.threads.busy,25)

    Draws the servers with average values above 25.

    """
    return [series for series in seriesList if safeAvg(series) >= n]


def averageBelow(requestContext, seriesList, n):
    """
    Takes one metric or a wildcard seriesList followed by an integer N.
    Out of all metrics passed, draws only the metrics with an average value
    below N for the time period specified.

    Example::

        &target=averageBelow(server*.instance*.threads.busy,25)

    Draws the servers with average values below 25.

    """
    return [series for series in seriesList if safeAvg(series) <= n]


def _getPercentile(points, n, interpolate=False):
    """
    Percentile is calculated using the method outlined in the NIST Engineering
    Statistics Handbook:
    http://www.itl.nist.gov/div898/handbook/prc/section2/prc252.htm
    """
    sortedPoints = sorted(filter(not_none, points))
    if len(sortedPoints) == 0:
        return None
    fractionalRank = (n/100.0) * (len(sortedPoints) + 1)
    rank = int(fractionalRank)
    rankFraction = fractionalRank - rank

    if not interpolate:
        rank += int(math.ceil(rankFraction))

    if rank == 0:
        percentile = sortedPoints[0]
    elif rank - 1 == len(sortedPoints):
        percentile = sortedPoints[-1]
    else:
        percentile = sortedPoints[rank - 1]  # Adjust for 0-index

    if interpolate:
        if rank != len(sortedPoints):  # if a next value exists
            nextValue = sortedPoints[rank]
            percentile = percentile + rankFraction * (nextValue - percentile)

    return percentile


def nPercentile(requestContext, seriesList, n):
    """Returns n-percent of each series in the seriesList."""
    assert n, 'The requested percent is required to be greater than 0'

    results = []
    for s in seriesList:
        # Create a sorted copy of the TimeSeries excluding None values in the
        # values list.
        s_copy = TimeSeries(s.name, s.start, s.end, s.step,
                            sorted(filter(not_none, s)))
        if not s_copy:
            continue    # Skip this series because it is empty.

        perc_val = _getPercentile(s_copy, n)
        if perc_val is not None:
            name = 'nPercentile(%s, %g)' % (s_copy.name, n)
            point_count = int((s.end - s.start)/s.step)
            perc_series = TimeSeries(name, s_copy.start, s_copy.end,
                                     s_copy.step, [perc_val] * point_count)
            perc_series.pathExpression = name
            results.append(perc_series)
    return results


def averageOutsidePercentile(requestContext, seriesList, n):
    """
    Removes functions lying inside an average percentile interval
    """
    averages = [safeAvg(s) for s in seriesList]

    if n < 50:
        n = 100 - n

    lowPercentile = _getPercentile(averages, 100 - n)
    highPercentile = _getPercentile(averages, n)

    return [s for s in seriesList
            if not lowPercentile < safeAvg(s) < highPercentile]


def removeBetweenPercentile(requestContext, seriesList, n):
    """
    Removes lines who do not have an value lying in the x-percentile of all
    the values at a moment
    """
    if n < 50:
        n = 100 - n

    transposed = list(zip(*seriesList))

    lowPercentiles = [_getPercentile(col, 100-n) for col in transposed]
    highPercentiles = [_getPercentile(col, n) for col in transposed]

    return [l for l in seriesList
            if sum([not lowPercentiles[index] < val < highPercentiles[index]
                    for index, val in enumerate(l)]) > 0]


def removeAbovePercentile(requestContext, seriesList, n):
    """
    Removes data above the nth percentile from the series or list of series
    provided. Values above this percentile are assigned a value of None.
    """
    for s in seriesList:
        s.name = 'removeAbovePercentile(%s, %d)' % (s.name, n)
        s.pathExpression = s.name
        percentile = nPercentile(requestContext, [s], n)[0][0]
        for index, val in enumerate(s):
            if val is None:
                continue
            if val > percentile:
                s[index] = None

    return seriesList


def removeAboveValue(requestContext, seriesList, n):
    """
    Removes data above the given threshold from the series or list of series
    provided. Values above this threshole are assigned a value of None.
    """
    for s in seriesList:
        s.name = 'removeAboveValue(%s, %d)' % (s.name, n)
        s.pathExpression = s.name
        for (index, val) in enumerate(s):
            if val is None:
                continue
            if val > n:
                s[index] = None

    return seriesList


def removeBelowPercentile(requestContext, seriesList, n):
    """
    Removes data below the nth percentile from the series or list of series
    provided. Values below this percentile are assigned a value of None.
    """
    for s in seriesList:
        s.name = 'removeBelowPercentile(%s, %d)' % (s.name, n)
        s.pathExpression = s.name
        percentile = nPercentile(requestContext, [s], n)[0][0]
        for (index, val) in enumerate(s):
            if val is None:
                continue
            if val < percentile:
                s[index] = None

    return seriesList


def removeBelowValue(requestContext, seriesList, n):
    """
    Removes data below the given threshold from the series or list of series
    provided. Values below this threshole are assigned a value of None.
    """
    for s in seriesList:
        s.name = 'removeBelowValue(%s, %d)' % (s.name, n)
        s.pathExpression = s.name
        for index, val in enumerate(s):
            if val is None:
                continue
            if val < n:
                s[index] = None

    return seriesList


def limit(requestContext, seriesList, n):
    """
    Takes one metric or a wildcard seriesList followed by an integer N.

    Only draw the first N metrics. Useful when testing a wildcard in a
    metric.

    Example::

        &target=limit(server*.instance*.memory.free,5)

    Draws only the first 5 instance's memory free.

    """
    return seriesList[0:n]


def sortByName(requestContext, seriesList):
    """
    Takes one metric or a wildcard seriesList.

    Sorts the list of metrics by the metric name.
    """
    return list(sorted(seriesList, key=lambda x: x.name))


def sortByTotal(requestContext, seriesList):
    """
    Takes one metric or a wildcard seriesList.

    Sorts the list of metrics by the sum of values across the time period
    specified.
    """
    return list(sorted(seriesList, key=safeSum, reverse=True))


def sortByMaxima(requestContext, seriesList):
    """
    Takes one metric or a wildcard seriesList.

    Sorts the list of metrics by the maximum value across the time period
    specified.    Useful with the &areaMode=all parameter, to keep the
    lowest value lines visible.

    Example::

        &target=sortByMaxima(server*.instance*.memory.free)

    """
    return list(sorted(seriesList, key=max))


def sortByMinima(requestContext, seriesList):
    """
    Takes one metric or a wildcard seriesList.

    Sorts the list of metrics by the lowest value across the time period
    specified.

    Example::

        &target=sortByMinima(server*.instance*.memory.free)

    """
    return list(sorted(seriesList, key=min))


def useSeriesAbove(requestContext, seriesList, value, search, replace):
    """
    Compares the maximum of each series against the given `value`. If the
    series maximum is greater than `value`, the regular expression search and
    replace is applied against the series name to plot a related metric.

    e.g. given useSeriesAbove(ganglia.metric1.reqs,10,'reqs','time'),
    the response time metric will be plotted only when the maximum value of the
    corresponding request/s metric is > 10

    Example::

        &target=useSeriesAbove(ganglia.metric1.reqs,10,"reqs","time")
    """
    from .app import evaluateTarget
    newSeries = []

    for series in seriesList:
        newname = re.sub(search, replace, series.name)
        if safeMax(series) > value:
            n = evaluateTarget(requestContext, newname)
            if n is not None and len(n) > 0:
                newSeries.append(n[0])

    return newSeries


def mostDeviant(requestContext, seriesList, n):
    """
    Takes one metric or a wildcard seriesList followed by an integer N.
    Draws the N most deviant metrics.
    To find the deviants, the standard deviation (sigma) of each series
    is taken and ranked. The top N standard deviations are returned.

    Example::

        &target=mostDeviant(server*.instance*.memory.free, 5)

    Draws the 5 instances furthest from the average memory free.
    """

    deviants = []
    for series in seriesList:
        mean = safeAvg(series)
        if mean is None:
            continue
        square_sum = sum([(value - mean) ** 2 for value in series
                          if value is not None])
        sigma = safeDiv(square_sum, safeLen(series))
        if sigma is None:
            continue
        deviants.append((sigma, series))
    return [series for sig, series in sorted(deviants,  # sort by sigma
                                             key=itemgetter(0),
                                             reverse=True)][:n]


def stdev(requestContext, seriesList, points, windowTolerance=0.1):
    """
    Takes one metric or a wildcard seriesList followed by an integer N.
    Draw the Standard Deviation of all metrics passed for the past N
    datapoints. If the ratio of null points in the window is greater than
    windowTolerance, skip the calculation. The default for windowTolerance is
    0.1 (up to 10% of points in the window can be missing). Note that if this
    is set to 0.0, it will cause large gaps in the output anywhere a single
    point is missing.

    Example::

        &target=stdev(server*.instance*.threads.busy,30)
        &target=stdev(server*.instance*.cpu.system,30,0.0)

    """

    # For this we take the standard deviation in terms of the moving average
    # and the moving average of series squares.
    for seriesIndex, series in enumerate(seriesList):
        stddevSeries = TimeSeries("stddev(%s,%d)" % (series.name, int(points)),
                                  series.start, series.end, series.step, [])
        stddevSeries.pathExpression = "stddev(%s,%d)" % (series.name,
                                                         int(points))

        validPoints = 0
        currentSum = 0
        currentSumOfSquares = 0
        for index, newValue in enumerate(series):
            # Mark whether we've reached our window size - dont drop points
            # out otherwise
            if index < points:
                bootstrapping = True
                droppedValue = None
            else:
                bootstrapping = False
                droppedValue = series[index - points]

            # Track non-None points in window
            if not bootstrapping and droppedValue is not None:
                validPoints -= 1
            if newValue is not None:
                validPoints += 1

            # Remove the value that just dropped out of the window
            if not bootstrapping and droppedValue is not None:
                currentSum -= droppedValue
                currentSumOfSquares -= droppedValue**2

            # Add in the value that just popped in the window
            if newValue is not None:
                currentSum += newValue
                currentSumOfSquares += newValue**2

            if (
                validPoints > 0 and
                float(validPoints) / points >= windowTolerance
            ):

                deviation = math.sqrt(validPoints * currentSumOfSquares
                                      - currentSum**2) / validPoints
                stddevSeries.append(deviation)
            else:
                stddevSeries.append(None)

        seriesList[seriesIndex] = stddevSeries

    return seriesList


def secondYAxis(requestContext, seriesList):
    """
    Graph the series on the secondary Y axis.
    """
    for series in seriesList:
        series.options['secondYAxis'] = True
        series.name = 'secondYAxis(%s)' % series.name
    return seriesList


def _fetchWithBootstrap(requestContext, seriesList, **delta_kwargs):
    """
    Request the same data but with a bootstrap period at the beginning.
    """
    from .app import evaluateTarget
    bootstrapContext = requestContext.copy()
    bootstrapContext['startTime'] = (
        requestContext['startTime'] - timedelta(**delta_kwargs))
    bootstrapContext['endTime'] = requestContext['startTime']

    bootstrapList = []
    for series in seriesList:
        if series.pathExpression in [b.pathExpression for b in bootstrapList]:
            # This pathExpression returns multiple series and we already
            # fetched it
            continue
        bootstraps = evaluateTarget(bootstrapContext, series.pathExpression)
        bootstrapList.extend(bootstraps)

    newSeriesList = []
    for bootstrap, original in zip(bootstrapList, seriesList):
        newValues = []
        if bootstrap.step != original.step:
            ratio = bootstrap.step / original.step
            for value in bootstrap:
                # XXX For series with aggregationMethod = sum this should also
                # divide by the ratio to bring counts to the same time unit
                # ...but we have no way of knowing whether that's the case
                newValues.extend([value] * ratio)
        else:
            newValues.extend(bootstrap)
        newValues.extend(original)

        newSeries = TimeSeries(original.name, bootstrap.start, original.end,
                               original.step, newValues)
        newSeries.pathExpression = series.pathExpression
        newSeriesList.append(newSeries)

    return newSeriesList


def _trimBootstrap(bootstrap, original):
    """
    Trim the bootstrap period off the front of this series so it matches the
    original.
    """
    original_len = len(original)
    length_limit = (original_len * original.step) // bootstrap.step
    trim_start = bootstrap.end - (length_limit * bootstrap.step)
    trimmed = TimeSeries(bootstrap.name, trim_start, bootstrap.end,
                         bootstrap.step, bootstrap[-length_limit:])
    return trimmed


def holtWintersIntercept(alpha, actual, last_season, last_intercept,
                         last_slope):
    return (alpha * (actual - last_season)
            + (1 - alpha) * (last_intercept + last_slope))


def holtWintersSlope(beta, intercept, last_intercept, last_slope):
    return beta * (intercept - last_intercept) + (1 - beta) * last_slope


def holtWintersSeasonal(gamma, actual, intercept, last_season):
    return gamma * (actual - intercept) + (1 - gamma) * last_season


def holtWintersDeviation(gamma, actual, prediction, last_seasonal_dev):
    if prediction is None:
        prediction = 0
    return (gamma * math.fabs(actual - prediction)
            + (1 - gamma) * last_seasonal_dev)


def holtWintersAnalysis(series):
    alpha = gamma = 0.1
    beta = 0.0035
    # season is currently one day
    season_length = (24 * 60 * 60) // series.step
    intercept = 0
    slope = 0
    intercepts = []
    slopes = []
    seasonals = []
    predictions = []
    deviations = []

    def getLastSeasonal(i):
        j = i - season_length
        if j >= 0:
            return seasonals[j]
        return 0

    def getLastDeviation(i):
        j = i - season_length
        if j >= 0:
            return deviations[j]
        return 0

    last_seasonal = 0
    last_seasonal_dev = 0
    next_last_seasonal = 0
    next_pred = None

    for i, actual in enumerate(series):
        if actual is None:
            # missing input values break all the math
            # do the best we can and move on
            intercepts.append(None)
            slopes.append(0)
            seasonals.append(0)
            predictions.append(next_pred)
            deviations.append(0)
            next_pred = None
            continue

        if i == 0:
            last_intercept = actual
            last_slope = 0
            # seed the first prediction as the first actual
            prediction = actual
        else:
            last_intercept = intercepts[-1]
            last_slope = slopes[-1]
            if last_intercept is None:
                last_intercept = actual
            prediction = next_pred

        last_seasonal = getLastSeasonal(i)
        next_last_seasonal = getLastSeasonal(i+1)
        last_seasonal_dev = getLastDeviation(i)

        intercept = holtWintersIntercept(alpha, actual, last_seasonal,
                                         last_intercept, last_slope)
        slope = holtWintersSlope(beta, intercept, last_intercept, last_slope)
        seasonal = holtWintersSeasonal(gamma, actual, intercept, last_seasonal)
        next_pred = intercept + slope + next_last_seasonal
        deviation = holtWintersDeviation(gamma, actual, prediction,
                                         last_seasonal_dev)

        intercepts.append(intercept)
        slopes.append(slope)
        seasonals.append(seasonal)
        predictions.append(prediction)
        deviations.append(deviation)

    # make the new forecast series
    forecastName = "holtWintersForecast(%s)" % series.name
    forecastSeries = TimeSeries(forecastName, series.start, series.end,
                                series.step, predictions)
    forecastSeries.pathExpression = forecastName

    # make the new deviation series
    deviationName = "holtWintersDeviation(%s)" % series.name
    deviationSeries = TimeSeries(deviationName, series.start, series.end,
                                 series.step, deviations)
    deviationSeries.pathExpression = deviationName

    results = {'predictions': forecastSeries,
               'deviations': deviationSeries,
               'intercepts': intercepts,
               'slopes': slopes,
               'seasonals': seasonals}
    return results


def holtWintersForecast(requestContext, seriesList):
    """
    Performs a Holt-Winters forecast using the series as input data. Data from
    one week previous to the series is used to bootstrap the initial forecast.
    """
    results = []
    bootstrapList = _fetchWithBootstrap(requestContext, seriesList, days=7)
    for bootstrap, series in zip(bootstrapList, seriesList):
        analysis = holtWintersAnalysis(bootstrap)
        results.append(_trimBootstrap(analysis['predictions'], series))
    return results


def holtWintersConfidenceBands(requestContext, seriesList, delta=3):
    """
    Performs a Holt-Winters forecast using the series as input data and plots
    upper and lower bands with the predicted forecast deviations.
    """
    results = []
    bootstrapList = _fetchWithBootstrap(requestContext, seriesList, days=7)
    for bootstrap, series in zip(bootstrapList, seriesList):
        analysis = holtWintersAnalysis(bootstrap)
        forecast = _trimBootstrap(analysis['predictions'], series)
        deviation = _trimBootstrap(analysis['deviations'], series)
        seriesLength = len(forecast)
        i = 0
        upperBand = list()
        lowerBand = list()
        while i < seriesLength:
            forecast_item = forecast[i]
            deviation_item = deviation[i]
            i = i + 1
            if forecast_item is None or deviation_item is None:
                upperBand.append(None)
                lowerBand.append(None)
            else:
                scaled_deviation = delta * deviation_item
                upperBand.append(forecast_item + scaled_deviation)
                lowerBand.append(forecast_item - scaled_deviation)

        upperName = "holtWintersConfidenceUpper(%s)" % series.name
        lowerName = "holtWintersConfidenceLower(%s)" % series.name
        upperSeries = TimeSeries(upperName, forecast.start, forecast.end,
                                 forecast.step, upperBand)
        lowerSeries = TimeSeries(lowerName, forecast.start, forecast.end,
                                 forecast.step, lowerBand)
        upperSeries.pathExpression = series.pathExpression
        lowerSeries.pathExpression = series.pathExpression
        results.append(lowerSeries)
        results.append(upperSeries)
    return results


def holtWintersAberration(requestContext, seriesList, delta=3):
    """
    Performs a Holt-Winters forecast using the series as input data and plots
    the positive or negative deviation of the series data from the forecast.
    """
    results = []
    for series in seriesList:
        confidenceBands = holtWintersConfidenceBands(requestContext, [series],
                                                     delta)
        lowerBand = confidenceBands[0]
        upperBand = confidenceBands[1]
        aberration = list()
        for i, actual in enumerate(series):
            if series[i] is None:
                aberration.append(0)
            elif upperBand[i] is not None and series[i] > upperBand[i]:
                aberration.append(series[i] - upperBand[i])
            elif lowerBand[i] is not None and series[i] < lowerBand[i]:
                aberration.append(series[i] - lowerBand[i])
            else:
                aberration.append(0)

        newName = "holtWintersAberration(%s)" % series.name
        results.append(TimeSeries(newName, series.start, series.end,
                                  series.step, aberration))
    return results


def holtWintersConfidenceArea(requestContext, seriesList, delta=3):
    """
    Performs a Holt-Winters forecast using the series as input data and plots
    the area between the upper and lower bands of the predicted forecast
    deviations.
    """
    bands = holtWintersConfidenceBands(requestContext, seriesList, delta)
    results = areaBetween(requestContext, bands)
    for series in results:
        series.name = series.name.replace('areaBetween',
                                          'holtWintersConfidenceArea')
    return results


def drawAsInfinite(requestContext, seriesList):
    """
    Takes one metric or a wildcard seriesList.
    If the value is zero, draw the line at 0. If the value is above zero, draw
    the line at infinity. If the value is null or less than zero, do not draw
    the line.

    Useful for displaying on/off metrics, such as exit codes. (0 = success,
    anything else = failure.)

    Example::

        drawAsInfinite(Testing.script.exitCode)

    """
    for series in seriesList:
        series.options['drawAsInfinite'] = True
        series.name = 'drawAsInfinite(%s)' % series.name
    return seriesList


def lineWidth(requestContext, seriesList, width):
    """
    Takes one metric or a wildcard seriesList, followed by a float F.

    Draw the selected metrics with a line width of F, overriding the default
    value of 1, or the &lineWidth=X.X parameter.

    Useful for highlighting a single metric out of many, or having multiple
    line widths in one graph.

    Example::

        &target=lineWidth(server01.instance01.memory.free,5)

    """
    for series in seriesList:
        series.options['lineWidth'] = width
    return seriesList


def dashed(requestContext, seriesList, dashLength=5):
    """
    Takes one metric or a wildcard seriesList, followed by a float F.

    Draw the selected metrics with a dotted line with segments of length F
    If omitted, the default length of the segments is 5.0

    Example::

        &target=dashed(server01.instance01.memory.free,2.5)

    """
    for series in seriesList:
        series.name = 'dashed(%s, %d)' % (series.name, dashLength)
        series.options['dashed'] = dashLength
    return seriesList


def timeStack(requestContext, seriesList, timeShiftUnit, timeShiftStart,
              timeShiftEnd):
    """
    Takes one metric or a wildcard seriesList, followed by a quoted string
    with the length of time (See ``from / until`` in the render\_api_ for
    examples of time formats). Also takes a start multiplier and end
    multiplier for the length of time-

    Create a seriesList which is composed the orginal metric series stacked
    with time shifts starting time shifts from the start multiplier through
    the end multiplier.

    Useful for looking at history, or feeding into seriesAverage or
    seriesStdDev.

    Example::

        # create a series for today and each of the previous 7 days
        &target=timeStack(Sales.widgets.largeBlue,"1d",0,7)
    """
    from .app import evaluateTarget
    # Default to negative. parseTimeOffset defaults to +
    if timeShiftUnit[0].isdigit():
        timeShiftUnit = '-' + timeShiftUnit
    delta = parseTimeOffset(timeShiftUnit)
    # if len(seriesList) > 1, they will all have the same pathExpression,
    # which is all we care about.
    series = seriesList[0]
    results = []
    timeShiftStartint = int(timeShiftStart)
    timeShiftEndint = int(timeShiftEnd)

    for shft in range(timeShiftStartint, timeShiftEndint):
        myContext = requestContext.copy()
        innerDelta = delta * shft
        myContext['startTime'] = requestContext['startTime'] + innerDelta
        myContext['endTime'] = requestContext['endTime'] + innerDelta
        for shiftedSeries in evaluateTarget(myContext, series.pathExpression):
            shiftedSeries.name = 'timeShift(%s, %s, %s)' % (shiftedSeries.name,
                                                            timeShiftUnit,
                                                            shft)
            shiftedSeries.pathExpression = shiftedSeries.name
            shiftedSeries.start = series.start
            shiftedSeries.end = series.end
            results.append(shiftedSeries)

    return results


def timeShift(requestContext, seriesList, timeShift, resetEnd=True):
    """
    Takes one metric or a wildcard seriesList, followed by a quoted string
    with the length of time (See ``from / until`` in the render\_api_ for
    examples of time formats).

    Draws the selected metrics shifted in time. If no sign is given, a minus
    sign ( - ) is implied which will shift the metric back in time. If a plus
    sign ( + ) is given, the metric will be shifted forward in time.

    Will reset the end date range automatically to the end of the base stat
    unless resetEnd is False. Example case is when you timeshift to last week
    and have the graph date range set to include a time in the future, will
    limit this timeshift to pretend ending at the current time. If resetEnd is
    False, will instead draw full range including future time.

    Useful for comparing a metric against itself at a past periods or
    correcting data stored at an offset.

    Example::

        &target=timeShift(Sales.widgets.largeBlue,"7d")
        &target=timeShift(Sales.widgets.largeBlue,"-7d")
        &target=timeShift(Sales.widgets.largeBlue,"+1h")

    """
    from .app import evaluateTarget
    # Default to negative. parseTimeOffset defaults to +
    if timeShift[0].isdigit():
        timeShift = '-' + timeShift
    delta = parseTimeOffset(timeShift)
    myContext = requestContext.copy()
    myContext['startTime'] = requestContext['startTime'] + delta
    myContext['endTime'] = requestContext['endTime'] + delta
    results = []
    if not seriesList:
        return results

    # if len(seriesList) > 1, they will all have the same pathExpression,
    # which is all we care about.
    series = seriesList[0]

    for shiftedSeries in evaluateTarget(myContext, series.pathExpression):
        shiftedSeries.name = 'timeShift(%s, %s)' % (shiftedSeries.name,
                                                    timeShift)
        if resetEnd:
            shiftedSeries.end = series.end
        else:
            shiftedSeries.end = (
                shiftedSeries.end - shiftedSeries.start + series.start)
        shiftedSeries.start = series.start
        results.append(shiftedSeries)

    return results


def constantLine(requestContext, value):
    """
    Takes a float F.

    Draws a horizontal line at value F across the graph.

    Example::

        &target=constantLine(123.456)

    """
    start = int(epoch(requestContext['startTime']))
    end = int(epoch(requestContext['endTime']))
    step = end - start
    series = TimeSeries(str(value), start, end, step, [value, value])
    series.pathExpression = 'constantLine({0})'.format(value)
    return [series]


def aggregateLine(requestContext, seriesList, func='avg'):
    """
    Draws a horizontal line based the function applied to the series.

    Note: By default, the graphite renderer consolidates data points by
    averaging data points over time. If you are using the 'min' or 'max'
    function for aggregateLine, this can cause an unusual gap in the
    line drawn by this function and the data itself. To fix this, you
    should use the consolidateBy() function with the same function
    argument you are using for aggregateLine. This will ensure that the
    proper data points are retained and the graph should line up
    correctly.

    Example::

        &target=aggregateLineSeries(server.connections.total, 'avg')

    """
    t_funcs = {'avg': safeAvg, 'min': safeMin, 'max': safeMax}

    if func not in t_funcs:
        raise ValueError("Invalid function %s" % func)

    results = []
    for series in seriesList:
        value = t_funcs[func](series)
        name = 'aggregateLine(%s,%d)' % (series.pathExpression, value)

        [series] = constantLine(requestContext, value)
        series.name = name
        results.append(series)
    return results


def threshold(requestContext, value, label=None, color=None):
    """
    Takes a float F, followed by a label (in double quotes) and a color.
    (See ``bgcolor`` in the render\_api_ for valid color names & formats.)

    Draws a horizontal line at value F across the graph.

    Example::

        &target=threshold(123.456, "omgwtfbbq", red)

    """

    [series] = constantLine(requestContext, value)
    if label:
        series.name = label
    if color:
        series.color = color

    return [series]


def transformNull(requestContext, seriesList, default=0):
    """
    Takes a metric or wild card seriesList and an optional value
    to transform Nulls to. Default is 0. This method compliments
    drawNullAsZero flag in graphical mode but also works in text only
    mode.

    Example::

        &target=transformNull(webapp.pages.*.views,-1)

    This would take any page that didn't have values and supply negative 1 as
    a default. Any other numeric value may be used as well.
    """
    def transform(v):
        if v is None:
            return default
        else:
            return v

    for series in seriesList:
        series.name = "transformNull(%s,%g)" % (series.name, default)
        series.pathExpression = series.name
        values = [transform(v) for v in series]
        series.extend(values)
        del series[:len(values)]
    return seriesList


def isNonNull(requestContext, seriesList):
    """
    Takes a metric or wild card seriesList and counts up how many
    non-null values are specified. This is useful for understanding
    which metrics have data at a given point in time (ie, to count
    which servers are alive).

    Example::

        &target=isNonNull(webapp.pages.*.views)

    Returns a seriesList where 1 is specified for non-null values, and
    0 is specified for null values.
    """

    def transform(v):
        if v is None:
            return 0
        else:
            return 1

    for series in seriesList:
        series.name = "isNonNull(%s)" % (series.name)
        series.pathExpression = series.name
        values = [transform(v) for v in series]
        series.extend(values)
        del series[:len(values)]
    return seriesList


def identity(requestContext, name):
    """
    Identity function:
    Returns datapoints where the value equals the timestamp of the datapoint.
    Useful when you have another series where the value is a timestamp, and
    you want to compare it to the time of the datapoint, to render an age

    Example::

        &target=identity("The.time.series")

    This would create a series named "The.time.series" that contains points
    where x(t) == t.
    """
    step = 60
    start = int(epoch(requestContext["startTime"]))
    end = int(epoch(requestContext["endTime"]))
    values = range(start, end, step)
    series = TimeSeries(name, start, end, step, values)
    series.pathExpression = 'identity("%s")' % name

    return [series]


def countSeries(requestContext, *seriesLists):
    """
    Draws a horizontal line representing the number of nodes found in the
    seriesList.

    Example::

        &target=countSeries(carbon.agents.*.*)

    """
    seriesList, start, end, step = normalize(seriesLists)
    name = "countSeries(%s)" % formatPathExpressions(seriesList)
    values = (int(len(row)) for row in zip(*seriesList))
    series = TimeSeries(name, start, end, step, values)
    series.pathExpression = name
    return [series]


def group(requestContext, *seriesLists):
    """
    Takes an arbitrary number of seriesLists and adds them to a single
    seriesList. This is used to pass multiple seriesLists to a function which
    only takes one.
    """
    seriesGroup = []
    for s in seriesLists:
        seriesGroup.extend(s)

    return seriesGroup


def mapSeries(requestContext, seriesList, mapNode):
    """
    Takes a seriesList and maps it to a list of sub-seriesList. Each
    sub-seriesList has the given mapNode in common.

    Example::

        map(servers.*.cpu.*,1) =>
            [
                servers.server1.cpu.*,
                servers.server2.cpu.*,
                ...
                servers.serverN.cpu.*
            ]
    """
    metaSeries = {}
    keys = []
    for series in seriesList:
        key = series.name.split(".")[mapNode]
        if key not in metaSeries:
            metaSeries[key] = [series]
            keys.append(key)
        else:
            metaSeries[key].append(series)
    return [metaSeries[k] for k in keys]


def reduceSeries(requestContext, seriesLists, reduceFunction, reduceNode,
                 *reduceMatchers):
    """
    Takes a list of seriesLists and reduces it to a list of series by means of
    the reduceFunction.

    Reduction is performed by matching the reduceNode in each series against
    the list of reduceMatchers. The each series is then passed to the
    reduceFunction as arguments in the order given by reduceMatchers. The
    reduceFunction should yield a single series.

    Example::

        reduce(map(servers.*.disk.*,1),3,"asPercent",
               "bytes_used","total_bytes") =>

            asPercent(servers.server1.disk.bytes_used,
                      servers.server1.disk.total_bytes),
            asPercent(servers.server2.disk.bytes_used,
                      servers.server2.disk.total_bytes),
            ...
            asPercent(servers.serverN.disk.bytes_used,
                      servers.serverN.disk.total_bytes)

    The resulting list of series are aliased so that they can easily be nested
    in other functions. In the above example, the resulting series names would
    become::

        servers.server1.disk.reduce.asPercent,
        servers.server2.disk.reduce.asPercent,
        ...
        servers.serverN.disk.reduce.asPercent
    """
    from .app import app
    metaSeries = {}
    keys = []
    for seriesList in seriesLists:
        for series in seriesList:
            nodes = series.name.split('.')
            node = nodes[reduceNode]
            reduceSeriesName = '.'.join(
                nodes[0:reduceNode]) + '.reduce.' + reduceFunction
            if node in reduceMatchers:
                if reduceSeriesName not in metaSeries:
                    metaSeries[reduceSeriesName] = [None] * len(reduceMatchers)
                    keys.append(reduceSeriesName)
                i = reduceMatchers.index(node)
                metaSeries[reduceSeriesName][i] = series
    for key in keys:
        metaSeries[key] = app.functions[reduceFunction](requestContext,
                                                        metaSeries[key])[0]
        metaSeries[key].name = key
    return [metaSeries[key] for key in keys]


def groupByNode(requestContext, seriesList, nodeNum, callback):
    """
    Takes a serieslist and maps a callback to subgroups within as defined by a
    common node.

    Example::

        &target=groupByNode(ganglia.by-function.*.*.cpu.load5,2,"sumSeries")

    Would return multiple series which are each the result of applying the
    "sumSeries" function to groups joined on the second node (0 indexed)
    resulting in a list of targets like::

        sumSeries(ganglia.by-function.server1.*.cpu.load5),
        sumSeries(ganglia.by-function.server2.*.cpu.load5),...

    """
    from .app import app
    metaSeries = {}
    keys = []
    for series in seriesList:
        key = series.name.split(".")[nodeNum]
        if key not in metaSeries:
            metaSeries[key] = [series]
            keys.append(key)
        else:
            metaSeries[key].append(series)
    for key in metaSeries.keys():
        metaSeries[key] = app.functions[callback](requestContext,
                                                  metaSeries[key])[0]
        metaSeries[key].name = key
    return [metaSeries[key] for key in keys]


def exclude(requestContext, seriesList, pattern):
    """
    Takes a metric or a wildcard seriesList, followed by a regular expression
    in double quotes.    Excludes metrics that match the regular expression.

    Example::

        &target=exclude(servers*.instance*.threads.busy,"server02")
    """
    regex = re.compile(pattern)
    return [s for s in seriesList if not regex.search(s.name)]


def grep(requestContext, seriesList, pattern):
    """
    Takes a metric or a wildcard seriesList, followed by a regular expression
    in double quotes. Excludes metrics that don't match the regular
    expression.

    Example::

        &target=grep(servers*.instance*.threads.busy,"server02")
    """
    regex = re.compile(pattern)
    return [s for s in seriesList if regex.search(s.name)]


def smartSummarize(requestContext, seriesList, intervalString, func='sum'):
    """
    Smarter experimental version of summarize.
    """
    from .app import evaluateTarget
    results = []
    delta = parseTimeOffset(intervalString)
    interval = to_seconds(delta)

    # Adjust the start time to fit an entire day for intervals >= 1 day
    requestContext = requestContext.copy()
    s = requestContext['startTime']
    if interval >= DAY:
        requestContext['startTime'] = datetime(s.year, s.month, s.day)
    elif interval >= HOUR:
        requestContext['startTime'] = datetime(s.year, s.month, s.day, s.hour)
    elif interval >= MINUTE:
        requestContext['startTime'] = datetime(s.year, s.month, s.day, s.hour,
                                               s.minute)

    for i, series in enumerate(seriesList):
        # XXX: breaks with summarize(metric.{a,b})
        #            each series.pathExpression == metric.{a,b}
        newSeries = evaluateTarget(requestContext, series.pathExpression)[0]
        series[0:len(series)] = newSeries
        series.start = newSeries.start
        series.end = newSeries.end
        series.step = newSeries.step

    for series in seriesList:
        buckets = {}  # {timestamp: [values]}

        timestamps = range(int(series.start), int(series.end),
                           int(series.step))
        datapoints = zip(timestamps, series)

        # Populate buckets
        for timestamp, value in datapoints:
            bucketInterval = int((timestamp - series.start) / interval)

            if bucketInterval not in buckets:
                buckets[bucketInterval] = []

            if value is not None:
                buckets[bucketInterval].append(value)

        newValues = []
        for timestamp in range(series.start, series.end, interval):
            bucketInterval = int((timestamp - series.start) / interval)
            bucket = buckets.get(bucketInterval, [])

            if bucket:
                if func == 'avg':
                    newValues.append(float(sum(bucket)) / float(len(bucket)))
                elif func == 'last':
                    newValues.append(bucket[len(bucket)-1])
                elif func == 'max':
                    newValues.append(max(bucket))
                elif func == 'min':
                    newValues.append(min(bucket))
                else:
                    newValues.append(sum(bucket))
            else:
                newValues.append(None)

        newName = "smartSummarize(%s, \"%s\", \"%s\")" % (series.name,
                                                          intervalString,
                                                          func)
        alignedEnd = series.start + (bucketInterval * interval) + interval
        newSeries = TimeSeries(newName, series.start, alignedEnd, interval,
                               newValues)
        newSeries.pathExpression = newName
        results.append(newSeries)

    return results


def summarize(requestContext, seriesList, intervalString, func='sum',
              alignToFrom=False):
    """
    Summarize the data into interval buckets of a certain size.

    By default, the contents of each interval bucket are summed together.
    This is useful for counters where each increment represents a discrete
    event and retrieving a "per X" value requires summing all the events in
    that interval.

    Specifying 'avg' instead will return the mean for each bucket, which can
    be more useful when the value is a gauge that represents a certain value
    in time.

    'max', 'min' or 'last' can also be specified.

    By default, buckets are caculated by rounding to the nearest interval. This
    works well for intervals smaller than a day. For example, 22:32 will end up
    in the bucket 22:00-23:00 when the interval=1hour.

    Passing alignToFrom=true will instead create buckets starting at the from
    time. In this case, the bucket for 22:32 depends on the from time. If
    from=6:30 then the 1hour bucket for 22:32 is 22:30-23:30.

    Example::

        # total errors per hour
        &target=summarize(counter.errors, "1hour")

        # new users per week
        &target=summarize(nonNegativeDerivative(gauge.num_users), "1week")

        # average queue size per hour
        &target=summarize(queue.size, "1hour", "avg")

        # maximum queue size during each hour
        &target=summarize(queue.size, "1hour", "max")

        # 2010 Q1-4
        &target=summarize(metric, "13week", "avg", true)&from=midnight+20100101
    """
    results = []
    delta = parseTimeOffset(intervalString)
    interval = to_seconds(delta)

    for series in seriesList:
        buckets = {}

        timestamps = range(int(series.start), int(series.end),
                           int(series.step))
        datapoints = zip(timestamps, series)

        for timestamp, value in datapoints:
            if alignToFrom:
                bucketInterval = int((timestamp - series.start) / interval)
            else:
                bucketInterval = timestamp - (timestamp % interval)

            if bucketInterval not in buckets:
                buckets[bucketInterval] = []

            if value is not None:
                buckets[bucketInterval].append(value)

        if alignToFrom:
            newStart = series.start
            newEnd = series.end
        else:
            newStart = series.start - (series.start % interval)
            newEnd = series.end - (series.end % interval) + interval

        newValues = []
        for timestamp in range(newStart, newEnd, interval):
            if alignToFrom:
                newEnd = timestamp
                bucketInterval = int((timestamp - series.start) / interval)
            else:
                bucketInterval = timestamp - (timestamp % interval)

            bucket = buckets.get(bucketInterval, [])

            if bucket:
                if func == 'avg':
                    newValues.append(float(sum(bucket)) / float(len(bucket)))
                elif func == 'last':
                    newValues.append(bucket[len(bucket)-1])
                elif func == 'max':
                    newValues.append(max(bucket))
                elif func == 'min':
                    newValues.append(min(bucket))
                else:
                    newValues.append(sum(bucket))
            else:
                newValues.append(None)

        if alignToFrom:
            newEnd += interval

        newName = "summarize(%s, \"%s\", \"%s\"%s)" % (
            series.name, intervalString, func, alignToFrom and ", true" or "")
        newSeries = TimeSeries(newName, newStart, newEnd, interval, newValues)
        newSeries.pathExpression = newName
        results.append(newSeries)

    return results


def hitcount(requestContext, seriesList, intervalString,
             alignToInterval=False):
    """
    Estimate hit counts from a list of time series.

    This function assumes the values in each time series represent
    hits per second.    It calculates hits per some larger interval
    such as per day or per hour.    This function is like summarize(),
    except that it compensates automatically for different time scales
    (so that a similar graph results from using either fine-grained
    or coarse-grained records) and handles rarely-occurring events
    gracefully.
    """
    from .app import evaluateTarget
    results = []
    delta = parseTimeOffset(intervalString)
    interval = to_seconds(delta)

    if alignToInterval:
        requestContext = requestContext.copy()
        s = requestContext['startTime']
        if interval >= DAY:
            requestContext['startTime'] = datetime(s.year, s.month, s.day)
        elif interval >= HOUR:
            requestContext['startTime'] = datetime(s.year, s.month, s.day,
                                                   s.hour)
        elif interval >= MINUTE:
            requestContext['startTime'] = datetime(s.year, s.month, s.day,
                                                   s.hour, s.minute)

        for i, series in enumerate(seriesList):
            newSeries = evaluateTarget(requestContext,
                                       series.pathExpression)[0]
            intervalCount = int((series.end - series.start) / interval)
            series[0:len(series)] = newSeries
            series.start = newSeries.start
            series.end = newSeries.start + (
                intervalCount * interval) + interval
            series.step = newSeries.step

    for series in seriesList:
        step = int(series.step)
        bucket_count = int(math.ceil(
            float(series.end - series.start) / interval))
        buckets = [[] for _ in range(bucket_count)]
        newStart = int(series.end - bucket_count * interval)

        for i, value in enumerate(series):
            if value is None:
                continue

            start_time = int(series.start + i * step)
            start_bucket, start_mod = divmod(start_time - newStart, interval)
            end_time = start_time + step
            end_bucket, end_mod = divmod(end_time - newStart, interval)

            if end_bucket >= bucket_count:
                end_bucket = bucket_count - 1
                end_mod = interval

            if start_bucket == end_bucket:
                # All of the hits go to a single bucket.
                if start_bucket >= 0:
                    buckets[start_bucket].append(value * (end_mod - start_mod))

            else:
                # Spread the hits among 2 or more buckets.
                if start_bucket >= 0:
                    buckets[start_bucket].append(
                        value * (interval - start_mod))
                hits_per_bucket = value * interval
                for j in range(start_bucket + 1, end_bucket):
                    buckets[j].append(hits_per_bucket)
                if end_mod > 0:
                    buckets[end_bucket].append(value * end_mod)

        newValues = []
        for bucket in buckets:
            if bucket:
                newValues.append(sum(bucket))
            else:
                newValues.append(None)

        newName = 'hitcount(%s, "%s"%s)' % (series.name, intervalString,
                                            alignToInterval and ", true" or "")
        newSeries = TimeSeries(newName, newStart, series.end, interval,
                               newValues)
        newSeries.pathExpression = newName
        results.append(newSeries)

    return results


def sinFunction(requestContext, name, amplitude=1):
    """
    Short Alias: sin()

    Just returns the sine of the current time. The optional amplitude parameter
    changes the amplitude of the wave.

    Example::

        &target=sin("The.time.series", 2)

    This would create a series named "The.time.series" that contains sin(x)*2.
    """
    step = 60
    delta = timedelta(seconds=step)
    when = requestContext["startTime"]
    values = []

    while when < requestContext["endTime"]:
        values.append(math.sin(epoch(when))*amplitude)
        when += delta

    series = TimeSeries(
        name, int(epoch(requestContext["startTime"])),
        int(epoch(requestContext["endTime"])),
        step, values)
    series.pathExpression = 'sin({0})'.format(name)
    return [series]


def randomWalkFunction(requestContext, name):
    """
    Short Alias: randomWalk()

    Returns a random walk starting at 0. This is great for testing when there
    is no real data in whisper.

    Example::

        &target=randomWalk("The.time.series")

    This would create a series named "The.time.series" that contains points
    where x(t) == x(t-1)+random()-0.5, and x(0) == 0.
    """
    step = 60
    delta = timedelta(seconds=step)
    when = requestContext["startTime"]
    values = []
    current = 0
    while when < requestContext["endTime"]:
        values.append(current)
        current += random.random() - 0.5
        when += delta

    return [TimeSeries(
        name, int(epoch(requestContext["startTime"])),
        int(epoch(requestContext["endTime"])),
        step, values)]


def pieAverage(requestContext, series):
    return safeAvg(series)


def pieMaximum(requestContext, series):
    return safeMax(series)


def pieMinimum(requestContext, series):
    return safeMin(series)


PieFunctions = {
    'average': pieAverage,
    'maximum': pieMaximum,
    'minimum': pieMinimum,
}

SeriesFunctions = {
    # Combine functions
    'sumSeries': sumSeries,
    'sum': sumSeries,
    'multiplySeries': multiplySeries,
    'averageSeries': averageSeries,
    'stddevSeries': stddevSeries,
    'avg': averageSeries,
    'sumSeriesWithWildcards': sumSeriesWithWildcards,
    'averageSeriesWithWildcards': averageSeriesWithWildcards,
    'minSeries': minSeries,
    'maxSeries': maxSeries,
    'rangeOfSeries': rangeOfSeries,
    'percentileOfSeries': percentileOfSeries,
    'countSeries': countSeries,
    'weightedAverage': weightedAverage,

    # Transform functions
    'scale': scale,
    'invert': invert,
    'scaleToSeconds': scaleToSeconds,
    'offset': offset,
    'offsetToZero': offsetToZero,
    'derivative': derivative,
    'perSecond': perSecond,
    'integral': integral,
    'percentileOfSeries': percentileOfSeries,
    'nonNegativeDerivative': nonNegativeDerivative,
    'log': logarithm,
    'timeStack': timeStack,
    'timeShift': timeShift,
    'summarize': summarize,
    'smartSummarize': smartSummarize,
    'hitcount': hitcount,
    'absolute': absolute,

    # Calculate functions
    'movingAverage': movingAverage,
    'movingMedian': movingMedian,
    'stdev': stdev,
    'holtWintersForecast': holtWintersForecast,
    'holtWintersConfidenceBands': holtWintersConfidenceBands,
    'holtWintersConfidenceArea': holtWintersConfidenceArea,
    'holtWintersAberration': holtWintersAberration,
    'asPercent': asPercent,
    'pct': asPercent,
    'diffSeries': diffSeries,
    'divideSeries': divideSeries,

    # Series Filter functions
    'mostDeviant': mostDeviant,
    'highestCurrent': highestCurrent,
    'lowestCurrent': lowestCurrent,
    'highestMax': highestMax,
    'currentAbove': currentAbove,
    'currentBelow': currentBelow,
    'highestAverage': highestAverage,
    'lowestAverage': lowestAverage,
    'averageAbove': averageAbove,
    'averageBelow': averageBelow,
    'maximumAbove': maximumAbove,
    'minimumAbove': minimumAbove,
    'maximumBelow': maximumBelow,
    'nPercentile': nPercentile,
    'limit': limit,
    'sortByTotal': sortByTotal,
    'sortByName': sortByName,
    'averageOutsidePercentile': averageOutsidePercentile,
    'removeBetweenPercentile': removeBetweenPercentile,
    'sortByMaxima': sortByMaxima,
    'sortByMinima': sortByMinima,
    'useSeriesAbove': useSeriesAbove,
    'exclude': exclude,

    # Data Filter functions
    'removeAbovePercentile': removeAbovePercentile,
    'removeAboveValue': removeAboveValue,
    'removeBelowPercentile': removeBelowPercentile,
    'removeBelowValue': removeBelowValue,

    # Special functions
    'legendValue': legendValue,
    'alias': alias,
    'aliasSub': aliasSub,
    'aliasByNode': aliasByNode,
    'aliasByMetric': aliasByMetric,
    'cactiStyle': cactiStyle,
    'color': color,
    'alpha': alpha,
    'cumulative': cumulative,
    'consolidateBy': consolidateBy,
    'keepLastValue': keepLastValue,
    'drawAsInfinite': drawAsInfinite,
    'secondYAxis': secondYAxis,
    'lineWidth': lineWidth,
    'dashed': dashed,
    'substr': substr,
    'group': group,
    'map': mapSeries,
    'reduce': reduceSeries,
    'groupByNode': groupByNode,
    'constantLine': constantLine,
    'stacked': stacked,
    'areaBetween': areaBetween,
    'threshold': threshold,
    'transformNull': transformNull,
    'isNonNull': isNonNull,
    'identity': identity,
    'aggregateLine': aggregateLine,

    # test functions
    'time': identity,
    "sin": sinFunction,
    "randomWalk": randomWalkFunction,
    'timeFunction': identity,
    "sinFunction": sinFunction,
    "randomWalkFunction": randomWalkFunction,
}

########NEW FILE########
__FILENAME__ = intervals
INFINITY = float('inf')
NEGATIVE_INFINITY = -INFINITY


class IntervalSet(object):
    __slots__ = ('intervals', 'size')

    def __init__(self, intervals, disjoint=False):
        self.intervals = intervals

        if not disjoint:
            self.intervals = union_overlapping(self.intervals)

        self.size = sum(i.size for i in self.intervals)

    def __repr__(self):
        return repr(self.intervals)

    def __eq__(self, other):
        return self.intervals == other.intervals

    def __iter__(self):
        return iter(self.intervals)

    def __bool__(self):
        return self.size != 0
    __nonzero__ = __bool__  # python 2

    def __sub__(self, other):
        return self.intersect(other.complement())

    def complement(self):
        complementary = []
        cursor = NEGATIVE_INFINITY

        for interval in self.intervals:
            if cursor < interval.start:
                complementary.append(Interval(cursor, interval.start))
                cursor = interval.end

        if cursor < INFINITY:
            complementary.append(Interval(cursor, INFINITY))

        return IntervalSet(complementary, disjoint=True)

    def intersect(self, other):
        # XXX The last major bottleneck. Factorial-time hell.
        # Then again, this function is entirely unused...
        if not self or not other:
            return IntervalSet([])

        intersections = [x for x in (i.intersect(j)
                                     for i in self.intervals
                                     for j in other.intervals)
                         if x]

        return IntervalSet(intersections, disjoint=True)

    def intersect_interval(self, interval):
        intersections = [x for x in (i.intersect(interval)
                                     for i in self.intervals)
                         if x]
        return IntervalSet(intersections, disjoint=True)

    def union(self, other):
        return IntervalSet(sorted(self.intervals + other.intervals))


class Interval(object):
    __slots__ = ('start', 'end', 'tuple', 'size')

    def __init__(self, start, end):
        if end - start < 0:
            raise ValueError("Invalid interval start=%s end=%s" % (start, end))

        self.start = start
        self.end = end
        self.tuple = (start, end)
        self.size = self.end - self.start

    def __eq__(self, other):
        return self.tuple == other.tuple

    def __hash__(self):
        return hash(self.tuple)

    def __lt__(self, other):
        return (self.start < other.start) - (self.start > other.start)

    def __len__(self):
        raise TypeError("len() doesn't support infinite values, use the "
                        "'size' attribute instead")

    def __bool__(self):
        return self.size != 0
    __nonzero__ = __bool__  # python 2

    def __repr__(self):
        return '<Interval: %s>' % str(self.tuple)

    def intersect(self, other):
        start = max(self.start, other.start)
        end = min(self.end, other.end)

        if end > start:
            return Interval(start, end)

    def overlaps(self, other):
        earlier = self if self.start <= other.start else other
        later = self if earlier is other else other
        return earlier.end >= later.start

    def union(self, other):
        if not self.overlaps(other):
            raise TypeError("Union of disjoint intervals is not an interval")

        start = min(self.start, other.start)
        end = max(self.end, other.end)
        return Interval(start, end)


def union_overlapping(intervals):
    """Union any overlapping intervals in the given set."""
    disjoint_intervals = []

    for interval in intervals:
        if disjoint_intervals and disjoint_intervals[-1].overlaps(interval):
            disjoint_intervals[-1] = disjoint_intervals[-1].union(interval)
        else:
            disjoint_intervals.append(interval)

    return disjoint_intervals

########NEW FILE########
__FILENAME__ = middleware
from six.moves.urllib.parse import urlparse


class CORS(object):
    """
    Simple middleware that adds CORS headers.
    """
    def __init__(self, app, origins=None):
        self.app = app
        self.origins = origins

    def __call__(self, environ, start_response):
        origin = environ.get('HTTP_ORIGIN')
        if origin is None or self.origins is None:
            return self.app(environ, start_response)

        netloc = urlparse(origin).netloc
        if netloc in self.origins:
            allow_origin = [
                ('Access-Control-Allow-Origin', origin),
                ('Access-Control-Allow-Credentials', 'true'),
            ]
            if environ['REQUEST_METHOD'] == 'OPTIONS':
                start_response('204 No Content', allow_origin)
                return []

            def custom_start_response(status, headers, exc_info=None):
                headers.extend(allow_origin)
                return start_response(status, headers, exc_info)
        else:
            custom_start_response = start_response
        return self.app(environ, custom_start_response)


class TrailingSlash(object):
    """
    Middleware that strips trailing slashes from URLs.
    """
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        path_info = environ['PATH_INFO']
        if len(path_info) > 1 and path_info.endswith('/'):
            environ['PATH_INFO'] = path_info.rstrip('/')
        return self.app(environ, start_response)

########NEW FILE########
__FILENAME__ = node
class Node(object):
    __slots__ = ('name', 'path', 'local', 'is_leaf')

    def __init__(self, path):
        self.path = path
        self.name = path.split('.')[-1]
        self.local = True
        self.is_leaf = False

    def __repr__(self):
        return '<%s[%x]: %s>' % (self.__class__.__name__, id(self), self.path)


class BranchNode(Node):
    pass


class LeafNode(Node):
    __slots__ = ('reader', 'intervals')

    def __init__(self, path, reader):
        super(LeafNode, self).__init__(path)
        self.reader = reader
        self.intervals = reader.get_intervals()
        self.is_leaf = True

    def fetch(self, startTime, endTime):
        return self.reader.fetch(startTime, endTime)

    def __repr__(self):
        return '<LeafNode[%x]: %s (%s)>' % (id(self), self.path, self.reader)

########NEW FILE########
__FILENAME__ = readers
from .intervals import IntervalSet


class MultiReader(object):
    __slots__ = ('nodes',)

    def __init__(self, nodes):
        self.nodes = nodes

    def get_intervals(self):
        interval_sets = []
        for node in self.nodes:
            interval_sets.extend(node.intervals.intervals)
        return IntervalSet(sorted(interval_sets))

    def fetch(self, startTime, endTime):
        # Start the fetch on each node
        results = [n.fetch(startTime, endTime) for n in self.nodes]

        data = None
        for r in filter(None, results):
            if data is None:
                data = r
            else:
                data = self.merge(data, r)
        if data is None:
            raise Exception("All sub-fetches failed")
        return data

    def merge(self, results1, results2):
        # Ensure results1 is finer than results2
        if results1[0][2] > results2[0][2]:
            results1, results2 = results2, results1

        time_info1, values1 = results1
        time_info2, values2 = results2
        start1, end1, step1 = time_info1
        start2, end2, step2 = time_info2

        step = step1  # finest step
        start = min(start1, start2)  # earliest start
        end = max(end1, end2)  # latest end
        time_info = start, end, step
        values = []

        t = start
        while t < end:
            # Look for the finer precision value first if available
            i1 = (t - start1) / step1

            if len(values1) > i1:
                v1 = values1[i1]
            else:
                v1 = None

            if v1 is None:
                i2 = (t - start2) / step2

                if len(values2) > i2:
                    v2 = values2[i2]
                else:
                    v2 = None

                values.append(v2)
            else:
                values.append(v1)

            t += step

        return (time_info, values)

########NEW FILE########
__FILENAME__ = attime
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""
import pytz

from datetime import datetime, timedelta
from time import daylight

months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
          'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
weekdays = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']


def parseATTime(s, tzinfo=None):
    if tzinfo is None:
        from ..app import app
        tzinfo = pytz.timezone(app.config['TIME_ZONE'])
    s = s.strip().lower().replace('_', '').replace(',', '').replace(' ', '')
    if s.isdigit():
        if (
            len(s) == 8 and
            int(s[:4]) > 1900 and
            int(s[4:6]) < 13 and
            int(s[6:]) < 32
        ):
            pass  # Fall back because its not a timestamp, its YYYYMMDD form
        else:
            return datetime.fromtimestamp(int(s), tzinfo)
    elif ':' in s and len(s) == 13:
        return tzinfo.localize(datetime.strptime(s, '%H:%M%Y%m%d'), daylight)
    if '+' in s:
        ref, offset = s.split('+', 1)
        offset = '+' + offset
    elif '-' in s:
        ref, offset = s.split('-', 1)
        offset = '-' + offset
    else:
        ref, offset = s, ''
    return (parseTimeReference(ref) +
            parseTimeOffset(offset)).astimezone(tzinfo)


def parseTimeReference(ref):
    if not ref or ref == 'now':
        return datetime.utcnow().replace(tzinfo=pytz.utc)

    # Time-of-day reference
    i = ref.find(':')
    hour, min = 0, 0
    if i != -1:
        hour = int(ref[:i])
        min = int(ref[i+1:i+3])
        ref = ref[i+3:]
        if ref[:2] == 'am':
            ref = ref[2:]
        elif ref[:2] == 'pm':
            hour = (hour + 12) % 24
            ref = ref[2:]
    if ref.startswith('noon'):
        hour, min = 12, 0
        ref = ref[4:]
    elif ref.startswith('midnight'):
        hour, min = 0, 0
        ref = ref[8:]
    elif ref.startswith('teatime'):
        hour, min = 16, 0
        ref = ref[7:]

    refDate = datetime.utcnow().replace(hour=hour, minute=min, second=0,
                                        tzinfo=pytz.utc)

    # Day reference
    if ref in ('yesterday', 'today', 'tomorrow'):  # yesterday, today, tomorrow
        if ref == 'yesterday':
            refDate = refDate - timedelta(days=1)
        if ref == 'tomorrow':
            refDate = refDate + timedelta(days=1)
    elif ref.count('/') == 2:  # MM/DD/YY[YY]
        m, d, y = map(int, ref.split('/'))
        if y < 1900:
            y += 1900
        if y < 1970:
            y += 100
        refDate = refDate.replace(year=y)
        refDate = replace_date(refDate, m, d)

    elif len(ref) == 8 and ref.isdigit():  # YYYYMMDD
        refDate = refDate.replace(year=int(ref[:4]))
        refDate = replace_date(refDate, int(ref[4:6]), int(ref[6:8]))

    elif ref[:3] in months:  # MonthName DayOfMonth
        month = months.index(ref[:3]) + 1
        if ref[-2:].isdigit():
            day = int(ref[-2])
        elif ref[-1:].isdigit():
            day = int(ref[-1:])
        else:
            raise Exception("Day of month required after month name")
        refDate = replace_date(refDate, month, day)
    elif ref[:3] in weekdays:  # DayOfWeek (Monday, etc)
        todayDayName = refDate.strftime("%a").lower()[:3]
        today = weekdays.index(todayDayName)
        twoWeeks = weekdays * 2
        dayOffset = today - twoWeeks.index(ref[:3])
        if dayOffset < 0:
            dayOffset += 7
        refDate -= timedelta(days=dayOffset)
    elif ref:
        raise Exception("Unknown day reference")
    return refDate


def replace_date(date, month, day):
    try:
        date = date.replace(month=month)
        date = date.replace(day=day)
    except ValueError:  # day out of range for month, or vice versa
        date = date.replace(day=day)
        date = date.replace(month=month)
    return date


def parseTimeOffset(offset):
    if not offset:
        return timedelta()

    t = timedelta()

    if offset[0].isdigit():
        sign = 1
    else:
        sign = {'+': 1, '-': -1}[offset[0]]
        offset = offset[1:]

    while offset:
        i = 1
        while offset[:i].isdigit() and i <= len(offset):
            i += 1
        num = int(offset[:i-1])
        offset = offset[i-1:]
        i = 1
        while offset[:i].isalpha() and i <= len(offset):
            i += 1
        unit = offset[:i-1]
        offset = offset[i-1:]
        unitString = getUnitString(unit)
        if unitString == 'months':
            unitString = 'days'
            num = num * 30
        if unitString == 'years':
            unitString = 'days'
            num = num * 365
        t += timedelta(**{unitString: sign * num})

    return t


def getUnitString(s):
    if s.startswith('s'):
        return 'seconds'
    if s.startswith('min'):
        return 'minutes'
    if s.startswith('h'):
        return 'hours'
    if s.startswith('d'):
        return 'days'
    if s.startswith('w'):
        return 'weeks'
    if s.startswith('mon'):
        return 'months'
    if s.startswith('y'):
        return 'years'
    raise Exception("Invalid offset unit '%s'" % s)

########NEW FILE########
__FILENAME__ = datalib
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""
from collections import defaultdict
from structlog import get_logger

from ..utils import epoch

logger = get_logger()


class TimeSeries(list):
    def __init__(self, name, start, end, step, values, consolidate='average'):
        list.__init__(self, values)
        self.name = name
        self.start = start
        self.end = end
        self.step = step
        self.consolidationFunc = consolidate
        self.valuesPerPoint = 1
        self.options = {}

    def __iter__(self):
        if self.valuesPerPoint > 1:
            return self.__consolidatingGenerator(list.__iter__(self))
        else:
            return list.__iter__(self)

    def consolidate(self, valuesPerPoint):
        self.valuesPerPoint = int(valuesPerPoint)

    def __consolidatingGenerator(self, gen):
        buf = []
        for x in gen:
            buf.append(x)
            if len(buf) == self.valuesPerPoint:
                while None in buf:
                    buf.remove(None)
                if buf:
                    yield self.__consolidate(buf)
                    buf = []
                else:
                    yield None
        while None in buf:
            buf.remove(None)
        if buf:
            yield self.__consolidate(buf)
        else:
            yield None
        raise StopIteration

    def __consolidate(self, values):
        usable = [v for v in values if v is not None]
        if not usable:
            return None
        if self.consolidationFunc == 'sum':
            return sum(usable)
        if self.consolidationFunc == 'average':
            return float(sum(usable)) / len(usable)
        if self.consolidationFunc == 'max':
            return max(usable)
        if self.consolidationFunc == 'min':
            return min(usable)
        raise Exception("Invalid consolidation function!")

    def __repr__(self):
        return 'TimeSeries(name=%s, start=%s, end=%s, step=%s)' % (
            self.name, self.start, self.end, self.step)


# Data retrieval API
def fetchData(requestContext, pathExpr):
    from ..app import app

    seriesList = []
    startTime = int(epoch(requestContext['startTime']))
    endTime = int(epoch(requestContext['endTime']))

    def _fetchData(pathExpr, startTime, endTime, requestContext, seriesList):
        matching_nodes = app.store.find(pathExpr, startTime, endTime)

        # Group nodes that support multiple fetches
        multi_nodes = defaultdict(list)
        single_nodes = []
        for node in matching_nodes:
            if not node.is_leaf:
                continue
            if hasattr(node, '__fetch_multi__'):
                multi_nodes[node.__fetch_multi__].append(node)
            else:
                single_nodes.append(node)

        fetches = [
            (node, node.fetch(startTime, endTime)) for node in single_nodes]

        for finder in app.store.finders:
            if not hasattr(finder, '__fetch_multi__'):
                continue
            nodes = multi_nodes[finder.__fetch_multi__]
            if not nodes:
                continue
            time_info, series = finder.fetch_multi(nodes, startTime, endTime)
            start, end, step = time_info
            for path, values in series.items():
                series = TimeSeries(path, start, end, step, values)
                series.pathExpression = pathExpr
                seriesList.append(series)

        for node, results in fetches:
            if not results:
                logger.info("no results", node=node, start=startTime,
                            end=endTime)
                continue

            try:
                timeInfo, values = results
            except ValueError as e:
                raise Exception("could not parse timeInfo/values from metric "
                                "'%s': %s" % (node.path, e))
            start, end, step = timeInfo

            series = TimeSeries(node.path, start, end, step, values)
            # hack to pass expressions through to render functions
            series.pathExpression = pathExpr
            seriesList.append(series)

        # Prune empty series with duplicate metric paths to avoid showing
        # empty graph elements for old whisper data
        names = set([s.name for s in seriesList])
        for name in names:
            series_with_duplicate_names = [
                s for s in seriesList if s.name == name]
            empty_duplicates = [
                s for s in series_with_duplicate_names
                if not nonempty(series)]

            if (
                series_with_duplicate_names == empty_duplicates and
                len(empty_duplicates) > 0
            ):  # if they're all empty
                empty_duplicates.pop()  # make sure we leave one in seriesList

            for series in empty_duplicates:
                seriesList.remove(series)

        return seriesList

    return _fetchData(pathExpr, startTime, endTime, requestContext, seriesList)


def nonempty(series):
    for value in series:
        if value is not None:
            return True
    return False

########NEW FILE########
__FILENAME__ = glyph
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import cairocffi as cairo
import itertools
import json
import math
import pytz
import re
import six

from datetime import datetime, timedelta
from io import BytesIO
from six.moves import range
from six.moves.urllib.parse import unquote_plus

from .datalib import TimeSeries
from ..utils import to_seconds


INFINITY = float('inf')

colorAliases = {
    'black': (0, 0, 0),
    'white': (255, 255, 255),
    'blue': (100, 100, 255),
    'green': (0, 200, 0),
    'red': (200, 00, 50),
    'yellow': (255, 255, 0),
    'orange': (255, 165, 0),
    'purple': (200, 100, 255),
    'brown': (150, 100, 50),
    'cyan': (0, 255, 255),
    'aqua': (0, 150, 150),
    'gray': (175, 175, 175),
    'grey': (175, 175, 175),
    'magenta': (255, 0, 255),
    'pink': (255, 100, 100),
    'gold': (200, 200, 0),
    'rose': (200, 150, 200),
    'darkblue': (0, 0, 255),
    'darkgreen': (0, 255, 0),
    'darkred': (255, 0, 0),
    'darkgray': (111, 111, 111),
    'darkgrey': (111, 111, 111),
}

# This gets overriden by graphTemplates.conf
defaultGraphOptions = dict(
    background='white',
    foreground='black',
    majorline='rose',
    minorline='grey',
    linecolors=('blue,green,red,purple,brown,yellow,aqua,grey,'
                'magenta,pink,gold,rose'),
    fontname='Sans',
    fontsize=10,
    fontbold='false',
    fontitalic='false',
)

# X-axis configurations (copied from rrdtool, this technique is evil & ugly
# but effective)
SEC = 1
MIN = 60
HOUR = MIN * 60
DAY = HOUR * 24
WEEK = DAY * 7
MONTH = DAY * 31
YEAR = DAY * 365

# Set a flag to indicate whether the '%l' option can be used safely.
# On Windows, in particular the %l option in strftime is not supported.
# (It is not one of the documented Python formatters).
try:
    datetime.now().strftime("%a %l%p")
    percent_l_supported = True
except ValueError:
    percent_l_supported = False

xAxisConfigs = (
    dict(seconds=0.00,
         minorGridUnit=SEC,
         minorGridStep=5,
         majorGridUnit=MIN,
         majorGridStep=1,
         labelUnit=SEC,
         labelStep=5,
         format="%H:%M:%S",
         maxInterval=10*MIN),
    dict(seconds=0.07,
         minorGridUnit=SEC,
         minorGridStep=10,
         majorGridUnit=MIN,
         majorGridStep=1,
         labelUnit=SEC,
         labelStep=10,
         format="%H:%M:%S",
         maxInterval=20*MIN),
    dict(seconds=0.14,
         minorGridUnit=SEC,
         minorGridStep=15,
         majorGridUnit=MIN,
         majorGridStep=1,
         labelUnit=SEC,
         labelStep=15,
         format="%H:%M:%S",
         maxInterval=30*MIN),
    dict(seconds=0.27,
         minorGridUnit=SEC,
         minorGridStep=30,
         majorGridUnit=MIN,
         majorGridStep=2,
         labelUnit=MIN,
         labelStep=1,
         format="%H:%M",
         maxInterval=2*HOUR),
    dict(seconds=0.5,
         minorGridUnit=MIN,
         minorGridStep=1,
         majorGridUnit=MIN,
         majorGridStep=2,
         labelUnit=MIN,
         labelStep=1,
         format="%H:%M",
         maxInterval=2*HOUR),
    dict(seconds=1.2,
         minorGridUnit=MIN,
         minorGridStep=1,
         majorGridUnit=MIN,
         majorGridStep=4,
         labelUnit=MIN,
         labelStep=2,
         format="%H:%M",
         maxInterval=3*HOUR),
    dict(seconds=2,
         minorGridUnit=MIN,
         minorGridStep=1,
         majorGridUnit=MIN,
         majorGridStep=10,
         labelUnit=MIN,
         labelStep=5,
         format="%H:%M",
         maxInterval=6*HOUR),
    dict(seconds=5,
         minorGridUnit=MIN,
         minorGridStep=2,
         majorGridUnit=MIN,
         majorGridStep=10,
         labelUnit=MIN,
         labelStep=10,
         format="%H:%M",
         maxInterval=12*HOUR),
    dict(seconds=10,
         minorGridUnit=MIN,
         minorGridStep=5,
         majorGridUnit=MIN,
         majorGridStep=20,
         labelUnit=MIN,
         labelStep=20,
         format="%H:%M",
         maxInterval=1*DAY),
    dict(seconds=30,
         minorGridUnit=MIN,
         minorGridStep=10,
         majorGridUnit=HOUR,
         majorGridStep=1,
         labelUnit=HOUR,
         labelStep=1,
         format="%H:%M",
         maxInterval=2*DAY),
    dict(seconds=60,
         minorGridUnit=MIN,
         minorGridStep=30,
         majorGridUnit=HOUR,
         majorGridStep=2,
         labelUnit=HOUR,
         labelStep=2,
         format="%H:%M",
         maxInterval=2*DAY),
    dict(seconds=100,
         minorGridUnit=HOUR,
         minorGridStep=2,
         majorGridUnit=HOUR,
         majorGridStep=4,
         labelUnit=HOUR,
         labelStep=4,
         format=percent_l_supported and "%a %l%p" or "%a %I%p",
         maxInterval=6*DAY),
    dict(seconds=255,
         minorGridUnit=HOUR,
         minorGridStep=6,
         majorGridUnit=HOUR,
         majorGridStep=12,
         labelUnit=HOUR,
         labelStep=12,
         format=percent_l_supported and "%m/%d %l%p" or "%m/%d %I%p",
         maxInterval=10*DAY),
    dict(seconds=600,
         minorGridUnit=HOUR,
         minorGridStep=6,
         majorGridUnit=DAY,
         majorGridStep=1,
         labelUnit=DAY,
         labelStep=1,
         format="%m/%d",
         maxInterval=14*DAY),
    dict(seconds=600,
         minorGridUnit=HOUR,
         minorGridStep=12,
         majorGridUnit=DAY,
         majorGridStep=1,
         labelUnit=DAY,
         labelStep=1,
         format="%m/%d",
         maxInterval=365*DAY),
    dict(seconds=2000,
         minorGridUnit=DAY,
         minorGridStep=1,
         majorGridUnit=DAY,
         majorGridStep=2,
         labelUnit=DAY,
         labelStep=2,
         format="%m/%d",
         maxInterval=365*DAY),
    dict(seconds=4000,
         minorGridUnit=DAY,
         minorGridStep=2,
         majorGridUnit=DAY,
         majorGridStep=4,
         labelUnit=DAY,
         labelStep=4,
         format="%m/%d",
         maxInterval=365*DAY),
    dict(seconds=8000,
         minorGridUnit=DAY,
         minorGridStep=3.5,
         majorGridUnit=DAY,
         majorGridStep=7,
         labelUnit=DAY,
         labelStep=7,
         format="%m/%d",
         maxInterval=365*DAY),
    dict(seconds=16000,
         minorGridUnit=DAY,
         minorGridStep=7,
         majorGridUnit=DAY,
         majorGridStep=14,
         labelUnit=DAY,
         labelStep=14,
         format="%m/%d",
         maxInterval=365*DAY),
    dict(seconds=32000,
         minorGridUnit=DAY,
         minorGridStep=15,
         majorGridUnit=DAY,
         majorGridStep=30,
         labelUnit=DAY,
         labelStep=30,
         format="%m/%d",
         maxInterval=365*DAY),
    dict(seconds=64000,
         minorGridUnit=DAY,
         minorGridStep=30,
         majorGridUnit=DAY,
         majorGridStep=60,
         labelUnit=DAY,
         labelStep=60,
         format="%m/%d %Y"),
    dict(seconds=100000,
         minorGridUnit=DAY,
         minorGridStep=60,
         majorGridUnit=DAY,
         majorGridStep=120,
         labelUnit=DAY,
         labelStep=120,
         format="%m/%d %Y"),
    dict(seconds=120000,
         minorGridUnit=DAY,
         minorGridStep=120,
         majorGridUnit=DAY,
         majorGridStep=240,
         labelUnit=DAY,
         labelStep=240,
         format="%m/%d %Y"),
)

UnitSystems = {
    'binary': (
        ('Pi', 1024.0**5),
        ('Ti', 1024.0**4),
        ('Gi', 1024.0**3),
        ('Mi', 1024.0**2),
        ('Ki', 1024.0)),
    'si': (
        ('P', 1000.0**5),
        ('T', 1000.0**4),
        ('G', 1000.0**3),
        ('M', 1000.0**2),
        ('K', 1000.0)),
    'none': [],
}


def force_text(value):
    if not isinstance(value, six.string_types):
        value = six.text_type(value)
    return value


class GraphError(Exception):
    pass


class Graph(object):
    customizable = ('width', 'height', 'margin', 'bgcolor', 'fgcolor',
                    'fontName', 'fontSize', 'fontBold', 'fontItalic',
                    'colorList', 'template', 'yAxisSide', 'outputFormat')

    def __init__(self, **params):
        self.params = params
        self.data = params['data']
        self.dataLeft = []
        self.dataRight = []
        self.secondYAxis = False
        self.width = int(params.get('width', 200))
        self.height = int(params.get('height', 200))
        self.margin = int(params.get('margin', 10))
        self.userTimeZone = params.get('tz')
        self.logBase = params.get('logBase', None)
        self.minorY = int(params.get('minorY', 1))

        if self.logBase:
            if self.logBase == 'e':
                self.logBase = math.e
            elif self.logBase <= 1:
                self.logBase = None
                params['logBase'] = None
            else:
                self.logBase = float(self.logBase)

        if self.margin < 0:
            self.margin = 10

        self.area = {
            'xmin': self.margin + 10,  # Need extra room when the time is
                                       # near the left edge
            'xmax': self.width - self.margin,
            'ymin': self.margin,
            'ymax': self.height - self.margin,
        }

        self.loadTemplate(params.get('template', 'default'))

        self.setupCairo(params.get('outputFormat', 'png').lower())

        opts = self.ctx.get_font_options()
        opts.set_antialias(cairo.ANTIALIAS_NONE)
        self.ctx.set_font_options(opts)

        self.foregroundColor = params.get('fgcolor', self.defaultForeground)
        self.backgroundColor = params.get('bgcolor', self.defaultBackground)
        self.setColor(self.backgroundColor)
        self.drawRectangle(0, 0, self.width, self.height)

        if 'colorList' in params:
            colorList = unquote_plus(str(params['colorList'])).split(',')
        else:
            colorList = self.defaultColorList
        self.colors = itertools.cycle(colorList)

        self.drawGraph(**params)

    def setupCairo(self, outputFormat='png'):
        self.outputFormat = outputFormat
        if outputFormat == 'png':
            self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                              self.width, self.height)
        else:
            self.surfaceData = BytesIO()
            self.surface = cairo.SVGSurface(self.surfaceData,
                                            self.width, self.height)
        self.ctx = cairo.Context(self.surface)

    def setColor(self, value, alpha=1.0, forceAlpha=False):
        if isinstance(value, tuple) and len(value) == 3:
            r, g, b = value
        elif value in colorAliases:
            r, g, b = colorAliases[value]
        elif isinstance(value, six.string_types) and len(value) >= 6:
            s = value
            if s.startswith('#'):
                s = s[1:]
            r, g, b = (int(s[0:2], base=16), int(s[2:4], base=16),
                       int(s[4:6], base=16))
            if len(s) == 8 and not forceAlpha:
                alpha = int(s[6:8], base=16) / 255.0
        else:
            raise ValueError("Must specify an RGB 3-tuple, an html color "
                             "string, or a known color alias!")
        r, g, b = [float(c) / 255.0 for c in (r, g, b)]
        self.ctx.set_source_rgba(r, g, b, alpha)

    def setFont(self, **params):
        p = self.defaultFontParams.copy()
        p.update(params)
        self.ctx.select_font_face(p['name'], p['italic'], p['bold'])
        self.ctx.set_font_size(float(p['size']))

    def getExtents(self, text=None):
        F = self.ctx.font_extents()
        extents = {'maxHeight': F[2], 'maxAscent': F[0], 'maxDescent': F[1]}
        if text:
            T = self.ctx.text_extents(text)
            extents['width'] = T[4]
            extents['height'] = T[3]
        return extents

    def drawRectangle(self, x, y, w, h, fill=True):
        if not fill:
            # offset for borders so they are drawn as lines would be
            o = self.ctx.get_line_width() / 2.0
            x += o
            y += o
            w -= o
            h -= o
        self.ctx.rectangle(x, y, w, h)
        if fill:
            self.ctx.fill()
        else:
            self.ctx.set_dash([], 0)
            self.ctx.stroke()

    def drawText(self, text, x, y, align='left', valign='top', rotate=0):
        extents = self.getExtents(text)
        angle = math.radians(rotate)
        origMatrix = self.ctx.get_matrix()

        horizontal = {
            'left': 0,
            'center': extents['width'] / 2,
            'right': extents['width'],
        }[align.lower()]
        vertical = {
            'top': extents['maxAscent'],
            'middle': extents['maxHeight'] / 2 - extents['maxDescent'],
            'bottom': -extents['maxDescent'],
            'baseline': 0,
        }[valign.lower()]

        self.ctx.move_to(x, y)
        self.ctx.rel_move_to(math.sin(angle) * -vertical,
                             math.cos(angle) * vertical)
        self.ctx.rotate(angle)
        self.ctx.rel_move_to(-horizontal, 0)
        bx, by = self.ctx.get_current_point()
        by -= extents['maxAscent']
        self.ctx.text_path(text)
        self.ctx.fill()
        self.ctx.set_matrix(origMatrix)

    def drawTitle(self, text):
        self.encodeHeader('title')

        y = self.area['ymin']
        x = self.width / 2
        lineHeight = self.getExtents()['maxHeight']
        for line in text.split('\n'):
            self.drawText(line, x, y, align='center')
            y += lineHeight
        if self.params.get('yAxisSide') == 'right':
            self.area['ymin'] = y
        else:
            self.area['ymin'] = y + self.margin

    def drawLegend(self, elements, unique=False):
        # elements is [ (name,color,rightSide), (name,color,rightSide), ... ]
        self.encodeHeader('legend')

        if unique:
            # remove duplicate names
            namesSeen = []
            newElements = []
            for e in elements:
                if e[0] not in namesSeen:
                    namesSeen.append(e[0])
                    newElements.append(e)
            elements = newElements

        # Check if there's enough room to use two columns.
        rightSideLabels = False
        padding = 5
        longestName = sorted([e[0] for e in elements], key=len)[-1]
        # Double it to check if there's enough room for 2 columns
        testSizeName = longestName + " " + longestName
        testExt = self.getExtents(testSizeName)
        testBoxSize = testExt['maxHeight'] - 1
        testWidth = testExt['width'] + 2 * (testBoxSize + padding)
        if testWidth + 50 < self.width:
            rightSideLabels = True

        if self.secondYAxis and rightSideLabels:
            extents = self.getExtents(longestName)
            padding = 5
            boxSize = extents['maxHeight'] - 1
            lineHeight = extents['maxHeight'] + 1
            labelWidth = extents['width'] + 2 * (boxSize + padding)
            columns = max(1, math.floor(
                (self.width - self.area['xmin']) / labelWidth))
            numRight = len([name for (name, color, rightSide) in elements
                            if rightSide])
            numberOfLines = max(len(elements) - numRight, numRight)
            columns = math.floor(columns / 2.0)
            columns = max(columns, 1)
            legendHeight = max(
                1, (numberOfLines / columns)) * (lineHeight + padding)
            # scoot the drawing area up to fit the legend
            self.area['ymax'] -= legendHeight
            self.ctx.set_line_width(1.0)
            x = self.area['xmin']
            y = self.area['ymax'] + (2 * padding)
            n = 0
            xRight = self.area['xmax'] - self.area['xmin']
            yRight = y
            nRight = 0
            for name, color, rightSide in elements:
                self.setColor(color)
                if rightSide:
                    nRight += 1
                    self.drawRectangle(xRight - padding, yRight,
                                       boxSize, boxSize)
                    self.setColor('darkgrey')
                    self.drawRectangle(xRight - padding, yRight,
                                       boxSize, boxSize, fill=False)
                    self.setColor(self.foregroundColor)
                    self.drawText(name, xRight - boxSize, yRight,
                                  align='right')
                    xRight -= labelWidth
                    if nRight % columns == 0:
                        xRight = self.area['xmax'] - self.area['xmin']
                        yRight += lineHeight
                else:
                    n += 1
                    self.drawRectangle(x, y, boxSize, boxSize)
                    self.setColor('darkgrey')
                    self.drawRectangle(x, y, boxSize, boxSize, fill=False)
                    self.setColor(self.foregroundColor)
                    self.drawText(name, x + boxSize + padding, y, align='left')
                    x += labelWidth
                    if n % columns == 0:
                        x = self.area['xmin']
                        y += lineHeight
        else:
            extents = self.getExtents(longestName)
            boxSize = extents['maxHeight'] - 1
            lineHeight = extents['maxHeight'] + 1
            labelWidth = extents['width'] + 2 * (boxSize + padding)
            columns = math.floor(self.width / labelWidth)
            columns = max(columns, 1)
            numberOfLines = math.ceil(float(len(elements)) / columns)
            legendHeight = numberOfLines * (lineHeight + padding)
            # scoot the drawing area up to fit the legend
            self.area['ymax'] -= legendHeight
            self.ctx.set_line_width(1.0)
            x = self.area['xmin']
            y = self.area['ymax'] + (2 * padding)
            for i, (name, color, rightSide) in enumerate(elements):
                if rightSide:
                    self.setColor(color)
                    self.drawRectangle(x + labelWidth + padding, y,
                                       boxSize, boxSize)
                    self.setColor('darkgrey')
                    self.drawRectangle(x + labelWidth + padding, y,
                                       boxSize, boxSize, fill=False)
                    self.setColor(self.foregroundColor)
                    self.drawText(name, x + labelWidth, y, align='right')
                    x += labelWidth
                else:
                    self.setColor(color)
                    self.drawRectangle(x, y, boxSize, boxSize)
                    self.setColor('darkgrey')
                    self.drawRectangle(x, y, boxSize, boxSize, fill=False)
                    self.setColor(self.foregroundColor)
                    self.drawText(name, x + boxSize + padding, y, align='left')
                    x += labelWidth
                if (i + 1) % columns == 0:
                    x = self.area['xmin']
                    y += lineHeight

    def encodeHeader(self, text):
        self.ctx.save()
        self.setColor(self.backgroundColor)
        self.ctx.move_to(-88, -88)  # identifier
        for i, char in enumerate(text):
            self.ctx.line_to(-ord(char), -i-1)
        self.ctx.stroke()
        self.ctx.restore()

    def loadTemplate(self, template):
        opts = defaults = defaultGraphOptions

        self.defaultBackground = opts.get('background', defaults['background'])
        self.defaultForeground = opts.get('foreground', defaults['foreground'])
        self.defaultMajorGridLineColor = opts.get('majorline',
                                                  defaults['majorline'])
        self.defaultMinorGridLineColor = opts.get('minorline',
                                                  defaults['minorline'])
        self.defaultColorList = [
            c.strip() for c in opts.get('linecolors',
                                        defaults['linecolors']).split(',')]
        fontName = opts.get('fontname', defaults['fontname'])
        fontSize = float(opts.get('fontsize', defaults['fontsize']))
        fontBold = opts.get('fontbold', defaults['fontbold']).lower() == 'true'
        fontItalic = opts.get('fontitalic',
                              defaults['fontitalic']).lower() == 'true'
        self.defaultFontParams = {
            'name': self.params.get('fontName', fontName),
            'size': int(self.params.get('fontSize', fontSize)),
            'bold': self.params.get('fontBold', fontBold),
            'italic': self.params.get('fontItalic', fontItalic),
        }

    def output(self, fileObj):
        if self.outputFormat == 'png':
            self.surface.write_to_png(fileObj)
        else:
            metaData = {
                'x': {
                    'start': self.startTime,
                    'end': self.endTime
                },
                'options': {
                    'lineWidth': self.lineWidth
                },
                'font': self.defaultFontParams,
                'area': self.area,
                'series': []
            }

            if not self.secondYAxis:
                metaData['y'] = {
                    'top': self.yTop,
                    'bottom': self.yBottom,
                    'step': self.yStep,
                    'labels': self.yLabels,
                    'labelValues': self.yLabelValues
                }

            for series in self.data:
                if 'stacked' not in series.options:
                    metaData['series'].append({
                        'name': series.name,
                        'start': series.start,
                        'end': series.end,
                        'step': series.step,
                        'valuesPerPoint': series.valuesPerPoint,
                        'color': series.color,
                        'data': series,
                        'options': series.options
                    })

            self.surface.finish()
            svgData = self.surfaceData.getvalue()
            self.surfaceData.close()

            # we expect height/width in pixels, not points
            svgData = svgData.decode().replace('pt"', 'px"', 2)
            svgData = svgData.replace('</svg>\n', '', 1)
            svgData = svgData.replace('</defs>\n<g',
                                      '</defs>\n<g class="graphite"', 1)

            # We encode headers using special paths with d^="M -88 -88"
            # Find these, and turn them into <g> wrappers instead
            def onHeaderPath(match):
                name = ''
                for char in re.findall(r'L -(\d+) -\d+', match.group(1)):
                    name += chr(int(char))
                return '</g><g data-header="true" class="%s">' % name
            svgData = re.sub(r'<path.+?d="M -88 -88 (.+?)"/>',
                             onHeaderPath, svgData)

            # Replace the first </g><g> with <g>, and close out the last </g>
            # at the end
            svgData = svgData.replace('</g><g data-header',
                                      '<g data-header', 1) + "</g>"
            svgData = svgData.replace(' data-header="true"', '')

            fileObj.write(svgData.encode())
            fileObj.write(("""<script>
    <![CDATA[
        metadata = %s
    ]]>
</script>
</svg>""" % json.dumps(metaData)).encode())


class LineGraph(Graph):
    customizable = Graph.customizable + (
        'title', 'vtitle', 'lineMode', 'lineWidth', 'hideLegend', 'hideAxes',
        'minXStep', 'hideGrid', 'majorGridLineColor', 'minorGridLineColor',
        'thickness', 'min', 'max', 'graphOnly', 'yMin', 'yMax', 'yLimit',
        'yStep', 'areaMode', 'areaAlpha', 'drawNullAsZero', 'tz', 'yAxisSide',
        'pieMode', 'yUnitSystem', 'logBase', 'yMinLeft', 'yMinRight',
        'yMaxLeft', 'yMaxRight', 'yLimitLeft', 'yLimitRight', 'yStepLeft',
        'yStepRight', 'rightWidth', 'rightColor', 'rightDashed', 'leftWidth',
        'leftColor', 'leftDashed', 'xFormat', 'minorY', 'hideYAxis',
        'uniqueLegend', 'vtitleRight', 'yDivisors', 'connectedLimit')
    validLineModes = ('staircase', 'slope', 'connected')
    validAreaModes = ('none', 'first', 'all', 'stacked')
    validPieModes = ('maximum', 'minimum', 'average')

    def drawGraph(self, **params):
        # Make sure we've got datapoints to draw
        if self.data:
            startTime = min([series.start for series in self.data])
            endTime = max([series.end for series in self.data])
            timeRange = endTime - startTime
        else:
            timeRange = None

        if not timeRange:
            x = self.width / 2
            y = self.height / 2
            self.setColor('red')
            self.setFont(size=math.log(self.width * self.height))
            self.drawText("No Data", x, y, align='center')
            return

        # Determine if we're doing a 2 y-axis graph.
        for series in self.data:
            if 'secondYAxis' in series.options:
                self.dataRight.append(series)
            else:
                self.dataLeft.append(series)
        if len(self.dataRight) > 0:
            self.secondYAxis = True

        # API compatibilty hacks
        if params.get('graphOnly', False):
            params['hideLegend'] = True
            params['hideGrid'] = True
            params['hideAxes'] = True
            params['hideYAxis'] = False
            params['yAxisSide'] = 'left'
            params['title'] = ''
            params['vtitle'] = ''
            params['margin'] = 0
            params['tz'] = ''
            self.margin = 0
            self.area['xmin'] = 0
            self.area['xmax'] = self.width
            self.area['ymin'] = 0
            self.area['ymax'] = self.height
        if 'yMin' not in params and 'min' in params:
            params['yMin'] = params['min']
        if 'yMax' not in params and 'max' in params:
            params['yMax'] = params['max']
        if 'lineWidth' not in params and 'thickness' in params:
            params['lineWidth'] = params['thickness']
        if 'yAxisSide' not in params:
            params['yAxisSide'] = 'left'
        if 'yUnitSystem' not in params:
            params['yUnitSystem'] = 'si'
        else:
            params['yUnitSystem'] = str(params['yUnitSystem']).lower()
            if params['yUnitSystem'] not in UnitSystems.keys():
                params['yUnitSystem'] = 'si'

        self.params = params

        # Don't do any of the special right y-axis stuff if we're drawing 2
        # y-axes.
        if self.secondYAxis:
            params['yAxisSide'] = 'left'

        # When Y Axis is labeled on the right, we subtract x-axis positions
        # from the max, instead of adding to the minimum
        if self.params.get('yAxisSide') == 'right':
            self.margin = self.width
        # Now to setup our LineGraph specific options
        self.lineWidth = float(params.get('lineWidth', 1.2))
        self.lineMode = params.get('lineMode', 'slope').lower()
        self.connectedLimit = params.get("connectedLimit", INFINITY)
        assert self.lineMode in self.validLineModes, "Invalid line mode!"
        self.areaMode = params.get('areaMode', 'none').lower()
        assert self.areaMode in self.validAreaModes, "Invalid area mode!"
        self.pieMode = params.get('pieMode', 'maximum').lower()
        assert self.pieMode in self.validPieModes, "Invalid pie mode!"

        # Line mode slope does not work (or even make sense) for series that
        # have only one datapoint. So if any series have one datapoint we
        # force staircase mode.
        if self.lineMode == 'slope':
            for series in self.data:
                if len(series) == 1:
                    self.lineMode = 'staircase'
                    break

        if self.secondYAxis:
            for series in self.data:
                if 'secondYAxis' in series.options:
                    if 'rightWidth' in params:
                        series.options['lineWidth'] = params['rightWidth']
                    if 'rightDashed' in params:
                        series.options['dashed'] = params['rightDashed']
                    if 'rightColor' in params:
                        series.color = params['rightColor']
                else:
                    if 'leftWidth' in params:
                        series.options['lineWidth'] = params['leftWidth']
                    if 'leftDashed' in params:
                        series.options['dashed'] = params['leftDashed']
                    if 'leftColor' in params:
                        series.color = params['leftColor']

        for series in self.data:
            if not hasattr(series, 'color'):
                series.color = next(self.colors)

        titleSize = self.defaultFontParams['size'] + math.floor(
            math.log(self.defaultFontParams['size']))
        self.setFont(size=titleSize)
        self.setColor(self.foregroundColor)

        if params.get('title'):
            self.drawTitle(force_text(params['title']))
        if params.get('vtitle'):
            self.drawVTitle(force_text(params['vtitle']))
        if self.secondYAxis and params.get('vtitleRight'):
            self.drawVTitle(str(params['vtitleRight']), rightAlign=True)
        self.setFont()

        if not params.get('hideLegend', len(self.data) > 10):
            elements = [
                (series.name, series.color,
                 series.options.get('secondYAxis')) for series in self.data
                if series.name]
            self.drawLegend(elements, params.get('uniqueLegend', False))

        # Setup axes, labels, and grid
        # First we adjust the drawing area size to fit X-axis labels
        if not self.params.get('hideAxes', False):
            self.area['ymax'] -= self.getExtents()['maxAscent'] * 2

        self.startTime = min([series.start for series in self.data])
        if (
            self.lineMode == 'staircase' or
            set([len(series) for series in self.data]) == set([2])
        ):
            self.endTime = max([series.end for series in self.data])
        else:
            self.endTime = max([
                (series.end - series.step) for series in self.data])
        self.timeRange = self.endTime - self.startTime

        # Now we consolidate our data points to fit in the currently estimated
        # drawing area
        self.consolidateDataPoints()

        self.encodeHeader('axes')

        # Now its time to fully configure the Y-axis and determine the space
        # required for Y-axis labels. Since we'll probably have to squeeze the
        # drawing area to fit the Y labels, we may need to reconsolidate our
        # data points, which in turn means re-scaling the Y axis, this process
        # will repeat until we have accurate Y labels and enough space to fit
        # our data points
        currentXMin = self.area['xmin']
        currentXMax = self.area['xmax']

        if self.secondYAxis:
            self.setupTwoYAxes()
        else:
            self.setupYAxis()
        while (
            currentXMin != self.area['xmin'] or
            currentXMax != self.area['xmax']
        ):  # see if the Y-labels require more space
            # this can cause the Y values to change
            self.consolidateDataPoints()
            # so let's keep track of the previous Y-label space requirements
            currentXMin = self.area['xmin']
            currentXMax = self.area['xmax']
            if self.secondYAxis:  # and recalculate their new requirements
                self.setupTwoYAxes()
            else:
                self.setupYAxis()

        # Now that our Y-axis is finalized, let's determine our X labels (this
        # won't affect the drawing area)
        self.setupXAxis()

        if not self.params.get('hideAxes', False):
            self.drawLabels()
            if not self.params.get('hideGrid', False):
                # hideAxes implies hideGrid
                self.encodeHeader('grid')
                self.drawGridLines()

        # Finally, draw the graph lines
        self.encodeHeader('lines')
        self.drawLines()

    def drawVTitle(self, text, rightAlign=False):
        lineHeight = self.getExtents()['maxHeight']

        if rightAlign:
            self.encodeHeader('vtitleRight')
            x = self.area['xmax'] - lineHeight
            y = self.height / 2
            for line in text.split('\n'):
                self.drawText(line, x, y, align='center', valign='baseline',
                              rotate=90)
                x -= lineHeight
            self.area['xmax'] = x - self.margin - lineHeight
        else:
            self.encodeHeader('vtitle')
            x = self.area['xmin'] + lineHeight
            y = self.height / 2
            for line in text.split('\n'):
                self.drawText(line, x, y, align='center', valign='baseline',
                              rotate=270)
                x += lineHeight
            self.area['xmin'] = x + self.margin + lineHeight

    def getYCoord(self, value, side=None):
        if "left" == side:
            yLabelValues = self.yLabelValuesL
            yTop = self.yTopL
            yBottom = self.yBottomL
        elif "right" == side:
            yLabelValues = self.yLabelValuesR
            yTop = self.yTopR
            yBottom = self.yBottomR
        else:
            yLabelValues = self.yLabelValues
            yTop = self.yTop
            yBottom = self.yBottom

        try:
            highestValue = max(yLabelValues)
            lowestValue = min(yLabelValues)
        except ValueError:
            highestValue = yTop
            lowestValue = yBottom

        pixelRange = self.area['ymax'] - self.area['ymin']

        relativeValue = value - lowestValue
        valueRange = highestValue - lowestValue

        if self.logBase:
            if value <= 0:
                return None
            relativeValue = (
                math.log(value, self.logBase)
                - math.log(lowestValue, self.logBase))
            valueRange = math.log(highestValue, self.logBase) - math.log(
                lowestValue, self.logBase)

        pixelToValueRatio = pixelRange / valueRange
        valueInPixels = pixelToValueRatio * relativeValue
        return self.area['ymax'] - valueInPixels

    def drawLines(self, width=None, dash=None, linecap='butt',
                  linejoin='miter'):
        if not width:
            width = self.lineWidth
        self.ctx.set_line_width(width)
        originalWidth = width
        width = float(int(width) % 2) / 2
        if dash:
            self.ctx.set_dash(dash, 1)
        else:
            self.ctx.set_dash([], 0)
        self.ctx.set_line_cap({
            'butt': cairo.LINE_CAP_BUTT,
            'round': cairo.LINE_CAP_ROUND,
            'square': cairo.LINE_CAP_SQUARE,
        }[linecap])
        self.ctx.set_line_join({
            'miter': cairo.LINE_JOIN_MITER,
            'round': cairo.LINE_JOIN_ROUND,
            'bevel': cairo.LINE_JOIN_BEVEL,
        }[linejoin])

        # check whether there is an stacked metric
        singleStacked = False
        for series in self.data:
            if 'stacked' in series.options:
                singleStacked = True
        if singleStacked:
            self.data = sort_stacked(self.data)

        # stack the values
        if self.areaMode == 'stacked' and not self.secondYAxis:
            # TODO Allow stacked area mode with secondYAxis
            total = []
            for series in self.data:
                if 'drawAsInfinite' in series.options:
                    continue

                series.options['stacked'] = True
                for i in range(len(series)):
                    if len(total) <= i:
                        total.append(0)

                    if series[i] is not None:
                        original = series[i]
                        series[i] += total[i]
                        total[i] += original
        elif self.areaMode == 'first':
            self.data[0].options['stacked'] = True
        elif self.areaMode == 'all':
            for series in self.data:
                if 'drawAsInfinite' not in series.options:
                    series.options['stacked'] = True

        # apply alpha channel and create separate stroke series
        if self.params.get('areaAlpha'):
            try:
                alpha = float(self.params['areaAlpha'])
            except ValueError:
                alpha = 0.5

            strokeSeries = []
            for series in self.data:
                if 'stacked' in series.options:
                    series.options['alpha'] = alpha

                    newSeries = TimeSeries(
                        series.name, series.start, series.end,
                        series.step * series.valuesPerPoint,
                        [x for x in series])
                    newSeries.xStep = series.xStep
                    newSeries.color = series.color
                    if 'secondYAxis' in series.options:
                        newSeries.options['secondYAxis'] = True
                    strokeSeries.append(newSeries)
            self.data += strokeSeries

        # setup the clip region
        self.ctx.set_line_width(1.0)
        self.ctx.rectangle(self.area['xmin'], self.area['ymin'],
                           self.area['xmax'] - self.area['xmin'],
                           self.area['ymax'] - self.area['ymin'])
        self.ctx.clip()
        self.ctx.set_line_width(originalWidth)

        # save clip to restore once stacked areas are drawn
        self.ctx.save()
        clipRestored = False

        for series in self.data:

            if 'stacked' not in series.options:
                # stacked areas are always drawn first. if this series is not
                # stacked, we finished stacking. reset the clip region so
                # lines can show up on top of the stacked areas.
                if not clipRestored:
                    clipRestored = True
                    self.ctx.restore()

            if 'lineWidth' in series.options:
                self.ctx.set_line_width(series.options['lineWidth'])

            if 'dashed' in series.options:
                self.ctx.set_dash([series.options['dashed']], 1)
            else:
                self.ctx.set_dash([], 0)

            # Shift the beginning of drawing area to the start of the series
            # if the graph itself has a larger range
            missingPoints = (series.start - self.startTime) / series.step
            startShift = series.xStep * (missingPoints / series.valuesPerPoint)
            x = float(self.area['xmin']) + startShift + (self.lineWidth / 2.0)
            y = float(self.area['ymin'])

            startX = x

            if series.options.get('invisible'):
                self.setColor(series.color, 0, True)
            else:
                self.setColor(series.color,
                              series.options.get('alpha') or 1.0)

            # The number of preceeding datapoints that had a None value.
            consecutiveNones = 0

            for index, value in enumerate(series):
                if value != value:  # convert NaN to None
                    value = None

                if value is None and self.params.get('drawNullAsZero'):
                    value = 0.0

                if value is None:
                    if consecutiveNones == 0:
                        self.ctx.line_to(x, y)
                        if 'stacked' in series.options:
                            # Close off and fill area before unknown interval
                            if self.secondYAxis:
                                if 'secondYAxis' in series.options:
                                    self.fillAreaAndClip(
                                        x, y, startX,
                                        self.getYCoord(0, "right"))
                                else:
                                    self.fillAreaAndClip(
                                        x, y, startX,
                                        self.getYCoord(0, "left"))
                            else:
                                self.fillAreaAndClip(x, y, startX,
                                                     self.getYCoord(0))

                    x += series.xStep
                    consecutiveNones += 1

                else:
                    if self.secondYAxis:
                        if 'secondYAxis' in series.options:
                            y = self.getYCoord(value, "right")
                        else:
                            y = self.getYCoord(value, "left")
                    else:
                        y = self.getYCoord(value)

                    if y is None:
                        value = None
                    elif y < 0:
                        y = 0

                    if 'drawAsInfinite' in series.options and value > 0:
                        self.ctx.move_to(x, self.area['ymax'])
                        self.ctx.line_to(x, self.area['ymin'])
                        self.ctx.stroke()
                        x += series.xStep
                        continue

                    if consecutiveNones > 0:
                        startX = x

                    if self.lineMode == 'staircase':
                        if consecutiveNones > 0:
                            self.ctx.move_to(x, y)
                        else:
                            self.ctx.line_to(x, y)

                        x += series.xStep
                        self.ctx.line_to(x, y)

                    elif self.lineMode == 'slope':
                        if consecutiveNones > 0:
                            self.ctx.move_to(x, y)

                        self.ctx.line_to(x, y)
                        x += series.xStep

                    elif self.lineMode == 'connected':
                        # If if the gap is larger than the connectedLimit or
                        # if this is the first non-None datapoint in the
                        # series, start drawing from that datapoint.
                        if (
                            consecutiveNones > self.connectedLimit or
                            consecutiveNones == index
                        ):
                            self.ctx.move_to(x, y)

                        self.ctx.line_to(x, y)
                        x += series.xStep

                    consecutiveNones = 0

            if 'stacked' in series.options:
                if self.lineMode == 'staircase':
                    xPos = x
                else:
                    xPos = x-series.xStep
                if self.secondYAxis:
                    if 'secondYAxis' in series.options:
                        areaYFrom = self.getYCoord(0, "right")
                    else:
                        areaYFrom = self.getYCoord(0, "left")
                else:
                    areaYFrom = self.getYCoord(0)

                self.fillAreaAndClip(xPos, y, startX, areaYFrom)

            else:
                self.ctx.stroke()

            # return to the original line width
            self.ctx.set_line_width(originalWidth)
            if 'dash' in series.options:
                # if we changed the dash setting before, change it back now
                if dash:
                    self.ctx.set_dash(dash, 1)
                else:
                    self.ctx.set_dash([], 0)

    def fillAreaAndClip(self, x, y, startX=None, areaYFrom=None):
        startX = (startX or self.area['xmin'])
        areaYFrom = (areaYFrom or self.area['ymax'])
        pattern = self.ctx.copy_path()

        # fill
        self.ctx.line_to(x, areaYFrom)  # bottom endX
        self.ctx.line_to(startX, areaYFrom)  # bottom startX
        self.ctx.close_path()
        self.ctx.fill()

        # clip above y axis
        self.ctx.append_path(pattern)
        self.ctx.line_to(x, areaYFrom)  # yZero endX
        self.ctx.line_to(self.area['xmax'], areaYFrom)  # yZero right
        self.ctx.line_to(self.area['xmax'], self.area['ymin'])  # top right
        self.ctx.line_to(self.area['xmin'], self.area['ymin'])  # top left
        self.ctx.line_to(self.area['xmin'], areaYFrom)  # yZero left
        self.ctx.line_to(startX, areaYFrom)  # yZero startX

        # clip below y axis
        self.ctx.line_to(x, areaYFrom)  # yZero endX
        self.ctx.line_to(self.area['xmax'], areaYFrom)  # yZero right
        self.ctx.line_to(self.area['xmax'], self.area['ymax'])  # bottom right
        self.ctx.line_to(self.area['xmin'], self.area['ymax'])  # bottom left
        self.ctx.line_to(self.area['xmin'], areaYFrom)  # yZero left
        self.ctx.line_to(startX, areaYFrom)  # yZero startX
        self.ctx.close_path()
        self.ctx.clip()

    def consolidateDataPoints(self):
        numberOfPixels = self.graphWidth = (
            self.area['xmax'] - self.area['xmin'] - (self.lineWidth + 1))
        for series in self.data:
            numberOfDataPoints = self.timeRange / series.step
            minXStep = float(self.params.get('minXStep', 1.0))
            divisor = self.timeRange / series.step
            bestXStep = numberOfPixels / divisor
            if bestXStep < minXStep:
                drawableDataPoints = int(numberOfPixels / minXStep)
                pointsPerPixel = math.ceil(
                    float(numberOfDataPoints) / float(drawableDataPoints))
                series.consolidate(pointsPerPixel)
                series.xStep = (
                    numberOfPixels * pointsPerPixel) / numberOfDataPoints
            else:
                series.xStep = bestXStep

    def setupYAxis(self):
        seriesWithMissingValues = [series for series in self.data
                                   if None in series]

        if self.params.get('drawNullAsZero') and seriesWithMissingValues:
            yMinValue = 0.0
        else:
            yMinValue = safeMin([
                safeMin(series) for series in self.data
                if not series.options.get('drawAsInfinite')])

        if self.areaMode == 'stacked':
            length = safeMin([
                len(series) for series in self.data
                if not series.options.get('drawAsInfinite')])
            sumSeries = []

            for i in range(0, length):
                sumSeries.append(safeSum([
                    series[i] for series in self.data
                    if not series.options.get('drawAsInfinite')]))
            yMaxValue = safeMax(sumSeries)
        else:
            yMaxValue = safeMax([
                safeMax(series) for series in self.data
                if not series.options.get('drawAsInfinite')])

        if yMinValue is None:
            yMinValue = 0.0

        if yMaxValue is None:
            yMaxValue = 1.0

        if 'yMax' in self.params:
            if self.params['yMax'] != 'max':
                yMaxValue = self.params['yMax']

        if 'yLimit' in self.params and self.params['yLimit'] < yMaxValue:
            yMaxValue = self.params['yLimit']

        if 'yMin' in self.params:
            yMinValue = self.params['yMin']

        if yMaxValue <= yMinValue:
            yMaxValue = yMinValue + 1

        yVariance = yMaxValue - yMinValue
        if self.params.get('yUnitSystem') == 'binary':
            order = math.log(yVariance, 2)
            orderFactor = 2 ** math.floor(order)
        else:
            order = math.log10(yVariance)
            orderFactor = 10 ** math.floor(order)
        # we work with a scaled down yVariance for simplicity
        v = yVariance / orderFactor

        yDivisors = str(self.params.get('yDivisors', '4,5,6'))
        yDivisors = [int(d) for d in yDivisors.split(',')]

        prettyValues = (0.1, 0.2, 0.25, 0.5, 1.0, 1.2, 1.25, 1.5,
                        2.0, 2.25, 2.5)
        divisorInfo = []

        for d in yDivisors:
            # our scaled down quotient, must be in the open interval (0,10)
            q = v / d
            # the prettyValue our quotient is closest to
            p = closest(q, prettyValues)
            # make a list so we can find the prettiest of the pretty
            divisorInfo.append((p, abs(q-p)))

        # sort our pretty values by "closeness to a factor"
        divisorInfo.sort(key=lambda i: i[1])
        # our winner! Y-axis will have labels placed at multiples of our
        # prettyValue
        prettyValue = divisorInfo[0][0]
        # scale it back up to the order of yVariance
        self.yStep = prettyValue * orderFactor

        if 'yStep' in self.params:
            self.yStep = self.params['yStep']

        # start labels at the greatest multiple of yStep <= yMinValue
        self.yBottom = self.yStep * math.floor(yMinValue / self.yStep)
        # Extend the top of our graph to the lowest yStep multiple >= yMaxValue
        self.yTop = self.yStep * math.ceil(yMaxValue / self.yStep)

        if self.logBase and yMinValue > 0:
            self.yBottom = math.pow(self.logBase,
                                    math.floor(math.log(yMinValue,
                                                        self.logBase)))
            self.yTop = math.pow(self.logBase,
                                 math.ceil(math.log(yMaxValue, self.logBase)))
        elif self.logBase and yMinValue <= 0:
            raise GraphError('Logarithmic scale specified with a dataset with '
                             'a minimum value less than or equal to zero')

        if 'yMax' in self.params:
            if self.params['yMax'] == 'max':
                scale = 1.0 * yMaxValue / self.yTop
                self.yStep *= (scale - 0.000001)
                self.yTop = yMaxValue
            else:
                self.yTop = self.params['yMax'] * 1.0
        if 'yMin' in self.params:
            self.yBottom = self.params['yMin']

        self.ySpan = self.yTop - self.yBottom

        if self.ySpan == 0:
            self.yTop += 1
            self.ySpan += 1

        self.graphHeight = self.area['ymax'] - self.area['ymin']
        self.yScaleFactor = float(self.graphHeight) / float(self.ySpan)

        if not self.params.get('hideAxes', False):
            # Create and measure the Y-labels

            def makeLabel(yValue):
                yValue, prefix = format_units(
                    yValue, self.yStep, system=self.params.get('yUnitSystem'))
                ySpan, spanPrefix = format_units(
                    self.ySpan, self.yStep,
                    system=self.params.get('yUnitSystem'))
                if yValue < 0.1:
                    return "%g %s" % (float(yValue), prefix)
                elif yValue < 1.0:
                    return "%.2f %s" % (float(yValue), prefix)
                if ySpan > 10 or spanPrefix != prefix:
                    if isinstance(yValue, float):
                        return "%.1f %s" % (float(yValue), prefix)
                    else:
                        return "%d %s " % (int(yValue), prefix)
                elif ySpan > 3:
                    return "%.1f %s " % (float(yValue), prefix)
                elif ySpan > 0.1:
                    return "%.2f %s " % (float(yValue), prefix)
                else:
                    return "%g %s" % (float(yValue), prefix)

            self.yLabelValues = self.getYLabelValues(self.yBottom, self.yTop,
                                                     self.yStep)
            self.yLabels = list(map(makeLabel, self.yLabelValues))
            self.yLabelWidth = max([
                self.getExtents(label)['width'] for label in self.yLabels])

            if not self.params.get('hideYAxis'):
                if self.params.get('yAxisSide') == 'left':
                    # scoot the graph over to the left just enough to fit the
                    # y-labels
                    xMin = self.margin + (self.yLabelWidth * 1.02)
                    if self.area['xmin'] < xMin:
                        self.area['xmin'] = xMin
                else:
                    # scoot the graph over to the right just enough to fit
                    # # the y-labels
                    xMin = 0
                    xMax = self.margin - (self.yLabelWidth * 1.02)
                    if self.area['xmax'] >= xMax:
                        self.area['xmax'] = xMax
        else:
            self.yLabelValues = []
            self.yLabels = []
            self.yLabelWidth = 0.0

    def setupTwoYAxes(self):
        # I am Lazy.
        Ldata = []
        Rdata = []
        seriesWithMissingValuesL = []
        seriesWithMissingValuesR = []
        self.yLabelsL = []
        self.yLabelsR = []

        Ldata += self.dataLeft
        Rdata += self.dataRight

        # Lots of coupled lines ahead. Will operate on Left data first then
        # Right.

        seriesWithMissingValuesL = [
            series for series in Ldata if None in series]
        seriesWithMissingValuesR = [
            series for series in Rdata if None in series]

        if self.params.get('drawNullAsZero') and seriesWithMissingValuesL:
            yMinValueL = 0.0
        else:
            yMinValueL = safeMin([
                safeMin(series) for series in Ldata
                if not series.options.get('drawAsInfinite')])
        if self.params.get('drawNullAsZero') and seriesWithMissingValuesR:
            yMinValueR = 0.0
        else:
            yMinValueR = safeMin([
                safeMin(series) for series in Rdata
                if not series.options.get('drawAsInfinite')])

        if self.areaMode == 'stacked':
            yMaxValueL = safeSum([safeMax(series) for series in Ldata])
            yMaxValueR = safeSum([safeMax(series) for series in Rdata])
        else:
            yMaxValueL = safeMax([safeMax(series) for series in Ldata])
            yMaxValueR = safeMax([safeMax(series) for series in Rdata])

        if yMinValueL is None:
            yMinValueL = 0.0
        if yMinValueR is None:
            yMinValueR = 0.0

        if yMaxValueL is None:
            yMaxValueL = 1.0
        if yMaxValueR is None:
            yMaxValueR = 1.0

        if 'yMaxLeft' in self.params:
            yMaxValueL = self.params['yMaxLeft']
        if 'yMaxRight' in self.params:
            yMaxValueR = self.params['yMaxRight']

        if (
            'yLimitLeft' in self.params and
            self.params['yLimitLeft'] < yMaxValueL
        ):
            yMaxValueL = self.params['yLimitLeft']
        if (
            'yLimitRight' in self.params and
            self.params['yLimitRight'] < yMaxValueR
        ):
            yMaxValueR = self.params['yLimitRight']

        if 'yMinLeft' in self.params:
            yMinValueL = self.params['yMinLeft']
        if 'yMinRight' in self.params:
            yMinValueR = self.params['yMinRight']

        if yMaxValueL <= yMinValueL:
            yMaxValueL = yMinValueL + 1
        if yMaxValueR <= yMinValueR:
            yMaxValueR = yMinValueR + 1

        yVarianceL = yMaxValueL - yMinValueL
        yVarianceR = yMaxValueR - yMinValueR
        orderL = math.log10(yVarianceL)
        orderR = math.log10(yVarianceR)
        orderFactorL = 10 ** math.floor(orderL)
        orderFactorR = 10 ** math.floor(orderR)
        # we work with a scaled down yVariance for simplicity
        vL = yVarianceL / orderFactorL
        vR = yVarianceR / orderFactorR

        yDivisors = str(self.params.get('yDivisors', '4,5,6'))
        yDivisors = [int(d) for d in yDivisors.split(',')]

        prettyValues = (0.1, 0.2, 0.25, 0.5, 1.0, 1.2, 1.25, 1.5,
                        2.0, 2.25, 2.5)
        divisorInfoL = []
        divisorInfoR = []

        for d in yDivisors:
            # our scaled down quotient, must be in the open interval (0,10)
            qL = vL / d
            qR = vR / d
            # the prettyValue our quotient is closest to
            pL = closest(qL, prettyValues)
            pR = closest(qR, prettyValues)
            # make a list so we can find the prettiest of the pretty
            divisorInfoL.append((pL, abs(qL-pL)))
            divisorInfoR.append((pR, abs(qR-pR)))

        # sort our pretty values by "closeness to a factor"
        divisorInfoL.sort(key=lambda i: i[1])
        divisorInfoR.sort(key=lambda i: i[1])
        # our winner! Y-axis will have labels placed at multiples of our
        # prettyValue
        prettyValueL = divisorInfoL[0][0]
        prettyValueR = divisorInfoR[0][0]
        # scale it back up to the order of yVariance
        self.yStepL = prettyValueL * orderFactorL
        self.yStepR = prettyValueR * orderFactorR

        if 'yStepLeft' in self.params:
            self.yStepL = self.params['yStepLeft']
        if 'yStepRight' in self.params:
            self.yStepR = self.params['yStepRight']

        # start labels at the greatest multiple of yStepL <= yMinValue
        self.yBottomL = self.yStepL * math.floor(yMinValueL / self.yStepL)
        # start labels at the greatest multiple of yStepR <= yMinValue
        self.yBottomR = self.yStepR * math.floor(yMinValueR / self.yStepR)
        # Extend the top of our graph to the lowest
        # yStepL multiple >= yMaxValue
        self.yTopL = self.yStepL * math.ceil(yMaxValueL / self.yStepL)
        # Extend the top of our graph to the lowest
        # yStepR multiple >= yMaxValue
        self.yTopR = self.yStepR * math.ceil(yMaxValueR / self.yStepR)

        if self.logBase and yMinValueL > 0 and yMinValueR > 0:
            # TODO: Allow separate bases for L & R Axes.
            self.yBottomL = math.pow(self.logBase,
                                     math.floor(math.log(yMinValueL,
                                                         self.logBase)))
            self.yTopL = math.pow(self.logBase,
                                  math.ceil(math.log(yMaxValueL,
                                                     self.logBase)))
            self.yBottomR = math.pow(self.logBase,
                                     math.floor(math.log(yMinValueR,
                                                         self.logBase)))
            self.yTopR = math.pow(self.logBase,
                                  math.ceil(math.log(yMaxValueR,
                                                     self.logBase)))
        elif self.logBase and (yMinValueL <= 0 or yMinValueR <= 0):
            raise GraphError('Logarithmic scale specified with a dataset with '
                             'a minimum value less than or equal to zero')

        if 'yMaxLeft' in self.params:
            self.yTopL = self.params['yMaxLeft']
        if 'yMaxRight' in self.params:
            self.yTopR = self.params['yMaxRight']
        if 'yMinLeft' in self.params:
            self.yBottomL = self.params['yMinLeft']
        if 'yMinRight' in self.params:
            self.yBottomR = self.params['yMinRight']

        self.ySpanL = self.yTopL - self.yBottomL
        self.ySpanR = self.yTopR - self.yBottomR

        if self.ySpanL == 0:
            self.yTopL += 1
            self.ySpanL += 1
        if self.ySpanR == 0:
            self.yTopR += 1
            self.ySpanR += 1

        self.graphHeight = self.area['ymax'] - self.area['ymin']
        self.yScaleFactorL = float(self.graphHeight) / float(self.ySpanL)
        self.yScaleFactorR = float(self.graphHeight) / float(self.ySpanR)

        # Create and measure the Y-labels
        def makeLabel(yValue, yStep=None, ySpan=None):
            yValue, prefix = format_units(
                yValue, yStep, system=self.params.get('yUnitSystem'))
            ySpan, spanPrefix = format_units(
                ySpan, yStep, system=self.params.get('yUnitSystem'))
            if yValue < 0.1:
                return "%g %s" % (float(yValue), prefix)
            elif yValue < 1.0:
                return "%.2f %s" % (float(yValue), prefix)
            if ySpan > 10 or spanPrefix != prefix:
                if isinstance(yValue, float):
                    return "%.1f %s " % (float(yValue), prefix)
                else:
                    return "%d %s " % (int(yValue), prefix)
            elif ySpan > 3:
                return "%.1f %s " % (float(yValue), prefix)
            elif ySpan > 0.1:
                return "%.2f %s " % (float(yValue), prefix)
            else:
                return "%g %s" % (float(yValue), prefix)

        self.yLabelValuesL = self.getYLabelValues(self.yBottomL, self.yTopL,
                                                  self.yStepL)
        self.yLabelValuesR = self.getYLabelValues(self.yBottomR, self.yTopR,
                                                  self.yStepR)
        for value in self.yLabelValuesL:
            # can't use map() here self.yStepL and self.ySpanL are not iterable
            self.yLabelsL.append(makeLabel(value, self.yStepL, self.ySpanL))
        for value in self.yLabelValuesR:
            self.yLabelsR.append(makeLabel(value, self.yStepR, self.ySpanR))
        self.yLabelWidthL = max([
            self.getExtents(label)['width'] for label in self.yLabelsL])
        self.yLabelWidthR = max([
            self.getExtents(label)['width'] for label in self.yLabelsR])
        # scoot the graph over to the left just enough to fit the y-labels

        # xMin = self.margin + self.margin + (self.yLabelWidthL * 1.02)
        xMin = self.margin + (self.yLabelWidthL * 1.02)
        if self.area['xmin'] < xMin:
            self.area['xmin'] = xMin
        # scoot the graph over to the right just enough to fit the y-labels
        xMax = self.width - (self.yLabelWidthR * 1.02)
        if self.area['xmax'] >= xMax:
            self.area['xmax'] = xMax

    def getYLabelValues(self, minYValue, maxYValue, yStep=None):
        vals = []
        if self.logBase:
            vals = list(logrange(self.logBase, minYValue, maxYValue))
        else:
            vals = list(frange(minYValue, maxYValue, yStep))
        return vals

    def setupXAxis(self):
        from ..app import app
        if self.userTimeZone:
            tzinfo = pytz.timezone(self.userTimeZone)
        else:
            tzinfo = pytz.timezone(app.config['TIME_ZONE'])

        self.start_dt = datetime.fromtimestamp(self.startTime, tzinfo)
        self.end_dt = datetime.fromtimestamp(self.endTime, tzinfo)

        secondsPerPixel = float(self.timeRange) / float(self.graphWidth)
        # pixels per second
        self.xScaleFactor = float(self.graphWidth) / float(self.timeRange)

        potential = [
            c for c in xAxisConfigs if c['seconds'] <= secondsPerPixel
            and c.get('maxInterval', self.timeRange + 1) >= self.timeRange]
        if potential:
            self.xConf = potential[-1]
        else:
            self.xConf = xAxisConfigs[-1]

        self.xLabelStep = self.xConf['labelUnit'] * self.xConf['labelStep']
        self.xMinorGridStep = (
            self.xConf['minorGridUnit'] * self.xConf['minorGridStep'])
        self.xMajorGridStep = (
            self.xConf['majorGridUnit'] * self.xConf['majorGridStep'])

    def drawLabels(self):
        # Draw the Y-labels
        if not self.params.get('hideYAxis'):
            if not self.secondYAxis:
                for value, label in zip(self.yLabelValues, self.yLabels):
                    if self.params.get('yAxisSide') == 'left':
                        x = self.area['xmin'] - (self.yLabelWidth * 0.02)
                    else:
                        # Inverted for right side Y Axis
                        x = self.area['xmax'] + (self.yLabelWidth * 0.02)

                    y = self.getYCoord(value)
                    if y is None:
                        value = None
                    elif y < 0:
                        y = 0

                    if self.params.get('yAxisSide') == 'left':
                        self.drawText(label, x, y, align='right',
                                      valign='middle')
                    else:
                        # Inverted for right side Y Axis
                        self.drawText(label, x, y, align='left',
                                      valign='middle')
            else:  # Draws a right side and a Left side axis
                for valueL, labelL in zip(self.yLabelValuesL, self.yLabelsL):
                    xL = self.area['xmin'] - (self.yLabelWidthL * 0.02)
                    yL = self.getYCoord(valueL, "left")
                    if yL is None:
                        value = None
                    elif yL < 0:
                        yL = 0
                    self.drawText(labelL, xL, yL, align='right',
                                  valign='middle')

                    # Right Side
                for valueR, labelR in zip(self.yLabelValuesR, self.yLabelsR):
                    # Inverted for right side Y Axis
                    xR = self.area['xmax'] + (self.yLabelWidthR * 0.02) + 3
                    yR = self.getYCoord(valueR, "right")
                    if yR is None:
                        valueR = None
                    elif yR < 0:
                        yR = 0
                    # Inverted for right side Y Axis
                    self.drawText(labelR, xR, yR, align='left',
                                  valign='middle')

        dt, x_label_delta = find_x_times(self.start_dt,
                                         self.xConf['labelUnit'],
                                         self.xConf['labelStep'])

        # Draw the X-labels
        xFormat = self.params.get('xFormat', self.xConf['format'])
        while dt < self.end_dt:
            label = dt.strftime(xFormat)
            x = self.area['xmin'] + (
                to_seconds(dt - self.start_dt) * self.xScaleFactor)
            y = self.area['ymax'] + self.getExtents()['maxAscent']
            self.drawText(label, x, y, align='center', valign='top')
            dt += x_label_delta

    def drawGridLines(self):
        # Not sure how to handle this for 2 y-axes
        # Just using the left side info for the grid.

        # Horizontal grid lines
        leftSide = self.area['xmin']
        rightSide = self.area['xmax']
        labels = []
        if self.secondYAxis:
            labels = self.yLabelValuesL
        else:
            labels = self.yLabelValues
        if self.logBase:
            labels.append(self.logBase * max(labels))

        for i, value in enumerate(labels):
            self.ctx.set_line_width(0.4)
            self.setColor(self.params.get('majorGridLineColor',
                                          self.defaultMajorGridLineColor))

            if self.secondYAxis:
                y = self.getYCoord(value, "left")
            else:
                y = self.getYCoord(value)

            if y is None or y < 0:
                continue
            self.ctx.move_to(leftSide, y)
            self.ctx.line_to(rightSide, y)
            self.ctx.stroke()

            # draw minor gridlines if this isn't the last label
            if self.minorY >= 1 and i < (len(labels) - 1):
                # in case graphite supports inverted Y axis now or someday
                valueLower, valueUpper = sorted((value, labels[i+1]))

                # each minor gridline is 1/minorY apart from the nearby
                # gridlines. we calculate that distance, for adding to the
                # value in the loop.
                distance = ((valueUpper - valueLower) / float(1 + self.minorY))

                # starting from the initial valueLower, we add the minor
                # distance for each minor gridline that we wish to draw, and
                # then draw it.
                for minor in range(self.minorY):
                    self.ctx.set_line_width(0.3)
                    self.setColor(
                        self.params.get('minorGridLineColor',
                                        self.defaultMinorGridLineColor))

                    # the current minor gridline value is halfway between the
                    # current and next major gridline values
                    value = valueLower + ((1+minor) * distance)

                    if self.logBase:
                        yTopFactor = self.logBase * self.logBase
                    else:
                        yTopFactor = 1

                    if self.secondYAxis:
                        if value >= (yTopFactor * self.yTopL):
                            continue
                    else:
                        if value >= (yTopFactor * self.yTop):
                            continue

                    if self.secondYAxis:
                        y = self.getYCoord(value, "left")
                    else:
                        y = self.getYCoord(value)
                    if y is None or y < 0:
                        continue

                    self.ctx.move_to(leftSide, y)
                    self.ctx.line_to(rightSide, y)
                    self.ctx.stroke()

        # Vertical grid lines
        top = self.area['ymin']
        bottom = self.area['ymax']

        # First we do the minor grid lines (majors will paint over them)
        self.ctx.set_line_width(0.25)
        self.setColor(self.params.get('minorGridLineColor',
                                      self.defaultMinorGridLineColor))
        dt, x_minor_delta = find_x_times(
            self.start_dt, self.xConf['minorGridUnit'],
            self.xConf['minorGridStep'])

        while dt < self.end_dt:
            x = self.area['xmin'] + (
                to_seconds(dt - self.start_dt) * self.xScaleFactor)

            if x < self.area['xmax']:
                self.ctx.move_to(x, bottom)
                self.ctx.line_to(x, top)
                self.ctx.stroke()

            dt += x_minor_delta

        # Now we do the major grid lines
        self.ctx.set_line_width(0.33)
        self.setColor(self.params.get('majorGridLineColor',
                                      self.defaultMajorGridLineColor))
        dt, x_major_delta = find_x_times(self.start_dt,
                                         self.xConf['majorGridUnit'],
                                         self.xConf['majorGridStep'])

        while dt < self.end_dt:
            x = self.area['xmin'] + (
                to_seconds(dt - self.start_dt) * self.xScaleFactor)

            if x < self.area['xmax']:
                self.ctx.move_to(x, bottom)
                self.ctx.line_to(x, top)
                self.ctx.stroke()

            dt += x_major_delta

        # Draw side borders for our graph area
        self.ctx.set_line_width(0.5)
        self.ctx.move_to(self.area['xmax'], bottom)
        self.ctx.line_to(self.area['xmax'], top)
        self.ctx.move_to(self.area['xmin'], bottom)
        self.ctx.line_to(self.area['xmin'], top)
        self.ctx.stroke()


class PieGraph(Graph):
    customizable = Graph.customizable + (
        'title', 'valueLabels', 'valueLabelsMin', 'hideLegend', 'pieLabels',
    )
    validValueLabels = ('none', 'number', 'percent')

    def drawGraph(self, **params):
        self.pieLabels = params.get('pieLabels', 'horizontal')
        self.total = sum([t[1] for t in self.data])

        self.slices = []
        for name, value in self.data:
            self.slices.append({
                'name': name,
                'value': value,
                'percent': value / self.total,
                'color': next(self.colors),
            })

        titleSize = self.defaultFontParams['size'] + math.floor(
            math.log(self.defaultFontParams['size']))
        self.setFont(size=titleSize)
        self.setColor(self.foregroundColor)
        if params.get('title'):
            self.drawTitle(params['title'])
        self.setFont()

        if not params.get('hideLegend', False):
            elements = [
                (slice['name'], slice['color'], None) for slice in self.slices]
            self.drawLegend(elements)

        self.drawSlices()

        self.valueLabelsMin = float(params.get('valueLabelsMin', 5))
        self.valueLabels = params.get('valueLabels', 'percent')
        assert self.valueLabels in self.validValueLabels, (
            "valueLabels=%s must be one of %s" % (
                self.valueLabels, self.validValueLabels))
        if self.valueLabels != 'none':
            self.drawLabels()

    def drawSlices(self):
        theta = 3.0 * math.pi / 2.0
        halfX = (self.area['xmax'] - self.area['xmin']) / 2.0
        halfY = (self.area['ymax'] - self.area['ymin']) / 2.0
        self.x0 = x0 = self.area['xmin'] + halfX
        self.y0 = y0 = self.area['ymin'] + halfY
        self.radius = radius = min(halfX, halfY) * 0.95
        for slice in self.slices:
            self.setColor(slice['color'])
            self.ctx.move_to(x0, y0)
            phi = theta + (2 * math.pi) * slice['percent']
            self.ctx.arc(x0, y0, radius, theta, phi)
            self.ctx.line_to(x0, y0)
            self.ctx.fill()
            slice['midAngle'] = (theta + phi) / 2.0
            slice['midAngle'] %= 2.0 * math.pi
            theta = phi

    def drawLabels(self):
        self.setFont()
        self.setColor('black')
        for slice in self.slices:
            if self.valueLabels == 'percent':
                if slice['percent'] * 100.0 < self.valueLabelsMin:
                    continue
                label = "%%%.2f" % (slice['percent'] * 100.0)
            elif self.valueLabels == 'number':
                if slice['value'] < self.valueLabelsMin:
                    continue
                if (
                    slice['value'] < 10 and
                    slice['value'] != int(slice['value'])
                ):
                    label = "%.2f" % slice['value']
                else:
                    label = str(int(slice['value']))
            theta = slice['midAngle']
            x = self.x0 + (self.radius / 2.0 * math.cos(theta))
            y = self.y0 + (self.radius / 2.0 * math.sin(theta))

            if self.pieLabels == 'rotated':
                if theta > (math.pi / 2.0) and theta <= (3.0 * math.pi / 2.0):
                    theta -= math.pi
                self.drawText(label, x, y, align='center', valign='middle',
                              rotate=math.degrees(theta))
            else:
                self.drawText(label, x, y, align='center', valign='middle')


GraphTypes = {
    'line': LineGraph,
    'pie': PieGraph,
}


# Convience functions
def closest(number, neighbors):
    distance = None
    closestNeighbor = None
    for neighbor in neighbors:
        d = abs(neighbor - number)
        if distance is None or d < distance:
            distance = d
            closestNeighbor = neighbor
    return closestNeighbor


def frange(start, end, step):
    f = start
    while f <= end:
        yield f
        f += step
        # Protect against rounding errors on very small float ranges
        if f == start:
            yield end
            return


def safeMin(args):
    args = [arg for arg in args if arg not in (None, INFINITY)]
    if args:
        return min(args)


def safeMax(args):
    args = [arg for arg in args if arg not in (None, INFINITY)]
    if args:
        return max(args)


def safeSum(values):
    return sum([v for v in values if v not in (None, INFINITY)])


def sort_stacked(series_list):
    stacked = [s for s in series_list if 'stacked' in s.options]
    not_stacked = [s for s in series_list if 'stacked' not in s.options]
    return stacked + not_stacked


def format_units(v, step=None, system="si"):
    """Format the given value in standardized units.

    ``system`` is either 'binary' or 'si'

    For more info, see:
        http://en.wikipedia.org/wiki/SI_prefix
        http://en.wikipedia.org/wiki/Binary_prefix
    """

    if step is None:
        condition = lambda size: abs(v) >= size
    else:
        condition = lambda size: abs(v) >= size and step >= size

    for prefix, size in UnitSystems[system]:
        if condition(size):
            v2 = v / size
            if v2 - math.floor(v2) < 0.00000000001 and v > 1:
                v2 = math.floor(v2)
            return v2, prefix

    if v - math.floor(v) < 0.00000000001 and v > 1:
        v = math.floor(v)
    return v, ""


def find_x_times(start_dt, unit, step):
    if unit == SEC:
        dt = start_dt.replace(
            second=start_dt.second - (start_dt.second % step))
        x_delta = timedelta(seconds=step)

    elif unit == MIN:
        dt = start_dt.replace(
            second=0, minute=start_dt.minute - (start_dt.minute % step))
        x_delta = timedelta(minutes=step)

    elif unit == HOUR:
        dt = start_dt.replace(
            second=0, minute=0, hour=start_dt.hour - (start_dt.hour % step))
        x_delta = timedelta(hours=step)

    elif unit == DAY:
        dt = start_dt.replace(second=0, minute=0, hour=0)
        x_delta = timedelta(days=step)

    else:
        raise ValueError("Invalid unit: %s" % unit)

    while dt < start_dt:
        dt += x_delta

    return (dt, x_delta)


def logrange(base, scale_min, scale_max):
    current = scale_min
    if scale_min > 0:
            current = math.floor(math.log(scale_min, base))
    factor = current
    while current < scale_max:
        current = math.pow(base, factor)
        yield current
        factor += 1

########NEW FILE########
__FILENAME__ = grammar
from pyparsing import (
    ParserElement, Forward, Combine, Optional, Word, Literal, CaselessKeyword,
    CaselessLiteral, Group, FollowedBy, LineEnd, OneOrMore, ZeroOrMore,
    nums, alphas, alphanums, printables, delimitedList, quotedString,
)

ParserElement.enablePackrat()
grammar = Forward()

expression = Forward()

# Literals
intNumber = Combine(
    Optional('-') + Word(nums)
)('integer')

floatNumber = Combine(
    Optional('-') + Word(nums) + Literal('.') + Word(nums)
)('float')

sciNumber = Combine(
    (floatNumber | intNumber) + CaselessLiteral('e') + intNumber
)('scientific')

aString = quotedString('string')

# Use lookahead to match only numbers in a list (can't remember why this
# is necessary)
afterNumber = FollowedBy(",") ^ FollowedBy(")") ^ FollowedBy(LineEnd())
number = Group(
    (sciNumber + afterNumber) |
    (floatNumber + afterNumber) |
    (intNumber + afterNumber)
)('number')

boolean = Group(
    CaselessKeyword("true") |
    CaselessKeyword("false")
)('boolean')

argname = Word(alphas + '_', alphanums + '_')('argname')
funcname = Word(alphas + '_', alphanums + '_')('funcname')

# Symbols
leftParen = Literal('(').suppress()
rightParen = Literal(')').suppress()
comma = Literal(',').suppress()
equal = Literal('=').suppress()

# Function calls

# Symbols
leftBrace = Literal('{')
rightBrace = Literal('}')
leftParen = Literal('(').suppress()
rightParen = Literal(')').suppress()
comma = Literal(',').suppress()
equal = Literal('=').suppress()
backslash = Literal('\\').suppress()

symbols = '''(){},=.'"\\'''
arg = Group(
    boolean |
    number |
    aString |
    expression
)('args*')
kwarg = Group(argname + equal + arg)('kwargs*')

args = delimitedList(~kwarg + arg)    # lookahead to prevent failing on equals
kwargs = delimitedList(kwarg)

call = Group(
    funcname + leftParen +
    Optional(
        args + Optional(
            comma + kwargs
        )
    ) + rightParen
)('call')

# Metric pattern (aka. pathExpression)
validMetricChars = ''.join((set(printables) - set(symbols)))
escapedChar = backslash + Word(symbols, exact=1)
partialPathElem = Combine(
    OneOrMore(
        escapedChar | Word(validMetricChars)
    )
)

matchEnum = Combine(
    leftBrace +
    delimitedList(partialPathElem, combine=True) +
    rightBrace
)

pathElement = Combine(
    Group(partialPathElem | matchEnum) +
    ZeroOrMore(matchEnum | partialPathElem)
)
pathExpression = delimitedList(pathElement,
                               delim='.', combine=True)('pathExpression')

expression <<= Group(call | pathExpression)('expression')
grammar <<= expression

########NEW FILE########
__FILENAME__ = search
import time
import os.path

from structlog import get_logger

from .finders import match_entries
from .utils import is_pattern

logger = get_logger()


class IndexSearcher(object):
    def __init__(self, index_path):
        self.log = logger.bind(index_path=index_path)
        self.index_path = index_path
        self.last_mtime = 0
        self._tree = (None, {})  # (data, children)
        self.reload()

    @property
    def tree(self):
        current_mtime = os.path.getmtime(self.index_path)
        if current_mtime > self.last_mtime:
            self.log.info('reloading stale index',
                          current_mtime=current_mtime,
                          last_mtime=self.last_mtime)
            self.reload()

        return self._tree

    def reload(self):
        self.log.info("reading index data")
        if not os.path.exists(self.index_path):
            with open(self.index_path, 'w'):
                pass
        t = time.time()
        total_entries = 0
        tree = (None, {})  # (data, children)
        with open(self.index_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                branches = line.split('.')
                leaf = branches.pop()
                cursor = tree
                for branch in branches:
                    if branch not in cursor[1]:
                        cursor[1][branch] = (None, {})  # (data, children)
                    cursor = cursor[1][branch]

                cursor[1][leaf] = (line, {})
                total_entries += 1

        self._tree = tree
        self.last_mtime = os.path.getmtime(self.index_path)
        self.log.info("search index reloaded", total_entries=total_entries,
                      duration=time.time() - t)

    def search(self, query, max_results=None, keep_query_pattern=False):
        query_parts = query.split('.')
        metrics_found = set()
        for result in self.subtree_query(self.tree, query_parts):
            if result['path'] in metrics_found:
                continue
            yield result

            metrics_found.add(result['path'])
            if max_results is not None and len(metrics_found) >= max_results:
                return

    def subtree_query(self, root, query_parts):
        if query_parts:
            my_query = query_parts[0]
            if is_pattern(my_query):
                matches = [root[1][node] for node in match_entries(root[1],
                                                                   my_query)]
            elif my_query in root[1]:
                matches = [root[1][my_query]]
            else:
                matches = []

        else:
            matches = root[1].values()

        for child_node in matches:
            result = {
                'path': child_node[0],
                'is_leaf': bool(child_node[0]),
            }
            if result['path'] is not None and not result['is_leaf']:
                result['path'] += '.'
            yield result

            if query_parts:
                for result in self.subtree_query(child_node, query_parts[1:]):
                    yield result

########NEW FILE########
__FILENAME__ = storage
import time

from collections import defaultdict

from .utils import is_pattern
from .node import LeafNode
from .intervals import Interval
from .readers import MultiReader


class Store(object):
    def __init__(self, finders=None):
        self.finders = finders

    def find(self, pattern, startTime=None, endTime=None, local=True):
        query = FindQuery(pattern, startTime, endTime)

        matching_nodes = set()

        # Search locally
        for finder in self.finders:
            for node in finder.find_nodes(query):
                matching_nodes.add(node)

        # Group matching nodes by their path
        nodes_by_path = defaultdict(list)
        for node in matching_nodes:
            nodes_by_path[node.path].append(node)

        # Reduce matching nodes for each path to a minimal set
        found_branch_nodes = set()

        for path, nodes in nodes_by_path.items():
            leaf_nodes = set()

            # First we dispense with the BranchNodes
            for node in nodes:
                if node.is_leaf:
                    leaf_nodes.add(node)
                elif node.path not in found_branch_nodes:
                    # TODO need to filter branch nodes based on requested
                    # interval... how?!?!?
                    yield node
                    found_branch_nodes.add(node.path)

            if not leaf_nodes:
                continue

            if len(leaf_nodes) == 1:
                yield leaf_nodes.pop()
            elif len(leaf_nodes) > 1:
                reader = MultiReader(leaf_nodes)
                yield LeafNode(path, reader)


class FindQuery(object):
    def __init__(self, pattern, startTime, endTime):
        self.pattern = pattern
        self.startTime = startTime
        self.endTime = endTime
        self.isExact = is_pattern(pattern)
        self.interval = Interval(
            float('-inf') if startTime is None else startTime,
            float('inf') if endTime is None else endTime)

    def __repr__(self):
        if self.startTime is None:
            startString = '*'
        else:
            startString = time.ctime(self.startTime)

        if self.endTime is None:
            endString = '*'
        else:
            endString = time.ctime(self.endTime)

        return '<FindQuery: %s from %s until %s>' % (self.pattern, startString,
                                                     endString)

########NEW FILE########
__FILENAME__ = utils
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""
import calendar
import pytz

from flask import request


def is_pattern(s):
    return '*' in s or '?' in s or '[' in s or '{' in s


class RequestParams(object):
    """Dict-like structure that allows accessing request params
    whatever their origin (json body, form body, request args)."""

    def __getitem__(self, key):
        if request.json and key in request.json:
            return request.json[key]
        if key in request.form:
            return request.form[key]
        if key in request.args:
            return request.args[key]
        raise KeyError

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def getlist(self, key):
        if request.json and key in request.json:
            value = self[key]
            if not isinstance(value, list):
                value = [value]
            return value
        if key in request.form:
            return request.form.getlist(key)
        return request.args.getlist(key)
RequestParams = RequestParams()


def to_seconds(delta):
    return abs(delta.seconds + delta.days * 86400)


def epoch(dt):
    """
    Returns the epoch timestamp of a timezone-aware datetime object.
    """
    return calendar.timegm(dt.astimezone(pytz.utc).timetuple())

########NEW FILE########
__FILENAME__ = whisper
# Copyright 2009-Present The Graphite Development Team
# Copyright 2008 Orbitz WorldWide
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# This module is an implementation of the Whisper database API
# Here is the basic layout of a whisper data file
#
# File = Header,Data
#	Header = Metadata,ArchiveInfo+
#		Metadata = aggregationType,maxRetention,xFilesFactor,archiveCount
#		ArchiveInfo = Offset,SecondsPerPoint,Points
#	Data = Archive+
#		Archive = Point+
#			Point = timestamp,value

import itertools
import operator
import os
import struct
import sys
import time

izip = getattr(itertools, 'izip', zip)
ifilter = getattr(itertools, 'ifilter', filter)

if sys.version_info >= (3, 0):
    xrange = range

try:
  import fcntl
  CAN_LOCK = True
except ImportError:
  CAN_LOCK = False

try:
  import ctypes
  import ctypes.util
  CAN_FALLOCATE = True
except ImportError:
  CAN_FALLOCATE = False

fallocate = None

if CAN_FALLOCATE:
  libc_name = ctypes.util.find_library('c')
  libc = ctypes.CDLL(libc_name)
  c_off64_t = ctypes.c_int64
  c_off_t = ctypes.c_int

  try:
    _fallocate = libc.posix_fallocate64
    _fallocate.restype = ctypes.c_int
    _fallocate.argtypes = [ctypes.c_int, c_off64_t, c_off64_t]
  except AttributeError:
    try:
      _fallocate = libc.posix_fallocate
      _fallocate.restype = ctypes.c_int
      _fallocate.argtypes = [ctypes.c_int, c_off_t, c_off_t]
    except AttributeError:
      CAN_FALLOCATE = False

  if CAN_FALLOCATE:
    def _py_fallocate(fd, offset, len_):
      res = _fallocate(fd.fileno(), offset, len_)
      if res != 0:
        raise IOError(res, 'fallocate')
    fallocate = _py_fallocate
  del libc
  del libc_name

LOCK = False
CACHE_HEADERS = False
AUTOFLUSH = False
__headerCache = {}

longFormat = "!L"
longSize = struct.calcsize(longFormat)
floatFormat = "!f"
floatSize = struct.calcsize(floatFormat)
valueFormat = "!d"
valueSize = struct.calcsize(valueFormat)
pointFormat = "!Ld"
pointSize = struct.calcsize(pointFormat)
metadataFormat = "!2LfL"
metadataSize = struct.calcsize(metadataFormat)
archiveInfoFormat = "!3L"
archiveInfoSize = struct.calcsize(archiveInfoFormat)

aggregationTypeToMethod = dict({
  1: 'average',
  2: 'sum',
  3: 'last',
  4: 'max',
  5: 'min'
})
aggregationMethodToType = dict([[v,k] for k,v in aggregationTypeToMethod.items()])
aggregationMethods = aggregationTypeToMethod.values()

debug = startBlock = endBlock = lambda *a,**k: None

UnitMultipliers = {
  'seconds' : 1,
  'minutes' : 60,
  'hours' : 3600,
  'days' : 86400,
  'weeks' : 86400 * 7,
  'years' : 86400 * 365
}


def getUnitString(s):
  if 'seconds'.startswith(s): return 'seconds'
  if 'minutes'.startswith(s): return 'minutes'
  if 'hours'.startswith(s): return 'hours'
  if 'days'.startswith(s): return 'days'
  if 'weeks'.startswith(s): return 'weeks'
  if 'years'.startswith(s): return 'years'
  raise ValueError("Invalid unit '%s'" % s)

def parseRetentionDef(retentionDef):
  import re
  (precision, points) = retentionDef.strip().split(':')

  if precision.isdigit():
    precision = int(precision) * UnitMultipliers[getUnitString('s')]
  else:
    precision_re = re.compile(r'^(\d+)([a-z]+)$')
    match = precision_re.match(precision)
    if match:
      precision = int(match.group(1)) * UnitMultipliers[getUnitString(match.group(2))]
    else:
      raise ValueError("Invalid precision specification '%s'" % precision)

  if points.isdigit():
    points = int(points)
  else:
    points_re = re.compile(r'^(\d+)([a-z]+)$')
    match = points_re.match(points)
    if match:
      points = int(match.group(1)) * UnitMultipliers[getUnitString(match.group(2))] // precision
    else:
      raise ValueError("Invalid retention specification '%s'" % points)

  return (precision, points)


class WhisperException(Exception):
    """Base class for whisper exceptions."""


class InvalidConfiguration(WhisperException):
    """Invalid configuration."""


class InvalidAggregationMethod(WhisperException):
    """Invalid aggregation method."""


class InvalidTimeInterval(WhisperException):
    """Invalid time interval."""


class TimestampNotCovered(WhisperException):
    """Timestamp not covered by any archives in this database."""

class CorruptWhisperFile(WhisperException):
  def __init__(self, error, path):
    Exception.__init__(self, error)
    self.error = error
    self.path = path

  def __repr__(self):
    return "<CorruptWhisperFile[%s] %s>" % (self.path, self.error)

  def __str__(self):
    return "%s (%s)" % (self.error, self.path)

def enableDebug():
  global open, debug, startBlock, endBlock
  class open(file):
    def __init__(self,*args,**kwargs):
      file.__init__(self,*args,**kwargs)
      self.writeCount = 0
      self.readCount = 0

    def write(self,data):
      self.writeCount += 1
      debug('WRITE %d bytes #%d' % (len(data),self.writeCount))
      return file.write(self,data)

    def read(self,bytes):
      self.readCount += 1
      debug('READ %d bytes #%d' % (bytes,self.readCount))
      return file.read(self,bytes)

  def debug(message):
    print('DEBUG :: %s' % message)

  __timingBlocks = {}

  def startBlock(name):
    __timingBlocks[name] = time.time()

  def endBlock(name):
    debug("%s took %.5f seconds" % (name,time.time() - __timingBlocks.pop(name)))


def __readHeader(fh):
  info = __headerCache.get(fh.name)
  if info:
    return info

  originalOffset = fh.tell()
  fh.seek(0)
  packedMetadata = fh.read(metadataSize)

  try:
    (aggregationType,maxRetention,xff,archiveCount) = struct.unpack(metadataFormat,packedMetadata)
  except:
    raise CorruptWhisperFile("Unable to read header", fh.name)

  archives = []

  for i in xrange(archiveCount):
    packedArchiveInfo = fh.read(archiveInfoSize)
    try:
      (offset,secondsPerPoint,points) = struct.unpack(archiveInfoFormat,packedArchiveInfo)
    except:
      raise CorruptWhisperFile("Unable to read archive%d metadata" % i, fh.name)

    archiveInfo = {
      'offset' : offset,
      'secondsPerPoint' : secondsPerPoint,
      'points' : points,
      'retention' : secondsPerPoint * points,
      'size' : points * pointSize,
    }
    archives.append(archiveInfo)

  fh.seek(originalOffset)
  info = {
    'aggregationMethod' : aggregationTypeToMethod.get(aggregationType, 'average'),
    'maxRetention' : maxRetention,
    'xFilesFactor' : xff,
    'archives' : archives,
  }
  if CACHE_HEADERS:
    __headerCache[fh.name] = info

  return info


def setAggregationMethod(path, aggregationMethod, xFilesFactor=None):
  """setAggregationMethod(path,aggregationMethod,xFilesFactor=None)

path is a string
aggregationMethod specifies the method to use when propagating data (see ``whisper.aggregationMethods``)
xFilesFactor specifies the fraction of data points in a propagation interval that must have known values for a propagation to occur.  If None, the existing xFilesFactor in path will not be changed
"""
  fh = None
  try:

    fh = open(path,'r+b')
    if LOCK:
      fcntl.flock( fh.fileno(), fcntl.LOCK_EX )

    packedMetadata = fh.read(metadataSize)

    try:
      (aggregationType,maxRetention,xff,archiveCount) = struct.unpack(metadataFormat,packedMetadata)
    except:
      raise CorruptWhisperFile("Unable to read header", fh.name)

    try:
      newAggregationType = struct.pack( longFormat, aggregationMethodToType[aggregationMethod] )
    except KeyError:
      raise InvalidAggregationMethod("Unrecognized aggregation method: %s" %
            aggregationMethod)

    if xFilesFactor is not None:
        #use specified xFilesFactor
        xff = struct.pack( floatFormat, float(xFilesFactor) )
    else:
	#retain old value
        xff = struct.pack( floatFormat, xff )

    #repack the remaining header information
    maxRetention = struct.pack( longFormat, maxRetention )
    archiveCount = struct.pack(longFormat, archiveCount)

    packedMetadata = newAggregationType + maxRetention + xff + archiveCount
    fh.seek(0)
    #fh.write(newAggregationType)
    fh.write(packedMetadata)

    if AUTOFLUSH:
      fh.flush()
      os.fsync(fh.fileno())

      if CACHE_HEADERS and fh.name in __headerCache:
        del __headerCache[fh.name]

  finally:
    if fh:
      fh.close()

  return aggregationTypeToMethod.get(aggregationType, 'average')


def validateArchiveList(archiveList):
  """ Validates an archiveList.
  An ArchiveList must:
  1. Have at least one archive config. Example: (60, 86400)
  2. No archive may be a duplicate of another.
  3. Higher precision archives' precision must evenly divide all lower precision archives' precision.
  4. Lower precision archives must cover larger time intervals than higher precision archives.
  5. Each archive must have at least enough points to consolidate to the next archive

  Returns True or False
  """

  if not archiveList:
    raise InvalidConfiguration("You must specify at least one archive configuration!")

  archiveList.sort(key=lambda a: a[0]) #sort by precision (secondsPerPoint)

  for i,archive in enumerate(archiveList):
    if i == len(archiveList) - 1:
      break

    nextArchive = archiveList[i+1]
    if not archive[0] < nextArchive[0]:
      raise InvalidConfiguration("A Whisper database may not configured having"
        "two archives with the same precision (archive%d: %s, archive%d: %s)" %
        (i, archive, i + 1, nextArchive))

    if nextArchive[0] % archive[0] != 0:
      raise InvalidConfiguration("Higher precision archives' precision "
        "must evenly divide all lower precision archives' precision "
        "(archive%d: %s, archive%d: %s)" %
        (i, archive[0], i + 1, nextArchive[0]))

    retention = archive[0] * archive[1]
    nextRetention = nextArchive[0] * nextArchive[1]

    if not nextRetention > retention:
      raise InvalidConfiguration("Lower precision archives must cover "
        "larger time intervals than higher precision archives "
        "(archive%d: %s seconds, archive%d: %s seconds)" %
        (i, retention, i + 1, nextRetention))

    archivePoints = archive[1]
    pointsPerConsolidation = nextArchive[0] // archive[0]
    if not archivePoints >= pointsPerConsolidation:
      raise InvalidConfiguration("Each archive must have at least enough points "
        "to consolidate to the next archive (archive%d consolidates %d of "
        "archive%d's points but it has only %d total points)" %
        (i + 1, pointsPerConsolidation, i, archivePoints))


def create(path,archiveList,xFilesFactor=None,aggregationMethod=None,sparse=False,useFallocate=False):
  """create(path,archiveList,xFilesFactor=0.5,aggregationMethod='average')

path is a string
archiveList is a list of archives, each of which is of the form (secondsPerPoint,numberOfPoints)
xFilesFactor specifies the fraction of data points in a propagation interval that must have known values for a propagation to occur
aggregationMethod specifies the function to use when propagating data (see ``whisper.aggregationMethods``)
"""
  # Set default params
  if xFilesFactor is None:
    xFilesFactor = 0.5
  if aggregationMethod is None:
    aggregationMethod = 'average'

  #Validate archive configurations...
  validateArchiveList(archiveList)

  #Looks good, now we create the file and write the header
  if os.path.exists(path):
    raise InvalidConfiguration("File %s already exists!" % path)
  fh = None
  try:
    fh = open(path,'wb')
    if LOCK:
      fcntl.flock( fh.fileno(), fcntl.LOCK_EX )

    aggregationType = struct.pack( longFormat, aggregationMethodToType.get(aggregationMethod, 1) )
    oldest = max([secondsPerPoint * points for secondsPerPoint,points in archiveList])
    maxRetention = struct.pack( longFormat, oldest )
    xFilesFactor = struct.pack( floatFormat, float(xFilesFactor) )
    archiveCount = struct.pack(longFormat, len(archiveList))
    packedMetadata = aggregationType + maxRetention + xFilesFactor + archiveCount
    fh.write(packedMetadata)
    headerSize = metadataSize + (archiveInfoSize * len(archiveList))
    archiveOffsetPointer = headerSize

    for secondsPerPoint,points in archiveList:
      archiveInfo = struct.pack(archiveInfoFormat, archiveOffsetPointer, secondsPerPoint, points)
      fh.write(archiveInfo)
      archiveOffsetPointer += (points * pointSize)

    #If configured to use fallocate and capable of fallocate use that, else
    #attempt sparse if configure or zero pre-allocate if sparse isn't configured.
    if CAN_FALLOCATE and useFallocate:
      remaining = archiveOffsetPointer - headerSize
      fallocate(fh, headerSize, remaining)
    elif sparse:
      fh.seek(archiveOffsetPointer - 1)
      fh.write('\x00')
    else:
      remaining = archiveOffsetPointer - headerSize
      chunksize = 16384
      zeroes = b'\x00' * chunksize
      while remaining > chunksize:
        fh.write(zeroes)
        remaining -= chunksize
      fh.write(zeroes[:remaining])

    if AUTOFLUSH:
      fh.flush()
      os.fsync(fh.fileno())
  finally:
    if fh:
      fh.close()

def aggregate(aggregationMethod, knownValues):
  if aggregationMethod == 'average':
    return float(sum(knownValues)) / float(len(knownValues))
  elif aggregationMethod == 'sum':
    return float(sum(knownValues))
  elif aggregationMethod == 'last':
    return knownValues[len(knownValues)-1]
  elif aggregationMethod == 'max':
    return max(knownValues)
  elif aggregationMethod == 'min':
    return min(knownValues)
  else:
    raise InvalidAggregationMethod("Unrecognized aggregation method %s" %
            aggregationMethod)


def __propagate(fh,header,timestamp,higher,lower):
  aggregationMethod = header['aggregationMethod']
  xff = header['xFilesFactor']

  lowerIntervalStart = timestamp - (timestamp % lower['secondsPerPoint'])
  lowerIntervalEnd = lowerIntervalStart + lower['secondsPerPoint']

  fh.seek(higher['offset'])
  packedPoint = fh.read(pointSize)
  (higherBaseInterval,higherBaseValue) = struct.unpack(pointFormat,packedPoint)

  if higherBaseInterval == 0:
    higherFirstOffset = higher['offset']
  else:
    timeDistance = lowerIntervalStart - higherBaseInterval
    pointDistance = timeDistance // higher['secondsPerPoint']
    byteDistance = pointDistance * pointSize
    higherFirstOffset = higher['offset'] + (byteDistance % higher['size'])

  higherPoints = lower['secondsPerPoint'] // higher['secondsPerPoint']
  higherSize = higherPoints * pointSize
  relativeFirstOffset = higherFirstOffset - higher['offset']
  relativeLastOffset = (relativeFirstOffset + higherSize) % higher['size']
  higherLastOffset = relativeLastOffset + higher['offset']
  fh.seek(higherFirstOffset)

  if higherFirstOffset < higherLastOffset: #we don't wrap the archive
    seriesString = fh.read(higherLastOffset - higherFirstOffset)
  else: #We do wrap the archive
    higherEnd = higher['offset'] + higher['size']
    seriesString = fh.read(higherEnd - higherFirstOffset)
    fh.seek(higher['offset'])
    seriesString += fh.read(higherLastOffset - higher['offset'])

  #Now we unpack the series data we just read
  byteOrder,pointTypes = pointFormat[0],pointFormat[1:]
  points = len(seriesString) // pointSize
  seriesFormat = byteOrder + (pointTypes * points)
  unpackedSeries = struct.unpack(seriesFormat, seriesString)

  #And finally we construct a list of values
  neighborValues = [None] * points
  currentInterval = lowerIntervalStart
  step = higher['secondsPerPoint']

  for i in xrange(0,len(unpackedSeries),2):
    pointTime = unpackedSeries[i]
    if pointTime == currentInterval:
      neighborValues[i//2] = unpackedSeries[i+1]
    currentInterval += step

  #Propagate aggregateValue to propagate from neighborValues if we have enough known points
  knownValues = [v for v in neighborValues if v is not None]
  if not knownValues:
    return False

  knownPercent = float(len(knownValues)) / float(len(neighborValues))
  if knownPercent >= xff: #we have enough data to propagate a value!
    aggregateValue = aggregate(aggregationMethod, knownValues)
    myPackedPoint = struct.pack(pointFormat,lowerIntervalStart,aggregateValue)
    fh.seek(lower['offset'])
    packedPoint = fh.read(pointSize)
    (lowerBaseInterval,lowerBaseValue) = struct.unpack(pointFormat,packedPoint)

    if lowerBaseInterval == 0: #First propagated update to this lower archive
      fh.seek(lower['offset'])
      fh.write(myPackedPoint)
    else: #Not our first propagated update to this lower archive
      timeDistance = lowerIntervalStart - lowerBaseInterval
      pointDistance = timeDistance // lower['secondsPerPoint']
      byteDistance = pointDistance * pointSize
      lowerOffset = lower['offset'] + (byteDistance % lower['size'])
      fh.seek(lowerOffset)
      fh.write(myPackedPoint)

    return True

  else:
    return False


def update(path,value,timestamp=None):
  """update(path,value,timestamp=None)

path is a string
value is a float
timestamp is either an int or float
"""
  value = float(value)
  fh = None
  try:
    fh = open(path,'r+b')
    return file_update(fh, value, timestamp)
  finally:
    if fh:
      fh.close()

def file_update(fh, value, timestamp):
  if LOCK:
    fcntl.flock( fh.fileno(), fcntl.LOCK_EX )

  header = __readHeader(fh)
  now = int( time.time() )
  if timestamp is None:
    timestamp = now

  timestamp = int(timestamp)
  diff = now - timestamp
  if not ((diff < header['maxRetention']) and diff >= 0):
    raise TimestampNotCovered("Timestamp not covered by any archives in "
      "this database.")

  for i,archive in enumerate(header['archives']): #Find the highest-precision archive that covers timestamp
    if archive['retention'] < diff: continue
    lowerArchives = header['archives'][i+1:] #We'll pass on the update to these lower precision archives later
    break

  #First we update the highest-precision archive
  myInterval = timestamp - (timestamp % archive['secondsPerPoint'])
  myPackedPoint = struct.pack(pointFormat,myInterval,value)
  fh.seek(archive['offset'])
  packedPoint = fh.read(pointSize)
  (baseInterval,baseValue) = struct.unpack(pointFormat,packedPoint)

  if baseInterval == 0: #This file's first update
    fh.seek(archive['offset'])
    fh.write(myPackedPoint)
    baseInterval,baseValue = myInterval,value
  else: #Not our first update
    timeDistance = myInterval - baseInterval
    pointDistance = timeDistance // archive['secondsPerPoint']
    byteDistance = pointDistance * pointSize
    myOffset = archive['offset'] + (byteDistance % archive['size'])
    fh.seek(myOffset)
    fh.write(myPackedPoint)

  #Now we propagate the update to lower-precision archives
  higher = archive
  for lower in lowerArchives:
    if not __propagate(fh, header, myInterval, higher, lower):
      break
    higher = lower

  if AUTOFLUSH:
    fh.flush()
    os.fsync(fh.fileno())



def update_many(path,points):
  """update_many(path,points)

path is a string
points is a list of (timestamp,value) points
"""
  if not points: return
  points = [ (int(t),float(v)) for (t,v) in points]
  points.sort(key=lambda p: p[0],reverse=True) #order points by timestamp, newest first
  fh = None
  try:
    fh = open(path,'r+b')
    return file_update_many(fh, points)
  finally:
    if fh:
      fh.close()


def file_update_many(fh, points):
  if LOCK:
    fcntl.flock( fh.fileno(), fcntl.LOCK_EX )

  header = __readHeader(fh)
  now = int( time.time() )
  archives = iter( header['archives'] )
  currentArchive = next(archives)
  currentPoints = []

  for point in points:
    age = now - point[0]

    while currentArchive['retention'] < age: #we can't fit any more points in this archive
      if currentPoints: #commit all the points we've found that it can fit
        currentPoints.reverse() #put points in chronological order
        __archive_update_many(fh,header,currentArchive,currentPoints)
        currentPoints = []
      try:
        currentArchive = next(archives)
      except StopIteration:
        currentArchive = None
        break

    if not currentArchive:
      break #drop remaining points that don't fit in the database

    currentPoints.append(point)

  if currentArchive and currentPoints: #don't forget to commit after we've checked all the archives
    currentPoints.reverse()
    __archive_update_many(fh,header,currentArchive,currentPoints)

  if AUTOFLUSH:
    fh.flush()
    os.fsync(fh.fileno())



def __archive_update_many(fh,header,archive,points):
  step = archive['secondsPerPoint']
  alignedPoints = [ (timestamp - (timestamp % step), value)
                    for (timestamp,value) in points ]
  alignedPoints = dict(alignedPoints).items() # Take the last val of duplicates
  #Create a packed string for each contiguous sequence of points
  packedStrings = []
  previousInterval = None
  currentString = b""
  for (interval,value) in alignedPoints:
    if (not previousInterval) or (interval == previousInterval + step):
      currentString += struct.pack(pointFormat,interval,value)
      previousInterval = interval
    else:
      numberOfPoints = len(currentString) // pointSize
      startInterval = previousInterval - (step * (numberOfPoints-1))
      packedStrings.append( (startInterval,currentString) )
      currentString = struct.pack(pointFormat,interval,value)
      previousInterval = interval
  if currentString:
    numberOfPoints = len(currentString) // pointSize
    startInterval = previousInterval - (step * (numberOfPoints-1))
    packedStrings.append( (startInterval,currentString) )

  #Read base point and determine where our writes will start
  fh.seek(archive['offset'])
  packedBasePoint = fh.read(pointSize)
  (baseInterval,baseValue) = struct.unpack(pointFormat,packedBasePoint)
  if baseInterval == 0: #This file's first update
    baseInterval = packedStrings[0][0] #use our first string as the base, so we start at the start

  #Write all of our packed strings in locations determined by the baseInterval
  for (interval,packedString) in packedStrings:
    timeDistance = interval - baseInterval
    pointDistance = timeDistance // step
    byteDistance = pointDistance * pointSize
    myOffset = archive['offset'] + (byteDistance % archive['size'])
    fh.seek(myOffset)
    archiveEnd = archive['offset'] + archive['size']
    bytesBeyond = (myOffset + len(packedString)) - archiveEnd

    if bytesBeyond > 0:
      fh.write( packedString[:-bytesBeyond] )
      assert fh.tell() == archiveEnd, "archiveEnd=%d fh.tell=%d bytesBeyond=%d len(packedString)=%d" % (archiveEnd,fh.tell(),bytesBeyond,len(packedString))
      fh.seek( archive['offset'] )
      fh.write( packedString[-bytesBeyond:] ) #safe because it can't exceed the archive (retention checking logic above)
    else:
      fh.write(packedString)

  #Now we propagate the updates to lower-precision archives
  higher = archive
  lowerArchives = [arc for arc in header['archives'] if arc['secondsPerPoint'] > archive['secondsPerPoint']]

  for lower in lowerArchives:
    fit = lambda i: i - (i % lower['secondsPerPoint'])
    lowerIntervals = [fit(p[0]) for p in alignedPoints]
    uniqueLowerIntervals = set(lowerIntervals)
    propagateFurther = False
    for interval in uniqueLowerIntervals:
      if __propagate(fh, header, interval, higher, lower):
        propagateFurther = True

    if not propagateFurther:
      break
    higher = lower


def info(path):
  """info(path)

path is a string
"""
  fh = None
  try:
    fh = open(path,'rb')
    return __readHeader(fh)
  finally:
    if fh:
      fh.close()
  return None

def fetch(path,fromTime,untilTime=None,now=None):
  """fetch(path,fromTime,untilTime=None)

path is a string
fromTime is an epoch time
untilTime is also an epoch time, but defaults to now.

Returns a tuple of (timeInfo, valueList)
where timeInfo is itself a tuple of (fromTime, untilTime, step)

Returns None if no data can be returned
"""
  fh = None
  try:
    fh = open(path,'rb')
    return file_fetch(fh, fromTime, untilTime, now)
  finally:
    if fh:
      fh.close()

def file_fetch(fh, fromTime, untilTime, now = None):
  header = __readHeader(fh)
  if now is None:
    now = int( time.time() )
  if untilTime is None:
    untilTime = now
  fromTime = int(fromTime)
  untilTime = int(untilTime)

  # Here we try and be flexible and return as much data as we can.
  # If the range of data is from too far in the past or fully in the future, we
  # return nothing
  if (fromTime > untilTime):
    raise InvalidTimeInterval("Invalid time interval: from time '%s' is after until time '%s'" % (fromTime, untilTime))

  oldestTime = now - header['maxRetention']
  # Range is in the future
  if fromTime > now:
    return None
  # Range is beyond retention
  if untilTime < oldestTime:
    return None
  # Range requested is partially beyond retention, adjust
  if fromTime < oldestTime:
    fromTime = oldestTime
  # Range is partially in the future, adjust
  if untilTime > now:
    untilTime = now

  diff = now - fromTime
  for archive in header['archives']:
    if archive['retention'] >= diff:
      break

  return __archive_fetch(fh, archive, fromTime, untilTime)

def __archive_fetch(fh, archive, fromTime, untilTime):
  """
Fetch data from a single archive. Note that checks for validity of the time
period requested happen above this level so it's possible to wrap around the
archive on a read and request data older than the archive's retention
"""
  fromInterval = int( fromTime - (fromTime % archive['secondsPerPoint']) ) + archive['secondsPerPoint']
  untilInterval = int( untilTime - (untilTime % archive['secondsPerPoint']) ) + archive['secondsPerPoint']
  fh.seek(archive['offset'])
  packedPoint = fh.read(pointSize)
  (baseInterval,baseValue) = struct.unpack(pointFormat,packedPoint)

  if baseInterval == 0:
    step = archive['secondsPerPoint']
    points = (untilInterval - fromInterval) // step
    timeInfo = (fromInterval,untilInterval,step)
    valueList = [None] * points
    return (timeInfo,valueList)

  #Determine fromOffset
  timeDistance = fromInterval - baseInterval
  pointDistance = timeDistance // archive['secondsPerPoint']
  byteDistance = pointDistance * pointSize
  fromOffset = archive['offset'] + (byteDistance % archive['size'])

  #Determine untilOffset
  timeDistance = untilInterval - baseInterval
  pointDistance = timeDistance // archive['secondsPerPoint']
  byteDistance = pointDistance * pointSize
  untilOffset = archive['offset'] + (byteDistance % archive['size'])

  #Read all the points in the interval
  fh.seek(fromOffset)
  if fromOffset < untilOffset: #If we don't wrap around the archive
    seriesString = fh.read(untilOffset - fromOffset)
  else: #We do wrap around the archive, so we need two reads
    archiveEnd = archive['offset'] + archive['size']
    seriesString = fh.read(archiveEnd - fromOffset)
    fh.seek(archive['offset'])
    seriesString += fh.read(untilOffset - archive['offset'])

  #Now we unpack the series data we just read (anything faster than unpack?)
  byteOrder,pointTypes = pointFormat[0],pointFormat[1:]
  points = len(seriesString) // pointSize
  seriesFormat = byteOrder + (pointTypes * points)
  unpackedSeries = struct.unpack(seriesFormat, seriesString)

  #And finally we construct a list of values (optimize this!)
  valueList = [None] * points #pre-allocate entire list for speed
  currentInterval = fromInterval
  step = archive['secondsPerPoint']

  for i in xrange(0,len(unpackedSeries),2):
    pointTime = unpackedSeries[i]
    if pointTime == currentInterval:
      pointValue = unpackedSeries[i+1]
      valueList[i//2] = pointValue #in-place reassignment is faster than append()
    currentInterval += step

  timeInfo = (fromInterval,untilInterval,step)
  return (timeInfo,valueList)

def merge(path_from, path_to):
  """ Merges the data from one whisper file into another. Each file must have
  the same archive configuration
"""
  fh_from = open(path_from, 'rb')
  fh_to = open(path_to, 'rb+')
  return file_merge(fh_from, fh_to)

def file_merge(fh_from, fh_to):
  headerFrom = __readHeader(fh_from)
  headerTo = __readHeader(fh_to)

  if headerFrom['archives'] != headerTo['archives']:
    raise NotImplementedError("%s and %s archive configurations are unalike. " \
    "Resize the input before merging" % (fh_from.name, fh_to.name))

  archives = headerFrom['archives']
  archives.sort(key=operator.itemgetter('retention'))

  now = int(time.time())
  untilTime = now
  for archive in archives:
    fromTime = now - archive['retention']
    (timeInfo, values) = __archive_fetch(fh_from, archive, fromTime, untilTime)
    (start, end, archive_step) = timeInfo
    pointsToWrite = list(ifilter(
      lambda points: points[1] is not None,
      izip(xrange(start, end, archive_step), values)))
    __archive_update_many(fh_to, headerTo, archive, pointsToWrite)
    untilTime = fromTime
  fh_from.close()
  fh_to.close()

def diff(path_from, path_to, ignore_empty = False):
  """ Compare two whisper databases. Each file must have the same archive configuration """
  fh_from = open(path_from, 'rb')
  fh_to = open(path_to, 'rb')
  diffs = file_diff(fh_from, fh_to, ignore_empty)
  fh_to.close()
  fh_from.close()
  return diffs

def file_diff(fh_from, fh_to, ignore_empty = False):
  headerFrom = __readHeader(fh_from)
  headerTo = __readHeader(fh_to)

  if headerFrom['archives'] != headerTo['archives']:
    # TODO: Add specific whisper-resize commands to right size things
    raise NotImplementedError("%s and %s archive configurations are unalike. " \
                                "Resize the input before diffing" % (fh_from.name, fh_to.name))

  archives = headerFrom['archives']
  archives.sort(key=operator.itemgetter('retention'))

  archive_diffs = []

  now = int(time.time())
  untilTime = now
  for archive_number, archive in enumerate(archives):
    diffs = []
    startTime = now - archive['retention']
    (fromTimeInfo, fromValues) = __archive_fetch(fh_from, archive, startTime, untilTime)
    (toTimeInfo, toValues) = __archive_fetch(fh_to, archive, startTime, untilTime)
    (start, end, archive_step) = ( min(fromTimeInfo[0],toTimeInfo[0]), max(fromTimeInfo[1],toTimeInfo[1]), min(fromTimeInfo[2],toTimeInfo[2]) )

    points = map(lambda s: (s * archive_step + start,fromValues[s],toValues[s]), xrange(0,(end - start) // archive_step))
    if ignore_empty:
      points = [p for p in points if p[1] != None and p[2] != None]
    else:
      points = [p for p in points if p[1] != None or p[2] != None]

    diffs = [p for p in points if p[1] != p[2]]

    archive_diffs.append( (archive_number, diffs, points.__len__()) )
    untilTime = startTime
  return archive_diffs

########NEW FILE########
__FILENAME__ = test_attime
import datetime
import time

from graphite_api.render.attime import parseATTime

from . import TestCase


class AtTestCase(TestCase):
    def test_parse(self):
        for value in [
            str(int(time.time())),
            '20140319',
            '20130319+1y',
            '20130319+1mon',
            '20130319+1w',
            '12:12_20130319',
            '3:05am_20130319',
            '3:05pm_20130319',
            'noon20130319',
            'midnight20130319',
            'teatime20130319',
            'yesterday',
            'tomorrow',
            '03/19/2014',
            '03/19/1800',
            '03/19/1950',
            'feb 27',
            'mar 5',
            'mon',
            'tue',
            'wed',
            'thu',
            'fri',
            'sat',
            'sun',
            '10:00',
        ]:
            self.assertIsInstance(parseATTime(value), datetime.datetime)

        for value in [
            '20130319+1foo',
            'mar',
            'wat',
        ]:
            with self.assertRaises(Exception):
                parseATTime(value)

########NEW FILE########
__FILENAME__ = test_finders
import random
import time

from . import TestCase

from graphite_api.intervals import Interval, IntervalSet
from graphite_api.node import LeafNode, BranchNode
from graphite_api.storage import Store


class FinderTest(TestCase):
    def test_custom_finder(self):
        store = Store([DummyFinder()])
        nodes = list(store.find("foo"))
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].path, 'foo')

        nodes = list(store.find('bar.*'))
        self.assertEqual(len(nodes), 10)
        node = nodes[0]
        self.assertEqual(node.path.split('.')[0], 'bar')

        time_info, series = node.fetch(100, 200)
        self.assertEqual(time_info, (100, 200, 10))
        self.assertEqual(len(series), 10)


class DummyReader(object):
    __slots__ = ('path',)

    def __init__(self, path):
        self.path = path

    def fetch(self, start_time, end_time):
        npoints = (end_time - start_time) // 10
        return (start_time, end_time, 10), [
            random.choice([None, 1, 2, 3]) for i in range(npoints)
        ]

    def get_intervals(self):
        return IntervalSet([Interval(time.time() - 3600, time.time())])


class DummyFinder(object):
    def find_nodes(self, query):
        if query.pattern == 'foo':
            yield BranchNode('foo')

        elif query.pattern == 'bar.*':
            for i in range(10):
                path = 'bar.{0}'.format(i)
                yield LeafNode(path, DummyReader(path))

########NEW FILE########
__FILENAME__ = test_functions
import copy
import time

from mock import patch, call, MagicMock

from graphite_api import functions
from graphite_api.app import app
from graphite_api.render.attime import parseATTime
from graphite_api.render.datalib import TimeSeries

from . import TestCase


def return_greater(series, value):
    return [i for i in series if i is not None and i > value]


def return_less(series, value):
    return [i for i in series if i is not None and i < value]


class FunctionsTest(TestCase):
    def test_highest_max(self):
        config = [20, 50, 30, 40]
        seriesList = [range(max_val) for max_val in config]

        # Expect the test results to be returned in decending order
        expected = [
            [seriesList[1]],
            [seriesList[1], seriesList[3]],
            [seriesList[1], seriesList[3], seriesList[2]],
            # Test where num_return == len(seriesList)
            [seriesList[1], seriesList[3], seriesList[2], seriesList[0]],
            # Test where num_return > len(seriesList)
            [seriesList[1], seriesList[3], seriesList[2], seriesList[0]],
        ]
        for index, test in enumerate(expected):
            results = functions.highestMax({}, seriesList, index + 1)
            self.assertEqual(test, results)

    def test_highest_max_empty_series_list(self):
        # Test the function works properly with an empty seriesList provided.
        self.assertEqual([], functions.highestMax({}, [], 1))

    def testGetPercentile(self):
        seriesList = [
            ([None, None, 15, 20, 35, 40, 50], 20),
            (range(100), 30),
            (range(200), 60),
            (range(300), 90),
            (range(1, 101), 31),
            (range(1, 201), 61),
            (range(1, 301), 91),
            (range(0, 102), 30),
            (range(1, 203), 61),
            (range(1, 303), 91),
        ]
        for index, conf in enumerate(seriesList):
            series, expected = conf
            result = functions._getPercentile(series, 30)
            self.assertEqual(
                expected, result,
                ('For series index <%s> the 30th percentile ordinal is not '
                 '%d, but %d ' % (index, expected, result)))

    def test_n_percentile(self):
        seriesList = []
        config = [
            [15, 35, 20, 40, 50],
            range(1, 101),
            range(1, 201),
            range(1, 301),
            range(0, 100),
            range(0, 200),
            range(0, 300),
            # Ensure None values in list has no effect.
            [None, None, None] + list(range(0, 300)),
        ]

        for i, c in enumerate(config):
            seriesList.append(TimeSeries('Test(%d)' % i, 0, 1, 1, c))

        def n_percentile(perc, expected):
            result = functions.nPercentile({}, seriesList, perc)
            self.assertEqual(expected, result)

        n_percentile(30, [[20], [31], [61], [91], [30], [60], [90], [90]])
        n_percentile(90, [[50], [91], [181], [271], [90], [180], [270], [270]])
        n_percentile(95, [[50], [96], [191], [286], [95], [190], [285], [285]])

    def _generate_series_list(self, config=(
        range(101),
        range(2, 103),
        [1] * 2 + [None] * 90 + [1] * 2 + [None] * 7
    )):
        seriesList = []

        now = int(time.time())

        for i, c in enumerate(config):
            name = "collectd.test-db{0}.load.value".format(i + 1)
            series = TimeSeries(name, now - 101, now, 1, c)
            series.pathExpression = name
            seriesList.append(series)
        return seriesList

    def test_remove_above_percentile(self):
        seriesList = self._generate_series_list()
        percent = 50
        results = functions.removeAbovePercentile({}, seriesList, percent)
        for result, exc in zip(results, [[], [51, 52]]):
            self.assertListEqual(return_greater(result, percent), exc)

    def test_remove_below_percentile(self):
        seriesList = self._generate_series_list()
        percent = 50
        results = functions.removeBelowPercentile({}, seriesList, percent)
        expected = [[], [], [1] * 4]

        for i, result in enumerate(results):
            self.assertListEqual(return_less(result, percent), expected[i])

    def test_remove_above_value(self):
        seriesList = self._generate_series_list()
        value = 5
        results = functions.removeAboveValue({}, seriesList, value)
        for result in results:
            self.assertListEqual(return_greater(result, value), [])

    def test_remove_below_value(self):
        seriesList = self._generate_series_list()
        value = 5
        results = functions.removeBelowValue({}, seriesList, value)
        for result in results:
            self.assertListEqual(return_less(result, value), [])

    def test_limit(self):
        seriesList = self._generate_series_list()
        limit = len(seriesList) - 1
        results = functions.limit({}, seriesList, limit)
        self.assertEqual(len(results), limit,
                         "More than {0} results returned".format(limit))

    def _verify_series_options(self, seriesList, name, value):
        """
        Verify a given option is set and True for each series in a
        series list
        """
        for series in seriesList:
            self.assertIn(name, series.options)
            if value is True:
                test_func = self.assertTrue
            else:
                test_func = self.assertEqual

            test_func(series.options.get(name), value)

    def test_second_y_axis(self):
        seriesList = self._generate_series_list()
        results = functions.secondYAxis({}, seriesList)
        self._verify_series_options(results, "secondYAxis", True)

    def test_draw_as_infinite(self):
        seriesList = self._generate_series_list()
        results = functions.drawAsInfinite({}, seriesList)
        self._verify_series_options(results, "drawAsInfinite", True)

    def test_line_width(self):
        seriesList = self._generate_series_list()
        width = 10
        results = functions.lineWidth({}, seriesList, width)
        self._verify_series_options(results, "lineWidth", width)

    def test_transform_null(self):
        seriesList = self._generate_series_list()
        transform = -5
        results = functions.transformNull({}, copy.deepcopy(seriesList),
                                          transform)

        for counter, series in enumerate(seriesList):
            if None not in series:
                continue
            # If the None values weren't transformed, there is a problem
            self.assertNotIn(None, results[counter],
                             "tranformNull should remove all None values")
            # Anywhere a None was in the original series, verify it
            # was transformed to the given value it should be.
            for i, value in enumerate(series):
                if value is None:
                    result_val = results[counter][i]
                    self.assertEqual(
                        transform, result_val,
                        "Transformed value should be {0}, not {1}".format(
                            transform, result_val))

    def test_alias(self):
        seriesList = self._generate_series_list()
        substitution = "Ni!"
        results = functions.alias({}, seriesList, substitution)
        for series in results:
            self.assertEqual(series.name, substitution)

    def test_alias_sub(self):
        seriesList = self._generate_series_list()
        substitution = "Shrubbery"
        results = functions.aliasSub({}, seriesList, "^\w+", substitution)
        for series in results:
            self.assertTrue(
                series.name.startswith(substitution),
                "aliasSub should replace the name with {0}".format(
                    substitution))

    # TODO: Add tests for * globbing and {} matching to this
    def test_alias_by_node(self):
        seriesList = self._generate_series_list()

        def verify_node_name(*nodes):
            # Use deepcopy so the original seriesList is unmodified
            results = functions.aliasByNode({}, copy.deepcopy(seriesList),
                                            *nodes)

            for i, series in enumerate(results):
                fragments = seriesList[i].name.split('.')
                # Super simplistic. Doesn't match {thing1,thing2}
                # or glob with *, both of what graphite allow you to use
                expected_name = '.'.join([fragments[i] for i in nodes])
                self.assertEqual(series.name, expected_name)

        verify_node_name(1)
        verify_node_name(1, 0)
        verify_node_name(-1, 0)

        # Verify broken input causes broken output
        with self.assertRaises(IndexError):
            verify_node_name(10000)

    def test_alpha(self):
        seriesList = self._generate_series_list()
        alpha = 0.5
        results = functions.alpha({}, seriesList, alpha)
        self._verify_series_options(results, "alpha", alpha)

    def test_color(self):
        seriesList = self._generate_series_list()
        color = "red"
        # Leave the original seriesList unmodified
        results = functions.color({}, copy.deepcopy(seriesList), color)

        for i, series in enumerate(results):
            self.assertTrue(
                hasattr(series, "color"),
                "The transformed seriesList is missing the 'color' attribute",
            )
            self.assertFalse(
                hasattr(seriesList[i], "color"),
                "The original seriesList shouldn't have a 'color' attribute",
            )
            self.assertEqual(series.color, color)

    def test_scale(self):
        seriesList = self._generate_series_list()
        multiplier = 2
        # Leave the original seriesList undisturbed for verification
        results = functions.scale({}, copy.deepcopy(seriesList), multiplier)
        for i, series in enumerate(results):
            for counter, value in enumerate(series):
                if value is None:
                    continue
                original_value = seriesList[i][counter]
                expected_value = original_value * multiplier
                self.assertEqual(value, expected_value)

    def test_average_series(self):
        series = self._generate_series_list()
        average = functions.averageSeries({}, series)[0]
        self.assertEqual(average[:3], [1.0, 5/3., 3.0])

    def test_average_series_wildcards(self):
        series = self._generate_series_list()
        average = functions.averageSeriesWithWildcards({}, series, 1)[0]
        self.assertEqual(average[:3], [1.0, 5/3., 3.0])
        self.assertEqual(average.name, 'collectd.load.value')

    def _generate_mr_series(self):
        seriesList = [
            TimeSeries('group.server1.metric1', 0, 1, 1, [None]),
            TimeSeries('group.server1.metric2', 0, 1, 1, [None]),
            TimeSeries('group.server2.metric1', 0, 1, 1, [None]),
            TimeSeries('group.server2.metric2', 0, 1, 1, [None]),
        ]
        mappedResult = [
            [seriesList[0], seriesList[1]],
            [seriesList[2], seriesList[3]]
        ]
        return seriesList, mappedResult

    def test_mapSeries(self):
        seriesList, expectedResult = self._generate_mr_series()
        results = functions.mapSeries({}, copy.deepcopy(seriesList), 1)
        self.assertEqual(results, expectedResult)

    def test_reduceSeries(self):
        sl, inputList = self._generate_mr_series()
        expectedResult = [
            TimeSeries('group.server1.reduce.mock', 0, 1, 1, [None]),
            TimeSeries('group.server2.reduce.mock', 0, 1, 1, [None])
        ]
        resultSeriesList = [TimeSeries('mock(series)', 0, 1, 1, [None])]
        mock = MagicMock(return_value=resultSeriesList)
        with patch.dict(app.config['GRAPHITE']['functions'], {'mock': mock}):
            results = functions.reduceSeries({}, copy.deepcopy(inputList),
                                             "mock", 2, "metric1", "metric2")
            self.assertEqual(results, expectedResult)
        self.assertEqual(mock.mock_calls, [call({}, inputList[0]),
                                           call({}, inputList[1])])

    def test_sum_series(self):
        series = self._generate_series_list()
        sum_ = functions.sumSeries({}, series)[0]
        self.assertEqual(sum_.pathExpression,
                         "sumSeries(collectd.test-db1.load.value,"
                         "collectd.test-db2.load.value,"
                         "collectd.test-db3.load.value)")
        self.assertEqual(sum_[:3], [3, 5, 6])

    def test_sum_series_wildcards(self):
        series = self._generate_series_list()
        sum_ = functions.sumSeriesWithWildcards({}, series, 1)[0]
        self.assertEqual(sum_.pathExpression,
                         "sumSeries(collectd.test-db3.load.value,"
                         "sumSeries(collectd.test-db1.load.value,"
                         "collectd.test-db2.load.value))")
        self.assertEqual(sum_[:3], [3, 5, 6])

    def test_diff_series(self):
        series = self._generate_series_list()[:2]
        diff = functions.diffSeries({}, [series[0]], [series[1]])[0]
        self.assertEqual(diff[:3], [-2, -2, -2])

    def test_stddev_series(self):
        series = self._generate_series_list()[:2]
        dev = functions.stddevSeries({}, [series[0]], [series[1]])[0]
        self.assertEqual(dev[:3], [1.0, 1.0, 1.0])

    def test_min_series(self):
        series = self._generate_series_list()[:2]
        min_ = functions.minSeries({}, [series[0]], [series[1]])[0]
        self.assertEqual(min_[:3], [0, 1, 2])

    def test_max_series(self):
        series = self._generate_series_list()[:2]
        max_ = functions.maxSeries({}, [series[0]], [series[1]])[0]
        self.assertEqual(max_[:3], [2, 3, 4])

    def test_range_of_series(self):
        series = self._generate_series_list()[:2]
        range_ = functions.rangeOfSeries({}, [series[0]], [series[1]])[0]
        self.assertEqual(range_[:3], [2, 2, 2])

    def test_percentile_of_series(self):
        series = self._generate_series_list()[:2]
        percent = functions.percentileOfSeries({}, series, 50)[0]
        self.assertEqual(percent[:3], [2, 3, 4])

        with self.assertRaises(ValueError):
            functions.percentileOfSeries({}, series, -1)

    def test_keep_last_value(self):
        series = self._generate_series_list()[2]
        last = functions.keepLastValue({}, [series], limit=97)[0]
        self.assertEqual(last[:3], [1, 1, 1])

        series[-1] = 1
        last = functions.keepLastValue({}, [series], limit=97)[0]
        self.assertEqual(last[:3], [1, 1, 1])

    def test_as_percent(self):
        series = self._generate_series_list()
        perc = functions.asPercent({}, series)[0]
        self.assertEqual(perc[:2], [0.0, 20.0])
        self.assertEqual(perc[3], 37.5)

        with self.assertRaises(ValueError):
            functions.asPercent({}, series[:2], [1, 2])

        perc = functions.asPercent({}, series[:2], [series[2]])[0]
        self.assertEqual(perc[:2], [0.0, 100.0])

        perc = functions.asPercent({}, series[:2], 12)[0]
        self.assertEqual(perc[:2], [0.0, 8.333333333333332])

    def test_divide_series(self):
        series = self._generate_series_list()
        div = functions.divideSeries({}, [series[0]], [series[1]])[0]
        self.assertEqual(div[:3], [0, 1/3., 0.5])

        with self.assertRaises(ValueError):
            functions.divideSeries({}, [series[0]], [1, 2])

    def test_multiply_series(self):
        series = self._generate_series_list()
        mul = functions.multiplySeries({}, series[:2])[0]
        self.assertEqual(mul[:3], [0, 3, 8])

        mul = functions.multiplySeries({}, series[:1])[0]
        self.assertEqual(mul[:3], [0, 1, 2])

    def test_weighted_average(self):
        series = self._generate_series_list()
        weight = functions.weightedAverage({}, [series[0]], [series[1]], 0)
        self.assertEqual(weight[:3], [0, 1, 2])

    def test_moving_median(self):
        series = self._generate_series_list()
        for s in series:
            self.write_series(s)
        median = functions.movingMedian({
            'startTime': parseATTime('-100s')
        }, series, '5s')[0]
        try:
            self.assertEqual(median[:4], [1, 0, 1, 1])
        except AssertionError:  # time race condition
            self.assertEqual(median[:4], [1, 1, 1, 1])

        median = functions.movingMedian({
            'startTime': parseATTime('-100s')
        }, series, 5)[0]
        try:
            self.assertEqual(median[:4], [1, 0, 1, 1])
        except AssertionError:
            self.assertEqual(median[:4], [1, 1, 1, 1])

    def test_invert(self):
        series = self._generate_series_list()
        invert = functions.invert({}, series)[0]
        self.assertEqual(invert[:5], [None, 1, 1/2., 1/3., 1/4.])

    def test_scale_to_seconds(self):
        series = self._generate_series_list()
        scaled = functions.scaleToSeconds({}, series, 10)[0]
        self.assertEqual(scaled[:3], [0, 10, 20])

    def test_absolute(self):
        series = self._generate_series_list(config=[range(-50, 50)])
        absolute = functions.absolute({}, series)[0]
        self.assertEqual(absolute[:3], [50, 49, 48])

    def test_offset(self):
        series = self._generate_series_list(config=[[None] + list(range(99))])
        offset = functions.offset({}, series, -50)[0]
        self.assertEqual(offset[:3], [None, -50, -49])

    def test_offset_to_zero(self):
        series = self._generate_series_list(
            config=[[None] + list(range(10, 110))])
        offset = functions.offsetToZero({}, series)[0]
        self.assertEqual(offset[:3], [None, 0, 1])

    def test_moving_average(self):
        series = self._generate_series_list()
        for s in series:
            self.write_series(s)
        average = functions.movingAverage({
            'startTime': parseATTime('-100s')
        }, series, '5s')[0]
        try:
            self.assertEqual(list(average)[:4], [0.5, 1/3., 0.5, 0.8])
        except AssertionError:  # time race condition
            self.assertEqual(list(average)[:4], [1, 3/4., 0.8, 1.2])

        average = functions.movingAverage({
            'startTime': parseATTime('-100s')
        }, series, 5)[0]
        try:
            self.assertEqual(average[:4], [0.5, 1/3., 0.5, 0.8])
        except AssertionError:
            self.assertEqual(list(average)[:4], [1, 3/4., 0.8, 1.2])

    def test_cumulative(self):
        series = self._generate_series_list(config=[range(100)])
        series[0].consolidate(2)
        cumul = functions.cumulative({}, series)[0]
        self.assertEqual(list(cumul)[:3], [1, 5, 9])

    def consolidate_by(self):
        series = self._generate_series_list(config=[range(100)])
        series[0].consolidate(2)
        min_ = functions.consolidateBy({}, series, 'min')
        self.assertEqual(list(min_)[:3], [0, 2, 4])

        max_ = functions.consolidateBy({}, series, 'max')
        self.assertEqual(list(max_)[:3], [1, 3, 5])

        avg_ = functions.consolidateBy({}, series, 'average')
        self.assertEqual(list(avg_)[:3], [0.5, 2.3, 4.5])

    def test_derivative(self):
        series = self._generate_series_list(config=[range(100)])
        der = functions.derivative({}, series)[0]
        self.assertEqual(der[:3], [None, 1, 1])

    def test_per_second(self):
        series = self._generate_series_list(config=[range(100)])
        series[0].step = 0.1
        per_sec = functions.perSecond({}, series)[0]
        self.assertEqual(per_sec[:3], [None, 10, 10])

        series = self._generate_series_list(config=[reversed(range(100))])
        series[0].step = 0.1
        per_sec = functions.perSecond({}, series, maxValue=20)[0]
        self.assertEqual(per_sec[:3], [None, None, None])

    def test_integral(self):
        series = self._generate_series_list(
            config=[list(range(1, 10)) * 9 + [None] * 10])
        integral = functions.integral({}, series)[0]
        self.assertEqual(integral[:3], [1, 3, 6])
        self.assertEqual(integral[-11:], [405] + [None] * 10)

    def test_non_negative_derivative(self):
        series = self._generate_series_list(config=[list(range(10)) * 10])
        der = functions.nonNegativeDerivative({}, series)[0]
        self.assertEqual(list(der),
                         [1 if i % 10 else None for i in range(100)])

        series = self._generate_series_list(
            config=[list(reversed(range(10))) * 10])
        der = functions.nonNegativeDerivative({}, series, maxValue=10)[0]
        self.assertEqual(list(der),
                         [None] + [10 if i % 10 else 9 for i in range(1, 100)])

    def test_stacked(self):
        series = self._generate_series_list(
            config=[[None] + list(range(99)), range(50, 150)])
        stacked = functions.stacked({}, series)[1]
        self.assertEqual(stacked[:3], [50, 51, 53])

        stacked = functions.stacked({'totalStack': {}}, series)[1]
        self.assertEqual(stacked[:3], [50, 51, 53])
        self.assertEqual(stacked.name, 'stacked(collectd.test-db2.load.value)')

        stacked = functions.stacked({}, series, 'tx')[1]
        self.assertEqual(stacked[:3], [50, 51, 53])
        self.assertEqual(stacked.name, series[1].name)

    def test_area_between(self):
        series = self._generate_series_list()
        lower, upper = functions.areaBetween({}, series[0], series[1])
        self.assertEqual(lower.options, {'stacked': True, 'invisible': True})
        self.assertEqual(upper.options, {'stacked': True})

    def test_cactistyle(self):
        series = self._generate_series_list()
        cacti = functions.cactiStyle({}, series)
        self.assertEqual(
            cacti[0].name,
            "collectd.test-db1.load.value Current:100.00    Max:100.00    "
            "Min:0.00    ")

        series = self._generate_series_list()
        cacti = functions.cactiStyle({}, series, 'si')
        self.assertEqual(
            cacti[0].name,
            "collectd.test-db1.load.value Current:100.00    Max:100.00    "
            "Min:0.00    ")

        series = self._generate_series_list(config=[[None] * 100])
        cacti = functions.cactiStyle({}, series)
        self.assertEqual(
            cacti[0].name,
            "collectd.test-db1.load.value Current:nan     Max:nan     "
            "Min:nan     ")

    def test_alias_by_metric(self):
        series = self._generate_series_list(config=[range(100)])
        alias = functions.aliasByMetric({}, series)[0]
        self.assertEqual(alias.name, "value")

    def test_legend_value(self):
        series = self._generate_series_list(config=[range(100)])
        legend = functions.legendValue({}, series, 'min', 'max', 'avg')[0]
        self.assertEqual(
            legend.name,
            "collectd.test-db1.load.value (min: 0) (max: 99) (avg: 49.5)")

        series = self._generate_series_list(config=[range(100)])
        series[0].name = 'load.value'
        legend = functions.legendValue({}, series, 'avg', 'si')[0]
        self.assertEqual(
            legend.name,
            "load.value          avg  49.50     ")

        series = self._generate_series_list(config=[range(100)])
        legend = functions.legendValue({}, series, 'lol')[0]
        self.assertEqual(
            legend.name, "collectd.test-db1.load.value (lol: (?))")

        series = self._generate_series_list(config=[[None] * 100])
        legend = functions.legendValue({}, series, 'min')[0]
        self.assertEqual(
            legend.name, "collectd.test-db1.load.value (min: None)")

    def test_substr(self):
        series = self._generate_series_list(config=[range(100)])
        sub = functions.substr({}, series, 1)[0]
        self.assertEqual(sub.name, "test-db1.load.value")

        series = functions.alias(
            {}, self._generate_series_list(config=[range(100)]),
            '(foo.bar, "baz")')
        sub = functions.substr({}, series, 1)[0]
        self.assertEqual(sub.name, "bar")

        series = self._generate_series_list(config=[range(100)])
        sub = functions.substr({}, series, 0, 2)[0]
        self.assertEqual(sub.name, "collectd.test-db1")

    def test_log(self):
        series = self._generate_series_list(config=[range(101)])
        log = functions.logarithm({}, series)[0]
        self.assertEqual(log[0], None)
        self.assertEqual(log[1], 0)
        self.assertEqual(log[10], 1)
        self.assertEqual(log[100], 2)

        series = self._generate_series_list(config=[[None] * 100])
        log = functions.logarithm({}, series)[0]
        self.assertEqual(list(log), [None] * 100)

    def test_max_above(self):
        series = self._generate_series_list(config=[range(100)])
        max_above = functions.maximumAbove({}, series, 200)
        self.assertEqual(max_above, [])
        max_above = functions.maximumAbove({}, series, 98)
        self.assertEqual(max_above, series)

    def test_min_above(self):
        series = self._generate_series_list(config=[range(100, 200)])
        min_above = functions.minimumAbove({}, series, 200)
        self.assertEqual(min_above, [])
        min_above = functions.minimumAbove({}, series, 99)
        self.assertEqual(min_above, series)

    def test_max_below(self):
        series = self._generate_series_list(config=[range(100)])
        max_below = functions.maximumBelow({}, series, 98)
        self.assertEqual(max_below, [])
        max_below = functions.maximumBelow({}, series, 100)
        self.assertEqual(max_below, series)

    def test_highest_current(self):
        series = self._generate_series_list(config=[range(100),
                                                    range(10, 110),
                                                    range(200, 300)])
        highest = functions.highestCurrent({}, series)[0]
        self.assertEqual(highest.name, "collectd.test-db3.load.value")

        highest = functions.highestCurrent({}, series, 2)
        self.assertEqual(highest[0].name, "collectd.test-db2.load.value")

    def test_lowest_current(self):
        series = self._generate_series_list(config=[range(100),
                                                    range(10, 110),
                                                    range(200, 300)])
        lowest = functions.lowestCurrent({}, series)[0]
        self.assertEqual(lowest.name, "collectd.test-db1.load.value")

    def test_current_above(self):
        series = self._generate_series_list(config=[range(100)])
        above = functions.currentAbove({}, series, 200)
        self.assertEqual(len(above), 0)

        above = functions.currentAbove({}, series, 98)
        self.assertEqual(above, series)

    def test_current_below(self):
        series = self._generate_series_list(config=[range(100)])
        below = functions.currentBelow({}, series, 50)
        self.assertEqual(len(below), 0)
        below = functions.currentBelow({}, series, 100)
        self.assertEqual(below, series)

    def test_highest_average(self):
        series = self._generate_series_list(config=[
            range(100),
            range(50, 150),
            list(range(150, 200)) + [None] * 50])
        highest = functions.highestAverage({}, series, 2)
        self.assertEqual(len(highest), 2)
        self.assertEqual(highest, [series[1], series[2]])

        highest = functions.highestAverage({}, series)
        self.assertEqual(highest, [series[2]])

    def test_lowest_average(self):
        series = self._generate_series_list(config=[
            range(100),
            range(50, 150),
            list(range(150, 200)) + [None] * 50])
        lowest = functions.lowestAverage({}, series, 2)
        self.assertEqual(len(lowest), 2)
        self.assertEqual(lowest, [series[0], series[1]])

        lowest = functions.lowestAverage({}, series)
        self.assertEqual(lowest, [series[0]])

    def test_average_above(self):
        series = self._generate_series_list(config=[range(100)])
        above = functions.averageAbove({}, series, 50)
        self.assertEqual(len(above), 0)

        above = functions.averageAbove({}, series, 40)
        self.assertEqual(above, series)

    def test_average_below(self):
        series = self._generate_series_list(config=[range(100)])
        below = functions.averageBelow({}, series, 40)
        self.assertEqual(len(below), 0)

        below = functions.averageBelow({}, series, 50)
        self.assertEqual(below, series)

    def test_average_outside_percentile(self):
        series = self._generate_series_list(
            config=[range(i, i+100) for i in range(50)])
        outside = functions.averageOutsidePercentile({}, series, 95)
        self.assertEqual(outside, series[:3] + series[-2:])

        outside = functions.averageOutsidePercentile({}, series, 5)
        self.assertEqual(outside, series[:3] + series[-2:])

    def test_remove_between_percentile(self):
        series = self._generate_series_list(
            config=[range(i, i+100) for i in range(50)])
        not_between = functions.removeBetweenPercentile({}, series, 95)
        self.assertEqual(not_between, series[:3] + series[-2:])

        not_between = functions.removeBetweenPercentile({}, series, 5)
        self.assertEqual(not_between, series[:3] + series[-2:])

    def test_sort_by_name(self):
        series = list(reversed(self._generate_series_list(
            config=[range(100) for i in range(10)])))
        sorted_s = functions.sortByName({}, series)
        self.assertEqual(sorted_s[0].name, series[-1].name)

    def test_sort_by_total(self):
        series = self._generate_series_list(
            config=[range(i, i+100) for i in range(10)])
        sorted_s = functions.sortByTotal({}, series)
        self.assertEqual(sorted_s[0].name, series[-1].name)

    def test_sort_by_maxima(self):
        series = list(reversed(self._generate_series_list(
            config=[range(i, i+100) for i in range(10)])))
        sorted_s = functions.sortByMaxima({}, series)
        self.assertEqual(sorted_s[0].name, series[-1].name)

    def test_sort_by_minima(self):
        series = list(reversed(self._generate_series_list(
            config=[range(i, i+100) for i in range(10)])))
        sorted_s = functions.sortByMinima({}, series)
        self.assertEqual(sorted_s[0].name, series[-1].name)

    def test_use_series_above(self):
        series = self._generate_series_list(
            config=[list(range(90)) + [None] * 10])
        series[0].pathExpression = 'bar'

        for s in series:
            self.write_series(s)

        series[0].name = 'foo'

        ctx = {
            'startTime': parseATTime('-100s'),
            'endTime': parseATTime('now'),
        }
        above = functions.useSeriesAbove(ctx, series, 10, 'foo', 'bar')[0]
        self.assertEqual(above[0], 2)

        above = functions.useSeriesAbove(ctx, series, 100, 'foo', 'bar')
        self.assertEqual(len(above), 0)

        above = functions.useSeriesAbove(ctx, series, 10, 'foo', 'baz')
        self.assertEqual(len(above), 0)

    def test_most_deviant(self):
        series = self._generate_series_list(config=[
            range(1, i * 100, i) for i in range(1, 10)] + [[None] * 100])
        deviant = functions.mostDeviant({}, series, 8)
        self.assertEqual(deviant[0].name, 'collectd.test-db9.load.value')

    def test_stdev(self):
        series = self._generate_series_list(config=[
            [x**1.5 for x in range(100)], [None] * 100])
        dev = functions.stdev({}, series, 10)[0]
        self.assertEqual(dev[1], 0.5)

    def test_holt_winters(self):
        timespan = 3600 * 24 * 8  # 8 days
        stop = int(time.time())
        step = 100
        series = TimeSeries('foo.bar',
                            stop - timespan,
                            stop,
                            step,
                            [x**1.5 for x in range(0, timespan, step)])
        series[10] = None
        series.pathExpression = 'foo.bar'
        self.write_series(series, [(100, timespan)])

        ctx = {
            'startTime': parseATTime('-1d'),
        }
        analysis = functions.holtWintersForecast(ctx, [series])
        self.assertEqual(len(analysis), 1)

        analysis = functions.holtWintersConfidenceBands(ctx, [series])
        self.assertEqual(len(analysis), 2)

        analysis = functions.holtWintersConfidenceArea(ctx, [series])
        self.assertEqual(len(analysis), 2)

        analysis = functions.holtWintersAberration(ctx, [series])
        self.assertEqual(len(analysis), 1)

    def test_dashed(self):
        series = self._generate_series_list(config=[range(100)])
        dashed = functions.dashed({}, series)[0]
        self.assertEqual(dashed.options, {'dashed': 5})

        dashed = functions.dashed({}, series, 12)[0]
        self.assertEqual(dashed.options, {'dashed': 12})

    def test_time_stack(self):
        timespan = 3600 * 24 * 8  # 8 days
        stop = int(time.time())
        step = 100
        series = TimeSeries('foo.bar',
                            stop - timespan,
                            stop,
                            step,
                            [x**1.5 for x in range(0, timespan, step)])
        series[10] = None
        series.pathExpression = 'foo.bar'
        self.write_series(series, [(100, timespan)])

        ctx = {'startTime': parseATTime('-1d'),
               'endTime': parseATTime('now')}
        stack = functions.timeStack(ctx, [series], '1d', 0, 7)
        self.assertEqual(len(stack), 7)

        stack = functions.timeStack(ctx, [series], '-1d', 0, 7)
        self.assertEqual(len(stack), 7)

    def test_time_shift(self):
        timespan = 3600 * 24 * 8  # 8 days
        stop = int(time.time())
        step = 100
        series = TimeSeries('foo.bar',
                            stop - timespan,
                            stop,
                            step,
                            [x**1.5 for x in range(0, timespan, step)])
        series[10] = None
        series.pathExpression = 'foo.bar'
        self.write_series(series, [(100, timespan)])

        ctx = {'startTime': parseATTime('-1d'),
               'endTime': parseATTime('now')}
        shift = functions.timeShift(ctx, [series], '1d')
        self.assertEqual(len(shift), 1)

        shift = functions.timeShift(ctx, [series], '-1d', False)
        self.assertEqual(len(shift), 1)

        shift = functions.timeShift(ctx, [], '-1d')
        self.assertEqual(len(shift), 0)

    def test_constant_line(self):
        ctx = {
            'startTime': parseATTime('-1d'),
            'endTime': parseATTime('now'),
        }
        line = functions.constantLine(ctx, 12)[0]
        self.assertEqual(list(line), [12, 12])
        self.assertEqual(line.step, 3600 * 24)

    def test_agg_line(self):
        ctx = {
            'startTime': parseATTime('-1d'),
            'endTime': parseATTime('now'),
        }
        series = self._generate_series_list(config=[range(100)])
        line = functions.aggregateLine(ctx, series)[0]
        self.assertEqual(list(line), [49.5, 49.5])

        with self.assertRaises(ValueError):
            functions.aggregateLine(ctx, series, 'foo')

    def test_threshold(self):
        ctx = {
            'startTime': parseATTime('-1d'),
            'endTime': parseATTime('now'),
        }
        threshold = functions.threshold(ctx, 123, 'foobar')[0]
        self.assertEqual(list(threshold), [123, 123])

        threshold = functions.threshold(ctx, 123)[0]
        self.assertEqual(list(threshold), [123, 123])

        threshold = functions.threshold(ctx, 123, 'foo', 'red')[0]
        self.assertEqual(list(threshold), [123, 123])
        self.assertEqual(threshold.color, 'red')

    def test_non_null(self):
        one = [None, 0, 2, 3] * 25
        two = [None, 3, 1] * 33 + [None]
        series = self._generate_series_list(config=[one, two])
        non_null = functions.isNonNull({}, series)
        self.assertEqual(non_null[0][:5], [0, 1, 1, 1, 0])
        self.assertEqual(non_null[1][:5], [0, 1, 1, 0, 1])

    def test_identity(self):
        ctx = {
            'startTime': parseATTime('-1d'),
            'endTime': parseATTime('now'),
        }
        identity = functions.identity(ctx, 'foo')[0]
        self.assertEqual(identity.end - identity.start, 3600 * 24)

    def test_count(self):
        series = self._generate_series_list(config=[range(100),
                                                    range(100, 200)])
        count = functions.countSeries({}, series)[0]
        self.assertEqual(list(count), [2] * 100)

    def test_group_by_node(self):
        series = self._generate_series_list(config=[range(100),
                                                    range(100, 200)])
        grouped = functions.groupByNode({}, series, 1, 'sumSeries')
        first, second = grouped
        self.assertEqual(first.name, 'test-db1')
        self.assertEqual(second.name, 'test-db2')

        series[1].name = series[0].name
        grouped = functions.groupByNode({}, series, 1, 'sumSeries')
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0].name, 'test-db1')
        self.assertEqual(list(grouped[0])[:3], [100, 102, 104])

    def test_exclude(self):
        series = self._generate_series_list(config=[range(100),
                                                    range(100, 200)])
        excl = functions.exclude({}, series, 'db1')
        self.assertEqual(excl, [series[1]])

    def test_grep(self):
        series = self._generate_series_list(config=[range(100),
                                                    range(100, 200)])
        grep = functions.grep({}, series, 'db1')
        self.assertEqual(grep, [series[0]])

    def test_smart_summarize(self):
        ctx = {
            'startTime': parseATTime('-1min'),
            'endTime': parseATTime('now'),
        }
        series = self._generate_series_list(config=[range(100)])
        for s in series:
            self.write_series(s)
        summ = functions.smartSummarize(ctx, series, '5s')[0]
        self.assertEqual(summ[:3], [220, 245, 270])

        summ = functions.smartSummarize(ctx, series, '5s', 'avg')[0]
        self.assertEqual(summ[:3], [44, 49, 54])

        summ = functions.smartSummarize(ctx, series, '5s', 'last')[0]
        self.assertEqual(summ[:3], [46, 51, 56])

        summ = functions.smartSummarize(ctx, series, '5s', 'max')[0]
        self.assertEqual(summ[:3], [46, 51, 56])

        summ = functions.smartSummarize(ctx, series, '5s', 'min')[0]
        self.assertEqual(summ[:3], [42, 47, 52])

    def test_summarize(self):
        series = self._generate_series_list(config=[list(range(99)) + [None]])

        # summarize is not consistent enough to allow testing exact output
        functions.summarize({}, series, '5s')[0]
        functions.summarize({}, series, '5s', 'avg', True)[0]
        functions.summarize({}, series, '5s', 'last')[0]
        functions.summarize({}, series, '5s', 'min')[0]
        functions.summarize({}, series, '5s', 'max')[0]

    def test_hitcount(self):
        ctx = {
            'startTime': parseATTime('-1min'),
            'endTime': parseATTime('now'),
        }
        series = self._generate_series_list(config=[list(range(99)) + [None]])
        for s in series:
            self.write_series(s)

        hit = functions.hitcount(ctx, series, '5s')[0]
        self.assertEqual(hit[:3], [0, 15, 40])

        hit = functions.hitcount(ctx, series, '5s', True)[0]
        self.assertEqual(hit[:3], [220, 245, 270])

    def test_random_walk(self):
        ctx = {
            'startTime': parseATTime('-12h'),
            'endTime': parseATTime('now'),
        }
        walk = functions.randomWalkFunction(ctx, 'foo')[0]
        self.assertEqual(len(walk), 721)

########NEW FILE########
__FILENAME__ = test_http
from . import TestCase


class HttpTestCase(TestCase):
    def test_cors(self):
        response = self.app.options('/render')
        self.assertFalse(
            'Access-Control-Allow-Origin' in response.headers.keys())

        response = self.app.options('/render', headers=(
            ('Origin', 'https://example.com'),
        ))
        self.assertEqual(response.headers['Access-Control-Allow-Origin'],
                         'https://example.com')

        response = self.app.options('/render', headers=(
            ('Origin', 'http://foo.example.com:8888'),
        ))
        self.assertEqual(response.headers['Access-Control-Allow-Origin'],
                         'http://foo.example.com:8888')

        response = self.app.options('/', headers=(
            ('Origin', 'http://foo.example.com'),
        ))
        self.assertFalse(
            'Access-Control-Allow-Origin' in response.headers.keys())

    def test_trailing_slash(self):
        response = self.app.get('/render?target=foo')
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/render/?target=foo')
        self.assertEqual(response.status_code, 200)

########NEW FILE########
__FILENAME__ = test_intervals
from graphite_api.intervals import IntervalSet, Interval, union_overlapping

from . import TestCase


class IntervalTestCase(TestCase):
    def test_interval(self):
        with self.assertRaises(ValueError):
            Interval(1, 0)

        i = Interval(0, 1)
        j = Interval(1, 2)
        k = Interval(0, 1)
        l = Interval(0, 0)
        self.assertNotEqual(i, j)
        self.assertEqual(i, k)
        self.assertEqual(hash(i), hash(k))

        with self.assertRaises(TypeError):
            len(i)

        self.assertTrue(j > i)

        self.assertTrue(i)
        self.assertFalse(l)

        self.assertEqual(repr(i), '<Interval: (0, 1)>')

        self.assertIsNone(i.intersect(j))
        self.assertEqual(i.intersect(k), k)
        self.assertTrue(i.overlaps(j))
        self.assertEqual(i.union(j), Interval(0, 2))

        with self.assertRaises(TypeError):
            j.union(l)

        self.assertEqual(union_overlapping([i, j, k, l]),
                         [Interval(0, 2)])

    def test_interval_set(self):
        i = Interval(0, 1)
        j = Interval(1, 2)

        s = IntervalSet([i, j])
        self.assertEqual(repr(s), '[<Interval: (0, 2)>]')
        s = IntervalSet([i, j], disjoint=True)

        it = iter(s)
        self.assertEqual(next(it), i)
        self.assertEqual(next(it), j)

        self.assertTrue(s)
        self.assertFalse(IntervalSet([]))

        self.assertEqual(s - IntervalSet([i]),
                         IntervalSet([j]))

        self.assertFalse(IntervalSet([]).intersect(s))

        self.assertEqual(s.union(IntervalSet([Interval(3, 4)])),
                         IntervalSet([Interval(3, 4), i, j]))

########NEW FILE########
__FILENAME__ = test_metrics
import os.path
from graphite_api._vendor import whisper

from . import TestCase, WHISPER_DIR


class MetricsTests(TestCase):
    def _create_dbs(self):
        for db in (
            ('test', 'foo.wsp'),
            ('test', 'wat', 'welp.wsp'),
            ('test', 'bar', 'baz.wsp'),
        ):
            db_path = os.path.join(WHISPER_DIR, *db)
            os.makedirs(os.path.dirname(db_path))
            whisper.create(db_path, [(1, 60)])

    def test_find(self):
        url = '/metrics/find'

        response = self.app.get(url)
        self.assertEqual(response.status_code, 400)

        response = self.app.get(url, query_string={'query': 'test'})
        self.assertJSON(response, [])

        response = self.app.get(url, query_string={'query': 'test',
                                                   'format': 'completer'})
        self.assertJSON(response, {'metrics': []})

        self._create_dbs()

        response = self.app.get(url, query_string={'query': 'test.*',
                                                   'format': 'treejson'})
        self.assertJSON(response, [{
            'allowChildren': 1,
            'expandable': 1,
            'id': 'test.bar',
            'leaf': 0,
            'text': 'bar',
        }, {
            'allowChildren': 1,
            'expandable': 1,
            'id': 'test.wat',
            'leaf': 0,
            'text': 'wat',
        }, {
            'allowChildren': 0,
            'expandable': 0,
            'id': 'test.foo',
            'leaf': 1,
            'text': 'foo',
        }])

        response = self.app.get(url, query_string={'query': 'test.*',
                                                   'format': 'treejson',
                                                   'wildcards': 1})
        self.assertJSON(response, [{
            'text': '*',
            'expandable': 1,
            'leaf': 0,
            'id': 'test.*',
            'allowChildren': 1,
        }, {
            'allowChildren': 1,
            'expandable': 1,
            'id': 'test.bar',
            'leaf': 0,
            'text': 'bar',
        }, {
            'allowChildren': 1,
            'expandable': 1,
            'id': 'test.wat',
            'leaf': 0,
            'text': 'wat',
        }, {
            'allowChildren': 0,
            'expandable': 0,
            'id': 'test.foo',
            'leaf': 1,
            'text': 'foo',
        }])

        response = self.app.get(url, query_string={'query': 'test.*',
                                                   'format': 'completer'})
        self.assertJSON(response, {'metrics': [{
            'is_leaf': 0,
            'name': 'bar',
            'path': 'test.bar.',
        }, {
            'is_leaf': 1,
            'name': 'foo',
            'path': 'test.foo',
        }, {
            'is_leaf': 0,
            'name': 'wat',
            'path': 'test.wat.',
        }]})

        response = self.app.get(url, query_string={'query': 'test.*',
                                                   'wildcards': 1,
                                                   'format': 'completer'})
        self.assertJSON(response, {'metrics': [{
            'is_leaf': 0,
            'name': 'bar',
            'path': 'test.bar.',
        }, {
            'is_leaf': 1,
            'name': 'foo',
            'path': 'test.foo',
        }, {
            'is_leaf': 0,
            'name': 'wat',
            'path': 'test.wat.',
        }, {
            'name': '*',
        }]})

    def test_find_validation(self):
        url = '/metrics/find'
        response = self.app.get(url, query_string={'query': 'foo',
                                                   'wildcards': 'aaa'})
        self.assertJSON(response, {'errors': {'wildcards': 'must be 0 or 1.'}},
                        status_code=400)

        response = self.app.get(url, query_string={'query': 'foo',
                                                   'from': 'aaa',
                                                   'until': 'bbb'})
        self.assertJSON(response, {'errors': {
            'from': 'must be an epoch timestamp.',
            'until': 'must be an epoch timestamp.',
        }}, status_code=400)

        response = self.app.get(url, query_string={'query': 'foo',
                                                   'format': 'other'})
        self.assertJSON(response, {'errors': {
            'format': 'unrecognized format: "other".',
        }}, status_code=400)

    def test_expand(self):
        url = '/metrics/expand'

        response = self.app.get(url)
        self.assertJSON(response, {'errors':
                                   {'query': 'this parameter is required.'}},
                        status_code=400)

        response = self.app.get(url, query_string={'query': 'test'})
        self.assertJSON(response, {'results': []})

        self._create_dbs()
        response = self.app.get(url, query_string={'query': 'test'})
        self.assertJSON(response, {'results': ['test']})

        response = self.app.get(url, query_string={'query': 'test.*'})
        self.assertJSON(response, {'results': ['test.bar', 'test.foo',
                                               'test.wat']})

        response = self.app.get(url, query_string={'query': 'test.*',
                                                   'leavesOnly': 1})
        self.assertJSON(response, {'results': ['test.foo']})

        response = self.app.get(url, query_string={'query': 'test.*',
                                                   'groupByExpr': 1})
        self.assertJSON(response, {'results': {'test.*': ['test.bar',
                                                          'test.foo',
                                                          'test.wat']}})

    def test_expand_validation(self):
        url = '/metrics/expand'
        response = self.app.get(url, query_string={'query': 'foo',
                                                   'leavesOnly': 'bbb',
                                                   'groupByExpr': 'aaa'})
        self.assertJSON(response, {'errors': {
            'groupByExpr': 'must be 0 or 1.',
            'leavesOnly': 'must be 0 or 1.',
        }}, status_code=400)

    def test_noop(self):
        url = '/dashboard/find'
        response = self.app.get(url)
        self.assertJSON(response, {'dashboards': []})

        url = '/dashboard/load/foo'
        response = self.app.get(url)
        self.assertJSON(response, {'error': "Dashboard 'foo' does not exist."},
                        status_code=404)

        url = '/events/get_data'
        response = self.app.get(url)
        self.assertJSON(response, [])

    def test_search(self):
        url = '/metrics/search'
        response = self.app.get(url, query_string={'max_results': 'a'})
        self.assertJSON(response, {'errors': {
            'max_results': 'must be an integer.',
            'query': 'this parameter is required.'}}, status_code=400)

        response = self.app.get(url, query_string={'query': 'test'})
        self.assertJSON(response, {'metrics': []})

    def test_search_index(self):
        response = self.app.get('/metrics/search',
                                query_string={'query': 'collectd.*'})
        self.assertJSON(response, {'metrics': []})
        parent = os.path.join(WHISPER_DIR, 'collectd')
        os.makedirs(parent)

        for metric in ['load', 'memory', 'cpu']:
            db = os.path.join(parent, '{0}.wsp'.format(metric))
            whisper.create(db, [(1, 60)])

        response = self.app.put('/index')
        self.assertJSON(response, {'success': True, 'entries': 3})

        response = self.app.get('/metrics/search',
                                query_string={'query': 'collectd.*'})
        self.assertJSON(response, {'metrics': [
            {'is_leaf': False, 'path': None},
            {'is_leaf': True, 'path': 'collectd.cpu'},
            {'is_leaf': True, 'path': 'collectd.load'},
            {'is_leaf': True, 'path': 'collectd.memory'},
        ]})

########NEW FILE########
__FILENAME__ = test_render
# coding: utf-8
import json
import os
import time

from graphite_api._vendor import whisper

from . import TestCase, WHISPER_DIR


class RenderTest(TestCase):
    db = os.path.join(WHISPER_DIR, 'test.wsp')
    url = '/render'

    def create_db(self):
        whisper.create(self.db, [(1, 60)])

        self.ts = int(time.time())
        whisper.update(self.db, 0.5, self.ts - 2)
        whisper.update(self.db, 0.4, self.ts - 1)
        whisper.update(self.db, 0.6, self.ts)

    def test_render_view(self):
        response = self.app.get(self.url, query_string={'target': 'test',
                                                        'format': 'json'})
        self.assertEqual(json.loads(response.data.decode('utf-8')), [])

        response = self.app.get(self.url, query_string={'target': 'test'})
        self.assertEqual(response.headers['Content-Type'], 'image/png')

        self.create_db()
        response = self.app.get(self.url, query_string={'target': 'test',
                                                        'format': 'json'})
        data = json.loads(response.data.decode('utf-8'))
        end = data[0]['datapoints'][-4:]
        try:
            self.assertEqual(
                end, [[None, self.ts - 3], [0.5, self.ts - 2],
                      [0.4, self.ts - 1], [0.6, self.ts]])
        except AssertionError:
            self.assertEqual(
                end, [[0.5, self.ts - 2], [0.4, self.ts - 1],
                      [0.6, self.ts], [None, self.ts + 1]])

        response = self.app.get(self.url, query_string={'target': 'test',
                                                        'maxDataPoints': 2,
                                                        'format': 'json'})
        data = json.loads(response.data.decode('utf-8'))
        # 1 is a time race cond
        self.assertTrue(len(data[0]['datapoints']) in [1, 2])

        response = self.app.get(self.url, query_string={'target': 'test',
                                                        'maxDataPoints': 200,
                                                        'format': 'json'})
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(len(data[0]['datapoints']), 60)

    def test_render_constant_line(self):
        response = self.app.get(self.url, query_string={
            'target': 'constantLine(12)'})
        self.assertEqual(response.headers['Content-Type'], 'image/png')

        response = self.app.get(self.url, query_string={
            'target': 'constantLine(12)', 'format': 'json'})
        data = json.loads(response.data.decode('utf-8'))[0]['datapoints']
        self.assertEqual(len(data), 2)
        for point, ts in data:
            self.assertEqual(point, 12)

        response = self.app.get(self.url, query_string={
            'target': 'constantLine(12)', 'format': 'json',
            'maxDataPoints': 12})
        data = json.loads(response.data.decode('utf-8'))[0]['datapoints']
        self.assertEqual(len(data), 2)
        for point, ts in data:
            self.assertEqual(point, 12)

    def test_float_maxdatapoints(self):
        response = self.app.get(self.url, query_string={
            'target': 'sin("foo")', 'format': 'json',
            'maxDataPoints': 5.5})  # rounded to int
        data = json.loads(response.data.decode('utf-8'))[0]['datapoints']
        self.assertEqual(len(data), 5)

    def test_constantline_pathexpr(self):
        response = self.app.get(self.url, query_string={
            'target': 'sumSeries(constantLine(12), constantLine(5))',
            'format': 'json',
        })
        data = json.loads(response.data.decode('utf-8'))[0]['datapoints']
        self.assertEqual([d[0] for d in data], [17, 17])

    def test_area_between(self):
        response = self.app.get(self.url, query_string={
            'target': ['areaBetween(sin("foo"), sin("bar", 2))'],
            'format': 'json',
        })
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(len(data), 2)

    def test_sumseries(self):
        response = self.app.get(self.url, query_string={
            'target': ['sumSeries(sin("foo"), sin("bar", 2))',
                       'sin("baz", 3)'],
            'format': 'json',
        })
        data = json.loads(response.data.decode('utf-8'))
        agg = {}
        for series in data:
            agg[series['target']] = series['datapoints']
        for index, value in enumerate(agg['baz']):
            self.assertEqual(value, agg['sumSeries(sin(bar),sin(foo))'][index])

        response = self.app.get(self.url, query_string={
            'target': ['sumSeries(sin("foo"), sin("bar", 2))',
                       'sin("baz", 3)'],
            'format': 'json',
            'maxDataPoints': 100,
        })
        data = json.loads(response.data.decode('utf-8'))
        agg = {}
        for series in data:
            self.assertTrue(len(series['datapoints']) <= 100)
            agg[series['target']] = series['datapoints']
        for index, value in enumerate(agg['baz']):
            self.assertEqual(value, agg['sumSeries(sin(bar),sin(foo))'][index])

    def test_correct_timezone(self):
        response = self.app.get(self.url, query_string={
            'target': 'constantLine(12)',
            'format': 'json',
            'from': '07:00_20140226',
            'until': '08:00_20140226',
            # tz is UTC
        })
        data = json.loads(response.data.decode('utf-8'))[0]['datapoints']

        # all the from/until/tz combinations lead to the same window
        expected = [[12, 1393398000], [12, 1393401600]]
        self.assertEqual(data, expected)

        response = self.app.get(self.url, query_string={
            'target': 'constantLine(12)',
            'format': 'json',
            'from': '08:00_20140226',
            'until': '09:00_20140226',
            'tz': 'Europe/Berlin',
        })
        data = json.loads(response.data.decode('utf-8'))[0]['datapoints']
        self.assertEqual(data, expected)

    def test_render_options(self):
        self.create_db()
        db2 = os.path.join(WHISPER_DIR, 'foo.wsp')
        whisper.create(db2, [(1, 60)])
        ts = int(time.time())
        whisper.update(db2, 0.5, ts - 2)

        for qs in [
            {'logBase': 'e'},
            {'logBase': 1},
            {'logBase': 0.5},
            {'margin': -1},
            {'colorList': 'orange,green,blue,#0f0'},
            {'bgcolor': 'orange'},
            {'bgcolor': 'aaabbb'},
            {'bgcolor': '#aaabbb'},
            {'bgcolor': '#aaabbbff'},
            {'fontBold': 'true'},
            {'title': 'Hellò'},
            {'title': 'true'},
            {'vtitle': 'Hellò'},
            {'title': 'Hellò', 'yAxisSide': 'right'},
            {'uniqueLegend': 'true', '_expr': 'secondYAxis({0})'},
            {'uniqueLegend': 'true', 'vtitleRight': 'foo',
             '_expr': 'secondYAxis({0})'},
            {'graphOnly': 'true', 'yUnitSystem': 'si'},
            {'lineMode': 'staircase'},
            {'lineMode': 'slope'},
            {'lineMode': 'connected'},
            {'min': 1, 'max': 1, 'thickness': 2, 'yUnitSystem': 'welp'},
            {'yMax': 5, 'yLimit': 0.5, 'yStep': 0.1},
            {'yMax': 'max', 'yUnitSystem': 'binary'},
            {'areaMode': 'stacked', '_expr': 'stacked({0})'},
            {'lineMode': 'staircase', '_expr': 'stacked({0})'},
            {'areaMode': 'first', '_expr': 'stacked({0})'},
            {'areaMode': 'all', '_expr': 'stacked({0})'},
            {'areaMode': 'stacked', 'areaAlpha': 0.5, '_expr': 'stacked({0})'},
            {'areaMode': 'stacked', 'areaAlpha': 'a', '_expr': 'stacked({0})'},
            {'_expr': 'dashed(lineWidth({0}, 5))'},
            {'target': 'areaBetween(*)'},
            {'drawNullAsZero': 'true'},
            {'_expr': 'drawAsInfinite({0})'},
            {'graphType': 'pie', 'pieMode': 'average', 'title': 'Pie'},
            {'graphType': 'pie', 'pieMode': 'average', 'hideLegend': 'true'},
            {'graphType': 'pie', 'pieMode': 'average', 'valueLabels': 'none'},
            {'graphType': 'pie', 'pieMode': 'average',
             'valueLabels': 'number'},
            {'graphType': 'pie', 'pieMode': 'average', 'pieLabels': 'rotated'},
        ]:
            if qs.setdefault('target', ['foo', 'test']) == ['foo', 'test']:
                if '_expr' in qs:
                    expr = qs.pop('_expr')
                    qs['target'] = [expr.format(t) for t in qs['target']]
            response = self.app.get(self.url, query_string=qs)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['Content-Type'], 'image/png')

        for qs in [
            {'bgcolor': 'foo'},
        ]:
            qs['target'] = 'test'
            with self.assertRaises(ValueError):
                response = self.app.get(self.url, query_string=qs)

        for qs in [
            {'lineMode': 'stacked'},
        ]:
            qs['target'] = 'test'
            with self.assertRaises(AssertionError):
                response = self.app.get(self.url, query_string=qs)

    def test_render_validation(self):
        whisper.create(self.db, [(1, 60)])

        response = self.app.get(self.url)
        self.assertJSON(response, {'errors': {
            'target': 'This parameter is required.'}}, status_code=400)

        response = self.app.get(self.url, query_string={'graphType': 'foo',
                                                        'target': 'test'})
        self.assertJSON(response, {'errors': {
            'graphType': "Invalid graphType 'foo', must be one of 'line', "
            "'pie'."}}, status_code=400)

        response = self.app.get(self.url, query_string={'maxDataPoints': 'foo',
                                                        'target': 'test'})
        self.assertJSON(response, {'errors': {
            'maxDataPoints': 'Must be an integer.'}}, status_code=400)

        response = self.app.get(self.url, query_string={
            'from': '21:2020140313',
            'until': '21:2020140313',
            'target': 'test'})
        self.assertJSON(response, {'errors': {
            'from': 'Invalid empty time range',
            'until': 'Invalid empty time range',
        }}, status_code=400)

        response = self.app.get(self.url, query_string={
            'target': 'foo',
            'width': 100,
            'thickness': '1.5',
            'fontBold': 'true',
            'fontItalic': 'default',
        })
        self.assertEqual(response.status_code, 200)

        response = self.app.get(self.url, query_string={
            'target': 'foo', 'tz': 'Europe/Lausanne'})
        self.assertJSON(response, {'errors': {
            'tz': "Unknown timezone: 'Europe/Lausanne'.",
        }}, status_code=400)

        response = self.app.get(self.url, query_string={'target': 'test:aa',
                                                        'graphType': 'pie'})
        self.assertJSON(response, {'errors': {
            'target': "Invalid target: 'test:aa'.",
        }}, status_code=400)

        response = self.app.get(self.url, query_string={
            'target': ['test', 'foo:1.2'], 'graphType': 'pie'})
        self.assertEqual(response.status_code, 200)

        response = self.app.get(self.url, query_string={'target': ['test',
                                                                   '']})
        self.assertEqual(response.status_code, 200)

        response = self.app.get(self.url, query_string={'target': 'test',
                                                        'format': 'csv'})
        lines = response.data.decode('utf-8').strip().split('\n')
        self.assertEqual(len(lines), 60)
        self.assertFalse(any([l.strip().split(',')[2] for l in lines]))

        response = self.app.get(self.url, query_string={'target': 'test',
                                                        'format': 'svg',
                                                        'jsonp': 'foo'})
        jsonpsvg = response.data.decode('utf-8')
        self.assertTrue(jsonpsvg.startswith('foo("<?xml version=\\"1.0\\"'))
        self.assertTrue(jsonpsvg.endswith('</script>\\n</svg>")'))

        response = self.app.get(self.url, query_string={'target': 'test',
                                                        'format': 'svg'})
        svg = response.data.decode('utf-8')
        self.assertTrue(svg.startswith('<?xml version="1.0"'))

        response = self.app.get(self.url, query_string={
            'target': 'sum(test)',
        })
        self.assertEqual(response.status_code, 200)

        response = self.app.get(self.url, query_string={
            'target': ['sinFunction("a test", 2)',
                       'sinFunction("other test", 2.1)',
                       'sinFunction("other test", 2e1)'],
        })
        self.assertEqual(response.status_code, 200)

        response = self.app.get(self.url, query_string={
            'target': ['percentileOfSeries(sin("foo bar"), 95, true)']
        })
        self.assertEqual(response.status_code, 200)

    def test_raw_data(self):
        whisper.create(self.db, [(1, 60)])

        response = self.app.get(self.url, query_string={'rawData': '1',
                                                        'target': 'test'})
        info, data = response.data.decode('utf-8').strip().split('|', 1)
        path, start, stop, step = info.split(',')
        datapoints = data.split(',')
        try:
            self.assertEqual(datapoints, ['None'] * 60)
            self.assertEqual(int(stop) - int(start), 60)
        except AssertionError:
            self.assertEqual(datapoints, ['None'] * 59)
            self.assertEqual(int(stop) - int(start), 59)
        self.assertEqual(path, 'test')
        self.assertEqual(int(step), 1)

    def test_jsonp(self):
        whisper.create(self.db, [(1, 60)])

        start = int(time.time()) - 59
        response = self.app.get(self.url, query_string={'format': 'json',
                                                        'jsonp': 'foo',
                                                        'target': 'test'})
        data = response.data.decode('utf-8')
        self.assertTrue(data.startswith('foo('))
        data = json.loads(data[4:-1])
        try:
            self.assertEqual(data, [{'datapoints': [
                [None, start + i] for i in range(60)
            ], 'target': 'test'}])
        except AssertionError:  # Race condition when time overlaps a second
            self.assertEqual(data, [{'datapoints': [
                [None, start + i + 1] for i in range(60)
            ], 'target': 'test'}])

########NEW FILE########
__FILENAME__ = unittest_main
"""Main entry point"""

import sys
if sys.argv[0].endswith("__main__.py"):
    import os.path
    # We change sys.argv[0] to make help message more useful
    # use executable without path, unquoted
    # (it's just a hint anyway)
    # (if you have spaces in your executable you get what you deserve!)
    executable = os.path.basename(sys.executable)
    sys.argv[0] = executable + " -m unittest"
    del os

__unittest = True

from unittest.main import main, TestProgram, USAGE_AS_MAIN
TestProgram.USAGE = USAGE_AS_MAIN

main(module=None)

########NEW FILE########
