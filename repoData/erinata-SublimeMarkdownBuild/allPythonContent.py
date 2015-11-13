__FILENAME__ = MarkdownBuild
import sublime
import sublime_plugin
import markdown_python
import os
import tempfile
import webbrowser
#import ctypes
#from functools import partial


# TODO: set focus back to sublime after build
# TODO: option to embedded the css into the file or using external file
# TODO: Some way to make html prettier?
class MarkdownBuild(sublime_plugin.WindowCommand):
    def run(self):
        #hwnd = sublime.active_window().hwnd()
        s = sublime.load_settings("MarkdownBuild.sublime-settings")
        output_html = s.get("output_html", False)
        open_html_in = s.get("open_html_in", "browser")
        use_css = s.get("use_css", True)
        charset = s.get("charset", "UTF-8")

        view = self.window.active_view()
        if not view:
            return
        file_name = view.file_name()
        if not file_name:
            return
        contents = view.substr(sublime.Region(0, view.size()))
        md = markdown_python.markdown(contents)
        html = '<html><meta charset="' + charset + '">'
        if use_css:
            css = os.path.join(sublime.packages_path(), 'MarkdownBuild', 'markdown.css')
            if (os.path.isfile(css)):
                styles = open(css, 'r').read()
                html += '<style>' + styles + '</style>'
        html += "<body>" + md + "</body></html>"

        if output_html:
            html_name = os.path.splitext(file_name)[0]
            html_name = html_name + ".html"
            output = open(html_name, 'w')
        else:
            output = tempfile.NamedTemporaryFile(delete=False, suffix='.html')

        output.write(html.encode('UTF-8'))
        output.close()

        if open_html_in == "both":
            webbrowser.open("file://" + output.name)
            self.window.open_file(output.name)
        elif open_html_in == "sublime":
            self.window.open_file(output.name)
        else:
            webbrowser.open("file://" + output.name)
                
        #sublime.set_timeout(partial(ctypes.windll.user32.SwitchToThisWindow,sublime.active_window().hwnd(), 0), 250)
        #sublime.set_timeout(partial(ctypes.windll.user32.ShowWindow,sublime.active_window().hwnd(), 5), 500)
        #sublime.set_timeout(partial(ctypes.windll.user32.SetActiveWindow,sublime.active_window().hwnd()), 500)
        #sublime.set_timeout(partial(ctypes.windll.user32.SetFocus,sublime.active_window().hwnd()), 250)

########NEW FILE########
__FILENAME__ = blockparser

import util
import odict

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
                   processor.run(parent, blocks)
                   break



########NEW FILE########
__FILENAME__ = blockprocessors
"""
CORE MARKDOWN BLOCKPARSER
=============================================================================

This parser handles basic parsing of Markdown blocks.  It doesn't concern itself
with inline elements such as **bold** or *italics*, but rather just catches 
blocks, lists, quotes, etc.

The BlockParser is made up of a bunch of BlockProssors, each handling a 
different type of block. Extensions may add/replace/remove BlockProcessors
as they need to alter how markdown blocks are parsed.

"""

import logging
import re
import util
from blockparser import BlockParser

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
            if child and (child.tag in self.LIST_TYPES or child.tag in self.ITEM_TYPES):
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
        if sibling and sibling.tag == "pre" and len(sibling) \
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
        if sibling and sibling.tag == "blockquote":
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

        if sibling and sibling.tag in self.SIBLING_TAGS:
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
        hr = util.etree.SubElement(parent, 'hr')
        # check for lines in block after hr.
        postlines = block[self.match.end():].lstrip('\n')
        if postlines:
            # Add lines after hr to master blocks for later parsing.
            blocks.insert(0, postlines)



class EmptyBlockProcessor(BlockProcessor):
    """ Process blocks and start with an empty line. """

    # Detect a block that only contains whitespace 
    # or only whitespace on the first line.
    RE = re.compile(r'^\s*\n')

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.match(block)
        if m:
            # Add remaining line to master blocks for later.
            blocks.insert(0, block[m.end():])
            sibling = self.lastChild(parent)
            if sibling and sibling.tag == 'pre' and sibling[0] and \
                    sibling[0].tag == 'code':
                # Last block is a codeblock. Append to preserve whitespace.
                sibling[0].text = util.AtomicString('%s/n/n/n' % sibling[0].text )


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
__FILENAME__ = etree_loader

## Import
def importETree():
    """Import the best implementation of ElementTree, return a module object."""
    etree_in_c = None
    try: # Is it Python 2.5+ with C implemenation of ElementTree installed?
        import xml.etree.cElementTree as etree_in_c
        from xml.etree.ElementTree import Comment
    except ImportError:
        try: # Is it Python 2.5+ with Python implementation of ElementTree?
            import xml.etree.ElementTree as etree
        except ImportError:
            try: # An earlier version of Python with cElementTree installed?
                import cElementTree as etree_in_c
                from elementtree.ElementTree import Comment
            except ImportError:
                try: # An earlier version of Python with Python ElementTree?
                    import elementtree.ElementTree as etree
                except ImportError:
                    raise ImportError("Failed to import ElementTree")
    if etree_in_c: 
        if etree_in_c.VERSION < "1.0.5":
            raise RuntimeError("cElementTree version 1.0.5 or higher is required.")
        # Third party serializers (including ours) test with non-c Comment
        etree_in_c.test_comment = Comment
        return etree_in_c
    elif etree.VERSION < "1.1":
        raise RuntimeError("ElementTree version 1.1 or higher is required")
    else:
        return etree


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

import re
import markdown
from markdown.util import etree

# Global Vars
ABBR_REF_RE = re.compile(r'[*]\[(?P<abbr>[^\]]*)\][ ]?:\s*(?P<title>.*)')

class AbbrExtension(markdown.Extension):
    """ Abbreviation Extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Insert AbbrPreprocessor before ReferencePreprocessor. """
        md.preprocessors.add('abbr', AbbrPreprocessor(md), '<reference')
        
           
class AbbrPreprocessor(markdown.preprocessors.Preprocessor):
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


class AbbrPattern(markdown.inlinepatterns.Pattern):
    """ Abbreviation inline pattern. """

    def __init__(self, pattern, title):
        markdown.inlinepatterns.Pattern.__init__(self, pattern)
        self.title = title

    def handleMatch(self, m):
        abbr = etree.Element('abbr')
        abbr.text = m.group('abbr')
        abbr.set('title', self.title)
        return abbr

def makeExtension(configs=None):
    return AbbrExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

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

License: BSD (see ../../LICENSE for details) 

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.1+](http://www.freewisdom.org/projects/python-markdown/)

"""

import markdown
import re
from markdown.util import isBlockLevel

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
        return u'.', t[1:]
    if t.startswith('#'):
        return u'id', t[1:]
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

class AttrListTreeprocessor(markdown.treeprocessors.Treeprocessor):
    
    BASE_RE = r'\{\:?([^\}]*)\}'
    HEADER_RE = re.compile(r'[ ]*%s[ ]*$' % BASE_RE)
    BLOCK_RE = re.compile(r'\n[ ]*%s[ ]*$' % BASE_RE)
    INLINE_RE = re.compile(r'^%s' % BASE_RE)

    def run(self, doc):
        for elem in doc.getiterator():
            #import pdb; pdb.set_trace()
            if isBlockLevel(elem.tag):
                # Block level: check for attrs on last line of text
                RE = self.BLOCK_RE
                if isheader(elem):
                    # header: check for attrs at end of line
                    RE = self.HEADER_RE
                if len(elem) and elem[-1].tail:
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
                # assing attr k with v
                elem.set(k, v)


class AttrListExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md, md_globals):
        # insert after 'inline' treeprocessor
        md.treeprocessors.add('attr_list', AttrListTreeprocessor(md), '>inline')


def makeExtension(configs={}):
    return AttrListExtension(configs=configs)

########NEW FILE########
__FILENAME__ = codehilite
#!/usr/bin/python

"""
CodeHilite Extension for Python-Markdown
========================================

Adds code/syntax highlighting to standard Python-Markdown code blocks.

Copyright 2006-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://www.freewisdom.org/project/python-markdown/CodeHilite>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details)

Dependencies:
* [Python 2.3+](http://python.org/)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)
* [Pygments](http://pygments.org/)

"""

import markdown
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
    from pygments.formatters import HtmlFormatter
    pygments = True
except ImportError:
    pygments = False

# ------------------ The Main CodeHilite Class ----------------------
class CodeHilite:
    """
    Determine language of source code, and pass it into the pygments hilighter.

    Basic Usage:
        >>> code = CodeHilite(src = 'some text')
        >>> html = code.hilite()

    * src: Source string or any object with a .readline attribute.

    * linenos: (Boolen) Turn line numbering 'on' or 'off' (off by default).

    * guess_lang: (Boolen) Turn language auto-detection 'on' or 'off' (on by default).

    * css_class: Set class name of wrapper div ('codehilite' by default).

    Low Level Usage:
        >>> code = CodeHilite()
        >>> code.src = 'some text' # String or anything with a .readline attr.
        >>> code.linenos = True  # True or False; Turns line numbering on or of.
        >>> html = code.hilite()

    """

    def __init__(self, src=None, linenos=False, guess_lang=True,
                css_class="codehilite", lang=None, style='default',
                noclasses=False, tab_length=4):
        self.src = src
        self.lang = lang
        self.linenos = linenos
        self.guess_lang = guess_lang
        self.css_class = css_class
        self.style = style
        self.noclasses = noclasses
        self.tab_length = tab_length

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
            self._getLang()

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
            formatter = HtmlFormatter(linenos=self.linenos,
                                      cssclass=self.css_class,
                                      style=self.style,
                                      noclasses=self.noclasses)
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
            if self.linenos:
                classes.append('linenums')
            class_str = ''
            if classes:
                class_str = ' class="%s"' % ' '.join(classes) 
            return '<pre class="%s"><code%s>%s</code></pre>\n'% \
                        (self.css_class, class_str, txt)

    def _getLang(self):
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

        """

        import re

        #split text into lines
        lines = self.src.split("\n")
        #pull first line to examine
        fl = lines.pop(0)

        c = re.compile(r'''
            (?:(?:::+)|(?P<shebang>[#]!))	# Shebang or 2 or more colons.
            (?P<path>(?:/\w+)*[/ ])?        # Zero or 1 path
            (?P<lang>[\w+-]*)               # The language
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
            if m.group('shebang'):
                # shebang exists - use line numbers
                self.linenos = True
        else:
            # No match
            lines.insert(0, fl)

        self.src = "\n".join(lines).strip("\n")



# ------------------ The Markdown Extension -------------------------------
class HiliteTreeprocessor(markdown.treeprocessors.Treeprocessor):
    """ Hilight source code in code blocks. """

    def run(self, root):
        """ Find code blocks and store in htmlStash. """
        blocks = root.getiterator('pre')
        for block in blocks:
            children = block.getchildren()
            if len(children) == 1 and children[0].tag == 'code':
                code = CodeHilite(children[0].text,
                            linenos=self.config['force_linenos'],
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


class CodeHiliteExtension(markdown.Extension):
    """ Add source code hilighting to markdown codeblocks. """

    def __init__(self, configs):
        # define default configs
        self.config = {
            'force_linenos' : [False, "Force line numbers - Default: False"],
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
#!/usr/bin/env python
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

import re
import markdown
from markdown.util import etree


class DefListProcessor(markdown.blockprocessors.BlockProcessor):
    """ Process Definition Lists. """

    RE = re.compile(r'(^|\n)[ ]{0,3}:[ ]{1,3}(.*?)(\n|$)')
    NO_INDENT_RE = re.compile(r'^[ ]{0,3}[^ :]')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        terms = [l.strip() for l in block[:m.start()].split('\n') if l.strip()]
        block = block[m.end():]
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
            if len(dl) and dl[-1].tag == 'dd' and len(dl[-1]):
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

class DefListIndentProcessor(markdown.blockprocessors.ListIndentProcessor):
    """ Process indented children of definition list items. """

    ITEM_TYPES = ['dd']
    LIST_TYPES = ['dl']

    def create_item(self, parent, block):
        """ Create a new dd and parse the block with it as the parent. """
        dd = markdown.etree.SubElement(parent, 'dd')
        self.parser.parseBlocks(dd, [block])
 


class DefListExtension(markdown.Extension):
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
#!/usr/bin/env python
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

import markdown

extensions = ['smart_strong',
              'fenced_code',
              'footnotes',
              'attr_list',
              'def_list',
              'tables',
              'abbr',
              ]
              

class ExtraExtension(markdown.Extension):
    """ Add various extensions to Markdown class."""

    def extendMarkdown(self, md, md_globals):
        """ Register extension instances. """
        md.registerExtensions(extensions, self.config)
        # Turn on processing of markdown text within raw html
        md.preprocessors['html_block'].markdown_in_raw = True

def makeExtension(configs={}):
    return ExtraExtension(configs=dict(configs))

########NEW FILE########
__FILENAME__ = fenced_code
#!/usr/bin/env python

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

Copyright 2007-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://www.freewisdom.org/project/python-markdown/Fenced__Code__Blocks>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details)

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)
* [Pygments (optional)](http://pygments.org)

"""

import re
import markdown
from markdown.extensions.codehilite import CodeHilite, CodeHiliteExtension

# Global vars
FENCED_BLOCK_RE = re.compile( \
    r'(?P<fence>^(?:~{3,}|`{3,}))[ ]*(\{?\.?(?P<lang>[a-zA-Z0-9_-]*)\}?)?[ ]*\n(?P<code>.*?)(?<=\n)(?P=fence)[ ]*$',
    re.MULTILINE|re.DOTALL
    )
CODE_WRAP = '<pre><code%s>%s</code></pre>'
LANG_TAG = ' class="%s"'

class FencedCodeExtension(markdown.Extension):

    def extendMarkdown(self, md, md_globals):
        """ Add FencedBlockPreprocessor to the Markdown instance. """
        md.registerExtension(self)

        md.preprocessors.add('fenced_code_block',
                                 FencedBlockPreprocessor(md),
                                 "_begin")


class FencedBlockPreprocessor(markdown.preprocessors.Preprocessor):

    def __init__(self, md):
        markdown.preprocessors.Preprocessor.__init__(self, md)

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
            m = FENCED_BLOCK_RE.search(text)
            if m:
                lang = ''
                if m.group('lang'):
                    lang = LANG_TAG % m.group('lang')

                # If config is not empty, then the codehighlite extension
                # is enabled, so we call it to highlite the code
                if self.codehilite_conf:
                    highliter = CodeHilite(m.group('code'),
                            linenos=self.codehilite_conf['force_linenos'][0],
                            guess_lang=self.codehilite_conf['guess_lang'][0],
                            css_class=self.codehilite_conf['css_class'][0],
                            style=self.codehilite_conf['pygments_style'][0],
                            lang=(m.group('lang') or None),
                            noclasses=self.codehilite_conf['noclasses'][0])

                    code = highliter.hilite()
                else:
                    code = CODE_WRAP % (lang, self._escape(m.group('code')))

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


if __name__ == "__main__":
    import doctest
    doctest.testmod()

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

import re
import markdown
from markdown.util import etree

FN_BACKLINK_TEXT = "zz1337820767766393qq"
NBSP_PLACEHOLDER =  "qq3936677670287331zz"
DEF_RE = re.compile(r'[ ]{0,3}\[\^([^\]]*)\]:\s*(.*)')
TABBED_RE = re.compile(r'((\t)|(    ))(.*)')

class FootnoteExtension(markdown.Extension):
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
        self.footnotes = markdown.odict.OrderedDict()
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

    def makeFootnoteId(self, id):
        """ Return footnote link id. """
        if self.getConfig("UNIQUE_IDS"):
            return 'fn:%d-%s' % (self.unique_prefix, id)
        else:
            return 'fn:%s' % id

    def makeFootnoteRefId(self, id):
        """ Return footnote back-link id. """
        if self.getConfig("UNIQUE_IDS"):
            return 'fnref:%d-%s' % (self.unique_prefix, id)
        else:
            return 'fnref:%s' % id

    def makeFootnotesDiv(self, root):
        """ Return div of footnotes as et Element. """

        if not self.footnotes.keys():
            return None

        div = etree.Element("div")
        div.set('class', 'footnote')
        hr = etree.SubElement(div, "hr")
        ol = etree.SubElement(div, "ol")

        for id in self.footnotes.keys():
            li = etree.SubElement(ol, "li")
            li.set("id", self.makeFootnoteId(id))
            self.parser.parseChunk(li, self.footnotes[id])
            backlink = etree.Element("a")
            backlink.set("href", "#" + self.makeFootnoteRefId(id))
            backlink.set("rev", "footnote")
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


class FootnotePreprocessor(markdown.preprocessors.Preprocessor):
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
        #import pdb; pdb.set_trace() #for i, line in enumerate(lines):
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


class FootnotePattern(markdown.inlinepatterns.Pattern):
    """ InlinePattern for footnote markers in a document's body text. """

    def __init__(self, pattern, footnotes):
        markdown.inlinepatterns.Pattern.__init__(self, pattern)
        self.footnotes = footnotes

    def handleMatch(self, m):
        id = m.group(2)
        if id in self.footnotes.footnotes.keys():
            sup = etree.Element("sup")
            a = etree.SubElement(sup, "a")
            sup.set('id', self.footnotes.makeFootnoteRefId(id))
            a.set('href', '#' + self.footnotes.makeFootnoteId(id))
            a.set('rel', 'footnote')
            a.text = unicode(self.footnotes.footnotes.index(id) + 1)
            return sup
        else:
            return None


class FootnoteTreeprocessor(markdown.treeprocessors.Treeprocessor):
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

class FootnotePostprocessor(markdown.postprocessors.Postprocessor):
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
#!/usr/bin/python

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

Project website: <http://www.freewisdom.org/project/python-markdown/HeaderId>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details) 

Dependencies:
* [Python 2.3+](http://python.org)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)

"""

import markdown
from markdown.util import etree
import re
from string import ascii_lowercase, digits, punctuation
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
    while id in ids:
        m = IDCOUNT_RE.match(id)
        if m:
            id = '%s_%d'% (m.group(1), int(m.group(2))+1)
        else:
            id = '%s_%d'% (id, 1)
    ids.append(id)
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


class HeaderIdTreeprocessor(markdown.treeprocessors.Treeprocessor):
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
                        id = elem.id
                    else:
                        id = slugify(''.join(itertext(elem)), sep)
                    elem.set('id', unique(id, self.IDs))
                if start_level:
                    level = int(elem.tag[-1]) + start_level
                    if level > 6:
                        level = 6
                    elem.tag = 'h%d' % level


    def _get_meta(self):
        """ Return meta data suported by this ext as a tuple """
        level = int(self.config['level']) - 1
        force = self._str2bool(self.config['forceid'])
        if hasattr(self.md, 'Meta'):
            if self.md.Meta.has_key('header_level'):
                level = int(self.md.Meta['header_level'][0]) - 1
            if self.md.Meta.has_key('header_forceid'): 
                force = self._str2bool(self.md.Meta['header_forceid'][0])
        return level, force

    def _str2bool(self, s, default=False):
        """ Convert a string to a booleen value. """
        s = str(s)
        if s.lower() in ['0', 'f', 'false', 'off', 'no', 'n']:
            return False
        elif s.lower() in ['1', 't', 'true', 'on', 'yes', 'y']:
            return True
        return default


class HeaderIdExtension (markdown.Extension):
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
        # Replace existing hasheader in place.
        md.treeprocessors.add('headerid', self.processor, '>inline')

    def reset(self):
        self.processor.IDs = []


def makeExtension(configs=None):
    return HeaderIdExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = html_tidy
#!/usr/bin/env python

"""
HTML Tidy Extension for Python-Markdown
=======================================

Runs [HTML Tidy][] on the output of Python-Markdown using the [uTidylib][] 
Python wrapper. Both libtidy and uTidylib must be installed on your system.

Note than any Tidy [options][] can be passed in as extension configs. So, 
for example, to output HTML rather than XHTML, set ``output_xhtml=0``. To
indent the output, set ``indent=auto`` and to have Tidy wrap the output in 
``<html>`` and ``<body>`` tags, set ``show_body_only=0``.

[HTML Tidy]: http://tidy.sourceforge.net/
[uTidylib]: http://utidylib.berlios.de/
[options]: http://tidy.sourceforge.net/docs/quickref.html

Copyright (c)2008 [Waylan Limberg](http://achinghead.com)

License: [BSD](http://www.opensource.org/licenses/bsd-license.php) 

Dependencies:
* [Python2.3+](http://python.org)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)
* [HTML Tidy](http://utidylib.berlios.de/)
* [uTidylib](http://utidylib.berlios.de/)

"""

import markdown
try:
    import tidy
except ImportError:
    tidy = None

class TidyExtension(markdown.Extension):

    def __init__(self, configs):
        # Set defaults to match typical markdown behavior.
        self.config = dict(output_xhtml=1,
                           show_body_only=1,
                           char_encoding='utf8'
                          )
        # Merge in user defined configs overriding any present if nessecary.
        for c in configs:
            self.config[c[0]] = c[1]

    def extendMarkdown(self, md, md_globals):
        # Save options to markdown instance
        md.tidy_options = self.config
        # Add TidyProcessor to postprocessors
        if tidy:
            md.postprocessors['tidy'] = TidyProcessor(md)


class TidyProcessor(markdown.postprocessors.Postprocessor):

    def run(self, text):
        # Pass text to Tidy. As Tidy does not accept unicode we need to encode
        # it and decode its return value.
        enc = self.markdown.tidy_options.get('char_encoding', 'utf8')
        return unicode(tidy.parseString(text.encode(enc), 
                                        **self.markdown.tidy_options),
                       encoding=enc) 


def makeExtension(configs=None):
    return TidyExtension(configs=configs)

########NEW FILE########
__FILENAME__ = meta
#!usr/bin/python

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

Project website: <http://www.freewisdom.org/project/python-markdown/Meta-Data>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details)

"""
import re

import markdown

# Global Vars
META_RE = re.compile(r'^[ ]{0,3}(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*)')
META_MORE_RE = re.compile(r'^[ ]{4,}(?P<value>.*)')

class MetaExtension (markdown.Extension):
    """ Meta-Data extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add MetaPreprocessor to Markdown instance. """

        md.preprocessors.add("meta", MetaPreprocessor(md), "_begin")


class MetaPreprocessor(markdown.preprocessors.Preprocessor):
    """ Get Meta-Data. """

    def run(self, lines):
        """ Parse Meta-Data and store in Markdown.Meta. """
        meta = {}
        key = None
        while 1:
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

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = nl2br
"""
NL2BR Extension
===============

A Python-Markdown extension to treat newlines as hard breaks; like
StackOverflow and GitHub flavored Markdown do.

Usage:

    >>> import markdown
    >>> print markdown.markdown('line 1\\nline 2', extensions=['nl2br'])
    <p>line 1<br />
    line 2</p>

Copyright 2011 [Brian Neal](http://deathofagremmie.com/)

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.1+](http://www.freewisdom.org/projects/python-markdown/)

"""

import markdown

BR_RE = r'\n'

class Nl2BrExtension(markdown.Extension):

    def extendMarkdown(self, md, md_globals):
        br_tag = markdown.inlinepatterns.SubstituteTagPattern(BR_RE, 'br')
        md.inlinePatterns.add('nl', br_tag, '_end')


def makeExtension(configs=None):
    return Nl2BrExtension(configs)


########NEW FILE########
__FILENAME__ = rss
import markdown
from markdown.util import etree

DEFAULT_URL = "http://www.freewisdom.org/projects/python-markdown/"
DEFAULT_CREATOR = "Yuri Takhteyev"
DEFAULT_TITLE = "Markdown in Python"
GENERATOR = "http://www.freewisdom.org/projects/python-markdown/markdown2rss"

month_map = { "Jan" : "01",
              "Feb" : "02",
              "March" : "03",
              "April" : "04",
              "May" : "05",
              "June" : "06",
              "July" : "07",
              "August" : "08",
              "September" : "09",
              "October" : "10",
              "November" : "11",
              "December" : "12" }

def get_time(heading):

    heading = heading.split("-")[0]
    heading = heading.strip().replace(",", " ").replace(".", " ")

    month, date, year = heading.split()
    month = month_map[month]

    return rdftime(" ".join((month, date, year, "12:00:00 AM")))

def rdftime(time):

    time = time.replace(":", " ")
    time = time.replace("/", " ")
    time = time.split()
    return "%s-%s-%sT%s:%s:%s-08:00" % (time[0], time[1], time[2],
                                        time[3], time[4], time[5])


def get_date(text):
    return "date"

class RssExtension (markdown.Extension):

    def extendMarkdown(self, md, md_globals):

        self.config = { 'URL' : [DEFAULT_URL, "Main URL"],
                        'CREATOR' : [DEFAULT_CREATOR, "Feed creator's name"],
                        'TITLE' : [DEFAULT_TITLE, "Feed title"] }

        md.xml_mode = True
        
        # Insert a tree-processor that would actually add the title tag
        treeprocessor = RssTreeProcessor(md)
        treeprocessor.ext = self
        md.treeprocessors['rss'] = treeprocessor
        md.stripTopLevelTags = 0
        md.docType = '<?xml version="1.0" encoding="utf-8"?>\n'

class RssTreeProcessor(markdown.treeprocessors.Treeprocessor):

    def run (self, root):

        rss = etree.Element("rss")
        rss.set("version", "2.0")

        channel = etree.SubElement(rss, "channel")

        for tag, text in (("title", self.ext.getConfig("TITLE")),
                          ("link", self.ext.getConfig("URL")),
                          ("description", None)):
            
            element = etree.SubElement(channel, tag)
            element.text = text

        for child in root:

            if child.tag in ["h1", "h2", "h3", "h4", "h5"]:
      
                heading = child.text.strip()
                item = etree.SubElement(channel, "item")
                link = etree.SubElement(item, "link")
                link.text = self.ext.getConfig("URL")
                title = etree.SubElement(item, "title")
                title.text = heading

                guid = ''.join([x for x in heading if x.isalnum()])
                guidElem = etree.SubElement(item, "guid")
                guidElem.text = guid
                guidElem.set("isPermaLink", "false")

            elif child.tag in ["p"]:
                try:
                    description = etree.SubElement(item, "description")
                except UnboundLocalError:
                    # Item not defined - moving on
                    pass
                else:
                    if len(child):
                        content = "\n".join([etree.tostring(node)
                                             for node in child])
                    else:
                        content = child.text
                    pholder = self.markdown.htmlStash.store(
                                                "<![CDATA[ %s]]>" % content)
                    description.text = pholder
    
        return rss


def makeExtension(configs):

    return RssExtension(configs)

########NEW FILE########
__FILENAME__ = sane_lists
#!/usr/bin/env python
"""
Sane List Extension for Python-Markdown
=======================================

Modify the behavior of Lists in Python-Markdown t act in a sane manor.

In standard Markdown sytex, the following would constitute a single 
ordered list. However, with this extension, the output would include 
two lists, the first an ordered list and the second and unordered list.

    1. ordered
    2. list

    * unordered
    * list

Copyright 2011 - [Waylan Limberg](http://achinghead.com)

"""

import re
import markdown


class SaneOListProcessor(markdown.blockprocessors.OListProcessor):
    
    CHILD_RE = re.compile(r'^[ ]{0,3}((\d+\.))[ ]+(.*)')
    SIBLING_TAGS = ['ol']


class SaneUListProcessor(markdown.blockprocessors.UListProcessor):
    
    CHILD_RE = re.compile(r'^[ ]{0,3}(([*+-]))[ ]+(.*)')
    SIBLING_TAGS = ['ul']


class SaneListExtension(markdown.Extension):
    """ Add sane lists to Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Override existing Processors. """
        md.parser.blockprocessors['olist'] = SaneOListProcessor(md.parser)
        md.parser.blockprocessors['ulist'] = SaneUListProcessor(md.parser)


def makeExtension(configs={}):
    return SaneListExtension(configs=configs)


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

import re
import markdown
from markdown.inlinepatterns import SimpleTagPattern

SMART_STRONG_RE = r'(?<!\w)(_{2})(?!_)(.+?)(?<!_)\2(?!\w)'
STRONG_RE = r'(\*{2})(.+?)\2'

class SmartEmphasisExtension(markdown.extensions.Extension):
    """ Add smart_emphasis extension to Markdown class."""

    def extendMarkdown(self, md, md_globals):
        """ Modify inline patterns. """
        md.inlinePatterns['strong'] = SimpleTagPattern(STRONG_RE, 'strong')
        md.inlinePatterns.add('strong2', SimpleTagPattern(SMART_STRONG_RE, 'strong'), '>emphasis2')

def makeExtension(configs={}):
    return SmartEmphasisExtension(configs=dict(configs))

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = tables
#!/usr/bin/env python
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
import markdown
from markdown.util import etree


class TableProcessor(markdown.blockprocessors.BlockProcessor):
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


class TableExtension(markdown.Extension):
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
* [Markdown 2.1+](http://www.freewisdom.org/projects/python-markdown/)

"""
import markdown
from markdown.util import etree
from markdown.extensions.headerid import slugify, unique, itertext

import re


class TocTreeprocessor(markdown.treeprocessors.Treeprocessor):
    # Iterator wrapper to get parent and child all at once
    def iterparent(self, root):
        for parent in root.getiterator():
            for child in parent:
                yield parent, child

    def run(self, doc):
        marker_found = False

        div = etree.Element("div")
        div.attrib["class"] = "toc"
        last_li = None

        # Add title to the div
        if self.config["title"]:
            header = etree.SubElement(div, "span")
            header.attrib["class"] = "toctitle"
            header.text = self.config["title"]

        level = 0
        list_stack=[div]
        header_rgx = re.compile("[Hh][123456]")

        # Get a list of id attributes
        used_ids = []
        for c in doc.getiterator():
            if "id" in c.attrib:
                used_ids.append(c.attrib["id"])

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
                try:
                    tag_level = int(c.tag[-1])
                    
                    while tag_level < level:
                        list_stack.pop()
                        level -= 1

                    if tag_level > level:
                        newlist = etree.Element("ul")
                        if last_li:
                            last_li.append(newlist)
                        else:
                            list_stack[-1].append(newlist)
                        list_stack.append(newlist)
                        if level == 0:
                            level = tag_level
                        else:
                            level += 1

                    # Do not override pre-existing ids 
                    if not "id" in c.attrib:
                        id = unique(self.config["slugify"](text, '-'), used_ids)
                        c.attrib["id"] = id
                    else:
                        id = c.attrib["id"]

                    # List item link, to be inserted into the toc div
                    last_li = etree.Element("li")
                    link = etree.SubElement(last_li, "a")
                    link.text = text
                    link.attrib["href"] = '#' + id

                    if self.config["anchorlink"] in [1, '1', True, 'True', 'true']:
                        anchor = etree.Element("a")
                        anchor.text = c.text
                        anchor.attrib["href"] = "#" + id
                        anchor.attrib["class"] = "toclink"
                        c.text = ""
                        for elem in c.getchildren():
                            anchor.append(elem)
                            c.remove(elem)
                        c.append(anchor)

                    list_stack[-1].append(last_li)
                except IndexError:
                    # We have bad ordering of headers. Just move on.
                    pass
        if not marker_found:
            # searialize and attach to markdown instance.
            prettify = self.markdown.treeprocessors.get('prettify')
            if prettify: prettify.run(div)
            toc = self.markdown.serializer(div)
            for pp in self.markdown.postprocessors.values():
                toc = pp.run(toc)
            self.markdown.toc = toc

class TocExtension(markdown.Extension):
    def __init__(self, configs):
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
                            "Defaults to 0"]}

        for key, value in configs:
            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        tocext = TocTreeprocessor(md)
        tocext.config = self.getConfigs()
        # Headerid ext is set to '>inline'. With this set to '<prettify',
        # it should always come after headerid ext (and honor ids assinged 
        # by the header id extension) if both are used. Same goes for 
        # attr_list extension. This must come last because we don't want
        # to redefine ids after toc is created. But we do want toc prettified.
        md.treeprocessors.add("toc", tocext, "<prettify")
	
def makeExtension(configs={}):
    return TocExtension(configs=configs)

########NEW FILE########
__FILENAME__ = wikilinks
#!/usr/bin/env python

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
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)
'''

import markdown
import re

def build_url(label, base, end):
    """ Build a url from the label, a base, and an end. """
    clean_label = re.sub(r'([ ]+_)|(_[ ]+)|([ ]+)', '_', label)
    return '%s%s%s'% (base, clean_label, end)


class WikiLinkExtension(markdown.Extension):
    def __init__(self, configs):
        # set extension defaults
        self.config = {
                        'base_url' : ['/', 'String to append to beginning or URL.'],
                        'end_url' : ['/', 'String to append to end of URL.'],
                        'html_class' : ['wikilink', 'CSS hook. Leave blank for none.'],
                        'build_url' : [build_url, 'Callable formats URL from label.'],
        }
        
        # Override defaults with user settings
        for key, value in configs :
            self.setConfig(key, value)
        
    def extendMarkdown(self, md, md_globals):
        self.md = md
    
        # append to end of inline patterns
        WIKILINK_RE = r'\[\[([\w0-9_ -]+)\]\]'
        wikilinkPattern = WikiLinks(WIKILINK_RE, self.getConfigs())
        wikilinkPattern.md = md
        md.inlinePatterns.add('wikilink', wikilinkPattern, "<not_strong")


class WikiLinks(markdown.inlinepatterns.Pattern):
    def __init__(self, pattern, config):
        markdown.inlinepatterns.Pattern.__init__(self, pattern)
        self.config = config
  
    def handleMatch(self, m):
        if m.group(2).strip():
            base_url, end_url, html_class = self._getMeta()
            label = m.group(2).strip()
            url = self.config['build_url'](label, base_url, end_url)
            a = markdown.util.etree.Element('a')
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
            if self.md.Meta.has_key('wiki_base_url'):
                base_url = self.md.Meta['wiki_base_url'][0]
            if self.md.Meta.has_key('wiki_end_url'):
                end_url = self.md.Meta['wiki_end_url'][0]
            if self.md.Meta.has_key('wiki_html_class'):
                html_class = self.md.Meta['wiki_html_class'][0]
        return base_url, end_url, html_class
    

def makeExtension(configs=None) :
    return WikiLinkExtension(configs=configs)


if __name__ == "__main__":
    import doctest
    doctest.testmod()


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

import util
import odict
import re
from urlparse import urlparse, urlunparse
import sys
# If you see an ImportError for htmlentitydefs after using 2to3 to convert for 
# use by Python3, then you are probably using the buggy version from Python 3.0.
# We recomend using the tool from Python 3.1 even if you will be running the 
# code on Python 3.0.  The following line should be converted by the tool to:
# `from html import entities` and later calls to `htmlentitydefs` should be
# changed to call `entities`. Python 3.1's tool does this but 3.0's does not.
import htmlentitydefs


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
    inlinePatterns["linebreak2"] = SubstituteTagPattern(LINE_BREAK_2_RE, 'br')
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

IMAGE_LINK_RE = r'\!' + BRK + r'\s*\((<.*?>|([^\)]*))\)'
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
LINE_BREAK_2_RE = r'  $'                    # two spaces at end of text


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

class Pattern:
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
        def get_stash(m):
            id = m.group(1)
            if id in stash:
                return stash.get(id)
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
            return '\\%s' % char


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
    """ Return a eLement of type `tag` with no children. """
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
        if netloc == '' and scheme not in locless_schemes:
            # This fails regardless of anything else. 
            # Return immediately to save additional proccessing
            return ''

        for part in url[2:]:
            if ":" in part:
                # Not a safe url
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

        el.set('alt', truealt)
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
        el.set("alt", text)
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
            entity = htmlentitydefs.codepoint2name.get(code)
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
        if data is None:
            data = {}
        super(OrderedDict, self).__init__(data)
        if isinstance(data, dict):
            self.keyOrder = data.keys()
        else:
            self.keyOrder = []
            for key, value in data:
                if key not in self.keyOrder:
                    self.keyOrder.append(key)

    def __deepcopy__(self, memo):
        from copy import deepcopy
        return self.__class__([(key, deepcopy(value, memo))
                               for key, value in self.iteritems()])

    def __setitem__(self, key, value):
        super(OrderedDict, self).__setitem__(key, value)
        if key not in self.keyOrder:
            self.keyOrder.append(key)

    def __delitem__(self, key):
        super(OrderedDict, self).__delitem__(key)
        self.keyOrder.remove(key)

    def __iter__(self):
        for k in self.keyOrder:
            yield k

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

    def items(self):
        return zip(self.keyOrder, self.values())

    def iteritems(self):
        for key in self.keyOrder:
            yield key, super(OrderedDict, self).__getitem__(key)

    def keys(self):
        return self.keyOrder[:]

    def iterkeys(self):
        return iter(self.keyOrder)

    def values(self):
        return [super(OrderedDict, self).__getitem__(k) for k in self.keyOrder]

    def itervalues(self):
        for key in self.keyOrder:
            yield super(OrderedDict, self).__getitem__(key)

    def update(self, dict_):
        for k, v in dict_.items():
            self.__setitem__(k, v)

    def setdefault(self, key, default):
        if key not in self.keyOrder:
            self.keyOrder.append(key)
        return super(OrderedDict, self).setdefault(key, default)

    def value_for_index(self, index):
        """Return the value of the item at the given zero-based index."""
        return self[self.keyOrder[index]]

    def insert(self, index, key, value):
        """Insert the key, value pair before the item with the given index."""
        if key in self.keyOrder:
            n = self.keyOrder.index(key)
            del self.keyOrder[n]
            if n < index:
                index -= 1
        self.keyOrder.insert(index, key)
        super(OrderedDict, self).__setitem__(key, value)

    def copy(self):
        """Return a copy of this object."""
        # This way of initializing the copy means it works for subclasses, too.
        obj = self.__class__(self)
        obj.keyOrder = self.keyOrder[:]
        return obj

    def __repr__(self):
        """
        Replace the normal dict.__repr__ with a version that returns the keys
        in their sorted order.
        """
        return '{%s}' % ', '.join(['%r: %r' % (k, v) for k, v in self.items()])

    def clear(self):
        super(OrderedDict, self).clear()
        self.keyOrder = []

    def index(self, key):
        """ Return the index of a given key. """
        return self.keyOrder.index(key)

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
        i = self.index_for_location(location)
        try:
            if i is not None:
                self.keyOrder.insert(i, key)
            else:
                self.keyOrder.append(key)
        except Error:
            # restore to prevent data loss and reraise
            self.keyOrder.insert(n, key)
            raise Error

########NEW FILE########
__FILENAME__ = postprocessors
"""
POST-PROCESSORS
=============================================================================

Markdown also allows post-processors, which are similar to preprocessors in
that they need to implement a "run" method. However, they are run after core
processing.

"""

import re
import util
import odict

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
        return unichr(int(m.group(1)))

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

import re
import util
import odict


def build_preprocessors(md_instance, **kwargs):
    """ Build the default set of preprocessors used by Markdown. """
    preprocessors = odict.OrderedDict()
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

    def run(self, lines):
        text = "\n".join(lines)
        new_blocks = []
        text = text.split("\n\n")
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

                    if block[1] == "!":
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
                            start = re.sub(r'\smarkdown(=[\'"]?[^> ]*[\'"]?)?', 
                                           '', block[:left_index])
                            end = block[-len(right_tag)-2:]
                            block = block[left_index:-len(right_tag)-2]
                            new_blocks.append(
                                self.markdown.htmlStash.store(start))
                            new_blocks.append(block)
                            new_blocks.append(
                                self.markdown.htmlStash.store(end))
                        else:
                            new_blocks.append(
                                self.markdown.htmlStash.store(block.strip()))
                        continue
                    else: 
                        # if is block level tag and is not complete

                        if util.isBlockLevel(left_tag) or left_tag == "--" \
                            and not block.rstrip().endswith(">"):
                            items.append(block.strip())
                            in_tag = True
                        else:
                            new_blocks.append(
                            self.markdown.htmlStash.store(block.strip()))

                        continue

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
                        start = re.sub(r'\smarkdown(=[\'"]?[^> ]*[\'"]?)?', 
                                       '', items[0][:left_index])
                        items[0] = items[0][left_index:]
                        end = items[-1][-len(right_tag)-2:]
                        items[-1] = items[-1][:-len(right_tag)-2]
                        new_blocks.append(
                            self.markdown.htmlStash.store(start))
                        new_blocks.extend(items)
                        new_blocks.append(
                            self.markdown.htmlStash.store(end))
                    else:
                        new_blocks.append(
                            self.markdown.htmlStash.store('\n\n'.join(items)))
                    items = []

        if items:
            if self.markdown_in_raw and 'markdown' in attrs.keys():
                start = re.sub(r'\smarkdown(=[\'"]?[^> ]*[\'"]?)?', 
                               '', items[0][:left_index])
                items[0] = items[0][left_index:]
                end = items[-1][-len(right_tag)-2:]
                items[-1] = items[-1][:-len(right_tag)-2]
                new_blocks.append(
                    self.markdown.htmlStash.store(start))
                new_blocks.extend(items)
                if end.strip():
                    new_blocks.append(
                        self.markdown.htmlStash.store(end))
            else:
                new_blocks.append(
                    self.markdown.htmlStash.store('\n\n'.join(items)))
            #new_blocks.append(self.markdown.htmlStash.store('\n\n'.join(items)))
            new_blocks.append('\n')

        new_text = "\n\n".join(new_blocks)
        return new_text.split("\n")


class ReferencePreprocessor(Preprocessor):
    """ Remove reference definitions from text and store for later use. """

    RE = re.compile(r'^(\ ?\ ?\ ?)\[([^\]]*)\]:\s*([^ ]*)(.*)$', re.DOTALL)

    def run (self, lines):
        new_text = [];
        for line in lines:
            m = self.RE.match(line)
            if m:
                id = m.group(2).strip().lower()
                link = m.group(3).lstrip('<').rstrip('>')
                t = m.group(4).strip()  # potential title
                if not t:
                    self.markdown.references[id] = (link, t)
                elif (len(t) >= 2
                      and (t[0] == t[-1] == "\""
                           or t[0] == t[-1] == "\'"
                           or (t[0] == "(" and t[-1] == ")") ) ):
                    self.markdown.references[id] = (link, t[1:-1])
                else:
                    new_text.append(line)
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


import util
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
                items.sort() # lexical order
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
            if format == "xhtml" and tag in HTML_EMPTY:
                write(" />")
            else:
                write(">")
                tag = tag.lower()
                if text:
                    if tag == "script" or tag == "style":
                        write(text)
                    else:
                        write(_escape_cdata(text))
                for e in elem:
                    _serialize_html(write, e, qnames, None, format)
                if tag not in HTML_EMPTY:
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
        elif isinstance(tag, basestring):
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
import re
import inlinepatterns
import util
import odict


def build_treeprocessors(md_instance, **kwargs):
    """ Build the default treeprocessors for Markdown. """
    treeprocessors = odict.OrderedDict()
    treeprocessors["inline"] = InlineProcessor(md_instance)
    treeprocessors["prettify"] = PrettifyTreeprocessor(md_instance)
    return treeprocessors


def isString(s):
    """ Check if it's string """
    if not isinstance(s, util.AtomicString):
        return isinstance(s, basestring)
    return False


class Processor:
    def __init__(self, markdown_instance=None):
        if markdown_instance:
            self.markdown = markdown_instance


class Treeprocessor(Processor):
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
            while patternIndex < len(self.markdown.inlinePatterns):
                data, matched, startIndex = self.__applyPattern(
                    self.markdown.inlinePatterns.value_for_index(patternIndex),
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
            pos = node.getchildren().index(subnode)
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
                        for child in [node] + node.getchildren():
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
                for child in [node] + node.getchildren():
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
            for child in currElement.getchildren():
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
                    pos = currElement.getchildren().index(child) + 1
                    tailResult.reverse()
                    for newChild in tailResult:
                        currElement.insert(pos, newChild)
                if child.getchildren():
                    stack.append(child)

            if self.markdown.enable_attributes:
                for element, lst in insertQueue:
                    if element.text:
                        element.text = \
                            inlinepatterns.handleAttributes(element.text, 
                                                                    element)
                    i = 0
                    for newChild in lst:
                        # Processing attributes
                        if newChild.tail:
                            newChild.tail = \
                                inlinepatterns.handleAttributes(newChild.tail,
                                                                    element)
                        if newChild.text:
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

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
import re
from logging import CRITICAL

import etree_loader


"""
CONSTANTS
=============================================================================
"""

"""
Constants you might want to modify
-----------------------------------------------------------------------------
"""

BLOCK_LEVEL_ELEMENTS = re.compile("^(p|div|h[1-6]|blockquote|pre|table|dl|ol|ul"
                                  "|script|noscript|form|fieldset|iframe|math"
                                  "|ins|del|hr|hr/|style|li|dt|dd|thead|tbody"
                                  "|tr|th|td|section|footer|header|group|figure"
                                  "|figcaption|aside|article|canvas|output"
                                  "|progress|video)$")
# Placeholders
STX = u'\u0002'  # Use STX ("Start of text") for start-of-placeholder
ETX = u'\u0003'  # Use ETX ("End of text") for end-of-placeholder
INLINE_PLACEHOLDER_PREFIX = STX+"klzzwxh:"
INLINE_PLACEHOLDER = INLINE_PLACEHOLDER_PREFIX + "%s" + ETX
INLINE_PLACEHOLDER_RE = re.compile(INLINE_PLACEHOLDER % r'([0-9]{4})')
AMP_SUBSTITUTE = STX+"amp"+ETX

"""
Constants you probably do not need to change
-----------------------------------------------------------------------------
"""

RTL_BIDI_RANGES = ( (u'\u0590', u'\u07FF'),
                     # Hebrew (0590-05FF), Arabic (0600-06FF),
                     # Syriac (0700-074F), Arabic supplement (0750-077F),
                     # Thaana (0780-07BF), Nko (07C0-07FF).
                    (u'\u2D30', u'\u2D7F'), # Tifinagh
                    )

# Extensions should use "markdown.util.etree" instead of "etree" (or do `from
# markdown.util import etree`).  Do not import it by yourself.

etree = etree_loader.importETree()

"""
AUXILIARY GLOBAL FUNCTIONS
=============================================================================
"""


def isBlockLevel(tag):
    """Check if the tag is a block level HTML tag."""
    if isinstance(tag, basestring):
        return BLOCK_LEVEL_ELEMENTS.match(tag)
    # Some ElementTree tags are not strings, so return False.
    return False

"""
MISC AUXILIARY CLASSES
=============================================================================
"""

class AtomicString(unicode):
    """A string which should not be further processed."""
    pass


class Processor:
    def __init__(self, markdown_instance=None):
        if markdown_instance:
            self.markdown = markdown_instance


class HtmlStash:
    """
    This class is used for stashing HTML objects that we extract
    in the beginning and replace with place-holders.
    """

    def __init__ (self):
        """ Create a HtmlStash. """
        self.html_counter = 0 # for counting inline html segments
        self.rawHtmlBlocks=[]

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
        return "%swzxhzdk:%d%s" % (STX, key, ETX)


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
           "http://www.freewisdom.org/projects/python-markdown/"
    ver = "%%prog %s" % markdown.version
    
    parser = optparse.OptionParser(usage=usage, description=desc, version=ver)
    parser.add_option("-f", "--file", dest="filename", default=sys.stdout,
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
