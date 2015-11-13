__FILENAME__ = read
from fuqit.web import render, error
from config import db

def run(web):
    post_id = web.sub_path[1:]

    if not post_id: return error(404, "Not Found")

    web.post = db.get('post', by_id=post_id)

    if web.post:
        return render('show_post.html', web)
    else:
        return error(404, "Not Found")


########NEW FILE########
__FILENAME__ = write
from fuqit.web import render, redirect
from config import db


def GET(web):
    return render("write_post.html", web)

def POST(web):
    db.insert('post',
              title=web.params['title'],
              content=web.params['content'])


    return redirect("/")

########NEW FILE########
__FILENAME__ = config
from fuqit import data

db = data.database(dbn='sqlite', db='data.sqlite3')
allowed_referer = '.*'
default_mtype = 'text/html'
static_dir = '/static/'


########NEW FILE########
__FILENAME__ = dbtest
from fuqit.web import render, redirect
from config import db

def GET(web):
    """
    This shows how to do a simple database setup. You can also just
    import the db inside the .html file if you want and don't need
    to go to a handler first.
    """
    if web.sub_path == '/delete':
        db.delete('test', where='id = $id', vars=web.params)

    return render("showdb.html", web)

def POST(web):
    db.insert('test', title=web.params['title'])
    return redirect("/dbtest")


########NEW FILE########
__FILENAME__ = form


def run(web):
    headers = [(k,v) for k,v in web.headers.items()]

    result = "HEADERS: %r\nPARAMS: %r\nPATH: %r\nMETHOD: %r" % (
        headers, web.params, web.path, web.method)

    return result, 200, {'content-type': 'text/plain'}



########NEW FILE########
__FILENAME__ = stuff


def test(instuff):
    return "OUT %r" % instuff


########NEW FILE########
__FILENAME__ = test
from fuqit import forms
from fuqit.web import render


def GET(web):
    """
    Demonstrates using the session and also how to then render another
    thing seamlessly.  Just call web.app.render() and it'll do all the
    resolving gear again, so one method works on statics, modules, jinja2
    just like you accessed it from a browser.
    """
    web.form = forms.read(web, reset=False)

    if web.form.reset:
        web.session['count'] = 1
    else:
        web.session['count'] = web.session.get('count', 1) + 1

    return render('renderme.html', web)

########NEW FILE########
__FILENAME__ = config
from fuqit import data

db = data.database(dbn='sqlite', db='data.sqlite3')
allowed_referer = '.*'
default_mtype = 'text/html'
static_dir = '/static/'


########NEW FILE########
__FILENAME__ = commands
# Fuqit Web Framework
# Copyright (C) 2013  Zed A. Shaw
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from modargs import args
import fuqit
import os
import sys

def help_command(**options):
    """
    Prints out help for the commands. 

    fuqit help

    You can get help for one command with:

    fuqit help -for STR
    """

    if "for" in options:
        help_text = args.help_for_command(fuqit.commands, options['for'])

        if help_text:
            print help_text
        else:
            args.invalid_command_message(fuqit.commands, exit_on_error=True)
    else:
        print "Available commands:\n"
        print ", ".join(args.available_commands(fuqit.commands))
        print "\nUse fuqit help -for <command> to find out more."


def init_command(into=None):
    """
    Initializes a fuqit app, default directory is 'app'.

    fuqit init -into myapp
    """

    if not os.path.exists(into):

        for newdir in ['/', '/app', '/app/static']:
            os.mkdir(into + newdir)

        open(into + '/app/__init__.py', 'w').close()
        with open(into + '/config.py', 'w') as config:
            config.write("from fuqit import data\n\ndb = data.database(dbn='sqlite', db='data.sqlite3')")

        with open(into + '/app/index.html', 'w') as index:
            index.write('Put your crap in %s/app and hit rephresh.' % into)

        print "Your app is ready for hackings in %s" % into

    else:
        print "The app directory already exists. Try:\n\nfuqit init -into [SOMEDIR]"


def run_command(host='127.0.0.1', port=8000, config_module='config', app='app',
                debug=True, chroot="."):
    """
    Runs a fuqit server.

    fuqit run -host 127.0.0.1 -port 8000 -referer http:// -app app -debug True \
            -chroot .

    NOTE: In run mode it's meant for developers, so -chroot just does a cd
    to the directory.  In server mode it actually chroots there.  It also
    adds the chroot path to the python syspath.

    """
    from fuqit import server

    sys.path.append(os.path.realpath(chroot))
    os.chdir(chroot)
    
    server.run_server(host=host,
                            port=port,
                            config_module=config_module,
                            app=app,
                            debug=debug)


def start_command(host='127.0.0.1', port=8000, referer='http://', app='app',
                   debug=True, chroot="."):
    """
    Runs the fuqit server as a daemon.

    fuqit start -host 127.0.0.1 -port 8000 -referer http:// -app app -debug True
    """

   
def stop_command():
    """
    Stops a running fuqit daemon.

    fuqit stop
    """


def status_command():
    """
    Tells you if a running fuqit service is running or not.

    fuqit status
    """




########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
"""
General Utilities taken from web.py for use with the db.py file.
"""

__all__ = [
  "storage", "storify", 
  "iters", 
  "safeunicode", "safestr",
  "iterbetter",
  "threadeddict",
]

import itertools
from threading import local as threadlocal

class storage(dict):
    """
    A storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.
    
        >>> o = storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        Traceback (most recent call last):
            ...
        AttributeError: 'a'
    
    """
    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __setattr__(self, key, value): 
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __repr__(self):     
        return '<storage ' + dict.__repr__(self) + '>'

def storify(mapping, *requireds, **defaults):
    """
    Creates a `storage` object from dictionary `mapping`, raising `KeyError` if
    d doesn't have all of the keys in `requireds` and using the default 
    values for keys found in `defaults`.

    For example, `storify({'a':1, 'c':3}, b=2, c=0)` will return the equivalent of
    `storage({'a':1, 'b':2, 'c':3})`.
    
    If a `storify` value is a list (e.g. multiple values in a form submission), 
    `storify` returns the last element of the list, unless the key appears in 
    `defaults` as a list. Thus:
    
        >>> storify({'a':[1, 2]}).a
        2
        >>> storify({'a':[1, 2]}, a=[]).a
        [1, 2]
        >>> storify({'a':1}, a=[]).a
        [1]
        >>> storify({}, a=[]).a
        []
    
    Similarly, if the value has a `value` attribute, `storify will return _its_
    value, unless the key appears in `defaults` as a dictionary.
    
        >>> storify({'a':storage(value=1)}).a
        1
        >>> storify({'a':storage(value=1)}, a={}).a
        <storage {'value': 1}>
        >>> storify({}, a={}).a
        {}
        
    Optionally, keyword parameter `_unicode` can be passed to convert all values to unicode.
    
        >>> storify({'x': 'a'}, _unicode=True)
        <storage {'x': u'a'}>
        >>> storify({'x': storage(value='a')}, x={}, _unicode=True)
        <storage {'x': <storage {'value': 'a'}>}>
        >>> storify({'x': storage(value='a')}, _unicode=True)
        <storage {'x': u'a'}>
    """
    _unicode = defaults.pop('_unicode', False)

    # if _unicode is callable object, use it convert a string to unicode.
    to_unicode = safeunicode
    if _unicode is not False and hasattr(_unicode, "__call__"):
        to_unicode = _unicode
    
    def unicodify(s):
        if _unicode and isinstance(s, str): return to_unicode(s)
        else: return s
        
    def getvalue(x):
        if hasattr(x, 'file') and hasattr(x, 'value'):
            return x.value
        elif hasattr(x, 'value'):
            return unicodify(x.value)
        else:
            return unicodify(x)
    
    stor = storage()
    for key in requireds + tuple(mapping.keys()):
        value = mapping[key]
        if isinstance(value, list):
            if isinstance(defaults.get(key), list):
                value = [getvalue(x) for x in value]
            else:
                value = value[-1]
        if not isinstance(defaults.get(key), dict):
            value = getvalue(value)
        if isinstance(defaults.get(key), list) and not isinstance(value, list):
            value = [value]
        setattr(stor, key, value)

    for (key, value) in defaults.iteritems():
        result = value
        if hasattr(stor, key): 
            result = stor[key]
        if value == () and not isinstance(result, tuple): 
            result = (result,)
        setattr(stor, key, result)
    
    return stor

iters = (list, tuple, set, frozenset)

def safeunicode(obj, encoding='utf-8'):
    r"""
    Converts any given object to unicode string.
    
        >>> safeunicode('hello')
        u'hello'
        >>> safeunicode(2)
        u'2'
        >>> safeunicode('\xe1\x88\xb4')
        u'\u1234'
    """
    t = type(obj)
    if t is unicode:
        return obj
    elif t is str:
        return obj.decode(encoding)
    elif t in [int, float, bool]:
        return unicode(obj)
    elif hasattr(obj, '__unicode__') or isinstance(obj, unicode):
        return unicode(obj)
    else:
        return str(obj).decode(encoding)
    
def safestr(obj, encoding='utf-8'):
    r"""
    Converts any given object to utf-8 encoded string. 
    
        >>> safestr('hello')
        'hello'
        >>> safestr(u'\u1234')
        '\xe1\x88\xb4'
        >>> safestr(2)
        '2'
    """
    if isinstance(obj, unicode):
        return obj.encode(encoding)
    elif isinstance(obj, str):
        return obj
    elif hasattr(obj, 'next'): # iterator
        return itertools.imap(safestr, obj)
    else:
        return str(obj)

class iterbetter:
    """
    Returns an object that can be used as an iterator 
    but can also be used via __getitem__ (although it 
    cannot go backwards -- that is, you cannot request 
    `iterbetter[0]` after requesting `iterbetter[1]`).
    
        >>> import itertools
        >>> c = iterbetter(itertools.count())
        >>> c[1]
        1
        >>> c[5]
        5
        >>> c[3]
        Traceback (most recent call last):
            ...
        IndexError: already passed 3

    For boolean test, iterbetter peeps at first value in the itertor without effecting the iteration.

        >>> c = iterbetter(iter(range(5)))
        >>> bool(c)
        True
        >>> list(c)
        [0, 1, 2, 3, 4]
        >>> c = iterbetter(iter([]))
        >>> bool(c)
        False
        >>> list(c)
        []
    """
    def __init__(self, iterator): 
        self.i, self.c = iterator, 0

    def __iter__(self): 
        if hasattr(self, "_head"):
            yield self._head

        while 1:    
            yield self.i.next()
            self.c += 1

    def __getitem__(self, i):
        #todo: slices
        if i < self.c: 
            raise IndexError, "already passed "+str(i)
        try:
            while i > self.c: 
                self.i.next()
                self.c += 1
            # now self.c == i
            self.c += 1
            return self.i.next()
        except StopIteration: 
            raise IndexError, str(i)
            
    def __nonzero__(self):
        if hasattr(self, "__len__"):
            return len(self) != 0
        elif hasattr(self, "_head"):
            return True
        else:
            try:
                self._head = self.i.next()
            except StopIteration:
                return False
            else:
                return True

class threadeddict(threadlocal):
    """
    Thread local storage.
    
        >>> d = threadeddict()
        >>> d.x = 1
        >>> d.x
        1
        >>> import threading
        >>> def f(): d.x = 2
        ...
        >>> t = threading.Thread(target=f)
        >>> t.start()
        >>> t.join()
        >>> d.x
        1
    """
    _instances = set()
    
    def __init__(self):
        threadeddict._instances.add(self)
        
    def __del__(self):
        threadeddict._instances.remove(self)
        
    def __hash__(self):
        return id(self)
    
    def clear_all():
        """Clears all threadeddict instances.
        """
        for t in list(threadeddict._instances):
            t.clear()
    clear_all = staticmethod(clear_all)
    
    # Define all these methods to more or less fully emulate dict -- attribute access
    # is built into threading.local.

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __delitem__(self, key):
        del self.__dict__[key]

    def __contains__(self, key):
        return key in self.__dict__

    has_key = __contains__
        
    def clear(self):
        self.__dict__.clear()

    def copy(self):
        return self.__dict__.copy()

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def items(self):
        return self.__dict__.items()

    def iteritems(self):
        return self.__dict__.iteritems()

    def keys(self):
        return self.__dict__.keys()

    def iterkeys(self):
        return self.__dict__.iterkeys()

    iter = iterkeys

    def values(self):
        return self.__dict__.values()

    def itervalues(self):
        return self.__dict__.itervalues()

    def pop(self, key, *args):
        return self.__dict__.pop(key, *args)

    def popitem(self):
        return self.__dict__.popitem()

    def setdefault(self, key, default=None):
        return self.__dict__.setdefault(key, default)

    def update(self, *args, **kwargs):
        self.__dict__.update(*args, **kwargs)

    def __repr__(self):
        return '<threadeddict %r>' % self.__dict__

    __str__ = __repr__
    

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = forms
from fuqit.web import RequestDict

def read(web, **expected):
    results = web.params.copy()

    for key, value in expected.items():
        if key in results:
            try:
                if isinstance(value, int):
                    results[key] = int(results[key])
                elif isinstance(value, float):
                    results[key] = float(results[key])
                elif isinstance(value, bool):
                    results[key] = bool(results[key])
                else:
                    results[key] = results[key]
            except ValueError:
                # TODO: log these since they might matter
                results[key] = value
        else:
            results[key] = value

    return RequestDict(results)

########NEW FILE########
__FILENAME__ = server
# Fuqit Web Framework
# Copyright (C) 2013  Zed A. Shaw
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lust import log, server
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from fuqit import web, tools

DEFAULT_HEADERS = {
    'Content-type': 'text/plain'
}

class FuqitHandler(BaseHTTPRequestHandler):

    def transform_request(self, request_body=None):
        path, params = tools.parse_request(self.path, request_body)
        context = tools.build_context(params, self)
        body, code, headers = web.process(self.command, path, params, context)
        self.generate_response(body, code, headers)

    def do_GET(self):
        self.transform_request()

    def do_POST(self):
        clength = int(self.headers['content-length'])
        request_body = self.rfile.read(clength)
        self.transform_request(request_body)

    def generate_response(self, body, code, headers):
        headers = headers or DEFAULT_HEADERS

        self.send_response(code)

        for header, value in headers.items():
            self.send_header(header, value)
        self.end_headers()

        self.wfile.write(body)


def run_server(host='127.0.0.1', port=8000, config_module='config', app='app',
               debug=True):

    server_address = (host, port)
    web.configure(app_module=app, config_module=config_module) 
    httpd = HTTPServer(server_address, FuqitHandler)
    httpd.serve_forever()



class Service(server.Simple):
    name = 'fuqit'
    should_jail = False

    def before_drop_privs(self, args):
        pass

    def start(self, args):
        pass


def run(args, config_file, config_name):
    service = Service(config_file=config_file)
    log.setup(service.get('log_file'))
    service.run(args)


########NEW FILE########
__FILENAME__ = sessions
# Fuqit Web Framework
# Copyright (C) 2013  Zed A. Shaw
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import re
import os

expires_format = "%a, %d-%b-%Y %X GMT"

SESSION_PATTERN = re.compile('FuqitSession\s*=\s*([A-Fa-f0-9]+)')
SESSION_TIMEOUT = 100 # days
SESSION_STORE = {}

def make_random_id():
    return os.urandom(64/8).encode('hex_codec')

def get_session_id(headers):
    cookies = headers.get('cookie', None)

    if cookies:
        sid_match = SESSION_PATTERN.search(cookies)

        if sid_match:
            return sid_match.group(1)
        else:
            return make_random_id()
    else:
        return make_random_id()

def set_session_id(headers, session_id):
    dt = datetime.timedelta(days=SESSION_TIMEOUT)
    diff = datetime.datetime.now() + dt
    stamp = diff.strftime(expires_format)

    cookies = {'Set-Cookie': 'FuqitSession=%s; version=1; path=/; expires=%s; HttpOnly' % (session_id, stamp),
                'Cookie': 'FuqitSession=%s; version=1; path=/; expires=%s' % (session_id, stamp)}

    headers.update(cookies)

def load_session(variables):
    session_id = get_session_id(variables['headers'])
    session = SESSION_STORE.get(session_id, {})
    variables['session'] = session
    variables['session_id'] = session_id

def save_session(variables, response_headers):
    session_id = variables['session_id']
    set_session_id(response_headers, session_id)
    SESSION_STORE[session_id] = variables['session']


########NEW FILE########
__FILENAME__ = tools
# Fuqit Web Framework
# Copyright (C) 2013  Zed A. Shaw
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import importlib
import mimetypes
import cgi
import os

mimetypes.init()

def module(name, app_name=None):
    if app_name:
        themodule = importlib.import_module("." + name, package=app_name)
    else:
        themodule = importlib.import_module(name)

    reload(themodule)
    return themodule


def build_context(params, handler):
    return {'params': params,
              'headers': handler.headers,
              'path': handler.path,
              'method': handler.command,
              'client_address': handler.client_address,
              'request_version': handler.request_version,
            }

def parse_request(path, request_body):
    request_params = {}

    if '?' in path:
        path, params = path.split('?', 1)
        params = cgi.parse_qsl(params)
        request_params.update(params)

    if request_body:
        params = cgi.parse_qsl(request_body)
        request_params.update(params)

    return path, request_params


def make_ctype(ext, default_mtype):
    mtype = mimetypes.types_map.get(ext, default_mtype)
    return {'Content-Type': mtype}



def find_longest_module(app, name, variables):
    base = name[1:]

    # need to limit the max we'll try to 20 for safety
    for i in xrange(0, 20):
        # go until we hit the /
        if base == '/' or base == '':
            return None, None

        modname = base.replace('/', '.')

        try:
            return base, module(modname, app)
        except ImportError, e:
            # split off the next chunk to try to load
            print "ERROR", e 
            base, tail = os.path.split(base)

    # exhausted the path limit
    return None, None



########NEW FILE########
__FILENAME__ = web
# Fuqit Web Framework
# Copyright (C) 2013  Zed A. Shaw
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from jinja2 import Environment, PackageLoader, TemplateNotFound
from fuqit import tools, sessions
import re
import traceback
import os

config = None # this gets set by calling configure below

class RequestDict(dict):
    __getattr__ = dict.__getitem__


def render_error(code, message="", variables=None):
    try:
        return render_template(config.errors_dir + '%d.html' %
                                    code, variables or {}, ext='.html')
    except TemplateNotFound:
        return message, code, {}

def csrf_check(context):
    referer = context['headers'].get('referer', '')

    if referer:
        return config.allowed_referer.match(referer)
    else:
        return True

def process(method, path, params, context):
    if not csrf_check(context):
        return render_error(404, "Not Found")

    try:
        return render(path, context)
    except TemplateNotFound:
        print "Jinja2 template missing in path: %r for context %r" % (path, context)
        traceback.print_exc()
        return render_error(404, "Not Found")
    except Exception as e:
        traceback.print_exc()
        return render_error(500, str(e))

def render_template(path, variables, ext=None):
    ext = ext or os.path.splitext(path)[1]
    headers = tools.make_ctype(ext, config.default_mtype)

    if 'headers' in variables:
        sessions.load_session(variables)

    context = {'web': variables,
               'module': tools.module,
               'response_headers': headers,
               'config': config,
               'db': config.db, # it's so common
              }

    template = config.env.get_template(path)
    result = template.render(**context)

    if 'headers' in variables:
        sessions.save_session(variables, headers)

    return result, 200, headers


def render_module(name, variables):
    base, target = tools.find_longest_module(config.app_moudle, name, variables)

    if not (base and target):
        return render_error(404, "Not Found", variables=variables)
        
    variables['base_path'] = base
    variables['sub_path'] = name[len(base)+1:]
    sessions.load_session(variables)

    context = RequestDict(variables)

    if target:
        try:
            actions = target.__dict__
            # TODO: need to white-list context.method
            func = actions.get(context.method, None) or actions['run']
        except KeyError:
            return render_error(500, 'No run method or %s method.' %
                                     context.method)

        result = func(context)

        session_headers = {}
        sessions.save_session(variables, session_headers)

        if isinstance(result, tuple):
            body, code, headers = result
            headers.update(session_headers)
            return body, code, headers
        else:
            session_headers['Content-type'] = config.default_mtype
            return result, 200, session_headers
    else:
        return render_error(404, "Not Found", variables=variables)

def render_static(ext, path):
    # stupid inefficient, but that's what you get
    headers = tools.make_ctype(ext, config.default_mtype)

    try:
        return open(path).read(), 200, headers
    except IOError:
        return render_error(404, "Not Found")

def render(path, variables):
    assert config, "You need to call fuqit.web.configure."

    root, ext = os.path.splitext(path)
    realpath = os.path.realpath(config.app_path + path)

    if not realpath.startswith(config.app_path) or ext == ".py":
        # prevent access outside the app dir by comparing path roots
        return render_error(404, "Not Found", variables=variables)

    elif realpath.startswith(config.static_dir):
        return render_static(ext, realpath)

    elif ext:
        # if it has an extension it's a template
        return render_template(path, variables, ext=ext)

    elif path.endswith('/'):
        # if it ends in /, it's a /index.html or /index.py
        base = os.path.join(path, 'index')

        #! this will be hackable if you get rid of the realpath check at top
        if os.path.exists(config.app_path + base + '.html'):
            return render_template(base + '.html', variables, ext='.html')
        else:
            return render_module(path[:-1], variables)

    elif os.path.isdir(realpath):
        return "", 301, {'Location': path + '/'}

    else:
        # otherwise it's a module, tack on .py and load or fail
        return render_module(path, variables)

def redirect(path):
    """
    Simple redirect function for most of the interaction you need to do.
    """
    return "", 301, {'Location': path}

def error(code, message):
    return render_error(code, message)

def configure(app_module="app", config_module="config"):
    global config

    if not config:
        config = tools.module(config_module)
        config.app_module = app_module
        config.app_path = os.path.realpath(app_module)
        config.errors_dir = config.app_path + '/errors/'
        config.env = Environment(loader=PackageLoader(config.app_module, '.'))
        config.allowed_referer = re.compile(config.allowed_referer)
        config.static_dir = os.path.realpath(config.app_path +
                                           (config.static_dir or '/static/'))



########NEW FILE########
