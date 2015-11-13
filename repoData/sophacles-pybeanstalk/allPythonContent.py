__FILENAME__ = errors
class FailureError(Exception): pass
class JobError(FailureError): pass

class BeanStalkError(Exception): pass
class ProtoError(BeanStalkError): pass
class ServerError(BeanStalkError): pass

class NotConnected(BeanStalkError): pass

class OutOfMemory(ServerError): pass
class InternalError(ServerError): pass
class Draining(ServerError): pass

class BadFormat(ProtoError): pass
class UnknownCommand(ProtoError): pass
class ExpectedCrlf(ProtoError): pass
class JobTooBig(ProtoError): pass
class NotFound(ProtoError): pass
class NotIgnored(ProtoError): pass
class DeadlineSoon(ProtoError):pass

class UnexpectedResponse(ProtoError): pass

def checkError(linestr):
    '''Note, this will throw an error internally for every case that is a
    response that is NOT an error response, and that error will be caught,
    and checkError will return happily.

    In the case that an error was returned by beanstalkd, an appropriate error
    will be raised'''

    try:
        errname = ''.join([x.capitalize() for x in linestr.split('_')])
        err = eval(errname)('Server returned: %s' % (linestr,))
    except Exception, e:
        return
    raise err

########NEW FILE########
__FILENAME__ = job
import StringIO
from pprint import pformat
from functools import wraps

import yaml

import errors

DEFAULT_CONN = None

def honorimmutable(func):
    @wraps(func)
    def deco(*args, **kw):
        if args[0].imutable:
            raise errors.JobError("Cannot do that to a job you don't own")
        return func(*args, **kw)
    return deco

class Job(object):
    ''' class Job is an optional class for keeping track of jobs returned
    by the beanstalk server.

    It is designed to be as flexible as possible, with a minimal number of extra
    methods. (See below).  It has 4 protocol methods, for dealing with the
    server via a connection object. It also has 2 methods, _serialize and
    _unserialize for dealing with the data returned by beanstalkd. These
    default to a simple yaml dump and load respectively.

    One intent is that in simple applications, the Job class can be a
    superclass or mixin, with a method run. In this case, the pybeanstalk.main()
    loop will get a Job, call its run method, and when finished delete the job.

    In more complex applications, where the pybeanstalk.main is insufficient,
    Job was designed so that processing data (e.g. data is more of a message),
    can be handled within the specific data object (JobObj.data) or by external
    means. In this case, Job is just a convenience class, to simplify job
    management on the consumer end.
    '''

    def __init__(self, conn = None, jid=0, pri=0, data='', state = 'ok', **kw):

        if not any([conn, DEFAULT_CONN]):
            raise AttributeError("No connection specified")

        self._conn = conn if conn else DEFAULT_CONN
        self.jid = jid
        self.pri = pri
        self.delay = 0
        self.state = state
        self.data = data if data else ''

        self.imutable = bool(kw.get('imutable', False))
        self._from_queue = bool(kw.get('from_queue', False))
        self.tube = kw.get('tube', 'default')
        self.ttr = kw.get('ttr', 60)

    def __eq__(self, comparable):
        if not isinstance(comparable, Job):
            return False
        return not all([cmp(self.Server, comparable.Server),
                        cmp(self.jid, comparable.jid),
                        cmp(self.state, comparable.state),
                        cmp(self.data, comparable.data)])

    def __del__(self):
        self.Finish()

    def __str__(self):
        return pformat(self._serialize())

    def __getitem__(self, key):
        #validate key for TypeError
        #TODO: make elegant
        validkey = isinstance(key, basestring)
        if not validkey:
            raise TypeError, "Invalid subscript type: %s" % type(key)
        #return KeyError
        try:
            value = getattr(self, key)
        except AttributeError, e:
            raise KeyError, e
        else:
            return value

    def _unserialize(self, data):
        self.data = yaml.dump(data)

    def _serialize(self):
        handler = StringIO.StringIO({
            'data' : self.data,
            'jid' : self.jid,
            'state' : self.state,
            'conn' : str(self.Server)
        })
        return yaml.load(handler)

    def run(self):
        raise NotImplemented('The Job.run method must be implemented in a subclass')

    def Queue(self):
        if self._from_queue:
            self.Delay(self.delay)
            return
        oldtube = self.Server.tube
        if oldtube != self.tube:
            self.Server.use(self.tube)
        self.Server.put(self._serialize(), self.pri, self.delay, self.ttr)
        if oldtube != self.tube:
            self.Server.use(oldtube)

    @honorimmutable
    def Return(self):
        try:
            self.Server.release(self.jid, self.pri, 0)
        except errors.NotFound:
            return False
        except:
            raise
        else:
            return True

    @honorimmutable
    def Delay(self, delay):
        try:
            self.Server.release(self.jid, self.pri, delay)
        except errors.NotFound:
            return False
        except:
            raise
        else:
            return True

    @honorimmutable
    def Finish(self):
        try:
            self.Server.delete(self.jid)
        except errors.NotFound:
            return False
        except:
            raise
        else:
            return True

    @honorimmutable
    def Touch(self):
        try:
            self.Server.touch(self.jid)
        except errors.NotFound:
            return False
        except:
            raise
        else:
            return True

    @honorimmutable
    def Bury(self, newpri = 0):
        if newpri:
            self.pri = newpri

        try:
            self.Server.bury(self.jid, newpri)
        except errors.NotFound:
            return False
        except:
            raise
        else:
            return True

    @property
    def Info(self):
        try:
            stats = self.Server.stats_job(self.jid)
        except:
            raise
        else:
            return stats

    @property
    def Server(self):
        return self._conn

def newJob(**kw):
    kw['from_queue'] = False
    return Job(**kw)

########NEW FILE########
__FILENAME__ = multiserverconn
import socket
import select
import random
import logging
import threading
import asyncore
import asynchat
import errno
import traceback
import time
import sys
import copy

import protohandler
from serverconn import ServerConn
from job import Job

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# This should be set to experiment with from the importing
# module.
# For example:
# from beanstalk import multiserverconn
# from multiserverconn import ServerPool ...
# multiserverconn.ASYNCORE_TIMEOUT = 5

ASYNCORE_TIMEOUT = 0.1
ASYNCORE_COUNT   = 10

class ServerInUse(Exception): pass

class AsyncServerConn(object, asyncore.dispatcher):
    def __init__(self, server, port, job = False):
        self.job = job
        self.server = server
        self.port = port

        self.__line = None
        self.__handler = None
        self.__result = None
        self.__waiting = False
        self.__mutex = threading.Lock()

        self._socket  = None
        asyncore.dispatcher.__init__(self)

    def __repr__(self):
        s = "<0x%(id)s %(object)s>"
        return s % {'id' : id(self), 'object' : self }

    def __str__(self):
        s = "%(class)s(%(ip)s:%(port)s#[%(active)s][%(waiting)s])"
        active_ = "Open" if self._socket else "Closed"
        waiting_ = "Waiting" if self.__waiting else "NotWaiting"
        return s % {"class" : self.__class__.__name__,
                    "active" : active_,
                    "ip" : self.server,
                    "port" : self.port,
                    "waiting" : waiting_}

    def __getattribute__(self, attr):
        res = getattr(protohandler, 'process_%s' % attr, None)
        if res:
            def caller(*args, **kw):
                logger.info("Calling %s on %r with args(%s), kwargs(%s)",
                             res.__name__, self, args, kw)

                func = self._do_interaction
                func(*res(*args, **kw))
                asyncore.loop(use_poll=True,
                              timeout=ASYNCORE_TIMEOUT,
                              count=ASYNCORE_COUNT)
                return self.result
            return caller

        return super(AsyncServerConn, self).__getattribute__(attr)

    def __eq__(self, comparable):
        #for unit testing
        assert isinstance(comparable, AsyncServerConn)
        return not any([cmp(self.server, comparable.server),
                        cmp(self.port, comparable.port)])

    def __assert_not_waiting(self):
        if self.waiting:
            raise ServerInUse, ("%s is currently in use!" % self, self)

    def _get_response(self):
        while True:
            recv = self._socket.recv(self.handler.remaining)

            if not recv:
                closedmsg = "Remote server %(server)s:%(port)s has "\
                            "closed connection" % { "server" : self.server,
                                                    "port" : self.port}
                self.close()
                raise protohandler.errors.NotConnected, (closedmsg, self)

            res = self.handler(recv)
            if res: break

        if self.job and 'jid' in res:
            res = self.job(conn=self,**res)
        return res

    def _do_interaction(self, line, handler):
        self.__assert_not_waiting()
        self.__result = None
        self.line = line
        self.handler = handler

    def _get_watchlist(self):
        return self.list_tubes_watched()['data']

    def _set_watchlist(self, seq):
        if len(seq) == 0:
            seq.append('default')
        seq = set(seq)
        current = set(self._get_watchlist())
        add = seq - current
        rem = current - seq

        for x in add:
            self.watch(x)
        for x in rem:
            self.ignore(x)
        return

    watchlist = property(_get_watchlist, _set_watchlist)

    def threadsafe(func):
        def make_threadsafe(self, *args, **kwargs):
            logger.debug("Acquiring mutex")
            self.__mutex.acquire()
            try:
                logger.info("Calling %s with args: %s kwargs: %s",
                             func.__name__, args, kwargs)
                return func(self, *args, **kwargs)
            finally:
                logger.debug("Releasing mutex")
                self.__mutex.release()
        return make_threadsafe

    @threadsafe
    def _set_waiting(self, waiting):
        self.__waiting = waiting

    def _get_waiting(self):
        return self.__waiting

    waiting = property(_get_waiting, _set_waiting)

    @threadsafe
    def _set_line(self, line):
        self.__line = line

    def _get_line(self):
        return self.__line

    line = property(_get_line, _set_line)

    @threadsafe
    def _set_handler(self, handler):
        self.__handler = handler

    def _get_handler(self):
        return self.__handler

    handler = property(_get_handler, _set_handler)

    def _get_result(self):
        return self.__result

    result = property(_get_result)

    @property
    def tube(self):
        return self.list_tube_used()['tube']

    def post_connection(func):
        def handle_post_connect(self, *args, **kwargs):
            value = func(self, *args, **kwargs)
            protohandler.MAX_JOB_SIZE = self.stats()['data']['max-job-size']
            return value
        return handle_post_connect

    @post_connection
    def connect(self):
        # else the socket is not open at all
        # so, open the socket, and add it to the dispatcher
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_socket(self._socket) # set socket to asyncore.dispatcher
        self.set_reuse_addr() # try to re-use the address
        self._socket.connect((self.server, self.port))

    def interact(self, line):
        self.__assert_not_waiting()
        try:
            self._socket.sendall(line)
        except Exception, e:
            raise protohandler.errors.ProtoError(e)

    def close(self):
        self._socket.close()
        self.del_channel()
        # very important in python to set to None
        # if socket is not set to None, then it will try to re-use the same
        # file descriptor...
        self._socket = None

    def fileno(self):
        return self._socket.fileno()

    @threadsafe
    def handle_read(self):
        logger.info("Handling read on %s", self)
        try:
            self.__result = self._get_response()
            logger.info("Results are: %s", self.result)
        finally:
            # must make sure that waiting is set to false!
            self.__waiting = False

    @threadsafe
    def handle_write(self):
        logger.info("writing: %s to %s", self.line, self)
        self.interact(self.line)
        self.__waiting = True
        self.__line = None
        logger.info("Handled write")

    def handle_connect(self):
        logger.info("Connected to: %s", self)

    def handle_close(self):
        logger.info("Closing connection to: %s", self)

    def handle_error(self):
        # get exception information
        exctype, value = sys.exc_info()[:2]
        # if we disconnected..
        if exctype == protohandler.errors.NotConnected:
            msg, server = value
            logger.warn("Got %s, so, reconnecting to: %s", msg, server)
            assert server == self # sanity 
            # remove from the socket map
            del asyncore.socket_map[self.fileno()]
            # reconnect
            self.connect()
        else:
            raise
            asyncore.dispatcher.handle_error(self)

    def handle_accept(self):
        logger.info("Handle socket accept...")

    def readable(self):
        """This socket is only readable if it's waiting."""
        logger.debug("Checking if %s is readable.", self)
        return self.waiting

    def writable(self):
        """This socket is only writeable if something gave a line"""
        logger.debug("Checking if %s is writeable.", self)
        return self.line

class ServerPool(object):
    """ServerPool is a queue implementation of ServerConns with distributed
    server support.

    @serverlist is a list of tuples as so: (ip, port, job)

    """
    def __init__(self, serverlist):
        # build servers into the self.servers list
        self.servers = []
        for ip, port, job in serverlist:
            self.add_server(ip, port, job)

    def _get_watchlist(self):
        """Returns the global watchlist for all servers"""
        # TODO: it's late and I'm getting tired, going to just make
        # a list for now and see maybe later if I want to do a dict
        # with the server IPs as the keys as well as their watchlist..
        L = []
        for server in self.servers:
            L.extend(server.watchlist)
        return list(set(L))

    def _set_watchlist(self, value):
        """Sets the watchlist for all global servers"""
        for server in self.servers:
            server.watchlist = value

    watchlist = property(_get_watchlist, _set_watchlist)

    def _server_cmp(self, ip, port):
        def comparison(server):
            matching_port = 0
            if port:
                matching_port = cmp(server.port, port)
            return not any([cmp(server.server, ip), matching_port])
        return comparison

    def close(self):
        for server in self.servers:
            server.close()
        del self.servers[:]

    def clone(self):
        return ServerPool(map(lambda s: (s.server, s.port, s.job), self.servers))

    def get_random_server(self):
        #random seed by local time
        random.seed()
        try:
            choice = random.choice(self.servers)
        except IndexError, e:
            # implicitly convert IndexError to BeanStalkError
            NotConnected = protohandler.errors.NotConnected
            raise NotConnected("Not connected to a server!")
        else:
            return choice

    def remove_server(self, ip, port=None):
        """Removes the server from the server list and returns True on success.
        Else, if the target server doesn't exist, Returns false.

        If port is None, then all internal matching server ips are removed.

        """
        target = filter(self._server_cmp(ip, port), self.servers)
        if target:
            for t in target:
                t.close()
                self.servers.remove(t)
        return bool(target)

    def add_server(self, ip, port, job=Job):
        """Checks if the server doesn't already exist and adds it. Returns
        True on successful addition or False if the server already exists.

        Upon server addition, the server socket is automatically created
        and a connection is created.

        """
        target = filter(self._server_cmp(ip, port), self.servers)
        # if we got a server back
        if not target:
            server = AsyncServerConn(ip, port, job)
            server.pool_instance = self
            server.connect()
            self.servers.append(server)

        # return the opposite of target
        return not bool(target)

    def retry_until_succeeds(func):
        def retrier(self, *args, **kwargs):
            while True:
                try:
                    value = func(self, *args, **kwargs)
                except ServerInUse, e:
                    logger.exception(e[0])
                    # this should be caught in the function..
                    # clean this up a bit?
                    raise
                except protohandler.errors.Draining, e:
                    # ignore
                    pass
                except protohandler.errors.NotConnected, e:
                    # not connected..
                    logger.warning(e[0])
                    server = e[1]
                    self.remove_server(server.server, server.port)
                    logger.warn("Attempting to re-connect to: %s", server)
                    server.connect()
                    self.servers.append(server)
                else:
                    return value
        return retrier

    def multi_interact(self, line, handler):
        for server in self.servers:
            logger.warn("Sending %s to: %s", line, server)
            try:
                server._do_interaction(line, handler.clone())
            except ServerInUse, (msg, server):
                logger.info(msg)
                # ignore
                pass

        asyncore.loop(use_poll=True,
                      timeout=ASYNCORE_TIMEOUT,
                      count=ASYNCORE_COUNT)
        results = filter(None, (s.result for s in self.servers))
        return results

    @retry_until_succeeds
    def _all_broadcast(self, cmd, *args, **kwargs):
        """Broadcast to all servers and return the results in a compacted
        dictionary, where the keys are the server objects and the values are
        the result of the command.

        """
        func = getattr(protohandler, "process_%s" % cmd)
        return self.multi_interact(*func(*args, **kwargs))

    @retry_until_succeeds
    def _rand_broadcast(self, cmd, *args, **kwargs):
        """Randomly select a server from the pool of servers and broadcast
        the desired command.

        Retries if various error connections are encountered.
        """
        random_server = self.get_random_server()
        return getattr(random_server, cmd)(*args, **kwargs)

    @retry_until_succeeds
    def _first_broadcast_response(self, cmd, *args, **kwargs):
        """Broadcast to all servers and return the first valid server
        response.

        If no responses are found, return an empty list.

        This implementation actually just returns ONE response..

        """
        # TODO Fix this..
        result = self._all_broadcast(cmd, *args, **kwargs)
        if result:
            if isinstance(result, list):
                result = result[0]
            return result

        return []

    def put(self, *args, **kwargs):
        return self._rand_broadcast("put", *args, **kwargs)

    def reserve(self, *args, **kwargs):
        return self._all_broadcast("reserve", *args, **kwargs)

    def reserve_with_timeout(self, *args, **kwargs):
        return self._all_broadcast("reserve_with_timeout", *args, **kwargs)

    def use(self, *args, **kwargs):
        return self._all_broadcast("use", *args, **kwargs)

    def peek(self, *args, **kwargs):
        return self._all_broadcast("peek", *args, **kwargs)

    def peek_delayed(self, *args, **kwargs):
        return self._first_broadcast_response("peek_delayed", *args, **kwargs)

    def peek_buried(self, *args, **kwargs):
        return self._first_broadcast_response("peek_buried", *args, **kwargs)

    def peek_ready(self, *args, **kwargs):
        return self._first_broadcast_response("peek_ready", *args, **kwargs)

    def combine_stats(func):
        def combiner(self, *args, **kwargs):
            appendables = set(['name', 'version', 'pid'])
            returned = func(self, *args, **kwargs)

            if not returned:
                return {}

            # need to combine these results
            result = dict(reduce(lambda x, y: x.items() + y.items(), returned))
            # set-ify that which we want to add
            for a in appendables:
                try:
                    result['data'][a] = set(map(lambda x: x['data'][a],
                                                returned))
                except KeyError:
                    # if the appendable key isnt in the result..
                    # ignore
                    pass

            del returned[:]
            return result
        return combiner

    @combine_stats
    def stats(self, *args, **kwargs):
        return self._all_broadcast("stats", *args, **kwargs)

    @combine_stats
    def stats_tube(self, *args, **kwargs):
        return self._all_broadcast("stats_tube", *args, **kwargs)

    @retry_until_succeeds
    def apply_and_compact(func):
        """Applies func's func.__name__ to all servers in the server pool
        and tallies results into a dictionary.

        Returns a dictionary of all results tallied into one.

        """
        def generic_applier(self, *args, **kwargs):
            cmd = func.__name__
            results = {}
            for server in self.servers:
                results[server] = getattr(server, cmd)(*args, **kwargs)
            return results
        return generic_applier

    @apply_and_compact
    def list_tubes(self, *args, **kwargs):
        # instead of having to repeating myself by writing an iteration of
        # all servers to execute and store results in a hash, the decorator 
        # apply_and_compact will apply the function name (e.g. list_tubes)
        # to all servers and compact/tally them all into a dictionary
        #
        # we don't use multi_interact here because we don't need to handle
        # a response explicitly
        pass

    @apply_and_compact
    def list_tube_used(self, *args, **kwargs):
        pass

    @apply_and_compact
    def list_tubes_watched(self, *args, **kwargs):
        pass

    @property
    def tubes(self):
        """Returns a amalgamated list of tubes used on all servers

        For unit tests, this should be converted to a set.

        """
        return [tubes['tube'] for tubes in self.list_tube_used().itervalues()]

########NEW FILE########
__FILENAME__ = protohandler
"""
Protocol handler for processing the beanstalk protocol

See reference at:
    http://xph.us/software/beanstalkd/protocol.txt (as of Feb 2, 2008)

This module contains a set of functions which will implement the protocol for
beanstalk.  The beanstalk protocol simple, consisting of a command and a
response. Each command is 1 line of text. Each response is 1 line of text, and
optionally (depending on the nature of the command) a chunk of data.
If the data is related to the beanstalk server, or its jobs, it is encoded
as a yaml file. Otherwise it is a raw character stream.

The implementation is designed so that there is a function for each possible
command line in the protocol. These functions return the command line, and a
function for handling the response. The handler will return a ditcionary
conatining the response. The handler is a generator that when fed data will
yeild None when more input is expected, and the results dict when all the data
is provided. Further, it has an attribute, remaining, which is an integer that
specifies how many bytes are still expected in the data portion of a reply.

This may seem a bit round-about, but it allows for many different styles* of
programming to use the same bit of code for implementing the protocol.

* e.g. the simple syncronous connection and the twisted client both use this :)

NOTE: there are mre lines of documentation in this file than lines of code.
It may be that I need to practice terseness in this form as much as i do with
my code...
"""


import StringIO
import re
from itertools import izip, imap
from functools import wraps

import yaml

import errors
from errors import checkError

# default value on server
MAX_JOB_SIZE = (2**16) - 1

def load_yaml(yaml_string):
    handler = StringIO.StringIO(yaml_string)
    return yaml.load(handler)


def protProvider(cls):
    ''' Class decorator to be applied to anything that we want to provide the
    beanstalk protocol (e.g. connections).  This will implement all the
    protocol functions (i.e. process_*) as methods in the class that is
    decorated. in ver < py2.6 this should be cls = protProvider(cls), in
    2.6 and higher, they got all nice and implemented the decorator sugar for
    classes'''
    for name, value in globals().items():
        if not name.startswith('process_'):
            continue
        name = name.partition('_')[2]
        setattr(cls, name, staticmethod(value))

    return cls

class ExpectedData(Exception): pass

class Response(object):
    '''This is a simple object for describing the expected response to a
    command. It is intended to be subclassed, and the subclasses to be named
    in such a way as to describe the response.  For example, I've used
    OK for the expected normal response, and Buried for the cases where
    a command can result in a burried job.

    Arguments/attributes:
        word: the first word sent back from the server (eg OK)
        args: the server replies with space separated positional arguments,
              this describes the names of those argumens
        hasData: boolean stating whether or not to expect a data stream after
                 the response line
        parsefunc: a function, used to transform the data. This will be called
                   just prior to returning the dict, and its result will
                   be under the key 'data'
    '''

    def __init__(self, word, args =None , hasData = False, parsefunc = None):
        self.word = word
        self.args = args if args else []
        self.hasData = hasData
        if parsefunc:
            self.parsefunc = parsefunc
        else:
            self.parsefunc = (lambda x: x)

    def __str__(self):
        '''will fail if attr name hasnt been set by subclass or program'''
        return self.__class__.__name__.lower()

class OK(Response): pass
class TimeOut(Response): pass
class Buried(Response): pass

def intit(val):
    try: return int(val)
    except: return val


class Handler(object):
    '''
    Handler: generic response consumer for beanstalk.

    Each handler object has a __call__ method, allowing it to be fed data.
    '''
    def __init__(self, *responses):

        self.lookup =  dict((r.word, r) for r in responses)
        self.remaining = 10

        h = self.handler()
        h.next()
        self.__h = h.send

    def clone(self):
        """Clone the handler

        This method is primarily used in the distributed client to pass fresh
        generators to handle incoming data buffers.

        """
        return Handler(*self.lookup.values())

    def __call__(self, val):
        return self.__h(val)

    # Note: this takes advanage of 2.5+ style generators. The syntax:
    # x = (yield value)
    # yields the value, and expects x.send(foo) to be called. Foo will be
    # assigned to x.
    def handler(self):
        eol = '\r\n'

        response = ''
        sep = ''

        # TODO: figure out the max possible response line, and set the default
        # remaining to that amount. check for sep or that amount of data...
        # its a bit of a sanity check, as this could be attacked.
        #
        while not sep:
            response += (yield None)
            response, sep, data = response.partition(eol)

        checkError(response)

        response = response.split(' ')
        word = response.pop(0)

        resp = self.lookup.get(word, None)

        # sanity checks
        if not resp:
            errstr = "Response was: %s %s" % (word, ' '.join(response))
        elif len(response) != len(resp.args):
            errstr = "Response %s had wrong # args, got %s (expected %s)"
            errstr %= (word, response, args)
        else: # all good
            errstr = ''

        if errstr: raise errors.UnexpectedResponse(errstr)

        reply = dict(izip(resp.args, imap(intit, response)))
        reply['state'] = str(resp)

        if not resp.hasData:
            self.remaining = 0
            yield reply
            return

        self.remaining = (reply['bytes'] + 2) - len(data)

        while self.remaining > 0:
            newdata = (yield None)
            self.remaining -= len(newdata)
            data += newdata

        if not data.endswith(eol) or not (len(data) == reply['bytes']+2):
            raise errors.ExpectedCrlf('Data not properly sent from server')

        reply['data'] = resp.parsefunc(data.rstrip(eol))
        yield reply
        return

# since the beanstalk protocol uses a simple command-response structure,
# this decorator makes life easy.  The function it wraps corresponds to a
# beanstalk command, and returns the appropriate command text.
# This decorator sets up the structure for handling a response.
#
# One thing that may be a bit tricky for those who aren't familiar with python
# decorators: This changes return value for command function. The functions
# return a single sting, but after decoration return a tuple of:
#      (string, handler)
def interaction(*responses):
    '''Decorator-factory for process_* protocol functions. Takes N response objects
    as arguments, and returns decorator.

    The decorator replaces the wrapped function, and returns the result of
    the original function, as well as a response handler set up to use the
    expected responses.'''
    def deco(func):
        @wraps(func)
        def newfunc(*args, **kw):
            line = func(*args, **kw)
            handler = Handler(*responses)
            return (line, handler)
        return newfunc
    return deco

_namematch = re.compile(r'^[a-zA-Z0-9+\(\);.$][a-zA-Z0-9+\(\);.$-]{0,199}$')
def check_name(name):
    '''used to check the validity of a tube name'''
    if not _namematch.match(name):
        raise errors.BadFormat('Illegal name')

@interaction(OK('INSERTED',['jid']), Buried('BURIED', ['jid']))
def process_put(data, pri=1, delay=0, ttr=60):
    """
    put
        send:
            put <pri> <delay> <ttr> <bytes>
            <data>

        return:
            INSERTED <jid>
            BURIED <jid>
    NOTE: this function does a check for job size <= max job size, and
    raises a protocol error when the size is too big.
    """
    dlen = len(data)
    if dlen >= MAX_JOB_SIZE:
        raise errors.JobTooBig('Job size is %s (max allowed is %s' %\
            (dlen, MAX_JOB_SIZE))
    putline = 'put %(pri)s %(delay)s %(ttr)s %(dlen)s\r\n%(data)s\r\n'
    return putline % locals()

@interaction(OK('USING', ['tube']))
def process_use(tube):
    '''
    use
        send:
            use <tube>
        return:
            USING <tube>
    '''
    check_name(tube)
    return 'use %s\r\n' % (tube,)

@interaction(OK('RESERVED', ['jid','bytes'], True))
def process_reserve():
    '''
     reserve
        send:
            reserve

        return:
            RESERVED <id> <bytes>
            <data>

            DEADLINE_SOON
    '''
    x = 'reserve\r\n'
    return x

@interaction(OK('RESERVED', ['jid','bytes'], True), TimeOut('TIMED_OUT'))
def process_reserve_with_timeout(timeout=0):
    '''
     reserve
        send:
            reserve-with-timeout <timeout>

        return:
            RESERVED <id> <bytes>
            <data>

            TIME_OUT

            DEADLINE_SOON
    Note: After much internal debate I chose to go this route,
    with hte one-to-one mappaing of function to protocol command. Higher level
    objects, like the connection objects, can combine these if they see fit.
    '''
    if int(timeout) < 0:
        raise AttributeError('timeout must be greater than 0')
    return 'reserve-with-timeout %s\r\n' % (timeout,)

@interaction(OK('DELETED'))
def process_delete(jid):
    """
    delete
        send:
            delete <id>

        return:
            DELETED
            NOT_FOUND
    """
    return 'delete %s\r\n' % (jid,)

@interaction(OK('RELEASED'), Buried('BURIED'))
def process_release(jid, pri=1, delay=0):
    """
    release
        send:
            release <id> <pri> <delay>

        return:
            RELEASED
            BURIED
            NOT_FOUND
    """
    return 'release %(jid)s %(pri)s %(delay)s\r\n' % locals()

# XXX: semantic question: is this better being an OK since burried is the
# expected response. Or is it better being a burried since it is the more
# accurate description, but breaking the rest of semantics of the code?
#   ^^ this isnt a pressing issue, because for now we still return a
#      state string pair, which is currently backwards compatible
@interaction(OK('BURIED'))
def process_bury(jid, pri=1):
    """
    bury
        send:
            bury <id> <pri>

        return:
            BURIED
            NOT_FOUND
    """
    return 'bury %(jid)s %(pri)s\r\n' % locals()

@interaction(OK('WATCHING', ['count']))
def process_watch(tube):
    '''
    watch
        send:
            watch <tube>
        return:
            WATCHING <tube>
    '''
    check_name(tube)
    return 'watch %s\r\n' % (tube,)

@interaction(OK('WATCHING', ['count']))
def process_ignore(tube):
    '''
    ignore
        send:
            ignore <tube>
        reply:
            WATCHING <count>

            NOT_IGNORED
    '''
    check_name(tube)
    return 'ignore %s\r\n' % (tube,)

@interaction(OK('FOUND', ['jid','bytes'], True))
def process_peek(jid = 0):
    """
    peek
        send:
            peek <id>

        return:
            NOT_FOUND
            FOUND <id> <bytes>
            <data>

    """
    if jid:
        return 'peek %s\r\n' % (jid,)

@interaction(OK('FOUND', ['jid','bytes'], True))
def process_peek_ready():
    '''
    peek-ready
        send:
            peek-ready
        return:
            NOT_FOUND
            FOUND <id> <bytes>
    '''
    return 'peek-ready\r\n'

@interaction(OK('FOUND', ['jid','bytes'], True))
def process_peek_delayed():
    '''
    peek-delayed
        send:
            peek-delayed
        return:
            NOT_FOUND
            FOUND <id> <bytes>
    '''
    return 'peek-delayed\r\n'

@interaction(OK('FOUND', ['jid','bytes'], True))
def process_peek_buried():
    '''
    peek-buried
        send:
            peek-buried
        return:
            NOT_FOUND
            FOUND <id> <bytes>
    '''
    return 'peek-buried\r\n'

@interaction(OK('KICKED', ['count']))
def process_kick(bound=10):
    """
    kick
        send:
            kick <bound>

        return:
            KICKED <count>
    """
    return 'kick %s\r\n' % (bound,)

@interaction(OK('TOUCHED'))
def process_touch(jid):
    """
    touch
        send:
            touch <job>

        return:
            TOUCHED
            NOT_FOUND
    """
    return 'touch %s\r\n' % (jid,)

@interaction(OK('OK', ['bytes'], True, load_yaml))
def process_stats():
    """
    stats
        send:
            stats
        return:
            OK <bytes>
            <data> (YAML struct)
    """
    return 'stats\r\n'


@interaction(OK('OK', ['bytes'], True, load_yaml))
def process_stats_job(jid):
    """
    stats
        send:
            stats-job <jid>
        return:
            OK <bytes>
            <data> (YAML struct)

            NOT_FOUND
    """
    return 'stats-job %s\r\n' % (jid,)

@interaction(OK('OK', ['bytes'], True, load_yaml))
def process_stats_tube(tube):
    """
    stats
        send:
            stats-tube <tube>
        return:
            OK <bytes>
            <data> (YAML struct)

            NOT_FOUND
    """
    check_name(tube)
    return 'stats-tube %s\r\n' % (tube,)

@interaction(OK('OK', ['bytes'], True, load_yaml))
def process_list_tubes():
    '''
    list-tubes
        send:
            list-tubes
        return:
            OK <bytes>
            <data> (YAML struct)
    '''
    return 'list-tubes\r\n'

@interaction(OK('USING', ['tube']))
def process_list_tube_used():
    '''
    list-tube-used
        send:
            list-tubes
        return:
            USING <tube>
    '''
    return 'list-tube-used\r\n'

@interaction(OK('OK', ['bytes'], True, load_yaml))
def process_list_tubes_watched():
    '''
    list-tubes-watched
        send:
            list-tubes-watched
        return:
            OK <bytes>
            <data> (YAML struct)
    '''
    return 'list-tubes-watched\r\n'

########NEW FILE########
__FILENAME__ = serverconn
import socket
import select
import protohandler
import logging

_debug = False
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ConnectionError(Exception): pass


class ServerConn(object):
    """ServerConn is a simple, single thread single connection serialized
    beanstalk connection.  This class is meant to be used as is, or be the base
    class for more sophisticated connection handling.The methods that are
    intended to be overridden are the ones that begin with _ and __. These
    are the meat of the connection handling. The rest are just convenience
    wrappers around the protohandler methods.

    The Proto class returns a function as part of it's handling/conversion of
    the beanstalk protocol. This function is threadsafe and event safe, meant
    to be used as a callback. This should greatly simplify the writing of a
    twisted or libevent serverconn class

    """
    def __init__(self, server, port, job = False):
        self.poller = getattr(select, 'poll', lambda : None)()
        self.job = job
        self.server = server
        self.port = port

        self._socket  = None
        self.__makeConn()

    def __repr__(self):
        s = "<[%(active)s]%(class)s(%(ip)s:%(port)s)>"
        active_ = "Open" if self._socket else "Closed"
        return s % {"class" : self.__class__.__name__,
                    "active" : active_, "ip" : self.server, "port" : self.port}

    def __getattribute__(self, attr):
        logger.debug("Fetching: %s", attr)
        res = super(ServerConn, self).__getattribute__(attr)
        logger.debug("Attribute found: %s...", res)
        if not hasattr(res, "__name__") or not res.__name__.startswith('process_'):
            return res
        def caller(*args, **kw):
            logger.info("Calling %s with: args(%s), kwargs(%s)",
                         res.__name__, args, kw)
            return self._do_interaction(*res(*args, **kw))
        return caller

    def __eq__(self, comparable):
        # for unit testing
        assert isinstance(comparable, ServerConn)
        return not any([cmp(self.server, comparable.server),
                        cmp(self.port, comparable.port)])

    def __makeConn(self):
        self._socket = socket.socket()
        self._socket.connect((self.server, self.port))
        if self.poller:
            self.poller.register(self._socket, select.POLLIN)
        protohandler.MAX_JOB_SIZE = self.stats()['data']['max-job-size']

    def __writeline(self, line):
        try:
            self._socket.sendall(line)
        except:
            raise protohandler.errors.ProtoError

    def _get_response(self, handler):
        data = ''
        pcount = 0
        while True:
            if _debug and self.poller and not self.poller.poll(1):
                pcount += 1
                if pcount >= 20:
                    raise Exception('poller timeout %s times in a row' % (pcount,))
                else: continue
            pcount = 0
            recv = self._socket.recv(handler.remaining)
            if not recv:
                closedmsg = "Remote server %(server)s:%(port)s has "\
                            "closed connection" % { "server" : server.ip,
                                                    "port" : server.port}
                self.close()
                raise protohandler.errors.ProtoError(closedmsg)
            res = handler(recv)
            if res: break

        if self.job and 'jid' in res:
            res = self.job(conn=self,**res)
        return res

    def _do_interaction(self, line, handler):
        self.__writeline(line)
        return self._get_response(handler)

    def _get_watchlist(self):
        return self.list_tubes_watched()['data']

    def _set_watchlist(self, seq):
        if len(seq) == 0:
            seq.append('default')
        seq = set(seq)
        current = set(self._get_watchlist())
        add = seq - current
        rem = current - seq

        for x in add:
            self.watch(x)
        for x in rem:
            self.ignore(x)
        return

    watchlist = property(_get_watchlist, _set_watchlist)

    @property
    def tube(self):
        return self.list_tube_used()['tube']

    def close(self):
        self.poller.unregister(self._socket)
        self._socket.close()

    def fileno(self):
        return self._socket.fileno()


ServerConn = protohandler.protProvider(ServerConn)


class ThreadedConn(ServerConn):
    def __init__(self, *args, **kw):
        if 'pool' in kw:
            self.__pool = kw.pop('pool')
        super(ThreadedConn, self).__init__(*args, **kw)

    def __del__(self):
        self.__pool.release(self)
        super(ThreadedConn, self).__del__()


class ThreadedConnPool(object):
    '''
    ThreadedConnPool: A simple pool class for connection objects).
    This object will create a pool of size nconns. It does no thread wrangling,
    and no form of connection management, other than to get a unique connection
    to the thread that calls get.  In fact this could probably be simplified
    even more by subclassing Semaphore.
    '''

    import threading

    def __init__(self, nconns, server, port, job = False):
        self.__conns = list()
        self.__lock = self.threading.Lock()
        # threaded isn't defined here
        if threaded: conntype = ThreadedConn
        else: conntype = ServerConn
        for a in range(nconns):
            self.conns.append(conntype(server, port, job=job, pool=self))

        self.useme = self.threading.Semaphore(nconns)

    def get(self):
        self.useme.aquire()
        self.lock.acquire()
        ret = self.conns.pop(0)
        self.lock.release()

    def release(self, conn):
        self.lock.acquire()
        self.conns.append(conn)
        self.lock.release()
        self.useme.release()


try:
    from _libeventconn import LibeventConn
except ImportError:
    # most likely no libevent or pyevent. Thats fine, dont cause problems
    # for such cases
    pass

########NEW FILE########
__FILENAME__ = twisted_client
from twisted.protocols import basic
from twisted.internet import defer, protocol
from twisted.python import log
import protohandler

# Stolen from memcached protocol
try:
    from collections import deque
except ImportError:
    class deque(list):
        def popleft(self):
            return self.pop(0)
        def appendleft(self, item):
            self.insert(0, item)

class Command(object):
    """
    Wrap a client action into an object, that holds the values used in the
    protocol.

    @ivar _deferred: the L{Deferred} object that will be fired when the result
        arrives.
    @type _deferred: L{Deferred}

    @ivar command: name of the command sent to the server.
    @type command: C{str}
    """

    def __init__(self, command, handler, **kwargs):
        """
        Create a command.

        @param command: the name of the command.
        @type command: C{str}

        @param kwargs: this values will be stored as attributes of the object
            for future use
        """
        self.command = command
        self.handler = handler
        self._deferred = defer.Deferred()
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return "<Command: %s>" % self.command

    def success(self, value):
        """
        Shortcut method to fire the underlying deferred.
        """
        self._deferred.callback(value)


    def fail(self, error):
        """
        Make the underlying deferred fails.
        """
        self._deferred.errback(error)

class Beanstalk(basic.LineReceiver):

    def __init__(self):
        self._current = deque()

    def connectionMade(self):
        print "Connected!"
        self.setLineMode()

    def __getattr__(self, attr):
        def caller(*args, **kw):
            return self.__cmd(attr,
                *getattr(protohandler, 'process_%s' % attr)(*args, **kw))
        return caller

    def __cmd(self, command, full_command, handler):
        # Note here: the protohandler already inserts the \r\n, so
        # it would be an error to do self.sendline()
        self.transport.write(full_command)
        cmdObj = Command(command, handler)
        self._current.append(cmdObj)
        return cmdObj._deferred

    def lineReceived(self, line):
        """
        Receive line commands from the server.
        """
        pending = self._current.popleft()
        try:
            # this is a bit silly as twisted is so nice as to remove the
            # eol from the line, but protohandler.Handler needs it...
            # the reason its needed is that protohandler needs to work
            # in situations without twisted where things aren't so nice
            res = pending.handler(line + "\r\n")
        except Exception, e:
            pending.fail(e)
        else:
            if res is not None: # we have a result!
                pending.success(res)
            else: # there is more data, its a job or something...
                # push the pending command back on the stack
                self._current.appendleft(pending)
                self.setRawMode()

    def rawDataReceived(self, data):
        pending = self._current.popleft()
        if len(data) >= pending.handler.remaining:
            rem = data[pending.handler.remaining:]
            data = data[:pending.handler.remaining]
        else:
            rem = None

        try:
            res = pending.handler(data)
        except Exception, e:
            pending.fail(e)
            self.setLineMode(rem)
        if res:
            pending.success(res)
            self.setLineMode(rem)
        else:
            self._current.appendleft(pending)

class BeanstalkClientFactory(protocol.ClientFactory):
    def startedConnecting(self, connector):
        print 'Started to connect.'

    def buildProtocol(self, addr):
        print 'Connected.'
        return Beanstalk()

    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason

########NEW FILE########
__FILENAME__ = _libeventconn
import socket, sys
from collections import dequeue
import protohandler

class Command(object):
    def __init__(callback, command, handler):
        self.callback = callback
        self.comand = command
        self.handler = handler

class LibeventConn(object):
    '''LibeventConn -- Like other connection types in pybeanstalk, is
    intended to only handle the beanstalk related connections. This connection
    works much the same as ServerConn, and its initialization variables are
    the same.

    The connection object also has a few special properties:
    result_callback -- callable object, must take at least one argument,
                       a response (or job if job is set and the protocol
                       interaction returns a job), which will be the default
                       callback.
    result_callback_args -- a tuple which will be passed as *args to the
                            result_callback when it is called
    error_callback -- a callable that takes 3 arguments, which are the
                      results of a sys.exc_info() call

    To use the protocol, it works just like the ServerConn, but each function
    takes extra keyword options, for the callbacks, which override the connection
    defaults (but otherwise work the same) above.

    NOTE: I haven't included the convenience of the tube and watchlist
    properties in this connection type because I am still unsure of the best
    way to handle them.
    '''

    import event
    WAIT = 0
    IN_INTERACTION = 1
    MIN_TIME = .0000001

    def __init__(self, server, port, job = None):
        self.server = server
        self.port = port
        self._make_socket()
        self.job = None
        self.phase = self.WAIT

        self.interaction = None
        self.phase = self.WAIT
        self.result_callback = None
        self.result_callback_args = ()
        self.error_callback = None
        self.__current_Callbacks = None

    def _make_socket(self):
        self._socket = socket.socket(socket.AF_INET)
        self._socket.connect((self.server, self.port))
        #self._socket.setblocking(False)

    def fileno(self):
        return self._socket.fileno()

    def __write(self, idata):
        line = idata['line']
        if not 'sent' in idata:
            idata['sent'] = 0
        idata['sent'] += self._socket.send(line[idata['sent']:])
        if idata['sent'] == len(line):
            self.event.read(self._socket, self.__read, idata)
            return None
        else:
            return True

    def __read(self, idata):
        ec = idata['callbacks'][1]
        try:
            handler = idata['handler']
            recv = self._socket.recv(handler.remaining)
            resp = handler(recv)
            if resp:
                # we're done here, set up a timer for the minimum and call the
                # official callback.  Do this so that longer running jobs
                # dont do too much damage. Also in the case of e.g. stakless,
                # this wont interfere with the libevent loop as much
                self.phase = self.WAIT
                self.event.timeout(self.MIN_TIME, self.__callback, resp, idata)
                return None
            else:
                # more to read
                return True
        except:
            ec(*sys.exc_info())

    def __callback(self, response, idata):
        rc, ec, args = idata['callbacks']
        try: rc(response, *args)
        except: raise
        finally:
            self.__current_Callbacks = None
        return None

    def _do_interaction(self, idata):
        self.phase = self.IN_INTERACTION
        self.event.write(self._socket, self.__write, idata)
        return

    def _setup_callbacks(self, d):
        if 'result_callback' in d:
            rc = d.pop('result_callback')
            rca = d.pop('result_callback_args') \
                if 'result_callback_args' in d else tuple()
        else:
            rc = self.result_callback
            rca = self.result_callback_args

        if 'error_callback' in d:
            ec = d.pop('error_callback')
        else: ec = self.error_callback

        if not (rc and ec):
            raise ConnectionError('Callbacks missing')
        return (rc, ec, rca)

    def __getattr__(self, attr):
        def caller(callback, *args, **kw):
            cmd = Command(callback,
                *getattr(protohandler, 'process_%s' % (attr,))(*args, **kw))
            return self._do_interaction(idata)
        return caller


########NEW FILE########
__FILENAME__ = libevent_main
''' libevent_main.py
A simple example for using the LibeventConn connection type. This just pulls
jobs and deletes them, but shows how to set up callbacks and whatnot. A few
varibales for your tweaking pleasure are:
SERVER and PORT -- set these to your beanstalkd
PUT_ERROR -- Intentinally cause an error from the beanstalkd, by requesting
             delete of an already deleted job. Value bool
FIX_ERROR -- If an error is encounterd handle it well and fix it. Otherwise,
             print it and abort. Value bool.
'''

import beanstalk
import event

SERVER = '127.0.0.1'
PORT = 11300
# change this to False to die on an error.
# Its set up a bit hokey, but its a demo anyway
PUT_ERROR = False
FIX_ERROR = True

CONN = None
MRJ = None

def got_response(response, conn):
    global MRJ
    if 'jid' in response:
        if response['data'] == 'stop':
            print 'finishing'
            event.abort()
            return
        print 'got a response!', response
        MRJ = response
        dnum = response['jid'] if not PUT_ERROR else response['jid']-1
        conn.delete(dnum)
    else:
        print 'deleted'
        conn.reserve()

def got_error(eclass, e, tb):
    import traceback
    traceback.print_exception(eclass, e, tb)
    if FIX_ERROR:
        CONN.delete(MRJ['jid'], result_callback=got_response,
            result_callback_args = (CONN,))
        return
    print 'aborting now'
    event.abort()

def start(conn):
    print 'start called'
    conn.reserve()
    return

def main():
    global CONN
    # setup the connection
    myconn = beanstalk.serverconn.LibeventConn(SERVER, PORT)
    #setup callbacks
    myconn.result_callback_args = (myconn,)
    myconn.result_callback = got_response
    myconn.error_callback = got_error

    #setup the callchain
    start(myconn)
    CONN = myconn
    print 'dispatching'
    event.dispatch()

if __name__ == '__main__':
    event.init()
    main()

########NEW FILE########
__FILENAME__ = simple_clients
# stdlib imports
import sys
import time

# pybeanstalk imports
from beanstalk import serverconn
from beanstalk import job

def producer_main(connection):
    i = 0
    while True:
        data = 'This is data to be consumed (%s)!' % (i,)
        print data
        data = job.Job(data=data, conn=connection)
        data.Queue()
        time.sleep(1)
        i += 1;

def consumer_main(connection):
    while True:
        j = connection.reserve()
        print 'got job! job is: %s' % j.data
        j.Touch()
        j.Finish()

def main():
    try:
        print 'handling args'
        clienttype = sys.argv[1]
        server = sys.argv[2]
        try:
            port = int(sys.argv[3])
        except:
            port = 11300

        print 'setting up connection'
        connection = serverconn.ServerConn(server, port)
        connection.job = job.Job
        if clienttype == 'producer':
            print 'starting producer loop'
            producer_main(connection)
        elif clienttype == 'consumer':
            print 'starting consumer loop'
            consumer_main(connection)
        else:
            raise Exception('foo')
    except Exception, e:
        print "usage: example.py TYPE server [port]"
        print " TYPE is one of: [producer|consumer]"
        raise
        sys.exit(1)
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = twisted_consumer
#!/usr/bin/env python

import os
import sys
sys.path.append("..")
sys.path.append(os.path.join(sys.path[0], '..'))

from twisted.internet import reactor, protocol, defer, task

import beanstalk

def executor(bs, jobdata):
    print "Running job %s" % `jobdata`
    bs.touch(jobdata['jid'])
    bs.delete(jobdata['jid'])

def error_handler(e):
    print "Got an error", e

def executionGenerator(bs):
    while True:
        print "Waiting for a job..."
        yield bs.reserve().addCallback(lambda v: executor(bs, v)).addErrback(
            error_handler)

def worker(bs):
    bs.watch("myqueue")
    bs.ignore("default")

    coop = task.Cooperator()
    coop.coiterate(executionGenerator(bs))

d=protocol.ClientCreator(reactor,
    beanstalk.twisted_client.Beanstalk).connectTCP(sys.argv[1], 11300)
d.addCallback(worker)

reactor.run()


########NEW FILE########
__FILENAME__ = twisted_producer
#!/usr/bin/env python

import os
import sys
sys.path.append("..")
sys.path.append(os.path.join(sys.path[0], '..'))

from twisted.internet import reactor, protocol, defer, task

import beanstalk

def worker(bs):
    bs.use("myqueue")
    bs.put('Look!  A job!', 8192, 0, 300).addCallback(
        lambda x: sys.stdout.write("Queued job: %s\n" % `x`)).addCallback(
        lambda x: reactor.stop())

d=protocol.ClientCreator(reactor,
    beanstalk.twisted_client.Beanstalk).connectTCP(sys.argv[1], 11300)
d.addCallback(worker)

reactor.run()


########NEW FILE########
__FILENAME__ = config
import ConfigParser

class ConfigWrapper(object):
    def __init__(self, configfile, section):
        self.section = section
        self.config = ConfigParser.ConfigParser()
        self.config.read(configfile)
    def __getattr__(self, attr):
        return self.config.get(self.section, attr)

def get_config(section_name, configfile="tests.cfg"):
    return ConfigWrapper(configfile, section_name)

########NEW FILE########
__FILENAME__ = test_errors
import sys
sys.path.append('..')
from config import get_config
import nose.tools

config = get_config("ServerConn")

from beanstalk import errors

def test_checkError():
    def t_func(rstring, error):
        nose.tools.assert_raises(error, errors.checkError, rstring)

    errorlist = [(errors.OutOfMemory, 'OUT_OF_MEMORY'),
                 (errors.InternalError, 'INTERNAL_ERROR'),
                 (errors.Draining, 'DRAINING'),
                 (errors.BadFormat, 'BAD_FORMAT'),
                 (errors.UnknownCommand, 'UNKNOWN_COMMAND'),
                 (errors.ExpectedCrlf, 'EXPECTED_CRLF'),
                 (errors.JobTooBig, 'JOB_TOO_BIG'),
                 (errors.NotFound, 'NOT_FOUND'),
                 (errors.NotIgnored, 'NOT_IGNORED'),
                 (errors.DeadlineSoon, 'DEADLINE_SOON')]

    for error, rstring in errorlist:
        yield t_func, rstring, error

########NEW FILE########
__FILENAME__ = test_MultiServerConn
"""
MultiServerConn tests.

These tests are easiest run with nose, that's why they are free of
xUnit cruft ;)

There is a strong possibility of side effects from failing tests breaking
others.  Probably best to setup a new beanstalkd at each test.
"""

import os
import sys
import signal
import socket
import time
import random
import subprocess
import itertools

from nose.tools import with_setup, assert_raises
import nose

from beanstalk import multiserverconn
from beanstalk import errors
from beanstalk import job

from config import get_config


# created during setup
config = get_config("MultiServerConn")

processes = []
conn = None

def setup():
    global processes, conn, config
    output = "server started on %(ip)s:%(port)s with PID: %(pid)s"

    H = config.BEANSTALKD_HOSTS.split(';')
    C = int(config.BEANSTALKD_COUNT)
    P = int(config.BEANSTALKD_PORT_START)
    J = getattr(job, config.BEANSTALKD_JOB_CLASS, None)

    binloc = os.path.join(config.BPATH, config.BEANSTALKD)
    conn = multiserverconn.ServerPool([])

    for ip, port in itertools.izip_longest(H, xrange(P, P+C), fillvalue=H[0]):
        process = subprocess.Popen([binloc, "-l", str(ip), "-p", str(port)])
        processes.append(process)
        print output % { "ip" : ip, "port" : port, "pid" : process.pid }
        time.sleep(0.1)
        try:
            conn.add_server(ip, port, J)
        except Exception, e:
            processes.pop().kill()
            raise

def teardown():
    global processes
    output = "terminating beanstalkd with PID: %(pid)s"
    for process in processes:
        print output % {"pid" : process.pid}
        process.kill()

def _clean_up():
    """Cleans up from previous test by closing whatever connection was waiting
    and primes the connection for the next test

    - Resets the waiting flag
    - Disconnects and reconnects to the beanstalk queue server to clean out
      any pending requests.

    """
    for server in itertools.ifilter(lambda s: s.waiting, conn.servers):
        server.waiting = False
        server.close()
        server.connect()

    for server in conn.servers:
        assert not server.waiting


# Test helpers:
def _test_putter_and_reserver(payload, pri):
    """Returns a tuple consisting of the job and the reserved job.

    This will create a job, and get the reserved job from the queue, providing
    all sanity checking so we can D.R.Y. some stuff up.

    """
    # no point in checking preconditions here because we don't know what
    # server we're going to be looking at. 
    #
    # TODO: for sanity though, we should query all servers to check they're
    # empty.

    # create a job
    job_ = conn.put(payload, pri)
    put_id = job_['jid']

    print "created a job with id", put_id

    assert job_.Server.stats()['data']['current-jobs-ready'] == 1
    assert job_.Info['data']['state'] == 'ready'

    # reserve it
    res = conn.reserve()[0]
    # reserved here is a Job class
    print "reserved a job", res

    assert res['data'] == payload
    assert res['jid'] == put_id

    return (job_, res)


def _test_put_reserve_delete_a_job(payload, pri):

    job_, res = _test_putter_and_reserver(payload, pri)
    jstats = res.Info['data']

    assert jstats['pri'] == pri
    assert jstats['state'] == 'reserved'

    # delete it
    print 'about to delete'
    assert res.Finish()

    assert job_.Server.stats()['data']['current-jobs-ready'] == 0,\
            "job was not deleted"

    nose.tools.assert_raises(errors.NotFound, res.Server.stats_job, res['jid'])
    _clean_up()


def _test_put_reserve_release_a_job(payload, pri):

    job_, res = _test_putter_and_reserver(payload, pri)
    put_id = job_["jid"]

    # release it
    res.Return()
    assert res.Server.stats()['data']['current-jobs-ready'] == 1, "job was not released"
    assert job_.Info['data']['state'] == 'ready'

    # reserve again
    res = conn.reserve()[0]
    print "reserved a job", res

    assert res['data'] == payload
    assert res['jid'] == put_id

    # delete it
    res.Finish()
    assert job_.Server.stats()['data']['current-jobs-ready'] == 0, "job was not deleted"
    _clean_up()



# Test Cases:

def test_remove_server():
    """Test if remove_server works appropriately.

    Not going to test add_server because I already use it in setup()

    """
    global config

    H = config.BEANSTALKD_HOSTS.split(';')
    C = int(config.BEANSTALKD_COUNT)
    P = int(config.BEANSTALKD_PORT_START)
    J = getattr(job, config.BEANSTALKD_JOB_CLASS, None)

    assert conn.remove_server(H[0], P)

    # restore server..
    assert conn.add_server(H[0], P, J)

    _clean_up()

def test_ServerConn_can_put_reserve_delete_a_simple_job():
    _test_put_reserve_delete_a_job('abcdef', 0)

def test_ServerConn_can_put_reserve_delete_a_long_job():
    _test_put_reserve_delete_a_job('abc'*100, 0)

def test_ServerConn_can_put_reserve_delete_a_nasty_job():
    _test_put_reserve_delete_a_job('abc\r\nabc', 0)

def test_ServerConn_can_put_reserve_release_a_simple_job():
    _test_put_reserve_release_a_job('abcdef', 0)


def test_ServerConn_can_bury_and_kick_a_job():
    # check preconditions
    assert conn.stats()['data']['current-jobs-ready'] == 0, "The server is not empty "\
           "of jobs so test behaviour cannot be guaranteed.  Bailing out."

    # put and reserve the job
    job_ = conn.put('simple job')
    res = conn.reserve()[0]
    assert job_['jid'] == res['jid']

    # bury it
    print 'burying'
    bury = res.Bury()
    assert res.Server.stats()['data']['current-jobs-buried'] == 1, \
        "job was not buried"
    assert job_.Info['data']['state'] == 'buried'

    # kick it back into the queue
    print 'kicking'
    kick = res.Server.kick(1)
    assert res.Server.stats()['data']['current-jobs-ready'] == 1, "job was not kicked"

    # Need to reget the job, then delete it
    # WOAH: SIDE EFFECT OF __DEL__ IMPLEMENTATION
    # if the statement below was:
    #     job_ = job_.Server.reserve()
    # the GC would've ate up job_ and SERVER would return NOT_FOUND!!
    # be very careful!!
    resurrected = conn.reserve()[0]
    #while we are here, a sanity check to make sure the job is re-gettable
    #
    #these are dicts.
    #
    assert resurrected == res,\
                'second job get is different from original get'

    jstats = resurrected.Info['data']
    assert jstats['buries'] == 1
    assert jstats['kicks'] == 1

    delete = res.Finish()

    assert job_.Server.stats()['data']['current-jobs-ready'] == 0, "job was not deleted"
    _clean_up()


def test_ServerConn_fails_to_connect_with_a_reasonable_exception():
    # it may be nicer not to throw a socket error here?
    try:
        H = config.BEANSTALKD_HOSTS.split(';')
        C = int(config.BEANSTALKD_COUNT)
        P = int(config.BEANSTALKD_PORT_START)
        J = getattr(job, config.BEANSTALKD_JOB_CLASS, None)
        #add a new server with a port that is most likely not open
        multiserverconn.ServerPool([(H[0], P+C+1, J)])
    except socket.error, reason:
        pass

def test_tube_operations():
    # first make sure its watching default
    # this check is useless for our purposes, but will work fine since 
    # it will check all servers

    # test clone here
    assert conn.watchlist == ['default']

    # a dummy job for when we test a different tube...
    job_ = conn.put('dummy')
    dummy_id = job_['jid']

    testlist = ['foo','bar','baz']
    conn.watchlist = testlist

    # ordering may not be guaranteed, sets dont care!
    assert set(conn.watchlist) == set(testlist)

    # changes a bit since you're distributed..
    # returns a dict
    tubes = conn.list_tubes_watched()
    for server, tubes_watched in tubes.iteritems():
        # might as well assert that the server shoulnd't be waiting
        assert not server.waiting
        # check to make sur ethat the set is equal to the test list
        assert set(tubes_watched['data']) == set(testlist)

    #use test
    assert set(conn.tubes) == set(['default'])

    conn.use('bar')
    assert set(conn.tubes) == set(['bar'])

    newjob_ = conn.put('this is data', pri=100)
    jid = newjob_['jid']
    assert newjob_.Server.stats_tube('bar')['data']['current-jobs-ready'] == 1

    #because we're randomly choosing between servers, we shouldn't expect that
    #the current-jobs-ready will be the same, since they're on distributed
    #nodes
    print conn.stats()
    assert conn.stats()['data']['current-jobs-ready'] == 2,\
            "Was expecting %s, got %s" % (expecting,
                    newjob_.Server.stats()['data']['current-jobs-ready'])

    # because the protocol blocks when we try to reserve a job, theres not a
    # good way to test that it does not return when the watchlist doesn't
    # include this job, untill threading/async is better anyway
    # out of orderness is a good test tho... :)

    job = newjob_.Server.reserve()
    assert job['jid'] == jid, 'got wrong job from tube bar'
    job.Return()

    conn.watchlist = ['default']
    #job from default queue
    j_from_dq = job_.Server.reserve()
    assert j_from_dq['jid'] == dummy_id, 'got wrong job from default'
    print 'about to delete'
    j_from_dq.Finish()

    conn.watchlist = testlist
    j = newjob_.Server.reserve()
    print 'about to delete again'
    j.Finish()
    _clean_up()


def test_reserve_timeout_works():
    assert conn.stats()['data']['current-jobs-ready'] == 0, "The server is not empty "\
           "of jobs so test behaviour cannot be guaranteed.  Bailing out."
    # essentially an instant poll. This should just timeout!
    # remember that reserve with timeout is broadcasted to all servers
    # so all servers need to return timeout
    results = conn.reserve_with_timeout(0)
    for server in results:
        assert server['state'] == 'timeout'
    _clean_up()

def test_reserve_deadline_soon():

    # Put a short running job
    job_ = conn.put('foobarbaz job!', ttr=2)
    jid = job_["jid"]

    # Reserve it, so we can setup conditions to get a DeadlineSoon error
    res = conn.reserve()[0]
    assert jid == res['jid'], "Didn't get test job, something funky is happening."
    # a bit of padding to make sure that deadline soon is encountered
    time.sleep(1)
    assert_raises(errors.DeadlineSoon, conn.reserve), "Job should have warned "\
                  "of impending deadline. It did not. This is a problem!"

    job_.Finish()
    x = job_.Server.stats()
    assert x['state'] == 'ok', "Didn't delete the job right. This could break future tests"
    _clean_up()


########NEW FILE########
__FILENAME__ = test_Proto
import sys
print >>sys.stderr,sys.version
sys.path.append('..')
from nose import with_setup, tools
from beanstalk import protohandler
from beanstalk import errors


prototest_info = [
    [
        ('process_put', ('test_data', 0, 0, 10)),
        "put 0 0 10 %s\r\ntest_data\r\n" % (len('test_data'),),
        [
            ('INSERTED 3\r\n', {'state':'ok','jid':3}),
            ('BURIED 3\r\n', {'state':'buried','jid':3})
        ]
    ],
    [
        ('process_use', ('bar',)),
        'use bar\r\n',
        [
            ('USING bar\r\n', {'state':'ok', 'tube':'bar'})
        ]
    ],
    [
        ('process_reserve', ()),
        'reserve\r\n',
        [
            ('RESERVED 12 5\r\nabcde\r\n',{'state':'ok', 'bytes': 5, 'jid':12,
                'data':'abcde'})
        ]
    ],
    [
        ('process_reserve_with_timeout', (4,)),
        'reserve-with-timeout 4\r\n',
        [
            ('RESERVED 12 5\r\nabcde\r\n',{'state':'ok', 'bytes': 5, 'jid':12,
                'data':'abcde'}),
            ('TIMED_OUT\r\n', {'state':'timeout'})
        ]
    ],
    [
        ('process_delete', (12,)),
        'delete 12\r\n',
        [
            ('DELETED\r\n',{'state':'ok'})
        ]
    ],
    [
        ('process_touch', (185,)),
        'touch 185\r\n',
        [
            ('TOUCHED\r\n',{'state':'ok'})
        ]
    ],
    [
        ('process_release', (33,22,17)),
        'release 33 22 17\r\n',
        [
            ('RELEASED\r\n',{'state':'ok'}),
            ('BURIED\r\n',{'state':'buried'})
        ]
    ],
    [
        ('process_bury', (29, 21)),
        'bury 29 21\r\n',
        [
            ('BURIED\r\n',{'state':'ok'})
        ]
    ],
    [
        ('process_watch', ('supertube',)),
        'watch supertube\r\n',
        [
            ('WATCHING 5\r\n',{'state':'ok','count': 5})
        ]
    ],
    [
        ('process_ignore', ('supertube',)),
        'ignore supertube\r\n',
        [
            ('WATCHING 3\r\n', {'state':'ok', 'count':3})
            #('NOT_IGNORED',{'state':'buried'})
        ]
    ],
    [
        ('process_peek', (39,)),
        'peek 39\r\n',
        [
            ("FOUND 39 10\r\nabcdefghij\r\n", {'state':'ok', 'jid':39,
                'bytes':10, 'data':'abcdefghij'})
        ]
    ],
    [
        ('process_peek_ready', ()),
        'peek-ready\r\n',
        [
            ("FOUND 9 10\r\nabcdefghij\r\n",{'state':'ok', 'jid':9, 'bytes':10,
                'data':'abcdefghij'})
        ]
    ],
    [
        ('process_peek_delayed', ()),
        'peek-delayed\r\n',
        [
            ("FOUND 9 10\r\nabcdefghij\r\n",{'state':'ok', 'jid':9, 'bytes':10,
                'data':'abcdefghij'})
        ]
    ],
    [
        ('process_peek_buried', ()),
        'peek-buried\r\n',
        [
            ("FOUND 9 10\r\nabcdefghij\r\n",{'state':'ok', 'jid':9, 'bytes':10,
                'data':'abcdefghij'})
        ]
    ],
    [
        ('process_kick', (200,)),
        'kick 200\r\n',
        [
            ("KICKED 59\r\n",{'state':'ok', 'count':59})
        ]
    ],
    [
        ('process_stats', ()),
        'stats\r\n',
        [
            ('OK 15\r\n---\ntest: good\n\r\n', {'state':'ok', 'bytes':15,
                'data':{'test':'good'}})
        ]
    ],
    [
        ('process_stats_tube', ('barbaz',)),
        'stats-tube barbaz\r\n',
        [
            ('OK 15\r\n---\ntest: good\n\r\n',{'state':'ok', 'bytes':15,
                            'data':{'test':'good'}})

        ]
    ],
    [
        ('process_stats_job', (19,)),
        'stats-job 19\r\n',
        [
            ('OK 15\r\n---\ntest: good\n\r\n',{'state':'ok', 'bytes':15,
                'data':{'test':'good'}})

        ]
    ],
    [
        ('process_list_tubes', ()),
        'list-tubes\r\n',
        [
            ('OK 20\r\n---\n- default\n- foo\n\r\n', {'state':'ok', 'bytes':20,
                'data':['default','foo']})
        ]
    ],
    [
        ('process_list_tube_used',()),
        'list-tube-used\r\n',
        [
            ('USING bar\r\n', {'state':'ok', 'tube':'bar'})
        ]
    ],
    [
        ('process_list_tubes_watched', ()),
        'list-tubes-watched\r\n',
        [
            ('OK 20\r\n---\n- default\n- foo\n\r\n',{'state':'ok', 'bytes':20,
                'data':['default','foo']})

        ]
    ]
]




def check_line(l1, l2):
    assert l1 == l2, '%s %s' % (l1, l2)

def check_handler(handler, response, cv):
    l = 0
    while True:
        r = len(response)
        l = handler.remaining if handler.remaining > r else r
        y = handler(response[:l])
        response = response[l:]
        if y:
            assert y == cv
            break
    return

def test_interactions():
    for test in prototest_info:
        callinfo, commandline, responseinfo = test
        func = getattr(protohandler, callinfo[0])
        args = callinfo[1]
        for response, resultcomp in responseinfo:
            line, handler = func(*args)
            yield check_line, line, commandline
            yield check_handler, handler, response, resultcomp

def test_put_extra():
    #check that the put raises the right error on big jobs...
    tools.assert_raises(errors.JobTooBig, protohandler.process_put,'a' * (2**16),0,0,0)
    #check that it handles different job sizes correctly (not just default)
    oldmax = protohandler.MAX_JOB_SIZE
    protohandler.MAX_JOB_SIZE = 10
    tools.assert_raises(errors.JobTooBig, protohandler.process_put,'a' * 11,0,0,0)
    protohandler.MAX_JOB_SIZE = oldmax



########NEW FILE########
__FILENAME__ = test_ServerConn
"""
ServerConn tests.

These tests are easiest run with nose, that's why they are free of
xUnit cruft ;)

There is a strong possibility of side effects from failing tests breaking
others.  Probably best to setup a new beanstalkd at each test.
"""

import os
import signal
import socket
import time

from nose.tools import with_setup, assert_raises
import nose

from beanstalk import serverconn
from beanstalk import errors
from config import get_config

config = get_config("ServerConn")

# created during setup
server_pid = None
conn = None


def setup():
    global server_pid, conn, config
    server_pid = os.spawnl(os.P_NOWAIT,
                            os.path.join(config.BPATH,config.BEANSTALKD),
                            os.path.join(config.BPATH,config.BEANSTALKD),
                            '-l', config.BEANSTALKD_HOST,
                            '-p', config.BEANSTALKD_PORT
                            )
    print "server started at process", server_pid
    time.sleep(0.1)
    conn = serverconn.ServerConn(config.BEANSTALKD_HOST, int(config.BEANSTALKD_PORT))

def teardown():
    print "terminating beanstalkd at", server_pid
    os.kill(server_pid, signal.SIGTERM)


# Test helpers:

def _test_put_reserve_delete_a_job(payload, pri):
    # check preconditions
    assert conn.stats()['data']['current-jobs-ready'] == 0, "The server is not empty "\
           "of jobs so test behaviour cannot be guaranteed.  Bailing out."

    # create a job
    put_id = conn.put(payload, pri)['jid']
    print "created a job with id", put_id

    assert conn.stats()['data']['current-jobs-ready'] == 1
    assert conn.stats_job(put_id)['data']['state'] == 'ready'

    # reserve it
    res = conn.reserve()
    print "reserved a job", res

    assert res['data'] == payload
    assert res['jid'] == put_id
    jstats = conn.stats_job(res['jid'])['data']
    assert jstats['pri'] == pri
    assert jstats['state'] == 'reserved'

    # delete it
    print 'about to delete'
    conn.delete(res['jid'])
    assert conn.stats()['data']['current-jobs-ready'] == 0, "job was not deleted"
    nose.tools.assert_raises(errors.NotFound, conn.stats_job, res['jid'])


def _test_put_reserve_release_a_job(payload, pri):
    # check preconditions
    assert conn.stats()['data']['current-jobs-ready'] == 0, "The server is not empty "\
           "of jobs so test behaviour cannot be guaranteed.  Bailing out."

    # create a job
    put_id = conn.put(payload, pri)['jid']
    print "created a job with id", put_id

    assert conn.stats()['data']['current-jobs-ready'] == 1

    # reserve it
    res = conn.reserve()
    print "reserved a job", res

    assert res['data'] == payload
    assert res['jid'] == put_id

    # release it
    conn.release(res['jid'])
    assert conn.stats()['data']['current-jobs-ready'] == 1, "job was not released"
    assert conn.stats_job(put_id)['data']['state'] == 'ready'

    # reserve again
    res = conn.reserve()
    print "reserved a job", res

    assert res['data'] == payload
    assert res['jid'] == put_id

    # delete it
    conn.delete(res['jid'])
    assert conn.stats()['data']['current-jobs-ready'] == 0, "job was not deleted"


# Test Cases:

def test_ServerConn_can_put_reserve_delete_a_simple_job():
    _test_put_reserve_delete_a_job('abcdef', 0)

def test_ServerConn_can_put_reserve_delete_a_long_job():
    _test_put_reserve_delete_a_job('abc'*100, 0)

def test_ServerConn_can_put_reserve_delete_a_nasty_job():
    _test_put_reserve_delete_a_job('abc\r\nabc', 0)

def test_ServerConn_can_put_reserve_release_a_simple_job():
    _test_put_reserve_release_a_job('abcdef', 0)


def test_ServerConn_can_bury_and_kick_a_job():
    # check preconditions
    assert conn.stats()['data']['current-jobs-ready'] == 0, "The server is not empty "\
           "of jobs so test behaviour cannot be guaranteed.  Bailing out."

    # put and reserve the job
    put = conn.put('simple job')
    res = conn.reserve()
    assert put['jid'] == res['jid']

    # bury it
    print 'burying'
    bury = conn.bury(res['jid'])
    assert conn.stats()['data']['current-jobs-buried'] == 1, \
        "job was not buried"
    assert conn.stats_job(put['jid'])['data']['state'] == 'buried'

    # kick it back into the queue
    print 'kicking'
    kick = conn.kick(1)
    assert conn.stats()['data']['current-jobs-ready'] == 1, "job was not kicked"

    # Need to reget the job, then delete it
    job = conn.reserve()
    #while we are here, a sanity check to make sure the job is re-gettable
    assert job == res, 'second job get is different from origninal get'
    jstats = conn.stats_job(job['jid'])['data']
    assert jstats['buries'] == 1
    assert jstats['kicks'] == 1

    delete = conn.delete(res['jid'])

    assert conn.stats()['data']['current-jobs-ready'] == 0, "job was not deleted"


def test_ServerConn_fails_to_connect_with_a_reasonable_exception():
    # it may be nicer not to throw a socket error here?
    try:
        serverconn.ServerConn(config.BEANSTALKD_HOST,
                              int(config.BEANSTALKD_PORT)+1)
    except socket.error, reason:
        pass

def test_tube_operations():
    assert conn.stats()['data']['current-jobs-ready'] == 0, "The server is not empty "\
           "of jobs so test behaviour cannot be guaranteed.  Bailing out."
    # first make sure its watching default
    assert conn.watchlist == ['default']

    testlist = ['foo','bar','baz']
    conn.watchlist = testlist
    # ordering may not be garunteed, sets dont care!
    assert set(conn.watchlist) == set(testlist)
    assert set(conn.list_tubes_watched()['data']) == set(testlist)

    #use test
    assert conn.tube == 'default'
    # a dummy job for when we test a different tube...
    dummy_id = conn.put('dummy')['jid']

    conn.use('bar')
    assert conn.tube == 'bar'

    jid = conn.put('this is data', pri=100)['jid']
    assert conn.stats_tube('bar')['data']['current-jobs-ready'] == 1

    assert conn.stats()['data']['current-jobs-ready'] == 2
    # because the protocol blocks when we try to reserve a job, theres not a
    # good way to test that it does not return when the watchlist doesn't
    # include this job, untill threading/async is better anyway
    # out of orderness is a good test tho... :)

    job = conn.reserve()
    assert job['jid'] == jid, 'got wrong job from tube bar'
    conn.release(jid)

    conn.watchlist = ['default']
    job = conn.reserve()
    assert job['jid'] == dummy_id, 'got wrong job from default'
    print 'about to delete'
    conn.delete(dummy_id)

    conn.watchlist = testlist
    conn.reserve()
    print 'about to delete again'
    conn.delete(jid)

def test_reserve_timeout_works():
    assert conn.stats()['data']['current-jobs-ready'] == 0, "The server is not empty "\
           "of jobs so test behaviour cannot be guaranteed.  Bailing out."
    # essentially an instant poll. This should just timeout!
    x = conn.reserve_with_timeout(0)
    assert x['state'] == 'timeout'

def test_reserve_deadline_soon():
    assert conn.stats()['data']['current-jobs-ready'] == 0, "The server is not empty "\
           "of jobs so test behaviour cannot be guaranteed.  Bailing out."
    # Put a short running job
    jid = conn.put('foobarbaz job!', ttr=1)['jid']
    # Reserve it, so we can setup conditions to get a DeadlineSoon error
    job = conn.reserve()
    assert jid == job['jid'], "Didn't get test job, something funky is happening."
    # a bit of padding to make sure that deadline soon is encountered
    time.sleep(.2)
    assert_raises(errors.DeadlineSoon, conn.reserve), "Job should have warned "\
                  "of impending deadline. It did not. This is a problem!"
    x = conn.delete(jid)
    assert x['state'] == 'ok', "Didn't delete the job right. This could break future tests"


########NEW FILE########
