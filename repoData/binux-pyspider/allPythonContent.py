__FILENAME__ = projectdb
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-09 11:28:52

import time

{
'project': {
        'name': str,
        'group': str,
        'status': str,
        'script': str,
        #'config': str,
        'comments': str,
        #'priority': int,
        'rate': int,
        'burst': int,
        'updatetime': int,
        }
}

class ProjectDB(object):
    status_str = [
            'TODO',
            'STOP',
            'CHECKING',
            'DEBUG',
            'RUNNING',
            ]

    def insert(self, name, obj={}):
        raise NotImplementedError

    def update(self, name, obj={}, **kwargs):
        raise NotImplementedError

    def get_all(self, fields=None):
        raise NotImplementedError

    def get(self, name, fields):
        raise NotImplementedError

    def check_update(self, timestamp, fields=None):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = taskdb
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-08 10:28:48

# task schema
{
'task': {
        'taskid': str, # new, not change
        'project': str, # new, not change
        'url': str, # new, not change
        'status': int, # change
        'schedule': {
            'priority': int,
            'retries': int,
            'retried': int,
            'exetime': int,
            'age': int,
            'itag': str, #
            #'recrawl': int
            }, # new and restart
        'fetch': {
            'method': str,
            'headers': dict, 
            'data': str, 
            'timeout': int,
            'save': dict,
            }, # new and restart 
        'process': {
            'callback': str,
            }, # new and restart
        'track': {
            'fetch': {
                'ok': bool,
                'time': int,
                'status_code': int,
                'headers': dict, 
                'encoding': str,
                'content': str,
                },
            'process': {
                'ok': bool,
                'time': int,
                'follows': int,
                'outputs': int,
                'logs': str,
                'exception': str,
                },
            }, # finish
        'lastcrawltime': int, # keep between request
        'updatetime': int, # keep between request
        }
}


class TaskDB(object):
    ACTIVE = 1
    SUCCESS = 2
    FAILED = 3
    BAD = 4

    def load_tasks(self, status, project=None, fields=None):
        raise NotImplementedError

    def get_task(self, project, taskid, fields=None):
        raise NotImplementedError

    def status_count(self, project):
        '''
        return a dict
        '''
        raise NotImplementedError

    def insert(self, project, taskid, obj={}):
        raise NotImplementedError
        
    def update(self, project, taskid, obj={}, **kwargs):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = basedb
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.com>
#         http://binux.me
# Created on 2012-08-30 17:43:49

import logging
logger = logging.getLogger()

class BaseDB:
    '''
    BaseDB

    dbcur should be overwirte
    '''
    @property
    def dbcur(self):
        raise NotImplementedError

    def _execute(self, sql_query, values=[]):
        ret = self.dbcur.execute(sql_query, values)
        self.conn.commit()
        return ret
    
    def _select(self, tablename=None, what="*", where="", offset=0, limit=None):
        tablename = tablename or self.__tablename__
        sql_query = "SELECT %s FROM '%s'" % (what, tablename)
        if where: sql_query += " WHERE %s" % where
        if limit: sql_query += " LIMIT %d, %d" % (offset, limit)
        logger.debug("<sql: %s>" % sql_query)

        return self._execute(sql_query).fetchall()

    def _select2dic(self, tablename=None, what="*", where="", offset=0, limit=None):
        tablename = tablename or self.__tablename__
        sql_query = "SELECT %s FROM '%s'" % (what, tablename)
        if where: sql_query += " WHERE %s" % where
        if limit: sql_query += " LIMIT %d, %d" % (offset, limit)
        logger.debug("<sql: %s>" % sql_query)

        dbcur = self._execute(sql_query)
        fields = [f[0] for f in dbcur.description]
        if limit:
            return [dict(zip(fields, row)) for row in dbcur.fetchall()]
        else:
            def iterall():
                row = dbcur.fetchone()
                while row:
                    yield dict(zip(fields, row))
                    row = dbcur.fetchone()
            return iterall()
 
    def _replace(self, tablename=None, **values):
        tablename = tablename or self.__tablename__
        if values:
            _keys = ", ".join(("`%s`" % k for k in values.iterkeys()))
            _values = ", ".join(["?", ] * len(values))
            sql_query = "REPLACE INTO `%s` (%s) VALUES (%s)" % (tablename, _keys, _values)
        else:
            sql_query = "REPLACE INTO %s DEFAULT VALUES" % tablename
        logger.debug("<sql: %s>" % sql_query)
        
        if values:
            dbcur = self._execute(sql_query, values.values())
        else:
            dbcur = self._execute(sql_query)
        return dbcur.lastrowid
 
    def _insert(self, tablename=None, **values):
        tablename = tablename or self.__tablename__
        if values:
            _keys = ", ".join(("`%s`" % k for k in values.iterkeys()))
            _values = ", ".join(["?", ] * len(values))
            sql_query = "INSERT INTO `%s` (%s) VALUES (%s)" % (tablename, _keys, _values)
        else:
            sql_query = "INSERT INTO %s DEFAULT VALUES" % tablename
        logger.debug("<sql: %s>" % sql_query)
        
        if values:
            dbcur = self._execute(sql_query, values.values())
        else:
            dbcur = self._execute(sql_query)
        return dbcur.lastrowid

    def _update(self, tablename=None, where="1=0", **values):
        tablename = tablename or self.__tablename__
        _key_values = ", ".join(["`%s` = ?" % k for k in values.iterkeys()]) 
        sql_query = "UPDATE %s SET %s WHERE %s" % (tablename, _key_values, where)
        logger.debug("<sql: %s>" % sql_query)
        
        return self._execute(sql_query, values.values())
    
    def _delete(self, tablename=None, where="1=0"):
        tablename = tablename or self.__tablename__
        sql_query = "DELETE FROM '%s'" % tablename
        if where: sql_query += " WHERE %s" % where
        logger.debug("<sql: %s>" % sql_query)

        return self._execute(sql_query)

if __name__ == "__main__":
    import sqlite3
    class DB(BaseDB):
        __tablename__ = "test"
        def __init__(self):
            self.conn = sqlite3.connect(":memory:")
            cursor = self.conn.cursor()
            cursor.execute('''CREATE TABLE `%s` (id INTEGER PRIMARY KEY AUTOINCREMENT, name, age)'''
                    % self.__tablename__)
              
        @property
        def dbcur(self):
            return self.conn.cursor()

    db = DB()
    assert db._insert(db.__tablename__, name="binux", age=23) == 1
    assert db._select(db.__tablename__, "name, age").fetchone() == ("binux", 23)
    assert db._select2dic(db.__tablename__, "name, age")[0]["name"] == "binux"
    assert db._select2dic(db.__tablename__, "name, age")[0]["age"] == 23
    db._replace(db.__tablename__, id=1, age=24)
    assert db._select(db.__tablename__, "name, age").fetchone() == (None, 24)
    db._update(db.__tablename__, "id = 1", age=16)
    assert db._select(db.__tablename__, "name, age").fetchone() == (None, 16)
    db._delete(db.__tablename__, "id = 1")
    assert db._select(db.__tablename__).fetchall() == []

########NEW FILE########
__FILENAME__ = projectdb
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-09 12:05:52

import re
import time
import sqlite3
from database.base.projectdb import ProjectDB as BaseProjectDB
from basedb import BaseDB


class ProjectDB(BaseProjectDB, BaseDB):
    __tablename__ = 'projectdb'
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self._execute('''CREATE TABLE IF NOT EXISTS `%s` (
                name PRIMARY KEY,
                `group`,
                status, script, comments,
                rate, burst, updatetime
                )''' % self.__tablename__)

    @property
    def dbcur(self):
        return self.conn.cursor()

    def insert(self, name, obj={}):
        obj = dict(obj)
        obj['name'] = name
        obj['updatetime'] = time.time()
        return self._insert(self.__tablename__, **obj)

    def update(self, name, obj={}, **kwargs):
        obj = dict(obj)
        obj.update(kwargs)
        obj['updatetime'] = time.time()
        ret = self._update(self.__tablename__, where="name = '%s'" % name, **obj)
        return ret.rowcount

    def get_all(self, fields=None):
        what = ','.join(('`%s`' % x for x in fields)) if fields else '*'
        return self._select2dic(self.__tablename__, what=what)

    def get(self, name, fields=None):
        what = ','.join(('`%s`' % x for x in fields)) if fields else '*'
        where = "name = '%s'" % name
        for each in self._select2dic(self.__tablename__, what=what, where=where):
            return each
        return None

    def check_update(self, timestamp, fields=None):
        what = ','.join(('`%s`' % x for x in fields)) if fields else '*'
        where = "updatetime >= %f" % timestamp
        return self._select2dic(self.__tablename__, what=what, where=where)

########NEW FILE########
__FILENAME__ = taskdb
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-08 10:25:34

import re
import time
import json
import sqlite3
from database.base.taskdb import TaskDB as BaseTaskDB
from basedb import BaseDB


class TaskDB(BaseTaskDB, BaseDB):
    __tablename__ = 'taskdb'
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self._list_project()

    @property
    def dbcur(self):
        return self.conn.cursor()

    def _list_project(self):
        self.projects = set()
        prefix = '%s_' % self.__tablename__
        for project, in self._select('sqlite_master', what='name',
                where='type = "table"'):
            if project.startswith(prefix):
                project = project[len(prefix):]
                self.projects.add(project)

    def _create_project(self, project):
        assert re.match(r'^\w+$', project) is not None
        tablename = '%s_%s' % (self.__tablename__, project)
        self._execute('''CREATE TABLE IF NOT EXISTS `%s` (
                taskid PRIMARY KEY,
                project,
                url, status,
                schedule, fetch, process, track,
                lastcrawltime, updatetime
                )''' % tablename)

    def _parse(self, data):
        for each in ('schedule', 'fetch', 'process', 'track'):
            if each in data:
                if data[each]:
                    data[each] = json.loads(data[each])
                else:
                    data[each] = {}
        return data

    def _stringify(self, data):
        for each in ('schedule', 'fetch', 'process', 'track'):
            if each in data:
                data[each] = json.dumps(data[each])
        return data

    def load_tasks(self, status, project=None, fields=None):
        if project and project not in self.projects:
            raise StopIteration
        what = ','.join(fields) if fields else '*'
        where = "status = %d" % status
        if project:
            tablename = '%s_%s' % (self.__tablename__, project)
            for each in self._select2dic(tablename, what=what, where=where):
                yield self._parse(each)
        else:
            for project in self.projects:
                tablename = '%s_%s' % (self.__tablename__, project)
                for each in self._select2dic(tablename, what=what, where=where):
                    yield self._parse(each)

    def get_task(self, project, taskid, fields=None):
        if project not in self.projects:
            self._list_project()
        if project not in self.projects:
            return None
        what = ','.join(fields) if fields else '*'
        where = "taskid = '%s'" % taskid
        if project not in self.projects:
            return None
        tablename = '%s_%s' % (self.__tablename__, project)
        for each in self._select2dic(tablename, what=what, where=where):
            return self._parse(each)
        return None

    def status_count(self, project):
        '''
        return a dict
        '''
        result = dict()
        if project not in self.projects:
            return result
        if project not in self.projects:
            return result
        tablename = '%s_%s' % (self.__tablename__, project)
        for status, count in self._execute("SELECT status, count(1) FROM '%s' GROUP BY status" % tablename).fetchall():
            result[status] = count
        return result

    def insert(self, project, taskid, obj={}):
        if project not in self.projects:
            self._create_project(project)
            self._list_project()
        obj = dict(obj)
        obj['taskid'] = taskid
        obj['project'] = project
        obj['updatetime'] = time.time()
        tablename = '%s_%s' % (self.__tablename__, project)
        self._insert(tablename, **self._stringify(obj))
        
    def update(self, project, taskid, obj={}, **kwargs):
        if project not in self.projects:
            raise LookupError
        tablename = '%s_%s' % (self.__tablename__, project)
        obj = dict(obj)
        obj.update(kwargs)
        obj['updatetime'] = time.time()
        self._update(tablename, where="taskid = '%s'" % taskid, **self._stringify(obj))

########NEW FILE########
__FILENAME__ = cookie_utils
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2012-09-12 22:39:57
# form requests&tornado

import UserDict
import cookielib
from urlparse import urlparse
from tornado import httpclient, httputil

class MockRequest(object):
    """Wraps a `tornado.httpclient.HTTPRequest` to mimic a `urllib2.Request`.

    The code in `cookielib.CookieJar` expects this interface in order to correctly
    manage cookie policies, i.e., determine whether a cookie can be set, given the
    domains of the request and the cookie.

    The original request object is read-only. The client is responsible for collecting
    the new headers via `get_new_headers()` and interpreting them appropriately. You
    probably want `get_cookie_header`, defined below.
    """

    def __init__(self, request):
        self._r = request
        self._new_headers = {}

    def get_type(self):
        return urlparse(self._r.url).scheme

    def get_host(self):
        return urlparse(self._r.url).netloc

    def get_origin_req_host(self):
        return self.get_host()

    def get_full_url(self):
        return self._r.url

    def is_unverifiable(self):
        # unverifiable == redirected
        return False

    def has_header(self, name):
        return name in self._r.headers or name in self._new_headers

    def get_header(self, name, default=None):
        return self._r.headers.get(name, self._new_headers.get(name, default))

    def add_header(self, key, val):
        """cookielib has no legitimate use for this method; add it back if you find one."""
        raise NotImplementedError("Cookie headers should be added with add_unredirected_header()")

    def add_unredirected_header(self, name, value):
        self._new_headers[name] = value

    def get_new_headers(self):
        return self._new_headers


class MockResponse(object):
    """Wraps a `tornado.httputil.HTTPHeaders` to mimic a `urllib.addinfourl`.

    ...what? Basically, expose the parsed HTTP headers from the server response
    the way `cookielib` expects to see them.
    """

    def __init__(self, headers):
        """Make a MockResponse for `cookielib` to read.

        :param headers: a httplib.HTTPMessage or analogous carrying the headers
        """
        self._headers = headers

    def info(self):
        return self._headers

    def getheaders(self, name):
        self._headers.get_list(name)

def create_cookie(name, value, **kwargs):
    """Make a cookie from underspecified parameters.

    By default, the pair of `name` and `value` will be set for the domain ''
    and sent on every request (this is sometimes called a "supercookie").
    """
    result = dict(
        version=0,
        name=name,
        value=value,
        port=None,
        domain='',
        path='/',
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={'HttpOnly': None},
        rfc2109=False,
        )

    badargs = set(kwargs) - set(result)
    if badargs:
        err = 'create_cookie() got unexpected keyword arguments: %s'
        raise TypeError(err % list(badargs))

    result.update(kwargs)
    result['port_specified'] = bool(result['port'])
    result['domain_specified'] = bool(result['domain'])
    result['domain_initial_dot'] = result['domain'].startswith('.')
    result['path_specified'] = bool(result['path'])

    return cookielib.Cookie(**result)

def remove_cookie_by_name(cookiejar, name, domain=None, path=None):
    """Unsets a cookie by name, by default over all domains and paths.

    Wraps CookieJar.clear(), is O(n).
    """
    clearables = []
    for cookie in cookiejar:
        if cookie.name == name:
            if domain is None or domain == cookie.domain:
                if path is None or path == cookie.path:
                    clearables.append((cookie.domain, cookie.path, cookie.name))

    for domain, path, name in clearables:
        cookiejar.clear(domain, path, name)

class CookieSession(cookielib.CookieJar, UserDict.DictMixin):
    def extract_cookies_to_jar(self, request, response):
        """Extract the cookies from the response into a CookieJar.

        :param jar: cookielib.CookieJar (not necessarily a RequestsCookieJar)
        :param request: our own requests.Request object
        :param response: urllib3.HTTPResponse object
        """
        # the _original_response field is the wrapped httplib.HTTPResponse object,
        req = MockRequest(request)
        # pull out the HTTPMessage with the headers and put it in the mock:
        headers = response
        if not hasattr(headers, "keys"):
            headers = headers.headers
        headers.getheaders = headers.get_list
        res = MockResponse(headers)
        self.extract_cookies(res, req)

    def get_cookie_header(self, request):
        """Produce an appropriate Cookie header string to be sent with `request`, or None."""
        r = MockRequest(request)
        self.add_cookie_header(r)
        return r.get_new_headers().get('Cookie')

    def __getitem__(self, name):
        if isinstance(name, cookielib.Cookie):
            return name.value
        for cookie in cookielib.CookieJar.__iter__(self):
            if cookie.name == name:
                return cookie.value
        raise KeyError(name)

    def __setitem__(self, name, value):
        if value is None:
            remove_cookie_by_name(self, name)
        else:
            self.set_cookie(create_cookie(name, value))

    def __delitem__(self, name):
        remove_cookie_by_name(self, name)

    def keys(self):
        result = []
        for cookie in cookielib.CookieJar.__iter__(self):
            result.append(cookie.name)
        return result

    def to_dict(self):
        result = {}
        for key in self.keys():
            result[key] = self.get(key)
        return result

class CookieTracker:
    def __init__(self):
        self.headers = httputil.HTTPHeaders()

    def get_header_callback(self):
        _self = self
        def header_callback(header):
            header = header.strip()
            if header.starswith("HTTP/"):
                return
            if not header:
                return
            _self.headers.parse_line(header)
        return header_callback

########NEW FILE########
__FILENAME__ = tornado_fetcher
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2012-12-17 11:07:19

import time
import Queue
import logging
import threading
import cookie_utils
import tornado.ioloop
import tornado.httputil
import tornado.httpclient
from tornado.curl_httpclient import CurlAsyncHTTPClient
from tornado.simple_httpclient import SimpleAsyncHTTPClient
from libs import dataurl, counter
logger = logging.getLogger('fetcher')

class MyCurlAsyncHTTPClient(CurlAsyncHTTPClient):
    def free_size(self):
        return len(self._free_list)
    def size(self):
        return len(self._curls) - self.free_size()

class MySimpleAsyncHTTPClient(SimpleAsyncHTTPClient):
    def free_size(self):
        return self.max_clients - self.size()
    def size(self):
        return len(self.active)

fetcher_output = {
        "status_code": int,
        "orig_url": str,
        "url": str,
        "headers": dict,
        "content": str,
        "cookies": dict,
        }

class Fetcher(object):
    user_agent = "BaiDuSpider"
    default_options = {
            'method': 'GET',
            'headers': {},
            'timeout': 120,
            }
    allowed_options = ['method', 'headers', 'data', 'timeout', 'allow_redirects', 'cookies', ]

    def __init__(self, inqueue, outqueue, poolsize=10, proxy=None, async=True):
        self.inqueue = inqueue
        self.outqueue = outqueue

        self.poolsize = poolsize
        self._running = False
        self._quit = False
        self.proxy = proxy
        self.async = async
        
        if async:
            self.http_client = MyCurlAsyncHTTPClient(max_clients=self.poolsize)
        else:
            self.http_client = tornado.httpclient.HTTPClient(MyCurlAsyncHTTPClient, max_clients=self.poolsize)

        self._cnt = {
                '5m': counter.CounterManager(
                    lambda : counter.TimebaseAverageWindowCounter(30, 10)),
                '1h': counter.CounterManager(
                    lambda : counter.TimebaseAverageWindowCounter(60, 60)),
                }

    def send_result(self, type, task, result):
        """type in ('data', 'http')"""
        if self.outqueue:
            try:
                self.outqueue.put((task, result))
            except Exception, e:
                logger.exception(e)
        
    def fetch(self, task, callback=None):
        url = task.get('url', 'data:,')
        if callback is None:
            callback = self.send_result
        if url.startswith('data:'):
            return self.data_fetch(url, task, callback)
        else:
            return self.http_fetch(url, task, callback)

    def sync_fetch(self, task):
        wait_result = threading.Condition()
        _result = {}
        def callback(type, task, result):
            wait_result.acquire()
            _result['type'] = type
            _result['task'] = task
            _result['result'] = result
            wait_result.notify()
            wait_result.release()
        self.fetch(task, callback=callback)

        wait_result.acquire()
        while 'result' not in _result:
            wait_result.wait()
        wait_result.release()
        return _result['result']


    def data_fetch(self, url, task, callback):
        self.on_fetch('data', task)
        result = {}
        result['orig_url'] = url
        result['content'] = dataurl.decode(url)
        result['status_code'] = 200
        result['url'] = url
        result['time'] = 0
        if len(result['content']) < 70:
            logger.info("[200] %s 0s" % url)
        else:
            logger.info("[200] data:,%s...[content:%d] 0s" % (result['content'][:70], len(result['content'])))

        callback('data', task, result)
        self.on_result('data', task, result)
        return task, result

    def http_fetch(self, url, task, callback):
        self.on_fetch('http', task)
        fetch = dict(self.default_options)
        fetch.setdefault('url', url)
        fetch.setdefault('headers', {})
        fetch.setdefault('allow_redirects', True)
        fetch.setdefault('use_gzip', True)
        fetch['headers'].setdefault('User-Agent', self.user_agent)
        task_fetch = task.get('fetch', {})
        for each in self.allowed_options:
            if each in task_fetch:
                fetch[each] = task_fetch[each]

        track_headers = task.get('track', {}).get('fetch', {}).get('headers', {})
        #proxy
        if self.proxy and task_fetch.get('proxy', True):
            fetch['proxy_host'] = self.proxy['http'].split(":")[0]
            fetch['proxy_port'] = int(self.proxy['http'].split(":")[1])
        #etag
        if task_fetch.get('etag', True):
            _t = task_fetch.get('etag') if isinstance(task_fetch.get('etag'), basestring) \
                                          else track_headers.get('etag')
            if _t:
                fetch['headers'].setdefault('If-None-Match', _t)
        #last modifed
        if task_fetch.get('last_modified', True):
            _t = task_fetch.get('last_modifed') \
                        if isinstance(task_fetch.get('last_modifed'), basestring) \
                        else track_headers.get('last-modified')
            if _t:
                fetch['headers'].setdefault('If-Modifed-Since', _t)

        #fix for tornado request obj
        cookie = None
        if 'allow_redirects' in fetch:
            fetch['follow_redirects'] = fetch['allow_redirects']
            del fetch['allow_redirects']
        if 'timeout' in fetch:
            fetch['connect_timeout'] = fetch['timeout']
            fetch['request_timeout'] = fetch['timeout']
            del fetch['timeout']
        if 'data' in fetch:
            fetch['body'] = fetch['data']
            del fetch['data']
        if 'cookies' in fetch:
            cookie = fetch['cookies']
            del fetch['cookies']

        def handle_response(response):
            response.headers = final_headers
            session.extract_cookies_to_jar(request, cookie_headers)
            if response.error and not isinstance(response.error, tornado.httpclient.HTTPError):
                result = {'status_code': 599, 'error': "%r" % response.error,
                          'time': time.time() - start_time, 'orig_url': url, 'url': url, }
                callback('http', task, result)
                self.on_result('http', task, result)
                return task, result
            result = {}
            result['orig_url'] = url
            result['content'] = response.body or ''
            result['headers'] = dict(response.headers)
            result['status_code'] = response.code
            result['url'] = response.effective_url or url
            result['cookies'] = session.to_dict()
            result['time'] = time.time() - start_time
            result['save'] = task_fetch.get('save')
            if 200 <= response.code < 300:
                logger.info("[%d] %s %.2fs" % (response.code, url, result['time']))
            else:
                logger.warning("[%d] %s %.2fs" % (response.code, url, result['time']))
            callback('http', task, result)
            self.on_result('http', task, result)
            return task, result

        def header_callback(line):
            line = line.strip()
            if line.startswith("HTTP/"):
                final_headers.clear()
                return
            if not line:
                return
            final_headers.parse_line(line)
            cookie_headers.parse_line(line)

        start_time = time.time()
        session = cookie_utils.CookieSession()
        cookie_headers = tornado.httputil.HTTPHeaders()
        final_headers = tornado.httputil.HTTPHeaders()
        try:
            request = tornado.httpclient.HTTPRequest(header_callback=header_callback, **fetch)
            if cookie:
                session.update(cookie)
                request.headers.add('Cookie', self.session.get_cookie_header(request))
            if self.async:
                response = self.http_client.fetch(request, handle_response)
            else:
                return handle_response(self.http_client.fetch(request))
        except Exception, e:
            result = {'status_code': 599, 'error': "%r" % e, 'time': time.time() - start_time,
                      'orig_url': url, 'url': url, }
            logger.error("[599] %s, %r %.2fs" % (url, e, result['time']))
            callback('http', task, result)
            self.on_result('http', task, result)
            return task, result

    def run(self):
        def queue_loop():
            if not self.outqueue or not self.inqueue:
                return
            while not self._quit:
                try:
                    if self.outqueue.full():
                        break
                    if self.http_client.free_size() <= 0:
                        break
                    task = self.inqueue.get_nowait()
                    self.fetch(task)
                except Queue.Empty:
                    break
                except KeyboardInterrupt:
                    break
                except Exception, e:
                    logger.exception(e)
                    break

        tornado.ioloop.PeriodicCallback(queue_loop, 100).start()
        self._running = True
        try:
            tornado.ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            pass

    def size(self):
        return self.http_client.size()

    def quit(self):
        self._running = False
        self._quit = True
        tornado.ioloop.IOLoop.instance().stop()

    def xmlrpc_run(self, port=24444, bind='127.0.0.1', logRequests=False):
        from SimpleXMLRPCServer import SimpleXMLRPCServer
        from xmlrpclib import Binary
        import cPickle as pickle

        server = SimpleXMLRPCServer((bind, port), allow_none=True, logRequests=logRequests)
        server.register_introspection_functions()
        server.register_multicall_functions()

        server.register_function(self.quit, '_quit')
        server.register_function(self.size)
        def sync_fetch(task):
            result = self.sync_fetch(task)
            result = Binary(pickle.dumps(result))
            return result
        server.register_function(sync_fetch, 'fetch')
        def dump_counter(_time, _type):
            return self._cnt[_time].to_dict(_type)
        server.register_function(dump_counter, 'counter')

        server.serve_forever()

    def on_fetch(self, type, task):
        """type in ('data', 'http')"""
        pass

    def on_result(self, type, task, result):
        """type in ('data', 'http')"""
        status_code = result.get('status_code', 599)
        if status_code != 599:
            status_code = (int(status_code) / 100 * 100)
        self._cnt['5m'].event((task.get('project'), status_code), +1)
        self._cnt['1h'].event((task.get('project'), status_code), +1)

        if type == 'http' and result.get('time'):
            content_len = len(result.get('content', ''))
            self._cnt['5m'].event((task.get('project'), 'speed'), float(content_len)/result.get('time'))
            self._cnt['1h'].event((task.get('project'), 'speed'), float(content_len)/result.get('time'))
            self._cnt['5m'].event((task.get('project'), 'time'), result.get('time'))
            self._cnt['1h'].event((task.get('project'), 'time'), result.get('time'))

########NEW FILE########
__FILENAME__ = base_handler
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-16 23:12:48

import os
import sys
import time
import inspect
import functools
import traceback
from libs.log import LogFormatter
from libs.url import quote_chinese, _build_url
from libs.utils import md5string, hide_me
from libs.ListIO import ListO
from libs.response import rebuild_response
from collections import namedtuple

class ProcessorResult(object):
    def __init__(self, result, follows, messages, logs, exception, extinfo):
        self.result = result
        self.follows = follows
        self.messages = messages
        self.logs = logs
        self.exception = exception
        self.extinfo = extinfo

    def rethrow(self):
        if self.exception:
            raise self.exception

    def logstr(self):
        result = []
        formater = LogFormatter(color=False)
        for record in self.logs:
            if isinstance(record, basestring):
                result.append(record)
                continue
            else:
                if record.exc_info:
                    a, b, tb = record.exc_info
                    tb = hide_me(tb, globals())
                    record.exc_info = a, b, tb
                result.append(formater.format(record))
                result.append('\n')
        return ''.join(result)

def catch_status_code_error(func):
    func._catch_status_code_error = True
    return func

def not_send_status(func):
    @functools.wraps(func)
    def wrapper(self, response, task):
        self._extinfo['not_send_status'] = True
        function = func.__get__(self, self.__class__)
        return self._run_func(function, response, task)
    return wrapper

def config(_config):
    def wrapper(func):
        func._config = _config
        return func
    return wrapper

def every(minutes=1):
    def wrapper(func):
        @functools.wraps(func)
        def on_cronjob(self, response, task):
            if response.save and 'tick' in response.save and response.save['tick'] % minutes == 0:
                function = func.__get__(self, self.__class__)
                return self._run_func(function, response, task)
            return None
        return on_cronjob
    return wrapper


class BaseHandlerMeta(type):
    def __new__(cls, name, bases, attrs):
        if '_on_message' in attrs:
            attrs['_on_message'] = not_send_status(attrs['_on_message'])
        if 'on_cronjob' in attrs:
            attrs['on_cronjob'] = not_send_status(attrs['on_cronjob'])
        return type.__new__(cls, name, bases, attrs)


class BaseHandler(object):
    __metaclass__ = BaseHandlerMeta

    def _reset(self):
        self._extinfo = {}
        self._messages = []
        self._follows = []

    def _run_func(self, function, *arguments):
        args, varargs, keywords, defaults = inspect.getargspec(function)
        return function(*arguments[:len(args)-1])

    def _run(self, task, response):
        self._reset()
        if isinstance(response, dict):
            response = rebuild_response(response)
        process = task.get('process', {})
        callback = process.get('callback', '__call__')
        if not hasattr(self, callback):
            raise NotImplementedError("self.%s() not implemented!" % callback)

        function = getattr(self, callback)
        if not getattr(function, '_catch_status_code_error', False):
            response.raise_for_status()
        return self._run_func(function, response, task)
            
    def run(self, module, task, response):
        logger = module.logger
        result = None
        exception = None
        stdout = sys.stdout

        try:
            sys.stdout = ListO(module.log_buffer)
            result = self._run(task, response)
            self._run_func(self.on_result, result, response, task)
        except Exception, e:
            logger.exception(e)
            exception = e
        finally:
            sys.stdout = stdout
            follows = self._follows
            messages = self._messages
            logs = module.log_buffer
            extinfo = self._extinfo

        return ProcessorResult(result, follows, messages, logs, exception, extinfo)

    def _crawl(self, url, **kwargs):
        task = {}

        if kwargs.get('callback'):
            callback = kwargs['callback']
            if isinstance(callback, basestring) and hasattr(self, callback):
                func = getattr(self, callback)
            elif hasattr(callback, 'im_self') and callback.im_self is self:
                func = callback
                kwargs['callback'] = func.__name__
            else:
                raise NotImplementedError("self.%s() not implemented!" % callback)
            if hasattr(func, '_config'):
                for k, v in func._config.iteritems():
                    kwargs.setdefault(k, v)

        if hasattr(self, 'crawl_config'):
            for k, v in self.crawl_config.iteritems():
                kwargs.setdefault(k, v)

        url = quote_chinese(_build_url(url.strip(), kwargs.get('params')))
        if kwargs.get('files'):
            assert isinstance(kwargs.get('data', {}), dict), "data must be a dict when using with files!"
            content_type, data = _encode_multipart_formdata(kwargs.get('data', {}),
                                                            kwargs.get('files', {}))
            kwargs.setdefault('headers', {})
            kwargs['headers']['Content-Type'] = content_type
            kwargs['data'] = data
        if kwargs.get('data'):
            kwargs['data'] = _encode_params(kwargs['data'])

        schedule = {}
        for key in ('priority', 'retries', 'exetime', 'age', 'itag', 'force_update'):
            if key in kwargs and kwargs[key] is not None:
                schedule[key] = kwargs[key]
        if schedule:
            task['schedule'] = schedule

        fetch = {}
        for key in ('method', 'headers', 'data', 'timeout', 'allow_redirects', 'cookies', 'proxy', 'etag', 'last_modifed', 'save'):
            if key in kwargs and kwargs[key] is not None:
                fetch[key] = kwargs[key]
        if fetch:
            task['fetch'] = fetch

        process = {}
        for key in ('callback', ):
            if key in kwargs and kwargs[key] is not None:
                process[key] = kwargs[key]
        if process:
            task['process'] = process

        task['project'] = self._project_name
        task['url'] = url
        task['taskid'] = task.get('taskid') or md5string(url)

        self._follows.append(task)
        return task

    # apis
    def crawl(self, url, **kwargs):
        '''
        params:
          url
          callback

          method
          params
          data
          files
          headers
          timeout
          allow_redirects
          cookies
          proxy
          etag
          last_modifed

          priority
          retries
          exetime
          age
          itag

          save
          taskid
        '''


        if isinstance(url, basestring):
            return self._crawl(url, **kwargs)
        elif hasattr(url, "__iter__"):
            result = []
            for each in url:
                result.append(self._crawl(each, **kwargs))
            return result

    def send_message(self, project, msg):
        self._messages.append((project, msg))

    @not_send_status
    def _on_message(self, response):
        project, msg = response.save
        return self.on_message(project, msg)

    def on_message(self, project, msg):
        pass

    def on_cronjob(self):
        pass

    def on_result(self, result):
        pass

########NEW FILE########
__FILENAME__ = counter
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2012-11-14 17:09:50

import time
import cPickle
import logging
from collections import deque
from UserDict import DictMixin

class BaseCounter(object): pass

class TotalCounter(BaseCounter):
    def __init__(self):
        self.cnt = 0

    def event(self, value):
        self.cnt += value

    def value(self, value):
        self.cnt = value

    @property
    def avg(self):
        return self.cnt

    @property
    def sum(self):
        return self.cnt

    def empty(self):
        return self.cnt == 0

class AverageWindowCounter(BaseCounter):
    def __init__(self, window_size=300):
        self.window_size = window_size
        self.values = deque(maxlen=window_size)

    def event(self, value=1):
        self.values.append(value)

    value = event
        
    @property
    def avg(self):
        return float(self.sum) / len(self.values)

    @property
    def sum(self):
        return sum(self.values)

    def empty(self):
        if not self.values:
            return True

class TimebaseAverageWindowCounter(BaseCounter):
    def __init__(self, window_size=30, window_interval=10):
        self.max_window_size = window_size
        self.window_size = 0
        self.window_interval = window_interval
        self.values = deque(maxlen=window_size)
        self.times = deque(maxlen=window_size)

        self.cache_value = 0
        self.cache_start = None
        self._first_data_time = None

    def event(self, value=1):
        now = time.time()
        if self._first_data_time is None:
            self._first_data_time = now

        if self.cache_start is None:
            self.cache_value = value
            self.cache_start = now
        elif now - self.cache_start > self.window_interval:
            self.values.append(self.cache_value)
            self.times.append(self.cache_start)
            self.on_append(self.cache_value, self.cache_start)
            self.cache_value = value
            self.cache_start = now
        else:
            self.cache_value += value
        return self

    def value(self, value):
        self.cache_value = value

    def _trim_window(self):
        now = time.time()
        if self.cache_start and now - self.cache_start > self.window_interval:
            self.values.append(self.cache_value)
            self.times.append(self.cache_start)
            self.on_append(self.cache_value, self.cache_start)
            self.cache_value = 0
            self.cache_start = None

        if self.window_size != self.max_window_size and self._first_data_time is not None:
            time_passed = now - self._first_data_time
            self.window_size = min(self.max_window_size, time_passed / self.window_interval)
        window_limit = now - self.window_size * self.window_interval
        while self.times and self.times[0] < window_limit:
            self.times.popleft()
            self.values.popleft()

    @property
    def avg(self):
        if not self.window_size:
            return 0
        return float(self.sum) / self.window_size / self.window_interval

    @property
    def sum(self):
        self._trim_window()
        return sum(self.values)+self.cache_value

    def empty(self):
        self._trim_window()
        if not self.values and not self.cache_start:
            return True

    def on_append(self, value, time):
        pass

class CounterValue(DictMixin):
    def __init__(self, manager, keys):
        self.manager = manager
        self._keys = keys

    def __getitem__(self, key):
        if key == '__value__':
            key = self._keys
            return self.manager.counters[key]
        else:
            key = self._keys + (key, )

        available_keys = []
        for _key in self.manager.counters:
            if _key[:len(key)] == key:
                available_keys.append(_key)

        if len(available_keys) == 0:
            raise KeyError
        elif len(available_keys) == 1:
            if available_keys[0] == key:
                return self.manager.counters[key]
            else:
                return CounterValue(self.manager, key)
        else:
            return CounterValue(self.manager, key)

    def keys(self):
        result = set()
        for key in self.manager.counters:
            if key[:len(self._keys)] == self._keys:
                key = key[len(self._keys):]
                result.add(key[0] if key else '__value__')
        return result

    def to_dict(self, get_value=None):
        result = {}
        for key, value in self.iteritems():
            if isinstance(value, BaseCounter):
                if get_value is not None:
                    value = getattr(value, get_value)
                result[key] = value
            else:
                result[key] = value.to_dict(get_value)
        return result

class CounterManager(DictMixin):
    def __init__(self, cls=TimebaseAverageWindowCounter):
        self.cls = cls
        self.counters = {}

    def event(self, key, value=1):
        if isinstance(key, basestring):
            key = (key, )
        assert isinstance(key, tuple), "event key type error"
        if key not in self.counters:
            self.counters[key] = self.cls()
        self.counters[key].event(value)
        return self

    def value(self, key, value=1):
        if isinstance(key, basestring):
            key = (key, )
        assert isinstance(key, tuple), "event key type error"
        if key not in self.counters:
            self.counters[key] = self.cls()
        self.counters[key].value(value)
        return self

    def trim(self):
        for key, value in self.counters.items():
            if value.empty():
                del self.counters[key]

    def __getitem__(self, key):
        key = (key, )
        available_keys = []
        for _key in self.counters:
            if _key[:len(key)] == key:
                available_keys.append(_key)

        if len(available_keys) == 0:
            raise KeyError
        elif len(available_keys) == 1:
            if available_keys[0] == key:
                return self.counters[key]
            else:
                return CounterValue(self, key)
        else:
            return CounterValue(self, key)

    def keys(self):
        result = set()
        for key in self.counters:
            result.add(key[0] if key else ())
        return result

    def to_dict(self, get_value=None):
        self.trim()
        result = {}
        for key, value in self.iteritems():
            if isinstance(value, BaseCounter):
                if get_value is not None:
                    value = getattr(value, get_value)
                result[key] = value
            else:
                result[key] = value.to_dict(get_value)
        return result

    def dump(self, filename):
        try:
            cPickle.dump(self.counters, open(filename, 'wb'))
        except:
            logging.error("can't dump counter to file: %s" % filename)
            return False
        return True

    def load(self, filename):
        try:
            self.counters = cPickle.load(open(filename))
        except:
            logging.error("can't load counter from file: %s" % filename)
            return False
        return True


########NEW FILE########
__FILENAME__ = dataurl
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2012-11-16 10:33:20

from urllib import quote, unquote

def encode(data, mime_type='', charset='utf-8', base64=True):
    if isinstance(data, unicode):
        data = data.encode(charset)
    else:
        charset = None
    if base64:
        data = data.encode('base64').replace('\n', '')
    else:
        data = quote(data)

    result = ['data:', ]
    if mime_type:
        result.append(mime_type)
    if charset:
        result.append(';charset=')
        result.append(charset)
    if base64:
        result.append(';base64')
    result.append(',')
    result.append(data)

    return ''.join(result)

def decode(data_url):
    metadata, data = data_url.rsplit(',', 1)
    _, metadata = metadata.split('data:', 1)
    parts = metadata.split(';')
    if parts[-1] == 'base64':
        data = data.decode("base64")
    else:
        data = unquote(data)

    for part in parts:
        if part.startswith("charset="):
            data = data.decode(part[8:])
    return data

if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = ListIO
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-26 23:41:51

class ListO(object):
    """A StringO write to list."""

    def __init__(self, buffer=None):
        self._buffer = buffer
        if self._buffer is None:
            self._buffer = []

    def isatty(self):
        return False

    def close(self):
        pass

    def flush(self):
        pass

    def seek(self, n, mode=0):
        pass

    def readline(self):
        pass

    def reset(self):
        pass

    def write(self, x):
        self._buffer.append(x)

    def writelines(self, x):
        self._buffer.extend(x)


########NEW FILE########
__FILENAME__ = log
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2012-10-24 16:08:17

import logging
import sys
import time

try:
    import curses
except ImportError:
    curses = None

def _unicode(message):
    if isinstance(message, unicode):
        return message
    for each in ['utf8', 'gb18030']:
        try:
            return message.decode(each)
        except Exception, e:
            error = e
    raise e

def _stderr_supports_color():
    color = False
    if curses and sys.stderr.isatty():
        try:
            curses.setupterm()
            if curses.tigetnum("colors") > 0:
                color = True
        except Exception:
            pass
    return color


class LogFormatter(logging.Formatter):
    """Log formatter used in Tornado.

    Key features of this formatter are:

    * Color support when logging to a terminal that supports it.
    * Timestamps on every log line.
    * Robust against str/bytes encoding problems.

    This formatter is enabled automatically by
    `tornado.options.parse_command_line` (unless ``--logging=none`` is
    used).
    """
    def __init__(self, color=True, *args, **kwargs):
        logging.Formatter.__init__(self, *args, **kwargs)
        self._color = color and _stderr_supports_color()
        if self._color:
            # The curses module has some str/bytes confusion in
            # python3.  Until version 3.2.3, most methods return
            # bytes, but only accept strings.  In addition, we want to
            # output these strings with the logging module, which
            # works with unicode strings.  The explicit calls to
            # unicode() below are harmless in python2 but will do the
            # right conversion in python 3.
            fg_color = (curses.tigetstr("setaf") or
                        curses.tigetstr("setf") or "")
            if (3, 0) < sys.version_info < (3, 2, 3):
                fg_color = unicode(fg_color, "ascii")
            self._colors = {
                logging.DEBUG: unicode(curses.tparm(fg_color, 4),  # Blue
                                       "ascii"),
                logging.INFO: unicode(curses.tparm(fg_color, 2),  # Green
                                      "ascii"),
                logging.WARNING: unicode(curses.tparm(fg_color, 3),  # Yellow
                                         "ascii"),
                logging.ERROR: unicode(curses.tparm(fg_color, 1),  # Red
                                       "ascii"),
            }
            self._normal = unicode(curses.tigetstr("sgr0"), "ascii")

    def format(self, record):
        try:
            record.message = record.getMessage()
        except Exception, e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)
        assert isinstance(record.message, basestring)  # guaranteed by logging
        record.asctime = time.strftime(
            "%y%m%d %H:%M:%S", self.converter(record.created))
        prefix = '[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d]' % \
            record.__dict__
        if self._color:
            prefix = (self._colors.get(record.levelno, self._normal) +
                      prefix + self._normal)

        # Encoding notes:  The logging module prefers to work with character
        # strings, but only enforces that log messages are instances of
        # basestring.  In python 2, non-ascii bytestrings will make
        # their way through the logging framework until they blow up with
        # an unhelpful decoding error (with this formatter it happens
        # when we attach the prefix, but there are other opportunities for
        # exceptions further along in the framework).
        #
        # If a byte string makes it this far, convert it to unicode to
        # ensure it will make it out to the logs.  Use repr() as a fallback
        # to ensure that all byte strings can be converted successfully,
        # but don't do it by default so we don't add extra quotes to ascii
        # bytestrings.  This is a bit of a hacky place to do this, but
        # it's worth it since the encoding errors that would otherwise
        # result are so useless (and tornado is fond of using utf8-encoded
        # byte strings whereever possible).
        try:
            message = _unicode(record.message)
        except UnicodeDecodeError:
            message = repr(record.message)

        formatted = prefix + " " + message
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            formatted = formatted.rstrip() + "\n" + _unicode(record.exc_text)
        return formatted.replace("\n", "\n    ")

class SaveLogHandler(logging.Handler):
    def __init__(self, saveto=None, *args, **kwargs):
        self.saveto = saveto
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        if self.saveto is not None:
            self.saveto.append(record)

    handle = emit

def enable_pretty_logging(logger=logging.getLogger()):
    channel = logging.StreamHandler()
    channel.setFormatter(LogFormatter())
    logger.addHandler(channel)

########NEW FILE########
__FILENAME__ = pprint
#  Author:      Fred L. Drake, Jr. 
#               fdrake@... 
# 
#  This is a simple little module I wrote to make life easier.  I didn't 
#  see anything quite like it in the library, though I may have overlooked 
#  something.  I wrote this when I was trying to read some heavily nested 
#  tuples with fairly non-descriptive content.  This is modeled very much 
#  after Lisp/Scheme - style pretty-printing of lists.  If you find it 
#  useful, thank small children who sleep at night. 

"""Support to pretty-print lists, tuples, & dictionaries recursively. 

Very simple, but useful, especially in debugging data structures. 

Classes 
------- 

PrettyPrinter() 
    Handle pretty-printing operations onto a stream using a configured 
    set of formatting parameters. 

Functions 
--------- 

pformat() 
    Format a Python object into a pretty-printed representation. 

pprint() 
    Pretty-print a Python object to a stream [default is sys.stdout]. 

saferepr() 
    Generate a 'standard' repr()-like value, but protect against recursive 
    data structures. 

""" 

import sys as _sys 
import warnings 
import locale 

from cStringIO import StringIO as _StringIO 

__all__ = ["pprint","pformat","isreadable","isrecursive","saferepr", 
           "PrettyPrinter"] 

# cache these for faster access: 
_commajoin = ", ".join 
_id = id 
_len = len 
_type = type 


def pprint(object, stream=None, indent=1, width=80, depth=None): 
    """Pretty-print a Python object to a stream [default is sys.stdout].""" 
    printer = PrettyPrinter( 
        stream=stream, indent=indent, width=width, depth=depth) 
    printer.pprint(object) 

def pformat(object, indent=1, width=80, depth=None): 
    """Format a Python object into a pretty-printed representation.""" 
    return PrettyPrinter(indent=indent, width=width, depth=depth).pformat(object) 

def saferepr(object): 
    """Version of repr() which can handle recursive data structures.""" 
    return _safe_repr(object, {}, None, 0)[0] 

def isreadable(object): 
    """Determine if saferepr(object) is readable by eval().""" 
    return _safe_repr(object, {}, None, 0)[1] 

def isrecursive(object): 
    """Determine if object requires a recursive representation.""" 
    return _safe_repr(object, {}, None, 0)[2] 

def _sorted(iterable): 
    with warnings.catch_warnings(): 
        if _sys.py3kwarning: 
            warnings.filterwarnings("ignore", "comparing unequal types " 
                                    "not supported", DeprecationWarning) 
        return sorted(iterable) 

class PrettyPrinter: 
    def __init__(self, indent=1, width=80, depth=None, stream=None): 
        """Handle pretty printing operations onto a stream using a set of 
        configured parameters. 

        indent 
            Number of spaces to indent for each level of nesting. 

        width 
            Attempted maximum number of columns in the output. 

        depth 
            The maximum depth to print out nested structures. 

        stream 
            The desired output stream.  If omitted (or false), the standard 
            output stream available at construction will be used. 

        """ 
        indent = int(indent) 
        width = int(width) 
        assert indent >= 0, "indent must be >= 0" 
        assert depth is None or depth > 0, "depth must be > 0" 
        assert width, "width must be != 0" 
        self._depth = depth 
        self._indent_per_level = indent 
        self._width = width 
        if stream is not None: 
            self._stream = stream 
        else: 
            self._stream = _sys.stdout 

    def pprint(self, object): 
        self._format(object, self._stream, 0, 0, {}, 0) 
        self._stream.write("\n") 

    def pformat(self, object): 
        sio = _StringIO() 
        self._format(object, sio, 0, 0, {}, 0) 
        return sio.getvalue() 

    def isrecursive(self, object): 
        return self.format(object, {}, 0, 0)[2] 

    def isreadable(self, object): 
        s, readable, recursive = self.format(object, {}, 0, 0) 
        return readable and not recursive 

    def _format(self, object, stream, indent, allowance, context, level): 
        level = level + 1 
        objid = _id(object) 
        if objid in context: 
            stream.write(_recursion(object)) 
            self._recursive = True 
            self._readable = False 
            return 
        rep = self._repr(object, context, level - 1) 
        typ = _type(object) 
        sepLines = _len(rep) > (self._width - 1 - indent - allowance) 
        write = stream.write 

        if self._depth and level > self._depth: 
            write(rep) 
            return 

        r = getattr(typ, "__repr__", None) 
        if issubclass(typ, dict) and r is dict.__repr__: 
            write('{') 
            if self._indent_per_level > 1: 
                write((self._indent_per_level - 1) * ' ') 
            length = _len(object) 
            if length: 
                context[objid] = 1 
                indent = indent + self._indent_per_level 
                items = _sorted(object.items()) 
                key, ent = items[0] 
                rep = self._repr(key, context, level) 
                write(rep) 
                write(': ') 
                self._format(ent, stream, indent + _len(rep) + 2, 
                              allowance + 1, context, level) 
                if length > 1: 
                    for key, ent in items[1:]: 
                        rep = self._repr(key, context, level) 
                        if sepLines: 
                            write(',\n%s%s: ' % (' '*indent, rep)) 
                        else: 
                            write(', %s: ' % rep) 
                        self._format(ent, stream, indent + _len(rep) + 2, 
                                      allowance + 1, context, level) 
                indent = indent - self._indent_per_level 
                del context[objid] 
            write('}') 
            return 

        if ((issubclass(typ, list) and r is list.__repr__) or 
            (issubclass(typ, tuple) and r is tuple.__repr__) or 
            (issubclass(typ, set) and r is set.__repr__) or 
            (issubclass(typ, frozenset) and r is frozenset.__repr__) 
           ): 
            length = _len(object) 
            if issubclass(typ, list): 
                write('[') 
                endchar = ']' 
            elif issubclass(typ, set): 
                if not length: 
                    write('set()') 
                    return 
                write('set([') 
                endchar = '])' 
                object = _sorted(object) 
                indent += 4 
            elif issubclass(typ, frozenset): 
                if not length: 
                    write('frozenset()') 
                    return 
                write('frozenset([') 
                endchar = '])' 
                object = _sorted(object) 
                indent += 10 
            else: 
                write('(') 
                endchar = ')' 
            if self._indent_per_level > 1 and sepLines: 
                write((self._indent_per_level - 1) * ' ') 
            if length: 
                context[objid] = 1 
                indent = indent + self._indent_per_level 
                self._format(object[0], stream, indent, allowance + 1, 
                             context, level) 
                if length > 1: 
                    for ent in object[1:]: 
                        if sepLines: 
                            write(',\n' + ' '*indent) 
                        else: 
                            write(', ') 
                        self._format(ent, stream, indent, 
                                      allowance + 1, context, level) 
                indent = indent - self._indent_per_level 
                del context[objid] 
            if issubclass(typ, tuple) and length == 1: 
                write(',') 
            write(endchar) 
            return 

        write(rep) 

    def _repr(self, object, context, level): 
        repr, readable, recursive = self.format(object, context.copy(), 
                                                self._depth, level) 
        if not readable: 
            self._readable = False 
        if recursive: 
            self._recursive = True 
        return repr 

    def format(self, object, context, maxlevels, level): 
        """Format object for a specific context, returning a string 
        and flags indicating whether the representation is 'readable' 
        and whether the object represents a recursive construct. 
        """ 
        return _safe_repr(object, context, maxlevels, level) 


# Return triple (repr_string, isreadable, isrecursive). 

def _safe_repr(object, context, maxlevels, level): 
    typ = _type(object) 
    if typ is str: 
        string = object 
        string = string.replace('\n', '\\n').replace('\r','\\r').replace('\t','\\t') 
        if 'locale' not in _sys.modules: 
            return repr(object), True, False 
        if "'" in object and '"' not in object: 
            closure = '"' 
            quotes = {'"': '\\"'} 
            string = string.replace('"','\\"') 
        else: 
            closure = "'" 
            quotes = {"'": "\\'"} 
            string = string.replace("'", "\\'") 
        try: 
            string.decode('utf8').encode('gbk', 'replace') 
            return ("%s%s%s" % (closure, string, closure)), True, False 
        except: 
            pass 
        qget = quotes.get 
        sio = _StringIO() 
        write = sio.write 
        for char in object: 
            if char.isalpha(): 
                write(char) 
            else: 
                write(qget(char, repr(char)[1:-1])) 
        return ("%s%s%s" % (closure, sio.getvalue(), closure)), True, False 

    if typ is unicode: 
        string = object.encode("utf8", 'replace') 
        string = string.replace('\n', '\\n').replace('\r','\\r').replace('\t','\\t') 
        if "'" in object and '"' not in object: 
            closure = '"' 
            quotes = {'"': '\\"'} 
            string = string.replace('"','\\"') 
        else: 
            closure = "'" 
            quotes = {"'": "\\'"} 
            string = string.replace("'", "\\'") 
        return ("u%s%s%s" % (closure, string, closure)), True, False 

    r = getattr(typ, "__repr__", None) 
    if issubclass(typ, dict) and r is dict.__repr__: 
        if not object: 
            return "{}", True, False 
        objid = _id(object) 
        if maxlevels and level >= maxlevels: 
            return "{...}", False, objid in context 
        if objid in context: 
            return _recursion(object), False, True 
        context[objid] = 1 
        readable = True 
        recursive = False 
        components = [] 
        append = components.append 
        level += 1 
        saferepr = _safe_repr 
        for k, v in _sorted(object.items()): 
            krepr, kreadable, krecur = saferepr(k, context, maxlevels, level) 
            vrepr, vreadable, vrecur = saferepr(v, context, maxlevels, level) 
            append("%s: %s" % (krepr, vrepr)) 
            readable = readable and kreadable and vreadable 
            if krecur or vrecur: 
                recursive = True 
        del context[objid] 
        return "{%s}" % _commajoin(components), readable, recursive 

    if (issubclass(typ, list) and r is list.__repr__) or \
        (issubclass(typ, tuple) and r is tuple.__repr__): 
        if issubclass(typ, list): 
            if not object: 
                return "[]", True, False 
            format = "[%s]" 
        elif _len(object) == 1: 
            format = "(%s,)" 
        else: 
            if not object: 
                return "()", True, False 
            format = "(%s)" 
        objid = _id(object) 
        if maxlevels and level >= maxlevels: 
            return format % "...", False, objid in context 
        if objid in context: 
            return _recursion(object), False, True 
        context[objid] = 1 
        readable = True 
        recursive = False 
        components = [] 
        append = components.append 
        level += 1 
        for o in object: 
            orepr, oreadable, orecur = _safe_repr(o, context, maxlevels, level) 
            append(orepr) 
            if not oreadable: 
                readable = False 
            if orecur: 
                recursive = True 
        del context[objid] 
        return format % _commajoin(components), readable, recursive 

    rep = repr(object) 
    return rep, (rep and not rep.startswith('<')), False 


def _recursion(object): 
    return ("<Recursion on %s with id=%s>" 
            % (_type(object).__name__, _id(object))) 


def _perfcheck(object=None): 
    import time 
    if object is None: 
        object = [("string", (1, 2), [3, 4], {5: 6, 7: 8})] * 100000 
    p = PrettyPrinter() 
    t1 = time.time() 
    _safe_repr(object, {}, None, 0) 
    t2 = time.time() 
    p.pformat(object) 
    t3 = time.time() 
    print "_safe_repr:", t2 - t1 
    print "pformat:", t3 - t2 

if __name__ == "__main__": 
    _perfcheck() 

########NEW FILE########
__FILENAME__ = rabbitmq
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2012-11-15 17:27:54

import time
import socket
import cPickle
import Queue as BaseQueue
from amqplib import client_0_8 as amqp

def catch_error(func):
    def wrap(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (amqp.AMQPConnectionException, socket.error), e:
            self.reconnect()
            raise
    return wrap

class Queue(object):
    def __init__(self, name, host="localhost", user="guest", passwd="guest", vhost="/",
                       maxsize=0):
        self.name = name
        self.host = host
        self.user = user
        self.passwd = passwd
        self.vhost = vhost
        self.maxsize = maxsize
        self.name = name

        self._last_ack = None

        self.connection = amqp.Connection(host=host,userid=user,password=passwd,virtual_host=vhost)
        self.channel = self.connection.channel()
        self.channel.queue_declare(name)
        #self.channel.queue_purge(name)

    def reconnect(self):
        self.connection = amqp.Connection(host=self.host,userid=self.user,password=self.passwd,virtual_host=self.vhost)
        self.channel = self.connection.channel()

    @catch_error
    def qsize(self):
        name, size, consumers = self.channel.queue_declare(self.name, passive=True)
        return size

    def empty(self):
        if self.qsize() == 0:
            return True
        else:
            return False

    def full(self):
        if self.maxsize and self.qsize() >= self.maxsize:
            return True
        else:
            return False

    @catch_error
    def put(self, obj, block=True, timeout=None):
        if not block:
            return self.put_nowait()

        start_time = time.time()
        while self.full():
            if timeout and time.time() - start_time >= timeout:
                raise BaseQueue.Full
            time.sleep(0.3)
        msg = amqp.Message(cPickle.dumps(obj))
        self.channel.basic_publish(msg, "", self.name)

    @catch_error
    def put_nowait(self, obj):
        if self.full():
            raise BaseQueue.Full
        msg = amqp.Message(cPickle.dumps(obj))
        self.channel.basic_publish(msg, "", self.name)

    @catch_error
    def get(self, block=True, timeout=None, ack=True):
        if not block:
            return self.get_nowait()

        start_time = time.time()
        while True:
            if timeout and time.time() - start_time >= timeout:
                raise BaseQueue.Empty
            msg = self.channel.basic_get(self.name)
            if msg is not None:
                break
            time.sleep(0.3)
        if ack:
            self.channel.basic_ack(msg.delivery_info['delivery_tag'])
        else:
            self._last_ack = msg.delivery_info['delivery_tag']
        return cPickle.loads(msg.body)

    @catch_error
    def get_nowait(self, ack=True):
        msg = self.channel.basic_get(self.name)
        if msg is None:
            raise BaseQueue.Empty
        if ack:
            self.channel.basic_ack(msg.delivery_info['delivery_tag'])
        else:
            self._last_ack = msg.delivery_info['delivery_tag']
        return cPickle.loads(msg.body)

    @catch_error
    def ack(self, id=None):
        if id is None:
            id = self._last_ack
        if id is None:
            return False
        self.channel.basic_ack(id)
        return True

########NEW FILE########
__FILENAME__ = response
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2012-11-02 11:16:02

import json
import chardet
from pyquery import PyQuery
from requests.structures import CaseInsensitiveDict
from requests.utils import get_encoding_from_headers, get_encodings_from_content
from requests import HTTPError

class Response(object):
    def __init__(self):
        self.status_code = None
        self.url = None
        self.orig_url = None
        self.headers = CaseInsensitiveDict()
        self.content = ''
        self.cookies = {}
        self.error = None
        self.save = None
        self.time = 0

    def __repr__(self):
       return '<Response [%d]>' % self.status_code

    def __bool__(self):
        """Returns true if :attr:`status_code` is 'OK'."""
        return self.ok

    def __nonzero__(self):
        """Returns true if :attr:`status_code` is 'OK'."""
        return self.ok

    @property
    def ok(self):
        try:
            self.raise_for_status()
        except RequestException:
            return False
        return True

    @property
    def encoding(self):
        if hasattr(self, '_encoding'):
            return self._encoding

        # content is unicode
        if isinstance(self.content, unicode):
            return 'unicode'

        # Try charset from content-type
        encoding = get_encoding_from_headers(self.headers)
        if encoding == 'ISO-8859-1':
            encoding = None

        # Try charset from content
        if not encoding:
            encoding = get_encodings_from_content(self.content)
            encoding = encoding and encoding[0] or None

        # Fallback to auto-detected encoding.
        if not encoding and chardet is not None:
            encoding = chardet.detect(self.content)['encoding']

        if encoding and encoding.lower() == 'gb2312':
            encoding = 'gb18030'

        self._encoding = encoding or 'utf-8'
        return self._encoding

    @encoding.setter
    def encoding(self, value):
        self._encoding = value
        self._text = None

    @property
    def text(self):
        """Content of the response, in unicode.

        if Response.encoding is None and chardet module is available, encoding
        will be guessed.
        """
        if hasattr(self, '_text') and self._text:
            return self._text
        if not self.content:
            return u''
        if isinstance(self.content, unicode):
            return self.content

        content = None
        encoding = self.encoding

        # Decode unicode from given encoding.
        try:
            content = self.content.decode(encoding, 'replace')
        except LookupError:
            # A LookupError is raised if the encoding was not found which could
            # indicate a misspelling or similar mistake.
            #
            # So we try blindly encoding.
            content = self.content.decode('utf-8', 'replace')

        self._text = content
        return content

    @property
    def json(self):
        """Returns the json-encoded content of a request, if any."""
        try:
            return json.loads(self.text or self.content)
        except ValueError:
            return None

    @property
    def doc(self):
        """Returns a PyQuery object of a request's content"""
        if hasattr(self, '_doc'):
            return self._doc
        doc = self._doc = PyQuery(self.text or self.content)
        doc.make_links_absolute(self.url)
        return doc

    def raise_for_status(self, allow_redirects=True):
        """Raises stored :class:`HTTPError` or :class:`URLError`, if one occurred."""

        if self.error:
            raise HTTPError(self.error)

        if (self.status_code >= 300) and (self.status_code < 400) and not allow_redirects:
            http_error = HTTPError('%s Redirection' % (self.status_code))
            http_error.response = self
            raise http_error

        elif (self.status_code >= 400) and (self.status_code < 500):
            http_error = HTTPError('%s Client Error' % (self.status_code))
            http_error.response = self
            raise http_error

        elif (self.status_code >= 500) and (self.status_code < 600):
            http_error = HTTPError('%s Server Error' % (self.status_code))
            http_error.response = self
            raise http_error

def rebuild_response(r):
    response = Response()
    response.status_code = r.get('status_code', 599)
    response.url = r.get('url', '')
    response.headers = CaseInsensitiveDict(r.get('headers', {}))
    response.content = r.get('content', '')
    response.cookies = r.get('cookies', {})
    response.error = r.get('error')
    response.time = r.get('time', 0)
    response.orig_url = r.get('orig_url', response.url)
    response.save = r.get('save')
    return response

########NEW FILE########
__FILENAME__ = sample_handler
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Created on __DATE__


from libs.base_handler import *

class Handler(BaseHandler):
    '''
    this is a sample handler
    '''
    def on_start(self):
        self.crawl('http://www.baidu.com/', callback=self.index_page)

    def index_page(self, response):
        for each in response.doc('a[href^="http://"]').items():
            self.crawl(each.attr.href, callback=self.index_page)
        return response.doc('title').text()

    def on_result(self, result):
        if result:
            print result

########NEW FILE########
__FILENAME__ = url
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2012-11-09 14:39:57

import mimetypes
from urllib import urlencode
from urlparse import urlparse, urlunparse

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

def _encode_params(data):
    """Encode parameters in a piece of data.

    Will successfully encode parameters when passed as a dict or a list of
    2-tuples. Order is retained if data is a list of 2-tuples but abritrary
    if parameters are supplied as a dict.
    """

    if isinstance(data, basestring):
        return data
    elif hasattr(data, 'read'):
        return data
    elif hasattr(data, '__iter__'):
        result = []
        for k, vs in data.iteritems():
            for v in isinstance(vs, list) and vs or [vs]:
                if v is not None:
                    result.append(
                        (k.encode('utf-8') if isinstance(k, unicode) else k,
                         v.encode('utf-8') if isinstance(v, unicode) else v))
        return urlencode(result, doseq=True)
    else:
        return data

def _utf8(key):
    if not isinstance(key, basestring):
        key = str(key)
    return key.encode('utf-8') if isinstance(key, unicode) else key
    
def _encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for key, value in fields.iteritems():
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % _utf8(key))
        L.append('')
        L.append(_utf8(value))
    for key, (filename, value) in files.iteritems():
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (_utf8(key), _utf8(filename)))
        L.append('Content-Type: %s' % get_content_type(filename))
        L.append('')
        L.append(value.read() if hasattr(value, "read") else _utf8(value))
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

def _build_url(url, _params):
    """Build the actual URL to use."""

    # Support for unicode domain names and paths.
    scheme, netloc, path, params, query, fragment = urlparse(url)
    netloc = netloc.encode('idna').decode('utf-8')
    if not path:
        path = '/'

    if isinstance(scheme, unicode):
        scheme = scheme.encode('utf-8')
    if isinstance(netloc, unicode):
        netloc = netloc.encode('utf-8')
    if isinstance(path, unicode):
        path = path.encode('utf-8')
    if isinstance(params, unicode):
        params = params.encode('utf-8')
    if isinstance(query, unicode):
        query = query.encode('utf-8')
    if isinstance(fragment, unicode):
        fragment = fragment.encode('utf-8')

    enc_params = _encode_params(_params)
    if enc_params:
        if query:
            query = '%s&%s' % (query, enc_params)
        else:
            query = enc_params
    url = (urlunparse([scheme, netloc, path, params, query, fragment]))
    return url

def quote_chinese(url, encodeing="utf-8"):
    if isinstance(url, unicode):
        return quote_chinese(url.encode("utf-8"))
    res = [b if ord(b) < 128 else '%%%02X' % (ord(b)) for b in url]
    return "".join(res)

def xunlei_url_decode(url):
    url = url.split('&')[0]
    url = url[10:].decode('base64')
    assert url.startswith('AA') and url.endswith('ZZ'), 'xunlei url format error'
    return url[2:-2]

def flashget_url_decode(url):
    url = url.split('&')[0]
    url = url[11:].decode('base64')
    assert url.startswith('[FLASHGET]') and url.endswith('[FLASHGET]'), 'flashget url format error'
    return url[10:-10]

def flashgetx_url_decode(url):
    url = url.split('&')[0]
    name, size, hash, end = url.split('|')[2:]
    assert end == '/', 'flashgetx url format error'
    return 'ed2k://|file|'+name.decode('base64')+'|'+size+'|'+hash+'/'

def qqdl_url_decode(url):
    url = url.split('&')[0]
    return base64.decodestring(url[7:])

def url_unmask(url):
    url_lower = url.lower()
    if url_lower.startswith('thunder://'):
        url = xunlei_url_decode(url)
    elif url_lower.startswith('flashget://'):
        url = flashget_url_decode(url)
    elif url_lower.startswith('flashgetx://'):
        url = flashgetx_url_decode(url)
    elif url_lower.startswith('qqdl://'):
        url = qqdl_url_decode(url)

    return quote_chinese(url)

if __name__ == "__main__":
    assert _build_url("http://httpbin.org", {'id': 123}) == "http://httpbin.org/?id=123"
    assert _build_url("http://httpbin.org/get", {'id': 123}) == "http://httpbin.org/get?id=123"
    assert _encode_params({'id': 123, 'foo': 'fdsa'}) == "foo=fdsa&id=123"
    assert _encode_params({'id': "中文"}) == "id=%E4%B8%AD%E6%96%87"
    print _encode_multipart_formdata({'id': 123}, {'key': ('file.name', 'content')})

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2012-11-06 11:50:13

import logging
import hashlib

md5string = lambda x: hashlib.md5(x).hexdigest()

class ReadOnlyDict(dict):
    def __setitem__(self, key, value):
        raise "dict is read-only"

def getitem(obj, key=0, default=None):
    try:
        return obj[key]
    except:
        return default

def hide_me(tb, g=globals()):
    base_tb = tb
    try:
        while tb and tb.tb_frame.f_globals is not g:
            tb = tb.tb_next
        while tb and tb.tb_frame.f_globals is g:
            tb = tb.tb_next
    except Exception, e:
        logging.exception(e)
        tb = base_tb
    if not tb:
        tb = base_tb
    return tb

def run_in_thread(func, *args, **kwargs):
    from threading import Thread
    thread = Thread(target=func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread

def run_in_subprocess(func, *args, **kwargs):
    from multiprocessing import Process
    thread = Process(target=func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread

########NEW FILE########
__FILENAME__ = processor
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-16 22:59:56

import sys
import time
import Queue
import logging
from libs.response import rebuild_response
from project_module import ProjectLoader, ProjectFinder
logger = logging.getLogger("processor")

def build_module(project, env={}):
    assert 'name' in project, 'need name of project'
    assert 'script' in project, 'need script of project'

    env = dict(env)
    env.update({
        'debug': project.get('status', 'DEBUG') == 'DEBUG',
        })

    loader = ProjectLoader(project)
    module = loader.load_module(project['name'])
    _class = module.__dict__.get('__handler_cls__')
    assert _class is not None, "need BaseHandler in project module"
    instance = _class()
    instance.__env__ = env
    instance._project_name = project['name']

    return {
        'loader': loader,
        'module': module,
        'class': _class,
        'instance': instance,
        'info': project
        }

class Processor(object):
    CHECK_PROJECTS_INTERVAL = 5*60

    def __init__(self, projectdb, inqueue, status_queue, newtask_queue):
        self.inqueue = inqueue
        self.status_queue = status_queue
        self.newtask_queue = newtask_queue
        self.projectdb = projectdb

        self._quit = False
        self.projects = {}
        self.last_check_projects = 0

        self.enable_projects_import()

    def enable_projects_import(self):
        _self = self
        class ProcessProjectFinder(ProjectFinder):
            def get_loader(self, name):
                info = _self.projectdb.get(name)
                if info:
                    return ProjectLoader(info)
        sys.meta_path.append(ProcessProjectFinder())

    def __del__(self):
        reload(__builtin__)

    def _init_projects(self):
        for project in self.projectdb.get_all():
            try:
                self._update_project(project)
            except Exception, e:
                logger.exception("exception when init projects for %s" % project.get('name', None))
                continue
        self.last_check_projects = time.time()

    def _need_update(self, task):
        if task['project'] not in self.projects:
            return True
        if task.get('project_updatetime', 0) > self.projects[task['project']]['info'].get('updatetime', 0):
            return True
        if time.time() - self.last_check_projects < self.CHECK_PROJECTS_INTERVAL:
            return True
        return False

    def _check_projects(self, task):
        if not self._need_update(task):
            return
        for project in self.projectdb.check_update(self.last_check_projects):
            try:
                logger.debug("project: %s updated." % project['name'])
                self._update_project(project)
            except Exception, e:
                logger.exception("exception when check update for %s" % project.get('name', None))
                continue
        self.last_check_projects = time.time()

    def _update_project(self, project):
        self.projects[project['name']] = build_module(project)

    def on_task(self, task, response):
        start_time = time.time()
        try:
            response = rebuild_response(response)
            assert 'taskid' in task, 'need taskid in task'
            project = task['project']
            if project not in self.projects:
                raise LookupError("not such project: %s" % project)
            project_data = self.projects[project]
            ret = project_data['instance'].run(project_data['module'], task, response)
        except Exception, e:
            logger.exception(e)
            return False
        process_time = time.time() - start_time

        if not ret.extinfo.get('not_send_status', False):
            status_pack = {
                    'taskid': task['taskid'],
                    'project': task['project'],
                    'url': task.get('url'),
                    'track': {
                        'fetch': {
                            'ok': not response.error,
                            'time': response.time,
                            'status_code': response.status_code,
                            'headers': dict(response.headers),
                            'encoding': response.encoding,
                            #'content': response.content,
                            },
                        'process': {
                            'ok': not ret.exception,
                            'time': process_time,
                            'follows': len(ret.follows),
                            'result': unicode(ret.result)[:100],
                            'logs': ret.logstr()[:200],
                            'exception': unicode(ret.exception),
                            }
                        }
                    }
            self.status_queue.put(status_pack)

        for task in ret.follows:
            self.newtask_queue.put(task)

        for project, msg in ret.messages:
            self.inqueue.put(({
                    'taskid': 'data:,on_message',
                    'project': project,
                    'url': 'data:,on_message',
                    'process': {
                        'callback': '_on_message',
                        }
                }, {
                    'status_code': 200,
                    'url': 'data:,on_message',
                    'save': (task['project'], msg),
                }))

        if response.error or ret.exception:
            logger_func = logger.error
        else:
            logger_func = logger.info
        logger_func('process %s:%s %s -> [%d] len:%d -> fol:%d msg:%d err:%r' % (task['project'], task['taskid'],
            task.get('url'), response.status_code, len(response.content),
            len(ret.follows), len(ret.messages), ret.exception))
        return True

    def run(self):
        while not self._quit:
            try:
                task, response = self.inqueue.get()
                self._check_projects(task)
                self.on_task(task, response)
            except Queue.Empty, e:
                time.sleep(1)
                continue
            except KeyboardInterrupt:
                break
            except Exception, e:
                logger.exception(e)
                continue

########NEW FILE########
__FILENAME__ = project_module
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-16 22:24:20

import os
import sys
import imp
import logging
import inspect
import linecache
from libs import base_handler
from libs.log import SaveLogHandler
from libs.utils import hide_me

class ProjectFinder(object):
    def find_module(self, fullname, path=None):
        if fullname == 'projects':
            return ProjectsLoader()
        parts = fullname.split('.')
        if len(parts) == 2 and parts[0] == 'projects':
            return self.get_loader(parts[1])

class ProjectsLoader(object):
    def load_module(self, fullname):
        mod = sys.modules.setdefault('projects', imp.new_module(fullname))
        mod.__file__ = '<projects>'
        mod.__loader__ = self
        mod.__path__ = []
        mod.__package__ = 'projects'
        return mod

class ProjectLoader(object):
    def __init__(self, project, mod=None):
        self.project = project
        self.name = project['name']
        self.mod = mod

    def load_module(self, fullname):
        if self.mod is None:
            mod = self.mod = imp.new_module(self.name)
        else:
            mod = self.mod

        log_buffer = []
        mod.logging = mod.logger = logging.Logger(self.name)
        mod.logger.addHandler(SaveLogHandler(log_buffer))
        mod.log_buffer = log_buffer
        mod.__file__ = '<%s>' % self.name
        mod.__loader__ = self
        mod.__project__ = self.project
        mod.__package__ = ''

        code = self.get_code(fullname)
        exec code in mod.__dict__
        linecache.clearcache()

        if '__handler_cls__' not in mod.__dict__:
            for each in mod.__dict__.values():
                if inspect.isclass(each) and each is not base_handler.BaseHandler \
                        and issubclass(each, base_handler.BaseHandler):
                    mod.__dict__['__handler_cls__'] = each

        return mod

    def is_package(self, fullname):
        return False

    def get_code(self, fullname):
        return compile(self.get_source(fullname), '<%s>' % self.name, 'exec')

    def get_source(self, fullname):
        script = self.project['script']
        if isinstance(script, unicode):
            return script.encode('utf8')
        return script

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-03-05 00:11:49

import sys
import time
import logging
import logging.config
from multiprocessing import Queue
from database.sqlite import taskdb, projectdb
from libs.utils import run_in_thread, run_in_subprocess

logging.config.fileConfig("logging.conf")

def get_taskdb():
    return taskdb.TaskDB('./data/task.db')

def get_projectdb():
    return projectdb.ProjectDB('./data/project.db')

queue_maxsize = 100
newtask_queue = Queue(queue_maxsize)
status_queue = Queue(queue_maxsize)
scheduler2fetcher = Queue(queue_maxsize)
fetcher2processor = Queue(queue_maxsize)

scheduler_xmlrpc_port = 23333
fetcher_xmlrpc_port = 24444
debug = True

def run_scheduler():
    from scheduler import Scheduler
    scheduler = Scheduler(taskdb=get_taskdb(), projectdb=get_projectdb(),
            newtask_queue=newtask_queue, status_queue=status_queue, out_queue=scheduler2fetcher)

    run_in_thread(scheduler.xmlrpc_run, port=scheduler_xmlrpc_port)
    scheduler.run()

def run_fetcher():
    from fetcher.tornado_fetcher import Fetcher
    fetcher = Fetcher(inqueue=scheduler2fetcher, outqueue=fetcher2processor)

    run_in_thread(fetcher.xmlrpc_run, port=fetcher_xmlrpc_port)
    fetcher.run()

def run_processor():
    from processor import Processor
    processor = Processor(projectdb=get_projectdb(),
            inqueue=fetcher2processor, status_queue=status_queue, newtask_queue=newtask_queue)
    
    processor.run()

def run_webui():
    import xmlrpclib
    import cPickle as pickle
    scheduler_rpc = xmlrpclib.ServerProxy('http://localhost:%d' % scheduler_xmlrpc_port)
    fetch_rpc = xmlrpclib.ServerProxy('http://localhost:%d' % fetcher_xmlrpc_port)

    from webui.app import app
    app.config['fetch'] = lambda task: pickle.loads(fetch_rpc.fetch(task).data)
    app.config['projectdb'] = get_projectdb
    app.config['scheduler_rpc'] = scheduler_rpc
    #app.config['cdn'] = '//cdnjs.cloudflare.com/ajax/libs/'
    app.run()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        threads = []
        threads.append(run_in_subprocess(run_fetcher))
        threads.append(run_in_subprocess(run_processor))
        threads.append(run_in_subprocess(run_scheduler))
        threads.append(run_in_subprocess(run_webui))

        while True:
            try:
                time.sleep(10)
            except KeyboardInterrupt:
                break

        for each in threads:
            each.join()
    else:
        cmd = "run_"+sys.argv[1]
        locals()[cmd]()

########NEW FILE########
__FILENAME__ = scheduler
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-07 17:05:11


import os
import time
import Queue
import logging
from task_queue import TaskQueue
from libs import counter
logger = logging.getLogger('scheduler')


class Scheduler(object):
    UPDATE_PROJECT_INTERVAL = 5*60
    default_schedule = {
            'priority': 0,
            'retries': 3,
            'exetime': 0,
            'age': 30*24*60*60,
            'itag': None,
            }
    LOOP_LIMIT = 1000
    LOOP_INTERVAL = 0.1
    
    def __init__(self, taskdb, projectdb, newtask_queue, status_queue, out_queue, data_path = './data'):
        self.taskdb = taskdb
        self.projectdb = projectdb
        self.newtask_queue = newtask_queue
        self.status_queue = status_queue
        self.out_queue = out_queue
        self.data_path = data_path

        self._quit = False
        self.projects = dict()
        self._last_update_project = 0
        self.task_queue = dict()
        self._last_tick = int(time.time() / 60)

        self._cnt = {
                "5m": counter.CounterManager(
                    lambda : counter.TimebaseAverageWindowCounter(30, 10)),
                "1h": counter.CounterManager(
                    lambda : counter.TimebaseAverageWindowCounter(60, 60)),
                "1d": counter.CounterManager(
                    lambda : counter.TimebaseAverageWindowCounter(10*60, 24*6)),
                "all": counter.CounterManager(
                    lambda : counter.TotalCounter()),
                }
        self._cnt['1h'].load(os.path.join(self.data_path, 'scheduler.1h'))
        self._cnt['1d'].load(os.path.join(self.data_path, 'scheduler.1d'))
        self._cnt['all'].load(os.path.join(self.data_path, 'scheduler.all'))
        self._last_dump_cnt = 0

    def _load_projects(self):
        self.projects = dict()
        for project in self.projectdb.get_all():
            self.projects[project['name']] = project
        self._last_update_project = time.time()

    def _update_projects(self):
        now = time.time()
        if self._last_update_project + self.UPDATE_PROJECT_INTERVAL > now:
            return
        for project in self.projectdb.check_update(self._last_update_project):
            logger.debug("project: %s updated." % project['name'])
            self.projects[project['name']] = project
            if project['name'] not in self.task_queue:
                self._load_tasks(project['name'])
            if project['status'] in ('RUNNING', 'DEBUG'):
                self.task_queue[project['name']].rate = project['rate']
                self.task_queue[project['name']].burst = project['burst']
            else:
                self.task_queue[project['name']].rate = 0
                self.task_queue[project['name']].burst = 0
        self._last_update_project = now

    scheduler_task_fields = ['taskid', 'project', 'schedule', ]
    def _load_tasks(self, project):
        self.task_queue[project] = TaskQueue(rate=0, burst=0)
        for task in self.taskdb.load_tasks(self.taskdb.ACTIVE, project, self.scheduler_task_fields):
            taskid = task['taskid']
            _schedule = task.get('schedule', self.default_schedule)
            priority = _schedule.get('priority', self.default_schedule['priority'])
            exetime = _schedule.get('exetime', self.default_schedule['exetime'])
            self.task_queue[project].put(taskid, priority, exetime)
        if self.projects[project]['status'] in ('RUNNING', 'DEBUG'):
            self.task_queue[project].rate = self.projects[project]['rate']
            self.task_queue[project].burst = self.projects[project]['burst']
        else:
            self.task_queue[project].rate = 0
            self.task_queue[project].burst = 0
        self._cnt['all'].value((project, 'pending'), len(self.task_queue[project]))

    def task_verify(self, task):
        for each in ('taskid', 'project', 'url', ):
            if each not in task or not task[each]:
                logger.error('%s not in task: %s' % (each, unicode(task)[:200]))
                return False
        if task['project'] not in self.task_queue:
            logger.error('unknow project: %s' % task['project'])
            return False
        return True

    def insert_task(self, task):
        return self.taskdb.insert(task['project'], task['taskid'], task)

    def update_task(self, task):
        return self.taskdb.update(task['project'], task['taskid'], task)

    def put_task(self, task):
        _schedule = task.get('schedule', self.default_schedule)
        self.task_queue[task['project']].put(task['taskid'],
                priority=_schedule.get('priority', self.default_schedule['priority']),
                exetime=_schedule.get('exetime', self.default_schedule['exetime']))

    def send_task(self, task):
        self.out_queue.put(task)

    def _check_task_done(self):
        cnt = 0
        try:
            while cnt < self.LOOP_LIMIT:
                task = self.status_queue.get_nowait()
                if not self.task_verify(task):
                    continue
                self.task_queue[task['project']].done(task['taskid'])
                task = self.on_task_status(task)
                cnt += 1
        except Queue.Empty:
            pass
        return cnt

    merge_task_fields = ['taskid', 'project', 'url', 'status', 'schedule', 'lastcrawltime']
    def _check_request(self):
        cnt = 0
        try:
            while cnt < self.LOOP_LIMIT:
                task = self.newtask_queue.get_nowait()
                if not self.task_verify(task):
                    continue
                if task['taskid'] in self.task_queue[task['project']]:
                    if not task.get('schedule', {}).get('force_update', False):
                        logger.debug('ignore newtask %(project)s:%(taskid)s %(url)s' % task)
                        continue
                oldtask = self.taskdb.get_task(task['project'], task['taskid'],
                        fields=self.merge_task_fields)
                if oldtask:
                    task = self.on_old_request(task, oldtask)
                else:
                    task = self.on_new_request(task)
                cnt += 1
        except Queue.Empty:
            pass
        return cnt

    def _check_cronjob(self):
        now = time.time()
        if now - self._last_tick * 60 < 60:
            return
        self._last_tick += 1
        for project in self.projects.itervalues():
            if project['status'] not in ('DEBUG', 'RUNNING'):
                continue
            self.send_task({
                'taskid': 'on_cronjob',
                'project': project['name'],
                'url': 'data:,on_cronjob',
                'status': self.taskdb.ACTIVE,
                'fetch': {
                    'save': {
                        'tick': self._last_tick,
                        },
                    },
                'process': {
                    'callback': 'on_cronjob',
                    },
                'project_updatetime': self.projects[project['name']].get('updatetime', 0),
                })

    request_task_fields = ['taskid', 'project', 'url', 'status', 'fetch', 'process', 'track', 'lastcrawltime']
    def _check_select(self):
        cnt_dict = dict()
        for project, task_queue in self.task_queue.iteritems():
            # task queue
            self.task_queue[project].check_update()
            cnt = 0
            taskid = task_queue.get()
            while taskid and cnt < self.LOOP_LIMIT / 10:
                task = self.taskdb.get_task(project, taskid, fields=self.request_task_fields)
                # inform processor project may updated
                task['project_updatetime'] = self.projects[project].get('updatetime', 0)
                task = self.on_select_task(task)
                taskid = task_queue.get()
                cnt += 1
            cnt_dict[project] = cnt
        return cnt_dict

    def _dump_cnt(self):
        self._cnt['1h'].dump(os.path.join(self.data_path, 'scheduler.1h'))
        self._cnt['1d'].dump(os.path.join(self.data_path, 'scheduler.1d'))
        self._cnt['all'].dump(os.path.join(self.data_path, 'scheduler.all'))

    def _try_dump_cnt(self):
        now = time.time()
        if now - self._last_dump_cnt > 60:
            self._last_dump_cnt = now
            self._dump_cnt()

    def __len__(self):
        return sum((len(x) for x in self.task_queue.itervalues()))

    def quit(self):
        self._quit = True

    def run(self):
        logger.info("loading projects")
        self._load_projects()
        for i, project in enumerate(self.projects.keys()):
            self._load_tasks(project)
            logger.info("loading tasks from %s loaded %d tasks -- %d/%d" % (project, len(self.task_queue[project]),
                i+1, len(self.projects)))

        while not self._quit:
            try:
                self._update_projects()
                self._check_task_done()
                self._check_request()
                self._check_cronjob()
                self._check_select()
                time.sleep(self.LOOP_INTERVAL)
            except KeyboardInterrupt:
                break

        logger.info("scheduler exiting...")
        self._dump_cnt()

    def xmlrpc_run(self, port=23333, bind='127.0.0.1', logRequests=False):
        from SimpleXMLRPCServer import SimpleXMLRPCServer

        server = SimpleXMLRPCServer((bind, port), allow_none=True, logRequests=logRequests)
        server.register_introspection_functions()
        server.register_multicall_functions()

        server.register_function(self.quit, '_quit')
        server.register_function(self.__len__, 'size')
        def dump_counter(_time, _type):
            return self._cnt[_time].to_dict(_type)
        server.register_function(dump_counter, 'counter')
        def new_task(task):
            if self.task_verify(task):
                self.newtask_queue.put(task)
                return True
            return False
        server.register_function(new_task, 'newtask')
        def update_project():
            self._last_update_project = 0
        server.register_function(update_project, 'update_project')

        server.serve_forever()
    
    def on_new_request(self, task):
        task['status'] = self.taskdb.ACTIVE
        self.insert_task(task)
        self.put_task(task)

        project = task['project']
        self._cnt['5m'].event((project, 'pending'), +1)
        self._cnt['1h'].event((project, 'pending'), +1)
        self._cnt['1d'].event((project, 'pending'), +1)
        self._cnt['all'].event((project, 'task'), +1).event((project, 'pending'), +1)
        logger.debug('new task %(project)s:%(taskid)s %(url)s' % task)
        return task

    def on_old_request(self, task, old_task):
        now = time.time()

        _schedule = task.get('schedule', self.default_schedule)
        old_schedule = old_task.get('schedule', {})

        restart = False
        if _schedule.get('itag') and _schedule['itag'] != old_schedule.get('itag'):
            restart = True
        elif _schedule.get('age', self.default_schedule['age']) + (old_task['lastcrawltime'] or 0) < now:
            restart = True
        elif _schedule.get('force_update'):
            restart = True

        if not restart:
            logger.debug('ignore newtask %(project)s:%(taskid)s %(url)s' % task)
            return

        task['status'] = self.taskdb.ACTIVE
        self.update_task(task)
        self.put_task(task)

        project = task['project']
        self._cnt['5m'].event((project, 'pending'), +1)
        self._cnt['1h'].event((project, 'pending'), +1)
        self._cnt['1d'].event((project, 'pending'), +1)
        if old_task['status'] == self.taskdb.SUCCESS:
            self._cnt['all'].event((project, 'success'), -1).event((project, 'pending'), +1)
        elif old_task['status'] == self.taskdb.FAILED:
            self._cnt['all'].event((project, 'failed'), -1).event((project, 'pending'), +1)
        logger.debug('restart task %(project)s:%(taskid)s %(url)s' % task)
        return task

    def on_task_status(self, task):
        try:
            fetchok = task['track']['fetch']['ok']
            procesok = task['track']['process']['ok']
            if task['taskid'] not in self.task_queue[task['project']].processing:
                logging.error('not processing pack: %(project)s:%(taskid)s %(url)s' % task)
                return None
        except KeyError, e:
            logger.error("Bad status pack: %s" % e)
            return None

        if fetchok and procesok:
            return self.on_task_done(task)
        else:
            return self.on_task_failed(task)

    def on_task_done(self, task):
        '''
        called by task_status
        '''
        task['status'] = self.taskdb.SUCCESS
        task['lastcrawltime'] = time.time()
        self.update_task(task)

        project = task['project']
        self._cnt['5m'].event((project, 'success'), +1)
        self._cnt['1h'].event((project, 'success'), +1)
        self._cnt['1d'].event((project, 'success'), +1)
        self._cnt['all'].event((project, 'success'), +1).event((project, 'pending'), -1)
        logger.debug('task done %(project)s:%(taskid)s %(url)s' % task)
        return task

    def on_task_failed(self, task):
        '''
        called by task_status
        '''
        old_task = self.taskdb.get_task(task['project'], task['taskid'], fields=['schedule'])
        if old_task is None:
            logging.error('unknow status pack: %s' % task)
            return
        if not task.get('schedule'):
            task['schedule'] = old_task.get('schedule', {})

        retries = task['schedule'].get('retries', self.default_schedule['retries'])
        retried = task['schedule'].get('retried', 0)
        if retried == 0:
            next_exetime = 0
        elif retried == 1:
            next_exetime = 1 * 60 * 60
        else:
            next_exetime = 6 * (2**retried) * 60 * 60

        if retried >= retries:
            task['status'] = self.taskdb.FAILED
            task['lastcrawltime'] = time.time()
            self.update_task(task)

            project = task['project']
            self._cnt['5m'].event((project, 'failed'), +1)
            self._cnt['1h'].event((project, 'failed'), +1)
            self._cnt['1d'].event((project, 'failed'), +1)
            self._cnt['all'].event((project, 'failed'), +1).event((project, 'pending'), -1)
            logger.info('task failed %(project)s:%(taskid)s %(url)s' % task)
            return task
        else:
            task['schedule']['retried'] = retried + 1
            task['schedule']['exetime'] = time.time() + next_exetime
            task['lastcrawltime'] = time.time()
            self.update_task(task)
            self.put_task(task)

            project = task['project']
            self._cnt['5m'].event((project, 'retry'), +1)
            self._cnt['1h'].event((project, 'retry'), +1)
            self._cnt['1d'].event((project, 'retry'), +1)
            logger.info('task retry %(project)s:%(taskid)s %(url)s' % task)
            return task
        
    def on_select_task(self, task):
        logger.debug('select %(project)s:%(taskid)s %(url)s' % task)
        self.send_task(task)
        return task

########NEW FILE########
__FILENAME__ = task_queue
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-07 13:12:10

import time
import heapq
import Queue
import logging
import threading
from UserDict import DictMixin
from token_bucket import Bucket


class InQueueTask(DictMixin):
    __slots__ = ('taskid', 'priority', 'exetime')
    __getitem__ = lambda *x: getattr(*x)
    __setitem__ = lambda *x: setattr(*x)
    keys = lambda self: self.__slots__

    def __init__(self, taskid, priority=0, exetime=0):
        self.taskid = taskid
        self.priority = priority
        self.exetime = exetime

    def __cmp__(self, other):
        if self.exetime == 0 and other.exetime == 0:
            return -cmp(self.priority, other.priority)
        else:
            return cmp(self.exetime, other.exetime)


class PriorityTaskQueue(Queue.Queue):
    '''
    TaskQueue
    '''

    def _init(self, maxsize):
        self.queue = []
        self.queue_dict = dict()

    def _qsize(self, len=len):
        return len(self.queue)

    def _put(self, item, heappush=heapq.heappush):
        heappush(self.queue, item)
        self.queue_dict[item.taskid] = item

    def _get(self, heappop=heapq.heappop):
        item = heappop(self.queue)
        self.queue_dict.pop(item.taskid, None)
        return item

    @property
    def top(self):
        return self.queue[0]

    def resort(self):
        self.mutex.acquire()
        heapq.heapify(self.queue)
        self.mutex.release()

    def __contains__(self, taskid):
        return taskid in self.queue_dict

    def __getitem__(self, taskid):
        return self.queue_dict[taskid]

    def __setitem__(self, taskid, item):
        assert item.taskid == taskid
        self.put(item)


class TaskQueue(object):
    '''
    task queue for scheduler, have a priority queue and a time queue for delayed tasks
    '''
    processing_timeout = 10*60
    def __init__(self, rate=0, burst=0):
        self.mutex = threading.Lock()
        self.priority_queue = PriorityTaskQueue()
        self.time_queue = PriorityTaskQueue()
        self.processing = PriorityTaskQueue()
        self.bucket = Bucket(rate=rate, burst=burst)

    @property
    def rate(self):
        return self.bucket.rate
    @rate.setter
    def rate(self, value):
        self.bucket.rate = value

    @property
    def burst(self):
        return self.burst.burst
    @burst.setter
    def burst(self, value):
        self.bucket.burst = value

    def check_update(self):
        self._check_time_queue()
        self._check_processing()

    def _check_time_queue(self):
        now = time.time()
        self.mutex.acquire()
        while self.time_queue.qsize() and self.time_queue.top.exetime < now:
            task = self.time_queue.get()
            task.exetime = 0
            self.priority_queue.put(task)
        self.mutex.release()

    def _check_processing(self):
        now = time.time()
        self.mutex.acquire()
        while self.processing.qsize() and self.processing.top.exetime < now:
            task = self.processing.get()
            if task.taskid is None:
                continue
            task.exetime = 0
            self.priority_queue.put(task)
            logging.info("[processing: retry] %s" % task.taskid)
        self.mutex.release()

    def put(self, taskid, priority=0, exetime=0):
        now = time.time()
        self.mutex.acquire()
        if taskid in self.priority_queue:
            task = self.priority_queue[taskid]
            if priority > task.priority:
                task.priority = priority
        elif taskid in self.time_queue:
            task = self.time_queue[taskid]
            if priority > task.priority:
                task.priority = priority
            if exetime < task.exetime:
                task.exetime = exetime
        else:
            task = InQueueTask(taskid, priority)
            if exetime and exetime > now:
                task.exetime = exetime
                self.time_queue.put(task)
            else:
                self.priority_queue.put(task)
        self.mutex.release()

    def get(self):
        if self.bucket.get() < 1:
            return None
        now = time.time()
        self.mutex.acquire()
        try:
            task = self.priority_queue.get_nowait()
            self.bucket.desc()
        except Queue.Empty:
            self.mutex.release()
            return None
        task.exetime = now + self.processing_timeout
        self.processing.put(task)
        self.mutex.release()
        return task.taskid

    def done(self, taskid):
        if taskid in self.processing:
            self.processing[taskid].taskid = None

    def __len__(self):
        return self.priority_queue.qsize() + self.time_queue.qsize()

    def __contains__(self, taskid):
        if taskid in self.priority_queue or taskid in self.time_queue:
            return True
        if taskid in self.processing and self.processing[taskid].taskid:
            return True
        return False


if __name__ == '__main__':
    task_queue = TaskQueue()
    task_queue.processing_timeout = 0.1
    task_queue.put('a3', 3, time.time()+0.1)
    task_queue.put('a1', 1)
    task_queue.put('a2', 2)
    assert task_queue.get() == 'a2'
    time.sleep(0.1)
    task_queue._check_time_queue()
    assert task_queue.get() == 'a3'
    assert task_queue.get() == 'a1'
    task_queue._check_processing()
    assert task_queue.get() == 'a2'
    assert len(task_queue) == 0

########NEW FILE########
__FILENAME__ = token_bucket
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-07 16:53:08

import time
try:
    import threading as _threading
except ImportError:
    import dummy_threading as _threading

class Bucket(object):
    '''
    traffic flow control with token bucket
    '''

    update_interval = 30
    def __init__(self, rate=1, burst=None):
        self.rate = float(rate)
        if burst is None:
            self.burst = float(rate)*10
        else:
            self.burst = float(burst)
        self.mutex = _threading.Lock()
        self.bucket = self.burst
        self.last_update = time.time()

    def get(self):
        now = time.time()
        if self.bucket >= self.burst:
            self.last_update = now
            return self.bucket
        bucket = self.rate * (now - self.last_update)
        self.mutex.acquire()
        if bucket > 1:
            self.bucket += bucket
            if self.bucket > self.burst:
                self.bucket = self.burst
            self.last_update = now
        self.mutex.release()
        return self.bucket

    def set(self, value):
        self.bucket = value

    def desc(self, value=1):
        self.bucket -= value

########NEW FILE########
__FILENAME__ = data_handler
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-22 14:02:21

from libs.base_handler import BaseHandler, catch_status_code_error

class TestHandler(BaseHandler):
    def hello(self):
        return "hello world!"

    def echo(self, response):
        return response.content

    def saved(self, response):
        return response.save

    def echo_task(self, response, task):
        return task['project']

    @catch_status_code_error
    def catch_status_code(self, response):
        return response.status_code

    def raise_exception(self):
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        raise Exception('exception')

    def add_task(self, response):
        self.crawl('http://www.google.com', callback='echo', params={'wd': u'中文'})
        self.send_message('some_project', {'some': 'message'})

########NEW FILE########
__FILENAME__ = test_database_sqlite
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-08 22:37:13


import time
import unittest
from database.sqlite.taskdb import TaskDB


class TestTaskDB(unittest.TestCase):
    sample_task = {
            'taskid': 'taskid',
            'project': 'project',
            'url': 'www.baidu.com/',
            'status': TaskDB.FAILED,
            'schedule': {
                'priority': 1,
                'retries': 3,
                'exetime': 0,
                'age': 3600,
                'itag': 'itag',
                'recrawl': 5,
                },
            'fetch': {
                'method': 'GET',
                'headers': {
                    'Cookie': 'a=b', 
                    },
                'data': 'a=b&c=d', 
                'timeout': 60,
                },
            'process': {
                'callback': 'callback',
                'save': [1, 2, 3],
                },
            'track': {
                'fetch': {
                    'ok': True,
                    'time': 300,
                    'status_code': 200,
                    'headers': {
                        'Content-Type': 'plain/html', 
                        },
                    'encoding': 'utf8',
                    #'content': 'asdfasdfasdfasdf',
                    },
                'process': {
                    'ok': False,
                    'time': 10,
                    'follows': 3,
                    'outputs': 5,
                    'exception': "?",
                    },
                },
            'lastcrawltime': time.time(),
            'updatetime': time.time(),
            }

    def test_create_project(self):
        taskdb = TaskDB(':memory:')
        with self.assertRaises(AssertionError):
            taskdb._create_project('abc.abc')
        taskdb._create_project('abc')
        taskdb._list_project()
        self.assertSetEqual(taskdb.projects, set(('abc', )))

    def test_other(self):
        taskdb = TaskDB(':memory:')

        # insert
        taskdb.insert('project', 'taskid', self.sample_task)
        taskdb.insert('project', 'taskid2', self.sample_task)

        # status_count
        status = taskdb.status_count('abc')
        self.assertEqual(status, {})
        status = taskdb.status_count('project')
        self.assertEqual(status, {taskdb.FAILED: 2})

        # update & status_count
        taskdb.update('project', 'taskid', status=taskdb.ACTIVE)
        status = taskdb.status_count('project')
        self.assertEqual(status, {taskdb.ACTIVE: 1, taskdb.FAILED: 1})

        # load tasks
        taskdb.update('project', 'taskid', track={})
        tasks = list(taskdb.load_tasks(taskdb.ACTIVE))
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task['taskid'], 'taskid')
        self.assertEqual(task['schedule'], self.sample_task['schedule'])
        self.assertEqual(task['fetch'], self.sample_task['fetch'])
        self.assertEqual(task['process'], self.sample_task['process'])
        self.assertEqual(task['track'], {})

        tasks = list(taskdb.load_tasks(taskdb.ACTIVE, project='project',
                fields=['taskid']))
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['taskid'], 'taskid')
        self.assertNotIn('project', tasks[0])

        # get_task
        task = taskdb.get_task('project', 'taskid1', fields=['status'])
        self.assertIsNone(task)

        task = taskdb.get_task('project', 'taskid2')
        self.assertEqual(task['taskid'], 'taskid2')
        self.assertEqual(task['status'], taskdb.FAILED)
        self.assertEqual(task['schedule'], self.sample_task['schedule'])
        self.assertEqual(task['fetch'], self.sample_task['fetch'])
        self.assertEqual(task['process'], self.sample_task['process'])
        self.assertEqual(task['track'], self.sample_task['track'])

        task = taskdb.get_task('project', 'taskid', fields=['status'])
        self.assertEqual(task['status'], taskdb.ACTIVE)
        self.assertNotIn('taskid', task)


from database.sqlite.projectdb import ProjectDB
class TestProjectDB(unittest.TestCase):
    sample_project = {
            'name': 'name',
            'group': 'group',
            'status': 'TODO',
            'script': 'import time\nprint time.time()',
            'comments': 'test project',
            'rate': 1.0,
            'burst': 10,
            'updatetime': time.time(),
            }

    def test_all(self):
        projectdb = ProjectDB(':memory:')

        # insert
        projectdb.insert('abc', self.sample_project)
        projectdb.insert('name', self.sample_project)

        # get all
        projects = list(projectdb.get_all())
        self.assertEqual(len(projects), 2)
        project = projects[0]
        self.assertEqual(project['script'], self.sample_project['script'])
        self.assertEqual(project['rate'], self.sample_project['rate'])
        self.assertEqual(project['burst'], self.sample_project['burst'])

        projects = list(projectdb.get_all(fields=['name', 'script']))
        self.assertEqual(len(projects), 2)
        project = projects[1]
        self.assertIn('name', project)
        self.assertNotIn('gourp', project)

        # update
        projectdb.update('not found', status='RUNNING')
        time.sleep(0.1)
        now = time.time()
        projectdb.update('abc', status='RUNNING')

        # check update
        projects = list(projectdb.check_update(now, fields=['name', 'status', 'group']))
        self.assertEqual(len(projects), 1)
        project = projects[0]
        self.assertEqual(project['name'], 'abc')
        self.assertEqual(project['status'], 'RUNNING')

        # get
        project = projectdb.get('not found')
        self.assertIsNone(project)

        project = projectdb.get('abc')
        self.assertEqual(project['name'], 'abc')
        self.assertEqual(project['status'], 'RUNNING')

        project = projectdb.get('name', ['group', 'status', 'name'])
        self.assertIn('status', project)
        self.assertNotIn('gourp', project)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_fetcher
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-15 22:10:35

import time
import threading
import unittest


import json
from fetcher.tornado_fetcher import Fetcher
class TestTaskDB(unittest.TestCase):
    sample_task_http = {
            'taskid': 'taskid',
            'project': 'project',
            'url': 'http://httpbin.org/get',
            'fetch': {
                'method': 'GET',
                'headers': {
                    'Cookie': 'a=b', 
                    'a': 'b'
                    },
                'timeout': 60,
                'save': 'abc',
                },
            'process': {
                'callback': 'callback',
                'save': [1, 2, 3],
                },
            }
    def setUp(self):
        self.fetcher = Fetcher(None, None)
        self.thread = threading.Thread(target=self.fetcher.run)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        self.fetcher.quit()
        self.thread.join()

    def test_http_get(self):
        result = self.fetcher.sync_fetch(self.sample_task_http)
        self.assertEqual(result['status_code'], 200)
        self.assertEqual(result['orig_url'], self.sample_task_http['url'])
        self.assertEqual(result['save'], self.sample_task_http['fetch']['save'])
        self.assertIn('content', result)
        content = json.loads(result['content'])
        self.assertIn('headers', content)
        self.assertIn('A', content['headers'])
        self.assertIn('Cookie', content['headers'])
        self.assertEqual(content['headers']['Cookie'], 'a=b')

########NEW FILE########
__FILENAME__ = test_processor
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-22 14:00:05

import os
import time
import unittest

from processor.processor import build_module
class TestProjectModule(unittest.TestCase):
    base_task = {
            'taskid': 'taskid',
            'project': 'test.project',
            'url': 'www.baidu.com/',
            'schedule': {
                'priority': 1,
                'retries': 3,
                'exetime': 0,
                'age': 3600,
                'itag': 'itag',
                'recrawl': 5,
                },
            'fetch': {
                'method': 'GET',
                'headers': {
                    'Cookie': 'a=b', 
                    },
                'data': 'a=b&c=d', 
                'timeout': 60,
                'save': [1, 2, 3],
                },
            'process': {
                'callback': 'callback',
                },
            }
    fetch_result = {
            'status_code': 200,
            'orig_url': 'www.baidu.com/',
            'url': 'http://www.baidu.com/',
            'headers': {
                'cookie': 'abc',
                },
            'content': 'test data',
            'cookies': {
                'a': 'b',
                },
            'save': [1, 2, 3],
            }

    def setUp(self):
        self.project = "test.project"
        self.script = open(os.path.join(os.path.dirname(__file__), 'data_handler.py')).read()
        self.env = {
                'test': True,
                }
        self.project_info = {
                'name': self.project,
                'status': 'DEBUG',
                }
        data = build_module({
            'name': self.project,
            'script': self.script
            }, {'test': True})
        self.module = data['module']
        self.instance = data['instance']

    def test_2_hello(self):
        self.base_task['process']['callback'] = 'hello'
        ret = self.instance.run(self.module, self.base_task, self.fetch_result)
        self.assertIsNone(ret.exception)
        self.assertEqual(ret.result, "hello world!")

    def test_3_echo(self):
        self.base_task['process']['callback'] = 'echo'
        ret = self.instance.run(self.module, self.base_task, self.fetch_result)
        self.assertIsNone(ret.exception)
        self.assertEqual(ret.result, "test data")

    def test_4_saved(self):
        self.base_task['process']['callback'] = 'saved'
        ret = self.instance.run(self.module, self.base_task, self.fetch_result)
        self.assertIsNone(ret.exception)
        self.assertEqual(ret.result, self.base_task['fetch']['save'])

    def test_5_echo_task(self):
        self.base_task['process']['callback'] = 'echo_task'
        ret = self.instance.run(self.module, self.base_task, self.fetch_result)
        self.assertIsNone(ret.exception)
        self.assertEqual(ret.result, self.project)

    def test_6_catch_status_code(self):
        self.fetch_result['status_code'] = 403
        self.base_task['process']['callback'] = 'catch_status_code'
        ret = self.instance.run(self.module, self.base_task, self.fetch_result)
        self.assertIsNone(ret.exception)
        self.assertEqual(ret.result, 403)
        self.fetch_result['status_code'] = 200

    def test_7_raise_exception(self):
        self.base_task['process']['callback'] = 'raise_exception'
        ret = self.instance.run(self.module, self.base_task, self.fetch_result)
        self.assertIsNotNone(ret.exception)
        logstr = ret.logstr()
        self.assertIn('info', logstr)
        self.assertIn('warning', logstr)
        self.assertIn('error', logstr)

    def test_8_add_task(self):
        self.base_task['process']['callback'] = 'add_task'
        ret = self.instance.run(self.module, self.base_task, self.fetch_result)
        self.assertIsNone(ret.exception)
        self.assertEqual(len(ret.follows), 1)
        self.assertEqual(len(ret.messages), 1)

########NEW FILE########
__FILENAME__ = test_scheduler
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-08 22:37:13

import os
import time
import shutil
import unittest
import logging
import logging.config
logging.config.fileConfig("logging.conf")


from scheduler.task_queue import TaskQueue
class TestTaskQueue(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.task_queue = TaskQueue()
        self.task_queue.rate = 100000
        self.task_queue.burst = 100000
        self.task_queue.processing_timeout = 0.2

        self.task_queue.put('a3', 2, time.time()+0.1)
        self.task_queue.put('a1', 1)
        self.task_queue.put('a2', 3)

    def test_1_priority_queue(self):
        self.assertEqual(self.task_queue.get(), 'a2')

    def test_2_time_queue(self):
        time.sleep(0.1)
        self.task_queue.check_update()
        self.assertEqual(self.task_queue.get(), 'a3')
        self.assertEqual(self.task_queue.get(), 'a1')

    def test_3_processing_queue(self):
        time.sleep(0.1)
        self.task_queue.check_update()
        self.assertEqual(self.task_queue.get(), 'a2')
        self.assertEqual(len(self.task_queue), 0)

    def test_4_done(self):
        self.task_queue.done('a2')
        self.task_queue.done('a1')
        time.sleep(0.1)
        self.task_queue.check_update()
        self.assertEqual(self.task_queue.get(), 'a3')
        self.assertEqual(self.task_queue.get(), None)


from scheduler.token_bucket import Bucket
class TestBucket(unittest.TestCase):
    def test_bucket(self):
        bucket = Bucket(100, 1000)
        self.assertEqual(bucket.get(), 1000)
        time.sleep(0.1)
        self.assertEqual(bucket.get(), 1000)
        bucket.desc(100)
        self.assertEqual(bucket.get(), 900)
        time.sleep(0.1)
        self.assertAlmostEqual(bucket.get(), 910, 0)
        time.sleep(0.1)
        self.assertAlmostEqual(bucket.get(), 920, 0)


import xmlrpclib
from multiprocessing import Queue
from scheduler.scheduler import Scheduler
from database.sqlite import taskdb, projectdb
from libs.utils import run_in_subprocess, run_in_thread
class TestScheduler(unittest.TestCase):
    taskdb_path = './test/data/task.db'
    projectdb_path = './test/data/project.db'
    check_project_time = 1
    scheduler_xmlrpc_port = 23333

    @classmethod
    def setUpClass(self):
        shutil.rmtree('./test/data/', ignore_errors=True)
        os.makedirs('./test/data/')

        def get_taskdb():
            return taskdb.TaskDB(self.taskdb_path)
        self.taskdb = get_taskdb()

        def get_projectdb():
            return projectdb.ProjectDB(self.projectdb_path)
        self.projectdb = get_projectdb()

        self.newtask_queue = Queue(10)
        self.status_queue = Queue(10)
        self.scheduler2fetcher = Queue(10)
        self.rpc = xmlrpclib.ServerProxy('http://localhost:%d' % self.scheduler_xmlrpc_port)

        def run_scheduler():
            scheduler = Scheduler(taskdb=get_taskdb(), projectdb=get_projectdb(),
                    newtask_queue=self.newtask_queue, status_queue=self.status_queue,
                    out_queue=self.scheduler2fetcher, data_path="./test/data/")
            scheduler.UPDATE_PROJECT_INTERVAL = 0.05
            scheduler.LOOP_INTERVAL = 0.01
            scheduler._last_tick = time.time() # not dispatch cronjob
            run_in_thread(scheduler.xmlrpc_run, port=self.scheduler_xmlrpc_port)
            scheduler.run()

        self.process = run_in_subprocess(run_scheduler)
        time.sleep(1)

    @classmethod
    def tearDownClass(self):
        shutil.rmtree('./test/data/', ignore_errors=True)
        self.process.terminate()

    def test_10_new_task_ignore(self):
        self.newtask_queue.put({
            'taskid': 'taskid',
            'project': 'test_project',
            'url': 'url'
            })
        self.assertEqual(self.rpc.size(), 0)

    def test_20_new_project(self):
        self.projectdb.insert('test_project', {
                'name': 'test_project',
                'group': 'group',
                'status': 'TODO',
                'script': 'import time\nprint time.time()',
                'comments': 'test project',
                'rate': 1.0,
                'burst': 10,
            })
        time.sleep(0.2)
        self.newtask_queue.put({
            'taskid': 'taskid',
            'project': 'test_project',
            'url': 'url',
            'fetch': {
                'data': 'abc',
                },
            'process': {
                'data': 'abc',
                },
            'schedule': {
                'age': 0,
                },
            })
        timeout = time.time() + 5
        while self.rpc.size() != 1 and timeout > time.time():
            time.sleep(0.1)
        self.assertEqual(self.rpc.size(), 1)
        self.assertEqual(self.rpc.counter('all', 'sum')['test_project']['pending'], 1)
        self.assertEqual(self.rpc.counter('all', 'sum')['test_project']['task'], 1)

    def test_30_update_project(self):
        self.projectdb.update('test_project', status="DEBUG")
        task = self.scheduler2fetcher.get(timeout=5)
        self.assertIsNotNone(task)
        self.assertEqual(task['project'], 'test_project')
        self.assertIn('fetch', task)
        self.assertIn('process', task)
        self.assertNotIn('schedule', task)
        self.assertEqual(task['fetch']['data'], 'abc')

    def test_40_taskdone_error_no_project(self):
        self.status_queue.put({
            'taskid': 'taskid',
            'project': 'no_project',
            'url': 'url'
            })
        time.sleep(0.1)
        self.assertEqual(self.rpc.size(), 0)

    def test_50_taskdone_error_no_track(self):
        self.status_queue.put({
            'taskid': 'taskid',
            'project': 'test_project',
            'url': 'url'
            })
        time.sleep(0.1)
        self.assertEqual(self.rpc.size(), 0)
        self.status_queue.put({
            'taskid': 'taskid',
            'project': 'test_project',
            'url': 'url',
            'track': {}
            })
        time.sleep(0.1)
        self.assertEqual(self.rpc.size(), 0)

    def test_60_taskdone_failed_retry(self):
        self.status_queue.put({
            'taskid': 'taskid',
            'project': 'test_project',
            'url': 'url',
            'track': {
                'fetch': {
                    'ok': True
                    },
                'process': {
                    'ok': False
                    },
                }
            })
        task = self.scheduler2fetcher.get(timeout=5)
        self.assertIsNotNone(task)

    def test_70_taskdone_ok(self):
        self.status_queue.put({
            'taskid': 'taskid',
            'project': 'test_project',
            'url': 'url',
            'track': {
                'fetch': {
                    'ok': True
                    },
                'process': {
                    'ok': True
                    },
                }
            })
        time.sleep(0.1)
        self.assertEqual(self.rpc.size(), 0)

    def test_80_newtask_age_ignore(self):
        self.newtask_queue.put({
            'taskid': 'taskid',
            'project': 'test_project',
            'url': 'url',
            'fetch': {
                'data': 'abc',
                },
            'process': {
                'data': 'abc',
                },
            'schedule': {
                'age': 30,
                },
            })
        time.sleep(0.1)
        self.assertEqual(self.rpc.size(), 0)

    def test_90_newtask_with_itag(self):
        time.sleep(0.1)
        self.newtask_queue.put({
            'taskid': 'taskid',
            'project': 'test_project',
            'url': 'url',
            'fetch': {
                'data': 'abc',
                },
            'process': {
                'data': 'abc',
                },
            'schedule': {
                'itag': "abc",
                'retries': 1
                },
            })
        task = self.scheduler2fetcher.get(timeout=5)
        self.assertIsNotNone(task)

        self.test_70_taskdone_ok()

    def test_a10_newtask_restart_by_age(self):
        self.newtask_queue.put({
            'taskid': 'taskid',
            'project': 'test_project',
            'url': 'url',
            'fetch': {
                'data': 'abc',
                },
            'process': {
                'data': 'abc',
                },
            'schedule': {
                'age': 0,
                'retries': 1
                },
            })
        task = self.scheduler2fetcher.get(timeout=5)
        self.assertIsNotNone(task)

    def test_a20_failed_retry(self):
        self.status_queue.put({
            'taskid': 'taskid',
            'project': 'test_project',
            'url': 'url',
            'track': {
                'fetch': {
                    'ok': True
                    },
                'process': {
                    'ok': False
                    },
                }
            })
        task = self.scheduler2fetcher.get(timeout=5)
        self.assertIsNotNone(task)

        self.status_queue.put({
            'taskid': 'taskid',
            'project': 'test_project',
            'url': 'url',
            'track': {
                'fetch': {
                    'ok': False
                    },
                'process': {
                    'ok': True
                    },
                }
            })
        time.sleep(0.2)

    def test_z10_startup(self):
        self.assertTrue(self.process.is_alive())

    def test_z20_quit(self):
        self.rpc._quit()
        time.sleep(0.2)
        self.assertFalse(self.process.is_alive())
        self.taskdb.conn.commit()
        self.assertEqual(self.taskdb.get_task('test_project', 'taskid')['status'], self.taskdb.FAILED)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-22 23:17:13

import os
import sys
import urlparse
from flask import Flask

app = Flask('webui',
        static_folder=os.path.join(os.path.dirname(__file__), 'static'),
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

def cdn_url_handler(error, endpoint, kwargs):
    if endpoint == 'cdn':
        path = kwargs.pop('path')
        cdn = app.config.get('cdn', 'http://cdn.staticfile.org/')
        return urlparse.urljoin(cdn, path)
    else:
        exc_type, exc_value, tb = sys.exc_info()
        if exc_value is error:
            raise exc_type, exc_value, tb
        else:
            raise error

app.handle_url_build_error = cdn_url_handler

########NEW FILE########
__FILENAME__ = debug
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-23 00:19:06


import re
import sys
import time
import datetime
import traceback
from app import app
from flask import abort, render_template, request, json
from libs.utils import hide_me
from libs.response import rebuild_response
from processor.processor import build_module
from processor.project_module import ProjectFinder, ProjectLoader

default_task = {
        'taskid': 'data:,on_start',
        'project': '',
        'url': 'data:,on_start',
        'process': {
            'callback': 'on_start',
            },
        }
default_script = open('libs/sample_handler.py').read()

def verify_project_name(project):
    if re.search(r"[^\w]", project):
        return False
    return True

@app.route('/debug/<project>')
def debug(project):
    if not verify_project_name(project):
        return 'project name is not allowed!', 400
    projectdb = app.config['projectdb']()
    info = projectdb.get(project)
    if info:
        script = info['script']
    else:
        script = default_script.replace('__DATE__', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    default_task['project'] = project
    return render_template("debug.html", task=default_task, script=script, project_name=project)

@app.before_first_request
def enable_projects_import():
    class DebuggerProjectFinder(ProjectFinder):
        def get_loader(self, name):
            info = app.config['projectdb']().get(name)
            if info:
                return ProjectLoader(info)
    sys.meta_path.append(DebuggerProjectFinder())

@app.route('/debug/<project>/run', methods=['POST', ])
def run(project):
    task = json.loads(request.form['task'])
    project_info = {
            'name': project,
            'status': 'DEBUG',
            'script': request.form['script'],
            }

    fetch_result = ""
    start_time = time.time()
    try:
        fetch_result = app.config['fetch'](task)
        response = rebuild_response(fetch_result)
        module = build_module(project_info, {
            'debugger': True
            })
        ret = module['instance'].run(module['module'], task, response)
    except Exception, e:
        type, value, tb = sys.exc_info()
        tb = hide_me(tb, globals())
        logs = ''.join(traceback.format_exception(type, value, tb))
        result = {
                'fetch_result': fetch_result,
                'logs': logs,
                'follows': [],
                'messages': [],
                'result': None,
                'time': time.time() - start_time,
                }
    else:
        result = {
                'fetch_result': fetch_result,
                'logs': ret.logstr(),
                'follows': ret.follows,
                'messages': ret.messages,
                'result': ret.result,
                'time': time.time() - start_time,
                }
        result['fetch_result']['content'] = response.text

    try:
        return json.dumps(result), 200, {'Content-Type': 'application/json'}
    except Exception, e:
        type, value, tb = sys.exc_info()
        tb = hide_me(tb, globals())
        logs = ''.join(traceback.format_exception(type, value, tb))
        result = {
                'fetch_result': "",
                'logs': logs,
                'follows': [],
                'messages': [],
                'result': None,
                'time': time.time() - start_time,
                }
        return json.dumps(result), 200, {'Content-Type': 'application/json'}

@app.route('/debug/<project>/save', methods=['POST', ])
def save(project):
    if not verify_project_name(project):
        return 'project name is not allowed!', 400
    projectdb = app.config['projectdb']()
    script = request.form['script']
    old_project = projectdb.get(project, fields=['name', 'status', ])
    if old_project:
        info = {
            'script': script,
            }
        if old_project.get('status') in ('DEBUG', 'RUNNING', ):
            info['status'] = 'CHECKING'
        projectdb.update(project, info)
    else:
        info = {
            'name': project,
            'script': script,
            'status': 'TODO',
            'rate': 1,
            'burst': 10
            }
        projectdb.insert(project, info)

    rpc = app.config['scheduler_rpc']
    rpc.update_project()

    return 'OK', 200

@app.route('/helper.js')
def resizer_js():
    host = request.headers['Host']
    return render_template("helper.js", host=host), 200, {'Content-Type': 'application/javascript'}

@app.route('/helper.html')
def resizer_html():
    height = request.args.get('height')
    script = request.args.get('script', '')
    return render_template("helper.html", height=height, script=script)

########NEW FILE########
__FILENAME__ = index
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-22 23:20:39

from app import app
from flask import abort, render_template, request, json


index_fields = ['name', 'group', 'status', 'comments', 'rate', 'burst', ]
@app.route('/')
def index():
    projectdb = app.config['projectdb']()
    return render_template("index.html", projects=projectdb.get_all(fields=index_fields))

@app.route('/update', methods=['POST', ])
def project_update():
    projectdb = app.config['projectdb']()
    project = request.form['pk']
    name = request.form['name']
    value = request.form['value']

    if name not in ('group', 'status', 'rate'):
        return 'unknow field: %s' % name, 400
    if name == 'rate':
        value = value.split('/')
        if len(value) != 2:
            return 'format error: rate/burst', 400
        update = {
                'rate': float(value[0]),
                'burst': float(value[1]),
                }
    else:
        update = {
                name: value
                }
    
    ret = projectdb.update(project, update)
    if ret:
        rpc = app.config['scheduler_rpc']
        rpc.update_project()
        return 'ok', 200
    else:
        return 'update error', 500

@app.route('/counter')
def counter():
    rpc = app.config['scheduler_rpc']
    time = request.args['time']
    type = request.args.get('type', 'sum')

    return json.dumps(rpc.counter(time, type)), 200, {'Content-Type': 'application/json'}

@app.route('/run', methods=['POST', ])
def runtask():
    rpc = app.config['scheduler_rpc']
    project = request.form['project']
    newtask = {
        "project": project,
        "taskid": "on_start",
        "url": "data:,on_start",
        "process": {
            "callback": "on_start",
            },
        "schedule": {
            "age": 0,
            "priority": 9,
            "force_update": True,
            },
        }

    ret = rpc.newtask(newtask)
    return json.dumps({"result": ret}), 200, {'Content-Type': 'application/json'}

########NEW FILE########
__FILENAME__ = webui
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-22 23:19:11

from webui.app import app
from fetcher import tornado_fetcher
from database.sqlite.projectdb import ProjectDB

def fetch(task):
    t, f = tornado_fetcher.Fetcher(None, None, async=False).fetch(task)
    return f

def projectdb():
    return ProjectDB('data/project.db')

config = {
        'fetch': fetch,
        'projectdb': projectdb,
        }

if __name__ == '__main__':
    app.config.update(**config)
    app.debug = True
    app.run()

########NEW FILE########
