__FILENAME__ = experience
#!/usr/bin/env python

# a hack so you can run it 'python demo/stats.py'
import sys
sys.path.append('.')
sys.path.append('..')
from stackexchange import Site, StackOverflow

user_id = 41981 if len(sys.argv) < 2 else int(sys.argv[1])
print 'StackOverflow user %d\'s experience:' % user_id

so = Site(StackOverflow)
user = so.user(user_id)

print 'Most experienced on %s.' % user.top_answer_tags.fetch()[0].tag_name
print 'Most curious about %s.' % user.top_question_tags.fetch()[0].tag_name

total_questions = len(user.questions.fetch())
unaccepted_questions = len(user.unaccepted_questions.fetch())
accepted = total_questions - unaccepted_questions
rate = accepted / float(total_questions) * 100
print 'Accept rate is %.2f%%.' % rate

########NEW FILE########
__FILENAME__ = highest_voted
#!/usr/bin/env python

# a hack so you can run it 'python demo/stats.py'
import sys
sys.path.append('.')
sys.path.append('..')
from stackauth import StackAuth
from stackexchange import Site, StackOverflow, Sort, DESC

so = Site(StackOverflow)

print 'The highest voted question on StackOverflow is:'
question = so.questions(sort=Sort.Votes, order=DESC)[0]
print '\t%s\t%d' % (question.title, question.score)
print
print 'Look, see:', question.url

########NEW FILE########
__FILENAME__ = narcissism
#!/usr/bin/env python

# a hack so you can run it 'python demo/stats.py'
import sys
sys.path.append('.')
sys.path.append('..')
from stackauth import StackAuth
from stackexchange import Site, StackOverflow

user_id = 41981 if len(sys.argv) < 2 else int(sys.argv[1])
print 'StackOverflow user %d\'s accounts:' % user_id

stack_auth = StackAuth()
so = Site(StackOverflow)
accounts = stack_auth.api_associated(so, user_id)
reputation = {}

for account in accounts:
	print '  %s / %d reputation' % (account.on_site.name, account.reputation)

	# This may seem a slightly backwards way of storing it, but it's easier for finding the max
	reputation[account.reputation] = account.on_site.name

print 'Most reputation on: %s' % reputation[max(reputation)]

########NEW FILE########
__FILENAME__ = object_explorer
#!/usr/bin/env python

# a hack so you can run it 'python demo/object_explorer.py'
import sys
sys.path.append('.')
sys.path.append('..')
from stackauth import StackAuth
from stackexchange import Site, StackOverflow, StackExchangeLazySequence

site = None

print 'Loading sites...',
sys.stdout.flush()
all_sites = StackAuth().sites()
chosen_site_before = False
code_so_far = []

def choose_site():
	global chosen_site_before

	print '\r                \rSelect a site (0 exits):'
	
	i = 1
	for site in all_sites:
		print '%d) %s' % (i, site.name)
		i += 1
	
	if i == 0:
		return
	else:
		site_def = all_sites[int(raw_input('\nSite ID: ')) - 1]
	
	site = site_def.get_site()
	site.app_key = '1_9Gj-egW0q_k1JaweDG8Q'
	site.be_inclusive = True

	if not chosen_site_before:
		print 'Use function names you would when using the Site, etc. objects.'
		print 'return:	Move back up an object.'
		print 'exit:	Quits.'
		print 'dir:		Shows meaningful methods and properties on the current object.'
		print 'dir*:	Same as dir, but includes *all* methods and properties.'
		print 'code:	Show the code you\'d need to get to where you are now.'
		print '! before a non-function means "explore anyway."'
		print 'a prompt ending in []> means the current item is a list.'

		chosen_site_before = True
	return (site, site_def)

def explore(ob, nm, pname=None):
	global code_so_far

	# sometimes, we have to use a different name for variables
	vname = nm if pname is None else pname

	is_dict = isinstance(ob, dict)
	is_list = isinstance(ob, list) or isinstance(ob, tuple) or is_dict
	suffix = '{}' if is_dict else '[]' if is_list else ''

	while True:
		# kind of hackish, but oh, well!
		inp = raw_input('%s%s> ' % (nm, suffix))
		punt_to_default = False

		if inp == 'exit':
			sys.exit(0)
		elif inp == 'return':
			code_so_far = code_so_far[:-1]
			return
		elif inp == 'dir':
			if is_list:
				i = 0
				for item in ob:
					print '%d) %s' % (i, str(item))
					i += 1
			else:
				print repr([x for x in dir(ob) if not x.startswith('_') and x[0].lower() == x[0]])
		elif inp == 'dir*':
			print repr(dir(ob))
		elif inp == 'code':
			print '\n'.join(code_so_far)
		elif is_list:
			try:
				item = ob[inp if is_dict else int(inp)]
				code_so_far.append('%s_item = %s[%s]' % (vname, vname, inp))
				explore(item, vname + '_item')
			except:
				print 'Not in list... continuing as if was an attribute.'
				punt_to_default = True
		elif hasattr(ob, inp) or (len(inp) > 0 and inp[0] == '!') or punt_to_default:
			should_explore = False
			if inp[0] == '!':
				inp = inp[1:]
				should_explore = True

			rval = getattr(ob, inp)
			extra_code = ''

			if hasattr(rval, 'func_code'):
				# it's a function!

				if inp != 'fetch':
					should_explore = True
				
				# we ask the user for each parameter in turn. we offset by one for self, after using reflection to find the parameter names.
				args = []
				for i in range(rval.func_code.co_argcount - 1):
					name = rval.func_code.co_varnames[i + 1]
					value = raw_input(name + ': ')

					if value == '':
						value = None
					else:
						value = eval(value)

					args.append(value)

				if len(args) > 0:
					extra_code = '('
					for arg in args:
						extra_code += repr(arg) + ', '
					extra_code = '%s)' % extra_code[:-2]
				else:
					extra_code = '()'
				
				rval = rval(*args)

			if isinstance(rval, StackExchangeLazySequence):
				print 'Fetching data...',
				sys.stdout.flush()
				rval = rval.fetch()
				print '\r                 \rFetched. You\'ll need to remember to call .fetch() in your code.'
				
				extra_code = '.fetch()'
				should_explore = True
			
			if isinstance(rval, list) or isinstance(rval, tuple):
				should_explore = True

			print repr(rval)
			if should_explore:
				# generate code
				code = '%s = %s.%s%s' % (inp, vname, inp, extra_code)
				code_so_far.append(code)

				explore(rval, inp)
		else:
			print 'Invalid response.'

code_so_far.append('import stackexchange')
while True:
	site, site_def = choose_site()
	code_so_far.append('site = stackexchange.Site("' + site_def.api_endpoint[7:] + '")')
	explore(site, site_def.name, 'site')

########NEW FILE########
__FILENAME__ = question
#!/usr/bin/env python

# Same directory hack
import sys
sys.path.append('.')

import stackexchange
site = stackexchange.Site(stackexchange.StackOverflow)
site.be_inclusive()

id = int(raw_input("Enter a question ID: "))
question = site.question(id)

print '--- %s ---' % question.title
print question.body
print
print '%d answers.' % len(question.answers)

########NEW FILE########
__FILENAME__ = recent_questions
#!/usr/bin/env python

# Same directory hack
import sys
sys.path.append('.')

import stackexchange, thread
so = stackexchange.Site(stackexchange.StackOverflow)
so.be_inclusive()

sys.stdout.write('Loading...')
sys.stdout.flush()

questions = so.recent_questions(pagesize=10, filter='_b')
print '\r #  vote ans view'

cur = 1
for question in questions:
	print '%2d %3d  %3d  %3d \t%s' % (cur, question.score, len(question.answers), question.view_count, question.title)
	cur += 1

num = int(raw_input('Question no.: '))
qu  = questions[num - 1]
print '--- %s' % qu.title
print '%d votes, %d answers, %d views.' % (qu.score, len(qu.answers), qu.view_count)
print 'Tagged: ' + ', '.join(qu.tags)
print
print qu.body[:250] + ('...' if len(qu.body) > 250 else '')

########NEW FILE########
__FILENAME__ = search
#!/usr/bin/env python

# a hack so you can run it 'python demo/stats.py'
import sys
sys.path.append('.')

import stackexchange
so = stackexchange.Site(stackexchange.StackOverflow)

if len(sys.argv) < 2:
	print 'Usage: search.py TERM'
else:
	term = ' '.join(sys.argv[1:])
	print 'Searching for %s...' % term,
	sys.stdout.flush()

	qs = so.search(intitle=term)

	print '\r--- questions with "%s" in title ---' % (term)
	
	for q in qs:
		print '%8d %s' % (q.id, q.title)


########NEW FILE########
__FILENAME__ = stats
#!/usr/bin/env python

# a hack so you can run it 'python demo/stats.py'
import sys
sys.path.append('.')

import stackexchange
so = stackexchange.Site(stackexchange.StackOverflow)
stats = so.stats()

print 'Total questions:\t%d' % stats.total_questions
print '\tAnswered:\t%d' % (stats.total_questions - stats.total_unanswered)
print '\tUnanswered:\t%d' % (stats.total_unanswered)

percent = (stats.total_unanswered / float(stats.total_questions)) * 100
print '%.2f%% unanswered. (%.2f%% answered!)' % (percent, 100 - percent)

########NEW FILE########
__FILENAME__ = versus
#!/usr/bin/env python

import sys
sys.path.append('.')
sys.path.append('..')
import stackexchange, stackauth

if len(sys.argv) < 3:
	print 'Usage: versus.py YOUR_SO_UID THEIR_SO_UID'
	sys.exit(1)

so = stackexchange.Site(stackexchange.StackOverflow)

user1, user2 = (int(x) for x in sys.argv[1:])
rep1, rep2 = {}, {}
username1, username2 = (so.user(x).display_name for x in (user1, user2))
total_rep1, total_rep2 = 0, 0

sites = []

for site in stackauth.StackAuth().api_associated(so, user1):
	rep1[site.on_site.name] = site.reputation
	sites.append(site.on_site.name)
for site in stackauth.StackAuth().api_associated(so, user2):
	rep2[site.on_site.name] = site.reputation

for site in sites:
	total_rep1 += rep1[site]
	if site in rep2:
		total_rep2 += rep2[site]

	max_user = username1
	max_rep, other_rep = rep1[site], rep2.get(site, 0)
	if rep2.get(site, 0) > rep1[site]:
		max_user = username2
		max_rep, other_rep = other_rep, max_rep
	
	diff = max_rep - other_rep

	print '%s: %s wins (+%d)' % (site, max_user, diff)

print 'Overall: %s wins (+%d)' % (username1 if total_rep1 >= total_rep2 else username2, max(total_rep1, total_rep2) - min(total_rep1, total_rep2))


########NEW FILE########
__FILENAME__ = stackauth
# stackauth.py - Implements basic StackAuth support for Py-StackExchange

from stackexchange.web import WebRequestManager
from stackexchange.core import *
from stackexchange import Site, User, UserType
import datetime, re

class SiteState(Enumeration):
	"""Describes the state of a StackExchange site."""
	Normal, OpenBeta, ClosedBeta, LinkedMeta = range(4)

class SiteType(Enumeration):
	'''Describes the type (meta or non-meta) of a StackExchange site.'''
	MainSite, MetaSite = range(2)

class MarkdownExtensions(Enumeration):
	'''Specifies one of the possible extensions to Markdown a site can have enabled.'''
	MathJax, Prettify, Balsamiq, JTab = range(4)

class SiteDefinition(JSONModel):
	"""Contains information about a StackExchange site, reported by StackAuth."""
	transfer = ('aliases', 'api_site_parameter', 'audience', 'favicon_url', 'high_resolution_icon_url', 'icon_url', 'logo_url', 'name', 'open_beta_date', 'related_sites', 'site_state', 'site_type', 'site_url', 'twitter_account', 'api_site_parameter')

	def _extend(self, json, stackauth):
		fixed_state = re.sub(r'_([a-z])', lambda match: match.group(1).upper(), json.site_state)
		fixed_state = fixed_state[0].upper() + fixed_state[1:]

		# To maintain API compatibility only; strictly speaking, we should use api_site_parameter
		# to create new sites, and that's what we do in get_site()
		self.api_endpoint = self.site_url
		# Also to maintain rough API compatibility
		self.description = json.audience

		if hasattr(json, 'closed_beta_date'):
			self.closed_beta_date = datetime.datetime.fromtimestamp(json.closed_beta_date)
		if hasattr(json, 'open_beta_date'):
			self.open_beta_date = datetime.datetime.fromtimestamp(json.open_beta_date)
		if hasattr(json, 'markdown_extensions'):
			self.markdown_extensions = [MarkdownExtensions.from_string(m) for m in json.markdown_extensions]
		if hasattr(json, 'launch_date'):
			# This field is not marked optional in the documentation, but for some reason certain
			# meta sites omit it nonetheless
			self.launch_date = datetime.datetime.fromtimestamp(json.launch_date)

		self.site_state = SiteState.from_string(json.site_state)
		self.site_type = SiteType.from_string(json.site_type)
		self.state = SiteState.from_string(fixed_state)
		self.styling = DictObject(json.styling)
	
	def get_site(self, **kw):
		return Site(self.api_site_parameter, **kw)

class Area51(object):
	def __getattr__(self, attr):
		raise Exception("You have encountered, through StackAuth association, Area51. Area51 is not accessible through the API.")

class UserAssociationSiteListing(JSONModel):
	transfer = ()

	def _extend(self, json, stackauth):
		self.name = json.site_name
		self.api_endpoint = json.site_url
		self.site_url = json.site_url

class UserAssociation(JSONModel):
	transfer = ('display_name', 'reputation', 'email_hash')
	has_endpoint = True
	
	def _extend(self, json, stackauth):
		self.id = json.user_id
		self.user_type = UserType.from_string(json.user_type)

		if not hasattr(json, 'site_url'):
			# assume it's Area 51 if we can't get a site out of it
			self.on_site = Area51()
			self.has_endpoint = False
		else:
			self.on_site = UserAssociationSiteListing(self.json, stackauth)

	def get_user(self):
		return self.on_site.get_site().user(self.id)

class StackAuth(object):
	def __init__(self, domain='api.stackexchange.com'):
		# 2010-07-03: There's no reason to change this now, but you never know.
		# 2013-11-11: Proven right, in a way, by v2.x...
		self.domain = domain
		self.api_version = '2.1'
	
	# These methods are slightly more complex than they
	# could be so they retain rough compatibility with
	# their StackExchange counterparts for paginated sets

	def url(self, u):
		# We need to stick an API version in now for v2.x
		return 'http://' + self.domain + '/' + self.api_version + '/' + u

	def build(self, url, typ, collection, kw = {}):
		mgr = WebRequestManager()
		json, info = mgr.json_request(url, kw)

		return JSONMangler.json_to_resultset(self, json, typ, collection, (self, url, typ, collection, kw))
	
	def sites(self):
		"""Returns information about all the StackExchange sites currently listed."""
		# For optimisation purposes, it is explicitly expected in the documentation to have higher
		# values for the page size for this method.
		return self.build(self.url('sites'), SiteDefinition, 'api_sites', {'pagesize': 120})
	
	def api_associated_from_assoc(self, assoc_id):
		return self.associated_from_assoc(assoc_id, only_valid=True)

	def associated_from_assoc(self, assoc_id, only_valid = False):
		"""Returns, given a user's *association ID*, all their accounts on other StackExchange sites."""
		# In API v2.x, the user_type attribute is not included by default, so we
		# need a filter.
		accounts = self.build(self.url('users/%s/associated' % assoc_id), UserAssociation, 'associated_users', {'filter': '0lWhwQSz'})
		if only_valid:
			return tuple([acc for acc in accounts if acc.has_endpoint])
		else:
			return accounts
	
	def associated(self, site, user_id, **kw):
		"""Returns, given a target site object and a user ID for that site, their associated accounts on other StackExchange sites."""
		user = site.user(user_id)
		if hasattr(user, 'account_id'):
			assoc = user.account_id
			return self.associated_from_assoc(assoc, **kw)
		else:
			return []
	
	def api_associated(self, site, uid):
		return self.associated(site, uid, only_valid=True)
	

########NEW FILE########
__FILENAME__ = core
# stackcore.py - JSONModel/Enumeration + other utility classes that don't really belong now that the API's multi-file
# This file is relatively safe to "import *"

import datetime, urllib2
from math import floor

## JSONModel base class
class JSONModel(object):
	"""The base class of all the objects which describe API objects directly - ie, those which take JSON objects as parameters to their constructor."""

	def __init__(self, json, site, skip_ext=False):
		self.json = json
		self.json_ob = DictObject(json)
		self.site = site

		for f in self.transfer:
			if hasattr(self.json_ob, f):
				setattr(self, f, getattr(self.json_ob, f))

		if hasattr(self, '_extend') and not skip_ext:
			self._extend(self.json_ob, site)

	def fetch(self):
		"""Fetches all the data that the model can describe, not just the attributes which were specified in the original response."""
		if hasattr(self, 'fetch_callback'):
			res = self.fetch_callback(self, self.site)

			if isinstance(res, dict):
				self.__init__(res, self.site)
			elif hasattr(res, 'json'):
				self.__init__(res.json, self.site)
			else:
				raise ValueError('Supplied fetch callback did not return a usable value.')
		else:
			return False

	# Allows the easy creation of updateable, partial classes
	@classmethod
	def partial(cls, fetch_callback, site, populate):
		"""Creates a partial description of the API object, with the proviso that the full set of data can be fetched later."""

		model = cls({}, site, True)

		for k, v in populate.iteritems():
			setattr(model, k, v)

		model.fetch_callback = fetch_callback
		return model

	# for use with Lazy classes that need a callback to actually set the model property
	def _up(self, a):
		"""Returns a function which can be used with the LazySequence class to actually update the results properties on the model with the
new fetched data."""

		def inner(m):
			setattr(self, a, m)
		return inner

class Enumeration(object):
	"""Provides a base class for enumeration classes. (Similar to 'enum' types in other languages.)"""

	@classmethod
	def from_string(cls, text, typ=None):
		'Returns the appropriate enumeration value for the given string, mapping underscored names to CamelCase, or the input string if a mapping could not be made.'
		if typ is not None:
			if hasattr(typ, '_map') and text in typ._map:
				return getattr(typ, typ._map[text])
			elif hasattr(typ, text[0].upper() + text[1:]):
				return getattr(typ, text[0].upper() + text[1:])
			elif '_' in text:
				real_name = ''.join(x.title() for x in text.split('_'))
				if hasattr(typ, real_name):
					return getattr(typ, real_name)
				else:
					return text
			else:
				return text
		else:
			return cls.from_string(text, cls)

class StackExchangeError(Exception):
	"""A generic error thrown on a bad HTTP request during a StackExchange API request."""
	def __init__(self, urlerror):
		self.urlerror = urlerror
	def __str__(self):
		return 'Received HTTP error \'%d\'.' % self.urlerror.code


class StackExchangeResultset(tuple):
	"""Defines an immutable, paginated resultset. This class can be used as a tuple, but provides extended metadata as well, including methods
to fetch the next page."""

	def __new__(cls, items, build_info, has_more = True, page = 1, pagesize = None):
		if pagesize is None:
			pagesize = len(items)

		instance = tuple.__new__(cls, items)
		instance.page, instance.pagesize, instance.build_info = page, pagesize, build_info
		instance.items = items
		instance.has_more = has_more

		return instance

	def reload(self):
		"""Refreshes the data in the resultset with fresh API data. Note that this doesn't work with extended resultsets."""
		# kind of a cheat, but oh well
		return self.fetch_page(self.page)

	def fetch_page(self, page, **kw):
		"""Returns a new resultset containing data from the specified page of the results. It re-uses all parameters that were passed in
to the initial function which created the resultset."""
		new_params = list(self.build_info)
		new_params[4] = new_params[4].copy()
		new_params[4].update(kw)
		new_params[4]['page'] = page

		new_set = new_params[0].build(*new_params[1:])
		new_set.page = page
		return new_set

	def fetch_extended(self, page):
		"""Returns a new resultset containing data from this resultset AND from the specified page."""
		next = self.fetch_page(page)
		extended = self + next

		# max(0, ...) is so a non-zero, positive result for page is always found
		return StackExchangeResultset(extended, self.build_info, next.has_more, page)

	def fetch_next(self):
		"""Returns the resultset of the data in the next page."""
		return self.fetch_page(self.page + 1)

	def extend_next(self):
		"""Returns a new resultset containing data from this resultset AND from the next page."""
		return self.fetch_extended(self.page + 1)

	def fetch(self):
		# Do nothing, but allow multiple fetch calls
		return self

	def __iter__(self):
		return self.next()

	def next(self):
		for obj in self.items:
			yield obj

		current = self
		while current.has_more:
			for obj in current.items:
				yield obj

			try:
				current = current.fetch_next()
				if len(current) == 0:
					return
			except urllib2.HTTPError:
				return

class NeedsAwokenError(Exception):
	"""An error raised when an attempt is made to access a property of a lazy collection that requires the data to have been fetched,
but whose data has not yet been requested."""

	def __init__(self, lazy):
		self.lazy = lazy
	def __str__(self):
		return 'Could not return requested data; the sequence of "%s" has not been fetched.' % self.lazy.m_lazy

class StackExchangeLazySequence(list):
	"""Provides a sequence which *can* contain extra data available on an object. It is 'lazy' in the sense that data is only fetched when
required - not on object creation."""

	def __init__(self, m_type, count, site, url, fetch=None, collection=None, **kw):
		self.m_type = m_type
		self.count = count
		self.site = site
		self.url = url
		self.fetch_callback = fetch
		self.kw = kw
		self.collection = collection if collection != None else self._collection(url)

	def _collection(self, c):
		return c.split('/')[-1]

	def __len__(self):
		if self.count != None:
			return self.count
		else:
			raise NeedsAwokenError(self)

	def fetch(self, **direct_kw):
		"""Fetch, from the API, the data this sequence is meant to hold."""
		# If we have any default parameters, include them, but overwrite any
		# passed in here directly.
		kw = dict(self.kw)
		kw.update(direct_kw)

		res = self.site.build(self.url, self.m_type, self.collection, kw)
		if self.fetch_callback != None:
			self.fetch_callback(res)
		return res

class StackExchangeLazyObject(list):
	"""Provides a proxy to fetching a single item from a collection, lazily."""

	def __init__(self, m_type, site, url, fetch=None, collection=None):
		self.m_type = m_type
		self.site = site
		self.url = url
		self.fetch_callback = fetch
		self.collection = collection if collection != None else self._collection(url)

	def fetch(self, **kw):
		"""Fetch, from the API, the data supposed to be held."""
		res = self.site.build(self.url, self.m_type, self.collection, kw)[0]
		if self.fetch_callback != None:
			self.fetch_callback(res)
		return res

	def __getattr__(self, key):
		raise NeedsAwokenError

#### Hack, because I can't be bothered to fix my mistaking JSON's output for an object not a dict
# (Si jeunesse savait, si vieillesse pouvait...)
# Attrib: Eli Bendersky, http://stackoverflow.com/questions/1305532/convert-python-dict-to-object/1305663#1305663
class DictObject:
    def __init__(self, entries):
		self.__dict__.update(entries)

class JSONMangler(object):
	"""This class handles all sorts of random JSON-handling stuff"""

	@staticmethod
	def paginated_to_resultset(site, json, typ, collection, params):
		# N.B.: We ignore the 'collection' parameter for now, given that it is
		# no longer variable in v2.x, having been replaced by a generic field
		# 'items'. To perhaps be removed completely at some later point.
		items = []
		
		# create strongly-typed objects from the JSON items
		for json_item in json['items']:
			json_item['_params_'] = params[-1] # convenient access to the kw hash
			items.append(typ(json_item, site))

		rs = StackExchangeResultset(items, params, json['has_more'])
		if 'total' in json:
			rs.total = json['total']

		return rs

	@staticmethod
	def normal_to_resultset(site, json, typ, collection):
		# the parameter 'collection' may be need in future, and was needed pre-2.0
		return tuple([typ(x, site) for x in json['items']])

	@classmethod
	def json_to_resultset(cls, site, json, typ, collection, params=None):
		if 'has_more' in json:
			# we have a paginated resultset
			return cls.paginated_to_resultset(site, json, typ, collection, params)
		else:
			# this isn't paginated (unlikely but possible - eg badges)
			return cls.normal_to_resultset(site, json, typ, collection)

def format_relative_date(date):
	"""Takes a datetime object and returns the date formatted as a string e.g. "3 minutes ago", like the real site.
	This is based roughly on George Edison's code from StackApps:
	http://stackapps.com/questions/1009/how-to-format-time-since-xxx-e-g-4-minutes-ago-similar-to-stack-exchange-site/1018#1018"""

	now = datetime.datetime.now()
	diff = (now - date).seconds

	# Anti-repetition! These simplify the code somewhat.
	plural = lambda d: 's' if d != 1 else ''
	frmt   = lambda d: (diff / float(d), plural(diff / float(d)))

	if diff < 60:
		return '%d second%s ago' % frmt(1)
	elif diff < 3600:
		return '%d minute%s ago' % frmt(60)
	elif diff < 86400:
		return '%d hour%s ago' % frmt(3600)
	elif diff < 172800:
		return 'yesterday'
	else:
		return date.strftime('M j / y - H:i')

class Sort(Enumeration):
	Activity = 'activity'
	Views = 'views'
	Creation = 'creation'
	Votes = 'votes'

ASC = 'asc'
DESC = 'desc'

########NEW FILE########
__FILENAME__ = sites
import stackexchange
class __SEAPI(str):
	def __call__(self):
		return stackexchange.Site(self)
StackOverflow = __SEAPI('api.stackoverflow.com')
ServerFault = __SEAPI('api.serverfault.com')
SuperUser = __SEAPI('api.superuser.com')
MetaStackOverflow = __SEAPI('api.meta.stackoverflow.com')
WebApplications = __SEAPI('api.webapps.stackexchange.com')
WebApplicationsMeta = __SEAPI('api.meta.webapps.stackexchange.com')
Gaming = __SEAPI('api.gaming.stackexchange.com')
GamingMeta = __SEAPI('api.meta.gaming.stackexchange.com')
Webmasters = __SEAPI('api.webmasters.stackexchange.com')
WebmastersMeta = __SEAPI('api.meta.webmasters.stackexchange.com')
Cooking = __SEAPI('api.cooking.stackexchange.com')
CookingMeta = __SEAPI('api.meta.cooking.stackexchange.com')
GameDevelopment = __SEAPI('api.gamedev.stackexchange.com')
GameDevelopmentMeta = __SEAPI('api.meta.gamedev.stackexchange.com')
Photography = __SEAPI('api.photo.stackexchange.com')
PhotographyMeta = __SEAPI('api.meta.photo.stackexchange.com')
StatisticalAnalysis = __SEAPI('api.stats.stackexchange.com')
StatisticalAnalysisMeta = __SEAPI('api.meta.stats.stackexchange.com')
Mathematics = __SEAPI('api.math.stackexchange.com')
MathematicsMeta = __SEAPI('api.meta.math.stackexchange.com')
HomeImprovement = __SEAPI('api.diy.stackexchange.com')
HomeImprovementMeta = __SEAPI('api.meta.diy.stackexchange.com')
MetaSuperUser = __SEAPI('api.meta.superuser.com')
MetaServerFault = __SEAPI('api.meta.serverfault.com')
GIS = __SEAPI('api.gis.stackexchange.com')
GISMeta = __SEAPI('api.meta.gis.stackexchange.com')
TeXLaTeX = __SEAPI('api.tex.stackexchange.com')
TeXLaTeXMeta = __SEAPI('api.meta.tex.stackexchange.com')
AskUbuntu = __SEAPI('api.askubuntu.com')
AskUbuntuMeta = __SEAPI('api.meta.askubuntu.com')
PersonalFinanceandMoney = __SEAPI('api.money.stackexchange.com')
PersonalFinanceandMoneyMeta = __SEAPI('api.meta.money.stackexchange.com')
EnglishLanguageandUsage = __SEAPI('api.english.stackexchange.com')
EnglishLanguageandUsageMeta = __SEAPI('api.meta.english.stackexchange.com')
StackApps = __SEAPI('api.stackapps.com')
UserExperience = __SEAPI('api.ux.stackexchange.com')
UserExperienceMeta = __SEAPI('api.meta.ux.stackexchange.com')
UnixandLinux = __SEAPI('api.unix.stackexchange.com')
UnixandLinuxMeta = __SEAPI('api.meta.unix.stackexchange.com')
WordPress = __SEAPI('api.wordpress.stackexchange.com')
WordPressMeta = __SEAPI('api.meta.wordpress.stackexchange.com')
TheoreticalComputerScience = __SEAPI('api.cstheory.stackexchange.com')
TheoreticalComputerScienceMeta = __SEAPI('api.meta.cstheory.stackexchange.com')
Apple = __SEAPI('api.apple.stackexchange.com')
AppleMeta = __SEAPI('api.meta.apple.stackexchange.com')
RoleplayingGames = __SEAPI('api.rpg.stackexchange.com')
RoleplayingGamesMeta = __SEAPI('api.meta.rpg.stackexchange.com')
Bicycles = __SEAPI('api.bicycles.stackexchange.com')
BicyclesMeta = __SEAPI('api.meta.bicycles.stackexchange.com')
Programmers = __SEAPI('api.programmers.stackexchange.com')
ProgrammersMeta = __SEAPI('api.meta.programmers.stackexchange.com')
ElectricalEngineering = __SEAPI('api.electronics.stackexchange.com')
ElectricalEngineeringMeta = __SEAPI('api.meta.electronics.stackexchange.com')
AndroidEnthusiasts = __SEAPI('api.android.stackexchange.com')
AndroidEnthusiastsMeta = __SEAPI('api.meta.android.stackexchange.com')
OnStartups = __SEAPI('api.onstartups.stackexchange.com')
OnStartupsMeta = __SEAPI('api.meta.onstartups.stackexchange.com')
BoardandCardGames = __SEAPI('api.boardgames.stackexchange.com')
BoardandCardGamesMeta = __SEAPI('api.meta.boardgames.stackexchange.com')
Physics = __SEAPI('api.physics.stackexchange.com')
PhysicsMeta = __SEAPI('api.meta.physics.stackexchange.com')
Homebrew = __SEAPI('api.homebrew.stackexchange.com')
HomebrewMeta = __SEAPI('api.meta.homebrew.stackexchange.com')
ITSecurity = __SEAPI('api.security.stackexchange.com')
ITSecurityMeta = __SEAPI('api.meta.security.stackexchange.com')
Writers = __SEAPI('api.writers.stackexchange.com')
WritersMeta = __SEAPI('api.meta.writers.stackexchange.com')
AudioVideoProduction = __SEAPI('api.avp.stackexchange.com')
AudioVideoProductionMeta = __SEAPI('api.meta.avp.stackexchange.com')
GraphicDesign = __SEAPI('api.graphicdesign.stackexchange.com')
GraphicDesignMeta = __SEAPI('api.meta.graphicdesign.stackexchange.com')
DatabaseAdministrators = __SEAPI('api.dba.stackexchange.com')
DatabaseAdministratorsMeta = __SEAPI('api.meta.dba.stackexchange.com')
ScienceFictionandFantasy = __SEAPI('api.scifi.stackexchange.com')
ScienceFictionandFantasyMeta = __SEAPI('api.meta.scifi.stackexchange.com')
CodeReview = __SEAPI('api.codereview.stackexchange.com')
CodeReviewMeta = __SEAPI('api.meta.codereview.stackexchange.com')
CodeGolf = __SEAPI('api.codegolf.stackexchange.com')
CodeGolfMeta = __SEAPI('api.meta.codegolf.stackexchange.com')
QuantitativeFinance = __SEAPI('api.quant.stackexchange.com')
QuantitativeFinanceMeta = __SEAPI('api.meta.quant.stackexchange.com')
ProjectManagement = __SEAPI('api.pm.stackexchange.com')
ProjectManagementMeta = __SEAPI('api.meta.pm.stackexchange.com')
Skeptics = __SEAPI('api.skeptics.stackexchange.com')
SkepticsMeta = __SEAPI('api.meta.skeptics.stackexchange.com')
FitnessandNutrition = __SEAPI('api.fitness.stackexchange.com')
FitnessandNutritionMeta = __SEAPI('api.meta.fitness.stackexchange.com')
DrupalAnswers = __SEAPI('api.drupal.stackexchange.com')
DrupalAnswersMeta = __SEAPI('api.meta.drupal.stackexchange.com')
MotorVehicleMaintenanceandRepair = __SEAPI('api.mechanics.stackexchange.com')
MotorVehicleMaintenanceandRepairMeta = __SEAPI('api.meta.mechanics.stackexchange.com')
Parenting = __SEAPI('api.parenting.stackexchange.com')
ParentingMeta = __SEAPI('api.meta.parenting.stackexchange.com')
SharePoint = __SEAPI('api.sharepoint.stackexchange.com')
SharePointMeta = __SEAPI('api.meta.sharepoint.stackexchange.com')
MusicalPracticeandPerformance = __SEAPI('api.music.stackexchange.com')
MusicalPracticeandPerformanceMeta = __SEAPI('api.meta.music.stackexchange.com')
SoftwareQualityAssuranceandTesting = __SEAPI('api.sqa.stackexchange.com')
SoftwareQualityAssuranceandTestingMeta = __SEAPI('api.meta.sqa.stackexchange.com')
JewishLifeandLearning = __SEAPI('api.judaism.stackexchange.com')
JewishLifeandLearningMeta = __SEAPI('api.meta.judaism.stackexchange.com')
GermanLanguageandUsage = __SEAPI('api.german.stackexchange.com')
GermanLanguageandUsageMeta = __SEAPI('api.meta.german.stackexchange.com')
JapaneseLanguageandUsage = __SEAPI('api.japanese.stackexchange.com')
JapaneseLanguageandUsageMeta = __SEAPI('api.meta.japanese.stackexchange.com')
Astronomy = __SEAPI('api.astronomy.stackexchange.com')
AstronomyMeta = __SEAPI('api.meta.astronomy.stackexchange.com')
Philosophy = __SEAPI('api.philosophy.stackexchange.com')
PhilosophyMeta = __SEAPI('api.meta.philosophy.stackexchange.com')
GardeningandLandscaping = __SEAPI('api.gardening.stackexchange.com')
GardeningandLandscapingMeta = __SEAPI('api.meta.gardening.stackexchange.com')
Travel = __SEAPI('api.travel.stackexchange.com')
TravelMeta = __SEAPI('api.meta.travel.stackexchange.com')
PersonalProductivity = __SEAPI('api.productivity.stackexchange.com')
PersonalProductivityMeta = __SEAPI('api.meta.productivity.stackexchange.com')
Cryptography = __SEAPI('api.crypto.stackexchange.com')
CryptographyMeta = __SEAPI('api.meta.crypto.stackexchange.com')
Literature = __SEAPI('api.literature.stackexchange.com')
LiteratureMeta = __SEAPI('api.meta.literature.stackexchange.com')
SignalProcessing = __SEAPI('api.dsp.stackexchange.com')
SignalProcessingMeta = __SEAPI('api.meta.dsp.stackexchange.com')
FrenchLanguageandUsage = __SEAPI('api.french.stackexchange.com')
FrenchLanguageandUsageMeta = __SEAPI('api.meta.french.stackexchange.com')
Christianity = __SEAPI('api.christianity.stackexchange.com')
ChristianityMeta = __SEAPI('api.meta.christianity.stackexchange.com')
Bitcoin = __SEAPI('api.bitcoin.stackexchange.com')
BitcoinMeta = __SEAPI('api.meta.bitcoin.stackexchange.com')

########NEW FILE########
__FILENAME__ = web
# stackweb.py - Core classes for web-request stuff

import urllib2, httplib, datetime, operator, StringIO, gzip, time, urllib, urlparse
import datetime
try:
	import json
except ImportError:
	import simplejson as json

class TooManyRequestsError(Exception):
	def __str__(self):
		return "More than 30 requests have been made in the last five seconds."

class WebRequest(object):
	data = ''
	info = None

	def __init__(self, data, info):
		self.data = data
		self.info = info
	
	def __str__(self):
		return str(self.data)

class WebRequestManager(object):
	debug = False
	cache = {}

	def __init__(self, impose_throttling=False, throttle_stop=True, cache=True, cache_age=1800):
		# Whether to monitor requests for overuse of the API
		self.impose_throttling = impose_throttling
		# Whether to throw an error (when True) if the limit is reached, or wait until another request
		# can be made (when False).
		self.throttle_stop = throttle_stop
		# Whether to use request caching.
		self.do_cache = cache
		# The time, in seconds, for which to cache a response
		self.cache_age = cache_age
		# The time at which we should resume making requests after receiving a 'backoff' for each method
		self.backoff_expires = {}
	
	# When we last made a request
	window = datetime.datetime.now()
	# Number of requests since last throttle window
	num_requests = 0

	def debug_print(self, *p):
		if WebRequestManager.debug:
			print ' '.join([x if isinstance(x, str) else repr(x) for x in p])
	
	def canon_method_name(self, url):
		# Take the URL relative to the domain, without initial / or parameters
		parsed = urlparse.urlparse(url)
		return '/'.join(parsed.path.split('/')[1:])

	def request(self, url, params):
		now = datetime.datetime.now()

		# Quote URL fields (mostly for 'c#'), but not : in http://
		components = url.split('/')
		url = components[0] + '/'  + ('/'.join(urllib.quote(path) for path in components[1:]))

		done = False
		for k, v in params.iteritems():
			if not done:
				url += '?'
				done = True
			else:
				url += '&'

			url += '%s=%s' % (k, urllib.quote(str(v).encode('utf-8')))
		
		# Now we have the `proper` URL, we can check the cache
		if self.do_cache and url in self.cache:
			timestamp, data = self.cache[url]
			self.debug_print('C>', url, '@', timestamp)

			if (now - timestamp).seconds <= self.cache_age:
				self.debug_print('Hit>', url)
				return data

		# Before we do the actual request, are we going to be throttled?
		def halt(wait_time):
			if self.throttle_stop:
				raise TooManyRequestsError()
			else:
				# Wait the required time, plus a bit of extra padding time.
				time.sleep(wait_time + 0.1)

		if self.impose_throttling:
			# We need to check if we've been told to back off
			method = self.canon_method_name(url)
			backoff_time = self.backoff_expires.get(method, None)
			if backoff_time is not None and backoff_time >= now:
				self.debug_print('backoff: %s until %s' % (method, backoff_time))
				halt((now - backoff_time).seconds)

			if (now - WebRequestManager.window).seconds >= 5:
				WebRequestManager.window = now
				WebRequestManager.num_requests = 0
			WebRequestManager.num_requests += 1
			if WebRequestManager.num_requests > 30:
				halt(5 - (WebRequestManager.window - now).seconds)

		# We definitely do need to go out to the internet, so make the real request
		self.debug_print('R>', url)
		request = urllib2.Request(url)
		
		request.add_header('Accept-encoding', 'gzip')
		req_open = urllib2.build_opener()
		conn = req_open.open(request)

		req_data = conn.read()

		# Handle compressed responses.
		# (Stack Exchange's API sends its responses compressed but intermediary
		# proxies may send them to us decompressed.)
		if conn.info().getheader('Content-Encoding') == 'gzip':
			data_stream = StringIO.StringIO(req_data)
			gzip_stream = gzip.GzipFile(fileobj=data_stream)

			actual_data = gzip_stream.read()
		else:
			actual_data = req_data

		info = conn.info()
		conn.close()

		req_object = WebRequest(actual_data, info)

		# Let's store the response in the cache
		if self.do_cache:
			self.cache[url] = (now, req_object)
			self.debug_print('Store>', url)

		return req_object
	
	def json_request(self, to, params):
		req = self.request(to, params)
		parsed_result = json.loads(req.data)

		# In API v2.x we now need to respect the 'backoff' warning
		if 'backoff' in parsed_result:
			method = self.canon_method_name(to)
			self.backoff_expires[method] = datetime.datetime.now() + parsed_result[backoff]

		return (parsed_result, req.info)


########NEW FILE########
__FILENAME__ = testsuite
import logging

import stackauth, stackexchange, stackexchange.web, unittest
import stackexchange.sites as stacksites
import htmlentitydefs, re

QUESTION_ID = 4
ANSWER_ID = 98
USER_ID = 23901
API_KEY = 'pXlviKYs*UZIwKLPwJGgpg(('

_l = logging.getLogger(__name__)

def _setUp(self):
	self.site = stackexchange.Site(stackexchange.StackOverflow, API_KEY, impose_throttling = True)

stackexchange.web.WebRequestManager.debug = True

htmlentitydefs.name2codepoint['#39'] = 39
def html_unescape(text):
    return re.sub('&(%s);' % '|'.join(htmlentitydefs.name2codepoint),
              lambda m: unichr(htmlentitydefs.name2codepoint[m.group(1)]), text)

class DataTests(unittest.TestCase):
	def setUp(self):
		_setUp(self)

	def test_fetch_paged(self):
		user = stackexchange.Site(stackexchange.Programmers, API_KEY).user(USER_ID)

		answers = user.answers.fetch(pagesize=60)
		for answer in answers:
			# dummy assert.. we're really testing paging here to make sure it doesn't get
			# stuck in an infinite loop. there very well may be a better way of testing this,
			# but it's been a long day and this does the trick
			# this used to test for title's presence, but title has been removed from the
			# default filter
			self.assertTrue(answer.id is not None)

	def test_fetch_question(self):
		s = self.site.question(QUESTION_ID)
		self.assertEqual(html_unescape(s.title), u"When setting a form's opacity should I use a decimal or double?")

	def test_fetch_answer(self):
		s = self.site.answer(ANSWER_ID)

	def test_fetch_answer_comment(self):
		# First try the comments on an answer with lots of comments
		# http://stackoverflow.com/a/22389702
		s = self.site.answer(22389702)
		s.comments.fetch()
		first_comment = s.comments[0]
		self.assertNotEqual(first_comment, None)
		self.assertTrue(first_comment.body)

	def test_fetch_question_comment(self):
		# Now try a question
		# http://stackoverflow.com/a/22342854
		s = self.site.question(22342854)
		s.comments.fetch()
		first_comment = s.comments[0]
		self.assertNotEqual(first_comment, None)
		self.assertTrue(first_comment.body)
	
	def test_post_revisions(self):
		a = self.site.answer(4673436)
		a.revisions.fetch()
		first_revision = a.revisions[0]
		self.assertNotEqual(first_revision, None)
		self.assertEqual(first_revision.post_id, a.id)

	def test_has_body(self):
		q = self.site.question(QUESTION_ID, body=True)
		self.assertTrue(hasattr(q, 'body'))
		self.assertNotEqual(q.body, None)

		a = self.site.answer(ANSWER_ID, body=True)
		self.assertTrue(hasattr(q, 'body'))
		self.assertNotEqual(q.body, None)
	
	def test_tag_synonyms(self):
		syns = self.site.tag_synonyms()
		self.assertTrue(len(syns) > 0)
	
	def test_tag_wiki(self):
		tag = self.site.tag('javascript')
		self.assertEqual(tag.name, 'javascript')
		wiki = tag.wiki.fetch()
		self.assertTrue(len(wiki.excerpt) > 0)
	
	def test_badge_name(self):
		badge = self.site.badge(name = 'Nice Answer')
		self.assertNotEqual(badge, None)
		self.assertEqual(badge.name, 'Nice Answer')
	
	def test_badge_id(self):
		badge = self.site.badge(23)
		self.assertEqual(badge.name, 'Nice Answer')
	
	def test_rep_change(self):
		user = self.site.user(41981)
		user.reputation_detail.fetch()
		recent_change = user.reputation_detail[0]
		self.assertNotEqual(recent_change, None)
		self.assertEqual(recent_change.user_id, user.id)

	def test_timeline(self):
		user = self.site.user(41981)
		user.timeline.fetch()
		event = user.timeline[0]
		self.assertNotEqual(event, None)
		self.assertEqual(event.user_id, user.id)
	
	def test_top_tag(self):
		user = self.site.user(41981)

		user.top_answer_tags.fetch()
		answer_tag = user.top_answer_tags[0]
		self.assertNotEqual(answer_tag, None)
		self.assertTrue(answer_tag.answer_count > 0)

		user.top_question_tags.fetch()
		question_tag = user.top_question_tags[0]
		self.assertNotEqual(question_tag, None)
		self.assertTrue(question_tag.question_count > 0)
	
	def test_privilege(self):
		privileges = self.site.privileges()
		self.assertTrue(len(privileges) > 0)
		self.assertTrue(privileges[0].reputation > 0)

	def test_stackauth_site_types(self):
		s = stackauth.StackAuth()
		for site in s.sites():
			self.assertTrue(site.site_type in {stackauth.SiteType.MainSite, stackauth.SiteType.MetaSite})
	
	def test_stackauth_site_instantiate(self):
		for defn in stackauth.StackAuth().sites():
			site_ob = defn.get_site()
			# Do the same as test_fetch_answer() and hope we don't get an exception
			defn.get_site().answer(ANSWER_ID)
			# Only do it once!
			break


class PlumbingTests(unittest.TestCase):
	def setUp(self):
		_setUp(self)

	def test_key_ratelimit(self):
		# a key was given, so check the rate limit is 10000
		if not hasattr(self.site, 'rate_limit'):
			self.site.question(QUESTION_ID)
		self.assertTrue(self.site.rate_limit[1] == 10000)

	def test_site_constants(self):
		# SOFU should always be present
		self.assertTrue(hasattr(stacksites, 'StackOverflow'))
		self.assertTrue(hasattr(stacksites, 'ServerFault'))
		self.assertTrue(hasattr(stacksites, 'SuperUser'))

	def test_vectorise(self):
		# check different types
		q = self.site.question(QUESTION_ID)
		v = self.site.vectorise(('hello', 10, True, False, q), stackexchange.Question)
		self.assertEqual(v, 'hello;10;true;false;%d' % QUESTION_ID)

	def test_resultset_independence(self):
		# repro code for bug #4 (thanks, beaumartinez!)

		# Create two different sites.
		a = stackexchange.Site('api.askubuntu.com')
		b = self.site

		# Create two different searches from the different sites.
		a_search = a.search(intitle='vim', pagesize=100)
		b_search = b.search(intitle='vim', pagesize=100)

		# (We demonstrate that the second search has a second page.)
		self.assertEqual(len(b_search.fetch_next()), 100)

		# Reset the searches.
		a_search = a.search(intitle='vim', pagesize=100)
		b_search = b.search(intitle='vim', pagesize=100)

		# Exhaust the first search.
		while len(a_search) > 0:
			    a_search = a_search.fetch_next()

		# Try get the next page of the second search. It will be empty.
		# Here's the bug.
		self.assertEqual(len(b_search.fetch_next()), 100)


if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = makedoc
#!/usr/bin/env python
# Creates HTML documentation from api.yml

import yaml

class Function(object):
	def __init__(self, id, tree_ob):
		def use(key, v=None):
			if key in tree_ob:
				val = tree_ob[key]
				
				if isinstance(val, str):
					val = val.replace('<', '&lt;').replace('>', '&gt;')

				setattr(self, key, val)
				return True
			else:
				if v is not None:
					setattr(self, key, v)
				return False

		self.id = id

		use('description', '')
		use('se_route', self.description)

		if not use('unimplemented', False):
			use('function')
			use('returns')
			use('parameters')
			use('see')
			use('example')
	
	@property
	def prototype(self):
		if self.unimplemented:
			raise AttributeError('prototype')
		elif hasattr(self, 'see'):
			return self.see
		else:
			params = ''

			if hasattr(self, 'parameters'):
				params = ', '.join(self.parameters.keys())

			return '%s(%s)' % (self.function, params)

class HTMLDocGenerator(object):
	def __init__(self, file_ob):
		self.categories = []

		self.parse(file_ob)
	
	def parse(self, file_ob):
		self.tree = yaml.load(file_ob)

		unimplemented = 0
		total = 0
	
		for name, category in self.tree.items():
			if name.startswith('__'):
				continue

			current_category = []

			for funct_id, function in category.iteritems():
				f = Function('%s.%s' % (name, funct_id), function)

				if f.unimplemented:
					unimplemented += 1

				total += 1
				current_category.append(f)

			self.categories.append((name, current_category))
	
	def to_html(self):
		html = []

		html.append('<style type="text/css">%s</style>' %  self.tree.get('__style__', ''))

		for category, functions in self.categories:
			html.append('<h2>%s</h2>' % category.title())

			for funct in functions:
				html.append('<a name="%s"></a>' % funct.id)
				html.append('<h3>%s</h3>' % funct.se_route)
				html.append('<div class="api">')

				if hasattr(funct, 'see'):
					html.append('<div class="see">see <a href="#%s">%s</a></div>' % (funct.see, funct.see))
					html.append('</div>')
					continue

				if not funct.unimplemented:
					html.append('<div class="prototype">%s</div>' % funct.prototype)

				html.append('<div class="description">%s</div>' % funct.description)
				
				if funct.unimplemented:
					html.append('<div class="unimplemented">Unimplemented.</div>')
					html.append('</div>')
					continue


				if hasattr(funct, 'returns'):
					html.append('<div class="returns">Returns: <span>%s</span></div>' % funct.returns)

				if hasattr(funct, 'parameters'):
					html.append('<h4>Parameters</h4>')
					html.append('<div class="params">')

					for key, desc in funct.parameters.iteritems():
						html.append('<div><span class="param_name">%s</span> <span class="param_desc">%s</span></div>' % (key, desc))

					html.append('</div>')

				if hasattr(funct, 'example'):
					html.append('<h4>Example</h4>')
					html.append('<pre class="example">%s</pre>' % funct.example)

				html.append('</div>')

		return '\n'.join(html)

if __name__ == '__main__':
	in_handle = open('api.yml')
	out_handle = open('api.html', 'w')

	docgen = HTMLDocGenerator(in_handle)
	out_handle.write(docgen.to_html())

	in_handle.close()
	out_handle.close()

########NEW FILE########
__FILENAME__ = se_inter
#!/usr/bin/env ipython
# Saves me quite a bit of typing during interactive
# testing sessions.
# Just execute.
import sys
sys.path.append('.')

from stackexchange import *
from stackauth import *
#so = Site(StackOverflow, '1_9Gj-egW0q_k1JaweDG8Q')
so = Site(StackOverflow, 'pXlviKYs*UZIwKLPwJGgpg((')

########NEW FILE########
__FILENAME__ = _genconsts
import stackauth

sites = stackauth.StackAuth().sites()
source = ['''import stackexchange
class __SEAPI(str):
	def __call__(self):
		return stackexchange.Site(self)''']

for site in sites:
	name = site.name
	name = name.replace(' ', '')
	name = name.replace('-', '')
	source.append('%s = __SEAPI(\'%s\')' % (name, site.api_endpoint[7:]))

print ('\n'.join(source))

########NEW FILE########
