__FILENAME__ = changes
# -*- Mode: Python; test-case-name: paisley.test.test_changes -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2011
# See LICENSE for details.

from urllib import urlencode

from twisted.internet import error, defer
from twisted.protocols import basic

from paisley.client import json


class ChangeReceiver(basic.LineReceiver):
    # figured out by checking the last two characters on actually received
    # lines
    delimiter = '\n'

    def __init__(self, notifier):
        self._notifier = notifier

    def lineReceived(self, line):
        if not line:
            return

        change = json.loads(line)

        if not 'id' in change:
            return

        self._notifier.changed(change)

    def connectionLost(self, reason):
        self._notifier.connectionLost(reason)


class ChangeListener:
    """
    I am an interface for receiving changes from a L{ChangeNotifier}.
    """

    def changed(self, change):
        """
        @type  change: dict of str -> str

        The given change was received.
        Only changes that contain an id get received.

        A change is a dictionary with:
          - id:  document id
          - seq: sequence number of change
          - changes: list of dict containing document revisions
          - deleted (optional)
        """
        pass

    def connectionLost(self, reason):
        """
        @type  reason: L{twisted.python.failure.Failure}
        """
        pass


class ChangeNotifier(object):

    def __init__(self, db, dbName, since=None):
        self._db = db
        self._dbName = dbName

        self._caches = []
        self._listeners = []
        self._prot = None

        self._since = since

        self._running = False

    def addCache(self, cache):
        self._caches.append(cache)

    def addListener(self, listener):
        self._listeners.append(listener)

    def isRunning(self):
        return self._running

    def start(self, **kwargs):
        """
        Start listening and notifying of changes.
        Separated from __init__ so you can add caches and listeners.

        By default, I will start listening from the most recent change.
        """
        assert 'feed' not in kwargs, \
            "ChangeNotifier always listens continuously."

        d = defer.succeed(None)

        def setSince(info):
            self._since = info['update_seq']

        if self._since is None:
            d.addCallback(lambda _: self._db.infoDB(self._dbName))
            d.addCallback(setSince)

        def requestChanges():
            kwargs['feed'] = 'continuous'
            kwargs['since'] = self._since
            # FIXME: str should probably be unicode, as dbName can be
            url = str(self._db.url_template %
                '/%s/_changes?%s' % (self._dbName, urlencode(kwargs)))
            return self._db.client.request('GET', url)
        d.addCallback(lambda _: requestChanges())

        def requestCb(response):
            self._prot = ChangeReceiver(self)
            response.deliverBody(self._prot)
            self._running = True
        d.addCallback(requestCb)

        def returnCb(_):
            return self._since
        d.addCallback(returnCb)
        return d

    def stop(self):
        # FIXME: this should produce a clean stop, but it does not.
        # From http://twistedmatrix.com/documents/current/web/howto/client.html
        # "If it is decided that the rest of the response body is not desired,
        # stopProducing can be used to stop delivery permanently; after this,
        # the protocol's connectionLost method will be called."
        self._running = False
        self._prot.stopProducing()

    # called by receiver

    def changed(self, change):
        seq = change.get('seq', None)
        if seq:
            self._since = seq

        for cache in self._caches:
            cache.delete(change['id'])

        for listener in self._listeners:
            listener.changed(change)

    def connectionLost(self, reason):
        # even if we asked to stop, we still get
        # a twisted.web._newclient.ResponseFailed containing
        #   twisted.internet.error.ConnectionDone
        # and
        #   twisted.web.http._DataLoss
        # If we actually asked to stop, just pass through only ConnectionDone

        # FIXME: poking at internals to get failures ? Yuck!
        from twisted.web import _newclient
        if reason.check(_newclient.ResponseFailed):
            if reason.value.reasons[0].check(error.ConnectionDone) and \
                not self.isRunning():
                reason = reason.value.reasons[0]

        self._prot = None
        self._running = False
        for listener in self._listeners:
            listener.connectionLost(reason)

########NEW FILE########
__FILENAME__ = client
# -*- Mode: Python; test-case-name: paisley.test.test_client -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2007-2008
# See LICENSE for details.

"""
CouchDB client.
"""

from paisley import pjson as json

from encodings import utf_8
import logging
import new

from urllib import urlencode, quote
from zope.interface import implements

from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer

from twisted.internet.defer import Deferred, maybeDeferred
from twisted.internet.protocol import Protocol

try:
    from base64 import b64encode
except ImportError:
    import base64

    def b64encode(s):
        return "".join(base64.encodestring(s).split("\n"))


def short_print(body, trim=255):
    # don't go nuts on possibly huge log entries
    # since we're a library we should try to avoid calling this and instead
    # write awesome logs
    if not isinstance(body, basestring):
        body = str(body)
    if len(body) < trim:
        return body.replace('\n', '\\n')
    else:
        return body[:trim].replace('\n', '\\n') + '...'

try:
    from functools import partial
except ImportError:

    class partial(object):

        def __init__(self, fn, *args, **kw):
            self.fn = fn
            self.args = args
            self.kw = kw

        def __call__(self, *args, **kw):
            if kw and self.kw:
                d = self.kw.copy()
                d.update(kw)
            else:
                d = kw or self.kw
            return self.fn(*(self.args + args), **d)

SOCK_TIMEOUT = 300


class StringProducer(object):
    """
    Body producer for t.w.c.Agent
    """
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        return maybeDeferred(consumer.write, self.body)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class ResponseReceiver(Protocol):
    """
    Assembles HTTP response from return stream.
    """

    def __init__(self, deferred, decode_utf8):
        self.recv_chunks = []
        self.decoder = utf_8.IncrementalDecoder() if decode_utf8 else None
        self.deferred = deferred

    def dataReceived(self, bytes, final=False):
        if self.decoder:
            bytes = self.decoder.decode(bytes, final)
        self.recv_chunks.append(bytes)

    def connectionLost(self, reason):
        # _newclient and http import reactor
        from twisted.web._newclient import ResponseDone
        from twisted.web.http import PotentialDataLoss

        if reason.check(ResponseDone) or reason.check(PotentialDataLoss):
            self.dataReceived('', final=True)
            self.deferred.callback(''.join(self.recv_chunks))
        else:
            self.deferred.errback(reason)


class CouchDB(object):
    """
    CouchDB client: hold methods for accessing a couchDB.
    """

    def __init__(self, host, port=5984, dbName=None,
                 username=None, password=None, disable_log=False,
                 version=(1, 0, 1)):
        """
        Initialize the client for given host.

        @param host: address of the server.
        @type host: C{str}

        @param port: if specified, the port of the server.
        @type port: C{int}

        @param dbName: if specified, all calls needing a database name will use
            this one by default.
        @type dbName: C{str}
        """
        from twisted.internet import reactor
        # t.w.c imports reactor
        from twisted.web.client import Agent
        self.client = Agent(reactor)
        self.host = host
        self.port = int(port)
        self.username = username
        self.password =password
        self.url_template = "http://%s:%s%%s" % (self.host, self.port)
        if dbName is not None:
            self.bindToDB(dbName)

        if disable_log:
            # since this is the db layer, and we generate a lot of logs,
            # let people disable them completely if they want to.
            levels = ['trace', 'debug', 'info', 'warn', 'error', 'exception']

            class FakeLog(object):
                pass

            def nullfn(self, *a, **k):
                pass
            self.log = FakeLog()
            for level in levels:
                self.log.__dict__[level] = new.instancemethod(nullfn, self.log)
        else:
            self.log = logging.getLogger('paisley')


        self.log.debug("[%s%s:%s/%s] init new db client",
                       '%s@' % (username, ) if username else '',
                       host,
                       port,
                       dbName if dbName else '')
        self.version = version

    def parseResult(self, result):
        """
        Parse JSON result from the DB.
        """
        return json.loads(result)

    def bindToDB(self, dbName):
        """
        Bind all operations asking for a DB name to the given DB.
        """
        for methname in ["createDB", "deleteDB", "infoDB", "listDoc",
                         "openDoc", "saveDoc", "deleteDoc", "openView",
                         "tempView"]:
            method = getattr(self, methname)
            newMethod = partial(method, dbName)
            setattr(self, methname, newMethod)

    # Database operations

    def createDB(self, dbName):
        """
        Creates a new database on the server.

        @type  dbName: str
        """
        # Responses: {u'ok': True}, 409 Conflict, 500 Internal Server Error,
        # 401 Unauthorized
        # 400 {"error":"illegal_database_name","reason":"Only lowercase
        # characters (a-z), digits (0-9), and any of the characters _, $, (,
        # ), +, -, and / are allowed. Must begin with a letter."}

        return self.put("/%s/" % (dbName, ), "", descr='CreateDB'
            ).addCallback(self.parseResult)

    def deleteDB(self, dbName):
        """
        Deletes the database on the server.

        @type  dbName: str
        """
        # Responses: {u'ok': True}, 404 Object Not Found
        return self.delete("/%s/" % (dbName, )
            ).addCallback(self.parseResult)

    def listDB(self):
        """
        List the databases on the server.
        """
        # Responses: list of db names
        return self.get("/_all_dbs", descr='listDB').addCallback(
            self.parseResult)

    def getVersion(self):
        """
        Returns the couchDB version.
        """
        # Responses: {u'couchdb': u'Welcome', u'version': u'1.1.0'}
        # Responses: {u'couchdb': u'Welcome', u'version': u'1.1.1a1162549'}
        d = self.get("/", descr='version').addCallback(self.parseResult)

        def cacheVersion(result):
            self.version = self._parseVersion(result['version'])
            return result
        return d.addCallback(cacheVersion)

    def _parseVersion(self, versionString):

        def onlyInt(part):
            import re
            intRegexp = re.compile("^(\d+)")
            m = intRegexp.search(part)
            if not m:
                return None
            return int(m.expand('\\1'))

        ret = tuple(onlyInt(_) for _ in versionString.split('.'))
        return ret

    def infoDB(self, dbName):
        """
        Returns info about the couchDB.
        """
        # Responses: {u'update_seq': 0, u'db_name': u'mydb', u'doc_count': 0}
        # 404 Object Not Found
        return self.get("/%s/" % (dbName, ), descr='infoDB'
            ).addCallback(self.parseResult)

    # Document operations

    def listDoc(self, dbName, reverse=False, startkey=None, endkey=None,
                include_docs=False, limit=-1, **obsolete):
        """
        List all documents in a given database.
        """
        # Responses: {u'rows': [{u'_rev': -1825937535, u'_id': u'mydoc'}],
        # u'view': u'_all_docs'}, 404 Object Not Found
        import warnings
        if 'count' in obsolete:
            warnings.warn("listDoc 'count' parameter has been renamed to "
                          "'limit' to reflect changing couchDB api",
                          DeprecationWarning)
            limit = obsolete.pop('count')
        if obsolete:
            raise AttributeError("Unknown attribute(s): %r" % (
                obsolete.keys(), ))
        uri = "/%s/_all_docs" % (dbName, )
        args = {}
        if reverse:
            args["reverse"] = "true"
        if startkey:
            args["startkey"] = json.dumps(startkey)
        if endkey:
            args["endkey"] = json.dumps(endkey)
        if include_docs:
            args["include_docs"] = True
        if limit >= 0:
            args["limit"] = int(limit)
        if args:
            uri += "?%s" % (urlencode(args), )
        return self.get(uri, descr='listDoc').addCallback(self.parseResult)

    def openDoc(self, dbName, docId, revision=None, full=False, attachment=""):
        """
        Open a document in a given database.

        @type docId: C{unicode}

        @param revision: if specified, the revision of the document desired.
        @type revision: C{unicode}

        @param full: if specified, return the list of all the revisions of the
            document, along with the document itself.
        @type full: C{bool}

        @param attachment: if specified, return the named attachment from the
            document.
        @type attachment: C{str}
        """
        # Responses: {u'_rev': -1825937535, u'_id': u'mydoc', ...}
        # 404 Object Not Found

        # FIXME: remove these conversions and have our callers do them
        docId = unicode(docId)
        assert type(docId) is unicode, \
            'docId is %r instead of unicode' % (type(docId), )

        if revision:
            revision = unicode(revision)
            assert type(revision) is unicode, \
                'revision is %r instead of unicode' % (type(revision), )

        uri = "/%s/%s" % (dbName, quote(docId.encode('utf-8')))
        if revision is not None:
            uri += "?%s" % (urlencode({"rev": revision.encode('utf-8')}), )
        elif full:
            uri += "?%s" % (urlencode({"full": "true"}), )
        elif attachment:
            uri += "/%s" % quote(attachment)
            # No parsing
            return self.get(uri, descr='openDoc', isJson=False)
        return self.get(uri, descr='openDoc').addCallback(self.parseResult)

    def addAttachments(self, document, attachments):
        """
        Add attachments to a document, before sending it to the DB.

        @param document: the document to modify.
        @type document: C{dict}

        @param attachments: the attachments to add.
        @type attachments: C{dict}
        """
        document.setdefault("_attachments", {})
        for name, data in attachments.iteritems():
            data = b64encode(data)
            document["_attachments"][name] = {"type": "base64", "data": data}

    def saveDoc(self, dbName, body, docId=None):
        """
        Save/create a document to/in a given database.

        @param dbName: identifier of the database.
        @type dbName: C{str}

        @param body: content of the document.
        @type body: C{str} or any structured object

        @param docId: if specified, the identifier to be used in the database.
        @type docId: C{unicode}
        """
        # Responses: {'rev': '1-9dd776365618752ddfaf79d9079edf84',
        #             'ok': True, 'id': '198abfee8852816bc112992564000295'}

        # 404 Object not found (if database does not exist)
        # 409 Conflict, 500 Internal Server Error
        if docId:
            # FIXME: remove these conversions and have our callers do them
            docId = unicode(docId)
            assert type(docId) is unicode, \
                'docId is %r instead of unicode' % (type(docId), )

        if not isinstance(body, (str, unicode)):
            body = json.dumps(body)
        if docId is not None:
            d = self.put("/%s/%s" % (dbName, quote(docId.encode('utf-8'))),
                body, descr='saveDoc')
        else:
            d = self.post("/%s/" % (dbName, ), body, descr='saveDoc')
        return d.addCallback(self.parseResult)

    def deleteDoc(self, dbName, docId, revision):
        """
        Delete a document on given database.

        @param dbName:   identifier of the database.
        @type  dbName:   C{str}

        @param docId:    the document identifier to be used in the database.
        @type  docId:    C{unicode}

        @param revision: the revision of the document to delete.
        @type  revision: C{unicode}

        """
        # Responses: {u'_rev': 1469561101, u'ok': True}
        # 500 Internal Server Error

        docId = unicode(docId)
        assert type(docId) is unicode, \
            'docId is %r instead of unicode' % (type(docId), )

        revision = unicode(revision)
        assert type(revision) is unicode, \
            'revision is %r instead of unicode' % (type(revision), )


        return self.delete("/%s/%s?%s" % (
                dbName,
                quote(docId.encode('utf-8')),
                urlencode({'rev': revision.encode('utf-8')}))).addCallback(
                    self.parseResult)

    # View operations

    def openView(self, dbName, docId, viewId, **kwargs):
        """
        Open a view of a document in a given database.
        """
        # Responses:
        # 500 Internal Server Error (illegal database name)

        def buildUri(dbName=dbName, docId=docId, viewId=viewId, kwargs=kwargs):
            return "/%s/_design/%s/_view/%s?%s" % (
                dbName, quote(docId), viewId, urlencode(kwargs))

        # if there is a "keys" argument, remove it from the kwargs
        # dictionary now so that it doesn't get double JSON-encoded
        body = None
        if "keys" in kwargs:
            body = json.dumps({"keys": kwargs.pop("keys")})

        # encode the rest of the values with JSON for use as query
        # arguments in the URI
        for k, v in kwargs.iteritems():
            if k == 'keys': # we do this below, for the full body
                pass
            else:
                kwargs[k] = json.dumps(v)
        # we keep the paisley API, but couchdb uses limit now
        if 'count' in kwargs:
            kwargs['limit'] = kwargs.pop('count')

        # If there's a list of keys to send, POST the
        # query so that we can upload the keys as the body of
        # the POST request, otherwise use a GET request
        if body:
            return self.post(
                buildUri(), body=body, descr='openView').addCallback(
                    self.parseResult)
        else:
            return self.get(
                buildUri(), descr='openView').addCallback(
                    self.parseResult)

    def addViews(self, document, views):
        """
        Add views to a document.

        @param document: the document to modify.
        @type document: C{dict}

        @param views: the views to add.
        @type views: C{dict}
        """
        document.setdefault("views", {})
        for name, data in views.iteritems():
            document["views"][name] = data

    def tempView(self, dbName, view):
        """
        Make a temporary view on the server.
        """
        if not isinstance(view, (str, unicode)):
            view = json.dumps(view)
        d = self.post("/%s/_temp_view" % (dbName, ), view, descr='tempView')
        return d.addCallback(self.parseResult)

    # Basic http methods

    def _getPage(self, uri, method="GET", postdata=None, headers=None,
            isJson=True):
        """
        C{getPage}-like.
        """

        def cb_recv_resp(response):
            d_resp_recvd = Deferred()
            content_type = response.headers.getRawHeaders('Content-Type',
                    [''])[0].lower().strip()
            decode_utf8 = 'charset=utf-8' in content_type or \
                    content_type == 'application/json'
            response.deliverBody(ResponseReceiver(d_resp_recvd,
                decode_utf8=decode_utf8))
            return d_resp_recvd.addCallback(cb_process_resp, response)

        def cb_process_resp(body, response):
            # twisted.web.error imports reactor
            from twisted.web import error as tw_error

            # Emulate HTTPClientFactory and raise t.w.e.Error
            # and PageRedirect if we have errors.
            if response.code > 299 and response.code < 400:
                raise tw_error.PageRedirect(response.code, body)
            elif response.code > 399:
                raise tw_error.Error(response.code, body)

            return body

        uurl = unicode(self.url_template % (uri, ))
        url = uurl.encode('utf-8')

        if not headers:
            headers = {}

        if isJson:
            headers["Accept"] = ["application/json"]
            headers["Content-Type"] = ["application/json"]

        if self.username:
            headers["Authorization"] = ["Basic %s" % b64encode(
                "%s:%s" % (self.username, self.password))]

        body = StringProducer(postdata) if postdata else None

        d = self.client.request(method, url, Headers(headers), body)

        d.addCallback(cb_recv_resp)

        return d

    def get(self, uri, descr='', isJson=True):
        """
        Execute a C{GET} at C{uri}.
        """
        self.log.debug("[%s:%s%s] GET %s",
                       self.host, self.port, short_print(uri), descr)
        return self._getPage(uri, method="GET", isJson=isJson)

    def post(self, uri, body, descr=''):
        """
        Execute a C{POST} of C{body} at C{uri}.
        """
        self.log.debug("[%s:%s%s] POST %s: %s",
                      self.host, self.port, short_print(uri), descr,
                      short_print(repr(body)))
        return self._getPage(uri, method="POST", postdata=body)

    def put(self, uri, body, descr=''):
        """
        Execute a C{PUT} of C{body} at C{uri}.
        """
        self.log.debug("[%s:%s%s] PUT %s: %s",
                       self.host, self.port, short_print(uri), descr,
                       short_print(repr(body)))
        return self._getPage(uri, method="PUT", postdata=body)

    def delete(self, uri, descr=''):
        """
        Execute a C{DELETE} at C{uri}.
        """
        self.log.debug("[%s:%s%s] DELETE %s",
                       self.host, self.port, short_print(uri), descr)
        return self._getPage(uri, method="DELETE")

########NEW FILE########
__FILENAME__ = mapping
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2009 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Mapping from raw JSON data structures to Python objects and vice versa.

>>> from couchdb import Server
>>> server = Server('http://localhost:5984/')
>>> db = server.create('python-tests')

To define a document mapping, you declare a Python class inherited from
`Document`, and add any number of `Field` attributes:

>>> class Person(Document):
...     name = TextField()
...     age = IntegerField()
...     added = DateTimeField(default=datetime.now)
>>> person = Person(name='John Doe', age=42)
>>> person.store(db) #doctest: +ELLIPSIS
<Person ...>
>>> person.age
42

You can then load the data from the CouchDB server through your `Document`
subclass, and conveniently access all attributes:

>>> person = Person.load(db, person.id)
>>> old_rev = person.rev
>>> person.name
u'John Doe'
>>> person.age
42
>>> person.added                #doctest: +ELLIPSIS
datetime.datetime(...)

To update a document, simply set the attributes, and then call the ``store()``
method:

>>> person.name = 'John R. Doe'
>>> person.store(db)            #doctest: +ELLIPSIS
<Person ...>

If you retrieve the document from the server again, you should be getting the
updated data:

>>> person = Person.load(db, person.id)
>>> person.name
u'John R. Doe'
>>> person.rev != old_rev
True

>>> del server['python-tests']
"""

import copy

from calendar import timegm
from datetime import date, datetime, time
from decimal import Decimal
from time import strptime, struct_time

__all__ = ['Mapping', 'Document', 'Field', 'TextField', 'FloatField',
           'IntegerField', 'LongField', 'BooleanField', 'DecimalField',
           'DateField', 'DateTimeField', 'TimeField', 'DictField', 'ListField',
           'TupleField']
__docformat__ = 'restructuredtext en'

DEFAULT = object()


class Field(object):
    """Basic unit for mapping a piece of data between Python and JSON.
    
    Instances of this class can be added to subclasses of `Document` to describe
    the mapping of a document.
    """

    def __init__(self, name=None, default=None):
        self.name = name
        self.default = default

    def __get__(self, instance, owner):
        if instance is None:
            return self
        value = instance._data.get(self.name)
        if value is not None:
            value = self._to_python(value)
        elif self.default is not None:
            default = self.default
            if callable(default):
                default = default()
            value = default
        return value

    def __set__(self, instance, value):
        if value is not None:
            value = self._to_json(value)
        instance._data[self.name] = value

    def _to_python(self, value):
        return unicode(value)

    def _to_json(self, value):
        return self._to_python(value)


class MappingMeta(type):

    def __new__(cls, name, bases, d):
        fields = {}
        for base in bases:
            if hasattr(base, '_fields'):
                fields.update(base._fields)
        for attrname, attrval in d.items():
            if isinstance(attrval, Field):
                if not attrval.name:
                    attrval.name = attrname
                fields[attrname] = attrval
        d['_fields'] = fields
        return type.__new__(cls, name, bases, d)


class Mapping(object):
    __metaclass__ = MappingMeta

    def __init__(self, **values):
        self._data = {}
        for attrname, field in self._fields.items():
            if attrname in values:
                setattr(self, attrname, values.pop(attrname))
            else:
                setattr(self, attrname, getattr(self, attrname))

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data or ())

    def __delitem__(self, name):
        del self._data[name]

    def __getitem__(self, name):
        return self._data[name]

    def __setitem__(self, name, value):
        self._data[name] = value

    def get(self, name, default):
        return self._data.get(name, default)

    def setdefault(self, name, default):
        return self._data.setdefault(name, default)

    def unwrap(self):
        return self._data

    @classmethod
    def build(cls, **d):
        fields = {}
        for attrname, attrval in d.items():
            if not attrval.name:
                attrval.name = attrname
            fields[attrname] = attrval
        d['_fields'] = fields
        return type('AnonymousStruct', (cls,), d)

    @classmethod
    def wrap(cls, data):
        instance = cls()
        instance._data = data
        return instance

    def _to_python(self, value):
        return self.wrap(value)

    def _to_json(self, value):
        return self.unwrap()


class DocumentMeta(MappingMeta):
    pass


class Document(Mapping):
    __metaclass__ = DocumentMeta

    def __init__(self, id=None, **values):
        Mapping.__init__(self, **values)
        if id is not None:
            self.id = id

    def __repr__(self):
        return '<%s %r@%r %r>' % (type(self).__name__, self.id, self.rev,
                                  dict([(k, v) for k, v in self._data.items()
                                        if k not in ('_id', '_rev')]))

    def _get_id(self):
        if hasattr(self._data, 'id'): # When data is client.Document
            return self._data.id
        return self._data.get('_id')
    def _set_id(self, value):
        if self.id is not None:
            raise AttributeError('id can only be set on new documents')
        self._data['_id'] = value
    id = property(_get_id, _set_id, doc='The document ID')

    @property
    def rev(self):
        """The document revision.
        
        :rtype: basestring
        """
        if hasattr(self._data, 'rev'): # When data is client.Document
            return self._data.rev
        return self._data.get('_rev')

    def items(self):
        """Return the fields as a list of ``(name, value)`` tuples.
        
        This method is provided to enable easy conversion to native dictionary
        objects, for example to allow use of `mapping.Document` instances with
        `client.Database.update`.
        
        >>> class Post(Document):
        ...     title = TextField()
        ...     author = TextField()
        >>> post = Post(id='foo-bar', title='Foo bar', author='Joe')
        >>> sorted(post.items())
        [('_id', 'foo-bar'), ('author', u'Joe'), ('title', u'Foo bar')]
        
        :return: a list of ``(name, value)`` tuples
        """
        retval = []
        if self.id is not None:
            retval.append(('_id', self.id))
            if self.rev is not None:
                retval.append(('_rev', self.rev))
        for name, value in self._data.items():
            if name not in ('_id', '_rev'):
                retval.append((name, value))
        return retval

    @classmethod
    def load(cls, db, id):
        """Load a specific document from the given database.
        
        :param db: the `Database` object to retrieve the document from
        :param id: the document ID
        :return: the `Document` instance, or `None` if no document with the
                 given ID was found
        """
        doc = db.get(id)
        if doc is None:
            return None
        return cls.wrap(doc)

    def store(self, db):
        """Store the document in the given database."""
        db.save(self._data)
        return self

    @classmethod
    def query(cls, db, map_fun, reduce_fun, language='javascript', **options):
        """Execute a CouchDB temporary view and map the result values back to
        objects of this mapping.
        
        Note that by default, any properties of the document that are not
        included in the values of the view will be treated as if they were
        missing from the document. If you want to load the full document for
        every row, set the ``include_docs`` option to ``True``.
        """
        def _wrapper(row):
            if row.doc is not None:
                return cls.wrap(row.doc)
            data = row.value
            data['_id'] = row.id
            return cls.wrap(data)
        return db.query(map_fun, reduce_fun=reduce_fun, language=language,
                        wrapper=_wrapper, **options)

    @classmethod
    def view(cls, db, viewname, **options):
        """Execute a CouchDB named view and map the result values back to
        objects of this mapping.
        
        Note that by default, any properties of the document that are not
        included in the values of the view will be treated as if they were
        missing from the document. If you want to load the full document for
        every row, set the ``include_docs`` option to ``True``.
        """
        def _wrapper(row):
            if row.doc is not None: # include_docs=True
                return cls.wrap(row.doc)
            data = row.value
            data['_id'] = row.id
            return cls.wrap(data)
        return db.view(viewname, wrapper=_wrapper, **options)

    def fromDict(self, d):
        """
        Set the object from the given result dictionary obtained from CouchDB.
        """
        # FIXME: this is poking at internals of python-couchdb
        # FIXME: do we need copy ?
        self._data = d.copy()
        return

class TextField(Field):
    """Mapping field for string values."""
    _to_python = unicode


class FloatField(Field):
    """Mapping field for float values."""
    _to_python = float


class IntegerField(Field):
    """Mapping field for integer values."""
    _to_python = int


class LongField(Field):
    """Mapping field for long integer values."""
    _to_python = long


class BooleanField(Field):
    """Mapping field for boolean values."""
    _to_python = bool


class DecimalField(Field):
    """Mapping field for decimal values."""

    def _to_python(self, value):
        return Decimal(value)

    def _to_json(self, value):
        return unicode(value)


class DateField(Field):
    """Mapping field for storing dates.
    
    >>> field = DateField()
    >>> field._to_python('2007-04-01')
    datetime.date(2007, 4, 1)
    >>> field._to_json(date(2007, 4, 1))
    '2007-04-01'
    >>> field._to_json(datetime(2007, 4, 1, 15, 30))
    '2007-04-01'
    """

    def _to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = date(*strptime(value, '%Y-%m-%d')[:3])
            except ValueError:
                raise ValueError('Invalid ISO date %r' % value)
        return value

    def _to_json(self, value):
        if isinstance(value, datetime):
            value = value.date()
        return value.isoformat()


class DateTimeField(Field):
    """Mapping field for storing date/time values.
    
    >>> field = DateTimeField()
    >>> field._to_python('2007-04-01T15:30:00Z')
    datetime.datetime(2007, 4, 1, 15, 30)
    >>> field._to_json(datetime(2007, 4, 1, 15, 30, 0, 9876))
    '2007-04-01T15:30:00Z'
    >>> field._to_json(date(2007, 4, 1))
    '2007-04-01T00:00:00Z'
    """

    def _to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = value.split('.', 1)[0] # strip out microseconds
                value = value.rstrip('Z') # remove timezone separator
                timestamp = timegm(strptime(value, '%Y-%m-%dT%H:%M:%S'))
                value = datetime.utcfromtimestamp(timestamp)
            except ValueError:
                raise ValueError('Invalid ISO date/time %r' % value)
        return value

    def _to_json(self, value):
        if isinstance(value, struct_time):
            value = datetime.utcfromtimestamp(timegm(value))
        elif not isinstance(value, datetime):
            value = datetime.combine(value, time(0))
        return value.replace(microsecond=0).isoformat() + 'Z'


class TimeField(Field):
    """Mapping field for storing times.
    
    >>> field = TimeField()
    >>> field._to_python('15:30:00')
    datetime.time(15, 30)
    >>> field._to_json(time(15, 30))
    '15:30:00'
    >>> field._to_json(datetime(2007, 4, 1, 15, 30))
    '15:30:00'
    """

    def _to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = value.split('.', 1)[0] # strip out microseconds
                value = time(*strptime(value, '%H:%M:%S')[3:6])
            except ValueError:
                raise ValueError('Invalid ISO time %r' % value)
        return value

    def _to_json(self, value):
        if isinstance(value, datetime):
            value = value.time()
        return value.replace(microsecond=0).isoformat()


class DictField(Field):
    """Field type for nested dictionaries.
    
    >>> from couchdb import Server
    >>> server = Server('http://localhost:5984/')
    >>> db = server.create('python-tests')

    >>> class Post(Document):
    ...     title = TextField()
    ...     content = TextField()
    ...     author = DictField(Mapping.build(
    ...         name = TextField(),
    ...         email = TextField()
    ...     ))
    ...     extra = DictField()

    >>> post = Post(
    ...     title='Foo bar',
    ...     author=dict(name='John Doe',
    ...                 email='john@doe.com'),
    ...     extra=dict(foo='bar'),
    ... )
    >>> post.store(db) #doctest: +ELLIPSIS
    <Post ...>
    >>> post = Post.load(db, post.id)
    >>> post.author.name
    u'John Doe'
    >>> post.author.email
    u'john@doe.com'
    >>> post.extra
    {'foo': 'bar'}

    >>> del server['python-tests']
    """
    def __init__(self, mapping=None, name=None, default=None):
        default = default or {}
        Field.__init__(self, name=name, default=lambda: default.copy())
        self.mapping = mapping

    def _to_python(self, value):
        if self.mapping is None:
            return value
        else:
            return self.mapping.wrap(value)

    def _to_json(self, value):
        if self.mapping is None:
            return value
        if not isinstance(value, Mapping):
            value = self.mapping(**value)
        return value.unwrap()


class ListField(Field):
    """Field type for sequences of other fields.

    >>> from couchdb import Server
    >>> server = Server('http://localhost:5984/')
    >>> db = server.create('python-tests')

    >>> class Post(Document):
    ...     title = TextField()
    ...     content = TextField()
    ...     pubdate = DateTimeField(default=datetime.now)
    ...     comments = ListField(DictField(Mapping.build(
    ...         author = TextField(),
    ...         content = TextField(),
    ...         time = DateTimeField()
    ...     )))

    >>> post = Post(title='Foo bar')
    >>> post.comments.append(author='myself', content='Bla bla',
    ...                      time=datetime.now())
    >>> len(post.comments)
    1
    >>> post.store(db) #doctest: +ELLIPSIS
    <Post ...>
    >>> post = Post.load(db, post.id)
    >>> comment = post.comments[0]
    >>> comment['author']
    'myself'
    >>> comment['content']
    'Bla bla'
    >>> comment['time'] #doctest: +ELLIPSIS
    '...T...Z'

    >>> del server['python-tests']
    """

    def __init__(self, field, name=None, default=None):
        default = default or []
        Field.__init__(self, name=name, default=lambda: copy.copy(default))
        if type(field) is type:
            if issubclass(field, Field):
                field = field()
            elif issubclass(field, Mapping):
                field = DictField(field)
        self.field = field

    def _to_python(self, value):
        return self.Proxy(value, self.field)

    def _to_json(self, value):
        return [self.field._to_json(item) for item in value]


    class Proxy(list):

        def __init__(self, list, field):
            self.list = list
            self.field = field

        def __lt__(self, other):
            return self.list < other

        def __le__(self, other):
            return self.list <= other

        def __eq__(self, other):
            return self.list == other

        def __ne__(self, other):
            return self.list != other

        def __gt__(self, other):
            return self.list > other

        def __ge__(self, other):
            return self.list >= other

        def __repr__(self):
            return repr(self.list)

        def __str__(self):
            return str(self.list)

        def __unicode__(self):
            return unicode(self.list)

        def __delitem__(self, index):
            del self.list[index]

        def __getitem__(self, index):
            return self.field._to_python(self.list[index])

        def __setitem__(self, index, value):
            self.list[index] = self.field._to_json(value)

        def __delslice__(self, i, j):
            del self.list[i:j]

        def __getslice__(self, i, j):
            return ListField.Proxy(self.list[i:j], self.field)

        def __setslice__(self, i, j, seq):
            self.list[i:j] = (self.field._to_json(v) for v in seq)

        def __contains__(self, value):
            for item in self.list:
                if self.field._to_python(item) == value:
                    return True
            return False

        def __iter__(self):
            for index in range(len(self)):
                yield self[index]

        def __len__(self):
            return len(self.list)

        def __nonzero__(self):
            return bool(self.list)

        def append(self, *args, **kwargs):
            if args or not isinstance(self.field, DictField):
                if len(args) != 1:
                    raise TypeError('append() takes exactly one argument '
                                    '(%s given)' % len(args))
                value = args[0]
            else:
                value = kwargs
            self.list.append(self.field._to_json(value))

        def count(self, value):
            return [i for i in self].count(value)

        def extend(self, list):
            for item in list:
                self.append(item)

        def index(self, value):
            return self.list.index(self.field._to_json(value))

        def insert(self, idx, *args, **kwargs):
            if args or not isinstance(self.field, DictField):
                if len(args) != 1:
                    raise TypeError('insert() takes exactly 2 arguments '
                                    '(%s given)' % len(args))
                value = args[0]
            else:
                value = kwargs
            self.list.insert(idx, self.field._to_json(value))

        def remove(self, value):
            return self.list.remove(self.field._to_json(value))

        def pop(self, *args):
            return self.field._to_python(self.list.pop(*args))

class TupleField(Field):
    """Field type for tuple of other fields, with possibly different types.

    >>> from couchdb import Server
    >>> server = Server('http://localhost:5984/')
    >>> db = server.create('python-tests')

    >>> class Post(Document):
    ...     title = TextField()
    ...     content = TextField()
    ...     pubdate = DateTimeField(default=datetime.now)
    ...     comments = ListField(TupleField((
    ...         TextField(),
    ...         TextField(),
    ...         DateTimeField()
    ...     )))

    >>> post = Post(title='Foo bar')
    >>> post.comments.append(('myself', 'Bla bla',
    ...                      datetime.now()))
    >>> len(post.comments)
    1
    >>> post.store(db) #doctest: +ELLIPSIS
    <Post ...>
    >>> post = Post.load(db, post.id)
    >>> comment = post.comments[0]
    >>> comment[0]
    u'myself'
    >>> comment[1]
    u'Bla bla'
    >>> comment[2] #doctest: +ELLIPSIS
    datetime.datetime(...)

    >>> del server['python-tests']
    """

    def __init__(self, fields, name=None, default=None):
        Field.__init__(self, name=name,
            default=default or (None, ) * len(fields))

        res = []
        for field in fields:
            if type(field) is type:
                if issubclass(field, Field):
                    field = field()
                elif issubclass(field, Mapping):
                    field = DictField(field)
            res.append(field)
        self.fields = tuple(res)

    def _to_python(self, value):
        return tuple([self.fields[i]._to_python(m)
            for i, m in enumerate(value)])

    def _to_json(self, value):
        # value is a tuple with python values to be converted
        assert len(self.fields) == len(value)
        return [self.fields[i]._to_json(m) for i, m in enumerate(value)]



########NEW FILE########
__FILENAME__ = pjson
# -*- Mode: Python; test-case-name: paisley.test.test_pjson -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2011
# See LICENSE for details.

"""
Paisley JSON compatibility code.

json is the stdlib JSON library.
It has an unfortunate bug in 2.7: http://bugs.python.org/issue10038
where the C-based implementation returns str instead of unicode for text.

This caused
  import json; json.loads('"abc"')
to return
  "abc"
instead of
  u"abc"
when using the C implementation, but not the python implementation.

If json is not installed, this falls back to simplejson, which is
also not strict and will return str instead of unicode.

In that case, STRICT will be set to True.
"""

STRICT = True


def set_strict(strict=True):
    """
    Set strictness of the loads function.
    Can be called after importing to change strictness level.

    Recommended to use only at startup.
    """
    global loads
    loads = _get_loads(strict)
    global STRICT
    STRICT = strict


def _get_loads(strict=STRICT):
    if not strict:
        try:
            from simplejson import loads
        except ImportError:
            from json import loads
        return loads

    # If we don't have json, we can only fall back to simplejson, non-strict
    try:
        from json import decoder
    except ImportError:
        global STRICT
        STRICT = False
        from simplejson import loads
        return loads
    try:
        res = decoder.c_scanstring('"str"', 1)
    except TypeError:
        # github issue #33: pypy may not have c_scanstring
        res = decoder.scanstring('"str"', 1)

    if type(res[0]) is unicode:
        from json import loads
        return loads

    import json as _myjson
    from json import scanner

    class MyJSONDecoder(_myjson.JSONDecoder):

        def __init__(self, *args, **kwargs):
            _myjson.JSONDecoder.__init__(self, *args, **kwargs)

            # reset scanner to python-based one using python scanstring
            self.parse_string = decoder.py_scanstring
            self.scan_once = scanner.py_make_scanner(self)

    def loads(s, *args, **kwargs):
        if 'cls' not in kwargs:
            kwargs['cls'] = MyJSONDecoder
        return _myjson.loads(s, *args, **kwargs)

    return loads


def _get_dumps(strict=STRICT):
    if not strict:
        try:
            from simplejson import dumps
        except ImportError:
            from json import dumps
        return dumps


    try:
        from json import dumps
        return dumps
    except ImportError:
        global STRICT
        STRICT = False
        from simplejson import dumps
        return dumps

dumps = _get_dumps()
loads = _get_loads()

########NEW FILE########
__FILENAME__ = test_changes
# -*- Mode: Python; test-case-name: paisley.test.test_changes -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2011
# See LICENSE for details.

import os

from twisted.internet import defer, reactor, error
from twisted.trial import unittest

from paisley import client, changes

from paisley.test import util


class FakeNotifier(object):

    def __init__(self):
        self.changes = []

    def changed(self, change):
        self.changes.append(change)


class TestStubChangeReceiver(unittest.TestCase):

    def testChanges(self):
        notifier = FakeNotifier()
        receiver = changes.ChangeReceiver(notifier)

        # ChangeNotifier test lines
        path = os.path.join(os.path.dirname(__file__),
            'test.changes')
        handle = open(path)
        text = handle.read()

        for line in text.split("\n"):
            receiver.lineReceived(line)

        self.assertEquals(len(notifier.changes), 3)
        self.assertEquals(notifier.changes[0]["seq"], 3934)
        self.assertEquals(notifier.changes[2]["deleted"], True)


class BaseTestCase(util.CouchDBTestCase):
    tearing = False # set to True during teardown so we can assert
    expect_tearing = False

    def setUp(self):
        util.CouchDBTestCase.setUp(self)

    def tearDown(self):
        self.tearing = True
        util.CouchDBTestCase.tearDown(self)

    def waitForNextCycle(self):
        # Wait for the reactor to cycle.
        # Useful after telling the notifier to stop, since the actual
        # shutdown is triggered on one of the next cycles
        # 0 is not enough though
        d = defer.Deferred()
        reactor.callLater(0.01, d.callback, None)
        return d


class ChangeReceiverTestCase(BaseTestCase, changes.ChangeListener):

    lastChange = None
    _deferred = None

    ### ChangeListener interface

    def changed(self, change):
        self.lastChange = change
        if self._deferred is not None:
            # reset self._deferred before callback because this can be
            # called recursively
            d = self._deferred
            self._deferred = None
            d.callback(change)

    def connectionLost(self, reason):
        # make sure we lost the connection cleanly
        self.failIf(self.tearing,
            'connectionLost should be called before teardown '
            'through notifier.stop')
        self.failUnless(reason.check(error.ConnectionDone))

    ### method for subclasses

    def waitForChange(self):
        self._deferred = defer.Deferred()
        return self._deferred


class ListenerChangeReceiverTestCase(ChangeReceiverTestCase):

    def setUp(self):
        ChangeReceiverTestCase.setUp(self)

        return self.db.createDB('test')

    def testChanges(self):
        notifier = changes.ChangeNotifier(self.db, 'test')
        notifier.addListener(self)


        d = notifier.start()

        def create(_):
            changeD = self.waitForChange()

            saveD = self.db.saveDoc('test', {'key': 'value'})
            saveD.addCallback(lambda r: setattr(self, 'firstid', r['id']))

            dl = defer.DeferredList([saveD, changeD])

            def check(_):
                c = self.lastChange
                self.assertEquals(c['id'], self.firstid)
                self.assertEquals(len(c['changes']), 1)
                self.assertEquals(c['changes'][0]['rev'][:2], '1-')
            dl.addCallback(check)

            dl.addCallback(lambda _: self.db.openDoc('test', self.firstid))
            dl.addCallback(lambda r: setattr(self, 'first', r))

            return dl
        d.addCallback(create)

        def update(_):
            changeD = self.waitForChange()

            self.first['key'] = 'othervalue'
            saveD = self.db.saveDoc('test', self.first, docId=self.firstid)

            dl = defer.DeferredList([saveD, changeD])

            def check(_):
                c = self.lastChange
                self.assertEquals(c['id'], self.firstid)
                self.assertEquals(len(c['changes']), 1)
                self.assertEquals(c['changes'][0]['rev'][:2], '2-')
            dl.addCallback(check)

            return dl
        d.addCallback(update)

        d.addCallback(lambda _: notifier.stop())
        d.addCallback(lambda _: self.waitForNextCycle())
        return d

    def testChangesFiltered(self):
        """
        This tests that we can use a filter to only receive notifications
        for documents that interest us.
        """
        notifier = changes.ChangeNotifier(self.db, 'test')
        notifier.addListener(self)

        d = defer.Deferred()

        filterjs = """
function(doc, req) {
    log(req.query);
    var docids = eval('(' + req.query.docids + ')');
    log(docids);
    if (docids.indexOf(doc._id) > -1) {
        return true;
    } else {
        return false;
    }
}
"""

        d.addCallback(lambda _: self.db.saveDoc('test',
            {
                'filters': {
                    "test": filterjs,
                },
            },
            '_design/design_doc'))


        d.addCallback(lambda _: notifier.start(
            filter='design_doc/test',
            docids=client.json.dumps(['one', ])))

        def create(_):
            changeD = self.waitForChange()

            saveD = self.db.saveDoc('test', {'key': 'value'}, docId='one')
            saveD.addCallback(lambda r: setattr(self, 'firstid', r['id']))

            dl = defer.DeferredList([saveD, changeD])

            def check(_):
                c = self.lastChange
                self.assertEquals(c['id'], self.firstid)
                self.assertEquals(len(c['changes']), 1)
                self.assertEquals(c['changes'][0]['rev'][:2], '1-')
                self.assertEquals(c['seq'], 2)
            dl.addCallback(check)

            dl.addCallback(lambda _: self.db.openDoc('test', self.firstid))
            dl.addCallback(lambda r: setattr(self, 'first', r))

            return dl
        d.addCallback(create)

        def update(_):
            changeD = self.waitForChange()

            self.first['key'] = 'othervalue'
            saveD = self.db.saveDoc('test', self.first, docId=self.firstid)
            saveD.addCallback(lambda r: setattr(self, 'firstrev', r['rev']))

            dl = defer.DeferredList([saveD, changeD])

            def check(_):
                c = self.lastChange
                self.assertEquals(c['id'], self.firstid)
                self.assertEquals(len(c['changes']), 1)
                self.assertEquals(c['changes'][0]['rev'][:2], '2-')
                self.assertEquals(c['seq'], 3)
            dl.addCallback(check)

            return dl
        d.addCallback(update)

        def createTwoAndUpdateOne(_):
            # since createTwo is not supposed to trigger a change, we can't
            # assert that it didn't until we make another change that is
            # detected.
            changeD = self.waitForChange()

            saveD = self.db.saveDoc('test', {'key': 'othervalue'}, docId='two')

            def update(_):
                self.first['key'] = 'thirdvalue'
                self.first['_rev'] = self.firstrev
                return self.db.saveDoc('test', self.first, docId=self.firstid)
            saveD.addCallback(update)

            dl = defer.DeferredList([saveD, changeD])
            # FIXME: this failure actually gets swallowed, even though
            # DeferredList should not do that; so force DeferredList to fail
            # to reproduce, remove the line that updates firstrev, and
            # don't add the eb below

            def eb(failure):
                dl.errback(failure)
                # self.fail('Could not update: %r' % failure)
                return failure
            saveD.addErrback(eb)

            def check(_):
                c = self.lastChange
                self.assertEquals(c['id'], self.firstid)
                self.assertEquals(len(c['changes']), 1)
                self.assertEquals(c['changes'][0]['rev'][:2], '3-')
                # Note that we didn't receive change with seq 4,
                # which was the creation of doc two
                self.assertEquals(c['seq'], 5)
            dl.addCallback(check)

            return dl
        d.addCallback(createTwoAndUpdateOne)
        d.addCallback(lambda _: notifier.stop())
        d.addCallback(lambda _: self.waitForNextCycle())

        d.callback(None)
        return d


class RestartingNotifierTest(ChangeReceiverTestCase):

    def setUp(self):
        ChangeReceiverTestCase.setUp(self)
        # get database with some history
        d = self.db.createDB('test')
        d.addCallback(self._createDoc, 'mydoc')
        return d

    def testStartingWithSinceParam(self):
        '''
        Here we start notifier from the begining of the history and assert
        we get the historical change.
        Than we update the database once the notifier is stopped, restart
        notifier and assert we got the change.
        '''

        notifier = self._createNotifier(since=0)
        self.assertFalse(notifier.isRunning())

        d = defer.succeed(None)
        d.addCallback(self._start, notifier)
        d.addCallback(self._assertNotification, 'mydoc')
        d.addCallback(self._stop, notifier)
        # now create other document while notifier is not working
        d.addCallback(self._createDoc, 'other_doc')
        d.addCallback(self._start, notifier)
        # assert than we receive notification after reconnecting
        d.addCallback(self._assertNotification, 'other_doc')
        d.addCallback(self._stop, notifier)
        return d

    def _start(self, _, notifier):
        d = self.waitForChange()
        d2 = notifier.start()
        d2.addCallback(lambda _: d)
        d2.addCallback(lambda _: self.assertTrue(notifier.isRunning()))
        return d2

    def _stop(self, _, notifier):
        notifier.stop()
        d = self.waitForNextCycle()
        d.addCallback(lambda _: self.assertFalse(notifier.isRunning()))
        return d

    def _assertNotification(self, _, expected_id):
        self.assertEqual(expected_id, self.lastChange['id'])

    def _createNotifier(self, **options):
        notifier = changes.ChangeNotifier(self.db, 'test', **options)
        notifier.addListener(self)
        return notifier

    def _createDoc(self, _, doc_id):
        return self.db.saveDoc('test', {'key': 'value'}, doc_id)


class ConnectionLostTestCase(BaseTestCase, changes.ChangeListener):

    def setUp(self):
        BaseTestCase.setUp(self)

        notifier = changes.ChangeNotifier(self.db, 'test')
        notifier.addListener(self)

        d = self.db.createDB('test')
        d.addCallback(lambda _: notifier.start())
        return d

    ### ChangeListener interface

    def changed(self, change):
        pass

    def connectionLost(self, reason):
        # make sure we lost the connection before teardown
        self.failIf(self.tearing and self.expect_tearing,
            'connectionLost should be called before teardown')

        self.failIf(reason.check(error.ConnectionDone))

        from twisted.web import _newclient
        self.failUnless(reason.check(_newclient.ResponseFailed))

    def testKill(self):
        self.expect_tearing = True
        self.wrapper.process.terminate()
        return self.waitForNextCycle()

########NEW FILE########
__FILENAME__ = test_client
# -*- Mode: Python; test-case-name: paisley.test.test_client -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2007-2008
# See LICENSE for details.

"""
Test for couchdb client.
"""

from paisley import pjson as json

import cgi

from twisted.internet import defer

from twisted.trial.unittest import TestCase
from twisted.internet.defer import Deferred
from twisted.internet import reactor
from twisted.web import resource, server
from twisted.web._newclient import ResponseDone
from twisted.python.failure import Failure

from paisley import client

from paisley.test import util


class TestableCouchDB(client.CouchDB):
    """
    A couchdb client that can be tested: override the getPage method.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the client: forward parameters, and create attributes used
        in tests.
        """
        client.CouchDB.__init__(self, *args, **kwargs)
        self.deferred = Deferred()
        self.uri = None
        self.kwargs = None
        self.called = False

    def _getPage(self, uri, *args, **kwargs):
        """
        Fake getPage that do nothing but saving the arguments.
        """
        if self.called:
            raise RuntimeError("One shot client")
        self.called = True
        self.uri = uri
        self.kwargs = kwargs
        return self.deferred


class CouchDBTestCase(TestCase):
    """
    Test methods against a couchDB.
    """

    def setUp(self):
        """
        Create a fake client to be used in the tests.
        """
        self.client = TestableCouchDB("localhost")

    def test_disable_log(self):
        client = TestableCouchDB('localhost', disable_log=True)
        import logging
        log = logging.getLogger('paisley')
        self.assertNotEqual(log, client.log)

    def test_enable_log_and_defaults(self):
        client = TestableCouchDB('localhost')
        import logging
        log = logging.getLogger('paisley')
        self.assertEqual(log, client.log)

    def test_auth_init(self):
        """
        Test setting up client with authentication
        """
        self.client_auth = client.CouchDB("localhost",
                                           username="test",
                                           password="testpass")

        self.assertEquals(self.client_auth.username, "test")
        self.assertEquals(self.client_auth.password, "testpass")

    def test_get(self):
        """
        Test get method.
        """
        self.client.get("foo")
        self.assertEquals(self.client.uri, "foo")
        self.assertEquals(self.client.kwargs["method"], "GET")

    def test_post(self):
        """
        Test post method.
        """
        self.client.post("bar", "egg")
        self.assertEquals(self.client.uri, "bar")
        self.assertEquals(self.client.kwargs["method"], "POST")
        self.assertEquals(self.client.kwargs["postdata"], "egg")

    def test_put(self):
        """
        Test put method.
        """
        self.client.put("bar", "egg")
        self.assertEquals(self.client.uri, "bar")
        self.assertEquals(self.client.kwargs["method"], "PUT")
        self.assertEquals(self.client.kwargs["postdata"], "egg")

    def test_delete(self):
        """
        Test get method.
        """
        self.client.delete("foo")
        self.assertEquals(self.client.uri, "foo")
        self.assertEquals(self.client.kwargs["method"], "DELETE")

    def _checkParseDeferred(self, d):
        """
        Utility function to test that a Deferred is called with JSON parsing.
        """
        d.callback('["foo"]')

        def cb(res):
            self.assertEquals(res, ["foo"])
        return d.addCallback(cb)

    def test_createDB(self):
        """
        Test createDB: this should C{PUT} the DB name in the uri.
        """
        d = self.client.createDB("mydb")
        self.assertEquals(self.client.uri, "/mydb/")
        self.assertEquals(self.client.kwargs["method"], "PUT")
        return self._checkParseDeferred(d)

    def test_deleteDB(self):
        """
        Test deleteDB: this should C{DELETE} the DB name.
        """
        d = self.client.deleteDB("mydb")
        self.assertEquals(self.client.uri, "/mydb/")
        self.assertEquals(self.client.kwargs["method"], "DELETE")
        return self._checkParseDeferred(d)

    def test_listDB(self):
        """
        Test listDB: this should C{GET} a specific uri.
        """
        d = self.client.listDB()
        self.assertEquals(self.client.uri, "/_all_dbs")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_infoDB(self):
        """
        Test infoDB: this should C{GET} the DB name.
        """
        d = self.client.infoDB("mydb")
        self.assertEquals(self.client.uri, "/mydb/")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_listDoc(self):
        """
        Test listDoc.
        """
        d = self.client.listDoc("mydb")
        self.assertEquals(self.client.uri, "/mydb/_all_docs")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_listDocReversed(self):
        """
        Test listDoc reversed.
        """
        d = self.client.listDoc("mydb", reverse=True)
        self.assertEquals(self.client.uri, "/mydb/_all_docs?reverse=true")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_listDocStartKey(self):
        """
        Test listDoc with a start_key.
        """
        d = self.client.listDoc("mydb", startkey=2)
        self.assertEquals(self.client.uri, "/mydb/_all_docs?startkey=2")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_listDocLimit(self):
        """
        Test listDoc with a limit.
        """
        d = self.client.listDoc("mydb", limit=3)
        self.assertEquals(self.client.uri, "/mydb/_all_docs?limit=3")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_listDocMultipleArguments(self):
        """
        Test listDoc with all options activated.
        """
        d = self.client.listDoc("mydb", limit=3, startkey=1, reverse=True)
        self.assertEquals(self.client.uri,
            "/mydb/_all_docs?startkey=1&limit=3&reverse=true")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_openDoc(self):
        """
        Test openDoc.
        """
        d = self.client.openDoc("mydb", "mydoc")
        self.assertEquals(self.client.uri, "/mydb/mydoc")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_openDocAtRevision(self):
        """
        Test openDoc with a specific revision.
        """
        d = self.client.openDoc("mydb", "mydoc", revision="ABC")
        self.assertEquals(self.client.uri, "/mydb/mydoc?rev=ABC")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_openDocWithRevisionHistory(self):
        """
        Test openDoc with revision history.
        """
        d = self.client.openDoc("mydb", "mydoc", full=True)
        self.assertEquals(self.client.uri, "/mydb/mydoc?full=true")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_openDocAttachment(self):
        """
        Test openDoc for an attachment.
        """
        d = self.client.openDoc("mydb", "mydoc", attachment="bar")
        self.assertEquals(self.client.uri, "/mydb/mydoc/bar")
        self.assertEquals(self.client.kwargs["method"], "GET")
        # Data is transfered without parsing
        d.callback("test")
        return d.addCallback(self.assertEquals, "test")

    def test_saveDocWithDocId(self):
        """
        Test saveDoc, giving an explicit document ID.
        """
        d = self.client.saveDoc("mydb", "mybody", "mydoc")
        self.assertEquals(self.client.uri, "/mydb/mydoc")
        self.assertEquals(self.client.kwargs["method"], "PUT")
        return self._checkParseDeferred(d)

    def test_saveDocWithoutDocId(self):
        """
        Test saveDoc without a document ID.
        """
        d = self.client.saveDoc("mydb", "mybody")
        self.assertEquals(self.client.uri, "/mydb/")
        self.assertEquals(self.client.kwargs["method"], "POST")
        return self._checkParseDeferred(d)

    def test_saveStructuredDoc(self):
        """
        saveDoc should automatically serialize a structured document.
        """
        d = self.client.saveDoc("mydb", {"value": "mybody", "_id": "foo"},
            "mydoc")
        self.assertEquals(self.client.uri, "/mydb/mydoc")
        self.assertEquals(self.client.kwargs["method"], "PUT")
        return self._checkParseDeferred(d)

    def test_deleteDoc(self):
        """
        Test deleteDoc.
        """
        d = self.client.deleteDoc("mydb", "mydoc", "1234567890")
        self.assertEquals(self.client.uri, "/mydb/mydoc?rev=1234567890")
        self.assertEquals(self.client.kwargs["method"], "DELETE")
        return self._checkParseDeferred(d)

    def test_addAttachments(self):
        """
        Test addAttachments.
        """
        doc = {"value": "bar"}
        self.client.addAttachments(doc,
            {"file1": "value", "file2": "second value"})
        self.assertEquals(doc["_attachments"],
            {'file2': {'data': 'c2Vjb25kIHZhbHVl', 'type': 'base64'},
             'file1': {'data': 'dmFsdWU=', 'type': 'base64'}})

    def test_openView(self):
        """
        Test openView.
        """
        d = self.client.openView("mydb", "viewdoc", "myview")
        self.assertEquals(self.client.uri,
            "/mydb/_design/viewdoc/_view/myview?")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_openViewWithQuery(self):
        """
        Test openView with query arguments.
        """
        d = self.client.openView("mydb",
                                 "viewdoc",
                                 "myview",
                                 startkey="foo",
                                 limit=10)
        self.assertEquals(self.client.kwargs["method"], "GET")
        self.failUnless(
            self.client.uri.startswith("/mydb/_design/viewdoc/_view/myview"))
        query = cgi.parse_qs(self.client.uri.split('?', 1)[-1])
        # couchdb expects valid JSON as the query values, so a string of foo
        # should be serialized as "foo" explicitly
        # e.g., ?startkey=A would return
        # {"error":"bad_request","reason":"invalid UTF-8 JSON"}
        self.assertEquals(query["startkey"], ['"foo"'])
        self.assertEquals(query["limit"], ["10"])
        return self._checkParseDeferred(d)

    def test_openViewWithKeysQuery(self):
        """
        Test openView handles couchdb's strange requirements for keys arguments
        """
        d = self.client.openView("mydb2",
                                 "viewdoc2",
                                 "myview2",
                                 keys=[1, 3, 4, "hello, world", {1: 5}],
                                 limit=5)
        self.assertEquals(self.client.kwargs["method"], "POST")
        self.failUnless(
            self.client.uri.startswith(
                '/mydb2/_design/viewdoc2/_view/myview2'))
        query = cgi.parse_qs(self.client.uri.split('?', 1)[-1])
        self.assertEquals(query, dict(limit=['5']))
        self.assertEquals(self.client.kwargs['postdata'],
                          '{"keys": [1, 3, 4, "hello, world", {"1": 5}]}')

    def test_tempView(self):
        """
        Test tempView.
        """
        d = self.client.tempView("mydb", "js code")
        self.assertEquals(self.client.uri, "/mydb/_temp_view")
        self.assertEquals(self.client.kwargs["postdata"], "js code")
        self.assertEquals(self.client.kwargs["method"], "POST")
        return self._checkParseDeferred(d)

    def test_addViews(self):
        """
        Test addViews.
        """
        doc = {"value": "bar"}
        self.client.addViews(doc, {"view1": "js code 1", "view2": "js code 2"})
        self.assertEquals(doc["views"],
            {"view1": "js code 1", "view2": "js code 2"})

    def test_bindToDB(self):
        """
        Test bindToDB, calling a bind method afterwards.
        """
        self.client.bindToDB("mydb")
        d = self.client.listDoc()
        self.assertEquals(self.client.uri, "/mydb/_all_docs")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_escapeId(self):
        d = self.client.openDoc("mydb", "my doc with spaces")
        self.assertEquals(self.client.uri, "/mydb/my%20doc%20with%20spaces")
        self.assertEquals(self.client.kwargs["method"], "GET")
        return self._checkParseDeferred(d)

    def test_parseVersion(self):
        version = self.client._parseVersion('1.1.0')
        self.assertEquals(version, (1, 1, 0))
        version = self.client._parseVersion('1.1.1a1162549')
        self.assertEquals(version, (1, 1, 1))


class FakeCouchDBResource(resource.Resource):
    """
    Fake a couchDB resource.

    @ivar result: value set in tests to be returned by the resource.
    @type result: C{str}
    """
    result = ""

    def getChild(self, path, request):
        """
        Return self as only child.
        """
        return self

    def render(self, request):
        """
        Return C{result}.
        """
        return self.result


class ConnectedCouchDBTestCase(TestCase):
    """
    Test C{CouchDB} with a real web server.
    """

    def setUp(self):
        """
        Create a web server and a client bound to it.
        """
        self.resource = FakeCouchDBResource()
        site = server.Site(self.resource)
        port = reactor.listenTCP(0, site, interface="127.0.0.1")
        self.addCleanup(port.stopListening)
        self.client = client.CouchDB("127.0.0.1", port.getHost().port)

    def test_createDB(self):
        """
        Test listDB.
        """
        data = [u"mydb"]
        self.resource.result = json.dumps(data)
        d = self.client.listDB()

        def cb(result):
            self.assertEquals(result, data)
        d.addCallback(cb)
        return d


class RealCouchDBTestCase(util.CouchDBTestCase):

    def setUp(self):
        util.CouchDBTestCase.setUp(self)
        self.bound = False
        self.db_name = 'test'
        return self._resetDatabase()

    def _resetDatabase(self):
        """
        Helper method to create an empty test database, deleting the existing
        one if required.  Used to clean up before running each test.
        """
        d = defer.Deferred()
        d.addCallback(lambda _: self._deleteTestDatabaseIfExists())
        d.addCallback(lambda _: self.db.createDB(self.db_name))
        d.addCallback(self.checkResultOk)
        d.addCallback(lambda _: self.db.infoDB(self.db_name))

        d.addCallback(self.checkInfoNewDatabase)
        # We need to know the version to perform the tests
        #   Ideally the client class would trigger this automatically
        d.addCallback(lambda _: self.db.getVersion())
        d.callback(None)
        return d

    def _deleteTestDatabaseIfExists(self):
        """
        Helper method to delete the test database, wether it exists or not.
        Used to clean up before running each test.
        """
        d = defer.Deferred()
        if self.bound:
            d.addCallback(lambda _: self.db.deleteDB())
        else:
            d.addCallback(lambda _: self.db.deleteDB(self.db_name))

        def deleteFailedCb(failure):
            pass
        d.addCallbacks(self.checkResultOk, deleteFailedCb)
        d.callback(None)
        return d

    def _saveDoc(self, body, doc_id):
        """
        Helper method to save a document, and verify that it was successfull.
        """
        d = defer.Deferred()
        if self.bound:
            d.addCallback(lambda _: self.db.saveDoc(body, doc_id))
        else:
            d.addCallback(lambda _:
                self.db.saveDoc(self.db_name, body, doc_id))

        def checkDocumentCreated(result):
            self.assertEquals(result['ok'], True)
            if doc_id != None:
                self.assertEquals(result['id'], doc_id)
            self._rev = result['rev']
        d.addCallback(checkDocumentCreated)
        d.callback(None)
        return d

    def testDB(self):
        d = defer.Deferred()
        d.addCallback(lambda _: self._deleteTestDatabaseIfExists())
        d.addCallback(lambda _: self.db.getVersion())
        d.addCallback(lambda _: self.db.createDB('test'))
        d.addCallback(self.checkResultOk)
        d.addCallback(lambda _: self.db.listDB())

        def listCb(result):
            if self.db.version.__ge__((1, 1, 0)):
                self.assertEquals(len(result), 3)
                self.failUnless('_replicator' in result)
            else:
                self.assertEquals(len(result), 2)
            self.failUnless('test' in result)
            self.failUnless('_users' in result)
        d.addCallback(listCb)
        d.addCallback(lambda _: self.db.saveDoc('test', {'number': 1}, '1'))

        def saveDoc(result):
            self.assertEquals(result[u'ok'], True)
            self.assertEquals(result[u'id'], u'1')
            # save document revision for comparison later
            self.doc_rev = result[u'rev']
        d.addCallback(saveDoc)
        doc = {}
        self.db.addViews(doc, {'test':
            {'map': 'function (doc) { emit(doc.number, doc) }'}})
        d.addCallback(lambda _: self.db.saveDoc('test', doc, '_design/test'))

        def addViewCb(result):
            self.assertEquals(result[u'ok'], True)
            self.assertEquals(result[u'id'], u'_design/test')
        d.addCallback(addViewCb)
        d.addCallback(lambda _: self.db.openView('test', 'test', 'test'))

        def openViewCb(result):
            self.assertEquals(result[u'total_rows'], 1)
            self.assertEquals(result[u'offset'], 0)
            self.assertEquals(result[u'rows'][0][u'id'], u'1')
            self.assertEquals(result[u'rows'][0][u'key'], 1)
            self.assertEquals(result[u'rows'][0][u'value'][u'_id'], u'1')
            self.assertEquals(result[u'rows'][0][u'value'][u'number'], 1)
            self.assertEquals(result[u'rows'][0][u'value'][u'_rev'],
                self.doc_rev)
        d.addCallback(openViewCb)
        d.addCallback(lambda _:
            self.db.openView('test', 'test', 'test', keys=[1]))
        d.addCallback(openViewCb)
        d.addCallback(lambda _:
            self.db.openView('test', 'test', 'test', keys = [0]))

        def openView3Cb(result):
            self.assertEquals(result[u'total_rows'], 1)
            self.assertEquals(result[u'offset'], 0)
            self.assertEquals(result[u'update_seq'], 2)
            self.assertEquals(result[u'rows'], [])
        d.addCallback(openView3Cb)
        d.addCallback(lambda _: self.db.deleteDB('test'))
        d.addCallback(self.checkResultOk)
        d.addCallback(lambda _: self.db.listDB())

        def listCbAgain(result):
            if self.db.version.__ge__((1, 1, 0)):
                self.assertEquals(len(result), 2)
            else:
                self.assertEquals(len(result), 1)
            self.failUnless('_users' in result)
        d.addCallback(listCbAgain)

        d.callback(None)
        return d

    def test_createDB(self):
        """
        Test createDB: this should C{PUT} the DB name in the uri.
        """
        d = defer.Deferred()
        # Since during setUp we already create the database, and here we are
        #   specifically testing the creation, we need to delete it first
        d.addCallback(lambda _: self._deleteTestDatabaseIfExists())
        d.addCallback(lambda _: self.db.createDB(self.db_name))
        d.addCallback(self.checkResultOk)
        d.callback(None)
        return d

    def test_deleteDB(self):
        """
        Test deleteDB: this should C{DELETE} the DB name.
        """
        d = defer.Deferred()
        d.addCallback(lambda _: self.db.deleteDB(self.db_name))
        d.addCallback(self.checkResultOk)
        d.callback(None)
        return d

    def test_listDB(self):
        """
        Test listDB: this should C{GET} a specific uri.
        """
        d = defer.Deferred()
        d.addCallback(lambda _: self.db.listDB())

        def listCb(result):
            if self.db.version.__ge__((1, 1, 0)):
                self.assertEquals(len(result), 3)
                self.failUnless('_replicator' in result)
            else:
                self.assertEquals(len(result), 2)
            self.failUnless('test' in result)
            self.failUnless('_users' in result)
        d.addCallback(listCb)
        d.callback(None)
        return d

    def test_infoDB(self):
        """
        Test infoDB: this should C{GET} the DB name.
        """
        d = defer.Deferred()
        # Get info about newly created database
        d.addCallback(lambda _: self.db.infoDB(self.db_name))
        d.addCallback(self.checkInfoNewDatabase)
        d.callback(None)
        return d

    def test_listDoc(self):
        """
        Test listDoc.
        """
        d = defer.Deferred()
        # List documents in newly created database
        d.addCallback(lambda _: self.db.listDoc(self.db_name))
        d.addCallback(self.checkDatabaseEmpty)
        d.callback(None)
        return d

    def test_listDocReversed(self):
        """
        Test listDoc reversed.
        """
        d = defer.Deferred()
        # List documents in newly created database
        d.addCallback(lambda _: self.db.listDoc(self.db_name, reverse=True))
        d.addCallback(self.checkDatabaseEmpty)
        d.callback(None)
        return d

    def test_listDocStartKey(self):
        """
        Test listDoc with a startkey.
        """
        d = defer.Deferred()
        # List documents in newly created database
        d.addCallback(lambda _: self.db.listDoc(self.db_name, startkey=u'2'))
        d.addCallback(self.checkDatabaseEmpty)
        d.callback(None)
        return d

    def test_listDocLimit(self):
        """
        Test listDoc with a limit.
        """
        d = defer.Deferred()
        # List documents in newly created database
        d.addCallback(lambda _: self.db.listDoc(self.db_name, limit=3))
        d.addCallback(self.checkDatabaseEmpty)
        d.callback(None)
        return d

    def test_listDocMultipleArguments(self):
        """
        Test listDoc with all options activated.
        """
        d = defer.Deferred()
        # List documents in newly created database
        d.addCallback(lambda _:
            self.db.listDoc(self.db_name, limit=3, startkey=u'1',
                reverse=True))
        d.addCallback(self.checkDatabaseEmpty)
        d.callback(None)
        return d

    def test_openDoc(self):
        """
        Test openDoc.
        """
        d = defer.Deferred()
        doc_id = 'foo'
        body = {"value": "mybody"}
        d.addCallback(lambda _: self._saveDoc(body, doc_id))
        d.addCallback(lambda _: self.db.openDoc(self.db_name, doc_id))

        def checkDoc(result):
            self.assertEquals(result['_id'], doc_id)
            self.assertEquals(result['value'], 'mybody')
        d.addCallback(checkDoc)
        d.callback(None)
        return d

    @defer.inlineCallbacks
    def test_openDocAttachment(self):
        """
        Test opening an attachment with openDoc.
        """
        attachment_name = 'bindata.dat'
        attachment_data = util.eight_bit_test_string()

        doc_id = 'foo'
        body = {"value": "mybody"}
        self.db.addAttachments(body, {attachment_name: attachment_data})

        yield self._saveDoc(body, doc_id)

        retrieved_data = yield self.db.openDoc(self.db_name, doc_id,
            attachment=attachment_name)
        self.assertEquals(retrieved_data, attachment_data)

    def test_saveDocWithDocId(self):
        """
        Test saveDoc, giving an explicit document ID.
        """
        d = defer.Deferred()
        # Save simple document and check the result
        doc_id = 'foo'
        body = {}
        d.addCallback(lambda _: self._saveDoc(body, doc_id))
        d.callback(None)
        return d

    def test_saveDocWithoutDocId(self):
        """
        Test saveDoc without a document ID.
        """
        d = defer.Deferred()
        doc_id = None
        body = {}
        d.addCallback(lambda _: self._saveDoc(body, doc_id))
        d.callback(None)
        return d

    def test_saveStructuredDoc(self):
        """
        saveDoc should automatically serialize a structured document.
        """
        d = defer.Deferred()
        doc_id = 'foo'
        body = {"value": "mybody", "_id": doc_id}
        d.addCallback(lambda _: self._saveDoc(body, doc_id))
        d.addCallback(lambda _: self.db.openDoc(self.db_name, doc_id))

        def checkDocumentContent(result):
            #self.assertEquals(result['_id'], "AAA")
            self.assertEquals(result['_id'], doc_id)
            self.assertEquals(result['value'], 'mybody')
        d.addCallback(checkDocumentContent)
        d.callback(None)
        return d

    def test_deleteDoc(self):
        """
        Test deleteDoc.
        """
        d = defer.Deferred()
        doc_id = 'foo'
        body = {"value": "mybody", "_id": doc_id}
        d.addCallback(lambda _: self._saveDoc(body, doc_id))
        d.addCallback(lambda _:
            self.db.deleteDoc(self.db_name, doc_id, self._rev))

        def checkDocumentDeleted(result):
            self.assertEquals(result['id'], doc_id)
            self.assertEquals(result['ok'], True)
        d.addCallback(checkDocumentDeleted)
        d.callback(None)
        return d

    def test_addAttachments(self):
        """
        Test addAttachments.
        """
        doc_id = 'foo'
        d = defer.Deferred()
        body = {"value": "mybody", "_id": doc_id}
        attachments = {"file1": "value", "file2": "second value"}
        d.addCallback(lambda _: self.db.addAttachments(body, attachments))
        d.addCallback(lambda _: self._saveDoc(body, doc_id))
        d.addCallback(lambda _: self.db.openDoc(self.db_name, doc_id))

        def checkAttachments(result):
            self.failUnless('file1' in result["_attachments"])
            self.failUnless('file2' in result["_attachments"])
            self.assertEquals(result['_id'], doc_id)
            self.assertEquals(result['value'], 'mybody')
        d.addCallback(checkAttachments)
        d.callback(None)
        return d

    #def test_openView(self):
    # This is already covered by test_addViews

    def test_openViewWithKeysQuery(self):
        """
        Test openView handles couchdb's strange requirements for keys arguments
        """
        d = defer.Deferred()
        #d = Deferred()
        doc_id = 'foo'
        body = {"value": "bar"}
        view1_id = 'view1'
        view1 = ''' function(doc) {
        emit(doc._id, doc);
        }'''
        views = {view1_id: {'map': view1}}
        d.addCallback(lambda _: self.db.addViews(body, views))
        d.addCallback(lambda _: self._saveDoc(body, '_design/' + doc_id))
        keys=[
            {
                'startkey': ["a", "b", "c"],
                'endkey': ["x", "y", "z"],
            },
            {
                'startkey': ["a", "b", "c"],
                'endkey': ["x", "y", "z"],
            },
        ]
        d.addCallback(lambda _: self.db.openView(
            self.db_name, doc_id, view1_id, keys=keys, limit=5))
        d.addCallback(self.checkResultEmptyView)
        d.callback(None)
        return d

    def test_tempView(self):
        """
        Test tempView.
        """
        d = defer.Deferred()
        view1 = ''' function(doc) { emit(doc._id, doc); } '''
        view1 = ''' function(doc) {
        emit(doc._id, doc);
        }'''
        doc = {'map': view1}
        d.addCallback(lambda _: self.db.tempView(self.db_name, doc))
        d.addCallback(self.checkResultEmptyView)
        d.callback(None)
        return d

    def test_addViews(self):
        """
        Test addViews.
        """
        d = defer.Deferred()
        doc_id = 'foo'
        #d = Deferred()
        body = {"value": "bar"}
        view1 = ''' function(doc) {
        emit(doc._id, doc);
        }'''
        view2 = ''' function(doc) {
        emit(doc._id, doc);
        }'''
        views = {"view1": {'map': view1}, "view2": {'map': view2}}
        d.addCallback(lambda _: self.db.addViews(body, views))
        d.addCallback(lambda _: self._saveDoc(body, '_design/' + doc_id))
        d.addCallback(lambda _:
            self.db.openDoc(self.db_name, '_design/' + doc_id))

        def checkViews(result):
            self.failUnless(result["views"]['view1']['map'] == view1)
            self.failUnless(result["views"]['view2']['map'] == view2)
            self.assertEquals(result['_id'], '_design/' + doc_id)
            self.assertEquals(result['value'], 'bar')
        d.addCallback(checkViews)
        d.addCallback(lambda _:
            self.db.openView(self.db_name, doc_id, 'view1'))

        def checkOpenView(result):
            self.assertEquals(result["rows"], [])
            self.assertEquals(result["total_rows"], 0)
            self.assertEquals(result["offset"], 0)
        d.addCallback(checkOpenView)
        d.addCallback(lambda _:
            self.db.openView(self.db_name, doc_id, 'view2'))
        d.addCallback(checkOpenView)
        d.callback(None)
        return d

    def test_bindToDB(self):
        """
        Test bindToDB, calling a bind method afterwards.
        """
        d = defer.Deferred()
        doc_id = 'foo'
        body = {"value": "bar"}
        self.db.bindToDB(self.db_name)
        self.bound = True
        d.addCallback(lambda _: self._saveDoc(body, '_design/' + doc_id))
        d.addCallback(lambda _: self.db.listDoc(self.db_name))

        def checkViews(result):
            self.assertEquals(result['total_rows'], 1)
            self.assertEquals(result['offset'], 0)
        d.addCallback(checkViews)
        d.callback(None)
        return d

    def test_escapeId(self):
        d = defer.Deferred()
        doc_id = 'my doc with spaces'
        body = {"value": "bar"}
        d.addCallback(lambda _: self._saveDoc(body, doc_id))
        d.addCallback(lambda _: self.db.openDoc(self.db_name, doc_id))

        def checkDoc(result):
            self.assertEquals(result['_id'], doc_id)
            self.assertEquals(result['value'], 'bar')
        d.addCallback(checkDoc)
        d.callback(None)
        return d


class UnicodeTestCase(util.CouchDBTestCase):

    def setUp(self):
        util.CouchDBTestCase.setUp(self)
        d = self.db.createDB('test')
        d.addCallback(self.checkResultOk)
        return d

    def tearDown(self):
        d = self.db.deleteDB('test')
        d.addCallback(self.checkResultOk)
        d.addCallback(lambda _: util.CouchDBTestCase.tearDown(self))
        return d

    def testUnicodeContents(self):
        name = u'\xc3\xa9preuve'

        d = defer.Deferred()

        d.addCallback(lambda _: self.db.saveDoc('test', {
            'name': name,
            name: 'name',
            }))
        d.addCallback(lambda r: self.db.openDoc('test', r['id']))

        def check(r):
            self.assertEquals(r['name'], name)
            self.assertEquals(r[name], u'name')
            self.assertEquals(type(r['name']), unicode)
            self.assertEquals(type(r[name]), unicode)
        d.addCallback(check)
        d.callback(None)
        return d

    def testUnicodeId(self):
        docId = u'\xc3\xa9preuve'

        d = defer.Deferred()

        d.addCallback(lambda _: self.db.saveDoc('test', {
            'name': 'name',
            }, docId=docId))

        def saveDocCb(r):
            self.assertEquals(r['id'], docId)
            return self.db.openDoc('test', r['id'])
        d.addCallback(saveDocCb)

        def check(r):
            self.assertEquals(r[u'name'], u'name')
            self.assertEquals(type(r['name']), unicode)
            self.assertEquals(r[u'_id'], docId)
            self.assertEquals(type(r[u'_id']), unicode)
            self.assertEquals(type(r[u'_rev']), unicode)

            # open again, with revision
            return self.db.openDoc('test', r['_id'], revision=r['_rev'])
        d.addCallback(check)

        def checkRevisioned(r):
            self.assertEquals(r[u'name'], u'name')
            self.assertEquals(type(r['name']), unicode)
            self.assertEquals(r[u'_id'], docId)
            self.assertEquals(type(r[u'_id']), unicode)
            self.assertEquals(type(r[u'_rev']), unicode)
            return r
        d.addCallback(checkRevisioned)

        d.addCallback(lambda r: self.db.deleteDoc(
            'test', r[u'_id'], r[u'_rev']))

        d.callback(None)
        return d


class ResponseReceiverTestCase(TestCase):

    def test_utf8Receiving(self):
        d = defer.Deferred()
        rvr = client.ResponseReceiver(d, decode_utf8=True)

        # "Internationalization" string from
        # http://rentzsch.tumblr.com
        # /post/9133498042/howto-use-utf-8-throughout-your-web-stack
        data = u'\u201cI\xf1t\xebrn\xe2ti\xf4n\xe0liz\xe6ti\xf8n\u201d'
        d.addCallback(lambda encoded_out: self.assertEqual(encoded_out, data))

        for c in data.encode('utf-8'):
            rvr.dataReceived(c)

        rvr.connectionLost(Failure(ResponseDone()))

    def test_8bitReceiving(self):
        d = defer.Deferred()
        rvr = client.ResponseReceiver(d, decode_utf8=False)

        data = util.eight_bit_test_string()
        d.addCallback(lambda out: self.assertEqual(out, data))

        for c in data:
            rvr.dataReceived(c)

        rvr.connectionLost(Failure(ResponseDone()))

########NEW FILE########
__FILENAME__ = test_mapping
# -*- Mode: Python; test-case-name: paisley.test.test_mapping -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2008
# See LICENSE for details.

"""
Tests for the object mapping API.
"""

from twisted.trial.unittest import TestCase
from paisley import mapping, views
from test_views import StubCouch

# an object for a view result that includes docs


class Tag(mapping.Document):
    name = mapping.TextField()
    count = mapping.IntegerField()

    def fromDict(self, dictionary):
        self._data = dictionary['doc']


class MappingTests(TestCase):

    def setUp(self):
        # this StubCouch is different than in test_views; it replies to
        # include_docs=true, hence it has an additional key/value pair
        # for doc from which the object can be mapped
        self.fc = StubCouch(views={'all_tags?include_docs=true': {
             'total_rows': 3,
             'offset': 0,
             'rows': [
                {'key':'foo', 'value':3, 'doc': {'name':'foo', 'count':3}},
                {'key':'bar', 'value':2, 'doc': {'name':'foo', 'count':3}},
                {'key':'baz', 'value':1, 'doc': {'name':'foo', 'count':3}},
            ]}})

    def test_queryView(self):
        """
        Test that a querying a view gives us an iterable of our user defined
        objects.
        """
        v = views.View(self.fc, None, None, 'all_tags?include_docs=true', Tag)

        def _checkResults(results):
            results = list(results)
            self.assertEquals(len(results), 3)

            # this used to be not executed because it worked on the empty
            # generator; so guard against that
            looped = False
            for tag in results:
                looped = True
                self.assertIn(tag.name, ['foo', 'bar', 'baz'])
            self.failUnless(looped)

        d = v.queryView()
        d.addCallback(_checkResults)
        return d

########NEW FILE########
__FILENAME__ = test_pjson
# -*- Mode: Python; test-case-name: paisley.test.test_pjson -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2011
# See LICENSE for details.

"""
Test for Paisley JSON code.
"""

from paisley import pjson as json

# uncomment to run test with non-strict JSON parsing
# json.set_strict(False)

from twisted.trial import unittest


class JSONTestCase(unittest.TestCase):

    def testStrict(self):
        self.assertEquals(json.STRICT, True)

    def testStrToUnicode(self):
        u = json.loads('"str"')
        self.assertEquals(u, u'str')
        self.assertEquals(type(u), unicode)

    def testUnicodeToUnicode(self):
        u = json.loads(u'"str"')
        self.assertEquals(u, u'str')
        self.assertEquals(type(u), unicode)

########NEW FILE########
__FILENAME__ = test_views
# -*- Mode: Python; test-case-name: paisley.test.test_views -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2008
# See LICENSE for details.

"""
Tests for the object mapping view API.
"""

from twisted.trial.unittest import TestCase
from twisted.internet.defer import succeed

from paisley.test import util

from paisley.views import View


class StubCouch(object):
    """
    A stub couchdb object that will return preset dictionaries
    """

    def __init__(self, views=None):
        self._views = views

    def openView(self, dbName, docId, viewId, **kwargs):
        return succeed(self._views[viewId])

# an object for a view result not including docs


class Tag(object):

    def fromDict(self, dictionary):
        self.name = dictionary['key']
        self.count = dictionary['value']

ROWS = [
                {'key':'foo', 'value':3},
                {'key':'bar', 'value':2},
                {'key':'baz', 'value':1},
]


class CommonTestCase:
    """
    These tests are executed both against the stub couch and the real couch.
    """

    def test_queryView(self):
        """
        Test that querying a view gives us an iterable of our user defined
        objects.
        """
        v = View(self.db, 'test', 'design_doc', 'all_tags', Tag)

        def _checkResults(results):
            results = list(results)
            self.assertEquals(len(results), 3)

            # this used to be not executed because it worked on the empty
            # generator; so guard against that
            looped = False
            for tag in results:
                looped = True
                self.assertIn({'key': tag.name, 'value': tag.count},
                              ROWS)
            self.failUnless(looped)

        d = v.queryView()
        d.addCallback(_checkResults)
        return d


class StubViewTests(CommonTestCase, TestCase):

    def setUp(self):
        self.db = StubCouch(views={'all_tags': {
            'total_rows': 3,
            'offset': 0,
            'rows': ROWS,
            }})


class RealViewTests(CommonTestCase, util.CouchDBTestCase):

    def setUp(self):
        util.CouchDBTestCase.setUp(self)

        d = self.db.createDB('test')

        for row in ROWS:
            d.addCallback(lambda _, r: self.db.saveDoc('test', r), row)


        viewmapjs = """
function(doc) {
    emit(doc.key, doc.value);
}
"""

        d.addCallback(lambda _: self.db.saveDoc('test',
            {
                'views': {
                    "all_tags": {
                        "map": viewmapjs,
                    },
                },
            },
            '_design/design_doc'))

        return d

########NEW FILE########
__FILENAME__ = util
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2007-2008
# See LICENSE for details.

import re
import os
import tempfile
import subprocess
import time

from twisted.trial import unittest

from paisley import client


class CouchDBWrapper(object):
    """
    I wrap an external CouchDB instance started and stopped for testing.

    @ivar tempdir: the temporary directory used for logging and running
    @ivar process: the CouchDB process
    @type process: L{subprocess.Popen}
    @ivar port:    the randomly assigned port on which CouchDB listens
    @type port:    str
    @ivar db:      the CouchDB client to this server
    @type db:      L{client.CouchDB}
    """

    def start(self):
        self.tempdir = tempfile.mkdtemp(suffix='.paisley.test')

        path = os.path.join(os.path.dirname(__file__),
            'test.ini.template')
        handle = open(path)

        conf = handle.read() % {
            'tempdir': self.tempdir,
        }

        confPath = os.path.join(self.tempdir, 'test.ini')
        handle = open(confPath, 'w')
        handle.write(conf)
        handle.close()

        # create the dirs from the template
        os.mkdir(os.path.join(self.tempdir, 'lib'))
        os.mkdir(os.path.join(self.tempdir, 'log'))

        args = ['couchdb', '-a', confPath]
        null = open('/dev/null', 'w')
        self.process = subprocess.Popen(
            args, env=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # find port
        logPath = os.path.join(self.tempdir, 'log', 'couch.log')
        while not os.path.exists(logPath):
            if self.process.poll() is not None:
                raise Exception("""
couchdb exited with code %d.
stdout:
%s
stderr:
%s""" % (
                    self.process.returncode, self.process.stdout.read(),
                    self.process.stderr.read()))
            time.sleep(0.01)

        while os.stat(logPath).st_size == 0:
            time.sleep(0.01)

        PORT_RE = re.compile(
            'Apache CouchDB has started on http://127.0.0.1:(?P<port>\d+)')

        handle = open(logPath)
        line = handle.read()
        m = PORT_RE.search(line)
        if not m:
            self.stop()
            raise Exception("Cannot find port in line %s" % line)

        self.port = int(m.group('port'))
        self.db = client.CouchDB(host='localhost', port=self.port,
            username='testpaisley', password='testpaisley')

    def stop(self):
        self.process.terminate()

        os.system("rm -rf %s" % self.tempdir)


class CouchDBTestCase(unittest.TestCase):
    """
    I am a TestCase base class for tests against a real CouchDB server.
    I start a server during setup and stop it during teardown.

    @ivar  db: the CouchDB client
    @type  db: L{client.CouchDB}
    """

    def setUp(self):
        self.wrapper = CouchDBWrapper()
        self.wrapper.start()
        self.db = self.wrapper.db

    def tearDown(self):
        self.wrapper.stop()

    # helper callbacks

    def checkDatabaseEmpty(self, result):
        self.assertEquals(result['rows'], [])
        self.assertEquals(result['total_rows'], 0)
        self.assertEquals(result['offset'], 0)

    def checkInfoNewDatabase(self, result):
        self.assertEquals(result['update_seq'], 0)
        self.assertEquals(result['purge_seq'], 0)
        self.assertEquals(result['doc_count'], 0)
        self.assertEquals(result['db_name'], 'test')
        self.assertEquals(result['doc_del_count'], 0)
        self.assertEquals(result['committed_update_seq'], 0)

    def checkResultOk(self, result):
        self.assertEquals(result, {'ok': True})

    def checkResultEmptyView(self, result):
        self.assertEquals(result['rows'], [])
        self.assertEquals(result['total_rows'], 0)
        self.assertEquals(result['offset'], 0)


def eight_bit_test_string():
    return ''.join(chr(cn) for cn in xrange(0x100)) * 2

########NEW FILE########
__FILENAME__ = views
# -*- Mode: Python; test-case-name: paisley.test.test_views -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2007-2008
# See LICENSE for details.

"""
Object mapping view API.
"""


class View(object):

    def __init__(self, couch, dbName, docId, viewId, objectFactory, **options):
        """
        objectFactory should implement fromDict, taking a dictionary containing
        key and value.
        """
        self._couch = couch
        self._dbName = dbName
        self._docId = docId
        self._viewId = viewId
        self._objectFactory = objectFactory
        self._options = options

    def __repr__(self):
        return "<View on db %r, doc %r, view %r>" % (
            self._dbName, self._docId, self._viewId)

    def _mapObjects(self, result, **options):
        # result is a dict:
        # rows -> dict with id, key, value, [doc?]
        # total_rows
        # offset
        for x in result['rows']:
            obj = self._objectFactory()
            if options.get('include_docs', False):
                obj.fromDict(x['doc'])
                self._couch.mapped(self._dbName, x['id'], obj)
            else:
                obj.fromDict(x)
            yield obj

    # how do we know if it is bound already ?

    def queryView(self):
        d = self._couch.openView(
            self._dbName,
            self._docId,
            self._viewId,
            **self._options)
        d.addCallback(self._mapObjects, **self._options)
        return d

########NEW FILE########
__FILENAME__ = paisley_bench
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2007-2008
# See LICENSE for details.


import time
import sys
import numpy

import paisley

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, waitForDeferred

def benchmark(times, timer=time.time, timeStore=None, progressDest=sys.stdout):
    def _decorator(f):
        def _decorated(*args, **kwargs):
            for x in xrange(times):
                startTime=timer()
                result = yield f(*args, **kwargs)
                timeStore.setdefault(f.__name__, []).append(timer()-startTime)

                if x%(times*.10) == 0.0:
                    progressDest.write('.')
                    progressDest.flush()
            progressDest.write('\n')

        _decorated.__name__ = f.__name__

        return inlineCallbacks(_decorated)

    return _decorator

RUN_TIMES = 1000
TIMES = {}

benchmarkDecorator = benchmark(RUN_TIMES, timeStore=TIMES)


@benchmarkDecorator
def bench_saveDoc(server):
    d = server.saveDoc('benchmarks', """
        {
            "Subject":"I like Planktion",
            "Author":"Rusty",
            "PostedDate":"2006-08-15T17:30:12-04:00",
            "Tags":["plankton", "baseball", "decisions"],
            "Body":"I decided today that I don't like baseball. I like plankton."
        }
""")
    return d


@inlineCallbacks
def run_tests(server):
    for bench in [bench_saveDoc]:
        print "benchmarking %s" % (bench.__name__,)
        result = yield bench(server).addCallback(_printCb)
        print "    avg: %r" % (
            sum(TIMES[bench.__name__])/len(TIMES[bench.__name__]),)
        print "    std: %r" % (
            numpy.std(TIMES[bench.__name__]),)
        print "    min: %r" % (
            min(TIMES[bench.__name__]),)
        print "    max: %r" % (
            max(TIMES[bench.__name__]),)
        print "  total: %r" % (
            sum(TIMES[bench.__name__]),)


def run():
    s = paisley.CouchDB('localhost')
    d = s.createDB('benchmarks')
    d.addBoth(_printCb)
    d.addCallback(lambda _: run_tests(s))

    return d


def _printCb(msg):
    if msg is not None:
        print msg


if __name__ == '__main__':
    def _run():
        d = run()
        d.addBoth(_printCb)
        d.addBoth(lambda _: reactor.stop())

    reactor.callWhenRunning(_run)
    reactor.run()

########NEW FILE########
__FILENAME__ = paisley_example
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2007-2008
# See LICENSE for details.


import paisley

import sys
from twisted.internet import reactor, defer
from twisted.python import log
from twisted.web import client, error, http

client.HTTPClientFactory.noisy = False



def test():
    foo = paisley.CouchDB('localhost')

    print "\nCreate database 'mydb':"
    d = foo.createDB('mydb')
    wfd = defer.waitForDeferred(d)
    yield wfd

    try:
        print wfd.getResult()
    except error.Error, e:
        # FIXME: not sure why Error.status is a str compared to http constants
        if e.status == str(http.UNAUTHORIZED):
            print "\nError: not allowed to create databases"
            reactor.stop()
            return
        else:
            raise

    print "\nList databases on server:"
    d = foo.listDB()
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    print "\nCreate a document 'mydoc' in database 'mydb':"
    doc = """
    {
        "value":
        {
            "Subject":"I like Planktion",
            "Author":"Rusty",
            "PostedDate":"2006-08-15T17:30:12-04:00",
            "Tags":["plankton", "baseball", "decisions"],
            "Body":"I decided today that I don't like baseball. I like plankton."
        }
    }
    """
    d = foo.saveDoc('mydb', doc, 'mydoc')
    wfd = defer.waitForDeferred(d)
    yield wfd
    mydoc = wfd.getResult()
    print mydoc

    print "\nCreate a document, using an assigned docId:"
    d = foo.saveDoc('mydb', doc)
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    print "\nList all documents in database 'mydb'"
    d = foo.listDoc('mydb')
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    print "\nRetrieve document 'mydoc' in database 'mydb':"
    d = foo.openDoc('mydb', 'mydoc')
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    print "\nDelete document 'mydoc' in database 'mydb':"
    d = foo.deleteDoc('mydb', 'mydoc', mydoc['rev'])
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    print "\nList all documents in database 'mydb'"
    d = foo.listDoc('mydb')
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    print "\nList info about database 'mydb':"
    d = foo.infoDB('mydb')
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    print "\nDelete database 'mydb':"
    d = foo.deleteDB('mydb')
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    print "\nList databases on server:"
    d = foo.listDB()
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    reactor.stop()
test = defer.deferredGenerator(test)


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    reactor.callWhenRunning(test)
    reactor.run()

########NEW FILE########
__FILENAME__ = pep8
#!/usr/bin/python
# pep8.py - Check Python source code formatting, according to PEP 8
# Copyright (C) 2006 Johann C. Rocholl <johann@browsershots.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Check Python source code formatting, according to PEP 8:
http://www.python.org/dev/peps/pep-0008/

For usage and a list of options, try this:
$ python pep8.py -h

This program and its regression test suite live here:
http://svn.browsershots.org/trunk/devtools/pep8/
http://trac.browsershots.org/browser/trunk/devtools/pep8/

Groups of errors and warnings:
E errors
W warnings
100 indentation
200 whitespace
300 blank lines
400 imports
500 line length
600 deprecation
700 statements

You can add checks to this program by writing plugins. Each plugin is
a simple function that is called for each line of source code, either
physical or logical.

Physical line:
- Raw line of text from the input file.

Logical line:
- Multi-line statements converted to a single line.
- Stripped left and right.
- Contents of strings replaced with 'xxx' of same length.
- Comments removed.

The check function requests physical or logical lines by the name of
the first argument:

def maximum_line_length(physical_line)
def extraneous_whitespace(logical_line)
def blank_lines(logical_line, blank_lines, indent_level, line_number)

The last example above demonstrates how check plugins can request
additional information with extra arguments. All attributes of the
Checker object are available. Some examples:

lines: a list of the raw lines from the input file
tokens: the tokens that contribute to this logical line
line_number: line number in the input file
blank_lines: blank lines before this one
indent_char: first indentation character in this file (' ' or '\t')
indent_level: indentation (with tabs expanded to multiples of 8)
previous_indent_level: indentation on previous line
previous_logical: previous logical line

The docstring of each check function shall be the relevant part of
text from PEP 8. It is printed if the user enables --show-pep8.

"""

import os
import sys
import re
import time
import inspect
import tokenize
from optparse import OptionParser
from keyword import iskeyword
from fnmatch import fnmatch

__version__ = '0.2.0'
__revision__ = '$Rev$'

default_exclude = '.svn,CVS,*.pyc,*.pyo'

indent_match = re.compile(r'([ \t]*)').match
raise_comma_match = re.compile(r'raise\s+\w+\s*(,)').match

operators = """
+  -  *  /  %  ^  &  |  =  <  >  >>  <<
+= -= *= /= %= ^= &= |= == <= >= >>= <<=
!= <> :
in is or not and
""".split()

options = None
args = None


##############################################################################
# Plugins (check functions) for physical lines
##############################################################################


def tabs_or_spaces(physical_line, indent_char):
    """
    Never mix tabs and spaces.

    The most popular way of indenting Python is with spaces only.  The
    second-most popular way is with tabs only.  Code indented with a mixture
    of tabs and spaces should be converted to using spaces exclusively.  When
    invoking the Python command line interpreter with the -t option, it issues
    warnings about code that illegally mixes tabs and spaces.  When using -tt
    these warnings become errors.  These options are highly recommended!
    """
    indent = indent_match(physical_line).group(1)
    for offset, char in enumerate(indent):
        if char != indent_char:
            return offset, "E101 indentation contains mixed spaces and tabs"


def tabs_obsolete(physical_line):
    """
    For new projects, spaces-only are strongly recommended over tabs.  Most
    editors have features that make this easy to do.
    """
    indent = indent_match(physical_line).group(1)
    if indent.count('\t'):
        return indent.index('\t'), "W191 indentation contains tabs"


def trailing_whitespace(physical_line):
    """
    JCR: Trailing whitespace is superfluous.
    """
    physical_line = physical_line.rstrip('\n') # chr(10), newline
    physical_line = physical_line.rstrip('\r') # chr(13), carriage return
    physical_line = physical_line.rstrip('\x0c') # chr(12), form feed, ^L
    stripped = physical_line.rstrip()
    if physical_line != stripped:
        return len(stripped), "W291 trailing whitespace"


def trailing_blank_lines(physical_line, lines, line_number):
    """
    JCR: Trailing blank lines are superfluous.
    """
    if physical_line.strip() == '' and line_number == len(lines):
        return 0, "W391 blank line at end of file"


def missing_newline(physical_line):
    """
    JCR: The last line should have a newline.
    """
    if physical_line.rstrip() == physical_line:
        return len(physical_line), "W292 no newline at end of file"


def maximum_line_length(physical_line):
    """
    Limit all lines to a maximum of 79 characters.

    There are still many devices around that are limited to 80 character
    lines; plus, limiting windows to 80 characters makes it possible to have
    several windows side-by-side.  The default wrapping on such devices looks
    ugly.  Therefore, please limit all lines to a maximum of 79 characters.
    For flowing long blocks of text (docstrings or comments), limiting the
    length to 72 characters is recommended.
    """
    length = len(physical_line.rstrip())
    if length > 79:
        return 79, "E501 line too long (%d characters)" % length


##############################################################################
# Plugins (check functions) for logical lines
##############################################################################


def blank_lines(logical_line, blank_lines, indent_level, line_number,
                previous_logical):
    """
    Separate top-level function and class definitions with two blank lines.

    Method definitions inside a class are separated by a single blank line.

    Extra blank lines may be used (sparingly) to separate groups of related
    functions.  Blank lines may be omitted between a bunch of related
    one-liners (e.g. a set of dummy implementations).

    Use blank lines in functions, sparingly, to indicate logical sections.
    """
    if line_number == 1:
        return # Don't expect blank lines before the first line
    if previous_logical.startswith('@'):
        return # Don't expect blank lines after function decorator
    if (logical_line.startswith('def ') or
        logical_line.startswith('class ') or
        logical_line.startswith('@')):
        if indent_level > 0 and blank_lines != 1:
            return 0, "E301 expected 1 blank line, found %d" % blank_lines
        if indent_level == 0 and blank_lines != 2:
            return 0, "E302 expected 2 blank lines, found %d" % blank_lines
    if blank_lines > 2:
        return 0, "E303 too many blank lines (%d)" % blank_lines


def extraneous_whitespace(logical_line):
    """
    Avoid extraneous whitespace in the following situations:

    - Immediately inside parentheses, brackets or braces.

    - Immediately before a comma, semicolon, or colon.
    """
    line = logical_line
    for char in '([{':
        found = line.find(char + ' ')
        if found > -1:
            return found + 1, "E201 whitespace after '%s'" % char
    for char in '}])':
        found = line.find(' ' + char)
        if found > -1 and line[found - 1] != ',':
            return found, "E202 whitespace before '%s'" % char
    for char in ',;:':
        found = line.find(' ' + char)
        if found > -1:
            return found, "E203 whitespace before '%s'" % char


def missing_whitespace(logical_line):
    """
    JCR: Each comma, semicolon or colon should be followed by whitespace.
    """
    line = logical_line
    for index in range(len(line) - 1):
        char = line[index]
        if char in ',;:' and line[index + 1] != ' ':
            before = line[:index]
            if char == ':' and before.count('[') > before.count(']'):
                continue # Slice syntax, no space required
            return index, "E231 missing whitespace after '%s'" % char


def indentation(logical_line, previous_logical, indent_char,
                indent_level, previous_indent_level):
    """
    Use 4 spaces per indentation level.

    For really old code that you don't want to mess up, you can continue to
    use 8-space tabs.
    """
    if indent_char == ' ' and indent_level % 4:
        return 0, "E111 indentation is not a multiple of four"
    indent_expect = previous_logical.endswith(':')
    if indent_expect and indent_level <= previous_indent_level:
        return 0, "E112 expected an indented block"
    if indent_level > previous_indent_level and not indent_expect:
        return 0, "E113 unexpected indentation"


def whitespace_before_parameters(logical_line, tokens):
    """
    Avoid extraneous whitespace in the following situations:

    - Immediately before the open parenthesis that starts the argument
      list of a function call.

    - Immediately before the open parenthesis that starts an indexing or
      slicing.
    """
    prev_type = tokens[0][0]
    prev_text = tokens[0][1]
    prev_end = tokens[0][3]
    for index in range(1, len(tokens)):
        token_type, text, start, end, line = tokens[index]
        if (token_type == tokenize.OP and
            text in '([' and
            start != prev_end and
            prev_type == tokenize.NAME and
            (index < 2 or tokens[index - 2][1] != 'class') and
            (not iskeyword(prev_text))):
            return prev_end, "E211 whitespace before '%s'" % text
        prev_type = token_type
        prev_text = text
        prev_end = end


def whitespace_around_operator(logical_line):
    """
    Avoid extraneous whitespace in the following situations:

    - More than one space around an assignment (or other) operator to
      align it with another.
    """
    line = logical_line
    for operator in operators:
        found = line.find('  ' + operator)
        if found > -1:
            return found, "E221 multiple spaces before operator"
        found = line.find(operator + '  ')
        if found > -1:
            return found, "E222 multiple spaces after operator"
        found = line.find('\t' + operator)
        if found > -1:
            return found, "E223 tab before operator"
        found = line.find(operator + '\t')
        if found > -1:
            return found, "E224 tab after operator"


def whitespace_around_comma(logical_line):
    """
    Avoid extraneous whitespace in the following situations:

    - More than one space around an assignment (or other) operator to
      align it with another.

    JCR: This should also be applied around comma etc.
    """
    line = logical_line
    for separator in ',;:':
        found = line.find(separator + '  ')
        if found > -1:
            return found + 1, "E241 multiple spaces after '%s'" % separator
        found = line.find(separator + '\t')
        if found > -1:
            return found + 1, "E242 tab after '%s'" % separator


def imports_on_separate_lines(logical_line):
    """
    Imports should usually be on separate lines.
    """
    line = logical_line
    if line.startswith('import '):
        found = line.find(',')
        if found > -1:
            return found, "E401 multiple imports on one line"


def compound_statements(logical_line):
    """
    Compound statements (multiple statements on the same line) are
    generally discouraged.
    """
    line = logical_line
    found = line.find(':')
    if -1 < found < len(line) - 1:
        before = line[:found]
        if (before.count('{') <= before.count('}') and # {'a': 1} (dict)
            before.count('[') <= before.count(']') and # [1:2] (slice)
            not re.search(r'\blambda\b', before)):     # lambda x: x
            return found, "E701 multiple statements on one line (colon)"
    found = line.find(';')
    if -1 < found:
        return found, "E702 multiple statements on one line (semicolon)"


def python_3000_has_key(logical_line):
    """
    The {}.has_key() method will be removed in the future version of
    Python. Use the 'in' operation instead, like:
    d = {"a": 1, "b": 2}
    if "b" in d:
        print d["b"]
    """
    pos = logical_line.find('.has_key(')
    if pos > -1:
        return pos, "W601 .has_key() is deprecated, use 'in'"


def python_3000_raise_comma(logical_line):
    """
    When raising an exception, use "raise ValueError('message')"
    instead of the older form "raise ValueError, 'message'".

    The paren-using form is preferred because when the exception arguments
    are long or include string formatting, you don't need to use line
    continuation characters thanks to the containing parentheses.  The older
    form will be removed in Python 3000.
    """
    match = raise_comma_match(logical_line)
    if match:
        return match.start(1), "W602 deprecated form of raising exception"


##############################################################################
# Helper functions
##############################################################################


def expand_indent(line):
    """
    Return the amount of indentation.
    Tabs are expanded to the next multiple of 8.

    >>> expand_indent('    ')
    4
    >>> expand_indent('\\t')
    8
    >>> expand_indent('    \\t')
    8
    >>> expand_indent('       \\t')
    8
    >>> expand_indent('        \\t')
    16
    """
    result = 0
    for char in line:
        if char == '\t':
            result = result / 8 * 8 + 8
        elif char == ' ':
            result += 1
        else:
            break
    return result


##############################################################################
# Framework to run all checks
##############################################################################


def message(text):
    """Print a message."""
    # print >> sys.stderr, options.prog + ': ' + text
    # print >> sys.stderr, text
    print text


def find_checks(argument_name):
    """
    Find all globally visible functions where the first argument name
    starts with argument_name.
    """
    checks = []
    function_type = type(find_checks)
    for name, function in globals().iteritems():
        if type(function) is function_type:
            args = inspect.getargspec(function)[0]
            if len(args) >= 1 and args[0].startswith(argument_name):
                checks.append((name, function, args))
    checks.sort()
    return checks


def mute_string(text):
    """
    Replace contents with 'xxx' to prevent syntax matching.

    >>> mute_string('"abc"')
    '"xxx"'
    >>> mute_string("'''abc'''")
    "'''xxx'''"
    >>> mute_string("r'abc'")
    "r'xxx'"
    """
    start = 1
    end = len(text) - 1
    # String modifiers (e.g. u or r)
    if text.endswith('"'):
        start += text.index('"')
    elif text.endswith("'"):
        start += text.index("'")
    # Triple quotes
    if text.endswith('"""') or text.endswith("'''"):
        start += 2
        end -= 2
    return text[:start] + 'x' * (end - start) + text[end:]


class Checker:
    """
    Load a Python source file, tokenize it, check coding style.
    """

    def __init__(self, filename):
        self.filename = filename
        self.lines = file(filename).readlines()
        self.physical_checks = find_checks('physical_line')
        self.logical_checks = find_checks('logical_line')
        options.counters['physical lines'] = \
            options.counters.get('physical lines', 0) + len(self.lines)

    def readline(self):
        """
        Get the next line from the input buffer.
        """
        self.line_number += 1
        if self.line_number > len(self.lines):
            return ''
        return self.lines[self.line_number - 1]

    def readline_check_physical(self):
        """
        Check and return the next physical line. This method can be
        used to feed tokenize.generate_tokens.
        """
        line = self.readline()
        if line:
            self.check_physical(line)
        return line

    def run_check(self, check, argument_names):
        """
        Run a check plugin.
        """
        arguments = []
        for name in argument_names:
            arguments.append(getattr(self, name))
        return check(*arguments)

    def check_physical(self, line):
        """
        Run all physical checks on a raw input line.
        """
        self.physical_line = line
        if self.indent_char is None and len(line) and line[0] in ' \t':
            self.indent_char = line[0]
        for name, check, argument_names in self.physical_checks:
            result = self.run_check(check, argument_names)
            if result is not None:
                offset, text = result
                self.report_error(self.line_number, offset, text, check)

    def build_tokens_line(self):
        """
        Build a logical line from tokens.
        """
        self.mapping = []
        logical = []
        length = 0
        previous = None
        for token in self.tokens:
            token_type, text = token[0:2]
            if token_type in (tokenize.COMMENT, tokenize.NL,
                              tokenize.INDENT, tokenize.DEDENT,
                              tokenize.NEWLINE):
                continue
            if token_type == tokenize.STRING:
                text = mute_string(text)
            if previous:
                end_line, end = previous[3]
                start_line, start = token[2]
                if end_line != start_line: # different row
                    if self.lines[end_line - 1][end - 1] not in '{[(':
                        logical.append(' ')
                        length += 1
                elif end != start: # different column
                    fill = self.lines[end_line - 1][end:start]
                    logical.append(fill)
                    length += len(fill)
            self.mapping.append((length, token))
            logical.append(text)
            length += len(text)
            previous = token
        self.logical_line = ''.join(logical)
        assert self.logical_line.lstrip() == self.logical_line
        assert self.logical_line.rstrip() == self.logical_line

    def check_logical(self):
        """
        Build a line from tokens and run all logical checks on it.
        """
        options.counters['logical lines'] = \
            options.counters.get('logical lines', 0) + 1
        self.build_tokens_line()
        first_line = self.lines[self.mapping[0][1][2][0] - 1]
        indent = first_line[:self.mapping[0][1][2][1]]
        self.previous_indent_level = self.indent_level
        self.indent_level = expand_indent(indent)
        if options.verbose >= 2:
            print self.logical_line[:80].rstrip()
        for name, check, argument_names in self.logical_checks:
            if options.verbose >= 3:
                print '   ', name
            result = self.run_check(check, argument_names)
            if result is not None:
                offset, text = result
                if type(offset) is tuple:
                    original_number, original_offset = offset
                else:
                    for token_offset, token in self.mapping:
                        if offset >= token_offset:
                            original_number = token[2][0]
                            original_offset = (token[2][1]
                                               + offset - token_offset)
                self.report_error(original_number, original_offset,
                                  text, check)
        self.previous_logical = self.logical_line

    def check_all(self):
        """
        Run all checks on the input file.
        """
        self.file_errors = 0
        self.line_number = 0
        self.indent_char = None
        self.indent_level = 0
        self.previous_logical = ''
        self.blank_lines = 0
        self.tokens = []
        parens = 0
        for token in tokenize.generate_tokens(self.readline_check_physical):
            # print tokenize.tok_name[token[0]], repr(token)
            self.tokens.append(token)
            token_type, text = token[0:2]
            if token_type == tokenize.OP and text in '([{':
                parens += 1
            if token_type == tokenize.OP and text in '}])':
                parens -= 1
            if token_type == tokenize.NEWLINE and not parens:
                self.check_logical()
                self.blank_lines = 0
                self.tokens = []
            if token_type == tokenize.NL and not parens:
                if len(self.tokens) <= 1:
                    # The physical line contains only this token.
                    self.blank_lines += 1
                self.tokens = []
            if token_type == tokenize.COMMENT:
                source_line = token[4]
                token_start = token[2][1]
                if source_line[:token_start].strip() == '':
                    self.blank_lines = 0
                if text.endswith('\n') and not parens:
                    # The comment also ends a physical line.  This works around
                    # Python < 2.6 behaviour, which does not generate NL after
                    # a comment which is on a line by itself.
                    self.tokens = []
        return self.file_errors

    def report_error(self, line_number, offset, text, check):
        """
        Report an error, according to options.
        """
        if options.quiet == 1 and not self.file_errors:
            message(self.filename)
        self.file_errors += 1
        code = text[:4]
        options.counters[code] = options.counters.get(code, 0) + 1
        options.messages[code] = text[5:]
        if options.quiet:
            return
        if options.testsuite:
            base = os.path.basename(self.filename)[:4]
            if base == code:
                return
            if base[0] == 'E' and code[0] == 'W':
                return
        if ignore_code(code):
            return
        if options.counters[code] == 1 or options.repeat:
            message("%s:%s:%d: %s" %
                    (self.filename, line_number, offset + 1, text))
            if options.show_source:
                line = self.lines[line_number - 1]
                message(line.rstrip())
                message(' ' * offset + '^')
            if options.show_pep8:
                message(check.__doc__.lstrip('\n').rstrip())


def input_file(filename):
    """
    Run all checks on a Python source file.
    """
    if excluded(filename) or not filename_match(filename):
        return {}
    if options.verbose:
        message('checking ' + filename)
    options.counters['files'] = options.counters.get('files', 0) + 1
    errors = Checker(filename).check_all()
    if options.testsuite and not errors:
        message("%s: %s" % (filename, "no errors found"))
    return errors


def input_dir(dirname):
    """
    Check all Python source files in this directory and all subdirectories.
    """
    dirname = dirname.rstrip('/')
    if excluded(dirname):
        return 0
    errors = 0
    for root, dirs, files in os.walk(dirname):
        if options.verbose:
            message('directory ' + root)
        options.counters['directories'] = \
            options.counters.get('directories', 0) + 1
        dirs.sort()
        for subdir in dirs:
            if excluded(subdir):
                dirs.remove(subdir)
        files.sort()
        for filename in files:
            errors += input_file(os.path.join(root, filename))
    return errors


def excluded(filename):
    """
    Check if options.exclude contains a pattern that matches filename.
    """
    basename = os.path.basename(filename)
    for pattern in options.exclude:
        if fnmatch(basename, pattern):
            # print basename, 'excluded because it matches', pattern
            return True


def filename_match(filename):
    """
    Check if options.filename contains a pattern that matches filename.
    If options.filename is unspecified, this always returns True.
    """
    if not options.filename:
        return True
    for pattern in options.filename:
        if fnmatch(filename, pattern):
            return True


def ignore_code(code):
    """
    Check if options.ignore contains a prefix of the error code.
    """
    for ignore in options.ignore:
        if code.startswith(ignore):
            return True


def get_error_statistics():
    """Get error statistics."""
    return get_statistics("E")


def get_warning_statistics():
    """Get warning statistics."""
    return get_statistics("W")


def get_statistics(prefix=''):
    """
    Get statistics for message codes that start with the prefix.

    prefix='' matches all errors and warnings
    prefix='E' matches all errors
    prefix='W' matches all warnings
    prefix='E4' matches all errors that have to do with imports
    """
    stats = []
    keys = options.messages.keys()
    keys.sort()
    for key in keys:
        if key.startswith(prefix):
            stats.append('%-7s %s %s' %
                         (options.counters[key], key, options.messages[key]))
    return stats


def print_statistics(prefix=''):
    """Print overall statistics (number of errors and warnings)."""
    for line in get_statistics(prefix):
        print line


def print_benchmark(elapsed):
    """
    Print benchmark numbers.
    """
    print '%-7.2f %s' % (elapsed, 'seconds elapsed')
    keys = ['directories', 'files',
            'logical lines', 'physical lines']
    for key in keys:
        if key in options.counters:
            print '%-7d %s per second (%d total)' % (
                options.counters[key] / elapsed, key,
                options.counters[key])


def process_options(arglist=None):
    """
    Process options passed either via arglist or via command line args.
    """
    global options, args
    usage = "%prog [options] input ..."
    parser = OptionParser(usage)
    parser.add_option('-v', '--verbose', default=0, action='count',
                      help="print status messages, or debug with -vv")
    parser.add_option('-q', '--quiet', default=0, action='count',
                      help="report only file names, or nothing with -qq")
    parser.add_option('--exclude', metavar='patterns', default=default_exclude,
                      help="skip matches (default %s)" % default_exclude)
    parser.add_option('--filename', metavar='patterns',
                      help="only check matching files (e.g. *.py)")
    parser.add_option('--ignore', metavar='errors', default='',
                      help="skip errors and warnings (e.g. E4,W)")
    parser.add_option('--repeat', action='store_true',
                      help="show all occurrences of the same error")
    parser.add_option('--show-source', action='store_true',
                      help="show source code for each error")
    parser.add_option('--show-pep8', action='store_true',
                      help="show text of PEP 8 for each error")
    parser.add_option('--statistics', action='store_true',
                      help="count errors and warnings")
    parser.add_option('--benchmark', action='store_true',
                      help="measure processing speed")
    parser.add_option('--testsuite', metavar='dir',
                      help="run regression tests from dir")
    parser.add_option('--doctest', action='store_true',
                      help="run doctest on myself")
    options, args = parser.parse_args(arglist)
    if options.testsuite:
        args.append(options.testsuite)
    if len(args) == 0:
        parser.error('input not specified')
    options.prog = os.path.basename(sys.argv[0])
    options.exclude = options.exclude.split(',')
    for index in range(len(options.exclude)):
        options.exclude[index] = options.exclude[index].rstrip('/')
    if options.filename:
        options.filename = options.filename.split(',')
    if options.ignore:
        options.ignore = options.ignore.split(',')
    else:
        options.ignore = []
    options.counters = {}
    options.messages = {}

    return options, args


def _main():
    """
    Parse options and run checks on Python source.
    """
    options, args = process_options()
    if options.doctest:
        import doctest
        return doctest.testmod()
    start_time = time.time()
    errors = 0
    for path in args:
        if os.path.isdir(path):
            errors += input_dir(path)
        else:
            errors += input_file(path)
    elapsed = time.time() - start_time
    if options.statistics:
        print_statistics()
    if options.benchmark:
        print_benchmark(elapsed)
    return errors > 0

if __name__ == '__main__':
    sys.exit(_main())

########NEW FILE########
__FILENAME__ = show-coverage
#!/usr/bin/python

import os
import re
import sys


class Presentation:

    def __init__(self, name, lines, covered):
        self.name = name
        self.lines = lines
        self.covered = covered

        if self.covered == 0:
            self.percent = 0
        else:
            self.percent = 100 * self.covered / float(self.lines)

    def show(self, maxlen=20):
        format = '%%-%ds  %%3d %%%%   (%%4d / %%4d)' % maxlen
        print format % (self.name, self.percent, self.covered, self.lines)


class Coverage:

    def __init__(self):
        self.files = []
        self.total_lines = 0
        self.total_covered = 0

        # The python Trace class prints coverage results by prefixing
        # lines that got executed with a couple of spaces, the number
        # of times it has been executed and a colon. Uncovered lines
        # get prefixed with six angle brackets. Lines like comments
        # and blank lines just get indented.
        # This regexp will match executed and executable-but-not-covered lines.
        self.codeline_matcher = re.compile(r'^(>>>>>>)|(\s*\d+:)')

    def _strip_filename(self, filename):
        filename = os.path.basename(filename)
        if filename.endswith('.cover'):
            filename = filename[:-6]
        return filename

    def add_file(self, file):
        self.files.append(file)

    def show_results(self):
        if not hasattr(self, 'files'):
            print 'No coverage data'
            return

        self.maxlen = max(map(lambda f: len(self._strip_filename(f)),
                              self.files))
        print 'Coverage report:'
        print '-' * (self.maxlen + 23)
        for file in self.files:
            self.show_one(file)
        print '-' * (self.maxlen + 23)

        p = Presentation('Total', self.total_lines, self.total_covered)
        p.show(self.maxlen)

    def show_one(self, filename):
        f = open(filename)
        # Grab all executables lines
        lines = [line for line in f.readlines()
                 if self.codeline_matcher.match(line)]

        # Find out which of them were not executed
        uncovered_lines = [line for line in lines
                                   if line.startswith('>>>>>>')]
        if not lines:
            return

        filename = self._strip_filename(filename)

        p = Presentation(filename,
                         len(lines),
                         len(lines) - len(uncovered_lines))
        p.show(self.maxlen)

        self.total_lines += p.lines
        self.total_covered += p.covered


def main(args):
    c = Coverage()
    files = args[1:]
    files.sort()
    for file in files:
        if 'flumotion.test' in file:
            continue
        if '__init__' in file:
            continue
        c.add_file(file)

    c.show_results()

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
