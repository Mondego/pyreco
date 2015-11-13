__FILENAME__ = error
""" Error class for different punjab parts. """


class Error(Exception):
    stanza_error = ''
    punjab_error = ''
    msg          = ''
    children     = []
    def __init__(self,msg = None):
        Exception.__init__(self)
        if msg:
            self.stanza_error = msg
            self.punjab_error = msg
            self.msg          = msg

    def __str__(self):
        return self.stanza_error

class BadRequest(Error):
    stanza_error = 'bad-request'
    msg = 'bad-request'

class InternalServerError(Error):
    msg = 'internal-server-error'
    stanza_error = 'internal-server-error'

class RemoteConnectionFailed(Error):
    msg = 'remote-connection-failed'
    stanza_error = 'remote-connection-failed'

class NotFound(Error):
    msg = '404 not found'
    stanza_error = 'not-found'

class NotAuthorized(Error):
    pass

class NotImplemented(Error):
    pass


NS_XMPP_STANZAS = "urn:ietf:params:xml:ns:xmpp-stanzas"

conditions = {
    'bad-request':		{'code': '400', 'type': 'modify'},
    'not-authorized':		{'code': '401', 'type': 'cancel'},
    'forbidden':		{'code': '403', 'type': 'cancel'},
    'not-found':		{'code': '404', 'type': 'cancel'},
    'not-acceptable':		{'code': '406', 'type': 'modify'},
    'conflict':			{'code': '409', 'type': 'cancel'},
    'internal-server-error':	{'code': '500', 'type': 'wait'},
    'feature-not-implemented':  {'code': '501', 'type': 'cancel'},
    'service-unavailable':	{'code': '503', 'type': 'cancel'},
    'host-gone':		{'code': '200', 'type': 'terminate'},
    'host-unknown':		{'code': '200', 'type': 'terminate'},
    'improper-addressing':	{'code': '200', 'type': 'terminate'},
    'other-request':	{'code': '200', 'type': 'terminate'},
    'remote-connection-failed':	{'code': '200', 'type': 'terminate'},
    'remote-stream-error':	{'code': '200', 'type': 'terminate'},
    'see-other-uri':	{'code': '200', 'type': 'terminate'},
    'system-shutdown':	{'code': '200', 'type': 'terminate'},
    'undefined-condition':	{'code': '200', 'type': 'terminate'},
    'item-not-found':		{'code': '200', 'type': 'terminate'},

}


########NEW FILE########
__FILENAME__ = httpb
"""
 http binding interface
"""
from twisted.python import components
from twisted.web import server, resource
from twisted.internet import defer, task
from twisted.python import log

from zope.interface import Interface, implements

try:
    from twisted.words.xish import domish
except ImportError:
    from twisted.xish import domish

import hashlib, time
import error
from session import make_session
import punjab
from punjab.xmpp import ns


NS_BIND = 'http://jabber.org/protocol/httpbind'
NS_FEATURES = 'http://etherx.jabber.org/streams'
NS_XMPP = 'urn:xmpp:xbosh'

class DummyElement:
    """
    dummy element for a quicker parse
    """
    # currently not used
    def __init__(self, *args, **kwargs):

        self.children = []



class HttpbElementStream(domish.ExpatElementStream):
    """
    add rawXml to the elements
    """

    def __init__(self, prefixes=None):
        domish.ExpatElementStream.__init__(self)
        self.prefixes = {}
        if prefixes:
            self.prefixes.update(prefixes)
        self.prefixes.update(domish.G_PREFIXES)
        self.prefixStack = [domish.G_PREFIXES.values()]
        self.prefixCounter = 0


    def getPrefix(self, uri):
        if not self.prefixes.has_key(uri):
            self.prefixes[uri] = "xn%d" % (self.prefixCounter)
            self.prefixCounter = self.prefixCounter + 1
        return self.prefixes[uri]

    def prefixInScope(self, prefix):
        stack = self.prefixStack
        for i in range(-1, (len(self.prefixStack)+1) * -1, -1):
            if prefix in stack[i]:
                return True
        return False

    def _onStartElement(self, name, attrs):
        # Generate a qname tuple from the provided name
        attr_str   = ''
        defaultUri = None
        uri        = None
        qname = name.split(" ")
        if len(qname) == 1:
            qname = ('', name)
            currentUri = None
        else:
            currentUri = qname[0]
        if self.currElem:
            defaultUri = self.currElem.defaultUri
            uri = self.currElem.uri

        if not defaultUri and currentUri in self.defaultNsStack:
            defaultUri = self.defaultNsStack[1]

        if defaultUri and currentUri != defaultUri:

            raw_xml = u"""<%s xmlns='%s'%s""" % (qname[1], qname[0], '%s')

        else:
            raw_xml = u"""<%s%s""" % (qname[1], '%s')


        # Process attributes

        for k, v in attrs.items():
            if k.find(" ") != -1:
                aqname = k.split(" ")
                attrs[(aqname[0], aqname[1])] = v

                attr_prefix = self.getPrefix(aqname[0])
                if not self.prefixInScope(attr_prefix):
                    attr_str = attr_str + " xmlns:%s='%s'" % (attr_prefix,
                                                              aqname[0])
                    self.prefixStack[-1].append(attr_prefix)
                attr_str = attr_str + " %s:%s='%s'" % (attr_prefix,
                                                       aqname[1],
                                                       domish.escapeToXml(v,
                                                                          True))
                del attrs[k]
            else:
                v = domish.escapeToXml(v, True)
                attr_str = attr_str + " " + k + "='" + v + "'"

        raw_xml = raw_xml % (attr_str,)

        # Construct the new element
        e = domish.Element(qname, self.defaultNsStack[-1], attrs, self.localPrefixes)
        self.localPrefixes = {}

        # Document already started
        if self.documentStarted == 1:
            if self.currElem != None:
                if len(self.currElem.children)==0 or isinstance(self.currElem.children[-1], domish.Element):
                    if self.currRawElem[-1] != ">":
                        self.currRawElem = self.currRawElem +">"

                self.currElem.children.append(e)
                e.parent = self.currElem

            self.currRawElem = self.currRawElem + raw_xml
            self.currElem = e
        # New document
        else:
            self.currRawElem = u''
            self.documentStarted = 1
            self.DocumentStartEvent(e)

    def _onEndElement(self, _):
        # Check for null current elem; end of doc
        if self.currElem is None:
            self.DocumentEndEvent()

        # Check for parent that is None; that's
        # the top of the stack
        elif self.currElem.parent is None:
            if len(self.currElem.children)>0:
                self.currRawElem = self.currRawElem + "</"+ self.currElem.name+">"
            else:
                self.currRawElem = self.currRawElem + "/>"
            self.ElementEvent(self.currElem, self.currRawElem)
            self.currElem = None
            self.currRawElem = u''
        # Anything else is just some element in the current
        # packet wrapping up
        else:
            if len(self.currElem.children)==0:
                self.currRawElem = self.currRawElem + "/>"
            else:
                self.currRawElem = self.currRawElem + "</"+ self.currElem.name+">"
            self.currElem = self.currElem.parent

    def _onCdata(self, data):
        if self.currElem != None:
            if len(self.currElem.children)==0:
                self.currRawElem = self.currRawElem + ">" + domish.escapeToXml(data)
                #self.currRawElem = self.currRawElem + ">" + data
            else:
                self.currRawElem = self.currRawElem  + domish.escapeToXml(data)
                #self.currRawElem = self.currRawElem  + data

            self.currElem.addContent(data)

    def _onStartNamespace(self, prefix, uri):
        # If this is the default namespace, put
        # it on the stack
        if prefix is None:
            self.defaultNsStack.append(uri)
        else:
            self.localPrefixes[prefix] = uri

    def _onEndNamespace(self, prefix):
        # Remove last element on the stack
        if prefix is None:
            self.defaultNsStack.pop()

def elementStream():
    """ Preferred method to construct an ElementStream

    Uses Expat-based stream if available, and falls back to Sux if necessary.
    """
    try:
        es = HttpbElementStream()
        return es
    except ImportError:
        if domish.SuxElementStream is None:
            raise Exception("No parsers available :(")
        es = domish.SuxElementStream()
        return es

# make httpb body class, similar to xmlrpclib
#
class HttpbParse:
    """
    An xml parser for parsing the body elements.
    """
    def __init__(self, use_t=False):
        """
        Call reset to initialize object
        """
        self.use_t = use_t # use domish element stream
        self._reset()


    def parse(self, buf):
        """
        Parse incoming xml and return the body and its children in a list
        """
        self.stream.parse(buf)

        # return the doc element and its children in a list
        return self.body, self.xmpp_elements

    def serialize(self, obj):
        """
        Turn object into a string type
        """
        if isinstance(obj, domish.Element):
            obj = obj.toXml()
        return obj

    def onDocumentStart(self, rootelem):
        """
        The body document has started.

        This should be a body.
        """
        if rootelem.name == 'body':
            self.body = rootelem

    def onElement(self, element, raw_element = None):
        """
        A child element has been found.
        """
        if isinstance(element, domish.Element):
            if raw_element:
                self.xmpp_elements.append(raw_element)
            else:
                self.xmpp_elements.append(element)
        else:
            pass

    def _reset(self):
        """
        Setup the parser
        """
        if not self.use_t:
            self.stream = elementStream()
        else:
            self.stream = domish.elementStream()

        self.stream.DocumentStartEvent = self.onDocumentStart
        self.stream.ElementEvent = self.onElement
        self.stream.DocumentEndEvent = self.onDocumentEnd
        self.body = ""
        self.xmpp_elements = []


    def onDocumentEnd(self):
        """
        Body End
        """
        pass

class IHttpbService(Interface):
    """
    Interface for http binding class
    """
    def __init__(self, verbose):
        """ """

    def startSession(self, body):
        """ Start a punjab jabber session """

    def endSession(self, session):
        """ end a punjab jabber session """

    def onExpire(self, session_id):
        """ preform actions based on when the jabber connection expires """

    def parseBody(self, body):
        """ parse a body element """


    def error(self, error):
        """ send a body error element """


    def inSession(self, body):
        """ """

    def getXmppElements(self, body, session):
        """ """



class IHttpbFactory(Interface):
    """
    Factory class for generating binding sessions.
    """
    def startSession(self):
        """ Start a punjab jabber session """

    def endSession(self, session):
        """ end a punjab jabber session """

    def parseBody(self, body):
        """ parse an body element """

    def buildProtocol(self, addr):
        """Return a protocol """



class Httpb(resource.Resource):
    """
    Http resource to handle BOSH requests.
    """
    isLeaf = True
    def __init__(self, service, v = 0):
        """Initialize.
        """
        resource.Resource.__init__(self)
        self.service  = service
        self.hp       = None
        self.children = {}
        self.client   = 0
        self.verbose  = v

        self.polling = self.service.polling or 15

    def render_OPTIONS(self, request):
        request.setHeader('Access-Control-Allow-Origin', '*')
        request.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        request.setHeader('Access-Control-Allow-Headers', 'Content-Type')
        request.setHeader('Access-Control-Max-Age', '86400')
        return ""

    def render_GET(self, request):
        """
        GET is not used, print docs.
        """
        request.setHeader('Access-Control-Allow-Origin', '*')
        request.setHeader('Access-Control-Allow-Headers', 'Content-Type')
        return """<html>
                 <body>
                 <a href='http://www.xmpp.org/extensions/xep-0124.html'>XEP-0124</a> - BOSH
                 </body>
               </html>"""

    def render_POST(self, request):
        """
        Parse received xml
        """
        request.setHeader('Access-Control-Allow-Origin', '*')
        request.setHeader('Access-Control-Allow-Headers', 'Content-Type')
        request.content.seek(0, 0)
        if self.service.v:
            log.msg('HEADERS %s:' % (str(time.time()),))
            log.msg(request.received_headers)
            log.msg("HTTPB POST : ")
            log.msg(str(request.content.read()))
            request.content.seek(0, 0)

        self.hp       = HttpbParse()
        try:
            body_tag, xmpp_elements = self.hp.parse(request.content.read())
            self.hp._reset()

            if getattr(body_tag, 'name', '') != "body":
                if self.service.v:
                    log.msg('Client sent bad POST data')
                self.send_http_error(400, request)
                return server.NOT_DONE_YET
        except domish.ParserError:
            log.msg('ERROR: Xml Parse Error')
            log.err()
            self.hp._reset()
            self.send_http_error(400, request)
            return server.NOT_DONE_YET
        except:
            log.err()
            # reset parser, just in case
            self.hp._reset()
            self.send_http_error(400, request)
            return server.NOT_DONE_YET
        else:
            if self.service.inSession(body_tag):
                # sid is an existing session
                if body_tag.getAttribute('rid'):
                    request.rid = body_tag['rid']
                    if self.service.v:
                        log.msg(request.rid)

                s, d = self.service.parseBody(body_tag, xmpp_elements)
                d.addCallback(self.return_httpb, s, request)
            elif body_tag.hasAttribute('sid'):
                if self.service.v:
                    log.msg("no sid is found but the body element has a 'sid' attribute")
                # This is an error, no sid is found but the body element has a 'sid' attribute
                self.send_http_error(404, request)
                return server.NOT_DONE_YET
            else:
                # start session
                s, d = self.service.startSession(body_tag, xmpp_elements)
                d.addCallback(self.return_session, s, request)

            # Add an error back for returned errors
            d.addErrback(self.return_error, request)
        return server.NOT_DONE_YET


    def return_session(self, data, session, request):
        # create body
        if session.xmlstream is None:
            self.send_http_error(200, request, 'remote-connection-failed',
                                 'terminate')
            return server.NOT_DONE_YET

        b = domish.Element((NS_BIND, "body"), localPrefixes = {'xmpp' : NS_XMPP, 'stream' : NS_FEATURES })
        # if we don't have an authid, we have to fail
        if session.authid != 0:
            b['authid'] = session.authid
        else:
            self.send_http_error(500, request, 'internal-server-error',
                                 'terminate')
            return server.NOT_DONE_YET

        b['sid']  = session.sid
        b['wait'] = str(session.wait)
        if session.secure == 0:
            b['secure'] = 'false'
        else:
            b['secure'] = 'true'

        b['inactivity'] = str(session.inactivity)
        b['polling'] = str(self.polling)
        b['requests'] = str(session.hold + 1)
        b['window'] = str(session.window)
        b[(NS_XMPP, 'version')] = '1.0'

        punjab.uriCheck(b, NS_BIND)
        if session.attrs.has_key('content'):
            b['content'] = session.attrs['content']

        # We need to send features
        while len(data) > 0:
            felem = data.pop(0)
            if isinstance(felem, domish.Element):
                b.addChild(felem)
            else:
                b.addRawXml(felem)

        self.return_body(request, b)

    def return_httpb(self, data, session, request):
        # create body
        b = domish.Element((NS_BIND, "body"))
        punjab.uriCheck(b, NS_BIND)
        session.touch()
        if getattr(session,'terminated', False):
            b['type']      = 'terminate'
        if data:
            b.children += data

        self.return_body(request, b, session.charset)


    def return_error(self, e, request):
        echildren = []
        try:
            # TODO - clean this up and make errors better
            if getattr(e.value,'stanza_error',None):
                ec = getattr(e.value, 'children', None)
                if ec:
                    echildren = ec

                self.send_http_error(error.conditions[str(e.value.stanza_error)]['code'],
                                     request,
                                     condition = str(e.value.stanza_error),
                                     typ = error.conditions[str(e.value.stanza_error)]['type'],
                                     children=echildren)

                return  server.NOT_DONE_YET
            elif e.value:
                self.send_http_error(error.conditions[str(e.value)]['code'],
                                     request,
                                     str(e.value),
                                     error.conditions[str(e.value)]['type'])
                return  server.NOT_DONE_YET
            else:
                self.send_http_error(500, request, 'internal-server-error', 'error', e)
        except:
            log.err()
            pass


    def return_body(self, request, b, charset="utf-8"):
        request.setResponseCode(200)
        bxml = b.toXml(prefixes=ns.XMPP_PREFIXES.copy()).encode(charset,'replace')

        request.setHeader('content-type', 'text/xml')
        request.setHeader('content-length', len(bxml))
        if self.service.v:
            log.msg('\n\nRETURN HTTPB %s:' % (str(time.time()),))
            log.msg(bxml)
            if getattr(request, 'rid', None):
                log.msg(request.rid)
        request.write(bxml)
        request.finish()

    def send_http_error(self, code, request, condition = 'undefined-condition', typ = 'terminate', data = '', charset = 'utf-8', children=None):
        request.setResponseCode(int(code))
        xml_prefixes = ns.XMPP_PREFIXES.copy()

        b = domish.Element((NS_BIND, "body"))
        if condition:
            b['condition'] = str(condition)
        else:
            b['condition'] = 'undefined-condition'

        if typ:
            b['type']      = str(typ)
        else:
            b['type']      = 'terminate'
        punjab.uriCheck(b, NS_BIND)
        bxml = b.toXml(prefixes=xml_prefixes).encode(charset, 'replace')

        if children:
            b.children += children

        if self.service.v:
            log.msg('HTTPB Error %d' %(int(code),))

        if int(code) != 400 and int(code) != 404 and int(code) != 403:
            if data != '':
                if condition == 'see-other-uri':
                    b.addElement('uri', None, content = str(data))
                else:
                    t = b.addElement('text', content = str(data))
                    t['xmlns'] = 'urn:ietf:params:xml:ns:xmpp-streams'

            bxml = b.toXml(prefixes=xml_prefixes).encode(charset, 'replace')
            if self.service.v:
                log.msg('HTTPB Return Error: ' + str(code) + ' -> ' + bxml)
            request.setHeader("content-type", "text/xml")
            request.setHeader("content-length", len(bxml))
            request.write(bxml)
        else:
            request.setHeader("content-length", "0")
        request.finish()


components.registerAdapter(Httpb, IHttpbService, resource.IResource)


class HttpbService(punjab.Service):

    implements(IHttpbService)

    white_list = []
    black_list = []

    def __init__(self,
                 verbose = 0, polling = 15,
                 use_raw = False, bindAddress=None,
                 session_creator = None):
        if session_creator is not None:
            self.make_session = session_creator
        else:
            self.make_session = make_session
        self.v  = verbose
        self.sessions = {}
        self.polling = polling
        # self.expired  = {}
        self.use_raw  = use_raw

        # run a looping call to do pollTimeouts on sessions
        self.poll_timeouts = task.LoopingCall(self._doPollTimeOuts)

        self.poll_timeouts.start(3) # run every 3 seconds

        self.bindAddress=bindAddress

    def _doPollTimeOuts(self):
        """
        Call poll time outs on sessions that have waited too long.
        """
        time_now = time.time() + 2.9 # need a number to offset the poll timeouts
        for session in self.sessions.itervalues():
            if len(session.waiting_requests)>0:
                for wr in session.waiting_requests:
                    if time_now - wr.wait_start >= wr.timeout:
                        wr.delayedcall(wr.deferred)


    def startSession(self, body, xmpp_elements):
        """ Start a punjab jabber session """

        # look for rid
        if not body.hasAttribute('rid') or body['rid']=='':
            if self.v:
                log.msg('start session called but we had a rid')
            return None, defer.fail(error.NotFound)

        # look for to
        if not body.hasAttribute('to') or body['to']=='':
            return None, defer.fail(error.BadRequest)

        # The target host must match an entry in the white_list. white_list
        # entries beginning with periods will allow subdomains.
        #
        # e.g.: A 'to' of 'foo.example.com' would not match 'example.com' but
        #       would match '.example.com' or '*example.com' or '*.example.com'
        #
        # Or target must not be in black_list. If neither white_list or
        # black_list is present, target is always allowed.
        if self.white_list:
            valid_host = False
            for domain in self.white_list:
                if body['to'] == domain or \
                        (domain[0] == '*' and domain[1] == '.' and\
                             body['to'].endswith(domain[2:])) or \
                        (domain[0] == '*' and \
                             body['to'].endswith(domain[1:])) or \
                        (domain[0] == '.' and \
                             body['to'].endswith(domain[1:])):
                    valid_host = True
                    break
            if not valid_host:
                return None, defer.fail(error.BadRequest)

        if self.black_list:
            valid_host = True
            for domain in self.black_list:
                if body['to'] == domain or \
                        (domain[0] == '*' and domain[1] == '.' and
                         body['to'].endswith(domain[2:])) or \
                        (domain[0] == '*' and \
                         body['to'].endswith(domain[1:])) or \
                        (domain[0] == '.' and \
                         body['to'].endswith(domain[1:])):
                    valid_host = False
                    break
            if not valid_host:
                return None, defer.fail(error.BadRequest)

        # look for wait
        if not body.hasAttribute('wait') or body['wait']=='':
            body['wait'] = 3

        # look for lang
        lang = None
        if not body.hasAttribute("xml:lang") or body['xml:lang']=='':
            for k in body.attributes:
                if isinstance(k, tuple):
                    if str(k[1])=='lang' and body.getAttribute(k) !='':
                        lang = body.getAttribute(k)
        if lang:
            body['lang'] = lang
        if not body.hasAttribute('inactivity'):
            body['inactivity'] = 60
        return self.make_session(self, body.attributes)

    def stopService(self):
        """Perform shutdown procedures."""
        if self.v:
            log.msg("Stopping HTTPB service.")
        self.terminateSessions()
        return defer.succeed(True)

    def terminateSessions(self):
        """Terminate all active sessions."""
        if self.v:
            log.msg('Terminating %d BOSH sessions.' % len(self.sessions))
        for s in self.sessions.values():
            s.terminate()

    def parseBody(self, body, xmpp_elements):
        try:
            # grab session
            if body.hasAttribute('sid'):
                sid = str(body['sid'])
            else:
                if self.v:
                    log.msg('Session ID not found')
                return None, defer.fail(error.NotFound)
            if self.inSession(body):
                s = self.sessions[sid]
                s.touch() # any connection should be a renew on wait
            else:
                if self.v:
                    log.msg('session does not exist?')
                return None, defer.fail(error.NotFound)

            if bool(s.key) != body.hasAttribute('key'):
                # This session is keyed, but there's no key in this packet; or there's
                # a key in this packet, but the session isn't keyed.
                return s, defer.fail(error.Error('item-not-found'))

            # If this session is keyed, validate the next key.
            if s.key:
                key = hashlib.sha1(body['key']).hexdigest()
                next_key = body['key']
                if key != s.key:
                    if self.v:
                        log.msg('Error in key')
                    return s, defer.fail(error.Error('item-not-found'))
                s.key = next_key

            # If there's a newkey in this packet, save it.  Do this after validating the
            # previous key.
            if body.hasAttribute('newkey'):
                s.key = body['newkey']


            # need to check if this is a valid rid (within tolerance)
            if body.hasAttribute('rid') and body['rid']!='':
                if s.cache_data.has_key(int(body['rid'])):
                    s.touch()
                    # implements issue 32 and returns the data returned on a dropped connection
                    return s, defer.succeed(s.cache_data[int(body['rid'])])
                if abs(int(body['rid']) - int(s.rid)) > s.window:
                    if self.v:
                        log.msg('This rid is invalid %s %s ' % (str(body['rid']), str(s.rid),))
                    return  s, defer.fail(error.NotFound)
            else:
                if self.v:
                    log.msg('There is no rid on this request')
                return  s, defer.fail(error.NotFound)

            return s, self._parse(s, body, xmpp_elements)

        except:
            log.err()
            return  s, defer.fail(error.InternalServerError)


    def onExpire(self, session_id):
        """ preform actions based on when the jabber connection expires """
        if self.v:
            log.msg('expire (%s)' % (str(session_id),))
            log.msg(len(self.sessions.keys()))

    def _parse(self, session, body_tag, xmpp_elements):
        # increment the request counter
        session.rid  = session.rid + 1

        if getattr(session, 'stream_error', None) != None:
            # The server previously sent us a stream:error, and has probably closed
            # the connection by now.  Forward the error to the client and terminate
            # the session.
            d = defer.Deferred()
            d.errback(session.stream_error)
            session.elems = []
            session.terminate()
            return d

        # Send received elements from the client to the server.  Do this even for
        # type='terminate'.
        for el in xmpp_elements:
            if isinstance(el, domish.Element):
                # something is wrong here, need to figure out what
                # the xmlns will be lost if this is not done
                # punjab.uriCheck(el,NS_BIND)
                # if el.uri and el.uri != NS_BIND:
                #    el['xmlns'] = el.uri
                # TODO - get rid of this when we stop supporting old versions
                #        of twisted.words
                if el.uri == NS_BIND:
                    el.uri = None
                if el.defaultUri == NS_BIND:
                    el.defaultUri = None

            session.sendRawXml(el)

        if body_tag.hasAttribute('type') and \
           body_tag['type'] == 'terminate':
            return session.terminate()

        # normal request
        return session.poll(None, rid = int(body_tag['rid']))

    def _returnIq(self, cur_session, d, iq):
        """
        A callback from auth iqs
        """
        return cur_session.poll(d)

    def _cbIq(self, iq, cur_session, d):
        """
        A callback from auth iqs
        """

        # session.elems.append(iq)
        return cur_session.poll(d)

    def inSession(self, body):
        """ """
        if body.hasAttribute('sid'):
            if self.sessions.has_key(body['sid']):
                return True
        return False

    def getXmppElements(self, b, session):
        """
        Get waiting xmpp elements
        """
        for i, obj in enumerate(session.msgs):
            m = session.msgs.pop(0)
            b.addChild(m)
        for i, obj in enumerate(session.prs):
            p = session.prs.pop(0)
            b.addChild(p)
        for i, obj in enumerate(session.iqs):
            iq = session.iqs.pop(0)
            b.addChild(iq)

        return b

    def endSession(self, cur_session):
        """ end a punjab jabber session """
        d = cur_session.terminate()
        return d


########NEW FILE########
__FILENAME__ = httpb_client
import hashlib
import random
import urlparse
import os

from twisted.internet import defer, reactor, protocol
from twisted.python import log, failure
try:
    from twisted.words.xish import domish, utility
except:
    from twisted.xish import domish, utility
from twisted.web import http

from twisted.words.protocols.jabber import xmlstream, client




from punjab.httpb import HttpbParse # maybe use something else to seperate from punjab

TLS_XMLNS = 'urn:ietf:params:xml:ns:xmpp-tls'
SASL_XMLNS = 'urn:ietf:params:xml:ns:xmpp-sasl'
BIND_XMLNS = 'urn:ietf:params:xml:ns:xmpp-bind'
SESSION_XMLNS = 'urn:ietf:params:xml:ns:xmpp-session'

NS_HTTP_BIND = "http://jabber.org/protocol/httpbind"

class Error(Exception):
    stanza_error = ''
    punjab_error = ''
    msg          = ''
    def __init__(self, msg = None):
        if msg:
            self.stanza_error = msg
            self.punjab_error = msg
            self.msg          = msg

    def __str__(self):
        return self.stanza_error


class RemoteConnectionFailed(Error):
    msg = 'remote-connection-failed'
    stanza_error = 'remote-connection-failed'


class NodeNotFound(Error):
    msg = '404 not found'

class NotAuthorized(Error):
    pass

class NotImplemented(Error):
    pass



# Exceptions raised by the client.
class HTTPBException(Exception): pass
class HTTPBNetworkTerminated(HTTPBException):
    def __init__(self, body_tag, elements):
        self.body_tag = body_tag
        self.elements = elements

    def __str__(self):
        return self.body_tag.toXml()



class XMPPAuthenticator(client.XMPPAuthenticator):
    """
    Authenticate against an xmpp server using BOSH
    """

class QueryProtocol(http.HTTPClient):
    noisy = False
    def connectionMade(self):
        self.factory.sendConnected(self)
        self.sendBody(self.factory.cb)

    def sendCommand(self, command, path):
        self.transport.write('%s %s HTTP/1.1\r\n' % (command, path))

    def sendBody(self, b, close = 0):
        if isinstance(b, domish.Element):
            bdata = b.toXml().encode('utf-8')
        else:
            bdata = b

        self.sendCommand('POST', self.factory.url)
        self.sendHeader('User-Agent', 'Twisted/XEP-0124')
        self.sendHeader('Host', self.factory.host)
        self.sendHeader('Content-type', 'text/xml')
        self.sendHeader('Content-length', str(len(bdata)))
        self.endHeaders()
        self.transport.write(bdata)

    def handleStatus(self, version, status, message):
        if status != '200':
            self.factory.badStatus(status, message)

    def handleResponse(self, contents):
        self.factory.parseResponse(contents, self)

    def lineReceived(self, line):
        if self.firstLine:
            self.firstLine = 0
            l = line.split(None, 2)
            version = l[0]
            status = l[1]
            try:
                message = l[2]
            except IndexError:
                # sometimes there is no message
                message = ""
            self.handleStatus(version, status, message)
            return
        if line:
            key, val = line.split(':', 1)
            val = val.lstrip()
            self.handleHeader(key, val)
            if key.lower() == 'content-length':
                self.length = int(val)
        else:
            self.__buffer = []
            self.handleEndHeaders()
            self.setRawMode()

    def handleResponseEnd(self):
        self.firstLine = 1
        if self.__buffer != None:
            b = ''.join(self.__buffer)

            self.__buffer = None
            self.handleResponse(b)

    def handleResponsePart(self, data):
        self.__buffer.append(data)


    def connectionLost(self, reason):
        #log.msg(dir(reason))
        #log.msg(reason)
        pass


class QueryFactory(protocol.ClientFactory):
    """ a factory to create http client connections.
    """
    deferred = None
    noisy = False
    protocol = QueryProtocol
    def __init__(self, url, host, b):
        self.url, self.host = url, host
        self.deferred = defer.Deferred()
        self.cb = b

    def send(self,b):
        self.deferred = defer.Deferred()

        self.client.sendBody(b)

        return self.deferred

    def parseResponse(self, contents, protocol):
        self.client = protocol
        hp = HttpbParse(True)

        try:
            body_tag,elements = hp.parse(contents)
        except:
            raise
        else:
            if body_tag.hasAttribute('type') and body_tag['type'] == 'terminate':
                error = failure.Failure(HTTPBNetworkTerminated(body_tag, elements))
                if self.deferred.called:
                    return defer.fail(error)
                else:
                    self.deferred.errback(error)
                return
            if self.deferred.called:
                return defer.succeed((body_tag,elements))
            else:
                self.deferred.callback((body_tag,elements))


    def sendConnected(self, q):
        self.q = q



    def clientConnectionLost(self, _, reason):
        try:
            self.client = None
            if not self.deferred.called:
                self.deferred.errback(reason)

        except:
            return reason

    clientConnectionFailed = clientConnectionLost

    def badStatus(self, status, message):
        if not self.deferred.called:
            self.deferred.errback(ValueError(status, message))




class Keys:
    """Generate keys according to XEP-0124 #15 "Protecting Insecure Sessions"."""
    def __init__(self):
        self.k = []

    def _set_keys(self):
        seed = os.urandom(1024)
        num_keys = random.randint(55,255)
        self.k = [hashlib.sha1(seed).hexdigest()]
        for i in xrange(num_keys-1):
            self.k.append(hashlib.sha1(self.k[-1]).hexdigest())

    def getKey(self):
        """
        Return (key, newkey), where key is the next key to use and newkey is the next
        newkey value to use.  If key or newkey are None, the next request doesn't require
        that value.
        """
        if not self.k:
            # This is the first call, so generate keys and only return new_key.
            self._set_keys()
            return None, self.k.pop()

        key = self.k.pop()

        if not self.k:
            # We're out of keys.  Regenerate keys and re-key.
            self._set_keys()
            return key, self.k.pop()

        return key, None


class Proxy:
    """A Proxy for making HTTP Binding calls.

    Pass the URL of the remote HTTP Binding server to the constructor.

    """

    def __init__(self, url):
        """
        Parse the given url and find the host and port to connect to.
        """
        parts = urlparse.urlparse(url)
        self.url = urlparse.urlunparse(('', '')+parts[2:])
        if self.url == "":
            self.url = "/"
        if ':' in parts[1]:
            self.host, self.port = parts[1].split(':')
            self.port = int(self.port)
        else:
            self.host, self.port = parts[1], None
        self.secure = parts[0] == 'https'

    def connect(self, b):
        """
        Make a connection to the web server and send along the data.
        """
        self.factory = QueryFactory(self.url, self.host, b)

        if self.secure:
            from twisted.internet import ssl
            self.rid = reactor.connectSSL(self.host, self.port or 443,
                                          self.factory, ssl.ClientContextFactory())
        else:
            self.rid = reactor.connectTCP(self.host, self.port or 80, self.factory)


        return self.factory.deferred


    def send(self,b):
        """ Send data to the web server. """

        # if keepalive is off we need a new query factory
        # TODO - put a check to reuse the factory, right now we open a new one.
        d = self.connect(b)
        return d

class HTTPBClientConnector:
    """
    A HTTP Binding client connector.
    """
    def __init__(self, url):
        self.url = url

    def connect(self, factory):
        self.proxy = Proxy(self.url)
        self.xs = factory.buildProtocol(self.proxy.host)
        self.xs.proxy = self.proxy
        self.xs.connectionMade()


    def disconnect(self):
        self.xs.connectionLost('disconnect')
        self.xs = None


class HTTPBindingStream(xmlstream.XmlStream):
    """
    HTTP Binding wrapper that acts like xmlstream

    """

    def __init__(self, authenticator):
        xmlstream.XmlStream.__init__(self, authenticator)
        self.base_url = '/xmpp-httpbind/'
        self.host = 'dev.chesspark.com'
        self.mechanism = 'PLAIN'
        # request id
        self.rid = random.randint(0, 10000000)
        # session id
        self.session_id = 0
        # keys
        self.keys = Keys()
        self.initialized = False
        self.requests = []

    def _cbConnect(self, result):
        r,e = result
        ms = ''
        self.initialized = True
        # log.msg('======================================== cbConnect ====================')
        self.session_id = r['sid']
        self.authid = r['authid']
        self.namespace = self.authenticator.namespace
        self.otherHost = self.authenticator.otherHost
        self.dispatch(self, xmlstream.STREAM_START_EVENT)
        # Setup observer for stream errors
        self.addOnetimeObserver("/error[@xmlns='%s']" % xmlstream.NS_STREAMS,
                                self.onStreamError)

        if len(e)>0 and e[0].name == 'features':
            # log.msg('============================= on features ==============================')
            self.onFeatures(e[0])
        else:
            self.authenticator.streamStarted()

    def _ebError(self, e):
        log.err(e.printTraceback())


    def _initializeStream(self):
        """ Initialize binding session.

        Just need to create a session once, this can be done elsewhere, but here will do for now.
        """

        if not self.initialized:
            b = domish.Element((NS_HTTP_BIND,'body'))

            b['content']  = 'text/xml; charset=utf-8'
            b['hold']     = '1'
            b['rid']      = str(self.rid)
            b['to']       = self.authenticator.jid.host
            b['wait']     = '60'
            b['xml:lang'] = 'en'
            # FIXME - there is an issue with the keys
            # b = self.key(b)

            # Connection test
            d = self.proxy.connect(b)
            d.addCallback(self._cbConnect)
            d.addErrback(self._ebError)
            return d
        else:
            self.authenticator.initializeStream()


    def key(self,b):
        key, newkey = self.keys.getKey()

        if key:
            b['key'] = key
        if newkey:
            b['newkey'] = newkey

    def _cbSend(self, result):
        body, elements = result
        if body.hasAttribute('type') and body['type'] == 'terminate':
            reactor.close()
        self.requests.pop(0)
        for e in elements:
            if self.rawDataInFn:
                self.rawDataInFn(str(e.toXml()))
            if e.name == 'features':
                self.onFeatures(e)
            else:
                self.onElement(e)
        # if no elements lets send out another poll
        if len(self.requests)==0:
            self.send()


    def send(self, obj = None):
        if self.session_id == 0:
            return defer.succeed(False)

        b = domish.Element((NS_HTTP_BIND,"body"))
        b['content']  = 'text/xml; charset=utf-8'
        self.rid = self.rid + 1
        b['rid']      = str(self.rid)
        b['sid']      = str(self.session_id)
        b['xml:lang'] = 'en'

        if obj is not None:
            if domish.IElement.providedBy(obj):
                if self.rawDataOutFn:
                    self.rawDataOutFn(str(obj.toXml()))
                b.addChild(obj)
        #b = self.key(b)
        self.requests.append(b)
        d = self.proxy.send(b)
        d.addCallback(self._cbSend)
        return d


class HTTPBindingStreamFactory(xmlstream.XmlStreamFactory):
    """
    Factory for HTTPBindingStream protocol objects.
    """

    def buildProtocol(self, _):
        self.resetDelay()
        xs = HTTPBindingStream(self.authenticator)
        xs.factory = self
        for event, fn in self.bootstraps: xs.addObserver(event, fn)
        return xs


########NEW FILE########
__FILENAME__ = jabber
# punjab's jabber client
from twisted.internet import reactor, error
from twisted.words.protocols.jabber import client, jid
from twisted.python import log
from copy import deepcopy

from twisted.words import version
hasNewTwisted = version.major >= 8
if version.major == 0 and version.minor < 5: raise Exception, "Unsupported Version of Twisted Words"

from twisted.words.xish import domish
from twisted.words.protocols.jabber import xmlstream


INVALID_USER_EVENT    = "//event/client/basicauth/invaliduser"
AUTH_FAILED_EVENT     = "//event/client/basicauth/authfailed"
REGISTER_FAILED_EVENT = "//event/client/basicauth/registerfailed"

# event funtions

from punjab.xmpp.ns import XMPP_PREFIXES

def basic_connect(jabberid, secret, host, port, cb, v=0):
    myJid = jid.JID(jabberid)
    factory = client.basicClientFactory(myJid,secret)
    factory.v = v
    factory.addBootstrap('//event/stream/authd',cb)
    reactor.connectTCP(host,port,factory)
    return factory

def basic_disconnect(f, xmlstream):
    sh = "</stream:stream>"
    xmlstream.send(sh)
    f.stopTrying()
    xmlstream = None


class JabberClientFactory(xmlstream.XmlStreamFactory):
    def __init__(self, host, v=0):
        """ Initialize
        """
        p = self.authenticator = PunjabAuthenticator(host)
        xmlstream.XmlStreamFactory.__init__(self, p)

        self.pending = {}
        self.maxRetries = 2
        self.host = host
        self.jid  = ""
        self.raw_buffer = ""

        if v!=0:
            self.v = v
            self.rawDataOutFn = self.rawDataOut
            self.rawDataInFn = self.rawDataIn

    def clientConnectionFailed(self, connector, reason, d = None):
        if self.continueTrying:
            self.connector = connector
            if not reason.check(error.UserError):
                self.retry()
            if self.maxRetries and (self.retries > self.maxRetries):
                if d:
                    d.errback(reason)


    def rawDataIn(self, buf):
        log.msg("RECV: %s" % unicode(buf, 'utf-8').encode('ascii', 'replace'))


    def rawDataOut(self, buf):
        log.msg("SEND: %s" % unicode(buf, 'utf-8').encode('ascii', 'replace'))


class PunjabAuthenticator(xmlstream.ConnectAuthenticator):
    namespace = "jabber:client"
    version   = '1.0'
    useTls    = 1
    def connectionMade(self):
        host = self.otherHost
        self.streamHost = host

        self.xmlstream.useTls = self.useTls
        self.xmlstream.namespace = self.namespace
        self.xmlstream.otherHost = self.otherHost
        if hasNewTwisted:
            self.xmlstream.otherEntity = jid.internJID(self.otherHost)
        self.xmlstream.prefixes = deepcopy(XMPP_PREFIXES)
        self.xmlstream.sendHeader()

    def streamStarted(self, rootelem = None):
        if hasNewTwisted: # This is here for backwards compatibility
            xmlstream.ConnectAuthenticator.streamStarted(self, rootelem)
        else:
            xmlstream.ConnectAuthenticator.streamStarted(self)
        if rootelem is None:
            self.xversion = 3
            return

        self.xversion = 0
        if rootelem.hasAttribute('version'):
            self.version = rootelem['version']
        else:
            self.version = 0.0

    def associateWithStream(self, xs):
        xmlstream.ConnectAuthenticator.associateWithStream(self, xs)

        inits = [ (xmlstream.TLSInitiatingInitializer, False),
                  # (IQAuthInitializer, True),
                ]

        for initClass, required in inits:
            init = initClass(xs)
            init.required = required
            xs.initializers.append(init)

    def _reset(self):
        # need this to be in xmlstream
        self.xmlstream.stream = domish.elementStream()
        self.xmlstream.stream.DocumentStartEvent = self.xmlstream.onDocumentStart
        self.xmlstream.stream.ElementEvent = self.xmlstream.onElement
        self.xmlstream.stream.DocumentEndEvent = self.xmlstream.onDocumentEnd
        self.xmlstream.prefixes = deepcopy(XMPP_PREFIXES)
        # Generate stream header

        if self.version != 0.0:
            sh = "<stream:stream xmlns='%s' xmlns:stream='http://etherx.jabber.org/streams' version='%s' to='%s'>" % \
                 (self.namespace,self.version, self.streamHost.encode('utf-8'))

            self.xmlstream.send(str(sh))

    def sendAuth(self, jid, passwd, callback, errback = None):
        self.jid    = jid
        self.passwd = passwd
        if errback:
            self.xmlstream.addObserver(INVALID_USER_EVENT,errback)
            self.xmlstream.addObserver(AUTH_FAILED_EVENT,errback)
        if self.version != '1.0':
            iq = client.IQ(self.xmlstream, "get")
            iq.addElement(("jabber:iq:auth", "query"))
            iq.query.addElement("username", content = jid.user)
            iq.addCallback(callback)
            iq.send()


    def authQueryResultEvent(self, iq, callback):
        if iq["type"] == "result":
            # Construct auth request
            iq = client.IQ(self.xmlstream, "set")
            iq.addElement(("jabber:iq:auth", "query"))
            iq.query.addElement("username", content = self.jid.user)
            iq.query.addElement("resource", content = self.jid.resource)

            # Prefer digest over plaintext
            if client.DigestAuthQry.matches(iq):
                digest = xmlstream.hashPassword(self.xmlstream.sid, self.passwd)
                iq.query.addElement("digest", content = digest)
            else:
                iq.query.addElement("password", content = self.passwd)

            iq.addCallback(callback)
            iq.send()
        else:
            # Check for 401 -- Invalid user
            if iq.error["code"] == "401":
                self.xmlstream.dispatch(iq, INVALID_USER_EVENT)
            else:
                self.xmlstream.dispatch(iq, AUTH_FAILED_EVENT)

########NEW FILE########
__FILENAME__ = patches
# XXX: All monkey patches should be sent upstream and eventually removed.

import functools

def patch(cls, attr):
    """Patch the function named attr in the object cls with the decorated function."""
    orig_func = getattr(cls, attr)
    @functools.wraps(orig_func)
    def decorator(func):
        def wrapped_func(*args, **kwargs):
            return func(orig_func, *args, **kwargs)
        setattr(cls, attr, wrapped_func)
        return orig_func
    return decorator

# Modify jabber.error.exceptionFromStreamError to include the XML element in
# the exception.
from twisted.words.protocols.jabber import error as jabber_error
@patch(jabber_error, "exceptionFromStreamError")
def exceptionFromStreamError(orig, element):
    exception = orig(element)
    exception.element = element
    return exception


########NEW FILE########
__FILENAME__ = session
"""
 session stuff for jabber connections

"""
from twisted.internet import defer,  reactor
from twisted.python import failure, log
from twisted.web import server
from twisted.names.srvconnect import SRVConnector

try:
    from twisted.words.xish import domish, xmlstream
    from twisted.words.protocols import jabber as jabber_protocol
except ImportError:
    from twisted.xish import domish, xmlstream


import traceback
import os
import warnings
from punjab import jabber
from punjab.xmpp import ns

import time
import error

try:
    from twisted.internet import ssl
except ImportError:
    ssl = None
if ssl and not ssl.supported:
    ssl = None
if not ssl:
    log.msg("SSL ERROR: You do not have ssl support this may cause problems with tls client connections.")



class XMPPClientConnector(SRVConnector):
    """
    A jabber connection to find srv records for xmpp client connections.
    """
    def __init__(self, client_reactor, domain, factory):
        """ Init """
        if isinstance(domain, unicode):
            warnings.warn(
                "Domain argument to XMPPClientConnector should be bytes, "
                "not unicode",
                stacklevel=2)
            domain = domain.encode('ascii')
        SRVConnector.__init__(self, client_reactor, 'xmpp-client', domain, factory)
        self.timeout = [1,3]

    def pickServer(self):
        """
        Pick a server and port to make the connection.
        """
        host, port = SRVConnector.pickServer(self)

        if port == 5223 and ssl:
            context = ssl.ClientContextFactory()
            context.method = ssl.SSL.SSLv23_METHOD

            self.connectFuncName = 'connectSSL'
            self.connectFuncArgs = (context,)
        return host, port

def make_session(pint, attrs, session_type='BOSH'):
    """
    pint  - punjab session interface class
    attrs - attributes sent from the body tag
    """

    s    = Session(pint, attrs)

    if pint.v:
        log.msg('================================== %s connect to %s:%s ==================================' % (str(time.time()),s.hostname,s.port))

    connect_srv = s.connect_srv
    if attrs.has_key('route'):
        connect_srv = False
    if s.hostname in ['localhost', '127.0.0.1']:
        connect_srv = False
    if not connect_srv:
        reactor.connectTCP(s.hostname, s.port, s, bindAddress=pint.bindAddress)
    else:
        connector = XMPPClientConnector(reactor, s.hostname, s)
        connector.connect()
    # timeout
    reactor.callLater(s.inactivity, s.checkExpired)

    pint.sessions[s.sid] = s

    return s, s.waiting_requests[0].deferred


class WaitingRequest(object):
    """A helper object for managing waiting requests."""

    def __init__(self, deferred, delayedcall, timeout = 30, startup = False, rid = None):
        """ """
        self.deferred    = deferred
        self.delayedcall = delayedcall
        self.startup     = startup
        self.timeout     = timeout
        self.wait_start  = time.time()
        self.rid         = rid

    def doCallback(self, data):
        """ """
        self.deferred.callback(data)

    def doErrback(self, data):
        """ """
        self.deferred.errback(data)


class Session(jabber.JabberClientFactory, server.Session):
    """ Jabber Client Session class for client XMPP connections. """
    def __init__(self, pint, attrs):
        """
        Initialize the session
        """
        if attrs.has_key('charset'):
            self.charset = str(attrs['charset'])
        else:
            self.charset = 'utf-8'

        self.to    = attrs['to']
        self.port  = 5222
        self.inactivity = 900
        if self.to != '' and self.to.find(":") != -1:
            # Check if port is in the 'to' string
            to, port = self.to.split(':')

            if port:
                self.to   = to
                self.port = int(port)
            else:
                self.port = 5222

        self.sid = "".join("%02x" % ord(i) for i in os.urandom(20))

        jabber.JabberClientFactory.__init__(self, self.to, pint.v)
        server.Session.__init__(self, pint, self.sid)
        self.pint  = pint

        self.attrs = attrs
        self.s     = None

        self.elems = []
        rid        = int(attrs['rid'])

        self.waiting_requests = []
        self.use_raw = attrs.get('raw', False)

        self.raw_buffer = u""
        self.xmpp_node  = ''
        self.success    = 0
        self.mechanisms = []
        self.xmlstream  = None
        self.features   = None
        self.session    = None

        self.cache_data = {}
        self.verbose    = self.pint.v
        self.noisy      = self.verbose

        self.version = attrs.get('version', 0.0)

        self.key = attrs.get('newkey')

        self.wait  = int(attrs.get('wait', 0))

        self.hold  = int(attrs.get('hold', 0))
        self.inactivity = int(attrs.get('inactivity', 900)) # default inactivity 15 mins

        if attrs.has_key('window'):
            self.window  = int(attrs['window'])
        else:
            self.window  = self.hold + 2

        if attrs.has_key('polling'):
            self.polling  = int(attrs['polling'])
        else:
            self.polling  = 0

        if attrs.has_key('port'):
            self.port = int(attrs['port'])

        if attrs.has_key('hostname'):
            self.hostname = attrs['hostname']
        else:
            self.hostname = self.to

        self.use_raw = getattr(pint, 'use_raw', False) # use raw buffers

        self.connect_srv = getattr(pint, 'connect_srv', True)

        self.secure = attrs.has_key('secure') and attrs['secure'] == 'true'
        self.authenticator.useTls = self.secure

        if attrs.has_key('route'):
            if attrs['route'].startswith("xmpp:"):
                self.route = attrs['route'][5:]
                if self.route.startswith("//"):
                    self.route = self.route[2:]

                # route format change, see http://www.xmpp.org/extensions/xep-0124.html#session-request
                rhostname, rport = self.route.split(":")
                self.port = int(rport)
                self.hostname = rhostname
                self.resource = ''
            else:
                raise error.Error('internal-server-error')


        self.authid      = 0
        self.rid         = rid + 1
        self.connected   = 0 # number of clients connected on this session

        self.notifyOnExpire(self.onExpire)
        self.stream_error = None
        if pint.v:
            log.msg('Session Created : %s %s' % (str(self.sid),str(time.time()), ))
        self.stream_error_called = False
        self.addBootstrap(xmlstream.STREAM_START_EVENT, self.streamStart)
        self.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.connectEvent)
        self.addBootstrap(xmlstream.STREAM_ERROR_EVENT, self.streamError)
        self.addBootstrap(xmlstream.STREAM_END_EVENT, self.connectError)

        # create the first waiting request
        d = defer.Deferred()
        timeout = 30
        rid = self.rid - 1
        self.appendWaitingRequest(d, rid,
                                  timeout=timeout,
                                  poll=self._startup_timeout,
                                  startup=True,
                                  )

    def rawDataIn(self, buf):
        """ Log incoming data on the xmlstream """
        if self.pint and self.pint.v:
            try:
                log.msg("SID: %s => RECV: %r" % (self.sid, buf,))
            except:
                log.err()
        if self.use_raw and self.authid:
            if type(buf) == type(''):
                buf = unicode(buf, 'utf-8')
            # add some raw data
            self.raw_buffer = self.raw_buffer + buf


    def rawDataOut(self, buf):
        """ Log outgoing data on the xmlstream """
        try:
            log.msg("SID: %s => SEND: %r" % (self.sid, buf,))
        except:
            log.err()

    def _wrPop(self, data, i=0):
        """Pop off a waiting requst, do callback, and cache request
        """
        wr = self.waiting_requests.pop(i)
        wr.doCallback(data)
        self._cacheData(wr.rid, data)

    def clearWaitingRequests(self, hold = 0):
        """clear number of requests given

           hold - number of requests to clear, default is all
        """
        while len(self.waiting_requests) > hold:
            self._wrPop([])

    def _wrError(self, err, i = 0):
        wr = self.waiting_requests.pop(i)
        wr.doErrback(err)


    def appendWaitingRequest(self, d, rid, timeout=None, poll=None, startup=False):
        """append waiting request
        """
        if timeout is None:
            timeout = self.wait
        if poll is None:
            poll = self._pollTimeout
        self.waiting_requests.append(
            WaitingRequest(d,
                           poll,
                           timeout = timeout,
                           rid = rid,
                           startup=startup))

    def returnWaitingRequests(self):
        """return a waiting request
        """
        while len(self.elems) > 0 and len(self.waiting_requests) > 0:
            data = self.elems
            self.elems = []
            self._wrPop(data)


    def onExpire(self):
        """ When the session expires call this. """
        if 'onExpire' in dir(self.pint):
            self.pint.onExpire(self.sid)
        if self.verbose and not getattr(self, 'terminated', False):
            log.msg('SESSION -> We have expired', self.sid, self.rid, self.waiting_requests)
        self.disconnect()

    def terminate(self):
        """Terminates the session."""
        self.wait = 0
        self.terminated = True
        if self.verbose:
            log.msg('SESSION -> Terminate')

        # if there are any elements hanging around and waiting
        # requests, send those off
        self.returnWaitingRequests()

        self.clearWaitingRequests()

        try:
            self.expire()
        except:
            self.onExpire()


        return defer.succeed(self.elems)

    def poll(self, d = None, rid = None):
        """Handles the responses to requests.

        This function is called for every request except session setup
        and session termination.  It handles the reply portion of the
        request by returning a deferred which will get called back
        when there is data or when the wait timeout expires.
        """
        # queue this request
        if d is None:
            d = defer.Deferred()
        if self.pint.error:
            d.addErrback(self.pint.error)
        if not rid:
            rid = self.rid - 1
        self.appendWaitingRequest(d, rid)
        # check if there is any data to send back to a request
        self.returnWaitingRequests()

        # make sure we aren't queueing too many requests
        self.clearWaitingRequests(self.hold)
        return d

    def _pollTimeout(self, d):
        """Handle request timeouts.

        Since the timeout function is called, we must return an empty
        reply as there is no data to send back.
        """
        # find the request that timed out and reply
        pop_eye = []
        for i in range(len(self.waiting_requests)):
            if self.waiting_requests[i].deferred == d:
                pop_eye.append(i)
                self.touch()

        for i in pop_eye:
            self._wrPop([],i)


    def _pollForId(self, d):
        if self.xmlstream.sid:
            self.authid = self.xmlstream.sid
        self._pollTimeout(d)



    def connectEvent(self, xs):

        self.version =  self.authenticator.version
        self.xmlstream = xs
        if self.pint.v:
            # add logging for verbose output

            self.xmlstream.rawDataOutFn = self.rawDataOut
        self.xmlstream.rawDataInFn = self.rawDataIn

        if self.version == '1.0':
            self.xmlstream.addObserver("/features", self.featuresHandler)



    def streamStart(self, xs):
        """
        A xmpp stream has started
        """
        # This is done to fix the stream id problem, I should submit a bug to twisted bugs

        try:

            self.authid    = self.xmlstream.sid

            if not self.attrs.has_key('no_events'):

                self.xmlstream.addOnetimeObserver("/auth", self.stanzaHandler)
                self.xmlstream.addOnetimeObserver("/response", self.stanzaHandler)
                self.xmlstream.addOnetimeObserver("/success", self._saslSuccess)
                self.xmlstream.addOnetimeObserver("/failure", self._saslError)

                self.xmlstream.addObserver("/iq/bind", self.bindHandler)
                self.xmlstream.addObserver("/bind", self.stanzaHandler)

                self.xmlstream.addObserver("/challenge", self.stanzaHandler)
                self.xmlstream.addObserver("/message",  self.stanzaHandler)
                self.xmlstream.addObserver("/iq",  self.stanzaHandler)
                self.xmlstream.addObserver("/presence",  self.stanzaHandler)
                # TODO - we should do something like this
                # self.xmlstream.addObserver("/*",  self.stanzaHandler)

        except:
            log.err(traceback.print_exc())
            self._wrError(error.Error("remote-connection-failed"))
            self.disconnect()


    def featuresHandler(self, f):
        """
        handle stream:features
        """
        f.prefixes   = ns.XMPP_PREFIXES.copy()

        #check for tls
        self.f = {}
        for feature in f.elements():
            self.f[(feature.uri, feature.name)] = feature

        starttls = (ns.TLS_XMLNS, 'starttls') in self.f

        initializers   = getattr(self.xmlstream, 'initializers', [])
        self.features = f
        self.xmlstream.features = f

        # There is a tls initializer added by us, if it is available we need to try it
        if len(initializers)>0 and starttls:
            self.secure = True

        if self.authid is None:
            self.authid = self.xmlstream.sid


        # If we get tls, then we should start tls, wait and then return
        # Here we wait, the tls initializer will start it
        if starttls and self.secure:
            if self.verbose:
                log.msg("Wait until starttls is completed.")
                log.msg(initializers)
            return
        self.elems.append(f)
        if len(self.waiting_requests) > 0:
            self.returnWaitingRequests()
            self.elems = [] # reset elems
            self.raw_buffer = u"" # reset raw buffer, features should not be in it

    def bindHandler(self, stz):
        """bind debugger for punjab, this is temporary! """
        if self.verbose:
            try:
                log.msg('BIND: %s %s' % (str(self.sid), str(stz.bind.jid)))
            except:
                log.err()
        if self.use_raw:
            self.raw_buffer = stz.toXml()

    def stanzaHandler(self, stz):
        """generic stanza handler for httpbind and httppoll"""
        stz.prefixes = ns.XMPP_PREFIXES
        if self.use_raw and self.authid:
            stz = domish.SerializedXML(self.raw_buffer)
            self.raw_buffer = u""

        self.elems.append(stz)
        if self.waiting_requests and len(self.waiting_requests) > 0:
            # if there are any waiting requests, give them all the
            # data so far, plus this new data
            self.returnWaitingRequests()


    def _startup_timeout(self, d):
        # this can be called if connection failed, or if we connected
        # but never got a stream features before the timeout
        if self.pint.v:
            log.msg('================================== %s %s startup timeout ==================================' % (str(self.sid), str(time.time()),))

        for i in range(len(self.waiting_requests)):
            if self.waiting_requests[i].deferred == d:
                # check if we really failed or not
                if self.authid:
                    self._wrPop(self.elems, i=i)
                else:
                    self._wrError(error.Error("remote-connection-failed"), i=i)


    def buildRemoteError(self, err_elem=None):
        # This may not be a stream error, such as an XML parsing error.
        # So expose it as remote-connection-failed.
        err = 'remote-connection-failed'
        if err_elem is not None:
            # This is an actual stream:error.  Create a remote-stream-error to encapsulate it.
            err = 'remote-stream-error'
        e = error.Error(err)
        e.error_stanza = err
        e.children = []
        if err_elem is not None:
            e.children.append(err_elem)
        return e

    def streamError(self, streamerror):
        """called when we get a stream:error stanza"""
        self.stream_error_called = True
        try:
            err_elem = streamerror.value.getElement()
        except AttributeError:
            err_elem = None

        e = self.buildRemoteError(err_elem)

        do_expire = True

        if len(self.waiting_requests) > 0:
            wr = self.waiting_requests.pop(0)
            wr.doErrback(e)
        else: # need to wait for a new request and then expire
            do_expire = False

        if self.pint and self.pint.sessions.has_key(self.sid):
            if do_expire:
                try:
                    self.expire()
                except:
                    self.onExpire()
            else:
                s = self.pint.sessions.get(self.sid)
                s.stream_error = e

    def connectError(self, reason):
        """called when we get disconnected"""
        if self.stream_error_called: return
        # Before Twisted 11.x the xmlstream object was passed instead of the
        # disconnect reason. See http://twistedmatrix.com/trac/ticket/2618
        if not isinstance(reason, failure.Failure):
            reason_str = 'Reason unknown'
        else:
            reason_str = str(reason)

        # If the connection was established and lost, then we need to report
        # the error back to the client, since he needs to reauthenticate.
        # FIXME: If the connection was lost before anything happened, we could
        # silently retry instead.
        if self.verbose:
            log.msg('connect ERROR: %s' % reason_str)

        self.stopTrying()

        e = error.Error('remote-connection-failed')

        do_expire = True

        if self.waiting_requests:
            wr = self.waiting_requests.pop(0)
            wr.doErrback(e)
        else: # need to wait for a new request and then expire
            do_expire = False

        if self.pint and self.pint.sessions.has_key(self.sid):
            if do_expire:
                try:
                    self.expire()
                except:
                    self.onExpire()
            else:
                s = self.pint.sessions.get(self.sid)
                s.stream_error = e


    def sendRawXml(self, obj):
        """
        Send a raw xml string, not a domish.Element
        """
        self.touch()
        self._send(obj)


    def _send(self, xml):
        """
        Send valid data over the xmlstream
        """
        if self.xmlstream: # FIXME this happens on an expired session and the post has something to send
            if isinstance(xml, domish.Element):
                xml.localPrefixes = {}
            self.xmlstream.send(xml)

    def _removeObservers(self, typ = ''):
        if typ == 'event':
            observers = self.xmlstream._eventObservers
        else:
            observers = self.xmlstream._xpathObservers
        emptyLists = []
        for priority, priorityObservers in observers.iteritems():
            for query, callbacklist in priorityObservers.iteritems():
                callbacklist.callbacks = []
                emptyLists.append((priority, query))

        for priority, query in emptyLists:
            del observers[priority][query]

    def disconnect(self):
        """
        Disconnect from the xmpp server.
        """
        if not getattr(self, 'xmlstream',None):
            return

        if self.xmlstream:
            #sh = "<presence type='unavailable' xmlns='jabber:client'/>"
            sh = "</stream:stream>"
            self.xmlstream.send(sh)

        self.stopTrying()
        if self.xmlstream:
            self.xmlstream.transport.loseConnection()

            del self.xmlstream
        self.connected = 0
        self.pint      = None
        self.elems     = []

        if self.waiting_requests:
            self.clearWaitingRequests()
            del self.waiting_requests
        self.mechanisms = None
        self.features   = None



    def checkExpired(self):
        """
        Check if the session or xmpp connection has expired
        """
        # send this so we do not timeout from servers
        if getattr(self, 'xmlstream', None):
            self.xmlstream.send(' ')
        if self.inactivity is None:
            wait = 900
        elif self.inactivity == 0:
            wait = time.time()

        else:
            wait = self.inactivity

        if self.waiting_requests and len(self.waiting_requests)>0:
            wait += self.wait # if we have pending requests we need to add the wait time

        if time.time() - self.lastModified > wait+(0.1):
            if self.site.sessions.has_key(self.uid):
                self.terminate()
            else:
                pass

        else:
            reactor.callLater(wait, self.checkExpired)


    def _cacheData(self, rid, data):
        if len(self.cache_data.keys())>=3:
            # remove the first one in
            keys = self.cache_data.keys()
            keys.sort()
            del self.cache_data[keys[0]]

        self.cache_data[int(rid)] = data

# This stuff will leave when SASL and TLS are implemented correctly
# session stuff

    def _sessionResultEvent(self, iq):
        """ """
	if len(self.waiting_requests)>0:
		wr = self.waiting_requests.pop(0)
		d  = wr.deferred
	else:
		d = None

        if iq["type"] == "result":
            if d:
                d.callback(self)
        else:
            if d:
                d.errback(self)


    def _saslSuccess(self, s):
        """ """
        self.success = 1
        self.s = s
        # return success to the client
        if len(self.waiting_requests)>0:
            self._wrPop([s])

        self.authenticator._reset()
        if self.use_raw:
            self.raw_buffer = u""



    def _saslError(self, sasl_error, d = None):
        """ SASL error """

        if d:
            d.errback(self)
        if len(self.waiting_requests)>0:
            self._wrPop([sasl_error])

########NEW FILE########
__FILENAME__ = ssl
from OpenSSL import SSL
from twisted.internet import ssl


# Override DefaultOpenSSLContextFactory to call ctx.use_certificate_chain_file
# instead of ctx.use_certificate_file, to allow certificate chains to be loaded.
class OpenSSLContextFactoryChaining(ssl.DefaultOpenSSLContextFactory):
    def __init__(self, *args, **kwargs):
        ssl.DefaultOpenSSLContextFactory.__init__(self, *args, **kwargs)

    def cacheContext(self):
        ctx = self._contextFactory(self.sslmethod)
        ctx.set_options(SSL.OP_NO_SSLv2)
        ctx.use_certificate_chain_file(self.certificateFileName)
        ctx.use_privatekey_file(self.privateKeyFileName)
        self._context = ctx

########NEW FILE########
__FILENAME__ = stream
"""

"""
from twisted.words import domish


class PunjabElementStream(domish.ExpatElementStream):
    """

    We need to store the raw unicode data to bypass serialization.

    """
    
    def _onStartElement(self, name, attrs):
        # Generate a qname tuple from the provided name
        qname = name.split(" ")
        if len(qname) == 1:
            qname = ('', name)

        # Process attributes
        for k, v in attrs.items():
            if k.find(" ") != -1:
                aqname = k.split(" ")
                attrs[(aqname[0], aqname[1])] = v
                del attrs[k]

        # Construct the new element
        e = domish.Element(qname, self.defaultNsStack[-1], attrs, self.localPrefixes)
        self.localPrefixes = {}

        # Document already started
        if self.documentStarted == 1:
            if self.currElem != None:
                self.currElem.children.append(e)
                e.parent = self.currElem
            self.currElem = e

        # New document
        else:
            self.documentStarted = 1
            self.DocumentStartEvent(e)

    def _onEndElement(self, _):
        # Check for null current elem; end of doc
        if self.currElem is None:
            self.DocumentEndEvent()
            
        # Check for parent that is None; that's
        # the top of the stack
        elif self.currElem.parent is None:
            self.ElementEvent(self.currElem)
            self.currElem = None

        # Anything else is just some element in the current
        # packet wrapping up
        else:
            self.currElem = self.currElem.parent

    def _onCdata(self, data):
        if self.currElem != None:
            self.currElem.addContent(data)

    def _onStartNamespace(self, prefix, uri):
        # If this is the default namespace, put
        # it on the stack
        if prefix is None:
            self.defaultNsStack.append(uri)
        else:
            self.localPrefixes[prefix] = uri

    def _onEndNamespace(self, prefix):
        # Remove last element on the stack
        if prefix is None:
            self.defaultNsStack.pop()

########NEW FILE########
__FILENAME__ = error
# Some code from idavoll, thanks Ralph!!
NS_XMPP_STANZAS = "urn:ietf:params:xml:ns:xmpp-stanzas"



conditions = {
	'bad-request':				{'code': '400', 'type': 'modify'},
	'not-authorized':			{'code': '401', 'type': 'cancel'},
	'item-not-found':			{'code': '404', 'type': 'cancel'},
	'not-acceptable':			{'code': '406', 'type': 'modify'},
	'conflict':					{'code': '409', 'type': 'cancel'},
	'internal-server-error':	{'code': '500', 'type': 'wait'},
	'feature-not-implemented':	{'code': '501', 'type': 'cancel'},
	'service-unavailable':		{'code': '503', 'type': 'cancel'},
}

def error_from_iq(iq, condition, text = '', type = None):
	iq.swapAttributeValues("to", "from")
	iq["type"] = 'error'
	e = iq.addElement("error")

	c = e.addElement((NS_XMPP_STANZAS, condition), NS_XMPP_STANZAS)

	if type == None:
		type = conditions[condition]['type']

	code = conditions[condition]['code']

	e["code"] = code
	e["type"] = type

	if text:
		t = e.addElement((NS_XMPP_STANZAS, "text"), NS_XMPP_STANZAS, text)

	return iq

########NEW FILE########
__FILENAME__ = ns

NS_CLIENT   = 'jabber:client'
NS_ROSTER   = 'jabber:iq:roster'
NS_AUTH     = 'jabber:iq:auth'
NS_STREAMS  = 'http://etherx.jabber.org/streams'
NS_XMPP_TLS = 'urn:ietf:params:xml:ns:xmpp-tls'
NS_COMMANDS = 'http://jabber.org/protocol/commands'

TLS_XMLNS = 'urn:ietf:params:xml:ns:xmpp-tls'
SASL_XMLNS = 'urn:ietf:params:xml:ns:xmpp-sasl'
BIND_XMLNS = 'urn:ietf:params:xml:ns:xmpp-bind'
SESSION_XMLNS = 'urn:ietf:params:xml:ns:xmpp-session'
STREAMS_XMLNS  = 'urn:ietf:params:xml:ns:xmpp-streams'

IQ_GET      = "/iq[@type='get']"
IQ_SET      = "/iq[@type='set']"

IQ_GET_AUTH = IQ_GET+"/query[@xmlns='%s']" % (NS_AUTH,)
IQ_SET_AUTH = IQ_SET+"/query[@xmlns='%s']" % (NS_AUTH,)


XMPP_PREFIXES = {NS_STREAMS:'stream'}
#                 NS_COMMANDS: 'commands'}


########NEW FILE########
__FILENAME__ = server
# XMPP server class

from twisted.application import service
from twisted.python import components

from twisted.internet import reactor


from twisted.words.xish import domish, xpath, xmlstream
from twisted.words.protocols.jabber import jid

from punjab.xmpp import ns

SASL_XMLNS = 'urn:ietf:params:xml:ns:xmpp-sasl'
COMP_XMLNS = 'http://jabberd.jabberstudio.org/ns/component/1.0'
STREAMS_XMLNS  = 'urn:ietf:params:xml:ns:xmpp-streams'

from zope.interface import Interface, implements

# interfaces
class IXMPPServerService(Interface):
    pass

class IXMPPServerFactory(Interface):
    pass

class IXMPPFeature(Interface):
    pass

class IXMPPAuthenticationFeature(IXMPPFeature):
    pass

class IQAuthFeature(object):
    """ XEP-0078 : http://www.xmpp.org/extensions/xep-0078.html"""

    implements(IXMPPAuthenticationFeature)


    IQ_GET_AUTH = xpath.internQuery(ns.IQ_GET_AUTH)
    IQ_SET_AUTH = xpath.internQuery(ns.IQ_SET_AUTH)


    def associateWithStream(self, xs):
        """Add a streamm start event observer.
           And do other things to associate with the xmlstream if necessary.
        """
        self.xmlstream = xs
        self.xmlstream.addOnetimeObserver(xmlstream.STREAM_START_EVENT,
                                          self.streamStarted)

    def disassociateWithStream(self, xs):
        self.xmlstream.removeObserver(self.IQ_GET_AUTH,
                                      self.authRequested)
        self.xmlstream.removeObserver(self.IQ_SET_AUTH,
                                      self.auth)
        self.xmlstream = None


    def streamStarted(self, elm):
        """
        Called when client sends stream:stream
        """
        self.xmlstream.addObserver(self.IQ_GET_AUTH,
                                   self.authRequested)
        self.xmlstream.addObserver(self.IQ_SET_AUTH,
                                   self.auth)

    def authRequested(self, elem):
        """Return the supported auth type.

        """
        resp = domish.Element(('iq', ns.NS_CLIENT))
        resp['type'] = 'result'
        resp['id'] = elem['id']
        q = resp.addElement("query", ns.NS_AUTH)
        q.addElement("username", content=str(elem.query.username))
        q.addElement("digest")
        q.addElement("password")
        q.addElement("resource")

        self.xmlstream.send(resp)

    def auth(self, elem):
        """Do not auth the user, anyone can log in"""

        username = elem.query.username.__str__()
        resource = elem.query.resource.__str__()

        user = jid.internJID(username+'@'+self.xmlstream.host+'/'+resource)

        resp = domish.Element(('iq', ns.NS_CLIENT))
        resp['type'] = 'result'
        resp['id'] = elem['id']

        self.xmlstream.send(resp)

        self.xmlstream.authenticated(user)



class XMPPServerProtocol(xmlstream.XmlStream):
    """ Basic dummy server protocol """
    host = "localhost"
    user = None
    initialized = False
    id = 'Punjab123'
    features = [IQAuthFeature()]
    delay_features = 0

    def connectionMade(self):
        """
        a client connection has been made
        """
        xmlstream.XmlStream.connectionMade(self)

        self.bootstraps = [
            (xmlstream.STREAM_CONNECTED_EVENT, self.streamConnected),
            (xmlstream.STREAM_START_EVENT, self.streamStarted),
            (xmlstream.STREAM_END_EVENT, self.streamEnded),
            (xmlstream.STREAM_ERROR_EVENT, self.streamErrored),
            ]

        for event, fn in self.bootstraps:
            self.addObserver(event, fn)

        # load up the authentication features
        for f in self.features:
            if IXMPPAuthenticationFeature.implementedBy(f.__class__):
                f.associateWithStream(self)

    def send(self, obj):
        if not self.initialized:
            self.transport.write("""<?xml version="1.0"?>\n""")
            self.initialized = True
        xmlstream.XmlStream.send(self, obj)


    def streamConnected(self, elm):
        print "stream connected"

    def streamStarted(self, elm):
        """stream has started, we need to respond

        """
        if self.delay_features == 0:
            self.send("""<stream:stream xmlns='%s' xmlns:stream='http://etherx.jabber.org/streams' from='%s' id='%s' version='1.0' xml:lang='en'><stream:features><register xmlns='http://jabber.org/features/iq-register'/></stream:features>""" % (ns.NS_CLIENT, self.host, self.id,))
        else:
            self.send("""<stream:stream xmlns='%s' xmlns:stream='http://etherx.jabber.org/streams' from='%s' id='%s' version='1.0' xml:lang='en'>""" % (ns.NS_CLIENT, self.host, self.id,))
            reactor.callLater(self.delay_features, self.send, """<stream:features><register xmlns='http://jabber.org/features/iq-register'/></stream:features>""")

    def streamEnded(self, elm):
        self.send("""</stream:stream>""")

    def streamErrored(self, elm):
        self.send("""<stream:error/></stream:stream>""")

    def authenticated(self, user):
        """User has authenticated.
        """
        self.user = user

    def onElement(self, element):
        try:
            xmlstream.XmlStream.onElement(self, element)
        except Exception, e:
            print "Exception!", e
            raise e

    def onDocumentEnd(self):
        pass

    def connectionLost(self, reason):
        xmlstream.XmlStream.connectionLost(self, reason)
        pass

    def triggerChallenge(self):
        """ send a fake challenge for testing
        """
        self.send("""<challenge xmlns='urn:ietf:params:xml:ns:xmpp-sasl'>cmVhbG09ImNoZXNzcGFyay5jb20iLG5vbmNlPSJ0YUhIM0FHQkpQSE40eXNvNEt5cFlBPT0iLHFvcD0iYXV0aCxhdXRoLWludCIsY2hhcnNldD11dGYtOCxhbGdvcml0aG09bWQ1LXNlc3M=</challenge>""")


    def triggerInvalidXML(self):
        """Send invalid XML, to trigger a parse error."""
        self.send("""<parse error=>""")
        self.streamEnded(None)

    def triggerStreamError(self):
        """ send a stream error
        """
        self.send("""
        <stream:error xmlns:stream='http://etherx.jabber.org/streams'>
            <policy-violation xmlns='urn:ietf:params:xml:ns:xmpp-streams'/>
            <text xmlns='urn:ietf:params:xml:ns:xmpp-streams' xml:lang='langcode'>Error text</text>
            <arbitrary-extension val='2'/>
        </stream:error>""")
        self.streamEnded(None)



class XMPPServerFactoryFromService(xmlstream.XmlStreamFactory):
    implements(IXMPPServerFactory)

    protocol = XMPPServerProtocol

    def __init__(self, service):
        xmlstream.XmlStreamFactory.__init__(self)
        self.service = service


    def buildProtocol(self, addr):
        self.resetDelay()
        xs = self.protocol()
        xs.factory = self
        for event, fn in self.bootstraps:
            xs.addObserver(event, fn)
        return xs


components.registerAdapter(XMPPServerFactoryFromService,
                           IXMPPServerService,
                           IXMPPServerFactory)


class XMPPServerService(service.Service):

    implements(IXMPPServerService)




########NEW FILE########
__FILENAME__ = testparser

import os
import sys, random
from twisted.trial import unittest
import time
from twisted.web import server, resource, static, http, client
from twisted.words.protocols.jabber import jid
from twisted.internet import defer, protocol, reactor
from twisted.application import internet, service
from twisted.words.xish import domish, xpath

from twisted.python import log

from punjab.httpb import HttpbParse



class ParseTestCase(unittest.TestCase):
    """
    Tests for Punjab compatability with http://www.xmpp.org/extensions/xep-0124.html
    """

    def testTime(self):
        XML = """
 <body rid='4019888743' xmlns='http://jabber.org/protocol/httpbind' sid='948972a64d524f862107cdbd748d1d16'><iq id='980:getprefs' type='get'><query xmlns='jabber:iq:private'><preferences xmlns='http://chesspark.com/xml/chesspark-01'/></query></iq><iq id='981:getallignorelists' type='get'><query xmlns='jabber:iq:privacy'/></iq><test/><testing><ha/></testing></body>
"""
        t = time.time()

        for i in range(0, 10000):
            hp = HttpbParse(use_t=True)
            b, elems = hp.parse(XML)
            for e in elems:
                x = e.toXml()
        td = time.time() - t


        t = time.time()
        for i in range(0, 10000):
            hp = HttpbParse()
            b, elems = hp.parse(XML)
            for e in elems:
                if type(u'') == type(e):
                    x = e
                
        ntd = time.time() - t
        
        self.failUnless(td>ntd, 'Not faster')
        


    def testGtBug(self):
        XML = """ <body rid='1445008480' xmlns='http://jabber.org/protocol/httpbind' sid='1f2f8585f41e2dacf1f1f0ad83f8833d'><presence type='unavailable' from='KurodaJr@chesspark.com/cpc' to='5252844@games.chesspark.com/KurodaJr@chesspark.com'/><iq id='10059:enablepush' to='search.chesspark.com' type='set'><search xmlns='http://onlinegamegroup.com/xml/chesspark-01' node='play'><filter><relative-rating>500</relative-rating><time-control-range name='speed'/></filter></search></iq><iq id='10060:enablepush' to='search.chesspark.com' type='set'><search xmlns='http://onlinegamegroup.com/xml/chesspark-01' node='play'><filter><relative-rating>500</relative-rating><time-control-range name='speed'/></filter></search></iq></body>
"""
        hp = HttpbParse()

        b, e = hp.parse(XML)

        # need tests here
        self.failUnless(e[0]==u"<presence from='KurodaJr@chesspark.com/cpc' type='unavailable' to='5252844@games.chesspark.com/KurodaJr@chesspark.com'/>",'invalid xml')
        self.failUnless(e[1]==u"<iq to='search.chesspark.com' type='set' id='10059:enablepush'><search xmlns='http://onlinegamegroup.com/xml/chesspark-01' node='play'><filter><relative-rating>500</relative-rating><time-control-range name='speed'/></filter></search></iq>", 'invalid xml')
        self.failUnless(e[2]==u"<iq to='search.chesspark.com' type='set' id='10060:enablepush'><search xmlns='http://onlinegamegroup.com/xml/chesspark-01' node='play'><filter><relative-rating>500</relative-rating><time-control-range name='speed'/></filter></search></iq>", 'invalid xml')


    def testParse(self):
        XML = """
 <body rid='4019888743' xmlns='http://jabber.org/protocol/httpbind' sid='948972a64d524f862107cdbd748d1d16'><iq id='980:getprefs' type='get'><query xmlns='jabber:iq:private'><preferences xmlns='http://chesspark.com/xml/chesspark-01'/></query></iq><iq id='981:getallignorelists' type='get'><query xmlns='jabber:iq:privacy'/></iq></body>
"""
        hp = HttpbParse()

        b, e = hp.parse(XML)

        # need tests here
        self.failUnless(e[0]==u"<iq type='get' id='980:getprefs'><query xmlns='jabber:iq:private'><preferences xmlns='http://chesspark.com/xml/chesspark-01'/></query></iq>", 'invalid xml')
        self.failUnless(e[1]==u"<iq type='get' id='981:getallignorelists'><query xmlns='jabber:iq:privacy'/></iq>", 'invalid xml')
        

    def testParseEscapedAttribute(self):
        XML = """<body rid='4019888743' xmlns='http://jabber.org/protocol/httpbind' sid='948972a64d524f862107cdbd748d1d16'><presence from='dude@example.com' to='room@conf.example.com/D&apos;Artagnan Longfellow'/></body>"""

        hp = HttpbParse()

        b, e = hp.parse(XML)

        ex = "<presence to='room@conf.example.com/D&apos;Artagnan Longfellow' from='dude@example.com'/>"
        self.assertEquals(e[0], ex)


    def testPrefixes(self):
        XML = """<body rid='384852951' xmlns='http://jabber.org/protocol/httpbind' sid='e46501b24abd334c062598498a8e02ba'><auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='DIGEST-MD5'/></body>"""

        hp = HttpbParse()

        b, e = hp.parse(XML)

        self.failUnless(e[0]==u"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='DIGEST-MD5'/>", 'invalid xml')

    def testPrefixesLang(self):
        XML = """<body rid='384852951' xmlns='http://jabber.org/protocol/httpbind' sid='e46501b24abd334c062598498a8e02ba'><message xml:lang='fr' to='test@test.com'><body>test</body></message></body>"""

        hp = HttpbParse()

        b, e = hp.parse(XML)
        self.failUnless(e[0]==u"<message to='test@test.com' xml:lang='fr'><body>test</body></message>", 'invalid xml')



    def testEscapedCDATA(self):
        XML = """<body rid='384852951' xmlns='http://jabber.org/protocol/httpbind' sid='e46501b24abd334c062598498a8e02ba'><message><body>&gt; </body></message></body>"""

        hp = HttpbParse()

        b, e = hp.parse(XML)

        XML = """ <body rid='1484853516' xmlns='http://jabber.org/protocol/httpbind' sid='4dc131a03346bf94b0d2565dda02de36'><message to='dev@chat.chesspark.com' from='jack@chesspark.com/cpc' type='groupchat' id='2900'><body xmlns='jabber:client'>i type &gt; and i see &gt;&gt;&gt;</body></message></body>"""

        hp = HttpbParse()

        b, e = hp.parse(XML)

        self.failUnless(e[0]==u"<message to='dev@chat.chesspark.com' from='jack@chesspark.com/cpc' id='2900' type='groupchat'><body xmlns='jabber:client'>i type &gt; and i see &gt;&gt;&gt;</body></message>", 'Invalid Xml')


    def testCDATA(self):
        XML = """<body rid='3116008962' xmlns='http://jabber.org/protocol/httpbind' sid='88be95e7ebbd8c12465e311ce73fb8ac'><response xmlns='urn:ietf:params:xml:ns:xmpp-sasl'>dXNlcm5hbWU9InRvZnUiLHJlYWxtPSJkZXYuY2hlc3NwYXJrLmNvbSIsbm9uY2U9Ik5SaW5HQkNaWjg0U09Ea1BzMWpxd1E9PSIsY25vbmNlPSJkNDFkOGNkOThmMDBiMjA0ZTk4MDA5OThlY2Y4NDI3ZSIsbmM9IjAwMDAwMDAxIixxb3A9ImF1dGgiLGRpZ2VzdC11cmk9InhtcHAvZGV2LmNoZXNzcGFyay5jb20iLHJlc3BvbnNlPSIxNGQ3NWE5YmU2MzdkOTdkOTM1YjU2Y2M4ZWZhODk4OSIsY2hhcnNldD0idXRmLTgi</response></body>"""

        hp = HttpbParse()

        b, e = hp.parse(XML)

        self.failUnless(e[0]==u"<response xmlns='urn:ietf:params:xml:ns:xmpp-sasl'>dXNlcm5hbWU9InRvZnUiLHJlYWxtPSJkZXYuY2hlc3NwYXJrLmNvbSIsbm9uY2U9Ik5SaW5HQkNaWjg0U09Ea1BzMWpxd1E9PSIsY25vbmNlPSJkNDFkOGNkOThmMDBiMjA0ZTk4MDA5OThlY2Y4NDI3ZSIsbmM9IjAwMDAwMDAxIixxb3A9ImF1dGgiLGRpZ2VzdC11cmk9InhtcHAvZGV2LmNoZXNzcGFyay5jb20iLHJlc3BvbnNlPSIxNGQ3NWE5YmU2MzdkOTdkOTM1YjU2Y2M4ZWZhODk4OSIsY2hhcnNldD0idXRmLTgi</response>", 'Invalid xml')



    def testPrefsCdata(self):

        XML = """<body rid='4017760695' xmlns='http://jabber.org/protocol/httpbind' sid='74a730628186b053a953999bc2ae7dba'>
      <iq id='6161:setprefs' type='set' xmlns='jabber:client'>
        <query xmlns='jabber:iq:private'>
          <preferences xmlns='http://chesspark.com/xml/chesspark-01'>
            <statuses>
              <away>test2</away>
              <available>test1</available>
            </statuses>
            <favorite-channels>
              <channel jid='asdf@chat.chesspark.com' autojoin='no'/>
              <channel jid='focus@chat.chesspark.com' autojoin='no'/>
              <channel jid='help@chat.chesspark.com' autojoin='no'/>
            </favorite-channels>
            <time-controls/>
            <searchfilters>
              <filter node='play'>
                <variant name='standard'/>
              </filter>
              <filter open='yes' node='watch'>
                <computer/>
              </filter>
              <filter node='adjourned'>
                <computer/>
              </filter>
              <filter node='myads'>
                <computer/>
              </filter>
            </searchfilters>
            <loginrooms>
              <room>pro@chat.chesspark.com</room>
            </loginrooms>
            <noinitialroster/>
            <boardsize size='61'/>
            <volume setting='100'/>
            <hidewelcomedialog/>
            <showoffline/>
            <showavatars/>
            <showmucpresenceinchat/>
            <hideparticipants/>
            <newlineonshift/>
            <nochatnotify/>
            <no-gameboard-autoresize/>
            <messagewhenplaying/>
            <hidegamefinderhelp/>
            <hidewarningondisconnect/>
            <disablesounds/>
            <nogamesearchonlogin/>
          </preferences>
        </query>
      </iq>
    </body>"""


        hp = HttpbParse()

        b, e = hp.parse(XML)

        self.failUnless(e[0]==u"<iq xmlns='jabber:client' type='set' id='6161:setprefs'>\n        <query xmlns='jabber:iq:private'>\n          <preferences xmlns='http://chesspark.com/xml/chesspark-01'>\n            <statuses>\n              <away>test2</away>\n              <available>test1</available>\n            </statuses>\n            <favorite-channels>\n              <channel jid='asdf@chat.chesspark.com' autojoin='no'/>\n              <channel jid='focus@chat.chesspark.com' autojoin='no'/>\n              <channel jid='help@chat.chesspark.com' autojoin='no'/>\n            </favorite-channels>\n            <time-controls/>\n            <searchfilters>\n              <filter node='play'>\n                <variant name='standard'/>\n              </filter>\n              <filter node='watch' open='yes'>\n                <computer/>\n              </filter>\n              <filter node='adjourned'>\n                <computer/>\n              </filter>\n              <filter node='myads'>\n                <computer/>\n              </filter>\n            </searchfilters>\n            <loginrooms>\n              <room>pro@chat.chesspark.com</room>\n            </loginrooms>\n            <noinitialroster/>\n            <boardsize size='61'/>\n            <volume setting='100'/>\n            <hidewelcomedialog/>\n            <showoffline/>\n            <showavatars/>\n            <showmucpresenceinchat/>\n            <hideparticipants/>\n            <newlineonshift/>\n            <nochatnotify/>\n            <no-gameboard-autoresize/>\n            <messagewhenplaying/>\n            <hidegamefinderhelp/>\n            <hidewarningondisconnect/>\n            <disablesounds/>\n            <nogamesearchonlogin/>\n          </preferences>\n        </query>\n      </iq>", 'invalid xml')

########NEW FILE########
__FILENAME__ = test_basic

import os
import os.path
import random
from twisted.trial import unittest

from twisted.web import server, resource, static

from twisted.internet import defer, reactor

from twisted.words.xish import domish

from punjab.httpb import HttpbService
from punjab.xmpp import server as xmppserver
from punjab import httpb_client

class DummyTransport:

    def __init__(self):
        self.data = []

    def write(self, bytes):
        self.data.append(bytes)

    def loseConnection(self, *args, **kwargs):
        self.data = []

class TestCase(unittest.TestCase):
    """Basic test class for Punjab
    """

    def setUp(self):
        # set up punjab
        html_dir = "./html"
        if not os.path.exists(html_dir):
            os.mkdir(html_dir) # create directory in _trial_temp
        self.root = static.File(html_dir) # make _trial_temp/html the root html directory
        self.rid = random.randint(0,10000000)
        self.hbs = HttpbService(1)
        self.b = resource.IResource(self.hbs)
        self.root.putChild('xmpp-bosh', self.b)

        self.site  = server.Site(self.root)

        self.p =  reactor.listenTCP(0, self.site, interface="127.0.0.1")
        self.port = self.p.getHost().port

        # set up proxy

        self.proxy = httpb_client.Proxy(self.getURL())
        self.sid   = None
        self.keys  = httpb_client.Keys()

        # set up dummy xmpp server

        self.server_service = xmppserver.XMPPServerService()
        self.server_factory = xmppserver.IXMPPServerFactory(self.server_service)
        self.server = reactor.listenTCP(0, self.server_factory, interface="127.0.0.1")
        self.server_port = self.server.socket.getsockname()[1]

        # Hook the server's buildProtocol to make the protocol instance
        # accessible to tests.
        buildProtocol = self.server_factory.buildProtocol
        d1 = defer.Deferred()
        def _rememberProtocolInstance(addr):
            self.server_protocol = buildProtocol(addr)
            # keeping this around because we may want to wrap this specific to tests
            # self.server_protocol = protocol.wrappedProtocol
            d1.callback(None)
            return self.server_protocol
        self.server_factory.buildProtocol = _rememberProtocolInstance


    def getURL(self, path = "xmpp-bosh"):
        return "http://127.0.0.1:%d/%s" % (self.port, path)


    def key(self,b):
        key, newkey = self.keys.getKey()

        if key:
            b['key'] = key
        if newkey:
            b['newkey'] = newkey

        return b

    def resend(self, ext = None):
        self.rid = self.rid - 1
        return self.send(ext)

    def get_body_node(self, ext=None, sid=None, rid=None, useKey=False, connect=False, **kwargs):
        self.rid = self.rid + 1
        if sid is None:
            sid = self.sid
        if rid is None:
            rid = self.rid
        b = domish.Element(("http://jabber.org/protocol/httpbind","body"))
        b['content']  = 'text/xml; charset=utf-8'
        b['hold'] = '0'
        b['wait'] = '60'
        b['ack'] = '1'
        b['xml:lang'] = 'en'
        b['rid'] = str(rid)

        if sid:
            b['sid'] = str(sid)

        if connect:
            b['to'] = 'localhost'
            b['route'] = 'xmpp:127.0.0.1:%i' % self.server_port
            b['ver'] = '1.6'

        if useKey:
            self.key(b)

        if ext is not None:
            if isinstance(ext, domish.Element):
                b.addChild(ext)
            else:
                b.addRawXml(ext)

        for key, value in kwargs.iteritems():
            b[key] = value
        return b

    def send(self, ext = None, sid = None, rid = None):
        b = self.get_body_node(ext, sid, rid)
        d = self.proxy.send(b)
        return d

    def _storeSID(self, res):
        self.sid = res[0]['sid']
        return res

    def connect(self, b):
        d = self.proxy.connect(b)
        # If we don't already have a SID, store the one we get back.
        if not self.sid:
            d.addCallback(self._storeSID)
        return d


    def _error(self, e):
        # self.fail(e)
        pass

    def _cleanPending(self):
        pending = reactor.getDelayedCalls()
        if pending:
            for p in pending:
                if p.active():
                    p.cancel()

    def _cleanSelectables(self):
        reactor.removeAll()

    def tearDown(self):
        def cbStopListening(result=None):
            self.root = None
            self.site = None
            self.proxy.factory.stopFactory()
            self.server_factory.stopFactory()
            self.server = None
            self._cleanPending()
            self._cleanSelectables()

        os.rmdir("./html") # remove directory from _trial_temp
        self.b.service.poll_timeouts.stop()
        self.b.service.stopService()
        self.p.stopListening()
        for s in self.b.service.sessions.keys():
            sess = self.b.service.sessions.get(s)
            if sess:
                self.b.service.endSession(sess)
        if hasattr(self.proxy.factory,'client'):
            self.proxy.factory.client.transport.stopConnecting()
        self.server_factory.protocol.delay_features = 0

        d = defer.maybeDeferred(self.server.stopListening)
        d.addCallback(cbStopListening)

        return d


########NEW FILE########
__FILENAME__ = xep124
from twisted.internet import defer, reactor, task
from twisted.words.xish import xpath

from twisted.python import log

from punjab import httpb_client

import test_basic


class XEP0124TestCase(test_basic.TestCase):
    """
    Tests for Punjab compatability with http://www.xmpp.org/extensions/xep-0124.html
    """


    def testCreateSession(self):
        """
        Test Section 7.1 of BOSH xep : http://www.xmpp.org/extensions/xep-0124.html#session
        """

        def _testSessionCreate(res):
            self.failUnless(res[0].name=='body', 'Wrong element')
            self.failUnless(res[0].hasAttribute('sid'), 'Not session id')

        def _error(e):
            # This fails on DNS
            log.err(e)

        BOSH_XML = """<body content='text/xml; charset=utf-8'
      hold='1'
      rid='1573741820'
      to='localhost'
      route='xmpp:127.0.0.1:%(server_port)i'
      secure='true'
      ver='1.6'
      wait='60'
      ack='1'
      xml:lang='en'
      xmlns='http://jabber.org/protocol/httpbind'/>
 """% { "server_port": self.server_port }

        d = self.proxy.connect(BOSH_XML).addCallback(_testSessionCreate)
        d.addErrback(_error)
        return d


    def testWhiteList(self):
        """
        Basic tests for whitelisting domains.
        """

        def _testSessionCreate(res):
            self.failUnless(res[0].name=='body', 'Wrong element')
            self.failUnless(res[0].hasAttribute('sid'), 'Not session id')

        def _error(e):
            # This fails on DNS
            log.err(e)

        self.hbs.white_list = ['.localhost']
        BOSH_XML = """<body content='text/xml; charset=utf-8'
      hold='1'
      rid='1573741820'
      to='localhost'
      route='xmpp:127.0.0.1:%(server_port)i'
      secure='true'
      ver='1.6'
      wait='60'
      ack='1'
      xml:lang='en'
      xmlns='http://jabber.org/protocol/httpbind'/>
 """% { "server_port": self.server_port }

        d = self.proxy.connect(BOSH_XML).addCallback(_testSessionCreate)
        d.addErrback(_error)
        return d

    def testWhiteListError(self):
        """
        Basic tests for whitelisting domains.
        """

        def _testSessionCreate(res):
            self.fail("Session should not be created")

        def _error(e):
            # This is the error we expect.
            if isinstance(e.value, ValueError) and e.value.args == ('400', 'Bad Request'):
                return True

            # Any other error, including the error raised from _testSessionCreate, should
            # be propagated up to the test runner.
            return e

        self.hbs.white_list = ['test']
        BOSH_XML = """<body content='text/xml; charset=utf-8'
      hold='1'
      rid='1573741820'
      to='localhost'
      route='xmpp:127.0.0.1:%(server_port)i'
      secure='true'
      ver='1.6'
      wait='60'
      ack='1'
      xml:lang='en'
      xmlns='http://jabber.org/protocol/httpbind'/>
 """% { "server_port": self.server_port }

        d = self.proxy.connect(BOSH_XML).addCallback(_testSessionCreate)
        d.addErrback(_error)
        return d

    def testSessionTimeout(self):
        """Test if we timeout correctly
        """

        def testTimeout(res):
            self.failUnlessEqual(res.value[0], '404')

        def testCBTimeout(res):
            # check for terminate if we expire
            terminate = res[0].getAttribute('type',False)
            self.failUnlessEqual(terminate, 'terminate')

        def sendTest():
            sd = self.send()
            sd.addCallback(testCBTimeout)
            sd.addErrback(testTimeout)
            return sd

        def testResend(res):
            self.failUnless(res[0].name=='body', 'Wrong element')
            s = self.b.service.sessions[self.sid]
            self.failUnless(s.inactivity==2,'Wrong inactivity value')
            self.failUnless(s.wait==2, 'Wrong wait value')
            return task.deferLater(reactor, s.wait+s.inactivity+1, sendTest)

        def testSessionCreate(res):
            self.failUnless(res[0].name=='body', 'Wrong element')
            self.failUnless(res[0].hasAttribute('sid'),'Not session id')
            self.sid = res[0]['sid']

            # send and wait
            sd = self.send()
            sd.addCallback(testResend)
            return sd



        BOSH_XML = """<body content='text/xml; charset=utf-8'
      hold='1'
      rid='%(rid)i'
      to='localhost'
      route='xmpp:127.0.0.1:%(server_port)i'
      ver='1.6'
      wait='2'
      ack='1'
      inactivity='2'
      xml:lang='en'
      xmlns='http://jabber.org/protocol/httpbind'/>
 """% { "rid": self.rid, "server_port": self.server_port }

        return self.proxy.connect(BOSH_XML).addCallbacks(testSessionCreate)

    def testRemoteError(self):
        """
        This is to test if we get errors when there are no waiting requests.
        """

        def _testStreamError(res):
            self.assertEqual(True, isinstance(res.value, httpb_client.HTTPBNetworkTerminated))

            self.assertEqual(True, res.value.body_tag.hasAttribute('condition'), 'No attribute condition')
            # This is not a stream error because we sent invalid xml
            self.assertEqual(res.value.body_tag['condition'], 'remote-stream-error')
            self.assertEqual(True, len(res.value.elements)>0)
            # The XML should exactly match the error XML sent by triggerStreamError().
            self.assertEqual(True,xpath.XPathQuery("/error").matches(res.value.elements[0]))
            self.assertEqual(True,xpath.XPathQuery("/error/policy-violation").matches(res.value.elements[0]))
            self.assertEqual(True,xpath.XPathQuery("/error/arbitrary-extension").matches(res.value.elements[0]))
            self.assertEqual(True,xpath.XPathQuery("/error/text[text() = 'Error text']").matches(res.value.elements[0]))



        def _failStreamError(res):
            self.fail('A stream error needs to be returned')

        def _testSessionCreate(res):
            self.sid = res[0]['sid']
            # this xml is valid, just for testing
            # the point is to wait for a stream error
            d = self.send('<fdsfd/>')
            d.addCallback(_failStreamError)
            d.addErrback(_testStreamError)
            self.server_protocol.triggerStreamError()

            return d

        BOSH_XML = """<body content='text/xml; charset=utf-8'
      hold='1'
      rid='%(rid)i'
      to='localhost'
      route='xmpp:127.0.0.1:%(server_port)i'
      ver='1.6'
      wait='60'
      ack='1'
      xml:lang='en'
      xmlns='http://jabber.org/protocol/httpbind'/>
 """% { "rid": self.rid, "server_port": self.server_port }

        d = self.proxy.connect(BOSH_XML).addCallback(_testSessionCreate)

        return d


    @defer.inlineCallbacks
    def testStreamFlushOnError(self):
        """
        Test that messages included in a <body type='terminate'> message from the
        client are sent to the server before terminating.
        """
        yield self.connect(self.get_body_node(connect=True))

        # Set got_testing_node to true when the XMPP server receives the <testing/> we
        # send below.
        got_testing_node = [False] # work around Python's 2.6 lack of nonlocal
        wait = defer.Deferred()
        def received_testing(a):
            got_testing_node[0] = True
            wait.callback(True)
        self.server_protocol.addObserver("/testing", received_testing)

        # Ensure that we always remove the received_testing listener.
        try:
            # Send <body type='terminate'><testing/></body>.  This should result in a
            # HTTPBNetworkTerminated exception.
            try:
                yield self.proxy.send(self.get_body_node(ext='<testing/>', type='terminate'))
            except httpb_client.HTTPBNetworkTerminated as e:
                self.failUnlessEqual(e.body_tag.getAttribute('condition', None), None)

            # Wait until <testing/> is actually received by the XMPP server.  The previous
            # request completing only means that the proxy has received the stanza, not that
            # it's been delivered to the XMPP server.
            yield wait

        finally:
            self.server_protocol.removeObserver("/testing", received_testing)

        # This should always be true, or we'd never have woken up from wait.
        self.assertEqual(True,got_testing_node[0])

    @defer.inlineCallbacks
    def testTerminateRace(self):
        """Test that buffered messages are flushed when the connection is terminated."""
        yield self.connect(self.get_body_node(connect=True))

        def log_observer(event):
            self.failIf(event['isError'], event)

        log.addObserver(log_observer)

        # Simultaneously cause a stream error (server->client closed) and send a terminate
        # from the client to the server.  Both sides are closing the connection at once.
        # Make sure the connection closes cleanly without logging any errors ("Unhandled
        # Error"), and the client receives a terminate in response.
        try:
            self.server_protocol.triggerStreamError()
            yield self.proxy.send(self.get_body_node(type='terminate'))
        except httpb_client.HTTPBNetworkTerminated as e:
            self.assertEqual(e.body_tag.getAttribute('condition', None), 'remote-stream-error')
        finally:
            log.removeObserver(log_observer)

    @defer.inlineCallbacks
    def testStreamKeying1(self):
        """Test that connections succeed when stream keying is active."""

        yield self.connect(self.get_body_node(connect=True, useKey=True))
        yield self.proxy.send(self.get_body_node(useKey=True))
        yield self.proxy.send(self.get_body_node(useKey=True))

    @defer.inlineCallbacks
    def testStreamKeying2(self):
        """Test that 404 is received if stream keying is active and no key is supplied."""
        yield self.connect(self.get_body_node(connect=True, useKey=True))

        try:
            yield self.proxy.send(self.get_body_node(useKey=False))
        except httpb_client.HTTPBNetworkTerminated as e:
            self.failUnlessEqual(e.body_tag.getAttribute('condition', None), 'item-not-found')
        else:
            self.fail("Expected 404 Not Found")


    @defer.inlineCallbacks
    def testStreamKeying3(self):
        """Test that 404 is received if stream keying is active and an invalid key is supplied."""
        yield self.connect(self.get_body_node(connect=True, useKey=True))

        try:
            yield self.proxy.send(self.get_body_node(useKey=True, key='0'*40))
        except httpb_client.HTTPBNetworkTerminated as e:
            self.failUnlessEqual(e.body_tag.getAttribute('condition', None), 'item-not-found')
        else:
            self.fail("Expected 404 Not Found")


    @defer.inlineCallbacks
    def testStreamKeying4(self):
        """Test that 404 is received if we supply a key on a connection without active keying."""
        yield self.connect(self.get_body_node(connect=True, useKey=False))

        try:
            yield self.proxy.send(self.get_body_node(key='0'*40))
        except httpb_client.HTTPBNetworkTerminated as e:
            self.failUnlessEqual(e.body_tag.getAttribute('condition', None), 'item-not-found')
        else:
            self.fail("Expected 404 Not Found")

    @defer.inlineCallbacks
    def testStreamKeying5(self):
        """Test rekeying."""
        yield self.connect(self.get_body_node(connect=True, useKey=True))
        yield self.proxy.send(self.get_body_node(useKey=True))

        # Erase all but the last key to force a rekeying.
        self.keys.k = [self.keys.k[-1]]

        yield self.proxy.send(self.get_body_node(useKey=True))
        yield self.proxy.send(self.get_body_node(useKey=True))


    def testStreamParseError(self):
        """
        Test that remote-connection-failed is received when the proxy receives invalid XML
        from the XMPP server.
        """

        def _testStreamError(res):
            self.assertEqual(True, isinstance(res.value, httpb_client.HTTPBNetworkTerminated))
            self.assertEqual(res.value.body_tag.getAttribute('condition', None), 'remote-connection-failed')

        def _failStreamError(res):
            self.fail('Expected a remote-connection-failed error')

        def _testSessionCreate(res):
            self.sid = res[0]['sid']
            self.server_protocol.triggerInvalidXML()
            return self.send().addCallbacks(_failStreamError, _testStreamError)

        return self.proxy.connect(self.get_body_node(connect=True)).addCallback(_testSessionCreate)

    def testFeaturesError(self):
        """
        This is to test if we get stream features and NOT twice
        """

        def _testError(res):
            self.assertEqual(True,res[1][0].name=='challenge','Did not get correct challenge stanza')

        def _testSessionCreate(res):
            self.sid = res[0]['sid']
            # this xml is valid, just for testing
            # the point is to wait for a stream error
            self.assertEqual(True,res[1][0].name=='features','Did not get initial features')

            d = self.send("<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='DIGEST-MD5'/>")
            d.addCallback(_testError)
            reactor.callLater(1.1, self.server_protocol.triggerChallenge)
            return d

        BOSH_XML = """<body content='text/xml; charset=utf-8'
      hold='1'
      rid='%(rid)i'
      to='localhost'
      route='xmpp:127.0.0.1:%(server_port)i'
      ver='1.6'
      wait='15'
      ack='1'
      xml:lang='en'
      xmlns='http://jabber.org/protocol/httpbind'/>
 """% { "rid": self.rid, "server_port": self.server_port }
        self.server_factory.protocol.delay_features = 3

        d = self.proxy.connect(BOSH_XML).addCallback(_testSessionCreate)
        # NOTE : to trigger this bug there needs to be 0 waiting requests.

        return d


    def testRidCountBug(self):
        """
        This is to test if rid becomes off on resends
        """
        @defer.inlineCallbacks
        def _testError(res):
            self.assertEqual(res[1][0].name, 'challenge','Did not get correct challenge stanza')
            for r in range(5):
                # send auth to bump up rid
                res = yield self.send("<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='DIGEST-MD5'/>")
            # resend auth
            for r in range(5):
                res = yield self.resend("<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='DIGEST-MD5'/>")

            res = yield self.resend("<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='DIGEST-MD5'/>")


        def _testSessionCreate(res):
            self.sid = res[0]['sid']
            # this xml is valid, just for testing
            # the point is to wait for a stream error
            self.assertEqual(res[1][0].name, 'features','Did not get initial features')

            d = self.send("<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='DIGEST-MD5'/>")
            d.addCallback(_testError)
            reactor.callLater(1, self.server_protocol.triggerChallenge)

            return d

        BOSH_XML = """<body content='text/xml; charset=utf-8'
      hold='1'
      rid='%(rid)i'
      to='localhost'
      route='xmpp:127.0.0.1:%(server_port)i'
      ver='1.6'
      wait='3'
      ack='1'
      xml:lang='en'
      xmlns='http://jabber.org/protocol/httpbind'/>
 """% { "rid": self.rid, "server_port": self.server_port }

        self.server_factory.protocol.delay_features = 10
        d = self.proxy.connect(BOSH_XML).addCallback(_testSessionCreate)
        # NOTE : to trigger this bug there needs to be 0 waiting requests.

        return d



########NEW FILE########
__FILENAME__ = xep206

import os
import sys
import time
from twisted.internet import defer, protocol, reactor
from twisted.python import log
from punjab.httpb import *
import test_basic

class DummyClient:
    """
    a client for testing
    """

class DummyTransport:
    """
    a transport for testing
    """



class XEP0206TestCase(test_basic.TestCase):
    """
    Tests for Punjab compatability with http://www.xmpp.org/extensions/xep-0206.html
    """

    def testCreateSession(self):

        def _testSessionCreate(res):
            self.failUnless(res[0].localPrefixes['xmpp'] == NS_XMPP, 'xmpp namespace not defined')
            self.failUnless(res[0].localPrefixes['stream'] == NS_FEATURES, 'stream namespace not defined')
            self.failUnless(res[0].hasAttribute((NS_XMPP, 'version')), 'version not found')

        BOSH_XML = """<body content='text/xml; charset=utf-8'
      hold='1'
      rid='1573741820'
      to='localhost'
      route='xmpp:127.0.0.1:%(server_port)i'
      secure='true'
      ver='1.6'
      wait='60'
      ack='1'
      xml:lang='en'
      xmlns='http://jabber.org/protocol/httpbind'/>
 """% { "server_port": self.server_port }

        d = self.proxy.connect(BOSH_XML).addCallback(_testSessionCreate)
        return d


########NEW FILE########
__FILENAME__ = punjab_plugin
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker

# Due to the directory layout, and the fact that plugin directories aren't
# modules (no __init__.py), this file is named something other than punjab.py,
# to ensure that this import pulls in the right module.
import punjab

class Options(usage.Options):
    optParameters = [
        ('host', None, 'localhost', "The hostname sent in the HTTP header of BOSH requests"),
        ('port', None, 5280, "HTTP Port for BOSH connections"),
        ('httpb', 'b', "http-bind", "URL path for BOSH resource."),
        ('polling', None, '15', "Seconds allowed between client polling requests"),
        ('html_dir', None, "./html", "The path were static html files are served."),
        ('ssl', None, None, "A flag to turn on ssl for BOSH requests"),
        ('ssl_privkey', None, "ssl.key", "SSL private key location"),
        ('ssl_cert', None, "ssl.crt", "SSL certificate location"),
        ('white_list', None, None,
            'Comma separated list of domains to allow connections to. \
            Begin an entry with a period to allow connections to subdomains. \
            e.g.: --white_list=.example.com,domain.com'),
        ('black_list', None, None,
         'Comma separated list of domains to deny connections to. ' \
         'Begin an entry with a period to deny connections to subdomains. '\
         'e.g.: --black_list=.example.com,domain.com'),
        ('site_log_file', None, None,
         'File path where the site access logs will be written. ' \
         'This overrides the twisted default logging. ' \
         'e.g.: --site_log_file=/var/log/punjab.access.log'),
    ]

    optFlags = [
        ('verbose', 'v', 'Show traffic and verbose logging.'),
    ]

class ServiceFactory(object):
    implements(IServiceMaker, IPlugin)
    tapname = "punjab"
    description = "A HTTP XMPP client interface"
    options = Options

    def makeService(self, options):
        return punjab.makeService(options)

service = ServiceFactory()


########NEW FILE########
