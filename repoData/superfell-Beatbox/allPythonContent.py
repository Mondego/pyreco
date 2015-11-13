__FILENAME__ = beatbox
"""beatbox: Makes the salesforce.com SOAP API easily accessible."""

__version__ = "0.95"
__author__ = "Simon Fell"
__credits__ = "Mad shouts to the sforce possie"
__copyright__ = "(C) 2006-2013 Simon Fell. GNU GPL 2."

import sys
import httplib
from urlparse import urlparse
from StringIO import StringIO
import gzip
import datetime
import xmltramp
from xmltramp import islst
from xml.sax.saxutils import XMLGenerator
from xml.sax.saxutils import quoteattr
from xml.sax.xmlreader import AttributesNSImpl

# global constants for namespace strings, used during serialization
_partnerNs = "urn:partner.soap.sforce.com"
_sobjectNs = "urn:sobject.partner.soap.sforce.com"
_envNs = "http://schemas.xmlsoap.org/soap/envelope/"
_noAttrs = AttributesNSImpl({}, {})

# global constants for xmltramp namespaces, used to access response data
_tPartnerNS = xmltramp.Namespace(_partnerNs)
_tSObjectNS = xmltramp.Namespace(_sobjectNs)
_tSoapNS = xmltramp.Namespace(_envNs)

# global config
gzipRequest=True	# are we going to gzip the request ?
gzipResponse=True	# are we going to tell the server to gzip the response ?
forceHttp=False		# force all connections to be HTTP, for debugging


def makeConnection(scheme, host, timeout=1200):
	kwargs = {} if sys.version_info<(2,6,0) else {'timeout':timeout}
	if forceHttp or scheme.upper() == 'HTTP':
		return httplib.HTTPConnection(host, **kwargs)
	return httplib.HTTPSConnection(host, **kwargs)


# the main sforce client proxy class
class Client:
	def __init__(self):
		self.batchSize = 500
		self.serverUrl = "https://login.salesforce.com/services/Soap/u/28.0"
		self.__conn = None
		self.timeout = 15
		
	def __del__(self):
		if self.__conn != None:
			self.__conn.close()
			
	# login, the serverUrl and sessionId are automatically handled, returns the loginResult structure		
	def login(self, username, password):
		lr = LoginRequest(self.serverUrl, username, password).post()
		self.useSession(str(lr[_tPartnerNS.sessionId]), str(lr[_tPartnerNS.serverUrl]))
		return lr

	# perform a portal login, orgId is always needed, portalId is needed for new style portals
	# is not required for the old self service portal
	# for the self service portal, only the login request will work, self service users don't
	# get API access, for new portals, the users should have API acesss, and can call the rest 
	# of the API.
	def portalLogin(self, username, password, orgId, portalId):
		lr = PortalLoginRequest(self.serverUrl, username, password, orgId, portalId).post()
		self.useSession(str(lr[_tPartnerNS.sessionId]), str(lr[_tPartnerNS.serverUrl]))
		return lr
		
	# initialize from an existing sessionId & serverUrl, useful if we're being launched via a custom link	
	def useSession(self, sessionId, serverUrl):
		self.sessionId = sessionId
		self.__serverUrl = serverUrl
		(scheme, host, path, params, query, frag) = urlparse(self.__serverUrl)
		self.__conn = makeConnection(scheme, host)

	# calls logout which invalidates the current sessionId, in general its better to not call this and just 
	# let the sessions expire on their own.
	def logout(self):
		return LogoutRequest(self.__serverUrl, self.sessionId).post(self.__conn, True)
		
	# set the batchSize property on the Client instance to change the batchsize for query/queryMore
	def query(self, soql):
		return QueryRequest(self.__serverUrl, self.sessionId, self.batchSize, soql).post(self.__conn)
	
	# query include deleted and archived rows.
	def queryAll(self, soql):
		return QueryRequest(self.__serverUrl, self.sessionId, self.batchSize, soql, "queryAll").post(self.__conn)
		
	def queryMore(self, queryLocator):
		return QueryMoreRequest(self.__serverUrl, self.sessionId, self.batchSize, queryLocator).post(self.__conn)
	
	def search(self, sosl):
		return SearchRequest(self.__serverUrl, self.sessionId, sosl).post(self.__conn)
			
	def getUpdated(self, sObjectType, start, end):
		return GetUpdatedRequest(self.__serverUrl, self.sessionId, sObjectType, start, end).post(self.__conn)
		
	def getDeleted(self, sObjectType, start, end):
		return GetDeletedRequest(self.__serverUrl, self.sessionId, sObjectType, start, end).post(self.__conn)
				
	def retrieve(self, fields, sObjectType, ids):
		return RetrieveRequest(self.__serverUrl, self.sessionId, fields, sObjectType, ids).post(self.__conn)

	# sObjects can be 1 or a list, returns a single save result or a list
	def create(self, sObjects):
		return CreateRequest(self.__serverUrl, self.sessionId, sObjects).post(self.__conn)

	# sObjects can be 1 or a list, returns a single save result or a list
	def update(self, sObjects):
		return UpdateRequest(self.__serverUrl, self.sessionId, sObjects).post(self.__conn)
		
	# sObjects can be 1 or a list, returns a single upsert result or a list
	def upsert(self, externalIdName, sObjects):
		return UpsertRequest(self.__serverUrl, self.sessionId, externalIdName, sObjects).post(self.__conn)	
	
	# ids can be 1 or a list, returns a single delete result or a list
	def delete(self, ids):
		return DeleteRequest(self.__serverUrl, self.sessionId, ids).post(self.__conn)

	# ids can be 1 or a list, returns a single delete result or a list
	def undelete(self, ids):
		return UndeleteRequest(self.__serverUrl, self.sessionId, ids).post(self.__conn)
	
	# leadConverts can be 1 or a list of dictionaries, each dictionary should be filled out as per the LeadConvert type in the WSDL.
	# 	<element name="accountId"              type="tns:ID" nillable="true"/>
    # 	<element name="contactId"              type="tns:ID" nillable="true"/>
    # 	<element name="convertedStatus"        type="xsd:string"/>
    # 	<element name="doNotCreateOpportunity" type="xsd:boolean"/>
    # 	<element name="leadId"                 type="tns:ID"/>
    # 	<element name="opportunityName"        type="xsd:string" nillable="true"/>
    # 	<element name="overwriteLeadSource"    type="xsd:boolean"/>
    # 	<element name="ownerId"                type="tns:ID"     nillable="true"/>
    # 	<element name="sendNotificationEmail"  type="xsd:boolean"/>
	def convertLead(self, leadConverts):
		return ConvertLeadRequest(self.__serverUrl, self.sessionId, leadConverts).post(self.__conn)
		
	# sObjectTypes can be 1 or a list, returns a single describe result or a list of them
	def describeSObjects(self, sObjectTypes):
		return DescribeSObjectsRequest(self.__serverUrl, self.sessionId, sObjectTypes).post(self.__conn)
		
	def describeGlobal(self):
		return AuthenticatedRequest(self.__serverUrl, self.sessionId, "describeGlobal").post(self.__conn)

	def describeLayout(self, sObjectType):
		return DescribeLayoutRequest(self.__serverUrl, self.sessionId, sObjectType).post(self.__conn)
		
	def describeTabs(self):
		return AuthenticatedRequest(self.__serverUrl, self.sessionId, "describeTabs").post(self.__conn, True)

	def describeSearchScopeOrder(self):
		return AuthenticatedRequest(self.__serverUrl, self.sessionId, "describeSearchScopeOrder").post(self.__conn, True)

	def describeQuickActions(self, actions):
		return DescribeQuickActionsRequest(self.__serverUrl, self.sessionId, actions).post(self.__conn, True)
	
	def describeAvailableQuickActions(self, parentType = None):
		return DescribeAvailableQuickActionsRequest(self.__serverUrl, self.sessionId, parentType).post(self.__conn, True)
	
	def performQuickActions(self, actions):
		return PerformQuickActionsRequest(self.__serverUrl, self.sessionId, actions).post(self.__conn, True)
		
	def getServerTimestamp(self):
		return str(AuthenticatedRequest(self.__serverUrl, self.sessionId, "getServerTimestamp").post(self.__conn)[_tPartnerNS.timestamp])
		
	def resetPassword(self, userId):
		return ResetPasswordRequest(self.__serverUrl, self.sessionId, userId).post(self.__conn)
		
	def setPassword(self, userId, password):
		SetPasswordRequest(self.__serverUrl, self.sessionId, userId, password).post(self.__conn)
		
	def getUserInfo(self):
		return AuthenticatedRequest(self.__serverUrl, self.sessionId, "getUserInfo").post(self.__conn)

	#def convertLead(self, convertLeads):

# fixed version of XmlGenerator, handles unqualified attributes correctly
class BeatBoxXmlGenerator(XMLGenerator):
	def __init__(self, destination, encoding):
		XMLGenerator.__init__(self, destination, encoding)
	
	def makeName(self, name):	
		if name[0] is None:
			#if the name was not namespace-scoped, use the qualified part
			return name[1]
		# else try to restore the original prefix from the namespace
		return self._current_context[name[0]] + ":" + name[1]
		
	def startElementNS(self, name, qname, attrs):
		self._write(unicode('<' + self.makeName(name)))
		
		for pair in self._undeclared_ns_maps:
			self._write(unicode(' xmlns:%s="%s"' % pair))
		self._undeclared_ns_maps = []
		
		for (name, value) in attrs.items():
			self._write(unicode(' %s=%s' % (self.makeName(name), quoteattr(value))))
		self._write(unicode('>'))

# general purpose xml writer, does a bunch of useful stuff above & beyond XmlGenerator
class XmlWriter:			
	def __init__(self, doGzip):
		self.__buf = StringIO("")
		if doGzip:
			self.__gzip = gzip.GzipFile(mode='wb', fileobj=self.__buf)
			stm = self.__gzip
		else:
			stm = self.__buf
			self.__gzip = None
		self.xg = BeatBoxXmlGenerator(stm, "utf-8")
		self.xg.startDocument()
		self.__elems = []

	def startPrefixMapping(self, prefix, namespace):
		self.xg.startPrefixMapping(prefix, namespace)
	
	def endPrefixMapping(self, prefix):
		self.xg.endPrefixMapping(prefix)
		
	def startElement(self, namespace, name, attrs = _noAttrs):
		self.xg.startElementNS((namespace, name), name, attrs)
		self.__elems.append((namespace, name))

	# if value is a list, then it writes out repeating elements, one for each value
	def writeStringElement(self, namespace, name, value, attrs = _noAttrs):
		if islst(value):
			for v in value:
				self.writeStringElement(namespace, name, v, attrs)
		else:
			self.startElement(namespace, name, attrs)
			self.characters(value)
			self.endElement()

	def endElement(self):
		e = self.__elems[-1];
		self.xg.endElementNS(e, e[1])
		del self.__elems[-1]

	def characters(self, s):
		# todo base64 ?
		if isinstance(s, datetime.datetime):
			# todo, timezones
			s = s.isoformat()
		elif isinstance(s, datetime.date):
			# todo, try isoformat
			s = "%04d-%02d-%02d" % (s.year, s.month, s.day)
		elif isinstance(s, int):
			s = str(s)
		elif isinstance(s, float):
			s = str(s)
		self.xg.characters(s)

	def endDocument(self):
		self.xg.endDocument()
		if (self.__gzip != None):
			self.__gzip.close();
		return self.__buf.getvalue()

# exception class for soap faults
class SoapFaultError(Exception):
	def __init__(self, faultCode, faultString):
		self.faultCode = faultCode
		self.faultString = faultString
			
	def __str__(self):
		return repr(self.faultCode) + " " + repr(self.faultString)
		
# soap specific stuff ontop of XmlWriter
class SoapWriter(XmlWriter):
	__xsiNs = "http://www.w3.org/2001/XMLSchema-instance"
	
	def __init__(self):
		XmlWriter.__init__(self, gzipRequest)
		self.startPrefixMapping("s", _envNs)
		self.startPrefixMapping("p", _partnerNs)
		self.startPrefixMapping("o", _sobjectNs)
		self.startPrefixMapping("x", SoapWriter.__xsiNs)
		self.startElement(_envNs, "Envelope")
	
	def writeStringElement(self, namespace, name, value, attrs = _noAttrs):
		if value is None:
			if attrs:
				attrs[(SoapWriter.__xsiNs, "nil")] = 'true';
			else:
				attrs = { (SoapWriter.__xsiNs, "nil") : 'true' }
			value = ""
		XmlWriter.writeStringElement(self, namespace, name, value, attrs)
		
	def endDocument(self):
		self.endElement()  # envelope
		self.endPrefixMapping("o")
		self.endPrefixMapping("p")
		self.endPrefixMapping("s")
		self.endPrefixMapping("x")
		return XmlWriter.endDocument(self)	

# processing for a single soap request / response		
class SoapEnvelope:
	def __init__(self, serverUrl, operationName, clientId="BeatBox/" + __version__):
		self.serverUrl = serverUrl
		self.operationName = operationName
		self.clientId = clientId

	def writeHeaders(self, writer):
		pass

	def writeBody(self, writer):
		pass

	def makeEnvelope(self):
		s = SoapWriter()
		s.startElement(_envNs, "Header")
		s.characters("\n")
		s.startElement(_partnerNs, "CallOptions")
		s.writeStringElement(_partnerNs, "client", self.clientId)
		s.endElement()
		s.characters("\n")
		self.writeHeaders(s)
		s.endElement()	# Header
		s.startElement(_envNs, "Body")
		s.characters("\n")
		s.startElement(_partnerNs, self.operationName)
		self.writeBody(s)
		s.endElement()	# operation
		s.endElement()  # body
		return s.endDocument()

	# does all the grunt work, 
	#   serializes the request, 
	#   makes a http request, 
	#   passes the response to tramp
	#   checks for soap fault
	#   todo: check for mU='1' headers
	#   returns the relevant result from the body child
	def post(self, conn=None, alwaysReturnList=False):
		headers = { "User-Agent": "BeatBox/" + __version__,
					"SOAPAction": "\"\"",
					"Content-Type": "text/xml; charset=utf-8" }
		if gzipResponse:
			headers['accept-encoding'] = 'gzip'
		if gzipRequest:
			headers['content-encoding'] = 'gzip'					
		close = False
		(scheme, host, path, params, query, frag) = urlparse(self.serverUrl)
		if conn == None:
			conn = makeConnection(scheme, host)
			close = True
		rawRequest = self.makeEnvelope();
		# print rawRequest
		conn.request("POST", path, rawRequest, headers)
		response = conn.getresponse()
		rawResponse = response.read()
		if response.getheader('content-encoding','') == 'gzip':
			rawResponse = gzip.GzipFile(fileobj=StringIO(rawResponse)).read()
		if close:
			conn.close()
		tramp = xmltramp.parse(rawResponse)
		try:
			faultString = str(tramp[_tSoapNS.Body][_tSoapNS.Fault].faultstring)
			faultCode   = str(tramp[_tSoapNS.Body][_tSoapNS.Fault].faultcode).split(':')[-1]
			raise SoapFaultError(faultCode, faultString)
		except KeyError:
			pass
		# first child of body is XXXXResponse
		result = tramp[_tSoapNS.Body][0]
		# it contains either a single child, or for a batch call multiple children
		if alwaysReturnList or len(result) > 1:
			return result[:]
		else:
			return result[0]
	

class LoginRequest(SoapEnvelope):
	def __init__(self, serverUrl, username, password):
		SoapEnvelope.__init__(self, serverUrl, "login")
		self.__username = username
		self.__password = password

	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "username", self.__username)
		s.writeStringElement(_partnerNs, "password", self.__password)

class PortalLoginRequest(LoginRequest):
	def __init__(self, serverUrl, username, password, orgId, portalId):
		LoginRequest.__init__(self, serverUrl, username, password)
		self.__orgId = orgId
		self.__portalId = portalId
	
	def writeHeaders(self, s):
		s.startElement(_partnerNs, "LoginScopeHeader")
		s.writeStringElement(_partnerNs, "organizationId", self.__orgId)
		if (not (self.__portalId is None or self.__portalId == "")):
			s.writeStringElement(_partnerNs, "portalId", self.__portalId)
		s.endElement()
		
# base class for all methods that require a sessionId
class AuthenticatedRequest(SoapEnvelope):
	def __init__(self, serverUrl, sessionId, operationName):
		SoapEnvelope.__init__(self, serverUrl, operationName)
		self.sessionId = sessionId

	def writeHeaders(self, s):
		s.startElement(_partnerNs, "SessionHeader")
		s.writeStringElement(_partnerNs, "sessionId", self.sessionId)
		s.endElement()

	def writeDict(self, s, elemName, d):
		if islst(d):
			for o in d:
				self.writeDict(s, elemName, o)
		else:
			s.startElement(_partnerNs, elemName)
			for fn in d.keys():
				if (isinstance(d[fn], dict)):
					self.writeDict(s, d[fn], fn)
				else:
					s.writeStringElement(_sobjectNs, fn, d[fn])
			s.endElement()

	def writeSObjects(self, s, sObjects, elemName="sObjects"):
		if islst(sObjects):
			for o in sObjects:
				self.writeSObjects(s, o, elemName)
		else:
			s.startElement(_partnerNs, elemName)
			# type has to go first
			s.writeStringElement(_sobjectNs, "type", sObjects['type'])
			for fn in sObjects.keys():
				if (fn != 'type'):
					if (isinstance(sObjects[fn],dict)):
						self.writeSObjects(s, sObjects[fn], fn)
					else:
						s.writeStringElement(_sobjectNs, fn, sObjects[fn])
			s.endElement()
	
class LogoutRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, "logout")


class QueryOptionsRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, batchSize, operationName):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, operationName)
		self.batchSize = batchSize
		
	def writeHeaders(self, s):
		AuthenticatedRequest.writeHeaders(self, s)
		s.startElement(_partnerNs, "QueryOptions")
		s.writeStringElement(_partnerNs, "batchSize", self.batchSize)
		s.endElement()
		
		
class QueryRequest(QueryOptionsRequest):
	def __init__(self, serverUrl, sessionId, batchSize, soql, operationName="query"):
		QueryOptionsRequest.__init__(self, serverUrl, sessionId, batchSize, operationName)
		self.__query = soql
				
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "queryString", self.__query)


class QueryMoreRequest(QueryOptionsRequest):
	def __init__(self, serverUrl, sessionId, batchSize, queryLocator):
		QueryOptionsRequest.__init__(self, serverUrl, sessionId, batchSize, "queryMore")
		self.__queryLocator = queryLocator
		
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "queryLocator", self.__queryLocator)
		
		
class SearchRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, sosl):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, "search")
		self.__query = sosl
	
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "searchString", self.__query)
		
		
class GetUpdatedRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, sObjectType, start, end, operationName="getUpdated"):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, operationName)
		self.__sObjectType = sObjectType
		self.__start = start;
		self.__end = end;
		
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "sObjectType", self.__sObjectType)
		s.writeStringElement(_partnerNs, "startDate", self.__start)
		s.writeStringElement(_partnerNs, "endDate", self.__end)						
			

class GetDeletedRequest(GetUpdatedRequest):
	def __init__(self, serverUrl, sessionId, sObjectType, start, end):
		GetUpdatedRequest.__init__(self, serverUrl, sessionId, sObjectType, start, end, "getDeleted")

	
class UpsertRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, externalIdName, sObjects):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, "upsert")
		self.__externalIdName = externalIdName
		self.__sObjects = sObjects
		
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "externalIDFieldName", self.__externalIdName)
		self.writeSObjects(s, self.__sObjects)


class UpdateRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, sObjects, operationName="update"):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, operationName)
		self.__sObjects = sObjects
		
	def writeBody(self, s):
		self.writeSObjects(s, self.__sObjects)
				

class CreateRequest(UpdateRequest):		
	def __init__(self, serverUrl, sessionId, sObjects):
		UpdateRequest.__init__(self, serverUrl, sessionId, sObjects, "create")
		

class DeleteRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, ids, operationName="delete"):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, operationName)
		self.__ids = ids;
		
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "id", self.__ids)

class UndeleteRequest(DeleteRequest):
	def __init__(self, serverUrl, sessionId, ids):
		DeleteRequest.__init__(self, serverUrl, sessionId, ids, "undelete")
					
		
class RetrieveRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, fields, sObjectType, ids):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, "retrieve")
		self.__fields = fields
		self.__sObjectType = sObjectType
		self.__ids = ids
		
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "fieldList", self.__fields)
		s.writeStringElement(_partnerNs, "sObjectType", self.__sObjectType);
		s.writeStringElement(_partnerNs, "ids", self.__ids)
			
		
class ResetPasswordRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, userId):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, "resetPassword")
		self.__userId = userId
		
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "userId", self.__userId)
		

class SetPasswordRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, userId, password):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, "setPassword")
		self.__userId = userId
		self.__password = password
		
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "userId", self.__userId)
		s.writeStringElement(_partnerNs, "password", self.__password)	
		

class ConvertLeadRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, leadConverts):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, "convertLead")
		self.__leads = leadConverts
	
	def writeBody(self, s):
		self.writeDict(s, "leadConverts", self.__leads)


class DescribeSObjectsRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, sObjectTypes):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, "describeSObjects")
		self.__sObjectTypes = sObjectTypes
	
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "sObjectType", self.__sObjectTypes)
			
		
class DescribeLayoutRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, sObjectType):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, "describeLayout")
		self.__sObjectType = sObjectType
		
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "sObjectType", self.__sObjectType)


class DescribeQuickActionsRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, actions):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, "describeQuickActions")
		self.__actions = actions
		
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "action", self.__actions)

class DescribeAvailableQuickActionsRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, parentType):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, "describeAvailableQuickActions")
		self.__parentType = parentType
		
	def writeBody(self, s):
		s.writeStringElement(_partnerNs, "parentType", self.__parentType)
		
class PerformQuickActionsRequest(AuthenticatedRequest):
	def __init__(self, serverUrl, sessionId, actions):
		AuthenticatedRequest.__init__(self, serverUrl, sessionId, "performQuickActions")
		self.__actions = actions
		
	def writeBody(self, s):
		if (islst(self.__actions)):
			for action in self.__actions:
				self.writeQuckAction(s, action)
		else:
			self.writeQuickAction(s, self.__actions)

	def writeQuickAction(self, s, action):
		s.startElement(_partnerNs, "quickActions")
		s.writeStringElement(_partnerNs, "parentId", action.get("parentId"))
		s.writeStringElement(_partnerNs, "quickActionName", action["quickActionName"])
		self.writeSObjects(s, action["records"], "records")
		s.endElement()

########NEW FILE########
__FILENAME__ = demo
# demonstration of using the BeatBox library to call the sforce API

import sys
import beatbox
import xmltramp
import datetime

sf = beatbox._tPartnerNS
svc = beatbox.Client()
beatbox.gzipRequest=False

class BeatBoxDemo:
	def login(self, username, password):
		self.password = password
		loginResult = svc.login(username, password)
		print "sid = " + str(loginResult[sf.sessionId])
		print "welcome " + str(loginResult[sf.userInfo][sf.userFullName])
	
	def getServerTimestamp(self):
		print "\ngetServerTimestamp " + svc.getServerTimestamp()
	
	def describeGlobal(self):
		print "\ndescribeGlobal"
		dg = svc.describeGlobal()
		for t in dg[sf.sobjects:]:
			print str(t[sf.name]) + " \t " + str(t[sf.label])

	def describeTabs(self):
		print "\ndescribeTabs"
		dt = svc.describeTabs()
		for t in dt:
			print str(t[sf.label])

	def describeSearchScopeOrder(self):
		print "\ndescribeSearchScopeOrder"
		types = svc.describeSearchScopeOrder()
		for t in types:
			print "\t" + str(t[sf.name]) + " : " + str(t[sf.keyPrefix])
			
	def dumpQueryResult(self, qr):
		print "query size = " + str(qr[sf.size])
	
		for rec in qr[sf.records:]:
			print str(rec[0]) + " : " + str(rec[2]) + " : " + str(rec[3])
	
		if (str(qr[sf.done]) == 'false'):
			print "\nqueryMore"
			qr = svc.queryMore(str(qr[sf.queryLocator]))
			for rec in qr[sf.records:]:
				print str(rec[0]) + " : " + str(rec[2]) + " : " + str(rec[3])

	def query(self):
		print "\nquery"			
		qr = svc.query("select Id, Name from Account")
		self.dumpQueryResult(qr)

	def queryAll(self):
		print "\nqueryAll"
		qr = svc.queryAll("select id, isDeleted from Account")
		self.dumpQueryResult(qr)
		
	def search(self):				
		print "\nsearch"
		sr = svc.search("find {Apple*} in all fields")
		for rec in sr[sf.searchRecords:]:
			r = rec[sf.record]
			print str(r[0]) + "\t: " + str(r[2])

	def upsert(self):
		print "\nupsert"
		t = { 'type': 'Task', 
			  'ChandlerId__c': '12345', 
			  'subject': 'BeatBoxTest updated', 
			  'ActivityDate' : datetime.date(2006,2,20) }
	
		ur = svc.upsert('ChandlerId__c', t)
		print str(ur[sf.success]) + " -> " + str(ur[sf.id])
	
		t = { 	'type': 'Event', 
			'ChandlerId__c': '67890', 
			'durationinminutes': 45, 
			'subject': 'BeatBoxTest', 
			'ActivityDateTime' : datetime.datetime(2006,2,20,13,30,30),
			'IsPrivate': False }
		ur = svc.upsert('ChandlerId__c', t)
		if str(ur[sf.success]) == 'true':
			print "id " + str(ur[sf.id])
		else:
			print "error " + str(ur[sf.errors][sf.statusCode]) + ":" + str(ur[sf.errors][sf.message])

	def update(self):
		print "\nupdate"
		a = { 'type': 'Account',
			  'Id':   self.__idToDelete,
			  'Name': 'BeatBoxBaby',
			  'NumberofLocations__c': 123.456 }
		sr = svc.update(a)

		if str(sr[sf.success]) == 'true':
			print "id " + str(sr[sf.id])
		else:
			print "error " + str(sr[sf.errors][sf.statusCode]) + ":" + str(sr[sf.errors][sf.message])
    	
	def create(self):
		print "\ncreate"
		a = { 'type': 'Account',
			'Name': 'New Account',
			'Website': 'http://www.pocketsoap.com/' }
		sr = svc.create([a])

		if str(sr[sf.success]) == 'true':
			print "id " + str(sr[sf.id])
			self.__idToDelete = str(sr[sf.id])
		else:
			print "error " + str(sr[sf.errors][sf.statusCode]) + ":" + str(sr[sf.errors][sf.message])
    
    
	def getUpdated(self):
		print "\ngetUpdated"
		updatedIds = svc.getUpdated("Account", datetime.datetime.today()-datetime.timedelta(1), datetime.datetime.today()+datetime.timedelta(1))
		self.__theIds = []
		for id in updatedIds[sf.ids:]:
			print "getUpdated " + str(id)
			self.__theIds.append(str(id))

	def delete(self):
		print "\ndelete"
		dr = svc.delete(self.__idToDelete)
		if str(dr[sf.success]) == 'true':
			print "deleted id " + str(dr[sf.id])
		else:
			print "error " + str(dr[sf.errors][sf.statusCode]) + ":" + str(dr[sf.errors][sf.message])
	
	def undelete(self):
		print "\nundelete"
		dr = svc.undelete(self.__idToDelete)
		if (str(dr[sf.success])) == 'true':
			print "undeleted id " + str(dr[sf.id])
		else:
			print "error " + str(dr[sf.errors][sf.statusCode]) + ":" + str(dr[sf.errors][sf.message])

	def getDeleted(self):
		print "\ngetDeleted"
		drs = svc.getDeleted("Account", datetime.datetime.today()-datetime.timedelta(1), datetime.datetime.today()+datetime.timedelta(1))
		print "latestDate Covered : " + str(drs[sf.latestDateCovered])
		for dr in drs[sf.deletedRecords:]:
			print "getDeleted " + str(dr[sf.id]) + " on " + str(dr[sf.deletedDate])

	def retrieve(self):
		print "\nretrieve"
		accounts = svc.retrieve("id, name", "Account", self.__theIds)
		for acc in accounts:
			if len(acc._dir) > 0:
				print str(acc[beatbox._tSObjectNS.Id]) + " : " + str(acc[beatbox._tSObjectNS.Name])
			else:
				print "<null>"
			
			
	def getUserInfo(self):			
		print "\ngetUserInfo"
		ui = svc.getUserInfo()
		print "hello " + str(ui[sf.userFullName]) + " from " + str(ui[sf.organizationName])
	
	def resetPassword(self):
		ui = svc.getUserInfo()
		print "\nresetPassword"
		pr = svc.resetPassword(str(ui[sf.userId]))
		print "password reset to " + str(pr[sf.password])
	
		print "\nsetPassword"
		svc.setPassword(str(ui[sf.userId]), self.password)
		print "password set back to original password"
	
	def convertLead(self):
		print "\nconvertLead"
		lead = { 'type' : 'Lead', 
				 'LastName' : 'Fell', 
				 'Company' : '@superfell' }
		leadId = str(svc.create(lead)[sf.id])
		print "created new lead with id " + leadId
		convert = { 'leadId' : leadId,
					'convertedStatus' : 'Closed - Converted',
					'doNotCreateOpportunity' : 'true' }
		res = svc.convertLead(convert)
		print "converted lead to contact with Id " + str(res[sf.contactId])
					
	def describeSObjects(self):
		print "\ndescribeSObjects(Account)"
		desc = svc.describeSObjects("Account")
		for f in desc[sf.fields:]:
			print "\t" + str(f[sf.name])

		print "\ndescribeSObjects(Lead, Contact)"
		desc = svc.describeSObjects(["Lead", "Contact"])
		for d in desc:
			print str(d[sf.name]) + "\n" + ( "-" * len(str(d[sf.name])))
			for f in d[sf.fields:]:
				print "\t" + str(f[sf.name])
		
	def describeLayout(self):		
		print "\ndescribeLayout(Account)"
		desc = svc.describeLayout("Account")
		for layout in desc[sf.layouts:]:
			print "sections in detail layout " + str(layout[sf.id])
			for s in layout[sf.detailLayoutSections:]:
				print "\t" + str(s[sf.heading])
			
			
			
if __name__ == "__main__":

	if len(sys.argv) != 3:
		print "usage is demo.py <username> <password>"
	else:
		demo = BeatBoxDemo()
		demo.login(sys.argv[1], sys.argv[2])
		demo.getServerTimestamp()
		demo.getUserInfo()
		demo.convertLead()
		#demo.resetPassword()
		demo.describeGlobal()
		demo.describeSearchScopeOrder()
		demo.describeTabs()
		demo.describeSObjects()
		demo.describeLayout()
		demo.query()
		demo.upsert()
		demo.create()
		demo.update()
		demo.getUpdated()
		demo.delete()
		demo.getDeleted()
		demo.queryAll()
		demo.undelete()
		demo.retrieve()
		demo.search()
		
########NEW FILE########
__FILENAME__ = export
# runs a sforce SOQL query and saves the results as a csv file.
import sys
import string
import beatbox
import xmltramp

sf = beatbox._tPartnerNS
svc = beatbox.Client()

def buildSoql(sobjectName):
	dr = svc.describeSObjects(sobjectName)
	soql = ""
	for f in dr[sf.fields:]:
		if len(soql) > 0: soql += ','
		soql += str(f[sf.name])
	return "select " + soql + " from " + sobjectName

def printColumnHeaders(queryResult):
	needsComma = 0
	# note that we offset 2 into the records child collection to skip the type and base sObject id elements
	for col in queryResult[sf.records][2:]:
		if needsComma: print ',',
		else: needsComma = 1
		print col._name[1],
	print
		
def export(username, password, objectOrSoql):
	svc.login(username, password)
	if string.find(objectOrSoql, ' ') < 0:
		soql = buildSoql(objectOrSoql)
	else:
		soql = objectOrSoql
	
	qr = svc.query(soql)
	printHeaders = 1
	while True:
		if printHeaders: printColumnHeaders(qr); printHeaders = 0
		for row in qr[sf.records:]:
			needsComma = False
			for col in row[2:]:
				if needsComma: print ',',
				else: needsComma = True
				print str(col),
			print
		if str(qr[sf.done]) == 'true': break
		qr = svc.queryMore(str(qr[sf.queryLocator]))

if __name__ == "__main__":

	if len(sys.argv) != 4:
		print "usage is export.py <username> <password> [<sobjectName> || <soqlQuery>]"
	else:
		export(sys.argv[1], sys.argv[2], sys.argv[3])

########NEW FILE########
__FILENAME__ = portal_login_demo
# demonstration of using the BeatBox library to authentication a portal user

import sys
import beatbox
import xmltramp
import datetime

sf = beatbox._tPartnerNS
svc = beatbox.Client()

class BeatBoxDemo:
	def login(self, username, password, orgId, portalId):
		loginResult = svc.portalLogin(username, password, orgId, portalId)
		print str(loginResult[sf.sessionId])
	
if __name__ == "__main__":

	if len(sys.argv) <4 or len(sys.argv) > 5:
		print "usage is login_portal.py <username> <password> <orgId> {portalId}"
	else:
		demo = BeatBoxDemo()
		portalId = None
		if len(sys.argv) > 4:
			portalId = sys.argv[4]
		demo.login(sys.argv[1], sys.argv[2], sys.argv[3], portalId)

########NEW FILE########
__FILENAME__ = setstatus
# demonstration of using the BeatBox library to call the sforce API, this will update your chatter status

import sys
import beatbox
import xmltramp
import datetime

sf = beatbox._tPartnerNS
svc = beatbox.Client()

if __name__ == "__main__":

	if len(sys.argv) != 4:
		print "usage is setstatus.py <username> <password> <new status>"
	else:
		loginResult = svc.login(sys.argv[1], sys.argv[2])
		print "welcome " + str(loginResult[sf.userInfo][sf.userFullName])
		user = { 'type' : 'FeedItem',
				 'parentId'   	: str(loginResult[sf.userId]),
				 'body' 		: sys.argv[3] }
		r = svc.create(user)
		if (str(r[sf.success]) == 'false'):
			print "error updating status:" + str(r[sf.errors][sf.statusCode]) + ":" + str(r[sf.errors][sf.message])
		else:
			print "success!"

########NEW FILE########
__FILENAME__ = soql2atom
#!/usr/bin/python

"""soql2atom: a beatbox demo that generates an atom 1.0 formatted feed of any SOQL query (requires beatbox 0.9 or later)

   The fields Id, SystemModStamp and CreatedDate are automatically added to the SOQL if needed.
   The first field in the select list becomes the title of the entry, so make sure to setup the order of the fields as you need.
   The soql should be passed via a 'soql' queryString parameter
   Optionally, you can also pass a 'title' queryString parameter to set the title of the feed

   The script forces authentication, but many apache installations are configured to block the AUTHORIZATION header,
   so the scirpt looks for X_HTTP_AUTHORIZATION instead, you can use a mod_rewrite rule to manage the mapping, something like this

   Options +FollowSymLinks
   RewriteEngine on
   RewriteRule ^(.*)$ soql2atom.py [E=X-HTTP_AUTHORIZATION:%{HTTP:Authorization},QSA,L]

   I have this in a .htaccess file in the same directory as soql2atom.py etc.
"""

__version__ = "1.0"
__author__ = "Simon Fell"
__copyright__ = "(C) 2006 Simon Fell. GNU GPL 2."

import sys
import beatbox
import cgi
import cgitb
from xml.sax.xmlreader import AttributesNSImpl
import datetime
from urlparse import urlparse
import os 
import base64
import string

cgitb.enable()
sf = beatbox._tPartnerNS
svc = beatbox.Client()
_noAttrs = beatbox._noAttrs

def addRequiredFieldsToSoql(soql):
	findPos = string.find(string.lower(soql), "from")
	selectList = []
	for f in string.lower(soql)[:findPos].split(","):
		selectList.append(string.strip(f))
	if not "id" in selectList: selectList.append("Id")
	if not "systemmodstamp" in selectList: selectList.append("systemModStamp")
	if not "createddate" in selectList: selectList.append("createdDate")
	return string.join(selectList, ", ") + soql[findPos-1:]
			
def soql2atom(loginResult, soql, title):
	soqlWithFields = addRequiredFieldsToSoql(soql)
	userInfo = loginResult[beatbox._tPartnerNS.userInfo]
	serverUrl = str(loginResult[beatbox._tPartnerNS.serverUrl])
	(scheme, host, path, params, query, frag) = urlparse(serverUrl)
	sfbaseUrl = scheme + "://" + host + "/"
	thisUrl = "http://" + os.environ["HTTP_HOST"] + os.environ["REQUEST_URI"]
	qr = svc.query(soqlWithFields)
	
	atom_ns = "http://www.w3.org/2005/Atom"
	ent_ns = "urn:sobject.enterprise.soap.sforce.com"

	print "content-type: application/atom+xml"
	doGzip = os.environ.has_key("HTTP_ACCEPT_ENCODING") and "gzip" in string.lower(os.environ["HTTP_ACCEPT_ENCODING"]).split(',')
	if (doGzip): print "content-encoding: gzip"
	print ""
	x = beatbox.XmlWriter(doGzip)
	x.startPrefixMapping("a", atom_ns)
	x.startPrefixMapping("s", ent_ns)
	x.startElement(atom_ns, "feed")
	x.writeStringElement(atom_ns, "title", title)
	x.characters("\n")
	x.startElement(atom_ns, "author")
	x.writeStringElement(atom_ns, "name", str(userInfo.userFullName))
	x.endElement()
	x.characters("\n")
	rel = AttributesNSImpl( {(None, "rel"): "self", (None, "href") : thisUrl}, 
						    {(None, "rel"): "rel",  (None, "href"): "href"})
	x.startElement(atom_ns, "link", rel)
	x.endElement()
	x.writeStringElement(atom_ns, "updated", datetime.datetime.utcnow().isoformat() +"Z") 
	x.writeStringElement(atom_ns, "id", thisUrl + "&userid=" + str(loginResult[beatbox._tPartnerNS.userId]))
	x.characters("\n")
	type = AttributesNSImpl({(None, u"type") : "html"}, {(None, u"type") : u"type" })
	for row in qr[sf.records:]:
		x.startElement(atom_ns, "entry")
		desc = ""
		x.writeStringElement(atom_ns, "title", str(row[2]))
		for col in row[2:]:
			if col._name[1] == 'Id':
				x.writeStringElement(atom_ns, "id", sfbaseUrl + str(col))
				writeLink(x, atom_ns, "link", "alternate", "text/html", sfbaseUrl + str(col))
			elif col._name[1] == 'SystemModstamp':
				x.writeStringElement(atom_ns, "updated", str(col))
			elif col._name[1] == 'CreatedDate':
				x.writeStringElement(atom_ns, "published", str(col))
			elif str(col) != "":
				desc = desc + "<b>" + col._name[1] + "</b> : " + str(col) + "<br>"
				x.writeStringElement(ent_ns, col._name[1], str(col))
		x.startElement(atom_ns, "content", type)
		x.characters(desc)
		x.endElement() # content
		x.characters("\n")
		x.endElement() # entry
	x.endElement() # feed
	print x.endDocument()

def writeLink(x, namespace, localname, rel, type, href):
	rel = AttributesNSImpl( {(None, "rel"): rel,   (None, "href"): href,   (None, "type"): type }, 
						    {(None, "rel"): "rel", (None, "href"): "href", (None, "type"): "type"})
	x.startElement(namespace, localname, rel)
	x.endElement()

def authenticationRequired(message="Unauthorized"):
	print "status: 401 Unauthorized"
	print "WWW-authenticate: Basic realm=""www.salesforce.com"""
	print "content-type: text/plain"
	print ""
	print message

if not os.environ.has_key('X_HTTP_AUTHORIZATION') or os.environ['X_HTTP_AUTHORIZATION'] == '':
	authenticationRequired()
else:
	auth = os.environ['X_HTTP_AUTHORIZATION']
	(username, password) = base64.decodestring(auth.split(" ")[1]).split(':')
	form = cgi.FieldStorage()
	if not form.has_key('soql'): raise Exception("Must provide the SOQL query to run via the soql queryString parameter")
	soql = form.getvalue("soql")
	title = "SOQL2ATOM : " + soql
	if form.has_key("title"):
		title = form.getvalue("title")
	try:
		lr = svc.login(username, password)	
		soql2atom(lr, soql, title)
	except beatbox.SoapFaultError, sfe:
		if (sfe.faultCode == 'INVALID_LOGIN'):
			authenticationRequired(sfe.faultString)
		else:
			raise
			
########NEW FILE########
__FILENAME__ = xmltramp
"""xmltramp: Make XML documents easily accessible."""

__version__ = "2.18"
__author__ = "Aaron Swartz"
__credits__ = "Many thanks to pjz, bitsko, and DanC."
__copyright__ = "(C) 2003-2006 Aaron Swartz. GNU GPL 2."

if not hasattr(__builtins__, 'True'): True, False = 1, 0
def isstr(f): return isinstance(f, type('')) or isinstance(f, type(u''))
def islst(f): return isinstance(f, type(())) or isinstance(f, type([]))

empty = {'http://www.w3.org/1999/xhtml': ['img', 'br', 'hr', 'meta', 'link', 'base', 'param', 'input', 'col', 'area']}

def quote(x, elt=True):
	if elt and '<' in x and len(x) > 24 and x.find(']]>') == -1: return "<![CDATA["+x+"]]>"
	else: x = x.replace('&', '&amp;').replace('<', '&lt;').replace(']]>', ']]&gt;')
	if not elt: x = x.replace('"', '&quot;')
	return x

class Element:
	def __init__(self, name, attrs=None, children=None, prefixes=None):
		if islst(name) and name[0] == None: name = name[1]
		if attrs:
			na = {}
			for k in attrs.keys():
				if islst(k) and k[0] == None: na[k[1]] = attrs[k]
				else: na[k] = attrs[k]
			attrs = na
		
		self._name = name
		self._attrs = attrs or {}
		self._dir = children or []
		
		prefixes = prefixes or {}
		self._prefixes = dict(zip(prefixes.values(), prefixes.keys()))
		
		if prefixes: self._dNS = prefixes.get(None, None)
		else: self._dNS = None
	
	def __repr__(self, recursive=0, multiline=0, inprefixes=None):
		def qname(name, inprefixes): 
			if islst(name):
				if inprefixes[name[0]] is not None:
					return inprefixes[name[0]]+':'+name[1]
				else:
					return name[1]
			else:
				return name
		
		def arep(a, inprefixes, addns=1):
			out = ''

			for p in self._prefixes.keys():
				if not p in inprefixes.keys():
					if addns: out += ' xmlns'
					if addns and self._prefixes[p]: out += ':'+self._prefixes[p]
					if addns: out += '="'+quote(p, False)+'"'
					inprefixes[p] = self._prefixes[p]
			
			for k in a.keys():
				out += ' ' + qname(k, inprefixes)+ '="' + quote(a[k], False) + '"'
			
			return out
		
		inprefixes = inprefixes or {u'http://www.w3.org/XML/1998/namespace':'xml'}
		
		# need to call first to set inprefixes:
		attributes = arep(self._attrs, inprefixes, recursive) 
		out = '<' + qname(self._name, inprefixes)  + attributes 
		
		if not self._dir and (self._name[0] in empty.keys() 
		  and self._name[1] in empty[self._name[0]]):
			out += ' />'
			return out
		
		out += '>'

		if recursive:
			content = 0
			for x in self._dir: 
				if isinstance(x, Element): content = 1
				
			pad = '\n' + ('\t' * recursive)
			for x in self._dir:
				if multiline and content: out +=  pad 
				if isstr(x): out += quote(x)
				elif isinstance(x, Element):
					out += x.__repr__(recursive+1, multiline, inprefixes.copy())
				else:
					raise TypeError, "I wasn't expecting "+`x`+"."
			if multiline and content: out += '\n' + ('\t' * (recursive-1))
		else:
			if self._dir: out += '...'
		
		out += '</'+qname(self._name, inprefixes)+'>'
			
		return out
	
	def __unicode__(self):
		text = ''
		for x in self._dir:
			text += unicode(x)
		return ' '.join(text.split())
		
	def __str__(self):
		return self.__unicode__().encode('utf-8')
	
	def __getattr__(self, n):
		if n[0] == '_': raise AttributeError, "Use foo['"+n+"'] to access the child element."
		if self._dNS: n = (self._dNS, n)
		for x in self._dir:
			if isinstance(x, Element) and x._name == n: return x
		raise AttributeError, 'No child element named %s' % repr(n)
		
	def __hasattr__(self, n):
		for x in self._dir:
			if isinstance(x, Element) and x._name == n: return True
		return False
		
 	def __setattr__(self, n, v):
		if n[0] == '_': self.__dict__[n] = v
		else: self[n] = v
 

	def __getitem__(self, n):
		if isinstance(n, type(0)): # d[1] == d._dir[1]
			return self._dir[n]
		elif isinstance(n, slice(0).__class__):
			# numerical slices
			if isinstance(n.start, type(0)): return self._dir[n.start:n.stop]
			
			# d['foo':] == all <foo>s
			n = n.start
			if self._dNS and not islst(n): n = (self._dNS, n)
			out = []
			for x in self._dir:
				if isinstance(x, Element) and x._name == n: out.append(x) 
			return out
		else: # d['foo'] == first <foo>
			if self._dNS and not islst(n): n = (self._dNS, n)
			for x in self._dir:
				if isinstance(x, Element) and x._name == n: return x
			raise KeyError, n
	
	def __setitem__(self, n, v):
		if isinstance(n, type(0)): # d[1]
			self._dir[n] = v
		elif isinstance(n, slice(0).__class__):
			# d['foo':] adds a new foo
			n = n.start
			if self._dNS and not islst(n): n = (self._dNS, n)

			nv = Element(n)
			self._dir.append(nv)
			
		else: # d["foo"] replaces first <foo> and dels rest
			if self._dNS and not islst(n): n = (self._dNS, n)

			nv = Element(n); nv._dir.append(v)
			replaced = False

			todel = []
			for i in range(len(self)):
				if self[i]._name == n:
					if replaced:
						todel.append(i)
					else:
						self[i] = nv
						replaced = True
			if not replaced: self._dir.append(nv)
			for i in todel: del self[i]

	def __delitem__(self, n):
		if isinstance(n, type(0)): del self._dir[n]
		elif isinstance(n, slice(0).__class__):
			# delete all <foo>s
			n = n.start
			if self._dNS and not islst(n): n = (self._dNS, n)
			
			for i in range(len(self)):
				if self[i]._name == n: del self[i]
		else:
			# delete first foo
			for i in range(len(self)):
				if self[i]._name == n: del self[i]
				break
	
	def __call__(self, *_pos, **_set): 
		if _set:
			for k in _set.keys(): self._attrs[k] = _set[k]
		if len(_pos) > 1:
			for i in range(0, len(_pos), 2):
				self._attrs[_pos[i]] = _pos[i+1]
		if len(_pos) == 1:
			return self._attrs[_pos[0]]
		if len(_pos) == 0:
			return self._attrs

	def __len__(self): return len(self._dir)

class Namespace:
	def __init__(self, uri): self.__uri = uri
	def __getattr__(self, n): return (self.__uri, n)
	def __getitem__(self, n): return (self.__uri, n)

from xml.sax.handler import EntityResolver, DTDHandler, ContentHandler, ErrorHandler

class Seeder(EntityResolver, DTDHandler, ContentHandler, ErrorHandler):
	def __init__(self):
		self.stack = []
		self.ch = ''
		self.prefixes = {}
		ContentHandler.__init__(self)
		
	def startPrefixMapping(self, prefix, uri):
		if not self.prefixes.has_key(prefix): self.prefixes[prefix] = []
		self.prefixes[prefix].append(uri)
	def endPrefixMapping(self, prefix):
		self.prefixes[prefix].pop()
		# szf: 5/15/5
		if len(self.prefixes[prefix]) == 0:
			del self.prefixes[prefix]
	
	def startElementNS(self, name, qname, attrs):
		ch = self.ch; self.ch = ''	
		if ch and not ch.isspace(): self.stack[-1]._dir.append(ch)

		attrs = dict(attrs)
		newprefixes = {}
		for k in self.prefixes.keys(): newprefixes[k] = self.prefixes[k][-1]
		
		self.stack.append(Element(name, attrs, prefixes=newprefixes.copy()))
	
	def characters(self, ch):
		self.ch += ch
	
	def endElementNS(self, name, qname):
		ch = self.ch; self.ch = ''
		if ch and not ch.isspace(): self.stack[-1]._dir.append(ch)
	
		element = self.stack.pop()
		if self.stack:
			self.stack[-1]._dir.append(element)
		else:
			self.result = element

from xml.sax import make_parser
from xml.sax.handler import feature_namespaces

def seed(fileobj):
	seeder = Seeder()
	parser = make_parser()
	parser.setFeature(feature_namespaces, 1)
	parser.setContentHandler(seeder)
	parser.parse(fileobj)
	return seeder.result

def parse(text):
	from StringIO import StringIO
	return seed(StringIO(text))

def load(url): 
	import urllib
	return seed(urllib.urlopen(url))

def unittest():
	parse('<doc>a<baz>f<b>o</b>ob<b>a</b>r</baz>a</doc>').__repr__(1,1) == \
	  '<doc>\n\ta<baz>\n\t\tf<b>o</b>ob<b>a</b>r\n\t</baz>a\n</doc>'
	
	assert str(parse("<doc />")) == ""
	assert str(parse("<doc>I <b>love</b> you.</doc>")) == "I love you."
	assert parse("<doc>\nmom\nwow\n</doc>")[0].strip() == "mom\nwow"
	assert str(parse('<bing>  <bang> <bong>center</bong> </bang>  </bing>')) == "center"
	assert str(parse('<doc>\xcf\x80</doc>')) == '\xcf\x80'
	
	d = Element('foo', attrs={'foo':'bar'}, children=['hit with a', Element('bar'), Element('bar')])
	
	try: 
		d._doesnotexist
		raise "ExpectedError", "but found success. Damn."
	except AttributeError: pass
	assert d.bar._name == 'bar'
	try:
		d.doesnotexist
		raise "ExpectedError", "but found success. Damn."
	except AttributeError: pass
	
	assert hasattr(d, 'bar') == True
	
	assert d('foo') == 'bar'
	d(silly='yes')
	assert d('silly') == 'yes'
	assert d() == d._attrs
	
	assert d[0] == 'hit with a'
	d[0] = 'ice cream'
	assert d[0] == 'ice cream'
	del d[0]
	assert d[0]._name == "bar"
	assert len(d[:]) == len(d._dir)
	assert len(d[1:]) == len(d._dir) - 1
	assert len(d['bar':]) == 2
	d['bar':] = 'baz'
	assert len(d['bar':]) == 3
	assert d['bar']._name == 'bar'
	
	d = Element('foo')
	
	doc = Namespace("http://example.org/bar")
	bbc = Namespace("http://example.org/bbc")
	dc = Namespace("http://purl.org/dc/elements/1.1/")
	d = parse("""<doc version="2.7182818284590451"
	  xmlns="http://example.org/bar" 
	  xmlns:dc="http://purl.org/dc/elements/1.1/"
	  xmlns:bbc="http://example.org/bbc">
		<author>John Polk and John Palfrey</author>
		<dc:creator>John Polk</dc:creator>
		<dc:creator>John Palfrey</dc:creator>
		<bbc:show bbc:station="4">Buffy</bbc:show>
	</doc>""")

	assert repr(d) == '<doc version="2.7182818284590451">...</doc>'
	assert d.__repr__(1) == '<doc xmlns:bbc="http://example.org/bbc" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns="http://example.org/bar" version="2.7182818284590451"><author>John Polk and John Palfrey</author><dc:creator>John Polk</dc:creator><dc:creator>John Palfrey</dc:creator><bbc:show bbc:station="4">Buffy</bbc:show></doc>'
	assert d.__repr__(1,1) == '<doc xmlns:bbc="http://example.org/bbc" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns="http://example.org/bar" version="2.7182818284590451">\n\t<author>John Polk and John Palfrey</author>\n\t<dc:creator>John Polk</dc:creator>\n\t<dc:creator>John Palfrey</dc:creator>\n\t<bbc:show bbc:station="4">Buffy</bbc:show>\n</doc>'

	assert repr(parse("<doc xml:lang='en' />")) == '<doc xml:lang="en"></doc>'

	assert str(d.author) == str(d['author']) == "John Polk and John Palfrey"
	assert d.author._name == doc.author
	assert str(d[dc.creator]) == "John Polk"
	assert d[dc.creator]._name == dc.creator
	assert str(d[dc.creator:][1]) == "John Palfrey"
	d[dc.creator] = "Me!!!"
	assert str(d[dc.creator]) == "Me!!!"
	assert len(d[dc.creator:]) == 1
	d[dc.creator:] = "You!!!"
	assert len(d[dc.creator:]) == 2
	
	assert d[bbc.show](bbc.station) == "4"
	d[bbc.show](bbc.station, "5")
	assert d[bbc.show](bbc.station) == "5"

	e = Element('e')
	e.c = '<img src="foo">'
	assert e.__repr__(1) == '<e><c>&lt;img src="foo"></c></e>'
	e.c = '2 > 4'
	assert e.__repr__(1) == '<e><c>2 > 4</c></e>'
	e.c = 'CDATA sections are <em>closed</em> with ]]>.'
	assert e.__repr__(1) == '<e><c>CDATA sections are &lt;em>closed&lt;/em> with ]]&gt;.</c></e>'
	e.c = parse('<div xmlns="http://www.w3.org/1999/xhtml">i<br /><span></span>love<br />you</div>')
	assert e.__repr__(1) == '<e><c><div xmlns="http://www.w3.org/1999/xhtml">i<br /><span></span>love<br />you</div></c></e>'	
	
	e = Element('e')
	e('c', 'that "sucks"')
	assert e.__repr__(1) == '<e c="that &quot;sucks&quot;"></e>'

	
	assert quote("]]>") == "]]&gt;"
	assert quote('< dkdkdsd dkd sksdksdfsd fsdfdsf]]> kfdfkg >') == '&lt; dkdkdsd dkd sksdksdfsd fsdfdsf]]&gt; kfdfkg >'
	
	assert parse('<x a="&lt;"></x>').__repr__(1) == '<x a="&lt;"></x>'
	assert parse('<a xmlns="http://a"><b xmlns="http://b"/></a>').__repr__(1) == '<a xmlns="http://a"><b xmlns="http://b"></b></a>'
	
if __name__ == '__main__': unittest()

########NEW FILE########
