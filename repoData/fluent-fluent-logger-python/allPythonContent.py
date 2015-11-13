__FILENAME__ = event
# -*- coding: utf-8 -*-

import time

from fluent import sender


class Event(object):
    def __init__(self, label, data, **kwargs):
        assert isinstance(data, dict), 'data must be a dict'
        sender_ = kwargs.get('sender', sender.get_global_sender())
        timestamp = kwargs.get('time', int(time.time()))
        sender_.emit_with_time(label, timestamp, data)

########NEW FILE########
__FILENAME__ = handler
# -*- coding: utf-8 -*-

import logging
import socket

try:
    import simplejson as json
except ImportError:
    import json

from fluent import sender


class FluentRecordFormatter(object):
    def __init__(self):
        self.hostname = socket.gethostname()

    def format(self, record):
        data = {'sys_host': self.hostname,
                'sys_name': record.name,
                'sys_module': record.module,
                # 'sys_lineno': record.lineno,
                # 'sys_levelno': record.levelno,
                # 'sys_levelname': record.levelname,
                # 'sys_filename': record.filename,
                # 'sys_funcname': record.funcName,
                # 'sys_exc_info': record.exc_info,
                }
        # if 'sys_exc_info' in data and data['sys_exc_info']:
        #    data['sys_exc_info'] = self.formatException(data['sys_exc_info'])

        self._structuring(data, record.msg)
        return data

    def _structuring(self, data, msg):
        if isinstance(msg, dict):
            self._add_dic(data, msg)
        elif isinstance(msg, str):
            try:
                self._add_dic(data, json.loads(str(msg)))
            except (ValueError, json.JSONDecodeError):
                pass

    @staticmethod
    def _add_dic(data, dic):
        for key, value in dic.items():
            if isinstance(key, basestring):
                data[str(key)] = value


class FluentHandler(logging.Handler):
    '''
    Logging Handler for fluent.
    '''
    def __init__(self,
                 tag,
                 host='localhost',
                 port=24224,
                 timeout=3.0,
                 verbose=False):

        self.tag = tag
        self.sender = sender.FluentSender(tag,
                                          host=host, port=port,
                                          timeout=timeout, verbose=verbose)
        logging.Handler.__init__(self)

    def emit(self, record):
        data = self.format(record)
        self.sender.emit(None, data)

    def close(self):
        self.acquire()
        try:
            self.sender._close()
            logging.Handler.close(self)
        finally:
            self.release()
########NEW FILE########
__FILENAME__ = sender
# -*- coding: utf-8 -*-

from __future__ import print_function
import socket
import threading
import time

import msgpack


_global_sender = None


def setup(tag, **kwargs):
    host = kwargs.get('host', 'localhost')
    port = kwargs.get('port', 24224)

    global _global_sender
    _global_sender = FluentSender(tag, host=host, port=port)


def get_global_sender():
    return _global_sender


class FluentSender(object):
    def __init__(self,
                 tag,
                 host='localhost',
                 port=24224,
                 bufmax=1 * 1024 * 1024,
                 timeout=3.0,
                 verbose=False):

        self.tag = tag
        self.host = host
        self.port = port
        self.bufmax = bufmax
        self.timeout = timeout
        self.verbose = verbose

        self.socket = None
        self.pendings = None
        self.packer = msgpack.Packer()
        self.lock = threading.Lock()

        try:
            self._reconnect()
        except Exception:
            # will be retried in emit()
            self._close()

    def emit(self, label, data):
        cur_time = int(time.time())
        self.emit_with_time(label, cur_time, data)

    def emit_with_time(self, label, timestamp, data):
        bytes_ = self._make_packet(label, timestamp, data)
        self._send(bytes_)

    def _make_packet(self, label, timestamp, data):
        if label:
            tag = '.'.join((self.tag, label))
        else:
            tag = self.tag
        packet = (tag, timestamp, data)
        if self.verbose:
            print(packet)
        return self.packer.pack(packet)

    def _send(self, bytes_):
        self.lock.acquire()
        try:
            self._send_internal(bytes_)
        finally:
            self.lock.release()

    def _send_internal(self, bytes_):
        # buffering
        if self.pendings:
            self.pendings += bytes_
            bytes_ = self.pendings

        try:
            # reconnect if possible
            self._reconnect()

            # send message
            self.socket.sendall(bytes_)

            # send finished
            self.pendings = None
        except Exception:
            # close socket
            self._close()
            # clear buffer if it exceeds max bufer size
            if self.pendings and (len(self.pendings) > self.bufmax):
                # TODO: add callback handler here
                self.pendings = None
            else:
                self.pendings = bytes_

    def _reconnect(self):
        if not self.socket:
            if self.host.startswith('unix://'):
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                sock.connect(self.host[len('unix://'):])
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
            self.socket = sock

    def _close(self):
        if self.socket:
            self.socket.close()
        self.socket = None

########NEW FILE########
__FILENAME__ = run_tests
import unittest

from tests import *

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = mockserver
# -*- coding: utf-8 -*-

try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

import socket
import threading
import time

from msgpack import Unpacker


class MockRecvServer(threading.Thread):
    """
    Single threaded server accepts one connection and recv until EOF.
    """
    def __init__(self, host='localhost', port=24224):
        if host.startswith('unix://'):
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.bind(host[len('unix://'):])
        else:
            self._sock = socket.socket()
            self._sock.bind((host, port))
        self._buf = BytesIO()

        threading.Thread.__init__(self)
        self.start()

    def run(self):
        sock = self._sock
        sock.listen(1)
        con, _ = sock.accept()
        while True:
            data = con.recv(4096)
            if not data:
                break
            self._buf.write(data)
        con.close()
        sock.close()
        self._sock = None

    def wait(self):
        while self._sock:
            time.sleep(0.1)

    def get_recieved(self):
        self.wait()
        self._buf.seek(0)
        # TODO: have to process string encoding properly. currently we assume
        # that all encoding is utf-8.
        return list(Unpacker(self._buf, encoding='utf-8'))

########NEW FILE########
__FILENAME__ = test_event
# -*- coding: utf-8 -*-

import unittest

from fluent import event, sender


sender.setup(server='localhost', tag='app')


class TestEvent(unittest.TestCase):
    def testLogging(self):
        # send event with tag app.follow
        event.Event('follow', {
            'from': 'userA',
            'to':   'userB'
        })

        # send event with tag app.follow, with timestamp
        event.Event('follow', {
            'from': 'userA',
            'to':   'userB'
        }, time=int(0))

########NEW FILE########
__FILENAME__ = test_handler
# -*- coding: utf-8 -*-

import logging
import unittest

import fluent.handler

from tests import mockserver


class TestHandler(unittest.TestCase):
    def setUp(self):
        super(TestHandler, self).setUp()
        for port in range(10000, 20000):
            try:
                self._server = mockserver.MockRecvServer('localhost', port)
                self._port = port
                break
            except IOError:
                pass

    def get_data(self):
        return self._server.get_recieved()

    def test_simple(self):
        handler = fluent.handler.FluentHandler('app.follow', port=self._port)

        logging.basicConfig(level=logging.INFO)
        log = logging.getLogger('fluent.test')
        handler.setFormatter(fluent.handler.FluentRecordFormatter())
        log.addHandler(handler)
        log.info({
            'from': 'userA',
            'to': 'userB'
        })
        handler.close()

        data = self.get_data()
        eq = self.assertEqual
        eq(1, len(data))
        eq(3, len(data[0]))
        eq('app.follow', data[0][0])
        eq('userA', data[0][2]['from'])
        eq('userB', data[0][2]['to'])
        self.assert_(data[0][1])
        self.assert_(isinstance(data[0][1], int))

########NEW FILE########
__FILENAME__ = test_sender
# -*- coding: utf-8 -*-

from __future__ import print_function
import unittest

import fluent.sender

from tests import mockserver


class TestSender(unittest.TestCase):
    def setUp(self):
        super(TestSender, self).setUp()
        for port in range(10000, 20000):
            try:
                self._server = mockserver.MockRecvServer('localhost', port)
                break
            except IOError as exc:
                print(exc)
        self._sender = fluent.sender.FluentSender(tag='test', port=port)

    def get_data(self):
        return self._server.get_recieved()

    def test_simple(self):
        sender = self._sender
        sender.emit('foo', {'bar': 'baz'})
        sender._close()
        data = self.get_data()
        eq = self.assertEqual
        eq(1, len(data))
        eq(3, len(data[0]))
        eq('test.foo', data[0][0])
        eq({'bar': 'baz'}, data[0][2])
        self.assert_(data[0][1])
        self.assert_(isinstance(data[0][1], int))

########NEW FILE########
