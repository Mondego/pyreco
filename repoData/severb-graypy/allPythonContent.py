__FILENAME__ = handler
import logging
import json
import zlib
import traceback
import struct
import random
import socket
import math
from logging.handlers import DatagramHandler


WAN_CHUNK, LAN_CHUNK = 1420, 8154


class GELFHandler(DatagramHandler):
    """Graylog Extended Log Format handler

    :param host: The host of the graylog server.
    :param port: The port of the graylog server (default 12201).
    :param chunk_size: Message chunk size. Messages larger than this
        size will be sent to graylog in multiple chunks. Defaults to
        `WAN_CHUNK=1420`.
    :param debugging_fields: Send debug fields if true (the default).
    :param extra_fields: Send extra fields on the log record to graylog
        if true (the default).
    :param fqdn: Use fully qualified domain name of localhost as source 
        host (socket.getfqdn()).
    :param localname: Use specified hostname as source host.
    :param facility: Replace facility with specified value. If specified,
        record.name will be passed as `logger` parameter.
    """

    def __init__(self, host, port=12201, chunk_size=WAN_CHUNK,
            debugging_fields=True, extra_fields=True, fqdn=False, 
            localname=None, facility=None):
        self.debugging_fields = debugging_fields
        self.extra_fields = extra_fields
        self.chunk_size = chunk_size
        self.fqdn = fqdn
        self.localname = localname
        self.facility = facility
        DatagramHandler.__init__(self, host, port)

    def send(self, s):
        if len(s) < self.chunk_size:
            DatagramHandler.send(self, s)
        else:
            for chunk in ChunkedGELF(s, self.chunk_size):
                DatagramHandler.send(self, chunk)

    def makePickle(self, record):
        message_dict = make_message_dict(
            record, self.debugging_fields, self.extra_fields, self.fqdn, 
	    self.localname, self.facility)
        return zlib.compress(json.dumps(message_dict).encode('utf-8'))


class ChunkedGELF(object):
    def __init__(self, message, size):
        self.message = message
        self.size = size
        self.pieces = struct.pack('B', int(math.ceil(len(message) * 1.0/size)))
        self.id = struct.pack('Q', random.randint(0, 0xFFFFFFFFFFFFFFFF))

    def message_chunks(self):
        return (self.message[i:i + self.size] for i
                    in range(0, len(self.message), self.size))

    def encode(self, sequence, chunk):
        return ''.join([
            '\x1e\x0f',
            self.id,
            struct.pack('B', sequence),
            self.pieces,
            chunk
        ])

    def __iter__(self):
        for sequence, chunk in enumerate(self.message_chunks()):
            yield self.encode(sequence, chunk)


def make_message_dict(record, debugging_fields, extra_fields, fqdn, localname, facility=None):
    if fqdn:
        host = socket.getfqdn()
    elif localname:
        host = localname
    else:
        host = socket.gethostname()
    fields = {'version': "1.0",
        'host': host,
        'short_message': record.getMessage(),
        'full_message': get_full_message(record.exc_info, record.getMessage()),
        'timestamp': record.created,
        'level': SYSLOG_LEVELS.get(record.levelno, record.levelno),
        'facility': facility or record.name,
    }

    if facility is not None:
        fields.update({
            '_logger': record.name
        })

    if debugging_fields:
        fields.update({
            'file': record.pathname,
            'line': record.lineno,
            '_function': record.funcName,
            '_pid': record.process,
            '_thread_name': record.threadName,
        })
        # record.processName was added in Python 2.6.2
        pn = getattr(record, 'processName', None)
        if pn is not None:
            fields['_process_name'] = pn
    if extra_fields:
        fields = add_extra_fields(fields, record)
    return fields

SYSLOG_LEVELS = {
    logging.CRITICAL: 2,
    logging.ERROR: 3,
    logging.WARNING: 4,
    logging.INFO: 6,
    logging.DEBUG: 7,
}


def get_full_message(exc_info, message):
    return '\n'.join(traceback.format_exception(*exc_info)) if exc_info else message


def add_extra_fields(message_dict, record):
    # skip_list is used to filter additional fields in a log message.
    # It contains all attributes listed in
    # http://docs.python.org/library/logging.html#logrecord-attributes
    # plus exc_text, which is only found in the logging module source,
    # and id, which is prohibited by the GELF format.
    skip_list = (
        'args', 'asctime', 'created', 'exc_info',  'exc_text', 'filename',
        'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
        'msecs', 'msecs', 'message', 'msg', 'name', 'pathname', 'process',
        'processName', 'relativeCreated', 'thread', 'threadName')

    for key, value in record.__dict__.items():
        if key not in skip_list and not key.startswith('_'):
            if isinstance(value, basestring):
                message_dict['_%s' % key] = value
            else:
                message_dict['_%s' % key] = repr(value)

    return message_dict

########NEW FILE########
__FILENAME__ = rabbitmq
import json
from amqplib import client_0_8 as amqp
from graypy.handler import make_message_dict
from logging import Filter
from logging.handlers import SocketHandler
from urlparse import urlparse
import urllib


_ifnone = lambda v, x: x if v is None else v


class GELFRabbitHandler(SocketHandler):
    """RabbitMQ / Graylog Extended Log Format handler

    NOTE: this handler ingores all messages logged by amqplib.

    :param url: RabbitMQ URL (ex: amqp://guest:guest@localhost:5672/).
    :param exchange: RabbitMQ exchange. Default 'logging.gelf'.
        A queue binding must be defined on the server to prevent
        log messages from being dropped.
    :param debugging_fields: Send debug fields if true (the default).
    :param extra_fields: Send extra fields on the log record to graylog
        if true (the default).
    :param fqdn: Use fully qualified domain name of localhost as source 
        host (socket.getfqdn()).
    :param exchange_type: RabbitMQ exchange type (default 'fanout').
    :param localname: Use specified hostname as source host.
    :param facility: Replace facility with specified value. If specified,
        record.name will be passed as `logger` parameter.
    """

    def __init__(self, url, exchange='logging.gelf', debugging_fields=True,
            extra_fields=True, fqdn=False, exchange_type='fanout', localname=None,
            facility=None, virtual_host='/'):
        self.url = url
        parsed = urlparse(url)
        if parsed.scheme != 'amqp':
            raise ValueError('invalid URL scheme (expected "amqp"): %s' % url)
        host = parsed.hostname or 'localhost'
        port = _ifnone(parsed.port, 5672)
        virtual_host = virtual_host if not urllib.unquote(parsed.path[1:]) else urllib.unquote(parsed.path[1:])
        self.cn_args = {
            'host': '%s:%s' % (host, port),
            'userid': _ifnone(parsed.username, 'guest'),
            'password': _ifnone(parsed.password, 'guest'),
            'virtual_host': virtual_host,
            'insist': False,
        }
        self.exchange = exchange
        self.debugging_fields = debugging_fields
        self.extra_fields = extra_fields
        self.fqdn = fqdn
        self.exchange_type = exchange_type
        self.localname = localname
        self.facility = facility
        self.virtual_host = virtual_host
        SocketHandler.__init__(self, host, port)
        self.addFilter(ExcludeFilter('amqplib'))

    def makeSocket(self, timeout=1):
        return RabbitSocket(self.cn_args, timeout, self.exchange,
            self.exchange_type)

    def makePickle(self, record):
        message_dict = make_message_dict(
            record, self.debugging_fields, self.extra_fields, self.fqdn, self.localname,
            self.facility)
        return json.dumps(message_dict)


class RabbitSocket(object):

    def __init__(self, cn_args, timeout, exchange, exchange_type):
        self.cn_args = cn_args
        self.timeout = timeout
        self.exchange = exchange
        self.exchange_type = exchange_type
        self.connection = amqp.Connection(
            connection_timeout=timeout, **self.cn_args)
        self.channel = self.connection.channel()
        self.channel.exchange_declare(
            exchange=self.exchange,
            type=self.exchange_type,
            durable=True,
            auto_delete=False,
        )

    def sendall(self, data):
        msg = amqp.Message(data, delivery_mode=2)
        self.channel.basic_publish(msg, exchange=self.exchange)

    def close(self):
        try:
            self.connection.close()
        except Exception:
            pass


class ExcludeFilter(Filter):

    def __init__(self, name):
        """Initialize filter.

        Initialize with the name of the logger which, together with its
        children, will have its events excluded (filtered out).
        """
        if not name:
            raise ValueError('ExcludeFilter requires a non-empty name')
        self.name = name
        self.nlen = len(name)

    def filter(self, record):
        return not (record.name.startswith(self.name) and (
            len(record.name) == self.nlen or record.name[self.nlen] == "."))

########NEW FILE########
__FILENAME__ = perftest
#! /usr/bin/env python
import argparse
import logging
import logging.config
import sys
import time

def main(argv=sys.argv):
    parser = argparse.ArgumentParser(prog="perftest.py")
    parser.add_argument('--graylog-host',
        help='Graylog2 host. Do not test GELFHandler if not specified.')
    parser.add_argument('--graylog-port', type=int, default=12201,
        help='Graylog2 GELF UDP port. Default: 12201')
    parser.add_argument('--rabbit-url',
        help='RabbitMQ url (ex: amqp://guest:guest@localhost/). '
             'Do not test GELFRabbitHandler if not specified.')
    parser.add_argument('--rabbit-exchange', default='logging.gelf',
        help='RabbitMQ exchange. Default: logging.gelf')
    parser.add_argument('--console-logger', action='store_true', default=None)
    parser.add_argument('--stress', action='store_true',
        help='Enable performance/stress test. WARNING this logs MANY warnings.')
    args = parser.parse_args(argv[1:])

    if all(v is None for v in
            [args.graylog_host, args.rabbit_url, args.console_logger]):
        parser.print_help()

    config = {
        'version': 1,
        'formatters': {
            'brief': {'format': "%(levelname)-7s %(name)s - %(message)s"},
            'message': {'format': "%(message)s"},
        },
        'handlers': {},
        'root': {'handlers': [], 'level': 'DEBUG'},
        'disable_existing_loggers': False,
    }
    
    if args.graylog_host is not None:
        config['handlers']['graylog_udp'] = {
            'class': 'graypy.GELFHandler',
            'host': args.graylog_host,
            'port': args.graylog_port,
            'debugging_fields': 0,
            'formatter': 'message',
        }
        config['root']['handlers'].append('graylog_udp')

    if args.rabbit_url is not None:
        config['handlers']['graylog_rabbit'] = {
            'class': 'graypy.GELFRabbitHandler',
            'url': args.rabbit_url,
            'exchange': args.rabbit_exchange,
            'debugging_fields': 0,
            'formatter': 'message',
        }
        config['root']['handlers'].append('graylog_rabbit')

    if args.console_logger:
        config['handlers']['console'] = {
            'class': 'logging.StreamHandler',
            'formatter': 'brief',
        }
        config['root']['handlers'].append('console')

    logging.config.dictConfig(config)

    log = logging.getLogger()
    t_start = time.time()
    total = 0

    log.debug('debug')
    log.info('info')
    log.warn('warning')
    log.error('error')
    log.critical('critical')
    total += 5

    if args.stress:
        t_end = time.time() + 10
        tx = t_end - 9
        cx = 0
        while True:
            log.warn('warning')
            cx += 1
            total += 1
            if time.time() > tx:
                elapsed = time.time() - (tx - 1)
                tx += 1
                print('%s messages in %.3f seconds (%.3f msg/s)'
                    % (cx, elapsed, cx / elapsed))
                cx = 0
                if tx > t_end:
                    break

    elapsed = time.time() - t_start
    print('%s messages in %.3f seconds (%.3f msg/s)'
        % (total, elapsed, total / elapsed))

if __name__ == '__main__':
    main()

########NEW FILE########
