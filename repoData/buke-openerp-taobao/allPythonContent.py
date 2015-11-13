__FILENAME__ = beanstalkc
#!/usr/bin/env python
"""beanstalkc - A beanstalkd Client Library for Python"""

__license__ = '''
Copyright (C) 2008-2011 Andreas Bolka

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

__version__ = '0.2.0'

import logging
import socket


DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 11300
DEFAULT_PRIORITY = 2**31
DEFAULT_TTR = 120


class BeanstalkcException(Exception): pass
class UnexpectedResponse(BeanstalkcException): pass
class CommandFailed(BeanstalkcException): pass
class DeadlineSoon(BeanstalkcException): pass

class SocketError(BeanstalkcException):
    @staticmethod
    def wrap(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except socket.error, e:
            raise SocketError(e)


class Connection(object):
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, parse_yaml=True,
                 connect_timeout=socket.getdefaulttimeout()):
        if parse_yaml is True:
            try:
                parse_yaml = __import__('yaml').load
            except ImportError:
                logging.error('Failed to load PyYAML, will not parse YAML')
                parse_yaml = False
        self._connect_timeout= connect_timeout
        self._parse_yaml = parse_yaml or (lambda x: x)
        self.host = host
        self.port = port
        self.connect()

    def connect(self):
        """Connect to beanstalkd server."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(self._connect_timeout)
        SocketError.wrap(self._socket.connect, (self.host, self.port))
        self._socket.settimeout(None)
        self._socket_file = self._socket.makefile('rb')

    def close(self):
        """Close connection to server."""
        try:
            self._socket.sendall('quit\r\n')
            self._socket.close()
        except socket.error:
            pass

    def _interact(self, command, expected_ok, expected_err=[]):
        SocketError.wrap(self._socket.sendall, command)
        status, results = self._read_response()
        if status in expected_ok:
            return results
        elif status in expected_err:
            raise CommandFailed(command.split()[0], status, results)
        else:
            raise UnexpectedResponse(command.split()[0], status, results)

    def _read_response(self):
        line = SocketError.wrap(self._socket_file.readline)
        if not line:
            raise SocketError()
        response = line.split()
        return response[0], response[1:]

    def _read_body(self, size):
        body = SocketError.wrap(self._socket_file.read, size)
        SocketError.wrap(self._socket_file.read, 2) # trailing crlf
        if size > 0 and not body:
            raise SocketError()
        return body

    def _interact_value(self, command, expected_ok, expected_err=[]):
        return self._interact(command, expected_ok, expected_err)[0]

    def _interact_job(self, command, expected_ok, expected_err, reserved=True):
        jid, size = self._interact(command, expected_ok, expected_err)
        body = self._read_body(int(size))
        return Job(self, int(jid), body, reserved)

    def _interact_yaml(self, command, expected_ok, expected_err=[]):
        size, = self._interact(command, expected_ok, expected_err)
        body = self._read_body(int(size))
        return self._parse_yaml(body)

    def _interact_peek(self, command):
        try:
            return self._interact_job(command, ['FOUND'], ['NOT_FOUND'], False)
        except CommandFailed, (_, status, results):
            return None

    # -- public interface --

    def put(self, body, priority=DEFAULT_PRIORITY, delay=0, ttr=DEFAULT_TTR):
        """Put a job into the current tube. Returns job id."""
        assert isinstance(body, str), 'Job body must be a str instance'
        jid = self._interact_value(
                'put %d %d %d %d\r\n%s\r\n' %
                    (priority, delay, ttr, len(body), body),
                ['INSERTED', 'BURIED'], ['JOB_TOO_BIG'])
        return int(jid)

    def reserve(self, timeout=None):
        """Reserve a job from one of the watched tubes, with optional timeout
        in seconds. Returns a Job object, or None if the request times out."""
        if timeout is not None:
            command = 'reserve-with-timeout %d\r\n' % timeout
        else:
            command = 'reserve\r\n'
        try:
            return self._interact_job(command,
                                      ['RESERVED'],
                                      ['DEADLINE_SOON', 'TIMED_OUT'])
        except CommandFailed, (_, status, results):
            if status == 'TIMED_OUT':
                return None
            elif status == 'DEADLINE_SOON':
                raise DeadlineSoon(results)

    def kick(self, bound=1):
        """Kick at most bound jobs into the ready queue."""
        return int(self._interact_value('kick %d\r\n' % bound, ['KICKED']))

    def peek(self, jid):
        """Peek at a job. Returns a Job, or None."""
        return self._interact_peek('peek %d\r\n' % jid)

    def peek_ready(self):
        """Peek at next ready job. Returns a Job, or None."""
        return self._interact_peek('peek-ready\r\n')

    def peek_delayed(self):
        """Peek at next delayed job. Returns a Job, or None."""
        return self._interact_peek('peek-delayed\r\n')

    def peek_buried(self):
        """Peek at next buried job. Returns a Job, or None."""
        return self._interact_peek('peek-buried\r\n')

    def tubes(self):
        """Return a list of all existing tubes."""
        return self._interact_yaml('list-tubes\r\n', ['OK'])

    def using(self):
        """Return a list of all tubes currently being used."""
        return self._interact_value('list-tube-used\r\n', ['USING'])

    def use(self, name):
        """Use a given tube."""
        return self._interact_value('use %s\r\n' % name, ['USING'])

    def watching(self):
        """Return a list of all tubes being watched."""
        return self._interact_yaml('list-tubes-watched\r\n', ['OK'])

    def watch(self, name):
        """Watch a given tube."""
        return int(self._interact_value('watch %s\r\n' % name, ['WATCHING']))

    def ignore(self, name):
        """Stop watching a given tube."""
        try:
            return int(self._interact_value('ignore %s\r\n' % name,
                                            ['WATCHING'],
                                            ['NOT_IGNORED']))
        except CommandFailed:
            return 1

    def stats(self):
        """Return a dict of beanstalkd statistics."""
        return self._interact_yaml('stats\r\n', ['OK'])

    def stats_tube(self, name):
        """Return a dict of stats about a given tube."""
        return self._interact_yaml('stats-tube %s\r\n' % name,
                                  ['OK'],
                                  ['NOT_FOUND'])

    def pause_tube(self, name, delay):
        """Pause a tube for a given delay time, in seconds."""
        self._interact('pause-tube %s %d\r\n' %(name, delay),
                       ['PAUSED'],
                       ['NOT_FOUND'])

    # -- job interactors --

    def delete(self, jid):
        """Delete a job, by job id."""
        self._interact('delete %d\r\n' % jid, ['DELETED'], ['NOT_FOUND'])

    def release(self, jid, priority=DEFAULT_PRIORITY, delay=0):
        """Release a reserved job back into the ready queue."""
        self._interact('release %d %d %d\r\n' % (jid, priority, delay),
                       ['RELEASED', 'BURIED'],
                       ['NOT_FOUND'])

    def bury(self, jid, priority=DEFAULT_PRIORITY):
        """Bury a job, by job id."""
        self._interact('bury %d %d\r\n' % (jid, priority),
                       ['BURIED'],
                       ['NOT_FOUND'])

    def touch(self, jid):
        """Touch a job, by job id, requesting more time to work on a reserved
        job before it expires."""
        self._interact('touch %d\r\n' % jid, ['TOUCHED'], ['NOT_FOUND'])

    def stats_job(self, jid):
        """Return a dict of stats about a job, by job id."""
        return self._interact_yaml('stats-job %d\r\n' % jid,
                                   ['OK'],
                                   ['NOT_FOUND'])


class Job(object):
    def __init__(self, conn, jid, body, reserved=True):
        self.conn = conn
        self.jid = jid
        self.body = body
        self.reserved = reserved

    def _priority(self):
        stats = self.stats()
        if isinstance(stats, dict):
            return stats['pri']
        return DEFAULT_PRIORITY

    # -- public interface --

    def delete(self):
        """Delete this job."""
        self.conn.delete(self.jid)
        self.reserved = False

    def release(self, priority=None, delay=0):
        """Release this job back into the ready queue."""
        if self.reserved:
            self.conn.release(self.jid, priority or self._priority(), delay)
            self.reserved = False

    def bury(self, priority=None):
        """Bury this job."""
        if self.reserved:
            self.conn.bury(self.jid, priority or self._priority())
            self.reserved = False

    def touch(self):
        """Touch this reserved job, requesting more time to work on it before
        it expires."""
        if self.reserved:
            self.conn.touch(self.jid)

    def stats(self):
        """Return a dict of stats about this job."""
        return self.conn.stats_job(self.jid)


if __name__ == '__main__':
    import doctest, os, signal
    try:
        pid = os.spawnlp(os.P_NOWAIT,
                         'beanstalkd',
                         'beanstalkd', '-l', '127.0.0.1', '-p', '14711')
        doctest.testfile('TUTORIAL.mkd', optionflags=doctest.ELLIPSIS)
        doctest.testfile('test/no-yaml.doctest', optionflags=doctest.ELLIPSIS)
    finally:
        os.kill(pid, signal.SIGTERM)

########NEW FILE########
__FILENAME__ = decorator
##########################     LICENCE     ###############################

# Copyright (c) 2005-2012, Michele Simionato
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

#   Redistributions of source code must retain the above copyright 
#   notice, this list of conditions and the following disclaimer.
#   Redistributions in bytecode form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution. 

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.

"""
Decorator module, see http://pypi.python.org/pypi/decorator
for the documentation.
"""

__version__ = '3.3.3'

__all__ = ["decorator", "FunctionMaker", "partial"]

import sys, re, inspect

try:
    from functools import partial
except ImportError: # for Python version < 2.5
    class partial(object):
        "A simple replacement of functools.partial"
        def __init__(self, func, *args, **kw):
            self.func = func
            self.args = args                
            self.keywords = kw
        def __call__(self, *otherargs, **otherkw):
            kw = self.keywords.copy()
            kw.update(otherkw)
            return self.func(*(self.args + otherargs), **kw)

if sys.version >= '3':
    from inspect import getfullargspec
else:
    class getfullargspec(object):
        "A quick and dirty replacement for getfullargspec for Python 2.X"
        def __init__(self, f):
            self.args, self.varargs, self.varkw, self.defaults = \
                inspect.getargspec(f)
            self.kwonlyargs = []
            self.kwonlydefaults = None
        def __iter__(self):
            yield self.args
            yield self.varargs
            yield self.varkw
            yield self.defaults

DEF = re.compile('\s*def\s*([_\w][_\w\d]*)\s*\(')

# basic functionality
class FunctionMaker(object):
    """
    An object with the ability to create functions with a given signature.
    It has attributes name, doc, module, signature, defaults, dict and
    methods update and make.
    """
    def __init__(self, func=None, name=None, signature=None,
                 defaults=None, doc=None, module=None, funcdict=None):
        self.shortsignature = signature
        if func:
            # func can be a class or a callable, but not an instance method
            self.name = func.__name__
            if self.name == '<lambda>': # small hack for lambda functions
                self.name = '_lambda_' 
            self.doc = func.__doc__
            self.module = func.__module__
            if inspect.isfunction(func):
                argspec = getfullargspec(func)
                self.annotations = getattr(func, '__annotations__', {})
                for a in ('args', 'varargs', 'varkw', 'defaults', 'kwonlyargs',
                          'kwonlydefaults'):
                    setattr(self, a, getattr(argspec, a))
                for i, arg in enumerate(self.args):
                    setattr(self, 'arg%d' % i, arg)
                if sys.version < '3': # easy way
                    self.shortsignature = self.signature = \
                        inspect.formatargspec(
                        formatvalue=lambda val: "", *argspec)[1:-1]
                else: # Python 3 way
                    self.signature = self.shortsignature = ', '.join(self.args)
                    if self.varargs:
                        self.signature += ', *' + self.varargs
                        self.shortsignature += ', *' + self.varargs
                    if self.kwonlyargs:
                        for a in self.kwonlyargs:
                            self.signature += ', %s=None' % a
                            self.shortsignature += ', %s=%s' % (a, a)
                    if self.varkw:
                        self.signature += ', **' + self.varkw
                        self.shortsignature += ', **' + self.varkw
                self.dict = func.__dict__.copy()
        # func=None happens when decorating a caller
        if name:
            self.name = name
        if signature is not None:
            self.signature = signature
        if defaults:
            self.defaults = defaults
        if doc:
            self.doc = doc
        if module:
            self.module = module
        if funcdict:
            self.dict = funcdict
        # check existence required attributes
        assert hasattr(self, 'name')
        if not hasattr(self, 'signature'):
            raise TypeError('You are decorating a non function: %s' % func)

    def update(self, func, **kw):
        "Update the signature of func with the data in self"
        func.__name__ = self.name
        func.__doc__ = getattr(self, 'doc', None)
        func.__dict__ = getattr(self, 'dict', {})
        func.func_defaults = getattr(self, 'defaults', ())
        func.__kwdefaults__ = getattr(self, 'kwonlydefaults', None)
        func.__annotations__ = getattr(self, 'annotations', None)
        callermodule = sys._getframe(3).f_globals.get('__name__', '?')
        func.__module__ = getattr(self, 'module', callermodule)
        func.__dict__.update(kw)

    def make(self, src_templ, evaldict=None, addsource=False, **attrs):
        "Make a new function from a given template and update the signature"
        src = src_templ % vars(self) # expand name and signature
        evaldict = evaldict or {}
        mo = DEF.match(src)
        if mo is None:
            raise SyntaxError('not a valid function template\n%s' % src)
        name = mo.group(1) # extract the function name
        names = set([name] + [arg.strip(' *') for arg in 
                             self.shortsignature.split(',')])
        for n in names:
            if n in ('_func_', '_call_'):
                raise NameError('%s is overridden in\n%s' % (n, src))
        if not src.endswith('\n'): # add a newline just for safety
            src += '\n' # this is needed in old versions of Python
        try:
            code = compile(src, '<string>', 'single')
            # print >> sys.stderr, 'Compiling %s' % src
            exec code in evaldict
        except:
            print >> sys.stderr, 'Error in generated code:'
            print >> sys.stderr, src
            raise
        func = evaldict[name]
        if addsource:
            attrs['__source__'] = src
        self.update(func, **attrs)
        return func

    @classmethod
    def create(cls, obj, body, evaldict, defaults=None,
               doc=None, module=None, addsource=True, **attrs):
        """
        Create a function from the strings name, signature and body.
        evaldict is the evaluation dictionary. If addsource is true an attribute
        __source__ is added to the result. The attributes attrs are added,
        if any.
        """
        if isinstance(obj, str): # "name(signature)"
            name, rest = obj.strip().split('(', 1)
            signature = rest[:-1] #strip a right parens            
            func = None
        else: # a function
            name = None
            signature = None
            func = obj
        self = cls(func, name, signature, defaults, doc, module)
        ibody = '\n'.join('    ' + line for line in body.splitlines())
        return self.make('def %(name)s(%(signature)s):\n' + ibody, 
                        evaldict, addsource, **attrs)
  
def decorator(caller, func=None):
    """
    decorator(caller) converts a caller function into a decorator;
    decorator(caller, func) decorates a function using a caller.
    """
    if func is not None: # returns a decorated function
        evaldict = func.func_globals.copy()
        evaldict['_call_'] = caller
        evaldict['_func_'] = func
        return FunctionMaker.create(
            func, "return _call_(_func_, %(shortsignature)s)",
            evaldict, undecorated=func, __wrapped__=func)
    else: # returns a decorator
        if isinstance(caller, partial):
            return partial(decorator, caller)
        # otherwise assume caller is a function
        first = inspect.getargspec(caller)[0][0] # first arg
        evaldict = caller.func_globals.copy()
        evaldict['_call_'] = caller
        evaldict['decorator'] = decorator
        return FunctionMaker.create(
            '%s(%s)' % (caller.__name__, first), 
            'return decorator(_call_, %s)' % first,
            evaldict, undecorated=caller, __wrapped__=caller,
            doc=caller.__doc__, module=caller.__module__)

########NEW FILE########
__FILENAME__ = taobao_base
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from osv import fields, osv
from osv import orm
import time, datetime
import openerp.tools as tools

from .taobao_top import TOPException
from psycopg2.extensions import TransactionRollbackError
from psycopg2 import DataError

import logging
_logger = logging.getLogger(__name__)
import openerp.tools.config as config

import sys,os
sys.path.append (os.path.abspath(os.path.join(os.path.dirname(__file__), 'libs')))
import beanstalkc
from decorator import decorator

import cPickle
beanstalk = None
NAME2FUNC = {}

def mq_client(func):
    name = func.__name__
    NAME2FUNC[name] = func
    def _func(func, *args, **kwds):
        global beanstalk
        if beanstalk is None:
            beanstalk = beanstalkc.Connection(host=config.get('beanstalkd_interface', 'localhost'), port= int(config.get('beanstalkd_port', 11300)))
            beanstalk.use('taobao_stream')

        s = cPickle.dumps((name, args, kwds))
        beanstalk.put(s)
    return decorator(_func, func)

def mq_server():
    beanstalk = beanstalkc.Connection(host=config.get('beanstalkd_interface', 'localhost'), port= int(config.get('beanstalkd_port', 11300)))
    beanstalk.watch('taobao_stream')
    beanstalk.ignore('default')

    while True:
        try:
            job = beanstalk.reserve()
        except:
            import traceback
            exc = traceback.format_exc()
            _logger.error(exc)
            time.sleep(1/1000)
            continue

        try:
            name, args, kwds = cPickle.loads(job.body)
            func = NAME2FUNC.get(name)
        except:
            import traceback
            exc = traceback.format_exc()
            _logger.error(exc)
            job.delete()
            continue

        try:
            func(*args, **kwds)
            job.delete()

        except TOPException:
            import traceback
            exc = traceback.format_exc()
            _logger.error(exc)
            job.delete()

        except osv.except_osv:
            import traceback
            exc = traceback.format_exc()
            _logger.error(exc)
            job.delete()

        except TransactionRollbackError: #TransactionRollbackError: 错误:  由于同步更新而无法串行访问
            job.release(delay = 1)

        except DataError: #DataError: 错误:  无效的 "UTF8" 编码字节顺序: 0xad
            import traceback
            exc = traceback.format_exc()
            _logger.error(exc)
            job.delete()

        except:
            import traceback
            exc = traceback.format_exc()
            _logger.error(exc)
            job.release(delay = 1)

        finally:
            time.sleep(1/1000)


STREAM_MSG_ROUTER = {}
def msg_route(**kwargs):
    def decorator(callback):
        STREAM_MSG_ROUTER[tuple(sorted(kwargs.items(), key=lambda x:x[0]))] = callback
        return callback
    return decorator

import threading
from functools import wraps
_lock=threading.RLock()

def lock():
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                _lock.acquire()
                return func(self, *args, **kwargs)
            finally:
                _lock.release()
        return wrapper
    return decorator

class TaobaoException(Exception):
    def __init__(self, msg):
        super(TaobaoException, self).__init__(msg)

class TaobaoMixin:

    def _get(self, cr, uid, ids = None, args = []):
        if not ids:
            ids = self.search(cr, uid, args)

        if not ids: return None

        ret = self.browse(cr, uid, ids)
        if isinstance(ret, orm.browse_record_list):
            return ret[0]
        else:
            return ret

    def _save(self, cr, uid, ids = None, args = None, **kwargs):
        vals = {}
        for k, v in [(str(k), v) for (k, v) in kwargs.iteritems()]:
            if self._columns.has_key(k) and v != None:
                if isinstance(self._columns[k], fields.boolean):
                    vals[k] = bool(v)
                    continue
                if isinstance(self._columns[k], fields.integer):
                    vals[k] = int(v)
                    continue
                if isinstance(self._columns[k], fields.char):
                    if type(v) == unicode:
                        vals[k] = unicode(v).strip()
                    else:
                        vals[k] = str(v).strip()
                    continue
                if isinstance(self._columns[k], fields.text):
                    vals[k] = type(v)(v).strip()
                    continue
                if isinstance(self._columns[k], fields.float):
                    vals[k] = float(v)
                    continue
                if isinstance(self._columns[k], fields.date):
                    if type(v) == str or type(v) == unicode:
                        vals[k] = type(v)(v).strip()
                    elif type(v) == datetime.datetime or type(v) == time:
                        vals[k] = type(v).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
                    continue
                if isinstance(self._columns[k], fields.datetime):
                    if type(v) == str or type(v) == unicode:
                        vals[k] = type(v)(v).strip()
                    elif type(v) == datetime.datetime or type(v) == time:
                        vals[k] = type(v).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
                    continue
                if isinstance(self._columns[k], fields.time):
                    if type(v) == str or type(v) == unicode:
                        vals[k] = type(v)(v).strip()
                    elif type(v) == datetime.datetime or type(v) == time:
                        vals[k] =type(v).strftime(tools.DEFAULT_SERVER_TIME_FORMAT)
                    continue

                vals[k] = v

        if (not ids) and args:
            ids = self.search(cr, uid, args)

        if ids:
            self.write(cr, uid, ids, vals)
        else:
            ids = self.create(cr, uid, vals)

        ret = self.browse(cr, uid, ids)
        if isinstance(ret, orm.browse_record_list):
            return ret[0]
        else:
            return ret


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
#    商业使用及二次开发，您需要联系并得到作者的许可。

########NEW FILE########
__FILENAME__ = taobao_delivery_tracking
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from osv import osv, fields
import logging
_logger = logging.getLogger(__name__)
from taobao_base import TaobaoMixin
from .taobao_top import TOP
import re
import datetime
import urllib

class taobao_shop(osv.osv, TaobaoMixin):
    _inherit = "taobao.shop"
    _columns = {
            'delivery_enable_sign_check': fields.boolean(u'检查快递签收情况'),
            'delivery_sign_reg': fields.text(u'签收标志', help = u'签收标志，使用正则表达式'),
            'delivery_sms_alert': fields.boolean(u'发送短信提醒买家确认', help = u'开发中...'),
            'delivery_sms_content': fields.text(u'短信内容', help = u'短信提醒内容'),

            'delivery_enable_remind_user': fields.boolean(u'发送邮件报告'),
            'delivery_emailto_user_id': fields.many2one('res.users', u'负责人'),

        }
    _defaults = {
            'delivery_enable_sign_check': True,
            'delivery_sign_reg': u'签收',
            'delivery_sms_alert': False,
            }


class stock_picking(osv.osv, TaobaoMixin):
    _inherit = 'stock.picking'

    _columns = {
        'carrier_tracking_state':fields.boolean(u'签收'),
        'carrier_tracking_detail': fields.text(u'物流详情'),
        }
    _defaults = {
            'carrier_tracking_state': False,
            }

    def _top_logistics_trace_search(self, top, tid, seller_nick):
        rsp =top('taobao.logistics.trace.search', tid=tid, seller_nick=seller_nick)
        return rsp if rsp else None

    def cron_check_carrier_tracking_state(self, cr, uid, ids=False, context=None):
        shop_obj = self.pool.get('taobao.shop')
        shops = shop_obj.browse(cr, uid, shop_obj.search(cr, uid, []))
        for shop in shops:
            if not shop.delivery_enable_sign_check: continue
            try:
                top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
                recmp = re.compile(shop.delivery_sign_reg)
                sql_req= """
                SELECT p.id as pid, so.taobao_trade_id as tid, tb.taobao_nick as nick
                FROM stock_picking p
                JOIN
                    sale_order so ON (p.sale_id = so.id)
                JOIN
                    taobao_shop tb ON (so.taobao_shop_id = tb.id)
                WHERE
                    so.taobao_trade_status = 'WAIT_BUYER_CONFIRM_GOODS'
                    AND p.carrier_tracking_state <> true
                    AND tb.id = %d
                """ % shop.id
                cr.execute(sql_req)
                pick_ids = [(x[0], x[1], x[2]) for x in cr.fetchall()]
                for pick_id, tb_tid, nick in pick_ids:
                    rsp = self._top_logistics_trace_search(top, tb_tid, nick)

                    trace_info = u'\r\n'.join([ u'%s %s' % (info.get('status_time', u''), info.get('status_desc', u'')) for info in rsp.trace_list.transit_step_info])

                    self.write(cr, uid, pick_id, {
                        'carrier_tracking_state': True if recmp.search(trace_info) else False,
                        'carrier_tracking_detail': trace_info,
                        })
            except:
                import traceback
                exc = traceback.format_exc()
                _logger.error(exc)


    def cron_carrier_tracking_remind(self, cr, uid, ids=False, context=None):
        shop_obj = self.pool.get('taobao.shop')
        shops = shop_obj.browse(cr, uid, shop_obj.search(cr, uid, []))
        for shop in shops:
            sms_reminds = {}
            email_body_lines = []
            try:
                sql_req= """
                SELECT p.id as pid
                FROM stock_picking p
                JOIN
                    sale_order so ON (p.sale_id = so.id)
                JOIN
                    taobao_shop tb ON (so.taobao_shop_id = tb.id)
                WHERE
                    so.taobao_trade_status = 'WAIT_BUYER_CONFIRM_GOODS'
                    AND p.carrier_tracking_state = true
                    AND tb.id = %d
                ORDER BY p.partner_id
                """ % shop.id
                cr.execute(sql_req)
                rep = [x[0] for x in cr.fetchall()]
                if not rep: continue
                pickings = self.browse(cr, uid, rep)
                for picking in pickings:
                    if  shop.delivery_sms_alert and shop.delivery_sms_content.strip() and picking.partner_id.taobao_receive_sms_remind:
                        sms_reminds[picking.address_id.mobile] = shop.delivery_sms_content.strip()

                    if shop.delivery_enable_remind_user:
                        email_body_lines.append((
                            picking.partner_id.taobao_nick,
                            picking.sale_id.taobao_trade_id,
                            picking.carrier_id.name,
                            picking.carrier_tracking_ref,
                            picking.carrier_tracking_detail,
                            picking.address_id.taobao_full_address
                            ))

                #send sms
                if sms_reminds:
                    pass

                if email_body_lines:
                    lines = []
                    for nick, tid, kuaidi, num, info, address  in email_body_lines:
                        line = u"""
                        <tr>
                            <td>
                                <a target="_blank" href="http://www.taobao.com/webww/ww.php?ver=3&touid=%s&siteid=cntaobao&status=1&charset=utf-8"><img border="0" src="http://amos.alicdn.com/realonline.aw?v=2&uid=%s&site=cntaobao&s=1&charset=utf-8" alt="点击这里给我发消息" /></a>
                            </td>
                            <td><a target="_blank" href="http://trade.taobao.com/trade/detail/trade_item_detail.htm?bizOrderId=%s">%s</a></td>
                            <td>%s:%s</td>
                            <td width=50%%>%s</td>
                            <td>%s</td>
                        </tr>
                        """ % ( urllib.quote(nick.encode('utf8')), urllib.quote(nick.encode('utf8')),
                                tid, tid,
                                kuaidi, num,
                                info.replace(u'\r\n', u'<br/>'),
                                address,
                                )
                        lines.append(line)

                    body = u"""
                    <table border="1">
                        <tr>
                            <td>旺旺</td><td>淘宝订单</td><td>快递</td><td width=50%%>物流跟踪</td><td>地址</td>
                        </tr>
                        %s
                    </table>
                    """ % u''.join(lines)

                    now = datetime.datetime.utcnow() + datetime.timedelta(hours = 8)
                    subject = u'%s | %s | %d个订单 已签收未确认' % (now.strftime('%Y-%m-%d'), shop.taobao_nick, len(email_body_lines))
                    self.pool.get('mail.message').schedule_with_attach(cr, uid, shop.delivery_emailto_user_id.user_email, [shop.delivery_emailto_user_id.user_email], subject, body, subtype='html',)

            except:
                import traceback
                exc = traceback.format_exc()
                _logger.error(exc)












# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

########NEW FILE########
__FILENAME__ = taobao_order
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from osv import osv, fields
import time
import netsvc
from .taobao_top import TOP
import openerp
from openerp.osv.osv import except_osv
from taobao_base import TaobaoMixin
from taobao_base import mq_client
from taobao_base import msg_route
import logging
_logger = logging.getLogger(__name__)


class taobao_shop(osv.osv, TaobaoMixin):
    _inherit = "taobao.shop"
    _columns = {
            #taobao order
            'enable_auto_rate': fields.boolean(u'交易成功自动评价'),
            'taobao_rate_content': fields.text(u'评价内容'),
            'taobao_journal_id':fields.many2one('account.journal', 'Journal', select=1, required=True),
            }
    _defaults = {
            'enable_auto_rate': True,
            }


class account_voucher(osv.osv, TaobaoMixin):
    _inherit = "account.voucher"

class sale_order_line(osv.osv, TaobaoMixin):
    _inherit = "sale.order.line"
    _columns = {
            'taobao_order_id': fields.char(u'淘宝订单编号', size = 64),
            }

    _sql_constraints = [('taobao_order_id_uniq','unique(taobao_order_id)', 'Taobao Order must be unique!')]



class sale_order(osv.osv, TaobaoMixin):
    _inherit = "sale.order"

    def _get_taobao_trade_url(self, cr, uid, ids, field_name, arg, context=None):
        res = {}

        for trade in self.browse(cr, uid, ids, context=context):
            res[trade.id] = 'http://trade.taobao.com/trade/detail/trade_item_detail.htm?bizOrderId=%s' % trade.taobao_trade_id if trade.taobao_trade_id else None

        return res

    _columns = {
            'taobao_shop_id': fields.many2one('taobao.shop', 'Taobao Shop', select=True),
            'taobao_trade_id': fields.char(u'淘宝交易编号', size = 64),
            'taobao_pay_time': fields.char(u'淘宝付款时间', size = 64),
            'taobao_alipay_no': fields.char(u'支付宝交易编号', size = 64),
            'taobao_trade_url': fields.function(_get_taobao_trade_url, type='char', string=u'淘宝订单信息'),
            'taobao_trade_status': fields.selection([
                ('TRADE_NO_CREATE_PAY', u'没有创建支付宝交易'),
                ('WAIT_BUYER_PAY', u'等待买家付款'),
                ('WAIT_SELLER_SEND_GOODS', u'买家已付款,等待卖家发货'),
                ('WAIT_BUYER_CONFIRM_GOODS', u'卖家已发货,等待买家确认收货'),
                ('TRADE_BUYER_SIGNED', u'买家已签收,货到付款专用'),
                ('TRADE_FINISHED', u'交易成功'),
                ('TRADE_CLOSED', u'付款以后用户退款成功，交易自动关闭'),
                ('TRADE_CLOSED_BY_TAOBAO', u'付款以前，卖家或买家主动关闭交易')
                ],
                u'淘宝交易状态'),

            'taobao_buyer_message': fields.text(u'买家留言'),
            'taobao_seller_memo': fields.text(u'卖家备注'),
            }

    _sql_constraints = [('taobao_trade_id_uniq','unique(taobao_trade_id)', 'Taobao Trade must be unique!')]

    def _top_sold_get(self, top, order_status, start_created = None,  end_created = None):

        trades = []
        for status in order_status:
            page_no = 0
            page_size = 50
            total_results = 999
            while(total_results > page_no*page_size):
                if start_created and end_created:
                    rsp =top('taobao.trades.sold.get', start_created=start_created, end_created=end_created, status=status,  fields = ['tid', 'status', 'buyer_nick', 'total_fee', 'pay_time'], page_no = page_no + 1, page_size = page_size)
                else:
                    rsp =top('taobao.trades.sold.get', status=status,  fields = ['tid', 'status', 'buyer_nick', 'total_fee', 'pay_time'], page_no = page_no + 1, page_size = page_size)

                if rsp and  rsp.has_key('trades'): trades = trades + rsp.trades.trade
                total_results = int(rsp.total_results)
                page_no += 1
                time.sleep(1/1000)

        return trades


    def _top_trade_fullinfo_get(self, top, tid):
        rsp =top('taobao.trade.fullinfo.get', tid=tid, fields=[
            'seller_nick', 'buyer_nick', 'title', 'type', 'created',
            'tid', 'seller_rate', 'buyer_flag', 'buyer_rate', 'status',
            'payment', 'adjust_fee', 'post_fee', 'total_fee', 'pay_time',
            'end_time', 'modified', 'consign_time', 'buyer_obtain_point_fee',
            'point_fee', 'real_point_fee', 'received_payment', 'commission_fee',
            'buyer_memo', 'seller_memo', 'alipay_no', 'alipay_id','is_brand_sale',
            'buyer_message', 'pic_path', 'num_iid', 'num', 'price',
            'buyer_alipay_no', 'receiver_name', 'receiver_state', 'receiver_city',
            'receiver_district', 'receiver_address', 'receiver_zip', 'receiver_mobile',
            'receiver_phone', 'buyer_email', 'seller_flag', 'seller_alipay_no',
            'seller_mobile', 'seller_phone', 'seller_name', 'seller_email',
            'available_confirm_fee', 'has_post_fee', 'timeout_action_time',
            'snapshot_url', 'cod_fee', 'cod_status', 'shipping_type', 'trade_memo',
            'is_3D', 'buyer_area', 'trade_from', 'is_lgtype', 'is_force_wlb',
            'orders',
            'promotion_details',
            ])

        if rsp and rsp.get('trade', None):
            return rsp.trade
        else:
            return None

    def _taobao_save_fullinfo(self, pool, cr, uid, taobao_trade_id, shop, top, context=None):
        trade_fullinfo = self._top_trade_fullinfo_get(top, taobao_trade_id)
        if trade_fullinfo.get('seller_nick', None) != shop.taobao_nick:
            return None

        #保存 res.partner
        res_partner_obj = pool.get('res.partner')
        tbbuyer = res_partner_obj._top_user_get(top, nick=trade_fullinfo.buyer_nick)
        partner = res_partner_obj._save(cr, uid, args=[('taobao_nick','=', tbbuyer.nick), ('ref','=', '%s' % tbbuyer.nick)], **{'name':tbbuyer.nick, 'ref':'%s' % tbbuyer.nick, 'category_id': [shop.taobao_user_category_id.id], 'customer': True, 'taobao_user_id':tbbuyer.get('user_id', None), 'taobao_nick':tbbuyer.nick})

        #保存 res.partner.address
        res_partner_address_obj = pool.get('res.partner.address')
        vals = {}
        vals['partner_id'] = partner.id
        vals['type'] = 'default'
        vals['name'] = trade_fullinfo.get('receiver_name', '')
        vals['phone'] = trade_fullinfo.get('receiver_phone', '')
        vals['mobile'] = trade_fullinfo.get('receiver_mobile', '')
        vals['receiver_state'] = trade_fullinfo.get('receiver_state', '')
        state_ids = pool.get('res.country.state').search(cr, uid, [('name','=',trade_fullinfo.get('receiver_state', ''))])
        if state_ids: vals['state_id'] = state_ids[0]

        vals['city'] = trade_fullinfo.get('receiver_city', '')
        street = trade_fullinfo.get('receiver_district', '') + ' ' + trade_fullinfo.get('receiver_address','')
        vals['street'] = street[0:64]
        vals['street2'] = street[64:128]
        vals['zip'] =trade_fullinfo.get('receiver_zip', '')

        vals['buyer_alipay_no'] = trade_fullinfo.get('buyer_alipay_no', '')
        if vals['buyer_alipay_no'].find('@') > -1:
            vals['email'] = vals['buyer_alipay_no']

        vals['taobao_full_address'] = ','.join([vals['name'], vals['phone'], vals['mobile'], vals['receiver_state'], street, vals['zip']])

        country_id = pool.get('res.country').search(cr, uid, [('code','=','CN')])[0]
        vals['country_id'] = country_id
        partner_address = res_partner_address_obj._save(cr, uid, args=[
            ('taobao_full_address','=',vals['taobao_full_address']),
            ], **vals)

        # 保存支付宝帐号
        trade_fullinfo['buyer_alipay_no'] = trade_fullinfo.get('buyer_alipay_no', '')
        if trade_fullinfo['buyer_alipay_no']:
            vals = {}
            vals['acc_number'] = trade_fullinfo.buyer_alipay_no
            vals['bank'] = pool.get('res.bank').search(cr, uid, args=[('bic','=', 'alipay')])[0]
            vals['bank_bic'] = 'alipay'
            vals['bank_name'] = u'支付宝'
            vals['owner_name'] = tbbuyer.nick
            vals['partner_id'] = partner.id
            vals['state'] = 'alipay'
            pool.get('res.partner.bank')._save(cr, uid, args=[('acc_number','=', trade_fullinfo.buyer_alipay_no)], **vals)

        vals = {}
        #保存 sale.order
        vals['taobao_shop_id'] = shop.id
        vals['taobao_trade_id'] = trade_fullinfo.tid
        vals['taobao_pay_time'] = trade_fullinfo.get('pay_time', None)
        vals['taobao_alipay_no'] = trade_fullinfo.get('alipay_no', None)
        vals['taobao_trade_status'] = trade_fullinfo.status
        vals['name'] = 'TB%s' % trade_fullinfo.tid
        vals['shop_id'] = shop.sale_shop_id.id
        vals['origin'] = 'TB%s' % trade_fullinfo.tid
        vals['client_order_ref'] = 'TB%s' % trade_fullinfo.tid
        if context and context.get('order_state', None):
            vals['state'] = context.get('order_state', None)
        vals['pricelist_id'] = shop.sale_shop_id.pricelist_id.id
        vals['partner_id'] = partner.id
        vals['partner_invoice_id'] = partner_address.id
        vals['partner_order_id'] = partner_address.id
        vals['partner_shipping_id'] = partner_address.id
        vals['taobao_buyer_message'] = trade_fullinfo.get('buyer_message', '')
        vals['taobao_seller_memo'] = trade_fullinfo.get('seller_memo', '')

        sale_order_instance = self._save(cr, uid, args=[('origin','=','TB%s' % taobao_trade_id)], **vals)

        #保存 sale.order.line
        sale_order_line_obj = pool.get('sale.order.line')
        for order in trade_fullinfo.orders.order:
            product = pool.get('taobao.product')._get_create_product(
                    pool, cr, uid, shop, top,
                    taobao_num_iid = order.get('num_iid', None),
                    taobao_sku_id = order.get('sku_id', None),
                    )

            #TRADE_CLOSED(付款以后用户退款成功，交易自动关闭)
            #TRADE_CLOSED_BY_TAOBAO(付款以前，卖家或买家主动关闭交易)
            if order.status in ['TRADE_CLOSED']:
                sol = sale_order_line_obj._get(cr, uid, args = [('taobao_order_id','=', order.oid)])
                if sol : pool.get('sale.order.line').unlink(cr, uid, [sol.id])
                continue

            vals = {}
            vals['order_id'] = sale_order_instance.id
            order['num_iid'] = order.get('num_iid', None)
            order['sku_id'] = order.get('sku_id', None)
            vals['product_id'] = product.id
            vals['name'] = '[%s] %s' % (product.default_code, product.name)
            vals['taobao_order_id'] = order.oid
            vals['product_uom_qty'] = int(order.num)
            vals['price_unit'] = float(order.total_fee) / float(order.num)
            vals['delay'] = 30.0
            sale_order_line_obj._save(cr, uid, args=[('taobao_order_id','=', order.oid)], **vals)

        #保存邮费
        post_fee = float(trade_fullinfo.get('cod_fee', '0')) + float(trade_fullinfo.get('post_fee', '0'))
        product_product_obj = pool.get('product.product')
        post_product = product_product_obj._get(cr, uid, args=[('default_code', '=', 'post_fee')])

        if post_fee > 0 and bool(trade_fullinfo.get('has_post_fee', True)):
            vals = {}
            vals['order_id'] = sale_order_instance.id
            vals['product_id'] = post_product.id
            vals['name'] = '[%s] %s' % (post_product.default_code, post_product.name)
            vals['product_uom_qty'] = 1
            vals['price_unit'] = post_fee
            vals['sequence'] = 100
            sale_order_line_obj._save(cr, uid, args=[('order_id','=', sale_order_instance.id), ('product_id','=', post_product.id)], **vals)
        else:
            post_line = sale_order_line_obj._get(cr, uid, args=[('order_id','=', sale_order_instance.id), ('product_id','=', post_product.id)])
            if post_line:
                sale_order_line_obj._save(cr, uid, ids=[post_line.id], **{'state':'cancel'})
                sale_order_line_obj.unlink(cr, uid, [post_line.id])

        cr.commit()

        return sale_order_instance

    def _taobao_confirm_order(self, pool, cr, uid, ids):
        #confirm order
        for sale_id in ids:
            sale_order_obj = pool.get('sale.order')
            sale_order_instance = sale_order_obj.browse(cr, uid, sale_id)
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, "sale.order", sale_id, 'order_confirm', cr)

            picking_ids = map(lambda x: x.id, sale_order_instance.picking_ids)

            for picking_id in picking_ids:
                wf_service.trg_validate(uid, "stock.picking", picking_id, 'button_confirm', cr)

            for line in  sale_order_obj.procurement_lines_get(cr, uid, [sale_id]):
                wf_service.trg_validate(uid, "procurement.order", line, 'button_confirm', cr)

            picking_obj = pool.get('stock.picking')
            try:
                picking_obj.action_assign(cr, uid, picking_ids)
            except except_osv: #('Warning !', 'Not enough stock, unable to reserve the products.')
                picking_obj.force_assign(cr, uid, picking_ids)
            except:
                import traceback
                exc = traceback.format_exc()
                _logger.error(exc)

        cr.commit()

    def _taobao_cancel_order(self, pool, cr, uid, ids):
        for sale_id in ids:
            wf_service = netsvc.LocalService("workflow")
            sale_order_instance = self.browse(cr, uid, sale_id)
            picking_ids = map(lambda x: x.id, sale_order_instance.picking_ids)

            for picking_id in picking_ids:
                wf_service.trg_validate(uid, "stock.picking", picking_id, 'button_cancel', cr)

            invoice_ids = map(lambda x: x.id, sale_order_instance.invoice_ids)
            for inv in invoice_ids:
                wf_service.trg_validate(uid, 'account.invoice', inv, 'invoice_cancel', cr)

            self.action_cancel(cr, uid, [sale_id])

        cr.commit()

    def _taobao_reopen_order(self, pool, cr, uid, ids):
        self._save(cr, uid, ids = ids, **{'state':'draft'})
        cr.commit()

    def _taobao_order_ship(self, pool, cr, uid, ids, top):
        for sale_id in ids:
            wf_service = netsvc.LocalService("workflow")
            sale_order_instance = self.browse(cr, uid, sale_id)
            if (not sale_order_instance) or int(sale_order_instance.picked_rate) == 100: continue
            picking_obj = pool.get('stock.picking')
            picking_ids = map(lambda x: x.id, sale_order_instance.picking_ids)

            for picking_id in picking_ids:
                context = dict({'date':time.strftime('%Y-%m-%d')}, active_ids=picking_ids, active_model='stock.picking')
                partial_id = pool.get("stock.partial.picking").create(cr, uid, {'picking_id':picking_id, 'date':time.strftime('%Y-%m-%d')}, context=context)
                pool.get('stock.partial.picking').do_partial(cr, uid, [partial_id], context=context)

            #add carrier to picking
            ship_data = self._taobao_get_ship(top, sale_order_instance.taobao_trade_id)
            if not ship_data: continue
            try:
                carrier_id = pool.get('delivery.carrier').search(cr, uid, args=[('name','=', ship_data['company_name'])])[0]
            except:
                carrier_id = pool.get('delivery.carrier').write(cr, uid, {
                    'name': ship_data['company_name'],
                    'partner_id': pool.get('delivery.carrier').search(cr, uid, args=[('name','=', u'快递')])[0],
                    'product_id': pool.get('product.product').search(cr, uid, args=[('default_code','=', 'post_fee')])[0],
                    })

            carrier_tracking_ref = ship_data['out_sid']
            picking_obj.write(cr, uid, picking_ids, {
                'carrier_id': carrier_id,
                'carrier_tracking_ref': carrier_tracking_ref,
                })


            for line in  self.procurement_lines_get(cr, uid, [sale_id]):
                wf_service.trg_validate(uid, "procurement.order", line, 'button_check', cr)

            for picking_id in picking_ids:
                wf_service.trg_validate(uid, "stock.picking", picking_id, 'button_done', cr)

        cr.commit()

    def _taobao_create_invoice(self, pool, cr, uid, ids):
        for sale_id in ids:
            wf_service = netsvc.LocalService("workflow")
            sale_order_instance = self.browse(cr, uid, sale_id)
            self.manual_invoice(cr, uid, [sale_order_instance.id])
            invoice_ids = pool.get('account.invoice').search(cr, uid, [('origin','=',sale_order_instance.origin)])
            for invoice_id in invoice_ids:
                wf_service.trg_validate(uid, "account.invoice", invoice_id, 'invoice_open', cr)
        cr.commit()

    def _taobao_get_ship(self, top, taobao_trade_id):
        try:
            rsp =top('taobao.logistics.orders.detail.get', tid=taobao_trade_id, fields = ['order_code', 'out_sid', 'company_name'])
            return {
                    'company_name' : rsp.shippings.shipping[0].company_name,
                    'out_sid' : rsp.shippings.shipping[0].out_sid,
                    'order_code' : rsp.shippings.shipping[0].order_code,
                    }
        except:
            return None

    def _taobao_pay_invoice(self, pool, cr, uid, shop, ids):
        for sale_id in ids:
            sale_order_instance = self.browse(cr, uid, sale_id)
            invoice_ids = pool.get('account.invoice').search(cr, uid, [('origin','=',sale_order_instance.origin)])
            for invoice_id in invoice_ids:
                inv = pool.get('account.invoice').browse(cr, uid, invoice_id)
                account_voucher_obj = pool.get('account.voucher')
                context = {
                    'partner_id' : inv.partner_id.id,
                    'journal_id' : shop.taobao_journal_id.id,
                    'company_id' : shop.taobao_journal_id.company_id.id,
                    'account_id' : shop.taobao_journal_id.default_credit_account_id and shop.taobao_journal_id.default_credit_account_id.id or False,
                    'account_id': shop.taobao_journal_id.default_credit_account_id and shop.taobao_journal_id.default_credit_account_id.id or False,
                    'period_id': account_voucher_obj._get_period(cr, uid),
                    'payment_option': 'without_writeoff',
                    'amount': inv.residual,
                    'comment': 'Write-Off',
                    'reference': 'AL%s' % sale_order_instance.taobao_alipay_no if sale_order_instance.taobao_alipay_no else None,
                    'date': time.strftime('%Y-%m-%d'),
                    'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                        }
                context.update(account_voucher_obj.onchange_journal(cr, uid, [], context['journal_id'], [],  account_voucher_obj._get_tax(cr, uid, context=context), context['partner_id'],  context['date'], context['amount'], context['type'], context['company_id'],context=context)['value'])

                context['line_dr_ids'] =  [[5, False, False]] + [[0, False,line_id] for line_id in context['line_dr_ids']] if context['line_dr_ids'] else []
                context['line_cr_ids'] =  [[5, False, False]] + [[0, False,line_id] for line_id in context['line_cr_ids']] if context['line_cr_ids'] else []
                context['line_ids'] =  [[5, False, False]] + [[0, False,line_id] for line_id in context['line_ids']] if context['line_ids'] else []

                context.update(account_voucher_obj.onchange_line_ids(cr, uid, [], context['line_dr_ids'], context['line_cr_ids'], context['amount'], shop.taobao_journal_id.currency.id, context=context)['value'])

                account_voucher_instance = account_voucher_obj._save(cr, uid, **context)
                account_voucher_obj.proforma_voucher(cr, uid, [account_voucher_instance.id], context=context)

        cr.commit()

@mq_client
@msg_route(code = 202, notify = 'notify_trade', status = 'TradeAlipayCreate')
def TaobaoTradeAlipayCreate(dbname, uid, app_key, rsp):
    #创建支付宝交易
    notify_trade = rsp.packet.msg.notify_trade
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        sale_order_obj._taobao_save_fullinfo(pool, cr, uid, notify_trade.tid, shop, top)
        cr.commit()
    finally:
        cr.close()


@mq_client
@msg_route(code = 202, notify = 'notify_trade', status = 'TradeCreate')
def TaobaoTradeCreate(dbname, uid, app_key, rsp):
    #创建交易
    notify_trade = rsp.packet.msg.notify_trade
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        sale_order_obj._taobao_save_fullinfo(pool, cr, uid, notify_trade.tid, shop, top)
        cr.commit()
    finally:
        cr.close()


@mq_client
@msg_route(code = 202, notify = 'notify_trade', status = 'TradeModifyFee')
def TaobaoTradeModifyFee(dbname, uid, app_key, rsp):
    #修改交易费用
    notify_trade = rsp.packet.msg.notify_trade
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        sale_order_obj._taobao_save_fullinfo(pool, cr, uid, notify_trade.tid, shop, top)
        cr.commit()
    finally:
        cr.close()



@mq_client
@msg_route(code = 202, notify = 'notify_trade', status = 'TradeCloseAndModifyDetailOrder')
def TaobaoTradeCloseAndModifyDetailOrder(dbname, uid, app_key, rsp):
    #关闭或修改子订单
    notify_trade = rsp.packet.msg.notify_trade
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        sale_order_obj._taobao_cancel_order(pool, cr, uid, sale_order_obj.search(cr, uid, [('origin','=','TB%s' % notify_trade.tid)]))
        sale_order_instance = sale_order_obj._taobao_save_fullinfo(pool, cr, uid, notify_trade.tid, shop, top)
        if sale_order_instance and sale_order_instance.taobao_trade_status in ['WAIT_SELLER_SEND_GOODS', 'WAIT_BUYER_CONFIRM_GOODS', 'TRADE_FINISHED', 'TRADE_BUYER_SIGNED']:
            sale_order_obj._taobao_reopen_order(pool, cr, uid, [sale_order_instance.id])
            sale_order_obj._taobao_confirm_order(pool, cr, uid, [sale_order_instance.id])

        cr.commit()
    finally:
        cr.close()


@mq_client
@msg_route(code = 202, notify = 'notify_trade', status = 'TradeClose')
def TaobaoTradeClose(dbname, uid, app_key, rsp):
    #关闭交易
    notify_trade = rsp.packet.msg.notify_trade
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        sale_order_obj._taobao_save_fullinfo(pool, cr, uid, notify_trade.tid, shop, top)
        sale_order_obj._taobao_cancel_order(pool, cr, uid, sale_order_obj.search(cr, uid, [('origin','=','TB%s' % notify_trade.tid)]))

        cr.commit()
    finally:
        cr.close()


@mq_client
@msg_route(code = 202, notify = 'notify_trade', status = 'TradeBuyerPay')
def TaobaoTradeBuyerPay(dbname, uid, app_key, rsp):
    #买家付款
    notify_trade = rsp.packet.msg.notify_trade
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        sale_order_instance = sale_order_obj._taobao_save_fullinfo(pool, cr, uid, notify_trade.tid, shop, top)
        if sale_order_instance and sale_order_instance.taobao_trade_status in ['WAIT_SELLER_SEND_GOODS', 'WAIT_BUYER_CONFIRM_GOODS', 'TRADE_FINISHED', 'TRADE_BUYER_SIGNED']:
            sale_order_obj._taobao_confirm_order(pool, cr, uid, [sale_order_instance.id])

        cr.commit()
    finally:
        cr.close()

def TaobaoTradeDelayConfirmPay(cr, uid, app_key, rsp):
    #延迟收货
    pass

@mq_client
@msg_route(code = 202, notify = 'notify_trade', status = 'TradePartlyRefund')
def TaobaoTradePartlyRefund(dbname, uid, app_key, rsp):
    #子订单退款成功
    notify_trade = rsp.packet.msg.notify_trade
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        sale_order_obj._taobao_cancel_order(pool, cr, uid, sale_order_obj.search(cr, uid, [('origin','=','TB%s' % notify_trade.tid)]))
        sale_order_instance = sale_order_obj._taobao_save_fullinfo(pool, cr, uid, notify_trade.tid, shop, top)
        if sale_order_instance and sale_order_instance.taobao_trade_status in ['WAIT_SELLER_SEND_GOODS', 'WAIT_BUYER_CONFIRM_GOODS', 'TRADE_FINISHED', 'TRADE_BUYER_SIGNED']:
            sale_order_obj._taobao_reopen_order(pool, cr, uid, [sale_order_instance.id])
            sale_order_obj._taobao_confirm_order(pool, cr, uid, [sale_order_instance.id])
        cr.commit()
    finally:
        cr.close()

def TaobaoTradePartlyConfirmPay(cr, uid, app_key, rsp):
    #子订单付款成功
    pass

@mq_client
@msg_route(code = 202, notify = 'notify_trade', status = 'TradeSuccess')
def TaobaoTradeSuccess(dbname, uid, app_key, rsp):
    #买家确认收货
    notify_trade = rsp.packet.msg.notify_trade
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        sale_order_instance = sale_order_obj._taobao_save_fullinfo(pool, cr, uid, notify_trade.tid, shop, top)
        if sale_order_instance and sale_order_instance.taobao_trade_status in ['WAIT_SELLER_SEND_GOODS', 'WAIT_BUYER_CONFIRM_GOODS', 'TRADE_FINISHED', 'TRADE_BUYER_SIGNED']:
            sale_order_obj._taobao_confirm_order(pool, cr, uid, [sale_order_instance.id])
            sale_order_obj._taobao_order_ship(pool, cr, uid, [sale_order_instance.id], top)
            sale_order_obj._taobao_create_invoice(pool, cr, uid, [sale_order_instance.id])
            sale_order_obj._taobao_pay_invoice(pool, cr, uid, shop, [sale_order_instance.id])

        cr.commit()

        # 添加评价
        if shop.enable_auto_rate:
            pool.get('taobao.rate')._top_trade_rate_add(top, notify_trade.tid, content = shop.taobao_rate_content)

    finally:
        cr.close()

def TaobaoTradeTimeoutRemind(dbname, uid, app_key, rsp):
    #交易超时提醒
    pass

def TaobaoTradeRated(dbname, uid, app_key, rsp):
    #买家评价交易
    #TODO check bad rated
    pass

@mq_client
@msg_route(code = 202, notify = 'notify_trade', status = 'TradeMemoModified')
def TaobaoTradeMemoModified(dbname, uid, app_key, rsp):
    #交易备注修改
    notify_trade = rsp.packet.msg.notify_trade
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        sale_order_obj._taobao_save_fullinfo(pool, cr, uid, notify_trade.tid, shop, top)
        cr.commit()
    finally:
        cr.close()

@mq_client
@msg_route(code = 202, notify = 'notify_trade', status = 'TradeLogisticsAddressChanged')
def TaobaoTradeLogisticsAddressChanged(dbname, uid, app_key, rsp):
    #修改交易收货地址
    notify_trade = rsp.packet.msg.notify_trade
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        sale_order_obj._taobao_save_fullinfo(pool, cr, uid, notify_trade.tid, shop, top)
        cr.commit()
    finally:
        cr.close()

@mq_client
@msg_route(code = 202, notify = 'notify_trade', status = 'TradeChanged')
def TaobaoTradeChanged(dbname, uid, app_key, rsp):
    #修改订单信息（SKU等）
    notify_trade = rsp.packet.msg.notify_trade
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        sale_order_instance = sale_order_obj._taobao_save_fullinfo(pool, cr, uid, notify_trade.tid, shop, top)
        if sale_order_instance and sale_order_instance.taobao_trade_status in ['WAIT_SELLER_SEND_GOODS', 'WAIT_BUYER_CONFIRM_GOODS', 'TRADE_FINISHED', 'TRADE_BUYER_SIGNED']:
            sale_order_obj._taobao_confirm_order(pool, cr, uid, [sale_order_instance.id])
        cr.commit()
    finally:
        cr.close()

@mq_client
@msg_route(code = 202, notify = 'notify_trade', status = 'TradeSellerShip')
def TaobaoTradeSellerShip(dbname, uid, app_key, rsp):
    #卖家发货
    notify_trade = rsp.packet.msg.notify_trade
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        sale_order_instance = sale_order_obj._taobao_save_fullinfo(pool, cr, uid, notify_trade.tid, shop, top)
        if sale_order_instance and sale_order_instance.taobao_trade_status in ['WAIT_SELLER_SEND_GOODS', 'WAIT_BUYER_CONFIRM_GOODS', 'TRADE_FINISHED', 'TRADE_BUYER_SIGNED']:
            sale_order_obj._taobao_confirm_order(pool, cr, uid, [sale_order_instance.id])
            sale_order_obj._taobao_order_ship(pool, cr, uid, [sale_order_instance.id], top)
            sale_order_obj._taobao_create_invoice(pool, cr, uid, [sale_order_instance.id])
        cr.commit()
    finally:
        cr.close()
    #TODO send sms to client


@mq_client
@msg_route(code = 9999, notify = 'import_taobao_order')
def import_taobao_order(dbname, uid, app_key, rsp):
    trade = rsp.packet.msg.import_taobao_order

    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()

    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        sale_order_obj = pool.get('sale.order')
        if not trade.status:
            rsp = sale_order_obj._top_trade_fullinfo_get(top, trade.tid)
            trade['status'] = rsp.status
    finally:
        cr.close()

    job = {}
    if trade.status == 'WAIT_SELLER_SEND_GOODS':
        job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"notify_trade":{"topic":"trade", "status":"TradeBuyerPay", "tid": trade.tid,}}, "code": 202}}
    elif trade.status == 'WAIT_BUYER_CONFIRM_GOODS':
        job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"notify_trade":{"topic":"trade", "status":"TradeSellerShip", "tid": trade.tid,}}, "code": 202}}
    elif trade.status == 'WAIT_BUYER_PAY':
        job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"notify_trade":{"topic":"trade", "status":"TradeAlipayCreate", "tid": trade.tid,}}, "code": 202}}
    elif trade.status == 'TRADE_CLOSED_BY_TAOBAO':
        job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"notify_trade":{"topic":"trade", "status":"TradeClose", "tid": trade.tid,}}, "code": 202}}
    elif trade.status == 'TRADE_CLOSED':
        job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"notify_trade":{"topic":"trade", "status":"TradeClose", "tid": trade.tid,}}, "code": 202}}
        #job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"notify_refund":{"topic":"refund", "status":"RefundSuccess", "tid": trade.tid,}}, "code": 202}}
    elif trade.status == 'TRADE_NO_CREATE_PAY':
        job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"notify_trade":{"topic":"trade", "status":"TradeCreate", "tid": trade.tid,}}, "code": 202}}
    elif trade.status == 'TRADE_FINISHED':
        job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"notify_trade":{"topic":"trade", "status":"TradeSuccess", "tid": trade.tid,}}, "code": 202}}

    if job:
        from taobao_shop import TaobaoMsgRouter
        TaobaoMsgRouter(dbname, uid, app_key, job)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

########NEW FILE########
__FILENAME__ = taobao_packet
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from osv import osv, fields
from taobao_base import TaobaoMixin

class taobao_packet(osv.osv, TaobaoMixin):
    _name = "taobao.packet"
    _description = "Taobao Stream Packet"
    _columns = {
            'name': fields.char(u'名字', size=256),
            'taobao_app_key': fields.char('App Key', size=256),
            'data': fields.text(u'Taobao Stream Packet'),
            }
    _order = 'id DESC'

    def cron_flush(self, cr, uid, ids=False, context=None):
        self.unlink(cr, uid, self.search(cr, uid, [], offset = 1000))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

########NEW FILE########
__FILENAME__ = taobao_product
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from osv import osv, fields
import decimal_precision as dp
from taobao_base import TaobaoMixin
from tools.translate import _
import tools
import logging
_logger = logging.getLogger(__name__)
import time
import openerp
from .taobao_top import TOP
from taobao_base import mq_client
from taobao_base import msg_route

class taobao_shop(osv.osv, TaobaoMixin):
    _inherit = "taobao.shop"
    _columns = {
            #taobao product
            'taobao_product_ids': fields.one2many('taobao.product', 'taobao_shop_id', u'淘宝宝贝'),
            'taobao_product_category_id': fields.many2one('product.category', u'淘宝产品分类', select=1, required=True, domain="[('type','=','normal')]"),
            'taobao_product_supplier' : fields.many2one('res.partner', 'Supplier', required=True,domain = [('supplier','=',True)], ondelete='cascade', help="Supplier of this product"),

            'taobao_product_warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True, ondelete="cascade"),
            'taobao_product_location_id': fields.many2one('stock.location', u'淘宝产品库位', required=True, domain="[('usage', '=', 'internal')]"),

            'taobao_product_uom': fields.many2one('product.uom', 'Product UOM', required=True),

            'taobao_product_cost_method': fields.selection([('standard','Standard Price'), ('average','Average Price')], 'Costing Method', required=True,
            help="Standard Price: the cost price is fixed and recomputed periodically (usually at the end of the year), Average Price: the cost price is recomputed at each reception of products."),
            'taobao_product_type': fields.selection([('product','Stockable Product'),('consu', 'Consumable'),('service','Service')], 'Product Type', required=True, help="Will change the way procurements are processed. Consumable are product where you don't manage stock."),
            'taobao_product_supply_method': fields.selection([('produce','Produce'),('buy','Buy')], 'Supply method', required=True, help="Produce will generate production order or tasks, according to the product type. Buy will trigger purchase orders when requested."),
            'taobao_product_procure_method': fields.selection([('make_to_stock','Make to Stock'),('make_to_order','Make to Order')], 'Procurement Method', required=True, help="'Make to Stock': When needed, take from the stock or wait until re-supplying. 'Make to Order': When needed, purchase or produce for the procurement request."),

            'taobao_product_min_qty': fields.float('Min Quantity', required=True,
            help="When the virtual stock goes below the Min Quantity specified for this field, OpenERP generates "\
            "a procurement to bring the virtual stock to the Max Quantity."),
            'taobao_product_max_qty': fields.float('Max Quantity', required=True,
            help="When the virtual stock goes below the Min Quantity, OpenERP generates "\
            "a procurement to bring the virtual stock to the Quantity specified as Max Quantity."),


            }

    _defaults = {
            }




class product_supplierinfo(osv.osv, TaobaoMixin):
    _inherit = "product.supplierinfo"


class product_template(osv.osv, TaobaoMixin):
    _inherit = "product.template"
    _columns = {
            'taobao_item_num_iid': fields.char(u'淘宝宝贝编码', size = 64),
            }

class product_product(osv.osv, TaobaoMixin):
    _inherit = "product.product"

    def _get_taobao_qty_available(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = product.virtual_available - product.taobao_wait_buyer_pay_qty

        return res

    def _get_taobao_wait_buyer_pay_qty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            sql_req= """
            SELECT sum(l.product_uom_qty)
            FROM sale_order_line l
            JOIN
                sale_order so ON (l.order_id = so.id)
            WHERE
                so.taobao_trade_status = 'WAIT_BUYER_PAY'
                AND l.product_id = %d
            """ % product.id
            cr.execute(sql_req)
            qty_ids = [x[0] for x in cr.fetchall()]
            res[product.id] = qty_ids[0] if qty_ids else 0

        return res

    _columns = {
            'taobao_product_ids': fields.one2many('taobao.product', 'product_product_id', u'淘宝宝贝'),
            'taobao_qty_available': fields.function(_get_taobao_qty_available, type='float', digits_compute=dp.get_precision('Product UoM'), string=u'淘宝库存', help = u'淘宝库存 = 可供数量 - 淘宝已拍未付款'),
            'taobao_wait_buyer_pay_qty': fields.function(_get_taobao_wait_buyer_pay_qty, type='float', digits_compute=dp.get_precision('Product UoM'), string=u'淘宝已拍未付款',),
            }

class taobao_product(osv.osv, TaobaoMixin):
    _name = "taobao.product"
    _description = "Taobao Sku"

    def _get_taobao_item_url(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = 'http://item.taobao.com/item.htm?id=%s' % product.taobao_num_iid if product.taobao_num_iid else None
        return res

    _columns = {
            'name': fields.char(u'淘宝商品名称', size=256),
            'taobao_num_iid': fields.char(u'商品数字编码', size = 64),
            'taobao_sku_id': fields.char(u'Sku id', size = 64),
            'taobao_sku_properties_name': fields.char(u'Sku属性', size = 256),

            'taobao_item_url': fields.function(_get_taobao_item_url, type='char', string=u'宝贝地址'),

            'product_product_id': fields.many2one('product.product', 'Product', select=True),
            'taobao_shop_id': fields.many2one('taobao.shop', 'Taobao Shop', select=True),
            }


    def _top_items_get(self, shop, top, search_q):
        items = []
        page_no = 0
        page_size = 50
        total_results = 999
        while(total_results > page_no*page_size):
            if search_q:
                rsp =top('taobao.items.onsale.get', q = search_q, nicks = shop.taobao_nick, fields = ['num_iid','title', 'pic_url', 'price', 'volume'], page_no = page_no + 1, page_size = page_size)
            else:
                rsp =top('taobao.items.onsale.get', nicks = shop.taobao_nick, fields = ['num_iid','title', 'pic_url', 'price', 'volume'], page_no = page_no + 1, page_size = page_size)
            if rsp and rsp.get('items', False): items = items + rsp.Items.Item
            total_results = int(rsp.total_results)
            page_no += 1
            time.sleep(1/1000)

        return items

    def _top_item_skus_get(self, shop, top, num_iids):
        rsp =top('taobao.item.skus.get', num_iids = num_iids, fields = ['sku_id','num_iid','quantity'])
        if rsp and rsp.get('skus', False):
            return rsp.skus.sku
        else:
            return []

    def _top_item_quantity_update(self, top, quantity, num_iid, sku_id = None, update_type = 1):
        if sku_id:
            rsp =top('taobao.item.quantity.update', num_iid = num_iid, sku_id = sku_id, quantity = int(quantity), TYPE = update_type)
        else:
            rsp =top('taobao.item.quantity.update', num_iid = num_iid, quantity = int(quantity), TYPE = update_type)

        if rsp and rsp.get('item', False):
            return rsp['item']
        else:
            return []

    def _get_create_product(self, pool, cr, uid, shop, top, taobao_num_iid =None,  taobao_sku_id = None, taobao_product_category_id = None, taobao_product_supplier = None, taobao_product_warehouse_id = None, taobao_product_location_id = None, taobao_product_cost_method = None, taobao_product_type = None, taobao_product_supply_method = None, taobao_product_procure_method = None, taobao_product_min_qty = None, taobao_product_max_qty = None, taobao_product_uom =
            None, is_update_stock = False):

        rsp = top('taobao.item.get', num_iid = taobao_num_iid, fields=['title', 'num_iid', 'outer_id', 'num', 'price'])
        if not rsp: return
        item = rsp.get('item', None)
        if not item: return

        vals = {}
        vals['categ_id'] = taobao_product_category_id if taobao_product_category_id else shop.taobao_product_category_id.id
        vals['name'] = item.title

        vals['cost_method'] = taobao_product_cost_method if taobao_product_cost_method else shop.taobao_product_cost_method
        vals['type'] = taobao_product_type if taobao_product_type else shop.taobao_product_type
        vals['procure_method'] = taobao_product_procure_method if taobao_product_procure_method else shop.taobao_product_procure_method
        vals['supply_method'] = taobao_product_supply_method if taobao_product_supply_method else shop.taobao_product_supply_method
        vals['uom_id'] = taobao_product_uom if taobao_product_uom else shop.taobao_product_uom.id

        # add min order rules
        vals['orderpoint_ids'] = [[5, False, False]] + [[0, False, {
                'warehouse_id': taobao_product_warehouse_id if taobao_product_warehouse_id else shop.taobao_product_warehouse_id.id,
                'location_id': taobao_product_location_id if taobao_product_location_id else shop.taobao_product_location_id.id,
                'product_min_qty': taobao_product_min_qty if taobao_product_min_qty else shop.taobao_product_min_qty,
                'product_max_qty': taobao_product_max_qty if taobao_product_max_qty else shop.taobao_product_max_qty,
                'product_uom': taobao_product_uom if taobao_product_uom else shop.taobao_product_uom.id
                }]]

        vals['taobao_item_num_iid'] = item.num_iid
        vals['default_code'] = item.get('outer_id', '')
        vals['list_price'] = float(str(item.price))
        vals['qty_available'] = float(item.num)
        vals['taobao_sku_properties_name'] = None

        if taobao_sku_id:
            rsp = top('taobao.item.sku.get', sku_id=taobao_sku_id, num_iid=taobao_num_iid,fields=['num_iid', 'quantity', 'price', 'outer_id', 'properties_name'])
            if not rsp: return
            sku = rsp.get('sku', None)
            if not sku: return

            vals['list_price'] = float(str(sku.price))
            vals['qty_available'] = float(sku.quantity)
            vals['taobao_sku_properties_name'] = sku.properties_name
            vals['default_code'] = sku.get('outer_id', '')

            #if sku.get('outer_id', None):
                #vals['default_code'] = sku.get('outer_id', '')
            #else:
                #for props in sku.properties_name.split(';'):
                    #if len(props.split(':')) > 1:
                        #if props.split(':')[-1]: vals['default_code'] += '-' + props.split(':')[-1]
                    #else:
                        #vals['default_code'] += '-' + props

        taobao_product = self._get(cr, uid, args = [('taobao_num_iid', '=', taobao_num_iid), ('taobao_sku_id', '=', taobao_sku_id)])

        if taobao_product:
            product = pool.get('product.product')._save(cr, uid, ids = taobao_product.product_product_id.id,  **vals)
        else:
            product_tmpl = pool.get('product.template')._save(cr, uid, args=[('taobao_item_num_iid','=',item.num_iid)], **vals)
            if not product_tmpl.seller_ids:
                #add sellerinfo
                pool.get('product.supplierinfo')._save(cr, uid, args=[('product_id','=',product_tmpl.id)], **{'product_id':product_tmpl.id, 'name': taobao_product_supplier if taobao_product_supplier else shop.taobao_product_supplier.id, 'min_qty': 1 })

            vals['product_tmpl_id'] = product_tmpl.id
            product = pool.get('product.product')._save(cr, uid, **vals)

        taobao_product = self._save(cr, uid,
                args = [
                    ('taobao_num_iid', '=', taobao_num_iid),
                    ('taobao_sku_id', '=', taobao_sku_id)
                    ],
                **{
                    'name': item.title,
                    'taobao_num_iid': taobao_num_iid,
                    'taobao_sku_id': taobao_sku_id,
                    'taobao_sku_properties_name': vals['taobao_sku_properties_name'],
                    'product_product_id': product.id,  'taobao_shop_id':shop.id})


        # update stock
        if product and is_update_stock and taobao_product_location_id:
            inventry_obj = self.pool.get('stock.inventory')
            inventry_line_obj = self.pool.get('stock.inventory.line')
            inventory_id = inventry_obj.create(cr , uid, {'name': _(u'淘宝: %s') % tools.ustr(shop.taobao_nick)})
            line_data ={
                'inventory_id' : inventory_id,
                'product_qty' : vals['qty_available'] + product.taobao_wait_buyer_pay_qty - product.outgoing_qty - product.incoming_qty,
                'location_id' : taobao_product_location_id,
                'product_id' : product.id,
                'product_uom' : taobao_product_uom if taobao_product_uom else shop.taobao_product_uom.id,
            }
            inventry_line_obj.create(cr , uid, line_data)
            inventry_obj.action_confirm(cr, uid, [inventory_id])
            inventry_obj.action_done(cr, uid, [inventory_id])

        cr.commit()
        return product if product else None



def TaobaoItemAdd(dbname, uid, app_key, rsp):
    #新增商品
    pass

def TaobaoItemUpshelf(dbname, uid, app_key, rsp):
    #上架商品
    pass

def TaobaoItemDownshelf(dbname, uid, app_key, rsp):
    #下架商品
    pass

def TaobaoItemDelete(dbname, uid, app_key, rsp):
    #删除商品
    pass

def TaobaoItemUpdate(dbname, uid, app_key, rsp):
    #更新商品
    pass

def TaobaoItemRecommendDelete(dbname, uid, app_key, rsp):
    #取消橱窗推荐商品
    pass

def TaobaoItemRecommendAdd(dbname, uid, app_key, rsp):
    #橱窗推荐商品
    pass

def TaobaoItemZeroStock(dbname, uid, app_key, rsp):
    #商品卖空
    pass

def TaobaoItemPunishDelete(dbname, uid, app_key, rsp):
    #小二删除商品
    pass

def TaobaoItemPunishDownshelf(dbname, uid, app_key, rsp):
    #小二下架商品
    pass

def TaobaoItemPunishCc(dbname, uid, app_key, rsp):
    #小二cc商品
    pass

def TaobaoItemSkuZeroStock(dbname, uid, app_key, rsp):
    #商品sku卖空
    pass

def TaobaoItemStockChanged(dbname, uid, app_key, rsp):
    #更新商品库存
    pass

@mq_client
@msg_route(code = 9999, notify = 'import_taobao_product')
def import_taobao_product(dbname, uid, app_key, rsp):
    #导入淘宝产品
    line = rsp.packet.msg.import_taobao_product
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
        taobao_product_obj = pool.get('taobao.product')

        skus = taobao_product_obj._top_item_skus_get(shop, top, line.get("taobao_num_iid", None))
        if skus:
            for sku in skus:
                taobao_product_obj._get_create_product(pool, cr, uid, shop, top,
                        taobao_num_iid = line.get('taobao_num_iid', None),
                        taobao_sku_id = sku.sku_id,

                        taobao_product_category_id = line.get('taobao_product_category_id', None),
                        taobao_product_supplier = line.get('taobao_product_supplier', None),
                        taobao_product_warehouse_id = line.get('taobao_product_warehouse_id', None),
                        taobao_product_location_id = line.get('taobao_product_location_id', None),
                        taobao_product_cost_method = line.get('taobao_product_cost_method', None),
                        taobao_product_type = line.get('taobao_product_type', None),
                        taobao_product_supply_method = line.get('taobao_product_supply_method', None),
                        taobao_product_procure_method = line.get('taobao_product_procure_method', None),
                        taobao_product_min_qty = line.get('taobao_product_min_qty', None),
                        taobao_product_max_qty = line.get('taobao_product_max_qty', None),
                        taobao_product_uom = line.get('taobao_product_uom', None),
                        is_update_stock = line.get('is_update_stock', None),

                        )
        else:
            taobao_product_obj._get_create_product(pool, cr, uid, shop, top,
                    taobao_num_iid = line.get('taobao_num_iid', None),

                    taobao_product_category_id = line.get('taobao_product_category_id', None),
                    taobao_product_supplier = line.get('taobao_product_supplier', None),
                    taobao_product_warehouse_id = line.get('taobao_product_warehouse_id', None),
                    taobao_product_location_id = line.get('taobao_product_location_id', None),
                    taobao_product_cost_method = line.get('taobao_product_cost_method', None),
                    taobao_product_type = line.get('taobao_product_type', None),
                    taobao_product_supply_method = line.get('taobao_product_supply_method', None),
                    taobao_product_procure_method = line.get('taobao_product_procure_method', None),
                    taobao_product_min_qty = line.get('taobao_product_min_qty', None),
                    taobao_product_max_qty = line.get('taobao_product_max_qty', None),
                    taobao_product_uom = line.get('taobao_product_uom', None),
                    is_update_stock = line.get('is_update_stock', None),

                    )

    finally:
        cr.close()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

########NEW FILE########
__FILENAME__ = taobao_rate
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from osv import osv, fields
from taobao_base import TaobaoMixin
import datetime
import time
from .taobao_top import TOP
from crm import crm

class taobao_shop(osv.osv, TaobaoMixin):
    _inherit = "taobao.shop"
    _columns = {
            #taobao rate
            'enable_auto_check_rate': fields.boolean(u'自动检查中差评'),
            'rate_helpdesk_user_id': fields.many2one('res.users', u'默认负责人'),
            'rate_helpdesk_section_id': fields.many2one('crm.case.section', u'默认销售团队'),
            'rate_helpdesk_channel_id': fields.many2one('crm.case.channel', u'途径'),
            'rate_helpdesk_priority': fields.selection(crm.AVAILABLE_PRIORITIES, u'优先级'),
            'rate_helpdesk_categ_id': fields.many2one('crm.case.categ', 'Category', \
                            domain="['|',('section_id','=',False),('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.helpdesk')]"),
            'rate_remind_user': fields.boolean(u'发送邮件'),
            }

    _defaults = {
            'enable_auto_check_rate': True,
            }


class taobao_rate(osv.osv, TaobaoMixin):
    _name = "taobao.rate"
    _description = "Taobao Trade Rate"
    _columns = {
            'taobao_app_key': fields.char('App Key', size=256),
            'start_date': fields.char('Start Date', size=256),
            'end_date': fields.char('End Date', size=256),

            'name': fields.char(u'名字', size=256),
            'tid': fields.char(u'交易ID', size=256),
            'oid': fields.char(u'子订单ID', size=256),
            'valid_score': fields.boolean(u'评价信息是否用于记分'),
            'role': fields.selection([
                ('seller', u'卖家'),
                ('buyer', u'买家'),
                ],
                u'评价者角色',
                ),
            'nick': fields.char(u'评价者昵称', size=256),
            'result': fields.selection([
                ('good', u'好评'),
                ('neutral', u'中评'),
                ('bad', u'差评'),
                ],
                u'评价结果',
                ),
            'created': fields.datetime(u'评价创建时间'),
            'rated_nick': fields.char(u'被评价者昵称', size=256),
            'item_title': fields.char(u'商品标题', size=256),
            'item_price': fields.float(u'商品价格'),
            'content': fields.text(u'评价内容'),
            'reply': fields.text(u'评价解释'),
            }

    _sql_constraints = [('taobao_tid_oid_uniq','unique(tid, oid)', 'Taobao Order  must be unique!')]

    _order = 'id DESC'

    def _top_trade_rate_add(self, top, tid, result = 'good', role = 'seller', content = None, anony = False ):

        trade_fullinfo = self.pool.get('sale.order')._top_trade_fullinfo_get(top, tid)
        for order in trade_fullinfo.orders.order:
            top('taobao.traderate.add', tid = tid, oid = order.oid, result = result, role = role, content = content, anony = anony )

    def rate_ticket_new(self, cr, uid, shop, top, rate, remind_user = True):
        res_partner_obj = self.pool.get('res.partner')
        partner = res_partner_obj._get(cr, uid, args = [('taobao_nick','=',rate.nick)])
        if not partner:
            tbbuyer = res_partner_obj._top_user_get(top, nick=rate.nick)
            try:
                partner = res_partner_obj._save(cr, uid, args=[('taobao_nick','=', tbbuyer.nick), ('ref','=', '%s' % tbbuyer.nick)], **{'name':tbbuyer.nick, 'ref':'%s' % tbbuyer.nick, 'category_id': [shop.taobao_user_category_id.id], 'customer': True, 'taobao_user_id':tbbuyer.get('user_id', None), 'taobao_nick':tbbuyer.nick})
            except:
                #IntegrityError: duplicate key value violates unique constraint "res_partner_taobao_user_id_uniq"
                pass

        partner_address_id = res_partner_obj.address_get(cr, uid, [partner.id]).get('default', None)
        order = self.pool.get('sale.order')._get(cr, uid, args = [('taobao_trade_id','=',rate.tid)])
        desc = u"""
                买家昵称: %s
                卖家昵称: %s
                评价日期: %s
                评价类型: %s
                交易编号: %s
                子订单编号: %s
                商品标题: %s
                商品价格: %s
                评价内容: %s
               """ % (rate.nick, rate.rated_nick, rate.created, rate.result, rate.tid, rate.oid, rate.item_title, rate.item_price, rate.content )

        helpdesk_obj = self.pool.get('crm.helpdesk')
        helpdesk_id = helpdesk_obj.create(cr, uid, {
            'name': u'%s | %s | %s' % (rate.created, rate.nick, u'中评' if rate.result == 'neutral' else u'差评'),
            'active': True,
            'description': desc,
            'user_id': shop.rate_helpdesk_user_id.id,
            'section_id': shop.rate_helpdesk_section_id.id,
            'partner_id': partner.id,
            'partner_address_id':partner_address_id if partner_address_id else None,
            'ref' : '%s,%s' % ('sale.order', str(order.id)) if order else None,
            'channel_id': shop.rate_helpdesk_channel_id.id,
            'priority': shop.rate_helpdesk_priority,
            'categ_id': shop.rate_helpdesk_categ_id.id,
            })
        if remind_user: helpdesk_obj.remind_user(cr, uid, [helpdesk_id])

        cr.commit()


    def _top_traderates_get(self, top, start_date = None, end_date = None):
        rates = []
        #中评
        page_no = 0
        page_size = 50
        total_results = 999
        while(total_results > page_no*page_size):
            rsp =top('taobao.traderates.get', fields = ['tid','oid','role','nick','result','created','rated_nick','item_title','item_price','content','reply'], rate_type = 'get', role = 'buyer', result = 'neutral', start_date = start_date, end_date = end_date, page_no = page_no + 1, page_size = page_size)
            if rsp and rsp.get('trade_rates', False): rates = rates + rsp.trade_rates.trade_rate
            if rsp and rsp.has_key('total_results'):
                total_results = int(rsp.get('total_results', 0))
            else:
                total_results = 0
            page_no += 1
            time.sleep(1/1000)

        #差评
        page_no = 0
        page_size = 50
        total_results = 999
        while(total_results > page_no*page_size):
            rsp =top('taobao.traderates.get', fields = ['tid','oid','role','nick','result','created','rated_nick','item_title','item_price','content','reply'], rate_type = 'get', role = 'buyer', result = 'bad', start_date = start_date, end_date = end_date, page_no = page_no + 1, page_size = page_size)
            if rsp and rsp.get('trade_rates', False): rates = rates + rsp.trade_rates.trade_rate
            if rsp and rsp.has_key('total_results'):
                total_results = int(rsp.get('total_results', 0))
            else:
                total_results = 0
            page_no += 1
            time.sleep(1/1000)

        return rates


    def cron_check_rate(self, cr, uid, ids=False, context=None):
        shop_obj = self.pool.get('taobao.shop')
        shops = shop_obj.browse(cr, uid, shop_obj.search(cr, uid, []))
        for shop in shops:
            if not shop.enable_auto_check_rate: continue
            top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)

            end = datetime.datetime.utcnow() + datetime.timedelta(hours = 8)
            rate_ids = self.search(cr, uid, [('taobao_app_key','=', shop.taobao_app_key)], limit =1)
            if rate_ids and rate_ids[0]:
                start = datetime.datetime.strptime(self.browse(cr, uid, rate_ids[0]).end_date, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(seconds = 1)
            else:
                start = end - datetime.timedelta(days = 30)

            top_rates = self._top_traderates_get(top, start_date = start.strftime('%Y-%m-%d %H:%M:%S'), end_date = end.strftime('%Y-%m-%d %H:%M:%S'))
                #add ticket
            for rate in top_rates:
                self.rate_ticket_new(cr, uid, shop, top, rate, remind_user = shop.rate_remind_user)
                time.sleep(1)

            self.create(cr, uid, {
                'taobao_app_key': shop.taobao_app_key,
                'start_date': start.strftime('%Y-%m-%d %H:%M:%S'),
                'end_date': end.strftime('%Y-%m-%d %H:%M:%S'),
                })

            time.sleep(1)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

########NEW FILE########
__FILENAME__ = taobao_refund
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from osv import osv, fields
from taobao_base import TaobaoMixin

from crm import crm
import openerp
from taobao_base import mq_client
from taobao_base import msg_route
from .taobao_top import TOP

class taobao_shop(osv.osv, TaobaoMixin):
    _inherit = "taobao.shop"
    _columns = {
            #taobao refund
            'enable_auto_check_refund': fields.boolean(u'检查退换货'),
            'refund_helpdesk_user_id': fields.many2one('res.users', u'默认负责人'),
            'refund_helpdesk_section_id': fields.many2one('crm.case.section', u'默认销售团队'),
            'refund_helpdesk_channel_id': fields.many2one('crm.case.channel', u'途径'),
            'refund_helpdesk_priority': fields.selection(crm.AVAILABLE_PRIORITIES, u'优先级'),
            'refund_helpdesk_categ_id': fields.many2one('crm.case.categ', 'Category', \
                            domain="['|',('section_id','=',False),('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.helpdesk')]"),
            'refund_remind_user': fields.boolean(u'发送邮件'),
            }

    _defaults = {
            }



class taobao_refund(osv.osv, TaobaoMixin):
    _name = "taobao.refund"
    _description = "Taobao Refund"
    _columns = {
            'name': fields.char(u'名字', size=256),
            'refund_id': fields.char(u'退款ID', size=256),
            'tid': fields.char(u'交易ID', size=256),
            'oid': fields.char(u'子订单ID', size=256),
            }

    def _top_refund_get(self, top, refund_id):
        rsp =top('taobao.refund.get', refund_id = refund_id, fields = ['refund_id', 'alipay_no', 'tid', 'oid', 'buyer_nick', 'seller_nick', 'total_fee', 'status', 'created', 'refund_fee', 'good_status', 'has_good_return', 'payment', 'reason', 'desc', 'num_iid', 'title', 'price', 'num', 'good_return_time', 'company_name', 'sid', 'address', 'shipping_type', 'refund_remind_timeout'])
        if rsp and rsp.get('refund', False):
            return rsp.refund
        else:
            return None

    def refund_ticket_new(self, cr, uid, shop, top, refund_id, remind_user = True):
        refund = self._top_refund_get(top, refund_id)
        if refund.seller_nick != shop.taobao_nick: return

        partner = self.pool.get('res.partner')._get(cr, uid, args = [('taobao_nick','=',refund.buyer_nick)])
        order = self.pool.get('sale.order')._get(cr, uid, args = [('taobao_trade_id','=',refund.tid)])
        if not (partner and order):
            self.pool.get('sale.order')._taobao_save_fullinfo(self.pool, cr, uid, refund.tid, shop, top)
            partner = self.pool.get('res.partner')._get(cr, uid, args = [('taobao_nick','=',refund.buyer_nick)])
            order = self.pool.get('sale.order')._get(cr, uid, args = [('taobao_trade_id','=',refund.tid)])

        partner_address_id = self.pool.get('res.partner').address_get(cr, uid, [partner.id]).get('default', None)
        desc = u"""
                退款ID: %s
                支付宝交易编号: %s
                交易编号: %s
                子订单编号: %s
                买家昵称: %s
                卖家昵称: %s
                交易总金额: ￥%s
                退款状态: %s
                退款日期: %s
                退款金额: %s
                货物状态: %s
                买家是否需要退货: %s
                支付给卖家的金额: %s
                退款原因: %s
                退款说明: %s
                申请退款的商品数字编号: %s
                商品标题: %s
                商品价格: %s
                商品购买数量: %s
               """ % (refund.refund_id, refund.alipay_no, refund.tid, refund.oid, refund.buyer_nick, refund.seller_nick, refund.total_fee, refund.status, refund.created, refund.refund_fee, refund.good_status, refund.has_good_return, refund.payment, refund.reason, refund.desc, refund.num_iid, refund.title, refund.price, refund.num)

        helpdesk_obj = self.pool.get('crm.helpdesk')
        helpdesk_id = helpdesk_obj.create(cr, uid, {
            'name': u'%s | %s | 退款编号:%s' % (refund.created, refund.buyer_nick, refund.refund_id),
            'active': True,
            'description': desc,
            'user_id': shop.refund_helpdesk_user_id.id,
            'section_id': shop.refund_helpdesk_section_id.id,
            'partner_id': partner.id,
            'partner_address_id':partner_address_id if partner_address_id else None,
            'ref' : '%s,%s' % ('sale.order', str(order.id)),
            'channel_id': shop.refund_helpdesk_channel_id.id,
            'priority': shop.refund_helpdesk_priority,
            'categ_id': shop.refund_helpdesk_categ_id.id,
            #'state': 'draft',
            })
        if remind_user: helpdesk_obj.remind_user(cr, uid, [helpdesk_id])
        cr.commit()


def TaobaoRefundSuccess(dbname, uid, app_key, rsp):
    #退款成功
    #TODO receive return goods or pay customer
    return

def TaobaoRefundClosed(dbname, uid, app_key, rsp):
    #退款关闭
    pass

@mq_client
@msg_route(code = 202, notify = 'notify_refund', status = 'RefundCreated')
def TaobaoRefundCreated(dbname, uid, app_key, rsp):
    #退款创建
    notify_refund = rsp.packet.msg.notify_refund
    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    try:
        shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
        if shop.enable_auto_check_refund:
            top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
            pool.get('taobao.refund').refund_ticket_new(cr, uid, shop, top, notify_refund.refund_id, remind_user = shop.refund_remind_user)
            cr.commit()
    finally:
        cr.close()


def TaobaoRefundSellerAgreeAgreement(dbname, uid, app_key, rsp):
    #卖家同意退#款协议
    pass

def TaobaoRefundSellerRefuseAgreement(dbname, uid, app_key, rsp):
    #卖家拒绝退款协议
    pass

def TaobaoRefundBuyerModifyAgreement(dbname, uid, app_key, rsp):
    #买家修改退款协议
    pass

def TaobaoRefundBuyerReturnGoods(dbname, uid, app_key, rsp):
    #买家退货给卖家
    #TODO add carrier to incoming picking
    pass

def TaobaoRefundCreateMessage(dbname, uid, app_key, rsp):
    #发表退款留言
    pass

def TaobaoRefundBlockMessage(dbname, uid, app_key, rsp):
    #屏蔽退款留言
    pass

def TaobaoRefundTimeoutRemind(dbname, uid, app_key, rsp):
    #退款超时提醒
    #TODO send sms to customer?
    pass


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

########NEW FILE########
__FILENAME__ = taobao_shop
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from osv import osv, fields
import openerp.tools.config as config
from .taobao_top import TOP, _O
import json
import datetime
import time
from taobao_base import mq_client
from taobao_base import msg_route
from taobao_base import STREAM_MSG_ROUTER

import openerp
import logging
_logger = logging.getLogger(__name__)
from taobao_base import TaobaoMixin
import threading

CHECK_DISCARD_THREAD_START = {}

class taobao_shop(osv.osv, TaobaoMixin):
    _name = "taobao.shop"
    _description = "Taobao Shop"

    def _get_taobao_shop_url(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for shop in self.browse(cr, uid, ids, context=context):
            res[shop.id] = 'http://shop%s.taobao.com' % shop.taobao_shop_sid
        return res

    _columns = {
            'name': fields.char(u'店铺名字', size=256),
            'sale_shop_id': fields.many2one('sale.shop', 'Sale Shop', required=True, select=True),
            'taobao_shop_sid': fields.char(u'店铺编号', size=64),
            'taobao_shop_url': fields.function(_get_taobao_shop_url, type='char', string=u'店铺地址'),
            'taobao_nick': fields.char(u'卖家昵称', size=64 ),
            'taobao_user_id': fields.char(u'卖家数字ID', size=64 ),
            'taobao_app_key': fields.char('App Key', size=256, unique = True),
            'taobao_app_secret': fields.char('App Secret', size=256),
            'taobao_session_key': fields.char('Session Key', size=256),

            #taobao shop
            'enable_taobao_stream': fields.boolean(u'接收淘宝主动通知消息'),

            }


    _sql_constraints = [('taobao_app_key_uniq','unique(taobao_app_key)', 'Taobao Shop App Key must be unique!')]

    _defaults = {
            'enable_taobao_stream': True,
            }


    def create(self, cr, user, vals, context=None):
        try:
            top = TOP(vals['taobao_app_key'], vals['taobao_app_secret'], vals['taobao_session_key'])
            top('taobao.increment.customer.permit')
            tb_user = top('taobao.user.get', fields = ['user_id','nick']).user
            tb_shop = top('taobao.shop.get', nick = tb_user.nick, fields = ['sid','nick']).shop
            vals['taobao_shop_sid'] = tb_shop.sid
            vals['taobao_user_id'] = tb_user.user_id
            vals['taobao_nick'] = tb_user.nick
            if not vals.get('name', False):
                vals['name'] = tb_user.nick
            return super(taobao_shop, self).create(cr, user, vals, context=context)
        except:
            raise

    def write(self, cr, user, ids, vals, context=None):
        try:
            shop = self._get(cr, user, ids = ids)
            if not 'taobao_app_key' in vals.keys():
                vals['taobao_app_key'] = shop.taobao_app_key

            if not 'taobao_app_secret' in vals.keys():
                vals['taobao_app_secret'] = shop.taobao_app_secret

            if not 'taobao_session_key' in vals.keys():
                vals['taobao_session_key'] = shop.taobao_session_key

            top = TOP(vals['taobao_app_key'], vals['taobao_app_secret'], vals['taobao_session_key'])
            top('taobao.increment.customer.permit')
            tb_user = top('taobao.user.get', fields = ['user_id','nick']).user
            tb_shop = top('taobao.shop.get', nick = tb_user.nick, fields = ['sid','nick']).shop
            vals['taobao_shop_sid'] = tb_shop.sid
            vals['taobao_user_id'] = tb_user.user_id
            vals['taobao_nick'] = tb_user.nick

            return super(taobao_shop, self).write(cr, user, ids, vals, context)
        except:
            raise

    def __init__(self, pool, cr):
        super(taobao_shop, self).__init__(pool, cr)
        #pycurl两个函数不是线程安全。所以在主线程中进行一次的初始化和清除
        import pycurl
        pycurl.global_init(pycurl.GLOBAL_DEFAULT)
        pycurl.global_cleanup()


    def _start_worker_thread(self, cr, uid):
        """
        启动 taobao worker 线程
        """
        for i in range(int(config.get('taobao_worker_thread_limit', 4))):
            thread_name = 'taobao_worker_%s' % str(i)
            thread_exits = False
            for thread in threading.enumerate():
                if thread.getName() == thread_name:
                    thread_exits = True
                    break;

            if not thread_exits:
                from taobao_base import mq_server
                t = threading.Thread(target=mq_server, args = [], name=thread_name)
                t.setDaemon(True)
                t.start()

            time.sleep(50/1000)

    def _create_stream_thread(self, cr, uid, thread_name, shop):
        """
        创建链接 taobao stream 线程
        """
        #创建stream线程
        stream_thread_exits = False
        for thread in threading.enumerate():
            if thread.getName() == thread_name:
                stream_thread_exits = True
                break;

        if not stream_thread_exits:
            # check last discard_info
            global CHECK_DISCARD_THREAD_START
            if not CHECK_DISCARD_THREAD_START.get(shop.taobao_app_key, False):
                threading.Thread(target=self._check_discard_info, args=[cr.dbname, uid, shop.taobao_app_key]).start()
                CHECK_DISCARD_THREAD_START[shop.taobao_app_key] = True

            #start taobao stream
            stream_id = ''.join([config['xmlrpc_interface'] or '0.0.0.0', ':', str(config['xmlrpc_port']), '/', thread_name])

            t = threading.Thread(target=TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key).stream, args=[cr.dbname, uid, stream_id, shop.taobao_user_id, shop.taobao_nick], name=thread_name)
            t.setDaemon(True)
            t.start()


    def _start_stream_thread(self, cr, uid, shops):
        if not config.get('taobao_stream_service', True):
            return

        for shop in shops:
            if shop.taobao_app_key  and shop.enable_taobao_stream:
                for i in range(int(config.get('taobao_stream_thread_limit', 1))):
                    shop_thread_name = 'taobao_app_' + shop.taobao_app_key + str(i)
                    self._create_stream_thread(cr, uid, shop_thread_name, shop)


    def _check_discard_info(self, dbname, uid, app_key):
        try:
            pool = openerp.pooler.get_pool(dbname)
            cr = pool.db.cursor()
            tb_packet_obj = pool.get('taobao.packet')
            packet_ids = tb_packet_obj.search(cr, uid, [('taobao_app_key','=', app_key)], limit =1)
            if packet_ids:
                begin_str = tb_packet_obj.perm_read(cr, uid, packet_ids)[0].get('create_date').split('.')[0]
                begin = datetime.datetime.strptime(begin_str, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(hours = 8) - datetime.timedelta(minutes = 1)
                end = datetime.datetime.utcnow() + datetime.timedelta(hours = 8)

                job = {"taobao_app_key": app_key, "packet": {"msg": {"begin": int(time.mktime(begin.timetuple())*1000), "end": int(time.mktime(end.timetuple())*1000)}, "code": 203}}
                TaobaoMsgRouter(dbname, uid, app_key, job)
        except:
            import traceback
            exc = traceback.format_exc()
            _logger.error(exc)
        finally:
            cr.close()


    def stream(self, cr, uid, ids=False, context=None):
        if not ids: ids = self.search(cr, uid, [])
        if context is None: context = {}

        shops = self.browse(cr, uid, ids, context=context)
        if shops:
            self._start_worker_thread(cr, uid) # 启动worker 进程
            self._start_stream_thread(cr, uid, shops)

@mq_client
@msg_route(code = 203)
def TaobaoHandleDiscardInfo(dbname, uid, app_key, rsp):
    begin = datetime.datetime.fromtimestamp(rsp.packet.msg.begin/1000)
    end = datetime.datetime.fromtimestamp(rsp.packet.msg.end/1000)
    if begin >= end: return

    pool = openerp.pooler.get_pool(dbname)
    cr = pool.db.cursor()
    shop = pool.get('taobao.shop')._get(cr, uid, args = [('taobao_app_key','=',app_key)])
    top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
    cr.close()

    if begin.day < end.day:
        cut_time = datetime.datetime(begin.year, begin.month, begin.day, 23, 59, 59)
        job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"begin": int(time.mktime(begin.timetuple()) * 1000), "end": int(time.mktime(cut_time.timetuple())*1000)}, "code": 203}}
        TaobaoMsgRouter(dbname, uid, app_key, job)

        new_time = datetime.datetime(begin.year, begin.month, begin.day, 0, 0, 0) + datetime.timedelta(days=1)
        job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"begin": int(time.mktime(new_time.timetuple())*1000), "end": int(time.mktime(end.timetuple())*1000)}, "code": 203}}
        TaobaoMsgRouter(dbname, uid, app_key, job)
        return

    if (end - begin) > datetime.timedelta(hours = 1):
        cut_time = datetime.datetime(begin.year, begin.month, begin.day, begin.hour, 59, 59)
        job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"begin": int(time.mktime(begin.timetuple())*1000), "end": int(time.mktime(cut_time.timetuple())*1000)}, "code": 203}}
        TaobaoMsgRouter(dbname, uid, app_key, job)

        new_time = datetime.datetime(begin.year, begin.month, begin.day, begin.hour, 0, 0)  + datetime.timedelta(hours=1)
        job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"begin": int(time.mktime(new_time.timetuple())*1000), "end": int(time.mktime(end.timetuple())*1000)}, "code": 203}}
        TaobaoMsgRouter(dbname, uid, app_key, job)
        return

    tb_rsp = top('taobao.comet.discardinfo.get', user_id = shop.taobao_user_id, start = begin.strftime('%Y-%m-%d %H:%M:%S'), end = end.strftime('%Y-%m-%d %H:%M:%S'))

    if tb_rsp and tb_rsp.discard_info_list.has_key('discard_info'):
        discard_info_list = tb_rsp.discard_info_list.discard_info
        for discard_info in discard_info_list:
            page_no = 0
            page_size =  200
            total_results = 999
            while(total_results > page_no*page_size):
                method_name = 'taobao.increment.%ss.get' % str(discard_info.Type)
                start = datetime.datetime.fromtimestamp(discard_info.start/1000)
                end = datetime.datetime.fromtimestamp(discard_info.end/1000)
                notifys = []
                while start <= end:
                    if start.day == end.day:
                        notifys_rsp = top(method_name, nick = shop.taobao_nick, start_modified = start.strftime('%Y-%m-%d %H:%M:%S'), end_modified = end.strftime('%Y-%m-%d %H:%M:%S'),  page_no = page_no + 1, page_size = page_size)
                        start = datetime.datetime(start.year, start.month, start.day, 0, 0, 0)+ datetime.timedelta(days=1)
                        if notifys_rsp and notifys_rsp.get('notify_%ss' % str(discard_info.Type), None):
                            notifys += notifys_rsp['notify_%ss' % str(discard_info.Type)]['notify_%s' % str(discard_info.Type)]
                    elif start.day < end.day:
                        notifys_rsp = top(method_name, nick = shop.taobao_nick, start_modified = start.strftime('%Y-%m-%d %H:%M:%S'), page_no = page_no + 1, page_size = page_size)
                        start = datetime.datetime(start.year, start.month, start.day, 0, 0, 0)+ datetime.timedelta(days=1)
                        if notifys_rsp and notifys_rsp.get('notify_%ss' % str(discard_info.Type), None):
                            notifys += notifys_rsp['notify_%ss' % str(discard_info.Type)]['notify_%s' % str(discard_info.Type)]
                time.sleep(1/1000)

                for notify in notifys :
                    job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": notify, "code": 202}}
                    TaobaoMsgRouter(dbname, uid, app_key, job)

                total_results = int(notifys_rsp.total_results)
                page_no = page_no + 1

@mq_client
def TaobaoMsgRouter(dbname, uid, app_key, rsp, is_stream_data = False):
    _logger.info(rsp)

    if is_stream_data:
        try:
            pool = openerp.pooler.get_pool(dbname)
            cr = pool.db.cursor()
            pool.get('taobao.packet').create(cr, uid, {'taobao_app_key': app_key, 'data': rsp})
            cr.commit()
        finally:
            cr.close()

    try:
        if rsp.__class__ == dict:
            rsp = json.loads(json.dumps(rsp), strict=False, object_hook =lambda x: _O(x))
        elif rsp.__class__ == str or rsp.__class__ == unicode :
            rsp = json.loads(rsp, strict=False, object_hook =lambda x: _O(x))
    except:
        import traceback
        exc = traceback.format_exc()
        _logger.error(exc)
        return

    func = None
    keys = {}
    try:
        keys['code'] = rsp.packet.code
        tmp_func = STREAM_MSG_ROUTER.get(tuple(sorted(keys.items(), key=lambda x:x[0])), None)
        if tmp_func: func = tmp_func

        k,v = rsp.packet.msg.items()[0]
        keys['notify'] = str(k)
        tmp_func = STREAM_MSG_ROUTER.get(tuple(sorted(keys.items(), key=lambda x:x[0])), None)
        if tmp_func: func = tmp_func

        keys['status'] = str(v.status)
        tmp_func = STREAM_MSG_ROUTER.get(tuple(sorted(keys.items(), key=lambda x:x[0])), None)
        if tmp_func: func = tmp_func
    except:
        pass

    if func:func(dbname, uid, app_key, rsp)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

########NEW FILE########
__FILENAME__ = taobao_top
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

import datetime, time
import base64
from hashlib import md5
import pycurl
import StringIO
import urllib
import json
import hashlib

import logging
_logger = logging.getLogger(__name__)

#from .taobao import TaobaoException

ERROR_MESSAGES = {
    #系统级错误
    3:u'图片上传失败',
    4:u'用户调用次数超限',
    5:u'会话调用次数超限',
    6:u'合作伙伴调用次数超限',
    7:u'应用调用次数超限',
    8:u'应用调用频率超限',
    9:u'HTTP方法被禁止（请用大写的POST或GET）',
    10:u'服务不可用',
    11:u'开发者权限不足',
    12:u'用户权限不足',
    13:u'合作伙伴权限不足',
    15:u'远程服务出错',
    21:u'缺少方法名参数',
    22:u'不存在的方法名',
    23:u'非法数据格式',
    24:u'缺少签名参数',
    25:u'非法签名',
    26:u'缺少SessionKey参数',
    27:u'无效的SessionKey参数',
    28:u'缺少AppKey参数',
    29:u'非法的AppKe参数',
    30:u'缺少时间戳参数',
    31:u'非法的时间戳参数',
    32:u'缺少版本参数',
    33:u'非法的版本参数',
    34:u'不支持的版本号',
    40:u'缺少必选参数',
    41:u'非法的参数',
    42:u'请求被禁止',
    43:u'参数错误',

    #容器类错误
    100:u'授权码已经过期',
    101:u'授权码在缓存里不存在，一般是用同样的authcode两次获取sessionkey',
    103:u'appkey或者tid（插件ID）参数必须至少传入一个',
    104:u'appkey或者tid对应的插件不存在',
    105:u'插件的状态不对，不是上线状态或者正式环境下测试状态',
    106:u'没权限调用此app，由于插件不是所有用户都默认安装，所以需要用户和插件进行一个订购关系。',
    108:u'由于app有绑定昵称，而登陆的昵称不是绑定昵称，所以没权限访问。',
    109:u'服务端在生成参数的时候出了问题（一般是tair有问题）',
    110:u'服务端在写出参数的时候出了问题',
    111:u'服务端在生成参数的时候出了问题（一般是tair有问题）',

    #业务级错误
    501:u'语句不可索引',
    502:u'数据服务不可用',
    503:u'无法解释TBQL语句',
    504:u'需要绑定用户昵称',
    505:u'缺少参数',
    506:u'参数错误',
    507:u'参数格式错误',
    508:u'获取信息权限不足',
    540:u'交易统计服务不可用',
    541:u'类目统计服务不可用',
    542:u'商品统计服务不可用',
    550:u'用户服务不可用',
    551:u'商品服务不可用',
    552:u'商品图片服务不可用',
    553:u'商品更新服务不可用',
    554:u'商品删除失败',
    555:u'用户没有订购图片服务',
    556:u'图片URL错误',
    557:u'商品视频服务不可用',
    560:u'交易服务不可用',
    561:u'交易服务不可用',
    562:u'交易不存在',
    563:u'非法交易',
    564:u'没有权限添加或更新交易备注',
    565:u'交易备注超出长度限制',
    566:u'交易备注已经存在',
    567:u'没有权限添加或更新交易信息',
    568:u'交易没有子订单',
    569:u'交易关闭错误',
    570:u'物流服务不可用',
    571:u'非法的邮费',
    572:u'非法的物流公司编号',
    580:u'评价服务不可用',
    581:u'添加评价服务错误',
    582:u'获取评价服务错误',
    590:u'店铺服务不可用',
    591:u'店铺剩余推荐数 服务不可用',
    592:u'卖家自定义类目服务不可用',
    594:u'卖家自定义类目添加错误',
    595:u'卖家自定义类目更新错误',
    596:u'用户没有店铺',
    597:u'卖家自定义父类目错误',
    601:u'用户不存在',
    611:u'产品数据格式错误',
    612:u'产品ID错误',
    613:u'删除产品图片错误',
    614:u'没有权限添加产品',
    615:u'收货地址服务不可用',
    620:u'邮费服务不可用',
    621:u'邮费模板类型错误',
    622:u'缺少参数：post, express或ems',
    623:u'邮费模板参数错误',
    630:u'收费服务不可用',
    650:u'退款服务不可用',
    651:u'非法的退款编号',
    670:u'佣金服务不可用',
    671:u'佣金交易不存在',
    672:u'淘宝客报表服务不可用',
    673:u'备案服务不可用',
    674:u'应用服务不可用',
    710:u'淘宝客服务不可用',
    900:u'远程连接错误',
    901:u'远程服务超时',
    902:u'远程服务错误',

    #CUSTOM ERRORS
    1000:u'Bad Environment',
}


class TOPException(Exception):
    """There was an ambiguous exception that occurred while handling your
    TOP request."""
    def __init__(self, code, msg=None):
        if not msg:
            msg = ERROR_MESSAGES.get(code,u'未知错误(%d)'%code)
        if type(msg) == unicode:
            msg = msg.encode('utf-8')
        super(TOPException, self).__init__(msg)
        self.code = code

    def __str__(self):
        return "%s (code=%d)" % (super(TOPException, self).__str__(), self.code)

    __repr__ = __str__


class _O(dict):
    """Makes a dictionary behave like an object."""
    def __getattr__(self, name):
        try:
            return self[name.lower()] # python dict items 与淘宝返回 items 冲突
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name.lower] = value

class TOP(object):
    def __init__(self, app_key = None, app_secret = None, session = None):
        self.app_key = app_key
        self.app_secret = app_secret
        self.session = session
        self.top_url = 'http://gw.api.taobao.com/router/rest'
        self.stream_url = 'http://stream.api.taobao.com/stream'

    def _sign(self, params, qhs = False):
        '''
        Generate API sign code
        '''
        for k, v in params.iteritems():
            if type(v) == int: v = str(v)
            elif type(v) == float: v = '%.2f'%v
            elif type(v) in (list, set):
                v = ','.join([str(i) for i in v])
            elif type(v) == bool: v = 'true' if v else 'false'
            elif type(v) == datetime.datetime: v = v.strftime('%Y-%m-%d %H:%M:%S')
            if type(v) == unicode:
                params[k] = v.encode('utf-8')
            else:
                params[k] = v

        if qhs:
            src = self.app_secret.encode('utf-8') + ''.join(["%s%s" % (k, v) for k, v in sorted(params.iteritems())]) + self.app_secret.encode('utf-8')
        else:
            src = self.app_secret.encode('utf-8') + ''.join(["%s%s" % (k, v) for k, v in sorted(params.iteritems())])

        return md5(src).hexdigest().upper()

    def decode_params(top_parameters) :
        params = {}
        param_string = base64.b64decode(top_parameters)
        for p in param_string.split('&') :
            key, value = p.split('=')
            params[key] = value
        return params

    def _get_timestamp(self):
        #gmtimefix = 28800
        #stime = time.gmtime(time.time() - time.timezone + gmtimefix)
        if(time.timezone == 0):
            gmtimefix = 28800
            stime = time.gmtime(gmtimefix + time.time())
        else:
            stime = time.localtime()
        strtime = time.strftime('%Y-%m-%d %H:%M:%S', stime)
        return strtime


    def _get_top_resp(self, url, params):
        try:
            crl = pycurl.Curl()
            #debug
            #crl.setopt(pycurl.VERBOSE,1)
            crl.setopt(pycurl.CONNECTTIMEOUT, 60)
            crl.setopt(pycurl.TIMEOUT, 300)

            crl.setopt(pycurl.NOSIGNAL, 1)

            crl.setopt(crl.POSTFIELDS,  urllib.urlencode(params))
            crl.setopt(pycurl.URL, self.top_url)
            crl.fp = StringIO.StringIO()
            crl.setopt(crl.WRITEFUNCTION, crl.fp.write)
            crl.perform()
            rsp = crl.fp.getvalue()
            return rsp
        except:
            return None

    def execute(self, method_name, **kwargs):
        #构造参数
        params = {}
        for k, v in kwargs.iteritems():
            if v: params[k.lower()] = v
        params['app_key'] = self.app_key
        params['v'] = '2.0'
        params['sign_method'] = 'md5',
        params['format'] = 'json'
        params['partner_id'] = 'openerp_top_1.0'
        params['timestamp'] = self._get_timestamp()
        params['method'] = method_name
        params['session'] = self.session
        params['sign'] = self._sign(params)

        #_logger.info('%s(%s) response send -' % (method_name, params))
        curl_rsp = self._get_top_resp(self.top_url, params)
        if not curl_rsp: return None
        rsp = json.loads(curl_rsp, strict=False, object_hook =lambda x: _O(x))
        if rsp.has_key('error_response'):
            error_code = rsp['error_response']['code']
            if 'sub_msg' in rsp['error_response']:
                msg = rsp['error_response']['sub_msg']
            else:
                msg = rsp['error_response']['msg']

            raise TOPException(error_code, msg)
        else:
            rsp = rsp[method_name.replace('.','_')[7:] + '_response']
            if not rsp: return None
            _logger.info('%s(%s) response OK -' % (method_name, kwargs))
            return rsp

    def __call__(self, method_name, **kwargs):
        return self.execute(method_name, **kwargs)

    def stream(self, dbname, uid, stream_id, user_id, user_nick):
        from taobao_shop import TaobaoMsgRouter
        crl = pycurl.Curl()
        try:
            params = {}
            params['app_key'] = self.app_key
            params['user'] = user_id
            params['timestamp'] = self._get_timestamp()
            params['id'] = hashlib.md5(stream_id).hexdigest()
            params['sign'] = self._sign(params, True)

            #crl.setopt(pycurl.VERBOSE,1)
            crl.setopt(pycurl.CONNECTTIMEOUT, 60)
            #crl.setopt(pycurl.TIMEOUT, 30)
            crl.setopt(crl.POSTFIELDS,  urllib.urlencode(params))

            crl.setopt(pycurl.NOSIGNAL, 1)
            crl.setopt(pycurl.URL, self.stream_url)

            def _stream_callback(data):
                for line in data.split("\r\n"):
                    if line: TaobaoMsgRouter(dbname, uid, self.app_key, line, is_stream_data = True)

            crl.setopt(crl.WRITEFUNCTION, _stream_callback)
            crl.perform()
        except:
            _logger.warning('Taobao Stream Error!')
        finally:
            crl.close()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


########NEW FILE########
__FILENAME__ = taobao_user
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from osv import fields,osv
from taobao_base import TaobaoMixin
from .taobao_top import _O, TOPException

class taobao_shop(osv.osv, TaobaoMixin):
    _inherit = "taobao.shop"
    _columns = {
            # taobao user
            'taobao_user_category_id': fields.many2one('res.partner.category', u'淘宝用户分类', select=1, required=True),
            }

    _defaults = {
            }



class res_partner_bank(osv.osv, TaobaoMixin):
    _inherit = "res.partner.bank"

class res_partner_address(osv.osv, TaobaoMixin):
    _inherit = 'res.partner.address'
    _columns = {
            'taobao_full_address': fields.char(u'淘宝地址', size=512),
            }


class res_partner(osv.osv, TaobaoMixin):
    _inherit = 'res.partner'

    def _get_taobao_user_profile(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for user in self.browse(cr, uid, ids, context=context):
            res[user.id] = 'http://rate.taobao.com/rate.htm?user_id=%s' % user.taobao_user_id
        return res

    _columns = {
            'state': fields.related('address', 'state_id', type='many2one', relation='res.country.state', string=u'省份'),
            'taobao_user_id': fields.char(u'用户数字ID', size=64),
            'taobao_nick': fields.char(u'淘宝用户名', size=64),
            'taobao_user_profile': fields.function(_get_taobao_user_profile, type='char', string=u'淘宝用户信息'),
            'taobao_receive_sms_remind': fields.boolean(u'接收短信提醒'),
            'taobao_receive_email_remind': fields.boolean(u'接收邮件提醒'),
            }

    #_sql_constraints = [('taobao_user_id_uniq','unique(taobao_user_id)', 'Taobao User must be unique!')]
    _sql_constraints = [('taobao_nick_uniq','unique(taobao_nick)', 'Taobao Nick must be unique!')]

    _defaults = {
            'taobao_receive_sms_remind': True,
            'taobao_receive_email_remind': True,
            }


    def _top_user_get(self, top, nick=None):
        fields = [
                'user_id','uid','nick','sex', 'buyer_credit', 'seller_credit', 'zip', 'city',
                'state', 'country', 'district', 'area', 'created', 'last_visit', 'birthday',
                'type', 'has_more_pic', 'item_img_num', 'item_img_size', 'prop_img_num',
                'prop_img_size', 'auto_repost', 'promoted_type', 'status', 'alipay_bind',
                'consumer_protection', 'alipay_account', 'alipay_no', 'avatar', 'liangpin',
                'sign_food_seller_promise', 'has_shop', 'is_lightning_consignment', 'has_sub_stock'
                'is_golden_seller', 'vip_info', 'email', 'magazine_subscribe', 'vertical_market',
                'online_gaming',
                ]

        try:
            if nick:
                rsp =top('taobao.user.get', nick=nick, fields=fields)
            else:
                rsp =top('taobao.user.get', fields=fields)
        except TOPException:
            rsp = _O(dict(user = _O(dict(nick = nick))))

        if rsp and rsp.has_key('user'):
            top_user = rsp.user
            if top_user.has_key('buyer_credit'):
                top_user['buyer_credit_level'] = top_user.buyer_credit.level
                top_user['buyer_credit_score'] = top_user.buyer_credit.score
                top_user['buyer_credit_total_num'] = top_user.buyer_credit.total_num
                top_user['buyer_credit_good_num'] = top_user.buyer_credit.good_num
            if top_user.has_key('seller_credit'):
                top_user['seller_credit_level'] = top_user.seller_credit.level
                top_user['seller_credit_score'] = top_user.seller_credit.score
                top_user['seller_credit_total_num'] = top_user.seller_credit.total_num
                top_user['seller_credit_good_num'] = top_user.seller_credit.good_num
            return top_user
        else:
            return None




    # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

########NEW FILE########
__FILENAME__ = taobao_order_import
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from ..taobao_top import TOP
from osv import fields, osv
import datetime
import time
from ..taobao_shop import TaobaoMsgRouter

class taobao_order_import_line(osv.osv_memory):
    _name = "taobao.order.import.line"
    _description = "Taobao Order Import Line"
    _columns = {
            'tid': fields.char(u'淘宝交易编号', size = 64),
            'taobao_shop_id': fields.many2one('taobao.shop', 'Taobao Shop', required=True),
            'status': fields.selection([
                ('TRADE_NO_CREATE_PAY', u'没有创建支付宝交易'),
                ('WAIT_BUYER_PAY', u'等待买家付款'),
                ('WAIT_SELLER_SEND_GOODS', u'买家已付款,等待卖家发货'),
                ('WAIT_BUYER_CONFIRM_GOODS', u'卖家已发货,等待买家确认收货'),
                ('TRADE_BUYER_SIGNED', u'买家已签收,货到付款专用'),
                ('TRADE_FINISHED', u'交易成功'),
                ('TRADE_CLOSED', u'付款以后用户退款成功，交易自动关闭'),
                ('TRADE_CLOSED_BY_TAOBAO', u'付款以前，卖家或买家主动关闭交易')
                ],
                u'交易状态'),
            'buyer_nick': fields.char(u'买家', size = 128),
            'total_fee': fields.char(u'总价', size = 128),
            'pay_time': fields.char(u'付款时间', size = 128),
            'wizard_id' : fields.many2one('taobao.order.import', string="Wizard"),
            }

class taobao_order_import(osv.osv_memory):
    _name = "taobao.order.import"
    _description = "Import Taobao Order"
    _columns = {
            'taobao_shop_id': fields.many2one('taobao.shop', 'Taobao Shop', required=True),
            'order_time': fields.selection([
                (1, u'最近一天'),
                (3, u'最近三天'),
                (7, u'最近一周'),
                (15, u'最近半个月'),
                (30, u'最近一个月'),
                (90, u'最近三个月'),
                ],
                u'时间过滤', required=True),
            'TRADE_NO_CREATE_PAY': fields.boolean(u'没有创建支付宝交易'),
            'WAIT_BUYER_PAY': fields.boolean(u'等待买家付款'),
            'WAIT_SELLER_SEND_GOODS': fields.boolean(u'买家已付款,等待卖家发货'),
            'WAIT_BUYER_CONFIRM_GOODS': fields.boolean(u'卖家已发货,等待买家确认收货'),
            'TRADE_BUYER_SIGNED': fields.boolean(u'买家已签收,货到付款专用'),
            'TRADE_FINISHED': fields.boolean(u'交易成功'),
            'TRADE_CLOSED': fields.boolean(u'付款以后用户退款成功，交易自动关闭'),
            'TRADE_CLOSED_BY_TAOBAO': fields.boolean(u'付款以前，卖家或买家主动关闭交易'),

            'order_import_lines' : fields.one2many('taobao.order.import.line', 'wizard_id', u'淘宝产品列表'),
            }
    _defaults = {
            'order_time': 7,
            'WAIT_SELLER_SEND_GOODS': True,
            'WAIT_BUYER_CONFIRM_GOODS': True,
            }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(taobao_order_import, self).default_get(cr, uid, fields, context=context)


        if 'order_import_lines' in fields and context.has_key('order_import_lines'):
            res.update({'order_import_lines': context['order_import_lines']})

        if 'order_time' in fields and context.has_key('order_time'):
            res.update({'order_time': context['order_time']})

        if 'taobao_shop_id' in fields:
            if context.get('taobao_shop_id', False):
                res.update({'taobao_shop_id': context['taobao_shop_id']})
            else:
                active_model = context.get('active_model', False)
                active_ids = context.get('active_ids', False)
                if active_model == 'taobao.shop' and active_ids:
                    taobao_shop = self.pool.get('taobao.shop').browse(cr, uid, active_ids[0], context=context)
                    if taobao_shop: res.update({'taobao_shop_id':taobao_shop.id})
                if active_model == 'sale.order' and active_ids:
                    sale_orders = self.pool.get('sale.order').browse(cr, uid, active_ids, context=context)
                    lines = []
                    for order in sale_orders:
                        taobao_shop = order.taobao_shop_id
                        lines.append({
                            'tid': order.taobao_trade_id ,
                            'taobao_shop_id': order.taobao_shop_id.id ,
                            })
                        res.update({'taobao_shop_id':order.taobao_shop_id.id})
                    res.update({'order_import_lines': lines})

        if 'TRADE_NO_CREATE_PAY' in fields and context.has_key('TRADE_NO_CREATE_PAY'):
            res.update({'TRADE_NO_CREATE_PAY': context['TRADE_NO_CREATE_PAY']})
        if 'WAIT_BUYER_PAY' in fields and context.has_key('WAIT_BUYER_PAY'):
            res.update({'WAIT_BUYER_PAY': context['WAIT_BUYER_PAY']})
        if 'WAIT_SELLER_SEND_GOODS' in fields and context.has_key('WAIT_SELLER_SEND_GOODS'):
            res.update({'WAIT_SELLER_SEND_GOODS': context['WAIT_SELLER_SEND_GOODS']})
        if 'WAIT_BUYER_CONFIRM_GOODS' in fields and context.has_key('WAIT_BUYER_CONFIRM_GOODS'):
            res.update({'WAIT_BUYER_CONFIRM_GOODS': context['WAIT_BUYER_CONFIRM_GOODS']})
        if 'TRADE_BUYER_SIGNED' in fields and context.has_key('TRADE_BUYER_SIGNED'):
            res.update({'TRADE_BUYER_SIGNED': context['TRADE_BUYER_SIGNED']})
        if 'TRADE_FINISHED' in fields and context.has_key('TRADE_FINISHED'):
            res.update({'TRADE_FINISHED': context['TRADE_FINISHED']})
        if 'TRADE_CLOSED' in fields and context.has_key('TRADE_CLOSED'):
            res.update({'TRADE_CLOSED': context['TRADE_CLOSED']})
        if 'TRADE_CLOSED_BY_TAOBAO' in fields and context.has_key('TRADE_CLOSED_BY_TAOBAO'):
            res.update({'TRADE_CLOSED_BY_TAOBAO': context['TRADE_CLOSED_BY_TAOBAO']})
        return res


    def search_order(self, cr, uid, ids, context=None):
        if ids and ids[0]:
            order_import = self.browse(cr, uid, ids[0], context=context)
            context['taobao_shop_id'] = order_import.taobao_shop_id.id
            context['TRADE_NO_CREATE_PAY'] = order_import.TRADE_NO_CREATE_PAY
            context['WAIT_BUYER_PAY'] = order_import.WAIT_BUYER_PAY
            context['WAIT_SELLER_SEND_GOODS'] = order_import.WAIT_SELLER_SEND_GOODS
            context['WAIT_BUYER_CONFIRM_GOODS'] = order_import.WAIT_BUYER_CONFIRM_GOODS
            context['TRADE_BUYER_SIGNED'] = order_import.TRADE_BUYER_SIGNED
            context['TRADE_FINISHED'] = order_import.TRADE_FINISHED
            context['TRADE_CLOSED'] = order_import.TRADE_CLOSED
            context['TRADE_CLOSED_BY_TAOBAO'] = order_import.TRADE_CLOSED_BY_TAOBAO

            order_status = []
            if order_import.TRADE_NO_CREATE_PAY: order_status.append('TRADE_NO_CREATE_PAY')
            if order_import.WAIT_BUYER_PAY: order_status.append('WAIT_BUYER_PAY')
            if order_import.WAIT_SELLER_SEND_GOODS: order_status.append('WAIT_SELLER_SEND_GOODS')
            if order_import.WAIT_BUYER_CONFIRM_GOODS: order_status.append('WAIT_BUYER_CONFIRM_GOODS')
            if order_import.TRADE_BUYER_SIGNED: order_status.append('TRADE_BUYER_SIGNED')
            if order_import.TRADE_FINISHED: order_status.append('TRADE_FINISHED')
            if order_import.TRADE_CLOSED: order_status.append('TRADE_CLOSED')
            if order_import.TRADE_CLOSED_BY_TAOBAO: order_status.append('TRADE_CLOSED_BY_TAOBAO')

            shop = order_import.taobao_shop_id
            top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)

            context['order_time'] = order_import.order_time
            if order_import.order_time == 90:
                taobao_orders = self.pool.get('sale.order')._top_sold_get(top, order_status)
            else:
                now = datetime.datetime(*tuple(time.gmtime())[:6]) + datetime.timedelta(hours=8)
                end_created = now.strftime('%Y-%m-%d %H:%M:%S')
                start_created = (now - datetime.timedelta(days=order_import.order_time)).strftime('%Y-%m-%d %H:%M:%S')
                taobao_orders = self.pool.get('sale.order')._top_sold_get(top, order_status, start_created = start_created, end_created = end_created)

            for i in range(len(taobao_orders)):
                taobao_orders[i]['taobao_shop_id'] = order_import.taobao_shop_id.id

            context['order_import_lines'] = taobao_orders

        return {
                'name': 'Import Product',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'taobao.order.import',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context
                }


    def import_order(self, cr, uid, ids, context=None):
        if ids and ids[0]:
            order_import = self.browse(cr, uid, ids[0], context=context)

            for line in order_import.order_import_lines:
                shop = line.taobao_shop_id
                job = {"taobao_app_key": shop.taobao_app_key, "packet": {"msg": {"import_taobao_order":{"tid": line.tid, "status": line.status if line.status else None }}, "code": 9999}}
                TaobaoMsgRouter(cr.dbname, uid, shop.taobao_app_key, job)


        return {
                'type': 'ir.actions.act_window_close',
                }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

########NEW FILE########
__FILENAME__ = taobao_picking_update
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from osv import fields, osv
from ..taobao_top import TOP

class taobao_picking_update_line(osv.osv_memory):
    _name = "taobao.picking.update.line"
    _description = "Taobao Picking Stock Update Line"
    _columns = {
            'taobao_product_id': fields.many2one('taobao.product', 'Taobao Product'),
            'product_product_id': fields.many2one('product.product', 'Product'),
            'qty': fields.float(u'数量', required=True),
            'taobao_num_iid': fields.char(u'商品数字编码', size = 64),
            'taobao_sku_id': fields.char(u'Sku id', size = 64),
            'taobao_shop_id': fields.many2one('taobao.shop', 'Taobao Shop'),
            'update_type': fields.selection([
                (1, u'全量更新'),
                (2, u'增量更新'),
                ],
                u'库存更新方式',
                ),
            'wizard_id' : fields.many2one('taobao.picking.update', string="Wizard"),
            }

    _defaults = {
            'update_type': 1,
            }



class taobao_picking_update(osv.osv_memory):
    _name = "taobao.picking.update"
    _description = "Taobao Picking Update"

    _columns = {
            'stock_update_lines' : fields.one2many('taobao.picking.update.line', 'wizard_id', u'产品列表'),
            }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(taobao_picking_update, self).default_get(cr, uid, fields, context=context)

        active_model = context.get('active_model', False)
        active_ids = context.get('active_ids', False)

        stock_update_lines = []
        if active_model == 'stock.picking' and active_ids:
            for picking in self.pool.get('stock.picking').browse(cr, uid, active_ids, context=context):
                for move in picking.move_lines:
                    qty = move.product_qty
                    for taobao_product in move.product_id.taobao_product_ids:
                        stock_update_lines.append({
                            'taobao_product_id' : taobao_product.id,
                            'product_product_id' : move.product_id.id,
                            'qty' : qty,
                            'taobao_num_iid': taobao_product.taobao_num_iid,
                            'taobao_sku_id': taobao_product.taobao_sku_id,
                            'taobao_shop_id': taobao_product.taobao_shop_id.id,
                            'update_type': 2,
                        })

        context['stock_update_lines'] = stock_update_lines

        if 'stock_update_lines' in fields and context.has_key('stock_update_lines'):
            res.update({'stock_update_lines': context['stock_update_lines']})

        return res

    def update_stock(self, cr, uid, ids, context=None):
        for stock_update_obj in self.browse(cr, uid, ids, context=context):
            for line in stock_update_obj.stock_update_lines:
                shop = line.taobao_shop_id
                top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
                self.pool.get('taobao.product')._top_item_quantity_update(top, line.qty, line.taobao_num_iid, sku_id = line.taobao_sku_id, update_type = line.update_type)

        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

########NEW FILE########
__FILENAME__ = taobao_product_import
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from ..taobao_top import TOP
from osv import fields, osv
import time
from ..taobao_shop import TaobaoMsgRouter

class taobao_product_search(osv.osv_memory):
    _name = "taobao.product.search"
    _description = "Search Taobao Item"
    _columns = {
            'taobao_shop_id': fields.many2one('taobao.shop', 'Taobao Shop', required=True),
            'taobao_search_q': fields.char(u'搜索关键字', size = 256),
            }

    def search_product(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        product_import_lines = []
        for top_search_obj in self.browse(cr, uid, ids, context=context):
            shop = top_search_obj.taobao_shop_id
            context['taobao_shop_id'] = shop.id
            top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
            items = self.pool.get('taobao.product')._top_items_get(shop, top, top_search_obj.taobao_search_q)
            for item in items:
                product_import_lines.append({
                    'taobao_item_num_iid': item.num_iid,
                    'taobao_item_title': item.title,
                    'taobao_item_pic_url': item.pic_url ,
                    'taobao_item_price': float(item.price),
                    #'taobao_item_volume': int(item.volume),
                    'taobao_item_volume': 0,
                    })

        context['product_import_lines'] = product_import_lines

        return {
            'name': 'Import Product',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'taobao.product.import',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False) or False
        res = super(taobao_product_search, self).default_get(cr, uid, fields, context=context)

        taobao_shop = self.pool.get('taobao.shop').browse(cr, uid, record_id, context=context)
        if 'taobao_shop_id' in fields and taobao_shop:
            res.update({'taobao_shop_id':taobao_shop.id})
        return res

class taobao_product_import_line(osv.osv_memory):
    _name = "taobao.product.import.line"
    _description = "Taobao Product Import Line"
    _columns = {
            'taobao_item_num_iid': fields.char(u'淘宝产品数字编号', size = 128, required=True),
            'taobao_item_title': fields.char(u'淘宝产品标题', size = 128),
            'taobao_item_pic_url': fields.char(u'图片地址', size = 256),
            'taobao_item_price': fields.float(u'售价'),
            'taobao_item_volume': fields.integer(u'最近成交量'),
            'wizard_id' : fields.many2one('taobao.product.import', string="Wizard"),
            }


class taobao_product_import(osv.osv_memory):
    _name = "taobao.product.import"
    _description = "Import Taobao Product"
    _columns = {
            'taobao_shop_id': fields.many2one('taobao.shop', 'Taobao Shop', required=True),
            'taobao_product_category_id': fields.many2one('product.category', u'淘宝产品分类', select=1, required=True, domain="[('type','=','normal')]"),
            'taobao_product_supplier' : fields.many2one('res.partner', 'Supplier', required=True,domain = [('supplier','=',True)], ondelete='cascade', help="Supplier of this product"),
            'taobao_product_location_id': fields.many2one('stock.location', u'淘宝产品库位', required=True, domain="[('usage', '=', 'internal')]"),

            'taobao_product_warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True, ondelete="cascade"),
            'taobao_product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
            'taobao_product_cost_method': fields.selection([('standard','Standard Price'), ('average','Average Price')], 'Costing Method', required=True,
            help="Standard Price: the cost price is fixed and recomputed periodically (usually at the end of the year), Average Price: the cost price is recomputed at each reception of products."),
            'taobao_product_type': fields.selection([('product','Stockable Product'),('consu', 'Consumable'),('service','Service')], 'Product Type', required=True, help="Will change the way procurements are processed. Consumable are product where you don't manage stock."),
            'taobao_product_supply_method': fields.selection([('produce','Produce'),('buy','Buy')], 'Supply method', required=True, help="Produce will generate production order or tasks, according to the product type. Buy will trigger purchase orders when requested."),
            'taobao_product_procure_method': fields.selection([('make_to_stock','Make to Stock'),('make_to_order','Make to Order')], 'Procurement Method', required=True, help="'Make to Stock': When needed, take from the stock or wait until re-supplying. 'Make to Order': When needed, purchase or produce for the procurement request."),
            'taobao_product_min_qty': fields.float('Min Quantity', required=True,
            help="When the virtual stock goes below the Min Quantity specified for this field, OpenERP generates "\
            "a procurement to bring the virtual stock to the Max Quantity."),
            'taobao_product_max_qty': fields.float('Max Quantity', required=True,
            help="When the virtual stock goes below the Min Quantity, OpenERP generates "\
            "a procurement to bring the virtual stock to the Quantity specified as Max Quantity."),

            'is_update_stock': fields.boolean(u'是否更新库存'),
            'product_import_lines' : fields.one2many('taobao.product.import.line', 'wizard_id', u'淘宝产品列表'),
            }
    _defaults = {
            'is_update_stock': True,
            }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(taobao_product_import, self).default_get(cr, uid, fields, context=context)
        if 'product_import_lines' in fields and context.get('product_import_lines', False):
            res.update({'product_import_lines': context['product_import_lines']})

        taobao_shop = self.pool.get('taobao.shop').browse(cr, uid, context.get('taobao_shop_id', False), context=context)
        if 'taobao_shop_id' in fields and taobao_shop:
            res.update({'taobao_shop_id':taobao_shop.id})

        if 'taobao_product_category_id' in fields and taobao_shop:
            res.update({'taobao_product_category_id': taobao_shop.taobao_product_category_id.id})
        if 'taobao_product_supplier' in fields and taobao_shop:
            res.update({'taobao_product_supplier': taobao_shop.taobao_product_supplier.id})
        if 'taobao_product_location_id' in fields and taobao_shop:
            res.update({'taobao_product_location_id': taobao_shop.taobao_product_location_id.id})
        if 'taobao_product_warehouse_id' in fields and taobao_shop:
            res.update({'taobao_product_warehouse_id': taobao_shop.taobao_product_warehouse_id.id})
        if 'taobao_product_uom' in fields and taobao_shop:
            res.update({'taobao_product_uom': taobao_shop.taobao_product_uom.id})
        if 'taobao_product_cost_method' in fields and taobao_shop:
            res.update({'taobao_product_cost_method': taobao_shop.taobao_product_cost_method})
        if 'taobao_product_type' in fields and taobao_shop:
            res.update({'taobao_product_type': taobao_shop.taobao_product_type})
        if 'taobao_product_supply_method' in fields and taobao_shop:
            res.update({'taobao_product_supply_method': taobao_shop.taobao_product_supply_method})
        if 'taobao_product_procure_method' in fields and taobao_shop:
            res.update({'taobao_product_procure_method': taobao_shop.taobao_product_procure_method})
        if 'taobao_product_min_qty' in fields and taobao_shop:
            res.update({'taobao_product_min_qty': taobao_shop.taobao_product_min_qty})
        if 'taobao_product_max_qty' in fields and taobao_shop:
            res.update({'taobao_product_max_qty': taobao_shop.taobao_product_max_qty})

        return res

    def import_product(self, cr, uid, ids, context=None):
        for product_import_obj in self.browse(cr, uid, ids, context=context):

            shop = product_import_obj.taobao_shop_id
            top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)

            for line in product_import_obj.product_import_lines:
                job = {"taobao_app_key": top.app_key, "packet": {"msg": {
                    "import_taobao_product":{
                        "taobao_num_iid": line.taobao_item_num_iid,
                        "taobao_product_category_id": product_import_obj.taobao_product_category_id.id,
                        "taobao_product_supplier": product_import_obj.taobao_product_supplier.id,
                        "taobao_product_warehouse_id": product_import_obj.taobao_product_warehouse_id.id,
                        "taobao_product_location_id": product_import_obj.taobao_product_location_id.id,
                        "taobao_product_cost_method": product_import_obj.taobao_product_cost_method,
                        "taobao_product_type": product_import_obj.taobao_product_type,
                        "taobao_product_supply_method": product_import_obj.taobao_product_supply_method,
                        "taobao_product_procure_method": product_import_obj.taobao_product_procure_method,
                        "taobao_product_min_qty": product_import_obj.taobao_product_min_qty,
                        "taobao_product_max_qty": product_import_obj.taobao_product_max_qty,
                        "taobao_product_uom": product_import_obj.taobao_product_uom.id,
                        "is_update_stock": product_import_obj.is_update_stock,
                        }
                    }, "code": 9999}}
                TaobaoMsgRouter(cr.dbname, uid, shop.taobao_app_key, job)

        return {
                'type': 'ir.actions.act_window_close',
                }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

########NEW FILE########
__FILENAME__ = taobao_stock_update
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from ..taobao_top import TOP
from osv import fields, osv

class taobao_stock_update_line(osv.osv_memory):
    _name = "taobao.stock.update.line"
    _description = "Taobao Stock Update Line"
    _columns = {
            'taobao_product_id': fields.many2one('taobao.product', 'Taobao Product'),
            'product_product_id': fields.many2one('product.product', 'Product'),
            'qty': fields.float(u'数量', required=True),
            'taobao_num_iid': fields.char(u'商品数字编码', size = 64),
            'taobao_sku_id': fields.char(u'Sku id', size = 64),
            'taobao_shop_id': fields.many2one('taobao.shop', 'Taobao Shop'),
            'update_type': fields.selection([
                (1, u'全量更新'),
                (2, u'增量更新'),
                ],
                u'库存更新方式',
                ),
            'wizard_id' : fields.many2one('taobao.stock.update', string="Wizard"),
            }

    _defaults = {
            'update_type': 1,
            }



class taobao_stock_update(osv.osv_memory):
    _name = "taobao.stock.update"
    _description = "Update Taobao Stock"
    _columns = {
            'stock_update_lines' : fields.one2many('taobao.stock.update.line', 'wizard_id', u'产品列表'),
            }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(taobao_stock_update, self).default_get(cr, uid, fields, context=context)
        active_model = context.get('active_model', False)
        active_ids = context.get('active_ids', False)

        stock_update_lines = []
        if active_model == 'taobao.product' and active_ids:
            for taobao_product_obj in self.pool.get('taobao.product').browse(cr, uid, active_ids, context=context):
                stock_update_lines.append({
                    'taobao_product_id' : taobao_product_obj.id,
                    'product_product_id' : taobao_product_obj.product_product_id.id,
                    'qty' : taobao_product_obj.product_product_id.taobao_qty_available,
                    'taobao_num_iid': taobao_product_obj.taobao_num_iid,
                    'taobao_sku_id': taobao_product_obj.taobao_sku_id,
                    'taobao_shop_id': taobao_product_obj.taobao_shop_id.id,
                    'update_type': 1,
                })

        if active_model == 'product.product' and active_ids:
            for product_product_obj in self.pool.get('product.product').browse(cr, uid, active_ids, context=context):
                for taobao_product_obj in product_product_obj.taobao_product_ids:
                    stock_update_lines.append({
                        'taobao_product_id' : taobao_product_obj.id,
                        'product_product_id' : taobao_product_obj.product_product_id.id,
                        'qty' : taobao_product_obj.product_product_id.taobao_qty_available,
                        'taobao_num_iid': taobao_product_obj.taobao_num_iid,
                        'taobao_sku_id': taobao_product_obj.taobao_sku_id,
                        'taobao_shop_id': taobao_product_obj.taobao_shop_id.id,
                        'update_type': 1,
                    })

        context['stock_update_lines'] = stock_update_lines

        if 'stock_update_lines' in fields and context.has_key('stock_update_lines'):
            res.update({'stock_update_lines': context['stock_update_lines']})

        return res


    def update_stock(self, cr, uid, ids, context=None):
        for stock_update_obj in self.browse(cr, uid, ids, context=context):
            for line in stock_update_obj.stock_update_lines:
                shop = line.taobao_shop_id
                top = TOP(shop.taobao_app_key, shop.taobao_app_secret, shop.taobao_session_key)
                self.pool.get('taobao.product')._top_item_quantity_update(top, line.qty, line.taobao_num_iid, sku_id = line.taobao_sku_id, update_type = line.update_type)

        return {
                'type': 'ir.actions.act_window_close',
                }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

########NEW FILE########
__FILENAME__ = __openerp__
# -*- coding: utf-8 -*-
##############################################################################
#    Taobao OpenERP Connector
#    Copyright 2012 wangbuke <wangbuke@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

{
    "name": "Taobao OpenERP Connector",
    "author" : "wangbuke@gmail.com",
    'website': 'http://my.oschina.net/wangbuke',
    'category': 'Sales Management',
    "depends" : [
        'base',
        'product',
        'account',
        'account_voucher',
        'sale',
        'stock',
        'delivery',
        'crm_helpdesk',
        ],
    "init_xml" : [
    ],
    "demo_xml" : [],
    'update_xml': [
           'security/ir.model.access.csv',
           'data/res.country.state.csv',
           'data/bank_data.xml',
           'data/delivery_data.xml',
           'taobao_shop_view.xml',
           'wizard/taobao_product_import.xml',
           'wizard/taobao_order_import.xml',
           'wizard/taobao_stock_update.xml',
           'wizard/taobao_picking_update.xml',
           'taobao_product_view.xml',
           'taobao_packet_view.xml',
           'taobao_order_view.xml',
           'taobao_user_view.xml',
           'taobao_rate_view.xml',
           'taobao_refund_view.xml',
           'taobao_delivery_tracking_view.xml',
    ],
    "description":
        """
        Taobao Connect Module

        系统要求：
            beanstalkd (windows 用户请搜索 cgywin beanstalkd)

        功能:
        1. 接受淘宝主动通知，自动添加、确认订单、发货等。
        2. 同步淘宝订单
        3. 导入淘宝产品, 同步库存
        4. 导入淘宝用户
        5. 自动评价，中差评预警
        6. 跟踪淘宝订单物流信息, 签收提醒
        7. .... 等等等 (懒的写了，自己发现吧)

        wangbuke@gmail.com

        """,
    "version": "0.1",
    'installable': True,
    'auto_install': False,
    "js": [],
    "css": [],
    'images': [],
}

########NEW FILE########
