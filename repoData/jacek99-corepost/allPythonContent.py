__FILENAME__ = convert
'''
Created on 2011-10-11
@author: jacekf

Responsible for converting return values into cleanly serializable dict/tuples/lists
for JSON/XML/YAML output
'''

import collections
import logging
import json
from UserDict import DictMixin
from twisted.python import log

primitives = (int, long, float, bool, str,unicode)

def convertForSerialization(obj):
    """Converts anything (clas,tuples,list) to the safe serializable equivalent"""
    try:
        if type(obj) in primitives:
        # no conversion
            return obj 
        elif isinstance(obj, dict) or isinstance(obj,DictMixin):
            return traverseDict(obj)
        elif isClassInstance(obj):
            return convertClassToDict(obj)
        elif isinstance(obj,collections.Iterable) and not isinstance(obj,str):
            # iterable
            values = []
            for val in obj:
                values.append(convertForSerialization(val))
            return values
        else:
            # return as-is
            return obj
    except AttributeError as ex:
        log.msg(ex,logLevel=logging.WARN)
        return obj

def convertClassToDict(clazz):
    """Converts a class to a dictionary"""
    properties = {}
    for prop,val in clazz.__dict__.iteritems():
        #omit private fields
        if not prop.startswith("_"):
            properties[prop] = val

    return traverseDict(properties)

def traverseDict(dictObject):
    """Traverses a dict recursively to convertForSerialization any nested classes"""
    newDict = {}

    for prop,val in dictObject.iteritems():
        newDict[prop] = convertForSerialization(val)
    
    return newDict


def convertToJson(obj):
    """Converts to JSON, including Python classes that are not JSON serializable by default"""
    try:
        return json.dumps(obj)
    except Exception as ex:
        raise RuntimeError(str(ex))
    
def generateXml(obj):
    """Generates basic XML from an object that has already been converted for serialization"""
    if isinstance(obj, dict) or isinstance(obj,DictMixin):
        return getXML_dict(obj, "item")
    elif isinstance(obj,collections.Iterable):
        return "<list>%s</list>" % getXML(obj, "item")
    else:
        raise RuntimeError("Unable to convert to XML: %s" % obj)    
    
def isClassInstance(obj):
    """Checks if a given obj is a class instance"""
    return getattr(obj, "__class__",None) != None and not isinstance(obj,dict) and not isinstance(obj,tuple) and not isinstance(obj,list) and not isinstance(obj,str)

## {{{ http://code.activestate.com/recipes/440595/ (r2)
def getXML(obj, objname=None):
    """getXML(obj, objname=None)
    returns an object as XML where Python object names are the tags.
    
    >>> u={'UserID':10,'Name':'Mark','Group':['Admin','Webmaster']}
    >>> getXML(u,'User')
    '<User><UserID>10</UserID><Name>Mark</Name><Group>Admin</Group><Group>Webmaster</Group></User>'
    """
    if obj == None:
        return ""
    if not objname:
        objname = "item"
    adapt={
        dict: getXML_dict,
        list: getXML_list,
        tuple: getXML_list,
        }
    if adapt.has_key(obj.__class__):
        return adapt[obj.__class__](obj, objname)
    else:
        return "<%(n)s>%(o)s</%(n)s>"%{'n':objname,'o':str(obj)}

def getXML_dict(indict, objname=None):
    h = "<%s>"%objname
    for k, v in indict.items():
        h += getXML(v, k)
    h += "</%s>"%objname
    return h

def getXML_list(inlist, objname=None):
    h = ""
    for i in inlist:
        h += getXML(i, objname)
    return h
## end of http://code.activestate.com/recipes/440595/ }}}


########NEW FILE########
__FILENAME__ = enums
'''
Common enums

@author: jacekf
'''


class Http:
    """Enumerates HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"
    PATCH = "PATCH"


class HttpHeader:
    """Enumerates common HTTP headers"""
    CONTENT_TYPE = "content-type"
    ACCEPT = "accept"


class MediaType:
    """Enumerates media types"""
    WILDCARD = "*/*"
    APPLICATION_XML = "application/xml"
    APPLICATION_ATOM_XML = "application/atom+xml"
    APPLICATION_XHTML_XML = "application/xhtml+xml"
    APPLICATION_SVG_XML = "application/svg+xml"
    APPLICATION_JSON = "application/json"
    APPLICATION_FORM_URLENCODED = "application/x-www-form-urlencoded"
    MULTIPART_FORM_DATA = "multipart/form-data"
    APPLICATION_OCTET_STREAM = "application/octet-stream"
    TEXT_PLAIN = "text/plain"
    TEXT_XML = "text/xml"
    TEXT_HTML = "text/html"
    TEXT_YAML = "text/yaml"
########NEW FILE########
__FILENAME__ = zmq
__author__ = 'jacekf'

try:
    import txZMQ
except ImportError as ex:
    print "You must have ZeroMQ and txZMQ installed"
    raise ex

from corepost import Response, IRESTResource
from corepost.enums import Http
from corepost.routing import UrlRouter, RequestRouter
from enums import MediaType
from formencode import FancyValidator, Invalid
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from zope.interface import implements

class ZMQResource(Resource):
    """
    Responsible for intercepting HTTP requests and marshalling them via ZeroMQ to responders in the process pool
    """
    isLeaf = True
    implements(IRESTResource)

    def __init__(self):
        '''
        Constructor
        '''
        Resource.__init__(self)

    def render(self, request):
        """Posts request to ZeroMQ and waits for response"""
        pass


class ZMQResponder:
    """
    Responsible for processing an incoming request via ZeroMQ and responding via a REST API as if it were a direct HTTP request
    """
    def __init__(self,services=(),schema=None,filters=()):
        '''
        Constructor
        '''
        self.services = services
        self.__router = RequestRouter(self,schema,filters)

########NEW FILE########
__FILENAME__ = security
'''
Enhancements to core Twisted security
@author: jacekf
'''

from twisted.cred.checkers import ICredentialsChecker
from zope.interface import implements

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

class Principal:
    '''A security principal with privileges attached to it'''
    def __init__(self,userId,privileges=None):
        '''
        @param userId -- mandatory user ID
        @param privileges -- list of privileges assigned to this user
        '''
        self.__userId = userId
        self.__privileges = privileges
        
    @property
    def userId(self):
        return self.__userId

    @property
    def privileges(self):
        return self.__privileges

class CachedCredentialsChecker:
    """A cached credentials checker wrapper. It will forward calls to the actual credentials checker only when the cache expires (or on first call)"""
    implements(ICredentialsChecker)
    
    def __init__(self,credentialInterfaces,credentialsChecker):
        self.credentialInterfaces = credentialInterfaces
        self.checker = credentialsChecker
        
        #initialize cache
        cacheOptions = {
            'cache.type': 'memory',
        }
        self.cache = CacheManager(**parse_cache_config_options(cacheOptions))

    def requestAvatarId(self,credentials):
        pass

    
##################################################################################################
#
# DECORATORS
#
##################################################################################################    

def secured(privileges=None):
    '''
    Main decorator for securing REST endpoints via roles
    '''
    pass    
    
    
    
    
    
    
    
    
    
        
    
    
########NEW FILE########
__FILENAME__ = sql
'''
Created on 2012-04-17

@author: jacekf
'''

class SqlEntityService:
    pass

########NEW FILE########
__FILENAME__ = filters
'''
Various filters & interceptors
@author: jacekf
'''
from zope.interface import Interface

class IRequestFilter(Interface):
    """Request filter interface"""    
    def filterRequest(self,request):
        """Allows to intercept and change an incoming request"""
        pass

class IResponseFilter(Interface):
    """Response filter interface"""
    def filterResponse(self,request,response):
        """Allows to intercept and change an outgoing response"""
        pass

########NEW FILE########
__FILENAME__ = routing
'''
Created on 2011-10-03
@author: jacekf

Common routing classes, regardless of whether used in HTTP or multiprocess context
'''
from collections import defaultdict
from corepost import Response, RESTException
from corepost.enums import Http, HttpHeader
from corepost.utils import getMandatoryArgumentNames, safeDictUpdate
from corepost.convert import convertForSerialization, generateXml, convertToJson
from corepost.filters import IRequestFilter, IResponseFilter

from enums import MediaType
from twisted.internet import defer
from twisted.web.http import parse_qs
from twisted.python import log
import re, copy, exceptions, yaml,json, logging
from xml.etree import ElementTree
import uuid


class UrlRouter:
    ''' Common class for containing info related to routing a request to a function '''
    
    __urlMatcher = re.compile(r"<(int|float|uuid|):?([^/]+)>")
    __urlRegexReplace = {"":r"(?P<arg>([^/]+))","int":r"(?P<arg>\d+)","float":r"(?P<arg>\d+.?\d*)","uuid":r"(?P<arg>[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"}
    __typeConverters = {"int":int,"float":float,"uuid":uuid.UUID}
    
    def __init__(self,f,url,methods,accepts,produces,cache):
        self.__f = f
        self.__url = url
        self.__methods = methods if isinstance(methods,tuple) else (methods,)
        self.__accepts = accepts if isinstance(accepts,tuple) else (accepts,)
        self.__produces = produces
        self.__cache = cache
        self.__argConverters = {} # dict of arg names -> group index
        self.__validators = {}
        self.__mandatory = getMandatoryArgumentNames(f)[2:]
        
    def compileMatcherForFullUrl(self):
        """Compiles the regex matches once the URL has been updated to include the full path from the parent class"""
        #parse URL into regex used for matching
        m = UrlRouter.__urlMatcher.findall(self.url)
        self.__matchUrl = "^%s$" % self.url
        for match in m:
            if len(match[0]) == 0:
                # string
                self.__argConverters[match[1]] = None
                self.__matchUrl = self.__matchUrl.replace("<%s>" % match[1],
                                    UrlRouter.__urlRegexReplace[match[0]].replace("arg",match[1]))
            else:
                # non string
                self.__argConverters[match[1]] = UrlRouter.__typeConverters[match[0]]
                self.__matchUrl = self.__matchUrl.replace("<%s:%s>" % match,
                                    UrlRouter.__urlRegexReplace[match[0]].replace("arg",match[1]))

        self.__matcher = re.compile(self.__matchUrl)
        
        
    @property
    def cache(self):
        '''Indicates if this URL should be cached or not'''
        return self.__cache    

    @property
    def methods(self):
        return self.__methods
    
    @property
    def url(self):
        return self.__url

    @property
    def accepts(self):
        return self.__accepts

    def addValidator(self,fieldName,validator):
        '''Adds additional field-specific formencode validators'''
        self.__validators[fieldName] = validator
        
    def getArguments(self,url):
        '''
        Returns None if nothing matched (i.e. URL does not match), empty dict if no args found (i,e, static URL)
        or dict with arg/values for dynamic URLs
        '''
        g = self.__matcher.search(url)
        if g != None:
            args = g.groupdict()
            # convert to expected datatypes
            if len(args) > 0:
                for name in args.keys():
                    converter = self.__argConverters[name]
                    if converter != None:
                        args[name] = converter(args[name])
            return args
        else:
            return None
        
    def call(self,instance,request,**kwargs):
        '''Forwards call to underlying method'''
        for arg in self.__mandatory:
            if arg not in kwargs:
                raise TypeError("Missing mandatory argument '%s'" % arg)
        return self.__f(instance,request,**kwargs)
    
    def __str__(self):
        return "%s %s" % (self.url, self.methods) 

class UrlRouterInstance():
    """Combines a UrlRouter with a class instance it should be executed against"""
    def __init__(self,clazz,urlRouter):
        self.clazz = clazz
        self.urlRouter = urlRouter
        
    def __str__(self):
        return self.urlRouter.url

class CachedUrl:
    '''
    Used for caching URLs that have been already routed once before. Avoids the overhead
    of regex processing on every incoming call for commonly accessed REST URLs
    '''
    def __init__(self,urlRouterInstance,args):
        self.__urlRouterInstance = urlRouterInstance
        self.__args = args
        
    @property
    def urlRouterInstance(self):
        return self.__urlRouterInstance
    
    @property
    def args(self):
        return self.__args
    
class RequestRouter:
    '''
    Class that handles request->method routing functionality to any type of resource
    '''
    
    def __init__(self,restServiceContainer,schema=None,filters=()):
        '''
        Constructor
        '''
        self.__urls = {Http.GET: defaultdict(dict),Http.POST: defaultdict(dict),Http.PUT: defaultdict(dict),Http.DELETE: defaultdict(dict),Http.OPTIONS: defaultdict(dict),Http.PATCH: defaultdict(dict),Http.HEAD: defaultdict(dict)}
        self.__cachedUrls = {Http.GET: defaultdict(dict),Http.POST: defaultdict(dict),Http.PUT: defaultdict(dict),Http.DELETE: defaultdict(dict),Http.OPTIONS: defaultdict(dict),Http.PATCH: defaultdict(dict),Http.HEAD: defaultdict(dict)}
        self.__urlRouterInstances = {}
        self.__schema = schema
        self.__urlsMehods = {}
        self.__registerRouters(restServiceContainer)
        self.__urlContainer = restServiceContainer
        self.__requestFilters = []
        self.__responseFilters = []

        if filters != None:
            for webFilter in filters:
                valid = False
                if IRequestFilter.providedBy(webFilter):
                    self.__requestFilters.append(webFilter)
                    valid = True
                if IResponseFilter.providedBy(webFilter):
                    self.__responseFilters.append(webFilter)
                    valid = True

                if not valid:
                    raise RuntimeError("filter %s must implement IRequestFilter or IResponseFilter" % webFilter.__class__.__name__)

    @property
    def path(self):
        return self.__path

    def __registerRouters(self, restServiceContainer):
        """Main method responsible for registering routers"""
        from types import FunctionType

        for service in restServiceContainer.services:
            # check if the service has a root path defined, which is optional
            rootPath = service.__class__.path if "path" in service.__class__.__dict__ else ""
            
            for key in service.__class__.__dict__:
                func = service.__class__.__dict__[key]
                # handle REST resources directly on the CorePost resource
                if type(func) == FunctionType and hasattr(func,'corepostRequestRouter'):
                    # if specified, add class path to each function's path
                    rq = func.corepostRequestRouter
                    #workaround for multiple passes of __registerRouters (for unit tests etc)
                    if not hasattr(rq, 'urlAdapted'):
                        rq.url = "%s%s" % (rootPath,rq.url)
                        # remove first and trailing '/' to standardize URLs
                        start = 1 if rq.url[0:1] == "/" else 0
                        end =  -1 if rq.url[len(rq.url) -1] == '/' else len(rq.url)
                        rq.url = rq.url[start:end]
                        setattr(rq,'urlAdapted',True)

                    # now that the full URL is set, compile the matcher for it
                    rq.compileMatcherForFullUrl()
                    for method in rq.methods:
                        for accepts in rq.accepts:
                            urlRouterInstance = UrlRouterInstance(service,rq)
                            self.__urls[method][rq.url][accepts] = urlRouterInstance
                            self.__urlRouterInstances[func] = urlRouterInstance # needed so that we can lookup the urlRouterInstance for a specific function
                            if self.__urlsMehods.get(rq.url, None) is None:
                                self.__urlsMehods[rq.url] = []
                            self.__urlsMehods[rq.url].append(method)

    def getResponse(self,request):
        """Finds the appropriate instance and dispatches the request to the registered function. Returns the appropriate Response object"""
        # see if already cached
        response = None
        try:
            if len(self.__requestFilters) > 0:
                self.__filterRequests(request)

            # standardize URL and remove trailing "/" if necessary
            standardized_postpath = request.postpath if (request.postpath[-1] != '' or request.postpath == ['']) else request.postpath[:-1]
            path = '/'.join(standardized_postpath) 

            contentType =  MediaType.WILDCARD if HttpHeader.CONTENT_TYPE not in request.received_headers else request.received_headers[HttpHeader.CONTENT_TYPE]       

            urlRouterInstance, pathargs = None, None
            # fetch URL arguments <-> function from cache if hit at least once before
            if contentType in self.__cachedUrls[request.method][path]:
                cachedUrl = self.__cachedUrls[request.method][path][contentType]
                urlRouterInstance,pathargs = cachedUrl.urlRouterInstance, cachedUrl.args 
            else:
                # first time this URL is called
                instance = None

                # go through all the URLs, pick up the ones matching by content type
                # and then validate which ones match by path/argument to a particular UrlRouterInstance
                for contentTypeInstances in self.__urls[request.method].values():

                    if contentType in contentTypeInstances:
                        # there is an exact function for this incoming content type
                        instance = contentTypeInstances[contentType]
                    elif MediaType.WILDCARD in contentTypeInstances:
                        # fall back to any wildcard method
                        instance = contentTypeInstances[MediaType.WILDCARD]

                    if instance != None:
                        # see if the path arguments match up against any function @route definition
                        args = instance.urlRouter.getArguments(path)
                        if args != None:
                           
                            if instance.urlRouter.cache:
                                self.__cachedUrls[request.method][path][contentType] = CachedUrl(instance, args)
                            urlRouterInstance,pathargs = instance,args
                            break
            #actual call
            if urlRouterInstance != None and pathargs != None:
                allargs = copy.deepcopy(pathargs)
                
                try:
                    # if POST/PUT, check if we need to automatically parse JSON, YAML, XML
                    self.__parseRequestData(request)
                    # parse request arguments from form or JSON docss
                    self.__addRequestArguments(request, allargs)
                    urlRouter = urlRouterInstance.urlRouter
                    val = urlRouter.call(urlRouterInstance.clazz,request,**allargs)
                 
                    #handle Deferreds natively
                    if isinstance(val,defer.Deferred):
                        # add callback to finish the request
                        val.addCallback(self.__finishDeferred,request)
                        val.addErrback(self.__finishDeferredError,request)
                        return val
                    else:
                        #special logic for POST to return 201 (created)
                        if request.method == Http.POST:
                            if hasattr(request, 'code'):
                                if request.code == 200:
                                    request.setResponseCode(201) 
                            else:
                                request.setResponseCode(201)
                        
                        response = self.__generateResponse(request, val, request.code)
                    
                except exceptions.TypeError as ex:
                    log.msg(ex,logLevel=logging.WARN)
                    response = self.__createErrorResponse(request,400,"%s" % ex)

                except RESTException as ex:
                    """Convert REST exceptions to their responses. Input errors log at a lower level to avoid overloading logs"""
                    if (ex.response.code in (400,404)):
                        log.msg(ex,logLevel=logging.WARN)
                    else:
                        log.err(ex)
                    response = ex.response

                except Exception as ex:
                    log.err(ex)
                    response =  self.__createErrorResponse(request,500,"Unexpected server error: %s\n%s" % (type(ex),ex))
                    
            #if a url is defined, but not the requested method
            elif not request.method in self.__urlsMehods.get(path, []) and self.__urlsMehods.get(path, []) != []:
                
                response = self.__createErrorResponse(request,501, "")
            else:
                log.msg("URL %s not found" % path,logLevel=logging.WARN)
                response = self.__createErrorResponse(request,404,"URL '%s' not found\n" % request.path)
        
        except Exception as ex:
            log.err(ex)
            response = self.__createErrorResponse(request,500,"Internal server error: %s" % ex)
        
        # response handling
        if response != None and len(self.__responseFilters) > 0:
            self.__filterResponses(request,response)

        return response
    
    def __generateResponse(self,request,response,code=200):
        """
        Takes care of automatically rendering the response and converting it to appropriate format (text,XML,JSON,YAML)
        depending on what the caller can accept. Returns Response
        """
        if isinstance(response, str):
            return Response(code,response,{HttpHeader.CONTENT_TYPE: MediaType.TEXT_PLAIN})
        elif isinstance(response, Response):
            return response
        else:
            (content,contentType) = self.__convertObjectToContentType(request, response)
            return Response(code,content,{HttpHeader.CONTENT_TYPE:contentType})

    def __convertObjectToContentType(self,request,obj):
        """
        Takes care of converting an object (non-String) response to the appropriate format, based on the what the caller can accept.
        Returns a tuple of (content,contentType)
        """
        obj = convertForSerialization(obj)

        if HttpHeader.ACCEPT in request.received_headers:
            accept = request.received_headers[HttpHeader.ACCEPT]
            if MediaType.APPLICATION_JSON in accept:
                return (convertToJson(obj),MediaType.APPLICATION_JSON)
            elif MediaType.TEXT_YAML in accept:
                return (yaml.dump(obj),MediaType.TEXT_YAML)
            elif MediaType.APPLICATION_XML in accept or MediaType.TEXT_XML in accept:
                return (generateXml(obj),MediaType.APPLICATION_XML)
            else:
                # no idea, let's do JSON
                return (convertToJson(obj),MediaType.APPLICATION_JSON)
        else:
            # called has no accept header, let's default to JSON
            return (convertToJson(obj),MediaType.APPLICATION_JSON)

    def __finishDeferred(self,val,request):
        """Finishes any Defered/inlineCallback methods. Returns Response"""
        if isinstance(val,Response):
            return val
        elif val != None:
            try:
                return self.__generateResponse(request,val)
            except Exception as ex:
                msg = "Unexpected server error: %s\n%s" % (type(ex),ex)
                return self.__createErrorResponse(request, 500, msg)
        else:
            return Response(209,None)

    def __finishDeferredError(self,error,request):
        """Finishes any Defered/inlineCallback methods that raised an error. Returns Response"""
        log.err(error, "Deferred failed")
        return self.__createErrorResponse(request, 500,"Internal server error")

    def __createErrorResponse(self,request,code,message):
        """Common method for rendering errors"""
        return Response(code=code, entity=message, headers={"content-type": MediaType.TEXT_PLAIN})
 
    def __parseRequestData(self,request):
        '''Automatically parses JSON,XML,YAML if present'''
        if request.method in (Http.POST,Http.PUT) and HttpHeader.CONTENT_TYPE in request.received_headers.keys():
            contentType = request.received_headers["content-type"]
            request.data = request.content.read()

            if contentType == MediaType.APPLICATION_JSON:
                try:
                    request.json = json.loads(request.data) if request.data else {}
                except Exception as ex:
                    raise TypeError("Unable to parse JSON body: %s" % ex)
            elif contentType in (MediaType.APPLICATION_XML,MediaType.TEXT_XML):
                try: 
                    request.xml = ElementTree.XML(request.data)
                except Exception as ex:
                    raise TypeError("Unable to parse XML body: %s" % ex)
            elif contentType == MediaType.TEXT_YAML:
                try: 
                    request.yaml = yaml.safe_load(request.data)
                except Exception as ex:
                    raise TypeError("Unable to parse YAML body: %s" % ex)

    def __addRequestArguments(self,request,allargs):
        """Parses the request form arguments OR JSON document root elements to build the list of arguments to a method"""
        # handler for weird Twisted logic where PUT does not get form params
        # see: http://twistedmatrix.com/pipermail/twisted-web/2007-March/003338.html
        requestargs = request.args

        if request.method == Http.PUT and HttpHeader.CONTENT_TYPE in request.received_headers.keys() \
            and request.received_headers[HttpHeader.CONTENT_TYPE] == MediaType.APPLICATION_FORM_URLENCODED:
            # request.data is populated in __parseRequestData
            requestargs = parse_qs(request.data, 1)

        #merge form args
        if len(requestargs.keys()) > 0:
            for arg in requestargs.keys():
                # maintain first instance of an argument always
                safeDictUpdate(allargs,arg,requestargs[arg][0])
        elif hasattr(request,'json'):
            # if YAML parse root elements instead of form elements   
            for key in request.json.keys():
                safeDictUpdate(allargs, key, request.json[key])
        elif hasattr(request,'yaml'):
            # if YAML parse root elements instead of form elements   
            for key in request.yaml.keys():
                safeDictUpdate(allargs, key, request.yaml[key])
        elif hasattr(request,'xml'):
            # if XML, parse attributes first, then root nodes
            for key in request.xml.attrib:
                safeDictUpdate(allargs, key, request.xml.attrib[key])
            for el in request.xml.findall("*"):
                safeDictUpdate(allargs, el.tag,el.text)
        
            
    def __filterRequests(self,request):
        """Filters incoming requests"""
        for webFilter in self.__requestFilters:
            webFilter.filterRequest(request)
            
    def __filterResponses(self,request,response):
        """Filters incoming requests"""
        for webFilter in self.__responseFilters:
            webFilter.filterResponse(request,response)            
########NEW FILE########
__FILENAME__ = arguments
'''
Argument extraction tests
@author: jacekf
'''

from corepost.web import RESTResource, validate, route
from corepost.enums import Http
from formencode import Schema, validators

class TestSchema(Schema):
    allow_extra_fields = True
    childId = validators.Regex(regex="^jacekf|test$")

class ArgumentApp():
    
    @route("/int/<int:intarg>/float/<float:floatarg>/string/<stringarg>",Http.GET)
    def test(self,request,intarg,floatarg,stringarg,**kwargs):
        args = (intarg,floatarg,stringarg)
        return "%s" % map(lambda x: (type(x),x),args)
    
    @route("/validate/<int:rootId>/schema",Http.POST)
    @validate(schema=TestSchema())
    def postValidateSchema(self,request,rootId,childId,**kwargs):
        return "%s - %s - %s" % (rootId,childId,kwargs)
    
    @route("/validate/<int:rootId>/custom",Http.POST)
    @validate(childId=validators.Regex(regex="^jacekf|test$"))
    def postValidateCustom(self,request,rootId,childId,**kwargs):
        return "%s - %s - %s" % (rootId,childId,kwargs)

    @route("/formOrJson",Http.GET)
    def getArgumentsByContentType(self,request,first,last,**kwargs):
        return "%s %s" % (str(first),str(last))

    @route("/formOrJson",(Http.POST,Http.PUT))
    def postArgumentsByContentType(self,request,first,last,**kwargs):
        return "%s %s" % (str(first),str(last))


def run_app_arguments():
    app = RESTResource((ArgumentApp(),))
    app.run(8082)
########NEW FILE########
__FILENAME__ = zeromq_resource
'''
ZeroMQ resource

@author: jacekf
'''

from corepost.web import RESTResource, route
from corepost.enums import Http
from corepost.filters import IRequestFilter, IResponseFilter
from zope.interface import implements

from multiprocessing import Pool

class TestService:
    
    @route("/")
    def forward(self,request):
        return ""
    
def startClient():
    return "TEST"
    

def run_app_multicore():
    #start the ZeroMQ client
    pool = Pool(processes=4)
    
    #start the server
    app = RESTResource((TestService(),))
    app.run(8090)
                   
if __name__ == "__main__":
    run_app_multicore()    
    
    
########NEW FILE########
__FILENAME__ = filter_resource
'''
Server tests
@author: jacekf
'''

from corepost.web import RESTResource, route
from corepost.enums import Http
from corepost.filters import IRequestFilter, IResponseFilter
from zope.interface import implements

class AddCustomHeaderFilter():
    """Implements just a request filter"""
    implements(IRequestFilter)
    
    def filterRequest(self,request):
        request.received_headers["Custom-Header"] = "Custom Header Value"

class Change404to503Filter():
    """Implements just a response filter that changes 404 to 503 statuses"""
    implements(IResponseFilter)
    
    def filterResponse(self,request,response):
        if response.code == 404:
            response.code = 503

class WrapAroundFilter():
    """Implements both types of filters in one class"""
    implements(IRequestFilter,IResponseFilter)

    def filterRequest(self,request):
        del(request.received_headers["user-agent"]) # remove this for unit tests, it varies from one box to another
        request.received_headers["X-Wrap-Input"] = "Input"
    
    def filterResponse(self,request,response):
        response.headers["X-Wrap-Output"] = "Output"

class FilterService():
    path = "/"
    
    @route("/",Http.GET)
    def root(self,request,**kwargs):
        return request.received_headers

def run_filter_app():
    app = RESTResource(services=(FilterService(),),filters=(Change404to503Filter(),AddCustomHeaderFilter(),WrapAroundFilter(),))
    app.run(8083)
    
if __name__ == "__main__":
    run_filter_app()
########NEW FILE########
__FILENAME__ = home_resource
'''
Server tests
@author: jacekf
'''

from corepost.web import RESTResource, route
from corepost.enums import Http, MediaType, HttpHeader
from twisted.internet import defer
from xml.etree import ElementTree
import json, yaml

class HomeApp():
    
    def __init__(self,*args,**kwargs):
        self.issue1 = "issue 1"
    
    @route("/",Http.GET)
    @defer.inlineCallbacks
    def root(self,request,**kwargs):
        yield 1
        request.write("%s" % kwargs)
        request.finish()
    
    @route("/test",Http.GET)
    def test(self,request,**kwargs):
        return "%s" % kwargs
    
    @route("/test/<int:numericid>/resource/<stringid>",Http.GET)
    def test_get_resources(self,request,numericid,stringid,**kwargs):
        return "%s - %s" % (numericid,stringid)
    
    @route("/post",(Http.POST,Http.PUT))
    def test_post(self,request,**kwargs):
        return "%s" % kwargs
    
    @route("/put",(Http.POST,Http.PUT))
    def test_put(self,request,**kwargs):
        return "%s" % kwargs
    
    @route("/postput",(Http.POST,Http.PUT))
    def test_postput(self,request,**kwargs):
        return "%s" % kwargs
    
    @route("/delete",Http.DELETE)
    def test_delete(self,request,**kwargs):
        return "%s" % kwargs
    
    @route("/post/json",(Http.POST,Http.PUT))
    def test_json(self,request,**kwargs):
        return "%s" % json.dumps(request.json)

    @route("/post/xml",(Http.POST,Http.PUT))
    def test_xml(self,request,**kwargs):
        return "%s" % ElementTree.tostring(request.xml)

    @route("/post/yaml",(Http.POST,Http.PUT))
    def test_yaml(self,request,**kwargs):
        return "%s" % yaml.dump(request.yaml,indent=4,width=130,default_flow_style=False)

    ##################################################################
    # same URLs, routed by incoming content type
    ###################################################################
    @route("/post/by/content",(Http.POST,Http.PUT),MediaType.APPLICATION_JSON)
    def test_content_app_json(self,request,**kwargs):
        return request.received_headers[HttpHeader.CONTENT_TYPE]

    @route("/post/by/content",(Http.POST,Http.PUT),(MediaType.TEXT_XML,MediaType.APPLICATION_XML))
    def test_content_xml(self,request,**kwargs):
        return request.received_headers[HttpHeader.CONTENT_TYPE]

    @route("/post/by/content",(Http.POST,Http.PUT),MediaType.TEXT_YAML)
    def test_content_yaml(self,request,**kwargs):
        return request.received_headers[HttpHeader.CONTENT_TYPE]

    @route("/post/by/content",(Http.POST,Http.PUT))
    def test_content_catch_all(self,request,**kwargs):
        return MediaType.WILDCARD
    
    ##################################################################
    # one URL, serving different content types
    ###################################################################
    @route("/return/by/accept")
    def test_return_content_by_accepts(self,request,**kwargs):
        val = [{"test1":"Test1"},{"test2":"Test2"}]
        return val

    @route("/return/by/accept/deferred")
    @defer.inlineCallbacks
    def test_return_content_by_accept_deferred(self,request,**kwargs):
        """Ensure support for inline callbacks and deferred"""
        val = yield [{"test1":"Test1"},{"test2":"Test2"}]
        defer.returnValue(val) 

    @route("/return/by/accept/class")
    def test_return_class_content_by_accepts(self,request,**kwargs):
        """Uses Python class instead of dict/list"""
        
        class TestReturn:
            """Test return class"""
            def __init__(self):
                self.__t1 = 'Test'
        
        t1 = TestReturn()
        t1.test1 = 'Test1'
        
        t2 = TestReturn()
        t2.test2="Test2"
        return (t1,t2)

    ####################################
    # Issues
    ####################################
    @route("/issues/1")
    def test_issue_1(self,request,**kwargs):
        return self.issue1

    ####################################
    # extra HTTP methods
    ####################################
    @route("/methods/head",Http.HEAD)
    def test_head_http(self,request,**kwargs):
        return ""

    @route("/methods/options",Http.OPTIONS)
    def test_options_http(self,request,**kwargs):
        return "OPTIONS"

    @route("/methods/patch",Http.PATCH)
    def test_patch_http(self,request,**kwargs):
        return "PATCH=%s" % kwargs

def run_app_home():
    app = RESTResource((HomeApp(),))
    app.run()
    
if __name__ == "__main__":
    run_app_home()
########NEW FILE########
__FILENAME__ = multi_resource
'''
A RESTResource module1 that can be merged into the main RESTResource Resource
'''

from corepost.web import RESTResource, route
from corepost.enums import Http

class HomeApp():

    @route("/")
    def home_root(self,request,**kwargs):
        return "HOME %s" % kwargs

class Module1():
    path = "/module1"

    @route("/",Http.GET)
    def module1_get(self,request,**kwargs):
        return request.path
    
    @route("/sub",Http.GET)
    def module1e_sub(self,request,**kwargs):
        return request.path

class Module2():
    path = "/module2"
    
    @route("/",Http.GET)
    def module2_get(self,request,**kwargs):
        return request.path
    
    @route("/sub",Http.GET)
    def module2_sub(self,request,**kwargs):
        return request.path

def run_app_multi():
    app = RESTResource((HomeApp(),Module1(),Module2()))
    app.run(8081)
                   
if __name__ == "__main__":
    run_app_multi()
########NEW FILE########
__FILENAME__ = rest_resource
'''
Server tests
@author: jacekf
'''

from corepost import Response, NotFoundException, AlreadyExistsException
from corepost.web import RESTResource, route, Http 

from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import FilePasswordDB
from twisted.web.static import File
from twisted.web.resource import IResource
from twisted.web.guard import HTTPAuthSessionWrapper, BasicCredentialFactory

from zope.interface import implements

# Security

# Database
class DB():
    """Fake in-memory DB for testing"""
    customers = {}

    @classmethod
    def getAllCustomers(cls):
        return DB.customers.values()

    @classmethod
    def getCustomer(cls,customerId):
        if customerId in DB.customers:
            return DB.customers[customerId]
        else:
            raise NotFoundException("Customer",customerId)

    @classmethod
    def saveCustomer(cls,customer):
        if customer.customerId in DB.customers:
            raise AlreadyExistsException("Customer",customer.customerId)
        else:
            DB.customers[customer.customerId] = customer

    @classmethod
    def deleteCustomer(cls,customerId):
        if customerId in DB.customers:
            del(DB.customers[customerId])
        else:
            raise NotFoundException("Customer",customerId)

    @classmethod
    def deleteAllCustomers(cls):
        DB.customers.clear()

    @classmethod
    def getCustomerAddress(cls,customerId,addressId):
        c = DB.getCustomer(customerId)
        if addressId in c.addresses:
            return c.addresses[addressId]
        else:
            raise NotFoundException("Customer Address",addressId)


class Customer:
    """Represents customer entity"""
    def __init__(self,customerId,firstName,lastName):
        (self.customerId,self.firstName,self.lastName) = (customerId,firstName,lastName)
        self.addresses = {}

class CustomerAddress:
    """Represents customer address entity"""
    def __init__(self,streetNumber,streetName,stateCode,countryCode):
        (self.streetNumber,self.streetName,self.stateCode,self.countryCode) = (streetNumber,streetName,stateCode,countryCode)

class CustomerRESTService():
    path = "/customer"

    @route("/")
    def getAll(self,request):
        return DB.getAllCustomers()
    
    @route("/<customerId>")
    def get(self,request,customerId):
        return DB.getCustomer(customerId)
    
    @route("/",Http.POST)
    def post(self,request,customerId,firstName,lastName):
        customer = Customer(customerId, firstName, lastName)
        DB.saveCustomer(customer)
        return Response(201)
    
    @route("/<customerId>",Http.PUT)        
    def put(self,request,customerId,firstName,lastName):
        c = DB.getCustomer(customerId)
        (c.firstName,c.lastName) = (firstName,lastName)
        return Response(200)

    @route("/<customerId>",Http.DELETE)
    def delete(self,request,customerId):
        DB.deleteCustomer(customerId)
        return Response(200)
    
    @route("/",Http.DELETE)
    def deleteAll(self,request):
        DB.deleteAllCustomers()
        return Response(200)

class CustomerAddressRESTService():
    path = "/customer/<customerId>/address"

    @route("/")
    def getAll(self,request,customerId):
        return DB.getCustomer(customerId).addresses
    
    @route("/<addressId>")
    def get(self,request,customerId,addressId):
        return DB.getCustomerAddress(customerId, addressId)
    
    @route("/",Http.POST)
    def post(self,request,customerId,addressId,streetNumber,streetName,stateCode,countryCode):
        c = DB.getCustomer(customerId)
        address = CustomerAddress(streetNumber,streetName,stateCode,countryCode)
        c.addresses[addressId] = address
        return Response(201)
    
    @route("/<addressId>",Http.PUT)        
    def put(self,request,customerId,addressId,streetNumber,streetName,stateCode,countryCode):
        address = DB.getCustomerAddress(customerId, addressId)
        (address.streetNumber,address.streetName,address.stateCode,address.countryCode) = (streetNumber,streetName,stateCode,countryCode)
        return Response(200)

    @route("/<addressId>",Http.DELETE)
    def delete(self,request,customerId,addressId):
        DB.getCustomerAddress(customerId, addressId) #validate address exists
        del(DB.getCustomer(customerId).addresses[addressId])
        return Response(200)
    
    @route("/",Http.DELETE)
    def deleteAll(self,request,customerId):
        c = DB.getCustomer(customerId)
        c.addresses = {}
        return Response(200)

def run_rest_app():
    app = RESTResource((CustomerRESTService(),CustomerAddressRESTService()))
    app.run(8085)
    
if __name__ == "__main__":
    run_rest_app()
########NEW FILE########
__FILENAME__ = sql_resource
'''
Created on 2012-04-17

@author: jacekf
'''
from corepost.web import route
from twisted.python.constants import NamedConstant, Names

class REST_METHOD(Names):
    GET_ALL = NamedConstant()
    GET_ONE = NamedConstant()
    POST = NamedConstant()
    PUT = NamedConstant()
    DELETE = NamedConstant()
    DELETE_ALL = NamedConstant()
    ALL = NamedConstant()

class DatabaseRegistry:

    __registry = {}

    @classmethod
    def getConnection(cls,name=None):
        return DatabaseRegistry.__registery[name]
    
    @classmethod
    def registerPool(cls,name,dbPool):
        """Registers a DB connection pool under an appropriate name"""
        DatabaseRegistry.__registry[name] = dbPool
        
    @classmethod
    def getManager(cls,name=None,queriesFile=None):
        """Returns the high-level SQL data manager for easy SQL manipulation"""
        pass

class SqlDataManager:
    
    def __init__(self,table,columnMapping={}):
        pass    
    
class CustomerSqlService:
    path = "/customer"
    entityId ="<customerId>"
    dataManager = DatabaseRegistry.getManager("customer")
    methods = (REST_METHOD.GET_ONE,REST_METHOD.POST,REST_METHOD.PUT,REST_METHOD.DELETE)

class CustomerAddressSqlService:
    path = "/customer/<customerId>/address"
    entityId = "<addressId>"
    dataManager = DatabaseRegistry.getManager("customer_address")
    methods = (REST_METHOD.ALL,)
    

########NEW FILE########
__FILENAME__ = steps
'''
Common Freshen BDD steps

@author: jacekf
'''
from multiprocessing import Process
import httplib2, json, re, time, string
from freshen import Before, Given, When, Then, scc, glc, assert_equals, assert_true #@UnresolvedImport
from urllib import urlencode
from corepost.test.home_resource import run_app_home
from corepost.test.multi_resource import run_app_multi
from corepost.test.arguments import run_app_arguments
from corepost.test.filter_resource import run_filter_app
from corepost.test.rest_resource import run_rest_app

apps = {'home_resource' : run_app_home,'multi_resource':run_app_multi,'arguments':run_app_arguments, 'filter_resource':run_filter_app,'rest_resource':run_rest_app}

NULL = 'None'

def as_dict(parameters):
    dict_val = {}
    for pair in parameters.split('&') : 
        params = pair.split('=', 1)
        if (params[0] != None) and (len(params) == 2):
            dict_val[params[0]] = params[1]
    return dict_val

##################################
# BEFORE / AFTER
##################################

@Before
def setup(slc):
    scc.http_headers = {}

##################################
# GIVEN
##################################

@Given(r"^'(.+)' is running\s*$")
def given_process_is_running(processname):
    if glc.processes == None:
        glc.processes = {}

    if processname not in glc.processes:
        # start a process only once, keep it running
        # to make test runs faster
        process = Process(target=apps[processname])
        process.daemon = True
        process.start()
        time.sleep(0.25) # let it start up
        glc.processes[processname] = process

##################################
# WHEN
##################################

@When(r"^as user '(.+):(.+)' I (GET|DELETE|HEAD|OPTIONS) '(.+)'\s*$")
def when_as_user_i_send_get_delete_to_url(user,password,method,url):
    h = httplib2.Http()
    h.follow_redirects = False
    h.add_credentials(user, password)
    scc.response, scc.content = h.request(url, method, headers = scc.http_headers)

@When(r"^as user '(.+):(.+)' I (POST|PUT|PATCH) '(.+)' with '(.+)'\s*$")
def when_as_user_i_send_post_put_to_url(user,password,method,url,params):
    h = httplib2.Http()
    h.follow_redirects = False
    h.add_credentials(user, password)
    scc.http_headers['Content-type'] = 'application/x-www-form-urlencoded'
    scc.response, scc.content = h.request(url, method, urlencode(as_dict(params)), headers = scc.http_headers)

@When(r"^as user '(.+):(.+)' I (POST|PUT) '(.+)' with (XML|JSON|YAML) body '(.+)'\s*$")
def when_as_user_i_send_post_put_xml_json_to_url(user,password,method,url,request_type,body):
    when_as_user_i_send_post_put_xml_json_to_url_multiline(body,user,password,method,url,request_type)

@When(r"^as user '(.+):(.+)' I (POST|PUT) '(.+)' with (XML|JSON|YAML)\s*$")
def when_as_user_i_send_post_put_xml_json_to_url_multiline(body,user,password,method,url,request_type):
    h = httplib2.Http()
    h.follow_redirects = False
    h.add_credentials(user, password)
    if request_type == "JSON":
        scc.http_headers['Content-type'] = 'application/json'
    elif request_type == "XML":
        scc.http_headers['Content-type'] = 'text/xml'
    elif request_type == "YAML":
        scc.http_headers['Content-type'] = 'text/yaml'        
    scc.response, scc.content = h.request(url, method, body, headers = scc.http_headers)

@When("I prepare HTTP header '(.*)' = '(.*)'")
def when_i_define_http_header_with_value(header,value):
    if header != NULL:
        scc.http_headers[header] = value

##################################
# THEN
##################################
def transform_content(content):
    """Support embedded newlines"""
    if content != None:
        return string.replace(content,"\\n","\n")
    else:
        return None

@Then(r"^I expect HTTP code (\d+)\s*$")
def expect_http_code(code):
    assert_equals(int(code),int(scc.response.status), msg="%s != %s\n%s\n%s" % (code,scc.response.status,scc.response,scc.content))

@Then(r"^I expect content contains '(.+)'\s*$")
def expect_content(content):
    content = transform_content(content)
    assert_true(scc.content.find(content) >= 0,"Did not find:\n%s\nin content:\n%s" % (content,scc.content)) 

@Then(r"^I expect content contains\s*$")
def expect_content_multiline(content):
    content = transform_content(content)
    assert_true(scc.content.find(content) >= 0,"Did not find:\n%s\nin content:\n%s" % (content,scc.content)) 

@Then(r"^I expect '([^']*)' header matches '([^']*)'\s*$")
def then_check_http_header_matches(header,regex):
    assert_true(re.search(regex,scc.response[header.lower()], re.X | re.I) != None, 
                "the regex %s does not match the response\n%s" % (regex, scc.response[header.lower()])) 

@Then("^I expect JSON content\s*$")
def then_i_expect_json(content):
    expected_json = json.loads(content) 
    expected_json_sorted = json.dumps(expected_json,sort_keys=True,indent=4)
    received_json = json.loads(scc.content)
    received_json_sorted = json.dumps(received_json,sort_keys=True,indent=4)
    assert_equals(expected_json_sorted,received_json_sorted,"Expected JSON\n%s\n*** actual ****\n%s" % (expected_json_sorted,received_json_sorted))


########NEW FILE########
__FILENAME__ = utils
'''
Various CorePost utilities
'''
from inspect import getargspec


def getMandatoryArgumentNames(f):
    '''Returns a tuple of the mandatory arguments required in a function'''
    args,_,_,defaults = getargspec(f)
    if defaults == None:
        return args
    else:
        return args[0:len(args) - len(defaults)]


def getRouterKey(method,url):
    '''Returns the common key used to represent a function that a request can be routed to'''
    return "%s %s" % (method,url)


def checkExpectedInterfaces(objects,expectedInterface):
    """Verifies that all the objects implement the expected interface"""
    for obj in objects:
        if not expectedInterface.providedBy(obj):
            raise RuntimeError("Object %s does not implement %s interface" % (obj,expectedInterface))

def safeDictUpdate(dictObject,key,value):
    """Only adds a key to a dictionary. If key exists, it leaves it untouched"""
    if key not in dictObject:
        dictObject[key] = value

########NEW FILE########
__FILENAME__ = web
'''
Main server classes

@author: jacekf
'''
from corepost import Response, IRESTResource
from corepost.enums import Http
from corepost.routing import UrlRouter, RequestRouter
from enums import MediaType
from formencode import FancyValidator, Invalid
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from zope.interface import implements

#########################################################
#
# CLASSES
#
#########################################################
    
class RESTResource(Resource):
    '''
    Main resource responsible for routing REST requests to the implementing methods
    '''
    isLeaf = True
    implements(IRESTResource)
    
    def __init__(self,services=(),schema=None,filters=()):
        '''
        Constructor
        '''
        self.services = services
        self.__router = RequestRouter(self,schema,filters)
        Resource.__init__(self)

    def render_GET(self,request):
        """ Handles all GET requests """
        return self.__renderUrl(request)
    
    def render_POST(self,request):
        """ Handles all POST requests"""
        return self.__renderUrl(request)
    
    def render_PUT(self,request):
        """ Handles all PUT requests"""
        return self.__renderUrl(request)
    
    def render_DELETE(self,request):
        """ Handles all DELETE requests"""
        return self.__renderUrl(request)
    
    def __renderUrl(self,request):
        try:
            val = self.__router.getResponse(request)

            # return can be Deferred or Response
            if isinstance(val,Deferred):
                val.addCallback(self.__finishRequest,request)
                return NOT_DONE_YET
            elif isinstance(val,Response):
                self.__applyResponse(request, val.code, val.headers)
                return val.entity
            else:
                raise RuntimeError("Unexpected return type from request router %s" % val)
        except Exception as ex:
            self.__applyResponse(request, 500, None)
            return str(ex)
        
    def __finishRequest(self,response,request):
        if not request.finished:
            self.__applyResponse(request, response.code,response.headers)
            request.write(response.entity)
            request.finish()
        
    def __applyResponse(self,request,code,headers={"content-type":MediaType.TEXT_PLAIN}):
        request.setResponseCode(code)
        if headers != None:
            for header,value in headers.iteritems():
                request.setHeader(header, value)
                
    def run(self,port=8080):
        """Shortcut for running app within Twisted reactor"""
        factory = Site(self)
        reactor.listenTCP(port, factory)    #@UndefinedVariable
        reactor.run()                       #@UndefinedVariable

##################################################################################################
#
# DECORATORS
#
##################################################################################################    

def route(url,methods=(Http.GET,),accepts=MediaType.WILDCARD,produces=None,cache=True):
    '''
    Main decorator for registering REST functions
    '''
    def decorator(f):
        def wrap(*args,**kwargs):
            return f
        router = UrlRouter(f, url, methods, accepts, produces, cache)
        setattr(wrap,'corepostRequestRouter',router)
        
        return wrap
    return decorator
    
def validate(schema=None,**vKwargs):
    '''
    Main decorator for registering additional validators for incoming URL arguments
    '''
    def fn(realfn):  
        def wrap(*args,**kwargs):
            # first run schema validation, then the custom validators
            errors = []
            if schema != None:
                try:
                    schema.to_python(kwargs)
                except Invalid as ex:
                    for arg, error in ex.error_dict.items():
                        errors.append("%s: %s ('%s')" % (arg,error.msg,error.value))
             
            # custom validators    
            for arg in vKwargs.keys():
                validator = vKwargs[arg]
                if arg in kwargs:
                    val = kwargs[arg]
                    try:
                        validator.to_python(val)
                    except Invalid as ex:
                        errors.append("%s: %s ('%s')" % (arg,ex,val))
                else:
                    if isinstance(validator,FancyValidator) and validator.not_empty:
                        raise TypeError("Missing mandatory argument '%s'" % arg)
            
            # fire error if anything failed validation
            if len(errors) > 0:
                raise TypeError('\n'.join(errors))
            # all OK
            return realfn(*args,**kwargs)
        return wrap
    return fn    

########NEW FILE########
