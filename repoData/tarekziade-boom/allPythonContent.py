__FILENAME__ = pgbar
#!/usr/bin/env python
# flake8: noqa
"""
progressbar.py hosted on https://github.com/ikame/progressbar

A Python module with a ProgressBar class which can be used to represent a
task's progress in the form of a progress bar and it can be formated in a
basic way.

Here is some basic usage with the default options:

    >>> from progressbar import ProgressBar
    >>> p = ProgressBar()
    >>> print p
    [>............] 0%
    >>> p + 1
    >>> print p
    [=>...........] 10%
    >>> p + 9
    >>> print p
    [============>] 0%

And here another example with different options:

    >>> from progressbar import ProgressBar
    >>> custom_options = {
    ...     'end': 100,
    ...     'width': 20,
    ...     'fill': '#',
    ...     'format': '%(progress)s%% [%(fill)s%(blank)s]'
    ... }
    >>> p = ProgressBar(**custom_options)
    >>> print p
    0% [....................]
    >>> p + 5
    >>> print p
    5% [#...................]
    >>> p + 9
    >>> print p
    100% [####################]
"""
import sys
import time


class ProgressBar(object):
    """ProgressBar class holds the options of the progress bar.
    The options are:
        start   State from which start the progress. For example, if start is
                5 and the end is 10, the progress of this state is 50%
        end     State in which the progress has terminated.
        width   --
        fill    String to use for "filled" used to represent the progress
        blank   String to use for "filled" used to represent remaining space.
        format  Format
        incremental
    """

    def __init__(self, start=0, end=10, width=12, fill='=', blank='.', format='[%(fill)s>%(blank)s] %(progress)s%%',
                 incremental=True):
        super(ProgressBar, self).__init__()

        self.start = start
        self.end = end
        self.width = width
        self.fill = fill
        self.blank = blank
        self.format = format
        self.incremental = incremental
        self.step = 100 / float(width) #fix
        self.reset()

    def __add__(self, increment):
        increment = self._get_progress(increment)
        if 100 > self.progress + increment:
            self.progress += increment
        else:
            self.progress = 100
        return self

    def __str__(self):
        progressed = int(self.progress / self.step) #fix
        fill = progressed * self.fill
        blank = (self.width - progressed) * self.blank
        return self.format % {'fill': fill, 'blank': blank, 'progress': int(self.progress)}

    __repr__ = __str__

    def _get_progress(self, increment):
        return float(increment * 100) / self.end

    def reset(self):
        """Resets the current progress to the start point"""
        self.progress = self._get_progress(self.start)
        return self


class AnimatedProgressBar(ProgressBar):
    """Extends ProgressBar to allow you to use it straighforward on a script.
    Accepts an extra keyword argument named `stdout` (by default use sys.stdout)
    and may be any file-object to which send the progress status.
    """

    def __init__(self, *args, **kwargs):
        super(AnimatedProgressBar, self).__init__(*args, **kwargs)
        self.stdout = kwargs.get('stdout', sys.stdout)

    def show_progress(self):
        if hasattr(self.stdout, 'isatty') and self.stdout.isatty():
            self.stdout.write('\r')
        else:
            self.stdout.write('\n')
        self.stdout.write(str(self))
        self.stdout.flush()


if __name__ == '__main__':
    p = AnimatedProgressBar(end=100, width=80)

    while True:
        p + 5
        p.show_progress()
        time.sleep(0.1)
        if p.progress == 100:
            break
    print # new line


########NEW FILE########
__FILENAME__ = test_boom
import unittest2 as unittest
import subprocess
import sys
import shlex
import StringIO
import json

from gevent.pywsgi import WSGIServer
import requests
import gevent

from boom._boom import (run as runboom, main,
                        resolve, RunResults, RequestException)
from boom import _boom


class App(object):

    def __init__(self):
        self.numcalls = 0

    def handle(self, env, start_response):
        if env['PATH_INFO'] == '/':
            self.numcalls += 1
            start_response('200 OK', [('Content-Type', 'text/html')])
            return ["<b>hello world</b>"]
        elif env['PATH_INFO'] == '/calls':
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return [str(self.numcalls)]
        elif env['PATH_INFO'] == '/redir':
            self.numcalls += 1
            start_response('302 Found', [('Location', '/redir')])
            return []
        elif env['PATH_INFO'] == '/reset':
            self.numcalls = 0
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return ['numcalls set to zero']
        else:
            start_response(
                '404 Not Found', [('Content-Type', 'text/plain')])
            return ['%s' % env['PATH_INFO']]


def run():
    app = App()
    WSGIServer(('0.0.0.0', 8089), app.handle).serve_forever()


_CMD = "%s -c 'from boom.tests.test_boom import run; run()'"
CMD = shlex.split(_CMD % sys.executable)
_SERVER = None


def _start():
    global _SERVER
    _SERVER = subprocess.Popen(CMD, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)


def _stop():
    global _SERVER
    if _SERVER is not None:
        _SERVER.terminate()
        _SERVER = None


def pre_hook(method, url, options):
    options['files'] = {'file': open(__file__, 'rb')}
    return method, url, options


def post_hook(response):
    return response


def post_hook_fails(data):
    if 'pattern' not in data:
        raise RequestException('missing pattern')
    return data


class TestBoom(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _start()
        cls.server = 'http://0.0.0.0:8089'
        while True:
            try:
                requests.get(cls.server + '/')
                return
            except requests.ConnectionError:
                gevent.sleep(.1)

    @classmethod
    def tearDownClass(cls):
        _stop()

    def setUp(self):
        self.get('/reset')

    def get(self, path):
        return requests.get(self.server + path)

    def test_basic_run(self):
        runboom(self.server, num=10, concurrency=1, quiet=True)
        res = self.get('/calls').content
        self.assertEqual(int(res), 10)

    def test_pre_hook(self):
        runboom(self.server, method='POST', num=10, concurrency=1,
                pre_hook='boom.tests.test_boom.pre_hook', quiet=True)
        res = self.get('/calls').content
        self.assertEqual(int(res), 10)

    def test_post_hook(self):
        run_results = runboom(
            self.server, method='GET', num=10, concurrency=1,
            post_hook='boom.tests.test_boom.post_hook', quiet=True)
        res = self.get('/calls').content
        self.assertEqual(run_results.errors, [])
        self.assertEqual(int(res), 10)

    def test_post_hook_fails(self):
        run_results = runboom(
            self.server, method='GET', num=10, concurrency=1,
            post_hook='boom.tests.test_boom.post_hook_fails', quiet=True)
        res = self.get('/calls').content
        self.assertEqual(len(run_results.errors), 10)

        for err in run_results.errors:
            self.assertEqual(True, isinstance(err, RequestException))
            self.assertEqual(err.message, 'missing pattern')

        self.assertEqual(int(res), 10)

    def test_connection_error(self):
        run_results = runboom(
            'http://localhost:9999', num=10, concurrency=1,
            quiet=True)
        self.assertEqual(len(run_results.errors), 10)
        for error in run_results.errors:
            self.assertIsInstance(error, requests.ConnectionError)

    def test_too_many_redirects(self):
        run_results = runboom(
            self.server + '/redir', num=2, concurrency=1,
            quiet=True)
        res = self.get('/calls').content
        self.assertEqual(int(res), 62)
        for error in run_results.errors:
            self.assertIsInstance(error, requests.TooManyRedirects)

    def _run(self, *args):
        sys.argv[:] = [sys.executable] + list(args)
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        exit_code = 0
        sys.stdout = StringIO.StringIO()
        sys.stderr = StringIO.StringIO()
        try:
            main()
        except (Exception, SystemExit) as e:
            if isinstance(e, SystemExit):
                exit_code = e.code
            else:
                exit_code = 1
        finally:
            sys.stdout.seek(0)
            stdout = sys.stdout.read()
            sys.stderr.seek(0)
            stderr = sys.stdout.read()
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        return exit_code, stdout, stderr

    def test_dns_resolve(self):
        code, stdout, stderr = self._run('http://that.impossiblename')
        self.assertEqual(code, 1)
        self.assertTrue('DNS resolution failed for' in stdout, stdout)

    def test_resolve(self):
        test_url = 'http://localhost:9999'
        url, original, resolved = resolve(test_url)
        self.assertEqual(url, 'http://127.0.0.1:9999')
        self.assertEqual(original, 'localhost')
        self.assertEqual(resolved, '127.0.0.1')

    def test_ssl_resolve(self):
        test_url = 'https://localhost:9999'
        url, original, resolved = resolve(test_url)
        self.assertEqual(url, 'https://localhost:9999')
        self.assertEqual(original, 'localhost')
        self.assertEqual(resolved, 'localhost')

    def test_resolve_no_scheme(self):
        test_url = 'http://localhost'
        url, original, resolved = resolve(test_url)
        self.assertEqual(url, 'http://127.0.0.1:80')
        self.assertEqual(original, 'localhost')
        self.assertEqual(resolved, '127.0.0.1')

    def test_resolve_no_scheme_ssl(self):
        test_url = 'https://localhost'
        url, original, resolved = resolve(test_url)
        self.assertEqual(url, 'https://localhost:443')
        self.assertEqual(original, 'localhost')
        self.assertEqual(resolved, 'localhost')

    def test_json_output(self):
        results = RunResults()
        results.status_code_counter['200'].extend([0, 0.1, 0.2])
        results.total_time = 9

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            sys.stdout = StringIO.StringIO()
            sys.stderr = StringIO.StringIO()
            _boom.print_json(results)

            sys.stdout.seek(0)
            output = sys.stdout.read()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        actual = json.loads(output)
        self.assertEqual(3, actual['count'])
        self.assertAlmostEqual(0.333, actual['rps'], delta=0.1)
        self.assertEqual(0, actual['min'])
        self.assertEqual(0.2, actual['max'])
        self.assertAlmostEqual(0.1, actual['avg'], delta=0.1)
        self.assertEqual(0.2, actual['amp'])


if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = test_pgbar
import unittest
from boom.pgbar import ProgressBar


class DefaultsTestCase(unittest.TestCase):
    """
    ProgressBar defaults:
    start = 0
    end = 10
    width = 12
    fill = '='
    blank = '.'
    format = '[%(fill)s>%(blank)s] %(progress)s%%'
    incremental = True
    """

    def setUp(self):
        self.p = ProgressBar()

    def tearDown(self):
        del (self.p)

    def test_initialization(self):
        """
        >>> p = ProgressBar()
        >>> p
        [>............] 0%
        """
        self.assertEqual(str(self.p), '[>............] 0%')

    def test_increment(self):
        """
        >>> p = ProgressBar()
        >>> p + 1
        [=>...........] 10%
        """
        self.p + 1
        self.assertEqual(str(self.p), '[=>...........] 10%')

    def test_reset(self):
        """
        >>> p = ProgressBar()
        >>> p += 8
        >>> p.reset()
        [>............] 0%
        """
        self.p += 8
        self.p.reset()
        self.assertEqual(str(self.p), '[>............] 0%')

    def test_full_progress(self):
        """
        >>> p = ProgressBar()
        >>> p + 10
        [============>] 100%
        """
        self.p + 10
        self.assertEqual(str(self.p), '[============>] 100%')
        self.p + 10
        self.assertEqual(str(self.p), '[============>] 100%')


class CustomizedTestCase(unittest.TestCase):
    """
    ProgressBar custom:
    start = 0
    end = 100
    width = 20
    fill = '#'
    blank = '.'
    format = '%(progress)s%% [%(fill)s%(blank)s]'
    incremental = True
    """
    custom = {
        'end': 100,
        'width': 20,
        'fill': '#',
        'format': '%(progress)s%% [%(fill)s%(blank)s]'
    }

    def setUp(self):
        self.p = ProgressBar(**self.custom)

    def tearDown(self):
        del (self.p)

    def test_initialization(self):
        """
        >>> custom = {
        ...  'end': 100,
        ...  'width': 20,
        ...  'fill': '#',
        ...  'format': '%(progress)s%% [%(fill)s%(blank)s]'
        ... }
        >>> p = ProgressBar(custom)
        >>> p
        0% [....................]
        """
        self.assertEqual(str(self.p), '0% [....................]')

    def test_increment(self):
        """
        >>> custom = {
        ...  'end': 100,
        ...  'width': 20,
        ...  'fill': '#',
        ...  'format': '%(progress)s%% [%(fill)s%(blank)s]'
        ... }
        >>> p = ProgressBar(custom)
        >>> p + 1
        1% [....................]
        """
        self.p + 1
        self.assertEqual(str(self.p), '1% [....................]')
        self.p + 4
        self.assertEqual(str(self.p), '5% [#...................]')

    def test_reset(self):
        """
        >>> custom = {
        ...  'end': 100,
        ...  'width': 20,
        ...  'fill': '#',
        ...  'format': '%(progress)s%% [%(fill)s%(blank)s]'
        ... }
        >>> p = ProgressBar(custom)
        >>> p += 8
        >>> p.reset()
        0% [....................]
        """
        self.p += 8
        self.p.reset()
        self.assertEqual(str(self.p), '0% [....................]')

    def test_full_progress(self):
        """
        >>> p = ProgressBar()
        >>> p + 10
        100% [####################]
        """
        self.p + 100
        self.assertEqual(str(self.p), '100% [####################]')
        self.p + 100
        self.assertEqual(str(self.p), '100% [####################]')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = util
import sys

try:
    from importlib import import_module         # NOQA
except ImportError:
    def _resolve_name(name, package, level):
        """Returns the absolute name of the module to be imported. """
        if not hasattr(package, 'rindex'):
            raise ValueError("'package' not set to a string")
        dot = len(package)
        for x in xrange(level, 1, -1):
            try:
                dot = package.rindex('.', 0, dot)
            except ValueError:
                raise ValueError("attempted relative import beyond top-level "
                                 "package")
        return "%s.%s" % (package[:dot], name)

    def import_module(name, package=None):      # NOQA
        """Import a module.
        The 'package' argument is required when performing a relative import.
        It specifies the package to use as the anchor point from which to
        resolve the relative import to an absolute import."""
        if name.startswith('.'):
            if not package:
                raise TypeError("relative imports require the 'package' "
                                "argument")
            level = 0
            for character in name:
                if character != '.':
                    break
                level += 1
            name = _resolve_name(name[level:], package, level)
        __import__(name)
        return sys.modules[name]


# taken from werkzeug
class ImportStringError(ImportError):
    """Provides information about a failed :func:`import_string` attempt."""

    #: String in dotted notation that failed to be imported.
    import_name = None
    #: Wrapped exception.
    exception = None

    def __init__(self, import_name, exception):
        self.import_name = import_name
        self.exception = exception

        msg = (
            'import_string() failed for %r. Possible reasons are:\n\n'
            '- missing __init__.py in a package;\n'
            '- package or module path not included in sys.path;\n'
            '- duplicated package or module name taking precedence in '
            'sys.path;\n'
            '- missing module, class, function or variable;\n\n'
            'Debugged import:\n\n%s\n\n'
            'Original exception:\n\n%s: %s')

        name = ''
        tracked = []
        for part in import_name.replace(':', '.').split('.'):
            name += (name and '.') + part
            imported = resolve_name(name, silent=True)
            if imported:
                tracked.append((name, getattr(imported, '__file__', None)))
            else:
                track = ['- %r found in %r.' % (n, i) for n, i in tracked]
                track.append('- %r not found.' % name)
                msg = msg % (import_name, '\n'.join(track),
                             exception.__class__.__name__, str(exception))
                break

        ImportError.__init__(self, msg)

    def __repr__(self):
        return '<%s(%r, %r)>' % (self.__class__.__name__, self.import_name,
                                 self.exception)


def resolve_name(import_name, silent=False):
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If `silent` is True the return value will be `None` if the import fails.

    For better debugging we recommend the new :func:`import_module`
    function to be used instead.

    :param import_name: the dotted name for the object to import.
    :param silent: if set to `True` import errors are ignored and
                   `None` is returned instead.
    :return: imported object
    """
    # force the import name to automatically convert to strings
    if isinstance(import_name, unicode):
        import_name = str(import_name)
    try:
        if ':' in import_name:
            module, obj = import_name.split(':', 1)
        elif '.' in import_name:
            module, obj = import_name.rsplit('.', 1)
        else:
            return __import__(import_name)
            # __import__ is not able to handle unicode strings in the fromlist
        # if the module is a package
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        try:
            return getattr(__import__(module, None, None, [obj]), obj)
        except (ImportError, AttributeError):
            # support importing modules not yet set up by the parent module
            # (or package for that matter)
            modname = module + '.' + obj
            __import__(modname)
            return sys.modules[modname]
    except ImportError, e:
        if not silent:
            raise ImportStringError(import_name, e), None, sys.exc_info()[2]

########NEW FILE########
__FILENAME__ = _boom
import argparse
import gevent
import logging
import requests
import sys
import time
import urlparse
import math

from collections import defaultdict, namedtuple
from copy import copy
from gevent import monkey
from gevent.pool import Pool
from requests import RequestException
from requests.packages.urllib3.util import parse_url
from socket import gethostbyname, gaierror

from boom import __version__, _patch     # NOQA
from boom.util import resolve_name
from boom.pgbar import AnimatedProgressBar

monkey.patch_all()

logger = logging.getLogger('boom')

_VERBS = ('GET', 'POST', 'DELETE', 'PUT', 'HEAD', 'OPTIONS')
_DATA_VERBS = ('POST', 'PUT')


class RunResults(object):

    """Encapsulates the results of a single Boom run.

    Contains a dictionary of status codes to lists of request durations,
    a list of exception instances raised during the run, the total time
    of the run and an animated progress bar.
    """

    def __init__(self, num=1, quiet=False):
        self.status_code_counter = defaultdict(list)
        self.errors = []
        self.total_time = None
        if num is not None:
            self._progress_bar = AnimatedProgressBar(
                end=num,
                width=65)
        else:
            self._progress_bar = None
        self.quiet = quiet

    def incr(self):
        if self.quiet:
            return
        if self._progress_bar is not None:
            self._progress_bar + 1
            self._progress_bar.show_progress()
        else:
            sys.stdout.write('.')
            sys.stdout.flush()


RunStats = namedtuple(
    'RunStats', ['count', 'total_time', 'rps', 'avg', 'min',
                 'max', 'amp', 'stdev'])


def calc_stats(results):
    """Calculate stats (min, max, avg) from the given RunResults.

       The statistics are returned as a RunStats object.
    """
    all_res = []
    count = 0
    for values in results.status_code_counter.values():
        all_res += values
        count += len(values)

    cum_time = sum(all_res)

    if cum_time == 0 or len(all_res) == 0:
        rps = avg = min_ = max_ = amp = 0
    else:
        if results.total_time == 0:
            rps = 0
        else:
            rps = len(all_res) / float(results.total_time)
        avg = sum(all_res) / len(all_res)
        max_ = max(all_res)
        min_ = min(all_res)
        amp = max(all_res) - min(all_res)
        stdev = math.sqrt(sum((x-avg)**2 for x in all_res) / count)

    return (
        RunStats(count, results.total_time, rps, avg, min_, max_, amp, stdev)
    )


def print_stats(results):
    stats = calc_stats(results)
    rps = stats.rps

    print('')
    print('-------- Results --------')

    print('Successful calls\t\t%r' % stats.count)
    print('Total time        \t\t%.4f s  ' % stats.total_time)
    print('Average           \t\t%.4f s  ' % stats.avg)
    print('Fastest           \t\t%.4f s  ' % stats.min)
    print('Slowest           \t\t%.4f s  ' % stats.max)
    print('Amplitude         \t\t%.4f s  ' % stats.amp)
    print('Standard deviation\t\t%.6f' % stats.stdev)
    print('RPS               \t\t%d' % rps)
    if rps > 500:
        print('BSI              \t\tWoooooo Fast')
    elif rps > 100:
        print('BSI              \t\tPretty good')
    elif rps > 50:
        print('BSI              \t\tMeh')
    else:
        print('BSI              \t\tHahahaha')
    print('')
    print('-------- Status codes --------')
    for code, items in results.status_code_counter.items():
        print('Code %d          \t\t%d times.' % (code, len(items)))
    print('')
    print('-------- Legend --------')
    print('RPS: Request Per Second')
    print('BSI: Boom Speed Index')


def print_server_info(url, method, headers=None):
    res = requests.head(url)
    print(
        'Server Software: %s' %
        res.headers.get('server', 'Unknown'))
    print('Running %s %s' % (method, url))

    if headers:
        for k, v in headers.items():
            print('\t%s: %s' % (k, v))


def print_errors(errors):
    if len(errors) == 0:
        return
    print('')
    print('-------- Errors --------')
    for error in errors:
        print(error)


def print_json(results):
    """Prints a JSON representation of the results to stdout."""
    import json
    stats = calc_stats(results)
    print(json.dumps(stats._asdict()))


def onecall(method, url, results, **options):
    """Performs a single HTTP call and puts the result into the
       status_code_counter.

    RequestExceptions are caught and put into the errors set.
    """
    start = time.time()

    if 'data' in options and callable(options['data']):
        options = copy(options)
        options['data'] = options['data'](method, url, options)

    if 'pre_hook' in options:
        method, url, options = options[
            'pre_hook'](method, url, options)
        del options['pre_hook']

    post_hook = lambda _res: _res  # dummy hook
    if 'post_hook' in options:
        post_hook = options['post_hook']
        del options['post_hook']

    try:
        res = post_hook(method(url, **options))
    except RequestException as exc:
        results.errors.append(exc)
    else:
        duration = time.time() - start
        results.status_code_counter[res.status_code].append(duration)
    finally:
        results.incr()


def run(
    url, num=1, duration=None, method='GET', data=None, ct='text/plain',
        auth=None, concurrency=1, headers=None, pre_hook=None, post_hook=None,
        quiet=False):

    if headers is None:
        headers = {}

    if 'content-type' not in headers:
        headers['Content-Type'] = ct

    if data is not None and data.startswith('py:'):
        callable = data[len('py:'):]
        data = resolve_name(callable)

    method = getattr(requests, method.lower())
    options = {'headers': headers}

    if pre_hook is not None:
        options['pre_hook'] = resolve_name(pre_hook)

    if post_hook is not None:
        options['post_hook'] = resolve_name(post_hook)

    if data is not None:
        options['data'] = data

    if auth is not None:
        options['auth'] = tuple(auth.split(':', 1))

    pool = Pool(concurrency)

    start = time.time()
    jobs = None

    res = RunResults(num, quiet)

    try:
        if num is not None:
            jobs = [pool.spawn(onecall, method, url, res, **options)
                    for i in range(num)]
            pool.join()
        else:
            with gevent.Timeout(duration, False):
                jobs = []
                while True:
                    jobs.append(pool.spawn(onecall, method, url, res,
                                           **options))
                pool.join()
    except KeyboardInterrupt:
        # In case of a keyboard interrupt, just return whatever already got
        # put into the result object.
        pass
    finally:
        res.total_time = time.time() - start

    return res


def resolve(url):
    parts = parse_url(url)

    if not parts.port and parts.scheme == 'https':
        port = 443
    elif not parts.port and parts.scheme == 'http':
        port = 80
    else:
        port = parts.port

    original = parts.host
    resolved = gethostbyname(parts.host)

    # Don't use a resolved hostname for SSL requests otherwise the
    # certificate will not match the IP address (resolved)
    host = resolved if parts.scheme != 'https' else parts.host
    netloc = '%s:%d' % (host, port) if port else host

    return (urlparse.urlunparse((parts.scheme, netloc, parts.path or '',
                                 '', parts.query or '',
                                 parts.fragment or '')),
            original, host)


def load(url, requests, concurrency, duration, method, data, ct, auth,
         headers=None, pre_hook=None, post_hook=None, quiet=False):
    if not quiet:
        print_server_info(url, method, headers=headers)

        if requests is not None:
            print('Running %d queries - concurrency %d' % (requests,
                                                           concurrency))
        else:
            print('Running for %d seconds - concurrency %d.' %
                  (duration, concurrency))

        sys.stdout.write('Starting the load')
    try:
        return run(url, requests, duration, method,
                   data, ct, auth, concurrency, headers,
                   pre_hook, post_hook, quiet=quiet)
    finally:
        if not quiet:
            print(' Done')


def main():
    parser = argparse.ArgumentParser(
        description='Simple HTTP Load runner.')

    parser.add_argument(
        '--version', action='store_true', default=False,
        help='Displays version and exits.')

    parser.add_argument('-m', '--method', help='HTTP Method',
                        type=str, default='GET', choices=_VERBS)

    parser.add_argument('--content-type', help='Content-Type',
                        type=str, default='text/plain')

    parser.add_argument('-D', '--data',
                        help=('Data. Prefixed by "py:" to point '
                              'a python callable.'),
                        type=str)

    parser.add_argument('-c', '--concurrency', help='Concurrency',
                        type=int, default=1)

    parser.add_argument('-a', '--auth',
                        help='Basic authentication user:password', type=str)

    parser.add_argument('--header', help='Custom header. name:value',
                        type=str, action='append')

    parser.add_argument('--pre-hook',
                        help=("Python module path (eg: mymodule.pre_hook) "
                              "to a callable which will be executed before "
                              "doing a request for example: "
                              "pre_hook(method, url, options). "
                              "It must return a tupple of parameters given in "
                              "function definition"),
                        type=str)

    parser.add_argument('--post-hook',
                        help=("Python module path (eg: mymodule.post_hook) "
                              "to a callable which will be executed after "
                              "a request is done for example: "
                              "eg. post_hook(response). "
                              "It must return a given response parameter or "
                              "raise an `boom._boom.RequestException` for "
                              "failed request."),
                        type=str)

    parser.add_argument('--json-output',
                        help='Prints the results in JSON instead of the '
                             'default format',
                        action='store_true')

    parser.add_argument('-q', '--quiet', help="Don't display progress bar",
                        action='store_true')

    group = parser.add_mutually_exclusive_group()

    group.add_argument('-n', '--requests', help='Number of requests',
                       type=int)

    group.add_argument('-d', '--duration', help='Duration in seconds',
                       type=int)

    parser.add_argument('url', help='URL to hit', nargs='?')
    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    if args.url is None:
        print('You need to provide an URL.')
        parser.print_usage()
        sys.exit(0)

    if args.data is not None and not args.method in _DATA_VERBS:
        print("You can't provide data with %r" % args.method)
        parser.print_usage()
        sys.exit(0)

    if args.requests is None and args.duration is None:
        args.requests = 1

    try:
        url, original, resolved = resolve(args.url)
    except gaierror as e:
        print_errors(("DNS resolution failed for %s (%s)" %
                      (args.url, str(e)),))
        sys.exit(1)

    def _split(header):
        header = header.split(':')

        if len(header) != 2:
            print("A header must be of the form name:value")
            parser.print_usage()
            sys.exit(0)

        return header

    if args.header is None:
        headers = {}
    else:
        headers = dict([_split(header) for header in args.header])

    if original != resolved and 'Host' not in headers:
        headers['Host'] = original

    try:
        res = load(
            url, args.requests, args.concurrency, args.duration,
            args.method, args.data, args.content_type, args.auth,
            headers=headers, pre_hook=args.pre_hook,
            post_hook=args.post_hook, quiet=(args.json_output or args.quiet))
    except RequestException as e:
        print_errors((e, ))
        sys.exit(1)

    if not args.json_output:
        print_errors(res.errors)
        print_stats(res)
    else:
        print_json(res)

    logger.info('Bye!')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = _patch
import threading
from threading import (_active_limbo_lock, _limbo, _active, _sys, _trace_hook,
                       _profile_hook, _format_exc)


# see http://bugs.python.org/issue1596321
def _bootstrap_inner(self):
    try:
        self._set_ident()
        self._Thread__started.set()
        with _active_limbo_lock:
            _active[self._Thread__ident] = self
            del _limbo[self]

        if _trace_hook:
            _sys.settrace(_trace_hook)
        if _profile_hook:
            _sys.setprofile(_profile_hook)

        try:
            self.run()
        except SystemExit:
            pass
        except:
            if _sys:
                _sys.stderr.write("Exception in thread %s:\n%s\n" %
                                  (self.name, _format_exc()))
            else:
                exc_type, exc_value, exc_tb = self._exc_info()
                try:
                    self._stderr.write(
                        "Exception in thread " + self.name + " (most likely "
                        "raised during interpreter shutdown):")

                    self._stderr.write("Traceback (most recent call last):")
                    while exc_tb:
                        self._stderr.write(
                            '  File "%s", line %s, in %s' %
                            (exc_tb.tb_frame.f_code.co_filename,
                                exc_tb.tb_lineno,
                                exc_tb.tb_frame.f_code.co_name))

                        exc_tb = exc_tb.tb_next
                    self._stderr.write("%s: %s" % (exc_type, exc_value))
                finally:
                    del exc_type, exc_value, exc_tb
        finally:
            pass
    finally:
        with _active_limbo_lock:
            self._Thread__stop()
            try:
                del _active[self._Thread__ident]
            except:
                pass


def _delete(self):
    try:
        with _active_limbo_lock:
            del _active[self._Thread__ident]
    except KeyError:
        if 'dummy_threading' not in _sys.modules:
            raise


# http://bugs.python.org/issue14308
def _stop(self):
    # DummyThreads delete self.__block, but they have no waiters to
    # notify anyway (join() is forbidden on them).
    if not hasattr(self, '_Thread__block'):
        return
    self._Thread__stop_old()


threading.Thread._Thread__bootstrap_inner = _bootstrap_inner
threading.Thread._Thread__delete = _delete
threading.Thread._Thread__stop_old = threading.Thread._Thread__stop
threading.Thread._Thread__stop = _stop

########NEW FILE########
