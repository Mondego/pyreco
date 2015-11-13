__FILENAME__ = appstats_profiler
"""RPC profiler that uses appstats to track, time, and log all RPC events.

This is just a simple wrapper for appstats with result formatting. See
https://developers.google.com/appengine/docs/python/tools/appstats for more.
"""

import logging
from pprint import pformat

from google.appengine.ext.appstats import recording

import cleanup
import unformatter
import util

class Profile(object):
    """Profiler that wraps appstats for programmatic access and reporting."""
    def __init__(self):
        # Configure AppStats output, keeping a high level of request
        # content so we can detect dupe RPCs more accurately
        recording.config.MAX_REPR = 750

        # Each request has its own internal appstats recorder
        self.recorder = None

    def results(self):
        """Return appstats results in a dictionary for template context."""
        if not self.recorder:
            # If appstats fails to initialize for any reason, return an empty
            # set of results.
            logging.warn("Missing recorder for appstats profiler.")
            return {
                "calls": [],
                "total_time": 0,
            }

        total_call_count = 0
        total_time = 0
        calls = []
        service_totals_dict = {}
        likely_dupes = False
        end_offset_last = 0

        requests_set = set()

        appstats_key = long(self.recorder.start_timestamp * 1000)

        for trace in self.recorder.traces:
            total_call_count += 1

            total_time += trace.duration_milliseconds()

            # Don't accumulate total RPC time for traces that overlap asynchronously
            if trace.start_offset_milliseconds() < end_offset_last:
                total_time -= (end_offset_last - trace.start_offset_milliseconds())
            end_offset_last = trace.start_offset_milliseconds() + trace.duration_milliseconds()

            service_prefix = trace.service_call_name()

            if "." in service_prefix:
                service_prefix = service_prefix[:service_prefix.find(".")]

            if service_prefix not in service_totals_dict:
                service_totals_dict[service_prefix] = {
                    "total_call_count": 0,
                    "total_time": 0,
                    "total_misses": 0,
                }

            service_totals_dict[service_prefix]["total_call_count"] += 1
            service_totals_dict[service_prefix]["total_time"] += trace.duration_milliseconds()

            stack_frames_desc = []
            for frame in trace.call_stack_list():
                stack_frames_desc.append("%s:%s %s" %
                        (util.short_rpc_file_fmt(frame.class_or_file_name()),
                            frame.line_number(),
                            frame.function_name()))

            request = trace.request_data_summary()
            response = trace.response_data_summary()

            likely_dupe = request in requests_set
            likely_dupes = likely_dupes or likely_dupe
            requests_set.add(request)

            request_short = request_pretty = None
            response_short = response_pretty = None
            miss = 0
            try:
                request_object = unformatter.unformat(request)
                response_object = unformatter.unformat(response)

                request_short, response_short, miss = cleanup.cleanup(request_object, response_object)

                request_pretty = pformat(request_object)
                response_pretty = pformat(response_object)
            except Exception, e:
                pass
                # enable this if you want to improve prettification
                # logging.warning("Prettifying RPC calls failed.\n%s\nRequest: %s\nResponse: %s",
                #     e, request, response, exc_info=True)

            service_totals_dict[service_prefix]["total_misses"] += miss

            calls.append({
                "service": trace.service_call_name(),
                "start_offset": util.milliseconds_fmt(trace.start_offset_milliseconds()),
                "total_time": util.milliseconds_fmt(trace.duration_milliseconds()),
                "request": request_pretty or request,
                "response": response_pretty or response,
                "request_short": request_short or cleanup.truncate(request),
                "response_short": response_short or cleanup.truncate(response),
                "stack_frames_desc": stack_frames_desc,
                "likely_dupe": likely_dupe,
            })

        service_totals = []
        for service_prefix in service_totals_dict:
            service_totals.append({
                "service_prefix": service_prefix,
                "total_call_count": service_totals_dict[service_prefix]["total_call_count"],
                "total_misses": service_totals_dict[service_prefix]["total_misses"],
                "total_time": util.milliseconds_fmt(service_totals_dict[service_prefix]["total_time"]),
            })
        service_totals = sorted(service_totals, reverse=True, key=lambda service_total: float(service_total["total_time"]))

        return  {
                    "total_call_count": total_call_count,
                    "total_time": util.milliseconds_fmt(total_time),
                    "calls": calls,
                    "service_totals": service_totals,
                    "likely_dupes": likely_dupes,
                    "appstats_key": appstats_key,
                }

    def wrap(self, app):
        """Wrap and return a WSGI application with appstats recording enabled.

        Args:
            app: existing WSGI application to be wrapped
        Returns:
            new WSGI application that will run the original app with appstats
                enabled.
        """
        def wrapped_appstats_app(environ, start_response):
            # Use this wrapper to grab the app stats recorder for RequestStats.save()
            if recording.recorder_proxy.has_recorder_for_current_request():
                self.recorder = recording.recorder_proxy.get_for_current_request()
            return app(environ, start_response)

        return recording.appstats_wsgi_middleware(wrapped_appstats_app)

########NEW FILE########
__FILENAME__ = cleanup
import StringIO

def cleanup(request, response):
    '''
    Convert request and response dicts to a human readable format where
    possible.
    '''
    request_short = None
    response_short = None
    miss = 0

    if "MemcacheGetRequest" in request:
        request = request["MemcacheGetRequest"]
        response = response["MemcacheGetResponse"]
        if request:
            request_short = memcache_get(request)
        if response:
            response_short, miss = memcache_get_response(response)
    elif "MemcacheSetRequest" in request and request["MemcacheSetRequest"]:
        request_short = memcache_set(request["MemcacheSetRequest"])
    elif "Query" in request and request["Query"]:
        request_short = datastore_query(request["Query"])
    elif "GetRequest" in request and request["GetRequest"]:
        request_short = datastore_get(request["GetRequest"])
    elif "PutRequest" in request and request["PutRequest"]:
        request_short = datastore_put(request["PutRequest"])
    # todo:
    # TaskQueueBulkAddRequest
    # BeginTransaction
    # Transaction

    return request_short, response_short, miss

def memcache_get_response(response):
    """Pretty-format a memcache.get() response.

    Arguments:
      response - The memcache.get() response object, e.g.
        {'item': [{'Item': {'flags': '0L', 'key': 'memcache_key', ...

    Returns:
      The tuple (value, miss) where the "value" is the value of the
      memcache.get() response as a string. If there are multiple response
      values, as when multiple keys are passed in, the values are separated by
      newline characters. "miss" is 1 if there were no items returned from
      memcache and 0 otherwise.
    """
    if 'item' not in response or not response['item']:
        return None, 1

    items = response['item']
    for i, item in enumerate(items):
        if type(item) == dict:
            if 'MemcacheGetResponse_Item' in item:
                # This key exists in dev and in the 'python' production runtime.
                item = item['MemcacheGetResponse_Item']['value']
            else:
                # But it's a different key in the 'python27' production runtime.
                item = item['Item']['value']
            item = truncate(repr(item))
            items[i] = item
    response_short = "\n".join(items)
    return response_short, 0

def memcache_get(request):
    """Pretty-format a memcache.get() request.

    Arguments:
      request - The memcache.get() request object, i.e.
        {'key': ['memcache_key']}

    Returns:
      The keys of the memcache.get() response as a string. If there are
      multiple keys, they are separated by newline characters.
    """
    keys = request['key']
    request_short = "\n".join([truncate(k) for k in keys])
    namespace = ''
    if 'name_space' in request:
        namespace = request['name_space']
        if len(keys) > 1:
            request_short += '\n'
        else:
            request_short += ' '
        request_short += '(ns:%s)' % truncate(namespace)
    return request_short

def memcache_set(request):
    """Pretty-format a memcache.set() request.

    Arguments:
      request - The memcache.set() request object, e.g.,
        {'item': [{'Item': {'flags': '0L', 'key': 'memcache_key' ...

    Returns:
      The keys of the memcache.get() response as a string. If there are
      multiple keys, they are separated by newline characters.
    """
    keys = []
    for i in request["item"]:
        if "MemcacheSetRequest_Item" in i:
            # This key exists in dev and in the 'python' production runtime.
            key = i["MemcacheSetRequest_Item"]["key"]
        else:
            # But it's a different key in the 'python27' production runtime.
            key = i["Item"]["key"]
        keys.append(truncate(key))
    return "\n".join(keys)

def datastore_query(query):
    kind = query.get('kind', 'UnknownKind')
    count = query.get('count', '')

    filters_clean = datastore_query_filter(query)
    orders_clean = datastore_query_order(query)

    s = StringIO.StringIO()
    s.write("SELECT FROM %s\n" % kind)
    if filters_clean:
        s.write("WHERE\n")
        for name, op, value in filters_clean:
            s.write("%s %s %s\n" % (name, op, value))
    if orders_clean:
        s.write("ORDER BY\n")
        for prop, direction in orders_clean:
            s.write("%s %s\n" % (prop, direction))
    if count:
        s.write("LIMIT %s\n" % count)

    result = s.getvalue()
    s.close()
    return result

def datastore_query_filter(query):
    _Operator_NAMES = {
        0: "?",
        1: "<",
        2: "<=",
        3: ">",
        4: ">=",
        5: "=",
        6: "IN",
        7: "EXISTS",
    }
    filters = query.get('filter', [])
    filters_clean = []
    for f in filters:
        if 'Query_Filter' in f:
            # This key exists in dev and in the 'python' production runtime.
            f = f["Query_Filter"]
        elif 'Filter' in f:
            # But it's a different key in the 'python27' production runtime.
            f = f["Filter"]
        else:
            # Filters are optional, so there might be no filter at all.
            continue
        op = _Operator_NAMES[int(f.get('op', 0))]
        props = f["property"]
        for p in props:
            p = p["Property"]
            name = p["name"] if "name" in p else "UnknownName"

            if 'value' in p:

                propval = p['value']['PropertyValue']

                if 'stringvalue' in propval:
                    value = propval["stringvalue"]
                elif 'referencevalue' in propval:
                    if 'PropertyValue_ReferenceValue' in propval['referencevalue']:
                        # This key exists in dev and in the 'python' production runtime.
                        ref = propval['referencevalue']['PropertyValue_ReferenceValue']
                    else:
                        # But it's a different key in the 'python27' production runtime.
                        ref = propval['referencevalue']['ReferenceValue']
                    els = ref['pathelement']
                    paths = []
                    for el in els:
                        if 'PropertyValue_ReferenceValuePathElement' in el:
                            # This key exists in dev and in the 'python' production runtime.
                            path = el['PropertyValue_ReferenceValuePathElement']
                        else:
                            # But it's a different key in the 'python27' production runtime.
                            path = el['ReferenceValuePathElement']
                        paths.append("%s(%s)" % (path['type'], id_or_name(path)))
                    value = "->".join(paths)
                elif 'booleanvalue' in propval:
                    value = propval["booleanvalue"]
                elif 'uservalue' in propval:
                    if 'PropertyValue_UserValue' in propval['uservalue']:
                        # This key exists in dev and in the 'python' production runtime.
                        email = propval['uservalue']['PropertyValue_UserValue']['email']
                    else:
                        # But it's a different key in the 'python27' production runtime.
                        email = propval['uservalue']['UserValue']['email']
                    value = 'User(%s)' % email
                elif '...' in propval:
                    value = '...'
                elif 'int64value' in propval:
                    value = propval["int64value"]
                else:
                    raise Exception(propval)
            else:
                value = ''
            filters_clean.append((name, op, value))
    return filters_clean

def datastore_query_order(query):
    orders = query.get('order', [])
    _Direction_NAMES = {
        0: "?DIR",
        1: "ASC",
        2: "DESC",
    }
    orders_clean = []
    for order in orders:
        if 'Query_Order' in order:
            # This key exists in dev and in the 'python' production runtime.
            order = order['Query_Order']
        else:
            # But it's a different key in the 'python27' production runtime.
            order = order['Order']
        direction = _Direction_NAMES[int(order.get('direction', 0))]
        prop = order.get('property', 'UnknownProperty')
        orders_clean.append((prop, direction))
    return orders_clean

def id_or_name(path):
    if 'name' in path:
        return path['name']
    else:
        return path['id']

def datastore_get(request):
    keys = request["key"]
    if len(keys) > 1:
        keylist = cleanup_key(keys.pop(0))
        for key in keys:
            keylist += ", " + cleanup_key(key)
        return keylist
    elif keys:
        return cleanup_key(keys[0])

def cleanup_key(key):
    if 'Reference' not in key: 
        #sometimes key is passed in as '...'
        return key
    els = key['Reference']['path']['Path']['element']
    paths = []
    for el in els:
        if 'Path_Element' in el:
            # This key exists in dev and in the 'python' production runtime.
            path = el['Path_Element']
        else:
            # But it's a different key in the 'python27' production runtime.
            path = el['Element']
        paths.append("%s(%s)" % (path['type'] if 'type' in path 
                     else 'UnknownType', id_or_name(path)))
    return "->".join(paths)

def datastore_put(request):
    entities = request["entity"]
    keys = []
    for entity in entities:
        keys.append(cleanup_key(entity["EntityProto"]["key"]))
    return "\n".join(keys)

def truncate(value, limit=100):
    if len(value) > limit:
        return value[:limit - 3] + "..."
    else:
        return value

########NEW FILE########
__FILENAME__ = config
import os

from google.appengine.api import lib_config

# These should_profile functions return true whenever a request should be
# profiled.
#
# You can override these functions in appengine_config.py. See example below
# and https://developers.google.com/appengine/docs/python/tools/appengineconfig
#
# These functions will be run once per request, so make sure they are fast.
#
# Example:
#   ...in appengine_config.py:
#       def gae_mini_profiler_should_profile_production():
#           from google.appengine.api import users
#           return users.is_current_user_admin()

def _should_profile_production_default():
    """Default to disabling in production if this function isn't overridden.

    Can be overridden in appengine_config.py"""
    return False

def _should_profile_development_default():
    """Default to enabling in development if this function isn't overridden.

    Can be overridden in appengine_config.py"""
    return True

_config = lib_config.register("gae_mini_profiler", {
    "should_profile_production": _should_profile_production_default,
    "should_profile_development": _should_profile_development_default})

def should_profile():
    """Returns true if the current request should be profiles."""
    if os.environ["SERVER_SOFTWARE"].startswith("Devel"):
        return _config.should_profile_development()
    else:
        return _config.should_profile_production()

########NEW FILE########
__FILENAME__ = cookies
import Cookie
import logging
import os

def get_cookie_value(key):
    cookies = None
    try:
        cookies = Cookie.BaseCookie(os.environ.get('HTTP_COOKIE',''))
    except Cookie.CookieError, error:
        logging.debug("Ignoring Cookie Error, skipping get cookie: '%s'" % error)

    if not cookies:
        return None

    cookie = cookies.get(key)

    if not cookie:
        return None

    return cookie.value

# Cookie handling from http://appengine-cookbook.appspot.com/recipe/a-simple-cookie-class/
def set_cookie_value(key, value='', max_age=None,
               path='/', domain=None, secure=None, httponly=False,
               version=None, comment=None):
    cookies = Cookie.BaseCookie()
    cookies[key] = value
    for var_name, var_value in [
        ('max-age', max_age),
        ('path', path),
        ('domain', domain),
        ('secure', secure),
        #('HttpOnly', httponly), Python 2.6 is required for httponly cookies
        ('version', version),
        ('comment', comment),
        ]:
        if var_value is not None and var_value is not False:
            cookies[key][var_name] = str(var_value)
        if max_age is not None:
            cookies[key]['expires'] = max_age

    cookies_header = cookies[key].output(header='').lstrip()

    if httponly:
        # We have to manually add this part of the header until GAE uses Python 2.6.
        cookies_header += "; HttpOnly"

    return cookies_header



########NEW FILE########
__FILENAME__ = instrumented_profiler
"""CPU profiler that works by instrumenting all function calls (uses cProfile).

This profiler provides detailed function timings for all function calls
during a request.

This is just a simple wrapper for cProfile with result formatting. See
http://docs.python.org/2/library/profile.html for more.

PRO: since every function call is instrumented, you'll be sure to see
everything that goes on during a request. For code that doesn't have lots of
deeply nested function calls, this can be the easiest and most accurate way to
get an idea for which functions are taking lots of time.

CON: overhead is added to each function call due to this instrumentation. If
you're profiling code with deeply nested function calls or tight loops going
over lots of function calls, this perf overhead will add up.
"""

import cProfile
import pstats
import StringIO
import marshal
import base64

import util

class Profile(object):
    """Profiler that wraps cProfile for programmatic access and reporting."""
    def __init__(self):
        self.c_profile = cProfile.Profile()

    def results(self):
        """Return cProfile results in a dictionary for template context."""
        # Make sure nothing is printed to stdout
        output = StringIO.StringIO()
        stats = pstats.Stats(self.c_profile, stream=output)
        stats.sort_stats("cumulative")
        self.c_profile.create_stats()

        results = {
            "raw_stats": base64.b64encode(marshal.dumps(self.c_profile.stats)),
            "total_call_count": stats.total_calls,
            "total_time": util.seconds_fmt(stats.total_tt),
            "calls": []
        }

        width, list_func_names = stats.get_print_list([80])
        for func_name in list_func_names:
            primitive_call_count, total_call_count, total_time, cumulative_time, callers = stats.stats[func_name]

            func_desc = pstats.func_std_string(func_name)

            callers_names = map(lambda func_name: pstats.func_std_string(func_name), callers.keys())
            callers_desc = map(
                    lambda name: {"func_desc": name, "func_desc_short": util.short_method_fmt(name)},
                    callers_names)

            results["calls"].append({
                "primitive_call_count": primitive_call_count,
                "total_call_count": total_call_count,
                "cumulative_time": util.seconds_fmt(cumulative_time, 2),
                "total_time": util.seconds_fmt(total_time, 2),
                "per_call_cumulative": util.seconds_fmt(cumulative_time / primitive_call_count, 2) if primitive_call_count else "",
                "func_desc": func_desc,
                "func_desc_short": util.short_method_fmt(func_desc),
                "callers_desc": callers_desc,
            })

        output.close()

        return results

    def run(self, fxn):
        """Run function with cProfile enabled, saving results."""
        return self.c_profile.runcall(lambda *args, **kwargs: fxn(), None, None)

########NEW FILE########
__FILENAME__ = linebyline_profiler
"""CPU profiler that works by collecting line-by-line stats.

This works by storing a list of functions to profile, then telling
the third party line_profiler module to profile those functions.
"""

import collections
import inspect
import linecache
import os
import re
import sys

_is_dev_server = os.environ["SERVER_SOFTWARE"].startswith("Devel")

# We can't use LineProfiler in production because it requires a C-extension,
# but we can monkey-patch it in here for use on the dev server:
if _is_dev_server:
    if os.environ["SERVER_SOFTWARE"] == "Development/2.0":
        from google.appengine.tools.devappserver2.python import sandbox
        for meta in sys.meta_path:
            if isinstance(meta, sandbox.PathRestrictingImportHook):
                # module name looks something like
                # 'gae_mini_profiler._line_profiler'
                meta._enabled_regexes.append(
                        re.compile(r'(?:.*\.)?_line_profiler$'))
                break
        else:
            assert False, "Can't find PathRestrictingImportHook in meta_path"
    else:
        from google.appengine.tools import dev_appserver
        if isinstance(sys.meta_path[0], dev_appserver.HardenedModulesHook):
            sys.meta_path[0]._white_list_c_modules += ['_line_profiler']

    try:
        import line_profiler
        assert line_profiler  # silence pyflakes
    except ImportError:
        line_profiler = None
else:
    line_profiler = None

_FUNCTION_MARKER = "__gae_linebyline_profile"

_functions_to_profile = []


def line_profile(f):
    """The passed function will be included in the line profile displayed by
    the line profiler panel.
    """
    # TODO(jlfwong): See if this is needed.
    f.__dict__[_FUNCTION_MARKER] = True
    if f not in _functions_to_profile:
        _functions_to_profile.append(f)

    return f


def _process_line_stats(line_stats):
    """Convert line_profiler.LineStats instance into a dict.

    The returned dict has the following format:

        [{
            "filename": the filename of the function being profiled
            "start_lineno": the first line number of the function
            "func_name": the name of the function
            "total_time_ms": total time spent inside the function in ms
            "total_time_ms_s": formatted string version of above
            "timings": [{
                'lineno': line number being profiled
                'line': string source line being profiled
                'perc_time': percent of total time spent on this line
                'perc_time_s': formatted string version of above
                'time_ms': total time spent on this line
                'time_ms_s': formatted string version of above
                'numhits': the number of times this line was run
            }, ...]
        }, ...]
    """

    profile_results = []

    if not line_stats:
        return profile_results

    # We want timings in ms (instead of CPython's microseconds)
    multiplier = line_stats.unit / 1e-3

    for key, timings in sorted(line_stats.timings.items()):
        if not timings:
            continue

        filename, start_lineno, func_name = key

        all_lines = linecache.getlines(filename)
        sublines = inspect.getblock(all_lines[start_lineno - 1:])
        end_lineno = start_lineno + len(sublines)

        line_to_timing = collections.defaultdict(lambda: (-1, 0))

        for (lineno, nhits, time) in timings:
            line_to_timing[lineno] = (nhits, time)

        padded_timings = []

        for lineno in range(start_lineno, end_lineno):
            nhits, time = line_to_timing[lineno]
            padded_timings.append((lineno, nhits, time))

        timings = []

        result = {
            'filename': filename,
            'start_lineno': start_lineno,
            'func_name': func_name,
            'total_time_ms': (sum([time for _, _, time in padded_timings]) *
                    multiplier),
            'timings': []
        }

        result['total_time_ms_s'] = '%.0f' % result['total_time_ms']

        for (lineno, nhits, time) in padded_timings:
            time_ms = time * multiplier
            perc_time = (100.0 * time_ms) / result['total_time_ms']

            result['timings'].append({
                'lineno': lineno,
                'line': all_lines[lineno - 1],
                'perc_time': perc_time,
                'perc_time_s': '%.1f' % perc_time,
                'time_ms': time_ms,
                'time_ms_s': "%.2f" % time_ms,
                'numhits': nhits
            })

        profile_results.append(result)

    return profile_results


class Profile(object):
    """Profiler wrapping line_profiler."""
    def __init__(self):
        self.num_functions_marked = len(_functions_to_profile)

        if line_profiler is None:
            self.line_prof = None
        else:
            self.line_prof = line_profiler.LineProfiler()

            for f in _functions_to_profile:
                self.line_prof.add_function(f)

    def results(self):
        err_msg = ""

        if not _is_dev_server:
            err_msg = "The line-by-line profiler can only be used in dev."
        elif line_profiler is None:
            err_msg = (
                "Could not load the line_profiler module.<br><br>"
                "Try installing the C extension like so:<br>"
                "&nbsp;&nbsp;sudo pip install line_profiler==1.0b3<br>"
                "&nbsp;&nbsp;(cd / && cp `python -c 'import _line_profiler; print _line_profiler.__file__'` %s)" % os.path.dirname(__file__)
            )

        res = {
            "err_msg": err_msg,
            "num_functions_marked": self.num_functions_marked,
            "calls": []
        }

        if self.line_prof and self.num_functions_marked:
            res["calls"] = _process_line_stats(self.line_prof.get_stats())

        return res

    def run(self, fxn):
        if self.line_prof is None:
            return fxn()
        else:
            return self.line_prof.runcall(fxn)

########NEW FILE########
__FILENAME__ = line_profiler
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import cPickle
from cStringIO import StringIO
import inspect
import linecache
import optparse
import os
import sys

from _line_profiler import LineProfiler as CLineProfiler


CO_GENERATOR = 0x0020
def is_generator(f):
    """ Return True if a function is a generator.
    """
    isgen = (f.func_code.co_flags & CO_GENERATOR) != 0 
    return isgen

# Code to exec inside of LineProfiler.__call__ to support PEP-342-style
# generators in Python 2.5+.
pep342_gen_wrapper = '''
def wrap_generator(self, func):
    """ Wrap a generator to profile it.
    """
    def f(*args, **kwds):
        g = func(*args, **kwds)
        # The first iterate will not be a .send()
        self.enable_by_count()
        try:
            item = g.next()
        finally:
            self.disable_by_count()
        input = (yield item)
        # But any following one might be.
        while True:
            self.enable_by_count()
            try:
                item = g.send(input)
            finally:
                self.disable_by_count()
            input = (yield item)
    return f
'''

class LineProfiler(CLineProfiler):
    """ A profiler that records the execution times of individual lines.
    """

    def __call__(self, func):
        """ Decorate a function to start the profiler on function entry and stop
        it on function exit.
        """
        self.add_function(func)
        if is_generator(func):
            f = self.wrap_generator(func)
        else:
            f = self.wrap_function(func)
        f.__module__ = func.__module__
        f.__name__ = func.__name__
        f.__doc__ = func.__doc__
        f.__dict__.update(getattr(func, '__dict__', {}))
        return f

    if sys.version_info[:2] >= (2,5):
        # Delay compilation because the syntax is not compatible with older
        # Python versions.
        exec pep342_gen_wrapper
    else:
        def wrap_generator(self, func):
            """ Wrap a generator to profile it.
            """
            def f(*args, **kwds):
                g = func(*args, **kwds)
                while True:
                    self.enable_by_count()
                    try:
                        item = g.next()
                    finally:
                        self.disable_by_count()
                    yield item
            return f

    def wrap_function(self, func):
        """ Wrap a function to profile it.
        """
        def f(*args, **kwds):
            self.enable_by_count()
            try:
                result = func(*args, **kwds)
            finally:
                self.disable_by_count()
            return result
        return f

    def dump_stats(self, filename):
        """ Dump a representation of the data to a file as a pickled LineStats
        object from `get_stats()`.
        """
        lstats = self.get_stats()
        f = open(filename, 'wb')
        try:
            cPickle.dump(lstats, f, cPickle.HIGHEST_PROTOCOL)
        finally:
            f.close()

    def print_stats(self, stream=None):
        """ Show the gathered statistics.
        """
        lstats = self.get_stats()
        show_text(lstats.timings, lstats.unit, stream=stream)

    def run(self, cmd):
        """ Profile a single executable statment in the main namespace.
        """
        import __main__
        dict = __main__.__dict__
        return self.runctx(cmd, dict, dict)

    def runctx(self, cmd, globals, locals):
        """ Profile a single executable statement in the given namespaces.
        """
        self.enable_by_count()
        try:
            exec cmd in globals, locals
        finally:
            self.disable_by_count()
        return self

    def runcall(self, func, *args, **kw):
        """ Profile a single function call.
        """
        self.enable_by_count()
        try:
            return func(*args, **kw)
        finally:
            self.disable_by_count()


def show_func(filename, start_lineno, func_name, timings, unit, stream=None):
    """ Show results for a single function.
    """
    if stream is None:
        stream = sys.stdout
    print >>stream, "File: %s" % filename
    print >>stream, "Function: %s at line %s" % (func_name, start_lineno)
    template = '%6s %9s %12s %8s %8s  %-s'
    d = {}
    total_time = 0.0
    linenos = []
    for lineno, nhits, time in timings:
        total_time += time
        linenos.append(lineno)
    print >>stream, "Total time: %g s" % (total_time * unit)
    if not os.path.exists(filename):
        print >>stream, ""
        print >>stream, "Could not find file %s" % filename
        print >>stream, "Are you sure you are running this program from the same directory"
        print >>stream, "that you ran the profiler from?"
        print >>stream, "Continuing without the function's contents."
        # Fake empty lines so we can see the timings, if not the code.
        nlines = max(linenos) - min(min(linenos), start_lineno) + 1
        sublines = [''] * nlines
    else:
        all_lines = linecache.getlines(filename)
        sublines = inspect.getblock(all_lines[start_lineno-1:])
    for lineno, nhits, time in timings:
        d[lineno] = (nhits, time, '%5.1f' % (float(time) / nhits),
            '%5.1f' % (100*time / total_time))
    linenos = range(start_lineno, start_lineno + len(sublines))
    empty = ('', '', '', '')
    header = template % ('Line #', 'Hits', 'Time', 'Per Hit', '% Time', 
        'Line Contents')
    print >>stream, ""
    print >>stream, header
    print >>stream, '=' * len(header)
    for lineno, line in zip(linenos, sublines):
        nhits, time, per_hit, percent = d.get(lineno, empty)
        print >>stream, template % (lineno, nhits, time, per_hit, percent,
            line.rstrip('\n').rstrip('\r'))
    print >>stream, ""

def show_text(stats, unit, stream=None):
    """ Show text for the given timings.
    """
    if stream is None:
        stream = sys.stdout
    print >>stream, 'Timer unit: %g s' % unit
    print >>stream, ''
    for (fn, lineno, name), timings in sorted(stats.items()):
        show_func(fn, lineno, name, stats[fn, lineno, name], unit, stream=stream)

# A %lprun magic for IPython.
def magic_lprun(self, parameter_s=''):
    """ Execute a statement under the line-by-line profiler from the
    line_profiler module.

    Usage:
      %lprun -f func1 -f func2 <statement>

    The given statement (which doesn't require quote marks) is run via the
    LineProfiler. Profiling is enabled for the functions specified by the -f
    options. The statistics will be shown side-by-side with the code through the
    pager once the statement has completed.

    Options:
    
    -f <function>: LineProfiler only profiles functions and methods it is told
    to profile.  This option tells the profiler about these functions. Multiple
    -f options may be used. The argument may be any expression that gives
    a Python function or method object. However, one must be careful to avoid
    spaces that may confuse the option parser. Additionally, functions defined
    in the interpreter at the In[] prompt or via %run currently cannot be
    displayed.  Write these functions out to a separate file and import them.

    One or more -f options are required to get any useful results.

    -D <filename>: dump the raw statistics out to a pickle file on disk. The
    usual extension for this is ".lprof". These statistics may be viewed later
    by running line_profiler.py as a script.

    -T <filename>: dump the text-formatted statistics with the code side-by-side
    out to a text file.

    -r: return the LineProfiler object after it has completed profiling.
    """
    # Local imports to avoid hard dependency.
    from distutils.version import LooseVersion
    import IPython
    ipython_version = LooseVersion(IPython.__version__)
    if ipython_version < '0.11':
        from IPython.genutils import page
        from IPython.ipstruct import Struct
        from IPython.ipapi import UsageError
    else:
        from IPython.core.page import page
        from IPython.utils.ipstruct import Struct
        from IPython.core.error import UsageError

    # Escape quote markers.
    opts_def = Struct(D=[''], T=[''], f=[])
    parameter_s = parameter_s.replace('"',r'\"').replace("'",r"\'")
    opts, arg_str = self.parse_options(parameter_s, 'rf:D:T:', list_all=True)
    opts.merge(opts_def)

    global_ns = self.shell.user_global_ns
    local_ns = self.shell.user_ns

    # Get the requested functions.
    funcs = []
    for name in opts.f:
        try:
            funcs.append(eval(name, global_ns, local_ns))
        except Exception, e:
            raise UsageError('Could not find function %r.\n%s: %s' % (name, 
                e.__class__.__name__, e))

    profile = LineProfiler(*funcs)

    # Add the profiler to the builtins for @profile.
    import __builtin__
    if 'profile' in __builtin__.__dict__:
        had_profile = True
        old_profile = __builtin__.__dict__['profile']
    else:
        had_profile = False
        old_profile = None
    __builtin__.__dict__['profile'] = profile

    try:
        try:
            profile.runctx(arg_str, global_ns, local_ns)
            message = ''
        except SystemExit:
            message = """*** SystemExit exception caught in code being profiled."""
        except KeyboardInterrupt:
            message = ("*** KeyboardInterrupt exception caught in code being "
                "profiled.")
    finally:
        if had_profile:
            __builtin__.__dict__['profile'] = old_profile

    # Trap text output.
    stdout_trap = StringIO()
    profile.print_stats(stdout_trap)
    output = stdout_trap.getvalue()
    output = output.rstrip()

    if ipython_version < '0.11':
        page(output, screen_lines=self.shell.rc.screen_length)
    else:
        page(output)
    print message,

    dump_file = opts.D[0]
    if dump_file:
        profile.dump_stats(dump_file)
        print '\n*** Profile stats pickled to file',\
              `dump_file`+'.',message

    text_file = opts.T[0]
    if text_file:
        pfile = open(text_file, 'w')
        pfile.write(output)
        pfile.close()
        print '\n*** Profile printout saved to text file',\
              `text_file`+'.',message

    return_value = None
    if opts.has_key('r'):
        return_value = profile

    return return_value


def load_ipython_extension(ip):
    """ API for IPython to recognize this module as an IPython extension.
    """
    ip.define_magic('lprun', magic_lprun)


def load_stats(filename):
    """ Utility function to load a pickled LineStats object from a given
    filename.
    """
    f = open(filename, 'rb')
    try:
        lstats = cPickle.load(f)
    finally:
        f.close()
    return lstats


def main():
    usage = "usage: %prog profile.lprof"
    parser = optparse.OptionParser(usage=usage, version='%prog 1.0b2')

    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error("Must provide a filename.")
    lstats = load_stats(args[0])
    show_text(lstats.timings, lstats.unit)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = main
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import profiler

application = webapp.WSGIApplication([
    ("/gae_mini_profiler/request/log", profiler.RequestLogHandler),
    ("/gae_mini_profiler/request", profiler.RequestStatsHandler),
    ("/gae_mini_profiler/shared/raw", profiler.RawSharedStatsHandler),
    ("/gae_mini_profiler/shared", profiler.SharedStatsHandler),
])

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = profiler
from __future__ import with_statement

import datetime
import time
import logging
import os
import re
import urlparse
import base64

try:
    import threading
except ImportError:
    import dummy_threading as threading

# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

import StringIO
from types import GeneratorType
import zlib

from google.appengine.api import logservice
from google.appengine.api import memcache
from google.appengine.ext.appstats import recording
from google.appengine.ext.webapp import RequestHandler

import cookies
import pickle
import config
import util

dev_server = os.environ["SERVER_SOFTWARE"].startswith("Devel")


class CurrentRequestId(object):
    """A per-request identifier accessed by other pieces of mini profiler.
    
    It is managed as part of the middleware lifecycle."""

    # In production use threading.local() to make request ids threadsafe
    _local = threading.local()
    _local.request_id = None

    # On the devserver don't use threading.local b/c it's reset on Thread.start
    dev_server_request_id = None

    @staticmethod
    def get():
        if dev_server:
            return CurrentRequestId.dev_server_request_id
        else:
            return CurrentRequestId._local.request_id

    @staticmethod
    def set(request_id):
        if dev_server:
            CurrentRequestId.dev_server_request_id = request_id
        else:
            CurrentRequestId._local.request_id = request_id


class Mode(object):
    """Possible profiler modes.
    
    TODO(kamens): switch this from an enum to a more sensible bitmask or other
    alternative that supports multiple settings without an exploding number of
    enums.
    
    TODO(kamens): when this is changed from an enum to a bitmask or other more
    sensible object with multiple properties, we should pass a Mode object
    around the rest of this code instead of using a simple string that this
    static class is forced to examine (e.g. if self.mode.is_rpc_enabled()).
    """

    SIMPLE = "simple"  # Simple start/end timing for the request as a whole
    CPU_INSTRUMENTED = "instrumented"  # Profile all function calls
    CPU_SAMPLING = "sampling"  # Sample call stacks
    CPU_LINEBYLINE = "linebyline" # Line-by-line profiling on a subset of functions
    RPC_ONLY = "rpc"  # Profile all RPC calls
    RPC_AND_CPU_INSTRUMENTED = "rpc_instrumented" # RPCs and all fxn calls
    RPC_AND_CPU_SAMPLING = "rpc_sampling" # RPCs and sample call stacks
    RPC_AND_CPU_LINEBYLINE = "rpc_linebyline" # RPCs and line-by-line profiling

    @staticmethod
    def get_mode(environ):
        """Get the profiler mode requested by current request's headers &
        cookies."""
        if "HTTP_G_M_P_MODE" in environ:
            mode = environ["HTTP_G_M_P_MODE"]
        else:
            mode = cookies.get_cookie_value("g-m-p-mode")

        if (mode not in [
                Mode.SIMPLE,
                Mode.CPU_INSTRUMENTED,
                Mode.CPU_SAMPLING,
                Mode.CPU_LINEBYLINE,
                Mode.RPC_ONLY,
                Mode.RPC_AND_CPU_INSTRUMENTED,
                Mode.RPC_AND_CPU_SAMPLING,
                Mode.RPC_AND_CPU_LINEBYLINE]):
            mode = Mode.RPC_AND_CPU_INSTRUMENTED

        return mode

    @staticmethod
    def is_rpc_enabled(mode):
        return mode in [
                Mode.RPC_ONLY,
                Mode.RPC_AND_CPU_INSTRUMENTED,
                Mode.RPC_AND_CPU_SAMPLING]

    @staticmethod
    def is_sampling_enabled(mode):
        return mode in [
                Mode.CPU_SAMPLING,
                Mode.RPC_AND_CPU_SAMPLING]

    @staticmethod
    def is_instrumented_enabled(mode):
        return mode in [
                Mode.CPU_INSTRUMENTED,
                Mode.RPC_AND_CPU_INSTRUMENTED]

    @staticmethod
    def is_linebyline_enabled(mode):
        return mode in [
                Mode.CPU_LINEBYLINE,
                Mode.RPC_AND_CPU_LINEBYLINE]

class RawSharedStatsHandler(RequestHandler):
    def get(self):
        request_id = self.request.get("request_id")
        request_stats = RequestStats.get(request_id)

        if not request_stats:
            self.response.out.write("Profiler stats no longer exist for this request.")
            return

        if not 'raw_stats' in request_stats.profiler_results:
            self.response.out.write("No raw states available for this profile")
            return

        self.response.headers['Content-Disposition'] = (
                'attachment; filename="g-m-p-%s.profile"' % str(request_id))
        self.response.headers['Content-type'] = "application/octet-stream"
        self.response.out.write(
                base64.b64decode(request_stats.profiler_results['raw_stats']))


class SharedStatsHandler(RequestHandler):

    def get(self):
        path = os.path.join(os.path.dirname(__file__), "templates/shared.html")

        request_id = self.request.get("request_id")
        if not RequestStats.get(request_id):
            self.response.out.write("Profiler stats no longer exist for this request.")
            return

        # Late-bind templatetags to avoid a circular import.
        # TODO(chris): remove late-binding once templatetags has been teased
        # apart and no longer contains so many broad dependencies.

        import templatetags
        profiler_includes = templatetags.profiler_includes_request_id(request_id, True)

        # We are not using a templating engine here to avoid pulling in Jinja2
        # or Django. It's an admin page anyway, and all other templating lives
        # in javascript right now.

        with open(path, 'rU') as f:
            template = f.read()

        template = template.replace('{{profiler_includes}}', profiler_includes)
        self.response.out.write(template)


class RequestLogHandler(RequestHandler):
    """Handler for retrieving and returning a RequestLog from GAE's logs API.

    See https://developers.google.com/appengine/docs/python/logs.
    
    This GET request accepts a logging_request_id via query param that matches
    the request_id from an App Engine RequestLog.

    It returns a JSON object that contains the pieces of RequestLog info we
    find most interesting, such as pending_ms and loading_request.
    """

    def get(self):

        self.response.headers["Content-Type"] = "application/json"
        dict_request_log = None

        # This logging_request_id should match a request_id from an App Engine
        # request log.
        # https://developers.google.com/appengine/docs/python/logs/functions
        logging_request_id = self.request.get("logging_request_id")

        # Grab the single request log from logservice
        logs = logservice.fetch(request_ids=[logging_request_id])

        # This slightly strange query result implements __iter__ but not next,
        # so we have to iterate to get our expected single result.
        for log in logs:
            dict_request_log = {
                "pending_ms": log.pending_time,  # time spent in pending queue
                "loading_request": log.was_loading_request,  # loading request?
                "logging_request_id": logging_request_id
            }
            # We only expect a single result.
            break

        # Log fetching doesn't work on the dev server and this data isn't
        # relevant in dev server's case, so we return a simple fake response.
        if dev_server:
            dict_request_log = {
                "pending_ms": 0,
                "loading_request": False,
                "logging_request_id": logging_request_id
            }

        self.response.out.write(json.dumps(dict_request_log))


class RequestStatsHandler(RequestHandler):

    def get(self):

        self.response.headers["Content-Type"] = "application/json"

        list_request_ids = []

        request_ids = self.request.get("request_ids")
        if request_ids:
            list_request_ids = request_ids.split(",")

        list_request_stats = []

        for request_id in list_request_ids:

            request_stats = RequestStats.get(request_id)

            if request_stats and not request_stats.disabled:

                dict_request_stats = {}
                for property in RequestStats.serialized_properties:
                    dict_request_stats[property] = request_stats.__getattribute__(property)

                list_request_stats.append(dict_request_stats)

                # Don't show temporary redirect profiles more than once automatically, as they are
                # tied to URL params and may be copied around easily.
                if request_stats.temporary_redirect:
                    request_stats.disabled = True
                    request_stats.store()

        self.response.out.write(json.dumps(list_request_stats))

class RequestStats(object):

    serialized_properties = ["request_id", "url", "s_dt",
                             "profiler_results", "appstats_results", "mode",
                             "temporary_redirect", "logs",
                             "logging_request_id"]

    def __init__(self, profiler, environ):
        # unique mini profiler request id
        self.request_id = profiler.request_id

        # App Engine's logservice request_id
        # https://developers.google.com/appengine/docs/python/logs/
        self.logging_request_id = profiler.logging_request_id

        self.url = environ.get("PATH_INFO")
        if environ.get("QUERY_STRING"):
            self.url += "?%s" % environ.get("QUERY_STRING")

        self.mode = profiler.mode
        self.s_dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.profiler_results = profiler.profiler_results()
        self.appstats_results = profiler.appstats_results()
        self.logs = profiler.logs

        self.temporary_redirect = profiler.temporary_redirect
        self.disabled = False

    def store(self):
        # Store compressed results so we stay under the memcache 1MB limit
        pickled = pickle.dumps(self)
        compressed_pickled = zlib.compress(pickled)
        if len(compressed_pickled) > memcache.MAX_VALUE_SIZE:
            logging.warning('RequestStats bigger (%d) '
                + 'than max memcache size (%d), even after compression',
                len(compressed_pickled), memcache.MAX_VALUE_SIZE)
            return False

        return memcache.set(RequestStats.memcache_key(self.request_id), compressed_pickled)

    @staticmethod
    def get(request_id):
        if request_id:

            compressed_pickled = memcache.get(RequestStats.memcache_key(request_id))

            if compressed_pickled:
                pickled = zlib.decompress(compressed_pickled)
                return pickle.loads(pickled)

        return None

    @staticmethod
    def memcache_key(request_id):
        if not request_id:
            return None
        return "__gae_mini_profiler_request_%s" % request_id


class RequestProfiler(object):
    """Profile a single request."""

    def __init__(self, request_id, mode):
        self.request_id = request_id
        self.mode = mode
        self.instrumented_prof = None
        self.sampling_prof = None
        self.linebyline_prof = None
        self.appstats_prof = None
        self.temporary_redirect = False
        self.handler = None
        self.logs = None
        self.logging_request_id = self.get_logging_request_id()
        self.start = None
        self.end = None

    def profiler_results(self):
        """Return the CPU profiler results for this request, if any.
        
        This will return a dictionary containing results for either the
        sampling profiler, instrumented profiler results, or a simple
        start/stop timer if both profilers are disabled."""

        total_time = util.seconds_fmt(self.end - self.start, 0)
        results = {"total_time": total_time}

        if self.instrumented_prof:
            results.update(self.instrumented_prof.results())
        elif self.sampling_prof:
            results.update(self.sampling_prof.results())
        elif self.linebyline_prof:
            results.update(self.linebyline_prof.results())

        return results

    def appstats_results(self):
        """Return the RPC profiler (appstats) results for this request, if any.

        This will return a dictionary containing results from appstats or an
        empty result set if appstats profiling is disabled."""

        results = {
                "calls": [],
                "total_time": 0,
                }

        if self.appstats_prof:
            results.update(self.appstats_prof.results())

        return results

    def profile_start_response(self, app, environ, start_response):
        """Collect and store statistics for a single request.

        Use this method from middleware in place of the standard
        request-serving pattern. Do:

           profiler = RequestProfiler(...)
           return profiler(app, environ, start_response)

        Instead of:

           return app(environ, start_response)

        Depending on the mode, this method gathers timing information
        and an execution profile and stores them in the datastore for
        later access.
        """

        # Always track simple start/stop time.
        self.start = time.time()

        if self.mode == Mode.SIMPLE:

            # Detailed recording is disabled.
            result = app(environ, start_response)
            for value in result:
                yield value

        else:

            # Add logging handler
            self.add_handler()

            if Mode.is_rpc_enabled(self.mode):
                # Turn on AppStats monitoring for this request
                # Note that we don't import appstats_profiler at the top of
                # this file so we don't bring in a lot of imports for users who
                # don't have the profiler enabled.
                from . import appstats_profiler
                self.appstats_prof = appstats_profiler.Profile()
                app = self.appstats_prof.wrap(app)

            # By default, we create a placeholder wrapper function that
            # simply calls whatever function it is passed as its first
            # argument.
            result_fxn_wrapper = lambda fxn: fxn()

            # TODO(kamens): both sampling_profiler and instrumented_profiler
            # could subclass the same class. Then they'd both be guaranteed to
            # implement run(), and the following if/else could be simplified.
            if Mode.is_sampling_enabled(self.mode):
                # Turn on sampling profiling for this request.
                # Note that we don't import sampling_profiler at the top of
                # this file so we don't bring in a lot of imports for users who
                # don't have the profiler enabled.
                from . import sampling_profiler
                self.sampling_prof = sampling_profiler.Profile()
                result_fxn_wrapper = self.sampling_prof.run

            elif Mode.is_linebyline_enabled(self.mode):
                from . import linebyline_profiler
                self.linebyline_prof = linebyline_profiler.Profile()
                result_fxn_wrapper = self.linebyline_prof.run

            elif Mode.is_instrumented_enabled(self.mode):
                # Turn on cProfile instrumented profiling for this request
                # Note that we don't import instrumented_profiler at the top of
                # this file so we don't bring in a lot of imports for users who
                # don't have the profiler enabled.
                from . import instrumented_profiler
                self.instrumented_prof = instrumented_profiler.Profile()
                result_fxn_wrapper = self.instrumented_prof.run

            # Get wsgi result
            result = result_fxn_wrapper(lambda: app(environ, start_response))

            # If we're dealing w/ a generator, profile all of the .next calls as well
            if type(result) == GeneratorType:

                while True:
                    try:
                        yield result_fxn_wrapper(result.next)
                    except StopIteration:
                        break

            else:
                for value in result:
                    yield value

            self.logs = self.get_logs(self.handler)
            logging.getLogger().removeHandler(self.handler)
            self.handler.stream.close()
            self.handler = None

        self.end = time.time()

        # Store stats for later access
        RequestStats(self, environ).store()

    def get_logging_request_id(self):
        """Return the identifier for this request used by GAE's logservice.
        
        This logging_request_id will match the request_id parameter of a
        RequestLog object stored in App Engine's logging API:
        https://developers.google.com/appengine/docs/python/logs/
        """
        return os.environ.get("REQUEST_LOG_ID", None)

    def add_handler(self):
        if self.handler is None:
            self.handler = RequestProfiler.create_handler()
        logging.getLogger().addHandler(self.handler)

    @staticmethod
    def create_handler():
        handler = logging.StreamHandler(StringIO.StringIO())
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("\t".join([
            '%(levelno)s',
            '%(asctime)s%(msecs)d',
            '%(funcName)s',
            '%(filename)s',
            '%(lineno)d',
            '%(message)s',
        ]), '%M:%S.')
        handler.setFormatter(formatter)
        return handler

    @staticmethod
    def get_logs(handler):
        raw_lines = [l for l in handler.stream.getvalue().split("\n") if l]

        lines = []
        for line in raw_lines:
            if "\t" in line:
                fields = line.split("\t")
                lines.append(fields)
            else: # line is part of a multiline log message (prob a traceback)
                prevline = lines[-1][-1]
                if prevline: # ignore leading blank lines in the message
                    prevline += "\n"
                prevline += line
                lines[-1][-1] = prevline

        return lines

class ProfilerWSGIMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):

        CurrentRequestId.set(None)

        # Never profile calls to the profiler itself to avoid endless recursion.
        if (not config.should_profile() or
            environ.get("PATH_INFO", "").startswith("/gae_mini_profiler/")):
            result = self.app(environ, start_response)
            for value in result:
                yield value
        else:
            # Set a random ID for this request so we can look up stats later
            import base64
            CurrentRequestId.set(base64.urlsafe_b64encode(os.urandom(5)))

            # Send request id in headers so jQuery ajax calls can pick
            # up profiles.
            def profiled_start_response(status, headers, exc_info = None):

                if status.startswith("302 "):
                    # Temporary redirect. Add request identifier to redirect location
                    # so next rendered page can show this request's profile.
                    headers = ProfilerWSGIMiddleware.headers_with_modified_redirect(environ, headers)
                    # Access the profiler in closure scope
                    profiler.temporary_redirect = True

                # Append headers used when displaying profiler results from ajax requests
                headers.append(("X-MiniProfiler-Id", CurrentRequestId.get()))
                headers.append(("X-MiniProfiler-QS", environ.get("QUERY_STRING")))

                return start_response(status, headers, exc_info)

            # As a simple form of rate-limiting, appstats protects all
            # its work with a memcache lock to ensure that only one
            # appstats request ever runs at a time, across all
            # appengine instances.  (GvR confirmed this is the purpose
            # of the lock).  So our attempt to profile will fail if
            # appstats is running on another instance.  Boo-urns!  We
            # just turn off the lock-checking for us, which means we
            # don't rate-limit quite as much with the mini-profiler as
            # we would do without.
            old_memcache_add = memcache.add
            old_memcache_delete = memcache.delete
            memcache.add = (lambda key, *args, **kwargs:
                                (True if key == recording.lock_key() 
                                 else old_memcache_add(key, *args, **kwargs)))
            memcache.delete = (lambda key, *args, **kwargs:
                                   (True if key == recording.lock_key()
                                    else old_memcache_delete(key, *args, **kwargs)))

            try:
                profiler = RequestProfiler(CurrentRequestId.get(),
                                           Mode.get_mode(environ))
                result = profiler.profile_start_response(self.app, environ, profiled_start_response)
                for value in result:
                    yield value
            finally:
                CurrentRequestId.set(None)
                memcache.add = old_memcache_add
                memcache.delete = old_memcache_delete

    @staticmethod
    def headers_with_modified_redirect(environ, headers):
        """Return headers with redirects modified to include miniprofiler id.

        If this response is a redirect, we want the URL that's redirected *to*
        to be able to display the profiler results from *this* request that's
        being redirected *from*. We do this by adding a query string param,
        'mp-r-id', to the location that is being redirected to. (mp-r-id stands
        for mini profiler redirect id.) The value of this parameter is a unique
        identifier for the profiler results for the current request that is
        being redirected from.

        The mini profiler then knows how to use this id to display profiler
        results for two requests: the original request that redirected and the
        request that was served as a result of the redirect.

        e.g. if this set of headers is attempting to redirect to
            Location:http://khanacademy.org?login, the modified header will be:
            Location:http://khanacademy.org?login&mp-r-id={current request id}
        """
        headers_modified = []

        for header in headers:
            if header[0] == "Location":
                reg = re.compile("mp-r-id=([^&]+)")

                # Keep any chain of redirects around
                request_id_chain = CurrentRequestId.get()
                match = reg.search(environ.get("QUERY_STRING"))
                if match:
                    request_id_chain = ",".join([match.groups()[0], request_id_chain])

                # Remove any pre-existing miniprofiler redirect id
                url_parts = list(urlparse.urlparse(header[1]))
                query_string = reg.sub("", url_parts[4])

                # Add current request id as miniprofiler redirect id
                if query_string and not query_string.endswith("&"):
                    query_string += "&"
                query_string += "mp-r-id=%s" % request_id_chain
                url_parts[4] = query_string

                # Swap in the modified Location: header.
                location = urlparse.urlunparse(url_parts)
                headers_modified.append((header[0], location))
            else:
                headers_modified.append(header)

        return headers_modified

########NEW FILE########
__FILENAME__ = sampling_profiler
"""CPU profiler that works by sampling the call stack periodically.

This profiler provides a very simplistic view of where your request is spending
its time. It does this by periodically sampling your request's call stack to
figure out in which functions real time is being spent.

PRO: since the profiler only samples the call stack occasionally, it has much
less overhead than an instrumenting profiler, and avoids biases that
instrumenting profilers have due to instrumentation overhead (which causes
instrumenting profilers to overstate how much time is spent in frequently
called functions, or functions with deep call stacks).

CON: since the profiler only samples, it does not allow you to accurately
answer a question like, "how much time was spent in routine X?", especially if
routine X takes relatively little time.  (You *can* answer questions like "what
is the ratio of time spent in routine X vs routine Y," at least if both
routines take a reasonable amount of time.)  It is better suited for answering
the question, "Where is the time spent by my app?"
"""

from collections import defaultdict
import logging
import sys
import time
import threading

from . import util

class InspectingThread(threading.Thread):
    """Thread that periodically triggers profiler inspections."""
    SAMPLES_PER_SECOND = 250

    def __init__(self, profile=None):
        super(InspectingThread, self).__init__()
        self._stop_event = threading.Event()
        self.profile = profile

    def stop(self):
        """Signal the thread to stop and block until it is finished."""
        # http://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python
        self._stop_event.set()
        self.join()

    def should_stop(self):
        return self._stop_event.is_set()

    def run(self):
        """Start periodic profiler inspections.
        
        This will run, periodically inspecting and then sleeping, until
        manually stopped via stop().

        We try to "stay on schedule" by keeping track of the time we should be
        at and sleeping until that time. This means that if we stop running for
        a while due to context switching or other pauses, we'll start sampling
        faster to catch up, so we'll get the right number of samples in the
        end, but the samples may not be perfectly even."""

        next_sample_time_seconds = time.time()

        # Keep sampling until this thread is explicitly stopped.
        while not self.should_stop():
            # Take a sample of the main request thread's frame stack...
            self.profile.take_sample()

            # ...then sleep and let it do some more work.
            next_sample_time_seconds += (
                1.0 / InspectingThread.SAMPLES_PER_SECOND)
            seconds_to_sleep = next_sample_time_seconds - time.time()
            if seconds_to_sleep > 0:
                time.sleep(seconds_to_sleep)


class ProfileSample(object):
    """Single stack trace sample gathered during a periodic inspection."""
    def __init__(self, stack_trace, timestamp_ms):
        # stack_trace should be a list of (filename, line_num, function_name)
        # triples.
        self.stack_trace = stack_trace
        self.timestamp_ms = timestamp_ms

    @staticmethod
    def from_frame_and_timestamp(active_frame, timestamp_ms):
        """Creates a profile from the current frame of a particular thread.

        The "active_frame" parameter should be the current frame from some
        thread, as returned by sys._current_frames(). Note that we must walk
        the stack trace up-front at sampling time, since it will change out
        from under us if we wait to access it."""
        stack_trace = []
        frame = active_frame
        while frame is not None:
            code = frame.f_code
            stack_trace.append(
                (code.co_filename, frame.f_lineno, code.co_name))
            frame = frame.f_back

        return ProfileSample(stack_trace, timestamp_ms)

    def get_frame_descriptions(self):
        """Gets a list of text descriptions, one for each frame, in order."""
        return ["%s:%s (%s)" % file_line_func
                for file_line_func in self.stack_trace]


class Profile(object):
    """Profiler that periodically inspects a request and logs stack traces."""
    def __init__(self):
        # All saved stack trace samples
        self.samples = []

        # Thread id for the request thread currently being profiled
        self.current_request_thread_id = None

        # Thread that constantly waits, inspects, waits, inspect, ...
        self.inspecting_thread = None

        self.start_time = time.time()

    def results(self):
        """Return sampling results in a dictionary for template context."""
        aggregated_calls = defaultdict(int)
        total_samples = len(self.samples)

        # Compress the results by keeping an array of all of the frame
        # descriptions (we expect that there won't be that many total of them).
        # Each actual stack trace is given as an ordered list of indexes into
        # the array of frames.
        frames = []
        frame_indexes = {}

        for sample in self.samples:
            for frame_desc in sample.get_frame_descriptions():
                if not frame_desc in frame_indexes:
                    frame_indexes[frame_desc] = len(frames)
                    frames.append(frame_desc)

        samples = [{
                "timestamp_ms": util.milliseconds_fmt(sample.timestamp_ms, 1),
                "stack_frames": [frame_indexes[desc]
                                 for desc in sample.get_frame_descriptions()]
            } for sample in self.samples]

        return {
                "frame_names": [
                    util.short_method_fmt(frame) for frame in frames],
                "samples": samples,
                "total_samples": total_samples,
            }

    def take_sample(self):
        # Look at stacks of all existing threads...
        # See http://bzimmer.ziclix.com/2008/12/17/python-thread-dumps/
        for thread_id, active_frame in sys._current_frames().items():
            # ...but only sample from the main request thread.
            # TODO(kamens): this profiler will need work if we ever
            # actually use multiple threads in a single request and want to
            # profile more than one of them.
            if thread_id == self.current_request_thread_id:
                # Grab a sample of this thread's current stack
                timestamp_ms = (time.time() - self.start_time) * 1000
                self.samples.append(ProfileSample.from_frame_and_timestamp(
                        active_frame, timestamp_ms))

    def run(self, fxn):
        """Run function with samping profiler enabled, saving results."""

        if not hasattr(threading, "current_thread"):
            # Sampling profiler is not supported in Python2.5
            logging.warn("The sampling profiler is not supported in Python2.5")
            return fxn()

        # Store the thread id for the current request's thread. This lets
        # the inspecting thread know which thread to inspect.
        self.current_request_thread_id = threading.current_thread().ident

        # Start the thread that will be periodically inspecting the frame
        # stack of this current request thread
        self.inspecting_thread = InspectingThread(profile=self)
        self.inspecting_thread.start()

        try:
            # Run the request fxn which will be inspected by the inspecting
            # thread.
            return fxn()
        finally:
            # Stop and clear the inspecting thread
            self.inspecting_thread.stop()
            self.inspecting_thread = None

########NEW FILE########
__FILENAME__ = templatetags
# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

import profiler


def profiler_includes_request_id(request_id, show_immediately=False):
    if not request_id:
        return ""

    js_path = "/gae_mini_profiler/static/js/profiler.js"
    css_path = "/gae_mini_profiler/static/css/profiler.css"

    return """
<link rel="stylesheet" type="text/css" href="%s" />
<script type="text/javascript" src="%s"></script>
<script type="text/javascript">GaeMiniProfiler.init("%s", %s)</script>
    """ % (css_path, js_path, request_id, json.dumps(show_immediately))


def profiler_includes():
    return profiler_includes_request_id(profiler.CurrentRequestId.get())

########NEW FILE########
__FILENAME__ = util
def seconds_fmt(f, n=0):
    return milliseconds_fmt(f * 1000, n)

def milliseconds_fmt(f, n=0):
    return decimal_fmt(f, n)

def decimal_fmt(f, n=0):
    format = "%." + str(n) + "f"
    return format % f

def short_method_fmt(s):
    return s[s.rfind("/") + 1:]

def short_rpc_file_fmt(s):
    if not s:
        return ""
    return s[s.find("/"):]

########NEW FILE########
