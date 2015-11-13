__FILENAME__ = handlers
import logging
import redis
import simplejson as json


class RedisFormatter(logging.Formatter):
    def format(self, record):
        """
        JSON-encode a record for serializing through redis.

        Convert date to iso format, and stringify any exceptions.
        """
        data = record._raw.copy()

        # serialize the datetime date as utc string
        data['time'] = data['time'].isoformat()

        # stringify exception data
        if data.get('traceback'):
            data['traceback'] = self.formatException(data['traceback'])

        return json.dumps(data)


class RedisHandler(logging.Handler):
    """
    Publish messages to redis channel.

    As a convenience, the classmethod to() can be used as a
    constructor, just as in Andrei Savu's mongodb-log handler.
    """

    @classmethod
    def to(cklass, channel, host='localhost', port=6379, password=None, level=logging.NOTSET):
        return cklass(channel, redis.Redis(host=host, port=port, password=password), level=level)

    def __init__(self, channel, redis_client, level=logging.NOTSET):
        """
        Create a new logger for the given channel and redis_client.
        """
        logging.Handler.__init__(self, level)
        self.channel = channel
        self.redis_client = redis_client
        self.formatter = RedisFormatter()

    def emit(self, record):
        """
        Publish record to redis logging channel
        """
        try:
            self.redis_client.publish(self.channel, self.format(record))
        except redis.RedisError:
            pass


class RedisListHandler(logging.Handler):
    """
    Publish messages to redis a redis list.

    As a convenience, the classmethod to() can be used as a
    constructor, just as in Andrei Savu's mongodb-log handler.

    If max_messages is set, trim the list to this many items.
    """

    @classmethod
    def to(cklass, key, max_messages=None, host='localhost', port=6379, level=logging.NOTSET):
        return cklass(key, max_messages, redis.Redis(host=host, port=port), level=level)

    def __init__(self, key, max_messages, redis_client, level=logging.NOTSET):
        """
        Create a new logger for the given key and redis_client.
        """
        logging.Handler.__init__(self, level)
        self.key = key
        self.redis_client = redis_client
        self.formatter = RedisFormatter()
        self.max_messages = max_messages

    def emit(self, record):
        """
        Publish record to redis logging list
        """
        try:
            if self.max_messages:
                p = self.redis_client.pipeline()
                p.rpush(self.key, self.format(record))
                p.ltrim(self.key, -self.max_messages, -1)
                p.execute()
            else:
                self.redis_client.rpush(self.key, self.format(record))
        except redis.RedisError:
            pass

########NEW FILE########
__FILENAME__ = logger
import socket
import getpass
import datetime
import inspect
import logging

def levelAsString(level):
    return {logging.DEBUG: 'debug',
            logging.INFO: 'info',
            logging.WARNING: 'warning', 
            logging.ERROR: 'error', 
            logging.CRITICAL: 'critical', 
            logging.FATAL: 'fatal'}.get(level, 'unknown')

def _getCallingContext():
    """
    Utility function for the RedisLogRecord.

    Returns the module, function, and lineno of the function 
    that called the logger.  
 
    We look way up in the stack.  The stack at this point is:
    [0] logger.py _getCallingContext (hey, that's me!)
    [1] logger.py __init__
    [2] logger.py makeRecord
    [3] _log
    [4] <logging method>
    [5] caller of logging method
    """
    frames = inspect.stack()

    if len(frames) > 4:
        context = frames[5]
    else:
        context = frames[0]

    modname = context[1]
    lineno = context[2]

    if context[3]:
        funcname = context[3]
    else:
        funcname = ""
        
    # python docs say you don't want references to
    # frames lying around.  Bad things can happen.
    del context
    del frames

    return modname, funcname, lineno


class RedisLogRecord(logging.LogRecord):
    def __init__(self, name, lvl, fn, lno, msg, args, exc_info, func=None, extra=None):
        logging.LogRecord.__init__(self, name, lvl, fn, lno, msg, args, exc_info, func)

        # You can also access the following instance variables via the
        # formatter as
        #     %(hostname)s
        #     %(username)s
        #     %(modname)s
        # etc.
        self.hostname = socket.gethostname()
        self.username = getpass.getuser()
        self.modname, self.funcname, self.lineno = _getCallingContext()

        self._raw = {
            'name': name,
            'level': levelAsString(lvl),
            'filename': fn,
            'line_no': self.lineno,
            'msg': str(msg),
            'args': list(args),
            'time': datetime.datetime.utcnow(),
            'username': self.username,
            'funcname': self.funcname,
            'hostname': self.hostname,
            'traceback': exc_info
        }

class RedisLogger(logging.getLoggerClass()):
    def makeRecord(self, name, lvl, fn, lno, msg, args, exc_info, func=None, extra=None):
        record = RedisLogRecord(name, lvl, fn, lno, msg, args, exc_info, func=None)

        if extra:
            for key in extra:
                if (key in ["message", "asctime"]) or (key in record.__dict__):
                    raise KeyError("Attempt to overwrite %r in RedisLogRecord" % key)
                record.__dict__[key] = extra[key]
        return record





########NEW FILE########
