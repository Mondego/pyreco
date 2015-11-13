__FILENAME__ = main
#!/usr/bin/env python
'''Demo of appstats tracing.

Starts a simple server with appstats enabled.  Go to http://localhost:8888/
to generate some sample data, then go to http://localhost:8888/appstats/
to see the results.

Requires tornado, tornado_tracing, and the google appengine sdk to be
on $PYTHONPATH.  It also doesn't like it when the app is started using
a relative path, so run it with something like this:

  export PYTHONPATH=.:../tornado:/usr/local/google_appengine:/usr/local/google_appengine/lib/webob
  $PWD/demo/main.py
'''

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.options import define, options, parse_command_line
from tornado.web import Application, asynchronous
from tornado_tracing import config
from tornado_tracing import recording

import time

define('port', type=int, default=8888)
define('memcache', default='localhost:11211')

class DelayHandler(recording.RecordingRequestHandler):
    @asynchronous
    def get(self):
        IOLoop.instance().add_timeout(
          time.time() + int(self.get_argument('ms')) / 1000.0,
          self.handle_timeout)

    def handle_timeout(self):
        self.finish("ok")

# A handler that performs several HTTP requests taking different amount of
# time.  It waits for the first request to finish, then issues three requests
# in parallel.
class RootHandler(recording.RecordingRequestHandler):
    @asynchronous
    def get(self):
        self.client = recording.AsyncHTTPClient()
        self.client.fetch('http://localhost:%d/delay?ms=100' % options.port,
                          self.step2)

    def handle_step2_fetch(self, response):
        assert response.body == 'ok'
        self.fetches_remaining -= 1
        if self.fetches_remaining == 0:
            self.step3()

    def step2(self, response):
        assert response.body == 'ok'
        self.fetches_remaining = 3
        self.client.fetch('http://localhost:%d/delay?ms=50' % options.port,
                          self.handle_step2_fetch)
        self.client.fetch('http://localhost:%d/delay?ms=20' % options.port,
                          self.handle_step2_fetch)
        self.client.fetch('http://localhost:%d/delay?ms=30' % options.port,
                          self.handle_step2_fetch)

    def step3(self):
        self.finish('All done. See results <a href="/appstats/">here</a>.')

def main():
    parse_command_line()
    # doesn't make much sense to run this without appstats enabled
    options.enable_appstats = True
    config.setup_memcache([options.memcache])

    app = Application([
        ('/', RootHandler),
        ('/delay', DelayHandler),
        config.get_urlspec('/appstats/.*'),
        ], debug=True)
    server = HTTPServer(app)
    server.listen(options.port)
    IOLoop.instance().start()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = config
import functools
import memcache
import tornado.web
import tornado.wsgi
import warnings

with warnings.catch_warnings():
    warnings.simplefilter('ignore', DeprecationWarning)
    from google.appengine.api import memcache as appengine_memcache
    from google.appengine.api import lib_config
    from google.appengine.ext import webapp

def setup_memcache(*args, **kwargs):
    '''Configures the app engine memcache interface with a set of regular
    memcache servers.  All arguments are passed to the memcache.Client
    constructor.

    Example:
      setup_memcache(["localhost:11211"])
    '''
    client = memcache.Client(*args, **kwargs)
    # The appengine memcache interface has some methods that aren't
    # currently available in the regular memcache module (at least
    # in version 1.4.4).  Fortunately appstats doesn't use them, but
    # the setup_client function expects them to be there.
    client.add_multi = None
    client.replace_multi = None
    client.offset_multi = None
    # Appengine adds a 'namespace' parameter to many methods.  Since
    # appstats.recording uses both namespace and key_prefix, just drop
    # the namespace.  (This list of methods is not exhaustive, it's just
    # the ones appstats uses)
    for method in ('set_multi', 'set', 'add', 'delete', 'get', 'get_multi'):
        def wrapper(old_method, *args, **kwargs):
            # appstats.recording always passes namespace by keyword
            if 'namespace' in kwargs:
                del kwargs['namespace']
            return old_method(*args, **kwargs)
        setattr(client, method,
                functools.partial(wrapper, getattr(client, method)))
    appengine_memcache.setup_client(client)

def get_urlspec(prefix):
    '''Returns a tornado.web.URLSpec for the appstats UI.
    Should be mapped to a url prefix ending with 'stats/'.

    Example:
      app = tornado.web.Application([
        ...
        tornado_tracing.config.get_urlspec(r'/_stats/.*'),
        ])
    '''
    # This import can't happen at the top level because things get horribly
    # confused if it happens before django settings are initialized.
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', DeprecationWarning)
        from google.appengine.ext.appstats import ui
    wsgi_app = tornado.wsgi.WSGIContainer(webapp.WSGIApplication(ui.URLMAP))
    return tornado.web.url(prefix,
                           tornado.web.FallbackHandler,
                           dict(fallback=wsgi_app))

def set_options(**kwargs):
    '''Sets configuration options for appstats.  See
    /usr/local/google_appengine/ext/appstats/recording.py for possible keys.

    Example:
    tornado_tracing.config.set_options(RECORD_FRACTION=0.1,
                                       KEY_PREFIX='__appstats_myapp__')
    '''
    lib_config.register('appstats', kwargs)

########NEW FILE########
__FILENAME__ = recording
'''RPC Tracing support.

Records timing information about rpcs and other operations for performance
profiling.  Currently just a wrapper around the Google App Engine appstats
module.
'''

import contextlib
import functools
import logging
import tornado.httpclient
import tornado.web
import tornado.wsgi
import warnings

with warnings.catch_warnings():
    warnings.simplefilter('ignore', DeprecationWarning)
    from google.appengine.ext.appstats import recording
from tornado.httpclient import AsyncHTTPClient
from tornado.options import define, options
from tornado.stack_context import StackContext
from tornado.web import RequestHandler

define('enable_appstats', type=bool, default=False)

# These methods from the appengine recording module are a part of our
# public API.

# start_recording(wsgi_environ) creates a recording context
start_recording = recording.start_recording
# end_recording(http_status) terminates a recording context
end_recording = recording.end_recording

# pre/post_call_hook(service, method, request, response) mark the
# beginning/end of a time span to record in the trace.
pre_call_hook = recording.pre_call_hook
post_call_hook = recording.post_call_hook

def save():
    '''Returns an object that can be passed to restore() to resume
    a suspended record.
    '''
    return recording.recorder

def restore(recorder):
    '''Reactivates a previously-saved recording context.'''
    recording.recorder = recorder


class RecordingRequestHandler(RequestHandler):
    '''RequestHandler subclass that establishes a recording context for each
    request.
    '''
    def __init__(self, *args, **kwargs):
        super(RecordingRequestHandler, self).__init__(*args, **kwargs)
        self.__recorder = None

    def _execute(self, transforms, *args, **kwargs):
        if options.enable_appstats:
            start_recording(tornado.wsgi.WSGIContainer.environ(self.request))
            recorder = save()
            @contextlib.contextmanager
            def transfer_recorder():
                restore(recorder)
                yield
            with StackContext(transfer_recorder):
                super(RecordingRequestHandler, self)._execute(transforms,
                                                              *args, **kwargs)
        else:
            super(RecordingRequestHandler, self)._execute(transforms,
                                                          *args, **kwargs)

    def finish(self, chunk=None):
        super(RecordingRequestHandler, self).finish(chunk)
        if options.enable_appstats:
            end_recording(self._status_code)

class RecordingFallbackHandler(tornado.web.FallbackHandler):
    '''FallbackHandler subclass that establishes a recording context for
    each request.
    '''
    def prepare(self):
        if options.enable_appstats:
            recording.start_recording(
              tornado.wsgi.WSGIContainer.environ(self.request))
            recorder = save()
            @contextlib.contextmanager
            def transfer_recorder():
                restore(recorder)
                yield
            with StackContext(transfer_recorder):
                super(RecordingFallbackHandler, self).prepare()
            recording.end_recording(self._status_code)
        else:
            super(RecordingFallbackHandler, self).prepare()

def _request_info(request):
    '''Returns a tuple (method, url) for use in recording traces.

    Accepts either a url or HTTPRequest object, like HTTPClient.fetch.
    '''
    if isinstance(request, tornado.httpclient.HTTPRequest):
        return (request.method, request.url)
    else:
        return ('GET', request)

class HTTPClient(tornado.httpclient.HTTPClient):
    def fetch(self, request, *args, **kwargs):
        method, url = _request_info(request)
        recording.pre_call_hook('HTTP', method, url, None)
        response = super(HTTPClient, self).fetch(request, *args, **kwargs)
        recording.post_call_hook('HTTP', method, url, None)
        return response

class AsyncHTTPClient(AsyncHTTPClient):
    def fetch(self, request, callback, *args, **kwargs):
        method, url = _request_info(request)
        recording.pre_call_hook('HTTP', method, url, None)
        def wrapper(request, callback, response, *args):
            recording.post_call_hook('HTTP', method, url, None)
            callback(response)
        super(AsyncHTTPClient, self).fetch(
          request,
          functools.partial(wrapper, request, callback),
          *args, **kwargs)

########NEW FILE########
