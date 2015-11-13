__FILENAME__ = comment
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Comment important tags (with 'id' and 'class' attributes)
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
from zencoding import zen_core as zen_coding

alias = 'c'
"Filter name alias (if not defined, ZC will use module name)"

def add_comments(node, i):
	
	"""
	Add comments to tag
	@type node: ZenNode
	@type i: int
	"""
	id_attr = node.get_attribute('id')
	class_attr = node.get_attribute('class')
	nl = zen_coding.get_newline()
		
	if id_attr or class_attr:
		comment_str = ''
		padding = node.parent and node.parent.padding or ''
		if id_attr: comment_str += '#' + id_attr
		if class_attr: comment_str += '.' + class_attr
		
		node.start = node.start.replace('<', '<!-- ' + comment_str + ' -->' + nl + padding + '<', 1)
		node.end = node.end.replace('>', '>' + nl + padding + '<!-- /' + comment_str + ' -->', 1)
		
		# replace counters
		node.start = zen_coding.replace_counter(node.start, i + 1)
		node.end = zen_coding.replace_counter(node.end, i + 1)

def process(tree, profile):
	if profile['tag_nl'] is False:
		return tree
		
	for i, item in enumerate(tree.children):
		if item.is_block():
			add_comments(item, i)
		process(item, profile)
	
	return tree
########NEW FILE########
__FILENAME__ = escape
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Filter for escaping unsafe XML characters: <, >, &
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
import re

alias = 'e'
"Filter name alias (if not defined, ZC will use module name)"

char_map = {
	'<': '&lt;',
	'>': '&gt;',
	'&': '&amp;'
}

re_chars = re.compile(r'[<>&]')

def escape_chars(text):
	return re_chars.sub(lambda m: char_map[m.group(0)], text)

def process(tree, profile=None):
	for item in tree.children:
		item.start = escape_chars(item.start)
		item.end = escape_chars(item.end)
		
		process(item)
	
	return tree
########NEW FILE########
__FILENAME__ = format-css
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Format CSS properties: add space after property name:
padding:0; -> padding: 0;
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
import re

alias = 'fc'
"Filter name alias (if not defined, ZC will use module name)"

re_css_prop = re.compile(r'([\w\-]+\s*:)\s*')

def process(tree, profile):
	for item in tree.children:
		# CSS properties are always snippets 
		if item.type == 'snippet':
			item.start = re_css_prop.sub(r'\1 ', item.start)
		
		process(item, profile)
		
	return tree
########NEW FILE########
__FILENAME__ = format
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Generic formatting filter: creates proper indentation for each tree node,
placing "%s" placeholder where the actual output should be. You can use
this filter to preformat tree and then replace %s placeholder to whatever you
need. This filter should't be called directly from editor as a part 
of abbreviation.
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
"""
import re
from zencoding import zen_core as zen_coding

alias = '_format'
"Filter name alias (if not defined, ZC will use module name)"

child_token = '${child}'
placeholder = '%s'

def get_newline():
	return zen_coding.get_newline()


def get_indentation():
	return zen_coding.get_indentation()

def has_block_sibling(item):
	"""
	Test if passed node has block-level sibling element
	@type item: ZenNode
	@return: bool
	"""
	return item.parent and item.parent.has_block_children()

def is_very_first_child(item):
	"""
	Test if passed itrem is very first child of the whole tree
	@type tree: ZenNode
	"""
	return item.parent and not item.parent.parent and not item.previous_sibling

def should_break_line(node, profile):
	"""
	Need to add line break before element
	@type node: ZenNode
	@type profile: dict
	@return: bool
	"""
	if not profile['inline_break']:
		return False
		
	# find toppest non-inline sibling
	while node.previous_sibling and node.previous_sibling.is_inline():
		node = node.previous_sibling
	
	if not node.is_inline():
		return False
		
	# calculate how many inline siblings we have
	node_count = 1
	node = node.next_sibling
	while node:
		if node.is_inline():
			node_count += 1
		else:
			break
		node = node.next_sibling
	
	return node_count >= profile['inline_break']

def should_break_child(node, profile):
	"""
	 Need to add newline because <code>item</code> has too many inline children
	 @type node: ZenNode
	 @type profile: dict
	 @return: bool
	"""
	# we need to test only one child element, because 
	# has_block_children() method will do the rest
	return node.children and should_break_line(node.children[0], profile)

def process_snippet(item, profile, level=0):
	"""
	Processes element with <code>snippet</code> type
	@type item: ZenNode
	@type profile: dict
	@param level: Depth level
	@type level: int
	"""
	data = item.source.value;
		
	if not data:
		# snippet wasn't found, process it as tag
		return process_tag(item, profile, level)
		
	item.start = placeholder
	item.end = placeholder
	
	padding = item.parent.padding if item.parent else get_indentation() * level 
	
	if not is_very_first_child(item):
		item.start = get_newline() + padding + item.start
	
	# adjust item formatting according to last line of <code>start</code> property
	parts = data.split(child_token)
	lines = zen_coding.split_by_lines(parts[0] or '')
	padding_delta = get_indentation()
		
	if len(lines) > 1:
		m = re.match(r'^(\s+)', lines[-1])
		if m:
			padding_delta = m.group(1)
	
	item.padding = padding + padding_delta
	
	return item

def process_tag(item, profile, level=0):
	"""
	Processes element with <code>tag</code> type
	@type item: ZenNode
	@type profile: dict
	@param level: Depth level
	@type level: int
	"""
	if not item.name:
		# looks like it's a root element
		return item
	
	item.start = placeholder
	item.end = placeholder
	
	is_unary = item.is_unary() and not item.children
		
	# formatting output
	if profile['tag_nl'] is not False:
		padding = item.parent.padding if item.parent else get_indentation() * level
		force_nl = profile['tag_nl'] is True
		should_break = should_break_line(item, profile)
		
		# formatting block-level elements
		if ((item.is_block() or should_break) and item.parent) or force_nl:
			# snippet children should take different formatting
			if not item.parent or (item.parent.type != 'snippet' and not is_very_first_child(item)):
				item.start = get_newline() + padding + item.start
				
			if item.has_block_children() or should_break_child(item, profile) or (force_nl and not is_unary):
				item.end = get_newline() + padding + item.end
				
			if item.has_tags_in_content() or (force_nl and not item.has_children() and not is_unary):
				item.start += get_newline() + padding + get_indentation()
			
		elif item.is_inline() and has_block_sibling(item) and not is_very_first_child(item):
			item.start = get_newline() + padding + item.start
		
		item.padding = padding + get_indentation()
	
	return item

def process(tree, profile, level=0):
	"""
	Processes simplified tree, making it suitable for output as HTML structure
	@type item: ZenNode
	@type profile: dict
	@param level: Depth level
	@type level: int
	"""
	
	for item in tree.children:
		if item.type == 'tag':
			item = process_tag(item, profile, level)
		else:
			item = process_snippet(item, profile, level)
		
		if item.content:
			item.content = zen_coding.pad_string(item.content, item.padding)
			
		process(item, profile, level + 1)
	
	return tree
########NEW FILE########
__FILENAME__ = haml
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Filter that produces HAML tree
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
from zencoding import zen_core as zen_coding

child_token = '${child}'
	
def make_attributes_string(tag, profile):
	"""
	 Creates HTML attributes string from tag according to profile settings
	 @type tag: ZenNode
	 @type profile: dict
	"""
	# make attribute string
	attrs = ''
	attr_quote = profile['attr_quotes'] == 'single' and "'" or '"'
	cursor = profile['place_cursor'] and zen_coding.get_caret_placeholder() or ''
		
	# use short notation for ID and CLASS attributes
	for a in tag.attributes:
		name_lower = a['name'].lower()
		if name_lower == 'id':
			attrs += '#' + (a['value'] or cursor)
		elif name_lower == 'class':
			attrs += '.' + (a['value'] or cursor)
			
	other_attrs = []
	
	# process other attributes
	for a in tag.attributes:
		name_lower = a['name'].lower()
		if name_lower != 'id' and name_lower != 'class':
			attr_name = profile['attr_case'] == 'upper' and a['name'].upper() or name_lower
			other_attrs.append(':' + attr_name + ' => ' + attr_quote + (a['value'] or cursor) + attr_quote)
		
	if other_attrs:
		attrs += '{' + ', '.join(other_attrs) + '}'
	
	return attrs

def _replace(placeholder, value):
	if placeholder:
		return placeholder % value
	else:
		return value		

def process_snippet(item, profile, level=0):
	"""
	Processes element with <code>snippet</code> type
	@type item: ZenNode
	@type profile: dict
	@type level: int
	"""
	data = item.source.value
		
	if not data:
		# snippet wasn't found, process it as tag
		return process_tag(item, profile, level)
		
	tokens = data.split(child_token)
	if len(tokens) < 2:
		start = tokens[0]
		end = ''
	else:
		start, end = tokens
	
	padding = item.parent and item.parent.padding or ''
		
	item.start = _replace(item.start, zen_coding.pad_string(start, padding))
	item.end = _replace(item.end, zen_coding.pad_string(end, padding))
	
	return item

def has_block_sibling(item):
	"""
	Test if passed node has block-level sibling element
	@type item: ZenNode
	@return: bool
	"""
	return item.parent and item.parent.has_block_children()

def process_tag(item, profile, level=0):
	"""
	Processes element with <code>tag</code> type
	@type item: ZenNode
	@type profile: dict
	@type level: int
	"""
	if not item.name:
		# looks like it's root element
		return item
	
	attrs = make_attributes_string(item, profile) 
	cursor = profile['place_cursor'] and zen_coding.get_caret_placeholder() or ''
	self_closing = ''
	is_unary = item.is_unary() and not item.children
	
	if profile['self_closing_tag'] and is_unary:
		self_closing = '/'
		
	# define tag name
	tag_name = '%' + (profile['tag_case'] == 'upper' and item.name.upper() or item.name.lower())
					
	if tag_name.lower() == '%div' and '{' not in attrs:
		# omit div tag
		tag_name = ''
		
	item.end = ''
	item.start = _replace(item.start, tag_name + attrs + self_closing)
	
	if not item.children and not is_unary:
		item.start += cursor
	
	return item

def process(tree, profile, level=0):
	"""
	Processes simplified tree, making it suitable for output as HTML structure
	@type tree: ZenNode
	@type profile: dict
	@type level: int
	"""
	if level == 0:
		# preformat tree
		tree = zen_coding.run_filters(tree, profile, '_format')
		
	for i, item in enumerate(tree.children):
		if item.type == 'tag':
			process_tag(item, profile, level)
		else:
			process_snippet(item, profile, level)
	
		# replace counters
		item.start = zen_coding.unescape_text(zen_coding.replace_counter(item.start, item.counter))
		item.end = zen_coding.unescape_text(zen_coding.replace_counter(item.end, item.counter))
		process(item, profile, level + 1)
		
	return tree

########NEW FILE########
__FILENAME__ = html
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Filter that produces HTML tree
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
from zencoding import zen_core as zen_coding

child_token = '${child}'

def make_attributes_string(tag, profile):
	"""
	Creates HTML attributes string from tag according to profile settings
	@type tag: ZenNode
	@type profile: dict
	"""
	# make attribute string
	attrs = ''
	attr_quote = profile['attr_quotes'] == 'single' and "'" or '"'
	cursor = profile['place_cursor'] and zen_coding.get_caret_placeholder() or ''
	
	# process other attributes
	for a in tag.attributes:
		attr_name = profile['attr_case'] == 'upper' and a['name'].upper() or a['name'].lower()
		attrs += ' ' + attr_name + '=' + attr_quote + (a['value'] or cursor) + attr_quote
		
	return attrs

def _replace(placeholder, value):
	if placeholder:
		return placeholder % value
	else:
		return value

def process_snippet(item, profile, level):
	"""
	Processes element with <code>snippet</code> type
	@type item: ZenNode
	@type profile: dict
	@type level: int
	"""
	data = item.source.value;
		
	if not data:
		# snippet wasn't found, process it as tag
		return process_tag(item, profile, level)
		
	tokens = data.split(child_token)
	if len(tokens) < 2:
		start = tokens[0]
		end = ''
	else:
		start, end = tokens
		
	padding = item.parent and item.parent.padding or ''
		
	item.start = _replace(item.start, zen_coding.pad_string(start, padding))
	item.end = _replace(item.end, zen_coding.pad_string(end, padding))
	
	return item


def has_block_sibling(item):
	"""
	Test if passed node has block-level sibling element
	@type item: ZenNode
	@return: bool
	"""
	return item.parent and item.parent.has_block_children()

def process_tag(item, profile, level):
	"""
	Processes element with <code>tag</code> type
	@type item: ZenNode
	@type profile: dict
	@type level: int
	"""
	if not item.name:
		# looks like it's root element
		return item
	
	attrs = make_attributes_string(item, profile) 
	cursor = profile['place_cursor'] and zen_coding.get_caret_placeholder() or ''
	self_closing = ''
	is_unary = item.is_unary() and not item.children
	start= ''
	end = ''
	
	if profile['self_closing_tag'] == 'xhtml':
		self_closing = ' /'
	elif profile['self_closing_tag'] is True:
		self_closing = '/'
		
	# define opening and closing tags
	tag_name = profile['tag_case'] == 'upper' and item.name.upper() or item.name.lower()
	if is_unary:
		start = '<' + tag_name + attrs + self_closing + '>'
		item.end = ''
	else:
		start = '<' + tag_name + attrs + '>'
		end = '</' + tag_name + '>'
	
	item.start = _replace(item.start, start)
	item.end = _replace(item.end, end)
	
	if not item.children and not is_unary:
		item.start += cursor
	
	return item

def process(tree, profile, level=0):
	"""
	Processes simplified tree, making it suitable for output as HTML structure
	@type tree: ZenNode
	@type profile: dict
	@type level: int
	"""
	if level == 0:
		# preformat tree
		tree = zen_coding.run_filters(tree, profile, '_format')
		zen_coding.max_tabstop = 0
		
	for item in tree.children:
		if item.type == 'tag':
			process_tag(item, profile, level)
		else:
			process_snippet(item, profile, level)
	
		# replace counters
		item.start = zen_coding.unescape_text(zen_coding.replace_counter(item.start, item.counter))
		item.end = zen_coding.unescape_text(zen_coding.replace_counter(item.end, item.counter))
		zen_coding.upgrade_tabstops(item)
		
		process(item, profile, level + 1)
		
	return tree

########NEW FILE########
__FILENAME__ = xsl
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Filter for trimming "select" attributes from some tags that contains
child elements
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
'''
import re

tags = {
	'xsl:variable': 1,
	'xsl:with-param': 1
}

re_attr = re.compile(r'\s+select\s*=\s*([\'"]).*?\1')

def trim_attribute(node):
	"""
	Removes "select" attribute from node
	@type node: ZenNode
	"""
	node.start = re_attr.sub('', node.start)

def process(tree, profile):
	for item in tree.children:
		if item.type == 'tag' and item.name.lower() in tags and item.children:
			trim_attribute(item)
		
		process(item, profile)
########NEW FILE########
__FILENAME__ = html_matcher
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Context-independent xHTML pair matcher
Use method <code>match(html, start_ix)</code> to find matching pair.
If pair was found, this function returns a list of indexes where tag pair 
starts and ends. If pair wasn't found, <code>None</code> will be returned.

The last matched (or unmatched) result is saved in <code>last_match</code> 
dictionary for later use.

@author: Sergey Chikuyonok (serge.che@gmail.com)
'''
import re

start_tag = r'<([\w\:\-]+)((?:\s+[\w\-:]+(?:\s*=\s*(?:(?:"[^"]*")|(?:\'[^\']*\')|[^>\s]+))?)*)\s*(\/?)>'
end_tag = r'<\/([\w\:\-]+)[^>]*>'
attr = r'([\w\-:]+)(?:\s*=\s*(?:(?:"((?:\\.|[^"])*)")|(?:\'((?:\\.|[^\'])*)\')|([^>\s]+)))?'

"Last matched HTML pair"
last_match = {
	'opening_tag': None, # Tag() or Comment() object
	'closing_tag': None, # Tag() or Comment() object
	'start_ix': -1,
	'end_ix': -1
}

cur_mode = 'xhtml'
"Current matching mode"

def set_mode(new_mode):
	global cur_mode
	if new_mode != 'html': new_mode = 'xhtml'
	cur_mode = new_mode

def make_map(elems):
	"""
	Create dictionary of elements for faster searching
	@param elems: Elements, separated by comma
	@type elems: str
	"""
	obj = {}
	for elem in elems.split(','):
			obj[elem] = True

	return obj

# Empty Elements - HTML 4.01
empty = make_map("area,base,basefont,br,col,frame,hr,img,input,isindex,link,meta,param,embed");

# Block Elements - HTML 4.01
block = make_map("address,applet,blockquote,button,center,dd,dir,div,dl,dt,fieldset,form,frameset,hr,iframe,isindex,li,map,menu,noframes,noscript,object,ol,p,pre,script,table,tbody,td,tfoot,th,thead,tr,ul");

# Inline Elements - HTML 4.01
inline = make_map("a,abbr,acronym,applet,b,basefont,bdo,big,br,button,cite,code,del,dfn,em,font,i,iframe,img,input,ins,kbd,label,map,object,q,s,samp,select,small,span,strike,strong,sub,sup,textarea,tt,u,var");

# Elements that you can, intentionally, leave open
# (and which close themselves)
close_self = make_map("colgroup,dd,dt,li,options,p,td,tfoot,th,thead,tr");

# Attributes that have their values filled in disabled="disabled"
fill_attrs = make_map("checked,compact,declare,defer,disabled,ismap,multiple,nohref,noresize,noshade,nowrap,readonly,selected");

#Special Elements (can contain anything)
# serge.che: parsing data inside <scipt> elements is a "feature"
special = make_map("style");

class Tag():
	"""Matched tag"""
	def __init__(self, match, ix):
		"""
		@type match: MatchObject
		@param match: Matched HTML tag
		@type ix: int
		@param ix: Tag's position
		"""
		global cur_mode
		
		name = match.group(1).lower()
		self.name = name
		self.full_tag = match.group(0)
		self.start = ix
		self.end = ix + len(self.full_tag)
		self.unary = ( len(match.groups()) > 2 and bool(match.group(3)) ) or (name in empty and cur_mode == 'html')
		self.type = 'tag'
		self.close_self = (name in close_self and cur_mode == 'html')

class Comment():
	"Matched comment"
	def __init__(self, start, end):
		self.start = start
		self.end = end
		self.type = 'comment'

def make_range(opening_tag=None, closing_tag=None, ix=0):
	"""
	Makes selection ranges for matched tag pair
	@type opening_tag: Tag
    @type closing_tag: Tag
    @type ix: int
    @return list
	"""
	start_ix, end_ix = -1, -1
	
	if opening_tag and not closing_tag: # unary element
		start_ix = opening_tag.start
		end_ix = opening_tag.end
	elif opening_tag and closing_tag: # complete element
		if (opening_tag.start < ix and opening_tag.end > ix) or (closing_tag.start <= ix and closing_tag.end > ix):
			start_ix = opening_tag.start
			end_ix = closing_tag.end;
		else:
			start_ix = opening_tag.end
			end_ix = closing_tag.start
	
	return start_ix, end_ix

def save_match(opening_tag=None, closing_tag=None, ix=0):
	"""
	Save matched tag for later use and return found indexes
    @type opening_tag: Tag
    @type closing_tag: Tag
    @type ix: int
    @return list
	"""
	last_match['opening_tag'] = opening_tag; 
	last_match['closing_tag'] = closing_tag;
	
	last_match['start_ix'], last_match['end_ix'] = make_range(opening_tag, closing_tag, ix)
	
	return last_match['start_ix'] != -1 and (last_match['start_ix'], last_match['end_ix']) or (None, None)

def match(html, start_ix, mode='xhtml'):
	"""
	Search for matching tags in <code>html</code>, starting from
	<code>start_ix</code> position. The result is automatically saved
	in <code>last_match</code> property
	"""
	return _find_pair(html, start_ix, mode, save_match)

def find(html, start_ix, mode='xhtml'):
	"""
	Search for matching tags in <code>html</code>, starting from
	<code>start_ix</code> position.
	"""
	return _find_pair(html, start_ix, mode)

def get_tags(html, start_ix, mode='xhtml'):
	"""
	Search for matching tags in <code>html</code>, starting from 
	<code>start_ix</code> position. The difference between 
	<code>match</code> function itself is that <code>get_tags</code> 
	method doesn't save matched result in <code>last_match</code> property 
	and returns array of opening and closing tags
	This method is generally used for lookups
	"""
	return _find_pair(html, start_ix, mode, lambda op, cl=None, ix=0: (op, cl) if op and op.type == 'tag' else None)


def _find_pair(html, start_ix, mode='xhtml', action=make_range):
	"""
	Search for matching tags in <code>html</code>, starting from
	<code>start_ix</code> position
	
	@param html: Code to search
	@type html: str
	
	@param start_ix: Character index where to start searching pair
	(commonly, current caret position)
	@type start_ix: int
	
	@param action: Function that creates selection range
	@type action: function
	
	@return: list
	"""

	forward_stack = []
	backward_stack = []
	opening_tag = None
	closing_tag = None
	html_len = len(html)
	
	set_mode(mode)

	def has_match(substr, start=None):
		if start is None:
			start = ix

		return html.find(substr, start) == start


	def find_comment_start(start_pos):
		while start_pos:
			if html[start_pos] == '<' and has_match('<!--', start_pos):
				break

			start_pos -= 1

		return start_pos

#    find opening tag
	ix = start_ix - 1
	while ix >= 0:
		ch = html[ix]
		if ch == '<':
			check_str = html[ix:]
			m = re.match(end_tag, check_str)
			if m:  # found closing tag
				tmp_tag = Tag(m, ix)
				if tmp_tag.start < start_ix and tmp_tag.end > start_ix: # direct hit on searched closing tag
					closing_tag = tmp_tag
				else:
					backward_stack.append(tmp_tag)
			else:
				m = re.match(start_tag, check_str)
				if m: # found opening tag
					tmp_tag = Tag(m, ix);
					if tmp_tag.unary:
						if tmp_tag.start < start_ix and tmp_tag.end > start_ix: # exact match
							return action(tmp_tag, None, start_ix)
					elif backward_stack and backward_stack[-1].name == tmp_tag.name:
						backward_stack.pop()
					else: # found nearest unclosed tag
						opening_tag = tmp_tag
						break
				elif check_str.startswith('<!--'): # found comment start
					end_ix = check_str.find('-->') + ix + 3;
					if ix < start_ix and end_ix >= start_ix:
						return action(Comment(ix, end_ix))
		elif ch == '-' and has_match('-->'): # found comment end
			# search left until comment start is reached
			ix = find_comment_start(ix)

		ix -= 1
		
	if not opening_tag:
		return action(None)
	
	# find closing tag
	if not closing_tag:
		ix = start_ix
		while ix < html_len:
			ch = html[ix]
			if ch == '<':
				check_str = html[ix:]
				m = re.match(start_tag, check_str)
				if m: # found opening tag
					tmp_tag = Tag(m, ix);
					if not tmp_tag.unary:
						forward_stack.append(tmp_tag)
				else:
					m = re.match(end_tag, check_str)
					if m:   #found closing tag
						tmp_tag = Tag(m, ix);
						if forward_stack and forward_stack[-1].name == tmp_tag.name:
							forward_stack.pop()
						else:  # found matched closing tag
							closing_tag = tmp_tag;
							break
					elif has_match('<!--'): # found comment
						ix += check_str.find('-->') + 3
						continue
			elif ch == '-' and has_match('-->'):
				# looks like cursor was inside comment with invalid HTML
				if not forward_stack or forward_stack[-1].type != 'comment':
					end_ix = ix + 3
					return action(Comment( find_comment_start(ix), end_ix ))
				
			ix += 1
	
	return action(opening_tag, closing_tag, start_ix)

########NEW FILE########
__FILENAME__ = plugin
# @file plugin.py
#
# Connect Zen Coding to Gedit.
#
# Author Franck Marcia (franck.marcia@gmail.com)
#

import gedit, gobject, gtk, os

from zen_editor import ZenEditor

zencoding_ui_str = """
<ui>
  <menubar name="MenuBar">
    <menu name="EditMenu" action="Edit">
      <placeholder name="EditOps_5">
        <menu action="ZenCodingMenuAction">
          <menuitem name="ZenCodingExpand"   action="ZenCodingExpandAction"/>
          <menuitem name="ZenCodingExpandW"  action="ZenCodingExpandWAction"/>
          <menuitem name="ZenCodingWrap"     action="ZenCodingWrapAction"/>
          <separator/>
          <menuitem name="ZenCodingInward"   action="ZenCodingInwardAction"/>
          <menuitem name="ZenCodingOutward"  action="ZenCodingOutwardAction"/>
          <menuitem name="ZenCodingMerge"    action="ZenCodingMergeAction"/>
          <separator/>
          <menuitem name="ZenCodingPrev"     action="ZenCodingPrevAction"/>
          <menuitem name="ZenCodingNext"     action="ZenCodingNextAction"/>
          <separator/>
          <menuitem name="ZenCodingRemove"   action="ZenCodingRemoveAction"/>
          <menuitem name="ZenCodingSplit"    action="ZenCodingSplitAction"/>
          <menuitem name="ZenCodingComment"  action="ZenCodingCommentAction"/>
        </menu>
      </placeholder>
    </menu>
  </menubar>
</ui>
"""

class ZenCodingPlugin(gedit.Plugin):
    """A Gedit plugin to implement Zen Coding's HTML and CSS shorthand expander."""

    def activate(self, window):
        actions = [
          ('ZenCodingMenuAction',     None, '_Zen Coding',                  None,            "Zen Coding tools",                            None),
          ('ZenCodingExpandAction',   None, '_Expand abbreviation',         '<Ctrl>E',        "Expand abbreviation to raw HTML/CSS",         self.expand_abbreviation),
          ('ZenCodingExpandWAction',  None, 'E_xpand dynamic abbreviation...', '<Ctrl><Alt>E',   "Dynamically expand abbreviation as you type",           self.expand_with_abbreviation),
          ('ZenCodingWrapAction',     None, '_Wrap with abbreviation...',   '<Ctrl><Shift>E', "Wrap with code expanded from abbreviation",   self.wrap_with_abbreviation),
          ('ZenCodingInwardAction',   None, 'Balance tag _inward',          '<Ctrl><Alt>I',   "Select inner tag's content",                  self.match_pair_inward),
          ('ZenCodingOutwardAction',  None, 'Balance tag _outward',         '<Ctrl><Alt>O',   "Select outer tag's content",                  self.match_pair_outward),
          ('ZenCodingMergeAction',    None, '_Merge lines',                 '<Ctrl><Alt>M',   "Merge all lines of the current selection",    self.merge_lines),
          ('ZenCodingPrevAction',     None, '_Previous edit point',         '<Alt>Left',      "Place the cursor at the previous edit point", self.prev_edit_point),
          ('ZenCodingNextAction',     None, '_Next edit point',             '<Alt>Right',     "Place the cursor at the next edit point",     self.next_edit_point),
          ('ZenCodingRemoveAction',   None, '_Remove tag',                  '<Ctrl><Alt>R',   "Remove a tag",                                self.remove_tag),
          ('ZenCodingSplitAction',    None, 'Split or _join tag',           '<Ctrl><Alt>J',   "Toggle between single and double tag",        self.split_join_tag),
          ('ZenCodingCommentAction',  None, 'Toggle _comment',              '<Ctrl><Alt>C',   "Toggle an XML or HTML comment",               self.toggle_comment)
        ]
        windowdata = dict()
        window.set_data("ZenCodingPluginDataKey", windowdata)
        windowdata["action_group"] = gtk.ActionGroup("GeditZenCodingPluginActions")
        windowdata["action_group"].add_actions(actions, window)
        manager = window.get_ui_manager()
        manager.insert_action_group(windowdata["action_group"], -1)
        windowdata["ui_id"] = manager.add_ui_from_string(zencoding_ui_str)
        window.set_data("ZenCodingPluginInfo", windowdata)
        self.editor = ZenEditor()
        error = self.editor.get_user_settings_error()
        if error:
            md = gtk.MessageDialog(window, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
                gtk.BUTTONS_CLOSE, "There is an error in user settings:")
            message = "{0} on line {1} at character {2}\n\nUser settings will not be available."
            md.set_title("Zen Coding error")
            md.format_secondary_text(message.format(error['msg'], error['lineno'], error['offset']))
            md.run()
            md.destroy()


    def deactivate(self, window):
        windowdata = window.get_data("ZenCodingPluginDataKey")
        manager = window.get_ui_manager()
        manager.remove_ui(windowdata["ui_id"])
        manager.remove_action_group(windowdata["action_group"])

    def update_ui(self, window):
        view = window.get_active_view()
        windowdata = window.get_data("ZenCodingPluginDataKey")
        windowdata["action_group"].set_sensitive(bool(view and view.get_editable()))

    def expand_abbreviation(self, action, window):
        self.editor.expand_abbreviation(window)
        
    def expand_with_abbreviation(self, action, window):
        self.editor.expand_with_abbreviation(window)

    def wrap_with_abbreviation(self, action, window):
        self.editor.wrap_with_abbreviation(window)

    def match_pair_inward(self, action, window):
        self.editor.match_pair_inward(window)

    def match_pair_outward(self, action, window):
        self.editor.match_pair_outward(window)

    def merge_lines(self, action, window):
        self.editor.merge_lines(window)

    def prev_edit_point(self, action, window):
        self.editor.prev_edit_point(window)

    def next_edit_point(self, action, window):
        self.editor.next_edit_point(window)

    def remove_tag(self, action, window):
        self.editor.remove_tag(window)

    def split_join_tag(self, action, window):
        self.editor.split_join_tag(window)

    def toggle_comment(self, action, window):
        self.editor.toggle_comment(window)

########NEW FILE########
__FILENAME__ = stparser
'''
Zen Coding's settings parser
Created on Jun 14, 2009

@author: Sergey Chikuyonok (http://chikuyonok.ru)
'''
from copy import deepcopy

import re
import types
from zen_settings import zen_settings

_original_settings = deepcopy(zen_settings)

TYPE_ABBREVIATION = 'zen-tag',
TYPE_EXPANDO = 'zen-expando',
TYPE_REFERENCE = 'zen-reference';
""" Reference to another abbreviation or tag """

re_tag = r'^<([\w\-]+(?:\:[\w\-]+)?)((?:\s+[\w\-]+(?:\s*=\s*(?:(?:"[^"]*")|(?:\'[^\']*\')|[^>\s]+))?)*)\s*(\/?)>'
"Regular expression for XML tag matching"
	
re_attrs = r'([\w\-]+)\s*=\s*([\'"])(.*?)\2'
"Regular expression for matching XML attributes"

class Entry:
	"""
	Unified object for parsed data
	"""
	def __init__(self, entry_type, key, value):
		"""
		@type entry_type: str
		@type key: str
		@type value: dict
		"""
		self.type = entry_type
		self.key = key
		self.value = value

def _make_expando(key, value):
	"""
	Make expando from string
	@type key: str
	@type value: str
	@return: Entry
	"""
	return Entry(TYPE_EXPANDO, key, value)

def _make_abbreviation(key, tag_name, attrs, is_empty=False):
	"""
	Make abbreviation from string
	@param key: Abbreviation key
	@type key: str
	@param tag_name: Expanded element's tag name
	@type tag_name: str
	@param attrs: Expanded element's attributes
	@type attrs: str
	@param is_empty: Is expanded element empty or not
	@type is_empty: bool
	@return: dict
	"""
	result = {
		'name': tag_name,
		'is_empty': is_empty
	};
	
	if attrs:
		result['attributes'] = [];
		for m in re.findall(re_attrs, attrs):
			result['attributes'].append({
				'name': m[0],
				'value': m[2]
			})
			
	return Entry(TYPE_ABBREVIATION, key, result)

def _parse_abbreviations(obj):
	"""
	Parses all abbreviations inside dictionary
 	@param obj: dict
	"""
	for key, value in obj.items():
		key = key.strip()
		if key[-1] == '+':
#			this is expando, leave 'value' as is
			obj[key] = _make_expando(key, value)
		else:
			m = re.search(re_tag, value)
			if m:
				obj[key] = _make_abbreviation(key, m.group(1), m.group(2), (m.group(3) == '/'))
			else:
#				assume it's reference to another abbreviation
				obj[key] = Entry(TYPE_REFERENCE, key, value)

def parse(settings):
	"""
	Parse user's settings. This function must be called *before* any activity
	in zen coding (for example, expanding abbreviation)
 	@type settings: dict
	"""
	for p, value in settings.items():
		if p == 'abbreviations':
			_parse_abbreviations(value)
		elif p == 'extends':
			settings[p] = [v.strip() for v in value.split(',')]
		elif type(value) == types.DictType:
			parse(value)


def extend(parent, child):
	"""
	Recursevly extends parent dictionary with children's keys. Used for merging
	default settings with user's
	@type parent: dict
	@type child: dict
	"""
	for p, value in child.items():
		if type(value) == types.DictType:
			if p not in parent:
				parent[p] = {}
			extend(parent[p], value)
		else:
			parent[p] = value
				


def create_maps(obj):
	"""
	Create hash maps on certain string properties of zen settings
	@type obj: dict
	"""
	for p, value in obj.items():
		if p == 'element_types':
			for k, v in value.items():
				if isinstance(v, str):
					value[k] = [el.strip() for el in v.split(',')]
		elif type(value) == types.DictType:
			create_maps(value)


if __name__ == '__main__':
	pass

def get_settings(user_settings=None):
	"""
	Main function that gather all settings and returns parsed dictionary
	@param user_settings: A dictionary of user-defined settings
	"""
	settings = deepcopy(_original_settings)
	create_maps(settings)
	
	if user_settings:
		user_settings = deepcopy(user_settings)
		create_maps(user_settings)
		extend(settings, user_settings)
	
	# now we need to parse final set of settings
	parse(settings)
	
	return settings
	

########NEW FILE########
__FILENAME__ = zen_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Middleware layer that communicates between editor and Zen Coding.
This layer describes all available Zen Coding actions, like 
"Expand Abbreviation".
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
"""
from zencoding import zen_core as zen_coding
from zencoding import html_matcher
import re
from zen_core import char_at

def find_abbreviation(editor):
	"""
	Search for abbreviation in editor from current caret position
	@param editor: Editor instance
	@type editor: ZenEditor
	@return: str
	"""
	start, end = editor.get_selection_range()
	if start != end:
		# abbreviation is selected by user
		return editor.get_content()[start:end]
	
	# search for new abbreviation from current caret position
	cur_line_start, cur_line_end = editor.get_current_line_range()
	return zen_coding.extract_abbreviation(editor.get_content()[cur_line_start:start])

def expand_abbreviation(editor, syntax=None, profile_name=None):
	"""
	Find from current caret position and expand abbreviation in editor
	@param editor: Editor instance
	@type editor: ZenEditor
	@param syntax: Syntax type (html, css, etc.)
	@type syntax: str
	@param profile_name: Output profile name (html, xml, xhtml)
	@type profile_name: str
	@return: True if abbreviation was expanded successfully
	"""
	if syntax is None: syntax = editor.get_syntax()
	if profile_name is None: profile_name = editor.get_profile_name()
	
	range_start, caret_pos = editor.get_selection_range()
	abbr = find_abbreviation(editor)
	content = ''
		
	if abbr:
		content = zen_coding.expand_abbreviation(abbr, syntax, profile_name)
		if content:
			editor.replace_content(content, caret_pos - len(abbr), caret_pos)
			return True
	
	return False

def expand_abbreviation_with_tab(editor, syntax, profile_name='xhtml'):
	"""
	A special version of <code>expandAbbreviation</code> function: if it can't
	find abbreviation, it will place Tab character at caret position
	@param editor: Editor instance
	@type editor: ZenEditor
	@param syntax: Syntax type (html, css, etc.)
	@type syntax: str
	@param profile_name: Output profile name (html, xml, xhtml)
	@type profile_name: str
	"""
	if not expand_abbreviation(editor, syntax, profile_name):
		editor.replace_content(zen_coding.get_variable('indentation'), editor.get_caret_pos())
	
	return True 

def match_pair(editor, direction='out', syntax=None):
	"""
	Find and select HTML tag pair
	@param editor: Editor instance
	@type editor: ZenEditor
	@param direction: Direction of pair matching: 'in' or 'out'. 
	@type direction: str 
	"""
	direction = direction.lower()
	if syntax is None: syntax = editor.get_profile_name()
	
	range_start, range_end = editor.get_selection_range()
	cursor = range_end
	content = editor.get_content()
	rng = None
	
	old_open_tag = html_matcher.last_match['opening_tag']
	old_close_tag = html_matcher.last_match['closing_tag']
	
	if direction == 'in' and old_open_tag and range_start != range_end:
#		user has previously selected tag and wants to move inward
		if not old_close_tag:
#			unary tag was selected, can't move inward
			return False
		elif old_open_tag.start == range_start:
			if content[old_open_tag.end] == '<':
#				test if the first inward tag matches the entire parent tag's content
				_r = html_matcher.find(content, old_open_tag.end + 1, syntax)
				if _r[0] == old_open_tag.end and _r[1] == old_close_tag.start:
					rng = html_matcher.match(content, old_open_tag.end + 1, syntax)
				else:
					rng = (old_open_tag.end, old_close_tag.start)
			else:
				rng = (old_open_tag.end, old_close_tag.start)
		else:
			new_cursor = content[0:old_close_tag.start].find('<', old_open_tag.end)
			search_pos = new_cursor + 1 if new_cursor != -1 else old_open_tag.end
			rng = html_matcher.match(content, search_pos, syntax)
	else:
		rng = html_matcher.match(content, cursor, syntax)
	
	if rng and rng[0] is not None:
		editor.create_selection(rng[0], rng[1])
		return True
	else:
		return False

def match_pair_inward(editor):
	return match_pair(editor, 'in')
	
def match_pair_outward(editor):
	return match_pair(editor, 'out')

def narrow_to_non_space(text, start, end):
	"""
	Narrow down text indexes, adjusting selection to non-space characters
	@type text: str
	@type start: int
	@type end: int
	@return: list
	"""
	# narrow down selection until first non-space character
	while start < end:
		if not text[start].isspace():
			break
			
		start += 1
	
	while end > start:
		end -= 1
		if not text[end].isspace():
			end += 1
			break
		
	return start, end

def wrap_with_abbreviation(editor, abbr, syntax=None, profile_name=None):
	"""
	Wraps content with abbreviation
	@param editor: Editor instance
	@type editor: ZenEditor
	@param syntax: Syntax type (html, css, etc.)
	@type syntax: str
	@param profile_name: Output profile name (html, xml, xhtml)
	@type profile_name: str
	"""
	if not abbr: return None 
	
	if syntax is None: syntax = editor.get_syntax()
	if profile_name is None: profile_name = editor.get_profile_name()
	
	start_offset, end_offset = editor.get_selection_range()
	content = editor.get_content()
	
	if start_offset == end_offset:
		# no selection, find tag pair
		rng = html_matcher.match(content, start_offset, profile_name)
		
		if rng[0] is None: # nothing to wrap
			return None
		else:
			start_offset, end_offset = rng
			
	start_offset, end_offset = narrow_to_non_space(content, start_offset, end_offset)
	line_bounds = get_line_bounds(content, start_offset)
	padding = get_line_padding(content[line_bounds[0]:line_bounds[1]])
	
	new_content = content[start_offset:end_offset]
	result = zen_coding.wrap_with_abbreviation(abbr, unindent_text(new_content, padding), syntax, profile_name)
	
	if result:
		editor.replace_content(result, start_offset, end_offset)
		return True
	
	return False

def unindent(editor, text):
	"""
	Unindent content, thus preparing text for tag wrapping
	@param editor: Editor instance
	@type editor: ZenEditor
	@param text: str
	@return str
	"""
	return unindent_text(text, get_current_line_padding(editor))

def unindent_text(text, pad):
	"""
	Removes padding at the beginning of each text's line
	@type text: str
	@type pad: str
	"""
	lines = zen_coding.split_by_lines(text)
	
	for i,line in enumerate(lines):
		if line.startswith(pad):
			lines[i] = line[len(pad):]
	
	return zen_coding.get_newline().join(lines)

def get_current_line_padding(editor):
	"""
	Returns padding of current editor's line
	@return str
	"""
	return get_line_padding(editor.get_current_line())

def get_line_padding(line):
	"""
	Returns padding of current editor's line
	@return str
	"""
	m = re.match(r'^(\s+)', line)
	return m and m.group(0) or ''

def find_new_edit_point(editor, inc=1, offset=0):
	"""
	Search for new caret insertion point
	@param editor: Editor instance
	@type editor: ZenEditor
	@param inc: Search increment: -1 — search left, 1 — search right
	@param offset: Initial offset relative to current caret position
	@return: -1 if insertion point wasn't found
	"""
	cur_point = editor.get_caret_pos() + offset
	content = editor.get_content()
	max_len = len(content)
	next_point = -1
	re_empty_line = r'^\s+$'
	
	def get_line(ix):
		start = ix
		while start >= 0:
			c = content[start]
			if c == '\n' or c == '\r': break
			start -= 1
		
		return content[start:ix]
		
	while cur_point < max_len and cur_point > 0:
		cur_point += inc
		cur_char = char_at(content, cur_point)
		next_char = char_at(content, cur_point + 1)
		prev_char = char_at(content, cur_point - 1)
		
		if cur_char in '"\'':
			if next_char == cur_char and prev_char == '=':
				# empty attribute
				next_point = cur_point + 1
		elif cur_char == '>' and next_char == '<':
			# between tags
			next_point = cur_point + 1
		elif cur_char == ':' and next_char == ';':
			# empty CSS value
			next_point = cur_point + 1
		elif cur_char == '(' and next_char == ')':
		    # empty CSS parenthesis
		    next_point = cur_point + 1
		elif cur_char in '\r\n':
			# empty line
			if re.search(re_empty_line, get_line(cur_point - 1)):
				next_point = cur_point
		
		if next_point != -1: break
	
	return next_point

def prev_edit_point(editor):
	"""
	Move caret to previous edit point
	@param editor: Editor instance
	@type editor: ZenEditor
	"""
	cur_pos = editor.get_caret_pos()
	new_point = find_new_edit_point(editor, -1)
		
	if new_point == cur_pos:
		# we're still in the same point, try searching from the other place
		new_point = find_new_edit_point(editor, -1, -2)
	
	if new_point != -1:
		editor.set_caret_pos(new_point)
		return True
	
	return False

def next_edit_point(editor):
	"""
	Move caret to next edit point
	@param editor: Editor instance
	@type editor: ZenEditor
	""" 
	new_point = find_new_edit_point(editor, 1)
	if new_point != -1:
		editor.set_caret_pos(new_point)
		return True
	
	return False

def insert_formatted_newline(editor, mode='html'):
	"""
	Inserts newline character with proper indentation
	@param editor: Editor instance
	@type editor: ZenEditor
	@param mode: Syntax mode (only 'html' is implemented)
	@type mode: str
	"""
	caret_pos = editor.get_caret_pos()
	nl = zen_coding.get_newline()
	pad = zen_coding.get_variable('indentation')
		
	if mode == 'html':
		# let's see if we're breaking newly created tag
		pair = html_matcher.get_tags(editor.get_content(), editor.get_caret_pos(), editor.get_profile_name())
		
		if pair[0] and pair[1] and pair[0]['type'] == 'tag' and pair[0]['end'] == caret_pos and pair[1]['start'] == caret_pos:
			editor.replace_content(nl + pad + zen_coding.get_caret_placeholder() + nl, caret_pos)
		else:
			editor.replace_content(nl, caret_pos)
	else:
		editor.replace_content(nl, caret_pos)
		
	return True

def select_line(editor):
	"""
	Select line under cursor
	@param editor: Editor instance
	@type editor: ZenEditor
	"""
	start, end = editor.get_current_line_range();
	editor.create_selection(start, end)
	return True

def go_to_matching_pair(editor):
	"""
	Moves caret to matching opening or closing tag
	@param editor: Editor instance
	@type editor: ZenEditor
	"""
	content = editor.get_content()
	caret_pos = editor.get_caret_pos()
	
	if content[caret_pos] == '<': 
		# looks like caret is outside of tag pair  
		caret_pos += 1
		
	tags = html_matcher.get_tags(content, caret_pos, editor.get_profile_name())
		
	if tags and tags[0]:
		# match found
		open_tag, close_tag = tags
			
		if close_tag: # exclude unary tags
			if open_tag['start'] <= caret_pos and open_tag['end'] >= caret_pos:
				editor.set_caret_pos(close_tag['start'])
			elif close_tag['start'] <= caret_pos and close_tag['end'] >= caret_pos:
				editor.set_caret_pos(open_tag['start'])
				
		return True
	
	return False
				

def merge_lines(editor):
	"""
	Merge lines spanned by user selection. If there's no selection, tries to find
	matching tags and use them as selection
	@param editor: Editor instance
	@type editor: ZenEditor
	"""
	start, end = editor.get_selection_range()
	if start == end:
		# find matching tag
		pair = html_matcher.match(editor.get_content(), editor.get_caret_pos(), editor.get_profile_name())
		if pair and pair[0] is not None:
			start, end = pair
	
	if start != end:
		# got range, merge lines
		text = editor.get_content()[start:end]
		lines = map(lambda s: re.sub(r'^\s+', '', s), zen_coding.split_by_lines(text))
		text = re.sub(r'\s{2,}', ' ', ''.join(lines))
		editor.replace_content(text, start, end)
		editor.create_selection(start, start + len(text))
		return True
	
	return False

def toggle_comment(editor):
	"""
	Toggle comment on current editor's selection or HTML tag/CSS rule
	@type editor: ZenEditor
	"""
	syntax = editor.get_syntax()
	if syntax == 'css':
		return toggle_css_comment(editor)
	else:
		return toggle_html_comment(editor)

def toggle_html_comment(editor):
	"""
	Toggle HTML comment on current selection or tag
	@type editor: ZenEditor
	@return: True if comment was toggled
	"""
	start, end = editor.get_selection_range()
	content = editor.get_content()
		
	if start == end:
		# no selection, find matching tag
		pair = html_matcher.get_tags(content, editor.get_caret_pos(), editor.get_profile_name())
		if pair and pair[0]: # found pair
			start = pair[0].start
			end = pair[1] and pair[1].end or pair[0].end
	
	return generic_comment_toggle(editor, '<!--', '-->', start, end)

def toggle_css_comment(editor):
	"""
	Simple CSS commenting
	@type editor: ZenEditor
	@return: True if comment was toggled
	"""
	start, end = editor.get_selection_range()
	
	if start == end:
		# no selection, get current line
		start, end = editor.get_current_line_range()

		# adjust start index till first non-space character
		start, end = narrow_to_non_space(editor.get_content(), start, end)
	
	return generic_comment_toggle(editor, '/*', '*/', start, end)

def search_comment(text, pos, start_token, end_token):
	"""
	Search for nearest comment in <code>str</code>, starting from index <code>from</code>
	@param text: Where to search
	@type text: str
	@param pos: Search start index
	@type pos: int
	@param start_token: Comment start string
	@type start_token: str
	@param end_token: Comment end string
	@type end_token: str
	@return: None if comment wasn't found, list otherwise
	"""
	start_ch = start_token[0]
	end_ch = end_token[0]
	comment_start = -1
	comment_end = -1
	
	def has_match(tx, start):
		return text[start:start + len(tx)] == tx
	
		
	# search for comment start
	while pos:
		pos -= 1
		if text[pos] == start_ch and has_match(start_token, pos):
			comment_start = pos
			break
	
	if comment_start != -1:
		# search for comment end
		pos = comment_start
		content_len = len(text)
		while content_len >= pos:
			pos += 1
			if text[pos] == end_ch and has_match(end_token, pos):
				comment_end = pos + len(end_token)
				break
	
	if comment_start != -1 and comment_end != -1:
		return comment_start, comment_end
	else:
		return None

def generic_comment_toggle(editor, comment_start, comment_end, range_start, range_end):
	"""
	Generic comment toggling routine
	@type editor: ZenEditor
	@param comment_start: Comment start token
	@type comment_start: str
	@param comment_end: Comment end token
	@type comment_end: str
	@param range_start: Start selection range
	@type range_start: int
	@param range_end: End selection range
	@type range_end: int
	@return: bool
	"""
	content = editor.get_content()
	caret_pos = [editor.get_caret_pos()]
	new_content = None
		
	def adjust_caret_pos(m):
		caret_pos[0] -= len(m.group(0))
		return ''
		
	def remove_comment(text):
		"""
		Remove comment markers from string
		@param {Sting} str
		@return {String}
		"""
		text = re.sub(r'^' + re.escape(comment_start) + r'\s*', adjust_caret_pos, text)
		return re.sub(r'\s*' + re.escape(comment_end) + '$', '', text)
	
	def has_match(tx, start):
		return content[start:start + len(tx)] == tx
	
	# first, we need to make sure that this substring is not inside comment
	comment_range = search_comment(content, caret_pos[0], comment_start, comment_end)
	
	if comment_range and comment_range[0] <= range_start and comment_range[1] >= range_end:
		# we're inside comment, remove it
		range_start, range_end = comment_range
		new_content = remove_comment(content[range_start:range_end])
	else:
		# should add comment
		# make sure that there's no comment inside selection
		new_content = '%s %s %s' % (comment_start, re.sub(re.escape(comment_start) + r'\s*|\s*' + re.escape(comment_end), '', content[range_start:range_end]), comment_end)
			
		# adjust caret position
		caret_pos[0] += len(comment_start) + 1

	# replace editor content
	if new_content is not None:
		d = caret_pos[0] - range_start
		new_content = new_content[0:d] + zen_coding.get_caret_placeholder() + new_content[d:]
		editor.replace_content(unindent(editor, new_content), range_start, range_end)
		return True
	
	return False

def split_join_tag(editor, profile_name=None):
	"""
	Splits or joins tag, e.g. transforms it into a short notation and vice versa:
	<div></div> → <div /> : join
	<div /> → <div></div> : split
	@param editor: Editor instance
	@type editor: ZenEditor
	@param profile_name: Profile name
	@type profile_name: str
	"""
	caret_pos = editor.get_caret_pos()
	profile = zen_coding.get_profile(profile_name or editor.get_profile_name())
	caret = zen_coding.get_caret_placeholder()

	# find tag at current position
	pair = html_matcher.get_tags(editor.get_content(), caret_pos, profile_name or editor.get_profile_name())
	if pair and pair[0]:
		new_content = pair[0].full_tag
		
		if pair[1]: # join tag
			closing_slash = ''
			if profile['self_closing_tag'] is True:
				closing_slash = '/'
			elif profile['self_closing_tag'] == 'xhtml':
				closing_slash = ' /'
				
			new_content = re.sub(r'\s*>$', closing_slash + '>', new_content)
			
			# add caret placeholder
			if len(new_content) + pair[0].start < caret_pos:
				new_content += caret
			else:
				d = caret_pos - pair[0].start
				new_content = new_content[0:d] + caret + new_content[d:]
			
			editor.replace_content(new_content, pair[0].start, pair[1].end)
		else: # split tag
			nl = zen_coding.get_newline()
			pad = zen_coding.get_variable('indentation')
			
			# define tag content depending on profile
			tag_content = profile['tag_nl'] is True and nl + pad + caret + nl or caret
			
			new_content = '%s%s</%s>' % (re.sub(r'\s*\/>$', '>', new_content), tag_content, pair[0].name)
			editor.replace_content(new_content, pair[0].start, pair[0].end)
		
		return True
	else:
		return False
	

def get_line_bounds(text, pos):
	"""
	Returns line bounds for specific character position
	@type text: str
	@param pos: Where to start searching
	@type pos: int
	@return: list
	"""
	start = 0
	end = len(text) - 1
	
	# search left
	for i in range(pos - 1, 0, -1):
		if text[i] in '\n\r':
			start = i + 1
			break
		
	# search right
	for i in range(pos, len(text)):
		if text[i] in '\n\r':
			end = i
			break
		
	return start, end

def remove_tag(editor):
	"""
	Gracefully removes tag under cursor
	@type editor: ZenEditor
	"""
	caret_pos = editor.get_caret_pos()
	content = editor.get_content()
		
	# search for tag
	pair = html_matcher.get_tags(content, caret_pos, editor.get_profile_name())
	if pair and pair[0]:
		if not pair[1]:
			# simply remove unary tag
			editor.replace_content(zen_coding.get_caret_placeholder(), pair[0].start, pair[0].end)
		else:
			tag_content_range = narrow_to_non_space(content, pair[0].end, pair[1].start)
			start_line_bounds = get_line_bounds(content, tag_content_range[0])
			start_line_pad = get_line_padding(content[start_line_bounds[0]:start_line_bounds[1]])
			tag_content = content[tag_content_range[0]:tag_content_range[1]]
				
			tag_content = unindent_text(tag_content, start_line_pad)
			editor.replace_content(zen_coding.get_caret_placeholder() + tag_content, pair[0].start, pair[1].end)
		
		return True
	else:
		return False

########NEW FILE########
__FILENAME__ = zen_core
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Core Zen Coding library. Contains various text manipulation functions:

== Expand abbreviation
Expands abbreviation like ul#nav>li*5>a into a XHTML string.
=== How to use
First, you have to extract current string (where cursor is) from your test 
editor and use <code>find_abbr_in_line()</code> method to extract abbreviation. 
If abbreviation was found, this method will return it as well as position index
of abbreviation inside current line. If abbreviation wasn't 
found, method returns empty string. With abbreviation found, you should call
<code>parse_into_tree()</code> method to transform abbreviation into a tag tree. 
This method returns <code>Tag</code> object on success, None on failure. Then
simply call <code>to_string()</code> method of returned <code>Tag</code> object
to transoform tree into a XHTML string

You can setup output profile using <code>setup_profile()</code> method 
(see <code>default_profile</code> definition for available options) 

 
Created on Apr 17, 2009

@author: Sergey Chikuyonok (http://chikuyonok.ru)
'''
from zen_settings import zen_settings
import re
import stparser

newline = '\n'
"Newline symbol"

caret_placeholder = '{%::zen-caret::%}'

default_tag = 'div'

re_tag = re.compile(r'<\/?[\w:\-]+(?:\s+[\w\-:]+(?:\s*=\s*(?:(?:"[^"]*")|(?:\'[^\']*\')|[^>\s]+))?)*\s*(\/?)>$')

profiles = {}
"Available output profiles"

default_profile = {
	'tag_case': 'lower',         # values are 'lower', 'upper'
	'attr_case': 'lower',        # values are 'lower', 'upper'
	'attr_quotes': 'double',     # values are 'single', 'double'
	
	'tag_nl': 'decide',          # each tag on new line, values are True, False, 'decide'
	
	'place_cursor': True,        # place cursor char — | (pipe) — in output
	
	'indent': True,              # indent tags
	
	'inline_break': 3,           # how many inline elements should be to force line break (set to 0 to disable)
	
	'self_closing_tag': 'xhtml'  # use self-closing style for writing empty elements, e.g. <br /> or <br>. 
                                 # values are True, False, 'xhtml'
}

basic_filters = 'html';
"Filters that will be applied for unknown syntax"

max_tabstop = 0
"Maximum tabstop index for current session"

def char_at(text, pos):
	"""
	Returns character at specified index of text.
	If index if out of range, returns empty string
	"""
	return text[pos] if pos < len(text) else ''

def has_deep_key(obj, key):
	"""
	Check if <code>obj</code> dictionary contains deep key. For example,
	example, it will allow you to test existance of my_dict[key1][key2][key3],
	testing existance of my_dict[key1] first, then my_dict[key1][key2], 
	and finally my_dict[key1][key2][key3]
	@param obj: Dictionary to test
	@param obj: dict
	@param key: Deep key to test. Can be list (like ['key1', 'key2', 'key3']) or
	string (like 'key1.key2.key3')
	@type key: list, tuple, str
	@return: bool
	"""
	if isinstance(key, str):
		key = key.split('.')
		
	last_obj = obj
	for v in key:
		if hasattr(last_obj, v):
			last_obj = getattr(last_obj, v)
		elif last_obj.has_key(v):
			last_obj = last_obj[v]
		else:
			return False
	
	return True
		

def is_allowed_char(ch):
	"""
	Test if passed symbol is allowed in abbreviation
	@param ch: Symbol to test
	@type ch: str
	@return: bool
	"""
	return ch.isalnum() or ch in "#.>+*:$-_!@[]()|"

def split_by_lines(text, remove_empty=False):
	"""
	Split text into lines. Set <code>remove_empty</code> to true to filter out
	empty lines
	@param text: str
	@param remove_empty: bool
	@return list
	"""
	lines = text.splitlines()
	
	return remove_empty and [line for line in lines if line.strip()] or lines

def make_map(prop):
	"""
	Helper function that transforms string into dictionary for faster search
	@param prop: Key name in <code>zen_settings['html']</code> dictionary
	@type prop: str
	"""
	obj = {}
	for a in zen_settings['html'][prop].split(','):
		obj[a] = True
		
	zen_settings['html'][prop] = obj

def create_profile(options):
	"""
	Create profile by adding default values for passed optoin set
	@param options: Profile options
	@type options: dict
	"""
	for k, v in default_profile.items():
		options.setdefault(k, v)
	
	return options

def setup_profile(name, options = {}):
	"""
	@param name: Profile name
	@type name: str
	@param options: Profile options
	@type options: dict
	"""
	profiles[name.lower()] = create_profile(options);

def get_newline():
	"""
	Returns newline symbol which is used in editor. This function must be 
	redefined to return current editor's settings 
	@return: str
	"""
	return newline

def set_newline(char):
	"""
	Sets newline character used in Zen Coding
	"""
	global newline
	newline = char

def string_to_hash(text):
	"""
	Helper function that transforms string into hash
	@return: dict
	"""
	obj = {}
	items = text.split(",")
	for i in items:
		obj[i] = True
		
	return obj

def pad_string(text, pad):
	"""
	Indents string with space characters (whitespace or tab)
	@param text: Text to indent
	@type text: str
	@param pad: Indentation level (number) or indentation itself (string)
	@type pad: int, str
	@return: str
	"""
	pad_str = ''
	result = ''
	if isinstance(pad, basestring):
		pad_str = pad
	else:
		pad_str = get_indentation() * pad
		
	nl = get_newline()
	
	lines = split_by_lines(text)
	
	if lines:
		result += lines[0]
		for line in lines[1:]:
			result += nl + pad_str + line
			
	return result

def is_snippet(abbr, doc_type = 'html'):
	"""
	Check is passed abbreviation is a snippet
	@return bool
	"""
	return get_snippet(doc_type, abbr) and True or False

def is_ends_with_tag(text):
	"""
	Test is string ends with XHTML tag. This function used for testing if '<'
	symbol belogs to tag or abbreviation 
	@type text: str
	@return: bool
	"""
	return re_tag.search(text) != None

def get_elements_collection(resource, type):
	"""
	Returns specified elements collection (like 'empty', 'block_level') from
	<code>resource</code>. If collections wasn't found, returns empty object
	@type resource: dict
	@type type: str
	@return: dict
	"""
	if 'element_types' in resource and type in resource['element_types']:
		return resource['element_types'][type]
	else:
		return {}
	
def replace_variables(text):
	"""
	Replace variables like ${var} in string
	@param text: str
	@return: str
	"""
	return re.sub(r'\$\{([\w\-]+)\}', lambda m: get_variable(m.group(1)) or m.group(0), text)

def get_abbreviation(res_type, abbr):
	"""
	Returns abbreviation value from data set
	@param res_type: Resource type (html, css, ...)
	@type res_type: str
	@param abbr: Abbreviation name
	@type abbr: str
	@return dict, None
	"""
	return get_settings_resource(res_type, abbr, 'abbreviations')

def get_snippet(res_type, snippet_name):
	"""
	Returns snippet value from data set
	@param res_type: Resource type (html, css, ...)
	@type res_type: str
	@param snippet_name: Snippet name
	@type snippet_name: str
	@return dict, None
	"""
	return get_settings_resource(res_type, snippet_name, 'snippets');

def get_variable(name):
	"""
	Returns variable value
	 @return: str
	"""
	if name in zen_settings['variables']:
		return zen_settings['variables'][name]
	return None

def set_variable(name, value):
	"""
	Set variable value
	"""
	zen_settings['variables'][name] = value

def get_indentation():
	"""
	Returns indentation string
	@return {String}
	"""
	return get_variable('indentation');

def create_resource_chain(syntax, name):
	"""
	Creates resource inheritance chain for lookups
	@param syntax: Syntax name
	@type syntax: str
	@param name: Resource name
	@type name: str
	@return: list
	"""
	result = []
	
	if syntax in zen_settings:
		resource = zen_settings[syntax]
		if name in resource:
			result.append(resource[name])
		if 'extends' in resource:
			# find resource in ancestors
			for type in resource['extends']:
				if  has_deep_key(zen_settings, [type, name]):
					result.append(zen_settings[type][name])
				
	return result

def get_resource(syntax, name):
	"""
	Get resource collection from settings file for specified syntax. 
	It follows inheritance chain if resource wasn't directly found in
	syntax settings
	@param syntax: Syntax name
	@type syntax: str
	@param name: Resource name
	@type name: str
	"""
	chain = create_resource_chain(syntax, name)
	return chain[0] if chain else None

def get_settings_resource(syntax, abbr, name):
	"""
	Returns resurce value from data set with respect of inheritance
	@param syntax: Resource syntax (html, css, ...)
	@type syntax: str
	@param abbr: Abbreviation name
	@type abbr: str
	@param name: Resource name ('snippets' or 'abbreviation')
	@type name: str
	@return dict, None
	"""
	for item in create_resource_chain(syntax, name):
		if abbr in item:
			return item[abbr]
		
	return None

def get_word(ix, text):
	"""
	Get word, starting at <code>ix</code> character of <code>text</code>
	@param ix: int
	@param text: str
	"""
	m = re.match(r'^[\w\-:\$]+', text[ix:])
	return m.group(0) if m else ''
	
def extract_attributes(attr_set):
	"""
	Extract attributes and their values from attribute set 
 	@param attr_set: str
	"""
	attr_set = attr_set.strip()
	loop_count = 100 # endless loop protection
	re_string = r'^(["\'])((?:(?!\1)[^\\]|\\.)*)\1'
	result = []
		
	while attr_set and loop_count:
		loop_count -= 1
		attr_name = get_word(0, attr_set)
		attr = None
		if attr_name:
			attr = {'name': attr_name, 'value': ''}
			
			# let's see if attribute has value
			ch = attr_set[len(attr_name)] if len(attr_set) > len(attr_name) else ''
			if ch == '=':
				ch2 = attr_set[len(attr_name) + 1]
				if ch2 in '"\'':
					# we have a quoted string
					m = re.match(re_string, attr_set[len(attr_name) + 1:])
					if m:
						attr['value'] = m.group(2)
						attr_set = attr_set[len(attr_name) + len(m.group(0)) + 1:].strip()
					else:
						# something wrong, break loop
						attr_set = ''
				else:
					# unquoted string
					m = re.match(r'^(.+?)(\s|$)', attr_set[len(attr_name) + 1:])
					if m:
						attr['value'] = m.group(1)
						attr_set = attr_set[len(attr_name) + len(m.group(1)) + 1:].strip()
					else:
						# something wrong, break loop
						attr_set = ''
				
			else:
				attr_set = attr_set[len(attr_name):].strip()
		else:
			# something wrong, can't extract attribute name
			break
		
		if attr: result.append(attr)
		
	return result

def parse_attributes(text):
	"""
	Parses tag attributes extracted from abbreviation
	"""
	
#	Example of incoming data:
#	#header
#	.some.data
#	.some.data#header
#	[attr]
#	#item[attr=Hello other="World"].class

	result = []
	class_name = None
	char_map = {'#': 'id', '.': 'class'}
	
	# walk char-by-char
	i = 0
	il = len(text)
		
	while i < il:
		ch = text[i]
		
		if ch == '#': # id
			val = get_word(i, text[1:])
			result.append({'name': char_map[ch], 'value': val})
			i += len(val) + 1
			
		elif ch == '.': #class
			val = get_word(i, text[1:])
			if not class_name:
				# remember object pointer for value modification
				class_name = {'name': char_map[ch], 'value': ''}
				result.append(class_name)
			
			if class_name['value']:
				class_name['value'] += ' ' + val
			else:
				class_name['value'] = val
			
			i += len(val) + 1
				
		elif ch == '[': # begin attribute set
			# search for end of set
			end_ix = text.find(']', i)
			if end_ix == -1:
				# invalid attribute set, stop searching
				i = len(text)
			else:
				result.extend(extract_attributes(text[i + 1:end_ix]))
				i = end_ix
		else:
			i += 1
		
		
	return result

class AbbrGroup(object):
	"""
	Abreviation's group element
	"""
	def __init__(self, parent=None):
		"""
		@param parent: Parent group item element
		@type parent: AbbrGroup
		"""
		self.expr = ''
		self.parent = parent
		self.children = []
		
	def add_child(self):
		child = AbbrGroup(self)
		self.children.append(child)
		return child
	
	def clean_up(self):
		for item in self.children:
			expr = item.expr
			if not expr:
				self.children.remove(item)
			else:
				# remove operators at the and of expression
				item.clean_up()

def split_by_groups(abbr):
	"""
	Split abbreviation by groups
	@type abbr: str
	@return: AbbrGroup
	"""
	root = AbbrGroup()
	last_parent = root
	cur_item = root.add_child()
	stack = []
	i = 0
	il = len(abbr)
	
	while i < il:
		ch = abbr[i]
		if ch == '(':
			# found new group
			operator = i and abbr[i - 1] or ''
			if operator == '>':
				stack.append(cur_item)
				last_parent = cur_item
			else:
				stack.append(last_parent)
			cur_item = None
		elif ch == ')':
			last_parent = stack.pop()
			cur_item = None
			next_char = char_at(abbr, i + 1)
			if next_char == '+' or next_char == '>': 
				# next char is group operator, skip it
				i += 1
		else:
			if ch == '+' or ch == '>':
				# skip operator if it's followed by parenthesis
				next_char = char_at(abbr, i + 1)
				if next_char == '(':
					i += 1 
					continue
			
			if not cur_item:
				cur_item = last_parent.add_child()
			cur_item.expr += ch
			
		i += 1
	
	root.clean_up()
	return root

def rollout_tree(tree, parent=None):
	"""
	Roll outs basic Zen Coding tree into simplified, DOM-like tree.
	The simplified tree, for example, represents each multiplied element 
	as a separate element sets with its own content, if exists.
	 
	The simplified tree element contains some meta info (tag name, attributes, 
	etc.) as well as output strings, which are exactly what will be outputted
	after expanding abbreviation. This tree is used for <i>filtering</i>:
	you can apply filters that will alter output strings to get desired look
	of expanded abbreviation.
	 
	@type tree: Tag
	@param parent: ZenNode
	"""
	if not parent:
		parent = ZenNode(tree)
		
	how_many = 1
	tag_content = ''
	
	for child in tree.children:
		how_many = child.count
		
		if child.repeat_by_lines:
			# it's a repeating element
			tag_content = split_by_lines(child.get_content(), True)
			how_many = max(len(tag_content), 1)
		else:
			tag_content = child.get_content()
		
		for j in range(how_many):
			tag = ZenNode(child)
			parent.add_child(tag)
			tag.counter = j + 1
			
			if child.children:
				rollout_tree(child, tag)
				
			add_point = tag.find_deepest_child() or tag
			
			if tag_content:
				if isinstance(tag_content, basestring):
					add_point.content = tag_content
				else:
					add_point.content = tag_content[j] or ''
					
	return parent

def run_filters(tree, profile, filter_list):
	"""
	Runs filters on tree
	@type tree: ZenNode
	@param profile: str, object
	@param filter_list: str, list
	@return: ZenNode
	"""
	import filters
	
	if isinstance(profile, basestring) and profile in profiles:
		profile = profiles[profile];
	
	if not profile:
		profile = profiles['plain']
		
	if isinstance(filter_list, basestring):
		filter_list = re.split(r'[\|,]', filter_list)
		
	for name in filter_list:
		name = name.strip()
		if name and name in filters.filter_map:
			tree = filters.filter_map[name](tree, profile)
			
	return tree

def abbr_to_primary_tree(abbr, doc_type='html'):
	"""
	Transforms abbreviation into a primary internal tree. This tree should'n 
	be used ouside of this scope
	@param abbr: Abbreviation to transform
	@type abbr: str
	@param doc_type: Document type (xsl, html), a key of dictionary where to
	search abbreviation settings
	@type doc_type: str
	@return: Tag
	"""
	root = Tag('', 1, doc_type)
	token = re.compile(r'([\+>])?([a-z@\!\#\.][\w:\-]*)((?:(?:[#\.][\w\-\$]+)|(?:\[[^\]]+\]))+)?(\*(\d*))?(\+$)?', re.IGNORECASE)
	
	if not abbr:
		return None
	
	def expando_replace(m):
		ex = m.group(0)
		a = get_abbreviation(doc_type, ex)
		return a and a.value or ex
		
	def token_expander(operator, tag_name, attrs, has_multiplier, multiplier, has_expando):
		multiply_by_lines = (has_multiplier and not multiplier)
		multiplier = multiplier and int(multiplier) or 1
		
		tag_ch = tag_name[0]
		if tag_ch == '#' or tag_ch == '.':
			if attrs: attrs = tag_name + attrs
			else: attrs = tag_name
			tag_name = default_tag
		
		if has_expando:
			tag_name += '+'
		
		current = is_snippet(tag_name, doc_type) and Snippet(tag_name, multiplier, doc_type) or Tag(tag_name, multiplier, doc_type)
		
		if attrs:
			attrs = parse_attributes(attrs)
			for attr in attrs:
				current.add_attribute(attr['name'], attr['value'])
			
		# dive into tree
		if operator == '>' and token_expander.last:
			token_expander.parent = token_expander.last;
			
		token_expander.parent.add_child(current)
		token_expander.last = current
		
		if multiply_by_lines:
			root.multiply_elem = current
		
		return ''
		
	# replace expandos
	abbr = re.sub(r'([a-z][a-z0-9]*)\+$', expando_replace, abbr)
	
	token_expander.parent = root
	token_expander.last = None
	
	
#	abbr = re.sub(token, lambda m: token_expander(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6), m.group(7)), abbr)
	# Issue from Einar Egilsson
	abbr = token.sub(lambda m: token_expander(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)), abbr)
	
	root.last = token_expander.last
	
	# empty 'abbr' variable means that abbreviation was expanded successfully, 
	# non-empty variable means there was a syntax error
	return not abbr and root or None;

def expand_group(group, doc_type, parent):
	"""
	Expand single group item 
	@param group: AbbrGroup
	@param doc_type: str
	@param parent: Tag
	"""
	tree = abbr_to_primary_tree(group.expr, doc_type)
	last_item = None
		
	if tree:
		for item in tree.children:
			last_item = item
			parent.add_child(last_item)
	else:
		raise Exception('InvalidGroup')
	
	
	# set repeating element to the topmost node
	root = parent
	while root.parent:
		root = root.parent
	
	root.last = tree.last
	if tree.multiply_elem:
		root.multiply_elem = tree.multiply_elem
		
	# process child groups
	if group.children:
		add_point = last_item.find_deepest_child() or last_item
		for child in group.children:
			expand_group(child, doc_type, add_point)

def replace_unescaped_symbol(text, symbol, replace):
	"""
	Replaces unescaped symbols in <code>text</code>. For example, the '$' symbol
	will be replaced in 'item$count', but not in 'item\$count'.
	@param text: Original string
	@type text: str
	@param symbol: Symbol to replace
	@type symbol: st
	@param replace: Symbol replacement
	@type replace: str, function 
	@return: str
	"""
	i = 0
	il = len(text)
	sl = len(symbol)
	match_count = 0
		
	while i < il:
		if text[i] == '\\':
			# escaped symbol, skip next character
			i += sl + 1
		elif text[i:i + sl] == symbol:
			# have match
			cur_sl = sl
			match_count += 1
			new_value = replace
			if callable(new_value):
				replace_data = replace(text, symbol, i, match_count)
				if replace_data:
					cur_sl = len(replace_data[0])
					new_value = replace_data[1]
				else:
					new_value = False
			
			if new_value is False: # skip replacement
				i += 1
				continue
			
			text = text[0:i] + new_value + text[i + cur_sl:]
			# adjust indexes
			il = len(text)
			i += len(new_value)
		else:
			i += 1
	
	return text
	
def run_action(name, *args, **kwargs):
	"""
	 Runs Zen Coding action. For list of available actions and their
	 arguments see zen_actions.py file.
	 @param name: Action name 
	 @type name: str 
	 @param args: Additional arguments. It may be array of arguments
	 or inline arguments. The first argument should be <code>zen_editor</code> instance
	 @type args: list
	 @example
	 zen_coding.run_actions('expand_abbreviation', zen_editor)
	 zen_coding.run_actions('wrap_with_abbreviation', zen_editor, 'div')  
	"""
	import zen_actions
	
	try:
		if hasattr(zen_actions, name):
			return getattr(zen_actions, name)(*args, **kwargs)
	except:
		return False

def expand_abbreviation(abbr, syntax='html', profile_name='plain'):
	"""
	Expands abbreviation into a XHTML tag string
	@type abbr: str
	@return: str
	"""
	tree_root = parse_into_tree(abbr, syntax);
	if tree_root:
		tree = rollout_tree(tree_root)
		apply_filters(tree, syntax, profile_name, tree_root.filters)
		return replace_variables(tree.to_string())
	
	return ''

def extract_abbreviation(text):
	"""
	Extracts abbreviations from text stream, starting from the end
	@type text: str
	@return: Abbreviation or empty string
	"""
	cur_offset = len(text)
	start_index = -1
	brace_count = 0
	
	while True:
		cur_offset -= 1
		if cur_offset < 0:
			# moved at string start
			start_index = 0
			break
		
		ch = text[cur_offset]
		
		if ch == ']':
			brace_count += 1
		elif ch == '[':
			brace_count -= 1
		else:
			if brace_count: 
				# respect all characters inside attribute sets
				continue
			if not is_allowed_char(ch) or (ch == '>' and is_ends_with_tag(text[0:cur_offset + 1])):
				# found stop symbol
				start_index = cur_offset + 1
				break
		
	return text[start_index:] if start_index != -1 else ''

def parse_into_tree(abbr, doc_type='html'):
	"""
	Parses abbreviation into a node set
	@param abbr: Abbreviation to transform
	@type abbr: str
	@param doc_type: Document type (xsl, html), a key of dictionary where to
	search abbreviation settings
	@type doc_type: str
	@return: Tag
	"""
	# remove filters from abbreviation
	filter_list = []
	
	def filter_replace(m):
		filter_list.append(m.group(1))
		return ''
	
	re_filter = re.compile(r'\|([\w\|\-]+)$')
	abbr = re_filter.sub(filter_replace, abbr)
	
	# split abbreviation by groups
	group_root = split_by_groups(abbr)
	tree_root = Tag('', 1, doc_type)
	
	# then recursively expand each group item
	try:
		for item in group_root.children:
			expand_group(item, doc_type, tree_root)
	except:
		# there's invalid group, stop parsing
		return None
	
	tree_root.filters = ''.join(filter_list)
	return tree_root

def is_inside_tag(html, cursor_pos):
	re_tag = re.compile(r'^<\/?\w[\w\:\-]*.*?>')
	
	# search left to find opening brace
	pos = cursor_pos
	while pos > -1:
		if html[pos] == '<': break
		pos -= 1
	
	
	if pos != -1:
		m = re_tag.match(html[pos:]);
		if m and cursor_pos > pos and cursor_pos < pos + len(m.group(0)):
			return True

	return False

def wrap_with_abbreviation(abbr, text, doc_type='html', profile='plain'):
	"""
	Wraps passed text with abbreviation. Text will be placed inside last
	expanded element
	@param abbr: Abbreviation
	@type abbr: str
	
	@param text: Text to wrap
	@type text: str
	
	@param doc_type: Document type (html, xml, etc.)
	@type doc_type: str
	
	@param profile: Output profile's name.
	@type profile: str
	@return {String}
	"""
	tree_root = parse_into_tree(abbr, doc_type)
	if tree_root:
		repeat_elem = tree_root.multiply_elem or tree_root.last
		repeat_elem.set_content(text)
		repeat_elem.repeat_by_lines = bool(tree_root.multiply_elem)
		
		tree = rollout_tree(tree_root)
		apply_filters(tree, doc_type, profile, tree_root.filters);
		return replace_variables(tree.to_string())
	
	return None

def get_caret_placeholder():
	"""
	Returns caret placeholder
	@return: str
	"""
	if callable(caret_placeholder):
		return caret_placeholder()
	else:
		return caret_placeholder

def set_caret_placeholder(value):
	"""
	Set caret placeholder: a string (like '|') or function.
	You may use a function as a placeholder generator. For example,
	TextMate uses ${0}, ${1}, ..., ${n} natively for quick Tab-switching
	between them.
	@param {String|Function}
	"""
	global caret_placeholder
	caret_placeholder = value

def apply_filters(tree, syntax, profile, additional_filters=None):
	"""
	Applies filters to tree according to syntax
	@param tree: Tag tree to apply filters to
	@type tree: ZenNode
	@param syntax: Syntax name ('html', 'css', etc.)
	@type syntax: str
	@param profile: Profile or profile's name
	@type profile: str, object
	@param additional_filters: List or pipe-separated string of additional filters to apply
	@type additional_filters: str, list 
	 
	@return: ZenNode
	"""
	_filters = get_resource(syntax, 'filters') or basic_filters
		
	if additional_filters:
		_filters += '|'
		if isinstance(additional_filters, basestring):
			_filters += additional_filters
		else:
			_filters += '|'.join(additional_filters)
		
	if not _filters:
		# looks like unknown syntax, apply basic filters
		_filters = basic_filters
		
	return run_filters(tree, profile, _filters)

def replace_counter(text, value):
	"""
	 Replaces '$' character in string assuming it might be escaped with '\'
	 @type text: str
	 @type value: str, int
	 @return: str
	"""
	symbol = '$'
	value = str(value)
	
	def replace_func(tx, symbol, pos, match_num):
		if char_at(tx, pos + 1) == '{' or char_at(tx, pos + 1).isdigit():
			# it's a variable, skip it
			return False
		
		# replace sequense of $ symbols with padded number  
		j = pos + 1
		if j < len(text):
			while tx[j] == '$' and char_at(tx, j + 1) != '{': j += 1
		
		return (tx[pos:j], value.zfill(j - pos))
	
	return replace_unescaped_symbol(text, symbol, replace_func)

def upgrade_tabstops(node):
	"""
	Upgrades tabstops in zen node in order to prevent naming conflicts
	@type node: ZenNode
	@param offset: Tab index offset
	@type offset: int
	@returns Maximum tabstop index in element
	"""
	max_num = [0]
	props = ('start', 'end', 'content')
	
	def _replace(m):
		num = int(m.group(1) or m.group(2))
		if num > max_num[0]: max_num[0] = num
		return re.sub(r'\d+', str(num + max_tabstop), m.group(0), 1)
	
	for prop in props:
		node.__setattr__(prop, re.sub(r'\$(\d+)|\$\{(\d+):[^\}]+\}', _replace, node.__getattribute__(prop)))
		
	globals()['max_tabstop'] += max_num[0]
		
	return max_num[0]

def unescape_text(text):
	"""
	Unescapes special characters used in Zen Coding, like '$', '|', etc.
	@type text: str
	@return: str
	"""
	return re.sub(r'\\(.)', r'\1', text)

def get_profile(name):
	"""
	Get profile by it's name. If profile wasn't found, returns 'plain' profile
	"""
	return profiles[name] if name in profiles else profiles['plain']

def update_settings(settings):
	globals()['zen_settings'] = settings
	
class Tag(object):
	def __init__(self, name, count=1, doc_type='html'):
		"""
		@param name: Tag name
		@type name: str
		@param count:  How many times this tag must be outputted
		@type count: int
		@param doc_type: Document type (xsl, html)
		@type doc_type: str
		"""
		name = name.lower()
		
		abbr = get_abbreviation(doc_type, name)
		
		if abbr and abbr.type == stparser.TYPE_REFERENCE:
			abbr = get_abbreviation(doc_type, abbr.value)
		
		self.name = abbr and abbr.value['name'] or name.replace('+', '')
		self.count = count
		self.children = []
		self.attributes = []
		self.multiply_elem = None
		self.__attr_hash = {}
		self._abbr = abbr
		self.__content = ''
		self.repeat_by_lines = False
		self._res = zen_settings.has_key(doc_type) and zen_settings[doc_type] or {}
		self.parent = None
		
		# add default attributes
		if self._abbr and 'attributes' in self._abbr.value:
			for a in self._abbr.value['attributes']:
				self.add_attribute(a['name'], a['value'])
		
	def add_child(self, tag):
		"""
		Add new child
		@type tag: Tag
		"""
		tag.parent = self
		self.children.append(tag)
		
	def add_attribute(self, name, value):
		"""
		Add attribute to tag. If the attribute with the same name already exists,
		it will be overwritten, but if it's name is 'class', it will be merged
		with the existed one
		@param name: Attribute nama
		@type name: str
		@param value: Attribute value
		@type value: str
		"""
		
		# the only place in Tag where pipe (caret) character may exist
		# is the attribute: escape it with internal placeholder
		value = replace_unescaped_symbol(value, '|', get_caret_placeholder());
		
		if name in self.__attr_hash:
#			attribue already exists
			a = self.__attr_hash[name]
			if name == 'class':
#				'class' is a magic attribute
				if a['value']:
					value = ' ' + value
				a['value'] += value
			else:
				a['value'] = value
		else:
			a = {'name': name, 'value': value}
			self.__attr_hash[name] = a
			self.attributes.append(a)
	
	def has_tags_in_content(self):
		"""
		This function tests if current tags' content contains XHTML tags. 
	 	This function is mostly used for output formatting
		"""
		return self.get_content() and re_tag.search(self.get_content())
	
	def get_content(self):
		return self.__content
	
	def set_content(self, value):
		self.__content = value
		
	def set_content(self, content): #@DuplicatedSignature
		self.__content = content
		
	def get_content(self): #@DuplicatedSignature
		return self.__content
	
	def find_deepest_child(self):
		"""
		Search for deepest and latest child of current element.
		Returns None if there's no children
	 	@return Tag or None 
		"""
		if not self.children:
			return None
			
		deepest_child = self
		while True:
			deepest_child = deepest_child.children[-1]
			if not deepest_child.children:
				break
		
		return deepest_child
	
class Snippet(Tag):
	def __init__(self, name, count=1, doc_type='html'):
		super(Snippet, self).__init__(name, count, doc_type)
		self.value = replace_unescaped_symbol(get_snippet(doc_type, name), '|', get_caret_placeholder())
		self.attributes = {'id': get_caret_placeholder(), 'class': get_caret_placeholder()}
		self._res = zen_settings[doc_type]		
	
	def is_block(self):
		return True
	
class ZenNode(object):
	"""
	Creates simplified tag from Zen Coding tag
	"""
	def __init__(self, tag):
		"""
		@type tag: Tag
		"""
		self.type = 'snippet' if isinstance(tag, Snippet) else 'tag'
		self.name = tag.name
		self.attributes = tag.attributes
		self.children = [];
		self.counter = 1
		
		self.source = tag
		"Source element from which current tag was created"
		
		# relations
		self.parent = None
		self.next_sibling = None
		self.previous_sibling = None
		
		# output params
		self.start = ''
		self.end = ''
		self.content = ''
		self.padding = ''

	def add_child(self, tag):
		"""
		@type tag: ZenNode
		"""
		tag.parent = self
		
		if self.children:
			last_child = self.children[-1]
			tag.previous_sibling = last_child
			last_child.next_sibling = tag
		
		self.children.append(tag)
		
	def get_attribute(self, name):
		"""
		Get attribute's value.
		@type name: str
		@return: None if attribute wasn't found
		"""
		name = name.lower()
		for attr in self.attributes:
			if attr['name'].lower() == name:
				return attr['value']
		
		return None
	
	def is_unary(self):
		"""
		Test if current tag is unary (no closing tag)
		@return: bool
		"""
		if self.type == 'snippet':
			return False
			
		return (self.source._abbr and self.source._abbr.value['is_empty']) or (self.name in get_elements_collection(self.source._res, 'empty'))
	
	def is_inline(self):
		"""
		Test if current tag is inline-level (like <strong>, <img>)
		@return: bool
		"""
		return self.name in get_elements_collection(self.source._res, 'inline_level')
	
	def is_block(self):
		"""
		Test if current element is block-level
		@return: bool
		"""
		return self.type == 'snippet' or not self.is_inline()
	
	def has_tags_in_content(self):
		"""
		This function tests if current tags' content contains xHTML tags. 
		This function is mostly used for output formatting
		"""
		return self.content and re_tag.search(self.content)
	
	def has_children(self):
		"""
		Check if tag has child elements
		@return: bool
		"""
		return bool(self.children)
	
	def has_block_children(self):
		"""
		Test if current tag contains block-level children
		@return: bool
		"""
		if self.has_tags_in_content() and self.is_block():
			return True
		
		for item in self.children:
			if item.is_block():
				return True
			
		return False
	
	def find_deepest_child(self):
		"""
		Search for deepest and latest child of current element
		Returns None if there's no children
		@return: ZenNode|None 
		"""
		if not self.children:
			return None
			
		deepest_child = self
		while True:
			deepest_child = deepest_child.children[-1]
			if not deepest_child.children:
				break
		
		return deepest_child
	
	def to_string(self):
		"@return {String}"
		content = ''.join([item.to_string() for item in self.children])
		return self.start + self.content + content + self.end
		
# create default profiles
setup_profile('xhtml');
setup_profile('html', {'self_closing_tag': False});
setup_profile('xml', {'self_closing_tag': True, 'tag_nl': True});
setup_profile('plain', {'tag_nl': False, 'indent': False, 'place_cursor': False});

# This method call explicity loads default settings from zen_settings.py on start up
# Comment this line if you want to load data from other resources (like editor's 
# native snippet) 
update_settings(stparser.get_settings())

########NEW FILE########
__FILENAME__ = zen_dialog
'''
@author Franck Marcia (franck.marcia@gmail.com)
'''

import pygtk
pygtk.require('2.0')
import gtk

class ZenDialog():

    def __init__(self, editor, x, y, callback, text=""):

        self.editor = editor
        self.exit = False
        self.done = False
        self.abbreviation = text
        self.callback = callback

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_decorated(False)
        self.window.connect("destroy", self.quit)
        self.window.connect("focus-out-event", self.focus_lost)
        self.window.connect("key-press-event", self.key_pressed)
        self.window.set_resizable(False)
        self.window.move(x, y - 27)

        self.frame = gtk.Frame()
        self.window.add(self.frame)
        self.frame.show()

        self.box = gtk.HBox()
        self.frame.add(self.box)
        self.box.show()
        
        self.entry = gtk.Entry()
        self.entry.connect("changed", self.update)
        self.entry.set_text(text)
        self.entry.set_has_frame(False)
        self.entry.set_width_chars(36)
        self.box.pack_start(self.entry, True, True, 4)
        self.entry.show()

        self.window.show()

    def key_pressed(widget, what, event):
        if event.keyval == 65293: # Return
            widget.exit = True
            widget.quit()
        elif event.keyval == 65289: # Tab
            widget.exit = True
            widget.quit()
        elif event.keyval == 65307: # Escape
            widget.exit = False
            widget.done = widget.callback(widget.done, '')
            widget.quit()
        else:
            return False
            
    def focus_lost(self, widget=None, event=None):
        self.exit = True
        self.quit()

    def update(self, entry):
        self.abbreviation = self.entry.get_text()
        self.done = self.callback(self.done, self.abbreviation)

    def quit(self, widget=None, event=None):
        self.window.hide()
        self.window.destroy()
        gtk.main_quit()

    def main(self):
        gtk.main()

def main(editor, window, callback, text=""):

    # Ensure the caret is hidden.
    editor.view.set_cursor_visible(False)
    
    # Get coordinates of the cursor.
    offset_start, offset_end = editor.get_selection_range()
    insert = editor.buffer.get_iter_at_offset(offset_start)
    location = editor.view.get_iter_location(insert)
    window = editor.view.get_window(gtk.TEXT_WINDOW_TEXT)
    xo, yo = window.get_origin()
    xb, yb = editor.view.buffer_to_window_coords(gtk.TEXT_WINDOW_TEXT, location.x + location.width, location.y)

    # Open dialog at coordinates with eventual text.
    my_zen_dialog = ZenDialog(editor, xo + xb, yo + yb, callback, text)
    my_zen_dialog.main()

    # Show the caret again.
    editor.view.set_cursor_visible(True)

    # Return exit status and abbreviation.
    return my_zen_dialog.done and my_zen_dialog.exit, my_zen_dialog.abbreviation


########NEW FILE########
__FILENAME__ = zen_editor
'''
High-level editor interface that communicates with underlying editor (like
Espresso, Coda, etc.) or browser. Basically, you should call set_context(obj) 
method to set up undelying editor context before using any other method.

This interface is used by zen_actions.py for performing different
actions like Expand abbreviation

@example
import zen_editor
zen_editor.set_context(obj);
//now you are ready to use editor object
zen_editor.get_selection_range();

@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru

Gedit implementation:
@author Franck Marcia (franck.marcia@gmail.com)
'''

import zen_core, zen_actions
import os, re, locale
import zen_dialog

class ZenEditor():

    def __init__(self):
        self.last_wrap = ''
        self.last_expand = ''
        zen_core.set_caret_placeholder('')

    def set_context(self, context):
        """
        Setup underlying editor context. You should call this method before 
        using any Zen Coding action.
        @param context: context object
        """
        self.context = context # window
        self.buffer = self.context.get_active_view().get_buffer()
        self.view = context.get_active_view()
        self.document = context.get_active_document()
        
        default_locale = locale.getdefaultlocale()[0] if locale.getdefaultlocale()[0] else "en_US"
        lang = re.sub(r'_[^_]+$', '', default_locale)
        if lang != default_locale:
            zen_core.set_variable('lang', lang)
            zen_core.set_variable('locale', default_locale.replace('_', '-'))
        else:
            zen_core.set_variable('lang', default_locale)
            zen_core.set_variable('locale', default_locale)
        
        self.encoding = self.document.get_encoding().get_charset()
        zen_core.set_variable('charset', self.encoding)
        
        if self.view.get_insert_spaces_instead_of_tabs():
            zen_core.set_variable('indentation', " " * context.get_active_view().get_tab_width())
        else:
            zen_core.set_variable('indentation', "\t")
        
    def get_selection_range(self):
        """
        Returns character indexes of selected text
        @return: list of start and end indexes
        @example
        start, end = zen_editor.get_selection_range();
        print('%s, %s' % (start, end))
        """
        offset_start = self.get_insert_offset()
        offset_end = self.get_selection_bound_offset()
        if offset_start < offset_end:
            return offset_start, offset_end
        return offset_end, offset_start


    def create_selection(self, offset_start, offset_end=None):
        """
        Creates selection from start to end character indexes. If end is 
        omitted, this method should place caret and start index.
        @type start: int
        @type end: int
        @example
        zen_editor.create_selection(10, 40)
        # move caret to 15th character
        zen_editor.create_selection(15)
        """
        if offset_end is None:
            iter_start = self.buffer.get_iter_at_offset(offset_start)
            self.buffer.place_cursor(iter_start)
        else:
            iter_start = self.buffer.get_iter_at_offset(offset_start)
            iter_end = self.buffer.get_iter_at_offset(offset_end)
            self.buffer.select_range(iter_start, iter_end)

    def get_current_line_range(self):
        """
        Returns current line's start and end indexes
        @return: list of start and end indexes
        @example
        start, end = zen_editor.get_current_line_range();
        print('%s, %s' % (start, end))
        """
        iter_current = self.get_insert_iter()
        offset_start = self.buffer.get_iter_at_line(iter_current.get_line()).get_offset()
        offset_end = offset_start + iter_current.get_chars_in_line() - 1
        return offset_start, offset_end

    def get_caret_pos(self):
        """ Returns current caret position """
        return self.get_insert_offset()

    def set_caret_pos(self, pos):
        """
        Sets the new caret position
        @type pos: int
        """
        self.buffer.place_cursor(self.buffer.get_iter_at_offset(pos))

    def get_current_line(self):
        """
        Returns content of current line
        @return: str
        """
        offset_start, offset_end = self.get_current_line_range()
        iter_start = self.buffer.get_iter_at_offset(offset_start)
        iter_end = self.buffer.get_iter_at_offset(offset_end)
        return self.buffer.get_text(iter_start, iter_end).decode(self.encoding)

    def replace_content(self, value, offset_start=None, offset_end=None):
        """
        Replace editor's content or its part (from start to end index). If 
        value contains caret_placeholder, the editor will put caret into
        this position. If you skip start and end arguments, the whole target's 
        content will be replaced with value.

        If you pass start argument only, the value will be placed at start 
        string index of current content.

        If you pass start and end arguments, the corresponding substring of 
        current target's content will be replaced with value
        @param value: Content you want to paste
        @type value: str
        @param start: Start index of editor's content
        @type start: int
        @param end: End index of editor's content
        @type end: int
        """
        if offset_start is None and offset_end is None:
            iter_start = self.buffer.get_iter_at_offset(0)
            iter_end = self.get_end_iter()
        elif offset_end is None:
            iter_start = self.buffer.get_iter_at_offset(offset_start)
            iter_end = self.buffer.get_iter_at_offset(offset_start)
        else:
            iter_start = self.buffer.get_iter_at_offset(offset_start)
            iter_end = self.buffer.get_iter_at_offset(offset_end)

        self.buffer.delete(iter_start, iter_end)
        self.insertion_start = self.get_insert_offset()
        
        padding = zen_actions.get_current_line_padding(self)
        self.buffer.insert_at_cursor(zen_core.pad_string(value, padding))

        self.insertion_end = self.get_insert_offset()

    def get_content(self):
        """
        Returns editor's content
        @return: str
        """
        iter_start = self.buffer.get_iter_at_offset(0)
        iter_end = self.get_end_iter()
        return self.buffer.get_text(iter_start, iter_end).decode(self.encoding)

    def get_syntax(self):
        """
        Returns current editor's syntax mode
        @return: str
        """
        lang = self.context.get_active_document().get_language()
        lang = lang and lang.get_name()
        if lang == 'CSS': lang = 'css'
        elif lang == 'XSLT': lang = 'xsl'
        else: lang = 'html'
        return lang

    def get_profile_name(self):
        """
        Returns current output profile name (@see zen_coding#setup_profile)
        @return {String}
        """
        return 'xhtml'

    def get_insert_iter(self):
        return self.buffer.get_iter_at_mark(self.buffer.get_insert())
        
    def get_insert_offset(self):
        return self.get_insert_iter().get_offset()

    def get_selection_bound_iter(self):
        return self.buffer.get_iter_at_mark(self.buffer.get_selection_bound())

    def get_selection_bound_offset(self):
        return self.get_selection_bound_iter().get_offset()

    def get_end_iter(self):
        return self.buffer.get_iter_at_offset(self.buffer.get_char_count())

    def get_end_offset(self):
        return self.get_end_iter().get_offset()
        
    def start_edit(self):
        # Bug when the cursor is at the very beginning.
        if self.insertion_start == 0:
            self.insertion_start = 1
        self.set_caret_pos(self.insertion_start)
        if not self.next_edit_point() or (self.get_insert_offset() > self.insertion_end):
            self.set_caret_pos(self.insertion_end)
    
    def show_caret(self):
        self.view.scroll_mark_onscreen(self.buffer.get_insert())

    def get_user_settings_error(self):
        return zen_core.get_variable('user_settings_error')

    def expand_abbreviation(self, window):
        self.set_context(window)
        self.buffer.begin_user_action()
        result = zen_actions.expand_abbreviation(self)
        if result:
            self.start_edit()
        self.buffer.end_user_action()

    def save_selection(self):
        self.save_offset_insert = self.get_insert_offset()
        self.save_offset_selection_bound = self.get_selection_bound_offset()

    def restore_selection(self):
        iter_insert = self.buffer.get_iter_at_offset(self.save_offset_insert)
        iter_selection_bound = self.buffer.get_iter_at_offset(self.save_offset_selection_bound)
        self.buffer.select_range(iter_insert, iter_selection_bound)

    def do_expand_with_abbreviation(self, done, abbr):
        self.buffer.begin_user_action()
        if done:
            self.buffer.undo()
            self.restore_selection()
        content = zen_core.expand_abbreviation(abbr, self.get_syntax(), self.get_profile_name())
        if content:
            self.replace_content(content, self.get_insert_offset())
        self.buffer.end_user_action()
        return not not content

    def expand_with_abbreviation(self, window):
        self.set_context(window)
        self.save_selection()
        done, self.last_expand = zen_dialog.main(self, window, self.do_expand_with_abbreviation, self.last_expand)
        if done:
            self.start_edit()

    def do_wrap_with_abbreviation(self, done, abbr):
        self.buffer.begin_user_action()
        if done:
            self.buffer.undo()
            self.restore_selection()
        result = zen_actions.wrap_with_abbreviation(self, abbr)
        self.buffer.end_user_action()
        return result

    def wrap_with_abbreviation(self, window):
        self.set_context(window)
        self.save_selection()
        done, self.last_wrap = zen_dialog.main(self, window, self.do_wrap_with_abbreviation, self.last_wrap)
        if done:
            self.start_edit()

    def match_pair_inward(self, window):
        self.set_context(window)
        zen_actions.match_pair_inward(self)

    def match_pair_outward(self, window):
        self.set_context(window)
        zen_actions.match_pair_outward(self)

    def merge_lines(self, window):
        self.set_context(window)
        self.buffer.begin_user_action()
        result = zen_actions.merge_lines(self)
        self.buffer.end_user_action()
        return result

    def prev_edit_point(self, window=None):
        if window:
            self.set_context(window)
        result = zen_actions.prev_edit_point(self)
        self.show_caret()
        return result

    def next_edit_point(self, window=None):
        if window:
            self.set_context(window)
        result = zen_actions.next_edit_point(self)
        self.show_caret()
        return result

    def remove_tag(self, window):
        self.set_context(window)
        self.buffer.begin_user_action()
        result = zen_actions.remove_tag(self)
        self.buffer.end_user_action()
        return result

    def split_join_tag(self, window):
        self.set_context(window)
        self.buffer.begin_user_action()
        result = zen_actions.split_join_tag(self)
        self.buffer.end_user_action()
        return result

    def toggle_comment(self, window):
        self.set_context(window)
        self.buffer.begin_user_action()
        result = zen_actions.toggle_comment(self)
        self.buffer.end_user_action()
        return result

########NEW FILE########
__FILENAME__ = zen_settings
"""
Zen Coding settings
@author Sergey Chikuyonok (serge.che@gmail.com)
@link http://chikuyonok.ru
"""
zen_settings = {
			
#	Variables that can be placed inside snippets or abbreviations as ${variable}
#	${child} variable is reserved, don't use it
	'variables': {
		'lang': 'en',
		'locale': 'en-US',
		'charset': 'UTF-8',
		'profile': 'xhtml',
		
#		Inner element indentation
		'indentation': '\t'
	},
	
	# common settings are used for quick injection of user-defined snippets
	'common': {
		
	},
	
	'css': {
		'extends': 'common',
		'snippets': {
			"@i": "@import url(|);",
			"@m": "@media print {\n\t|\n}",
			"@f": "@font-face {\n\tfont-family:|;\n\tsrc:url(|);\n}",
			"!": "!important",
			"pos": "position:|;",
			"pos:s": "position:static;",
			"pos:a": "position:absolute;",
			"pos:r": "position:relative;",
			"pos:f": "position:fixed;",
			"t": "top:|;",
			"t:a": "top:auto;",
			"r": "right:|;",
			"r:a": "right:auto;",
			"b": "bottom:|;",
			"b:a": "bottom:auto;",
			"brad": "-webkit-border-radius: ${1:radius};\n-moz-border-radius: $1;\n-ms-border-radius: $1;\nborder-radius: $1;$0",
			"l": "left:|;",
			"l:a": "left:auto;",
			"z": "z-index:|;",
			"z:a": "z-index:auto;",
			"fl": "float:|;",
			"fl:n": "float:none;",
			"fl:l": "float:left;",
			"fl:r": "float:right;",
			"cl": "clear:|;",
			"cl:n": "clear:none;",
			"cl:l": "clear:left;",
			"cl:r": "clear:right;",
			"cl:b": "clear:both;",
			"d": "display:|;",
			"d:n": "display:none;",
			"d:b": "display:block;",
			"d:i": "display:inline;",
			"d:ib": "display:inline-block;",
			"d:li": "display:list-item;",
			"d:ri": "display:run-in;",
			"d:cp": "display:compact;",
			"d:tb": "display:table;",
			"d:itb": "display:inline-table;",
			"d:tbcp": "display:table-caption;",
			"d:tbcl": "display:table-column;",
			"d:tbclg": "display:table-column-group;",
			"d:tbhg": "display:table-header-group;",
			"d:tbfg": "display:table-footer-group;",
			"d:tbr": "display:table-row;",
			"d:tbrg": "display:table-row-group;",
			"d:tbc": "display:table-cell;",
			"d:rb": "display:ruby;",
			"d:rbb": "display:ruby-base;",
			"d:rbbg": "display:ruby-base-group;",
			"d:rbt": "display:ruby-text;",
			"d:rbtg": "display:ruby-text-group;",
			"v": "visibility:|;",
			"v:v": "visibility:visible;",
			"v:h": "visibility:hidden;",
			"v:c": "visibility:collapse;",
			"ov": "overflow:|;",
			"ov:v": "overflow:visible;",
			"ov:h": "overflow:hidden;",
			"ov:s": "overflow:scroll;",
			"ov:a": "overflow:auto;",
			"ovx": "overflow-x:|;",
			"ovx:v": "overflow-x:visible;",
			"ovx:h": "overflow-x:hidden;",
			"ovx:s": "overflow-x:scroll;",
			"ovx:a": "overflow-x:auto;",
			"ovy": "overflow-y:|;",
			"ovy:v": "overflow-y:visible;",
			"ovy:h": "overflow-y:hidden;",
			"ovy:s": "overflow-y:scroll;",
			"ovy:a": "overflow-y:auto;",
			"ovs": "overflow-style:|;",
			"ovs:a": "overflow-style:auto;",
			"ovs:s": "overflow-style:scrollbar;",
			"ovs:p": "overflow-style:panner;",
			"ovs:m": "overflow-style:move;",
			"ovs:mq": "overflow-style:marquee;",
			"zoo": "zoom:1;",
			"cp": "clip:|;",
			"cp:a": "clip:auto;",
			"cp:r": "clip:rect(|);",
			"bxz": "box-sizing:|;",
			"bxz:cb": "box-sizing:content-box;",
			"bxz:bb": "box-sizing:border-box;",
			"bxsh": "box-shadow:|;",
			"bxsh:n": "box-shadow:none;",
			"bxsh:w": "-webkit-box-shadow:0 0 0 #000;",
			"bxsh:m": "-moz-box-shadow:0 0 0 0 #000;",
			"m": "margin:|;",
			"m:a": "margin:auto;",
			"m:0": "margin:0;",
			"m:2": "margin:0 0;",
			"m:3": "margin:0 0 0;",
			"m:4": "margin:0 0 0 0;",
			"mt": "margin-top:|;",
			"mt:a": "margin-top:auto;",
			"mr": "margin-right:|;",
			"mr:a": "margin-right:auto;",
			"mb": "margin-bottom:|;",
			"mb:a": "margin-bottom:auto;",
			"ml": "margin-left:|;",
			"ml:a": "margin-left:auto;",
			"p": "padding:|;",
			"p:0": "padding:0;",
			"p:2": "padding:0 0;",
			"p:3": "padding:0 0 0;",
			"p:4": "padding:0 0 0 0;",
			"pt": "padding-top:|;",
			"pr": "padding-right:|;",
			"pb": "padding-bottom:|;",
			"pl": "padding-left:|;",
			"w": "width:|;",
			"w:a": "width:auto;",
			"h": "height:|;",
			"h:a": "height:auto;",
			"maw": "max-width:|;",
			"maw:n": "max-width:none;",
			"mah": "max-height:|;",
			"mah:n": "max-height:none;",
			"miw": "min-width:|;",
			"mih": "min-height:|;",
			"o": "outline:|;",
			"o:n": "outline:none;",
			"oo": "outline-offset:|;",
			"ow": "outline-width:|;",
			"os": "outline-style:|;",
			"oc": "outline-color:#000;",
			"oc:i": "outline-color:invert;",
			"bd": "border:|;",
			"bd+": "border:1px solid #000;",
			"bd:n": "border:none;",
			"bdbk": "border-break:|;",
			"bdbk:c": "border-break:close;",
			"bdcl": "border-collapse:|;",
			"bdcl:c": "border-collapse:collapse;",
			"bdcl:s": "border-collapse:separate;",
			"bdc": "border-color:#000;",
			"bdi": "border-image:url(|);",
			"bdi:n": "border-image:none;",
			"bdi:w": "-webkit-border-image:url(|) 0 0 0 0 stretch stretch;",
			"bdi:m": "-moz-border-image:url(|) 0 0 0 0 stretch stretch;",
			"bdti": "border-top-image:url(|);",
			"bdti:n": "border-top-image:none;",
			"bdri": "border-right-image:url(|);",
			"bdri:n": "border-right-image:none;",
			"bdbi": "border-bottom-image:url(|);",
			"bdbi:n": "border-bottom-image:none;",
			"bdli": "border-left-image:url(|);",
			"bdli:n": "border-left-image:none;",
			"bdci": "border-corner-image:url(|);",
			"bdci:n": "border-corner-image:none;",
			"bdci:c": "border-corner-image:continue;",
			"bdtli": "border-top-left-image:url(|);",
			"bdtli:n": "border-top-left-image:none;",
			"bdtli:c": "border-top-left-image:continue;",
			"bdtri": "border-top-right-image:url(|);",
			"bdtri:n": "border-top-right-image:none;",
			"bdtri:c": "border-top-right-image:continue;",
			"bdbri": "border-bottom-right-image:url(|);",
			"bdbri:n": "border-bottom-right-image:none;",
			"bdbri:c": "border-bottom-right-image:continue;",
			"bdbli": "border-bottom-left-image:url(|);",
			"bdbli:n": "border-bottom-left-image:none;",
			"bdbli:c": "border-bottom-left-image:continue;",
			"bdf": "border-fit:|;",
			"bdf:c": "border-fit:clip;",
			"bdf:r": "border-fit:repeat;",
			"bdf:sc": "border-fit:scale;",
			"bdf:st": "border-fit:stretch;",
			"bdf:ow": "border-fit:overwrite;",
			"bdf:of": "border-fit:overflow;",
			"bdf:sp": "border-fit:space;",
			"bdl": "border-length:|;",
			"bdl:a": "border-length:auto;",
			"bdsp": "border-spacing:|;",
			"bds": "border-style:|;",
			"bds:n": "border-style:none;",
			"bds:h": "border-style:hidden;",
			"bds:dt": "border-style:dotted;",
			"bds:ds": "border-style:dashed;",
			"bds:s": "border-style:solid;",
			"bds:db": "border-style:double;",
			"bds:dtds": "border-style:dot-dash;",
			"bds:dtdtds": "border-style:dot-dot-dash;",
			"bds:w": "border-style:wave;",
			"bds:g": "border-style:groove;",
			"bds:r": "border-style:ridge;",
			"bds:i": "border-style:inset;",
			"bds:o": "border-style:outset;",
			"bdw": "border-width:|;",
			"bdt": "border-top:|;",
			"bdt+": "border-top:1px solid #000;",
			"bdt:n": "border-top:none;",
			"bdtw": "border-top-width:|;",
			"bdts": "border-top-style:|;",
			"bdts:n": "border-top-style:none;",
			"bdtc": "border-top-color:#000;",
			"bdr": "border-right:|;",
			"bdr+": "border-right:1px solid #000;",
			"bdr:n": "border-right:none;",
			"bdrw": "border-right-width:|;",
			"bdrs": "border-right-style:|;",
			"bdrs:n": "border-right-style:none;",
			"bdrc": "border-right-color:#000;",
			"bdb": "border-bottom:|;",
			"bdb+": "border-bottom:1px solid #000;",
			"bdb:n": "border-bottom:none;",
			"bdbw": "border-bottom-width:|;",
			"bdbs": "border-bottom-style:|;",
			"bdbs:n": "border-bottom-style:none;",
			"bdbc": "border-bottom-color:#000;",
			"bdl": "border-left:|;",
			"bdl+": "border-left:1px solid #000;",
			"bdl:n": "border-left:none;",
			"bdlw": "border-left-width:|;",
			"bdls": "border-left-style:|;",
			"bdls:n": "border-left-style:none;",
			"bdlc": "border-left-color:#000;",
			"bdrs": "border-radius:|;",
			"bdtrrs": "border-top-right-radius:|;",
			"bdtlrs": "border-top-left-radius:|;",
			"bdbrrs": "border-bottom-right-radius:|;",
			"bdblrs": "border-bottom-left-radius:|;",
			"bg": "background:|;",
			"bg+": "background:#FFF url(|) 0 0 no-repeat;",
			"bg:n": "background:none;",
			"bg:ie": "filter:progid:DXImageTransform.Microsoft.AlphaImageLoader(src='|x.png');",
			"bgc": "background-color:#FFF;",
			"bgi": "background-image:url(|);",
			"bgi:n": "background-image:none;",
			"bgr": "background-repeat:|;",
			"bgr:n": "background-repeat:no-repeat;",
			"bgr:x": "background-repeat:repeat-x;",
			"bgr:y": "background-repeat:repeat-y;",
			"bga": "background-attachment:|;",
			"bga:f": "background-attachment:fixed;",
			"bga:s": "background-attachment:scroll;",
			"bgp": "background-position:0 0;",
			"bgpx": "background-position-x:|;",
			"bgpy": "background-position-y:|;",
			"bgbk": "background-break:|;",
			"bgbk:bb": "background-break:bounding-box;",
			"bgbk:eb": "background-break:each-box;",
			"bgbk:c": "background-break:continuous;",
			"bgcp": "background-clip:|;",
			"bgcp:bb": "background-clip:border-box;",
			"bgcp:pb": "background-clip:padding-box;",
			"bgcp:cb": "background-clip:content-box;",
			"bgcp:nc": "background-clip:no-clip;",
			"bgo": "background-origin:|;",
			"bgo:pb": "background-origin:padding-box;",
			"bgo:bb": "background-origin:border-box;",
			"bgo:cb": "background-origin:content-box;",
			"bgz": "background-size:|;",
			"bgz:a": "background-size:auto;",
			"bgz:ct": "background-size:contain;",
			"bgz:cv": "background-size:cover;",
			"c": "color:#000;",
			"tbl": "table-layout:|;",
			"tbl:a": "table-layout:auto;",
			"tbl:f": "table-layout:fixed;",
			"cps": "caption-side:|;",
			"cps:t": "caption-side:top;",
			"cps:b": "caption-side:bottom;",
			"ec": "empty-cells:|;",
			"ec:s": "empty-cells:show;",
			"ec:h": "empty-cells:hide;",
			"lis": "list-style:|;",
			"lis:n": "list-style:none;",
			"lisp": "list-style-position:|;",
			"lisp:i": "list-style-position:inside;",
			"lisp:o": "list-style-position:outside;",
			"list": "list-style-type:|;",
			"list:n": "list-style-type:none;",
			"list:d": "list-style-type:disc;",
			"list:c": "list-style-type:circle;",
			"list:s": "list-style-type:square;",
			"list:dc": "list-style-type:decimal;",
			"list:dclz": "list-style-type:decimal-leading-zero;",
			"list:lr": "list-style-type:lower-roman;",
			"list:ur": "list-style-type:upper-roman;",
			"lisi": "list-style-image:|;",
			"lisi:n": "list-style-image:none;",
			"q": "quotes:|;",
			"q:n": "quotes:none;",
			"q:ru": "quotes:'\00AB' '\00BB' '\201E' '\201C';",
			"q:en": "quotes:'\201C' '\201D' '\2018' '\2019';",
			"ct": "content:|;",
			"ct:n": "content:normal;",
			"ct:oq": "content:open-quote;",
			"ct:noq": "content:no-open-quote;",
			"ct:cq": "content:close-quote;",
			"ct:ncq": "content:no-close-quote;",
			"ct:a": "content:attr(|);",
			"ct:c": "content:counter(|);",
			"ct:cs": "content:counters(|);",
			"coi": "counter-increment:|;",
			"cor": "counter-reset:|;",
			"va": "vertical-align:|;",
			"va:sup": "vertical-align:super;",
			"va:t": "vertical-align:top;",
			"va:tt": "vertical-align:text-top;",
			"va:m": "vertical-align:middle;",
			"va:bl": "vertical-align:baseline;",
			"va:b": "vertical-align:bottom;",
			"va:tb": "vertical-align:text-bottom;",
			"va:sub": "vertical-align:sub;",
			"ta": "text-align:|;",
			"ta:l": "text-align:left;",
			"ta:c": "text-align:center;",
			"ta:r": "text-align:right;",
			"tal": "text-align-last:|;",
			"tal:a": "text-align-last:auto;",
			"tal:l": "text-align-last:left;",
			"tal:c": "text-align-last:center;",
			"tal:r": "text-align-last:right;",
			"td": "text-decoration:|;",
			"td:n": "text-decoration:none;",
			"td:u": "text-decoration:underline;",
			"td:o": "text-decoration:overline;",
			"td:l": "text-decoration:line-through;",
			"te": "text-emphasis:|;",
			"te:n": "text-emphasis:none;",
			"te:ac": "text-emphasis:accent;",
			"te:dt": "text-emphasis:dot;",
			"te:c": "text-emphasis:circle;",
			"te:ds": "text-emphasis:disc;",
			"te:b": "text-emphasis:before;",
			"te:a": "text-emphasis:after;",
			"th": "text-height:|;",
			"th:a": "text-height:auto;",
			"th:f": "text-height:font-size;",
			"th:t": "text-height:text-size;",
			"th:m": "text-height:max-size;",
			"ti": "text-indent:|;",
			"ti:-": "text-indent:-9999px;",
			"tj": "text-justify:|;",
			"tj:a": "text-justify:auto;",
			"tj:iw": "text-justify:inter-word;",
			"tj:ii": "text-justify:inter-ideograph;",
			"tj:ic": "text-justify:inter-cluster;",
			"tj:d": "text-justify:distribute;",
			"tj:k": "text-justify:kashida;",
			"tj:t": "text-justify:tibetan;",
			"to": "text-outline:|;",
			"to+": "text-outline:0 0 #000;",
			"to:n": "text-outline:none;",
			"tr": "text-replace:|;",
			"tr:n": "text-replace:none;",
			"tt": "text-transform:|;",
			"tt:n": "text-transform:none;",
			"tt:c": "text-transform:capitalize;",
			"tt:u": "text-transform:uppercase;",
			"tt:l": "text-transform:lowercase;",
			"tw": "text-wrap:|;",
			"tw:n": "text-wrap:normal;",
			"tw:no": "text-wrap:none;",
			"tw:u": "text-wrap:unrestricted;",
			"tw:s": "text-wrap:suppress;",
			"tsh": "text-shadow:|;",
			"tsh+": "text-shadow:0 0 0 #000;",
			"tsh:n": "text-shadow:none;",
			"lh": "line-height:|;",
			"whs": "white-space:|;",
			"whs:n": "white-space:normal;",
			"whs:p": "white-space:pre;",
			"whs:nw": "white-space:nowrap;",
			"whs:pw": "white-space:pre-wrap;",
			"whs:pl": "white-space:pre-line;",
			"whsc": "white-space-collapse:|;",
			"whsc:n": "white-space-collapse:normal;",
			"whsc:k": "white-space-collapse:keep-all;",
			"whsc:l": "white-space-collapse:loose;",
			"whsc:bs": "white-space-collapse:break-strict;",
			"whsc:ba": "white-space-collapse:break-all;",
			"wob": "word-break:|;",
			"wob:n": "word-break:normal;",
			"wob:k": "word-break:keep-all;",
			"wob:l": "word-break:loose;",
			"wob:bs": "word-break:break-strict;",
			"wob:ba": "word-break:break-all;",
			"wos": "word-spacing:|;",
			"wow": "word-wrap:|;",
			"wow:nm": "word-wrap:normal;",
			"wow:n": "word-wrap:none;",
			"wow:u": "word-wrap:unrestricted;",
			"wow:s": "word-wrap:suppress;",
			"lts": "letter-spacing:|;",
			"f": "font:|;",
			"f+": "font:1em Arial,sans-serif;",
			"fw": "font-weight:|;",
			"fw:n": "font-weight:normal;",
			"fw:b": "font-weight:bold;",
			"fw:br": "font-weight:bolder;",
			"fw:lr": "font-weight:lighter;",
			"fs": "font-style:|;",
			"fs:n": "font-style:normal;",
			"fs:i": "font-style:italic;",
			"fs:o": "font-style:oblique;",
			"fv": "font-variant:|;",
			"fv:n": "font-variant:normal;",
			"fv:sc": "font-variant:small-caps;",
			"fz": "font-size:|;",
			"fza": "font-size-adjust:|;",
			"fza:n": "font-size-adjust:none;",
			"ff": "font-family:|;",
			"ff:s": "font-family:serif;",
			"ff:ss": "font-family:sans-serif;",
			"ff:c": "font-family:cursive;",
			"ff:f": "font-family:fantasy;",
			"ff:m": "font-family:monospace;",
			"fef": "font-effect:|;",
			"fef:n": "font-effect:none;",
			"fef:eg": "font-effect:engrave;",
			"fef:eb": "font-effect:emboss;",
			"fef:o": "font-effect:outline;",
			"fem": "font-emphasize:|;",
			"femp": "font-emphasize-position:|;",
			"femp:b": "font-emphasize-position:before;",
			"femp:a": "font-emphasize-position:after;",
			"fems": "font-emphasize-style:|;",
			"fems:n": "font-emphasize-style:none;",
			"fems:ac": "font-emphasize-style:accent;",
			"fems:dt": "font-emphasize-style:dot;",
			"fems:c": "font-emphasize-style:circle;",
			"fems:ds": "font-emphasize-style:disc;",
			"fsm": "font-smooth:|;",
			"fsm:a": "font-smooth:auto;",
			"fsm:n": "font-smooth:never;",
			"fsm:aw": "font-smooth:always;",
			"fst": "font-stretch:|;",
			"fst:n": "font-stretch:normal;",
			"fst:uc": "font-stretch:ultra-condensed;",
			"fst:ec": "font-stretch:extra-condensed;",
			"fst:c": "font-stretch:condensed;",
			"fst:sc": "font-stretch:semi-condensed;",
			"fst:se": "font-stretch:semi-expanded;",
			"fst:e": "font-stretch:expanded;",
			"fst:ee": "font-stretch:extra-expanded;",
			"fst:ue": "font-stretch:ultra-expanded;",
			"op": "opacity:|;",
			"op:ie": "filter:progid:DXImageTransform.Microsoft.Alpha(Opacity=100);",
			"op:ms": "-ms-filter:'progid:DXImageTransform.Microsoft.Alpha(Opacity=100)';",
			"rz": "resize:|;",
			"rz:n": "resize:none;",
			"rz:b": "resize:both;",
			"rz:h": "resize:horizontal;",
			"rz:v": "resize:vertical;",
			"cur": "cursor:|;",
			"cur:a": "cursor:auto;",
			"cur:d": "cursor:default;",
			"cur:c": "cursor:crosshair;",
			"cur:ha": "cursor:hand;",
			"cur:he": "cursor:help;",
			"cur:m": "cursor:move;",
			"cur:p": "cursor:pointer;",
			"cur:t": "cursor:text;",
			"pgbb": "page-break-before:|;",
			"pgbb:au": "page-break-before:auto;",
			"pgbb:al": "page-break-before:always;",
			"pgbb:l": "page-break-before:left;",
			"pgbb:r": "page-break-before:right;",
			"pgbi": "page-break-inside:|;",
			"pgbi:au": "page-break-inside:auto;",
			"pgbi:av": "page-break-inside:avoid;",
			"pgba": "page-break-after:|;",
			"pgba:au": "page-break-after:auto;",
			"pgba:al": "page-break-after:always;",
			"pgba:l": "page-break-after:left;",
			"pgba:r": "page-break-after:right;",
			"orp": "orphans:|;",
			"wid": "widows:|;"
		}
	},
	
	'html': {
		'extends': 'common',
		'filters': 'html',
		'snippets': {
			'cc:ie6': '<!--[if lte IE 6]>\n\t${child}|\n<![endif]-->',
			'cc:ie': '<!--[if IE]>\n\t${child}|\n<![endif]-->',
			'cc:noie': '<!--[if !IE]><!-->\n\t${child}|\n<!--<![endif]-->',
			'html:4t': '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">\n' +
					'<html lang="${lang}">\n' +
					'<head>\n' +
					'${indentation}<meta http-equiv="Content-Type" content="text/html;charset=${charset}">\n' +
					'${indentation}<title></title>\n' +
					'</head>\n' +
					'<body>\n\t${child}|\n</body>\n' +
					'</html>',
			
			'html:4s': '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">\n' +
					'<html lang="${lang}">\n' +
					'<head>\n' +
					'${indentation}<meta http-equiv="Content-Type" content="text/html;charset=${charset}">\n' +
					'${indentation}<title></title>\n' +
					'</head>\n' +
					'<body>\n\t${child}|\n</body>\n' +
					'</html>',
			
			'html:xt': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n' +
					'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="${lang}">\n' +
					'<head>\n' +
					'${indentation}<meta http-equiv="Content-Type" content="text/html;charset=${charset}" />\n' +
					'${indentation}<title></title>\n' +
					'</head>\n' +
					'<body>\n\t${child}|\n</body>\n' +
					'</html>',
			
			'html:xs': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n' +
					'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="${lang}">\n' +
					'<head>\n' +
					'${indentation}<meta http-equiv="Content-Type" content="text/html;charset=${charset}" />\n' +
					'${indentation}<title></title>\n' +
					'</head>\n' +
					'<body>\n\t${child}|\n</body>\n' +
					'</html>',
			
			'html:xxs': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n' +
					'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="${lang}">\n' +
					'<head>\n' +
					'${indentation}<meta http-equiv="Content-Type" content="text/html;charset=${charset}" />\n' +
					'${indentation}<title></title>\n' +
					'</head>\n' +
					'<body>\n\t${child}|\n</body>\n' +
					'</html>',
			
			'html:5': '<!DOCTYPE HTML>\n' +
					'<html lang="${locale}">\n' +
					'<head>\n' +
					'${indentation}<meta charset="${charset}">\n' +
					'${indentation}<title></title>\n' +
					'</head>\n' +
					'<body>\n\t${child}|\n</body>\n' +
					'</html>'
		},
		
		'abbreviations': {
			'a': '<a href=""></a>',
			'a:link': '<a href="http://|"></a>',
			'a:mail': '<a href="mailto:|"></a>',
			'abbr': '<abbr title=""></abbr>',
			'acronym': '<acronym title=""></acronym>',
			'base': '<base href="" />',
			'bdo': '<bdo dir=""></bdo>',
			'bdo:r': '<bdo dir="rtl"></bdo>',
			'bdo:l': '<bdo dir="ltr"></bdo>',
			'link:css': '<link rel="stylesheet" type="text/css" href="|style.css" media="all" />',
			'link:print': '<link rel="stylesheet" type="text/css" href="|print.css" media="print" />',
			'link:favicon': '<link rel="shortcut icon" type="image/x-icon" href="|favicon.ico" />',
			'link:touch': '<link rel="apple-touch-icon" href="|favicon.png" />',
			'link:rss': '<link rel="alternate" type="application/rss+xml" title="RSS" href="|rss.xml" />',
			'link:atom': '<link rel="alternate" type="application/atom+xml" title="Atom" href="atom.xml" />',
			'meta:utf': '<meta http-equiv="Content-Type" content="text/html;charset=UTF-8" />',
			'meta:win': '<meta http-equiv="Content-Type" content="text/html;charset=Win-1251" />',
			'meta:compat': '<meta http-equiv="X-UA-Compatible" content="IE=7" />',
			'style': '<style type="text/css"></style>',
			'script': '<script type="text/javascript"></script>',
			'script:src': '<script type="text/javascript" src=""></script>',
			'img': '<img src="" alt="" />',
			'iframe': '<iframe src="" frameborder="0"></iframe>',
			'embed': '<embed src="" type="" />',
			'object': '<object data="" type=""></object>',
			'param': '<param name="" value="" />',
			'map': '<map name=""></map>',
			'area': '<area shape="" coords="" href="" alt="" />',
			'area:d': '<area shape="default" href="" alt="" />',
			'area:c': '<area shape="circle" coords="" href="" alt="" />',
			'area:r': '<area shape="rect" coords="" href="" alt="" />',
			'area:p': '<area shape="poly" coords="" href="" alt="" />',
			'link': '<link rel="stylesheet" href="" />',
			'form': '<form action=""></form>',
			'form:get': '<form action="" method="get"></form>',
			'form:post': '<form action="" method="post"></form>',
			'label': '<label for=""></label>',
			'input': '<input type="" />',
			'input:hidden': '<input type="hidden" name="" />',
			'input:h': '<input type="hidden" name="" />',
			'input:text': '<input type="text" name="" id="" />',
			'input:t': '<input type="text" name="" id="" />',
			'input:search': '<input type="search" name="" id="" />',
			'input:email': '<input type="email" name="" id="" />',
			'input:url': '<input type="url" name="" id="" />',
			'input:password': '<input type="password" name="" id="" />',
			'input:p': '<input type="password" name="" id="" />',
			'input:datetime': '<input type="datetime" name="" id="" />',
			'input:date': '<input type="date" name="" id="" />',
			'input:datetime-local': '<input type="datetime-local" name="" id="" />',
			'input:month': '<input type="month" name="" id="" />',
			'input:week': '<input type="week" name="" id="" />',
			'input:time': '<input type="time" name="" id="" />',
			'input:number': '<input type="number" name="" id="" />',
			'input:color': '<input type="color" name="" id="" />',
			'input:checkbox': '<input type="checkbox" name="" id="" />',
			'input:c': '<input type="checkbox" name="" id="" />',
			'input:radio': '<input type="radio" name="" id="" />',
			'input:r': '<input type="radio" name="" id="" />',
			'input:range': '<input type="range" name="" id="" />',
			'input:file': '<input type="file" name="" id="" />',
			'input:f': '<input type="file" name="" id="" />',
			'input:submit': '<input type="submit" value="" />',
			'input:s': '<input type="submit" value="" />',
			'input:image': '<input type="image" src="" alt="" />',
			'input:i': '<input type="image" src="" alt="" />',
			'input:reset': '<input type="reset" value="" />',
			'input:button': '<input type="button" value="" />',
			'input:b': '<input type="button" value="" />',
			'select': '<select name="" id=""></select>',
			'option': '<option value=""></option>',
			'textarea': '<textarea name="" id="" cols="30" rows="10"></textarea>',
			'menu:context': '<menu type="context"></menu>',
			'menu:c': '<menu type="context"></menu>',
			'menu:toolbar': '<menu type="toolbar"></menu>',
			'menu:t': '<menu type="toolbar"></menu>',
			'video': '<video src=""></video>',
			'audio': '<audio src=""></audio>',
			'html:xml': '<html xmlns="http://www.w3.org/1999/xhtml"></html>',
			'bq': '<blockquote></blockquote>',
			'acr': '<acronym></acronym>',
			'fig': '<figure></figure>',
			'ifr': '<iframe></iframe>',
			'emb': '<embed></embed>',
			'obj': '<object></object>',
			'src': '<source></source>',
			'cap': '<caption></caption>',
			'colg': '<colgroup></colgroup>',
			'fst': '<fieldset></fieldset>',
			'btn': '<button></button>',
			'optg': '<optgroup></optgroup>',
			'opt': '<option></option>',
			'tarea': '<textarea></textarea>',
			'leg': '<legend></legend>',
			'sect': '<section></section>',
			'art': '<article></article>',
			'hdr': '<header></header>',
			'ftr': '<footer></footer>',
			'adr': '<address></address>',
			'dlg': '<dialog></dialog>',
			'str': '<strong></strong>',
			'prog': '<progress></progress>',
			'fset': '<fieldset></fieldset>',
			'datag': '<datagrid></datagrid>',
			'datal': '<datalist></datalist>',
			'kg': '<keygen></keygen>',
			'out': '<output></output>',
			'det': '<details></details>',
			'cmd': '<command></command>',
			
#			expandos
			'ol+': 'ol>li',
			'ul+': 'ul>li',
			'dl+': 'dl>dt+dd',
			'map+': 'map>area',
			'table+': 'table>tr>td',
			'colgroup+': 'colgroup>col',
			'colg+': 'colgroup>col',
			'tr+': 'tr>td',
			'select+': 'select>option',
			'optgroup+': 'optgroup>option',
			'optg+': 'optgroup>option'

		},
		
		'element_types': {
			'empty': 'area,base,basefont,br,col,frame,hr,img,input,isindex,link,meta,param,embed,keygen,command',
			'block_level': 'address,applet,blockquote,button,center,dd,del,dir,div,dl,dt,fieldset,form,frameset,hr,iframe,ins,isindex,li,link,map,menu,noframes,noscript,object,ol,p,pre,script,table,tbody,td,tfoot,th,thead,tr,ul,h1,h2,h3,h4,h5,h6',
			'inline_level': 'a,abbr,acronym,applet,b,basefont,bdo,big,br,button,cite,code,del,dfn,em,font,i,iframe,img,input,ins,kbd,label,map,object,q,s,samp,script,select,small,span,strike,strong,sub,sup,textarea,tt,u,var'
		}
	},
	
	'xsl': {
		'extends': 'common,html',
		'filters': 'html, xsl',
		'abbreviations': {
			'tm': '<xsl:template match="" mode=""></xsl:template>',
			'tmatch': 'tm',
			'tn': '<xsl:template name=""></xsl:template>',
			'tname': 'tn',
			'xsl:when': '<xsl:when test=""></xsl:when>',
			'wh': 'xsl:when',
			'var': '<xsl:variable name="">|</xsl:variable>',
			'vare': '<xsl:variable name="" select=""/>',
			'if': '<xsl:if test=""></xsl:if>',
			'call': '<xsl:call-template name=""/>',
			'attr': '<xsl:attribute name=""></xsl:attribute>',
			'wp': '<xsl:with-param name="" select=""/>',
			'par': '<xsl:param name="" select=""/>',
			'val': '<xsl:value-of select=""/>',
			'co': '<xsl:copy-of select=""/>',
			'each': '<xsl:for-each select=""></xsl:for-each>',
			'ap': '<xsl:apply-templates select="" mode=""/>',
			
#			expandos
			'choose+': 'xsl:choose>xsl:when+xsl:otherwise'
		}
	},
	
	'haml': {
		'filters': 'haml',
		'extends': 'html'
	}
}

########NEW FILE########
