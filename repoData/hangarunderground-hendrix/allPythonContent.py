__FILENAME__ = messaging
import copy
import json
import uuid


class RecipientManager(object):
    """
        This class manages all the transports addressable by a single address.
    """

    def __init__(self, transport, address):
        self.address = address
        self.transports = {}

        if transport is not None:
            self.transports[transport.uid] = transport

    def __repr__(self):
        return 'RecipientManager object at %s with %d recipients' % (
            self.address, len(self.transports)
        )

    def add(self, transport):
        """
            add a transport
        """
        self.transports[transport.uid] = transport

    def send(self, string):  # usually a json string...
        """
            sends whatever it is to each transport
        """
        for transport in self.transports.values():
            transport.write(string)

    def remove(self, transport):
        """
            removes a transport if a member of this group
        """
        if transport.uid in self.transports:
            del(self.transports[transport.uid])


class MessageDispatcher(object):
    """
    MessageDispatcher is a PubSub state machine that routes data packets
    through an attribute called "recipients". The recipients attribute is a
    dict structure where the keys are unique addresses and the values are
    instances of RecipientManager. "address"es (i.e. RecipientManagers) are
    created and/or subscribed to. Subscribing to an address results in
    registering a clientswebsocket (i.e. the transport associated to the
    SockJSResource protocol) within a dict that is internal to the Manager
    called "transports".
    RecipientManager's purpose is to expose functions that MessageDispatcher
    can leverage to execute the PubSub process.
    N.B. subscribing a client to an address opens that client to all data
        published to that address. As such it useful to think of addresses as
        channels. To acheive a private channel an obsure address is required.
    """

    def __init__(self, *args, **kwargs):
        self.recipients = {}

    def add(self, transport, address=None):
        """
            add a new recipient to be addressable by this MessageDispatcher
            generate a new uuid address if one is not specified
        """

        if not address:
            address = str(uuid.uuid1())

        if address in self.recipients:
            self.recipients[address].add(transport)
        else:
            self.recipients[address] = RecipientManager(transport, address)

        return address

    def remove(self, transport):
        """
            removes a transport from all channels to which it belongs.
        """
        recipients = copy.copy(self.recipients)
        for address, recManager in recipients.iteritems():
            recManager.remove(transport)
            if not len(recManager.transports):
                del self.recipients[address]

    def send(self, address, data_dict):

        """
            address can either be a string or a list of strings

            data_dict gets sent along as is and could contain anything
        """
        if type(address) == list:
            recipients = [self.recipients.get(rec) for rec in address]
        else:
            recipients = [self.recipients.get(address)]

        if recipients:
            for recipient in recipients:
                if recipient:
                    recipient.send(json.dumps(data_dict))

    def subscribe(self, transport, data):
        """
            adds a transport to a channel
        """

        self.add(transport, address=data.get('hx_subscribe'))

        self.send(
            data.get('hx_subscribe'),
            {'message': "%r is listening" % transport}
        )


def send_json_message(address, message, **kwargs):
    """
        a shortcut for message sending
    """

    data = {
        'message': message,
    }

    if not kwargs.get('subject_id'):
        data['subject_id'] = address

    data.update(kwargs)

    hxdispatcher.send(address, data)


def send_callback_json_message(value, *args, **kwargs):
    """
        useful for sending messages from callbacks as it puts the
        result of the callback in the dict for serialization
    """

    if value:
        kwargs['result'] = value

    send_json_message(args[0], args[1], **kwargs)

    return value


def send_errback_json_message(error, *args, **kwargs):

    kwargs['error'] = error.getErrorMessage()
    send_json_message(args[0], args[1], **kwargs)

    error.trap(RuntimeError)


hxdispatcher = MessageDispatcher()

########NEW FILE########
__FILENAME__ = processing
# from txrdq.rdq import ResizableDispatchQueue

from twisted.internet.threads import deferToThread
from django.dispatch import receiver

from .signals import short_task, long_task
from .messaging import send_callback_json_message, send_json_message, send_errback_json_message

import inspect


def parse_signal_args(kwargs):

    # because of the way django signals work, args will be in kwargs
    args = kwargs['args']

    # we have 2 arguments that we need to pull from the 'args' tuple
    func = args[0]  # the function we will be calling
    args = args[1:][0]  # and the arguments to it

    # and then any keyword args
    kwargs = kwargs['kwargs']

    return func, args, kwargs


@receiver(short_task, dispatch_uid="hendrix.queue_short_task")
def send_short_task(sender, *args, **kwargs):
    """
        preps arguments which can come in many forms
        sendes them to a deferred thread with an optional
        callback to send results through a websocket (or other transport)
    """

    func, args, kwargs = parse_signal_args(kwargs)

    # specific args are used to address the message callback
    rec = kwargs.pop('hxrecipient', None)
    mess = kwargs.pop('hxmessage', None)
    subj = kwargs.pop('hxsubject_id', None)

    additional_callbacks = kwargs.pop('hxcallbacks', [])

    # send this job to a deferred thread
    job = deferToThread(func, *args, **kwargs)

    # and if we have a reciever, add the callback
    if rec:
        job.addCallback(send_callback_json_message, rec, mess, subject_id=subj)

        send_json_message(
            rec,
            'starting...',
            subject_id=subj,
            clear=True
        )

        job.addErrback(send_errback_json_message, rec, mess, subject_id=subj)

    for callback in additional_callbacks:
        job.addCallback(callback)


try:
    from celery import task
    import importlib

    @task
    def run_long_function(function_to_run, *args, **kwargs):
        print function_to_run, args, kwargs
        path_to_module, function_name = function_to_run.rsplit('.', 1)
        module = importlib.import_module(path_to_module)

        result = getattr(module, function_name)(*args, **kwargs)
        return result
except:
    pass


def task_complete_callback(celery_job_in_progress):

    return celery_job_in_progress.get()


@receiver(long_task, dispatch_uid="hendrix.queue_long_task")
def send_long_task(sender, *args, **kwargs):
    """
    preps arguments, sends to some kind of message queue backed task manager?
    sets up a callback which checks for the completion of this task and
    messages interested parties about its completion
    """
    # for external execution, we need to get the module path to the function

    func, args, kwargs = parse_signal_args(kwargs)

    module_name = inspect.getmodule(func).__name__
    func_name = func.__name__
    path_to_function = '%s.%s' % (module_name, func_name)

    # specific args are used to address the message callback
    rec = kwargs.pop('hxrecipient', None)
    mess = kwargs.pop('hxmessage', None)
    subj = kwargs.pop('hxsubject_id', None)
    additional_callbacks = kwargs.pop('hxcallbacks', [])

    try:
        # send this job to celery
        job = run_long_function.delay(path_to_function, *args, **kwargs)

        # create a deferred thread to watch for when it's done
        monitor = deferToThread(task_complete_callback, job)

        # tell someone that this happened?
        if rec:
            send_json_message(
                rec,
                'starting processing...',
                subject_id=subj,
                clear=True
            )
            # hook up notifiecation for when it's finished
            monitor.addCallback(
                send_callback_json_message, rec, mess, subject_id=subj
            )

        for callback in additional_callbacks:
            monitor.addCallback(callback)

        monitor.addErrback(
            send_errback_json_message, rec, mess, subject_id=subj
        )
    except Exception:
        raise NotImplementedError(
            "You must have celery installed and configured to queue long "
            "running tasks"
        )

########NEW FILE########
__FILENAME__ = resources
import json
import uuid

from twisted.internet import threads
from twisted.internet.protocol import Factory, Protocol
from txsockjs.factory import SockJSResource

from hendrix.resources import NamedResource

from .messaging import hxdispatcher
from .signals import message_signal


def send_signal(transport, data):
    message_signal.send(None, dispatcher=transport, data=data)


class MessageHandlerProtocol(Protocol):
    """
        A basic protocol for socket messaging
        using a hendrix messaging dispatcher to handle
        addressing messages to active sockets from
        different contexts
    """
    dispatcher = hxdispatcher
    guid = None

    def dataReceived(self, data):

        """
            Takes "data" which we assume is json encoded
            If data has a subject_id attribute, we pass that to the dispatcher
            as the subject_id so it will get carried through into any
            return communications and be identifiable to the client

            falls back to just passing the message along...

        """
        try:
            address = self.guid
            data = json.loads(data)
            threads.deferToThread(send_signal, self.dispatcher, data)

            if 'hx_subscribe' in data:
                return self.dispatcher.subscribe(self.transport, data)

            if 'address' in data:
                address = data['address']
            else:
                address = self.guid

            self.dispatcher.send(address, data)

        except Exception, exc:
            raise
            self.dispatcher.send(
                self.guid,
                {'message': data, 'error': str(exc)}
            )

    def connectionMade(self):
        """
        establish the address of this new connection and add it to the list of
        sockets managed by the dispatcher

        reply to the transport with a "setup_connection" notice
        containing the recipient's address for use by the client as a return
        address for future communications
        """
        self.transport.uid = str(uuid.uuid1())

        self.guid = self.dispatcher.add(self.transport)
        self.dispatcher.send(self.guid, {'setup_connection': self.guid})

    def connectionLost(self, something):
        "clean up the no longer useful socket in the dispatcher"
        self.dispatcher.remove(self.transport)


MessageResource = NamedResource('messages')
MessageResource.putChild(
    'main',
    SockJSResource(Factory.forProtocol(MessageHandlerProtocol))
)

########NEW FILE########
__FILENAME__ = signals
"""
    Signals for easy use in django projects
"""

from django import dispatch

short_task = dispatch.Signal(providing_args=["args", "kwargs"])

long_task = dispatch.Signal(providing_args=["args", "kwargs"])

message_signal = dispatch.Signal(providing_args=["data", "dispatcher"])

########NEW FILE########
__FILENAME__ = memory_cache
"""
local memory cache backend
"""
from . import CacheBackend
from hendrix.contrib.cache import CachedResource


class MemoryCacheBackend(CacheBackend):

    _cache = {}

    @property
    def cache(self):
        return self._cache

    def addResource(self, content, uri, headers):
        """
        Adds the a hendrix.contrib.cache.resource.CachedResource to the
        ReverseProxy cache connection
        """
        self.cache[uri] = CachedResource(content, headers)

    def resourceExists(self, uri):
        """
        Returns a boolean indicating whether or not the resource is in the
        cache
        """
        return uri in self.cache

    def getResource(self, uri):
        return self.cache[uri]

########NEW FILE########
__FILENAME__ = redis_cache

########NEW FILE########
__FILENAME__ = resource
import cStringIO
import urlparse

from . import decompressBuffer, compressBuffer
from .backends.memory_cache import MemoryCacheBackend

from hendrix.utils import responseInColor

from twisted.internet import reactor
from twisted.web import proxy, client
from twisted.web.server import NOT_DONE_YET
from urllib import quote as urlquote


class CacheClient(proxy.ProxyClient):
    """
    SHOW ME THE CACHE BABY!
    """

    def __init__(self, command, rest, version, headers, data, father, resource):
        proxy.ProxyClient.__init__(
            self, command, rest, version, headers, data, father
        )
        self.resource = resource
        self.buffer = cStringIO.StringIO()
        self._response = None

    def handleHeader(self, key, value):
        "extends handleHeader to save headers to a local response object"
        key_lower = key.lower()
        if key_lower == 'location':
            value = self.modLocationPort(value)
        self._response.headers[key_lower] = value
        if key_lower != 'cache-control':
            # This causes us to not pass on the 'cache-control' parameter
            # to the browser
            # TODO: we should have a means of giving the user the option to
            # configure how they want to manage browser-side cache control
            proxy.ProxyClient.handleHeader(self, key, value)

    def handleStatus(self, version, code, message):
        "extends handleStatus to instantiate a local response object"
        proxy.ProxyClient.handleStatus(self, version, code, message)
        # client.Response is currently just a container for needed data
        self._response = client.Response(version, code, message, {}, None)

    def modLocationPort(self, location):
        """
        Ensures that the location port is a the given port value
        Used in `handleHeader`
        """
        components = urlparse.urlparse(location)
        reverse_proxy_port = self.father.getHost().port
        reverse_proxy_host = self.father.getHost().host
        # returns an ordered dict of urlparse.ParseResult components
        _components = components._asdict()
        _components['netloc'] = '%s:%d' % (
            reverse_proxy_host, reverse_proxy_port
        )
        return urlparse.urlunparse(_components.values())

    def handleResponseEnd(self):
        """
        Extends handleResponseEnd to not care about the user closing/refreshing
        their browser before the response is finished. Also calls cacheContent
        in a thread that we don't care when it finishes.
        """
        try:
            if not self._finished:
                reactor.callInThread(
                    self.resource.cacheContent,
                    self.father,
                    self._response,
                    self.buffer
                )
            proxy.ProxyClient.handleResponseEnd(self)
        except RuntimeError:
            # because we don't care if the user hits
            # refresh before the request is done
            pass

    def handleResponsePart(self, buffer):
        """
        Sends the content to the browser and keeps a local copy of it.
        buffer is just a str of the content to be shown, father is the intial
        request.
        """
        self.father.write(buffer)
        self.buffer.write(buffer)

    def compressBuffer(self, buffer):
        """
        Note that this code compresses into a buffer held in memory, rather
        than a disk file. This is done through the use of cStringIO.StringIO().
        """
        # http://jython.xhaus.com/http-compression-in-python-and-jython/
        zbuf = cStringIO.StringIO()
        zfile = gzip.GzipFile(mode='wb',  fileobj=zbuf, compresslevel=9)
        zfile.write(buffer)
        zfile.close()
        return zbuf.getvalue()



class CacheClientFactory(proxy.ProxyClientFactory):

    protocol = CacheClient

    def __init__(self, command, rest, version, headers, data, father, resource):
        self.command = command
        self.rest = rest
        self.version = version
        self.headers = headers
        self.data = data
        self.father = father
        self.resource = resource

    def buildProtocol(self, addr):
        return self.protocol(
            self.command, self.rest, self.version,
            self.headers, self.data, self.father, self.resource
        )


class CacheProxyResource(proxy.ReverseProxyResource, MemoryCacheBackend):
    """
    This is a state persistent subclass of the built-in ReverseProxyResource.
    """

    def __init__(self, host, to_port, path, reactor=reactor):
        """
        The 'to_port' arg points to the port of the server that we are sending
        a request to
        """
        proxy.ReverseProxyResource.__init__(
            self, host, to_port, path, reactor=reactor
        )
        self.proxyClientFactoryClass = CacheClientFactory

    def getChild(self, path, request):
        """
        This is necessary because the parent class would call
        proxy.ReverseProxyResource instead of CacheProxyResource
        """
        return CacheProxyResource(
            self.host, self.port, self.path + '/' + urlquote(path, safe=""),
            self.reactor
        )

    def getChildWithDefault(self, path, request):
        """
        Retrieve a static or dynamically generated child resource from me.
        """
        cached_resource = self.getCachedResource(request)
        if cached_resource:
            reactor.callInThread(
                responseInColor,
                request,
                '200 OK',
                cached_resource,
                'Cached',
                'underscore'
            )
            return cached_resource
        # original logic
        if path in self.children:
            return self.children[path]
        return self.getChild(path, request)

    def render(self, request):
        """
        Render a request by forwarding it to the proxied server.
        """
        # set up and evaluate a connection to the target server
        if self.port == 80:
            host = self.host
        else:
            host = "%s:%d" % (self.host, self.port)
        request.requestHeaders.addRawHeader('host', host)
        request.content.seek(0, 0)
        qs = urlparse.urlparse(request.uri)[4]
        if qs:
            rest = self.path + '?' + qs
        else:
            rest = self.path

        global_self = self.getGlobalSelf()

        clientFactory = self.proxyClientFactoryClass(
            request.method, rest, request.clientproto,
            request.getAllHeaders(), request.content.read(), request,
            global_self  # this is new
        )
        self.reactor.connectTCP(self.host, self.port, clientFactory)

        return NOT_DONE_YET

    def decompressContent(self):
        self.content = decompressBuffer(self.content)

    def getGlobalSelf(self):
        """
        This searches the reactor for the original instance of
        CacheProxyResource. This is necessary because with each call of
        getChild a new instance of CacheProxyResource is created.
        """
        transports = self.reactor.getReaders()
        for transport in transports:
            try:
                resource = transport.factory.resource
                if isinstance(resource, self.__class__) and resource.port == self.port:
                    return resource
            except AttributeError:
                pass
        return

########NEW FILE########
__FILENAME__ = static
import os
from hendrix.resources import DjangoStaticResource
from django.conf import settings


try:
    DefaultDjangoStaticResource = DjangoStaticResource(
        settings.STATIC_ROOT, settings.STATIC_URL
    )
except AttributeError:
    raise AttributeError(
        "Please make sure you have assigned your STATIC_ROOT and STATIC_URL"
        " settings"
    )

try:
    from django.contrib import admin
    admin_media_path = os.path.join(admin.__path__[0], 'static/admin/')
    DjangoAdminStaticResource = DjangoStaticResource(
        admin_media_path, settings.STATIC_URL+'admin/'
    )
except:
    raise

########NEW FILE########
__FILENAME__ = cache
from hendrix.contrib.cache.resource import CacheProxyResource
from hendrix.services import TCPServer
from twisted.web import server


class CacheService(TCPServer):

    def __init__(self, host, from_port, to_port, path, *args, **kwargs):
        resource = CacheProxyResource(host, to_port, path)
        factory = server.Site(resource)
        TCPServer.__init__(self, from_port, factory)

########NEW FILE########
__FILENAME__ = proxy
from hendrix.services import TCPServer
from twisted.web import server, proxy


class ReverseProxyService(TCPServer):

    def __init__(self, host, from_port, to_port, host, path, *args, **kwargs):
        resource = proxy.ReverseProxyResource(host, to_port, path)
        factory = server.Site(resource)
        TCPServer.__init__(self, from_port, factory)

########NEW FILE########
__FILENAME__ = defaults
CACHE_PORT = 8000
HTTP_PORT = 8080
HTTPS_PORT = 4430


DEFAULT_MAX_AGE = 3600

########NEW FILE########
__FILENAME__ = deploy
import chalk
import importlib
import os
import time

import cPickle as pickle

from os import environ
from sys import executable
from socket import AF_INET

from hendrix import defaults
from hendrix.contrib import ssl
from hendrix.contrib.services.cache import CacheService
from hendrix.options import options as hx_options
from hendrix.resources import get_additional_resources
from hendrix.services import get_additional_services, HendrixService
from hendrix.utils import get_pid
from twisted.application.internet import TCPServer, SSLServer
from twisted.internet import reactor
from twisted.internet.ssl import PrivateCertificate
from twisted.protocols.tls import TLSMemoryBIOFactory


class HendrixDeploy(object):
    """
    HendrixDeploy encapsulates the necessary information needed to deploy the
    HendrixService on a single or multiple processes.
    """

    def __init__(self, action='start', options={}, reactor=reactor):
        self.action = action
        self.options = hx_options()
        self.options.update(options)
        self.services = []
        self.resources = []
        self.reactor = reactor

        self.use_settings = True
        # because running the management command overrides self.options['wsgi']
        if self.options['wsgi']:
            wsgi_dot_path = self.options['wsgi']
            self.application = HendrixDeploy.importWSGI(wsgi_dot_path)
            self.use_settings = False
        else:
            os.environ['DJANGO_SETTINGS_MODULE'] = self.options['settings']
            django_conf = importlib.import_module('django.conf')
            settings = getattr(django_conf, 'settings')
            self.services = get_additional_services(settings)
            self.resources = get_additional_resources(settings)
            self.options = HendrixDeploy.getConf(settings, self.options)

        if self.use_settings:
            wsgi_dot_path = getattr(settings, 'WSGI_APPLICATION', None)
            self.application = HendrixDeploy.importWSGI(wsgi_dot_path)

        self.is_secure = self.options['key'] and self.options['cert']

        self.servers = []

    @classmethod
    def importWSGI(cls, wsgi_dot_path):
        wsgi_module, application_name = wsgi_dot_path.rsplit('.', 1)
        wsgi = importlib.import_module(wsgi_module)
        return getattr(wsgi, application_name, None)

    @classmethod
    def getConf(cls, settings, options):
        "updates the options dict to use config options in the settings module"
        ports = ['http_port', 'https_port', 'cache_port']
        for port_name in ports:
            port = getattr(settings, port_name.upper(), None)
            # only use the settings ports if the defaults were left unchanged
            default = getattr(defaults, port_name.upper())
            if port and options.get(port_name) == default:
                options[port_name] = port

        _opts = [
            ('key', 'hx_private_key'),
            ('cert', 'hx_certficate'),
            ('wsgi', 'wsgi_application')
        ]
        for opt_name, settings_name in _opts:
            opt = getattr(settings, settings_name.upper(), None)
            if opt:
                options[opt_name] = opt

        if not options['settings']:
            options['settings'] = environ['DJANGO_SETTINGS_MODULE']
        return options

    def addServices(self):
        """
        a helper function used in HendrixDeploy.run
        it instanstiates the HendrixService and adds child services
        note that these services will also be run on all processes
        """
        self.addHendrix()

        if not self.options.get('global_cache') and not self.options.get('nocache'):
            self.addLocalCacheService()

        if self.is_secure:
            self.addSSLService()

        self.catalogServers(self.hendrix)

    def addHendrix(self):
        "instantiates the HendrixService"
        self.hendrix = HendrixService(
            self.application, self.options['http_port'],
            resources=self.resources, services=self.services,
            loud=self.options['loud']
        )

    def catalogServers(self, hendrix):
        "collects a list of service names serving on TCP or SSL"
        for service in hendrix.services:
            if isinstance(service, (TCPServer, SSLServer)):
                self.servers.append(service.name)

    def getCacheService(self):
        cache_port = self.options.get('cache_port')
        http_port = self.options.get('http_port')
        return CacheService(
            host='localhost', from_port=cache_port, to_port=http_port, path=''
        )

    def addLocalCacheService(self):
        "adds a CacheService to the instatiated HendrixService"
        _cache = self.getCacheService()
        _cache.setName('cache_proxy')
        _cache.setServiceParent(self.hendrix)

    def addSSLService(self):
        "adds a SSLService to the instaitated HendrixService"
        https_port = self.options['https_port']
        key = self.options['key']
        cert = self.options['cert']

        _tcp = self.hendrix.getServiceNamed('main_web_tcp')
        factory = _tcp.factory

        _ssl = ssl.SSLServer(https_port, factory, key, cert)

        _ssl.setName('main_web_ssl')
        _ssl.setServiceParent(self.hendrix)

    def run(self):
        "sets up the desired services and runs the requested action"
        self.addServices()
        action = self.action
        fd = self.options['fd']

        if action.startswith('start'):
            chalk.blue('Ready and Listening...')
            getattr(self, action)(fd)
            self.reactor.run()
        elif action == 'restart':
            getattr(self, action)(fd=fd)
        else:
            getattr(self, action)()

    @property
    def pid(self):
        "The default location of the pid file for process management"
        return get_pid(self.options)

    def getSpawnArgs(self):
        """
        For the child processes we don't need to specify the SSL or caching
        parameters as
        """
        _args = [
            executable,  # path to python executable e.g. /usr/bin/python
        ]
        if not self.options['loud']:
            _args += ['-W', 'ignore']
        _args += [
            'manage.py',
            'hx',
            'start',
            '--http_port', str(self.options['http_port']),
            '--https_port', str(self.options['https_port']),
            '--cache_port', str(self.options['cache_port']),
            '--workers', '0',
            '--fd', pickle.dumps(self.fds),
        ]
        if self.is_secure:
            _args += [
                '--key', self.options.get('key'),
                '--cert', self.options.get('cert')
            ]
        if self.options['nocache']:
            _args.append('--nocache')
        if self.options['dev']:
            _args.append('--dev')
        if self.options['traceback']:
            _args.append('--traceback')
        if self.options['global_cache']:
            _args.append('--global_cache')
        if not self.use_settings:
            _args += ['--wsgi', self.options['wsgi']]
        return _args

    def addGlobalServices(self):
        if self.options.get('global_cache') and not self.options.get('nocache'):
            _cache = self.getCacheService()
            _cache.startService()

    def start(self, fd=None):
        pids = [str(os.getpid())]  # script pid

        if fd is None:
            # anything in this block is only run once
            self.addGlobalServices()

            self.hendrix.startService()
            if self.options['workers']:
                # Create a new listening port and several other processes to
                # help out.
                childFDs = {0: 0, 1: 1, 2: 2}
                self.fds = {}
                for name in self.servers:
                    port = self.hendrix.get_port(name)
                    fd = port.fileno()
                    childFDs[fd] = fd
                    self.fds[name] = fd
                args = self.getSpawnArgs()
                transports = []
                for i in range(self.options['workers']):
                    transport = self.reactor.spawnProcess(
                        None, executable, args, childFDs=childFDs, env=environ
                    )
                    transports.append(transport)
                    pids.append(str(transport.pid))
            with open(self.pid, 'w') as pid_file:
                pid_file.write('\n'.join(pids))
        else:
            fds = pickle.loads(fd)
            factories = {}
            for name in self.servers:
                factory = self.disownService(name)
                factories[name] = factory
            self.hendrix.startService()
            for name, factory in factories.iteritems():
                if name == 'main_web_ssl':
                    privateCert = PrivateCertificate.loadPEM(
                        open(self.options['cert']).read() + open(self.options['key']).read()
                    )
                    factory = TLSMemoryBIOFactory(
                        privateCert.options(), False, factory
                    )
                port = self.reactor.adoptStreamPort(
                    fds[name], AF_INET, factory
                )

    def stop(self, sig=9):
        with open(self.pid) as pid_file:
            pids = pid_file.readlines()
            for pid in pids:
                try:
                    os.kill(int(pid), sig)
                except OSError:
                    # OSError raised when it trys to kill the child processes
                    pass
        os.remove(self.pid)

    def start_reload(self, fd=None):
        self.start(fd=fd)

    def restart(self, fd=None):
        self.stop()
        time.sleep(1)  # wait a second to ensure the port is closed
        self.start(fd)

    def disownService(self, name):
        """
        disowns a service on hendirix by name
        returns a factory for use in the adoptStreamPort part of setting up
        multiple processes
        """
        _service = self.hendrix.getServiceNamed(name)
        _service.disownServiceParent()
        return _service.factory

########NEW FILE########
__FILENAME__ = hx
from hendrix.ux import launch
from hendrix.options import HX_OPTION_LIST
from django.core.management.base import BaseCommand



class Command(BaseCommand):
    option_list = HX_OPTION_LIST

    def handle(self, *args, **options):
        launch(*args, **options)

########NEW FILE########
__FILENAME__ = options
from hendrix import defaults

from optparse import make_option, OptionParser


def cleanOptions(options):
    """
    Takes an options dict and returns a tuple containing the daemonize boolean,
    the reload boolean, and the parsed list of cleaned options as would be
    expected to be passed to hx
    """
    daemonize = options.pop('daemonize')
    _reload = options.pop('reload')
    dev = options.pop('dev')
    opts = []
    store_true = [
        '--nocache', '--global_cache', '--traceback', '--quiet', '--loud'
    ]
    store_false = []
    for key, value in options.iteritems():
        key = '--' + key
        if (key in store_true and value) or (key in store_false and not value):
            opts += [key, ]
        elif value:
            opts += [key, str(value)]
    return daemonize, _reload, opts


HX_OPTION_LIST = (
    make_option(
        '-v', '--verbosity',
        action='store',
        dest='verbosity',
        default='1',
        type='choice',
        choices=['0', '1', '2', '3'],
        help=(
            'Verbosity level; 0=minimal output, 1=normal output, 2=verbose '
            'output, 3=very verbose output'
        )
    ),
    make_option(
        '--settings',
        dest='settings',
        type=str,
        default='',
        help=(
            'The Python path to a settings module, e.g. "myproj.settings.x".'
            ' If this isn\'t provided, the DJANGO_SETTINGS_MODULE environment '
            'variable will be used.'
        )
    ),
    make_option(
        '--pythonpath',
        help=(
            'A directory to add to the Python path, e.g. '
            '"/home/djangoprojects/myproject".'
        )
    ),
    make_option(
        '--traceback',
        action='store_true',
        help='Raise on exception'
    ),
    make_option(
        '--reload',
        action='store_true',
        dest='reload',
        default=False,
        help=(
            "Flag that watchdog should restart the server when changes to the "
            "codebase occur. NOTE: Do NOT uset this flag with --daemonize "
            "because it will not daemonize."
        )
    ),
    make_option(
        '-l', '--loud',
        action='store_true',
        dest='loud',
        default=False,
        help="Use the custom verbose WSGI handler that prints in color"
    ),
    make_option(
        '-q', '--quiet',
        action='store_true',
        dest='quiet',
        default=False,
        help="Supress all output."
    ),
    make_option(
        '--http_port',
        type=int,
        dest='http_port',
        default=defaults.HTTP_PORT,
        help='Enter a port number for the server to serve content.'
    ),
    make_option(
        '--https_port',
        type=int,
        dest='https_port',
        default=defaults.HTTPS_PORT,
        help='Enter an ssl port number for the server to serve secure content.'
    ),
    make_option(
        '--cache_port',
        type=int,
        dest='cache_port',
        default=defaults.CACHE_PORT,
        help='Enter an cache port number to serve cached content.'
    ),
    make_option(
        '-g', '--global_cache',
        dest='global_cache',
        action='store_true',
        default=False,
        help='Make it so that there is only one cache server'
    ),
    make_option(
        '-n', '--nocache',
        dest='nocache',
        action='store_true',
        default=False,
        help='Disable page cache'
    ),
    make_option(
        '-w', '--workers',
        type=int,
        dest='workers',
        default=0,
        help='Number of processes to run'
    ),
    make_option(
        '--key',
        type=str,
        dest='key',
        default=None,
        help='Absolute path to SSL private key'
    ),
    make_option(
        '--cert',
        type=str,
        dest='cert',
        default=None,
        help='Absolute path to SSL public certificate'
    ),
    make_option(
        '--fd',
        type=str,
        dest='fd',
        default=None,
        help='DO NOT SET THIS'
    ),
    make_option(
        '-d', '--daemonize',
        dest='daemonize',
        action='store_true',
        default=False,
        help='Run in the background'
    ),
    make_option(
        '--dev',
        dest='dev',
        action='store_true',
        default=False,
        help=(
            'Runs in development mode. Meaning it uses the development wsgi '
            'handler subclass'
        )
    ),
    make_option(
        '--wsgi',
        dest='wsgi',
        type=str,
        default=None,
        help=(
            'Overrides the use of django settings for use in testing. N.B. '
            'This option is not for use with hx or hx.py'
        )
    )
)


HendrixOptionParser = OptionParser(
    description=(
        'hx is the interface to hendrix, use to start and stop your server'
    ),
    usage='hx start|stop [options]',
    option_list=HX_OPTION_LIST
)


def options(argv=[]):
    """
    A helper function that returns a dictionary of the default key-values pairs
    """
    parser = HendrixOptionParser
    return vars(parser.parse_args(argv)[0])

########NEW FILE########
__FILENAME__ = resources
import sys
import importlib
from hendrix.utils import responseInColor
from twisted.web import resource, static
from twisted.web.server import NOT_DONE_YET
from twisted.web.wsgi import WSGIResource, _WSGIResponse


import logging

logger = logging.getLogger(__name__)


class DevWSGIResource(WSGIResource):

    def render(self, request):
        """
        Turn the request into the appropriate C{environ} C{dict} suitable to be
        passed to the WSGI application object and then pass it on.

        The WSGI application object is given almost complete control of the
        rendering process.  C{NOT_DONE_YET} will always be returned in order
        and response completion will be dictated by the application object, as
        will the status, headers, and the response body.
        """
        response = LoudWSGIResponse(
            self._reactor, self._threadpool, self._application, request)
        response.start()
        return NOT_DONE_YET


class LoudWSGIResponse(_WSGIResponse):

    def startResponse(self, status, headers, excInfo=None):
        """
        extends startResponse to call speakerBox in a thread
        """
        if self.started and excInfo is not None:
            raise excInfo[0], excInfo[1], excInfo[2]
        self.status = status
        self.headers = headers
        self.reactor.callInThread(
            responseInColor, self.request, status, headers
        )
        return self.write


class HendrixResource(resource.Resource):
    """
    HendrixResource initialises a WSGIResource and stores it as wsgi_resource.
    It also overrides its own getChild method so to only serve wsgi_resource.
    This means that only the WSGIResource is able to serve dynamic content from
    the root url "/". However it is still possible to extend the resource tree
    via putChild. This is due the fact that getChildFromRequest checks for
    children of the resource before handling the dynamic content (through
    getChild). The modified getChild resource on HendrixResource also restores
    the request.postpath list to its original state. This is essentially a hack
    to ensure that django always gets the full path.
    """

    def __init__(self, reactor, threads, application, loud=False):
        resource.Resource.__init__(self)
        if loud:
            self.wsgi_resource = DevWSGIResource(reactor, threads, application)
        else:
            self.wsgi_resource = WSGIResource(reactor, threads, application)

    def getChild(self, name, request):
        """
        Postpath needs to contain all segments of
        the url, if it is incomplete then that incomplete url will be passed on
        to the child resource (in this case our wsgi application).
        """
        request.prepath = []
        request.postpath.insert(0, name)
        # re-establishes request.postpath so to contain the entire path
        return self.wsgi_resource

    def putNamedChild(self, res):
        """
        putNamedChild takes either an instance of hendrix.contrib.NamedResource
        or any resource.Resource with a "namespace" attribute as a means of
        allowing application level control of resource namespacing.

        if a child is already found at an existing path,
        resources with paths that are children of those physical paths
        will be added as children of those resources

        """
        try:
            EmptyResource = resource.Resource
            namespace = res.namespace
            parts = namespace.strip('/').split('/')

            # initialise parent and children
            parent = self
            children = self.children
            # loop through all of the path parts except for the last one
            for name in parts[:-1]:
                child = children.get(name)
                if not child:
                    # if the child does not exist then create an empty one
                    # and associate it to the parent
                    child = EmptyResource()
                    parent.putChild(name, child)
                # update parent and children for the next iteration
                parent = child
                children = parent.children

            name = parts[-1]  # get the path part that we care about
            if children.get(name):
                logger.warning(
                    'A resource already exists at this path. Check '
                    'your resources list to ensure each path is '
                    'unique. The previous resource will be overridden.'
                )
            parent.putChild(name, res)
        except AttributeError:
            # raise an attribute error if the resource `res` doesn't contain
            # the attribute `namespace`
            msg = (
                '%r improperly configured. additional_resources instances must'
                ' have a namespace attribute'
            ) % resource
            raise AttributeError(msg), None, sys.exc_info()[2]


class NamedResource(resource.Resource):
    """
    A resource that can be used to namespace other resources. Expected usage of
    this resource in a django application is:
        ... in myproject.myapp.somemodule ...
            NamespacedRes = NamedResource('some-namespace')
            NamespacedRes.putChild('namex', SockJSResource(FactoryX...))
            NamespacedRes.putChild('namey', SockJSResource(FactoryY...))
        ... then in settings ...
            HENDRIX_CHILD_RESOURCES = (
              'myproject.myapp.somemodule.NamespacedRes',
              ...,
            )
    """
    def __init__(self, namespace):
        resource.Resource.__init__(self)
        self.namespace = namespace

    def getChild(self, path, request):
        """
        By default this resource will yield a ForbiddenResource instance unless
        a request is made for a static child i.e. a child added using putChild
        """
        # override this method if you want to serve dynamic child resources
        return resource.ForbiddenResource("This is a resource namespace.")


class MediaResource(static.File):
    '''
    A simple static service with directory listing disabled
    (gives the client a 403 instead of letting them browse
    a static directory).
    '''
    def directoryListing(self):
        # Override to forbid directory listing
        return resource.ForbiddenResource()


def DjangoStaticResource(path, rel_url='static'):
    """
    takes an app level file dir to find the site root and servers static files
    from static
    Usage:
        [...in app.resource...]
        from hendrix.resources import DjangoStaticResource
        StaticResource = DjangoStaticResource('/abspath/to/static/folder')
        ... OR ...
        StaticResource = DjangoStaticResource(
            '/abspath/to/static/folder', 'custom-static-relative-url'
        )

        [...in settings...]
        HENDRIX_CHILD_RESOURCES = (
            ...,
            'app.resource.StaticResource',
            ...
        )
    """
    rel_url = rel_url.strip('/')
    StaticFilesResource = MediaResource(path)
    StaticFilesResource.namespace = rel_url
    return StaticFilesResource


def get_additional_resources(settings_module):
    """
    if HENDRIX_CHILD_RESOURCES is specified in settings_module,
    it should be a list resources subclassed from hendrix.contrib.NamedResource

    example:

        HENDRIX_CHILD_RESOURCES = (
          'apps.offload.resources.LongRunningProcessResource',
          'apps.chat.resources.ChatResource',
        )
    """

    additional_resources = []

    if hasattr(settings_module, 'HENDRIX_CHILD_RESOURCES'):
        for module_path in settings_module.HENDRIX_CHILD_RESOURCES:
            path_to_module, resource_name = module_path.rsplit('.', 1)
            resource_module = importlib.import_module(path_to_module)

            additional_resources.append(
                getattr(resource_module, resource_name)
            )

    return additional_resources

########NEW FILE########
__FILENAME__ = services
import importlib
from .resources import HendrixResource
from twisted.application import internet, service
from twisted.internet import reactor
from twisted.python.threadpool import ThreadPool
from twisted.web import server

import logging

logger = logging.getLogger(__name__)


class HendrixService(service.MultiService):
    """
    HendrixService is a constructor that facilitates the collection of services
    and the extension of resources on the website by subclassing MultiService.
    'application' refers to a django.core.handlers.wsgi.WSGIHandler
    'resources' refers to a list of Resources with a namespace attribute
    'services' refers to a list of twisted Services to add to the collection.
    """

    def __init__(
            self, application, port=80, resources=None, services=None,
            loud=False):
        service.MultiService.__init__(self)

        # Create, start and add a thread pool service, which is made available
        # to our WSGIResource within HendrixResource
        threads = ThreadPool()
        reactor.addSystemEventTrigger('after', 'shutdown', threads.stop)
        ThreadPoolService(threads).setServiceParent(self)

        # create the base resource and add any additional static resources
        resource = HendrixResource(reactor, threads, application, loud=loud)
        if resources:
            resources = sorted(resources, key=lambda r: r.namespace)
            for res in resources:
                resource.putNamedChild(res)

        factory = server.Site(resource)
        # add a tcp server that binds to port=port
        main_web_tcp = TCPServer(port, factory)
        main_web_tcp.setName('main_web_tcp')
        # to get this at runtime use
        # hedrix_service.getServiceNamed('main_web_tcp')
        main_web_tcp.setServiceParent(self)

        # add any additional services
        if services:
            for srv_name, srv in services:
                srv.setName(srv_name)
                srv.setServiceParent(self)

    def get_port(self, name):
        "Return the port object associated to our tcp server"
        service = self.getServiceNamed(name)
        return service._port

    def add_server(self, name, protocol, server):
        self.servers[(name, protocol)] = server


class ThreadPoolService(service.Service):
    '''
    A simple class that defines a threadpool on init
    and provides for starting and stopping it.
    '''
    def __init__(self, pool):
        "self.pool returns the twisted.python.ThreadPool() instance."
        if not isinstance(pool, ThreadPool):
            msg = '%s must be initialised with a ThreadPool instance'
            raise TypeError(
                msg % self.__class__.__name__
            )
        self.pool = pool

    def startService(self):
        service.Service.startService(self)
        self.pool.start()

    def stopService(self):
        service.Service.stopService(self)
        self.pool.stop()


def get_additional_services(settings_module):
    """
        if HENDRIX_SERVICES is specified in settings_module,
        it should be a list twisted internet services

        example:

            HENDRIX_SERVICES = (
              ('myServiceName', 'apps.offload.services.TimeService'),
            )
    """

    additional_services = []

    if hasattr(settings_module, 'HENDRIX_SERVICES'):
        for name, module_path in settings_module.HENDRIX_SERVICES:
            path_to_module, service_name = module_path.rsplit('.', 1)
            resource_module = importlib.import_module(path_to_module)
            additional_services.append(
                (name, getattr(resource_module, service_name))
            )
    return additional_services


class TCPServer(internet.TCPServer):

    def __init__(self, port, factory, *args, **kwargs):
        internet.TCPServer.__init__(self, port, factory, *args, **kwargs)
        self.factory = factory

########NEW FILE########
__FILENAME__ = flasky
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World!'

########NEW FILE########
__FILENAME__ = settings

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = ()

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.',
        'NAME': '',

        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

ALLOWED_HOSTS = []
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True
MEDIA_ROOT = ''
MEDIA_URL = ''
STATIC_ROOT = ''
STATIC_URL = '/static/'
STATICFILES_DIRS = ()
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

SECRET_KEY = 'NOTREALt@k0)scq$uuph3gjpbhjhd%ipe)04f5d^^1%)%my(%b6&pus_2NOTREAL'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'hendrix.tests.testproject.urls'

WSGI_APPLICATION = 'hendrix.test.testproject.wsgi.application'

TEMPLATE_DIRS = ()

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testproject.views.home', name='home'),
    # url(r'^testproject/', include('testproject.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hendrix.test.testproject.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = test_deploy
from hendrix.test import HendrixTestCase
from mock import patch
from twisted.application import service
from twisted.internet import tcp


class DeployTests(HendrixTestCase):
    "Tests HendrixDeploy"

    def test_settings_doesnt_break(self):
        """
        A placeholder test to ensure that instantiating HendrixDeploy through
        the hx bash script or the manage.py path wont raise any errors
        """
        self.settingsDeploy()

    def test_workers(self):
        "test the expected behaviour of workers and associated functions"
        num_workers = 2
        deploy = self.settingsDeploy('start', {'workers': num_workers})
        with patch.object(deploy.reactor, 'spawnProcess') as _spawnProcess:
            deploy.addServices()
            deploy.start()
            self.assertEqual(_spawnProcess.call_count, num_workers)

    def test_no_workers(self):
        deploy = self.settingsDeploy()
        with patch.object(deploy.reactor, 'spawnProcess') as _spawnProcess:
            deploy.addServices()
            deploy.start()
            self.assertEqual(_spawnProcess.call_count, 0)

    def test_addHendrix(self):
        "test that addHendrix returns a MulitService"
        deploy = self.settingsDeploy()
        deploy.addHendrix()
        self.assertIsInstance(deploy.hendrix, service.MultiService)


    def test_flask_deployment(self):
        deploy = self.wsgiDeploy(options={'wsgi': 'hendrix.test.flasky.app'})
        deploy.addServices()
        deploy.start()
        readers = deploy.reactor.getReaders()
        tcp_readers = [ p for p in readers if isinstance(p, tcp.Port) ]
        ports = [ p.port for p in tcp_readers ]
        self.assertTrue(8000 in ports)
        self.assertTrue(8080 in ports)

########NEW FILE########
__FILENAME__ = test_resources
import mock
import unittest

from hendrix.resources import HendrixResource, NamedResource, WSGIResource
from twisted.web.resource import getChildForRequest, NoResource
from twisted.web.test.requesthelper import DummyRequest


class TestHendrixResource(unittest.TestCase):

    def setUp(self):
        path = '/path/to/child/'
        self.res = NamedResource(path)
        self.hr = HendrixResource(None, None, None)
        self.hr.putNamedChild(self.res)

    def test_putNamedChild_success(self):
        with mock.patch('hendrix.resources.WSGIResource') as wsgi:
            request = DummyRequest(['path', 'to', 'child'])
            actual_res = getChildForRequest(self.hr, request)
            self.assertEqual(self.res, actual_res)

    def test_putNamedChild_very_bad_request(self):
        "check that requests outside of the children go to the WSGIResoure"
        with mock.patch('hendrix.resources.WSGIResource') as wsgi:
            request = DummyRequest(['very', 'wrong', 'uri'])
            actual_res = getChildForRequest(self.hr, request)
            self.assertIsInstance(actual_res, WSGIResource)

    def test_putNamedChild_sort_of_bad_request(self):
        "requests to incorrect subpaths go to NoResource"
        with mock.patch('hendrix.resources.WSGIResource') as wsgi:
            request = DummyRequest(['path', 'to', 'wrong'])
            actual_res = getChildForRequest(self.hr, request)
            self.assertIsInstance(actual_res, NoResource)

########NEW FILE########
__FILENAME__ = test_ux
import os
import sys
from . import HendrixTestCase, TEST_SETTINGS
from hendrix.contrib import SettingsError
from hendrix.options import options as hx_options
from hendrix import ux
from mock import patch
from path import path


class TestMain(HendrixTestCase):

    def setUp(self):
        super(TestMain, self).setUp()
        self.DEFAULTS = hx_options()
        os.environ['DJANGO_SETTINGS_MODULE'] = ''
        self.devnull = open(os.devnull, 'w')
        self.args_list = ['hx', 'start']

    def tearDown(self):
        super(TestMain, self).tearDown()
        self.devnull.close()

    def test_settings_from_system_variable(self):
        django_settings = 'django.inanity'
        os.environ['DJANGO_SETTINGS_MODULE'] = django_settings
        options = self.DEFAULTS
        self.assertEqual(options['settings'], '')
        options = ux.djangoVsWsgi(options)
        self.assertEqual(options['settings'], django_settings)

    def test_settings_wsgi_absense(self):
        self.assertRaises(SettingsError, ux.djangoVsWsgi, self.DEFAULTS)

    def test_user_settings_overrides_system_variable(self):
        django_settings = 'django.inanity'
        os.environ['DJANGO_SETTINGS_MODULE'] = django_settings
        options = self.DEFAULTS
        user_settings = 'myproject.settings'
        options['settings'] = user_settings
        self.assertEqual(options['settings'], user_settings)
        options = ux.djangoVsWsgi(options)
        self.assertEqual(options['settings'], user_settings)

    def test_wsgi_correct_wsgi_path_works(self):
        wsgi_dot_path = 'hendrix.test.wsgi'
        options = self.DEFAULTS
        options.update({'wsgi': wsgi_dot_path})
        options = ux.djangoVsWsgi(options)
        self.assertEqual(options['wsgi'], wsgi_dot_path)

    def test_wsgi_wrong_path_raises(self):
        wsgi_dot_path = '_this.leads.nowhere.man'
        options = self.DEFAULTS
        options.update({'wsgi': wsgi_dot_path})

        self.assertRaises(ImportError, ux.djangoVsWsgi, options)

    def test_cwd_exposure(self):
        cwd = os.getcwd()
        _path = sys.path
        sys.path = [ p for p in _path if p != cwd ]
        self.assertTrue(cwd not in sys.path)
        ux.exposeProject(self.DEFAULTS)
        self.assertTrue(cwd in sys.path)

    def test_pythonpath(self):
        options = self.DEFAULTS
        test_path = os.path.join(
            path(os.getcwd()).parent,
            'hendrix/test/testproject'
        )
        options['pythonpath'] = test_path
        ux.exposeProject(options)
        self.assertTrue(test_path in sys.path)
        sys.path = [ p for p in sys.path if p != test_path ]

    def test_shitty_pythonpath(self):
        options = self.DEFAULTS
        test_path = '/if/u/have/this/path/you/suck'
        options['pythonpath'] = test_path
        self.assertRaises(IOError, ux.exposeProject, options)

    def test_dev_friendly_options(self):
        options = self.DEFAULTS
        options['dev'] = True
        self.assertFalse(options['reload'])
        self.assertFalse(options['loud'])
        options = ux.devFriendly(options)
        self.assertTrue(options['reload'])
        self.assertTrue(options['loud'])

    def test_noise_control_quiet(self):
        options = self.DEFAULTS
        options['quiet'] = True
        stdout = sys.stdout
        stderr = sys.stderr
        redirect = ux.noiseControl(options)
        self.assertEqual(sys.stdout.name, self.devnull.name)
        self.assertEqual(sys.stderr.name, self.devnull.name)
        sys.stdout = stdout
        sys.stderr = stderr

        self.assertEqual(redirect.name, self.devnull.name)

    def test_noise_control_daemonize(self):
        options = self.DEFAULTS
        options['quiet'] = True
        options['daemonize'] = True
        stdout = sys.stdout
        stderr = sys.stderr
        redirect = ux.noiseControl(options)
        self.assertEqual(sys.stdout.name, stdout.name)
        self.assertEqual(sys.stderr.name, stderr.name)

        self.assertEqual(redirect.name, self.devnull.name)

    def test_noise_control_traceback(self):
        options = self.DEFAULTS
        options['quiet'] = True
        options['daemonize'] = True
        options['traceback'] = True
        stdout = sys.stdout
        stderr = sys.stderr
        redirect = ux.noiseControl(options)
        self.assertEqual(sys.stdout.name, stdout.name)
        self.assertEqual(sys.stderr.name, stderr.name)

        self.assertEqual(redirect, None)

    def test_noise_control_quiet_traceback(self):
        options = self.DEFAULTS
        options['quiet'] = True
        options['traceback'] = True
        stdout = sys.stdout
        stderr = sys.stderr
        redirect = ux.noiseControl(options)
        self.assertEqual(sys.stdout.name, self.devnull.name)
        self.assertEqual(sys.stderr.name, self.devnull.name)
        sys.stdout = stdout
        sys.stderr = stderr

        self.assertEqual(redirect, None)

    def test_main_with_daemonize(self):
        sys.argv = self.args_list + ['-d', '--settings', TEST_SETTINGS]
        class Process(object):
            def poll(self):
                return 0
        with patch('time.sleep') as sleep:
            with patch('subprocess.Popen') as popen:
                popen.return_value = Process()
                ux.main()
                self.assertTrue(popen.called)
                self.assertTrue('--settings' in popen.call_args[0][0])
        sys.argv = []


    def test_options_structure(self):
        """
        A test to ensure that HendrixDeploy.options also has the complete set
        of options available
        """
        deploy = self.wsgiDeploy()
        expected_keys = self.DEFAULTS.keys()
        actual_keys = deploy.options.keys()
        self.assertListEqual(expected_keys, actual_keys)

########NEW FILE########
__FILENAME__ = wsgi
def application(environ, start_response):
    """Basic WSGI Application"""
    start_response('200 OK', [('Content-type','text/plain')])
    return ['Hello World!']
########NEW FILE########
__FILENAME__ = conf
import jinja2
import yaml
from . import SHARE_PATH


def generateInitd(conf_file):
    """
    Helper function to generate the text content needed to create an init.d
    executable
    """
    allowed_opts = [
        'virtualenv', 'project_path', 'settings', 'processes',
        'http_port', 'cache', 'cache_port', 'https_port', 'key', 'cert'
    ]
    base_opts = ['--daemonize', ]  # always daemonize
    options = base_opts
    with open(conf_file, 'r') as cfg:
        conf = yaml.load(cfg)
    conf_specs = set(conf.keys())

    if len(conf_specs - set(allowed_opts)):
        raise RuntimeError('Improperly configured.')

    try:
        virtualenv = conf.pop('virtualenv')
        project_path = conf.pop('project_path')
    except:
        raise RuntimeError('Improperly configured.')

    cache = False
    if 'cache' in conf:
        cache = conf.pop('cache')
    if not cache:
        options.append('--nocache')

    workers = 0
    if 'processes' in conf:
        processes = conf.pop('processes')
        workers = int(processes) - 1
    if workers > 0:
        options += ['--workers', workers]

    for key, value in conf.iteritems():
        options += ['--%s' % key, str(value)]

    with open(os.path.join(SHARE_PATH, 'init.d.j2'), 'r') as f:
        TEMPLATE_FILE = f.read()
    template = jinja2.Template(TEMPLATE_FILE)

    initd_content = template.render(
        {
            'venv_path': virtualenv,
            'project_path': project_path,
            'hendrix_opts': ' '.join(options)
        }
    )

    return initd_content

########NEW FILE########
__FILENAME__ = ux
"""
A module to encapsulate the user experience logic
"""

import chalk
import os
import subprocess
import sys
import time
import traceback
from .options import HendrixOptionParser, cleanOptions
from hendrix.contrib import SettingsError
from hendrix.deploy import HendrixDeploy
from path import path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class Reload(FileSystemEventHandler):

    def __init__(self, options, *args, **kwargs):
        super(Reload, self).__init__(*args, **kwargs)
        daemonize, self.reload, self.options = cleanOptions(options)
        if not self.reload:
            raise RuntimeError(
                'Reload should not be run if --reload has not been passed to '
                'the command as an option.'
            )
        self.process = subprocess.Popen(
            ['hx', 'start_reload'] + self.options
        )

    def on_any_event(self, event):
        if event.is_directory:
            return
        ext = path(event.src_path).ext
        if ext == '.py':
            self.process = self.restart()
            chalk.eraser()
            chalk.yellow("Detected changes, restarting...")

    def restart(self):
        self.process.kill()
        process = subprocess.Popen(
            ['hx', 'start_reload'] + self.options
        )
        return process


def launch(*args, **options):
    """
    launch acts on the user specified action and options by executing
    Hedrix.run
    """
    action = args[0]
    if options['reload']:
        event_handler = Reload(options)
        observer = Observer()
        observer.schedule(event_handler, path='.', recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            pid = os.getpid()
            chalk.eraser()
            chalk.green('\nHendrix successfully closed.')
            os.kill(pid, 15)
        observer.join()
        exit('\n')
    else:
        try:
            deploy = HendrixDeploy(action, options)
            deploy.run()
        except Exception, e:
            if options.get('traceback'):
                tb = sys.exc_info()[2]
                msg = traceback.format_exc(tb)
            else:
                msg = str(e)
            chalk.red(msg, pipe=chalk.stderr)
            os._exit(1)


def djangoVsWsgi(options):
    # settings logic
    if not options['wsgi']:
        user_settings = options['settings']
        settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
        if not settings_module and not user_settings:
            msg = (
                '\nEither specify:\n--settings mysettings.dot.path\nOR\n'
                'export DJANGO_SETTINGS_MODULE="mysettings.dot.path"'
            )
            raise SettingsError(chalk.format_red(msg)), None, sys.exc_info()[2]
        elif user_settings:
            options['settings'] = user_settings
        elif settings_module:
            options['settings'] = settings_module
    else:
        try:
            HendrixDeploy.importWSGI(options['wsgi'])
        except ImportError:
            raise ImportError("The path '%s' does not exist" % options['wsgi'])

    return options


def exposeProject(options):
    # sys.path logic
    if options['pythonpath']:
        project_path = path(options['pythonpath'])
        if not project_path.exists():
            raise IOError("The path '%s' does not exist" % project_path)
        sys.path.append(project_path)
    else:
        sys.path.append(os.getcwd())


def devFriendly(options):
    # if the dev option is given then also set reload to true
    # note that clean options will remove reload so to honor that we use get
    # in the second part of the conditional
    options['reload'] = True if options['dev'] else options.get('reload', False)
    options['loud'] = True if options['dev'] else options['loud']
    return options


def noiseControl(options):
    # terminal noise/info logic
    devnull = open(os.devnull, 'w')
    if options['quiet'] and not options['daemonize']:
        sys.stdout = devnull
        sys.stderr = devnull
    redirect = devnull if not options['traceback'] else None
    return redirect


def main():
    "The function to execute when running hx"
    options, args = HendrixOptionParser.parse_args(sys.argv[1:])
    options = vars(options)

    action = args[0]

    options = djangoVsWsgi(options)

    exposeProject(options)

    options = devFriendly(options)

    redirect = noiseControl(options)

    try:
        if action == 'start' and not options['daemonize']:
            chalk.eraser()
            chalk.blue('Starting Hendrix...')
        elif action == 'stop':
            chalk.green('Stopping Hendrix...')
        if options['daemonize']:
            daemonize, _reload, opts = cleanOptions(options)
            process = subprocess.Popen(
                ['hx', action] + opts, stdout=redirect, stderr=redirect
            )
            time.sleep(2)
            if process.poll():
                raise RuntimeError
        else:
            launch(*args, **options)
            if action not in ['start_reload', 'restart']:
                chalk.eraser()
                chalk.green('\nHendrix successfully closed.')
    except Exception, e:
        msg = (
            'ERROR: %s\nCould not %s hendrix. Try again using the --traceback '
            'flag for more information.'
        )
        chalk.red(msg % (str(e), action), pipe=chalk.stderr)
        if options['traceback']:
            raise
        else:
            os._exit(1)

########NEW FILE########
