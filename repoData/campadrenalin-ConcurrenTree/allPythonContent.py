__FILENAME__ = address
from ConcurrenTree import ModelBase
import re
import json

# Internal storage format: assorted strings and (int, str) tuples.

class Address(ModelBase):
	''' Address format: [4,"hello"," dolly"] '''

	def __init__(self, target=[]):
		if type(target)==list:
			self.layers = []
			self.parse(target)
		elif isinstance(target, Address):
			self.layers = list(target.layers) # copies data, not ref
		elif type(target) in (str, unicode):
			self.layers = json.loads(target)
		else:
			raise TypeError("Expected list or address.Address, got "+str(type(target)))

	def parse(self, l):
		''' Reads and checks a list '''
		pos = None
		progress = list(self.layers)
		for i in expand(l):
			if type(i)==int:
				if pos==None:
					pos = i
					progress.append(i)
				else:
					raise ValueError("Address list cannot contain consecutive ints")

			elif type(i) in (str, unicode):
				progress.append(i)
				pos = None
			else:
				raise TypeError("Address cannot parse element %s" % str(i))
		if pos == None:
			self.layers = progress
		else:
			raise ValueError("Address list cannot end with int")

	def resolve(self, tree):
		return tree.resolve(self.layers)

	def proto(self):
		return expand(self.layers)

	def append(self, value):
		''' Value may be a 2-tuple or a string '''
		self.layers.append(expand(value))

	def prepend(self, value):
		''' Value may be a 2-tuple or a string '''
		self.layers.insert(0,expand(value))

	def jump(self, pos, max, key):
		if pos==max:
			return key
		else:
			return pos, key

	@property
	def parent(self):
		''' Address for the parent node of self's node '''
		if self.layers == []:
			raise ValueError("Root has no parent")
		new = Address(self) # copy
		new.layers = new.layers[:-1]
		return new

	def position(self, root):
		''' Position of final jump '''
		tail = self.layers[-1]
		if type(tail) == tuple:
			return tail[0]
		else:
			return len(self.parent.resolve(root))

	# Plumbing

	def __len__(self):
		''' Number of hops '''
		return len(self.layers)

	def __iter__(self):
		return self.proto().__iter__()

	def __eq__(self, other):
		return type(self)==type(other) and self.layers == other.layers

	def __add__(self, other):
		new = Address(self) # Copy layers
		new += other
		return new

	def __iadd__(self, other):
		if type(other) == list:
			self.parse(other)
		elif isinstance(other, Address):
			self.layers += other.layers
		elif isinstance(other, ModelBase):
			return other + self
		else:
			self += [other]
		return self

	def __radd__(self, other):
		if type(other) == list:
			return Address(other) + self
		else:
			return [other] + self

	__hash__ = None

	def __repr__(self):
		classname = repr(self.__class__).split()[1]
		return "<%s instance %s at %s>" % (classname, str(self), hex(long(id(self)))[:-1])

def expand(l):
	''' Expands all sub-lists '''
	result = []
	for i in l:
		if type(i) in (tuple, list):
			result += list(i)
		else:
			result.append(i)
	return result

########NEW FILE########
__FILENAME__ = auth
import user

class Auth(object):
    ''' Key-value store for storage spaces keyed on username. '''

    def __init__(self):
        self.contents = {}

    def make(self, username, password):
        if username in self:
            return self[username]
        else:
            self[username] = user.UserStorage(username, password)
            return self[username] 

    def __getitem__(self, username):
        return self.contents[username]

    def __setitem__(self, username, storage):
        self.contents[username] = storage

    def __delitem__(self, username):
        del self.contents[username]

    def __contains__(self, username):
        return username in self.contents

########NEW FILE########
__FILENAME__ = context
class Context(object):
	# Base class for all context objects, defines API
	def __init__(self, node):
		self.node = node
		self.register()
		self.live = Live(self)

	@property
	def value(self):
		return self.node.flatten()

	def register(self):
		# Register with node callbacks
		pass

class Live(object):
	# Applies context actions directly
	# For example, mycontext.live.insert(4, "Mayweather") does not just return
	# an op, it also applies it first.
	def __init__(self, context):
		self.context = context

	def __getattribute__(self, name):
		if name == "context":
			return object.__getattribute__(self, name)
		else:
			func = object.__getattribute__(self.context, name)
			def wrap_live(*args, **kwargs):
				op = func(*args, **kwargs)
				self.context.node.apply(op)
				return op
			return wrap_live

########NEW FILE########
__FILENAME__ = list
from ConcurrenTree import operation, instruction, address, node
import context

class ListContext(context.Context):
	def get(self, i):
		# Return (addr, node) for node at position i in self.value
		laddr, index = self._traceelem(i)
		n = self.node.resolve(laddr)._children[index].head
		addr = laddr + [index, n.key]
		return addr, n

	def insert(self, pos, value):
		iaddr, ipos = self._traceindex(pos)
		n = node.make([value])
		return iaddr + operation.FromNode(n, ipos)

	def delete(self, pos, size=1):
		killzones = [self._traceelem(pos+x) for x in range(size)]
		return operation.Operation([instruction.Delete(*k) for k in killzones])

	def _traceelem(self, pos, node = None, addr = [], fail=True):
		# Returns (addr, pos) for a char in the flat rep of the node
		node = node or self.node
		addr = address.Address(addr)

		for i in range(len(node)+1):
			for c in node.index(i):
				index = i+len(node)
				# naddr = new address
				# pos   = overwritten with leftovers
				naddr, pos = self._traceelem(pos,
					node.get(index,c), addr+[index,c], False)
				if naddr != None:
					return naddr, pos
			if i < len(node) and not node._del[i]:
				if pos == 0:
					return addr, i
				else:
					pos -= 1
		if fail:
			raise IndexError("pos out of range, longer than len(node.flatten())-1")
		else:
			return None, pos


	def _traceindex(self, pos, node = None, addr = [], fail=True):
		# Returns (addr, pos) for an index in the flat rep of the node
		node = node or self.node
		addr = address.Address(addr)

		for i in range(len(node)+1):
			for c in node.index(i):
				index = i+len(node)
				# naddr = new address
				# pos   = overwritten with leftovers
				naddr, pos = self._traceindex(pos,
					node.get(index,c), addr+[index,c], False)
				if naddr != None:
					return naddr, pos

			# Check for finish, kill one for nondeleted characters
			if pos == 0:
				return addr, i+len(node)
			elif i < len(node) and not node._del[i]:
				pos -= 1
		if fail:
			raise IndexError("pos out of range, longer than len(node.flatten())")
		else:
			return None, pos


########NEW FILE########
__FILENAME__ = map
from ConcurrenTree import operation, instruction, address, node
import context

class MapContext(context.Context):

	# Model level - accurate to data model

	def get(self, key):
		return self.node.get(key, "/single")

	def set(self, key, value):
		if self.has(key):
			# Use existing SingleNode
			r = self.get(key).context().set(value)
			return address.Address([key, "/single"])+r
		else:
			# Make Singlenode
			s = instruction.InsertSingle([], key)
			# Make actual node
			n = node.make(value).op(0, [key, "/single"])
			return s + n

	def has(self, key):
		return key in self.node._data

	# Virtual level - treat null values as removed, drop ops, etc.

	def __getitem__(self, key):
		return self.get(key).flatten()

	def __setitem__(self, key, value):
		self.live.set(key, value)

	def __contains__(self, key):
		return self.has(key) and (self[key] != None)

########NEW FILE########
__FILENAME__ = number
from ConcurrenTree import instruction, operation
import context

class NumberContext(context.Context):
	def __init__(self, node, unique = None):
		context.Context.__init__(self, node)
		if unique == None:
			print "WARNING: Random unique being used in NumberNode."
			print "Uniques should be based on personal id data to avoid collisions."
			import random
			unique = random.randint(0, 2**32)
		self.unique = unique

	def delta(self, amount, unique=None):
		addr = self.node.head()[0]
		return operation.Operation([
			instruction.InsertNumber(addr, 0, amount, self.unique)])

	def incr(self):
		return self.delta(1)

	def decr(self):
		return self.delta(-1)

########NEW FILE########
__FILENAME__ = single
from ConcurrenTree import operation, instruction, node
import context

class SingleContext(context.Context):
	def set(self, value):
		addr, head = self.head()
		op = operation.Operation()
		if len(head._children[0]) > 0:
			# Extend head
			op += instruction.InsertSingle(addr, 1)
			addr += [1, '/single']
			head = head.head()[1]
		# Insert value
		vnode = node.make(value)
		op += vnode.op(0, addr)
		return op

	def get(self):
		# Return (addr, node) for current value
		addr, head = self.head()
		vn = head.value_node()
		if vn == None:
			return (None, None)
		return addr+[0, vn.key], vn

	def head(self):
		# Return (addr, node) for the current head SingleNode
		return self.node.head()

########NEW FILE########
__FILENAME__ = string
from ConcurrenTree import operation, instruction, address, node
import context

class StringContext(context.Context):
	def insert(self, pos, value):
		iaddr, ipos = self._traceindex(pos)
		i = instruction.InsertNode(iaddr, ipos, node.make(value))
		return operation.Operation([i])

	def delete(self, pos, size=1):
		killzones = [self._traceelem(pos+x) for x in range(size)]
		return operation.Operation([instruction.Delete(*k) for k in killzones])

	def _traceelem(self, pos, node = None, addr = [], fail=True):
		# Returns (addr, pos) for a char in the flat rep of the node
		node = node or self.node
		addr = address.Address(addr)

		for i in range(len(node)+1):
			for c in node._children[i]:
				# naddr = new address
				# pos   = overwritten with leftovers
				naddr, pos = self._traceelem(pos,
					node.get(i,c), addr+[i,c], False)
				if naddr != None:
					return naddr, pos
			if i < len(node) and not node._del[i]:
				if pos == 0:
					return addr, i
				else:
					pos -= 1
		if fail:
			raise IndexError("pos out of range, longer than len(node.flatten())-1")
		else:
			return None, pos


	def _traceindex(self, pos, node = None, addr = [], fail=True):
		# Returns (addr, pos) for an index in the flat rep of the node
		node = node or self.node
		addr = address.Address(addr)

		for i in range(len(node)+1):
			for c in node._children[i]:
				# naddr = new address
				# pos   = overwritten with leftovers
				naddr, pos = self._traceindex(pos,
					node.get(i,c), addr+[i,c], False)
				if naddr != None:
					return naddr, pos

			# Check for finish, kill one for nondeleted characters
			if pos == 0:
				return addr, i
			elif i < len(node) and not node._del[i]:
				pos -= 1
		if fail:
			raise IndexError("pos out of range, longer than len(node.flatten())")
		else:
			return None, pos


########NEW FILE########
__FILENAME__ = test_funcs
# Probably not the most complete test functions, but better than nothing.

def tstring():
	from ConcurrenTree import node
	grey = node.make("grey")
	gc = grey.context()
	gc.live.insert(4, " cat.") # "grey cat."
	gc.live.delete(0, 1) # "rey cat."
	gc.live.delete(7, 1) # "rey cat"
	gc.live.insert(0, "G") # "Grey cat"
	gc.live.insert(8, "!") # "Grey cat!"
	return gc.value == "Grey cat!" or gc.value

def tlist():
	from ConcurrenTree import node
	hello = node.make(["Hello"])
	hc = hello.context()
	hc.live.insert(1, ['world']) # ["Hello", "world"]
	hc.live.delete(0,1) # ["world"]
	hc.live.insert(1, ['wide', 'web']) # ["world", "wide", "web"]
	hc.live.delete(0,2) # ["web"]
	hc.live.insert(1,['site']) # ["web", "site"]
	hc.live.insert(0,['major']) # ["major", "web", "site"]
	hc.live.delete(1,1) # ["major", "site"]
	return hc.value == ["major", "site"] or hc.value

########NEW FILE########
__FILENAME__ = trinary
import context

class TrinaryContext(context.Context):
	# Placeholder class for interface
	pass

########NEW FILE########
__FILENAME__ = document
from ejtp.util.hasher import strict
from ejtp.address import *

from ConcurrenTree import ModelBase
from ConcurrenTree.node import make
from ConcurrenTree.operation import Operation, FromNode

class Document(ModelBase):
	''' Stores a node and tracks operations. '''

	def __init__(self, root={}, applied = [], docname=""):
		self.root = make(root)
		self.docname = docname

		self.own_opsink = True
		self.private = dict({
			'ops':{
				'known'  : {},
				'applied': {}
				# MCP negotiation data should go here too
			}
		})
		for ophash in applied:
			self.applied[ophash] = True;
		self.routing
		self.content

	def apply(self, op, track=True):
		''' Apply an operation and track its application '''
		if self.is_applied(op):
			return
		op.apply(self.root)
		if track:
			ophash = op.hash # cache
			if not ophash in self.applied:
				self.applied[ophash] = True
			if not ophash in self.private['ops']['known']:
				self.private['ops']['known'][ophash] = op.proto()

	def is_applied(self, op):
		return op.hash in self.applied

	def load(self, json):
		self.apply(Operation(json[0]), False)
		self.private = json[1]

	def opsink(self, op):
		#print op.proto()
		self.apply(op)

	def wrapper(self):
		return self.root.wrapper(self.opsink)

	def flatten(self):
		return self.root.flatten()

	def proto(self):
		''' Fully serializes document. Not a terribly fast function. '''
		return [self.root.childop().proto(), self.private]

	def serialize(self):
 		return strict(self.proto())

	def pretty(self):
		# Pretty-prints the JSON content
		print self.wrapper().pretty()

	@property
	def applied(self):
		return self.private['ops']['applied']

	@applied.setter
	def applied(self, new_applied):
		self.private['ops']['applied'] = new_applied

	# Metadata properties

	def prop(self, key, default = {}):
		# Returns a wrapped top-level property
		wrap = self.wrapper()
		if not key in self.root:
			wrap[key] = default
		return wrap[key]

	@property
	def content(self):
		return self.prop("content")

	@property
	def routing(self):
		return self.prop("routing")

	@property
	def about(self):
		return self.prop("about", {
			"version": 0,
			"doctype": None,
			"docname": None,
			"owners" : {},
			"sources": {}
		})

	@property
	def version(self):
		# Document format version, not related to blockchain
		return self.about['version']

	@property
	def permissions(self):
		return self.prop("permissions", {
			"read":{},
			"write":{},
			"graph":{
				"vertices":{},
				"edges"   :{}
			}
		})

	@property
	def owner(self):
		return owner(self.docname)

	# Advanced properties and metadata functions

	@property
	def participants(self):
		# All routing sends and recieves
		if not "routing" in self.root:
			return []
		parts = set()
		routes = self.routing
		for sender in routes:
			parts.add(sender)
			for reciever in routes[sender]:
				parts.add(reciever.strict)
		import json
		return [json.loads(s) for s in parts]

	def add_participant(self, iface, can_read=True, can_write=True):
		routes = self.routing
		striface = strict(iface)
		if can_read:
			self.permissions['read'][striface] = True
		if can_write:
			self.permissions['write'][striface] = True
		if not iface in routes:
			routes[striface] = {}

	def has_permission(self, iface, name):
		# If self.permissions does not already exist, will always return false.
		if "permissions" not in self.root:
			return False
		perm = self.permissions[name]
		return strict(iface) in perm

	def add_permission(self, iface, name):
		self.permissions[name][strict(iface)] = True

	def remove_permission(self, iface, name):
		del self.permissions[name][strict(iface)]

	def can_read(self, iface):
		return self.has_permission(iface, "read")

	def can_write(self, iface):
		return self.has_permission(iface, "write")

	def routes_to(self, iface):
		# Returns which interfaces this interface sends to.
		return [x for x in self.routes_to_unfiltered(iface) if self.can_read(x)]

	def routes_to_unfiltered(self, iface):
		# Does not take read permissions into account.
		istr = strict(iface)
		if istr in self.routing and len(self.routing[istr]) > 0:
			result = set()
			for target in self.routing[istr]:
				result.add(target)
			import json
			return [json.loads(s) for s in result]
		else:
			parts = self.participants
			if iface in parts:
				parts.remove(iface)
			return parts

def mkname(owner, title):
	'''
	Construct a docname.
	>>> mkname("brick", "bat")
	'brick\\x00bat'
	>>> mkname(["brick"], "bat")
	'["brick"]\\x00bat'
	'''
	return "%s\x00%s" % (str_address(owner), title)

def lsname(docname):
	return docname.partition("\x00")

def owner(docname):
	return lsname(docname)[0]

def title(docname):
	return lsname(docname)[1]

########NEW FILE########
__FILENAME__ = event
class EventGrid(object):
    # Stores callbacks (they should take args (evgrid, label))
    def __init__(self, labels=[]):
        self.handlers = {}
        self.reset_current()
        self.setup_labels(labels+['all'])

    def setup_labels(self, labels):
        for i in labels:
            self[i]

    def register(self, label, func):
        # Move to end if already registered
        if func in self[label]:
            self[label].remove(func)
        self[label].append(func)

    def happen(self, label, data={}):
        try:
            self.current_label = label
            callbacks = list(self[label])
            if label != "all":
                callbacks += self['all']
            for i in callbacks:
                self.current_func = i
                i(self, label, data)
        finally:
            self.reset_current()

    def detach(self, label=None, func=None):
        # Can be called with no arguments during a callback to detach itself,
        # or with arguments outside a handler to detach a specific callback.
        label = label or self.current_label
        func  = func  or self.current_func
        if label and func:
            self[label].remove(func)
        else:
            raise ValueError("Insufficient detach information: (%r, %r)" % (self.current_label, self.current_func))

    def reset_current(self):
        self.current_label = None
        self.current_func  = None

    def __getitem__(self, label):
        if not label in self:
            self[label] = []
        return self.handlers[label]

    def __setitem__(self, label, value):
        self.handlers[label] = value

    def __delitem__(self, label):
        del self.handlers[label]

    def __contains__(self, label):
        return label in self.handlers

########NEW FILE########
__FILENAME__ = instruction
from ConcurrenTree import ModelBase, node
from address import Address

def validpos(tree, pos):
	if not (pos <= len(tree) and pos >= 0):
		raise IndexError(pos, len(tree), "0 <= %d <= %d not true!" % (pos, len(tree)))

class Instruction(ModelBase):
	''' General class for all instructions '''

	def __init__(self, value):
		''' Value is a list or Instruction. '''
		if isinstance(value, Instruction):
			self.fromother(value)
		else:
			# Process protocol instruction
			self.fromproto(value)

	def fromproto(self, value):
		''' Sets properties from list. '''
		# TODO: type checking
		value = list(value)
		self.code = value[0]
		self.address = Address(value[1])
		self.additional = value[2:]

	def fromother(self, other):
		''' Sets properties from other instruction. '''
		self.fromproto(other.proto())

	def apply(self, tree, checkfirst = False):
		''' Apply this instruction to a tree. Operation is responsible for calling sanitycheck before applying. '''
		# Resolve tree in question
		tree = self.address.resolve(tree)

		# Sanity check
		if checkfirst:
			self.sanitycheck(tree)

		# Branch based on insertion or deletion
		if self.isinsert:
			self._apply_insert(tree)
		else:
			self._apply_delete(tree)

	def _apply_delete(self, tree):
		for d in self.deletions:
			for i in range(d[0], d[1]+1):
				tree.delete(i)

	def _apply_insert(self, tree):
		vn = self.value_node
		try:
			tree.get(self.position, vn.key)
		except:
			tree.put(self.position, vn)

	def sanitycheck(self, tree):
		''' Check a tree to make sure this instruction can be applied. '''
		if self.isinsert:
			validpos(tree, self.position)
		else:
			for i in self.deletions:
				validpos(tree, i[0])
				validpos(tree, i[1])
				if i[0] > i[1]:
					raise ValueError("Backwards deletion range [%d, %d]" % i)

	def proto(self):
		''' Protocol representation '''
		return [self.code, self.address.proto()] + self.additional

	@property
	def isinsert(self):
		return self.code != 0

	@property
	def position(self):
		return self.additional[0]

	@property
	def value(self):
		return self.additional[1]

	@property
	def value_node(self):
		''' Generates a node for self.value on the fly. '''
		if self.code == 1:
			return node.StringNode(self.value)
		elif self.code == 2:
			return node.MapNode(self.value)
		elif self.code == 3:
			return node.ListNode(self.value)
		elif self.code == 4:
			return node.NumberNode(self.value, self.additional[2])
		elif self.code == 5:
			return node.SingleNode()
		elif self.code == 6:
			return node.TrinaryNode(self.value)
		else:
			raise TypeError("Unknown instruction code, or does not have a value node")

	@property
	def deletions(self):
		result = []
		for i in self.additional:
			if type(i) == int:
				result.append((i,i))
			else:
				result.append(tuple(i))
		return result

def set(array):
	return [Instruction(x) for x in array]

def InsertText(address, pos, value):
	''' Accepts value type str or unicode '''
	return Instruction([1, address, pos, value])

def InsertMap(address, pos, value):
	''' Accepts list of sorted keys as value '''
	return Instruction([2, address, pos, value])

def InsertList(address, pos, value):
	''' Accepts list of descendant node keys as value '''
	return Instruction([3, address, pos, value])

def InsertNumber(address, pos, value, unique):
	''' Accepts list of sorted keys as value '''
	return Instruction([4, address, pos, value, unique])

def InsertSingle(address, pos):
	''' Accepts no value '''
	return Instruction([5, address, pos])

def InsertTrinary(address, pos, value):
	''' Accepts True, False, or None as value '''
	return Instruction([6, address, pos, value])

def InsertNode(address, pos, n):
	''' 
	Determines type of n and returns result of appropriate Insert* function.
	Does not insert children or handle deletions.
	'''

	if type(n) == node.StringNode:
		return InsertText(address, pos, n.value)
	elif type(n) == node.MapNode:
		return InsertMap(address, pos, n.value)
	elif type(n) == node.ListNode:
		return InsertList(address, pos, n.value)
	elif type(n) == node.NumberNode:
		return InsertNumber(address, pos, n.value, n.unique)
	elif type(n) == node.SingleNode:
		return InsertSingle(address, pos)
	elif type(n) == node.TrinaryNode:
		return InsertTrinary(address, pos, n.value)
	else:
		raise TypeError("Cannot create insertion instruction for type "+repr(type(n)))

def Delete(address, *positions):
	return Instruction([0, address]+list(positions))

########NEW FILE########
__FILENAME__ = demo
__doc__ = '''

A demo of how to use the MCP system, as well as a unit test.
Note that this is a sorta silly demo since both gears/clients
are running in the same process and the same MCP router.

'''

### Setting up communication

localip = '127.0.0.1'
bob = ['udp4', [localip, 3939], "bob"]
bridget = ['udp4', [localip, 3940], "bridget"]

def demo_clients():
    '''
    Create a pair of clients, bob and bridget, for testing.
    
    >>> gbob, gbrg = demo_clients()
    >>> gbob.hosts.wrapper
    w<{'content': {'["udp4",["127.0.0.1",3939],"bob"]': {'encryptor': [['rotate', 3], []]}}, 'routing': {}}>
    >>> gbrg.hosts.wrapper
    w<{'content': {'["udp4",["127.0.0.1",3940],"bridget"]': {'encryptor': [['rotate', 7], []]}}, 'routing': {}}>

    >>> gbrg.client #doctest: +ELLIPSIS
    <ejtp.client.Client object at 0x...>
    >>> gbob.client #doctest: +ELLIPSIS
    <ejtp.client.Client object at 0x...>
    '''
    from ConcurrenTree.mcp import engine

    e = engine.Engine()
    gbob = e.make('bob','', bob, encryptor=["rotate", 3], make_jack=False)
    gbrg = e.make('bridget','', bridget, encryptor=["rotate", 7], make_jack=False)
    return (gbob, gbrg)

def demo_clients_enc():
    '''
    Set up clients from demo_clients with encryption data.

    >>> gbob, gbrg = demo_clients_enc()
    >>> gbrg.hosts.crypto_get(bob)
    ['rotate', 3]
    >>> gbrg.hosts.crypto_get(bridget)
    ['rotate', 7]
    >>> gbrg.client.encryptor_cache == gbrg.client_cache
    True
    >>> type(gbrg.client.encryptor_cache)
    <class 'ConcurrenTree.mcp.gear.ClientCache'>
    '''
    gbob, gbrg = demo_clients()
    gbrg.hosts.crypto_set(bob, ["rotate", 3])
    return gbob, gbrg

def demo_clients_hello():
    '''
    Hello stage of the test.

    >>> gbob, gbrg, hello_request = demo_clients_hello()
    >>> hello_request #doctest: +ELLIPSIS
    <ConcurrenTree.validation.hello.HelloRequest object at ...>

    >>> gbob.hosts.crypto_get(bridget)
    ['rotate', 7]
    '''
    gbob, gbrg = demo_clients_enc()
    gbrg.writer.hello(bob)
    hello_request = gbob.gv.pop()
    hello_request.approve()
    return gbob, gbrg, hello_request


### Track 1 Ops

def demo_documents():
    '''
    From here on, a lot more variables will get passed around.

    >>> gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg = demo_documents()
    >>> gbob.owns(helloname)
    True
    '''
    from ConcurrenTree.document import mkname
    gbob, gbrg, _ = demo_clients_hello()
    helloname = mkname(bob, "hello")
    hellobob  = gbob.document(helloname)
    hellobrg  = gbrg.document(helloname)
    hwbob = hellobob.content
    hwbrg = hellobrg.content
    return gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg

def demo_participants():
    '''
    Add Bridget as a participant of the document.
    '''
    gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg = demo_documents()
    gbob.add_participant(helloname, bridget)
    gbob.send_full(helloname, [bridget])
    return gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg

def demo_data():
    '''
    Demonstrate data transfer.
    
    >>> gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg = demo_data()
    >>> hwbrg
    w<{'Blabarsylt': 'Made of blueberries', u'goofy': 'gorsh'}>
    >>> hwbob
    w<{u'Blabarsylt': 'Made of blueberries', 'goofy': 'gorsh'}>
    '''
    gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg = demo_participants()
    hwbob["goofy"] = "gorsh"
    hwbrg["Blabarsylt"] = "Swedish jelly"
    hwbrg["Blabarsylt"] = "Made of blueberries"
    return gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg

### RSA

# Will do later


########NEW FILE########
__FILENAME__ = engine
from gear import Gear

class Engine(object):
	# Produces gears

	def __init__(self, auth=None, router=None):
		self.auth = auth or default_auth()
		self.router = router or default_router()

	def make(self, username, password, interface, **kwargs):
		return self.gear(self.auth.make(username, password), interface, **kwargs)

	def gear(self, storage, interface, **kwargs):
		return Gear(storage, self.router, interface, **kwargs)

def default_auth():
	from ConcurrenTree.auth import Auth
	return Auth()

def default_router():
	from ejtp import router
	return router.Router()

########NEW FILE########
__FILENAME__ = gear
from ejtp import frame, address as ejtpaddress, client as ejtpclient

from ConcurrenTree import document, event

import host_table
import message as mcp_message
import gear_validator
import demo

from sys import stderr
import json

class Gear(object):
	# Tracks clients in router, and documents.
	def __init__(self, storage, router, interface, encryptor=None, make_jack=True):
		self.storage = storage
		self.router = router

		# Components
		self.evgrid = event.EventGrid([
			'recv_index',
			'recv_op',
			'recv_snapshot',
			'recv_error',
		])
		self.writer = mcp_message.Writer(self)
		self.reader = mcp_message.Reader(self)
		self.client_cache = ClientCache(self)
		self.client = setup_client(self, interface, make_jack)
		self.gv = gear_validator.GearValidator(self)
		
		self.hosts = host_table.HostTable(self.document('?host'))
		if encryptor != None:
                        self.hosts.crypto_set(interface, encryptor)

		self.storage.listen(self.on_storage_event)

	# On-the-fly document creation and retrieval (Get-or-create semantics)

	def document(self, docname):
		doc = self.storage.doc_get(docname)
		return self.setdocsink(docname)

	def setdocsink(self, docname):
		# Set document operation sink callback and add owner with full permissions
		doc = self.storage.doc_get(docname)
		if doc.own_opsink:
			# Prevent crazy recursion
			doc.own_opsink = False

			# Add owner with full permissions
			try:
				owner = json.loads(document.owner(docname))
				self.add_participant(docname, owner)
			except ValueError:
				pass # No author could be decoded

			# Define opsink callback
			def opsink(op):
				if self.can_write(None, docname):
					self.storage.op(docname, op)
				else:
					print "Not applying op, you don't have permission"

			# Set document to use the above function
			doc.opsink = opsink
		return doc

	# Sender functions

	def send_full(self, docname, targets=[]):
		'''
		Send a full copy of a document.

		>>> gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg = demo.demo_participants()
		>>> gbob.can_read(demo.bridget, helloname)
		True
		>>> gbrg.can_read(demo.bridget, helloname)
		True
		>>> gbob.can_write(demo.bridget, helloname)
		True
		>>> gbrg.can_write(demo.bridget, helloname)
		True
		>>> gbrg.can_write(None, helloname)
		True
		'''
		doc = self.document(docname)
		self.writer.op(docname, doc.root.childop(), targets)

	# Callbacks for incoming data

	def rcv_callback(self, msg, client):
		self.reader.read(msg.ciphercontent, msg.addr)

	def on_storage_event(self, typestr, docname, data):
		# Callback for storage events
		if typestr == "op":
			self.writer.op(docname, data)

	# Utilities and conveninence functions.

	@property
	def interface(self):
		return self.client.interface

	def owns(self, docname):
		# Returns bool for whether document owner is a client.
		owner = document.owner(docname)
		return owner == ejtpaddress.str_address(self.interface)

	def add_participant(self, docname, iface):
		'''
		Adds person as a participant, does not send them data though.

		>>> gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg = demo.demo_documents()
		>>> hellobob.routes_to(demo.bob)
		[]
		>>> gbob.add_participant(helloname, demo.bridget)
		>>> hellobob.routes_to(demo.bob) == [demo.bridget]
		True
		'''
		doc = self.document(docname)
		doc.add_participant(iface)

	def can_read(self, iface, docname):
		# Returns whether an interface can read a document.
		# If iface == None, assumes self.interface
		if self.owns(docname) or docname[0] == "?":
			return True

		if iface == None:
			iface = self.interface

		doc = self.document(docname)
		return doc.can_read(iface)

	def can_write(self, iface, docname):
		# Returns whether an interface can write a document.
		# If iface == None, assumes self.interface
		if self.owns(docname) or docname[0] == "?":
			return True

		if iface == None:
			iface = self.interface

		doc = self.document(docname)
		return doc.can_write(iface)

class ClientCache(object):
	def __init__(self, gear):
		self.gear = gear

	def __getitem__(self, k):
		return self.gear.hosts.crypto_get(k)

	def __setitem__(self, k, i):
		self.gear.hosts.crypto_set(k, i)

# EJTP client setup

def setup_client(gear, interface, make_jack):
	client = ejtpclient.Client(gear.router, interface, gear.client_cache, make_jack = make_jack)
	client.rcv_callback = gear.rcv_callback
	return client

########NEW FILE########
__FILENAME__ = gear_validator
import ConcurrenTree.validation as validation

class GearValidator(object):
	def __init__(self, gear):
		self.gear = gear
		self.queue = validation.ValidationQueue(filters = std_gear_filters)
		self.queue.gear = gear

	def validate(self, request):
		self.queue.filter(request)
		return request

	def pop(self):
		# Get the next item out of the queue
		return self.queue.pop()

	def op(self, author, docname, op):
		def callback(result):
			if result:
				self.gear.storage.op(docname, op)
			else:
				print "Rejecting operation for docname: %r" % docname
		return self.validate(
			validation.make("operation", author, docname, op, callback)
		)

	def hello(self, author, encryptor):
		def callback(result):
			if result:
				self.gear.hosts.crypto_set(author, encryptor)
			else:
				print "Rejecting hello from sender: %r" % encryptor
		return self.validate(
			validation.make("hello", author, encryptor, callback)
		)

# FILTERS

def filter_op_approve_all(queue, request):
	if isinstance(request, validation.OperationRequest):
		return request.approve()
	return request

def filter_op_is_doc_stored(queue, request):
	if isinstance(request, validation.OperationRequest):
		if not request.docname in queue.gear.storage:
			queue.gear.writer.error(request.author, message="Unsolicited op")
			return request.reject()
	return request

def filter_op_can_write(queue, request):
	if isinstance(request, validation.OperationRequest):
		if not queue.gear.can_write(request.author, request.docname):
			queue.gear.writer.error(request.author, message="You don't have write permissions.")
			return request.reject()
	return request

std_gear_filters = [
	filter_op_is_doc_stored,
	filter_op_can_write,
	filter_op_approve_all,
]

########NEW FILE########
__FILENAME__ = host_table
from ejtp.address import *

class HostTable(object):
	def __init__(self, document=None):
		'''
		Convenience wrapper for host resolution tables.

		>>> hosty = HostTable()
		>>> hosty.document #doctest: +ELLIPSIS
		<ConcurrenTree.document.Document object at ...>
		>>> hosty.wrapper
		w<{'content': {}, 'routing': {}}>

		'''
		if document == None:
			from ConcurrenTree.document import Document
			document = Document()
		self.document = document
		self.wrapper = self.document.wrapper()

	# Access --------------------------------------------------------------

	def __getitem__(self, k):
		return self.wrapper['content'][k]

	def __setitem__(self, k, i):
		self.wrapper['content'][k] = i

	def __delitem__(self, k):
		del self.wrapper['content'][k]

	def __contains__(self, k):
		k = str_address(k)
		return k in self.wrapper['content']

	def get(self, address):
		'''
		Ensures that address is in string form, before returning
		the host data from the table.

		>>> hosty = HostTable()
		>>> addr = ['vaporware', ['bob'], 'catalina']
		>>> addr in hosty
		False
		>>> hosty.get(addr)
		w<{}>
		>>> addr in hosty
		True
		>>> hosty.set(addr, {'vikings':'pillagers'})
		>>> hosty.get(addr)
		w<{'vikings': 'pillagers'}>
		>>> addr in hosty
		True
		''' 
		address = str_address(address)
		if not address in self:
			self.set(address, {})
		return self[address]

	def set(self, address, i):
		'''
		Sets the data in the host document for a specific address.
		'''
		address = str_address(address)
		self[address] = i

	def destroy(self, address):
		'''
		Removes a host from the records.

		>>> hosty = HostTable()
		>>> addr = ['vaporware', ['bob'], 'catalina']
		>>> hosty.set(addr, {'vikings':'pillagers'})
		>>> hosty.get(addr)
		w<{'vikings': 'pillagers'}>
		>>> hosty.destroy(addr)
		>>> addr in hosty
		False
		'''
		address = str_address(address)
		del self[address]

	# Cryptography --------------------------------------------------------

	def crypto_set(self, iface, proto):
		'''
		Set encryptor information for an interface address.

		>>> hosty = HostTable()
		>>> addr = ['vaporware', ['bob'], 'catalina']
		>>> hosty.crypto_get(addr)
		Traceback (most recent call last):
		KeyError: 'encryptor'
		>>> hosty.crypto_set(addr, ['whalecipher', 'awooga'])
		>>> hosty.crypto_get(addr)
		['whalecipher', 'awooga']
		'''
		self.get(iface)['encryptor'] = [proto, []]

	def crypto_get(self, iface):
		return self.get(iface)['encryptor'].value[0]

########NEW FILE########
__FILENAME__ = message
from ejtp.util.crashnicely import Guard
from ejtp.util.hasher import strict
from ConcurrenTree import operation
from demo import bob, bridget, demo_data
from sys import stderr
import random
import json

class MessageProcessor(object):

	# Convenience accessors

	@property
	def client(self):
		return self.gear.client

	@property
	def hosts(self):
		return self.gear.hosts

	@property
	def interface(self):
		return self.gear.interface

class Writer(MessageProcessor):
	def __init__(self, gear):
		self.gear = gear

	def send(self, target, data, wrap_sender=True):
		data['ackc'] = str(random.randint(0, 2**32))
		self.client.write_json(target, data, wrap_sender)

	# Message creators

	def hello(self, target):
		# Send your EJTP encryption credentials to an interface
		self.send(target,
			{
				'type':'mcp-hello',
				'interface':self.interface,
				'key':self.hosts.crypto_get(self.interface),
			},
			False,
		)

	def error(self, target, code=500, message="", data={}):
		self.send(target, {
			"type":"mcp-error",
			"code":code,
			"msg":message,
			"data":data
		})

	def op_callback(self, target, docname, op_hash, callback):
		'''
		Set up a conditional, self-detaching callback for an expected op msg.
		'''
		if callback:
			def wrapped_callback(grid, label, data):
				if match(data, {
						'type':'mcp-error',
						'code':321,
						'sender':target,
						'data':{
							'res_type':'op',
							'id':op_hash
						}
					}):
					grid.detach()
					grid.detach('recv_op')
					return
				elif match(data, {
   						'type':'mcp-op',
						'docname':docname,
						'sender':target,
					}) and data['op'].hash == op_hash:
					grid.detach()
					grid.detach('recv_error')
					callback(grid, label, data)
			self.gear.evgrid.register('recv_error', wrapped_callback)
			self.gear.evgrid.register('recv_op', wrapped_callback)

	def pull_op(self, target, docname, op_hash, callback=None):
		'''
		Pull one op (shorthand alias to pull_ops, basically)

		>>> gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg = demo_data()
		>>> ophash = '079eeae801303fd811fe3f443c66528a6add7e42' # Real op
		>>> def callback(grid, label, data):
		...	 print "YES, THIS IS CALLBACK"
		...	 print data['op'].hash
		...	 print data['op'].hash == ophash
		>>> gbob.writer.pull_op(bridget, helloname, ophash, callback)
		YES, THIS IS CALLBACK
		079eeae801303fd811fe3f443c66528a6add7e42
		True
		>>> gbob.writer.pull_op(bridget, helloname, ophash) # Make sure callback is cleared
		'''
		self.op_callback(target, docname, op_hash, callback)
		self.pull_ops(target, docname, [op_hash])

	def pull_ops(self, target, docname, hashes, callback=None):
		'''
		Retrieve one or more operations by instruction hash.

		The callback will be called for every op response where the hash
		is present, so it's 

		>>> gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg = demo_data()
		>>> ophashes = [
		...    '079eeae801303fd811fe3f443c66528a6add7e42', # Real op
		...    'X79eeae801303fd811fe3f443c66528a6add7e42', # Real op
		... ]

		>>> gbob.writer.pull_op(bridget, helloname, ophashes[0]) # Real op
		>>> gbob.writer.pull_op(bridget, helloname, ophashes[1]) # Fake op
		Error from: [u'udp4', [u'127.0.0.1', 3940], u'bridget'] , code 321
		u'Resource not found'
		{"id":"X79eeae801303fd811fe3f443c66528a6add7e42","res_type":"op"}

		>>> gbob.writer.pull_ops(bridget, helloname, ophashes) # Both
		Error from: [u'udp4', [u'127.0.0.1', 3940], u'bridget'] , code 321
		u'Resource not found'
		{"id":"X79eeae801303fd811fe3f443c66528a6add7e42","res_type":"op"}

		>>> def callback(grid, label, data):
		...    print "hash:", data['op'].hash
		>>> gbob.writer.pull_ops(bridget, helloname, ophashes, callback) # Both 
		hash: 079eeae801303fd811fe3f443c66528a6add7e42
		Error from: [u'udp4', [u'127.0.0.1', 3940], u'bridget'] , code 321
		u'Resource not found'
		{"id":"X79eeae801303fd811fe3f443c66528a6add7e42","res_type":"op"}
		>>> gbob.evgrid['recv_op'] # Ensure that the error clears out the callback
		[]
		'''
		for op_hash in hashes:
			self.op_callback(target, docname, op_hash, callback)
		self.send(target, {
			"type":"mcp-pull-ops",
			"docname": docname,
			"hashes":hashes,
		})

	def op(self, docname, op, targets=[]):
		# Send an operation frame.
		# targets defaults to document.routes_to for every sender.
		proto = op.proto()
		proto['type'] = 'mcp-op'
		proto['docname'] = docname

		targets = targets or self.gear.document(docname).routes_to(self.interface)

		for i in targets:
			self.send(i, proto)

	def pull_index(self, target, docname, callback=None):
		'''
		Retrieve a remote source's personal index for a document.

		>>> gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg = demo_data()
		>>> def callback(grid, label, data):
		...    hashes = data['hashes']
		...    sorted_keys = hashes.keys()
		...    sorted_keys.sort()
		...    for key in sorted_keys:
		...        print "%s: %r" % (key, hashes[key])
		>>> gbob.writer.pull_index(bridget, helloname)
		>>> gbob.writer.pull_index(bridget, helloname, callback)
		079eeae801303fd811fe3f443c66528a6add7e42: u'\\\\_2^[Z\\\\2Z2*/Z)*_-]+Z*\\\\2./ZZ^*.))1_Z++*)['
		34004f4763524e87cfe4f5b5f915266f80bbbfe7: u'+0_].)]^Z[_1_++)Z/.,-_2*[[^00/0\\\\,*-*.)-+'
		44d0cb0c7e9b77eb053294915fdb031abd98adc5: u'\\\\[../)[_,+2)/\\\\Z)Z)^0/**.Z0_[/[*^[*_]./]\\\\'
		45e9f1b0334e99aac9c012b1cd1e25a2ce18c5d7: u'10)0Z.-.]+*0*\\\\.^\\\\,)//,.,_21-+[[*Z]Z2-\\\\/['
		47b01407c24b8be47fe5df780f4959c01be196ae: u'^_1[,0\\\\2].*_,_Z^2+*]2*-1/0+-1Z,\\\\[[2\\\\Z+0.'
		790742eb7a29172333fe025c2622ea18c5286d68: u'],-^-2,_)]2.[)/\\\\10Z\\\\\\\\-\\\\[2\\\\Z-+ZZZ21*2\\\\0.,'
		9bf7b64433a119b91b8790b3697712db8ee5b090: u'*[\\\\\\\\20\\\\1[\\\\0\\\\Z.2,[0^Z.+-^0^])0Z\\\\[.*^2Z))*'
		bc41162db8b81392569a5bedf52c7414212df665: u'^0**/0.^,0])\\\\_Z^0**0])^\\\\0^_0-000.2--,]\\\\_'
		c5467b8ced86280298b6df359835e23bf9742ca7: u'\\\\1,2^/^[1-.1]),2^,.Z/+0,[],.\\\\^*-)1).)/*1'
		d251f86d43c808ee5cbe8231ca8545419649d7c0: u']^\\\\,\\\\2.0[0^^+Z*]+0*21_1]Z2+-/2Z.^000))+.'
		ed61a0b09322e3b5e0361a015c275f7e46057d52: u',Z[/.1^^.^/]^\\\\0/2221*_0\\\\Z[).^[,/_\\\\\\\\_-,[]'
		>>> gbob.writer.pull_index(bridget, helloname)
	 
		'''
		if callback:
			def wrapped_callback(grid, label, data):
				if data['docname'] == docname and data['sender'] == target:
					grid.detach()
					callback(grid, label, data)
			self.gear.evgrid.register('recv_index', wrapped_callback)
		self.send(target, {
			"type":"mcp-pull-index",
			"docname":docname,
		})

	def index(self, target, docname, hashes):
		self.send(target, {
			"type":"mcp-index",
			"docname":docname,
			"hashes":hashes,
		})

	def pull_snapshot(self, target, docname, callback=None):
		'''
		Retrieve a flattened copy of the document from a remote.

		>>> gbob, gbrg, helloname, hellobob, hellobrg, hwbob, hwbrg = demo_data()
		>>> def callback(grid, label, data):
		...    content = data['content']
		...    keys = content.keys()
		...    keys.sort()
		...    for k in keys:
		...        print k, ":", strict(content[k])
		>>> gbob.writer.pull_snapshot(bridget, helloname)
		>>> gbob.writer.pull_snapshot(bridget, helloname, callback)
		content : {"Blabarsylt":"Made of blueberries","goofy":"gorsh"}
		permissions : {"graph":{"edges":{},"vertices":{}},"read":{"[\\"udp4\\",[\\"127.0.0.1\\",3939],\\"bob\\"]":true,"[\\"udp4\\",[\\"127.0.0.1\\",3940],\\"bridget\\"]":true},"write":{"[\\"udp4\\",[\\"127.0.0.1\\",3939],\\"bob\\"]":true,"[\\"udp4\\",[\\"127.0.0.1\\",3940],\\"bridget\\"]":true}}
		routing : {"[\\"udp4\\",[\\"127.0.0.1\\",3939],\\"bob\\"]":{},"[\\"udp4\\",[\\"127.0.0.1\\",3940],\\"bridget\\"]":{}}
		
		'''
		if callback:
			def wrapped_callback(grid, label, data):
				if data['docname'] == docname and data['sender'] == target:
					grid.detach()
					callback(grid, label, data)
			self.gear.evgrid.register('recv_snapshot', wrapped_callback)
		self.send(target, {
			"type":"mcp-pull-snapshot",
			"docname":docname,
		})

	def snapshot(self, target, docname, snapshot):
		self.send(target, {
			"type":"mcp-snapshot",
			"docname":docname,
			"content":snapshot
		})

	def ack(self, target, codes):
		self.send(target, {
			"type":"mcp-ack",
			"ackr":codes,
		})

class Reader(MessageProcessor):
	def __init__(self, gear):
		self.gear = gear

	def acknowledge(self, content, sender):
		if 'ackc' in content and content['type'] != 'mcp-ack':
			ackc = content['ackc']
			self.gear.writer.ack(sender, [ackc])
			return False
		elif 'ackr' in content and content['type'] == 'mcp-ack':
			return True
		else:
			print>>stderr, "Malformed frame:\n%s" % json.dumps(content, indent=2)

	def read(self, content, sender=None):
		try:
			content = json.loads(content)
		except:
			print "COULD NOT PARSE JSON:"
			print content
		t = content['type']
		if self.acknowledge(content, sender): return
		fname = t.replace('-','_')
		if hasattr(self, fname):
			return getattr(self, fname)(content, sender)
		else:
			print "Unknown msg type %r" % t

	# Message handlers

	def mcp_hello(self, content, sender):
		self.gear.gv.hello(content['interface'], content['key'])

	def mcp_op(self, content, sender):
		docname = content['docname']
		op = operation.Operation(content['instructions'])
		vrequest = self.gear.gv.op(sender, docname, op)
		self.gear.evgrid.happen('recv_op', {
			'type':'mcp-op',
			'docname':docname,
			'op':op,
			'sender':sender,
			'vrequest':vrequest,
		})

	def mcp_pull_index(self, content, sender):
		docname = content['docname']
		doc = self.gear.document(docname)
		result = {}
		for x in doc.applied:
			result[x] = self.client.sign(x)
		self.gear.writer.index(sender, docname, result)

	def mcp_index(self, content, sender):
		content['sender'] = sender
		self.gear.evgrid.happen('recv_index', content)

	def mcp_pull_snapshot(self, content, sender):
		docname = content['docname']
		doc = self.gear.document(docname)
		self.gear.writer.snapshot(sender, docname, doc.flatten())

	def mcp_snapshot(self, content, sender):
		content['sender'] = sender
		self.gear.evgrid.happen('recv_snapshot', content)

	def mcp_pull_ops(self, content, sender):
		docname = content['docname']
		hashes = content['hashes']
		doc = self.gear.document(docname)
		known_ops = doc.private['ops']['known']

		for h in hashes:
			if h in known_ops:
				op_proto = known_ops[h]
				op = operation.Operation(instructions = op_proto['instructions'])
				self.gear.writer.op(docname, op, [sender])
			else:
				self.gear.writer.error(sender,
					code     = 321,
					message  = "Resource not found",
					data     = {
						'res_type': 'op',
						'id':h,
					}
				)

	def mcp_error(self, content, sender):
		print "Error from:", sender, ", code", content["code"]
		print repr(content['msg'])
		if 'data' in content and content['data']:
			print strict(content['data'])
		content['sender'] = sender
		self.gear.evgrid.happen('recv_error', content)

def match(d1, d2):
	'''
	Tests if dict d1 matches the template of properties given by d2.

	>>> match({}, {'horse':'feathers'})
	False
	>>> match({'horse':'saddles'}, {'horse':'feathers'})
	False
	>>> match({'horse':'feathers'}, {})
	True
	>>> match({'horse':'feathers'}, {'horse':'feathers'})
	True
	'''
	for key in d2:
		if (not key in d1) or d1[key] != d2[key]:
			d1val = None
			if key in d1:
				d1val = d1[key]
			return False
	return True

########NEW FILE########
__FILENAME__ = list
import node
from ejtp.util.hasher import strict

class ListNode(node.Node):

	def __init__(self, value=[]):
		node.Node.__init__(self)
		try:
			self._value = value
		except:
			raise TypeError("ListNode value must list of keys")
		self._length = sum(x for x in value if type(x)==int) + \
			len([None for x in value if type(x)!=int])
		self.limit = {}
		i = 0
		for x in value:
			if type(x)==int:
				i += x
			else:
				self.limit[i] = x
				i += 1
		self._children = [node.ChildSet() for i in range(self.biglength)]
		self._del = [False for i in range(len(self))]

	@property
	def value(self):
		return self._value

	@property
	def key(self):
		return self.keysum(strict(self.value))

	def flatten(self):
		result = []
		for i in range(len(self)+1):
			for c in self.index(i):
				result += self.index(i)[c].flatten()
			if i<len(self) and not self._del[i]:
				val = None
				if len(self.elem(i)) > 0:
					val=self.elem(i).head.flatten()
				result.append(val)
		return result

	def _get(self, pos, key):
		return self._children[pos][key]

	def _put(self, pos, n):
		if pos < len(self) and n.key != self.value[pos]:
			raise ValueError("Node has key "+repr(n.key)+
				", expected key "+repr(self.value[pos]))
		self._children[pos].insert(n)

	def _delete(self, pos):
		self._del[pos] = True

	@property
	def _deletions(self):
		return node.enumerate_deletions(self._del)

	def __len__(self):
		return self._length

	def __getitem__(self, i):
		return self._value[i]

	def index(self, i):
		return self._children[i+len(self)]

	def elem(self, i):
		return self._children[i]

	@property
	def biglength(self):
		# Total number of slots for children
		return 2*len(self)+1

########NEW FILE########
__FILENAME__ = map
import node
import single
from ejtp.util import hasher

class MapNode(node.Node):
	def __init__(self, limit={}, source={}):
		node.Node.__init__(self)
		self._value = limit
		self._data = {}
		for k in self.value:
			if isinstance(self.value[k], node.Node):
				self._value[k] = self.value[k].key
			print "Setting limit on", k
			s = single.SingleNode(limit=self.value[k])
			self[k] = s
		self.update(source)

	def update(self, source):
		# Items must already be nodes
		for k in source:
			s = single.SingleNode()
			s.put(0, source[k])
			self[k] = s

	@property
	def value(self):
		return self._value

	@property
	def key(self):
		return self.keysum(hasher.strict(self.value))

	def flatten(self):
		result = {}
		for i in self._data:
			result[i] = self._data[i].flatten()
			if result[i] == None:
				del result[i]
		return result

	def _get(self, pos, key):
		# Due to mapping semantics, "pos" is the key, and "key" must be "/single".
		if key != "/single":
			raise KeyError("Mapping can only contain SingleNodes")
		if type(pos) not in (unicode, str):
			raise TypeError("pos must be str")
		return self._data[pos]

	def _put(self, pos, obj):
		# "pos" should be a string key.
		if type(pos) not in (unicode, str):
			raise TypeError("pos must be str, got %r instead" % pos)
		if not isinstance(obj,single.SingleNode):
			raise TypeError("obj must be a SingleNode")
		self._data[pos] = obj

	def _delete(self, pos):
		raise node.Undelable()

	@property
	def children(self):
		result = {}
		for k in self:
			result[k] = {"/single":self[k].hash}
		return result

	@property
	def deletions(self):
		return []

	def resolve(self, addrlist):
		if len(addrlist) == 0:
			return self
		else:
			return self.get(addrlist[0],addrlist[1]).resolve(addrlist[2:])

	# Plumbing

	def __iter__(self):
		return self._data.__iter__()

	def __getitem__(self, key):
		return self.get(key, "/single")

	def __setitem__(self, key, obj):
		self.put(key, obj)

########NEW FILE########
__FILENAME__ = node
from ejtp.util import hasher

from ConcurrenTree import ModelBase, event
from ConcurrenTree.address import Address

class Node(ModelBase):
	''' Base class for all node types. '''

	def __init__(self):
		self.evgrid = event.EventGrid([
			'insert',
			'delete',
			'childinsert',
			'childdelete',
			])

	# Stuff to be filled in by subclass:

	@property
	def value(self):
		''' Immutable value used to generate keys '''
		raise NotImplementedError("Subclasses of Node must provide property 'value'")

	@property
	def key(self):
		''' 1-16 char long string '''
		raise NotImplementedError("Subclasses of Node must provide property 'key'")

	def flatten(self):
		''' Current value in Python types '''
		raise NotImplementedError("Subclasses of Node must provide function 'flatten'")

	def _get(self, pos, key):
		''' Retrieves child at position "pos" and key "key" '''
		raise NotImplementedError("Subclasses of Node must provide function 'get'")

	def _put(self, pos, obj):
		''' Set a child at pos, acquiring the key from the object's .key property '''
		raise NotImplementedError("Subclasses of Node must provide function 'put'")

	def _delete(self, pos):
		''' Mark value[pos] as deleted '''
		raise NotImplementedError("Subclasses of Node must provide function 'delete'")

	# Properties to be defined by subclass:

		# self._deletions - list of deleted positions
		# self._children  - list of node.ChildSets

		# If you define self.deletions and self.children, respectively,
		# self._deletions and self._children will not be used externally.

	# Provided by base class:

	def get(self, pos, key):
		return self._get(pos, key)

	def put(self, pos, n):
		self._put(pos, n)
		n.register('insert', lambda grid, label, data: self.evgrid.happen('childinsert'))
		n.register('delete', lambda grid, label, data: self.evgrid.happen('childdelete'))
		self.evgrid.happen('insert')

	def delete(self, pos):
		self._delete(pos)
		self.evgrid.happen('delete')

	def register(self, *args):
		self.evgrid.register(*args)

	@property
	def deletions(self):
		''' Return a compressed list of deletions '''
		return compress_deletions(self._deletions)

	@property
	def children(self):
		''' Return a dict of position: childhashes, each of which is a dict of key:hash. '''
		positions = {}
		for p in range(len(self._children)):
			if self._children[p]:
				positions[p] = self._children[p].proto()
		return positions

	def proto(self):
		return [self.key, self.children, self.deletions]

	def apply(self, op):
		''' For operations, instructions, and anything else that takes self.apply(tree) '''
		op.apply(self)

	def keysum(self, string):
		return hasher.key(string)

	def resolve(self, addrlist):
		''' Map overrides this '''
		addrlist = list(addrlist)
		if len(addrlist) == 0:
			return self
		if type(addrlist[0])==int:
			pos = addrlist[0]
			key = addrlist[1]
			return self.get(pos, key).resolve(addrlist[2:])
		else:
			pos = len(self)
			key = addrlist[0]
			return self.get(pos, key).resolve(addrlist[1:])

	# High level imports

	def context(self, *args):
		from ConcurrenTree import context
		return context.make(self, *args)

	def wrapper(self, *args):
		from ConcurrenTree import wrapper
		return wrapper.make(self, *args)

	def op(self, pos, addr = []):
		from ConcurrenTree import operation
		addr = Address(addr)
		return addr + operation.FromNode(self, pos)

	def childop(self):
		from ConcurrenTree import operation
		return operation.FromChildren(self)

class UnsupportedInstructionError(Exception): pass

class Unputable(UnsupportedInstructionError): pass
class Ungetable(UnsupportedInstructionError): pass
class Undelable(UnsupportedInstructionError): pass

class ChildSet:
	def __init__(self, types=None, limit=None):
		if types != None:
			try:
				self.types = tuple(types)
			except TypeError:
				self.types = (types,)
		else:
			self.types = None
		self.limit = limit
		self.children = {}

	def insert(self, obj):
		self[obj.key] = obj

	def validtype(self, value):
		for i in self.types:
			if isinstance(value, i): return True
		return False

	def proto(self):
		result = {}
		for i in self:
			result[i] = self[i].hash
		return result

	def __setitem__(self, key, value):
		if self.types != None and not self.validtype(value):
			raise TypeError("Must be of one of the types: "+repr(self.types))
		if type(key) != str or len(key)<1 or len(key)>16:
			raise KeyError("Key must be a string of 1-16 characters")
		if key != value.key:
			raise ValueError("Key mismatch: cannot insert object with key %s as key %s" % (repr(value.key), repr(key)))
		if self.limit != None and key != self.limit:
			raise ValueError("Childset only accepts key "+self.limit)
		if key in self:
			print "Warning: clobbering over key "+repr(key)
		self.children[key] = value

	def __contains(self, key):
		return key in self.children

	def __getitem__(self, key):
		return self.children[key]

	def __delitem__(self, key):
		del self.children[key]

	def __iter__(self):
		return self.sorted.__iter__()

	def __len__(self):
		return len(self.children)

	@property
	def sorted(self):
		keys = self.children.keys()
		keys.sort()
		# always have "/single" win
		if "/single" in keys:
			keys.remove("/single")
			keys.append("/single")
		return keys

	@property
	def values(self):
		return [self[x] for x in self.sorted]

	@property
	def head(self):
		''' Child with highest key '''
		return self.values[-1]

	@property
	def tail(self):
		''' Child with lowest key '''
		return self.values[0]

def enumerate_deletions(l):
	''' Takes a list of bools and return a list of the positions in l where l[i] is true '''
	return [i for i in range(len(l)) if l[i]]

def compress_deletions(l):
	''' Takes a list of deleted positions, returns list of ints and ranges '''
	l.sort()
	stream = []
	start = None
	current = None
	for p in l:
		if start == None:
			start = p
			current = p
		else:
			if p == current + 1:
				current = p
			else:
				# append to stream
				if start == current:
					stream.append(start)
				else:
					stream.append((start, current))
				start = p
				current = p
	if start != None:
		if start == current:
			stream.append(start)
		else:
			stream.append((start, current))

	return stream

def ce_deletions(l):
	''' Enumerate and compress a deltetion list in one step. '''
	return compress_deletions(enumerate_deletions(l))

########NEW FILE########
__FILENAME__ = number
import node
import json

class NumberNode(node.Node):

	def __init__(self, value, unique):
		node.Node.__init__(self)
		self._value = str(value) # Store value as string to avoid loss of precision
		self.unique = int(unique)
		self._children = [node.ChildSet(NumberNode)]

	# Node interface

	@property
	def value(self):
		return self._value

	@property
	def key(self):
		return self.keysum("n%d/%d" % (
			int(json.loads(self.value)),
			self.unique
		))

	def flatten(self):
		result = json.loads(self.value)
		for i in self._children[0].values:
			result += i.flatten()
		return result

	def _get(self, pos, key):
		if pos != 0:
			raise IndexError("NumberNode only has children at position 0.")
		return self._children[0][key]

	def _put(self, pos, obj):
		if pos != 0:
			raise IndexError("NumberNode only has children at position 0.")
		self._children[0].insert(obj)

	def _delete(self, pos):
		raise node.Undelable("NumberNode does not support deletion")

	@property
	def deletions(self):
		return []

	def resolve(self, addr):
		if len(addr)==0:
			return self
		else:
			return self.get(0, addr[0]).resolve(addr[1:])

	# Extra

	def head(self):
		# return (addr, node) for deepest node
		winner = ([], self)
		for i in self._children[0]:
			addr, n = self.get(0,i).head()
			addr = [i] + addr
			if len(addr) > len(winner[0]):
				winner = addr, n
		return winner

########NEW FILE########
__FILENAME__ = single
import node

class SingleNode(node.Node):
	def __init__(self, limit=None):
		node.Node.__init__(self)
		self.limit = limit
		self._children = [node.ChildSet(limit=self.limit),
			node.ChildSet(types=(SingleNode,))]

	# Node interface

	@property
	def value(self):
		return ""

	@property
	def key(self):
		return "/single"

	def flatten(self):
		v = self.head()[1].value_node()
		if v:
			return v.flatten()
		else:
			return None

	def _get(self, pos, key):
		return self._children[pos][key]

	def _put(self, pos, obj):
		self._children[pos].insert(obj)

	def _delete(self):
		raise node.Undelable("SingleNodes do not support deletion. Recursive set to null instead.")

	@property
	def deletions(self):
		return []

	# Extra
	def head(self):
		if len(self._children[1]) > 0:
			addr, node = self._children[1]['/single'].head()
			return [1, '/single'] + addr, node
		else:
			return [], self

	def value_node(self):
		if len(self._children[0]) > 0:
			return self._children[0].head
		else:
			return None

	def __len__(self):
		return 2

########NEW FILE########
__FILENAME__ = string
import node

class StringNode(node.Node):
	def __init__(self, value):
		node.Node.__init__(self)
		try:
			self._value = str(value)
		except:
			raise TypeError("StringNode value must str, or something that can be turned into one")
		self._length = len(self._value)
		self._children = [node.ChildSet((StringNode,)) for i in range(len(self)+1)]
		self._del = [False for i in range(len(self))]

	@property
	def value(self):
		return self._value

	@property
	def key(self):
		return self.keysum("t"+self.value)

	def flatten(self):
		result = ""
		for i in range(len(self)+1):
			for child in self._children[i].values:
				result += child.flatten()
			if i < len(self) and not self._del[i]:
				result += self[i]
		return result

	def _get(self, pos, key):
		return self._children[pos][key]

	def _put(self, pos, obj):
		self._children[pos].insert(obj)

	def _delete(self, pos):
		self._del[pos] = True

	@property
	def _deletions(self):
		return node.enumerate_deletions(self._del)

	def __len__(self):
		return self._length

	def __getitem__(self, i):
		return self._value[i]

########NEW FILE########
__FILENAME__ = trinary
import node

class TrinaryNode(node.Node):
	def __init__(self, value):
		node.Node.__init__(self)
		if value in (True, False, None):
			self._value = value
		else:
			raise ValueError("A TrinaryNode can only represent True, False, or None")

	# Node interface

	@property
	def value(self):
		return self._value

	@property
	def key(self):
		if self.value == True:
			return "/true"
		elif self.value == False:
			return "/false"
		else:
			return "/null"

	def flatten(self):
		return self.value

	def get(self, pos, key):
		raise node.Ungetable("TrinaryNodes can contain no children")

	def put(self, pos, obj):
		raise node.Unputable("TrinaryNodes can contain no children")

	def delete(self):
		raise node.Undelable("TrinaryNodes can contain no children")

	@property
	def deletions(self):
		return []

	@property
	def children(self):
		return {}

########NEW FILE########
__FILENAME__ = operation
import ejtp.util.hasher as hasher

from ConcurrenTree import ModelBase, node
from address import Address
import instruction

from copy import deepcopy
import traceback
import json

class Operation(ModelBase):
	''' A collection of instructions '''

	def __init__(self, instructions = [], protostring = None): 
		# If protostring is present, uses that existing serialized instruction set. 
		# If not, use instructions.
		if type(instructions) == Operation:
			self.instructions = list(instructions.instructions)
		else:
			if protostring:
				instructions += json.loads(protostring)
			try:
				self.instructions = instruction.set(instructions)
			except:
				raise ParseError()

	def apply(self, tree):
		if not isinstance(tree, node.Node):
			return tree.apply(self)

		backup = deepcopy(tree)
		try:
			for i in self.instructions:
				i.apply(tree)
		except Exception as e:
			tree = backup
			traceback.print_exc()
			raise OpApplyError()

	def prefix(self, addr):
		''' Prepend all instruction addresses with addr '''
		for i in self.instructions:
			i.address = addr + i.address

	@property
	def inserts(self):
		results = []
		for i in self.instructions:
			if i.isinsert:
				results.append(i)
		return results

	@property
	def dep_provides(self):
		''' The dependencies that this operation provides to the tree '''
		return set([str(i.address.proto()+[i.position, i.value]) for i in self.inserts])

	@property
	def dep_requires(self):
		''' The dependencies that this operation requires before it can be applied '''
		return set([str(i.address) for i in self.instructions]) - self.dep_provides

	def ready(self, tree):
		''' Checks a tree for existence of all dependencies '''
		for i in self.dep_requires:
			try:
				Address(i).resolve(tree)
			except Exception as e:
				traceback.print_exc()
				return False
		return True

	def sanitycheck(self, tree):
		if not self.ready(tree): return False

	def applied(self, tree):
		''' Returns whether or not this op has been applied to the tree '''
		if hasattr(tree, "applied"):
			return self.hash in tree.applied
		else:
			return False

	def compress(self):
		# Todo - op compression (combining deletion instructions together)
		pass

	def proto(self):
		''' Returns a protocol operation object '''
		return {"type":"op","instructions":[i.proto() for i in self.instructions]}

	# Plumbing

	def __len__(self):
		return len(self.instructions)

	def __add__(self, other):
		new = Operation(self)
		new += other
		return new

	def __radd__(self, other):
		# Instruction
		if isinstance(other, instruction.Instruction):
			self.instructions = [other] + self.instructions

		# Address
		elif isinstance(other, Address):
			self.prefix(other)		

		else:
			raise ValueError("Unknown type being added to operation")
		return self

	def __iadd__(self, other):
		# Operation
		if isinstance(other, Operation):
			self.instructions += other.instructions

		# Instruction
		elif isinstance(other, instruction.Instruction):
			self.instructions.append(other)

		# Address
		elif isinstance(other, Address):
			self.prefix(other)

		else:
			raise ValueError("Unknown type being added to operation")
		return self

def FromChildren(n):
	''' Creates an op for the descendants of n with the assumption that n is root '''
	op = Operation()

	children = n.children
	if children != None:
		for i in children:
			child = children[i]
			for k in child:
				op += FromNode(n.get(i,k), i)
	return op

def FromNode(n, pos):
	''' Converts node n into an op that inserts it and its descendants to root '''

	op = Operation([instruction.InsertNode([], pos, n)])
	addr = Address([pos, n.key])

	deletions = n.deletions
	if deletions != []:
		op += instruction.Delete(addr, *deletions)

	op += FromChildren(n) + addr

	return op

def FromStructure(root, address=[]):
	''' Returns an op that inserts the node at address (and its descendants) to root '''
	address = Address(address)

	if len(address) > 0:
		pos = address.position(root)
		return FromNode(address.resolve(root), pos) + address.parent
	else:
		return FromChildren(root)

class ParseError(SyntaxError): pass
class OpApplyError(SyntaxError): pass

########NEW FILE########
__FILENAME__ = user
import json
from document import Document
from dbcps.storage import Storage

class UserStorage(object):
    '''
    Wraps dbcps storage and centralizes event callbacks.
    '''
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.cache = {}
        self.event_listeners = set()
        self.storage = Storage([self.backend_data()])

    def backend_data(self):
        '''
        The data tuple for the dbcps backend.

        >>> UserStorage('abc', 'def').storage.get_dbh().handle
        'abc'
        '''
        return ('ramdict', ['rotate', 51], self.username)

	# Events

    def listen(self, handler):
        # handler(typestr, docname, data)
        self.event_listeners.add(handler)

    def unlisten(self, handler):
        self.event_listeners.remove(handler)

    def event(self, typestr, docname, data):
        for ear in self.event_listeners:
            ear(typestr, docname, data)

    def op(self, docname, op):
        doc = self.doc_get(docname)
        if not doc.is_applied(op):
            doc.apply(op)
            self.event("op", docname, op)

    # Document cache manipulation

    def doc_get(self, docname):
        # Retrieve a document from cache, creating from CPS if necessary.
        if docname in self.cache:
            return self.cache[docname]
        doc = Document({})
        if docname in self:
            json_data = json.loads(self[docname])
            doc.load(json_data)
        self.doc_set(docname, doc)
        self.doc_save(docname)
        return doc

    def doc_set(self, docname, value):
        # Set a doc in the cache
        self.cache[docname] = value

    def doc_del(self, docname):
        # Remove a document from the cache.
        del self.cache[docname]

    def doc_reload(self, docname):
        # Convenience function for del & get
        self.doc_del(docname)
        self.doc_get(docname)

    def doc_save(self, docname):
        # Save the current document state to CPS
        doc = self.doc_get(docname)
        self[docname] = doc.serialize()

    # Dict access to strings

    def __getitem__(self, k):
        '''
        >>> s = UserStorage('abc', 'def') 
        >>> s['x']
        Traceback (most recent call last):
        KeyError: 'x'
        >>> s['x'] = 'y'
        >>> s['x']
        'y'
        '''
        return self.storage[k]

    def __setitem__(self, k, i):
        self.storage[k] = i

    def __delitem__(self, k):
        del self.storage[k]

    def __contains__(self, k):
        '''
        >>> s = UserStorage('abc', 'def') 
        >>> 'x' in s
        False
        >>> s['x'] = "Shaboygan"
        >>> 'x' in s
        True
        >>> del s['x']
        >>> 'x' in s
        False
        '''
        return k in self.storage

########NEW FILE########
__FILENAME__ = cmdline
def consider(queue):
	'''
	Takes an iterable, produces a simple approval loop.
	'''
	for request in queue:
		print request
		response = raw_input("Approve, Reject, Defer, or Quit? [a|r|d|q] ")
		if response == 'a':
			request.approve()
		elif response == 'r':
			request.reject()
		elif response == 'q':
			print "Exiting loop..."
			queue.add(request)
			return
		else:
			print "Deferring the choice until later..."
			queue.add(request)

########NEW FILE########
__FILENAME__ = hello
import request

class HelloRequest(request.ValidationRequest):
	'''
	Represents introductory information from a remote source.
	'''
	def __init__(self, author, encryptor, callback):
		self.author = author
		self.encryptor = encryptor
		self.callback = callback

	def desc_string(self):
		return "A remote interface is telling you its encryptor proto."

	def __str__(self):
		return self.desc_string() + " author: %r, encryptor: %r" % (
			self.author,
			self.encryptor,
		)



########NEW FILE########
__FILENAME__ = invitation
import request

class InvitationRequest(request.ValidationRequest):
	'''
	Represents another participant inviting you to
	load a document from them.
	'''
	def __init__(self, author, docname, callback):
		self.author = author
		self.docname = docname
		self.callback = callback

	def desc_string(self):
		return "A user invited you to join a document and load a copy from them."

	def __str__(self):
		'''
		>>> i = mock_invitation()
		>>> str(i)
		"A user invited you to join a document and load a copy from them. author: 'x', docname: 'y'"
		'''
		return self.desc_string() + " author: %r, docname: %r" % (
			self.author,
			self.docname,
		)

def mock_invitation():
	'''
	>>> i = mock_invitation()
	>>> i.approve()
	True
	>>> i.reject()
	False
	'''
	def printer(z):
		print z
	return InvitationRequest("x", "y", printer)

########NEW FILE########
__FILENAME__ = load
import request

class LoadRequest(request.ValidationRequest):
	'''
	Represents a request from a remote interface, for a full copy of a doc.
	'''
	def __init__(self, author, docname, callback):
		self.author = author
		self.docname = docname
		self.callback = callback

	def desc_string(self):
		return "A user requested to load a document from you."

	def __str__(self):
		return self.desc_string() + " author: %r, docname: %r" % (
			self.author,
			self.docname,
		)



########NEW FILE########
__FILENAME__ = operation
import request

class OperationRequest(request.ValidationRequest):
	'''
	Represents an operation from a remote source.
	'''
	def __init__(self, author, docname, op, callback):
		self.author = author
		self.docname = docname
		self.op = op
		self.callback = callback

	def desc_string(self):
		return "A user sent you an operation."

	def __str__(self):
		return self.desc_string() + " author: %r, docname: %r, op: %r" % (
			self.author,
			self.docname,
			self.op,
		)


########NEW FILE########
__FILENAME__ = queue
from Queue import Queue, Empty

class ValidationQueue(object):
	'''
	Class capable of taking an iterable (even a generator) and
	acting as an iterable queue. Iteration will end - not stop -
	if you get to the end of the current contents of the internal
	queue, so expect to for-loop through an instance multiple times.

	>>> my_queue = ValidationQueue(xrange(1,5))
	>>> for i in my_queue:
	...     print i
	...     if i < 5:
	...         my_queue.add(i*2)
	1
	2
	3
	4
	2
	4
	6
	8
	4
	8
	8
	'''

	def __init__(self, source=[], filters=[]):
		# Accepts any iterable as optional argument for initial data.
		self.source = source.__iter__()
		self.queue = Queue()
		self.filters = list(filters)

	def __iter__(self):
		return self.gen()

	def gen(self):
		# Returns the generator used by __iter__().
		while True:
			yield self.pop()

	def pop(self):
		try:
			return self.source.next()
		except StopIteration:
			pass
		try:
			return self.queue.get_nowait()
		except Empty:
			raise StopIteration

	def add(self, obj):
		# Add an object to the internal queue.
		self.queue.put(obj)

	def filter(self, obj):
		'''
		Runs a request through all the filters owned by the queue.
		Each filter is a callback filter(queue, obj)-> None | Request.

		Filters should return the Request if they want to pass it on to
		other filters, and otherwise, call the appropriate methods of
		the Queue and Request, and return None. For example:

		>>> def myFilter(queue, obj):
		...    return obj.approve() # Thus, returning None
		...
		>>> from invitation import mock_invitation
		>>> my_queue = ValidationQueue(filters = [myFilter])
		>>> my_queue.filter(mock_invitation())
		True

		This is the preferred way to handle requests from things like
		the Gear class and such, since it allows flexibility to auto-
		approve requests based on arbitrary criteria and algorithms.
		'''
		for i in self.filters:
			obj = i(self, obj)
			if obj==None:
				break
		if obj!=None:
			self.add(obj)

########NEW FILE########
__FILENAME__ = request

class ValidationRequest(object):
	def callback(self, value):
		# Placeholder function to be overridden
		raise NotImplementedError("ValidationRequest callback was not overridden. Cannot call with value %r" % value)

	def approve(self):
		self.callback(True)

	def reject(self):
		self.callback(False)

	def __str__(self):
		return self.desc_string() + " " + repr(self.properties())

	def desc_string(self):
		return "Generic validation request."

	def properties(self):
		names = [x for x in dir(self) if not x.startswith('_')]
		results = {}
		for name in names:
			results[name] = getattr(self, name)
		return results

########NEW FILE########
__FILENAME__ = list
from wrapper import Wrapper

class ListWrapper(Wrapper):
	def __getitem__(self, i):
		if type(i) == slice:
			return [self[x] for x in range(*i.indices(len(self)))]
		from ConcurrenTree.wrapper import make
		addr, n = self.context.get(i)
		return make(n, self.childsink(addr))

	def __setitem__(self, i, x):
		del self[i]
		self.insert(i, x)

	def __delitem__(self, i):
		self.opsink(self.context.delete(i,1))

	def __delslice__(self, i, k):
		l = len(self)
		i %= l
		k %= l
		size = max(k-i,0)
		self.opsink(self.context.delete(i, size))

	def __len__(self):
		return len(self.value)

	def __str__(self):
		return self.value

	def __add__(self, y):
		return self.value+y

	def __iadd__(self, y):
		# self += other
		self.insert(len(self), y)
		return self

	def insert(self, pos, value):
		self.opsink(self.context.insert(pos, value))

	def append(self, value):
		self.insert(len(self), value)

########NEW FILE########
__FILENAME__ = map
from wrapper import Wrapper

class MapWrapper(Wrapper):
	def __getitem__(self, i):
		# Compute address of landing node
		addr, node = self.context.get(i).head()
		node = node.value_node()
		if node == None:
			return None
		addr = [i, '/single'] + addr + [0, node.key]
		return self.childnode(node, addr)

	def __setitem__(self, i, v):
		self.opsink(self.context.set(i, v))

	def __delitem__(self, i):
		'''
		Delete an element of a map.

		>>> from ConcurrenTree import document
		>>> w = document.Document({}).wrapper()
		>>> "sample" in w
		False
		>>> w['sample'] = "value"
		>>> "sample" in w
		True
		>>> w['sample'] = {}
		>>> "sample" in w
		True
		>>> del w['sample']
		>>> w['sample']
		w<None>
		>>> "sample" in w
		False
		'''
		self.opsink(self.context.set(i, None))

	def __contains__(self, i):
		return i in self.node and self[i].value != None

	def __iter__(self):
		return self.node.__iter__()

	def __len__(self):
		return len(self.value)

	def apply(self, op):
		self.node.apply(op)

	def update(self, d):
		for k in d:
			self[k] = d[k]

########NEW FILE########
__FILENAME__ = number
from wrapper import Wrapper

class NumberWrapper(Wrapper):
	def __init__(self, node, opsink, unique=None):
		Wrapper.__init__(self, node, opsink)
		if unique:
			self.unique = unique
		else:
			self.unique = node.unique

	def __iadd__(self, other):
		self.opsink(self.context.delta(other, self.unique))
		return self

	def __isub__(self, other):
		self += -other
		return self

	def __int__(self):
		return int(self.value)

	def __long__(self):
		return long(self.value)

	def __float__(self):
		return float(self.value)

########NEW FILE########
__FILENAME__ = single
from wrapper import Wrapper

class SingleWrapper(Wrapper):
	def get(self):
		from ConcurrenTree.wrapper import make
		addr, n = self.context.get()
		if addr == None:
			return None
		return make(n, self.childsink(addr))

	def set(self, value):
		self.opsink(self.context.set(value))

	def __repr__(self):
		return "ws<%r>" % self.value

########NEW FILE########
__FILENAME__ = string
from wrapper import Wrapper

class StringWrapper(Wrapper):
	def __getitem__(self, i):
		return self.value[i]

	def __setitem__(self, i, x):
		del self[i]
		self.insert(i, x)

	def __delitem__(self, i):
		self.opsink(self.context.delete(i,1))

	def __getslice__(self, i, k):
		return self.value[i:k]

	def __delslice__(self, i, k):
		l = len(self)
		i %= l
		k %= l
		size = max(k-i,0)
		self.opsink(self.context.delete(i, size))

	def __len__(self):
		return len(self.value)

	def __str__(self):
		return self.value

	def __add__(self, y):
		return self.value+y

	def __iadd__(self, y):
		# self += other
		self.insert(len(self), y)

	def insert(self, pos, value):
		self.opsink(self.context.insert(pos, value))

########NEW FILE########
__FILENAME__ = trinary
from wrapper import Wrapper

class TrinaryWrapper(Wrapper):
	# Minimalist class for the interface
	pass

########NEW FILE########
__FILENAME__ = wrapper
from ConcurrenTree.address import Address
from ejtp.util.hasher import strict
import json

class Wrapper(object):
	# Lets you treat nodes directly like the objects they
	# represent, with implementation details abstracted
	# away (other than initialization).
	def __init__(self, node, opsink):
		# Takes a node object, and a callback.
		# The callback should accept an op.
		self.node = node
		self.opsink = opsink
		self.context = self.node.context()

	def childsink(self, address):
		# A simple mechanism to ripple ops to the top level.
		# You should use this as the default opsink when creating child wrappers.
		address = Address(address)
		def sink(op):
			self.opsink(address+op)
		return sink

	def childnode(self, node, address):
		# Create a child wrapper based on a childsink
		from ConcurrenTree.wrapper import make
		return make(node, self.childsink(address))

	def pretty(self):
		return json.dumps(self.value, indent=4)

	@property
	def value(self):
		return self.context.value

	@property
	def strict(self):
		# The strict string rep of self.value
		return strict(self.value)

	def __repr__(self):
		return "w<%r>" % self.value

########NEW FILE########
__FILENAME__ = rsatest
#!/usr/bin/python

from ejtp.util.crypto import make
from ejtp.util import hasher

# Create random keys
key1 = make(['rsa', None])
key2 = make(['rsa', None])

# Configure
TEST_COUNT = 103

def message(i):
	result = hasher.make(str(i))
	return result, result*10

# Wrapper functions
def encode(msg, sender, reciever):
	return reciever.encrypt(sender.decrypt(msg))

def decode(msg, sender, reciever):
	return encode(msg, reciever, sender)

def test_run(sender, reciever):
	for i in range(0, TEST_COUNT):
		desc, plaintext = message(i)
		ciphertext = encode(plaintext, key1, key2)
		if plaintext != decode(ciphertext, key1, key2):
			print "%r\n" % desc

# Actual test:
print "key1 >> key2"
test_run(key1, key2)
print "key2 >> key1"
test_run(key2, key1)

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

import doctest
import ConcurrenTree

def test_recursive(mod, debug=False):
	(failure_count, test_count) = doctest.testmod(mod)
	if "__all__" in dir(mod):
		for child in mod.__all__:
			fullchildname = mod.__name__+"."+child
			if debug:
				print "Testing", fullchildname
			childmod = __import__(fullchildname, fromlist=[""])
			cf, ct = test_recursive(childmod, debug)
			failure_count += cf
			test_count    += ct
	return (failure_count, test_count)

def test_ctree(debug = False):
	failures, tests = test_recursive(ConcurrenTree, debug)
	print "%d failures, %d tests." % (failures, tests)

if __name__ == "__main__":
	import sys
	debug = "-l" in sys.argv
	test_ctree(debug)

########NEW FILE########
