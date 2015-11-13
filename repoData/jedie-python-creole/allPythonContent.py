__FILENAME__ = cmdline
#!/usr/bin/env python
# coding: utf-8

"""
    python-creole commandline interface
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyleft: 2013 by the python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals
import argparse
import codecs

from creole import creole2html, html2creole, html2rest, html2textile
from creole import VERSION_STRING


class CreoleCLI(object):
    def __init__(self, convert_func):
        self.convert_func = convert_func
        self.parser = argparse.ArgumentParser(
            description=(
                "python-creole is an open-source (GPL) markup converter"
                " in pure Python for:"
                " creole2html, html2creole, html2ReSt, html2textile"
            ),
            version=VERSION_STRING,
        )

        self.parser.add_argument("sourcefile", help="source file to convert")
        self.parser.add_argument("destination", help="Output filename")
        self.parser.add_argument("--encoding",
            default="utf-8",
            help="Codec for read/write file (default encoding: utf-8)"
        )
        
        args = self.parser.parse_args()

        sourcefile = args.sourcefile
        destination = args.destination
        encoding = args.encoding

        self.convert(sourcefile, destination, encoding)

    def convert(self, sourcefile, destination, encoding):
        print("Convert %r to %r with %s (codec: %s)" % (
            sourcefile, destination, self.convert_func.__name__, encoding
        ))
        
        with codecs.open(sourcefile, "r", encoding=encoding) as infile:
            with codecs.open(destination, "w", encoding=encoding) as outfile:
                content = infile.read()
                converted = self.convert_func(content)
                outfile.write(converted)
        print("done. %r created." % destination)


def cli_creole2html():
    cli = CreoleCLI(creole2html)
#     cli.convert()

def cli_html2creole():
    cli = CreoleCLI(html2creole)
#     cli.convert()
    
def cli_html2rest():
    cli = CreoleCLI(html2rest)
#     cli.convert()
    
def cli_html2textile():
    cli = CreoleCLI(html2textile)
#     cli.convert()


if __name__ == "__main__":
    import sys
    sys.argv += ["../README.creole", "../test.html"]
    print(sys.argv)
    cli_creole2html()

########NEW FILE########
__FILENAME__ = emitter
# coding: utf-8


"""
    WikiCreole to HTML converter

    :copyleft: 2008-2014 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""


from __future__ import division, absolute_import, print_function, unicode_literals

from xml.sax.saxutils import escape
import sys
import traceback

from creole.creole2html.parser import CreoleParser
from creole.py3compat import TEXT_TYPE, repr2
from creole.shared.utils import string2dict



class TableOfContent(object):
    def __init__(self):
        self.max_depth = None
        self.headlines = []
        self._created = False
        self._current_level = 0

    def __call__(self, depth=None, **kwargs):
        """Called when if the macro <<toc>> is defined when it is emitted."""
        if self._created:
            return "&lt;&lt;toc&gt;&gt;"

        self._created = True
        if depth is not None:
            self.max_depth = depth

        return '<<toc>>'

    def add_headline(self, level, content):
        """Add the current header to the toc."""
        if self.max_depth is None or level <= self.max_depth:
            self.headlines.append(
                (level, content)
            )

    def flat_list2nest_list(self, flat_list):
        # this func code based on borrowed code from EyDu, Thanks!
        # http://www.python-forum.de/viewtopic.php?p=258121#p258121
        tree = []
        stack = [tree]

        for index, element in flat_list:
            stack_length = len(stack)

            if index > stack_length:
                for _ in range(stack_length, index):
                    l = []
                    stack[-1].append(l)
                    stack.append(l)
            elif index < stack_length:
                stack = stack[:index]

            stack[-1].append(element)

        return tree

    def nested_headlines2html(self, nested_headlines, level=0):
        """Convert a python nested list like the one representing the toc to an html equivalent."""
        indent = "\t"*level
        if isinstance(nested_headlines, TEXT_TYPE):
            return '%s<li><a href="#%s">%s</a></li>\n' % (indent, nested_headlines, nested_headlines)
        elif isinstance(nested_headlines, list):
            html = '%s<ul>\n' % indent
            for elt in nested_headlines:
                html += self.nested_headlines2html(elt, level + 1)
            html += '%s</ul>' % indent
            if level > 0:
                html += "\n"
            return html

    def emit(self, document):
        """Emit the toc where the <<toc>> macro was."""
        nested_headlines = self.flat_list2nest_list(self.headlines)
        html = self.nested_headlines2html(nested_headlines)

        # FIXME: We should not use <p> here, because it doesn't match
        #        if no newline was made before <<toc>>
        if "<p><<toc>></p>" in document:
            document = document.replace("<p><<toc>></p>", html, 1)
        else:
            document = document.replace("<<toc>>", html, 1)

        return document



class HtmlEmitter(object):
    """
    Generate HTML output for the document
    tree consisting of DocNodes.
    """
    def __init__(self, root, macros=None, verbose=None, stderr=None):
        self.root = root


        if callable(macros) == True:
            # was a DeprecationWarning in the past
            raise TypeError("Callable macros are not supported anymore!")

        if macros is None:
            self.macros = {}
        else:
            self.macros = macros

        if not "toc" in root.used_macros:
            # The document has no <<toc>>
            self.toc = None
        else:
            if isinstance(self.macros, dict):
                if "toc" in self.macros:
                    self.toc = self.macros["toc"]
                else:
                    self.toc = TableOfContent()
                    self.macros["toc"] = self.toc
            else:
                try:
                    self.toc = getattr(self.macros, "toc")
                except AttributeError:
                    self.toc = TableOfContent()
                    self.macros.toc = self.toc


        if verbose is None:
            self.verbose = 1
        else:
            self.verbose = verbose

        if stderr is None:
            self.stderr = sys.stderr
        else:
            self.stderr = stderr

    def get_text(self, node):
        """Try to emit whatever text is in the node."""
        try:
            return node.children[0].content or ''
        except:
            return node.content or ''

    def html_escape(self, text):
        return escape(text)

    def attr_escape(self, text):
        return self.html_escape(text).replace('"', '&quot')

    # *_emit methods for emitting nodes of the document:

    def document_emit(self, node):
        return self.emit_children(node)

    def text_emit(self, node):
        return self.html_escape(node.content)

    def separator_emit(self, node):
        return '<hr />\n\n'

    def paragraph_emit(self, node):
        return '<p>%s</p>\n' % self.emit_children(node)

    def _list_emit(self, node, list_type):
        if node.parent.kind in ("document",):
            # The first list item
            formatter = ''
        else:
            formatter = '\n'

        if list_type == "li":
            formatter += (
                '%(i)s<%(t)s>%(c)s</%(t)s>'
            )
        else:
            formatter += (
                '%(i)s<%(t)s>%(c)s\n'
                '%(i)s</%(t)s>'
            )
        return formatter % {
            "i": "\t" * node.level,
            "c": self.emit_children(node),
            "t": list_type,
        }

    def bullet_list_emit(self, node):
        return self._list_emit(node, list_type="ul")

    def number_list_emit(self, node):
        return self._list_emit(node, list_type="ol")

    def list_item_emit(self, node):
        return self._list_emit(node, list_type="li")

    def table_emit(self, node):
        return '<table>\n%s</table>\n' % self.emit_children(node)

    def table_row_emit(self, node):
        return '<tr>\n%s</tr>\n' % self.emit_children(node)

    def table_cell_emit(self, node):
        return '\t<td>%s</td>\n' % self.emit_children(node)

    def table_head_emit(self, node):
        return '\t<th>%s</th>\n' % self.emit_children(node)

    #--------------------------------------------------------------------------

    def _typeface(self, node, tag):
        return '<%(tag)s>%(data)s</%(tag)s>' % {
            "tag": tag,
            "data": self.emit_children(node),
        }

    # TODO: How can we generalize that:
    def emphasis_emit(self, node):
        return self._typeface(node, tag="i")
    def strong_emit(self, node):
        return self._typeface(node, tag="strong")
    def monospace_emit(self, node):
        return self._typeface(node, tag="tt")
    def superscript_emit(self, node):
        return self._typeface(node, tag="sup")
    def subscript_emit(self, node):
        return self._typeface(node, tag="sub")
    def underline_emit(self, node):
        return self._typeface(node, tag="u")
    def small_emit(self, node):
        return self._typeface(node, tag="small")
    def delete_emit(self, node):
        return self._typeface(node, tag="del")

    #--------------------------------------------------------------------------

    def header_emit(self, node):
        header = '<h%d>%s</h%d>' % (
                node.level, self.html_escape(node.content), node.level
        )
        if self.toc is not None:
            self.toc.add_headline(node.level, node.content)
            # add link attribute for toc navigation
            header = '<a name="%s">%s</a>' % (
                self.html_escape(node.content), header
            )

        header += "\n"
        return header

    def preformatted_emit(self, node):
        return '<pre>%s</pre>' % self.html_escape(node.content)

    def link_emit(self, node):
        target = node.content
        if node.children:
            inside = self.emit_children(node)
        else:
            inside = self.html_escape(target)

        return '<a href="%s">%s</a>' % (
            self.attr_escape(target), inside)

    def image_emit(self, node):
        target = node.content
        text = self.attr_escape(self.get_text(node))

        return '<img src="%s" title="%s" alt="%s" />' % (
            self.attr_escape(target), text, text)

    def macro_emit(self, node):
        #print(node.debug())
        macro_name = node.macro_name
        text = node.content
        macro = None

        args = node.macro_args
        try:
            macro_kwargs = string2dict(args)
        except ValueError as e:
            exc_info = sys.exc_info()
            return self.error(
                "Wrong macro arguments: %s for macro '%s' (maybe wrong macro tag syntax?)" % (
                    repr2(args), macro_name
                ),
                exc_info
            )

        macro_kwargs["text"] = text

        exc_info = None
        if isinstance(self.macros, dict):
            try:
                macro = self.macros[macro_name]
            except KeyError as e:
                exc_info = sys.exc_info()
        else:
            try:
                macro = getattr(self.macros, macro_name)
            except AttributeError as e:
                exc_info = sys.exc_info()

        if macro == None:
            return self.error(
                "Macro '%s' doesn't exist" % macro_name,
                exc_info
            )

        try:
            result = macro(**macro_kwargs)
        except TypeError as err:
            msg = "Macro '%s' error: %s" % (macro_name, err)
            exc_info = sys.exc_info()
            if self.verbose > 1:
                if self.verbose > 2:
                    raise

                # Inject more information about the macro in traceback
                etype, evalue, etb = exc_info
                import inspect
                try:
                    filename = inspect.getfile(macro)
                except TypeError:
                    pass
                else:
                    try:
                        sourceline = inspect.getsourcelines(macro)[0][0].strip()
                    except IOError as err:
                        evalue = etype("%s (error getting sourceline: %s from %s)" % (evalue, err, filename))
                    else:
                        evalue = etype("%s (sourceline: %r from %s)" % (evalue, sourceline, filename))
                    exc_info = etype, evalue, etb

            return self.error(msg, exc_info)
        except Exception as err:
            return self.error(
                "Macro '%s' error: %s" % (macro_name, err),
                exc_info=sys.exc_info()
            )

        if not isinstance(result, TEXT_TYPE):
            msg = "Macro '%s' doesn't return a unicode string!" % macro_name
            if self.verbose > 1:
                msg += " - returns: %r, type %r" % (result, type(result))
            return self.error(msg)

        if node.kind == "macro_block":
            result += "\n"

        return result
    macro_inline_emit = macro_emit
    macro_block_emit = macro_emit

    def break_emit(self, node):
        if node.parent.kind == "list_item":
            return "<br />\n" + "\t" * node.parent.level
        elif node.parent.kind in ("table_head", "table_cell"):
            return "<br />\n\t\t"
        else:
            return "<br />\n"

    def line_emit(self, node):
        return "\n"

    def pre_block_emit(self, node):
        """ pre block, with newline at the end """
        return "<pre>%s</pre>\n" % self.html_escape(node.content)

    def pre_inline_emit(self, node):
        """ pre without newline at the end """
        return "<tt>%s</tt>" % self.html_escape(node.content)

    def default_emit(self, node):
        """Fallback function for emitting unknown nodes."""
        raise NotImplementedError("Node '%s' unknown" % node.kind)

    def emit_children(self, node):
        """Emit all the children of a node."""
        return ''.join([self.emit_node(child) for child in node.children])

    def emit_node(self, node):
        """Emit a single node."""
        #print("%s_emit: %r" % (node.kind, node.content))
        emit = getattr(self, '%s_emit' % node.kind, self.default_emit)
        return emit(node)

    def emit(self):
        """Emit the document represented by self.root DOM tree."""
        document = self.emit_node(self.root).strip()
        if self.toc is not None:
            return self.toc.emit(document)
        else:
            return document

    def error(self, text, exc_info=None):
        """
        Error Handling.
        """
        if self.verbose > 1 and exc_info:
            exc_type, exc_value, exc_traceback = exc_info
            exception = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            self.stderr.write(exception)

        if self.verbose > 0:
            return "[Error: %s]\n" % text
        else:
            # No error output
            return ""


if __name__ == "__main__":
    txt = """Local test
<<toc>>
= headline 1 level 1
== headline 2 level 2
== headline 3 level 2
==== headline 4 level 4
= headline 5 level 1
=== headline 6 level 3
"""

    print("-" * 80)
#    from creole_alt.creole import CreoleParser
    p = CreoleParser(txt)
    document = p.parse()
    p.debug()

    html = HtmlEmitter(document, verbose=999).emit()
    print(html)
    print("-" * 79)
    print(html.replace(" ", ".").replace("\n", "\\n\n"))

########NEW FILE########
__FILENAME__ = parser
# coding: utf-8


"""
    Creole wiki markup parser

    See http://wikicreole.org/ for latest specs.

    Notes:
    * No markup allowed in headings.
      Creole 1.0 does not require us to support this.
    * No markup allowed in table headings.
      Creole 1.0 does not require us to support this.
    * No (non-bracketed) generic url recognition: this is "mission impossible"
      except if you want to risk lots of false positives. Only known protocols
      are recognized.
    * We do not allow ":" before "//" italic markup to avoid urls with
      unrecognized schemes (like wtf://server/path) triggering italic rendering
      for the rest of the paragraph.

    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import re

from creole.creole2html.rules import BlockRules, INLINE_FLAGS, INLINE_RULES, \
    SpecialRules, InlineRules
from creole.py3compat import TEXT_TYPE
from creole.shared.document_tree import DocNode, DebugList


class CreoleParser(object):
    """
    Parse the raw text and create a document object
    that can be converted into output using Emitter.
    """
    # For pre escaping, in creole 1.0 done with ~:
    pre_escape_re = re.compile(
        SpecialRules.pre_escape, re.MULTILINE | re.VERBOSE | re.UNICODE
    )

    # for link descriptions:
    link_re = re.compile(
        '|'.join([InlineRules.image, InlineRules.linebreak, InlineRules.char]),
        re.VERBOSE | re.UNICODE
    )
    # for list items:
    item_re = re.compile(
        SpecialRules.item, re.VERBOSE | re.UNICODE | re.MULTILINE
    )

    # for table cells:
    cell_re = re.compile(SpecialRules.cell, re.VERBOSE | re.UNICODE)

    # For inline elements:
    inline_re = re.compile('|'.join(INLINE_RULES), INLINE_FLAGS)


    def __init__(self, raw, block_rules=None, blog_line_breaks=True):
        assert isinstance(raw, TEXT_TYPE)
        self.raw = raw

        if block_rules is None:
            block_rules = BlockRules(blog_line_breaks=blog_line_breaks)

        # setup block element rules:
        self.block_re = re.compile('|'.join(block_rules.rules), block_rules.re_flags)

        self.blog_line_breaks = blog_line_breaks

        self.root = DocNode('document', None)
        self.cur = self.root        # The most recent document node
        self.text = None            # The node to add inline characters to
        self.last_text_break = None # Last break node, inserted by _text_repl()

        # Filled with all macros that's in the text
        self.root.used_macros = set()

    #--------------------------------------------------------------------------

    def cleanup_break(self, old_cur):
        """
        remove unused end line breaks.
        Should be called before a new block element.
        e.g.:
          <p>line one<br />
          line two<br />     <--- remove this br-tag
          </p>
        """
        if self.cur.children:
            last_child = self.cur.children[-1]
            if last_child.kind == "break":
                del(self.cur.children[-1])

    def _upto(self, node, kinds):
        """
        Look up the tree to the first occurence
        of one of the listed kinds of nodes or root.
        Start at the node node.
        """
        self.cleanup_break(node) # remove unused end line breaks.
        while node.parent is not None and not node.kind in kinds:
            node = node.parent

        return node

    def _upto_block(self):
        self.cur = self._upto(self.cur, ('document',))# 'section', 'blockquote'))

    #__________________________________________________________________________
    # The _*_repl methods called for matches in regexps. Sometimes the
    # same method needs several names, because of group names in regexps.

    def _text_repl(self, groups):
#        print("_text_repl()", self.cur.kind)
#        self.debug_groups(groups)

        if self.cur.kind in ('table', 'table_row', 'bullet_list', 'number_list'):
            self._upto_block()

        if self.cur.kind in ('document', 'section', 'blockquote'):
            self.cur = DocNode('paragraph', self.cur)

        text = groups.get('text', "")

        if groups.get('space'):
            # use wikipedia style line breaks and seperate a new line with one space
            text = " " + text

        self.parse_inline(text)

        if groups.get('break') and self.cur.kind in ('paragraph',
            'emphasis', 'strong', 'pre_inline'):
            self.last_text_break = DocNode('break', self.cur, "")

        self.text = None
    _break_repl = _text_repl
    _space_repl = _text_repl

    def _url_repl(self, groups):
        """Handle raw urls in text."""
        if not groups.get('escaped_url'):
            # this url is NOT escaped
            target = groups.get('url_target', "")
            node = DocNode('link', self.cur)
            node.content = target
            DocNode('text', node, node.content)
            self.text = None
        else:
            # this url is escaped, we render it as text
            if self.text is None:
                self.text = DocNode('text', self.cur, "")
            self.text.content += groups.get('url_target')
    _url_target_repl = _url_repl
    _url_proto_repl = _url_repl
    _escaped_url_repl = _url_repl

    def _link_repl(self, groups):
        """Handle all kinds of links."""
        target = groups.get('link_target', "")
        text = (groups.get('link_text', "") or "").strip()
        parent = self.cur
        self.cur = DocNode('link', self.cur)
        self.cur.content = target
        self.text = None
        re.sub(self.link_re, self._replace, text)
        self.cur = parent
        self.text = None
    _link_target_repl = _link_repl
    _link_text_repl = _link_repl

    #--------------------------------------------------------------------------

    def _add_macro(self, groups, macro_type, name_key, args_key, text_key=None):
        """
        generic method to handle the macro, used for all variants:
        inline, inline-tag, block
        """
        #self.debug_groups(groups)
        assert macro_type in ("macro_inline", "macro_block")

        if text_key:
            macro_text = groups.get(text_key, "").strip()
        else:
            macro_text = None

        node = DocNode(macro_type, self.cur, macro_text)
        macro_name = groups[name_key]
        node.macro_name = macro_name
        self.root.used_macros.add(macro_name)
        node.macro_args = groups.get(args_key, "").strip()

        self.text = None

    def _macro_block_repl(self, groups):
        """
        block macro, e.g:
        <<macro args="foo">>
        some
        lines
        <</macro>>
        """
        self._upto_block()
        self.cur = self.root
        self._add_macro(
            groups,
            macro_type="macro_block",
            name_key="macro_block_start",
            args_key="macro_block_args",
            text_key="macro_block_text",
        )
    _macro_block_start_repl = _macro_block_repl
    _macro_block_args_repl = _macro_block_repl
    _macro_block_text_repl = _macro_block_repl

    def _macro_tag_repl(self, groups):
        """
        A single macro tag, e.g.: <<macro-a foo="bar">> or <<macro />>
        """
        self._add_macro(
            groups,
            macro_type="macro_inline",
            name_key="macro_tag_name",
            args_key="macro_tag_args",
            text_key=None,
        )
    _macro_tag_name_repl = _macro_tag_repl
    _macro_tag_args_repl = _macro_tag_repl


    def _macro_inline_repl(self, groups):
        """
        inline macro tag with data, e.g.: <<macro>>text<</macro>>
        """
        self._add_macro(
            groups,
            macro_type="macro_inline",
            name_key="macro_inline_start",
            args_key="macro_inline_args",
            text_key="macro_inline_text",
        )
    _macro_inline_start_repl = _macro_inline_repl
    _macro_inline_args_repl = _macro_inline_repl
    _macro_inline_text_repl = _macro_inline_repl

    #--------------------------------------------------------------------------

    def _image_repl(self, groups):
        """Handles images and attachemnts included in the page."""
        target = groups.get('image_target', "").strip()
        text = (groups.get('image_text', "") or "").strip()
        node = DocNode("image", self.cur, target)
        DocNode('text', node, text or node.content)
        self.text = None
    _image_target_repl = _image_repl
    _image_text_repl = _image_repl

    def _separator_repl(self, groups):
        self._upto_block()
        DocNode('separator', self.cur)

    def _item_repl(self, groups):
        """ List item """
        bullet = groups.get('item_head', "")
        text = groups.get('item_text', "")
        if bullet[-1] == '#':
            kind = 'number_list'
        else:
            kind = 'bullet_list'
        level = len(bullet) - 1
        lst = self.cur
        # Find a list of the same kind and level up the tree
        while (lst and
                   not (lst.kind in ('number_list', 'bullet_list') and
                        lst.level == level) and
                    not lst.kind in ('document', 'section', 'blockquote')):
            lst = lst.parent
        if lst and lst.kind == kind:
            self.cur = lst
        else:
            # Create a new level of list
            self.cur = self._upto(self.cur,
                ('list_item', 'document', 'section', 'blockquote'))
            self.cur = DocNode(kind, self.cur)
            self.cur.level = level
        self.cur = DocNode('list_item', self.cur)
        self.cur.level = level + 1
        self.parse_inline(text)
        self.text = None
    _item_text_repl = _item_repl
    _item_head_repl = _item_repl

    def _list_repl(self, groups):
        """ complete list """
        self.item_re.sub(self._replace, groups["list"])

    def _head_repl(self, groups):
        self._upto_block()
        node = DocNode('header', self.cur, groups['head_text'].strip())
        node.level = len(groups['head_head'])
        self.text = None
    _head_head_repl = _head_repl
    _head_text_repl = _head_repl

    def _table_repl(self, groups):
        row = groups.get('table', '|').strip()
        self.cur = self._upto(self.cur, (
            'table', 'document', 'section', 'blockquote'))
        if self.cur.kind != 'table':
            self.cur = DocNode('table', self.cur)
        tb = self.cur
        tr = DocNode('table_row', tb)

        for m in self.cell_re.finditer(row):
            cell = m.group('cell')
            if cell:
                text = cell.strip()
                self.cur = DocNode('table_cell', tr)
                self.text = None
            else:
                text = m.group('head').strip('= ')
                self.cur = DocNode('table_head', tr)
                self.text = DocNode('text', self.cur, "")
            self.parse_inline(text)

        self.cur = tb
        self.text = None

    def _pre_block_repl(self, groups):
        self._upto_block()
        kind = groups.get('pre_block_kind', None)
        text = groups.get('pre_block_text', "")
        def remove_tilde(m):
            return m.group('indent') + m.group('rest')
        text = self.pre_escape_re.sub(remove_tilde, text)
        node = DocNode('pre_block', self.cur, text)
        node.sect = kind or ''
        self.text = None
    _pre_block_text_repl = _pre_block_repl
    _pre_block_head_repl = _pre_block_repl
    _pre_block_kind_repl = _pre_block_repl

    def _line_repl(self, groups):
        """ Transfer newline from the original markup into the html code """
        self._upto_block()
        DocNode('line', self.cur, "")

    def _pre_inline_repl(self, groups):
        text = groups.get('pre_inline_text', "")
        DocNode('pre_inline', self.cur, text)
        self.text = None
    _pre_inline_text_repl = _pre_inline_repl
    _pre_inline_head_repl = _pre_inline_repl

    #--------------------------------------------------------------------------

    def _inline_mark(self, groups, key):
        self.cur = DocNode(key, self.cur)

        self.text = None
        text = groups["%s_text" % key]
        self.parse_inline(text)

        self.cur = self._upto(self.cur, (key,)).parent
        self.text = None


    # TODO: How can we generalize that:
    def _emphasis_repl(self, groups):
        self._inline_mark(groups, key='emphasis')
    _emphasis_text_repl = _emphasis_repl

    def _strong_repl(self, groups):
        self._inline_mark(groups, key='strong')
    _strong_text_repl = _strong_repl

    def _monospace_repl(self, groups):
        self._inline_mark(groups, key='monospace')
    _monospace_text_repl = _monospace_repl

    def _superscript_repl(self, groups):
        self._inline_mark(groups, key='superscript')
    _superscript_text_repl = _superscript_repl

    def _subscript_repl(self, groups):
        self._inline_mark(groups, key='subscript')
    _subscript_text_repl = _subscript_repl

    def _underline_repl(self, groups):
        self._inline_mark(groups, key='underline')
    _underline_text_repl = _underline_repl

    def _small_repl(self, groups):
        self._inline_mark(groups, key='small')
    _small_text_repl = _small_repl

    def _delete_repl(self, groups):
        self._inline_mark(groups, key='delete')
    _delete_text_repl = _delete_repl

    #--------------------------------------------------------------------------

    def _linebreak_repl(self, groups):
        DocNode('break', self.cur, None)
        self.text = None

    def _escape_repl(self, groups):
        if self.text is None:
            self.text = DocNode('text', self.cur, "")
        self.text.content += groups.get('escaped_char', "")
    _escaped_char_repl = _escape_repl

    def _char_repl(self, groups):
        if self.text is None:
            self.text = DocNode('text', self.cur, "")
        self.text.content += groups.get('char', "")

    #--------------------------------------------------------------------------

    def _replace(self, match):
        """Invoke appropriate _*_repl method. Called for every matched group."""

#        def debug(groups):
#            from pprint import pformat
#            data = dict([
#                group for group in groups.items() if group[1] is not None
#            ])
#            print("%s\n" % pformat(data))

        groups = match.groupdict()
        for name, text in groups.items():
            if text is not None:
                #if name != "char": debug(groups)
                replace_method = getattr(self, '_%s_repl' % name)
                replace_method(groups)
                return

    def parse_inline(self, raw):
        """Recognize inline elements inside blocks."""
        re.sub(self.inline_re, self._replace, raw)

    def parse_block(self, raw):
        """Recognize block elements."""
        re.sub(self.block_re, self._replace, raw)

    def parse(self):
        """Parse the text given as self.raw and return DOM tree."""
        # convert all lineendings to \n
        text = self.raw.replace("\r\n", "\n").replace("\r", "\n")
        self.parse_block(text)
        return self.root


    #--------------------------------------------------------------------------
    def debug(self, start_node=None):
        """
        Display the current document tree
        """
        print("_" * 80)

        if start_node == None:
            start_node = self.root
            print("  document tree:")
        else:
            print("  tree from %s:" % start_node)

        print("=" * 80)
        def emit(node, ident=0):
            for child in node.children:
                print("%s%s: %r" % (" " * ident, child.kind, child.content))
                emit(child, ident + 4)
        emit(start_node)
        print("*" * 80)

    def debug_groups(self, groups):
        print("_" * 80)
        print("  debug groups:")
        for name, text in groups.items():
            if text is not None:
                print("%15s: %r" % (name, text))
        print("-" * 80)





if __name__ == "__main__":
    import doctest
    print(doctest.testmod())

    print("-" * 80)

    txt = """A <<test_macro1 args="foo1">>bar1<</test_macro1>> in a line..."""

    print(txt)
    print("-" * 80)

    blog_line_breaks = False

    p = CreoleParser(txt, blog_line_breaks=blog_line_breaks)
    document = p.parse()
    p.debug()

    def display_match(match):
        groups = match.groupdict()
        for name, text in groups.items():
            if name != "char" and text != None:
                print("%20s: %r" % (name, text))


    parser = CreoleParser("", blog_line_breaks=blog_line_breaks)

    print("_" * 80)
    print("merged block rules test:")
    re.sub(parser.block_re, display_match, txt)

    print("_" * 80)
    print("merged inline rules test:")
    re.sub(parser.inline_re, display_match, txt)


    def test_single(rules, flags, txt):
        for rule in rules:
            rexp = re.compile(rule, flags)
            rexp.sub(display_match, txt)

    print("_" * 80)
    print("single block rules match test:")
    block_rules = BlockRules()
    test_single(block_rules.rules, block_rules.re_flags, txt)

    print("_" * 80)
    print("single inline rules match test:")
    test_single(INLINE_RULES, INLINE_FLAGS, txt)


    print("---END---")

########NEW FILE########
__FILENAME__ = rules
# coding: utf-8


"""
    Creole Rules for parser
    ~~~~~~~~~~~~~~~~~~~~~~~

    :copyleft: 2008-2013 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import re


class InlineRules(object):
    """
    All inline rules
    """
    proto = r'http|https|ftp|nntp|news|mailto|telnet|file|irc'
    # New regex for finding uris, requires uri to free stand within whitespace or lineends.
    url = r'''(?P<url>
            (^ | (?<=\s))
            (?P<escaped_url>~)?
            (?P<url_target> (?P<url_proto> %s )://[^$\s]+ )
        )''' % proto
    # Original uri matching regex inherited from MoinMoin code.
    #url = r'''(?P<url>
            #(^ | (?<=\s | [.,:;!?()/=]))
            #(?P<escaped_url>~)?
            #(?P<url_target> (?P<url_proto> %s ):\S+? )
            #($ | (?=\s | [,.:;!?()] (\s | $)))
        #)''' % proto
    link = r'''(?P<link>
            \[\[
            (?P<link_target>.+?) \s*
            ([|] \s* (?P<link_text>.+?) \s*)?
            ]]
        )'''

#    link = r'''(?P<link1>
#            \[\[
#            (?P<link_target1>.+?)\|(?P<link_text1>.+?)
#            ]]
#        )|(?P<link2>
#            \[\[
#            (?P<link_target2> (%s)://[^ ]+) \s* (?P<link_text2>.+?)
#            ]]
#        )|
#            \[\[(?P<internal_link>.+)\]\]
#        ''' % proto

    # image tag
    image = r'''(?P<image>
            {{
            (?P<image_target>.+?) \s*
            (\| \s* (?P<image_text>.+?) \s*)?
            }}
        )(?i)'''
    #--------------------------------------------------------------------------

    # a macro like: <<macro>>text<</macro>>
    macro_inline = r'''
        (?P<macro_inline>
        << \s* (?P<macro_inline_start>\w+) \s* (?P<macro_inline_args>.*?) \s* >>
        (?P<macro_inline_text>(.|\n)*?)
        <</ \s* (?P=macro_inline_start) \s* >>
        )
    '''
    # A single macro tag, like <<macro-a foo="bar">> or <<macro />>
    macro_tag = r'''(?P<macro_tag>
            <<(?P<macro_tag_name> \w+) (?P<macro_tag_args>.*?) \s* /*>>
        )'''

    pre_inline = r'(?P<pre_inline> {{{ (?P<pre_inline_text>.*?) }}} )'

    # Basic text typefaces:

    emphasis = r'(?P<emphasis>(?<!:)// (?P<emphasis_text>.+?) (?<!:)// )'
    # there must be no : in front of the // avoids italic rendering
    # in urls with unknown protocols

    strong = r'(?P<strong>\*\* (?P<strong_text>.+?) \*\* )'

    # Creole 1.0 optional:
    monospace = r'(?P<monospace> \#\# (?P<monospace_text>.+?) \#\# )'
    superscript = r'(?P<superscript> \^\^ (?P<superscript_text>.+?) \^\^ )'
    subscript = r'(?P<subscript> ,, (?P<subscript_text>.+?) ,, )'
    underline = r'(?P<underline> __ (?P<underline_text>.+?) __ )'
    delete = r'(?P<delete> ~~ (?P<delete_text>.+?) ~~ )'

    # own additions:
    small = r'(?P<small>-- (?P<small_text>.+?) -- )'

    linebreak = r'(?P<linebreak> \\\\ )'
    escape = r'(?P<escape> ~ (?P<escaped_char>\S) )'
    char = r'(?P<char> . )'






class BlockRules(object):
    """
    All used block rules.
    """
#    macro_block = r'''(?P<macro_block>
#            \s* << (?P<macro_block_start>\w+) \s* (?P<macro_block_args>.*?) >>
#            (?P<macro_block_text>(.|\n)+?)
#            <</(?P=macro_block_start)>> \s*
#        )'''
#    macro_block = r'''(?P<macro_block>
#            <<(?P<macro_block_start>.*?)>>
#            (?P<macro_block_text>.*?)
#            <</.*?>>
#        )'''

    macro_block = r'''
        (?P<macro_block>
        << \s* (?P<macro_block_start>\w+) \s* (?P<macro_block_args>.*?) \s* >>
        (?P<macro_block_text>(.|\n)*?)
        <</ \s* (?P=macro_block_start) \s* >>
        )
    '''

    line = r'''(?P<line> ^\s*$ )''' # empty line that separates paragraphs

    head = r'''(?P<head>
        ^
        (?P<head_head>=+) \s*
        (?P<head_text> .*? )
        (=|\s)*?$
    )'''
    separator = r'(?P<separator> ^ \s* ---- \s* $ )' # horizontal line

    pre_block = r'''(?P<pre_block>
            ^{{{ \s* $
            (?P<pre_block_text>
                ([\#]!(?P<pre_block_kind>\w*?)(\s+.*)?$)?
                (.|\n)+?
            )
            ^}}})
        '''

    # Matches the whole list, separate items are parsed later. The
    # list *must* start with a single bullet.
    list = r'''(?P<list>
        ^ [ \t]* ([*][^*\#]|[\#][^\#*]).* $
        ( \n[ \t]* [*\#]+.* $ )*
    )'''

    table = r'''^ \s*(?P<table>
            [|].*? \s*
            [|]?
        ) \s* $'''

    re_flags = re.VERBOSE | re.UNICODE | re.MULTILINE

    def __init__(self, blog_line_breaks=True):
        if blog_line_breaks:
            # use blog style line breaks (every line break would be converted into <br />) 
            self.text = r'(?P<text> .+ ) (?P<break> (?<!\\)$\n(?!\s*$) )?'
        else:
            # use wiki style line breaks, seperate lines with one space
            self.text = r'(?P<space> (?<!\\)$\n(?!\s*$) )? (?P<text> .+ )'

        self.rules = (
            self.macro_block,
            self.line, self.head, self.separator,
            self.pre_block, self.list,
            self.table, self.text,
        )





class SpecialRules(object):
    """
    re rules witch not directly used as inline/block rules.
    """
    # Matches single list items:
    item = r'''^ \s* (?P<item>
        (?P<item_head> [\#*]+) \s*
        (?P<item_text> .*?)
    ) \s* $'''

    # For splitting table cells:
    cell = r'''
            \| \s*
            (
                (?P<head> [=][^|]+ ) |
                (?P<cell> (  %s | [^|])+ )
            ) \s*
        ''' % '|'.join([
            InlineRules.link,
            InlineRules.macro_inline, InlineRules.macro_tag,
            InlineRules.image,
            InlineRules.pre_inline
        ])

    # For pre escaping, in creole 1.0 done with ~:
    pre_escape = r' ^(?P<indent>\s*) ~ (?P<rest> \}\}\} \s*) $'


INLINE_FLAGS = re.VERBOSE | re.UNICODE
INLINE_RULES = (
    InlineRules.link, InlineRules.url,
    InlineRules.macro_inline, InlineRules.macro_tag,
    InlineRules.pre_inline, InlineRules.image,

    InlineRules.strong, InlineRules.emphasis,
    InlineRules.monospace, InlineRules.underline,
    InlineRules.superscript, InlineRules.subscript,
    InlineRules.small, InlineRules.delete,

    InlineRules.linebreak,
    InlineRules.escape, InlineRules.char
)


def _verify_rules(rules, flags):
    """
    Simple verify the rules -> try to compile it ;)
    
    >>> _verify_rules(INLINE_RULES, INLINE_FLAGS)
    Rule test ok.
    
    >>> block_rules = BlockRules()   
    >>> _verify_rules(block_rules.rules, block_rules.re_flags)
    Rule test ok.
    """
    # Test with re.compile
    rule_list = []
    for rule in rules:
        try:
#            print(rule)
            re.compile(rule, flags)

            # Try to merge the rules. e.g. Check if group named double used.
            rule_list.append(rule)
            re.compile('|'.join(rule_list), flags)
        except Exception as err:
            print(" *** Error with rule:")
            print(rule)
            print(" -" * 39)
            raise
    print("Rule test ok.")


if __name__ == "__main__":
    import doctest
    print(doctest.testmod())

    print("-" * 80)

########NEW FILE########
__FILENAME__ = exceptions
#!/usr/bin/env python
# coding: utf-8

"""
    python-creole exceptions
    ~~~~~~~~~~~~~~~~~~~~~~~~
    
    :copyleft: 2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

class DocutilsImportError(ImportError):
    pass

########NEW FILE########
__FILENAME__ = emitter
#!/usr/bin/env python
# coding: utf-8

"""
    html -> creole Emitter
    ~~~~~~~~~~~~~~~~~~~~~~


    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals
import posixpath

from creole.shared.base_emitter import BaseEmitter



class CreoleEmitter(BaseEmitter):
    """
    Build from a document_tree (html2creole.parser.HtmlParser instance) a
    creole markup text.
    """
    def __init__(self, *args, **kwargs):
        super(CreoleEmitter, self).__init__(*args, **kwargs)

        self.table_head_prefix = "= "
        self.table_auto_width = True

    def emit(self):
        """Emit the document represented by self.root DOM tree."""
        return self.emit_node(self.root).strip() # FIXME

    #--------------------------------------------------------------------------

    def blockdata_pre_emit(self, node):
        """ pre block -> with newline at the end """
        return "{{{%s}}}\n" % self.deentity.replace_all(node.content)
    def inlinedata_pre_emit(self, node):
        """ a pre inline block -> no newline at the end """
        return "{{{%s}}}" % self.deentity.replace_all(node.content)

    def blockdata_pass_emit(self, node):
        return "%s\n\n" % node.content
        return node.content

    #--------------------------------------------------------------------------

    def p_emit(self, node):
        result = self.emit_children(node)
        if self._inner_list == "":
            result += "\n\n"
        return result

    def br_emit(self, node):
        if self._inner_list != "":
            return "\\\\"
        else:
            return "\n"

    def headline_emit(self, node):
        return "%s %s\n\n" % ("=" * node.level, self.emit_children(node))

    #--------------------------------------------------------------------------

    def strong_emit(self, node):
        return self._typeface(node, key="**")
    b_emit = strong_emit
    big_emit = strong_emit

    def i_emit(self, node):
        return self._typeface(node, key="//")
    em_emit = i_emit

    def tt_emit(self, node):
        return self._typeface(node, key="##")
    def sup_emit(self, node):
        return self._typeface(node, key="^^")
    def sub_emit(self, node):
        return self._typeface(node, key=",,")
    def u_emit(self, node):
        return self._typeface(node, key="__")
    def small_emit(self, node):
        return self._typeface(node, key="--")
    def del_emit(self, node):
        return self._typeface(node, key="~~")
    strike_emit = del_emit

    #--------------------------------------------------------------------------

    def hr_emit(self, node):
        return "----\n\n"

    def a_emit(self, node):
        link_text = self.emit_children(node)
        try:
            url = node.attrs["href"]
        except KeyError:
            # e.g.: <a name="anchor-one">foo</a>
            return link_text
        if link_text == url:
            return "[[%s]]" % url
        else:
            return "[[%s|%s]]" % (url, link_text)

    def img_emit(self, node):
        src = node.attrs["src"]

        if src.split(':')[0] == 'data':
            return ""

        title = node.attrs.get("title", "")
        alt = node.attrs.get("alt", "")
        if len(alt) > len(title): # Use the longest one
            text = alt
        else:
            text = title

        if text == "": # Use filename as picture text
            text = posixpath.basename(src)

        return "{{%s|%s}}" % (src, text)

    #--------------------------------------------------------------------------

    def ul_emit(self, node):
        return self._list_emit(node, list_type="*")

    def ol_emit(self, node):
        return self._list_emit(node, list_type="#")

    #--------------------------------------------------------------------------

    def div_emit(self, node):
        return self._emit_content(node)

    def span_emit(self, node):
        return self._emit_content(node)






if __name__ == '__main__':
    import doctest
    print(doctest.testmod())

#    import sys;sys.exit()
    from creole.html_parser.parser import HtmlParser

    data = """A <<test_macro1 args="foo1">>bar1<</test_macro1>> in a line..."""

#    print(data.strip())
    h2c = HtmlParser(
        debug=True
    )
    document_tree = h2c.feed(data)
    h2c.debug()

    from creole.shared.unknown_tags import escape_unknown_nodes

    e = CreoleEmitter(document_tree,
        debug=True,
        unknown_emit=escape_unknown_nodes
    )
    content = e.emit()
    print("*" * 79)
    print(content)
    print("*" * 79)
    print(content.replace(" ", ".").replace("\n", "\\n\n"))

########NEW FILE########
__FILENAME__ = emitter
#!/usr/bin/env python
# coding: utf-8

"""
    html -> reStructuredText Emitter
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Links about reStructuredText:

    http://openalea.gforge.inria.fr/doc/openalea/doc/_build/html/source/sphinx/rest_syntax.html

    :copyleft: 2011-2012 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals
import posixpath

from creole.html_parser.config import BLOCK_TAGS
from creole.shared.base_emitter import BaseEmitter
from creole.shared.markup_table import MarkupTable


# Kink of nodes in which hyperlinks are stored in references intead of embedded urls.
DO_SUBSTITUTION = ("th", "td",) # TODO: In witch kind of node must we also substitude links?


class Html2restException(Exception):
    pass


class ReStructuredTextEmitter(BaseEmitter):
    """
    Build from a document_tree (html2creole.parser.HtmlParser instance) a
    creole markup text.
    """
    def __init__(self, *args, **kwargs):
        super(ReStructuredTextEmitter, self).__init__(*args, **kwargs)

        self.table_head_prefix = "_. "
        self.table_auto_width = False

        self._substitution_data = []
        self._used_substitution_links = {}
        self._used_substitution_images = {}
        self._list_markup = ""

    def _get_block_data(self):
        """
        return substitution bock data
        e.g.:
        .. _link text: /link/url/
        .. |substitution| image:: /image.png
        """
        content = "\n".join(self._substitution_data)
        self._substitution_data = []
        return content

    #--------------------------------------------------------------------------

    def blockdata_pre_emit(self, node):
        """ pre block -> with newline at the end """
        pre_block = self.deentity.replace_all(node.content).strip()
        pre_block = "\n".join(["    %s" % line for line in pre_block.splitlines()])
        return "::\n\n%s\n\n" % pre_block

    def inlinedata_pre_emit(self, node):
        """ a pre inline block -> no newline at the end """
        return "<pre>%s</pre>" % self.deentity.replace_all(node.content)

    def blockdata_pass_emit(self, node):
        return "%s\n\n" % node.content
        return node.content

    #--------------------------------------------------------------------------

    def emit_children(self, node):
        """Emit all the children of a node."""
        return "".join(self.emit_children_list(node))

    def emit(self):
        """Emit the document represented by self.root DOM tree."""
        return self.emit_node(self.root).rstrip()

    def document_emit(self, node):
        self.last = node
        result = self.emit_children(node)
        if self._substitution_data:
            # add rest at the end
            result += "%s\n\n" % self._get_block_data()
        return result

    def emit_node(self, node):
        result = ""
        if self._substitution_data and node.parent == self.root:
            result += "%s\n\n" % self._get_block_data()

        result += super(ReStructuredTextEmitter, self).emit_node(node)
        return result

    def p_emit(self, node):
        return "%s\n\n" % self.emit_children(node)

    HEADLINE_DATA = {
        1:("=", True),
        2:("-", True),
        3:("=", False),
        4:("-", False),
        5:('`', False),
        6:("'", False),
    }
    def headline_emit(self, node):
        text = self.emit_children(node)

        level = node.level
        if level > 6:
            level = 6

        char, both = self.HEADLINE_DATA[level]
        markup = char * len(text)

        if both:
            format = "%(m)s\n%(t)s\n%(m)s\n\n"
        else:
            format = "%(t)s\n%(m)s\n\n"

        return format % {"m":markup, "t":text}

    #--------------------------------------------------------------------------

    def _typeface(self, node, key):
        return key + self.emit_children(node) + key

    def strong_emit(self, node):
        return self._typeface(node, key="**")
    def b_emit(self, node):
        return self._typeface(node, key="**")
    big_emit = strong_emit

    def i_emit(self, node):
        return self._typeface(node, key="*")
    def em_emit(self, node):
        return self._typeface(node, key="*")

    def tt_emit(self, node):
        return self._typeface(node, key="``")

    def small_emit(self, node):
        # FIXME: Is there no small in ReSt???
        return self.emit_children(node)

#    def sup_emit(self, node):
#        return self._typeface(node, key="^")
#    def sub_emit(self, node):
#        return self._typeface(node, key="~")
#    def del_emit(self, node):
#        return self._typeface(node, key="-")
#
#    def cite_emit(self, node):
#        return self._typeface(node, key="??")
#    def ins_emit(self, node):
#        return self._typeface(node, key="+")
#
#    def span_emit(self, node):
#        return self._typeface(node, key="%")
#    def code_emit(self, node):
#        return self._typeface(node, key="@")

    #--------------------------------------------------------------------------

    def hr_emit(self, node):
        return "----\n\n"

    def _should_do_substitution(self, node):
        node = node.parent

        if node.kind in DO_SUBSTITUTION:
            return True

        if node is not self.root:
            return self._should_do_substitution(node)
        else:
            return False

    def _get_old_substitution(self, substitution_dict, text, url):
        if text not in substitution_dict:
            # save for the next time
            substitution_dict[text] = url
        else:
            # text has links with the same link text
            old_url = substitution_dict[text]
            if old_url == url:
                # same url -> substitution can be reused
                return old_url
            else:
                msg = (
                    "Duplicate explicit target name:"
                    " substitution was used more than one time, but with different URL."
                    " - link text: %r url1: %r url2: %r"
                ) % (text, old_url, url)
                raise Html2restException(msg)

    def a_emit(self, node):
        link_text = self.emit_children(node)
        url = node.attrs["href"]

        old_url = self._get_old_substitution(self._used_substitution_links, link_text, url)

        if self._should_do_substitution(node):
            # make a hyperlink reference
            if not old_url:
                # new substitution
                self._substitution_data.append(
                    ".. _%s: %s" % (link_text, url)
                )
            return "`%s`_" % link_text

        if old_url:
            # reuse a existing substitution
            return "`%s`_" % link_text
        else:
            # create a inline hyperlink
            return "`%s <%s>`_" % (link_text, url)

    def img_emit(self, node):
        src = node.attrs["src"]

        if src.split(':')[0] == 'data':
            return ""

        title = node.attrs.get("title", "")
        alt = node.attrs.get("alt", "")
        if len(alt) > len(title): # Use the longest one
            substitution_text = alt
        else:
            substitution_text = title

        if substitution_text == "": # Use filename as picture text
            substitution_text = posixpath.basename(src)

        old_src = self._get_old_substitution(
            self._used_substitution_images, substitution_text, src
        )
        if not old_src:
            self._substitution_data.append(
                ".. |%s| image:: %s" % (substitution_text, src)
            )

        return "|%s|" % substitution_text

    #--------------------------------------------------------------------------

    def code_emit(self, node):
        return "``%s``" % self._emit_content(node)

    #--------------------------------------------------------------------------

    def li_emit(self, node):
        content = self.emit_children(node).strip("\n")
        result = "\n%s%s %s\n" % (
            "    " * (node.level - 1), self._list_markup, content
        )
        return result

    def _list_emit(self, node, list_type):
        self._list_markup = list_type
        content = self.emit_children(node)

        if node.level == 1:
            # FIXME: This should be made ​​easier and better
            complete_list = "\n\n".join([i.strip("\n") for i in content.split("\n") if i])
            content = "%s\n\n" % complete_list

        return content

    def ul_emit(self, node):
        return self._list_emit(node, "*")

    def ol_emit(self, node):
        return self._list_emit(node, "#.")

    def table_emit(self, node):
        """
        http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#tables
        """
        self._table = MarkupTable(
            head_prefix="",
            auto_width=True,
            debug_msg=self.debug_msg
        )
        self.emit_children(node)
        content = self._table.get_rest_table()
        return "%s\n\n" % content


if __name__ == '__main__':
    import doctest
    print(doctest.testmod())

#    import sys;sys.exit()
    from creole.html_parser.parser import HtmlParser

    data = """<p>A nested bullet lists:</p>
<ul>
<li><p>item 1</p>
<ul>
<li><p>A <strong>bold subitem 1.1</strong> here.</p>
<ul>
<li>subsubitem 1.1.1</li>
<li>subsubitem 1.1.2 with inline <img alt="substitution text" src="/url/to/image.png" /> image.</li>
</ul>
</li>
<li><p>subitem 1.2</p>
</li>
</ul>
</li>
<li><p>item 2</p>
<ul>
<li>subitem 2.1</li>
</ul>
</li>
</ul>
<p>Text under list.</p>
<p>4 <img alt="PNG pictures" src="/image.png" /> four</p>
<p>5 <img alt="Image without files ext?" src="/path1/path2/image" /> five</p>
"""

    print(data)
    h2c = HtmlParser(
#        debug=True
    )
    document_tree = h2c.feed(data)
    h2c.debug()

    e = ReStructuredTextEmitter(document_tree,
        debug=True
    )
    content = e.emit()
    print("*" * 79)
    print(content)
    print("*" * 79)
    print(content.replace(" ", ".").replace("\n", "\\n\n"))


########NEW FILE########
__FILENAME__ = emitter
#!/usr/bin/env python
# coding: utf-8

"""
    html -> textile Emitter
    ~~~~~~~~~~~~~~~~~~~~~~


    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals
import posixpath

from creole.shared.base_emitter import BaseEmitter



class TextileEmitter(BaseEmitter):
    """
    Build from a document_tree (html2creole.parser.HtmlParser instance) a
    creole markup text.
    """

    def __init__(self, *args, **kwargs):
        super(TextileEmitter, self).__init__(*args, **kwargs)

        self.table_head_prefix = "_. "
        self.table_auto_width = False

    def emit(self):
        """Emit the document represented by self.root DOM tree."""
        return self.emit_node(self.root).strip() # FIXME

    #--------------------------------------------------------------------------

    def blockdata_pre_emit(self, node):
        """ pre block -> with newline at the end """
        return "<pre>%s</pre>\n" % self.deentity.replace_all(node.content)
    def inlinedata_pre_emit(self, node):
        """ a pre inline block -> no newline at the end """
        return "<pre>%s</pre>" % self.deentity.replace_all(node.content)

    def blockdata_pass_emit(self, node):
        return "%s\n\n" % node.content
        return node.content


    #--------------------------------------------------------------------------

    def p_emit(self, node):
        return "%s\n\n" % self.emit_children(node)

    def headline_emit(self, node):
        return "h%i. %s\n\n" % (node.level, self.emit_children(node))

    #--------------------------------------------------------------------------

    def _typeface(self, node, key):
        return key + self.emit_children(node) + key

    def strong_emit(self, node):
        return self._typeface(node, key="*")
    def b_emit(self, node):
        return self._typeface(node, key="**")
    big_emit = strong_emit

    def i_emit(self, node):
        return self._typeface(node, key="__")
    def em_emit(self, node):
        return self._typeface(node, key="_")

    def sup_emit(self, node):
        return self._typeface(node, key="^")
    def sub_emit(self, node):
        return self._typeface(node, key="~")
    def del_emit(self, node):
        return self._typeface(node, key="-")

    def cite_emit(self, node):
        return self._typeface(node, key="??")
    def ins_emit(self, node):
        return self._typeface(node, key="+")

    def span_emit(self, node):
        return self._typeface(node, key="%")
    def code_emit(self, node):
        return self._typeface(node, key="@")

    #--------------------------------------------------------------------------

    def hr_emit(self, node):
        return "----\n\n"

    def a_emit(self, node):
        link_text = self.emit_children(node)
        url = node.attrs["href"]
        return '"%s":%s' % (link_text, url)

    def img_emit(self, node):
        src = node.attrs["src"]

        if src.split(':')[0] == 'data':
            return ""

        title = node.attrs.get("title", "")
        alt = node.attrs.get("alt", "")
        if len(alt) > len(title): # Use the longest one
            text = alt
        else:
            text = title

        if text == "": # Use filename as picture text
            text = posixpath.basename(src)

        return "!%s(%s)!" % (src, text)

    #--------------------------------------------------------------------------

    def ul_emit(self, node):
        return self._list_emit(node, list_type="*")

    def ol_emit(self, node):
        return self._list_emit(node, list_type="#")








if __name__ == '__main__':
    import doctest
    print(doctest.testmod())

#    import sys;sys.exit()
    from creole.html_parser.parser import HtmlParser

    data = """
<h1>Textile</h1>
<table>
<tr>
    <th>Headline 1</th>
    <th>Headline 2</th>
</tr>
<tr>
    <td>cell one</td>
    <td>cell two</td>
</tr>
</table>
"""

#    print(data.strip())
    h2c = HtmlParser(
        debug=True
    )
    document_tree = h2c.feed(data)
    h2c.debug()

    e = TextileEmitter(document_tree,
        debug=True
    )
    content = e.emit()
    print("*" * 79)
    print(content)
    print("*" * 79)
    print(content.replace(" ", ".").replace("\n", "\\n\n"))

########NEW FILE########
__FILENAME__ = config
# coding: utf-8


"""
    python-creole
    ~~~~~~~~~~~~~
   
    created by Jens Diemer

    :copyleft: 2009-2011 by the python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

BLOCK_TAGS = (
    "address", "blockquote", "center", "dir", "div", "dl", "fieldset",
    "form",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "ins", "isindex", "men", "noframes", "noscript",
    "ul", "ol", "li", "table", "th", "tr", "td",
    "p", "pre",
    "br"
)
IGNORE_TAGS = ("tbody",)

########NEW FILE########
__FILENAME__ = parser
#!/usr/bin/env python
# coding: utf-8

"""
    python-creole
    ~~~~~~~~~~~~~


    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import re
import sys
import warnings

from creole.html_parser.config import BLOCK_TAGS, IGNORE_TAGS
from creole.html_tools.strip_html import strip_html
from creole.py3compat import TEXT_TYPE, BINARY_TYPE
from creole.shared.document_tree import DocNode, DebugList
from creole.shared.html_parser import HTMLParser

#------------------------------------------------------------------------------

block_re = re.compile(r'''
    ^<pre> \s* $
    (?P<pre_block>
        (\n|.)*?
    )
    ^</pre> \s* $
    [\s\n]*
''', re.VERBOSE | re.UNICODE | re.MULTILINE)

inline_re = re.compile(r'''
    <pre>
    (?P<pre_inline>
        (\n|.)*?
    )
    </pre>
''', re.VERBOSE | re.UNICODE)


headline_tag_re = re.compile(r"h(\d)", re.UNICODE)

#------------------------------------------------------------------------------


class HtmlParser(HTMLParser):
    """
    parse html code and create a document tree.
    
    >>> p = HtmlParser()
    >>> p.feed("<p>html <strong>code</strong></p>")
    <DocNode document: None>
    >>> p.debug()
    ________________________________________________________________________________
      document tree:
    ================================================================================
    p
        data: 'html '
        strong
            data: 'code'
    ********************************************************************************
    
    >>> p = HtmlParser()
    >>> p.feed("<p>html1 <script>var foo='<em>BAR</em>';</script> html2</p>")
    <DocNode document: None>
    >>> p.debug()
    ________________________________________________________________________________
      document tree:
    ================================================================================
    p
        data: 'html1 '
        script
            data: "var foo='<em>BAR"
            data: '</em>'
            data: "';"
        data: ' html2'
    ********************************************************************************
    """
    # placeholder html tag for pre cutout areas:
    _block_placeholder = "blockdata"
    _inline_placeholder = "inlinedata"

    def __init__(self, debug=False):
        HTMLParser.__init__(self)

        self.debugging = debug
        if self.debugging:
            warnings.warn(
                message="Html2Creole debug is on! warn every data append."
            )
            self.result = DebugList(self)
        else:
            self.result = []

        self.blockdata = []

        self.root = DocNode("document", None)
        self.cur = self.root

        self.__list_level = 0

    def _pre_cut(self, data, type, placeholder):
        if self.debugging:
            print("append blockdata: %r" % data)
        assert isinstance(data, TEXT_TYPE), "blockdata is not unicode"
        self.blockdata.append(data)
        id = len(self.blockdata) - 1
        return '<%s type="%s" id="%s" />' % (placeholder, type, id)

    def _pre_pre_inline_cut(self, groups):
        return self._pre_cut(groups["pre_inline"], "pre", self._inline_placeholder)

    def _pre_pre_block_cut(self, groups):
        return self._pre_cut(groups["pre_block"], "pre", self._block_placeholder)

    def _pre_pass_block_cut(self, groups):
        content = groups["pass_block"].strip()
        return self._pre_cut(content, "pass", self._block_placeholder)

    _pre_pass_block_start_cut = _pre_pass_block_cut

    def _pre_cut_out(self, match):
        groups = match.groupdict()
        for name, text in groups.items():
            if text is not None:
                if self.debugging:
                    print("%15s: %r (%r)" % (name, text, match.group(0)))
                method = getattr(self, '_pre_%s_cut' % name)
                return method(groups)

#        data = match.group("data")

    def feed(self, raw_data):
        assert isinstance(raw_data, TEXT_TYPE), "feed data must be unicode!"
        data = raw_data.strip()

        # cut out <pre> and <tt> areas block tag areas
        data = block_re.sub(self._pre_cut_out, data)
        data = inline_re.sub(self._pre_cut_out, data)

        # Delete whitespace from html code
        data = strip_html(data)

        if self.debugging:
            print("_" * 79)
            print("raw data:")
            print(repr(raw_data))
            print(" -" * 40)
            print("cleaned data:")
            print(data)
            print("-" * 79)
#            print(clean_data.replace(">", ">\n"))
#            print("-"*79)

        HTMLParser.feed(self, data)

        return self.root


    #-------------------------------------------------------------------------

    def _upto(self, node, kinds):
        """
        Look up the tree to the first occurence
        of one of the listed kinds of nodes or root.
        Start at the node node.
        """
        while node is not None and node.parent is not None:
            node = node.parent
            if node.kind in kinds:
                break

        return node

    def _go_up(self):
        kinds = list(BLOCK_TAGS) + ["document"]
        self.cur = self._upto(self.cur, kinds)
        self.debug_msg("go up to", self.cur)

    #-------------------------------------------------------------------------

    def handle_starttag(self, tag, attrs):
        self.debug_msg("starttag", "%r atts: %s" % (tag, attrs))

        if tag in IGNORE_TAGS:
            return

        headline = headline_tag_re.match(tag)
        if headline:
            self.cur = DocNode(
                "headline", self.cur, level=int(headline.group(1))
            )
            return

        if tag in ("li", "ul", "ol"):
            if tag in ("ul", "ol"):
                self.__list_level += 1
            self.cur = DocNode(tag, self.cur, None, attrs, level=self.__list_level)
        elif tag in ("img", "br"):
            # Work-a-round if img or br  tag is not marked as startendtag:
            # wrong: <img src="/image.jpg"> doesn't work if </img> not exist
            # right: <img src="/image.jpg" />
            DocNode(tag, self.cur, None, attrs)
        else:
            self.cur = DocNode(tag, self.cur, None, attrs)

    def handle_data(self, data):
        self.debug_msg("data", "%r" % data)
        if isinstance(data, BINARY_TYPE):
            data = unicode(data)
        DocNode("data", self.cur, content=data)

    def handle_charref(self, name):
        self.debug_msg("charref", "%r" % name)
        DocNode("charref", self.cur, content=name)

    def handle_entityref(self, name):
        self.debug_msg("entityref", "%r" % name)
        DocNode("entityref", self.cur, content=name)

    def handle_startendtag(self, tag, attrs):
        self.debug_msg("startendtag", "%r atts: %s" % (tag, attrs))
        attr_dict = dict(attrs)
        if tag in (self._block_placeholder, self._inline_placeholder):
            id = int(attr_dict["id"])
#            block_type = attr_dict["type"]
            DocNode(
                "%s_%s" % (tag, attr_dict["type"]),
                self.cur,
                content=self.blockdata[id],
#                attrs = attr_dict
            )
        else:
            DocNode(tag, self.cur, None, attrs)

    def handle_endtag(self, tag):
        if tag in IGNORE_TAGS:
            return

        self.debug_msg("endtag", "%r" % tag)

        if tag == "br": # handled in starttag
            return

        self.debug_msg("starttag", "%r" % self.get_starttag_text())

        if tag in ("ul", "ol"):
            self.__list_level -= 1

        if tag in BLOCK_TAGS or self.cur is None:
            self._go_up()
        else:
            self.cur = self.cur.parent

    #-------------------------------------------------------------------------

    def debug_msg(self, method, txt):
        if not self.debugging:
            return
        print("%-8s %8s: %s" % (self.getpos(), method, txt))

    def debug(self, start_node=None):
        """
        Display the current document tree
        """
        print("_" * 80)

        if start_node == None:
            start_node = self.root
            print("  document tree:")
        else:
            print("  tree from %s:" % start_node)

        print("=" * 80)
        def emit(node, ident=0):
            for child in node.children:
                txt = "%s%s" % (" " * ident, child.kind)

                if child.content:
                    txt += ": %r" % child.content

                if child.attrs:
                    txt += " - attrs: %r" % child.attrs

                if child.level != None:
                    txt += " - level: %r" % child.level

                print(txt)
                emit(child, ident + 4)
        emit(start_node)
        print("*" * 80)


if __name__ == '__main__':
    import doctest
    print(doctest.testmod())

#    p = HtmlParser(debug=True)
#    p.feed("""\
#<p><span>in span</span><br />
#<code>in code</code></p>
#""")
#    p.debug()

########NEW FILE########
__FILENAME__ = deentity
#!/usr/bin/env python
# coding: utf-8

"""
    python-creole utils
    ~~~~~~~~~~~~~~~~~~~    


    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import re
try:
    import htmlentitydefs as entities
except ImportError:
    from html import entities # python 3

from creole.py3compat import PY3


entities_rules = '|'.join([
    r"(&\#(?P<number>\d+);)",
    r"(&\#x(?P<hex>[a-fA-F0-9]+);)",
    r"(&(?P<named>[a-zA-Z]+);)",
])
#print(entities_rules)
entities_regex = re.compile(
    entities_rules, re.VERBOSE | re.UNICODE | re.MULTILINE
)


class Deentity(object):
    """
    replace html entity

    >>> d = Deentity()
    >>> d.replace_all("-=[&nbsp;&gt;&#62;&#x3E;nice&lt;&#60;&#x3C;&nbsp;]=-")
    '-=[ >>>nice<<< ]=-'
        
    >>> d.replace_all("-=[M&uuml;hlheim]=-") # uuml - latin small letter u with diaeresis
    '-=[M\\xfchlheim]=-'

    >>> d.replace_number("126")
    '~'
    >>> d.replace_hex("7E")
    '~'
    >>> d.replace_named("amp")
    '&'
    """
    def replace_number(self, text):
        """ unicode number entity """
        unicode_no = int(text)
        if PY3:
            return chr(unicode_no)
        else:
            return unichr(unicode_no)

    def replace_hex(self, text):
        """ hex entity """
        unicode_no = int(text, 16)
        if PY3:
            return chr(unicode_no)
        else:
            return unichr(unicode_no)

    def replace_named(self, text):
        """ named entity """
        if text == "nbsp":
            # Non breaking spaces is not in htmlentitydefs
            return " "
        else:
            codepoint = entities.name2codepoint[text]
            if PY3:
                return chr(codepoint)
            else:
                return unichr(codepoint)

    def replace_all(self, content):
        """ replace all html entities form the given text. """
        def replace_entity(match):
            groups = match.groupdict()
            for name, text in groups.items():
                if text is not None:
                    replace_method = getattr(self, 'replace_%s' % name)
                    return replace_method(text)

            # Should never happen:
            raise RuntimeError("deentitfy re rules wrong!")

        return entities_regex.sub(replace_entity, content)


if __name__ == '__main__':
    import doctest
    print(doctest.testmod())

########NEW FILE########
__FILENAME__ = strip_html
#!/usr/bin/env python
# coding: utf-8


"""
    python-creole utils
    ~~~~~~~~~~~~~~~~~~~    


    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import re

from creole.html_parser.config import BLOCK_TAGS


strip_html_regex = re.compile(
    r"""
        \s*
        <
            (?P<end>/{0,1})       # end tag e.g.: </end>
            (?P<tag>[^ >]+)       # tag name
            .*?
            (?P<startend>/{0,1})  # closed tag e.g.: <closed />
        >
        \s*
    """,
    re.VERBOSE | re.MULTILINE | re.UNICODE
)



def strip_html(html_code):
    """
    Delete whitespace from html code. Doesn't recordnize preformatted blocks!

    >>> strip_html(' <p>  one  \\n two  </p>')
    '<p>one two</p>'

    >>> strip_html('<p><strong><i>bold italics</i></strong></p>')
    '<p><strong><i>bold italics</i></strong></p>'

    >>> strip_html('<li>  Force  <br /> \\n linebreak </li>')
    '<li>Force<br />linebreak</li>'

    >>> strip_html('one  <i>two \\n <strong>   \\n  three  \\n  </strong></i>')
    'one <i>two <strong>three</strong> </i>'

    >>> strip_html('<p>a <unknown tag /> foobar  </p>')
    '<p>a <unknown tag /> foobar</p>'

    >>> strip_html('<p>a <pre> preformated area </pre> foo </p>')
    '<p>a<pre>preformated area</pre>foo</p>'

    >>> strip_html('<p>a <img src="/image.jpg" /> image.</p>')
    '<p>a <img src="/image.jpg" /> image.</p>'


    """

    def strip_tag(match):
        block = match.group(0)
        end_tag = match.group("end") in ("/", "/")
        startend_tag = match.group("startend") in ("/", "/")
        tag = match.group("tag")

#        print("_"*40)
#        print(match.groupdict())
#        print("block.......: %r" % block)
#        print("end_tag.....:", end_tag)
#        print("startend_tag:", startend_tag)
#        print("tag.........: %r" % tag)

        if tag in BLOCK_TAGS:
            return block.strip()

        space_start = block.startswith(" ")
        space_end = block.endswith(" ")

        result = block.strip()

        if end_tag:
            # It's a normal end tag e.g.: </strong>
            if space_start or space_end:
                result += " "
        elif startend_tag:
            # It's a closed start tag e.g.: <br />

            if space_start: # there was space before the tag
                result = " " + result

            if space_end: # there was space after the tag
                result += " "
        else:
            # a start tag e.g.: <strong>
            if space_start or space_end:
                result = " " + result

        return result

    data = html_code.strip()
    clean_data = " ".join([line.strip() for line in data.split("\n")])
    clean_data = strip_html_regex.sub(strip_tag, clean_data)
    return clean_data


if __name__ == '__main__':
    import doctest
    print(doctest.testmod())

########NEW FILE########
__FILENAME__ = text_tools
#!/usr/bin/env python
# coding: utf-8


"""
    python-creole utils
    ~~~~~~~~~~~~~~~~~~~    


    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import re


space_re = re.compile(r"^(\s*)(.*?)(\s*)$", re.DOTALL)
def clean_whitespace(txt):
    """
    Special whitespaces cleanup

    >>> clean_whitespace("\\n\\nfoo bar\\n\\n")
    'foo bar\\n'

    >>> clean_whitespace("   foo bar  \\n  \\n")
    ' foo bar\\n'

    >>> clean_whitespace(" \\n \\n  foo bar   ")
    ' foo bar '

    >>> clean_whitespace("foo   bar")
    'foo   bar'
    """
    def cleanup(match):
        start, txt, end = match.groups()

        if " " in start:
            start = " "
        else:
            start = ""

        if "\n" in end:
            end = "\n"
        elif " " in end:
            end = " "

        return start + txt + end

    return space_re.sub(cleanup, txt)


if __name__ == '__main__':
    import doctest
    print(doctest.testmod())

########NEW FILE########
__FILENAME__ = py3compat
# coding: utf-8

"""
    Helper to support Python v2 and v3
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    Some ideas borrowed from six
    
    See also:
        http://python3porting.com
        https://bitbucket.org/gutworth/six/src/tip/six.py
        http://packages.python.org/six/
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import sys
import doctest
import re

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3


if PY3:
    TEXT_TYPE = str
    BINARY_TYPE = bytes
else:
    TEXT_TYPE = unicode
    BINARY_TYPE = str

    # Simple remove 'u' from python 2 unicode repr string
    # See also:
    # http://bugs.python.org/issue3955
    # http://www.python-forum.de/viewtopic.php?f=1&t=27509 (de)
    origin_OutputChecker = doctest.OutputChecker
    class OutputChecker2(origin_OutputChecker):
        def check_output(self, want, got, optionflags):
            got = got.replace("u'", "'").replace('u"', '"')
            return origin_OutputChecker.check_output(self, want, got, optionflags)
    doctest.OutputChecker = OutputChecker2


def repr2(obj):
    """
    Don't mark unicode strings with u in Python 2
    """
    if not PY3:
        return repr(obj).lstrip("u")
    else:
        return repr(obj)



########NEW FILE########
__FILENAME__ = clean_writer
#!/usr/bin/env python
# coding: utf-8

"""
    A clean reStructuredText html writer
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    It will produce a minimal set of html output.
    (No extry divs, classes oder ids.)
    
    Some code stolen from:
    http://www.arnebrodowski.de/blog/write-your-own-restructuredtext-writer.html
    https://github.com/alex-morega/docutils-plainhtml/blob/master/plain_html_writer.py
    
    :copyleft: 2011-2013 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

#import warnings
import sys

from creole.exceptions import DocutilsImportError
from creole.py3compat import TEXT_TYPE, PY3

try:
    import docutils
    from docutils.core import publish_parts
    from docutils.writers import html4css1
except ImportError:
    etype, evalue, etb = sys.exc_info()
    msg = (
        "%s - You can't use rest2html!"
        " Please install: http://pypi.python.org/pypi/docutils"
    ) % evalue
    evalue = etype(msg)

    # Doesn't work with Python 3:
    # http://www.python-forum.de/viewtopic.php?f=1&t=27507
    # raise DocutilsImportError, evalue, etb

    raise DocutilsImportError(msg)



DEBUG = False
#DEBUG = True

IGNORE_ATTR = (
    "start", "class", "frame", "rules",
)
IGNORE_TAGS = (
    "div",
)


class CleanHTMLWriter(html4css1.Writer):
    """
    This docutils writer will use the CleanHTMLTranslator class below.
    """
    def __init__(self):
        html4css1.Writer.__init__(self)
        self.translator_class = CleanHTMLTranslator


class CleanHTMLTranslator(html4css1.HTMLTranslator, object):
    """
    Clean html translator for docutils system.
    """
    def _do_nothing(self, node, *args, **kwargs):
        pass

    def starttag(self, node, tagname, suffix='\n', empty=0, **attributes):
        """
        create start tag with the filter IGNORE_TAGS and IGNORE_ATTR.
        """
#        return super(CleanHTMLTranslator, self).starttag(node, tagname, suffix, empty, **attributes)
#        return "XXX%r" % tagname

        if tagname in IGNORE_TAGS:
            if DEBUG:
                print("ignore tag %r" % tagname)
            return ""

        parts = [tagname]
        for name, value in sorted(attributes.items()):
            # value=None was used for boolean attributes without
            # value, but this isn't supported by XHTML.
            assert value is not None

            name = name.lower()

            if name in IGNORE_ATTR:
                continue

            if isinstance(value, list):
                value = ' '.join([TEXT_TYPE(x) for x in value])

            part = '%s="%s"' % (name.lower(), self.attval(TEXT_TYPE(value)))
            parts.append(part)

        if DEBUG:
            print("Tag %r - ids: %r - attributes: %r - parts: %r" % (
                tagname, getattr(node, "ids", "-"), attributes, parts
            ))

        if empty:
            infix = ' /'
        else:
            infix = ''
        html = '<%s%s>%s' % (' '.join(parts), infix, suffix)
        if DEBUG:
            print("startag html: %r" % html)
        return html

    def visit_section(self, node):
        self.section_level += 1

    def depart_section(self, node):
        self.section_level -= 1

    set_class_on_child = _do_nothing
    set_first_last = _do_nothing

    # remove <blockquote> (e.g. in nested lists)
    visit_block_quote = _do_nothing
    depart_block_quote = _do_nothing

    # set only html_body, we used in rest2html() and don't surround it with <div>
    def depart_document(self, node):
        self.html_body.extend(self.body_prefix[1:] + self.body_pre_docinfo
                              + self.docinfo + self.body
                              + self.body_suffix[:-1])
        assert not self.context, 'len(context) = %s' % len(self.context)


    #__________________________________________________________________________
    # Clean table:

    visit_thead = _do_nothing
    depart_thead = _do_nothing
    visit_tbody = _do_nothing
    depart_tbody = _do_nothing

    def visit_table(self, node):
        if docutils.__version__ > "0.10":
            self.context.append(self.compact_p)
            self.compact_p = True
        self.body.append(self.starttag(node, 'table'))

    def visit_tgroup(self, node):
        node.stubs = []

    def visit_field_list(self, node):
        super(CleanHTMLTranslator, self).visit_field_list(node)
        if "<col" in self.body[-1]:
            del(self.body[-1])

    def depart_field_list(self, node):
        self.body.append('</table>\n')
        self.compact_field_list, self.compact_p = self.context.pop()

    def visit_docinfo(self, node):
        self.body.append(self.starttag(node, 'table'))

    def depart_docinfo(self, node):
        self.body.append('</table>\n')

    #__________________________________________________________________________
    # Clean image:

    depart_figure = _do_nothing

    def visit_image(self, node):
        super(CleanHTMLTranslator, self).visit_image(node)
        if self.body[-1].startswith('<img'):
            align = None

            if 'align' in node:
                # image with alignment
                align = node['align']

            elif node.parent.tagname == 'figure' and 'align' in node.parent:
                # figure with alignment
                align = node.parent['align']

            if align:
                self.body[-1] = self.body[-1].replace(' />', ' align="%s" />' % align)



def rest2html(content, enable_exit_status=None, **kwargs):
    """
    Convert reStructuredText markup to clean html code: No extra div, class or ids.
    
    >>> rest2html("- bullet list")
    '<ul>\\n<li>bullet list</li>\\n</ul>\\n'
    
    >>> rest2html("A ReSt link to `PyLucid CMS <http://www.pylucid.org>`_ :)")
    '<p>A ReSt link to <a href="http://www.pylucid.org">PyLucid CMS</a> :)</p>\\n'
         
    >>> rest2html("========", enable_exit_status=1, traceback=False, exit_status_level=2)
    Traceback (most recent call last):
    ...
    SystemExit: 13
    """
    if not PY3:
        content = unicode(content)

    assert isinstance(content, TEXT_TYPE), "rest2html content must be %s, but it's %s" % (TEXT_TYPE, type(content))

    settings_overrides = {
        "input_encoding": "unicode",
        "doctitle_xform": False,
        "file_insertion_enabled": False,
        "raw_enabled": False,
    }
    settings_overrides.update(kwargs)

    parts = publish_parts(
        source=content,
        writer=CleanHTMLWriter(),
        settings_overrides=settings_overrides,
        enable_exit_status=enable_exit_status,
    )
#    import pprint
#    pprint.pprint(parts)
    return parts["html_body"] # Don't detache the first heading


if __name__ == '__main__':
    import doctest
    print(doctest.testmod())

#    print(rest2html(""")
#+------------+------------+
#| Headline 1 | Headline 2 |
#+============+============+
#| cell one   | cell two   |
#+------------+------------+
#    """)

#    print(rest2html(""")
#:homepage:
#  http://code.google.com/p/python-creole/
#
#:sourcecode:
#  http://github.com/jedie/python-creole
#    """)

    print(rest2html("""
===============
Section Title 1
===============

---------------
Section Title 2
---------------

Section Title 3
===============

Section Title 4
---------------

Section Title 5
```````````````

Section Title 6
'''''''''''''''
    """))

########NEW FILE########
__FILENAME__ = base_emitter
#!/usr/bin/env python
# coding: utf-8

"""
    Base document tree emitter
    ~~~~~~~~~~~~~~~~~~~~~~~~~~


    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals
import posixpath

from creole.html_parser.config import BLOCK_TAGS
from creole.html_tools.deentity import Deentity
from creole.py3compat import TEXT_TYPE
from creole.shared.markup_table import MarkupTable
from creole.shared.unknown_tags import transparent_unknown_nodes


class BaseEmitter(object):
    """
    Build from a document_tree (html2creole.parser.HtmlParser instance) a
    creole markup text.
    """
    def __init__(self, document_tree, unknown_emit=None, debug=False):
        self.root = document_tree

        if unknown_emit is None:
            self._unknown_emit = transparent_unknown_nodes
        else:
            self._unknown_emit = unknown_emit

        self.last = None
        self.debugging = debug

        self.deentity = Deentity() # for replacing html entities
        self._inner_list = ""
        self._mask_linebreak = False

    #--------------------------------------------------------------------------

    def blockdata_pass_emit(self, node):
        return "%s\n\n" % node.content
        return node.content

    #--------------------------------------------------------------------------

    def data_emit(self, node):
        #node.debug()
        return node.content

    def entityref_emit(self, node):
        """
        emit a named html entity
        """
        entity = node.content

        try:
            return self.deentity.replace_named(entity)
        except KeyError as err:
            if self.debugging:
                print("unknown html entity found: %r" % entity)
            return "&%s" % entity # FIXME
        except UnicodeDecodeError as err:
            raise UnicodeError(
                "Error handling entity %r: %s" % (entity, err)
            )

    def charref_emit(self, node):
        """
        emit a not named html entity
        """
        entity = node.content

        if entity.startswith("x"):
            # entity in hex
            hex_no = entity[1:]
            return self.deentity.replace_hex(hex_no)
        else:
            # entity as a unicode number
            return self.deentity.replace_number(entity)

    #--------------------------------------------------------------------------

    def p_emit(self, node):
        return "%s\n\n" % self.emit_children(node)

    def br_emit(self, node):
        if self._inner_list != "":
            return "\\\\"
        else:
            return "\n"

    #--------------------------------------------------------------------------

    def _typeface(self, node, key):
        return key + self.emit_children(node) + key

    #--------------------------------------------------------------------------

    def li_emit(self, node):
        content = self.emit_children(node)
        return "\n%s %s" % (self._inner_list, content)

    def _list_emit(self, node, list_type):
        start_newline = False
        if self.last and self.last.kind not in BLOCK_TAGS:
            if not self.last.content or not self.last.content.endswith("\n"):
                start_newline = True

        if self._inner_list == "": # Start a new list
            self._inner_list = list_type
        else:
            self._inner_list += list_type

        content = "%s" % self.emit_children(node)

        self._inner_list = self._inner_list[:-1]

        if self._inner_list == "": # Start a new list
            if start_newline:
                return "\n" + content + "\n\n"
            else:
                return content.strip() + "\n\n"
        else:
            return content

    #--------------------------------------------------------------------------

    def table_emit(self, node):
        self._table = MarkupTable(
            head_prefix=self.table_head_prefix,
            auto_width=self.table_auto_width,
            debug_msg=self.debug_msg
        )
        self.emit_children(node)
        content = self._table.get_table_markup()
        return "%s\n" % content

    def tr_emit(self, node):
        self._table.add_tr()
        self.emit_children(node)
        return ""

    def _escape_linebreaks(self, text):
        text = text.strip()
        text = text.split("\n")
        lines = [line.strip() for line in text]
        lines = [line for line in lines if line]
        content = "\\\\".join(lines)
        content = content.strip("\\")
        return content

    def th_emit(self, node):
        content = self.emit_children(node)
        content = self._escape_linebreaks(content)
        self._table.add_th(content)
        return ""

    def td_emit(self, node):
        content = self.emit_children(node)
        content = self._escape_linebreaks(content)
        self._table.add_td(content)
        return ""

    #--------------------------------------------------------------------------

    def _emit_content(self, node):
        content = self.emit_children(node)
        content = self._escape_linebreaks(content)
        if node.kind in BLOCK_TAGS:
            content = "%s\n\n" % content
        return content

    def div_emit(self, node):
        return self._emit_content(node)

    def span_emit(self, node):
        return self._emit_content(node)

    #--------------------------------------------------------------------------

    def document_emit(self, node):
        self.last = node
        return self.emit_children(node)

    def emit_children(self, node):
        """Emit all the children of a node."""
        return "".join(self.emit_children_list(node))

    def emit_children_list(self, node):
        """Emit all the children of a node."""
        self.last = node
        result = []
        for child in node.children:
            content = self.emit_node(child)
            assert isinstance(content, TEXT_TYPE)
            result.append(content)
        return result

    def emit_node(self, node):
        """Emit a single node."""
        def unicode_error(method_name, method, node, content):
            node.debug()
            raise AssertionError(
                "Method '%s' (%s) returns no unicode - returns: %s (%s)" % (
                    method_name, method, repr(content), type(content)
                )
            )

        if node.level:
            self.debug_msg("emit_node", "%s (level: %i): %r" % (node.kind, node.level, node.content))
        else:
            self.debug_msg("emit_node", "%s: %r" % (node.kind, node.content))

        method_name = "%s_emit" % node.kind
        emit_method = getattr(self, method_name, None)

        if emit_method:
            content = emit_method(node)
            if not isinstance(content, TEXT_TYPE):
                unicode_error(method_name, emit_method, node, content)
        else:
            content = self._unknown_emit(self, node)
            if not isinstance(content, TEXT_TYPE):
                unicode_error(method_name, self._unknown_emit, node, content)

        self.last = node
        return content

#    def emit(self):
#        """Emit the document represented by self.root DOM tree."""
#        result = self.emit_node(self.root)
##        return result.strip() # FIXME
#        return result.rstrip() # FIXME

    #-------------------------------------------------------------------------

    def debug_msg(self, method, txt):
        if not self.debugging:
            return
        print("%13s: %s" % (method, txt))

########NEW FILE########
__FILENAME__ = document_tree
#!/usr/bin/env python
# coding: utf-8

"""
    python-creole
    ~~~~~~~~~~~~~


    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import warnings
import inspect

from creole.py3compat import TEXT_TYPE
from creole.shared.utils import dict2string


class DocNode:
    """
    A node in the document tree for html2creole and creole2html.
    
    The Document tree would be created in the parser and used in the emitter.
    """
    def __init__(self, kind='', parent=None, content=None, attrs=[], level=None):
        self.kind = kind

        self.children = []
        self.parent = parent
        if self.parent is not None:
            self.parent.children.append(self)

        self.attrs = dict(attrs)
        if content:
            assert isinstance(content, TEXT_TYPE), "Given content %r is not unicode, it's type: %s" % (
                content, type(content)
            )

        self.content = content
        self.level = level

    def get_attrs_as_string(self):
        """
        FIXME: Find a better was to do this.

        >>> node = DocNode(attrs={'foo':"bar", "no":123})
        >>> node.get_attrs_as_string()
        "foo='bar' no=123"

        >>> node = DocNode(attrs={"foo":'bar', "no":"ABC"})
        >>> node.get_attrs_as_string()
        "foo='bar' no='ABC'"
        """
        return dict2string(self.attrs)

    def __str__(self):
        return str(self.__repr__())

    def __repr__(self):
        return "<DocNode %s: %r>" % (self.kind, self.content)
#        return "<DocNode %s (parent: %r): %r>" % (self.kind, self.parent, self.content)

    def debug(self):
        print("_" * 80)
        print("\tDocNode - debug:")
        print("str(): %s" % self)
        print("attributes:")
        for i in dir(self):
            if i.startswith("_") or i == "debug":
                continue
            print("%20s: %r" % (i, getattr(self, i, "---")))


class DebugList(list):
    def __init__(self, html2creole):
        self.html2creole = html2creole
        super(DebugList, self).__init__()

    def append(self, item):
#        for stack_frame in inspect.stack(): print(stack_frame)

        line, method = inspect.stack()[1][2:4]
        msg = "%-8s   append: %-35r (%-15s line:%s)" % (
            self.html2creole.getpos(), item,
            method, line
        )
        warnings.warn(msg)
        list.append(self, item)


if __name__ == '__main__':
    import doctest
    print(doctest.testmod())

########NEW FILE########
__FILENAME__ = example_macros
# coding: utf-8


"""
    Creole macros
    ~~~~~~~~~~~~~

    Note: all mecro functions must return unicode!

    :copyleft: 2008-2014 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.

"""
from __future__ import division, absolute_import, print_function, unicode_literals

from xml.sax.saxutils import escape

try:
    from pygments import highlight
    PYGMENTS = True
except ImportError:
    PYGMENTS = False

from creole.shared.utils import get_pygments_lexer, get_pygments_formatter


def html(text):
    """
    Macro tag <<html>>...<</html>>
    Pass-trought for html code (or other stuff)
    """
    return text


def pre(text):
    """
    Macro tag <<pre>>...<</pre>>.
    Put text between html pre tag.
    """
    return '<pre>%s</pre>' % escape(text)


def code(ext, text):
    """
    Macro tag <<code ext=".some_extension">>...<</code>>
    If pygments is present, highlight the text according to the extension.
    """
    if not PYGMENTS:
        return pre(text)

    try:
        source_type = ''
        if '.' in ext:
            source_type = ext.strip().split('.')[1]
        else:
            source_type = ext.strip()
    except IndexError:
        source_type = ''

    lexer = get_pygments_lexer(source_type, code)
    formatter = get_pygments_formatter()

    try:
        highlighted_text = highlight(text, lexer, formatter).decode('utf-8')
    except:
        highlighted_text = pre(text)
    finally:
        return highlighted_text.replace('\n', '<br />\n')

########NEW FILE########
__FILENAME__ = HTMLParsercompat
"""
Patched version of the original from:
    http://hg.python.org/cpython/file/tip/Lib/html/parser.py
    
compare:
    http://hg.python.org/cpython/file/2.7/Lib/HTMLParser.py
    http://hg.python.org/cpython/file/3.2/Lib/html/parser.py

e.g.:
    cd /tmp/
    wget http://hg.python.org/cpython/raw-file/2.7/Lib/HTMLParser.py
    wget http://hg.python.org/cpython/raw-file/3.2/Lib/html/parser.py
    meld HTMLParser.py parser.py

Make it compatible with Python 2.x and 3.x
    
More info see html_parser.py !
"""

# ------------------------------------------------------------------- add start
from __future__ import division, absolute_import, print_function, unicode_literals
from creole.py3compat import PY3
# --------------------------------------------------------------------- add end

"""A parser for HTML and XHTML."""

# This file is based on sgmllib.py, but the API is slightly different.

# XXX There should be a way to distinguish between PCDATA (parsed
# character data -- the normal case), RCDATA (replaceable character
# data -- only char and entity references and end tags are special)
# and CDATA (character data -- only end tags are special).


# --------------------------------------------------------------- changes start
try:
    import _markupbase # python 3
except ImportError:
    import markupbase as _markupbase # python 2
# --------------------------------------------------------------- changes end
import re

# Regular expressions used for parsing

interesting_normal = re.compile('[&<]')
incomplete = re.compile('&[a-zA-Z#]')

entityref = re.compile('&([a-zA-Z][-.a-zA-Z0-9]*)[^a-zA-Z0-9]')
charref = re.compile('&#(?:[0-9]+|[xX][0-9a-fA-F]+)[^0-9a-fA-F]')

starttagopen = re.compile('<[a-zA-Z]')
piclose = re.compile('>')
commentclose = re.compile(r'--\s*>')
tagfind = re.compile('([a-zA-Z][-.a-zA-Z0-9:_]*)(?:\s|/(?!>))*')
# see http://www.w3.org/TR/html5/tokenization.html#tag-open-state
# and http://www.w3.org/TR/html5/tokenization.html#tag-name-state
tagfind_tolerant = re.compile('[a-zA-Z][^\t\n\r\f />\x00]*')
# Note:
#  1) the strict attrfind isn't really strict, but we can't make it
#     correctly strict without breaking backward compatibility;
#  2) if you change attrfind remember to update locatestarttagend too;
#  3) if you change attrfind and/or locatestarttagend the parser will
#     explode, so don't do it.
attrfind = re.compile(
    r'\s*([a-zA-Z_][-.:a-zA-Z_0-9]*)(\s*=\s*'
    r'(\'[^\']*\'|"[^"]*"|[^\s"\'=<>`]*))?')
attrfind_tolerant = re.compile(
    r'((?<=[\'"\s/])[^\s/>][^\s/=>]*)(\s*=+\s*'
    r'(\'[^\']*\'|"[^"]*"|(?![\'"])[^>\s]*))?(?:\s|/(?!>))*')
locatestarttagend = re.compile(r"""
  <[a-zA-Z][-.a-zA-Z0-9:_]*          # tag name
  (?:\s+                             # whitespace before attribute name
    (?:[a-zA-Z_][-.:a-zA-Z0-9_]*     # attribute name
      (?:\s*=\s*                     # value indicator
        (?:'[^']*'                   # LITA-enclosed value
          |\"[^\"]*\"                # LIT-enclosed value
          |[^'\">\s]+                # bare value
         )
       )?
     )
   )*
  \s*                                # trailing whitespace
""", re.VERBOSE)
locatestarttagend_tolerant = re.compile(r"""
  <[a-zA-Z][-.a-zA-Z0-9:_]*          # tag name
  (?:[\s/]*                          # optional whitespace before attribute name
    (?:(?<=['"\s/])[^\s/>][^\s/=>]*  # attribute name
      (?:\s*=+\s*                    # value indicator
        (?:'[^']*'                   # LITA-enclosed value
          |"[^"]*"                   # LIT-enclosed value
          |(?!['"])[^>\s]*           # bare value
         )
         (?:\s*,)*                   # possibly followed by a comma
       )?(?:\s|/(?!>))*
     )*
   )?
  \s*                                # trailing whitespace
""", re.VERBOSE)
endendtag = re.compile('>')
# the HTML 5 spec, section 8.1.2.2, doesn't allow spaces between
# </ and the tag name, so maybe this should be fixed
endtagfind = re.compile('</\s*([a-zA-Z][-.a-zA-Z0-9:_]*)\s*>')


class HTMLParseError(Exception):
    """Exception raised for all parse errors."""

    def __init__(self, msg, position=(None, None)):
        assert msg
        self.msg = msg
        self.lineno = position[0]
        self.offset = position[1]

    def __str__(self):
        result = self.msg
        if self.lineno is not None:
            result = result + ", at line %d" % self.lineno
        if self.offset is not None:
            result = result + ", column %d" % (self.offset + 1)
        return result


class HTMLParser(_markupbase.ParserBase):
    """Find tags and other markup and call handler functions.

    Usage:
        p = HTMLParser()
        p.feed(data)
        ...
        p.close()

    Start tags are handled by calling self.handle_starttag() or
    self.handle_startendtag(); end tags by self.handle_endtag().  The
    data between tags is passed from the parser to the derived class
    by calling self.handle_data() with the data as argument (the data
    may be split up in arbitrary chunks).  Entity references are
    passed by calling self.handle_entityref() with the entity
    reference as the argument.  Numeric character references are
    passed to self.handle_charref() with the string containing the
    reference as the argument.
    """

    CDATA_CONTENT_ELEMENTS = ("script", "style")

    def __init__(self, strict=True):
        """Initialize and reset this instance.

        If strict is set to True (the default), errors are raised when invalid
        HTML is encountered.  If set to False, an attempt is instead made to
        continue parsing, making "best guesses" about the intended meaning, in
        a fashion similar to what browsers typically do.
        """
        self.strict = strict
        self.reset()

    def reset(self):
        """Reset this instance.  Loses all unprocessed data."""
        self.rawdata = ''
        self.lasttag = '???'
        self.interesting = interesting_normal
        self.cdata_elem = None
        _markupbase.ParserBase.reset(self)

    def feed(self, data):
        r"""Feed data to the parser.

        Call this as often as you want, with as little or as much text
        as you want (may include '\n').
        """
        self.rawdata = self.rawdata + data
        self.goahead(0)

    def close(self):
        """Handle any buffered data."""
        self.goahead(1)

    def error(self, message):
        raise HTMLParseError(message, self.getpos())

    __starttag_text = None

    def get_starttag_text(self):
        """Return full source of start tag: '<...>'."""
        return self.__starttag_text

    def set_cdata_mode(self, elem):
        self.cdata_elem = elem.lower()
        self.interesting = re.compile(r'</\s*%s\s*>' % self.cdata_elem, re.I)

    def clear_cdata_mode(self):
        self.interesting = interesting_normal
        self.cdata_elem = None

    # Internal -- handle data as far as reasonable.  May leave state
    # and data to be processed by a subsequent call.  If 'end' is
    # true, force handling all data as if followed by EOF marker.
    def goahead(self, end):
        rawdata = self.rawdata
        i = 0
        n = len(rawdata)
        while i < n:
            match = self.interesting.search(rawdata, i) # < or &
            if match:
                j = match.start()
            else:
                if self.cdata_elem:
                    break
                j = n
            if i < j: self.handle_data(rawdata[i:j])
            i = self.updatepos(i, j)
            if i == n: break
            startswith = rawdata.startswith
            if startswith('<', i):
                if starttagopen.match(rawdata, i): # < + letter
                    k = self.parse_starttag(i)
                elif startswith("</", i):
                    k = self.parse_endtag(i)
                elif startswith("<!--", i):
                    k = self.parse_comment(i)
                elif startswith("<?", i):
                    k = self.parse_pi(i)
                elif startswith("<!", i):
                    if self.strict:
                        k = self.parse_declaration(i)
                    else:
                        k = self.parse_html_declaration(i)
                elif (i + 1) < n:
                    self.handle_data("<")
                    k = i + 1
                else:
                    break
                if k < 0:
                    if not end:
                        break
                    if self.strict:
                        self.error("EOF in middle of construct")
                    k = rawdata.find('>', i + 1)
                    if k < 0:
                        k = rawdata.find('<', i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    self.handle_data(rawdata[i:k])
                i = self.updatepos(i, k)
            elif startswith("&#", i):
                match = charref.match(rawdata, i)
                if match:
                    name = match.group()[2:-1]
                    self.handle_charref(name)
                    k = match.end()
                    if not startswith(';', k-1):
                        k = k - 1
                    i = self.updatepos(i, k)
                    continue
                else:
                    if ";" in rawdata[i:]: #bail by consuming &#
                        self.handle_data(rawdata[0:2])
                        i = self.updatepos(i, 2)
                    break
            elif startswith('&', i):
                match = entityref.match(rawdata, i)
                if match:
                    name = match.group(1)
                    self.handle_entityref(name)
                    k = match.end()
                    if not startswith(';', k-1):
                        k = k - 1
                    i = self.updatepos(i, k)
                    continue
                match = incomplete.match(rawdata, i)
                if match:
                    # match.group() will contain at least 2 chars
                    if end and match.group() == rawdata[i:]:
                        if self.strict:
                            self.error("EOF in middle of entity or char ref")
                        else:
                            if k <= i:
                                k = n
                            i = self.updatepos(i, i + 1)
                    # incomplete
                    break
                elif (i + 1) < n:
                    # not the end of the buffer, and can't be confused
                    # with some other construct
                    self.handle_data("&")
                    i = self.updatepos(i, i + 1)
                else:
                    break
            else:
                assert 0, "interesting.search() lied"
        # end while
        if end and i < n and not self.cdata_elem:
            self.handle_data(rawdata[i:n])
            i = self.updatepos(i, n)
        self.rawdata = rawdata[i:]

    # Internal -- parse html declarations, return length or -1 if not terminated
    # See w3.org/TR/html5/tokenization.html#markup-declaration-open-state
    # See also parse_declaration in _markupbase
    def parse_html_declaration(self, i):
        rawdata = self.rawdata
        if rawdata[i:i+2] != '<!':
            self.error('unexpected call to parse_html_declaration()')
        if rawdata[i:i+4] == '<!--':
            # this case is actually already handled in goahead()
            return self.parse_comment(i)
        elif rawdata[i:i+3] == '<![':
            return self.parse_marked_section(i)
        elif rawdata[i:i+9].lower() == '<!doctype':
            # find the closing >
            gtpos = rawdata.find('>', i+9)
            if gtpos == -1:
                return -1
            self.handle_decl(rawdata[i+2:gtpos])
            return gtpos+1
        else:
            return self.parse_bogus_comment(i)

    # Internal -- parse bogus comment, return length or -1 if not terminated
    # see http://www.w3.org/TR/html5/tokenization.html#bogus-comment-state
    def parse_bogus_comment(self, i, report=1):
        rawdata = self.rawdata
        if rawdata[i:i+2] not in ('<!', '</'):
            self.error('unexpected call to parse_comment()')
        pos = rawdata.find('>', i+2)
        if pos == -1:
            return -1
        if report:
            self.handle_comment(rawdata[i+2:pos])
        return pos + 1

    # Internal -- parse processing instr, return end or -1 if not terminated
    def parse_pi(self, i):
        rawdata = self.rawdata
        assert rawdata[i:i+2] == '<?', 'unexpected call to parse_pi()'
        match = piclose.search(rawdata, i+2) # >
        if not match:
            return -1
        j = match.start()
        self.handle_pi(rawdata[i+2: j])
        j = match.end()
        return j

    # Internal -- handle starttag, return end or -1 if not terminated
    def parse_starttag(self, i):
        self.__starttag_text = None
        endpos = self.check_for_whole_start_tag(i)
        if endpos < 0:
            return endpos
        rawdata = self.rawdata
        self.__starttag_text = rawdata[i:endpos]

        # Now parse the data between i+1 and j into a tag and attrs
        attrs = []
        match = tagfind.match(rawdata, i+1)
        assert match, 'unexpected call to parse_starttag()'
        k = match.end()
        self.lasttag = tag = match.group(1).lower()
        while k < endpos:
            if self.strict:
                m = attrfind.match(rawdata, k)
            else:
                m = attrfind_tolerant.match(rawdata, k)
            if not m:
                break
            attrname, rest, attrvalue = m.group(1, 2, 3)
            if not rest:
                attrvalue = None
            elif attrvalue[:1] == '\'' == attrvalue[-1:] or \
                 attrvalue[:1] == '"' == attrvalue[-1:]:
                attrvalue = attrvalue[1:-1]
            if attrvalue:
                attrvalue = self.unescape(attrvalue)
            attrs.append((attrname.lower(), attrvalue))
            k = m.end()

        end = rawdata[k:endpos].strip()
        if end not in (">", "/>"):
            lineno, offset = self.getpos()
            if "\n" in self.__starttag_text:
                lineno = lineno + self.__starttag_text.count("\n")
                offset = len(self.__starttag_text) \
                         - self.__starttag_text.rfind("\n")
            else:
                offset = offset + len(self.__starttag_text)
            if self.strict:
                self.error("junk characters in start tag: %r"
                           % (rawdata[k:endpos][:20],))
            self.handle_data(rawdata[i:endpos])
            return endpos
        if end.endswith('/>'):
            # XHTML-style empty tag: <span attr="value" />
            self.handle_startendtag(tag, attrs)
        else:
            self.handle_starttag(tag, attrs)
            if tag in self.CDATA_CONTENT_ELEMENTS:
                self.set_cdata_mode(tag)
        return endpos

    # Internal -- check to see if we have a complete starttag; return end
    # or -1 if incomplete.
    def check_for_whole_start_tag(self, i):
        rawdata = self.rawdata
        if self.strict:
            m = locatestarttagend.match(rawdata, i)
        else:
            m = locatestarttagend_tolerant.match(rawdata, i)
        if m:
            j = m.end()
            next = rawdata[j:j+1]
            if next == ">":
                return j + 1
            if next == "/":
                if rawdata.startswith("/>", j):
                    return j + 2
                if rawdata.startswith("/", j):
                    # buffer boundary
                    return -1
                # else bogus input
                if self.strict:
                    self.updatepos(i, j + 1)
                    self.error("malformed empty start tag")
                if j > i:
                    return j
                else:
                    return i + 1
            if next == "":
                # end of input
                return -1
            if next in ("abcdefghijklmnopqrstuvwxyz=/"
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
                # end of input in or before attribute value, or we have the
                # '/' from a '/>' ending
                return -1
            if self.strict:
                self.updatepos(i, j)
                self.error("malformed start tag")
            if j > i:
                return j
            else:
                return i + 1
        raise AssertionError("we should not get here!")

    # Internal -- parse endtag, return end or -1 if incomplete
    def parse_endtag(self, i):
        rawdata = self.rawdata
        assert rawdata[i:i+2] == "</", "unexpected call to parse_endtag"
        match = endendtag.search(rawdata, i+1) # >
        if not match:
            return -1
        gtpos = match.end()
        match = endtagfind.match(rawdata, i) # </ + tag + >
        if not match:
            if self.cdata_elem is not None:
                self.handle_data(rawdata[i:gtpos])
                return gtpos
            if self.strict:
                self.error("bad end tag: %r" % (rawdata[i:gtpos],))
            # find the name: w3.org/TR/html5/tokenization.html#tag-name-state
            namematch = tagfind_tolerant.match(rawdata, i+2)
            if not namematch:
                # w3.org/TR/html5/tokenization.html#end-tag-open-state
                if rawdata[i:i+3] == '</>':
                    return i+3
                else:
                    return self.parse_bogus_comment(i)
            tagname = namematch.group().lower()
            # consume and ignore other stuff between the name and the >
            # Note: this is not 100% correct, since we might have things like
            # </tag attr=">">, but looking for > after tha name should cover
            # most of the cases and is much simpler
            gtpos = rawdata.find('>', namematch.end())
            self.handle_endtag(tagname)
            return gtpos+1

        elem = match.group(1).lower() # script or style
        if self.cdata_elem is not None:
            if elem != self.cdata_elem:
                self.handle_data(rawdata[i:gtpos])
                return gtpos

        self.handle_endtag(elem.lower())
        self.clear_cdata_mode()
        return gtpos

    # Overridable -- finish processing of start+end tag: <tag.../>
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    # Overridable -- handle start tag
    def handle_starttag(self, tag, attrs):
        pass

    # Overridable -- handle end tag
    def handle_endtag(self, tag):
        pass

    # Overridable -- handle character reference
    def handle_charref(self, name):
        pass

    # Overridable -- handle entity reference
    def handle_entityref(self, name):
        pass

    # Overridable -- handle data
    def handle_data(self, data):
        pass

    # Overridable -- handle comment
    def handle_comment(self, data):
        pass

    # Overridable -- handle declaration
    def handle_decl(self, decl):
        pass

    # Overridable -- handle processing instruction
    def handle_pi(self, data):
        pass

    def unknown_decl(self, data):
        if self.strict:
            self.error("unknown declaration: %r" % (data,))

    # Internal -- helper to remove special character quoting
    entitydefs = None
    def unescape(self, s):
        if '&' not in s:
            return s
        # -------------------------------------------------------- change start
        if PY3:
            def replaceEntities(s):
                s = s.groups()[0]
                try:
                    if s[0] == "#":
                        s = s[1:]
                        if s[0] in ['x','X']:
                            c = int(s[1:], 16)
                        else:
                            c = int(s)
                        return chr(c)
                except ValueError:
                    return '&#'+ s +';'
                else:
                    # Cannot use name2codepoint directly, because HTMLParser
                    # supports apos, which is not part of HTML 4
                    import html.entities
                    if HTMLParser.entitydefs is None:
                        entitydefs = HTMLParser.entitydefs = {'apos':"'"}
                        for k, v in html.entities.name2codepoint.items():
                            entitydefs[k] = chr(v)
                    try:
                        return self.entitydefs[s]
                    except KeyError:
                        return '&'+s+';'
    
            return re.sub(r"&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));",
                          replaceEntities, s, flags=re.ASCII)
        else:
            def replaceEntities(s):
                s = s.groups()[0]
                try:
                    if s[0] == "#":
                        s = s[1:]
                        if s[0] in ['x','X']:
                            c = int(s[1:], 16)
                        else:
                            c = int(s)
                        return unichr(c)
                except ValueError:
                    return '&#'+s+';'
                else:
                    # Cannot use name2codepoint directly, because HTMLParser supports apos,
                    # which is not part of HTML 4
                    import htmlentitydefs
                    if HTMLParser.entitydefs is None:
                        entitydefs = HTMLParser.entitydefs = {'apos':"'"}
                        for k, v in htmlentitydefs.name2codepoint.iteritems():
                            entitydefs[k] = unichr(v)
                    try:
                        return self.entitydefs[s]
                    except KeyError:
                        return '&'+s+';'
    
            return re.sub(r"&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));", replaceEntities, s)
        # -------------------------------------------------------- change end        
########NEW FILE########
__FILENAME__ = html_parser
# coding: utf-8

"""
    HTMLParser for Python 2.x and 3.x
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The HTMLParser has problems with the correct handling of <script>...</script>
    and <style>...</style> areas.
       
    It was fixed with v2.7.3 and 3.2.3, see:
        http://www.python.org/download/releases/2.7.3/
        http://www.python.org/download/releases/3.2.3/
    see also:
        http://bugs.python.org/issue670664#msg146770
        
    :copyleft: 2011-2012 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""


try:
    import HTMLParser as OriginHTMLParser
except ImportError:
    from html import parser as OriginHTMLParser # python 3


if hasattr(OriginHTMLParser, "cdata_elem"):
    # Current python version is patched -> use the original
    HTMLParser = OriginHTMLParser
else:
    # Current python version is not patched -> use own patched version
    from creole.shared.HTMLParsercompat import HTMLParser

########NEW FILE########
__FILENAME__ = markup_table

class MarkupTable(object):
    """
    Container for holding table data and render the data in creole markup.
    Format every cell width to the same col width.
    """
    def __init__(self, head_prefix="= ", auto_width=True, debug_msg=None):
        self.head_prefix = head_prefix
        self.auto_width = auto_width

        if debug_msg is None:
            self.debug_msg = self._non_debug
        else:
            self.debug_msg = debug_msg

        self.rows = []
        self.row_index = None
        self.has_header = False

    def _non_debug(self, *args):
        pass

    def add_tr(self):
        self.debug_msg("Table.add_tr", "")
        self.rows.append([])
        self.row_index = len(self.rows) - 1

    def add_th(self, text):
        self.has_header = True
        self.add_td(self.head_prefix + text)

    def add_td(self, text):
        if self.row_index == None:
            self.add_tr()

        self.debug_msg("Table.add_td", text)
        self.rows[self.row_index].append(text)

    def _get_preformat_info(self):
        cells = []
        for row in self.rows:
            line_cells = []
            for cell in row:
                cell = cell.strip()
                if cell != "":
                    if self.head_prefix and cell.startswith(self.head_prefix):
                        cell += " " # Headline
                    else:
                        cell = " %s " % cell # normal cell
                line_cells.append(cell)
            cells.append(line_cells)

        # Build a list of max len for every column
        widths = [max(map(len, col)) for col in zip(*cells)]

        return cells, widths

    def get_table_markup(self):
        """ return the table data in creole/textile markup. """
        if not self.auto_width:
            lines = []
            for row in self.rows:
                lines.append("|" + "|".join([cell for cell in row]) + "|")
        else:
            # preformat every table cell
            cells, widths = self._get_preformat_info()

            # Join every line with ljust
            lines = []
            for row in cells:
                cells = [cell.ljust(width) for cell, width in zip(row, widths)]
                lines.append("|" + "|".join(cells) + "|")

        result = "\n".join(lines)

        self.debug_msg("Table.get_table_markup", result)
        return result

    def get_rest_table(self):
        """ return the table data in ReSt markup. """
        # preformat every table cell
        cells, widths = self._get_preformat_info()

        separator_line = "+%s+" % "+".join(["-"*width for width in widths])
        headline_separator = "+%s+" % "+".join(["="*width for width in widths])

        lines = []
        for no, row in enumerate(cells):
            if no == 1 and self.has_header:
                lines.append(headline_separator)
            else:
                lines.append(separator_line)

            # Join every line with ljust
            cells = [cell.ljust(width) for cell, width in zip(row, widths)]
            lines.append("|" + "|".join(cells) + "|")

        lines.append(separator_line)

        return "\n".join(lines)

if __name__ == '__main__':
    import doctest
    print(doctest.testmod())

########NEW FILE########
__FILENAME__ = unknown_tags
#!/usr/bin/env python
# coding: utf-8


"""
    python-creole
    ~~~~~~~~~~~~~


    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

from xml.sax.saxutils import escape


def _mask_content(emitter, node, mask_tag):
    attrs = node.get_attrs_as_string()
    if attrs:
        attrs = " " + attrs

    tag_data = {
        "tag": node.kind,
        "attrs": attrs,
        "mask_tag": mask_tag,
    }

    content = emitter.emit_children(node)
    if not content:
        # single tag
        return "<<%(mask_tag)s>><%(tag)s%(attrs)s /><</%(mask_tag)s>>" % tag_data

    start_tag = "<<%(mask_tag)s>><%(tag)s%(attrs)s><</%(mask_tag)s>>" % tag_data
    end_tag = "<<%(mask_tag)s>></%(tag)s><</%(mask_tag)s>>" % tag_data

    return start_tag + content + end_tag



def raise_unknown_node(emitter, node):
    """
    unknown_emit callable for Html2CreoleEmitter
    
    Raise NotImplementedError on unknown tags.
    """
    content = emitter.emit_children(node)
    raise NotImplementedError(
        "Node from type '%s' is not implemented! (child content: %r)" % (
            node.kind, content
        )
    )


def use_html_macro(emitter, node):
    """
    unknown_emit callable for Html2CreoleEmitter
    
    Use the <<html>> macro to mask unknown tags.
    """
    return _mask_content(emitter, node, mask_tag="html")


def preformat_unknown_nodes(emitter, node):
    """
    Put unknown tags in a <pre> area.
    
    Usefull for html2textile.emitter.TextileEmitter()
    """
    return _mask_content(emitter, node, mask_tag="pre")


def escape_unknown_nodes(emitter, node):
    """
    unknown_emit callable for Html2CreoleEmitter
    
    All unknown tags should be escaped.
    """
    attrs = node.get_attrs_as_string()
    if attrs:
        attrs = " " + attrs

    tag_data = {
        "tag": node.kind,
        "attrs": attrs,
    }

    content = emitter.emit_children(node)
    if not content:
        # single tag
        return escape("<%(tag)s%(attrs)s />" % tag_data)

    start_tag = escape("<%(tag)s%(attrs)s>" % tag_data)
    end_tag = escape("</%(tag)s>" % tag_data)

    return start_tag + content + end_tag


def transparent_unknown_nodes(emitter, node):
    """
    unknown_emit callable for Html2CreoleEmitter 
    
    Remove all unknown html tags and show only
    their child nodes' content.
    """
    return emitter._emit_content(node)

########NEW FILE########
__FILENAME__ = utils
# coding: utf-8


"""
    python creole utilities
    ~~~~~~~~~~~~~~~~~~~~~~~

    :copyleft: 2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import shlex

from creole.py3compat import TEXT_TYPE, PY3, repr2

try:
    from pygments import lexers
    from pygments.formatters import HtmlFormatter
    PYGMENTS = True
except ImportError:
    PYGMENTS = False


# For string2dict()
KEYWORD_MAP = {
    "True": True,
    "False": False,
    "None": None,
}

def string2dict(raw_content, encoding="utf-8"):
    """
    convert a string into a dictionary. e.g.:

    >>> string2dict('key1="value1" key2="value2"')
    {'key2': 'value2', 'key1': 'value1'}

    See test_creole2html.TestString2Dict()
    """
    if not PY3 and isinstance(raw_content, TEXT_TYPE):
        # shlex.split doesn't work with unicode?!?
        raw_content = raw_content.encode(encoding)

    parts = shlex.split(raw_content)

    result = {}
    for part in parts:
        key, value = part.split("=", 1)

        if value in KEYWORD_MAP:
            # True False or None
            value = KEYWORD_MAP[value]
        else:
            # A number?
            try:
                value = int(value.strip("'\""))
            except ValueError:
                pass

        result[key] = value

    return result


def dict2string(d):
    """
    FIXME: Find a better was to do this.

    >>> dict2string({'foo':"bar", "no":123})
    "foo='bar' no=123"

    >>> dict2string({"foo":'bar', "no":"ABC"})
    "foo='bar' no='ABC'"

    See test_creole2html.TestDict2String()
    """
    attr_list = []
    for key, value in sorted(d.items()):
        value_string = repr2(value)
        attr_list.append("%s=%s" % (key, value_string))
    return " ".join(attr_list)


def get_pygments_formatter():
    if PYGMENTS:
        return HtmlFormatter(lineos = True, encoding='utf-8',
                             style='colorful', outencoding='utf-8',
                             cssclass='pygments')


def get_pygments_lexer(source_type, code):
    if PYGMENTS:
        try:
            return lexers.get_lexer_by_name(source_type)
        except:
            return lexers.guess_lexer(code)
    else:
        return None


if __name__ == "__main__":
    import doctest
    print(doctest.testmod())

########NEW FILE########
__FILENAME__ = all_tests
#!/usr/bin/env python
# coding: utf-8

"""
    collects all existing unittests
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyleft: 2008-2012 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

from doctest import testmod
import os
import sys
import time
import unittest

try:
    import creole
except ImportError as err:
    # running tests, but creole is not in sys.path
    raise ImportError("Seems that pyhton-creole is not installed, correctly: %s" % err)

from creole.tests.test_creole2html import TestCreole2html, TestCreole2htmlMarkup, TestStr2Dict, TestDict2String
from creole.tests.test_cross_compare_all import CrossCompareTests
from creole.tests.test_cross_compare_creole import CrossCompareCreoleTests
from creole.tests.test_cross_compare_rest import CrossCompareReStTests
from creole.tests.test_cross_compare_textile import CrossCompareTextileTests
from creole.tests.test_html2creole import TestHtml2Creole, TestHtml2CreoleMarkup
from creole.tests.test_rest2html import ReSt2HtmlTests
from creole.tests.test_setup_utils import SetupUtilsTests
from creole.tests.test_utils import UtilsTests
from creole.tests.utils.utils import MarkupTest

import creole.tests


SKIP_DIRS = (".settings", ".git", "dist", "python_creole.egg-info")
SKIP_FILES = ("setup.py", "test.py")


if "-v" in sys.argv or "--verbosity" in sys.argv:
    VERBOSE = 2
elif "-q" in sys.argv or "--quite" in sys.argv:
    VERBOSE = 0
else:
    VERBOSE = 1


def run_all_doctests(verbosity=None):
    """
    run all python-creole DocTests
    """
    start_time = time.time()
    if verbosity is None:
        verbosity = VERBOSE

    path = os.path.abspath(os.path.dirname(creole.__file__))
    if verbosity >= 2:
        print("")
        print("_" * 79)
        print("Running %r DocTests:\n" % path)

    total_files = 0
    total_doctests = 0
    total_attempted = 0
    total_failed = 0
    for root, dirs, filelist in os.walk(path, followlinks=True):
        for skip_dir in SKIP_DIRS:
            if skip_dir in dirs:
                dirs.remove(skip_dir) # don't visit this directories

        for filename in filelist:
            if not filename.endswith(".py"):
                continue
            if filename in SKIP_FILES:
                continue

            total_files += 1

            sys.path.insert(0, root)
            try:
                m = __import__(filename[:-3])
            except ImportError as err:
                if verbosity >= 2:
                    print("***DocTest import %s error*** %s" % (filename, err))
            except Exception as err:
                if verbosity >= 2:
                    print("***DocTest %s error*** %s" % (filename, err))
            else:
                failed, attempted = testmod(m)
                total_attempted += attempted
                total_failed += failed
                if attempted or failed:
                    total_doctests += 1

                if attempted and not failed:
                    filepath = os.path.join(root, filename)
                    if verbosity <= 1:
                        sys.stdout.write(".")
                    elif verbosity >= 2:
                        print("DocTest in %s OK (failed=%i, attempted=%i)" % (
                            filepath, failed, attempted
                        ))
            finally:
                del sys.path[0]

    duration = time.time() - start_time
    print("")
    print("-"*70)
    print("Ran %i DocTests from %i files in %.3fs: failed=%i, attempted=%i\n\n" % (
        total_doctests, total_files, duration, total_failed, total_attempted
    ))


def run_unittests(verbosity=None):
    """
    run all python-creole unittests with unittest CLI TestProgram()
    """
    if verbosity is None:
        verbosity = VERBOSE

    if verbosity >= 2:
        print("")
        print("_" * 79)
        print("Running Unittests:\n")

    if sys.version_info >= (2, 7):
        unittest.main(verbosity=verbosity)
    else:
        unittest.main()


if __name__ == '__main__':
    # for e.g.:
    #    coverage run creole/tests/all_tests.py
    run_all_doctests()
    run_unittests()

########NEW FILE########
__FILENAME__ = test_cli
#!/usr/bin/env python
# coding: utf-8

"""
    unittest for CLI
    ~~~~~~~~~~~~~~~~

    :copyleft: 2013 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import unittest
import sys
import tempfile

from creole.tests.utils.base_unittest import BaseCreoleTest
from creole.cmdline import cli_creole2html, cli_html2creole, cli_html2rest, \
    cli_html2textile


class CreoleCLITests(BaseCreoleTest):
    def setUp(self):
        super(CreoleCLITests, self).setUp()
        self._old_argv = sys.argv[:]
    def tearDown(self):
        super(CreoleCLITests, self).tearDown()
        sys.argv = self._old_argv

    def _test_convert(self, source_content, dest_content, cli_func):
        source_file = tempfile.NamedTemporaryFile()
        sourcefilepath = source_file.name
        source_file.write(source_content)
        source_file.seek(0)

        dest_file = tempfile.NamedTemporaryFile()
        destfilepath = dest_file.name

        sys.argv += [sourcefilepath, destfilepath]
        cli_func()

        dest_file.seek(0)
        result_content = dest_file.read()

#         print(dest_content)
        self.assertEqual(result_content, dest_content)

    def test_creole2html(self):
        self._test_convert(
            source_content=b"= test creole2html =",
            dest_content=b"<h1>test creole2html</h1>",
            cli_func=cli_creole2html
        )

    def test_html2creole(self):
        self._test_convert(
            source_content=b"<h1>test html2creole</h1>",
            dest_content=b"= test html2creole",
            cli_func=cli_html2creole
        )

    def test_html2rest(self):
        self._test_convert(
            source_content=b"<h1>test html2rest</h1>",
            dest_content=(b"==============\n"
                "test html2rest\n"
                "=============="
            ),
            cli_func=cli_html2rest
        )

    def test_html2textile(self):
        self._test_convert(
            source_content=b"<h1>test html2textile</h1>",
            dest_content=b"h1. test html2textile",
            cli_func=cli_html2textile
        )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_creole2html
#!/usr/bin/env python
# coding: utf-8

"""
    creole2html unittest
    ~~~~~~~~~~~~~~~~~~~~

    Here are only some tests witch doesn't work in the cross compare tests.

    Info: There exist some situations with different whitespace handling
        between creol2html and html2creole.

    Test the creole markup.

    :copyleft: 2008-2014 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import sys
import unittest
import warnings

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO # python 3

try:
    from pygments import highlight
    PYGMENTS = True
except ImportError:
    PYGMENTS = False

from creole.tests.utils.base_unittest import BaseCreoleTest
from creole.tests import test_macros
from creole.py3compat import PY3

from creole import creole2html
from creole.shared import example_macros
from creole.shared.utils import string2dict, dict2string


class TestCreole2html(BaseCreoleTest):
    """
    Tests around creole2html API and macro function.
    """
    def setUp(self):
        # For fallback tests
        example_macros.PYGMENTS = PYGMENTS

    def test_stderr(self):
        """
        Test if the traceback information send to a stderr handler.
        """
        my_stderr = StringIO()
        creole2html(
            markup_string="<<notexist1>><<notexist2>><</notexist2>>",
            emitter_kwargs={
                "verbose":2,
                "stderr":my_stderr,
            }
        )
        error_msg = my_stderr.getvalue()

        # Note:
        # The error message change if macros are a dict or are a object!

        # Check if we get a traceback information into our stderr handler
        must_have = (
            "Traceback", "'notexist1'", "'notexist2'",
        )
        for part in must_have:
            tb_lines = [" -"*40]
            tb_lines += error_msg.splitlines()
            tb_lines += [" -"*40]
            tb = "\n".join([" >>> %s" % l for l in tb_lines])
            msg = "%r not found in:\n%s" % (part, tb)
            # TODO: use assertIn if python 2.6 will be not support anymore.
            if part not in error_msg:
                raise self.failureException(msg)

    def test_example_macros1(self):
        """
        Test the default "html" macro, found in ./creole/default_macros.py
        """
        html = creole2html(
            markup_string="<<html>><p>foo</p><</html>><bar?>",
            emitter_kwargs={
                "verbose":1,
                "macros":example_macros,
                "stderr":sys.stderr,
            }
        )
        self.assertEqual(html, '<p>foo</p>\n<p>&lt;bar?&gt;</p>')

    def test_example_macros2(self):
        html = creole2html(
            markup_string="<<html>>{{{&lt;nocode&gt;}}}<</html>>",
            emitter_kwargs={
                "verbose":1,
                "macros":example_macros,
                "stderr":sys.stderr,
            }
        )
        self.assertEqual(html, '{{{&lt;nocode&gt;}}}')

    def test_example_macros3(self):
        html = creole2html(
            markup_string="<<html>>1<</html>><<html>>2<</html>>",
            emitter_kwargs={
                "verbose":1,
                "macros":example_macros,
                "stderr":sys.stderr,
            }
        )
        self.assertEqual(html, '1\n2')

    def test_macro_dict(self):
        """
        simple test for the "macro API"
        """
        def test(text, foo, bar):
            return "|".join([foo, bar, text])

        html = creole2html(
            markup_string="<<test bar='b' foo='a'>>c<</test>>",
            emitter_kwargs={
                "verbose":1,
                "macros":{"test":test},
                "stderr":sys.stderr,
            }
        )
        self.assertEqual(html, 'a|b|c')

    def test_macro_callable(self):
        """
        simple test for the "macro API"
        """
        def testmacro():
            pass

        self.assertRaises(TypeError,
            creole2html,
            markup_string="<<test no=1 arg2='foo'>>bar<</test>>",
            emitter_kwargs={
                "verbose":1,
                "macros":testmacro,
                "stderr":sys.stderr,
            }
        )

    def test_macro_wrong_arguments_with_error_report(self):
        """
        simple test for the "macro API"
        """
        def test(text, foo):
            pass
        my_stderr = StringIO()

        html = creole2html(
            markup_string="<<test bar='foo'>>c<</test>>",
            emitter_kwargs={
                "verbose":2,
                "macros":{"test":test},
                "stderr":my_stderr,
            }
        )
        self.assertEqual(html,
            "[Error: Macro 'test' error: test() got an unexpected keyword argument 'bar']"
        )
        error_msg = my_stderr.getvalue()

        # Check traceback information into our stderr handler
        must_have = (
            "TypeError: test() got an unexpected keyword argument 'bar'",
            "sourceline: 'def test(text, foo):' from",
            "tests/test_creole2html.py",
        )
        for part in must_have:
            self.assertIn(part, error_msg)


    def test_macro_wrong_arguments_quite(self):
        """
        simple test for the "macro API"
        """
        def test(text, foo):
            pass
        my_stderr = StringIO()

        html = creole2html(
            markup_string="<<test bar='foo'>>c<</test>>",
            emitter_kwargs={
                "verbose":1,
                "macros":{"test":test},
                "stderr":my_stderr,
            }
        )
        self.assertEqual(html,
            "[Error: Macro 'test' error: test() got an unexpected keyword argument 'bar']"
        )
        error_msg = my_stderr.getvalue()
        self.assertEqual(error_msg, "")

    def test_code_macro(self):
        if not PYGMENTS:
            # TODO: Use @unittest.skipIf if python 2.6 will be not support anymore
            warnings.warn("Skip test, because 'pygments' is not installed.")
            return

        self.assert_creole2html(r"""
            Here a simple code macro test:
            <<code ext=".py">>
            for i in xrange(10):
                print('hello world')
            <</code>>
            """, """
            <p>Here a simple code macro test:</p>
            <div class="pygments"><pre><span class="k">for</span> <span class="n">i</span> <span class="ow">in</span> <span class="nb">xrange</span><span class="p">(</span><span class="mi">10</span><span class="p">):</span><br />
                <span class="k">print</span><span class="p">(</span><span class="s">&#39;hello world&#39;</span><span class="p">)</span><br />
            </pre></div><br />
            """,
            macros={'code': example_macros.code}
        )

    def test_code_macro_fallback(self):
        # force to use fallback. Will be reset in self.setUp()
        example_macros.PYGMENTS = False

        self.assert_creole2html(
            r"""
            Here a simple code macro test:
            <<code ext=".py">>
            for i in xrange(10):
                print('hello world')
            <</code>>
            """, """
            <p>Here a simple code macro test:</p>
            <pre>for i in xrange(10):
                print('hello world')</pre>
            """,
            macros={'code': example_macros.code}
        )

    def test_code_macro_fallback_escape(self):
        # force to use fallback. Will be reset in self.setUp()
        example_macros.PYGMENTS = False

        self.assert_creole2html(
            r"""
            <<code ext=".py">>
            print('This >>should<< be escaped!')
            <</code>>
            """, """
            <pre>print('This &gt;&gt;should&lt;&lt; be escaped!')</pre>
            """,
            macros={'code': example_macros.code}
        )




class TestCreole2htmlMarkup(BaseCreoleTest):

    def test_creole_basic(self):
        out_string = creole2html("a text line.")
        self.assertEqual(out_string, "<p>a text line.</p>")

    def test_lineendings(self):
        """ Test all existing lineending version """
        out_string = creole2html("first\nsecond")
        self.assertEqual(out_string, "<p>first<br />\nsecond</p>")

        out_string = creole2html("first\rsecond")
        self.assertEqual(out_string, "<p>first<br />\nsecond</p>")

        out_string = creole2html("first\r\nsecond")
        self.assertEqual(out_string, "<p>first<br />\nsecond</p>")

    #--------------------------------------------------------------------------

    def test_creole_linebreak(self):
        self.assert_creole2html(r"""
            Force\\linebreak
        """, """
            <p>Force<br />
            linebreak</p>
        """)

    def test_html_lines(self):
        self.assert_creole2html(r"""
            This is a normal Text block witch would
            escape html chars like < and > ;)

            So you can't insert <html> directly.

            <p>This escaped, too.</p>
        """, """
            <p>This is a normal Text block witch would<br />
            escape html chars like &lt; and &gt; ;)</p>

            <p>So you can't insert &lt;html&gt; directly.</p>

            <p>&lt;p&gt;This escaped, too.&lt;/p&gt;</p>
        """)

    def test_escape_char(self):
        self.assert_creole2html(r"""
            ~#1
            http://domain.tld/~bar/
            ~http://domain.tld/
            [[Link]]
            ~[[Link]]
        """, """
            <p>#1<br />
            <a href="http://domain.tld/~bar/">http://domain.tld/~bar/</a><br />
            http://domain.tld/<br />
            <a href="Link">Link</a><br />
            [[Link]]</p>
        """)

    def test_cross_paragraphs(self):
        self.assert_creole2html(r"""
            Bold and italics should //not be...

            ...able// to **cross

            paragraphs.**
        """, """
            <p>Bold and italics should //not be...</p>

            <p>...able// to **cross</p>

            <p>paragraphs.**</p>
        """)

    def test_list_special(self):
        """
        optional whitespace before the list
        """
        self.assert_creole2html(r"""
            * Item 1
            ** Item 1.1
             ** Item 1.2
                ** Item 1.3
                    * Item2

                # one
              ## two
        """, """
        <ul>
            <li>Item 1
            <ul>
                <li>Item 1.1</li>
                <li>Item 1.2</li>
                <li>Item 1.3</li>
            </ul></li>
            <li>Item2</li>
        </ul>
        <ol>
            <li>one
            <ol>
                <li>two</li>
            </ol></li>
        </ol>
        """)

    def test_macro_basic(self):
        """
        Test the three diferent macro types with a "unittest macro"
        """
        self.assert_creole2html(r"""
            There exist three different macro types:
            A <<test_macro1 args="foo1">>bar1<</test_macro1>> in a line...
            ...a single <<test_macro1 foo="bar">> tag,
            or: <<test_macro1 a=1 b=2 />> closed...

            a macro block:
            <<test_macro2 char="|">>
            the
            text
            <</test_macro2>>
            the end
        """, r"""
            <p>There exist three different macro types:<br />
            A [test macro1 - kwargs: args='foo1',text='bar1'] in a line...<br />
            ...a single [test macro1 - kwargs: foo='bar',text=None] tag,<br />
            or: [test macro1 - kwargs: a=1,b=2,text=None] closed...</p>

            <p>a macro block:</p>
            the|text
            <p>the end</p>
        """,
            macros=test_macros,
        )

    def test_macro_html1(self):
        self.assert_creole2html(r"""
                html macro:
                <<html>>
                <p><<this is broken 'html', but it will be pass throu>></p>
                <</html>>

                inline: <<html>>&#x7B;...&#x7D;<</html>> code
            """, r"""
                <p>html macro:</p>
                <p><<this is broken 'html', but it will be pass throu>></p>

                <p>inline: &#x7B;...&#x7D; code</p>
            """,
            macros=example_macros,
        )

    def test_macro_not_exist1(self):
        """
        not existing macro with creole2html.HtmlEmitter(verbose=1):
        A error message should be insertet into the generated code

        Two tests: with verbose=1 and verbose=2, witch write a Traceback
        information to a given "stderr"
        """
        source_string = r"""
            macro block:
            <<notexists>>
            foo bar
            <</notexists>>

            inline macro:
            <<notexisttoo foo="bar">>
        """
        should_string = r"""
            <p>macro block:</p>
            [Error: Macro 'notexists' doesn't exist]

            <p>inline macro:<br />
            [Error: Macro 'notexisttoo' doesn't exist]
            </p>
        """

        self.assert_creole2html(source_string, should_string, verbose=1)

        #----------------------------------------------------------------------
        # Test with verbose=2 ans a StringIO stderr handler

    def test_wrong_macro_syntax(self):
        self.assert_creole2html(r"""
                wrong macro line:
                <<summary>Some funky page summary.<</summary>>
            """, r"""
                <p>wrong macro line:<br />
                [Error: Wrong macro arguments: '>Some funky page summary.<</summary' for macro 'summary' (maybe wrong macro tag syntax?)]
                </p>
            """, # verbose=True
        )

    def test_macro_not_exist2(self):
        """
        not existing macro with creole2html.HtmlEmitter(verbose=0):

        No error messages should be inserted.
        """
        self.assert_creole2html(r"""
            macro block:
            <<notexists>>
            foo bar
            <</notexists>>

            inline macro:
            <<notexisttoo foo="bar">>
        """, r"""
            <p>macro block:</p>

            <p>inline macro:<br />
            </p>
        """, verbose=False
        )


    def test_toc_simple(self):
        """
        Simple test to check the table of content is correctly generated.
        """
        self.assert_creole2html(r"""
            <<toc>>
            = Headline
        """, """
            <ul>
                <li><a href="#Headline">Headline</a></li>
            </ul>
            <a name="Headline"><h1>Headline</h1></a>
        """)

    def test_toc_more_headlines(self):
        self.assert_creole2html(r"""
            Between text and toc must be a newline.

            <<toc>>
            = Headline 1
            == Sub-Headline 1.1
            == Sub-Headline 1.2
            = Headline 2
            == Sub-Headline 2.1
            == Sub-Headline 2.2
        """, """
            <p>Between text and toc must be a newline.</p>

            <ul>
                <li><a href="#Headline 1">Headline 1</a></li>
                <ul>
                    <li><a href="#Sub-Headline 1.1">Sub-Headline 1.1</a></li>
                    <li><a href="#Sub-Headline 1.2">Sub-Headline 1.2</a></li>
                </ul>
                <li><a href="#Headline 2">Headline 2</a></li>
                <ul>
                    <li><a href="#Sub-Headline 2.1">Sub-Headline 2.1</a></li>
                    <li><a href="#Sub-Headline 2.2">Sub-Headline 2.2</a></li>
                </ul>
            </ul>
            <a name="Headline 1"><h1>Headline 1</h1></a>
            <a name="Sub-Headline 1.1"><h2>Sub-Headline 1.1</h2></a>
            <a name="Sub-Headline 1.2"><h2>Sub-Headline 1.2</h2></a>
            <a name="Headline 2"><h1>Headline 2</h1></a>
            <a name="Sub-Headline 2.1"><h2>Sub-Headline 2.1</h2></a>
            <a name="Sub-Headline 2.2"><h2>Sub-Headline 2.2</h2></a>
        """)

    def test_toc_chaotic_headlines(self):
        self.assert_creole2html(r"""
            <<toc>>
            = level 1
            === level 3
            == level 2
            ==== level 4
            = level 1
        """, """
            <ul>
                <li><a href="#level 1">level 1</a></li>
                <ul>
                    <ul>
                        <li><a href="#level 3">level 3</a></li>
                    </ul>
                    <li><a href="#level 2">level 2</a></li>
                    <ul>
                        <ul>
                            <li><a href="#level 4">level 4</a></li>
                        </ul>
                    </ul>
                </ul>
                <li><a href="#level 1">level 1</a></li>
            </ul>
            <a name="level 1"><h1>level 1</h1></a>
            <a name="level 3"><h3>level 3</h3></a>
            <a name="level 2"><h2>level 2</h2></a>
            <a name="level 4"><h4>level 4</h4></a>
            <a name="level 1"><h1>level 1</h1></a>
        """)

    def test_toc_depth_1(self):
        self.assert_creole2html(r"""
            <<toc depth=1>>
            = Headline 1
            == Sub-Headline 1.1
            === Sub-Sub-Headline 1.1.1
            === Sub-Sub-Headline 1.1.2
            == Sub-Headline 1.2
            = Headline 2
            == Sub-Headline 2.1
            == Sub-Headline 2.2
            === Sub-Sub-Headline 2.2.1
        """, """
            <ul>
                <li><a href="#Headline 1">Headline 1</a></li>
                <li><a href="#Headline 2">Headline 2</a></li>
            </ul>
            <a name="Headline 1"><h1>Headline 1</h1></a>
            <a name="Sub-Headline 1.1"><h2>Sub-Headline 1.1</h2></a>
            <a name="Sub-Sub-Headline 1.1.1"><h3>Sub-Sub-Headline 1.1.1</h3></a>
            <a name="Sub-Sub-Headline 1.1.2"><h3>Sub-Sub-Headline 1.1.2</h3></a>
            <a name="Sub-Headline 1.2"><h2>Sub-Headline 1.2</h2></a>
            <a name="Headline 2"><h1>Headline 2</h1></a>
            <a name="Sub-Headline 2.1"><h2>Sub-Headline 2.1</h2></a>
            <a name="Sub-Headline 2.2"><h2>Sub-Headline 2.2</h2></a>
            <a name="Sub-Sub-Headline 2.2.1"><h3>Sub-Sub-Headline 2.2.1</h3></a>
        """)

    def test_toc_depth_2(self):
        self.assert_creole2html(r"""
            <<toc depth=2>>
            = Headline 1
            == Sub-Headline 1.1
            === Sub-Sub-Headline 1.1.1
            === Sub-Sub-Headline 1.1.2
            == Sub-Headline 1.2
            = Headline 2
            == Sub-Headline 2.1
            == Sub-Headline 2.2
            === Sub-Sub-Headline 2.2.1
        """, """
            <ul>
                <li><a href="#Headline 1">Headline 1</a></li>
                <ul>
                    <li><a href="#Sub-Headline 1.1">Sub-Headline 1.1</a></li>
                    <li><a href="#Sub-Headline 1.2">Sub-Headline 1.2</a></li>
                </ul>
                <li><a href="#Headline 2">Headline 2</a></li>
                <ul>
                    <li><a href="#Sub-Headline 2.1">Sub-Headline 2.1</a></li>
                    <li><a href="#Sub-Headline 2.2">Sub-Headline 2.2</a></li>
                </ul>
            </ul>
            <a name="Headline 1"><h1>Headline 1</h1></a>
            <a name="Sub-Headline 1.1"><h2>Sub-Headline 1.1</h2></a>
            <a name="Sub-Sub-Headline 1.1.1"><h3>Sub-Sub-Headline 1.1.1</h3></a>
            <a name="Sub-Sub-Headline 1.1.2"><h3>Sub-Sub-Headline 1.1.2</h3></a>
            <a name="Sub-Headline 1.2"><h2>Sub-Headline 1.2</h2></a>
            <a name="Headline 2"><h1>Headline 2</h1></a>
            <a name="Sub-Headline 2.1"><h2>Sub-Headline 2.1</h2></a>
            <a name="Sub-Headline 2.2"><h2>Sub-Headline 2.2</h2></a>
            <a name="Sub-Sub-Headline 2.2.1"><h3>Sub-Sub-Headline 2.2.1</h3></a>
        """)

    def test_toc_depth_3(self):
        self.assert_creole2html(r"""
            <<toc depth=3>>
            = Headline 1
            == Sub-Headline 1.1
            === Sub-Sub-Headline 1.1.1
            === Sub-Sub-Headline 1.1.2
            == Sub-Headline 1.2
            = Headline 2
            == Sub-Headline 2.1
            == Sub-Headline 2.2
            === Sub-Sub-Headline 2.2.1
        """, """
            <ul>
                <li><a href="#Headline 1">Headline 1</a></li>
                <ul>
                    <li><a href="#Sub-Headline 1.1">Sub-Headline 1.1</a></li>
                    <ul>
                        <li><a href="#Sub-Sub-Headline 1.1.1">Sub-Sub-Headline 1.1.1</a></li>
                        <li><a href="#Sub-Sub-Headline 1.1.2">Sub-Sub-Headline 1.1.2</a></li>
                    </ul>
                    <li><a href="#Sub-Headline 1.2">Sub-Headline 1.2</a></li>
                </ul>
                <li><a href="#Headline 2">Headline 2</a></li>
                <ul>
                    <li><a href="#Sub-Headline 2.1">Sub-Headline 2.1</a></li>
                    <li><a href="#Sub-Headline 2.2">Sub-Headline 2.2</a></li>
                    <ul>
                        <li><a href="#Sub-Sub-Headline 2.2.1">Sub-Sub-Headline 2.2.1</a></li>
                    </ul>
                </ul>
            </ul>
            <a name="Headline 1"><h1>Headline 1</h1></a>
            <a name="Sub-Headline 1.1"><h2>Sub-Headline 1.1</h2></a>
            <a name="Sub-Sub-Headline 1.1.1"><h3>Sub-Sub-Headline 1.1.1</h3></a>
            <a name="Sub-Sub-Headline 1.1.2"><h3>Sub-Sub-Headline 1.1.2</h3></a>
            <a name="Sub-Headline 1.2"><h2>Sub-Headline 1.2</h2></a>
            <a name="Headline 2"><h1>Headline 2</h1></a>
            <a name="Sub-Headline 2.1"><h2>Sub-Headline 2.1</h2></a>
            <a name="Sub-Headline 2.2"><h2>Sub-Headline 2.2</h2></a>
            <a name="Sub-Sub-Headline 2.2.1"><h3>Sub-Sub-Headline 2.2.1</h3></a>
        """)

    def test_toc_with_no_toc(self):
        self.assert_creole2html(r"""
            <<toc>>
            = This is the Headline
            Use {{{<<toc>>}}} to insert a table of contents.
        """, """
            <ul>
                <li><a href="#This is the Headline">This is the Headline</a></li>
            </ul>
            <a name="This is the Headline"><h1>This is the Headline</h1></a>
            <p>Use <tt>&lt;&lt;toc&gt;&gt;</tt> to insert a table of contents.</p>
        """)

    def test_toc_more_then_one_toc(self):
        self.assert_creole2html(r"""
            Not here:
            {{{
            print("<<toc>>")
            }}}

            and onle the first:

            <<toc>>

            <<toc>>
            <<toc>>
            = Headline
            == Sub-Headline
        """, """
            <p>Not here:</p>
            <pre>
            print("&lt;&lt;toc&gt;&gt;")
            </pre>

            <p>and onle the first:</p>

            <ul>
                <li><a href="#Headline">Headline</a></li>
                <ul>
                    <li><a href="#Sub-Headline">Sub-Headline</a></li>
                </ul>
            </ul>

            <p>&lt;&lt;toc&gt;&gt;<br />
            &lt;&lt;toc&gt;&gt;</p>
            <a name="Headline"><h1>Headline</h1></a>
            <a name="Sub-Headline"><h2>Sub-Headline</h2></a>
        """)

    def test_toc_headline_before_toc(self):
        self.assert_creole2html(r"""
            = headline
            == sub headline

            <<toc>>

            ok?
        """, """
            <a name="headline"><h1>headline</h1></a>
            <a name="sub headline"><h2>sub headline</h2></a>

            <ul>
                <li><a href="#headline">headline</a></li>
                <ul>
                    <li><a href="#sub headline">sub headline</a></li>
                </ul>
            </ul>

            <p>ok?</p>
        """)

    def test_image(self):
        """ test image tag with different picture text """
        self.assert_creole2html(r"""
            {{foobar1.jpg}}
            {{/path1/path2/foobar2.jpg}}
            {{/path1/path2/foobar3.jpg|foobar3.jpg}}
        """, """
            <p><img src="foobar1.jpg" title="foobar1.jpg" alt="foobar1.jpg" /><br />
            <img src="/path1/path2/foobar2.jpg" title="/path1/path2/foobar2.jpg" alt="/path1/path2/foobar2.jpg" /><br />
            <img src="/path1/path2/foobar3.jpg" title="foobar3.jpg" alt="foobar3.jpg" /></p>
        """)

    def test_image_unknown_extension(self):
        self.assert_creole2html(r"""
            # {{/path/to/image.ext|image ext}} one
            # {{/no/extension|no extension}} two
            # {{/image.xyz}} tree
        """, """
            <ol>
                <li><img src="/path/to/image.ext" title="image ext" alt="image ext" /> one</li>
                <li><img src="/no/extension" title="no extension" alt="no extension" /> two</li>
                <li><img src="/image.xyz" title="/image.xyz" alt="/image.xyz" /> tree</li>
            </ol>
        """)

    def test_links(self):
        self.assert_creole2html(r"""
            [[/foobar/Creole_(Markup)]]
            [[http://de.wikipedia.org/wiki/Creole_(Markup)|Creole@wikipedia]]
        """, """
            <p><a href="/foobar/Creole_(Markup)">/foobar/Creole_(Markup)</a><br />
            <a href="http://de.wikipedia.org/wiki/Creole_(Markup)">Creole@wikipedia</a></p>
        """)

    def test_standalone_hyperlink(self):
        self.assert_creole2html(r"""
                a link to the http://www.pylucid.org page.
            """, """
                <p>a link to the <a href="http://www.pylucid.org">http://www.pylucid.org</a> page.</p>
            """
        )

    def test_wiki_style_line_breaks1(self):
        html = creole2html(
            markup_string=self._prepare_text("""
                wiki style
                linebreaks

                ...and not blog styled.
            """),
            parser_kwargs={"blog_line_breaks":False},
        )
        self.assertEqual(html, self._prepare_text("""
            <p>wiki style linebreaks</p>

            <p>...and not blog styled.</p>
        """))

    def test_wiki_style_line_breaks2(self):
        html = creole2html(
            markup_string=self._prepare_text("""
                **one**
                //two//

                * one
                * two
            """),
            parser_kwargs={"blog_line_breaks":False},
        )
        self.assertEqual(html, self._prepare_text("""
            <p><strong>one</strong> <i>two</i></p>

            <ul>
            \t<li>one</li>
            \t<li>two</li>
            </ul>
        """))

    def test_wiki_style_line_breaks3(self):
        html = creole2html(
            markup_string=self._prepare_text("""
                with blog line breaks, every line break would be convertet into<br />
                with wiki style not.

                This is the first line,\\\\and this is the second.

                new line
                block 1

                new line
                block 2

                end
            """),
            parser_kwargs={"blog_line_breaks":False},
        )
        self.assertEqual(html, self._prepare_text("""
            <p>with blog line breaks, every line break would be convertet into&lt;br /&gt; with wiki style not.</p>

            <p>This is the first line,<br />
            and this is the second.</p>

            <p>new line block 1</p>

            <p>new line block 2</p>

            <p>end</p>
        """))


    def test_headline_spaces(self):
        """
        https://code.google.com/p/python-creole/issues/detail?id=15
        """
        html = creole2html(markup_string="== Headline1 == \n== Headline2== ")
        self.assertEqual(html, self._prepare_text("""
            <h2>Headline1</h2>
            <h2>Headline2</h2>
        """))

    def test_tt(self):
        self.assert_creole2html(r"""
            inline {{{<escaped>}}} and {{{ **not strong** }}}...
            ...and ##**strong** Teletyper## ;)
        """, """
            <p>inline <tt>&lt;escaped&gt;</tt> and <tt> **not strong** </tt>...<br />
            ...and <tt><strong>strong</strong> Teletyper</tt> ;)</p>
        """)

    def test_protocol_in_brackets(self):
        self.assert_creole2html(r"""
            My Server ([[ftp://foo/bar]]) is ok.
        """, """
            <p>My Server (<a href="ftp://foo/bar">ftp://foo/bar</a>) is ok.</p>
        """)
        self.assert_creole2html(r"""
            My Server (ftp://foo/bar) is ok.
        """, """
            <p>My Server (ftp://foo/bar) is ok.</p>
        """)

    def test_protocol_with_brackets(self):
        self.assert_creole2html(r"""
            A http://en.wikipedia.org/wiki/Uri_(Island) link.
        """, """
            <p>A <a href="http://en.wikipedia.org/wiki/Uri_(Island)">http://en.wikipedia.org/wiki/Uri_(Island)</a> link.</p>
        """)

    def test_wrong_protocol(self):
        self.assert_creole2html(r"""
            ~ftp://ok
        """, """
            <p>ftp://ok</p>
        """)
        self.assert_creole2html(r"""
            ftp:
        """, """
            <p>ftp:</p>
        """)
        self.assert_creole2html(r"""
            ftp:/
        """, """
            <p>ftp:/</p>
        """)
        self.assert_creole2html(r"""
            missing space.ftp://ok
        """, """
            <p>missing space.ftp://ok</p>
        """)


class TestStr2Dict(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(
            string2dict('key1="value1" key2="value2"'),
            {'key2': 'value2', 'key1': 'value1'}
        )

    def test_bool(self):
        self.assertEqual(
            string2dict('unicode=True'),
            {'unicode': True}
        )

    def test_mixed1(self):
        self.assertEqual(
            string2dict('A="B" C=1 D=1.1 E=True F=False G=None'),
            {'A': 'B', 'C': 1, 'E': True, 'D': '1.1', 'G': None, 'F': False}
        )

    def test_mixed2(self):
        self.assertEqual(
            string2dict('''key1="'1'" key2='"2"' key3="""'3'""" '''),
            {'key3': 3, 'key2': 2, 'key1': 1}
        )

class TestDict2String(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(
            dict2string({'key':'value'}),
            "key='value'"
        )

    def test_basic2(self):
        self.assertEqual(
            dict2string({'foo':"bar", "no":123}),
            "foo='bar' no=123"
        )
    def test_basic3(self):
        self.assertEqual(
            dict2string({"foo":'bar', "no":"ABC"}),
            "foo='bar' no='ABC'"
        )

if __name__ == '__main__':
    unittest.main(
        verbosity=2
    )

########NEW FILE########
__FILENAME__ = test_cross_compare_all
#!/usr/bin/env python
# coding: utf-8

"""
    cross compare unittest
    ~~~~~~~~~~~~~~~~~~~~~~
    
    Compare all similarities between:
        * creole2html
        * html2creole
        * textile2html (used the python textile module)
        * html2textile

    Note: This only works fine if there is no problematic whitespace handling.
        In this case, we must test in test_creole2html.py or test_html2creole.py

    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import unittest



from creole.tests.utils.base_unittest import BaseCreoleTest


class CrossCompareTests(BaseCreoleTest):
    """
    Cross compare tests for creol2html _and_ html2creole with the same test
    strings. Used BaseCreoleTest.assertCreole()
    """
    def test_bold_italics(self):
        self.cross_compare(
            creole_string=r"""
                **bold** //italics//
                //italics and **bold**.//
                **bold and //italics//.**
            """,
            textile_string="""
                *bold* __italics__
                __italics and *bold*.__
                *bold and __italics__.*
            """,
            html_string="""
                <p><strong>bold</strong> <i>italics</i><br />
                <i>italics and <strong>bold</strong>.</i><br />
                <strong>bold and <i>italics</i>.</strong></p>
            """,
        )
        # Note: In ReSt inline markup may not be nested.
        self.cross_compare(
            html_string="""
                <p><strong>bold</strong> <em>italics</em></p>
            """,
            rest_string="""
                **bold** *italics*
            """,
        )

    def test_bold_italics2(self):
        self.cross_compare(
            creole_string=r"""
                **//bold italics//**
                //**bold italics**//
                //This is **also** good.//
            """,
            textile_string="""
                *__bold italics__*
                __*bold italics*__
                __This is *also* good.__
            """,
            html_string="""
                <p><strong><i>bold italics</i></strong><br />
                <i><strong>bold italics</strong></i><br />
                <i>This is <strong>also</strong> good.</i></p>
            """,
        )

    def test_headlines1(self):
        self.cross_compare(
            creole_string=r"""
                = Section Title 1
                
                == Section Title 2
                
                === Section Title 3
                
                ==== Section Title 4
                
                ===== Section Title 5
                
                ====== Section Title 6
            """,
            textile_string="""
                h1. Section Title 1
                
                h2. Section Title 2
                
                h3. Section Title 3
                
                h4. Section Title 4
                
                h5. Section Title 5
                
                h6. Section Title 6
            """,
            html_string="""
                <h1>Section Title 1</h1>
                
                <h2>Section Title 2</h2>
                
                <h3>Section Title 3</h3>
                
                <h4>Section Title 4</h4>
                
                <h5>Section Title 5</h5>
                
                <h6>Section Title 6</h6>
            """
        )
        self.cross_compare(
            rest_string="""
                ===============
                Section Title 1
                ===============
                
                ---------------
                Section Title 2
                ---------------
                
                Section Title 3
                ===============
                
                Section Title 4
                ---------------
                
                Section Title 5
                ```````````````
                
                Section Title 6
                '''''''''''''''
            """,
            html_string="""
                <h1>Section Title 1</h1>
                <h2>Section Title 2</h2>
                <h3>Section Title 3</h3>
                <h4>Section Title 4</h4>
                <h5>Section Title 5</h5>
                <h6>Section Title 6</h6>
            """
        )

    def test_horizontal_rule(self):
        all_markups = """
            Text before horizontal rule.
            
            ----
            
            Text after the line.
        """
        self.cross_compare(
            creole_string=all_markups,
            #textile_string=all_markups, # FIXME: textile and <hr> ?
            html_string="""
                <p>Text before horizontal rule.</p>
                
                <hr />
                
                <p>Text after the line.</p>
            """
        )
        self.cross_compare(
            rest_string=all_markups,
            html_string="""
                <p>Text before horizontal rule.</p>
                <hr />
                <p>Text after the line.</p>
            """
        )

    def test_link(self):
        self.cross_compare(
            creole_string=r"""
                X [[http://domain.tld|link B]] test.
            """,
            textile_string="""
                X "link B":http://domain.tld test.
            """,
            rest_string="""
                X `link B <http://domain.tld>`_ test.
            """,
            html_string="""
                <p>X <a href="http://domain.tld">link B</a> test.</p>
            """
        )

    def test_link_without_title(self):
        self.cross_compare(
            creole_string=r"""
                [[http://www.pylucid.org]]
            """,
            textile_string="""
                "http://www.pylucid.org":http://www.pylucid.org
            """,
            rest_string="""
                `http://www.pylucid.org <http://www.pylucid.org>`_
            """,
            html_string="""
                <p><a href="http://www.pylucid.org">http://www.pylucid.org</a></p>
            """
        )

    def test_link_with_unknown_protocol(self):
        self.cross_compare(
            creole_string=r"""
                X [[Foo://bar|unknown protocol]] Y
            """,
            textile_string="""
                X "unknown protocol":Foo://bar Y
            """,
            rest_string="""
                X `unknown protocol <Foo://bar>`_ Y
            """,
            html_string="""
                <p>X <a href="Foo://bar">unknown protocol</a> Y</p>
            """
        )

    def test_link_with_at_sign(self):
        self.cross_compare(
            creole_string=r"""
                X [[http://de.wikipedia.org/wiki/Creole_(Markup)|Creole@wikipedia]]
            """,
            textile_string="""
                X "Creole@wikipedia":http://de.wikipedia.org/wiki/Creole_(Markup)
            """,
            html_string="""
                <p>X <a href="http://de.wikipedia.org/wiki/Creole_(Markup)">Creole@wikipedia</a></p>
            """
        )
        self.cross_compare(
            rest_string="""
                X `Creole@wikipedia <http://de.wikipedia.org/wiki/Creole_(Markup)>`_
            """,
            html_string="""
                <p>X <a href="http://de.wikipedia.org/wiki/Creole_(Markup)">Creole&#64;wikipedia</a></p>
            """
        )

    def test_image(self):
        self.cross_compare(
            creole_string=r"""
                a {{/image.jpg|JPG pictures}} and
                a {{/image.jpeg|JPEG pictures}} and
                a {{/image.gif|GIF pictures}} and
                a {{/image.png|PNG pictures}} !
                {{/path1/path2/image|Image without files ext?}}
            """,
            textile_string="""
                a !/image.jpg(JPG pictures)! and
                a !/image.jpeg(JPEG pictures)! and
                a !/image.gif(GIF pictures)! and
                a !/image.png(PNG pictures)! !
                !/path1/path2/image(Image without files ext?)!
            """,
            html_string="""
                <p>a <img src="/image.jpg" title="JPG pictures" alt="JPG pictures" /> and<br />
                a <img src="/image.jpeg" title="JPEG pictures" alt="JPEG pictures" /> and<br />
                a <img src="/image.gif" title="GIF pictures" alt="GIF pictures" /> and<br />
                a <img src="/image.png" title="PNG pictures" alt="PNG pictures" /> !<br />
                <img src="/path1/path2/image" title="Image without files ext?" alt="Image without files ext?" /></p>
            """
        )
        self.cross_compare(
            rest_string="""
                1 |JPG pictures| one
                
                .. |JPG pictures| image:: /image.jpg
                
                2 |JPEG pictures| two
                
                .. |JPEG pictures| image:: /image.jpeg
                
                3 |GIF pictures| tree
                
                .. |GIF pictures| image:: /image.gif
                
                4 |PNG pictures| four
                
                .. |PNG pictures| image:: /image.png
                
                5 |Image without files ext?| five
                
                .. |Image without files ext?| image:: /path1/path2/image
            """,
            html_string="""
                <p>1 <img alt="JPG pictures" src="/image.jpg" /> one</p>
                <p>2 <img alt="JPEG pictures" src="/image.jpeg" /> two</p>
                <p>3 <img alt="GIF pictures" src="/image.gif" /> tree</p>
                <p>4 <img alt="PNG pictures" src="/image.png" /> four</p>
                <p>5 <img alt="Image without files ext?" src="/path1/path2/image" /> five</p>
            """
        )

    def test_link_image(self):
        """ FIXME: ReSt. and linked images """
        self.cross_compare(
            creole_string=r"""
                Linked [[http://example.com/|{{myimage.jpg|example site}} image]]
            """,
            textile_string="""
                Linked "!myimage.jpg(example site)! image":http://example.com/
            """,
            html_string="""
                <p>Linked <a href="http://example.com/"><img src="myimage.jpg" title="example site" alt="example site" /> image</a></p>
            """
        )
#        self.cross_compare(# FIXME: ReSt
#            rest_string="""
#                I recommend you try |PyLucid CMS|_.
#                
#                .. |PyLucid CMS| image:: /images/pylucid.png
#                .. _PyLucid CMS: http://www.pylucid.org/
#            """,
#            html_string="""
#                <p>I recommend you try <a href="http://www.pylucid.org/"><img alt="PyLucid CMS" src="/images/pylucid.png" /></a>.</p>
#            """
#        )

    def test_pre1(self):
        self.cross_compare(
            creole_string=r"""
                {{{
                * no list
                }}}
                """,
            textile_string="""
                <pre>
                * no list
                </pre>
                """,
            html_string="""
                <pre>
                * no list
                </pre>
            """)
        self.cross_compare(# FIXME: Not the best html2rest output
            rest_string="""
                Preformatting text:
                
                ::
                
                    Here some performatting with
                    no `link <http://domain.tld>`_ here.
                    text... end.
                
                Under pre block
            """,
            html_string="""
                <p>Preformatting text:</p>
                <pre>
                Here some performatting with
                no `link &lt;http://domain.tld&gt;`_ here.
                text... end.
                </pre>
                <p>Under pre block</p>
            """
        )


#    def test_pre2(self):
#        """ TODO: html2creole: wrong lineendings """
#        self.cross_compare(
#            creole_string=r"""
#                start
#                
#                {{{
#                * no list
#                }}}
#                
#                end
#                """,
#            textile_string="""
#                start
#                
#                <pre>
#                * no list
#                </pre>
#                
#                end
#                """,
#            html_string="""
#                <p>start</p>
#                
#                <pre>
#                * no list
#                </pre>
#                
#                <p>end</p>
#            """)

    def test_pre_contains_braces(self):
        self.cross_compare(
            creole_string="""
                {{{
                # Closing braces in nowiki:
                if (x != NULL) {
                  for (i = 0) {
                    if (x = 1) {
                      x[i]--;
                  }}}
                }}}
                """,
            textile_string="""
                <pre>
                # Closing braces in nowiki:
                if (x != NULL) {
                  for (i = 0) {
                    if (x = 1) {
                      x[i]--;
                  }}}
                </pre>
                """,
            rest_string="""
                ::
                
                    # Closing braces in nowiki:
                    if (x != NULL) {
                      for (i = 0) {
                        if (x = 1) {
                          x[i]--;
                      }}}
                """,
            html_string="""
                <pre>
                # Closing braces in nowiki:
                if (x != NULL) {
                  for (i = 0) {
                    if (x = 1) {
                      x[i]--;
                  }}}
                </pre>
            """)

    def test_list(self):
        """ Bold, Italics, Links, Pre in Lists """
        self.cross_compare(
            creole_string=r"""
                * **bold** item
                * //italic// item
    
                # item about a [[/foo/bar|certain_page]]
                """,
            textile_string="""
                * *bold* item
                * __italic__ item
    
                # item about a "certain_page":/foo/bar
            """,
            html_string="""
                <ul>
                  <li><strong>bold</strong> item</li>
                  <li><i>italic</i> item</li>
                </ul>
                <ol>
                  <li>item about a <a href="/foo/bar">certain_page</a></li>
                </ol>
            """,
            strip_lines=True
        )

    def test_simple_table(self):
        self.cross_compare(
            creole_string="""
                |= Headline 1 |= Headline 2 |
                | cell one    | cell two    |
                """,
            textile_string="""
                |_. Headline 1|_. Headline 2|
                |cell one|cell two|
                """,
            html_string="""
                <table>
                <tr>
                    <th>Headline 1</th>
                    <th>Headline 2</th>
                </tr>
                <tr>
                    <td>cell one</td>
                    <td>cell two</td>
                </tr>
                </table>
            """,
            #debug=True
            strip_lines=True,
        )
        self.cross_compare(
            rest_string="""
                +------------+------------+
                | Headline 1 | Headline 2 |
                +============+============+
                | cell one   | cell two   |
                +------------+------------+
                """,
            html_string="""
                <table>
                <tr><th>Headline 1</th>
                <th>Headline 2</th>
                </tr>
                <tr><td>cell one</td>
                <td>cell two</td>
                </tr>
                </table>
            """,
            #debug=True
        )


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cross_compare_creole
#!/usr/bin/env python
# coding: utf-8

"""
    cross compare creole unittest
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    Compare all similarities between:
        * creole2html
        * html2creole

    Note: This only works fine if there is no problematic whitespace handling.
        In this case, we must test in test_creole2html.py or test_html2creole.py

    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import unittest

from creole.shared import example_macros
from creole.shared.unknown_tags import use_html_macro
from creole.tests.utils.base_unittest import BaseCreoleTest


class CrossCompareCreoleTests(BaseCreoleTest):
    def test_typeface(self):
        self.cross_compare_creole(
            creole_string=r"""
                basics:
                **//bold italics//**
                //**bold italics**//
                //This is **also** good.//
    
                Creole 1.0 optional:
                This is ##monospace## text.
                This is ^^superscripted^^ text.
                This is ,,subscripted,, text.
                This is __underlined__ text.
    
                own additions:
                This is --small-- and this ~~strikeout~~ ;)
            """,
            html_string="""
                <p>basics:<br />
                <strong><i>bold italics</i></strong><br />
                <i><strong>bold italics</strong></i><br />
                <i>This is <strong>also</strong> good.</i></p>
    
                <p>Creole 1.0 optional:<br />
                This is <tt>monospace</tt> text.<br />
                This is <sup>superscripted</sup> text.<br />
                This is <sub>subscripted</sub> text.<br />
                This is <u>underlined</u> text.</p>
    
                <p>own additions:<br />
                This is <small>small</small> and this <del>strikeout</del> ;)</p>
            """
        )

    def test_cross_lines_html2creole(self):
        """ bold/italics cross lines
        see: http://code.google.com/p/python-creole/issues/detail?id=13
        TODO: The way back creole2html doesn't work, see below
        """
        self.assert_html2creole(r"""
            Bold and italics should //be
            able// to **cross
            lines.**
        """, """
            <p>Bold and italics should <i>be<br />
            able</i> to <strong>cross<br />
            lines.</strong></p>
        """)


    def test_small(self):
        """
        http://code.google.com/p/python-creole/issues/detail?id=12#c0
        """
        self.cross_compare_creole(
            creole_string=r"""
                no -- small
                no // italics
                no ** bold
                no ## monospace
                no ^^ superscripted
                no ,, subscripted
                no __ underline
            """,
            html_string="""
                <p>no -- small<br />
                no // italics<br />
                no ** bold<br />
                no ## monospace<br />
                no ^^ superscripted<br />
                no ,, subscripted<br />
                no __ underline</p>
            """,
            debug=False
        )

    def test_link(self):
        self.cross_compare_creole(
            creole_string=r"""
                this is [[/a internal]] link.
                1 [[internal links|link A]] test.
            """,
            html_string="""
                <p>this is <a href="/a internal">/a internal</a> link.<br />
                1 <a href="internal links">link A</a> test.</p>
            """
        )

    def test_bolditalic_links(self):
        self.cross_compare_creole(r"""
            //[[a internal]]//
            **[[Shortcut2|a page2]]**
            //**[[Shortcut3|a page3]]**//
        """, """
            <p><i><a href="a internal">a internal</a></i><br />
            <strong><a href="Shortcut2">a page2</a></strong><br />
            <i><strong><a href="Shortcut3">a page3</a></strong></i></p>
        """)

    def test_pre_contains_braces(self):
        """
        braces, &gt and %lt in a pre area.
        """
        self.cross_compare_creole(
            creole_string=r"""
                === Closing braces in nowiki:
                
                {{{
                if (x != NULL) {
                  for (i = 0; i < size; i++) {
                    if (x[i] > 0) {
                      x[i]--;
                  }}}
                }}}
                """,
            html_string="""
                <h3>Closing braces in nowiki:</h3>
                
                <pre>
                if (x != NULL) {
                  for (i = 0; i &lt; size; i++) {
                    if (x[i] &gt; 0) {
                      x[i]--;
                  }}}
                </pre>
            """)

    def test_pre2(self):
        self.cross_compare_creole(r"""
            111
            
            {{{
            //This// does **not** get [[formatted]]
            }}}
            222

            one
            
            {{{
            foo

            bar
            }}}
            two
        """, """
            <p>111</p>
            
            <pre>
            //This// does **not** get [[formatted]]
            </pre>
            <p>222</p>
            
            <p>one</p>
            
            <pre>
            foo

            bar
            </pre>
            <p>two</p>
        """)

    def test_pre(self):
        self.cross_compare_creole(r"""
            start
            
            {{{
            * no list
            <html escaped>
            }}}
            end
        """, """
            <p>start</p>
            
            <pre>
            * no list
            &lt;html escaped&gt;
            </pre>
            <p>end</p>
        """)

    def test_tt(self):
        self.cross_compare_creole(r"""
            this is ##**strong** Teletyper## ;)
        """, """
            <p>this is <tt><strong>strong</strong> Teletyper</tt> ;)</p>
        """)


    def test_no_inline_headline(self):
        self.cross_compare_creole(
            creole_string=r"""
                = Headline
                
                === **not** //parsed//
                
                No == headline == or?
            """,
            html_string="""
                <h1>Headline</h1>
                
                <h3>**not** //parsed//</h3>
                
                <p>No == headline == or?</p>
            """
        )

    def test_horizontal_rule(self):
        self.cross_compare_creole(r"""
            one

            ----

            two
        """, """
            <p>one</p>

            <hr />

            <p>two</p>
        """)

    def test_bullet_list(self):
        self.cross_compare_creole(r"""
            * Item 1
            ** Item 1.1
            ** a **bold** Item 1.2
            * Item 2
            ** Item 2.1
            *** [[a link Item 3.1]]
            *** Force\\linebreak 3.2
            *** item 3.3
            *** item 3.4

            up to five levels

            * 1
            ** 2
            *** 3
            **** 4
            ***** 5
        """, """
            <ul>
                <li>Item 1
                <ul>
                    <li>Item 1.1</li>
                    <li>a <strong>bold</strong> Item 1.2</li>
                </ul></li>
                <li>Item 2
                <ul>
                    <li>Item 2.1
                    <ul>
                        <li><a href="a link Item 3.1">a link Item 3.1</a></li>
                        <li>Force<br />
                        linebreak 3.2</li>
                        <li>item 3.3</li>
                        <li>item 3.4</li>
                    </ul></li>
                </ul></li>
            </ul>
            <p>up to five levels</p>

            <ul>
                <li>1
                <ul>
                    <li>2
                    <ul>
                        <li>3
                        <ul>
                            <li>4
                            <ul>
                                <li>5</li>
                            </ul></li>
                        </ul></li>
                    </ul></li>
                </ul></li>
            </ul>
        """)

    def test_number_list(self):
        self.cross_compare_creole(r"""
            # Item 1
            ## Item 1.1
            ## a **bold** Item 1.2
            # Item 2
            ## Item 2.1
            ### [[a link Item 3.1]]
            ### Force\\linebreak 3.2
            ### item 3.3
            ### item 3.4

            up to five levels

            # 1
            ## 2
            ### 3
            #### 4
            ##### 5
        """, """
            <ol>
                <li>Item 1
                <ol>
                    <li>Item 1.1</li>
                    <li>a <strong>bold</strong> Item 1.2</li>
                </ol></li>
                <li>Item 2
                <ol>
                    <li>Item 2.1
                    <ol>
                        <li><a href="a link Item 3.1">a link Item 3.1</a></li>
                        <li>Force<br />
                        linebreak 3.2</li>
                        <li>item 3.3</li>
                        <li>item 3.4</li>
                    </ol></li>
                </ol></li>
            </ol>
            <p>up to five levels</p>

            <ol>
                <li>1
                <ol>
                    <li>2
                    <ol>
                        <li>3
                        <ol>
                            <li>4
                            <ol>
                                <li>5</li>
                            </ol></li>
                        </ol></li>
                    </ol></li>
                </ol></li>
            </ol>
        """,
#        debug = True
        )

    def test_big_table(self):
        self.cross_compare_creole(r"""
            A Table...

            |= Headline  |= a other\\headline    |= the **big end**     |
            | a cell     | a **big** cell        | **//bold italics//** |
            | next\\line | No == headline == or? |                      |
            | link test: | a [[/url/|link]] in   | a cell.              |
            |            |                       | empty cells          |
            ...end
        """, """
            <p>A Table...</p>

            <table>
            <tr>
                <th>Headline</th>
                <th>a other<br />
                    headline</th>
                <th>the <strong>big end</strong></th>
            </tr>
            <tr>
                <td>a cell</td>
                <td>a <strong>big</strong> cell</td>
                <td><strong><i>bold italics</i></strong></td>
            </tr>
            <tr>
                <td>next<br />
                    line</td>
                <td>No == headline == or?</td>
                <td></td>
            </tr>
            <tr>
                <td>link test:</td>
                <td>a <a href="/url/">link</a> in</td>
                <td>a cell.</td>
            </tr>
            <tr>
                <td></td>
                <td></td>
                <td>empty cells</td>
            </tr>
            </table>
            <p>...end</p>
        """,
#            debug = True
        )

    def test_html_macro_unknown_nodes(self):
        """
        use the <<html>> macro to mask unknown tags.
        Note:
            All cross compare tests use html2creole.HTML_MACRO_UNKNOWN_NODES
        """
        self.cross_compare_creole("""
            111 <<html>><x><</html>>foo<<html>></x><</html>> 222
            333<<html>><x foo1='bar1'><</html>>foobar<<html>></x><</html>>444

            555<<html>><x /><</html>>666
        """, """
            <p>111 <x>foo</x> 222<br />
            333<x foo1='bar1'>foobar</x>444</p>

            <p>555<x />666</p>
        """,
            # use macro in creole2html emitter:
            macros=example_macros,
            # escape unknown tags with <<html>> in html2creole emitter:
            unknown_emit=use_html_macro,
        )

    def test_entities(self):
        self.cross_compare_creole("""
            less-than sign: <
            greater-than sign: >
        """, """
            <p>less-than sign: &lt;<br />
            greater-than sign: &gt;</p>
        """)

#    def test_macro_html1(self):
#        self.cross_compare_creole(r"""
#            <<a_not_existing_macro>>
#
#            <<code>>
#            some code
#            <</code>>
#
#            a macro:
#            <<code>>
#            <<code>>
#            the sourcecode
#            <</code>>
#        """, r"""
#            <p>[Error: Macro 'a_not_existing_macro' doesn't exist]</p>
#            <fieldset class="pygments_code">
#            <legend class="pygments_code"><small title="no lexer matching the text found">unknown type</small></legend>
#            <pre><code>some code</code></pre>
#            </fieldset>
#            <p>a macro:</p>
#            <fieldset class="pygments_code">
#            <legend class="pygments_code"><small title="no lexer matching the text found">unknown type</small></legend>
#            <pre><code>&lt;&lt;code&gt;&gt;
#            the sourcecode</code></pre>
#            </fieldset>
#        """)



#    def test_macro_pygments_code(self):
#        self.cross_compare_creole(r"""
#            a macro:
#            <<code ext=.css>>
#            /* Stylesheet */
#            form * {
#              vertical-align:middle;
#            }
#            <</code>>
#            the end
#        """, """
#            <p>a macro:</p>
#            <fieldset class="pygments_code">
#            <legend class="pygments_code">CSS</legend><table class="pygmentstable"><tr><td class="linenos"><pre>1
#            2
#            3
#            4</pre></td><td class="code"><div class="pygments"><pre><span class="c">/* Stylesheet */</span>
#            <span class="nt">form</span> <span class="o">*</span> <span class="p">{</span>
#              <span class="k">vertical-align</span><span class="o">:</span><span class="k">middle</span><span class="p">;</span>
#            <span class="p">}</span>
#            </pre></div>
#            </td></tr></table></fieldset>
#            <p>the end</p>
#        """)




if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cross_compare_rest
#!/usr/bin/env python
# coding: utf-8

"""
    cross compare reStructuredText unittest
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Compare all similarities between:
        * rest2html (used docutils)
        * html2rest

    :copyleft: 2011-2012 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import unittest

from creole.tests.utils.base_unittest import BaseCreoleTest


class CrossCompareReStTests(BaseCreoleTest):
    def test_entities(self):
        self.cross_compare_rest(
            rest_string="""
                less-than sign: <

                greater-than sign: >
            """,
            html_string="""
                <p>less-than sign: &lt;</p>
                <p>greater-than sign: &gt;</p>
            """,
#            debug=True
        )

    def test_bullet_lists_basic(self):
        self.cross_compare_rest(
            rest_string="""
                * item 1

                * item 2

                * item 3
            """,
            html_string="""
                <ul>
                <li>item 1</li>
                <li>item 2</li>
                <li>item 3</li>
                </ul>
            """,
#            debug=True
        )

    def test_numbered_lists(self):
        self.cross_compare_rest(
            rest_string="""
            #. item 1

            #. item 2

                #. item 2.1

                #. a `link in </url/>`_ list item 2.2

            #. item 3
            """,
            html_string="""
            <ol>
            <li><p>item 1</p>
            </li>
            <li><p>item 2</p>
            <ol>
            <li>item 2.1</li>
            <li>a <a href="/url/">link in</a> list item 2.2</li>
            </ol>
            </li>
            <li><p>item 3</p>
            </li>
            </ol>
            """,
#            debug=True
        )

    def test_bullet_lists_nested(self):
        self.cross_compare_rest(
            rest_string="""
                A nested bullet lists:

                * item 1

                    * A **bold subitem 1.1** here.

                        * subsubitem 1.1.1

                        * subsubitem 1.1.2 with inline |substitution text| image.

                    * subitem 1.2

                * item 2

                    * subitem 2.1

                    * *bold 2.2*

                .. |substitution text| image:: /url/to/image.png

                Text under list.
            """,
            html_string="""
                <p>A nested bullet lists:</p>
                <ul>
                <li><p>item 1</p>
                <ul>
                <li><p>A <strong>bold subitem 1.1</strong> here.</p>
                <ul>
                <li>subsubitem 1.1.1</li>
                <li>subsubitem 1.1.2 with inline <img alt="substitution text" src="/url/to/image.png" /> image.</li>
                </ul>
                </li>
                <li><p>subitem 1.2</p>
                </li>
                </ul>
                </li>
                <li><p>item 2</p>
                <ul>
                <li>subitem 2.1</li>
                <li><em>bold 2.2</em></li>
                </ul>
                </li>
                </ul>
                <p>Text under list.</p>
            """,
#            debug=True
        )

    def test_typeface_basic(self):
        """
        http://docutils.sourceforge.net/docs/user/rst/quickref.html#inline-markup
        """
        self.cross_compare_rest(
            rest_string="""
                *emphasis* **strong**
            """,
            html_string="""
                <p><em>emphasis</em> <strong>strong</strong></p>
            """
        )

    def test_substitution_image_with_alt(self):
        self.cross_compare_rest(
            rest_string="""
                A inline |substitution text| image.

                .. |substitution text| image:: /url/to/image.png

                ...and some text below.
            """,
            html_string="""
                <p>A inline <img alt="substitution text" src="/url/to/image.png" /> image.</p>
                <p>...and some text below.</p>
            """
        )

    def test_table(self):
        self.cross_compare(
            rest_string="""
                before table.

                +------------+
                | table item |
                +------------+

                After table.
            """,
            html_string="""
                <p>before table.</p>
                <table>
                <tr><td>table item</td>
                </tr>
                </table>
                <p>After table.</p>
            """
        )

    def test_link_in_table1(self):
        self.cross_compare(
            rest_string="""
                +---------------+
                | `table item`_ |
                +---------------+

                .. _table item: foo/bar
            """,
            html_string="""
                <table>
                <tr><td><a href="foo/bar">table item</a></td>
                </tr>
                </table>
            """
        )

    def test_link_in_table2(self):
        self.cross_compare(
            rest_string="""
                +-----------------------+
                | foo `table item`_ bar |
                +-----------------------+

                .. _table item: foo/bar
            """,
            html_string="""
                <table>
                <tr><td>foo <a href="foo/bar">table item</a> bar</td>
                </tr>
                </table>
            """
        )

    def test_link_in_table3(self):
        self.cross_compare(
            rest_string="""
                +-----------------------------+
                | * foo `table item 1`_ bar 1 |
                +-----------------------------+
                | * foo `table item 2`_ bar 2 |
                +-----------------------------+

                .. _table item 1: foo/bar/1/
                .. _table item 2: foo/bar/2/
            """,
            html_string="""
                <table>
                <tr><td><ul>
                <li>foo <a href="foo/bar/1/">table item 1</a> bar 1</li>
                </ul>
                </td>
                </tr>
                <tr><td><ul>
                <li>foo <a href="foo/bar/2/">table item 2</a> bar 2</li>
                </ul>
                </td>
                </tr>
                </table>
            """
        )

    def test_paragraph_bwlow_table_links(self):
        self.cross_compare(
            rest_string="""
                +-----------------+
                | `table item 1`_ |
                +-----------------+
                | `table item 2`_ |
                +-----------------+

                .. _table item 1: foo/bar/1/
                .. _table item 2: foo/bar/2/

                Text after table.
            """,
            html_string="""
                <table>
                <tr><td><a href="foo/bar/1/">table item 1</a></td>
                </tr>
                <tr><td><a href="foo/bar/2/">table item 2</a></td>
                </tr>
                </table>
                <p>Text after table.</p>
            """,
#            debug=True
        )

    def test_reuse_link_substitution1(self):
        self.cross_compare(
            rest_string="""
                +--------------------------------+
                | this is `foo bar`_ first time. |
                +--------------------------------+
                | and here `foo bar`_ again.     |
                +--------------------------------+

                .. _foo bar: foo/bar/

                Text after table.
            """,
            html_string="""
                <table>
                <tr><td>this is <a href="foo/bar/">foo bar</a> first time.</td>
                </tr>
                <tr><td>and here <a href="foo/bar/">foo bar</a> again.</td>
                </tr>
                </table>
                <p>Text after table.</p>
            """,
#            debug=True
        )

    def test_reuse_link_substitution2(self):
        self.cross_compare(
            rest_string="""
                +--------------------------------+
                | this is `foo bar`_ first time. |
                +--------------------------------+

                .. _foo bar: foo/bar/

                and here `foo bar`_ again, after table.
            """,
            html_string="""
                <table>
                <tr><td>this is <a href="foo/bar/">foo bar</a> first time.</td>
                </tr>
                </table>
                <p>and here <a href="foo/bar/">foo bar</a> again, after table.</p>
            """,
#            debug=True
        )

    def test_reuse_image_substitution(self):
        self.cross_compare(
            rest_string="""
                +----------------------+
                | first |image| here   |
                +----------------------+
                | second |image| there |
                +----------------------+

                .. |image| image:: /picture.png
            """,
            html_string="""
                <table>
                <tr><td>first <img alt="image" src="/picture.png" /> here</td>
                </tr>
                <tr><td>second <img alt="image" src="/picture.png" /> there</td>
                </tr>
                </table>
            """,
#            debug=True
        )

    def test_duplicate_image_substitution(self):
        self.cross_compare(
            rest_string="""
                +----------------------+
                | a |same| image here  |
                +----------------------+
                | a `same`_ link there |
                +----------------------+

                .. |same| image:: /image.png
                .. _same: /url/foo/

                again: the |same| image and `same`_ link!
            """,
            html_string="""
                <table>
                <tr><td>a <img alt="same" src="/image.png" /> image here</td>
                </tr>
                <tr><td>a <a href="/url/foo/">same</a> link there</td>
                </tr>
                </table>
                <p>again: the <img alt="same" src="/image.png" /> image and <a href="/url/foo/">same</a> link!</p>
            """,
#            debug=True
        )




#    def test_inline_literal(self):
#        """ TODO
#        http://docutils.sourceforge.net/docs/user/rst/quickref.html#inline-markup
#        """
#        self.cross_compare_rest(
#            rest_string="""
#                ``inline literal``
#            """,
#            html_string="""
#                <p><code>inline&nbsp;literal</code></p>
#            """
#        )

#    def test_escape_in_pre(self):
#        self.cross_compare_rest(
#            textile_string="""
#                <pre>
#                <html escaped>
#                </pre>
#            """,
#            html_string="""
#                <pre>
#                &#60;html escaped&#62;
#                </pre>
#            """)


if __name__ == '__main__':
    unittest.main(
#        defaultTest="CrossCompareReStTests.test_paragraph_bwlow_table_links",
    )

########NEW FILE########
__FILENAME__ = test_cross_compare_textile
#!/usr/bin/env python
# coding: utf-8

"""
    cross compare textile unittest
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    Compare all similarities between:
        * textile2html (used the python textile module)
        * html2textile

    Note: This only works fine if there is no problematic whitespace handling.
        In this case, we must test in test_creole2html.py or test_html2creole.py

    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import unittest

from creole.tests.utils.base_unittest import BaseCreoleTest


class CrossCompareTextileTests(BaseCreoleTest):
    def test_typeface_basic(self):
        self.cross_compare_textile(
            textile_string="""
                _emphasis_
                *strong*
                __italic__
                **bold**
                ??citation??
                -deleted text-
                +inserted text+
                ^superscript^
                ~subscript~
                %span%
                @code@
            """,
            html_string="""
                <p><em>emphasis</em><br />
                <strong>strong</strong><br />
                <i>italic</i><br />
                <b>bold</b><br />
                <cite>citation</cite><br />
                <del>deleted text</del><br />
                <ins>inserted text</ins><br />
                <sup>superscript</sup><br />
                <sub>subscript</sub><br />
                <span>span</span><br />
                <code>code</code></p>
            """
        )

    def test_escape_in_pre(self):
        self.cross_compare_textile(
            textile_string="""
                <pre>
                <html escaped>
                </pre>
            """,
            html_string="""
                <pre>
                &#60;html escaped&#62;
                </pre>
            """)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_html2creole
#!/usr/bin/env python
# coding: utf-8


"""
    html2creole tests
    ~~~~~~~~~~~~~~~~~
    
    special html to creole convert tests, witch can't tests in "cross compare"
    

    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import unittest

from creole.tests.utils.base_unittest import BaseCreoleTest

from creole import html2creole
from creole.shared.unknown_tags import raise_unknown_node, use_html_macro, \
                            escape_unknown_nodes, transparent_unknown_nodes


class TestHtml2Creole(unittest.TestCase):
    """
    Tests around html2creole API.
    """
    pass




class TestHtml2CreoleMarkup(BaseCreoleTest):

#    def assertCreole(self, raw_markup, raw_html, debug=False, **kwargs):
#        self.assert_html2creole(raw_markup, raw_html, debug=debug, **kwargs)

    #--------------------------------------------------------------------------

    def test_not_used(self):
        """
        Some other html tags -> convert.
        """
        self.assert_html2creole(r"""
            **Bold text**
            **Big text**
            //em tag//
            //italic//
        """, """
            <p><b>Bold text</b><br />
            <big>Big text</big><br />
            <em>em tag</em><br />
            <i>italic</i></p>
        """)

    #--------------------------------------------------------------------------

    def test_raise_unknown_node(self):
        """
        Test creole.html2creole.raise_unknown_node callable:
        Raise NotImplementedError on unknown tags.
        """
        self.assertRaises(NotImplementedError,
            html2creole,
            html_string="<unknwon>",
            unknown_emit=raise_unknown_node
        )

    def test_use_html_macro(self):
        """
        Test creole.html2creole.use_html_macro callable:
        Use the <<html>> macro to mask unknown tags.
        """
        self.assert_html2creole(r"""
            111 <<html>><unknown><</html>>foo<<html>></unknown><</html>> 222
            333<<html>><unknown foo1='bar1' foo2='bar2'><</html>>foobar<<html>></unknown><</html>>444

            555<<html>><unknown /><</html>>666
        """, """
            <p>111 <unknown>foo</unknown> 222<br />
            333<unknown foo1="bar1" foo2="bar2">foobar</unknown>444</p>

            <p>555<unknown />666</p>
        """,
            unknown_emit=use_html_macro
        )

    def test_escape_unknown_nodes(self):
        """
        Test creole.html2creole.escape_unknown_nodes callable:
        All unknown tags should be escaped.
        """
        self.assert_html2creole(r"""
            111 &lt;unknown&gt;foo&lt;/unknown&gt; 222
            333&lt;unknown foo1='bar1' foo2='bar2'&gt;foobar&lt;/unknown&gt;444

            555&lt;unknown /&gt;666
        """, """
            <p>111 <unknown>foo</unknown> 222<br />
            333<unknown foo1="bar1" foo2='bar2'>foobar</unknown>444</p>

            <p>555<unknown />666</p>
        """,
            unknown_emit=escape_unknown_nodes
        )

    def test_escape_unknown_nodes2(self):
        """
        HTMLParser has problems with <script> tags.
        See: http://bugs.python.org/issue670664
        """
        self.assert_html2creole(r"""
            &lt;script&gt;var js_sha_link='<p>***</p>';&lt;/script&gt;
        """, """
            <script>
            var js_sha_link='<p>***</p>';
            </script>
        """,
            unknown_emit=escape_unknown_nodes
        )

    def test_transparent_unknown_nodes(self):
        """
        Test creole.html2creole.transparent_unknown_nodes callable:
        All unknown tags should be "transparent" and show only
        their child nodes' content.
        """
        self.assert_html2creole(r"""
            //baz//, **quux**
        """, """
            <form class="foo" id="bar"><label><em>baz</em></label>, <strong>quux</strong></form>
        """, unknown_emit=transparent_unknown_nodes
        )

    def test_transparent_unknown_nodes2(self):
        """ 
        HTMLParser has problems with <script> tags.
        See: http://bugs.python.org/issue670664
        """
        self.assert_html2creole(r"""
            FOO var a='<em>STRONG</em>'; BAR
        """, """
            <p>FOO <script>var a='<em>STRONG</em>';</script> BAR</p>
        """, unknown_emit=transparent_unknown_nodes
        )

    def test_transparent_unknown_nodes_block_elements(self):
        """
        Test that block elements insert linefeeds into the stream.
        """
        self.assert_html2creole(r"""
            //baz//,

            **quux**

            spam, ham, and eggs
        """, """
            <div><em>baz</em>,</div> <fieldset><strong>quux</strong></fieldset>
            <span>spam, </span><label>ham, </label>and eggs
        """, unknown_emit=transparent_unknown_nodes
        )

    #--------------------------------------------------------------------------        

    def test_entities(self):
        """
        Test html entities.

        copyright sign is in Latin-1 Supplement:
            http://pylucid.org/_command/144/DecodeUnicode/display/1/
        Box Drawing:
            http://pylucid.org/_command/144/DecodeUnicode/display/66/
        """
        self.assert_html2creole("""
            * less-than sign: < < <
            * greater-than sign: > > >
            * copyright sign: © ©
            * box drawing: ╬ ╬
            * german umlauts: ä ö ü
        """, """
            <ul>
            <li>less-than sign: &lt; &#60; &#x3C;</li>
            <li>greater-than sign: &gt; &#62; &#x3E;</li>
            <li>copyright sign: &#169; &#xA9;</li>
            <li>box drawing: &#9580; &#x256C;</li>
            <li>german umlauts: &auml; &ouml; &uuml;</li>
            </ul>
        """)

    def test_html_entity_nbsp(self):
        """ Non breaking spaces is not in htmlentitydefs """
        self.assert_html2creole(r"""
            a non braking space: [ ] !
        """, """
            <p>a non braking space: [&nbsp;] !</p>
        """)

    def test_html_entity_in_pre(self):
        self.assert_html2creole(r"""
            {{{<code>{% lucidTag RSS url="http url" %}</code>}}}
        """, """
            <pre><code>&#x7B;% lucidTag RSS url="http url" %&#x7D;</code></pre>
        """)

    def test_unknown_entity(self):
        """
        Test a unknown html entity.
        FIXME: What sould happend?
        """
        self.assert_html2creole(r"""
            copy&paste
        """, """
            <p>copy&paste</p>
        """)
        self.assert_html2creole(r"""
            [[/url/|Search & Destroy]]
        """, """
            <a href="/url/">Search & Destroy</a>
        """)

    def test_tbody_table(self):
        self.assert_html2creole(r"""
            Ignore 'tbody' tag in tables:
            
            |= Headline 1 |= Headline 2 |
            | cell one    | cell two    |
            end
        """, """
            <p>Ignore 'tbody' tag in tables:</p>
            <table>
            <tbody>
            <tr>
                <th>Headline 1</th>
                <th>Headline 2</th>
            </tr>
            <tr>
                <td>cell one</td>
                <td>cell two</td>
            </tr>
            </tbody>
            </table>
            <p>end</p>
        """)

    def test_p_table(self):
        """ strip <p> tags in table cells """
        self.assert_html2creole(r"""
            | cell one | cell two\\new line |
        """, """
            <table>
            <tr>
                <td><p>cell one</p></td>
                <td><p>cell two</p><p>new line</p><p></p></td>
            </tr>
            </table>
        """)

    def test_image(self):
        """ test image tag with different alt/title attribute """
        self.assert_html2creole(r"""
            {{foobar1.jpg|foobar1.jpg}}
            {{/foobar2.jpg|foobar2.jpg}}
            {{/path1/path2/foobar3.jpg|foobar3.jpg}}
            {{/foobar4.jpg|It's foobar 4}}
            {{/foobar5.jpg|It's foobar 5}}
            {{/foobar6.jpg|a long picture title}}
        """, """
            <p><img src="foobar1.jpg" /><br />
            <img src="/foobar2.jpg" /><br />
            <img src="/path1/path2/foobar3.jpg" /><br />
            <img src="/foobar4.jpg" alt="It's foobar 4" /><br />
            <img src="/foobar5.jpg" title="It's foobar 5" /><br />
            <img src="/foobar6.jpg" alt="short name" title="a long picture title" /><br />
            <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA
            AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO
            9TXL0Y4OHwAAAABJRU5ErkJggg==" alt="data uri should be disallowed" /></p>
        """)

    def test_non_closed_br(self):
        self.assert_html2creole(r"""
            one
            two
        """, """
            <p>one<br>
            two</p>
        """)

    def test_explicit_closed_br(self):
        self.assert_html2creole(r"""
            one
            two
        """, """
            <p>one<br></br>
            two</p>
        """)

    def test_newline_before_list(self):
        """
        http://code.google.com/p/python-creole/issues/detail?id=16
        """
        self.assert_html2creole(r"""
            **foo**
            
            * one
        """, """
            <b>foo</b><ul><li>one</li></ul>
        """)

    def test_empty_tags_are_not_escaped(self):
        self.assert_html2creole(r"""
            //baz//, **quux**
        """, """
            <div class="foo" id="bar"><span><em>baz</em></span>, <strong>quux</strong></div>
        """)

    def test_nested_listsitems_with_paragraph(self):
        self.assert_html2creole("""
            * item 1
            ** subitem 1.1
            *** subsubitem 1.1.1
            *** subsubitem 1.1.2
            ** subitem 1.2
            * item 2
            ** subitem 2.1
            """, """
            <ul>
                <li><p>item 1</p>
                    <ul>
                        <li><p>subitem 1.1</p>
                            <ul>
                                <li>subsubitem 1.1.1</li>
                                <li>subsubitem 1.1.2</li>
                            </ul>
                        </li>
                            <li><p>subitem 1.2</p></li>
                    </ul>
                </li>
                <li><p>item 2</p>
                    <ul>
                        <li>subitem 2.1</li>
                    </ul>
                </li>
            </ul>
        """)

    def test_class_in_list(self):
        """https://code.google.com/p/python-creole/issues/detail?id=19#c4"""
        self.assert_html2creole(r"""
            # foo
        """, """
            <ol class=gbtc><li>foo</li></ol>
        """)#, debug=True)

    def test_ignore_links_without_href(self):
        """https://code.google.com/p/python-creole/issues/detail?id=19#c4"""
        self.assert_html2creole(r"""
            bar
        """, """
            <a class="foo">bar</a>
        """)#, debug=True)

    def test_newlines_after_headlines(self):
        self.assert_html2creole(r"""
            = Headline news

            [[http://google.com|The googlezor]] is a big bad mother.
        """, """
            <h1>Headline news</h1>

            <p><a href="http://google.com">The googlezor</a> is a big bad mother.</p>
        """)

    def test_links(self):
        self.assert_html2creole(r"""
            test link: '[[internal links|link A]]' 1 and
            test link: '[[http://domain.tld|link B]]' 2.
        """, """
            <p>test link: '<a href="internal links">link A</a>' 1 and<br />
            test link: '<a href="http://domain.tld">link B</a>' 2.</p>
        """)

    def test_horizontal_rule(self):
        self.assert_html2creole(r"""
            one
            
            ----
            
            two
        """, """
            <p>one</p>
            <hr />
            <p>two</p>
        """)

    def test_nested_empty_tags(self):
        self.assert_html2creole2("TEST", "<p>TEST</p>")
        self.assert_html2creole2("TEST", "<bar><p>TEST</p></bar>")
        self.assert_html2creole2("TEST", "<foo><bar><p>TEST</p></bar></foo>")


#    def test_nowiki1(self):
#        self.assert_html2creole(r"""
#            this:
#            {{{
#            //This// does **not** get [[formatted]]
#            }}}
#            and this: {{{** <i>this</i> ** }}} not, too.
#
#            === Closing braces in nowiki:
#            {{{
#            if (x != NULL) {
#              for (i = 0; i < size; i++) {
#                if (x[i] > 0) {
#                  x[i]--;
#              }}}
#            }}}
#        """, """
#            <p>this:</p>
#            <pre>
#            //This// does **not** get [[formatted]]
#            </pre>
#            <p>and this: <tt>** &lt;i&gt;this&lt;/i&gt; ** </tt> not, too.</p>
#
#            <h3>Closing braces in nowiki:</h3>
#            <pre>
#            if (x != NULL) {
#              for (i = 0; i &lt; size; i++) {
#                if (x[i] &gt; 0) {
#                  x[i]--;
#              }}}
#            </pre>
#        """)
#
#    def test_list1(self):
#        """
#        FIXME: Two newlines between a list and the next paragraph :(
#        """
#        self.assert_html2creole(r"""
#            ==== List a:
#            * a1 item
#            ** a1.1 Force\\linebreak
#            ** a1.2 item
#            *** a1.2.1 item
#            *** a1.2.2 item
#            * a2 item
#
#
#            list 'a' end
#
#            ==== List b:
#            # b1 item
#            ## b1.2 item
#            ### b1.2.1 item
#            ### b1.2.2 Force\\linebreak1\\linebreak2
#            ## b1.3 item
#            # b2 item
#
#
#            list 'b' end
#        """, """
#            <h4>List a:</h4>
#            <ul>
#            <li>a1 item</li>
#            <ul>
#                <li>a1.1 Force
#                linebreak</li>
#                <li>a1.2 item</li>
#                <ul>
#                    <li>a1.2.1 item</li>
#                    <li>a1.2.2 item</li>
#                </ul>
#            </ul>
#            <li>a2 item</li>
#            </ul>
#            <p>list 'a' end</p>
#
#            <h4>List b:</h4>
#            <ol>
#            <li>b1 item</li>
#            <ol>
#                <li>b1.2 item</li>
#                <ol>
#                    <li>b1.2.1 item</li>
#                    <li>b1.2.2 Force
#                    linebreak1
#                    linebreak2</li>
#                </ol>
#                <li>b1.3 item</li>
#            </ol>
#            <li>b2 item</li>
#            </ol>
#            <p>list 'b' end</p>
#        """,
##            debug=True
#        )
#
#    def test_list2(self):
#        """ Bold, Italics, Links, Pre in Lists """
#        self.assert_html2creole(r"""
#            * **bold** item
#            * //italic// item
#
#            # item about a [[domain.tld|page link]]
#            # {{{ //this// is **not** [[processed]] }}}
#        """, """
#            <ul>
#                <li><strong>bold</strong> item</li>
#                <li><i>italic</i> item</li>
#            </ul>
#            <ol>
#                <li>item about a <a href="domain.tld">page link</a></li>
#                <li><tt>//this// is **not** [[processed]]</tt></li>
#            </ol>
#        """,
##            debug=True
#        )


if __name__ == '__main__':
    unittest.main(
#        defaultTest="TestHtml2CreoleMarkup.test_nested_listsitems_with_paragraph"
    )


########NEW FILE########
__FILENAME__ = test_html2rest
#!/usr/bin/env python
# coding: utf-8

"""
    html2rest unittest
    ~~~~~~~~~~~~~~~~~~~~~
    
    Unittests for special cases which only works in the html2rest way.

    Note: This only works fine if there is no problematic whitespace handling.

    :copyleft: 2011-2012 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import unittest

from creole.html2rest.emitter import Html2restException
from creole.shared.unknown_tags import preformat_unknown_nodes
from creole.tests.utils.base_unittest import BaseCreoleTest


class ReStTests(BaseCreoleTest):
    def test_line_breaks(self):
        """
        Line breaks in HTML are lost.
        """
        self.assert_html2rest(
            rest_string="""
                first block, line 1 and line 2
                
                second block, line 1 and line 2
            """,
            html_string="""
                <p>first block, line 1
                and line 2</p>
                <p>second block, line 1
                and line 2</p>
            """,
#            debug=True
        )

    def test_substitution_image_without_alt_or_title(self):
        self.assert_html2rest(
            rest_string="""
                A inline |image.png| image.

                .. |image.png| image:: /url/to/image.png

                ...and some text below.
            """,
            html_string="""
                <p>A inline <img src="/url/to/image.png" /> image.</p>
                <p>...and some text below.</p>
            """
        )

    def test_substitution_image_with_title(self):
        self.assert_html2rest(
            rest_string="""
                A inline |foo bar| image.

                .. |foo bar| image:: /url/to/image.png

                ...and some text below.
            """,
            html_string="""
                <p>A inline <img title="foo bar" src="/url/to/image.png" /> image.</p>
                <p>...and some text below.</p>
            """
        )

    def test_pre_code1(self):
        self.assert_html2rest(
            rest_string="""
                ::
                
                    >>> from creole import creole2html
                    >>> creole2html("This is **creole //markup//**")
                    '<p>This is <strong>creole <i>markup</i></strong></p>
            """,
            html_string="""
                <pre>
                &gt;&gt;&gt; from creole import creole2html
                &gt;&gt;&gt; creole2html(&quot;This is **creole //markup//**&quot;)
                '&lt;p&gt;This is &lt;strong&gt;creole &lt;i&gt;markup&lt;/i&gt;&lt;/strong&gt;&lt;/p&gt;\n'
                </pre>
            """
        )

    def test_escape(self):
        self.assert_html2rest(
            rest_string="""
                * Use <tt> when {{{ ... }}} is inline and not <pre>, or not?
            """,
            html_string="""
                <ul>
                <li>Use &lt;tt&gt; when {{{ ... }}} is inline and not &lt;pre&gt;, or not?</li>
                </ul>
            """
        )

    def test_inline_literals(self):
        self.assert_html2rest(
            rest_string="""
                This text is an example of ``inline literals``.
            """,
            html_string="""
                <ul>
                <p>This text is an example of <tt>inline literals</tt>.</p>
                </ul>
            """
        )

    def test_list_without_p(self):
        self.assert_html2rest(
            rest_string="""
                A nested bullet lists:
                
                * item 1 without p-tag
                
                    * A **`subitem 1.1 </1.1/url/>`_ link** here.
                    
                        * subsubitem 1.1.1
                        
                        * subsubitem 1.1.2
                    
                    * subitem 1.2
                
                * item 2 without p-tag
                
                    * subitem 2.1
                    
                Text under list.
            """,
            html_string="""
                <p>A nested bullet lists:</p>
                <ul>
                    <li>item 1 without p-tag
                        <ul>
                            <li>A <strong><a href="/1.1/url/">subitem 1.1</a> link</strong> here.
                                <ul>
                                    <li>subsubitem 1.1.1</li>
                                    <li>subsubitem 1.1.2</li>
                                </ul>
                            </li>
                            <li>subitem 1.2</li>
                        </ul>
                    </li>
                    <li>item 2 without p-tag
                        <ul>
                            <li>subitem 2.1</li>
                        </ul>
                    </li>
                </ul>
                <p>Text under list.</p>
            """
        )

    def test_table_with_headings(self):
        self.assert_html2rest(
            rest_string="""
                +--------+--------+
                | head 1 | head 2 |
                +========+========+
                | item 1 | item 2 |
                +--------+--------+
            """,
            html_string="""
                <table>
                <tr><th>head 1</th><th>head 2</th>
                </tr>
                <tr><td>item 1</td><td>item 2</td>
                </tr>
                </table>
            """
        )

    def test_table_without_headings(self):
        self.assert_html2rest(
            rest_string="""
                +--------+--------+
                | item 1 | item 2 |
                +--------+--------+
                | item 3 | item 4 |
                +--------+--------+
            """,
            html_string="""
                <table>
                <tr><td>item 1</td><td>item 2</td>
                </tr>
                <tr><td>item 3</td><td>item 4</td>
                </tr>
                </table>
            """
        )
        
    def test_duplicate_substitution1(self):
        self.assertRaises(Html2restException, self.assert_html2rest,
            rest_string="""
                +-----------------------------+
                | this is `same`_ first time. |
                +-----------------------------+
                
                .. _same: /first/
                
                the `same </other/>`_ link?
            """,
            html_string="""
                <table>
                <tr><td>the <a href="/first/">same</a> first time.</td>
                </tr>
                </table>
                <p>the <a href="/other/">same</a> link?</p>
            """,
#            debug=True
        )
        
    def test_duplicate_link_substitution(self):
        self.assertRaises(Html2restException, self.assert_html2rest,
#        self.cross_compare(
            rest_string="""
                +-----------------------------+
                | this is `same`_ first time. |
                +-----------------------------+
                
                .. _same: /first/
                
                the `same </other/>`_ link?
            """,
            html_string="""
                <table>
                <tr><td>the <a href="/first/">same</a> first time.</td>
                </tr>
                </table>
                <p>the <a href="/other/">same</a> link?</p>
            """,
#            debug=True
        )

    def test_duplicate_image_substitution(self):
        self.assertRaises(Html2restException, self.assert_html2rest,
#        self.cross_compare(
            rest_string="""
                a |image|...
                and a other |image|!
                
                .. |image| image:: /image.png
                .. |image| image:: /other.png
            """,
            html_string="""
                <p>a <img src="/image.png" title="image" alt="image" />...<br />
                and a other <img src="/other.png" title="image" alt="image" />!</p>
            """,
#            debug=True
        )



#    def test_preformat_unknown_nodes(self):
#        """
#        Put unknown tags in a <pre> area.
#        """
#        self.assert_html2rest(
#            rest_string="""
#                111 <<pre>><x><</pre>>foo<<pre>></x><</pre>> 222
#                333<<pre>><x foo1="bar1"><</pre>>foobar<<pre>></x><</pre>>444
#                
#                555<<pre>><x /><</pre>>666
#            """,
#            html_string="""
#                <p>111 <x>foo</x> 222<br />
#                333<x foo1="bar1">foobar</x>444</p>
#    
#                <p>555<x />666</p>
#            """,
#            emitter_kwargs={"unknown_emit":preformat_unknown_nodes}
#        )
#
#    def test_transparent_unknown_nodes(self):
#        """
#        transparent_unknown_nodes is the default unknown_emit:
#        
#        Remove all unknown html tags and show only
#        their child nodes' content.
#        """
#        self.assert_html2rest(
#            rest_string="""
#                111 <<pre>><x><</pre>>foo<<pre>></x><</pre>> 222
#                333<<pre>><x foo1="bar1"><</pre>>foobar<<pre>></x><</pre>>444
#                
#                555<<pre>><x /><</pre>>666
#            """,
#            html_string="""
#                <p>111 <x>foo</x> 222<br />
#                333<x foo1="bar1">foobar</x>444</p>
#    
#                <p>555<x />666</p>
#            """,
#        )


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_html2textile
#!/usr/bin/env python
# coding: utf-8

"""
    html2textile unittest
    ~~~~~~~~~~~~~~~~~~~~~
    
    Unittests for special cases which only works in the html2textile way.

    Note: This only works fine if there is no problematic whitespace handling.

    :copyleft: 2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import unittest

from creole.shared.unknown_tags import preformat_unknown_nodes
from creole.tests.utils.base_unittest import BaseCreoleTest


class TextileTests(BaseCreoleTest):
    def test_entities(self):
        """
        can't be cross tested, because textile would convert < to &#60; and > to &#62;
        """
        self.assert_html2textile(
            textile_string="""
                less-than sign: <
                greater-than sign: >
            """,
            html_string="""
                <p>less-than sign: &lt;<br />
                greater-than sign: &gt;</p>
            """,
#            debug=True
        )

    def test_preformat_unknown_nodes(self):
        """
        Put unknown tags in a <pre> area.
        """
        self.assert_html2textile(
            textile_string="""
                111 <<pre>><x><</pre>>foo<<pre>></x><</pre>> 222
                333<<pre>><x foo1="bar1"><</pre>>foobar<<pre>></x><</pre>>444
                
                555<<pre>><x /><</pre>>666
            """,
            html_string="""
                <p>111 <x>foo</x> 222<br />
                333<x foo1="bar1">foobar</x>444</p>
    
                <p>555<x />666</p>
            """,
            emitter_kwargs={"unknown_emit":preformat_unknown_nodes}
        )

    def test_transparent_unknown_nodes(self):
        """
        transparent_unknown_nodes is the default unknown_emit:
        
        Remove all unknown html tags and show only
        their child nodes' content.
        """
        self.assert_html2textile(
            textile_string="""
                111 <<pre>><x><</pre>>foo<<pre>></x><</pre>> 222
                333<<pre>><x foo1="bar1"><</pre>>foobar<<pre>></x><</pre>>444
                
                555<<pre>><x /><</pre>>666
            """,
            html_string="""
                <p>111 <x>foo</x> 222<br />
                333<x foo1="bar1">foobar</x>444</p>
    
                <p>555<x />666</p>
            """,
        )


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_macros
# coding: utf-8


"""
    Creole unittest macros
    ~~~~~~~~~~~~~~~~~~~~~~
    
    Note: all mecro functions must return unicode!
    
    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""


from __future__ import division, absolute_import, print_function, unicode_literals

from creole.py3compat import repr2


def test_macro1(**kwargs):
    """
    >>> test_macro1(foo="bar")
    "[test macro1 - kwargs: foo='bar']"
    
    >>> test_macro1()
    '[test macro1 - kwargs: ]'
    
    >>> test_macro1(a=1,b=2)
    '[test macro1 - kwargs: a=1,b=2]'
    """
    kwargs = ','.join(['%s=%s' % (k, repr2(v)) for k, v in sorted(kwargs.items())])
    return "[test macro1 - kwargs: %s]" % kwargs


def test_macro2(char, text):
    """
    >>> test_macro2(char="|", text="a\\nb")
    'a|b'
    """
    return char.join(text.split())


if __name__ == "__main__":
    import doctest
    print(doctest.testmod())

########NEW FILE########
__FILENAME__ = test_rest2html
#!/usr/bin/env python
# coding: utf-8

"""
    rest2html unittest
    ~~~~~~~~~~~~~~~~~~
    
    Unittests for rest2html, see: creole/rest2html/clean_writer.py

    :copyleft: 2011-2012 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import tempfile
import unittest

from creole.tests.utils.base_unittest import BaseCreoleTest


class ReSt2HtmlTests(BaseCreoleTest):
    def test_clean_link_table(self):
        self.assert_rest2html("""
            :homepage:
              http://code.google.com/p/python-creole/
            
            :sourcecode:
              http://github.com/jedie/python-creole
        """, """
            <table>
            <tr><th>homepage:</th><td><a href="http://code.google.com/p/python-creole/">http://code.google.com/p/python-creole/</a></td>
            </tr>
            <tr><th>sourcecode:</th><td><a href="http://github.com/jedie/python-creole">http://github.com/jedie/python-creole</a></td>
            </tr>
            </table>
        """)

    def test_clean_table(self):
        self.assert_rest2html("""
            +------------+------------+
            | Headline 1 | Headline 2 |
            +============+============+
            | cell one   | cell two   |
            +------------+------------+
        """, """
            <table>
            <tr><th>Headline 1</th>
            <th>Headline 2</th>
            </tr>
            <tr><td>cell one</td>
            <td>cell two</td>
            </tr>
            </table>
        """)

    def test_clean_list(self):
        self.assert_rest2html("""
            * item 1
            
                * item 1.1
                
                * item 1.2
            
            * item 2
            
            numbered list:
            
            #. item A
        
            #. item B
        """, """
            <ul>
            <li><p>item 1</p>
            <ul>
            <li>item 1.1</li>
            <li>item 1.2</li>
            </ul>
            </li>
            <li><p>item 2</p>
            </li>
            </ul>
            <p>numbered list:</p>
            <ol>
            <li>item A</li>
            <li>item B</li>
            </ol>
        """)

    def test_clean_headline(self):
        self.assert_rest2html("""
            ======
            head 1
            ======
            
            ------
            head 2
            ------
        """, """
            <h1>head 1</h1>
            <h2>head 2</h2>
        """)

    def test_include_disabled_by_default(self):
        self.assert_rest2html("""
            Include should be disabled by default.
            
            .. include:: doesntexist.txt
        """, """
            <p>Include should be disabled by default.</p>
        """, report_level=3) # Set log level to "error" to suppress the waring output

    def test_include_enabled(self):
        test_content = "Content from include file."
        test_content = test_content.encode("utf-8")
        with tempfile.NamedTemporaryFile() as temp:
            temp.write(test_content)
            temp.flush()
            self.assert_rest2html("""
                Enable include and test it.
                
                .. include:: %s
            """ % temp.name, """
                <p>Enable include and test it.</p>
                <p>Content from include file.</p>
            """, file_insertion_enabled=True, input_encoding="utf-8")

    def test_raw_disabled_by_default(self):
        self.assert_rest2html("""
            Raw directive should be disabled by default.
            
            .. raw:: html

               <hr width=50 size=10>
        """, """
            <p>Raw directive should be disabled by default.</p>
        """, report_level=3) # Set log level to "error" to suppress the waring output

    def test_raw_enabled(self):
        self.assert_rest2html("""
            Now RAW is enabled.
            
            .. raw:: html

               <hr width=50 size=10>
        """, """
            <p>Now RAW is enabled.</p>
            <hr width=50 size=10>
        """, raw_enabled=True)

    def test_preserve_image_alignment(self):
        self.assert_rest2html("""
            Image alignment should be preserved.

            .. image:: foo.png
               :align: right
        """, """
            <p>Image alignment should be preserved.</p>
            <img alt="foo.png" src="foo.png" align="right" />
        """)

    def test_preserve_figure_alignment(self):
        self.assert_rest2html("""
            Image alignment should be preserved.

            .. figure:: bar.png
               :align: right
        """, """
            <p>Image alignment should be preserved.</p>
            <img alt="bar.png" src="bar.png" align="right" />
        """)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_TODOs
# coding: utf-8

"""
    Unittest which failed, cause bugfixes not implemented, yet.
"""

import unittest

from creole.tests.utils.base_unittest import BaseCreoleTest
from creole.html_tools.strip_html import strip_html


class StripHtml(unittest.TestCase):
    def test_not_closed_image_tag(self):
        output = strip_html('<p>a <img src="/image.jpg"> image.</p>')
        self.assertEqual(output, '<p>a <img src="/image.jpg"> image.</p>')

    def test_remove_linebreak(self):
        output = strip_html('<strong>foo</strong>\n<ul><li>one</li></ul>')
        self.assertEqual(output, '<strong>foo</strong><ul><li>one</li></ul>')



class CrossCompareCreoleTests(BaseCreoleTest):
    def test_cross_lines_creole2html(self):
        """ TODO: bold/italics cross lines in creole2html
        see: http://code.google.com/p/python-creole/issues/detail?id=13
        Info: The way html2creole works, see above
        """
        self.cross_compare_creole(
            creole_string=r"""
                Bold and italics should //be
                able// to **cross
                lines.**
            """,
            html_string="""
                <p>Bold and italics should <i>be<br />
                able</i> to <strong>cross<br />
                lines.</strong></p>
            """
        )

    def test_cross_paragraphs(self):
        """ TODO: bold/italics cross paragraphs in creole2html
        see: http://code.google.com/p/python-creole/issues/detail?id=13 
        """
        self.assert_creole2html("""
            But, should //not be...

            ...able// to cross paragraphs.
        """, """
            <p>But, should <em>not be...</em></p>
            <p>...able<em> to cross paragraphs.</em></p>
        """)


    def test_escape_inline(self):
        """ TODO: different pre/code syntax?
        """
        self.cross_compare_creole(r"""
            this is {{{**escaped** inline}}}, isn't it?
            
            {{{
            a **code**
            block
            }}}
        """, """
            <p>this is <tt>**escaped** inline</tt>, isn't it?</p>
            
            <pre>
            a **code**
            block
            </pre>
        """)


class TestHtml2CreoleMarkup(BaseCreoleTest):
    def test_format_in_a_text(self):
        """ TODO: http://code.google.com/p/python-creole/issues/detail?id=4 """
        self.assert_html2creole(r"""
            **[[/url/|title]]**
        """, """
            <a href="/url/"><strong>title</strong></a>
        """)


    def test_newline_before_headline(self):
        """ TODO: http://code.google.com/p/python-creole/issues/detail?id=16#c5 """
        self.assert_html2creole(r"""
            **foo**
            
            = one
        """, """
            <b>foo</b>
            <h1>one</h1>
        """)#, debug=True)

    def test_no_space_before_blocktag(self):
        """ TODO: Bug in html2creole.strip_html(): Don't add a space before/after block tags """
        self.assert_html2creole(r"""
            **foo**
            
            * one
        """, """
            <b>foo</b>
            <ul><li>one</li></ul>
        """#, debug=True
        )

    def test_escape_char(self):
        self.assert_html2creole(r"""
            ~#1
            http://domain.tld/~bar/
            ~http://domain.tld/
            [[Link]]
            ~[[Link]]
        """, """
            <p>#1<br />
            <a href="http://domain.tld/~bar/">http://domain.tld/~bar/</a><br />
            http://domain.tld/<br />
            <a href="Link">Link</a><br />
            [[Link]]</p>
        """)

    def test_images(self):
        self.assert_html2creole(r"""
            a {{/image.jpg|JPG pictures}} and
            a {{/image.jpeg|JPEG pictures}} and
            a {{/image.gif|GIF pictures}} and
            a {{/image.png|PNG pictures}} !

            picture [[www.domain.tld|{{foo.JPG|Foo}}]] as a link
        """, """
            <p>a <img src="/image.jpg" alt="JPG pictures"> and<br />
            a <img src="/image.jpeg" alt="JPEG pictures"> and<br />
            a <img src="/image.gif" alt="GIF pictures" /> and<br />
            a <img src="/image.png" alt="PNG pictures" /> !</p>

            <p>picture <a href="www.domain.tld"><img src="foo.JPG" alt="Foo"></a> as a link</p>
        """#, debug=True
        )

if __name__ == '__main__':
    unittest.main(
        verbosity=2
    )

########NEW FILE########
__FILENAME__ = test_utils
#!/usr/bin/env python
# coding: utf-8

"""
    unittest for some utils
    ~~~~~~~~~~~~~~~~~~~~~~~

    :copyleft: 2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import unittest

from creole.tests.utils.utils import MarkupTest
from creole.shared.markup_table import MarkupTable


class UtilsTests(MarkupTest):
    def assertEqual2(self, first, second, msg=""):
        self.assertNotEqual(first, second, msg)

#        first = self._prepare_text(first)
        second = self._prepare_text(second)

        self.assertEqual(first, second, msg)

    def test_markup_table_creole(self):
        t = MarkupTable(head_prefix="* ")
        t.add_tr()
        t.add_th("head1")
        t.add_th("head2")
        t.add_tr()
        t.add_td("1.1.")
        t.add_td("1.2.")
        t.add_tr()
        t.add_td("2.1.")
        t.add_td("2.2.")
        table = t.get_table_markup()

        self.assertEqual2(
            table,
            """
            |* head1 |* head2 |
            | 1.1.   | 1.2.   |
            | 2.1.   | 2.2.   |
            """
        )

    def test_markup_table_textile(self):
        t = MarkupTable(head_prefix="_. ", auto_width=False)
        t.add_tr()
        t.add_th("head1")
        t.add_th("head2")
        t.add_tr()
        t.add_td("1.1.")
        t.add_td("1.2.")
        t.add_tr()
        t.add_td("2.1.")
        t.add_td("2.2.")
        table = t.get_table_markup()

        self.assertEqual2(
            table,
            """
            |_. head1|_. head2|
            |1.1.|1.2.|
            |2.1.|2.2.|
            """
        )

    def test_markup_table_rest(self):
        t = MarkupTable(head_prefix="")
        t.add_tr()
        t.add_th("head1")
        t.add_th("head2")
        t.add_tr()
        t.add_td("1.1.")
        t.add_td("1.2.")
        t.add_tr()
        t.add_td("2.1.")
        t.add_td("2.2.")
        table = t.get_rest_table()

        self.assertEqual2(
            table,
            """
            +-------+-------+
            | head1 | head2 |
            +=======+=======+
            | 1.1.  | 1.2.  |
            +-------+-------+
            | 2.1.  | 2.2.  |
            +-------+-------+
            """
        )


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = base_unittest
# coding: utf-8


"""
    unitest base class
    ~~~~~~~~~~~~~~~~~~

    Basic unittest class for all python-creole tests.

    :copyleft: 2008-2009 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import re
import warnings

from creole.tests.utils.utils import MarkupTest
from creole.py3compat import TEXT_TYPE


try:
    import textile
except ImportError:
    test_textile = False
    warnings.warn(
        "Markup error: The Python textile library isn't installed."
        " Download: http://pypi.python.org/pypi/textile"
    )
else:
    test_textile = True


from creole.exceptions import DocutilsImportError
from creole import creole2html, html2creole, html2textile, html2rest

try:
    from creole.rest2html.clean_writer import rest2html
except DocutilsImportError as err:
    REST_INSTALLED = False
    warnings.warn("Can't run all ReSt unittests: %s" % err)
else:
    REST_INSTALLED = True

tabs2spaces_re = re.compile(r"^(\t*)(.*?)$", re.M)



def tabs2spaces(html):
    """ form reformating textile html code
    >>> tabs2spaces("\\t<p>one<br />\\n\\t\\ttwo<br />\\n\\t\\t\\ttree</p>")
    '<p>one<br />\\n  two<br />\\n    tree</p>'
    """
    def reformat_tabs(match):
        tabs = match.group(1)
        text = match.group(2)

        indent = len(tabs) - 1
        if indent < 0:
            indent = 0

#        print(len(tabs), indent, repr(tabs), text)
        return "  " * indent + text
    return tabs2spaces_re.sub(reformat_tabs, html)


def strip_html_lines(html, strip_lines=False):
    """
    >>> strip_html_lines("\t<p>foo   \\n\\n\t\t  bar</p>", strip_lines=True)
    '<p>foo\\nbar</p>'
    """
    html = "\n".join(
        [line.strip(" \t") for line in html.splitlines() if line]
    )
    return html



class BaseCreoleTest(MarkupTest):
    """
    Basic unittest class for all python-creole unittest classes.
    """
    def _debug_text(self, msg, raw_text):
        text = raw_text.replace(" ", ".")
        text = text.replace("\n", "\\n\n")
        text = text.replace("\t", "\\t")

        print
        print("_" * 79)
        print(" Debug Text: %s" % msg)
        print(text)
        print("-" * 79)

    def assertIn(self, member, container, *args, **kwargs):
        """
        Assert member in container.
        assertIn is new in Python 2.7
        """
        try:
            f = super(BaseCreoleTest, self).assertIn
        except AttributeError:
            self.assertTrue(member in container, *args, **kwargs)
        else:
            f(member, container, *args, **kwargs)

    def assert_creole2html(self, raw_creole, raw_html, \
            strip_lines=False, debug=False,
            parser_kwargs={}, emitter_kwargs={},
            block_rules=None, blog_line_breaks=True, macros=None, verbose=None, stderr=None,
        ):
        """
        compare the generated html code from the markup string >creole_string<
        with the >html_string< reference.
        """
        self.assertNotEqual(raw_creole, raw_html)
        self.assertEqual(parser_kwargs, {}, "parser_kwargs is deprecated!")
        self.assertEqual(emitter_kwargs, {}, "parser_kwargs is deprecated!")

        # prepare whitespace on test strings
        markup_string = self._prepare_text(raw_creole)
        assert isinstance(markup_string, TEXT_TYPE)

        html_string = self._prepare_text(raw_html)
        assert isinstance(html_string, TEXT_TYPE)
        if strip_lines:
            html_string = strip_html_lines(html_string, strip_lines)
        if debug:
            self._debug_text("assert_creole2html() html_string", html_string)

        # convert creole markup into html code
        out_string = creole2html(
            markup_string, debug,
            block_rules=block_rules, blog_line_breaks=blog_line_breaks,
            macros=macros, verbose=verbose, stderr=stderr,
        )
        if debug:
            self._debug_text("assert_creole2html() creole2html", out_string)

        if strip_lines:
            out_string = strip_html_lines(out_string, strip_lines)
        else:
            out_string = out_string.replace("\t", "    ")

        # compare
        self.assertEqual(out_string, html_string, msg="creole2html")

    def assert_html2creole2(self, creole, html, debug=False, unknown_emit=None):
        # convert html code into creole markup
        out_string = html2creole(html, debug, unknown_emit=unknown_emit)
        if debug:
            self._debug_text("assert_html2creole() html2creole", out_string)

        # compare
        self.assertEqual(out_string, creole, msg="html2creole")

    def assert_html2creole(self, raw_creole, raw_html, \
                strip_lines=False, debug=False,
                # OLD API:
                parser_kwargs={}, emitter_kwargs={},
                # html2creole:
                unknown_emit=None
        ):
        """
        Compare the genereted markup from the given >raw_html< html code, with
        the given >creole_string< reference string.
        """
        self.assertEqual(parser_kwargs, {}, "parser_kwargs is deprecated!")
        self.assertEqual(emitter_kwargs, {}, "parser_kwargs is deprecated!")
#        assert isinstance(raw_html, TEXT_TYPE)
#        creole_string = unicode(creole_string, encoding="utf8")
#        raw_html = unicode(raw_html, "utf8")

        self.assertNotEqual(raw_creole, raw_html)

        # prepare whitespace on test strings
        creole = self._prepare_text(raw_creole)
        assert isinstance(creole, TEXT_TYPE)
        if debug:
            self._debug_text("assert_creole2html() markup", creole)

        html = self._prepare_text(raw_html)
        assert isinstance(html, TEXT_TYPE)

        self.assert_html2creole2(creole, html, debug, unknown_emit)


    def cross_compare_creole(self, creole_string, html_string,
                        strip_lines=False, debug=False,
                        # creole2html old API:
                        creole_parser_kwargs={}, html_emitter_kwargs={},
                        # html2creole old API:
                        html_parser_kwargs={}, creole_emitter_kwargs={},

                        # creole2html new API:
                        block_rules=None, blog_line_breaks=True, macros=None, stderr=None,
                        # html2creole:
                        unknown_emit=None
        ):
        """
        Cross compare with:
            * creole2html
            * html2creole
        """
        self.assertEqual(creole_parser_kwargs, {}, "creole_parser_kwargs is deprecated!")
        self.assertEqual(html_emitter_kwargs, {}, "html_emitter_kwargs is deprecated!")
        self.assertEqual(html_parser_kwargs, {}, "html_parser_kwargs is deprecated!")
        self.assertEqual(creole_emitter_kwargs, {}, "creole_emitter_kwargs is deprecated!")

        assert isinstance(creole_string, TEXT_TYPE)
        assert isinstance(html_string, TEXT_TYPE)
        self.assertNotEqual(creole_string, html_string)

        self.assert_creole2html(
            creole_string, html_string, strip_lines, debug,
            block_rules=block_rules, blog_line_breaks=blog_line_breaks,
            macros=macros, stderr=stderr,
        )

        self.assert_html2creole(
            creole_string, html_string, strip_lines, debug,
            unknown_emit=unknown_emit,
        )

    def assert_html2textile(self, textile_string, html_string, \
                        strip_lines=False, debug=False, parser_kwargs={}, emitter_kwargs={}):
        """
        Check html2textile
        """
        self.assertNotEqual(textile_string, html_string)

        textile_string = self._prepare_text(textile_string)
        html_string = self._prepare_text(html_string)

        if strip_lines:
            html_string = strip_html_lines(html_string, strip_lines)

        # compare html -> textile
        textile_string2 = html2textile(html_string, debug, parser_kwargs, emitter_kwargs)
        if debug:
            print("-" * 79)
            print(textile_string2)
            print("-" * 79)

        self.assertEqual(textile_string2, textile_string, msg="html2textile")

        return textile_string, html_string

    def cross_compare_textile(self, textile_string, html_string, \
                        strip_lines=False, debug=False, parser_kwargs={}, emitter_kwargs={}):
        """
            Checks:
                * html2textile
                * textile2html
        """
#        assert isinstance(textile_string, TEXT_TYPE)
#        assert isinstance(html_string, TEXT_TYPE)
        self.assertNotEqual(textile_string, html_string)

        # compare html -> textile
        textile_string, html_string = self.assert_html2textile(
            textile_string, html_string,
            strip_lines, debug, parser_kwargs, emitter_kwargs
        )

        # compare textile -> html
        if not test_textile:
            warnings.warn("Skip textile test. Please install python textile module.")
            return

        html = textile.textile(textile_string)
        html = html.replace("<br />", "<br />\n")
        html = tabs2spaces(html)
        if strip_lines:
            html = strip_html_lines(html, strip_lines)

        self.assertEqual(html_string, html, msg="textile2html")

    def assert_html2rest(self, rest_string, html_string, \
                        strip_lines=False, debug=False, parser_kwargs={}, emitter_kwargs={}):
        """
        Check html to reStructuredText converter
        """
        self.assertNotEqual(rest_string, html_string)

        rest_string = self._prepare_text(rest_string)
        html_string = self._prepare_text(html_string)

        if strip_lines:
            html_string = strip_html_lines(html_string, strip_lines)

        # compare html -> reStructuredText
        rest_string2 = html2rest(html_string, debug, parser_kwargs, emitter_kwargs)
        if debug:
            print("-" * 79)
            print(rest_string2)
            print("-" * 79)

        self.assertEqual(rest_string2, rest_string, msg="html2rest")

        return rest_string, html_string

    def assert_rest2html(self, rest_string, html_string, \
            strip_lines=False, debug=False, prepare_strings=True, **kwargs):

        # compare rest -> html
        if not REST_INSTALLED:
            warnings.warn("Skip ReSt test. Please install Docutils.")
            return

        if prepare_strings:
            rest_string = self._prepare_text(rest_string)
            html_string = self._prepare_text(html_string)

        html = rest2html(rest_string, **kwargs)

        if debug:
            print(rest_string)
            print(html_string)
            print(html)

        html = html.strip()
#        html = html.replace("<br />", "<br />\n")
#        html = tabs2spaces(html)
        if strip_lines:
            html = strip_html_lines(html, strip_lines)

        self.assertEqual(html, html_string, msg="rest2html")

    def cross_compare_rest(self, rest_string, html_string, \
                        strip_lines=False, debug=False, parser_kwargs={}, emitter_kwargs={}):
#        assert isinstance(textile_string, TEXT_TYPE)
#        assert isinstance(html_string, TEXT_TYPE)
        self.assertNotEqual(rest_string, html_string)

        rest_string, html_string = self.assert_html2rest(
            rest_string, html_string,
            strip_lines, debug, parser_kwargs, emitter_kwargs
        )

        # compare rest -> html
        self.assert_rest2html(
            rest_string, html_string,
            strip_lines=strip_lines, debug=debug,
            prepare_strings=False,
        )

    def cross_compare(self,
            html_string,
            creole_string=None,
            textile_string=None,
            rest_string=None,
            strip_lines=False, debug=False, parser_kwargs={}, emitter_kwargs={}):
        """
        Cross compare with:
            * creole2html
            * html2creole
            * html2textile
            * html2ReSt
        """
        if creole_string:
            self.cross_compare_creole(
                creole_string, html_string, strip_lines, debug, parser_kwargs, emitter_kwargs
            )

        if textile_string:
            self.cross_compare_textile(
                textile_string, html_string, strip_lines, debug, parser_kwargs, emitter_kwargs
            )

        if rest_string:
            self.cross_compare_rest(
                rest_string, html_string, strip_lines, debug, parser_kwargs, emitter_kwargs
            )

if __name__ == '__main__':
    import doctest
    print(doctest.testmod())

########NEW FILE########
__FILENAME__ = utils
# coding: utf-8


"""
    unitest generic utils
    ~~~~~~~~~~~~~~~~~~~~~

    Generic utils useable for a markup test.

    :copyleft: 2008-2011 by python-creole team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import difflib
import unittest


## error output format:
# =1 -> via repr()
# =2 -> raw
VERBOSE = 1
#VERBOSE = 2


def make_diff(block1, block2):
    d = difflib.Differ()

    block1 = block1.replace("\\n", "\\n\n").split("\n")
    block2 = block2.replace("\\n", "\\n\n").split("\n")

    diff = d.compare(block1, block2)

    result = ["%2s %s\n" % (line, i) for line, i in enumerate(diff)]
    return "".join(result)


class MarkupTest(unittest.TestCase):
    """
    Special error class: Try to display markup errors in a better way.
    """
    def _format_output(self, txt):
        txt = txt.split("\\n")
        if VERBOSE == 1:
            txt = "".join(['%s\\n\n' % i for i in txt])
        elif VERBOSE == 2:
            txt = "".join(['%s\n' % i for i in txt])
        return txt

    def assertEqual(self, first, second, msg=""):
        if not first == second:
            if VERBOSE >= 2:
                print("first: %r" % first)
                print("second: %r" % second)

            #~ first = first.rstrip("\\n")
            #~ second = second.rstrip("\\n")
            try:
                diff = make_diff(first, second)
            except AttributeError:
                raise self.failureException("%s is not %s" % (repr(first), repr(second)))

            if VERBOSE >= 2:
                print("diff: %r" % diff)

            first = self._format_output(first)
            second = self._format_output(second)

            msg += (
                "\n---[Output:]---\n%s\n"
                "---[not equal to:]---\n%s"
                "\n---[diff:]---\n%s"
            ) % (first, second, diff)
            raise self.failureException(msg)

    def _prepare_text(self, txt):
        """
        prepare the multiline, indentation text.
        """
        #txt = unicode(txt)
        txt = txt.splitlines()
        assert txt[0] == "", "First assertion line must be empty! Is: %s" % repr(txt[0])
        txt = txt[1:] # Skip the first line

        # get the indentation level from the first line
        count = False
        for count, char in enumerate(txt[0]):
            if char != " ":
                break

        assert count != False, "second line is empty!"

        # remove indentation from all lines
        txt = [i[count:].rstrip(" ") for i in txt]

        #~ txt = re.sub("\n {2,}", "\n", txt)
        txt = "\n".join(txt)

        # strip *one* newline at the begining...
        if txt.startswith("\n"): txt = txt[1:]
        # and strip *one* newline at the end of the text
        if txt.endswith("\n"): txt = txt[:-1]
        #~ print(repr(txt))
        #~ print("-"*79)

        return txt

    def testSelf(self):
        """
        Test for self._prepare_text()
        """
        out1 = self._prepare_text("""
            one line
            line two""")
        self.assertEqual(out1, "one line\nline two")

        out2 = self._prepare_text("""
            one line
            line two
        """)
        self.assertEqual(out2, "one line\nline two")

        out3 = self._prepare_text("""
            one line

            line two
        """)
        self.assertEqual(out3, "one line\n\nline two")

        out4 = self._prepare_text("""
            one line
                line two

        """)
        self.assertEqual(out4, "one line\n    line two\n")

        # removing whitespace and the end
        self.assertEqual(self._prepare_text("\n  111  \n  222"), "111\n222")

        out5 = self._prepare_text("""
            one line
                line two
            dritte Zeile
        """)
        self.assertEqual(out5, "one line\n    line two\ndritte Zeile")

        self.assertRaises(
            AssertionError, self.assertEqual, "foo", "bar"
        )



if __name__ == '__main__':
    import doctest
    print("DocTest:", doctest.testmod())

    unittest.main()

########NEW FILE########
__FILENAME__ = demo
#!/usr/bin/env python
# coding: utf-8


"""
    simple demo
    ~~~~~~~~~~~
"""

from __future__ import division, absolute_import, print_function, unicode_literals

from creole import creole2html, html2creole, html2rest, html2textile


source_creole = """\
== simple demo

You can convert from:

* **creole2html**, **html2creole**, **html2rest**, //html2textile//

=== a table:

|=headline 1 |= headline 2 |
| 1.1. cell  | 1.2. cell   |
| 2.1. cell  | 2.2. cell   |

----

More info on our [[http://code.google.com/p/python-creole/|Homepage]]."""


if __name__ == "__main__":
    print("_" * 79 + "\n*** Convert creole into html: ***\n\n")
    html = creole2html(source_creole)
    print(html)


    print("\n\n" + "_" * 79 + "\n*** Convert html back into creole: ***\n\n")
    creole = html2creole(html)
    print(creole)


    print("\n\n" + "_" * 79 + "\n*** Convert html into ReStructuredText: ***\n\n")
    rest = html2rest(html)
    print(rest)


    print("\n\n" + "_" * 79 + "\n*** Convert html into textile: ***\n\n")
    textile = html2textile(html)
    print(textile)

########NEW FILE########
