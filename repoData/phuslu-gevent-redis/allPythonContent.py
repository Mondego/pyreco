__FILENAME__ = benchmark
#!/usr/bin/env python

import time

CONNECTIONS = 10
INCR_NUMBER = 100

def test_redispy():
    import threading, redis
    import gevent.monkey
    gevent.monkey.patch_all()
    redis_client = redis.Redis()
    redis_client.delete('test')
    del redis_client
    time_begin = time.time()
    print 'test_redispy begin', time_begin
    def worker():
        redis_client = redis.Redis()
        for i in xrange(INCR_NUMBER):
            redis_client.lpush('test', i)
            redis_client.lrange('test', 0, -1)
    jobs = [threading.Thread(target=worker) for i in xrange(CONNECTIONS)]
    for job in jobs:
        job.start()
    for job in jobs:
        job.join()
    time_end = time.time()
    print 'test_redispy end', time_end
    print 'test_redispy total', time_end - time_begin

def test_geventredis():
    import gevent, geventredis
    redis_client = geventredis.connect()
    redis_client.delete('test')
    del redis_client
    time_begin = time.time()
    print 'test_geventredis begin', time_begin
    def worker():
        redis_client = geventredis.connect()
        for i in xrange(INCR_NUMBER):
            redis_client.lpush('test', i)
            redis_client.lrange('test', 0, -1)
    jobs = [gevent.spawn(worker) for i in xrange(CONNECTIONS)]
    gevent.joinall(jobs)
    time_end = time.time()
    print 'test_geventredis end', time_end
    print 'test_geventredis total', time_end - time_begin

def test():
    print '-----------------------------'
    test_geventredis()
    print '-----------------------------'
    test_redispy()
    print '-----------------------------'

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = core
from cStringIO import StringIO
from errno import EINTR
from gevent.socket import socket, error
from gevent import coros, select, spawn

class RedisError(Exception):
    pass

class RedisSocket(socket):

    def __init__(self, *args, **kwargs):
        socket.__init__(self, *args, **kwargs)
        self._rbuf = StringIO()
        self._semaphore = coros.Semaphore()
        spawn( self._drain )

    def _read(self, size):
        return self.recv(size)
    
    def _readline(self):
        '''Read the receive buffer until we find \n, return it all'''
        ret = []
        while True:
            ret.append( self.recv(1) )
            if ret[-1] == '\n':
                break
        return ''.join( ret )
        
    def _drain(self):
        '''Keep the socket clear when not expecting any callbacks'''
        while True:
            ready, w, x = select.select( [self], [], [] )
            if not self._semaphore.locked():
                # We're here if there's data in the receive buffer but no one's reading
                junk = self.recv(1)
            else:
                # If someone else is reading, hang out until they're done
                self._semaphore.wait()
    

    ## Define the parsers for various messages we may receive
    # +(message)
    def _response_single_line(self, response):
        return response[1:-2]
        
    # -(message)
    def _response_error(self, response):
        raise RedisError(response[1:-2])
    
    # :nn
    def _response_integer(self, response):
        return int(response[1:])
    
    # $nn            length.  -1 = Null
    # (binary data)
    def _response_bulk(self, response):
        number = int(response[1:])
        if number == -1:
            return None
        else:
            return self._read(number+2)[:-2]

    # *nn            length.  -1 = Null
    # (any of the above messages)
    def _response_multi_bulk(self, response):
        number = int(response[1:])
        if number == -1:
            return None
        else:
            return [ self._read_response() for i in xrange(number) ]

    ## Create a dict to parse each message
    _response_dict = {
        '+': _response_single_line,
        '-': _response_error,
        ':': _response_integer,
        '$': _response_bulk,
        '*': _response_multi_bulk,
        }
    
    def _read_response(self):
        response = self._readline()
        try:
            return self._response_dict[ response[0] ]( self, response )
        except IndexError:
            raise RedisError('Did not understand response: %s' % response)
    

    def _execute_command(self, *args):
        """Executes a redis command and return a result"""
        data = '*%d\r\n' % len(args) + ''.join(['$%d\r\n%s\r\n' % (len(str(x)), x) for x in args])
        self._semaphore.acquire()
        self.send(data)
        try:
            response = self._read_response()
        finally:
            self._semaphore.release()
        return response

    def _execute_yield_command(self, *args, **kwargs):
        """Executes a redis command and yield multiple results"""
        data = '*%d\r\n' % len(args) + ''.join(['$%d\r\n%s\r\n' % (len(str(x)), x) for x in args])
        try:
            cancel = kwargs['cancel']
        except:
            cancel = None
        self._semaphore.acquire()
        self.send(data)
        try:
            while True:
                yield self._read_response()
        finally:
            if cancel:
                self.send( '%s\r\n' % cancel )
                self._read_response()
            self._semaphore.release()


########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

import sys, os, re, time
import geventredis, gevent

def test():
    ## Not checked:
    # shutdown
    # expire
    # expireat
    # slaveof
    # config_set
    # bgwriteaof
    # move
    # setrange
    # watch
    # unwatch
    # No list commands
    # No set commands
    # No sorted set commands
    # publish/subscribe/monitor commands
    
    ## Not really verified:
    # setex
    # persist
    # info
    # save
    # config_get
    # dbsize
    # ttl
    

    reply = raw_input("Warning:  This test will flush any data out of the localhost Redis server!  Type OK:  ")
    if reply.upper() != 'OK':
        print("Not OK?  Sorry, I can't test.")
        return
    redis_client = geventredis.connect()
    x =  redis_client.info()
    for msg in redis_client.subscribe('my chan'):
        print msg
        break
        
    print( "save: %s" % redis_client.save() )
    print( "bgsave: %s" % redis_client.bgsave() )
    x = redis_client.config_get()
    x = redis_client.dbsize()
    print( "set: %s" % redis_client.set('foo', 'bar') )
    gevent.sleep(0.1)
    ret = redis_client.get('foo')
    if ret != 'bar':
        raise ValueError('Failed to get or set.  Expected "bar" but got %s' % ret)

    print( "flushall: %s" % redis_client.flushall() )
    gevent.sleep(0.1)
    #imperfect check.  Should switch DB to see if that was effected.
    if None != redis_client.get('foo'):
        raise ValueError('Flush failed')
    
    x = redis_client.set('foo', 'bar')
    print( "flushdb: %s" % redis_client.flushdb() )
    gevent.sleep(0.1)
    if None != redis_client.get('foo'):
        raise ValueError('FlushDB failed')
    
    print( "lastsave: %s" % redis_client.lastsave() )
    print( "ping: %s" % redis_client.ping() )
    print( "append: %s" % redis_client.append('foo', 'bar') )
    x = redis_client.append('foo', '2bar')
    gevent.sleep(0.1)
    if 'bar2bar' != redis_client.get('foo'):
        raise ValueError('append failed')
    
    if 1 != redis_client.incr('n'):
        raise ValueError('incr failed')
    if -1 != redis_client.decr('-n'):
        raise ValueError('decr failed')
    gevent.sleep(0.1)

    if redis_client.exists('nope') or not redis_client.exists('n'):
        raise ValueError('exists failed')
    
    print( "setbit: %s" % redis_client.setbit('bool', 1, False) )
    x = redis_client.setbit('bool', 2, True)
    gevent.sleep(0.1)
    if redis_client.getbit('bool', 1) or not redis_client.getbit('bool', 2):
        raise ValueError('setbit or getbit failed')
        
    x = redis_client.set('foo', 'bar')
    ret = redis_client.getset('foo', 'newbar')
    if ret != 'bar':
        raise ValueError('getset failed.  Expected "bar", but %s' % ret)
    
    ret = redis_client.getset('foo', 'bar') 
    if ret != 'newbar':
        raise ValueError('getset failed.  Expected "newbar", got %s' % ret)
        
    x = redis_client.keys()
    x = redis_client.mget('n')
    print( "mset: %s" % redis_client.mset({'n':'5', 'o':'6'}) )
    if '6' != redis_client.get('o'):
        raise ValueError('mset failed')
    
    print( "msetnx: %s" % redis_client.msetnx({'o':'7', 'p':'8'}) )
    ret = redis_client.get('o')
    if '7' == ret:
        raise ValueError('msetnx failed.  Expected "6" but got %s' % ret)
    ret = redis_client.get('p')
    if ret:
        raise ValueError('msetnx failed.  Expected None but got %s' % ret)
    
    print( "setex: %s" % redis_client.setex('o', 'newval', 1) )
    print( "persist: %s" % redis_client.persist('o') )
    print( "randomkey: %s" % redis_client.randomkey() )
    print( "rename: %s" % redis_client.rename('foo', 'newfoo') )
    if not redis_client.get('newfoo'):
        raise ValueError('rename failed')
    
    x = redis_client.set('newfoo', 'newbar')
    x = redis_client.set('foo', 'bar')
    print( "renamex: %s" % redis_client.renamenx('foo', 'newfoo') )
    if 'bar' == redis_client.get('newfoo'):
        raise ValueError('renamenx failed')
        
    redis_client.flushdb()
    print( "setnx: %s" % redis_client.setnx('foo', 'bar') )
    redis_client.setnx('foo', 'oops')
    if 'bar' != redis_client.get('foo'):
        raise ValuError('setnx failed')
        
    if 3 != redis_client.strlen('foo'):
        raise ValueError('strlen failed')
        
    if 'ar' != redis_client.substr('foo', 1):
        raise ValueError('substr failed')
    if 'ba' != redis_client.substr('foo', 0, 1):
        raise ValueError('substr failed')
        
    print( "ttl: %s" % redis_client.ttl('foo') )
    
    ret =  redis_client.type('foo')
    if 'string' != ret:
        raise ValueError('type failed.  Expected "string" got %s'%ret)
        
    ## Skip a lot
    
    ## Hash commands
    print( "hset: %s" % redis_client.hset('hoo', 'foo', 'bar') )
    if 'bar' != redis_client.hget('hoo', 'foo'):
        raise ValueError('hset/hget failed')
        
    if ['foo'] != redis_client.hkeys('hoo'):
        raise ValueError('hkeys failed')
    if not redis_client.hexists('hoo', 'foo'):
        raise ValueError('hexists failed')
        
    if 1 != redis_client.hlen('hoo'):
        raise ValueError('hlen failed')
        
    print( "hdel: %s" % redis_client.hdel('hoo', 'foo') )
    if 0 != redis_client.hlen('hoo'):
        raise ValueError('hdel or hlen failed')
        
    print( "hmset: %s" % redis_client.hmset('hoo', {'foo':'bar', 'foo2':'bar2'}) )
    print( "hsetnx: %s" % redis_client.hsetnx('hoo', 'foo', 'oops') )
    r = redis_client.hmget('hoo', ['foo', 'foo2', 'foo3'])
    if r != ['bar', 'bar2', None]:
        raise ValueError('hmset, hsetnx or hmget failed.  Expected ["bar", "bar2", None] but got %s' % r)
    
    x = redis_client.hset('hoo2', 'hoo2foo', 'hoo2bar')
    if ['hoo2bar'] != redis_client.hvals('hoo2'):
        raise ValueError('hvals failed')
    
    # try saving data with embedded \r\n
    print("set with tough data: %s" % redis_client.set('foo', 'bar\r\nbar') )
    ret = redis_client.get('foo')
    if ret != 'bar\r\nbar':
        raise ValueError('set/get failed with embedded termination')
    
    # try to break with spurious data
    print("\ntest spurious data...")
    try:
        print("sending 'bad command!'")
        ret = redis_client._execute_command('bad command!')
    except geventredis.RedisError as e:
        print("correctly caught bad command: %s" % e)
    else:
        raise ValueError('failed to catch bad command. Excpeted RedisError exception, got %s', ret)
        
    redis_client.send('PING\r\n')
    gevent.sleep(0.1)
    print( "set: %s" % redis_client.set('foo', 'bar') )
    ret = redis_client.get('foo')
    if ret != 'bar':
        raise ValueError('get or set failed with spurious data.')
    
    print( "\nflushing all test data: %s" % redis_client.flushall() )

    
    print "\nAll tests passed."

if __name__ == '__main__':
    test()

########NEW FILE########
