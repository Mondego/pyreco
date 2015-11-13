__FILENAME__ = apitest
#=============================================================================
# eveapi module demonstration script - Jamie van den Berge
#=============================================================================
#
# This file is in the Public Domain - Do with it as you please.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE
#
#----------------------------------------------------------------------------
# Put your userID and apiKey (full access) here before running this script.
YOUR_KEYID = 123456
YOUR_VCODE = "nyanyanyanyanyanyanyanyanyanyanyanyanyanyanyanyanyanya:3"

import time
import tempfile
import cPickle
import zlib
import os
from os.path import join, exists
from httplib import HTTPException

import eveapi

api = eveapi.EVEAPIConnection()

#----------------------------------------------------------------------------
print
print "EXAMPLE 1: GETTING THE ALLIANCE LIST"
print " (and showing alliances with 1000 or more members)"
print

# Let's get the list of alliances.
# The API function we need to get the list is:
#
#    /eve/AllianceList.xml.aspx
#
# There is a 1:1 correspondence between folders/files and attributes on api
# objects, so to call this particular function, we simply do this:
result1 = api.eve.AllianceList()

# This result contains a rowset object called "alliances". Rowsets are like
# database tables and you can do various useful things with them. For now
# we'll just iterate over it and display all alliances with more than 1000
# members:
for alliance in result1.alliances:
	if alliance.memberCount >= 1000:
		print "%s <%s> has %d members" %\
			(alliance.name, alliance.shortName, alliance.memberCount)


#-----------------------------------------------------------------------------
print
print "EXAMPLE 2: GETTING WALLET BALANCE OF ALL YOUR CHARACTERS"
print

# To get any info on character/corporation related stuff, we need to acquire
# an authentication context. All API requests that require authentication need
# to be called through this object. While it is possible to call such API
# functions directly through the api object, you would have to specify the
# userID and apiKey on every call. If you are iterating over many accounts,
# that may actually be the better option. However, for these examples we only
# use one account, so this is more convenient.
auth = api.auth(keyID=YOUR_KEYID, vCode=YOUR_VCODE)

# Now let's say you want to the wallet balance of all your characters.
# The API function we need to get the characters on your account is:
#
#    /account/Characters.xml.aspx
#
# As in example 1, this simply means adding folder names as attributes
# and calling the function named after the base page name:
result2 = auth.account.Characters()

# Some tracking for later examples.
rich = 0
rich_charID = 0

# Now the best way to iterate over the characters on your account and show
# the isk balance is probably this way:
for character in result2.characters:
	wallet = auth.char.AccountBalance(characterID=character.characterID)
	isk = wallet.accounts[0].balance
	print character.name, "has", isk, "ISK."

	if isk > rich:
		rich = isk
		rich_charID = character.characterID



#-----------------------------------------------------------------------------
print
print "EXAMPLE 3: WHEN STUFF GOES WRONG"
print

# Obviously you cannot assume an API call to succeed. There's a myriad of
# things that can go wrong:
#
# - Connection error
# - Server error
# - Invalid parameters passed
# - Hamsters died
#
# Therefor it is important to handle errors properly. eveapi will raise
# an AttributeError if the requested function does not exist on the server
# (ie. when it returns a 404), a RuntimeError on any other webserver error
# (such as 500 Internal Server error).
# On top of this, you can get any of the httplib (which eveapi uses) and
# socket (which httplib uses) exceptions so you might want to catch those
# as well.
#

try:
	# Try calling account/Characters without authentication context
	api.account.Characters()
except eveapi.Error, e:
	print "Oops! eveapi returned the following error:"
	print "code:", e.code
	print "message:", e.message
except Exception, e:
	print "Something went horribly wrong:", str(e)
	raise


#-----------------------------------------------------------------------------
print
print "EXAMPLE 4: GETTING CHARACTER SHEET INFORMATION"
print

# We grab ourselves a character context object.
# Note that this is a convenience function that takes care of passing the
# characterID=x parameter to every API call much like auth() does (in fact
# it's exactly like that, apart from the fact it also automatically adds the
# "/char" folder). Again, it is possible to use the API functions directly
# from the api or auth context, but then you have to provide the missing
# keywords on every call (characterID in this case).
#
# The victim we'll use is the last character on the account we used in
# example 1.
me = auth.character(result2.characters[-1].characterID)

# Now that we have a character context, we can display skills trained on
# a character. First we have to get the skill tree. A real application
# would cache this data; all objects returned by the api interface can be
# pickled.
skilltree = api.eve.SkillTree()

# Now we have to fetch the charactersheet.
# Note that the call below is identical to:
#
#   acc.char.CharacterSheet(characterID=your_character_id)
#
# But, as explained above, the context ("me") we created automatically takes
# care of adding the characterID parameter and /char folder attribute.
sheet = me.CharacterSheet()

# This list should look familiar. They're the skillpoints at each level for
# a rank 1 skill. We could use the formula, but this is much simpler :)
sp = [0, 250, 1414, 8000, 45255, 256000]

total_sp = 0
total_skills = 0

# Now the fun bit starts. We walk the skill tree, and for every group in the
# tree...
for g in skilltree.skillGroups:

	skills_trained_in_this_group = False

	# ... iterate over the skills in this group...
	for skill in g.skills:

		# see if we trained this skill by checking the character sheet object
		trained = sheet.skills.Get(skill.typeID, False)
		if trained:
			# yep, we trained this skill.

			# print the group name if we haven't done so already
			if not skills_trained_in_this_group:
				print g.groupName
				skills_trained_in_this_group = True

			# and display some info about the skill!
			print "- %s Rank(%d) - SP: %d/%d - Level: %d" %\
				(skill.typeName, skill.rank, trained.skillpoints, (skill.rank * sp[trained.level]), trained.level)
			total_skills += 1
			total_sp += trained.skillpoints


# And to top it off, display totals.
print "You currently have %d skills and %d skill points" % (total_skills, total_sp)



#-----------------------------------------------------------------------------
print
print "EXAMPLE 5: USING ROWSETS"
print

# For this one we will use the result1 that contains the alliance list from
# the first example.
rowset = result1.alliances

# Now, what if we want to sort the alliances by ticker name. We could unpack
# all alliances into a list and then use python's sort(key=...) on that list,
# but that's not efficient. The rowset objects support sorting on columns
# directly:
rowset.SortBy("shortName")

# Note the use of Select() here. The Select method speeds up iterating over
# large rowsets considerably as no temporary row instances are created.
for ticker in rowset.Select("shortName"):
	print ticker,
print

# The sort above modified the result inplace. There is another method, called
# SortedBy, which returns a new rowset. 

print

# Another useful method of rowsets is IndexBy, which enables you to do direct
# key lookups on columns. We already used this feature in example 3. Indeed
# most rowsets returned are IndexRowsets already if the data has a primary
# key attribute defined in the <rowset> tag in the XML data.
#
# IndexRowsets are efficient, they reference the data from the rowset they
# were created from, and create an index mapping on top of it.
#
# Anyway, to create an index:
alliances_by_ticker = rowset.IndexedBy("shortName")

# Now use the Get() method to get a row directly.
# Assumes ISD alliance exists. If it doesn't, we probably have bigger
# problems than the unhandled exception here -_-
try:
	print alliances_by_ticker.Get("ISD")
except :
	print "Blimey! CCP let the ISD alliance expire -AGAIN-. How inconvenient!"

# You may specify a default to return in case the row wasn't found:
print alliances_by_ticker.Get("123456", 42)

# If no default was specified and you try to look up a key that does not
# exist, an appropriate exception will be raised:
try:
	print alliances_by_ticker.Get("123456")
except KeyError:
	print "This concludes example 5"



#-----------------------------------------------------------------------------
print
print "EXAMPLE 6: CACHING DATA"
print

# For some calls you will want caching. To facilitate this, a customized
# cache handler can be attached. Below is an example of a simple cache
# handler. 

class MyCacheHandler(object):
	# Note: this is an example handler to demonstrate how to use them.
	# a -real- handler should probably be thread-safe and handle errors
	# properly (and perhaps use a better hashing scheme).

	def __init__(self, debug=False):
		self.debug = debug
		self.count = 0
		self.cache = {}
		self.tempdir = join(tempfile.gettempdir(), "eveapi")
		if not exists(self.tempdir):
			os.makedirs(self.tempdir)

	def log(self, what):
		if self.debug:
			print "[%d] %s" % (self.count, what)

	def retrieve(self, host, path, params):
		# eveapi asks if we have this request cached
		key = hash((host, path, frozenset(params.items())))

		self.count += 1  # for logging

		# see if we have the requested page cached...
		cached = self.cache.get(key, None)
		if cached:
			cacheFile = None
			#print "'%s': retrieving from memory" % path
		else:
			# it wasn't cached in memory, but it might be on disk.
			cacheFile = join(self.tempdir, str(key) + ".cache")
			if exists(cacheFile):
				self.log("%s: retrieving from disk" % path)
				f = open(cacheFile, "rb")
				cached = self.cache[key] = cPickle.loads(zlib.decompress(f.read()))
				f.close()

		if cached:
			# check if the cached doc is fresh enough
			if time.time() < cached[0]:
				self.log("%s: returning cached document" % path)
				return cached[1]  # return the cached XML doc

			# it's stale. purge it.
			self.log("%s: cache expired, purging!" % path)
			del self.cache[key]
			if cacheFile:
				os.remove(cacheFile)

		self.log("%s: not cached, fetching from server..." % path)
		# we didn't get a cache hit so return None to indicate that the data
		# should be requested from the server.
		return None

	def store(self, host, path, params, doc, obj):
		# eveapi is asking us to cache an item
		key = hash((host, path, frozenset(params.items())))

		cachedFor = obj.cachedUntil - obj.currentTime
		if cachedFor:
			self.log("%s: cached (%d seconds)" % (path, cachedFor))

			cachedUntil = time.time() + cachedFor

			# store in memory
			cached = self.cache[key] = (cachedUntil, doc)

			# store in cache folder
			cacheFile = join(self.tempdir, str(key) + ".cache")
			f = open(cacheFile, "wb")
			f.write(zlib.compress(cPickle.dumps(cached, -1)))
			f.close()


# Now try out the handler! Even though were initializing a new api object
# here, a handler can be attached or removed from an existing one at any
# time with its setcachehandler() method.
cachedApi = eveapi.EVEAPIConnection(cacheHandler=MyCacheHandler(debug=True))

# First time around this will fetch the document from the server. That is,
# if this demo is run for the first time, otherwise it will attempt to load
# the cache written to disk on the previous run.
result = cachedApi.eve.SkillTree()

# But the second time it should be returning the cached version
result = cachedApi.eve.SkillTree()



#-----------------------------------------------------------------------------
print
print "EXAMPLE 7: TRANSACTION DATA"
print "(and doing more nifty stuff with rowsets)"
print

# okay since we have a caching api object now it is fairly safe to do this
# example repeatedly without server locking you out for an hour every time!

# Let's use the first character on the account (using the richest character
# found in example 2). Note how we are chaining the various contexts here to
# arrive directly at a character context. If you're not using any intermediate
# contexts in the chain anyway, this is okay.
me = cachedApi.auth(keyID=YOUR_KEYID, vCode=YOUR_VCODE).character(rich_charID)

# Now fetch the journal. Since this character context was created through 
# the cachedApi object, it will still use the cachehandler from example 5.
journal = me.WalletJournal()

# Let's see how much we paid SCC in transaction tax in the first page
# of data!

# Righto, now we -could- sift through the rows and extract what we want,
# but we can do it in a much more clever way using the GroupedBy method
# of the rowset in the result. This creates a mapping that maps keys
# to Rowsets of all rows with that key value in specified column.
# These data structures are also quite efficient as the only extra data
# created is the index and grouping.
entriesByRefType = journal.transactions.GroupedBy("refTypeID")

# Also note that we're using a hardcoded refTypeID of 54 here. You're
# supposed to use .eve.RefTypes() though (however they are not likely
# to be changed anyway so we can get away with it)
# Note the use of Select() to speed things up here.
amount = 0.0
date = 0
for taxAmount, date in entriesByRefType[54].Select("amount", "date"):
	amount += -taxAmount

print "You paid a %.2f ISK transaction tax since %s" %\
	(amount, time.asctime(time.gmtime(date)))


# You might also want to see how much a certain item yielded you recently.
typeName = "Expanded Cargohold II"  # change this to something you sold.
amount = 0.0

wallet = me.WalletTransactions()
soldTx = wallet.transactions.GroupedBy("transactionType")["sell"]
for row in soldTx.GroupedBy("typeName")[typeName]:
	amount += (row.quantity * row.price)

print "%s sales yielded %.2f ISK since %s" %\
	(typeName, amount, time.asctime(time.gmtime(row.transactionDateTime)))

# I'll leave walking the transaction pages as an excercise to the reader ;)
# Please also see the eveapi module itself for more documentation.

# That's all folks!


########NEW FILE########
__FILENAME__ = eveapi
#-----------------------------------------------------------------------------
# eveapi - EVE Online API access
#
# Copyright (c)2007-2014 Jamie "Entity" van den Berge <jamie@hlekkir.com>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE
#
#-----------------------------------------------------------------------------
#
# Version: 1.3.0 - 27 May 2014
# - Added set_user_agent() module-level function to set the User-Agent header
#   to be used for any requests by the library. If this function is not used,
#   a warning will be thrown for every API request.
#
# Version: 1.2.9 - 14 September 2013
# - Updated error handling: Raise an AuthenticationError in case
#	the API returns HTTP Status Code 403 - Forbidden
#
# Version: 1.2.8 - 9 August 2013
# - the XML value cast function (_autocast) can now be changed globally to a
#   custom one using the set_cast_func(func) module-level function.
#
# Version: 1.2.7 - 3 September 2012
# - Added get() method to Row object.
#
# Version: 1.2.6 - 29 August 2012
# - Added finer error handling + added setup.py to allow distributing eveapi
#   through pypi.
#
# Version: 1.2.5 - 1 August 2012
# - Row objects now have __hasattr__ and __contains__ methods
#
# Version: 1.2.4 - 12 April 2012
# - API version of XML response now available as _meta.version
#
# Version: 1.2.3 - 10 April 2012
# - fix for tags of the form <tag attr=bla ... />
#
# Version: 1.2.2 - 27 February 2012
# - fix for the workaround in 1.2.1.
#
# Version: 1.2.1 - 23 February 2012
# - added workaround for row tags missing attributes that were defined
#   in their rowset (this should fix ContractItems)
#
# Version: 1.2.0 - 18 February 2012
# - fix handling of empty XML tags.
# - improved proxy support a bit.
#
# Version: 1.1.9 - 2 September 2011
# - added workaround for row tags with attributes that were not defined
#   in their rowset (this should fix AssetList)
#
# Version: 1.1.8 - 1 September 2011
# - fix for inconsistent columns attribute in rowsets.
#
# Version: 1.1.7 - 1 September 2011
# - auth() method updated to work with the new authentication scheme.
#
# Version: 1.1.6 - 27 May 2011
# - Now supports composite keys for IndexRowsets.
# - Fixed calls not working if a path was specified in the root url.
#
# Version: 1.1.5 - 27 Januari 2011
# - Now supports (and defaults to) HTTPS. Non-SSL proxies will still work by
#   explicitly specifying http:// in the url.
#
# Version: 1.1.4 - 1 December 2010
# - Empty explicit CDATA tags are now properly handled.
# - _autocast now receives the name of the variable it's trying to typecast,
#   enabling custom/future casting functions to make smarter decisions.
#
# Version: 1.1.3 - 6 November 2010
# - Added support for anonymous CDATA inside row tags. This makes the body of
#   mails in the rows of char/MailBodies available through the .data attribute.
#
# Version: 1.1.2 - 2 July 2010
# - Fixed __str__ on row objects to work properly with unicode strings.
#
# Version: 1.1.1 - 10 Januari 2010
# - Fixed bug that causes nested tags to not appear in rows of rowsets created
#   from normal Elements. This should fix the corp.MemberSecurity method,
#   which now returns all data for members. [jehed]
#
# Version: 1.1.0 - 15 Januari 2009
# - Added Select() method to Rowset class. Using it avoids the creation of
#   temporary row instances, speeding up iteration considerably.
# - Added ParseXML() function, which can be passed arbitrary API XML file or
#   string objects.
# - Added support for proxy servers. A proxy can be specified globally or
#   per api connection instance. [suggestion by graalman]
# - Some minor refactoring.
# - Fixed deprecation warning when using Python 2.6.
#
# Version: 1.0.7 - 14 November 2008
# - Added workaround for rowsets that are missing the (required!) columns
#   attribute. If missing, it will use the columns found in the first row.
#   Note that this is will still break when expecting columns, if the rowset
#   is empty. [Flux/Entity]
#
# Version: 1.0.6 - 18 July 2008
# - Enabled expat text buffering to avoid content breaking up. [BigWhale]
#
# Version: 1.0.5 - 03 February 2008
# - Added workaround to make broken XML responses (like the "row:name" bug in
#   eve/CharacterID) work as intended.
# - Bogus datestamps before the epoch in XML responses are now set to 0 to
#   avoid breaking certain date/time functions. [Anathema Matou]
#
# Version: 1.0.4 - 23 December 2007
# - Changed _autocast() to use timegm() instead of mktime(). [Invisible Hand]
# - Fixed missing attributes of elements inside rows. [Elandra Tenari]
#
# Version: 1.0.3 - 13 December 2007
# - Fixed keyless columns bugging out the parser (in CorporationSheet for ex.)
#
# Version: 1.0.2 - 12 December 2007
# - Fixed parser not working with indented XML.
#
# Version: 1.0.1
# - Some micro optimizations
#
# Version: 1.0
# - Initial release
#
# Requirements:
#   Python 2.4+
#
#-----------------------------------------------------------------------------

import httplib
import urlparse
import urllib
import copy
import warnings

from xml.parsers import expat
from time import strptime
from calendar import timegm

proxy = None
proxySSL = False

_default_useragent = "eveapi.py/1.3"
_useragent = None  # use set_user_agent() to set this.

#-----------------------------------------------------------------------------

def set_cast_func(func):
	"""Sets an alternative value casting function for the XML parser.
	The function must have 2 arguments; key and value. It should return a
	value or object of the type appropriate for the given attribute name/key.
	func may be None and will cause the default _autocast function to be used.
	"""
	global _castfunc
	_castfunc = _autocast if func is None else func

def set_user_agent(user_agent_string):
	"""Sets a User-Agent for any requests sent by the library."""
	global _useragent
	_useragent = user_agent_string


class Error(StandardError):
	def __init__(self, code, message):
		self.code = code
		self.args = (message.rstrip("."),)
	def __unicode__(self):
		return u'%s [code=%s]' % (self.args[0], self.code)

class RequestError(Error):
	pass

class AuthenticationError(Error):
	pass

class ServerError(Error):
	pass


def EVEAPIConnection(url="api.eveonline.com", cacheHandler=None, proxy=None, proxySSL=False):
	# Creates an API object through which you can call remote functions.
	#
	# The following optional arguments may be provided:
	#
	# url - root location of the EVEAPI server
	#
	# proxy - (host,port) specifying a proxy server through which to request
	#         the API pages. Specifying a proxy overrides default proxy.
	#
	# proxySSL - True if the proxy requires SSL, False otherwise.
	#
	# cacheHandler - an object which must support the following interface:
	#
	#      retrieve(host, path, params)
	#
	#          Called when eveapi wants to fetch a document.
	#          host is the address of the server, path is the full path to
	#          the requested document, and params is a dict containing the
	#          parameters passed to this api call (keyID, vCode, etc).
	#          The method MUST return one of the following types:
	#
	#           None - if your cache did not contain this entry
	#           str/unicode - eveapi will parse this as XML
	#           Element - previously stored object as provided to store()
	#           file-like object - eveapi will read() XML from the stream.
	#
	#      store(host, path, params, doc, obj)
	#
	#          Called when eveapi wants you to cache this item.
	#          You can use obj to get the info about the object (cachedUntil
	#          and currentTime, etc) doc is the XML document the object
	#          was generated from. It's generally best to cache the XML, not
	#          the object, unless you pickle the object. Note that this method
	#          will only be called if you returned None in the retrieve() for
	#          this object.
	#

	if not url.startswith("http"):
		url = "https://" + url
	p = urlparse.urlparse(url, "https")
	if p.path and p.path[-1] == "/":
		p.path = p.path[:-1]
	ctx = _RootContext(None, p.path, {}, {})
	ctx._handler = cacheHandler
	ctx._scheme = p.scheme
	ctx._host = p.netloc
	ctx._proxy = proxy or globals()["proxy"]
	ctx._proxySSL = proxySSL or globals()["proxySSL"]
	return ctx


def ParseXML(file_or_string):
	try:
		return _ParseXML(file_or_string, False, None)
	except TypeError:
		raise TypeError("XML data must be provided as string or file-like object")


def _ParseXML(response, fromContext, storeFunc):
	# pre/post-process XML or Element data

	if fromContext and isinstance(response, Element):
		obj = response
	elif type(response) in (str, unicode):
		obj = _Parser().Parse(response, False)
	elif hasattr(response, "read"):
		obj = _Parser().Parse(response, True)
	else:
		raise TypeError("retrieve method must return None, string, file-like object or an Element instance")

	error = getattr(obj, "error", False)
	if error:
		if error.code >= 500:
			raise ServerError(error.code, error.data)
		elif error.code >= 200:
			raise AuthenticationError(error.code, error.data)
		elif error.code >= 100:
			raise RequestError(error.code, error.data)
		else:
			raise Error(error.code, error.data)

	result = getattr(obj, "result", False)
	if not result:
		raise RuntimeError("API object does not contain result")

	if fromContext and storeFunc:
		# call the cache handler to store this object
		storeFunc(obj)

	# make metadata available to caller somehow
	result._meta = obj

	return result


	


#-----------------------------------------------------------------------------
# API Classes
#-----------------------------------------------------------------------------

_listtypes = (list, tuple, dict)
_unspecified = []

class _Context(object):

	def __init__(self, root, path, parentDict, newKeywords=None):
		self._root = root or self
		self._path = path
		if newKeywords:
			if parentDict:
				self.parameters = parentDict.copy()
			else:
				self.parameters = {}
			self.parameters.update(newKeywords)
		else:
			self.parameters = parentDict or {}

	def context(self, *args, **kw):
		if kw or args:
			path = self._path
			if args:
				path += "/" + "/".join(args)
			return self.__class__(self._root, path, self.parameters, kw)
		else:
			return self

	def __getattr__(self, this):
		# perform arcane attribute majick trick
		return _Context(self._root, self._path + "/" + this, self.parameters)

	def __call__(self, **kw):
		if kw:
			# specified keywords override contextual ones
			for k, v in self.parameters.iteritems():
				if k not in kw:
					kw[k] = v
		else:
			# no keywords provided, just update with contextual ones.
			kw.update(self.parameters)

		# now let the root context handle it further
		return self._root(self._path, **kw)


class _AuthContext(_Context):

	def character(self, characterID):
		# returns a copy of this connection object but for every call made
		# through it, it will add the folder "/char" to the url, and the
		# characterID to the parameters passed.
		return _Context(self._root, self._path + "/char", self.parameters, {"characterID":characterID})

	def corporation(self, characterID):
		# same as character except for the folder "/corp"
		return _Context(self._root, self._path + "/corp", self.parameters, {"characterID":characterID})


class _RootContext(_Context):

	def auth(self, **kw):
		if len(kw) == 2 and (("keyID" in kw and "vCode" in kw) or ("userID" in kw and "apiKey" in kw)):
			return _AuthContext(self._root, self._path, self.parameters, kw)
		raise ValueError("Must specify keyID and vCode")

	def setcachehandler(self, handler):
		self._root._handler = handler

	def __call__(self, path, **kw):
		# convert list type arguments to something the API likes
		for k, v in kw.iteritems():
			if isinstance(v, _listtypes):
				kw[k] = ','.join(map(str, list(v)))

		cache = self._root._handler

		# now send the request
		path += ".xml.aspx"

		if cache:
			response = cache.retrieve(self._host, path, kw)
		else:
			response = None

		if response is None:
			if not _useragent:
				warnings.warn("No User-Agent set! Please use the set_user_agent() module-level function before accessing the EVE API.", stacklevel=3)

			if self._proxy is None:
				req = path
				if self._scheme == "https":
					conn = httplib.HTTPSConnection(self._host)
				else:
					conn = httplib.HTTPConnection(self._host)
			else:
				req = self._scheme+'://'+self._host+path
				if self._proxySSL:
					conn = httplib.HTTPSConnection(*self._proxy)
				else:
					conn = httplib.HTTPConnection(*self._proxy)

			if kw:
				conn.request("POST", req, urllib.urlencode(kw), {"Content-type": "application/x-www-form-urlencoded", "User-Agent": _useragent or _default_useragent})
			else:
				conn.request("GET", req, "", {"User-Agent": _useragent or _default_useragent})

			response = conn.getresponse()
			if response.status != 200:
				if response.status == httplib.NOT_FOUND:
					raise AttributeError("'%s' not available on API server (404 Not Found)" % path)
				elif response.status == httplib.FORBIDDEN:
					raise AuthenticationError(response.status, 'HTTP 403 - Forbidden')
				else:
					raise ServerError(response.status, "'%s' request failed (%s)" % (path, response.reason))

			if cache:
				store = True
				response = response.read()
			else:
				store = False
		else:
			store = False

		retrieve_fallback = cache and getattr(cache, "retrieve_fallback", False)
		if retrieve_fallback:
			# implementor is handling fallbacks...
			try:
				return _ParseXML(response, True, store and (lambda obj: cache.store(self._host, path, kw, response, obj)))
			except Error, e:
				response = retrieve_fallback(self._host, path, kw, reason=e)
				if response is not None:
					return response
				raise
		else:
			# implementor is not handling fallbacks...
			return _ParseXML(response, True, store and (lambda obj: cache.store(self._host, path, kw, response, obj)))

#-----------------------------------------------------------------------------
# XML Parser
#-----------------------------------------------------------------------------

def _autocast(key, value):
	# attempts to cast an XML string to the most probable type.
	try:
		if value.strip("-").isdigit():
			return int(value)
	except ValueError:
		pass

	try:
		return float(value)
	except ValueError:
		pass

	if len(value) == 19 and value[10] == ' ':
		# it could be a date string
		try:
			return max(0, int(timegm(strptime(value, "%Y-%m-%d %H:%M:%S"))))
		except OverflowError:
			pass
		except ValueError:
			pass

	# couldn't cast. return string unchanged.
	return value

_castfunc = _autocast


class _Parser(object):

	def Parse(self, data, isStream=False):
		self.container = self.root = None
		self._cdata = False
		p = expat.ParserCreate()
		p.StartElementHandler = self.tag_start
		p.CharacterDataHandler = self.tag_cdata
		p.StartCdataSectionHandler = self.tag_cdatasection_enter
		p.EndCdataSectionHandler = self.tag_cdatasection_exit
		p.EndElementHandler = self.tag_end
		p.ordered_attributes = True
		p.buffer_text = True

		if isStream:
			p.ParseFile(data)
		else:
			p.Parse(data, True)
		return self.root


	def tag_cdatasection_enter(self):
		# encountered an explicit CDATA tag.
		self._cdata = True

	def tag_cdatasection_exit(self):
		if self._cdata:
			# explicit CDATA without actual data. expat doesn't seem
			# to trigger an event for this case, so do it manually.
			# (_cdata is set False by this call)
			self.tag_cdata("")
		else:
			self._cdata = False

	def tag_start(self, name, attributes):
		# <hack>
		# If there's a colon in the tag name, cut off the name from the colon
		# onward. This is a workaround to make certain bugged XML responses
		# (such as eve/CharacterID.xml.aspx) work.
		if ":" in name:
			name = name[:name.index(":")]
		# </hack>

		if name == "rowset":
			# for rowsets, use the given name
			try:
				columns = attributes[attributes.index('columns')+1].replace(" ", "").split(",")
			except ValueError:
				# rowset did not have columns tag set (this is a bug in API)
				# columns will be extracted from first row instead.
				columns = []

			try:
				priKey = attributes[attributes.index('key')+1]
				this = IndexRowset(cols=columns, key=priKey)
			except ValueError:
				this = Rowset(cols=columns)


			this._name = attributes[attributes.index('name')+1]
			this.__catch = "row" # tag to auto-add to rowset.
		else:
			this = Element()
			this._name = name

		this.__parent = self.container

		if self.root is None:
			# We're at the root. The first tag has to be "eveapi" or we can't
			# really assume the rest of the xml is going to be what we expect.
			if name != "eveapi":
				raise RuntimeError("Invalid API response")
			try:
				this.version = attributes[attributes.index("version")+1]
			except KeyError:
				raise RuntimeError("Invalid API response")
			self.root = this

		if isinstance(self.container, Rowset) and (self.container.__catch == this._name):
			# <hack>
			# - check for missing columns attribute (see above).
			# - check for missing row attributes.
			# - check for extra attributes that were not defined in the rowset,
			#   such as rawQuantity in the assets lists.
			# In either case the tag is assumed to be correct and the rowset's
			# columns are overwritten with the tag's version, if required.
			numAttr = len(attributes)/2
			numCols = len(self.container._cols)
			if numAttr < numCols and (attributes[-2] == self.container._cols[-1]):
				# the row data is missing attributes that were defined in the rowset.
				# missing attributes' values will be set to None.
				fixed = []
				row_idx = 0; hdr_idx = 0; numAttr*=2
				for col in self.container._cols:
					if col == attributes[row_idx]:
						fixed.append(_castfunc(col, attributes[row_idx+1]))
						row_idx += 2
					else:
						fixed.append(None)
					hdr_idx += 1
				self.container.append(fixed)
			else:
				if not self.container._cols or (numAttr > numCols):
					# the row data contains more attributes than were defined.
					self.container._cols = attributes[0::2]
				self.container.append([_castfunc(attributes[i], attributes[i+1]) for i in xrange(0, len(attributes), 2)])
			# </hack>

			this._isrow = True
			this._attributes = this._attributes2 = None
		else:
			this._isrow = False
			this._attributes = attributes
			this._attributes2 = []
	
		self.container = self._last = this
		self.has_cdata = False

	def tag_cdata(self, data):
		self.has_cdata = True
		if self._cdata:
			# unset cdata flag to indicate it's been handled.
			self._cdata = False
		else:
			if data in ("\r\n", "\n") or data.strip() != data:
				return

		this = self.container
		data = _castfunc(this._name, data)

		if this._isrow:
			# sigh. anonymous data inside rows makes Entity cry.
			# for the love of Jove, CCP, learn how to use rowsets.
			parent = this.__parent
			_row = parent._rows[-1]
			_row.append(data)
			if len(parent._cols) < len(_row):
				parent._cols.append("data")

		elif this._attributes:
			# this tag has attributes, so we can't simply assign the cdata
			# as an attribute to the parent tag, as we'll lose the current
			# tag's attributes then. instead, we'll assign the data as
			# attribute of this tag.
			this.data = data
		else:
			# this was a simple <tag>data</tag> without attributes.
			# we won't be doing anything with this actual tag so we can just
			# bind it to its parent (done by __tag_end)
			setattr(this.__parent, this._name, data)

	def tag_end(self, name):
		this = self.container

		if this is self.root:
			del this._attributes
			#this.__dict__.pop("_attributes", None)
			return

		# we're done with current tag, so we can pop it off. This means that
		# self.container will now point to the container of element 'this'.
		self.container = this.__parent
		del this.__parent

		attributes = this.__dict__.pop("_attributes")
		attributes2 = this.__dict__.pop("_attributes2")
		if attributes is None:
			# already processed this tag's closure early, in tag_start()
			return

		if self.container._isrow:
			# Special case here. tags inside a row! Such tags have to be
			# added as attributes of the row.
			parent = self.container.__parent

			# get the row line for this element from its parent rowset
			_row = parent._rows[-1]

			# add this tag's value to the end of the row
			_row.append(getattr(self.container, this._name, this))

			# fix columns if neccessary.
			if len(parent._cols) < len(_row):
				parent._cols.append(this._name)
		else:
			# see if there's already an attribute with this name (this shouldn't
			# really happen, but it doesn't hurt to handle this case!
			sibling = getattr(self.container, this._name, None)
			if sibling is None:
				if (not self.has_cdata) and (self._last is this) and (name != "rowset"):
					if attributes:
						# tag of the form <tag attribute=bla ... />
						e = Element()
						e._name = this._name
						setattr(self.container, this._name, e)
						for i in xrange(0, len(attributes), 2):
							setattr(e, attributes[i], attributes[i+1])
					else:
						# tag of the form: <tag />, treat as empty string.
						setattr(self.container, this._name, "")
				else:
					self.container._attributes2.append(this._name)
					setattr(self.container, this._name, this)

			# Note: there aren't supposed to be any NON-rowset tags containing
			# multiples of some tag or attribute. Code below handles this case.
			elif isinstance(sibling, Rowset):
				# its doppelganger is a rowset, append this as a row to that.
				row = [_castfunc(attributes[i], attributes[i+1]) for i in xrange(0, len(attributes), 2)]
				row.extend([getattr(this, col) for col in attributes2])
				sibling.append(row)
			elif isinstance(sibling, Element):
				# parent attribute is an element. This means we're dealing
				# with multiple of the same sub-tag. Change the attribute
				# into a Rowset, adding the sibling element and this one.
				rs = Rowset()
				rs.__catch = rs._name = this._name
				row = [_castfunc(attributes[i], attributes[i+1]) for i in xrange(0, len(attributes), 2)]+[getattr(this, col) for col in attributes2]
				rs.append(row)
				row = [getattr(sibling, attributes[i]) for i in xrange(0, len(attributes), 2)]+[getattr(sibling, col) for col in attributes2]
				rs.append(row)
				rs._cols = [attributes[i] for i in xrange(0, len(attributes), 2)]+[col for col in attributes2]
				setattr(self.container, this._name, rs)
			else:
				# something else must have set this attribute already.
				# (typically the <tag>data</tag> case in tag_data())
				pass

		# Now fix up the attributes and be done with it.
		for i in xrange(0, len(attributes), 2):
			this.__dict__[attributes[i]] = _castfunc(attributes[i], attributes[i+1])

		return




#-----------------------------------------------------------------------------
# XML Data Containers
#-----------------------------------------------------------------------------
# The following classes are the various container types the XML data is
# unpacked into.
#
# Note that objects returned by API calls are to be treated as read-only. This
# is not enforced, but you have been warned.
#-----------------------------------------------------------------------------

class Element(object):
	# Element is a namespace for attributes and nested tags
	def __str__(self):
		return "<Element '%s'>" % self._name

_fmt = u"%s:%s".__mod__
class Row(object):
	# A Row is a single database record associated with a Rowset.
	# The fields in the record are accessed as attributes by their respective
	# column name.
	#
	# To conserve resources, Row objects are only created on-demand. This is
	# typically done by Rowsets (e.g. when iterating over the rowset).
	
	def __init__(self, cols=None, row=None):
		self._cols = cols or []
		self._row = row or []

	def __nonzero__(self):
		return True

	def __ne__(self, other):
		return self.__cmp__(other)

	def __eq__(self, other):
		return self.__cmp__(other) == 0

	def __cmp__(self, other):
		if type(other) != type(self):
			raise TypeError("Incompatible comparison type")
		return cmp(self._cols, other._cols) or cmp(self._row, other._row)

	def __hasattr__(self, this):
		if this in self._cols:
			return self._cols.index(this) < len(self._row)
		return False

	__contains__ = __hasattr__

	def get(self, this, default=None):
		if (this in self._cols) and (self._cols.index(this) < len(self._row)):
			return self._row[self._cols.index(this)]
		return default

	def __getattr__(self, this):
		try:
			return self._row[self._cols.index(this)]
		except:
			raise AttributeError, this

	def __getitem__(self, this):
		return self._row[self._cols.index(this)]

	def __str__(self):
		return "Row(" + ','.join(map(_fmt, zip(self._cols, self._row))) + ")"


class Rowset(object):
	# Rowsets are collections of Row objects.
	#
	# Rowsets support most of the list interface:
	#   iteration, indexing and slicing
	#
	# As well as the following methods: 
	#
	#   IndexedBy(column)
	#     Returns an IndexRowset keyed on given column. Requires the column to
	#     be usable as primary key.
	#
	#   GroupedBy(column)
	#     Returns a FilterRowset keyed on given column. FilterRowset objects
	#     can be accessed like dicts. See FilterRowset class below.
	#
	#   SortBy(column, reverse=True)
	#     Sorts rowset in-place on given column. for a descending sort,
	#     specify reversed=True.
	#
	#   SortedBy(column, reverse=True)
	#     Same as SortBy, except this returns a new rowset object instead of
	#     sorting in-place.
	#
	#   Select(columns, row=False)
	#     Yields a column values tuple (value, ...) for each row in the rowset.
	#     If only one column is requested, then just the column value is
	#     provided instead of the values tuple.
	#     When row=True, each result will be decorated with the entire row.
	#

	def IndexedBy(self, column):
		return IndexRowset(self._cols, self._rows, column)

	def GroupedBy(self, column):
		return FilterRowset(self._cols, self._rows, column)

	def SortBy(self, column, reverse=False):
		ix = self._cols.index(column)
		self.sort(key=lambda e: e[ix], reverse=reverse)

	def SortedBy(self, column, reverse=False):
		rs = self[:]
		rs.SortBy(column, reverse)
		return rs

	def Select(self, *columns, **options):
		if len(columns) == 1:
			i = self._cols.index(columns[0])
			if options.get("row", False):
				for line in self._rows:
					yield (line, line[i])
			else:
				for line in self._rows:
					yield line[i]
		else:
			i = map(self._cols.index, columns)
			if options.get("row", False):
				for line in self._rows:
					yield line, [line[x] for x in i]
			else:
				for line in self._rows:
					yield [line[x] for x in i]


	# -------------

	def __init__(self, cols=None, rows=None):
		self._cols = cols or []
		self._rows = rows or []

	def append(self, row):
		if isinstance(row, list):
			self._rows.append(row)
		elif isinstance(row, Row) and len(row._cols) == len(self._cols):
			self._rows.append(row._row)
		else:
			raise TypeError("incompatible row type")

	def __add__(self, other):
		if isinstance(other, Rowset):
			if len(other._cols) == len(self._cols):
				self._rows += other._rows
		raise TypeError("rowset instance expected")

	def __nonzero__(self):
		return not not self._rows

	def __len__(self):
		return len(self._rows)

	def copy(self):
		return self[:]

	def __getitem__(self, ix):
		if type(ix) is slice:
			return Rowset(self._cols, self._rows[ix])
		return Row(self._cols, self._rows[ix])

	def sort(self, *args, **kw):
		self._rows.sort(*args, **kw)

	def __str__(self):
		return ("Rowset(columns=[%s], rows=%d)" % (','.join(self._cols), len(self)))

	def __getstate__(self):
		return (self._cols, self._rows)

	def __setstate__(self, state):
		self._cols, self._rows = state



class IndexRowset(Rowset):
	# An IndexRowset is a Rowset that keeps an index on a column.
	#
	# The interface is the same as Rowset, but provides an additional method:
	#
	#   Get(key [, default])
	#     Returns the Row mapped to provided key in the index. If there is no
	#     such key in the index, KeyError is raised unless a default value was
	#     specified.
	#

	def Get(self, key, *default):
		row = self._items.get(key, None)
		if row is None:
			if default:
				return default[0]
			raise KeyError, key
		return Row(self._cols, row)

	# -------------

	def __init__(self, cols=None, rows=None, key=None):
		try:
			if "," in key:
				self._ki = ki = [cols.index(k) for k in key.split(",")]
				self.composite = True
			else:
				self._ki = ki = cols.index(key)
				self.composite = False
		except IndexError:
			raise ValueError("Rowset has no column %s" % key)

		Rowset.__init__(self, cols, rows)
		self._key = key

		if self.composite:
			self._items = dict((tuple([row[k] for k in ki]), row) for row in self._rows)
		else:
			self._items = dict((row[ki], row) for row in self._rows)

	def __getitem__(self, ix):
		if type(ix) is slice:
			return IndexRowset(self._cols, self._rows[ix], self._key)
		return Rowset.__getitem__(self, ix)

	def append(self, row):
		Rowset.append(self, row)
		if self.composite:
			self._items[tuple([row[k] for k in self._ki])] = row
		else:
			self._items[row[self._ki]] = row

	def __getstate__(self):
		return (Rowset.__getstate__(self), self._items, self._ki)

	def __setstate__(self, state):
		state, self._items, self._ki = state
		Rowset.__setstate__(self, state)


class FilterRowset(object):
	# A FilterRowset works much like an IndexRowset, with the following
	# differences:
	# - FilterRowsets are accessed much like dicts
	# - Each key maps to a Rowset, containing only the rows where the value
	#   of the column this FilterRowset was made on matches the key.

	def __init__(self, cols=None, rows=None, key=None, key2=None, dict=None):
		if dict is not None:
			self._items = items = dict
		elif cols is not None:
			self._items = items = {}

			idfield = cols.index(key)
			if not key2:
				for row in rows:
					id = row[idfield]
					if id in items:
						items[id].append(row)
					else:
						items[id] = [row]
			else:
				idfield2 = cols.index(key2)
				for row in rows:
					id = row[idfield]
					if id in items:
						items[id][row[idfield2]] = row
					else:
						items[id] = {row[idfield2]:row}

		self._cols = cols
		self.key = key
		self.key2 = key2
		self._bind()

	def _bind(self):
		items = self._items
		self.keys = items.keys
		self.iterkeys = items.iterkeys
		self.__contains__ = items.__contains__
		self.has_key = items.has_key
		self.__len__ = items.__len__
		self.__iter__ = items.__iter__

	def copy(self):
		return FilterRowset(self._cols[:], None, self.key, self.key2, dict=copy.deepcopy(self._items))

	def get(self, key, default=_unspecified):
		try:
			return self[key]
		except KeyError:
			if default is _unspecified:
				raise
		return default

	def __getitem__(self, i):
		if self.key2:
			return IndexRowset(self._cols, None, self.key2, self._items.get(i, {}))
		return Rowset(self._cols, self._items[i])

	def __getstate__(self):
		return (self._cols, self._rows, self._items, self.key, self.key2)

	def __setstate__(self, state):
		self._cols, self._rows, self._items, self.key, self.key2 = state
		self._bind()


########NEW FILE########
