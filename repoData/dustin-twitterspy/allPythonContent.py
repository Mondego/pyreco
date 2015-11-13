__FILENAME__ = add_timestamps
#!/usr/bin/env python

import sys
sys.path.append('lib')
sys.path.append('../lib')

import models

models._engine.execute("alter table users add column created_at timestamp")

########NEW FILE########
__FILENAME__ = convert_db
#!/usr/bin/env python

import sys
sys.path.extend(["lib", "../lib"])

from sqlite3 import dbapi2 as sqlite

from twisted.internet import reactor, defer

from twitterspy import db

GET_USERS="""
select jid, username, password, active, status, min_id, language,
       auto_post, friend_timeline_id, direct_message_id, created_at, id
    from users
"""

GET_TRACKS="""
select query
    from tracks join user_tracks on (tracks.id = user_tracks.track_id)
    where user_tracks.user_id = ?
"""

DB=sqlite.connect(sys.argv[1])

CUR=DB.cursor()

def parse_timestamp(ts):
    return None

def create(e, r):
    print "Creating record for", r[0]
    user = db.User()
    user.jid = r[0]
    user.username = r[1]
    user.password = r[2]
    user.active = bool(r[3])
    user.status = r[4]
    user.min_id = r[5]
    user.language = r[6]
    user.auto_post = bool(r[7])
    user.friend_timeline_id = r[8]
    user.direct_message_id = r[9]
    user.created_at = parse_timestamp(r[10])

    for tr in CUR.execute(GET_TRACKS, [r[11]]).fetchall():
        user.track(tr[0])

    return user.save()

@defer.deferredGenerator
def load_records():
    couch = db.get_couch()

    for r in CUR.execute(GET_USERS).fetchall():
        d = couch.openDoc(db.DB_NAME, str(r[0]))
        d.addErrback(create, r)
        wfd = defer.waitForDeferred(d)
        yield wfd

    reactor.stop()

reactor.callWhenRunning(load_records)
reactor.run()

########NEW FILE########
__FILENAME__ = create_couch
#!/usr/bin/env python

import sys
sys.path.extend(["lib", "../lib"])

from twisted.internet import reactor, defer

from twitterspy import db, cache

def parse_timestamp(ts):
    return None

@defer.deferredGenerator
def create_database():
    couch = db.get_couch()
    d = couch.createDB(db.DB_NAME)
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    doc="""
   {"language": "javascript",
   "views": {
       "counts": {
           "map": "function(doc) {
  if(doc.doctype == 'User') {
    var cnt = 0;
    if(doc.tracks) {
        cnt = doc.tracks.length;
    }
    emit(null, {users: 1, tracks: cnt});
  }
}",
           "reduce": "function(key, values) {
  var result = {users: 0, tracks: 0};
  values.forEach(function(p) {
     result.users += p.users;
     result.tracks += p.tracks;
  });
  return result;
}"
       },
       "status": {
           "map": "function(doc) {
  if(doc.doctype == 'User') {
    emit(doc.status, 1);
  }
}",
           "reduce": "function(k, v) {
  return sum(v);
}"
       },
       "service": {
           "map": "function(doc) {
  emit(doc.service_jid, 1);
}",
           "reduce": "function(k, v) {
  return sum(v);
}"
       }
   }}
"""
    d = couch.saveDoc(db.DB_NAME, doc, '_design/counts')
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    doc="""
{"language":"javascript","views":{"query_counts":{"map":"function(doc) {\n  if(doc.doctype == 'User') {\n    doc.tracks.forEach(function(query) {\n      emit(query, 1);\n    });\n  }\n}","reduce":"function(key, values) {\n   return sum(values);\n}"}}}
"""

    d = couch.saveDoc(db.DB_NAME, doc, '_design/query_counts')
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    doc="""
   {"language": "javascript",
   "views": {
       "active": {
           "map": "function(doc) {
  if(doc.doctype == 'User' && doc.active) {
    emit(null, doc._id);
  }
}"
       },
       "to_be_migrated": {
           "map": "function(doc) {
  if(doc.service_jid === 'twitterspy@jabber.org/bot') {
    emit(doc.service_jid, null);
  }
}"
       }
   }}
"""

    d = couch.saveDoc(db.DB_NAME, doc, '_design/users')
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    reactor.stop()

reactor.callWhenRunning(cache.connect)
reactor.callWhenRunning(create_database)
reactor.run()

########NEW FILE########
__FILENAME__ = scratch
#!/usr/bin/env python

import sys
sys.path.extend(['lib', '../lib'])

from twisted.internet import defer, reactor

from twitterspy import db

@defer.deferredGenerator
def f():
    d = db.get_active_users()
    wfd = defer.waitForDeferred(d)
    yield wfd
    u = wfd.getResult()
    print u

    reactor.stop()

reactor.callWhenRunning(f)
reactor.run()

########NEW FILE########
__FILENAME__ = verify_couch
#!/usr/bin/env python

import sys
sys.path.extend(["lib", "../lib"])

from sqlite3 import dbapi2 as sqlite

from twisted.internet import reactor, defer

from twitterspy import db

GET_USERS="""
select jid, username, password, active, status, min_id, language,
       auto_post, friend_timeline_id, direct_message_id, created_at, id
    from users
"""

DB=sqlite.connect(sys.argv[1])

CUR=DB.cursor()

def parse_timestamp(ts):
    return None

@defer.deferredGenerator
def verify_users():
    couch = db.get_couch()
    for r in CUR.execute(GET_USERS).fetchall():
        d = couch.openDoc(db.DB_NAME, str(r[0]))
        d.addErrback(lambda x: sys.stdout.write("Can't find %s\n" % r[0]))
        wfd = defer.waitForDeferred(d)
        yield wfd

    reactor.stop()

reactor.callWhenRunning(verify_users)
reactor.run()

########NEW FILE########
__FILENAME__ = paisley
# -*- test-case-name: test_paisley -*-
# Copyright (c) 2007-2008
# See LICENSE for details.

"""
CouchDB client.
"""

import simplejson
from urllib import urlencode

from twisted.web.client import HTTPClientFactory
from twisted.internet import defer

from twitterspy import cache

try:
    from base64 import b64encode
except ImportError:
    import base64

    def b64encode(s):
        return "".join(base64.encodestring(s).split("\n"))

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



class CouchDB(object):
    """
    CouchDB client: hold methods for accessing a couchDB.
    """

    def __init__(self, host, port=5984, dbName=None):
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
        self.host = host
        self.port = int(port)
        self.url_template = "http://%s:%s%%s" % (self.host, self.port)
        if dbName is not None:
            self.bindToDB(dbName)


    def parseResult(self, result):
        """
        Parse JSON result from the DB.
        """
        return simplejson.loads(result)


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
        """
        # Responses: {u'ok': True}, 409 Conflict, 500 Internal Server Error
        return self.put("/%s/" % (dbName,), ""
            ).addCallback(self.parseResult)


    def deleteDB(self, dbName):
        """
        Deletes the database on the server.
        """
        # Responses: {u'ok': True}, 404 Object Not Found
        return self.delete("/%s/" % (dbName,)
            ).addCallback(self.parseResult)


    def listDB(self):
        """
        List the databases on the server.
        """
        # Responses: list of db names
        return self.get("/_all_dbs").addCallback(self.parseResult)


    def infoDB(self, dbName):
        """
        Returns info about the couchDB.
        """
        # Responses: {u'update_seq': 0, u'db_name': u'mydb', u'doc_count': 0}
        # 404 Object Not Found
        return self.get("/%s/" % (dbName,)
            ).addCallback(self.parseResult)


    # Document operations

    def listDoc(self, dbName, reverse=False, startKey=0, count=-1):
        """
        List all documents in a given database.
        """
        # Responses: {u'rows': [{u'_rev': -1825937535, u'_id': u'mydoc'}],
        # u'view': u'_all_docs'}, 404 Object Not Found
        uri = "/%s/_all_docs" % (dbName,)
        args = {}
        if reverse:
            args["reverse"] = "true"
        if startKey > 0:
            args["startkey"] = int(startKey)
        if count >= 0:
            args["count"] = int(count)
        if args:
            uri += "?%s" % (urlencode(args),)
        return self.get(uri
            ).addCallback(self.parseResult)


    def openDoc(self, dbName, docId, revision=None, full=False, attachment=""):
        """
        Open a document in a given database.

        @param revision: if specified, the revision of the document desired.
        @type revision: C{str}

        @param full: if specified, return the list of all the revisions of the
            document, along with the document itself.
        @type full: C{bool}

        @param attachment: if specified, return the named attachment from the
            document.
        @type attachment: C{str}
        """
        # Responses: {u'_rev': -1825937535, u'_id': u'mydoc', ...}
        # 404 Object Not Found
        uri = "/%s/%s" % (dbName, docId)
        if revision is not None:
            uri += "?%s" % (urlencode({"rev": revision}),)
        elif full:
            uri += "?%s" % (urlencode({"full": "true"}),)
        elif attachment:
            uri += "?%s" % (urlencode({"attachment": attachment}),)
            # No parsing
            return  self.get(uri)

        rv = defer.Deferred()

        def mc_res(res):
            if res[1]:
                rv.callback(self.parseResult(res[1]))
            else:
                d = self.get(uri)
                def cf(s):
                    cache.mc.set(uri, s)
                    return s
                d.addCallback(cf)
                d.addCallback(lambda s: rv.callback(self.parseResult(s)))
                d.addErrback(lambda e: rv.errback(e))

        cache.mc.get(uri).addCallback(mc_res)

        return rv

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
        @type docId: C{str}
        """
        # Responses: {u'_rev': 1175338395, u'_id': u'mydoc', u'ok': True}
        # 409 Conflict, 500 Internal Server Error
        if not isinstance(body, (str, unicode)):
            body = simplejson.dumps(body)
        if docId is not None:
            uri = "/%s/%s" % (dbName, docId)
            cache.mc.delete(uri)
            d = self.put(uri, body)
        else:
            d = self.post("/%s/" % (dbName,), body)

        return d.addCallback(self.parseResult)


    def deleteDoc(self, dbName, docId, revision):
        """
        Delete a document on given database.
        """
        # Responses: {u'_rev': 1469561101, u'ok': True}
        # 500 Internal Server Error
        return self.delete("/%s/%s?%s" % (
                dbName,
                docId,
                urlencode({'rev': revision}))
            ).addCallback(self.parseResult)


    # View operations

    def openView(self, dbName, docId, viewId, **kwargs):
        """
        Open a view of a document in a given database.
        """
        uri = "/%s/_design/%s/_view/%s" % (dbName, docId, viewId)

        if kwargs:
            uri += "?%s" % (urlencode(kwargs),)

        return self.get(uri
            ).addCallback(self.parseResult)


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
        d = self.post("/%s/_temp_view" % (dbName,), view)
        return d.addCallback(self.parseResult)


    # Basic http methods

    def _getPage(self, uri, **kwargs):
        """
        C{getPage}-like.
        """
        url = self.url_template % (uri,)
        if not 'headers' in kwargs:
            kwargs['headers'] = {}
        kwargs["headers"]["Accept"] = "application/json"
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 10
        factory = HTTPClientFactory(url, **kwargs)
        from twisted.internet import reactor
        reactor.connectTCP(self.host, self.port, factory)
        return factory.deferred


    def get(self, uri):
        """
        Execute a C{GET} at C{uri}.
        """
        return self._getPage(uri, method="GET")


    def post(self, uri, body, **kwargs):
        """
        Execute a C{POST} of C{body} at C{uri}.
        """
        kwargs['postdata'] = body
        kwargs['method'] = 'POST'
        return self._getPage(uri, **kwargs)


    def put(self, uri, body):
        """
        Execute a C{PUT} of C{body} at C{uri}.
        """
        return self._getPage(uri, method="PUT", postdata=body)


    def delete(self, uri):
        """
        Execute a C{DELETE} at C{uri}.
        """
        return self._getPage(uri, method="DELETE")

########NEW FILE########
__FILENAME__ = adhoc_commands
from zope.interface import implements

from twisted.python import log
from twisted.internet import defer
from twisted.words.xish import domish
from wokkel.subprotocols import XMPPHandler, IQHandlerMixin
from twisted.words.protocols.jabber import jid, error
from twisted.words.protocols.jabber.xmlstream import toResponse
from wokkel import disco
from wokkel import generic
from wokkel import data_form
from wokkel.iwokkel import IDisco

import db
import protocol
import scheduling

NS_CMD = 'http://jabber.org/protocol/commands'
CMD = generic.IQ_SET + '/command[@xmlns="' + NS_CMD + '"]'

all_commands = {}

def form_required(orig):
    def every(self, user, iq, cmd):
        if cmd.firstChildElement():
            form = data_form.Form.fromElement(cmd.firstChildElement())
            return orig(self, user, iq, cmd, form)
        else:
            form = data_form.Form(formType="form", title=self.name)
            self.fillForm(user, iq, cmd, form)
            return self.genFormCmdResponse(iq, cmd, form)
    return every

class BaseCommand(object):
    """Base class for xep 0050 command processors."""

    def __init__(self, node, name):
        self.node = node
        self.name = name

    def _genCmdResponse(self, iq, cmd, status=None):

        command = domish.Element(('http://jabber.org/protocol/commands',
                                     "command"))
        command['node'] = cmd['node']
        if status:
            command['status'] = status
        try:
            command['action'] = cmd['action']
        except KeyError:
            pass

        return command

    def genFormCmdResponse(self, iq, cmd, form):
        command = self._genCmdResponse(iq, cmd, 'executing')

        actions = command.addElement('actions')
        actions['execute'] = 'next'
        actions.addElement('next')

        command.addChild(form.toElement())

        return command

    def __call__(self, user, iq, cmd):
        # Will return success
        pass

class TrackManagementCommand(BaseCommand):

    def __init__(self):
        super(TrackManagementCommand, self).__init__('tracks',
                                                     'List and manage tracks')

    def fillForm(self, user, iq, cmd, form):
        form.instructions = ["Select the items you no longer wish to track."]
        form.addField(data_form.Field(var='tracks', fieldType='list-multi',
                                      options=(data_form.Option(v, v)
                                               for v in sorted(user.tracks))))

    @form_required
    def __call__(self, user, iq, cmd, form):
        vals = set(form.fields['tracks'].values)
        log.msg("Removing:  %s" % vals)
        user.tracks = list(set(user.tracks).difference(vals))

        def worked(stuff):
            for v in vals:
                scheduling.queries.untracked(user.jid, v)

        user.save().addCallback(worked)

class TrackManagementCommand(BaseCommand):

    def __init__(self):
        super(TrackManagementCommand, self).__init__('tracks',
                                                     'List and manage tracks')

    def fillForm(self, user, iq, cmd, form):
        form.instructions = ["Select the items you no longer wish to track."]
        form.addField(data_form.Field(var='tracks', fieldType='list-multi',
                                      options=(data_form.Option(v, v)
                                               for v in sorted(user.tracks))))

    @form_required
    def __call__(self, user, iq, cmd, form):
        vals = set(form.fields['tracks'].values)
        log.msg("Removing:  %s" % vals)
        user.tracks = list(set(user.tracks).difference(vals))

        def worked(stuff):
            for v in vals:
                scheduling.queries.untracked(user.jid, v)

        user.save().addCallback(worked)

for __t in (t for t in globals().values() if isinstance(type, type(t))):
    if BaseCommand in __t.__mro__:
        try:
            i = __t()
            all_commands[i.node] = i
        except TypeError, e:
            # Ignore abstract bases
            log.msg("Error loading %s: %s" % (__t.__name__, str(e)))
            pass

class AdHocHandler(XMPPHandler, IQHandlerMixin):

    implements(IDisco)

    iqHandlers = { CMD: 'onCommand' }

    def connectionInitialized(self):
        super(AdHocHandler, self).connectionInitialized()
        self.xmlstream.addObserver(CMD, self.handleRequest)

    def _onUserCmd(self, user, iq, cmd):
        return all_commands[cmd['node']](user, iq, cmd)

    def onCommand(self, iq):
        log.msg("Got an adhoc command request")
        cmd = iq.firstChildElement()
        assert cmd.name == 'command'

        return db.User.by_jid(jid.JID(iq['from']).userhost()
                              ).addCallback(self._onUserCmd, iq, cmd)

    def getDiscoInfo(self, requestor, target, node):
        info = set()

        if node:
            info.add(disco.DiscoIdentity('automation', 'command-node'))
            info.add(disco.DiscoFeature('http://jabber.org/protocol/commands'))
        else:
            info.add(disco.DiscoFeature(NS_CMD))

        return defer.succeed(info)

    def getDiscoItems(self, requestor, target, node):
        myjid = jid.internJID(protocol.default_conn.jid)
        return defer.succeed([disco.DiscoItem(myjid, c.node, c.name)
                              for c in all_commands.values()])


########NEW FILE########
__FILENAME__ = cache
from twisted.python import log
from twisted.internet import protocol, reactor
from twisted.protocols import memcache

mc = None

class MemcacheFactory(protocol.ReconnectingClientFactory):

    def buildProtocol(self, addr):
        global mc
        self.resetDelay()
        log.msg("Connected to memcached.")
        mc = memcache.MemCacheProtocol()
        return mc

def connect():
    reactor.connectTCP('localhost', memcache.DEFAULT_PORT,
                       MemcacheFactory())

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
"""
Configuration for twitterspy.

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import ConfigParser
import commands

CONF=ConfigParser.ConfigParser()
CONF.read('twitterspy.conf')
VERSION=commands.getoutput("git describe").strip()
ADMINS=CONF.get("general", "admins").split(' ')

########NEW FILE########
__FILENAME__ = db
import ConfigParser

import config

db_type = config.CONF.get("db", "type")

if db_type == 'couch':
    from db_couch import *
elif db_type == 'sql':
    from db_sql import *
else:
    raise ConfigParser.Error("Unknown database type:  " + db_type)

########NEW FILE########
__FILENAME__ = db_base
import time
import base64

import config

class BaseUser(object):

    def __init__(self, jid=None):
        self.jid = jid
        self.active = True
        self.min_id = 0
        self.auto_post = False
        self.username = None
        self.password = None
        self.status = None
        self.friend_timeline_id = None
        self.direct_message_id = None
        self.created_at = time.time()
        self._rev = None
        self.service_jid = None
        self.tracks = []

    def __repr__(self):
        return "<User %s with %d tracks>" % (self.jid, len(self.tracks))

    def track(self, query):
        self.tracks.append(query)

    def untrack(self, query):
        try:
            self.tracks.remove(query)
            return True
        except ValueError:
            return False

    @property
    def has_credentials(self):
        return self.username and self.password

    @property
    def decoded_password(self):
        return base64.decodestring(self.password) if self.password else None

    @property
    def is_admin(self):
        return self.jid in config.ADMINS


########NEW FILE########
__FILENAME__ = db_couch
"""All kinds of stuff for talking to databases."""

import time

from twisted.python import log
from twisted.internet import defer, task

import paisley

import config
import db_base

DB_NAME='twitterspy'

def get_couch():
    try:
        port = config.CONF.getint('db', 'port')
    except:
        port = 5984
    return paisley.CouchDB(config.CONF.get('db', 'host'), port=port)

class User(db_base.BaseUser):

    @staticmethod
    def from_doc(doc):
        user = User()
        user.jid = doc['_id']
        v = doc
        user.active = v.get('active')
        user.auto_post = v.get('auto_post')
        user.username = v.get('username')
        user.password = v.get('password')
        user.status = v.get('status')
        user.friend_timeline_id = v.get('friend_timeline_id')
        user.direct_message_id = v.get('direct_message_id')
        user.service_jid = v.get('service_jid')
        user.created_at = v.get('created_at', time.time())
        user._rev = v.get('_rev')
        user.tracks = v.get('tracks', [])
        return user

    def to_doc(self):
        rv = dict(self.__dict__)
        rv['doctype'] = 'User'
        for k in [k for k,v in rv.items() if not v]:
            del rv[k]
        # Don't need two copies of the jids.
        del rv['jid']
        return rv

    @staticmethod
    def by_jid(jid):
        couch = get_couch()
        d = couch.openDoc(DB_NAME, str(jid))
        rv = defer.Deferred()
        d.addCallback(lambda doc: rv.callback(User.from_doc(doc)))
        d.addErrback(lambda e: rv.callback(User(jid)))
        return rv

    def save(self):
        return get_couch().saveDoc(DB_NAME, self.to_doc(), str(self.jid))

def initialize():
    def periodic(name, path):
        log.msg("Performing %s." % name)
        def cb(x):
            log.msg("%s result:  %s" % (name, repr(x)))
        headers = {'Content-Type': 'application/json'}
        get_couch().post("/" + DB_NAME + path,
                         '', headers=headers).addCallback(cb)

    compactLoop = task.LoopingCall(periodic, 'compaction', '/_compact')
    compactLoop.start(3600, now=False)

    viewCleanLoop = task.LoopingCall(periodic, 'view cleanup',
                                     '/_view_cleanup')
    viewCleanLoop.start(3*3600, now=False)

def model_counts():
    """Returns a deferred whose callback will receive a dict of object
    counts, e.g.

       {'users': n, 'tracks': m}
    """
    d = defer.Deferred()
    docd = get_couch().openView(DB_NAME, "counts", "counts")
    docd.addCallback(lambda r: d.callback(r['rows'][0]['value']))
    docd.addErrback(lambda e: d.errback(e))

    return d

def get_top10(n=10):
    """Returns a deferred whose callback will receive a list of at
    most `n` (number, 'tag') pairs sorted in reverse"""
    d = defer.Deferred()
    docd = get_couch().openView(DB_NAME, "query_counts", "query_counts",
                                group="true")
    def processResults(resp):
        rows = sorted([(r['value'], r['key']) for r in resp['rows']],
                      reverse=True)
        d.callback(rows[:n])
    docd.addCallback(processResults)
    docd.addErrback(lambda e: d.errback(e))
    return d

def get_active_users():
    """Returns a deferred whose callback will receive a list of active JIDs."""
    d = defer.Deferred()
    docd = get_couch().openView(DB_NAME, "users", "active")
    docd.addCallback(lambda res: d.callback([r['value'] for r in res['rows']]))
    docd.addErrback(lambda e: d.errback(e))
    return d

def get_service_distribution():
    """Returns a deferred whose callback will receive a list of jid -> count pairs"""
    d = defer.Deferred()
    docd = get_couch().openView(DB_NAME, "counts", "service", group='true')
    docd.addCallback(lambda rv: d.callback([(r['key'], r['value']) for r in rv['rows']]))
    docd.addErrback(lambda e: d.errback(e))
    return d

########NEW FILE########
__FILENAME__ = db_sql
"""All kinds of stuff for talking to databases."""

import base64
import time

from twisted.python import log
from twisted.internet import defer, task
from twisted.enterprise import adbapi

import config
import db_base

DB_POOL = adbapi.ConnectionPool(config.CONF.get("db", "driver"),
                                *eval(config.CONF.get("db", "args", raw=True)))

def parse_time(t):
    return None

def maybe_int(t):
    if t:
        return int(t)

class User(db_base.BaseUser):

    def __init__(self, jid=None):
        super(User, self).__init__(jid)
        self._id = -1

    @staticmethod
    def by_jid(jid):
        def load_user(txn):
            txn.execute("select active, auto_post, username, password, "
                        "friend_timeline_id, direct_message_id, created_at, "
                        "status, service_jid, id "
                        "from users where jid = ?", [jid])
            u = txn.fetchall()
            if u:
                r = u[0]
                log.msg("Loading from %s" % str(r))
                user = User()
                user.jid = jid
                user.active = maybe_int(r[0]) == 1
                user.auto_post = maybe_int(r[1]) == 1
                user.username = r[2]
                user.password = r[3]
                user.friend_timeline_id = maybe_int(r[4])
                user.direct_message_id = maybe_int(r[5])
                user.created_at = parse_time(r[6])
                user.status = r[7]
                user.service_jid = r[8]
                user._id = r[9]

                txn.execute("""select query
from tracks join user_tracks on (tracks.id = user_tracks.track_id)
where user_tracks.user_id = ?""", [user._id])
                user.tracks = [t[0] for t in txn.fetchall()]

                log.msg("Loaded %s (%s)" % (user, user.active))
                return user
            else:
                return User(jid)
        return DB_POOL.runInteraction(load_user)

    def _save_in_txn(self, txn):

        active = 1 if self.active else 0

        if self._id == -1:
            txn.execute("insert into users("
                        "  jid, active, auto_post, username, password, status, "
                        "  friend_timeline_id, direct_message_id, "
                        "  service_jid, created_at )"
                        " values(?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)",
                        [self.jid, active, self.auto_post, self.status,
                         self.username, self.password,
                         self.friend_timeline_id,
                         self.direct_message_id, self.service_jid])

                # sqlite specific...
            txn.execute("select last_insert_rowid()")
            self._id = txn.fetchall()[0][0]
        else:
            txn.execute("update users set active=?, auto_post=?, "
                        "  username=?, password=?, status=?, "
                        "  friend_timeline_id=?, direct_message_id=?, "
                        "  service_jid = ? "
                        " where id = ?",
                        [active, self.auto_post,
                         self.username, self.password, self.status,
                         self.friend_timeline_id,
                         self.direct_message_id, self.service_jid,
                         self._id])

        # TODO:  Begin difficult process of synchronizing track lists
        txn.execute("""select user_tracks.id, query
from tracks join user_tracks on (tracks.id = user_tracks.track_id)
where user_tracks.user_id = ?""", [self._id])
        db_tracks = {}
        for i, q in txn.fetchall():
            db_tracks[q] = str(i)

        rm_ids = [db_tracks[q] for q in db_tracks.keys() if not q in self.tracks]

        # Remove track records that no longer exist.
        txn.execute("delete from user_tracks where id in (?)",
                    [', '.join(rm_ids)])

        # Add the missing tracks.
        for q in [q for q in self.tracks if not q in db_tracks]:
            txn.execute("insert into user_tracks(user_id, track_id, created_at) "
                        " values(?, ?, current_timestamp)",
                        [self._id, self._qid(txn, q)])

        return True

    def _qid(self, txn, q):
        txn.execute("select id from tracks where query = ?", [q])
        r = txn.fetchall()
        if r:
            return r[0][0]
        else:
            txn.execute("insert into tracks (query) values(?)", [q])
            txn.execute("select last_insert_rowid()")
            res = txn.fetchall()
            return res[0][0]

    def save(self):
        return DB_POOL.runInteraction(self._save_in_txn)

def initialize():
    pass

def model_counts():
    """Returns a deferred whose callback will receive a dict of object
    counts, e.g.

       {'users': n, 'tracks': m}
    """
    d = defer.Deferred()

    dbd = DB_POOL.runQuery("""select 'users', count(*) from users
union all
select 'tracks', count(*) from user_tracks""")

    def cb(rows):
        rv = {}
        for r in rows:
            rv[r[0]] = int(r[1])
        d.callback(rv)

    dbd.addCallback(cb)
    dbd.addErrback(lambda e: d.errback(e))

    return d

def get_top10(n=10):
    """Returns a deferred whose callback will receive a list of at
    most `n` (number, 'tag') pairs sorted in reverse"""

    return DB_POOL.runQuery("""select count(*), t.query as watchers
 from tracks t join user_tracks ut on (t.id = ut.track_id)
 group by t.query
 order by watchers desc, query
 limit 10""")


def get_active_users():
    """Returns a deferred whose callback will receive a list of active JIDs."""

    d = defer.Deferred()
    dbd = DB_POOL.runQuery("select jid from users where active = 1")
    dbd.addCallback(lambda res: d.callback([r[0] for r in res]))
    dbd.addErrback(lambda e: d.errback(e))

    return d

########NEW FILE########
__FILENAME__ = moodiness
from collections import deque, defaultdict
import random

from twisted.python import log

import protocol

MAX_RESULTS = 1000

class Moodiness(object):

    MOOD_CHOICES=[
        (0.9, ('happy', 'humbled')),
        (0.5, ('frustrated', 'annoyed', 'anxious', 'grumpy')),
        (0.1, ('annoyed', 'dismayed', 'depressed', 'worried')),
        (float('-inf'), ('angry', 'cranky', 'disappointed'))
        ]

    def __init__(self):
        self.recent_results = deque()
        self.previous_good = (0, 0)

    def current_mood(self):
        """Get the current mood (good, total, percentage)"""
        if not self.recent_results:
            log.msg("Short-circuiting tally results since there aren't any.")
            return None, None, None, None
        try:
            good = reduce(lambda x, y: x + 1 if (y is True) else x, self.recent_results, 0)
        except TypeError:
            log.msg("Error reducing:  %s" % str(self.recent_results))
            raise
        total = len(self.recent_results)
        percentage = float(good) / float(total)
        choices=[v for a,v in self.MOOD_CHOICES if percentage >= a][0]
        mood=random.choice(choices)

        return mood, good, total, percentage

    def result_counts(self):
        rv = defaultdict(lambda: 0)
        for v in self.recent_results:
            rv[v] += 1
        return rv

    def __call__(self):
        mood, good, total, percentage = self.current_mood()
        if mood is None:
            return
        self.previous_good = (good, total)

        msg = ("Processed %d out of %d recent searches (previously %d/%d)."
            % (good, total, self.previous_good[0], self.previous_good[1]))

        log.msg(msg + " my mood is " + mood)
        for conn in protocol.current_conns.values():
            if conn.pubsub:
                conn.publish_mood(mood, msg)

    def add(self, result):
        if len(self.recent_results) >= MAX_RESULTS:
            self.recent_results.popleft()
        self.recent_results.append(result)

    def markSuccess(self, *args):
        """Record that a search was successfully performed."""
        self.add(True)

    def markFailure(self, error):
        """Record that a search failed to complete successfully."""
        try:
            erval = error.value.status
        except AttributeError:
            erval = False
        self.add(erval)
        return error

moodiness = Moodiness()

########NEW FILE########
__FILENAME__ = protocol
#!/usr/bin/env python

from __future__ import with_statement

import time

from twisted.python import log
from twisted.internet import protocol, reactor, threads
from twisted.words.xish import domish
from twisted.words.protocols.jabber.jid import JID
from twisted.words.protocols.jabber.xmlstream import IQ

from wokkel.xmppim import MessageProtocol, PresenceClientProtocol
from wokkel.xmppim import AvailablePresence

import db
import xmpp_commands
import config
import cache
import scheduling
import string

CHATSTATE_NS = 'http://jabber.org/protocol/chatstates'

current_conns = {}
presence_conns = {}

# This... could get big
# user_jid -> service_jid
service_mapping = {}

default_conn = None
default_presence = None

class TwitterspyMessageProtocol(MessageProtocol):

    pubsub = True

    def __init__(self, jid):
        super(TwitterspyMessageProtocol, self).__init__()
        self._pubid = 1
        self.jid = jid.full()

        self.preferred = self.jid == config.CONF.get("xmpp", "jid")

        goodChars=string.letters + string.digits + "/=,_+.-~@"
        self.jidtrans = self._buildGoodSet(goodChars)

    def _buildGoodSet(self, goodChars, badChar='_'):
        allChars=string.maketrans("", "")
        badchars=string.translate(allChars, allChars, goodChars)
        rv=string.maketrans(badchars, badChar * len(badchars))
        return rv

    def connectionInitialized(self):
        super(TwitterspyMessageProtocol, self).connectionInitialized()
        log.msg("Connected!")

        commands=xmpp_commands.all_commands
        self.commands={}
        for c in commands.values():
            self.commands[c.name] = c
            for a in c.aliases:
                self.commands[a] = c
        log.msg("Loaded commands: %s" % `sorted(commands.keys())`)

        self.pubsub = True

        # Let the scheduler know we connected.
        scheduling.connected()

        self._pubid = 1

        global current_conns, default_conn
        current_conns[self.jid] = self
        if self.preferred:
            default_conn = self

    def connectionLost(self, reason):
        log.msg("Disconnected!")

        global current_conns, default_conn
        del current_conns[self.jid]

        if default_conn == self:
            default_conn = None

        scheduling.disconnected()

    def _gen_id(self, prefix):
        self._pubid += 1
        return prefix + str(self._pubid)

    def publish_mood(self, mood_str, text):
        iq = IQ(self.xmlstream, 'set')
        iq['from'] = self.jid
        pubsub = iq.addElement(('http://jabber.org/protocol/pubsub', 'pubsub'))
        moodpub = pubsub.addElement('publish')
        moodpub['node'] = 'http://jabber.org/protocol/mood'
        item = moodpub.addElement('item')
        mood = item.addElement(('http://jabber.org/protocol/mood', 'mood'))
        mood.addElement(mood_str)
        mood.addElement('text').addContent(text)
        def _doLog(x):
            log.msg("Delivered mood: %s (%s)" % (mood_str, text))
        def _hasError(x):
            log.err(x)
            log.msg("Error delivering mood, disabling for %s." % self.jid)
            self.pubsub = False
        log.msg("Delivering mood: %s" % iq.toXml())
        d = iq.send()
        d.addCallback(_doLog)
        d.addErrback(_hasError)

    def typing_notification(self, jid):
        """Send a typing notification to the given jid."""

        msg = domish.Element((None, "message"))
        msg["to"] = jid
        msg["from"] = self.jid
        msg.addElement((CHATSTATE_NS, 'composing'))
        self.send(msg)

    def create_message(self):
        msg = domish.Element((None, "message"))
        msg.addElement((CHATSTATE_NS, 'active'))
        return msg

    def send_plain(self, jid, content):
        msg = self.create_message()
        msg["to"] = jid
        msg["from"] = self.jid
        msg["type"] = 'chat'
        msg.addElement("body", content=content)

        self.send(msg)

    def send_html(self, jid, body, html):
        msg = self.create_message()
        msg["to"] = jid
        msg["from"] = self.jid
        msg["type"] = 'chat'
        html = u"<html xmlns='http://jabber.org/protocol/xhtml-im'><body xmlns='http://www.w3.org/1999/xhtml'>"+unicode(html)+u"</body></html>"
        msg.addRawXml(u"<body>" + unicode(body) + u"</body>")
        msg.addRawXml(unicode(html))

        self.send(msg)

    def send_html_deduped(self, jid, body, html, key):
        key = string.translate(str(key), self.jidtrans)[0:128]
        def checkedSend(is_new, jid, body, html):
            if is_new:
                self.send_html(jid, body, html)
        cache.mc.add(key, "x").addCallback(checkedSend, jid, body, html)

    def onError(self, msg):
        log.msg("Error received for %s: %s" % (msg['from'], msg.toXml()))
        scheduling.unavailable_user(JID(msg['from']))

    def onMessage(self, msg):
        try:
            self.__onMessage(msg)
        except KeyError:
            log.err()

    def __onUserMessage(self, user, a, args, msg):
        cmd = self.commands.get(a[0].lower())
        if cmd:
            cmd(user, self, args)
        else:
            d = None
            if user.auto_post:
                d=self.commands['post']
            elif a[0][0] == '@':
                d=self.commands['post']
            if d:
                d(user, self, unicode(msg.body).strip())
            else:
                self.send_plain(msg['from'],
                                "No such command: %s\n"
                                "Send 'help' for known commands\n"
                                "If you intended to post your message, "
                                "please start your message with 'post', or see "
                                "'help autopost'" % a[0])

    def __onMessage(self, msg):
        if msg.getAttribute("type") == 'chat' and hasattr(msg, "body") and msg.body:
            self.typing_notification(msg['from'])
            a=unicode(msg.body).strip().split(None, 1)
            args = a[1] if len(a) > 1 else None
            db.User.by_jid(JID(msg['from']).userhost()
                           ).addCallback(self.__onUserMessage, a, args, msg)
        else:
            log.msg("Non-chat/body message: %s" % msg.toXml())

class TwitterspyPresenceProtocol(PresenceClientProtocol):

    _tracking=-1
    _users=-1
    started = time.time()
    connected = None
    lost = None
    num_connections = 0

    def __init__(self, jid):
        super(TwitterspyPresenceProtocol, self).__init__()
        self.jid = jid.full()

        self.preferred = self.jid == config.CONF.get("xmpp", "jid")

    def connectionInitialized(self):
        super(TwitterspyPresenceProtocol, self).connectionInitialized()
        self._tracking=-1
        self._users=-1
        self.connected = time.time()
        self.lost = None
        self.num_connections += 1
        self.update_presence()

        global presence_conns, default_presence
        presence_conns[self.jid] = self
        if self.preferred:
            default_presence = self

    def connectionLost(self, reason):
        self.connected = None
        self.lost = time.time()

    def presence_fallback(self, *stuff):
        log.msg("Running presence fallback.")
        self.available(None, None, {None: "Hi, everybody!"})

    def update_presence(self):
        try:
            if scheduling.available_requests > 0:
                self._update_presence_ready()
            else:
                self._update_presence_not_ready()
        except:
            log.err()

    def _update_presence_ready(self):
        def gotResult(counts):
            users = counts['users']
            tracking = counts['tracks']
            if tracking != self._tracking or users != self._users:
                status="Tracking %s topics for %s users" % (tracking, users)
                self.available(None, None, {None: status})
                self._tracking = tracking
                self._users = users
        db.model_counts().addCallback(gotResult).addErrback(self.presence_fallback)

    def _update_presence_not_ready(self):
        status="Ran out of Twitter API requests."
        self.available(None, 'away', {None: status})
        self._tracking = -1
        self._users = -1

    def availableReceived(self, entity, show=None, statuses=None, priority=0):
        log.msg("Available from %s (%s, %s, pri=%s)" % (
            entity.full(), show, statuses, priority))

        if priority >= 0 and show not in ['xa', 'dnd']:
            scheduling.available_user(entity)
        else:
            log.msg("Marking jid unavailable due to negative priority or "
                    "being somewhat unavailable.")
            scheduling.unavailable_user(entity)
        self._find_and_set_status(entity.userhost(), show)

    def unavailableReceived(self, entity, statuses=None):
        log.msg("Unavailable from %s" % entity.full())

        def cb():
            scheduling.unavailable_user(entity)

        self._find_and_set_status(entity.userhost(), 'offline', cb)

    def subscribedReceived(self, entity):
        log.msg("Subscribe received from %s" % (entity.userhost()))
        welcome_message="""Welcome to twitterspy.

Here you can use your normal IM client to post to twitter, track topics, watch
your friends, make new ones, and more.

Type "help" to get started.
"""
        global current_conns
        conn = current_conns[self.jid]
        conn.send_plain(entity.full(), welcome_message)
        def send_notices(counts):
            cnt = counts['users']
            msg = "New subscriber: %s ( %d )" % (entity.userhost(), cnt)
            for a in config.ADMINS:
                conn.send_plain(a, msg)
        db.model_counts().addCallback(send_notices)

    def _set_status(self, u, status, cb):

        # If we've got them on the preferred service, unsubscribe them
        # from this one.
        if not self.preferred and (u.service_jid and u.service_jid != self.jid):
            log.msg("Unsubscribing %s from non-preferred service %s" % (
                    u.jid, self.jid))
            self.unsubscribe(JID(u.jid))
            self.unsubscribed(JID(u.jid))
            return

        modified = False

        j = self.jid
        if (not u.service_jid) or (self.preferred and u.service_jid != j):
            u.service_jid = j
            modified = True

        if u.status != status:
            u.status=status
            modified = True

        global service_mapping
        service_mapping[u.jid] = u.service_jid
        log.msg("Service mapping for %s is %s" % (u.jid, u.service_jid))

        if modified:
            if cb:
                cb()
            return u.save()

    def _find_and_set_status(self, jid, status, cb=None):
        if status is None:
            status = 'available'
        def f():
            db.User.by_jid(jid).addCallback(self._set_status, status, cb)
        scheduling.available_sem.run(f)

    def unsubscribedReceived(self, entity):
        log.msg("Unsubscribed received from %s" % (entity.userhost()))
        self._find_and_set_status(entity.userhost(), 'unsubscribed')
        self.unsubscribe(entity)
        self.unsubscribed(entity)

    def subscribeReceived(self, entity):
        log.msg("Subscribe received from %s" % (entity.userhost()))
        self.subscribe(entity)
        self.subscribed(entity)
        self.update_presence()

    def unsubscribeReceived(self, entity):
        log.msg("Unsubscribe received from %s" % (entity.userhost()))
        self._find_and_set_status(entity.userhost(), 'unsubscribed')
        self.unsubscribe(entity)
        self.unsubscribed(entity)
        self.update_presence()

def conn_for(jid):
    return current_conns[service_mapping[jid]]

def presence_for(jid):
    return presence_conns[service_mapping[jid]]

def send_html_deduped(jid, plain, html, key):
    conn_for(jid).send_html_deduped(jid, plain, html, key)

def send_html(jid, plain, html):
    conn_for(jid).send_html(jid, plain, html)

def send_plain(jid, plain):
    conn_for(jid).send_plain(jid, plain)

########NEW FILE########
__FILENAME__ = scheduling
import time
import bisect
import random
import hashlib

from twisted.python import log
from twisted.internet import task, defer, reactor, threads
from twisted.words.protocols.jabber.jid import JID
from twisted.web import error

import twitter
import protocol

import db
import moodiness
import cache
import config
import search_collector

search_semaphore = defer.DeferredSemaphore(tokens=5)
private_semaphore = defer.DeferredSemaphore(tokens=20)
available_sem = defer.DeferredSemaphore(tokens=1)

MAX_REQUESTS = 20000
REQUEST_PERIOD = 3600

QUERY_FREQUENCY = 15 * 60
USER_FREQUENCY = 3 * 60

TIMEOUT=5

available_requests = MAX_REQUESTS
reported_empty = False
empty_resets = 0

suspended_until = 0

locks_requested = 0
locks_acquired = 0

def getTwitterAPI(*args):
    global available_requests, reported_empty
    now = time.time()
    if suspended_until > now:
        return ErrorGenerator()
    elif available_requests > 0:
        available_requests -= 1
        return twitter.Twitter(*args)
    else:
        if not reported_empty:
            reported_empty = True
            for conn in protocol.presence_conns.values():
                conn.update_presence()
        log.msg("Out of requests.  :(")
        # Return something that just generates deferreds that error.
        class ErrorGenerator(object):
            def __getattr__(self, attr):
                def error_generator(*args):
                    return defer.fail(
                        "There are no more available twitter requests.")
                return error_generator
        return ErrorGenerator()

def resetRequests():
    global available_requests, empty_resets, reported_empty
    if available_requests == 0:
        empty_resets += 1
        reported_empty = False
    available_requests = MAX_REQUESTS
    for conn in protocol.presence_conns.values():
        conn.update_presence()
    log.msg("Available requests are reset to %d" % available_requests)

class JidSet(set):

    def bare_jids(self):
        return set([JID(j).userhost() for j in self])

class Query(JidSet):

    loop_time = QUERY_FREQUENCY

    def __init__(self, query, last_id=0, getAPI=getTwitterAPI):
        super(Query, self).__init__()
        self.getAPI = getAPI
        self.query = query
        self.cache_key = self._compute_cache_key(query)
        self.loop = None

        cache.mc.get(self.cache_key).addCallback(self._doStart)

    def _compute_cache_key(self, query):
        return hashlib.md5(query.encode('utf-8')).hexdigest()

    def _doStart(self, res):
        if res[1]:
            self.last_id = res[1]
            # log.msg("Loaded last ID for %s from memcache: %s"
            #         % (self.query, self.last_id))
        else:
            log.msg("No last ID for %s" % (self.query,))
            self.last_id = 0
        r=random.Random()
        then = r.randint(1, min(60, self.loop_time / 2))
        # log.msg("Starting %s in %ds" % (self.query, then))
        reactor.callLater(then, self.start)

    def _sendMessages(self, something, results):
        first_shot = self.last_id == 0
        self.last_id = results.last_id
        if not first_shot:
            def send(r):
                for eid, plain, html in results.results:
                    for jid in self.bare_jids():
                        key = str(eid) + "@" + jid
                        protocol.send_html_deduped(jid, plain, html, key)
            dl = defer.DeferredList(results.deferreds)
            dl.addCallback(send)

    def __call__(self):
        # Don't bother if we're not connected...
        if protocol.current_conns:
            global search_semaphore, locks_requested
            locks_requested += 1
            # log.msg("Acquiring lock for %s" % self.query)
            d = search_semaphore.run(self._do_search)
            def _complete(x):
                global locks_requested, locks_acquired
                locks_requested -= 1
                locks_acquired -= 1
                # log.msg("Released lock for %s" % self.query)
            d.addBoth(_complete)
        else:
            log.msg("No xmpp connection, so skipping search of %s" % self.query)

    def _reportError(self, e):
        if int(e.value.status) == 420:
            global available_requests
            suspended_until = time.time() + 5
            log.msg("Twitter is reporting that we're out of stuff: " % str(e))
        else:
            log.msg("Error in search %s: %s" % (self.query, str(e)))

    def _save_track_id(self, x, old_id):
        if old_id != self.last_id:
            cache.mc.set(self.cache_key, str(self.last_id))

    def _do_search(self):
        global locks_acquired
        locks_acquired += 1
        # log.msg("Searching %s" % self.query)
        params = {}
        if self.last_id > 0:
            params['since_id'] = str(self.last_id)
        results=search_collector.SearchCollector(self.last_id)
        return self.getAPI().search(self.query, results.gotResult,
            params
            ).addCallback(moodiness.moodiness.markSuccess
            ).addErrback(moodiness.moodiness.markFailure
            ).addCallback(self._sendMessages, results
            ).addCallback(self._save_track_id, self.last_id
            ).addErrback(self._reportError)

    def start(self):
        self.loop = task.LoopingCall(self)
        d = self.loop.start(self.loop_time)
        d.addCallback(lambda x: log.msg("Search query for %s has been stopped: %s"
                                        % (self.query, x)))
        d.addErrback(lambda e: log.err("Search query for %s has errored:  %s"
                                       % (self.query, e)))

    def stop(self):
        log.msg("Stopping query %s" % self.query)
        if self.loop:
            self.loop.stop()
            self.loop = None

class QueryRegistry(object):

    def __init__(self, getAPI=getTwitterAPI):
        self.queries = {}
        self.getAPI = getAPI

    def add(self, user, query_str, last_id=0):
        # log.msg("Adding %s: %s" % (user, query_str))
        if not self.queries.has_key(query_str):
            self.queries[query_str] = Query(query_str, last_id, self.getAPI)
        self.queries[query_str].add(user)

    def untracked(self, user, query):
        q = self.queries.get(query)
        if q:
            if user in q:
                log.msg("Untracking %s from %s" % (query, user))
            q.discard(user)
            if not q:
                q.stop()
                del self.queries[query]
        else:
            log.msg("Query %s not found when untracking." % query)

    def remove(self, user):
        log.msg("Removing %s" % user)
        for k in list(self.queries.keys()):
            self.untracked(user, k)

    def remove_user(self, user, jids):
        for k in list(self.queries.keys()):
            for j in jids:
                self.untracked(j, k)

    def __len__(self):
        return len(self.queries)

class UserStuff(JidSet):

    loop_time = USER_FREQUENCY

    def __init__(self, short_jid, friends_id, dm_id):
        super(UserStuff, self).__init__()
        self.short_jid = short_jid
        self.last_friend_id = friends_id
        self.last_dm_id = dm_id

        self.username = None
        self.password = None
        self.loop = None

    def _format_message(self, type, entry, results):
        s = getattr(entry, 'sender', None)
        if not s:
            s=entry.user
        u = s.screen_name
        plain="[%s] %s: %s" % (type, u, entry.text)
        aurl = "https://twitter.com/" + u
        htype = '<b>' + type + '</b>'
        html="[%s] <a href='%s'>%s</a>: %s" % (htype, aurl, u, entry.text)
        bisect.insort(results, (entry.id, plain, html))

    def _deliver_messages(self, whatever, messages):
        for eid, plain, html in messages:
            for jid in self.bare_jids():
                key = str(eid) + "@" + jid
                protocol.send_html_deduped(jid, plain, html, key)

    def _gotDMResult(self, results):
        def f(entry):
            self.last_dm_id = max(self.last_dm_id, int(entry.id))
            self._format_message('direct', entry, results)
        return f

    def _gotFriendsResult(self, results):
        def f(entry):
            self.last_friend_id = max(self.last_friend_id, int(entry.id))
            self._format_message('friend', entry, results)
        return f

    def _deferred_write(self, u, mprop, new_val):
        setattr(u, mprop, new_val)
        u.save()

    def _maybe_update_prop(self, prop, mprop):
        old_val = getattr(self, prop)
        def f(x):
            new_val = getattr(self, prop)
            if old_val != new_val:
                db.User.by_jid(self.short_jid).addCallback(self._deferred_write,
                                                           mprop, new_val)
        return f

    def __call__(self):
        if self.username and self.password and protocol.current_conns:
            global private_semaphore
            private_semaphore.run(self._get_user_stuff)

    def _cleanup401s(self, e):
        e.trap(error.Error)
        if int(e.value.status) == 401:
            log.msg("Error 401 getting user data for %s, disabling"
                    % self.short_jid)
            self.stop()
        else:
            log.msg("Unknown http error:  %s: %s" % (e.value.status, str(e)))

    def _reportError(self, e):
        log.msg("Error getting user data for %s: %s" % (self.short_jid, str(e)))

    def _get_user_stuff(self):
        log.msg("Getting privates for %s" % self.short_jid)
        params = {}
        if self.last_dm_id > 0:
            params['since_id'] = str(self.last_dm_id)
        tw = getTwitterAPI(self.username, self.password)
        dm_list=[]
        tw.direct_messages(self._gotDMResult(dm_list), params).addCallback(
            self._maybe_update_prop('last_dm_id', 'direct_message_id')
            ).addCallback(self._deliver_messages, dm_list
            ).addErrback(self._cleanup401s).addErrback(self._reportError)

        if self.last_friend_id is not None:
            friend_list=[]
            tw.friends(self._gotFriendsResult(friend_list),
                {'since_id': str(self.last_friend_id)}).addCallback(
                    self._maybe_update_prop(
                        'last_friend_id', 'friend_timeline_id')
                ).addCallback(self._deliver_messages, friend_list
                ).addErrback(self._cleanup401s).addErrback(self._reportError)

    def start(self):
        log.msg("Starting %s" % self.short_jid)
        self.loop = task.LoopingCall(self)
        self.loop.start(self.loop_time, now=False)

    def stop(self):
        if self.loop:
            log.msg("Stopping user %s" % self.short_jid)
            self.loop.stop()
            self.loop = None

class UserRegistry(object):

    def __init__(self):
        self.users = {}

    def add(self, short_jid, full_jid, friends_id, dm_id):
        log.msg("Adding %s as %s" % (short_jid, full_jid))
        if not self.users.has_key(short_jid):
            self.users[short_jid] = UserStuff(short_jid, friends_id, dm_id)
        self.users[short_jid].add(full_jid)

    def set_creds(self, short_jid, un, pw):
        u=self.users.get(short_jid)
        if u:
            u.username = un
            u.password = pw
            available = un and pw
            if available and not u.loop:
                u.start()
            elif u.loop and not available:
                u.stop()
        else:
            log.msg("Couldn't find %s to set creds" % short_jid)

    def __len__(self):
        return len(self.users)

    def remove(self, short_jid, full_jid=None):
        q = self.users.get(short_jid)
        if not q:
            return
        q.discard(full_jid)
        if not q:
            q.stop()
            del self.users[short_jid]

queries = QueryRegistry()
users = UserRegistry()

def _entity_to_jid(entity):
    return entity if isinstance(entity, basestring) else entity.userhost()

def __init_user(entity, jids=[]):
    jid = _entity_to_jid(entity)
    def f(u):
        if u.active:
            full_jids = users.users.get(jid, jids)
            for j in full_jids:
                users.add(jid, j, u.friend_timeline_id, u.direct_message_id)
                for q in u.tracks:
                    queries.add(j, q)
            users.set_creds(jid, u.username, u.decoded_password)
    db.User.by_jid(jid).addCallback(f)

def enable_user(jid):
    global available_sem
    available_sem.run(__init_user, jid)

def disable_user(jid):
    queries.remove_user(jid, users.users.get(jid, []))
    users.set_creds(jid, None, None)

def available_user(entity):
    global available_sem
    available_sem.run(__init_user, entity, [entity.full()])

def unavailable_user(entity):
    queries.remove(entity.full())
    users.remove(entity.userhost(), entity.full())

def resources(jid):
    """Find all watched resources for the given JID."""
    jids=users.users.get(jid, [])
    return [JID(j).resource for j in jids]

def _reset_all():
    global queries
    global users
    for q in queries.queries.values():
        q.clear()
        q.stop()
    for u in users.users.values():
        u.clear()
        u.stop()
    queries = QueryRegistry()
    users = UserRegistry()

def connected():
    # _reset_all()
    pass

def disconnected():
    # _reset_all()
    pass

########NEW FILE########
__FILENAME__ = search_collector
import bisect

from twisted.python import log

import url_expansion

class SearchCollector(object):

    def __init__(self, last_id=0):
        self.results=[]
        self.last_id = last_id
        self.deferreds = []

    def gotResult(self, entry):
        eid = int(entry.id.split(':')[-1])
        self.last_id = max(self.last_id, eid)
        u = entry.author.name.split(' ')[0]
        plain=u + ": " + entry.title
        hcontent=entry.content.replace("&lt;", "<"
                                       ).replace("&gt;", ">"
                                       ).replace('&amp;', '&')
        html="<a href='%s'>%s</a>: %s" % (entry.author.uri, u, hcontent)
        def errHandler(e):
            log.err(e)
            return plain, html
        def saveResults(t):
            p, h = t
            bisect.insort(self.results, (eid, p, h))
        d = url_expansion.expander.expand(plain, html).addErrback(
            errHandler).addCallback(saveResults)
        self.deferreds.append(d)

########NEW FILE########
__FILENAME__ = url_expansion
import re

from twisted.internet import task, reactor, defer
from twisted.python import log

import cache
import longurl

class BasicUrl(object):

    def __init__(self, title, url):
        self.title = title
        self.url = url

class Expander(object):

    cache = True

    def __init__(self):
        self.lu = longurl.LongUrl('twitterspy')
        self.regex = None

    def loadServices(self):
        def _e(e):
            log.msg("Error loading expansion rules.  Trying again in 5s")
            reactor.callLater(5, self.loadServices)
        self.lu.getServices().addCallback(self._registerServices).addErrback(_e)

    def _registerServices(self, svcs):
        domains = set()
        for s in svcs.values():
            domains.update(s.domains)

        self.regex_str = "(http://(" + '|'.join(self.__fixup(d) for d in domains) + r")/\S+)"
        self.regex = re.compile(self.regex_str)

    def __fixup(self, d):
        return d.replace('.', r'\.')

    def _e(self, u):
        return u.replace("&", "&amp;")

    def expand(self, plain, html=None):
        rv = defer.Deferred()

        m = self.regex and self.regex.search(plain)
        if m:
            u, k = m.groups()
            def gotErr(e):
                log.err(e)
                reactor.callWhenRunning(rv.callback, (plain, html))
            def gotRes(res):
                # Sometimes, the expander returns its input.  That sucks.
                if res.url == u:
                    plainSub = plain
                    htmlSub = html
                else:
                    plainSub = plain.encode('utf-8').replace(
                        u, "%s (from %s)" % (self._e(res.url), u))
                    if html:
                        htmlSub = html.encode('utf-8').replace(
                            u, "%s" % (self._e(res.url),))
                    else:
                        htmlSub = None
                        log.msg("rewrote %s to %s" % (plain, plainSub))
                reactor.callWhenRunning(rv.callback, (plainSub, htmlSub))
            self._expand(u).addCallback(gotRes).addErrback(gotErr)
        else:
            # No match, immediately hand the message back.
            reactor.callWhenRunning(rv.callback, (plain, html))

        return rv

    def _cached_lookup(self, u, mc):
        rv = defer.Deferred()

        def identity(ignored_param):
            rv.callback(BasicUrl(None, u))

        def mc_res(res):
            if res[1]:
                rv.callback(BasicUrl(None, res[1]))
            else:
                def save_res(lu_res):
                    if lu_res:
                        mc.set(u, lu_res.url.encode('utf-8'))
                        rv.callback(BasicUrl(None, lu_res.url))
                    else:
                        log.msg("No response found for %s" % u)
                        rv.callback(BasicUrl(None, u))
                self.lu.expand(u).addCallback(save_res).addErrback(identity)

        mc.get(u).addCallback(mc_res).addErrback(identity)

        return rv

    def _expand(self, u):
        if self.cache:
            import protocol
            if cache.mc:
                return self._cached_lookup(u.encode('utf-8'), cache.mc)
            else:
                return self.lu.expand(u)
        else:
            return self.lu.expand(u)

expander = Expander()

########NEW FILE########
__FILENAME__ = xmpp_commands
# coding=utf-8
import re
import sys
import time
import types
import base64
import datetime
import urlparse
import sre_constants

from twisted.python import log
from twisted.words.xish import domish
from twisted.words.protocols.jabber.jid import JID
from twisted.web import client
from twisted.internet import reactor, threads, defer
from wokkel import ping

import db

import config
import twitter
import scheduling
import search_collector
import protocol
import moodiness

all_commands={}

def arg_required(validator=lambda n: n):
    def f(orig):
        def every(self, user, prot, args):
            if validator(args):
                orig(self, user, prot, args)
            else:
                prot.send_plain(user.jid, "Arguments required for %s:\n%s"
                    % (self.name, self.extended_help))
        return every
    return f

def login_required(orig):
    def every(self, user, prot, args):
        if user.has_credentials:
            orig(self, user, prot, args)
        else:
            prot.send_plain(user.jid, "You must twlogin before calling %s"
                % self.name)
    return every

def admin_required(orig):
    def every(self, user, prot, args):
        if user.is_admin:
            orig(self, user, prot, args)
        else:
            prot.send_plain(user.jid, "You're not an admin.")
    return every

class BaseCommand(object):
    """Base class for command processors."""

    def __get_extended_help(self):
        if self.__extended_help:
            return self.__extended_help
        else:
            return self.help

    def __set_extended_help(self, v):
        self.__extended_help=v

    extended_help=property(__get_extended_help, __set_extended_help)

    def __init__(self, name, help=None, extended_help=None, aliases=[]):
        self.name=name
        self.help=help
        self.aliases=aliases
        self.extended_help=extended_help

    def __call__(self, user, prot, args, session):
        raise NotImplementedError()

    def is_a_url(self, u):
        try:
            parsed = urlparse.urlparse(str(u))
            return parsed.scheme in ['http', 'https'] and parsed.netloc
        except:
            return False

class BaseStatusCommand(BaseCommand):

    def get_user_status(self, user):
        rv=[]
        rv.append("Jid:  %s" % user.jid)
        rv.append("Twitterspy status:  %s"
            % {True: 'Active', None: 'Inactive', False: 'Inactive'}[user.active])
        rv.append("Service jid:  %s" % user.service_jid)
        rv.append("Autopost:  %s"
                  % {True: 'on', None: 'off', False: 'off'}[user.auto_post])
        resources = scheduling.resources(user.jid)
        if resources:
            rv.append("I see you logged in with the following resources:")
            for r in resources:
                rv.append(u"  • %s" % r)
        else:
            rv.append("I don't see you logged in with any resource I'd send "
                "a message to.  Perhaps you're dnd, xa, or negative priority.")
        rv.append("You are currently tracking %d topics." % len(user.tracks))
        if user.has_credentials:
            rv.append("You're logged in to twitter as %s" % (user.username))
        if user.friend_timeline_id is not None:
            rv.append("Friend tracking is enabled.")
        return "\n".join(rv)

class StatusCommand(BaseStatusCommand):

    def __init__(self):
        super(StatusCommand, self).__init__('status', 'Check your status.')

    def __call__(self, user, prot, args):
        prot.send_plain(user.jid, self.get_user_status(user))

class HelpCommand(BaseCommand):

    def __init__(self):
        super(HelpCommand, self).__init__('help', 'You need help.')

    def __call__(self, user, prot, args):
        rv=[]
        if args and args.strip():
            c=all_commands.get(args.strip().lower(), None)
            if c:
                rv.append("Help for %s:\n" % c.name)
                rv.append(c.extended_help)
                if c.aliases:
                    rv.append("\nAliases:\n * ")
                    "\n * ".join(c.aliases)
            else:
                rv.append("Unknown command %s." % args)
        else:
            for k in sorted(all_commands.keys()):
                if (not k.startswith('adm_')) or user.is_admin:
                    rv.append('%s\t%s' % (k, all_commands[k].help))
        rv.append("\nFor more help, see http://dustin.github.com/twitterspy/")
        prot.send_plain(user.jid, "\n".join(rv))

class OnCommand(BaseCommand):
    def __init__(self):
        super(OnCommand, self).__init__('on', 'Enable tracks.')

    def __call__(self, user, prot, args):
        user.active=True
        def worked(stuff):
            scheduling.available_user(JID(user.jid))
            prot.send_plain(user.jid, "Enabled tracks.")
        def notWorked(e):
            log.err(e)
            prot.send_plain(user.jid, "Failed to enable.  Try again.")
        user.save().addCallback(worked).addErrback(notWorked)

class OffCommand(BaseCommand):
    def __init__(self):
        super(OffCommand, self).__init__('off', 'Disable tracks.')

    def __call__(self, user, prot, args):
        user.active=False
        def worked(stuff):
            scheduling.disable_user(user.jid)
            prot.send_plain(user.jid, "Disabled tracks.")
        def notWorked(e):
            log.err(e)
            prot.send_plain(user.jid, "Failed to disable.  Try again.")
        user.save().addCallback(worked).addErrback(notWorked)

class SearchCommand(BaseCommand):

    def __init__(self):
        super(SearchCommand, self).__init__('search',
            'Perform a search query (but do not track).')

    def _success(self, e, jid, prot, query, rv):
        # log.msg("%d results found for %s" % (len(rv.results), query))
        def send(r):
            plain = []
            html = []
            for eid, p, h in rv.results:
                plain.append(p)
                html.append(h)
            prot.send_html(jid, str(len(rv.results))
                           + " results for " + query
                           + "\n\n" + "\n\n".join(plain),
                           str(len(rv.results)) + " results for "
                           + query + "<br/>\n<br/>\n"
                           + "<br/>\n<br/>\n".join(html))
        defer.DeferredList(rv.deferreds).addCallback(send)

    def _error(self, e, jid, prot):
        mood, good, lrr, percentage = moodiness.moodiness.current_mood()
        rv = [":( Problem performing search."]
        if percentage > 0.5:
            rv.append("%.1f%% of recent searches have worked (%d out of %d)"
                      % ((percentage * 100.0), good, lrr))
        elif good == 0:
            rv.append("This is not surprising, "
                      "no recent searches worked for me, either (%d out of %d)"
                      % (good, lrr))
        else:
            rv.append("This is not surprising -- only %.1f%% work now anyway (%d out of %d)"
                      % ((percentage * 100.0), good, lrr))
        prot.send_plain(jid, "\n".join(rv))
        return e

    def _do_search(self, query, jid, prot):
        rv = search_collector.SearchCollector()
        scheduling.getTwitterAPI().search(query, rv.gotResult, {'rpp': '3'}
            ).addCallback(moodiness.moodiness.markSuccess
            ).addErrback(moodiness.moodiness.markFailure
            ).addCallback(self._success, jid, prot, query, rv
            ).addErrback(self._error, jid, prot
            ).addErrback(log.err)

    @arg_required()
    def __call__(self, user, prot, args):
        scheduling.search_semaphore.run(self._do_search, args, user.jid, prot)

class TWLoginCommand(BaseCommand):

    def __init__(self):
        super(TWLoginCommand, self).__init__('twlogin',
            'Set your twitter username and password (use at your own risk)')

    @arg_required()
    def __call__(self, user, prot, args):
        args = args.replace(">", "").replace("<", "")
        username, password=args.split(' ', 1)
        jid = user.jid
        scheduling.getTwitterAPI(username, password
                                 ).direct_messages(lambda x: None).addCallback(
            self.__credsVerified, prot, jid, username, password, user).addErrback(
            self.__credsRefused, prot, jid)

    def __credsRefused(self, e, prot, jid):
        log.msg("Failed to verify creds for %s: %s" % (jid, e))
        prot.send_plain(jid,
            ":( Your credentials were refused. "
                "Please try again: twlogin username password")

    def __credsVerified(self, x, prot, jid, username, password, user):
        user.username = username
        user.password = base64.encodestring(password)
        def worked(stuff):
            prot.send_plain(user.jid, "Added credentials for %s"
                % user.username)
            scheduling.users.set_creds(jid, username, password)
        def notWorked(stuff):
            log.err()
            prot.send_plain(user.jid, "Error setting credentials for %s. "
                "Please try again." % user.username)
        user.save().addCallback(worked).addErrback(notWorked)

class TWLogoutCommand(BaseCommand):

    def __init__(self):
        super(TWLogoutCommand, self).__init__('twlogout',
            "Discard your twitter credentials.")

    def __call__(self, user, prot, args):
        user.username = None
        user.password = None
        def worked(stuff):
            prot.send_plain(user.jid, "You have been logged out.")
            scheduling.users.set_creds(user.jid, None, None)
        def notWorked(e):
            log.err(e)
            prot.send_plain(user.jid, "Failed to log you out.  Try again.")
        user.save().addCallback(worked).addErrback(notWorked)

class TrackCommand(BaseCommand):

    def __init__(self):
        super(TrackCommand, self).__init__('track', "Start tracking a topic.")

    @arg_required()
    def __call__(self, user, prot, args):
        user.track(args)
        if user.active:
            rv = "Tracking %s" % args
        else:
            rv = "Will track %s as soon as you activate again." % args

        def worked(stuff):
            if user.active:
                scheduling.queries.add(user.jid, args, 0)
            prot.send_plain(user.jid, rv)
        def notWorked(e):
            log.err(e)
            prot.send_plain(user.jid, ":( Failed to save your tracks.  Try again.")
        user.save().addCallback(worked).addErrback(notWorked)

class UnTrackCommand(BaseCommand):

    def __init__(self):
        super(UnTrackCommand, self).__init__('untrack',
            "Stop tracking a topic.")

    @arg_required()
    def __call__(self, user, prot, args):
        log.msg("Untracking %s for %s" % (repr(args), user.jid))
        if user.untrack(args):
            def worked(stuff):
                log.msg("Untrack %s for %s successful." % (repr(args), user.jid))
                scheduling.queries.untracked(user.jid, args)
                prot.send_plain(user.jid, "Stopped tracking %s" % args)
            def notWorked(e):
                log.msg("Untrack %s for %s failed." % (repr(args), user.jid))
                log.err(e)
                prot.send_plain(user.jid, ":( Failed to save tracks. Try again")
            user.save().addCallback(worked).addErrback(notWorked)
        else:
            prot.send_plain(user.jid,
                "Didn't untrack %s (sure you were tracking it?)" % args)

class TracksCommand(BaseCommand):

    def __init__(self):
        super(TracksCommand, self).__init__('tracks',
            "List the topics you're tracking.", aliases=['tracking'])

    def __call__(self, user, prot, args):
        rv = ["Currently tracking:\n"]
        rv.extend(sorted(user.tracks))
        prot.send_plain(user.jid, "\n".join(rv))

class PostCommand(BaseCommand):

    def __init__(self):
        super(PostCommand, self).__init__('post',
            "Post a message to twitter.")

    def _posted(self, id, jid, username, prot):
        url = "https://twitter.com/%s/statuses/%s" % (username, id)
        prot.send_plain(jid, ":) Your message has been posted: %s" % url)

    def _failed(self, e, jid, prot):
        log.msg("Error updating for %s:  %s" % (jid, str(e)))
        prot.send_plain(jid, ":( Failed to post your message. "
            "Your password may be wrong, or twitter may be broken.")

    @arg_required()
    def __call__(self, user, prot, args):
        if user.has_credentials:
            jid = user.jid
            scheduling.getTwitterAPI(user.username, user.decoded_password).update(
                args, 'twitterspy'
                ).addCallback(self._posted, jid, user.username, prot
                ).addErrback(self._failed, jid, prot)
        else:
            prot.send_plain(user.jid, "You must twlogin before you can post.")

class FollowCommand(BaseCommand):

    def __init__(self):
        super(FollowCommand, self).__init__('follow',
            "Begin following a user.")

    def _following(self, e, jid, prot, user):
        prot.send_plain(jid, ":) Now following %s" % user)

    def _failed(self, e, jid, prot, user):
        log.msg("Failed a follow request %s" % repr(e))
        prot.send_plain(jid, ":( Failed to follow %s" % user)

    @arg_required()
    @login_required
    def __call__(self, user, prot, args):
        scheduling.getTwitterAPI(user.username, user.decoded_password).follow(
            str(args)).addCallback(self._following, user.jid, prot, args
            ).addErrback(self._failed, user.jid, prot, args)

class LeaveUser(BaseCommand):

    def __init__(self):
        super(LeaveUser, self).__init__('leave',
            "Stop following a user.", aliases=['unfollow'])

    def _left(self, e, jid, prot, user):
        prot.send_plain(jid, ":) No longer following %s" % user)

    def _failed(self, e, jid, prot, user):
        log.msg("Failed an unfollow request: %s", repr(e))
        prot.send_plain(jid, ":( Failed to stop following %s" % user)

    @arg_required()
    @login_required
    def __call__(self, user, prot, args):
        scheduling.getTwitterAPI(user.username, user.decoded_password).leave(
            str(args)).addCallback(self._left, user.jid, prot, args
            ).addErrback(self._failed, user.jid, prot, args)

class BlockCommand(BaseCommand):

    def __init__(self):
        super(BlockCommand, self).__init__('block',
                                            "Block a user.")

    def _blocked(self, e, jid, prot, user):
        prot.send_plain(jid, ":) Now blocking %s" % user)

    def _failed(self, e, jid, prot, user):
        log.msg("Failed a block request %s" % repr(e))
        prot.send_plain(jid, ":( Failed to block %s" % user)

    @arg_required()
    @login_required
    def __call__(self, user, prot, args):
        scheduling.getTwitterAPI(user.username, user.decoded_password).block(
            str(args)).addCallback(self._blocked, user.jid, prot, args
            ).addErrback(self._failed, user.jid, prot, args)

class UnblockCommand(BaseCommand):

    def __init__(self):
        super(UnblockCommand, self).__init__('unblock',
                                        "Unblock a user.")

    def _left(self, e, jid, prot, user):
        prot.send_plain(jid, ":) No longer blocking %s" % user)

    def _failed(self, e, jid, prot, user):
        log.msg("Failed an unblock request: %s", repr(e))
        prot.send_plain(jid, ":( Failed to unblock %s" % user)

    @arg_required()
    @login_required
    def __call__(self, user, prot, args):
        scheduling.getTwitterAPI(user.username, user.decoded_password).unblock(
            str(args)).addCallback(self._left, user.jid, prot, args
            ).addErrback(self._failed, user.jid, prot, args)

def must_be_on_or_off(args):
    return args and args.lower() in ["on", "off"]

class AutopostCommand(BaseCommand):

    def __init__(self):
        super(AutopostCommand, self).__init__('autopost',
            "Enable or disable autopost.")

    @arg_required(must_be_on_or_off)
    def __call__(self, user, prot, args):
        user.auto_post = (args.lower() == "on")
        def worked(stuff):
            prot.send_plain(user.jid, "Autoposting is now %s." % (args.lower()))
        def notWorked(e):
            prot.send_plain(user.jid, "Problem saving autopost. Try again.")
        user.save().addCallback(worked).addErrback(notWorked)

class WatchFriendsCommand(BaseCommand):

    def __init__(self):
        super(WatchFriendsCommand, self).__init__(
            'watch_friends',
            "Enable or disable watching friends (watch_friends on|off)",
            aliases=['watchfriends'])

    def _gotFriendStatus(self, user, prot):
        def f(entry):
            user.friend_timeline_id = entry.id
            def worked(stuff):
                # Tell scheduling so the process may begin.
                scheduling.users.set_creds(user.jid,
                                           user.username, user.decoded_password)
                prot.send_plain(user.jid, ":) Starting to watch friends.")
            def notWorked(e):
                prot.send_plain(user.jid, ":( Error watching friends.  Try again.")
            user.save().addCallback(worked).addErrback(notWorked)
        return f

    @arg_required(must_be_on_or_off)
    @login_required
    def __call__(self, user, prot, args):
        args = args.lower()
        if args == 'on':
            scheduling.getTwitterAPI(user.username, user.decoded_password).friends(
                self._gotFriendStatus(user, prot), params={'count': '1'})
        elif args == 'off':
            user.friend_timeline_id = None
            # Disable the privates search.
            scheduling.users.set_creds(user.jid, None, None)
            def worked(stuff):
                prot.send_plain(user.jid, ":) No longer watching your friends.")
            def notWorked(e):
                prot.send_plain(user.jid, ":( Problem stopping friend watches. Try again.")
            user.save().addCallback(worked).addErrback(notWorked)
        else:
            prot.send_plain(user.jid, "Watch must be 'on' or 'off'.")

class WhoisCommand(BaseCommand):

    def __init__(self):
        super(WhoisCommand, self).__init__('whois',
            'Find out who a user is.')

    def _fail(self, e, prot, jid, u):
        prot.send_plain(user.jid, "Couldn't get info for %s" % u)

    def _gotUser(self, u, prot, jid):
        html="""Whois <a
  href="https://twitter.com/%(screen_name)s">%(screen_name)s</a><br/><br/>
Name:  %(name)s<br/>
Home:  %(url)s<br/>
Where: %(location)s<br/>
Friends: <a
  href="https://twitter.com/%(screen_name)s/friends">%(friends_count)s</a><br/>
Followers: <a
  href="https://twitter.com/%(screen_name)s/followers">%(followers_count)s</a><br/>
Recently:<br/>
        %(status_text)s
"""
        params = dict(u.__dict__)
        params['status_text'] = u.status.text
        prot.send_html(jid, "(no plain text yet)", html % params)

    @arg_required()
    @login_required
    def __call__(self, user, prot, args):
        scheduling.getTwitterAPI(user.username, user.decoded_password).show_user(
            str(args)).addErrback(self._fail, prot, user.jid, args
            ).addCallback(self._gotUser, prot, user.jid)

class Top10Command(BaseCommand):

    def __init__(self):
        super(Top10Command, self).__init__('top10',
            'Get the top10 most common tracks.')

    def __call__(self, user, prot, args):
        def worked(top10):
            rv=["Top 10 most tracked topics:"]
            rv.append("")
            rv.extend(["%s (%d watchers)" % (row[1], row[0]) for row in top10])
            prot.send_plain(user.jid, "\n".join(rv))
        def notWorked(e):
            log.err(e)
            prot.send_plain(user.jid, "Problem grabbing top10")
        db.get_top10().addCallback(worked).addErrback(notWorked)

class AdminServiceDistributionCommand(BaseCommand):

    def __init__(self):
        super(AdminServiceDistributionCommand, self).__init__('adm_udist',
            'Find out the distribution of jid/service counts.')

    @admin_required
    def __call__(self, user, prot, args):
        def worked(dist):
            rv=["Service Distribution:"]
            rv.append("")
            rv.extend(["%s:  %s" % (row[1], row[0]) for row in dist])
            prot.send_plain(user.jid, "\n".join(rv))
        def notWorked(e):
            log.err(e)
            prot.send_plain(user.jid, "Problem grabbing distribution")
        db.get_service_distribution().addCallback(worked).addErrback(notWorked)

class MoodCommand(BaseCommand):

    def __init__(self):
        super(MoodCommand, self).__init__('mood',
            "Ask about twitterspy's mood.")

    def __call__(self, user, prot, args):
        mood, good, total, percentage = moodiness.moodiness.current_mood()
        if mood:
            rv=["My current mood is %s" % mood]
            rv.append("I've processed %d out of the last %d searches."
                      % (good, total))
        else:
            rv=["I just woke up.  Ask me in a minute or two."]
        rv.append("I currently have %d API requests available, "
                  "and have run out %d times."
                  % (scheduling.available_requests, scheduling.empty_resets))
        rv.append("Locks wanted: %d, locks held: %d"
                  % (scheduling.locks_requested, scheduling.locks_acquired))
        prot.send_plain(user.jid, "\n".join(rv))

class MoodDetailCommand(BaseCommand):

    def __init__(self):
        super(MoodDetailCommand, self).__init__('mood_detail',
                                                'Detailed mood info.')

    def __call__(self, user, prot, args):
        h = moodiness.moodiness.result_counts()
        rv = ["Recent statuses from searches:\n"]
        for s,c in sorted(h.items()):
            rv.append("%s: %d" % (str(s), c))
        prot.send_plain(user.jid, "\n".join(rv))

class UptimeCommand(BaseCommand):

    def __init__(self):
        super(UptimeCommand, self).__init__('uptime',
                                            "Ask about twitterspy's uptime.")

    def _pluralize(self, v, word):
        if v == 1:
            return str(v) + " " + word
        else:
            return str(v) + " " + word + "s"

    def _ts(self, td):
        rv = ""
        if td.days > 0:
            rv += self._pluralize(td.days, "day") + " "
        secs = td.seconds
        if secs >= 3600:
            rv += self._pluralize(int(secs / 3600), "hr") + " "
            secs = secs % 3600
        if secs >= 60:
            rv += self._pluralize(int(secs / 60), "min") + " "
            secs = secs % 60
        rv += self._pluralize(secs, "sec")
        return rv

    def _pluralize(self, n, w):
        if n == 1:
            return str(n) + " " + w
        else:
            return str(n) + " " + w + "s"

    def __call__(self, user, prot, args):
        time_format = "%Y/%m/%d %H:%M:%S"
        now = datetime.datetime.utcfromtimestamp(time.time())

        started = datetime.datetime.utcfromtimestamp(
            protocol.presence_for(user.jid).started)

        start_delta = now - started

        rv=[]
        rv.append("Twitterspy Standard Time:  %s"
                  % now.strftime(time_format))
        rv.append("Started at %s (%s ago)"
                  % (started.strftime(time_format), self._ts(start_delta)))

        for p in protocol.presence_conns.values():
            if p.connected:
                connected = datetime.datetime.utcfromtimestamp(p.connected)
                conn_delta = now - connected
                rv.append("Connected to %s at %s (%s ago, connected %s)"
                          % (p.jid, connected.strftime(time_format),
                             self._ts(conn_delta),
                             self._pluralize(p.num_connections, "time")))
            elif p.lost:
                lost = datetime.datetime.utcfromtimestamp(p.lost)
                lost_delta = now - lost
                rv.append("Lost connection to %s at %s (%s ago, connected %s)"
                          % (p.jid, lost.strftime(time_format),
                             self._ts(lost_delta),
                             self._pluralize(p.num_connections, "time")))
            else:
                rv.append("Not currently, nor ever connected to %s" % jid)
        prot.send_plain(user.jid, "\n\n".join(rv))

class AdminHangupCommand(BaseCommand):

    def __init__(self):
        super(AdminHangupCommand, self).__init__('adm_hangup',
                                                 'Disconnect an xmpp session.')

    @admin_required
    @arg_required()
    def __call__(self, user, prot, args):
        try:
            conn = protocol.presence_conns[args]
            prot.send_plain(user.jid, "Disconnecting %s" % args)
            reactor.callWhenRunning(conn.xmlstream.transport.loseConnection)
        except KeyError:
            prot.send_plain(user.jid, "Could not find session %s" % args)

class AdminSubscribeCommand(BaseCommand):

    def __init__(self):
        super(AdminSubscribeCommand, self).__init__('adm_subscribe',
            'Subscribe a user.')

    @admin_required
    @arg_required()
    def __call__(self, user, prot, args):
        prot.send_plain(user.jid, "Subscribing " + args)
        protocol.default_presence.subscribe(JID(args))

class AdminUserStatusCommand(BaseStatusCommand):

    def __init__(self):
        super(AdminUserStatusCommand, self).__init__('adm_status',
            "Check a user's status.")

    @admin_required
    @arg_required()
    def __call__(self, user, prot, args):
        def worked(u):
            prot.send_plain(user.jid, self.get_user_status(u))
        def notWorked(e):
            log.err(e)
            prot.send_plain(user.jid, "Failed to load user: " + str(e))
        db.User.by_jid(args).addCallback(worked).addErrback(notWorked)

class AdminPingCommand(BaseCommand):

    def __init__(self):
        super(AdminPingCommand, self).__init__('adm_ping',
            'Ping a JID')

    def ping(self, prot, fromjid, tojid):
        p = ping.Ping(prot.xmlstream, protocol.default_conn.jid, tojid)
        d = p.send()
        log.msg("Sending ping %s" % p.toXml())
        def _gotPing(x):
            duration = time.time() - p.start_time
            log.msg("pong %s" % tojid)
            prot.send_plain(fromjid, ":) Pong (%s) - %fs" % (tojid, duration))
        def _gotError(x):
            duration = time.time() - p.start_time
            log.msg("Got an error pinging %s: %s" % (tojid, x))
            prot.send_plain(fromjid, ":( Error pinging %s (%fs): %s"
                            % (tojid, duration, x.value.condition))
        d.addCallback(_gotPing)
        d.addErrback(_gotError)
        return d

    @admin_required
    @arg_required()
    def __call__(self, user, prot, args):
        # For bare jids, we'll send what was requested,
        # but also look up the user and send it to any active resources
        self.ping(prot, user.jid, args)
        j = JID(args)
        if j.user and not j.resource:
            for rsrc in scheduling.resources(args):
                j.resource=rsrc
                self.ping(prot, user.jid, j.full())

class AdminBroadcastCommand(BaseCommand):

    def __init__(self):
        super(AdminBroadcastCommand, self).__init__('adm_broadcast',
                                                    'Broadcast a message.')

    def _do_broadcast(self, users, prot, jid, msg):
        log.msg("Administrative broadcast from %s" % jid)
        for j in users:
            log.msg("Sending message to %s" % j)
            prot.send_plain(j, msg)
        prot.send_plain(jid, "Sent message to %d users" % len(users))

    @admin_required
    @arg_required()
    def __call__(self, user, prot, args):
        db.get_active_users().addCallback(self._do_broadcast, prot, user.jid, args)

class AdminUserPresenceCommand(BaseCommand):

    def __init__(self):
        super(AdminUserPresenceCommand, self).__init__('adm_userpresence',
                                                       "Find out about user presence.")

    @admin_required
    def __call__(self, user, prot, args):
        prot.send_plain(user.jid, "Watching %d active queries for %d active users."
                        % (len(scheduling.queries), len(scheduling.users)))

for __t in (t for t in globals().values() if isinstance(type, type(t))):
    if BaseCommand in __t.__mro__:
        try:
            i = __t()
            all_commands[i.name] = i
        except TypeError, e:
            # Ignore abstract bases
            log.msg("Error loading %s: %s" % (__t.__name__, str(e)))
            pass

########NEW FILE########
__FILENAME__ = xmpp_ping
from zope.interface import implements

from twisted.python import log
from twisted.internet import defer
from wokkel.subprotocols import XMPPHandler, IQHandlerMixin
from wokkel import disco
from wokkel import generic
from wokkel.iwokkel import IDisco

NS_PING = 'urn:xmpp:ping'
PING = generic.IQ_GET + '/ping[@xmlns="' + NS_PING + '"]'

class PingHandler(XMPPHandler, IQHandlerMixin):
    """
    XMPP subprotocol handler for Ping.

    This protocol is described in
    U{XEP-0199<http://www.xmpp.org/extensions/xep-0199.html>}.
    """

    implements(IDisco)

    iqHandlers = {PING: 'onPing'}

    def connectionInitialized(self):
        super(PingHandler, self).connectionInitialized()
        self.xmlstream.addObserver(PING, self.handleRequest)

    def onPing(self, iq):
        log.msg("Got ping from %s" % iq.getAttribute("from"))

    def getDiscoInfo(self, requestor, target, node):
        info = set()

        if not node:
            info.add(disco.DiscoFeature(NS_PING))

        return defer.succeed(info)

    def getDiscoItems(self, requestor, target, node):
        return defer.succeed([])


########NEW FILE########
__FILENAME__ = expansion_test
#!/usr/bin/env python

from __future__ import with_statement

import sys
import xml

from twisted.trial import unittest
from twisted.internet import defer, reactor

sys.path.extend(['lib', '../lib',
                 'lib/twitterspy', '../lib/twitterspy',
                 'lib/twisted-longurl/lib', '../lib/twisted-longurl/lib'])

import url_expansion

class SimpleService(object):

    def __init__(self, name, domains=None):
        self.name = name
        if domains:
            self.domains = domains
        else:
            self.domains = [name]

class FakeHTTP(object):

    def __init__(self):
        self.d = defer.Deferred()

    def getPage(self, *args, **kwargs):
        return self.d

class Result(url_expansion.BasicUrl):
    pass

class FakeLongUrl(object):

    def __init__(self, r):
        self.result = r

    def expand(self, u):
        rv = defer.Deferred()

        if self.result:
            reactor.callWhenRunning(rv.callback, self.result)
        else:
            reactor.callWhenRunning(rv.errback, RuntimeError("http failed"))
        return rv

class MatcherTest(unittest.TestCase):

    def setUp(self):
        self.expander = url_expansion.Expander()
        self.expander.cache = False
        self.expander._registerServices({'is.gd':
                                             SimpleService('is.gd'),
                                         'bit.ly':
                                             SimpleService('bit.ly',
                                                           ['bit.ly', 'bit.ley'])})

    def testNoopExpansion(self):
        d = self.expander.expand("test message")
        def v(r):
            self.assertEquals('test message', r[0])
            self.assertEquals(None, r[1])
        d.addCallback(v)
        return d

    def testExpansion(self):
        self.expander.lu = FakeLongUrl(Result('Test Title', 'http://w/'))

        d = self.expander.expand("test http://is.gd/whatever message")
        def v(r):
            self.assertEquals('test http://w/ (from http://is.gd/whatever) message', r[0])
            self.assertEquals(None, r[1])
        d.addCallback(v)
        return d

    def testIdentityExpansion(self):
        self.expander.lu = FakeLongUrl(Result(None, 'http://is.gd/whatever'))

        d = self.expander.expand("test http://is.gd/whatever message")
        def v(r):
            self.assertEquals('test http://is.gd/whatever message', r[0])
            self.assertEquals(None, r[1])
        d.addCallback(v)
        return d

    def testExpansionWithAmpersand(self):
        self.expander.lu = FakeLongUrl(Result('Test Title', 'http://w/?a=1&b=2'))

        d = self.expander.expand("test http://is.gd/whatever message")
        def v(r):
            self.assertEquals('test http://w/?a=1&amp;b=2 '
                              '(from http://is.gd/whatever) message', r[0])
            self.assertEquals(None, r[1])
        d.addCallback(v)
        return d


    def testFailedExpansion(self):
        self.expander.lu = FakeLongUrl(None)

        def v(r):
            self.assertEquals('test http://is.gd/whatever message', r[0])
            self.assertEquals(None, r[1])
            self.flushLoggedErrors(RuntimeError)
        def h(e):
            self.fail("Error bubbled up.")
        d = self.expander.expand("test http://is.gd/whatever message")
        d.addCallback(v)
        d.addErrback(h)
        return d

    def testHtmlExpansion(self):
        self.expander.lu = FakeLongUrl(Result('Test Title', 'http://w/'))

        d = self.expander.expand("test http://is.gd/whatever message",
                                 """test <a href="http://is.gd/whatever">"""
                                 """http://is.gd/whatever</a> message""")
        def v(r):
            self.assertEquals('test http://w/ (from http://is.gd/whatever) message', r[0])
            self.assertEquals("""test <a href="http://w/">"""
                              """http://w/</a> message""", r[1])
        d.addCallback(v)
        return d

########NEW FILE########
__FILENAME__ = mood_test
#!/usr/bin/env python

import sys

from twisted.trial import unittest
from twisted.internet import defer, reactor
from twisted.python import failure
from twisted import web

sys.path.extend(['lib', '../lib',
                 'lib/twitterspy', '../lib/twitterspy',
                 'lib/twitty-twister/twittytwister', '../lib/twitty-twister',
                 'lib/twisted-longurl/lib', '../lib/twisted-longurl',
                 'lib/wokkel', '../lib/wokkel'])

import moodiness

def webError(n):
    return failure.Failure(web.error.Error(n))

class MoodiTest(unittest.TestCase):

    def setUp(self):
        self.m = moodiness.Moodiness()

        for i in range(25):
            self.m.markSuccess("ignored")
        for i in range(25):
            self.m.markFailure("not an exception")
        for i in range(50):
            self.m.markFailure(webError('503'))

    def testMoodCounts(self):
        h = self.m.result_counts()
        self.assertEquals(25, h[True])
        self.assertEquals(25, h[False])
        self.assertEquals(50, h['503'])

    def testMood(self):
        mood, good, total, percentage = self.m.current_mood()
        self.assertTrue(mood in ('annoyed', 'dismayed', 'depressed', 'worried'))
        self.assertEquals(25, good)
        self.assertEquals(100, total)
        self.assertEquals(0.25, percentage)


    def testWeirdFailure(self):
        r = ['503', '503', '503', '503',
        '503', '503', '503', '503', '503', '503', '503', '503', '503',
        '503', '503', '503', '503', True, '503', '503', '503', '503',
        '503', '503', '503', '503', '503', '503', '503', '503', '503',
        True, True, True, True, True, True, True, True, True, True,
        True, True, True, True, '400', True, True, True, True, True,
        True, True, True, True, True, True, True, True, True, True,
        True, True, True, True, True, True, True, True, True, True,
        True, True, True, True, True, True, True]

        self.m = moodiness.Moodiness()
        self.m.recent_results = r

        mood, good, total, percentage = self.m.current_mood()
        self.assertTrue(mood in ('frustrated', 'annoyed', 'anxious', 'grumpy'))
        self.assertEquals(47, good)
        self.assertEquals(78, total)
        self.assertAlmostEquals(0.60, percentage, .01)

########NEW FILE########
__FILENAME__ = scheduling_test
import sys
import xml

from twisted.trial import unittest
from twisted.internet import defer, reactor

sys.path.extend(['lib', '../lib',
                 'lib/twitterspy', '../lib/twitterspy',
                 'lib/wokkel/', '../lib/wokkel/',
                 'lib/twisted-longurl/lib', '../lib/twisted-longurl/lib/',
                 'lib/twitty-twister/twittytwister', '../lib/twitty-twister/twittytwister'])

import cache
import scheduling

class FakeTwitterAPI(object):

    def __init__(self, res):
        self.res = res

    def search(self, query, cb, params):
        def f():
            for r in self.res:
                cb(res)
            return defer.succeed("yay")
        reactor.callWhenRunning(f)

class FakeCache(object):

    def get(self, x):
        return defer.succeed([0, None])

    def set(self, k, v):
        return defer.succeed(None)

class QueryRegistryTest(unittest.TestCase):

    started = 0
    stopped = 0

    def setUp(self):
        import twisted
        twisted.internet.base.DelayedCall.debug = True
        super(QueryRegistryTest, self).setUp()

        cache.mc = FakeCache()
        self.patch(scheduling.Query, '_doStart', self.trackStarted)
        self.patch(scheduling.Query, 'start', lambda *x: self.fail("unexpected start"))
        self.patch(scheduling.Query, 'stop', self.trackStopped)

        self.qr = scheduling.QueryRegistry(lambda x: FakeTwitterAPI(['a']))
        self.assertEquals(0, len(self.qr))
        self.qr.add('dustin@localhost', 'test query')

    def trackStarted(self, *args):
        self.started += 1

    def trackStopped(self, *args):
        self.stopped += 1

    def testTracking(self):
        self.assertEquals(1, len(self.qr))
        self.assertEquals(1, self.started)

    def testUntracking(self):
        self.qr.untracked('dustin@localhost', 'test query')
        self.assertEquals(0, len(self.qr))
        self.assertEquals(1, self.stopped)

    def testRemove(self):
        self.qr.add('dustin@localhost', 'test query two')
        self.assertEquals(2, len(self.qr))
        self.assertEquals(2, self.started)
        self.qr.remove('dustin@localhost')
        self.assertEquals(0, len(self.qr))
        self.assertEquals(2, self.stopped)

    def testRemoveTwo(self):
        self.qr.add('dustin2@localhost', 'test query two')
        self.assertEquals(2, len(self.qr))
        self.assertEquals(2, self.started)
        self.qr.remove('dustin@localhost')
        self.assertEquals(1, len(self.qr))
        self.assertEquals(1, self.stopped)

    def testRemoveUser(self):
        self.qr.add('dustin@localhost', 'test query two')
        self.assertEquals(2, len(self.qr))
        self.assertEquals(2, self.started)
        self.qr.remove_user('', ['dustin@localhost'])
        self.assertEquals(0, len(self.qr))
        self.assertEquals(2, self.stopped)

    def testRemoveUserTwo(self):
        self.qr.add('dustin@localhost', 'test query two')
        self.qr.add('dustin2@localhost', 'test query two')
        self.assertEquals(2, len(self.qr))
        self.assertEquals(2, self.started)
        self.qr.remove_user('', ['dustin@localhost'])
        self.assertEquals(1, len(self.qr))
        self.assertEquals(1, self.stopped)

class JidSetTest(unittest.TestCase):

    def testIteration(self):
        js = scheduling.JidSet()
        js.add('dustin@localhost/r1')
        js.add('dustin@localhost/r2')
        js.add('dustin@elsewhere/r1')

        self.assertEquals(3, len(js))

        self.assertEquals(2, len(js.bare_jids()))

        self.assertTrue('dustin@localhost', js.bare_jids())
        self.assertTrue('dustin@elsewhere', js.bare_jids())

########NEW FILE########
__FILENAME__ = search_collector_test
from __future__ import with_statement

import sys
import xml

from twisted.trial import unittest
from twisted.internet import defer, reactor

sys.path.extend(['lib', '../lib',
                 'lib/twitterspy', '../lib/twitterspy',
                 'lib/twisted-longurl/lib', '../lib/twisted-longurl/lib'])

import search_collector, url_expansion

class FakeAuthor(object):

    def __init__(self, name, uri):
        self.name = name
        self.uri = uri

class FakeEntry(object):

    def __init__(self, i, author, title, content):
        self.id = i
        self.author = author
        self.title = title
        self.content = content

class FakeUrlExpander(object):

    def __init__(self):
        self.expectations = set()

    def instantError(self, plain, html):
        return defer.fail(RuntimeError("failed " + plain))

    def instantSuccess(self, plain, html):
        return defer.succeed((plain + " m", html + " m"))

    def expand(self, plain, html):
        if plain in self.expectations:
            return self.instantSuccess(plain, html)
        else:
            return self.instantError(plain, html)

class SearchCollectorTest(unittest.TestCase):

    def setUp(self):
        url_expansion.expander = FakeUrlExpander()

    def doSomeStuff(self, sc):
        sc.gotResult(FakeEntry('blah:14',
                               FakeAuthor('dustin author', 'http://w/'),
                               'Some Title 14',
                               'Some Content 14'))

        sc.gotResult(FakeEntry('blah:11',
                               FakeAuthor('dustin author', 'http://w/'),
                               'Some Title 11',
                               'Some Content 11'))

        sc.gotResult(FakeEntry('blah:13',
                               FakeAuthor('dustin author', 'http://w/'),
                               'Some Title 13',
                               'Some Content 13'))

    def testSimpleNoMatches(self):
        sc = search_collector.SearchCollector()
        self.doSomeStuff(sc)

        self.assertEquals(3, len(sc.deferreds))
        dl = defer.DeferredList(sc.deferreds)

        def verify(r):
            self.assertEquals([11, 13, 14], [e[0] for e in sc.results])
            self.assertEquals("dustin: Some Title 11", sc.results[0][1])
            self.flushLoggedErrors(RuntimeError)

        dl.addCallback(verify)

        return dl

    def testSomeMatches(self):
        url_expansion.expander.expectations.add('dustin: Some Title 11')
        sc = search_collector.SearchCollector()
        self.doSomeStuff(sc)

        self.assertEquals(3, len(sc.deferreds))
        dl = defer.DeferredList(sc.deferreds)

        def verify(r):
            self.assertEquals([11, 13, 14], [e[0] for e in sc.results])
            self.assertEquals("dustin: Some Title 11 m", sc.results[0][1])
            self.assertEquals("dustin: Some Title 13", sc.results[1][1])
            self.flushLoggedErrors(RuntimeError)

        dl.addCallback(verify)

        return dl

########NEW FILE########
