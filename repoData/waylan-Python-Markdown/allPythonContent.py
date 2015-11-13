__FILENAME__ = blockparser
from __future__ import unicode_literals
from __future__ import absolute_import
from . import util
from . import odict

class State(list):
    """ Track the current and nested state of the parser. 
    
    This utility class is used to track the state of the BlockParser and 
    support multiple levels if nesting. It's just a simple API wrapped around
    a list. Each time a state is set, that state is appended to the end of the
    list. Each time a state is reset, that state is removed from the end of
    the list.

    Therefore, each time a state is set for a nested block, that state must be 
    reset when we back out of that level of nesting or the state could be
    corrupted.

    While all the methods of a list object are available, only the three
    defined below need be used.

    """

    def set(self, state):
        """ Set a new state. """
        self.append(state)

    def reset(self):
        """ Step back one step in nested state. """
        self.pop()

    def isstate(self, state):
        """ Test that top (current) level is of given state. """
        if len(self):
            return self[-1] == state
        else:
            return False

class BlockParser:
    """ Parse Markdown blocks into an ElementTree object. 
    
    A wrapper class that stitches the various BlockProcessors together,
    looping through them and creating an ElementTree object.
    """

    def __init__(self, markdown):
        self.blockprocessors = odict.OrderedDict()
        self.state = State()
        self.markdown = markdown

    def parseDocument(self, lines):
        """ Parse a markdown document into an ElementTree. 
        
        Given a list of lines, an ElementTree object (not just a parent Element)
        is created and the root element is passed to the parser as the parent.
        The ElementTree object is returned.
        
        This should only be called on an entire document, not pieces.

        """
        # Create a ElementTree from the lines
        self.root = util.etree.Element(self.markdown.doc_tag)
        self.parseChunk(self.root, '\n'.join(lines))
        return util.etree.ElementTree(self.root)

    def parseChunk(self, parent, text):
        """ Parse a chunk of markdown text and attach to given etree node. 
        
        While the ``text`` argument is generally assumed to contain multiple
        blocks which will be split on blank lines, it could contain only one
        block. Generally, this method would be called by extensions when
        block parsing is required. 
        
        The ``parent`` etree Element passed in is altered in place. 
        Nothing is returned.

        """
        self.parseBlocks(parent, text.split('\n\n'))

    def parseBlocks(self, parent, blocks):
        """ Process blocks of markdown text and attach to given etree node. 
        
        Given a list of ``blocks``, each blockprocessor is stepped through
        until there are no blocks left. While an extension could potentially
        call this method directly, it's generally expected to be used internally.

        This is a public method as an extension may need to add/alter additional
        BlockProcessors which call this method to recursively parse a nested
        block.

        """
        while blocks:
            for processor in self.blockprocessors.values():
                if processor.test(parent, blocks[0]):
                    if processor.run(parent, blocks) is not False:
                        # run returns True or None
                        break



########NEW FILE########
__FILENAME__ = blockprocessors
"""
CORE MARKDOWN BLOCKPARSER
===========================================================================

This parser handles basic parsing of Markdown blocks.  It doesn't concern itself
with inline elements such as **bold** or *italics*, but rather just catches
blocks, lists, quotes, etc.

The BlockParser is made up of a bunch of BlockProssors, each handling a
different type of block. Extensions may add/replace/remove BlockProcessors
as they need to alter how markdown blocks are parsed.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
import logging
import re
from . import util
from .blockparser import BlockParser

logger =  logging.getLogger('MARKDOWN')


def build_block_parser(md_instance, **kwargs):
    """ Build the default block parser used by Markdown. """
    parser = BlockParser(md_instance)
    parser.blockprocessors['empty'] = EmptyBlockProcessor(parser)
    parser.blockprocessors['indent'] = ListIndentProcessor(parser)
    parser.blockprocessors['code'] = CodeBlockProcessor(parser)
    parser.blockprocessors['hashheader'] = HashHeaderProcessor(parser)
    parser.blockprocessors['setextheader'] = SetextHeaderProcessor(parser)
    parser.blockprocessors['hr'] = HRProcessor(parser)
    parser.blockprocessors['olist'] = OListProcessor(parser)
    parser.blockprocessors['ulist'] = UListProcessor(parser)
    parser.blockprocessors['quote'] = BlockQuoteProcessor(parser)
    parser.blockprocessors['paragraph'] = ParagraphProcessor(parser)
    return parser


class BlockProcessor:
    """ Base class for block processors. 
    
    Each subclass will provide the methods below to work with the source and
    tree. Each processor will need to define it's own ``test`` and ``run``
    methods. The ``test`` method should return True or False, to indicate
    whether the current block should be processed by this processor. If the
    test passes, the parser will call the processors ``run`` method.

    """

    def __init__(self, parser):
        self.parser = parser
        self.tab_length = parser.markdown.tab_length

    def lastChild(self, parent):
        """ Return the last child of an etree element. """
        if len(parent):
            return parent[-1]
        else:
            return None

    def detab(self, text):
        """ Remove a tab from the front of each line of the given text. """
        newtext = []
        lines = text.split('\n')
        for line in lines:
            if line.startswith(' '*self.tab_length):
                newtext.append(line[self.tab_length:])
            elif not line.strip():
                newtext.append('')
            else:
                break
        return '\n'.join(newtext), '\n'.join(lines[len(newtext):])

    def looseDetab(self, text, level=1):
        """ Remove a tab from front of lines but allowing dedented lines. """
        lines = text.split('\n')
        for i in range(len(lines)):
            if lines[i].startswith(' '*self.tab_length*level):
                lines[i] = lines[i][self.tab_length*level:]
        return '\n'.join(lines)

    def test(self, parent, block):
        """ Test for block type. Must be overridden by subclasses. 
        
        As the parser loops through processors, it will call the ``test`` method
        on each to determine if the given block of text is of that type. This
        method must return a boolean ``True`` or ``False``. The actual method of
        testing is left to the needs of that particular block type. It could 
        be as simple as ``block.startswith(some_string)`` or a complex regular
        expression. As the block type may be different depending on the parent
        of the block (i.e. inside a list), the parent etree element is also 
        provided and may be used as part of the test.

        Keywords:
        
        * ``parent``: A etree element which will be the parent of the block.
        * ``block``: A block of text from the source which has been split at 
            blank lines.
        """
        pass

    def run(self, parent, blocks):
        """ Run processor. Must be overridden by subclasses. 
        
        When the parser determines the appropriate type of a block, the parser
        will call the corresponding processor's ``run`` method. This method
        should parse the individual lines of the block and append them to
        the etree. 

        Note that both the ``parent`` and ``etree`` keywords are pointers
        to instances of the objects which should be edited in place. Each
        processor must make changes to the existing objects as there is no
        mechanism to return new/different objects to replace them.

        This means that this method should be adding SubElements or adding text
        to the parent, and should remove (``pop``) or add (``insert``) items to
        the list of blocks.

        Keywords:

        * ``parent``: A etree element which is the parent of the current block.
        * ``blocks``: A list of all remaining blocks of the document.
        """
        pass


class ListIndentProcessor(BlockProcessor):
    """ Process children of list items. 
    
    Example:
        * a list item
            process this part

            or this part

    """

    ITEM_TYPES = ['li']
    LIST_TYPES = ['ul', 'ol']

    def __init__(self, *args):
        BlockProcessor.__init__(self, *args)
        self.INDENT_RE = re.compile(r'^(([ ]{%s})+)'% self.tab_length)

    def test(self, parent, block):
        return block.startswith(' '*self.tab_length) and \
                not self.parser.state.isstate('detabbed') and  \
                (parent.tag in self.ITEM_TYPES or \
                    (len(parent) and parent[-1] and \
                        (parent[-1].tag in self.LIST_TYPES)
                    )
                )

    def run(self, parent, blocks):
        block = blocks.pop(0)
        level, sibling = self.get_level(parent, block)
        block = self.looseDetab(block, level)

        self.parser.state.set('detabbed')
        if parent.tag in self.ITEM_TYPES:
            # It's possible that this parent has a 'ul' or 'ol' child list
            # with a member.  If that is the case, then that should be the
            # parent.  This is intended to catch the edge case of an indented 
            # list whose first member was parsed previous to this point
            # see OListProcessor
            if len(parent) and parent[-1].tag in self.LIST_TYPES:
                self.parser.parseBlocks(parent[-1], [block])
            else:
                # The parent is already a li. Just parse the child block.
                self.parser.parseBlocks(parent, [block])
        elif sibling.tag in self.ITEM_TYPES:
            # The sibling is a li. Use it as parent.
            self.parser.parseBlocks(sibling, [block])
        elif len(sibling) and sibling[-1].tag in self.ITEM_TYPES:
            # The parent is a list (``ol`` or ``ul``) which has children.
            # Assume the last child li is the parent of this block.
            if sibling[-1].text:
                # If the parent li has text, that text needs to be moved to a p
                # The p must be 'inserted' at beginning of list in the event
                # that other children already exist i.e.; a nested sublist.
                p = util.etree.Element('p')
                p.text = sibling[-1].text
                sibling[-1].text = ''
                sibling[-1].insert(0, p)
            self.parser.parseChunk(sibling[-1], block)
        else:
            self.create_item(sibling, block)
        self.parser.state.reset()

    def create_item(self, parent, block):
        """ Create a new li and parse the block with it as the parent. """
        li = util.etree.SubElement(parent, 'li')
        self.parser.parseBlocks(li, [block])
 
    def get_level(self, parent, block):
        """ Get level of indent based on list level. """
        # Get indent level
        m = self.INDENT_RE.match(block)
        if m:
            indent_level = len(m.group(1))/self.tab_length
        else:
            indent_level = 0
        if self.parser.state.isstate('list'):
            # We're in a tightlist - so we already are at correct parent.
            level = 1
        else:
            # We're in a looselist - so we need to find parent.
            level = 0
        # Step through children of tree to find matching indent level.
        while indent_level > level:
            child = self.lastChild(parent)
            if child is not None and (child.tag in self.LIST_TYPES or child.tag in self.ITEM_TYPES):
                if child.tag in self.LIST_TYPES:
                    level += 1
                parent = child
            else:
                # No more child levels. If we're short of indent_level,
                # we have a code block. So we stop here.
                break
        return level, parent


class CodeBlockProcessor(BlockProcessor):
    """ Process code blocks. """

    def test(self, parent, block):
        return block.startswith(' '*self.tab_length)
    
    def run(self, parent, blocks):
        sibling = self.lastChild(parent)
        block = blocks.pop(0)
        theRest = ''
        if sibling is not None and sibling.tag == "pre" and len(sibling) \
                    and sibling[0].tag == "code":
            # The previous block was a code block. As blank lines do not start
            # new code blocks, append this block to the previous, adding back
            # linebreaks removed from the split into a list.
            code = sibling[0]
            block, theRest = self.detab(block)
            code.text = util.AtomicString('%s\n%s\n' % (code.text, block.rstrip()))
        else:
            # This is a new codeblock. Create the elements and insert text.
            pre = util.etree.SubElement(parent, 'pre')
            code = util.etree.SubElement(pre, 'code')
            block, theRest = self.detab(block)
            code.text = util.AtomicString('%s\n' % block.rstrip())
        if theRest:
            # This block contained unindented line(s) after the first indented 
            # line. Insert these lines as the first block of the master blocks
            # list for future processing.
            blocks.insert(0, theRest)


class BlockQuoteProcessor(BlockProcessor):

    RE = re.compile(r'(^|\n)[ ]{0,3}>[ ]?(.*)')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            before = block[:m.start()] # Lines before blockquote
            # Pass lines before blockquote in recursively for parsing forst.
            self.parser.parseBlocks(parent, [before])
            # Remove ``> `` from begining of each line.
            block = '\n'.join([self.clean(line) for line in 
                            block[m.start():].split('\n')])
        sibling = self.lastChild(parent)
        if sibling is not None and sibling.tag == "blockquote":
            # Previous block was a blockquote so set that as this blocks parent
            quote = sibling
        else:
            # This is a new blockquote. Create a new parent element.
            quote = util.etree.SubElement(parent, 'blockquote')
        # Recursively parse block with blockquote as parent.
        # change parser state so blockquotes embedded in lists use p tags
        self.parser.state.set('blockquote')
        self.parser.parseChunk(quote, block)
        self.parser.state.reset()

    def clean(self, line):
        """ Remove ``>`` from beginning of a line. """
        m = self.RE.match(line)
        if line.strip() == ">":
            return ""
        elif m:
            return m.group(2)
        else:
            return line

class OListProcessor(BlockProcessor):
    """ Process ordered list blocks. """

    TAG = 'ol'
    # Detect an item (``1. item``). ``group(1)`` contains contents of item.
    RE = re.compile(r'^[ ]{0,3}\d+\.[ ]+(.*)')
    # Detect items on secondary lines. they can be of either list type.
    CHILD_RE = re.compile(r'^[ ]{0,3}((\d+\.)|[*+-])[ ]+(.*)')
    # Detect indented (nested) items of either type
    INDENT_RE = re.compile(r'^[ ]{4,7}((\d+\.)|[*+-])[ ]+.*')
    # The integer (python string) with which the lists starts (default=1)
    # Eg: If list is intialized as)
    #   3. Item
    # The ol tag will get starts="3" attribute
    STARTSWITH = '1'
    # List of allowed sibling tags. 
    SIBLING_TAGS = ['ol', 'ul']

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        # Check fr multiple items in one block.
        items = self.get_items(blocks.pop(0))
        sibling = self.lastChild(parent)

        if sibling is not None and sibling.tag in self.SIBLING_TAGS:
            # Previous block was a list item, so set that as parent
            lst = sibling
            # make sure previous item is in a p- if the item has text, then it
            # it isn't in a p
            if lst[-1].text: 
                # since it's possible there are other children for this sibling,
                # we can't just SubElement the p, we need to insert it as the 
                # first item
                p = util.etree.Element('p')
                p.text = lst[-1].text
                lst[-1].text = ''
                lst[-1].insert(0, p)
            # if the last item has a tail, then the tail needs to be put in a p
            # likely only when a header is not followed by a blank line
            lch = self.lastChild(lst[-1])
            if lch is not None and lch.tail:
                p = util.etree.SubElement(lst[-1], 'p')
                p.text = lch.tail.lstrip()
                lch.tail = ''

            # parse first block differently as it gets wrapped in a p.
            li = util.etree.SubElement(lst, 'li')
            self.parser.state.set('looselist')
            firstitem = items.pop(0)
            self.parser.parseBlocks(li, [firstitem])
            self.parser.state.reset()
        elif parent.tag in ['ol', 'ul']:
            # this catches the edge case of a multi-item indented list whose 
            # first item is in a blank parent-list item:
            # * * subitem1
            #     * subitem2
            # see also ListIndentProcessor
            lst = parent
        else:
            # This is a new list so create parent with appropriate tag.
            lst = util.etree.SubElement(parent, self.TAG)
            # Check if a custom start integer is set
            if not self.parser.markdown.lazy_ol and self.STARTSWITH !='1':
                lst.attrib['start'] = self.STARTSWITH

        self.parser.state.set('list')
        # Loop through items in block, recursively parsing each with the
        # appropriate parent.
        for item in items:
            if item.startswith(' '*self.tab_length):
                # Item is indented. Parse with last item as parent
                self.parser.parseBlocks(lst[-1], [item])
            else:
                # New item. Create li and parse with it as parent
                li = util.etree.SubElement(lst, 'li')
                self.parser.parseBlocks(li, [item])
        self.parser.state.reset()

    def get_items(self, block):
        """ Break a block into list items. """
        items = []
        for line in block.split('\n'):
            m = self.CHILD_RE.match(line)
            if m:
                # This is a new list item
                # Check first item for the start index
                if not items and self.TAG=='ol':
                    # Detect the integer value of first list item
                    INTEGER_RE = re.compile('(\d+)')
                    self.STARTSWITH = INTEGER_RE.match(m.group(1)).group()
                # Append to the list
                items.append(m.group(3))
            elif self.INDENT_RE.match(line):
                # This is an indented (possibly nested) item.
                if items[-1].startswith(' '*self.tab_length):
                    # Previous item was indented. Append to that item.
                    items[-1] = '%s\n%s' % (items[-1], line)
                else:
                    items.append(line)
            else:
                # This is another line of previous item. Append to that item.
                items[-1] = '%s\n%s' % (items[-1], line)
        return items


class UListProcessor(OListProcessor):
    """ Process unordered list blocks. """

    TAG = 'ul'
    RE = re.compile(r'^[ ]{0,3}[*+-][ ]+(.*)')


class HashHeaderProcessor(BlockProcessor):
    """ Process Hash Headers. """

    # Detect a header at start of any line in block
    RE = re.compile(r'(^|\n)(?P<level>#{1,6})(?P<header>.*?)#*(\n|$)')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            before = block[:m.start()] # All lines before header
            after = block[m.end():]    # All lines after header
            if before:
                # As the header was not the first line of the block and the
                # lines before the header must be parsed first,
                # recursively parse this lines as a block.
                self.parser.parseBlocks(parent, [before])
            # Create header using named groups from RE
            h = util.etree.SubElement(parent, 'h%d' % len(m.group('level')))
            h.text = m.group('header').strip()
            if after:
                # Insert remaining lines as first block for future parsing.
                blocks.insert(0, after)
        else:
            # This should never happen, but just in case...
            logger.warn("We've got a problem header: %r" % block)


class SetextHeaderProcessor(BlockProcessor):
    """ Process Setext-style Headers. """

    # Detect Setext-style header. Must be first 2 lines of block.
    RE = re.compile(r'^.*?\n[=-]+[ ]*(\n|$)', re.MULTILINE)

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        lines = blocks.pop(0).split('\n')
        # Determine level. ``=`` is 1 and ``-`` is 2.
        if lines[1].startswith('='):
            level = 1
        else:
            level = 2
        h = util.etree.SubElement(parent, 'h%d' % level)
        h.text = lines[0].strip()
        if len(lines) > 2:
            # Block contains additional lines. Add to  master blocks for later.
            blocks.insert(0, '\n'.join(lines[2:]))


class HRProcessor(BlockProcessor):
    """ Process Horizontal Rules. """

    RE = r'^[ ]{0,3}((-+[ ]{0,2}){3,}|(_+[ ]{0,2}){3,}|(\*+[ ]{0,2}){3,})[ ]*'
    # Detect hr on any line of a block.
    SEARCH_RE = re.compile(RE, re.MULTILINE)

    def test(self, parent, block):
        m = self.SEARCH_RE.search(block)
        # No atomic grouping in python so we simulate it here for performance.
        # The regex only matches what would be in the atomic group - the HR.
        # Then check if we are at end of block or if next char is a newline.
        if m and (m.end() == len(block) or block[m.end()] == '\n'):
            # Save match object on class instance so we can use it later.
            self.match = m
            return True
        return False

    def run(self, parent, blocks):
        block = blocks.pop(0)
        # Check for lines in block before hr.
        prelines = block[:self.match.start()].rstrip('\n')
        if prelines:
            # Recursively parse lines before hr so they get parsed first.
            self.parser.parseBlocks(parent, [prelines])
        # create hr
        util.etree.SubElement(parent, 'hr')
        # check for lines in block after hr.
        postlines = block[self.match.end():].lstrip('\n')
        if postlines:
            # Add lines after hr to master blocks for later parsing.
            blocks.insert(0, postlines)



class EmptyBlockProcessor(BlockProcessor):
    """ Process blocks that are empty or start with an empty line. """

    def test(self, parent, block):
        return not block or block.startswith('\n')

    def run(self, parent, blocks):
        block = blocks.pop(0)
        filler = '\n\n'
        if block:
            # Starts with empty line
            # Only replace a single line.
            filler = '\n'
            # Save the rest for later.
            theRest = block[1:]
            if theRest:
                # Add remaining lines to master blocks for later.
                blocks.insert(0, theRest)
        sibling = self.lastChild(parent)
        if sibling is not None and sibling.tag == 'pre' and len(sibling) and sibling[0].tag == 'code':
            # Last block is a codeblock. Append to preserve whitespace.
            sibling[0].text = util.AtomicString('%s%s' % (sibling[0].text, filler))


class ParagraphProcessor(BlockProcessor):
    """ Process Paragraph blocks. """

    def test(self, parent, block):
        return True

    def run(self, parent, blocks):
        block = blocks.pop(0)
        if block.strip():
            # Not a blank block. Add to parent, otherwise throw it away.
            if self.parser.state.isstate('list'):
                # The parent is a tight-list.
                #
                # Check for any children. This will likely only happen in a 
                # tight-list when a header isn't followed by a blank line.
                # For example:
                #
                #     * # Header
                #     Line 2 of list item - not part of header.
                sibling = self.lastChild(parent)
                if sibling is not None:
                    # Insetrt after sibling.
                    if sibling.tail:
                        sibling.tail = '%s\n%s' % (sibling.tail, block)
                    else:
                        sibling.tail = '\n%s' % block
                else:
                    # Append to parent.text
                    if parent.text:
                        parent.text = '%s\n%s' % (parent.text, block)
                    else:
                        parent.text = block.lstrip()
            else:
                # Create a regular paragraph
                p = util.etree.SubElement(parent, 'p')
                p.text = block.lstrip()

########NEW FILE########
__FILENAME__ = abbr
'''
Abbreviation Extension for Python-Markdown
==========================================

This extension adds abbreviation handling to Python-Markdown.

Simple Usage:

    >>> import markdown
    >>> text = """
    ... Some text with an ABBR and a REF. Ignore REFERENCE and ref.
    ...
    ... *[ABBR]: Abbreviation
    ... *[REF]: Abbreviation Reference
    ... """
    >>> print markdown.markdown(text, ['abbr'])
    <p>Some text with an <abbr title="Abbreviation">ABBR</abbr> and a <abbr title="Abbreviation Reference">REF</abbr>. Ignore REFERENCE and ref.</p>

Copyright 2007-2008
* [Waylan Limberg](http://achinghead.com/)
* [Seemant Kulleen](http://www.kulleen.org/)
	

'''

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..preprocessors import Preprocessor
from ..inlinepatterns import Pattern
from ..util import etree, AtomicString
import re

# Global Vars
ABBR_REF_RE = re.compile(r'[*]\[(?P<abbr>[^\]]*)\][ ]?:\s*(?P<title>.*)')

class AbbrExtension(Extension):
    """ Abbreviation Extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Insert AbbrPreprocessor before ReferencePreprocessor. """
        md.preprocessors.add('abbr', AbbrPreprocessor(md), '<reference')
        
           
class AbbrPreprocessor(Preprocessor):
    """ Abbreviation Preprocessor - parse text for abbr references. """

    def run(self, lines):
        '''
        Find and remove all Abbreviation references from the text.
        Each reference is set as a new AbbrPattern in the markdown instance.
        
        '''
        new_text = []
        for line in lines:
            m = ABBR_REF_RE.match(line)
            if m:
                abbr = m.group('abbr').strip()
                title = m.group('title').strip()
                self.markdown.inlinePatterns['abbr-%s'%abbr] = \
                    AbbrPattern(self._generate_pattern(abbr), title)
            else:
                new_text.append(line)
        return new_text
    
    def _generate_pattern(self, text):
        '''
        Given a string, returns an regex pattern to match that string. 
        
        'HTML' -> r'(?P<abbr>[H][T][M][L])' 
        
        Note: we force each char as a literal match (in brackets) as we don't 
        know what they will be beforehand.

        '''
        chars = list(text)
        for i in range(len(chars)):
            chars[i] = r'[%s]' % chars[i]
        return r'(?P<abbr>\b%s\b)' % (r''.join(chars))


class AbbrPattern(Pattern):
    """ Abbreviation inline pattern. """

    def __init__(self, pattern, title):
        super(AbbrPattern, self).__init__(pattern)
        self.title = title

    def handleMatch(self, m):
        abbr = etree.Element('abbr')
        abbr.text = AtomicString(m.group('abbr'))
        abbr.set('title', self.title)
        return abbr

def makeExtension(configs=None):
    return AbbrExtension(configs=configs)

########NEW FILE########
__FILENAME__ = admonition
"""
Admonition extension for Python-Markdown
========================================

Adds rST-style admonitions. Inspired by [rST][] feature with the same name.

The syntax is (followed by an indented block with the contents):
    !!! [type] [optional explicit title]

Where `type` is used as a CSS class name of the div. If not present, `title`
defaults to the capitalized `type`, so "note" -> "Note".

rST suggests the following `types`, but you're free to use whatever you want:
    attention, caution, danger, error, hint, important, note, tip, warning


A simple example:
    !!! note
        This is the first line inside the box.

Outputs:
    <div class="admonition note">
    <p class="admonition-title">Note</p>
    <p>This is the first line inside the box</p>
    </div>

You can also specify the title and CSS class of the admonition:
    !!! custom "Did you know?"
        Another line here.

Outputs:
    <div class="admonition custom">
    <p class="admonition-title">Did you know?</p>
    <p>Another line here.</p>
    </div>

[rST]: http://docutils.sourceforge.net/docs/ref/rst/directives.html#specific-admonitions

By [Tiago Serafim](http://www.tiagoserafim.com/).

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..blockprocessors import BlockProcessor
from ..util import etree
import re


class AdmonitionExtension(Extension):
    """ Admonition extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add Admonition to Markdown instance. """
        md.registerExtension(self)

        md.parser.blockprocessors.add('admonition',
                                      AdmonitionProcessor(md.parser),
                                      '_begin')


class AdmonitionProcessor(BlockProcessor):

    CLASSNAME = 'admonition'
    CLASSNAME_TITLE = 'admonition-title'
    RE = re.compile(r'(?:^|\n)!!!\ ?([\w\-]+)(?:\ "(.*?)")?')

    def test(self, parent, block):
        sibling = self.lastChild(parent)
        return self.RE.search(block) or \
            (block.startswith(' ' * self.tab_length) and sibling and \
                sibling.get('class', '').find(self.CLASSNAME) != -1)

    def run(self, parent, blocks):
        sibling = self.lastChild(parent)
        block = blocks.pop(0)
        m = self.RE.search(block)

        if m:
            block = block[m.end() + 1:]  # removes the first line

        block, theRest = self.detab(block)

        if m:
            klass, title = self.get_class_and_title(m)
            div = etree.SubElement(parent, 'div')
            div.set('class', '%s %s' % (self.CLASSNAME, klass))
            if title:
                p = etree.SubElement(div, 'p')
                p.text = title
                p.set('class', self.CLASSNAME_TITLE)
        else:
            div = sibling

        self.parser.parseChunk(div, block)

        if theRest:
            # This block contained unindented line(s) after the first indented
            # line. Insert these lines as the first block of the master blocks
            # list for future processing.
            blocks.insert(0, theRest)

    def get_class_and_title(self, match):
        klass, title = match.group(1).lower(), match.group(2)
        if title is None:
            # no title was provided, use the capitalized classname as title
            # e.g.: `!!! note` will render `<p class="admonition-title">Note</p>`
            title = klass.capitalize()
        elif title == '':
            # an explicit blank title should not be rendered
            # e.g.: `!!! warning ""` will *not* render `p` with a title
            title = None
        return klass, title


def makeExtension(configs={}):
    return AdmonitionExtension(configs=configs)

########NEW FILE########
__FILENAME__ = attr_list
"""
Attribute List Extension for Python-Markdown
============================================

Adds attribute list syntax. Inspired by 
[maruku](http://maruku.rubyforge.org/proposal.html#attribute_lists)'s
feature of the same name.

Copyright 2011 [Waylan Limberg](http://achinghead.com/).

Contact: markdown@freewisdom.org

License: BSD (see ../LICENSE.md for details) 

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.1+](http://packages.python.org/Markdown/)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..treeprocessors import Treeprocessor
from ..util import isBlockLevel
import re

try:
    Scanner = re.Scanner
except AttributeError:
    # must be on Python 2.4
    from sre import Scanner

def _handle_double_quote(s, t):
    k, v = t.split('=')
    return k, v.strip('"')

def _handle_single_quote(s, t):
    k, v = t.split('=')
    return k, v.strip("'")

def _handle_key_value(s, t): 
    return t.split('=')

def _handle_word(s, t):
    if t.startswith('.'):
        return '.', t[1:]
    if t.startswith('#'):
        return 'id', t[1:]
    return t, t

_scanner = Scanner([
    (r'[^ ]+=".*?"', _handle_double_quote),
    (r"[^ ]+='.*?'", _handle_single_quote),
    (r'[^ ]+=[^ ]*', _handle_key_value),
    (r'[^ ]+', _handle_word),
    (r' ', None)
])

def get_attrs(str):
    """ Parse attribute list and return a list of attribute tuples. """
    return _scanner.scan(str)[0]

def isheader(elem):
    return elem.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

class AttrListTreeprocessor(Treeprocessor):
    
    BASE_RE = r'\{\:?([^\}]*)\}'
    HEADER_RE = re.compile(r'[ ]+%s[ ]*$' % BASE_RE)
    BLOCK_RE = re.compile(r'\n[ ]*%s[ ]*$' % BASE_RE)
    INLINE_RE = re.compile(r'^%s' % BASE_RE)
    NAME_RE = re.compile(r'[^A-Z_a-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u02ff\u0370-\u037d'
                         r'\u037f-\u1fff\u200c-\u200d\u2070-\u218f\u2c00-\u2fef'
                         r'\u3001-\ud7ff\uf900-\ufdcf\ufdf0-\ufffd'
                         r'\:\-\.0-9\u00b7\u0300-\u036f\u203f-\u2040]+')

    def run(self, doc):
        for elem in doc.getiterator():
            if isBlockLevel(elem.tag):
                # Block level: check for attrs on last line of text
                RE = self.BLOCK_RE
                if isheader(elem) or elem.tag == 'dt':
                    # header or def-term: check for attrs at end of line
                    RE = self.HEADER_RE
                if len(elem) and elem.tag == 'li':
                    # special case list items. children may include a ul or ol.
                    pos = None
                    # find the ul or ol position
                    for i, child in enumerate(elem):
                        if child.tag in ['ul', 'ol']:
                            pos = i
                            break
                    if pos is None and elem[-1].tail:
                        # use tail of last child. no ul or ol.
                        m = RE.search(elem[-1].tail)
                        if m:
                            self.assign_attrs(elem, m.group(1))
                            elem[-1].tail = elem[-1].tail[:m.start()]
                    elif pos is not None and pos > 0 and elem[pos-1].tail:
                        # use tail of last child before ul or ol
                        m = RE.search(elem[pos-1].tail)
                        if m:
                            self.assign_attrs(elem, m.group(1))
                            elem[pos-1].tail = elem[pos-1].tail[:m.start()]
                    elif elem.text:
                        # use text. ul is first child.
                        m = RE.search(elem.text)
                        if m:
                            self.assign_attrs(elem, m.group(1))
                            elem.text = elem.text[:m.start()]
                elif len(elem) and elem[-1].tail:
                    # has children. Get from tail of last child
                    m = RE.search(elem[-1].tail)
                    if m:
                        self.assign_attrs(elem, m.group(1))
                        elem[-1].tail = elem[-1].tail[:m.start()]
                        if isheader(elem):
                            # clean up trailing #s
                            elem[-1].tail = elem[-1].tail.rstrip('#').rstrip()
                elif elem.text:
                    # no children. Get from text.
                    m = RE.search(elem.text)
                    if not m and elem.tag == 'td':
                        m = re.search(self.BASE_RE, elem.text)
                    if m:
                        self.assign_attrs(elem, m.group(1))
                        elem.text = elem.text[:m.start()]
                        if isheader(elem):
                            # clean up trailing #s
                            elem.text = elem.text.rstrip('#').rstrip()
            else:
                # inline: check for attrs at start of tail
                if elem.tail:
                    m = self.INLINE_RE.match(elem.tail)
                    if m:
                        self.assign_attrs(elem, m.group(1))
                        elem.tail = elem.tail[m.end():]

    def assign_attrs(self, elem, attrs):
        """ Assign attrs to element. """
        for k, v in get_attrs(attrs):
            if k == '.':
                # add to class
                cls = elem.get('class')
                if cls:
                    elem.set('class', '%s %s' % (cls, v))
                else:
                    elem.set('class', v)
            else:
                # assign attr k with v
                elem.set(self.sanitize_name(k), v)

    def sanitize_name(self, name):
        """
        Sanitize name as 'an XML Name, minus the ":"'.
        See http://www.w3.org/TR/REC-xml-names/#NT-NCName
        """
        return self.NAME_RE.sub('_', name)


class AttrListExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        md.treeprocessors.add('attr_list', AttrListTreeprocessor(md), '>prettify')


def makeExtension(configs={}):
    return AttrListExtension(configs=configs)

########NEW FILE########
__FILENAME__ = codehilite
"""
CodeHilite Extension for Python-Markdown
========================================

Adds code/syntax highlighting to standard Python-Markdown code blocks.

Copyright 2006-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://packages.python.org/Markdown/extensions/code_hilite.html>
Contact: markdown@freewisdom.org

License: BSD (see ../LICENSE.md for details)

Dependencies:
* [Python 2.3+](http://python.org/)
* [Markdown 2.0+](http://packages.python.org/Markdown/)
* [Pygments](http://pygments.org/)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..treeprocessors import Treeprocessor
import warnings
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
    from pygments.formatters import HtmlFormatter
    pygments = True
except ImportError:
    pygments = False


def parse_hl_lines(expr):
    """Support our syntax for emphasizing certain lines of code.

    expr should be like '1 2' to emphasize lines 1 and 2 of a code block.
    Returns a list of ints, the line numbers to emphasize.
    """
    if not expr:
        return []

    try:
        return list(map(int, expr.split()))
    except ValueError:
        return []


# ------------------ The Main CodeHilite Class ----------------------
class CodeHilite(object):
    """
    Determine language of source code, and pass it into the pygments hilighter.

    Basic Usage:
        >>> code = CodeHilite(src = 'some text')
        >>> html = code.hilite()

    * src: Source string or any object with a .readline attribute.

    * linenums: (Boolean) Set line numbering to 'on' (True), 'off' (False) or 'auto'(None). 
    Set to 'auto' by default.

    * guess_lang: (Boolean) Turn language auto-detection 'on' or 'off' (on by default).

    * css_class: Set class name of wrapper div ('codehilite' by default).

    * hl_lines: (List of integers) Lines to emphasize, 1-indexed.

    Low Level Usage:
        >>> code = CodeHilite()
        >>> code.src = 'some text' # String or anything with a .readline attr.
        >>> code.linenos = True  # True or False; Turns line numbering on or of.
        >>> html = code.hilite()

    """

    def __init__(self, src=None, linenums=None, guess_lang=True,
                css_class="codehilite", lang=None, style='default',
                noclasses=False, tab_length=4, hl_lines=None):
        self.src = src
        self.lang = lang
        self.linenums = linenums
        self.guess_lang = guess_lang
        self.css_class = css_class
        self.style = style
        self.noclasses = noclasses
        self.tab_length = tab_length
        self.hl_lines = hl_lines or []

    def hilite(self):
        """
        Pass code to the [Pygments](http://pygments.pocoo.org/) highliter with
        optional line numbers. The output should then be styled with css to
        your liking. No styles are applied by default - only styling hooks
        (i.e.: <span class="k">).

        returns : A string of html.

        """

        self.src = self.src.strip('\n')

        if self.lang is None:
            self._parseHeader()

        if pygments:
            try:
                lexer = get_lexer_by_name(self.lang)
            except ValueError:
                try:
                    if self.guess_lang:
                        lexer = guess_lexer(self.src)
                    else:
                        lexer = TextLexer()
                except ValueError:
                    lexer = TextLexer()
            formatter = HtmlFormatter(linenos=self.linenums,
                                      cssclass=self.css_class,
                                      style=self.style,
                                      noclasses=self.noclasses,
                                      hl_lines=self.hl_lines)
            return highlight(self.src, lexer, formatter)
        else:
            # just escape and build markup usable by JS highlighting libs
            txt = self.src.replace('&', '&amp;')
            txt = txt.replace('<', '&lt;')
            txt = txt.replace('>', '&gt;')
            txt = txt.replace('"', '&quot;')
            classes = []
            if self.lang:
                classes.append('language-%s' % self.lang)
            if self.linenums:
                classes.append('linenums')
            class_str = ''
            if classes:
                class_str = ' class="%s"' % ' '.join(classes) 
            return '<pre class="%s"><code%s>%s</code></pre>\n'% \
                        (self.css_class, class_str, txt)

    def _parseHeader(self):
        """
        Determines language of a code block from shebang line and whether said
        line should be removed or left in place. If the sheband line contains a
        path (even a single /) then it is assumed to be a real shebang line and
        left alone. However, if no path is given (e.i.: #!python or :::python)
        then it is assumed to be a mock shebang for language identifitation of a
        code fragment and removed from the code block prior to processing for
        code highlighting. When a mock shebang (e.i: #!python) is found, line
        numbering is turned on. When colons are found in place of a shebang
        (e.i.: :::python), line numbering is left in the current state - off
        by default.

        Also parses optional list of highlight lines, like:

            :::python hl_lines="1 3"
        """

        import re

        #split text into lines
        lines = self.src.split("\n")
        #pull first line to examine
        fl = lines.pop(0)

        c = re.compile(r'''
            (?:(?:^::+)|(?P<shebang>^[#]!)) # Shebang or 2 or more colons
            (?P<path>(?:/\w+)*[/ ])?        # Zero or 1 path
            (?P<lang>[\w+-]*)               # The language
            \s*                             # Arbitrary whitespace
            # Optional highlight lines, single- or double-quote-delimited
            (hl_lines=(?P<quot>"|')(?P<hl_lines>.*?)(?P=quot))?
            ''',  re.VERBOSE)
        # search first line for shebang
        m = c.search(fl)
        if m:
            # we have a match
            try:
                self.lang = m.group('lang').lower()
            except IndexError:
                self.lang = None
            if m.group('path'):
                # path exists - restore first line
                lines.insert(0, fl)
            if self.linenums is None and m.group('shebang'):
                # Overridable and Shebang exists - use line numbers
                self.linenums = True

            self.hl_lines = parse_hl_lines(m.group('hl_lines'))
        else:
            # No match
            lines.insert(0, fl)

        self.src = "\n".join(lines).strip("\n")



# ------------------ The Markdown Extension -------------------------------
class HiliteTreeprocessor(Treeprocessor):
    """ Hilight source code in code blocks. """

    def run(self, root):
        """ Find code blocks and store in htmlStash. """
        blocks = root.getiterator('pre')
        for block in blocks:
            children = block.getchildren()
            if len(children) == 1 and children[0].tag == 'code':
                code = CodeHilite(children[0].text,
                            linenums=self.config['linenums'],
                            guess_lang=self.config['guess_lang'],
                            css_class=self.config['css_class'],
                            style=self.config['pygments_style'],
                            noclasses=self.config['noclasses'],
                            tab_length=self.markdown.tab_length)
                placeholder = self.markdown.htmlStash.store(code.hilite(),
                                                            safe=True)
                # Clear codeblock in etree instance
                block.clear()
                # Change to p element which will later
                # be removed when inserting raw html
                block.tag = 'p'
                block.text = placeholder


class CodeHiliteExtension(Extension):
    """ Add source code hilighting to markdown codeblocks. """

    def __init__(self, configs):
        # define default configs
        self.config = {
            'linenums': [None, "Use lines numbers. True=yes, False=no, None=auto"],
            'force_linenos' : [False, "Depreciated! Use 'linenums' instead. Force line numbers - Default: False"],
            'guess_lang' : [True, "Automatic language detection - Default: True"],
            'css_class' : ["codehilite",
                           "Set class name for wrapper <div> - Default: codehilite"],
            'pygments_style' : ['default', 'Pygments HTML Formatter Style (Colorscheme) - Default: default'],
            'noclasses': [False, 'Use inline styles instead of CSS classes - Default false']
            }

        # Override defaults with user settings
        for key, value in configs:
            # convert strings to booleans
            if value == 'True': value = True
            if value == 'False': value = False
            if value == 'None': value = None

            if key == 'force_linenos':
                warnings.warn('The "force_linenos" config setting'
                    ' to the CodeHilite extension is deprecrecated.'
                    ' Use "linenums" instead.', DeprecationWarning)
                if value:
                    # Carry 'force_linenos' over to new 'linenos'.
                    self.setConfig('linenums', True)

            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        """ Add HilitePostprocessor to Markdown instance. """
        hiliter = HiliteTreeprocessor(md)
        hiliter.config = self.getConfigs()
        md.treeprocessors.add("hilite", hiliter, "<inline")

        md.registerExtension(self)


def makeExtension(configs={}):
  return CodeHiliteExtension(configs=configs)


########NEW FILE########
__FILENAME__ = def_list
"""
Definition List Extension for Python-Markdown
=============================================

Added parsing of Definition Lists to Python-Markdown.

A simple example:

    Apple
    :   Pomaceous fruit of plants of the genus Malus in 
        the family Rosaceae.
    :   An american computer company.

    Orange
    :   The fruit of an evergreen tree of the genus Citrus.

Copyright 2008 - [Waylan Limberg](http://achinghead.com)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..blockprocessors import BlockProcessor, ListIndentProcessor
from ..util import etree
import re


class DefListProcessor(BlockProcessor):
    """ Process Definition Lists. """

    RE = re.compile(r'(^|\n)[ ]{0,3}:[ ]{1,3}(.*?)(\n|$)')
    NO_INDENT_RE = re.compile(r'^[ ]{0,3}[^ :]')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):

        raw_block = blocks.pop(0)
        m = self.RE.search(raw_block)
        terms = [l.strip() for l in raw_block[:m.start()].split('\n') if l.strip()]
        block = raw_block[m.end():]
        no_indent = self.NO_INDENT_RE.match(block)
        if no_indent:
            d, theRest = (block, None)
        else:
            d, theRest = self.detab(block)
        if d:
            d = '%s\n%s' % (m.group(2), d)
        else:
            d = m.group(2)
        sibling = self.lastChild(parent)
        if not terms and sibling is None:
            # This is not a definition item. Most likely a paragraph that 
            # starts with a colon at the begining of a document or list.
            blocks.insert(0, raw_block)
            return False
        if not terms and sibling.tag == 'p':
            # The previous paragraph contains the terms
            state = 'looselist'
            terms = sibling.text.split('\n')
            parent.remove(sibling)
            # Aquire new sibling
            sibling = self.lastChild(parent)
        else:
            state = 'list'

        if sibling and sibling.tag == 'dl':
            # This is another item on an existing list
            dl = sibling
            if not terms and len(dl) and dl[-1].tag == 'dd' and len(dl[-1]):
                state = 'looselist'
        else:
            # This is a new list
            dl = etree.SubElement(parent, 'dl')
        # Add terms
        for term in terms:
            dt = etree.SubElement(dl, 'dt')
            dt.text = term
        # Add definition
        self.parser.state.set(state)
        dd = etree.SubElement(dl, 'dd')
        self.parser.parseBlocks(dd, [d])
        self.parser.state.reset()

        if theRest:
            blocks.insert(0, theRest)

class DefListIndentProcessor(ListIndentProcessor):
    """ Process indented children of definition list items. """

    ITEM_TYPES = ['dd']
    LIST_TYPES = ['dl']

    def create_item(self, parent, block):
        """ Create a new dd and parse the block with it as the parent. """
        dd = etree.SubElement(parent, 'dd')
        self.parser.parseBlocks(dd, [block])
 


class DefListExtension(Extension):
    """ Add definition lists to Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add an instance of DefListProcessor to BlockParser. """
        md.parser.blockprocessors.add('defindent',
                                      DefListIndentProcessor(md.parser),
                                      '>indent')
        md.parser.blockprocessors.add('deflist', 
                                      DefListProcessor(md.parser),
                                      '>ulist')


def makeExtension(configs={}):
    return DefListExtension(configs=configs)


########NEW FILE########
__FILENAME__ = extra
"""
Python-Markdown Extra Extension
===============================

A compilation of various Python-Markdown extensions that imitates
[PHP Markdown Extra](http://michelf.com/projects/php-markdown/extra/).

Note that each of the individual extensions still need to be available
on your PYTHONPATH. This extension simply wraps them all up as a
convenience so that only one extension needs to be listed when
initiating Markdown. See the documentation for each individual
extension for specifics about that extension.

In the event that one or more of the supported extensions are not
available for import, Markdown will issue a warning and simply continue
without that extension.

There may be additional extensions that are distributed with
Python-Markdown that are not included here in Extra. Those extensions
are not part of PHP Markdown Extra, and therefore, not part of
Python-Markdown Extra. If you really would like Extra to include
additional extensions, we suggest creating your own clone of Extra
under a differant name. You could also edit the `extensions` global
variable defined below, but be aware that such changes may be lost
when you upgrade to any future version of Python-Markdown.

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..blockprocessors import BlockProcessor
from .. import util
import re

extensions = ['smart_strong',
              'fenced_code',
              'footnotes',
              'attr_list',
              'def_list',
              'tables',
              'abbr',
              ]


class ExtraExtension(Extension):
    """ Add various extensions to Markdown class."""

    def extendMarkdown(self, md, md_globals):
        """ Register extension instances. """
        md.registerExtensions(extensions, self.config)
        if not md.safeMode:
            # Turn on processing of markdown text within raw html
            md.preprocessors['html_block'].markdown_in_raw = True
            md.parser.blockprocessors.add('markdown_block',
                                          MarkdownInHtmlProcessor(md.parser),
                                          '_begin')
            md.parser.blockprocessors.tag_counter = -1
            md.parser.blockprocessors.contain_span_tags = re.compile(
                r'^(p|h[1-6]|li|dd|dt|td|th|legend|address)$', re.IGNORECASE)


def makeExtension(configs={}):
    return ExtraExtension(configs=dict(configs))


class MarkdownInHtmlProcessor(BlockProcessor):
    """Process Markdown Inside HTML Blocks."""
    def test(self, parent, block):
        return block == util.TAG_PLACEHOLDER % \
            str(self.parser.blockprocessors.tag_counter + 1)

    def _process_nests(self, element, block):
        """Process the element's child elements in self.run."""
        # Build list of indexes of each nest within the parent element.
        nest_index = []  # a list of tuples: (left index, right index)
        i = self.parser.blockprocessors.tag_counter + 1
        while len(self._tag_data) > i and self._tag_data[i]['left_index']:
            left_child_index = self._tag_data[i]['left_index']
            right_child_index = self._tag_data[i]['right_index']
            nest_index.append((left_child_index - 1, right_child_index))
            i += 1

        # Create each nest subelement.
        for i, (left_index, right_index) in enumerate(nest_index[:-1]):
            self.run(element, block[left_index:right_index],
                     block[right_index:nest_index[i + 1][0]], True)
        self.run(element, block[nest_index[-1][0]:nest_index[-1][1]],  # last
                 block[nest_index[-1][1]:], True)                      # nest

    def run(self, parent, blocks, tail=None, nest=False):
        self._tag_data = self.parser.markdown.htmlStash.tag_data

        self.parser.blockprocessors.tag_counter += 1
        tag = self._tag_data[self.parser.blockprocessors.tag_counter]

        # Create Element
        markdown_value = tag['attrs'].pop('markdown')
        element = util.etree.SubElement(parent, tag['tag'], tag['attrs'])

        # Slice Off Block
        if nest:
            self.parser.parseBlocks(parent, tail)  # Process Tail
            block = blocks[1:]
        else:  # includes nests since a third level of nesting isn't supported
            block = blocks[tag['left_index'] + 1: tag['right_index']]
            del blocks[:tag['right_index']]

        # Process Text
        if (self.parser.blockprocessors.contain_span_tags.match(  # Span Mode
                tag['tag']) and markdown_value != 'block') or \
                markdown_value == 'span':
            element.text = '\n'.join(block)
        else:                                                     # Block Mode
            i = self.parser.blockprocessors.tag_counter + 1
            if len(self._tag_data) > i and self._tag_data[i]['left_index']:
                first_subelement_index = self._tag_data[i]['left_index'] - 1
                self.parser.parseBlocks(
                    element, block[:first_subelement_index])
                if not nest:
                    block = self._process_nests(element, block)
            else:
                self.parser.parseBlocks(element, block)

########NEW FILE########
__FILENAME__ = fenced_code
"""
Fenced Code Extension for Python Markdown
=========================================

This extension adds Fenced Code Blocks to Python-Markdown.

    >>> import markdown
    >>> text = '''
    ... A paragraph before a fenced code block:
    ...
    ... ~~~
    ... Fenced code block
    ... ~~~
    ... '''
    >>> html = markdown.markdown(text, extensions=['fenced_code'])
    >>> print html
    <p>A paragraph before a fenced code block:</p>
    <pre><code>Fenced code block
    </code></pre>

Works with safe_mode also (we check this because we are using the HtmlStash):

    >>> print markdown.markdown(text, extensions=['fenced_code'], safe_mode='replace')
    <p>A paragraph before a fenced code block:</p>
    <pre><code>Fenced code block
    </code></pre>

Include tilde's in a code block and wrap with blank lines:

    >>> text = '''
    ... ~~~~~~~~
    ...
    ... ~~~~
    ... ~~~~~~~~'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code>
    ~~~~
    </code></pre>

Language tags:

    >>> text = '''
    ... ~~~~{.python}
    ... # Some python code
    ... ~~~~'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code class="python"># Some python code
    </code></pre>

Optionally backticks instead of tildes as per how github's code block markdown is identified:

    >>> text = '''
    ... `````
    ... # Arbitrary code
    ... ~~~~~ # these tildes will not close the block
    ... `````'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code># Arbitrary code
    ~~~~~ # these tildes will not close the block
    </code></pre>

If the codehighlite extension and Pygments are installed, lines can be highlighted:

    >>> text = '''
    ... ```hl_lines="1 3"
    ... line 1
    ... line 2
    ... line 3
    ... ```'''
    >>> print markdown.markdown(text, extensions=['codehilite', 'fenced_code'])
    <pre><code><span class="hilight">line 1</span>
    line 2
    <span class="hilight">line 3</span>
    </code></pre>

Copyright 2007-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://packages.python.org/Markdown/extensions/fenced_code_blocks.html>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details)

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.0+](http://packages.python.org/Markdown/)
* [Pygments (optional)](http://pygments.org)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..preprocessors import Preprocessor
from .codehilite import CodeHilite, CodeHiliteExtension, parse_hl_lines
import re


class FencedCodeExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        """ Add FencedBlockPreprocessor to the Markdown instance. """
        md.registerExtension(self)

        md.preprocessors.add('fenced_code_block',
                                 FencedBlockPreprocessor(md),
                                 ">normalize_whitespace")


class FencedBlockPreprocessor(Preprocessor):
    FENCED_BLOCK_RE = re.compile(r'''
(?P<fence>^(?:~{3,}|`{3,}))[ ]*         # Opening ``` or ~~~
(\{?\.?(?P<lang>[a-zA-Z0-9_+-]*))?[ ]*  # Optional {, and lang
# Optional highlight lines, single- or double-quote-delimited
(hl_lines=(?P<quot>"|')(?P<hl_lines>.*?)(?P=quot))?[ ]*
}?[ ]*\n                                # Optional closing }
(?P<code>.*?)(?<=\n)
(?P=fence)[ ]*$''', re.MULTILINE | re.DOTALL | re.VERBOSE)
    CODE_WRAP = '<pre><code%s>%s</code></pre>'
    LANG_TAG = ' class="%s"'

    def __init__(self, md):
        super(FencedBlockPreprocessor, self).__init__(md)

        self.checked_for_codehilite = False
        self.codehilite_conf = {}

    def run(self, lines):
        """ Match and store Fenced Code Blocks in the HtmlStash. """

        # Check for code hilite extension
        if not self.checked_for_codehilite:
            for ext in self.markdown.registeredExtensions:
                if isinstance(ext, CodeHiliteExtension):
                    self.codehilite_conf = ext.config
                    break

            self.checked_for_codehilite = True

        text = "\n".join(lines)
        while 1:
            m = self.FENCED_BLOCK_RE.search(text)
            if m:
                lang = ''
                if m.group('lang'):
                    lang = self.LANG_TAG % m.group('lang')

                # If config is not empty, then the codehighlite extension
                # is enabled, so we call it to highlight the code
                if self.codehilite_conf:
                    highliter = CodeHilite(m.group('code'),
                            linenums=self.codehilite_conf['linenums'][0],
                            guess_lang=self.codehilite_conf['guess_lang'][0],
                            css_class=self.codehilite_conf['css_class'][0],
                            style=self.codehilite_conf['pygments_style'][0],
                            lang=(m.group('lang') or None),
                            noclasses=self.codehilite_conf['noclasses'][0],
                            hl_lines=parse_hl_lines(m.group('hl_lines')))

                    code = highliter.hilite()
                else:
                    code = self.CODE_WRAP % (lang, self._escape(m.group('code')))

                placeholder = self.markdown.htmlStash.store(code, safe=True)
                text = '%s\n%s\n%s'% (text[:m.start()], placeholder, text[m.end():])
            else:
                break
        return text.split("\n")

    def _escape(self, txt):
        """ basic html escaping """
        txt = txt.replace('&', '&amp;')
        txt = txt.replace('<', '&lt;')
        txt = txt.replace('>', '&gt;')
        txt = txt.replace('"', '&quot;')
        return txt


def makeExtension(configs=None):
    return FencedCodeExtension(configs=configs)

########NEW FILE########
__FILENAME__ = footnotes
"""
========================= FOOTNOTES =================================

This section adds footnote handling to markdown.  It can be used as
an example for extending python-markdown with relatively complex
functionality.  While in this case the extension is included inside
the module itself, it could just as easily be added from outside the
module.  Not that all markdown classes above are ignorant about
footnotes.  All footnote functionality is provided separately and
then added to the markdown instance at the run time.

Footnote functionality is attached by calling extendMarkdown()
method of FootnoteExtension.  The method also registers the
extension to allow it's state to be reset by a call to reset()
method.

Example:
    Footnotes[^1] have a label[^label] and a definition[^!DEF].

    [^1]: This is a footnote
    [^label]: A footnote on "label"
    [^!DEF]: The footnote for definition

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..preprocessors import Preprocessor
from ..inlinepatterns import Pattern
from ..treeprocessors import Treeprocessor
from ..postprocessors import Postprocessor
from ..util import etree, text_type
from ..odict import OrderedDict
import re

FN_BACKLINK_TEXT = "zz1337820767766393qq"
NBSP_PLACEHOLDER =  "qq3936677670287331zz"
DEF_RE = re.compile(r'[ ]{0,3}\[\^([^\]]*)\]:\s*(.*)')
TABBED_RE = re.compile(r'((\t)|(    ))(.*)')

class FootnoteExtension(Extension):
    """ Footnote Extension. """

    def __init__ (self, configs):
        """ Setup configs. """
        self.config = {'PLACE_MARKER':
                       ["///Footnotes Go Here///",
                        "The text string that marks where the footnotes go"],
                       'UNIQUE_IDS':
                       [False,
                        "Avoid name collisions across "
                        "multiple calls to reset()."],
                       "BACKLINK_TEXT":
                       ["&#8617;",
                        "The text string that links from the footnote to the reader's place."]
                       }

        for key, value in configs:
            self.config[key][0] = value

        # In multiple invocations, emit links that don't get tangled.
        self.unique_prefix = 0

        self.reset()

    def extendMarkdown(self, md, md_globals):
        """ Add pieces to Markdown. """
        md.registerExtension(self)
        self.parser = md.parser
        self.md = md
        # Insert a preprocessor before ReferencePreprocessor
        md.preprocessors.add("footnote", FootnotePreprocessor(self),
                             "<reference")
        # Insert an inline pattern before ImageReferencePattern
        FOOTNOTE_RE = r'\[\^([^\]]*)\]' # blah blah [^1] blah
        md.inlinePatterns.add("footnote", FootnotePattern(FOOTNOTE_RE, self),
                              "<reference")
        # Insert a tree-processor that would actually add the footnote div
        # This must be before all other treeprocessors (i.e., inline and 
        # codehilite) so they can run on the the contents of the div.
        md.treeprocessors.add("footnote", FootnoteTreeprocessor(self),
                                 "_begin")
        # Insert a postprocessor after amp_substitute oricessor
        md.postprocessors.add("footnote", FootnotePostprocessor(self),
                                  ">amp_substitute")

    def reset(self):
        """ Clear the footnotes on reset, and prepare for a distinct document. """
        self.footnotes = OrderedDict()
        self.unique_prefix += 1

    def findFootnotesPlaceholder(self, root):
        """ Return ElementTree Element that contains Footnote placeholder. """
        def finder(element):
            for child in element:
                if child.text:
                    if child.text.find(self.getConfig("PLACE_MARKER")) > -1:
                        return child, element, True
                if child.tail:
                    if child.tail.find(self.getConfig("PLACE_MARKER")) > -1:
                        return child, element, False
                finder(child)
            return None
                
        res = finder(root)
        return res

    def setFootnote(self, id, text):
        """ Store a footnote for later retrieval. """
        self.footnotes[id] = text

    def get_separator(self):
        if self.md.output_format in ['html5', 'xhtml5']:
            return '-'
        return ':'

    def makeFootnoteId(self, id):
        """ Return footnote link id. """
        if self.getConfig("UNIQUE_IDS"):
            return 'fn%s%d-%s' % (self.get_separator(), self.unique_prefix, id)
        else:
            return 'fn%s%s' % (self.get_separator(), id)

    def makeFootnoteRefId(self, id):
        """ Return footnote back-link id. """
        if self.getConfig("UNIQUE_IDS"):
            return 'fnref%s%d-%s' % (self.get_separator(), self.unique_prefix, id)
        else:
            return 'fnref%s%s' % (self.get_separator(), id)

    def makeFootnotesDiv(self, root):
        """ Return div of footnotes as et Element. """

        if not list(self.footnotes.keys()):
            return None

        div = etree.Element("div")
        div.set('class', 'footnote')
        etree.SubElement(div, "hr")
        ol = etree.SubElement(div, "ol")

        for id in self.footnotes.keys():
            li = etree.SubElement(ol, "li")
            li.set("id", self.makeFootnoteId(id))
            self.parser.parseChunk(li, self.footnotes[id])
            backlink = etree.Element("a")
            backlink.set("href", "#" + self.makeFootnoteRefId(id))
            if self.md.output_format not in ['html5', 'xhtml5']:
                backlink.set("rev", "footnote") # Invalid in HTML5
            backlink.set("class", "footnote-backref")
            backlink.set("title", "Jump back to footnote %d in the text" % \
                            (self.footnotes.index(id)+1))
            backlink.text = FN_BACKLINK_TEXT

            if li.getchildren():
                node = li[-1]
                if node.tag == "p":
                    node.text = node.text + NBSP_PLACEHOLDER
                    node.append(backlink)
                else:
                    p = etree.SubElement(li, "p")
                    p.append(backlink)
        return div


class FootnotePreprocessor(Preprocessor):
    """ Find all footnote references and store for later use. """

    def __init__ (self, footnotes):
        self.footnotes = footnotes

    def run(self, lines):
        """
        Loop through lines and find, set, and remove footnote definitions.

        Keywords:

        * lines: A list of lines of text

        Return: A list of lines of text with footnote definitions removed.

        """
        newlines = []
        i = 0
        while True:
            m = DEF_RE.match(lines[i])
            if m:
                fn, _i = self.detectTabbed(lines[i+1:])
                fn.insert(0, m.group(2))
                i += _i-1 # skip past footnote
                self.footnotes.setFootnote(m.group(1), "\n".join(fn))
            else:
                newlines.append(lines[i])
            if len(lines) > i+1:
                i += 1
            else:
                break
        return newlines

    def detectTabbed(self, lines):
        """ Find indented text and remove indent before further proccesing.

        Keyword arguments:

        * lines: an array of strings

        Returns: a list of post processed items and the index of last line.

        """
        items = []
        blank_line = False # have we encountered a blank line yet?
        i = 0 # to keep track of where we are

        def detab(line):
            match = TABBED_RE.match(line)
            if match:
               return match.group(4)

        for line in lines:
            if line.strip(): # Non-blank line
                detabbed_line = detab(line)
                if detabbed_line:
                    items.append(detabbed_line)
                    i += 1
                    continue
                elif not blank_line and not DEF_RE.match(line):
                    # not tabbed but still part of first par.
                    items.append(line)
                    i += 1
                    continue
                else:
                    return items, i+1

            else: # Blank line: _maybe_ we are done.
                blank_line = True
                i += 1 # advance

                # Find the next non-blank line
                for j in range(i, len(lines)):
                    if lines[j].strip():
                        next_line = lines[j]; break
                else:
                    break # There is no more text; we are done.

                # Check if the next non-blank line is tabbed
                if detab(next_line): # Yes, more work to do.
                    items.append("")
                    continue
                else:
                    break # No, we are done.
        else:
            i += 1

        return items, i


class FootnotePattern(Pattern):
    """ InlinePattern for footnote markers in a document's body text. """

    def __init__(self, pattern, footnotes):
        super(FootnotePattern, self).__init__(pattern)
        self.footnotes = footnotes

    def handleMatch(self, m):
        id = m.group(2)
        if id in self.footnotes.footnotes.keys():
            sup = etree.Element("sup")
            a = etree.SubElement(sup, "a")
            sup.set('id', self.footnotes.makeFootnoteRefId(id))
            a.set('href', '#' + self.footnotes.makeFootnoteId(id))
            if self.footnotes.md.output_format not in ['html5', 'xhtml5']:
                a.set('rel', 'footnote') # invalid in HTML5
            a.set('class', 'footnote-ref')
            a.text = text_type(self.footnotes.footnotes.index(id) + 1)
            return sup
        else:
            return None


class FootnoteTreeprocessor(Treeprocessor):
    """ Build and append footnote div to end of document. """

    def __init__ (self, footnotes):
        self.footnotes = footnotes

    def run(self, root):
        footnotesDiv = self.footnotes.makeFootnotesDiv(root)
        if footnotesDiv:
            result = self.footnotes.findFootnotesPlaceholder(root)
            if result:
                child, parent, isText = result
                ind = parent.getchildren().index(child)
                if isText:
                    parent.remove(child)
                    parent.insert(ind, footnotesDiv)
                else:
                    parent.insert(ind + 1, footnotesDiv)
                    child.tail = None
            else:
                root.append(footnotesDiv)

class FootnotePostprocessor(Postprocessor):
    """ Replace placeholders with html entities. """
    def __init__(self, footnotes):
        self.footnotes = footnotes

    def run(self, text):
        text = text.replace(FN_BACKLINK_TEXT, self.footnotes.getConfig("BACKLINK_TEXT"))
        return text.replace(NBSP_PLACEHOLDER, "&#160;")

def makeExtension(configs=[]):
    """ Return an instance of the FootnoteExtension """
    return FootnoteExtension(configs=configs)


########NEW FILE########
__FILENAME__ = headerid
"""
HeaderID Extension for Python-Markdown
======================================

Auto-generate id attributes for HTML headers.

Basic usage:

    >>> import markdown
    >>> text = "# Some Header #"
    >>> md = markdown.markdown(text, ['headerid'])
    >>> print md
    <h1 id="some-header">Some Header</h1>

All header IDs are unique:

    >>> text = '''
    ... #Header
    ... #Header
    ... #Header'''
    >>> md = markdown.markdown(text, ['headerid'])
    >>> print md
    <h1 id="header">Header</h1>
    <h1 id="header_1">Header</h1>
    <h1 id="header_2">Header</h1>

To fit within a html template's hierarchy, set the header base level:

    >>> text = '''
    ... #Some Header
    ... ## Next Level'''
    >>> md = markdown.markdown(text, ['headerid(level=3)'])
    >>> print md
    <h3 id="some-header">Some Header</h3>
    <h4 id="next-level">Next Level</h4>

Works with inline markup.

    >>> text = '#Some *Header* with [markup](http://example.com).'
    >>> md = markdown.markdown(text, ['headerid'])
    >>> print md
    <h1 id="some-header-with-markup">Some <em>Header</em> with <a href="http://example.com">markup</a>.</h1>

Turn off auto generated IDs:

    >>> text = '''
    ... # Some Header
    ... # Another Header'''
    >>> md = markdown.markdown(text, ['headerid(forceid=False)'])
    >>> print md
    <h1>Some Header</h1>
    <h1>Another Header</h1>

Use with MetaData extension:

    >>> text = '''header_level: 2
    ... header_forceid: Off
    ...
    ... # A Header'''
    >>> md = markdown.markdown(text, ['headerid', 'meta'])
    >>> print md
    <h2>A Header</h2>

Copyright 2007-2011 [Waylan Limberg](http://achinghead.com/).

Project website: <http://packages.python.org/Markdown/extensions/header_id.html>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details) 

Dependencies:
* [Python 2.3+](http://python.org)
* [Markdown 2.0+](http://packages.python.org/Markdown/)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..treeprocessors import Treeprocessor
from ..util import HTML_PLACEHOLDER_RE, parseBoolValue
import re
import logging
import unicodedata

logger = logging.getLogger('MARKDOWN')

IDCOUNT_RE = re.compile(r'^(.*)_([0-9]+)$')


def slugify(value, separator):
    """ Slugify a string, to make it URL friendly. """
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = re.sub('[^\w\s-]', '', value.decode('ascii')).strip().lower()
    return re.sub('[%s\s]+' % separator, separator, value)


def unique(id, ids):
    """ Ensure id is unique in set of ids. Append '_1', '_2'... if not """
    while id in ids or not id:
        m = IDCOUNT_RE.match(id)
        if m:
            id = '%s_%d'% (m.group(1), int(m.group(2))+1)
        else:
            id = '%s_%d'% (id, 1)
    ids.add(id)
    return id


def itertext(elem):
    """ Loop through all children and return text only. 
    
    Reimplements method of same name added to ElementTree in Python 2.7
    
    """
    if elem.text:
        yield elem.text
    for e in elem:
        for s in itertext(e):
            yield s
        if e.tail:
            yield e.tail


def stashedHTML2text(text, md):
    """ Extract raw HTML, reduce to plain text and swap with placeholder. """
    def _html_sub(m):
        """ Substitute raw html with plain text. """
        try:
    	    raw, safe = md.htmlStash.rawHtmlBlocks[int(m.group(1))]
        except (IndexError, TypeError):
            return m.group(0)
        if md.safeMode and not safe:
            return ''
        # Strip out tags and entities - leaveing text
        return re.sub(r'(<[^>]+>)|(&[\#a-zA-Z0-9]+;)', '', raw)

    return HTML_PLACEHOLDER_RE.sub(_html_sub, text)


class HeaderIdTreeprocessor(Treeprocessor):
    """ Assign IDs to headers. """

    IDs = set()

    def run(self, doc):
        start_level, force_id = self._get_meta()
        slugify = self.config['slugify']
        sep = self.config['separator']
        for elem in doc.getiterator():
            if elem.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                if force_id:
                    if "id" in elem.attrib:
                        id = elem.get('id')
                    else:
                        id = stashedHTML2text(''.join(itertext(elem)), self.md)
                        id = slugify(id, sep)
                    elem.set('id', unique(id, self.IDs))
                if start_level:
                    level = int(elem.tag[-1]) + start_level
                    if level > 6:
                        level = 6
                    elem.tag = 'h%d' % level


    def _get_meta(self):
        """ Return meta data suported by this ext as a tuple """
        level = int(self.config['level']) - 1
        force = parseBoolValue(self.config['forceid'])
        if hasattr(self.md, 'Meta'):
            if 'header_level' in self.md.Meta:
                level = int(self.md.Meta['header_level'][0]) - 1
            if 'header_forceid' in self.md.Meta: 
                force = parseBoolValue(self.md.Meta['header_forceid'][0])
        return level, force


class HeaderIdExtension(Extension):
    def __init__(self, configs):
        # set defaults
        self.config = {
                'level' : ['1', 'Base level for headers.'],
                'forceid' : ['True', 'Force all headers to have an id.'],
                'separator' : ['-', 'Word separator.'],
                'slugify' : [slugify, 'Callable to generate anchors'], 
            }

        for key, value in configs:
            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        self.processor = HeaderIdTreeprocessor()
        self.processor.md = md
        self.processor.config = self.getConfigs()
        if 'attr_list' in md.treeprocessors.keys():
            # insert after attr_list treeprocessor
            md.treeprocessors.add('headerid', self.processor, '>attr_list')
        else:
            # insert after 'prettify' treeprocessor.
            md.treeprocessors.add('headerid', self.processor, '>prettify')

    def reset(self):
        self.processor.IDs = set()


def makeExtension(configs=None):
    return HeaderIdExtension(configs=configs)

########NEW FILE########
__FILENAME__ = meta
"""
Meta Data Extension for Python-Markdown
=======================================

This extension adds Meta Data handling to markdown.

Basic Usage:

    >>> import markdown
    >>> text = '''Title: A Test Doc.
    ... Author: Waylan Limberg
    ...         John Doe
    ... Blank_Data:
    ...
    ... The body. This is paragraph one.
    ... '''
    >>> md = markdown.Markdown(['meta'])
    >>> print md.convert(text)
    <p>The body. This is paragraph one.</p>
    >>> print md.Meta
    {u'blank_data': [u''], u'author': [u'Waylan Limberg', u'John Doe'], u'title': [u'A Test Doc.']}

Make sure text without Meta Data still works (markdown < 1.6b returns a <p>).

    >>> text = '    Some Code - not extra lines of meta data.'
    >>> md = markdown.Markdown(['meta'])
    >>> print md.convert(text)
    <pre><code>Some Code - not extra lines of meta data.
    </code></pre>
    >>> md.Meta
    {}

Copyright 2007-2008 [Waylan Limberg](http://achinghead.com).

Project website: <http://packages.python.org/Markdown/meta_data.html>
Contact: markdown@freewisdom.org

License: BSD (see ../LICENSE.md for details)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..preprocessors import Preprocessor
import re

# Global Vars
META_RE = re.compile(r'^[ ]{0,3}(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*)')
META_MORE_RE = re.compile(r'^[ ]{4,}(?P<value>.*)')

class MetaExtension (Extension):
    """ Meta-Data extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add MetaPreprocessor to Markdown instance. """

        md.preprocessors.add("meta", MetaPreprocessor(md), "_begin")


class MetaPreprocessor(Preprocessor):
    """ Get Meta-Data. """

    def run(self, lines):
        """ Parse Meta-Data and store in Markdown.Meta. """
        meta = {}
        key = None
        while lines:
            line = lines.pop(0)
            if line.strip() == '':
                break # blank line - done
            m1 = META_RE.match(line)
            if m1:
                key = m1.group('key').lower().strip()
                value = m1.group('value').strip()
                try:
                    meta[key].append(value)
                except KeyError:
                    meta[key] = [value]
            else:
                m2 = META_MORE_RE.match(line)
                if m2 and key:
                    # Add another line to existing key
                    meta[key].append(m2.group('value').strip())
                else:
                    lines.insert(0, line)
                    break # no meta data - done
        self.markdown.Meta = meta
        return lines
        

def makeExtension(configs={}):
    return MetaExtension(configs=configs)

########NEW FILE########
__FILENAME__ = nl2br
"""
NL2BR Extension
===============

A Python-Markdown extension to treat newlines as hard breaks; like
GitHub-flavored Markdown does.

Usage:

    >>> import markdown
    >>> print markdown.markdown('line 1\\nline 2', extensions=['nl2br'])
    <p>line 1<br />
    line 2</p>

Copyright 2011 [Brian Neal](http://deathofagremmie.com/)

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.1+](http://packages.python.org/Markdown/)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..inlinepatterns import SubstituteTagPattern

BR_RE = r'\n'

class Nl2BrExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        br_tag = SubstituteTagPattern(BR_RE, 'br')
        md.inlinePatterns.add('nl', br_tag, '_end')


def makeExtension(configs=None):
    return Nl2BrExtension(configs)

########NEW FILE########
__FILENAME__ = sane_lists
"""
Sane List Extension for Python-Markdown
=======================================

Modify the behavior of Lists in Python-Markdown t act in a sane manor.

In standard Markdown syntax, the following would constitute a single 
ordered list. However, with this extension, the output would include 
two lists, the first an ordered list and the second and unordered list.

    1. ordered
    2. list

    * unordered
    * list

Copyright 2011 - [Waylan Limberg](http://achinghead.com)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..blockprocessors import OListProcessor, UListProcessor
import re


class SaneOListProcessor(OListProcessor):
    
    CHILD_RE = re.compile(r'^[ ]{0,3}((\d+\.))[ ]+(.*)')
    SIBLING_TAGS = ['ol']


class SaneUListProcessor(UListProcessor):
    
    CHILD_RE = re.compile(r'^[ ]{0,3}(([*+-]))[ ]+(.*)')
    SIBLING_TAGS = ['ul']


class SaneListExtension(Extension):
    """ Add sane lists to Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Override existing Processors. """
        md.parser.blockprocessors['olist'] = SaneOListProcessor(md.parser)
        md.parser.blockprocessors['ulist'] = SaneUListProcessor(md.parser)


def makeExtension(configs={}):
    return SaneListExtension(configs=configs)


########NEW FILE########
__FILENAME__ = smarty
# -*- coding: utf-8 -*-
# Smarty extension for Python-Markdown
# Author: 2013, Dmitry Shachnev <mitya57@gmail.com>

# SmartyPants license:
#
#   Copyright (c) 2003 John Gruber <http://daringfireball.net/>
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are
#   met:
#
#   *  Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#   *  Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in
#      the documentation and/or other materials provided with the
#      distribution.
#
#   *  Neither the name "SmartyPants" nor the names of its contributors 
#      may be used to endorse or promote products derived from this
#      software without specific prior written permission.
#
#   This software is provided by the copyright holders and contributors "as
#   is" and any express or implied warranties, including, but not limited
#   to, the implied warranties of merchantability and fitness for a
#   particular purpose are disclaimed. In no event shall the copyright
#   owner or contributors be liable for any direct, indirect, incidental,
#   special, exemplary, or consequential damages (including, but not
#   limited to, procurement of substitute goods or services; loss of use,
#   data, or profits; or business interruption) however caused and on any
#   theory of liability, whether in contract, strict liability, or tort
#   (including negligence or otherwise) arising in any way out of the use
#   of this software, even if advised of the possibility of such damage.
#
#
# smartypants.py license:
#
#   smartypants.py is a derivative work of SmartyPants.
#   Copyright (c) 2004, 2007 Chad Miller <http://web.chad.org/>
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are
#   met:
#
#   *  Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#   *  Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in
#      the documentation and/or other materials provided with the
#      distribution.
#
#   This software is provided by the copyright holders and contributors "as
#   is" and any express or implied warranties, including, but not limited
#   to, the implied warranties of merchantability and fitness for a
#   particular purpose are disclaimed. In no event shall the copyright
#   owner or contributors be liable for any direct, indirect, incidental,
#   special, exemplary, or consequential damages (including, but not
#   limited to, procurement of substitute goods or services; loss of use,
#   data, or profits; or business interruption) however caused and on any
#   theory of liability, whether in contract, strict liability, or tort
#   (including negligence or otherwise) arising in any way out of the use
#   of this software, even if advised of the possibility of such damage.

from __future__ import unicode_literals
from . import Extension
from ..inlinepatterns import HtmlPattern
from ..odict import OrderedDict
from ..treeprocessors import InlineProcessor
from ..util import parseBoolValue

# Constants for quote education.
punctClass = r"""[!"#\$\%'()*+,-.\/:;<=>?\@\[\\\]\^_`{|}~]"""
endOfWordClass = r"[\s.,;:!?)]"
closeClass = "[^\ \t\r\n\[\{\(\-\u0002\u0003]"

openingQuotesBase = (
   '(\s'              # a  whitespace char
   '|&nbsp;'          # or a non-breaking space entity
   '|--'              # or dashes
   '|–|—'             # or unicode
   '|&[mn]dash;'      # or named dash entities
   '|&#8211;|&#8212;' # or decimal entities
   ')'
)

# Special case if the very first character is a quote
# followed by punctuation at a non-word-break. Close the quotes by brute force:
singleQuoteStartRe = r"^'(?=%s\\B)" % punctClass
doubleQuoteStartRe = r'^"(?=%s\\B)' % punctClass

# Special case for double sets of quotes, e.g.:
#   <p>He said, "'Quoted' words in a larger quote."</p>
doubleQuoteSetsRe = r""""'(?=\w)"""
singleQuoteSetsRe = r"""'"(?=\w)"""

# Get most opening double quotes:
openingDoubleQuotesRegex = r'%s"(?=\w)' % openingQuotesBase

# Double closing quotes:
closingDoubleQuotesRegex = r'"(?=\s)'
closingDoubleQuotesRegex2 = '(?<=%s)"' % closeClass

# Get most opening single quotes:
openingSingleQuotesRegex = r"%s'(?=\w)" % openingQuotesBase

# Single closing quotes:
closingSingleQuotesRegex  = r"(?<=%s)'(?!\s|s\b|\d)" % closeClass
closingSingleQuotesRegex2 = r"(?<=%s)'(\s|s\b)" % closeClass

# All remaining quotes should be opening ones
remainingSingleQuotesRegex = "'"
remainingDoubleQuotesRegex = '"'

lsquo, rsquo, ldquo, rdquo = '&lsquo;', '&rsquo;', '&ldquo;', '&rdquo;'

class SubstituteTextPattern(HtmlPattern):
    def __init__(self, pattern, replace, markdown_instance):
        """ Replaces matches with some text. """
        HtmlPattern.__init__(self, pattern)
        self.replace = replace
        self.markdown = markdown_instance

    def handleMatch(self, m):
        result = ''
        for part in self.replace:
            if isinstance(part, int):
                result += m.group(part)
            else:
                result += self.markdown.htmlStash.store(part, safe=True)
        return result

class SmartyExtension(Extension):
    def __init__(self, configs):
        self.config = {
            'smart_quotes': [True, 'Educate quotes'],
            'smart_dashes': [True, 'Educate dashes'],
            'smart_ellipses': [True, 'Educate ellipses']
        }
        for key, value in configs:
            self.setConfig(key, parseBoolValue(value))

    def _addPatterns(self, md, patterns, serie):
        for ind, pattern in enumerate(patterns):
            pattern += (md,)
            pattern = SubstituteTextPattern(*pattern)
            after = ('>smarty-%s-%d' % (serie, ind - 1) if ind else '_begin')
            name = 'smarty-%s-%d' % (serie, ind)
            self.inlinePatterns.add(name, pattern, after)

    def educateDashes(self, md):
        emDashesPattern = SubstituteTextPattern(r'(?<!-)---(?!-)', ('&mdash;',), md)
        enDashesPattern = SubstituteTextPattern(r'(?<!-)--(?!-)', ('&ndash;',), md)
        self.inlinePatterns.add('smarty-em-dashes', emDashesPattern, '_begin')
        self.inlinePatterns.add('smarty-en-dashes', enDashesPattern,
            '>smarty-em-dashes')

    def educateEllipses(self, md):
        ellipsesPattern = SubstituteTextPattern(r'(?<!\.)\.{3}(?!\.)', ('&hellip;',), md)
        self.inlinePatterns.add('smarty-ellipses', ellipsesPattern, '_begin')

    def educateQuotes(self, md):
        patterns = (
            (singleQuoteStartRe, (rsquo,)),
            (doubleQuoteStartRe, (rdquo,)),
            (doubleQuoteSetsRe, (ldquo + lsquo,)),
            (singleQuoteSetsRe, (lsquo + ldquo,)),
            (openingSingleQuotesRegex, (2, lsquo)),
            (closingSingleQuotesRegex, (rsquo,)),
            (closingSingleQuotesRegex2, (rsquo, 2)),
            (remainingSingleQuotesRegex, (lsquo,)),
            (openingDoubleQuotesRegex, (2, ldquo)),
            (closingDoubleQuotesRegex, (rdquo,)),
            (closingDoubleQuotesRegex2, (rdquo,)),
            (remainingDoubleQuotesRegex, (ldquo,))
        )
        self._addPatterns(md, patterns, 'quotes')

    def extendMarkdown(self, md, md_globals):
        configs = self.getConfigs()
        self.inlinePatterns = OrderedDict()
        if configs['smart_quotes']:
            self.educateQuotes(md)
        if configs['smart_dashes']:
            self.educateDashes(md)
        if configs['smart_ellipses']:
            self.educateEllipses(md)
        inlineProcessor = InlineProcessor(md)
        inlineProcessor.inlinePatterns = self.inlinePatterns
        md.treeprocessors.add('smarty', inlineProcessor, '_end')
        md.ESCAPED_CHARS.extend(['"', "'"])

def makeExtension(configs=None):
    return SmartyExtension(configs)

########NEW FILE########
__FILENAME__ = smart_strong
'''
Smart_Strong Extension for Python-Markdown
==========================================

This extention adds smarter handling of double underscores within words.

Simple Usage:

    >>> import markdown
    >>> print markdown.markdown('Text with double__underscore__words.',
    ...                   extensions=['smart_strong'])
    <p>Text with double__underscore__words.</p>
    >>> print markdown.markdown('__Strong__ still works.',
    ...                   extensions=['smart_strong'])
    <p><strong>Strong</strong> still works.</p>
    >>> print markdown.markdown('__this__works__too__.',
    ...                   extensions=['smart_strong'])
    <p><strong>this__works__too</strong>.</p>

Copyright 2011
[Waylan Limberg](http://achinghead.com)

'''

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..inlinepatterns import SimpleTagPattern

SMART_STRONG_RE = r'(?<!\w)(_{2})(?!_)(.+?)(?<!_)\2(?!\w)'
STRONG_RE = r'(\*{2})(.+?)\2'

class SmartEmphasisExtension(Extension):
    """ Add smart_emphasis extension to Markdown class."""

    def extendMarkdown(self, md, md_globals):
        """ Modify inline patterns. """
        md.inlinePatterns['strong'] = SimpleTagPattern(STRONG_RE, 'strong')
        md.inlinePatterns.add('strong2', SimpleTagPattern(SMART_STRONG_RE, 'strong'), '>emphasis2')

def makeExtension(configs={}):
    return SmartEmphasisExtension(configs=dict(configs))

########NEW FILE########
__FILENAME__ = tables
"""
Tables Extension for Python-Markdown
====================================

Added parsing of tables to Python-Markdown.

A simple example:

    First Header  | Second Header
    ------------- | -------------
    Content Cell  | Content Cell
    Content Cell  | Content Cell

Copyright 2009 - [Waylan Limberg](http://achinghead.com)
"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..blockprocessors import BlockProcessor
from ..util import etree

class TableProcessor(BlockProcessor):
    """ Process Tables. """

    def test(self, parent, block):
        rows = block.split('\n')
        return (len(rows) > 2 and '|' in rows[0] and 
                '|' in rows[1] and '-' in rows[1] and 
                rows[1].strip()[0] in ['|', ':', '-'])

    def run(self, parent, blocks):
        """ Parse a table block and build table. """
        block = blocks.pop(0).split('\n')
        header = block[0].strip()
        seperator = block[1].strip()
        rows = block[2:]
        # Get format type (bordered by pipes or not)
        border = False
        if header.startswith('|'):
            border = True
        # Get alignment of columns
        align = []
        for c in self._split_row(seperator, border):
            if c.startswith(':') and c.endswith(':'):
                align.append('center')
            elif c.startswith(':'):
                align.append('left')
            elif c.endswith(':'):
                align.append('right')
            else:
                align.append(None)
        # Build table
        table = etree.SubElement(parent, 'table')
        thead = etree.SubElement(table, 'thead')
        self._build_row(header, thead, align, border)
        tbody = etree.SubElement(table, 'tbody')
        for row in rows:
            self._build_row(row.strip(), tbody, align, border)

    def _build_row(self, row, parent, align, border):
        """ Given a row of text, build table cells. """
        tr = etree.SubElement(parent, 'tr')
        tag = 'td'
        if parent.tag == 'thead':
            tag = 'th'
        cells = self._split_row(row, border)
        # We use align here rather than cells to ensure every row 
        # contains the same number of columns.
        for i, a in enumerate(align):
            c = etree.SubElement(tr, tag)
            try:
                c.text = cells[i].strip()
            except IndexError:
                c.text = ""
            if a:
                c.set('align', a)

    def _split_row(self, row, border):
        """ split a row of text into list of cells. """
        if border:
            if row.startswith('|'):
                row = row[1:]
            if row.endswith('|'):
                row = row[:-1]
        return row.split('|')


class TableExtension(Extension):
    """ Add tables to Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add an instance of TableProcessor to BlockParser. """
        md.parser.blockprocessors.add('table', 
                                      TableProcessor(md.parser),
                                      '<hashheader')


def makeExtension(configs={}):
    return TableExtension(configs=configs)

########NEW FILE########
__FILENAME__ = toc
"""
Table of Contents Extension for Python-Markdown
* * *

(c) 2008 [Jack Miller](http://codezen.org)

Dependencies:
* [Markdown 2.1+](http://packages.python.org/Markdown/)

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..treeprocessors import Treeprocessor
from ..util import etree, parseBoolValue, AMP_SUBSTITUTE
from .headerid import slugify, unique, itertext, stashedHTML2text
import re


def order_toc_list(toc_list):
    """Given an unsorted list with errors and skips, return a nested one.
    [{'level': 1}, {'level': 2}]
    =>
    [{'level': 1, 'children': [{'level': 2, 'children': []}]}]
    
    A wrong list is also converted:
    [{'level': 2}, {'level': 1}]
    =>
    [{'level': 2, 'children': []}, {'level': 1, 'children': []}]
    """
    
    def build_correct(remaining_list, prev_elements=[{'level': 1000}]):
        
        if not remaining_list:
            return [], []
        
        current = remaining_list.pop(0)
        if not 'children' in current.keys():
            current['children'] = []
        
        if not prev_elements:
            # This happens for instance with [8, 1, 1], ie. when some
            # header level is outside a scope. We treat it as a
            # top-level
            next_elements, children = build_correct(remaining_list, [current])
            current['children'].append(children)
            return [current] + next_elements, []
        
        prev_element = prev_elements.pop()
        children = []
        next_elements = []
        # Is current part of the child list or next list?
        if current['level'] > prev_element['level']:
            #print "%d is a child of %d" % (current['level'], prev_element['level'])
            prev_elements.append(prev_element)
            prev_elements.append(current)
            prev_element['children'].append(current)
            next_elements2, children2 = build_correct(remaining_list, prev_elements)
            children += children2
            next_elements += next_elements2
        else:
            #print "%d is ancestor of %d" % (current['level'], prev_element['level'])
            if not prev_elements:
                #print "No previous elements, so appending to the next set"
                next_elements.append(current)
                prev_elements = [current]
                next_elements2, children2 = build_correct(remaining_list, prev_elements)
                current['children'].extend(children2)
            else:
                #print "Previous elements, comparing to those first"
                remaining_list.insert(0, current)
                next_elements2, children2 = build_correct(remaining_list, prev_elements)
                children.extend(children2)
            next_elements += next_elements2
        
        return next_elements, children
    
    ordered_list, __ = build_correct(toc_list)
    return ordered_list


class TocTreeprocessor(Treeprocessor):
    
    # Iterator wrapper to get parent and child all at once
    def iterparent(self, root):
        for parent in root.getiterator():
            for child in parent:
                yield parent, child
    
    def add_anchor(self, c, elem_id): #@ReservedAssignment
        anchor = etree.Element("a")
        anchor.text = c.text
        anchor.attrib["href"] = "#" + elem_id
        anchor.attrib["class"] = "toclink"
        c.text = ""
        for elem in c.getchildren():
            anchor.append(elem)
            c.remove(elem)
        c.append(anchor)

    def add_permalink(self, c, elem_id):
        permalink = etree.Element("a")
        permalink.text = ("%spara;" % AMP_SUBSTITUTE
            if self.use_permalinks is True else self.use_permalinks)
        permalink.attrib["href"] = "#" + elem_id
        permalink.attrib["class"] = "headerlink"
        permalink.attrib["title"] = "Permanent link"
        c.append(permalink)
    
    def build_toc_etree(self, div, toc_list):
        # Add title to the div
        if self.config["title"]:
            header = etree.SubElement(div, "span")
            header.attrib["class"] = "toctitle"
            header.text = self.config["title"]

        def build_etree_ul(toc_list, parent):
            ul = etree.SubElement(parent, "ul")
            for item in toc_list:
                # List item link, to be inserted into the toc div
                li = etree.SubElement(ul, "li")
                link = etree.SubElement(li, "a")
                link.text = item.get('name', '')
                link.attrib["href"] = '#' + item.get('id', '')
                if item['children']:
                    build_etree_ul(item['children'], li)
            return ul
        
        return build_etree_ul(toc_list, div)
        
    def run(self, doc):

        div = etree.Element("div")
        div.attrib["class"] = "toc"
        header_rgx = re.compile("[Hh][123456]")
        
        self.use_anchors = parseBoolValue(self.config["anchorlink"])
        self.use_permalinks = parseBoolValue(self.config["permalink"], False)
        if self.use_permalinks is None:
            self.use_permalinks = self.config["permalink"]
        
        # Get a list of id attributes
        used_ids = set()
        for c in doc.getiterator():
            if "id" in c.attrib:
                used_ids.add(c.attrib["id"])

        toc_list = []
        marker_found = False
        for (p, c) in self.iterparent(doc):
            text = ''.join(itertext(c)).strip()
            if not text:
                continue

            # To keep the output from screwing up the
            # validation by putting a <div> inside of a <p>
            # we actually replace the <p> in its entirety.
            # We do not allow the marker inside a header as that
            # would causes an enless loop of placing a new TOC 
            # inside previously generated TOC.
            if c.text and c.text.strip() == self.config["marker"] and \
               not header_rgx.match(c.tag) and c.tag not in ['pre', 'code']:
                for i in range(len(p)):
                    if p[i] == c:
                        p[i] = div
                        break
                marker_found = True
                            
            if header_rgx.match(c.tag):
                
                # Do not override pre-existing ids 
                if not "id" in c.attrib:
                    elem_id = stashedHTML2text(text, self.markdown)
                    elem_id = unique(self.config["slugify"](elem_id, '-'), used_ids)
                    c.attrib["id"] = elem_id
                else:
                    elem_id = c.attrib["id"]

                tag_level = int(c.tag[-1])
                
                toc_list.append({'level': tag_level,
                    'id': elem_id,
                    'name': text})

                if self.use_anchors:
                    self.add_anchor(c, elem_id)
                if self.use_permalinks:
                    self.add_permalink(c, elem_id)
                
        toc_list_nested = order_toc_list(toc_list)
        self.build_toc_etree(div, toc_list_nested)
        prettify = self.markdown.treeprocessors.get('prettify')
        if prettify: prettify.run(div)
        if not marker_found:
            # serialize and attach to markdown instance.
            toc = self.markdown.serializer(div)
            for pp in self.markdown.postprocessors.values():
                toc = pp.run(toc)
            self.markdown.toc = toc


class TocExtension(Extension):
    
    TreeProcessorClass = TocTreeprocessor
    
    def __init__(self, configs=[]):
        self.config = { "marker" : ["[TOC]", 
                            "Text to find and replace with Table of Contents -"
                            "Defaults to \"[TOC]\""],
                        "slugify" : [slugify,
                            "Function to generate anchors based on header text-"
                            "Defaults to the headerid ext's slugify function."],
                        "title" : [None,
                            "Title to insert into TOC <div> - "
                            "Defaults to None"],
                        "anchorlink" : [0,
                            "1 if header should be a self link"
                            "Defaults to 0"],
                        "permalink" : [0,
                            "1 or link text if a Sphinx-style permalink should be added",
                            "Defaults to 0"]
                       }

        for key, value in configs:
            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        tocext = self.TreeProcessorClass(md)
        tocext.config = self.getConfigs()
        # Headerid ext is set to '>prettify'. With this set to '_end',
        # it should always come after headerid ext (and honor ids assinged 
        # by the header id extension) if both are used. Same goes for 
        # attr_list extension. This must come last because we don't want
        # to redefine ids after toc is created. But we do want toc prettified.
        md.treeprocessors.add("toc", tocext, "_end")


def makeExtension(configs={}):
    return TocExtension(configs=configs)

########NEW FILE########
__FILENAME__ = wikilinks
'''
WikiLinks Extension for Python-Markdown
======================================

Converts [[WikiLinks]] to relative links.  Requires Python-Markdown 2.0+

Basic usage:

    >>> import markdown
    >>> text = "Some text with a [[WikiLink]]."
    >>> html = markdown.markdown(text, ['wikilinks'])
    >>> print html
    <p>Some text with a <a class="wikilink" href="/WikiLink/">WikiLink</a>.</p>

Whitespace behavior:

    >>> print markdown.markdown('[[ foo bar_baz ]]', ['wikilinks'])
    <p><a class="wikilink" href="/foo_bar_baz/">foo bar_baz</a></p>
    >>> print markdown.markdown('foo [[ ]] bar', ['wikilinks'])
    <p>foo  bar</p>

To define custom settings the simple way:

    >>> print markdown.markdown(text, 
    ...     ['wikilinks(base_url=/wiki/,end_url=.html,html_class=foo)']
    ... )
    <p>Some text with a <a class="foo" href="/wiki/WikiLink.html">WikiLink</a>.</p>
    
Custom settings the complex way:

    >>> md = markdown.Markdown(
    ...     extensions = ['wikilinks'], 
    ...     extension_configs = {'wikilinks': [
    ...                                 ('base_url', 'http://example.com/'), 
    ...                                 ('end_url', '.html'),
    ...                                 ('html_class', '') ]},
    ...     safe_mode = True)
    >>> print md.convert(text)
    <p>Some text with a <a href="http://example.com/WikiLink.html">WikiLink</a>.</p>

Use MetaData with mdx_meta.py (Note the blank html_class in MetaData):

    >>> text = """wiki_base_url: http://example.com/
    ... wiki_end_url:   .html
    ... wiki_html_class:
    ...
    ... Some text with a [[WikiLink]]."""
    >>> md = markdown.Markdown(extensions=['meta', 'wikilinks'])
    >>> print md.convert(text)
    <p>Some text with a <a href="http://example.com/WikiLink.html">WikiLink</a>.</p>

MetaData should not carry over to next document:

    >>> print md.convert("No [[MetaData]] here.")
    <p>No <a class="wikilink" href="/MetaData/">MetaData</a> here.</p>

Define a custom URL builder:

    >>> def my_url_builder(label, base, end):
    ...     return '/bar/'
    >>> md = markdown.Markdown(extensions=['wikilinks'], 
    ...         extension_configs={'wikilinks' : [('build_url', my_url_builder)]})
    >>> print md.convert('[[foo]]')
    <p><a class="wikilink" href="/bar/">foo</a></p>

From the command line:

    python markdown.py -x wikilinks(base_url=http://example.com/,end_url=.html,html_class=foo) src.txt

By [Waylan Limberg](http://achinghead.com/).

License: [BSD](http://www.opensource.org/licenses/bsd-license.php) 

Dependencies:
* [Python 2.3+](http://python.org)
* [Markdown 2.0+](http://packages.python.org/Markdown/)
'''

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..inlinepatterns import Pattern
from ..util import etree
import re

def build_url(label, base, end):
    """ Build a url from the label, a base, and an end. """
    clean_label = re.sub(r'([ ]+_)|(_[ ]+)|([ ]+)', '_', label)
    return '%s%s%s'% (base, clean_label, end)


class WikiLinkExtension(Extension):
    def __init__(self, configs):
        # set extension defaults
        self.config = {
                        'base_url' : ['/', 'String to append to beginning or URL.'],
                        'end_url' : ['/', 'String to append to end of URL.'],
                        'html_class' : ['wikilink', 'CSS hook. Leave blank for none.'],
                        'build_url' : [build_url, 'Callable formats URL from label.'],
        }
        configs = dict(configs) or {}
        # Override defaults with user settings
        for key, value in configs.items():
            self.setConfig(key, value)
        
    def extendMarkdown(self, md, md_globals):
        self.md = md
    
        # append to end of inline patterns
        WIKILINK_RE = r'\[\[([\w0-9_ -]+)\]\]'
        wikilinkPattern = WikiLinks(WIKILINK_RE, self.getConfigs())
        wikilinkPattern.md = md
        md.inlinePatterns.add('wikilink', wikilinkPattern, "<not_strong")


class WikiLinks(Pattern):
    def __init__(self, pattern, config):
        super(WikiLinks, self).__init__(pattern)
        self.config = config
  
    def handleMatch(self, m):
        if m.group(2).strip():
            base_url, end_url, html_class = self._getMeta()
            label = m.group(2).strip()
            url = self.config['build_url'](label, base_url, end_url)
            a = etree.Element('a')
            a.text = label 
            a.set('href', url)
            if html_class:
                a.set('class', html_class)
        else:
            a = ''
        return a

    def _getMeta(self):
        """ Return meta data or config data. """
        base_url = self.config['base_url']
        end_url = self.config['end_url']
        html_class = self.config['html_class']
        if hasattr(self.md, 'Meta'):
            if 'wiki_base_url' in self.md.Meta:
                base_url = self.md.Meta['wiki_base_url'][0]
            if 'wiki_end_url' in self.md.Meta:
                end_url = self.md.Meta['wiki_end_url'][0]
            if 'wiki_html_class' in self.md.Meta:
                html_class = self.md.Meta['wiki_html_class'][0]
        return base_url, end_url, html_class
    

def makeExtension(configs=None) :
    return WikiLinkExtension(configs=configs)

########NEW FILE########
__FILENAME__ = inlinepatterns
"""
INLINE PATTERNS
=============================================================================

Inline patterns such as *emphasis* are handled by means of auxiliary
objects, one per pattern.  Pattern objects must be instances of classes
that extend markdown.Pattern.  Each pattern object uses a single regular
expression and needs support the following methods:

    pattern.getCompiledRegExp() # returns a regular expression

    pattern.handleMatch(m) # takes a match object and returns
                           # an ElementTree element or just plain text

All of python markdown's built-in patterns subclass from Pattern,
but you can add additional patterns that don't.

Also note that all the regular expressions used by inline must
capture the whole block.  For this reason, they all start with
'^(.*)' and end with '(.*)!'.  In case with built-in expression
Pattern takes care of adding the "^(.*)" and "(.*)!".

Finally, the order in which regular expressions are applied is very
important - e.g. if we first replace http://.../ links with <a> tags
and _then_ try to replace inline html, we would end up with a mess.
So, we apply the expressions in the following order:

* escape and backticks have to go before everything else, so
  that we can preempt any markdown patterns by escaping them.

* then we handle auto-links (must be done before inline html)

* then we handle inline HTML.  At this point we will simply
  replace all inline HTML strings with a placeholder and add
  the actual HTML to a hash.

* then inline images (must be done before links)

* then bracketed links, first regular then reference-style

* finally we apply strong and emphasis
"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import util
from . import odict
import re
try:
    from urllib.parse import urlparse, urlunparse
except ImportError:
    from urlparse import urlparse, urlunparse
try:
    from html import entities
except ImportError:
    import htmlentitydefs as entities


def build_inlinepatterns(md_instance, **kwargs):
    """ Build the default set of inline patterns for Markdown. """
    inlinePatterns = odict.OrderedDict()
    inlinePatterns["backtick"] = BacktickPattern(BACKTICK_RE)
    inlinePatterns["escape"] = EscapePattern(ESCAPE_RE, md_instance)
    inlinePatterns["reference"] = ReferencePattern(REFERENCE_RE, md_instance)
    inlinePatterns["link"] = LinkPattern(LINK_RE, md_instance)
    inlinePatterns["image_link"] = ImagePattern(IMAGE_LINK_RE, md_instance)
    inlinePatterns["image_reference"] = \
            ImageReferencePattern(IMAGE_REFERENCE_RE, md_instance)
    inlinePatterns["short_reference"] = \
            ReferencePattern(SHORT_REF_RE, md_instance)
    inlinePatterns["autolink"] = AutolinkPattern(AUTOLINK_RE, md_instance)
    inlinePatterns["automail"] = AutomailPattern(AUTOMAIL_RE, md_instance)
    inlinePatterns["linebreak"] = SubstituteTagPattern(LINE_BREAK_RE, 'br')
    if md_instance.safeMode != 'escape':
        inlinePatterns["html"] = HtmlPattern(HTML_RE, md_instance)
    inlinePatterns["entity"] = HtmlPattern(ENTITY_RE, md_instance)
    inlinePatterns["not_strong"] = SimpleTextPattern(NOT_STRONG_RE)
    inlinePatterns["strong_em"] = DoubleTagPattern(STRONG_EM_RE, 'strong,em')
    inlinePatterns["strong"] = SimpleTagPattern(STRONG_RE, 'strong')
    inlinePatterns["emphasis"] = SimpleTagPattern(EMPHASIS_RE, 'em')
    if md_instance.smart_emphasis:
        inlinePatterns["emphasis2"] = SimpleTagPattern(SMART_EMPHASIS_RE, 'em')
    else:
        inlinePatterns["emphasis2"] = SimpleTagPattern(EMPHASIS_2_RE, 'em')
    return inlinePatterns

"""
The actual regular expressions for patterns
-----------------------------------------------------------------------------
"""

NOBRACKET = r'[^\]\[]*'
BRK = ( r'\[('
        + (NOBRACKET + r'(\[')*6
        + (NOBRACKET+ r'\])*')*6
        + NOBRACKET + r')\]' )
NOIMG = r'(?<!\!)'

BACKTICK_RE = r'(?<!\\)(`+)(.+?)(?<!`)\2(?!`)' # `e=f()` or ``e=f("`")``
ESCAPE_RE = r'\\(.)'                             # \<
EMPHASIS_RE = r'(\*)([^\*]+)\2'                    # *emphasis*
STRONG_RE = r'(\*{2}|_{2})(.+?)\2'                      # **strong**
STRONG_EM_RE = r'(\*{3}|_{3})(.+?)\2'            # ***strong***
SMART_EMPHASIS_RE = r'(?<!\w)(_)(?!_)(.+?)(?<!_)\2(?!\w)'  # _smart_emphasis_
EMPHASIS_2_RE = r'(_)(.+?)\2'                 # _emphasis_
LINK_RE = NOIMG + BRK + \
r'''\(\s*(<.*?>|((?:(?:\(.*?\))|[^\(\)]))*?)\s*((['"])(.*?)\12\s*)?\)'''
# [text](url) or [text](<url>) or [text](url "title")

IMAGE_LINK_RE = r'\!' + BRK + r'\s*\((<.*?>|([^")]+"[^"]*"|[^\)]*))\)'
# ![alttxt](http://x.com/) or ![alttxt](<http://x.com/>)
REFERENCE_RE = NOIMG + BRK+ r'\s?\[([^\]]*)\]'           # [Google][3]
SHORT_REF_RE = NOIMG + r'\[([^\]]+)\]'                   # [Google]
IMAGE_REFERENCE_RE = r'\!' + BRK + '\s?\[([^\]]*)\]' # ![alt text][2]
NOT_STRONG_RE = r'((^| )(\*|_)( |$))'                        # stand-alone * or _
AUTOLINK_RE = r'<((?:[Ff]|[Hh][Tt])[Tt][Pp][Ss]?://[^>]*)>' # <http://www.123.com>
AUTOMAIL_RE = r'<([^> \!]*@[^> ]*)>'               # <me@example.com>

HTML_RE = r'(\<([a-zA-Z/][^\>]*?|\!--.*?--)\>)'               # <...>
ENTITY_RE = r'(&[\#a-zA-Z0-9]*;)'               # &amp;
LINE_BREAK_RE = r'  \n'                     # two spaces at end of line


def dequote(string):
    """Remove quotes from around a string."""
    if ( ( string.startswith('"') and string.endswith('"'))
         or (string.startswith("'") and string.endswith("'")) ):
        return string[1:-1]
    else:
        return string

ATTR_RE = re.compile("\{@([^\}]*)=([^\}]*)}") # {@id=123}

def handleAttributes(text, parent):
    """Set values of an element based on attribute definitions ({@id=123})."""
    def attributeCallback(match):
        parent.set(match.group(1), match.group(2).replace('\n', ' '))
    return ATTR_RE.sub(attributeCallback, text)


"""
The pattern classes
-----------------------------------------------------------------------------
"""

class Pattern(object):
    """Base class that inline patterns subclass. """

    def __init__(self, pattern, markdown_instance=None):
        """
        Create an instant of an inline pattern.

        Keyword arguments:

        * pattern: A regular expression that matches a pattern

        """
        self.pattern = pattern
        self.compiled_re = re.compile("^(.*?)%s(.*?)$" % pattern, 
                                      re.DOTALL | re.UNICODE)

        # Api for Markdown to pass safe_mode into instance
        self.safe_mode = False
        if markdown_instance:
            self.markdown = markdown_instance

    def getCompiledRegExp(self):
        """ Return a compiled regular expression. """
        return self.compiled_re

    def handleMatch(self, m):
        """Return a ElementTree element from the given match.

        Subclasses should override this method.

        Keyword arguments:

        * m: A re match object containing a match of the pattern.

        """
        pass

    def type(self):
        """ Return class name, to define pattern type """
        return self.__class__.__name__

    def unescape(self, text):
        """ Return unescaped text given text with an inline placeholder. """
        try:
            stash = self.markdown.treeprocessors['inline'].stashed_nodes
        except KeyError:
            return text
        def itertext(el):
            ' Reimplement Element.itertext for older python versions '
            tag = el.tag
            if not isinstance(tag, util.string_type) and tag is not None:
                return
            if el.text:
                yield el.text
            for e in el:
                for s in itertext(e):
                    yield s
                if e.tail:
                    yield e.tail
        def get_stash(m):
            id = m.group(1)
            if id in stash:
                value = stash.get(id)
                if isinstance(value, util.string_type):
                    return value
                else:
                    # An etree Element - return text content only
                    return ''.join(itertext(value)) 
        return util.INLINE_PLACEHOLDER_RE.sub(get_stash, text)


class SimpleTextPattern(Pattern):
    """ Return a simple text of group(2) of a Pattern. """
    def handleMatch(self, m):
        text = m.group(2)
        if text == util.INLINE_PLACEHOLDER_PREFIX:
            return None
        return text


class EscapePattern(Pattern):
    """ Return an escaped character. """

    def handleMatch(self, m):
        char = m.group(2)
        if char in self.markdown.ESCAPED_CHARS:
            return '%s%s%s' % (util.STX, ord(char), util.ETX)
        else:
            return None 


class SimpleTagPattern(Pattern):
    """
    Return element of type `tag` with a text attribute of group(3)
    of a Pattern.

    """
    def __init__ (self, pattern, tag):
        Pattern.__init__(self, pattern)
        self.tag = tag

    def handleMatch(self, m):
        el = util.etree.Element(self.tag)
        el.text = m.group(3)
        return el


class SubstituteTagPattern(SimpleTagPattern):
    """ Return an element of type `tag` with no children. """
    def handleMatch (self, m):
        return util.etree.Element(self.tag)


class BacktickPattern(Pattern):
    """ Return a `<code>` element containing the matching text. """
    def __init__ (self, pattern):
        Pattern.__init__(self, pattern)
        self.tag = "code"

    def handleMatch(self, m):
        el = util.etree.Element(self.tag)
        el.text = util.AtomicString(m.group(3).strip())
        return el


class DoubleTagPattern(SimpleTagPattern):
    """Return a ElementTree element nested in tag2 nested in tag1.

    Useful for strong emphasis etc.

    """
    def handleMatch(self, m):
        tag1, tag2 = self.tag.split(",")
        el1 = util.etree.Element(tag1)
        el2 = util.etree.SubElement(el1, tag2)
        el2.text = m.group(3)
        return el1


class HtmlPattern(Pattern):
    """ Store raw inline html and return a placeholder. """
    def handleMatch (self, m):
        rawhtml = self.unescape(m.group(2))
        place_holder = self.markdown.htmlStash.store(rawhtml)
        return place_holder

    def unescape(self, text):
        """ Return unescaped text given text with an inline placeholder. """
        try:
            stash = self.markdown.treeprocessors['inline'].stashed_nodes
        except KeyError:
            return text
        def get_stash(m):
            id = m.group(1)
            value = stash.get(id)
            if value is not None:
                try:
                    return self.markdown.serializer(value)
                except:
                    return '\%s' % value
            
        return util.INLINE_PLACEHOLDER_RE.sub(get_stash, text)


class LinkPattern(Pattern):
    """ Return a link element from the given match. """
    def handleMatch(self, m):
        el = util.etree.Element("a")
        el.text = m.group(2)
        title = m.group(13)
        href = m.group(9)

        if href:
            if href[0] == "<":
                href = href[1:-1]
            el.set("href", self.sanitize_url(self.unescape(href.strip())))
        else:
            el.set("href", "")

        if title:
            title = dequote(self.unescape(title)) 
            el.set("title", title)
        return el

    def sanitize_url(self, url):
        """
        Sanitize a url against xss attacks in "safe_mode".

        Rather than specifically blacklisting `javascript:alert("XSS")` and all
        its aliases (see <http://ha.ckers.org/xss.html>), we whitelist known
        safe url formats. Most urls contain a network location, however some
        are known not to (i.e.: mailto links). Script urls do not contain a
        location. Additionally, for `javascript:...`, the scheme would be
        "javascript" but some aliases will appear to `urlparse()` to have no
        scheme. On top of that relative links (i.e.: "foo/bar.html") have no
        scheme. Therefore we must check "path", "parameters", "query" and
        "fragment" for any literal colons. We don't check "scheme" for colons
        because it *should* never have any and "netloc" must allow the form:
        `username:password@host:port`.

        """
        if not self.markdown.safeMode:
            # Return immediately bipassing parsing.
            return url
        
        try:
            scheme, netloc, path, params, query, fragment = url = urlparse(url)
        except ValueError:
            # Bad url - so bad it couldn't be parsed.
            return ''
        
        locless_schemes = ['', 'mailto', 'news']
        allowed_schemes = locless_schemes + ['http', 'https', 'ftp', 'ftps']
        if scheme not in allowed_schemes:
            # Not a known (allowed) scheme. Not safe.
            return ''
            
        if netloc == '' and scheme not in locless_schemes:
            # This should not happen. Treat as suspect.
            return ''

        for part in url[2:]:
            if ":" in part:
                # A colon in "path", "parameters", "query" or "fragment" is suspect.
                return ''

        # Url passes all tests. Return url as-is.
        return urlunparse(url)

class ImagePattern(LinkPattern):
    """ Return a img element from the given match. """
    def handleMatch(self, m):
        el = util.etree.Element("img")
        src_parts = m.group(9).split()
        if src_parts:
            src = src_parts[0]
            if src[0] == "<" and src[-1] == ">":
                src = src[1:-1]
            el.set('src', self.sanitize_url(self.unescape(src)))
        else:
            el.set('src', "")
        if len(src_parts) > 1:
            el.set('title', dequote(self.unescape(" ".join(src_parts[1:]))))

        if self.markdown.enable_attributes:
            truealt = handleAttributes(m.group(2), el)
        else:
            truealt = m.group(2)

        el.set('alt', self.unescape(truealt))
        return el

class ReferencePattern(LinkPattern):
    """ Match to a stored reference and return link element. """

    NEWLINE_CLEANUP_RE = re.compile(r'[ ]?\n', re.MULTILINE)

    def handleMatch(self, m):
        try:
            id = m.group(9).lower()
        except IndexError:
            id = None
        if not id:
            # if we got something like "[Google][]" or "[Goggle]"
            # we'll use "google" as the id
            id = m.group(2).lower()

        # Clean up linebreaks in id
        id = self.NEWLINE_CLEANUP_RE.sub(' ', id)
        if not id in self.markdown.references: # ignore undefined refs
            return None
        href, title = self.markdown.references[id]

        text = m.group(2)
        return self.makeTag(href, title, text)

    def makeTag(self, href, title, text):
        el = util.etree.Element('a')

        el.set('href', self.sanitize_url(href))
        if title:
            el.set('title', title)

        el.text = text
        return el


class ImageReferencePattern(ReferencePattern):
    """ Match to a stored reference and return img element. """
    def makeTag(self, href, title, text):
        el = util.etree.Element("img")
        el.set("src", self.sanitize_url(href))
        if title:
            el.set("title", title)

        if self.markdown.enable_attributes:
            text = handleAttributes(text, el)

        el.set("alt", self.unescape(text))
        return el


class AutolinkPattern(Pattern):
    """ Return a link Element given an autolink (`<http://example/com>`). """
    def handleMatch(self, m):
        el = util.etree.Element("a")
        el.set('href', self.unescape(m.group(2)))
        el.text = util.AtomicString(m.group(2))
        return el

class AutomailPattern(Pattern):
    """
    Return a mailto link Element given an automail link (`<foo@example.com>`).
    """
    def handleMatch(self, m):
        el = util.etree.Element('a')
        email = self.unescape(m.group(2))
        if email.startswith("mailto:"):
            email = email[len("mailto:"):]

        def codepoint2name(code):
            """Return entity definition by code, or the code if not defined."""
            entity = entities.codepoint2name.get(code)
            if entity:
                return "%s%s;" % (util.AMP_SUBSTITUTE, entity)
            else:
                return "%s#%d;" % (util.AMP_SUBSTITUTE, code)

        letters = [codepoint2name(ord(letter)) for letter in email]
        el.text = util.AtomicString(''.join(letters))

        mailto = "mailto:" + email
        mailto = "".join([util.AMP_SUBSTITUTE + '#%d;' %
                          ord(letter) for letter in mailto])
        el.set('href', mailto)
        return el


########NEW FILE########
__FILENAME__ = odict
from __future__ import unicode_literals
from __future__ import absolute_import
from . import util

from copy import deepcopy

class OrderedDict(dict):
    """
    A dictionary that keeps its keys in the order in which they're inserted.
    
    Copied from Django's SortedDict with some modifications.

    """
    def __new__(cls, *args, **kwargs):
        instance = super(OrderedDict, cls).__new__(cls, *args, **kwargs)
        instance.keyOrder = []
        return instance

    def __init__(self, data=None):
        if data is None or isinstance(data, dict):
            data = data or []
            super(OrderedDict, self).__init__(data)
            self.keyOrder = list(data) if data else []
        else:
            super(OrderedDict, self).__init__()
            super_set = super(OrderedDict, self).__setitem__
            for key, value in data:
                # Take the ordering from first key
                if key not in self:
                    self.keyOrder.append(key)
                # But override with last value in data (dict() does this)
                super_set(key, value)

    def __deepcopy__(self, memo):
        return self.__class__([(key, deepcopy(value, memo))
                               for key, value in self.items()])

    def __copy__(self):
        # The Python's default copy implementation will alter the state
        # of self. The reason for this seems complex but is likely related to
        # subclassing dict.
        return self.copy()

    def __setitem__(self, key, value):
        if key not in self:
            self.keyOrder.append(key)
        super(OrderedDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        super(OrderedDict, self).__delitem__(key)
        self.keyOrder.remove(key)

    def __iter__(self):
        return iter(self.keyOrder)

    def __reversed__(self):
        return reversed(self.keyOrder)

    def pop(self, k, *args):
        result = super(OrderedDict, self).pop(k, *args)
        try:
            self.keyOrder.remove(k)
        except ValueError:
            # Key wasn't in the dictionary in the first place. No problem.
            pass
        return result

    def popitem(self):
        result = super(OrderedDict, self).popitem()
        self.keyOrder.remove(result[0])
        return result

    def _iteritems(self):
        for key in self.keyOrder:
            yield key, self[key]

    def _iterkeys(self):
        for key in self.keyOrder:
            yield key

    def _itervalues(self):
        for key in self.keyOrder:
            yield self[key]

    if util.PY3:
        items = _iteritems
        keys = _iterkeys
        values = _itervalues
    else:
        iteritems = _iteritems
        iterkeys = _iterkeys
        itervalues = _itervalues

        def items(self):
            return [(k, self[k]) for k in self.keyOrder]

        def keys(self):
            return self.keyOrder[:]

        def values(self):
            return [self[k] for k in self.keyOrder]

    def update(self, dict_):
        for k in dict_:
            self[k] = dict_[k]

    def setdefault(self, key, default):
        if key not in self:
            self.keyOrder.append(key)
        return super(OrderedDict, self).setdefault(key, default)

    def value_for_index(self, index):
        """Returns the value of the item at the given zero-based index."""
        return self[self.keyOrder[index]]

    def insert(self, index, key, value):
        """Inserts the key, value pair before the item with the given index."""
        if key in self.keyOrder:
            n = self.keyOrder.index(key)
            del self.keyOrder[n]
            if n < index:
                index -= 1
        self.keyOrder.insert(index, key)
        super(OrderedDict, self).__setitem__(key, value)

    def copy(self):
        """Returns a copy of this object."""
        # This way of initializing the copy means it works for subclasses, too.
        return self.__class__(self)

    def __repr__(self):
        """
        Replaces the normal dict.__repr__ with a version that returns the keys
        in their Ordered order.
        """
        return '{%s}' % ', '.join(['%r: %r' % (k, v) for k, v in self._iteritems()])

    def clear(self):
        super(OrderedDict, self).clear()
        self.keyOrder = []

    def index(self, key):
        """ Return the index of a given key. """
        try:
            return self.keyOrder.index(key)
        except ValueError:
            raise ValueError("Element '%s' was not found in OrderedDict" % key)

    def index_for_location(self, location):
        """ Return index or None for a given location. """
        if location == '_begin':
            i = 0
        elif location == '_end':
            i = None
        elif location.startswith('<') or location.startswith('>'):
            i = self.index(location[1:])
            if location.startswith('>'):
                if i >= len(self):
                    # last item
                    i = None
                else:
                    i += 1
        else:
            raise ValueError('Not a valid location: "%s". Location key '
                             'must start with a ">" or "<".' % location)
        return i

    def add(self, key, value, location):
        """ Insert by key location. """
        i = self.index_for_location(location)
        if i is not None:
            self.insert(i, key, value)
        else:
            self.__setitem__(key, value)

    def link(self, key, location):
        """ Change location of an existing item. """
        n = self.keyOrder.index(key)
        del self.keyOrder[n]
        try:
            i = self.index_for_location(location)
            if i is not None:
                self.keyOrder.insert(i, key)
            else:
                self.keyOrder.append(key)
        except Exception as e:
            # restore to prevent data loss and reraise
            self.keyOrder.insert(n, key)
            raise e

########NEW FILE########
__FILENAME__ = postprocessors
"""
POST-PROCESSORS
=============================================================================

Markdown also allows post-processors, which are similar to preprocessors in
that they need to implement a "run" method. However, they are run after core
processing.

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import util
from . import odict
import re


def build_postprocessors(md_instance, **kwargs):
    """ Build the default postprocessors for Markdown. """
    postprocessors = odict.OrderedDict()
    postprocessors["raw_html"] = RawHtmlPostprocessor(md_instance)
    postprocessors["amp_substitute"] = AndSubstitutePostprocessor()
    postprocessors["unescape"] = UnescapePostprocessor()
    return postprocessors


class Postprocessor(util.Processor):
    """
    Postprocessors are run after the ElementTree it converted back into text.

    Each Postprocessor implements a "run" method that takes a pointer to a
    text string, modifies it as necessary and returns a text string.

    Postprocessors must extend markdown.Postprocessor.

    """

    def run(self, text):
        """
        Subclasses of Postprocessor should implement a `run` method, which
        takes the html document as a single text string and returns a
        (possibly modified) string.

        """
        pass


class RawHtmlPostprocessor(Postprocessor):
    """ Restore raw html to the document. """

    def run(self, text):
        """ Iterate over html stash and restore "safe" html. """
        for i in range(self.markdown.htmlStash.html_counter):
            html, safe  = self.markdown.htmlStash.rawHtmlBlocks[i]
            if self.markdown.safeMode and not safe:
                if str(self.markdown.safeMode).lower() == 'escape':
                    html = self.escape(html)
                elif str(self.markdown.safeMode).lower() == 'remove':
                    html = ''
                else:
                    html = self.markdown.html_replacement_text
            if self.isblocklevel(html) and (safe or not self.markdown.safeMode):
                text = text.replace("<p>%s</p>" % 
                            (self.markdown.htmlStash.get_placeholder(i)),
                            html + "\n")
            text =  text.replace(self.markdown.htmlStash.get_placeholder(i), 
                                 html)
        return text

    def escape(self, html):
        """ Basic html escaping """
        html = html.replace('&', '&amp;')
        html = html.replace('<', '&lt;')
        html = html.replace('>', '&gt;')
        return html.replace('"', '&quot;')

    def isblocklevel(self, html):
        m = re.match(r'^\<\/?([^ >]+)', html)
        if m:
            if m.group(1)[0] in ('!', '?', '@', '%'):
                # Comment, php etc...
                return True
            return util.isBlockLevel(m.group(1))
        return False


class AndSubstitutePostprocessor(Postprocessor):
    """ Restore valid entities """

    def run(self, text):
        text =  text.replace(util.AMP_SUBSTITUTE, "&")
        return text


class UnescapePostprocessor(Postprocessor):
    """ Restore escaped chars """

    RE = re.compile('%s(\d+)%s' % (util.STX, util.ETX))

    def unescape(self, m):
        return util.int2str(int(m.group(1)))

    def run(self, text):
        return self.RE.sub(self.unescape, text)

########NEW FILE########
__FILENAME__ = preprocessors
"""
PRE-PROCESSORS
=============================================================================

Preprocessors work on source text before we start doing anything too
complicated.
"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import util
from . import odict
import re


def build_preprocessors(md_instance, **kwargs):
    """ Build the default set of preprocessors used by Markdown. """
    preprocessors = odict.OrderedDict()
    preprocessors['normalize_whitespace'] = NormalizeWhitespace(md_instance)
    if md_instance.safeMode != 'escape':
        preprocessors["html_block"] = HtmlBlockPreprocessor(md_instance)
    preprocessors["reference"] = ReferencePreprocessor(md_instance)
    return preprocessors


class Preprocessor(util.Processor):
    """
    Preprocessors are run after the text is broken into lines.

    Each preprocessor implements a "run" method that takes a pointer to a
    list of lines of the document, modifies it as necessary and returns
    either the same pointer or a pointer to a new list.

    Preprocessors must extend markdown.Preprocessor.

    """
    def run(self, lines):
        """
        Each subclass of Preprocessor should override the `run` method, which
        takes the document as a list of strings split by newlines and returns
        the (possibly modified) list of lines.

        """
        pass


class NormalizeWhitespace(Preprocessor):
    """ Normalize whitespace for consistant parsing. """

    def run(self, lines):
        source = '\n'.join(lines)
        source = source.replace(util.STX, "").replace(util.ETX, "")
        source = source.replace("\r\n", "\n").replace("\r", "\n") + "\n\n"
        source = source.expandtabs(self.markdown.tab_length)
        source = re.sub(r'(?<=\n) +\n', '\n', source)
        return source.split('\n')


class HtmlBlockPreprocessor(Preprocessor):
    """Remove html blocks from the text and store them for later retrieval."""

    right_tag_patterns = ["</%s>", "%s>"]
    attrs_pattern = r"""
        \s+(?P<attr>[^>"'/= ]+)=(?P<q>['"])(?P<value>.*?)(?P=q)   # attr="value"
        |                                                         # OR
        \s+(?P<attr1>[^>"'/= ]+)=(?P<value1>[^> ]+)               # attr=value
        |                                                         # OR
        \s+(?P<attr2>[^>"'/= ]+)                                  # attr
        """
    left_tag_pattern = r'^\<(?P<tag>[^> ]+)(?P<attrs>(%s)*)\s*\/?\>?' % attrs_pattern
    attrs_re = re.compile(attrs_pattern, re.VERBOSE)
    left_tag_re = re.compile(left_tag_pattern, re.VERBOSE)
    markdown_in_raw = False

    def _get_left_tag(self, block):
        m = self.left_tag_re.match(block)
        if m:
            tag = m.group('tag')
            raw_attrs = m.group('attrs')
            attrs = {}
            if raw_attrs:
                for ma in self.attrs_re.finditer(raw_attrs):
                    if ma.group('attr'):
                        if ma.group('value'):
                            attrs[ma.group('attr').strip()] = ma.group('value')
                        else:
                            attrs[ma.group('attr').strip()] = ""
                    elif ma.group('attr1'):
                        if ma.group('value1'):
                            attrs[ma.group('attr1').strip()] = ma.group('value1')
                        else:
                            attrs[ma.group('attr1').strip()] = ""
                    elif ma.group('attr2'):
                        attrs[ma.group('attr2').strip()] = ""
            return tag, len(m.group(0)), attrs
        else:
            tag = block[1:].split(">", 1)[0].lower()
            return tag, len(tag)+2, {}

    def _recursive_tagfind(self, ltag, rtag, start_index, block):
        while 1:
            i = block.find(rtag, start_index)
            if i == -1:
                return -1
            j = block.find(ltag, start_index)
            # if no ltag, or rtag found before another ltag, return index
            if (j > i or j == -1):
                return i + len(rtag)
            # another ltag found before rtag, use end of ltag as starting
            # point and search again
            j = block.find('>', j)
            start_index = self._recursive_tagfind(ltag, rtag, j + 1, block)
            if start_index == -1:
                # HTML potentially malformed- ltag has no corresponding
                # rtag
                return -1

    def _get_right_tag(self, left_tag, left_index, block):
        for p in self.right_tag_patterns:
            tag = p % left_tag
            i = self._recursive_tagfind("<%s" % left_tag, tag, left_index, block)
            if i > 2:
                return tag.lstrip("<").rstrip(">"), i
        return block.rstrip()[-left_index:-1].lower(), len(block)

    def _equal_tags(self, left_tag, right_tag):
        if left_tag[0] in ['?', '@', '%']: # handle PHP, etc.
            return True
        if ("/" + left_tag) == right_tag:
            return True
        if (right_tag == "--" and left_tag == "--"):
            return True
        elif left_tag == right_tag[1:] \
            and right_tag[0] == "/":
            return True
        else:
            return False

    def _is_oneliner(self, tag):
        return (tag in ['hr', 'hr/'])

    def _stringindex_to_listindex(self, stringindex, items):
        """
        Same effect as concatenating the strings in items,
        finding the character to which stringindex refers in that string,
        and returning the index of the item in which that character resides.
        """
        items.append('dummy')
        i, count = 0, 0
        while count <= stringindex:
            count += len(items[i])
            i += 1
        return i - 1

    def _nested_markdown_in_html(self, items):
        """Find and process html child elements of the given element block."""
        for i, item in enumerate(items):
            if self.left_tag_re.match(item):
                left_tag, left_index, attrs = \
                    self._get_left_tag(''.join(items[i:]))
                right_tag, data_index = self._get_right_tag(
                    left_tag, left_index, ''.join(items[i:]))
                right_listindex = \
                    self._stringindex_to_listindex(data_index, items[i:]) + i
                if 'markdown' in attrs.keys():
                    items[i] = items[i][left_index:]  # remove opening tag
                    placeholder = self.markdown.htmlStash.store_tag(
                        left_tag, attrs, i + 1, right_listindex + 1)
                    items.insert(i, placeholder)
                    if len(items) - right_listindex <= 1:  # last nest, no tail
                        right_listindex -= 1
                    items[right_listindex] = items[right_listindex][
                        :-len(right_tag) - 2]  # remove closing tag
                else:  # raw html
                    if len(items) - right_listindex <= 1:  # last element
                        right_listindex -= 1
                    placeholder = self.markdown.htmlStash.store('\n\n'.join(
                        items[i:right_listindex + 1]))
                    del items[i:right_listindex + 1]
                    items.insert(i, placeholder)
        return items

    def run(self, lines):
        text = "\n".join(lines)
        new_blocks = []
        text = text.rsplit("\n\n")
        items = []
        left_tag = ''
        right_tag = ''
        in_tag = False # flag

        while text:
            block = text[0]
            if block.startswith("\n"):
                block = block[1:]
            text = text[1:]

            if block.startswith("\n"):
                block = block[1:]

            if not in_tag:
                if block.startswith("<") and len(block.strip()) > 1:

                    if block[1:4] == "!--":
                        # is a comment block
                        left_tag, left_index, attrs  = "--", 2, {}
                    else:
                        left_tag, left_index, attrs = self._get_left_tag(block)
                    right_tag, data_index = self._get_right_tag(left_tag,
                                                                left_index,
                                                                block)
                    # keep checking conditions below and maybe just append

                    if data_index < len(block) \
                        and (util.isBlockLevel(left_tag)
                        or left_tag == '--'):
                        text.insert(0, block[data_index:])
                        block = block[:data_index]

                    if not (util.isBlockLevel(left_tag) \
                        or block[1] in ["!", "?", "@", "%"]):
                        new_blocks.append(block)
                        continue

                    if self._is_oneliner(left_tag):
                        new_blocks.append(block.strip())
                        continue

                    if block.rstrip().endswith(">") \
                            and self._equal_tags(left_tag, right_tag):
                        if self.markdown_in_raw and 'markdown' in attrs.keys():
                            block = block[left_index:-len(right_tag) - 2]
                            new_blocks.append(self.markdown.htmlStash.
                                              store_tag(left_tag, attrs, 0, 2))
                            new_blocks.extend([block])
                        else:
                            new_blocks.append(
                                self.markdown.htmlStash.store(block.strip()))
                        continue
                    else:
                        # if is block level tag and is not complete
                        if  (not self._equal_tags(left_tag, right_tag)) and \
                            (util.isBlockLevel(left_tag) or left_tag == "--"):
                            items.append(block.strip())
                            in_tag = True
                        else:
                            new_blocks.append(
                            self.markdown.htmlStash.store(block.strip()))

                        continue

                else:
                    new_blocks.append(block)

            else:
                items.append(block)

                right_tag, data_index = self._get_right_tag(left_tag, 0, block)

                if self._equal_tags(left_tag, right_tag):
                    # if find closing tag

                    if data_index < len(block):
                        # we have more text after right_tag
                        items[-1] = block[:data_index]
                        text.insert(0, block[data_index:])

                    in_tag = False
                    if self.markdown_in_raw and 'markdown' in attrs.keys():
                        items[0] = items[0][left_index:]
                        items[-1] = items[-1][:-len(right_tag) - 2]
                        if items[len(items) - 1]:  # not a newline/empty string
                            right_index = len(items) + 3
                        else:
                            right_index = len(items) + 2
                        new_blocks.append(self.markdown.htmlStash.store_tag(
                            left_tag, attrs, 0, right_index))
                        placeholderslen = len(self.markdown.htmlStash.tag_data)
                        new_blocks.extend(
                            self._nested_markdown_in_html(items))
                        nests = len(self.markdown.htmlStash.tag_data) - \
                            placeholderslen
                        self.markdown.htmlStash.tag_data[-1 - nests][
                            'right_index'] += nests - 2
                    else:
                        new_blocks.append(
                            self.markdown.htmlStash.store('\n\n'.join(items)))
                    items = []

        if items:
            if self.markdown_in_raw and 'markdown' in attrs.keys():
                items[0] = items[0][left_index:]
                items[-1] = items[-1][:-len(right_tag) - 2]
                if items[len(items) - 1]:  # not a newline/empty string
                    right_index = len(items) + 3
                else:
                    right_index = len(items) + 2
                new_blocks.append(
                    self.markdown.htmlStash.store_tag(
                        left_tag, attrs, 0, right_index))
                placeholderslen = len(self.markdown.htmlStash.tag_data)
                new_blocks.extend(self._nested_markdown_in_html(items))
                nests = len(self.markdown.htmlStash.tag_data) - placeholderslen
                self.markdown.htmlStash.tag_data[-1 - nests][
                    'right_index'] += nests - 2
            else:
                new_blocks.append(
                    self.markdown.htmlStash.store('\n\n'.join(items)))
            new_blocks.append('\n')

        new_text = "\n\n".join(new_blocks)
        return new_text.split("\n")


class ReferencePreprocessor(Preprocessor):
    """ Remove reference definitions from text and store for later use. """

    TITLE = r'[ ]*(\"(.*)\"|\'(.*)\'|\((.*)\))[ ]*'
    RE = re.compile(r'^[ ]{0,3}\[([^\]]*)\]:\s*([^ ]*)[ ]*(%s)?$' % TITLE, re.DOTALL)
    TITLE_RE = re.compile(r'^%s$' % TITLE)

    def run (self, lines):
        new_text = [];
        while lines:
            line = lines.pop(0)
            m = self.RE.match(line)
            if m:
                id = m.group(1).strip().lower()
                link = m.group(2).lstrip('<').rstrip('>')
                t = m.group(5) or m.group(6) or m.group(7)
                if not t:
                    # Check next line for title
                    tm = self.TITLE_RE.match(lines[0])
                    if tm:
                        lines.pop(0)
                        t = tm.group(2) or tm.group(3) or tm.group(4)
                self.markdown.references[id] = (link, t)
            else:
                new_text.append(line)

        return new_text #+ "\n"

########NEW FILE########
__FILENAME__ = serializers
# markdown/searializers.py
#
# Add x/html serialization to Elementree
# Taken from ElementTree 1.3 preview with slight modifications
#
# Copyright (c) 1999-2007 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2007 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------


from __future__ import absolute_import
from __future__ import unicode_literals
from . import util
ElementTree = util.etree.ElementTree
QName = util.etree.QName
if hasattr(util.etree, 'test_comment'):
    Comment = util.etree.test_comment
else:
    Comment = util.etree.Comment
PI = util.etree.PI
ProcessingInstruction = util.etree.ProcessingInstruction

__all__ = ['to_html_string', 'to_xhtml_string']

HTML_EMPTY = ("area", "base", "basefont", "br", "col", "frame", "hr",
              "img", "input", "isindex", "link", "meta" "param")

try:
    HTML_EMPTY = set(HTML_EMPTY)
except NameError:
    pass

_namespace_map = {
    # "well-known" namespace prefixes
    "http://www.w3.org/XML/1998/namespace": "xml",
    "http://www.w3.org/1999/xhtml": "html",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://schemas.xmlsoap.org/wsdl/": "wsdl",
    # xml schema
    "http://www.w3.org/2001/XMLSchema": "xs",
    "http://www.w3.org/2001/XMLSchema-instance": "xsi",
    # dublic core
    "http://purl.org/dc/elements/1.1/": "dc",
}


def _raise_serialization_error(text):
    raise TypeError(
        "cannot serialize %r (type %s)" % (text, type(text).__name__)
        )

def _encode(text, encoding):
    try:
        return text.encode(encoding, "xmlcharrefreplace")
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_cdata(text):
    # escape character data
    try:
        # it's worth avoiding do-nothing calls for strings that are
        # shorter than 500 character, or so.  assume that's, by far,
        # the most common case in most applications.
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)


def _escape_attrib(text):
    # escape attribute value
    try:
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        if "\"" in text:
            text = text.replace("\"", "&quot;")
        if "\n" in text:
            text = text.replace("\n", "&#10;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_attrib_html(text):
    # escape attribute value
    try:
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        if "\"" in text:
            text = text.replace("\"", "&quot;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)


def _serialize_html(write, elem, qnames, namespaces, format):
    tag = elem.tag
    text = elem.text
    if tag is Comment:
        write("<!--%s-->" % _escape_cdata(text))
    elif tag is ProcessingInstruction:
        write("<?%s?>" % _escape_cdata(text))
    else:
        tag = qnames[tag]
        if tag is None:
            if text:
                write(_escape_cdata(text))
            for e in elem:
                _serialize_html(write, e, qnames, None, format)
        else:
            write("<" + tag)
            items = elem.items()
            if items or namespaces:
                items = sorted(items) # lexical order
                for k, v in items:
                    if isinstance(k, QName):
                        k = k.text
                    if isinstance(v, QName):
                        v = qnames[v.text]
                    else:
                        v = _escape_attrib_html(v)
                    if qnames[k] == v and format == 'html':
                        # handle boolean attributes
                        write(" %s" % v)
                    else:
                        write(" %s=\"%s\"" % (qnames[k], v))
                if namespaces:
                    items = namespaces.items()
                    items.sort(key=lambda x: x[1]) # sort on prefix
                    for v, k in items:
                        if k:
                            k = ":" + k
                        write(" xmlns%s=\"%s\"" % (k, _escape_attrib(v)))
            if format == "xhtml" and tag.lower() in HTML_EMPTY:
                write(" />")
            else:
                write(">")
                if text:
                    if tag.lower() in ["script", "style"]:
                        write(text)
                    else:
                        write(_escape_cdata(text))
                for e in elem:
                    _serialize_html(write, e, qnames, None, format)
                if tag.lower() not in HTML_EMPTY:
                    write("</" + tag + ">")
    if elem.tail:
        write(_escape_cdata(elem.tail))

def _write_html(root,
                encoding=None,
                default_namespace=None,
                format="html"):
    assert root is not None
    data = []
    write = data.append
    qnames, namespaces = _namespaces(root, default_namespace)
    _serialize_html(write, root, qnames, namespaces, format)
    if encoding is None:
        return "".join(data)
    else:
        return _encode("".join(data))


# --------------------------------------------------------------------
# serialization support

def _namespaces(elem, default_namespace=None):
    # identify namespaces used in this tree

    # maps qnames to *encoded* prefix:local names
    qnames = {None: None}

    # maps uri:s to prefixes
    namespaces = {}
    if default_namespace:
        namespaces[default_namespace] = ""

    def add_qname(qname):
        # calculate serialized qname representation
        try:
            if qname[:1] == "{":
                uri, tag = qname[1:].split("}", 1)
                prefix = namespaces.get(uri)
                if prefix is None:
                    prefix = _namespace_map.get(uri)
                    if prefix is None:
                        prefix = "ns%d" % len(namespaces)
                    if prefix != "xml":
                        namespaces[uri] = prefix
                if prefix:
                    qnames[qname] = "%s:%s" % (prefix, tag)
                else:
                    qnames[qname] = tag # default element
            else:
                if default_namespace:
                    raise ValueError(
                        "cannot use non-qualified names with "
                        "default_namespace option"
                        )
                qnames[qname] = qname
        except TypeError:
            _raise_serialization_error(qname)

    # populate qname and namespaces table
    try:
        iterate = elem.iter
    except AttributeError:
        iterate = elem.getiterator # cET compatibility
    for elem in iterate():
        tag = elem.tag
        if isinstance(tag, QName) and tag.text not in qnames:
            add_qname(tag.text)
        elif isinstance(tag, util.string_type):
            if tag not in qnames:
                add_qname(tag)
        elif tag is not None and tag is not Comment and tag is not PI:
            _raise_serialization_error(tag)
        for key, value in elem.items():
            if isinstance(key, QName):
                key = key.text
            if key not in qnames:
                add_qname(key)
            if isinstance(value, QName) and value.text not in qnames:
                add_qname(value.text)
        text = elem.text
        if isinstance(text, QName) and text.text not in qnames:
            add_qname(text.text)
    return qnames, namespaces

def to_html_string(element):
    return _write_html(ElementTree(element).getroot(), format="html")

def to_xhtml_string(element):
    return _write_html(ElementTree(element).getroot(), format="xhtml")

########NEW FILE########
__FILENAME__ = treeprocessors
from __future__ import unicode_literals
from __future__ import absolute_import
from . import util
from . import odict
from . import inlinepatterns


def build_treeprocessors(md_instance, **kwargs):
    """ Build the default treeprocessors for Markdown. """
    treeprocessors = odict.OrderedDict()
    treeprocessors["inline"] = InlineProcessor(md_instance)
    treeprocessors["prettify"] = PrettifyTreeprocessor(md_instance)
    return treeprocessors


def isString(s):
    """ Check if it's string """
    if not isinstance(s, util.AtomicString):
        return isinstance(s, util.string_type)
    return False


class Treeprocessor(util.Processor):
    """
    Treeprocessors are run on the ElementTree object before serialization.

    Each Treeprocessor implements a "run" method that takes a pointer to an
    ElementTree, modifies it as necessary and returns an ElementTree
    object.

    Treeprocessors must extend markdown.Treeprocessor.

    """
    def run(self, root):
        """
        Subclasses of Treeprocessor should implement a `run` method, which
        takes a root ElementTree. This method can return another ElementTree 
        object, and the existing root ElementTree will be replaced, or it can 
        modify the current tree and return None.
        """
        pass


class InlineProcessor(Treeprocessor):
    """
    A Treeprocessor that traverses a tree, applying inline patterns.
    """

    def __init__(self, md):
        self.__placeholder_prefix = util.INLINE_PLACEHOLDER_PREFIX
        self.__placeholder_suffix = util.ETX
        self.__placeholder_length = 4 + len(self.__placeholder_prefix) \
                                      + len(self.__placeholder_suffix)
        self.__placeholder_re = util.INLINE_PLACEHOLDER_RE
        self.markdown = md
        self.inlinePatterns = md.inlinePatterns

    def __makePlaceholder(self, type):
        """ Generate a placeholder """
        id = "%04d" % len(self.stashed_nodes)
        hash = util.INLINE_PLACEHOLDER % id
        return hash, id

    def __findPlaceholder(self, data, index):
        """
        Extract id from data string, start from index

        Keyword arguments:

        * data: string
        * index: index, from which we start search

        Returns: placeholder id and string index, after the found placeholder.
        
        """
        m = self.__placeholder_re.search(data, index)
        if m:
            return m.group(1), m.end()
        else:
            return None, index + 1

    def __stashNode(self, node, type):
        """ Add node to stash """
        placeholder, id = self.__makePlaceholder(type)
        self.stashed_nodes[id] = node
        return placeholder

    def __handleInline(self, data, patternIndex=0):
        """
        Process string with inline patterns and replace it
        with placeholders

        Keyword arguments:

        * data: A line of Markdown text
        * patternIndex: The index of the inlinePattern to start with

        Returns: String with placeholders.

        """
        if not isinstance(data, util.AtomicString):
            startIndex = 0
            while patternIndex < len(self.inlinePatterns):
                data, matched, startIndex = self.__applyPattern(
                    self.inlinePatterns.value_for_index(patternIndex),
                    data, patternIndex, startIndex)
                if not matched:
                    patternIndex += 1
        return data

    def __processElementText(self, node, subnode, isText=True):
        """
        Process placeholders in Element.text or Element.tail
        of Elements popped from self.stashed_nodes.

        Keywords arguments:

        * node: parent node
        * subnode: processing node
        * isText: bool variable, True - it's text, False - it's tail

        Returns: None

        """
        if isText:
            text = subnode.text
            subnode.text = None
        else:
            text = subnode.tail
            subnode.tail = None

        childResult = self.__processPlaceholders(text, subnode)

        if not isText and node is not subnode:
            pos = list(node).index(subnode)
            node.remove(subnode)
        else:
            pos = 0

        childResult.reverse()
        for newChild in childResult:
            node.insert(pos, newChild)

    def __processPlaceholders(self, data, parent):
        """
        Process string with placeholders and generate ElementTree tree.

        Keyword arguments:

        * data: string with placeholders instead of ElementTree elements.
        * parent: Element, which contains processing inline data

        Returns: list with ElementTree elements with applied inline patterns.
        
        """
        def linkText(text):
            if text:
                if result:
                    if result[-1].tail:
                        result[-1].tail += text
                    else:
                        result[-1].tail = text
                else:
                    if parent.text:
                        parent.text += text
                    else:
                        parent.text = text
        result = []
        strartIndex = 0
        while data:
            index = data.find(self.__placeholder_prefix, strartIndex)
            if index != -1:
                id, phEndIndex = self.__findPlaceholder(data, index)

                if id in self.stashed_nodes:
                    node = self.stashed_nodes.get(id)

                    if index > 0:
                        text = data[strartIndex:index]
                        linkText(text)

                    if not isString(node): # it's Element
                        for child in [node] + list(node):
                            if child.tail:
                                if child.tail.strip():
                                    self.__processElementText(node, child,False)
                            if child.text:
                                if child.text.strip():
                                    self.__processElementText(child, child)
                    else: # it's just a string
                        linkText(node)
                        strartIndex = phEndIndex
                        continue

                    strartIndex = phEndIndex
                    result.append(node)

                else: # wrong placeholder
                    end = index + len(self.__placeholder_prefix)
                    linkText(data[strartIndex:end])
                    strartIndex = end
            else:
                text = data[strartIndex:]
                if isinstance(data, util.AtomicString):
                    # We don't want to loose the AtomicString
                    text = util.AtomicString(text)
                linkText(text)
                data = ""

        return result

    def __applyPattern(self, pattern, data, patternIndex, startIndex=0):
        """
        Check if the line fits the pattern, create the necessary
        elements, add it to stashed_nodes.

        Keyword arguments:

        * data: the text to be processed
        * pattern: the pattern to be checked
        * patternIndex: index of current pattern
        * startIndex: string index, from which we start searching

        Returns: String with placeholders instead of ElementTree elements.

        """
        match = pattern.getCompiledRegExp().match(data[startIndex:])
        leftData = data[:startIndex]

        if not match:
            return data, False, 0

        node = pattern.handleMatch(match)

        if node is None:
            return data, True, len(leftData)+match.span(len(match.groups()))[0]

        if not isString(node):
            if not isinstance(node.text, util.AtomicString):
                # We need to process current node too
                for child in [node] + list(node):
                    if not isString(node):
                        if child.text: 
                            child.text = self.__handleInline(child.text,
                                                            patternIndex + 1)
                        if child.tail:
                            child.tail = self.__handleInline(child.tail,
                                                            patternIndex)

        placeholder = self.__stashNode(node, pattern.type())

        return "%s%s%s%s" % (leftData,
                             match.group(1),
                             placeholder, match.groups()[-1]), True, 0

    def run(self, tree):
        """Apply inline patterns to a parsed Markdown tree.

        Iterate over ElementTree, find elements with inline tag, apply inline
        patterns and append newly created Elements to tree.  If you don't
        want to process your data with inline paterns, instead of normal string,
        use subclass AtomicString:

            node.text = markdown.AtomicString("This will not be processed.")

        Arguments:

        * tree: ElementTree object, representing Markdown tree.

        Returns: ElementTree object with applied inline patterns.

        """
        self.stashed_nodes = {}

        stack = [tree]

        while stack:
            currElement = stack.pop()
            insertQueue = []
            for child in currElement:
                if child.text and not isinstance(child.text, util.AtomicString):
                    text = child.text
                    child.text = None
                    lst = self.__processPlaceholders(self.__handleInline(
                                                    text), child)
                    stack += lst
                    insertQueue.append((child, lst))
                if child.tail:
                    tail = self.__handleInline(child.tail)
                    dumby = util.etree.Element('d')
                    tailResult = self.__processPlaceholders(tail, dumby)
                    if dumby.text:
                        child.tail = dumby.text
                    else:
                        child.tail = None
                    pos = list(currElement).index(child) + 1
                    tailResult.reverse()
                    for newChild in tailResult:
                        currElement.insert(pos, newChild)
                if len(child):
                    stack.append(child)

            for element, lst in insertQueue:
                if self.markdown.enable_attributes:
                    if element.text and isString(element.text):
                        element.text = \
                            inlinepatterns.handleAttributes(element.text, 
                                                                    element)
                i = 0
                for newChild in lst:
                    if self.markdown.enable_attributes:
                        # Processing attributes
                        if newChild.tail and isString(newChild.tail):
                            newChild.tail = \
                                inlinepatterns.handleAttributes(newChild.tail,
                                                                    element)
                        if newChild.text and isString(newChild.text):
                            newChild.text = \
                                inlinepatterns.handleAttributes(newChild.text,
                                                                    newChild)
                    element.insert(i, newChild)
                    i += 1
        return tree


class PrettifyTreeprocessor(Treeprocessor):
    """ Add linebreaks to the html document. """

    def _prettifyETree(self, elem):
        """ Recursively add linebreaks to ElementTree children. """

        i = "\n"
        if util.isBlockLevel(elem.tag) and elem.tag not in ['code', 'pre']:
            if (not elem.text or not elem.text.strip()) \
                    and len(elem) and util.isBlockLevel(elem[0].tag):
                elem.text = i
            for e in elem:
                if util.isBlockLevel(e.tag):
                    self._prettifyETree(e)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        if not elem.tail or not elem.tail.strip():
            elem.tail = i

    def run(self, root):
        """ Add linebreaks to ElementTree root object. """

        self._prettifyETree(root)
        # Do <br />'s seperately as they are often in the middle of
        # inline content and missed by _prettifyETree.
        brs = root.getiterator('br')
        for br in brs:
            if not br.tail or not br.tail.strip():
                br.tail = '\n'
            else:
                br.tail = '\n%s' % br.tail
        # Clean up extra empty lines at end of code blocks.
        pres = root.getiterator('pre')
        for pre in pres:
            if len(pre) and pre[0].tag == 'code':
                pre[0].text = pre[0].text.rstrip() + '\n'

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import sys


"""
Python 3 Stuff
=============================================================================
"""
PY3 = sys.version_info[0] == 3

if PY3:
    string_type = str
    text_type = str
    int2str = chr
else:
    string_type = basestring
    text_type = unicode
    int2str = unichr


"""
Constants you might want to modify
-----------------------------------------------------------------------------
"""

BLOCK_LEVEL_ELEMENTS = re.compile("^(p|div|h[1-6]|blockquote|pre|table|dl|ol|ul"
                                  "|script|noscript|form|fieldset|iframe|math"
                                  "|hr|hr/|style|li|dt|dd|thead|tbody"
                                  "|tr|th|td|section|footer|header|group|figure"
                                  "|figcaption|aside|article|canvas|output"
                                  "|progress|video|nav)$", re.IGNORECASE)
# Placeholders
STX = '\u0002'  # Use STX ("Start of text") for start-of-placeholder
ETX = '\u0003'  # Use ETX ("End of text") for end-of-placeholder
INLINE_PLACEHOLDER_PREFIX = STX+"klzzwxh:"
INLINE_PLACEHOLDER = INLINE_PLACEHOLDER_PREFIX + "%s" + ETX
INLINE_PLACEHOLDER_RE = re.compile(INLINE_PLACEHOLDER % r'([0-9]+)')
AMP_SUBSTITUTE = STX+"amp"+ETX
HTML_PLACEHOLDER = STX + "wzxhzdk:%s" + ETX
HTML_PLACEHOLDER_RE = re.compile(HTML_PLACEHOLDER % r'([0-9]+)')
TAG_PLACEHOLDER = STX + "hzzhzkh:%s" + ETX


"""
Constants you probably do not need to change
-----------------------------------------------------------------------------
"""

RTL_BIDI_RANGES = ( ('\u0590', '\u07FF'),
                     # Hebrew (0590-05FF), Arabic (0600-06FF),
                     # Syriac (0700-074F), Arabic supplement (0750-077F),
                     # Thaana (0780-07BF), Nko (07C0-07FF).
                    ('\u2D30', '\u2D7F'), # Tifinagh
                    )

# Extensions should use "markdown.util.etree" instead of "etree" (or do `from
# markdown.util import etree`).  Do not import it by yourself.

try: # Is the C implementation of ElementTree available?
    import xml.etree.cElementTree as etree
    from xml.etree.ElementTree import Comment
    # Serializers (including ours) test with non-c Comment
    etree.test_comment = Comment
    if etree.VERSION < "1.0.5":
        raise RuntimeError("cElementTree version 1.0.5 or higher is required.")
except (ImportError, RuntimeError):
    # Use the Python implementation of ElementTree?
    import xml.etree.ElementTree as etree
    if etree.VERSION < "1.1":
        raise RuntimeError("ElementTree version 1.1 or higher is required")


"""
AUXILIARY GLOBAL FUNCTIONS
=============================================================================
"""


def isBlockLevel(tag):
    """Check if the tag is a block level HTML tag."""
    if isinstance(tag, string_type):
        return BLOCK_LEVEL_ELEMENTS.match(tag)
    # Some ElementTree tags are not strings, so return False.
    return False

def parseBoolValue(value, fail_on_errors=True):
    """Parses a string representing bool value. If parsing was successful,
       returns True or False. If parsing was not successful, raises
       ValueError, or, if fail_on_errors=False, returns None."""
    if not isinstance(value, string_type):
        return bool(value)
    elif value.lower() in ('true', 'yes', 'y', 'on', '1'):
        return True
    elif value.lower() in ('false', 'no', 'n', 'off', '0'):
        return False
    elif fail_on_errors:
        raise ValueError('Cannot parse bool value: %r' % value)

"""
MISC AUXILIARY CLASSES
=============================================================================
"""

class AtomicString(text_type):
    """A string which should not be further processed."""
    pass


class Processor(object):
    def __init__(self, markdown_instance=None):
        if markdown_instance:
            self.markdown = markdown_instance


class HtmlStash(object):
    """
    This class is used for stashing HTML objects that we extract
    in the beginning and replace with place-holders.
    """

    def __init__(self):
        """ Create a HtmlStash. """
        self.html_counter = 0  # for counting inline html segments
        self.rawHtmlBlocks = []
        self.tag_counter = 0
        self.tag_data = []  # list of dictionaries in the order tags appear

    def store(self, html, safe=False):
        """
        Saves an HTML segment for later reinsertion.  Returns a
        placeholder string that needs to be inserted into the
        document.

        Keyword arguments:

        * html: an html segment
        * safe: label an html segment as safe for safemode

        Returns : a placeholder string

        """
        self.rawHtmlBlocks.append((html, safe))
        placeholder = self.get_placeholder(self.html_counter)
        self.html_counter += 1
        return placeholder

    def reset(self):
        self.html_counter = 0
        self.rawHtmlBlocks = []

    def get_placeholder(self, key):
        return HTML_PLACEHOLDER % key

    def store_tag(self, tag, attrs, left_index, right_index):
        """Store tag data and return a placeholder."""
        self.tag_data.append({'tag': tag, 'attrs': attrs,
                              'left_index': left_index,
                              'right_index': right_index})
        placeholder = TAG_PLACEHOLDER % str(self.tag_counter)
        self.tag_counter += 1  # equal to the tag's index in self.tag_data
        return placeholder

########NEW FILE########
__FILENAME__ = __main__
"""
COMMAND-LINE SPECIFIC STUFF
=============================================================================

"""

import markdown
import sys
import optparse

import logging
from logging import DEBUG, INFO, CRITICAL

logger =  logging.getLogger('MARKDOWN')

def parse_options():
    """
    Define and parse `optparse` options for command-line usage.
    """
    usage = """%prog [options] [INPUTFILE]
       (STDIN is assumed if no INPUTFILE is given)"""
    desc = "A Python implementation of John Gruber's Markdown. " \
           "http://packages.python.org/Markdown/"
    ver = "%%prog %s" % markdown.version
    
    parser = optparse.OptionParser(usage=usage, description=desc, version=ver)
    parser.add_option("-f", "--file", dest="filename", default=None,
                      help="Write output to OUTPUT_FILE. Defaults to STDOUT.",
                      metavar="OUTPUT_FILE")
    parser.add_option("-e", "--encoding", dest="encoding",
                      help="Encoding for input and output files.",)
    parser.add_option("-q", "--quiet", default = CRITICAL,
                      action="store_const", const=CRITICAL+10, dest="verbose",
                      help="Suppress all warnings.")
    parser.add_option("-v", "--verbose",
                      action="store_const", const=INFO, dest="verbose",
                      help="Print all warnings.")
    parser.add_option("-s", "--safe", dest="safe", default=False,
                      metavar="SAFE_MODE",
                      help="'replace', 'remove' or 'escape' HTML tags in input")
    parser.add_option("-o", "--output_format", dest="output_format", 
                      default='xhtml1', metavar="OUTPUT_FORMAT",
                      help="'xhtml1' (default), 'html4' or 'html5'.")
    parser.add_option("--noisy",
                      action="store_const", const=DEBUG, dest="verbose",
                      help="Print debug messages.")
    parser.add_option("-x", "--extension", action="append", dest="extensions",
                      help = "Load extension EXTENSION.", metavar="EXTENSION")
    parser.add_option("-n", "--no_lazy_ol", dest="lazy_ol", 
                      action='store_false', default=True,
                      help="Observe number of first item of ordered lists.")

    (options, args) = parser.parse_args()

    if len(args) == 0:
        input_file = None
    else:
        input_file = args[0]

    if not options.extensions:
        options.extensions = []

    return {'input': input_file,
            'output': options.filename,
            'safe_mode': options.safe,
            'extensions': options.extensions,
            'encoding': options.encoding,
            'output_format': options.output_format,
            'lazy_ol': options.lazy_ol}, options.verbose

def run():
    """Run Markdown from the command line."""

    # Parse options and adjust logging level if necessary
    options, logging_level = parse_options()
    if not options: sys.exit(2)
    logger.setLevel(logging_level)
    logger.addHandler(logging.StreamHandler())

    # Run
    markdown.markdownFromFile(**options)

if __name__ == '__main__':
    # Support running module as a commandline command. 
    # Python 2.5 & 2.6 do: `python -m markdown.__main__ [options] [args]`.
    # Python 2.7 & 3.x do: `python -m markdown [options] [args]`.
    run()

########NEW FILE########
__FILENAME__ = __version__
#
# markdown/__version__.py
#
# version_info should conform to PEP 386 
# (major, minor, micro, alpha/beta/rc/final, #)
# (1, 1, 2, 'alpha', 0) => "1.1.2.dev"
# (1, 2, 0, 'beta', 2) => "1.2b2"
version_info = (2, 4, 1, 'final', 0)

def _get_version():
    " Returns a PEP 386-compliant version number from version_info. "
    assert len(version_info) == 5
    assert version_info[3] in ('alpha', 'beta', 'rc', 'final')

    parts = 2 if version_info[2] == 0 else 3
    main = '.'.join(map(str, version_info[:parts]))

    sub = ''
    if version_info[3] == 'alpha' and version_info[4] == 0:
        # TODO: maybe append some sort of git info here??
        sub = '.dev'
    elif version_info[3] != 'final':
        mapping = {'alpha': 'a', 'beta': 'b', 'rc': 'c'}
        sub = mapping[version_info[3]] + str(version_info[4])

    return str(main + sub)

version = _get_version()

########NEW FILE########
__FILENAME__ = run-tests
#!/usr/bin/env python

import tests
import os, sys

if len(sys.argv) > 1 and sys.argv[1] == "update":
    if len(sys.argv) > 2:
        config = tests.get_config(os.path.dirname(sys.argv[2]))
        root, ext = os.path.splitext(sys.argv[2])
        if ext == config.get(tests.get_section(os.path.basename(root), config), 'input_ext'):
            tests.generate(root, config)
        else:
            print(sys.argv[2], 'does not have a valid file extension. Check config.')
    else:
        tests.generate_all()
else:
    tests.run()

########NEW FILE########
__FILENAME__ = plugins
import traceback
from .util import MarkdownSyntaxError
from nose.plugins import Plugin
from nose.plugins.errorclass import ErrorClass, ErrorClassPlugin

class Markdown(ErrorClassPlugin):
    """ Add MarkdownSyntaxError and ensure proper formatting. """
    mdsyntax = ErrorClass(MarkdownSyntaxError, 
                          label='MarkdownSyntaxError', 
                          isfailure=True)
    enabled = True

    def configure(self, options, conf):
        self.conf = conf

    def addError(self, test, err):
        """ Ensure other plugins see the error by returning nothing here. """
        pass

    def formatError(self, test, err):
        """ Remove unnessecary and unhelpful traceback from error report. """
        et, ev, tb = err
        if et.__name__ == 'MarkdownSyntaxError':
            return et, ev, ''
        return err


def escape(html):
    """ Escape HTML for display as source within HTML. """
    html = html.replace('&', '&amp;')
    html = html.replace('<', '&lt;')
    html = html.replace('>', '&gt;')
    return html


class HtmlOutput(Plugin):
    """Output test results as ugly, unstyled html. """
    
    name = 'html-output'
    score = 2 # run late
    enabled = True
    
    def __init__(self):
        super(HtmlOutput, self).__init__()
        self.html = [ '<html><head>',
                      '<title>Test output</title>',
                      '</head><body>' ]
   
    def configure(self, options, conf):
        self.conf = conf

    def addSuccess(self, test):
        self.html.append('<span>ok</span>')
    
    def addError(self, test, err):
        err = self.formatErr(err)
        self.html.append('<span>ERROR</span>')
        self.html.append('<pre>%s</pre>' % escape(err))
            
    def addFailure(self, test, err):
        err = self.formatErr(err)
        self.html.append('<span>FAIL</span>')
        self.html.append('<pre>%s</pre>' % escape(err))

    def finalize(self, result):
        self.html.append('<div>')
        self.html.append("Ran %d test%s" %
                         (result.testsRun, result.testsRun != 1 and "s" 
or ""))
        self.html.append('</div>')
        self.html.append('<div>')
        if not result.wasSuccessful():
            self.html.extend(['<span>FAILED (',
                              'failures=%d ' % len(result.failures),
                              'errors=%d' % len(result.errors)])
            for cls in list(result.errorClasses.keys()):
                storage, label, isfail = result.errorClasses[cls]
                if len(storage):
                    self.html.append(' %ss=%d' % (label, len(storage)))
            self.html.append(')</span>')
        else:
            self.html.append('OK')
        self.html.append('</div></body></html>')
        f = open('test-output.html', 'w')
        for l in self.html:
            f.write(l)
        f.close()

    def formatErr(self, err):
        exctype, value, tb = err
        return ''.join(traceback.format_exception(exctype, value, tb))
    
    def startContext(self, ctx):
        try:
            n = ctx.__name__
        except AttributeError:
            n = str(ctx).replace('<', '').replace('>', '')
        self.html.extend(['<fieldset>', '<legend>', n, '</legend>'])
        try:
            path = ctx.__file__.replace('.pyc', '.py')
            self.html.extend(['<div>', path, '</div>'])
        except AttributeError:
            pass

    def stopContext(self, ctx):
        self.html.append('</fieldset>')
    
    def startTest(self, test):
        self.html.extend([ '<div><span>',
                           test.shortDescription() or str(test),
                           '</span>' ])
        
    def stopTest(self, test):
        self.html.append('</div>')


########NEW FILE########
__FILENAME__ = test_apis
#!/usr/bin/python
"""
Python-Markdown Regression Tests
================================

Tests of the various APIs with the python markdown lib.

"""

from __future__ import unicode_literals
import unittest
import sys
import types
import markdown
import warnings

PY3 = sys.version_info[0] == 3

class TestMarkdownBasics(unittest.TestCase):
    """ Tests basics of the Markdown class. """

    def setUp(self):
        """ Create instance of Markdown. """
        self.md = markdown.Markdown()

    def testBlankInput(self):
        """ Test blank input. """
        self.assertEqual(self.md.convert(''), '')

    def testWhitespaceOnly(self):
        """ Test input of only whitespace. """
        self.assertEqual(self.md.convert(' '), '')

    def testSimpleInput(self):
        """ Test simple input. """
        self.assertEqual(self.md.convert('foo'), '<p>foo</p>')

class TestBlockParser(unittest.TestCase):
    """ Tests of the BlockParser class. """

    def setUp(self):
        """ Create instance of BlockParser. """
        self.parser = markdown.Markdown().parser

    def testParseChunk(self):
        """ Test BlockParser.parseChunk. """
        root = markdown.util.etree.Element("div")
        text = 'foo'
        self.parser.parseChunk(root, text)
        self.assertEqual(markdown.serializers.to_xhtml_string(root), 
                         "<div><p>foo</p></div>")

    def testParseDocument(self):
        """ Test BlockParser.parseDocument. """
        lines = ['#foo', '', 'bar', '', '    baz']
        tree = self.parser.parseDocument(lines)
        self.assertTrue(isinstance(tree, markdown.util.etree.ElementTree))
        self.assertTrue(markdown.util.etree.iselement(tree.getroot()))
        self.assertEqual(markdown.serializers.to_xhtml_string(tree.getroot()),
            "<div><h1>foo</h1><p>bar</p><pre><code>baz\n</code></pre></div>")


class TestBlockParserState(unittest.TestCase):
    """ Tests of the State class for BlockParser. """

    def setUp(self):
        self.state = markdown.blockparser.State()

    def testBlankState(self):
        """ Test State when empty. """
        self.assertEqual(self.state, [])

    def testSetSate(self):
        """ Test State.set(). """
        self.state.set('a_state')
        self.assertEqual(self.state, ['a_state'])
        self.state.set('state2')
        self.assertEqual(self.state, ['a_state', 'state2'])

    def testIsSate(self):
        """ Test State.isstate(). """
        self.assertEqual(self.state.isstate('anything'), False)
        self.state.set('a_state')
        self.assertEqual(self.state.isstate('a_state'), True)
        self.state.set('state2')
        self.assertEqual(self.state.isstate('state2'), True)
        self.assertEqual(self.state.isstate('a_state'), False)
        self.assertEqual(self.state.isstate('missing'), False)

    def testReset(self):
        """ Test State.reset(). """
        self.state.set('a_state')
        self.state.reset()
        self.assertEqual(self.state, [])
        self.state.set('state1')
        self.state.set('state2')
        self.state.reset()
        self.assertEqual(self.state, ['state1'])

class TestHtmlStash(unittest.TestCase):
    """ Test Markdown's HtmlStash. """
    
    def setUp(self):
        self.stash = markdown.util.HtmlStash()
        self.placeholder = self.stash.store('foo')

    def testSimpleStore(self):
        """ Test HtmlStash.store. """
        self.assertEqual(self.placeholder, self.stash.get_placeholder(0))
        self.assertEqual(self.stash.html_counter, 1)
        self.assertEqual(self.stash.rawHtmlBlocks, [('foo', False)])

    def testStoreMore(self):
        """ Test HtmlStash.store with additional blocks. """
        placeholder = self.stash.store('bar')
        self.assertEqual(placeholder, self.stash.get_placeholder(1))
        self.assertEqual(self.stash.html_counter, 2)
        self.assertEqual(self.stash.rawHtmlBlocks, 
                        [('foo', False), ('bar', False)])

    def testSafeStore(self):
        """ Test HtmlStash.store with 'safe' html. """
        self.stash.store('bar', True)
        self.assertEqual(self.stash.rawHtmlBlocks, 
                        [('foo', False), ('bar', True)])

    def testReset(self):
        """ Test HtmlStash.reset. """
        self.stash.reset()
        self.assertEqual(self.stash.html_counter, 0)
        self.assertEqual(self.stash.rawHtmlBlocks, [])

class TestOrderedDict(unittest.TestCase):
    """ Test OrderedDict storage class. """

    def setUp(self):
        self.odict = markdown.odict.OrderedDict()
        self.odict['first'] = 'This'
        self.odict['third'] = 'a'
        self.odict['fourth'] = 'self'
        self.odict['fifth'] = 'test'

    def testValues(self):
        """ Test output of OrderedDict.values(). """
        self.assertEqual(list(self.odict.values()), ['This', 'a', 'self', 'test'])

    def testKeys(self):
        """ Test output of OrderedDict.keys(). """
        self.assertEqual(list(self.odict.keys()),
                    ['first', 'third', 'fourth', 'fifth'])

    def testItems(self):
        """ Test output of OrderedDict.items(). """
        self.assertEqual(list(self.odict.items()),
                    [('first', 'This'), ('third', 'a'), 
                    ('fourth', 'self'), ('fifth', 'test')])

    def testAddBefore(self):
        """ Test adding an OrderedDict item before a given key. """
        self.odict.add('second', 'is', '<third')
        self.assertEqual(list(self.odict.items()),
                    [('first', 'This'), ('second', 'is'), ('third', 'a'), 
                    ('fourth', 'self'), ('fifth', 'test')])

    def testAddAfter(self):
        """ Test adding an OrderDict item after a given key. """
        self.odict.add('second', 'is', '>first')
        self.assertEqual(list(self.odict.items()),
                    [('first', 'This'), ('second', 'is'), ('third', 'a'), 
                    ('fourth', 'self'), ('fifth', 'test')])

    def testAddAfterEnd(self):
        """ Test adding an OrderedDict item after the last key. """
        self.odict.add('sixth', '.', '>fifth')
        self.assertEqual(list(self.odict.items()),
                    [('first', 'This'), ('third', 'a'), 
                    ('fourth', 'self'), ('fifth', 'test'), ('sixth', '.')])

    def testAdd_begin(self):
        """ Test adding an OrderedDict item using "_begin". """
        self.odict.add('zero', 'CRAZY', '_begin')
        self.assertEqual(list(self.odict.items()),
                    [('zero', 'CRAZY'), ('first', 'This'), ('third', 'a'), 
                    ('fourth', 'self'), ('fifth', 'test')])

    def testAdd_end(self):
        """ Test adding an OrderedDict item using "_end". """
        self.odict.add('sixth', '.', '_end')
        self.assertEqual(list(self.odict.items()),
                    [('first', 'This'), ('third', 'a'), 
                    ('fourth', 'self'), ('fifth', 'test'), ('sixth', '.')])

    def testAddBadLocation(self):
        """ Test Error on bad location in OrderedDict.add(). """
        self.assertRaises(ValueError, self.odict.add, 'sixth', '.', '<seventh')
        self.assertRaises(ValueError, self.odict.add, 'second', 'is', 'third')

    def testDeleteItem(self):
        """ Test deletion of an OrderedDict item. """
        del self.odict['fourth']
        self.assertEqual(list(self.odict.items()),
                    [('first', 'This'), ('third', 'a'), ('fifth', 'test')])

    def testChangeValue(self):
        """ Test OrderedDict change value. """
        self.odict['fourth'] = 'CRAZY'
        self.assertEqual(list(self.odict.items()),
                    [('first', 'This'), ('third', 'a'), 
                    ('fourth', 'CRAZY'), ('fifth', 'test')])

    def testChangeOrder(self):
        """ Test OrderedDict change order. """
        self.odict.link('fourth', '<third')
        self.assertEqual(list(self.odict.items()),
                    [('first', 'This'), ('fourth', 'self'),
                    ('third', 'a'), ('fifth', 'test')])

    def textBadLink(self):
        """ Test OrderedDict change order with bad location. """
        self.assertRaises(ValueError, self.odict.link('fourth', '<bad'))
        # Check for data integrity ("fourth" wasn't deleted).'
        self.assertEqual(list(self.odict.items()),
                    [('first', 'This'), ('third', 'a'), 
                    ('fourth', 'self'), ('fifth', 'test')])

class TestErrors(unittest.TestCase):
    """ Test Error Reporting. """

    def setUp(self):
        # Set warnings to be raised as errors
        warnings.simplefilter('error')

    def tearDown(self):
        # Reset warning behavior back to default
        warnings.simplefilter('default')

    def testNonUnicodeSource(self):
        """ Test falure on non-unicode source text. """
        if sys.version_info < (3, 0):
            source = "foo".encode('utf-16') 
            self.assertRaises(UnicodeDecodeError, markdown.markdown, source)

    def testBadOutputFormat(self):
        """ Test failure on bad output_format. """
        self.assertRaises(KeyError, markdown.Markdown, output_format='invalid')

    def testLoadExtensionFailure(self):
        """ Test failure of an extension to load. """
        self.assertRaises(ImportError, 
                        markdown.Markdown, extensions=['non_existant_ext']) 

    def testLoadBadExtension(self):
        """ Test loading of an Extension with no makeExtension function. """
        _create_fake_extension(name='fake', has_factory_func=False)
        self.assertRaises(AttributeError, markdown.Markdown, extensions=['fake'])

    def testNonExtension(self):
        """ Test loading a non Extension object as an extension. """
        _create_fake_extension(name='fake', is_wrong_type=True)
        self.assertRaises(TypeError, markdown.Markdown, extensions=['fake'])

    def testBaseExtention(self):
        """ Test that the base Extension class will raise NotImplemented. """
        _create_fake_extension(name='fake')
        self.assertRaises(NotImplementedError, 
                        markdown.Markdown, extensions=['fake'])


def _create_fake_extension(name, has_factory_func=True, is_wrong_type=False):
    """ Create a fake extension module for testing. """
    mod_name = '_'.join(['mdx', name])
    if not PY3:
        # mod_name must be bytes in Python 2.x
        mod_name = bytes(mod_name)
    ext_mod = types.ModuleType(mod_name)
    def makeExtension(configs=None):
        if is_wrong_type:
            return object
        else:
            return markdown.extensions.Extension(configs=configs)
    if has_factory_func:
        ext_mod.makeExtension = makeExtension
    # Warning: this brute forces the extenson module onto the system. Either 
    # this needs to be specificly overriden or a new python session needs to 
    # be started to get rid of this. This should be ok in a testing context.
    sys.modules[mod_name] =  ext_mod


class testETreeComments(unittest.TestCase):
    """ 
    Test that ElementTree Comments work.

    These tests should only be a concern when using cElementTree with third
    party serializers (including markdown's (x)html serializer). While markdown
    doesn't use ElementTree.Comment itself, we should certainly support any
    third party extensions which may. Therefore, these tests are included to
    ensure such support is maintained.
    """

    def setUp(self):
        # Create comment node
        self.comment = markdown.util.etree.Comment('foo')
        if hasattr(markdown.util.etree, 'test_comment'):
            self.test_comment = markdown.util.etree.test_comment
        else:
            self.test_comment = markdown.util.etree.Comment

    def testCommentIsComment(self):
        """ Test that an ElementTree Comment passes the `is Comment` test. """
        self.assertTrue(self.comment.tag is markdown.util.etree.test_comment)

    def testCommentIsBlockLevel(self):
        """ Test that an ElementTree Comment is recognized as BlockLevel. """
        self.assertFalse(markdown.util.isBlockLevel(self.comment.tag))

    def testCommentSerialization(self):
        """ Test that an ElementTree Comment serializes properly. """
        self.assertEqual(markdown.serializers.to_html_string(self.comment),
                    '<!--foo-->')

    def testCommentPrettify(self):
        """ Test that an ElementTree Comment is prettified properly. """
        pretty = markdown.treeprocessors.PrettifyTreeprocessor()
        pretty.run(self.comment)
        self.assertEqual(markdown.serializers.to_html_string(self.comment),
                    '<!--foo-->\n')


class testSerializers(unittest.TestCase):
    """ Test the html and xhtml serializers. """

    def testHtml(self):
        """ Test HTML serialization. """
        el = markdown.util.etree.Element('div')
        p = markdown.util.etree.SubElement(el, 'p')
        p.text = 'foo'
        hr = markdown.util.etree.SubElement(el, 'hr')
        self.assertEqual(markdown.serializers.to_html_string(el),
                    '<div><p>foo</p><hr></div>')

    def testXhtml(self):
        """" Test XHTML serialization. """
        el = markdown.util.etree.Element('div')
        p = markdown.util.etree.SubElement(el, 'p')
        p.text = 'foo'
        hr = markdown.util.etree.SubElement(el, 'hr')
        self.assertEqual(markdown.serializers.to_xhtml_string(el),
                    '<div><p>foo</p><hr /></div>')

    def testMixedCaseTags(self):
        """" Test preservation of tag case. """
        el = markdown.util.etree.Element('MixedCase')
        el.text = 'not valid '
        em = markdown.util.etree.SubElement(el, 'EMPHASIS')
        em.text = 'html'
        hr = markdown.util.etree.SubElement(el, 'HR')
        self.assertEqual(markdown.serializers.to_xhtml_string(el),
                    '<MixedCase>not valid <EMPHASIS>html</EMPHASIS><HR /></MixedCase>')


    def buildExtension(self):
        """ Build an extension which registers fakeSerializer. """
        def fakeSerializer(elem):
            # Ignore input and return hardcoded output
            return '<div><p>foo</p></div>'

        class registerFakeSerializer(markdown.extensions.Extension):
            def extendMarkdown(self, md, md_globals):
                md.output_formats['fake'] = fakeSerializer

        return registerFakeSerializer()

    def testRegisterSerializer(self):
        self.assertEqual(markdown.markdown('baz', 
                extensions=[self.buildExtension()], output_format='fake'),
                    '<p>foo</p>')


class testAtomicString(unittest.TestCase):
    """ Test that AtomicStrings are honored (not parsed). """

    def setUp(self):
        md = markdown.Markdown()
        self.inlineprocessor = md.treeprocessors['inline']

    def testString(self):
        """ Test that a regular string is parsed. """
        tree = markdown.util.etree.Element('div')
        p = markdown.util.etree.SubElement(tree, 'p')
        p.text = 'some *text*'
        new = self.inlineprocessor.run(tree)
        self.assertEqual(markdown.serializers.to_html_string(new), 
                    '<div><p>some <em>text</em></p></div>')

    def testSimpleAtomicString(self):
        """ Test that a simple AtomicString is not parsed. """
        tree = markdown.util.etree.Element('div')
        p = markdown.util.etree.SubElement(tree, 'p')
        p.text = markdown.util.AtomicString('some *text*')
        new = self.inlineprocessor.run(tree)
        self.assertEqual(markdown.serializers.to_html_string(new), 
                    '<div><p>some *text*</p></div>')

    def testNestedAtomicString(self):
        """ Test that a nested AtomicString is not parsed. """
        tree = markdown.util.etree.Element('div')
        p = markdown.util.etree.SubElement(tree, 'p')
        p.text = markdown.util.AtomicString('*some* ')
        span1 = markdown.util.etree.SubElement(p, 'span')
        span1.text = markdown.util.AtomicString('*more* ')
        span2 = markdown.util.etree.SubElement(span1, 'span')
        span2.text = markdown.util.AtomicString('*text* ')
        span3 = markdown.util.etree.SubElement(span2, 'span')
        span3.text = markdown.util.AtomicString('*here*')
        span3.tail = markdown.util.AtomicString(' *to*')
        span2.tail = markdown.util.AtomicString(' *test*')
        span1.tail = markdown.util.AtomicString(' *with*')
        new = self.inlineprocessor.run(tree)
        self.assertEqual(markdown.serializers.to_html_string(new), 
            '<div><p>*some* <span>*more* <span>*text* <span>*here*</span> '
            '*to*</span> *test*</span> *with*</p></div>')

class TestConfigParsing(unittest.TestCase):
    def assertParses(self, value, result):
        self.assertTrue(markdown.util.parseBoolValue(value, False) is result)

    def testBooleansParsing(self):
        self.assertParses(True, True)
        self.assertParses('novalue', None)
        self.assertParses('yES', True)
        self.assertParses('FALSE', False)
        self.assertParses(0., False)

    def testInvalidBooleansParsing(self):
        self.assertRaises(ValueError, markdown.util.parseBoolValue, 'novalue')

########NEW FILE########
__FILENAME__ = test_extensions
"""
Python-Markdown Extension Regression Tests
==========================================

A collection of regression tests to confirm that the included extensions
continue to work as advertised. This used to be accomplished by doctests.

"""

from __future__ import unicode_literals
import unittest
import markdown

class TestAbbr(unittest.TestCase):
    """ Test abbr extension. """

    def setUp(self):
        self.md = markdown.Markdown(extensions=['abbr'])

    def testSimpleAbbr(self):
        """ Test Abbreviations. """
        text = 'Some text with an ABBR and a REF. Ignore REFERENCE and ref.' + \
               '\n\n*[ABBR]: Abbreviation\n' + \
               '*[REF]: Abbreviation Reference'
        self.assertEqual(self.md.convert(text),
            '<p>Some text with an <abbr title="Abbreviation">ABBR</abbr> '
            'and a <abbr title="Abbreviation Reference">REF</abbr>. Ignore '
            'REFERENCE and ref.</p>')

    def testNestedAbbr(self):
        """ Test Nested Abbreviations. """
        text = '[ABBR](/foo) and _ABBR_\n\n' + \
               '*[ABBR]: Abreviation'
        self.assertEqual(self.md.convert(text),
            '<p><a href="/foo"><abbr title="Abreviation">ABBR</abbr></a> '
            'and <em><abbr title="Abreviation">ABBR</abbr></em></p>')


class TestCodeHilite(unittest.TestCase):
    """ Test codehilite extension. """

    def setUp(self):
        self.has_pygments = True
        try:
            import pygments
        except ImportError:
            self.has_pygments = False

    def testBasicCodeHilite(self):
        text = '\t# A Code Comment'
        md = markdown.Markdown(extensions=['codehilite'])
        if self.has_pygments:
            self.assertEqual(md.convert(text),
                '<div class="codehilite">'
                '<pre><span class="c"># A Code Comment</span>\n'
                '</pre></div>')
        else:
            self.assertEqual(md.convert(text),
                '<pre class="codehilite"><code># A Code Comment'
                '</code></pre>')
    
    def testLinenumsTrue(self):
        text = '\t# A Code Comment'
        md = markdown.Markdown(extensions=['codehilite(linenums=True)'])
        if self.has_pygments:
            # Differant versions of pygments output slightly different markup.
            # So we use 'startwith' and test just enough to confirm that 
            # pygments received and processed linenums.
            self.assertTrue(md.convert(text).startswith(
                '<table class="codehilitetable"><tr><td class="linenos">'))
        else:
            self.assertEqual(md.convert(text),
                '<pre class="codehilite"><code class="linenums"># A Code Comment'
                '</code></pre>')

    def testLinenumsFalse(self):
        text = '\t#!Python\n\t# A Code Comment'
        md = markdown.Markdown(extensions=['codehilite(linenums=False)'])
        if self.has_pygments:
            self.assertEqual(md.convert(text),
                '<div class="codehilite">'
                '<pre><span class="c"># A Code Comment</span>\n'
                '</pre></div>')
        else:
            self.assertEqual(md.convert(text),
                '<pre class="codehilite"><code class="language-python"># A Code Comment'
                '</code></pre>')

    def testLinenumsNone(self):
        text = '\t# A Code Comment'
        md = markdown.Markdown(extensions=['codehilite(linenums=None)'])
        if self.has_pygments:
            self.assertEqual(md.convert(text),
                '<div class="codehilite">'
                '<pre><span class="c"># A Code Comment</span>\n'
                '</pre></div>')
        else:
            self.assertEqual(md.convert(text),
                '<pre class="codehilite"><code># A Code Comment'
                '</code></pre>')

    def testLinenumsNoneWithShebang(self):
        text = '\t#!Python\n\t# A Code Comment'
        md = markdown.Markdown(extensions=['codehilite(linenums=None)'])
        if self.has_pygments:
            # Differant versions of pygments output slightly different markup.
            # So we use 'startwith' and test just enough to confirm that 
            # pygments received and processed linenums.
            self.assertTrue(md.convert(text).startswith(
                '<table class="codehilitetable"><tr><td class="linenos">'))
        else:
            self.assertEqual(md.convert(text),
                '<pre class="codehilite"><code class="language-python linenums"># A Code Comment'
                '</code></pre>')

    def testLinenumsNoneWithColon(self):
        text = '\t:::Python\n\t# A Code Comment'
        md = markdown.Markdown(extensions=['codehilite(linenums=None)'])
        if self.has_pygments:
            self.assertEqual(md.convert(text),
                '<div class="codehilite">'
                '<pre><span class="c"># A Code Comment</span>\n'
                '</pre></div>')
        else:
            self.assertEqual(md.convert(text),
                '<pre class="codehilite"><code class="language-python"># A Code Comment'
                '</code></pre>')

    def testHighlightLinesWithColon(self):
        # Test with hl_lines delimited by single or double quotes.
        text0 = '\t:::Python hl_lines="2"\n\t#line 1\n\t#line 2\n\t#line 3'
        text1 = "\t:::Python hl_lines='2'\n\t#line 1\n\t#line 2\n\t#line 3"

        for text in (text0, text1):
            md = markdown.Markdown(extensions=['codehilite'])
            if self.has_pygments:
                self.assertEqual(md.convert(text),
                    '<div class="codehilite"><pre>'
                    '<span class="c">#line 1</span>\n'
                    '<span class="hll"><span class="c">#line 2</span>\n</span>'
                    '<span class="c">#line 3</span>\n'
                    '</pre></div>')
            else:
                self.assertEqual(md.convert(text),
                    '<pre class="codehilite">'
                    '<code class="language-python">#line 1\n'
                    '#line 2\n'
                    '#line 3</code></pre>')

class TestFencedCode(unittest.TestCase):
    """ Test fenced_code extension. """

    def setUp(self):
        self.md = markdown.Markdown(extensions=['fenced_code'])
        self.has_pygments = True
        try:
            import pygments
        except ImportError:
            self.has_pygments = False

    def testBasicFence(self):
        """ Test Fenced Code Blocks. """
        text = '''
A paragraph before a fenced code block:

~~~
Fenced code block
~~~'''
        self.assertEqual(self.md.convert(text),
            '<p>A paragraph before a fenced code block:</p>\n'
            '<pre><code>Fenced code block\n'
            '</code></pre>')

    def testSafeFence(self):
        """ Test Fenced Code with safe_mode. """
        text = '~~~\nCode\n~~~'
        self.md.safeMode = 'replace'
        self.assertEqual(self.md.convert(text),
            '<pre><code>Code\n'
            '</code></pre>')

    def testNestedFence(self):
        """ Test nested fence. """

        text = '''
~~~~~~~~

~~~~
~~~~~~~~'''
        self.assertEqual(self.md.convert(text),
            '<pre><code>\n'
            '~~~~\n'
            '</code></pre>')

    def testFencedLanguage(self):
        """ Test Language Tags. """

        text = '''
~~~~{.python}
# Some python code
~~~~'''
        self.assertEqual(self.md.convert(text),
            '<pre><code class="python"># Some python code\n'
            '</code></pre>')

    def testFencedBackticks(self):
        """ Test Code Fenced with Backticks. """

        text = '''
`````
# Arbitrary code
~~~~~ # these tildes will not close the block
`````'''
        self.assertEqual(self.md.convert(text),
        '<pre><code># Arbitrary code\n'
        '~~~~~ # these tildes will not close the block\n'
        '</code></pre>')

    def testFencedCodeWithHighlightLines(self):
        """ Test Fenced Code with Highlighted Lines. """

        text = '''
```hl_lines="1 3"
line 1
line 2
line 3
```'''
        md = markdown.Markdown(extensions=[
            'codehilite(linenums=None,guess_lang=False)',
            'fenced_code'])

        if self.has_pygments:
            self.assertEqual(md.convert(text),
                '<div class="codehilite"><pre>'
                '<span class="hll">line 1\n</span>'
                'line 2\n'
                '<span class="hll">line 3\n</span>'
                '</pre></div>')
        else:
            self.assertEqual(md.convert(text),
                '<pre class="codehilite"><code>line 1\n'
                'line 2\n'
                'line 3</code></pre>')

    def testFencedLanguageAndHighlightLines(self):
        """ Test Fenced Code with Highlighted Lines. """

        text0 = '''
```.python hl_lines="1 3"
#line 1
#line 2
#line 3
```'''
        text1 = '''
~~~{.python hl_lines='1 3'}
#line 1
#line 2
#line 3
~~~'''
        for text in (text0, text1):
            md = markdown.Markdown(extensions=[
                'codehilite(linenums=None,guess_lang=False)',
                'fenced_code'])

            if self.has_pygments:
                self.assertEqual(md.convert(text),
                    '<div class="codehilite"><pre>'
                    '<span class="hll"><span class="c">#line 1</span>\n</span>'
                    '<span class="c">#line 2</span>\n'
                    '<span class="hll"><span class="c">#line 3</span>\n</span>'
                    '</pre></div>')
            else:
                self.assertEqual(md.convert(text),
                    '<pre class="codehilite"><code class="language-python">#line 1\n'
                    '#line 2\n'
                    '#line 3</code></pre>')

class TestHeaderId(unittest.TestCase):
    """ Test HeaderId Extension. """

    def setUp(self):
        self.md = markdown.Markdown(extensions=['headerid'])

    def testBasicHeaderId(self):
        """ Test Basic HeaderID """

        text = "# Some Header #"
        self.assertEqual(self.md.convert(text),
            '<h1 id="some-header">Some Header</h1>')

    def testUniqueFunc(self):
        """ Test 'unique' function. """
        from markdown.extensions.headerid import unique
        ids = set(['foo'])
        self.assertEqual(unique('foo', ids), 'foo_1')
        self.assertEqual(ids, set(['foo', 'foo_1']))

    def testUniqueIds(self):
        """ Test Unique IDs. """

        text = '#Header\n#Header\n#Header'
        self.assertEqual(self.md.convert(text),
            '<h1 id="header">Header</h1>\n'
            '<h1 id="header_1">Header</h1>\n'
            '<h1 id="header_2">Header</h1>')

    def testBaseLevel(self):
        """ Test Header Base Level. """

        text = '#Some Header\n## Next Level'
        self.assertEqual(markdown.markdown(text, ['headerid(level=3)']),
            '<h3 id="some-header">Some Header</h3>\n'
            '<h4 id="next-level">Next Level</h4>')

    def testHeaderInlineMarkup(self):
        """ Test Header IDs with inline markup. """

        text = '#Some *Header* with [markup](http://example.com).'
        self.assertEqual(self.md.convert(text),
            '<h1 id="some-header-with-markup">Some <em>Header</em> with '
            '<a href="http://example.com">markup</a>.</h1>')

    def testHtmlEntities(self):
        """ Test HeaderIDs with HTML Entities. """
        text = '# Foo &amp; bar'
        self.assertEqual(self.md.convert(text),
            '<h1 id="foo-bar">Foo &amp; bar</h1>')

    def testRawHtml(self):
        """ Test HeaderIDs with raw HTML. """
        text = '# Foo <b>Bar</b> Baz.'
        self.assertEqual(self.md.convert(text),
            '<h1 id="foo-bar-baz">Foo <b>Bar</b> Baz.</h1>')

    def testNoAutoIds(self):
        """ Test HeaderIDs with no auto generated IDs. """

        text = '# Some Header\n# Another Header'
        self.assertEqual(markdown.markdown(text, ['headerid(forceid=False)']),
            '<h1>Some Header</h1>\n'
            '<h1>Another Header</h1>')

    def testHeaderIdWithMetaData(self):
        """ Test Header IDs with MetaData extension. """

        text = '''header_level: 2
header_forceid: Off

# A Header'''
        self.assertEqual(markdown.markdown(text, ['headerid', 'meta']),
            '<h2>A Header</h2>')

    def testHeaderIdWithAttr_List(self):
        """ Test HeaderIDs with Attr_List extension. """
        
        text = '# Header1 {: #foo }\n# Header2 {: .bar }'
        self.assertEqual(markdown.markdown(text, ['headerid', 'attr_list']),
            '<h1 id="foo">Header1</h1>\n'
            '<h1 class="bar" id="header2">Header2</h1>')
        # Switch order extensions are loaded - should be no change in behavior.
        self.assertEqual(markdown.markdown(text, ['attr_list', 'headerid']),
            '<h1 id="foo">Header1</h1>\n'
            '<h1 class="bar" id="header2">Header2</h1>')

class TestMetaData(unittest.TestCase):
    """ Test MetaData extension. """

    def setUp(self):
        self.md = markdown.Markdown(extensions=['meta'])

    def testBasicMetaData(self):
        """ Test basic metadata. """

        text = '''Title: A Test Doc.
Author: Waylan Limberg
        John Doe
Blank_Data:

The body. This is paragraph one.'''
        self.assertEqual(self.md.convert(text),
            '<p>The body. This is paragraph one.</p>')
        self.assertEqual(self.md.Meta,
            {'author': ['Waylan Limberg', 'John Doe'],
             'blank_data': [''],
             'title': ['A Test Doc.']})

    def testMissingMetaData(self):
        """ Test document without Meta Data. """

        text = '    Some Code - not extra lines of meta data.'
        self.assertEqual(self.md.convert(text),
            '<pre><code>Some Code - not extra lines of meta data.\n'
            '</code></pre>')
        self.assertEqual(self.md.Meta, {})

    def testMetaDataWithoutNewline(self):
        """ Test doocument with only metadata and no newline at end."""
        text = 'title: No newline'
        self.assertEqual(self.md.convert(text), '')
        self.assertEqual(self.md.Meta, {'title': ['No newline']})


class TestWikiLinks(unittest.TestCase):
    """ Test Wikilinks Extension. """

    def setUp(self):
        self.md = markdown.Markdown(extensions=['wikilinks'])
        self.text = "Some text with a [[WikiLink]]."

    def testBasicWikilinks(self):
        """ Test [[wikilinks]]. """

        self.assertEqual(self.md.convert(self.text),
            '<p>Some text with a '
            '<a class="wikilink" href="/WikiLink/">WikiLink</a>.</p>')

    def testWikilinkWhitespace(self):
        """ Test whitespace in wikilinks. """
        self.assertEqual(self.md.convert('[[ foo bar_baz ]]'),
            '<p><a class="wikilink" href="/foo_bar_baz/">foo bar_baz</a></p>')
        self.assertEqual(self.md.convert('foo [[ ]] bar'),
            '<p>foo  bar</p>')

    def testSimpleSettings(self):
        """ Test Simple Settings. """

        self.assertEqual(markdown.markdown(self.text,
            ['wikilinks(base_url=/wiki/,end_url=.html,html_class=foo)']),
            '<p>Some text with a '
            '<a class="foo" href="/wiki/WikiLink.html">WikiLink</a>.</p>')

    def testComplexSettings(self):
        """ Test Complex Settings. """

        md = markdown.Markdown(
            extensions = ['wikilinks'],
            extension_configs = {'wikilinks': [
                                        ('base_url', 'http://example.com/'),
                                        ('end_url', '.html'),
                                        ('html_class', '') ]},
            safe_mode = True)
        self.assertEqual(md.convert(self.text),
            '<p>Some text with a '
            '<a href="http://example.com/WikiLink.html">WikiLink</a>.</p>')

    def testWikilinksMetaData(self):
        """ test MetaData with Wikilinks Extension. """

        text = """wiki_base_url: http://example.com/
wiki_end_url:   .html
wiki_html_class:

Some text with a [[WikiLink]]."""
        md = markdown.Markdown(extensions=['meta', 'wikilinks'])
        self.assertEqual(md.convert(text),
            '<p>Some text with a '
            '<a href="http://example.com/WikiLink.html">WikiLink</a>.</p>')

        # MetaData should not carry over to next document:
        self.assertEqual(md.convert("No [[MetaData]] here."),
            '<p>No <a class="wikilink" href="/MetaData/">MetaData</a> '
            'here.</p>')

    def testURLCallback(self):
        """ Test used of a custom URL builder. """

        def my_url_builder(label, base, end):
            return '/bar/'
        md = markdown.Markdown(extensions=['wikilinks'],
            extension_configs={'wikilinks' : [('build_url', my_url_builder)]})
        self.assertEqual(md.convert('[[foo]]'),
            '<p><a class="wikilink" href="/bar/">foo</a></p>')

class TestAdmonition(unittest.TestCase):
    """ Test Admonition Extension. """

    def setUp(self):
        self.md = markdown.Markdown(extensions=['admonition'])

    def testRE(self):
        RE = self.md.parser.blockprocessors['admonition'].RE
        tests = [
            ('!!! note', ('note', None)),
            ('!!! note "Please Note"', ('note', 'Please Note')),
            ('!!! note ""', ('note', '')),
        ]
        for test, expected in tests:
            self.assertEqual(RE.match(test).groups(), expected)

class TestTOC(unittest.TestCase):
    """ Test TOC Extension. """
    
    def setUp(self):
        self.md = markdown.Markdown(extensions=['toc'])

    def testMarker(self):
        """ Test TOC with a Marker. """
        text = '[TOC]\n\n# Header 1\n\n## Header 2'
        self.assertEqual(self.md.convert(text),
            '<div class="toc">\n'
              '<ul>\n'
                '<li><a href="#header-1">Header 1</a>'
                  '<ul>\n'
                    '<li><a href="#header-2">Header 2</a></li>\n'
                  '</ul>\n'
                '</li>\n'
              '</ul>\n'
            '</div>\n'
            '<h1 id="header-1">Header 1</h1>\n'
            '<h2 id="header-2">Header 2</h2>')
    
    def testNoMarker(self):
        """ Test TOC without a Marker. """
        text = '# Header 1\n\n## Header 2'
        self.assertEqual(self.md.convert(text),
            '<h1 id="header-1">Header 1</h1>\n'
            '<h2 id="header-2">Header 2</h2>')
        self.assertEqual(self.md.toc,
            '<div class="toc">\n'
              '<ul>\n'
                '<li><a href="#header-1">Header 1</a>'
                  '<ul>\n'
                    '<li><a href="#header-2">Header 2</a></li>\n'
                  '</ul>\n'
                '</li>\n'
              '</ul>\n'
            '</div>\n')

########NEW FILE########
__FILENAME__ = util
import sys
if sys.version_info[0] == 3:
    from configparser import ConfigParser
else:
    from ConfigParser import SafeConfigParser as ConfigParser

class MarkdownSyntaxError(Exception):
    pass


class CustomConfigParser(ConfigParser):
    def get(self, section, option):
        value = ConfigParser.get(self, section, option)
        if option == 'extensions':
            if len(value.strip()):
                return value.split(',')
            else:
                return []
        if value.lower() in ['yes', 'true', 'on', '1']:
            return True
        if value.lower() in ['no', 'false', 'off', '0']:
            return False
        return value

########NEW FILE########
