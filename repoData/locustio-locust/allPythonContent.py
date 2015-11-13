__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import os

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ["sphinx.ext.autodoc", "sphinx.ext.intersphinx"]

# autoclass options
#autoclass_content = "both"

# Add any paths that contain templates here, relative to this directory.
#templates_path = ["_templates"]

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'Locust'
#copyright = ''

# Intersphinx config
intersphinx_mapping = {
    'requests': ('http://requests.readthedocs.org/en/latest/', None),
}

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
from locust import version

# The full version, including alpha/beta/rc tags.
release = version

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = False

# Sphinx will recurse into subversion configuration folders and try to read  
# any document file within. These should be ignored. 
# Note: exclude_dirnames is new in Sphinx 0.5 
exclude_dirnames = []

# Options for HTML output
# -----------------------

html_show_sourcelink = False
html_file_suffix = ".html"


# on_rtd is whether we are on readthedocs.org, this line of code grabbed from docs.readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# HTML theme
#html_theme = "haiku"

#html_theme = "default"
#html_theme_options = {
#    "rightsidebar": "true",
#    "codebgcolor": "#fafcfa",
#    "bodyfont": "Arial",
#}

# The name of the Pygments (syntax highlighting) style to use.
#pygments_style = 'trac'

########NEW FILE########
__FILENAME__ = basic
from locust import HttpLocust, TaskSet, task

def index(l):
    l.client.get("/")

def stats(l):
    l.client.get("/stats/requests")

class UserTasks(TaskSet):
    # one can specify tasks like this
    tasks = [index, stats]
    
    # but it might be convenient to use the @task decorator
    @task
    def page404(self):
        self.client.get("/does_not_exist")
    
class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """
    host = "http://127.0.0.1:8089"
    min_wait = 2000
    max_wait = 5000
    task_set = UserTasks

########NEW FILE########
__FILENAME__ = server
import time
import random
from SimpleXMLRPCServer import SimpleXMLRPCServer
import xmlrpclib

def get_time():
    time.sleep(random.random())
    return time.time()

def get_random_number(low, high):
    time.sleep(random.random())
    return random.randint(low, high)

server = SimpleXMLRPCServer(("localhost", 8877))
print "Listening on port 8877..."
server.register_function(get_time, "get_time")
server.register_function(get_random_number, "get_random_number")
server.serve_forever()

########NEW FILE########
__FILENAME__ = xmlrpc_locustfile
import time
import xmlrpclib

from locust import Locust, events, task, TaskSet


class XmlRpcClient(xmlrpclib.ServerProxy):
    """
    Simple, sample XML RPC client implementation that wraps xmlrpclib.ServerProxy and 
    fires locust events on request_success and request_failure, so that all requests 
    gets tracked in locust's statistics.
    """
    def __getattr__(self, name):
        func = xmlrpclib.ServerProxy.__getattr__(self, name)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
            except xmlrpclib.Fault as e:
                total_time = int((time.time() - start_time) * 1000)
                events.request_failure.fire(request_type="xmlrpc", name=name, response_time=total_time, exception=e)
            else:
                total_time = int((time.time() - start_time) * 1000)
                events.request_success.fire(request_type="xmlrpc", name=name, response_time=total_time, response_length=0)
                # In this example, I've hardcoded response_length=0. If we would want the response length to be 
                # reported correctly in the statistics, we would probably need to hook in at a lower level
        
        return wrapper


class XmlRpcLocust(Locust):
    """
    This is the abstract Locust class which should be subclassed. It provides an XML-RPC client
    that can be used to make XML-RPC requests that will be tracked in Locust's statistics.
    """
    def __init__(self, *args, **kwargs):
        super(XmlRpcLocust, self).__init__(*args, **kwargs)
        self.client = XmlRpcClient(self.host)


class ApiUser(XmlRpcLocust):
    
    host = "http://127.0.0.1:8877/"
    min_wait = 100
    max_wait = 1000
    
    class task_set(TaskSet):
        @task(10)
        def get_time(self):
            self.client.get_time()
        
        @task(5)
        def get_random_number(self):
            self.client.get_random_number(0, 100)

########NEW FILE########
__FILENAME__ = events
# encoding: utf-8

"""
This is an example of a locustfile that uses Locust's built in event hooks to 
track the sum of the content-length header in all successful HTTP responses
"""

from locust import HttpLocust, TaskSet, task, events, web

class MyTaskSet(TaskSet):
    @task(2)
    def index(l):
        l.client.get("/")
    
    @task(1)
    def stats(l):
        l.client.get("/stats/requests")

class WebsiteUser(HttpLocust):
    host = "http://127.0.0.1:8089"
    min_wait = 2000
    max_wait = 5000
    task_set = MyTaskSet
    

"""
We need somewhere to store the stats.

On  the master node stats will contain the aggregated sum of all content-lengths,
while one the slave nodes this will be the sum of the content-lengths since the 
last stats report was sent to the master
"""
stats = {"content-length":0}

def on_request_success(request_type, name, response_time, response_length):
    """
    Event handler that get triggered on every successful request
    """
    stats["content-length"] += response_length

def on_report_to_master(client_id, data):
    """
    This event is triggered on the slave instances every time a stats report is
    to be sent to the locust master. It will allow us to add our extra content-length
    data to the dict that is being sent, and then we clear the local stats in the slave.
    """
    data["content-length"] = stats["content-length"]
    stats["content-length"] = 0

def on_slave_report(client_id, data):
    """
    This event is triggered on the master instance when a new stats report arrives
    from a slave. Here we just add the content-length to the master's aggregated
    stats dict.
    """
    stats["content-length"] += data["content-length"]

# Hook up the event listeners
events.request_success += on_request_success
events.report_to_master += on_report_to_master
events.slave_report += on_slave_report

@web.app.route("/content-length")
def total_content_length():
    """
    Add a route to the Locust web app, where we can see the total content-length
    """
    return "Total content-length recieved: %i" % stats["content-length"]

########NEW FILE########
__FILENAME__ = cache
from time import time

def memoize(timeout, dynamic_timeout=False):
    """
    Memoization decorator with support for timeout.
    
    If dynamic_timeout is set, the cache timeout is doubled if the cached function 
    takes longer time to run than the timeout time
    """
    cache = {"timeout":timeout}
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time()
            if (not "time" in cache) or (start - cache["time"] > cache["timeout"]):
                # cache miss
                cache["result"] = func(*args, **kwargs)
                cache["time"] = time()
                if dynamic_timeout and cache["time"] - start > cache["timeout"]:
                    cache["timeout"] *= 2
            return cache["result"]
        
        def clear_cache():
            if "time" in cache:
                del cache["time"]
            if "result" in cache:
                del cache["result"]
        
        wrapper.clear_cache = clear_cache
        return wrapper
    return decorator


########NEW FILE########
__FILENAME__ = clients
import re
import time
from urlparse import urlparse, urlunparse

import requests
from requests import Response, Request
from requests.auth import HTTPBasicAuth
from requests.exceptions import (RequestException, MissingSchema,
    InvalidSchema, InvalidURL)

import events
from exception import CatchResponseError, ResponseError

absolute_http_url_regexp = re.compile(r"^https?://", re.I)


def timedelta_to_ms(td):
    "python 2.7 has a total_seconds method for timedelta objects. This is here for py<2.7 compat."
    return int((td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**3) 


class LocustResponse(Response):

    def raise_for_status(self):
        if hasattr(self, 'error') and self.error:
            raise self.error
        Response.raise_for_status(self)


class HttpSession(requests.Session):
    """
    Class for performing web requests and holding (session-) cookies between requests (in order
    to be able to log in and out of websites). Each request is logged so that locust can display 
    statistics.
    
    This is a slightly extended version of `python-request <http://python-requests.org>`_'s
    :py:class:`requests.Session` class and mostly this class works exactly the same. However 
    the methods for making requests (get, post, delete, put, head, options, patch, request) 
    can now take a *url* argument that's only the path part of the URL, in which case the host 
    part of the URL will be prepended with the HttpSession.base_url which is normally inherited
    from a Locust class' host property.
    
    Each of the methods for making requests also takes two additional optional arguments which 
    are Locust specific and doesn't exist in python-requests. These are:
    
    :param name: (optional) An argument that can be specified to use as label in Locust's statistics instead of the URL path. 
                 This can be used to group different URL's that are requested into a single entry in Locust's statistics.
    :param catch_response: (optional) Boolean argument that, if set, can be used to make a request return a context manager 
                           to work as argument to a with statement. This will allow the request to be marked as a fail based on the content of the 
                           response, even if the response code is ok (2xx). The opposite also works, one can use catch_response to catch a request
                           and then mark it as successful even if the response code was not (i.e 500 or 404).
    """
    def __init__(self, base_url, *args, **kwargs):
        requests.Session.__init__(self, *args, **kwargs)

        self.base_url = base_url
        
        # Check for basic authentication
        parsed_url = urlparse(self.base_url)
        if parsed_url.username and parsed_url.password:
            netloc = parsed_url.hostname
            if parsed_url.port:
                netloc += ":%d" % parsed_url.port
            
            # remove username and password from the base_url
            self.base_url = urlunparse((parsed_url.scheme, netloc, parsed_url.path, parsed_url.params, parsed_url.query, parsed_url.fragment))
            # configure requests to use basic auth
            self.auth = HTTPBasicAuth(parsed_url.username, parsed_url.password)
    
    def _build_url(self, path):
        """ prepend url with hostname unless it's already an absolute URL """
        if absolute_http_url_regexp.match(path):
            return path
        else:
            return "%s%s" % (self.base_url, path)
    
    def request(self, method, url, name=None, catch_response=False, **kwargs):
        """
        Constructs and sends a :py:class:`requests.Request`.
        Returns :py:class:`requests.Response` object.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param name: (optional) An argument that can be specified to use as label in Locust's statistics instead of the URL path. 
          This can be used to group different URL's that are requested into a single entry in Locust's statistics.
        :param catch_response: (optional) Boolean argument that, if set, can be used to make a request return a context manager 
          to work as argument to a with statement. This will allow the request to be marked as a fail based on the content of the 
          response, even if the response code is ok (2xx). The opposite also works, one can use catch_response to catch a request
          and then mark it as successful even if the response code was not (i.e 500 or 404).
        :param params: (optional) Dictionary or bytes to be sent in the query string for the :class:`Request`.
        :param data: (optional) Dictionary or bytes to send in the body of the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
        :param files: (optional) Dictionary of 'filename': file-like-objects for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) Float describing the timeout of the request.
        :param allow_redirects: (optional) Boolean. Set to True by default.
        :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
        :param return_response: (optional) If False, an un-sent Request object will returned.
        :param config: (optional) A configuration dictionary. See ``request.defaults`` for allowed keys and their default values.
        :param stream: (optional) whether to immediately download the response content. Defaults to ``False``.
        :param verify: (optional) if ``True``, the SSL cert will be verified. A CA_BUNDLE path can also be provided.
        :param cert: (optional) if String, path to ssl client cert file (.pem). If Tuple, ('cert', 'key') pair.
        """
        
        # prepend url with hostname unless it's already an absolute URL
        url = self._build_url(url)
        
        # store meta data that is used when reporting the request to locust's statistics
        request_meta = {}
        
        # set up pre_request hook for attaching meta data to the request object
        request_meta["start_time"] = time.time()
        
        response = self._send_request_safe_mode(method, url, **kwargs)
        
        request_meta["method"] = response.request.method
        request_meta["name"] = name or response.request.path_url 

        # record the consumed time
        request_meta["response_time"] = timedelta_to_ms(response.elapsed) 
        
        # get the length of the content, but if the argument stream is set to True, we take
        # the size from the content-length header, in order to not trigger fetching of the body
        if kwargs.get("stream", False):
            request_meta["content_size"] = int(response.headers.get("content-length") or 0)
        else:
            request_meta["content_size"] = len(response.content or "")
        
        if catch_response:
            response.locust_request_meta = request_meta
            return ResponseContextManager(response)
        else:
            try:
                response.raise_for_status()
            except RequestException as e:
                events.request_failure.fire(
                    request_type=request_meta["method"], 
                    name=request_meta["name"], 
                    response_time=request_meta["response_time"], 
                    exception=e, 
                )
            else:
                events.request_success.fire(
                    request_type=request_meta["method"],
                    name=request_meta["name"],
                    response_time=request_meta["response_time"],
                    response_length=request_meta["content_size"],
                )
            return response
    
    def _send_request_safe_mode(self, method, url, **kwargs):
        """
        Send an HTTP request, and catch any exception that might occur due to connection problems.
        
        Safe mode has been removed from requests 1.x.
        """
        try:
            return requests.Session.request(self, method, url, **kwargs)
        except (MissingSchema, InvalidSchema, InvalidURL):
            raise
        except RequestException as e:
            r = LocustResponse()
            r.error = e
            r.status_code = 0  # with this status_code, content returns None
            r.request = Request(method, url).prepare() 
            return r


class ResponseContextManager(LocustResponse):
    """
    A Response class that also acts as a context manager that provides the ability to manually 
    control if an HTTP request should be marked as successful or a failure in Locust's statistics
    
    This class is a subclass of :py:class:`Response <requests.Response>` with two additional 
    methods: :py:meth:`success <locust.clients.ResponseContextManager.success>` and 
    :py:meth:`failure <locust.clients.ResponseContextManager.failure>`.
    """
    
    _is_reported = False
    
    def __init__(self, response):
        # copy data from response to this object
        self.__dict__ = response.__dict__
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc, value, traceback):
        if self._is_reported:
            # if the user has already manually marked this response as failure or success
            # we can ignore the default haviour of letting the response code determine the outcome
            return exc is None
        
        if exc:
            if isinstance(value, ResponseError):
                self.failure(value)
            else:
                return False
        else:
            try:
                self.raise_for_status()
            except requests.exceptions.RequestException as e:
                self.failure(e)
            else:
                self.success()
        return True
    
    def success(self):
        """
        Report the response as successful
        
        Example::
        
            with self.client.get("/does/not/exist", catch_response=True) as response:
                if response.status_code == 404:
                    response.success()
        """
        events.request_success.fire(
            request_type=self.locust_request_meta["method"],
            name=self.locust_request_meta["name"],
            response_time=self.locust_request_meta["response_time"],
            response_length=self.locust_request_meta["content_size"],
        )
        self._is_reported = True
    
    def failure(self, exc):
        """
        Report the response as a failure.
        
        exc can be either a python exception, or a string in which case it will
        be wrapped inside a CatchResponseError. 
        
        Example::
        
            with self.client.get("/", catch_response=True) as response:
                if response.content == "":
                    response.failure("No data")
        """
        if isinstance(exc, basestring):
            exc = CatchResponseError(exc)
        
        events.request_failure.fire(
            request_type=self.locust_request_meta["method"],
            name=self.locust_request_meta["name"],
            response_time=self.locust_request_meta["response_time"],
            exception=exc,
        )
        self._is_reported = True

########NEW FILE########
__FILENAME__ = core
import gevent
from gevent import monkey, GreenletExit

monkey.patch_all(thread=False)

from time import time
import sys
import random
import warnings
import traceback
import logging

from clients import HttpSession
import events

from exception import LocustError, InterruptTaskSet, RescheduleTask, RescheduleTaskImmediately, StopLocust

logger = logging.getLogger(__name__)


def task(weight=1):
    """
    Used as a convenience decorator to be able to declare tasks for a TaskSet 
    inline in the class. Example::
    
        class ForumPage(TaskSet):
            @task(100)
            def read_thread(self):
                pass
            
            @task(7)
            def create_thread(self):
                pass
    """
    
    def decorator_func(func):
        func.locust_task_weight = weight
        return func
    
    """
    Check if task was used without parentheses (not called), like this::
    
        @task
        def my_task()
            pass
    """
    if callable(weight):
        func = weight
        weight = 1
        return decorator_func(func)
    else:
        return decorator_func


class NoClientWarningRaiser(object):
    """
    The purpose of this class is to emit a sensible error message for old test scripts that 
    inherits from Locust, and expects there to be an HTTP client under the client attribute.
    """
    def __getattr__(self, _):
        raise LocustError("No client instantiated. Did you intend to inherit from HttpLocust?")


class Locust(object):
    """
    Represents a "user" which is to be hatched and attack the system that is to be load tested.
    
    The behaviour of this user is defined by the task_set attribute, which should point to a 
    :py:class:`TaskSet <locust.core.TaskSet>` class.
    
    This class should usually be subclassed by a class that defines some kind of client. For 
    example when load testing an HTTP system, you probably want to use the 
    :py:class:`HttpLocust <locust.core.HttpLocust>` class.
    """
    
    host = None
    """Base hostname to swarm. i.e: http://127.0.0.1:1234"""
    
    min_wait = 1000
    """Minimum waiting time between the execution of locust tasks"""
    
    max_wait = 1000
    """Maximum waiting time between the execution of locust tasks"""
    
    task_set = None
    """TaskSet class that defines the execution behaviour of this locust"""
    
    stop_timeout = None
    """Number of seconds after which the Locust will die. If None it won't timeout."""

    weight = 10
    """Probability of locust being chosen. The higher the weight, the greater is the chance of it being chosen."""
        
    client = NoClientWarningRaiser()
    _catch_exceptions = True
    
    def __init__(self):
        super(Locust, self).__init__()
    
    def run(self):
        try:
            self.task_set(self).run()
        except StopLocust:
            pass
        except (RescheduleTask, RescheduleTaskImmediately) as e:
            raise LocustError, LocustError("A task inside a Locust class' main TaskSet (`%s.task_set` of type `%s`) seems to have called interrupt() or raised an InterruptTaskSet exception. The interrupt() function is used to hand over execution to a parent TaskSet, and should never be called in the main TaskSet which a Locust class' task_set attribute points to." % (type(self).__name__, self.task_set.__name__)), sys.exc_info()[2]


class HttpLocust(Locust):
    """
    Represents an HTTP "user" which is to be hatched and attack the system that is to be load tested.
    
    The behaviour of this user is defined by the task_set attribute, which should point to a 
    :py:class:`TaskSet <locust.core.TaskSet>` class.
    
    This class creates a *client* attribute on instantiation which is an HTTP client with support 
    for keeping a user session between requests.
    """
    
    client = None
    """
    Instance of HttpSession that is created upon instantiation of Locust. 
    The client support cookies, and therefore keeps the session between HTTP requests.
    """
    
    def __init__(self):
        super(HttpLocust, self).__init__()
        if self.host is None:
            raise LocustError("You must specify the base host. Either in the host attribute in the Locust class, or on the command line using the --host option.")
        
        self.client = HttpSession(base_url=self.host)


class TaskSetMeta(type):
    """
    Meta class for the main Locust class. It's used to allow Locust classes to specify task execution 
    ratio using an {task:int} dict, or a [(task0,int), ..., (taskN,int)] list.
    """
    
    def __new__(mcs, classname, bases, classDict):
        new_tasks = []
        for base in bases:
            if hasattr(base, "tasks") and base.tasks:
                new_tasks += base.tasks
        
        if "tasks" in classDict and classDict["tasks"] is not None:
            tasks = classDict["tasks"]
            if isinstance(tasks, dict):
                tasks = list(tasks.iteritems())
            
            for task in tasks:
                if isinstance(task, tuple):
                    task, count = task
                    for i in xrange(0, count):
                        new_tasks.append(task)
                else:
                    new_tasks.append(task)
        
        for item in classDict.itervalues():
            if hasattr(item, "locust_task_weight"):
                for i in xrange(0, item.locust_task_weight):
                    new_tasks.append(item)
        
        classDict["tasks"] = new_tasks
        
        return type.__new__(mcs, classname, bases, classDict)

class TaskSet(object):
    """
    Class defining a set of tasks that a Locust user will execute. 
    
    When a TaskSet starts running, it will pick a task from the *tasks* attribute, 
    execute it, call it's wait function which will sleep a random number between
    *min_wait* and *max_wait* milliseconds. It will then schedule another task for 
    execution and so on.
    
    TaskTests can be nested, which means that a TaskSet's *tasks* attribute can contain 
    another TaskSet. If the nested TaskSet it scheduled to be executed, it will be 
    instantiated and called from the current executing TaskSet. Execution in the the
    currently running TaskSet will then be handed over to the nested TaskSet which will 
    continue to run until it throws an InterruptTaskSet exception, which is done when 
    :py:meth:`TaskSet.interrupt() <locust.core.TaskSet.interrupt>` is called. (execution 
    will then continue in the first TaskSet).
    """
    
    tasks = []
    """
    List with python callables that represents a locust user task.

    If tasks is a list, the task to be performed will be picked randomly.

    If tasks is a *(callable,int)* list of two-tuples, or a  {callable:int} dict, 
    the task to be performed will be picked randomly, but each task will be weighted 
    according to it's corresponding int value. So in the following case *ThreadPage* will 
    be fifteen times more likely to be picked than *write_post*::

        class ForumPage(TaskSet):
            tasks = {ThreadPage:15, write_post:1}
    """
    
    min_wait = None
    """
    Minimum waiting time between the execution of locust tasks. Can be used to override 
    the min_wait defined in the root Locust class, which will be used if not set on the 
    TaskSet.
    """
    
    max_wait = None
    """
    Maximum waiting time between the execution of locust tasks. Can be used to override 
    the max_wait defined in the root Locust class, which will be used if not set on the 
    TaskSet.
    """
    
    locust = None
    """Will refer to the root Locust class instance when the TaskSet has been instantiated"""

    parent = None
    """
    Will refer to the parent TaskSet, or Locust, class instance when the TaskSet has been 
    instantiated. Useful for nested TaskSet classes.
    """

    __metaclass__ = TaskSetMeta    
    
    def __init__(self, parent):
        self._task_queue = []
        self._time_start = time()
        
        if isinstance(parent, TaskSet):
            self.locust = parent.locust
        elif isinstance(parent, Locust):
            self.locust = parent
        else:
            raise LocustError("TaskSet should be called with Locust instance or TaskSet instance as first argument")

        self.parent = parent
        
        # if this class doesn't have a min_wait or max_wait defined, copy it from Locust
        if not self.min_wait:
            self.min_wait = self.locust.min_wait
        if not self.max_wait:
            self.max_wait = self.locust.max_wait

    def run(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        
        try:
            if hasattr(self, "on_start"):
                self.on_start()
        except InterruptTaskSet as e:
            if e.reschedule:
                raise RescheduleTaskImmediately, e, sys.exc_info()[2]
            else:
                raise RescheduleTask, e, sys.exc_info()[2]
        
        while (True):
            try:
                if self.locust.stop_timeout is not None and time() - self._time_start > self.locust.stop_timeout:
                    return
        
                if not self._task_queue:
                    self.schedule_task(self.get_next_task())
                
                try:
                    self.execute_next_task()
                except RescheduleTaskImmediately:
                    pass
                except RescheduleTask:
                    self.wait()
                else:
                    self.wait()
            except InterruptTaskSet as e:
                if e.reschedule:
                    raise RescheduleTaskImmediately, e, sys.exc_info()[2]
                else:
                    raise RescheduleTask, e, sys.exc_info()[2]
            except StopLocust:
                raise
            except GreenletExit:
                raise
            except Exception as e:
                events.locust_error.fire(locust_instance=self, exception=e, tb=sys.exc_info()[2])
                if self.locust._catch_exceptions:
                    sys.stderr.write("\n" + traceback.format_exc())
                    self.wait()
                else:
                    raise
    
    def execute_next_task(self):
        task = self._task_queue.pop(0)
        self.execute_task(task["callable"], *task["args"], **task["kwargs"])
    
    def execute_task(self, task, *args, **kwargs):
        # check if the function is a method bound to the current locust, and if so, don't pass self as first argument
        if hasattr(task, "im_self") and task.__self__ == self:
            # task is a bound method on self
            task(*args, **kwargs)
        elif hasattr(task, "tasks") and issubclass(task, TaskSet):
            # task is another (nested) TaskSet class
            task(self).run(*args, **kwargs)
        else:
            # task is a function
            task(self, *args, **kwargs)
    
    def schedule_task(self, task_callable, args=None, kwargs=None, first=False):
        """
        Add a task to the Locust's task execution queue.
        
        *Arguments*:
        
        * task_callable: Locust task to schedule
        * args: Arguments that will be passed to the task callable
        * kwargs: Dict of keyword arguments that will be passed to the task callable.
        * first: Optional keyword argument. If True, the task will be put first in the queue.
        """
        task = {"callable":task_callable, "args":args or [], "kwargs":kwargs or {}}
        if first:
            self._task_queue.insert(0, task)
        else:
            self._task_queue.append(task)
    
    def get_next_task(self):
        return random.choice(self.tasks)
    
    def wait(self):
        millis = random.randint(self.min_wait, self.max_wait)
        seconds = millis / 1000.0
        self._sleep(seconds)

    def _sleep(self, seconds):
        gevent.sleep(seconds)
    
    def interrupt(self, reschedule=True):
        """
        Interrupt the TaskSet and hand over execution control back to the parent TaskSet.
        
        If *reschedule* is True (default), the parent Locust will immediately re-schedule,
        and execute, a new task
        
        This method should not be called by the root TaskSet (the one that is immediately, 
        attached to the Locust class' *task_set* attribute), but rather in nested TaskSet
        classes further down the hierarchy.
        """
        raise InterruptTaskSet(reschedule)
    
    @property
    def client(self):
        """
        Reference to the :py:attr:`client <locust.core.Locust.client>` attribute of the root 
        Locust instance.
        """
        return self.locust.client


########NEW FILE########
__FILENAME__ = events
class EventHook(object):
    """
    Simple event class used to provide hooks for different types of events in Locust.

    Here's how to use the EventHook class::

        my_event = EventHook()
        def on_my_event(a, b, **kw):
            print "Event was fired with arguments: %s, %s" % (a, b)
        my_event += on_my_event
        my_event.fire(a="foo", b="bar")
    """

    def __init__(self):
        self._handlers = []

    def __iadd__(self, handler):
        self._handlers.append(handler)
        return self

    def __isub__(self, handler):
        self._handlers.remove(handler)
        return self

    def fire(self, **kwargs):
        for handler in self._handlers:
            handler(**kwargs)

request_success = EventHook()
"""
*request_success* is fired when a request is completed successfully.

Listeners should take the following arguments:

* *request_type*: Request type method used
* *name*: Path to the URL that was called (or override name if it was used in the call to the client)
* *response_time*: Response time in milliseconds
* *response_length*: Content-length of the response
"""

request_failure = EventHook()
"""
*request_failure* is fired when a request fails

Event is fired with the following arguments:

* *request_type*: Request type method used
* *name*: Path to the URL that was called (or override name if it was used in the call to the client)
* *response_time*: Time in milliseconds until exception was thrown
* *exception*: Exception instance that was thrown
"""

locust_error = EventHook()
"""
*locust_error* is fired when an exception occurs inside the execution of a Locust class.

Event is fired with the following arguments:

* *locust_instance*: Locust class instance where the exception occurred
* *exception*: Exception that was thrown
* *tb*: Traceback object (from sys.exc_info()[2])
"""

report_to_master = EventHook()
"""
*report_to_master* is used when Locust is running in --slave mode. It can be used to attach 
data to the dicts that are regularly sent to the master. It's fired regularly when a report 
is to be sent to the master server.

Note that the keys "stats" and "errors" are used by Locust and shouldn't be overridden.

Event is fired with the following arguments:

* *client_id*: The client id of the running locust process.
* *data*: Data dict that can be modified in order to attach data that should be sent to the master.
"""

slave_report = EventHook()
"""
*slave_report* is used when Locust is running in --master mode and is fired when the master 
server receives a report from a Locust slave server.

This event can be used to aggregate data from the locust slave servers.

Event is fired with following arguments:

* *client_id*: Client id of the reporting locust slave
* *data*: Data dict with the data from the slave node
"""

hatch_complete = EventHook()
"""
*hatch_complete* is fired when all locust users has been spawned.

Event is fire with the following arguments:

* *user_count*: Number of users that was hatched
"""

quitting = EventHook()
"""
*quitting* is fired when the locust process in exiting
"""

########NEW FILE########
__FILENAME__ = exception
class LocustError(Exception):
    pass

class ResponseError(Exception):
    pass

class CatchResponseError(Exception):
    pass

class InterruptTaskSet(Exception):
    """
    Exception that will interrupt a Locust when thrown inside a task
    """
    
    def __init__(self, reschedule=True):
        """
        If *reschedule* is True and the InterruptTaskSet is raised inside a nested TaskSet,
        the parent TaskSet whould immediately reschedule another task.
        """
        self.reschedule = reschedule

class StopLocust(Exception):
    pass

class RescheduleTask(Exception):
    """
    When raised in a task it's equivalent of a return statement.
    
    Used internally by TaskSet. When raised within the task control flow of a TaskSet, 
    but not inside a task, the execution should be handed over to the parent TaskSet.
    """

class RescheduleTaskImmediately(Exception):
    """
    When raised in a Locust task, another locust task will be rescheduled immediately
    """

########NEW FILE########
__FILENAME__ = inspectlocust
import inspect

from core import Locust, TaskSet
from log import console_logger

def print_task_ratio(locusts, total=False, level=0, parent_ratio=1.0):
    d = get_task_ratio_dict(locusts, total=total, parent_ratio=parent_ratio)
    _print_task_ratio(d)

def _print_task_ratio(x, level=0):
    for k, v in x.iteritems():
        padding = 2*" "*level
        ratio = v.get('ratio', 1)
        console_logger.info(" %-10s %-50s" % (padding + "%-6.1f" % (ratio*100), padding + k))
        if 'tasks' in v:
            _print_task_ratio(v['tasks'], level + 1)


def get_task_ratio_dict(tasks, total=False, parent_ratio=1.0):
    """
    Return a dict containing task execution ratio info
    """
    if hasattr(tasks[0], 'weight'):
        divisor = sum(t.weight for t in tasks)
    else:
        divisor = len(tasks) / parent_ratio
    ratio = {}
    for task in tasks:
        ratio.setdefault(task, 0)
        ratio[task] += task.weight if hasattr(task, 'weight') else 1

    # get percentage
    ratio_percent = dict((k, float(v) / divisor) for k, v in ratio.iteritems())

    task_dict = {}
    for locust, ratio in ratio_percent.iteritems():
        d = {"ratio":ratio}
        if inspect.isclass(locust):
            if issubclass(locust, Locust):
                T = locust.task_set.tasks
            elif issubclass(locust, TaskSet):
                T = locust.tasks
            if total:
                d["tasks"] = get_task_ratio_dict(T, total, ratio)
            else:
                d["tasks"] = get_task_ratio_dict(T, total)
        
        task_dict[locust.__name__] = d

    return task_dict
########NEW FILE########
__FILENAME__ = log
import logging
import sys
import socket

host = socket.gethostname()

def setup_logging(loglevel, logfile):
    numeric_level = getattr(logging, loglevel.upper(), None)
    if numeric_level is None:
        raise ValueError("Invalid log level: %s" % loglevel)
    
    log_format = "[%(asctime)s] {0}/%(levelname)s/%(name)s: %(message)s".format(host)
    logging.basicConfig(level=numeric_level, filename=logfile, format=log_format)
    
    sys.stderr = StdErrWrapper()
    sys.stdout = StdOutWrapper()

stdout_logger = logging.getLogger("stdout")
stderr_logger = logging.getLogger("stderr")

class StdOutWrapper(object):
    """
    Wrapper for stdout
    """
    def write(self, s):
        stdout_logger.info(s.strip())

class StdErrWrapper(object):
    """
    Wrapper for stderr
    """
    def write(self, s):
        stderr_logger.error(s.strip())

# set up logger for the statistics tables
console_logger = logging.getLogger("console_logger")
# create console handler
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
# formatter that doesn't include anything but the message
sh.setFormatter(logging.Formatter('%(message)s'))
console_logger.addHandler(sh)
console_logger.propagate = False

# configure python-requests log level
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

########NEW FILE########
__FILENAME__ = main
import locust
import runners

import gevent
import sys
import os
import signal
import inspect
import logging
import socket
from optparse import OptionParser

import web
from log import setup_logging, console_logger
from stats import stats_printer, print_percentile_stats, print_error_report, print_stats
from inspectlocust import print_task_ratio, get_task_ratio_dict
from core import Locust, HttpLocust
from runners import MasterLocustRunner, SlaveLocustRunner, LocalLocustRunner
import events

_internals = [Locust, HttpLocust]
version = locust.version

def parse_options():
    """
    Handle command-line options with optparse.OptionParser.

    Return list of arguments, largely for use in `parse_arguments`.
    """

    # Initialize
    parser = OptionParser(usage="locust [options] [LocustClass [LocustClass2 ... ]]")

    parser.add_option(
        '-H', '--host',
        dest="host",
        default=None,
        help="Host to load test in the following format: http://10.21.32.33"
    )

    parser.add_option(
        '--web-host',
        dest="web_host",
        default="",
        help="Host to bind the web interface to. Defaults to '' (all interfaces)"
    )
    
    parser.add_option(
        '-P', '--port', '--web-port',
        type="int",
        dest="port",
        default=8089,
        help="Port on which to run web host"
    )
    
    parser.add_option(
        '-f', '--locustfile',
        dest='locustfile',
        default='locustfile',
        help="Python module file to import, e.g. '../other.py'. Default: locustfile"
    )

    # if locust should be run in distributed mode as master
    parser.add_option(
        '--master',
        action='store_true',
        dest='master',
        default=False,
        help="Set locust to run in distributed mode with this process as master"
    )

    # if locust should be run in distributed mode as slave
    parser.add_option(
        '--slave',
        action='store_true',
        dest='slave',
        default=False,
        help="Set locust to run in distributed mode with this process as slave"
    )
    
    # master host options
    parser.add_option(
        '--master-host',
        action='store',
        type='str',
        dest='master_host',
        default="127.0.0.1",
        help="Host or IP address of locust master for distributed load testing. Only used when running with --slave. Defaults to 127.0.0.1."
    )
    
    parser.add_option(
        '--master-port',
        action='store',
        type='int',
        dest='master_port',
        default=5557,
        help="The port to connect to that is used by the locust master for distributed load testing. Only used when running with --slave. Defaults to 5557. Note that slaves will also connect to the master node on this port + 1."
    )

    parser.add_option(
        '--master-bind-host',
        action='store',
        type='str',
        dest='master_bind_host',
        default="*",
        help="Interfaces (hostname, ip) that locust master should bind to. Only used when running with --master. Defaults to * (all available interfaces)."
    )
    
    parser.add_option(
        '--master-bind-port',
        action='store',
        type='int',
        dest='master_bind_port',
        default=5557,
        help="Port that locust master should bind to. Only used when running with --master. Defaults to 5557. Note that Locust will also use this port + 1, so by default the master node will bind to 5557 and 5558."
    )

    # if we should print stats in the console
    parser.add_option(
        '--no-web',
        action='store_true',
        dest='no_web',
        default=False,
        help="Disable the web interface, and instead start running the test immediately. Requires -c and -r to be specified."
    )

    # Number of clients
    parser.add_option(
        '-c', '--clients',
        action='store',
        type='int',
        dest='num_clients',
        default=1,
        help="Number of concurrent clients. Only used together with --no-web"
    )

    # Client hatch rate
    parser.add_option(
        '-r', '--hatch-rate',
        action='store',
        type='float',
        dest='hatch_rate',
        default=1,
        help="The rate per second in which clients are spawned. Only used together with --no-web"
    )
    
    # Number of requests
    parser.add_option(
        '-n', '--num-request',
        action='store',
        type='int',
        dest='num_requests',
        default=None,
        help="Number of requests to perform. Only used together with --no-web"
    )
    
    # log level
    parser.add_option(
        '--loglevel', '-L',
        action='store',
        type='str',
        dest='loglevel',
        default='INFO',
        help="Choose between DEBUG/INFO/WARNING/ERROR/CRITICAL. Default is INFO.",
    )
    
    # log file
    parser.add_option(
        '--logfile',
        action='store',
        type='str',
        dest='logfile',
        default=None,
        help="Path to log file. If not set, log will go to stdout/stderr",
    )
    
    # if we should print stats in the console
    parser.add_option(
        '--print-stats',
        action='store_true',
        dest='print_stats',
        default=False,
        help="Print stats in the console"
    )

    # only print summary stats
    parser.add_option(
       '--only-summary',
       action='store_true',
       dest='only_summary',
       default=False,
       help='Only print the summary stats'
    )
    
    # List locust commands found in loaded locust files/source files
    parser.add_option(
        '-l', '--list',
        action='store_true',
        dest='list_commands',
        default=False,
        help="Show list of possible locust classes and exit"
    )
    
    # Display ratio table of all tasks
    parser.add_option(
        '--show-task-ratio',
        action='store_true',
        dest='show_task_ratio',
        default=False,
        help="print table of the locust classes' task execution ratio"
    )
    # Display ratio table of all tasks in JSON format
    parser.add_option(
        '--show-task-ratio-json',
        action='store_true',
        dest='show_task_ratio_json',
        default=False,
        help="print json data of the locust classes' task execution ratio"
    )
    
    # Version number (optparse gives you --version but we have to do it
    # ourselves to get -V too. sigh)
    parser.add_option(
        '-V', '--version',
        action='store_true',
        dest='show_version',
        default=False,
        help="show program's version number and exit"
    )

    # Finalize
    # Return three-tuple of parser + the output from parse_args (opt obj, args)
    opts, args = parser.parse_args()
    return parser, opts, args


def _is_package(path):
    """
    Is the given path a Python package?
    """
    return (
        os.path.isdir(path)
        and os.path.exists(os.path.join(path, '__init__.py'))
    )


def find_locustfile(locustfile):
    """
    Attempt to locate a locustfile, either explicitly or by searching parent dirs.
    """
    # Obtain env value
    names = [locustfile]
    # Create .py version if necessary
    if not names[0].endswith('.py'):
        names += [names[0] + '.py']
    # Does the name contain path elements?
    if os.path.dirname(names[0]):
        # If so, expand home-directory markers and test for existence
        for name in names:
            expanded = os.path.expanduser(name)
            if os.path.exists(expanded):
                if name.endswith('.py') or _is_package(expanded):
                    return os.path.abspath(expanded)
    else:
        # Otherwise, start in cwd and work downwards towards filesystem root
        path = '.'
        # Stop before falling off root of filesystem (should be platform
        # agnostic)
        while os.path.split(os.path.abspath(path))[1]:
            for name in names:
                joined = os.path.join(path, name)
                if os.path.exists(joined):
                    if name.endswith('.py') or _is_package(joined):
                        return os.path.abspath(joined)
            path = os.path.join('..', path)
    # Implicit 'return None' if nothing was found


def is_locust(tup):
    """
    Takes (name, object) tuple, returns True if it's a public Locust subclass.
    """
    name, item = tup
    return bool(
        inspect.isclass(item)
        and issubclass(item, Locust)
        and hasattr(item, "task_set")
        and getattr(item, "task_set")
        and not name.startswith('_')
    )


def load_locustfile(path):
    """
    Import given locustfile path and return (docstring, callables).

    Specifically, the locustfile's ``__doc__`` attribute (a string) and a
    dictionary of ``{'name': callable}`` containing all callables which pass
    the "is a Locust" test.
    """
    # Get directory and locustfile name
    directory, locustfile = os.path.split(path)
    # If the directory isn't in the PYTHONPATH, add it so our import will work
    added_to_path = False
    index = None
    if directory not in sys.path:
        sys.path.insert(0, directory)
        added_to_path = True
    # If the directory IS in the PYTHONPATH, move it to the front temporarily,
    # otherwise other locustfiles -- like Locusts's own -- may scoop the intended
    # one.
    else:
        i = sys.path.index(directory)
        if i != 0:
            # Store index for later restoration
            index = i
            # Add to front, then remove from original position
            sys.path.insert(0, directory)
            del sys.path[i + 1]
    # Perform the import (trimming off the .py)
    imported = __import__(os.path.splitext(locustfile)[0])
    # Remove directory from path if we added it ourselves (just to be neat)
    if added_to_path:
        del sys.path[0]
    # Put back in original index if we moved it
    if index is not None:
        sys.path.insert(index + 1, directory)
        del sys.path[0]
    # Return our two-tuple
    locusts = dict(filter(is_locust, vars(imported).items()))
    return imported.__doc__, locusts

def main():
    parser, options, arguments = parse_options()

    # setup logging
    setup_logging(options.loglevel, options.logfile)
    logger = logging.getLogger(__name__)
    
    if options.show_version:
        print "Locust %s" % (version,)
        sys.exit(0)

    locustfile = find_locustfile(options.locustfile)
    if not locustfile:
        logger.error("Could not find any locustfile! See --help for available options.")
        sys.exit(1)

    docstring, locusts = load_locustfile(locustfile)

    if options.list_commands:
        console_logger.info("Available Locusts:")
        for name in locusts:
            console_logger.info("    " + name)
        sys.exit(0)

    if not locusts:
        logger.error("No Locust class found!")
        sys.exit(1)

    # make sure specified Locust exists
    if arguments:
        missing = set(arguments) - set(locusts.keys())
        if missing:
            logger.error("Unknown Locust(s): %s\n" % (", ".join(missing)))
            sys.exit(1)
        else:
            names = set(arguments) & set(locusts.keys())
            locust_classes = [locusts[n] for n in names]
    else:
        locust_classes = locusts.values()
    
    if options.show_task_ratio:
        console_logger.info("\n Task ratio per locust class")
        console_logger.info( "-" * 80)
        print_task_ratio(locust_classes)
        console_logger.info("\n Total task ratio")
        console_logger.info("-" * 80)
        print_task_ratio(locust_classes, total=True)
        sys.exit(0)
    if options.show_task_ratio_json:
        from json import dumps
        task_data = {
            "per_class": get_task_ratio_dict(locust_classes), 
            "total": get_task_ratio_dict(locust_classes, total=True)
        }
        console_logger.info(dumps(task_data))
        sys.exit(0)
    
    # if --master is set, make sure --no-web isn't set
    if options.master and options.no_web:
        logger.error("Locust can not run distributed with the web interface disabled (do not use --no-web and --master together)")
        sys.exit(0)

    if not options.no_web and not options.slave:
        # spawn web greenlet
        logger.info("Starting web monitor at %s:%s" % (options.web_host or "*", options.port))
        main_greenlet = gevent.spawn(web.start, locust_classes, options)
    
    if not options.master and not options.slave:
        runners.locust_runner = LocalLocustRunner(locust_classes, options)
        # spawn client spawning/hatching greenlet
        if options.no_web:
            runners.locust_runner.start_hatching(wait=True)
            main_greenlet = runners.locust_runner.greenlet
    elif options.master:
        runners.locust_runner = MasterLocustRunner(locust_classes, options)
    elif options.slave:
        try:
            runners.locust_runner = SlaveLocustRunner(locust_classes, options)
            main_greenlet = runners.locust_runner.greenlet
        except socket.error, e:
            logger.error("Failed to connect to the Locust master: %s", e)
            sys.exit(-1)
    
    if not options.only_summary and (options.print_stats or (options.no_web and not options.slave)):
        # spawn stats printing greenlet
        gevent.spawn(stats_printer)
    
    def shutdown(code=0):
        """
        Shut down locust by firing quitting event, printing stats and exiting
        """
        logger.info("Shutting down (exit code %s), bye." % code)

        events.quitting.fire()
        print_stats(runners.locust_runner.request_stats)
        print_percentile_stats(runners.locust_runner.request_stats)

        print_error_report()
        sys.exit(code)
    
    # install SIGTERM handler
    def sig_term_handler():
        logger.info("Got SIGTERM signal")
        shutdown(0)
    gevent.signal(signal.SIGTERM, sig_term_handler)
    
    try:
        logger.info("Starting Locust %s" % version)
        main_greenlet.join()
        code = 0
        if len(runners.locust_runner.errors):
            code = 1
        shutdown(code=code)
    except KeyboardInterrupt as e:
        shutdown(0)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = protocol
import msgpack

class Message(object):
    def __init__(self, message_type, data, node_id):
        self.type = message_type
        self.data = data
        self.node_id = node_id
    
    def serialize(self):
        return msgpack.dumps((self.type, self.data, self.node_id))
    
    @classmethod
    def unserialize(cls, data):
        msg = cls(*msgpack.loads(data))
        return msg

########NEW FILE########
__FILENAME__ = socketrpc
import struct
import logging

import gevent
from gevent import socket
from gevent import queue

from locust.exception import LocustError
from .protocol import Message

logger = logging.getLogger(__name__)

def _recv_bytes(sock, bytes):
    data = ""
    while bytes:
        temp = sock.recv(bytes)
        if not temp:
            raise Exception("Connection reset by peer? Received so far: %r" % (data, ))
        bytes -= len(temp)
        data += temp
    return data

def _send_obj(sock, msg):
    data = msg.serialize()
    packed = struct.pack('!i', len(data)) + data
    try:
        sock.sendall(packed)
    except Exception as e:
        try:
            sock.close()
        except:
            pass
        finally:
            raise LocustError("Slave has disconnected")

def _recv_obj(sock):
    d = _recv_bytes(sock, 4)
    bytes, = struct.unpack('!i', d)
    data = _recv_bytes(sock, bytes)
    return Message.unserialize(data)

class Client(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.command_queue = gevent.queue.Queue()
        self.socket = self._connect()

    def _connect(self):
        sock = socket.create_connection((self.host, self.port))
        def handle():
            try:
                while True:
                    self.command_queue.put_nowait(_recv_obj(sock))
            except Exception as e:
                try:
                    sock.close()
                except:
                    pass

        gevent.spawn(handle)
        return sock

    def send(self, event):
        _send_obj(self.socket, event)

    def recv(self):
        return self.command_queue.get()

class Server(object):
    def __init__(self, host, port):
        self.host = "0.0.0.0" if host == "*" else host
        self.port = port
        self.event_queue = gevent.queue.Queue()
        self.command_dispatcher = self._listen()

    def send(self, msg):
        self.command_dispatcher(msg)

    def recv(self):
        return self.event_queue.get()

    def _listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(256)
        self.slave_index = 0
        slaves = []

        def dispatch_command(cmd):

            _send_obj(slaves[self.slave_index], cmd)
            self.slave_index += 1
            if self.slave_index == len(slaves):
                self.slave_index = 0

        def handle_slave(sock):
            try:
                while True:
                    self.event_queue.put_nowait(_recv_obj(sock))
            except Exception as e:
                logger.info("Slave disconnected")
                slaves.remove(sock)
                if self.slave_index == len(slaves) and len(slaves) > 0:
                    self.slave_index -= 1

                try:
                    sock.close()
                except:
                    pass

        def listener():
            while True:
                _socket, _addr = sock.accept()
                logger.info("Slave connected")
                slaves.append(_socket)
                gevent.spawn(lambda: handle_slave(_socket))

        gevent.spawn(listener)
        return dispatch_command

########NEW FILE########
__FILENAME__ = zmqrpc
import zmq.green as zmq
from .protocol import Message

class BaseSocket(object):

    def send(self, msg):
        self.sender.send(msg.serialize())
    
    def recv(self):
        data = self.receiver.recv()
        return Message.unserialize(data)


class Server(BaseSocket):
    def __init__(self, host, port):
        context = zmq.Context()
        self.receiver = context.socket(zmq.PULL)
        self.receiver.bind("tcp://%s:%i" % (host, port))
        
        self.sender = context.socket(zmq.PUSH)
        self.sender.bind("tcp://%s:%i" % (host, port+1))
    

class Client(BaseSocket):
    def __init__(self, host, port):
        context = zmq.Context()
        self.receiver = context.socket(zmq.PULL)
        self.receiver.connect("tcp://%s:%i" % (host, port+1))
        
        self.sender = context.socket(zmq.PUSH)
        self.sender.connect("tcp://%s:%i" % (host, port))

########NEW FILE########
__FILENAME__ = runners
# coding=UTF-8
import socket
import traceback
import warnings
import random
import logging
from time import time
from hashlib import md5

import gevent
from gevent import GreenletExit
from gevent.pool import Group

import events
from stats import global_stats

from rpc import rpc, Message

logger = logging.getLogger(__name__)

# global locust runner singleton
locust_runner = None

STATE_INIT, STATE_HATCHING, STATE_RUNNING, STATE_STOPPED = ["ready", "hatching", "running", "stopped"]
SLAVE_REPORT_INTERVAL = 3.0


class LocustRunner(object):
    def __init__(self, locust_classes, options):
        self.locust_classes = locust_classes
        self.hatch_rate = options.hatch_rate
        self.num_clients = options.num_clients
        self.num_requests = options.num_requests
        self.host = options.host
        self.locusts = Group()
        self.state = STATE_INIT
        self.hatching_greenlet = None
        self.exceptions = {}
        self.stats = global_stats
        
        # register listener that resets stats when hatching is complete
        def on_hatch_complete(user_count):
            self.state = STATE_RUNNING
            logger.info("Resetting stats\n")
            self.stats.reset_all()
        events.hatch_complete += on_hatch_complete

    @property
    def request_stats(self):
        return self.stats.entries
    
    @property
    def errors(self):
        return self.stats.errors
    
    @property
    def user_count(self):
        return len(self.locusts)

    def weight_locusts(self, amount, stop_timeout = None):
        """
        Distributes the amount of locusts for each WebLocust-class according to it's weight
        returns a list "bucket" with the weighted locusts
        """
        bucket = []
        weight_sum = sum((locust.weight for locust in self.locust_classes if locust.task_set))
        for locust in self.locust_classes:
            if not locust.task_set:
                warnings.warn("Notice: Found Locust class (%s) got no task_set. Skipping..." % locust.__name__)
                continue

            if self.host is not None:
                locust.host = self.host
            if stop_timeout is not None:
                locust.stop_timeout = stop_timeout

            # create locusts depending on weight
            percent = locust.weight / float(weight_sum)
            num_locusts = int(round(amount * percent))
            bucket.extend([locust for x in xrange(0, num_locusts)])
        return bucket

    def spawn_locusts(self, spawn_count=None, stop_timeout=None, wait=False):
        if spawn_count is None:
            spawn_count = self.num_clients

        if self.num_requests is not None:
            self.stats.max_requests = self.num_requests

        bucket = self.weight_locusts(spawn_count, stop_timeout)
        spawn_count = len(bucket)
        if self.state == STATE_INIT or self.state == STATE_STOPPED:
            self.state = STATE_HATCHING
            self.num_clients = spawn_count
        else:
            self.num_clients += spawn_count

        logger.info("Hatching and swarming %i clients at the rate %g clients/s..." % (spawn_count, self.hatch_rate))
        occurence_count = dict([(l.__name__, 0) for l in self.locust_classes])
        
        def hatch():
            sleep_time = 1.0 / self.hatch_rate
            while True:
                if not bucket:
                    logger.info("All locusts hatched: %s" % ", ".join(["%s: %d" % (name, count) for name, count in occurence_count.iteritems()]))
                    events.hatch_complete.fire(user_count=self.num_clients)
                    return

                locust = bucket.pop(random.randint(0, len(bucket)-1))
                occurence_count[locust.__name__] += 1
                def start_locust(_):
                    try:
                        locust().run()
                    except GreenletExit:
                        pass
                new_locust = self.locusts.spawn(start_locust, locust)
                if len(self.locusts) % 10 == 0:
                    logger.debug("%i locusts hatched" % len(self.locusts))
                gevent.sleep(sleep_time)
        
        hatch()
        if wait:
            self.locusts.join()
            logger.info("All locusts dead\n")

    def kill_locusts(self, kill_count):
        """
        Kill a kill_count of weighted locusts from the Group() object in self.locusts
        """
        bucket = self.weight_locusts(kill_count)
        kill_count = len(bucket)
        self.num_clients -= kill_count
        logger.info("Killing %i locusts" % kill_count)
        dying = []
        for g in self.locusts:
            for l in bucket:
                if l == g.args[0]:
                    dying.append(g)
                    bucket.remove(l)
                    break
        for g in dying:
            self.locusts.killone(g)
        events.hatch_complete.fire(user_count=self.num_clients)

    def start_hatching(self, locust_count=None, hatch_rate=None, wait=False):
        if self.state != STATE_RUNNING and self.state != STATE_HATCHING:
            self.stats.clear_all()
            self.stats.start_time = time()
            self.exceptions = {}

        # Dynamically changing the locust count
        if self.state != STATE_INIT and self.state != STATE_STOPPED:
            self.state = STATE_HATCHING
            if self.num_clients > locust_count:
                # Kill some locusts
                kill_count = self.num_clients - locust_count
                self.kill_locusts(kill_count)
            elif self.num_clients < locust_count:
                # Spawn some locusts
                if hatch_rate:
                    self.hatch_rate = hatch_rate
                spawn_count = locust_count - self.num_clients
                self.spawn_locusts(spawn_count=spawn_count)
            else:
                events.hatch_complete.fire(user_count=self.num_clients)
        else:
            if hatch_rate:
                self.hatch_rate = hatch_rate
            if locust_count is not None:
                self.spawn_locusts(locust_count, wait=wait)
            else:
                self.spawn_locusts(wait=wait)

    def stop(self):
        # if we are currently hatching locusts we need to kill the hatching greenlet first
        if self.hatching_greenlet and not self.hatching_greenlet.ready():
            self.hatching_greenlet.kill(block=True)
        self.locusts.kill(block=True)
        self.state = STATE_STOPPED

    def log_exception(self, node_id, msg, formatted_tb):
        key = hash(formatted_tb)
        row = self.exceptions.setdefault(key, {"count": 0, "msg": msg, "traceback": formatted_tb, "nodes": set()})
        row["count"] += 1
        row["nodes"].add(node_id)
        self.exceptions[key] = row

class LocalLocustRunner(LocustRunner):
    def __init__(self, locust_classes, options):
        super(LocalLocustRunner, self).__init__(locust_classes, options)

        # register listener thats logs the exception for the local runner
        def on_locust_error(locust_instance, exception, tb):
            formatted_tb = "".join(traceback.format_tb(tb))
            self.log_exception("local", str(exception), formatted_tb)
        events.locust_error += on_locust_error

    def start_hatching(self, locust_count=None, hatch_rate=None, wait=False):
        self.hatching_greenlet = gevent.spawn(lambda: super(LocalLocustRunner, self).start_hatching(locust_count, hatch_rate, wait=wait))
        self.greenlet = self.hatching_greenlet

class DistributedLocustRunner(LocustRunner):
    def __init__(self, locust_classes, options):
        super(DistributedLocustRunner, self).__init__(locust_classes, options)
        self.master_host = options.master_host
        self.master_port = options.master_port
        self.master_bind_host = options.master_bind_host
        self.master_bind_port = options.master_bind_port
    
    def noop(self, *args, **kwargs):
        """ Used to link() greenlets to in order to be compatible with gevent 1.0 """
        pass

class SlaveNode(object):
    def __init__(self, id, state=STATE_INIT):
        self.id = id
        self.state = state
        self.user_count = 0

class MasterLocustRunner(DistributedLocustRunner):
    def __init__(self, *args, **kwargs):
        super(MasterLocustRunner, self).__init__(*args, **kwargs)
        
        class SlaveNodesDict(dict):
            def get_by_state(self, state):
                return [c for c in self.itervalues() if c.state == state]
            
            @property
            def ready(self):
                return self.get_by_state(STATE_INIT)
            
            @property
            def hatching(self):
                return self.get_by_state(STATE_HATCHING)
            
            @property
            def running(self):
                return self.get_by_state(STATE_RUNNING)
        
        self.clients = SlaveNodesDict()
        
        self.client_stats = {}
        self.client_errors = {}
        self._request_stats = {}

        self.server = rpc.Server(self.master_bind_host, self.master_bind_port)
        self.greenlet = Group()
        self.greenlet.spawn(self.client_listener).link_exception(callback=self.noop)
        
        # listener that gathers info on how many locust users the slaves has spawned
        def on_slave_report(client_id, data):
            if client_id not in self.clients:
                logger.info("Discarded report from unrecognized slave %s", client_id)
                return

            self.clients[client_id].user_count = data["user_count"]
        events.slave_report += on_slave_report
        
        # register listener that sends quit message to slave nodes
        def on_quitting():
            self.quit()
        events.quitting += on_quitting
    
    def noop(self, *args, **kwargs):
        pass
    
    @property
    def user_count(self):
        return sum([c.user_count for c in self.clients.itervalues()])
    
    def start_hatching(self, locust_count, hatch_rate):
        num_slaves = len(self.clients.ready) + len(self.clients.running)
        if not num_slaves:
            logger.warning("You are running in distributed mode but have no slave servers connected. "
                           "Please connect slaves prior to swarming.")
            return

        self.num_clients = locust_count
        slave_num_clients = locust_count / (num_slaves or 1)
        slave_hatch_rate = float(hatch_rate) / (num_slaves or 1)
        remaining = locust_count % num_slaves

        logger.info("Sending hatch jobs to %d ready clients", num_slaves)

        if self.state != STATE_RUNNING and self.state != STATE_HATCHING:
            self.stats.clear_all()
            self.exceptions = {}
        
        for client in self.clients.itervalues():
            data = {
                "hatch_rate":slave_hatch_rate,
                "num_clients":slave_num_clients,
                "num_requests": self.num_requests,
                "host":self.host,
                "stop_timeout":None
            }

            if remaining > 0:
                data["num_clients"] += 1
                remaining -= 1

            self.server.send(Message("hatch", data, None))
        
        self.stats.start_time = time()
        self.state = STATE_HATCHING

    def stop(self):
        for client in self.clients.hatching + self.clients.running:
            self.server.send(Message("stop", None, None))
    
    def quit(self):
        for client in self.clients.itervalues():
            self.server.send(Message("quit", None, None))
        self.greenlet.kill(block=True)
    
    def client_listener(self):
        while True:
            msg = self.server.recv()
            if msg.type == "client_ready":
                id = msg.node_id
                self.clients[id] = SlaveNode(id)
                logger.info("Client %r reported as ready. Currently %i clients ready to swarm." % (id, len(self.clients.ready)))
                ## emit a warning if the slave's clock seem to be out of sync with our clock
                #if abs(time() - msg.data["time"]) > 5.0:
                #    warnings.warn("The slave node's clock seem to be out of sync. For the statistics to be correct the different locust servers need to have synchronized clocks.")
            elif msg.type == "client_stopped":
                del self.clients[msg.node_id]
                if len(self.clients.hatching + self.clients.running) == 0:
                    self.state = STATE_STOPPED
                logger.info("Removing %s client from running clients" % (msg.node_id))
            elif msg.type == "stats":
                events.slave_report.fire(client_id=msg.node_id, data=msg.data)
            elif msg.type == "hatching":
                self.clients[msg.node_id].state = STATE_HATCHING
            elif msg.type == "hatch_complete":
                self.clients[msg.node_id].state = STATE_RUNNING
                self.clients[msg.node_id].user_count = msg.data["count"]
                if len(self.clients.hatching) == 0:
                    count = sum(c.user_count for c in self.clients.itervalues())
                    events.hatch_complete.fire(user_count=count)
            elif msg.type == "quit":
                if msg.node_id in self.clients:
                    del self.clients[msg.node_id]
                    logger.info("Client %r quit. Currently %i clients connected." % (msg.node_id, len(self.clients.ready)))
            elif msg.type == "exception":
                self.log_exception(msg.node_id, msg.data["msg"], msg.data["traceback"])

    @property
    def slave_count(self):
        return len(self.clients.ready) + len(self.clients.hatching) + len(self.clients.running)

class SlaveLocustRunner(DistributedLocustRunner):
    def __init__(self, *args, **kwargs):
        super(SlaveLocustRunner, self).__init__(*args, **kwargs)
        self.client_id = socket.gethostname() + "_" + md5(str(time() + random.randint(0,10000))).hexdigest()
        
        self.client = rpc.Client(self.master_host, self.master_port)
        self.greenlet = Group()

        self.greenlet.spawn(self.worker).link_exception(callback=self.noop)
        self.client.send(Message("client_ready", None, self.client_id))
        self.greenlet.spawn(self.stats_reporter).link_exception(callback=self.noop)
        
        # register listener for when all locust users have hatched, and report it to the master node
        def on_hatch_complete(user_count):
            self.client.send(Message("hatch_complete", {"count":user_count}, self.client_id))
        events.hatch_complete += on_hatch_complete
        
        # register listener that adds the current number of spawned locusts to the report that is sent to the master node 
        def on_report_to_master(client_id, data):
            data["user_count"] = self.user_count
        events.report_to_master += on_report_to_master
        
        # register listener that sends quit message to master
        def on_quitting():
            self.client.send(Message("quit", None, self.client_id))
        events.quitting += on_quitting

        # register listener thats sends locust exceptions to master
        def on_locust_error(locust_instance, exception, tb):
            formatted_tb = "".join(traceback.format_tb(tb))
            self.client.send(Message("exception", {"msg" : str(exception), "traceback" : formatted_tb}, self.client_id))
        events.locust_error += on_locust_error

    def noop(self, *args, **kwargs):
        pass

    def worker(self):
        while True:
            msg = self.client.recv()
            if msg.type == "hatch":
                self.client.send(Message("hatching", None, self.client_id))
                job = msg.data
                self.hatch_rate = job["hatch_rate"]
                #self.num_clients = job["num_clients"]
                self.num_requests = job["num_requests"]
                self.host = job["host"]
                self.hatching_greenlet = gevent.spawn(lambda: self.start_hatching(locust_count=job["num_clients"], hatch_rate=job["hatch_rate"]))
            elif msg.type == "stop":
                self.stop()
                self.client.send(Message("client_stopped", None, self.client_id))
                self.client.send(Message("client_ready", None, self.client_id))
            elif msg.type == "quit":
                logger.info("Got quit message from master, shutting down...")
                self.stop()
                self.greenlet.kill(block=True)

    def stats_reporter(self):
        while True:
            data = {}
            events.report_to_master.fire(client_id=self.client_id, data=data)
            try:
                self.client.send(Message("stats", data, self.client_id))
            except:
                logger.error("Connection lost to master server. Aborting...")
                break
            
            gevent.sleep(SLAVE_REPORT_INTERVAL)

########NEW FILE########
__FILENAME__ = stats
import time
import gevent
import hashlib

import events
from exception import StopLocust
from log import console_logger

STATS_NAME_WIDTH = 60

class RequestStatsAdditionError(Exception):
    pass


class RequestStats(object):
    def __init__(self):
        self.entries = {}
        self.errors = {}
        self.num_requests = 0
        self.num_failures = 0
        self.max_requests = None
        self.last_request_timestamp = None
        self.start_time = None
    
    def get(self, name, method):
        """
        Retrieve a StatsEntry instance by name and method
        """
        entry = self.entries.get((name, method))
        if not entry:
            entry = StatsEntry(self, name, method)
            self.entries[(name, method)] = entry
        return entry
    
    def aggregated_stats(self, name="Total", full_request_history=False):
        """
        Returns a StatsEntry which is an aggregate of all stats entries 
        within entries.
        """
        total = StatsEntry(self, name, method=None)
        for r in self.entries.itervalues():
            total.extend(r, full_request_history=full_request_history)
        return total
    
    def reset_all(self):
        """
        Go through all stats entries and reset them to zero
        """
        self.start_time = time.time()
        self.num_requests = 0
        self.num_failures = 0
        for r in self.entries.itervalues():
            r.reset()
    
    def clear_all(self):
        """
        Remove all stats entries and errors
        """
        self.num_requests = 0
        self.num_failures = 0
        self.entries = {}
        self.errors = {}
        self.max_requests = None
        self.last_request_timestamp = None
        self.start_time = None
        

class StatsEntry(object):
    """
    Represents a single stats entry (name and method)
    """
    
    name = None
    """ Name (URL) of this stats entry """
    
    method = None
    """ Method (GET, POST, PUT, etc.) """
    
    num_requests = None
    """ The number of requests made """
    
    num_failures = None
    """ Number of failed request """
    
    total_response_time = None
    """ Total sum of the response times """
    
    min_response_time = None
    """ Minimum response time """
    
    max_response_time = None
    """ Maximum response time """
    
    num_reqs_per_sec = None
    """ A {second => request_count} dict that holds the number of requests made per second """
    
    response_times = None
    """
    A {response_time => count} dict that holds the the response time distribution of all 
    the requests.
    
    The keys (the response time in ms) are rounded to store 1, 2, ... 9, 10, 20. .. 90, 
    100, 200 .. 900, 1000, 2000 ... 9000, in order to save memory.
    
    This dict is used to calculate the median and percentile response times.
    """
    
    total_content_length = None
    """ The sum of the content length of all the requests for this entry """
    
    start_time = None
    """ Time of the first request for this entry """
    
    last_request_timestamp = None
    """ Time of the last request for this entry """
    
    def __init__(self, stats, name, method):
        self.stats = stats
        self.name = name
        self.method = method
        self.reset()
    
    def reset(self):
        self.start_time = time.time()
        self.num_requests = 0
        self.num_failures = 0
        self.total_response_time = 0
        self.response_times = {}
        self.min_response_time = None
        self.max_response_time = 0
        self.last_request_timestamp = int(time.time())
        self.num_reqs_per_sec = {}
        self.total_content_length = 0
    
    def log(self, response_time, content_length):
        self.stats.num_requests += 1
        self.num_requests += 1

        self._log_time_of_request()
        self._log_response_time(response_time)

        # increase total content-length
        self.total_content_length += content_length

    def _log_time_of_request(self):
        t = int(time.time())
        self.num_reqs_per_sec[t] = self.num_reqs_per_sec.setdefault(t, 0) + 1
        self.last_request_timestamp = t
        self.stats.last_request_timestamp = t

    def _log_response_time(self, response_time):
        self.total_response_time += response_time

        if self.min_response_time is None:
            self.min_response_time = response_time

        self.min_response_time = min(self.min_response_time, response_time)
        self.max_response_time = max(self.max_response_time, response_time)

        # to avoid to much data that has to be transfered to the master node when
        # running in distributed mode, we save the response time rounded in a dict
        # so that 147 becomes 150, 3432 becomes 3400 and 58760 becomes 59000
        if response_time < 100:
            rounded_response_time = response_time
        elif response_time < 1000:
            rounded_response_time = int(round(response_time, -1))
        elif response_time < 10000:
            rounded_response_time = int(round(response_time, -2))
        else:
            rounded_response_time = int(round(response_time, -3))

        # increase request count for the rounded key in response time dict
        self.response_times.setdefault(rounded_response_time, 0)
        self.response_times[rounded_response_time] += 1

    def log_error(self, error):
        self.num_failures += 1
        self.stats.num_failures += 1
        key = StatsError.create_key(self.method, self.name, error)
        entry = self.stats.errors.get(key)
        if not entry:
            entry = StatsError(self.method, self.name, error)
            self.stats.errors[key] = entry

        entry.occured()

    @property
    def fail_ratio(self):
        try:
            return float(self.num_failures) / (self.num_requests + self.num_failures)
        except ZeroDivisionError:
            if self.num_failures > 0:
                return 1.0
            else:
                return 0.0

    @property
    def avg_response_time(self):
        try:
            return float(self.total_response_time) / self.num_requests
        except ZeroDivisionError:
            return 0

    @property
    def median_response_time(self):
        if not self.response_times:
            return 0

        return median_from_dict(self.num_requests, self.response_times)

    @property
    def current_rps(self):
        if self.stats.last_request_timestamp is None:
            return 0
        slice_start_time = max(self.stats.last_request_timestamp - 12, int(self.stats.start_time or 0))

        reqs = [self.num_reqs_per_sec.get(t, 0) for t in range(slice_start_time, self.stats.last_request_timestamp-2)]
        return avg(reqs)

    @property
    def total_rps(self):
        if not self.stats.last_request_timestamp or not self.stats.start_time:
            return 0.0

        return self.num_requests / max(self.stats.last_request_timestamp - self.stats.start_time, 1)

    @property
    def avg_content_length(self):
        try:
            return self.total_content_length / self.num_requests
        except ZeroDivisionError:
            return 0
    
    def extend(self, other, full_request_history=False):
        """
        Extend the data fro the current StatsEntry with the stats from another
        StatsEntry instance. 
        
        If full_request_history is False, we'll only care to add the data from 
        the last 20 seconds of other's stats. The reason for this argument is that 
        extend can be used to generate an aggregate of multiple different StatsEntry 
        instances on the fly, in order to get the *total* current RPS, average 
        response time, etc.
        """
        self.last_request_timestamp = max(self.last_request_timestamp, other.last_request_timestamp)
        self.start_time = min(self.start_time, other.start_time)

        self.num_requests = self.num_requests + other.num_requests
        self.num_failures = self.num_failures + other.num_failures
        self.total_response_time = self.total_response_time + other.total_response_time
        self.max_response_time = max(self.max_response_time, other.max_response_time)
        self.min_response_time = min(self.min_response_time, other.min_response_time) or other.min_response_time
        self.total_content_length = self.total_content_length + other.total_content_length

        if full_request_history:
            for key in other.response_times:
                self.response_times[key] = self.response_times.get(key, 0) + other.response_times[key]
            for key in other.num_reqs_per_sec:
                self.num_reqs_per_sec[key] = self.num_reqs_per_sec.get(key, 0) +  other.num_reqs_per_sec[key]
        else:
            # still add the number of reqs per seconds the last 20 seconds
            for i in xrange(other.last_request_timestamp-20, other.last_request_timestamp+1):
                if i in other.num_reqs_per_sec:
                    self.num_reqs_per_sec[i] = self.num_reqs_per_sec.get(i, 0) + other.num_reqs_per_sec[i]
    
    def serialize(self):
        return {
            "name": self.name,
            "method": self.method,
            "last_request_timestamp": self.last_request_timestamp,
            "start_time": self.start_time,
            "num_requests": self.num_requests,
            "num_failures": self.num_failures,
            "total_response_time": self.total_response_time,
            "max_response_time": self.max_response_time,
            "min_response_time": self.min_response_time,
            "total_content_length": self.total_content_length,
            "response_times": self.response_times,
            "num_reqs_per_sec": self.num_reqs_per_sec,
        }
    
    @classmethod
    def unserialize(cls, data):
        obj = cls(None, data["name"], data["method"])
        for key in [
            "last_request_timestamp",
            "start_time",
            "num_requests",
            "num_failures",
            "total_response_time",
            "max_response_time",
            "min_response_time",
            "total_content_length",
            "response_times",
            "num_reqs_per_sec",
        ]:
            setattr(obj, key, data[key])
        return obj
    
    def get_stripped_report(self):
        """
        Return the serialized version of this StatsEntry, and then clear the current stats.
        """
        report = self.serialize()
        self.reset()
        return report

    def __str__(self):
        try:
            fail_percent = (self.num_failures/float(self.num_requests + self.num_failures))*100
        except ZeroDivisionError:
            fail_percent = 0
        
        return (" %-" + str(STATS_NAME_WIDTH) + "s %7d %12s %7d %7d %7d  | %7d %7.2f") % (
            self.method + " " + self.name,
            self.num_requests,
            "%d(%.2f%%)" % (self.num_failures, fail_percent),
            self.avg_response_time,
            self.min_response_time or 0,
            self.max_response_time,
            self.median_response_time or 0,
            self.current_rps or 0
        )
    
    def get_response_time_percentile(self, percent):
        """
        Get the response time that a certain number of percent of the requests
        finished within.
        
        Percent specified in range: 0.0 - 1.0
        """
        num_of_request = int((self.num_requests * percent))

        processed_count = 0
        for response_time in sorted(self.response_times.iterkeys(), reverse=True):
            processed_count += self.response_times[response_time]
            if((self.num_requests - processed_count) <= num_of_request):
                return response_time

    def percentile(self, tpl=" %-" + str(STATS_NAME_WIDTH) + "s %8d %6d %6d %6d %6d %6d %6d %6d %6d %6d"):
        if not self.num_requests:
            raise ValueError("Can't calculate percentile on url with no successful requests")
        
        return tpl % (
            self.name,
            self.num_requests,
            self.get_response_time_percentile(0.5),
            self.get_response_time_percentile(0.66),
            self.get_response_time_percentile(0.75),
            self.get_response_time_percentile(0.80),
            self.get_response_time_percentile(0.90),
            self.get_response_time_percentile(0.95),
            self.get_response_time_percentile(0.98),
            self.get_response_time_percentile(0.99),
            self.max_response_time
        )

class StatsError(object):
    def __init__(self, method, name, error, occurences=0):
        self.method = method
        self.name = name
        self.error = error
        self.occurences = occurences

    @classmethod
    def create_key(cls, method, name, error):
        key = "%s.%s.%r" % (method, name, error)
        return hashlib.md5(key).hexdigest()

    def occured(self):
        self.occurences += 1

    def to_name(self):
        return "%s %s: %r" % (self.method, 
            self.name, repr(self.error))

    def to_dict(self):
        return {
            "method": self.method,
            "name": self.name,
            "error": repr(self.error),
            "occurences": self.occurences
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["method"], 
            data["name"], 
            data["error"], 
            data["occurences"]
        )


def avg(values):
    return sum(values, 0.0) / max(len(values), 1)

def median_from_dict(total, count):
    """
    total is the number of requests made
    count is a dict {response_time: count}
    """
    pos = (total - 1) / 2
    for k in sorted(count.iterkeys()):
        if pos < count[k]:
            return k
        pos -= count[k]


global_stats = RequestStats()
"""
A global instance for holding the statistics. Should be removed eventually.
"""

def on_request_success(request_type, name, response_time, response_length):
    if global_stats.max_requests is not None and (global_stats.num_requests + global_stats.num_failures) >= global_stats.max_requests:
        raise StopLocust("Maximum number of requests reached")
    global_stats.get(name, request_type).log(response_time, response_length)

def on_request_failure(request_type, name, response_time, exception):
    if global_stats.max_requests is not None and (global_stats.num_requests + global_stats.num_failures) >= global_stats.max_requests:
        raise StopLocust("Maximum number of requests reached")
    global_stats.get(name, request_type).log_error(exception)

def on_report_to_master(client_id, data):
    data["stats"] = [global_stats.entries[key].get_stripped_report() for key in global_stats.entries.iterkeys() if not (global_stats.entries[key].num_requests == 0 and global_stats.entries[key].num_failures == 0)]
    data["errors"] =  dict([(k, e.to_dict()) for k, e in global_stats.errors.iteritems()])
    global_stats.errors = {}

def on_slave_report(client_id, data):
    for stats_data in data["stats"]:
        entry = StatsEntry.unserialize(stats_data)
        request_key = (entry.name, entry.method)
        if not request_key in global_stats.entries:
            global_stats.entries[request_key] = StatsEntry(global_stats, entry.name, entry.method)
        global_stats.entries[request_key].extend(entry, full_request_history=True)
        global_stats.last_request_timestamp = max(global_stats.last_request_timestamp, entry.last_request_timestamp)

    for error_key, error in data["errors"].iteritems():
        if error_key not in global_stats.errors:
            global_stats.errors[error_key] = StatsError.from_dict(error)
        else:
            global_stats.errors[error_key].occurences += error["occurences"]

events.request_success += on_request_success
events.request_failure += on_request_failure
events.report_to_master += on_report_to_master
events.slave_report += on_slave_report


def print_stats(stats):
    console_logger.info((" %-" + str(STATS_NAME_WIDTH) + "s %7s %12s %7s %7s %7s  | %7s %7s") % ('Name', '# reqs', '# fails', 'Avg', 'Min', 'Max', 'Median', 'req/s'))
    console_logger.info("-" * (80 + STATS_NAME_WIDTH))
    total_rps = 0
    total_reqs = 0
    total_failures = 0
    for key in sorted(stats.iterkeys()):
        r = stats[key]
        total_rps += r.current_rps
        total_reqs += r.num_requests
        total_failures += r.num_failures
        console_logger.info(r)
    console_logger.info("-" * (80 + STATS_NAME_WIDTH))

    try:
        fail_percent = (total_failures/float(total_reqs))*100
    except ZeroDivisionError:
        fail_percent = 0

    console_logger.info((" %-" + str(STATS_NAME_WIDTH) + "s %7d %12s %42.2f") % ('Total', total_reqs, "%d(%.2f%%)" % (total_failures, fail_percent), total_rps))
    console_logger.info("")

def print_percentile_stats(stats):
    console_logger.info("Percentage of the requests completed within given times")
    console_logger.info((" %-" + str(STATS_NAME_WIDTH) + "s %8s %6s %6s %6s %6s %6s %6s %6s %6s %6s") % ('Name', '# reqs', '50%', '66%', '75%', '80%', '90%', '95%', '98%', '99%', '100%'))
    console_logger.info("-" * (80 + STATS_NAME_WIDTH))
    for key in sorted(stats.iterkeys()):
        r = stats[key]
        if r.response_times:
            console_logger.info(r.percentile())
    console_logger.info("-" * (80 + STATS_NAME_WIDTH))
    
    total_stats = global_stats.aggregated_stats()
    if total_stats.response_times:
        console_logger.info(total_stats.percentile())
    console_logger.info("")

def print_error_report():
    if not len(global_stats.errors):
        return
    console_logger.info("Error report")
    console_logger.info(" %-18s %-100s" % ("# occurences", "Error"))
    console_logger.info("-" * (80 + STATS_NAME_WIDTH))
    for error in global_stats.errors.itervalues():
        console_logger.info(" %-18i %-100s" % (error.occurences, error.to_name()))
    console_logger.info("-" * (80 + STATS_NAME_WIDTH))
    console_logger.info("")

def stats_printer():
    from runners import locust_runner
    while True:
        print_stats(locust_runner.request_stats)
        gevent.sleep(2)

########NEW FILE########
__FILENAME__ = testcases
import base64
import gevent
import gevent.pywsgi
import random
import unittest
from copy import copy
from StringIO import StringIO

from locust import events
from locust.stats import global_stats
from flask import Flask, request, redirect, make_response, send_file

app = Flask(__name__)

@app.route("/ultra_fast")
def ultra_fast():
    return "This is an ultra fast response"

@app.route("/fast")
def fast():
    gevent.sleep(random.choice([0.1, 0.2, 0.3]))
    return "This is a fast response"

@app.route("/slow")
def slow():
    gevent.sleep(random.choice([0.5, 1, 1.5]))
    return "This is a slow response"

@app.route("/consistent")
def consistent():
    gevent.sleep(0.2)
    return "This is a consistent response"

@app.route("/request_method", methods=["POST", "GET", "HEAD", "PUT", "DELETE"])
def request_method():
    return request.method

@app.route("/request_header_test")
def request_header_test():
    return request.headers["X-Header-Test"]

@app.route("/post", methods=["POST"])
@app.route("/put", methods=["PUT"])
def manipulate():
    return str(request.form.get("arg", ""))

@app.route("/fail")
def failed_request():
    return "This response failed", 500

@app.route("/redirect")
def do_redirect():
    return redirect("/ultra_fast")

@app.route("/basic_auth")
def basic_auth():
    auth = base64.b64decode(request.headers.get("Authorization").replace("Basic ", ""))
    if auth == "locust:menace":
        return "Authorized"
    resp = make_response("401 Authorization Required", 401)
    resp.headers["WWW-Authenticate"] = 'Basic realm="Locust"'
    return resp

@app.route("/no_content_length")
def no_content_length():
    r = send_file(StringIO("This response does not have content-length in the header"), add_etags=False)
    return r

@app.errorhandler(404)
def not_found(error):
    return "Not Found", 404


class LocustTestCase(unittest.TestCase):
    """
    Test case class that restores locust.events.EventHook listeners on tearDown, so that it is
    safe to register any custom event handlers within the test.
    """
    def setUp(self):
        self._event_handlers = {}
        for name in dir(events):
            event = getattr(events, name)
            if isinstance(event, events.EventHook):
                self._event_handlers[event] = copy(event._handlers)
                      
    def tearDown(self):
        for event, handlers in self._event_handlers.iteritems():
            event._handlers = handlers
    
    def assertIn(self, member, container, msg=None):
        """
        Just like self.assertTrue(a in b), but with a nicer default message.
        Implemented here to work with Python 2.6
        """
        
        _MAX_LENGTH = 80
        def safe_repr(obj, short=False):
            try:
                result = repr(obj)
            except Exception:
                result = object.__repr__(obj)
            if not short or len(result) < _MAX_LENGTH:
                return result
            return result[:_MAX_LENGTH] + ' [truncated]...'
        
        if member not in container:
            standardMsg = '%s not found in %s' % (safe_repr(member),
                                                  safe_repr(container))
            self.fail(self._formatMessage(msg, standardMsg))

            
class WebserverTestCase(LocustTestCase):
    """
    Test case class that sets up an HTTP server which can be used within the tests
    """
    def setUp(self):
        super(WebserverTestCase, self).setUp()
        self._web_server = gevent.pywsgi.WSGIServer(("127.0.0.1", 0), app, log=None)
        gevent.spawn(lambda: self._web_server.serve_forever())
        gevent.sleep(0.01)
        self.port = self._web_server.server_port
        global_stats.clear_all()

    def tearDown(self):
        super(WebserverTestCase, self).tearDown()
        self._web_server.stop_accepting()
        self._web_server.stop()

########NEW FILE########
__FILENAME__ = test_client
from requests.exceptions import (RequestException, MissingSchema,
        InvalidSchema, InvalidURL)

from locust.clients import HttpSession
from testcases import WebserverTestCase

class TestHttpSession(WebserverTestCase):
    def test_get(self):
        s = HttpSession("http://127.0.0.1:%i" % self.port)
        r = s.get("/ultra_fast")
        self.assertEqual(200, r.status_code)
    
    def test_connection_error(self):
        s = HttpSession("http://localhost:1")
        r = s.get("/", timeout=0.1)
        self.assertEqual(r.status_code, 0)
        self.assertEqual(None, r.content)
        self.assertRaises(RequestException, r.raise_for_status)

    def test_wrong_url(self):
        for url, exception in (
                (u"http://\x94", InvalidURL),
                ("telnet://127.0.0.1", InvalidSchema),
                ("127.0.0.1", MissingSchema), 
            ):
            s = HttpSession(url)
            try:
                self.assertRaises(exception, s.get, "/")
            except KeyError:
                self.fail("Invalid URL %s was not propagated" % url)

########NEW FILE########
__FILENAME__ = test_locust_class
import unittest

from locust.core import HttpLocust, Locust, TaskSet, task, events
from locust import ResponseError, InterruptTaskSet
from locust.exception import CatchResponseError, RescheduleTask, RescheduleTaskImmediately, LocustError

from testcases import LocustTestCase, WebserverTestCase

class TestTaskSet(LocustTestCase):
    def setUp(self):
        super(TestTaskSet, self).setUp()
        
        class User(Locust):
            host = "127.0.0.1"
        self.locust = User()
    
    def test_task_ratio(self):
        t1 = lambda l: None
        t2 = lambda l: None
        class MyTasks(TaskSet):
            tasks = {t1:5, t2:2}
        
        l = MyTasks(self.locust)

        t1_count = len([t for t in l.tasks if t == t1])
        t2_count = len([t for t in l.tasks if t == t2])

        self.assertEqual(t1_count, 5)
        self.assertEqual(t2_count, 2)
    
    def test_task_decorator_ratio(self):
        t1 = lambda l: None
        t2 = lambda l: None
        class MyTasks(TaskSet):
            tasks = {t1:5, t2:2}
            host = ""
            
            @task(3)
            def t3(self):
                pass
            
            @task(13)
            def t4(self):
                pass
            

        l = MyTasks(self.locust)

        t1_count = len([t for t in l.tasks if t == t1])
        t2_count = len([t for t in l.tasks if t == t2])
        t3_count = len([t for t in l.tasks if t.__name__ == MyTasks.t3.__name__])
        t4_count = len([t for t in l.tasks if t.__name__ == MyTasks.t4.__name__])

        self.assertEqual(t1_count, 5)
        self.assertEqual(t2_count, 2)
        self.assertEqual(t3_count, 3)
        self.assertEqual(t4_count, 13)

    def test_on_start(self):
        class MyTasks(TaskSet):
            t1_executed = False
            t2_executed = False
            
            def on_start(self):
                self.t1()
            
            def t1(self):
                self.t1_executed = True
            
            @task
            def t2(self):
                self.t2_executed = True
                raise InterruptTaskSet(reschedule=False)

        l = MyTasks(self.locust)
        self.assertRaises(RescheduleTask, lambda: l.run())
        self.assertTrue(l.t1_executed)
        self.assertTrue(l.t2_executed)

    def test_schedule_task(self):
        self.t1_executed = False
        self.t2_arg = None

        def t1(l):
            self.t1_executed = True

        def t2(l, arg):
            self.t2_arg = arg

        class MyTasks(TaskSet):
            tasks = [t1, t2]

        taskset = MyTasks(self.locust)
        taskset.schedule_task(t1)
        taskset.execute_next_task()
        self.assertTrue(self.t1_executed)

        taskset.schedule_task(t2, args=["argument to t2"])
        taskset.execute_next_task()
        self.assertEqual("argument to t2", self.t2_arg)
    
    def test_schedule_task_with_kwargs(self):
        class MyTasks(TaskSet):
            @task
            def t1(self):
                self.t1_executed = True
            @task
            def t2(self, *args, **kwargs):
                self.t2_args = args
                self.t2_kwargs = kwargs
        loc = MyTasks(self.locust)
        loc.schedule_task(loc.t2, [42], {"test_kw":"hello"})
        loc.execute_next_task()
        self.assertEqual((42, ), loc.t2_args)
        self.assertEqual({"test_kw":"hello"}, loc.t2_kwargs)
        
        loc.schedule_task(loc.t2, args=[10, 4], kwargs={"arg1":1, "arg2":2})
        loc.execute_next_task()
        self.assertEqual((10, 4), loc.t2_args)
        self.assertEqual({"arg1":1, "arg2":2}, loc.t2_kwargs)
    
    def test_schedule_task_bound_method(self):
        class MyTasks(TaskSet):
            host = ""
            
            @task()
            def t1(self):
                self.t1_executed = True
                self.schedule_task(self.t2)
            def t2(self):
                self.t2_executed = True
        
        taskset = MyTasks(self.locust)
        taskset.schedule_task(taskset.get_next_task())
        taskset.execute_next_task()
        self.assertTrue(taskset.t1_executed)
        taskset.execute_next_task()
        self.assertTrue(taskset.t2_executed)
        
    
    def test_taskset_inheritance(self):
        def t1(l):
            pass
        class MyBaseTaskSet(TaskSet):
            tasks = [t1]
            host = ""
        class MySubTaskSet(MyBaseTaskSet):
            @task
            def t2(self):
                pass
        
        l = MySubTaskSet(self.locust)
        self.assertEqual(2, len(l.tasks))
        self.assertEqual([t1, MySubTaskSet.t2.__func__], l.tasks)
    
    def test_task_decorator_with_or_without_argument(self):
        class MyTaskSet(TaskSet):
            @task
            def t1(self):
                pass
        taskset = MyTaskSet(self.locust)
        self.assertEqual(len(taskset.tasks), 1)
        
        class MyTaskSet2(TaskSet):
            @task()
            def t1(self):
                pass
        taskset = MyTaskSet2(self.locust)
        self.assertEqual(len(taskset.tasks), 1)
        
        class MyTaskSet3(TaskSet):
            @task(3)
            def t1(self):
                pass
        taskset = MyTaskSet3(self.locust)
        self.assertEqual(len(taskset.tasks), 3)
    
    def test_sub_taskset(self):
        class MySubTaskSet(TaskSet):
            min_wait=1
            max_wait=1
            @task()
            def a_task(self):
                self.locust.sub_locust_task_executed = True
                self.interrupt()
            
        class MyTaskSet(TaskSet):
            tasks = [MySubTaskSet]
        
        self.sub_locust_task_executed = False
        loc = MyTaskSet(self.locust)
        loc.schedule_task(loc.get_next_task())
        self.assertRaises(RescheduleTaskImmediately, lambda: loc.execute_next_task())
        self.assertTrue(self.locust.sub_locust_task_executed)
    
    def test_sub_taskset_tasks_decorator(self):
        class MyTaskSet(TaskSet):
            @task
            class MySubTaskSet(TaskSet):
                min_wait=1
                max_wait=1
                @task()
                def a_task(self):
                    self.locust.sub_locust_task_executed = True
                    self.interrupt()
        
        self.sub_locust_task_executed = False
        loc = MyTaskSet(self.locust)
        loc.schedule_task(loc.get_next_task())
        self.assertRaises(RescheduleTaskImmediately, lambda: loc.execute_next_task())
        self.assertTrue(self.locust.sub_locust_task_executed)
    
    def test_sub_taskset_arguments(self):
        class MySubTaskSet(TaskSet):
            min_wait=1
            max_wait=1
            @task()
            def a_task(self):
                self.locust.sub_taskset_args = self.args
                self.locust.sub_taskset_kwargs = self.kwargs
                self.interrupt()
        class MyTaskSet(TaskSet):
            sub_locust_args = None
            sub_locust_kwargs = None
            tasks = [MySubTaskSet]
        
        self.locust.sub_taskset_args = None
        self.locust.sub_taskset_kwargs = None
        
        loc = MyTaskSet(self.locust)
        loc.schedule_task(MySubTaskSet, args=[1,2,3], kwargs={"hello":"world"})
        self.assertRaises(RescheduleTaskImmediately, lambda: loc.execute_next_task())
        self.assertEqual((1,2,3), self.locust.sub_taskset_args)
        self.assertEqual({"hello":"world"}, self.locust.sub_taskset_kwargs)
    
    def test_interrupt_taskset_in_main_taskset(self):
        class MyTaskSet(TaskSet):
            @task
            def interrupted_task(self):
                raise InterruptTaskSet(reschedule=False)
        class MyLocust(Locust):
            host = "http://127.0.0.1"
            task_set = MyTaskSet
        
        class MyTaskSet2(TaskSet):
            @task
            def interrupted_task(self):
                self.interrupt()
        class MyLocust2(Locust):
            host = "http://127.0.0.1"
            task_set = MyTaskSet2
        
        l = MyLocust()
        l2 = MyLocust2()
        self.assertRaises(LocustError, lambda: l.run())
        self.assertRaises(LocustError, lambda: l2.run())
        
        try:
            l.run()
        except LocustError as e:
            self.assertTrue("MyLocust" in e.args[0], "MyLocust should have been referred to in the exception message")
            self.assertTrue("MyTaskSet" in e.args[0], "MyTaskSet should have been referred to in the exception message")
        except:
            raise
        
        try:
            l2.run()
        except LocustError as e:
            self.assertTrue("MyLocust2" in e.args[0], "MyLocust2 should have been referred to in the exception message")
            self.assertTrue("MyTaskSet2" in e.args[0], "MyTaskSet2 should have been referred to in the exception message")
        except:
            raise
    
    def test_on_start_interrupt(self):
        class SubTaskSet(TaskSet):
            def on_start(self):
                if self.kwargs["reschedule"]:
                    self.interrupt(reschedule=True)
                else:
                    self.interrupt(reschedule=False)
        
        class MyLocust(Locust):
            host = ""
            task_set = SubTaskSet
        
        l = MyLocust()
        task_set = SubTaskSet(l)
        self.assertRaises(RescheduleTaskImmediately, lambda: task_set.run(reschedule=True))
        self.assertRaises(RescheduleTask, lambda: task_set.run(reschedule=False))

    
    def test_parent_attribute(self):
        from locust.exception import StopLocust
        parents = {}
        
        class SubTaskSet(TaskSet):
            def on_start(self):
                parents["sub"] = self.parent
            
            @task
            class SubSubTaskSet(TaskSet):
                def on_start(self):
                    parents["subsub"] = self.parent
                @task
                def stop(self):
                    raise StopLocust()
        class RootTaskSet(TaskSet):
            tasks = [SubTaskSet]
        
        class MyLocust(Locust):
            host = ""
            task_set = RootTaskSet
        
        l = MyLocust()
        l.run()
        self.assertTrue(isinstance(parents["sub"], RootTaskSet))
        self.assertTrue(isinstance(parents["subsub"], SubTaskSet))
    

class TestWebLocustClass(WebserverTestCase):
    def test_get_request(self):
        self.response = ""
        def t1(l):
            self.response = l.client.get("/ultra_fast")
        class MyLocust(HttpLocust):
            tasks = [t1]
            host = "http://127.0.0.1:%i" % self.port

        my_locust = MyLocust()
        t1(my_locust)
        self.assertEqual(self.response.content, "This is an ultra fast response")

    def test_client_request_headers(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port

        locust = MyLocust()
        self.assertEqual("hello", locust.client.get("/request_header_test", headers={"X-Header-Test":"hello"}).content)

    def test_client_get(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port

        locust = MyLocust()
        self.assertEqual("GET", locust.client.get("/request_method").content)
    
    def test_client_get_absolute_url(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port

        locust = MyLocust()
        self.assertEqual("GET", locust.client.get("http://127.0.0.1:%i/request_method" % self.port).content)

    def test_client_post(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port

        locust = MyLocust()
        self.assertEqual("POST", locust.client.post("/request_method", {"arg":"hello world"}).content)
        self.assertEqual("hello world", locust.client.post("/post", {"arg":"hello world"}).content)

    def test_client_put(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port

        locust = MyLocust()
        self.assertEqual("PUT", locust.client.put("/request_method", {"arg":"hello world"}).content)
        self.assertEqual("hello world", locust.client.put("/put", {"arg":"hello world"}).content)

    def test_client_delete(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port

        locust = MyLocust()
        self.assertEqual("DELETE", locust.client.delete("/request_method").content)
        self.assertEqual(200, locust.client.delete("/request_method").status_code)

    def test_client_head(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port

        locust = MyLocust()
        self.assertEqual(200, locust.client.head("/request_method").status_code)

    def test_client_basic_auth(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port

        class MyAuthorizedLocust(HttpLocust):
            host = "http://locust:menace@127.0.0.1:%i" % self.port

        class MyUnauthorizedLocust(HttpLocust):
            host = "http://locust:wrong@127.0.0.1:%i" % self.port

        locust = MyLocust()
        unauthorized = MyUnauthorizedLocust()
        authorized = MyAuthorizedLocust()
        self.assertEqual("Authorized", authorized.client.get("/basic_auth").content)
        self.assertFalse(locust.client.get("/basic_auth"))
        self.assertFalse(unauthorized.client.get("/basic_auth"))
    
    def test_log_request_name_argument(self):
        from locust.stats import RequestStats, global_stats
        self.response = ""
        
        class MyLocust(HttpLocust):
            tasks = []
            host = "http://127.0.0.1:%i" % self.port
            
            @task()
            def t1(l):
                self.response = l.client.get("/ultra_fast", name="new name!")

        my_locust = MyLocust()
        my_locust.t1()
        
        self.assertEqual(1, global_stats.get("new name!", "GET").num_requests)
        self.assertEqual(0, global_stats.get("/ultra_fast", "GET").num_requests)
    
    def test_locust_client_error(self):
        class MyTaskSet(TaskSet):
            @task
            def t1(self):
                self.client.get("/")
                self.interrupt()
        
        class MyLocust(Locust):
            host = "http://127.0.0.1:%i" % self.port
            task_set = MyTaskSet
        
        my_locust = MyLocust()
        self.assertRaises(LocustError, lambda: my_locust.client.get("/"))
        my_taskset = MyTaskSet(my_locust)
        self.assertRaises(LocustError, lambda: my_taskset.client.get("/"))


class TestCatchResponse(WebserverTestCase):
    def setUp(self):
        super(TestCatchResponse, self).setUp()
        
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port

        self.locust = MyLocust()
        
        self.num_failures = 0
        self.num_success = 0
        def on_failure(request_type, name, response_time, exception):
            self.num_failures += 1
            self.last_failure_exception = exception
        def on_success(**kwargs):
            self.num_success += 1
        events.request_failure += on_failure
        events.request_success += on_success
        
    def test_catch_response(self):
        self.assertEqual(500, self.locust.client.get("/fail").status_code)
        self.assertEqual(1, self.num_failures)
        self.assertEqual(0, self.num_success)
        
        with self.locust.client.get("/ultra_fast", catch_response=True) as response: pass
        self.assertEqual(1, self.num_failures)
        self.assertEqual(1, self.num_success)
        
        with self.locust.client.get("/ultra_fast", catch_response=True) as response:
            raise ResponseError("Not working")
        
        self.assertEqual(2, self.num_failures)
        self.assertEqual(1, self.num_success)
    
    def test_catch_response_http_fail(self):
        with self.locust.client.get("/fail", catch_response=True) as response: pass
        self.assertEqual(1, self.num_failures)
        self.assertEqual(0, self.num_success)
    
    def test_catch_response_http_manual_fail(self):
        with self.locust.client.get("/ultra_fast", catch_response=True) as response:
            response.failure("Haha!")
        self.assertEqual(1, self.num_failures)
        self.assertEqual(0, self.num_success)
        self.assertTrue(
            isinstance(self.last_failure_exception, CatchResponseError),
            "Failure event handler should have been passed a CatchResponseError instance"
        )
    
    def test_catch_response_http_manual_success(self):
        with self.locust.client.get("/fail", catch_response=True) as response:
            response.success()
        self.assertEqual(0, self.num_failures)
        self.assertEqual(1, self.num_success)
    
    def test_catch_response_allow_404(self):
        with self.locust.client.get("/does/not/exist", catch_response=True) as response:
            self.assertEqual(404, response.status_code)
            if response.status_code == 404:
                response.success()
        self.assertEqual(0, self.num_failures)
        self.assertEqual(1, self.num_success)
    
    def test_interrupt_taskset_with_catch_response(self):
        class MyTaskSet(TaskSet):
            @task
            def interrupted_task(self):
                with self.client.get("/ultra_fast", catch_response=True) as r:
                    raise InterruptTaskSet()
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port
            task_set = MyTaskSet
        
        l = MyLocust()
        ts = MyTaskSet(l)
        self.assertRaises(InterruptTaskSet, lambda: ts.interrupted_task())
        self.assertEqual(0, self.num_failures)
        self.assertEqual(0, self.num_success)
    
    def test_catch_response_connection_error_success(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:1"
        l = MyLocust()
        with l.client.get("/", catch_response=True) as r:
            self.assertEqual(r.status_code, 0)
            self.assertEqual(None, r.content)
            r.success()
        self.assertEqual(1, self.num_success)
        self.assertEqual(0, self.num_failures)
    
    def test_catch_response_connection_error_fail(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:1"
        l = MyLocust()
        with l.client.get("/", catch_response=True) as r:
            self.assertEqual(r.status_code, 0)
            self.assertEqual(None, r.content)
            r.success()
        self.assertEqual(1, self.num_success)
        self.assertEqual(0, self.num_failures)

########NEW FILE########
__FILENAME__ = test_main
import unittest

from locust.core import HttpLocust, Locust, TaskSet
from locust import main
from .testcases import LocustTestCase, WebserverTestCase

class TestTaskSet(LocustTestCase):
    def test_is_locust(self):
        self.assertFalse(main.is_locust(("Locust", Locust)))
        self.assertFalse(main.is_locust(("HttpLocust", HttpLocust)))
        self.assertFalse(main.is_locust(("random_dict", {})))
        self.assertFalse(main.is_locust(("random_list", [])))
        
        class MyTaskSet(TaskSet):
            pass
        
        class MyHttpLocust(HttpLocust):
            task_set = MyTaskSet
        
        class MyLocust(Locust):
            task_set = MyTaskSet
        
        self.assertTrue(main.is_locust(("MyHttpLocust", MyHttpLocust)))
        self.assertTrue(main.is_locust(("MyLocust", MyLocust)))
        
        class ThriftLocust(Locust):
            pass
        
        self.assertFalse(main.is_locust(("ThriftLocust", ThriftLocust)))

########NEW FILE########
__FILENAME__ = test_runners
import unittest

import gevent
import mock

from gevent.queue import Queue
from gevent import sleep

from locust.runners import LocalLocustRunner, MasterLocustRunner, SlaveLocustRunner
from locust.core import Locust, task, TaskSet
from locust.exception import LocustError
from locust.rpc import Message
from locust.stats import RequestStats, global_stats
from locust.main import parse_options
from locust.test.testcases import LocustTestCase
from locust import events


def mocked_rpc_server():
    class MockedRpcServer(object):
        queue = Queue()
        outbox = []

        def __init__(self, host, port):
            pass
        
        @classmethod
        def mocked_send(cls, message):
            cls.queue.put(message.serialize())
        
        def recv(self):
            results = self.queue.get()
            return Message.unserialize(results)
        
        def send(self, message):
            self.outbox.append(message.serialize())
    
    return MockedRpcServer


class TestMasterRunner(LocustTestCase):
    def setUp(self):
        global_stats.reset_all()
        self._slave_report_event_handlers = [h for h in events.slave_report._handlers]

        parser, _, _ = parse_options()
        args = [
            "--clients", "10",
            "--hatch-rate", "10"
        ]
        opts, _ = parser.parse_args(args)
        self.options = opts
        
    def tearDown(self):
        events.slave_report._handlers = self._slave_report_event_handlers
    
    def test_slave_connect(self):
        import mock
        
        class MyTestLocust(Locust):
            pass
        
        with mock.patch("locust.rpc.rpc.Server", mocked_rpc_server()) as server:
            master = MasterLocustRunner(MyTestLocust, self.options)
            server.mocked_send(Message("client_ready", None, "zeh_fake_client1"))
            sleep(0)
            self.assertEqual(1, len(master.clients))
            self.assertTrue("zeh_fake_client1" in master.clients, "Could not find fake client in master instance's clients dict")
            server.mocked_send(Message("client_ready", None, "zeh_fake_client2"))
            server.mocked_send(Message("client_ready", None, "zeh_fake_client3"))
            server.mocked_send(Message("client_ready", None, "zeh_fake_client4"))
            sleep(0)
            self.assertEqual(4, len(master.clients))
            
            server.mocked_send(Message("quit", None, "zeh_fake_client3"))
            sleep(0)
            self.assertEqual(3, len(master.clients))
    
    def test_slave_stats_report_median(self):
        import mock
        
        class MyTestLocust(Locust):
            pass
        
        with mock.patch("locust.rpc.rpc.Server", mocked_rpc_server()) as server:
            master = MasterLocustRunner(MyTestLocust, self.options)
            server.mocked_send(Message("client_ready", None, "fake_client"))
            sleep(0)
            
            master.stats.get("/", "GET").log(100, 23455)
            master.stats.get("/", "GET").log(800, 23455)
            master.stats.get("/", "GET").log(700, 23455)
            
            data = {"user_count":1}
            events.report_to_master.fire(client_id="fake_client", data=data)
            master.stats.clear_all()
            
            server.mocked_send(Message("stats", data, "fake_client"))
            sleep(0)
            s = master.stats.get("/", "GET")
            self.assertEqual(700, s.median_response_time)
    
    def test_spawn_zero_locusts(self):
        class MyTaskSet(TaskSet):
            @task
            def my_task(self):
                pass
            
        class MyTestLocust(Locust):
            task_set = MyTaskSet
            min_wait = 100
            max_wait = 100
        
        runner = LocalLocustRunner([MyTestLocust], self.options)
        
        timeout = gevent.Timeout(2.0)
        timeout.start()
        
        try:
            runner.start_hatching(0, 1, wait=True)
            runner.greenlet.join()
        except gevent.Timeout:
            self.fail("Got Timeout exception. A locust seems to have been spawned, even though 0 was specified.")
        finally:
            timeout.cancel()
    
    def test_spawn_uneven_locusts(self):
        """
        Tests that we can accurately spawn a certain number of locusts, even if it's not an 
        even number of the connected slaves
        """
        import mock
        
        class MyTestLocust(Locust):
            pass
        
        with mock.patch("locust.rpc.rpc.Server", mocked_rpc_server()) as server:
            master = MasterLocustRunner(MyTestLocust, self.options)
            for i in range(5):
                server.mocked_send(Message("client_ready", None, "fake_client%i" % i))
                sleep(0)
            
            master.start_hatching(7, 7)
            self.assertEqual(5, len(server.outbox))
            
            num_clients = 0
            for msg in server.outbox:
                num_clients += Message.unserialize(msg).data["num_clients"]
            
            self.assertEqual(7, num_clients, "Total number of locusts that would have been spawned is not 7")
    
    def test_spawn_fewer_locusts_than_slaves(self):
        import mock
        
        class MyTestLocust(Locust):
            pass
        
        with mock.patch("locust.rpc.rpc.Server", mocked_rpc_server()) as server:
            master = MasterLocustRunner(MyTestLocust, self.options)
            for i in range(5):
                server.mocked_send(Message("client_ready", None, "fake_client%i" % i))
                sleep(0)
            
            master.start_hatching(2, 2)
            self.assertEqual(5, len(server.outbox))
            
            num_clients = 0
            for msg in server.outbox:
                num_clients += Message.unserialize(msg).data["num_clients"]
            
            self.assertEqual(2, num_clients, "Total number of locusts that would have been spawned is not 2")
    
    def test_exception_in_task(self):
        class HeyAnException(Exception):
            pass
        
        class MyLocust(Locust):
            class task_set(TaskSet):
                @task
                def will_error(self):
                    raise HeyAnException(":(")
        
        runner = LocalLocustRunner([MyLocust], self.options)
        
        l = MyLocust()
        l._catch_exceptions = False
        
        self.assertRaises(HeyAnException, l.run)
        self.assertRaises(HeyAnException, l.run)
        self.assertEqual(1, len(runner.exceptions))
        
        hash_key, exception = runner.exceptions.popitem()
        self.assertTrue("traceback" in exception)
        self.assertTrue("HeyAnException" in exception["traceback"])
        self.assertEqual(2, exception["count"])
    
    def test_exception_is_catched(self):
        """ Test that exceptions are stored, and execution continues """
        class HeyAnException(Exception):
            pass
        
        class MyTaskSet(TaskSet):
            def __init__(self, *a, **kw):
                super(MyTaskSet, self).__init__(*a, **kw)
                self._task_queue = [
                    {"callable":self.will_error, "args":[], "kwargs":{}}, 
                    {"callable":self.will_stop, "args":[], "kwargs":{}},
                ]
            
            @task(1)
            def will_error(self):
                raise HeyAnException(":(")
            
            @task(1)
            def will_stop(self):
                self.interrupt()
        
        class MyLocust(Locust):
            min_wait = 10
            max_wait = 10
            task_set = MyTaskSet
        
        runner = LocalLocustRunner([MyLocust], self.options)
        l = MyLocust()
        
        # supress stderr
        with mock.patch("sys.stderr") as mocked:
            l.task_set._task_queue = [l.task_set.will_error, l.task_set.will_stop]
            self.assertRaises(LocustError, l.run) # make sure HeyAnException isn't raised
            l.task_set._task_queue = [l.task_set.will_error, l.task_set.will_stop]
            self.assertRaises(LocustError, l.run) # make sure HeyAnException isn't raised
        self.assertEqual(2, len(mocked.method_calls))
        
        # make sure exception was stored
        self.assertEqual(1, len(runner.exceptions))
        hash_key, exception = runner.exceptions.popitem()
        self.assertTrue("traceback" in exception)
        self.assertTrue("HeyAnException" in exception["traceback"])
        self.assertEqual(2, exception["count"])


class TestMessageSerializing(unittest.TestCase):
    def test_message_serialize(self):
        msg = Message("client_ready", None, "my_id")
        rebuilt = Message.unserialize(msg.serialize())
        self.assertEqual(msg.type, rebuilt.type)
        self.assertEqual(msg.data, rebuilt.data)
        self.assertEqual(msg.node_id, rebuilt.node_id)
        

########NEW FILE########
__FILENAME__ = test_stats
import unittest
import time

from requests.exceptions import RequestException

from testcases import WebserverTestCase
from locust.stats import RequestStats, StatsEntry, global_stats
from locust.core import HttpLocust, Locust, TaskSet, task
from locust.inspectlocust import get_task_ratio_dict
from locust.rpc.protocol import Message

class TestRequestStats(unittest.TestCase):
    def setUp(self):
        self.stats = RequestStats()
        self.stats.start_time = time.time()
        self.s = StatsEntry(self.stats, "test_entry", "GET")
        self.s.log(45, 0)
        self.s.log(135, 0)
        self.s.log(44, 0)
        self.s.log_error(Exception("dummy fail"))
        self.s.log_error(Exception("dummy fail"))
        self.s.log(375, 0)
        self.s.log(601, 0)
        self.s.log(35, 0)
        self.s.log(79, 0)
        self.s.log_error(Exception("dummy fail"))

    def test_percentile(self):
        s = StatsEntry(self.stats, "percentile_test", "GET")
        for x in xrange(100):
            s.log(x, 0)

        self.assertEqual(s.get_response_time_percentile(0.5), 50)
        self.assertEqual(s.get_response_time_percentile(0.6), 60)
        self.assertEqual(s.get_response_time_percentile(0.95), 95)

    def test_median(self):
        self.assertEqual(self.s.median_response_time, 79)

    def test_total_rps(self):
        self.assertEqual(self.s.total_rps, 7)

    def test_current_rps(self):
        self.stats.last_request_timestamp = int(time.time()) + 4
        self.assertEqual(self.s.current_rps, 3.5)

        self.stats.last_request_timestamp = int(time.time()) + 25
        self.assertEqual(self.s.current_rps, 0)

    def test_num_reqs_fails(self):
        self.assertEqual(self.s.num_requests, 7)
        self.assertEqual(self.s.num_failures, 3)

    def test_avg(self):
        self.assertEqual(self.s.avg_response_time, 187.71428571428571428571428571429)

    def test_reset(self):
        self.s.reset()
        self.s.log(756, 0)
        self.s.log_error(Exception("dummy fail after reset"))
        self.s.log(85, 0)

        self.assertEqual(self.s.total_rps, 2)
        self.assertEqual(self.s.num_requests, 2)
        self.assertEqual(self.s.num_failures, 1)
        self.assertEqual(self.s.avg_response_time, 420.5)
        self.assertEqual(self.s.median_response_time, 85)
    
    def test_reset_min_response_time(self):
        self.s.reset()
        self.s.log(756, 0)
        self.assertEqual(756, self.s.min_response_time)

    def test_aggregation(self):
        s1 = StatsEntry(self.stats, "aggregate me!", "GET")
        s1.log(12, 0)
        s1.log(12, 0)
        s1.log(38, 0)
        s1.log_error("Dummy exzeption")

        s2 = StatsEntry(self.stats, "aggregate me!", "GET")
        s2.log_error("Dummy exzeption")
        s2.log_error("Dummy exzeption")
        s2.log(12, 0)
        s2.log(99, 0)
        s2.log(14, 0)
        s2.log(55, 0)
        s2.log(38, 0)
        s2.log(55, 0)
        s2.log(97, 0)

        s = StatsEntry(self.stats, "GET", "")
        s.extend(s1, full_request_history=True)
        s.extend(s2, full_request_history=True)

        self.assertEqual(s.num_requests, 10)
        self.assertEqual(s.num_failures, 3)
        self.assertEqual(s.median_response_time, 38)
        self.assertEqual(s.avg_response_time, 43.2)
    
    def test_serialize_through_message(self):
        """
        Serialize a RequestStats instance, then serialize it through a Message, 
        and unserialize the whole thing again. This is done "IRL" when stats are sent 
        from slaves to master.
        """
        s1 = StatsEntry(self.stats, "test", "GET")
        s1.log(10, 0)
        s1.log(20, 0)
        s1.log(40, 0)
        u1 = StatsEntry.unserialize(s1.serialize())
        
        data = Message.unserialize(Message("dummy", s1.serialize(), "none").serialize()).data
        u1 = StatsEntry.unserialize(data)
        
        self.assertEqual(20, u1.median_response_time)


class TestRequestStatsWithWebserver(WebserverTestCase):
    def test_request_stats_content_length(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port
    
        locust = MyLocust()
        locust.client.get("/ultra_fast")
        self.assertEqual(global_stats.get("/ultra_fast", "GET").avg_content_length, len("This is an ultra fast response"))
        locust.client.get("/ultra_fast")
        self.assertEqual(global_stats.get("/ultra_fast", "GET").avg_content_length, len("This is an ultra fast response"))
    
    def test_request_stats_no_content_length(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port
        l = MyLocust()
        path = "/no_content_length"
        r = l.client.get(path)
        self.assertEqual(global_stats.get(path, "GET").avg_content_length, len("This response does not have content-length in the header"))
    
    def test_request_stats_no_content_length_streaming(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port
        l = MyLocust()
        path = "/no_content_length"
        r = l.client.get(path, stream=True)
        self.assertEqual(0, global_stats.get(path, "GET").avg_content_length)
    
    def test_request_stats_named_endpoint(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port
    
        locust = MyLocust()
        locust.client.get("/ultra_fast", name="my_custom_name")
        self.assertEqual(1, global_stats.get("my_custom_name", "GET").num_requests)
    
    def test_request_stats_query_variables(self):
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port
    
        locust = MyLocust()
        locust.client.get("/ultra_fast?query=1")
        self.assertEqual(1, global_stats.get("/ultra_fast?query=1", "GET").num_requests)
    
    def test_request_connection_error(self):
        class MyLocust(HttpLocust):
            host = "http://localhost:1"
        
        locust = MyLocust()
        response = locust.client.get("/", timeout=0.1)
        self.assertEqual(response.status_code, 0)
        self.assertEqual(1, global_stats.get("/", "GET").num_failures)
        self.assertEqual(0, global_stats.get("/", "GET").num_requests)
    
    def test_max_requests(self):
        class MyTaskSet(TaskSet):
            @task
            def my_task(self):
                self.client.get("/ultra_fast")
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port
            task_set = MyTaskSet
            min_wait = 1
            max_wait = 1
            
        try:
            from locust.exception import StopLocust
            global_stats.clear_all()
            global_stats.max_requests = 2
            
            l = MyLocust()
            self.assertRaises(StopLocust, lambda: l.task_set(l).run())
            self.assertEqual(2, global_stats.num_requests)
            
            global_stats.clear_all()
            global_stats.max_requests = 2
            self.assertEqual(0, global_stats.num_requests)
            
            l.run()
            self.assertEqual(2, global_stats.num_requests)
        finally:
            global_stats.clear_all()
            global_stats.max_requests = None
    
    def test_max_requests_failed_requests(self):
        class MyTaskSet(TaskSet):
            @task
            def my_task(self):
                self.client.get("/ultra_fast")
                self.client.get("/fail")
                self.client.get("/fail")
            
        class MyLocust(HttpLocust):
            host = "http://127.0.0.1:%i" % self.port
            task_set = MyTaskSet
            min_wait = 1
            max_wait = 1
            
        try:
            from locust.exception import StopLocust
            global_stats.clear_all()
            global_stats.max_requests = 3
            
            l = MyLocust()
            self.assertRaises(StopLocust, lambda: l.task_set(l).run())
            self.assertEqual(1, global_stats.num_requests)
            self.assertEqual(2, global_stats.num_failures)
            
            global_stats.clear_all()
            global_stats.max_requests = 2
            self.assertEqual(0, global_stats.num_requests)
            self.assertEqual(0, global_stats.num_failures)
            l.run()
            self.assertEqual(1, global_stats.num_requests)
            self.assertEqual(1, global_stats.num_failures)
        finally:
            global_stats.clear_all()
            global_stats.max_requests = None


class MyTaskSet(TaskSet):
    @task(75)
    def root_task(self):
        pass
    
    @task(25)
    class MySubTaskSet(TaskSet):
        @task
        def task1(self):
            pass
        @task
        def task2(self):
            pass
    
class TestInspectLocust(unittest.TestCase):
    def test_get_task_ratio_dict_relative(self):
        ratio = get_task_ratio_dict([MyTaskSet])
        self.assertEqual(1.0, ratio["MyTaskSet"]["ratio"])
        self.assertEqual(0.75, ratio["MyTaskSet"]["tasks"]["root_task"]["ratio"])
        self.assertEqual(0.25, ratio["MyTaskSet"]["tasks"]["MySubTaskSet"]["ratio"])
        self.assertEqual(0.5, ratio["MyTaskSet"]["tasks"]["MySubTaskSet"]["tasks"]["task1"]["ratio"])
        self.assertEqual(0.5, ratio["MyTaskSet"]["tasks"]["MySubTaskSet"]["tasks"]["task2"]["ratio"])
    
    def test_get_task_ratio_dict_total(self):
        ratio = get_task_ratio_dict([MyTaskSet], total=True)
        self.assertEqual(1.0, ratio["MyTaskSet"]["ratio"])
        self.assertEqual(0.75, ratio["MyTaskSet"]["tasks"]["root_task"]["ratio"])
        self.assertEqual(0.25, ratio["MyTaskSet"]["tasks"]["MySubTaskSet"]["ratio"])
        self.assertEqual(0.125, ratio["MyTaskSet"]["tasks"]["MySubTaskSet"]["tasks"]["task1"]["ratio"])
        self.assertEqual(0.125, ratio["MyTaskSet"]["tasks"]["MySubTaskSet"]["tasks"]["task2"]["ratio"])

########NEW FILE########
__FILENAME__ = test_taskratio
import unittest

from locust.core import Locust, TaskSet, task
from locust.inspectlocust import get_task_ratio_dict

class TestTaskRatio(unittest.TestCase):
    def test_task_ratio_command(self):
        class Tasks(TaskSet):
            @task
            def root_task1(self):
                pass
            @task
            
            class SubTasks(TaskSet):
                @task
                def task1(self):
                    pass
                
                @task
                def task2(self):
                    pass
        
        class User(Locust):
            task_set = Tasks
        
        ratio_dict = get_task_ratio_dict(User.task_set.tasks, total=True)
        
        self.assertEqual({
            'SubTasks': {
                'tasks': {
                    'task1': {'ratio': 0.25},
                    'task2': {'ratio': 0.25}
                },
                'ratio': 0.5
            }, 
            'root_task1': {'ratio': 0.5}
        }, ratio_dict)
    
    def test_task_ratio_command_with_locust_weight(self):
        class Tasks(TaskSet):
            @task(1)
            def task1(self):
                pass

            @task(3)
            def task3(self):
                pass

        class UnlikelyLocust(Locust):
            weight = 1
            task_set = Tasks

	class MoreLikelyLocust(Locust):
            weight = 3
            task_set = Tasks

        ratio_dict = get_task_ratio_dict([UnlikelyLocust, MoreLikelyLocust], total=True)

        self.assertEquals({
               'UnlikelyLocust':   {'tasks': {'task1': {'ratio': 0.25*0.25}, 'task3': {'ratio': 0.25*0.75}}, 'ratio': 0.25},
               'MoreLikelyLocust': {'tasks': {'task1': {'ratio': 0.75*0.25}, 'task3': {'ratio': 0.75*0.75}}, 'ratio': 0.75}
               }, ratio_dict)
        unlikely = ratio_dict['UnlikelyLocust']['tasks']
        likely = ratio_dict['MoreLikelyLocust']['tasks']
        assert unlikely['task1']['ratio'] + unlikely['task3']['ratio'] + likely['task1']['ratio'] + likely['task3']['ratio'] == 1

########NEW FILE########
__FILENAME__ = test_web
import json

import requests
import mock
import gevent
from gevent import wsgi

from locust import web, runners, stats
from locust.runners import LocustRunner
from locust.main import parse_options
from .testcases import LocustTestCase

class TestWebUI(LocustTestCase):
    def setUp(self):
        super(TestWebUI, self).setUp()
        
        stats.global_stats.clear_all()
        parser = parse_options()[0]
        options = parser.parse_args([])[0]
        runners.locust_runner = LocustRunner([], options)
        
        self._web_ui_server = wsgi.WSGIServer(('127.0.0.1', 0), web.app, log=None)
        gevent.spawn(lambda: self._web_ui_server.serve_forever())
        gevent.sleep(0.01)
        self.web_port = self._web_ui_server.server_port
    
    def tearDown(self):
        super(TestWebUI, self).tearDown()
        self._web_ui_server.stop()
    
    def test_index(self):
        self.assertEqual(200, requests.get("http://127.0.0.1:%i/" % self.web_port).status_code)
    
    def test_stats_no_data(self):
        self.assertEqual(200, requests.get("http://127.0.0.1:%i/stats/requests" % self.web_port).status_code)
    
    def test_stats(self):
        stats.global_stats.get("/test", "GET").log(120, 5612)
        response = requests.get("http://127.0.0.1:%i/stats/requests" % self.web_port)
        self.assertEqual(200, response.status_code)
        
        data = json.loads(response.content)
        self.assertEqual(2, len(data["stats"])) # one entry plus Total
        self.assertEqual("/test", data["stats"][0]["name"])
        self.assertEqual("GET", data["stats"][0]["method"])
        self.assertEqual(120, data["stats"][0]["avg_response_time"])
        
    def test_stats_cache(self):
        stats.global_stats.get("/test", "GET").log(120, 5612)
        response = requests.get("http://127.0.0.1:%i/stats/requests" % self.web_port)
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content)
        self.assertEqual(2, len(data["stats"])) # one entry plus Total
        
        # add another entry
        stats.global_stats.get("/test2", "GET").log(120, 5612)
        data = json.loads(requests.get("http://127.0.0.1:%i/stats/requests" % self.web_port).content)
        self.assertEqual(2, len(data["stats"])) # old value should be cached now
        
        web.request_stats.clear_cache()
        
        data = json.loads(requests.get("http://127.0.0.1:%i/stats/requests" % self.web_port).content)
        self.assertEqual(3, len(data["stats"])) # this should no longer be cached
    
    def test_request_stats_csv(self):
        stats.global_stats.get("/test", "GET").log(120, 5612)
        response = requests.get("http://127.0.0.1:%i/stats/requests/csv" % self.web_port)
        self.assertEqual(200, response.status_code)
    
    def test_distribution_stats_csv(self):
        stats.global_stats.get("/test", "GET").log(120, 5612)
        response = requests.get("http://127.0.0.1:%i/stats/distribution/csv" % self.web_port)
        self.assertEqual(200, response.status_code)

########NEW FILE########
__FILENAME__ = web
# encoding: utf-8

import json
import os.path
from time import time
from itertools import chain
from collections import defaultdict

from gevent import wsgi
from flask import Flask, make_response, request, render_template

from . import runners
from .cache import memoize
from .runners import MasterLocustRunner
from locust.stats import median_from_dict
from locust import version
import gevent

import logging
logger = logging.getLogger(__name__)

DEFAULT_CACHE_TIME = 2.0

app = Flask(__name__)
app.debug = True
app.root_path = os.path.dirname(os.path.abspath(__file__))


@app.route('/')
def index():
    is_distributed = isinstance(runners.locust_runner, MasterLocustRunner)
    if is_distributed:
        slave_count = runners.locust_runner.slave_count
    else:
        slave_count = 0
    
    return render_template("index.html",
        state=runners.locust_runner.state,
        is_distributed=is_distributed,
        slave_count=slave_count,
        user_count=runners.locust_runner.user_count,
        version=version
    )

@app.route('/swarm', methods=["POST"])
def swarm():
    assert request.method == "POST"

    locust_count = int(request.form["locust_count"])
    hatch_rate = float(request.form["hatch_rate"])
    runners.locust_runner.start_hatching(locust_count, hatch_rate)
    response = make_response(json.dumps({'success':True, 'message': 'Swarming started'}))
    response.headers["Content-type"] = "application/json"
    return response

@app.route('/stop')
def stop():
    runners.locust_runner.stop()
    response = make_response(json.dumps({'success':True, 'message': 'Test stopped'}))
    response.headers["Content-type"] = "application/json"
    return response

@app.route("/stats/reset")
def reset_stats():
    runners.locust_runner.stats.reset_all()
    return "ok"
    
@app.route("/stats/requests/csv")
def request_stats_csv():
    rows = [
        ",".join([
            '"Method"',
            '"Name"',
            '"# requests"',
            '"# failures"',
            '"Median response time"',
            '"Average response time"',
            '"Min response time"', 
            '"Max response time"',
            '"Average Content Size"',
            '"Requests/s"',
        ])
    ]
    
    for s in chain(_sort_stats(runners.locust_runner.request_stats), [runners.locust_runner.stats.aggregated_stats("Total", full_request_history=True)]):
        rows.append('"%s","%s",%i,%i,%i,%i,%i,%i,%i,%.2f' % (
            s.method,
            s.name,
            s.num_requests,
            s.num_failures,
            s.median_response_time,
            s.avg_response_time,
            s.min_response_time or 0,
            s.max_response_time,
            s.avg_content_length,
            s.total_rps,
        ))

    response = make_response("\n".join(rows))
    file_name = "requests_{0}.csv".format(time())
    disposition = "attachment;filename={0}".format(file_name)
    response.headers["Content-type"] = "text/csv"
    response.headers["Content-disposition"] = disposition
    return response

@app.route("/stats/distribution/csv")
def distribution_stats_csv():
    rows = [",".join((
        '"Name"',
        '"# requests"',
        '"50%"',
        '"66%"',
        '"75%"',
        '"80%"',
        '"90%"',
        '"95%"',
        '"98%"',
        '"99%"',
        '"100%"',
    ))]
    for s in chain(_sort_stats(runners.locust_runner.request_stats), [runners.locust_runner.stats.aggregated_stats("Total", full_request_history=True)]):
        if s.num_requests:
            rows.append(s.percentile(tpl='"%s",%i,%i,%i,%i,%i,%i,%i,%i,%i,%i'))
        else:
            rows.append('"%s",0,"N/A","N/A","N/A","N/A","N/A","N/A","N/A","N/A","N/A"' % s.name)

    response = make_response("\n".join(rows))
    file_name = "distribution_{0}.csv".format(time())
    disposition = "attachment;filename={0}".format(file_name)
    response.headers["Content-type"] = "text/csv"
    response.headers["Content-disposition"] = disposition
    return response

@app.route('/stats/requests')
@memoize(timeout=DEFAULT_CACHE_TIME, dynamic_timeout=True)
def request_stats():
    stats = []
    for s in chain(_sort_stats(runners.locust_runner.request_stats), [runners.locust_runner.stats.aggregated_stats("Total")]):
        stats.append({
            "method": s.method,
            "name": s.name,
            "num_requests": s.num_requests,
            "num_failures": s.num_failures,
            "avg_response_time": s.avg_response_time,
            "min_response_time": s.min_response_time or 0,
            "max_response_time": s.max_response_time,
            "current_rps": s.current_rps,
            "median_response_time": s.median_response_time,
            "avg_content_length": s.avg_content_length,
        })
    
    report = {"stats":stats, "errors":[e.to_dict() for e in runners.locust_runner.errors.itervalues()]}
    if stats:
        report["total_rps"] = stats[len(stats)-1]["current_rps"]
        report["fail_ratio"] = runners.locust_runner.stats.aggregated_stats("Total").fail_ratio
        
        # since generating a total response times dict with all response times from all
        # urls is slow, we make a new total response time dict which will consist of one
        # entry per url with the median response time as key and the number of requests as
        # value
        response_times = defaultdict(int) # used for calculating total median
        for i in xrange(len(stats)-1):
            response_times[stats[i]["median_response_time"]] += stats[i]["num_requests"]
        
        # calculate total median
        stats[len(stats)-1]["median_response_time"] = median_from_dict(stats[len(stats)-1]["num_requests"], response_times)
    
    is_distributed = isinstance(runners.locust_runner, MasterLocustRunner)
    if is_distributed:
        report["slave_count"] = runners.locust_runner.slave_count
    
    report["state"] = runners.locust_runner.state
    report["user_count"] = runners.locust_runner.user_count
    return json.dumps(report)

@app.route("/exceptions")
def exceptions():
    response = make_response(json.dumps({'exceptions': [{"count": row["count"], "msg": row["msg"], "traceback": row["traceback"], "nodes" : ", ".join(row["nodes"])} for row in runners.locust_runner.exceptions.itervalues()]}))
    response.headers["Content-type"] = "application/json"
    return response

def start(locust, options):
    wsgi.WSGIServer((options.web_host, options.port), app, log=None).serve_forever()

def _sort_stats(stats):
    return [stats[key] for key in sorted(stats.iterkeys())]

########NEW FILE########
