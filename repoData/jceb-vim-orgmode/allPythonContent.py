__FILENAME__ = PluginExample
# -*- coding: utf-8 -*-

from orgmode import echo, echom, echoe, ORGMODE, apply_count, repeat
from orgmode.menu import Submenu, Separator, ActionEntry
from orgmode.keybinding import Keybinding, Plug, Command

import vim


class Example(object):
	u"""
	Example plugin.

	TODO: Extend this doc!
	"""

	def __init__(self):
		u""" Initialize plugin """
		object.__init__(self)
		# menu entries this plugin should create
		self.menu = ORGMODE.orgmenu + Submenu(u'Example')

		# key bindings for this plugin
		# key bindings are also registered through the menu so only additional
		# bindings should be put in this variable
		self.keybindings = []

		# commands for this plugin
		self.commands = []

	@classmethod
	def action(cls):
		u"""
		Some kind of action.

		:returns: TODO
		"""
		pass

	def register(self):
		u"""
		Registration of the plugin.

		Key bindings and other initialization should be done here.
		"""
		# an Action menu entry which binds "keybinding" to action ":action"
		self.commands.append(Command(u'OrgActionCommand',
				u':py ORGMODE.plugins["Example"].action()'))
		self.keybindings.append(Keybinding(u'keybinding',
				Plug(u'OrgAction', self.commands[-1])))
		self.menu + ActionEntry(u'&Action', self.keybindings[-1])

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-


class PluginError(Exception):
	def __init__(self, message):
		Exception.__init__(self, message)


class BufferNotFound(Exception):
	def __init__(self, message):
		Exception.__init__(self, message)


class BufferNotInSync(Exception):
	def __init__(self, message):
		Exception.__init__(self, message)


class HeadingDomError(Exception):
	def __init__(self, message):
		Exception.__init__(self, message)

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = keybinding
# -*- coding: utf-8 -*-

import vim

MODE_ALL = u'a'
MODE_NORMAL = u'n'
MODE_VISUAL = u'v'
MODE_INSERT = u'i'
MODE_OPERATOR = u'o'

OPTION_BUFFER_ONLY = u'<buffer>'
OPTION_SLIENT = u'<silent>'


def _register(f, name):
	def r(*args, **kwargs):
		p = f(*args, **kwargs)
		if hasattr(p, name) and isinstance(getattr(p, name), list):
			for i in getattr(p, name):
				i.create()
		return p
	return r


def register_keybindings(f):
	return _register(f, u'keybindings')


def register_commands(f):
	return _register(f, u'commands')


class Command(object):
	u""" A vim command """

	def __init__(self, name, command, arguments=u'0', complete=None, overwrite_exisiting=False):
		u"""
		:name:		The name of command, first character must be uppercase
		:command:	The actual command that is executed
		:arguments:	See :h :command-nargs, only the arguments need to be specified
		:complete:	See :h :command-completion, only the completion arguments need to be specified
		"""
		object.__init__(self)

		self._name                = name
		self._command             = command
		self._arguments           = arguments
		self._complete            = complete
		self._overwrite_exisiting = overwrite_exisiting

	def __unicode__(self):
		return u':%s<CR>' % self.name

	def __str__(self):
		return self.__unicode__().encode(u'utf-8')

	@property
	def name(self):
		return self._name

	@property
	def command(self):
		return self._command

	@property
	def arguments(self):
		return self._arguments

	@property
	def complete(self):
		return self._complete

	@property
	def overwrite_exisiting(self):
		return self._overwrite_exisiting

	def create(self):
		u""" Register/create the command
		"""
		vim.command((':command%(overwrite)s -nargs=%(arguments)s %(complete)s %(name)s %(command)s' %
				{u'overwrite': '!' if self.overwrite_exisiting else '',
					u'arguments': self.arguments.encode(u'utf-8'),
					u'complete': '-complete=%s' % self.complete.encode(u'utf-8') if self.complete else '',
					u'name': self.name,
					u'command': self.command}
				).encode(u'utf-8'))


class Plug(object):
	u""" Represents a <Plug> to an abitrary command """

	def __init__(self, name, command, mode=MODE_NORMAL):
		u"""
		:name: the name of the <Plug> should be ScriptnameCommandname
		:command: the actual command
		"""
		object.__init__(self)

		if mode not in (MODE_ALL, MODE_NORMAL, MODE_VISUAL, MODE_INSERT, MODE_OPERATOR):
			raise ValueError(u'Parameter mode not in MODE_ALL, MODE_NORMAL, MODE_VISUAL, MODE_INSERT, MODE_OPERATOR')
		self._mode = mode

		self.name = name
		self.command = command
		self.created = False

	def __unicode__(self):
		return u'<Plug>%s' % self.name

	def __str__(self):
		return self.__unicode__().encode(u'utf-8')

	def create(self):
		if not self.created:
			self.created = True
			cmd = self._mode
			if cmd == MODE_ALL:
				cmd = u''
			vim.command((u':%snoremap %s %s' % (cmd, str(self), self.command)).encode(u'utf-8'))

	@property
	def mode(self):
		return self._mode


class Keybinding(object):
	u""" Representation of a single key binding """

	def __init__(self, key, action, mode=None, options=None, remap=True, buffer_only=True, silent=True):
		u"""
		:key: the key(s) action is bound to
		:action: the action triggered by key(s)
		:mode: definition in which vim modes the key binding is valid. Should be one of MODE_*
		:option: list of other options like <silent>, <buffer> ...
		:repmap: allow or disallow nested mapping
		:buffer_only: define the key binding only for the current buffer
		"""
		object.__init__(self)
		self._key = key
		self._action = action

		# grab mode from plug if not set otherwise
		if isinstance(self._action, Plug) and not mode:
			mode = self._action.mode

		if mode not in (MODE_ALL, MODE_NORMAL, MODE_VISUAL, MODE_INSERT, MODE_OPERATOR):
			raise ValueError(u'Parameter mode not in MODE_ALL, MODE_NORMAL, MODE_VISUAL, MODE_INSERT, MODE_OPERATOR')
		self._mode = mode
		self._options = options
		if self._options is None:
			self._options = []
		self._remap = remap
		self._buffer_only = buffer_only
		self._silent = silent

		if self._buffer_only and OPTION_BUFFER_ONLY not in self._options:
			self._options.append(OPTION_BUFFER_ONLY)

		if self._silent and OPTION_SLIENT not in self._options:
			self._options.append(OPTION_SLIENT)

	@property
	def key(self):
		return self._key

	@property
	def action(self):
		return str(self._action)

	@property
	def mode(self):
		return self._mode

	@property
	def options(self):
		return self._options[:]

	@property
	def remap(self):
		return self._remap

	@property
	def buffer_only(self):
		return self._buffer_only

	@property
	def silent(self):
		return self._silent

	def create(self):
		from orgmode._vim import ORGMODE, echom

		cmd = self._mode
		if cmd == MODE_ALL:
			cmd = u''
		if not self._remap:
			cmd += u'nore'
		try:
			create_mapping = True
			if isinstance(self._action, Plug):
				# create plug
				self._action.create()
				if int(vim.eval((u'hasmapto("%s")' % (self._action, )).encode(u'utf-8'))):
					create_mapping = False
			if isinstance(self._action, Command):
				# create command
				self._action.create()

			if create_mapping:
				vim.command((u':%smap %s %s %s' % (cmd, u' '.join(self._options), self._key, self._action)).encode(u'utf-8'))
		except Exception, e:
			if ORGMODE.debug:
				echom(u'Failed to register key binding %s %s' % (self._key, self._action))


# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = agenda
# -*- coding: utf-8 -*-

u"""
	Agenda
	~~~~~~~~~~~~~~~~~~

	The agenda is one of the main concepts of orgmode. It allows to
	collect TODO items from multiple org documents in an agenda view.

	Features:
	* filtering
	* sorting
"""

from orgmode.liborgmode.agendafilter import filter_items
from orgmode.liborgmode.agendafilter import is_within_week_and_active_todo
from orgmode.liborgmode.agendafilter import contains_active_todo
from orgmode.liborgmode.agendafilter import contains_active_date


class AgendaManager(object):
	u"""Simple parsing of Documents to create an agenda."""

	def __init__(self):
		super(AgendaManager, self).__init__()

	def get_todo(self, documents):
		u"""
		Get the todo agenda for the given documents (list of document).
		"""
		filtered = []
		for i, document in enumerate(documents):
			# filter and return headings
			tmp = filter_items(document.all_headings(), [contains_active_todo])
			filtered.extend(tmp)
		return sorted(filtered)

	def get_next_week_and_active_todo(self, documents):
		u"""
		Get the agenda for next week for the given documents (list of
		document).
		"""
		filtered = []
		for i, document in enumerate(documents):
			# filter and return headings
			tmp = filter_items(
				document.all_headings(),
				[is_within_week_and_active_todo])
			filtered.extend(tmp)
		return sorted(filtered)

	def get_timestamped_items(self, documents):
		u"""
		Get all time-stamped items in a time-sorted way for the given
		documents (list of document).
		"""
		filtered = []
		for i, document in enumerate(documents):
			# filter and return headings
			tmp = filter_items(
				document.all_headings(),
				[contains_active_date])
			filtered.extend(tmp)
		return sorted(filtered)

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = agendafilter
# -*- coding: utf-8 -*-

u"""
	agendafilter
	~~~~~~~~~~~~~~~~

	AgendaFilter contains all the filters that can be applied to create the
	agenda.


	All functions except filter_items() in the module are filters. Given a
	heading they return if the heading meets the critera of the filter.

	The function filter_items() can combine different filters and only returns
	the filtered headings.
"""

from datetime import datetime
from datetime import timedelta


def filter_items(headings, filters):
	u"""
	Filter the given headings. Return the list of headings which were not
	filtered.

	:headings: is an list of headings
	:filters: is the list of filters that are to be applied. all function in
			this module (except this function) are filters.

	You can use it like this:

	>>> filtered = filter_items(headings, [contains_active_date,
				contains_active_todo])

	"""
	filtered = headings
	for f in filters:
		filtered = filter(f, filtered)
	return filtered


def is_within_week(heading):
	u"""
	Return True if the date in the deading is within a week in the future (or
	older.
	"""
	if contains_active_date(heading):
		next_week = datetime.today() + timedelta(days=7)
		if heading.active_date < next_week:
			return True


def is_within_week_and_active_todo(heading):
	u"""
	Return True if heading contains an active TODO and the date is within a
	week.
	"""
	return is_within_week(heading) and contains_active_todo(heading)


def contains_active_todo(heading):
	u"""
	Return True if heading contains an active TODO.

	FIXME: the todo checking should consider a number of different active todo
	states
	"""
	return heading.todo == u"TODO"


def contains_active_date(heading):
	u"""
	Return True if heading contains an active date.
	"""
	return not(heading.active_date is None)

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

"""
	base
	~~~~~~~~~~

	Here are some really basic data structures that are used throughout
	the liborgmode.
"""

from UserList import UserList


def flatten_list(l):
	"""TODO"""
	res = []
	if type(l) in (tuple, list) or isinstance(l, UserList):
		for i in l:
			if type(i) in (list, tuple) or isinstance(i, UserList):
				res.extend(flatten_list(i))
			else:
				res.append(i)
	return res


class Direction():
	u"""
	Direction is used to indicate the direction of certain actions.

	Example: it defines the direction headings get parted in.
	"""
	FORWARD = 1
	BACKWARD = 2


class MultiPurposeList(UserList):
	u"""
	A Multi Purpose List is a list that calls a user defined hook on
	change. The implementation is very basic - the hook is called without any
	parameters. Otherwise the Multi Purpose List can be used like any other
	list.

	The member element "data" can be used to fill the list without causing the
	list to be marked dirty. This should only be used during initialization!
	"""

	def __init__(self, initlist=None, on_change=None):
		UserList.__init__(self, initlist)
		self._on_change = on_change

	def _changed(self):
		u"""
		Call hook
		"""
		if callable(self._on_change):
			self._on_change()

	def __setitem__(self, i, item):
		UserList.__setitem__(self, i, item)
		self._changed()

	def __delitem__(self, i):
		UserList.__delitem__(self, i)
		self._changed()

	def __setslice__(self, i, j, other):
		UserList.__setslice__(self, i, j, other)
		self._changed()

	def __delslice__(self, i, j):
		UserList.__delslice__(self, i, j)
		self._changed()

	def __getslice__(self, i, j):
		# fix UserList - don't return a new list of the same type but just the
		# normal list item
		i = max(i, 0)
		j = max(j, 0)
		return self.data[i:j]

	def __iadd__(self, other):
		res = UserList.__iadd__(self, other)
		self._changed()
		return res

	def __imul__(self, n):
		res = UserList.__imul__(self, n)
		self._changed()
		return res

	def append(self, item):
		UserList.append(self, item)
		self._changed()

	def insert(self, i, item):
		UserList.insert(self, i, item)
		self._changed()

	def pop(self, i=-1):
		item = self[i]
		del self[i]
		return item

	def remove(self, item):
		self.__delitem__(self.index(item))

	def reverse(self):
		UserList.reverse(self)
		self._changed()

	def sort(self, *args, **kwds):
		UserList.sort(self, *args, **kwds)
		self._changed()

	def extend(self, other):
		UserList.extend(self, other)
		self._changed()


def get_domobj_range(content=[], position=0, direction=Direction.FORWARD, identify_fun=None):
	u"""
	Get the start and end line number of the dom obj lines from content.

	:content:		String to be recognized dom obj
	:positon:		Line number in content
	:direction:		Search direction
	:identify_fun:  A identify function to recognize dom obj(Heading, Checkbox) title string.

	:return:		Start and end line number for the recognized dom obj.
	"""
	len_cb = len(content)

	if position < 0 or position > len_cb:
		return (None, None)

	tmp_line = position
	start = None
	end = None

	if direction == Direction.FORWARD:
		while tmp_line < len_cb:
			if identify_fun(content[tmp_line]) is not None:
				if start is None:
					start = tmp_line
				elif end is None:
					end = tmp_line - 1
				if start is not None and end is not None:
					break
			tmp_line += 1
	else:
		while tmp_line >= 0 and tmp_line < len_cb:
			if identify_fun(content[tmp_line]) is not None:
				if start is None:
					start = tmp_line
				elif end is None:
					end = tmp_line - 1
				if start is not None and end is not None:
					break
			tmp_line -= 1 if start is None else -1

	return (start, end)

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = checkboxes
# -*- coding: utf-8 -*-

"""
	checkboxes
	~~~~~~~~~

	TODO: explain this :)
"""

import re
from UserList import UserList

import vim
from orgmode.liborgmode.base import MultiPurposeList, flatten_list
from orgmode.liborgmode.orgdate import OrgTimeRange
from orgmode.liborgmode.orgdate import get_orgdate
from orgmode.liborgmode.dom_obj import DomObj, DomObjList, REGEX_SUBTASK, REGEX_SUBTASK_PERCENT, REGEX_HEADING, REGEX_CHECKBOX


class Checkbox(DomObj):
	u""" Structural checkbox object """
	STATUS_ON = u'[X]'
	STATUS_OFF = u'[ ]'
	# intermediate status
	STATUS_INT = u'[-]'

	def __init__(self, level=1, type=u'-', title=u'', status=u'[ ]', body=None):
		u"""
		:level:		Indent level of the checkbox
		:type:		Type of the checkbox list (-, +, *)
		:title:		Title of the checkbox
		:status:	Status of the checkbox ([ ], [X], [-])
		:body:		Body of the checkbox
		"""
		DomObj.__init__(self, level=level, title=title, body=body)

		# heading
		self._heading = None

		self._children = CheckboxList(obj=self)
		self._dirty_checkbox = False
		# list type
		self._type = u'-'
		if type:
			self.type = type
		# status
		self._status = Checkbox.STATUS_OFF
		if status:
			self.status = status

	def __unicode__(self):
		return u' ' * self.level + self.type + u' ' + \
			(self.status + u' ' if self.status else u'') + self.title

	def __str__(self):
		return self.__unicode__().encode(u'utf-8')

	def __len__(self):
		# 1 is for the heading's title
		return 1 + len(self.body)

	def copy(self, including_children=True, parent=None):
		u"""
		Create a copy of the current checkbox. The checkbox will be completely
		detached and not even belong to a document anymore.

		:including_children:	If True a copy of all children is create as
								well. If False the returned checkbox doesn't
								have any children.
		:parent:				Don't use this parameter. It's set
								automatically.
		"""
		checkbox = self.__class__(
			level=self.level, title=self.title,
			body=self.body[:])
		if parent:
			parent.children.append(checkbox)
		if including_children and self.children:
			for item in self.children:
				item.copy(
					including_children=including_children,
					parent=checkbox)
		checkbox._orig_start = self._orig_start
		checkbox._orig_len = self._orig_len

		checkbox._dirty_heading = self.is_dirty_checkbox

		return checkbox

	@classmethod
	def parse_checkbox_from_data(cls, data, heading=None, orig_start=None):
		u""" Construct a new checkbox from the provided data

		:data:			List of lines
		:heading:		The heading object this checkbox belongs to
		:orig_start:	The original start of the heading in case it was read
						from a document. If orig_start is provided, the
						resulting heading will not be marked dirty.

		:returns:	The newly created checkbox
		"""
		def parse_title(heading_line):
			# checkbox is not heading
			if REGEX_HEADING.match(heading_line) is not None:
				return None
			m = REGEX_CHECKBOX.match(heading_line)
			if m:
				r = m.groupdict()
				return (len(r[u'level']), r[u'type'], r[u'status'], r[u'title'])

			return None

		if not data:
			raise ValueError(u'Unable to create checkbox, no data provided.')

		# create new checkbox
		nc = cls()
		nc.level, nc.type, nc.status, nc.title = parse_title(data[0])
		nc.body = data[1:]
		if orig_start is not None:
			nc._dirty_heading = False
			nc._dirty_body = False
			nc._orig_start = orig_start
			nc._orig_len = len(nc)
		if heading:
			nc._heading = heading

		return nc

	def update_subtasks(self, total=0, on=0):
		if total != 0:
			percent = (on * 100) / total
		else:
			percent = 0

		count = "%d/%d" % (on, total)
		self.title = REGEX_SUBTASK.sub("[%s]" % (count), self.title)
		self.title = REGEX_SUBTASK_PERCENT.sub("[%d%%]" % (percent), self.title)
		d = self._heading.document.write_checkbox(self, including_children=False)

	@classmethod
	def identify_checkbox(cls, line):
		u""" Test if a certain line is a checkbox or not.

		:line: the line to check

		:returns: indent_level
		"""
		# checkbox is not heading
		if REGEX_HEADING.match(line) is not None:
			return None
		m = REGEX_CHECKBOX.match(line)
		if m:
			r = m.groupdict()
			return len(r[u'level'])

		return None

	@property
	def is_dirty(self):
		u""" Return True if the heading's body is marked dirty """
		return self._dirty_checkbox or self._dirty_body

	@property
	def is_dirty_checkbox(self):
		u""" Return True if the heading is marked dirty """
		return self._dirty_checkbox

	def get_index_in_parent_list(self):
		""" Retrieve the index value of current checkbox in the parents list of
		checkboxes. This works also for top level checkboxes.

		:returns:	Index value or None if heading doesn't have a
					parent/document or is not in the list of checkboxes
		"""
		if self.parent:
			return super(Checkbox, self).get_index_in_parent_list()
		elif self.document:
			l = self.get_parent_list()
			if l:
				return l.index(self)

	def get_parent_list(self):
		""" Retrieve the parents' list of headings. This works also for top
		level headings.

		:returns:	List of headings or None if heading doesn't have a
					parent/document or is not in the list of headings
		"""
		if self.parent:
			return super(Checkbox, self).get_parent_list()
		elif self.document:
			if self in self.document.checkboxes:
				return self.document.checkboxes

	def set_dirty(self):
		u""" Mark the heading and body dirty so that it will be rewritten when
		saving the document """
		self._dirty_checkbox = True
		self._dirty_body = True
		if self._document:
			self._document.set_dirty_document()

	def set_dirty_checkbox(self):
		u""" Mark the checkbox dirty so that it will be rewritten when saving the
		document """
		self._dirty_checkbox = True
		if self._document:
			self._document.set_dirty_document()

	@property
	def previous_checkbox(self):
		u""" Serialized access to the previous checkbox """
		return super(Checkbox, self).previous_item

	@property
	def next_checkbox(self):
		u""" Serialized access to the next checkbox """
		return super(Checkbox, self).next_item

	@property
	def first_checkbox(self):
		u""" Access to the first child heading or None if no children exist """
		if self.children:
			return self.children[0]

	@property
	def start(self):
		u""" Access to the starting line of the checkbox """
		if self.document is None:
			return self._orig_start

		# static computation of start
		if not self.document.is_dirty:
			return self._orig_start

		# dynamic computation of start, really slow!
		def compute_start(h):
			if h:
				return len(h) + compute_start(h.previous_checkbox)
		return compute_start(self.previous_checkbox)

	def toggle(self):
		u""" Toggle status of this checkbox """
		if self.status == Checkbox.STATUS_OFF:
			self.status = Checkbox.STATUS_ON
		else:
			self.status = Checkbox.STATUS_OFF
		self.set_dirty()

	def all_siblings(self):
		if not self.parent:
			p = self._heading
		else:
			p = self.parent
			if not p.children:
				raise StopIteration()

		c = p.first_checkbox
		while c:
			yield c
			c = c.next_sibling
		raise StopIteration()

	def all_children(self):
		if not self.children:
			raise StopIteration()

		c = self.first_checkbox
		while c:
			yield c
			for d in c.all_children():
				yield d
			c = c.next_sibling

		raise StopIteration()

	def all_siblings_status(self):
		u""" Return checkboxes status for currnet checkbox's all siblings

		:return: (total, on)
			total: total # of checkboxes
			on:	   # of checkboxes which are on
		"""
		total, on = 0, 0
		for c in self.all_siblings():
			if c.status is not None:
				total += 1

				if c.status == Checkbox.STATUS_ON:
					on += 1

		return (total, on)

	def are_children_all(self, status):
		u""" Check all children checkboxes status """
		clen = len(self.children)
		for i in range(clen):
			if self.children[i].status != status:
				return False
			# recursively check children's status
			if not self.children[i].are_children_all(status):
				return False

		return True

	def is_child_one(self, status):
		u""" Return true, if there is one child with given status """
		clen = len(self.children)
		for i in range(clen):
			if self.children[i].status == status:
				return True

		return False

	def are_siblings_all(self, status):
		u""" Check all sibling checkboxes status """
		for c in self.all_siblings():
			if c.status != status:
				return False

		return True

	def level():
		u""" Access to the checkbox indent level """
		def fget(self):
			return self._level

		def fset(self, value):
			self._level = int(value)
			self.set_dirty_checkbox()

		def fdel(self):
			self.level = None

		return locals()
	level = property(**level())

	def title():
		u""" Title of current checkbox """
		def fget(self):
			return self._title.strip()

		def fset(self, value):
			if type(value) not in (unicode, str):
				raise ValueError(u'Title must be a string.')
			v = value
			if type(v) == str:
				v = v.decode(u'utf-8')
			self._title = v.strip()
			self.set_dirty_checkbox()

		def fdel(self):
			self.title = u''

		return locals()
	title = property(**title())

	def status():
		u""" status of current checkbox """
		def fget(self):
			return self._status

		def fset(self, value):
			self._status = value
			self.set_dirty()

		def fdel(self):
			self._status = u''

		return locals()
	status = property(**status())

	def type():
		u""" type of current checkbox list type """
		def fget(self):
			return self._type

		def fset(self, value):
			self._type = value

		def fdel(self):
			self._type = u''

		return locals()
	type = property(**type())


class CheckboxList(DomObjList):
	u"""
	Checkbox List
	"""
	def __init__(self, initlist=None, obj=None):
		"""
		:initlist:	Initial data
		:obj:		Link to a concrete Checkbox or Document object
		"""
		# it's not necessary to register a on_change hook because the heading
		# list will itself take care of marking headings dirty or adding
		# headings to the deleted headings list
		DomObjList.__init__(self, initlist, obj)

	@classmethod
	def is_checkbox(cls, obj):
		return CheckboxList.is_domobj(obj)

	def _get_heading(self):
		if self.__class__.is_checkbox(self._obj):
			return self._obj._document
		return self._obj


# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = documents
# -*- coding: utf-8 -*-

"""
	documents
	~~~~~~~~~

	TODO: explain this :)
"""

from UserList import UserList

from orgmode.liborgmode.base import MultiPurposeList, flatten_list, Direction, get_domobj_range
from orgmode.liborgmode.headings import Heading, HeadingList


class Document(object):
	u"""
	Representation of a whole org-mode document.

	A Document consists basically of headings (see Headings) and some metadata.

	TODO: explain the 'dirty' mechanism
	"""

	def __init__(self):
		u"""
		Don't call this constructor directly but use one of the concrete
		implementations.

		TODO: what are the concrete implementatiions?
		"""
		object.__init__(self)

		# is a list - only the Document methods should work on this list!
		self._content = None
		self._dirty_meta_information = False
		self._dirty_document = False
		self._meta_information = MultiPurposeList(on_change=self.set_dirty_meta_information)
		self._orig_meta_information_len = None
		self._headings = HeadingList(obj=self)
		self._deleted_headings = []

		# settings needed to align tags properly
		self._tabstop = 8
		self._tag_column = 77

		self.todo_states = [u'TODO', u'DONE']

	def __unicode__(self):
		if self.meta_information is None:
			return u'\n'.join(self.all_headings())
		return u'\n'.join(self.meta_information) + u'\n' + u'\n'.join([u'\n'.join([unicode(i)] + i.body) for i in self.all_headings()])

	def __str__(self):
		return self.__unicode__().encode(u'utf-8')

	def get_all_todo_states(self):
		u""" Convenience function that returns all todo and done states and
		sequences in one big list.

		:returns:	[all todo/done states]
		"""
		return flatten_list(self.get_todo_states())

	def get_todo_states(self):
		u""" Returns a list containing a tuple of two lists of allowed todo
		states split by todo and done states. Multiple todo-done state
		sequences can be defined.

		:returns:	[([todo states], [done states]), ..]
		"""
		return self.todo_states

	def tabstop():
		u""" Tabstop for this document """
		def fget(self):
			return self._tabstop

		def fset(self, value):
			self._tabstop = value

		return locals()
	tabstop = property(**tabstop())

	def tag_column():
		u""" The column all tags are right-aligned to """
		def fget(self):
			return self._tag_column

		def fset(self, value):
			self._tag_column = value

		return locals()
	tag_column = property(**tag_column())

	def init_dom(self, heading=Heading):
		u""" Initialize all headings in document - build DOM. This method
		should be call prior to accessing the document.

		:returns:	self
		"""
		def init_heading(_h):
			u"""
			:returns	the initialized heading
			"""
			start = _h.end + 1
			prev_heading = None
			while True:
				new_heading = self.find_heading(start, heading=heading)

				# * Heading 1 <- heading
				# * Heading 1 <- sibling
				# or
				# * Heading 2 <- heading
				# * Heading 1 <- parent's sibling
				if not new_heading or \
					new_heading.level <= _h.level:
					break

				# * Heading 1 <- heading
				#  * Heading 2 <- first child
				#  * Heading 2 <- another child
				new_heading._parent = _h
				if prev_heading:
					prev_heading._next_sibling = new_heading
					new_heading._previous_sibling = prev_heading
				_h.children.data.append(new_heading)
				# the start and end computation is only
				# possible when the new heading was properly
				# added to the document structure
				init_heading(new_heading)
				if new_heading.children:
					# skip children
					start = new_heading.end_of_last_child + 1
				else:
					start = new_heading.end + 1
				prev_heading = new_heading

			return _h

		h = self.find_heading(heading=heading)
		# initialize meta information
		if h:
			self._meta_information.data.extend(self._content[:h._orig_start])
		else:
			self._meta_information.data.extend(self._content[:])
		self._orig_meta_information_len = len(self.meta_information)

		# initialize dom tree
		prev_h = None
		while h:
			if prev_h:
				prev_h._next_sibling = h
				h._previous_sibling = prev_h
			self.headings.data.append(h)
			init_heading(h)
			prev_h = h
			h = self.find_heading(h.end_of_last_child + 1, heading=heading)

		return self

	def meta_information():
		u"""
		Meta information is text that precedes all headings in an org-mode
		document. It might contain additional information about the document,
		e.g. author
		"""
		def fget(self):
			return self._meta_information

		def fset(self, value):
			if self._orig_meta_information_len is None:
				self._orig_meta_information_len = len(self.meta_information)
			if type(value) in (list, tuple) or isinstance(value, UserList):
				self._meta_information[:] = flatten_list(value)
			elif type(value) in (str, ):
				self._meta_information[:] = value.decode(u'utf-8').split(u'\n')
			elif type(value) in (unicode, ):
				self._meta_information[:] = value.split(u'\n')
			self.set_dirty_meta_information()

		def fdel(self):
			self.meta_information = u''

		return locals()
	meta_information = property(**meta_information())

	def headings():
		u""" List of top level headings """
		def fget(self):
			return self._headings

		def fset(self, value):
			self._headings[:] = value

		def fdel(self):
			del self.headings[:]

		return locals()
	headings = property(**headings())

	def write(self):
		u""" write the document

		:returns:	True if something was written, otherwise False
		"""
		raise NotImplementedError(u'Abstract method, please use concrete impelementation!')

	def set_dirty_meta_information(self):
		u""" Mark the meta information dirty so that it will be rewritten when
		saving the document """
		self._dirty_meta_information = True

	def set_dirty_document(self):
		u""" Mark the whole document dirty. When changing a heading this
		method must be executed in order to changed computation of start and
		end positions from a static to a dynamic computation """
		self._dirty_document = True

	@property
	def is_dirty(self):
		u"""
		Return information about unsaved changes for the document and all
		related headings.

		:returns:	 Return True if document contains unsaved changes.
		"""
		if self.is_dirty_meta_information:
			return True

		if self.is_dirty_document:
			return True

		if self._deleted_headings:
			return True

		return False

	@property
	def is_dirty_meta_information(self):
		u""" Return True if the meta information is marked dirty """
		return self._dirty_meta_information

	@property
	def is_dirty_document(self):
		u""" Return True if the document is marked dirty """
		return self._dirty_document

	def all_headings(self):
		u""" Iterate over all headings of the current document in serialized
		order

		:returns:	Returns an iterator object which returns all headings of
					the current file in serialized order
		"""
		if not self.headings:
			raise StopIteration()

		h = self.headings[0]
		while h:
			yield h
			h = h.next_heading
		raise StopIteration()

	def find_heading(
		self, position=0, direction=Direction.FORWARD,
		heading=Heading, connect_with_document=True):
		u""" Find heading in the given direction

		:postition: starting line, counting from 0 (in vim you start
				counting from 1, don't forget)
		:direction: downwards == Direction.FORWARD,
				upwards == Direction.BACKWARD
		:heading:   Heading class from which new heading objects will be
				instanciated
		:connect_with_document: if True, the newly created heading will be
				connected with the document, otherwise not

		:returns:	New heading object or None
		"""
		(start, end) = get_domobj_range(content=self._content, position=position, direction=direction, identify_fun=heading.identify_heading)

		if start is not None and end is None:
			end = len(self._content) - 1
		if start is not None and end is not None:
			return heading.parse_heading_from_data(
				self._content[start:end + 1], self.get_all_todo_states(),
				document=self if connect_with_document else None, orig_start=start)


# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = dom_obj
# -*- coding: utf-8 -*-

"""
	dom object
	~~~~~~~~~~

	TODO: explain this :)
"""

import re
from UserList import UserList
from orgmode.liborgmode.base import MultiPurposeList, flatten_list

# breaking down tasks regex
REGEX_SUBTASK = re.compile(r'\[(\d*)/(\d*)\]')
REGEX_SUBTASK_PERCENT = re.compile(r'\[(\d*)%\]')

# heading regex
REGEX_HEADING = re.compile(
	r'^(?P<level>\*+)(\s+(?P<title>.*?))?\s*(\s(?P<tags>:[\w_:@]+:))?$',
	flags=re.U | re.L)
REGEX_TAG = re.compile(
	r'^\s*((?P<title>[^\s]*?)\s+)?(?P<tags>:[\w_:@]+:)$',
	flags=re.U | re.L)
REGEX_TODO = re.compile(r'^[^\s]*$')

# checkbox regex:
#   - [ ] checkbox item
# - [X] checkbox item
# - [ ]
# - no status checkbox
UnOrderListType = [u'-', 'u+', 'u*']
OrderListType = [u'.', u')']
REGEX_CHECKBOX = re.compile(
	r'^(?P<level>\s*)(?P<type>[%s]|\w+[%s])\s*(?P<status>\[.\])?\s*(?P<title>.*)$'
	% (''.join(UnOrderListType), ''.join(OrderListType)), flags=re.U | re.L)


class DomObj(object):
	u"""
	A DomObj is DOM structure element, like Heading and Checkbox.
	Its purpose is to abstract the same parts of Heading and Checkbox objects,
	and make code reusable.

	All methods and properties are extracted from Heading object.
	Heading and Checkbox objects inherit from DomObj, and override some specific
	methods in their own objects.

	Normally, we don't intend to use DomObj directly. However, we can add some more
	DOM structure element based on this class to make code more concise.
	"""

	def __init__(self, level=1, title=u'', body=None):
		u"""
		:level:		Level of the dom object
		:title:		Title of the dom object
		:body:		Body of the dom object
		"""
		object.__init__(self)

		self._document = None
		self._parent = None
		self._previous_sibling = None
		self._next_sibling = None
		self._children = MultiPurposeList()
		self._orig_start = None
		self._orig_len = 0

		self._level = level
		# title
		self._title = u''
		if title:
			self.title = title

		# body
		self._dirty_body = False
		self._body = MultiPurposeList(on_change=self.set_dirty_body)
		if body:
			self.body = body

	def __unicode__(self):
		return u'<dom obj level=%s, title=%s>' % (level, title)

	def __str__(self):
		return self.__unicode__().encode(u'utf-8')

	def __len__(self):
		# 1 is for the heading's title
		return 1 + len(self.body)

	@property
	def is_dirty(self):
		u""" Return True if the dom obj body is marked dirty """
		return self._dirty_body

	@property
	def is_dirty_body(self):
		u""" Return True if the dom obj body is marked dirty """
		return self._dirty_body

	def get_index_in_parent_list(self):
		""" Retrieve the index value of current dom obj in the parents list of
		dom objs. This works also for top level dom objs.

		:returns:	Index value or None if dom obj doesn't have a
					parent/document or is not in the list of dom objs
		"""
		l = self.get_parent_list()
		if l:
			return l.index(self)

	def get_parent_list(self):
		""" Retrieve the parents list of dom objs. This works also for top
		level dom objs.

		:returns:	List of dom objs or None if dom objs doesn't have a
					parent/document or is not in the list of dom objs
		"""
		if self.parent:
			if self in self.parent.children:
				return self.parent.children

	def set_dirty(self):
		u""" Mark the dom objs and body dirty so that it will be rewritten when
		saving the document """
		if self._document:
			self._document.set_dirty_document()

	def set_dirty_body(self):
		u""" Mark the dom objs' body dirty so that it will be rewritten when
		saving the document """
		self._dirty_body = True
		if self._document:
			self._document.set_dirty_document()

	@property
	def document(self):
		u""" Read only access to the document. If you want to change the
		document, just assign the dom obj to another document """
		return self._document

	@property
	def parent(self):
		u""" Access to the parent dom obj """
		return self._parent

	@property
	def number_of_parents(self):
		u""" Access to the number of parent dom objs before reaching the root
		document """
		def count_parents(h):
			if h.parent:
				return 1 + count_parents(h.parent)
			else:
				return 0
		return count_parents(self)

	@property
	def previous_sibling(self):
		u""" Access to the previous dom obj that's a sibling of the current one
		"""
		return self._previous_sibling

	@property
	def next_sibling(self):
		u""" Access to the next dom obj that's a sibling of the current one """
		return self._next_sibling

	@property
	def previous_item(self):
		u""" Serialized access to the previous dom obj """
		if self.previous_sibling:
			h = self.previous_sibling
			while h.children:
				h = h.children[-1]
			return h
		elif self.parent:
			return self.parent

	@property
	def next_item(self):
		u""" Serialized access to the next dom obj """
		if self.children:
			return self.children[0]
		elif self.next_sibling:
			return self.next_sibling
		else:
			h = self.parent
			while h:
				if h.next_sibling:
					return h.next_sibling
				else:
					h = h.parent

	@property
	def start(self):
		u""" Access to the starting line of the dom obj """
		if self.document is None:
			return self._orig_start

		# static computation of start
		if not self.document.is_dirty:
			return self._orig_start

		# dynamic computation of start, really slow!
		def compute_start(h):
			if h:
				return len(h) + compute_start(h.previous_item)
		return compute_start(self.previous_item)

	@property
	def start_vim(self):
		if self.start is not None:
			return self.start + 1

	@property
	def end(self):
		u""" Access to the ending line of the dom obj """
		if self.start is not None:
			return self.start + len(self.body)

	@property
	def end_vim(self):
		if self.end is not None:
			return self.end + 1

	@property
	def end_of_last_child(self):
		u""" Access to end of the last child """
		if self.children:
			child = self.children[-1]
			while child.children:
				child = child.children[-1]
			return child.end
		return self.end

	@property
	def end_of_last_child_vim(self):
		return self.end_of_last_child + 1

	def children():
		u""" Subheadings of the current dom obj """
		def fget(self):
			return self._children

		def fset(self, value):
			v = value
			if type(v) in (list, tuple) or isinstance(v, UserList):
				v = flatten_list(v)
			self._children[:] = v

		def fdel(self):
			del self.children[:]

		return locals()
	children = property(**children())

	@property
	def first_child(self):
		u""" Access to the first child dom obj or None if no children exist """
		if self.children:
			return self.children[0]

	@property
	def last_child(self):
		u""" Access to the last child dom obj or None if no children exist """
		if self.children:
			return self.children[-1]

	def level():
		u""" Access to the dom obj level """
		def fget(self):
			return self._level

		def fset(self, value):
			self._level = int(value)
			self.set_dirty()

		def fdel(self):
			self.level = None

		return locals()
	level = property(**level())

	def title():
		u""" Title of current dom object """
		def fget(self):
			return self._title.strip()

		def fset(self, value):
			if type(value) not in (unicode, str):
				raise ValueError(u'Title must be a string.')
			v = value
			if type(v) == str:
				v = v.decode(u'utf-8')
			self._title = v.strip()
			self.set_dirty()

		def fdel(self):
			self.title = u''

		return locals()
	title = property(**title())

	def body():
		u""" Holds the content belonging to the heading """
		def fget(self):
			return self._body

		def fset(self, value):
			if type(value) in (list, tuple) or isinstance(value, UserList):
				self._body[:] = flatten_list(value)
			elif type(value) in (str, ):
				self._body[:] = value.decode('utf-8').split(u'\n')
			elif type(value) in (unicode, ):
				self._body[:] = value.split(u'\n')
			else:
				self.body = list(unicode(value))

		def fdel(self):
			self.body = []

		return locals()
	body = property(**body())


class DomObjList(MultiPurposeList):
	u"""
	A Dom Obj List
	"""
	def __init__(self, initlist=None, obj=None):
		"""
		:initlist:	Initial data
		:obj:		Link to a concrete Heading or Document object
		"""
		# it's not necessary to register a on_change hook because the heading
		# list will itself take care of marking headings dirty or adding
		# headings to the deleted headings list
		MultiPurposeList.__init__(self)

		self._obj = obj

		# initialization must be done here, because
		# self._document is not initialized when the
		# constructor of MultiPurposeList is called
		if initlist:
			self.extend(initlist)

	@classmethod
	def is_domobj(cls, obj):
		return isinstance(obj, DomObj)

	def _get_document(self):
		if self.__class__.is_domobj(self._obj):
			return self._obj._document
		return self._obj

	def __setitem__(self, i, item):
		if not self.__class__.is_domobj(item):
			raise ValueError(u'Item is not a Dom obj!')
		if item in self:
			raise ValueError(u'Dom obj is already part of this list!')
		# self._add_to_deleted_domobjs(self[i])

		# self._associate_domobj(item, \
		# self[i - 1] if i - 1 >= 0 else None, \
		# self[i + 1] if i + 1 < len(self) else None)
		MultiPurposeList.__setitem__(self, i, item)

	def __setslice__(self, i, j, other):
		o = other
		if self.__class__.is_domobj(o):
			o = (o, )
		o = flatten_list(o)
		for item in o:
			if not self.__class__.is_domobj(item):
				raise ValueError(u'List contains items that are not a Dom obj!')
		i = max(i, 0)
		j = max(j, 0)
		# self._add_to_deleted_domobjs(self[i:j])
		# self._associate_domobj(o, \
		# self[i - 1] if i - 1 >= 0 and i < len(self) else None, \
		# self[j] if j >= 0 and j < len(self) else None)
		MultiPurposeList.__setslice__(self, i, j, o)

	def __delitem__(self, i, taint=True):
		item = self[i]
		if item.previous_sibling:
			item.previous_sibling._next_sibling = item.next_sibling
		if item.next_sibling:
			item.next_sibling._previous_sibling = item.previous_sibling

		# if taint:
			# self._add_to_deleted_domobjs(item)
		MultiPurposeList.__delitem__(self, i)

	def __delslice__(self, i, j, taint=True):
		i = max(i, 0)
		j = max(j, 0)
		items = self[i:j]
		if items:
			first = items[0]
			last = items[-1]
			if first.previous_sibling:
				first.previous_sibling._next_sibling = last.next_sibling
			if last.next_sibling:
				last.next_sibling._previous_sibling = first.previous_sibling
		# if taint:
			# self._add_to_deleted_domobjs(items)
		MultiPurposeList.__delslice__(self, i, j)

	def __iadd__(self, other):
		o = other
		if self.__class__.is_domobj(o):
			o = (o, )
		for item in flatten_list(o):
			if not self.__class__.is_domobj(item):
				raise ValueError(u'List contains items that are not a Dom obj!')
		# self._associate_domobj(o, self[-1] if len(self) > 0 else None, None)
		return MultiPurposeList.__iadd__(self, o)

	def __imul__(self, n):
		# TODO das müsste eigentlich ein klonen von objekten zur Folge haben
		return MultiPurposeList.__imul__(self, n)

	def append(self, item, taint=True):
		if not self.__class__.is_domobj(item):
			raise ValueError(u'Item is not a heading!')
		if item in self:
			raise ValueError(u'Heading is already part of this list!')
		# self._associate_domobj(
		# 	item, self[-1] if len(self) > 0 else None,
		# 	None, taint=taint)
		MultiPurposeList.append(self, item)

	def insert(self, i, item, taint=True):
		# self._associate_domobj(
		# 	item,
		# 	self[i - 1] if i - 1 >= 0 and i - 1 < len(self) else None,
		# 	self[i] if i >= 0 and i < len(self) else None, taint=taint)
		MultiPurposeList.insert(self, i, item)

	def pop(self, i=-1):
		item = self[i]
		# self._add_to_deleted_domobjs(item)
		del self[i]
		return item

	def remove_slice(self, i, j, taint=True):
		self.__delslice__(i, j, taint=taint)

	def remove(self, item, taint=True):
		self.__delitem__(self.index(item), taint=taint)

	def reverse(self):
		MultiPurposeList.reverse(self)
		prev_h = None
		for h in self:
			h._previous_sibling = prev_h
			h._next_sibling = None
			prev_h._next_sibling = h
			h.set_dirty()
			prev_h = h

	def sort(self, *args, **kwds):
		MultiPurposeList.sort(*args, **kwds)
		prev_h = None
		for h in self:
			h._previous_sibling = prev_h
			h._next_sibling = None
			prev_h._next_sibling = h
			h.set_dirty()
			prev_h = h

	def extend(self, other):
		o = other
		if self.__class__.is_domobj(o):
			o = (o, )
		for item in o:
			if not self.__class__.is_domobj(item):
				raise ValueError(u'List contains items that are not a heading!')
		# self._associate_domobj(o, self[-1] if len(self) > 0 else None, None)
		MultiPurposeList.extend(self, o)


# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = headings
# -*- coding: utf-8 -*-

"""
	headings
	~~~~~~~~~

	TODO: explain this :)
"""

import re
from UserList import UserList

import vim
from orgmode.liborgmode.base import MultiPurposeList, flatten_list, Direction, get_domobj_range
from orgmode.liborgmode.orgdate import OrgTimeRange
from orgmode.liborgmode.orgdate import get_orgdate
from orgmode.liborgmode.checkboxes import Checkbox, CheckboxList
from orgmode.liborgmode.dom_obj import DomObj, DomObjList, REGEX_SUBTASK, REGEX_SUBTASK_PERCENT, REGEX_HEADING, REGEX_TAG, REGEX_TODO


class Heading(DomObj):
	u""" Structural heading object """

	def __init__(self, level=1, title=u'', tags=None, todo=None, body=None, active_date=None):
		u"""
		:level:		Level of the heading
		:title:		Title of the heading
		:tags:		Tags of the heading
		:todo:		Todo state of the heading
		:body:		Body of the heading
		:active_date: active date that is used in the agenda
		"""
		DomObj.__init__(self, level=level, title=title, body=body)

		self._children = HeadingList(obj=self)
		self._dirty_heading = False

		# todo
		self._todo = None
		if todo:
			self.todo = todo

		# tags
		self._tags = MultiPurposeList(on_change=self.set_dirty_heading)
		if tags:
			self.tags = tags

		# active date
		self._active_date = active_date
		if active_date:
			self.active_date = active_date

		# checkboxes
		self._checkboxes = CheckboxList(obj=self)
		self._cached_checkbox = None

	def __unicode__(self):
		res = u'*' * self.level
		if self.todo:
			res = u' '.join((res, self.todo))
		if self.title:
			res = u' '.join((res, self.title))

		# compute position of tags
		if self.tags:
			tabs = 0
			spaces = 2
			tags = u':%s:' % (u':'.join(self.tags), )

			# FIXME this is broken because of missing associations for headings
			ts = 6
			tag_column = 77
			if self.document:
				ts = self.document.tabstop
				tag_column = self.document.tag_column

			len_heading = len(res)
			len_tags = len(tags)
			if len_heading + spaces + len_tags < tag_column:
				spaces_to_next_tabstop = ts - divmod(len_heading, ts)[1]

				if len_heading + spaces_to_next_tabstop + len_tags < tag_column:
					tabs, spaces = divmod(
						tag_column - (len_heading + spaces_to_next_tabstop + len_tags),
						ts)

					if spaces_to_next_tabstop:
						tabs += 1
				else:
					spaces = tag_column - (len_heading + len_tags)

			res += u'\t' * tabs + u' ' * spaces + tags

		# append a trailing space when there are just * and no text
		if len(res) == self.level:
			res += u' '
		return res

	def __str__(self):
		return self.__unicode__().encode(u'utf-8')

	def __len__(self):
		# 1 is for the heading's title
		return 1 + len(self.body)

	def __lt__(self, other):
		"""
		Headings can be sorted by date.
		"""
		try:
			if self.active_date < other.active_date:
				return True
			elif self.active_date == other.active_date:
				return False
			elif self.active_date > other.active_date:
				return False
		except:
			if self.active_date and not other.active_date:
				return True
			elif not self.active_date and other.active_date:
				return False
			elif not self.active_date and not other.active:
				return False

	def __le__(self, other):
		"""
		Headings can be sorted by date.
		"""
		try:
			if self.active_date < other.active_date:
				return True
			elif self.active_date == other.active_date:
				return True
			elif self.active_date > other.active_date:
				return False
		except:
			if self.active_date and not other.active_date:
				return True
			elif not self.active_date and other.active_date:
				return False
			elif not self.active_date and not other.active:
				return True

	def __ge__(self, other):
		"""
		Headings can be sorted by date.
		"""
		try:
			if self.active_date > other.active_date:
				return True
			elif self.active_date == other.active_date:
				return True
			elif self.active_date < other.active_date:
				return False
		except:
			if not self.active_date and other.active_date:
				return True
			elif self.active_date and not other.active_date:
				return False
			elif not self.active_date and not other.active:
				return True

	def __gt__(self, other):
		"""
		Headings can be sorted by date.
		"""
		try:
			if self.active_date > other.active_date:
				return True
			elif self.active_date == other.active_date:
				return False
			elif self.active_date < other.active_date:
				return False
		except:
			if not self.active_date and other.active_date:
				return True
			elif self.active_date and not other.active_date:
				return False
			elif not self.active_date and not other.active:
				return False

	def copy(self, including_children=True, parent=None):
		u"""
		Create a copy of the current heading. The heading will be completely
		detached and not even belong to a document anymore.

		:including_children:	If True a copy of all children is create as
								well. If False the returned heading doesn't
								have any children.
		:parent:				Don't use this parameter. It's set
								automatically.
		"""
		heading = self.__class__(
			level=self.level, title=self.title,
			tags=self.tags, todo=self.todo, body=self.body[:])
		if parent:
			parent.children.append(heading)
		if including_children and self.children:
			for item in self.children:
				item.copy(
					including_children=including_children,
					parent=heading)
		heading._orig_start = self._orig_start
		heading._orig_len = self._orig_len

		heading._dirty_heading = self.is_dirty_heading

		return heading

	def all_checkboxes(self):
		u""" Iterate over all checkboxes of the current heading in serialized
		order

		:returns:	Returns an iterator object which returns all checkboxes of
					the current heading in serialized order
		"""
		if not self.checkboxes:
			raise StopIteration()

		c = self.first_checkbox
		while c:
			yield c
			c = c.next_checkbox
		raise StopIteration()

	def all_toplevel_checkboxes(self):
		u""" return all top level checkboxes for current heading """
		if not self.checkboxes:
			raise StopIteration()

		c = self.first_checkbox
		while c:
			yield c
			c = c.next_sibling
		raise StopIteration()

	def find_checkbox(self, position=0, direction=Direction.FORWARD,
		checkbox=Checkbox, connect_with_heading=True):
		u""" Find checkbox in the given direction

		:postition: starting line, counting from 0 (in vim you start
					counting from 1, don't forget)
		:direction: downwards == Direction.FORWARD,
					upwards == Direction.BACKWARD
		:checkbox:  Checkbox class from which new checkbox objects will be
					instanciated
		:connect_with_heading: if True, the newly created checkbox will be
								connected with the heading, otherwise not

		:returns:	New checkbox object or None
		"""
		doc = self.document
		(start, end) = get_domobj_range(content=doc._content, position=position, direction=direction, identify_fun=checkbox.identify_checkbox)
		# if out of current headinig range, reutrn None
		heading_end = self.start + len(self) - 1
		if start > heading_end:
			return None

		if end > heading_end:
			end = heading_end

		if start is not None and end is None:
			end = heading_end
		if start is not None and end is not None:
			return checkbox.parse_checkbox_from_data(
				doc._content[start:end + 1],
				heading=self if connect_with_heading else None, orig_start=start)

	def init_checkboxes(self, checkbox=Checkbox):
		u""" Initialize all checkboxes in current heading - build DOM.

		:returns:	self
		"""
		def init_checkbox(_c):
			u"""
			:returns	the initialized checkbox
			"""
			start = _c.end + 1
			prev_checkbox = None
			while True:
				new_checkbox = self.find_checkbox(start, checkbox=checkbox)

				# * Checkbox 1 <- checkbox
				# * Checkbox 1 <- sibling
				# or
				#  * Checkbox 2 <- checkbox
				# * Checkbox 1 <- parent's sibling
				if not new_checkbox or \
					new_checkbox.level <= _c.level:
					break

				# * Checkbox 1 <- heading
				#  * Checkbox 2 <- first child
				#  * Checkbox 2 <- another child
				new_checkbox._parent = _c
				if prev_checkbox:
					prev_checkbox._next_sibling = new_checkbox
					new_checkbox._previous_sibling = prev_checkbox
				_c.children.data.append(new_checkbox)
				# the start and end computation is only
				# possible when the new checkbox was properly
				# added to the document structure
				init_checkbox(new_checkbox)
				if new_checkbox.children:
					# skip children
					start = new_checkbox.end_of_last_child + 1
				else:
					start = new_checkbox.end + 1
				prev_checkbox = new_checkbox

			return _c

		c = self.find_checkbox(checkbox=checkbox, position=self.start)

		# initialize dom tree
		prev_c = None
		while c:
			if prev_c and prev_c.level == c.level:
				prev_c._next_sibling = c
				c._previous_sibling = prev_c
			self.checkboxes.data.append(c)
			init_checkbox(c)
			prev_c = c
			c = self.find_checkbox(c.end_of_last_child + 1, checkbox=checkbox)

		return self

	def current_checkbox(self, position=None):
		u""" Find the current checkbox (search backward) and return the related object
		:returns:	Checkbox object or None
		"""
		if position is None:
			position = vim.current.window.cursor[0] - 1

		if not self.checkboxes:
			return

		def binaryFindInHeading():
			hi = len(self.checkboxes)
			lo = 0
			while lo < hi:
				mid = (lo + hi) // 2
				c = self.checkboxes[mid]
				if c.end_of_last_child < position:
					lo = mid + 1
				elif c.start > position:
					hi = mid
				else:
					return binaryFindCheckbox(c)

		def binaryFindCheckbox(checkbox):
			if not checkbox.children or checkbox.end >= position:
				return checkbox

			hi = len(checkbox.children)
			lo = 0
			while lo < hi:
				mid = (lo + hi) // 2
				c = checkbox.children[mid]
				if c.end_of_last_child < position:
					lo = mid + 1
				elif c.start > position:
					hi = mid
				else:
					return binaryFindCheckbox(c)

		# look at the cache to find the heading
		c_tmp = self._cached_checkbox
		if c_tmp is not None:
			if c_tmp.end_of_last_child > position and \
				c_tmp.start < position:
				if c_tmp.end < position:
					self._cached_checkbox = binaryFindCheckbox(c_tmp)
				return self._cached_checkbox

		self._cached_checkbox = binaryFindInHeading()
		return self._cached_checkbox

	@property
	def first_checkbox(self):
		u""" Access to the first child checkbox or None if no children exist """
		if self.checkboxes:
			return self.checkboxes[0]

	@classmethod
	def parse_heading_from_data(
		cls, data, allowed_todo_states, document=None,
		orig_start=None):
		u""" Construct a new heading from the provided data

		:data:			List of lines
		:allowed_todo_states: TODO???
		:document:		The document object this heading belongs to
		:orig_start:	The original start of the heading in case it was read
						from a document. If orig_start is provided, the
						resulting heading will not be marked dirty.

		:returns:	The newly created heading
		"""
		test_not_empty = lambda x: x != u''

		def parse_title(heading_line):
			# WARNING this regular expression fails if there is just one or no
			# word in the heading but a tag!
			m = REGEX_HEADING.match(heading_line)
			if m:
				r = m.groupdict()
				level = len(r[u'level'])
				todo = None
				title = u''
				tags = filter(test_not_empty, r[u'tags'].split(u':')) if r[u'tags'] else []

				# if there is just one or no word in the heading, redo the parsing
				mt = REGEX_TAG.match(r[u'title'])
				if not tags and mt:
					r = mt.groupdict()
					tags = filter(test_not_empty, r[u'tags'].split(u':')) if r[u'tags'] else []
				if r[u'title'] is not None:
					_todo_title = [i.strip() for i in r[u'title'].split(None, 1)]
					if _todo_title and _todo_title[0] in allowed_todo_states:
						todo = _todo_title[0]
						if len(_todo_title) > 1:
							title = _todo_title[1]
					else:
						title = r[u'title'].strip()

				return (level, todo, title, tags)
			raise ValueError(u'Data doesn\'t start with a heading definition.')

		if not data:
			raise ValueError(u'Unable to create heading, no data provided.')

		# create new heaing
		new_heading = cls()
		new_heading.level, new_heading.todo, new_heading.title, new_heading.tags = parse_title(data[0])
		new_heading.body = data[1:]
		if orig_start is not None:
			new_heading._dirty_heading = False
			new_heading._dirty_body = False
			new_heading._orig_start = orig_start
			new_heading._orig_len = len(new_heading)
		if document:
			new_heading._document = document

		# try to find active dates
		tmp_orgdate = get_orgdate(data)
		if tmp_orgdate and tmp_orgdate.active \
			and not isinstance(tmp_orgdate, OrgTimeRange):
			new_heading.active_date = tmp_orgdate
		else:
			new_heading.active_date = None

		return new_heading

	def update_subtasks(self, total=0, on=0):
		u""" Update subtask information for current heading
		:total:	total # of top level checkboxes
		:on:	# of top level checkboxes which are on
		"""
		if total != 0:
			percent = (on * 100) / total
		else:
			percent = 0

		count = "%d/%d" % (on, total)
		self.title = REGEX_SUBTASK.sub("[%s]" % (count), self.title)
		self.title = REGEX_SUBTASK_PERCENT.sub("[%d%%]" % (percent), self.title)
		self.document.write_heading(self, including_children=False)

	@classmethod
	def identify_heading(cls, line):
		u""" Test if a certain line is a heading or not.

		:line: the line to check

		:returns: level
		"""
		level = 0
		if not line:
			return None
		for i in xrange(0, len(line)):
			if line[i] == u'*':
				level += 1
				if len(line) > (i + 1) and line[i + 1] in (u'\t', u' '):
					return level
			else:
				return None

	@property
	def is_dirty(self):
		u""" Return True if the heading's body is marked dirty """
		return self._dirty_heading or self._dirty_body

	@property
	def is_dirty_heading(self):
		u""" Return True if the heading is marked dirty """
		return self._dirty_heading

	def get_index_in_parent_list(self):
		""" Retrieve the index value of current heading in the parents list of
		headings. This works also for top level headings.

		:returns:	Index value or None if heading doesn't have a
					parent/document or is not in the list of headings
		"""
		if self.parent:
			return super(Heading, self).get_index_in_parent_list()
		elif self.document:
			l = self.get_parent_list()
			if l:
				return l.index(self)

	def get_parent_list(self):
		""" Retrieve the parents' list of headings. This works also for top
		level headings.

		:returns:	List of headings or None if heading doesn't have a
					parent/document or is not in the list of headings
		"""
		if self.parent:
			return super(Heading, self).get_parent_list()
		elif self.document:
			if self in self.document.headings:
				return self.document.headings

	def set_dirty(self):
		u""" Mark the heading and body dirty so that it will be rewritten when
		saving the document """
		self._dirty_heading = True
		self._dirty_body = True
		if self._document:
			self._document.set_dirty_document()

	def set_dirty_heading(self):
		u""" Mark the heading dirty so that it will be rewritten when saving the
		document """
		self._dirty_heading = True
		if self._document:
			self._document.set_dirty_document()

	@property
	def previous_heading(self):
		u""" Serialized access to the previous heading """
		return super(Heading, self).previous_item

	@property
	def next_heading(self):
		u""" Serialized access to the next heading """
		return super(Heading, self).next_item

	@property
	def start(self):
		u""" Access to the starting line of the heading """
		if self.document is None:
			return self._orig_start

		# static computation of start
		if not self.document.is_dirty:
			return self._orig_start

		# dynamic computation of start, really slow!
		def compute_start(h):
			if h:
				return len(h) + compute_start(h.previous_heading)
			return len(self.document.meta_information) if \
				self.document.meta_information else 0
		return compute_start(self.previous_heading)

	def level():
		u""" Access to the heading level """
		def fget(self):
			return self._level

		def fset(self, value):
			self._level = int(value)
			self.set_dirty_heading()

		def fdel(self):
			self.level = None

		return locals()
	level = property(**level())

	def todo():
		u""" Todo state of current heading. When todo state is set, it will be
		converted to uppercase """
		def fget(self):
			# extract todo state from heading
			return self._todo

		def fset(self, value):
			# update todo state
			if type(value) not in (unicode, str, type(None)):
				raise ValueError(u'Todo state must be a string or None.')
			if value and not REGEX_TODO.match(value):
				raise ValueError(u'Found non allowed character in todo state! %s' % value)
			if not value:
				self._todo = None
			else:
				v = value
				if type(v) == str:
					v = v.decode(u'utf-8')
				self._todo = v.upper()
			self.set_dirty_heading()

		def fdel(self):
			self.todo = None

		return locals()
	todo = property(**todo())

	def active_date():
		u"""
		active date of the hearing.

		active dates are used in the agenda view. they can be part of the
		heading and/or the body.
		"""
		def fget(self):
			return self._active_date

		def fset(self, value):
			self._active_date = value

		def fdel(self):
			self._active_date = None
		return locals()
	active_date = property(**active_date())

	def title():
		u""" Title of current heading """
		def fget(self):
			return self._title.strip()

		def fset(self, value):
			if type(value) not in (unicode, str):
				raise ValueError(u'Title must be a string.')
			v = value
			if type(v) == str:
				v = v.decode(u'utf-8')
			self._title = v.strip()
			self.set_dirty_heading()

		def fdel(self):
			self.title = u''

		return locals()
	title = property(**title())

	def tags():
		u""" Tags of the current heading """
		def fget(self):
			return self._tags

		def fset(self, value):
			v = value
			if type(v) in (unicode, str):
				v = list(unicode(v))
			if type(v) not in (list, tuple) and not isinstance(v, UserList):
				v = list(unicode(v))
			v = flatten_list(v)
			v_decoded = []
			for i in v:
				if type(i) not in (unicode, str):
					raise ValueError(u'Found non string value in tags! %s' % unicode(i))
				if u':' in i:
					raise ValueError(u'Found non allowed character in tag! %s' % i)
				i_tmp = i.strip().replace(' ', '_').replace('\t', '_')
				if type(i) == str:
					i_tmp = i.decode(u'utf-8')
				v_decoded.append(i_tmp)

			self._tags[:] = v_decoded

		def fdel(self):
			self.tags = []

		return locals()
	tags = property(**tags())

	def checkboxes():
		u""" All checkboxes in current heading """
		def fget(self):
			return self._checkboxes

		def fset(self, value):
			self._checkboxes[:] = value

		def fdel(self):
			del self.checkboxes[:]

		return locals()
	checkboxes = property(**checkboxes())


class HeadingList(DomObjList):
	u"""
	A Heading List just contains headings. It's used for documents to store top
	level headings and for headings to store subheadings.

	A Heading List must be linked to a Document or Heading!

	See documenatation of MultiPurposeList for more information.
	"""
	def __init__(self, initlist=None, obj=None):
		"""
		:initlist:	Initial data
		:obj:		Link to a concrete Heading or Document object
		"""
		# it's not necessary to register a on_change hook because the heading
		# list will itself take care of marking headings dirty or adding
		# headings to the deleted headings list
		DomObjList.__init__(self, initlist, obj)

	@classmethod
	def is_heading(cls, obj):
		return HeadingList.is_domobj(obj)

	def _get_document(self):
		if self.__class__.is_heading(self._obj):
			return self._obj._document
		return self._obj

	def _add_to_deleted_headings(self, item):
		u"""
		Serialize headings so that all subheadings are also marked for deletion
		"""
		if not self._get_document():
			# HeadingList has not yet been associated
			return

		if type(item) in (list, tuple) or isinstance(item, UserList):
			for i in flatten_list(item):
				self._add_to_deleted_headings(i)
		else:
			self._get_document()._deleted_headings.append(
				item.copy(including_children=False))
			self._add_to_deleted_headings(item.children)
			self._get_document().set_dirty_document()

	def _associate_heading(
		self, heading, previous_sibling, next_sibling,
		children=False, taint=True):
		"""
		:heading:		The heading or list to associate with the current heading
		:previous_sibling:	The previous sibling of the current heading. If
							heading is a list the first heading will be
							connected with the previous sibling and the last
							heading with the next sibling. The items in between
							will be linked with one another.
		:next_sibling:	The next sibling of the current heading. If
							heading is a list the first heading will be
							connected with the previous sibling and the last
							heading with the next sibling. The items in between
							will be linked with one another.
		:children:		Marks whether children are processed in the current
							iteration or not (should not be use, it's set
							automatically)
		:taint:			If not True, the heading is not marked dirty at the end
							of the association process and its orig_start and
							orig_len values are not updated.
		"""
		# TODO this method should be externalized and moved to the Heading class
		if type(heading) in (list, tuple) or isinstance(heading, UserList):
			prev = previous_sibling
			current = None
			for _next in flatten_list(heading):
				if current:
					self._associate_heading(
						current, prev, _next,
						children=children, taint=taint)
					prev = current
				current = _next
			if current:
				self._associate_heading(
					current, prev, next_sibling,
					children=children, taint=taint)
		else:
			if taint:
				heading._orig_start = None
				heading._orig_len = None
			d = self._get_document()
			if heading._document != d:
				heading._document = d
			if not children:
				# connect heading with previous and next headings
				heading._previous_sibling = previous_sibling
				if previous_sibling:
					previous_sibling._next_sibling = heading
				heading._next_sibling = next_sibling
				if next_sibling:
					next_sibling._previous_sibling = heading

				if d == self._obj:
					# self._obj is a Document
					heading._parent = None
				elif heading._parent != self._obj:
					# self._obj is a Heading
					heading._parent = self._obj
			if taint:
				heading.set_dirty()

			self._associate_heading(
				heading.children, None, None,
				children=True, taint=taint)

	def __setitem__(self, i, item):
		if not self.__class__.is_heading(item):
			raise ValueError(u'Item is not a heading!')
		if item in self:
			raise ValueError(u'Heading is already part of this list!')
		self._add_to_deleted_headings(self[i])

		self._associate_heading(
			item,
			self[i - 1] if i - 1 >= 0 else None,
			self[i + 1] if i + 1 < len(self) else None)
		MultiPurposeList.__setitem__(self, i, item)

	def __setslice__(self, i, j, other):
		o = other
		if self.__class__.is_heading(o):
			o = (o, )
		o = flatten_list(o)
		for item in o:
			if not self.__class__.is_heading(item):
				raise ValueError(u'List contains items that are not a heading!')
		i = max(i, 0)
		j = max(j, 0)
		self._add_to_deleted_headings(self[i:j])
		self._associate_heading(
			o,
			self[i - 1] if i - 1 >= 0 and i < len(self) else None,
			self[j] if j >= 0 and j < len(self) else None)
		MultiPurposeList.__setslice__(self, i, j, o)

	def __delitem__(self, i, taint=True):
		item = self[i]
		if item.previous_sibling:
			item.previous_sibling._next_sibling = item.next_sibling
		if item.next_sibling:
			item.next_sibling._previous_sibling = item.previous_sibling

		if taint:
			self._add_to_deleted_headings(item)
		MultiPurposeList.__delitem__(self, i)

	def __delslice__(self, i, j, taint=True):
		i = max(i, 0)
		j = max(j, 0)
		items = self[i:j]
		if items:
			first = items[0]
			last = items[-1]
			if first.previous_sibling:
				first.previous_sibling._next_sibling = last.next_sibling
			if last.next_sibling:
				last.next_sibling._previous_sibling = first.previous_sibling
		if taint:
			self._add_to_deleted_headings(items)
		MultiPurposeList.__delslice__(self, i, j)

	def __iadd__(self, other):
		o = other
		if self.__class__.is_heading(o):
			o = (o, )
		for item in flatten_list(o):
			if not self.__class__.is_heading(item):
				raise ValueError(u'List contains items that are not a heading!')
		self._associate_heading(o, self[-1] if len(self) > 0 else None, None)
		return MultiPurposeList.__iadd__(self, o)

	def append(self, item, taint=True):
		if not self.__class__.is_heading(item):
			raise ValueError(u'Item is not a heading!')
		if item in self:
			raise ValueError(u'Heading is already part of this list!')
		self._associate_heading(
			item, self[-1] if len(self) > 0 else None,
			None, taint=taint)
		MultiPurposeList.append(self, item)

	def insert(self, i, item, taint=True):
		self._associate_heading(
			item,
			self[i - 1] if i - 1 >= 0 and i - 1 < len(self) else None,
			self[i] if i >= 0 and i < len(self) else None, taint=taint)
		MultiPurposeList.insert(self, i, item)

	def pop(self, i=-1):
		item = self[i]
		self._add_to_deleted_headings(item)
		del self[i]
		return item

	def extend(self, other):
		o = other
		if self.__class__.is_heading(o):
			o = (o, )
		for item in o:
			if not self.__class__.is_heading(item):
				raise ValueError(u'List contains items that are not a heading!')
		self._associate_heading(o, self[-1] if len(self) > 0 else None, None)
		MultiPurposeList.extend(self, o)


# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = orgdate
# -*- coding: utf-8 -*-
u"""
	OrgDate
	~~~~~~~~~~~~~~~~~~

	This module contains all date/time/timerange representations that exist in
	orgmode.

	There exist three different kinds:

	* OrgDate: is similar to a date object in python and it looks like
	  '2011-09-07 Wed'.

	* OrgDateTime: is similar to a datetime object in python and looks like
	  '2011-09-07 Wed 10:30'

	* OrgTimeRange: indicates a range of time. It has a start and and end date:
	  * <2011-09-07 Wed>--<2011-09-08 Fri>
	  * <2011-09-07 Wed 10:00-13:00>

	All OrgTime oblects can be active or inactive.
"""

import datetime
import re

# <2011-09-12 Mon>
_DATE_REGEX = re.compile(r"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w>")
# [2011-09-12 Mon]
_DATE_PASSIVE_REGEX = re.compile(r"\[(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w\]")

# <2011-09-12 Mon 10:20>
_DATETIME_REGEX = re.compile(
	r"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d{1,2}):(\d\d)>")
# [2011-09-12 Mon 10:20]
_DATETIME_PASSIVE_REGEX = re.compile(
	r"\[(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d{1,2}):(\d\d)\]")

# <2011-09-12 Mon>--<2011-09-13 Tue>
_DATERANGE_REGEX = re.compile(
	# <2011-09-12 Mon>--
	r"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w>--"
	# <2011-09-13 Tue>
	"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w>")
# <2011-09-12 Mon 10:00>--<2011-09-12 Mon 11:00>
_DATETIMERANGE_REGEX = re.compile(
	# <2011-09-12 Mon 10:00>--
	r"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d\d):(\d\d)>--"
	# <2011-09-12 Mon 11:00>
	"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d\d):(\d\d)>")
# <2011-09-12 Mon 10:00--12:00>
_DATETIMERANGE_SAME_DAY_REGEX = re.compile(
	r"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d\d):(\d\d)-(\d\d):(\d\d)>")


def get_orgdate(data):
	u"""
	Parse the given data (can be a string or list). Return an OrgDate if data
	contains a string representation of an OrgDate; otherwise return None.

	data can be a string or a list containing strings.
	"""
	if isinstance(data, list):
		return _findfirst(_text2orgdate, data)
	else:
		return _text2orgdate(data)
	# if no dates found
	return None


def _findfirst(f, seq):
	u"""
	Return first item in sequence seq where f(item) == True.

	TODO: this is a general help function and it should be moved somewhere
	else; preferably into the standard lib :)
	"""
	for found in (f(item) for item in seq if f(item)):
		return found


def _text2orgdate(string):
	u"""
	Transform the given string into an OrgDate.
	Return an OrgDate if data contains a string representation of an OrgDate;
	otherwise return None.
	"""
	# handle active datetime with same day
	result = _DATETIMERANGE_SAME_DAY_REGEX.search(string)
	if result:
		try:
			(syear, smonth, sday, shour, smin, ehour, emin) = \
				[int(m) for m in result.groups()]
			start = datetime.datetime(syear, smonth, sday, shour, smin)
			end = datetime.datetime(syear, smonth, sday, ehour, emin)
			return OrgTimeRange(True, start, end)
		except Exception:
			return None

	# handle active datetime
	result = _DATETIMERANGE_REGEX.search(string)
	if result:
		try:
			tmp = [int(m) for m in result.groups()]
			(syear, smonth, sday, shour, smin, eyear, emonth, eday, ehour, emin) = tmp
			start = datetime.datetime(syear, smonth, sday, shour, smin)
			end = datetime.datetime(eyear, emonth, eday, ehour, emin)
			return OrgTimeRange(True, start, end)
		except Exception:
			return None

	# handle active datetime
	result = _DATERANGE_REGEX.search(string)
	if result:
		try:
			tmp = [int(m) for m in result.groups()]
			syear, smonth, sday, eyear, emonth, ehour = tmp
			start = datetime.date(syear, smonth, sday)
			end = datetime.date(eyear, emonth, ehour)
			return OrgTimeRange(True, start, end)
		except Exception:
			return None

	# handle active datetime
	result = _DATETIME_REGEX.search(string)
	if result:
		try:
			year, month, day, hour, minutes = [int(m) for m in result.groups()]
			return OrgDateTime(True, year, month, day, hour, minutes)
		except Exception:
			return None

	# handle passive datetime
	result = _DATETIME_PASSIVE_REGEX.search(string)
	if result:
		try:
			year, month, day, hour, minutes = [int(m) for m in result.groups()]
			return OrgDateTime(False, year, month, day, hour, minutes)
		except Exception:
			return None

	# handle passive dates
	result = _DATE_PASSIVE_REGEX.search(string)
	if result:
		try:
			year, month, day = [int(m) for m in result.groups()]
			return OrgDate(False, year, month, day)
		except Exception:
			return None

	# handle active dates
	result = _DATE_REGEX.search(string)
	if result:
		try:
			year, month, day = [int(m) for m in result.groups()]
			return OrgDate(True, year, month, day)
		except Exception:
			return None


class OrgDate(datetime.date):
	u"""
	OrgDate represents a normal date like '2011-08-29 Mon'.

	OrgDates can be active or inactive.

	NOTE: date is immutable. Thats why there needs to be __new__().
	See: http://docs.python.org/reference/datamodel.html#object.__new__
	"""
	def __init__(self, active, year, month, day):
		self.active = active
		pass

	def __new__(cls, active, year, month, day):
		return datetime.date.__new__(cls, year, month, day)

	def __unicode__(self):
		u"""
		Return a string representation.
		"""
		if self.active:
			return self.strftime(u'<%Y-%m-%d %a>')
		else:
			return self.strftime(u'[%Y-%m-%d %a]')

	def __str__(self):
		return self.__unicode__().encode(u'utf-8')


class OrgDateTime(datetime.datetime):
	u"""
	OrgDateTime represents a normal date like '2011-08-29 Mon'.

	OrgDateTime can be active or inactive.

	NOTE: date is immutable. Thats why there needs to be __new__().
	See: http://docs.python.org/reference/datamodel.html#object.__new__
	"""

	def __init__(self, active, year, month, day, hour, mins):
		self.active = active

	def __new__(cls, active, year, month, day, hour, minute):
		return datetime.datetime.__new__(cls, year, month, day, hour, minute)

	def __unicode__(self):
		u"""
		Return a string representation.
		"""
		if self.active:
			return self.strftime(u'<%Y-%m-%d %a %H:%M>')
		else:
			return self.strftime(u'[%Y-%m-%d %a %H:%M]')

	def __str__(self):
		return self.__unicode__().encode(u'utf-8')


class OrgTimeRange(object):
	u"""
	OrgTimeRange objects have a start and an end. Start and ent can be date
	or datetime. Start and end have to be the same type.

	OrgTimeRange objects look like this:
	* <2011-09-07 Wed>--<2011-09-08 Fri>
	* <2011-09-07 Wed 20:00>--<2011-09-08 Fri 10:00>
	* <2011-09-07 Wed 10:00-13:00>
	"""

	def __init__(self, active, start, end):
		u"""
		stat and end must be datetime.date or datetime.datetime (both of the
		same type).
		"""
		super(OrgTimeRange, self).__init__()
		self.start = start
		self.end = end
		self.active = active

	def __unicode__(self):
		u"""
		Return a string representation.
		"""
		# active
		if self.active:
			# datetime
			if isinstance(self.start, datetime.datetime):
				# if start and end are on same the day
				if self.start.year == self.end.year and\
					self.start.month == self.end.month and\
					self.start.day == self.end.day:
					return u"<%s-%s>" % (
						self.start.strftime(u'%Y-%m-%d %a %H:%M'),
						self.end.strftime(u'%H:%M'))
				else:
					return u"<%s>--<%s>" % (
						self.start.strftime(u'%Y-%m-%d %a %H:%M'),
						self.end.strftime(u'%Y-%m-%d %a %H:%M'))
			# date
			if isinstance(self.start, datetime.date):
				return u"<%s>--<%s>" % (
					self.start.strftime(u'%Y-%m-%d %a'),
					self.end.strftime(u'%Y-%m-%d %a'))
		# inactive
		else:
			if isinstance(self.start, datetime.datetime):
				# if start and end are on same the day
				if self.start.year == self.end.year and\
					self.start.month == self.end.month and\
					self.start.day == self.end.day:
					return u"[%s-%s]" % (
						self.start.strftime(u'%Y-%m-%d %a %H:%M'),
						self.end.strftime(u'%H:%M'))
				else:
					return u"[%s]--[%s]" % (
						self.start.strftime(u'%Y-%m-%d %a %H:%M'),
						self.end.strftime(u'%Y-%m-%d %a %H:%M'))
			if isinstance(self.start, datetime.date):
				return u"[%s]--[%s]" % (
					self.start.strftime(u'%Y-%m-%d %a'),
					self.end.strftime(u'%Y-%m-%d %a'))

	def __str__(self):
		return self.__unicode__().encode(u'utf-8')

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = menu
# -*- coding: utf-8 -*-

import vim

from orgmode.keybinding import Command, Plug, Keybinding
from orgmode.keybinding import MODE_ALL, MODE_NORMAL, MODE_VISUAL, MODE_INSERT

def register_menu(f):
	def r(*args, **kwargs):
		p = f(*args, **kwargs)
		def create(entry):
			if isinstance(entry, Submenu) or isinstance(entry, Separator) \
					or isinstance(entry, ActionEntry):
				entry.create()

		if hasattr(p, u'menu'):
			if isinstance(p.menu, list) or isinstance(p.menu, tuple):
				for e in p.menu:
					create(e)
			else:
				create(p.menu)
		return p
	return r


def add_cmd_mapping_menu(plugin, name, function, key_mapping, menu_desrc):
	u"""A helper function to create a vim command and keybinding and add these
	to the menu for a given plugin.

	:plugin: the plugin to operate on.
	:name: the name of the vim command (and the name of the Plug)
	:function: the actual python function which is called when executing the
				vim command.
	:key_mapping: the keymapping to execute the command.
	:menu_desrc: the text which appears in the menu.
	"""
	cmd = Command(name, function)
	keybinding = Keybinding(key_mapping, Plug(name, cmd))

	plugin.commands.append(cmd)
	plugin.keybindings.append(keybinding)
	plugin.menu + ActionEntry(menu_desrc, keybinding)


class Submenu(object):
	u""" Submenu entry """

	def __init__(self, name, parent=None):
		object.__init__(self)
		self.name = name
		self.parent = parent
		self._children = []

	def __add__(self, entry):
		if entry not in self._children:
			self._children.append(entry)
			entry.parent = self
			return entry

	def __sub__(self, entry):
		if entry in self._children:
			idx = self._children.index(entry)
			del self._children[idx]

	@property
	def children(self):
		return self._children[:]

	def get_menu(self):
		n = self.name.replace(u' ', u'\\ ')
		if self.parent:
			return u'%s.%s' % (self.parent.get_menu(), n)
		return n

	def create(self):
		for c in self.children:
			c.create()

	def __str__(self):
		res = self.name
		for c in self.children:
			res += str(c)
		return res

class Separator(object):
	u""" Menu entry for a Separator """

	def __init__(self, parent=None):
		object.__init__(self)
		self.parent = parent

	def __unicode__(self):
		return u'-----'

	def __str__(self):
		return self.__unicode__().encode(u'utf-8')

	def create(self):
		if self.parent:
			menu = self.parent.get_menu()
			vim.command((u'menu %s.-%s- :' % (menu, id(self))).encode(u'utf-8'))

class ActionEntry(object):
	u""" ActionEntry entry """

	def __init__(self, lname, action, rname=None, mode=MODE_NORMAL, parent=None):
		u"""
		:lname: menu title on the left hand side of the menu entry
		:action: could be a vim command sequence or an actual Keybinding
		:rname: menu title that appears on the right hand side of the menu
				entry. If action is a Keybinding this value ignored and is
				taken from the Keybinding
		:mode: defines when the menu entry/action is executable
		:parent: the parent instance of this object. The only valid parent is Submenu
		"""
		object.__init__(self)
		self._lname = lname
		self._action = action
		self._rname = rname
		if mode not in (MODE_ALL, MODE_NORMAL, MODE_VISUAL, MODE_INSERT):
			raise ValueError(u'Parameter mode not in MODE_ALL, MODE_NORMAL, MODE_VISUAL, MODE_INSERT')
		self._mode = mode
		self.parent = parent

	def __str__(self):
		return u'%s\t%s' % (self.lname, self.rname)

	@property
	def lname(self):
		return self._lname.replace(u' ', u'\\ ')

	@property
	def action(self):
		if isinstance(self._action, Keybinding):
			return self._action.action
		return self._action

	@property
	def rname(self):
		if isinstance(self._action, Keybinding):
			return self._action.key.replace(u'<Tab>', u'Tab')
		return self._rname

	@property
	def mode(self):
		if isinstance(self._action, Keybinding):
			return self._action.mode
		return self._mode

	def create(self):
		menucmd = u':%smenu ' % self.mode
		menu = u''
		cmd = u''

		if self.parent:
			menu = self.parent.get_menu()
		menu += u'.%s' % self.lname

		if self.rname:
			cmd = u'%s %s<Tab>%s %s' % (menucmd, menu, self.rname, self.action)
		else:
			cmd = u'%s %s %s' % (menucmd, menu, self.action)

		vim.command(cmd.encode(u'utf-8'))

		# keybindings should be stored in the plugin.keybindings property and be registered by the appropriate keybinding registrar
		#if isinstance(self._action, Keybinding):
		#	self._action.create()


# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = Agenda
# -*- coding: utf-8 -*-

from datetime import date
import os
import glob

import vim

from orgmode._vim import ORGMODE, get_bufnumber, get_bufname, echoe
from orgmode import settings
from orgmode.keybinding import Keybinding, Plug, Command
from orgmode.menu import Submenu, ActionEntry, add_cmd_mapping_menu


class Agenda(object):
	u"""
	The Agenda Plugin uses liborgmode.agenda to display the agenda views.

	The main task is to format the agenda from liborgmode.agenda.
	Also all the mappings: jump from agenda to todo, etc are realized here.
	"""

	def __init__(self):
		u""" Initialize plugin """
		object.__init__(self)
		# menu entries this plugin should create
		self.menu = ORGMODE.orgmenu + Submenu(u'Agenda')

		# key bindings for this plugin
		# key bindings are also registered through the menu so only additional
		# bindings should be put in this variable
		self.keybindings = []

		# commands for this plugin
		self.commands = []

	@classmethod
	def _switch_to(cls, bufname, vim_commands=None):
		u"""
		Swicht to the buffer with bufname.

		A list of vim.commands (if given) gets executed as well.

		TODO: this should be extracted and imporved to create an easy to use
		way to create buffers/jump to buffers. Otherwise there are going to be
		quite a few ways to open buffers in vimorgmode.
		"""
		cmds = [
			u'botright split org:%s' % bufname,
			u'setlocal buftype=nofile',
			u'setlocal modifiable',
			u'setlocal nonumber',
			# call opendoc() on enter the original todo item
			u'nnoremap <silent> <buffer> <CR> :exec "py ORGMODE.plugins[u\'Agenda\'].opendoc()"<CR>',
			u'nnoremap <silent> <buffer> <TAB> :exec "py ORGMODE.plugins[u\'Agenda\'].opendoc(switch=True)"<CR>',
			u'nnoremap <silent> <buffer> <S-CR> :exec "py ORGMODE.plugins[u\'Agenda\'].opendoc(split=True)"<CR>',
			# statusline
			u'setlocal statusline=Org\\ %s' % bufname]
		if vim_commands:
			cmds.extend(vim_commands)
		for cmd in cmds:
			vim.command(cmd.encode(u'utf-8'))

	@classmethod
	def _get_agendadocuments(self):
		u"""
		Return the org documents of the agenda files; return None if no
		agenda documents are defined.

		TODO: maybe turn this into an decorator?
		"""
		# load org files of agenda
		agenda_files = settings.get(u'org_agenda_files', u',')
		if not agenda_files or agenda_files == ',':
			echoe((
				u"No org_agenda_files defined. Use :let "
				u"g:org_agenda_files=['~/org/index.org'] to add "
				u"files to the agenda view."))
			return

		# glob for files in agenda_files
		resolved_files = []
		for f in agenda_files:
			f = glob.glob(os.path.join(
				os.path.expanduser(os.path.dirname(f)),
				os.path.basename(f)))
			resolved_files.extend(f)

		agenda_files = [os.path.realpath(f) for f in resolved_files]

		# load the agenda files into buffers
		for agenda_file in agenda_files:
			vim.command((u'badd %s' % agenda_file.replace(" ", "\ ")).encode(u'utf-8'))

		# determine the buffer nr of the agenda files
		agenda_nums = [get_bufnumber(fn) for fn in agenda_files]

		# collect all documents of the agenda files and create the agenda
		return [ORGMODE.get_document(i) for i in agenda_nums if i is not None]

	@classmethod
	def opendoc(cls, split=False, switch=False):
		u"""
		If you are in the agenda view jump to the document the item in the
		current line belongs to. cls.line2doc is used for that.

		:split: if True, open the document in a new split window.
		:switch: if True, switch to another window and open the the document
			there.
		"""
		row, _ = vim.current.window.cursor
		try:
			bufname, bufnr, destrow = cls.line2doc[row]
		except:
			return

		# reload source file if it is not loaded
		if get_bufname(bufnr) is None:
			vim.command((u'badd %s' % bufname).encode(u'utf-8'))
			bufnr = get_bufnumber(bufname)
			tmp = cls.line2doc[row]
			cls.line2doc[bufnr] = tmp
			# delete old endry
			del cls.line2doc[row]

		if split:
			vim.command((u"sbuffer %s" % bufnr).encode(u'utf-8'))
		elif switch:
			vim.command(u"wincmd w".encode(u'utf-8'))
			vim.command((u"buffer %d" % bufnr).encode(u'utf-8'))
		else:
			vim.command((u"buffer %s" % bufnr).encode(u'utf-8'))
		vim.command((u"normal! %dgg <CR>" % (destrow + 1)).encode(u'utf-8'))

	@classmethod
	def list_next_week(cls):
		agenda_documents = cls._get_agendadocuments()
		if not agenda_documents:
			return
		raw_agenda = ORGMODE.agenda_manager.get_next_week_and_active_todo(
			agenda_documents)

		# create buffer at bottom
		cmd = [u'setlocal filetype=orgagenda', ]
		cls._switch_to(u'AGENDA', cmd)

		# line2doc is a dic with the mapping:
		#     line in agenda buffer --> source document
		# It's easy to jump to the right document this way
		cls.line2doc = {}
		# format text for agenda
		last_date = raw_agenda[0].active_date
		final_agenda = [u'Week Agenda:', unicode(last_date)]
		for i, h in enumerate(raw_agenda):
			# insert date information for every new date (not datetime)
			if unicode(h.active_date)[1:11] != unicode(last_date)[1:11]:
				today = date.today()
				# insert additional "TODAY" string
				if h.active_date.year == today.year and \
					h.active_date.month == today.month and \
					h.active_date.day == today.day:
					section = unicode(h.active_date) + u" TODAY"
					today_row = len(final_agenda) + 1
				else:
					section = unicode(h.active_date)
				final_agenda.append(section)

				# update last_date
				last_date = h.active_date

			bufname = os.path.basename(vim.buffers[h.document.bufnr - 1].name)
			bufname = bufname[:-4] if bufname.endswith(u'.org') else bufname
			formated = u"  %(bufname)s (%(bufnr)d)  %(todo)s  %(title)s" % {
				'bufname': bufname,
				'bufnr': h.document.bufnr,
				'todo': h.todo,
				'title': h.title
			}
			final_agenda.append(formated)
			cls.line2doc[len(final_agenda)] = (get_bufname(h.document.bufnr), h.document.bufnr, h.start)

		# show agenda
		vim.current.buffer[:] = [i.encode(u'utf-8') for i in final_agenda]
		vim.command(u'setlocal nomodifiable  conceallevel=2 concealcursor=nc'.encode(u'utf-8'))
		# try to jump to the positon of today
		try:
			vim.command((u'normal! %sgg<CR>' % today_row).encode(u'utf-8'))
		except:
			pass

	@classmethod
	def list_all_todos(cls):
		u"""
		List all todos in all agenda files in one buffer.
		"""
		agenda_documents = cls._get_agendadocuments()
		if not agenda_documents:
			return
		raw_agenda = ORGMODE.agenda_manager.get_todo(agenda_documents)

		cls.line2doc = {}
		# create buffer at bottom
		cmd = [u'setlocal filetype=orgagenda']
		cls._switch_to(u'AGENDA', cmd)

		# format text of agenda
		final_agenda = []
		for i, h in enumerate(raw_agenda):
			tmp = u"%s %s" % (h.todo, h.title)
			final_agenda.append(tmp)
			cls.line2doc[len(final_agenda)] = (get_bufname(h.document.bufnr), h.document.bufnr, h.start)

		# show agenda
		vim.current.buffer[:] = [i.encode(u'utf-8') for i in final_agenda]
		vim.command(u'setlocal nomodifiable  conceallevel=2 concealcursor=nc'.encode(u'utf-8'))

	@classmethod
	def list_timeline(cls):
		"""
		List a timeline of the current buffer to get an overview of the
		current file.
		"""
		raw_agenda = ORGMODE.agenda_manager.get_timestamped_items(
			[ORGMODE.get_document()])

		# create buffer at bottom
		cmd = [u'setlocal filetype=orgagenda']
		cls._switch_to(u'AGENDA', cmd)

		cls.line2doc = {}
		# format text of agenda
		final_agenda = []
		for i, h in enumerate(raw_agenda):
			tmp = u"%s %s" % (h.todo, h.title)
			final_agenda.append(tmp)
			cls.line2doc[len(final_agenda)] = (get_bufname(h.document.bufnr), h.document.bufnr, h.start)

		# show agenda
		vim.current.buffer[:] = [i.encode(u'utf-8') for i in final_agenda]
		vim.command(u'setlocal nomodifiable conceallevel=2 concealcursor=nc'.encode(u'utf-8'))

	def register(self):
		u"""
		Registration of the plugin.

		Key bindings and other initialization should be done here.
		"""
		add_cmd_mapping_menu(
			self,
			name=u"OrgAgendaTodo",
			function=u':py ORGMODE.plugins[u"Agenda"].list_all_todos()',
			key_mapping=u'<localleader>cat',
			menu_desrc=u'Agenda for all TODOs'
		)
		add_cmd_mapping_menu(
			self,
			name=u"OrgAgendaWeek",
			function=u':py ORGMODE.plugins[u"Agenda"].list_next_week()',
			key_mapping=u'<localleader>caa',
			menu_desrc=u'Agenda for the week'
		)
		add_cmd_mapping_menu(
			self,
			name=u'OrgAgendaTimeline',
			function=u':py ORGMODE.plugins[u"Agenda"].list_timeline()',
			key_mapping=u'<localleader>caL',
			menu_desrc=u'Timeline for this buffer'
		)

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = Date
# -*- coding: utf-8 -*-
import re
from datetime import timedelta, date, datetime

import vim

from orgmode._vim import ORGMODE, echom, insert_at_cursor, get_user_input
from orgmode import settings
from orgmode.keybinding import Keybinding, Plug
from orgmode.menu import Submenu, ActionEntry, add_cmd_mapping_menu


class Date(object):
	u"""
	Handles all date and timestamp related tasks.

	TODO: extend functionality (calendar, repetitions, ranges). See
			http://orgmode.org/guide/Dates-and-Times.html#Dates-and-Times
	"""

	date_regex = r"\d\d\d\d-\d\d-\d\d"
	datetime_regex = r"[A-Z]\w\w \d\d\d\d-\d\d-\d\d \d\d:\d\d>"

	month_mapping = {
		u'jan': 1, u'feb': 2, u'mar': 3, u'apr': 4, u'may': 5,
		u'jun': 6, u'jul': 7, u'aug': 8, u'sep': 9, u'oct': 10, u'nov': 11,
		u'dec': 12}

	def __init__(self):
		u""" Initialize plugin """
		object.__init__(self)
		# menu entries this plugin should create
		self.menu = ORGMODE.orgmenu + Submenu(u'Dates and Scheduling')

		# key bindings for this plugin
		# key bindings are also registered through the menu so only additional
		# bindings should be put in this variable
		self.keybindings = []

		# commands for this plugin
		self.commands = []

		# set speeddating format that is compatible with orgmode
		try:
			if int(vim.eval(u'exists(":SpeedDatingFormat")'.encode(u'utf-8'))) == 2:
				vim.command(u':1SpeedDatingFormat %Y-%m-%d %a'.encode(u'utf-8'))
				vim.command(u':1SpeedDatingFormat %Y-%m-%d %a %H:%M'.encode(u'utf-8'))
			else:
				echom(u'Speeddating plugin not installed. Please install it.')
		except:
			echom(u'Speeddating plugin not installed. Please install it.')

	@classmethod
	def _modify_time(cls, startdate, modifier):
		u"""Modify the given startdate according to modifier. Return the new
		date or datetime.

		See http://orgmode.org/manual/The-date_002ftime-prompt.html
		"""
		if modifier is None or modifier == '' or modifier == '.':
			return startdate

		# rm crap from modifier
		modifier = modifier.strip()

		# check real date
		date_regex = r"(\d\d\d\d)-(\d\d)-(\d\d)"
		match = re.search(date_regex, modifier)
		if match:
			year, month, day = match.groups()
			newdate = date(int(year), int(month), int(day))

		# check abbreviated date, seperated with '-'
		date_regex = u"(\d{1,2})-(\d+)-(\d+)"
		match = re.search(date_regex, modifier)
		if match:
			year, month, day = match.groups()
			newdate = date(2000 + int(year), int(month), int(day))

		# check abbreviated date, seperated with '/'
		# month/day
		date_regex = u"(\d{1,2})/(\d{1,2})"
		match = re.search(date_regex, modifier)
		if match:
			month, day = match.groups()
			newdate = date(startdate.year, int(month), int(day))
			# date should be always in the future
			if newdate < startdate:
				newdate = date(startdate.year + 1, int(month), int(day))

		# check full date, seperated with 'space'
		# month day year
		# 'sep 12 9' --> 2009 9 12
		date_regex = u"(\w\w\w) (\d{1,2}) (\d{1,2})"
		match = re.search(date_regex, modifier)
		if match:
			gr = match.groups()
			day = int(gr[1])
			month = int(cls.month_mapping[gr[0]])
			year = 2000 + int(gr[2])
			newdate = date(year, int(month), int(day))

		# check days as integers
		date_regex = u"^(\d{1,2})$"
		match = re.search(date_regex, modifier)
		if match:
			newday, = match.groups()
			newday = int(newday)
			if newday > startdate.day:
				newdate = date(startdate.year, startdate.month, newday)
			else:
				# TODO: DIRTY, fix this
				#       this does NOT cover all edge cases
				newdate = startdate + timedelta(days=28)
				newdate = date(newdate.year, newdate.month, newday)

		# check for full days: Mon, Tue, Wed, Thu, Fri, Sat, Sun
		modifier_lc = modifier.lower()
		match = re.search(u'mon|tue|wed|thu|fri|sat|sun', modifier_lc)
		if match:
			weekday_mapping = {
				u'mon': 0, u'tue': 1, u'wed': 2, u'thu': 3,
				u'fri': 4, u'sat': 5, u'sun': 6}
			diff = (weekday_mapping[modifier_lc] - startdate.weekday()) % 7
			# use next weeks weekday if current weekday is the same as modifier
			if diff == 0:
				diff = 7
			newdate = startdate + timedelta(days=diff)

		# check for days modifier with appended d
		match = re.search(u'\+(\d*)d', modifier)
		if match:
			days = int(match.groups()[0])
			newdate = startdate + timedelta(days=days)

		# check for days modifier without appended d
		match = re.search(u'\+(\d*) |\+(\d*)$', modifier)
		if match:
			try:
				days = int(match.groups()[0])
			except:
				days = int(match.groups()[1])
			newdate = startdate + timedelta(days=days)

		# check for week modifier
		match = re.search(u'\+(\d+)w', modifier)
		if match:
			weeks = int(match.groups()[0])
			newdate = startdate + timedelta(weeks=weeks)

		# check for week modifier
		match = re.search(u'\+(\d+)m', modifier)
		if match:
			months = int(match.groups()[0])
			newdate = date(startdate.year, startdate.month + months, startdate.day)

		# check for year modifier
		match = re.search(u'\+(\d*)y', modifier)
		if match:
			years = int(match.groups()[0])
			newdate = date(startdate.year + years, startdate.month, startdate.day)

		# check for month day
		match = re.search(
			u'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec) (\d{1,2})',
			modifier.lower())
		if match:
			month = cls.month_mapping[match.groups()[0]]
			day = int(match.groups()[1])
			newdate = date(startdate.year, int(month), int(day))
			# date should be always in the future
			if newdate < startdate:
				newdate = date(startdate.year + 1, int(month), int(day))

		# check abbreviated date, seperated with '/'
		# month/day/year
		date_regex = u"(\d{1,2})/(\d+)/(\d+)"
		match = re.search(date_regex, modifier)
		if match:
			month, day, year = match.groups()
			newdate = date(2000 + int(year), int(month), int(day))

		# check for month day year
		# sep 12 2011
		match = re.search(
			u'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec) (\d{1,2}) (\d{1,4})',
			modifier.lower())
		if match:
			month = int(cls.month_mapping[match.groups()[0]])
			day = int(match.groups()[1])
			if len(match.groups()[2]) < 4:
				year = 2000 + int(match.groups()[2])
			else:
				year = int(match.groups()[2])
			newdate = date(year, month, day)

		# check for time: HH:MM
		# '12:45' --> datetime(2006, 06, 13, 12, 45))
		match = re.search(u'(\d{1,2}):(\d\d)$', modifier)
		if match:
			try:
				startdate = newdate
			except:
				pass
			return datetime(
				startdate.year, startdate.month, startdate.day,
				int(match.groups()[0]), int(match.groups()[1]))

		try:
			return newdate
		except:
			return startdate

	@classmethod
	def insert_timestamp(cls, active=True):
		u"""
		Insert a timestamp at the cursor position.

		TODO: show fancy calendar to pick the date from.
		TODO: add all modifier of orgmode.
		"""
		today = date.today()
		msg = u''.join([
			u'Inserting ',
			unicode(today.strftime(u'%Y-%m-%d %a'), u'utf-8'),
			u' | Modify date'])
		modifier = get_user_input(msg)

		# abort if the user canceled the input promt
		if modifier is None:
			return

		newdate = cls._modify_time(today, modifier)

		# format
		if isinstance(newdate, datetime):
			newdate = newdate.strftime(
				u'%Y-%m-%d %a %H:%M'.encode(u'utf-8')).decode(u'utf-8')
		else:
			newdate = newdate.strftime(
				u'%Y-%m-%d %a'.encode(u'utf-8')).decode(u'utf-8')
		timestamp = u'<%s>' % newdate if active else u'[%s]' % newdate

		insert_at_cursor(timestamp)

	@classmethod
	def insert_timestamp_with_calendar(cls, active=True):
		u"""
		Insert a timestamp at the cursor position.
		Show fancy calendar to pick the date from.

		TODO: add all modifier of orgmode.
		"""
		if int(vim.eval(u'exists(":CalendarH")'.encode(u'utf-8'))) != 2:
			vim.command("echo 'Please install plugin Calendar to enable this function'")
			return
		vim.command("CalendarH")
		# backup calendar_action
		calendar_action = vim.eval("g:calendar_action")
		vim.command("let g:org_calendar_action_backup = '" + calendar_action + "'")
		vim.command("let g:calendar_action = 'CalendarAction'")

		timestamp_template = u'<%s>' if active else u'[%s]'
		# timestamp template
		vim.command("let g:org_timestamp_template = '" + timestamp_template + "'")

	def register(self):
		u"""
		Registration of the plugin.

		Key bindings and other initialization should be done here.
		"""
		add_cmd_mapping_menu(
			self,
			name=u'OrgDateInsertTimestampActiveCmdLine',
			key_mapping=u'<localleader>sa',
			function=u':py ORGMODE.plugins[u"Date"].insert_timestamp()',
			menu_desrc=u'Timest&amp'
		)
		add_cmd_mapping_menu(
			self,
			name=u'OrgDateInsertTimestampInactiveCmdLine',
			key_mapping='<localleader>si',
			function=u':py ORGMODE.plugins[u"Date"].insert_timestamp(False)',
			menu_desrc=u'Timestamp (&inactive)'
		)
		add_cmd_mapping_menu(
			self,
			name=u'OrgDateInsertTimestampActiveWithCalendar',
			key_mapping=u'<localleader>pa',
			function=u':py ORGMODE.plugins[u"Date"].insert_timestamp_with_calendar()',
			menu_desrc=u'Timestamp with Calendar'
		)
		add_cmd_mapping_menu(
			self,
			name=u'OrgDateInsertTimestampInactiveWithCalendar',
			key_mapping=u'<localleader>pi',
			function=u':py ORGMODE.plugins[u"Date"].insert_timestamp_with_calendar(False)',
			menu_desrc=u'Timestamp with Calendar(inactive)'
		)

		submenu = self.menu + Submenu(u'Change &Date')
		submenu + ActionEntry(u'Day &Earlier', u'<C-x>', u'<C-x>')
		submenu + ActionEntry(u'Day &Later', u'<C-a>', u'<C-a>')

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = EditCheckbox
# -*- coding: utf-8 -*-

import vim
from orgmode._vim import echo, echom, echoe, ORGMODE, apply_count, repeat, insert_at_cursor, indent_orgmode
from orgmode.menu import Submenu, Separator, ActionEntry, add_cmd_mapping_menu
from orgmode.keybinding import Keybinding, Plug, Command
from orgmode.liborgmode.checkboxes import Checkbox
from orgmode.liborgmode.dom_obj import OrderListType


class EditCheckbox(object):
	u"""
	Checkbox plugin.
	"""

	def __init__(self):
		u""" Initialize plugin """
		object.__init__(self)
		# menu entries this plugin should create
		self.menu = ORGMODE.orgmenu + Submenu(u'Edit Checkbox')

		# key bindings for this plugin
		# key bindings are also registered through the menu so only additional
		# bindings should be put in this variable
		self.keybindings = []

		# commands for this plugin
		self.commands = []

	@classmethod
	def new_checkbox(cls, below=None):
		d = ORGMODE.get_document()
		h = d.current_heading()
		if h is None:
			return
		# init checkboxes for current heading
		h.init_checkboxes()
		c = h.current_checkbox()

		nc = Checkbox()
		nc._heading = h

		# default checkbox level
		level = h.level
		start = vim.current.window.cursor[0] - 1
		# if no checkbox is found, insert at current line with indent level=1
		if c is None:
			if h.checkboxes:
				level = h.first_checkbox.level
				h.checkboxes.append(nc)
		else:
			l = c.get_parent_list()
			idx = c.get_index_in_parent_list()
			if l is not None and idx is not None:
				l.insert(idx + (1 if below else 0), nc)
				# workaround for broken associations, Issue #165
				nc._parent = c.parent
				if below:
					if c.next_sibling:
						c.next_sibling._previous_sibling = nc
					nc._next_sibling = c.next_sibling
					c._next_sibling = nc
					nc._previous_sibling = c
				else:
					if c.previous_sibling:
						c.previous_sibling._next_sibling = nc
					nc._next_sibling = c
					nc._previous_sibling = c.previous_sibling
					c._previous_sibling = nc

			t = c.type
			# increase key for ordered lists
			if t[-1] in OrderListType:
				try:
					num = int(t[:-1]) + (1 if below else -1)
					t = '%d%s' % (num, t[-1])
				except ValueError:
					try:
						char = ord(t[:-1]) + (1 if below else -1)
						t = '%s%s' % (chr(char), t[-1])
					except ValueError:
						pass
			nc.type = t
			if not c.status:
				nc.status = None
			level = c.level

			if below:
				start = c.end_of_last_child
			else:
				start = c.start
		nc.level = level

		vim.current.window.cursor = (start + 1, 0)

		if below:
			vim.command("normal o")
		else:
			vim.command("normal O")

		insert_at_cursor(str(nc))
		vim.command("call feedkeys('a')")

	@classmethod
	def toggle(cls, checkbox=None):
		u"""
		Toggle the checkbox given in the parameter.
		If the checkbox is not given, it will toggle the current checkbox.
		"""
		d = ORGMODE.get_document()
		current_heading = d.current_heading()
		# init checkboxes for current heading
		if current_heading is None:
			return
		current_heading = current_heading.init_checkboxes()

		if checkbox is None:
			# get current_checkbox
			c = current_heading.current_checkbox()
			# no checkbox found
			if c is None:
				cls.update_checkboxes_status()
				return
		else:
			c = checkbox

		if c.status == Checkbox.STATUS_OFF:
			# set checkbox status on if all children are on
			if not c.children or c.are_children_all(Checkbox.STATUS_ON):
				c.toggle()
				d.write_checkbox(c)

		elif c.status == Checkbox.STATUS_ON:
			if not c.children or c.is_child_one(Checkbox.STATUS_OFF):
				c.toggle()
				d.write_checkbox(c)

		elif c.status == Checkbox.STATUS_INT:
			# can't toggle intermediate state directly according to emacs orgmode
			pass
		# update checkboxes status
		cls.update_checkboxes_status()

	@classmethod
	def _update_subtasks(cls):
		d = ORGMODE.get_document()
		h = d.current_heading()
		# init checkboxes for current heading
		h.init_checkboxes()
		# update heading subtask info
		c = h.first_checkbox
		if c is None:
			return
		total, on = c.all_siblings_status()
		h.update_subtasks(total, on)
		# update all checkboxes under current heading
		cls._update_checkboxes_subtasks(c)

	@classmethod
	def _update_checkboxes_subtasks(cls, checkbox):
		# update checkboxes
		for c in checkbox.all_siblings():
			if c.children:
				total, on = c.first_child.all_siblings_status()
				c.update_subtasks(total, on)
				cls._update_checkboxes_subtasks(c.first_child)

	@classmethod
	def update_checkboxes_status(cls):
		d = ORGMODE.get_document()
		h = d.current_heading()
		# init checkboxes for current heading
		h.init_checkboxes()

		cls._update_checkboxes_status(h.first_checkbox)
		cls._update_subtasks()

	@classmethod
	def _update_checkboxes_status(cls, checkbox=None):
		u""" helper function for update checkboxes status
			:checkbox: The first checkbox of this indent level
			:return: The status of the parent checkbox
		"""
		if checkbox is None:
			return

		status_off, status_on, status_int, total = 0, 0, 0, 0
		# update all top level checkboxes' status
		for c in checkbox.all_siblings():
			current_status = c.status
			# if this checkbox is not leaf, its status should determine by all its children
			if c.children:
				current_status = cls._update_checkboxes_status(c.first_child)

			# don't update status if the checkbox has no status
			if c.status is None:
				current_status = None
			# the checkbox needs to have status
			else:
				total +=  1

			# count number of status in this checkbox level
			if current_status == Checkbox.STATUS_OFF:
				status_off += 1
			elif current_status == Checkbox.STATUS_ON:
				status_on += 1
			elif current_status == Checkbox.STATUS_INT:
				status_int += 1

			# write status if any update
			if current_status is not None and c.status != current_status:
				c.status = current_status
				d = ORGMODE.get_document()
				d.write_checkbox(c)

		parent_status = Checkbox.STATUS_INT
		# all silbing checkboxes are off status
		if status_off == total:
			parent_status = Checkbox.STATUS_OFF
		# all silbing checkboxes are on status
		elif status_on == total:
			parent_status = Checkbox.STATUS_ON
		# one silbing checkbox is on or int status
		elif status_on != 0 or status_int != 0:
			parent_status = Checkbox.STATUS_INT
		# other cases
		else:
			parent_status = None

		return parent_status

	def register(self):
		u"""
		Registration of the plugin.

		Key bindings and other initialization should be done here.
		"""
		add_cmd_mapping_menu(
			self,
			name=u'OrgCheckBoxNewAbove',
			function=u':py ORGMODE.plugins[u"EditCheckbox"].new_checkbox()<CR>',
			key_mapping=u'<localleader>cN',
			menu_desrc=u'New CheckBox Above'
		)
		add_cmd_mapping_menu(
			self,
			name=u'OrgCheckBoxNewBelow',
			function=u':py ORGMODE.plugins[u"EditCheckbox"].new_checkbox(below=True)<CR>',
			key_mapping=u'<localleader>cn',
			menu_desrc=u'New CheckBox Below'
		)
		add_cmd_mapping_menu(
			self,
			name=u'OrgCheckBoxToggle',
			function=u':silent! py ORGMODE.plugins[u"EditCheckbox"].toggle()<CR>',
			key_mapping=u'<localleader>cc',
			menu_desrc=u'Toggle Checkbox'
		)
		add_cmd_mapping_menu(
			self,
			name=u'OrgCheckBoxUpdate',
			function=u':silent! py ORGMODE.plugins[u"EditCheckbox"].update_checkboxes_status()<CR>',
			key_mapping=u'<localleader>c#',
			menu_desrc=u'Update Subtasks'
		)

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = EditStructure
# -*- coding: utf-8 -*-

import vim

from orgmode._vim import ORGMODE, apply_count, repeat, realign_tags
from orgmode import settings
from orgmode.exceptions import HeadingDomError
from orgmode.keybinding import Keybinding, Plug, MODE_INSERT, MODE_NORMAL
from orgmode.menu import Submenu, Separator, ActionEntry
from orgmode.liborgmode.base import Direction
from orgmode.liborgmode.headings import Heading


class EditStructure(object):
	u""" EditStructure plugin """

	def __init__(self):
		u""" Initialize plugin """
		object.__init__(self)
		# menu entries this plugin should create
		self.menu = ORGMODE.orgmenu + Submenu(u'&Edit Structure')

		# key bindings for this plugin
		# key bindings are also registered through the menu so only additional
		# bindings should be put in this variable
		self.keybindings = []

	@classmethod
	def new_heading(cls, below=None, insert_mode=False, end_of_last_child=False):
		u"""
		:below:				True, insert heading below current heading, False,
							insert heading above current heading, None, special
							behavior for insert mode, use the current text as
							heading
		:insert_mode:		True, if action is performed in insert mode
		:end_of_last_child:	True, insert heading at the end of last child,
							otherwise the newly created heading will "take
							over" the current heading's children
		"""
		d = ORGMODE.get_document()
		current_heading = d.current_heading()
		cursor = vim.current.window.cursor[:]
		if not current_heading:
			# the user is in meta data region
			pos = cursor[0] - 1
			heading = Heading(title=d.meta_information[pos], body=d.meta_information[pos + 1:])
			d.headings.insert(0, heading)
			del d.meta_information[pos:]
			d.write()
			vim.command((u'exe "normal %dgg"|startinsert!' % (heading.start_vim, )).encode(u'utf-8'))
			return heading

		heading = Heading(level=current_heading.level)

		# it's weird but this is the behavior of original orgmode
		if below is None:
			below = cursor[1] != 0 or end_of_last_child

		# insert newly created heading
		l = current_heading.get_parent_list()
		idx = current_heading.get_index_in_parent_list()
		if l is not None and idx is not None:
			l.insert(idx + (1 if below else 0), heading)
		else:
			raise HeadingDomError(u'Current heading is not properly linked in DOM')

		if below and not end_of_last_child:
			# append heading at the end of current heading and also take
			# over the children of current heading
			for child in current_heading.children:
				heading.children.append(child, taint=False)
			current_heading.children.remove_slice(
				0, len(current_heading.children),
				taint=False)

		# if cursor is currently on a heading, insert parts of it into the
		# newly created heading
		if insert_mode and cursor[1] != 0 and cursor[0] == current_heading.start_vim:
			offset = cursor[1] - current_heading.level - 1 - (
				len(current_heading.todo) + 1 if current_heading.todo else 0)
			if offset < 0:
				offset = 0
			if int(settings.get(u'org_improve_split_heading', u'1')) and \
				offset > 0 and len(current_heading.title) == offset + 1 \
				and current_heading.title[offset - 1] not in (u' ', u'\t'):
				offset += 1
			heading.title = current_heading.title[offset:]
			current_heading.title = current_heading.title[:offset]
			heading.body = current_heading.body[:]
			current_heading.body = []

		d.write()
		vim.command((u'exe "normal %dgg"|startinsert!' % (heading.start_vim, )).encode(u'utf-8'))

		# return newly created heading
		return heading

	@classmethod
	def _append_heading(cls, heading, parent):
		if heading.level <= parent.level:
			raise ValueError('Heading level not is lower than parent level: %d ! > %d' % (heading.level, parent.level))

		if parent.children and parent.children[-1].level < heading.level:
			cls._append_heading(heading, parent.children[-1])
		else:
			parent.children.append(heading, taint=False)

	@classmethod
	def _change_heading_level(cls, level, including_children=True, on_heading=False, insert_mode=False):
		u"""
		Change level of heading realtively with or without including children.

		:level:					the number of levels to promote/demote heading
		:including_children:	True if should should be included in promoting/demoting
		:on_heading:			True if promoting/demoting should only happen when the cursor is on the heading
		:insert_mode:			True if vim is in insert mode
		"""
		d = ORGMODE.get_document()
		current_heading = d.current_heading()
		if not current_heading or on_heading and current_heading.start_vim != vim.current.window.cursor[0]:
			# TODO figure out the actually pressed keybinding and feed these
			# keys instead of making keys up like this
			if level > 0:
				if insert_mode:
					vim.eval(u'feedkeys("\<C-t>", "n")'.encode(u'utf-8'))
				elif including_children:
					vim.eval(u'feedkeys(">]]", "n")'.encode(u'utf-8'))
				elif on_heading:
					vim.eval(u'feedkeys(">>", "n")'.encode(u'utf-8'))
				else:
					vim.eval(u'feedkeys(">}", "n")'.encode(u'utf-8'))
			else:
				if insert_mode:
					vim.eval(u'feedkeys("\<C-d>", "n")'.encode(u'utf-8'))
				elif including_children:
					vim.eval(u'feedkeys("<]]", "n")'.encode(u'utf-8'))
				elif on_heading:
					vim.eval(u'feedkeys("<<", "n")'.encode(u'utf-8'))
				else:
					vim.eval(u'feedkeys("<}", "n")'.encode(u'utf-8'))
			# return True because otherwise apply_count will not work
			return True

		# don't allow demotion below level 1
		if current_heading.level == 1 and level < 1:
			return False

		# reduce level of demotion to a minimum heading level of 1
		if (current_heading.level + level) < 1:
			level = 1

		def indent(heading, ic):
			if not heading:
				return
			heading.level += level

			if ic:
				for child in heading.children:
					indent(child, ic)

		# save cursor position
		c = vim.current.window.cursor[:]

		# indent the promoted/demoted heading
		indent_end_vim = current_heading.end_of_last_child_vim if including_children else current_heading.end_vim
		indent(current_heading, including_children)

		# when changing the level of a heading, its position in the DOM
		# needs to be updated. It's likely that the heading gets a new
		# parent and new children when demoted or promoted

		# find new parent
		p = current_heading.parent
		pl = current_heading.get_parent_list()
		ps = current_heading.previous_sibling
		nhl = current_heading.level

		if level > 0:
			# demotion
			# subheading or top level heading
			if ps and nhl > ps.level:
				pl.remove(current_heading, taint=False)
				# find heading that is the new parent heading
				oh = ps
				h = ps
				while nhl > h.level:
					oh = h
					if h.children:
						h = h.children[-1]
					else:
						break
				np = h if nhl > h.level else oh

				# append current heading to new heading
				np.children.append(current_heading, taint=False)

				# if children are not included, distribute them among the
				# parent heading and it's siblings
				if not including_children:
					for h in current_heading.children[:]:
						if h and h.level <= nhl:
							cls._append_heading(h, np)
							current_heading.children.remove(h, taint=False)
		else:
			# promotion
			if p and nhl <= p.level:
				idx = current_heading.get_index_in_parent_list() + 1
				# find the new parent heading
				oh = p
				h = p
				while nhl <= h.level:
					# append new children to current heading
					for child in h.children[idx:]:
						cls._append_heading(child, current_heading)
					h.children.remove_slice(idx, len(h.children), taint=False)
					idx = h.get_index_in_parent_list() + 1
					if h.parent:
						h = h.parent
					else:
						break
				ns = oh.next_sibling
				while ns and ns.level > current_heading.level:
					nns = ns.next_sibling
					cls._append_heading(ns, current_heading)
					ns = nns

				# append current heading to new parent heading / document
				pl.remove(current_heading, taint=False)
				if nhl > h.level:
					h.children.insert(idx, current_heading, taint=False)
				else:
					d.headings.insert(idx, current_heading, taint=False)

		d.write()
		if indent_end_vim != current_heading.start_vim:
			vim.command((u'normal %dggV%dgg=' % (current_heading.start_vim, indent_end_vim)).encode(u'utf-8'))
		# restore cursor position
		vim.current.window.cursor = (c[0], c[1] + level)

		return True

	@classmethod
	@realign_tags
	@repeat
	@apply_count
	def demote_heading(cls, including_children=True, on_heading=False, insert_mode=False):
		if cls._change_heading_level(1, including_children=including_children, on_heading=on_heading, insert_mode=insert_mode):
			if including_children:
				return u'OrgDemoteSubtree'
			return u'OrgDemoteHeading'

	@classmethod
	@realign_tags
	@repeat
	@apply_count
	def promote_heading(cls, including_children=True, on_heading=False, insert_mode=False):
		if cls._change_heading_level(-1, including_children=including_children, on_heading=on_heading, insert_mode=insert_mode):
			if including_children:
				return u'OrgPromoteSubtreeNormal'
			return u'OrgPromoteHeadingNormal'

	@classmethod
	def _move_heading(cls, direction=Direction.FORWARD, including_children=True):
		u""" Move heading up or down

		:returns: heading or None
		"""
		d = ORGMODE.get_document()
		current_heading = d.current_heading()
		if not current_heading or \
			(direction == Direction.FORWARD and not current_heading.next_sibling) or \
			(direction == Direction.BACKWARD and not current_heading.previous_sibling):
			return None

		cursor_offset = vim.current.window.cursor[0] - (current_heading._orig_start + 1)
		l = current_heading.get_parent_list()
		if l is None:
			raise HeadingDomError(u'Current heading is not properly linked in DOM')

		if not including_children:
			if current_heading.previous_sibling:
				npl = current_heading.previous_sibling.children
				for child in current_heading.children:
					npl.append(child, taint=False)
			elif current_heading.parent:
				# if the current heading doesn't have a previous sibling it
				# must be the first heading
				np = current_heading.parent
				for child in current_heading.children:
					cls._append_heading(child, np)
			else:
				# if the current heading doesn't have a parent, its children
				# must be added as top level headings to the document
				npl = l
				for child in current_heading.children[::-1]:
					npl.insert(0, child, taint=False)
			current_heading.children.remove_slice(0, len(current_heading.children), taint=False)

		idx = current_heading.get_index_in_parent_list()
		if idx is None:
			raise HeadingDomError(u'Current heading is not properly linked in DOM')

		offset = 1 if direction == Direction.FORWARD else -1
		del l[idx]
		l.insert(idx + offset, current_heading)

		d.write()

		vim.current.window.cursor = (
			current_heading.start_vim + cursor_offset,
			vim.current.window.cursor[1])

		return True

	@classmethod
	@repeat
	@apply_count
	def move_heading_upward(cls, including_children=True):
		if cls._move_heading(direction=Direction.BACKWARD, including_children=including_children):
			if including_children:
				return u'OrgMoveSubtreeUpward'
			return u'OrgMoveHeadingUpward'

	@classmethod
	@repeat
	@apply_count
	def move_heading_downward(cls, including_children=True):
		if cls._move_heading(direction=Direction.FORWARD, including_children=including_children):
			if including_children:
				return u'OrgMoveSubtreeDownward'
			return u'OrgMoveHeadingDownward'

	def register(self):
		u"""
		Registration of plugin. Key bindings and other initialization should be done.
		"""
		settings.set(u'org_improve_split_heading', u'1')

		self.keybindings.append(Keybinding(u'<C-S-CR>', Plug(u'OrgNewHeadingAboveNormal', u':silent! py ORGMODE.plugins[u"EditStructure"].new_heading(below=False)<CR>')))
		self.menu + ActionEntry(u'New Heading &above', self.keybindings[-1])
		self.keybindings.append(Keybinding(u'<S-CR>', Plug(u'OrgNewHeadingBelowNormal', u':silent! py ORGMODE.plugins[u"EditStructure"].new_heading(below=True)<CR>')))
		self.menu + ActionEntry(u'New Heading &below', self.keybindings[-1])
		self.keybindings.append(Keybinding(u'<C-CR>', Plug(u'OrgNewHeadingBelowAfterChildrenNormal', u':silent! py ORGMODE.plugins[u"EditStructure"].new_heading(below=True, end_of_last_child=True)<CR>')))
		self.menu + ActionEntry(u'New Heading below, after &children', self.keybindings[-1])

		self.keybindings.append(Keybinding(u'<C-S-CR>', Plug(u'OrgNewHeadingAboveInsert', u'<C-o>:<C-u>silent! py ORGMODE.plugins[u"EditStructure"].new_heading(below=False, insert_mode=True)<CR>', mode=MODE_INSERT)))
		self.keybindings.append(Keybinding(u'<S-CR>', Plug(u'OrgNewHeadingBelowInsert', u'<C-o>:<C-u>silent! py ORGMODE.plugins[u"EditStructure"].new_heading(insert_mode=True)<CR>', mode=MODE_INSERT)))
		self.keybindings.append(Keybinding(u'<C-CR>', Plug(u'OrgNewHeadingBelowAfterChildrenInsert', u'<C-o>:<C-u>silent! py ORGMODE.plugins[u"EditStructure"].new_heading(insert_mode=True, end_of_last_child=True)<CR>', mode=MODE_INSERT)))

		self.menu + Separator()

		self.keybindings.append(Keybinding(u'm{', Plug(u'OrgMoveHeadingUpward', u':py ORGMODE.plugins[u"EditStructure"].move_heading_upward(including_children=False)<CR>')))
		self.keybindings.append(Keybinding(u'm[[', Plug(u'OrgMoveSubtreeUpward', u':py ORGMODE.plugins[u"EditStructure"].move_heading_upward()<CR>')))
		self.menu + ActionEntry(u'Move Subtree &Up', self.keybindings[-1])
		self.keybindings.append(Keybinding(u'm}', Plug(u'OrgMoveHeadingDownward', u':py ORGMODE.plugins[u"EditStructure"].move_heading_downward(including_children=False)<CR>')))
		self.keybindings.append(Keybinding(u'm]]', Plug(u'OrgMoveSubtreeDownward', u':py ORGMODE.plugins[u"EditStructure"].move_heading_downward()<CR>')))
		self.menu + ActionEntry(u'Move Subtree &Down', self.keybindings[-1])

		self.menu + Separator()

		self.menu + ActionEntry(u'&Copy Heading', u'yah', u'yah')
		self.menu + ActionEntry(u'C&ut Heading', u'dah', u'dah')

		self.menu + Separator()

		self.menu + ActionEntry(u'&Copy Subtree', u'yar', u'yar')
		self.menu + ActionEntry(u'C&ut Subtree', u'dar', u'dar')
		self.menu + ActionEntry(u'&Paste Subtree', u'p', u'p')

		self.menu + Separator()

		self.keybindings.append(Keybinding(u'<ah', Plug(u'OrgPromoteHeadingNormal', u':silent! py ORGMODE.plugins[u"EditStructure"].promote_heading(including_children=False)<CR>')))
		self.menu + ActionEntry(u'&Promote Heading', self.keybindings[-1])
		self.keybindings.append(Keybinding(u'<<', Plug(u'OrgPromoteOnHeadingNormal', u':silent! py ORGMODE.plugins[u"EditStructure"].promote_heading(including_children=False, on_heading=True)<CR>')))
		self.keybindings.append(Keybinding(u'<{', u'<Plug>OrgPromoteHeadingNormal', mode=MODE_NORMAL))
		self.keybindings.append(Keybinding(u'<ih', u'<Plug>OrgPromoteHeadingNormal', mode=MODE_NORMAL))

		self.keybindings.append(Keybinding(u'<ar', Plug(u'OrgPromoteSubtreeNormal', u':silent! py ORGMODE.plugins[u"EditStructure"].promote_heading()<CR>')))
		self.menu + ActionEntry(u'&Promote Subtree', self.keybindings[-1])
		self.keybindings.append(Keybinding(u'<[[', u'<Plug>OrgPromoteSubtreeNormal', mode=MODE_NORMAL))
		self.keybindings.append(Keybinding(u'<ir', u'<Plug>OrgPromoteSubtreeNormal', mode=MODE_NORMAL))

		self.keybindings.append(Keybinding(u'>ah', Plug(u'OrgDemoteHeadingNormal', u':silent! py ORGMODE.plugins[u"EditStructure"].demote_heading(including_children=False)<CR>')))
		self.menu + ActionEntry(u'&Demote Heading', self.keybindings[-1])
		self.keybindings.append(Keybinding(u'>>', Plug(u'OrgDemoteOnHeadingNormal', u':silent! py ORGMODE.plugins[u"EditStructure"].demote_heading(including_children=False, on_heading=True)<CR>')))
		self.keybindings.append(Keybinding(u'>}', u'<Plug>OrgDemoteHeadingNormal', mode=MODE_NORMAL))
		self.keybindings.append(Keybinding(u'>ih', u'<Plug>OrgDemoteHeadingNormal', mode=MODE_NORMAL))

		self.keybindings.append(Keybinding(u'>ar', Plug(u'OrgDemoteSubtreeNormal', u':silent! py ORGMODE.plugins[u"EditStructure"].demote_heading()<CR>')))
		self.menu + ActionEntry(u'&Demote Subtree', self.keybindings[-1])
		self.keybindings.append(Keybinding(u'>]]', u'<Plug>OrgDemoteSubtreeNormal', mode=MODE_NORMAL))
		self.keybindings.append(Keybinding(u'>ir', u'<Plug>OrgDemoteSubtreeNormal', mode=MODE_NORMAL))

		# other keybindings
		self.keybindings.append(Keybinding(u'<C-d>', Plug(u'OrgPromoteOnHeadingInsert', u'<C-o>:silent! py ORGMODE.plugins[u"EditStructure"].promote_heading(including_children=False, on_heading=True, insert_mode=True)<CR>', mode=MODE_INSERT)))
		self.keybindings.append(Keybinding(u'<C-t>', Plug(u'OrgDemoteOnHeadingInsert', u'<C-o>:silent! py ORGMODE.plugins[u"EditStructure"].demote_heading(including_children=False, on_heading=True, insert_mode=True)<CR>', mode=MODE_INSERT)))

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = Export
# -*- coding: utf-8 -*-

import os
import subprocess

import vim

from orgmode._vim import ORGMODE, echoe, echom
from orgmode.menu import Submenu, ActionEntry, add_cmd_mapping_menu
from orgmode.keybinding import Keybinding, Plug, Command
from orgmode import settings


class Export(object):
	u"""
	Export a orgmode file using emacs orgmode.

	This is a *very simple* wrapper of the emacs/orgmode export.  emacs and
	orgmode need to be installed. We simply call emacs with some options to
	export the .org.

	TODO: Offer export options in vim. Don't use the menu.
	TODO: Maybe use a native implementation.
	"""

	def __init__(self):
		u""" Initialize plugin """
		object.__init__(self)
		# menu entries this plugin should create
		self.menu = ORGMODE.orgmenu + Submenu(u'Export')

		# key bindings for this plugin
		# key bindings are also registered through the menu so only additional
		# bindings should be put in this variable
		self.keybindings = []

		# commands for this plugin
		self.commands = []

	@classmethod
	def _get_init_script(cls):
		init_script = settings.get(u'org_export_init_script', u'')
		if init_script:
			init_script = os.path.expandvars(os.path.expanduser(init_script))
			if os.path.exists(init_script):
				return init_script
			else:
				echoe(u'Unable to find init script %s' % init_script)

	@classmethod
	def _export(cls, format_):
		"""Export current file to format_.

		:format_:  pdf or html
		:returns:  return code
		"""
		emacsbin = os.path.expandvars(os.path.expanduser(
			settings.get(u'org_export_emacs', u'/usr/bin/emacs')))
		if not os.path.exists(emacsbin):
			echoe(u'Unable to find emacs binary %s' % emacsbin)

		# build the export command
		cmd = [
			emacsbin,
			u'-nw',
			u'--batch',
			u'--visit=%s' % vim.eval(u'expand("%:p")'),
			u'--funcall=org-export-as-%s' % format_
		]
		# source init script as well
		init_script = cls._get_init_script()
		if init_script:
			cmd.extend(['--script', init_script])

		# export
		p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		p.wait()

		if p.returncode != 0 or settings.get(u'org_export_verbose') == 1:
			echom('\n'.join(p.communicate()))
		return p.returncode

	@classmethod
	def topdf(cls):
		u"""Export the current buffer as pdf using emacs orgmode."""
		ret = cls._export(u'pdf')
		if ret != 0:
			echoe(u'PDF export failed.')
		else:
			echom(u'Export successful: %s.%s' % (vim.eval(u'expand("%:r")'), 'pdf'))

	@classmethod
	def tohtml(cls):
		u"""Export the current buffer as html using emacs orgmode."""
		ret = cls._export(u'html')
		if ret != 0:
			echoe(u'HTML export failed.')
		else:
			echom(u'Export successful: %s.%s' % (vim.eval(u'expand("%:r")'), 'html'))

	@classmethod
	def tolatex(cls):
		u"""Export the current buffer as latex using emacs orgmode."""
		ret = cls._export(u'latex')
		if ret != 0:
			echoe(u'latex export failed.')
		else:
			echom(u'Export successful: %s.%s' % (vim.eval(u'expand("%:r")'), 'tex'))

	def register(self):
		u"""Registration and keybindings."""

		# path to emacs executable
		settings.set(u'org_export_emacs', u'/usr/bin/emacs')
		# verbose output for export
		settings.set(u'org_export_verbose', 0)
		# allow the user to define an initialization script
		settings.set(u'org_export_init_script', u'')

		# to PDF
		add_cmd_mapping_menu(
			self,
			name=u'OrgExportToPDF',
			function=u':py ORGMODE.plugins[u"Export"].topdf()<CR>',
			key_mapping=u'<localleader>ep',
			menu_desrc=u'To PDF (via Emacs)'
		)
		# to latex
		add_cmd_mapping_menu(
			self,
			name=u'OrgExportToLaTeX',
			function=u':py ORGMODE.plugins[u"Export"].tolatex()<CR>',
			key_mapping=u'<localleader>el',
			menu_desrc=u'To LaTeX (via Emacs)'
		)
		# to HTML
		add_cmd_mapping_menu(
			self,
			name=u'OrgExportToHTML',
			function=u':py ORGMODE.plugins[u"Export"].tohtml()<CR>',
			key_mapping=u'<localleader>eh',
			menu_desrc=u'To HTML (via Emacs)'
		)

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = Hyperlinks
# -*- coding: utf-8 -*-

import re

import vim

from orgmode._vim import echom, ORGMODE, realign_tags
from orgmode.menu import Submenu, Separator, ActionEntry
from orgmode.keybinding import Keybinding, Plug, Command


class Hyperlinks(object):
	u""" Hyperlinks plugin """

	def __init__(self):
		u""" Initialize plugin """
		object.__init__(self)
		# menu entries this plugin should create
		self.menu = ORGMODE.orgmenu + Submenu(u'Hyperlinks')

		# key bindings for this plugin
		# key bindings are also registered through the menu so only additional
		# bindings should be put in this variable
		self.keybindings = []

		# commands for this plugin
		self.commands = []

	uri_match = re.compile(
		r'^\[{2}(?P<uri>[^][]*)(\]\[(?P<description>[^][]*))?\]{2}')

	@classmethod
	def _get_link(cls, cursor=None):
		u"""
		Get the link the cursor is on and return it's URI and description

		:cursor: None or (Line, Column)
		:returns: None if no link was found, otherwise {uri:URI,
				description:DESCRIPTION, line:LINE, start:START, end:END}
				or uri and description could be None if not set
		"""
		cursor = cursor if cursor else vim.current.window.cursor
		line = vim.current.buffer[cursor[0] - 1].decode(u'utf-8')

		# if the cursor is on the last bracket, it's not recognized as a hyperlink
		start = line.rfind(u'[[', 0, cursor[1])
		if start == -1:
			start = line.rfind(u'[[', 0, cursor[1] + 2)
		end = line.find(u']]', cursor[1])
		if end == -1:
			end = line.find(u']]', cursor[1] - 1)

		# extract link
		if start != -1 and end != -1:
			end += 2
			match = Hyperlinks.uri_match.match(line[start:end])

			res = {
				u'line': line,
				u'start': start,
				u'end': end,
				u'uri': None,
				u'description': None}
			if match:
				res.update(match.groupdict())
			return res

	@classmethod
	def follow(cls, action=u'openLink', visual=u''):
		u""" Follow hyperlink. If called on a regular string UTL determines the
		outcome. Normally a file with that name will be opened.

		:action: "copy" if the link should be copied to clipboard, otherwise
				the link will be opened
		:visual: "visual" if Universal Text Linking should be triggered in
				visual mode

		:returns: URI or None
		"""
		if not int(vim.eval(u'exists(":Utl")')):
			echom(u'Universal Text Linking plugin not installed, unable to proceed.')
			return

		action = u'copyLink' \
			if (action and action.startswith(u'copy')) \
			else u'openLink'
		visual = u'visual' if visual and visual.startswith(u'visual') else u''

		link = Hyperlinks._get_link()

		if link and link[u'uri'] is not None:
			# call UTL with the URI
			vim.command((
				u'Utl %s %s %s' % (action, visual, link[u'uri'])).encode(u'utf-8'))
			return link[u'uri']
		else:
			# call UTL and let it decide what to do
			vim.command((u'Utl %s %s' % (action, visual)).encode(u'utf-8'))

	@classmethod
	@realign_tags
	def insert(cls, uri=None, description=None):
		u""" Inserts a hyperlink. If no arguments are provided, an interactive
		query will be started.

		:uri: The URI that will be opened
		:description: An optional description that will be displayed instead of
				the URI

		:returns: (URI, description)
		"""
		link = Hyperlinks._get_link()
		if link:
			if uri is None and link[u'uri'] is not None:
				uri = link[u'uri']
			if description is None and link[u'description'] is not None:
				description = link[u'description']

		if uri is None:
			uri = vim.eval(u'input("Link: ", "", "file")')
		elif link:
			uri = vim.eval(u'input("Link: ", "%s", "file")' % link[u'uri'])
		if uri is None:
			return
		else:
			uri = uri.decode(u'utf-8')

		if description is None:
			description = vim.eval(u'input("Description: ")').decode(u'utf-8')
		elif link:
			description = vim.eval(
				u'input("Description: ", "%s")' %
				link[u'description']).decode(u'utf-8')
		if description is None:
			return

		cursor = vim.current.window.cursor
		cl = vim.current.buffer[cursor[0] - 1].decode(u'utf-8')
		head = cl[:cursor[1] + 1] if not link else cl[:link[u'start']]
		tail = cl[cursor[1] + 1:] if not link else cl[link[u'end']:]

		separator = u''
		if description:
			separator = u']['

		if uri or description:
			vim.current.buffer[cursor[0] - 1] = \
				(u''.join((head, u'[[%s%s%s]]' %
					(uri, separator, description), tail))).encode(u'utf-8')
		elif link:
			vim.current.buffer[cursor[0] - 1] = \
				(u''.join((head, tail))).encode(u'utf-8')

	def register(self):
		u"""
		Registration of plugin. Key bindings and other initialization should be done.
		"""
		cmd = Command(
			u'OrgHyperlinkFollow',
			u':py ORGMODE.plugins[u"Hyperlinks"].follow()')
		self.commands.append(cmd)
		self.keybindings.append(
			Keybinding(u'gl', Plug(u'OrgHyperlinkFollow', self.commands[-1])))
		self.menu + ActionEntry(u'&Follow Link', self.keybindings[-1])

		cmd = Command(
			u'OrgHyperlinkCopy',
			u':py ORGMODE.plugins[u"Hyperlinks"].follow(action=u"copy")')
		self.commands.append(cmd)
		self.keybindings.append(
			Keybinding(u'gyl', Plug(u'OrgHyperlinkCopy', self.commands[-1])))
		self.menu + ActionEntry(u'&Copy Link', self.keybindings[-1])

		cmd = Command(
			u'OrgHyperlinkInsert',
			u':py ORGMODE.plugins[u"Hyperlinks"].insert(<f-args>)',
			arguments=u'*')
		self.commands.append(cmd)
		self.keybindings.append(
			Keybinding(u'gil', Plug(u'OrgHyperlinkInsert', self.commands[-1])))
		self.menu + ActionEntry(u'&Insert Link', self.keybindings[-1])

		self.menu + Separator()

		# find next link
		cmd = Command(
			u'OrgHyperlinkNextLink',
			u":if search('\[\{2}\zs[^][]*\(\]\[[^][]*\)\?\ze\]\{2}', 's') == 0 | echo 'No further link found.' | endif")
		self.commands.append(cmd)
		self.keybindings.append(
			Keybinding(u'gn', Plug(u'OrgHyperlinkNextLink', self.commands[-1])))
		self.menu + ActionEntry(u'&Next Link', self.keybindings[-1])

		# find previous link
		cmd = Command(
			u'OrgHyperlinkPreviousLink',
			u":if search('\[\{2}\zs[^][]*\(\]\[[^][]*\)\?\ze\]\{2}', 'bs') == 0 | echo 'No further link found.' | endif")
		self.commands.append(cmd)
		self.keybindings.append(
			Keybinding(u'go', Plug(u'OrgHyperlinkPreviousLink', self.commands[-1])))
		self.menu + ActionEntry(u'&Previous Link', self.keybindings[-1])

		self.menu + Separator()

		# Descriptive Links
		cmd = Command(u'OrgHyperlinkDescriptiveLinks', u':setlocal cole=2')
		self.commands.append(cmd)
		self.menu + ActionEntry(u'&Descriptive Links', self.commands[-1])

		# Literal Links
		cmd = Command(u'OrgHyperlinkLiteralLinks', u':setlocal cole=0')
		self.commands.append(cmd)
		self.menu + ActionEntry(u'&Literal Links', self.commands[-1])

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = LoggingWork
# -*- coding: utf-8 -*-

import vim

from orgmode._vim import echo, echom, echoe, ORGMODE, apply_count, repeat
from orgmode.menu import Submenu, Separator, ActionEntry
from orgmode.keybinding import Keybinding, Plug, Command


class LoggingWork(object):
	u""" LoggingWork plugin """

	def __init__(self):
		u""" Initialize plugin """
		object.__init__(self)
		# menu entries this plugin should create
		self.menu = ORGMODE.orgmenu + Submenu(u'&Logging work')

		# key bindings for this plugin
		# key bindings are also registered through the menu so only additional
		# bindings should be put in this variable
		self.keybindings = []

		# commands for this plugin
		self.commands = []

	@classmethod
	def action(cls):
		u""" Some kind of action

		:returns: TODO
		"""
		pass

	def register(self):
		u"""
		Registration of plugin. Key bindings and other initialization should be done.
		"""
		# an Action menu entry which binds "keybinding" to action ":action"
		self.commands.append(Command(u'OrgLoggingRecordDoneTime', u':py ORGMODE.plugins[u"LoggingWork"].action()'))
		self.menu + ActionEntry(u'&Record DONE time', self.commands[-1])

########NEW FILE########
__FILENAME__ = Misc
# -*- coding: utf-8 -*-

import vim

from orgmode._vim import ORGMODE, apply_count
from orgmode.menu import Submenu
from orgmode.keybinding import Keybinding, Plug, MODE_VISUAL, MODE_OPERATOR


class Misc(object):
	u""" Miscellaneous functionality """

	def __init__(self):
		u""" Initialize plugin """
		object.__init__(self)
		# menu entries this plugin should create
		self.menu = ORGMODE.orgmenu + Submenu(u'Misc')

		# key bindings for this plugin
		# key bindings are also registered through the menu so only additional
		# bindings should be put in this variable
		self.keybindings = []

	@classmethod
	def jump_to_first_character(cls):
		heading = ORGMODE.get_document().current_heading()
		if not heading:
			vim.eval(u'feedkeys("^", "n")'.encode(u'utf-8'))
			return

		vim.current.window.cursor = (vim.current.window.cursor[0], heading.level + 1)

	@classmethod
	def edit_at_first_character(cls):
		heading = ORGMODE.get_document().current_heading()
		if not heading or heading.start_vim != vim.current.window.cursor[0]:
			vim.eval(u'feedkeys("I", "n")'.encode(u'utf-8'))
			return

		vim.current.window.cursor = (vim.current.window.cursor[0], heading.level + 1)
		vim.command(u'startinsert'.encode(u'utf-8'))

	# @repeat
	@classmethod
	@apply_count
	def i_heading(cls, mode=u'visual', selection=u'inner', skip_children=False):
		u"""
		inner heading text object
		"""
		heading = ORGMODE.get_document().current_heading()
		if heading:
			if selection != u'inner':
				heading = heading if not heading.parent else heading.parent

			line_start, col_start = [int(i) for i in vim.eval(u'getpos("\'<")'.encode(u'utf-8'))[1:3]]
			line_end, col_end = [int(i) for i in vim.eval(u'getpos("\'>")'.encode(u'utf-8'))[1:3]]

			if mode != u'visual':
				line_start = vim.current.window.cursor[0]
				line_end = line_start

			start = line_start
			end = line_end
			move_one_character_back = u'' if mode == u'visual' else u'h'

			if heading.start_vim < line_start:
				start = heading.start_vim
			if heading.end_vim > line_end and not skip_children:
				end = heading.end_vim
			elif heading.end_of_last_child_vim > line_end and skip_children:
				end = heading.end_of_last_child_vim

			if mode != u'visual' and not vim.current.buffer[end - 1]:
				end -= 1
				move_one_character_back = u''

			swap_cursor = u'o' if vim.current.window.cursor[0] == line_start else u''

			if selection == u'inner' and vim.current.window.cursor[0] != line_start:
				h = ORGMODE.get_document().current_heading()
				if h:
					heading = h

			visualmode = vim.eval(u'visualmode()').decode(u'utf-8') if mode == u'visual' else u'v'

			if line_start == start and line_start != heading.start_vim:
				if col_start in (0, 1):
					vim.command(
						(u'normal! %dgg0%s%dgg$%s%s' %
							(start, visualmode, end, move_one_character_back, swap_cursor)).encode(u'utf-8'))
				else:
					vim.command(
						(u'normal! %dgg0%dl%s%dgg$%s%s' %
							(start, col_start - 1, visualmode, end, move_one_character_back, swap_cursor)).encode(u'utf-8'))
			else:
				vim.command(
					(u'normal! %dgg0%dl%s%dgg$%s%s' %
						(start, heading.level + 1, visualmode, end, move_one_character_back, swap_cursor)).encode(u'utf-8'))

			if selection == u'inner':
				if mode == u'visual':
					return u'OrgInnerHeadingVisual' if not skip_children else u'OrgInnerTreeVisual'
				else:
					return u'OrgInnerHeadingOperator' if not skip_children else u'OrgInnerTreeOperator'
			else:
				if mode == u'visual':
					return u'OrgOuterHeadingVisual' if not skip_children else u'OrgOuterTreeVisual'
				else:
					return u'OrgOuterHeadingOperator' if not skip_children else u'OrgOuterTreeOperator'
		elif mode == u'visual':
			vim.command(u'normal! gv'.encode(u'utf-8'))

	# @repeat
	@classmethod
	@apply_count
	def a_heading(cls, selection=u'inner', skip_children=False):
		u"""
		a heading text object
		"""
		heading = ORGMODE.get_document().current_heading()
		if heading:
			if selection != u'inner':
				heading = heading if not heading.parent else heading.parent

			line_start, col_start = [int(i) for i in vim.eval(u'getpos("\'<")'.encode(u'utf-8'))[1:3]]
			line_end, col_end = [int(i) for i in vim.eval(u'getpos("\'>")'.encode(u'utf-8'))[1:3]]

			start = line_start
			end = line_end

			if heading.start_vim < line_start:
				start = heading.start_vim
			if heading.end_vim > line_end and not skip_children:
				end = heading.end_vim
			elif heading.end_of_last_child_vim > line_end and skip_children:
				end = heading.end_of_last_child_vim

			swap_cursor = u'o' if vim.current.window.cursor[0] == line_start else u''

			vim.command(
				(u'normal! %dgg%s%dgg$%s' %
					(start, vim.eval(u'visualmode()'.encode(u'utf-8')), end, swap_cursor)).encode(u'utf-8'))
			if selection == u'inner':
				return u'OrgAInnerHeadingVisual' if not skip_children else u'OrgAInnerTreeVisual'
			else:
				return u'OrgAOuterHeadingVisual' if not skip_children else u'OrgAOuterTreeVisual'
		else:
			vim.command(u'normal! gv'.encode(u'utf-8'))

	def register(self):
		u"""
		Registration of plugin. Key bindings and other initialization should be done.
		"""
		self.keybindings.append(Keybinding(u'^', Plug(u'OrgJumpToFirstCharacter', u':py ORGMODE.plugins[u"Misc"].jump_to_first_character()<CR>')))
		self.keybindings.append(Keybinding(u'I', Plug(u'OrgEditAtFirstCharacter', u':py ORGMODE.plugins[u"Misc"].edit_at_first_character()<CR>')))

		self.keybindings.append(Keybinding(u'ih', Plug(u'OrgInnerHeadingVisual', u':<C-u>py ORGMODE.plugins[u"Misc"].i_heading()<CR>', mode=MODE_VISUAL)))
		self.keybindings.append(Keybinding(u'ah', Plug(u'OrgAInnerHeadingVisual', u':<C-u>py ORGMODE.plugins[u"Misc"].a_heading()<CR>', mode=MODE_VISUAL)))
		self.keybindings.append(Keybinding(u'Oh', Plug(u'OrgOuterHeadingVisual', u':<C-u>py ORGMODE.plugins[u"Misc"].i_heading(selection=u"outer")<CR>', mode=MODE_VISUAL)))
		self.keybindings.append(Keybinding(u'OH', Plug(u'OrgAOuterHeadingVisual', u':<C-u>py ORGMODE.plugins[u"Misc"].a_heading(selection=u"outer")<CR>', mode=MODE_VISUAL)))

		self.keybindings.append(Keybinding(u'ih', Plug(u'OrgInnerHeadingOperator', u':<C-u>py ORGMODE.plugins[u"Misc"].i_heading(mode=u"operator")<CR>', mode=MODE_OPERATOR)))
		self.keybindings.append(Keybinding(u'ah', u':normal Vah<CR>', mode=MODE_OPERATOR))
		self.keybindings.append(Keybinding(u'Oh', Plug(u'OrgOuterHeadingOperator', ':<C-u>py ORGMODE.plugins[u"Misc"].i_heading(mode=u"operator", selection=u"outer")<CR>', mode=MODE_OPERATOR)))
		self.keybindings.append(Keybinding(u'OH', u':normal VOH<CR>', mode=MODE_OPERATOR))

		self.keybindings.append(Keybinding(u'ir', Plug(u'OrgInnerTreeVisual', u':<C-u>py ORGMODE.plugins[u"Misc"].i_heading(skip_children=True)<CR>', mode=MODE_VISUAL)))
		self.keybindings.append(Keybinding(u'ar', Plug(u'OrgAInnerTreeVisual', u':<C-u>py ORGMODE.plugins[u"Misc"].a_heading(skip_children=True)<CR>', mode=MODE_VISUAL)))
		self.keybindings.append(Keybinding(u'Or', Plug(u'OrgOuterTreeVisual', u'<:<C-u>py ORGMODE.plugins[u"Misc"].i_heading(selection=u"outer", skip_children=True)<CR>', mode=MODE_VISUAL)))
		self.keybindings.append(Keybinding(u'OR', Plug(u'OrgAOuterTreeVisual', u':<C-u>py ORGMODE.plugins[u"Misc"].a_heading(selection=u"outer", skip_children=True)<CR>', mode=MODE_VISUAL)))

		self.keybindings.append(Keybinding(u'ir', Plug(u'OrgInnerTreeOperator', u':<C-u>py ORGMODE.plugins[u"Misc"].i_heading(mode=u"operator")<CR>', mode=MODE_OPERATOR)))
		self.keybindings.append(Keybinding(u'ar', u':normal Var<CR>', mode=MODE_OPERATOR))
		self.keybindings.append(Keybinding(u'Or', Plug(u'OrgOuterTreeOperator', u':<C-u>py ORGMODE.plugins[u"Misc"].i_heading(mode=u"operator", selection=u"outer", skip_children=True)<CR>', mode=MODE_OPERATOR)))
		self.keybindings.append(Keybinding(u'OR', u':normal VOR<CR>', mode=MODE_OPERATOR))

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = Navigator
# -*- coding: utf-8 -*-

import vim

from orgmode._vim import echo, ORGMODE, apply_count
from orgmode.menu import Submenu, ActionEntry
from orgmode.keybinding import Keybinding, MODE_VISUAL, MODE_OPERATOR, Plug
from orgmode.liborgmode.documents import Direction


class Navigator(object):
	u""" Implement navigation in org-mode documents """

	def __init__(self):
		object.__init__(self)
		self.menu = ORGMODE.orgmenu + Submenu(u'&Navigate Headings')
		self.keybindings = []

	@classmethod
	@apply_count
	def parent(cls, mode):
		u"""
		Focus parent heading

		:returns: parent heading or None
		"""
		heading = ORGMODE.get_document().current_heading()
		if not heading:
			if mode == u'visual':
				vim.command(u'normal! gv'.encode(u'utf-8'))
			else:
				echo(u'No heading found')
			return

		if not heading.parent:
			if mode == u'visual':
				vim.command(u'normal! gv'.encode(u'utf-8'))
			else:
				echo(u'No parent heading found')
			return

		p = heading.parent

		if mode == u'visual':
			cls._change_visual_selection(heading, p, direction=Direction.BACKWARD, parent=True)
		else:
			vim.current.window.cursor = (p.start_vim, p.level + 1)
		return p

	@classmethod
	@apply_count
	def parent_next_sibling(cls, mode):
		u"""
		Focus the parent's next sibling

		:returns: parent's next sibling heading or None
		"""
		heading = ORGMODE.get_document().current_heading()
		if not heading:
			if mode == u'visual':
				vim.command(u'normal! gv'.encode(u'utf-8'))
			else:
				echo(u'No heading found')
			return

		if not heading.parent or not heading.parent.next_sibling:
			if mode == u'visual':
				vim.command(u'normal! gv'.encode(u'utf-8'))
			else:
				echo(u'No parent heading found')
			return

		ns = heading.parent.next_sibling

		if mode == u'visual':
			cls._change_visual_selection(heading, ns, direction=Direction.FORWARD, parent=False)
		elif mode == u'operator':
			vim.current.window.cursor = (ns.start_vim, 0)
		else:
			vim.current.window.cursor = (ns.start_vim, ns.level + 1)
		return ns

	@classmethod
	def _change_visual_selection(cls, current_heading, heading, direction=Direction.FORWARD, noheadingfound=False, parent=False):
		current = vim.current.window.cursor[0]
		line_start, col_start = [int(i) for i in vim.eval(u'getpos("\'<")'.encode(u'utf-8'))[1:3]]
		line_end, col_end = [int(i) for i in vim.eval(u'getpos("\'>")'.encode(u'utf-8'))[1:3]]

		f_start = heading.start_vim
		f_end = heading.end_vim
		swap_cursor = True

		# << |visual start
		# selection end >>
		if current == line_start:
			if (direction == Direction.FORWARD and line_end < f_start) or noheadingfound and not direction == Direction.BACKWARD:
				swap_cursor = False

			# focus heading HERE
			# << |visual start
			# selection end >>

			# << |visual start
			# focus heading HERE
			# selection end >>
			if f_start < line_start and direction == Direction.BACKWARD:
				if current_heading.start_vim < line_start and not parent:
					line_start = current_heading.start_vim
				else:
					line_start = f_start

			elif (f_start < line_start or f_start < line_end) and not noheadingfound:
				line_start = f_start

			# << |visual start
			# selection end >>
			# focus heading HERE
			else:
				if direction == Direction.FORWARD:
					if line_end < f_start and not line_start == f_start - 1 and current_heading:
						# focus end of previous heading instead of beginning of next heading
						line_start = line_end
						line_end = f_start - 1
					else:
						# focus end of next heading
						line_start = line_end
						line_end = f_end
				elif direction == Direction.BACKWARD:
					if line_end < f_end:
						pass
				else:
					line_start = line_end
					line_end = f_end

		# << visual start
		# selection end| >>
		else:
			# focus heading HERE
			# << visual start
			# selection end| >>
			if line_start > f_start and line_end > f_end and not parent:
				line_end = f_end
				swap_cursor = False

			elif (line_start > f_start or line_start == f_start) and \
				line_end <= f_end and direction == Direction.BACKWARD:
				line_end = line_start
				line_start = f_start

			# << visual start
			# selection end and focus heading end HERE| >>

			# << visual start
			# focus heading HERE
			# selection end| >>

			# << visual start
			# selection end| >>
			# focus heading HERE
			else:
				if direction == Direction.FORWARD:
					if line_end < f_start - 1:
						# focus end of previous heading instead of beginning of next heading
						line_end = f_start - 1
					else:
						# focus end of next heading
						line_end = f_end
				else:
					line_end = f_end
				swap_cursor = False

		move_col_start = u'%dl' % (col_start - 1) if (col_start - 1) > 0 and (col_start - 1) < 2000000000 else u''
		move_col_end = u'%dl' % (col_end - 1) if (col_end - 1) > 0 and (col_end - 1) < 2000000000 else u''
		swap = u'o' if swap_cursor else u''

		vim.command((
			u'normal! %dgg%s%s%dgg%s%s' %
			(line_start, move_col_start, vim.eval(u'visualmode()'.encode(u'utf-8')), line_end, move_col_end, swap)).encode(u'utf-8'))

	@classmethod
	def _focus_heading(cls, mode, direction=Direction.FORWARD, skip_children=False):
		u"""
		Focus next or previous heading in the given direction

		:direction: True for next heading, False for previous heading
		:returns: next heading or None
		"""
		d = ORGMODE.get_document()
		current_heading = d.current_heading()
		heading = current_heading
		focus_heading = None
		# FIXME this is just a piece of really ugly and unmaintainable code. It
		# should be rewritten
		if not heading:
			if direction == Direction.FORWARD and d.headings \
				and vim.current.window.cursor[0] < d.headings[0].start_vim:
				# the cursor is in the meta information are, therefore focus
				# first heading
				focus_heading = d.headings[0]
			if not (heading or focus_heading):
				if mode == u'visual':
					# restore visual selection when no heading was found
					vim.command(u'normal! gv'.encode(u'utf-8'))
				else:
					echo(u'No heading found')
				return
		elif direction == Direction.BACKWARD:
			if vim.current.window.cursor[0] != heading.start_vim:
				# the cursor is in the body of the current heading, therefore
				# the current heading will be focused
				if mode == u'visual':
					line_start, col_start = [int(i) for i in vim.eval(u'getpos("\'<")'.encode(u'utf-8'))[1:3]]
					line_end, col_end = [int(i) for i in vim.eval(u'getpos("\'>")'.encode(u'utf-8'))[1:3]]
					if line_start >= heading.start_vim and line_end > heading.start_vim:
						focus_heading = heading
				else:
					focus_heading = heading

		# so far no heading has been found that the next focus should be on
		if not focus_heading:
			if not skip_children and direction == Direction.FORWARD and heading.children:
				focus_heading = heading.children[0]
			elif direction == Direction.FORWARD and heading.next_sibling:
				focus_heading = heading.next_sibling
			elif direction == Direction.BACKWARD and heading.previous_sibling:
				focus_heading = heading.previous_sibling
				if not skip_children:
					while focus_heading.children:
						focus_heading = focus_heading.children[-1]
			else:
				if direction == Direction.FORWARD:
					focus_heading = current_heading.next_heading
				else:
					focus_heading = current_heading.previous_heading

		noheadingfound = False
		if not focus_heading:
			if mode in (u'visual', u'operator'):
				# the cursor seems to be on the last or first heading of this
				# document and performes another next/previous operation
				focus_heading = heading
				noheadingfound = True
			else:
				if direction == Direction.FORWARD:
					echo(u'Already focussing last heading')
				else:
					echo(u'Already focussing first heading')
				return

		if mode == u'visual':
			cls._change_visual_selection(current_heading, focus_heading, direction=direction, noheadingfound=noheadingfound)
		elif mode == u'operator':
			if direction == Direction.FORWARD and vim.current.window.cursor[0] >= focus_heading.start_vim:
				vim.current.window.cursor = (focus_heading.end_vim, len(vim.current.buffer[focus_heading.end].decode(u'utf-8')))
			else:
				vim.current.window.cursor = (focus_heading.start_vim, 0)
		else:
			vim.current.window.cursor = (focus_heading.start_vim, focus_heading.level + 1)
		if noheadingfound:
			return
		return focus_heading

	@classmethod
	@apply_count
	def previous(cls, mode, skip_children=False):
		u"""
		Focus previous heading
		"""
		return cls._focus_heading(mode, direction=Direction.BACKWARD, skip_children=skip_children)

	@classmethod
	@apply_count
	def next(cls, mode, skip_children=False):
		u"""
		Focus next heading
		"""
		return cls._focus_heading(mode, direction=Direction.FORWARD, skip_children=skip_children)

	def register(self):
		# normal mode
		self.keybindings.append(Keybinding(u'g{', Plug('OrgJumpToParentNormal', u':py ORGMODE.plugins[u"Navigator"].parent(mode=u"normal")<CR>')))
		self.menu + ActionEntry(u'&Up', self.keybindings[-1])
		self.keybindings.append(Keybinding(u'g}', Plug('OrgJumpToParentsSiblingNormal', u':py ORGMODE.plugins[u"Navigator"].parent_next_sibling(mode=u"normal")<CR>')))
		self.menu + ActionEntry(u'&Down', self.keybindings[-1])
		self.keybindings.append(Keybinding(u'{', Plug(u'OrgJumpToPreviousNormal', u':py ORGMODE.plugins[u"Navigator"].previous(mode=u"normal")<CR>')))
		self.menu + ActionEntry(u'&Previous', self.keybindings[-1])
		self.keybindings.append(Keybinding(u'}', Plug(u'OrgJumpToNextNormal', u':py ORGMODE.plugins[u"Navigator"].next(mode=u"normal")<CR>')))
		self.menu + ActionEntry(u'&Next', self.keybindings[-1])

		# visual mode
		self.keybindings.append(Keybinding(u'g{', Plug(u'OrgJumpToParentVisual', u'<Esc>:<C-u>py ORGMODE.plugins[u"Navigator"].parent(mode=u"visual")<CR>', mode=MODE_VISUAL)))
		self.keybindings.append(Keybinding(u'g}', Plug('OrgJumpToParentsSiblingVisual', u'<Esc>:<C-u>py ORGMODE.plugins[u"Navigator"].parent_next_sibling(mode=u"visual")<CR>', mode=MODE_VISUAL)))
		self.keybindings.append(Keybinding(u'{', Plug(u'OrgJumpToPreviousVisual', u'<Esc>:<C-u>py ORGMODE.plugins[u"Navigator"].previous(mode=u"visual")<CR>', mode=MODE_VISUAL)))
		self.keybindings.append(Keybinding(u'}', Plug(u'OrgJumpToNextVisual', u'<Esc>:<C-u>py ORGMODE.plugins[u"Navigator"].next(mode=u"visual")<CR>', mode=MODE_VISUAL)))

		# operator-pending mode
		self.keybindings.append(Keybinding(u'g{', Plug(u'OrgJumpToParentOperator', u':<C-u>py ORGMODE.plugins[u"Navigator"].parent(mode=u"operator")<CR>', mode=MODE_OPERATOR)))
		self.keybindings.append(Keybinding(u'g}', Plug('OrgJumpToParentsSiblingOperator', u':<C-u>py ORGMODE.plugins[u"Navigator"].parent_next_sibling(mode=u"operator")<CR>', mode=MODE_OPERATOR)))
		self.keybindings.append(Keybinding(u'{', Plug(u'OrgJumpToPreviousOperator', u':<C-u>py ORGMODE.plugins[u"Navigator"].previous(mode=u"operator")<CR>', mode=MODE_OPERATOR)))
		self.keybindings.append(Keybinding(u'}', Plug(u'OrgJumpToNextOperator', u':<C-u>py ORGMODE.plugins[u"Navigator"].next(mode=u"operator")<CR>', mode=MODE_OPERATOR)))

		# section wise movement (skip children)
		# normal mode
		self.keybindings.append(Keybinding(u'[[', Plug(u'OrgJumpToPreviousSkipChildrenNormal', u':py ORGMODE.plugins[u"Navigator"].previous(mode=u"normal", skip_children=True)<CR>')))
		self.menu + ActionEntry(u'Ne&xt Same Level', self.keybindings[-1])
		self.keybindings.append(Keybinding(u']]', Plug(u'OrgJumpToNextSkipChildrenNormal', u':py ORGMODE.plugins[u"Navigator"].next(mode=u"normal", skip_children=True)<CR>')))
		self.menu + ActionEntry(u'Pre&vious Same Level', self.keybindings[-1])

		# visual mode
		self.keybindings.append(Keybinding(u'[[', Plug(u'OrgJumpToPreviousSkipChildrenVisual', u'<Esc>:<C-u>py ORGMODE.plugins[u"Navigator"].previous(mode=u"visual", skip_children=True)<CR>', mode=MODE_VISUAL)))
		self.keybindings.append(Keybinding(u']]', Plug(u'OrgJumpToNextSkipChildrenVisual', u'<Esc>:<C-u>py ORGMODE.plugins[u"Navigator"].next(mode=u"visual", skip_children=True)<CR>', mode=MODE_VISUAL)))

		# operator-pending mode
		self.keybindings.append(Keybinding(u'[[', Plug(u'OrgJumpToPreviousSkipChildrenOperator', u':<C-u>py ORGMODE.plugins[u"Navigator"].previous(mode=u"operator", skip_children=True)<CR>', mode=MODE_OPERATOR)))
		self.keybindings.append(Keybinding(u']]', Plug(u'OrgJumpToNextSkipChildrenOperator', u':<C-u>py ORGMODE.plugins[u"Navigator"].next(mode=u"operator", skip_children=True)<CR>', mode=MODE_OPERATOR)))

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = ShowHide
# -*- coding: utf-8 -*-

import vim

from orgmode.liborgmode.headings import Heading
from orgmode._vim import ORGMODE, apply_count
from orgmode import settings
from orgmode.menu import Submenu, ActionEntry
from orgmode.keybinding import Keybinding, Plug, MODE_NORMAL


class ShowHide(object):
	u""" Show Hide plugin """

	def __init__(self):
		u""" Initialize plugin """
		object.__init__(self)
		# menu entries this plugin should create
		self.menu = ORGMODE.orgmenu + Submenu(u'&Show Hide')

		# key bindings for this plugin
		# key bindings are also registered through the menu so only additional
		# bindings should be put in this variable
		self.keybindings = []

	@classmethod
	def _fold_depth(cls, h):
		""" Find the deepest level of open folds

		:h:			Heading
		:returns:	Tuple (int - level of open folds, boolean - found fold) or None if h is not a Heading
		"""
		if not isinstance(h, Heading):
			return

		if int(vim.eval((u'foldclosed(%d)' % h.start_vim).encode(u'utf-8'))) != -1:
			return (h.number_of_parents, True)

		res = [h.number_of_parents + 1]
		found = False
		for c in h.children:
			d, f = cls._fold_depth(c)
			res.append(d)
			found |= f

		return (max(res), found)

	@classmethod
	@apply_count
	def toggle_folding(cls, reverse=False):
		u""" Toggle folding similar to the way orgmode does

		This is just a convenience function, don't hesitate to use the z*
		keybindings vim offers to deal with folding!

		:reverse:	If False open folding by one level otherwise close it by one.
		"""
		d = ORGMODE.get_document()
		heading = d.current_heading()
		if not heading:
			vim.eval(u'feedkeys("<Tab>", "n")'.encode(u'utf-8'))
			return

		cursor = vim.current.window.cursor[:]

		if int(vim.eval((u'foldclosed(%d)' % heading.start_vim).encode(u'utf-8'))) != -1:
			if not reverse:
				# open closed fold
				p = heading.number_of_parents
				if not p:
					p = heading.level
				vim.command((u'normal! %dzo' % p).encode(u'utf-8'))
			else:
				# reverse folding opens all folds under the cursor
				vim.command((u'%d,%dfoldopen!' % (heading.start_vim, heading.end_of_last_child_vim)).encode(u'utf-8'))
			vim.current.window.cursor = cursor
			return heading

		def open_fold(h):
			if h.number_of_parents <= open_depth:
				vim.command((u'normal! %dgg%dzo' % (h.start_vim, open_depth)).encode(u'utf-8'))
			for c in h.children:
				open_fold(c)

		def close_fold(h):
			for c in h.children:
				close_fold(c)
			if h.number_of_parents >= open_depth - 1 and \
				int(vim.eval((u'foldclosed(%d)' % h.start_vim).encode(u'utf-8'))) == -1:
				vim.command((u'normal! %dggzc' % (h.start_vim, )).encode(u'utf-8'))

		# find deepest fold
		open_depth, found_fold = cls._fold_depth(heading)

		if not reverse:
			# recursively open folds
			if found_fold:
				for child in heading.children:
					open_fold(child)
			else:
				vim.command((u'%d,%dfoldclose!' % (heading.start_vim, heading.end_of_last_child_vim)).encode(u'utf-8'))

				if heading.number_of_parents:
					# restore cursor position, it might have been changed by open_fold
					vim.current.window.cursor = cursor

					p = heading.number_of_parents
					if not p:
						p = heading.level
					# reopen fold again beacause the former closing of the fold closed all levels, including parents!
					vim.command((u'normal! %dzo' % (p, )).encode(u'utf-8'))
		else:
			# close the last level of folds
			close_fold(heading)

		# restore cursor position
		vim.current.window.cursor = cursor
		return heading

	@classmethod
	@apply_count
	def global_toggle_folding(cls, reverse=False):
		""" Toggle folding globally

		:reverse:	If False open folding by one level otherwise close it by one.
		"""
		d = ORGMODE.get_document()
		if reverse:
			foldlevel = int(vim.eval(u'&foldlevel'.encode(u'utf-8')))
			if foldlevel == 0:
				# open all folds because the user tries to close folds beyound 0
				vim.eval(u'feedkeys("zR", "n")'.encode(u'utf-8'))
			else:
				# vim can reduce the foldlevel on its own
				vim.eval(u'feedkeys("zm", "n")'.encode(u'utf-8'))
		else:
			found = False
			for h in d.headings:
				res = cls._fold_depth(h)
				if res:
					found = res[1]
				if found:
					break
			if not found:
				# no fold found and the user tries to advance the fold level
				# beyond maximum so close everything
				vim.eval(u'feedkeys("zM", "n")'.encode(u'utf-8'))
			else:
				# fold found, vim can increase the foldlevel on its own
				vim.eval(u'feedkeys("zr", "n")'.encode(u'utf-8'))

		return d

	def register(self):
		u"""
		Registration of plugin. Key bindings and other initialization should be done.
		"""
		# register plug

		self.keybindings.append(Keybinding(u'<Tab>', Plug(u'OrgToggleFoldingNormal', u':py ORGMODE.plugins[u"ShowHide"].toggle_folding()<CR>')))
		self.menu + ActionEntry(u'&Cycle Visibility', self.keybindings[-1])

		self.keybindings.append(Keybinding(u'<S-Tab>', Plug(u'OrgToggleFoldingReverse', u':py ORGMODE.plugins[u"ShowHide"].toggle_folding(reverse=True)<CR>')))
		self.menu + ActionEntry(u'Cycle Visibility &Reverse', self.keybindings[-1])

		self.keybindings.append(Keybinding(u'<localleader>.', Plug(u'OrgGlobalToggleFoldingNormal', u':py ORGMODE.plugins[u"ShowHide"].global_toggle_folding()<CR>')))
		self.menu + ActionEntry(u'Cycle Visibility &Globally', self.keybindings[-1])

		self.keybindings.append(Keybinding(u'<localleader>,', Plug(u'OrgGlobalToggleFoldingReverse', u':py ORGMODE.plugins[u"ShowHide"].global_toggle_folding(reverse=True)<CR>')))
		self.menu + ActionEntry(u'Cycle Visibility Reverse G&lobally', self.keybindings[-1])

		for i in xrange(0, 10):
			self.keybindings.append(Keybinding(u'<localleader>%d' % (i, ), u'zM:set fdl=%d<CR>' % i, mode=MODE_NORMAL))

########NEW FILE########
__FILENAME__ = TagsProperties
# -*- coding: utf-8 -*-

import vim

from orgmode._vim import ORGMODE, repeat
from orgmode.menu import Submenu, ActionEntry
from orgmode.keybinding import Keybinding, Plug, Command
from orgmode import settings


class TagsProperties(object):
	u""" TagsProperties plugin """

	def __init__(self):
		u""" Initialize plugin """
		object.__init__(self)
		# menu entries this plugin should create
		self.menu = ORGMODE.orgmenu + Submenu(u'&TAGS and Properties')

		# key bindings for this plugin
		# key bindings are also registered through the menu so only additional
		# bindings should be put in this variable
		self.keybindings = []

		# commands for this plugin
		self.commands = []

	@classmethod
	def complete_tags(cls):
		u""" build a list of tags and store it in variable b:org_tag_completion
		"""
		d = ORGMODE.get_document()
		heading = d.current_heading()
		if not heading:
			return

		leading_portion = vim.eval(u'a:ArgLead').decode(u'utf-8')
		cursor = int(vim.eval(u'a:CursorPos'))

		# extract currently completed tag
		idx_orig = leading_portion.rfind(u':', 0, cursor)
		if idx_orig == -1:
			idx = 0
		else:
			idx = idx_orig

		current_tag = leading_portion[idx: cursor].lstrip(u':')
		head = leading_portion[:idx + 1]
		if idx_orig == -1:
			head = u''
		tail = leading_portion[cursor:]

		# extract all tags of the current file
		all_tags = set()
		for h in d.all_headings():
			for t in h.tags:
				all_tags.add(t)

		ignorecase = bool(int(settings.get(u'org_tag_completion_ignorecase', int(vim.eval(u'&ignorecase')))))
		possible_tags = []
		current_tags = heading.tags
		for t in all_tags:
			if ignorecase:
				if t.lower().startswith(current_tag.lower()):
					possible_tags.append(t)
			elif t.startswith(current_tag):
				possible_tags.append(t)

		vim.command((u'let b:org_complete_tags = [%s]' % u', '.join([u'"%s%s:%s"' % (head, i, tail) for i in possible_tags])).encode(u'utf-8'))

	@classmethod
	@repeat
	def set_tags(cls):
		u""" Set tags for current heading
		"""
		d = ORGMODE.get_document()
		heading = d.current_heading()
		if not heading:
			return

		# retrieve tags
		res = None
		if heading.tags:
			res = vim.eval(u'input("Tags: ", ":%s:", "customlist,Org_complete_tags")' % u':'.join(heading.tags))
		else:
			res = vim.eval(u'input("Tags: ", "", "customlist,Org_complete_tags")')

		if res is None:
			# user pressed <Esc> abort any further processing
			return

		# remove empty tags
		heading.tags = filter(lambda x: x.strip() != u'', res.decode(u'utf-8').strip().strip(u':').split(u':'))

		d.write()

		return u'OrgSetTags'

	@classmethod
	def find_tags(cls):
		""" Find tags in current file
		"""
		tags = vim.eval(u'input("Find Tags: ", "", "customlist,Org_complete_tags")')
		if tags is None:
			# user pressed <Esc> abort any further processing
			return

		tags = filter(lambda x: x.strip() != u'', tags.decode(u'utf-8').strip().strip(u':').split(u':'))
		if tags:
			searchstring = u'\\('
			first = True
			for t1 in tags:
				if first:
					first = False
					searchstring += u'%s' % t1
				else:
					searchstring += u'\\|%s' % t1

				for t2 in tags:
					if t1 == t2:
						continue
					searchstring += u'\\(:[a-zA-Z:]*\\)\?:%s' % t2
			searchstring += u'\\)'

			vim.command(u'/\\zs:%s:\\ze' % searchstring)
		return u'OrgFindTags'

	@classmethod
	def realign_tags(cls):
		u"""
		Updates tags when user finished editing a heading
		"""
		d = ORGMODE.get_document(allow_dirty=True)
		heading = d.find_current_heading()
		if not heading:
			return

		if vim.current.window.cursor[0] == heading.start_vim:
			heading.set_dirty_heading()
			d.write_heading(heading, including_children=False)

	@classmethod
	def realign_all_tags(cls):
		u"""
		Updates tags when user finishes editing a heading
		"""
		d = ORGMODE.get_document()
		for heading in d.all_headings():
			heading.set_dirty_heading()

		d.write()

	def register(self):
		u"""
		Registration of plugin. Key bindings and other initialization should be done.
		"""
		# an Action menu entry which binds "keybinding" to action ":action"
		settings.set(u'org_tag_column', u'77')
		settings.set(u'org_tag_completion_ignorecase', int(vim.eval(u'&ignorecase')))

		cmd = Command(
			u'OrgSetTags',
			u':py ORGMODE.plugins[u"TagsProperties"].set_tags()')
		self.commands.append(cmd)
		keybinding = Keybinding(
			u'<localleader>st',
			Plug(u'OrgSetTags', cmd))
		self.keybindings.append(keybinding)
		self.menu + ActionEntry(u'Set &Tags', keybinding)

		cmd = Command(
			u'OrgFindTags',
			u':py ORGMODE.plugins[u"TagsProperties"].find_tags()')
		self.commands.append(cmd)
		keybinding = Keybinding(
			u'<localleader>ft',
			Plug(u'OrgFindTags', cmd))
		self.keybindings.append(keybinding)
		self.menu + ActionEntry(u'&Find Tags', keybinding)

		cmd = Command(
			u'OrgTagsRealign',
			u":py ORGMODE.plugins[u'TagsProperties'].realign_all_tags()")
		self.commands.append(cmd)

		# workaround to align tags when user is leaving insert mode
		vim.command(u"""function Org_complete_tags(ArgLead, CmdLine, CursorPos)
python << EOF
ORGMODE.plugins[u'TagsProperties'].complete_tags()
EOF
if exists('b:org_complete_tags')
	let tmp = b:org_complete_tags
	unlet b:org_complete_tags
	return tmp
else
	return []
endif
endfunction""".encode(u'utf-8'))

		# this is for all org files opened after this file
		vim.command(u"au orgmode FileType org :au orgmode InsertLeave <buffer> :py ORGMODE.plugins[u'TagsProperties'].realign_tags()".encode(u'utf-8'))

		# this is for the current file
		vim.command(u"au orgmode InsertLeave <buffer> :py ORGMODE.plugins[u'TagsProperties'].realign_tags()".encode(u'utf-8'))

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = Todo
# -*- coding: utf-8 -*-

import vim

from orgmode._vim import echom, ORGMODE, apply_count, repeat, realign_tags
from orgmode import settings
from orgmode.liborgmode.base import Direction
from orgmode.menu import Submenu, ActionEntry
from orgmode.keybinding import Keybinding, Plug

# temporary todo states for differnent orgmode buffers
ORGTODOSTATES = {}


def split_access_key(t):
	u"""
	:t:		todo state

	:return:	todo state and access key separated (TODO, ACCESS_KEY)
	"""
	if type(t) != unicode:
		return (None, None)

	idx = t.find(u'(')
	v, k = ((t[:idx], t[idx + 1:-1]) if t[idx + 1:-1] else (t, None)) if idx != -1 else (t, None)
	return (v, k)


class Todo(object):
	u"""
	Todo plugin.

	Description taken from orgmode.org:

	You can use TODO keywords to indicate different sequential states in the
	process of working on an item, for example:

	["TODO", "FEEDBACK", "VERIFY", "|", "DONE", "DELEGATED"]

	The vertical bar separates the TODO keywords (states that need action) from
	the DONE states (which need no further action). If you don't provide the
	separator bar, the last state is used as the DONE state. With this setup,
	the command ``,d`` will cycle an entry from TODO to FEEDBACK, then to
	VERIFY, and finally to DONE and DELEGATED.
	"""

	def __init__(self):
		u""" Initialize plugin """
		object.__init__(self)
		# menu entries this plugin should create
		self.menu = ORGMODE.orgmenu + Submenu(u'&TODO Lists')

		# key bindings for this plugin
		# key bindings are also registered through the menu so only additional
		# bindings should be put in this variable
		self.keybindings = []

	@classmethod
	def _get_next_state(
		cls, current_state, all_states,
		direction=Direction.FORWARD, interactive=False, next_set=False):
		u"""
		WTF is going on here!!!
		FIXME: reimplement this in a clean way :)

		:current_state:		the current todo state
		:all_states:		a list containing all todo states within sublists.
							The todo states may contain access keys
		:direction:			direction of state or keyword set change (forward/backward)
		:interactive:		if interactive and more than one todo sequence is
							specified, open a selection window
		:next_set:			advance to the next keyword set in defined direction

		:return:			return the next state as string, or NONE if the
							next state is no state.
		"""
		if not all_states:
			return

		def find_current_todo_state(c, a, stop=0):
			u"""
			:c:		current todo state
			:a:		list of todo states
			:stop:	internal parameter for parsing only two levels of lists

			:return:	first position of todo state in list in the form
						(IDX_TOPLEVEL, IDX_SECOND_LEVEL (0|1), IDX_OF_ITEM)
			"""
			for i in xrange(0, len(a)):
				if type(a[i]) in (tuple, list) and stop < 2:
					r = find_current_todo_state(c, a[i], stop=stop + 1)
					if r:
						r.insert(0, i)
						return r
				# ensure that only on the second level of sublists todo states
				# are found
				if type(a[i]) == unicode and stop == 2:
					_i = split_access_key(a[i])[0]
					if c == _i:
						return [i]

		ci = find_current_todo_state(current_state, all_states)

		if not ci:
			if next_set and direction == Direction.BACKWARD:
				echom(u'Already at the first keyword set')
				return current_state

			return split_access_key(all_states[0][0][0] if all_states[0][0] else all_states[0][1][0])[0] \
				if direction == Direction.FORWARD else \
				split_access_key(all_states[0][1][-1] if all_states[0][1] else all_states[0][0][-1])[0]
		elif next_set:
			if direction == Direction.FORWARD and ci[0] + 1 < len(all_states[ci[0]]):
				echom(u'Keyword set: %s | %s' % (u', '.join(all_states[ci[0] + 1][0]), u', '.join(all_states[ci[0] + 1][1])))
				return split_access_key(
					all_states[ci[0] + 1][0][0] if all_states[ci[0] + 1][0] else all_states[ci[0] + 1][1][0])[0]
			elif current_state is not None and direction == Direction.BACKWARD and ci[0] - 1 >= 0:
				echom(u'Keyword set: %s | %s' % (u', '.join(all_states[ci[0] - 1][0]), u', '.join(all_states[ci[0] - 1][1])))
				return split_access_key(
					all_states[ci[0] - 1][0][0] if all_states[ci[0] - 1][0] else all_states[ci[0] - 1][1][0])[0]
			else:
				echom(u'Already at the %s keyword set' % (u'first' if direction == Direction.BACKWARD else u'last'))
				return current_state
		else:
			next_pos = ci[2] + 1 if direction == Direction.FORWARD else ci[2] - 1
			if direction == Direction.FORWARD:
				if next_pos < len(all_states[ci[0]][ci[1]]):
					# select next state within done or todo states
					return split_access_key(all_states[ci[0]][ci[1]][next_pos])[0]

				elif not ci[1] and next_pos - len(all_states[ci[0]][ci[1]]) < len(all_states[ci[0]][ci[1] + 1]):
					# finished todo states, jump to done states
					return split_access_key(all_states[ci[0]][ci[1] + 1][next_pos - len(all_states[ci[0]][ci[1]])])[0]
			else:
				if next_pos >= 0:
					# select previous state within done or todo states
					return split_access_key(all_states[ci[0]][ci[1]][next_pos])[0]

				elif ci[1] and len(all_states[ci[0]][ci[1] - 1]) + next_pos < len(all_states[ci[0]][ci[1] - 1]):
					# finished done states, jump to todo states
					return split_access_key(all_states[ci[0]][ci[1] - 1][len(all_states[ci[0]][ci[1] - 1]) + next_pos])[0]

	@classmethod
	@realign_tags
	@repeat
	@apply_count
	def toggle_todo_state(cls, direction=Direction.FORWARD, interactive=False, next_set=False):
		u""" Toggle state of TODO item

		:returns: The changed heading
		"""
		d = ORGMODE.get_document(allow_dirty=True)

		# get heading
		heading = d.find_current_heading()
		if not heading:
			vim.eval(u'feedkeys("^", "n")')
			return

		todo_states = d.get_todo_states(strip_access_key=False)
		# get todo states
		if not todo_states:
			echom(u'No todo keywords configured.')
			return

		current_state = heading.todo

		# get new state interactively
		if interactive:
			# determine position of the interactive prompt
			prompt_pos = settings.get(u'org_todo_prompt_position', u'botright')
			if prompt_pos not in [u'botright', u'topleft']:
				prompt_pos = u'botright'

			# pass todo states to new window
			ORGTODOSTATES[d.bufnr] = todo_states
			settings.set(
				u'org_current_state_%d' % d.bufnr,
				current_state if current_state is not None else u'', overwrite=True)
			todo_buffer_exists = bool(int(vim.eval((
				u'bufexists("org:todo/%d")' % (d.bufnr, )).encode(u'utf-8'))))
			if todo_buffer_exists:
				# if the buffer already exists, reuse it
				vim.command((
					u'%s sbuffer org:todo/%d' % (prompt_pos, d.bufnr, )).encode(u'utf-8'))
			else:
				# create a new window
				vim.command((
					u'keepalt %s %dsplit org:todo/%d' % (prompt_pos, len(todo_states), d.bufnr)).encode(u'utf-8'))
		else:
			new_state = Todo._get_next_state(
				current_state, todo_states, direction=direction,
				interactive=interactive, next_set=next_set)
			cls.set_todo_state(new_state)

		# plug
		plug = u'OrgTodoForward'
		if direction == Direction.BACKWARD:
			plug = u'OrgTodoBackward'

		return plug

	@classmethod
	def set_todo_state(cls, state):
		u""" Set todo state for buffer.

		:bufnr:		Number of buffer the todo state should be updated for
		:state:		The new todo state
		"""
		lineno, colno = vim.current.window.cursor
		d = ORGMODE.get_document(allow_dirty=True)
		heading = d.find_current_heading()

		if not heading:
			return

		current_state = heading.todo

		# set new headline
		heading.todo = state
		d.write_heading(heading)

		# move cursor along with the inserted state only when current position
		# is in the heading; otherwite do nothing
		if heading.start_vim == lineno and colno > heading.level:
			if current_state is not None and \
				colno <= heading.level + len(current_state):
				# the cursor is actually on the todo keyword
				# move it back to the beginning of the keyword in that case
				vim.current.window.cursor = (lineno, heading.level + 1)
			else:
				# the cursor is somewhere in the text, move it along
				if current_state is None and state is None:
					offset = 0
				elif current_state is None and state is not None:
					offset = len(state) + 1
				elif current_state is not None and state is None:
					offset = -len(current_state) - 1
				else:
					offset = len(state) - len(current_state)
				vim.current.window.cursor = (lineno, colno + offset)

	@classmethod
	def init_org_todo(cls):
		u""" Initialize org todo selection window.
		"""
		bufnr = int(vim.current.buffer.name.split('/')[-1])
		all_states = ORGTODOSTATES.get(bufnr, None)

		# because timeoutlen can only be set globally it needs to be stored and restored later
		vim.command(u'let g:org_sav_timeoutlen=&timeoutlen'.encode(u'utf-8'))
		vim.command(u'au orgmode BufEnter <buffer> :if ! exists("g:org_sav_timeoutlen")|let g:org_sav_timeoutlen=&timeoutlen|set timeoutlen=1|endif'.encode(u'utf-8'))
		vim.command(u'au orgmode BufLeave <buffer> :if exists("g:org_sav_timeoutlen")|let &timeoutlen=g:org_sav_timeoutlen|unlet g:org_sav_timeoutlen|endif'.encode(u'utf-8'))
		# make window a scratch window and set the statusline differently
		vim.command(u'setlocal tabstop=16 buftype=nofile timeout timeoutlen=1 winfixheight'.encode(u'utf-8'))
		vim.command((u'setlocal statusline=Org\\ todo\\ (%s)' % vim.eval((u'fnameescape(fnamemodify(bufname(%d), ":t"))' % bufnr).encode(u'utf-8'))).encode(u'utf-8'))
		vim.command((u'nnoremap <silent> <buffer> <Esc> :%sbw<CR>' % (vim.eval(u'bufnr("%")'.encode(u'utf-8')), )).encode(u'utf-8'))
		vim.command(u'nnoremap <silent> <buffer> <CR> :let g:org_state = fnameescape(expand("<cword>"))<Bar>bw<Bar>exec "py ORGMODE.plugins[u\'Todo\'].set_todo_state(\'".g:org_state."\')"<Bar>unlet! g:org_state<CR>'.encode(u'utf-8'))

		if all_states is None:
			vim.command(u'bw'.encode(u'utf-8'))
			echom(u'No todo states avaiable for buffer %s' % vim.current.buffer.name)

		for l in xrange(0, len(all_states)):
			res = u''
			for j in xrange(0, 2):
				if j < len(all_states[l]):
					for i in all_states[l][j]:
						if type(i) != unicode:
							continue
						v, k = split_access_key(i)
						if k:
							res += (u'\t' if res else u'') + u'[%s] %s' % (k, v)
							# map access keys to callback that updates current heading
							# map selection keys
							vim.command((u'nnoremap <silent> <buffer> %s :bw<Bar>py ORGMODE.plugins[u"Todo"].set_todo_state("%s".decode(u"utf-8"))<CR>' % (k, v)).encode(u'utf-8'))
						elif v:
							res += (u'\t' if res else u'') + v
			if res:
				if l == 0:
					# WORKAROUND: the cursor can not be positioned properly on
					# the first line. Another line is just inserted and it
					# works great
					vim.current.buffer[0] = u''.encode(u'utf-8')
				vim.current.buffer.append(res.encode(u'utf-8'))

		# position the cursor of the current todo item
		vim.command(u'normal! G'.encode(u'utf-8'))
		current_state = settings.unset(u'org_current_state_%d' % bufnr)
		found = False
		if current_state is not None and current_state != '':
			for i in xrange(0, len(vim.current.buffer)):
				idx = vim.current.buffer[i].find(current_state)
				if idx != -1:
					vim.current.window.cursor = (i + 1, idx)
					found = True
					break
		if not found:
			vim.current.window.cursor = (2, 4)

		# finally make buffer non modifiable
		vim.command(u'setfiletype orgtodo'.encode(u'utf-8'))
		vim.command(u'setlocal nomodifiable'.encode(u'utf-8'))

		# remove temporary todo states for the current buffer
		del ORGTODOSTATES[bufnr]

	def register(self):
		u"""
		Registration of plugin. Key bindings and other initialization should be done.
		"""
		self.keybindings.append(Keybinding(u'<localleader>ct', Plug(
			u'OrgTodoToggleNonInteractive',
			u':py ORGMODE.plugins[u"Todo"].toggle_todo_state(interactive=False)<CR>')))
		self.menu + ActionEntry(u'&TODO/DONE/-', self.keybindings[-1])

		self.keybindings.append(Keybinding(u'<localleader>d', Plug(
			u'OrgTodoToggleInteractive',
			u':py ORGMODE.plugins[u"Todo"].toggle_todo_state(interactive=True)<CR>')))
		self.menu + ActionEntry(u'&TODO/DONE/- (interactiv)', self.keybindings[-1])

		# add submenu
		submenu = self.menu + Submenu(u'Select &keyword')

		self.keybindings.append(Keybinding(u'<S-Right>', Plug(
			u'OrgTodoForward',
			u':py ORGMODE.plugins[u"Todo"].toggle_todo_state()<CR>')))
		submenu + ActionEntry(u'&Next keyword', self.keybindings[-1])

		self.keybindings.append(Keybinding(u'<S-Left>', Plug(
			u'OrgTodoBackward',
			u':py ORGMODE.plugins[u"Todo"].toggle_todo_state(direction=2)<CR>')))
		submenu + ActionEntry(u'&Previous keyword', self.keybindings[-1])

		self.keybindings.append(Keybinding(u'<C-S-Right>', Plug(
			u'OrgTodoSetForward',
			u':py ORGMODE.plugins[u"Todo"].toggle_todo_state(next_set=True)<CR>')))
		submenu + ActionEntry(u'Next keyword &set', self.keybindings[-1])

		self.keybindings.append(Keybinding(u'<C-S-Left>', Plug(
			u'OrgTodoSetBackward',
			u':py ORGMODE.plugins[u"Todo"].toggle_todo_state(direction=2, next_set=True)<CR>')))
		submenu + ActionEntry(u'Previous &keyword set', self.keybindings[-1])

		settings.set(u'org_todo_keywords', [u'TODO'.encode(u'utf-8'), u'|'.encode(u'utf-8'), u'DONE'.encode(u'utf-8')])

		settings.set(u'org_todo_prompt_position', u'botright')

		vim.command(u'au orgmode BufReadCmd org:todo/* :py ORGMODE.plugins[u"Todo"].init_org_todo()'.encode(u'utf-8'))

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-

import vim

SCOPE_ALL = 1

# for all vim-orgmode buffers
SCOPE_GLOBAL = 2

# just for the current buffer - has priority before the global settings
SCOPE_BUFFER = 4

VARIABLE_LEADER = {SCOPE_GLOBAL: u'g', SCOPE_BUFFER: u'b'}

u""" Evaluate and store settings """


def get(setting, default=None, scope=SCOPE_ALL):
	u""" Evaluate setting in scope of the current buffer,
	globally and also from the contents of the current buffer

	WARNING: Only string values are converted to unicode. If a different value
	is received, e.g. a list or dict, no conversion is done.

	:setting: name of the variable to evaluate
	:default: default value in case the variable is empty

	:returns: variable value
	"""
	# TODO first read setting from org file which take precedence over vim
	# variable settings
	if (scope & SCOPE_ALL | SCOPE_BUFFER) and \
			int(vim.eval((u'exists("b:%s")' % setting).encode(u'utf-8'))):
		res = vim.eval((u"b:%s" % setting).encode(u'utf-8'))
		if type(res) in (unicode, str):
			return res.decode(u'utf-8')
		return res

	elif (scope & SCOPE_ALL | SCOPE_GLOBAL) and \
			int(vim.eval((u'exists("g:%s")' % setting).encode(u'utf-8'))):
		res = vim.eval((u"g:%s" % setting).encode(u'utf-8'))
		if type(res) in (unicode, str):
			return res.decode(u'utf-8')
		return res
	return default


def set(setting, value, scope=SCOPE_GLOBAL, overwrite=False):
	u""" Store setting in the definied scope

	WARNING: For the return value, only string are converted to unicode. If a
	different value is received by vim.eval, e.g. a list or dict, no conversion
	is done.

	:setting:   name of the setting
	:value:     the actual value, repr is called on the value to create a string
	            representation
	:scope:     the scope o the setting/variable
	:overwrite: overwrite existing settings (probably user definied settings)

	:returns: the new value in case of overwrite==False the current value
	"""
	if (not overwrite) and (
			int(vim.eval((u'exists("%s:%s")' % \
			(VARIABLE_LEADER[scope], setting)).encode(u'utf-8')))):
		res = vim.eval(
				(u'%s:%s' % (VARIABLE_LEADER[scope], setting)).encode(u'utf-8'))
		if type(res) in (unicode, str):
			return res.decode(u'utf-8')
		return res
	v = repr(value)
	if type(value) == unicode:
		# strip leading u of unicode string representations
		v = v[1:]

	cmd = u'let %s:%s = %s' % (VARIABLE_LEADER[scope], setting, v)
	vim.command(cmd.encode(u'utf-8'))
	return value


def unset(setting, scope=SCOPE_GLOBAL):
	u""" Unset setting int the definied scope
	:setting: name of the setting
	:scope:   the scope o the setting/variable

	:returns: last value of setting
	"""
	value = get(setting, scope=scope)
	cmd = u'unlet! %s:%s' % (VARIABLE_LEADER[scope], setting)
	vim.command(cmd.encode(u'utf-8'))
	return value


# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = vimbuffer
# -*- coding: utf-8 -*-

"""
	vimbuffer
	~~~~~~~~~~

	VimBuffer and VimBufferContent are the interface between liborgmode and
	vim.

	VimBuffer extends the liborgmode.document.Document().
	Document() is just a general implementation for loading an org file. It
	has no interface to an actual file or vim buffer. This is the task of
	vimbuffer.VimBuffer(). It is the interfaces to vim. The main tasks for
	VimBuffer are to provide read and write access to a real vim buffer.

	VimBufferContent is a helper class for VimBuffer. Basically, it hides the
	details of encoding - everything read from or written to VimBufferContent
	is UTF-8.
"""

from UserList import UserList

import vim

from orgmode import settings
from orgmode.exceptions import BufferNotFound, BufferNotInSync
from orgmode.liborgmode.documents import Document, MultiPurposeList, Direction
from orgmode.liborgmode.headings import Heading


class VimBuffer(Document):
	def __init__(self, bufnr=0):
		u"""
		:bufnr:		0: current buffer, every other number refers to another buffer
		"""
		Document.__init__(self)
		self._bufnr            = vim.current.buffer.number if bufnr == 0 else bufnr
		self._changedtick      = -1
		self._cached_heading   = None

		if self._bufnr == vim.current.buffer.number:
			self._content = VimBufferContent(vim.current.buffer)
		else:
			_buffer = None
			for b in vim.buffers:
				if self._bufnr == b.number:
					_buffer = b
					break

			if not _buffer:
				raise BufferNotFound(u'Unable to locate buffer number #%d' % self._bufnr)
			self._content = VimBufferContent(_buffer)

		self.update_changedtick()
		self._orig_changedtick = self._changedtick

	@property
	def tabstop(self):
		return int(vim.eval(u'&ts'.encode(u'utf-8')))

	@property
	def tag_column(self):
		return int(settings.get('org_tag_column', '77'))

	@property
	def is_insync(self):
		if self._changedtick == self._orig_changedtick:
			self.update_changedtick()
		return self._changedtick == self._orig_changedtick

	@property
	def bufnr(self):
		u"""
		:returns:	The buffer's number for the current document
		"""
		return self._bufnr

	def changedtick():
		""" Number of changes in vimbuffer """
		def fget(self):
			return self._changedtick
		def fset(self, value):
			self._changedtick = value
		return locals()
	changedtick = property(**changedtick())

	def get_todo_states(self, strip_access_key=True):
		u""" Returns a list containing a tuple of two lists of allowed todo
		states split by todo and done states. Multiple todo-done state
		sequences can be defined.

		:returns:	[([todo states], [done states]), ..]
		"""
		states = settings.get(u'org_todo_keywords', [])
		if type(states) not in (list, tuple):
			return []

		def parse_states(s, stop=0):
			res = []
			if not s:
				return res
			if type(s[0]) in (unicode, str):
				r = []
				for i in s:
					_i = i
					if type(_i) == str:
						_i = _i.decode(u'utf-8')
					if type(_i) == unicode and _i:
						if strip_access_key and u'(' in _i:
							_i = _i[:_i.index(u'(')]
							if _i:
								r.append(_i)
						else:
							r.append(_i)
				if not u'|' in r:
					if not stop:
						res.append((r[:-1], [r[-1]]))
					else:
						res = (r[:-1], [r[-1]])
				else:
					seperator_pos = r.index(u'|')
					if not stop:
						res.append((r[0:seperator_pos], r[seperator_pos + 1:]))
					else:
						res = (r[0:seperator_pos], r[seperator_pos + 1:])
			elif type(s) in (list, tuple) and not stop:
				for i in s:
					r = parse_states(i, stop=1)
					if r:
						res.append(r)
			return res

		return parse_states(states)

	def update_changedtick(self):
		if self.bufnr == vim.current.buffer.number:
			self._changedtick = int(vim.eval(u'b:changedtick'.encode(u'utf-8')))
		else:
			vim.command(u'unlet! g:org_changedtick | let g:org_lz = &lz | let g:org_hidden = &hidden | set lz hidden'.encode(u'utf-8'))
			# TODO is this likely to fail? maybe some error hangling should be added
			vim.command((u'keepalt buffer %d | let g:org_changedtick = b:changedtick | buffer %d' % \
					(self.bufnr, vim.current.buffer.number)).encode(u'utf-8'))
			vim.command(u'let &lz = g:org_lz | let &hidden = g:org_hidden | unlet! g:org_lz g:org_hidden | redraw'.encode(u'utf-8'))
			self._changedtick = int(vim.eval(u'g:org_changedtick'.encode(u'utf-8')))

	def write(self):
		u""" write the changes to the vim buffer

		:returns:	True if something was written, otherwise False
		"""
		if not self.is_dirty:
			return False

		self.update_changedtick()
		if not self.is_insync:
			raise BufferNotInSync(u'Buffer is not in sync with vim!')

		# write meta information
		if self.is_dirty_meta_information:
			meta_end = 0 if self._orig_meta_information_len is None else self._orig_meta_information_len
			self._content[:meta_end] = self.meta_information
			self._orig_meta_information_len = len(self.meta_information)

		# remove deleted headings
		already_deleted = []
		for h in sorted(self._deleted_headings, cmp=lambda x, y: cmp(x._orig_start, y._orig_start), reverse=True):
			if h._orig_start is not None and h._orig_start not in already_deleted:
				# this is a heading that actually exists on the buffer and it
				# needs to be removed
				del self._content[h._orig_start:h._orig_start + h._orig_len]
				already_deleted.append(h._orig_start)
		del self._deleted_headings[:]
		del already_deleted

		# update changed headings and add new headings
		for h in self.all_headings():
			if h.is_dirty:
				if h._orig_start is not None:
					# this is a heading that existed before and was changed. It
					# needs to be replaced
					if h.is_dirty_heading:
						self._content[h.start:h.start + 1] = [unicode(h)]
					if h.is_dirty_body:
						self._content[h.start + 1:h.start + h._orig_len] = h.body
				else:
					# this is a new heading. It needs to be inserted
					self._content[h.start:h.start] = [unicode(h)] + h.body
				h._dirty_heading = False
				h._dirty_body = False
			# for all headings the length and start offset needs to be updated
			h._orig_start = h.start
			h._orig_len = len(h)

		self._dirty_meta_information = False
		self._dirty_document = False

		self.update_changedtick()
		self._orig_changedtick = self._changedtick
		return True

	def write_heading(self, heading, including_children=True):
		""" WARNING: use this function only when you know what you are doing!
		This function writes a heading to the vim buffer. It offers performance
		advantages over the regular write() function. This advantage is
		combined with no sanity checks! Whenever you use this function, make
		sure the heading you are writing contains the right offsets
		(Heading._orig_start, Heading._orig_len).

		Usage example:
			# Retrieve a potentially dirty document
			d = ORGMODE.get_document(allow_dirty=True)
			# Don't rely on the DOM, retrieve the heading afresh
			h = d.find_heading(direction=Direction.FORWARD, position=100)
			# Update tags
			h.tags = ['tag1', 'tag2']
			# Write the heading
			d.write_heading(h)

		This function can't be used to delete a heading!

		:heading:				Write this heading with to the vim buffer
		:including_children:	Also include children in the update

		:returns				The written heading
		"""
		if including_children and heading.children:
			for child in heading.children[::-1]:
				self.write_heading(child, including_children)

		if heading.is_dirty:
			if heading._orig_start is not None:
				# this is a heading that existed before and was changed. It
				# needs to be replaced
				if heading.is_dirty_heading:
					self._content[heading._orig_start:heading._orig_start + 1] = [unicode(heading)]
				if heading.is_dirty_body:
					self._content[heading._orig_start + 1:heading._orig_start + heading._orig_len] = heading.body
			else:
				# this is a new heading. It needs to be inserted
				raise ValueError('Heading must contain the attribute _orig_start! %s' % heading)
			heading._dirty_heading = False
			heading._dirty_body = False
		# for all headings the length offset needs to be updated
		heading._orig_len = len(heading)

		return heading

	def write_checkbox(self, checkbox, including_children=True):
		if including_children and checkbox.children:
			for child in checkbox.children[::-1]:
				self.write_checkbox(child, including_children)

		if checkbox.is_dirty:
			if checkbox._orig_start is not None:
				# this is a heading that existed before and was changed. It
				# needs to be replaced
				# print "checkbox is dirty? " + str(checkbox.is_dirty_checkbox)
				# print checkbox
				if checkbox.is_dirty_checkbox:
					self._content[checkbox._orig_start:checkbox._orig_start + 1] = [unicode(checkbox)]
				if checkbox.is_dirty_body:
					self._content[checkbox._orig_start + 1:checkbox._orig_start + checkbox._orig_len] = checkbox.body
			else:
				# this is a new checkbox. It needs to be inserted
				raise ValueError('Checkbox must contain the attribute _orig_start! %s' % checkbox)
			checkbox._dirty_checkbox = False
			checkbox._dirty_body = False
		# for all headings the length offset needs to be updated
		checkbox._orig_len = len(checkbox)

		return checkbox

	def write_checkboxes(self, checkboxes):
		pass

	def previous_heading(self, position=None):
		u""" Find the next heading (search forward) and return the related object
		:returns:	Heading object or None
		"""
		h = self.current_heading(position=position)
		if h:
			return h.previous_heading

	def current_heading(self, position=None):
		u""" Find the current heading (search backward) and return the related object
		:returns:	Heading object or None
		"""
		if position is None:
			position = vim.current.window.cursor[0] - 1

		if not self.headings:
			return

		def binaryFindInDocument():
			hi = len(self.headings)
			lo = 0
			while lo < hi:
				mid = (lo+hi)//2
				h = self.headings[mid]
				if h.end_of_last_child < position:
					lo = mid + 1
				elif h.start > position:
					hi = mid
				else:
					return binaryFindHeading(h)

		def binaryFindHeading(heading):
			if not heading.children or heading.end >= position:
				return heading

			hi = len(heading.children)
			lo = 0
			while lo < hi:
				mid = (lo+hi)//2
				h = heading.children[mid]
				if h.end_of_last_child < position:
					lo = mid + 1
				elif h.start > position:
					hi = mid
				else:
					return binaryFindHeading(h)

		# look at the cache to find the heading
		h_tmp = self._cached_heading
		if h_tmp is not None:
			if h_tmp.end_of_last_child > position and \
					h_tmp.start < position:
				if h_tmp.end < position:
					self._cached_heading = binaryFindHeading(h_tmp)
				return self._cached_heading

		self._cached_heading = binaryFindInDocument()
		return self._cached_heading

	def next_heading(self, position=None):
		u""" Find the next heading (search forward) and return the related object
		:returns:	Heading object or None
		"""
		h = self.current_heading(position=position)
		if h:
			return h.next_heading

	def find_current_heading(self, position=None, heading=Heading):
		u""" Find the next heading backwards from the position of the cursor.
		The difference to the function current_heading is that the returned
		object is not built into the DOM. In case the DOM doesn't exist or is
		out of sync this function is much faster in fetching the current
		heading.

		:position:	The position to start the search from

		:heading:	The base class for the returned heading

		:returns:	Heading object or None
		"""
		return self.find_heading(vim.current.window.cursor[0] - 1 \
				if position is None else position, \
				direction=Direction.BACKWARD, heading=heading, \
				connect_with_document=False)


class VimBufferContent(MultiPurposeList):
	u""" Vim Buffer Content is a UTF-8 wrapper around a vim buffer. When
	retrieving or setting items in the buffer an automatic conversion is
	performed.

	This ensures UTF-8 usage on the side of liborgmode and the vim plugin
	vim-orgmode.
	"""

	def __init__(self, vimbuffer, on_change=None):
		MultiPurposeList.__init__(self, on_change=on_change)

		# replace data with vimbuffer to make operations change the actual
		# buffer
		self.data = vimbuffer

	def __contains__(self, item):
		i = item
		if type(i) is unicode:
			i = item.encode(u'utf-8')
		return MultiPurposeList.__contains__(self, i)

	def __getitem__(self, i):
		item = MultiPurposeList.__getitem__(self, i)
		if type(item) is str:
			return item.decode(u'utf-8')
		return item

	def __getslice__(self, i, j):
		return [item.decode(u'utf-8') if type(item) is str else item \
				for item in MultiPurposeList.__getslice__(self, i, j)]

	def __setitem__(self, i, item):
		_i = item
		if type(_i) is unicode:
			_i = item.encode(u'utf-8')

		MultiPurposeList.__setitem__(self, i, _i)

	def __setslice__(self, i, j, other):
		o = []
		o_tmp = other
		if type(o_tmp) not in (list, tuple) and not isinstance(o_tmp, UserList):
			o_tmp = list(o_tmp)
		for item in o_tmp:
			if type(item) == unicode:
				o.append(item.encode(u'utf-8'))
			else:
				o.append(item)
		MultiPurposeList.__setslice__(self, i, j, o)

	def __add__(self, other):
		raise NotImplementedError()
		# TODO: implement me
		if isinstance(other, UserList):
			return self.__class__(self.data + other.data)
		elif isinstance(other, type(self.data)):
			return self.__class__(self.data + other)
		else:
			return self.__class__(self.data + list(other))

	def __radd__(self, other):
		raise NotImplementedError()
		# TODO: implement me
		if isinstance(other, UserList):
			return self.__class__(other.data + self.data)
		elif isinstance(other, type(self.data)):
			return self.__class__(other + self.data)
		else:
			return self.__class__(list(other) + self.data)

	def __iadd__(self, other):
		o = []
		o_tmp = other
		if type(o_tmp) not in (list, tuple) and not isinstance(o_tmp, UserList):
			o_tmp = list(o_tmp)
		for i in o_tmp:
			if type(i) is unicode:
				o.append(i.encode(u'utf-8'))
			else:
				o.append(i)

		return MultiPurposeList.__iadd__(self, o)

	def append(self, item):
		i = item
		if type(item) is str:
			i = item.encode(u'utf-8')
		MultiPurposeList.append(self, i)

	def insert(self, i, item):
		_i = item
		if type(_i) is str:
			_i = item.encode(u'utf-8')
		MultiPurposeList.insert(self, i, _i)

	def index(self, item, *args):
		i = item
		if type(i) is unicode:
			i = item.encode(u'utf-8')
		MultiPurposeList.index(self, i, *args)

	def pop(self, i=-1):
		return MultiPurposeList.pop(self, i).decode(u'utf-8')

	def extend(self, other):
		o = []
		o_tmp = other
		if type(o_tmp) not in (list, tuple) and not isinstance(o_tmp, UserList):
			o_tmp = list(o_tmp)
		for i in o_tmp:
			if type(i) is unicode:
				o.append(i.encode(u'utf-8'))
			else:
				o.append(i)
		MultiPurposeList.extend(self, o)


# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = _vim
# -*- coding: utf-8 -*-

"""
	VIM ORGMODE
	~~~~~~~~~~~~

	TODO
"""

import imp
import types

import vim
from datetime import datetime

import orgmode.keybinding
import orgmode.menu
import orgmode.plugins
import orgmode.settings
from orgmode.exceptions import PluginError
from orgmode.vimbuffer import VimBuffer
from orgmode.liborgmode.agenda import AgendaManager


REPEAT_EXISTS = bool(int(vim.eval('exists("*repeat#set()")')))
TAGSPROPERTIES_EXISTS = False

cache_heading = None

def realign_tags(f):
	u"""
	Update tag alignment, dependency to TagsProperties plugin!
	"""
	def r(*args, **kwargs):
		global TAGSPROPERTIES_EXISTS
		res = f(*args, **kwargs)

		if not TAGSPROPERTIES_EXISTS and u'TagsProperties' in ORGMODE.plugins:
			TAGSPROPERTIES_EXISTS = True

		if TAGSPROPERTIES_EXISTS:
			ORGMODE.plugins[u'TagsProperties'].realign_tags()

		return res
	return r


def repeat(f):
	u"""
	Integrate with the repeat plugin if available

	The decorated function must return the name of the <Plug> command to
	execute by the repeat plugin.
	"""
	def r(*args, **kwargs):
		res = f(*args, **kwargs)
		if REPEAT_EXISTS and isinstance(res, basestring):
			vim.command((u'silent! call repeat#set("\\<Plug>%s")' % res)
					.encode(u'utf-8'))
		return res
	return r


def apply_count(f):
	u"""
	Decorator which executes function v:count or v:prevount (not implemented,
	yet) times. The decorated function must return a value that evaluates to
	True otherwise the function is not repeated.
	"""
	def r(*args, **kwargs):
		count = 0
		try:
			count = int(vim.eval(u'v:count'.encode('utf-8')))

			# visual count is not implemented yet
			#if not count:
			#	count = int(vim.eval(u'v:prevcount'.encode(u'utf-8')))
		except Exception, e:
			pass

		res = f(*args, **kwargs)
		count -= 1
		while res and count > 0:
			f(*args, **kwargs)
			count -= 1
		return res
	return r


def echo(message):
	u"""
	Print a regular message that will not be visible to the user when
	multiple lines are printed
	"""
	for m in message.split(u'\n'):
		vim.command((u':echo "%s"' % m).encode(u'utf-8'))


def echom(message):
	u"""
	Print a regular message that will be visible to the user, even when
	multiple lines are printed
	"""
	# probably some escaping is needed here
	for m in message.split(u'\n'):
		vim.command((u':echomsg "%s"' % m).encode(u'utf-8'))


def echoe(message):
	u"""
	Print an error message. This should only be used for serious errors!
	"""
	# probably some escaping is needed here
	for m in message.split(u'\n'):
		vim.command((u':echoerr "%s"' % m).encode(u'utf-8'))


def insert_at_cursor(text, move=True, start_insertmode=False):
	u"""Insert text at the position of the cursor.

	If move==True move the cursor with the inserted text.
	"""
	d = ORGMODE.get_document(allow_dirty=True)
	line, col = vim.current.window.cursor
	_text = d._content[line - 1]
	d._content[line - 1] = _text[:col + 1] + text + _text[col + 1:]
	if move:
		vim.current.window.cursor = (line, col + len(text))
	if start_insertmode:
		vim.command(u'startinsert'.encode(u'utf-8'))


def get_user_input(message):
	u"""Print the message and take input from the user.
	Return the input or None if there is no input.
	"""
	vim.command(u'call inputsave()'.encode(u'utf-8'))
	vim.command((u"let user_input = input('" + message + u": ')")
			.encode(u'utf-8'))
	vim.command(u'call inputrestore()'.encode(u'utf-8'))
	try:
		return vim.eval(u'user_input'.encode(u'utf-8')).decode(u'utf-8')
	except:
		return None


def get_bufnumber(bufname):
	"""
	Return the number of the buffer for the given bufname if it exist;
	else None.
	"""
	for b in vim.buffers:
		if b.name == bufname:
			return int(b.number)


def get_bufname(bufnr):
	"""
	Return the name of the buffer for the given bufnr if it exist; else None.
	"""
	for b in vim.buffers:
		if b.number == bufnr:
			return b.name


def indent_orgmode():
	u""" Set the indent value for the current line in the variable
	b:indent_level

	Vim prerequisites:
		:setlocal indentexpr=Method-which-calls-indent_orgmode

	:returns: None
	"""
	line = int(vim.eval(u'v:lnum'.encode(u'utf-8')))
	d = ORGMODE.get_document()
	heading = d.current_heading(line - 1)
	if heading and line != heading.start_vim:
		heading.init_checkboxes()
		checkbox = heading.current_checkbox()
		level = heading.level + 1
		if checkbox:
			level = level + checkbox.number_of_parents * 6
			if line != checkbox.start_vim:
				# indent body up to the beginning of the checkbox' text
				# if checkbox isn't indented to the proper location, the body
				# won't be indented either
				level = checkbox.level + len(checkbox.type) + 1 + \
						(4 if checkbox.status else 0)
		vim.command((u'let b:indent_level = %d' % level).encode(u'utf-8'))


def fold_text(allow_dirty=False):
	u""" Set the fold text
		:setlocal foldtext=Method-which-calls-foldtext

	:allow_dirty:	Perform a query without (re)building the DOM if True
	:returns: None
	"""
	line = int(vim.eval(u'v:foldstart'.encode(u'utf-8')))
	d = ORGMODE.get_document(allow_dirty=allow_dirty)
	heading = None
	if allow_dirty:
		heading = d.find_current_heading(line - 1)
	else:
		heading = d.current_heading(line - 1)
	if heading:
		str_heading = unicode(heading)

		# expand tabs
		ts = int(vim.eval(u'&ts'.encode('utf-8')))
		idx = str_heading.find(u'\t')
		if idx != -1:
			tabs, spaces = divmod(idx, ts)
			str_heading = str_heading.replace(u'\t', u' ' * (ts - spaces), 1)
			str_heading = str_heading.replace(u'\t', u' ' * ts)

		# Workaround for vim.command seems to break the completion menu
		vim.eval((u'SetOrgFoldtext("%s...")' % (str_heading.replace(
				u'\\', u'\\\\').replace(u'"', u'\\"'), )).encode(u'utf-8'))
		#vim.command((u'let b:foldtext = "%s... "' % \
		#		(str_heading.replace(u'\\', u'\\\\')
		#		.replace(u'"', u'\\"'), )).encode('utf-8'))


def fold_orgmode(allow_dirty=False):
	u""" Set the fold expression/value for the current line in the variable
	b:fold_expr

	Vim prerequisites:
		:setlocal foldmethod=expr
		:setlocal foldexpr=Method-which-calls-fold_orgmode

	:allow_dirty:	Perform a query without (re)building the DOM if True
	:returns: None
	"""
	line = int(vim.eval(u'v:lnum'.encode(u'utf-8')))
	d = ORGMODE.get_document(allow_dirty=allow_dirty)
	heading = None
	if allow_dirty:
		heading = d.find_current_heading(line - 1)
	else:
		heading = d.current_heading(line - 1)

	# if cache_heading != heading:
		# heading.init_checkboxes()
		# checkbox = heading.current_checkbox()

	# cache_heading = heading
	if heading:
		# if checkbox:
			# vim.command((u'let b:fold_expr = ">%d"' % heading.level + checkbox.level).encode(u'utf-8'))
		if 0:
			pass
		elif line == heading.start_vim:
			vim.command((u'let b:fold_expr = ">%d"' % heading.level).encode(u'utf-8'))
		#elif line == heading.end_vim:
		#	vim.command((u'let b:fold_expr = "<%d"' % heading.level).encode(u'utf-8'))
		# end_of_last_child_vim is a performance junky and is actually not needed
		#elif line == heading.end_of_last_child_vim:
		#	vim.command((u'let b:fold_expr = "<%d"' % heading.level).encode(u'utf-8'))
		else:
			vim.command((u'let b:fold_expr = %d' % heading.level).encode(u'utf-8'))


def date_to_str(date):
	if isinstance(date, datetime):
		date = date.strftime(
				u'%Y-%m-%d %a %H:%M'.encode(u'utf-8')).decode(u'utf-8')
	else:
		date = date.strftime(
				u'%Y-%m-%d %a'.encode(u'utf-8')).decode(u'utf-8')
	return date

class OrgMode(object):
	u""" Vim Buffer """

	def __init__(self):
		object.__init__(self)
		self.debug = bool(int(orgmode.settings.get(u'org_debug', False)))

		self.orgmenu = orgmode.menu.Submenu(u'&Org')
		self._plugins = {}
		# list of vim buffer objects
		self._documents = {}

		# agenda manager
		self.agenda_manager = AgendaManager()

	def get_document(self, bufnr=0, allow_dirty=False):
		""" Retrieve instance of vim buffer document. This Document should be
		used for manipulating the vim buffer.

		:bufnr:			Retrieve document with bufnr
		:allow_dirty:	Allow the retrieved document to be dirty

		:returns:	vim buffer instance
		"""
		if bufnr == 0:
			bufnr = vim.current.buffer.number

		if bufnr in self._documents:
			if allow_dirty or self._documents[bufnr].is_insync:
				return self._documents[bufnr]
		self._documents[bufnr] = VimBuffer(bufnr).init_dom()
		return self._documents[bufnr]

	@property
	def plugins(self):
		return self._plugins.copy()

	@orgmode.keybinding.register_keybindings
	@orgmode.keybinding.register_commands
	@orgmode.menu.register_menu
	def register_plugin(self, plugin):
		if not isinstance(plugin, basestring):
			raise ValueError(u'Parameter plugin is not of type string')

		if plugin == u'|':
			self.orgmenu + orgmode.menu.Separator()
			self.orgmenu.children[-1].create()
			return

		if plugin in self._plugins:
			raise PluginError(u'Plugin %s has already been loaded')

		# a python module
		module = None

		# actual plugin class
		_class = None

		# locate module and initialize plugin class
		try:
			module = imp.find_module(plugin, orgmode.plugins.__path__)
		except ImportError, e:
			echom(u'Plugin not found: %s' % plugin)
			if self.debug:
				raise e
			return

		if not module:
			echom(u'Plugin not found: %s' % plugin)
			return

		try:
			module = imp.load_module(plugin, *module)
			if not hasattr(module, plugin):
				echoe(u'Unable to find plugin: %s' % plugin)
				if self.debug:
					raise PluginError(u'Unable to find class %s' % plugin)
				return
			_class = getattr(module, plugin)
			self._plugins[plugin] = _class()
			self._plugins[plugin].register()
			if self.debug:
				echo(u'Plugin registered: %s' % plugin)
			return self._plugins[plugin]
		except Exception, e:
			echoe(u'Unable to activate plugin: %s' % plugin)
			echoe(u"%s" % e)
			if self.debug:
				import traceback
				echoe(traceback.format_exc())

	def register_keybindings(self):
		@orgmode.keybinding.register_keybindings
		def dummy(plugin):
			return plugin

		for p in self.plugins.itervalues():
			dummy(p)

	def register_menu(self):
		self.orgmenu.create()

	def unregister_menu(self):
		vim.command(u'silent! aunmenu Org'.encode(u'utf-8'))

	def start(self):
		u""" Start orgmode and load all requested plugins
		"""
		plugins = orgmode.settings.get(u"org_plugins")

		if not plugins:
			echom(u'orgmode: No plugins registered.')

		if isinstance(plugins, basestring):
			try:
				self.register_plugin(plugins)
			except Exception, e:
				import traceback
				traceback.print_exc()
		elif isinstance(plugins, types.ListType) or \
				isinstance(plugins, types.TupleType):
			for p in plugins:
				try:
					self.register_plugin(p)
				except Exception, e:
					echoe('Error in %s plugin:' % p)
					import traceback
					traceback.print_exc()

		return plugins


ORGMODE = OrgMode()


# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import test_vimbuffer

import test_libagendafilter
import test_libcheckbox
import test_libbase
import test_libheading
import test_liborgdate
import test_liborgdate_parsing
import test_liborgdatetime
import test_liborgtimerange

import test_plugin_date
import test_plugin_edit_structure
import test_plugin_edit_checkbox
import test_plugin_misc
import test_plugin_navigator
import test_plugin_show_hide
import test_plugin_tags_properties
import test_plugin_todo
import test_plugin_mappings

import unittest


if __name__ == '__main__':
	tests = unittest.TestSuite()

	tests.addTests(test_vimbuffer.suite())

	# lib
	tests.addTests(test_libbase.suite())
	tests.addTests(test_libcheckbox.suite())
	tests.addTests(test_libagendafilter.suite())
	tests.addTests(test_libheading.suite())
	tests.addTests(test_liborgdate.suite())
	tests.addTests(test_liborgdate_parsing.suite())
	tests.addTests(test_liborgdatetime.suite())
	tests.addTests(test_liborgtimerange.suite())

	# plugins
	tests.addTests(test_plugin_date.suite())
	tests.addTests(test_plugin_edit_structure.suite())
	tests.addTests(test_plugin_edit_checkbox.suite())
	tests.addTests(test_plugin_misc.suite())
	tests.addTests(test_plugin_navigator.suite())
	tests.addTests(test_plugin_show_hide.suite())
	tests.addTests(test_plugin_tags_properties.suite())
	tests.addTests(test_plugin_todo.suite())
	tests.addTests(test_plugin_mappings.suite())

	runner = unittest.TextTestRunner()
	runner.run(tests)

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = test_libagendafilter
# -*- coding: utf-8 -*-


import sys
sys.path.append(u'../ftplugin')

import unittest
from datetime import date
from datetime import timedelta

from orgmode.liborgmode.headings import Heading
from orgmode.liborgmode.orgdate import OrgDate
from orgmode.liborgmode.agendafilter import contains_active_todo
from orgmode.liborgmode.agendafilter import contains_active_date
from orgmode.liborgmode.orgdate import OrgDateTime
from orgmode.liborgmode.agendafilter import is_within_week
from orgmode.liborgmode.agendafilter import is_within_week_and_active_todo
from orgmode.liborgmode.agendafilter import filter_items


class AgendaFilterTestCase(unittest.TestCase):
	u"""Tests all the functionality of the Agenda filter module."""

	def setUp(self):
		self.text = [ i.encode(u'utf-8') for i in u"""
* TODO Heading 1
  some text
""".split(u'\n') ]

	def test_contains_active_todo(self):
		heading = Heading(title=u'Refactor the code', todo='TODO')
		self.assertTrue(contains_active_todo(heading))

		heading = Heading(title=u'Refactor the code', todo='DONE')
		self.assertFalse(contains_active_todo(heading))

		heading = Heading(title=u'Refactor the code', todo=None)
		self.assertFalse(contains_active_todo(heading))

	def test_contains_active_date(self):
		heading = Heading(title=u'Refactor the code', active_date=None)
		self.assertFalse(contains_active_date(heading))

		odate = OrgDate(True, 2011, 11, 1)
		heading = Heading(title=u'Refactor the code', active_date=odate)
		self.assertTrue(contains_active_date(heading))

	def test_is_within_week_with_orgdate(self):
		# to far in the future
		tmpdate = date.today() + timedelta(days=8)
		odate = OrgDate(True, tmpdate.year, tmpdate.month, tmpdate.day)
		heading = Heading(title=u'Refactor the code', active_date=odate)
		self.assertFalse(is_within_week(heading))

		# within a week
		tmpdate = date.today() + timedelta(days=5)
		odate = OrgDate(True, tmpdate.year, tmpdate.month, tmpdate.day)
		heading = Heading(title=u'Refactor the code', active_date=odate)
		self.assertTrue(is_within_week(heading))

		# in the past
		tmpdate = date.today() - timedelta(days=105)
		odate = OrgDate(True, tmpdate.year, tmpdate.month, tmpdate.day)
		heading = Heading(title=u'Refactor the code', active_date=odate)
		self.assertTrue(is_within_week(heading))

	def test_is_within_week_with_orgdatetime(self):
		# to far in the future
		tmp = date.today() + timedelta(days=1000)
		odate = OrgDateTime(True, tmp.year, tmp.month, tmp.day, 10, 10)
		heading = Heading(title=u'Refactor the code', active_date=odate)
		self.assertFalse(is_within_week(heading))

		# within a week
		tmpdate = date.today() + timedelta(days=5)
		odate = OrgDateTime(True, tmpdate.year, tmpdate.month, tmpdate.day, 1, 0)
		heading = Heading(title=u'Refactor the code', active_date=odate)
		self.assertTrue(is_within_week(heading))

		# in the past
		tmpdate = date.today() - timedelta(days=5)
		odate = OrgDateTime(True, tmpdate.year, tmpdate.month, tmpdate.day, 1, 0)
		heading = Heading(title=u'Refactor the code', active_date=odate)
		self.assertTrue(is_within_week(heading))

	def test_filter_items(self):
		# only headings with date and todo should be returned
		tmpdate = date.today()
		odate = OrgDate(True, tmpdate.year, tmpdate.month, tmpdate.day)
		tmp_head = Heading(title=u'Refactor the code', todo=u'TODO', active_date=odate)
		headings = [tmp_head]
		filtered = filter_items(headings,
				[contains_active_date, contains_active_todo])

		self.assertEqual(len(filtered), 1)
		self.assertEqual(filtered, headings)

		# try a longer list
		headings = headings * 3
		filtered = filter_items(headings,
				[contains_active_date, contains_active_todo])

		self.assertEqual(len(filtered), 3)
		self.assertEqual(filtered, headings)

		# date does not contain all needed fields thus gets ignored
		tmpdate = date.today()
		odate = OrgDate(True, tmpdate.year, tmpdate.month, tmpdate.day)
		tmp_head = Heading(title=u'Refactor the code', active_date=odate)
		headings = [tmp_head]
		filtered = filter_items(headings, [contains_active_date,
				contains_active_todo])
		self.assertEqual([], filtered)

	def test_filter_items_with_some_todos_and_dates(self):
		u"""
		Only the headings with todo and dates should be retunrned.
		"""
		tmp = [u"* TODO OrgMode Demo und Tests"
				u"<2011-08-22 Mon>"]
		headings = [Heading.parse_heading_from_data(tmp, [u'TODO'])]
		filtered = filter_items(headings, [is_within_week_and_active_todo])
		self.assertEqual(len(filtered), 1)
		self.assertEqual(headings, filtered)

		tmp = [Heading.parse_heading_from_data([u"** DONE something <2011-08-10 Wed>"], [u'TODO']),
				Heading.parse_heading_from_data([u"*** TODO rsitenaoritns more <2011-08-25 Thu>"], [u'TODO']),
				Heading.parse_heading_from_data([u"*** DONE some more <2011-08-25 Thu>"], [u'TODO']),
				Heading.parse_heading_from_data([u"*** TODO some more <2011-08-25 Thu>"], [u'TODO']),
				Heading.parse_heading_from_data([u"** DONE something2 <2011-08-10 Wed>"], [u'TODO'])
		]
		for h in tmp:
			headings.append(h)

		filtered = filter_items(headings, [is_within_week_and_active_todo])
		self.assertEqual(len(filtered), 3)
		self.assertEqual(filtered, [headings[0], headings[2], headings[4]])


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(AgendaFilterTestCase)


# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = test_libbase
# -*- coding: utf-8 -*-

import unittest
import sys
sys.path.append(u'../ftplugin')

from orgmode.liborgmode.base import Direction, get_domobj_range
from orgmode.liborgmode.headings import Heading


class LibBaseTestCase(unittest.TestCase):

	def setUp(self):
		self.case1 = """
* head1
 heading body
 for testing
* head2
** head3
		""".split("\n")

	def test_base_functions(self):
		# direction FORWARD
		(start, end) = get_domobj_range(content=self.case1, position=1, identify_fun=Heading.identify_heading)
		self.assertEqual((start, end), (1, 3))
		(start, end) = get_domobj_range(content=self.case1, position=3, direction=Direction.BACKWARD, \
										identify_fun=Heading.identify_heading)
		self.assertEqual((start, end), (1, 3))

def suite():
	return unittest.TestLoader().loadTestsFromTestCase(
			LibBaseTestCase)

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = test_libcheckbox
# -*- coding: utf-8 -*-

import unittest
import sys
sys.path.append(u'../ftplugin')

import vim
from orgmode.liborgmode.checkboxes import Checkbox
from orgmode._vim import ORGMODE


def set_vim_buffer(buf=None, cursor=(2, 0), bufnr=0):
	if buf is None:
		buf = []
	vim.current.buffer[:] = buf
	vim.current.window.cursor = cursor
	vim.current.buffer.number = bufnr


class CheckboxTestCase(unittest.TestCase):

	def setUp(self):
		counter = 0
		vim.CMDHISTORY = []
		vim.CMDRESULTS = {}
		vim.EVALHISTORY = []
		vim.EVALRESULTS = {
				# no org_todo_keywords for b
				u'exists("b:org_todo_keywords")'.encode(u'utf-8'): '0'.encode(u'utf-8'),
				# global values for org_todo_keywords
				u'exists("g:org_todo_keywords")'.encode(u'utf-8'): '1'.encode(u'utf-8'),
				u'g:org_todo_keywords'.encode(u'utf-8'): [u'TODO'.encode(u'utf-8'), u'DONE'.encode(u'utf-8'), u'|'.encode(u'utf-8')],
				u'exists("g:org_improve_split_heading")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("b:org_improve_split_heading")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("b:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("*repeat#set()")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'b:changedtick'.encode(u'utf-8'): (u'%d' % counter).encode(u'utf-8'),
				u'&ts'.encode(u'utf-8'): u'8'.encode(u'utf-8'),
				u'exists("g:org_tag_column")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("b:org_tag_column")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u"v:count".encode(u'utf-8'): u'0'.encode(u'utf-8')}

		self.c1 = """
* heading1 [/]
  - [-] checkbox1 [%]
        - [X] checkbox2
        - [ ] checkbox3
  - [X] checkbox4
""".split("\n")

		self.c2 = """
* heading1
  - [ ] checkbox1
  - [ ] checkbox2
        - [ ] checkbox3
              - [ ] checkbox4
                    - [ ] checkbox5
   - [ ] checkbox6
""".split("\n")

	def test_init(self):
		# test initialize Checkbox
		c = Checkbox(level=1, title="checkbox1")
		self.assertEqual(str(c), " - [ ] checkbox1")
		c = Checkbox(level=3, title="checkbox2", status="[X]")
		self.assertEqual(str(c), "   - [X] checkbox2")

	def test_basic(self):
		bufnr = 1
		set_vim_buffer(buf=self.c1, bufnr=bufnr)
		h = ORGMODE.get_document(bufnr=bufnr).current_heading()
		h.init_checkboxes()

		c = h.current_checkbox(position=2)
		self.assertEqual(str(c), self.c1[2])
		self.assertFalse(c.are_children_all(Checkbox.STATUS_ON))
		self.assertTrue(c.is_child_one(Checkbox.STATUS_OFF))
		self.assertFalse(c.are_siblings_all(Checkbox.STATUS_ON))

		for child in c.all_children():
			pass
		for sibling in c.all_siblings():
			pass
		c = h.current_checkbox(position=3)
		new_checkbox = c.copy()
		self.assertEqual(str(c), self.c1[3])
		c.get_parent_list()
		c.get_index_in_parent_list()

	def test_identify(self):
		# test identify_checkbox
		self.assertEqual(Checkbox.identify_checkbox(self.c1[2]), 2)
		self.assertEqual(Checkbox.identify_checkbox(self.c1[3]), 8)
		# check for corner case
		self.assertEqual(Checkbox.identify_checkbox(" - [ ]"), 1)

	def test_toggle(self):
		bufnr = 2
		# test init_checkboxes
		set_vim_buffer(buf=self.c1, bufnr=bufnr)
		h = ORGMODE.get_document(bufnr=bufnr).current_heading()
		h.init_checkboxes()

		# toggle checkbox
		c = h.current_checkbox(position=4)
		c.toggle()
		self.assertEqual(str(c), "        - [X] checkbox3")
		c.toggle()
		self.assertEqual(str(c), "        - [ ] checkbox3")

		(total, on) = c.all_siblings_status()
		self.assertEqual((total, on), (2, 1))

	def test_subtasks(self):
		bufnr = 3
		set_vim_buffer(buf=self.c1, bufnr=bufnr)
		h = ORGMODE.get_document(bufnr=bufnr).current_heading()
		h.init_checkboxes()
		c = h.current_checkbox(position=3)
		c.toggle()
		c = h.current_checkbox(position=2)
		(total, on) = c.all_siblings_status()
		c.update_subtasks(total=total, on=on)
		self.assertEqual(str(c), "  - [-] checkbox1 [50%]")


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(CheckboxTestCase)

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = test_libheading
﻿# -*- coding: utf-8 -*-

import unittest
import sys
sys.path.append(u'../ftplugin')

from orgmode.liborgmode.headings import Heading
from orgmode.liborgmode.orgdate import OrgDate
from orgmode.liborgmode.orgdate import OrgDateTime


class TestHeadingRecognizeDatesInHeading(unittest.TestCase):

	def setUp(self):
		self.allowed_todo_states = ["TODO"]

		tmp = ["* This heading is earlier  <2011-08-24 Wed>"]
		self.h1 = Heading.parse_heading_from_data(tmp, self.allowed_todo_states)

		tmp = ["* This heading is later <2011-08-25 Thu>"]
		self.h2 = Heading.parse_heading_from_data(tmp, self.allowed_todo_states)

		tmp = ["* This heading is later <2011-08-25 Thu 10:20>"]
		self.h2_datetime = Heading.parse_heading_from_data(tmp, self.allowed_todo_states)

		tmp = ["* This heading is later <2011-08-26 Fri 10:20>"]
		self.h3 = Heading.parse_heading_from_data(tmp, self.allowed_todo_states)

		tmp = ["* This heading has no date and should be later than the rest"]
		self.h_no_date = Heading.parse_heading_from_data(tmp,
				self.allowed_todo_states)

	def test_heading_parsing_no_date(self):
		"""""
		'text' doesn't contain any valid date.
		"""
		text = ["* TODO This is a test :hallo:"]
		h = Heading.parse_heading_from_data(text, self.allowed_todo_states)
		self.assertEqual(None, h.active_date)

		text = ["* TODO This is a test <2011-08-25>"]
		h = Heading.parse_heading_from_data(text, self.allowed_todo_states)
		self.assertEqual(None, h.active_date)

		text = ["* TODO This is a test <2011-08-25 Wednesday>"]
		h = Heading.parse_heading_from_data(text, self.allowed_todo_states)
		self.assertEqual(None, h.active_date)

		text = ["* TODO This is a test <20110825>"]
		h = Heading.parse_heading_from_data(text, self.allowed_todo_states)
		self.assertEqual(None, h.active_date)

	def test_heading_parsing_with_date(self):
		"""""
		'text' does contain valid dates.
		"""
		# orgdate
		text = ["* TODO This is a test <2011-08-24 Wed> :hallo:"]
		odate = OrgDate(True, 2011, 8, 24)
		h = Heading.parse_heading_from_data(text, self.allowed_todo_states)
		self.assertEqual(odate, h.active_date)

		# orgdatetime
		text = ["* TODO This is a test <2011-08-25 Thu 10:10> :hallo:"]
		odate = OrgDateTime(True, 2011, 8, 25, 10, 10)
		h = Heading.parse_heading_from_data(text, self.allowed_todo_states)
		self.assertEqual(odate, h.active_date)

	def test_heading_parsing_with_date_and_body(self):
		"""""
		'text' contains valid dates (in the body).
		"""
		# orgdatetime
		text = ["* TODO This is a test <2011-08-25 Thu 10:10> :hallo:",
				"some body text",
				"some body text"]
		h = Heading.parse_heading_from_data(text, self.allowed_todo_states)
		self.assertTrue(isinstance(h.active_date, OrgDateTime))
		self.assertEqual("<2011-08-25 Thu 10:10>", str(h.active_date))

		text = ["* TODO This is a test  :hallo:",
				"some body text",
				"some body text<2011-08-25 Thu 10:10>"]
		h = Heading.parse_heading_from_data(text, self.allowed_todo_states)
		self.assertTrue(isinstance(h.active_date, OrgDateTime))
		self.assertEqual("<2011-08-25 Thu 10:10>", str(h.active_date))

		text = ["* TODO This is a test  :hallo:",
				"some body text <2011-08-24 Wed>",
				"some body text<2011-08-25 Thu 10:10>"]
		h = Heading.parse_heading_from_data(text, self.allowed_todo_states)
		odate = OrgDate(True, 2011, 8, 24)
		self.assertEqual(odate, h.active_date)

	def test_less_than_for_dates_in_heading(self):
		self.assertTrue(self.h1 < self.h2)
		self.assertTrue(self.h1 < self.h3)
		self.assertTrue(self.h1 < self.h_no_date)
		self.assertTrue(self.h2 < self.h_no_date)
		self.assertTrue(self.h2 < self.h3)
		self.assertTrue(self.h3 < self.h_no_date)

		self.assertFalse(self.h2 < self.h1)
		self.assertFalse(self.h3 < self.h2)

	def test_less_equal_for_dates_in_heading(self):
		self.assertTrue(self.h1 <= self.h2)
		self.assertTrue(self.h1 <= self.h_no_date)
		self.assertTrue(self.h2 <= self.h_no_date)
		self.assertTrue(self.h2 <= self.h2_datetime)
		self.assertTrue(self.h2 <= self.h3)

	def test_greate_than_for_dates_in_heading(self):
		self.assertTrue(self.h2 > self.h1)
		self.assertTrue(self.h_no_date > self.h1)
		self.assertTrue(self.h_no_date > self.h2)

		self.assertFalse(self.h2 > self.h2_datetime)

	def test_greate_equal_for_dates_in_heading(self):
		self.assertTrue(self.h2 >= self.h1)
		self.assertTrue(self.h_no_date >= self.h1)
		self.assertTrue(self.h_no_date >= self.h2)
		self.assertTrue(self.h2 >= self.h2_datetime)

	def test_sorting_of_headings(self):
		"""Headings should be sortable."""
		self.assertEqual([self.h1, self.h2], sorted([self.h2, self.h1]))

		self.assertEqual([self.h1, self.h2_datetime],
				sorted([self.h2_datetime, self.h1]))

		self.assertEqual([self.h2_datetime, self.h2],
				sorted([self.h2_datetime, self.h2]))

		self.assertEqual([self.h1, self.h2], sorted([self.h1, self.h2]))

		self.assertEqual([self.h1, self.h_no_date],
				sorted([self.h1, self.h_no_date]))

		self.assertEqual([self.h1, self.h_no_date],
				sorted([self.h_no_date, self.h1]))

		self.assertEqual([self.h1, self.h2, self.h_no_date],
				sorted([self.h2, self.h_no_date, self.h1]))

		self.assertEqual(
				[self.h1, self.h2_datetime, self.h2, self.h3, self.h_no_date],
				sorted([self.h2_datetime, self.h3, self.h2, self.h_no_date, self.h1]))


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(
			TestHeadingRecognizeDatesInHeading)

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = test_liborgdate
# -*- coding: utf-8 -*-


import sys
import unittest
from datetime import date

sys.path.append(u'../ftplugin')
from orgmode.liborgmode.orgdate import OrgDate


class OrgDateTestCase(unittest.TestCase):
	u"""
	Tests all the functionality of the OrgDate
	"""

	def setUp(self):
		self.date = date(2011, 8, 29)
		self.year = 2011
		self.month = 8
		self.day = 29
		self.text = u'<2011-08-29 Mon>'
		self.textinactive = u'[2011-08-29 Mon]'

	def test_OrgDate_ctor_active(self):
		u"""OrdDate should be created."""
		today = date.today()
		od = OrgDate(True, today.year, today.month, today.day)
		self.assertTrue(isinstance(od, OrgDate))
		self.assertTrue(od.active)

	def test_OrgDate_ctor_inactive(self):
		u"""OrdDate should be created."""
		today = date.today()
		od = OrgDate(False, today.year, today.month, today.day)
		self.assertTrue(isinstance(od, OrgDate))
		self.assertFalse(od.active)

	def test_OrdDate_str_active(self):
		u"""Representation of OrgDates"""
		od = OrgDate(True, self.year, self.month, self.day)
		self.assertEqual(self.text, unicode(od))

	def test_OrdDate_str_inactive(self):
		od = OrgDate(False, self.year, self.month, self.day)
		self.assertEqual(self.textinactive, unicode(od))


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(OrgDateTestCase)

# vi: noexpandtab

########NEW FILE########
__FILENAME__ = test_liborgdatetime
# -*- coding: utf-8 -*-

import sys
import unittest
from datetime import datetime

sys.path.append(u'../ftplugin')
from orgmode.liborgmode.orgdate import OrgDateTime


class OrgDateTimeTestCase(unittest.TestCase):
	u"""
	Tests all the functionality of the OrgDateTime
	"""

	def test_OrgDateTime_ctor_active(self):
		u"""OrdDateTime should be created."""
		today = datetime.today()
		odt = OrgDateTime(True, today.year, today.month, today.day, today.hour,
				today.minute)
		self.assertTrue(isinstance(odt, OrgDateTime))
		self.assertTrue(odt.active)

	def test_OrgDateTime_ctor_inactive(self):
		u"""OrdDateTime should be created."""
		today = datetime.today()
		odt = OrgDateTime(False, today.year, today.month, today.day, today.hour,
				today.minute)
		self.assertTrue(isinstance(odt, OrgDateTime))
		self.assertFalse(odt.active)

	def test_OrdDateTime_str_active(self):
		u"""Representation of OrgDateTime"""
		t = 2011, 9, 8, 10, 20
		odt = OrgDateTime(False, t[0], t[1], t[2], t[3], t[4])
		self.assertEqual(u"[2011-09-08 Thu 10:20]", unicode(odt))

	def test_OrdDateTime_str_inactive(self):
		u"""Representation of OrgDateTime"""
		t = 2011, 9, 8, 10, 20
		odt = OrgDateTime(True, t[0], t[1], t[2], t[3], t[4])
		self.assertEqual(u"<2011-09-08 Thu 10:20>", unicode(odt))


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(OrgDateTimeTestCase)


# vim: noexpandtab

########NEW FILE########
__FILENAME__ = test_liborgdate_parsing
# -*- coding: utf-8 -*-


import sys
import unittest

sys.path.append(u'../ftplugin')
from orgmode.liborgmode.orgdate import get_orgdate
from orgmode.liborgmode.orgdate import OrgDate
from orgmode.liborgmode.orgdate import OrgDateTime
from orgmode.liborgmode.orgdate import OrgTimeRange


class OrgDateParsingTestCase(unittest.TestCase):
	u"""
	Tests the functionality of the parsing function of OrgDate.

	Mostly function get_orgdate().
	"""

	def setUp(self):
		self.text = u'<2011-08-29 Mon>'
		self.textinactive = u'[2011-08-29 Mon]'

	def test_get_orgdate_parsing_active(self):
		u"""
		get_orgdate should recognice all orgdates in a given text
		"""
		result = get_orgdate(self.text)
		self.assertNotEqual(result, None)
		self.assertTrue(isinstance(result, OrgDate))
		self.assertTrue(isinstance(get_orgdate(u"<2011-08-30 Tue>"), OrgDate))
		self.assertEqual(get_orgdate(u"<2011-08-30 Tue>").year, 2011)
		self.assertEqual(get_orgdate(u"<2011-08-30 Tue>").month, 8)
		self.assertEqual(get_orgdate(u"<2011-08-30 Tue>").day, 30)
		self.assertTrue(get_orgdate(u"<2011-08-30 Tue>").active)

		datestr = u"This date <2011-08-30 Tue> is embedded"
		self.assertTrue(isinstance(get_orgdate(datestr), OrgDate))

	def test_get_orgdatetime_parsing_active(self):
		u"""
		get_orgdate should recognice all orgdatetimess in a given text
		"""
		result = get_orgdate(u"<2011-09-12 Mon 10:20>")
		self.assertNotEqual(result, None)
		self.assertTrue(isinstance(result, OrgDateTime))
		self.assertEqual(result.year, 2011)
		self.assertEqual(result.month, 9)
		self.assertEqual(result.day, 12)
		self.assertEqual(result.hour, 10)
		self.assertEqual(result.minute, 20)
		self.assertTrue(result.active)

		result = get_orgdate(u"some datetime <2011-09-12 Mon 10:20> stuff")
		self.assertTrue(isinstance(result, OrgDateTime))

	def test_get_orgtimerange_parsing_active(self):
		u"""
		get_orgdate should recognice all orgtimeranges in a given text
		"""
		daterangestr = u"<2011-09-12 Mon>--<2011-09-13 Tue>"
		result = get_orgdate(daterangestr)
		self.assertNotEqual(result, None)
		self.assertTrue(isinstance(result, OrgTimeRange))
		self.assertEqual(unicode(result), daterangestr)
		self.assertTrue(result.active)

		daterangestr = u"<2011-09-12 Mon 10:20>--<2011-09-13 Tue 13:20>"
		result = get_orgdate(daterangestr)
		self.assertNotEqual(result, None)
		self.assertTrue(isinstance(result, OrgTimeRange))
		self.assertEqual(unicode(result), daterangestr)
		self.assertTrue(result.active)

		daterangestr = u"<2011-09-12 Mon 10:20-13:20>"
		result = get_orgdate(daterangestr)
		self.assertNotEqual(result, None)
		self.assertTrue(isinstance(result, OrgTimeRange))
		self.assertEqual(unicode(result), daterangestr)
		self.assertTrue(result.active)

	def test_get_orgdate_parsing_inactive(self):
		u"""
		get_orgdate should recognice all inactive orgdates in a given text
		"""
		result = get_orgdate(self.textinactive)
		self.assertNotEqual(result, None)
		self.assertTrue(isinstance(result, OrgDate))
		self.assertTrue(isinstance(get_orgdate(u"[2011-08-30 Tue]"), OrgDate))
		self.assertEqual(get_orgdate(u"[2011-08-30 Tue]").year, 2011)
		self.assertEqual(get_orgdate(u"[2011-08-30 Tue]").month, 8)
		self.assertEqual(get_orgdate(u"[2011-08-30 Tue]").day, 30)
		self.assertFalse(get_orgdate(u"[2011-08-30 Tue]").active)

		datestr = u"This date [2011-08-30 Tue] is embedded"
		self.assertTrue(isinstance(get_orgdate(datestr), OrgDate))

	def test_get_orgdatetime_parsing_passive(self):
		u"""
		get_orgdate should recognice all orgdatetimess in a given text
		"""
		result = get_orgdate(u"[2011-09-12 Mon 10:20]")
		self.assertNotEqual(result, None)
		self.assertTrue(isinstance(result, OrgDateTime))
		self.assertEqual(result.year, 2011)
		self.assertEqual(result.month, 9)
		self.assertEqual(result.day, 12)
		self.assertEqual(result.hour, 10)
		self.assertEqual(result.minute, 20)
		self.assertFalse(result.active)

		result = get_orgdate(u"some datetime [2011-09-12 Mon 10:20] stuff")
		self.assertTrue(isinstance(result, OrgDateTime))

	def test_get_orgdate_parsing_with_list_of_texts(self):
		u"""
		get_orgdate should return the first date in the list.
		"""
		datelist = [u"<2011-08-29 Mon>"]
		result = get_orgdate(datelist)
		self.assertNotEquals(result, None)
		self.assertTrue(isinstance(result, OrgDate))
		self.assertEqual(result.year, 2011)
		self.assertEqual(result.month, 8)
		self.assertEqual(result.day, 29)

		datelist = [u"<2011-08-29 Mon>",
				u"<2012-03-30 Fri>"]
		result = get_orgdate(datelist)
		self.assertNotEquals(result, None)
		self.assertTrue(isinstance(result, OrgDate))
		self.assertEqual(result.year, 2011)
		self.assertEqual(result.month, 8)
		self.assertEqual(result.day, 29)

		datelist = [u"some <2011-08-29 Mon>text",
				u"<2012-03-30 Fri> is here"]
		result = get_orgdate(datelist)
		self.assertNotEquals(result, None)
		self.assertTrue(isinstance(result, OrgDate))
		self.assertEqual(result.year, 2011)
		self.assertEqual(result.month, 8)
		self.assertEqual(result.day, 29)

		datelist = [u"here is no date",
				u"some <2011-08-29 Mon>text",
				u"<2012-03-30 Fri> is here"]
		result = get_orgdate(datelist)
		self.assertNotEquals(result, None)
		self.assertTrue(isinstance(result, OrgDate))
		self.assertEqual(result.year, 2011)
		self.assertEqual(result.month, 8)
		self.assertEqual(result.day, 29)

		datelist = [u"here is no date",
				u"some <2011-08-29 Mon 20:10> text",
				u"<2012-03-30 Fri> is here"]
		result = get_orgdate(datelist)
		self.assertNotEquals(result, None)
		self.assertTrue(isinstance(result, OrgDateTime))
		self.assertEqual(result.year, 2011)
		self.assertEqual(result.month, 8)
		self.assertEqual(result.day, 29)
		self.assertEqual(result.hour, 20)
		self.assertEqual(result.minute, 10)

	def test_get_orgdate_parsing_with_invalid_input(self):
		self.assertEquals(get_orgdate(u"NONSENSE"), None)
		self.assertEquals(get_orgdate(u"No D<2011- Date 08-29 Mon>"), None)
		self.assertEquals(get_orgdate(u"2011-08-r9 Mon]"), None)
		self.assertEquals(get_orgdate(u"<2011-08-29 Mon"), None)
		self.assertEquals(get_orgdate(u"<2011-08-29 Mon]"), None)
		self.assertEquals(get_orgdate(u"2011-08-29 Mon"), None)
		self.assertEquals(get_orgdate(u"2011-08-29"), None)
		self.assertEquals(get_orgdate(u"2011-08-29 mon"), None)
		self.assertEquals(get_orgdate(u"<2011-08-29 mon>"), None)

		self.assertEquals(get_orgdate(u"wrong date embedded <2011-08-29 mon>"), None)
		self.assertEquals(get_orgdate(u"wrong date <2011-08-29 mon>embedded "), None)

	def test_get_orgdate_parsing_with_invalid_dates(self):
		u"""
		Something like <2011-14-29 Mon> (invalid dates, they don't exist)
		should not be parsed
		"""
		datestr = u"<2011-14-30 Tue>"
		self.assertEqual(get_orgdate(datestr), None)

		datestr = u"<2012-03-40 Tue>"
		self.assertEqual(get_orgdate(datestr), None)

		datestr = u"<2012-03-40 Tue 24:70>"
		self.assertEqual(get_orgdate(datestr), None)


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(OrgDateParsingTestCase)

# vim: noexpandtab

########NEW FILE########
__FILENAME__ = test_liborgtimerange
# -*- coding: utf-8 -*-


import sys
import unittest
from datetime import date
from datetime import datetime

sys.path.append(u'../ftplugin')
from orgmode.liborgmode.orgdate import OrgTimeRange


class OrgTimeRangeTestCase(unittest.TestCase):

	def setUp(self):
		self.date = date(2011, 8, 29)
		self.year = 2011
		self.month = 8
		self.day = 29
		self.text = '<2011-08-29 Mon>'
		self.textinactive = '[2011-08-29 Mon]'

	def test_OrgTimeRange_ctor_active(self):
		u"""
		timerange should be created.
		"""
		start = date(2011, 9 , 12)
		end = date(2011, 9 , 13)
		timerange = OrgTimeRange(True, start, end)
		self.assertTrue(isinstance(timerange, OrgTimeRange))
		self.assertTrue(timerange.active)

	def test_OrgTimeRange_ctor_inactive(self):
		u"""
		timerange should be created.
		"""
		start = date(2011, 9 , 12)
		end = date(2011, 9 , 13)
		timerange = OrgTimeRange(False, start, end)
		self.assertTrue(isinstance(timerange, OrgTimeRange))
		self.assertFalse(timerange.active)

	def test_OrdDate_str_active(self):
		u"""Representation of OrgDates"""
		start = date(2011, 9 , 12)
		end = date(2011, 9 , 13)
		timerange = OrgTimeRange(True, start, end)
		expected = "<2011-09-12 Mon>--<2011-09-13 Tue>"
		self.assertEqual(str(timerange), expected)

		start = datetime(2011, 9 , 12, 20, 00)
		end = datetime(2011, 9 , 13, 21, 59)
		timerange = OrgTimeRange(True, start, end)
		expected = "<2011-09-12 Mon 20:00>--<2011-09-13 Tue 21:59>"
		self.assertEqual(str(timerange), expected)

		start = datetime(2011, 9 , 12, 20, 00)
		end = datetime(2011, 9 , 12, 21, 00)
		timerange = OrgTimeRange(True, start, end)
		expected = "<2011-09-12 Mon 20:00-21:00>"
		self.assertEqual(str(timerange), expected)

	def test_OrdDate_str_inactive(self):
		u"""Representation of OrgDates"""
		start = date(2011, 9 , 12)
		end = date(2011, 9 , 13)
		timerange = OrgTimeRange(False, start, end)
		expected = "[2011-09-12 Mon]--[2011-09-13 Tue]"
		self.assertEqual(str(timerange), expected)

		start = datetime(2011, 9 , 12, 20, 00)
		end = datetime(2011, 9 , 13, 21, 59)
		timerange = OrgTimeRange(False, start, end)
		expected = "[2011-09-12 Mon 20:00]--[2011-09-13 Tue 21:59]"
		self.assertEqual(str(timerange), expected)

		start = datetime(2011, 9 , 12, 20, 00)
		end = datetime(2011, 9 , 12, 21, 00)
		timerange = OrgTimeRange(False, start, end)
		expected = "[2011-09-12 Mon 20:00-21:00]"
		self.assertEqual(str(timerange), expected)

def suite():
	return unittest.TestLoader().loadTestsFromTestCase(OrgTimeRangeTestCase)

# vim: noexpandtab

########NEW FILE########
__FILENAME__ = test_plugin_date
# -*- coding: utf-8 -*-

import unittest
import sys
sys.path.append(u'../ftplugin')

from datetime import date
from datetime import datetime

from orgmode.plugins.Date import Date


class DateTestCase(unittest.TestCase):
	u"""Tests all the functionality of the Date plugin.

	Also see:
	http://orgmode.org/manual/The-date_002ftime-prompt.html#The-date_002ftime-prompt
	"""

	def setUp(self):
		self.d = date(2011, 5, 22)

	def test_modify_time_with_None(self):
		# no modification should happen
		res = Date._modify_time(self.d, None)
		self.assertEquals(self.d, res)

	def test_modify_time_with_dot(self):
		# no modification should happen
		res = Date._modify_time(self.d, u'.')
		self.assertEquals(self.d, res)

	def test_modify_time_with_given_relative_days(self):
		# modifier and expected result
		test_data = [(u'+0d', self.d),
				(u'+1d', date(2011, 5, 23)),
				(u'+2d', date(2011, 5, 24)),
				(u'+7d', date(2011, 5, 29)),
				(u'+9d', date(2011, 5, 31)),
				(u'+10d', date(2011, 6, 1)),
				(u'7d', self.d)]  # wrong format: plus is missing

		for modifier, expected in test_data:
			self.assertEquals(expected, Date._modify_time(self.d, modifier))

	def test_modify_time_with_given_relative_days_without_d(self):
		# modifier and expected result
		test_data = [(u'+0', self.d),
				(u'+1', date(2011, 5, 23)),
				(u'+2', date(2011, 5, 24)),
				(u'+7', date(2011, 5, 29)),
				(u'+9', date(2011, 5, 31)),
				(u'+10', date(2011, 6, 1))]

		for modifier, expected in test_data:
			result = Date._modify_time(self.d, modifier)
			self.assertEquals(expected, result)

	def test_modify_time_with_given_relative_weeks(self):
		# modifier and expected result
		test_data = [(u'+1w', date(2011, 5, 29)),
				(u'+2w', date(2011, 6, 5)),
				(u'+3w', date(2011, 6, 12)),
				(u'+3w', date(2011, 6, 12)),
				(u'+0w', self.d),
				(u'3w', self.d),  # wrong format
				(u'+w', self.d)]  # wrong format

		for modifier, expected in test_data:
			self.assertEquals(expected, Date._modify_time(self.d, modifier))

	def test_modify_time_with_given_relative_months(self):
		test_data = [(u'+0m', self.d),
				(u'+1m', date(2011, 6, 22)),
				(u'+2m', date(2011, 7, 22))]

		for modifier, expected in test_data:
			self.assertEquals(expected, Date._modify_time(self.d, modifier))

	def test_modify_time_with_given_relative_years(self):
		test_data = [(u'+1y', date(2012, 5, 22)),
				(u'+10y', date(2021, 5, 22)),
				(u'+0y', self.d)]

		for modifier, expected in test_data:
			self.assertEquals(expected, Date._modify_time(self.d, modifier))


	def test_modify_time_with_given_weekday(self):
		# use custom day instead of self.d to ease testing
		cust_day = date(2011, 5, 25)  # it's a Wednesday
		#print cust_day.weekday()  # 2
		test_data = [(u'Thu', date(2011, 5, 26)),
				(u'thu', date(2011, 5, 26)),
				(u'tHU', date(2011, 5, 26)),
				(u'THU', date(2011, 5, 26)),
				(u'Fri', date(2011, 5, 27)),
				(u'sat', date(2011, 5, 28)),
				(u'sun', date(2011, 5, 29)),
				(u'mon', date(2011, 5, 30)),
				(u'tue', date(2011, 5, 31)),
				(u'wed', date(2011, 6, 1))]

		for modifier, expected in test_data:
			self.assertEquals(expected, Date._modify_time(cust_day, modifier))

	def test_modify_time_with_month_and_day(self):
		cust_date = date(2006, 6, 13)
		test_data = [(u'sep 15', date(2006, 9, 15)),
				(u'Sep 15', date(2006, 9, 15)),
				(u'SEP 15', date(2006, 9, 15)),
				(u'feb 15', date(2007, 2, 15)),
				(u'jan 1', date(2007, 1, 1)),
				(u'7/5', date(2006, 07, 05)),
				(u'2/5', date(2007, 02, 05)),]

		for modifier, expected in test_data:
			self.assertEquals(expected, Date._modify_time(cust_date, modifier))

	def test_modify_time_with_time(self):
		cust_date = date(2006, 6, 13)
		test_data = [(u'12:45', datetime(2006, 06, 13, 12, 45)),
				(u'1:45', datetime(2006, 06, 13, 1, 45)),
				(u'1:05', datetime(2006, 06, 13, 1, 5)),]

		for modifier, expected in test_data:
			res = Date._modify_time(cust_date, modifier)
			self.assertTrue(isinstance(res, datetime))
			self.assertEquals(expected, res)

	def test_modify_time_with_full_dates(self):
		result = Date._modify_time(self.d, u'2011-01-12')
		expected = date(2011, 1, 12)
		self.assertEquals(expected, result)

		reults = Date._modify_time(self.d, u'2015-03-12')
		expected = date(2015, 3, 12)
		self.assertEquals(expected, reults)

		cust_date = date(2006, 6, 13)
		test_data = [(u'3-2-5', date(2003, 2, 05)),
				(u'12-2-28', date(2012, 2, 28)),
				(u'2/5/3', date(2003, 02, 05)),
				(u'sep 12 9', date(2009, 9, 12)),
				(u'jan 2 99', date(2099, 1, 2)),]

		for modifier, expected in test_data:
			self.assertEquals(expected, Date._modify_time(cust_date, modifier))

	def test_modify_time_with_only_days(self):
		cust_date = date(2006, 6, 13)
		test_data = [(u'14', date(2006, 06, 14)),
				(u'12', date(2006, 07, 12)),
				(u'1', date(2006, 07, 1)),
				(u'29', date(2006, 06, 29)),]
		for modifier, expected in test_data:
			self.assertEquals(expected, Date._modify_time(cust_date, modifier))

	def test_modify_time_with_day_and_time(self):
		cust_date = date(2006, 6, 13)
		test_data = [(u'+1 10:20', datetime(2006, 06, 14, 10, 20)),
				(u'+1w 10:20', datetime(2006, 06, 20, 10, 20)),
				(u'+2 10:30', datetime(2006, 06, 15, 10, 30)),
				(u'+2d 10:30', datetime(2006, 06, 15, 10, 30))]
		for modifier, expected in test_data:
			result = Date._modify_time(cust_date, modifier)
			self.assertEquals(expected, result)

def suite():
	return unittest.TestLoader().loadTestsFromTestCase(DateTestCase)

# vi: noexpandtab

########NEW FILE########
__FILENAME__ = test_plugin_edit_checkbox
# -*- coding: utf-8 -*-

import unittest
import sys
sys.path.append(u'../ftplugin')

import vim

from orgmode._vim import ORGMODE

PLUGIN_NAME = u'EditCheckbox'

bufnr = 10

def set_vim_buffer(buf=None, cursor=(2, 0), bufnr=0):
	if buf is None:
		buf = []
	vim.current.buffer[:] = buf
	vim.current.window.cursor = cursor
	vim.current.buffer.number = bufnr


class EditCheckboxTestCase(unittest.TestCase):
	def setUp(self):
		if PLUGIN_NAME not in ORGMODE.plugins:
			ORGMODE.register_plugin(PLUGIN_NAME)
		self.editcheckbox = ORGMODE.plugins[PLUGIN_NAME]

		self.c1 = u"""
* heading1 [%]
  - [ ] checkbox1 [/]
        - [ ] checkbox2
        - [ ] checkbox3
              - [ ] checkbox4
  - [ ] checkbox5
        - [ ] checkbox6
              - [ ] checkbox7
              - [ ] checkbox8
""".split(u'\n')

		self.c2 = u"""
* a checkbox list [%]
  - checkbox [0%]
        - [ ] test1
        - [ ] test2
        - [ ] test3
""".split(u'\n')

		self.c3 = u"""
* heading
  1. [ ] another main task [%]
         - [ ] sub task 1
         - [ ] sub task 2
  2. [ ] another main task
""".split(u'\n')

	def test_toggle(self):
		global bufnr
		bufnr += 1
		# test on self.c1
		set_vim_buffer(buf=self.c1, cursor=(6, 0), bufnr=bufnr)
		# update_checkboxes_status
		self.editcheckbox.update_checkboxes_status()
		self.assertEqual(vim.current.buffer[1], "* heading1 [0%]")
		# toggle
		self.editcheckbox.toggle()
		self.assertEqual(vim.current.buffer[5], "              - [X] checkbox4")

		bufnr += 1
		set_vim_buffer(buf=self.c1, cursor=(9, 0), bufnr=bufnr)
		# toggle and check checkbox status
		self.editcheckbox.toggle()
		self.assertEqual(vim.current.buffer[8], "              - [X] checkbox7")
		self.assertEqual(vim.current.buffer[7], "        - [-] checkbox6")
		self.assertEqual(vim.current.buffer[6], "  - [-] checkbox5")

		# new_checkbox
		vim.current.window.cursor = (10, 0)
		self.editcheckbox.new_checkbox(below=True)
		self.assertEqual(vim.current.buffer[10], '              - [ ] ')
		self.editcheckbox.update_checkboxes_status()

	def test_no_status_checkbox(self):
		global bufnr
		bufnr += 1
		# test on self.c2
		set_vim_buffer(buf=self.c2, bufnr=bufnr)
		self.assertEqual(vim.current.buffer[2], "  - checkbox [0%]")
		# toggle
		vim.current.window.cursor = (4, 0)
		self.editcheckbox.toggle()
		self.assertEqual(vim.current.buffer[3], "        - [X] test1")

		# self.editcheckbox.update_checkboxes_status()
		# see if the no status checkbox update its status
		self.assertEqual(vim.current.buffer[2], "  - checkbox [33%]")

	def test_number_list(self):
		global bufnr
		bufnr += 1
		set_vim_buffer(buf=self.c3, bufnr=bufnr)
		vim.current.window.cursor = (6, 0)
		self.editcheckbox.toggle()
		self.assertEqual(vim.current.buffer[5], "  2. [X] another main task")


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(EditCheckboxTestCase)

# vim: set noexpandtab:

########NEW FILE########
__FILENAME__ = test_plugin_edit_structure
# -*- coding: utf-8 -*-

import unittest
import sys
sys.path.append(u'../ftplugin')

import vim

from orgmode._vim import ORGMODE

counter = 0
class EditStructureTestCase(unittest.TestCase):
	def setUp(self):
		global counter
		counter += 1
		vim.CMDHISTORY = []
		vim.CMDRESULTS = {}
		vim.EVALHISTORY = []
		vim.EVALRESULTS = {
				# no org_todo_keywords for b
				u'exists("b:org_todo_keywords")'.encode(u'utf-8'): '0'.encode(u'utf-8'),
				# global values for org_todo_keywords
				u'exists("g:org_todo_keywords")'.encode(u'utf-8'): '1'.encode(u'utf-8'),
				u'g:org_todo_keywords'.encode(u'utf-8'): [u'TODO'.encode(u'utf-8'), u'DONE'.encode(u'utf-8'), u'|'.encode(u'utf-8')],
				u'exists("g:org_improve_split_heading")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("b:org_improve_split_heading")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("b:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("*repeat#set()")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'b:changedtick'.encode(u'utf-8'): (u'%d' % counter).encode(u'utf-8'),
				u'&ts'.encode(u'utf-8'): u'8'.encode(u'utf-8'),
				u'exists("g:org_tag_column")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("b:org_tag_column")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u"v:count".encode(u'utf-8'): u'0'.encode(u'utf-8')}
		if not u'EditStructure' in ORGMODE.plugins:
			ORGMODE.register_plugin(u'EditStructure')
		self.editstructure = ORGMODE.plugins[u'EditStructure']
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* Überschrift 1
Text 1

Bla bla
** Überschrift 1.1
Text 2

Bla Bla bla
** Überschrift 1.2
Text 3

**** Überschrift 1.2.1.falsch

Bla Bla bla bla
*** Überschrift 1.2.1
* Überschrift 2
* Überschrift 3
  asdf sdf
""".split(u'\n')]

	def test_new_heading_below_normal_behavior(self):
		vim.current.window.cursor = (1, 0)
		self.assertNotEqual(self.editstructure.new_heading(below=True), None)
		self.assertEqual(vim.current.buffer[0], u'* '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1'.encode(u'utf-8'))

	def test_new_heading_above_normal_behavior(self):
		vim.current.window.cursor = (1, 1)
		self.assertNotEqual(self.editstructure.new_heading(below=False), None)
		self.assertEqual(vim.current.buffer[0], u'* '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1'.encode(u'utf-8'))

	def test_new_heading_below(self):
		vim.current.window.cursor = (2, 0)
		vim.current.buffer[5] = u'** Überschrift 1.1 :Tag:'.encode(u'utf-8')
		self.assertNotEqual(self.editstructure.new_heading(below=True, insert_mode=False), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 6gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[4], u'Bla bla'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[5], u'* '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[6], u'** Überschrift 1.1 :Tag:'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[10], u'** Überschrift 1.2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[13], u'**** Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'*** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[17], u'* Überschrift 2'.encode(u'utf-8'))

	def test_new_heading_below_insert_mode(self):
		vim.current.window.cursor = (2, 1)
		self.assertNotEqual(self.editstructure.new_heading(below=True, insert_mode=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 3gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[2], u'* Überschrift 1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[5], u'Bla bla'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[6], u'** Überschrift 1.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[10], u'** Überschrift 1.2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[13], u'**** Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'*** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[17], u'* Überschrift 2'.encode(u'utf-8'))

	def test_new_heading_below_split_text_at_the_end(self):
		vim.current.buffer[1] = u'* Überschriftx1'.encode(u'utf-8')
		vim.current.window.cursor = (2, 14)
		self.assertNotEqual(self.editstructure.new_heading(below=True, insert_mode=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 3gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[2], u'* '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[5], u'Bla bla'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[6], u'** Überschrift 1.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[10], u'** Überschrift 1.2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[13], u'**** Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'*** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[17], u'* Überschrift 2'.encode(u'utf-8'))

	def test_new_heading_below_split_text_at_the_end_insert_parts(self):
		vim.current.window.cursor = (2, 14)
		self.assertNotEqual(self.editstructure.new_heading(below=True, insert_mode=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 3gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[2], u'* 1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[5], u'Bla bla'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[6], u'** Überschrift 1.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[10], u'** Überschrift 1.2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[13], u'**** Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'*** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[17], u'* Überschrift 2'.encode(u'utf-8'))

	def test_new_heading_below_in_the_middle(self):
		vim.current.window.cursor = (10, 0)
		self.assertNotEqual(self.editstructure.new_heading(below=True, insert_mode=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 13gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[11], u''.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[12], u'** '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[13], u'**** Überschrift 1.2.1.falsch'.encode(u'utf-8'))

	def test_new_heading_below_in_the_middle2(self):
		vim.current.window.cursor = (13, 0)
		self.assertNotEqual(self.editstructure.new_heading(below=True, insert_mode=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 16gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[14], u'Bla Bla bla bla'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[15], u'**** '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'*** Überschrift 1.2.1'.encode(u'utf-8'))

	def test_new_heading_below_in_the_middle3(self):
		vim.current.window.cursor = (16, 0)
		self.assertNotEqual(self.editstructure.new_heading(below=True, insert_mode=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 17gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[15], u'*** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'*** '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[17], u'* Überschrift 2'.encode(u'utf-8'))

	def test_new_heading_below_at_the_end(self):
		vim.current.window.cursor = (18, 0)
		self.assertNotEqual(self.editstructure.new_heading(below=True, insert_mode=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 21gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[19], u''.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[20], u'* '.encode(u'utf-8'))
		self.assertEqual(len(vim.current.buffer), 21)

	def test_new_heading_above(self):
		vim.current.window.cursor = (2, 0)
		self.assertNotEqual(self.editstructure.new_heading(below=False, insert_mode=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 2gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[0], u''.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[1], u'* '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[2], u'* Überschrift 1'.encode(u'utf-8'))

	def test_new_heading_above_in_the_middle(self):
		vim.current.window.cursor = (10, 0)
		self.assertNotEqual(self.editstructure.new_heading(below=False, insert_mode=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 10gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[8], u'Bla Bla bla'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[9], u'** '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[10], u'** Überschrift 1.2'.encode(u'utf-8'))

	def test_new_heading_above_in_the_middle2(self):
		vim.current.window.cursor = (13, 0)
		self.assertNotEqual(self.editstructure.new_heading(below=False, insert_mode=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 13gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[11], u''.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[12], u'**** '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[13], u'**** Überschrift 1.2.1.falsch'.encode(u'utf-8'))

	def test_new_heading_above_in_the_middle3(self):
		vim.current.window.cursor = (16, 0)
		self.assertNotEqual(self.editstructure.new_heading(below=False, insert_mode=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 16gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[14], u'Bla Bla bla bla'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[15], u'*** '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'*** Überschrift 1.2.1'.encode(u'utf-8'))

	def test_new_heading_above_at_the_end(self):
		vim.current.window.cursor = (18, 0)
		self.assertNotEqual(self.editstructure.new_heading(below=False, insert_mode=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 18gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'* Überschrift 2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[17], u'* '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[18], u'* Überschrift 3'.encode(u'utf-8'))

	def test_new_heading_below_split_heading_title(self):
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* Überschrift 1  :Tag:
Text 1

Bla bla
** Überschrift 1.1
Text 2

Bla Bla bla
** Überschrift 1.2
Text 3

**** Überschrift 1.2.1.falsch

Bla Bla bla bla
*** Überschrift 1.2.1
* Überschrift 2
* Überschrift 3
  asdf sdf
""".split(u'\n')]
		vim.current.window.cursor = (2, 6)
		self.assertNotEqual(self.editstructure.new_heading(insert_mode=True), None)
		self.assertEqual(vim.current.buffer[0], u''.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[1], u'* Über									:Tag:'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[2], u'* schrift 1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[3], u'Text 1'.encode(u'utf-8'))

	def test_new_heading_below_split_heading_title_with_todo(self):
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* TODO Überschrift 1  :Tag:
Text 1

Bla bla
** Überschrift 1.1
Text 2

Bla Bla bla
** Überschrift 1.2
Text 3

**** Überschrift 1.2.1.falsch

Bla Bla bla bla
*** Überschrift 1.2.1
* Überschrift 2
* Überschrift 3
  asdf sdf
""".split(u'\n')]
		vim.current.window.cursor = (2, 5)
		self.assertNotEqual(self.editstructure.new_heading(insert_mode=True), None)
		self.assertEqual(vim.current.buffer[0], u''.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[1], u'* TODO									:Tag:'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[2], u'* Überschrift 1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[3], u'Text 1'.encode(u'utf-8'))

	def test_demote_heading(self):
		vim.current.window.cursor = (13, 0)
		self.assertNotEqual(self.editstructure.demote_heading(), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal 13ggV15gg='.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[10], u'Text 3'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[11], u''.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[12], u'***** Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[13], u''.encode(u'utf-8'))
		# actually the indentation comes through vim, just the heading is updated
		self.assertEqual(vim.current.buffer[14], u'Bla Bla bla bla'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[15], u'*** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (13, 1))

	def test_demote_newly_created_level_one_heading(self):
		vim.current.window.cursor = (2, 0)
		self.assertNotEqual(self.editstructure.new_heading(below=True), None)
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[5], u'* '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[6], u'** Überschrift 1.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[10], u'** Überschrift 1.2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[13], u'**** Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'*** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[17], u'* Überschrift 2'.encode(u'utf-8'))

		vim.current.window.cursor = (6, 2)
		self.assertNotEqual(self.editstructure.demote_heading(), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal 6ggV17gg='.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[5], u'** '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[6], u'*** Überschrift 1.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[10], u'*** Überschrift 1.2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[13], u'***** Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'**** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[17], u'* Überschrift 2'.encode(u'utf-8'))

	def test_demote_newly_created_level_two_heading(self):
		vim.current.window.cursor = (10, 0)
		self.assertNotEqual(self.editstructure.new_heading(below=True), None)
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[5], u'** Überschrift 1.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[9], u'** Überschrift 1.2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[12], u'** '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[13], u'**** Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'*** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[17], u'* Überschrift 2'.encode(u'utf-8'))

		vim.current.window.cursor = (13, 3)
		self.assertNotEqual(self.editstructure.demote_heading(including_children=False, on_heading=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'exe "normal 13gg"|startinsert!'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[5], u'** Überschrift 1.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[9], u'** Überschrift 1.2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[12], u'*** '.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[13], u'**** Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'*** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[17], u'* Überschrift 2'.encode(u'utf-8'))

	def test_demote_last_heading(self):
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* Überschrift 2
* Überschrift 3""".split('\n')]
		vim.current.window.cursor = (3, 0)
		h = ORGMODE.get_document().current_heading()
		self.assertNotEqual(self.editstructure.demote_heading(), None)
		self.assertEqual(h.end, 2)
		self.assertFalse(vim.CMDHISTORY)
		self.assertEqual(vim.current.buffer[2], u'** Überschrift 3'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (3, 1))

	def test_promote_heading(self):
		vim.current.window.cursor = (13, 0)
		self.assertNotEqual(self.editstructure.promote_heading(), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal 13ggV15gg='.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[10], u'Text 3'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[11], u''.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[12], u'*** Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[13], u''.encode(u'utf-8'))
		# actually the indentation comes through vim, just the heading is updated
		self.assertEqual(vim.current.buffer[14], u'Bla Bla bla bla'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[15], u'*** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (13, -1))

	def test_promote_level_one_heading(self):
		vim.current.window.cursor = (2, 0)
		self.assertEqual(self.editstructure.promote_heading(), None)
		self.assertEqual(len(vim.CMDHISTORY), 0)
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_demote_parent_heading(self):
		vim.current.window.cursor = (2, 0)
		self.assertNotEqual(self.editstructure.demote_heading(), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal 2ggV16gg='.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[1], u'** Überschrift 1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[5], u'*** Überschrift 1.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[9], u'*** Überschrift 1.2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[12], u'***** Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[15], u'**** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'* Überschrift 2'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 1))

	def test_promote_parent_heading(self):
		vim.current.window.cursor = (10, 0)
		self.assertNotEqual(self.editstructure.promote_heading(), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal 10ggV16gg='.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[5], u'** Überschrift 1.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[9], u'* Überschrift 1.2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[12], u'*** Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[15], u'** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'* Überschrift 2'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (10, -1))

	# run tests with count
	def test_demote_parent_heading_count(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u"v:count"] = u'3'.encode(u'utf-8')
		self.assertNotEqual(self.editstructure.demote_heading(), None)
		self.assertEqual(len(vim.CMDHISTORY), 3)
		self.assertEqual(vim.CMDHISTORY[-3], u'normal 2ggV16gg='.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-2], u'normal 2ggV16gg='.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-1], u'normal 2ggV16gg='.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[1], u'**** Überschrift 1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[5], u'***** Überschrift 1.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[9], u'***** Überschrift 1.2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[12], u'******* Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[15], u'****** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'* Überschrift 2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'* Überschrift 2'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 3))

	def test_promote_parent_heading(self):
		vim.current.window.cursor = (13, 0)
		vim.EVALRESULTS[u"v:count"] = u'3'.encode(u'utf-8')
		self.assertNotEqual(self.editstructure.promote_heading(), None)
		self.assertEqual(len(vim.CMDHISTORY), 3)
		self.assertEqual(vim.CMDHISTORY[-3], u'normal 13ggV15gg='.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-2], u'normal 13ggV15gg='.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-1], u'normal 13ggV16gg='.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[5], u'** Überschrift 1.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[9], u'** Überschrift 1.2'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[12], u'* Überschrift 1.2.1.falsch'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[15], u'** Überschrift 1.2.1'.encode(u'utf-8'))
		self.assertEqual(vim.current.buffer[16], u'* Überschrift 2'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (13, -3))

def suite():
	return unittest.TestLoader().loadTestsFromTestCase(EditStructureTestCase)

########NEW FILE########
__FILENAME__ = test_plugin_mappings
# -*- coding: utf-8 -*-


import sys
sys.path.append(u'../ftplugin')

import unittest
import orgmode.settings
from orgmode.exceptions import PluginError
from orgmode._vim import ORGMODE
from orgmode.keybinding import MODE_ALL, Plug

import vim

ORG_PLUGINS = ['ShowHide', '|', 'Navigator', 'EditStructure', '|', 'Hyperlinks', '|', 'Todo', 'TagsProperties', 'Date', 'Agenda', 'Misc', '|', 'Export']


class MappingTestCase(unittest.TestCase):
	u"""Tests all plugins for overlapping mappings."""
	def test_non_overlapping_plug_mappings(self):
		def find_overlapping_mappings(kb, all_keybindings):
			found_overlapping_mapping = False
			for tkb in all_keybindings:
				if kb.mode == tkb.mode or MODE_ALL in (kb.mode, tkb.mode):
					if isinstance(kb._action, Plug) and isinstance(tkb._action, Plug):
						akb = kb.action
						atkb = tkb.action
						if (akb.startswith(atkb) or atkb.startswith(akb)) and akb != atkb:
							print u'\nERROR: Found overlapping mapping: %s (%s), %s (%s)' % (kb.key, akb, tkb.key, atkb)
							found_overlapping_mapping = True

			if all_keybindings:
				res = find_overlapping_mappings(all_keybindings[0], all_keybindings[1:])
				if not found_overlapping_mapping:
					return res
			return found_overlapping_mapping

		if self.keybindings:
			self.assertFalse(find_overlapping_mappings(self.keybindings[0], self.keybindings[1:]))

	def setUp(self):
		self.keybindings = []

		vim.EVALRESULTS = {
				u'exists("g:org_debug")': 0,
				u'exists("b:org_debug")': 0,
				u'exists("*repeat#set()")': 0,
				u'b:changedtick': 0,
				u'exists("b:org_plugins")'.encode(u'utf-8'): 0,
				u'exists("g:org_plugins")'.encode(u'utf-8'): 1,
				u'g:org_plugins'.encode(u'utf-8'): ORG_PLUGINS,
				}
		for plugin in filter(lambda p: p != '|', ORG_PLUGINS):
			try:
				ORGMODE.register_plugin(plugin)
			except PluginError:
				pass
			if plugin in ORGMODE._plugins:
				self.keybindings.extend(ORGMODE._plugins[plugin].keybindings)


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(MappingTestCase)

# vi: noexpandtab

########NEW FILE########
__FILENAME__ = test_plugin_misc
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
sys.path.append(u'../ftplugin')

import vim

from orgmode._vim import indent_orgmode, fold_orgmode, ORGMODE

ORGMODE.debug = True

START = True
END = False

counter = 0
class MiscTestCase(unittest.TestCase):
	def setUp(self):
		global counter
		counter += 1
		vim.CMDHISTORY = []
		vim.CMDRESULTS = {}
		vim.EVALHISTORY = []
		vim.EVALRESULTS = {
				# no org_todo_keywords for b
				u'exists("b:org_todo_keywords")'.encode(u'utf-8'): '0'.encode(u'utf-8'),
				# global values for org_todo_keywords
				u'exists("g:org_todo_keywords")'.encode(u'utf-8'): '1'.encode(u'utf-8'),
				u'g:org_todo_keywords'.encode(u'utf-8'): [u'TODO'.encode(u'utf-8'), u'DONE'.encode(u'utf-8'), u'|'.encode(u'utf-8')],
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("*repeat#set()")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u"v:count".encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'b:changedtick'.encode(u'utf-8'): (u'%d' % counter).encode(u'utf-8'),
				u"v:lnum".encode(u'utf-8'): u'0'.encode(u'utf-8')}
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* Überschrift 1
Text 1

Bla bla
** Überschrift 1.1
Text 2

Bla Bla bla
** Überschrift 1.2
Text 3

**** Überschrift 1.2.1.falsch

Bla Bla bla bla
*** Überschrift 1.2.1
* Überschrift 2
* Überschrift 3
  asdf sdf
""".split(u'\n') ]

	def test_indent_noheading(self):
		# test first heading
		vim.current.window.cursor = (1, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'1'.encode(u'utf-8')
		indent_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 0)

	def test_indent_heading(self):
		# test first heading
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'2'.encode(u'utf-8')
		indent_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 0)

	def test_indent_heading_middle(self):
		# test first heading
		vim.current.window.cursor = (3, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'3'.encode(u'utf-8')
		indent_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'let b:indent_level = 2'.encode(u'utf-8'))

	def test_indent_heading_middle2(self):
		# test first heading
		vim.current.window.cursor = (4, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'4'.encode(u'utf-8')
		indent_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'let b:indent_level = 2'.encode(u'utf-8'))

	def test_indent_heading_end(self):
		# test first heading
		vim.current.window.cursor = (5, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'5'.encode(u'utf-8')
		indent_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'let b:indent_level = 2'.encode(u'utf-8'))

	def test_fold_heading_start(self):
		# test first heading
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'2'.encode(u'utf-8')
		fold_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'let b:fold_expr = ">1"'.encode(u'utf-8'))

	def test_fold_heading_middle(self):
		# test first heading
		vim.current.window.cursor = (3, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'3'.encode(u'utf-8')
		fold_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'let b:fold_expr = 1'.encode(u'utf-8'))

	def test_fold_heading_end(self):
		# test first heading
		vim.current.window.cursor = (5, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'5'.encode(u'utf-8')
		fold_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'let b:fold_expr = 1'.encode(u'utf-8'))

	def test_fold_heading_end_of_last_child(self):
		# test first heading
		vim.current.window.cursor = (16, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'16'.encode(u'utf-8')
		fold_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 1)
		# which is also end of the parent heading <1
		self.assertEqual(vim.CMDHISTORY[-1], u'let b:fold_expr = ">3"'.encode(u'utf-8'))

	def test_fold_heading_end_of_last_child_next_heading(self):
		# test first heading
		vim.current.window.cursor = (17, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'17'.encode(u'utf-8')
		fold_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'let b:fold_expr = ">1"'.encode(u'utf-8'))

	def test_fold_middle_subheading(self):
		# test first heading
		vim.current.window.cursor = (13, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'13'.encode(u'utf-8')
		fold_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'let b:fold_expr = ">4"'.encode(u'utf-8'))

	def test_fold_middle_subheading2(self):
		# test first heading
		vim.current.window.cursor = (14, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'14'.encode(u'utf-8')
		fold_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'let b:fold_expr = 4'.encode(u'utf-8'))

	def test_fold_middle_subheading3(self):
		# test first heading
		vim.current.window.cursor = (15, 0)
		vim.EVALRESULTS[u'v:lnum'.encode(u'utf-8')] = u'15'.encode(u'utf-8')
		fold_orgmode()
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'let b:fold_expr = 4'.encode(u'utf-8'))

def suite():
	return unittest.TestLoader().loadTestsFromTestCase(MiscTestCase)

########NEW FILE########
__FILENAME__ = test_plugin_navigator
# -*- coding: utf-8 -*-

import unittest
import sys
sys.path.append(u'../ftplugin')

import vim

from orgmode._vim import ORGMODE

START = True
END = False

def set_visual_selection(visualmode, line_start, line_end, col_start=1,
        col_end=1, cursor_pos=START):

	if visualmode not in (u'', u'V', u'v'):
		raise ValueError(u'Illegal value for visualmode, must be in , V, v')

	vim.EVALRESULTS['visualmode()'] = visualmode

	# getpos results [bufnum, lnum, col, off]
	vim.EVALRESULTS['getpos("\'<")'] = ('', '%d' % line_start, '%d' %
			col_start, '')
	vim.EVALRESULTS['getpos("\'>")'] = ('', '%d' % line_end, '%d' %
			col_end, '')
	if cursor_pos == START:
		vim.current.window.cursor = (line_start, col_start)
	else:
		vim.current.window.cursor = (line_end, col_end)


counter = 0
class NavigatorTestCase(unittest.TestCase):
	def setUp(self):
		global counter
		counter += 1
		vim.CMDHISTORY = []
		vim.CMDRESULTS = {}
		vim.EVALHISTORY = []
		vim.EVALRESULTS = {
				# no org_todo_keywords for b
				u'exists("b:org_todo_keywords")'.encode(u'utf-8'): '0'.encode(u'utf-8'),
				# global values for org_todo_keywords
				u'exists("g:org_todo_keywords")'.encode(u'utf-8'): '1'.encode(u'utf-8'),
				u'g:org_todo_keywords'.encode(u'utf-8'): [u'TODO'.encode(u'utf-8'), u'DONE'.encode(u'utf-8'), u'|'.encode(u'utf-8')],
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("*repeat#set()")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'b:changedtick'.encode(u'utf-8'): (u'%d' % counter).encode(u'utf-8'),
				u"v:count".encode(u'utf-8'): u'0'.encode(u'utf-8'),
				}
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* Überschrift 1
Text 1

Bla bla
** Überschrift 1.1
Text 2

Bla Bla bla
** Überschrift 1.2
Text 3

**** Überschrift 1.2.1.falsch

Bla Bla bla bla
*** Überschrift 1.2.1
* Überschrift 2
* Überschrift 3
  asdf sdf
""".split(u'\n') ]

		if not u'Navigator' in ORGMODE.plugins:
			ORGMODE.register_plugin(u'Navigator')
		self.navigator = ORGMODE.plugins[u'Navigator']

	def test_movement(self):
		# test movement outside any heading
		vim.current.window.cursor = (1, 0)
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (1, 0))
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (2, 2))

	def test_forward_movement(self):
		# test forward movement
		vim.current.window.cursor = (2, 0)
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (6, 3))
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (10, 3))
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (13, 5))
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (16, 4))
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (17, 2))
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (18, 2))
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (18, 2))

		## don't move cursor if last heading is already focussed
		vim.current.window.cursor = (19, 6)
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (19, 6))

		## test movement with count
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'-1'.encode(u'utf-8')
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (6, 3))

		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'0'.encode(u'utf-8')
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (6, 3))

		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'1'.encode(u'utf-8')
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (6, 3))
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'3'.encode(u'utf-8')
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (16, 4))
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (18, 2))
		self.navigator.next(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (18, 2))
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'0'.encode(u'utf-8')

	def test_backward_movement(self):
		# test backward movement
		vim.current.window.cursor = (19, 6)
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (18, 2))
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (17, 2))
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (16, 4))
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (13, 5))
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (10, 3))
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (6, 3))
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (2, 2))

		## test movement with count
		vim.current.window.cursor = (19, 6)
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'-1'.encode(u'utf-8')
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (18, 2))

		vim.current.window.cursor = (19, 6)
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'0'.encode(u'utf-8')
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (18, 2))

		vim.current.window.cursor = (19, 6)
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'3'.encode(u'utf-8')
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (16, 4))
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'4'.encode(u'utf-8')
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (2, 2))
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'4'.encode(u'utf-8')
		self.navigator.previous(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (2, 2))

	def test_parent_movement(self):
		# test movement to parent
		vim.current.window.cursor = (2, 0)
		self.assertEqual(self.navigator.parent(mode=u'normal'), None)
		self.assertEqual(vim.current.window.cursor, (2, 0))

		vim.current.window.cursor = (3, 4)
		self.navigator.parent(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (3, 4))

		vim.current.window.cursor = (16, 4)
		self.navigator.parent(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (10, 3))
		self.navigator.parent(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (2, 2))

		vim.current.window.cursor = (15, 6)
		self.navigator.parent(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (10, 3))
		self.navigator.parent(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (2, 2))

		## test movement with count
		vim.current.window.cursor = (16, 4)
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'-1'.encode(u'utf-8')
		self.navigator.parent(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (10, 3))

		vim.current.window.cursor = (16, 4)
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'0'.encode(u'utf-8')
		self.navigator.parent(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (10, 3))

		vim.current.window.cursor = (16, 4)
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'1'.encode(u'utf-8')
		self.navigator.parent(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (10, 3))

		vim.current.window.cursor = (16, 4)
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'2'.encode(u'utf-8')
		self.navigator.parent(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (2, 2))

		vim.current.window.cursor = (16, 4)
		vim.EVALRESULTS[u"v:count".encode(u'utf-8')] = u'3'.encode(u'utf-8')
		self.navigator.parent(mode=u'normal')
		self.assertEqual(vim.current.window.cursor, (2, 2))

	def test_next_parent_movement(self):
		# test movement to parent
		vim.current.window.cursor = (6, 0)
		self.assertNotEqual(self.navigator.parent_next_sibling(mode=u'normal'), None)
		self.assertEqual(vim.current.window.cursor, (17, 2))

	def test_forward_movement_visual(self):
		# selection start: <<
		# selection end:   >>
		# cursor poistion: |

		# << text
		# text| >>
		# text
		# heading
		set_visual_selection(u'V', 2, 4, cursor_pos=END)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV5gg'.encode(u'utf-8'))

		# << text
		# text
		# text| >>
		# heading
		set_visual_selection(u'V', 2, 5, cursor_pos=END)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV9gg'.encode(u'utf-8'))

		# << text
		# x. heading
		# text| >>
		# heading
		set_visual_selection(u'V', 12, 14, cursor_pos=END)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 12ggV15gg'.encode(u'utf-8'))

		set_visual_selection(u'V', 12, 15, cursor_pos=END)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 12ggV16gg'.encode(u'utf-8'))

		set_visual_selection(u'V', 12, 16, cursor_pos=END)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 12ggV17gg'.encode(u'utf-8'))

		# << text
		# text
		# text| >>
		# heading
		# EOF
		set_visual_selection(u'V', 15, 17, cursor_pos=END)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 15ggV20gg'.encode(u'utf-8'))

		# << text >>
		# heading
		set_visual_selection(u'V', 1, 1, cursor_pos=START)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 1ggV5gg'.encode(u'utf-8'))

		# << heading >>
		# text
		# heading
		set_visual_selection(u'V', 2, 2, cursor_pos=START)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV5gg'.encode(u'utf-8'))

		# << text >>
		# heading
		set_visual_selection(u'V', 1, 1, cursor_pos=END)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 1ggV5gg'.encode(u'utf-8'))

		# << |text
		# heading
		# text
		# heading
		# text >>
		set_visual_selection(u'V', 1, 8, cursor_pos=START)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV8ggo'.encode(u'utf-8'))

		# << |heading
		# text
		# heading
		# text >>
		set_visual_selection(u'V', 2, 8, cursor_pos=START)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 6ggV8ggo'.encode(u'utf-8'))

		# << |heading
		# text >>
		# heading
		set_visual_selection(u'V', 6, 8, cursor_pos=START)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 8ggV9gg'.encode(u'utf-8'))

		# << |x. heading
		# text >>
		# heading
		set_visual_selection(u'V', 13, 15, cursor_pos=START)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 15ggV15gg'.encode(u'utf-8'))

		set_visual_selection(u'V', 13, 16, cursor_pos=START)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 16ggV16ggo'.encode(u'utf-8'))

		set_visual_selection(u'V', 16, 16, cursor_pos=START)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 16ggV17gg'.encode(u'utf-8'))

		# << |x. heading
		# text >>
		# heading
		# EOF
		set_visual_selection(u'V', 17, 17, cursor_pos=START)
		self.assertNotEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 17ggV20gg'.encode(u'utf-8'))

		# << |heading
		# text>>
		# text
		# EOF
		set_visual_selection(u'V', 18, 19, cursor_pos=START)
		self.assertEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 19ggV20gg'.encode(u'utf-8'))

		# << heading
		# text|>>
		# text
		# EOF
		set_visual_selection(u'V', 18, 19, cursor_pos=END)
		self.assertEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 18ggV20gg'.encode(u'utf-8'))

		# << heading
		# text|>>
		# EOF
		set_visual_selection(u'V', 18, 20, cursor_pos=END)
		self.assertEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 18ggV20gg'.encode(u'utf-8'))

		# << |heading
		# text>>
		# EOF
		set_visual_selection(u'V', 20, 20, cursor_pos=START)
		self.assertEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 20ggV20gg'.encode(u'utf-8'))

	def test_forward_movement_visual_to_the_end_of_the_file(self):
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* Überschrift 1
Text 1

Bla bla
** Überschrift 1.1
Text 2

Bla Bla bla
** Überschrift 1.2
Text 3

**** Überschrift 1.2.1.falsch

Bla Bla bla bla
test
""".split(u'\n') ]
		# << |heading
		# text>>
		# EOF
		set_visual_selection(u'V', 15, 15, cursor_pos=START)
		self.assertEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 15ggV17gg'.encode(u'utf-8'))

		set_visual_selection(u'V', 15, 17, cursor_pos=END)
		self.assertEqual(self.navigator.next(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 15ggV17gg'.encode(u'utf-8'))

	def test_backward_movement_visual(self):
		# selection start: <<
		# selection end:   >>
		# cursor poistion: |

		# << text | >>
		# text
		# heading
		set_visual_selection(u'V', 1, 1, cursor_pos=START)
		self.assertEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! gv'.encode(u'utf-8'))

		set_visual_selection(u'V', 1, 1, cursor_pos=END)
		self.assertEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! gv'.encode(u'utf-8'))

		# << heading| >>
		# text
		# heading
		set_visual_selection(u'V', 2, 2, cursor_pos=START)
		self.assertEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV2ggo'.encode(u'utf-8'))

		set_visual_selection(u'V', 2, 2, cursor_pos=END)
		self.assertEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV2ggo'.encode(u'utf-8'))

		# heading
		# text
		# << |text
		# text >>
		set_visual_selection(u'V', 3, 5, cursor_pos=START)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV5ggo'.encode(u'utf-8'))

		# heading
		# text
		# << text
		# text| >>
		set_visual_selection(u'V', 3, 5, cursor_pos=END)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV3ggo'.encode(u'utf-8'))

		# heading
		# text
		# << text
		# text| >>
		set_visual_selection(u'V', 8, 9, cursor_pos=END)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 6ggV8ggo'.encode(u'utf-8'))

		# heading
		# << text
		# x. heading
		# text| >>
		set_visual_selection(u'V', 12, 14, cursor_pos=END)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 12ggV12gg'.encode(u'utf-8'))

		set_visual_selection(u'V', 12, 15, cursor_pos=END)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 12ggV12gg'.encode(u'utf-8'))

		# heading
		# << |text
		# x. heading
		# text >>
		set_visual_selection(u'V', 12, 15, cursor_pos=START)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 10ggV15ggo'.encode(u'utf-8'))

		# heading
		# << text
		# x. heading| >>
		set_visual_selection(u'V', 12, 13, cursor_pos=END)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 12ggV12gg'.encode(u'utf-8'))

		# heading
		# << text
		# heading
		# text
		# x. heading| >>
		set_visual_selection(u'V', 12, 16, cursor_pos=END)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 12ggV15gg'.encode(u'utf-8'))

		# << text
		# heading
		# text
		# heading| >>
		set_visual_selection(u'V', 15, 17, cursor_pos=END)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 15ggV16gg'.encode(u'utf-8'))

		# heading
		# << |text
		# text
		# heading
		# text >>
		set_visual_selection(u'V', 4, 8, cursor_pos=START)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV8ggo'.encode(u'utf-8'))

		# heading
		# << text
		# text
		# heading
		# text| >>
		set_visual_selection(u'V', 4, 8, cursor_pos=END)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 4ggV5gg'.encode(u'utf-8'))

		# heading
		# << text
		# text
		# heading
		# text| >>
		set_visual_selection(u'V', 4, 5, cursor_pos=END)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV4ggo'.encode(u'utf-8'))

		# BOF
		# << |heading
		# text
		# heading
		# text >>
		set_visual_selection(u'V', 2, 8, cursor_pos=START)
		self.assertEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV8ggo'.encode(u'utf-8'))

		# BOF
		# heading
		# << text
		# text| >>
		set_visual_selection(u'V', 3, 4, cursor_pos=END)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV3ggo'.encode(u'utf-8'))

		# BOF
		# << heading
		# text
		# text| >>
		set_visual_selection(u'V', 2, 4, cursor_pos=END)
		self.assertNotEqual(self.navigator.previous(mode=u'visual'), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV2ggo'.encode(u'utf-8'))

		# << text
		# heading
		# text
		# x. heading
		# text| >>
		set_visual_selection(u'V', 8, 14, cursor_pos=END)
		self.navigator.previous(mode=u'visual')
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 8ggV12gg'.encode(u'utf-8'))

	def test_parent_movement_visual(self):
		# selection start: <<
		# selection end:   >>
		# cursor poistion: |

		# heading
		# << text|
		# text
		# text >>
		set_visual_selection(u'V', 4, 8, cursor_pos=START)
		self.navigator.parent(mode=u'visual')
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! gv'.encode(u'utf-8'))

		# heading
		# << text|
		# text
		# text >>
		set_visual_selection(u'V', 6, 8, cursor_pos=START)
		self.navigator.parent(mode=u'visual')
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV8ggo'.encode(u'utf-8'))

		# heading
		# << text
		# text
		# text| >>
		set_visual_selection(u'V', 6, 8, cursor_pos=END)
		self.navigator.parent(mode=u'visual')
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 6ggV5gg'.encode(u'utf-8'))

		# << |heading
		# text
		# text
		# text >>
		set_visual_selection(u'V', 2, 8, cursor_pos=START)
		self.assertEqual(self.navigator.parent(mode=u'visual'), None)

		# << heading
		# text
		# heading
		# text| >>
		set_visual_selection(u'V', 2, 8, cursor_pos=END)
		self.navigator.parent(mode=u'visual')
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV5gg'.encode(u'utf-8'))

		set_visual_selection(u'V', 7, 8, cursor_pos=START)
		self.navigator.parent(mode=u'visual')
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV8ggo'.encode(u'utf-8'))

		# heading
		# heading
		# << text
		# text| >>
		set_visual_selection(u'V', 12, 13, cursor_pos=END)
		self.navigator.parent(mode=u'visual')
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 12ggV12gg'.encode(u'utf-8'))

		set_visual_selection(u'V', 10, 12, cursor_pos=START)
		self.navigator.parent(mode=u'visual')
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggV12ggo'.encode(u'utf-8'))

		# heading
		# << text
		# text
		# heading| >>
		set_visual_selection(u'V', 11, 17, cursor_pos=END)
		self.assertEqual(self.navigator.parent(mode=u'visual'), None)

		# << text
		# heading
		# text
		# x. heading
		# text| >>
		set_visual_selection(u'V', 8, 14, cursor_pos=END)
		self.navigator.parent(mode=u'visual')
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 8ggV12gg'.encode(u'utf-8'))

def suite():
	return unittest.TestLoader().loadTestsFromTestCase(NavigatorTestCase)

########NEW FILE########
__FILENAME__ = test_plugin_show_hide
# -*- coding: utf-8 -*-

import unittest
import sys
sys.path.append(u'../ftplugin')

import vim

from orgmode._vim import ORGMODE

counter = 0
class ShowHideTestCase(unittest.TestCase):
	def setUp(self):
		global counter
		counter += 1
		vim.CMDHISTORY = []
		vim.CMDRESULTS = {}
		vim.EVALHISTORY = []
		vim.EVALRESULTS = {
				# no org_todo_keywords for b
				u'exists("b:org_todo_keywords")'.encode(u'utf-8'): '0'.encode(u'utf-8'),
				# global values for org_todo_keywords
				u'exists("g:org_todo_keywords")'.encode(u'utf-8'): '1'.encode(u'utf-8'),
				u'g:org_todo_keywords'.encode(u'utf-8'): [u'TODO'.encode(u'utf-8'), u'DONE'.encode(u'utf-8'), u'|'.encode(u'utf-8')],
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("b:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("*repeat#set()")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'b:changedtick'.encode(u'utf-8'): (u'%d' % counter).encode(u'utf-8'),
				u"v:count".encode(u'utf-8'): u'0'.encode(u'utf-8')}
		if not u'ShowHide' in ORGMODE.plugins:
			ORGMODE.register_plugin(u'ShowHide')
		self.showhide = ORGMODE.plugins[u'ShowHide']
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* Überschrift 1
Text 1

Bla bla
** Überschrift 1.1
Text 2

Bla Bla bla
** Überschrift 1.2
Text 3

**** Überschrift 1.2.1.falsch

Bla Bla bla bla
*** Überschrift 1.2.1
* Überschrift 2
* Überschrift 3
  asdf sdf
""".split(u'\n') ]

	def test_no_heading_toggle_folding(self):
		vim.current.window.cursor = (1, 0)
		self.assertEqual(self.showhide.toggle_folding(), None)
		self.assertEqual(vim.EVALHISTORY[-1], u'feedkeys("<Tab>", "n")'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (1, 0))

	def test_toggle_folding_first_heading_with_no_children(self):
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* Überschrift 1
Text 1

Bla bla
* Überschrift 2
* Überschrift 3
  asdf sdf
""".split(u'\n') ]
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'2'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(7)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				})
		vim.current.window.cursor = (2, 0)

		self.assertNotEqual(self.showhide.toggle_folding(), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 1zo'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_close_one(self):
		vim.current.window.cursor = (13, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(13)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(), None)
		self.assertEqual(len(vim.CMDHISTORY), 2)
		self.assertEqual(vim.CMDHISTORY[-2], u'13,15foldclose!'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2zo'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (13, 0))

	def test_toggle_folding_open_one(self):
		vim.current.window.cursor = (10, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(10)'.encode(u'utf-8'): u'10'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(), None)
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 1zo'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (10, 0))

	def test_toggle_folding_close_multiple_all_open(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(), None)
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'2,16foldclose!'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_all_closed(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'2'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(), None)
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 1zo'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_first_level_open(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'6'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'10'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'13'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'16'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(), None)
		self.assertEqual(len(vim.CMDHISTORY), 2)
		self.assertEqual(vim.CMDHISTORY[-2], u'normal! 6gg1zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 10gg1zo'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_second_level_half_open(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'10'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'13'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'16'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(), None)
		self.assertEqual(len(vim.CMDHISTORY), 4)
		self.assertEqual(vim.CMDHISTORY[-4], u'normal! 6gg2zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-3], u'normal! 10gg2zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-2], u'normal! 13gg2zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 16gg2zo'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_other_second_level_half_open(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'6'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'13'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'16'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(), None)
		self.assertEqual(len(vim.CMDHISTORY), 4)
		self.assertEqual(vim.CMDHISTORY[-4], u'normal! 6gg2zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-3], u'normal! 10gg2zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-2], u'normal! 13gg2zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 16gg2zo'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_third_level_half_open(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'16'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(), None)
		self.assertEqual(len(vim.CMDHISTORY), 4)
		self.assertEqual(vim.CMDHISTORY[-4], u'normal! 6gg3zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-3], u'normal! 10gg3zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-2], u'normal! 13gg3zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 16gg3zo'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_other_third_level_half_open(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'13'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(), None)
		self.assertEqual(len(vim.CMDHISTORY), 4)
		self.assertEqual(vim.CMDHISTORY[-4], u'normal! 6gg3zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-3], u'normal! 10gg3zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-2], u'normal! 13gg3zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 16gg3zo'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_other_third_level_half_open_second_level_half_closed(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'6'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'13'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(), None)
		self.assertEqual(len(vim.CMDHISTORY), 4)
		self.assertEqual(vim.CMDHISTORY[-4], u'normal! 6gg3zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-3], u'normal! 10gg3zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-2], u'normal! 13gg3zo'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 16gg3zo'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_no_heading_toggle_folding_reverse(self):
		vim.current.window.cursor = (1, 0)
		self.assertEqual(self.showhide.toggle_folding(reverse=True), None)
		self.assertEqual(vim.EVALHISTORY[-1], u'feedkeys("<Tab>", "n")'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (1, 0))

	def test_toggle_folding_first_heading_with_no_children_reverse(self):
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* Überschrift 1
Text 1

Bla bla
* Überschrift 2
* Überschrift 3
  asdf sdf
""".split(u'\n') ]
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'2'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(7)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				})
		vim.current.window.cursor = (2, 0)

		self.assertNotEqual(self.showhide.toggle_folding(reverse=True), None)
		self.assertEqual(vim.CMDHISTORY[-1], u'2,5foldopen!'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_close_one_reverse(self):
		vim.current.window.cursor = (13, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(13)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(reverse=True), None)
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 13ggzc'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (13, 0))

	def test_toggle_folding_open_one_reverse(self):
		vim.current.window.cursor = (10, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(10)'.encode(u'utf-8'): u'10'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(reverse=True), None)
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'10,16foldopen!'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (10, 0))

	def test_toggle_folding_close_multiple_all_open_reverse(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(reverse=True), None)
		self.assertEqual(len(vim.CMDHISTORY), 2)
		self.assertEqual(vim.CMDHISTORY[-2], u'normal! 13ggzc'.encode(u'utf-8'))
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 16ggzc'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_all_closed_reverse(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'2'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(reverse=True), None)
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'2,16foldopen!'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_first_level_open_reverse(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'6'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'10'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'13'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'16'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(reverse=True), None)
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 2ggzc'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_second_level_half_open_reverse(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'10'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'13'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'16'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(reverse=True), None)
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 6ggzc'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_other_second_level_half_open_reverse(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'6'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'13'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'16'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(reverse=True), None)
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 10ggzc'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_third_level_half_open_reverse(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'16'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(reverse=True), None)
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 13ggzc'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_other_third_level_half_open_reverse(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'13'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(reverse=True), None)
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 16ggzc'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

	def test_toggle_folding_open_multiple_other_third_level_half_open_second_level_half_closed_reverse(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS.update({
				u'foldclosed(2)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(6)'.encode(u'utf-8'): u'6'.encode(u'utf-8'),
				u'foldclosed(10)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				u'foldclosed(13)'.encode(u'utf-8'): u'13'.encode(u'utf-8'),
				u'foldclosed(16)'.encode(u'utf-8'): u'-1'.encode(u'utf-8'),
				})
		self.assertNotEqual(self.showhide.toggle_folding(reverse=True), None)
		self.assertEqual(len(vim.CMDHISTORY), 1)
		self.assertEqual(vim.CMDHISTORY[-1], u'normal! 16ggzc'.encode(u'utf-8'))
		self.assertEqual(vim.current.window.cursor, (2, 0))

def suite():
	return unittest.TestLoader().loadTestsFromTestCase(ShowHideTestCase)

########NEW FILE########
__FILENAME__ = test_plugin_tags_properties
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
sys.path.append(u'../ftplugin')

import vim

from orgmode._vim import indent_orgmode, fold_orgmode, ORGMODE

ORGMODE.debug = True

START = True
END = False

counter = 0
class TagsPropertiesTestCase(unittest.TestCase):
	def setUp(self):
		global counter
		counter += 1
		vim.CMDHISTORY = []
		vim.CMDRESULTS = {}
		vim.EVALHISTORY = []
		vim.EVALRESULTS = {
				# no org_todo_keywords for b
				u'exists("b:org_todo_keywords")'.encode(u'utf-8'): '0'.encode(u'utf-8'),
				# global values for org_todo_keywords
				u'exists("g:org_todo_keywords")'.encode(u'utf-8'): '1'.encode(u'utf-8'),
				u'g:org_todo_keywords'.encode(u'utf-8'): [u'TODO'.encode(u'utf-8'), u'DONE'.encode(u'utf-8'), u'|'.encode(u'utf-8')],
				u'&ts'.encode(u'utf-8'): u'6'.encode(u'utf-8'),
				u'exists("b:org_tag_column")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("g:org_tag_column")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("b:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("*repeat#set()")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'b:changedtick'.encode(u'utf-8'): (u'%d' % counter).encode(u'utf-8'),
				u"v:count".encode(u'utf-8'): u'0'.encode(u'utf-8')}
		if not u'TagsProperties' in ORGMODE.plugins:
			ORGMODE.register_plugin(u'TagsProperties')
		self.tagsproperties = ORGMODE.plugins[u'TagsProperties']
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* Überschrift 1
Text 1

Bla bla
** Überschrift 1.1
Text 2

Bla Bla bla
** Überschrift 1.2
Text 3

**** Überschrift 1.2.1.falsch

Bla Bla bla bla
*** Überschrift 1.2.1
* Überschrift 2
* Überschrift 3
  asdf sdf
""".split(u'\n') ]

	def test_new_property(self):
		u""" TODO: Docstring for test_new_property

		:returns: TODO
		"""
		pass

	def test_set_tags(self):
		# set first tag
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u'input("Tags: ", "", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u':hello:'.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t\t    :hello:'.encode('utf-8'))

		# set second tag
		vim.EVALRESULTS[u'input("Tags: ", ":hello:", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u':hello:world:'.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t    :hello:world:'.encode('utf-8'))

	def test_parse_tags_no_colons_single_tag(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u'input("Tags: ", "", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u'hello'.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t\t    :hello:'.encode('utf-8'))

	def test_parse_tags_no_colons_multiple_tags(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u'input("Tags: ", "", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u'hello:world'.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t    :hello:world:'.encode('utf-8'))

	def test_parse_tags_single_colon_left_single_tag(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u'input("Tags: ", "", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u':hello'.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t\t    :hello:'.encode('utf-8'))

	def test_parse_tags_single_colon_left_multiple_tags(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u'input("Tags: ", "", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u':hello:world'.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t    :hello:world:'.encode('utf-8'))

	def test_parse_tags_single_colon_right_single_tag(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u'input("Tags: ", "", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u'hello:'.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t\t    :hello:'.encode('utf-8'))

	def test_parse_tags_single_colon_right_multiple_tags(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u'input("Tags: ", "", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u'hello:world:'.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t    :hello:world:'.encode('utf-8'))

	def test_filter_empty_tags(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u'input("Tags: ", "", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u'::hello::'.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t\t    :hello:'.encode('utf-8'))

	def test_delete_tags(self):
		# set up
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u'input("Tags: ", "", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u':hello:world:'.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t    :hello:world:'.encode('utf-8'))

		# delete second of two tags
		vim.EVALRESULTS[u'input("Tags: ", ":hello:world:", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u':hello:'.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t\t    :hello:'.encode('utf-8'))

		# delete last tag
		vim.EVALRESULTS[u'input("Tags: ", ":hello:", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u''.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1'.encode('utf-8'))

	def test_realign_tags_noop(self):
		vim.current.window.cursor = (2, 0)
		self.tagsproperties.realign_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1'.encode('utf-8'))

	def test_realign_tags_remove_spaces(self):
		# remove spaces in multiple locations
		vim.current.buffer[1] = u'*  Überschrift 1 '.encode(u'utf-8')
		vim.current.window.cursor = (2, 0)
		self.tagsproperties.realign_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1'.encode('utf-8'))

		# remove tabs and spaces in multiple locations
		vim.current.buffer[1] = u'*\t  \tÜberschrift 1 \t'.encode(u'utf-8')
		vim.current.window.cursor = (2, 0)
		self.tagsproperties.realign_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1'.encode('utf-8'))

	def test_realign_tags(self):
		vim.current.window.cursor = (2, 0)
		vim.EVALRESULTS[u'input("Tags: ", "", "customlist,Org_complete_tags")'.encode(u'utf-8')] = u':hello:world:'.encode('utf-8')
		self.tagsproperties.set_tags()
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t    :hello:world:'.encode('utf-8'))

		d = ORGMODE.get_document()
		heading = d.find_current_heading()
		self.assertEqual(str(heading), u'* Überschrift 1\t\t\t\t\t\t\t\t    :hello:world:'.encode('utf-8'))
		self.tagsproperties.realign_tags()
		heading = d.find_current_heading()
		self.assertEqual(str(heading), u'* Überschrift 1\t\t\t\t\t\t\t\t    :hello:world:'.encode('utf-8'))
		self.assertEqual(vim.current.buffer[1], u'* Überschrift 1\t\t\t\t\t\t\t\t    :hello:world:'.encode('utf-8'))


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(TagsPropertiesTestCase)

########NEW FILE########
__FILENAME__ = test_plugin_todo
# -*- coding: utf-8 -*-


import sys
sys.path.append(u'../ftplugin')

import unittest
from orgmode.liborgmode.base import Direction
from orgmode.vimbuffer import VimBuffer
from orgmode.plugins.Todo import Todo

import vim

counter = 0

class TodoTestCase(unittest.TestCase):
	u"""Tests all the functionality of the TODO module."""

	def setUp(self):
		# set content of the buffer
		global counter
		counter += 1
		vim.EVALHISTORY = []
		vim.EVALRESULTS = {
				# no org_todo_keywords for b
				u'exists("b:org_todo_keywords")'.encode(u'utf-8'): '0'.encode(u'utf-8'),
				# global values for org_todo_keywords
				u'exists("g:org_todo_keywords")'.encode(u'utf-8'): '1'.encode(u'utf-8'),
				u'g:org_todo_keywords'.encode(u'utf-8'): [u'TODO'.encode(u'utf-8'), u'DONE'.encode(u'utf-8'), u'|'.encode(u'utf-8')],
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("b:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("*repeat#set()")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'b:changedtick'.encode(u'utf-8'): (u'%d' % counter).encode(u'utf-8'),
				u"v:count".encode(u'utf-8'): u'0'.encode(u'utf-8')
				}

		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* Heading 1
** Text 1
*** Text 2
* Text 1
** Text 1
   some text that is
   no heading

""".split(u'\n') ]

	# toggle
	def test_toggle_todo_with_no_heading(self):
		# nothing should happen
		vim.current.window.cursor = (1, 0)

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[0], u'')
		# and repeat it -> it should not change
		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[0], u'')

	def test_todo_toggle_NOTODO(self):
		vim.current.window.cursor = (2, 0)
		vim.current.buffer[1] = u'** NOTODO Überschrift 1.1'.encode(u'utf-8')

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[1], u'** TODO NOTODO Überschrift 1.1'.encode(u'utf-8'))

	def test_toggle_todo_in_heading_with_no_todo_state_different_levels(self):
		# level 1
		vim.current.window.cursor = (2, 0)
		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[1], u'* TODO Heading 1')
		self.assertEqual((2, 0), vim.current.window.cursor)

		# level 2
		vim.current.window.cursor = (3, 0)
		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[2], u'** TODO Text 1')

		# level 2
		vim.current.window.cursor = (4, 4)
		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[3], u'*** TODO Text 2')
		self.assertEqual((4, 9), vim.current.window.cursor)

	def test_circle_through_todo_states(self):
		# * Heading 1 -->
		# * TODO Heading 1 -->
		# * DONE Heading 1 -->
		# * Heading 1 -->
		# * TODO Heading 1 -->
		# * DONE Heading 1
		vim.current.window.cursor = (2, 6)

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[1], u'* TODO Heading 1')
		self.assertEqual((2, 11), vim.current.window.cursor)

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[1], u'* DONE Heading 1')
		self.assertEqual((2, 11), vim.current.window.cursor)

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[1], u'* Heading 1')
		self.assertEqual((2, 6), vim.current.window.cursor)

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[1], u'* TODO Heading 1')
		self.assertEqual((2, 11), vim.current.window.cursor)

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[1], u'* DONE Heading 1')
		self.assertEqual((2, 11), vim.current.window.cursor)

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[1], u'* Heading 1')
		self.assertEqual((2, 6), vim.current.window.cursor)

	def test_circle_through_todo_states_with_more_states(self):
		# * Heading 1 -->
		# * TODO Heading 1 -->
		# * STARTED Heading 1 -->
		# * DONE Heading 1 -->
		# * Heading 1 -->
		vim.EVALRESULTS[u'g:org_todo_keywords'.encode(u'utf-8')] = [u'TODO'.encode(u'utf-8'), u'STARTED'.encode(u'utf-8'), u'DONE'.encode(u'utf-8'),
				u'|'.encode(u'utf-8')]
		vim.current.window.cursor = (2, 0)

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[1], u'* TODO Heading 1')

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[1], u'* STARTED Heading 1')

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[1], u'* DONE Heading 1')

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[1], u'* Heading 1')

	def test_toggle_todo_with_cursor_in_text_not_heading(self):
		# nothing should happen
		vim.current.window.cursor = (7, 0)
		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[5], u'** TODO Text 1')
		self.assertEqual(vim.current.window.cursor, (7, 0))

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[5], u'** DONE Text 1')
		self.assertEqual(vim.current.window.cursor, (7, 0))

		Todo.toggle_todo_state()
		self.assertEqual(vim.current.buffer[5], u'** Text 1')
		self.assertEqual(vim.current.window.cursor, (7, 0))

	# get_states
	def test_get_states_without_seperator(self):
		u"""The last element in the todostates shouold be used as DONE-state when no sperator is given"""
		vim.EVALRESULTS[u'g:org_todo_keywords'.encode(u'utf-8')] = [u'TODO'.encode(u'utf-8'), u'DONE'.encode(u'utf-8')]
		states_todo, states_done = VimBuffer().get_todo_states()[0]
		expected_todo, expected_done = [u'TODO'], [u'DONE']
		self.assertEqual(states_todo, expected_todo)
		self.assertEqual(states_done, expected_done)

		vim.EVALRESULTS[u'g:org_todo_keywords'.encode(u'utf-8')] = [u'TODO'.encode(u'utf-8'), u'INPROGRESS'.encode(u'utf-8'), u'DONE'.encode(u'utf-8')]
		states_todo, states_done = VimBuffer().get_todo_states()[0]
		expected_todo = [u'TODO', u'INPROGRESS']
		expected_done = [u'DONE']
		self.assertEqual(states_todo, expected_todo)
		self.assertEqual(states_done, expected_done)

		vim.EVALRESULTS[u'g:org_todo_keywords'.encode(u'utf-8')] = [u'TODO'.encode(u'utf-8'), u'INPROGRESS'.encode(u'utf-8'),
				u'DUMMY'.encode(u'utf-8'), u'DONE'.encode(u'utf-8')]
		states_todo, states_done = VimBuffer().get_todo_states()[0]
		expected_todo  = [u'TODO', u'INPROGRESS', u'DUMMY']
		expected_done = [u'DONE']
		self.assertEqual(states_todo, expected_todo)
		self.assertEqual(states_done, expected_done)

	def test_get_states_with_seperator(self):
		vim.EVALRESULTS[u'g:org_todo_keywords'.encode(u'utf-8')] = [u'TODO'.encode(u'utf-8'), u'|'.encode(u'utf-8'), u'DONE'.encode(u'utf-8')]
		states_todo, states_done = VimBuffer().get_todo_states()[0]
		expected_todo = [u'TODO']
		expected_done = [u'DONE']
		self.assertEqual(states_todo, expected_todo)
		self.assertEqual(states_done, expected_done)

		vim.EVALRESULTS[u'g:org_todo_keywords'.encode(u'utf-8')] = [u'TODO'.encode(u'utf-8'), u'INPROGRESS'.encode(u'utf-8'), u'|'.encode(u'utf-8'),
				u'DONE'.encode(u'utf-8')]
		states_todo, states_done = VimBuffer().get_todo_states()[0]
		expected_todo = [u'TODO', u'INPROGRESS']
		expected_done = [u'DONE']
		self.assertEqual(states_todo, expected_todo)
		self.assertEqual(states_done, expected_done)

		vim.EVALRESULTS[u'g:org_todo_keywords'.encode(u'utf-8')] = [u'TODO'.encode(u'utf-8'), u'INPROGRESS'.encode(u'utf-8'),
				u'DUMMY'.encode(u'utf-8'), u'|'.encode(u'utf-8'),  u'DONE'.encode(u'utf-8')]
		states_todo, states_done = VimBuffer().get_todo_states()[0]
		expected_todo = [u'TODO', u'INPROGRESS', u'DUMMY']
		expected_done = [u'DONE']
		self.assertEqual(states_todo, expected_todo)
		self.assertEqual(states_done, expected_done)

		vim.EVALRESULTS[u'g:org_todo_keywords'.encode(u'utf-8')] = [u'TODO'.encode(u'utf-8'), u'INPROGRESS'.encode(u'utf-8'),
				u'DUMMY'.encode(u'utf-8'), u'|'.encode(u'utf-8'), u'DELEGATED'.encode(u'utf-8'), u'DONE'.encode(u'utf-8')]
		states_todo, states_done = VimBuffer().get_todo_states()[0]
		expected_todo =[u'TODO', u'INPROGRESS', u'DUMMY']
		expected_done = [u'DELEGATED', u'DONE']
		self.assertEqual(states_todo, expected_todo)
		self.assertEqual(states_done, expected_done)

		vim.EVALRESULTS[u'g:org_todo_keywords'.encode(u'utf-8')] = [u'TODO'.encode(u'utf-8'), u'|'.encode(u'utf-8'), u'DONEX'.encode(u'utf-8'),
				u'DUMMY'.encode(u'utf-8'), u'DELEGATED'.encode(u'utf-8'), u'DONE'.encode(u'utf-8')]
		states_todo, states_done = VimBuffer().get_todo_states()[0]
		expected_todo = [u'TODO']
		expected_done = [u'DONEX', u'DUMMY', u'DELEGATED', u'DONE']
		self.assertEqual(states_todo, expected_todo)
		self.assertEqual(states_done, expected_done)

		vim.EVALRESULTS[u'g:org_todo_keywords'.encode(u'utf-8')] = [[u'TODO(t)'.encode(u'utf-8'), u'|'.encode(u'utf-8'), u'DONEX'.encode(u'utf-8')],
				[u'DUMMY'.encode(u'utf-8'), u'DELEGATED'.encode(u'utf-8'), u'DONE'.encode(u'utf-8')]]
		states_todo, states_done = VimBuffer().get_todo_states()[0]
		expected_todo = [u'TODO']
		expected_done = [u'DONEX']
		self.assertEqual(states_todo, expected_todo)
		self.assertEqual(states_done, expected_done)

	# get_next_state
	def test_get_next_state_with_no_current_state(self):
		states = [((u'TODO', ), (u'DONE', ))]
		current_state = u''
		self.assertEquals(Todo._get_next_state(current_state, states), u'TODO')

		states = [((u'TODO', u'NEXT'), (u'DELEGATED', u'DONE'))]
		self.assertEquals(Todo._get_next_state(current_state, states), u'TODO')

		states = [((u'NEXT', ), (u'DELEGATED', u'DONE'))]
		self.assertEquals(Todo._get_next_state(current_state, states), u'NEXT')

	def test_get_next_state_backward_with_no_current_state(self):
		states = [((u'TODO', ), (u'DONE', ))]
		current_state = u''
		self.assertEquals(Todo._get_next_state(current_state, states,
				Direction.BACKWARD), u'DONE')

		states = [((u'TODO', u'NEXT'), (u'DELEGATED', u'DONE'))]
		self.assertEquals(Todo._get_next_state(current_state, states,
				Direction.BACKWARD), u'DONE')

		states = [((u'NEXT', ), (u'DELEGATED', u'DONE'))]
		self.assertEquals(Todo._get_next_state(current_state, states,
				Direction.BACKWARD), u'DONE')

	def test_get_next_state_with_invalid_current_state(self):
		states = [((u'TODO', ), (u'DONE', ))]
		current_state = u'STI'
		self.assertEquals(Todo._get_next_state(current_state, states), u'TODO')

		states = [((u'TODO', u'NEXT'), (u'DELEGATED', u'DONE'))]
		self.assertEquals(Todo._get_next_state(current_state, states), u'TODO')

		states = [((u'NEXT', ), (u'DELEGATED', u'DONE'))]
		self.assertEquals(Todo._get_next_state(current_state, states), u'NEXT')

	def test_get_next_state_backward_with_invalid_current_state(self):
		states = [((u'TODO', ), (u'DONE', ))]
		current_state = u'STI'
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD)
		self.assertEquals(result, u'DONE')

		states = [((u'TODO', u'NEXT'), (u'DELEGATED', u'DONE'))]
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD)
		self.assertEquals(result, u'DONE')

		states = [((u'NEXT', ), (u'DELEGATED', u'DONE'))]
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD)
		self.assertEquals(result, u'DONE')

	def test_get_next_state_with_current_state_equals_todo_state(self):
		states = [((u'TODO', u'NEXT', u'NOW'), (u'DELEGATED', u'DONE'))]
		current_state = u'TODO'
		self.assertEquals(Todo._get_next_state(current_state, states), u'NEXT')

		current_state = u'NEXT'
		self.assertEquals(Todo._get_next_state(current_state, states), u'NOW')

	def test_get_next_state_backward_with_current_state_equals_todo_state(self):
		states = [((u'TODO', u'NEXT', u'NOW'), (u'DELEGATED', u'DONE'))]
		current_state = u'TODO'
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD)
		self.assertEquals(result, None)

	def test_get_next_state_backward_misc(self):
		states = [((u'TODO', u'NEXT', u'NOW'), (u'DELEGATED', u'DONE'))]
		current_state = u'DONE'
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD)
		self.assertEquals(result, u'DELEGATED')

		current_state = u'DELEGATED'
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD)
		self.assertEquals(result, u'NOW')

		current_state = u'NOW'
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD)
		self.assertEquals(result, u'NEXT')

		current_state = u'NEXT'
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD)
		self.assertEquals(result, u'TODO')

		current_state = u'TODO'
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD)
		self.assertEquals(result, None)

		current_state = None
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD)
		self.assertEquals(result, u'DONE')

	def test_get_next_state_with_jump_from_todo_to_done(self):
		states = [((u'TODO', u'NEXT', u'NOW'), (u'DELEGATED', u'DONE'))]
		current_state = u'NOW'
		self.assertEquals(Todo._get_next_state(current_state, states), u'DELEGATED')

	def test_get_next_state_with_jump_from_done_to_todo(self):
		states = [((u'TODO', u'NEXT', u'NOW'), (u'DELEGATED', u'DONE'))]
		current_state = u'DONE'
		self.assertEquals(Todo._get_next_state(current_state, states), None)

	def test_get_next_state_in_current_sequence(self):
		states = [((u'TODO', u'NEXT', u'NOW'), (u'DELEGATED', u'DONE')), ((u'QA', ), (u'RELEASED', ))]
		current_state = u'QA'
		result = Todo._get_next_state(current_state, states,
				Direction.FORWARD)
		self.assertEquals(result, u'RELEASED')

	def test_get_next_state_in_current_sequence_with_access_keys(self):
		states = [((u'TODO(t)', u'NEXT(n)', u'NOW(w)'), (u'DELEGATED(g)', u'DONE(d)')), ((u'QA(q)', ), (u'RELEASED(r)', ))]
		current_state = u'QA'
		result = Todo._get_next_state(current_state, states,
				Direction.FORWARD)
		self.assertEquals(result, u'RELEASED')

		current_state = u'NEXT'
		result = Todo._get_next_state(current_state, states,
				Direction.FORWARD)
		self.assertEquals(result, u'NOW')

		current_state = u'TODO'
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD)
		self.assertEquals(result, None)

		current_state = None
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD)
		self.assertEquals(result, u'DONE')

	def test_get_next_keyword_sequence(self):
		states = [((u'TODO(t)', u'NEXT(n)', u'NOW(w)'), (u'DELEGATED(g)', u'DONE(d)')), ((u'QA(q)', ), (u'RELEASED(r)', ))]
		current_state = None
		result = Todo._get_next_state(current_state, states,
				Direction.FORWARD, next_set=True)
		self.assertEquals(result, u'TODO')

		current_state = None
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD, next_set=True)
		self.assertEquals(result, None)

		current_state = u'TODO'
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD, next_set=True)
		self.assertEquals(result, u'TODO')

		current_state = u'TODO'
		result = Todo._get_next_state(current_state, states,
				Direction.FORWARD, next_set=True)
		self.assertEquals(result, u'QA')

		current_state = u'NOW'
		result = Todo._get_next_state(current_state, states,
				Direction.FORWARD, next_set=True)
		self.assertEquals(result, u'QA')

		current_state = u'DELEGATED'
		result = Todo._get_next_state(current_state, states,
				Direction.FORWARD, next_set=True)
		self.assertEquals(result, u'QA')

		current_state = u'QA'
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD, next_set=True)
		self.assertEquals(result, u'TODO')

		current_state = u'QA'
		result = Todo._get_next_state(current_state, states,
				Direction.FORWARD, next_set=True)
		self.assertEquals(result, u'QA')

		current_state = u'RELEASED'
		result = Todo._get_next_state(current_state, states,
				Direction.FORWARD, next_set=True)
		self.assertEquals(result, u'RELEASED')

		current_state = u'RELEASED'
		result = Todo._get_next_state(current_state, states,
				Direction.BACKWARD, next_set=True)
		self.assertEquals(result, u'TODO')


def suite():
	return unittest.TestLoader().loadTestsFromTestCase(TodoTestCase)

# vi: noexpandtab

########NEW FILE########
__FILENAME__ = test_vimbuffer
# -*- coding: utf-8 -*-

import unittest
import sys
sys.path.append(u'../ftplugin')

import vim

from orgmode.liborgmode.headings import Heading
from orgmode.vimbuffer import VimBuffer


counter = 0
class VimBufferTestCase(unittest.TestCase):
	def setUp(self):
		global counter
		counter += 1
		vim.CMDHISTORY = []
		vim.CMDRESULTS = {}
		vim.EVALHISTORY = []
		vim.EVALRESULTS = {
				# no org_todo_keywords for b
				u'exists("b:org_todo_keywords")'.encode(u'utf-8'): '0'.encode(u'utf-8'),
				# global values for org_todo_keywords
				u'exists("g:org_todo_keywords")'.encode(u'utf-8'): '1'.encode(u'utf-8'),
				u'g:org_todo_keywords'.encode(u'utf-8'): [u'TODO'.encode(u'utf-8'), u'DONE'.encode(u'utf-8'), u'|'.encode(u'utf-8')],
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("*repeat#set()")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'b:changedtick'.encode(u'utf-8'): (u'%d' % counter).encode(u'utf-8'),
				u'&ts'.encode(u'utf-8'): u'8'.encode(u'utf-8'),
				u'exists("g:org_tag_column")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("b:org_tag_column")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u"v:count".encode(u'utf-8'): u'0'.encode(u'utf-8')}
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""#Meta information
#more meta information
* Überschrift 1
Text 1

Bla bla
** Überschrift 1.1
Text 2

Bla Bla bla
** Überschrift 1.2
Text 3

**** Überschrift 1.2.1.falsch

Bla Bla bla bla
*** Überschrift 1.2.1
* Überschrift 2
* Überschrift 3
  asdf sdf
""".split(u'\n') ]
		self.document = VimBuffer().init_dom()

	def test_write_heading_tags(self):
		self.assertEqual(self.document.is_dirty, False)
		h = self.document.find_heading()
		self.assertEqual(h._orig_start, 2)
		self.assertEqual(h.title, u'Überschrift 1')
		h.tags = [u'test', u'tag']
		self.assertEqual(h.tags[0], u'test')
		self.document.write_heading(h)

		# sanity check
		d = VimBuffer().init_dom()
		h2 = self.document.find_heading()
		self.assertEqual(d.headings[0].title, u'Überschrift 1')
		self.assertEqual(len(d.headings[0].tags), 2)
		self.assertEqual(d.headings[0].tags[0], u'test')
		self.assertEqual(d.headings[0]._orig_start, 2)
		self.assertEqual(d.headings[0].children[0]._orig_start, 6)

	def test_write_multi_heading_bodies(self):
		self.assertEqual(self.document.is_dirty, False)
		h = self.document.headings[0].copy()
		self.assertEqual(h._orig_start, 2)
		self.assertEqual(h.title, u'Überschrift 1')
		h.body.append(u'test')
		h.children[0].body.append(u'another line')
		self.document.write_heading(h)

		# sanity check
		d = VimBuffer().init_dom()
		h2 = self.document.find_heading()
		self.assertEqual(len(d.headings[0].body), 4)
		self.assertEqual(d.headings[0]._orig_start, 2)
		self.assertEqual(d.headings[0].children[0]._orig_start, 7)
		self.assertEqual(d.headings[0].children[0].title, u'Überschrift 1.1')
		self.assertEqual(len(d.headings[0].children[0].body), 4)
		self.assertEqual(d.headings[0].children[1]._orig_start, 12)
		self.assertEqual(d.headings[0].children[1].title, u'Überschrift 1.2')
		self.assertEqual(len(d.headings[0].children[1].body), 2)

	def test_meta_information_assign_directly(self):
		# read meta information from document
		self.assertEqual(u'\n'.join(self.document.meta_information), u'#Meta information\n#more meta information')
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].start, 2)

		# assign meta information directly to an element in array
		self.document.meta_information[0] = u'#More or less meta information'
		self.assertEqual(u'\n'.join(self.document.meta_information), u'#More or less meta information\n#more meta information')
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.is_dirty_meta_information, True)
		self.assertEqual(self.document.headings[0].start, 2)

	def test_meta_information_assign_string(self):
		# assign a single line string
		self.document.meta_information = u'#Less meta information'
		self.assertEqual('\n'.join(self.document.meta_information), u'#Less meta information')
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.is_dirty_meta_information, True)
		self.assertEqual(self.document.headings[0].start, 1)

	def test_meta_information_assign_multi_line_string(self):
		# assign a multi line string
		self.document.meta_information = u'#Less meta information\n#lesser information'
		self.assertEqual(u'\n'.join(self.document.meta_information), u'#Less meta information\n#lesser information')
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.is_dirty_meta_information, True)
		self.assertEqual(self.document.headings[0].start, 2)

	def test_meta_information_assign_one_element_array(self):
		# assign a single element array of strings
		self.document.meta_information = u'#More or less meta information'.split(u'\n')
		self.assertEqual(u'\n'.join(self.document.meta_information), u'#More or less meta information')
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.is_dirty_meta_information, True)
		self.assertEqual(self.document.headings[0].start, 1)

	def test_meta_information_assign_multi_element_array(self):
		# assign a multi element array of strings
		self.document.meta_information = u'#More or less meta information\n#lesser information'.split(u'\n')
		self.assertEqual(u'\n'.join(self.document.meta_information), u'#More or less meta information\n#lesser information')
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.is_dirty_meta_information, True)
		self.assertEqual(self.document.headings[0].start, 2)

	def test_meta_information_read_no_meta_information(self):
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""* Überschrift 1
Text 1

Bla bla
** Überschrift 1.1
Text 2

Bla Bla bla
** Überschrift 1.2
Text 3

**** Überschrift 1.2.1.falsch

Bla Bla bla bla
*** Überschrift 1.2.1
* Überschrift 2
* Überschrift 3
  asdf sdf
""".split(u'\n') ]
		self.document = VimBuffer().init_dom()

		# read no meta information from document
		self.assertEqual(self.document.meta_information, [])
		self.assertEqual(self.document.headings[0].start, 0)
		self.assertEqual(self.document.is_dirty, False)

		# assign meta information to a former empty field
		self.document.meta_information = u'#More or less meta information\n#lesser information'.split('\n')
		self.assertEqual(u'\n'.join(self.document.meta_information), u'#More or less meta information\n#lesser information')
		self.assertEqual(self.document.headings[0].start, 2)
		self.assertEqual(self.document.is_dirty, True)

	def test_meta_information_assign_empty_array(self):
		# assign an empty array as meta information
		self.document.meta_information = []
		self.assertEqual(self.document.meta_information, [])
		self.assertEqual(self.document.headings[0].start, 0)
		self.assertEqual(self.document.is_dirty, True)

	def test_meta_information_assign_empty_string(self):
		# assign an empty string as meta information
		self.document.meta_information = u''
		self.assertEqual(self.document.meta_information, [u''])
		self.assertEqual(self.document.headings[0].start, 1)
		self.assertEqual(self.document.is_dirty, True)

	def test_bufnr(self):
		self.assertEqual(self.document.bufnr, vim.current.buffer.number)
		# TODO add more tests as soon as multi buffer support has been implemented

	def test_write_meta_information(self):
		# write nothing
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.write(), False)
		self.assertEqual(u'\n'.join(self.document.meta_information), u'#Meta information\n#more meta information')

		# write changed meta information
		self.assertEqual(self.document.is_dirty, False)
		self.document.meta_information = u'#More or less meta information\n#lesser information'.split('\n')
		self.assertEqual(u'\n'.join(self.document.meta_information), u'#More or less meta information\n#lesser information')
		self.assertEqual(self.document.headings[0].start, 2)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].start, 2)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(u'\n'.join(VimBuffer().init_dom().meta_information), u'#More or less meta information\n#lesser information')

		# shorten meta information
		self.assertEqual(self.document.is_dirty, False)
		self.document.meta_information = u'!More or less meta information'.split(u'\n')
		self.assertEqual(u'\n'.join(self.document.meta_information), u'!More or less meta information')
		self.assertEqual(self.document.headings[0].start, 1)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].start, 1)
		self.assertEqual(self.document.headings[0]._orig_start, 1)
		self.assertEqual(u'\n'.join(VimBuffer().init_dom().meta_information), u'!More or less meta information')

		# lengthen meta information
		self.assertEqual(self.document.is_dirty, False)
		self.document.meta_information = u'!More or less meta information\ntest\ntest'
		self.assertEqual(u'\n'.join(self.document.meta_information), u'!More or less meta information\ntest\ntest')
		self.assertEqual(self.document.headings[0].start, 3)
		self.assertEqual(self.document.headings[0]._orig_start, 1)
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].start, 3)
		self.assertEqual(self.document.headings[0]._orig_start, 3)
		self.assertEqual(u'\n'.join(VimBuffer().init_dom().meta_information), u'!More or less meta information\ntest\ntest')

		# write empty meta information
		self.assertEqual(self.document.is_dirty, False)
		self.document.meta_information = []
		self.assertEqual(self.document.meta_information, [])
		self.assertEqual(self.document.headings[0].start, 0)
		self.assertEqual(self.document.headings[0]._orig_start, 3)
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].start, 0)
		self.assertEqual(self.document.headings[0]._orig_start, 0)
		self.assertEqual(VimBuffer().init_dom().meta_information, [])

	def test_write_changed_title(self):
		# write a changed title
		self.document.headings[0].title = u'Heading 1'
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.is_dirty_meta_information, False)
		self.assertEqual(self.document.headings[0].is_dirty_body, False)
		self.assertEqual(self.document.headings[0].is_dirty_heading, True)
		self.assertEqual(self.document.headings[0].title, u'Heading 1')
		self.assertEqual(self.document.headings[0].end, 5)
		self.assertEqual(len(self.document.headings[0]), 4)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 4)
		self.assertEqual(self.document.headings[0].children[0].start, 6)
		self.assertEqual(self.document.headings[0].children[0]._orig_start, 6)

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].end, 5)
		self.assertEqual(len(self.document.headings[0]), 4)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 4)
		self.assertEqual(self.document.headings[0].children[0].start, 6)
		self.assertEqual(self.document.headings[0].children[0]._orig_start, 6)
		self.assertEqual(VimBuffer().init_dom().headings[0].title, u'Heading 1')

	def test_write_changed_body(self):
		# write a changed body
		self.assertEqual(self.document.headings[0].end, 5)
		self.document.headings[0].body[0] = u'Another text'
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.is_dirty_meta_information, False)
		self.assertEqual(self.document.headings[0].is_dirty_body, True)
		self.assertEqual(self.document.headings[0].is_dirty_heading, False)
		self.assertEqual(self.document.headings[0].end, 5)
		self.assertEqual(len(self.document.headings[0]), 4)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 4)
		self.assertEqual(self.document.headings[0].children[0].start, 6)
		self.assertEqual(self.document.headings[0].children[0]._orig_start, 6)
		self.assertEqual(self.document.headings[0].body, [u'Another text', u'', u'Bla bla'])

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].end, 5)
		self.assertEqual(len(self.document.headings[0]), 4)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 4)
		self.assertEqual(self.document.headings[0].children[0].start, 6)
		self.assertEqual(self.document.headings[0].children[0]._orig_start, 6)
		self.assertEqual(VimBuffer().init_dom().headings[0].body, [u'Another text', u'', u'Bla bla'])

	def test_write_shortened_body(self):
		# write a shortened body
		self.document.headings[0].body = u'Another text'
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.is_dirty_meta_information, False)
		self.assertEqual(self.document.headings[0].is_dirty_body, True)
		self.assertEqual(self.document.headings[0].is_dirty_heading, False)
		self.assertEqual(self.document.headings[0].end, 3)
		self.assertEqual(len(self.document.headings[0]), 2)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 4)
		self.assertEqual(self.document.headings[0].children[0].start, 4)
		self.assertEqual(self.document.headings[0].children[0]._orig_start, 6)
		self.assertEqual(self.document.headings[0].body, [u'Another text'])

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].end, 3)
		self.assertEqual(len(self.document.headings[0]), 2)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 2)
		self.assertEqual(self.document.headings[0].children[0].start, 4)
		self.assertEqual(self.document.headings[0].children[0]._orig_start, 4)
		self.assertEqual(VimBuffer().init_dom().headings[0].body, [u'Another text'])

	def test_write_lengthened_body(self):
		# write a lengthened body
		self.document.headings[0].body = [u'Another text', u'more', u'and more', u'and more']
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.is_dirty_meta_information, False)
		self.assertEqual(self.document.headings[0].is_dirty_body, True)
		self.assertEqual(self.document.headings[0].is_dirty_heading, False)
		self.assertEqual(self.document.headings[0].end, 6)
		self.assertEqual(len(self.document.headings[0]), 5)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 4)
		self.assertEqual(self.document.headings[0].children[0].start, 7)
		self.assertEqual(self.document.headings[0].children[0]._orig_start, 6)
		self.assertEqual(self.document.headings[0].body, [u'Another text', u'more', u'and more', u'and more'])

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].end, 6)
		self.assertEqual(len(self.document.headings[0]), 5)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 5)
		self.assertEqual(self.document.headings[0].children[0].start, 7)
		self.assertEqual(self.document.headings[0].children[0]._orig_start, 7)
		self.assertEqual(VimBuffer().init_dom().headings[0].body, [u'Another text', u'more', u'and more', u'and more'])

	def test_write_delete_heading(self):
		# delete a heading
		self.assertEqual(len(self.document.headings[0].children), 2)
		del self.document.headings[0].children[0]
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(len(self.document.headings[0].children), 1)
		self.assertEqual(self.document.headings[0].end, 5)
		self.assertEqual(len(self.document.headings[0]), 4)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 4)
		self.assertEqual(self.document.headings[0].children[0].start, 6)
		self.assertEqual(self.document.headings[0].children[0]._orig_start, 10)
		self.assertEqual(self.document.headings[0].children[0]._orig_len, 3)

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].end, 5)
		self.assertEqual(len(self.document.headings[0]), 4)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 4)
		self.assertEqual(self.document.headings[0].children[0].start, 6)
		self.assertEqual(self.document.headings[0].children[0]._orig_start, 6)
		self.assertEqual(self.document.headings[0].children[0]._orig_len, 3)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(self.document.headings[0].children), 1)
		self.assertEqual(self.document.headings[0].end, 5)
		self.assertEqual(d.headings[0].end, 5)
		self.assertEqual(len(d.headings[0]), 4)
		self.assertEqual(d.headings[0]._orig_start, 2)
		self.assertEqual(d.headings[0]._orig_len, 4)
		self.assertEqual(d.headings[0].children[0].start, 6)
		self.assertEqual(d.headings[0].children[0]._orig_start, 6)
		self.assertEqual(d.headings[0].children[0]._orig_len, 3)

	def test_write_delete_first_heading(self):
		# delete the first heading
		self.assertEqual(len(self.document.headings), 3)
		del self.document.headings[0]
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(len(self.document.headings), 2)
		self.assertEqual(self.document.headings[0].end, 2)
		self.assertEqual(len(self.document.headings[0]), 1)
		self.assertEqual(self.document.headings[0]._orig_start, 17)
		self.assertEqual(self.document.headings[0]._orig_len, 1)
		self.assertEqual(self.document.headings[1].start, 3)
		self.assertEqual(self.document.headings[1]._orig_start, 18)
		self.assertEqual(self.document.headings[1]._orig_len, 3)

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].end, 2)
		self.assertEqual(len(self.document.headings[0]), 1)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 1)
		self.assertEqual(self.document.headings[1].start, 3)
		self.assertEqual(self.document.headings[1]._orig_start, 3)
		self.assertEqual(self.document.headings[1]._orig_len, 3)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(self.document.headings), 2)
		self.assertEqual(d.headings[0].end, 2)
		self.assertEqual(len(d.headings[0]), 1)
		self.assertEqual(d.headings[0]._orig_start, 2)
		self.assertEqual(d.headings[0]._orig_len, 1)
		self.assertEqual(d.headings[1].start, 3)
		self.assertEqual(d.headings[1]._orig_start, 3)
		self.assertEqual(d.headings[1]._orig_len, 3)

	def test_write_delete_last_heading(self):
		# delete the last heading
		self.assertEqual(len(self.document.headings), 3)
		del self.document.headings[-1]
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(len(self.document.headings), 2)
		self.assertEqual(self.document.headings[0].end, 5)
		self.assertEqual(self.document.headings[0].end_of_last_child, 16)
		self.assertEqual(len(self.document.headings[0]), 4)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 4)
		self.assertEqual(self.document.headings[-1].start, 17)
		self.assertEqual(self.document.headings[-1]._orig_start, 17)
		self.assertEqual(self.document.headings[-1]._orig_len, 1)
		self.assertEqual(self.document.headings[-1].end, 17)
		self.assertEqual(self.document.headings[-1].end_of_last_child, 17)

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].end, 5)
		self.assertEqual(self.document.headings[0].end_of_last_child, 16)
		self.assertEqual(len(self.document.headings[0]), 4)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0]._orig_len, 4)
		self.assertEqual(self.document.headings[-1].start, 17)
		self.assertEqual(self.document.headings[-1]._orig_start, 17)
		self.assertEqual(self.document.headings[-1]._orig_len, 1)
		self.assertEqual(self.document.headings[-1].end, 17)
		self.assertEqual(self.document.headings[-1].end_of_last_child, 17)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(self.document.headings), 2)
		self.assertEqual(d.headings[0].end, 5)
		self.assertEqual(d.headings[0].end_of_last_child, 16)
		self.assertEqual(len(d.headings[0]), 4)
		self.assertEqual(d.headings[0]._orig_start, 2)
		self.assertEqual(d.headings[0]._orig_len, 4)
		self.assertEqual(d.headings[-1].start, 17)
		self.assertEqual(d.headings[-1]._orig_start, 17)
		self.assertEqual(d.headings[-1]._orig_len, 1)
		self.assertEqual(d.headings[-1].end, 17)
		self.assertEqual(d.headings[-1].end_of_last_child, 17)

	def test_write_delete_multiple_headings(self):
		# delete multiple headings
		self.assertEqual(len(self.document.headings), 3)
		del self.document.headings[1]
		del self.document.headings[0].children[1].children[0]
		del self.document.headings[0].children[0]
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(len(self.document.headings), 2)
		self.assertEqual(len(self.document.headings[0].children), 1)
		self.assertEqual(len(self.document.headings[0].children[0].children), 1)
		self.assertEqual(self.document.headings[0].end, 5)
		self.assertEqual(self.document.headings[0].end_of_last_child, 9)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0].children[0]._orig_start, 10)
		self.assertEqual(self.document.headings[0].children[0].children[0]._orig_start, 16)
		self.assertEqual(self.document.headings[-1]._orig_start, 18)
		self.assertEqual(self.document.headings[0].start, 2)
		self.assertEqual(self.document.headings[0].children[0].start, 6)
		self.assertEqual(self.document.headings[0].children[0].children[0].start, 9)
		self.assertEqual(self.document.headings[-1].start, 10)

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].end, 5)
		self.assertEqual(self.document.headings[0].end_of_last_child, 9)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(self.document.headings[0].children[0]._orig_start, 6)
		self.assertEqual(self.document.headings[0].children[0].children[0]._orig_start, 9)
		self.assertEqual(self.document.headings[-1]._orig_start, 10)
		self.assertEqual(self.document.headings[0].start, 2)
		self.assertEqual(self.document.headings[0].children[0].start, 6)
		self.assertEqual(self.document.headings[0].children[0].children[0].start, 9)
		self.assertEqual(self.document.headings[-1].start, 10)
		self.assertEqual(self.document.headings[0].title, u'Überschrift 1')
		self.assertEqual(self.document.headings[0].children[0].title, u'Überschrift 1.2')
		self.assertEqual(self.document.headings[0].children[0].children[0].title, u'Überschrift 1.2.1')
		self.assertEqual(self.document.headings[-1].title, u'Überschrift 3')

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(self.document.headings), 2)
		self.assertEqual(len(self.document.headings[0].children), 1)
		self.assertEqual(len(self.document.headings[0].children[0].children), 1)
		self.assertEqual(d.headings[0].end, 5)
		self.assertEqual(d.headings[0].end_of_last_child, 9)
		self.assertEqual(d.headings[0]._orig_start, 2)
		self.assertEqual(d.headings[0].children[0]._orig_start, 6)
		self.assertEqual(d.headings[0].children[0].children[0]._orig_start, 9)
		self.assertEqual(d.headings[-1]._orig_start, 10)
		self.assertEqual(d.headings[0].start, 2)
		self.assertEqual(d.headings[0].children[0].start, 6)
		self.assertEqual(d.headings[0].children[0].children[0].start, 9)
		self.assertEqual(d.headings[-1].start, 10)
		self.assertEqual(d.headings[0].title, u'Überschrift 1')
		self.assertEqual(d.headings[0].children[0].title, u'Überschrift 1.2')
		self.assertEqual(d.headings[0].children[0].children[0].title, u'Überschrift 1.2.1')
		self.assertEqual(d.headings[-1].title, u'Überschrift 3')


	def test_write_add_heading(self):
		# add a heading
		self.assertEqual(len(self.document.headings), 3)
		self.assertEqual(len(self.document.headings[0].children), 2)
		h = Heading()
		h.title = u'Test heading'
		h.level = 2
		h.body = u'Text, text\nmore text'
		self.document.headings[0].children.append(h)
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(len(self.document.headings[0].children), 3)
		self.assertEqual(self.document.headings[0].children[-1].title, u'Test heading')

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(len(self.document.headings[0].children), 3)
		self.assertEqual(self.document.headings[0].children[-1].title, u'Test heading')

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(d.headings[0].children), 3)
		self.assertEqual(d.headings[0].children[-1].title, u'Test heading')

	def test_write_add_heading_before_first_heading(self):
		# add a heading before the first heading
		self.assertEqual(len(self.document.headings), 3)
		h = Heading()
		h.title = u'Test heading'
		h.level = 2
		h.body = u'Text, text\nmore text'
		self.assertEqual(h.start, None)
		self.document.headings[0:0] = h
		self.assertEqual(h.start, 2)
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(len(self.document.headings), 4)

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].title, u'Test heading')
		self.assertEqual(self.document.headings[0].start, 2)
		self.assertEqual(self.document.headings[0]._orig_start, 2)
		self.assertEqual(len(self.document.headings[0]), 3)
		self.assertEqual(self.document.headings[1].title, u'Überschrift 1')
		self.assertEqual(self.document.headings[1].start, 5)
		self.assertEqual(len(self.document.headings[1]), 4)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(d.headings), 4)
		self.assertEqual(d.headings[0].title, u'Test heading')
		self.assertEqual(d.headings[0].start, 2)
		self.assertEqual(d.headings[0]._orig_start, 2)
		self.assertEqual(len(d.headings[0]), 3)
		self.assertEqual(d.headings[1].title, u'Überschrift 1')
		self.assertEqual(d.headings[1].start, 5)
		self.assertEqual(len(d.headings[1]), 4)

	def test_write_add_heading_after_last_heading_toplevel(self):
		# add a heading after the last heading (top level heading)
		self.assertEqual(len(self.document.headings), 3)
		h = Heading()
		h.title = u'Test heading'
		h.body = u'Text, text\nmore text'
		self.assertEqual(h.start, None)
		#self.document.headings += h
		self.document.headings.append(h)
		self.assertEqual(h.start, 21)
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(len(self.document.headings), 4)

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[-1].title, u'Test heading')
		self.assertEqual(self.document.headings[-1].start, 21)
		self.assertEqual(self.document.headings[-1]._orig_start, 21)
		self.assertEqual(len(self.document.headings[-1]), 3)
		self.assertEqual(self.document.headings[-2].title, u'Überschrift 3')
		self.assertEqual(self.document.headings[-2].start, 18)
		self.assertEqual(len(self.document.headings[-2]), 3)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(d.headings), 4)
		self.assertEqual(d.headings[-1].title, u'Test heading')
		self.assertEqual(d.headings[-1].start, 21)
		self.assertEqual(d.headings[-1]._orig_start, 21)
		self.assertEqual(len(d.headings[-1]), 3)
		self.assertEqual(d.headings[-2].title, u'Überschrift 3')
		self.assertEqual(d.headings[-2].start, 18)
		self.assertEqual(len(d.headings[-2]), 3)

	def test_write_add_heading_after_last_heading_subheading(self):
		# add a heading after the last heading (subheading)
		self.assertEqual(len(self.document.headings), 3)
		h = Heading()
		h.title = u'Test heading'
		h.level = 2
		h.body = u'Text, text\nmore text'
		self.assertEqual(h.start, None)
		self.document.headings[-1].children += h
		self.assertEqual(h.start, 21)
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(len(self.document.headings), 3)
		self.assertEqual(len(self.document.headings[-1]), 3)

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[-1].children[-1].title, u'Test heading')
		self.assertEqual(self.document.headings[-1].children[-1].start, 21)
		self.assertEqual(self.document.headings[-1].children[-1]._orig_start, 21)
		self.assertEqual(len(self.document.headings[-1].children[-1]), 3)
		self.assertEqual(self.document.headings[-1].title, u'Überschrift 3')
		self.assertEqual(self.document.headings[-1].start, 18)
		self.assertEqual(len(self.document.headings[-1]), 3)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(d.headings), 3)
		self.assertEqual(len(d.headings[-1]), 3)
		self.assertEqual(d.headings[-1].children[-1].title, u'Test heading')
		self.assertEqual(d.headings[-1].children[-1].start, 21)
		self.assertEqual(d.headings[-1].children[-1]._orig_start, 21)
		self.assertEqual(len(d.headings[-1].children[-1]), 3)
		self.assertEqual(d.headings[-1].title, u'Überschrift 3')
		self.assertEqual(d.headings[-1].start, 18)
		self.assertEqual(len(d.headings[-1]), 3)

	def test_write_replace_one_heading(self):
		# replace subheadings by a list of newly created headings (one item)
		self.assertEqual(len(self.document.headings), 3)
		h = Heading()
		h.title = u'Test heading'
		h.level = 3
		h.body = u'Text, text\nmore text\nanother text'
		self.assertEqual(h.start, None)
		self.document.headings[0].children[1].children[0] = h
		self.assertEqual(h.start, 13)
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(len(self.document.headings), 3)
		self.assertEqual(len(self.document.headings[0].children[1].children), 2)

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].children[1].children[0].title, u'Test heading')
		self.assertEqual(self.document.headings[0].children[1].children[0].start, 13)
		self.assertEqual(self.document.headings[0].children[1].children[0]._orig_start, 13)
		self.assertEqual(len(self.document.headings[0].children[1].children[0]), 4)
		self.assertEqual(len(self.document.headings[0].children[1].children[0].children), 0)
		self.assertEqual(len(self.document.headings[0].children[1]), 3)
		self.assertEqual(len(self.document.headings[0].children[0].children), 0)
		self.assertEqual(len(self.document.headings[1].children), 0)
		self.assertEqual(self.document.headings[0].children[1].children[-1].title, u'Überschrift 1.2.1')
		self.assertEqual(self.document.headings[0].children[1].children[-1].start, 17)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(d.headings), 3)
		self.assertEqual(len(d.headings[0].children[1].children), 2)
		self.assertEqual(d.headings[0].children[1].children[0].title, u'Test heading')
		self.assertEqual(d.headings[0].children[1].children[0].start, 13)
		self.assertEqual(d.headings[0].children[1].children[0]._orig_start, 13)
		self.assertEqual(len(d.headings[0].children[1].children[0]), 4)
		self.assertEqual(len(d.headings[0].children[1].children[0].children), 0)
		self.assertEqual(len(d.headings[0].children[1]), 3)
		self.assertEqual(len(d.headings[0].children[0].children), 0)
		self.assertEqual(len(d.headings[1].children), 0)
		self.assertEqual(d.headings[0].children[1].children[-1].title, u'Überschrift 1.2.1')
		self.assertEqual(d.headings[0].children[1].children[-1].start, 17)

	def test_write_replace_multiple_headings_with_one_heading(self):
		# replace subheadings by a list of newly created headings (one item)
		self.assertEqual(len(self.document.headings), 3)
		h = Heading()
		h.title = u'Test heading'
		h.level = 3
		h.body = u'Text, text\nmore text\nanother text'

		self.assertEqual(h.start, None)
		self.assertEqual(len(self.document.headings[0].children[1].children), 2)
		self.document.headings[0].children[1].children[:] = h
		self.assertEqual(h.start, 13)
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.headings[0].children[1].is_dirty, False)
		self.assertEqual(len(self.document.headings), 3)
		self.assertEqual(len(self.document.headings[0].children[1].children), 1)

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].children[1].title, u'Überschrift 1.2')
		self.assertEqual(self.document.headings[0].children[1].children[0].title, u'Test heading')
		self.assertEqual(self.document.headings[0].children[1].children[0].start, 13)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(d.headings[0].children[1].children), 1)
		self.assertEqual(d.headings[0].children[1].title, u'Überschrift 1.2')
		self.assertEqual(d.headings[0].children[1].children[0].title, u'Test heading')
		self.assertEqual(d.headings[0].children[1].children[0].start, 13)

	def test_write_replace_multiple_headings_with_a_multiple_heading_structure(self):
		# replace subheadings by a list of newly created headings (multiple items)
		self.assertEqual(len(self.document.headings), 3)
		h = Heading()
		h.title = u'Test heading'
		h.level = 3
		h.body = u'Text, text\nmore text\nanother text'
		h1 = Heading()
		h1.title = u'another heading'
		h1.level = 4
		h1.body = u'This\nIs\nJust more\ntext'
		h.children.append(h1)
		h2 = Heading()
		h2.title = u'yet another heading'
		h2.level = 3
		h2.body = u'This\nis less text'

		self.assertEqual(h.start, None)
		self.document.headings[0].children[1].children[:] = (h, h2)
		self.assertEqual(h.start, 13)
		self.assertEqual(h1.start, 17)
		self.assertEqual(h2.start, 22)
		self.assertEqual(self.document.is_dirty, True)
		self.assertEqual(self.document.headings[0].children[1].is_dirty, False)
		self.assertEqual(len(self.document.headings), 3)
		self.assertEqual(len(self.document.headings[0].children[1].children), 2)
		self.assertEqual(len(self.document.headings[0].children[1].children[0].children), 1)
		self.assertEqual(len(self.document.headings[0].children[1].children[1].children), 0)

		self.assertEqual(self.document.write(), True)
		self.assertEqual(self.document.is_dirty, False)
		self.assertEqual(self.document.headings[0].children[1].title, u'Überschrift 1.2')
		self.assertEqual(self.document.headings[0].children[1].children[0].title, u'Test heading')
		self.assertEqual(self.document.headings[0].children[1].children[0].children[0].title, u'another heading')
		self.assertEqual(self.document.headings[0].children[1].children[1].title, u'yet another heading')
		self.assertEqual(self.document.headings[0].children[1].children[0].start, 13)
		self.assertEqual(self.document.headings[0].children[1].children[0].children[0].start, 17)
		self.assertEqual(self.document.headings[0].children[1].children[1].start, 22)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(d.headings[0].children[1].title, u'Überschrift 1.2')
		self.assertEqual(d.headings[0].children[1].children[0].title, u'Test heading')
		self.assertEqual(d.headings[0].children[1].children[0].children[0].title, u'another heading')
		self.assertEqual(d.headings[0].children[1].children[1].title, u'yet another heading')
		self.assertEqual(d.headings[0].children[1].children[0].start, 13)
		self.assertEqual(d.headings[0].children[1].children[0].children[0].start, 17)
		self.assertEqual(d.headings[0].children[1].children[1].start, 22)

	def test_dom(self):
		self.assertEqual(len(self.document.headings), 3)
		for h in self.document.headings:
			self.assertEqual(h.level, 1)
		self.assertEqual(len(self.document.headings[0].children), 2)
		self.assertEqual(len(self.document.headings[0].children[0].children), 0)
		self.assertEqual(len(self.document.headings[0].children[1].children), 2)
		self.assertEqual(len(self.document.headings[0].children[1].children[0].children), 0)
		self.assertEqual(len(self.document.headings[0].children[1].children[1].children), 0)
		self.assertEqual(len(self.document.headings[1].children), 0)
		self.assertEqual(len(self.document.headings[2].children), 0)

		# test no heading
		vim.current.window.cursor = (1, 0)
		h = self.document.current_heading()
		self.assertEqual(h, None)

	def test_index_boundaries(self):
		# test index boundaries
		vim.current.window.cursor = (-1, 0)
		h = self.document.current_heading()
		self.assertEqual(h, None)

		vim.current.window.cursor = (21, 0)
		h = self.document.current_heading()
		self.assertNotEqual(h, None)
		self.assertEqual(h.level, 1)
		self.assertEqual(h.start, 18)
		self.assertNotEqual(h.previous_sibling, None)
		self.assertEqual(h.previous_sibling.level, 1)
		self.assertEqual(h.parent, None)
		self.assertEqual(h.next_sibling, None)
		self.assertEqual(len(h.children), 0)

		vim.current.window.cursor = (999, 0)
		h = self.document.current_heading()
		self.assertEqual(h, None)

	def test_heading_start_and_end(self):
		# test heading start and end
		vim.current.window.cursor = (3, 0)
		h = self.document.current_heading()
		self.assertNotEqual(h, None)
		self.assertEqual(h.start, 2)
		self.assertEqual(h.end, 5)
		self.assertEqual(h.end_of_last_child, 16)

		vim.current.window.cursor = (12, 0)
		h = self.document.current_heading()
		self.assertNotEqual(h, None)
		self.assertEqual(h.start, 10)
		self.assertEqual(h.end, 12)
		self.assertEqual(h.end_of_last_child, 16)

		vim.current.window.cursor = (19, 0)
		h = self.document.current_heading()
		self.assertNotEqual(h, None)
		self.assertEqual(h.start, 18)
		self.assertEqual(h.end, 20)
		self.assertEqual(h.end_of_last_child, 20)

		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
** Überschrift 1.2
Text 3

**** Überschrift 1.2.1.falsch

Bla Bla bla bla
*** Überschrift 1.2.1
* Überschrift 2
* Überschrift 3
  asdf sdf
""".split(u'\n') ]
		self.document = VimBuffer().init_dom()
		vim.current.window.cursor = (3, 0)
		h = self.document.current_heading()
		self.assertNotEqual(h, None)
		self.assertEqual(h.parent, None)
		self.assertEqual(h.level, 2)
		self.assertEqual(h.title, u'Überschrift 1.2')
		self.assertEqual(len(h.children), 2)
		self.assertEqual(h.children[1].start, 7)
		self.assertEqual(h.children[1].children, [])
		self.assertEqual(h.children[1].next_sibling, None)
		self.assertEqual(h.children[1].end, 7)
		self.assertEqual(h.start, 1)
		self.assertEqual(h.end, 3)
		self.assertEqual(h.end_of_last_child, 7)

		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* Überschrift 2
* Überschrift 3""".split(u'\n') ]
		self.document = VimBuffer().init_dom()
		vim.current.window.cursor = (3, 0)
		h = self.document.current_heading()
		self.assertNotEqual(h, None)
		self.assertEqual(h.end, 2)
		self.assertEqual(h.end_of_last_child, 2)
		self.assertEqual(h.title, u'Überschrift 3')

	def test_first_heading(self):
		# test first heading
		vim.current.window.cursor = (3, 0)
		h = self.document.current_heading()

		self.assertNotEqual(h, None)
		self.assertEqual(h.parent, None)
		self.assertEqual(h.level, 1)
		self.assertEqual(len(h.children), 2)
		self.assertEqual(h.previous_sibling, None)

		self.assertEqual(h.children[0].level, 2)
		self.assertEqual(h.children[0].children, [])
		self.assertEqual(h.children[1].level, 2)
		self.assertEqual(len(h.children[1].children), 2)
		self.assertEqual(h.children[1].children[0].level, 4)
		self.assertEqual(h.children[1].children[1].level, 3)

		self.assertEqual(h.next_sibling.level, 1)

		self.assertEqual(h.next_sibling.next_sibling.level, 1)

		self.assertEqual(h.next_sibling.next_sibling.next_sibling, None)
		self.assertEqual(h.next_sibling.next_sibling.parent, None)

	def test_heading_in_the_middle(self):
		# test heading in the middle of the file
		vim.current.window.cursor = (14, 0)
		h = self.document.current_heading()

		self.assertNotEqual(h, None)
		self.assertEqual(h.level, 4)
		self.assertEqual(h.parent.level, 2)
		self.assertNotEqual(h.next_sibling, None)
		self.assertNotEqual(h.next_sibling.previous_sibling, None)
		self.assertEqual(h.next_sibling.level, 3)
		self.assertEqual(h.previous_sibling, None)

	def test_previous_headings(self):
		# test previous headings
		vim.current.window.cursor = (17, 0)
		h = self.document.current_heading()

		self.assertNotEqual(h, None)
		self.assertEqual(h.level, 3)
		self.assertNotEqual(h.previous_sibling, None)
		self.assertEqual(h.parent.level, 2)
		self.assertNotEqual(h.parent.previous_sibling, None)
		self.assertNotEqual(h.previous_sibling.parent, None)
		self.assertEqual(h.previous_sibling.parent.start, 10)

		vim.current.window.cursor = (14, 0)
		h = self.document.current_heading()
		self.assertNotEqual(h.parent, None)
		self.assertEqual(h.parent.start, 10)

		vim.current.window.cursor = (21, 0)
		h = self.document.current_heading()
		self.assertNotEqual(h, None)
		self.assertEqual(h.level, 1)
		self.assertNotEqual(h.previous_sibling, None)
		self.assertEqual(h.previous_sibling.level, 1)
		self.assertNotEqual(h.previous_sibling.previous_sibling, None)
		self.assertEqual(h.previous_sibling.previous_sibling.level, 1)
		self.assertEqual(h.previous_sibling.previous_sibling.previous_sibling,
                None)

		vim.current.window.cursor = (77, 0)
		h = self.document.current_heading()
		self.assertEqual(h, None)

class VimBufferTagsTestCase(unittest.TestCase):
	def setUp(self):
		global counter
		counter += 1
		vim.CMDHISTORY = []
		vim.CMDRESULTS = {}
		vim.EVALHISTORY = []
		vim.EVALRESULTS = {
				# no org_todo_keywords for b
				u'exists("b:org_todo_keywords")'.encode(u'utf-8'): '0'.encode(u'utf-8'),
				# global values for org_todo_keywords
				u'exists("g:org_todo_keywords")'.encode(u'utf-8'): '1'.encode(u'utf-8'),
				u'g:org_todo_keywords'.encode(u'utf-8'): [u'TODO'.encode(u'utf-8'), u'DONE'.encode(u'utf-8'), u'|'.encode(u'utf-8')],
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("*repeat#set()")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'b:changedtick'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'&ts'.encode(u'utf-8'): u'8'.encode(u'utf-8'),
				u'exists("g:org_tag_column")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("b:org_tag_column")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u"v:count".encode(u'utf-8'): u'0'.encode(u'utf-8')}
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""#Meta information
#more meta information
* Überschrift 1     :testtag:
Text 1

Bla bla
** Überschrift 1.1 :multi:tags:
Text 2

Bla Bla bla
** Überschrift 1.2:notag:
Text 3

**** Überschrift 1.2.1.falsch :no tag:

Bla Bla bla bla
*** Überschrift 1.2.1 :no tag
*** Überschrift 1.2.2 no tag:
* Überschrift 2				  :more:tags:
* Überschrift 3	:lesser:tag:
  asdf sdf
* Überschrift 4 super long long long long long long long long extremely long title	:title:long:
* TODO Überschrift 5 super long long long long long long long long extremely long title	:title_with_todo:
* oneword :with:tags:
* :noword:with:tags:
* TODO :todo:with:tags:
""".split(u'\n') ]
		self.document = VimBuffer().init_dom()

	def test_tag_read_no_word_with_tags(self):
		self.assertEqual(len(self.document.headings[6].tags), 3)
		self.assertEqual(self.document.headings[6].tags[0], u'noword')
		self.assertEqual(self.document.headings[6].title, u'')
		self.assertEqual(self.document.headings[6].todo, None)

	def test_tag_read_one_word_with_tags(self):
		self.assertEqual(len(self.document.headings[5].tags), 2)
		self.assertEqual(self.document.headings[5].tags[0], u'with')
		self.assertEqual(self.document.headings[5].title, u'oneword')
		self.assertEqual(self.document.headings[5].todo, None)

	def test_tag_read_TODO_with_tags(self):
		self.assertEqual(len(self.document.headings[7].tags), 3)
		self.assertEqual(self.document.headings[7].tags[0], u'todo')
		self.assertEqual(self.document.headings[7].title, u'')
		self.assertEqual(self.document.headings[7].todo, u'TODO')

	def test_tag_read_one(self):
		self.assertEqual(len(self.document.headings[0].tags), 1)
		self.assertEqual(self.document.headings[0].tags[0], u'testtag')
		self.assertEqual(unicode(self.document.headings[0]), u'* Überschrift 1							    :testtag:')

	def test_tag_read_multiple(self):
		self.assertEqual(len(self.document.headings[0].children[0].tags), 2)
		self.assertEqual(self.document.headings[0].children[0].tags, [u'multi', 'tags'])
		self.assertEqual(unicode(self.document.headings[0].children[0]), u'** Überschrift 1.1						 :multi:tags:')

	def test_tag_no_tags(self):
		self.assertEqual(len(self.document.headings[0].children[1].children), 3)
		self.assertEqual(len(self.document.headings[0].children[1].tags), 0)
		self.assertEqual(len(self.document.headings[0].children[1].children[0].tags), 0)
		self.assertEqual(len(self.document.headings[0].children[1].children[1].tags), 0)
		self.assertEqual(len(self.document.headings[0].children[1].children[2].tags), 0)

	def test_tag_read_space_and_tab_separated(self):
		self.assertEqual(len(self.document.headings[1].children), 0)
		self.assertEqual(len(self.document.headings[1].tags), 2)
		self.assertEqual(self.document.headings[1].tags, [u'more', u'tags'])

	def test_tag_read_tab_separated(self):
		self.assertEqual(len(self.document.headings[2].children), 0)
		self.assertEqual(len(self.document.headings[2].tags), 2)
		self.assertEqual(self.document.headings[2].tags, [u'lesser', u'tag'])

	def test_tag_read_long_title(self):
		self.assertEqual(len(self.document.headings[3].children), 0)
		self.assertEqual(len(self.document.headings[3].tags), 2)
		self.assertEqual(self.document.headings[3].tags, [u'title', u'long'])
		self.assertEqual(unicode(self.document.headings[3]), u'* Überschrift 4 super long long long long long long long long extremely long title  :title:long:')

	def test_tag_read_long_title_plus_todo_state(self):
		self.assertEqual(len(self.document.headings[4].children), 0)
		self.assertEqual(len(self.document.headings[4].tags), 1)
		self.assertEqual(self.document.headings[4].level, 1)
		self.assertEqual(self.document.headings[4].todo, u'TODO')
		self.assertEqual(self.document.headings[4].title, u'Überschrift 5 super long long long long long long long long extremely long title')
		self.assertEqual(self.document.headings[4].tags, [u'title_with_todo'])
		self.assertEqual(unicode(self.document.headings[4]), u'* TODO Überschrift 5 super long long long long long long long long extremely long title  :title_with_todo:')

	def test_tag_del_tags(self):
		self.assertEqual(len(self.document.headings[0].tags), 1)
		del self.document.headings[0].tags
		self.assertEqual(len(self.document.headings[0].tags), 0)
		self.assertEqual(self.document.headings[0].is_dirty_heading, True)
		self.assertEqual(self.document.headings[0].is_dirty_body, False)
		self.assertEqual(unicode(self.document.headings[0]), u'* Überschrift 1')
		self.assertEqual(self.document.write(), True)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(d.headings[0].tags), 0)
		self.assertEqual(d.headings[0].title, u'Überschrift 1')
		self.assertEqual(unicode(d.headings[0]), u'* Überschrift 1')

	def test_tag_replace_one_tag(self):
		self.assertEqual(len(self.document.headings[0].tags), 1)
		self.document.headings[0].tags = [u'justonetag']
		self.assertEqual(len(self.document.headings[0].tags), 1)
		self.assertEqual(self.document.headings[0].is_dirty_heading, True)
		self.assertEqual(self.document.headings[0].is_dirty_body, False)
		self.assertEqual(unicode(self.document.headings[0]), u'* Überschrift 1							 :justonetag:')
		self.assertEqual(self.document.write(), True)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(d.headings[0].tags), 1)
		self.assertEqual(d.headings[0].tags, [u'justonetag'])
		self.assertEqual(d.headings[0].title, u'Überschrift 1')
		self.assertEqual(unicode(d.headings[0]), u'* Überschrift 1							 :justonetag:')

	def test_tag_replace_multiple_tags(self):
		self.assertEqual(len(self.document.headings[1].tags), 2)
		self.document.headings[1].tags = [u'justonetag', u'moretags', u'lesstags']
		self.assertEqual(len(self.document.headings[1].tags), 3)
		self.assertEqual(self.document.headings[1].is_dirty_heading, True)
		self.assertEqual(self.document.headings[1].is_dirty_body, False)
		self.assertEqual(unicode(self.document.headings[1]), u'* Überschrift 2				       :justonetag:moretags:lesstags:')
		self.assertEqual(self.document.write(), True)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(len(d.headings[1].tags), 3)
		self.assertEqual(d.headings[1].tags, [u'justonetag', u'moretags', u'lesstags'])
		self.assertEqual(d.headings[1].title, u'Überschrift 2')
		self.assertEqual(unicode(d.headings[1]), u'* Überschrift 2				       :justonetag:moretags:lesstags:')

class VimBufferTodoTestCase(unittest.TestCase):
	def setUp(self):
		global counter
		counter += 1
		vim.CMDHISTORY = []
		vim.CMDRESULTS = {}
		vim.EVALHISTORY = []
		vim.EVALRESULTS = {
				# no org_todo_keywords for b
				u'exists("b:org_todo_keywords")'.encode(u'utf-8'): '0'.encode(u'utf-8'),
				# global values for org_todo_keywords
				u'exists("g:org_todo_keywords")'.encode(u'utf-8'): '1'.encode(u'utf-8'),
				u'g:org_todo_keywords'.encode(u'utf-8'): [u'TODO'.encode(u'utf-8'), \
						u'DONß'.encode(u'utf-8'), u'DONÉ'.encode(u'utf-8'), \
						u'DÖNE'.encode(u'utf-8'), u'WAITING'.encode(u'utf-8'), \
						u'DONE'.encode(u'utf-8'), u'|'.encode(u'utf-8')],
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("g:org_debug")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("*repeat#set()")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'b:changedtick'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'&ts'.encode(u'utf-8'): u'8'.encode(u'utf-8'),
				u'exists("g:org_tag_column")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u'exists("b:org_tag_column")'.encode(u'utf-8'): u'0'.encode(u'utf-8'),
				u"v:count".encode(u'utf-8'): u'0'.encode(u'utf-8')}
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""#Meta information
#more meta information
* TODO Überschrift 1     :testtag:
Text 1

Bla bla
** TODO NOTODO Überschrift 1.1 :multi:tags:
Text 2

Bla Bla bla
** NO-TODO Überschrift 1.2:notag:
Text 3

**** NOTODOÜberschrift 1.2.1.falsch :no tag:

Bla Bla bla bla
*** notodo Überschrift 1.2.1 :no tag
*** NOTODo Überschrift 1.2.2 no tag:
* WAITING Überschrift 2				  :more:tags:
* DONE Überschrift 3	:lesser:tag:
  asdf sdf
* DÖNE Überschrift 4
* DONß Überschrift 5
* DONÉ Überschrift 6
* DONé    Überschrift 7
""".split(u'\n') ]
		self.document = VimBuffer().init_dom()

	def test_no_space_after_upper_case_single_word_heading(self):
		vim.current.buffer[:] = [ i.encode(u'utf-8') for i in u"""
* TEST
** Text 1
*** Text 2
* Text 1
** Text 1
   some text that is
   no heading

""".split(u'\n') ]
		d = VimBuffer().init_dom()
		self.assertEqual(unicode(d.headings[0]), u'* TEST')

	def test_todo_read_TODO(self):
		self.assertEqual(self.document.headings[0].todo, u'TODO')
		self.assertEqual(self.document.headings[0].title, u'Überschrift 1')
		self.assertEqual(unicode(self.document.headings[0]), u'* TODO Überschrift 1						    :testtag:')

	def test_todo_read_TODO_NOTODO(self):
		self.assertEqual(self.document.headings[0].children[0].todo, u'TODO')
		self.assertEqual(self.document.headings[0].children[0].title, u'NOTODO Überschrift 1.1')
		self.assertEqual(unicode(self.document.headings[0].children[0]), u'** TODO NOTODO Überschrift 1.1					 :multi:tags:')

	def test_todo_read_WAITING(self):
		self.assertEqual(self.document.headings[1].todo, u'WAITING')
		self.assertEqual(self.document.headings[1].title, u'Überschrift 2')
		self.assertEqual(unicode(self.document.headings[1]), u'* WAITING Überschrift 2						  :more:tags:')

	def test_todo_read_DONE(self):
		self.assertEqual(self.document.headings[2].todo, u'DONE')
		self.assertEqual(self.document.headings[2].title, u'Überschrift 3')
		self.assertEqual(unicode(self.document.headings[2]), u'* DONE Überschrift 3						 :lesser:tag:')

	def test_todo_read_special(self):
		self.assertEqual(self.document.headings[3].todo, u'DÖNE')
		self.assertEqual(self.document.headings[3].title, u'Überschrift 4')

		self.assertEqual(self.document.headings[4].todo, u'DONß')
		self.assertEqual(self.document.headings[4].title, u'Überschrift 5')

		self.assertEqual(self.document.headings[5].todo, u'DONÉ')
		self.assertEqual(self.document.headings[5].title, u'Überschrift 6')

		self.assertEqual(self.document.headings[6].todo, None)
		self.assertEqual(self.document.headings[6].title, u'DONé    Überschrift 7')

	def test_todo_del_todo(self):
		self.assertEqual(self.document.headings[0].todo, u'TODO')
		del self.document.headings[0].todo
		self.assertEqual(self.document.headings[0].is_dirty_body, False)
		self.assertEqual(self.document.headings[0].is_dirty_heading, True)
		self.assertEqual(self.document.headings[0].todo, None)
		self.assertEqual(self.document.headings[0].title, u'Überschrift 1')
		self.assertEqual(unicode(self.document.headings[0]), u'* Überschrift 1							    :testtag:')
		self.assertEqual(self.document.write(), True)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(d.headings[0].todo, None)
		self.assertEqual(d.headings[0].title, u'Überschrift 1')
		self.assertEqual(unicode(d.headings[0]), u'* Überschrift 1							    :testtag:')

	def test_todo_write_todo_lowercase(self):
		self.assertEqual(self.document.headings[0].todo, u'TODO')
		self.document.headings[0].todo = u'waiting'
		self.assertEqual(self.document.headings[0].is_dirty_body, False)
		self.assertEqual(self.document.headings[0].is_dirty_heading, True)
		self.assertEqual(self.document.headings[0].todo, u'WAITING')
		self.assertEqual(self.document.headings[0].title, u'Überschrift 1')
		self.assertEqual(unicode(self.document.headings[0]), u'* WAITING Überschrift 1						    :testtag:')
		self.assertEqual(self.document.write(), True)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(d.headings[0].todo, u'WAITING')
		self.assertEqual(d.headings[0].title, u'Überschrift 1')
		self.assertEqual(unicode(d.headings[0]), u'* WAITING Überschrift 1						    :testtag:')

	def test_todo_write_todo_uppercase(self):
		self.assertEqual(self.document.headings[0].todo, u'TODO')
		self.document.headings[0].todo = u'DONE'
		self.assertEqual(self.document.headings[0].is_dirty_body, False)
		self.assertEqual(self.document.headings[0].is_dirty_heading, True)
		self.assertEqual(self.document.headings[0].todo, u'DONE')
		self.assertEqual(self.document.headings[0].title, u'Überschrift 1')
		self.assertEqual(unicode(self.document.headings[0]), u'* DONE Überschrift 1						    :testtag:')
		self.assertEqual(self.document.write(), True)

		# sanity check
		d = VimBuffer().init_dom()
		self.assertEqual(d.headings[0].todo, u'DONE')
		self.assertEqual(d.headings[0].title, u'Überschrift 1')
		self.assertEqual(unicode(d.headings[0]), u'* DONE Überschrift 1						    :testtag:')

	def test_todo_set_illegal_todo(self):
		def set_todo(todo):
			self.document.headings[0].todo = todo
		self.assertEqual(self.document.headings[0].todo, u'TODO')
		self.assertRaises(ValueError, set_todo, u'DO NE')
		self.assertRaises(ValueError, set_todo, u'DO\tNE')
		self.assertRaises(ValueError, set_todo, u'D\nNE')
		self.assertRaises(ValueError, set_todo, u'DO\rNE')
		self.assertEqual(self.document.headings[0].todo, u'TODO')

def suite():
	return ( \
			unittest.TestLoader().loadTestsFromTestCase(VimBufferTestCase), \
			unittest.TestLoader().loadTestsFromTestCase(VimBufferTagsTestCase), \
			unittest.TestLoader().loadTestsFromTestCase(VimBufferTodoTestCase), \
			)

########NEW FILE########
__FILENAME__ = vim
# -*- coding: utf-8 -*-


class VimWindow(object):
	u""" Docstring for VimWindow """

	def __init__(self, test):
		object.__init__(self)
		self._test = test
		self.cursor = (1, 0)

	def buffer():
		def fget(self):
			return self._test.buffer

		def fset(self, value):
			self._test.buffer = value
		return locals()
	buffer = property(**buffer())


class VimBuffer(list):
	def __init__(self, iterable=None):
		self.number = 0
		if iterable is not None:
			list.__init__(self, iterable)
		else:
			list.__init__(self)

	def append(self, o):
		u"""
		mimic the specific behavior of vim.current.buffer
		"""
		if isinstance(o, list) or isinstance(o, tuple):
			for i in o:
				list.append(self, i)
		else:
			list.append(self, o)


class VimTest(object):
	u""" Replacement for vim API """

	def __init__(self):
		object.__init__(self)
		self._buffer = VimBuffer()
		self.window = VimWindow(self)

	def buffer():
		def fget(self):
			return self._buffer

		def fset(self, value):
			self._buffer = VimBuffer(value)
		return locals()
	buffer = property(**buffer())


EVALHISTORY = []
EVALRESULTS = {
		u'exists("g:org_debug")': 0,
		u'exists("b:org_debug")': 0,
		u'exists("*repeat#set()")': 0,
		u'exists("b:org_plugins")': 0,
		u'exists("g:org_plugins")': 0,
		u'b:changedtick': 0,
		}


def eval(cmd):
	u""" evaluate command

	:returns: results stored in EVALRESULTS
	"""
	EVALHISTORY.append(cmd)
	return EVALRESULTS.get(cmd, None)


CMDHISTORY = []
CMDRESULTS = {}


def command(cmd):
	CMDHISTORY.append(cmd)
	return CMDRESULTS.get(cmd, None)


current = VimTest()

########NEW FILE########
