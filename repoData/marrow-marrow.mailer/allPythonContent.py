__FILENAME__ = imap
import logging
from marrow.mailer import Message, Mailer
logging.basicConfig(level=logging.DEBUG)

mail = Mailer({
        'manager.use': 'futures',
        'transport.use': 'imap',
        'transport.host': '',
        'transport.ssl': True,
        'transport.username': '',
        'transport.password': '',
        'transport.folder': 'Marrow'
    })

mail.start()

message = Message([('Alice Bevan-McGregor', 'alice@gothcandy.com')], [('Alice Two', 'alice.mcgregor@me.com')], "This is a test message.", plain="Testing!")

mail.send(message)
mail.stop()

########NEW FILE########
__FILENAME__ = maildir
import logging
from marrow.mailer import Message, Mailer
logging.basicConfig(level=logging.INFO)

mail = Mailer({'manager.use': 'immediate', 'transport.use': 'maildir', 'transport.directory': 'data/maildir'})
mail.start()

message = Message([('Alice Bevan-McGregor', 'alice@gothcandy.com')], [('Alice Two', 'alice.mcgregor@me.com')], "This is a test message.", plain="Testing!")

mail.send(message)
mail.stop()


########NEW FILE########
__FILENAME__ = mbox
import logging
from marrow.mailer import Message, Mailer
logging.basicConfig(level=logging.INFO)

mail = Mailer({'manager.use': 'immediate', 'transport.use': 'mbox', 'transport.file': 'data/mbox'})
mail.start()

message = Message([('Alice Bevan-McGregor', 'alice@gothcandy.com')], [('Alice Two', 'alice.mcgregor@me.com')], "This is a test message.", plain="Testing!")

mail.send(message)
mail.stop()


########NEW FILE########
__FILENAME__ = smtp
import logging
from marrow.mailer import Message, Mailer
logging.basicConfig(level=logging.INFO)

mail = Mailer({
        'manager.use': 'futures',
        'transport.use': 'smtp',
        'transport.host': '',
        'transport.tls': 'ssl',
        'transport.username': '',
        'transport.password': '',
        'transport.max_messages_per_connection': 5
    })
mail.start()

message = Message([('Alice Bevan-McGregor', 'alice@gothcandy.com')], [('Alice Two', 'alice.mcgregor@me.com')], "This is a test message.", plain="Testing!")

mail.send(message)
mail.stop()

########NEW FILE########
__FILENAME__ = address
# encoding: utf-8

"""TurboMail utility functions and support classes."""

from __future__ import unicode_literals
import sys

from email.utils import formataddr, parseaddr
from email.header import Header

from marrow.mailer.validator import EmailValidator
from marrow.util.compat import basestring, unicode, unicodestr, native

__all__ = ['Address', 'AddressList']


class Address(object):
    """Validated electronic mail address class.
    
    This class knows how to validate and format e-mail addresses.  It uses
    Python's built-in `parseaddr` and `formataddr` helper functions and helps
    guarantee a uniform base for all e-mail address operations.
    
    The AddressList unit tests provide comprehensive testing of this class as
    well."""
    
    def __init__(self, name_or_email, email=None, encoding='utf-8'):
        self.encoding = encoding
        
        if email is None:
            if isinstance(name_or_email, AddressList):
                if not 0 < len(name_or_email) < 2:
                    raise ValueError("AddressList to convert must only contain a single Address.")
                
                name_or_email = unicode(name_or_email[0])
            
            if isinstance(name_or_email, (tuple, list)):
                self.name = unicodestr(name_or_email[0], encoding)
                self.address = unicodestr(name_or_email[1], encoding)
            
            elif isinstance(name_or_email, bytes):
                self.name, self.address = parseaddr(unicodestr(name_or_email, encoding))
            
            elif isinstance(name_or_email, unicode):
                self.name, self.address = parseaddr(name_or_email)
            
            else:
                raise TypeError('Expected string, tuple or list, got {0} instead'.format(
                        repr(type(name_or_email))
                    ))
        else:
            self.name = unicodestr(name_or_email, encoding)
            self.address = unicodestr(email, encoding)
        
        email, err = EmailValidator().validate_email(self.address)
        
        if err:
            raise ValueError('"{0}" is not a valid e-mail address: {1}'.format(email, err))
    
    def __eq__(self, other):
        if isinstance(other, Address):
            return (self.name, self.address) == (other.name, other.address)
        
        elif isinstance(other, unicode):
            return unicode(self) == other
        
        elif isinstance(other, bytes):
            return bytes(self) == other
        
        elif isinstance(other, tuple):
            return (self.name, self.address) == other
        
        raise NotImplementedError("Can not compare Address instance against {0} instance".format(type(other)))
    
    def __ne__(self, other):
        return not self == other
    
    def __len__(self):
        return len(self.__unicode__())
    
    def __repr__(self):
        return 'Address("{0}")'.format(unicode(self).encode('ascii', 'backslashreplace'))
    
    def __unicode__(self):
        return self.encode('utf8').decode('utf8')
    
    def __bytes__(self):
        return self.encode()
    
    if sys.version_info < (3, 0):
        __str__ = __bytes__
    
    else:  # pragma: no cover
        __str__ = __unicode__
    
    def encode(self, encoding=None):
        if encoding is None:
            encoding = self.encoding
        
        name_string = Header(self.name, encoding).encode()
        
        # Encode punycode for internationalized domains.
        localpart, domain = self.address.split('@', 1)
        domain = domain.encode('idna').decode()
        address = '@'.join((localpart, domain))
        
        return formataddr((name_string, address)).replace('\n', '').encode(encoding)
    
    @property
    def valid(self):
        email, err = EmailValidator().validate_email(self.address)
        return False if err else True


class AddressList(list):
    def __init__(self, addresses=None, encoding="utf-8"):
        super(AddressList, self).__init__()
        
        self.encoding = encoding
        
        if addresses is None:
            return
        
        if isinstance(addresses, basestring):
            addresses = addresses.split(',')
        
        elif isinstance(addresses, tuple):
            self.append(Address(addresses, encoding=encoding))
            return
        
        if not isinstance(addresses, list):
            raise ValueError("Invalid value for AddressList: {0}".format(repr(addresses)))
        
        self.extend(addresses)
    
    def __repr__(self):
        if not self:
            return "AddressList()"
        
        return "AddressList(\"{0}\")".format(", ".join([str(i) for i in self]))
    
    def __bytes__(self):
        return self.encode()
    
    def __unicode__(self):
        return ", ".join(unicode(i) for i in self)
    
    if sys.version_info < (3, 0):
        __str__ = __bytes__
    
    else:  # pragma: no cover
        __str__ = __unicode__
    
    def __setitem__(self, k, value):
        if isinstance(k, slice):
            value = [Address(val) if not isinstance(val, Address) else val for val in value]
        
        elif not isinstance(value, Address):
            value = Address(value)
        
        super(AddressList, self).__setitem__(k, value)
    
    def __setslice__(self, i, j, sequence):
        self.__setitem__(slice(i, j), sequence)
    
    def encode(self, encoding=None):
        encoding = encoding if encoding else self.encoding
        # print type(self[0]), self[0], self[0].encode(encoding)
        return b", ".join([a.encode(encoding) for a in self])
    
    def extend(self, sequence):
        values = [Address(val) if not isinstance(val, Address) else val for val in sequence]
        super(AddressList, self).extend(values)
    
    def append(self, value):
        self.extend([value])
    
    @property
    def addresses(self):
        return AddressList([i.address for i in self])
    
    @property
    def string_addresses(self, encoding=None):
        """Return a list of string representations of the addresses suitable
        for usage in an SMTP transaction."""
        encoding = encoding if encoding else self.encoding
        return [a.encode(encoding) for a in AddressList([i.address for i in self])]


class AutoConverter(object):
    """Automatically converts an assigned value to the given type."""
    
    def __init__(self, attr, cls, can=True):
        self.cls = cls
        self.can = can
        self.attr = native(attr)
    
    def __get__(self, instance, owner):
        value = getattr(instance, self.attr, None)
        
        if value is None:
            return self.cls() if self.can else None
        
        return value
    
    def __set__(self, instance, value):
        if not isinstance(value, self.cls):
            value = self.cls(value)
        
        setattr(instance, self.attr, value)
    
    def __delete__(self, instance):
        setattr(instance, self.attr, None)

########NEW FILE########
__FILENAME__ = exc
# encoding: utf-8

"""Exceptions used by marrow.mailer to report common errors."""


__all__ = [
        'MailException',
        'MailConfigurationException',
        'TransportException',
        'TransportFailedException',
        'MessageFailedException',
        'TransportExhaustedException',
        'ManagerException'
    ]



class MailException(Exception):
    """The base for all marrow.mailer exceptions."""
    
    pass


# Application Exceptions

class DeliveryException(MailException):
    """The base class for all public-facing exceptions."""
    
    pass


class DeliveryFailedException(DeliveryException):
    """The message stored in args[0] could not be delivered for the reason
    given in args[1].  (These can be accessed as e.msg and e.reason.)"""
    
    def __init__(self, message, reason):
        self.msg = message
        self.reason = reason
        
        super(DeliveryFailedException, self).__init__(message, reason)


# Internal Exceptions

class MailerNotRunning(MailException):
    """Raised when attempting to deliver messages using a dead interface."""
    
    pass


class MailConfigurationException(MailException):
    """There was an error in the configuration of marrow.mailer."""
    
    pass


class TransportException(MailException):
    """The base for all marrow.mailer Transport exceptions."""
    
    pass


class TransportFailedException(TransportException):
    """The transport has failed to deliver the message due to an internal
    error; a new instance of the transport should be used to retry."""
    
    pass


class MessageFailedException(TransportException):
    """The transport has failed to deliver the message due to a problem with
    the message itself, and no attempt should be made to retry delivery of
    this message.  The transport may still be re-used, however.
    
    The reason for the failure should be the first argument.
    """
    
    pass


class TransportExhaustedException(TransportException):
    """The transport has successfully delivered the message, but can no longer
    be used for future message delivery; a new instance should be used on the
    next request."""
    
    pass


class ManagerException(MailException):
    """The base for all marrow.mailer Manager exceptions."""
    pass

########NEW FILE########
__FILENAME__ = interfaces
# encoding: utf-8

from marrow.interface import Interface
from marrow.interface.schema import Method


__all__ = ['IManager', 'ITransport']


class IPlugin(Interface):
    startup = Method(args=0)
    deliver = Method(args=1)
    shutdown = Method(args=0)


class IManager(IPlugin):
    __init__ = Method(args=2)


class ITransport(IPlugin):
    __init__ = Method(args=1)

########NEW FILE########
__FILENAME__ = logger
# encoding: utf-8

import logging

from marrow.mailer import Mailer



class MailHandler(logging.Handler):
    """A class which sends records out via e-mail.
    
    This handler should be configured using the same configuration
    directives that Marrow Mailer itself understands.
    
    Be careful how many notifications get sent.
    
    It is suggested to use background delivery using the 'dynamic' manager.
    """
    
    def __init__(self, *args, **config):
        """Initialize the instance, optionally configuring TurboMail itself.
        
        If no additional arguments are supplied to the handler, re-use any
        existing running TurboMail configuration.
        
        To get around limitations of the INI parser, you can pass in a tuple
        of name, value pairs to populate the dictionary.  (Use `{}` dict
        notation in produciton, though.)
        """
        
        logging.Handler.__init__(self)
        
        self.config = dict()
        
        if args:
            config.update(dict(zip(*[iter(args)]*2)))
        
        self.mailer = Mailer(config).start()
        
        # If we get a configuration that doesn't explicitly start TurboMail
        # we use the configuration to populate the Message instance.
        self.config = config
    
    def emit(self, record):
        """Emit a record."""
        
        try:
            self.mailer.new(plain=self.format(record)).send()
        
        except (KeyboardInterrupt, SystemExit):
            raise
        
        except:
            self.handleError(record)


logging.MailHandler = MailHandler

########NEW FILE########
__FILENAME__ = dynamic
# encoding: utf-8

import atexit
import threading
import weakref
import sys
import math

from functools import partial

from marrow.mailer.manager.futures import worker
from marrow.mailer.manager.util import TransportPool

try:
    import queue
except ImportError:
    import Queue as queue

try:
    from concurrent import futures
except ImportError:  # pragma: no cover
    raise ImportError("You must install the futures package to use background delivery.")


__all__ = ['DynamicManager']

log = __import__('logging').getLogger(__name__)


def thread_worker(executor, jobs, timeout, maximum):
    i = maximum + 1

    try:
        while i:
            i -= 1

            try:
                work = jobs.get(True, timeout)

                if work is None:
                    runner = executor()

                    if runner is None or runner._shutdown:
                        log.debug("Worker instructed to shut down.")
                        break

                    # Can't think of a test case for this; best to be safe.
                    del runner  # pragma: no cover
                    continue  # pragma: no cover

            except queue.Empty:  # pragma: no cover
                log.debug("Worker death from starvation.")
                break

            else:
                work.run()

        else:  # pragma: no cover
            log.debug("Worker death from exhaustion.")

    except:  # pragma: no cover
        log.critical("Unhandled exception in worker.", exc_info=True)

    runner = executor()
    if runner:
        runner._threads.discard(threading.current_thread())


class WorkItem(object):
    __slots__ = ('future', 'fn', 'args', 'kwargs')

    def __init__(self, future, fn, args, kwargs):
        self.future = future
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        if not self.future.set_running_or_notify_cancel():
            return

        try:
            result = self.fn(*self.args, **self.kwargs)

        except:
            e = sys.exc_info()[1]
            self.future.set_exception(e)

        else:
            self.future.set_result(result)


class ScalingPoolExecutor(futures.ThreadPoolExecutor):
    def __init__(self, workers, divisor, timeout):
        self._max_workers = workers
        self.divisor = divisor
        self.timeout = timeout

        self._work_queue = queue.Queue()

        self._threads = set()
        self._shutdown = False
        self._shutdown_lock = threading.Lock()
        self._management_lock = threading.Lock()

        atexit.register(self._atexit)

    def shutdown(self, wait=True):
        with self._shutdown_lock:
            self._shutdown = True

            for i in range(len(self._threads)):
                self._work_queue.put(None)

        if wait:
            for thread in list(self._threads):
                thread.join()

    def _atexit(self):  # pragma: no cover
        self.shutdown(True)

    def _spawn(self):
        t = threading.Thread(target=thread_worker, args=(weakref.ref(self), self._work_queue, self.divisor, self.timeout))
        t.daemon = True
        t.start()

        with self._management_lock:
            self._threads.add(t)

    def _adjust_thread_count(self):
        pool = len(self._threads)

        if pool < self._optimum_workers:
            tospawn = int(self._optimum_workers - pool)
            log.debug("Spawning %d thread%s." % (tospawn, tospawn != 1 and "s" or ""))

            for i in range(tospawn):
                self._spawn()

    @property
    def _optimum_workers(self):
        return min(self._max_workers, math.ceil(self._work_queue.qsize() / float(self.divisor)))


class DynamicManager(object):
    __slots__ = ('workers', 'divisor', 'timeout', 'executor', 'transport')

    name = "Dynamic"
    Executor = ScalingPoolExecutor

    def __init__(self, config, transport):
        self.workers = int(config.get('workers', 10))  # Maximum number of threads to create.
        self.divisor = int(config.get('divisor', 10))  # Estimate the number of required threads by dividing the queue size by this.
        self.timeout = float(config.get('timeout', 60))  # Seconds before starvation.

        self.executor = None
        self.transport = TransportPool(transport)

        super(DynamicManager, self).__init__()

    def startup(self):
        log.info("%s manager starting up.", self.name)

        log.debug("Initializing transport queue.")
        self.transport.startup()

        workers = self.workers
        log.debug("Starting thread pool with %d workers." % (workers, ))
        self.executor = self.Executor(workers, self.divisor, self.timeout)

        log.info("%s manager ready.", self.name)

    def deliver(self, message):
        # Return the Future object so the application can register callbacks.
        # We pass the message so the executor can do what it needs to to make
        # the message thread-local.
        return self.executor.submit(partial(worker, self.transport), message)

    def shutdown(self, wait=True):
        log.info("%s manager stopping.", self.name)

        log.debug("Stopping thread pool.")
        self.executor.shutdown(wait=wait)

        log.debug("Draining transport queue.")
        self.transport.shutdown()

        log.info("%s manager stopped.", self.name)

########NEW FILE########
__FILENAME__ = futures
# encoding: utf-8

from functools import partial

from marrow.mailer.exc import TransportFailedException, TransportExhaustedException, MessageFailedException, DeliveryFailedException
from marrow.mailer.manager.util import TransportPool

try:
    from concurrent import futures
except ImportError: # pragma: no cover
    raise ImportError("You must install the futures package to use background delivery.")


__all__ = ['FuturesManager']

log = __import__('logging').getLogger(__name__)



def worker(pool, message):
    # This may be non-obvious, but there are several conditions which
    # we trap later that require us to retry the entire delivery.
    result = None
    
    while True:
        with pool() as transport:
            try:
                result = transport.deliver(message)
            
            except MessageFailedException as e:
                raise DeliveryFailedException(message, e.args[0] if e.args else "No reason given.")
            
            except TransportFailedException:
                # The transport has suffered an internal error or has otherwise
                # requested to not be recycled. Delivery should be attempted
                # again.
                transport.ephemeral = True
                continue
            
            except TransportExhaustedException:
                # The transport sent the message, but pre-emptively
                # informed us that future attempts will not be successful.
                transport.ephemeral = True
        
        break
    
    return message, result



class FuturesManager(object):
    __slots__ = ('workers', 'executor', 'transport')
    
    def __init__(self, config, transport):
        self.workers = config.get('workers', 1)
        
        self.executor = None
        self.transport = TransportPool(transport)
        
        super(FuturesManager, self).__init__()
    
    def startup(self):
        log.info("Futures delivery manager starting.")
        
        log.debug("Initializing transport queue.")
        self.transport.startup()
        
        workers = self.workers
        log.debug("Starting thread pool with %d workers." % (workers, ))
        self.executor = futures.ThreadPoolExecutor(workers)
        
        log.info("Futures delivery manager ready.")
    
    def deliver(self, message):
        # Return the Future object so the application can register callbacks.
        # We pass the message so the executor can do what it needs to to make
        # the message thread-local.
        return self.executor.submit(partial(worker, self.transport), message)
    
    def shutdown(self, wait=True):
        log.info("Futures delivery manager stopping.")
        
        log.debug("Stopping thread pool.")
        self.executor.shutdown(wait=wait)
        
        log.debug("Draining transport queue.")
        self.transport.shutdown()
        
        log.info("Futures delivery manager stopped.")

########NEW FILE########
__FILENAME__ = immediate
# encoding: utf-8

from marrow.mailer.exc import TransportExhaustedException, TransportFailedException, DeliveryFailedException, MessageFailedException
from marrow.mailer.manager.util import TransportPool


__all__ = ['ImmediateManager']

log = __import__('logging').getLogger(__name__)



class ImmediateManager(object):
    __slots__ = ('transport', )
    
    def __init__(self, config, Transport):
        """Initialize the immediate delivery manager."""
        
        # Create a transport pool; this will encapsulate the recycling logic.
        self.transport = TransportPool(Transport)
        
        super(ImmediateManager, self).__init__()
    
    def startup(self):
        """Perform startup actions.
        
        This just chains down to the transport layer.
        """
        
        log.info("Immediate delivery manager starting.")
        
        log.debug("Initializing transport queue.")
        self.transport.startup()
        
        log.info("Immediate delivery manager started.")
    
    def deliver(self, message):
        result = None
        
        while True:
            with self.transport() as transport:
                try:
                    result = transport.deliver(message)
                
                except MessageFailedException as e:
                    raise DeliveryFailedException(message, e.args[0] if e.args else "No reason given.")
                
                except TransportFailedException:
                    # The transport has suffered an internal error or has otherwise
                    # requested to not be recycled. Delivery should be attempted
                    # again.
                    transport.ephemeral = True
                    continue
                
                except TransportExhaustedException:
                    # The transport sent the message, but pre-emptively
                    # informed us that future attempts will not be successful.
                    transport.ephemeral = True
            
            break
        
        return message, result
    
    def shutdown(self):
        log.info("Immediate delivery manager stopping.")
        
        log.debug("Draining transport queue.")
        self.transport.shutdown()
        
        log.info("Immediate delivery manager stopped.")

########NEW FILE########
__FILENAME__ = transactional
# encoding: utf-8

"""Currently unsupported and non-functional."""

raise ImportError("This module is currently unsupported.")


import transaction

from functools import partial

from zope.interface import implements
from transaction.interfaces import IDataManager
  
from marrow.mailer.manager.dynamic import ScalingPoolExecutor, DynamicManager


__all__ = ['TransactionalDynamicManager']

log = __import__('logging').getLogger(__name__)



class ExecutorDataManager(object):
    implements(IDataManager)
    
    __slots__ = ('callback', 'abort_callback')
    
    def __init__(self, callback, abort=None, pool=None):
        self.callback = callback
        self.abort_callback = abort
    
    def commit(self, transaction):
        pass
    
    def abort(self, transaction):
        if self.abort_callback:
            self.abort_callback()
    
    def sortKey(self):
        return id(self)
    
    def abort_sub(self, transaction):
        pass
    
    commit_sub = abort_sub
    
    def beforeCompletion(self, transaction):
        pass
    
    afterCompletion = beforeCompletion
    
    def tpc_begin(self, transaction, subtransaction=False):
        if subtransaction:
            raise RuntimeError()
    
    def tpc_vote(self, transaction):
        pass
    
    def tpc_finish(self, transaction):
        self.callback()
    
    tpc_abort = abort


class TransactionalScalingPoolExecutor(ScalingPoolExecutor):
    def _submit(self, w):
        self._work_queue.put(w)
        self._adjust_thread_count()
    
    def _cancel_tn(self, f):
        if f.cancel():
            f.set_running_or_notify_cancel()
    
    def submit(self, fn, *args, **kwargs):
        with self._shutdown_lock:
            if self._shutdown:
                raise RuntimeError('cannot schedule new futures after shutdown')
            
            f = _base.Future()
            w = _WorkItem(f, fn, args, kwargs)
            
            dm = ExecutorDataManager(partial(self._submit, w), partial(self._cancel_tn, f))
            transaction.get().join(dm)
            
            return f


class TransactionalDynamicManager(DynamicManager):
    name = "Transactional dynamic"
    Executor = TransactionalScalingPoolExecutor

########NEW FILE########
__FILENAME__ = util
# encoding: utf-8

try:
    import queue
except ImportError:
    import Queue as queue


__all__ = ['TransportPool']

log = __import__('logging').getLogger(__name__)



class TransportPool(object):
    __slots__ = ('factory', 'transports')
    
    def __init__(self, factory):
        self.factory = factory
        self.transports = queue.Queue()
    
    def startup(self):
        pass
    
    def shutdown(self):
        try:
            while True:
                transport = self.transports.get(False)
                transport.shutdown()
        
        except queue.Empty:
            pass
    
    class Context(object):
        __slots__ = ('pool', 'transport')
        
        def __init__(self, pool):
            self.pool = pool
            self.transport = None
        
        def __enter__(self):
            # First we attempt to find an available transport.
            pool = self.pool
            transport = None
            
            while not transport:
                try:
                    # By consuming transports this way, we maintain thread safety.
                    # Transports are only accessed by a single thread at a time.
                    transport = pool.transports.get(False)
                    log.debug("Acquired existing transport instance.")
                
                except queue.Empty:
                    # No transport is available, so we initialize another one.
                    log.debug("Unable to acquire existing transport, initalizing new instance.")
                    transport = pool.factory()
                    transport.startup()
            
            self.transport = transport
            return transport
        
        def __exit__(self, type, value, traceback):
            transport = self.transport
            ephemeral = getattr(transport, 'ephemeral', False)
            
            if type is not None:
                log.error("Shutting down transport due to unhandled exception.", exc_info=True)
                transport.shutdown()
                return
            
            if not ephemeral:
                log.debug("Scheduling transport instance for re-use.")
                self.pool.transports.put(transport)
            
            else:
                log.debug("Transport marked as ephemeral, shutting down instance.")
                transport.shutdown()
    
    def __call__(self):
        return self.Context(self)

########NEW FILE########
__FILENAME__ = message
# encoding: utf-8

"""MIME-encoded electronic mail message class."""

import imghdr
import os
import time

from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email.header import Header
from email.utils import make_msgid, formatdate
from mimetypes import guess_type

from marrow.mailer import release
from marrow.mailer.address import Address, AddressList, AutoConverter
from marrow.util.compat import basestring, unicode

__all__ = ['Message']


class Message(object):
    """Represents an e-mail message."""

    sender = AutoConverter('_sender', Address, False)
    author = AutoConverter('_author', AddressList)
    authors = author
    to = AutoConverter('_to', AddressList)
    cc = AutoConverter('_cc', AddressList)
    bcc = AutoConverter('_bcc', AddressList)
    reply = AutoConverter('_reply', AddressList)
    notify = AutoConverter('_notify', AddressList)

    def __init__(self, author=None, to=None, subject=None, **kw):
        """Instantiate a new Message object.

        No arguments are required, as everything can be set using class
        properties.  Alternatively, __everything__ can be set using the
        constructor, using named arguments.  The first three positional
        arguments can be used to quickly prepare a simple message.
        """

        # Internally used attributes
        self._id = None
        self._processed = False
        self._dirty = False
        self.mailer = None

        # Default values
        self.subject = None
        self.date = datetime.now()
        self.encoding = 'utf-8'
        self.organization = None
        self.priority = None
        self.plain = None
        self.rich = None
        self.attachments = []
        self.embedded = []
        self.headers = []
        self.retries = 3
        self.brand = True

        self._sender = None
        self._author = AddressList()
        self._to = AddressList()
        self._cc = AddressList()
        self._bcc = AddressList()
        self._reply = AddressList()
        self._notify = AddressList()

        # Overrides at initialization time
        if author is not None:
            self.author = author

        if to is not None:
            self.to = to

        if subject is not None:
            self.subject = subject

        for k in kw:
            if not hasattr(self, k):
                raise TypeError("Unexpected keyword argument: %s" % k)

            setattr(self, k, kw[k])

    def __setattr__(self, name, value):
        """Set the dirty flag as properties are updated."""
        object.__setattr__(self, name, value)
        if name not in ('bcc', '_id', '_dirty', '_processed'):
            object.__setattr__(self, '_dirty', True)

    def __str__(self):
        return self.mime.as_string()

    @property
    def id(self):
        if not self._id or (self._processed and self._dirty):
            self._id = make_msgid()
            self._processed = False
        return self._id

    @property
    def envelope(self):
        """Returns the address of the envelope sender address (SMTP from, if
        not set the sender, if this one isn't set too, the author)."""
        if not self.sender and not self.author:
            raise ValueError("Unable to determine message sender; no author or sender defined.")

        return self.sender or self.author[0]

    @property
    def recipients(self):
        return AddressList(self.to + self.cc + self.bcc)

    def _mime_document(self, plain, rich=None):
        if not rich:
            message = plain

        else:
            message = MIMEMultipart('alternative')
            message.attach(plain)

            if not self.embedded:
                message.attach(rich)

            else:
                embedded = MIMEMultipart('related')
                embedded.attach(rich)
                for attachment in self.embedded:
                    embedded.attach(attachment)
                message.attach(embedded)

        if self.attachments:
            attachments = MIMEMultipart()
            attachments.attach(message)
            for attachment in self.attachments:
                attachments.attach(attachment)
            message = attachments

        return message

    def _build_date_header_string(self, date_value):
        """Gets the date_value (may be None, basestring, float or
        datetime.datetime instance) and returns a valid date string as per
        RFC 2822."""
        if isinstance(date_value, datetime):
            date_value = time.mktime(date_value.timetuple())
        if not isinstance(date_value, basestring):
            date_value = formatdate(date_value, localtime=True)
        # Encode it here to avoid this:
        # Date: =?utf-8?q?Sat=2C_01_Sep_2012_13=3A08=3A29_-0300?=
        return date_value.encode('ascii')

    def _build_header_list(self, author, sender):
        date_value = self._build_date_header_string(self.date)
        headers = [
                ('Sender', sender),
                ('From', author),
                ('Reply-To', self.reply),
                ('Subject', self.subject),
                ('Date', date_value),
                ('To', self.to),
                ('Cc', self.cc),
                ('Disposition-Notification-To', self.notify),
                ('Organization', self.organization),
                ('X-Priority', self.priority),
            ]

        if self.brand:
            headers.extend([
                    ('X-Mailer', "marrow.mailer {0}".format(release.version))
                ])

        if isinstance(self.headers, dict):
            for key in self.headers:
                headers.append((key, self.headers[key]))

        else:
            headers.extend(self.headers)

        return headers

    def _add_headers_to_message(self, message, headers):
        for header in headers:
            if header[1] is None or (isinstance(header[1], list) and not header[1]):
                continue

            name, value = header

            if isinstance(value, Address):
                value = value.encode(self.encoding)
            elif isinstance(value, AddressList):
                value = value.encode(self.encoding)

            if isinstance(value, unicode):
                value = Header(value, self.encoding)
            else:
                value = Header(value)

            message[name] = value

    @property
    def mime(self):
        """Produce the final MIME message."""
        author = self.author
        sender = self.sender

        if not author:
            raise ValueError("You must specify an author.")

        if not self.subject:
            raise ValueError("You must specify a subject.")

        if len(self.recipients) == 0:
            raise ValueError("You must specify at least one recipient.")

        if not self.plain:
            raise ValueError("You must provide plain text content.")

        # DISCUSS: Take the first author, or raise this error?
        # if len(author) > 1 and len(sender) == 0:
        #     raise ValueError('If there are multiple authors of message, you must specify a sender!')

        # if len(sender) > 1:
        #     raise ValueError('You must not specify more than one sender!')

        if not self._dirty and self._processed:
            return self._mime

        self._processed = False

        plain = MIMEText(self._callable(self.plain), 'plain', self.encoding)

        rich = None
        if self.rich:
            rich = MIMEText(self._callable(self.rich), 'html', self.encoding)

        message = self._mime_document(plain, rich)
        headers = self._build_header_list(author, sender)
        self._add_headers_to_message(message, headers)

        self._mime = message
        self._processed = True
        self._dirty = False

        return message

    def attach(self, name, data=None, maintype=None, subtype=None,
        inline=False):
        """Attach a file to this message.

        :param name: Path to the file to attach if data is None, or the name
                     of the file if the ``data`` argument is given
        :param data: Contents of the file to attach, or None if the data is to
                     be read from the file pointed to by the ``name`` argument
        :type data: bytes or a file-like object
        :param maintype: First part of the MIME type of the file -- will be
                         automatically guessed if not given
        :param subtype: Second part of the MIME type of the file -- will be
                        automatically guessed if not given
        :param inline: Whether to set the Content-Disposition for the file to
                       "inline" (True) or "attachment" (False)
        """
        self._dirty = True

        if not maintype:
            maintype, _ = guess_type(name)
            if not maintype:
                maintype, subtype = 'application', 'octet-stream'
            else:
                maintype, _, subtype = maintype.partition('/')

        part = MIMENonMultipart(maintype, subtype)

        if data is None:
            with open(name, 'rb') as fp:
                part.set_payload(fp.read())
            name = os.path.basename(name)
        elif isinstance(data, bytes):
            part.set_payload(data)
        elif hasattr(data, 'read'):
            part.set_payload(data.read())
        else:
            raise TypeError("Unable to read attachment contents")

        if inline:
            part.add_header('Content-Disposition', 'inline', filename=name)
            part.add_header('Content-ID', '<%s>' % name)
            self.embedded.append(part)
        else:
            part.add_header('Content-Disposition', 'attachment', filename=name)
            self.attachments.append(part)

    def embed(self, name, data=None):
        """Attach an image file and prepare for HTML embedding.

        This method should only be used to embed images.

        :param name: Path to the image to embed if data is None, or the name
                     of the file if the ``data`` argument is given
        :param data: Contents of the image to embed, or None if the data is to
                     be read from the file pointed to by the ``name`` argument
        """
        if data is None:
            with open(name, 'rb') as fp:
                data = fp.read()
            name = os.path.basename(name)
        elif isinstance(data, bytes):
            pass
        elif hasattr(data, 'read'):
            data = data.read()
        else:
            raise TypeError("Unable to read image contents")

        subtype = imghdr.what(None, data)
        self.attach(name, data, 'image', subtype, True)

    @staticmethod
    def _callable(var):
        if hasattr(var, '__call__'):
            return var()

        return var

    def send(self):
        if not self.mailer:
            raise NotImplementedError("Message instance is not bound to " \
                "a Mailer. Use mailer.send() instead.")
        return self.mailer.send(self)

########NEW FILE########
__FILENAME__ = release
# encoding: utf-8

"""Release information about Marrow Mail."""

from collections import namedtuple


__all__ = ['version_info', 'version']


version_info = namedtuple('version_info', ('major', 'minor', 'micro', 'releaselevel', 'serial'))(4, 0, 0, 'final', 0)

version = ".".join([str(i) for i in version_info[:3]]) + ((version_info.releaselevel[0] + str(version_info.serial)) if version_info.releaselevel != 'final' else '')

########NEW FILE########
__FILENAME__ = gae
# encoding: utf-8

from google.appengine.api import mail


__all__ = ['AppEngineTransport']

log = __import__('logging').getLogger(__name__)



class AppEngineTransport(object): # pragma: no cover
    __slots__ = ('ephemeral', )
    
    def __init__(self, config):
        pass
    
    def startup(self):
        pass
    
    def deliver(self, message):
        msg = mail.EmailMessage(
                sender = message.author.encode(),
                to = [to.encode() for to in message.to],
                subject = message.subject,
                body = message.plain
            )
        
        if message.cc:
            msg.cc = [cc.encode() for cc in message.cc]
        
        if message.bcc:
            msg.bcc = [bcc.encode() for bcc in message.bcc]
        
        if message.reply:
            msg.reply_to = message.reply.encode()
        
        if message.rich:
            msg.html = message.rich
        
        if message.attachments:
            attachments = []
            
            for attachment in message.attachments:
                attachments.append((
                        attachment['Content-Disposition'].partition(';')[2],
                        attachment.get_payload(True)
                    ))
            
            msg.attachments = attachments
        
        msg.send()
    
    def shutdown(self):
        pass

########NEW FILE########
__FILENAME__ = imap
# encoding: utf-8

import imaplib

from datetime import datetime

from marrow.mailer.exc import MailConfigurationException, TransportException, MessageFailedException


__all__ = ['IMAPTransport']

log = __import__('logging').getLogger(__name__)



class IMAPTransport(object): # pragma: no cover
    __slots__ = ('ephemeral', 'host', 'ssl', 'port', 'username', 'password', 'folder', 'connection')
    
    def __init__(self, config):
        if not 'host' in config:
            raise MailConfigurationException('No server configured for IMAP.')
        
        self.host = config.get('host', None)
        self.ssl = config.get('ssl', False)
        self.port = config.get('port', 993 if self.ssl else 143)
        self.username = config.get('username', None)
        self.password = config.get('password', None)
        self.folder = config.get('folder', "INBOX")
    
    def startup(self):
        Protocol = imaplib.IMAP4_SSL if self.ssl else imaplib.IMAP4
        self.connection = Protocol(self.host, self.port)
        
        if self.username:
            result = self.connection.login(self.username, self.password)
            
            if result[0] != b'OK':
                raise TransportException("Unable to authenticate with IMAP server.")
    
    def deliver(self, message):
        result = self.connection.append(
                self.folder,
                '', # TODO: Set message urgency / flagged state.
                message.date.timetuple() if message.date else datetime.now(),
                bytes(message)
            )
        
        if result[0] != b'OK':
            raise MessageFailedException("\n".join(result[1]))
    
    def shutdown(self):
        self.connection.logout()

########NEW FILE########
__FILENAME__ = log
# encoding: utf-8


__all__ = ['LoggingTransport']

log = __import__('logging').getLogger(__name__)



class LoggingTransport(object):
    __slots__ = ('ephemeral', 'log')
    
    def __init__(self, config):
        self.log = log if 'name' not in config else __import__('logging').getLogger(config.name)
    
    def startup(self):
        log.debug("Logging transport starting.")
    
    def deliver(self, message):
        msg = str(message)
        self.log.info("DELIVER %s %s %d %r %r", message.id, message.date.isoformat(),
            len(msg), message.author, message.recipients)
        self.log.critical(msg)
    
    def shutdown(self):
        log.debug("Logging transport stopping.")

########NEW FILE########
__FILENAME__ = maildir
# encoding: utf-8

import mailbox


__all__ = ['MaildirTransport']

log = __import__('logging').getLogger(__name__)



class MaildirTransport(object):
    """A modern UNIX maildir on-disk file delivery transport."""
    
    __slots__ = ('ephemeral', 'box', 'directory', 'folder', 'create', 'separator')
    
    def __init__(self, config):
        self.box = None
        self.directory = config.get('directory', None) # maildir directory
        self.folder = config.get('folder', None) # maildir folder to deliver to
        self.create = config.get('create', False) # create folder if missing
        self.separator = config.get('separator', '!')
        
        if not self.directory:
            raise ValueError("You must specify the path to a maildir tree to write messages to.")
    
    def startup(self):
        self.box = mailbox.Maildir(self.directory)
        
        if self.folder:
            try:
                folder = self.box.get_folder(self.folder)
            
            except mailbox.NoSuchMailboxError:
                if not self.create: # pragma: no cover
                    raise # TODO: Raise appropraite internal exception.
                
                folder = self.box.add_folder(self.folder)
            
            self.box = folder
        
        self.box.colon = self.separator
    
    def deliver(self, message):
        # TODO: Create an ID based on process and thread IDs.
        # Current bhaviour may allow for name clashes in multi-threaded.
        self.box.add(mailbox.MaildirMessage(str(message)))
    
    def shutdown(self):
        self.box = None

########NEW FILE########
__FILENAME__ = mbox
# encoding: utf-8

import mailbox


__all__ = ['MailboxTransport']

log = __import__('logging').getLogger(__name__)



class MailboxTransport(object):
    """A classic UNIX mailbox on-disk file delivery transport.
    
    Due to the file locking inherent in this format, using a background
    delivery mechanism (such as a Futures thread pool) makes no sense.
    """
    
    __slots__ = ('ephemeral', 'box', 'filename')
    
    def __init__(self, config):
        self.box = None
        self.filename = config.get('file', None)
        
        if not self.filename:
            raise ValueError("You must specify an mbox file name to write messages to.")
    
    def startup(self):
        self.box = mailbox.mbox(self.filename)
    
    def deliver(self, message):
        self.box.lock()
        self.box.add(mailbox.mboxMessage(str(message)))
        self.box.unlock()
    
    def shutdown(self):
        if self.box is None:
            return
        
        self.box.close()
        self.box = None

########NEW FILE########
__FILENAME__ = mock
# encoding: utf-8

import random

from marrow.mailer.exc import TransportFailedException, TransportExhaustedException

from marrow.util.bunch import Bunch


__all__ = ['MockTransport']

log = __import__('logging').getLogger(__name__)



class MockTransport(object):
    """A no-op dummy transport.
    
    Accepts two configuration directives:
    
     * success - probability of successful delivery
     * failure - probability of failure
     * exhaustion - probability of exhaustion
    
    All are represented as percentages between 0.0 and 1.0, inclusive.
    (Setting failure or exhaustion to 1.0 means every delivery will fail
    badly; do not do this except under controlled, unit testing scenarios!)
    """
    
    __slots__ = ('ephemeral', 'config')
    
    def __init__(self, config):
        base = {'success': 1.0, 'failure': 0.0, 'exhaustion': 0.0}
        base.update(dict(config))
        self.config = Bunch(base)
    
    def startup(self):
        pass
    
    def deliver(self, message):
        """Concrete message delivery."""
        
        config = self.config
        success = config.success
        failure = config.failure
        exhaustion = config.exhaustion
        
        if getattr(message, 'die', False):
            1/0
        
        if failure:
            chance = random.randint(0,100001) / 100000.0
            if chance < failure:
                raise TransportFailedException("Mock failure.")
        
        if exhaustion:
            chance = random.randint(0,100001) / 100000.0
            if chance < exhaustion:
                raise TransportExhaustedException("Mock exhaustion.")
        
        if success == 1.0:
            return True
        
        chance = random.randint(0,100001) / 100000.0
        if chance <= success:
            return True
        
        return False
    
    def shutdown(self):
        pass

########NEW FILE########
__FILENAME__ = sendmail
# encoding: utf-8

from subprocess import Popen, PIPE

from marrow.mailer.exc import MessageFailedException


__all__ = ['SendmailTransport']

log = __import__('logging').getLogger(__name__)



class SendmailTransport(object): # pragma: no cover
    __slots__ = ('ephemeral', 'executable')

    def __init__(self, config):
        self.executable = config.get('path', '/usr/sbin/sendmail')

    def startup(self):
        pass

    def deliver(self, message):
        # TODO: Utilize -F full_name (sender full name), -f sender (envelope sender), -V envid (envelope ID), and space-separated BCC recipients
        # TODO: Record the output of STDOUT and STDERR to capture errors.
        proc = Popen('%s -t -i' % (self.executable,), shell=True, stdin=PIPE)
        proc.communicate(bytes(message))
        proc.stdin.close()
        if proc.wait() != 0:
            raise MessageFailedException("Status code %d." % (proc.returncode, ))

    def shutdown(self):
        pass

########NEW FILE########
__FILENAME__ = ses
# encoding: utf-8

# TODO: Port: https://github.com/pankratiev/python-amazon-ses-api/blob/master/amazon_ses.py

try:
    from boto.ses import SESConnection

except ImportError:
    raise ImportError("You must install the boto package to deliver mail via Amazon SES.")


__all__ = ['AmazonTransport']

log = __import__('logging').getLogger(__name__)



class AmazonTransport(object): # pragma: no cover
    __slots__ = ('ephemeral', 'id', 'key', 'host', 'connection')
    
    def __init__(self, config):
        self.id = config.get('id')
        self.key = config.get('key')
        self.host = config.get('host', "email.us-east-1.amazonaws.com")
        self.connection = None
    
    def startup(self):
        self.connection = SESConnection(
                aws_access_key_id = self.id,
                aws_secret_access_key = self.key,
                host = self.host
            )
    
    def deliver(self, message):
        try:
            response = self.connection.send_raw_email(
                    source = message.author.encode(),
                    destinations = message.recipients.encode(),
                    raw_message = str(message)
                )
            
            return (
                    response['SendRawEmailResponse']['SendRawEmailResult']['MessageId'],
                    response['SendRawEmailResponse']['ResponseMetadata']['RequestId']
                )
        
        except SESConnection.ResponseError:
            raise # TODO: Raise appropriate internal exception.
            # ['status', 'reason', 'body', 'request_id', 'error_code', 'error_message']
    
    def shutdown(self):
        if self.connection:
            self.connection.close()
        
        self.connection = None

########NEW FILE########
__FILENAME__ = smtp
# encoding: utf-8

"""Deliver messages using (E)SMTP."""

import socket

from smtplib import (SMTP, SMTP_SSL, SMTPException, SMTPRecipientsRefused,
                     SMTPSenderRefused, SMTPServerDisconnected)

from marrow.util.convert import boolean
from marrow.util.compat import native

from marrow.mailer.exc import TransportExhaustedException, TransportException, TransportFailedException, MessageFailedException


log = __import__('logging').getLogger(__name__)



class SMTPTransport(object):
    """An (E)SMTP pipelining transport."""
    
    __slots__ = ('ephemeral', 'host', 'tls', 'certfile', 'keyfile', 'port', 'local_hostname', 'username', 'password', 'timeout', 'debug', 'pipeline', 'connection', 'sent')
    
    def __init__(self, config):
        self.host = native(config.get('host', '127.0.0.1'))
        self.tls = config.get('tls', 'optional')
        self.certfile = config.get('certfile', None)
        self.keyfile = config.get('keyfile', None)
        self.port = int(config.get('port', 465 if self.tls == 'ssl' else 25))
        self.local_hostname = native(config.get('local_hostname', '')) or None
        self.username = native(config.get('username', '')) or None
        self.password = native(config.get('password', '')) or None
        self.timeout = config.get('timeout', None)
        
        if self.timeout:
            self.timeout = int(self.timeout)
        
        self.debug = boolean(config.get('debug', False))
        
        self.pipeline = config.get('pipeline', None)
        if self.pipeline not in (None, True, False):
            self.pipeline = int(self.pipeline)
        
        self.connection = None
        self.sent = 0
    
    def startup(self):
        if not self.connected:
            self.connect_to_server()
    
    def shutdown(self):
        if self.connected:
            log.debug("Closing SMTP connection")
            
            try:
                try:
                    self.connection.quit()
                
                except SMTPServerDisconnected: # pragma: no cover
                    pass
                
                except (SMTPException, socket.error): # pragma: no cover
                    log.exception("Unhandled error while closing connection.")
            
            finally:
                self.connection = None
    
    def connect_to_server(self):
        if self.tls == 'ssl': # pragma: no cover
            connection = SMTP_SSL(local_hostname=self.local_hostname, keyfile=self.keyfile,
                                  certfile=self.certfile, timeout=self.timeout)
        else:
            connection = SMTP(local_hostname=self.local_hostname, timeout=self.timeout)

        log.info("Connecting to SMTP server %s:%s", self.host, self.port)
        connection.set_debuglevel(self.debug)
        connection.connect(self.host, self.port)

        # Do TLS handshake if configured
        connection.ehlo()
        if self.tls in ('required', 'optional', True):
            if connection.has_extn('STARTTLS'): # pragma: no cover
                connection.starttls(self.keyfile, self.certfile)
            elif self.tls == 'required':
                raise TransportException('TLS is required but not available on the server -- aborting')

        # Authenticate to server if necessary
        if self.username and self.password:
            log.info("Authenticating as %s", self.username)
            connection.login(self.username, self.password)

        self.connection = connection
        self.sent = 0
    
    @property
    def connected(self):
        return getattr(self.connection, 'sock', None) is not None

    def deliver(self, message):
        if not self.connected:
            self.connect_to_server()
        
        try:
            self.send_with_smtp(message)
        
        finally:
            if not self.pipeline or self.sent >= self.pipeline:
                raise TransportExhaustedException()
    
    def send_with_smtp(self, message):
        sender = bytes(message.envelope)
        recipients = message.recipients.string_addresses
        content = bytes(message)
        
        try:
            self.connection.sendmail(sender, recipients, content)
            self.sent += 1
        
        except SMTPSenderRefused as e:
            # The envelope sender was refused.  This is bad.
            log.error("%s REFUSED %s %s", message.id, e.__class__.__name__, e)
            raise MessageFailedException(str(e))
        
        except SMTPRecipientsRefused as e:
            # All recipients were refused. Log which recipients.
            # This allows you to automatically parse your logs for bad e-mail addresses.
            log.warning("%s REFUSED %s %s", message.id, e.__class__.__name__, e)
            raise MessageFailedException(str(e))
        
        except SMTPServerDisconnected as e: # pragma: no cover
            if message.retries >= 0:
                log.warning("%s DEFERRED %s", message.id, "SMTPServerDisconnected")
                message.retries -= 1
            
            raise TransportFailedException()
        
        except Exception as e: # pragma: no cover
            cls_name = e.__class__.__name__
            log.debug("%s EXCEPTION %s", message.id, cls_name, exc_info=True)
            
            if message.retries >= 0:
                log.warning("%s DEFERRED %s", message.id, cls_name)
                message.retries -= 1
            
            else:
                log.exception("%s REFUSED %s", message.id, cls_name)
                raise TransportFailedException()

########NEW FILE########
__FILENAME__ = validator
# encoding: utf-8
#
# This file was taken from webpyte (r179):
# http://code.google.com/p/webpyte/source/browse/trunk/webpyte/email_validator.py
# According to the docstring, it is licensed as 'public domain'
# 
# Modifications:
# * Wed Mar 25 2009 Felix Schwarz
# - Removed 'from __future__ import absolute_import to stay compatible with Python 2.3/2.4
# * Fri Mar 27 2009 Felix Schwarz
# - Disabled DNS server discovery on module import
# - added __all__ declaration
# - modified domain validator so that domains without second-level domain will
#   be accepted as well.
#

"""A method of validating e-mail addresses and mail domains.

This module aims to provide the ultimate functions for:
* domain validation, and
* e-mail validation.

Why not just use a regular expression?
======================================
http://haacked.com/archive/2007/08/21/i-knew-how-to-validate-an-email-address-until-i.aspx

There are many regular expressions out there for this. The "perfect one" is
several KB long and therefore unmaintainable (Perl people wrote it...).

This is 2009 and domain rules are changing too. Impossible domain names have
become possible, international domain names are real...

So validating an e-mail address is more complex than you might think. Take a
look at some of the rules:
http://en.wikipedia.org/wiki/E-mail_address#RFC_specification

How to do it then?
==================
I believe the solution should combine simple regular expressions with
imperative programming.

E-mail validation is also dependent on the robustness principle:
"Be conservative in what you do, be liberal in what you accept from others."
http://en.wikipedia.org/wiki/Postel%27s_law

This module recognizes that e-mail validation can be done in several different
ways, according to purpose:

1) Most of the time you just want validation according to the standard rules.
So just say:  v = EmailValidator()

2) If you are creating e-mail addresses for your server or your organization,
you might need to satisfy a stricter policy such as "dash is not allowed in
email addresses". The EmailValidator constructor accepts a *local_part_chars*
argument to help build the right regular expression for you.
Example:  v = EmailValidator(local_part_chars='.-+_')

3) What about typos? An erroneous dot at the end of a typed email is typical.
Other common errors with the dots revolve around the @: user@.domain.com.
These typing mistakes can be automatically corrected, saving you from doing
it manually. For this you use the *fix* flag when instantiating a validator:

    d = DomainValidator(fix=True)
    domain, error_message = d.validate('.supercalifragilistic.com.br')
    if error_message:
        print 'Invalid domain: ' + domain
    else:
        print 'Valid domain: ' + domain

4) TODO: Squash the bugs in this feature!
Paranoid people may wish to verify that the informed domain actually exists.
For that you can pass a *lookup_dns='a'* argument to the constructor, or even
*lookup_dns='mx'* to verify that the domain actually has e-mail servers.
To use this feature, you need to install the *pydns* library:

     easy_install -UZ pydns

How to use
==========

The validating methods return a tuple (email, error_msg).
*email* is the trimmed and perhaps fixed email.
*error_msg* is an empty string when the e-mail is valid.

Typical usage is:

    v = EmailValidator() # or EmailValidator(fix=True)
    email = raw_input('Type an email: ')
    email, err = v.validate(email)
    if err:
        print 'Error: ' + err
    else:
        print 'E-mail is valid: ' + email  # the email, corrected

There is also an EmailHarvester class to collect e-mail addresses from any text.

Authors: Nando Florestan, Marco Ferreira
Code written in 2009 and donated to the public domain.
"""

import re

__all__ = ['ValidationException', 'BaseValidator', 'DomainValidator', 'EmailValidator', 'EmailHarvester']


class ValidationException(ValueError):
    pass


class BaseValidator(object):
    def validate_or_raise(self, *a, **k):
        """Some people would condemn this whole module screaming:
        "Don't return success codes, use exceptions!"
        This method allows them to be happy, too.
        """
        
        validate, err = self.validate(*a, **k)
        
        if err:
            raise ValidationException(err)
        
        return validate


class DomainValidator(BaseValidator):
    """A domain name validator that is ready for internationalized domains.
    
    http://en.wikipedia.org/wiki/Internationalized_domain_name
    http://en.wikipedia.org/wiki/Top-level_domain
    """
    # non_international_regex = re.compile(r"^[a-z0-9][a-z0-9\.\-]*\.[a-z]+$",
    #domain_pattern = r'[\w][\w\.\-]+?\.[\w]+'
    # fs: New domain regex that accepts domains without second-level domain also
    domain_pattern = r'[\w]+([\w\.\-]+\w)?'
    domain_regex = \
        re.compile('^' + domain_pattern + '$', re.IGNORECASE | re.UNICODE)

    # OpenDNS has a feature that bites us. If you are using OpenDNS, and you
    # type in your browser a domain that does not exist, OpenDNS catches that
    # and presents a page. "Did you mean www.hovercraft.eels?"
    # For us, this feature appears as a false positive when looking up the
    # DNS server. So we try to work around it:
    false_positive_ips = ['208.67.217.132']

    def __init__(self, fix=False, lookup_dns=None):
        self.fix = fix
        
        if lookup_dns:
            try:
                import DNS
            except ImportError: # pragma: no cover
                raise ImportError("To enable DNS lookup of domains install the PyDNS package.")
            
            lookup_dns = lookup_dns.lower()
            if lookup_dns not in ('a', 'mx'):
                raise RuntimeError("Not a valid *lookup_dns* value: " + lookup_dns)
        
        self._lookup_dns = lookup_dns

    def _apply_common_rules(self, part, maxlength):
        """This method contains the rules that must be applied to both the
        domain and the local part of the e-mail address.
        """
        part = part.strip()
        
        if self.fix:
            part = part.strip('.')
        
        if not part:
            return part, 'It cannot be empty.'
        
        if len(part) > maxlength:
            return part, 'It cannot be longer than %i chars.' % maxlength
        
        if part[0] == '.':
            return part, 'It cannot start with a dot.'
        
        if part[-1] == '.':
            return part, 'It cannot end with a dot.'
        
        if '..' in part:
            return part, 'It cannot contain consecutive dots.'
        
        return part, ''

    def validate_domain(self, part):
        part, err = self._apply_common_rules(part, maxlength=255)
        
        if err:
            return part, 'Invalid domain: %s' % err
        
        if not self.domain_regex.search(part):
            return part, 'Invalid domain.'
        
        if self._lookup_dns and not self.lookup_domain(part):
            return part, 'Domain does not seem to exist.'
        
        return part.lower(), ''

    validate = validate_domain

    # TODO: As an option, DNS lookup on the domain:
    # http://mail.python.org/pipermail/python-list/2008-July/497997.html

    def lookup_domain(self, domain, lookup_record=None, **kw):
        """Looks up the DNS record for *domain* and returns:
        
        * None if it does not exist,
        * The IP address if looking up the "A" record, or
        * The list of hosts in the "MX" record.
        
        The return value, if treated as a boolean, says whether a domain exists.
        
        You can pass "a" or "mx" as the *lookup_record* parameter. Otherwise,
        the *lookup_dns* parameter from the constructor is used.
        "a" means verify that the domain exists.
        "mx" means verify that the domain exists and specifies mail servers.
        """
        import DNS
        
        lookup_record = lookup_record.lower() if lookup_record else self._lookup_dns
        
        if lookup_record not in ('a', 'mx'):
            raise RuntimeError("Not a valid lookup_record value: " + lookup_record)
        
        if lookup_record == "a":
            request = DNS.Request(domain, **kw)
            
            try:
                answers = request.req().answers
            
            except (DNS.Lib.PackError, UnicodeError):
                # A part of the domain name is longer than 63.
                return False
            
            if not answers:
                return False
            
            result = answers[0]['data'] # This is an IP address
            
            if result in self.false_positive_ips: # pragma: no cover
                return False
            
            return result
        
        try:
            return DNS.mxlookup(domain)
        
        except UnicodeError:
            pass
        
        return False


class EmailValidator(DomainValidator):
    # TODO: Implement all rules!
    # http://tools.ietf.org/html/rfc3696
    # http://en.wikipedia.org/wiki/E-mail_address#RFC_specification
    # TODO: Local part in quotes?
    # TODO: Quoted-printable local part?

    def __init__(self, local_part_chars=".-+_!#$%&'/=`|~?^{}*", **k):
        super(EmailValidator, self).__init__(**k)
        # Add a backslash before the dash so it can go into the regex:
        self.local_part_pattern = '[a-z0-9' + local_part_chars.replace('-', r'\-') + ']+'
        # Regular expression for validation:
        self.local_part_regex = re.compile('^' + self.local_part_pattern + '$', re.IGNORECASE)

    def validate_local_part(self, part):
        part, err = self._apply_common_rules(part, maxlength=64)
        if err:
            return part, 'Invalid local part: %s' % err
        if not self.local_part_regex.search(part):
            return part, 'Invalid local part.'
        return part, ''
        # We don't go lowercase because the local part is case-sensitive.

    def validate_email(self, email):
        if not email:
            return email, 'The e-mail is empty.'
        
        parts = email.split('@')
        
        if len(parts) != 2:
            return email, 'An email address must contain a single @'
        
        local, domain = parts
        
        # Validate the domain
        domain, err = self.validate_domain(domain)
        if err:
            return email, "The e-mail has a problem to the right of the @: %s" % err
        
        # Validate the local part
        local, err = self.validate_local_part(local)
        if err:
            return email, "The email has a problem to the left of the @: %s" % err
        
        # It is valid
        return local + '@' + domain, ''

    validate = validate_email


class EmailHarvester(EmailValidator):
    def __init__(self, *a, **k):
        super(EmailHarvester, self).__init__(*a, **k)
        # Regular expression for harvesting:
        self.harvest_regex = \
            re.compile(self.local_part_pattern + '@' + self.domain_pattern,
                       re.IGNORECASE | re.UNICODE)

    def harvest(self, text):
        """Iterator that yields the e-mail addresses contained in *text*."""
        for match in self.harvest_regex.finditer(text):
            # TODO: optionally validate before yielding?
            # TODO: keep a list of harvested but not validated?
            yield match.group().replace('..', '.')


# rfc822_specials = '()<>@,;:\\"[]'

# is_address_valid(addr):
# # First we validate the name portion (name@domain)
# c = 0
# while c < len(addr):
#     if addr[c] == '"' and (not c or addr[c - 1] == '.' or addr[c - 1] == '"'):
#         c = c + 1
#         while c < len(addr):
#             if addr[c] == '"': break
#             if addr[c] == '\\' and addr[c + 1] == ' ':
#                 c = c + 2
#                 continue
#             if ord(addr[c]) < 32 or ord(addr[c]) >= 127: return 0
#             c = c + 1
#         else: return 0
#         if addr[c] == '@': break
#         if addr[c] != '.': return 0
#         c = c + 1
#         continue
#     if addr[c] == '@': break
#     if ord(addr[c]) <= 32 or ord(addr[c]) >= 127: return 0
#     if addr[c] in rfc822_specials: return 0
#     c = c + 1
# if not c or addr[c - 1] == '.': return 0
# 
# # Next we validate the domain portion (name@domain)
# domain = c = c + 1
# if domain >= len(addr): return 0
# count = 0
# while c < len(addr):
#     if addr[c] == '.':
#         if c == domain or addr[c - 1] == '.': return 0
#         count = count + 1
#     if ord(addr[c]) <= 32 or ord(addr[c]) >= 127: return 0
#     if addr[c] in rfc822_specials: return 0
#     c = c + 1
# 
# return count >= 1

########NEW FILE########
__FILENAME__ = test_dynamic
# encoding: utf-8

from __future__ import unicode_literals

import logging
import pkg_resources

from functools import partial
from unittest import TestCase
from nose.tools import ok_, eq_, raises
from nose.plugins.skip import Skip, SkipTest

from marrow.mailer.exc import TransportExhaustedException, TransportFailedException, DeliveryFailedException, MessageFailedException
from marrow.mailer.manager.dynamic import DynamicManager, WorkItem


log = logging.getLogger('tests')



class MockFuture(object):
    def __init__(self):
        self.cancelled = False
        self.running = False
        self.exception = None
        self.result = None
        
        super(MockFuture, self).__init__()
    
    def set_running_or_notify_cancel(self):
        if self.cancelled:
            return False
        
        self.running = True
        return True
    
    def set_exception(self, e):
        self.exception = e
    
    def set_result(self, r):
        self.result = r


class TestWorkItem(TestCase):
    calls = list()
    
    def closure(self):
        self.calls.append(True)
        return True
    
    def setUp(self):
        self.f = MockFuture()
        self.wi = WorkItem(self.f, self.closure, (), {})
        
    def test_success(self):
        self.wi.run()
        
        self.assertEquals(self.calls, [True])
        self.assertTrue(self.f.result)
    
    def test_cancelled(self):
        self.f.cancelled = True
        self.wi.run()
        
        self.assertEquals(self.calls, [])
    
    def test_exception(self):
        self.wi.fn = lambda: 1/0
        self.wi.run()
        
        self.assertTrue(isinstance(self.f.exception, ZeroDivisionError))


class ManagerTestCase(TestCase):
    manager = None
    config = dict()
    states = []
    messages = []
    
    class MockTransport(object):
        def __init__(self, states, messages):
            self.ephemeral = False
            self.states = states
            self.messages = messages
        
        def startup(self):
            self.states.append('running')
        
        def deliver(self, message):
            self.messages.append(message)
            
            if isinstance(message, Exception) and ( len(self.messages) < 2 or self.messages[-2] is not message):
                raise message
        
        def shutdown(self):
            self.states.append('stopped')
    
    def setUp(self):
        self.manager = self.manager(self.config, partial(self.MockTransport, self.states, self.messages))
    
    def tearDown(self):
        del self.states[:]
        del self.messages[:]


class TestDynamicManager(ManagerTestCase):
    manager = DynamicManager
    
    def test_startup(self):
        # TODO: Test logging messages.
        self.manager.startup()
        self.assertEquals(self.states, [])
    
    def test_shutdown(self):
        # TODO: Test logging messages.
        self.manager.startup()
        self.manager.shutdown()
        self.assertEquals(self.states, [])
    
    def test_success(self):
        self.manager.startup()
        
        self.manager.deliver("success")
        
        self.assertEquals(self.states, ["running"])
        self.assertEquals(self.messages, ["success"])
        
        self.manager.shutdown()
        self.assertEquals(self.states, ["running", "stopped"])
    
    def test_message_failure(self):
        self.manager.startup()
        
        exc = MessageFailedException()
        
        receipt = self.manager.deliver(exc)
        self.assertRaises(DeliveryFailedException, receipt.result)
        
        self.assertEquals(self.states, ['running', 'stopped'])
        self.assertEquals(self.messages, [exc])
        
        self.manager.shutdown()
        self.assertEquals(self.states, ['running', 'stopped'])
    
    def test_transport_failure(self):
        self.manager.startup()
        
        exc = TransportFailedException()
        
        self.manager.deliver(exc).result()
        
        self.assertEquals(self.states, ['running', 'stopped', 'running'])
        self.assertEquals(self.messages, [exc, exc])
        
        self.manager.shutdown()
        self.assertEquals(self.states, ['running', 'stopped', 'running', 'stopped'])
    
    def test_transport_exhaustion(self):
        self.manager.startup()
        
        exc = TransportExhaustedException()
        
        self.manager.deliver(exc).result()
        
        self.assertEquals(self.states, ['running', 'stopped'])
        self.assertEquals(self.messages, [exc])
        
        self.manager.shutdown()
        self.assertEquals(self.states, ['running', 'stopped'])

########NEW FILE########
__FILENAME__ = test_futures
# encoding: utf-8

from __future__ import unicode_literals

import logging
import pkg_resources

from functools import partial
from unittest import TestCase
from nose.tools import ok_, eq_, raises
from nose.plugins.skip import Skip, SkipTest

from marrow.mailer.exc import TransportExhaustedException, TransportFailedException, DeliveryFailedException, MessageFailedException
from marrow.mailer.manager.futures import FuturesManager


log = logging.getLogger('tests')



class ManagerTestCase(TestCase):
    manager = None
    config = dict()
    states = []
    messages = []
    
    class MockTransport(object):
        def __init__(self, states, messages):
            self.ephemeral = False
            self.states = states
            self.messages = messages
        
        def startup(self):
            self.states.append('running')
        
        def deliver(self, message):
            self.messages.append(message)
            
            if isinstance(message, Exception) and ( len(self.messages) < 2 or self.messages[-2] is not message):
                raise message
        
        def shutdown(self):
            self.states.append('stopped')
    
    def setUp(self):
        self.manager = self.manager(self.config, partial(self.MockTransport, self.states, self.messages))
    
    def tearDown(self):
        del self.states[:]
        del self.messages[:]


class TestImmediateManager(ManagerTestCase):
    manager = FuturesManager
    
    def test_startup(self):
        # TODO: Test logging messages.
        self.manager.startup()
        self.assertEquals(self.states, [])
    
    def test_shutdown(self):
        # TODO: Test logging messages.
        self.manager.startup()
        self.manager.shutdown()
        self.assertEquals(self.states, [])
    
    def test_success(self):
        self.manager.startup()
        
        self.manager.deliver("success")
        
        self.assertEquals(self.states, ["running"])
        self.assertEquals(self.messages, ["success"])
        
        self.manager.shutdown()
        self.assertEquals(self.states, ["running", "stopped"])
    
    def test_message_failure(self):
        self.manager.startup()
        
        exc = MessageFailedException()
        
        receipt = self.manager.deliver(exc)
        self.assertRaises(DeliveryFailedException, receipt.result)
        
        self.assertEquals(self.states, ['running', 'stopped'])
        self.assertEquals(self.messages, [exc])
        
        self.manager.shutdown()
        self.assertEquals(self.states, ['running', 'stopped'])
    
    def test_transport_failure(self):
        self.manager.startup()
        
        exc = TransportFailedException()
        
        self.manager.deliver(exc).result()
        
        self.assertEquals(self.states, ['running', 'stopped', 'running'])
        self.assertEquals(self.messages, [exc, exc])
        
        self.manager.shutdown()
        self.assertEquals(self.states, ['running', 'stopped', 'running', 'stopped'])
    
    def test_transport_exhaustion(self):
        self.manager.startup()
        
        exc = TransportExhaustedException()
        
        self.manager.deliver(exc).result()
        
        self.assertEquals(self.states, ['running', 'stopped'])
        self.assertEquals(self.messages, [exc])
        
        self.manager.shutdown()
        self.assertEquals(self.states, ['running', 'stopped'])

########NEW FILE########
__FILENAME__ = test_immediate
# encoding: utf-8

from __future__ import unicode_literals

import logging
import pkg_resources

from functools import partial
from unittest import TestCase
from nose.tools import ok_, eq_, raises
from nose.plugins.skip import Skip, SkipTest

from marrow.mailer.exc import TransportExhaustedException, TransportFailedException, DeliveryFailedException, MessageFailedException
from marrow.mailer.manager.immediate import ImmediateManager


log = logging.getLogger('tests')



class ManagerTestCase(TestCase):
    manager = None
    config = dict()
    states = []
    messages = []
    
    class MockTransport(object):
        def __init__(self, states, messages):
            self.ephemeral = False
            self.states = states
            self.messages = messages
        
        def startup(self):
            self.states.append('running')
        
        def deliver(self, message):
            self.messages.append(message)
            
            if isinstance(message, Exception) and ( len(self.messages) < 2 or self.messages[-2] is not message):
                raise message
        
        def shutdown(self):
            self.states.append('stopped')
    
    def setUp(self):
        self.manager = ImmediateManager(self.config, partial(self.MockTransport, self.states, self.messages))
    
    def tearDown(self):
        del self.states[:]
        del self.messages[:]


class TestImmediateManager(ManagerTestCase):
    manager = ImmediateManager
    
    def test_startup(self):
        # TODO: Test logging messages.
        self.manager.startup()
        self.assertEquals(self.states, [])
    
    def test_shutdown(self):
        # TODO: Test logging messages.
        self.manager.startup()
        self.manager.shutdown()
        self.assertEquals(self.states, [])
    
    def test_success(self):
        self.manager.startup()
        
        self.manager.deliver("success")
        
        self.assertEquals(self.states, ["running"])
        self.assertEquals(self.messages, ["success"])
        
        self.manager.shutdown()
        self.assertEquals(self.states, ["running", "stopped"])
    
    def test_message_failure(self):
        self.manager.startup()
        
        exc = MessageFailedException()
        
        self.assertRaises(DeliveryFailedException, self.manager.deliver, exc)
        
        self.assertEquals(self.states, ['running', 'stopped'])
        self.assertEquals(self.messages, [exc])
        
        self.manager.shutdown()
        self.assertEquals(self.states, ['running', 'stopped'])
    
    def test_transport_failure(self):
        self.manager.startup()
        
        exc = TransportFailedException()
        
        self.manager.deliver(exc)
        
        self.assertEquals(self.states, ['running', 'stopped', 'running'])
        self.assertEquals(self.messages, [exc, exc])
        
        self.manager.shutdown()
        self.assertEquals(self.states, ['running', 'stopped', 'running', 'stopped'])
    
    def test_transport_exhaustion(self):
        self.manager.startup()
        
        exc = TransportExhaustedException()
        
        self.manager.deliver(exc)
        
        self.assertEquals(self.states, ['running', 'stopped'])
        self.assertEquals(self.messages, [exc])
        
        self.manager.shutdown()
        self.assertEquals(self.states, ['running', 'stopped'])

########NEW FILE########
__FILENAME__ = test_addresses
# encoding: utf-8
"""Test the TurboMail Message class."""

from __future__ import unicode_literals

from nose.tools import raises, eq_, assert_raises

from marrow.mailer.address import Address, AddressList, AutoConverter
from marrow.util.compat import unicode


class TestAddress(object):
    def test_punycode(self):
        addr = Address('Foo', 'foo@exámple.test')
        eq_(b'Foo <foo@xn--exmple-qta.test>', bytes(addr))
    
    def test_bytestring(self):
        addr = Address('Foo <foo@exámple.test>'.encode('utf-8'))
        eq_(b'Foo <foo@xn--exmple-qta.test>', bytes(addr))
    
    def test_address_from_addresslist(self):
        email = 'foo@example.com'
        addr = Address(AddressList([Address(email)]))
        eq_(email, unicode(addr))
    
    @raises(ValueError)
    def test_address_from_addresslist_limit_0(self):
        email = 'foo@example.com'
        addr = Address(AddressList())
    
    @raises(ValueError)
    def test_address_from_addresslist_limit_2(self):
        email = 'foo@example.com'
        addr = Address(AddressList([Address(email), Address(email)]))
    
    def test_initialization_with_tuple(self):
        name = 'Foo'
        emailaddress = 'foo@example.com'
        address = Address((name, emailaddress))
        eq_('%s <%s>' % (name, emailaddress), unicode(address))
    
    def test_initialization_with_string(self):
        emailaddress = 'foo@example.com'
        address = Address(emailaddress)
        eq_(emailaddress, unicode(address))
    
    def test_initialization_with_named_string(self):
        emailaddress = 'My Name <foo@example.com>'
        address = Address(emailaddress)
        eq_(emailaddress, unicode(address))
    
    @raises(TypeError)
    def test_invalid_initialization(self):
        Address(123)
    
    def test_compare_address(self):
        addr1 = Address('foo@example.com')
        addr2 = Address(' foo@example.com  ')
        eq_(addr1, addr2)
    
    def test_compare_unicode(self):
        addr = Address('foo@example.com')
        eq_(addr, 'foo@example.com')
    
    def test_compare_bytestring(self):
        addr = Address('foo@example.com')
        eq_(addr, b'foo@example.com')
    
    def test_compare_tuple(self):
        addr = Address('foo', 'foo@example.com')
        eq_(addr, ('foo', 'foo@example.com'))
    
    @raises(NotImplementedError)
    def test_compare_othertype(self):
        addr = Address('foo@example.com')
        addr != 123
    
    def test_len(self):
        addr = Address('foo@example.com')
        eq_(len(addr), len('foo@example.com'))
    
    def test_repr(self):
        addr = Address('foo@example.com')
        eq_(repr(addr), 'Address("foo@example.com")')
    
    def test_validation_truncates_at_second_at_character(self):
        # This is basically due to Python's parseaddr behavior.
        eq_('bad@user', Address('bad@user@example.com'))
    
    @raises(ValueError)
    def test_validation_rejects_addresses_without_at(self):
        # TODO: This may be actually a valid input - some mail systems allow to
        # use only the local part which will be qualified by the MTA
        Address('baduser.example.com')
    
    def test_validation_accepts_uncommon_local_parts(self):
        Address('good-u+s+er@example.com')
        # This address caused 100% CPU load for 50s in Python's (2.5.2) re 
        # module on Fedora Linux 10 (AMD x2 4200).
        Address('steve.blackmill.rules.for.all@bar.blackmill-goldworks.example')
        Address('customer/department=shipping@example.com')
        Address('$A12345@example.com ')
        Address('!def!xyz%abc@example.com ')
        Address('_somename@example.com')
        Address('!$&*-=^`|~#%\'+/?_{}@example.com')
    
    def test_revalidation(self):
        addr = Address('_somename@example.com')
        eq_(addr.valid, True)
    
# TODO: Later
#    def test_validation_accepts_quoted_local_parts(self):
#        Address('"Fred Bloggs"@example.com ')
#        Address('"Joe\\Blow"@example.com ')
#        Address('"Abc@def"@example.com ')
#        Address('"Abc\@def"@example.com')
    
    def test_validation_accepts_multilevel_domains(self):
        Address('foo@my.my.company-name.com')
        Address('blah@foo-bar.example.com')
        Address('blah@duckburg.foo-bar.example.com')
    
    def test_validation_accepts_domain_without_tld(self):
        eq_('user@company', Address('user@company'))
    
    def test_validation_rejects_local_parts_starting_or_ending_with_dot(self):
        assert_raises(ValueError, Address, '.foo@example.com')
        assert_raises(ValueError, Address, 'foo.@example.com')
    
    def test_validation_rejects_double_dot(self):
        assert_raises(ValueError, Address, 'foo..bar@example.com')

# TODO: Later
#    def test_validation_rejects_special_characters_if_not_quoted(self):
#        for char in '()[]\;:,<>':
#            localpart = 'foo%sbar' % char
#            self.assertRaises(ValueError, Address, '%s@example.com' % localpart)
#            Address("%s"@example.com' % localpart)

# TODO: Later
#    def test_validation_accepts_ip_address_literals(self):
#        Address('jsmith@[192.168.2.1]')


class TestAddressList(object):
    """Test the AddressList helper class."""
    
    addresses = AutoConverter('_addresses', AddressList)
    
    def __init__(self):
        self._addresses = AddressList()
    
    def setUp(self):
        self.addresses = AddressList()
    
    def tearDown(self):
        del self.addresses
    
    def test_assignment(self):
        eq_([], self.addresses)
        self.addresses = ['me@example.com']
        eq_(['me@example.com'], self.addresses)
    
    def test_assign_single_address(self):
        address = 'user@example.com'
        self.addresses = address
        
        eq_(self.addresses, [address])
        eq_(unicode(self.addresses), address)
    
    def test_assign_list_of_addresses(self):
        addresses = ['user1@example.com', 'user2@example.com']
        self.addresses = addresses
        eq_(', '.join(addresses), unicode(self.addresses))
        eq_(addresses, self.addresses)
    
    def test_assign_list_of_named_addresses(self):
        addresses = [('Test User 1', 'user1@example.com'), ('Test User 2', 'user2@example.com')]
        self.addresses = addresses
        
        string_addresses = [unicode(Address(*value)) for value in addresses]
        eq_(', '.join(string_addresses), unicode(self.addresses))
        eq_(string_addresses, self.addresses)
    
    def test_assign_item(self):
        self.addresses.append('user1@example.com')
        eq_(self.addresses[0], 'user1@example.com')
        self.addresses[0] = 'user2@example.com'
        
        assert isinstance(self.addresses[0], Address)
        eq_(self.addresses[0], 'user2@example.com')
    
    def test_assign_slice(self):
        self.addresses[:] = ('user1@example.com', 'user2@example.com')
        
        assert isinstance(self.addresses[0], Address)
        assert isinstance(self.addresses[1], Address)
    
    def test_init_accepts_string_list(self):
        addresses = 'user1@example.com, user2@example.com'
        self.addresses = addresses
        
        eq_(addresses, unicode(self.addresses))
    
    def test_init_accepts_tuple(self):
        addresses = AddressList(('foo', 'foo@example.com'))
        eq_([('foo', 'foo@example.com')], addresses)
    
    def test_bytes(self):
        self.addresses = [('User1', 'foo@exámple.test'), ('User2', 'foo@exámple.test')]
        eq_(bytes(self.addresses), b'User1 <foo@xn--exmple-qta.test>, User2 <foo@xn--exmple-qta.test>')
    
    def test_repr(self):
        eq_(repr(self.addresses), 'AddressList()')
        
        self.addresses = ['user1@example.com', 'user2@example.com']
        
        eq_(repr(self.addresses),
            'AddressList("user1@example.com, user2@example.com")')
    
    @raises(ValueError)
    def test_invalid_init(self):
        AddressList(2)
    
    def test_addresses(self):
        self.addresses = [('Test User 1', 'user1@example.com'), ('Test User 2', 'user2@example.com')]
        eq_(self.addresses.addresses, AddressList('user1@example.com, user2@example.com'))
    
    def test_validation_strips_multiline_addresses(self):
        self.addresses = 'user.name+test@info.example.com'
        evil_lines = ['eviluser@example.com', 'To: spammeduser@example.com', 'From: spammeduser@example.com']
        evil_input = '\n'.join(evil_lines)
        self.addresses.append(evil_input)
        eq_(['user.name+test@info.example.com', evil_lines[0]], self.addresses)
    
    def test_return_addresses_as_strings(self):
        self.addresses = 'foo@exámple.test'
        encoded_address = b'foo@xn--exmple-qta.test'
        eq_([encoded_address], self.addresses.string_addresses)

########NEW FILE########
__FILENAME__ = test_core
# encoding: utf-8

"""Test the primary configurator interface, Mailer."""

import logging
import warnings

from unittest import TestCase

from marrow.mailer import Mailer, Delivery, Message
from marrow.mailer.exc import MailerNotRunning
from marrow.mailer.manager.immediate import ImmediateManager
from marrow.mailer.transport.mock import MockTransport

from marrow.util.bunch import Bunch


log = logging.getLogger('tests')


base_config = dict(manager=dict(use='immediate'), transport=dict(use='mock'))



class TestLookup(TestCase):
    def test_load_literal(self):
        self.assertEqual(Mailer._load(ImmediateManager, None), ImmediateManager)
    
    def test_load_dotcolon(self):
        self.assertEqual(Mailer._load('marrow.mailer.manager.immediate:ImmediateManager', None), ImmediateManager)
    
    def test_load_entrypoint(self):
        self.assertEqual(Mailer._load('immediate', 'marrow.mailer.manager'), ImmediateManager)


class TestInitialization(TestCase):
    def test_deprecation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            Delivery(base_config)
            
            self.assertEqual(len(w), 1, "No, or more than one, warning issued.")
            self.assertTrue(issubclass(w[-1].category, DeprecationWarning), "Category of warning is not DeprecationWarning.")
            self.assertTrue('deprecated' in str(w[-1].message), "Warning does not include 'deprecated'.")
            self.assertTrue('Mailer' in str(w[-1].message), "Warning does not include correct class name.")
            self.assertTrue('Delivery' in str(w[-1].message), "Warning does not include old class name.")
    
    def test_use_deprecation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            Mailer(dict(manager='immediate', transport='mock'))
            
            self.assertEqual(len(w), 2, "Too few or too many warnings issued.")
            
            self.assertTrue(issubclass(w[0].category, DeprecationWarning), "Category of warning is not DeprecationWarning.")
            self.assertTrue('deprecated' in str(w[0].message), "Warning does not include 'deprecated'.")
            self.assertTrue('manager.use' in str(w[0].message), "Warning does not include correct use.")
            
            self.assertTrue(issubclass(w[1].category, DeprecationWarning), "Category of warning is not DeprecationWarning.")
            self.assertTrue('deprecated' in str(w[1].message), "Warning does not include 'deprecated'.")
            self.assertTrue('transport.use' in str(w[1].message), "Warning does not include correct use.")
    
    def test_default_manager(self):
        a = Mailer(dict(transport=dict(use='mock')))
        
        self.assertEqual(a.Manager, ImmediateManager)
        self.assertEqual(a.Transport, MockTransport)
    
    def test_standard(self):
        log.info("Testing configuration: %r", dict(base_config))
        a = Mailer(base_config)
        
        self.assertEqual(a.Manager, ImmediateManager)
        self.assertEqual(a.Transport, MockTransport)
    
    def test_bad_manager(self):
        config = dict(manager=dict(use=object()), transport=dict(use='mock'))
        log.info("Testing configuration: %r", dict(config))
        self.assertRaises(TypeError, Mailer, config)
    
    def test_bad_transport(self):
        config = dict(manager=dict(use='immediate'), transport=dict(use=object()))
        log.info("Testing configuration: %r", dict(config))
        self.assertRaises(TypeError, Mailer, config)
    
    def test_repr(self):
        a = Mailer(base_config)
        self.assertEqual(repr(a), "Mailer(manager=ImmediateManager, transport=MockTransport)")
    
    def test_prefix(self):
        config = {
                'mail.manager.use': 'immediate',
                'mail.transport.use': 'mock'
            }
        
        log.info("Testing configuration: %r", dict(config))
        a = Mailer(config, 'mail')
        
        self.assertEqual(a.Manager, ImmediateManager)
        self.assertEqual(a.Transport, MockTransport)
    
    def test_deep_prefix(self):
        config = {
                'marrow.mailer.manager.use': 'immediate',
                'marrow.mailer.transport.use': 'mock'
            }
        
        log.info("Testing configuration: %r", dict(config))
        a = Mailer(config, 'marrow.mailer')
        
        self.assertEqual(a.Manager, ImmediateManager)
        self.assertEqual(a.Transport, MockTransport)
    
    def test_manager_entrypoint_failure(self):
        config = {
                'manager.use': 'immediate2',
                'transport.use': 'mock'
            }
        
        log.info("Testing configuration: %r", dict(config))
        self.assertRaises(LookupError, Mailer, config)
    
    def test_manager_dotcolon_failure(self):
        config = {
                'manager.use': 'marrow.mailer.manager.foo:FooManager',
                'transport.use': 'mock'
            }
        
        log.info("Testing configuration: %r", dict(config))
        self.assertRaises(ImportError, Mailer, config)
        
        config['manager.use'] = 'marrow.mailer.manager.immediate:FooManager'
        log.info("Testing configuration: %r", dict(config))
        self.assertRaises(AttributeError, Mailer, config)
    
    def test_transport_entrypoint_failure(self):
        config = {
                'manager.use': 'immediate',
                'transport.use': 'mock2'
            }
        
        log.info("Testing configuration: %r", dict(config))
        self.assertRaises(LookupError, Mailer, config)
    
    def test_transport_dotcolon_failure(self):
        config = {
                'manager.use': 'immediate',
                'transport.use': 'marrow.mailer.transport.foo:FooTransport'
            }
        
        log.info("Testing configuration: %r", dict(config))
        self.assertRaises(ImportError, Mailer, config)
        
        config['manager.use'] = 'marrow.mailer.transport.mock:FooTransport'
        log.info("Testing configuration: %r", dict(config))
        self.assertRaises(AttributeError, Mailer, config)


class TestMethods(TestCase):
    def test_startup(self):
        messages = logging.getLogger().handlers[0].buffer
        
        interface = Mailer(base_config)
        interface.start()
        
        self.assertEqual(len(messages), 5)
        self.assertEqual(messages[0].getMessage(), "Mail delivery service starting.")
        self.assertEqual(messages[-1].getMessage(), "Mail delivery service started.")
        
        interface.start()
        
        self.assertEqual(len(messages), 6)
        self.assertEqual(messages[-1].getMessage(), "Attempt made to start an already running Mailer service.")
        
        interface.stop()
    
    def test_shutdown(self):
        interface = Mailer(base_config)
        interface.start()
        
        logging.getLogger().handlers[0].truncate()
        messages = logging.getLogger().handlers[0].buffer
        
        interface.stop()
        
        self.assertEqual(len(messages), 5)
        self.assertEqual(messages[0].getMessage(), "Mail delivery service stopping.")
        self.assertEqual(messages[-1].getMessage(), "Mail delivery service stopped.")
        
        interface.stop()
        
        self.assertEqual(len(messages), 6)
        self.assertEqual(messages[-1].getMessage(), "Attempt made to stop an already stopped Mailer service.")
    
    def test_send(self):
        message = Bunch(id='foo')
        
        interface = Mailer(base_config)
        
        self.assertRaises(MailerNotRunning, interface.send, message)
        
        interface.start()
        
        logging.getLogger().handlers[0].truncate()
        messages = logging.getLogger().handlers[0].buffer
        
        self.assertEqual(interface.send(message), (message, True))
        
        self.assertEqual(messages[0].getMessage(), "Attempting delivery of message foo.")
        self.assertEqual(messages[-1].getMessage(), "Message foo delivered.")
        
        message_fail = Bunch(id='bar', die=True)
        self.assertRaises(Exception, interface.send, message_fail)
        
        self.assertEqual(messages[-4].getMessage(), "Attempting delivery of message bar.")
        self.assertEqual(messages[-3].getMessage(), "Acquired existing transport instance.")
        self.assertEqual(messages[-2].getMessage(), "Shutting down transport due to unhandled exception.")
        self.assertEqual(messages[-1].getMessage(), "Delivery of message bar failed.")
        
        interface.stop()
    
    def test_new(self):
        config = dict(manager=dict(use='immediate'), transport=dict(use='mock'),
                message=dict(author='from@example.com', retries=1, brand=False))
        
        interface = Mailer(config).start()
        message = interface.new(retries=2)
        
        self.assertEqual(message.author, ["from@example.com"])
        self.assertEqual(message.bcc, [])
        self.assertEqual(message.retries, 2)
        self.assertTrue(message.mailer is interface)
        self.assertEqual(message.brand, False)
        
        self.assertRaises(NotImplementedError, Message().send)
        
        self.assertEqual(message.send(), (message, True))
        
        message = interface.new("alternate@example.com", "recipient@example.com", "Test.")
        
        self.assertEqual(message.author, ["alternate@example.com"])
        self.assertEqual(message.to, ["recipient@example.com"])
        self.assertEqual(message.subject, "Test.")

########NEW FILE########
__FILENAME__ = test_exceptions
# encoding: utf-8

"""Test the primary configurator interface, Delivery."""

import logging

from unittest import TestCase
from nose.tools import ok_, eq_, raises

from marrow.mailer.exc import DeliveryFailedException


log = logging.getLogger('tests')



class TestDeliveryFailedException(TestCase):
    def test_init(self):
        exc = DeliveryFailedException("message", "reason")
        self.assertEquals(exc.msg, "message")
        self.assertEquals(exc.reason, "reason")
        self.assertEquals(exc.args[0], "message")
        self.assertEquals(exc.args[1], "reason")

########NEW FILE########
__FILENAME__ = test_issue_2
# encoding: utf-8

from __future__ import unicode_literals

import logging

from unittest import TestCase
from nose.tools import ok_, eq_, raises

from marrow.mailer import Mailer


log = logging.getLogger('tests')



def test_issue_2():
    mail = Mailer({
            'manager.use': 'immediate',
            'transport.use': 'smtp',
            'transport.host': 'secure.emailsrvr.com',
            'transport.tls': 'ssl'
        })
    
    mail.start()
    mail.stop()

########NEW FILE########
__FILENAME__ = test_message
# encoding: utf-8
"""Test the TurboMail Message class."""

from __future__ import unicode_literals

import calendar
from datetime import datetime, timedelta
import email
import logging
import re
import time
import unittest

from email.header import Header
from email.mime.text import MIMEText
from email.utils import formatdate, parsedate_tz

from marrow.mailer import Message
from marrow.mailer.address import AddressList

from nose.tools import raises

# logging.disable(logging.WARNING)


class TestBasicMessage(unittest.TestCase):
    """Test the basic output of the Message class."""
    
    gif = b'47494638396101000100910000000000000000fe010200000021f904041400ff002c00000000010001000002024401003b'
    
    def build_message(self, **kw):
        return Message(
                    author=('Author', 'author@example.com'),
                    to=('Recipient', 'recipient@example.com'),
                    subject='Test message subject.',
                    plain='This is a test message plain text body.',
                    **kw
                )
    
    def test_missing_values(self):
        message = Message()
        self.assertRaises(ValueError, str, message)
        
        message.author = "bob.dole@whitehouse.gov"
        self.assertRaises(ValueError, str, message)
        
        message.subject = "Attn: Bob Dole"
        self.assertRaises(ValueError, str, message)
        
        message.to = "user@example.com"
        self.assertRaises(ValueError, str, message)
        
        message.plain = "Testing!"
        
        try:
            str(message)
        except ValueError:
            self.fail("Message should be valid.")
    
    def test_message_id(self):
        msg = self.build_message()
        
        self.assertEquals(msg._id, None)
        
        id_ = msg.id
        self.assertEquals(msg._id, id_)
        
        self.assertEquals(msg.id, id_)
    
    def test_missing_author(self):
        message = self.build_message()
        message.author = []
        
        self.assertRaises(ValueError, lambda: message.envelope)
    
    def test_message_properties(self):
        message = self.build_message()
        self.assertEqual(message.author, [("Author", "author@example.com")])
        self.assertEqual(str(message.author), "Author <author@example.com>")
        self.failUnless(isinstance(message.mime, MIMEText))
    
    def test_message_string_with_basic(self):
        msg = email.message_from_string(str(self.build_message(encoding="iso-8859-1")))
        
        self.assertEqual('Author <author@example.com>', msg['From'])
        self.assertEqual('Recipient <recipient@example.com>', msg['To'])
        self.assertEqual('Test message subject.', msg['Subject'])
        self.assertEqual('This is a test message plain text body.', msg.get_payload())
    
    def test_message_recipients_and_addresses(self):
        message = self.build_message()
        
        message.cc = 'cc@example.com'
        message.bcc = 'bcc@example.com'
        message.sender = 'sender@example.com'
        message.reply = 'replyto@example.com'
        message.notify = 'disposition@example.com'
        
        msg = email.message_from_string(str(message))
        
        self.assertEqual('cc@example.com', msg['cc'])
        self.assertEqual(None, msg['bcc'])
        self.assertEqual('sender@example.com', msg['sender'])
        self.assertEqual('replyto@example.com', msg['reply-to'])
        self.assertEqual('disposition@example.com', msg['disposition-notification-to'])
    
    def test_mime_generation_plain(self):
        message = self.build_message()
        mime = message.mime
        
        self.failUnless(message.mime is mime)
        message.subject = "Test message subject."
        self.failIf(message.mime is mime)
    
    def test_mime_generation_rich(self):
        message = self.build_message()
        message.plain = "Hello world."
        message.rich = "Farewell cruel world."
        
        self.failUnless('Hello world.' in str(message))
        self.failUnless('Farewell cruel world.' in str(message))
    
    def test_mime_generation_rich_embedded(self):
        message = self.build_message()
        message.plain = "Hello world."
        message.rich = "Farewell cruel world."
        
        message.attach("hello.txt", b"Fnord.", "text", "plain", True)
        
        self.failUnless('Hello world.' in str(message))
        self.failUnless('Farewell cruel world.' in str(message))
        self.failUnless('hello.txt' in str(message))
        self.failUnless('Fnord.' in str(message))
    
    def test_mime_attachments(self):
        message = self.build_message()
        message.plain = "Hello world."
        message.rich = "Farewell cruel world."
        
        message.attach("hello.txt", b"Fnord.")
        
        self.failUnless('Hello world.' in str(message))
        self.failUnless('Farewell cruel world.' in str(message))
        self.failUnless('hello.txt' in str(message))
        self.failUnless('Fnord.' in str(message))
        self.failUnless('text/plain\n' in str(message))
    
    def test_mime_attachments_unknown(self):
        message = self.build_message()
        message.plain = "Hello world."
        message.rich = "Farewell cruel world."
        message.attach('test.xbin', b"Word.")
        self.failUnless('test.xbin' in str(message))
        self.failUnless('application/octet-stream' in str(message))
        
        self.assertRaises(TypeError, message.attach, 'foo', object())
    
    def test_mime_attachments_file(self):
        import tempfile
        
        message = self.build_message()
        message.plain = "Hello world."
        message.rich = "Farewell cruel world."
        
        with tempfile.NamedTemporaryFile() as fh:
            fh.write("foo")
            fh.flush()
            
            message.attach(fh.name)
            self.failUnless('application/octet-stream' in str(message))
            self.failUnless('foo' in str(message))
    
    def test_mime_attachments_filelike(self):
        class Mock(object):
            def read(self):
                return b'foo'
        
        message = self.build_message()
        message.plain = "Hello world."
        message.rich = "Farewell cruel world."
        message.attach('test.xbin', Mock())
        self.failUnless('test.xbin' in str(message))
        self.failUnless('application/octet-stream' in str(message))
        self.failUnless('foo' in str(message))
    
    def test_mime_embed_gif_file(self):
        import tempfile
        import codecs
        
        message = self.build_message()
        message.plain = "Hello world."
        message.rich = "Farewell cruel world."
        
        with tempfile.NamedTemporaryFile() as fh:
            fh.write(codecs.decode(self.gif, 'hex'))
            fh.flush()
            
            message.embed(fh.name)
            
            result = bytes(message)
            
            self.failUnless(b'image/gif' in result)
            self.failUnless(b'GIF89a' in result)
    
    def test_mime_embed_gif_bytes(self):
        import codecs
        
        message = self.build_message()
        message.plain = "Hello world."
        message.rich = "Farewell cruel world."
        message.embed('test.gif', bytes(codecs.decode(self.gif, 'hex')))
        
        result = bytes(message)
        
        self.failUnless(b'image/gif' in result)
        self.failUnless(b'GIF89a' in result)
        
        class Mock(object):
            def read(s):
                return codecs.decode(self.gif, 'hex')
        
        message = self.build_message()
        message.plain = "Hello world."
        message.rich = "Farewell cruel world."
        message.embed('test.gif', Mock())
        
        result = bytes(message)
        
        self.failUnless(b'image/gif' in result)
        self.failUnless(b'GIF89a' in result)
    
    def test_mime_embed_failures(self):
        message = self.build_message()
        message.plain = "Hello world."
        message.rich = "Farewell cruel world."
        
        self.assertRaises(TypeError, message.embed, 'test.gif', object())
    
    def test_recipients_collection(self):
        message = self.build_message()
        message.cc.append("copied@example.com")
        self.assertEqual(["recipient@example.com", "copied@example.com"], message.recipients.addresses)
    
    def test_smtp_from_as_envelope(self):
        message = self.build_message()
        message.sender = 'devnull@example.com'
        self.assertEqual('devnull@example.com', str(message.envelope))
    
    def test_subject_with_umlaut(self):
        message = self.build_message()
        
        subject_string = "Test with äöü"
        message.subject = subject_string
        message.encoding = "UTF-8"
        
        msg = email.message_from_string(str(message))
        encoded_subject = str(Header(subject_string, "UTF-8"))
        self.assertEqual(encoded_subject, msg['Subject'])
    
    def test_from_with_umlaut(self):
        message = self.build_message()
        
        from_name = "Karl Müller"
        from_email = "karl.mueller@example.com"
        
        message.author = [(from_name, from_email)]
        message.encoding = "ISO-8859-1"
        
        msg = email.message_from_string(str(message))
        encoded_name = "%s <%s>" % (str(Header(from_name, "ISO-8859-1")), from_email)
        self.assertEqual(encoded_name, msg['From'])
    
    def test_multiple_authors(self):
        message = self.build_message()
        
        message.authors = 'authors@example.com'
        self.assertEqual(message.authors, message.author)
        
        message.authors = ['bar@example.com', 'baz@example.com']
        message.sender = 'foo@example.com'
        msg = email.message_from_string(str(message))
        from_addresses = re.split(r",\n?\s+", msg['From'])
        self.assertEqual(['bar@example.com', 'baz@example.com'], from_addresses)
    
    # def test_multiple_authors_require_sender(self):
    #     message = self.build_message()
    #     
    #     message.authors = ['bar@example.com', 'baz@example.com']
    #     self.assertRaises(ValueError, str, message)
    #     
    #     message.sender = 'bar@example.com'
    #     str(message)
    
    @raises(ValueError)
    def test_permit_one_sender_at_most(self):
        message = self.build_message()
        message.sender = AddressList(['bar@example.com', 'baz@example.com'])
    
    def test_raise_error_for_unknown_kwargs_at_class_instantiation(self):
        self.assertRaises(TypeError, Message, invalid_argument=True)
    
    def test_add_custom_headers_dict(self):
        message = self.build_message()
        message.headers = {'Precedence': 'bulk', 'X-User': 'Alice'}
        msg = email.message_from_string(str(message))
        
        self.assertEqual('bulk', msg['Precedence'])
        self.assertEqual('Alice', msg['X-User'])
    
    def test_add_custom_headers_tuple(self):
        message = self.build_message()
        message.headers = (('Precedence', 'bulk'), ('X-User', 'Alice'))
        
        msg = email.message_from_string(str(message))
        self.assertEqual('bulk', msg['Precedence'])
        self.assertEqual('Alice', msg['X-User'])

    def test_add_custom_headers_list(self):
        "Test that a custom header (list type) can be attached."
        message = self.build_message()
        message.headers = [('Precedence', 'bulk'), ('X-User', 'Alice')]
        
        msg = email.message_from_string(str(message))
        self.assertEqual('bulk', msg['Precedence'])
        self.assertEqual('Alice', msg['X-User'])
    
    def test_no_sender_header_if_no_sender_required(self):
        message = self.build_message()
        msg = email.message_from_string(str(message))
        self.assertEqual(None, msg['sender'])
    
    def _date_header_to_utc_datetime(self, date_string):
        """Converts a date_string from the Date header into a naive datetime
        object in UTC."""
        # There is pytz which could solve whole isssue but it is not in Fedora
        # EPEL 4 currently so I don't want to depend on out-of-distro modules - 
        # hopefully I'll get it right anyway...
        assert date_string != None
        tztime_struct = parsedate_tz(date_string)
        time_tuple, tz_offset = (tztime_struct[:9], tztime_struct[9])
        epoch_utc_seconds = calendar.timegm(time_tuple)
        if tz_offset is not None:
            epoch_utc_seconds -= tz_offset
        datetime_obj = datetime.utcfromtimestamp(epoch_utc_seconds)
        return datetime_obj
    
    def _almost_now(self, date_string):
        """Returns True if the date_string represents a time which is 'almost 
        now'."""
        utc_date = self._date_header_to_utc_datetime(date_string)
        delta = abs(datetime.utcnow() - utc_date)
        return (delta < timedelta(seconds=1))
    
    def test_date_header_added_even_if_date_not_set_explicitely(self):
        message = self.build_message()
        msg = email.message_from_string(str(message))
        self.failUnless(self._almost_now(msg['Date']))
    
    def test_date_can_be_set_as_string(self):
        message = self.build_message()
        date_string = 'Fri, 26 Dec 2008 11:19:42 +0530'
        message.date = date_string
        msg = email.message_from_string(str(message))
        self.assertEqual(date_string, msg['Date'])
    
    def test_date_can_be_set_as_float(self):
        message = self.build_message()
        expected_date = datetime(2008, 12, 26, 12, 55)
        expected_time = time.mktime(expected_date.timetuple())
        message.date = expected_time
        msg = email.message_from_string(str(message))
        header_string = msg['Date']
        header_date = self._date_header_to_utc_datetime(header_string)
        self.assertEqual(self.localdate_to_utc(expected_date), header_date)
        expected_datestring = formatdate(expected_time, localtime=True)
        self.assertEqual(expected_datestring, header_string)
    
    def localdate_to_utc(self, localdate):
        local_epoch_seconds = time.mktime(localdate.timetuple())
        date_string = formatdate(local_epoch_seconds, localtime=True)
        return self._date_header_to_utc_datetime(date_string)
    
    def test_date_can_be_set_as_datetime(self):
        message = self.build_message()
        expected_date = datetime(2008, 12, 26, 12, 55)
        message.date = expected_date
        msg = email.message_from_string(str(message))
        header_date = self._date_header_to_utc_datetime(msg['Date'])
        self.assertEqual(self.localdate_to_utc(expected_date), header_date)
    
    def test_date_header_is_set_even_if_reset_to_none(self):
        message = self.build_message()
        message.date = None
        msg = email.message_from_string(str(message))
        self.failUnless(self._almost_now(msg['Date']))
    
    def test_recipients_property_includes_cc_and_bcc(self):
        message = self.build_message()
        message.cc = 'cc@example.com'
        message.bcc = 'bcc@example.com'
        expected_recipients = ['recipient@example.com', 'cc@example.com', 
                               'bcc@example.com']
        recipients = map(str, list(message.recipients.addresses))
        self.assertEqual(expected_recipients, recipients)
    
    def test_can_set_encoding_for_message_explicitely(self):
        message = self.build_message()
        self.failIf('iso-8859-1' in str(message).lower())
        message.encoding = 'ISO-8859-1'
        msg = email.message_from_string(str(message))
        self.assertEqual('text/plain; charset="iso-8859-1"', msg['Content-Type'])
        self.assertEqual('quoted-printable', msg['Content-Transfer-Encoding'])
    
    # def test_message_encoding_can_be_set_in_config_file(self):
    #     interface.config['mail.message.encoding'] = 'ISO-8859-1'
    #     message = self.build_message()
    #     msg = email.message_from_string(str(message))
    #     self.assertEqual('text/plain; charset="iso-8859-1"', msg['Content-Type'])
    #     self.assertEqual('quoted-printable', msg['Content-Transfer-Encoding'])
    
    def test_plain_utf8_encoding_uses_qp(self):
        message = self.build_message()
        msg = email.message_from_string(str(message))
        self.assertEqual('text/plain; charset="utf-8"', msg['Content-Type'])
        self.assertEqual('quoted-printable', msg['Content-Transfer-Encoding'])
    
    def test_callable_bodies(self):
        message = self.build_message()
        message.plain = lambda: "plain text"
        message.rich = lambda: "rich text"
        
        self.assertTrue('plain text' in str(message))
        self.assertTrue('rich text' in str(message))

########NEW FILE########
__FILENAME__ = test_plugins
# encoding: utf-8

from __future__ import unicode_literals

import logging
import pkg_resources

from unittest import TestCase
from nose.tools import ok_, eq_, raises
from nose.plugins.skip import Skip, SkipTest

from marrow.mailer.interfaces import IManager, ITransport


log = logging.getLogger('tests')



def test_managers():
    def closure(plugin):
        try:
            plug = plugin.load()
        except ImportError as e:
            raise SkipTest("Skipped {name} manager due to ImportError:\n{err}".format(name=plugin.name, err=str(e)))
        
        ok_(isinstance(plug, IManager), "{name} does not conform to the IManager API.".format(name=plugin.name))
    
    entrypoint = None
    for entrypoint in pkg_resources.iter_entry_points('marrow.mailer.manager', None):
        yield closure, entrypoint
    
    if entrypoint is None:
        raise SkipTest("No managers found, have you run `setup.py develop` yet?")


def test_transports():
    def closure(plugin):
        try:
            plug = plugin.load()
        except ImportError as e:
            raise SkipTest("Skipped {name} transport due to ImportError:\n{err}".format(name=plugin.name, err=str(e)))
        
        ok_(isinstance(plug, ITransport), "{name} does not conform to the ITransport API.".format(name=plugin.name))
    
    entrypoint = None
    for entrypoint in pkg_resources.iter_entry_points('marrow.mailer.transport', None):
        yield closure, entrypoint
    
    if entrypoint is None:
        raise SkipTest("No transports found, have you run `setup.py develop` yet?")

########NEW FILE########
__FILENAME__ = test_validator
# encoding: utf-8

"""Test the primary configurator interface, Delivery."""

import DNS
import logging

from unittest import TestCase
from nose.tools import ok_, eq_, raises
from nose.plugins.skip import Skip, SkipTest

from marrow.mailer.validator import ValidationException, BaseValidator, DomainValidator, EmailValidator, EmailHarvester

from marrow.util.bunch import Bunch


log = logging.getLogger('tests')



class TestBaseValidator(TestCase):
    class MockValidator(BaseValidator):
        def validate(self, success=True):
            if success:
                return True, None
            
            return False, "Mock failure."
    
    def test_validator_success(self):
        mock = self.MockValidator()
        self.assertTrue(mock.validate_or_raise())
    
    def test_validator_failure(self):
        mock = self.MockValidator()
        self.assertRaises(ValidationException, mock.validate_or_raise, False)


def test_common_rules():
    mock = DomainValidator()
    dataset = [
            ('valid@example.com', ''),
            ('', 'It cannot be empty.'),
            ('*' * 256, 'It cannot be longer than 255 chars.'),
            ('.invalid@example.com', 'It cannot start with a dot.'),
            ('invalid@example.com.', 'It cannot end with a dot.'),
            ('invalid..@example.com', 'It cannot contain consecutive dots.'),
        ]
    
    def closure(address, expect):
        eq_(mock._apply_common_rules(address, 255), (address, expect))
    
    for address, expect in dataset:
        yield closure, address, expect


def test_common_rules_fixed():
    mock = DomainValidator(fix=True)
    dataset = [
            ('.fixme@example.com', ('fixme@example.com', '')),
            ('fixme@example.com.', ('fixme@example.com', '')),
        ]
    
    def closure(address, expect):
        eq_(mock._apply_common_rules(address, 255), expect)
    
    for address, expect in dataset:
        yield closure, address, expect


def test_domain_validation_basic():
    mock = DomainValidator()
    dataset = [
            ('example.com', ''),
            ('xn--ls8h.la', ''), # IDN: (poop).la
            ('', 'Invalid domain: It cannot be empty.'),
            ('-bad.example.com', 'Invalid domain.'),
        ]
    
    def closure(domain, expect):
        eq_(mock.validate_domain(domain), (domain, expect))
    
    for domain, expect in dataset:
        yield closure, domain, expect


def test_domain_lookup():
    mock = DomainValidator()
    dataset = [
            ('gothcandy.com', 'a', '174.129.236.35'),
            ('a' * 64 + '.gothcandy.com', 'a', False),
            ('gothcandy.com', 'mx', [(10, 'mx1.emailsrvr.com'), (20, 'mx2.emailsrvr.com')]),
            ('nx.example.com', 'a', False),
            ('xn--ls8h.la', 'a', '38.103.165.5'), # IDN: (poop).la
        ]
    
    def closure(domain, kind, expect):
        try:
            eq_(mock.lookup_domain(domain, kind, server=['8.8.8.8']), expect)
        except DNS.DNSError:
            raise SkipTest("Skipped due to DNS error.")

    
    for domain, kind, expect in dataset:
        yield closure, domain, kind, expect


def test_domain_validation():
    mock = DomainValidator(lookup_dns='mx')
    dataset = [
            ('example.com', 'Domain does not seem to exist.'),
            ('xn--ls8h.la', ''), # IDN: (poop).la
            ('', 'Invalid domain: It cannot be empty.'),
            ('-bad.example.com', 'Invalid domain.'),
            ('gothcandy.com', ''),
            ('a' * 64 + '.gothcandy.com', 'Domain does not seem to exist.'),
            ('gothcandy.com', ''),
            ('nx.example.com', 'Domain does not seem to exist.'),
        ]
    
    def closure(domain, expect):
        try:
            eq_(mock.validate_domain(domain), (domain, expect))
        except DNS.DNSError:
            raise SkipTest("Skipped due to DNS error.")
    
    for domain, expect in dataset:
        yield closure, domain, expect


@raises(RuntimeError)
def test_bad_lookup_record_1():
    mock = DomainValidator(lookup_dns='cname')


@raises(RuntimeError)
def test_bad_lookup_record_2():
    mock = DomainValidator()
    mock.lookup_domain('example.com', 'cname')


def test_email_validation():
    mock = EmailValidator()
    dataset = [
            ('user@example.com', ''),
            ('user@xn--ls8h.la', ''), # IDN: (poop).la
            ('', 'The e-mail is empty.'),
            ('user@user@example.com', 'An email address must contain a single @'),
            ('user@-example.com', 'The e-mail has a problem to the right of the @: Invalid domain.'),
            ('bad,user@example.com', 'The email has a problem to the left of the @: Invalid local part.'),
        ]
    
    def closure(address, expect):
        eq_(mock.validate_email(address), (address, expect))
    
    for address, expect in dataset:
        yield closure, address, expect


def test_harvester():
    mock = EmailHarvester()
    dataset = [
            ('', []),
            ('test@example.com', ['test@example.com']),
            ('lorem ipsum test@example.com dolor sit', ['test@example.com']),
        ]
    
    def closure(text, expect):
        eq_(list(mock.harvest(text)), expect)
    
    for text, expect in dataset:
        yield closure, text, expect

########NEW FILE########
__FILENAME__ = test_gae
# Use: http://pypi.python.org/pypi/gaetestbed
########NEW FILE########
__FILENAME__ = test_log
# encoding: utf-8

import logging

from unittest import TestCase

from marrow.mailer import Message
from marrow.mailer.transport.log import LoggingTransport


log = logging.getLogger('tests')



class TestLoggingTransport(TestCase):
    def setUp(self):
        self.messages = logging.getLogger().handlers[0].buffer
        del self.messages[:]
        
        self.transport = LoggingTransport(dict())
        self.transport.startup()
    
    def tearDown(self):
        self.transport.shutdown()
    
    def test_startup(self):
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(self.messages[0].getMessage(), "Logging transport starting.")
        self.assertEqual(self.messages[0].levelname, 'DEBUG')
    
    def test_shutdown(self):
        self.transport.shutdown()
        
        self.assertEqual(len(self.messages), 2)
        self.assertEqual(self.messages[0].getMessage(), "Logging transport starting.")
        self.assertEqual(self.messages[1].getMessage(), "Logging transport stopping.")
        self.assertEqual(self.messages[1].levelname, 'DEBUG')
    
    def test_delivery(self):
        self.assertEqual(len(self.messages), 1)
        
        message = Message('from@example.com', 'to@example.com', 'Subject.', plain='Body.')
        msg = str(message)
        
        self.transport.deliver(message)
        self.assertEqual(len(self.messages), 3)
        
        expect = "DELIVER %s %s %d %r %r" % (message.id, message.date.isoformat(),
            len(msg), message.author, message.recipients)
        
        self.assertEqual(self.messages[0].getMessage(), "Logging transport starting.")
        self.assertEqual(self.messages[1].getMessage(), expect)
        self.assertEqual(self.messages[1].levelname, 'INFO')
        self.assertEqual(self.messages[2].getMessage(), str(message))
        self.assertEqual(self.messages[2].levelname, 'CRITICAL')

########NEW FILE########
__FILENAME__ = test_maildir
# encoding: utf-8

from __future__ import unicode_literals

import os
import sys
import shutil
import logging
import mailbox
import tempfile

from unittest import TestCase
from nose.tools import ok_, eq_, raises
from nose.plugins.skip import Skip, SkipTest

from marrow.mailer import Message
from marrow.mailer.transport.maildir import MaildirTransport


log = logging.getLogger('tests')



class TestMailDirectoryTransport(TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp()
        
        for i in ('cur', 'new', 'tmp'):
            os.mkdir(os.path.join(self.path, i))
        
        self.transport = MaildirTransport(dict(directory=self.path, create=True))
    
    def tearDown(self):
        self.transport.shutdown()
        shutil.rmtree(self.path)
    
    def test_bad_config(self):
        self.assertRaises(ValueError, MaildirTransport, dict())
    
    def test_startup(self):
        self.transport.startup()
        self.assertTrue(isinstance(self.transport.box, mailbox.Maildir))
    
    def test_child_folder_startup(self):
        self.transport.folder = 'test'
        self.transport.startup()
        self.assertTrue(os.path.exists(os.path.join(self.path, '.test')))
    
    def test_shutdown(self):
        self.transport.startup()
        self.transport.shutdown()
        self.assertTrue(self.transport.box is None)
    
    def test_delivery(self):
        message = Message('from@example.com', 'to@example.com', "Test subject.")
        message.plain = "Test message."
        
        self.transport.startup()
        self.transport.deliver(message)
        
        filename = os.listdir(os.path.join(self.path, 'new'))[0]
        
        with open(os.path.join(self.path, 'new', filename), 'rb') as fh:
            self.assertEqual(str(message), fh.read())

########NEW FILE########
__FILENAME__ = test_mbox
# encoding: utf-8

from __future__ import unicode_literals

import os
import sys
import logging
import mailbox
import tempfile

from unittest import TestCase
from nose.tools import ok_, eq_, raises
from nose.plugins.skip import Skip, SkipTest

from marrow.mailer import Message
from marrow.mailer.transport.mbox import MailboxTransport


log = logging.getLogger('tests')



class TestMailboxTransport(TestCase):
    def setUp(self):
        _, self.filename = tempfile.mkstemp('.mbox')
        os.close(_)
        
        self.transport = MailboxTransport(dict(file=self.filename))
    
    def tearDown(self):
        self.transport.shutdown()
        os.unlink(self.filename)
    
    def test_bad_config(self):
        self.assertRaises(ValueError, MailboxTransport, dict())
    
    def test_startup(self):
        self.transport.startup()
        self.assertTrue(isinstance(self.transport.box, mailbox.mbox))
    
    def test_shutdown(self):
        self.transport.startup()
        self.transport.shutdown()
        self.assertTrue(self.transport.box is None)
    
    def test_delivery(self):
        message = Message('from@example.com', 'to@example.com', "Test subject.")
        message.plain = "Test message."
        
        self.transport.startup()
        self.transport.deliver(message)
        
        with open(self.filename, 'rb') as fh:
            self.assertEqual(str(message), b"\n".join(fh.read().splitlines()[1:]))

########NEW FILE########
__FILENAME__ = test_mock
# encoding: utf-8

from __future__ import unicode_literals

import logging

from unittest import TestCase
from nose.tools import ok_, eq_, raises
from nose.plugins.skip import Skip, SkipTest

from marrow.mailer import Message
from marrow.mailer.exc import TransportFailedException, TransportExhaustedException
from marrow.mailer.transport.mock import MockTransport

from marrow.util.bunch import Bunch


log = logging.getLogger('tests')



class TestMockTransport(TestCase):
    def test_success(self):
        transport = MockTransport(dict(success=1.1))
        self.assertTrue(transport.deliver(None))
    
    def test_failure(self):
        transport = MockTransport(dict(success=0.0))
        self.assertFalse(transport.deliver(None))
        
        transport = MockTransport(dict(success=0.0, failure=1.0))
        self.assertRaises(TransportFailedException, transport.deliver, None)
    
    def test_death(self):
        transport = MockTransport(dict())
        self.assertRaises(ZeroDivisionError, transport.deliver, Bunch(die=True))
    
    def test_exhaustion(self):
        transport = MockTransport(dict(success=0.0, exhaustion=1.0))
        self.assertRaises(TransportExhaustedException, transport.deliver, None)

########NEW FILE########
__FILENAME__ = test_smtp
# encoding: utf-8

from __future__ import unicode_literals

import os
import sys
import socket
import logging
import smtplib

from unittest import TestCase
from nose.tools import ok_, eq_, raises
from nose.plugins.skip import Skip, SkipTest

try:
    from pymta.api import IMTAPolicy, PolicyDecision, IAuthenticator
    from pymta.test_util import BlackholeDeliverer, DebuggingMTA, MTAThread
except ImportError: # pragma: no cover
    raise SkipTest("PyMTA not installed; skipping SMTP tests.")

from marrow.mailer import Message
from marrow.mailer.exc import TransportException, TransportExhaustedException, MessageFailedException
from marrow.mailer.transport.smtp import SMTPTransport


log = logging.getLogger('tests')


class SMTPTestCase(TestCase):
    server = None
    Policy = IMTAPolicy
    
    class Authenticator(IAuthenticator):
        def authenticate(self, username, password, peer):
            return True
    
    @classmethod
    def setUpClass(cls):
        assert not cls.server, "Server already running?"
        
        cls.port = __import__('random').randint(9000, 40000)
        cls.collector = BlackholeDeliverer
        cls.host = DebuggingMTA('127.0.0.1', cls.port, cls.collector, policy_class=cls.Policy,
                authenticator_class=cls.Authenticator)
        cls.server = MTAThread(cls.host)
        cls.server.start()
    
    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.stop()
            cls.server = None


class TestSMTPTransportBase(SMTPTestCase):
    def test_basic_config(self):
        transport = SMTPTransport(dict(port=self.port, timeout="10", tls=False, pipeline="10"))
        
        self.assertEqual(transport.sent, 0)
        self.assertEqual(transport.host, '127.0.0.1')
        self.assertEqual(transport.port, self.port)
        self.assertEqual(transport.timeout, 10)
        self.assertEqual(transport.pipeline, 10)
        self.assertEqual(transport.debug, False)
        
        self.assertEqual(transport.connected, False)
    
    def test_startup_shutdown(self):
        transport = SMTPTransport(dict(port=self.port))
        
        transport.startup()
        self.assertTrue(transport.connected)
        
        transport.shutdown()
        self.assertFalse(transport.connected)
    
    def test_authentication(self):
        transport = SMTPTransport(dict(port=self.port, username='bob', password='dole'))
        
        transport.startup()
        self.assertTrue(transport.connected)
        
        transport.shutdown()
        self.assertFalse(transport.connected)
    
    def test_bad_tls(self):
        transport = SMTPTransport(dict(port=self.port, tls='required'))
        self.assertRaises(TransportException, transport.startup)


class TransportTestCase(SMTPTestCase):
    pipeline = None
    
    def setUp(self):
        self.transport = SMTPTransport(dict(port=self.port, pipeline=self.pipeline))
        self.transport.startup()
        self.msg = self.message
    
    def tearDown(self):
        self.transport.shutdown()
        self.transport = None
        self.msg = None
    
    @property
    def message(self):
        return Message('from@example.com', 'to@example.com', 'Test subject.', plain="Test body.")


class TestSMTPTransport(TransportTestCase):
    def test_send_simple_message(self):
        self.assertRaises(TransportExhaustedException, self.transport.deliver, self.msg)
        self.assertEqual(self.collector.received_messages.qsize(), 1)
        
        message = self.collector.received_messages.get()
        self.assertEqual(message.msg_data, str(self.msg))
        self.assertEqual(message.smtp_from, self.msg.envelope)
        self.assertEqual(message.smtp_to, self.msg.recipients)
    
    def test_send_after_shutdown(self):
        self.transport.shutdown()
        
        self.assertRaises(TransportExhaustedException, self.transport.deliver, self.msg)
        self.assertEqual(self.collector.received_messages.qsize(), 1)
        
        message = self.collector.received_messages.get()
        self.assertEqual(message.msg_data, str(self.msg))
        self.assertEqual(message.smtp_from, self.msg.envelope)
        self.assertEqual(message.smtp_to, self.msg.recipients)
    
    def test_sender(self):
        self.msg.sender = "sender@example.com"
        self.assertEqual(self.msg.envelope, self.msg.sender)
        
        self.assertRaises(TransportExhaustedException, self.transport.deliver, self.msg)
        self.assertEqual(self.collector.received_messages.qsize(), 1)
        
        message = self.collector.received_messages.get()
        self.assertEqual(message.msg_data, str(self.msg))
        self.assertEqual(message.smtp_from, self.msg.envelope)
    
    def test_many_recipients(self):
        self.msg.cc = 'cc@example.com'
        self.msg.bcc = 'bcc@example.com'
        
        self.assertRaises(TransportExhaustedException, self.transport.deliver, self.msg)
        self.assertEqual(self.collector.received_messages.qsize(), 1)
        
        message = self.collector.received_messages.get()
        self.assertEqual(message.msg_data, str(self.msg))
        self.assertEqual(message.smtp_from, self.msg.envelope)
        self.assertEqual(message.smtp_to, self.msg.recipients)


class TestSMTPTransportRefusedSender(TransportTestCase):
    pipeline = 10
    
    class Policy(IMTAPolicy):
        def accept_from(self, sender, message):
            return False
    
    def test_refused_sender(self):
        self.assertRaises(MessageFailedException, self.transport.deliver, self.msg)
        self.assertEquals(self.collector.received_messages.qsize(), 0)


class TestSMTPTransportRefusedRecipients(TransportTestCase):
    pipeline = True
    
    class Policy(IMTAPolicy):
        def accept_rcpt_to(self, sender, message):
            return False
    
    def test_refused_recipients(self):
        self.assertRaises(MessageFailedException, self.transport.deliver, self.msg)
        self.assertEquals(self.collector.received_messages.qsize(), 0)


'''
    def get_connection(self):
        # We can not use the id of transport.connection because sometimes Python
        # returns the same id for new, but two different instances of the same
        # object (Fedora 10, Python 2.5):
        # class Bar: pass
        # id(Bar()) == id(Bar())  -> True
        sock = getattr(interface.manager.transport.connection, 'sock', None)
        return sock
    
    def get_transport(self):
        return interface.manager.transport
    
    def test_close_connection_when_max_messages_per_connection_was_reached(self):
        self.config['mail.smtp.max_messages_per_connection'] = 2
        self.init_mta()
        self.msg.send()
        first_connection = self.get_connection()
        self.msg.send()
        second_connection = self.get_connection()
        
        queue = self.get_received_messages()
        self.assertEqual(2, queue.qsize())
        self.assertNotEqual(first_connection, second_connection)
    
    def test_close_connection_when_max_messages_per_connection_was_reached_even_on_errors(self):
        self.config['mail.smtp.max_messages_per_connection'] = 1
        class RejectHeloPolicy(IMTAPolicy):
            def accept_helo(self, sender, message):
                return False
        self.init_mta(policy_class=RejectHeloPolicy)
        
        self.msg.send()
        self.assertEqual(False, self.get_transport().is_connected())
    
    def test_reopen_connection_when_server_closed_connection(self):
        self.config['mail.smtp.max_messages_per_connection'] = 2
        class DropEverySecondConnectionPolicy(IMTAPolicy):
            def accept_msgdata(self, sender, message):
                if not hasattr(self, 'nr_connections'):
                    self.nr_connections = 0
                self.nr_connections = (self.nr_connections + 1) % 2
                decision = PolicyDecision(True)
                drop_this_connection = (self.nr_connections == 1)
                decision._close_connection_after_response = drop_this_connection
                return decision
        self.init_mta(policy_class=DropEverySecondConnectionPolicy)
        
        self.msg.send()
        first_connection = self.get_connection()
        self.msg.send()
        second_connection = self.get_connection()
        
        queue = self.get_received_messages()
        self.assertEqual(2, queue.qsize())
        opened_new_connection = (first_connection != second_connection)
        self.assertEqual(True, opened_new_connection)
    
    def test_smtp_shutdown_ignores_socket_errors(self):
        self.config['mail.smtp.max_messages_per_connection'] = 2
        class CloseConnectionAfterDeliveryPolicy(IMTAPolicy):
            def accept_msgdata(self, sender, message):
                decision = PolicyDecision(True)
                decision._close_connection_after_response = True
                return decision
        self.init_mta(policy_class=CloseConnectionAfterDeliveryPolicy)
        
        self.msg.send()
        smtp_transport = self.get_transport()
        interface.stop(force=True)
        
        queue = self.get_received_messages()
        self.assertEqual(1, queue.qsize())
        self.assertEqual(False, smtp_transport.is_connected())
    
    def test_handle_server_which_rejects_all_connections(self):
        class RejectAllConnectionsPolicy(IMTAPolicy):
            def accept_new_connection(self, peer):
                return False
        self.init_mta(policy_class=RejectAllConnectionsPolicy)
        
        self.assertRaises(smtplib.SMTPServerDisconnected, self.msg.send)
    
    def test_handle_error_when_server_is_not_running_at_all(self):
        self.init_mta()
        self.assertEqual(None, self.get_transport())
        interface.config['mail.smtp.server'] = 'localhost:47115'
        
        self.assertRaises(socket.error, self.msg.send)
    
    def test_can_retry_failed_connection(self):
        self.config['mail.message.nr_retries'] = 4
        class DropFirstFourConnectionsPolicy(IMTAPolicy):
            def accept_msgdata(self, sender, message):
                if not hasattr(self, 'nr_connections'):
                    self.nr_connections = 0
                self.nr_connections += 1
                return (self.nr_connections > 4)
        self.init_mta(policy_class=DropFirstFourConnectionsPolicy)
        
        msg = self.build_message()
        self.assertEqual(4, msg.nr_retries)
        msg.send()
        
        queue = self.get_received_messages()
        self.assertEqual(1, queue.qsize())

'''

########NEW FILE########
