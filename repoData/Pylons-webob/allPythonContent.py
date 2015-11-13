__FILENAME__ = example
import os
import urllib
import time
import re
from cPickle import load, dump
from webob import Request, Response, html_escape
from webob import exc

class Commenter(object):

    def __init__(self, app, storage_dir):
        self.app = app
        self.storage_dir = storage_dir
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)

    def __call__(self, environ, start_response):
        req = Request(environ)
        if req.path_info_peek() == '.comments':
            return self.process_comment(req)(environ, start_response)
        # This is the base path of *this* middleware:
        base_url = req.application_url
        resp = req.get_response(self.app)
        if resp.content_type != 'text/html' or resp.status_code != 200:
            # Not an HTML response, we don't want to
            # do anything to it
            return resp(environ, start_response)
        # Make sure the content isn't gzipped:
        resp.decode_content()
        comments = self.get_data(req.url)
        body = resp.body
        body = self.add_to_end(body, self.format_comments(comments))
        body = self.add_to_end(body, self.submit_form(base_url, req))
        resp.body = body
        return resp(environ, start_response)

    def get_data(self, url):
        # Double-quoting makes the filename safe
        filename = self.url_filename(url)
        if not os.path.exists(filename):
            return []
        else:
            f = open(filename, 'rb')
            data = load(f)
            f.close()
            return data

    def save_data(self, url, data):
        filename = self.url_filename(url)
        f = open(filename, 'wb')
        dump(data, f)
        f.close()

    def url_filename(self, url):
        return os.path.join(self.storage_dir, urllib.quote(url, ''))

    _end_body_re = re.compile(r'</body.*?>', re.I|re.S)

    def add_to_end(self, html, extra_html):
        """
        Adds extra_html to the end of the html page (before </body>)
        """
        match = self._end_body_re.search(html)
        if not match:
            return html + extra_html
        else:
            return html[:match.start()] + extra_html + html[match.start():]

    def format_comments(self, comments):
        if not comments:
            return ''
        text = []
        text.append('<hr>')
        text.append('<h2><a name="comment-area"></a>Comments (%s):</h2>' % len(comments))
        for comment in comments:
            text.append('<h3><a href="%s">%s</a> at %s:</h3>' % (
                html_escape(comment['homepage']), html_escape(comment['name']),
                time.strftime('%c', comment['time'])))
            # Susceptible to XSS attacks!:
            text.append(comment['comments'])
        return ''.join(text)

    def submit_form(self, base_path, req):
        return '''<h2>Leave a comment:</h2>
        <form action="%s/.comments" method="POST">
         <input type="hidden" name="url" value="%s">
         <table width="100%%">
          <tr><td>Name:</td>
              <td><input type="text" name="name" style="width: 100%%"></td></tr>
          <tr><td>URL:</td>
              <td><input type="text" name="homepage" style="width: 100%%"></td></tr>
         </table>
         Comments:<br>
         <textarea name="comments" rows=10 style="width: 100%%"></textarea><br>
         <input type="submit" value="Submit comment">
        </form>
        ''' % (base_path, html_escape(req.url))

    def process_comment(self, req):
        try:
            url = req.params['url']
            name = req.params['name']
            homepage = req.params['homepage']
            comments = req.params['comments']
        except KeyError, e:
            resp = exc.HTTPBadRequest('Missing parameter: %s' % e)
            return resp
        data = self.get_data(url)
        data.append(dict(
            name=name,
            homepage=homepage,
            comments=comments,
            time=time.gmtime()))
        self.save_data(url, data)
        resp = exc.HTTPSeeOther(location=url+'#comment-area')
        return resp

if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser(
        usage='%prog --port=PORT BASE_DIRECTORY'
        )
    parser.add_option(
        '-p', '--port',
        default='8080',
        dest='port',
        type='int',
        help='Port to serve on (default 8080)')
    parser.add_option(
        '--comment-data',
        default='./comments',
        dest='comment_data',
        help='Place to put comment data into (default ./comments/)')
    options, args = parser.parse_args()
    if not args:
        parser.error('You must give a BASE_DIRECTORY')
    base_dir = args[0]
    from paste.urlparser import StaticURLParser
    app = StaticURLParser(base_dir)
    app = Commenter(app, options.comment_data)
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', options.port, app)
    print 'Serving on http://localhost:%s' % options.port
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print '^C'

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
import pkg_resources

version = release = pkg_resources.get_distribution('webob').version

extensions = ['sphinx.ext.autodoc']

source_suffix = '.txt' # The suffix of source filenames.
master_doc = 'index' # The master toctree document.

project = 'WebOb'
copyright = '2011, Ian Bicking and contributors'
exclude_patterns = ['jsonrpc-example-code/*']

modindex_common_prefix = ['webob.']

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True


# html_favicon = ...
html_add_permalinks = False
#html_show_sourcelink = True # ?set to False?

# Content template for the index page.
#html_index = ''

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Output file base name for HTML help builder.
htmlhelp_basename = 'WebObdoc'


########NEW FILE########
__FILENAME__ = doctests
import unittest
import doctest

def test_suite():
    flags = doctest.ELLIPSIS|doctest.NORMALIZE_WHITESPACE
    return unittest.TestSuite((
        doctest.DocFileSuite('test_request.txt', optionflags=flags),
        doctest.DocFileSuite('test_response.txt', optionflags=flags),
        doctest.DocFileSuite('test_dec.txt', optionflags=flags),
        doctest.DocFileSuite('do-it-yourself.txt', optionflags=flags),
        doctest.DocFileSuite('file-example.txt', optionflags=flags),
        doctest.DocFileSuite('index.txt', optionflags=flags),
        doctest.DocFileSuite('reference.txt', optionflags=flags),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

########NEW FILE########
__FILENAME__ = jsonrpc
# A reaction to: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/552751
from webob import Request, Response
from webob import exc
from simplejson import loads, dumps
import traceback
import sys

class JsonRpcApp(object):
    """
    Serve the given object via json-rpc (http://json-rpc.org/)
    """

    def __init__(self, obj):
        self.obj = obj

    def __call__(self, environ, start_response):
        req = Request(environ)
        try:
            resp = self.process(req)
        except ValueError, e:
            resp = exc.HTTPBadRequest(str(e))
        except exc.HTTPException, e:
            resp = e
        return resp(environ, start_response)

    def process(self, req):
        if not req.method == 'POST':
            raise exc.HTTPMethodNotAllowed(
                "Only POST allowed",
                allowed='POST')
        try:
            json = loads(req.body)
        except ValueError, e:
            raise ValueError('Bad JSON: %s' % e)
        try:
            method = json['method']
            params = json['params']
            id = json['id']
        except KeyError, e:
            raise ValueError(
                "JSON body missing parameter: %s" % e)
        if method.startswith('_'):
            raise exc.HTTPForbidden(
                "Bad method name %s: must not start with _" % method)
        if not isinstance(params, list):
            raise ValueError(
                "Bad params %r: must be a list" % params)
        try:
            method = getattr(self.obj, method)
        except AttributeError:
            raise ValueError(
                "No such method %s" % method)
        try:
            result = method(*params)
        except:
            text = traceback.format_exc()
            exc_value = sys.exc_info()[1]
            error_value = dict(
                name='JSONRPCError',
                code=100,
                message=str(exc_value),
                error=text)
            return Response(
                status=500,
                content_type='application/json',
                body=dumps(dict(result=None,
                                error=error_value,
                                id=id)))
        return Response(
            content_type='application/json',
            body=dumps(dict(result=result,
                            error=None,
                            id=id)))


class ServerProxy(object):
    """
    JSON proxy to a remote service.
    """

    def __init__(self, url, proxy=None):
        self._url = url
        if proxy is None:
            from wsgiproxy.exactproxy import proxy_exact_request
            proxy = proxy_exact_request
        self.proxy = proxy

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return _Method(self, name)

    def __repr__(self):
        return '<%s for %s>' % (
            self.__class__.__name__, self._url)

class _Method(object):

    def __init__(self, parent, name):
        self.parent = parent
        self.name = name

    def __call__(self, *args):
        json = dict(method=self.name,
                    id=None,
                    params=list(args))
        req = Request.blank(self.parent._url)
        req.method = 'POST'
        req.content_type = 'application/json'
        req.body = dumps(json)
        resp = req.get_response(self.parent.proxy)
        if resp.status_code != 200 and not (
            resp.status_code == 500
            and resp.content_type == 'application/json'):
            raise ProxyError(
                "Error from JSON-RPC client %s: %s"
                % (self.parent._url, resp.status),
                resp)
        json = loads(resp.body)
        if json.get('error') is not None:
            e = Fault(
                json['error'].get('message'),
                json['error'].get('code'),
                json['error'].get('error'),
                resp)
            raise e
        return json['result']

class ProxyError(Exception):
    """
    Raised when a request via ServerProxy breaks
    """
    def __init__(self, message, response):
        Exception.__init__(self, message)
        self.response = response

class Fault(Exception):
    """
    Raised when there is a remote error
    """
    def __init__(self, message, code, error, response):
        Exception.__init__(self, message)
        self.code = code
        self.error = error
        self.response = response
    def __str__(self):
        return 'Method error calling %s: %s\n%s' % (
            self.response.request.url,
            self.args[0],
            self.error)

class DemoObject(object):
    """
    Something interesting to attach to
    """
    def add(self, *args):
        return sum(args)
    def average(self, *args):
        return sum(args) / float(len(args))
    def divide(self, a, b):
        return a / b

def make_app(expr):
    module, expression = expr.split(':', 1)
    __import__(module)
    module = sys.modules[module]
    obj = eval(expression, module.__dict__)
    return JsonRpcApp(obj)

def main(args=None):
    import optparse
    from wsgiref import simple_server
    parser = optparse.OptionParser(
        usage='%prog [OPTIONS] MODULE:EXPRESSION')
    parser.add_option(
        '-p', '--port', default='8080',
        help='Port to serve on (default 8080)')
    parser.add_option(
        '-H', '--host', default='127.0.0.1',
        help='Host to serve on (default localhost; 0.0.0.0 to make public)')
    options, args = parser.parse_args()
    if not args or len(args) > 1:
        print 'You must give a single object reference'
        parser.print_help()
        sys.exit(2)
    app = make_app(args[0])
    server = simple_server.make_server(options.host, int(options.port), app)
    print 'Serving on http://%s:%s' % (options.host, options.port)
    server.serve_forever()
    # Try python jsonrpc.py 'jsonrpc:DemoObject()'

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_jsonrpc
if __name__ == '__main__':
    import doctest
    doctest.testfile('test_jsonrpc.txt')

########NEW FILE########
__FILENAME__ = example
import os
import re
from webob import Request, Response
from webob import exc
from tempita import HTMLTemplate

VIEW_TEMPLATE = HTMLTemplate("""\
<html>
 <head>
  <title>{{page.title}}</title>
 </head>
 <body>
<h1>{{page.title}}</h1>
{{if message}}
<div style="background-color: #99f">{{message}}</div>
{{endif}}

<div>{{page.content|html}}</div>

<hr>
<a href="{{req.url}}?action=edit">Edit</a>
 </body>
</html>
""")

EDIT_TEMPLATE = HTMLTemplate("""\
<html>
 <head>
  <title>Edit: {{page.title}}</title>
 </head>
 <body>
{{if page.exists}}
<h1>Edit: {{page.title}}</h1>
{{else}}
<h1>Create: {{page.title}}</h1>
{{endif}}

<form action="{{req.path_url}}" method="POST">
 <input type="hidden" name="mtime" value="{{page.mtime}}">
 Title: <input type="text" name="title" style="width: 70%" value="{{page.title}}"><br>
 Content: <input type="submit" value="Save">
 <a href="{{req.path_url}}">Cancel</a>
   <br>
 <textarea name="content" style="width: 100%; height: 75%" rows="40">{{page.content}}</textarea>
   <br>
 <input type="submit" value="Save">
 <a href="{{req.path_url}}">Cancel</a>
</form>
</body></html>
""")

class WikiApp(object):

    view_template = VIEW_TEMPLATE
    edit_template = EDIT_TEMPLATE

    def __init__(self, storage_dir):
        self.storage_dir = os.path.abspath(os.path.normpath(storage_dir))

    def __call__(self, environ, start_response):
        req = Request(environ)
        action = req.params.get('action', 'view')
        page = self.get_page(req.path_info)
        try:
            try:
                meth = getattr(self, 'action_%s_%s' % (action, req.method))
            except AttributeError:
                raise exc.HTTPBadRequest('No such action %r' % action)
            resp = meth(req, page)
        except exc.HTTPException, e:
            resp = e
        return resp(environ, start_response)

    def get_page(self, path):
        path = path.lstrip('/')
        if not path:
            path = 'index'
        path = os.path.join(self.storage_dir, path)
        path = os.path.normpath(path)
        if path.endswith('/'):
            path += 'index'
        if not path.startswith(self.storage_dir):
            raise exc.HTTPBadRequest("Bad path")
        path += '.html'
        return Page(path)

    def action_view_GET(self, req, page):
        if not page.exists:
            return exc.HTTPTemporaryRedirect(
                location=req.url + '?action=edit')
        if req.cookies.get('message'):
            message = req.cookies['message']
        else:
            message = None
        text = self.view_template.substitute(
            page=page, req=req, message=message)
        resp = Response(text)
        if message:
            resp.delete_cookie('message')
        else:
            resp.last_modified = page.mtime
            resp.conditional_response = True
        return resp

    def action_view_POST(self, req, page):
        submit_mtime = int(req.params.get('mtime') or '0') or None
        if page.mtime != submit_mtime:
            return exc.HTTPPreconditionFailed(
                "The page has been updated since you started editing it")
        page.set(
            title=req.params['title'],
            content=req.params['content'])
        resp = exc.HTTPSeeOther(
            location=req.path_url)
        resp.set_cookie('message', 'Page updated')
        return resp

    def action_edit_GET(self, req, page):
        text = self.edit_template.substitute(
            page=page, req=req)
        return Response(text)

class Page(object):
    def __init__(self, filename):
        self.filename = filename

    @property
    def exists(self):
        return os.path.exists(self.filename)

    @property
    def title(self):
        if not self.exists:
            # we need to guess the title
            basename = os.path.splitext(os.path.basename(self.filename))[0]
            basename = re.sub(r'[_-]', ' ', basename)
            return basename.capitalize()
        content = self.full_content
        match = re.search(r'<title>(.*?)</title>', content, re.I|re.S)
        return match.group(1)

    @property
    def full_content(self):
        f = open(self.filename, 'rb')
        try:
            return f.read()
        finally:
            f.close()

    @property
    def content(self):
        if not self.exists:
            return ''
        content = self.full_content
        match = re.search(r'<body[^>]*>(.*?)</body>', content, re.I|re.S)
        return match.group(1)

    @property
    def mtime(self):
        if not self.exists:
            return None
        else:
            return int(os.stat(self.filename).st_mtime)

    def set(self, title, content):
        dir = os.path.dirname(self.filename)
        if not os.path.exists(dir):
            os.makedirs(dir)
        new_content = """<html><head><title>%s</title></head><body>%s</body></html>""" % (
            title, content)
        f = open(self.filename, 'wb')
        f.write(new_content)
        f.close()

if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser(
        usage='%prog --port=PORT'
        )
    parser.add_option(
        '-p', '--port',
        default='8080',
        dest='port',
        type='int',
        help='Port to serve on (default 8080)')
    parser.add_option(
        '--wiki-data',
        default='./wiki',
        dest='wiki_data',
        help='Place to put wiki data into (default ./wiki/)')
    options, args = parser.parse_args()
    print 'Writing wiki pages to %s' % options.wiki_data
    app = WikiApp(options.wiki_data)
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', options.port, app)
    print 'Serving on http://localhost:%s' % options.port
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print '^C'

########NEW FILE########
__FILENAME__ = conftest
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pkg_resources
pkg_resources.require('WebOb')

########NEW FILE########
__FILENAME__ = performance_test
#!/usr/bin/env python
from webob.response import Response

def make_middleware(app):
    from repoze.profile.profiler import AccumulatingProfileMiddleware
    return AccumulatingProfileMiddleware(
        app,
        log_filename='/tmp/profile.log',
        discard_first_request=True,
        flush_at_shutdown=True,
        path='/__profile__')

def simple_app(environ, start_response):
    resp = Response('Hello world!')
    return resp(environ, start_response)

if __name__ == '__main__':
    import sys
    import os
    import signal
    if sys.argv[1:]:
        arg = sys.argv[1]
    else:
        arg = None
    if arg in ['open', 'run']:
        import subprocess
        import webbrowser
        import time
        os.environ['SHOW_OUTPUT'] = '0'
        proc = subprocess.Popen([sys.executable, __file__])
        time.sleep(1)
        subprocess.call(['ab', '-n', '1000', 'http://localhost:8080/'])
        if arg == 'open':
            webbrowser.open('http://localhost:8080/__profile__')
        print('Hit ^C to end')
        try:
            while 1:
                raw_input()
        finally:
            os.kill(proc.pid, signal.SIGKILL)
    else:
        from paste.httpserver import serve
        if os.environ.get('SHOW_OUTPUT') != '0':
            print('Note you can also use:)')
            print('  %s %s open' % (sys.executable, __file__))
            print('to run ab and open a browser (or "run" to just run ab)')
            print('Now do:')
            print('ab -n 1000 http://localhost:8080/')
            print('wget -O - http://localhost:8080/__profile__')
        serve(make_middleware(simple_app))

########NEW FILE########
__FILENAME__ = test_acceptparse
from webob.request import Request
from webob.acceptparse import Accept
from webob.acceptparse import MIMEAccept
from webob.acceptparse import NilAccept
from webob.acceptparse import NoAccept
from webob.acceptparse import accept_property
from webob.acceptparse import AcceptLanguage
from webob.acceptparse import AcceptCharset

from nose.tools import eq_, assert_raises

def test_parse_accept_badq():
    assert list(Accept.parse("value1; q=0.1.2")) == [('value1', 1)]

def test_init_accept_content_type():
    accept = Accept('text/html')
    assert accept._parsed == [('text/html', 1)]

def test_init_accept_accept_charset():
    accept = AcceptCharset('iso-8859-5, unicode-1-1;q=0.8')
    assert accept._parsed == [('iso-8859-5', 1),
                              ('unicode-1-1', 0.80000000000000004),
                              ('iso-8859-1', 1)]

def test_init_accept_accept_charset_mixedcase():
    """3.4 Character Sets
           [...]
           HTTP character sets are identified by case-insensitive tokens."""
    accept = AcceptCharset('ISO-8859-5, UNICODE-1-1;q=0.8')
    assert accept._parsed == [('iso-8859-5', 1),
                              ('unicode-1-1', 0.80000000000000004),
                              ('iso-8859-1', 1)]

def test_init_accept_accept_charset_with_iso_8859_1():
    accept = Accept('iso-8859-1')
    assert accept._parsed == [('iso-8859-1', 1)]

def test_init_accept_accept_charset_wildcard():
    accept = Accept('*')
    assert accept._parsed == [('*', 1)]

def test_init_accept_accept_language():
    accept = AcceptLanguage('da, en-gb;q=0.8, en;q=0.7')
    assert accept._parsed == [('da', 1),
                              ('en-gb', 0.80000000000000004),
                              ('en', 0.69999999999999996)]

def test_init_accept_invalid_value():
    accept = AcceptLanguage('da, q, en-gb;q=0.8')
    # The "q" value should not be there.
    assert accept._parsed == [('da', 1),
                              ('en-gb', 0.80000000000000004)]

def test_init_accept_invalid_q_value():
    accept = AcceptLanguage('da, en-gb;q=foo')
    # I can't get to cover line 40-41 (webob.acceptparse) as the regex
    # will prevent from hitting these lines (aconrad)
    assert accept._parsed == [('da', 1), ('en-gb', 1)]

def test_accept_repr():
    accept = Accept('text/html')
    assert repr(accept) == "<Accept('text/html')>"

def test_accept_str():
    accept = Accept('text/html')
    assert str(accept) == 'text/html'

def test_zero_quality():
    assert Accept('bar, *;q=0').best_match(['foo']) is None
    assert 'foo' not in Accept('*;q=0')


def test_accept_str_with_q_not_1():
    value = 'text/html;q=0.5'
    accept = Accept(value)
    assert str(accept) == value

def test_accept_str_with_q_not_1_multiple():
    value = 'text/html;q=0.5, foo/bar'
    accept = Accept(value)
    assert str(accept) == value

def test_accept_add_other_accept():
    accept = Accept('text/html') + Accept('foo/bar')
    assert str(accept) == 'text/html, foo/bar'
    accept += Accept('bar/baz;q=0.5')
    assert str(accept) == 'text/html, foo/bar, bar/baz;q=0.5'

def test_accept_add_other_list_of_tuples():
    accept = Accept('text/html')
    accept += [('foo/bar', 1)]
    assert str(accept) == 'text/html, foo/bar'
    accept += [('bar/baz', 0.5)]
    assert str(accept) == 'text/html, foo/bar, bar/baz;q=0.5'
    accept += ['she/bangs', 'the/house']
    assert str(accept) == ('text/html, foo/bar, bar/baz;q=0.5, '
                           'she/bangs, the/house')

def test_accept_add_other_dict():
    accept = Accept('text/html')
    accept += {'foo/bar': 1}
    assert str(accept) == 'text/html, foo/bar'
    accept += {'bar/baz': 0.5}
    assert str(accept) == 'text/html, foo/bar, bar/baz;q=0.5'

def test_accept_add_other_empty_str():
    accept = Accept('text/html')
    accept += ''
    assert str(accept) == 'text/html'

def test_accept_with_no_value_add_other_str():
    accept = Accept('')
    accept += 'text/html'
    assert str(accept) == 'text/html'

def test_contains():
    accept = Accept('text/html')
    assert 'text/html' in accept

def test_contains_not():
    accept = Accept('text/html')
    assert not 'foo/bar' in accept

def test_quality():
    accept = Accept('text/html')
    assert accept.quality('text/html') == 1
    accept = Accept('text/html;q=0.5')
    assert accept.quality('text/html') == 0.5

def test_quality_not_found():
    accept = Accept('text/html')
    assert accept.quality('foo/bar') is None

def test_best_match():
    accept = Accept('text/html, foo/bar')
    assert accept.best_match(['text/html', 'foo/bar']) == 'text/html'
    assert accept.best_match(['foo/bar', 'text/html']) == 'foo/bar'
    assert accept.best_match([('foo/bar', 0.5),
                              'text/html']) == 'text/html'
    assert accept.best_match([('foo/bar', 0.5),
                              ('text/html', 0.4)]) == 'foo/bar'
    assert_raises(ValueError, accept.best_match, ['text/*'])

def test_best_match_with_one_lower_q():
    accept = Accept('text/html, foo/bar;q=0.5')
    assert accept.best_match(['text/html', 'foo/bar']) == 'text/html'
    accept = Accept('text/html;q=0.5, foo/bar')
    assert accept.best_match(['text/html', 'foo/bar']) == 'foo/bar'


def test_best_match_with_complex_q():
    accept = Accept('text/html, foo/bar;q=0.55, baz/gort;q=0.59')
    assert accept.best_match(['text/html', 'foo/bar']) == 'text/html'
    accept = Accept('text/html;q=0.5, foo/bar;q=0.586, baz/gort;q=0.5966')
    assert "baz/gort;q=0.597" in str(accept)
    assert "foo/bar;q=0.586" in str(accept)
    assert "text/html;q=0.5" in str(accept)
    assert accept.best_match(['text/html', 'baz/gort']) == 'baz/gort'


def test_accept_match():
    for mask in ['*', 'text/html', 'TEXT/HTML']:
        assert 'text/html' in Accept(mask)
    assert 'text/html' not in Accept('foo/bar')

def test_accept_match_lang():
    for mask, lang in [
        ('*', 'da'),
        ('da', 'DA'),
        ('en', 'en-gb'),
        ('en-gb', 'en-gb'),
        ('en-gb', 'en'),
        ('en-gb', 'en_GB'),
    ]:
        assert lang in AcceptLanguage(mask)
    for mask, lang in [
        ('en-gb', 'en-us'),
        ('en-gb', 'fr-fr'),
        ('en-gb', 'fr'),
        ('en', 'fr-fr'),
    ]:
        assert lang not in AcceptLanguage(mask)

# NilAccept tests

def test_nil():
    nilaccept = NilAccept()
    eq_(repr(nilaccept),
        "<NilAccept: <class 'webob.acceptparse.Accept'>>"
    )
    assert not nilaccept
    assert str(nilaccept) == ''
    assert nilaccept.quality('dummy') == 0

def test_nil_add():
    nilaccept = NilAccept()
    accept = Accept('text/html')
    assert nilaccept + accept is accept
    new_accept = nilaccept + nilaccept
    assert isinstance(new_accept, accept.__class__)
    assert new_accept.header_value == ''
    new_accept = nilaccept + 'foo'
    assert isinstance(new_accept, accept.__class__)
    assert new_accept.header_value == 'foo'

def test_nil_radd():
    nilaccept = NilAccept()
    accept = Accept('text/html')
    assert isinstance('foo' + nilaccept, accept.__class__)
    assert ('foo' + nilaccept).header_value == 'foo'
    # How to test ``if isinstance(item, self.MasterClass): return item``
    # under NilAccept.__radd__ ??

def test_nil_radd_masterclass():
    # Is this "reaching into" __radd__ legit?
    nilaccept = NilAccept()
    accept = Accept('text/html')
    assert nilaccept.__radd__(accept) is accept

def test_nil_contains():
    nilaccept = NilAccept()
    assert 'anything' in nilaccept

def test_nil_best_match():
    nilaccept = NilAccept()
    assert nilaccept.best_match(['foo', 'bar']) == 'foo'
    assert nilaccept.best_match([('foo', 1), ('bar', 0.5)]) == 'foo'
    assert nilaccept.best_match([('foo', 0.5), ('bar', 1)]) == 'bar'
    assert nilaccept.best_match([('foo', 0.5), 'bar']) == 'bar'
    assert nilaccept.best_match([('foo', 0.5), 'bar'],
                                default_match=True) == 'bar'
    assert nilaccept.best_match([('foo', 0.5), 'bar'],
                                default_match=False) == 'bar'
    assert nilaccept.best_match([], default_match='fallback') == 'fallback'


# NoAccept tests
def test_noaccept_contains():
    assert 'text/plain' not in NoAccept()


# MIMEAccept tests

def test_mime_init():
    mimeaccept = MIMEAccept('image/jpg')
    assert mimeaccept._parsed == [('image/jpg', 1)]
    mimeaccept = MIMEAccept('image/png, image/jpg;q=0.5')
    assert mimeaccept._parsed == [('image/png', 1), ('image/jpg', 0.5)]
    mimeaccept = MIMEAccept('image, image/jpg;q=0.5')
    assert mimeaccept._parsed == [('image/jpg', 0.5)]
    mimeaccept = MIMEAccept('*/*')
    assert mimeaccept._parsed == [('*/*', 1)]
    mimeaccept = MIMEAccept('*/png')
    assert mimeaccept._parsed == []
    mimeaccept = MIMEAccept('image/pn*')
    assert mimeaccept._parsed == []
    mimeaccept = MIMEAccept('imag*/png')
    assert mimeaccept._parsed == []
    mimeaccept = MIMEAccept('image/*')
    assert mimeaccept._parsed == [('image/*', 1)]

def test_accept_html():
    mimeaccept = MIMEAccept('image/jpg')
    assert not mimeaccept.accept_html()
    mimeaccept = MIMEAccept('image/jpg, text/html')
    assert mimeaccept.accept_html()

def test_match():
    mimeaccept = MIMEAccept('image/jpg')
    assert mimeaccept._match('image/jpg', 'image/jpg')
    assert mimeaccept._match('image/*', 'image/jpg')
    assert mimeaccept._match('*/*', 'image/jpg')
    assert not mimeaccept._match('text/html', 'image/jpg')
    assert_raises(ValueError, mimeaccept._match, 'image/jpg', '*/*')

def test_accept_json():
    mimeaccept = MIMEAccept('text/html, *; q=.2, */*; q=.2')
    assert mimeaccept.best_match(['application/json']) == 'application/json'

def test_accept_mixedcase():
    """3.7 Media Types
           [...]
           The type, subtype, and parameter attribute names are case-
           insensitive."""
    mimeaccept = MIMEAccept('text/HtMl')
    assert mimeaccept.accept_html()

def test_match_mixedcase():
    mimeaccept = MIMEAccept('image/jpg; q=.2, Image/pNg; Q=.4, image/*; q=.05')
    assert mimeaccept.best_match(['Image/JpG']) == 'Image/JpG'
    assert mimeaccept.best_match(['image/Tiff']) == 'image/Tiff'
    assert mimeaccept.best_match(['image/Tiff', 'image/PnG', 'image/jpg']) == 'image/PnG'

def test_match_uppercase_q():
    """The relative-quality-factor "q" parameter is defined as an exact string
       in "14.1 Accept" BNF grammar"""
    mimeaccept = MIMEAccept('image/jpg; q=.4, Image/pNg; Q=.2, image/*; q=.05')
    assert mimeaccept._parsed == [('image/jpg', 0.4), ('image/png', 1), ('image/*', 0.05)]

# property tests

def test_accept_property_fget():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/', environ={'envkey': 'envval'})
    desc.fset(req, 'val')
    eq_(desc.fget(req).header_value, 'val')

def test_accept_property_fget_nil():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/')
    eq_(type(desc.fget(req)), NilAccept)

def test_accept_property_fset():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/', environ={'envkey': 'envval'})
    desc.fset(req, 'baz')
    eq_(desc.fget(req).header_value, 'baz')

def test_accept_property_fset_acceptclass():
    req = Request.blank('/', environ={'envkey': 'envval'})
    req.accept_charset = ['utf-8', 'latin-11']
    eq_(req.accept_charset.header_value, 'utf-8, latin-11, iso-8859-1')

def test_accept_property_fdel():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/', environ={'envkey': 'envval'})
    desc.fset(req, 'val')
    assert desc.fget(req).header_value == 'val'
    desc.fdel(req)
    eq_(type(desc.fget(req)), NilAccept)

########NEW FILE########
__FILENAME__ = test_byterange
from webob.byterange import Range
from webob.byterange import ContentRange
from webob.byterange import _is_content_range_valid

from nose.tools import assert_true, assert_false, eq_, assert_raises

# Range class

def test_not_satisfiable():
    range = Range.parse('bytes=-100')
    assert range.range_for_length(50) is None
    range = Range.parse('bytes=100-')
    assert range.range_for_length(50) is None

def test_range_parse():
    assert isinstance(Range.parse('bytes=0-99'), Range)
    assert isinstance(Range.parse('BYTES=0-99'), Range)
    assert isinstance(Range.parse('bytes = 0-99'), Range)
    assert isinstance(Range.parse('bytes=0 - 102'), Range)
    assert Range.parse('bytes=10-5') is None
    assert Range.parse('bytes 5-10') is None
    assert Range.parse('words=10-5') is None

def test_range_content_range_length_none():
    range = Range(0, 100)
    eq_(range.content_range(None), None)
    assert isinstance(range.content_range(1), ContentRange)
    eq_(tuple(range.content_range(1)), (0,1,1))
    eq_(tuple(range.content_range(200)), (0,100,200))

def test_range_for_length_end_is_none():
    # End is None
    range = Range(0, None)
    eq_(range.range_for_length(100), (0,100))

def test_range_for_length_end_is_none_negative_start():
    # End is None and start is negative
    range = Range(-5, None)
    eq_(range.range_for_length(100), (95,100))

def test_range_start_none():
    # Start is None
    range = Range(None, 99)
    eq_(range.range_for_length(100), None)

def test_range_str_end_none():
    range = Range(0, None)
    eq_(str(range), 'bytes=0-')

def test_range_str_end_none_negative_start():
    range = Range(-5, None)
    eq_(str(range), 'bytes=-5')

def test_range_str_1():
    range = Range(0, 100)
    eq_(str(range), 'bytes=0-99')

def test_range_repr():
    range = Range(0, 99)
    assert_true(range.__repr__(), '<Range bytes 0-98>')


# ContentRange class

def test_contentrange_bad_input():
    assert_raises(ValueError, ContentRange, None, 99, None)

def test_contentrange_repr():
    contentrange = ContentRange(0, 99, 100)
    assert_true(repr(contentrange), '<ContentRange bytes 0-98/100>')

def test_contentrange_str():
    contentrange = ContentRange(0, 99, None)
    eq_(str(contentrange), 'bytes 0-98/*')
    contentrange = ContentRange(None, None, 100)
    eq_(str(contentrange), 'bytes */100')

def test_contentrange_iter():
    contentrange = ContentRange(0, 99, 100)
    assert_true(type(contentrange.__iter__()), iter)
    assert_true(ContentRange.parse('bytes 0-99/100').__class__, ContentRange)
    eq_(ContentRange.parse(None), None)
    eq_(ContentRange.parse('0-99 100'), None)
    eq_(ContentRange.parse('bytes 0-99 100'), None)
    eq_(ContentRange.parse('bytes 0-99/xxx'), None)
    eq_(ContentRange.parse('bytes 0 99/100'), None)
    eq_(ContentRange.parse('bytes */100').__class__, ContentRange)
    eq_(ContentRange.parse('bytes A-99/100'), None)
    eq_(ContentRange.parse('bytes 0-B/100'), None)
    eq_(ContentRange.parse('bytes 99-0/100'), None)
    eq_(ContentRange.parse('bytes 0 99/*'), None)

# _is_content_range_valid function

def test_is_content_range_valid():
    assert not _is_content_range_valid( None, 99, 90)
    assert not _is_content_range_valid( 99, None, 90)
    assert _is_content_range_valid(None, None, 90)
    assert not _is_content_range_valid(None, 99, 90)
    assert _is_content_range_valid(0, 99, None)
    assert not _is_content_range_valid(0, 99, 90, response=True)
    assert _is_content_range_valid(0, 99, 90)

########NEW FILE########
__FILENAME__ = test_cachecontrol
from nose.tools import eq_
from nose.tools import raises
import unittest


def test_cache_control_object_max_age_None():
    from webob.cachecontrol import CacheControl
    cc = CacheControl({}, 'a')
    cc.properties['max-age'] = None
    eq_(cc.max_age, -1)


class TestUpdateDict(unittest.TestCase):

    def setUp(self):
        self.call_queue = []
        def callback(args):
            self.call_queue.append("Called with: %s" % repr(args))
        self.callback = callback

    def make_one(self, callback):
        from webob.cachecontrol import UpdateDict
        ud = UpdateDict()
        ud.updated = callback
        return ud

    def test_clear(self):
        newone = self.make_one(self.callback)
        newone['first'] = 1
        assert len(newone) == 1
        newone.clear()
        assert len(newone) == 0

    def test_update(self):
        newone = self.make_one(self.callback)
        d = {'one' : 1 }
        newone.update(d)
        assert newone == d

    def test_set_delete(self):
        newone = self.make_one(self.callback)
        newone['first'] = 1
        assert len(self.call_queue) == 1
        assert self.call_queue[-1] == "Called with: {'first': 1}"

        del newone['first']
        assert len(self.call_queue) == 2
        assert self.call_queue[-1] == 'Called with: {}'

    def test_setdefault(self):
        newone = self.make_one(self.callback)
        assert newone.setdefault('haters', 'gonna-hate') == 'gonna-hate'
        assert len(self.call_queue) == 1
        assert self.call_queue[-1] == "Called with: {'haters': 'gonna-hate'}", self.call_queue[-1]

        # no effect if failobj is not set
        assert newone.setdefault('haters', 'gonna-love') == 'gonna-hate'
        assert len(self.call_queue) == 1

    def test_pop(self):
        newone = self.make_one(self.callback)
        newone['first'] = 1
        newone.pop('first')
        assert len(self.call_queue) == 2
        assert self.call_queue[-1] == 'Called with: {}', self.call_queue[-1]

    def test_popitem(self):
        newone = self.make_one(self.callback)
        newone['first'] = 1
        assert newone.popitem() == ('first', 1)
        assert len(self.call_queue) == 2
        assert self.call_queue[-1] == 'Called with: {}', self.call_queue[-1]

    def test_callback_args(self):
        assert True
        #assert False


class TestExistProp(unittest.TestCase):
    """
    Test webob.cachecontrol.exists_property
    """

    def setUp(self):
        pass

    def make_one(self):
        from webob.cachecontrol import exists_property

        class Dummy(object):
            properties = dict(prop=1)
            type = 'dummy'
            prop = exists_property('prop', 'dummy')
            badprop = exists_property('badprop', 'big_dummy')

        return Dummy

    def test_get_on_class(self):
        from webob.cachecontrol import exists_property
        Dummy = self.make_one()
        assert isinstance(Dummy.prop, exists_property), Dummy.prop

    def test_get_on_instance(self):
        obj = self.make_one()()
        assert obj.prop is True

    @raises(AttributeError)
    def test_type_mismatch_raise(self):
        obj = self.make_one()()
        obj.badprop = True

    def test_set_w_value(self):
        obj = self.make_one()()
        obj.prop = True
        assert obj.prop is True
        assert obj.properties['prop'] is None

    def test_del_value(self):
        obj = self.make_one()()
        del obj.prop
        assert not 'prop' in obj.properties


class TestValueProp(unittest.TestCase):
    """
    Test webob.cachecontrol.exists_property
    """

    def setUp(self):
        pass

    def make_one(self):
        from webob.cachecontrol import value_property

        class Dummy(object):
            properties = dict(prop=1)
            type = 'dummy'
            prop = value_property('prop', 'dummy')
            badprop = value_property('badprop', 'big_dummy')

        return Dummy

    def test_get_on_class(self):
        from webob.cachecontrol import value_property
        Dummy = self.make_one()
        assert isinstance(Dummy.prop, value_property), Dummy.prop

    def test_get_on_instance(self):
        dummy = self.make_one()()
        assert dummy.prop, dummy.prop
        #assert isinstance(Dummy.prop, value_property), Dummy.prop

    def test_set_on_instance(self):
        dummy = self.make_one()()
        dummy.prop = "new"
        assert dummy.prop == "new", dummy.prop
        assert dummy.properties['prop'] == "new", dict(dummy.properties)

    def test_set_on_instance_bad_attribute(self):
        dummy = self.make_one()()
        dummy.prop = "new"
        assert dummy.prop == "new", dummy.prop
        assert dummy.properties['prop'] == "new", dict(dummy.properties)

    def test_set_wrong_type(self):
        from webob.cachecontrol import value_property
        class Dummy(object):
            properties = dict(prop=1, type='fail')
            type = 'dummy'
            prop = value_property('prop', 'dummy', type='failingtype')
        dummy = Dummy()
        def assign():
            dummy.prop = 'foo'
        self.assertRaises(AttributeError, assign)

    def test_set_type_true(self):
        dummy = self.make_one()()
        dummy.prop = True
        self.assertEqual(dummy.prop, None)

    def test_set_on_instance_w_default(self):
        dummy = self.make_one()()
        dummy.prop = "dummy"
        assert dummy.prop == "dummy", dummy.prop
        #@@ this probably needs more tests

    def test_del(self):
        dummy = self.make_one()()
        dummy.prop = 'Ian Bicking likes to skip'
        del dummy.prop
        assert dummy.prop == "dummy", dummy.prop


def test_copy_cc():
    from webob.cachecontrol import CacheControl
    cc = CacheControl({'header':'%', "msg":'arewerichyet?'}, 'request')
    cc2 = cc.copy()
    assert cc.properties is not cc2.properties
    assert cc.type is cc2.type

# 212

def test_serialize_cache_control_emptydict():
    from webob.cachecontrol import serialize_cache_control
    result = serialize_cache_control(dict())
    assert result == ''

def test_serialize_cache_control_cache_control_object():
    from webob.cachecontrol import serialize_cache_control, CacheControl
    result = serialize_cache_control(CacheControl({}, 'request'))
    assert result == ''

def test_serialize_cache_control_object_with_headers():
    from webob.cachecontrol import serialize_cache_control, CacheControl
    result = serialize_cache_control(CacheControl({'header':'a'}, 'request'))
    assert result == 'header=a'

def test_serialize_cache_control_value_is_None():
    from webob.cachecontrol import serialize_cache_control, CacheControl
    result = serialize_cache_control(CacheControl({'header':None}, 'request'))
    assert result == 'header'

def test_serialize_cache_control_value_needs_quote():
    from webob.cachecontrol import serialize_cache_control, CacheControl
    result = serialize_cache_control(CacheControl({'header':'""'}, 'request'))
    assert result == 'header=""""'

class TestCacheControl(unittest.TestCase):
    def make_one(self, props, typ):
        from webob.cachecontrol import CacheControl
        return CacheControl(props, typ)

    def test_ctor(self):
        cc = self.make_one({'a':1}, 'typ')
        self.assertEqual(cc.properties, {'a':1})
        self.assertEqual(cc.type, 'typ')

    def test_parse(self):
        from webob.cachecontrol import CacheControl
        cc = CacheControl.parse("public, max-age=315360000")
        self.assertEqual(type(cc), CacheControl)
        self.assertEqual(cc.max_age, 315360000)
        self.assertEqual(cc.public, True)

    def test_parse_updates_to(self):
        from webob.cachecontrol import CacheControl
        def foo(arg): return { 'a' : 1 }
        cc = CacheControl.parse("public, max-age=315360000", updates_to=foo)
        self.assertEqual(type(cc), CacheControl)
        self.assertEqual(cc.max_age, 315360000)

    def test_parse_valueerror_int(self):
        from webob.cachecontrol import CacheControl
        def foo(arg): return { 'a' : 1 }
        cc = CacheControl.parse("public, max-age=abc")
        self.assertEqual(type(cc), CacheControl)
        self.assertEqual(cc.max_age, 'abc')

    def test_repr(self):
        cc = self.make_one({'a':'1'}, 'typ')
        result = repr(cc)
        self.assertEqual(result, "<CacheControl 'a=1'>")

########NEW FILE########
__FILENAME__ = test_client
import unittest
import io
import socket

class TestSendRequest(unittest.TestCase):
    def _getTargetClass(self):
        from webob.client import SendRequest
        return SendRequest

    def _makeOne(self, **kw):
        cls = self._getTargetClass()
        return cls(**kw)

    def _makeEnviron(self, extra=None):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_NAME':'localhost',
            'HTTP_HOST':'localhost:80',
            'SERVER_PORT':'80',
            'wsgi.input':io.BytesIO(),
            'CONTENT_LENGTH':0,
            'REQUEST_METHOD':'GET',
            }
        if extra is not None:
            environ.update(extra)
        return environ

    def test___call___unknown_scheme(self):
        environ = self._makeEnviron({'wsgi.url_scheme':'abc'})
        inst = self._makeOne()
        self.assertRaises(ValueError, inst, environ, None)

    def test___call___gardenpath(self):
        environ = self._makeEnviron()
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])

    def test___call___no_servername_no_http_host(self):
        environ = self._makeEnviron()
        del environ['SERVER_NAME']
        del environ['HTTP_HOST']
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        self.assertRaises(ValueError, inst, environ, None)

    def test___call___no_servername_colon_not_in_host_http(self):
        environ = self._makeEnviron()
        del environ['SERVER_NAME']
        environ['HTTP_HOST'] = 'localhost'
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])
        self.assertEqual(environ['SERVER_NAME'], 'localhost')
        self.assertEqual(environ['SERVER_PORT'], '80')

    def test___call___no_servername_colon_not_in_host_https(self):
        environ = self._makeEnviron()
        del environ['SERVER_NAME']
        environ['HTTP_HOST'] = 'localhost'
        environ['wsgi.url_scheme'] = 'https'
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPSConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])
        self.assertEqual(environ['SERVER_NAME'], 'localhost')
        self.assertEqual(environ['SERVER_PORT'], '443')

    def test___call___no_content_length(self):
        environ = self._makeEnviron()
        del environ['CONTENT_LENGTH']
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])

    def test___call___with_webob_client_timeout_and_timeout_supported(self):
        environ = self._makeEnviron()
        environ['webob.client.timeout'] = 10
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])
        self.assertEqual(conn_factory.kw, {'timeout':10})

    def test___call___bad_content_length(self):
        environ = self._makeEnviron({'CONTENT_LENGTH':'abc'})
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])

    def test___call___with_socket_timeout(self):
        environ = self._makeEnviron()
        response = socket.timeout()
        response.msg = 'msg'
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '504 Gateway Timeout')
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertTrue(list(iterable)[0].startswith(b'504'))

    def test___call___with_socket_error_neg2(self):
        environ = self._makeEnviron()
        response = socket.error(-2)
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '502 Bad Gateway')
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertTrue(list(iterable)[0].startswith(b'502'))

    def test___call___with_socket_error_ENODATA(self):
        import errno
        environ = self._makeEnviron()
        if not hasattr(errno, 'ENODATA'):
            # no ENODATA on win
            return
        response = socket.error(errno.ENODATA)
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '502 Bad Gateway')
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertTrue(list(iterable)[0].startswith(b'502'))

    def test___call___with_socket_error_unknown(self):
        environ = self._makeEnviron()
        response = socket.error('nope')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '502 Bad Gateway')
            inst.start_response_called = True
        self.assertRaises(socket.error, inst, environ, start_response)

    def test___call___nolength(self):
        environ = self._makeEnviron()
        response = DummyResponse('msg', None)
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])
        self.assertEqual(response.length, None)

class DummyMessage(object):
    def __init__(self, msg):
        self.msg = msg
        self.headers = self._headers = {}

class DummyResponse(object):
    def __init__(self, msg, headerval='10'):
        self.msg = DummyMessage(msg)
        self.status = '200'
        self.reason = 'OK'
        self.headerval = headerval

    def getheader(self, name):
        return self.headerval

    def read(self, length=None):
        self.length = length
        return b'foo'

class DummyConnectionFactory(object):
    def __init__(self, result=None):
        self.result = result
        self.closed = False

    def __call__(self, hostport, **kw):
        self.hostport = hostport
        self.kw = kw
        self.request = DummyRequestFactory(hostport, **kw)
        return self

    def getresponse(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def close(self):
        self.closed = True

class DummyRequestFactory(object):
    def __init__(self, hostport, **kw):
        self.hostport = hostport
        self.kw = kw

    def __call__(self, method, path, body, headers):
        return self

########NEW FILE########
__FILENAME__ = test_client_functional
import time
import urllib
from webob import Request, Response
from webob.dec import wsgify
from webob.client import SendRequest
from .test_in_wsgiref import serve
from nose.tools import assert_raises


@wsgify
def simple_app(req):
    data = {'headers': dict(req.headers),
            'body': req.text,
            'method': req.method,
            }
    return Response(json=data)


def test_client(client_app=None):
    with serve(simple_app) as server:
        req = Request.blank(server.url, method='POST', content_type='application/json',
                            json={'test': 1})
        resp = req.send(client_app)
        assert resp.status_code == 200, resp.status
        assert resp.json['headers']['Content-Type'] == 'application/json'
        assert resp.json['method'] == 'POST'
        # Test that these values get filled in:
        del req.environ['SERVER_NAME']
        del req.environ['SERVER_PORT']
        resp = req.send(client_app)
        assert resp.status_code == 200, resp.status
        req = Request.blank(server.url)
        del req.environ['SERVER_NAME']
        del req.environ['SERVER_PORT']
        assert req.send(client_app).status_code == 200
        req.headers['Host'] = server.url.lstrip('http://')
        del req.environ['SERVER_NAME']
        del req.environ['SERVER_PORT']
        resp = req.send(client_app)
        assert resp.status_code == 200, resp.status
        del req.environ['SERVER_NAME']
        del req.environ['SERVER_PORT']
        del req.headers['Host']
        assert req.environ.get('SERVER_NAME') is None
        assert req.environ.get('SERVER_PORT') is None
        assert req.environ.get('HTTP_HOST') is None
        assert_raises(ValueError, req.send, client_app)
        req = Request.blank(server.url)
        req.environ['CONTENT_LENGTH'] = 'not a number'
        assert req.send(client_app).status_code == 200


def no_length_app(environ, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    return [b'ok']


def test_no_content_length(client_app=None):
    with serve(no_length_app) as server:
        req = Request.blank(server.url)
        resp = req.send(client_app)
        assert resp.status_code == 200, resp.status


@wsgify
def cookie_app(req):
    resp = Response('test')
    resp.headers.add('Set-Cookie', 'a=b')
    resp.headers.add('Set-Cookie', 'c=d')
    resp.headerlist.append(('X-Crazy', 'value\r\n  continuation'))
    return resp


def test_client_cookies(client_app=None):
    with serve(cookie_app) as server:
        req = Request.blank(server.url + '/?test')
        resp = req.send(client_app)
        assert resp.headers.getall('Set-Cookie') == ['a=b', 'c=d']
        assert resp.headers['X-Crazy'] == 'value, continuation', repr(resp.headers['X-Crazy'])


@wsgify
def slow_app(req):
    time.sleep(2)
    return Response('ok')


def test_client_slow(client_app=None):
    if client_app is None:
        client_app = SendRequest()
    if not client_app._timeout_supported(client_app.HTTPConnection):
        # timeout isn't supported
        return
    with serve(slow_app) as server:
        req = Request.blank(server.url)
        req.environ['webob.client.timeout'] = 0.1
        resp = req.send(client_app)
        assert resp.status_code == 504, resp.status

########NEW FILE########
__FILENAME__ = test_compat
import unittest

from webob.compat import text_type

class text_Tests(unittest.TestCase):
    def _callFUT(self, *arg, **kw):
        from webob.compat import text_
        return text_(*arg, **kw)

    def test_binary(self):
        result = self._callFUT(b'123')
        self.assertTrue(isinstance(result, text_type))
        self.assertEqual(result, text_type(b'123', 'ascii'))

    def test_binary_alternate_decoding(self):
        result = self._callFUT(b'La Pe\xc3\xb1a', 'utf-8')
        self.assertTrue(isinstance(result, text_type))
        self.assertEqual(result, text_type(b'La Pe\xc3\xb1a', 'utf-8'))

    def test_binary_decoding_error(self):
        self.assertRaises(UnicodeDecodeError, self._callFUT, b'\xff', 'utf-8')

    def test_text(self):
        result = self._callFUT(text_type(b'123', 'ascii'))
        self.assertTrue(isinstance(result, text_type))
        self.assertEqual(result, text_type(b'123', 'ascii'))

class bytes_Tests(unittest.TestCase):
    def _callFUT(self, *arg, **kw):
        from webob.compat import bytes_
        return bytes_(*arg, **kw)

    def test_binary(self):
        result = self._callFUT(b'123')
        self.assertTrue(isinstance(result, bytes))
        self.assertEqual(result, b'123')

    def test_text(self):
        val = text_type(b'123', 'ascii')
        result = self._callFUT(val)
        self.assertTrue(isinstance(result, bytes))
        self.assertEqual(result, b'123')

    def test_text_alternate_encoding(self):
        val = text_type(b'La Pe\xc3\xb1a', 'utf-8')
        result = self._callFUT(val, 'utf-8')
        self.assertTrue(isinstance(result, bytes))
        self.assertEqual(result, b'La Pe\xc3\xb1a')

########NEW FILE########
__FILENAME__ = test_cookies
# -*- coding: utf-8 -*-
from datetime import timedelta
from webob import cookies
from webob.compat import text_
from nose.tools import eq_
import unittest
from webob.compat import native_
from webob.compat import PY3

def test_cookie_empty():
    c = cookies.Cookie() # empty cookie
    eq_(repr(c), '<Cookie: []>')

def test_cookie_one_value():
    c = cookies.Cookie('dismiss-top=6')
    vals = list(c.values())
    eq_(len(vals), 1)
    eq_(vals[0].name, b'dismiss-top')
    eq_(vals[0].value, b'6')

def test_cookie_one_value_with_trailing_semi():
    c = cookies.Cookie('dismiss-top=6;')
    vals = list(c.values())
    eq_(len(vals), 1)
    eq_(vals[0].name, b'dismiss-top')
    eq_(vals[0].value, b'6')
    c = cookies.Cookie('dismiss-top=6;')

def test_cookie_escaped_unquoted():
    eq_(list(cookies.parse_cookie('x=\\040')), [(b'x', b' ')])

def test_cookie_complex():
    c = cookies.Cookie('dismiss-top=6; CP=null*, '\
                       'PHPSESSID=0a539d42abc001cdc762809248d4beed, a="42,"')
    d = lambda v: v.decode('ascii')
    c_dict = dict((d(k),d(v.value)) for k,v in c.items())
    eq_(c_dict, {'a': '42,',
        'CP': 'null*',
        'PHPSESSID': '0a539d42abc001cdc762809248d4beed',
        'dismiss-top': '6'
    })

def test_cookie_complex_serialize():
    c = cookies.Cookie('dismiss-top=6; CP=null*, '\
                       'PHPSESSID=0a539d42abc001cdc762809248d4beed, a="42,"')
    eq_(c.serialize(),
        'CP=null*; PHPSESSID=0a539d42abc001cdc762809248d4beed; a="42\\054"; '
        'dismiss-top=6')

def test_cookie_load_multiple():
    c = cookies.Cookie('a=1; Secure=true')
    vals = list(c.values())
    eq_(len(vals), 1)
    eq_(c[b'a'][b'secure'], b'true')

def test_cookie_secure():
    c = cookies.Cookie()
    c[text_('foo')] = b'bar'
    c[b'foo'].secure = True
    eq_(c.serialize(), 'foo=bar; secure')

def test_cookie_httponly():
    c = cookies.Cookie()
    c['foo'] = b'bar'
    c[b'foo'].httponly = True
    eq_(c.serialize(), 'foo=bar; HttpOnly')

def test_cookie_reserved_keys():
    c = cookies.Cookie('dismiss-top=6; CP=null*; $version=42; a=42')
    assert '$version' not in c
    c = cookies.Cookie('$reserved=42; a=$42')
    eq_(list(c.keys()), [b'a'])

def test_serialize_cookie_date():
    """
        Testing webob.cookies.serialize_cookie_date.
        Missing scenarios:
            * input value is an str, should be returned verbatim
            * input value is an int, should be converted to timedelta and we
              should continue the rest of the process
    """
    eq_(cookies.serialize_cookie_date(b'Tue, 04-Jan-2011 13:43:50 GMT'),
        b'Tue, 04-Jan-2011 13:43:50 GMT')
    eq_(cookies.serialize_cookie_date(text_('Tue, 04-Jan-2011 13:43:50 GMT')),
        b'Tue, 04-Jan-2011 13:43:50 GMT')
    eq_(cookies.serialize_cookie_date(None), None)
    cdate_delta = cookies.serialize_cookie_date(timedelta(seconds=10))
    cdate_int = cookies.serialize_cookie_date(10)
    eq_(cdate_delta, cdate_int)

def test_ch_unquote():
    eq_(cookies._unquote(b'"hello world'), b'"hello world')
    eq_(cookies._unquote(b'hello world'), b'hello world')
    eq_(cookies._unquote(b'"hello world"'), b'hello world')
    eq_(cookies._value_quote(b'hello world'), b'"hello world"')
    # quotation mark escaped w/ backslash is unquoted correctly (support
    # pre webob 1.3 cookies)
    eq_(cookies._unquote(b'"\\""'), b'"')
    # we also are able to unquote the newer \\042 serialization of quotation
    # mark
    eq_(cookies._unquote(b'"\\042"'), b'"')
    # but when we generate a new cookie, quote using normal octal quoting
    # rules
    eq_(cookies._value_quote(b'"'), b'"\\042"')
    # backslash escaped w/ backslash is unquoted correctly (support
    # pre webob 1.3 cookies)
    eq_(cookies._unquote(b'"\\\\"'), b'\\')
    # we also are able to unquote the newer \\134 serialization of backslash
    eq_(cookies._unquote(b'"\\134"'), b'\\')
    # but when we generate a new cookie, quote using normal octal quoting
    # rules
    eq_(cookies._value_quote(b'\\'), b'"\\134"')
    # misc byte escaped as octal
    eq_(cookies._unquote(b'"\\377"'), b'\xff')
    eq_(cookies._value_quote(b'\xff'), b'"\\377"')
    # combination
    eq_(cookies._unquote(b'"a\\"\\377"'), b'a"\xff')
    eq_(cookies._value_quote(b'a"\xff'), b'"a\\042\\377"')

def test_cookie_invalid_name():
    c = cookies.Cookie()
    c['La Pe\xc3\xb1a'] = '1'
    eq_(len(c), 0)

def test_morsel_serialize_with_expires():
    morsel = cookies.Morsel(b'bleh', b'blah')
    morsel.expires = b'Tue, 04-Jan-2011 13:43:50 GMT'
    result = morsel.serialize()
    eq_(result, 'bleh=blah; expires=Tue, 04-Jan-2011 13:43:50 GMT')

def test_serialize_max_age_timedelta():
    import datetime
    val = datetime.timedelta(86400)
    result = cookies.serialize_max_age(val)
    eq_(result, b'7464960000')

def test_serialize_max_age_int():
    val = 86400
    result = cookies.serialize_max_age(val)
    eq_(result, b'86400')

def test_serialize_max_age_str():
    val = '86400'
    result = cookies.serialize_max_age(val)
    eq_(result, b'86400')

def test_escape_comma_semi_dquote():
    c = cookies.Cookie()
    c['x'] = b'";,"'
    eq_(c.serialize(True), r'x="\042\073\054\042"')

def test_parse_qmark_in_val():
    v = r'x="\"\073\054\""; expires=Sun, 12-Jun-2011 23:16:01 GMT'
    c = cookies.Cookie(v)
    eq_(c[b'x'].value, b'";,"')
    eq_(c[b'x'].expires, b'Sun, 12-Jun-2011 23:16:01 GMT')

def test_morsel_repr():
    v = cookies.Morsel(b'a', b'b')
    result = repr(v)
    eq_(result, "<Morsel: a='b'>")

def test_strings_differ():
    from webob.util import strings_differ

    eq_(strings_differ('test1', 'test'), True)

class TestRequestCookies(unittest.TestCase):
    def _makeOne(self, environ):
        from webob.cookies import RequestCookies
        return RequestCookies(environ)

    def test_get_no_cache_key_in_environ_no_http_cookie_header(self):
        environ = {}
        inst = self._makeOne(environ)
        self.assertEqual(inst.get('a'), None)
        parsed = environ['webob._parsed_cookies']
        self.assertEqual(parsed, ({}, ''))

    def test_get_no_cache_key_in_environ_has_http_cookie_header(self):
        header ='a=1; b=2'
        environ = {'HTTP_COOKIE':header}
        inst = self._makeOne(environ)
        self.assertEqual(inst.get('a'), '1')
        parsed = environ['webob._parsed_cookies'][0]
        self.assertEqual(parsed['a'], '1')
        self.assertEqual(parsed['b'], '2')
        self.assertEqual(environ['HTTP_COOKIE'], header) # no change

    def test_get_cache_key_in_environ_no_http_cookie_header(self):
        environ = {'webob._parsed_cookies':({}, '')}
        inst = self._makeOne(environ)
        self.assertEqual(inst.get('a'), None)
        parsed = environ['webob._parsed_cookies']
        self.assertEqual(parsed, ({}, ''))

    def test_get_cache_key_in_environ_has_http_cookie_header(self):
        header ='a=1; b=2'
        environ = {'HTTP_COOKIE':header, 'webob._parsed_cookies':({}, '')}
        inst = self._makeOne(environ)
        self.assertEqual(inst.get('a'), '1')
        parsed = environ['webob._parsed_cookies'][0]
        self.assertEqual(parsed['a'], '1')
        self.assertEqual(parsed['b'], '2')
        self.assertEqual(environ['HTTP_COOKIE'], header) # no change

    def test_get_missing_with_default(self):
        environ = {}
        inst = self._makeOne(environ)
        self.assertEqual(inst.get('a', ''), '')

    def test___setitem__name_not_string_type(self):
        inst = self._makeOne({})
        self.assertRaises(TypeError, inst.__setitem__, None, 1)

    def test___setitem__name_not_encodeable_to_ascii(self):
        name = native_(b'La Pe\xc3\xb1a', 'utf-8')
        inst = self._makeOne({})
        self.assertRaises(TypeError, inst.__setitem__, name, 'abc')

    def test___setitem__name_not_rfc2109_valid(self):
        name = '$a'
        inst = self._makeOne({})
        self.assertRaises(TypeError, inst.__setitem__, name, 'abc')

    def test___setitem__value_not_string_type(self):
        inst = self._makeOne({})
        self.assertRaises(ValueError, inst.__setitem__, 'a', None)

    def test___setitem__value_not_utf_8_decodeable(self):
        value = text_(b'La Pe\xc3\xb1a', 'utf-8')
        value = value.encode('utf-16')
        inst = self._makeOne({})
        self.assertRaises(ValueError, inst.__setitem__, 'a', value)

    def test__setitem__success_no_existing_headers(self):
        value = native_(b'La Pe\xc3\xb1a', 'utf-8')
        environ = {}
        inst = self._makeOne(environ)
        inst['a'] = value
        self.assertEqual(environ['HTTP_COOKIE'], 'a="La Pe\\303\\261a"')

    def test__setitem__success_append(self):
        value = native_(b'La Pe\xc3\xb1a', 'utf-8')
        environ = {'HTTP_COOKIE':'a=1; b=2'}
        inst = self._makeOne(environ)
        inst['c'] = value
        self.assertEqual(
            environ['HTTP_COOKIE'], 'a=1; b=2; c="La Pe\\303\\261a"')

    def test__setitem__success_replace(self):
        environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
        inst = self._makeOne(environ)
        inst['b'] = 'abc'
        self.assertEqual(environ['HTTP_COOKIE'], 'a=1; b=abc; c=3')
        inst['c'] = '4'
        self.assertEqual(environ['HTTP_COOKIE'], 'a=1; b=abc; c=4')

    def test__delitem__fail_no_http_cookie(self):
        environ = {}
        inst = self._makeOne(environ)
        self.assertRaises(KeyError, inst.__delitem__, 'a')
        self.assertEqual(environ, {})

    def test__delitem__fail_with_http_cookie(self):
        environ = {'HTTP_COOKIE':''}
        inst = self._makeOne(environ)
        self.assertRaises(KeyError, inst.__delitem__, 'a')
        self.assertEqual(environ, {'HTTP_COOKIE':''})

    def test__delitem__success(self):
        environ = {'HTTP_COOKIE':'a=1'}
        inst = self._makeOne(environ)
        del inst['a']
        self.assertEqual(environ['HTTP_COOKIE'], '')
        self.assertEqual(inst._cache, {})

    def test_keys(self):
        environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
        inst = self._makeOne(environ)
        self.assertEqual(sorted(list(inst.keys())), ['a', 'b', 'c'])

    def test_values(self):
        val = text_(b'La Pe\xc3\xb1a', 'utf-8')
        environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
        inst = self._makeOne(environ)
        self.assertEqual(sorted(list(inst.values())), ['1', '3', val])

    def test_items(self):
        val = text_(b'La Pe\xc3\xb1a', 'utf-8')
        environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
        inst = self._makeOne(environ)
        self.assertEqual(sorted(list(inst.items())),
                         [('a', '1'), ('b', val), ('c', '3')])

    if not PY3:
        def test_iterkeys(self):
            environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
            inst = self._makeOne(environ)
            self.assertEqual(sorted(list(inst.iterkeys())), ['a', 'b', 'c'])

        def test_itervalues(self):
            val = text_(b'La Pe\xc3\xb1a', 'utf-8')
            environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
            inst = self._makeOne(environ)
            self.assertEqual(sorted(list(inst.itervalues())), ['1', '3', val])

        def test_iteritems(self):
            val = text_(b'La Pe\xc3\xb1a', 'utf-8')
            environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
            inst = self._makeOne(environ)
            self.assertEqual(sorted(list(inst.iteritems())),
                             [('a', '1'), ('b', val), ('c', '3')])

    def test___contains__(self):
        environ = {'HTTP_COOKIE':'a=1'}
        inst = self._makeOne(environ)
        self.assertTrue('a' in inst)
        self.assertFalse('b' in inst)

    def test___iter__(self):
        environ = {'HTTP_COOKIE':'a=1; b=2; c=3'}
        inst = self._makeOne(environ)
        self.assertEqual(sorted(list(iter(inst))), ['a', 'b', 'c'])

    def test___len__(self):
        environ = {'HTTP_COOKIE':'a=1; b=2; c=3'}
        inst = self._makeOne(environ)
        self.assertEqual(len(inst), 3)
        del inst['a']
        self.assertEqual(len(inst), 2)

    def test_clear(self):
        environ = {'HTTP_COOKIE':'a=1; b=2; c=3'}
        inst = self._makeOne(environ)
        inst.clear()
        self.assertEqual(environ['HTTP_COOKIE'], '')
        self.assertEqual(inst.get('a'), None)

    def test___repr__(self):
        environ = {'HTTP_COOKIE':'a=1; b=2; c=3'}
        inst = self._makeOne(environ)
        r = repr(inst)
        self.assertTrue(r.startswith(
            '<RequestCookies (dict-like) with values '))
        self.assertTrue(r.endswith('>'))


class CookieMakeCookie(unittest.TestCase):
    def makeOne(self, name, value, **kw):
        from webob.cookies import make_cookie
        return make_cookie(name, value, **kw)

    def test_make_cookie_max_age(self):
        cookie = self.makeOne('test_cookie', 'value', max_age=500)

        self.assertTrue('test_cookie=value' in cookie)
        self.assertTrue('Max-Age=500;' in cookie)
        self.assertTrue('expires' in cookie)

    def test_make_cookie_max_age_timedelta(self):
        from datetime import timedelta
        cookie = self.makeOne('test_cookie', 'value',
                              max_age=timedelta(seconds=500))

        self.assertTrue('test_cookie=value' in cookie)
        self.assertTrue('Max-Age=500;' in cookie)
        self.assertTrue('expires' in cookie)

    def test_make_cookie_comment(self):
        cookie = self.makeOne('test_cookie', 'value', comment='lolwhy')

        self.assertTrue('test_cookie=value' in cookie)
        self.assertTrue('Comment=lolwhy' in cookie)

    def test_make_cookie_path(self):
        cookie = self.makeOne('test_cookie', 'value', path='/foo/bar/baz')

        self.assertTrue('test_cookie=value' in cookie)
        self.assertTrue('Path=/foo/bar/baz' in cookie)

class CommonCookieProfile(unittest.TestCase):
    def makeDummyRequest(self, **kw):
        class Dummy(object):
            def __init__(self, **kwargs):
                self.__dict__.update(**kwargs)
        d = Dummy(**kw)
        d.response = Dummy()
        d.response.headerlist = list()
        return d

    def makeOneRequest(self):
        request = self.makeDummyRequest(environ=dict())
        request.environ['HTTP_HOST'] = 'www.example.net'
        request.cookies = dict()

        return request


class CookieProfileTest(CommonCookieProfile):
    def makeOne(self, name='uns', **kw):
        if 'request' in kw:
            request = kw['request']
            del kw['request']
        else:
            request = self.makeOneRequest()

        from webob.cookies import CookieProfile
        return CookieProfile(name, **kw)(request)

    def test_cookie_creation(self):
        cookie = self.makeOne()

        from webob.cookies import CookieProfile
        self.assertTrue(isinstance(cookie, CookieProfile))

    def test_cookie_name(self):
        cookie = self.makeOne()

        cookie_list = cookie.get_headers("test")

        for cookie in cookie_list:
            self.assertTrue(cookie[1].startswith('uns'))
            self.assertFalse('uns="";' in cookie[1])

    def test_cookie_no_request(self):
        from webob.cookies import CookieProfile
        cookie = CookieProfile('uns')

        self.assertRaises(ValueError, cookie.get_value)

    def test_get_value_serializer_raises_value_error(self):
        class RaisingSerializer(object):
            def loads(self, val):
                raise ValueError('foo')
        cookie = self.makeOne(serializer=RaisingSerializer())
        self.assertEqual(cookie.get_value(), None)

class SignedCookieProfileTest(CommonCookieProfile):
    def makeOne(self, secret='seekrit', salt='salty', name='uns', **kw):
        if 'request' in kw:
            request = kw['request']
            del kw['request']
        else:
            request = self.makeOneRequest()

        from webob.cookies import SignedCookieProfile as CookieProfile
        return CookieProfile(secret, salt, name, **kw)(request)


    def test_cookie_name(self):
        cookie = self.makeOne()

        cookie_list = cookie.get_headers("test")

        for cookie in cookie_list:
            self.assertTrue(cookie[1].startswith('uns'))
            self.assertFalse('uns="";' in cookie[1])

    def test_cookie_expire(self):
        cookie = self.makeOne()

        cookie_list = cookie.get_headers(None, max_age=0)

        for cookie in cookie_list:
            self.assertTrue('Max-Age=0;' in cookie[1])

    def test_cookie_max_age(self):
        cookie = self.makeOne()

        cookie_list = cookie.get_headers("test", max_age=60)

        for cookie in cookie_list:
            self.assertTrue('Max-Age=60;' in cookie[1])
            self.assertTrue('expires=' in cookie[1])

    def test_cookie_raw(self):
        cookie = self.makeOne()

        cookie_list = cookie.get_headers("test")

        self.assertTrue(isinstance(cookie_list, list))

    def test_set_cookie(self):
        request = self.makeOneRequest()
        cookie = self.makeOne(request=request)

        ret = cookie.set_cookies(request.response, "test")

        self.assertEqual(ret, request.response)

    def test_no_cookie(self):
        cookie = self.makeOne()

        ret = cookie.get_value()

        self.assertEqual(None, ret)

    def test_with_cookies(self):
        request = self.makeOneRequest()
        request.cookies['uns'] = (
            'FLIoEwZcKG6ITQSqbYcUNnPljwOcGNs25JRVCSoZcx_uX-OA1AhssA-CNeVKpWksQ'
            'a0ktMhuQDdjzmDwgzbptiJ0ZXN0Ig'
            )
        cookie = self.makeOne(request=request)
        ret = cookie.get_value()

        self.assertEqual(ret, "test")

    def test_with_bad_cookie_invalid_base64(self):
        request = self.makeOneRequest()
        request.cookies['uns'] = (
            "gAJVBHRlc3RxAS4KjKfwGmCkliC4ba99rWUdpy_{}riHzK7MQFPsbSgYTgALHa"
            "SHrRkd3lyE8c4w5ruxAKOyj2h5oF69Ix7ERZv_")
        cookie = self.makeOne(request=request)

        val = cookie.get_value()

        self.assertEqual(val, None)

    def test_with_bad_cookie_invalid_signature(self):
        request = self.makeOneRequest()
        request.cookies['uns'] = (
            "InRlc3QiFLIoEwZcKG6ITQSqbYcUNnPljwOcGNs25JRVCSoZcx/uX+OA1AhssA"
            "+CNeVKpWksQa0ktMhuQDdjzmDwgzbptg==")
        cookie = self.makeOne(secret='sekrit!', request=request)

        val = cookie.get_value()

        self.assertEqual(val, None)

    def test_with_domain(self):
        cookie = self.makeOne(domains=("testing.example.net",))
        ret = cookie.get_headers("test")

        passed = False

        for cookie in ret:
            if 'Domain=testing.example.net' in cookie[1]:
                passed = True

        self.assertTrue(passed)
        self.assertEqual(len(ret), 1)

    def test_with_domains(self):
        cookie = self.makeOne(
            domains=("testing.example.net", "testing2.example.net")
            )
        ret = cookie.get_headers("test")

        passed = 0

        for cookie in ret:
            if 'Domain=testing.example.net' in cookie[1]:
                passed += 1
            if 'Domain=testing2.example.net' in cookie[1]:
                passed += 1

        self.assertEqual(passed, 2)
        self.assertEqual(len(ret), 2)

    def test_flag_secure(self):
        cookie = self.makeOne(secure=True)
        ret = cookie.get_headers("test")

        for cookie in ret:
            self.assertTrue('; secure' in cookie[1])

    def test_flag_http_only(self):
        cookie = self.makeOne(httponly=True)
        ret = cookie.get_headers("test")

        for cookie in ret:
            self.assertTrue('; HttpOnly' in cookie[1])

    def test_cookie_length(self):
        cookie = self.makeOne()

        longstring = 'a' * 4096
        self.assertRaises(ValueError, cookie.get_headers, longstring)

    def test_very_long_key(self):
        longstring = 'a' * 1024
        cookie = self.makeOne(secret=longstring)

        cookie.get_headers("test")

def serialize(secret, salt, data):
    import hmac
    import base64
    import json
    from hashlib import sha1
    from webob.compat import bytes_
    salted_secret = bytes_(salt or '', 'utf-8') + bytes_(secret, 'utf-8')
    cstruct = bytes_(json.dumps(data))
    sig = hmac.new(salted_secret, cstruct, sha1).digest()
    return base64.urlsafe_b64encode(sig + cstruct).rstrip(b'=')

class SignedSerializerTest(unittest.TestCase):
    def makeOne(self, secret, salt, hashalg='sha1', **kw):
        from webob.cookies import SignedSerializer
        return SignedSerializer(secret, salt, hashalg=hashalg, **kw)

    def test_serialize(self):
        ser = self.makeOne('seekrit', 'salty')

        self.assertEqual(
            ser.dumps('test'),
            serialize('seekrit', 'salty', 'test')
            )

    def test_deserialize(self):
        ser = self.makeOne('seekrit', 'salty')

        self.assertEqual(
            ser.loads(serialize('seekrit', 'salty', 'test')),
            'test'
            )

    def test_with_highorder_secret(self):
        secret = b'\xce\xb1\xce\xb2\xce\xb3\xce\xb4'.decode('utf-8')
        ser = self.makeOne(secret, 'salty')

        self.assertEqual(
            ser.loads(serialize(secret, 'salty', 'test')),
            'test'
            )

    def test_with_highorder_salt(self):
        salt = b'\xce\xb1\xce\xb2\xce\xb3\xce\xb4'.decode('utf-8')
        ser = self.makeOne('secret', salt)

        self.assertEqual(
            ser.loads(serialize('secret', salt, 'test')),
            'test'
            )

    # bw-compat with webob <= 1.3.1 where secrets were encoded with latin-1
    def test_with_latin1_secret(self):
        secret = b'La Pe\xc3\xb1a'
        ser = self.makeOne(secret.decode('latin-1'), 'salty')

        self.assertEqual(
            ser.loads(serialize(secret, 'salty', 'test')),
            'test'
            )

    # bw-compat with webob <= 1.3.1 where salts were encoded with latin-1
    def test_with_latin1_salt(self):
        salt = b'La Pe\xc3\xb1a'
        ser = self.makeOne('secret', salt.decode('latin-1'))

        self.assertEqual(
            ser.loads(serialize('secret', salt, 'test')),
            'test'
            )

########NEW FILE########
__FILENAME__ = test_datetime_utils
# -*- coding: utf-8 -*-

import datetime
import calendar
from email.utils import formatdate
from webob import datetime_utils
from nose.tools import ok_, eq_, assert_raises

def test_UTC():
    """Test missing function in _UTC"""
    x = datetime_utils.UTC
    ok_(x.tzname(datetime.datetime.now())=='UTC')
    eq_(x.dst(datetime.datetime.now()), datetime.timedelta(0))
    eq_(x.utcoffset(datetime.datetime.now()), datetime.timedelta(0))
    eq_(repr(x), 'UTC')

def test_parse_date():
    """Testing datetime_utils.parse_date.
    We need to verify the following scenarios:
        * a nil submitted value
        * a submitted value that cannot be parse into a date
        * a valid RFC2822 date with and without timezone
    """
    ret = datetime_utils.parse_date(None)
    ok_(ret is None, "We passed a None value "
        "to parse_date. We should get None but instead we got %s" %\
        ret)
    ret = datetime_utils.parse_date('Hi There')
    ok_(ret is None, "We passed an invalid value "
        "to parse_date. We should get None but instead we got %s" %\
        ret)
    ret = datetime_utils.parse_date(1)
    ok_(ret is None, "We passed an invalid value "
        "to parse_date. We should get None but instead we got %s" %\
        ret)
    ret = datetime_utils.parse_date('á')
    ok_(ret is None, "We passed an invalid value "
        "to parse_date. We should get None but instead we got %s" %\
        ret)
    ret = datetime_utils.parse_date('Mon, 20 Nov 1995 19:12:08 -0500')
    eq_(ret, datetime.datetime(
        1995, 11, 21, 0, 12, 8, tzinfo=datetime_utils.UTC))
    ret = datetime_utils.parse_date('Mon, 20 Nov 1995 19:12:08')
    eq_(ret,
        datetime.datetime(1995, 11, 20, 19, 12, 8, tzinfo=datetime_utils.UTC))
    ret = datetime_utils.parse_date(Uncooperative())
    eq_(ret, None)

class Uncooperative(object):
    def __str__(self):
        raise NotImplementedError

def test_serialize_date():
    """Testing datetime_utils.serialize_date
    We need to verify the following scenarios:
        * on py3, passing an binary date, return the same date but str
        * on py2, passing an unicode date, return the same date but str
        * passing a timedelta, return now plus the delta
        * passing an invalid object, should raise ValueError
    """
    from webob.compat import text_
    ret = datetime_utils.serialize_date('Mon, 20 Nov 1995 19:12:08 GMT')
    assert isinstance(ret, str)
    eq_(ret, 'Mon, 20 Nov 1995 19:12:08 GMT')
    ret = datetime_utils.serialize_date(text_('Mon, 20 Nov 1995 19:12:08 GMT'))
    assert isinstance(ret, str)
    eq_(ret, 'Mon, 20 Nov 1995 19:12:08 GMT')
    dt = formatdate(
        calendar.timegm(
            (datetime.datetime.now()+datetime.timedelta(1)).timetuple()),
        usegmt=True)
    eq_(dt, datetime_utils.serialize_date(datetime.timedelta(1)))
    assert_raises(ValueError, datetime_utils.serialize_date, None)

def test_parse_date_delta():
    """Testing datetime_utils.parse_date_delta
    We need to verify the following scenarios:
        * passing a nil value, should return nil
        * passing a value that fails the conversion to int, should call
          parse_date
    """
    ok_(datetime_utils.parse_date_delta(None) is None, 'Passing none value, '
        'should return None')
    ret = datetime_utils.parse_date_delta('Mon, 20 Nov 1995 19:12:08 -0500')
    eq_(ret, datetime.datetime(
        1995, 11, 21, 0, 12, 8, tzinfo=datetime_utils.UTC))
    WHEN = datetime.datetime(2011, 3, 16, 10, 10, 37, tzinfo=datetime_utils.UTC)
    #with _NowRestorer(WHEN): Dammit, only Python 2.5 w/ __future__
    nr = _NowRestorer(WHEN)
    nr.__enter__()
    try:
        ret = datetime_utils.parse_date_delta(1)
        eq_(ret, WHEN + datetime.timedelta(0, 1))
    finally:
        nr.__exit__(None, None, None)


def test_serialize_date_delta():
    """Testing datetime_utils.serialize_date_delta
    We need to verify the following scenarios:
        * if we pass something that's not an int or float, it should delegate
          the task to serialize_date
    """
    eq_(datetime_utils.serialize_date_delta(1), '1')
    eq_(datetime_utils.serialize_date_delta(1.5), '1')
    ret = datetime_utils.serialize_date_delta('Mon, 20 Nov 1995 19:12:08 GMT')
    assert type(ret) is (str)
    eq_(ret, 'Mon, 20 Nov 1995 19:12:08 GMT')

def test_timedelta_to_seconds():
    val = datetime.timedelta(86400)
    result = datetime_utils.timedelta_to_seconds(val)
    eq_(result, 7464960000)


class _NowRestorer(object):
    def __init__(self, new_now):
        self._new_now = new_now
        self._old_now = None

    def __enter__(self):
        import webob.datetime_utils
        self._old_now = webob.datetime_utils._now
        webob.datetime_utils._now = lambda: self._new_now

    def __exit__(self, exc_type, exc_value, traceback):
        import webob.datetime_utils
        webob.datetime_utils._now = self._old_now

########NEW FILE########
__FILENAME__ = test_dec
import unittest
from webob.request import Request
from webob.response import Response
from webob.dec import wsgify
from webob.compat import bytes_
from webob.compat import text_
from webob.compat import PY3

class DecoratorTests(unittest.TestCase):
    def _testit(self, app, req):
        if isinstance(req, str):
            req = Request.blank(req)
        resp = req.get_response(app)
        return resp

    def test_wsgify(self):
        resp_str = 'hey, this is a test: %s'
        @wsgify
        def test_app(req):
            return bytes_(resp_str % req.url)
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body,
                         bytes_(resp_str % 'http://localhost/a%20url'))
        self.assertEqual(resp.content_length, 45)
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.charset, 'UTF-8')

    def test_wsgify_empty_repr(self):
        self.assertTrue('wsgify at' in repr(wsgify()))

    def test_wsgify_args(self):
        resp_str = b'hey hey my my'
        @wsgify(args=(resp_str,))
        def test_app(req, strarg):
            return strarg
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body, resp_str)
        self.assertEqual(resp.content_length, 13)
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.charset, 'UTF-8')

    def test_wsgify_kwargs(self):
        resp_str = b'hey hey my my'
        @wsgify(kwargs=dict(strarg=resp_str))
        def test_app(req, strarg=''):
            return strarg
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body, resp_str)
        self.assertEqual(resp.content_length, 13)
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.charset, 'UTF-8')

    def test_wsgify_raise_httpexception(self):
        from webob.exc import HTTPBadRequest
        @wsgify
        def test_app(req):
            raise HTTPBadRequest
        resp = self._testit(test_app, '/a url')
        self.assertTrue(resp.body.startswith(b'400 Bad Request'))
        self.assertEqual(resp.content_type, 'text/plain')
        self.assertEqual(resp.charset, 'UTF-8')

    def test_wsgify_no___get__(self):
        # use a class instance instead of a fn so we wrap something w/
        # no __get__
        class TestApp(object):
            def __call__(self, req):
                return 'nothing to see here'
        test_app = wsgify(TestApp())
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body, b'nothing to see here')
        self.assertTrue(test_app.__get__(test_app) is test_app)

    def test_wsgify_app_returns_unicode(self):
        def test_app(req):
            return text_('some text')
        test_app = wsgify(test_app)
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body, b'some text')

    def test_wsgify_args_no_func(self):
        test_app = wsgify(None, args=(1,))
        self.assertRaises(TypeError, self._testit, test_app, '/a url')

    def test_wsgify_wrong_sig(self):
        @wsgify
        def test_app(req):
            return 'What have you done for me lately?'
        req = dict()
        self.assertRaises(TypeError, test_app, req, 1, 2)
        self.assertRaises(TypeError, test_app, req, 1, key='word')

    def test_wsgify_none_response(self):
        @wsgify
        def test_app(req):
            return
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body, b'')
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.content_length, 0)

    def test_wsgify_get(self):
        resp_str = b"What'choo talkin' about, Willis?"
        @wsgify
        def test_app(req):
            return Response(resp_str)
        resp = test_app.get('/url/path')
        self.assertEqual(resp.body, resp_str)

    def test_wsgify_post(self):
        post_dict = dict(speaker='Robin',
                         words='Holy test coverage, Batman!')
        @wsgify
        def test_app(req):
            return Response('%s: %s' % (req.POST['speaker'],
                                        req.POST['words']))
        resp = test_app.post('/url/path', post_dict)
        self.assertEqual(resp.body, bytes_('%s: %s' % (post_dict['speaker'],
                                                       post_dict['words'])))

    def test_wsgify_request_method(self):
        resp_str = b'Nice body!'
        @wsgify
        def test_app(req):
            self.assertEqual(req.method, 'PUT')
            return Response(req.body)
        resp = test_app.request('/url/path', method='PUT',
                                body=resp_str)
        self.assertEqual(resp.body, resp_str)
        self.assertEqual(resp.content_length, 10)
        self.assertEqual(resp.content_type, 'text/html')

    def test_wsgify_undecorated(self):
        def test_app(req):
            return Response('whoa')
        wrapped_test_app = wsgify(test_app)
        self.assertTrue(wrapped_test_app.undecorated is test_app)

    def test_wsgify_custom_request(self):
        resp_str = 'hey, this is a test: %s'
        class MyRequest(Request):
            pass
        @wsgify(RequestClass=MyRequest)
        def test_app(req):
            return bytes_(resp_str % req.url)
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body,
                         bytes_(resp_str % 'http://localhost/a%20url'))
        self.assertEqual(resp.content_length, 45)
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.charset, 'UTF-8')

    def test_middleware(self):
        resp_str = "These are the vars: %s"
        @wsgify.middleware
        def set_urlvar(req, app, **vars):
            req.urlvars.update(vars)
            return app(req)
        from webob.dec import _MiddlewareFactory
        self.assertTrue(set_urlvar.__class__ is _MiddlewareFactory)
        r = repr(set_urlvar)
        self.assertTrue('set_urlvar' in r)
        @wsgify
        def show_vars(req):
            return resp_str % (sorted(req.urlvars.items()))
        show_vars2 = set_urlvar(show_vars, a=1, b=2)
        resp = self._testit(show_vars2, '/path')
        self.assertEqual(resp.body, bytes_(resp_str % "[('a', 1), ('b', 2)]"))
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.charset, 'UTF-8')
        self.assertEqual(resp.content_length, 40)

    def test_unbound_middleware(self):
        @wsgify
        def test_app(req):
            return Response('Say wha!?')
        unbound = wsgify.middleware(None, test_app, some='thing')
        from webob.dec import _UnboundMiddleware
        self.assertTrue(unbound.__class__ is _UnboundMiddleware)
        self.assertEqual(unbound.kw, dict(some='thing'))
        @unbound
        def middle(req, app, **kw):
            return app(req)
        self.assertTrue(middle.__class__ is wsgify)
        self.assertTrue('test_app' in repr(unbound))

    def test_unbound_middleware_no_app(self):
        unbound = wsgify.middleware(None, None)
        from webob.dec import _UnboundMiddleware
        self.assertTrue(unbound.__class__ is _UnboundMiddleware)
        self.assertEqual(unbound.kw, dict())

    def test_classapp(self):
        class HostMap(dict):
            @wsgify
            def __call__(self, req):
                return self[req.host.split(':')[0]]
        app = HostMap()
        app['example.com'] = Response('1')
        app['other.com'] = Response('2')
        resp = Request.blank('http://example.com/').get_response(wsgify(app))
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.charset, 'UTF-8')
        self.assertEqual(resp.content_length, 1)
        self.assertEqual(resp.body, b'1')

    def test_middleware_direct_call(self):
        @wsgify.middleware
        def mw(req, app):
            return 'foo'

        app = mw(Response())
        self.assertEqual(app(Request.blank('/')), 'foo')

########NEW FILE########
__FILENAME__ = test_descriptors
# -*- coding: utf-8 -*-
import unittest

from webob.compat import (
    PY3,
    text_,
    native_,
    )

from datetime import tzinfo
from datetime import timedelta

from nose.tools import eq_
from nose.tools import ok_
from nose.tools import assert_raises

from webob.request import Request


class GMT(tzinfo):
    """UTC"""
    ZERO = timedelta(0)
    def utcoffset(self, dt):
        return self.ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return self.ZERO


class MockDescriptor:
    _val = 'avalue'
    def __get__(self, obj, type=None):
        return self._val
    def __set__(self, obj, val):
        self._val = val
    def __delete__(self, obj):
        self._val = None


def test_environ_getter_docstring():
    from webob.descriptors import environ_getter
    desc = environ_getter('akey')
    eq_(desc.__doc__, "Gets and sets the ``akey`` key in the environment.")

def test_environ_getter_nodefault_keyerror():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey')
    assert_raises(KeyError, desc.fget, req)

def test_environ_getter_nodefault_fget():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey')
    desc.fset(req, 'bar')
    eq_(req.environ['akey'], 'bar')

def test_environ_getter_nodefault_fdel():
    from webob.descriptors import environ_getter
    desc = environ_getter('akey')
    eq_(desc.fdel, None)

def test_environ_getter_default_fget():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey', default='the_default')
    eq_(desc.fget(req), 'the_default')

def test_environ_getter_default_fset():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey', default='the_default')
    desc.fset(req, 'bar')
    eq_(req.environ['akey'], 'bar')

def test_environ_getter_default_fset_none():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey', default='the_default')
    desc.fset(req, 'baz')
    desc.fset(req, None)
    ok_('akey' not in req.environ)

def test_environ_getter_default_fdel():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey', default='the_default')
    desc.fset(req, 'baz')
    assert 'akey' in req.environ
    desc.fdel(req)
    ok_('akey' not in req.environ)

def test_environ_getter_rfc_section():
    from webob.descriptors import environ_getter
    desc = environ_getter('HTTP_X_AKEY', rfc_section='14.3')
    eq_(desc.__doc__, "Gets and sets the ``X-Akey`` header "
        "(`HTTP spec section 14.3 "
        "<http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.3>`_)."
    )


def test_upath_property_fget():
    from webob.descriptors import upath_property
    req = Request.blank('/')
    desc = upath_property('akey')
    eq_(desc.fget(req), '')

def test_upath_property_fset():
    from webob.descriptors import upath_property
    req = Request.blank('/')
    desc = upath_property('akey')
    desc.fset(req, 'avalue')
    eq_(desc.fget(req), 'avalue')

def test_header_getter_doc():
    from webob.descriptors import header_getter
    desc = header_getter('X-Header', '14.3')
    assert('http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.3'
           in desc.__doc__)
    assert '``X-Header`` header' in desc.__doc__

def test_header_getter_fget():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    eq_(desc.fget(resp), None)

def test_header_getter_fset():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, 'avalue')
    eq_(desc.fget(resp), 'avalue')

def test_header_getter_fset_none():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, 'avalue')
    desc.fset(resp, None)
    eq_(desc.fget(resp), None)

def test_header_getter_fset_text():
    from webob.compat import text_
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, text_('avalue'))
    eq_(desc.fget(resp), 'avalue')

def test_header_getter_fdel():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, 'avalue2')
    desc.fdel(resp)
    eq_(desc.fget(resp), None)

def test_header_getter_unicode_fget_none():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    eq_(desc.fget(resp), None)

def test_header_getter_unicode_fget():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, 'avalue')
    eq_(desc.fget(resp), 'avalue')

def test_header_getter_unicode_fset_none():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, None)
    eq_(desc.fget(resp), None)

def test_header_getter_unicode_fset():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, 'avalue2')
    eq_(desc.fget(resp), 'avalue2')

def test_header_getter_unicode_fdel():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, 'avalue3')
    desc.fdel(resp)
    eq_(desc.fget(resp), None)

def test_converter_not_prop():
    from webob.descriptors import converter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    assert_raises(AssertionError,converter,
        ('CONTENT_LENGTH', None, '14.13'),
        parse_int_safe, serialize_int, 'int')

def test_converter_with_name_docstring():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int, 'int')

    assert 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.13' in desc.__doc__
    assert '``Content-Length`` header' in desc.__doc__

def test_converter_with_name_fget():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int, 'int')
    eq_(desc.fget(req), 666)

def test_converter_with_name_fset():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int, 'int')
    desc.fset(req, '999')
    eq_(desc.fget(req), 999)

def test_converter_without_name_fget():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int)
    eq_(desc.fget(req), 666)

def test_converter_without_name_fset():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int)
    desc.fset(req, '999')
    eq_(desc.fget(req), 999)

def test_converter_none_for_wrong_type():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        ## XXX: Should this fail  if the type is wrong?
        environ_getter('CONTENT_LENGTH', 'sixsixsix', '14.13'),
        parse_int_safe, serialize_int, 'int')
    eq_(desc.fget(req), None)

def test_converter_delete():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        ## XXX: Should this fail  if the type is wrong?
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int, 'int')
    assert_raises(KeyError, desc.fdel, req)

def test_list_header():
    from webob.descriptors import list_header
    desc = list_header('CONTENT_LENGTH', '14.13')
    eq_(type(desc), property)

def test_parse_list_single():
    from webob.descriptors import parse_list
    result = parse_list('avalue')
    eq_(result, ('avalue',))

def test_parse_list_multiple():
    from webob.descriptors import parse_list
    result = parse_list('avalue,avalue2')
    eq_(result, ('avalue', 'avalue2'))

def test_parse_list_none():
    from webob.descriptors import parse_list
    result = parse_list(None)
    eq_(result, None)

def test_parse_list_unicode_single():
    from webob.descriptors import parse_list
    result = parse_list('avalue')
    eq_(result, ('avalue',))

def test_parse_list_unicode_multiple():
    from webob.descriptors import parse_list
    result = parse_list('avalue,avalue2')
    eq_(result, ('avalue', 'avalue2'))

def test_serialize_list():
    from webob.descriptors import serialize_list
    result = serialize_list(('avalue', 'avalue2'))
    eq_(result, 'avalue, avalue2')

def test_serialize_list_string():
    from webob.descriptors import serialize_list
    result = serialize_list('avalue')
    eq_(result, 'avalue')

def test_serialize_list_unicode():
    from webob.descriptors import serialize_list
    result = serialize_list('avalue')
    eq_(result, 'avalue')

def test_converter_date():
    import datetime
    from webob.descriptors import converter_date
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    UTC = GMT()
    desc = converter_date(environ_getter(
        "HTTP_DATE", "Tue, 15 Nov 1994 08:12:31 GMT", "14.8"))
    eq_(desc.fget(req),
        datetime.datetime(1994, 11, 15, 8, 12, 31, tzinfo=UTC))

def test_converter_date_docstring():
    from webob.descriptors import converter_date
    from webob.descriptors import environ_getter
    desc = converter_date(environ_getter(
        "HTTP_DATE", "Tue, 15 Nov 1994 08:12:31 GMT", "14.8"))
    assert 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.8' in desc.__doc__
    assert '``Date`` header' in desc.__doc__


def test_date_header_fget_none():
    from webob import Response
    from webob.descriptors import date_header
    resp = Response('aresponse')
    desc = date_header('HTTP_DATE', "14.8")
    eq_(desc.fget(resp), None)

def test_date_header_fset_fget():
    import datetime
    from webob import Response
    from webob.descriptors import date_header
    resp = Response('aresponse')
    UTC = GMT()
    desc = date_header('HTTP_DATE', "14.8")
    desc.fset(resp, "Tue, 15 Nov 1994 08:12:31 GMT")
    eq_(desc.fget(resp), datetime.datetime(1994, 11, 15, 8, 12, 31, tzinfo=UTC))

def test_date_header_fdel():
    from webob import Response
    from webob.descriptors import date_header
    resp = Response('aresponse')
    desc = date_header('HTTP_DATE', "14.8")
    desc.fset(resp, "Tue, 15 Nov 1994 08:12:31 GMT")
    desc.fdel(resp)
    eq_(desc.fget(resp), None)

def test_deprecated_property():
    from webob.descriptors import deprecated_property
    class Foo(object):
        pass
    Foo.attr = deprecated_property('attr', 'attr', 'whatever', '1.2')
    foo = Foo()
    assert_raises(DeprecationWarning, getattr, foo, 'attr')
    assert_raises(DeprecationWarning, setattr, foo, 'attr', {})
    assert_raises(DeprecationWarning, delattr, foo, 'attr')

def test_parse_etag_response():
    from webob.descriptors import parse_etag_response
    etresp = parse_etag_response("etag")
    eq_(etresp, "etag")

def test_parse_etag_response_quoted():
    from webob.descriptors import parse_etag_response
    etresp = parse_etag_response('"etag"')
    eq_(etresp, "etag")

def test_parse_etag_response_is_none():
    from webob.descriptors import parse_etag_response
    etresp = parse_etag_response(None)
    eq_(etresp, None)

def test_serialize_etag_response():
    from webob.descriptors import serialize_etag_response
    etresp = serialize_etag_response("etag")
    eq_(etresp, '"etag"')

def test_serialize_if_range_string():
    from webob.descriptors import serialize_if_range
    val = serialize_if_range("avalue")
    eq_(val, "avalue")

def test_serialize_if_range_unicode():
    from webob.descriptors import serialize_if_range
    val = serialize_if_range("avalue")
    eq_(val, "avalue")

def test_serialize_if_range_datetime():
    import datetime
    from webob.descriptors import serialize_if_range
    UTC = GMT()
    val = serialize_if_range(datetime.datetime(1994, 11, 15, 8, 12, 31, tzinfo=UTC))
    eq_(val, "Tue, 15 Nov 1994 08:12:31 GMT")

def test_serialize_if_range_other():
    from webob.descriptors import serialize_if_range
    val = serialize_if_range(123456)
    eq_(val, '123456')

def test_parse_range_none():
    from webob.descriptors import parse_range
    eq_(parse_range(None), None)

def test_parse_range_type():
    from webob.byterange import Range
    from webob.descriptors import parse_range
    val = parse_range("bytes=1-500")
    eq_(type(val), type(Range.parse("bytes=1-500")))

def test_parse_range_values():
    from webob.byterange import Range
    range = Range.parse("bytes=1-500")
    eq_(range.start, 1)
    eq_(range.end, 501)

def test_serialize_range_none():
    from webob.descriptors import serialize_range
    val = serialize_range(None)
    eq_(val, None)

def test_serialize_range():
    from webob.descriptors import serialize_range
    val = serialize_range((1,500))
    eq_(val, 'bytes=1-499')

def test_parse_int_none():
    from webob.descriptors import parse_int
    val = parse_int(None)
    eq_(val, None)

def test_parse_int_emptystr():
    from webob.descriptors import parse_int
    val = parse_int('')
    eq_(val, None)

def test_parse_int():
    from webob.descriptors import parse_int
    val = parse_int('123')
    eq_(val, 123)

def test_parse_int_invalid():
    from webob.descriptors import parse_int
    assert_raises(ValueError, parse_int, 'abc')

def test_parse_int_safe_none():
    from webob.descriptors import parse_int_safe
    eq_(parse_int_safe(None), None)

def test_parse_int_safe_emptystr():
    from webob.descriptors import parse_int_safe
    eq_(parse_int_safe(''), None)

def test_parse_int_safe():
    from webob.descriptors import parse_int_safe
    eq_(parse_int_safe('123'), 123)

def test_parse_int_safe_invalid():
    from webob.descriptors import parse_int_safe
    eq_(parse_int_safe('abc'), None)

def test_serialize_int():
    from webob.descriptors import serialize_int
    assert serialize_int is str

def test_parse_content_range_none():
    from webob.descriptors import parse_content_range
    eq_(parse_content_range(None), None)

def test_parse_content_range_emptystr():
    from webob.descriptors import parse_content_range
    eq_(parse_content_range(' '), None)

def test_parse_content_range_length():
    from webob.byterange import ContentRange
    from webob.descriptors import parse_content_range
    val = parse_content_range("bytes 0-499/1234")
    eq_(val.length, ContentRange.parse("bytes 0-499/1234").length)

def test_parse_content_range_start():
    from webob.byterange import ContentRange
    from webob.descriptors import parse_content_range
    val = parse_content_range("bytes 0-499/1234")
    eq_(val.start, ContentRange.parse("bytes 0-499/1234").start)

def test_parse_content_range_stop():
    from webob.byterange import ContentRange
    from webob.descriptors import parse_content_range
    val = parse_content_range("bytes 0-499/1234")
    eq_(val.stop, ContentRange.parse("bytes 0-499/1234").stop)

def test_serialize_content_range_none():
    from webob.descriptors import serialize_content_range
    eq_(serialize_content_range(None), 'None') ### XXX: Seems wrong

def test_serialize_content_range_emptystr():
    from webob.descriptors import serialize_content_range
    eq_(serialize_content_range(''), None)

def test_serialize_content_range_invalid():
    from webob.descriptors import serialize_content_range
    assert_raises(ValueError, serialize_content_range, (1,))

def test_serialize_content_range_asterisk():
    from webob.descriptors import serialize_content_range
    eq_(serialize_content_range((0, 500)), 'bytes 0-499/*')

def test_serialize_content_range_defined():
    from webob.descriptors import serialize_content_range
    eq_(serialize_content_range((0, 500, 1234)), 'bytes 0-499/1234')

def test_parse_auth_params_leading_capital_letter():
    from webob.descriptors import parse_auth_params
    val = parse_auth_params('Basic Realm=WebOb')
    eq_(val, {'ealm': 'WebOb'})

def test_parse_auth_params_trailing_capital_letter():
    from webob.descriptors import parse_auth_params
    val = parse_auth_params('Basic realM=WebOb')
    eq_(val, {})

def test_parse_auth_params_doublequotes():
    from webob.descriptors import parse_auth_params
    val = parse_auth_params('Basic realm="Web Object"')
    eq_(val, {'realm': 'Web Object'})

def test_parse_auth_params_multiple_values():
    from webob.descriptors import parse_auth_params
    val = parse_auth_params("foo='blah &&234', qop=foo, nonce='qwerty1234'")
    eq_(val, {'nonce': "'qwerty1234'", 'foo': "'blah &&234'", 'qop': 'foo'})

def test_parse_auth_params_truncate_on_comma():
    from webob.descriptors import parse_auth_params
    val = parse_auth_params("Basic realm=WebOb,this_will_truncate")
    eq_(val, {'realm': 'WebOb'})

def test_parse_auth_params_emptystr():
    from webob.descriptors import parse_auth_params
    eq_(parse_auth_params(''), {})

def test_authorization2():
    from webob.descriptors import parse_auth_params
    for s, d in [
            ('x=y', {'x': 'y'}),
            ('x="y"', {'x': 'y'}),
            ('x=y,z=z', {'x': 'y', 'z': 'z'}),
            ('x=y, z=z', {'x': 'y', 'z': 'z'}),
            ('x="y",z=z', {'x': 'y', 'z': 'z'}),
            ('x="y", z=z', {'x': 'y', 'z': 'z'}),
            ('x="y,x", z=z', {'x': 'y,x', 'z': 'z'}),
            ]:
        eq_(parse_auth_params(s), d)

def test_parse_auth_none():
    from webob.descriptors import parse_auth
    eq_(parse_auth(None), None)

def test_parse_auth_emptystr():
    from webob.descriptors import parse_auth
    assert_raises(ValueError, parse_auth, '')

def test_parse_auth_basic():
    from webob.descriptors import parse_auth
    eq_(parse_auth("Basic realm=WebOb"), ('Basic', 'realm=WebOb'))

def test_parse_auth_basic_quoted():
    from webob.descriptors import parse_auth
    eq_(parse_auth('Basic realm="Web Ob"'), ('Basic', {'realm': 'Web Ob'}))

def test_parse_auth_basic_quoted_multiple_unknown():
    from webob.descriptors import parse_auth
    eq_(parse_auth("foo='blah &&234', qop=foo, nonce='qwerty1234'"),
        ("foo='blah", "&&234', qop=foo, nonce='qwerty1234'"))

def test_parse_auth_basic_quoted_known_multiple():
    from webob.descriptors import parse_auth
    eq_(parse_auth("Basic realm='blah &&234', qop=foo, nonce='qwerty1234'"),
        ('Basic', "realm='blah &&234', qop=foo, nonce='qwerty1234'"))

def test_serialize_auth_none():
    from webob.descriptors import serialize_auth
    eq_(serialize_auth(None), None)

def test_serialize_auth_emptystr():
    from webob.descriptors import serialize_auth
    eq_(serialize_auth(''), '')

def test_serialize_auth_basic_quoted():
    from webob.descriptors import serialize_auth
    val = serialize_auth(('Basic', 'realm="WebOb"'))
    eq_(val, 'Basic realm="WebOb"')

def test_serialize_auth_digest_multiple():
    from webob.descriptors import serialize_auth
    val = serialize_auth(('Digest', 'realm="WebOb", nonce=abcde12345, qop=foo'))
    flags = val[len('Digest'):]
    result = sorted([ x.strip() for x in flags.split(',') ])
    eq_(result, ['nonce=abcde12345', 'qop=foo', 'realm="WebOb"'])

def test_serialize_auth_digest_tuple():
    from webob.descriptors import serialize_auth
    val = serialize_auth(('Digest', {'realm':'"WebOb"', 'nonce':'abcde12345', 'qop':'foo'}))
    flags = val[len('Digest'):]
    result = sorted([ x.strip() for x in flags.split(',') ])
    eq_(result, ['nonce="abcde12345"', 'qop="foo"', 'realm=""WebOb""'])


_nodefault = object()

class _TestEnvironDecoder(object):
    def _callFUT(self, key, default=_nodefault, rfc_section=None,
                 encattr=None):
        from webob.descriptors import environ_decoder
        if default is _nodefault:
            return environ_decoder(key, rfc_section=rfc_section,
                                   encattr=encattr)
        else:
            return environ_decoder(key, default=default,
                                   rfc_section=rfc_section, encattr=encattr)

    def test_docstring(self):
        desc = self._callFUT('akey')
        self.assertEqual(desc.__doc__,
                         "Gets and sets the ``akey`` key in the environment.")

    def test_nodefault_keyerror(self):
        req = self._makeRequest()
        desc = self._callFUT('akey')
        self.assertRaises(KeyError, desc.fget, req)

    def test_nodefault_fget(self):
        req = self._makeRequest()
        desc = self._callFUT('akey')
        desc.fset(req, 'bar')
        self.assertEqual(req.environ['akey'], 'bar')

    def test_nodefault_fdel(self):
        desc = self._callFUT('akey')
        self.assertEqual(desc.fdel, None)

    def test_default_fget(self):
        req = self._makeRequest()
        desc = self._callFUT('akey', default='the_default')
        self.assertEqual(desc.fget(req), 'the_default')

    def test_default_fset(self):
        req = self._makeRequest()
        desc = self._callFUT('akey', default='the_default')
        desc.fset(req, 'bar')
        self.assertEqual(req.environ['akey'], 'bar')

    def test_default_fset_none(self):
        req = self._makeRequest()
        desc = self._callFUT('akey', default='the_default')
        desc.fset(req, 'baz')
        desc.fset(req, None)
        self.assertTrue('akey' not in req.environ)

    def test_default_fdel(self):
        req = self._makeRequest()
        desc = self._callFUT('akey', default='the_default')
        desc.fset(req, 'baz')
        self.assertTrue('akey' in req.environ)
        desc.fdel(req)
        self.assertTrue('akey' not in req.environ)

    def test_rfc_section(self):
        desc = self._callFUT('HTTP_X_AKEY', rfc_section='14.3')
        self.assertEqual(
            desc.__doc__,
            "Gets and sets the ``X-Akey`` header "
            "(`HTTP spec section 14.3 "
            "<http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.3>`_)."
        )

    def test_fset_nonascii(self):
        desc = self._callFUT('HTTP_X_AKEY', encattr='url_encoding')
        req = self._makeRequest()
        desc.fset(req, text_(b'\xc3\xab', 'utf-8'))
        if PY3:
            self.assertEqual(req.environ['HTTP_X_AKEY'],
                             b'\xc3\xab'.decode('latin-1'))
        else:
            self.assertEqual(req.environ['HTTP_X_AKEY'], b'\xc3\xab')


class TestEnvironDecoder(unittest.TestCase, _TestEnvironDecoder):
    def _makeRequest(self):
        from webob.request import BaseRequest
        req = BaseRequest.blank('/')
        return req

    def test_fget_nonascii(self):
        desc = self._callFUT('HTTP_X_AKEY', encattr='url_encoding')
        req = self._makeRequest()
        if PY3:
            req.environ['HTTP_X_AKEY'] = b'\xc3\xab'.decode('latin-1')
        else:
            req.environ['HTTP_X_AKEY'] = b'\xc3\xab'
        result = desc.fget(req)
        self.assertEqual(result, text_(b'\xc3\xab', 'utf-8'))

class TestEnvironDecoderLegacy(unittest.TestCase, _TestEnvironDecoder):
    def _makeRequest(self):
        from webob.request import LegacyRequest
        req = LegacyRequest.blank('/')
        return req

    def test_fget_nonascii(self):
        desc = self._callFUT('HTTP_X_AKEY', encattr='url_encoding')
        req = self._makeRequest()
        if PY3:
            req.environ['HTTP_X_AKEY'] = b'\xc3\xab'.decode('latin-1')
        else:
            req.environ['HTTP_X_AKEY'] = b'\xc3\xab'
        result = desc.fget(req)
        self.assertEqual(result, native_(b'\xc3\xab', 'latin-1'))

    def test_default_fget_nonascii(self):
        req = self._makeRequest()
        desc = self._callFUT('akey', default=b'the_default')
        self.assertEqual(desc.fget(req).__class__, bytes)

########NEW FILE########
__FILENAME__ = test_etag
import unittest
from webob import Response
from webob.etag import ETagMatcher, IfRange, etag_property, ETagMatcher


class etag_propertyTests(unittest.TestCase):
    def _makeDummyRequest(self, **kw):
        """
        Return a DummyRequest object with attrs from kwargs.
        Use like:     dr = _makeDummyRequest(environment={'userid': 'johngalt'})
        Then you can: uid = dr.environment.get('userid', 'SomeDefault')
        """
        class Dummy(object):
            def __init__(self, **kwargs):
                self.__dict__.update(**kwargs)
        d = Dummy(**kw)
        return d

    def test_fget_missing_key(self):
        ep = etag_property("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={})
        self.assertEqual(ep.fget(req), "DEFAULT")

    def test_fget_found_key(self):
        ep = etag_property("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY':'"VALUE"'})
        res = ep.fget(req)
        self.assertEqual(res.etags, ['VALUE'])

    def test_fget_star_key(self):
        ep = etag_property("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY':'*'})
        res = ep.fget(req)
        import webob.etag
        self.assertEqual(type(res), webob.etag._AnyETag)
        self.assertEqual(res.__dict__, {})

    def test_fset_None(self):
        ep = etag_property("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY':'*'})
        res = ep.fset(req, None)
        self.assertEqual(res, None)

    def test_fset_not_None(self):
        ep = etag_property("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY':'OLDVAL'})
        res = ep.fset(req, "NEWVAL")
        self.assertEqual(res, None)
        self.assertEqual(req.environ['KEY'], 'NEWVAL')

    def test_fedl(self):
        ep = etag_property("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY':'VAL', 'QUAY':'VALYOU'})
        res = ep.fdel(req)
        self.assertEqual(res, None)
        self.assertFalse('KEY' in req.environ)
        self.assertEqual(req.environ['QUAY'], 'VALYOU')

class AnyETagTests(unittest.TestCase):
    def _getTargetClass(self):
        from webob.etag import _AnyETag
        return _AnyETag

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test___repr__(self):
        etag = self._makeOne()
        self.assertEqual(etag.__repr__(), '<ETag *>')

    def test___nonzero__(self):
        etag = self._makeOne()
        self.assertEqual(etag.__nonzero__(), False)

    def test___contains__something(self):
        etag = self._makeOne()
        self.assertEqual('anything' in etag, True)

    def test_weak_match_something(self):
        etag = self._makeOne()
        self.assertRaises(DeprecationWarning, etag.weak_match, 'anything')

    def test___str__(self):
        etag = self._makeOne()
        self.assertEqual(str(etag), '*')

class NoETagTests(unittest.TestCase):
    def _getTargetClass(self):
        from webob.etag import _NoETag
        return _NoETag

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test___repr__(self):
        etag = self._makeOne()
        self.assertEqual(etag.__repr__(), '<No ETag>')

    def test___nonzero__(self):
        etag = self._makeOne()
        self.assertEqual(etag.__nonzero__(), False)

    def test___contains__something(self):
        etag = self._makeOne()
        assert 'anything' not in etag

    def test___str__(self):
        etag = self._makeOne()
        self.assertEqual(str(etag), '')


class ParseTests(unittest.TestCase):
    def test_parse_None(self):
        et = ETagMatcher.parse(None)
        self.assertEqual(et.etags, [])

    def test_parse_anyetag(self):
        # these tests smell bad, are they useful?
        et = ETagMatcher.parse('*')
        self.assertEqual(et.__dict__, {})
        self.assertEqual(et.__repr__(), '<ETag *>')

    def test_parse_one(self):
        et = ETagMatcher.parse('"ONE"')
        self.assertEqual(et.etags, ['ONE'])

    def test_parse_invalid(self):
        for tag in ['one', 'one, two', '"one two']:
            et = ETagMatcher.parse(tag)
            self.assertEqual(et.etags, [tag])
        et = ETagMatcher.parse('"foo" and w/"weak"', strong=False)
        self.assertEqual(et.etags, ['foo'])


    def test_parse_commasep(self):
        et = ETagMatcher.parse('"ONE", "TWO"')
        self.assertEqual(et.etags, ['ONE', 'TWO'])

    def test_parse_commasep_w_weak(self):
        et = ETagMatcher.parse('"ONE", W/"TWO"')
        self.assertEqual(et.etags, ['ONE'])
        et = ETagMatcher.parse('"ONE", W/"TWO"', strong=False)
        self.assertEqual(et.etags, ['ONE', 'TWO'])

    def test_parse_quoted(self):
        et = ETagMatcher.parse('"ONE"')
        self.assertEqual(et.etags, ['ONE'])

    def test_parse_quoted_two(self):
        et = ETagMatcher.parse('"ONE", "TWO"')
        self.assertEqual(et.etags, ['ONE', 'TWO'])

    def test_parse_quoted_two_weak(self):
        et = ETagMatcher.parse('"ONE", W/"TWO"')
        self.assertEqual(et.etags, ['ONE'])
        et = ETagMatcher.parse('"ONE", W/"TWO"', strong=False)
        self.assertEqual(et.etags, ['ONE', 'TWO'])

class IfRangeTests(unittest.TestCase):
    def test___repr__(self):
        self.assertEqual(repr(IfRange(None)), 'IfRange(None)')

    def test___repr__etag(self):
        self.assertEqual(repr(IfRange('ETAG')), "IfRange('ETAG')")

    def test___repr__date(self):
        ir = IfRange.parse('Fri, 09 Nov 2001 01:08:47 GMT')
        self.assertEqual(
            repr(ir),
            'IfRangeDate(datetime.datetime(2001, 11, 9, 1, 8, 47, tzinfo=UTC))'
        )

########NEW FILE########
__FILENAME__ = test_etag_nose
from webob.etag import IfRange, ETagMatcher
from webob import Response
from nose.tools import eq_, assert_raises

def test_if_range_None():
    ir = IfRange.parse(None)
    eq_(str(ir), '')
    assert not ir
    assert Response() in ir
    assert Response(etag='foo') in ir
    assert Response(etag='foo GMT') in ir

def test_if_range_match_date():
    date = 'Fri, 09 Nov 2001 01:08:47 GMT'
    ir = IfRange.parse(date)
    eq_(str(ir), date)
    assert Response() not in ir
    assert Response(etag='etag') not in ir
    assert Response(etag=date) not in ir
    assert Response(last_modified='Fri, 09 Nov 2001 01:00:00 GMT') in ir
    assert Response(last_modified='Fri, 10 Nov 2001 01:00:00 GMT') not in ir

def test_if_range_match_etag():
    ir = IfRange.parse('ETAG')
    eq_(str(ir), '"ETAG"')
    assert Response() not in ir
    assert Response(etag='other') not in ir
    assert Response(etag='ETAG') in ir
    assert Response(etag='W/"ETAG"') not in ir

def test_if_range_match_etag_weak():
    ir = IfRange.parse('W/"ETAG"')
    eq_(str(ir), '')
    assert Response(etag='ETAG') not in ir
    assert Response(etag='W/"ETAG"') not in ir

def test_if_range_repr():
    eq_(repr(IfRange.parse(None)), 'IfRange(<ETag *>)')
    eq_(str(IfRange.parse(None)), '')

def test_resp_etag():
    def t(tag, res, raw, strong):
        eq_(Response(etag=tag).etag, res)
        eq_(Response(etag=tag).headers.get('etag'), raw)
        eq_(Response(etag=tag).etag_strong, strong)
    t('foo', 'foo', '"foo"', 'foo')
    t('"foo"', 'foo', '"foo"', 'foo')
    t('a"b', 'a"b', '"a\\"b"', 'a"b')
    t('W/"foo"', 'foo', 'W/"foo"', None)
    t('W/"a\\"b"', 'a"b', 'W/"a\\"b"', None)
    t(('foo', True), 'foo', '"foo"', 'foo')
    t(('foo', False), 'foo', 'W/"foo"', None)
    t(('"foo"', True), '"foo"', r'"\"foo\""', '"foo"')
    t(('W/"foo"', True), 'W/"foo"', r'"W/\"foo\""', 'W/"foo"')
    t(('W/"foo"', False), 'W/"foo"', r'W/"W/\"foo\""', None)

def test_matcher():
    matcher = ETagMatcher(['ETAGS'])
    matcher = ETagMatcher(['ETAGS'])
    eq_(matcher.etags, ['ETAGS'])
    assert_raises(DeprecationWarning, matcher.weak_match, "etag")
    assert "ETAGS" in matcher
    assert "WEAK" not in matcher
    assert "BEER" not in matcher
    assert None not in matcher
    eq_(repr(matcher), '<ETag ETAGS>')
    eq_(str(matcher), '"ETAGS"')

    matcher2 = ETagMatcher(("ETAG1","ETAG2"))
    eq_(repr(matcher2), '<ETag ETAG1 or ETAG2>')

########NEW FILE########
__FILENAME__ = test_exc
from webob.request import Request
from webob.dec import wsgify
from webob.exc import no_escape
from webob.exc import strip_tags
from webob.exc import HTTPException
from webob.exc import WSGIHTTPException
from webob.exc import _HTTPMove
from webob.exc import HTTPMethodNotAllowed
from webob.exc import HTTPExceptionMiddleware
from webob.exc import status_map

from nose.tools import eq_, ok_, assert_equal, assert_raises

@wsgify
def method_not_allowed_app(req):
    if req.method != 'GET':
        raise HTTPMethodNotAllowed()
    return 'hello!'

def test_noescape_null():
    assert_equal(no_escape(None), '')

def test_noescape_not_basestring():
    assert_equal(no_escape(42), '42')

def test_noescape_unicode():
    class DummyUnicodeObject(object):
        def __unicode__(self):
            return '42'
    duo = DummyUnicodeObject()
    assert_equal(no_escape(duo), '42')

def test_strip_tags_empty():
    assert_equal(strip_tags(''), '')

def test_strip_tags_newline_to_space():
    assert_equal(strip_tags('a\nb'), 'a b')

def test_strip_tags_zaps_carriage_return():
    assert_equal(strip_tags('a\rb'), 'ab')

def test_strip_tags_br_to_newline():
    assert_equal(strip_tags('a<br/>b'), 'a\nb')

def test_strip_tags_zaps_comments():
    assert_equal(strip_tags('a<!--b-->'), 'ab')

def test_strip_tags_zaps_tags():
    assert_equal(strip_tags('foo<bar>baz</bar>'), 'foobaz')

def test_HTTPException():
    import warnings
    _called = []
    _result = object()
    def _response(environ, start_response):
        _called.append((environ, start_response))
        return _result
    environ = {}
    start_response = object()
    exc = HTTPException('testing', _response)
    ok_(exc.wsgi_response is _response)
    result = exc(environ, start_response)
    ok_(result is result)
    assert_equal(_called, [(environ, start_response)])

def test_exception_with_unicode_data():
    req = Request.blank('/', method='POST')
    res = req.get_response(method_not_allowed_app)
    assert res.status_code == 405

def test_WSGIHTTPException_headers():
    exc = WSGIHTTPException(headers=[('Set-Cookie', 'a=1'),
                                     ('Set-Cookie', 'a=2')])
    mixed = exc.headers.mixed()
    assert mixed['set-cookie'] ==  ['a=1', 'a=2']

def test_WSGIHTTPException_w_body_template():
    from string import Template
    TEMPLATE = '$foo: $bar'
    exc = WSGIHTTPException(body_template = TEMPLATE)
    assert_equal(exc.body_template, TEMPLATE)
    ok_(isinstance(exc.body_template_obj, Template))
    eq_(exc.body_template_obj.substitute({'foo': 'FOO', 'bar': 'BAR'}),
        'FOO: BAR')

def test_WSGIHTTPException_w_empty_body():
    class EmptyOnly(WSGIHTTPException):
        empty_body = True
    exc = EmptyOnly(content_type='text/plain', content_length=234)
    ok_('content_type' not in exc.__dict__)
    ok_('content_length' not in exc.__dict__)

def test_WSGIHTTPException___str__():
    exc1 = WSGIHTTPException(detail='Detail')
    eq_(str(exc1), 'Detail')
    class Explain(WSGIHTTPException):
        explanation = 'Explanation'
    eq_(str(Explain()), 'Explanation')

def test_WSGIHTTPException_plain_body_no_comment():
    class Explain(WSGIHTTPException):
        code = '999'
        title = 'Testing'
        explanation = 'Explanation'
    exc = Explain(detail='Detail')
    eq_(exc.plain_body({}),
        '999 Testing\n\nExplanation\n\n Detail  ')

def test_WSGIHTTPException_html_body_w_comment():
    class Explain(WSGIHTTPException):
        code = '999'
        title = 'Testing'
        explanation = 'Explanation'
    exc = Explain(detail='Detail', comment='Comment')
    eq_(exc.html_body({}),
        '<html>\n'
        ' <head>\n'
        '  <title>999 Testing</title>\n'
        ' </head>\n'
        ' <body>\n'
        '  <h1>999 Testing</h1>\n'
        '  Explanation<br /><br />\n'
        'Detail\n'
        '<!-- Comment -->\n\n'
        ' </body>\n'
        '</html>'
       )

def test_WSGIHTTPException_generate_response():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'PUT',
       'HTTP_ACCEPT': 'text/html'
    }
    excep = WSGIHTTPException()
    assert_equal( excep(environ,start_response), [
        b'<html>\n'
        b' <head>\n'
        b'  <title>None None</title>\n'
        b' </head>\n'
        b' <body>\n'
        b'  <h1>None None</h1>\n'
        b'  <br /><br />\n'
        b'\n'
        b'\n\n'
        b' </body>\n'
        b'</html>' ]
    )

def test_WSGIHTTPException_call_w_body():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'PUT'
    }
    excep = WSGIHTTPException()
    excep.body = b'test'
    assert_equal( excep(environ,start_response), [b'test'] )


def test_WSGIHTTPException_wsgi_response():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD'
    }
    excep = WSGIHTTPException()
    assert_equal( excep.wsgi_response(environ,start_response), [] )

def test_WSGIHTTPException_exception_newstyle():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD'
    }
    excep = WSGIHTTPException()
    from webob import exc
    exc.newstyle_exceptions = True
    assert_equal( excep(environ,start_response), [] )

def test_WSGIHTTPException_exception_no_newstyle():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD'
    }
    excep = WSGIHTTPException()
    from webob import exc
    exc.newstyle_exceptions = False
    assert_equal( excep(environ,start_response), [] )

def test_HTTPOk_head_of_proxied_head():
    # first set up a response to a HEAD request
    HELLO_WORLD = "Hi!\n"
    CONTENT_TYPE = "application/hello"
    def head_app(environ, start_response):
        """An application object that understands HEAD"""
        status = '200 OK'
        response_headers = [('Content-Type', CONTENT_TYPE),
                            ('Content-Length', len(HELLO_WORLD))]
        start_response(status, response_headers)

        if environ['REQUEST_METHOD'] == 'HEAD':
            return []
        else:
            return [HELLO_WORLD]

    def verify_response(resp, description):
        assert_equal(resp.content_type, CONTENT_TYPE, description)
        assert_equal(resp.content_length, len(HELLO_WORLD), description)
        assert_equal(resp.body, b'', description)

    req = Request.blank('/', method='HEAD')
    resp1 = req.get_response(head_app)
    verify_response(resp1, "first response")

    # Copy the response like a proxy server would.
    # Copying an empty body has set content_length
    # so copy the headers only afterwards.
    resp2 = status_map[resp1.status_int](request=req)
    resp2.body = resp1.body
    resp2.headerlist = resp1.headerlist
    verify_response(resp2, "copied response")

    # evaluate it again
    resp3 = req.get_response(resp2)
    verify_response(resp3, "evaluated copy")

def test_HTTPMove():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD',
       'PATH_INFO': '/',
    }
    m = _HTTPMove()
    assert_equal( m( environ, start_response ), [] )

def test_HTTPMove_location_not_none():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD',
       'PATH_INFO': '/',
    }
    m = _HTTPMove(location='http://example.com')
    assert_equal( m( environ, start_response ), [] )

def test_HTTPMove_add_slash_and_location():
    def start_response(status, headers, exc_info=None):
        pass
    assert_raises( TypeError, _HTTPMove, location='http://example.com',
                   add_slash=True )

def test_HTTPMove_call_add_slash():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD',
       'PATH_INFO': '/',
    }
    m = _HTTPMove()
    m.add_slash = True
    assert_equal( m( environ, start_response ), [] )

def test_HTTPMove_call_query_string():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD'
    }
    m = _HTTPMove()
    m.add_slash = True
    environ[ 'QUERY_STRING' ] = 'querystring'
    environ['PATH_INFO'] = '/'
    assert_equal( m( environ, start_response ), [] )

def test_HTTPExceptionMiddleware_ok():
    def app( environ, start_response ):
        return '123'
    application = app
    m = HTTPExceptionMiddleware(application)
    environ = {}
    start_response = None
    res = m( environ, start_response )
    assert_equal( res, '123' )

def test_HTTPExceptionMiddleware_exception():
    def wsgi_response( environ, start_response):
        return '123'
    def app( environ, start_response ):
        raise HTTPException( None, wsgi_response )
    application = app
    m = HTTPExceptionMiddleware(application)
    environ = {}
    start_response = None
    res = m( environ, start_response )
    assert_equal( res, '123' )

def test_HTTPExceptionMiddleware_exception_exc_info_none():
    class DummySys:
        def exc_info(self):
            return None
    def wsgi_response( environ, start_response):
        return start_response('200 OK', [], exc_info=None)
    def app( environ, start_response ):
        raise HTTPException( None, wsgi_response )
    application = app
    m = HTTPExceptionMiddleware(application)
    environ = {}
    def start_response(status, headers, exc_info):
        pass
    try:
        from webob import exc
        old_sys = exc.sys
        sys = DummySys()
        res = m( environ, start_response )
        assert_equal( res, None )
    finally:
        exc.sys = old_sys

########NEW FILE########
__FILENAME__ = test_headers
# -*- coding: utf-8 -*-
from webob import headers
from nose.tools import ok_, assert_raises, eq_

class TestError(Exception):
    pass

def test_ResponseHeaders_delitem_notpresent():
    """Deleting a missing key from ResponseHeaders should raise a KeyError"""
    d = headers.ResponseHeaders()
    assert_raises(KeyError, d.__delitem__, 'b')

def test_ResponseHeaders_delitem_present():
    """
    Deleting a present key should not raise an error at all
    """
    d = headers.ResponseHeaders(a=1)
    del d['a']
    ok_('a' not in d)

def test_ResponseHeaders_setdefault():
    """Testing set_default for ResponseHeaders"""
    d = headers.ResponseHeaders(a=1)
    res = d.setdefault('b', 1)
    assert res == d['b'] == 1
    res = d.setdefault('b', 10)
    assert res == d['b'] == 1
    res = d.setdefault('B', 10)
    assert res == d['b'] == d['B'] == 1

def test_ResponseHeader_pop():
    """Testing if pop return TypeError when more than len(*args)>1 plus other
    assorted tests"""
    d = headers.ResponseHeaders(a=1, b=2, c=3, d=4)
    assert_raises(TypeError, d.pop, 'a', 'z', 'y')
    eq_(d.pop('a'), 1)
    ok_('a' not in d)
    eq_(d.pop('B'), 2)
    ok_('b' not in d)
    eq_(d.pop('c', 'u'), 3)
    ok_('c' not in d)
    eq_(d.pop('e', 'u'), 'u')
    ok_('e' not in d)
    assert_raises(KeyError, d.pop, 'z')

def test_ResponseHeaders_getitem_miss():
    d = headers.ResponseHeaders()
    assert_raises(KeyError, d.__getitem__, 'a')

def test_ResponseHeaders_getall():
    d = headers.ResponseHeaders()
    d.add('a', 1)
    d.add('a', 2)
    result = d.getall('a')
    eq_(result, [1,2])

def test_ResponseHeaders_mixed():
    d = headers.ResponseHeaders()
    d.add('a', 1)
    d.add('a', 2)
    d['b'] = 1
    result = d.mixed()
    eq_(result, {'a':[1,2], 'b':1})

def test_ResponseHeaders_setitem_scalar_replaces_seq():
    d = headers.ResponseHeaders()
    d.add('a', 2)
    d['a'] = 1
    result = d.getall('a')
    eq_(result, [1])

def test_ResponseHeaders_contains():
    d = headers.ResponseHeaders()
    d['a'] = 1
    ok_('a' in d)
    ok_(not 'b' in d)

def test_EnvironHeaders_delitem():
    d = headers.EnvironHeaders({'CONTENT_LENGTH': '10'})
    del d['CONTENT-LENGTH']
    assert not d
    assert_raises(KeyError, d.__delitem__, 'CONTENT-LENGTH')

def test_EnvironHeaders_getitem():
    d = headers.EnvironHeaders({'CONTENT_LENGTH': '10'})
    eq_(d['CONTENT-LENGTH'], '10')

def test_EnvironHeaders_setitem():
    d = headers.EnvironHeaders({})
    d['abc'] = '10'
    eq_(d['abc'], '10')

def test_EnvironHeaders_contains():
    d = headers.EnvironHeaders({})
    d['a'] = '10'
    ok_('a' in d)
    ok_(not 'b' in d)

def test__trans_key_not_basestring():
    result = headers._trans_key(None)
    eq_(result, None)

def test__trans_key_not_a_header():
    result = headers._trans_key('')
    eq_(result, None)

def test__trans_key_key2header():
    result = headers._trans_key('CONTENT_TYPE')
    eq_(result, 'Content-Type')

def test__trans_key_httpheader():
    result = headers._trans_key('HTTP_FOO_BAR')
    eq_(result, 'Foo-Bar')

########NEW FILE########
__FILENAME__ = test_in_wsgiref
import sys
import logging
import threading
import random
import socket
import cgi
from webob.request import Request
from webob.response import Response
from webob.compat import url_open
from webob.compat import bytes_
from webob.compat import reraise
from webob.compat import Queue
from webob.compat import Empty
from contextlib import contextmanager
from nose.tools import assert_raises
from nose.tools import eq_ as eq
from wsgiref.simple_server import make_server
from wsgiref.simple_server import WSGIRequestHandler
from wsgiref.simple_server import WSGIServer
from wsgiref.simple_server import ServerHandler

log = logging.getLogger(__name__)

def test_request_reading():
    """
        Test actual request/response cycle in the presence of Request.copy()
        and other methods that can potentially hang.
    """
    with serve(_test_app_req_reading) as server:
        for key in _test_ops_req_read:
            resp = url_open(server.url+key, timeout=3)
            assert resp.read() == b"ok"

def _test_app_req_reading(env, sr):
    req = Request(env)
    log.debug('starting test operation: %s', req.path_info)
    test_op = _test_ops_req_read[req.path_info]
    test_op(req)
    log.debug('done')
    r = Response("ok")
    return r(env, sr)

_test_ops_req_read = {
    '/copy': lambda req: req.copy(),
    '/read-all': lambda req: req.body_file.read(),
    '/read-0': lambda req: req.body_file.read(0),
    '/make-seekable': lambda req: req.make_body_seekable()
}




# TODO: remove server logging for interrupted requests
# TODO: test interrupted body directly

def test_interrupted_request():
    with serve(_test_app_req_interrupt) as server:
        for path in _test_ops_req_interrupt:
            _send_interrupted_req(server, path)
            try:
                res = _global_res.get(timeout=1)
            except Empty:
                raise AssertionError("Error during test %s", path)
            if res is not None:
                print("Error during test:", path)
                reraise(res)

_global_res = Queue()

def _test_app_req_interrupt(env, sr):
    target_cl = 100000
    try:
        req = Request(env)
        cl = req.content_length
        if cl != target_cl:
            raise AssertionError(
                'request.content_length is %s instead of %s' % (cl, target_cl))
        op = _test_ops_req_interrupt[req.path_info]
        log.info("Running test: %s", req.path_info)
        assert_raises(IOError, op, req)
    except:
        _global_res.put(sys.exc_info())
    else:
        _global_res.put(None)
        sr('200 OK', [])
        return []

def _req_int_cgi(req):
    assert req.body_file.read(0) == b''
    #req.environ.setdefault('CONTENT_LENGTH', '0')
    d = cgi.FieldStorage(
        fp=req.body_file,
        environ=req.environ,
    )

def _req_int_readline(req):
    try:
        eq(req.body_file.readline(), b'a=b\n')
    except IOError:
        # too early to detect disconnect
        raise AssertionError("False disconnect alert")
    req.body_file.readline()


_test_ops_req_interrupt = {
    '/copy': lambda req: req.copy(),
    '/read-body': lambda req: req.body,
    '/read-post': lambda req: req.POST,
    '/read-all': lambda req: req.body_file.read(),
    '/read-too-much': lambda req: req.body_file.read(1<<22),
    '/readline': _req_int_readline,
    '/readlines': lambda req: req.body_file.readlines(),
    '/read-cgi': _req_int_cgi,
    '/make-seekable': lambda req: req.make_body_seekable()
}


def _send_interrupted_req(server, path='/'):
    sock = socket.socket()
    sock.connect(('localhost', server.server_port))
    f = sock.makefile('wb')
    f.write(bytes_(_interrupted_req % path))
    f.flush()
    f.close()
    sock.close()

_interrupted_req = (
    "POST %s HTTP/1.0\r\n"
    "content-type: application/x-www-form-urlencoded\r\n"
    "content-length: 100000\r\n"
    "\r\n"
)
_interrupted_req += 'a=b\nz='+'x'*10000


@contextmanager
def serve(app):
    server = _make_test_server(app)
    try:
        #worker = threading.Thread(target=server.handle_request)
        worker = threading.Thread(target=server.serve_forever)
        worker.setDaemon(True)
        worker.start()
        server.url = "http://localhost:%d" % server.server_port
        log.debug("server started on %s", server.url)
        yield server
    finally:
        log.debug("shutting server down")
        server.shutdown()
        worker.join(1)
        if worker.isAlive():
            log.warning('worker is hanged')
        else:
            log.debug("server stopped")


class QuietHanlder(WSGIRequestHandler):
    def log_request(self, *args):
        pass

ServerHandler.handle_error = lambda: None

class QuietServer(WSGIServer):
    def handle_error(self, req, addr):
        pass

def _make_test_server(app):
    maxport = ((1<<16)-1)
    # we'll make 3 attempts to find a free port
    for i in range(3, 0, -1):
        try:
            port = random.randint(maxport//2, maxport)
            server = make_server('localhost', port, app,
                server_class=QuietServer,
                handler_class=QuietHanlder
            )
            server.timeout = 5
            return server
        except:
            if i == 1:
                raise



if __name__ == '__main__':
    #test_request_reading()
    test_interrupted_request()

########NEW FILE########
__FILENAME__ = test_misc
import cgi
from webob.util import html_escape
from webob.multidict import MultiDict
from nose.tools import eq_ as eq, assert_raises
from webob.compat import (
    text_,
    PY3
    )

def test_html_escape():
    if PY3:
        EXPECTED_LT = 'expected a &#x27;&lt;&#x27;.'
    else:
        EXPECTED_LT = "expected a '&lt;'."
    for v, s in [
        # unsafe chars
        ('these chars: < > & "', 'these chars: &lt; &gt; &amp; &quot;'),
        (' ', ' '),
        ('&egrave;', '&amp;egrave;'),
        # The apostrophe is *not* escaped, which some might consider to be
        # a serious bug (see, e.g. http://www.cvedetails.com/cve/CVE-2010-2480/)
        (text_('the majestic m\xf8ose'), 'the majestic m&#248;ose'),
        #("'", "&#39;")

        # 8-bit strings are passed through
        (text_('\xe9'), '&#233;'),
        ## (text_(b'the majestic m\xf8ose').encode('utf-8'),
        ##  'the majestic m\xc3\xb8ose'),

        # ``None`` is treated specially, and returns the empty string.
        (None, ''),

        # Objects that define a ``__html__`` method handle their own escaping
        (t_esc_HTML(), '<div>hello</div>'),

        # Things that are not strings are converted to strings and then escaped
        (42, '42'),
        (Exception("expected a '<'."), EXPECTED_LT),

        # If an object implements both ``__str__`` and ``__unicode__``, the latter
        # is preferred
        (t_esc_SuperMoose(), 'm&#248;ose'),
        (t_esc_Unicode(), '&#233;'),
        (t_esc_UnsafeAttrs(), '&lt;UnsafeAttrs&gt;'),
    ]:
        eq(html_escape(v), s)

class t_esc_HTML(object):
    def __html__(self):
        return '<div>hello</div>'


class t_esc_Unicode(object):
    def __unicode__(self):
        return text_(b'\xe9')

class t_esc_UnsafeAttrs(object):
    attr = 'value'
    def __getattr__(self, k):
        return self.attr
    def __repr__(self):
        return '<UnsafeAttrs>'

class t_esc_SuperMoose(object):
    def __str__(self):
        return text_(b'm\xf8ose').encode('utf-8')
    def __unicode__(self):
        return text_(b'm\xf8ose')






def test_multidict():
    d = MultiDict(a=1, b=2)
    eq(d['a'], 1)
    eq(d.getall('c'), [])

    d.add('a', 2)
    eq(d['a'], 2)
    eq(d.getall('a'), [1, 2])

    d['b'] = 4
    eq(d.getall('b'), [4])
    eq(list(d.keys()), ['a', 'a', 'b'])
    eq(list(d.items()), [('a', 1), ('a', 2), ('b', 4)])
    eq(d.mixed(), {'a': [1, 2], 'b': 4})

    # test getone

    # KeyError: "Multiple values match 'a': [1, 2]"
    assert_raises(KeyError, d.getone, 'a')
    eq(d.getone('b'), 4)
    # KeyError: "Key not found: 'g'"
    assert_raises(KeyError, d.getone, 'g')

    eq(d.dict_of_lists(), {'a': [1, 2], 'b': [4]})
    assert 'b' in d
    assert 'e' not in d
    d.clear()
    assert 'b' not in d
    d['a'] = 4
    d.add('a', 5)
    e = d.copy()
    assert 'a' in e
    e.clear()
    e['f'] = 42
    d.update(e)
    eq(d, MultiDict([('a', 4), ('a', 5), ('f', 42)]))
    f = d.pop('a')
    eq(f, 4)
    eq(d['a'], 5)


    eq(d.pop('g', 42), 42)
    assert_raises(KeyError, d.pop, 'n')
    # TypeError: pop expected at most 2 arguments, got 3
    assert_raises(TypeError, d.pop, 4, 2, 3)
    d.setdefault('g', []).append(4)
    eq(d, MultiDict([('a', 5), ('f', 42), ('g', [4])]))



def test_multidict_init():
    d = MultiDict([('a', 'b')], c=2)
    eq(repr(d), "MultiDict([('a', 'b'), ('c', 2)])")
    eq(d, MultiDict([('a', 'b')], c=2))

    # TypeError: MultiDict can only be called with one positional argument
    assert_raises(TypeError, MultiDict, 1, 2, 3)

    # TypeError: MultiDict.view_list(obj) takes only actual list objects, not None
    assert_raises(TypeError, MultiDict.view_list, None)

########NEW FILE########
__FILENAME__ = test_multidict
# -*- coding: utf-8 -*-

import unittest
from webob import multidict
from webob.compat import text_

class BaseDictTests(object):
    def setUp(self):
        self._list = [('a', text_('\xe9')), ('a', 'e'), ('a', 'f'), ('b', '1')]
        self.data = multidict.MultiDict(self._list)
        self.d = self._get_instance()

    def _get_instance(self, **kwargs):
        if kwargs:
            data = multidict.MultiDict(kwargs)
        else:
            data = self.data.copy()
        return self.klass(data)

    def test_len(self):
        self.assertEqual(len(self.d), 4)

    def test_getone(self):
        self.assertEqual(self.d.getone('b'),  '1')

    def test_getone_missing(self):
        self.assertRaises(KeyError, self.d.getone, 'z')

    def test_getone_multiple_raises(self):
        self.assertRaises(KeyError, self.d.getone, 'a')

    def test_getall(self):
        self.assertEqual(list(self.d.getall('b')), ['1'])

    def test_dict_of_lists(self):
        self.assertEqual(
            self.d.dict_of_lists(),
            {'a': [text_('\xe9'), 'e', 'f'], 'b': ['1']})

    def test_dict_api(self):
        self.assertTrue('a' in self.d.mixed())
        self.assertTrue('a' in self.d.keys())
        self.assertTrue('a' in self.d.iterkeys())
        self.assertTrue(('b', '1') in self.d.items())
        self.assertTrue(('b', '1') in self.d.iteritems())
        self.assertTrue('1' in self.d.values())
        self.assertTrue('1' in self.d.itervalues())
        self.assertEqual(len(self.d), 4)

    def test_set_del_item(self):
        d = self._get_instance()
        self.assertTrue('a' in d)
        del d['a']
        self.assertTrue(not 'a' in d)

    def test_pop(self):
        d = self._get_instance()
        d['a'] = '1'
        self.assertEqual(d.pop('a'), '1')
        self.assertEqual(d.pop('x', '1'), '1')

    def test_pop_wrong_args(self):
        d = self._get_instance()
        self.assertRaises(TypeError, d.pop, 'a', '1', '1')

    def test_pop_missing(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.pop, 'z')

    def test_popitem(self):
        d = self._get_instance()
        self.assertEqual(d.popitem(), ('b', '1'))

    def test_update(self):
        d = self._get_instance()
        d.update(e='1')
        self.assertTrue('e' in d)
        d.update(dict(x='1'))
        self.assertTrue('x' in d)
        d.update([('y', '1')])
        self.assertTrue('y' in d)

    def test_setdefault(self):
        d = self._get_instance()
        d.setdefault('a', '1')
        self.assertNotEqual(d['a'], '1')
        d.setdefault('e', '1')
        self.assertTrue('e' in d)

    def test_add(self):
        d = multidict.MultiDict({'a': '1'})
        d.add('a', '2')
        self.assertEqual(list(d.getall('a')), ['1', '2'])
        d = self._get_instance()
        d.add('b', '3')
        self.assertEqual(list(d.getall('b')), ['1', '3'])

    def test_copy(self):
        assert self.d.copy() is not self.d
        if hasattr(self.d, 'multi'):
            self.assertFalse(self.d.copy().multi is self.d.multi)
            self.assertFalse(self.d.copy() is self.d.multi)

    def test_clear(self):
        d = self._get_instance()
        d.clear()
        self.assertEqual(len(d), 0)

    def test_nonzero(self):
        d = self._get_instance()
        self.assertTrue(d)
        d.clear()
        self.assertFalse(d)

    def test_repr(self):
        self.assertTrue(repr(self._get_instance()))

    def test_too_many_args(self):
        from webob.multidict import MultiDict
        self.assertRaises(TypeError, MultiDict, '1', 2)

    def test_no_args(self):
        from webob.multidict import MultiDict
        md = MultiDict()
        self.assertEqual(md._items, [])

    def test_kwargs(self):
        from webob.multidict import MultiDict
        md = MultiDict(kw1='val1')
        self.assertEqual(md._items, [('kw1','val1')])

    def test_view_list_not_list(self):
        from webob.multidict import MultiDict
        d = MultiDict()
        self.assertRaises(TypeError, d.view_list, 42)

    def test_view_list(self):
        from webob.multidict import MultiDict
        d = MultiDict()
        self.assertEqual(d.view_list([1,2])._items, [1,2])

    def test_from_fieldstorage_with_filename(self):
        from webob.multidict import MultiDict
        d = MultiDict()
        fs = DummyFieldStorage('a', '1', 'file')
        self.assertEqual(d.from_fieldstorage(fs), MultiDict({'a':fs.list[0]}))

    def test_from_fieldstorage_without_filename(self):
        from webob.multidict import MultiDict
        d = MultiDict()
        fs = DummyFieldStorage('a', '1')
        self.assertEqual(d.from_fieldstorage(fs), MultiDict({'a':'1'}))

    def test_from_fieldstorage_with_charset(self):
        from cgi import FieldStorage
        from webob.request import BaseRequest
        from webob.multidict import MultiDict
        multipart_type = 'multipart/form-data; boundary=foobar'
        from io import BytesIO
        body = (
            b'--foobar\r\n'
            b'Content-Disposition: form-data; name="title"\r\n'
            b'Content-type: text/plain; charset="ISO-2022-JP"\r\n'
            b'\r\n'
            b'\x1b$B$3$s$K$A$O\x1b(B'
            b'\r\n'
            b'--foobar--')
        multipart_body = BytesIO(body)
        environ = BaseRequest.blank('/').environ
        environ.update(CONTENT_TYPE=multipart_type)
        environ.update(REQUEST_METHOD='POST')
        environ.update(CONTENT_LENGTH=len(body))
        fs = FieldStorage(multipart_body, environ=environ)
        vars = MultiDict.from_fieldstorage(fs)
        self.assertEqual(vars['title'].encode('utf8'),
                         text_('こんにちは', 'utf8').encode('utf8'))

    def test_from_fieldstorage_with_base64_encoding(self):
        from cgi import FieldStorage
        from webob.request import BaseRequest
        from webob.multidict import MultiDict
        multipart_type = 'multipart/form-data; boundary=foobar'
        from io import BytesIO
        body = (
            b'--foobar\r\n'
            b'Content-Disposition: form-data; name="title"\r\n'
            b'Content-type: text/plain; charset="ISO-2022-JP"\r\n'
            b'Content-Transfer-Encoding: base64\r\n'
            b'\r\n'
            b'GyRCJDMkcyRLJEEkTxsoQg=='
            b'\r\n'
            b'--foobar--')
        multipart_body = BytesIO(body)
        environ = BaseRequest.blank('/').environ
        environ.update(CONTENT_TYPE=multipart_type)
        environ.update(REQUEST_METHOD='POST')
        environ.update(CONTENT_LENGTH=len(body))
        fs = FieldStorage(multipart_body, environ=environ)
        vars = MultiDict.from_fieldstorage(fs)
        self.assertEqual(vars['title'].encode('utf8'),
                         text_('こんにちは', 'utf8').encode('utf8'))

    def test_from_fieldstorage_with_quoted_printable_encoding(self):
        from cgi import FieldStorage
        from webob.request import BaseRequest
        from webob.multidict import MultiDict
        multipart_type = 'multipart/form-data; boundary=foobar'
        from io import BytesIO
        body = (
            b'--foobar\r\n'
            b'Content-Disposition: form-data; name="title"\r\n'
            b'Content-type: text/plain; charset="ISO-2022-JP"\r\n'
            b'Content-Transfer-Encoding: quoted-printable\r\n'
            b'\r\n'
            b'=1B$B$3$s$K$A$O=1B(B'
            b'\r\n'
            b'--foobar--')
        multipart_body = BytesIO(body)
        environ = BaseRequest.blank('/').environ
        environ.update(CONTENT_TYPE=multipart_type)
        environ.update(REQUEST_METHOD='POST')
        environ.update(CONTENT_LENGTH=len(body))
        fs = FieldStorage(multipart_body, environ=environ)
        vars = MultiDict.from_fieldstorage(fs)
        self.assertEqual(vars['title'].encode('utf8'),
                         text_('こんにちは', 'utf8').encode('utf8'))


class MultiDictTestCase(BaseDictTests, unittest.TestCase):
    klass = multidict.MultiDict

    def test_update_behavior_warning(self):
        import warnings
        class Foo(dict):
            def __len__(self):
                return 0
        foo = Foo()
        foo['a'] = 1
        d = self._get_instance()
        with warnings.catch_warnings(record=True) as w:
            d.update(foo)
        self.assertEqual(len(w), 1)

    def test_repr_with_password(self):
        d = self._get_instance(password='pwd')
        self.assertEqual(repr(d), "MultiDict([('password', '******')])")


class NestedMultiDictTestCase(BaseDictTests, unittest.TestCase):
    klass = multidict.NestedMultiDict

    def test_getitem(self):
        d = self.klass({'a':1})
        self.assertEqual(d['a'], 1)

    def test_getitem_raises(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.__getitem__, 'z')

    def test_contains(self):
        d = self._get_instance()
        assert 'a' in d
        assert 'z' not in d

    def test_add(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.add, 'b', 3)

    def test_set_del_item(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.__delitem__, 'a')
        self.assertRaises(KeyError, d.__setitem__, 'a', 1)

    def test_update(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.update, e=1)
        self.assertRaises(KeyError, d.update, dict(x=1))
        self.assertRaises(KeyError, d.update, [('y', 1)])

    def test_setdefault(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.setdefault, 'a', 1)

    def test_pop(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.pop, 'a')
        self.assertRaises(KeyError, d.pop, 'a', 1)

    def test_popitem(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.popitem, 'a')

    def test_pop_wrong_args(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.pop, 'a', 1, 1)

    def test_clear(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.clear)

    def test_nonzero(self):
        d = self._get_instance()
        self.assertEqual(d.__nonzero__(), True)
        d.dicts = [{}]
        self.assertEqual(d.__nonzero__(), False)
        assert not d

class TestGetDict(BaseDictTests, unittest.TestCase):
    klass = multidict.GetDict

    def _get_instance(self, **kwargs):
        if kwargs:
            data = multidict.MultiDict(kwargs)
        else:
            data = self.data.copy()
        return self.klass(data, {})

    def test_inititems(self):
        #The first argument passed into the __init__ method
        class Arg:
            def items(self):
                return [('a', text_('\xe9')), ('a', 'e'), ('a', 'f'), ('b', 1)]

        d = self._get_instance()
        d._items = None
        d.__init__(Arg(), lambda:None)
        self.assertEqual(self.d._items, self._list)

    def test_nullextend(self):
        d = self._get_instance()
        self.assertEqual(d.extend(), None)
        d.extend(test = 'a')
        self.assertEqual(d['test'], 'a')

    def test_listextend(self):
        class Other:
            def items(self):
                return [text_('\xe9'), 'e', 'f', 1]

        other = Other()
        d = self._get_instance()
        d.extend(other)

        _list = [text_('\xe9'), 'e', r'f', 1]
        for v in _list:
            self.assertTrue(v in d._items)

    def test_dictextend(self):
        class Other:
            def __getitem__(self, item):
                return {'a':1, 'b':2, 'c':3}.get(item)

            def keys(self):
                return ['a', 'b', 'c']

        other = Other()
        d = self._get_instance()
        d.extend(other)

        _list = [('a', 1), ('b', 2), ('c', 3)]
        for v in _list:
            self.assertTrue(v in d._items)

    def test_otherextend(self):
        class Other(object):
            def __iter__(self):
                return iter([('a', 1)])

        other = Other()
        d = self._get_instance()
        d.extend(other)

        _list = [('a', 1)]
        for v in _list:
            self.assertTrue(v in d._items)

    def test_repr_with_password(self):
        d = self._get_instance(password='pwd')
        self.assertEqual(repr(d), "GET([('password', '******')])")

class NoVarsTestCase(unittest.TestCase):
    klass = multidict.NoVars

    def _get_instance(self):
        return self.klass()

    def test_getitem(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.__getitem__, 'a')

    def test_setitem(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.__setitem__, 'a')

    def test_delitem(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.__delitem__, 'a')

    def test_get(self):
        d = self._get_instance()
        self.assertEqual(d.get('a', default = 'b'), 'b')

    def test_getall(self):
        d = self._get_instance()
        self.assertEqual(d.getall('a'), [])

    def test_getone(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.getone, 'a')

    def test_mixed(self):
        d = self._get_instance()
        self.assertEqual(d.mixed(), {})

    def test_contains(self):
        d = self._get_instance()
        assert 'a' not in d

    def test_copy(self):
        d = self._get_instance()
        self.assertEqual(d.copy(), d)

    def test_len(self):
        d = self._get_instance()
        self.assertEqual(len(d), 0)

    def test_repr(self):
        d = self._get_instance()
        self.assertEqual(repr(d), '<NoVars: N/A>')

    def test_keys(self):
        d = self._get_instance()
        self.assertEqual(list(d.keys()), [])

    def test_iterkeys(self):
        d = self._get_instance()
        self.assertEqual(list(d.iterkeys()), [])

class DummyField(object):
    def __init__(self, name, value, filename=None):
        self.name = name
        self.value = value
        self.filename = filename
        self.type_options = {}
        self.headers = {}

class DummyFieldStorage(object):
    def __init__(self, name, value, filename=None):
        self.list = [DummyField(name, value, filename)]

########NEW FILE########
__FILENAME__ = test_request
# -*- coding: utf-8 -*-

import collections
import sys
import unittest
import warnings

from io import (
    BytesIO,
    StringIO,
    )

from webob.compat import (
    bytes_,
    native_,
    text_type,
    text_,
    PY3,
    )

class TestRequestCommon(unittest.TestCase):
    # unit tests of non-bytes-vs-text-specific methods of request object
    def _getTargetClass(self):
        from webob.request import Request
        return Request

    def _makeOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls(*arg, **kw)

    def _blankOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls.blank(*arg, **kw)

    def test_ctor_environ_getter_raises_WTF(self):
        self.assertRaises(TypeError,
                          self._makeOne, {}, environ_getter=object())

    def test_ctor_wo_environ_raises_WTF(self):
        self.assertRaises(TypeError, self._makeOne, None)

    def test_ctor_w_environ(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertEqual(req.environ, environ)

    def test_ctor_w_non_utf8_charset(self):
        environ = {}
        self.assertRaises(DeprecationWarning, self._makeOne, environ,
                          charset='latin-1')

    def test_scheme(self):
        environ = {'wsgi.url_scheme': 'something:',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.scheme, 'something:')

    def test_body_file_getter(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
        }
        req = self._makeOne(environ)
        self.assertTrue(req.body_file is not INPUT)

    def test_body_file_getter_seekable(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
            'webob.is_body_seekable': True,
        }
        req = self._makeOne(environ)
        self.assertTrue(req.body_file is INPUT)

    def test_body_file_getter_cache(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
        }
        req = self._makeOne(environ)
        self.assertTrue(req.body_file is req.body_file)

    def test_body_file_getter_unreadable(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'REQUEST_METHOD': 'FOO'}
        req = self._makeOne(environ)
        assert req.body_file_raw is INPUT
        assert req.body_file is not INPUT
        assert req.body_file.read() == b''

    def test_body_file_setter_w_bytes(self):
        req = self._blankOne('/')
        self.assertRaises(DeprecationWarning,
                          setattr, req, 'body_file', b'foo')

    def test_body_file_setter_non_bytes(self):
        BEFORE = BytesIO(b'before')
        AFTER =  BytesIO(b'after')
        environ = {'wsgi.input': BEFORE,
                   'CONTENT_LENGTH': len('before'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = self._makeOne(environ)
        req.body_file = AFTER
        self.assertTrue(req.body_file is AFTER)
        self.assertEqual(req.content_length, None)

    def test_body_file_deleter(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT,
                   'CONTENT_LENGTH': len(body),
                   'REQUEST_METHOD': 'POST',
                  }
        req = self._makeOne(environ)
        del req.body_file
        self.assertEqual(req.body_file.getvalue(), b'')
        self.assertEqual(req.content_length, 0)

    def test_body_file_raw(self):
        INPUT = BytesIO(b'input')
        environ = {'wsgi.input': INPUT,
                   'CONTENT_LENGTH': len('input'),
                   'REQUEST_METHOD': 'POST',
                  }
        req = self._makeOne(environ)
        self.assertTrue(req.body_file_raw is INPUT)

    def test_body_file_seekable_input_not_seekable(self):
        data = b'input'
        INPUT = BytesIO(data)
        INPUT.seek(1, 0) # consume
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': False,
                   'CONTENT_LENGTH': len(data)-1,
                   'REQUEST_METHOD': 'POST',
                  }
        req = self._makeOne(environ)
        seekable = req.body_file_seekable
        self.assertTrue(seekable is not INPUT)
        self.assertEqual(seekable.getvalue(), b'nput')

    def test_body_file_seekable_input_is_seekable(self):
        INPUT = BytesIO(b'input')
        INPUT.seek(1, 0) # consume
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len('input')-1,
                   'REQUEST_METHOD': 'POST',
                  }
        req = self._makeOne(environ)
        seekable = req.body_file_seekable
        self.assertTrue(seekable is INPUT)

    def test_urlvars_getter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.urlvars, {'foo': 'bar'})

    def test_urlvars_getter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.urlvars, {'foo': 'bar'})

    def test_urlvars_getter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertEqual(req.urlvars, {})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {}))

    def test_urlvars_setter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        req.urlvars = {'baz': 'bam'}
        self.assertEqual(req.urlvars, {'baz': 'bam'})
        self.assertEqual(environ['paste.urlvars'], {'baz': 'bam'})
        self.assertTrue('wsgiorg.routing_args' not in environ)

    def test_urlvars_setter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                   'paste.urlvars': {'qux': 'spam'},
                  }
        req = self._makeOne(environ)
        req.urlvars = {'baz': 'bam'}
        self.assertEqual(req.urlvars, {'baz': 'bam'})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {'baz': 'bam'}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlvars_setter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        req.urlvars = {'baz': 'bam'}
        self.assertEqual(req.urlvars, {'baz': 'bam'})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {'baz': 'bam'}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlvars_deleter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        del req.urlvars
        self.assertEqual(req.urlvars, {})
        self.assertTrue('paste.urlvars' not in environ)
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {}))

    def test_urlvars_deleter_w_wsgiorg_key_non_empty_tuple(self):
        environ = {'wsgiorg.routing_args': (('a', 'b'), {'foo': 'bar'}),
                   'paste.urlvars': {'qux': 'spam'},
                  }
        req = self._makeOne(environ)
        del req.urlvars
        self.assertEqual(req.urlvars, {})
        self.assertEqual(environ['wsgiorg.routing_args'], (('a', 'b'), {}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlvars_deleter_w_wsgiorg_key_empty_tuple(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                   'paste.urlvars': {'qux': 'spam'},
                  }
        req = self._makeOne(environ)
        del req.urlvars
        self.assertEqual(req.urlvars, {})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlvars_deleter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        del req.urlvars
        self.assertEqual(req.urlvars, {})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlargs_getter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.urlargs, ())

    def test_urlargs_getter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': (('a', 'b'), {'foo': 'bar'}),
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.urlargs, ('a', 'b'))

    def test_urlargs_getter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertEqual(req.urlargs, ())
        self.assertTrue('wsgiorg.routing_args' not in environ)

    def test_urlargs_setter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        req.urlargs = ('a', 'b')
        self.assertEqual(req.urlargs, ('a', 'b'))
        self.assertEqual(environ['wsgiorg.routing_args'],
                         (('a', 'b'), {'foo': 'bar'}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlargs_setter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                  }
        req = self._makeOne(environ)
        req.urlargs = ('a', 'b')
        self.assertEqual(req.urlargs, ('a', 'b'))
        self.assertEqual(environ['wsgiorg.routing_args'],
                         (('a', 'b'), {'foo': 'bar'}))

    def test_urlargs_setter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        req.urlargs = ('a', 'b')
        self.assertEqual(req.urlargs, ('a', 'b'))
        self.assertEqual(environ['wsgiorg.routing_args'],
                         (('a', 'b'), {}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlargs_deleter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': (('a', 'b'), {'foo': 'bar'}),
                  }
        req = self._makeOne(environ)
        del req.urlargs
        self.assertEqual(req.urlargs, ())
        self.assertEqual(environ['wsgiorg.routing_args'],
                         ((), {'foo': 'bar'}))

    def test_urlargs_deleter_w_wsgiorg_key_empty(self):
        environ = {'wsgiorg.routing_args': ((), {}),
                  }
        req = self._makeOne(environ)
        del req.urlargs
        self.assertEqual(req.urlargs, ())
        self.assertTrue('paste.urlvars' not in environ)
        self.assertTrue('wsgiorg.routing_args' not in environ)

    def test_urlargs_deleter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        del req.urlargs
        self.assertEqual(req.urlargs, ())
        self.assertTrue('paste.urlvars' not in environ)
        self.assertTrue('wsgiorg.routing_args' not in environ)

    def test_cookies_empty_environ(self):
        req = self._makeOne({})
        self.assertEqual(req.cookies, {})

    def test_cookies_is_mutable(self):
        req = self._makeOne({})
        cookies = req.cookies
        cookies['a'] = '1'
        self.assertEqual(req.cookies['a'], '1')

    def test_cookies_w_webob_parsed_cookies_matching_source(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
            'webob._parsed_cookies': ('a=b', {'a': 'b'}),
        }
        req = self._makeOne(environ)
        self.assertEqual(req.cookies, {'a': 'b'})

    def test_cookies_w_webob_parsed_cookies_mismatched_source(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
            'webob._parsed_cookies': ('a=b;c=d', {'a': 'b', 'c': 'd'}),
        }
        req = self._makeOne(environ)
        self.assertEqual(req.cookies, {'a': 'b'})

    def test_set_cookies(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
        }
        req = self._makeOne(environ)
        req.cookies = {'a':'1', 'b': '2'}
        self.assertEqual(req.cookies, {'a': '1', 'b':'2'})
        rcookies = [x.strip() for x in environ['HTTP_COOKIE'].split(';')]
        self.assertEqual(sorted(rcookies), ['a=1', 'b=2'])

    # body
    def test_body_getter(self):
        INPUT = BytesIO(b'input')
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len('input'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.body, b'input')
        self.assertEqual(req.content_length, len(b'input'))

    def test_body_setter_None(self):
        INPUT = BytesIO(b'input')
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len(b'input'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = self._makeOne(environ)
        req.body = None
        self.assertEqual(req.body, b'')
        self.assertEqual(req.content_length, 0)
        self.assertTrue(req.is_body_seekable)

    def test_body_setter_non_string_raises(self):
        req = self._makeOne({})
        def _test():
            req.body = object()
        self.assertRaises(TypeError, _test)

    def test_body_setter_value(self):
        BEFORE = BytesIO(b'before')
        environ = {'wsgi.input': BEFORE,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len('before'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = self._makeOne(environ)
        req.body = b'after'
        self.assertEqual(req.body, b'after')
        self.assertEqual(req.content_length, len(b'after'))
        self.assertTrue(req.is_body_seekable)

    def test_body_deleter_None(self):
        data = b'input'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len(data),
                   'REQUEST_METHOD': 'POST',
                  }
        req = self._makeOne(environ)
        del req.body
        self.assertEqual(req.body, b'')
        self.assertEqual(req.content_length, 0)
        self.assertTrue(req.is_body_seekable)

    # JSON

    def test_json_body(self):
        body = b'{"a":1}'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'CONTENT_LENGTH': str(len(body))}
        req = self._makeOne(environ)
        self.assertEqual(req.json, {"a": 1})
        self.assertEqual(req.json_body, {"a": 1})
        req.json = {"b": 2}
        self.assertEqual(req.body, b'{"b":2}')
        del req.json
        self.assertEqual(req.body, b'')

    def test_json_body_array(self):
        body = b'[{"a":1}, {"b":2}]'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'CONTENT_LENGTH': str(len(body))}
        req = self._makeOne(environ)
        self.assertEqual(req.json, [{"a": 1}, {"b": 2}])
        self.assertEqual(req.json_body, [{"a": 1}, {"b": 2}])
        req.json = [{"b": 2}]
        self.assertEqual(req.body, b'[{"b":2}]')
        del req.json
        self.assertEqual(req.body, b'')

    # .text

    def test_text_body(self):
        body = b'test'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'CONTENT_LENGTH': str(len(body))}
        req = self._makeOne(environ)
        self.assertEqual(req.body, b'test')
        self.assertEqual(req.text, 'test')
        req.text = text_('\u1000')
        self.assertEqual(req.body, '\u1000'.encode(req.charset))
        del req.text
        self.assertEqual(req.body, b'')
        def set_bad_text():
            req.text = 1
        self.assertRaises(TypeError, set_bad_text)

    def test__text_get_without_charset(self):
        body = b'test'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'CONTENT_LENGTH': str(len(body))}
        req = self._makeOne(environ)
        req._charset = ''
        self.assertRaises(AttributeError, getattr, req, 'text')

    def test__text_set_without_charset(self):
        body = b'test'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'CONTENT_LENGTH': str(len(body))}
        req = self._makeOne(environ)
        req._charset = ''
        self.assertRaises(AttributeError, setattr, req, 'text', 'abc')

    # POST
    def test_POST_not_POST_or_PUT(self):
        from webob.multidict import NoVars
        environ = {'REQUEST_METHOD': 'GET',
                  }
        req = self._makeOne(environ)
        result = req.POST
        self.assertTrue(isinstance(result, NoVars))
        self.assertTrue(result.reason.startswith('Not a form request'))

    def test_POST_existing_cache_hit(self):
        data = b'input'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'REQUEST_METHOD': 'POST',
                   'webob._parsed_post_vars': ({'foo': 'bar'}, INPUT),
                  }
        req = self._makeOne(environ)
        result = req.POST
        self.assertEqual(result, {'foo': 'bar'})

    def test_PUT_missing_content_type(self):
        from webob.multidict import NoVars
        data = b'input'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'REQUEST_METHOD': 'PUT',
                  }
        req = self._makeOne(environ)
        result = req.POST
        self.assertTrue(isinstance(result, NoVars))
        self.assertTrue(result.reason.startswith(
                                        'Not an HTML form submission'))

    def test_POST_missing_content_type(self):
        data = b'var1=value1&var2=value2&rep=1&rep=2'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'REQUEST_METHOD': 'POST',
                   'CONTENT_LENGTH':len(data),
                   'webob.is_body_seekable': True,
                  }
        req = self._makeOne(environ)
        result = req.POST
        self.assertEqual(result['var1'], 'value1')

    def test_PUT_bad_content_type(self):
        from webob.multidict import NoVars
        data = b'input'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'REQUEST_METHOD': 'PUT',
                   'CONTENT_TYPE': 'text/plain',
                  }
        req = self._makeOne(environ)
        result = req.POST
        self.assertTrue(isinstance(result, NoVars))
        self.assertTrue(result.reason.startswith(
                                        'Not an HTML form submission'))

    def test_POST_multipart(self):
        BODY_TEXT = (
            b'------------------------------deb95b63e42a\n'
            b'Content-Disposition: form-data; name="foo"\n'
            b'\n'
            b'foo\n'
            b'------------------------------deb95b63e42a\n'
            b'Content-Disposition: form-data; name="bar"; filename="bar.txt"\n'
            b'Content-type: application/octet-stream\n'
            b'\n'
            b'these are the contents of the file "bar.txt"\n'
            b'\n'
            b'------------------------------deb95b63e42a--\n')
        INPUT = BytesIO(BODY_TEXT)
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'REQUEST_METHOD': 'POST',
                   'CONTENT_TYPE': 'multipart/form-data; '
                      'boundary=----------------------------deb95b63e42a',
                   'CONTENT_LENGTH': len(BODY_TEXT),
                  }
        req = self._makeOne(environ)
        result = req.POST
        self.assertEqual(result['foo'], 'foo')
        bar = result['bar']
        self.assertEqual(bar.name, 'bar')
        self.assertEqual(bar.filename, 'bar.txt')
        self.assertEqual(bar.file.read(),
                         b'these are the contents of the file "bar.txt"\n')

    # GET
    def test_GET_reflects_query_string(self):
        environ = {
            'QUERY_STRING': 'foo=123',
        }
        req = self._makeOne(environ)
        result = req.GET
        self.assertEqual(result, {'foo': '123'})
        req.query_string = 'foo=456'
        result = req.GET
        self.assertEqual(result, {'foo': '456'})
        req.query_string = ''
        result = req.GET
        self.assertEqual(result, {})

    def test_GET_updates_query_string(self):
        req = self._makeOne({})
        result = req.query_string
        self.assertEqual(result, '')
        req.GET['foo'] = '123'
        result = req.query_string
        self.assertEqual(result, 'foo=123')
        del req.GET['foo']
        result = req.query_string
        self.assertEqual(result, '')

    # cookies
    def test_cookies_wo_webob_parsed_cookies(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
        }
        req = self._blankOne('/', environ)
        self.assertEqual(req.cookies, {'a': 'b'})

    # copy
    def test_copy_get(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
        }
        req = self._blankOne('/', environ)
        clone = req.copy_get()
        for k, v in req.environ.items():
            if k in ('CONTENT_LENGTH', 'webob.is_body_seekable'):
                self.assertTrue(k not in clone.environ)
            elif k == 'wsgi.input':
                self.assertTrue(clone.environ[k] is not v)
            else:
                self.assertEqual(clone.environ[k], v)

    def test_remove_conditional_headers_accept_encoding(self):
        req = self._blankOne('/')
        req.accept_encoding='gzip,deflate'
        req.remove_conditional_headers()
        self.assertEqual(bool(req.accept_encoding), False)

    def test_remove_conditional_headers_if_modified_since(self):
        from webob.datetime_utils import UTC
        from datetime import datetime
        req = self._blankOne('/')
        req.if_modified_since = datetime(2006, 1, 1, 12, 0, tzinfo=UTC)
        req.remove_conditional_headers()
        self.assertEqual(req.if_modified_since, None)

    def test_remove_conditional_headers_if_none_match(self):
        req = self._blankOne('/')
        req.if_none_match = 'foo'
        assert req.if_none_match
        req.remove_conditional_headers()
        assert not req.if_none_match

    def test_remove_conditional_headers_if_range(self):
        req = self._blankOne('/')
        req.if_range = 'foo, bar'
        req.remove_conditional_headers()
        self.assertEqual(bool(req.if_range), False)

    def test_remove_conditional_headers_range(self):
        req = self._blankOne('/')
        req.range = 'bytes=0-100'
        req.remove_conditional_headers()
        self.assertEqual(req.range, None)

    def test_is_body_readable_POST(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD':'POST'})
        self.assertTrue(req.is_body_readable)

    def test_is_body_readable_PATCH(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD':'PATCH'})
        self.assertTrue(req.is_body_readable)

    def test_is_body_readable_GET(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD':'GET'})
        self.assertFalse(req.is_body_readable)

    def test_is_body_readable_unknown_method_and_content_length(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD':'WTF'})
        req.content_length = 10
        self.assertTrue(req.is_body_readable)

    def test_is_body_readable_special_flag(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD':'WTF',
                                          'webob.is_body_readable': True})
        self.assertTrue(req.is_body_readable)


    # is_body_seekable
    # make_body_seekable
    # copy_body
    # make_tempfile
    # remove_conditional_headers
    # accept
    # accept_charset
    # accept_encoding
    # accept_language
    # authorization

    # cache_control
    def test_cache_control_reflects_environ(self):
        environ = {
            'HTTP_CACHE_CONTROL': 'max-age=5',
        }
        req = self._makeOne(environ)
        result = req.cache_control
        self.assertEqual(result.properties, {'max-age': 5})
        req.environ.update(HTTP_CACHE_CONTROL='max-age=10')
        result = req.cache_control
        self.assertEqual(result.properties, {'max-age': 10})
        req.environ.update(HTTP_CACHE_CONTROL='')
        result = req.cache_control
        self.assertEqual(result.properties, {})

    def test_cache_control_updates_environ(self):
        environ = {}
        req = self._makeOne(environ)
        req.cache_control.max_age = 5
        result = req.environ['HTTP_CACHE_CONTROL']
        self.assertEqual(result, 'max-age=5')
        req.cache_control.max_age = 10
        result = req.environ['HTTP_CACHE_CONTROL']
        self.assertEqual(result, 'max-age=10')
        req.cache_control = None
        result = req.environ['HTTP_CACHE_CONTROL']
        self.assertEqual(result, '')
        del req.cache_control
        self.assertTrue('HTTP_CACHE_CONTROL' not in req.environ)

    def test_cache_control_set_dict(self):
        environ = {}
        req = self._makeOne(environ)
        req.cache_control = {'max-age': 5}
        result = req.cache_control
        self.assertEqual(result.max_age, 5)

    def test_cache_control_set_object(self):
        from webob.cachecontrol import CacheControl
        environ = {}
        req = self._makeOne(environ)
        req.cache_control = CacheControl({'max-age': 5}, type='request')
        result = req.cache_control
        self.assertEqual(result.max_age, 5)

    def test_cache_control_gets_cached(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertTrue(req.cache_control is req.cache_control)

    #if_match
    #if_none_match

    #date
    #if_modified_since
    #if_unmodified_since
    #if_range
    #max_forwards
    #pragma
    #range
    #referer
    #referrer
    #user_agent
    #__repr__
    #__str__
    #from_file

    #call_application
    def test_call_application_calls_application(self):
        environ = {}
        req = self._makeOne(environ)
        def application(environ, start_response):
            start_response('200 OK', [('content-type', 'text/plain')])
            return ['...\n']
        status, headers, output = req.call_application(application)
        self.assertEqual(status, '200 OK')
        self.assertEqual(headers, [('content-type', 'text/plain')])
        self.assertEqual(''.join(output), '...\n')

    def test_call_application_provides_write(self):
        environ = {}
        req = self._makeOne(environ)
        def application(environ, start_response):
            write = start_response('200 OK', [('content-type', 'text/plain')])
            write('...\n')
            return []
        status, headers, output = req.call_application(application)
        self.assertEqual(status, '200 OK')
        self.assertEqual(headers, [('content-type', 'text/plain')])
        self.assertEqual(''.join(output), '...\n')

    def test_call_application_closes_iterable_when_mixed_w_write_calls(self):
        environ = {
            'test._call_application_called_close': False
        }
        req = self._makeOne(environ)
        def application(environ, start_response):
            write = start_response('200 OK', [('content-type', 'text/plain')])
            class AppIter(object):
                def __iter__(self):
                    yield '...\n'
                def close(self):
                    environ['test._call_application_called_close'] = True
            write('...\n')
            return AppIter()
        status, headers, output = req.call_application(application)
        self.assertEqual(''.join(output), '...\n...\n')
        self.assertEqual(environ['test._call_application_called_close'], True)

    def test_call_application_raises_exc_info(self):
        environ = {}
        req = self._makeOne(environ)
        def application(environ, start_response):
            try:
                raise RuntimeError('OH NOES')
            except:
                exc_info = sys.exc_info()
            start_response('200 OK',
                           [('content-type', 'text/plain')], exc_info)
            return ['...\n']
        self.assertRaises(RuntimeError, req.call_application, application)

    def test_call_application_returns_exc_info(self):
        environ = {}
        req = self._makeOne(environ)
        def application(environ, start_response):
            try:
                raise RuntimeError('OH NOES')
            except:
                exc_info = sys.exc_info()
            start_response('200 OK',
                           [('content-type', 'text/plain')], exc_info)
            return ['...\n']
        status, headers, output, exc_info = req.call_application(
            application, True)
        self.assertEqual(status, '200 OK')
        self.assertEqual(headers, [('content-type', 'text/plain')])
        self.assertEqual(''.join(output), '...\n')
        self.assertEqual(exc_info[0], RuntimeError)

    #get_response
    def test_blank__method_subtitution(self):
        request = self._blankOne('/', environ={'REQUEST_METHOD': 'PUT'})
        self.assertEqual(request.method, 'PUT')

        request = self._blankOne(
            '/', environ={'REQUEST_METHOD': 'PUT'}, POST={})
        self.assertEqual(request.method, 'PUT')

        request = self._blankOne(
            '/', environ={'REQUEST_METHOD': 'HEAD'}, POST={})
        self.assertEqual(request.method, 'POST')

    def test_blank__ctype_in_env(self):
        request = self._blankOne(
            '/', environ={'CONTENT_TYPE': 'application/json'})
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'GET')

        request = self._blankOne(
            '/', environ={'CONTENT_TYPE': 'application/json'}, POST='')
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'POST')

    def test_blank__ctype_in_headers(self):
        request = self._blankOne(
            '/', headers={'Content-type': 'application/json'})
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'GET')

        request = self._blankOne(
            '/', headers={'Content-Type': 'application/json'}, POST='')
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'POST')

    def test_blank__ctype_as_kw(self):
        request = self._blankOne('/', content_type='application/json')
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'GET')

        request = self._blankOne('/', content_type='application/json',
                                         POST='')
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'POST')

    def test_blank__str_post_data_for_unsupported_ctype(self):
        self.assertRaises(ValueError,
                          self._blankOne,
                          '/', content_type='application/json', POST={})

    def test_blank__post_urlencoded(self):
        from webob.multidict import MultiDict
        POST = MultiDict()
        POST["first"] = 1
        POST["second"] = 2

        request = self._blankOne('/', POST=POST)
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.content_type,
                         'application/x-www-form-urlencoded')
        self.assertEqual(request.body, b'first=1&second=2')
        self.assertEqual(request.content_length, 16)

    def test_blank__post_multipart(self):
        from webob.multidict import MultiDict
        POST = MultiDict()
        POST["first"] = "1"
        POST["second"] = "2"


        request = self._blankOne('/',
                                 POST=POST,
                                 content_type='multipart/form-data; '
                                              'boundary=boundary')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.content_type, 'multipart/form-data')
        expected = (
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="first"\r\n\r\n'
            b'1\r\n'
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="second"\r\n\r\n'
            b'2\r\n'
            b'--boundary--')
        self.assertEqual(request.body, expected)
        self.assertEqual(request.content_length, 139)

    def test_blank__post_files(self):
        import cgi
        from webob.request import _get_multipart_boundary
        from webob.multidict import MultiDict
        POST = MultiDict()
        POST["first"] = ('filename1', BytesIO(b'1'))
        POST["second"] = ('filename2', '2')
        POST["third"] = "3"
        request = self._blankOne('/', POST=POST)
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.content_type, 'multipart/form-data')
        boundary = bytes_(
            _get_multipart_boundary(request.headers['content-type']))
        body_norm = request.body.replace(boundary, b'boundary')
        expected = (
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="first"; '
                    b'filename="filename1"\r\n\r\n'
            b'1\r\n'
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="second"; '
                    b'filename="filename2"\r\n\r\n'
            b'2\r\n'
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="third"\r\n\r\n'
            b'3\r\n'
            b'--boundary--'
            )
        self.assertEqual(body_norm, expected)
        self.assertEqual(request.content_length, 294)
        self.assertTrue(isinstance(request.POST['first'], cgi.FieldStorage))
        self.assertTrue(isinstance(request.POST['second'], cgi.FieldStorage))
        self.assertEqual(request.POST['first'].value, b'1')
        self.assertEqual(request.POST['second'].value, b'2')
        self.assertEqual(request.POST['third'], '3')

    def test_blank__post_file_w_wrong_ctype(self):
        self.assertRaises(
            ValueError, self._blankOne, '/', POST={'first':('filename1', '1')},
            content_type='application/x-www-form-urlencoded')

    #from_bytes
    def test_from_bytes_extra_data(self):
        _test_req_copy = _test_req.replace(
            b'Content-Type',
            b'Content-Length: 337\r\nContent-Type')
        cls = self._getTargetClass()
        self.assertRaises(ValueError, cls.from_bytes,
                _test_req_copy+b'EXTRA!')

    #as_bytes
    def test_as_bytes_skip_body(self):
        cls = self._getTargetClass()
        req = cls.from_bytes(_test_req)
        body = req.as_bytes(skip_body=True)
        self.assertEqual(body.count(b'\r\n\r\n'), 0)
        self.assertEqual(req.as_bytes(skip_body=337), req.as_bytes())
        body = req.as_bytes(337-1).split(b'\r\n\r\n', 1)[1]
        self.assertEqual(body, b'<body skipped (len=337)>')

    def test_from_string_deprecated(self):
        cls = self._getTargetClass()
        self.assertRaises(DeprecationWarning, cls.from_string, _test_req)

    def test_as_string_deprecated(self):
        cls = self._getTargetClass()
        req = cls.from_bytes(_test_req)
        self.assertRaises(DeprecationWarning, req.as_string)

class TestBaseRequest(unittest.TestCase):
    # tests of methods of a base request which are encoding-specific
    def _getTargetClass(self):
        from webob.request import BaseRequest
        return BaseRequest

    def _makeOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls(*arg, **kw)

    def _blankOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls.blank(*arg, **kw)

    def test_method(self):
        environ = {'REQUEST_METHOD': 'OPTIONS',
                  }
        req = self._makeOne(environ)
        result = req.method
        self.assertEqual(result.__class__, str)
        self.assertEqual(result, 'OPTIONS')

    def test_http_version(self):
        environ = {'SERVER_PROTOCOL': '1.1',
                  }
        req = self._makeOne(environ)
        result = req.http_version
        self.assertEqual(result, '1.1')

    def test_script_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.script_name, '/script')

    def test_path_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_info, '/path/info')

    def test_content_length_getter(self):
        environ = {'CONTENT_LENGTH': '1234',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.content_length, 1234)

    def test_content_length_setter_w_str(self):
        environ = {'CONTENT_LENGTH': '1234',
                  }
        req = self._makeOne(environ)
        req.content_length = '3456'
        self.assertEqual(req.content_length, 3456)

    def test_remote_user(self):
        environ = {'REMOTE_USER': 'phred',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.remote_user, 'phred')

    def test_remote_addr(self):
        environ = {'REMOTE_ADDR': '1.2.3.4',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.remote_addr, '1.2.3.4')

    def test_query_string(self):
        environ = {'QUERY_STRING': 'foo=bar&baz=bam',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.query_string, 'foo=bar&baz=bam')

    def test_server_name(self):
        environ = {'SERVER_NAME': 'somehost.tld',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.server_name, 'somehost.tld')

    def test_server_port_getter(self):
        environ = {'SERVER_PORT': '6666',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.server_port, 6666)

    def test_server_port_setter_with_string(self):
        environ = {'SERVER_PORT': '6666',
                  }
        req = self._makeOne(environ)
        req.server_port = '6667'
        self.assertEqual(req.server_port, 6667)

    def test_uscript_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = self._makeOne(environ)
        self.assertTrue(isinstance(req.uscript_name, text_type))
        self.assertEqual(req.uscript_name, '/script')

    def test_upath_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertTrue(isinstance(req.upath_info, text_type))
        self.assertEqual(req.upath_info, '/path/info')

    def test_upath_info_set_unicode(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        req.upath_info = text_('/another')
        self.assertTrue(isinstance(req.upath_info, text_type))
        self.assertEqual(req.upath_info, '/another')

    def test_content_type_getter_no_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.content_type, 'application/xml+foobar')

    def test_content_type_getter_w_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.content_type, 'application/xml+foobar')

    def test_content_type_setter_w_None(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = None
        self.assertEqual(req.content_type, '')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_content_type_setter_existing_paramter_no_new_paramter(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = 'text/xml'
        self.assertEqual(req.content_type, 'text/xml')
        self.assertEqual(environ['CONTENT_TYPE'], 'text/xml;charset="utf8"')

    def test_content_type_deleter_clears_environ_value(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        del req.content_type
        self.assertEqual(req.content_type, '')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_content_type_deleter_no_environ_value(self):
        environ = {}
        req = self._makeOne(environ)
        del req.content_type
        self.assertEqual(req.content_type, '')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_headers_getter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        headers = req.headers
        self.assertEqual(headers,
                        {'Content-Type': CONTENT_TYPE,
                         'Content-Length': '123'})

    def test_headers_setter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        req.headers = {'Qux': 'Spam'}
        self.assertEqual(req.headers,
                        {'Qux': 'Spam'})
        self.assertEqual(environ, {'HTTP_QUX': 'Spam'})

    def test_no_headers_deleter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        def _test():
            del req.headers
        self.assertRaises(AttributeError, _test)

    def test_client_addr_xff_singleval(self):
        environ = {
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.1')

    def test_client_addr_xff_multival(self):
        environ = {
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1, 192.168.1.2',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.1')

    def test_client_addr_prefers_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.1')

    def test_client_addr_no_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.2')

    def test_client_addr_no_xff_no_remote_addr(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, None)

    def test_host_port_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '80')

    def test_host_port_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '80')

    def test_host_port_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '8888')

    def test_host_port_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '443')

    def test_host_port_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '443')

    def test_host_port_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '8888')

    def test_host_port_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '4333')

    def test_host_url_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'http://example.com')

    def test_host_url_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'http://example.com')

    def test_host_url_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'http://example.com:8888')

    def test_host_url_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com')

    def test_host_url_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com')

    def test_host_url_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com:4333')

    def test_host_url_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com:4333')

    def test_application_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = text_(b'/\xc3\xab', 'utf-8')
        app_url = inst.application_url
        self.assertEqual(app_url.__class__, str)
        self.assertEqual(app_url, 'http://localhost/%C3%AB')

    def test_path_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = text_(b'/\xc3\xab', 'utf-8')
        app_url = inst.path_url
        self.assertEqual(app_url.__class__, str)
        self.assertEqual(app_url, 'http://localhost/%C3%AB/%C3%AB')

    def test_path(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = text_(b'/\xc3\xab', 'utf-8')
        app_url = inst.path
        self.assertEqual(app_url.__class__, str)
        self.assertEqual(app_url, '/%C3%AB/%C3%AB')

    def test_path_qs_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_qs, '/script/path/info')

    def test_path_qs_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_qs, '/script/path/info?foo=bar&baz=bam')

    def test_url_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.url, 'http://example.com/script/path/info')

    def test_url_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.url,
                         'http://example.com/script/path/info?foo=bar&baz=bam')

    def test_relative_url_to_app_true_wo_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.relative_url('other/page', True),
                         'http://example.com/script/other/page')

    def test_relative_url_to_app_true_w_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.relative_url('/other/page', True),
                         'http://example.com/other/page')

    def test_relative_url_to_app_false_other_w_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.relative_url('/other/page', False),
                         'http://example.com/other/page')

    def test_relative_url_to_app_false_other_wo_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.relative_url('other/page', False),
                         'http://example.com/script/path/other/page')

    def test_path_info_pop_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, None)
        self.assertEqual(environ['SCRIPT_NAME'], '/script')

    def test_path_info_pop_just_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, '')
        self.assertEqual(environ['SCRIPT_NAME'], '/script/')
        self.assertEqual(environ['PATH_INFO'], '')

    def test_path_info_pop_non_empty_no_pattern(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, 'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script/path')
        self.assertEqual(environ['PATH_INFO'], '/info')

    def test_path_info_pop_non_empty_w_pattern_miss(self):
        import re
        PATTERN = re.compile('miss')
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop(PATTERN)
        self.assertEqual(popped, None)
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '/path/info')

    def test_path_info_pop_non_empty_w_pattern_hit(self):
        import re
        PATTERN = re.compile('path')
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop(PATTERN)
        self.assertEqual(popped, 'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script/path')
        self.assertEqual(environ['PATH_INFO'], '/info')

    def test_path_info_pop_skips_empty_elements(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '//path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, 'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script//path')
        self.assertEqual(environ['PATH_INFO'], '/info')

    def test_path_info_peek_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, None)
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '')

    def test_path_info_peek_just_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, '')
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '/')

    def test_path_info_peek_non_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, 'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '/path')

    def test_is_xhr_no_header(self):
        req = self._makeOne({})
        self.assertTrue(not req.is_xhr)

    def test_is_xhr_header_miss(self):
        environ = {'HTTP_X_REQUESTED_WITH': 'notAnXMLHTTPRequest'}
        req = self._makeOne(environ)
        self.assertTrue(not req.is_xhr)

    def test_is_xhr_header_hit(self):
        environ = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        req = self._makeOne(environ)
        self.assertTrue(req.is_xhr)

    # host
    def test_host_getter_w_HTTP_HOST(self):
        environ = {'HTTP_HOST': 'example.com:8888'}
        req = self._makeOne(environ)
        self.assertEqual(req.host, 'example.com:8888')

    def test_host_getter_wo_HTTP_HOST(self):
        environ = {'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '8888'}
        req = self._makeOne(environ)
        self.assertEqual(req.host, 'example.com:8888')

    def test_host_setter(self):
        environ = {}
        req = self._makeOne(environ)
        req.host = 'example.com:8888'
        self.assertEqual(environ['HTTP_HOST'], 'example.com:8888')

    def test_host_deleter_hit(self):
        environ = {'HTTP_HOST': 'example.com:8888'}
        req = self._makeOne(environ)
        del req.host
        self.assertTrue('HTTP_HOST' not in environ)

    def test_host_deleter_miss(self):
        environ = {}
        req = self._makeOne(environ)
        del req.host # doesn't raise

    def test_domain_nocolon(self):
        environ = {'HTTP_HOST':'example.com'}
        req = self._makeOne(environ)
        self.assertEqual(req.domain, 'example.com')

    def test_domain_withcolon(self):
        environ = {'HTTP_HOST':'example.com:8888'}
        req = self._makeOne(environ)
        self.assertEqual(req.domain, 'example.com')

    def test_encget_raises_without_default(self):
        inst = self._makeOne({})
        self.assertRaises(KeyError, inst.encget, 'a')

    def test_encget_doesnt_raises_with_default(self):
        inst = self._makeOne({})
        self.assertEqual(inst.encget('a', None), None)

    def test_encget_with_encattr(self):
        if PY3:
            val = b'\xc3\xab'.decode('latin-1')
        else:
            val = b'\xc3\xab'
        inst = self._makeOne({'a':val})
        self.assertEqual(inst.encget('a', encattr='url_encoding'),
                         text_(b'\xc3\xab', 'utf-8'))

    def test_encget_with_encattr_latin_1(self):
        if PY3:
            val = b'\xc3\xab'.decode('latin-1')
        else:
            val = b'\xc3\xab'
        inst = self._makeOne({'a':val})
        inst.my_encoding = 'latin-1'
        self.assertEqual(inst.encget('a', encattr='my_encoding'),
                         text_(b'\xc3\xab', 'latin-1'))

    def test_encget_no_encattr(self):
        if PY3:
            val = b'\xc3\xab'.decode('latin-1')
        else:
            val = b'\xc3\xab'
        inst = self._makeOne({'a':val})
        self.assertEqual(inst.encget('a'), val)

    def test_relative_url(self):
        inst = self._blankOne('/%C3%AB/c')
        result = inst.relative_url('a')
        self.assertEqual(result.__class__, str)
        self.assertEqual(result, 'http://localhost/%C3%AB/a')

    def test_header_getter(self):
        if PY3:
            val = b'abc'.decode('latin-1')
        else:
            val = b'abc'
        inst = self._makeOne({'HTTP_FLUB':val})
        result = inst.headers['Flub']
        self.assertEqual(result.__class__, str)
        self.assertEqual(result, 'abc')

    def test_json_body(self):
        inst = self._makeOne({})
        inst.body = b'{"a":"1"}'
        self.assertEqual(inst.json_body, {'a':'1'})
        inst.json_body = {'a': '2'}
        self.assertEqual(inst.body, b'{"a":"2"}')

    def test_host_get(self):
        inst = self._makeOne({'HTTP_HOST':'example.com'})
        result = inst.host
        self.assertEqual(result.__class__, str)
        self.assertEqual(result, 'example.com')

    def test_host_get_w_no_http_host(self):
        inst = self._makeOne({'SERVER_NAME':'example.com', 'SERVER_PORT':'80'})
        result = inst.host
        self.assertEqual(result.__class__, str)
        self.assertEqual(result, 'example.com:80')

class TestLegacyRequest(unittest.TestCase):
    # tests of methods of a bytesrequest which deal with http environment vars
    def _getTargetClass(self):
        from webob.request import LegacyRequest
        return LegacyRequest

    def _makeOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls(*arg, **kw)

    def _blankOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls.blank(*arg, **kw)

    def test_method(self):
        environ = {'REQUEST_METHOD': 'OPTIONS',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.method, 'OPTIONS')

    def test_http_version(self):
        environ = {'SERVER_PROTOCOL': '1.1',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.http_version, '1.1')

    def test_script_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.script_name, '/script')

    def test_path_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_info, '/path/info')

    def test_content_length_getter(self):
        environ = {'CONTENT_LENGTH': '1234',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.content_length, 1234)

    def test_content_length_setter_w_str(self):
        environ = {'CONTENT_LENGTH': '1234',
                  }
        req = self._makeOne(environ)
        req.content_length = '3456'
        self.assertEqual(req.content_length, 3456)

    def test_remote_user(self):
        environ = {'REMOTE_USER': 'phred',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.remote_user, 'phred')

    def test_remote_addr(self):
        environ = {'REMOTE_ADDR': '1.2.3.4',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.remote_addr, '1.2.3.4')

    def test_query_string(self):
        environ = {'QUERY_STRING': 'foo=bar&baz=bam',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.query_string, 'foo=bar&baz=bam')

    def test_server_name(self):
        environ = {'SERVER_NAME': 'somehost.tld',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.server_name, 'somehost.tld')

    def test_server_port_getter(self):
        environ = {'SERVER_PORT': '6666',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.server_port, 6666)

    def test_server_port_setter_with_string(self):
        environ = {'SERVER_PORT': '6666',
                  }
        req = self._makeOne(environ)
        req.server_port = '6667'
        self.assertEqual(req.server_port, 6667)

    def test_uscript_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = self._makeOne(environ)
        self.assertTrue(isinstance(req.uscript_name, text_type))
        result = req.uscript_name
        self.assertEqual(result.__class__, text_type)
        self.assertEqual(result, '/script')

    def test_upath_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        result = req.upath_info
        self.assertTrue(isinstance(result, text_type))
        self.assertEqual(result, '/path/info')

    def test_upath_info_set_unicode(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        req.upath_info = text_('/another')
        result = req.upath_info
        self.assertTrue(isinstance(result, text_type))
        self.assertEqual(result, '/another')

    def test_content_type_getter_no_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.content_type, 'application/xml+foobar')

    def test_content_type_getter_w_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.content_type, 'application/xml+foobar')

    def test_content_type_setter_w_None(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = None
        self.assertEqual(req.content_type, '')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_content_type_setter_existing_paramter_no_new_paramter(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = 'text/xml'
        self.assertEqual(req.content_type, 'text/xml')
        self.assertEqual(environ['CONTENT_TYPE'], 'text/xml;charset="utf8"')

    def test_content_type_deleter_clears_environ_value(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        del req.content_type
        self.assertEqual(req.content_type, '')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_content_type_deleter_no_environ_value(self):
        environ = {}
        req = self._makeOne(environ)
        del req.content_type
        self.assertEqual(req.content_type, '')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_headers_getter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        headers = req.headers
        self.assertEqual(headers,
                        {'Content-Type':CONTENT_TYPE,
                         'Content-Length': '123'})

    def test_headers_setter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        req.headers = {'Qux': 'Spam'}
        self.assertEqual(req.headers,
                        {'Qux': 'Spam'})
        self.assertEqual(environ['HTTP_QUX'], native_('Spam'))
        self.assertEqual(environ, {'HTTP_QUX': 'Spam'})

    def test_no_headers_deleter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        def _test():
            del req.headers
        self.assertRaises(AttributeError, _test)

    def test_client_addr_xff_singleval(self):
        environ = {
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.1')

    def test_client_addr_xff_multival(self):
        environ = {
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1, 192.168.1.2',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.1')

    def test_client_addr_prefers_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.1')

    def test_client_addr_no_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.2')

    def test_client_addr_no_xff_no_remote_addr(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, None)

    def test_host_port_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '80')

    def test_host_port_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '80')

    def test_host_port_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '8888')

    def test_host_port_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '443')

    def test_host_port_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '443')

    def test_host_port_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '8888')

    def test_host_port_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '4333')

    def test_host_url_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'http://example.com')

    def test_host_url_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'http://example.com')

    def test_host_url_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'http://example.com:8888')

    def test_host_url_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com')

    def test_host_url_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com')

    def test_host_url_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com:4333')

    def test_host_url_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com:4333')

    def test_application_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        app_url = inst.application_url
        if PY3: # pragma: no cover
            # this result is why you should not use legacyrequest under py 3
            self.assertEqual(app_url, 'http://localhost/%C3%83%C2%AB')
        else:
            self.assertEqual(app_url, 'http://localhost/%C3%AB')

    def test_path_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        result = inst.path_url
        if PY3: # pragma: no cover
            # this result is why you should not use legacyrequest under py 3
            self.assertEqual(result,
                             'http://localhost/%C3%83%C2%AB/%C3%83%C2%AB')
        else:
            self.assertEqual(result, 'http://localhost/%C3%AB/%C3%AB')

    def test_path(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        result = inst.path
        if PY3: # pragma: no cover
            # this result is why you should not use legacyrequest under py 3
            self.assertEqual(result, '/%C3%83%C2%AB/%C3%83%C2%AB')
        else:
            self.assertEqual(result, '/%C3%AB/%C3%AB')

    def test_path_qs_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_qs, '/script/path/info')

    def test_path_qs_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_qs, '/script/path/info?foo=bar&baz=bam')

    def test_url_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.url, 'http://example.com/script/path/info')

    def test_url_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.url,
                         'http://example.com/script/path/info?foo=bar&baz=bam')

    def test_relative_url_to_app_true_wo_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.relative_url('other/page', True),
                         'http://example.com/script/other/page')

    def test_relative_url_to_app_true_w_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.relative_url('/other/page', True),
                         'http://example.com/other/page')

    def test_relative_url_to_app_false_other_w_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.relative_url('/other/page', False),
                         'http://example.com/other/page')

    def test_relative_url_to_app_false_other_wo_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.relative_url('other/page', False),
                         'http://example.com/script/path/other/page')

    def test_path_info_pop_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, None)
        self.assertEqual(environ['SCRIPT_NAME'], '/script')

    def test_path_info_pop_just_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, '')
        self.assertEqual(environ['SCRIPT_NAME'], '/script/')
        self.assertEqual(environ['PATH_INFO'], '')

    def test_path_info_pop_non_empty_no_pattern(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, 'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script/path')
        self.assertEqual(environ['PATH_INFO'], '/info')

    def test_path_info_pop_non_empty_w_pattern_miss(self):
        import re
        PATTERN = re.compile('miss')
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop(PATTERN)
        self.assertEqual(popped, None)
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '/path/info')

    def test_path_info_pop_non_empty_w_pattern_hit(self):
        import re
        PATTERN = re.compile('path')
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop(PATTERN)
        self.assertEqual(popped, 'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script/path')
        self.assertEqual(environ['PATH_INFO'], '/info')

    def test_path_info_pop_skips_empty_elements(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '//path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, 'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script//path')
        self.assertEqual(environ['PATH_INFO'], '/info')

    def test_path_info_peek_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, None)
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '')

    def test_path_info_peek_just_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, '')
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '/')

    def test_path_info_peek_non_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, 'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '/path')

    def test_is_xhr_no_header(self):
        req = self._makeOne({})
        self.assertTrue(not req.is_xhr)

    def test_is_xhr_header_miss(self):
        environ = {'HTTP_X_REQUESTED_WITH': 'notAnXMLHTTPRequest'}
        req = self._makeOne(environ)
        self.assertTrue(not req.is_xhr)

    def test_is_xhr_header_hit(self):
        environ = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        req = self._makeOne(environ)
        self.assertTrue(req.is_xhr)

    # host
    def test_host_getter_w_HTTP_HOST(self):
        environ = {'HTTP_HOST': 'example.com:8888'}
        req = self._makeOne(environ)
        self.assertEqual(req.host, 'example.com:8888')

    def test_host_getter_wo_HTTP_HOST(self):
        environ = {'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '8888'}
        req = self._makeOne(environ)
        self.assertEqual(req.host, 'example.com:8888')

    def test_host_setter(self):
        environ = {}
        req = self._makeOne(environ)
        req.host = 'example.com:8888'
        self.assertEqual(environ['HTTP_HOST'], 'example.com:8888')

    def test_host_deleter_hit(self):
        environ = {'HTTP_HOST': 'example.com:8888'}
        req = self._makeOne(environ)
        del req.host
        self.assertTrue('HTTP_HOST' not in environ)

    def test_host_deleter_miss(self):
        environ = {}
        req = self._makeOne(environ)
        del req.host # doesn't raise

    def test_encget_raises_without_default(self):
        inst = self._makeOne({})
        self.assertRaises(KeyError, inst.encget, 'a')

    def test_encget_doesnt_raises_with_default(self):
        inst = self._makeOne({})
        self.assertEqual(inst.encget('a', None), None)

    def test_encget_with_encattr(self):
        if PY3:
            val = b'\xc3\xab'.decode('latin-1')
        else:
            val = b'\xc3\xab'
        inst = self._makeOne({'a':val})
        self.assertEqual(inst.encget('a', encattr='url_encoding'),
                         native_(b'\xc3\xab', 'latin-1'))

    def test_encget_no_encattr(self):
        if PY3:
            val = b'\xc3\xab'.decode('latin-1')
        else:
            val = b'\xc3\xab'
        inst = self._makeOne({'a':val})
        self.assertEqual(inst.encget('a'), native_(b'\xc3\xab', 'latin-1'))

    def test_relative_url(self):
        inst = self._blankOne('/%C3%AB/c')
        result = inst.relative_url('a')
        if PY3: # pragma: no cover
            # this result is why you should not use legacyrequest under py 3
            self.assertEqual(result, 'http://localhost/%C3%83%C2%AB/a')
        else:
            self.assertEqual(result, 'http://localhost/%C3%AB/a')

    def test_header_getter(self):
        if PY3:
            val = b'abc'.decode('latin-1')
        else:
            val = b'abc'
        inst = self._makeOne({'HTTP_FLUB':val})
        result = inst.headers['Flub']
        self.assertEqual(result, 'abc')

    def test_json_body(self):
        inst = self._makeOne({})
        inst.body = b'{"a":"1"}'
        self.assertEqual(inst.json_body, {'a':'1'})

    def test_host_get_w_http_host(self):
        inst = self._makeOne({'HTTP_HOST':'example.com'})
        result = inst.host
        self.assertEqual(result, 'example.com')

    def test_host_get_w_no_http_host(self):
        inst = self._makeOne({'SERVER_NAME':'example.com', 'SERVER_PORT':'80'})
        result = inst.host
        self.assertEqual(result, 'example.com:80')

class TestRequestConstructorWarnings(unittest.TestCase):
    def _getTargetClass(self):
        from webob.request import Request
        return Request

    def _makeOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls(*arg, **kw)

    def test_ctor_w_unicode_errors(self):
        with warnings.catch_warnings(record=True) as w:
            # still emit if warning was printed previously
            warnings.simplefilter('always')
            self._makeOne({}, unicode_errors=True)
        self.assertEqual(len(w), 1)

    def test_ctor_w_decode_param_names(self):
        with warnings.catch_warnings(record=True) as w:
            # still emit if warning was printed previously
            warnings.simplefilter('always')
            self._makeOne({}, decode_param_names=True)
        self.assertEqual(len(w), 1)

class TestRequestWithAdhocAttr(unittest.TestCase):
    def _blankOne(self, *arg, **kw):
        from webob.request import Request
        return Request.blank(*arg, **kw)

    def test_adhoc_attrs_set(self):
        req = self._blankOne('/')
        req.foo = 1
        self.assertEqual(req.environ['webob.adhoc_attrs'], {'foo': 1})

    def test_adhoc_attrs_set_nonadhoc(self):
        req = self._blankOne('/', environ={'webob.adhoc_attrs':{}})
        req.request_body_tempfile_limit = 1
        self.assertEqual(req.environ['webob.adhoc_attrs'], {})

    def test_adhoc_attrs_get(self):
        req = self._blankOne('/', environ={'webob.adhoc_attrs': {'foo': 1}})
        self.assertEqual(req.foo, 1)

    def test_adhoc_attrs_get_missing(self):
        req = self._blankOne('/')
        self.assertRaises(AttributeError, getattr, req, 'some_attr')

    def test_adhoc_attrs_del(self):
        req = self._blankOne('/', environ={'webob.adhoc_attrs': {'foo': 1}})
        del req.foo
        self.assertEqual(req.environ['webob.adhoc_attrs'], {})

    def test_adhoc_attrs_del_missing(self):
        req = self._blankOne('/')
        self.assertRaises(AttributeError, delattr, req, 'some_attr')

class TestRequest_functional(unittest.TestCase):
    # functional tests of request
    def _getTargetClass(self):
        from webob.request import Request
        return Request

    def _makeOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls(*arg, **kw)

    def _blankOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls.blank(*arg, **kw)

    def test_gets(self):
        request = self._blankOne('/')
        status, headerlist, app_iter = request.call_application(simpleapp)
        self.assertEqual(status, '200 OK')
        res = b''.join(app_iter)
        self.assertTrue(b'Hello' in res)
        self.assertTrue(b"MultiDict([])" in res)
        self.assertTrue(b"post is <NoVars: Not a form request>" in res)

    def test_gets_with_query_string(self):
        request = self._blankOne('/?name=george')
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"MultiDict" in res)
        self.assertTrue(b"'name'" in res)
        self.assertTrue(b"'george'" in res)
        self.assertTrue(b"Val is " in res)

    def test_language_parsing1(self):
        request = self._blankOne('/')
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"The languages are: []" in res)

    def test_language_parsing2(self):
        request = self._blankOne(
            '/', headers={'Accept-Language': 'da, en-gb;q=0.8'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"languages are: ['da', 'en-gb']" in res)

    def test_language_parsing3(self):
        request = self._blankOne(
            '/',
            headers={'Accept-Language': 'en-gb;q=0.8, da'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"languages are: ['da', 'en-gb']" in res)

    def test_mime_parsing1(self):
        request = self._blankOne(
            '/',
            headers={'Accept':'text/html'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"accepttypes is: text/html" in res)

    def test_mime_parsing2(self):
        request = self._blankOne(
            '/',
            headers={'Accept':'application/xml'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"accepttypes is: application/xml" in res)

    def test_mime_parsing3(self):
        request = self._blankOne(
            '/',
            headers={'Accept':'application/xml,*/*'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"accepttypes is: application/xml" in res)

    def test_accept_best_match(self):
        accept = self._blankOne('/').accept
        self.assertTrue(not accept)
        self.assertTrue(not self._blankOne('/', headers={'Accept': ''}).accept)
        req = self._blankOne('/', headers={'Accept':'text/plain'})
        self.assertTrue(req.accept)
        self.assertRaises(ValueError, req.accept.best_match, ['*/*'])
        req = self._blankOne('/', accept=['*/*','text/*'])
        self.assertEqual(
            req.accept.best_match(['application/x-foo', 'text/plain']),
            'text/plain')
        self.assertEqual(
            req.accept.best_match(['text/plain', 'application/x-foo']),
            'text/plain')
        req = self._blankOne('/', accept=['text/plain', 'message/*'])
        self.assertEqual(
            req.accept.best_match(['message/x-foo', 'text/plain']),
            'text/plain')
        self.assertEqual(
            req.accept.best_match(['text/plain', 'message/x-foo']),
            'text/plain')

    def test_from_mimeparse(self):
        # http://mimeparse.googlecode.com/svn/trunk/mimeparse.py
        supported = ['application/xbel+xml', 'application/xml']
        tests = [('application/xbel+xml', 'application/xbel+xml'),
                ('application/xbel+xml; q=1', 'application/xbel+xml'),
                ('application/xml; q=1', 'application/xml'),
                ('application/*; q=1', 'application/xbel+xml'),
                ('*/*', 'application/xbel+xml')]

        for accept, get in tests:
            req = self._blankOne('/', headers={'Accept':accept})
            self.assertEqual(req.accept.best_match(supported), get)

        supported = ['application/xbel+xml', 'text/xml']
        tests = [('text/*;q=0.5,*/*; q=0.1', 'text/xml'),
                ('text/html,application/atom+xml; q=0.9', None)]

        for accept, get in tests:
            req = self._blankOne('/', headers={'Accept':accept})
            self.assertEqual(req.accept.best_match(supported), get)

        supported = ['application/json', 'text/html']
        tests = [
            ('application/json, text/javascript, */*', 'application/json'),
            ('application/json, text/html;q=0.9', 'application/json'),
        ]

        for accept, get in tests:
            req = self._blankOne('/', headers={'Accept':accept})
            self.assertEqual(req.accept.best_match(supported), get)

        offered = ['image/png', 'application/xml']
        tests = [
            ('image/png', 'image/png'),
            ('image/*', 'image/png'),
            ('image/*, application/xml', 'application/xml'),
        ]

        for accept, get in tests:
            req = self._blankOne('/', accept=accept)
            self.assertEqual(req.accept.best_match(offered), get)

    def test_headers(self):
        headers = {
            'If-Modified-Since': 'Sat, 29 Oct 1994 19:43:31 GMT',
            'Cookie': 'var1=value1',
            'User-Agent': 'Mozilla 4.0 (compatible; MSIE)',
            'If-None-Match': '"etag001", "etag002"',
            'X-Requested-With': 'XMLHttpRequest',
            }
        request = self._blankOne('/?foo=bar&baz', headers=headers)
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        for thing in (
            'if_modified_since: ' +
                'datetime.datetime(1994, 10, 29, 19, 43, 31, tzinfo=UTC)',
            "user_agent: 'Mozilla",
            'is_xhr: True',
            "cookies is <RequestCookies",
            'var1',
            'value1',
            'params is NestedMultiDict',
            'foo',
            'bar',
            'baz',
            'if_none_match: <ETag etag001 or etag002>',
            ):
            self.assertTrue(bytes_(thing) in res)

    def test_bad_cookie(self):
        req = self._blankOne('/')
        req.headers['Cookie'] = '070-it-:><?0'
        self.assertEqual(req.cookies, {})
        req.headers['Cookie'] = 'foo=bar'
        self.assertEqual(req.cookies, {'foo': 'bar'})
        req.headers['Cookie'] = '...'
        self.assertEqual(req.cookies, {})
        req.headers['Cookie'] = '=foo'
        self.assertEqual(req.cookies, {})
        req.headers['Cookie'] = ('dismiss-top=6; CP=null*; '
            'PHPSESSID=0a539d42abc001cdc762809248d4beed; a=42')
        self.assertEqual(req.cookies, {
            'CP':           'null*',
            'PHPSESSID':    '0a539d42abc001cdc762809248d4beed',
            'a':            '42',
            'dismiss-top':  '6'
        })
        req.headers['Cookie'] = 'fo234{=bar blub=Blah'
        self.assertEqual(req.cookies, {'blub': 'Blah'})

    def test_cookie_quoting(self):
        req = self._blankOne('/')
        req.headers['Cookie'] = 'foo="?foo"; Path=/'
        self.assertEqual(req.cookies, {'foo': '?foo'})

    def test_path_quoting(self):
        path = '/:@&+$,/bar'
        req = self._blankOne(path)
        self.assertEqual(req.path, path)
        self.assertTrue(req.url.endswith(path))

    def test_params(self):
        req = self._blankOne('/?a=1&b=2')
        req.method = 'POST'
        req.body = b'b=3'
        self.assertEqual(list(req.params.items()),
                         [('a', '1'), ('b', '2'), ('b', '3')])
        new_params = req.params.copy()
        self.assertEqual(list(new_params.items()),
                         [('a', '1'), ('b', '2'), ('b', '3')])
        new_params['b'] = '4'
        self.assertEqual(list(new_params.items()), [('a', '1'), ('b', '4')])
        # The key name is \u1000:
        req = self._blankOne('/?%E1%80%80=x')
        val = text_type(b'\u1000', 'unicode_escape')
        self.assertTrue(val in list(req.GET.keys()))
        self.assertEqual(req.GET[val], 'x')

    def test_copy_body(self):
        req = self._blankOne('/', method='POST', body=b'some text',
                            request_body_tempfile_limit=1)
        old_body_file = req.body_file_raw
        req.copy_body()
        self.assertTrue(req.body_file_raw is not old_body_file)
        req = self._blankOne('/', method='POST',
                body_file=UnseekableInput(b'0123456789'), content_length=10)
        self.assertTrue(not hasattr(req.body_file_raw, 'seek'))
        old_body_file = req.body_file_raw
        req.make_body_seekable()
        self.assertTrue(req.body_file_raw is not old_body_file)
        self.assertEqual(req.body, b'0123456789')
        old_body_file = req.body_file
        req.make_body_seekable()
        self.assertTrue(req.body_file_raw is old_body_file)
        self.assertTrue(req.body_file is old_body_file)

    def test_broken_seek(self):
        # copy() should work even when the input has a broken seek method
        req = self._blankOne('/', method='POST',
                body_file=UnseekableInputWithSeek(b'0123456789'),
                content_length=10)
        self.assertTrue(hasattr(req.body_file_raw, 'seek'))
        self.assertRaises(IOError, req.body_file_raw.seek, 0)
        old_body_file = req.body_file
        req2 = req.copy()
        self.assertTrue(req2.body_file_raw is req2.body_file is not
                        old_body_file)
        self.assertEqual(req2.body, b'0123456789')

    def test_set_body(self):
        req = self._blankOne('/', method='PUT', body=b'foo')
        self.assertTrue(req.is_body_seekable)
        self.assertEqual(req.body, b'foo')
        self.assertEqual(req.content_length, 3)
        del req.body
        self.assertEqual(req.body, b'')
        self.assertEqual(req.content_length, 0)

    def test_broken_clen_header(self):
        # if the UA sends "content_length: ..' header (the name is wrong)
        # it should not break the req.headers.items()
        req = self._blankOne('/')
        req.environ['HTTP_CONTENT_LENGTH'] = '0'
        req.headers.items()

    def test_nonstr_keys(self):
        # non-string env keys shouldn't break req.headers
        req = self._blankOne('/')
        req.environ[1] = 1
        req.headers.items()

    def test_authorization(self):
        req = self._blankOne('/')
        req.authorization = 'Digest uri="/?a=b"'
        self.assertEqual(req.authorization, ('Digest', {'uri': '/?a=b'}))

    def test_as_bytes(self):
        req = self._blankOne('http://example.com:8000/test.html?params')
        inp = BytesIO(req.as_bytes())
        self.equal_req(req, inp)

        req = self._blankOne('http://example.com/test2')
        req.method = 'POST'
        req.body = b'test=example'
        inp = BytesIO(req.as_bytes())
        self.equal_req(req, inp)

    def test_as_text(self):
        req = self._blankOne('http://example.com:8000/test.html?params')
        inp = StringIO(req.as_text())
        self.equal_req(req, inp)

        req = self._blankOne('http://example.com/test2')
        req.method = 'POST'
        req.body = b'test=example'
        inp = StringIO(req.as_text())
        self.equal_req(req, inp)

    def test_req_kw_none_val(self):
        request = self._makeOne({}, content_length=None)
        self.assertTrue('content-length' not in request.headers)
        self.assertTrue('content-type' not in request.headers)

    def test_env_keys(self):
        req = self._blankOne('/')
        # SCRIPT_NAME can be missing
        del req.environ['SCRIPT_NAME']
        self.assertEqual(req.script_name, '')
        self.assertEqual(req.uscript_name, '')

    def test_repr_nodefault(self):
        from webob.request import NoDefault
        nd = NoDefault
        self.assertEqual(repr(nd), '(No Default)')

    def test_request_noenviron_param(self):
        # Environ is a a mandatory not null param in Request.
        self.assertRaises(TypeError, self._makeOne, environ=None)

    def test_unexpected_kw(self):
        # Passed an attr in kw that does not exist in the class, should
        # raise an error
        # Passed an attr in kw that does exist in the class, should be ok
        self.assertRaises(TypeError,
                          self._makeOne, {'a':1}, this_does_not_exist=1)
        r = self._makeOne({'a':1}, server_name='127.0.0.1')
        self.assertEqual(getattr(r, 'server_name', None), '127.0.0.1')

    def test_conttype_set_del(self):
        # Deleting content_type attr from a request should update the
        # environ dict
        # Assigning content_type should replace first option of the environ
        # dict
        r = self._makeOne({'a':1}, **{'content_type':'text/html'})
        self.assertTrue('CONTENT_TYPE' in r.environ)
        self.assertTrue(hasattr(r, 'content_type'))
        del r.content_type
        self.assertTrue('CONTENT_TYPE' not in r.environ)
        a = self._makeOne({'a':1},
                content_type='charset=utf-8;application/atom+xml;type=entry')
        self.assertTrue(a.environ['CONTENT_TYPE']==
                'charset=utf-8;application/atom+xml;type=entry')
        a.content_type = 'charset=utf-8'
        self.assertTrue(a.environ['CONTENT_TYPE']==
                'charset=utf-8;application/atom+xml;type=entry')

    def test_headers2(self):
        # Setting headers in init and later with a property, should update
        # the info
        headers = {'Host': 'www.example.com',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '115',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0'}
        r = self._makeOne({'a':1}, headers=headers)
        for i in headers.keys():
            self.assertTrue(i in r.headers and
                'HTTP_'+i.upper().replace('-', '_') in r.environ)
        r.headers = {'Server':'Apache'}
        self.assertEqual(set(r.environ.keys()), set(['a',  'HTTP_SERVER']))

    def test_host_url(self):
        # Request has a read only property host_url that combines several
        # keys to create a host_url
        a = self._makeOne(
            {'wsgi.url_scheme':'http'}, **{'host':'www.example.com'})
        self.assertEqual(a.host_url, 'http://www.example.com')
        a = self._makeOne(
            {'wsgi.url_scheme':'http'}, **{'server_name':'localhost',
                                                'server_port':5000})
        self.assertEqual(a.host_url, 'http://localhost:5000')
        a = self._makeOne(
            {'wsgi.url_scheme':'https'}, **{'server_name':'localhost',
                                            'server_port':443})
        self.assertEqual(a.host_url, 'https://localhost')

    def test_path_info_p(self):
        # Peek path_info to see what's coming
        # Pop path_info until there's nothing remaining
        a = self._makeOne({'a':1}, **{'path_info':'/foo/bar','script_name':''})
        self.assertEqual(a.path_info_peek(), 'foo')
        self.assertEqual(a.path_info_pop(), 'foo')
        self.assertEqual(a.path_info_peek(), 'bar')
        self.assertEqual(a.path_info_pop(), 'bar')
        self.assertEqual(a.path_info_peek(), None)
        self.assertEqual(a.path_info_pop(), None)

    def test_urlvars_property(self):
        # Testing urlvars setter/getter/deleter
        a = self._makeOne({'wsgiorg.routing_args':((),{'x':'y'}),
                           'paste.urlvars':{'test':'value'}})
        a.urlvars = {'hello':'world'}
        self.assertTrue('paste.urlvars' not in a.environ)
        self.assertEqual(a.environ['wsgiorg.routing_args'],
                         ((), {'hello':'world'}))
        del a.urlvars
        self.assertTrue('wsgiorg.routing_args' not in a.environ)
        a = self._makeOne({'paste.urlvars':{'test':'value'}})
        self.assertEqual(a.urlvars, {'test':'value'})
        a.urlvars = {'hello':'world'}
        self.assertEqual(a.environ['paste.urlvars'], {'hello':'world'})
        del a.urlvars
        self.assertTrue('paste.urlvars' not in a.environ)

    def test_urlargs_property(self):
        # Testing urlargs setter/getter/deleter
        a = self._makeOne({'paste.urlvars':{'test':'value'}})
        self.assertEqual(a.urlargs, ())
        a.urlargs = {'hello':'world'}
        self.assertEqual(a.environ['wsgiorg.routing_args'],
                         ({'hello':'world'}, {'test':'value'}))
        a = self._makeOne({'a':1})
        a.urlargs = {'hello':'world'}
        self.assertEqual(a.environ['wsgiorg.routing_args'],
                         ({'hello':'world'}, {}))
        del a.urlargs
        self.assertTrue('wsgiorg.routing_args' not in a.environ)

    def test_host_property(self):
        # Testing host setter/getter/deleter
        a = self._makeOne({'wsgi.url_scheme':'http'}, server_name='localhost',
                          server_port=5000)
        self.assertEqual(a.host, "localhost:5000")
        a.host = "localhost:5000"
        self.assertTrue('HTTP_HOST' in a.environ)
        del a.host
        self.assertTrue('HTTP_HOST' not in a.environ)

    def test_body_property(self):
        # Testing body setter/getter/deleter plus making sure body has a
        # seek method
        #a = Request({'a':1}, **{'CONTENT_LENGTH':'?'})
        # I cannot think of a case where somebody would put anything else
        # than a # numerical value in CONTENT_LENGTH, Google didn't help
        # either
        #self.assertEqual(a.body, '')
        # I need to implement a not seekable stringio like object.

        import string
        class DummyIO(object):
            def __init__(self, txt):
                self.txt = txt
            def read(self, n=-1):
                return self.txt[0:n]
        cls = self._getTargetClass()
        limit = cls.request_body_tempfile_limit
        len_strl = limit // len(string.ascii_letters) + 1
        r = self._makeOne(
            {'a':1, 'REQUEST_METHOD': 'POST'},
            body_file=DummyIO(bytes_(string.ascii_letters) * len_strl))
        self.assertEqual(len(r.body), len(string.ascii_letters*len_strl)-1)
        self.assertRaises(TypeError,
                          setattr, r, 'body', text_('hello world'))
        r.body = None
        self.assertEqual(r.body, b'')
        r = self._makeOne({'a':1}, method='PUT', body_file=DummyIO(
            bytes_(string.ascii_letters)))
        self.assertTrue(not hasattr(r.body_file_raw, 'seek'))
        r.make_body_seekable()
        self.assertTrue(hasattr(r.body_file_raw, 'seek'))
        r = self._makeOne({'a':1}, method='PUT',
                          body_file=BytesIO(bytes_(string.ascii_letters)))
        self.assertTrue(hasattr(r.body_file_raw, 'seek'))
        r.make_body_seekable()
        self.assertTrue(hasattr(r.body_file_raw, 'seek'))

    def test_repr_invalid(self):
        # If we have an invalid WSGI environ, the repr should tell us.
        req = self._makeOne({'CONTENT_LENGTH':'0', 'body':''})
        self.assertTrue(repr(req).endswith('(invalid WSGI environ)>'))

    def test_from_garbage_file(self):
        # If we pass a file with garbage to from_file method it should
        # raise an error plus missing bits in from_file method
        io = BytesIO(b'hello world')

        cls = self._getTargetClass()
        self.assertRaises(ValueError, cls.from_file, io)
        val_file = BytesIO(
            b"GET /webob/ HTTP/1.1\n"
            b"Host: pythonpaste.org\n"
            b"User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13)"
            b"Gecko/20101206 Ubuntu/10.04 (lucid) Firefox/3.6.13\n"
            b"Accept: "
            b"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;"
            b"q=0.8\n"
            b"Accept-Language: en-us,en;q=0.5\n"
            b"Accept-Encoding: gzip,deflate\n"
            b"Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\n"
            # duplicate on purpose
            b"Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\n"
            b"Keep-Alive: 115\n"
            b"Connection: keep-alive\n"
        )
        req = cls.from_file(val_file)
        self.assertTrue(isinstance(req, cls))
        self.assertTrue(not repr(req).endswith('(invalid WSGI environ)>'))
        val_file = BytesIO(
            b"GET /webob/ HTTP/1.1\n"
            b"Host pythonpaste.org\n"
        )
        self.assertRaises(ValueError, cls.from_file, val_file)

    def test_from_bytes(self):
        # A valid request without a Content-Length header should still read
        # the full body.
        # Also test parity between as_string and from_bytes / from_file.
        import cgi
        cls = self._getTargetClass()
        req = cls.from_bytes(_test_req)
        self.assertTrue(isinstance(req, cls))
        self.assertTrue(not repr(req).endswith('(invalid WSGI environ)>'))
        self.assertTrue('\n' not in req.http_version or '\r' in
                        req.http_version)
        self.assertTrue(',' not in req.host)
        self.assertTrue(req.content_length is not None)
        self.assertEqual(req.content_length, 337)
        self.assertTrue(b'foo' in req.body)
        bar_contents = b"these are the contents of the file 'bar.txt'\r\n"
        self.assertTrue(bar_contents in req.body)
        self.assertEqual(req.params['foo'], 'foo')
        bar = req.params['bar']
        self.assertTrue(isinstance(bar, cgi.FieldStorage))
        self.assertEqual(bar.type, 'application/octet-stream')
        bar.file.seek(0)
        self.assertEqual(bar.file.read(), bar_contents)
        # out should equal contents, except for the Content-Length header,
        # so insert that.
        _test_req_copy = _test_req.replace(
            b'Content-Type',
            b'Content-Length: 337\r\nContent-Type'
            )
        self.assertEqual(req.as_bytes(), _test_req_copy)

        req2 = cls.from_bytes(_test_req2)
        self.assertTrue('host' not in req2.headers)
        self.assertEqual(req2.as_bytes(), _test_req2.rstrip())
        self.assertRaises(ValueError, cls.from_bytes, _test_req2 + b'xx')

    def test_from_text(self):
        import cgi
        cls = self._getTargetClass()
        req = cls.from_text(text_(_test_req, 'utf-8'))
        self.assertTrue(isinstance(req, cls))
        self.assertTrue(not repr(req).endswith('(invalid WSGI environ)>'))
        self.assertTrue('\n' not in req.http_version or '\r' in
                        req.http_version)
        self.assertTrue(',' not in req.host)
        self.assertTrue(req.content_length is not None)
        self.assertEqual(req.content_length, 337)
        self.assertTrue(b'foo' in req.body)
        bar_contents = b"these are the contents of the file 'bar.txt'\r\n"
        self.assertTrue(bar_contents in req.body)
        self.assertEqual(req.params['foo'], 'foo')
        bar = req.params['bar']
        self.assertTrue(isinstance(bar, cgi.FieldStorage))
        self.assertEqual(bar.type, 'application/octet-stream')
        bar.file.seek(0)
        self.assertEqual(bar.file.read(), bar_contents)
        # out should equal contents, except for the Content-Length header,
        # so insert that.
        _test_req_copy = _test_req.replace(
            b'Content-Type',
            b'Content-Length: 337\r\nContent-Type'
            )
        self.assertEqual(req.as_bytes(), _test_req_copy)

        req2 = cls.from_bytes(_test_req2)
        self.assertTrue('host' not in req2.headers)
        self.assertEqual(req2.as_bytes(), _test_req2.rstrip())
        self.assertRaises(ValueError, cls.from_bytes, _test_req2 + b'xx')

    def test_blank(self):
        # BaseRequest.blank class method
        self.assertRaises(ValueError, self._blankOne,
                    'www.example.com/foo?hello=world', None,
                    'www.example.com/foo?hello=world')
        self.assertRaises(ValueError, self._blankOne,
                    'gopher.example.com/foo?hello=world', None,
                    'gopher://gopher.example.com')
        req = self._blankOne('www.example.com/foo?hello=world', None,
                             'http://www.example.com')
        self.assertEqual(req.environ.get('HTTP_HOST', None),
                         'www.example.com:80')
        self.assertEqual(req.environ.get('PATH_INFO', None),
                         'www.example.com/foo')
        self.assertEqual(req.environ.get('QUERY_STRING', None),
                         'hello=world')
        self.assertEqual(req.environ.get('REQUEST_METHOD', None), 'GET')
        req = self._blankOne('www.example.com/secure?hello=world', None,
                             'https://www.example.com/secure')
        self.assertEqual(req.environ.get('HTTP_HOST', None),
                         'www.example.com:443')
        self.assertEqual(req.environ.get('PATH_INFO', None),
                         'www.example.com/secure')
        self.assertEqual(req.environ.get('QUERY_STRING', None), 'hello=world')
        self.assertEqual(req.environ.get('REQUEST_METHOD', None), 'GET')
        self.assertEqual(req.environ.get('SCRIPT_NAME', None), '/secure')
        self.assertEqual(req.environ.get('SERVER_NAME', None),
                         'www.example.com')
        self.assertEqual(req.environ.get('SERVER_PORT', None), '443')


    def test_post_does_not_reparse(self):
        # test that there's no repetitive parsing is happening on every
        # req.POST access
        req = self._blankOne('/',
            content_type='multipart/form-data; boundary=boundary',
            POST=_cgi_escaping_body
        )
        f0 = req.body_file_raw
        post1 = req.POST
        f1 = req.body_file_raw
        self.assertTrue(f1 is not f0)
        post2 = req.POST
        f2 = req.body_file_raw
        self.assertTrue(post1 is post2)
        self.assertTrue(f1 is f2)


    def test_middleware_body(self):
        def app(env, sr):
            sr('200 OK', [])
            return [env['wsgi.input'].read()]

        def mw(env, sr):
            req = self._makeOne(env)
            data = req.body_file.read()
            resp = req.get_response(app)
            resp.headers['x-data'] = data
            return resp(env, sr)

        req = self._blankOne('/', method='PUT', body=b'abc')
        resp = req.get_response(mw)
        self.assertEqual(resp.body, b'abc')
        self.assertEqual(resp.headers['x-data'], b'abc')

    def test_body_file_noseek(self):
        req = self._blankOne('/', method='PUT', body=b'abc')
        lst = [req.body_file.read(1) for i in range(3)]
        self.assertEqual(lst, [b'a', b'b', b'c'])

    def test_cgi_escaping_fix(self):
        req = self._blankOne('/',
            content_type='multipart/form-data; boundary=boundary',
            POST=_cgi_escaping_body
        )
        self.assertEqual(list(req.POST.keys()), ['%20%22"'])
        req.body_file.read()
        self.assertEqual(list(req.POST.keys()), ['%20%22"'])

    def test_content_type_none(self):
        r = self._blankOne('/', content_type='text/html')
        self.assertEqual(r.content_type, 'text/html')
        r.content_type = None

    def test_body_file_seekable(self):
        r = self._blankOne('/', method='POST')
        r.body_file = BytesIO(b'body')
        self.assertEqual(r.body_file_seekable.read(), b'body')

    def test_request_init(self):
        # port from doctest (docs/reference.txt)
        req = self._blankOne('/article?id=1')
        self.assertEqual(req.environ['HTTP_HOST'], 'localhost:80')
        self.assertEqual(req.environ['PATH_INFO'], '/article')
        self.assertEqual(req.environ['QUERY_STRING'], 'id=1')
        self.assertEqual(req.environ['REQUEST_METHOD'], 'GET')
        self.assertEqual(req.environ['SCRIPT_NAME'], '')
        self.assertEqual(req.environ['SERVER_NAME'], 'localhost')
        self.assertEqual(req.environ['SERVER_PORT'], '80')
        self.assertEqual(req.environ['SERVER_PROTOCOL'], 'HTTP/1.0')
        self.assertTrue(hasattr(req.environ['wsgi.errors'], 'write') and
                     hasattr(req.environ['wsgi.errors'], 'flush'))
        self.assertTrue(hasattr(req.environ['wsgi.input'], 'next') or
                     hasattr(req.environ['wsgi.input'], '__next__'))
        self.assertEqual(req.environ['wsgi.multiprocess'], False)
        self.assertEqual(req.environ['wsgi.multithread'], False)
        self.assertEqual(req.environ['wsgi.run_once'], False)
        self.assertEqual(req.environ['wsgi.url_scheme'], 'http')
        self.assertEqual(req.environ['wsgi.version'], (1, 0))

        # Test body
        self.assertTrue(hasattr(req.body_file, 'read'))
        self.assertEqual(req.body, b'')
        req.method = 'PUT'
        req.body = b'test'
        self.assertTrue(hasattr(req.body_file, 'read'))
        self.assertEqual(req.body, b'test')

        # Test method & URL
        self.assertEqual(req.method, 'PUT')
        self.assertEqual(req.scheme, 'http')
        self.assertEqual(req.script_name, '') # The base of the URL
        req.script_name = '/blog'  # make it more interesting
        self.assertEqual(req.path_info, '/article')
        # Content-Type of the request body
        self.assertEqual(req.content_type, '')
        # The auth'ed user (there is none set)
        self.assertTrue(req.remote_user is None)
        self.assertTrue(req.remote_addr is None)
        self.assertEqual(req.host, 'localhost:80')
        self.assertEqual(req.host_url, 'http://localhost')
        self.assertEqual(req.application_url, 'http://localhost/blog')
        self.assertEqual(req.path_url, 'http://localhost/blog/article')
        self.assertEqual(req.url, 'http://localhost/blog/article?id=1')
        self.assertEqual(req.path, '/blog/article')
        self.assertEqual(req.path_qs, '/blog/article?id=1')
        self.assertEqual(req.query_string, 'id=1')
        self.assertEqual(req.relative_url('archive'),
                         'http://localhost/blog/archive')

        # Doesn't change request
        self.assertEqual(req.path_info_peek(), 'article')
        # Does change request!
        self.assertEqual(req.path_info_pop(), 'article')
        self.assertEqual(req.script_name, '/blog/article')
        self.assertEqual(req.path_info, '')

        # Headers
        req.headers['Content-Type'] = 'application/x-www-urlencoded'
        self.assertEqual(sorted(req.headers.items()),
                         [('Content-Length', '4'),
                          ('Content-Type', 'application/x-www-urlencoded'),
                          ('Host', 'localhost:80')])
        self.assertEqual(req.environ['CONTENT_TYPE'],
                         'application/x-www-urlencoded')

    def test_request_query_and_POST_vars(self):
        # port from doctest (docs/reference.txt)

        # Query & POST variables
        from webob.multidict import MultiDict
        from webob.multidict import NestedMultiDict
        from webob.multidict import NoVars
        from webob.multidict import GetDict
        req = self._blankOne('/test?check=a&check=b&name=Bob')
        GET = GetDict([('check', 'a'),
                      ('check', 'b'),
                      ('name', 'Bob')], {})
        self.assertEqual(req.GET, GET)
        self.assertEqual(req.GET['check'], 'b')
        self.assertEqual(req.GET.getall('check'), ['a', 'b'])
        self.assertEqual(list(req.GET.items()),
                         [('check', 'a'), ('check', 'b'), ('name', 'Bob')])

        self.assertTrue(isinstance(req.POST, NoVars))
        # NoVars can be read like a dict, but not written
        self.assertEqual(list(req.POST.items()), [])
        req.method = 'POST'
        req.body = b'name=Joe&email=joe@example.com'
        self.assertEqual(req.POST,
                         MultiDict([('name', 'Joe'),
                                    ('email', 'joe@example.com')]))
        self.assertEqual(req.POST['name'], 'Joe')

        self.assertTrue(isinstance(req.params, NestedMultiDict))
        self.assertEqual(list(req.params.items()),
                         [('check', 'a'),
                          ('check', 'b'),
                          ('name', 'Bob'),
                          ('name', 'Joe'),
                          ('email', 'joe@example.com')])
        self.assertEqual(req.params['name'], 'Bob')
        self.assertEqual(req.params.getall('name'), ['Bob', 'Joe'])

    def test_request_put(self):
        from datetime import datetime
        from webob import Response
        from webob import UTC
        from webob.acceptparse import MIMEAccept
        from webob.byterange import Range
        from webob.etag import ETagMatcher
        from webob.multidict import MultiDict
        from webob.multidict import GetDict
        req = self._blankOne('/test?check=a&check=b&name=Bob')
        req.method = 'PUT'
        req.body = b'var1=value1&var2=value2&rep=1&rep=2'
        req.environ['CONTENT_LENGTH'] = str(len(req.body))
        req.environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        GET = GetDict([('check', 'a'),
                      ('check', 'b'),
                      ('name', 'Bob')], {})
        self.assertEqual(req.GET, GET)
        self.assertEqual(req.POST, MultiDict(
                                [('var1', 'value1'),
                                 ('var2', 'value2'),
                                 ('rep', '1'),
                                 ('rep', '2')]))
        self.assertEqual(
            list(req.GET.items()),
            [('check', 'a'), ('check', 'b'), ('name', 'Bob')])

        # Unicode
        req.charset = 'utf8'
        self.assertEqual(list(req.GET.items()),
                         [('check', 'a'), ('check', 'b'), ('name', 'Bob')])

        # Cookies
        req.headers['Cookie'] = 'test=value'
        self.assertTrue(isinstance(req.cookies, collections.MutableMapping))
        self.assertEqual(list(req.cookies.items()), [('test', 'value')])
        req.charset = None
        self.assertEqual(req.cookies, {'test': 'value'})

        # Accept-* headers
        self.assertTrue('text/html' in req.accept)
        req.accept = 'text/html;q=0.5, application/xhtml+xml;q=1'
        self.assertTrue(isinstance(req.accept, MIMEAccept))
        self.assertTrue('text/html' in req.accept)

        self.assertRaises(DeprecationWarning,
                          req.accept.first_match, ['text/html'])
        self.assertEqual(req.accept.best_match(['text/html',
                                                'application/xhtml+xml']),
                         'application/xhtml+xml')

        req.accept_language = 'es, pt-BR'
        self.assertEqual(req.accept_language.best_match(['es']), 'es')

        # Conditional Requests
        server_token = 'opaque-token'
        # shouldn't return 304
        self.assertTrue(not server_token in req.if_none_match)
        req.if_none_match = server_token
        self.assertTrue(isinstance(req.if_none_match, ETagMatcher))
        # You *should* return 304
        self.assertTrue(server_token in req.if_none_match)
        # if_none_match should use weak matching
        weak_token = 'W/"%s"' % server_token
        req.if_none_match = weak_token
        assert req.headers['if-none-match'] == weak_token
        self.assertTrue(server_token in req.if_none_match)


        req.if_modified_since = datetime(2006, 1, 1, 12, 0, tzinfo=UTC)
        self.assertEqual(req.headers['If-Modified-Since'],
                         'Sun, 01 Jan 2006 12:00:00 GMT')
        server_modified = datetime(2005, 1, 1, 12, 0, tzinfo=UTC)
        self.assertTrue(req.if_modified_since)
        self.assertTrue(req.if_modified_since >= server_modified)

        self.assertTrue(not req.if_range)
        self.assertTrue(Response(etag='some-etag',
                              last_modified=datetime(2005, 1, 1, 12, 0))
            in req.if_range)
        req.if_range = 'opaque-etag'
        self.assertTrue(Response(etag='other-etag') not in req.if_range)
        self.assertTrue(Response(etag='opaque-etag') in req.if_range)

        res = Response(etag='opaque-etag')
        self.assertTrue(res in req.if_range)

        req.range = 'bytes=0-100'
        self.assertTrue(isinstance(req.range, Range))
        self.assertEqual(tuple(req.range), (0, 101))
        cr = req.range.content_range(length=1000)
        self.assertEqual(tuple(cr), (0, 101, 1000))

        self.assertTrue(server_token in req.if_match)
        # No If-Match means everything is ok
        req.if_match = server_token
        self.assertTrue(server_token in req.if_match)
        # Still OK
        req.if_match = 'other-token'
        # Not OK, should return 412 Precondition Failed:
        self.assertTrue(not server_token in req.if_match)

    def test_request_patch(self):
        from webob.multidict import MultiDict
        from webob.multidict import GetDict
        req = self._blankOne('/test?check=a&check=b&name=Bob')
        req.method = 'PATCH'
        req.body = b'var1=value1&var2=value2&rep=1&rep=2'
        req.environ['CONTENT_LENGTH'] = str(len(req.body))
        req.environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        GET = GetDict([('check', 'a'),
                      ('check', 'b'),
                      ('name', 'Bob')], {})
        self.assertEqual(req.GET, GET)
        self.assertEqual(req.POST, MultiDict(
                                [('var1', 'value1'),
                                 ('var2', 'value2'),
                                 ('rep', '1'),
                                 ('rep', '2')]))

    def test_call_WSGI_app(self):
        req = self._blankOne('/')
        def wsgi_app(environ, start_response):
            start_response('200 OK', [('Content-type', 'text/plain')])
            return [b'Hi!']
        self.assertEqual(req.call_application(wsgi_app),
                         ('200 OK', [('Content-type', 'text/plain')],
                          [b'Hi!']))

        res = req.get_response(wsgi_app)
        from webob.response import Response
        self.assertTrue(isinstance(res, Response))
        self.assertEqual(res.status, '200 OK')
        from webob.headers import ResponseHeaders
        self.assertTrue(isinstance(res.headers, ResponseHeaders))
        self.assertEqual(list(res.headers.items()),
                         [('Content-type', 'text/plain')])
        self.assertEqual(res.body, b'Hi!')

    def test_get_response_catch_exc_info_true(self):
        req = self._blankOne('/')
        def wsgi_app(environ, start_response):
            start_response('200 OK', [('Content-type', 'text/plain')])
            return [b'Hi!']
        res = req.get_response(wsgi_app, catch_exc_info=True)
        from webob.response import Response
        self.assertTrue(isinstance(res, Response))
        self.assertEqual(res.status, '200 OK')
        from webob.headers import ResponseHeaders
        self.assertTrue(isinstance(res.headers, ResponseHeaders))
        self.assertEqual(list(res.headers.items()),
                         [('Content-type', 'text/plain')])
        self.assertEqual(res.body, b'Hi!')

    def equal_req(self, req, inp):
        cls = self._getTargetClass()
        req2 = cls.from_file(inp)
        self.assertEqual(req.url, req2.url)
        headers1 = dict(req.headers)
        headers2 = dict(req2.headers)
        self.assertEqual(int(headers1.get('Content-Length', '0')),
            int(headers2.get('Content-Length', '0')))
        if 'Content-Length' in headers1:
            del headers1['Content-Length']
        if 'Content-Length' in headers2:
            del headers2['Content-Length']
        self.assertEqual(headers1, headers2)
        req_body = req.body
        req2_body = req2.body
        self.assertEqual(req_body, req2_body)

class FakeCGIBodyTests(unittest.TestCase):
    def test_encode_multipart_value_type_options(self):
        from cgi import FieldStorage
        from webob.request import BaseRequest, FakeCGIBody
        from webob.multidict import MultiDict
        multipart_type = 'multipart/form-data; boundary=foobar'
        from io import BytesIO
        body = (
            b'--foobar\r\n'
            b'Content-Disposition: form-data; name="bananas"; '
                    b'filename="bananas.txt"\r\n'
            b'Content-type: text/plain; charset="utf-7"\r\n'
            b'\r\n'
            b"these are the contents of the file 'bananas.txt'\r\n"
            b'\r\n'
            b'--foobar--')
        multipart_body = BytesIO(body)
        environ = BaseRequest.blank('/').environ
        environ.update(CONTENT_TYPE=multipart_type)
        environ.update(REQUEST_METHOD='POST')
        environ.update(CONTENT_LENGTH=len(body))
        fs = FieldStorage(multipart_body, environ=environ)
        vars = MultiDict.from_fieldstorage(fs)
        self.assertEqual(vars['bananas'].__class__, FieldStorage)
        fake_body = FakeCGIBody(vars, multipart_type)
        self.assertEqual(fake_body.read(), body)

    def test_encode_multipart_no_boundary(self):
        from webob.request import FakeCGIBody
        self.assertRaises(ValueError, FakeCGIBody, {}, 'multipart/form-data')

    def test_repr(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'multipart/form-data; boundary=foobar')
        body.read(1)
        import re
        self.assertEqual(
            re.sub(r'\b0x[0-9a-f]+\b', '<whereitsat>', repr(body)),
            "<FakeCGIBody at <whereitsat> viewing {'bananas': 'ba...nas'}>",
        )

    def test_fileno(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'multipart/form-data; boundary=foobar')
        self.assertEqual(body.fileno(), None)

    def test_iter(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'multipart/form-data; boundary=foobar')
        self.assertEqual(list(body), [
            b'--foobar\r\n',
            b'Content-Disposition: form-data; name="bananas"\r\n',
            b'\r\n',
            b'bananas\r\n',
            b'--foobar--',
         ])

    def test_readline(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'multipart/form-data; boundary=foobar')
        self.assertEqual(body.readline(), b'--foobar\r\n')
        self.assertEqual(
            body.readline(),
            b'Content-Disposition: form-data; name="bananas"\r\n')
        self.assertEqual(body.readline(), b'\r\n')
        self.assertEqual(body.readline(), b'bananas\r\n')
        self.assertEqual(body.readline(), b'--foobar--')
        # subsequent calls to readline will return ''

    def test_read_bad_content_type(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'}, 'application/jibberjabber')
        self.assertRaises(AssertionError, body.read)

    def test_read_urlencoded(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'application/x-www-form-urlencoded')
        self.assertEqual(body.read(), b'bananas=bananas')


class Test_cgi_FieldStorage__repr__patch(unittest.TestCase):
    def _callFUT(self, fake):
        from webob.request import _cgi_FieldStorage__repr__patch
        return _cgi_FieldStorage__repr__patch(fake)

    def test_with_file(self):
        class Fake(object):
            name = 'name'
            file = 'file'
            filename = 'filename'
            value = 'value'
        fake = Fake()
        result = self._callFUT(fake)
        self.assertEqual(result, "FieldStorage('name', 'filename')")

    def test_without_file(self):
        class Fake(object):
            name = 'name'
            file = None
            filename = 'filename'
            value = 'value'
        fake = Fake()
        result = self._callFUT(fake)
        self.assertEqual(result, "FieldStorage('name', 'filename', 'value')")


class TestLimitedLengthFile(unittest.TestCase):
    def _makeOne(self, file, maxlen):
        from webob.request import LimitedLengthFile
        return LimitedLengthFile(file, maxlen)

    def test_fileno(self):
        class DummyFile(object):
            def fileno(self):
                return 1
        dummyfile = DummyFile()
        inst = self._makeOne(dummyfile, 0)
        self.assertEqual(inst.fileno(), 1)


class Test_environ_from_url(unittest.TestCase):
    def _callFUT(self, *arg, **kw):
        from webob.request import environ_from_url
        return environ_from_url(*arg, **kw)

    def test_environ_from_url(self):
        # Generating an environ just from an url plus testing environ_add_POST
        self.assertRaises(TypeError, self._callFUT,
                    'http://www.example.com/foo?bar=baz#qux')
        self.assertRaises(TypeError, self._callFUT,
                    'gopher://gopher.example.com')
        req = self._callFUT('http://www.example.com/foo?bar=baz')
        self.assertEqual(req.get('HTTP_HOST', None), 'www.example.com:80')
        self.assertEqual(req.get('PATH_INFO', None), '/foo')
        self.assertEqual(req.get('QUERY_STRING', None), 'bar=baz')
        self.assertEqual(req.get('REQUEST_METHOD', None), 'GET')
        self.assertEqual(req.get('SCRIPT_NAME', None), '')
        self.assertEqual(req.get('SERVER_NAME', None), 'www.example.com')
        self.assertEqual(req.get('SERVER_PORT', None), '80')
        req = self._callFUT('https://www.example.com/foo?bar=baz')
        self.assertEqual(req.get('HTTP_HOST', None), 'www.example.com:443')
        self.assertEqual(req.get('PATH_INFO', None), '/foo')
        self.assertEqual(req.get('QUERY_STRING', None), 'bar=baz')
        self.assertEqual(req.get('REQUEST_METHOD', None), 'GET')
        self.assertEqual(req.get('SCRIPT_NAME', None), '')
        self.assertEqual(req.get('SERVER_NAME', None), 'www.example.com')
        self.assertEqual(req.get('SERVER_PORT', None), '443')


        from webob.request import environ_add_POST

        environ_add_POST(req, None)
        self.assertTrue('CONTENT_TYPE' not in req)
        self.assertTrue('CONTENT_LENGTH' not in req)
        environ_add_POST(req, {'hello':'world'})
        self.assertTrue(req.get('HTTP_HOST', None), 'www.example.com:443')
        self.assertEqual(req.get('PATH_INFO', None), '/foo')
        self.assertEqual(req.get('QUERY_STRING', None), 'bar=baz')
        self.assertEqual(req.get('REQUEST_METHOD', None), 'POST')
        self.assertEqual(req.get('SCRIPT_NAME', None), '')
        self.assertEqual(req.get('SERVER_NAME', None), 'www.example.com')
        self.assertEqual(req.get('SERVER_PORT', None), '443')
        self.assertEqual(req.get('CONTENT_LENGTH', None),'11')
        self.assertEqual(req.get('CONTENT_TYPE', None),
                         'application/x-www-form-urlencoded')
        self.assertEqual(req['wsgi.input'].read(), b'hello=world')

    def test_environ_from_url_highorder_path_info(self):
        from webob.request import Request
        env = self._callFUT('/%E6%B5%81')
        self.assertEqual(env['PATH_INFO'], '/\xe6\xb5\x81')
        request = Request(env)
        expected = text_(b'/\xe6\xb5\x81', 'utf-8') # u'/\u6d41'
        self.assertEqual(request.path_info, expected)
        self.assertEqual(request.upath_info, expected)

    def test_fileupload_mime_type_detection(self):
        from webob.request import Request
        # sometimes on win the detected mime type for .jpg will be
        # image/pjpeg for ex. so use a non-standard extesion to avoid that
        import mimetypes
        mimetypes.add_type('application/x-foo', '.foo')
        request = Request.blank("/", POST=dict(file1=("foo.foo", "xxx"),
                                               file2=("bar.mp3", "xxx")))
        self.assertTrue("audio/mpeg" in request.body.decode('ascii'),
                        str(request))
        self.assertTrue('application/x-foo' in request.body.decode('ascii'),
                        str(request))

class TestRequestMultipart(unittest.TestCase):
    def test_multipart_with_charset(self):
        from webob.request import Request
        req = Request.from_bytes(_test_req_multipart_charset)
        self.assertEqual(req.POST['title'].encode('utf8'),
                         text_('こんにちは', 'utf-8').encode('utf8'))

def simpleapp(environ, start_response):
    from webob.request import Request
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    request = Request(environ)
    request.remote_user = 'bob'
    return [ bytes_(x) for x in [
        'Hello world!\n',
        'The get is %r' % request.GET,
        ' and Val is %s\n' % repr(request.GET.get('name')),
        'The languages are: %s\n' % list(request.accept_language),
        'The accepttypes is: %s\n' %
            request.accept.best_match(['application/xml', 'text/html']),
        'post is %r\n' % request.POST,
        'params is %r\n' % request.params,
        'cookies is %r\n' % request.cookies,
        'body: %r\n' % request.body,
        'method: %s\n' % request.method,
        'remote_user: %r\n' % request.environ['REMOTE_USER'],
        'host_url: %r; application_url: %r; path_url: %r; url: %r\n' %
            (request.host_url,
             request.application_url,
             request.path_url,
             request.url),
        'urlvars: %r\n' % request.urlvars,
        'urlargs: %r\n' % (request.urlargs, ),
        'is_xhr: %r\n' % request.is_xhr,
        'if_modified_since: %r\n' % request.if_modified_since,
        'user_agent: %r\n' % request.user_agent,
        'if_none_match: %r\n' % request.if_none_match,
        ]]

_cgi_escaping_body = '''--boundary
Content-Disposition: form-data; name="%20%22""


--boundary--'''

def _norm_req(s):
    return b'\r\n'.join(s.strip().replace(b'\r', b'').split(b'\n'))

_test_req = b"""
POST /webob/ HTTP/1.0
Accept: */*
Cache-Control: max-age=0
Content-Type: multipart/form-data; boundary=----------------------------deb95b63e42a
Host: pythonpaste.org
User-Agent: UserAgent/1.0 (identifier-version) library/7.0 otherlibrary/0.8

------------------------------deb95b63e42a
Content-Disposition: form-data; name="foo"

foo
------------------------------deb95b63e42a
Content-Disposition: form-data; name="bar"; filename="bar.txt"
Content-type: application/octet-stream

these are the contents of the file 'bar.txt'

------------------------------deb95b63e42a--
"""

_test_req2 = b"""
POST / HTTP/1.0
Content-Length: 0

"""

_test_req_multipart_charset = b"""
POST /upload/ HTTP/1.1
Host: foo.com
User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) Gecko/20101206 Ubuntu/10.04 (lucid) Firefox/3.6.13
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: en-US,en;q=0.8,ja;q=0.6
Accept-Encoding: gzip,deflate
Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7
Content-Type: multipart/form-data; boundary=000e0ce0b196b4ee6804c6c8af94
Content-Length: 926

--000e0ce0b196b4ee6804c6c8af94
Content-Type: text/plain; charset=ISO-2022-JP
Content-Disposition: form-data; name=title
Content-Transfer-Encoding: 7bit

\x1b$B$3$s$K$A$O\x1b(B
--000e0ce0b196b4ee6804c6c8af94
Content-Type: text/plain; charset=ISO-8859-1
Content-Disposition: form-data; name=submit

Submit
--000e0ce0b196b4ee6804c6c8af94
Content-Type: message/external-body; charset=ISO-8859-1; blob-key=AMIfv94TgpPBtKTL3a0U9Qh1QCX7OWSsmdkIoD2ws45kP9zQAGTOfGNz4U18j7CVXzODk85WtiL5gZUFklTGY3y4G0Jz3KTPtJBOFDvQHQew7YUymRIpgUXgENS_fSEmInAIQdpSc2E78MRBVEZY392uhph3r-In96t8Z58WIRc-Yikx1bnarWo
Content-Disposition: form-data; name=file; filename="photo.jpg"

Content-Type: image/jpeg
Content-Length: 38491
X-AppEngine-Upload-Creation: 2012-08-08 15:32:29.035959
Content-MD5: ZjRmNGRhYmNhZTkyNzcyOWQ5ZGUwNDgzOWFkNDAxN2Y=
Content-Disposition: form-data; name=file; filename="photo.jpg"


--000e0ce0b196b4ee6804c6c8af94--"""


_test_req = _norm_req(_test_req)
_test_req2 = _norm_req(_test_req2) + b'\r\n'
_test_req_multipart_charset = _norm_req(_test_req_multipart_charset)

class UnseekableInput(object):
    def __init__(self, data):
        self.data = data
        self.pos = 0
    def read(self, size=-1):
        if size == -1:
            t = self.data[self.pos:]
            self.pos = len(self.data)
            return t
        else:
            assert(self.pos + size <= len(self.data))
            t = self.data[self.pos:self.pos+size]
            self.pos += size
            return t

class UnseekableInputWithSeek(UnseekableInput):
    def seek(self, pos, rel=0):
        raise IOError("Invalid seek!")

########NEW FILE########
__FILENAME__ = test_request_nose
from webob.request import Request
from nose.tools import eq_ as eq, assert_raises
from webob.compat import bytes_

def test_request_no_method():
    assert Request({}).method == 'GET'

def test_request_read_no_content_length():
    req, input = _make_read_tracked_request(b'abc', 'FOO')
    assert req.content_length is None
    assert req.body == b''
    assert not input.was_read

def test_request_read_no_content_length_POST():
    req, input = _make_read_tracked_request(b'abc', 'POST')
    assert req.content_length is None
    assert req.body == b'abc'
    assert input.was_read

def test_request_read_no_flag_but_content_length_is_present():
    req, input = _make_read_tracked_request(b'abc')
    req.content_length = 3
    assert req.body == b'abc'
    assert input.was_read

def test_request_read_no_content_length_but_flagged_readable():
    req, input = _make_read_tracked_request(b'abc')
    req.is_body_readable = True
    assert req.body == b'abc'
    assert input.was_read

def test_request_read_after_setting_body_file():
    req = _make_read_tracked_request()[0]
    input = req.body_file = ReadTracker(b'abc')
    assert req.content_length is None
    assert not req.is_body_seekable
    assert req.body == b'abc'
    # reading body made the input seekable and set the clen
    assert req.content_length == 3
    assert req.is_body_seekable
    assert input.was_read

def test_request_readlines():
    req = Request.blank('/', POST='a\n'*3)
    req.is_body_seekable = False
    eq(req.body_file.readlines(), [b'a\n'] * 3)

def test_request_delete_with_body():
    req = Request.blank('/', method='DELETE')
    assert not req.is_body_readable
    req.body = b'abc'
    assert req.is_body_readable
    assert req.body_file.read() == b'abc'


def _make_read_tracked_request(data='', method='PUT'):
    input = ReadTracker(data)
    env = {
        'REQUEST_METHOD': method,
        'wsgi.input': input,
    }
    return Request(env), input

class ReadTracker(object):
    """
        Helper object to determine if the input was read or not
    """
    def __init__(self, data):
        self.data = data
        self.was_read = False
    def read(self, size=-1):
        if size < 0:
            size = len(self.data)
        assert size == len(self.data)
        self.was_read = True
        return self.data


def test_limited_length_file_repr():
    req = Request.blank('/', POST='x')
    req.body_file_raw = 'dummy'
    req.is_body_seekable = False
    eq(repr(req.body_file.raw), "<LimitedLengthFile('dummy', maxlen=1)>")

def test_request_wrong_clen(is_seekable=False):
    tlen = 1<<20
    req = Request.blank('/', POST='x'*tlen)
    eq(req.content_length, tlen)
    req.body_file = _Helper_test_request_wrong_clen(req.body_file)
    eq(req.content_length, None)
    req.content_length = tlen + 100
    req.is_body_seekable = is_seekable
    eq(req.content_length, tlen+100)
    # this raises AssertionError if the body reading
    # trusts content_length too much
    assert_raises(IOError, req.copy_body)

def test_request_wrong_clen_seekable():
    test_request_wrong_clen(is_seekable=True)

class _Helper_test_request_wrong_clen(object):
    def __init__(self, f):
        self.f = f
        self.file_ended = False

    def read(self, *args):
        r = self.f.read(*args)
        if not r:
            if self.file_ended:
                raise AssertionError("Reading should stop after first empty string")
            self.file_ended = True
        return r


def test_disconnect_detection_cgi():
    data = 'abc'*(1<<20)
    req = Request.blank('/', POST={'file':('test-file', data)})
    req.is_body_seekable = False
    req.POST # should not raise exceptions

def test_disconnect_detection_hinted_readline():
    data = 'abc'*(1<<20)
    req = Request.blank('/', POST=data)
    req.is_body_seekable = False
    line = req.body_file.readline(1<<16)
    assert line
    assert bytes_(data).startswith(line)



def test_charset_in_content_type():
    # should raise no exception
    req = Request({
        'REQUEST_METHOD': 'POST',
        'QUERY_STRING':'a=b',
        'CONTENT_TYPE':'text/html;charset=ascii'
    })
    eq(req.charset, 'ascii')
    eq(dict(req.GET), {'a': 'b'})
    eq(dict(req.POST), {})
    req.charset = 'ascii' # no exception
    assert_raises(DeprecationWarning, setattr, req, 'charset', 'utf-8')

    # again no exception
    req = Request({
        'REQUEST_METHOD': 'POST',
        'QUERY_STRING':'a=b',
        'CONTENT_TYPE':'multipart/form-data;charset=ascii'
    })
    eq(req.charset, 'ascii')
    eq(dict(req.GET), {'a': 'b'})
    assert_raises(DeprecationWarning, getattr, req, 'POST')




def test_json_body_invalid_json():
    request = Request.blank('/', POST=b'{')
    assert_raises(ValueError, getattr, request, 'json_body')

def test_json_body_valid_json():
    request = Request.blank('/', POST=b'{"a":1}')
    eq(request.json_body, {'a':1})

def test_json_body_alternate_charset():
    import json
    body = (b'\xff\xfe{\x00"\x00a\x00"\x00:\x00 \x00"\x00/\x00\\\x00u\x006\x00d\x004\x001\x00'
        b'\\\x00u\x008\x008\x004\x00c\x00\\\x00u\x008\x00d\x008\x00b\x00\\\x00u\x005\x002\x00'
        b'b\x00f\x00"\x00}\x00'
    )
    request = Request.blank('/', POST=body)
    request.content_type = 'application/json; charset=utf-16'
    s = request.json_body['a']
    eq(s.encode('utf8'), b'/\xe6\xb5\x81\xe8\xa1\x8c\xe8\xb6\x8b\xe5\x8a\xbf')

def test_json_body_GET_request():
    request = Request.blank('/')
    assert_raises(ValueError, getattr, request, 'json_body')

def test_non_ascii_body_params():
    body = b'test=%D1%82%D0%B5%D1%81%D1%82'
    req = Request.blank('/', POST=body)
    # acessing params parses request body
    req.params
    # accessing body again makes the POST dict serialize again
    # make sure it can handle the non-ascii characters in the query
    eq(req.body, body)

########NEW FILE########
__FILENAME__ = test_response
import zlib
import io

from nose.tools import eq_, ok_, assert_raises

from webob.request import BaseRequest
from webob.request import Request
from webob.response import Response
from webob.compat import text_
from webob.compat import bytes_

def simple_app(environ, start_response):
    start_response('200 OK', [
        ('Content-Type', 'text/html; charset=utf8'),
        ])
    return ['OK']

def test_response():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    assert res.status == '200 OK'
    assert res.status_code == 200
    assert res.body == "OK"
    assert res.charset == 'utf8'
    assert res.content_type == 'text/html'
    res.status = 404
    assert res.status == '404 Not Found'
    assert res.status_code == 404
    res.body = b'Not OK'
    assert b''.join(res.app_iter) == b'Not OK'
    res.charset = 'iso8859-1'
    assert res.headers['content-type'] == 'text/html; charset=iso8859-1'
    res.content_type = 'text/xml'
    assert res.headers['content-type'] == 'text/xml; charset=iso8859-1'
    res.headers = {'content-type': 'text/html'}
    assert res.headers['content-type'] == 'text/html'
    assert res.headerlist == [('content-type', 'text/html')]
    res.set_cookie('x', 'y')
    assert res.headers['set-cookie'].strip(';') == 'x=y; Path=/'
    res.set_cookie(text_('x'), text_('y'))
    assert res.headers['set-cookie'].strip(';') == 'x=y; Path=/'
    res = Response('a body', '200 OK', content_type='text/html')
    res.encode_content()
    assert res.content_encoding == 'gzip'
    eq_(res.body, b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xffKTH\xcaO\xa9\x04\x00\xf6\x86GI\x06\x00\x00\x00')
    res.decode_content()
    assert res.content_encoding is None
    assert res.body == b'a body'
    res.set_cookie('x', text_(b'foo')) # test unicode value
    assert_raises(TypeError, Response, app_iter=iter(['a']),
                  body="somebody")
    del req.environ
    assert_raises(TypeError, Response, charset=None,
                  body=text_(b"unicode body"))
    assert_raises(TypeError, Response, wrong_key='dummy')

def test_set_response_status_binary():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    res.status == b'200 OK'
    assert res.status_code == 200
    assert res.status == '200 OK'

def test_set_response_status_str_no_reason():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    res.status = '200'
    assert res.status_code == 200
    assert res.status == '200 OK'

def test_set_response_status_str_generic_reason():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    res.status = '299'
    assert res.status_code == 299
    assert res.status == '299 Success'

def test_set_response_status_code():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    res.status_code = 200
    assert res.status_code == 200
    assert res.status == '200 OK'

def test_set_response_status_code_generic_reason():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    res.status_code = 299
    assert res.status_code == 299
    assert res.status == '299 Success'

def test_content_type():
    r = Response()
    # default ctype and charset
    eq_(r.content_type, 'text/html')
    eq_(r.charset, 'UTF-8')
    # setting to none, removes the header
    r.content_type = None
    eq_(r.content_type, None)
    eq_(r.charset, None)
    # can set missing ctype
    r.content_type = None
    eq_(r.content_type, None)

def test_init_content_type_w_charset():
    v = 'text/plain;charset=ISO-8859-1'
    eq_(Response(content_type=v).headers['content-type'], v)


def test_cookies():
    res = Response()
    # test unicode value
    res.set_cookie('x', text_(b'\N{BLACK SQUARE}', 'unicode_escape'))
    # utf8 encoded
    eq_(res.headers.getall('set-cookie'), ['x="\\342\\226\\240"; Path=/'])
    r2 = res.merge_cookies(simple_app)
    r2 = BaseRequest.blank('/').get_response(r2)
    eq_(r2.headerlist,
        [('Content-Type', 'text/html; charset=utf8'),
        ('Set-Cookie', 'x="\\342\\226\\240"; Path=/'),
        ]
    )

def test_http_only_cookie():
    req = Request.blank('/')
    res = req.get_response(Response('blah'))
    res.set_cookie("foo", "foo", httponly=True)
    eq_(res.headers['set-cookie'], 'foo=foo; Path=/; HttpOnly')

def test_headers():
    r = Response()
    tval = 'application/x-test'
    r.headers.update({'content-type': tval})
    eq_(r.headers.getall('content-type'), [tval])
    r.headers.clear()
    assert not r.headerlist

def test_response_copy():
    r = Response(app_iter=iter(['a']))
    r2 = r.copy()
    eq_(r.body, 'a')
    eq_(r2.body, 'a')

def test_response_copy_content_md5():
    res = Response()
    res.md5_etag(set_content_md5=True)
    assert res.content_md5
    res2 = res.copy()
    assert res.content_md5
    assert res2.content_md5
    eq_(res.content_md5, res2.content_md5)

def test_HEAD_closes():
    req = Request.blank('/')
    req.method = 'HEAD'
    app_iter = io.BytesIO(b'foo')
    res = req.get_response(Response(app_iter=app_iter))
    eq_(res.status_code, 200)
    eq_(res.body, b'')
    ok_(app_iter.closed)

def test_HEAD_conditional_response_returns_empty_response():
    req = Request.blank('/',
        method='HEAD',
        if_none_match='none'
    )
    res = Response(conditional_response=True)
    def start_response(status, headerlist):
        pass
    result = res(req.environ, start_response)
    assert not list(result)

def test_HEAD_conditional_response_range_empty_response():
    req = Request.blank('/',
        method = 'HEAD',
        range=(4,5),
    )
    res = Response('Are we not men?', conditional_response=True)
    assert req.get_response(res).body == b''


def test_conditional_response_if_none_match_false():
    req = Request.blank('/', if_none_match='foo')
    resp = Response(app_iter=['foo\n'],
            conditional_response=True, etag='bar')
    resp = req.get_response(resp)
    eq_(resp.status_code, 200)

def test_conditional_response_if_none_match_true():
    req = Request.blank('/', if_none_match='foo')
    resp = Response(app_iter=['foo\n'],
            conditional_response=True, etag='foo')
    resp = req.get_response(resp)
    eq_(resp.status_code, 304)

def test_conditional_response_if_none_match_weak():
    req = Request.blank('/', headers={'if-none-match': '"bar"'})
    req_weak = Request.blank('/', headers={'if-none-match': 'W/"bar"'})
    resp = Response(app_iter=['foo\n'], conditional_response=True, etag='bar')
    resp_weak = Response(app_iter=['foo\n'], conditional_response=True, headers={'etag': 'W/"bar"'})
    for rq in [req, req_weak]:
        for rp in [resp, resp_weak]:
            rq.get_response(rp).status_code == 304

    r2 = Response(app_iter=['foo\n'], conditional_response=True, headers={'etag': '"foo"'})
    r2_weak = Response(app_iter=['foo\n'], conditional_response=True, headers={'etag': 'W/"foo"'})
    req_weak.get_response(r2).status_code == 200
    req.get_response(r2_weak) == 200


def test_conditional_response_if_modified_since_false():
    from datetime import datetime, timedelta
    req = Request.blank('/', if_modified_since=datetime(2011, 3, 17, 13, 0, 0))
    resp = Response(app_iter=['foo\n'], conditional_response=True,
            last_modified=req.if_modified_since-timedelta(seconds=1))
    resp = req.get_response(resp)
    eq_(resp.status_code, 304)

def test_conditional_response_if_modified_since_true():
    from datetime import datetime, timedelta
    req = Request.blank('/', if_modified_since=datetime(2011, 3, 17, 13, 0, 0))
    resp = Response(app_iter=['foo\n'], conditional_response=True,
            last_modified=req.if_modified_since+timedelta(seconds=1))
    resp = req.get_response(resp)
    eq_(resp.status_code, 200)

def test_conditional_response_range_not_satisfiable_response():
    req = Request.blank('/', range='bytes=100-200')
    resp = Response(app_iter=['foo\n'], content_length=4,
            conditional_response=True)
    resp = req.get_response(resp)
    eq_(resp.status_code, 416)
    eq_(resp.content_range.start, None)
    eq_(resp.content_range.stop, None)
    eq_(resp.content_range.length, 4)
    eq_(resp.body, b'Requested range not satisfiable: bytes=100-200')

def test_HEAD_conditional_response_range_not_satisfiable_response():
    req = Request.blank('/', method='HEAD', range='bytes=100-200')
    resp = Response(app_iter=['foo\n'], content_length=4,
            conditional_response=True)
    resp = req.get_response(resp)
    eq_(resp.status_code, 416)
    eq_(resp.content_range.start, None)
    eq_(resp.content_range.stop, None)
    eq_(resp.content_range.length, 4)
    eq_(resp.body, b'')

def test_md5_etag():
    res = Response()
    res.body = b"""\
In A.D. 2101
War was beginning.
Captain: What happen ?
Mechanic: Somebody set up us the bomb.
Operator: We get signal.
Captain: What !
Operator: Main screen turn on.
Captain: It's You !!
Cats: How are you gentlemen !!
Cats: All your base are belong to us.
Cats: You are on the way to destruction.
Captain: What you say !!
Cats: You have no chance to survive make your time.
Cats: HA HA HA HA ....
Captain: Take off every 'zig' !!
Captain: You know what you doing.
Captain: Move 'zig'.
Captain: For great justice."""
    res.md5_etag()
    ok_(res.etag)
    ok_('\n' not in res.etag)
    eq_(res.etag, 'pN8sSTUrEaPRzmurGptqmw')
    eq_(res.content_md5, None)

def test_md5_etag_set_content_md5():
    res = Response()
    body = b'The quick brown fox jumps over the lazy dog'
    res.md5_etag(body, set_content_md5=True)
    eq_(res.content_md5, 'nhB9nTcrtoJr2B01QqQZ1g==')

def test_decode_content_defaults_to_identity():
    res = Response()
    res.body = b'There be dragons'
    res.decode_content()
    eq_(res.body, b'There be dragons')

def test_decode_content_with_deflate():
    res = Response()
    body = b'Hey Hey Hey'
    # Simulate inflate by chopping the headers off
    # the gzip encoded data
    res.body = zlib.compress(body)[2:-4]
    res.content_encoding = 'deflate'
    res.decode_content()
    eq_(res.body, body)
    eq_(res.content_encoding, None)

def test_content_length():
    r0 = Response('x'*10, content_length=10)

    req_head = Request.blank('/', method='HEAD')
    r1 = req_head.get_response(r0)
    eq_(r1.status_code, 200)
    eq_(r1.body, b'')
    eq_(r1.content_length, 10)

    req_get = Request.blank('/')
    r2 = req_get.get_response(r0)
    eq_(r2.status_code, 200)
    eq_(r2.body, b'x'*10)
    eq_(r2.content_length, 10)

    r3 = Response(app_iter=[b'x']*10)
    eq_(r3.content_length, None)
    eq_(r3.body, b'x'*10)
    eq_(r3.content_length, 10)

    r4 = Response(app_iter=[b'x']*10,
                  content_length=20) # wrong content_length
    eq_(r4.content_length, 20)
    assert_raises(AssertionError, lambda: r4.body)

    req_range = Request.blank('/', range=(0,5))
    r0.conditional_response = True
    r5 = req_range.get_response(r0)
    eq_(r5.status_code, 206)
    eq_(r5.body, b'xxxxx')
    eq_(r5.content_length, 5)

def test_app_iter_range():
    req = Request.blank('/', range=(2,5))
    for app_iter in [
        [b'012345'],
        [b'0', b'12345'],
        [b'0', b'1234', b'5'],
        [b'01', b'2345'],
        [b'01', b'234', b'5'],
        [b'012', b'34', b'5'],
        [b'012', b'3', b'4', b'5'],
        [b'012', b'3', b'45'],
        [b'0', b'12', b'34', b'5'],
        [b'0', b'12', b'345'],
    ]:
        r = Response(
            app_iter=app_iter,
            content_length=6,
            conditional_response=True,
        )
        res = req.get_response(r)
        eq_(list(res.content_range), [2,5,6])
        eq_(res.body, b'234', (res.body, app_iter))

def test_app_iter_range_inner_method():
    class FakeAppIter:
        def app_iter_range(self, start, stop):
            return 'you win', start, stop
    res = Response(app_iter=FakeAppIter())
    eq_(res.app_iter_range(30, 40), ('you win', 30, 40))

def test_content_type_in_headerlist():
    # Couldn't manage to clone Response in order to modify class
    # attributes safely. Shouldn't classes be fresh imported for every
    # test?
    default_content_type = Response.default_content_type
    Response.default_content_type = None
    try:
        res = Response(headerlist=[('Content-Type', 'text/html')],
                            charset='utf8')
        ok_(res._headerlist)
        eq_(res.charset, 'utf8')
    finally:
        Response.default_content_type = default_content_type

def test_from_file():
    res = Response('test')
    inp = io.BytesIO(bytes_(str(res)))
    equal_resp(res, inp)

def test_from_file2():
    res = Response(app_iter=iter([b'test ', b'body']),
                    content_type='text/plain')
    inp = io.BytesIO(bytes_(str(res)))
    equal_resp(res, inp)

def test_from_text_file():
    res = Response('test')
    inp = io.StringIO(text_(str(res), 'utf-8'))
    equal_resp(res, inp)
    res = Response(app_iter=iter([b'test ', b'body']),
                    content_type='text/plain')
    inp = io.StringIO(text_(str(res), 'utf-8'))
    equal_resp(res, inp)

def equal_resp(res, inp):
    res2 = Response.from_file(inp)
    eq_(res.body, res2.body)
    eq_(res.headers, res2.headers)

def test_from_file_w_leading_space_in_header():
    # Make sure the removal of code dealing with leading spaces is safe
    res1 = Response()
    file_w_space = io.BytesIO(
        b'200 OK\n\tContent-Type: text/html; charset=UTF-8')
    res2 = Response.from_file(file_w_space)
    eq_(res1.headers, res2.headers)

def test_file_bad_header():
    file_w_bh = io.BytesIO(b'200 OK\nBad Header')
    assert_raises(ValueError, Response.from_file, file_w_bh)

def test_set_status():
    res = Response()
    res.status = "200"
    eq_(res.status, "200 OK")
    assert_raises(TypeError, setattr, res, 'status', float(200))

def test_set_headerlist():
    res = Response()
    # looks like a list
    res.headerlist = (('Content-Type', 'text/html; charset=UTF-8'),)
    eq_(res.headerlist, [('Content-Type', 'text/html; charset=UTF-8')])
    # has items
    res.headerlist = {'Content-Type': 'text/html; charset=UTF-8'}
    eq_(res.headerlist, [('Content-Type', 'text/html; charset=UTF-8')])
    del res.headerlist
    eq_(res.headerlist, [])

def test_request_uri_no_script_name():
    from webob.response import _request_uri
    environ = {
        'wsgi.url_scheme': 'http',
        'HTTP_HOST': 'test.com',
    }
    eq_(_request_uri(environ), 'http://test.com/')

def test_request_uri_https():
    from webob.response import _request_uri
    environ = {
        'wsgi.url_scheme': 'https',
        'SERVER_NAME': 'test.com',
        'SERVER_PORT': '443',
        'SCRIPT_NAME': '/foobar',
    }
    eq_(_request_uri(environ), 'https://test.com/foobar')

def test_app_iter_range_starts_after_iter_end():
    from webob.response import AppIterRange
    range = AppIterRange(iter([]), start=1, stop=1)
    eq_(list(range), [])

def test_resp_write_app_iter_non_list():
    res = Response(app_iter=(b'a', b'b'))
    eq_(res.content_length, None)
    res.write(b'c')
    eq_(res.body, b'abc')
    eq_(res.content_length, 3)

def test_response_file_body_writelines():
    from webob.response import ResponseBodyFile
    res = Response(app_iter=[b'foo'])
    rbo = ResponseBodyFile(res)
    rbo.writelines(['bar', 'baz'])
    eq_(res.app_iter, [b'foo', b'bar', b'baz'])
    rbo.flush() # noop
    eq_(res.app_iter, [b'foo', b'bar', b'baz'])

def test_response_write_non_str():
    res = Response()
    assert_raises(TypeError, res.write, object())

def test_response_file_body_write_empty_app_iter():
    res = Response('foo')
    res.write('baz')
    eq_(res.app_iter, [b'foo', b'baz'])

def test_response_file_body_write_empty_body():
    res = Response('')
    res.write('baz')
    eq_(res.app_iter, [b'', b'baz'])

def test_response_file_body_close_not_implemented():
    rbo = Response().body_file
    assert_raises(NotImplementedError, rbo.close)

def test_response_file_body_repr():
    rbo = Response().body_file
    rbo.response = 'yo'
    eq_(repr(rbo), "<body_file for 'yo'>")

def test_body_get_is_none():
    res = Response()
    res._app_iter = None
    assert_raises(TypeError, Response, app_iter=iter(['a']),
                  body="somebody")
    assert_raises(AttributeError, res.__getattribute__, 'body')

def test_body_get_is_unicode_notverylong():
    res = Response(app_iter=(text_(b'foo'),))
    assert_raises(TypeError, res.__getattribute__, 'body')

def test_body_get_is_unicode():
    res = Response(app_iter=(['x'] * 51 + [text_(b'x')]))
    assert_raises(TypeError, res.__getattribute__, 'body')

def test_body_set_not_unicode_or_str():
    res = Response()
    assert_raises(TypeError, res.__setattr__, 'body', object())

def test_body_set_unicode():
    res = Response()
    assert_raises(TypeError, res.__setattr__, 'body', text_(b'abc'))

def test_body_set_under_body_doesnt_exist():
    res = Response('abc')
    eq_(res.body, b'abc')
    eq_(res.content_length, 3)

def test_body_del():
    res = Response('123')
    del res.body
    eq_(res.body, b'')
    eq_(res.content_length, 0)

def test_text_get_no_charset():
    res = Response(charset=None)
    assert_raises(AttributeError, res.__getattribute__, 'text')

def test_unicode_body():
    res = Response()
    res.charset = 'utf-8'
    bbody = b'La Pe\xc3\xb1a' # binary string
    ubody = text_(bbody, 'utf-8') # unicode string
    res.body = bbody
    eq_(res.unicode_body, ubody)
    res.ubody = ubody
    eq_(res.body, bbody)
    del res.ubody
    eq_(res.body, b'')

def test_text_get_decode():
    res = Response()
    res.charset = 'utf-8'
    res.body = b'La Pe\xc3\xb1a'
    eq_(res.text, text_(b'La Pe\xc3\xb1a', 'utf-8'))

def test_text_set_no_charset():
    res = Response()
    res.charset = None
    assert_raises(AttributeError, res.__setattr__, 'text', 'abc')

def test_text_set_not_unicode():
    res = Response()
    res.charset = 'utf-8'
    assert_raises(TypeError, res.__setattr__, 'text',
                  b'La Pe\xc3\xb1a')

def test_text_del():
    res = Response('123')
    del res.text
    eq_(res.body, b'')
    eq_(res.content_length, 0)

def test_body_file_del():
    res = Response()
    res.body = b'123'
    eq_(res.content_length, 3)
    eq_(res.app_iter, [b'123'])
    del res.body_file
    eq_(res.body, b'')
    eq_(res.content_length, 0)

def test_write_unicode():
    res = Response()
    res.text = text_(b'La Pe\xc3\xb1a', 'utf-8')
    res.write(text_(b'a'))
    eq_(res.text, text_(b'La Pe\xc3\xb1aa', 'utf-8'))

def test_write_unicode_no_charset():
    res = Response(charset=None)
    assert_raises(TypeError, res.write, text_(b'a'))

def test_write_text():
    res = Response()
    res.body = b'abc'
    res.write(text_(b'a'))
    eq_(res.text, 'abca')

def test_app_iter_del():
    res = Response(
        content_length=3,
        app_iter=['123'],
    )
    del res.app_iter
    eq_(res.body, b'')
    eq_(res.content_length, None)

def test_charset_set_no_content_type_header():
    res = Response()
    res.headers.pop('Content-Type', None)
    assert_raises(AttributeError, res.__setattr__, 'charset', 'utf-8')

def test_charset_del_no_content_type_header():
    res = Response()
    res.headers.pop('Content-Type', None)
    eq_(res._charset__del(), None)

def test_content_type_params_get_no_semicolon_in_content_type_header():
    res = Response()
    res.headers['Content-Type'] = 'foo'
    eq_(res.content_type_params, {})

def test_content_type_params_get_semicolon_in_content_type_header():
    res = Response()
    res.headers['Content-Type'] = 'foo;encoding=utf-8'
    eq_(res.content_type_params, {'encoding':'utf-8'})

def test_content_type_params_set_value_dict_empty():
    res = Response()
    res.headers['Content-Type'] = 'foo;bar'
    res.content_type_params = None
    eq_(res.headers['Content-Type'], 'foo')

def test_content_type_params_set_ok_param_quoting():
    res = Response()
    res.content_type_params = {'a':''}
    eq_(res.headers['Content-Type'], 'text/html; a=""')

def test_set_cookie_overwrite():
    res = Response()
    res.set_cookie('a', '1')
    res.set_cookie('a', '2', overwrite=True)
    eq_(res.headerlist[-1], ('Set-Cookie', 'a=2; Path=/'))

def test_set_cookie_value_is_None():
    res = Response()
    res.set_cookie('a', None)
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    eq_(val[0], 'Max-Age=0')
    eq_(val[1], 'Path=/')
    eq_(val[2], 'a=')
    assert val[3].startswith('expires')

def test_set_cookie_expires_is_None_and_max_age_is_int():
    res = Response()
    res.set_cookie('a', '1', max_age=100)
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    eq_(val[0], 'Max-Age=100')
    eq_(val[1], 'Path=/')
    eq_(val[2], 'a=1')
    assert val[3].startswith('expires')

def test_set_cookie_expires_is_None_and_max_age_is_timedelta():
    from datetime import timedelta
    res = Response()
    res.set_cookie('a', '1', max_age=timedelta(seconds=100))
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    eq_(val[0], 'Max-Age=100')
    eq_(val[1], 'Path=/')
    eq_(val[2], 'a=1')
    assert val[3].startswith('expires')

def test_set_cookie_expires_is_not_None_and_max_age_is_None():
    import datetime
    res = Response()
    then = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    res.set_cookie('a', '1', expires=then)
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    ok_(val[0] in ('Max-Age=86399', 'Max-Age=86400'))
    eq_(val[1], 'Path=/')
    eq_(val[2], 'a=1')
    assert val[3].startswith('expires')

def test_set_cookie_value_is_unicode():
    res = Response()
    val = text_(b'La Pe\xc3\xb1a', 'utf-8')
    res.set_cookie('a', val)
    eq_(res.headerlist[-1], ('Set-Cookie', 'a="La Pe\\303\\261a"; Path=/'))

def test_delete_cookie():
    res = Response()
    res.headers['Set-Cookie'] = 'a=2; Path=/'
    res.delete_cookie('a')
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    eq_(val[0], 'Max-Age=0')
    eq_(val[1], 'Path=/')
    eq_(val[2], 'a=')
    assert val[3].startswith('expires')

def test_delete_cookie_with_path():
    res = Response()
    res.headers['Set-Cookie'] = 'a=2; Path=/'
    res.delete_cookie('a', path='/abc')
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    eq_(val[0], 'Max-Age=0')
    eq_(val[1], 'Path=/abc')
    eq_(val[2], 'a=')
    assert val[3].startswith('expires')

def test_delete_cookie_with_domain():
    res = Response()
    res.headers['Set-Cookie'] = 'a=2; Path=/'
    res.delete_cookie('a', path='/abc', domain='example.com')
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 5
    val.sort()
    eq_(val[0], 'Domain=example.com')
    eq_(val[1], 'Max-Age=0')
    eq_(val[2], 'Path=/abc')
    eq_(val[3], 'a=')
    assert val[4].startswith('expires')

def test_unset_cookie_not_existing_and_not_strict():
    res = Response()
    res.unset_cookie('a', strict=False) # no exception


def test_unset_cookie_not_existing_and_strict():
    res = Response()
    assert_raises(KeyError, res.unset_cookie, 'a')

def test_unset_cookie_key_in_cookies():
    res = Response()
    res.headers.add('Set-Cookie', 'a=2; Path=/')
    res.headers.add('Set-Cookie', 'b=3; Path=/')
    res.unset_cookie('a')
    eq_(res.headers.getall('Set-Cookie'), ['b=3; Path=/'])
    res.unset_cookie(text_('b'))
    eq_(res.headers.getall('Set-Cookie'), [])

def test_merge_cookies_no_set_cookie():
    res = Response()
    result = res.merge_cookies('abc')
    eq_(result, 'abc')

def test_merge_cookies_resp_is_Response():
    inner_res = Response()
    res = Response()
    res.set_cookie('a', '1')
    result = res.merge_cookies(inner_res)
    eq_(result.headers.getall('Set-Cookie'), ['a=1; Path=/'])

def test_merge_cookies_resp_is_wsgi_callable():
    L = []
    def dummy_wsgi_callable(environ, start_response):
        L.append((environ, start_response))
        return 'abc'
    res = Response()
    res.set_cookie('a', '1')
    wsgiapp = res.merge_cookies(dummy_wsgi_callable)
    environ = {}
    def dummy_start_response(status, headers, exc_info=None):
        eq_(headers, [('Set-Cookie', 'a=1; Path=/')])
    result = wsgiapp(environ, dummy_start_response)
    assert result == 'abc'
    assert len(L) == 1
    L[0][1]('200 OK', []) # invoke dummy_start_response assertion

def test_body_get_body_is_None_len_app_iter_is_zero():
    res = Response()
    res._app_iter = io.BytesIO()
    res._body = None
    result = res.body
    eq_(result, b'')

def test_cache_control_get():
    res = Response()
    eq_(repr(res.cache_control), "<CacheControl ''>")
    eq_(res.cache_control.max_age, None)

def test_location():
    res = Response()
    res.location = '/test.html'
    eq_(res.location, '/test.html')
    req = Request.blank('/')
    eq_(req.get_response(res).location, 'http://localhost/test.html')
    res.location = '/test2.html'
    eq_(req.get_response(res).location, 'http://localhost/test2.html')

def test_request_uri_http():
    # covers webob/response.py:1152
    from webob.response import _request_uri
    environ = {
        'wsgi.url_scheme': 'http',
        'SERVER_NAME': 'test.com',
        'SERVER_PORT': '80',
        'SCRIPT_NAME': '/foobar',
    }
    eq_(_request_uri(environ), 'http://test.com/foobar')

def test_request_uri_no_script_name2():
    # covers webob/response.py:1160
    # There is a test_request_uri_no_script_name in test_response.py, but it
    # sets SCRIPT_NAME.
    from webob.response import _request_uri
    environ = {
        'wsgi.url_scheme': 'http',
        'HTTP_HOST': 'test.com',
        'PATH_INFO': '/foobar',
    }
    eq_(_request_uri(environ), 'http://test.com/foobar')

def test_cache_control_object_max_age_ten():
    res = Response()
    res.cache_control.max_age = 10
    eq_(repr(res.cache_control), "<CacheControl 'max-age=10'>")
    eq_(res.headers['cache-control'], 'max-age=10')

def test_cache_control_set_object_error():
    res = Response()
    assert_raises(AttributeError, setattr, res.cache_control, 'max_stale', 10)

def test_cache_expires_set():
    res = Response()
    res.cache_expires = True
    eq_(repr(res.cache_control),
        "<CacheControl 'max-age=0, must-revalidate, no-cache, no-store'>")

def test_status_code_set():
    res = Response()
    res.status_code = 400
    eq_(res._status, '400 Bad Request')
    res.status_int = 404
    eq_(res._status, '404 Not Found')

def test_cache_control_set_dict():
    res = Response()
    res.cache_control = {'a':'b'}
    eq_(repr(res.cache_control), "<CacheControl 'a=b'>")

def test_cache_control_set_None():
    res = Response()
    res.cache_control = None
    eq_(repr(res.cache_control), "<CacheControl ''>")

def test_cache_control_set_unicode():
    res = Response()
    res.cache_control = text_(b'abc')
    eq_(repr(res.cache_control), "<CacheControl 'abc'>")

def test_cache_control_set_control_obj_is_not_None():
    class DummyCacheControl(object):
        def __init__(self):
            self.header_value = 1
            self.properties = {'bleh':1}
    res = Response()
    res._cache_control_obj = DummyCacheControl()
    res.cache_control = {}
    eq_(res.cache_control.properties, {})

def test_cache_control_del():
    res = Response()
    del res.cache_control
    eq_(repr(res.cache_control), "<CacheControl ''>")

def test_body_file_get():
    res = Response()
    result = res.body_file
    from webob.response import ResponseBodyFile
    eq_(result.__class__, ResponseBodyFile)

def test_body_file_write_no_charset():
    res = Response
    assert_raises(TypeError, res.write, text_('foo'))

def test_body_file_write_unicode_encodes():
    s = text_(b'La Pe\xc3\xb1a', 'utf-8')
    res = Response()
    res.write(s)
    eq_(res.app_iter, [b'', b'La Pe\xc3\xb1a'])

def test_repr():
    res = Response()
    ok_(repr(res).endswith('200 OK>'))

def test_cache_expires_set_timedelta():
    res = Response()
    from datetime import timedelta
    delta = timedelta(seconds=60)
    res.cache_expires(seconds=delta)
    eq_(res.cache_control.max_age, 60)

def test_cache_expires_set_int():
    res = Response()
    res.cache_expires(seconds=60)
    eq_(res.cache_control.max_age, 60)

def test_cache_expires_set_None():
    res = Response()
    res.cache_expires(seconds=None, a=1)
    eq_(res.cache_control.a, 1)

def test_cache_expires_set_zero():
    res = Response()
    res.cache_expires(seconds=0)
    eq_(res.cache_control.no_store, True)
    eq_(res.cache_control.no_cache, '*')
    eq_(res.cache_control.must_revalidate, True)
    eq_(res.cache_control.max_age, 0)
    eq_(res.cache_control.post_check, 0)

def test_encode_content_unknown():
    res = Response()
    assert_raises(AssertionError, res.encode_content, 'badencoding')

def test_encode_content_identity():
    res = Response()
    result = res.encode_content('identity')
    eq_(result, None)

def test_encode_content_gzip_already_gzipped():
    res = Response()
    res.content_encoding = 'gzip'
    result = res.encode_content('gzip')
    eq_(result, None)

def test_encode_content_gzip_notyet_gzipped():
    res = Response()
    res.app_iter = io.BytesIO(b'foo')
    result = res.encode_content('gzip')
    eq_(result, None)
    eq_(res.content_length, 23)
    eq_(res.app_iter, [
        b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff',
        b'K\xcb\xcf\x07\x00',
        b'!es\x8c\x03\x00\x00\x00'
        ])

def test_encode_content_gzip_notyet_gzipped_lazy():
    res = Response()
    res.app_iter = io.BytesIO(b'foo')
    result = res.encode_content('gzip', lazy=True)
    eq_(result, None)
    eq_(res.content_length, None)
    eq_(list(res.app_iter), [
        b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff',
        b'K\xcb\xcf\x07\x00',
        b'!es\x8c\x03\x00\x00\x00'
        ])

def test_encode_content_gzip_buffer_coverage():
    #this test is to provide 100% coverage of
    #.Response.encode_content was necessary in order to get
    # request https://github.com/Pylons/webob/pull/85 into upstream
    res = Response()
    DATA = b"abcdefghijklmnopqrstuvwxyz0123456789" * 1000000
    res.app_iter = io.BytesIO(DATA)
    res.encode_content('gzip')
    result = list(res.app_iter)
    assert len(b"".join(result)) < len(DATA)

def test_decode_content_identity():
    res = Response()
    res.content_encoding = 'identity'
    result = res.decode_content()
    eq_(result, None)

def test_decode_content_weird():
    res = Response()
    res.content_encoding = 'weird'
    assert_raises(ValueError, res.decode_content)

def test_decode_content_gzip():
    from gzip import GzipFile
    io_ = io.BytesIO()
    gzip_f = GzipFile(filename='', mode='w', fileobj=io_)
    gzip_f.write(b'abc')
    gzip_f.close()
    body = io_.getvalue()
    res = Response()
    res.content_encoding = 'gzip'
    res.body = body
    res.decode_content()
    eq_(res.body, b'abc')

def test__abs_headerlist_location_with_scheme():
    res = Response()
    res.content_encoding = 'gzip'
    res.headerlist = [('Location', 'http:')]
    result = res._abs_headerlist({})
    eq_(result, [('Location', 'http:')])

def test__abs_headerlist_location_no_scheme():
    res = Response()
    res.content_encoding = 'gzip'
    res.headerlist = [('Location', '/abc')]
    result = res._abs_headerlist({'wsgi.url_scheme':'http',
                                  'HTTP_HOST':'example.com:80'})
    eq_(result, [('Location', 'http://example.com/abc')])

def test_response_set_body_file1():
     data  = b'abc'
     file = io.BytesIO(data)
     r = Response(body_file=file)
     assert r.body == data

def test_response_set_body_file2():
    data = b'abcdef'*1024
    file = io.BytesIO(data)
    r = Response(body_file=file)
    assert r.body == data

def test_response_json_body():
    r = Response(json_body={'a': 1})
    assert r.body == b'{"a":1}', repr(r.body)
    assert r.content_type == 'application/json'
    r = Response()
    r.json_body = {"b": 1}
    assert r.content_type == 'text/html'
    del r.json_body
    assert r.body == b''

def test_cache_expires_set_zero_then_nonzero():
    res = Response()
    res.cache_expires(seconds=0)
    res.cache_expires(seconds=1)
    eq_(res.pragma, None)
    ok_(not res.cache_control.no_cache)
    ok_(not res.cache_control.no_store)
    ok_(not res.cache_control.must_revalidate)
    eq_(res.cache_control.max_age, 1)

########NEW FILE########
__FILENAME__ = test_static
from io import BytesIO
from os.path import getmtime
import tempfile
from time import gmtime
import os
import shutil
import unittest

from webob import static
from webob.compat import bytes_
from webob.request import Request, environ_from_url
from webob.response import Response


def get_response(app, path='/', **req_kw):
    """Convenient function to query an application"""
    req = Request(environ_from_url(path), **req_kw)
    return req.get_response(app)


def create_file(content, *paths):
    """Convenient function to create a new file with some content"""
    path = os.path.join(*paths)
    with open(path, 'wb') as fp:
        fp.write(bytes_(content))
    return path


class TestFileApp(unittest.TestCase):
    def setUp(self):
        fp = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        self.tempfile = fp.name
        fp.write(b"import this\n")
        fp.close()

    def tearDown(self):
        os.unlink(self.tempfile)

    def test_fileapp(self):
        app = static.FileApp(self.tempfile)
        resp1 = get_response(app)
        self.assertEqual(resp1.content_type, 'text/x-python')
        self.assertEqual(resp1.charset, 'UTF-8')
        self.assertEqual(resp1.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))

        resp2 = get_response(app)
        self.assertEqual(resp2.content_type, 'text/x-python')
        self.assertEqual(resp2.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))

        resp3 = get_response(app, range=(7, 11))
        self.assertEqual(resp3.status_code, 206)
        self.assertEqual(tuple(resp3.content_range)[:2], (7, 11))
        self.assertEqual(resp3.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))
        self.assertEqual(resp3.body, bytes_('this'))

    def test_unexisting_file(self):
        app = static.FileApp('/tmp/this/doesnt/exist')
        self.assertEqual(404, get_response(app).status_code)

    def test_allowed_methods(self):
        app = static.FileApp(self.tempfile)

        # Alias
        resp = lambda method: get_response(app, method=method)

        self.assertEqual(200, resp(method='GET').status_code)
        self.assertEqual(200, resp(method='HEAD').status_code)
        self.assertEqual(405, resp(method='POST').status_code)
        # Actually any other method is not allowed
        self.assertEqual(405, resp(method='xxx').status_code)

    def test_exception_while_opening_file(self):
        # Mock the built-in ``open()`` function to allow finner control about
        # what we are testing.
        def open_ioerror(*args, **kwargs):
            raise IOError()

        def open_oserror(*args, **kwargs):
            raise OSError()

        app = static.FileApp(self.tempfile)

        app._open = open_ioerror
        self.assertEqual(403, get_response(app).status_code)

        app._open = open_oserror
        self.assertEqual(403, get_response(app).status_code)

    def test_use_wsgi_filewrapper(self):
        class TestWrapper(object):
            def __init__(self, file, block_size):
                self.file = file
                self.block_size = block_size

        environ = environ_from_url('/')
        environ['wsgi.file_wrapper'] = TestWrapper
        app = static.FileApp(self.tempfile)
        app_iter = Request(environ).get_response(app).app_iter

        self.assertTrue(isinstance(app_iter, TestWrapper))
        self.assertEqual(bytes_('import this\n'), app_iter.file.read())
        self.assertEqual(static.BLOCK_SIZE, app_iter.block_size)


class TestFileIter(unittest.TestCase):
    def test_empty_file(self):
        fp = BytesIO()
        fi = static.FileIter(fp)
        self.assertRaises(StopIteration, next, iter(fi))

    def test_seek(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(seek=4)

        self.assertEqual(bytes_("456789"), next(i))
        self.assertRaises(StopIteration, next, i)

    def test_limit(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(limit=4)

        self.assertEqual(bytes_("0123"), next(i))
        self.assertRaises(StopIteration, next, i)

    def test_limit_and_seek(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(limit=4, seek=1)

        self.assertEqual(bytes_("123"), next(i))
        self.assertRaises(StopIteration, next, i)

    def test_multiple_reads(self):
        fp = BytesIO(bytes_("012"))
        i = static.FileIter(fp).app_iter_range(block_size=1)

        self.assertEqual(bytes_("0"), next(i))
        self.assertEqual(bytes_("1"), next(i))
        self.assertEqual(bytes_("2"), next(i))
        self.assertRaises(StopIteration, next, i)

    def test_seek_bigger_than_limit(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(limit=1, seek=2)

        # XXX: this should not return anything actually, since we are starting
        # to read after the place we wanted to stop.
        self.assertEqual(bytes_("23456789"), next(i))
        self.assertRaises(StopIteration, next, i)

    def test_limit_is_zero(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(limit=0)

        self.assertRaises(StopIteration, next, i)



class TestDirectoryApp(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_empty_directory(self):
        app = static.DirectoryApp(self.test_dir)
        self.assertEqual(404, get_response(app).status_code)
        self.assertEqual(404, get_response(app, '/foo').status_code)

    def test_serve_file(self):
        app = static.DirectoryApp(self.test_dir)
        create_file('abcde', self.test_dir, 'bar')
        self.assertEqual(404, get_response(app).status_code)
        self.assertEqual(404, get_response(app, '/foo').status_code)

        resp = get_response(app, '/bar')
        self.assertEqual(200, resp.status_code)
        self.assertEqual(bytes_('abcde'), resp.body)

    def test_dont_serve_file_in_parent_directory(self):
        # We'll have:
        #   /TEST_DIR/
        #   /TEST_DIR/bar
        #   /TEST_DIR/foo/   <- serve this directory
        create_file('abcde', self.test_dir, 'bar')
        serve_path = os.path.join(self.test_dir, 'foo')
        os.mkdir(serve_path)
        app = static.DirectoryApp(serve_path)

        # The file exists, but is outside the served dir.
        self.assertEqual(403, get_response(app, '/../bar').status_code)

    def test_file_app_arguments(self):
        app = static.DirectoryApp(self.test_dir, content_type='xxx/yyy')
        create_file('abcde', self.test_dir, 'bar')

        resp = get_response(app, '/bar')
        self.assertEqual(200, resp.status_code)
        self.assertEqual('xxx/yyy', resp.content_type)

    def test_file_app_factory(self):
        def make_fileapp(*args, **kwargs):
            make_fileapp.called = True
            return Response()
        make_fileapp.called = False

        app = static.DirectoryApp(self.test_dir)
        app.make_fileapp = make_fileapp
        create_file('abcde', self.test_dir, 'bar')

        get_response(app, '/bar')
        self.assertTrue(make_fileapp.called)

    def test_must_serve_directory(self):
        serve_path = create_file('abcde', self.test_dir, 'bar')
        self.assertRaises(IOError, static.DirectoryApp, serve_path)

    def test_index_page(self):
        os.mkdir(os.path.join(self.test_dir, 'index-test'))
        create_file(bytes_('index'), self.test_dir, 'index-test', 'index.html')
        app = static.DirectoryApp(self.test_dir)
        resp = get_response(app, '/index-test')
        self.assertEqual(resp.status_code, 301)
        self.assertTrue(resp.location.endswith('/index-test/'))
        resp = get_response(app, '/index-test?test')
        self.assertTrue(resp.location.endswith('/index-test/?test'))
        resp = get_response(app, '/index-test/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.body, bytes_('index'))
        self.assertEqual(resp.content_type, 'text/html')
        resp = get_response(app, '/index-test/index.html')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.body, bytes_('index'))
        redir_app = static.DirectoryApp(self.test_dir, hide_index_with_redirect=True)
        resp = get_response(redir_app, '/index-test/index.html')
        self.assertEqual(resp.status_code, 301)
        self.assertTrue(resp.location.endswith('/index-test/'))
        resp = get_response(redir_app, '/index-test/index.html?test')
        self.assertTrue(resp.location.endswith('/index-test/?test'))
        page_app = static.DirectoryApp(self.test_dir, index_page='something-else.html')
        self.assertEqual(get_response(page_app, '/index-test/').status_code, 404)

########NEW FILE########
__FILENAME__ = test_transcode
# coding: cp1251
from webob.request import Request, Transcoder
from webob.response import Response
from webob.compat import text_, native_
from nose.tools import eq_

# def tapp(env, sr):
#     req = Request(env)
#     r = Response(str(req))
#     #r = Response(str(dict(req.POST)))
#     return r(env, sr)

t1 = b'--BOUNDARY\r\nContent-Disposition: form-data; name="a"\r\n\r\n\xea\xf3...\r\n--BOUNDARY--'
t2 = b'--BOUNDARY\r\nContent-Disposition: form-data; name="a"; filename="file"\r\n\r\n\xea\xf3...\r\n--BOUNDARY--'
t3 = b'--BOUNDARY\r\nContent-Disposition: form-data; name="a"; filename="\xea\xf3..."\r\n\r\nfoo\r\n--BOUNDARY--'

def test_transcode():
    def tapp(env, sr):
        req = Request(env)
        #import pprint; pprint.pprint(req.environ)
        #print(req.body)
        req = req.decode()
        #import pprint; pprint.pprint(req.environ)
        #print(req.body)
        v = req.POST[req.query_string]
        if hasattr(v, 'filename'):
            r = Response(text_('%s\n%r' % (v.filename, v.value)))
        else:
            r = Response(v)
        return r(env, sr)
    text = b'\xea\xf3...'.decode('cp1251')
    def test(post):
        req = Request.blank('/?a', POST=post)
        req.environ['CONTENT_TYPE'] = 'multipart/form-data; charset=windows-1251; boundary=BOUNDARY'
        return req.get_response(tapp)

    r = test(t1)
    eq_(r.text, text)
    r = test(t2)
    eq_(r.text, 'file\n%r' % text.encode('cp1251'))
    r = test(t3)
    eq_(r.text, "%s\n%r" % (text, b'foo'))

    #req = Request.blank('/?a', POST={'a': ('file', text.encode('cp1251'))},


    # req = Request({}, charset='utf8')
    # req = Request({})
    # print req.charset
    # print req._charset_cache
    # print req.environ.get('CONTENT_TYPE')
    #print '\xd0\xba\xd1\x83...'.decode('utf8').encode('cp1251')
    #print u'\u043a'.encode('cp1251')

def test_transcode_query():
    req = Request.blank('/?%EF%F0%E8=%E2%E5%F2')
    req2 = req.decode('cp1251')
    eq_(req2.query_string, '%D0%BF%D1%80%D0%B8=%D0%B2%D0%B5%D1%82')

def test_transcode_non_multipart():
    req = Request.blank('/?a', POST='%EF%F0%E8=%E2%E5%F2')
    req._content_type_raw = 'application/x-www-form-urlencoded'
    req2 = req.decode('cp1251')
    eq_(native_(req2.body), '%D0%BF%D1%80%D0%B8=%D0%B2%D0%B5%D1%82')

def test_transcode_non_form():
    req = Request.blank('/?a', POST='%EF%F0%E8=%E2%E5%F2')
    req._content_type_raw = 'application/x-foo'
    req2 = req.decode('cp1251')
    eq_(native_(req2.body), '%EF%F0%E8=%E2%E5%F2')

def test_transcode_noop():
    req = Request.blank('/')
    assert req.decode() is req

def test_transcode_query():
    t = Transcoder('ascii')
    eq_(t.transcode_query('a'), 'a')

########NEW FILE########
__FILENAME__ = test_util
import unittest
from webob.response import Response

class Test_warn_deprecation(unittest.TestCase):
    def setUp(self):
        import warnings
        self.oldwarn = warnings.warn
        warnings.warn = self._warn
        self.warnings = []

    def tearDown(self):
        import warnings
        warnings.warn = self.oldwarn
        del self.warnings

    def _callFUT(self, text, version, stacklevel):
        from webob.util import warn_deprecation
        return warn_deprecation(text, version, stacklevel)

    def _warn(self, text, type, stacklevel=1):
        self.warnings.append(locals())

    def test_multidict_update_warning(self):
        # test warning when duplicate keys are passed
        r = Response()
        r.headers.update([
            ('Set-Cookie', 'a=b'),
            ('Set-Cookie', 'x=y'),
        ])
        self.assertEqual(len(self.warnings), 1)
        deprecation_warning = self.warnings[0]
        self.assertEqual(deprecation_warning['type'], UserWarning)
        assert 'Consider using .extend()' in deprecation_warning['text']

    def test_multidict_update_warning_unnecessary(self):
        # no warning on normal operation
        r = Response()
        r.headers.update([('Set-Cookie', 'a=b')])
        self.assertEqual(len(self.warnings), 0)

    def test_warn_deprecation(self):
        v = '1.3.0'
        from webob.util import warn_deprecation
        self.assertRaises(DeprecationWarning, warn_deprecation, 'foo', v[:3], 1)

    def test_warn_deprecation_future_version(self):
        v = '9.9.9'
        from webob.util import warn_deprecation
        warn_deprecation('foo', v[:3], 1)
        self.assertEqual(len(self.warnings), 1)

########NEW FILE########
__FILENAME__ = acceptparse
"""
Parses a variety of ``Accept-*`` headers.

These headers generally take the form of::

    value1; q=0.5, value2; q=0

Where the ``q`` parameter is optional.  In theory other parameters
exists, but this ignores them.
"""

import re

from webob.headers import _trans_name as header_to_key
from webob.util import (
    header_docstring,
    warn_deprecation,
    )

part_re = re.compile(
    r',\s*([^\s;,\n]+)(?:[^,]*?;\s*q=([0-9.]*))?')




def _warn_first_match():
    # TODO: remove .first_match in version 1.3
    warn_deprecation("Use best_match instead", '1.2', 3)

class Accept(object):
    """
    Represents a generic ``Accept-*`` style header.

    This object should not be modified.  To add items you can use
    ``accept_obj + 'accept_thing'`` to get a new object
    """

    def __init__(self, header_value):
        self.header_value = header_value
        self._parsed = list(self.parse(header_value))
        self._parsed_nonzero = [(m,q) for (m,q) in self._parsed if q]

    @staticmethod
    def parse(value):
        """
        Parse ``Accept-*`` style header.

        Return iterator of ``(value, quality)`` pairs.
        ``quality`` defaults to 1.
        """
        for match in part_re.finditer(','+value):
            name = match.group(1)
            if name == 'q':
                continue
            quality = match.group(2) or ''
            if quality:
                try:
                    quality = max(min(float(quality), 1), 0)
                    yield (name, quality)
                    continue
                except ValueError:
                    pass
            yield (name, 1)

    def __repr__(self):
        return '<%s(%r)>' % (self.__class__.__name__, str(self))

    def __iter__(self):
        for m,q in sorted(
            self._parsed_nonzero,
            key=lambda i: i[1],
            reverse=True
        ):
            yield m

    def __str__(self):
        result = []
        for mask, quality in self._parsed:
            if quality != 1:
                mask = '%s;q=%0.*f' % (
                    mask, min(len(str(quality).split('.')[1]), 3), quality)
            result.append(mask)
        return ', '.join(result)

    def __add__(self, other, reversed=False):
        if isinstance(other, Accept):
            other = other.header_value
        if hasattr(other, 'items'):
            other = sorted(other.items(), key=lambda item: -item[1])
        if isinstance(other, (list, tuple)):
            result = []
            for item in other:
                if isinstance(item, (list, tuple)):
                    name, quality = item
                    result.append('%s; q=%s' % (name, quality))
                else:
                    result.append(item)
            other = ', '.join(result)
        other = str(other)
        my_value = self.header_value
        if reversed:
            other, my_value = my_value, other
        if not other:
            new_value = my_value
        elif not my_value:
            new_value = other
        else:
            new_value = my_value + ', ' + other
        return self.__class__(new_value)

    def __radd__(self, other):
        return self.__add__(other, True)

    def __contains__(self, offer):
        """
        Returns true if the given object is listed in the accepted
        types.
        """
        for mask, quality in self._parsed_nonzero:
            if self._match(mask, offer):
                return True

    def quality(self, offer, modifier=1):
        """
        Return the quality of the given offer.  Returns None if there
        is no match (not 0).
        """
        bestq = 0
        for mask, q in self._parsed:
            if self._match(mask, offer):
                bestq = max(bestq, q * modifier)
        return bestq or None

    def first_match(self, offers):
        """
        DEPRECATED
        Returns the first allowed offered type. Ignores quality.
        Returns the first offered type if nothing else matches; or if you include None
        at the end of the match list then that will be returned.
        """
        _warn_first_match()

    def best_match(self, offers, default_match=None):
        """
        Returns the best match in the sequence of offered types.

        The sequence can be a simple sequence, or you can have
        ``(match, server_quality)`` items in the sequence.  If you
        have these tuples then the client quality is multiplied by the
        server_quality to get a total.  If two matches have equal
        weight, then the one that shows up first in the `offers` list
        will be returned.

        But among matches with the same quality the match to a more specific
        requested type will be chosen. For example a match to text/* trumps */*.

        default_match (default None) is returned if there is no intersection.
        """
        best_quality = -1
        best_offer = default_match
        matched_by = '*/*'
        for offer in offers:
            if isinstance(offer, (tuple, list)):
                offer, server_quality = offer
            else:
                server_quality = 1
            for mask, quality in self._parsed_nonzero:
                possible_quality = server_quality * quality
                if possible_quality < best_quality:
                    continue
                elif possible_quality == best_quality:
                    # 'text/plain' overrides 'message/*' overrides '*/*'
                    # (if all match w/ the same q=)
                    if matched_by.count('*') <= mask.count('*'):
                        continue
                if self._match(mask, offer):
                    best_quality = possible_quality
                    best_offer = offer
                    matched_by = mask
        return best_offer

    def _match(self, mask, offer):
        _check_offer(offer)
        return mask == '*' or offer.lower() == mask.lower()



class NilAccept(object):
    MasterClass = Accept

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.MasterClass)

    def __str__(self):
        return ''

    def __nonzero__(self):
        return False
    __bool__ = __nonzero__ # python 3

    def __iter__(self):
        return iter(())

    def __add__(self, item):
        if isinstance(item, self.MasterClass):
            return item
        else:
            return self.MasterClass('') + item

    def __radd__(self, item):
        if isinstance(item, self.MasterClass):
            return item
        else:
            return item + self.MasterClass('')

    def __contains__(self, item):
        _check_offer(item)
        return True

    def quality(self, offer, default_quality=1):
        return 0

    def first_match(self, offers): # pragma: no cover
        _warn_first_match()

    def best_match(self, offers, default_match=None):
        best_quality = -1
        best_offer = default_match
        for offer in offers:
            _check_offer(offer)
            if isinstance(offer, (list, tuple)):
                offer, quality = offer
            else:
                quality = 1
            if quality > best_quality:
                best_offer = offer
                best_quality = quality
        return best_offer

class NoAccept(NilAccept):
    def __contains__(self, item):
        return False

class AcceptCharset(Accept):
    @staticmethod
    def parse(value):
        latin1_found = False
        for m, q in Accept.parse(value):
            _m = m.lower()
            if _m == '*' or _m == 'iso-8859-1':
                latin1_found = True
            yield _m, q
        if not latin1_found:
            yield ('iso-8859-1', 1)

class AcceptLanguage(Accept):
    def _match(self, mask, item):
        item = item.replace('_', '-').lower()
        mask = mask.lower()
        return (mask == '*'
            or item == mask
            or item.split('-')[0] == mask
            or item == mask.split('-')[0]
        )


class MIMEAccept(Accept):
    """
        Represents the ``Accept`` header, which is a list of mimetypes.

        This class knows about mime wildcards, like ``image/*``
    """
    @staticmethod
    def parse(value):
        for mask, q in Accept.parse(value):
            try:
                mask_major, mask_minor = map(lambda x: x.lower(), mask.split('/'))
            except ValueError:
                continue
            if mask_major == '*' and mask_minor != '*':
                continue
            if mask_major != "*" and "*" in mask_major:
                continue
            if mask_minor != "*" and "*" in mask_minor:
                continue
            yield ("%s/%s" % (mask_major, mask_minor), q)

    def accept_html(self):
        """
        Returns true if any HTML-like type is accepted
        """
        return ('text/html' in self
                or 'application/xhtml+xml' in self
                or 'application/xml' in self
                or 'text/xml' in self)

    accepts_html = property(accept_html) # note the plural

    def _match(self, mask, offer):
        """
            Check if the offer is covered by the mask
        """
        _check_offer(offer)
        if '*' not in mask:
            return offer.lower() == mask.lower()
        elif mask == '*/*':
            return True
        else:
            assert mask.endswith('/*')
            mask_major = mask[:-2].lower()
            offer_major = offer.split('/', 1)[0].lower()
            return offer_major == mask_major


class MIMENilAccept(NilAccept):
    MasterClass = MIMEAccept

def _check_offer(offer):
    if '*' in offer:
        raise ValueError("The application should offer specific types, got %r" % offer)



def accept_property(header, rfc_section,
    AcceptClass=Accept, NilClass=NilAccept
):
    key = header_to_key(header)
    doc = header_docstring(header, rfc_section)
    #doc += "  Converts it as a %s." % convert_name
    def fget(req):
        value = req.environ.get(key)
        if not value:
            return NilClass()
        return AcceptClass(value)
    def fset(req, val):
        if val:
            if isinstance(val, (list, tuple, dict)):
                val = AcceptClass('') + val
            val = str(val)
        req.environ[key] = val or None
    def fdel(req):
        del req.environ[key]
    return property(fget, fset, fdel, doc)

########NEW FILE########
__FILENAME__ = byterange
import re

__all__ = ['Range', 'ContentRange']

_rx_range = re.compile('bytes *= *(\d*) *- *(\d*)', flags=re.I)
_rx_content_range = re.compile(r'bytes (?:(\d+)-(\d+)|[*])/(?:(\d+)|[*])')

class Range(object):
    """
        Represents the Range header.
    """

    def __init__(self, start, end):
        assert end is None or end >= 0, "Bad range end: %r" % end
        self.start = start
        self.end = end # non-inclusive

    def range_for_length(self, length):
        """
            *If* there is only one range, and *if* it is satisfiable by
            the given length, then return a (start, end) non-inclusive range
            of bytes to serve.  Otherwise return None
        """
        if length is None:
            return None
        start, end = self.start, self.end
        if end is None:
            end = length
            if start < 0:
                start += length
        if _is_content_range_valid(start, end, length):
            stop = min(end, length)
            return (start, stop)
        else:
            return None

    def content_range(self, length):
        """
            Works like range_for_length; returns None or a ContentRange object

            You can use it like::

                response.content_range = req.range.content_range(response.content_length)

            Though it's still up to you to actually serve that content range!
        """
        range = self.range_for_length(length)
        if range is None:
            return None
        return ContentRange(range[0], range[1], length)

    def __str__(self):
        s,e = self.start, self.end
        if e is None:
            r = 'bytes=%s' % s
            if s >= 0:
                r += '-'
            return r
        return 'bytes=%s-%s' % (s, e-1)

    def __repr__(self):
        return '%s(%r, %r)' % (
            self.__class__.__name__,
            self.start, self.end)

    def __iter__(self):
        return iter((self.start, self.end))

    @classmethod
    def parse(cls, header):
        """
            Parse the header; may return None if header is invalid
        """
        m = _rx_range.match(header or '')
        if not m:
            return None
        start, end = m.groups()
        if not start:
            return cls(-int(end), None)
        start = int(start)
        if not end:
            return cls(start, None)
        end = int(end) + 1 # return val is non-inclusive
        if start >= end:
            return None
        return cls(start, end)


class ContentRange(object):

    """
    Represents the Content-Range header

    This header is ``start-stop/length``, where start-stop and length
    can be ``*`` (represented as None in the attributes).
    """

    def __init__(self, start, stop, length):
        if not _is_content_range_valid(start, stop, length):
            raise ValueError(
                "Bad start:stop/length: %r-%r/%r" % (start, stop, length))
        self.start = start
        self.stop = stop # this is python-style range end (non-inclusive)
        self.length = length

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self)

    def __str__(self):
        if self.length is None:
            length = '*'
        else:
            length = self.length
        if self.start is None:
            assert self.stop is None
            return 'bytes */%s' % length
        stop = self.stop - 1 # from non-inclusive to HTTP-style
        return 'bytes %s-%s/%s' % (self.start, stop, length)

    def __iter__(self):
        """
            Mostly so you can unpack this, like:

                start, stop, length = res.content_range
        """
        return iter([self.start, self.stop, self.length])

    @classmethod
    def parse(cls, value):
        """
            Parse the header.  May return None if it cannot parse.
        """
        m = _rx_content_range.match(value or '')
        if not m:
            return None
        s, e, l = m.groups()
        if s:
            s = int(s)
            e = int(e) + 1
        l = l and int(l)
        if not _is_content_range_valid(s, e, l, response=True):
            return None
        return cls(s, e, l)


def _is_content_range_valid(start, stop, length, response=False):
    if (start is None) != (stop is None):
        return False
    elif start is None:
        return length is None or length >= 0
    elif length is None:
        return 0 <= start < stop
    elif start >= stop:
        return False
    elif response and stop > length:
        # "content-range: bytes 0-50/10" is invalid for a response
        # "range: bytes 0-50" is valid for a request to a 10-bytes entity
        return False
    else:
        return 0 <= start < length

########NEW FILE########
__FILENAME__ = cachecontrol
"""
Represents the Cache-Control header
"""
import re

class UpdateDict(dict):
    """
    Dict that has a callback on all updates
    """
    # these are declared as class attributes so that
    # we don't need to override constructor just to
    # set some defaults
    updated = None
    updated_args = None

    def _updated(self):
        """
        Assign to new_dict.updated to track updates
        """
        updated = self.updated
        if updated is not None:
            args = self.updated_args
            if args is None:
                args = (self,)
            updated(*args)

    def __setitem__(self, key, item):
        dict.__setitem__(self, key, item)
        self._updated()

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._updated()

    def clear(self):
        dict.clear(self)
        self._updated()

    def update(self, *args, **kw):
        dict.update(self, *args, **kw)
        self._updated()

    def setdefault(self, key, value=None):
        val = dict.setdefault(self, key, value)
        if val is value:
            self._updated()
        return val

    def pop(self, *args):
        v = dict.pop(self, *args)
        self._updated()
        return v

    def popitem(self):
        v = dict.popitem(self)
        self._updated()
        return v


token_re = re.compile(
    r'([a-zA-Z][a-zA-Z_-]*)\s*(?:=(?:"([^"]*)"|([^ \t",;]*)))?')
need_quote_re = re.compile(r'[^a-zA-Z0-9._-]')


class exists_property(object):
    """
    Represents a property that either is listed in the Cache-Control
    header, or is not listed (has no value)
    """
    def __init__(self, prop, type=None):
        self.prop = prop
        self.type = type

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return self.prop in obj.properties

    def __set__(self, obj, value):
        if (self.type is not None
            and self.type != obj.type):
            raise AttributeError(
                "The property %s only applies to %s Cache-Control" % (
                    self.prop, self.type))

        if value:
            obj.properties[self.prop] = None
        else:
            if self.prop in obj.properties:
                del obj.properties[self.prop]

    def __delete__(self, obj):
        self.__set__(obj, False)


class value_property(object):
    """
    Represents a property that has a value in the Cache-Control header.

    When no value is actually given, the value of self.none is returned.
    """
    def __init__(self, prop, default=None, none=None, type=None):
        self.prop = prop
        self.default = default
        self.none = none
        self.type = type

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        if self.prop in obj.properties:
            value = obj.properties[self.prop]
            if value is None:
                return self.none
            else:
                return value
        else:
            return self.default

    def __set__(self, obj, value):
        if (self.type is not None
            and self.type != obj.type):
            raise AttributeError(
                "The property %s only applies to %s Cache-Control" % (
                    self.prop, self.type))
        if value == self.default:
            if self.prop in obj.properties:
                del obj.properties[self.prop]
        elif value is True:
            obj.properties[self.prop] = None # Empty value, but present
        else:
            obj.properties[self.prop] = value

    def __delete__(self, obj):
        if self.prop in obj.properties:
            del obj.properties[self.prop]


class CacheControl(object):

    """
    Represents the Cache-Control header.

    By giving a type of ``'request'`` or ``'response'`` you can
    control what attributes are allowed (some Cache-Control values
    only apply to requests or responses).
    """

    update_dict = UpdateDict

    def __init__(self, properties, type):
        self.properties = properties
        self.type = type

    @classmethod
    def parse(cls, header, updates_to=None, type=None):
        """
        Parse the header, returning a CacheControl object.

        The object is bound to the request or response object
        ``updates_to``, if that is given.
        """
        if updates_to:
            props = cls.update_dict()
            props.updated = updates_to
        else:
            props = {}
        for match in token_re.finditer(header):
            name = match.group(1)
            value = match.group(2) or match.group(3) or None
            if value:
                try:
                    value = int(value)
                except ValueError:
                    pass
            props[name] = value
        obj = cls(props, type=type)
        if updates_to:
            props.updated_args = (obj,)
        return obj

    def __repr__(self):
        return '<CacheControl %r>' % str(self)

    # Request values:
    # no-cache shared (below)
    # no-store shared (below)
    # max-age shared  (below)
    max_stale = value_property('max-stale', none='*', type='request')
    min_fresh = value_property('min-fresh', type='request')
    # no-transform shared (below)
    only_if_cached = exists_property('only-if-cached', type='request')

    # Response values:
    public = exists_property('public', type='response')
    private = value_property('private', none='*', type='response')
    no_cache = value_property('no-cache', none='*')
    no_store = exists_property('no-store')
    no_transform = exists_property('no-transform')
    must_revalidate = exists_property('must-revalidate', type='response')
    proxy_revalidate = exists_property('proxy-revalidate', type='response')
    max_age = value_property('max-age', none=-1)
    s_maxage = value_property('s-maxage', type='response')
    s_max_age = s_maxage

    def __str__(self):
        return serialize_cache_control(self.properties)

    def copy(self):
        """
        Returns a copy of this object.
        """
        return self.__class__(self.properties.copy(), type=self.type)


def serialize_cache_control(properties):
    if isinstance(properties, CacheControl):
        properties = properties.properties
    parts = []
    for name, value in sorted(properties.items()):
        if value is None:
            parts.append(name)
            continue
        value = str(value)
        if need_quote_re.search(value):
            value = '"%s"' % value
        parts.append('%s=%s' % (name, value))
    return ', '.join(parts)

########NEW FILE########
__FILENAME__ = client
import errno
import sys
import re
try:
    import httplib
except ImportError: # pragma: no cover
    import http.client as httplib
from webob.compat import url_quote
import socket
from webob import exc
from webob.compat import PY3


__all__ = ['send_request_app', 'SendRequest']

class SendRequest:
    """
    Sends the request, as described by the environ, over actual HTTP.
    All controls about how it is sent are contained in the request
    environ itself.

    This connects to the server given in SERVER_NAME:SERVER_PORT, and
    sends the Host header in HTTP_HOST -- they do not have to match.
    You can send requests to servers despite what DNS says.

    Set ``environ['webob.client.timeout'] = 10`` to set the timeout on
    the request (to, for example, 10 seconds).

    Does not add X-Forwarded-For or other standard headers

    If you use ``send_request_app`` then simple ``httplib``
    connections will be used.
    """

    def __init__(self, HTTPConnection=httplib.HTTPConnection,
                 HTTPSConnection=httplib.HTTPSConnection):
        self.HTTPConnection = HTTPConnection
        self.HTTPSConnection = HTTPSConnection

    def __call__(self, environ, start_response):
        scheme = environ['wsgi.url_scheme']
        if scheme == 'http':
            ConnClass = self.HTTPConnection
        elif scheme == 'https':
            ConnClass = self.HTTPSConnection
        else:
            raise ValueError(
                "Unknown scheme: %r" % scheme)
        if 'SERVER_NAME' not in environ:
            host = environ.get('HTTP_HOST')
            if not host:
                raise ValueError(
                    "environ contains neither SERVER_NAME nor HTTP_HOST")
            if ':' in host:
                host, port = host.split(':', 1)
            else:
                if scheme == 'http':
                    port = '80'
                else:
                    port = '443'
            environ['SERVER_NAME'] = host
            environ['SERVER_PORT'] = port
        kw = {}
        if ('webob.client.timeout' in environ and
            self._timeout_supported(ConnClass) ):
            kw['timeout'] = environ['webob.client.timeout']
        conn = ConnClass('%(SERVER_NAME)s:%(SERVER_PORT)s' % environ, **kw)
        headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                key = key[5:].replace('_', '-').title()
                headers[key] = value
        path = (url_quote(environ.get('SCRIPT_NAME', ''))
                + url_quote(environ.get('PATH_INFO', '')))
        if environ.get('QUERY_STRING'):
            path += '?' + environ['QUERY_STRING']
        try:
            content_length = int(environ.get('CONTENT_LENGTH', '0'))
        except ValueError:
            content_length = 0
        ## FIXME: there is no streaming of the body, and that might be useful
        ## in some cases
        if content_length:
            body = environ['wsgi.input'].read(content_length)
        else:
            body = ''
        headers['Content-Length'] = content_length
        if environ.get('CONTENT_TYPE'):
            headers['Content-Type'] = environ['CONTENT_TYPE']
        if not path.startswith("/"):
            path = "/" + path
        try:
            conn.request(environ['REQUEST_METHOD'],
                         path, body, headers)
            res = conn.getresponse()
        except socket.timeout:
            resp = exc.HTTPGatewayTimeout()
            return resp(environ, start_response)
        except (socket.error, socket.gaierror) as e:
            if ((isinstance(e, socket.error) and e.args[0] == -2) or
                (isinstance(e, socket.gaierror) and e.args[0] == 8)):
                # Name or service not known
                resp = exc.HTTPBadGateway(
                    "Name or service not known (bad domain name: %s)"
                    % environ['SERVER_NAME'])
                return resp(environ, start_response)
            elif e.args[0] in _e_refused: # pragma: no cover
                # Connection refused
                resp = exc.HTTPBadGateway("Connection refused")
                return resp(environ, start_response)
            raise
        headers_out = self.parse_headers(res.msg)
        status = '%s %s' % (res.status, res.reason)
        start_response(status, headers_out)
        length = res.getheader('content-length')
        # FIXME: This shouldn't really read in all the content at once
        if length is not None:
            body = res.read(int(length))
        else:
            body = res.read()
        conn.close()
        return [body]

    # Remove these headers from response (specify lower case header
    # names):
    filtered_headers = (
        'transfer-encoding',
    )

    MULTILINE_RE = re.compile(r'\r?\n\s*')

    def parse_headers(self, message):
        """
        Turn a Message object into a list of WSGI-style headers.
        """
        headers_out = []
        if PY3:  # pragma: no cover
            headers = message._headers
        else:  # pragma: no cover
            headers = message.headers
        for full_header in headers:
            if not full_header: # pragma: no cover
                # Shouldn't happen, but we'll just ignore
                continue
            if full_header[0].isspace():  # pragma: no cover
                # Continuation line, add to the last header
                if not headers_out:
                    raise ValueError(
                        "First header starts with a space (%r)" % full_header)
                last_header, last_value = headers_out.pop()
                value = last_value + ', ' + full_header.strip()
                headers_out.append((last_header, value))
                continue
            if isinstance(full_header, tuple):  # pragma: no cover
                header, value = full_header
            else:  # pragma: no cover
                try:
                    header, value = full_header.split(':', 1)
                except:
                    raise ValueError("Invalid header: %r" % (full_header,))
            value = value.strip()
            if '\n' in value or '\r\n' in value:  # pragma: no cover
                # Python 3 has multiline values for continuations, Python 2
                # has two items in headers
                value = self.MULTILINE_RE.sub(', ', value)
            if header.lower() not in self.filtered_headers:
                headers_out.append((header, value))
        return headers_out

    def _timeout_supported(self, ConnClass):
        if sys.version_info < (2, 7) and ConnClass in (
            httplib.HTTPConnection, httplib.HTTPSConnection): # pragma: no cover
            return False
        return True


send_request_app = SendRequest()

_e_refused = (errno.ECONNREFUSED,)
if hasattr(errno, 'ENODATA'): # pragma: no cover
    _e_refused += (errno.ENODATA,)

########NEW FILE########
__FILENAME__ = compat
# code stolen from "six"

import sys
import types

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3: # pragma: no cover
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    long = int
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    long = long

# TODO check if errors is ever used

def text_(s, encoding='latin-1', errors='strict'):
    if isinstance(s, bytes):
        return s.decode(encoding, errors)
    return s

def bytes_(s, encoding='latin-1', errors='strict'):
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    return s

if PY3: # pragma: no cover
    def native_(s, encoding='latin-1', errors='strict'):
        if isinstance(s, text_type):
            return s
        return str(s, encoding, errors)
else:
    def native_(s, encoding='latin-1', errors='strict'):
        if isinstance(s, text_type):
            return s.encode(encoding, errors)
        return str(s)

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty

if PY3: # pragma: no cover
    from urllib import parse
    urlparse = parse
    from urllib.parse import quote as url_quote
    from urllib.parse import urlencode as url_encode, quote_plus
    from urllib.request import urlopen as url_open
else:
    import urlparse
    from urllib import quote_plus
    from urllib import quote as url_quote
    from urllib import unquote as url_unquote
    from urllib import urlencode as url_encode
    from urllib2 import urlopen as url_open

if PY3: # pragma: no cover
    def reraise(exc_info):
        etype, exc, tb = exc_info
        if exc.__traceback__ is not tb:
            raise exc.with_traceback(tb)
        raise exc
else: # pragma: no cover
    exec("def reraise(exc): raise exc[0], exc[1], exc[2]")


if PY3: # pragma: no cover
    def iteritems_(d):
        return d.items()
    def itervalues_(d):
        return d.values()
else:
    def iteritems_(d):
        return d.iteritems()
    def itervalues_(d):
        return d.itervalues()


if PY3: # pragma: no cover
    def unquote(string):
        if not string:
            return b''
        res = string.split(b'%')
        if len(res) != 1:
            string = res[0]
            for item in res[1:]:
                try:
                    string += bytes([int(item[:2], 16)]) + item[2:]
                except ValueError:
                    string += b'%' + item
        return string

    def url_unquote(s):
        return unquote(s.encode('ascii')).decode('latin-1')

    def parse_qsl_text(qs, encoding='utf-8'):
        qs = qs.encode('latin-1')
        qs = qs.replace(b'+', b' ')
        pairs = [s2 for s1 in qs.split(b'&') for s2 in s1.split(b';') if s2]
        for name_value in pairs:
            nv = name_value.split(b'=', 1)
            if len(nv) != 2:
                nv.append('')
            name = unquote(nv[0])
            value = unquote(nv[1])
            yield (name.decode(encoding), value.decode(encoding))

else:
    from urlparse import parse_qsl

    def parse_qsl_text(qs, encoding='utf-8'):
        qsl = parse_qsl(
            qs,
            keep_blank_values=True,
            strict_parsing=False
        )
        for (x, y) in qsl:
            yield (x.decode(encoding), y.decode(encoding))


if PY3: # pragma no cover
    from html import escape
else:
    from cgi import escape

########NEW FILE########
__FILENAME__ = cookies
import collections

import base64
import binascii
import hashlib
import hmac
import json
from datetime import (
    date,
    datetime,
    timedelta,
    )
import re
import string
import time

from webob.compat import (
    PY3,
    text_type,
    bytes_,
    text_,
    native_,
    string_types,
    )

from webob.util import strings_differ

__all__ = ['Cookie', 'CookieProfile', 'SignedCookieProfile', 'SignedSerializer',
           'JSONSerializer', 'make_cookie']

_marker = object()

class RequestCookies(collections.MutableMapping):

    _cache_key = 'webob._parsed_cookies'

    def __init__(self, environ):
        self._environ = environ

    @property
    def _cache(self):
        env = self._environ
        header = env.get('HTTP_COOKIE', '')
        cache, cache_header = env.get(self._cache_key, ({}, None))
        if cache_header == header:
            return cache
        d = lambda b: b.decode('utf8')
        cache = dict((d(k), d(v)) for k,v in parse_cookie(header))
        env[self._cache_key] = (cache, header)
        return cache

    def _mutate_header(self, name, value):
        header = self._environ.get('HTTP_COOKIE')
        had_header = header is not None
        header = header or ''
        if PY3: # pragma: no cover
                header = header.encode('latin-1')
        bytes_name = bytes_(name, 'ascii')
        if value is None:
            replacement = None
        else:
            bytes_val = _value_quote(bytes_(value, 'utf-8'))
            replacement = bytes_name + b'=' + bytes_val
        matches = _rx_cookie.finditer(header)
        found = False
        for match in matches:
            start, end = match.span()
            match_name = match.group(1)
            if match_name == bytes_name:
                found = True
                if replacement is None: # remove value
                    header = header[:start].rstrip(b' ;') + header[end:]
                else: # replace value
                    header = header[:start] + replacement + header[end:]
                break
        else:
            if replacement is not None:
                if header:
                    header += b'; ' + replacement
                else:
                    header = replacement

        if header:
            self._environ['HTTP_COOKIE'] = native_(header, 'latin-1')
        elif had_header:
            self._environ['HTTP_COOKIE'] = ''

        return found

    def _valid_cookie_name(self, name):
        if not isinstance(name, string_types):
            raise TypeError(name, 'cookie name must be a string')
        if not isinstance(name, text_type):
            name = text_(name, 'utf-8')
        try:
            bytes_cookie_name = bytes_(name, 'ascii')
        except UnicodeEncodeError:
            raise TypeError('cookie name must be encodable to ascii')
        if not _valid_cookie_name(bytes_cookie_name):
            raise TypeError('cookie name must be valid according to RFC 6265')
        return name

    def __setitem__(self, name, value):
        name = self._valid_cookie_name(name)
        if not isinstance(value, string_types):
            raise ValueError(value, 'cookie value must be a string')
        if not isinstance(value, text_type):
            try:
                value = text_(value, 'utf-8')
            except UnicodeDecodeError:
                raise ValueError(
                    value, 'cookie value must be utf-8 binary or unicode')
        self._mutate_header(name, value)

    def __getitem__(self, name):
        return self._cache[name]

    def get(self, name, default=None):
        return self._cache.get(name, default)

    def __delitem__(self, name):
        name = self._valid_cookie_name(name)
        found = self._mutate_header(name, None)
        if not found:
            raise KeyError(name)

    def keys(self):
        return self._cache.keys()

    def values(self):
        return self._cache.values()

    def items(self):
        return self._cache.items()

    if not PY3:
        def iterkeys(self):
            return self._cache.iterkeys()

        def itervalues(self):
            return self._cache.itervalues()

        def iteritems(self):
            return self._cache.iteritems()

    def __contains__(self, name):
        return name in self._cache

    def __iter__(self):
        return self._cache.__iter__()

    def __len__(self):
        return len(self._cache)

    def clear(self):
        self._environ['HTTP_COOKIE'] = ''

    def __repr__(self):
        return '<RequestCookies (dict-like) with values %r>' % (self._cache,)


class Cookie(dict):
    def __init__(self, input=None):
        if input:
            self.load(input)

    def load(self, data):
        morsel = {}
        for key, val in _parse_cookie(data):
            if key.lower() in _c_keys:
                morsel[key] = val
            else:
                morsel = self.add(key, val)

    def add(self, key, val):
        if not isinstance(key, bytes):
           key = key.encode('ascii', 'replace')
        if not _valid_cookie_name(key):
            return {}
        r = Morsel(key, val)
        dict.__setitem__(self, key, r)
        return r
    __setitem__ = add

    def serialize(self, full=True):
        return '; '.join(m.serialize(full) for m in self.values())

    def values(self):
        return [m for _, m in sorted(self.items())]

    __str__ = serialize

    def __repr__(self):
        return '<%s: [%s]>' % (self.__class__.__name__,
                               ', '.join(map(repr, self.values())))


def _parse_cookie(data):
    if PY3: # pragma: no cover
        data = data.encode('latin-1')
    for key, val in _rx_cookie.findall(data):
        yield key, _unquote(val)

def parse_cookie(data):
    """
    Parse cookies ignoring anything except names and values
    """
    return ((k,v) for k,v in _parse_cookie(data) if _valid_cookie_name(k))


def cookie_property(key, serialize=lambda v: v):
    def fset(self, v):
        self[key] = serialize(v)
    return property(lambda self: self[key], fset)

def serialize_max_age(v):
    if isinstance(v, timedelta):
        v = str(v.seconds + v.days*24*60*60)
    elif isinstance(v, int):
        v = str(v)
    return bytes_(v)

def serialize_cookie_date(v):
    if v is None:
        return None
    elif isinstance(v, bytes):
        return v
    elif isinstance(v, text_type):
        return v.encode('ascii')
    elif isinstance(v, int):
        v = timedelta(seconds=v)
    if isinstance(v, timedelta):
        v = datetime.utcnow() + v
    if isinstance(v, (datetime, date)):
        v = v.timetuple()
    r = time.strftime('%%s, %d-%%s-%Y %H:%M:%S GMT', v)
    return bytes_(r % (weekdays[v[6]], months[v[1]]), 'ascii')

class Morsel(dict):
    __slots__ = ('name', 'value')
    def __init__(self, name, value):
        self.name = bytes_(name, encoding='ascii')
        self.value = bytes_(value, encoding='ascii')
        assert _valid_cookie_name(self.name)
        self.update(dict.fromkeys(_c_keys, None))

    path = cookie_property(b'path')
    domain = cookie_property(b'domain')
    comment = cookie_property(b'comment')
    expires = cookie_property(b'expires', serialize_cookie_date)
    max_age = cookie_property(b'max-age', serialize_max_age)
    httponly = cookie_property(b'httponly', bool)
    secure = cookie_property(b'secure', bool)

    def __setitem__(self, k, v):
        k = bytes_(k.lower(), 'ascii')
        if k in _c_keys:
            dict.__setitem__(self, k, v)

    def serialize(self, full=True):
        result = []
        add = result.append
        add(self.name + b'=' + _value_quote(self.value))
        if full:
            for k in _c_valkeys:
                v = self[k]
                if v:
                    info = _c_renames[k]
                    name = info['name']
                    quoter = info['quoter']
                    add(name + b'=' + quoter(v))
            expires = self[b'expires']
            if expires:
                add(b'expires=' + expires)
            if self.secure:
                add(b'secure')
            if self.httponly:
                add(b'HttpOnly')
        return native_(b'; '.join(result), 'ascii')

    __str__ = serialize

    def __repr__(self):
        return '<%s: %s=%r>' % (self.__class__.__name__,
            native_(self.name),
            native_(self.value)
        )

#
# parsing
#


_re_quoted = r'"(?:\\"|.)*?"' # any doublequoted string
_legal_special_chars = "~!@#$%^&*()_+=-`.?|:/(){}<>'"
_re_legal_char  = r"[\w\d%s]" % re.escape(_legal_special_chars)
_re_expires_val = r"\w{3},\s[\w\d-]{9,11}\s[\d:]{8}\sGMT"
_re_cookie_str_key = r"(%s+?)" % _re_legal_char
_re_cookie_str_equal = r"\s*=\s*"
_re_unquoted_val = r"(?:%s|\\(?:[0-3][0-7][0-7]|.))*" % _re_legal_char
_re_cookie_str_val = r"(%s|%s|%s)" % (_re_quoted, _re_expires_val,
                                       _re_unquoted_val)
_re_cookie_str = _re_cookie_str_key + _re_cookie_str_equal + _re_cookie_str_val

_rx_cookie = re.compile(bytes_(_re_cookie_str, 'ascii'))
_rx_unquote = re.compile(bytes_(r'\\([0-3][0-7][0-7]|.)', 'ascii'))

_bchr = (lambda i: bytes([i])) if PY3 else chr
_ch_unquote_map = dict((bytes_('%03o' % i), _bchr(i))
    for i in range(256)
)
_ch_unquote_map.update((v, v) for v in list(_ch_unquote_map.values()))

_b_dollar_sign = ord('$') if PY3 else '$'
_b_quote_mark = ord('"') if PY3 else '"'

def _unquote(v):
    #assert isinstance(v, bytes)
    if v and v[0] == v[-1] == _b_quote_mark:
        v = v[1:-1]
    return _rx_unquote.sub(_ch_unquote, v)

def _ch_unquote(m):
    return _ch_unquote_map[m.group(1)]


#
# serializing
#

# these chars can be in cookie value w/o causing it to be quoted
# see http://tools.ietf.org/html/rfc6265#section-4.1.1
# and https://github.com/Pylons/webob/pull/104#issuecomment-28044314

# allowed in cookie values without quoting:
# <space> (0x21), "#$%&'()*+" (0x25-0x2B), "-./0123456789:" (0x2D-0x3A),
# "<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[" (0x3C-0x5B),
# "]^_`abcdefghijklmnopqrstuvwxyz{|}~" (0x5D-0x7E)

_no_escape_special_chars = "!#$%&'()*+-./<=>?@[]^_`{|}~"
_no_escape_chars = (string.ascii_letters + string.digits +
                    _no_escape_special_chars)
_no_escape_bytes = bytes_(_no_escape_chars)

# these chars should not be quoted themselves but if they are present they
# should cause the cookie value to be surrounded by quotes (voodoo inherited
# by old webob code without any comments)
_escape_noop_chars = _no_escape_chars + ': '

# this is a map used to escape the values
_escape_map = dict((chr(i), '\\%03o' % i) for i in range(256))
_escape_map.update(zip(_escape_noop_chars, _escape_noop_chars))
if PY3: # pragma: no cover
    # convert to {int -> bytes}
    _escape_map = dict(
        (ord(k), bytes_(v, 'ascii')) for k, v in _escape_map.items()
        )
_escape_char = _escape_map.__getitem__

weekdays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
months = (None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
          'Oct', 'Nov', 'Dec')

_notrans_binary = b' '*256

# these are the characters accepted in cookie *names*
_valid_token_chars = string.ascii_letters + string.digits + "!#$%&'*+,-.^_`|~"
_valid_token_bytes = bytes_(_valid_token_chars)

def _value_needs_quoting(v):
    return v.translate(_notrans_binary, _no_escape_bytes)

def _value_quote(v):
    #assert isinstance(v, bytes)
    if _value_needs_quoting(v):
        return b'"' + b''.join(map(_escape_char, v)) + b'"'
    return v

def _valid_cookie_name(key):
    return isinstance(key, bytes) and not (
        key.translate(_notrans_binary, _valid_token_bytes)
        or key[0] == _b_dollar_sign
        or key.lower() in _c_keys
    )

def _path_quote(v):
    return b''.join(map(_escape_char, v))

_domain_quote = _path_quote
_max_age_quote = _path_quote

_c_renames = {
    b"path" : {'name':b"Path", 'quoter':_path_quote},
    b"comment" : {'name':b"Comment", 'quoter':_value_quote},
    b"domain" : {'name':b"Domain", 'quoter':_domain_quote},
    b"max-age" : {'name':b"Max-Age", 'quoter':_max_age_quote},
    }
_c_valkeys = sorted(_c_renames)
_c_keys = set(_c_renames)
_c_keys.update([b'expires', b'secure', b'httponly'])


def make_cookie(name, value, max_age=None, path='/', domain=None,
                secure=False, httponly=False, comment=None):
    """ Generate a cookie value.  If ``value`` is None, generate a cookie value
    with an expiration date in the past"""
    
    # We are deleting the cookie, override max_age and expires
    if value is None:
        value = b''
        # Note that the max-age value of zero is technically contraspec;
        # RFC6265 says that max-age cannot be zero.  However, all browsers
        # appear to support this to mean "delete immediately".
        # http://www.timwilson.id.au/news-three-critical-problems-with-rfc6265.html
        max_age = 0
        expires = 'Wed, 31-Dec-97 23:59:59 GMT'

    # Convert max_age to seconds
    elif isinstance(max_age, timedelta):
        max_age = (max_age.days * 60 * 60 * 24) + max_age.seconds
        expires = max_age
    else:
        expires = max_age

    morsel = Morsel(name, value)

    if domain is not None:
        morsel.domain = bytes_(domain)
    if path is not None:
        morsel.path = bytes_(path)
    if httponly:
        morsel.httponly = True
    if secure:
        morsel.secure = True
    if max_age is not None:
        morsel.max_age = max_age
    if expires is not None:
        morsel.expires = expires
    if comment is not None:
        morsel.comment = bytes_(comment)
    return morsel.serialize()

class JSONSerializer(object):
    """ A serializer which uses `json.dumps`` and ``json.loads``"""
    def dumps(self, appstruct):
        return bytes_(json.dumps(appstruct), encoding='utf-8')

    def loads(self, bstruct):
        # NB: json.loads raises ValueError if no json object can be decoded
        # so we don't have to do it explicitly here.
        return json.loads(text_(bstruct, encoding='utf-8'))

class SignedSerializer(object):
    """
    A helper to cryptographically sign arbitrary content using HMAC.

    The serializer accepts arbitrary functions for performing the actual
    serialization and deserialization.

    ``secret``
      A string which is used to sign the cookie. The secret should be at
      least as long as the block size of the selected hash algorithm. For
      ``sha512`` this would mean a 128 bit (64 character) secret.

    ``salt``
      A namespace to avoid collisions between different uses of a shared
      secret.

    ``hashalg``
      The HMAC digest algorithm to use for signing. The algorithm must be
      supported by the :mod:`hashlib` library. Default: ``'sha512'``.

    ``serializer``
      An object with two methods: `loads`` and ``dumps``.  The ``loads`` method
      should accept bytes and return a Python object.  The ``dumps`` method
      should accept a Python object and return bytes.  A ``ValueError`` should
      be raised for malformed inputs.  Default: ``None`, which will use a
      derivation of :func:`json.dumps` and ``json.loads``.

    """

    def __init__(self,
                 secret,
                 salt,
                 hashalg='sha512',
                 serializer=None,
                 ):
        self.salt = salt
        self.secret = secret
        self.hashalg = hashalg

        try:
            # bwcompat with webob <= 1.3.1, leave latin-1 as the default
            self.salted_secret = bytes_(salt or '') + bytes_(secret)
        except UnicodeEncodeError:
            self.salted_secret = (
                bytes_(salt or '', 'utf-8') + bytes_(secret, 'utf-8'))

        self.digestmod = lambda string=b'': hashlib.new(self.hashalg, string)
        self.digest_size = self.digestmod().digest_size

        if serializer is None:
            serializer = JSONSerializer()

        self.serializer = serializer

    def dumps(self, appstruct):
        """
        Given an ``appstruct``, serialize and sign the data.

        Returns a bytestring.
        """
        cstruct = self.serializer.dumps(appstruct) # will be bytes
        sig = hmac.new(self.salted_secret, cstruct, self.digestmod).digest()
        return base64.urlsafe_b64encode(sig + cstruct).rstrip(b'=')

    def loads(self, bstruct):
        """
        Given a ``bstruct`` (a bytestring), verify the signature and then
        deserialize and return the deserialized value.

        A ``ValueError`` will be raised if the signature fails to validate.
        """
        try:
            b64padding = b'=' * (-len(bstruct) % 4)
            fstruct = base64.urlsafe_b64decode(bytes_(bstruct) + b64padding)
        except (binascii.Error, TypeError) as e:
            raise ValueError('Badly formed base64 data: %s' % e)

        cstruct = fstruct[self.digest_size:]
        expected_sig = fstruct[:self.digest_size]

        sig = hmac.new(
            self.salted_secret, bytes_(cstruct), self.digestmod).digest()

        if strings_differ(sig, expected_sig):
            raise ValueError('Invalid signature')

        return self.serializer.loads(cstruct)


_default = object()

class CookieProfile(object):
    """
    A helper class that helps bring some sanity to the insanity that is cookie
    handling.

    The helper is capable of generating multiple cookies if necessary to
    support subdomains and parent domains.

    ``cookie_name``
      The name of the cookie used for sessioning. Default: ``'session'``.

    ``max_age``
      The maximum age of the cookie used for sessioning (in seconds).
      Default: ``None`` (browser scope).

    ``secure``
      The 'secure' flag of the session cookie. Default: ``False``.

    ``httponly``
      Hide the cookie from Javascript by setting the 'HttpOnly' flag of the
      session cookie. Default: ``False``.

    ``path``
      The path used for the session cookie. Default: ``'/'``.

    ``domains``
      The domain(s) used for the session cookie. Default: ``None`` (no domain).
      Can be passed an iterable containing multiple domains, this will set
      multiple cookies one for each domain.

    ``serializer``
      An object with two methods: ``loads`` and ``dumps``.  The ``loads`` method
      should accept a bytestring and return a Python object.  The ``dumps``
      method should accept a Python object and return bytes.  A ``ValueError``
      should be raised for malformed inputs.  Default: ``None``, which will use
      a derivation of :func:`json.dumps` and :func:`json.loads`.

    """

    def __init__(self,
                 cookie_name,
                 secure=False,
                 max_age=None,
                 httponly=None,
                 path='/',
                 domains=None,
                 serializer=None
                 ):
        self.cookie_name = cookie_name
        self.secure = secure
        self.max_age = max_age
        self.httponly = httponly
        self.path = path
        self.domains = domains

        if serializer is None:
            serializer = JSONSerializer()

        self.serializer = serializer
        self.request = None

    def __call__(self, request):
        """ Bind a request to a copy of this instance and return it"""

        return self.bind(request)

    def bind(self, request):
        """ Bind a request to a copy of this instance and return it"""

        selfish = CookieProfile(
            self.cookie_name,
            self.secure,
            self.max_age,
            self.httponly,
            self.path,
            self.domains,
            self.serializer,
            )
        selfish.request = request
        return selfish

    def get_value(self):
        """ Looks for a cookie by name in the currently bound request, and
        returns its value.  If the cookie profile is not bound to a request,
        this method will raise a :exc:`ValueError`.

        Looks for the cookie in the cookies jar, and if it can find it it will
        attempt to deserialize it.  Returns ``None`` if there is no cookie or
        if the value in the cookie cannot be successfully deserialized.
        """

        if not self.request:
            raise ValueError('No request bound to cookie profile')

        cookie = self.request.cookies.get(self.cookie_name)

        if cookie is not None:
            try:
                return self.serializer.loads(bytes_(cookie))
            except ValueError:
                return None

    def set_cookies(self, response, value, domains=_default, max_age=_default,
                    path=_default, secure=_default, httponly=_default):
        """ Set the cookies on a response."""
        cookies = self.get_headers(
            value,
            domains=domains,
            max_age=max_age,
            path=path,
            secure=secure,
            httponly=httponly
            )
        response.headerlist.extend(cookies)
        return response

    def get_headers(self, value, domains=_default, max_age=_default,
                    path=_default, secure=_default, httponly=_default):
        """ Retrieve raw headers for setting cookies.

        Returns a list of headers that should be set for the cookies to
        be correctly tracked.
        """
        if value is None:
            max_age = 0
            bstruct = None
        else:
            bstruct = self.serializer.dumps(value)

        return self._get_cookies(
            bstruct,
            domains=domains,
            max_age=max_age,
            path=path,
            secure=secure,
            httponly=httponly
            )

    def _get_cookies(self, value, domains, max_age, path, secure, httponly):
        """Internal function

        This returns a list of cookies that are valid HTTP Headers.

        :environ: The request environment
        :value: The value to store in the cookie
        :domains: The domains, overrides any set in the CookieProfile
        :max_age: The max_age, overrides any set in the CookieProfile
        :path: The path, overrides any set in the CookieProfile
        :secure: Set this cookie to secure, overrides any set in CookieProfile
        :httponly: Set this cookie to HttpOnly, overrides any set in CookieProfile

        """

        # If the user doesn't provide values, grab the defaults
        if domains is _default:
            domains = self.domains

        if max_age is _default:
            max_age = self.max_age

        if path is _default:
            path = self.path

        if secure is _default:
            secure = self.secure

        if httponly is _default:
            httponly = self.httponly

        # Length selected based upon http://browsercookielimits.x64.me
        if value is not None and len(value) > 4093:
            raise ValueError(
                'Cookie value is too long to store (%s bytes)' %
                len(value)
            )

        cookies = []

        if not domains:
            cookievalue = make_cookie(
                    self.cookie_name,
                    value,
                    path=path,
                    max_age=max_age,
                    httponly=httponly,
                    secure=secure
            )
            cookies.append(('Set-Cookie', cookievalue))

        else:
            for domain in domains:
                cookievalue = make_cookie(
                    self.cookie_name,
                    value,
                    path=path,
                    domain=domain,
                    max_age=max_age,
                    httponly=httponly,
                    secure=secure,
                )
                cookies.append(('Set-Cookie', cookievalue))

        return cookies


class SignedCookieProfile(CookieProfile):
    """
    A helper for generating cookies that are signed to prevent tampering.

    By default this will create a single cookie, given a value it will
    serialize it, then use HMAC to cryptographically sign the data. Finally
    the result is base64-encoded for transport. This way a remote user can
    not tamper with the value without uncovering the secret/salt used.

    ``secret``
      A string which is used to sign the cookie. The secret should be at
      least as long as the block size of the selected hash algorithm. For
      ``sha512`` this would mean a 128 bit (64 character) secret.

    ``salt``
      A namespace to avoid collisions between different uses of a shared
      secret. 

    ``hashalg``
      The HMAC digest algorithm to use for signing. The algorithm must be
      supported by the :mod:`hashlib` library. Default: ``'sha512'``.

    ``cookie_name``
      The name of the cookie used for sessioning. Default: ``'session'``.

    ``max_age``
      The maximum age of the cookie used for sessioning (in seconds).
      Default: ``None`` (browser scope).

    ``secure``
      The 'secure' flag of the session cookie. Default: ``False``.

    ``httponly``
      Hide the cookie from Javascript by setting the 'HttpOnly' flag of the
      session cookie. Default: ``False``.

    ``path``
      The path used for the session cookie. Default: ``'/'``.

    ``domains``
      The domain(s) used for the session cookie. Default: ``None`` (no domain).
      Can be passed an iterable containing multiple domains, this will set
      multiple cookies one for each domain.

    ``serializer``
      An object with two methods: `loads`` and ``dumps``.  The ``loads`` method
      should accept bytes and return a Python object.  The ``dumps`` method
      should accept a Python object and return bytes.  A ``ValueError`` should
      be raised for malformed inputs.  Default: ``None`, which will use a
      derivation of :func:`json.dumps` and ``json.loads``.
    """
    def __init__(self,
                 secret,
                 salt,
                 cookie_name,
                 secure=False,
                 max_age=None,
                 httponly=False,
                 path="/",
                 domains=None,
                 hashalg='sha512',
                 serializer=None,
                 ):
        self.secret = secret
        self.salt = salt
        self.hashalg = hashalg
        self.original_serializer = serializer

        signed_serializer = SignedSerializer(
            secret,
            salt,
            hashalg,
            serializer=self.original_serializer,
            )
        CookieProfile.__init__(
            self,
            cookie_name,
            secure=secure,
            max_age=max_age,
            httponly=httponly,
            path=path,
            domains=domains,
            serializer=signed_serializer,
            )

    def bind(self, request):
        """ Bind a request to a copy of this instance and return it"""

        selfish = SignedCookieProfile(
            self.secret,
            self.salt,
            self.cookie_name,
            self.secure,
            self.max_age,
            self.httponly,
            self.path,
            self.domains,
            self.hashalg,
            self.original_serializer,
            )
        selfish.request = request
        return selfish


########NEW FILE########
__FILENAME__ = datetime_utils
import calendar

from datetime import (
    date,
    datetime,
    timedelta,
    tzinfo,
    )

from email.utils import (
    formatdate,
    mktime_tz,
    parsedate_tz,
    )

import time

from webob.compat import (
    integer_types,
    long,
    native_,
    text_type,
    )

__all__ = [
    'UTC', 'timedelta_to_seconds',
    'year', 'month', 'week', 'day', 'hour', 'minute', 'second',
    'parse_date', 'serialize_date',
    'parse_date_delta', 'serialize_date_delta',
]

_now = datetime.now # hook point for unit tests

class _UTC(tzinfo):
    def dst(self, dt):
        return timedelta(0)
    def utcoffset(self, dt):
        return timedelta(0)
    def tzname(self, dt):
        return 'UTC'
    def __repr__(self):
        return 'UTC'

UTC = _UTC()



def timedelta_to_seconds(td):
    """
    Converts a timedelta instance to seconds.
    """
    return td.seconds + (td.days*24*60*60)

day = timedelta(days=1)
week = timedelta(weeks=1)
hour = timedelta(hours=1)
minute = timedelta(minutes=1)
second = timedelta(seconds=1)
# Estimate, I know; good enough for expirations
month = timedelta(days=30)
year = timedelta(days=365)


def parse_date(value):
    if not value:
        return None
    try:
        value = native_(value)
    except:
        return None
    t = parsedate_tz(value)
    if t is None:
        # Could not parse
        return None
    if t[-1] is None:
        # No timezone given.  None would mean local time, but we'll force UTC
        t = t[:9] + (0,)
    t = mktime_tz(t)
    return datetime.fromtimestamp(t, UTC)

def serialize_date(dt):
    if isinstance(dt, (bytes, text_type)):
        return native_(dt)
    if isinstance(dt, timedelta):
        dt = _now() + dt
    if isinstance(dt, (datetime, date)):
        dt = dt.timetuple()
    if isinstance(dt, (tuple, time.struct_time)):
        dt = calendar.timegm(dt)
    if not (isinstance(dt, float) or isinstance(dt, integer_types)):
        raise ValueError(
            "You must pass in a datetime, date, time tuple, or integer object, "
            "not %r" % dt)
    return formatdate(dt, usegmt=True)



def parse_date_delta(value):
    """
    like parse_date, but also handle delta seconds
    """
    if not value:
        return None
    try:
        value = int(value)
    except ValueError:
        return parse_date(value)
    else:
        return _now() + timedelta(seconds=value)


def serialize_date_delta(value):
    if isinstance(value, (float, int, long)):
        return str(int(value))
    else:
        return serialize_date(value)

########NEW FILE########
__FILENAME__ = dec
"""
Decorators to wrap functions to make them WSGI applications.

The main decorator :class:`wsgify` turns a function into a WSGI
application (while also allowing normal calling of the method with an
instantiated request).
"""

from webob.compat import (
    bytes_,
    text_type,
    )

from webob.request import Request
from webob.exc import HTTPException

__all__ = ['wsgify']

class wsgify(object):
    """Turns a request-taking, response-returning function into a WSGI
    app

    You can use this like::

        @wsgify
        def myfunc(req):
            return webob.Response('hey there')

    With that ``myfunc`` will be a WSGI application, callable like
    ``app_iter = myfunc(environ, start_response)``.  You can also call
    it like normal, e.g., ``resp = myfunc(req)``.  (You can also wrap
    methods, like ``def myfunc(self, req)``.)

    If you raise exceptions from :mod:`webob.exc` they will be turned
    into WSGI responses.

    There are also several parameters you can use to customize the
    decorator.  Most notably, you can use a :class:`webob.Request`
    subclass, like::

        class MyRequest(webob.Request):
            @property
            def is_local(self):
                return self.remote_addr == '127.0.0.1'
        @wsgify(RequestClass=MyRequest)
        def myfunc(req):
            if req.is_local:
                return Response('hi!')
            else:
                raise webob.exc.HTTPForbidden

    Another customization you can add is to add `args` (positional
    arguments) or `kwargs` (of course, keyword arguments).  While
    generally not that useful, you can use this to create multiple
    WSGI apps from one function, like::

        import simplejson
        def serve_json(req, json_obj):
            return Response(json.dumps(json_obj),
                            content_type='application/json')

        serve_ob1 = wsgify(serve_json, args=(ob1,))
        serve_ob2 = wsgify(serve_json, args=(ob2,))

    You can return several things from a function:

    * A :class:`webob.Response` object (or subclass)
    * *Any* WSGI application
    * None, and then ``req.response`` will be used (a pre-instantiated
      Response object)
    * A string, which will be written to ``req.response`` and then that
      response will be used.
    * Raise an exception from :mod:`webob.exc`

    Also see :func:`wsgify.middleware` for a way to make middleware.

    You can also subclass this decorator; the most useful things to do
    in a subclass would be to change `RequestClass` or override
    `call_func` (e.g., to add ``req.urlvars`` as keyword arguments to
    the function).
    """

    RequestClass = Request

    def __init__(self, func=None, RequestClass=None,
                 args=(), kwargs=None, middleware_wraps=None):
        self.func = func
        if (RequestClass is not None
            and RequestClass is not self.RequestClass):
            self.RequestClass = RequestClass
        self.args = tuple(args)
        if kwargs is None:
            kwargs = {}
        self.kwargs = kwargs
        self.middleware_wraps = middleware_wraps

    def __repr__(self):
        return '<%s at %s wrapping %r>' % (self.__class__.__name__,
                                           id(self), self.func)

    def __get__(self, obj, type=None):
        # This handles wrapping methods
        if hasattr(self.func, '__get__'):
            return self.clone(self.func.__get__(obj, type))
        else:
            return self

    def __call__(self, req, *args, **kw):
        """Call this as a WSGI application or with a request"""
        func = self.func
        if func is None:
            if args or kw:
                raise TypeError(
                    "Unbound %s can only be called with the function it "
                    "will wrap" % self.__class__.__name__)
            func = req
            return self.clone(func)
        if isinstance(req, dict):
            if len(args) != 1 or kw:
                raise TypeError(
                    "Calling %r as a WSGI app with the wrong signature")
            environ = req
            start_response = args[0]
            req = self.RequestClass(environ)
            req.response = req.ResponseClass()
            try:
                args = self.args
                if self.middleware_wraps:
                    args = (self.middleware_wraps,) + args
                resp = self.call_func(req, *args, **self.kwargs)
            except HTTPException as exc:
                resp = exc
            if resp is None:
                ## FIXME: I'm not sure what this should be?
                resp = req.response
            if isinstance(resp, text_type):
                resp = bytes_(resp, req.charset)
            if isinstance(resp, bytes):
                body = resp
                resp = req.response
                resp.write(body)
            if resp is not req.response:
                resp = req.response.merge_cookies(resp)
            return resp(environ, start_response)
        else:
            if self.middleware_wraps:
                args = (self.middleware_wraps,) + args
            return self.func(req, *args, **kw)

    def get(self, url, **kw):
        """Run a GET request on this application, returning a Response.

        This creates a request object using the given URL, and any
        other keyword arguments are set on the request object (e.g.,
        ``last_modified=datetime.now()``).

        ::

            resp = myapp.get('/article?id=10')
        """
        kw.setdefault('method', 'GET')
        req = self.RequestClass.blank(url, **kw)
        return self(req)

    def post(self, url, POST=None, **kw):
        """Run a POST request on this application, returning a Response.

        The second argument (`POST`) can be the request body (a
        string), or a dictionary or list of two-tuples, that give the
        POST body.

        ::

            resp = myapp.post('/article/new',
                              dict(title='My Day',
                                   content='I ate a sandwich'))
        """
        kw.setdefault('method', 'POST')
        req = self.RequestClass.blank(url, POST=POST, **kw)
        return self(req)

    def request(self, url, **kw):
        """Run a request on this application, returning a Response.

        This can be used for DELETE, PUT, etc requests.  E.g.::

            resp = myapp.request('/article/1', method='PUT', body='New article')
        """
        req = self.RequestClass.blank(url, **kw)
        return self(req)

    def call_func(self, req, *args, **kwargs):
        """Call the wrapped function; override this in a subclass to
        change how the function is called."""
        return self.func(req, *args, **kwargs)

    def clone(self, func=None, **kw):
        """Creates a copy/clone of this object, but with some
        parameters rebound
        """
        kwargs = {}
        if func is not None:
            kwargs['func'] = func
        if self.RequestClass is not self.__class__.RequestClass:
            kwargs['RequestClass'] = self.RequestClass
        if self.args:
            kwargs['args'] = self.args
        if self.kwargs:
            kwargs['kwargs'] = self.kwargs
        kwargs.update(kw)
        return self.__class__(**kwargs)

    # To match @decorator:
    @property
    def undecorated(self):
        return self.func

    @classmethod
    def middleware(cls, middle_func=None, app=None, **kw):
        """Creates middleware

        Use this like::

            @wsgify.middleware
            def restrict_ip(app, req, ips):
                if req.remote_addr not in ips:
                    raise webob.exc.HTTPForbidden('Bad IP: %s' % req.remote_addr)
                return app

            @wsgify
            def app(req):
                return 'hi'

            wrapped = restrict_ip(app, ips=['127.0.0.1'])

        Or if you want to write output-rewriting middleware::

            @wsgify.middleware
            def all_caps(app, req):
                resp = req.get_response(app)
                resp.body = resp.body.upper()
                return resp

            wrapped = all_caps(app)

        Note that you must call ``req.get_response(app)`` to get a WebOb
        response object.  If you are not modifying the output, you can just
        return the app.

        As you can see, this method doesn't actually create an application, but
        creates "middleware" that can be bound to an application, along with
        "configuration" (that is, any other keyword arguments you pass when
        binding the application).

        """
        if middle_func is None:
            return _UnboundMiddleware(cls, app, kw)
        if app is None:
            return _MiddlewareFactory(cls, middle_func, kw)
        return cls(middle_func, middleware_wraps=app, kwargs=kw)

class _UnboundMiddleware(object):
    """A `wsgify.middleware` invocation that has not yet wrapped a
    middleware function; the intermediate object when you do
    something like ``@wsgify.middleware(RequestClass=Foo)``
    """

    def __init__(self, wrapper_class, app, kw):
        self.wrapper_class = wrapper_class
        self.app = app
        self.kw = kw

    def __repr__(self):
        return '<%s at %s wrapping %r>' % (self.__class__.__name__,
                                           id(self), self.app)

    def __call__(self, func, app=None):
        if app is None:
            app = self.app
        return self.wrapper_class.middleware(func, app=app, **self.kw)

class _MiddlewareFactory(object):
    """A middleware that has not yet been bound to an application or
    configured.
    """

    def __init__(self, wrapper_class, middleware, kw):
        self.wrapper_class = wrapper_class
        self.middleware = middleware
        self.kw = kw

    def __repr__(self):
        return '<%s at %s wrapping %r>' % (self.__class__.__name__, id(self),
                                           self.middleware)

    def __call__(self, app, **config):
        kw = self.kw.copy()
        kw.update(config)
        return self.wrapper_class.middleware(self.middleware, app, **kw)

########NEW FILE########
__FILENAME__ = descriptors
from datetime import (
    date,
    datetime,
    )

import re

from webob.byterange import (
    ContentRange,
    Range,
    )

from webob.compat import (
    PY3,
    text_type,
    )

from webob.datetime_utils import (
    parse_date,
    serialize_date,
    )

from webob.util import (
    header_docstring,
    warn_deprecation,
    )


CHARSET_RE = re.compile(r';\s*charset=([^;]*)', re.I)
SCHEME_RE = re.compile(r'^[a-z]+:', re.I)


_not_given = object()

def environ_getter(key, default=_not_given, rfc_section=None):
    if rfc_section:
        doc = header_docstring(key, rfc_section)
    else:
        doc = "Gets and sets the ``%s`` key in the environment." % key
    if default is _not_given:
        def fget(req):
            return req.environ[key]
        def fset(req, val):
            req.environ[key] = val
        fdel = None
    else:
        def fget(req):
            return req.environ.get(key, default)
        def fset(req, val):
            if val is None:
                if key in req.environ:
                    del req.environ[key]
            else:
                req.environ[key] = val
        def fdel(req):
            del req.environ[key]
    return property(fget, fset, fdel, doc=doc)


def environ_decoder(key, default=_not_given, rfc_section=None,
                    encattr=None):
    if rfc_section:
        doc = header_docstring(key, rfc_section)
    else:
        doc = "Gets and sets the ``%s`` key in the environment." % key
    if default is _not_given:
        def fget(req):
            return req.encget(key, encattr=encattr)
        def fset(req, val):
            return req.encset(key, val, encattr=encattr)
        fdel = None
    else:
        def fget(req):
            return req.encget(key, default, encattr=encattr)
        def fset(req, val):
            if val is None:
                if key in req.environ:
                    del req.environ[key]
            else:
                return req.encset(key, val, encattr=encattr)
        def fdel(req):
            del req.environ[key]
    return property(fget, fset, fdel, doc=doc)

def upath_property(key):
    if PY3: # pragma: no cover
        def fget(req):
            encoding = req.url_encoding
            return req.environ.get(key, '').encode('latin-1').decode(encoding)
        def fset(req, val):
            encoding = req.url_encoding
            req.environ[key] = val.encode(encoding).decode('latin-1')
    else:
        def fget(req):
            encoding = req.url_encoding
            return req.environ.get(key, '').decode(encoding)
        def fset(req, val):
            encoding = req.url_encoding
            if isinstance(val, text_type):
                val = val.encode(encoding)
            req.environ[key] = val
    return property(fget, fset, doc='upath_property(%r)' % key)


def deprecated_property(attr, name, text, version): # pragma: no cover
    """
    Wraps a descriptor, with a deprecation warning or error
    """
    def warn():
        warn_deprecation('The attribute %s is deprecated: %s'
            % (attr, text),
            version,
            3
        )
    def fget(self):
        warn()
        return attr.__get__(self, type(self))
    def fset(self, val):
        warn()
        attr.__set__(self, val)
    def fdel(self):
        warn()
        attr.__delete__(self)
    return property(fget, fset, fdel,
        '<Deprecated attribute %s>' % attr
    )


def header_getter(header, rfc_section):
    doc = header_docstring(header, rfc_section)
    key = header.lower()

    def fget(r):
        for k, v in r._headerlist:
            if k.lower() == key:
                return v

    def fset(r, value):
        fdel(r)
        if value is not None:
            if isinstance(value, text_type) and not PY3:
                value = value.encode('latin-1')
            r._headerlist.append((header, value))

    def fdel(r):
        items = r._headerlist
        for i in range(len(items)-1, -1, -1):
            if items[i][0].lower() == key:
                del items[i]

    return property(fget, fset, fdel, doc)




def converter(prop, parse, serialize, convert_name=None):
    assert isinstance(prop, property)
    convert_name = convert_name or "``%s`` and ``%s``" % (parse.__name__,
                                                  serialize.__name__)
    doc = prop.__doc__ or ''
    doc += "  Converts it using %s." % convert_name
    hget, hset = prop.fget, prop.fset
    def fget(r):
        return parse(hget(r))
    def fset(r, val):
        if val is not None:
            val = serialize(val)
        hset(r, val)
    return property(fget, fset, prop.fdel, doc)



def list_header(header, rfc_section):
    prop = header_getter(header, rfc_section)
    return converter(prop, parse_list, serialize_list, 'list')

def parse_list(value):
    if not value:
        return None
    return tuple(filter(None, [v.strip() for v in value.split(',')]))

def serialize_list(value):
    if isinstance(value, (text_type, bytes)):
        return str(value)
    else:
        return ', '.join(map(str, value))




def converter_date(prop):
    return converter(prop, parse_date, serialize_date, 'HTTP date')

def date_header(header, rfc_section):
    return converter_date(header_getter(header, rfc_section))









########################
## Converter functions
########################


_rx_etag = re.compile(r'(?:^|\s)(W/)?"((?:\\"|.)*?)"')

def parse_etag_response(value, strong=False):
    """
    Parse a response ETag.
    See:
        * http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.19
        * http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.11
    """
    if not value:
        return None
    m = _rx_etag.match(value)
    if not m:
        # this etag is invalid, but we'll just return it anyway
        return value
    elif strong and m.group(1):
        # this is a weak etag and we want only strong ones
        return None
    else:
        return m.group(2).replace('\\"', '"')

def serialize_etag_response(value): #return '"%s"' % value.replace('"', '\\"')
    strong = True
    if isinstance(value, tuple):
        value, strong = value
    elif _rx_etag.match(value):
        # this is a valid etag already
        return value
    # let's quote the value
    r = '"%s"' % value.replace('"', '\\"')
    if not strong:
        r = 'W/' + r
    return r

def serialize_if_range(value):
    if isinstance(value, (datetime, date)):
        return serialize_date(value)
    value = str(value)
    return value or None

def parse_range(value):
    if not value:
        return None
    # Might return None too:
    return Range.parse(value)

def serialize_range(value):
    if not value:
        return None
    elif isinstance(value, (list, tuple)):
        return str(Range(*value))
    else:
        assert isinstance(value, str)
        return value

def parse_int(value):
    if value is None or value == '':
        return None
    return int(value)

def parse_int_safe(value):
    if value is None or value == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None

serialize_int = str

def parse_content_range(value):
    if not value or not value.strip():
        return None
    # May still return None
    return ContentRange.parse(value)

def serialize_content_range(value):
    if isinstance(value, (tuple, list)):
        if len(value) not in (2, 3):
            raise ValueError(
                "When setting content_range to a list/tuple, it must "
                "be length 2 or 3 (not %r)" % value)
        if len(value) == 2:
            begin, end = value
            length = None
        else:
            begin, end, length = value
        value = ContentRange(begin, end, length)
    value = str(value).strip()
    if not value:
        return None
    return value




_rx_auth_param = re.compile(r'([a-z]+)=(".*?"|[^,]*)(?:\Z|, *)')

def parse_auth_params(params):
    r = {}
    for k, v in _rx_auth_param.findall(params):
        r[k] = v.strip('"')
    return r

# see http://lists.w3.org/Archives/Public/ietf-http-wg/2009OctDec/0297.html
known_auth_schemes = ['Basic', 'Digest', 'WSSE', 'HMACDigest', 'GoogleLogin',
                      'Cookie', 'OpenID']
known_auth_schemes = dict.fromkeys(known_auth_schemes, None)

def parse_auth(val):
    if val is not None:
        authtype, params = val.split(' ', 1)
        if authtype in known_auth_schemes:
            if authtype == 'Basic' and '"' not in params:
                # this is the "Authentication: Basic XXXXX==" case
                pass
            else:
                params = parse_auth_params(params)
        return authtype, params
    return val

def serialize_auth(val):
    if isinstance(val, (tuple, list)):
        authtype, params = val
        if isinstance(params, dict):
            params = ', '.join(map('%s="%s"'.__mod__, params.items()))
        assert isinstance(params, str)
        return '%s %s' % (authtype, params)
    return val

########NEW FILE########
__FILENAME__ = etag
"""
Does parsing of ETag-related headers: If-None-Matches, If-Matches

Also If-Range parsing
"""

from webob.datetime_utils import (
    parse_date,
    serialize_date,
    )
from webob.descriptors import _rx_etag

from webob.util import (
    header_docstring,
    warn_deprecation,
    )

__all__ = ['AnyETag', 'NoETag', 'ETagMatcher', 'IfRange', 'etag_property']

def etag_property(key, default, rfc_section, strong=True):
    doc = header_docstring(key, rfc_section)
    doc += "  Converts it as a Etag."
    def fget(req):
        value = req.environ.get(key)
        if not value:
            return default
        else:
            return ETagMatcher.parse(value, strong=strong)
    def fset(req, val):
        if val is None:
            req.environ[key] = None
        else:
            req.environ[key] = str(val)
    def fdel(req):
        del req.environ[key]
    return property(fget, fset, fdel, doc=doc)

def _warn_weak_match_deprecated():
    warn_deprecation("weak_match is deprecated", '1.2', 3)

def _warn_if_range_match_deprecated(*args, **kw): # pragma: no cover
    raise DeprecationWarning("IfRange.match[_response] API is deprecated")


class _AnyETag(object):
    """
    Represents an ETag of *, or a missing ETag when matching is 'safe'
    """

    def __repr__(self):
        return '<ETag *>'

    def __nonzero__(self):
        return False

    __bool__ = __nonzero__ # python 3

    def __contains__(self, other):
        return True

    def weak_match(self, other):
        _warn_weak_match_deprecated()

    def __str__(self):
        return '*'

AnyETag = _AnyETag()

class _NoETag(object):
    """
    Represents a missing ETag when matching is unsafe
    """

    def __repr__(self):
        return '<No ETag>'

    def __nonzero__(self):
        return False

    __bool__ = __nonzero__ # python 3

    def __contains__(self, other):
        return False

    def weak_match(self, other): # pragma: no cover
        _warn_weak_match_deprecated()

    def __str__(self):
        return ''

NoETag = _NoETag()


# TODO: convert into a simple tuple

class ETagMatcher(object):
    def __init__(self, etags):
        self.etags = etags

    def __contains__(self, other):
        return other in self.etags

    def weak_match(self, other): # pragma: no cover
        _warn_weak_match_deprecated()

    def __repr__(self):
        return '<ETag %s>' % (' or '.join(self.etags))

    @classmethod
    def parse(cls, value, strong=True):
        """
        Parse this from a header value
        """
        if value == '*':
            return AnyETag
        if not value:
            return cls([])
        matches = _rx_etag.findall(value)
        if not matches:
            return cls([value])
        elif strong:
            return cls([t for w,t in matches if not w])
        else:
            return cls([t for w,t in matches])

    def __str__(self):
        return ', '.join(map('"%s"'.__mod__, self.etags))


class IfRange(object):
    def __init__(self, etag):
        self.etag = etag

    @classmethod
    def parse(cls, value):
        """
        Parse this from a header value.
        """
        if not value:
            return cls(AnyETag)
        elif value.endswith(' GMT'):
            # Must be a date
            return IfRangeDate(parse_date(value))
        else:
            return cls(ETagMatcher.parse(value))

    def __contains__(self, resp):
        """
        Return True if the If-Range header matches the given etag or last_modified
        """
        return resp.etag_strong in self.etag

    def __nonzero__(self):
        return bool(self.etag)

    def __repr__(self):
        return '%s(%r)' % (
            self.__class__.__name__,
            self.etag
        )

    def __str__(self):
        return str(self.etag) if self.etag else ''

    match = match_response = _warn_if_range_match_deprecated

    __bool__ = __nonzero__ # python 3

class IfRangeDate(object):
    def __init__(self, date):
        self.date = date

    def __contains__(self, resp):
        last_modified = resp.last_modified
        #if isinstance(last_modified, str):
        #    last_modified = parse_date(last_modified)
        return last_modified and (last_modified <= self.date)

    def __repr__(self):
        return '%s(%r)' % (
            self.__class__.__name__,
            self.date
            #serialize_date(self.date)
        )

    def __str__(self):
        return serialize_date(self.date)

    match = match_response = _warn_if_range_match_deprecated

########NEW FILE########
__FILENAME__ = exc
"""
HTTP Exception
--------------
This module processes Python exceptions that relate to HTTP exceptions
by defining a set of exceptions, all subclasses of HTTPException.
Each exception, in addition to being a Python exception that can be
raised and caught, is also a WSGI application and ``webob.Response``
object.

This module defines exceptions according to RFC 2068 [1]_ : codes with
100-300 are not really errors; 400's are client errors, and 500's are
server errors.  According to the WSGI specification [2]_ , the application
can call ``start_response`` more then once only under two conditions:
(a) the response has not yet been sent, or (b) if the second and
subsequent invocations of ``start_response`` have a valid ``exc_info``
argument obtained from ``sys.exc_info()``.  The WSGI specification then
requires the server or gateway to handle the case where content has been
sent and then an exception was encountered.

Exception
  HTTPException
    HTTPOk
      * 200 - HTTPOk
      * 201 - HTTPCreated
      * 202 - HTTPAccepted
      * 203 - HTTPNonAuthoritativeInformation
      * 204 - HTTPNoContent
      * 205 - HTTPResetContent
      * 206 - HTTPPartialContent
    HTTPRedirection
      * 300 - HTTPMultipleChoices
      * 301 - HTTPMovedPermanently
      * 302 - HTTPFound
      * 303 - HTTPSeeOther
      * 304 - HTTPNotModified
      * 305 - HTTPUseProxy
      * 306 - Unused (not implemented, obviously)
      * 307 - HTTPTemporaryRedirect
    HTTPError
      HTTPClientError
        * 400 - HTTPBadRequest
        * 401 - HTTPUnauthorized
        * 402 - HTTPPaymentRequired
        * 403 - HTTPForbidden
        * 404 - HTTPNotFound
        * 405 - HTTPMethodNotAllowed
        * 406 - HTTPNotAcceptable
        * 407 - HTTPProxyAuthenticationRequired
        * 408 - HTTPRequestTimeout
        * 409 - HTTPConflict
        * 410 - HTTPGone
        * 411 - HTTPLengthRequired
        * 412 - HTTPPreconditionFailed
        * 413 - HTTPRequestEntityTooLarge
        * 414 - HTTPRequestURITooLong
        * 415 - HTTPUnsupportedMediaType
        * 416 - HTTPRequestRangeNotSatisfiable
        * 417 - HTTPExpectationFailed
        * 428 - HTTPPreconditionRequired
        * 429 - HTTPTooManyRequests
        * 431 - HTTPRequestHeaderFieldsTooLarge
      HTTPServerError
        * 500 - HTTPInternalServerError
        * 501 - HTTPNotImplemented
        * 502 - HTTPBadGateway
        * 503 - HTTPServiceUnavailable
        * 504 - HTTPGatewayTimeout
        * 505 - HTTPVersionNotSupported
        * 511 - HTTPNetworkAuthenticationRequired

Subclass usage notes:
---------------------

The HTTPException class is complicated by 4 factors:

  1. The content given to the exception may either be plain-text or
     as html-text.

  2. The template may want to have string-substitutions taken from
     the current ``environ`` or values from incoming headers. This
     is especially troublesome due to case sensitivity.

  3. The final output may either be text/plain or text/html
     mime-type as requested by the client application.

  4. Each exception has a default explanation, but those who
     raise exceptions may want to provide additional detail.

Subclass attributes and call parameters are designed to provide an easier path
through the complications.

Attributes:

   ``code``
       the HTTP status code for the exception

   ``title``
       remainder of the status line (stuff after the code)

   ``explanation``
       a plain-text explanation of the error message that is
       not subject to environment or header substitutions;
       it is accessible in the template via %(explanation)s

   ``detail``
       a plain-text message customization that is not subject
       to environment or header substitutions; accessible in
       the template via %(detail)s

   ``body_template``
       a content fragment (in HTML) used for environment and
       header substitution; the default template includes both
       the explanation and further detail provided in the
       message

Parameters:

   ``detail``
     a plain-text override of the default ``detail``

   ``headers``
     a list of (k,v) header pairs

   ``comment``
     a plain-text additional information which is
     usually stripped/hidden for end-users

   ``body_template``
     a string.Template object containing a content fragment in HTML
     that frames the explanation and further detail

To override the template (which is HTML content) or the plain-text
explanation, one must subclass the given exception; or customize it
after it has been created.  This particular breakdown of a message
into explanation, detail and template allows both the creation of
plain-text and html messages for various clients as well as
error-free substitution of environment variables and headers.


The subclasses of :class:`~_HTTPMove`
(:class:`~HTTPMultipleChoices`, :class:`~HTTPMovedPermanently`,
:class:`~HTTPFound`, :class:`~HTTPSeeOther`, :class:`~HTTPUseProxy` and
:class:`~HTTPTemporaryRedirect`) are redirections that require a ``Location``
field. Reflecting this, these subclasses have two additional keyword arguments:
``location`` and ``add_slash``.

Parameters:

    ``location``
      to set the location immediately

    ``add_slash``
      set to True to redirect to the same URL as the request, except with a
      ``/`` appended

Relative URLs in the location will be resolved to absolute.

References:

.. [1] http://www.python.org/peps/pep-0333.html#error-handling
.. [2] http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.5


"""

from string import Template
import re
import sys

from webob.compat import (
    class_types,
    text_,
    text_type,
    urlparse,
    )
from webob.request import Request
from webob.response import Response
from webob.util import (
    html_escape,
    warn_deprecation,
    )

tag_re = re.compile(r'<.*?>', re.S)
br_re = re.compile(r'<br.*?>', re.I|re.S)
comment_re = re.compile(r'<!--|-->')

def no_escape(value):
    if value is None:
        return ''
    if not isinstance(value, text_type):
        if hasattr(value, '__unicode__'):
            value = value.__unicode__()
        if isinstance(value, bytes):
            value = text_(value, 'utf-8')
        else:
            value = text_type(value)
    return value

def strip_tags(value):
    value = value.replace('\n', ' ')
    value = value.replace('\r', '')
    value = br_re.sub('\n', value)
    value = comment_re.sub('', value)
    value = tag_re.sub('', value)
    return value

class HTTPException(Exception):
    def __init__(self, message, wsgi_response):
        Exception.__init__(self, message)
        self.wsgi_response = wsgi_response

    def __call__(self, environ, start_response):
        return self.wsgi_response(environ, start_response)

class WSGIHTTPException(Response, HTTPException):

    ## You should set in subclasses:
    # code = 200
    # title = 'OK'
    # explanation = 'why this happens'
    # body_template_obj = Template('response template')
    code = None
    title = None
    explanation = ''
    body_template_obj = Template('''\
${explanation}<br /><br />
${detail}
${html_comment}
''')

    plain_template_obj = Template('''\
${status}

${body}''')

    html_template_obj = Template('''\
<html>
 <head>
  <title>${status}</title>
 </head>
 <body>
  <h1>${status}</h1>
  ${body}
 </body>
</html>''')

    ## Set this to True for responses that should have no request body
    empty_body = False

    def __init__(self, detail=None, headers=None, comment=None,
                 body_template=None, **kw):
        Response.__init__(self,
                          status='%s %s' % (self.code, self.title),
                          **kw)
        Exception.__init__(self, detail)
        if headers:
            self.headers.extend(headers)
        self.detail = detail
        self.comment = comment
        if body_template is not None:
            self.body_template = body_template
            self.body_template_obj = Template(body_template)
        if self.empty_body:
            del self.content_type
            del self.content_length

    def __str__(self):
        return self.detail or self.explanation

    def _make_body(self, environ, escape):
        args = {
            'explanation': escape(self.explanation),
            'detail': escape(self.detail or ''),
            'comment': escape(self.comment or ''),
            }
        if self.comment:
            args['html_comment'] = '<!-- %s -->' % escape(self.comment)
        else:
            args['html_comment'] = ''
        if WSGIHTTPException.body_template_obj is not self.body_template_obj:
            # Custom template; add headers to args
            for k, v in environ.items():
                args[k] = escape(v)
            for k, v in self.headers.items():
                args[k.lower()] = escape(v)
        t_obj = self.body_template_obj
        return t_obj.substitute(args)

    def plain_body(self, environ):
        body = self._make_body(environ, no_escape)
        body = strip_tags(body)
        return self.plain_template_obj.substitute(status=self.status,
                                                  title=self.title,
                                                  body=body)

    def html_body(self, environ):
        body = self._make_body(environ, html_escape)
        return self.html_template_obj.substitute(status=self.status,
                                                 body=body)

    def generate_response(self, environ, start_response):
        if self.content_length is not None:
            del self.content_length
        headerlist = list(self.headerlist)
        accept = environ.get('HTTP_ACCEPT', '')
        if accept and 'html' in accept or '*/*' in accept:
            content_type = 'text/html'
            body = self.html_body(environ)
        else:
            content_type = 'text/plain'
            body = self.plain_body(environ)
        extra_kw = {}
        if isinstance(body, text_type):
            extra_kw.update(charset='utf-8')
        resp = Response(body,
            status=self.status,
            headerlist=headerlist,
            content_type=content_type,
            **extra_kw
        )
        resp.content_type = content_type
        return resp(environ, start_response)

    def __call__(self, environ, start_response):
        is_head = environ['REQUEST_METHOD'] == 'HEAD'
        if self.body or self.empty_body or is_head:
            app_iter = Response.__call__(self, environ, start_response)
        else:
            app_iter = self.generate_response(environ, start_response)
        if is_head:
            app_iter = []
        return app_iter

    @property
    def wsgi_response(self):
        return self



class HTTPError(WSGIHTTPException):
    """
    base class for status codes in the 400's and 500's

    This is an exception which indicates that an error has occurred,
    and that any work in progress should not be committed.  These are
    typically results in the 400's and 500's.
    """

class HTTPRedirection(WSGIHTTPException):
    """
    base class for 300's status code (redirections)

    This is an abstract base class for 3xx redirection.  It indicates
    that further action needs to be taken by the user agent in order
    to fulfill the request.  It does not necessarly signal an error
    condition.
    """

class HTTPOk(WSGIHTTPException):
    """
    Base class for the 200's status code (successful responses)

    code: 200, title: OK
    """
    code = 200
    title = 'OK'

############################################################
## 2xx success
############################################################

class HTTPCreated(HTTPOk):
    """
    subclass of :class:`~HTTPOk`

    This indicates that request has been fulfilled and resulted in a new
    resource being created.

    code: 201, title: Created
    """
    code = 201
    title = 'Created'

class HTTPAccepted(HTTPOk):
    """
    subclass of :class:`~HTTPOk`

    This indicates that the request has been accepted for processing, but the
    processing has not been completed.

    code: 202, title: Accepted
    """
    code = 202
    title = 'Accepted'
    explanation = 'The request is accepted for processing.'

class HTTPNonAuthoritativeInformation(HTTPOk):
    """
    subclass of :class:`~HTTPOk`

    This indicates that the returned metainformation in the entity-header is
    not the definitive set as available from the origin server, but is
    gathered from a local or a third-party copy.

    code: 203, title: Non-Authoritative Information
    """
    code = 203
    title = 'Non-Authoritative Information'

class HTTPNoContent(HTTPOk):
    """
    subclass of :class:`~HTTPOk`

    This indicates that the server has fulfilled the request but does
    not need to return an entity-body, and might want to return updated
    metainformation.

    code: 204, title: No Content
    """
    code = 204
    title = 'No Content'
    empty_body = True

class HTTPResetContent(HTTPOk):
    """
    subclass of :class:`~HTTPOk`

    This indicates that the the server has fulfilled the request and
    the user agent SHOULD reset the document view which caused the
    request to be sent.

    code: 205, title: Reset Content
    """
    code = 205
    title = 'Reset Content'
    empty_body = True

class HTTPPartialContent(HTTPOk):
    """
    subclass of :class:`~HTTPOk`

    This indicates that the server has fulfilled the partial GET
    request for the resource.

    code: 206, title: Partial Content
    """
    code = 206
    title = 'Partial Content'

############################################################
## 3xx redirection
############################################################

class _HTTPMove(HTTPRedirection):
    """
    redirections which require a Location field

    Since a 'Location' header is a required attribute of 301, 302, 303,
    305 and 307 (but not 304), this base class provides the mechanics to
    make this easy.

    You can provide a location keyword argument to set the location
    immediately.  You may also give ``add_slash=True`` if you want to
    redirect to the same URL as the request, except with a ``/`` added
    to the end.

    Relative URLs in the location will be resolved to absolute.
    """
    explanation = 'The resource has been moved to'
    body_template_obj = Template('''\
${explanation} <a href="${location}">${location}</a>;
you should be redirected automatically.
${detail}
${html_comment}''')

    def __init__(self, detail=None, headers=None, comment=None,
                 body_template=None, location=None, add_slash=False):
        super(_HTTPMove, self).__init__(
            detail=detail, headers=headers, comment=comment,
            body_template=body_template)
        if location is not None:
            self.location = location
            if add_slash:
                raise TypeError(
                    "You can only provide one of the arguments location "
                    "and add_slash")
        self.add_slash = add_slash

    def __call__(self, environ, start_response):
        req = Request(environ)
        if self.add_slash:
            url = req.path_url
            url += '/'
            if req.environ.get('QUERY_STRING'):
                url += '?' + req.environ['QUERY_STRING']
            self.location = url
        self.location = urlparse.urljoin(req.path_url, self.location)
        return super(_HTTPMove, self).__call__(
            environ, start_response)

class HTTPMultipleChoices(_HTTPMove):
    """
    subclass of :class:`~_HTTPMove`

    This indicates that the requested resource corresponds to any one
    of a set of representations, each with its own specific location,
    and agent-driven negotiation information is being provided so that
    the user can select a preferred representation and redirect its
    request to that location.

    code: 300, title: Multiple Choices
    """
    code = 300
    title = 'Multiple Choices'

class HTTPMovedPermanently(_HTTPMove):
    """
    subclass of :class:`~_HTTPMove`

    This indicates that the requested resource has been assigned a new
    permanent URI and any future references to this resource SHOULD use
    one of the returned URIs.

    code: 301, title: Moved Permanently
    """
    code = 301
    title = 'Moved Permanently'

class HTTPFound(_HTTPMove):
    """
    subclass of :class:`~_HTTPMove`

    This indicates that the requested resource resides temporarily under
    a different URI.

    code: 302, title: Found
    """
    code = 302
    title = 'Found'
    explanation = 'The resource was found at'

# This one is safe after a POST (the redirected location will be
# retrieved with GET):
class HTTPSeeOther(_HTTPMove):
    """
    subclass of :class:`~_HTTPMove`

    This indicates that the response to the request can be found under
    a different URI and SHOULD be retrieved using a GET method on that
    resource.

    code: 303, title: See Other
    """
    code = 303
    title = 'See Other'

class HTTPNotModified(HTTPRedirection):
    """
    subclass of :class:`~HTTPRedirection`

    This indicates that if the client has performed a conditional GET
    request and access is allowed, but the document has not been
    modified, the server SHOULD respond with this status code.

    code: 304, title: Not Modified
    """
    # TODO: this should include a date or etag header
    code = 304
    title = 'Not Modified'
    empty_body = True

class HTTPUseProxy(_HTTPMove):
    """
    subclass of :class:`~_HTTPMove`

    This indicates that the requested resource MUST be accessed through
    the proxy given by the Location field.

    code: 305, title: Use Proxy
    """
    # Not a move, but looks a little like one
    code = 305
    title = 'Use Proxy'
    explanation = (
        'The resource must be accessed through a proxy located at')

class HTTPTemporaryRedirect(_HTTPMove):
    """
    subclass of :class:`~_HTTPMove`

    This indicates that the requested resource resides temporarily
    under a different URI.

    code: 307, title: Temporary Redirect
    """
    code = 307
    title = 'Temporary Redirect'

############################################################
## 4xx client error
############################################################

class HTTPClientError(HTTPError):
    """
    base class for the 400's, where the client is in error

    This is an error condition in which the client is presumed to be
    in-error.  This is an expected problem, and thus is not considered
    a bug.  A server-side traceback is not warranted.  Unless specialized,
    this is a '400 Bad Request'
    """
    code = 400
    title = 'Bad Request'
    explanation = ('The server could not comply with the request since\r\n'
                   'it is either malformed or otherwise incorrect.\r\n')

class HTTPBadRequest(HTTPClientError):
    pass

class HTTPUnauthorized(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the request requires user authentication.

    code: 401, title: Unauthorized
    """
    code = 401
    title = 'Unauthorized'
    explanation = (
        'This server could not verify that you are authorized to\r\n'
        'access the document you requested.  Either you supplied the\r\n'
        'wrong credentials (e.g., bad password), or your browser\r\n'
        'does not understand how to supply the credentials required.\r\n')

class HTTPPaymentRequired(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    code: 402, title: Payment Required
    """
    code = 402
    title = 'Payment Required'
    explanation = ('Access was denied for financial reasons.')

class HTTPForbidden(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server understood the request, but is
    refusing to fulfill it.

    code: 403, title: Forbidden
    """
    code = 403
    title = 'Forbidden'
    explanation = ('Access was denied to this resource.')

class HTTPNotFound(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server did not find anything matching the
    Request-URI.

    code: 404, title: Not Found
    """
    code = 404
    title = 'Not Found'
    explanation = ('The resource could not be found.')

class HTTPMethodNotAllowed(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the method specified in the Request-Line is
    not allowed for the resource identified by the Request-URI.

    code: 405, title: Method Not Allowed
    """
    code = 405
    title = 'Method Not Allowed'
    # override template since we need an environment variable
    body_template_obj = Template('''\
The method ${REQUEST_METHOD} is not allowed for this resource. <br /><br />
${detail}''')

class HTTPNotAcceptable(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates the resource identified by the request is only
    capable of generating response entities which have content
    characteristics not acceptable according to the accept headers
    sent in the request.

    code: 406, title: Not Acceptable
    """
    code = 406
    title = 'Not Acceptable'
    # override template since we need an environment variable
    template = Template('''\
The resource could not be generated that was acceptable to your browser
(content of type ${HTTP_ACCEPT}. <br /><br />
${detail}''')

class HTTPProxyAuthenticationRequired(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This is similar to 401, but indicates that the client must first
    authenticate itself with the proxy.

    code: 407, title: Proxy Authentication Required
    """
    code = 407
    title = 'Proxy Authentication Required'
    explanation = ('Authentication with a local proxy is needed.')

class HTTPRequestTimeout(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the client did not produce a request within
    the time that the server was prepared to wait.

    code: 408, title: Request Timeout
    """
    code = 408
    title = 'Request Timeout'
    explanation = ('The server has waited too long for the request to '
                   'be sent by the client.')

class HTTPConflict(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the request could not be completed due to a
    conflict with the current state of the resource.

    code: 409, title: Conflict
    """
    code = 409
    title = 'Conflict'
    explanation = ('There was a conflict when trying to complete '
                   'your request.')

class HTTPGone(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the requested resource is no longer available
    at the server and no forwarding address is known.

    code: 410, title: Gone
    """
    code = 410
    title = 'Gone'
    explanation = ('This resource is no longer available.  No forwarding '
                   'address is given.')

class HTTPLengthRequired(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the the server refuses to accept the request
    without a defined Content-Length.

    code: 411, title: Length Required
    """
    code = 411
    title = 'Length Required'
    explanation = ('Content-Length header required.')

class HTTPPreconditionFailed(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the precondition given in one or more of the
    request-header fields evaluated to false when it was tested on the
    server.

    code: 412, title: Precondition Failed
    """
    code = 412
    title = 'Precondition Failed'
    explanation = ('Request precondition failed.')

class HTTPRequestEntityTooLarge(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server is refusing to process a request
    because the request entity is larger than the server is willing or
    able to process.

    code: 413, title: Request Entity Too Large
    """
    code = 413
    title = 'Request Entity Too Large'
    explanation = ('The body of your request was too large for this server.')

class HTTPRequestURITooLong(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server is refusing to service the request
    because the Request-URI is longer than the server is willing to
    interpret.

    code: 414, title: Request-URI Too Long
    """
    code = 414
    title = 'Request-URI Too Long'
    explanation = ('The request URI was too long for this server.')

class HTTPUnsupportedMediaType(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server is refusing to service the request
    because the entity of the request is in a format not supported by
    the requested resource for the requested method.

    code: 415, title: Unsupported Media Type
    """
    code = 415
    title = 'Unsupported Media Type'
    # override template since we need an environment variable
    template_obj = Template('''\
The request media type ${CONTENT_TYPE} is not supported by this server.
<br /><br />
${detail}''')

class HTTPRequestRangeNotSatisfiable(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    The server SHOULD return a response with this status code if a
    request included a Range request-header field, and none of the
    range-specifier values in this field overlap the current extent
    of the selected resource, and the request did not include an
    If-Range request-header field.

    code: 416, title: Request Range Not Satisfiable
    """
    code = 416
    title = 'Request Range Not Satisfiable'
    explanation = ('The Range requested is not available.')

class HTTPExpectationFailed(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indidcates that the expectation given in an Expect
    request-header field could not be met by this server.

    code: 417, title: Expectation Failed
    """
    code = 417
    title = 'Expectation Failed'
    explanation = ('Expectation failed.')

class HTTPUnprocessableEntity(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server is unable to process the contained
    instructions. Only for WebDAV.

    code: 422, title: Unprocessable Entity
    """
    ## Note: from WebDAV
    code = 422
    title = 'Unprocessable Entity'
    explanation = 'Unable to process the contained instructions'

class HTTPLocked(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the resource is locked. Only for WebDAV

    code: 423, title: Locked
    """
    ## Note: from WebDAV
    code = 423
    title = 'Locked'
    explanation = ('The resource is locked')

class HTTPFailedDependency(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the method could not be performed because the
    requested action depended on another action and that action failed.
    Only for WebDAV.

    code: 424, title: Failed Dependency
    """
    ## Note: from WebDAV
    code = 424
    title = 'Failed Dependency'
    explanation = (
        'The method could not be performed because the requested '
        'action dependended on another action and that action failed')

class HTTPPreconditionRequired(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the origin server requires the request to be
    conditional.  From RFC 6585, "Additional HTTP Status Codes".

    code: 428, title: Precondition Required
    """
    code = 428
    title = 'Precondition Required'
    explanation = ('This request is required to be conditional')

class HTTPTooManyRequests(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the client has sent too many requests in a
    given amount of time.  Useful for rate limiting.

    From RFC 6585, "Additional HTTP Status Codes".

    code: 429, title: Too Many Requests
    """
    code = 429
    title = 'Too Many Requests'
    explanation = (
        'The client has sent too many requests in a given amount of time')

class HTTPRequestHeaderFieldsTooLarge(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server is unwilling to process the request
    because its header fields are too large. The request may be resubmitted
    after reducing the size of the request header fields.

    From RFC 6585, "Additional HTTP Status Codes".

    code: 431, title: Request Header Fields Too Large
    """
    code = 431
    title = 'Request Header Fields Too Large'
    explanation = (
        'The request header fields were too large')

class HTTPUnavailableForLegalReasons(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server is unable to process the request
    because of legal reasons, e.g. censorship or government-mandated
    blocked access.

    From the draft "A New HTTP Status Code for Legally-restricted Resources"
    by Tim Bray:

    http://tools.ietf.org/html/draft-tbray-http-legally-restricted-status-00

    code: 451, title: Unavailable For Legal Reasons
    """
    code = 451
    title = 'Unavailable For Legal Reasons'
    explanation = ('The resource is not available due to legal reasons.')

############################################################
## 5xx Server Error
############################################################
#  Response status codes beginning with the digit "5" indicate cases in
#  which the server is aware that it has erred or is incapable of
#  performing the request. Except when responding to a HEAD request, the
#  server SHOULD include an entity containing an explanation of the error
#  situation, and whether it is a temporary or permanent condition. User
#  agents SHOULD display any included entity to the user. These response
#  codes are applicable to any request method.

class HTTPServerError(HTTPError):
    """
    base class for the 500's, where the server is in-error

    This is an error condition in which the server is presumed to be
    in-error.  This is usually unexpected, and thus requires a traceback;
    ideally, opening a support ticket for the customer. Unless specialized,
    this is a '500 Internal Server Error'
    """
    code = 500
    title = 'Internal Server Error'
    explanation = (
      'The server has either erred or is incapable of performing\r\n'
      'the requested operation.\r\n')

class HTTPInternalServerError(HTTPServerError):
    pass

class HTTPNotImplemented(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the server does not support the functionality
    required to fulfill the request.

    code: 501, title: Not Implemented
    """
    code = 501
    title = 'Not Implemented'
    template = Template('''
The request method ${REQUEST_METHOD} is not implemented for this server. <br /><br />
${detail}''')

class HTTPBadGateway(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the server, while acting as a gateway or proxy,
    received an invalid response from the upstream server it accessed
    in attempting to fulfill the request.

    code: 502, title: Bad Gateway
    """
    code = 502
    title = 'Bad Gateway'
    explanation = ('Bad gateway.')

class HTTPServiceUnavailable(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the server is currently unable to handle the
    request due to a temporary overloading or maintenance of the server.

    code: 503, title: Service Unavailable
    """
    code = 503
    title = 'Service Unavailable'
    explanation = ('The server is currently unavailable. '
                   'Please try again at a later time.')

class HTTPGatewayTimeout(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the server, while acting as a gateway or proxy,
    did not receive a timely response from the upstream server specified
    by the URI (e.g. HTTP, FTP, LDAP) or some other auxiliary server
    (e.g. DNS) it needed to access in attempting to complete the request.

    code: 504, title: Gateway Timeout
    """
    code = 504
    title = 'Gateway Timeout'
    explanation = ('The gateway has timed out.')

class HTTPVersionNotSupported(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the server does not support, or refuses to
    support, the HTTP protocol version that was used in the request
    message.

    code: 505, title: HTTP Version Not Supported
    """
    code = 505
    title = 'HTTP Version Not Supported'
    explanation = ('The HTTP version is not supported.')

class HTTPInsufficientStorage(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the server does not have enough space to save
    the resource.

    code: 507, title: Insufficient Storage
    """
    code = 507
    title = 'Insufficient Storage'
    explanation = ('There was not enough space to save the resource')

class HTTPNetworkAuthenticationRequired(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the client needs to authenticate to gain
    network access.  From RFC 6585, "Additional HTTP Status Codes".

    code: 511, title: Network Authentication Required
    """
    code = 511
    title = 'Network Authentication Required'
    explanation = ('Network authentication is required')

class HTTPExceptionMiddleware(object):
    """
    Middleware that catches exceptions in the sub-application.  This
    does not catch exceptions in the app_iter; only during the initial
    calling of the application.

    This should be put *very close* to applications that might raise
    these exceptions.  This should not be applied globally; letting
    *expected* exceptions raise through the WSGI stack is dangerous.
    """

    def __init__(self, application):
        self.application = application
    def __call__(self, environ, start_response):
        try:
            return self.application(environ, start_response)
        except HTTPException:
            parent_exc_info = sys.exc_info()
            def repl_start_response(status, headers, exc_info=None):
                if exc_info is None:
                    exc_info = parent_exc_info
                return start_response(status, headers, exc_info)
            return parent_exc_info[1](environ, repl_start_response)

try:
    from paste import httpexceptions
except ImportError:   # pragma: no cover
    # Without Paste we don't need to do this fixup
    pass
else: # pragma: no cover
    for name in dir(httpexceptions):
        obj = globals().get(name)
        if (obj and isinstance(obj, type) and issubclass(obj, HTTPException)
            and obj is not HTTPException
            and obj is not WSGIHTTPException):
            obj.__bases__ = obj.__bases__ + (getattr(httpexceptions, name),)
    del name, obj, httpexceptions

__all__ = ['HTTPExceptionMiddleware', 'status_map']
status_map={}
for name, value in list(globals().items()):
    if (isinstance(value, (type, class_types)) and
        issubclass(value, HTTPException)
        and not name.startswith('_')):
        __all__.append(name)
        if getattr(value, 'code', None):
            status_map[value.code]=value
        if hasattr(value, 'explanation'):
            value.explanation = ' '.join(value.explanation.strip().split())
del name, value

########NEW FILE########
__FILENAME__ = headers
from collections import MutableMapping
from webob.compat import (
    iteritems_,
    string_types,
    )
from webob.multidict import MultiDict

__all__ = ['ResponseHeaders', 'EnvironHeaders']

class ResponseHeaders(MultiDict):
    """
        Dictionary view on the response headerlist.
        Keys are normalized for case and whitespace.
    """
    def __getitem__(self, key):
        key = key.lower()
        for k, v in reversed(self._items):
            if k.lower() == key:
                return v
        raise KeyError(key)

    def getall(self, key):
        key = key.lower()
        result = []
        for k, v in self._items:
            if k.lower() == key:
                result.append(v)
        return result

    def mixed(self):
        r = self.dict_of_lists()
        for key, val in iteritems_(r):
            if len(val) == 1:
                r[key] = val[0]
        return r

    def dict_of_lists(self):
        r = {}
        for key, val in iteritems_(self):
            r.setdefault(key.lower(), []).append(val)
        return r

    def __setitem__(self, key, value):
        norm_key = key.lower()
        items = self._items
        for i in range(len(items)-1, -1, -1):
            if items[i][0].lower() == norm_key:
                del items[i]
        self._items.append((key, value))

    def __delitem__(self, key):
        key = key.lower()
        items = self._items
        found = False
        for i in range(len(items)-1, -1, -1):
            if items[i][0].lower() == key:
                del items[i]
                found = True
        if not found:
            raise KeyError(key)

    def __contains__(self, key):
        key = key.lower()
        for k, v in self._items:
            if k.lower() == key:
                return True
        return False

    has_key = __contains__

    def setdefault(self, key, default=None):
        c_key = key.lower()
        for k, v in self._items:
            if k.lower() == c_key:
                return v
        self._items.append((key, default))
        return default

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError("pop expected at most 2 arguments, got %s"
                              % repr(1 + len(args)))
        key = key.lower()
        for i in range(len(self._items)):
            if self._items[i][0].lower() == key:
                v = self._items[i][1]
                del self._items[i]
                return v
        if args:
            return args[0]
        else:
            raise KeyError(key)






key2header = {
    'CONTENT_TYPE': 'Content-Type',
    'CONTENT_LENGTH': 'Content-Length',
    'HTTP_CONTENT_TYPE': 'Content_Type',
    'HTTP_CONTENT_LENGTH': 'Content_Length',
}

header2key = dict([(v.upper(),k) for (k,v) in key2header.items()])

def _trans_key(key):
    if not isinstance(key, string_types):
        return None
    elif key in key2header:
        return key2header[key]
    elif key.startswith('HTTP_'):
        return key[5:].replace('_', '-').title()
    else:
        return None

def _trans_name(name):
    name = name.upper()
    if name in header2key:
        return header2key[name]
    return 'HTTP_'+name.replace('-', '_')

class EnvironHeaders(MutableMapping):
    """An object that represents the headers as present in a
    WSGI environment.

    This object is a wrapper (with no internal state) for a WSGI
    request object, representing the CGI-style HTTP_* keys as a
    dictionary.  Because a CGI environment can only hold one value for
    each key, this dictionary is single-valued (unlike outgoing
    headers).
    """

    def __init__(self, environ):
        self.environ = environ

    def __getitem__(self, hname):
        return self.environ[_trans_name(hname)]

    def __setitem__(self, hname, value):
        self.environ[_trans_name(hname)] = value

    def __delitem__(self, hname):
        del self.environ[_trans_name(hname)]

    def keys(self):
        return filter(None, map(_trans_key, self.environ))

    def __contains__(self, hname):
        return _trans_name(hname) in self.environ

    def __len__(self):
        return len(list(self.keys()))

    def __iter__(self):
        for k in self.keys():
            yield k

########NEW FILE########
__FILENAME__ = multidict
# (c) 2005 Ian Bicking and contributors; written for Paste
# (http://pythonpaste.org) Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Gives a multi-value dictionary object (MultiDict) plus several wrappers
"""
from collections import MutableMapping

import binascii
import warnings

from webob.compat import (
    PY3,
    iteritems_,
    itervalues_,
    url_encode,
    )

__all__ = ['MultiDict', 'NestedMultiDict', 'NoVars', 'GetDict']

class MultiDict(MutableMapping):
    """
        An ordered dictionary that can have multiple values for each key.
        Adds the methods getall, getone, mixed and extend and add to the normal
        dictionary interface.
    """

    def __init__(self, *args, **kw):
        if len(args) > 1:
            raise TypeError("MultiDict can only be called with one positional "
                            "argument")
        if args:
            if hasattr(args[0], 'iteritems'):
                items = list(args[0].iteritems())
            elif hasattr(args[0], 'items'):
                items = list(args[0].items())
            else:
                items = list(args[0])
            self._items = items
        else:
            self._items = []
        if kw:
            self._items.extend(kw.items())

    @classmethod
    def view_list(cls, lst):
        """
        Create a dict that is a view on the given list
        """
        if not isinstance(lst, list):
            raise TypeError(
                "%s.view_list(obj) takes only actual list objects, not %r"
                % (cls.__name__, lst))
        obj = cls()
        obj._items = lst
        return obj

    @classmethod
    def from_fieldstorage(cls, fs):
        """
        Create a dict from a cgi.FieldStorage instance
        """
        obj = cls()
        # fs.list can be None when there's nothing to parse
        for field in fs.list or ():
            charset = field.type_options.get('charset', 'utf8')
            transfer_encoding = field.headers.get('Content-Transfer-Encoding', None)
            supported_tranfer_encoding = {
                'base64' : binascii.a2b_base64,
                'quoted-printable' : binascii.a2b_qp
                }
            if PY3: # pragma: no cover
                if charset == 'utf8':
                    decode = lambda b: b
                else:
                    decode = lambda b: b.encode('utf8').decode(charset)
            else:
                decode = lambda b: b.decode(charset)
            if field.filename:
                field.filename = decode(field.filename)
                obj.add(field.name, field)
            else:
                value = field.value
                if transfer_encoding in supported_tranfer_encoding:
                    if PY3: # pragma: no cover
                        # binascii accepts bytes
                        value = value.encode('utf8')
                    value = supported_tranfer_encoding[transfer_encoding](value)
                    if PY3: # pragma: no cover
                        # binascii returns bytes
                        value = value.decode('utf8')
                obj.add(field.name, decode(value))
        return obj

    def __getitem__(self, key):
        for k, v in reversed(self._items):
            if k == key:
                return v
        raise KeyError(key)

    def __setitem__(self, key, value):
        try:
            del self[key]
        except KeyError:
            pass
        self._items.append((key, value))

    def add(self, key, value):
        """
        Add the key and value, not overwriting any previous value.
        """
        self._items.append((key, value))

    def getall(self, key):
        """
        Return a list of all values matching the key (may be an empty list)
        """
        return [v for k, v in self._items if k == key]

    def getone(self, key):
        """
        Get one value matching the key, raising a KeyError if multiple
        values were found.
        """
        v = self.getall(key)
        if not v:
            raise KeyError('Key not found: %r' % key)
        if len(v) > 1:
            raise KeyError('Multiple values match %r: %r' % (key, v))
        return v[0]

    def mixed(self):
        """
        Returns a dictionary where the values are either single
        values, or a list of values when a key/value appears more than
        once in this dictionary.  This is similar to the kind of
        dictionary often used to represent the variables in a web
        request.
        """
        result = {}
        multi = {}
        for key, value in self.items():
            if key in result:
                # We do this to not clobber any lists that are
                # *actual* values in this dictionary:
                if key in multi:
                    result[key].append(value)
                else:
                    result[key] = [result[key], value]
                    multi[key] = None
            else:
                result[key] = value
        return result

    def dict_of_lists(self):
        """
        Returns a dictionary where each key is associated with a list of values.
        """
        r = {}
        for key, val in self.items():
            r.setdefault(key, []).append(val)
        return r

    def __delitem__(self, key):
        items = self._items
        found = False
        for i in range(len(items)-1, -1, -1):
            if items[i][0] == key:
                del items[i]
                found = True
        if not found:
            raise KeyError(key)

    def __contains__(self, key):
        for k, v in self._items:
            if k == key:
                return True
        return False

    has_key = __contains__

    def clear(self):
        del self._items[:]

    def copy(self):
        return self.__class__(self)

    def setdefault(self, key, default=None):
        for k, v in self._items:
            if key == k:
                return v
        self._items.append((key, default))
        return default

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError("pop expected at most 2 arguments, got %s"
                             % repr(1 + len(args)))
        for i in range(len(self._items)):
            if self._items[i][0] == key:
                v = self._items[i][1]
                del self._items[i]
                return v
        if args:
            return args[0]
        else:
            raise KeyError(key)

    def popitem(self):
        return self._items.pop()

    def update(self, *args, **kw):
        if args:
            lst = args[0]
            if len(lst) != len(dict(lst)):
                # this does not catch the cases where we overwrite existing
                # keys, but those would produce too many warning
                msg = ("Behavior of MultiDict.update() has changed "
                    "and overwrites duplicate keys. Consider using .extend()"
                )
                warnings.warn(msg, UserWarning, stacklevel=2)
        MutableMapping.update(self, *args, **kw)

    def extend(self, other=None, **kwargs):
        if other is None:
            pass
        elif hasattr(other, 'items'):
            self._items.extend(other.items())
        elif hasattr(other, 'keys'):
            for k in other.keys():
                self._items.append((k, other[k]))
        else:
            for k, v in other:
                self._items.append((k, v))
        if kwargs:
            self.update(kwargs)

    def __repr__(self):
        items = map('(%r, %r)'.__mod__, _hide_passwd(self.items()))
        return '%s([%s])' % (self.__class__.__name__, ', '.join(items))

    def __len__(self):
        return len(self._items)

    ##
    ## All the iteration:
    ##

    def iterkeys(self):
        for k, v in self._items:
            yield k
    if PY3: # pragma: no cover
        keys = iterkeys
    else:
        def keys(self):
            return [k for k, v in self._items]

    __iter__ = iterkeys

    def iteritems(self):
        return iter(self._items)

    if PY3: # pragma: no cover
        items = iteritems
    else:
        def items(self):
            return self._items[:]

    def itervalues(self):
        for k, v in self._items:
            yield v

    if PY3: # pragma: no cover
        values = itervalues
    else:
        def values(self):
            return [v for k, v in self._items]

_dummy = object()

class GetDict(MultiDict):
#     def __init__(self, data, tracker, encoding, errors):
#         d = lambda b: b.decode(encoding, errors)
#         data = [(d(k), d(v)) for k,v in data]
    def __init__(self, data, env):
        self.env = env
        MultiDict.__init__(self, data)
    def on_change(self):
        e = lambda t: t.encode('utf8')
        data = [(e(k), e(v)) for k,v in self.items()]
        qs = url_encode(data)
        self.env['QUERY_STRING'] = qs
        self.env['webob._parsed_query_vars'] = (self, qs)
    def __setitem__(self, key, value):
        MultiDict.__setitem__(self, key, value)
        self.on_change()
    def add(self, key, value):
        MultiDict.add(self, key, value)
        self.on_change()
    def __delitem__(self, key):
        MultiDict.__delitem__(self, key)
        self.on_change()
    def clear(self):
        MultiDict.clear(self)
        self.on_change()
    def setdefault(self, key, default=None):
        result = MultiDict.setdefault(self, key, default)
        self.on_change()
        return result
    def pop(self, key, *args):
        result = MultiDict.pop(self, key, *args)
        self.on_change()
        return result
    def popitem(self):
        result = MultiDict.popitem(self)
        self.on_change()
        return result
    def update(self, *args, **kwargs):
        MultiDict.update(self, *args, **kwargs)
        self.on_change()
    def __repr__(self):
        items = map('(%r, %r)'.__mod__, _hide_passwd(self.items()))
        # TODO: GET -> GetDict
        return 'GET([%s])' % (', '.join(items))
    def copy(self):
        # Copies shouldn't be tracked
        return MultiDict(self)

class NestedMultiDict(MultiDict):
    """
    Wraps several MultiDict objects, treating it as one large MultiDict
    """

    def __init__(self, *dicts):
        self.dicts = dicts

    def __getitem__(self, key):
        for d in self.dicts:
            value = d.get(key, _dummy)
            if value is not _dummy:
                return value
        raise KeyError(key)

    def _readonly(self, *args, **kw):
        raise KeyError("NestedMultiDict objects are read-only")
    __setitem__ = _readonly
    add = _readonly
    __delitem__ = _readonly
    clear = _readonly
    setdefault = _readonly
    pop = _readonly
    popitem = _readonly
    update = _readonly

    def getall(self, key):
        result = []
        for d in self.dicts:
            result.extend(d.getall(key))
        return result

    # Inherited:
    # getone
    # mixed
    # dict_of_lists

    def copy(self):
        return MultiDict(self)

    def __contains__(self, key):
        for d in self.dicts:
            if key in d:
                return True
        return False

    has_key = __contains__

    def __len__(self):
        v = 0
        for d in self.dicts:
            v += len(d)
        return v

    def __nonzero__(self):
        for d in self.dicts:
            if d:
                return True
        return False

    def iteritems(self):
        for d in self.dicts:
            for item in iteritems_(d):
                yield item
    if PY3: # pragma: no cover
        items = iteritems
    else:
        def items(self):
            return list(self.iteritems())

    def itervalues(self):
        for d in self.dicts:
            for value in itervalues_(d):
                yield value
    if PY3: # pragma: no cover
        values = itervalues
    else:
        def values(self):
            return list(self.itervalues())

    def __iter__(self):
        for d in self.dicts:
            for key in d:
                yield key

    iterkeys = __iter__

    if PY3: # pragma: no cover
        keys = iterkeys
    else:
        def keys(self):
            return list(self.iterkeys())

class NoVars(object):
    """
    Represents no variables; used when no variables
    are applicable.

    This is read-only
    """

    def __init__(self, reason=None):
        self.reason = reason or 'N/A'

    def __getitem__(self, key):
        raise KeyError("No key %r: %s" % (key, self.reason))

    def __setitem__(self, *args, **kw):
        raise KeyError("Cannot add variables: %s" % self.reason)

    add = __setitem__
    setdefault = __setitem__
    update = __setitem__

    def __delitem__(self, *args, **kw):
        raise KeyError("No keys to delete: %s" % self.reason)
    clear = __delitem__
    pop = __delitem__
    popitem = __delitem__

    def get(self, key, default=None):
        return default

    def getall(self, key):
        return []

    def getone(self, key):
        return self[key]

    def mixed(self):
        return {}
    dict_of_lists = mixed

    def __contains__(self, key):
        return False
    has_key = __contains__

    def copy(self):
        return self

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__,
                             self.reason)

    def __len__(self):
        return 0

    def __cmp__(self, other):
        return cmp({}, other)

    def iterkeys(self):
        return iter([])

    if PY3: # pragma: no cover
        keys = iterkeys
        items = iterkeys
        values = iterkeys
    else:
        def keys(self):
            return []
        items = keys
        values = keys
        itervalues = iterkeys
        iteritems = iterkeys

    __iter__ = iterkeys

def _hide_passwd(items):
    for k, v in items:
        if ('password' in k
            or 'passwd' in k
            or 'pwd' in k
        ):
            yield k, '******'
        else:
            yield k, v

########NEW FILE########
__FILENAME__ = request
import binascii
import cgi
import io
import os
import re
import sys
import tempfile
import mimetypes
try:
    import simplejson as json
except ImportError:
    import json
import warnings

from webob.acceptparse import (
    AcceptLanguage,
    AcceptCharset,
    MIMEAccept,
    MIMENilAccept,
    NoAccept,
    accept_property,
    )

from webob.cachecontrol import (
    CacheControl,
    serialize_cache_control,
    )

from webob.compat import (
    PY3,
    bytes_,
    integer_types,
    native_,
    parse_qsl_text,
    reraise,
    text_type,
    url_encode,
    url_quote,
    url_unquote,
    quote_plus,
    urlparse,
    )

from webob.cookies import RequestCookies

from webob.descriptors import (
    CHARSET_RE,
    SCHEME_RE,
    converter,
    converter_date,
    environ_getter,
    environ_decoder,
    parse_auth,
    parse_int,
    parse_int_safe,
    parse_range,
    serialize_auth,
    serialize_if_range,
    serialize_int,
    serialize_range,
    upath_property,
    deprecated_property,
    )

from webob.etag import (
    IfRange,
    AnyETag,
    NoETag,
    etag_property,
    )

from webob.headers import EnvironHeaders

from webob.multidict import (
    NestedMultiDict,
    MultiDict,
    NoVars,
    GetDict,
    )

from webob.util import warn_deprecation

__all__ = ['BaseRequest', 'Request', 'LegacyRequest']

class _NoDefault:
    def __repr__(self):
        return '(No Default)'
NoDefault = _NoDefault()

PATH_SAFE = '/:@&+$,'

http_method_probably_has_body = dict.fromkeys(
    ('GET', 'HEAD', 'DELETE', 'TRACE'), False)
http_method_probably_has_body.update(
    dict.fromkeys(('POST', 'PUT', 'PATCH'), True))

_LATIN_ENCODINGS = (
    'ascii', 'latin-1', 'latin', 'latin_1', 'l1', 'latin1',
    'iso-8859-1', 'iso8859_1', 'iso_8859_1', 'iso8859', '8859',
    )

class BaseRequest(object):
    ## The limit after which request bodies should be stored on disk
    ## if they are read in (under this, and the request body is stored
    ## in memory):
    request_body_tempfile_limit = 10*1024

    _charset = None

    def __init__(self, environ, charset=None, unicode_errors=None,
                 decode_param_names=None, **kw):

        if type(environ) is not dict:
            raise TypeError(
                "WSGI environ must be a dict; you passed %r" % (environ,))
        if unicode_errors is not None:
            warnings.warn(
                "You unicode_errors=%r to the Request constructor.  Passing a "
                "``unicode_errors`` value to the Request is no longer "
                "supported in WebOb 1.2+.  This value has been ignored " % (
                    unicode_errors,),
                DeprecationWarning
                )
        if decode_param_names is not None:
            warnings.warn(
                "You passed decode_param_names=%r to the Request constructor. "
                "Passing a ``decode_param_names`` value to the Request "
                "is no longer supported in WebOb 1.2+.  This value has "
                "been ignored " % (decode_param_names,),
                DeprecationWarning
                )
        if not _is_utf8(charset):
            raise DeprecationWarning(
                "You passed charset=%r to the Request constructor. As of "
                "WebOb 1.2, if your application needs a non-UTF-8 request "
                "charset, please construct the request without a charset or "
                "with a charset of 'None',  then use ``req = "
                "req.decode(charset)``" % charset

            )
        d = self.__dict__
        d['environ'] = environ
        if kw:
            cls = self.__class__
            if 'method' in kw:
                # set method first, because .body setters
                # depend on it for checks
                self.method = kw.pop('method')
            for name, value in kw.items():
                if not hasattr(cls, name):
                    raise TypeError(
                        "Unexpected keyword: %s=%r" % (name, value))
                setattr(self, name, value)

    if PY3: # pragma: no cover
        def encget(self, key, default=NoDefault, encattr=None):
            val = self.environ.get(key, default)
            if val is NoDefault:
                raise KeyError(key)
            if val is default:
                return default
            if not encattr:
                return val
            encoding = getattr(self, encattr)
            if encoding in _LATIN_ENCODINGS: # shortcut
                return val
            return bytes_(val, 'latin-1').decode(encoding)
    else:
        def encget(self, key, default=NoDefault, encattr=None):
            val = self.environ.get(key, default)
            if val is NoDefault:
                raise KeyError(key)
            if val is default:
                return default
            if encattr is None:
                return val
            encoding = getattr(self, encattr)
            return val.decode(encoding)

    def encset(self, key, val, encattr=None):
        if encattr:
            encoding = getattr(self, encattr)
        else:
            encoding = 'ascii'
        if PY3: # pragma: no cover
            self.environ[key] = bytes_(val, encoding).decode('latin-1')
        else:
            self.environ[key] = bytes_(val, encoding)

    @property
    def charset(self):
        if self._charset is None:
            charset = detect_charset(self._content_type_raw)
            if _is_utf8(charset):
                charset = 'UTF-8'
            self._charset = charset
        return self._charset

    @charset.setter
    def charset(self, charset):
        if _is_utf8(charset):
            charset = 'UTF-8'
        if charset != self.charset:
            raise DeprecationWarning("Use req = req.decode(%r)" % charset)

    def decode(self, charset=None, errors='strict'):
        charset = charset or self.charset
        if charset == 'UTF-8':
            return self
        # cookies and path are always utf-8
        t = Transcoder(charset, errors)

        new_content_type = CHARSET_RE.sub('; charset="UTF-8"',
                                          self._content_type_raw)
        content_type = self.content_type
        r = self.__class__(
            self.environ.copy(),
            query_string=t.transcode_query(self.query_string),
            content_type=new_content_type,
        )

        if content_type == 'application/x-www-form-urlencoded':
            r.body = bytes_(t.transcode_query(native_(r.body)))
            return r
        elif content_type != 'multipart/form-data':
            return r

        fs_environ = self.environ.copy()
        fs_environ.setdefault('CONTENT_LENGTH', '0')
        fs_environ['QUERY_STRING'] = ''
        if PY3: # pragma: no cover
            fs = cgi.FieldStorage(fp=self.body_file,
                                  environ=fs_environ,
                                  keep_blank_values=True,
                                  encoding=charset,
                                  errors=errors)
        else:
            fs = cgi.FieldStorage(fp=self.body_file,
                                  environ=fs_environ,
                                  keep_blank_values=True)


        fout = t.transcode_fs(fs, r._content_type_raw)

        # this order is important, because setting body_file
        # resets content_length
        r.body_file = fout
        r.content_length = fout.tell()
        fout.seek(0)
        return r


    # this is necessary for correct warnings depth for both
    # BaseRequest and Request (due to AdhocAttrMixin.__setattr__)
    _setattr_stacklevel = 2

    def _body_file__get(self):
        """
            Input stream of the request (wsgi.input).
            Setting this property resets the content_length and seekable flag
            (unlike setting req.body_file_raw).
        """
        if not self.is_body_readable:
            return io.BytesIO()
        r = self.body_file_raw
        clen = self.content_length
        if not self.is_body_seekable and clen is not None:
            # we need to wrap input in LimitedLengthFile
            # but we have to cache the instance as well
            # otherwise this would stop working
            # (.remaining counter would reset between calls):
            #   req.body_file.read(100)
            #   req.body_file.read(100)
            env = self.environ
            wrapped, raw = env.get('webob._body_file', (0,0))
            if raw is not r:
                wrapped = LimitedLengthFile(r, clen)
                wrapped = io.BufferedReader(wrapped)
                env['webob._body_file'] = wrapped, r
            r = wrapped
        return r

    def _body_file__set(self, value):
        if isinstance(value, bytes):
            warn_deprecation(
                "Please use req.body = b'bytes' or req.body_file = fileobj",
                '1.2',
                self._setattr_stacklevel
            )
        self.content_length = None
        self.body_file_raw = value
        self.is_body_seekable = False
        self.is_body_readable = True
    def _body_file__del(self):
        self.body = b''
    body_file = property(_body_file__get,
                         _body_file__set,
                         _body_file__del,
                         doc=_body_file__get.__doc__)
    body_file_raw = environ_getter('wsgi.input')
    @property
    def body_file_seekable(self):
        """
            Get the body of the request (wsgi.input) as a seekable file-like
            object. Middleware and routing applications should use this
            attribute over .body_file.

            If you access this value, CONTENT_LENGTH will also be updated.
        """
        if not self.is_body_seekable:
            self.make_body_seekable()
        return self.body_file_raw

    url_encoding = environ_getter('webob.url_encoding', 'UTF-8')
    scheme = environ_getter('wsgi.url_scheme')
    method = environ_getter('REQUEST_METHOD', 'GET')
    http_version = environ_getter('SERVER_PROTOCOL')
    content_length = converter(
        environ_getter('CONTENT_LENGTH', None, '14.13'),
        parse_int_safe, serialize_int, 'int')
    remote_user = environ_getter('REMOTE_USER', None)
    remote_addr = environ_getter('REMOTE_ADDR', None)
    query_string = environ_getter('QUERY_STRING', '')
    server_name = environ_getter('SERVER_NAME')
    server_port = converter(
        environ_getter('SERVER_PORT'),
        parse_int, serialize_int, 'int')

    script_name = environ_decoder('SCRIPT_NAME', '', encattr='url_encoding')
    path_info = environ_decoder('PATH_INFO', encattr='url_encoding')

    # bw compat
    uscript_name = script_name
    upath_info = path_info

    _content_type_raw = environ_getter('CONTENT_TYPE', '')

    def _content_type__get(self):
        """Return the content type, but leaving off any parameters (like
        charset, but also things like the type in ``application/atom+xml;
        type=entry``)

        If you set this property, you can include parameters, or if
        you don't include any parameters in the value then existing
        parameters will be preserved.
        """
        return self._content_type_raw.split(';', 1)[0]
    def _content_type__set(self, value=None):
        if value is not None:
            value = str(value)
            if ';' not in value:
                content_type = self._content_type_raw
                if ';' in content_type:
                    value += ';' + content_type.split(';', 1)[1]
        self._content_type_raw = value

    content_type = property(_content_type__get,
                            _content_type__set,
                            _content_type__set,
                            _content_type__get.__doc__)

    _headers = None

    def _headers__get(self):
        """
        All the request headers as a case-insensitive dictionary-like
        object.
        """
        if self._headers is None:
            self._headers = EnvironHeaders(self.environ)
        return self._headers

    def _headers__set(self, value):
        self.headers.clear()
        self.headers.update(value)

    headers = property(_headers__get, _headers__set, doc=_headers__get.__doc__)

    @property
    def client_addr(self):
        """
        The effective client IP address as a string.  If the
        ``HTTP_X_FORWARDED_FOR`` header exists in the WSGI environ, this
        attribute returns the client IP address present in that header
        (e.g. if the header value is ``192.168.1.1, 192.168.1.2``, the value
        will be ``192.168.1.1``). If no ``HTTP_X_FORWARDED_FOR`` header is
        present in the environ at all, this attribute will return the value
        of the ``REMOTE_ADDR`` header.  If the ``REMOTE_ADDR`` header is
        unset, this attribute will return the value ``None``.

        .. warning::

           It is possible for user agents to put someone else's IP or just
           any string in ``HTTP_X_FORWARDED_FOR`` as it is a normal HTTP
           header. Forward proxies can also provide incorrect values (private
           IP addresses etc).  You cannot "blindly" trust the result of this
           method to provide you with valid data unless you're certain that
           ``HTTP_X_FORWARDED_FOR`` has the correct values.  The WSGI server
           must be behind a trusted proxy for this to be true.
        """
        e = self.environ
        xff = e.get('HTTP_X_FORWARDED_FOR')
        if xff is not None:
            addr = xff.split(',')[0].strip()
        else:
            addr = e.get('REMOTE_ADDR')
        return addr

    @property
    def host_port(self):
        """
        The effective server port number as a string.  If the ``HTTP_HOST``
        header exists in the WSGI environ, this attribute returns the port
        number present in that header. If the ``HTTP_HOST`` header exists but
        contains no explicit port number: if the WSGI url scheme is "https" ,
        this attribute returns "443", if the WSGI url scheme is "http", this
        attribute returns "80" .  If no ``HTTP_HOST`` header is present in
        the environ at all, this attribute will return the value of the
        ``SERVER_PORT`` header (which is guaranteed to be present).
        """
        e = self.environ
        host = e.get('HTTP_HOST')
        if host is not None:
            if ':' in host:
                host, port = host.split(':', 1)
            else:
                url_scheme = e['wsgi.url_scheme']
                if url_scheme == 'https':
                    port = '443'
                else:
                    port = '80'
        else:
            port = e['SERVER_PORT']
        return port

    @property
    def host_url(self):
        """
        The URL through the host (no path)
        """
        e = self.environ
        scheme = e.get('wsgi.url_scheme')
        url = scheme + '://'
        host = e.get('HTTP_HOST')
        if host is not None:
            if ':' in host:
                host, port = host.split(':', 1)
            else:
                port = None
        else:
            host = e.get('SERVER_NAME')
            port = e.get('SERVER_PORT')
        if scheme == 'https':
            if port == '443':
                port = None
        elif scheme == 'http':
            if port == '80':
                port = None
        url += host
        if port:
            url += ':%s' % port
        return url

    @property
    def application_url(self):
        """
        The URL including SCRIPT_NAME (no PATH_INFO or query string)
        """
        bscript_name = bytes_(self.script_name, self.url_encoding)
        return self.host_url + url_quote(bscript_name, PATH_SAFE)

    @property
    def path_url(self):
        """
        The URL including SCRIPT_NAME and PATH_INFO, but not QUERY_STRING
        """
        bpath_info = bytes_(self.path_info, self.url_encoding)
        return self.application_url + url_quote(bpath_info, PATH_SAFE)

    @property
    def path(self):
        """
        The path of the request, without host or query string
        """
        bscript = bytes_(self.script_name, self.url_encoding)
        bpath = bytes_(self.path_info, self.url_encoding)
        return url_quote(bscript, PATH_SAFE) + url_quote(bpath, PATH_SAFE)

    @property
    def path_qs(self):
        """
        The path of the request, without host but with query string
        """
        path = self.path
        qs = self.environ.get('QUERY_STRING')
        if qs:
            path += '?' + qs
        return path

    @property
    def url(self):
        """
        The full request URL, including QUERY_STRING
        """
        url = self.path_url
        qs = self.environ.get('QUERY_STRING')
        if qs:
            url += '?' + qs
        return url

    def relative_url(self, other_url, to_application=False):
        """
        Resolve other_url relative to the request URL.

        If ``to_application`` is True, then resolve it relative to the
        URL with only SCRIPT_NAME
        """
        if to_application:
            url = self.application_url
            if not url.endswith('/'):
                url += '/'
        else:
            url = self.path_url
        return urlparse.urljoin(url, other_url)

    def path_info_pop(self, pattern=None):
        """
        'Pops' off the next segment of PATH_INFO, pushing it onto
        SCRIPT_NAME, and returning the popped segment.  Returns None if
        there is nothing left on PATH_INFO.

        Does not return ``''`` when there's an empty segment (like
        ``/path//path``); these segments are just ignored.

        Optional ``pattern`` argument is a regexp to match the return value
        before returning. If there is no match, no changes are made to the
        request and None is returned.
        """
        path = self.path_info
        if not path:
            return None
        slashes = ''
        while path.startswith('/'):
            slashes += '/'
            path = path[1:]
        idx = path.find('/')
        if idx == -1:
            idx = len(path)
        r = path[:idx]
        if pattern is None or re.match(pattern, r):
            self.script_name += slashes + r
            self.path_info = path[idx:]
            return r

    def path_info_peek(self):
        """
        Returns the next segment on PATH_INFO, or None if there is no
        next segment.  Doesn't modify the environment.
        """
        path = self.path_info
        if not path:
            return None
        path = path.lstrip('/')
        return path.split('/', 1)[0]

    def _urlvars__get(self):
        """
        Return any *named* variables matched in the URL.

        Takes values from ``environ['wsgiorg.routing_args']``.
        Systems like ``routes`` set this value.
        """
        if 'paste.urlvars' in self.environ:
            return self.environ['paste.urlvars']
        elif 'wsgiorg.routing_args' in self.environ:
            return self.environ['wsgiorg.routing_args'][1]
        else:
            result = {}
            self.environ['wsgiorg.routing_args'] = ((), result)
            return result

    def _urlvars__set(self, value):
        environ = self.environ
        if 'wsgiorg.routing_args' in environ:
            environ['wsgiorg.routing_args'] = (
                    environ['wsgiorg.routing_args'][0], value)
            if 'paste.urlvars' in environ:
                del environ['paste.urlvars']
        elif 'paste.urlvars' in environ:
            environ['paste.urlvars'] = value
        else:
            environ['wsgiorg.routing_args'] = ((), value)

    def _urlvars__del(self):
        if 'paste.urlvars' in self.environ:
            del self.environ['paste.urlvars']
        if 'wsgiorg.routing_args' in self.environ:
            if not self.environ['wsgiorg.routing_args'][0]:
                del self.environ['wsgiorg.routing_args']
            else:
                self.environ['wsgiorg.routing_args'] = (
                        self.environ['wsgiorg.routing_args'][0], {})

    urlvars = property(_urlvars__get,
                       _urlvars__set,
                       _urlvars__del,
                       doc=_urlvars__get.__doc__)

    def _urlargs__get(self):
        """
        Return any *positional* variables matched in the URL.

        Takes values from ``environ['wsgiorg.routing_args']``.
        Systems like ``routes`` set this value.
        """
        if 'wsgiorg.routing_args' in self.environ:
            return self.environ['wsgiorg.routing_args'][0]
        else:
            # Since you can't update this value in-place, we don't need
            # to set the key in the environment
            return ()

    def _urlargs__set(self, value):
        environ = self.environ
        if 'paste.urlvars' in environ:
            # Some overlap between this and wsgiorg.routing_args; we need
            # wsgiorg.routing_args to make this work
            routing_args = (value, environ.pop('paste.urlvars'))
        elif 'wsgiorg.routing_args' in environ:
            routing_args = (value, environ['wsgiorg.routing_args'][1])
        else:
            routing_args = (value, {})
        environ['wsgiorg.routing_args'] = routing_args

    def _urlargs__del(self):
        if 'wsgiorg.routing_args' in self.environ:
            if not self.environ['wsgiorg.routing_args'][1]:
                del self.environ['wsgiorg.routing_args']
            else:
                self.environ['wsgiorg.routing_args'] = (
                        (), self.environ['wsgiorg.routing_args'][1])

    urlargs = property(_urlargs__get,
                       _urlargs__set,
                       _urlargs__del,
                       _urlargs__get.__doc__)

    @property
    def is_xhr(self):
        """Is X-Requested-With header present and equal to ``XMLHttpRequest``?

        Note: this isn't set by every XMLHttpRequest request, it is
        only set if you are using a Javascript library that sets it
        (or you set the header yourself manually).  Currently
        Prototype and jQuery are known to set this header."""
        return self.environ.get('HTTP_X_REQUESTED_WITH', '') == 'XMLHttpRequest'

    def _host__get(self):
        """Host name provided in HTTP_HOST, with fall-back to SERVER_NAME"""
        if 'HTTP_HOST' in self.environ:
            return self.environ['HTTP_HOST']
        else:
            return '%(SERVER_NAME)s:%(SERVER_PORT)s' % self.environ
    def _host__set(self, value):
        self.environ['HTTP_HOST'] = value
    def _host__del(self):
        if 'HTTP_HOST' in self.environ:
            del self.environ['HTTP_HOST']
    host = property(_host__get, _host__set, _host__del, doc=_host__get.__doc__)

    @property
    def domain(self):
        """ Returns the domain portion of the host value.  Equivalent to:

        .. code-block:: python

           domain = request.host
           if ':' in domain:
               domain = domain.split(':', 1)[0]

        This will be equivalent to the domain portion of the ``HTTP_HOST``
        value in the environment if it exists, or the ``SERVER_NAME`` value in
        the environment if it doesn't.  For example, if the environment
        contains an ``HTTP_HOST`` value of ``foo.example.com:8000``,
        ``request.domain`` will return ``foo.example.com``.

        Note that this value cannot be *set* on the request.  To set the host
        value use :meth:`webob.request.Request.host` instead.
        """
        domain = self.host
        if ':' in domain:
             domain = domain.split(':', 1)[0]
        return domain

    def _body__get(self):
        """
        Return the content of the request body.
        """
        if not self.is_body_readable:
            return b''
        self.make_body_seekable() # we need this to have content_length
        r = self.body_file.read(self.content_length)
        self.body_file_raw.seek(0)
        return r
    def _body__set(self, value):
        if value is None:
            value = b''
        if not isinstance(value, bytes):
            raise TypeError("You can only set Request.body to bytes (not %r)"
                                % type(value))
        if not http_method_probably_has_body.get(self.method, True):
            if not value:
                self.content_length = None
                self.body_file_raw = io.BytesIO()
                return
        self.content_length = len(value)
        self.body_file_raw = io.BytesIO(value)
        self.is_body_seekable = True
    def _body__del(self):
        self.body = b''
    body = property(_body__get, _body__set, _body__del, doc=_body__get.__doc__)

    def _json_body__get(self):
        """Access the body of the request as JSON"""
        return json.loads(self.body.decode(self.charset))

    def _json_body__set(self, value):
        self.body = json.dumps(value, separators=(',', ':')).encode(self.charset)

    def _json_body__del(self):
        del self.body

    json = json_body = property(_json_body__get, _json_body__set, _json_body__del)

    def _text__get(self):
        """
        Get/set the text value of the body
        """
        if not self.charset:
            raise AttributeError(
                "You cannot access Request.text unless charset is set")
        body = self.body
        return body.decode(self.charset)

    def _text__set(self, value):
        if not self.charset:
            raise AttributeError(
                "You cannot access Response.text unless charset is set")
        if not isinstance(value, text_type):
            raise TypeError(
                "You can only set Request.text to a unicode string "
                "(not %s)" % type(value))
        self.body = value.encode(self.charset)

    def _text__del(self):
        del self.body

    text = property(_text__get, _text__set, _text__del, doc=_text__get.__doc__)


    @property
    def POST(self):
        """
        Return a MultiDict containing all the variables from a form
        request. Returns an empty dict-like object for non-form requests.

        Form requests are typically POST requests, however PUT & PATCH requests
        with an appropriate Content-Type are also supported.
        """
        env = self.environ
        if self.method not in ('POST', 'PUT', 'PATCH'):
            return NoVars('Not a form request')
        if 'webob._parsed_post_vars' in env:
            vars, body_file = env['webob._parsed_post_vars']
            if body_file is self.body_file_raw:
                return vars
        content_type = self.content_type
        if ((self.method == 'PUT' and not content_type)
            or content_type not in
                ('',
                 'application/x-www-form-urlencoded',
                 'multipart/form-data')
                 ):
            # Not an HTML form submission
            return NoVars('Not an HTML form submission (Content-Type: %s)'
                          % content_type)
        self._check_charset()
        if self.is_body_seekable:
            self.body_file_raw.seek(0)
        fs_environ = env.copy()
        # FieldStorage assumes a missing CONTENT_LENGTH, but a
        # default of 0 is better:
        fs_environ.setdefault('CONTENT_LENGTH', '0')
        fs_environ['QUERY_STRING'] = ''
        if PY3: # pragma: no cover
            fs = cgi.FieldStorage(
                fp=self.body_file,
                environ=fs_environ,
                keep_blank_values=True,
                encoding='utf8')
            vars = MultiDict.from_fieldstorage(fs)
        else:
            fs = cgi.FieldStorage(
                fp=self.body_file,
                environ=fs_environ,
                keep_blank_values=True)
            vars = MultiDict.from_fieldstorage(fs)


        #ctype = self.content_type or 'application/x-www-form-urlencoded'
        ctype = self._content_type_raw or 'application/x-www-form-urlencoded'
        f = FakeCGIBody(vars, ctype)
        self.body_file = io.BufferedReader(f)
        env['webob._parsed_post_vars'] = (vars, self.body_file_raw)
        return vars

    @property
    def GET(self):
        """
        Return a MultiDict containing all the variables from the
        QUERY_STRING.
        """
        env = self.environ
        source = env.get('QUERY_STRING', '')
        if 'webob._parsed_query_vars' in env:
            vars, qs = env['webob._parsed_query_vars']
            if qs == source:
                return vars

        data = []
        if source:
            # this is disabled because we want to access req.GET
            # for text/plain; charset=ascii uploads for example
            #self._check_charset()
            data = parse_qsl_text(source)
            #d = lambda b: b.decode('utf8')
            #data = [(d(k), d(v)) for k,v in data]
        vars = GetDict(data, env)
        env['webob._parsed_query_vars'] = (vars, source)
        return vars

    def _check_charset(self):
        if self.charset != 'UTF-8':
            raise DeprecationWarning(
                "Requests are expected to be submitted in UTF-8, not %s. "
                "You can fix this by doing req = req.decode('%s')" % (
                    self.charset, self.charset)
            )

    @property
    def params(self):
        """
        A dictionary-like object containing both the parameters from
        the query string and request body.
        """
        params = NestedMultiDict(self.GET, self.POST)
        return params


    @property
    def cookies(self):
        """
        Return a dictionary of cookies as found in the request.
        """
        return RequestCookies(self.environ)

    @cookies.setter
    def cookies(self, val):
        self.environ.pop('HTTP_COOKIE', None)
        r = RequestCookies(self.environ)
        r.update(val)

    def copy(self):
        """
        Copy the request and environment object.

        This only does a shallow copy, except of wsgi.input
        """
        self.make_body_seekable()
        env = self.environ.copy()
        new_req = self.__class__(env)
        new_req.copy_body()
        return new_req

    def copy_get(self):
        """
        Copies the request and environment object, but turning this request
        into a GET along the way.  If this was a POST request (or any other
        verb) then it becomes GET, and the request body is thrown away.
        """
        env = self.environ.copy()
        return self.__class__(env, method='GET', content_type=None,
                              body=b'')

    # webob.is_body_seekable marks input streams that are seekable
    # this way we can have seekable input without testing the .seek() method
    is_body_seekable = environ_getter('webob.is_body_seekable', False)

    #is_body_readable = environ_getter('webob.is_body_readable', False)

    def _is_body_readable__get(self):
        """
            webob.is_body_readable is a flag that tells us
            that we can read the input stream even though
            CONTENT_LENGTH is missing. This allows FakeCGIBody
            to work and can be used by servers to support
            chunked encoding in requests.
            For background see https://bitbucket.org/ianb/webob/issue/6
        """
        if http_method_probably_has_body.get(self.method):
            # known HTTP method with body
            return True
        elif self.content_length is not None:
            # unknown HTTP method, but the Content-Length
            # header is present
            return True
        else:
            # last resort -- rely on the special flag
            return self.environ.get('webob.is_body_readable', False)

    def _is_body_readable__set(self, flag):
        self.environ['webob.is_body_readable'] = bool(flag)

    is_body_readable = property(_is_body_readable__get, _is_body_readable__set,
        doc=_is_body_readable__get.__doc__
    )



    def make_body_seekable(self):
        """
        This forces ``environ['wsgi.input']`` to be seekable.
        That means that, the content is copied into a BytesIO or temporary
        file and flagged as seekable, so that it will not be unnecessarily
        copied again.

        After calling this method the .body_file is always seeked to the
        start of file and .content_length is not None.

        The choice to copy to BytesIO is made from
        ``self.request_body_tempfile_limit``
        """
        if self.is_body_seekable:
            self.body_file_raw.seek(0)
        else:
            self.copy_body()


    def copy_body(self):
        """
        Copies the body, in cases where it might be shared with
        another request object and that is not desired.

        This copies the body in-place, either into a BytesIO object
        or a temporary file.
        """
        if not self.is_body_readable:
            # there's no body to copy
            self.body = b''
        elif self.content_length is None:
            # chunked body or FakeCGIBody
            self.body = self.body_file_raw.read()
            self._copy_body_tempfile()
        else:
            # try to read body into tempfile
            did_copy = self._copy_body_tempfile()
            if not did_copy:
                # it wasn't necessary, so just read it into memory
                self.body = self.body_file.read(self.content_length)

    def _copy_body_tempfile(self):
        """
            Copy wsgi.input to tempfile if necessary. Returns True if it did.
        """
        tempfile_limit = self.request_body_tempfile_limit
        todo = self.content_length
        assert isinstance(todo, integer_types), todo
        if not tempfile_limit or todo <= tempfile_limit:
            return False
        fileobj = self.make_tempfile()
        input = self.body_file
        while todo > 0:
            data = input.read(min(todo, 65536))
            if not data:
                # Normally this should not happen, because LimitedLengthFile
                # should have raised an exception by now.
                # It can happen if the is_body_seekable flag is incorrect.
                raise DisconnectionError(
                    "Client disconnected (%s more bytes were expected)"
                    % todo
                )
            fileobj.write(data)
            todo -= len(data)
        fileobj.seek(0)
        self.body_file_raw = fileobj
        self.is_body_seekable = True
        return True

    def make_tempfile(self):
        """
            Create a tempfile to store big request body.
            This API is not stable yet. A 'size' argument might be added.
        """
        return tempfile.TemporaryFile()


    def remove_conditional_headers(self,
                                   remove_encoding=True,
                                   remove_range=True,
                                   remove_match=True,
                                   remove_modified=True):
        """
        Remove headers that make the request conditional.

        These headers can cause the response to be 304 Not Modified,
        which in some cases you may not want to be possible.

        This does not remove headers like If-Match, which are used for
        conflict detection.
        """
        check_keys = []
        if remove_range:
            check_keys += ['HTTP_IF_RANGE', 'HTTP_RANGE']
        if remove_match:
            check_keys.append('HTTP_IF_NONE_MATCH')
        if remove_modified:
            check_keys.append('HTTP_IF_MODIFIED_SINCE')
        if remove_encoding:
            check_keys.append('HTTP_ACCEPT_ENCODING')

        for key in check_keys:
            if key in self.environ:
                del self.environ[key]


    accept = accept_property('Accept', '14.1', MIMEAccept, MIMENilAccept)
    accept_charset = accept_property('Accept-Charset', '14.2', AcceptCharset)
    accept_encoding = accept_property('Accept-Encoding', '14.3',
                                      NilClass=NoAccept)
    accept_language = accept_property('Accept-Language', '14.4', AcceptLanguage)

    authorization = converter(
        environ_getter('HTTP_AUTHORIZATION', None, '14.8'),
        parse_auth, serialize_auth,
    )


    def _cache_control__get(self):
        """
        Get/set/modify the Cache-Control header (`HTTP spec section 14.9
        <http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.9>`_)
        """
        env = self.environ
        value = env.get('HTTP_CACHE_CONTROL', '')
        cache_header, cache_obj = env.get('webob._cache_control', (None, None))
        if cache_obj is not None and cache_header == value:
            return cache_obj
        cache_obj = CacheControl.parse(value,
                                       updates_to=self._update_cache_control,
                                       type='request')
        env['webob._cache_control'] = (value, cache_obj)
        return cache_obj

    def _cache_control__set(self, value):
        env = self.environ
        value = value or ''
        if isinstance(value, dict):
            value = CacheControl(value, type='request')
        if isinstance(value, CacheControl):
            str_value = str(value)
            env['HTTP_CACHE_CONTROL'] = str_value
            env['webob._cache_control'] = (str_value, value)
        else:
            env['HTTP_CACHE_CONTROL'] = str(value)
            env['webob._cache_control'] = (None, None)

    def _cache_control__del(self):
        env = self.environ
        if 'HTTP_CACHE_CONTROL' in env:
            del env['HTTP_CACHE_CONTROL']
        if 'webob._cache_control' in env:
            del env['webob._cache_control']

    def _update_cache_control(self, prop_dict):
        self.environ['HTTP_CACHE_CONTROL'] = serialize_cache_control(prop_dict)

    cache_control = property(_cache_control__get,
                             _cache_control__set,
                             _cache_control__del,
                             doc=_cache_control__get.__doc__)


    if_match = etag_property('HTTP_IF_MATCH', AnyETag, '14.24')
    if_none_match = etag_property('HTTP_IF_NONE_MATCH', NoETag, '14.26',
                                  strong=False)

    date = converter_date(environ_getter('HTTP_DATE', None, '14.8'))
    if_modified_since = converter_date(
                    environ_getter('HTTP_IF_MODIFIED_SINCE', None, '14.25'))
    if_unmodified_since = converter_date(
                    environ_getter('HTTP_IF_UNMODIFIED_SINCE', None, '14.28'))
    if_range = converter(
        environ_getter('HTTP_IF_RANGE', None, '14.27'),
        IfRange.parse, serialize_if_range, 'IfRange object')


    max_forwards = converter(
        environ_getter('HTTP_MAX_FORWARDS', None, '14.31'),
        parse_int, serialize_int, 'int')

    pragma = environ_getter('HTTP_PRAGMA', None, '14.32')

    range = converter(
        environ_getter('HTTP_RANGE', None, '14.35'),
        parse_range, serialize_range, 'Range object')

    referer = environ_getter('HTTP_REFERER', None, '14.36')
    referrer = referer

    user_agent = environ_getter('HTTP_USER_AGENT', None, '14.43')

    def __repr__(self):
        try:
            name = '%s %s' % (self.method, self.url)
        except KeyError:
            name = '(invalid WSGI environ)'
        msg = '<%s at 0x%x %s>' % (
            self.__class__.__name__,
            abs(id(self)), name)
        return msg

    def as_bytes(self, skip_body=False):
        """
            Return HTTP bytes representing this request.
            If skip_body is True, exclude the body.
            If skip_body is an integer larger than one, skip body
            only if its length is bigger than that number.
        """
        url = self.url
        host = self.host_url
        assert url.startswith(host)
        url = url[len(host):]
        parts = [bytes_('%s %s %s' % (self.method, url, self.http_version))]
        #self.headers.setdefault('Host', self.host)

        # acquire body before we handle headers so that
        # content-length will be set
        body = None
        if self.method in ('PUT', 'POST'):
            if skip_body > 1:
                if len(self.body) > skip_body:
                    body = bytes_('<body skipped (len=%s)>' % len(self.body))
                else:
                    skip_body = False
            if not skip_body:
                body = self.body

        for k, v in sorted(self.headers.items()):
            header = bytes_('%s: %s'  % (k, v))
            parts.append(header)

        if body:
            parts.extend([b'', body])
        # HTTP clearly specifies CRLF
        return b'\r\n'.join(parts)

    def as_string(self, skip_body=False):
        # TODO: Remove in 1.4
        warn_deprecation(
            "Please use req.as_bytes",
            '1.3',
            self._setattr_stacklevel
            )

    def as_text(self):
        bytes = self.as_bytes()
        return bytes.decode(self.charset)

    __str__ = as_text

    @classmethod
    def from_bytes(cls, b):
        """
            Create a request from HTTP bytes data. If the bytes contain
            extra data after the request, raise a ValueError.
        """
        f = io.BytesIO(b)
        r = cls.from_file(f)
        if f.tell() != len(b):
            raise ValueError("The string contains more data than expected")
        return r

    @classmethod
    def from_string(cls, b):
        # TODO: Remove in 1.4
        warn_deprecation(
            "Please use req.from_bytes",
            '1.3',
            cls._setattr_stacklevel
            )

    @classmethod
    def from_text(cls, s):
        b = bytes_(s, 'utf-8')
        return cls.from_bytes(b)

    @classmethod
    def from_file(cls, fp):
        """Read a request from a file-like object (it must implement
        ``.read(size)`` and ``.readline()``).

        It will read up to the end of the request, not the end of the
        file (unless the request is a POST or PUT and has no
        Content-Length, in that case, the entire file is read).

        This reads the request as represented by ``str(req)``; it may
        not read every valid HTTP request properly.
        """
        start_line = fp.readline()
        is_text = isinstance(start_line, text_type)
        if is_text:
            crlf = '\r\n'
            colon = ':'
        else:
            crlf = b'\r\n'
            colon = b':'
        try:
            header = start_line.rstrip(crlf)
            method, resource, http_version = header.split(None, 2)
            method = native_(method, 'utf-8')
            resource = native_(resource, 'utf-8')
            http_version = native_(http_version, 'utf-8')
        except ValueError:
            raise ValueError('Bad HTTP request line: %r' % start_line)
        r = cls(environ_from_url(resource),
                http_version=http_version,
                method=method.upper()
                )
        del r.environ['HTTP_HOST']
        while 1:
            line = fp.readline()
            if not line.strip():
                # end of headers
                break
            hname, hval = line.split(colon, 1)
            hname = native_(hname, 'utf-8')
            hval = native_(hval, 'utf-8').strip()
            if hname in r.headers:
                hval = r.headers[hname] + ', ' + hval
            r.headers[hname] = hval
        if r.method in ('PUT', 'POST'):
            clen = r.content_length
            if clen is None:
                body = fp.read()
            else:
                body = fp.read(clen)
            if is_text:
                body = bytes_(body, 'utf-8')
            r.body = body
        return r

    def call_application(self, application, catch_exc_info=False):
        """
        Call the given WSGI application, returning ``(status_string,
        headerlist, app_iter)``

        Be sure to call ``app_iter.close()`` if it's there.

        If catch_exc_info is true, then returns ``(status_string,
        headerlist, app_iter, exc_info)``, where the fourth item may
        be None, but won't be if there was an exception.  If you don't
        do this and there was an exception, the exception will be
        raised directly.
        """
        if self.is_body_seekable:
            self.body_file_raw.seek(0)
        captured = []
        output = []
        def start_response(status, headers, exc_info=None):
            if exc_info is not None and not catch_exc_info:
                reraise(exc_info)
            captured[:] = [status, headers, exc_info]
            return output.append
        app_iter = application(self.environ, start_response)
        if output or not captured:
            try:
                output.extend(app_iter)
            finally:
                if hasattr(app_iter, 'close'):
                    app_iter.close()
            app_iter = output
        if catch_exc_info:
            return (captured[0], captured[1], app_iter, captured[2])
        else:
            return (captured[0], captured[1], app_iter)

    # Will be filled in later:
    ResponseClass = None

    def send(self, application=None, catch_exc_info=False):
        """
        Like ``.call_application(application)``, except returns a
        response object with ``.status``, ``.headers``, and ``.body``
        attributes.

        This will use ``self.ResponseClass`` to figure out the class
        of the response object to return.

        If ``application`` is not given, this will send the request to
        ``self.make_default_send_app()``
        """
        if application is None:
            application = self.make_default_send_app()
        if catch_exc_info:
            status, headers, app_iter, exc_info = self.call_application(
                application, catch_exc_info=True)
            del exc_info
        else:
            status, headers, app_iter = self.call_application(
                application, catch_exc_info=False)
        return self.ResponseClass(
            status=status, headerlist=list(headers), app_iter=app_iter)

    get_response = send

    def make_default_send_app(self):
        global _client
        try:
            client = _client
        except NameError:
            from webob import client
            _client = client
        return client.send_request_app

    @classmethod
    def blank(cls, path, environ=None, base_url=None,
              headers=None, POST=None, **kw):
        """
        Create a blank request environ (and Request wrapper) with the
        given path (path should be urlencoded), and any keys from
        environ.

        The path will become path_info, with any query string split
        off and used.

        All necessary keys will be added to the environ, but the
        values you pass in will take precedence.  If you pass in
        base_url then wsgi.url_scheme, HTTP_HOST, and SCRIPT_NAME will
        be filled in from that value.

        Any extra keyword will be passed to ``__init__``.
        """
        env = environ_from_url(path)
        if base_url:
            scheme, netloc, path, query, fragment = urlparse.urlsplit(base_url)
            if query or fragment:
                raise ValueError(
                    "base_url (%r) cannot have a query or fragment"
                    % base_url)
            if scheme:
                env['wsgi.url_scheme'] = scheme
            if netloc:
                if ':' not in netloc:
                    if scheme == 'http':
                        netloc += ':80'
                    elif scheme == 'https':
                        netloc += ':443'
                    else:
                        raise ValueError(
                            "Unknown scheme: %r" % scheme)
                host, port = netloc.split(':', 1)
                env['SERVER_PORT'] = port
                env['SERVER_NAME'] = host
                env['HTTP_HOST'] = netloc
            if path:
                env['SCRIPT_NAME'] = url_unquote(path)
        if environ:
            env.update(environ)
        content_type = kw.get('content_type', env.get('CONTENT_TYPE'))
        if headers and 'Content-Type' in headers:
            content_type = headers['Content-Type']
        if content_type is not None:
            kw['content_type'] = content_type
        environ_add_POST(env, POST, content_type=content_type)
        obj = cls(env, **kw)
        if headers is not None:
            obj.headers.update(headers)
        return obj

class LegacyRequest(BaseRequest):
    uscript_name = upath_property('SCRIPT_NAME')
    upath_info = upath_property('PATH_INFO')

    def encget(self, key, default=NoDefault, encattr=None):
        val = self.environ.get(key, default)
        if val is NoDefault:
            raise KeyError(key)
        if val is default:
            return default
        return val

class AdhocAttrMixin(object):
    _setattr_stacklevel = 3

    def __setattr__(self, attr, value, DEFAULT=object()):
        if (getattr(self.__class__, attr, DEFAULT) is not DEFAULT or
                    attr.startswith('_')):
            object.__setattr__(self, attr, value)
        else:
            self.environ.setdefault('webob.adhoc_attrs', {})[attr] = value

    def __getattr__(self, attr, DEFAULT=object()):
        try:
            return self.environ['webob.adhoc_attrs'][attr]
        except KeyError:
            raise AttributeError(attr)

    def __delattr__(self, attr, DEFAULT=object()):
        if getattr(self.__class__, attr, DEFAULT) is not DEFAULT:
            return object.__delattr__(self, attr)
        try:
            del self.environ['webob.adhoc_attrs'][attr]
        except KeyError:
            raise AttributeError(attr)

class Request(AdhocAttrMixin, BaseRequest):
    """ The default request implementation """

def environ_from_url(path):
    if SCHEME_RE.search(path):
        scheme, netloc, path, qs, fragment = urlparse.urlsplit(path)
        if fragment:
            raise TypeError("Path cannot contain a fragment (%r)" % fragment)
        if qs:
            path += '?' + qs
        if ':' not in netloc:
            if scheme == 'http':
                netloc += ':80'
            elif scheme == 'https':
                netloc += ':443'
            else:
                raise TypeError("Unknown scheme: %r" % scheme)
    else:
        scheme = 'http'
        netloc = 'localhost:80'
    if path and '?' in path:
        path_info, query_string = path.split('?', 1)
        path_info = url_unquote(path_info)
    else:
        path_info = url_unquote(path)
        query_string = ''
    env = {
        'REQUEST_METHOD': 'GET',
        'SCRIPT_NAME': '',
        'PATH_INFO': path_info or '',
        'QUERY_STRING': query_string,
        'SERVER_NAME': netloc.split(':')[0],
        'SERVER_PORT': netloc.split(':')[1],
        'HTTP_HOST': netloc,
        'SERVER_PROTOCOL': 'HTTP/1.0',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': scheme,
        'wsgi.input': io.BytesIO(),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        #'webob.is_body_seekable': True,
    }
    return env


def environ_add_POST(env, data, content_type=None):
    if data is None:
        return
    elif isinstance(data, text_type): # pragma: no cover
        data = data.encode('ascii')
    if env['REQUEST_METHOD'] not in ('POST', 'PUT'):
        env['REQUEST_METHOD'] = 'POST'
    has_files = False
    if hasattr(data, 'items'):
        data = list(data.items())
        for k, v in data:
            if isinstance(v, (tuple, list)):
                has_files = True
                break
    if content_type is None:
        if has_files:
            content_type = 'multipart/form-data'
        else:
            content_type = 'application/x-www-form-urlencoded'
    if content_type.startswith('multipart/form-data'):
        if not isinstance(data, bytes):
            content_type, data = _encode_multipart(data, content_type)
    elif content_type.startswith('application/x-www-form-urlencoded'):
        if has_files:
            raise ValueError('Submiting files is not allowed for'
                             ' content type `%s`' % content_type)
        if not isinstance(data, bytes):
            data = url_encode(data)
    else:
        if not isinstance(data, bytes):
            raise ValueError('Please provide `POST` data as string'
                             ' for content type `%s`' % content_type)
    data = bytes_(data, 'utf8')
    env['wsgi.input'] = io.BytesIO(data)
    env['webob.is_body_seekable'] = True
    env['CONTENT_LENGTH'] = str(len(data))
    env['CONTENT_TYPE'] = content_type



#########################
## Helper classes and monkeypatching
#########################

class DisconnectionError(IOError):
    pass


class LimitedLengthFile(io.RawIOBase):
    def __init__(self, file, maxlen):
        self.file = file
        self.maxlen = maxlen
        self.remaining = maxlen

    def __repr__(self):
        return '<%s(%r, maxlen=%s)>' % (
            self.__class__.__name__,
            self.file,
            self.maxlen
        )

    def fileno(self):
        return self.file.fileno()

    @staticmethod
    def readable():
        return True

    def readinto(self, buff):
        if not self.remaining:
            return 0
        sz0 = min(len(buff), self.remaining)
        data = self.file.read(sz0)
        sz = len(data)
        self.remaining -= sz
        #if not data:
        if sz < sz0 and self.remaining:
            raise DisconnectionError(
                "The client disconnected while sending the POST/PUT body "
                + "(%d more bytes were expected)" % self.remaining
            )
        buff[:sz] = data
        return sz


def _cgi_FieldStorage__repr__patch(self):
    """ monkey patch for FieldStorage.__repr__

    Unbelievably, the default __repr__ on FieldStorage reads
    the entire file content instead of being sane about it.
    This is a simple replacement that doesn't do that
    """
    if self.file:
        return "FieldStorage(%r, %r)" % (self.name, self.filename)
    return "FieldStorage(%r, %r, %r)" % (self.name, self.filename, self.value)

cgi.FieldStorage.__repr__ = _cgi_FieldStorage__repr__patch

class FakeCGIBody(io.RawIOBase):
    def __init__(self, vars, content_type):
        if content_type.startswith('multipart/form-data'):
            if not _get_multipart_boundary(content_type):
                raise ValueError('Content-type: %r does not contain boundary'
                            % content_type)
        self.vars = vars
        self.content_type = content_type
        self.file = None

    def __repr__(self):
        inner = repr(self.vars)
        if len(inner) > 20:
            inner = inner[:15] + '...' + inner[-5:]
        return '<%s at 0x%x viewing %s>' % (
            self.__class__.__name__,
            abs(id(self)), inner)

    def fileno(self):
        return None

    @staticmethod
    def readable():
        return True

    def readinto(self, buff):
        if self.file is None:
            if self.content_type.startswith(
                'application/x-www-form-urlencoded'):
                data = '&'.join(
                    '%s=%s' % (quote_plus(bytes_(k, 'utf8')), quote_plus(bytes_(v, 'utf8')))
                    for k,v in self.vars.items()
                )
                self.file = io.BytesIO(bytes_(data))
            elif self.content_type.startswith('multipart/form-data'):
                self.file = _encode_multipart(
                    self.vars.items(),
                    self.content_type,
                    fout=io.BytesIO()
                )[1]
                self.file.seek(0)
            else:
                assert 0, ('Bad content type: %r' % self.content_type)
        return self.file.readinto(buff)


def _get_multipart_boundary(ctype):
    m = re.search(r'boundary=([^ ]+)', ctype, re.I)
    if m:
        return native_(m.group(1).strip('"'))


def _encode_multipart(vars, content_type, fout=None):
    """Encode a multipart request body into a string"""
    f = fout or io.BytesIO()
    w = f.write
    wt = lambda t: f.write(t.encode('utf8'))
    CRLF = b'\r\n'
    boundary = _get_multipart_boundary(content_type)
    if not boundary:
        boundary = native_(binascii.hexlify(os.urandom(10)))
        content_type += ('; boundary=%s' % boundary)
    for name, value in vars:
        w(b'--')
        wt(boundary)
        w(CRLF)
        assert name is not None, 'Value associated with no name: %r' % value
        wt('Content-Disposition: form-data; name="%s"' % name)
        filename = None
        if getattr(value, 'filename', None):
            filename = value.filename
        elif isinstance(value, (list, tuple)):
            filename, value = value
            if hasattr(value, 'read'):
                value = value.read()

        if filename is not None:
            wt('; filename="%s"' % filename)
            mime_type = mimetypes.guess_type(filename)[0]
        else:
            mime_type = None

        w(CRLF)

        # TODO: should handle value.disposition_options
        if getattr(value, 'type', None):
            wt('Content-type: %s' % value.type)
            if value.type_options:
                for ct_name, ct_value in sorted(value.type_options.items()):
                    wt('; %s="%s"' % (ct_name, ct_value))
            w(CRLF)
        elif mime_type:
            wt('Content-type: %s' % mime_type)
            w(CRLF)
        w(CRLF)
        if hasattr(value, 'value'):
            value = value.value
        if isinstance(value, bytes):
            w(value)
        else:
            wt(value)
        w(CRLF)
    wt('--%s--' % boundary)
    if fout:
        return content_type, fout
    else:
        return content_type, f.getvalue()

def detect_charset(ctype):
    m = CHARSET_RE.search(ctype)
    if m:
        return m.group(1).strip('"').strip()

def _is_utf8(charset):
    if not charset:
        return True
    else:
        return charset.lower().replace('-', '') == 'utf8'


class Transcoder(object):
    def __init__(self, charset, errors='strict'):
        self.charset = charset # source charset
        self.errors = errors # unicode errors
        self._trans = lambda b: b.decode(charset, errors).encode('utf8')

    def transcode_query(self, q):
        if PY3: # pragma: no cover
            q_orig = q
            if '=' not in q:
                # this doesn't look like a form submission
                return q_orig
            q = list(parse_qsl_text(q, self.charset))
            return url_encode(q)
        else:
            q_orig = q
            if '=' not in q:
                # this doesn't look like a form submission
                return q_orig
            q = urlparse.parse_qsl(q, self.charset)
            t = self._trans
            q = [(t(k), t(v)) for k,v in q]
            return url_encode(q)

    def transcode_fs(self, fs, content_type):
        # transcode FieldStorage
        if PY3: # pragma: no cover
            decode = lambda b: b
        else:
            decode = lambda b: b.decode(self.charset, self.errors)
        data = []
        for field in fs.list or ():
            field.name = decode(field.name)
            if field.filename:
                field.filename = decode(field.filename)
                data.append((field.name, field))
            else:
                data.append((field.name, decode(field.value)))

        # TODO: transcode big requests to temp file
        content_type, fout = _encode_multipart(
            data,
            content_type,
            fout=io.BytesIO()
        )
        return fout

# TODO: remove in 1.4
for _name in 'GET POST params cookies'.split():
    _str_name = 'str_'+_name
    _prop = deprecated_property(
        None, _str_name,
        "disabled starting WebOb 1.2, use %s instead" % _name, '1.2')
    setattr(BaseRequest, _str_name, _prop)

########NEW FILE########
__FILENAME__ = response
from base64 import b64encode
from datetime import (
    datetime,
    timedelta,
    )
from hashlib import md5
import re
import struct
import zlib
try:
    import simplejson as json
except ImportError:
    import json

from webob.byterange import ContentRange

from webob.cachecontrol import (
    CacheControl,
    serialize_cache_control,
    )

from webob.compat import (
    PY3,
    bytes_,
    native_,
    text_type,
    url_quote,
    urlparse,
    )

from webob.cookies import (
    Cookie,
    Morsel,
    )

from webob.datetime_utils import (
    parse_date_delta,
    serialize_date_delta,
    timedelta_to_seconds,
    )

from webob.descriptors import (
    CHARSET_RE,
    SCHEME_RE,
    converter,
    date_header,
    header_getter,
    list_header,
    parse_auth,
    parse_content_range,
    parse_etag_response,
    parse_int,
    parse_int_safe,
    serialize_auth,
    serialize_content_range,
    serialize_etag_response,
    serialize_int,
    )

from webob.headers import ResponseHeaders
from webob.request import BaseRequest
from webob.util import status_reasons, status_generic_reasons

__all__ = ['Response']

_PARAM_RE = re.compile(r'([a-z0-9]+)=(?:"([^"]*)"|([a-z0-9_.-]*))', re.I)
_OK_PARAM_RE = re.compile(r'^[a-z0-9_.-]+$', re.I)

_gzip_header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff'

class Response(object):
    """
        Represents a WSGI response
    """

    default_content_type = 'text/html'
    default_charset = 'UTF-8' # TODO: deprecate
    unicode_errors = 'strict' # TODO: deprecate (why would response body have errors?)
    default_conditional_response = False
    request = None
    environ = None

    #
    # __init__, from_file, copy
    #

    def __init__(self, body=None, status=None, headerlist=None, app_iter=None,
                 content_type=None, conditional_response=None,
                 **kw):
        if app_iter is None and body is None and ('json_body' in kw or 'json' in kw):
            if 'json_body' in kw:
                json_body = kw.pop('json_body')
            else:
                json_body = kw.pop('json')
            body = json.dumps(json_body, separators=(',', ':'))
            if content_type is None:
                content_type = 'application/json'
        if app_iter is None:
            if body is None:
                body = b''
        elif body is not None:
            raise TypeError(
                "You may only give one of the body and app_iter arguments")
        if status is None:
            self._status = '200 OK'
        else:
            self.status = status
        if headerlist is None:
            self._headerlist = []
        else:
            self._headerlist = headerlist
        self._headers = None
        if content_type is None:
            content_type = self.default_content_type
        charset = None
        if 'charset' in kw:
            charset = kw.pop('charset')
        elif self.default_charset:
            if (content_type
                and 'charset=' not in content_type
                and (content_type == 'text/html'
                    or content_type.startswith('text/')
                    or content_type.startswith('application/xml')
                    or content_type.startswith('application/json')
                    or (content_type.startswith('application/')
                         and (content_type.endswith('+xml') or content_type.endswith('+json'))))):
                charset = self.default_charset
        if content_type and charset:
            content_type += '; charset=' + charset
        elif self._headerlist and charset:
            self.charset = charset
        if not self._headerlist and content_type:
            self._headerlist.append(('Content-Type', content_type))
        if conditional_response is None:
            self.conditional_response = self.default_conditional_response
        else:
            self.conditional_response = bool(conditional_response)
        if app_iter is None:
            if isinstance(body, text_type):
                if charset is None:
                    raise TypeError(
                        "You cannot set the body to a text value without a "
                        "charset")
                body = body.encode(charset)
            app_iter = [body]
            if headerlist is None:
                self._headerlist.append(('Content-Length', str(len(body))))
            else:
                self.headers['Content-Length'] = str(len(body))
        self._app_iter = app_iter
        for name, value in kw.items():
            if not hasattr(self.__class__, name):
                # Not a basic attribute
                raise TypeError(
                    "Unexpected keyword: %s=%r" % (name, value))
            setattr(self, name, value)


    @classmethod
    def from_file(cls, fp):
        """Reads a response from a file-like object (it must implement
        ``.read(size)`` and ``.readline()``).

        It will read up to the end of the response, not the end of the
        file.

        This reads the response as represented by ``str(resp)``; it
        may not read every valid HTTP response properly.  Responses
        must have a ``Content-Length``"""
        headerlist = []
        status = fp.readline().strip()
        is_text = isinstance(status, text_type)
        if is_text:
            _colon = ':'
        else:
            _colon = b':'
        while 1:
            line = fp.readline().strip()
            if not line:
                # end of headers
                break
            try:
                header_name, value = line.split(_colon, 1)
            except ValueError:
                raise ValueError('Bad header line: %r' % line)
            value = value.strip()
            if not is_text:
                header_name = header_name.decode('utf-8')
                value = value.decode('utf-8')
            headerlist.append((header_name, value))
        r = cls(
            status=status,
            headerlist=headerlist,
            app_iter=(),
        )
        body = fp.read(r.content_length or 0)
        if is_text:
            r.text = body
        else:
            r.body = body
        return r

    def copy(self):
        """Makes a copy of the response"""
        # we need to do this for app_iter to be reusable
        app_iter = list(self._app_iter)
        iter_close(self._app_iter)
        # and this to make sure app_iter instances are different
        self._app_iter = list(app_iter)
        return self.__class__(
            content_type=False,
            status=self._status,
            headerlist=self._headerlist[:],
            app_iter=app_iter,
            conditional_response=self.conditional_response)


    #
    # __repr__, __str__
    #

    def __repr__(self):
        return '<%s at 0x%x %s>' % (self.__class__.__name__, abs(id(self)),
                                    self.status)

    def __str__(self, skip_body=False):
        parts = [self.status]
        if not skip_body:
            # Force enumeration of the body (to set content-length)
            self.body
        parts += map('%s: %s'.__mod__, self.headerlist)
        if not skip_body and self.body:
            parts += ['', self.text if PY3 else self.body]
        return '\n'.join(parts)

    #
    # status, status_code/status_int
    #

    def _status__get(self):
        """
        The status string
        """
        return self._status

    def _status__set(self, value):
        if isinstance(value, int):
            self.status_code = value
            return
        if PY3: # pragma: no cover
            if isinstance(value, bytes):
                value = value.decode('ascii')
        elif isinstance(value, text_type):
            value = value.encode('ascii')
        if not isinstance(value, str):
            raise TypeError(
                "You must set status to a string or integer (not %s)"
                % type(value))
        if ' ' not in value:
             try:
                value += ' ' + status_reasons[int(value)]
             except KeyError:
                value += ' ' + status_generic_reasons[int(value) // 100]
        self._status = value

    status = property(_status__get, _status__set, doc=_status__get.__doc__)

    def _status_code__get(self):
        """
        The status as an integer
        """
        return int(self._status.split()[0])

    def _status_code__set(self, code):
        try:
            self._status = '%d %s' % (code, status_reasons[code])
        except KeyError:
            self._status = '%d %s' % (code, status_generic_reasons[code // 100])

    status_code = status_int = property(_status_code__get, _status_code__set,
                           doc=_status_code__get.__doc__)


    #
    # headerslist, headers
    #

    def _headerlist__get(self):
        """
        The list of response headers
        """
        return self._headerlist

    def _headerlist__set(self, value):
        self._headers = None
        if not isinstance(value, list):
            if hasattr(value, 'items'):
                value = value.items()
            value = list(value)
        self._headerlist = value

    def _headerlist__del(self):
        self.headerlist = []

    headerlist = property(_headerlist__get, _headerlist__set,
                          _headerlist__del, doc=_headerlist__get.__doc__)

    def _headers__get(self):
        """
        The headers in a dictionary-like object
        """
        if self._headers is None:
            self._headers = ResponseHeaders.view_list(self.headerlist)
        return self._headers

    def _headers__set(self, value):
        if hasattr(value, 'items'):
            value = value.items()
        self.headerlist = value
        self._headers = None

    headers = property(_headers__get, _headers__set, doc=_headers__get.__doc__)


    #
    # body
    #

    def _body__get(self):
        """
        The body of the response, as a ``str``.  This will read in the
        entire app_iter if necessary.
        """
        app_iter = self._app_iter
#         try:
#             if len(app_iter) == 1:
#                 return app_iter[0]
#         except:
#             pass
        if isinstance(app_iter, list) and len(app_iter) == 1:
            return app_iter[0]
        if app_iter is None:
            raise AttributeError("No body has been set")
        try:
            body = b''.join(app_iter)
        finally:
            iter_close(app_iter)
        if isinstance(body, text_type):
            raise _error_unicode_in_app_iter(app_iter, body)
        self._app_iter = [body]
        if len(body) == 0:
            # if body-length is zero, we assume it's a HEAD response and
            # leave content_length alone
            pass # pragma: no cover (no idea why necessary, it's hit)
        elif self.content_length is None:
            self.content_length = len(body)
        elif self.content_length != len(body):
            raise AssertionError(
                "Content-Length is different from actual app_iter length "
                "(%r!=%r)"
                % (self.content_length, len(body))
            )
        return body

    def _body__set(self, value=b''):
        if not isinstance(value, bytes):
            if isinstance(value, text_type):
                msg = ("You cannot set Response.body to a text object "
                       "(use Response.text)")
            else:
                msg = ("You can only set the body to a binary type (not %s)" %
                       type(value))
            raise TypeError(msg)
        if self._app_iter is not None:
            self.content_md5 = None
        self._app_iter = [value]
        self.content_length = len(value)

#     def _body__del(self):
#         self.body = ''
#         #self.content_length = None

    body = property(_body__get, _body__set, _body__set)

    def _json_body__get(self):
        """Access the body of the response as JSON"""
        # Note: UTF-8 is a content-type specific default for JSON:
        return json.loads(self.body.decode(self.charset or 'UTF-8'))

    def _json_body__set(self, value):
        self.body = json.dumps(value, separators=(',', ':')).encode(self.charset or 'UTF-8')

    def _json_body__del(self):
        del self.body

    json = json_body = property(_json_body__get, _json_body__set, _json_body__del)


    #
    # text, unicode_body, ubody
    #

    def _text__get(self):
        """
        Get/set the text value of the body (using the charset of the
        Content-Type)
        """
        if not self.charset:
            raise AttributeError(
                "You cannot access Response.text unless charset is set")
        body = self.body
        return body.decode(self.charset, self.unicode_errors)

    def _text__set(self, value):
        if not self.charset:
            raise AttributeError(
                "You cannot access Response.text unless charset is set")
        if not isinstance(value, text_type):
            raise TypeError(
                "You can only set Response.text to a unicode string "
                "(not %s)" % type(value))
        self.body = value.encode(self.charset)

    def _text__del(self):
        del self.body

    text = property(_text__get, _text__set, _text__del, doc=_text__get.__doc__)

    unicode_body = ubody = property(_text__get, _text__set, _text__del,
        "Deprecated alias for .text")

    #
    # body_file, write(text)
    #

    def _body_file__get(self):
        """
        A file-like object that can be used to write to the
        body.  If you passed in a list app_iter, that app_iter will be
        modified by writes.
        """
        return ResponseBodyFile(self)

    def _body_file__set(self, file):
        self.app_iter = iter_file(file)

    def _body_file__del(self):
        del self.body

    body_file = property(_body_file__get, _body_file__set, _body_file__del,
                         doc=_body_file__get.__doc__)

    def write(self, text):
        if not isinstance(text, bytes):
            if not isinstance(text, text_type):
                msg = "You can only write str to a Response.body_file, not %s"
                raise TypeError(msg % type(text))
            if not self.charset:
                msg = ("You can only write text to Response if charset has "
                       "been set")
                raise TypeError(msg)
            text = text.encode(self.charset)
        app_iter = self._app_iter
        if not isinstance(app_iter, list):
            try:
                new_app_iter = self._app_iter = list(app_iter)
            finally:
                iter_close(app_iter)
            app_iter = new_app_iter
            self.content_length = sum(len(chunk) for chunk in app_iter)
        app_iter.append(text)
        if self.content_length is not None:
            self.content_length += len(text)



    #
    # app_iter
    #

    def _app_iter__get(self):
        """
        Returns the app_iter of the response.

        If body was set, this will create an app_iter from that body
        (a single-item list)
        """
        return self._app_iter

    def _app_iter__set(self, value):
        if self._app_iter is not None:
            # Undo the automatically-set content-length
            self.content_length = None
            self.content_md5 = None
        self._app_iter = value

    def _app_iter__del(self):
        self._app_iter = []
        self.content_length = None

    app_iter = property(_app_iter__get, _app_iter__set, _app_iter__del,
                        doc=_app_iter__get.__doc__)



    #
    # headers attrs
    #

    allow = list_header('Allow', '14.7')
    # TODO: (maybe) support response.vary += 'something'
    # TODO: same thing for all listy headers
    vary = list_header('Vary', '14.44')

    content_length = converter(
        header_getter('Content-Length', '14.17'),
        parse_int, serialize_int, 'int')

    content_encoding = header_getter('Content-Encoding', '14.11')
    content_language = list_header('Content-Language', '14.12')
    content_location = header_getter('Content-Location', '14.14')
    content_md5 = header_getter('Content-MD5', '14.14')
    content_disposition = header_getter('Content-Disposition', '19.5.1')

    accept_ranges = header_getter('Accept-Ranges', '14.5')
    content_range = converter(
        header_getter('Content-Range', '14.16'),
        parse_content_range, serialize_content_range, 'ContentRange object')

    date = date_header('Date', '14.18')
    expires = date_header('Expires', '14.21')
    last_modified = date_header('Last-Modified', '14.29')

    _etag_raw = header_getter('ETag', '14.19')
    etag = converter(_etag_raw,
        parse_etag_response, serialize_etag_response,
        'Entity tag'
    )
    @property
    def etag_strong(self):
        return parse_etag_response(self._etag_raw, strong=True)

    location = header_getter('Location', '14.30')
    pragma = header_getter('Pragma', '14.32')
    age = converter(
        header_getter('Age', '14.6'),
        parse_int_safe, serialize_int, 'int')

    retry_after = converter(
        header_getter('Retry-After', '14.37'),
        parse_date_delta, serialize_date_delta, 'HTTP date or delta seconds')

    server = header_getter('Server', '14.38')

    # TODO: the standard allows this to be a list of challenges
    www_authenticate = converter(
        header_getter('WWW-Authenticate', '14.47'),
        parse_auth, serialize_auth,
    )


    #
    # charset
    #

    def _charset__get(self):
        """
        Get/set the charset (in the Content-Type)
        """
        header = self.headers.get('Content-Type')
        if not header:
            return None
        match = CHARSET_RE.search(header)
        if match:
            return match.group(1)
        return None

    def _charset__set(self, charset):
        if charset is None:
            del self.charset
            return
        header = self.headers.pop('Content-Type', None)
        if header is None:
            raise AttributeError("You cannot set the charset when no "
                                 "content-type is defined")
        match = CHARSET_RE.search(header)
        if match:
            header = header[:match.start()] + header[match.end():]
        header += '; charset=%s' % charset
        self.headers['Content-Type'] = header

    def _charset__del(self):
        header = self.headers.pop('Content-Type', None)
        if header is None:
            # Don't need to remove anything
            return
        match = CHARSET_RE.search(header)
        if match:
            header = header[:match.start()] + header[match.end():]
        self.headers['Content-Type'] = header

    charset = property(_charset__get, _charset__set, _charset__del,
                       doc=_charset__get.__doc__)


    #
    # content_type
    #

    def _content_type__get(self):
        """
        Get/set the Content-Type header (or None), *without* the
        charset or any parameters.

        If you include parameters (or ``;`` at all) when setting the
        content_type, any existing parameters will be deleted;
        otherwise they will be preserved.
        """
        header = self.headers.get('Content-Type')
        if not header:
            return None
        return header.split(';', 1)[0]

    def _content_type__set(self, value):
        if not value:
            self._content_type__del()
            return
        if ';' not in value:
            header = self.headers.get('Content-Type', '')
            if ';' in header:
                params = header.split(';', 1)[1]
                value += ';' + params
        self.headers['Content-Type'] = value

    def _content_type__del(self):
        self.headers.pop('Content-Type', None)

    content_type = property(_content_type__get, _content_type__set,
                            _content_type__del, doc=_content_type__get.__doc__)


    #
    # content_type_params
    #

    def _content_type_params__get(self):
        """
        A dictionary of all the parameters in the content type.

        (This is not a view, set to change, modifications of the dict would not
        be applied otherwise)
        """
        params = self.headers.get('Content-Type', '')
        if ';' not in params:
            return {}
        params = params.split(';', 1)[1]
        result = {}
        for match in _PARAM_RE.finditer(params):
            result[match.group(1)] = match.group(2) or match.group(3) or ''
        return result

    def _content_type_params__set(self, value_dict):
        if not value_dict:
            del self.content_type_params
            return
        params = []
        for k, v in sorted(value_dict.items()):
            if not _OK_PARAM_RE.search(v):
                v = '"%s"' % v.replace('"', '\\"')
            params.append('; %s=%s' % (k, v))
        ct = self.headers.pop('Content-Type', '').split(';', 1)[0]
        ct += ''.join(params)
        self.headers['Content-Type'] = ct

    def _content_type_params__del(self):
        self.headers['Content-Type'] = self.headers.get(
            'Content-Type', '').split(';', 1)[0]

    content_type_params = property(
        _content_type_params__get,
        _content_type_params__set,
        _content_type_params__del,
        _content_type_params__get.__doc__
    )




    #
    # set_cookie, unset_cookie, delete_cookie, merge_cookies
    #

    def set_cookie(self, key, value='', max_age=None,
                   path='/', domain=None, secure=False, httponly=False,
                   comment=None, expires=None, overwrite=False):
        """
        Set (add) a cookie for the response.

        Arguments are:

        ``key``

           The cookie name.

        ``value``

           The cookie value, which should be a string or ``None``.  If
           ``value`` is ``None``, it's equivalent to calling the
           :meth:`webob.response.Response.unset_cookie` method for this
           cookie key (it effectively deletes the cookie on the client).

        ``max_age``

           An integer representing a number of seconds or ``None``.  If this
           value is an integer, it is used as the ``Max-Age`` of the
           generated cookie.  If ``expires`` is not passed and this value is
           an integer, the ``max_age`` value will also influence the
           ``Expires`` value of the cookie (``Expires`` will be set to now +
           max_age).  If this value is ``None``, the cookie will not have a
           ``Max-Age`` value (unless ``expires`` is also sent).

        ``path``

           A string representing the cookie ``Path`` value.  It defaults to
           ``/``.

        ``domain``

           A string representing the cookie ``Domain``, or ``None``.  If
           domain is ``None``, no ``Domain`` value will be sent in the
           cookie.

        ``secure``

           A boolean.  If it's ``True``, the ``secure`` flag will be sent in
           the cookie, if it's ``False``, the ``secure`` flag will not be
           sent in the cookie.

        ``httponly``

           A boolean.  If it's ``True``, the ``HttpOnly`` flag will be sent
           in the cookie, if it's ``False``, the ``HttpOnly`` flag will not
           be sent in the cookie.

        ``comment``

           A string representing the cookie ``Comment`` value, or ``None``.
           If ``comment`` is ``None``, no ``Comment`` value will be sent in
           the cookie.

        ``expires``

           A ``datetime.timedelta`` object representing an amount of time or
           the value ``None``.  A non-``None`` value is used to generate the
           ``Expires`` value of the generated cookie.  If ``max_age`` is not
           passed, but this value is not ``None``, it will influence the
           ``Max-Age`` header (``Max-Age`` will be 'expires_value -
           datetime.utcnow()').  If this value is ``None``, the ``Expires``
           cookie value will be unset (unless ``max_age`` is also passed).

        ``overwrite``

           If this key is ``True``, before setting the cookie, unset any
           existing cookie.

        """
        if overwrite:
            self.unset_cookie(key, strict=False)
        if value is None: # delete the cookie from the client
            value = ''
            max_age = 0
            expires = timedelta(days=-5)
        elif expires is None and max_age is not None:
            if isinstance(max_age, int):
                max_age = timedelta(seconds=max_age)
            expires = datetime.utcnow() + max_age
        elif max_age is None and expires is not None:
            max_age = expires - datetime.utcnow()
        value = bytes_(value, 'utf8')
        key = bytes_(key, 'utf8')
        m = Morsel(key, value)
        m.path = bytes_(path, 'utf8')
        m.domain = bytes_(domain, 'utf8')
        m.comment = bytes_(comment, 'utf8')
        m.expires = expires
        m.max_age = max_age
        m.secure = secure
        m.httponly = httponly
        self.headerlist.append(('Set-Cookie', m.serialize()))

    def delete_cookie(self, key, path='/', domain=None):
        """
        Delete a cookie from the client.  Note that path and domain must match
        how the cookie was originally set.

        This sets the cookie to the empty string, and max_age=0 so
        that it should expire immediately.
        """
        self.set_cookie(key, None, path=path, domain=domain)

    def unset_cookie(self, key, strict=True):
        """
        Unset a cookie with the given name (remove it from the
        response).
        """
        existing = self.headers.getall('Set-Cookie')
        if not existing and not strict:
            return
        cookies = Cookie()
        for header in existing:
            cookies.load(header)
        if isinstance(key, text_type):
            key = key.encode('utf8')
        if key in cookies:
            del cookies[key]
            del self.headers['Set-Cookie']
            for m in cookies.values():
                self.headerlist.append(('Set-Cookie', m.serialize()))
        elif strict:
            raise KeyError("No cookie has been set with the name %r" % key)


    def merge_cookies(self, resp):
        """Merge the cookies that were set on this response with the
        given `resp` object (which can be any WSGI application).

        If the `resp` is a :class:`webob.Response` object, then the
        other object will be modified in-place.
        """
        if not self.headers.get('Set-Cookie'):
            return resp
        if isinstance(resp, Response):
            for header in self.headers.getall('Set-Cookie'):
                resp.headers.add('Set-Cookie', header)
            return resp
        else:
            c_headers = [h for h in self.headerlist if
                         h[0].lower() == 'set-cookie']
            def repl_app(environ, start_response):
                def repl_start_response(status, headers, exc_info=None):
                    return start_response(status, headers+c_headers,
                                          exc_info=exc_info)
                return resp(environ, repl_start_response)
            return repl_app


    #
    # cache_control
    #

    _cache_control_obj = None

    def _cache_control__get(self):
        """
        Get/set/modify the Cache-Control header (`HTTP spec section 14.9
        <http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.9>`_)
        """
        value = self.headers.get('cache-control', '')
        if self._cache_control_obj is None:
            self._cache_control_obj = CacheControl.parse(
                value, updates_to=self._update_cache_control, type='response')
            self._cache_control_obj.header_value = value
        if self._cache_control_obj.header_value != value:
            new_obj = CacheControl.parse(value, type='response')
            self._cache_control_obj.properties.clear()
            self._cache_control_obj.properties.update(new_obj.properties)
            self._cache_control_obj.header_value = value
        return self._cache_control_obj

    def _cache_control__set(self, value):
        # This actually becomes a copy
        if not value:
            value = ""
        if isinstance(value, dict):
            value = CacheControl(value, 'response')
        if isinstance(value, text_type):
            value = str(value)
        if isinstance(value, str):
            if self._cache_control_obj is None:
                self.headers['Cache-Control'] = value
                return
            value = CacheControl.parse(value, 'response')
        cache = self.cache_control
        cache.properties.clear()
        cache.properties.update(value.properties)

    def _cache_control__del(self):
        self.cache_control = {}

    def _update_cache_control(self, prop_dict):
        value = serialize_cache_control(prop_dict)
        if not value:
            if 'Cache-Control' in self.headers:
                del self.headers['Cache-Control']
        else:
            self.headers['Cache-Control'] = value

    cache_control = property(
        _cache_control__get, _cache_control__set,
        _cache_control__del, doc=_cache_control__get.__doc__)


    #
    # cache_expires
    #

    def _cache_expires(self, seconds=0, **kw):
        """
            Set expiration on this request.  This sets the response to
            expire in the given seconds, and any other attributes are used
            for cache_control (e.g., private=True, etc).
        """
        if seconds is True:
            seconds = 0
        elif isinstance(seconds, timedelta):
            seconds = timedelta_to_seconds(seconds)
        cache_control = self.cache_control
        if seconds is None:
            pass
        elif not seconds:
            # To really expire something, you have to force a
            # bunch of these cache control attributes, and IE may
            # not pay attention to those still so we also set
            # Expires.
            cache_control.no_store = True
            cache_control.no_cache = True
            cache_control.must_revalidate = True
            cache_control.max_age = 0
            cache_control.post_check = 0
            cache_control.pre_check = 0
            self.expires = datetime.utcnow()
            if 'last-modified' not in self.headers:
                self.last_modified = datetime.utcnow()
            self.pragma = 'no-cache'
        else:
            cache_control.properties.clear()
            cache_control.max_age = seconds
            self.expires = datetime.utcnow() + timedelta(seconds=seconds)
            self.pragma = None
        for name, value in kw.items():
            setattr(cache_control, name, value)

    cache_expires = property(lambda self: self._cache_expires, _cache_expires)



    #
    # encode_content, decode_content, md5_etag
    #

    def encode_content(self, encoding='gzip', lazy=False):
        """
        Encode the content with the given encoding (only gzip and
        identity are supported).
        """
        assert encoding in ('identity', 'gzip'), \
               "Unknown encoding: %r" % encoding
        if encoding == 'identity':
            self.decode_content()
            return
        if self.content_encoding == 'gzip':
            return
        if lazy:
            self.app_iter = gzip_app_iter(self._app_iter)
            self.content_length = None
        else:
            self.app_iter = list(gzip_app_iter(self._app_iter))
            self.content_length = sum(map(len, self._app_iter))
        self.content_encoding = 'gzip'

    def decode_content(self):
        content_encoding = self.content_encoding or 'identity'
        if content_encoding == 'identity':
            return
        if content_encoding not in ('gzip', 'deflate'):
            raise ValueError(
                "I don't know how to decode the content %s" % content_encoding)
        if content_encoding == 'gzip':
            from gzip import GzipFile
            from io import BytesIO
            gzip_f = GzipFile(filename='', mode='r', fileobj=BytesIO(self.body))
            self.body = gzip_f.read()
            self.content_encoding = None
            gzip_f.close()
        else:
            # Weird feature: http://bugs.python.org/issue5784
            self.body = zlib.decompress(self.body, -15)
            self.content_encoding = None

    def md5_etag(self, body=None, set_content_md5=False):
        """
        Generate an etag for the response object using an MD5 hash of
        the body (the body parameter, or ``self.body`` if not given)

        Sets ``self.etag``
        If ``set_content_md5`` is True sets ``self.content_md5`` as well
        """
        if body is None:
            body = self.body
        md5_digest = md5(body).digest()
        md5_digest = b64encode(md5_digest)
        md5_digest = md5_digest.replace(b'\n', b'')
        md5_digest = native_(md5_digest)
        self.etag = md5_digest.strip('=')
        if set_content_md5:
            self.content_md5 = md5_digest



    #
    # __call__, conditional_response_app
    #

    def __call__(self, environ, start_response):
        """
        WSGI application interface
        """
        if self.conditional_response:
            return self.conditional_response_app(environ, start_response)
        headerlist = self._abs_headerlist(environ)
        start_response(self.status, headerlist)
        if environ['REQUEST_METHOD'] == 'HEAD':
            # Special case here...
            return EmptyResponse(self._app_iter)
        return self._app_iter

    def _abs_headerlist(self, environ):
        """Returns a headerlist, with the Location header possibly
        made absolute given the request environ.
        """
        headerlist = list(self.headerlist)
        for i, (name, value) in enumerate(headerlist):
            if name.lower() == 'location':
                if SCHEME_RE.search(value):
                    break
                new_location = urlparse.urljoin(_request_uri(environ), value)
                headerlist[i] = (name, new_location)
                break
        return headerlist

    _safe_methods = ('GET', 'HEAD')

    def conditional_response_app(self, environ, start_response):
        """
        Like the normal __call__ interface, but checks conditional headers:

        * If-Modified-Since   (304 Not Modified; only on GET, HEAD)
        * If-None-Match       (304 Not Modified; only on GET, HEAD)
        * Range               (406 Partial Content; only on GET, HEAD)
        """
        req = BaseRequest(environ)
        headerlist = self._abs_headerlist(environ)
        method = environ.get('REQUEST_METHOD', 'GET')
        if method in self._safe_methods:
            status304 = False
            if req.if_none_match and self.etag:
                status304 = self.etag in req.if_none_match
            elif req.if_modified_since and self.last_modified:
                status304 = self.last_modified <= req.if_modified_since
            if status304:
                start_response('304 Not Modified', filter_headers(headerlist))
                return EmptyResponse(self._app_iter)
        if (req.range and self in req.if_range
            and self.content_range is None
            and method in ('HEAD', 'GET')
            and self.status_code == 200
            and self.content_length is not None
        ):
            content_range = req.range.content_range(self.content_length)
            if content_range is None:
                iter_close(self._app_iter)
                body = bytes_("Requested range not satisfiable: %s" % req.range)
                headerlist = [
                    ('Content-Length', str(len(body))),
                    ('Content-Range', str(ContentRange(None, None,
                                                       self.content_length))),
                    ('Content-Type', 'text/plain'),
                ] + filter_headers(headerlist)
                start_response('416 Requested Range Not Satisfiable',
                               headerlist)
                if method == 'HEAD':
                    return ()
                return [body]
            else:
                app_iter = self.app_iter_range(content_range.start,
                                               content_range.stop)
                if app_iter is not None:
                    # the following should be guaranteed by
                    # Range.range_for_length(length)
                    assert content_range.start is not None
                    headerlist = [
                        ('Content-Length',
                         str(content_range.stop - content_range.start)),
                        ('Content-Range', str(content_range)),
                    ] + filter_headers(headerlist, ('content-length',))
                    start_response('206 Partial Content', headerlist)
                    if method == 'HEAD':
                        return EmptyResponse(app_iter)
                    return app_iter

        start_response(self.status, headerlist)
        if method  == 'HEAD':
            return EmptyResponse(self._app_iter)
        return self._app_iter

    def app_iter_range(self, start, stop):
        """
        Return a new app_iter built from the response app_iter, that
        serves up only the given ``start:stop`` range.
        """
        app_iter = self._app_iter
        if hasattr(app_iter, 'app_iter_range'):
            return app_iter.app_iter_range(start, stop)
        return AppIterRange(app_iter, start, stop)


def filter_headers(hlist, remove_headers=('content-length', 'content-type')):
    return [h for h in hlist if (h[0].lower() not in remove_headers)]


def iter_file(file, block_size=1<<18): # 256Kb
    while True:
        data = file.read(block_size)
        if not data:
            break
        yield data

class ResponseBodyFile(object):
    mode = 'wb'
    closed = False

    def __init__(self, response):
        self.response = response
        self.write = response.write

    def __repr__(self):
        return '<body_file for %r>' % self.response

    encoding = property(
        lambda self: self.response.charset,
        doc="The encoding of the file (inherited from response.charset)"
    )

    def writelines(self, seq):
        for item in seq:
            self.write(item)

    def close(self):
        raise NotImplementedError("Response bodies cannot be closed")

    def flush(self):
        pass



class AppIterRange(object):
    """
    Wraps an app_iter, returning just a range of bytes
    """

    def __init__(self, app_iter, start, stop):
        assert start >= 0, "Bad start: %r" % start
        assert stop is None or (stop >= 0 and stop >= start), (
            "Bad stop: %r" % stop)
        self.app_iter = iter(app_iter)
        self._pos = 0 # position in app_iter
        self.start = start
        self.stop = stop

    def __iter__(self):
        return self

    def _skip_start(self):
        start, stop = self.start, self.stop
        for chunk in self.app_iter:
            self._pos += len(chunk)
            if self._pos < start:
                continue
            elif self._pos == start:
                return b''
            else:
                chunk = chunk[start-self._pos:]
                if stop is not None and self._pos > stop:
                    chunk = chunk[:stop-self._pos]
                    assert len(chunk) == stop - start
                return chunk
        else:
            raise StopIteration()


    def next(self):
        if self._pos < self.start:
            # need to skip some leading bytes
            return self._skip_start()
        stop = self.stop
        if stop is not None and self._pos >= stop:
            raise StopIteration

        chunk = next(self.app_iter)
        self._pos += len(chunk)

        if stop is None or self._pos <= stop:
            return chunk
        else:
            return chunk[:stop-self._pos]

    __next__ = next # py3

    def close(self):
        iter_close(self.app_iter)


class EmptyResponse(object):
    """An empty WSGI response.

    An iterator that immediately stops. Optionally provides a close
    method to close an underlying app_iter it replaces.
    """

    def __init__(self, app_iter=None):
        if app_iter is not None and hasattr(app_iter, 'close'):
            self.close = app_iter.close

    def __iter__(self):
        return self

    def __len__(self):
        return 0

    def next(self):
        raise StopIteration()

    __next__ = next # py3

def _request_uri(environ):
    """Like wsgiref.url.request_uri, except eliminates :80 ports

    Return the full request URI"""
    url = environ['wsgi.url_scheme']+'://'

    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME'] + ':' + environ['SERVER_PORT']
    if url.endswith(':80') and environ['wsgi.url_scheme'] == 'http':
        url = url[:-3]
    elif url.endswith(':443') and environ['wsgi.url_scheme'] == 'https':
        url = url[:-4]

    if PY3: # pragma: no cover
        script_name = bytes_(environ.get('SCRIPT_NAME', '/'), 'latin-1')
        path_info = bytes_(environ.get('PATH_INFO', ''), 'latin-1')
    else:
        script_name = environ.get('SCRIPT_NAME', '/')
        path_info = environ.get('PATH_INFO', '')

    url += url_quote(script_name)
    qpath_info = url_quote(path_info)
    if not 'SCRIPT_NAME' in environ:
        url += qpath_info[1:]
    else:
        url += qpath_info
    return url


def iter_close(iter):
    if hasattr(iter, 'close'):
        iter.close()

def gzip_app_iter(app_iter):
    size = 0
    crc = zlib.crc32(b"") & 0xffffffff
    compress = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS,
                                zlib.DEF_MEM_LEVEL, 0)

    yield _gzip_header
    for item in app_iter:
        size += len(item)
        crc = zlib.crc32(item, crc) & 0xffffffff

        # The compress function may return zero length bytes if the input is
        # small enough; it buffers the input for the next iteration or for a
        # flush.
        result = compress.compress(item)
        if result:
            yield result

    # Similarly, flush may also not yield a value.
    result = compress.flush()
    if result:
        yield result
    yield struct.pack("<2L", crc, size & 0xffffffff)

def _error_unicode_in_app_iter(app_iter, body):
    app_iter_repr = repr(app_iter)
    if len(app_iter_repr) > 50:
        app_iter_repr = (
            app_iter_repr[:30] + '...' + app_iter_repr[-10:])
    raise TypeError(
        'An item of the app_iter (%s) was text, causing a '
        'text body: %r' % (app_iter_repr, body))

########NEW FILE########
__FILENAME__ = static
import mimetypes
import os

from webob import exc
from webob.dec import wsgify
from webob.response import Response

__all__ = [
    'FileApp', 'DirectoryApp',
]

mimetypes._winreg = None # do not load mimetypes from windows registry
mimetypes.add_type('text/javascript', '.js') # stdlib default is application/x-javascript
mimetypes.add_type('image/x-icon', '.ico') # not among defaults

BLOCK_SIZE = 1<<16


class FileApp(object):
    """An application that will send the file at the given filename.

    Adds a mime type based on `mimetypes.guess_type()`.
    """

    def __init__(self, filename, **kw):
        self.filename = filename
        content_type, content_encoding = mimetypes.guess_type(filename)
        kw.setdefault('content_type', content_type)
        kw.setdefault('content_encoding', content_encoding)
        kw.setdefault('accept_ranges', 'bytes')
        self.kw = kw
        # Used for testing purpose
        self._open = open

    @wsgify
    def __call__(self, req):
        if req.method not in ('GET', 'HEAD'):
            return exc.HTTPMethodNotAllowed("You cannot %s a file" %
                                            req.method)
        try:
            stat = os.stat(self.filename)
        except (IOError, OSError) as e:
            msg = "Can't open %r: %s" % (self.filename, e)
            return exc.HTTPNotFound(comment=msg)

        try:
            file = self._open(self.filename, 'rb')
        except (IOError, OSError) as e:
            msg = "You are not permitted to view this file (%s)" % e
            return exc.HTTPForbidden(msg)

        if 'wsgi.file_wrapper' in req.environ:
            app_iter = req.environ['wsgi.file_wrapper'](file, BLOCK_SIZE)
        else:
            app_iter = FileIter(file)

        return Response(
            app_iter = app_iter,
            content_length = stat.st_size,
            last_modified = stat.st_mtime,
            #@@ etag
            **self.kw
        ).conditional_response_app


class FileIter(object):
    def __init__(self, file):
        self.file = file

    def app_iter_range(self, seek=None, limit=None, block_size=None):
        """Iter over the content of the file.

        You can set the `seek` parameter to read the file starting from a
        specific position.

        You can set the `limit` parameter to read the file up to specific
        position.

        Finally, you can change the number of bytes read at once by setting the
        `block_size` parameter.
        """

        if block_size is None:
            block_size = BLOCK_SIZE

        if seek:
            self.file.seek(seek)
            if limit is not None:
                limit -= seek
        try:
            while True:
                data = self.file.read(min(block_size, limit)
                                      if limit is not None
                                      else block_size)
                if not data:
                    return
                yield data
                if limit is not None:
                    limit -= len(data)
                    if limit <= 0:
                        return
        finally:
            self.file.close()

    __iter__ = app_iter_range


class DirectoryApp(object):
    """An application that serves up the files in a given directory.

    This will serve index files (by default ``index.html``), or set
    ``index_page=None`` to disable this.  If you set
    ``hide_index_with_redirect=True`` (it defaults to False) then
    requests to, e.g., ``/index.html`` will be redirected to ``/``.

    To customize `FileApp` instances creation (which is what actually
    serves the responses), override the `make_fileapp` method.
    """

    def __init__(self, path, index_page='index.html', hide_index_with_redirect=False,
                 **kw):
        self.path = os.path.abspath(path)
        if not self.path.endswith(os.path.sep):
            self.path += os.path.sep
        if not os.path.isdir(self.path):
            raise IOError(
                "Path does not exist or is not directory: %r" % self.path)
        self.index_page = index_page
        self.hide_index_with_redirect = hide_index_with_redirect
        self.fileapp_kw = kw

    def make_fileapp(self, path):
        return FileApp(path, **self.fileapp_kw)

    @wsgify
    def __call__(self, req):
        path = os.path.abspath(os.path.join(self.path,
                                            req.path_info.lstrip('/')))
        if os.path.isdir(path) and self.index_page:
            return self.index(req, path)
        if (self.index_page and self.hide_index_with_redirect
            and path.endswith(os.path.sep + self.index_page)):
            new_url = req.path_url.rsplit('/', 1)[0]
            new_url += '/'
            if req.query_string:
                new_url += '?' + req.query_string
            return Response(
                status=301,
                location=new_url)
        if not os.path.isfile(path):
            return exc.HTTPNotFound(comment=path)
        elif not path.startswith(self.path):
            return exc.HTTPForbidden()
        else:
            return self.make_fileapp(path)

    def index(self, req, path):
        index_path = os.path.join(path, self.index_page)
        if not os.path.isfile(index_path):
            return exc.HTTPNotFound(comment=index_path)
        if not req.path_info.endswith('/'):
            url = req.path_url + '/'
            if req.query_string:
                url += '?' + req.query_string
            return Response(
                status=301,
                location=url)
        return self.make_fileapp(index_path)

########NEW FILE########
__FILENAME__ = util
import warnings

from webob.compat import (
    escape,
    string_types,
    text_,
    text_type,
    )

from webob.headers import _trans_key

def html_escape(s):
    """HTML-escape a string or object

    This converts any non-string objects passed into it to strings
    (actually, using ``unicode()``).  All values returned are
    non-unicode strings (using ``&#num;`` entities for all non-ASCII
    characters).

    None is treated specially, and returns the empty string.
    """
    if s is None:
        return ''
    __html__ = getattr(s, '__html__', None)
    if __html__ is not None and callable(__html__):
        return s.__html__()
    if not isinstance(s, string_types):
        __unicode__ = getattr(s, '__unicode__', None)
        if __unicode__ is not None and callable(__unicode__):
            s = s.__unicode__()
        else:
            s = str(s)
    s = escape(s, True)
    if isinstance(s, text_type):
        s = s.encode('ascii', 'xmlcharrefreplace')
    return text_(s)

def header_docstring(header, rfc_section):
    if header.isupper():
        header = _trans_key(header)
    major_section = rfc_section.split('.')[0]
    link = 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec%s.html#sec%s' % (
        major_section, rfc_section)
    return "Gets and sets the ``%s`` header (`HTTP spec section %s <%s>`_)." % (
        header, rfc_section, link)


def warn_deprecation(text, version, stacklevel):
    # version specifies when to start raising exceptions instead of warnings
    if version in ('1.2', '1.3', '1.4'):
        raise DeprecationWarning(text)
    else:
        cls = DeprecationWarning
    warnings.warn(text, cls, stacklevel=stacklevel+1)

status_reasons = {
    # Status Codes
    # Informational
    100: 'Continue',
    101: 'Switching Protocols',
    102: 'Processing',

    # Successful
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    207: 'Multi Status',
    226: 'IM Used',

    # Redirection
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',

    # Client Error
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: "I'm a teapot",
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    426: 'Upgrade Required',
    428: 'Precondition Required',
    429: 'Too Many Requests',
    451: 'Unavailable for Legal Reasons',
    431: 'Request Header Fields Too Large',

    # Server Error
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    507: 'Insufficient Storage',
    510: 'Not Extended',
    511: 'Network Authentication Required',
}

# generic class responses as per RFC2616
status_generic_reasons = {
    1: 'Continue',
    2: 'Success',
    3: 'Multiple Choices',
    4: 'Unknown Client Error',
    5: 'Unknown Server Error',
}

try:
    # py3.3+ have native comparison support
    from hmac import compare_digest
except ImportError:
    compare_digest = None

def strings_differ(string1, string2):
    """Check whether two strings differ while avoiding timing attacks.

    This function returns True if the given strings differ and False
    if they are equal.  It's careful not to leak information about *where*
    they differ as a result of its running time, which can be very important
    to avoid certain timing-related crypto attacks:

        http://seb.dbzteam.org/crypto/python-oauth-timing-hmac.pdf

    """
    len_eq = len(string1) == len(string2)
    if len_eq:
        invalid_bits = 0
        left = string1
    else:
        invalid_bits = 1
        left = string2
    right = string2

    if compare_digest is not None: # pragma: nocover (Python 3.3+ only)
        invalid_bits += not compare_digest(left, right)
    else:
        for a, b in zip(left, right):
            invalid_bits += a != b
    return invalid_bits != 0

########NEW FILE########
