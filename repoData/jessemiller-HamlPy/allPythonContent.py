__FILENAME__ = elements
import re
import sys
from types import NoneType

class Element(object):
    """contains the pieces of an element and can populate itself from haml element text"""

    self_closing_tags = ('meta', 'img', 'link', 'br', 'hr', 'input', 'source', 'track')

    ELEMENT = '%'
    ID = '#'
    CLASS = '.'

    HAML_REGEX = re.compile(r"""
    (?P<tag>%\w+(\:\w+)?)?
    (?P<id>\#[\w-]*)?
    (?P<class>\.[\w\.-]*)*
    (?P<attributes>\{.*\})?
    (?P<nuke_outer_whitespace>\>)?
    (?P<nuke_inner_whitespace>\<)?
    (?P<selfclose>/)?
    (?P<django>=)?
    (?P<inline>[^\w\.#\{].*)?
    """, re.X | re.MULTILINE | re.DOTALL | re.UNICODE)

    _ATTRIBUTE_KEY_REGEX = r'(?P<key>[a-zA-Z_][a-zA-Z0-9_-]*)'
    #Single and double quote regexes from: http://stackoverflow.com/a/5453821/281469
    _SINGLE_QUOTE_STRING_LITERAL_REGEX = r"'([^'\\]*(?:\\.[^'\\]*)*)'"
    _DOUBLE_QUOTE_STRING_LITERAL_REGEX = r'"([^"\\]*(?:\\.[^"\\]*)*)"'
    _ATTRIBUTE_VALUE_REGEX = r'(?P<val>\d+|None(?!\w)|%s|%s)' % (_SINGLE_QUOTE_STRING_LITERAL_REGEX, _DOUBLE_QUOTE_STRING_LITERAL_REGEX)

    RUBY_HAML_REGEX = re.compile(r'(:|\")%s(\"|) =>' % (_ATTRIBUTE_KEY_REGEX))
    ATTRIBUTE_REGEX = re.compile(r'(?P<pre>\{\s*|,\s*)%s\s*:\s*%s' % (_ATTRIBUTE_KEY_REGEX, _ATTRIBUTE_VALUE_REGEX), re.UNICODE)
    DJANGO_VARIABLE_REGEX = re.compile(r'^\s*=\s(?P<variable>[a-zA-Z_][a-zA-Z0-9._-]*)\s*$')


    def __init__(self, haml, attr_wrapper="'"):
        self.haml = haml
        self.attr_wrapper = attr_wrapper
        self.tag = None
        self.id = None
        self.classes = None
        self.attributes = ''
        self.self_close = False
        self.django_variable = False
        self.nuke_inner_whitespace = False
        self.nuke_outer_whitespace = False
        self.inline_content = ''
        self._parse_haml()

    def attr_wrap(self, value):
        return '%s%s%s' % (self.attr_wrapper, value, self.attr_wrapper)

    def _parse_haml(self):
        split_tags = self.HAML_REGEX.search(self.haml).groupdict('')

        self.attributes_dict = self._parse_attribute_dictionary(split_tags.get('attributes'))
        self.tag = split_tags.get('tag').strip(self.ELEMENT) or 'div'
        self.id = self._parse_id(split_tags.get('id'))
        self.classes = ('%s %s' % (split_tags.get('class').lstrip(self.CLASS).replace('.', ' '), self._parse_class_from_attributes_dict())).strip()
        self.self_close = split_tags.get('selfclose') or self.tag in self.self_closing_tags
        self.nuke_inner_whitespace = split_tags.get('nuke_inner_whitespace') != ''
        self.nuke_outer_whitespace = split_tags.get('nuke_outer_whitespace') != ''
        self.django_variable = split_tags.get('django') != ''
        self.inline_content = split_tags.get('inline').strip()

    def _parse_class_from_attributes_dict(self):
        clazz = self.attributes_dict.get('class', '')
        if not isinstance(clazz, str):
            clazz = ''
            for one_class in self.attributes_dict.get('class'):
                clazz += ' ' + one_class
        return clazz.strip()

    def _parse_id(self, id_haml):
        id_text = id_haml.strip(self.ID)
        if 'id' in self.attributes_dict:
            id_text += self._parse_id_dict(self.attributes_dict['id'])
        id_text = id_text.lstrip('_')
        return id_text

    def _parse_id_dict(self, id_dict):
        text = ''
        id_dict = self.attributes_dict.get('id')
        if isinstance(id_dict, str):
            text = '_' + id_dict
        else:
            text = ''
            for one_id in id_dict:
                text += '_' + one_id
        return text

    def _escape_attribute_quotes(self, v):
        '''
        Escapes quotes with a backslash, except those inside a Django tag
        '''
        escaped = []
        inside_tag = False
        for i, _ in enumerate(v):
            if v[i:i + 2] == '{%':
                inside_tag = True
            elif v[i:i + 2] == '%}':
                inside_tag = False

            if v[i] == self.attr_wrapper and not inside_tag:
                escaped.append('\\')

            escaped.append(v[i])

        return ''.join(escaped)

    def _parse_attribute_dictionary(self, attribute_dict_string):
        attributes_dict = {}
        if (attribute_dict_string):
            attribute_dict_string = attribute_dict_string.replace('\n', ' ')
            try:
                # converting all allowed attributes to python dictionary style

                # Replace Ruby-style HAML with Python style
                attribute_dict_string = re.sub(self.RUBY_HAML_REGEX, '"\g<key>":', attribute_dict_string)
                # Put double quotes around key
                attribute_dict_string = re.sub(self.ATTRIBUTE_REGEX, '\g<pre>"\g<key>":\g<val>', attribute_dict_string)
                # Parse string as dictionary
                attributes_dict = eval(attribute_dict_string)
                for k, v in attributes_dict.items():
                    if k != 'id' and k != 'class':
                        if isinstance(v, NoneType):
                            self.attributes += "%s " % (k,)
                        elif isinstance(v, int) or isinstance(v, float):
                            self.attributes += "%s=%s " % (k, self.attr_wrap(v))
                        else:
                            # DEPRECATED: Replace variable in attributes (e.g. "= somevar") with Django version ("{{somevar}}")
                            v = re.sub(self.DJANGO_VARIABLE_REGEX, '{{\g<variable>}}', attributes_dict[k])
                            if v != attributes_dict[k]:
                                sys.stderr.write("\n---------------------\nDEPRECATION WARNING: %s" % self.haml.lstrip() + \
                                                 "\nThe Django attribute variable feature is deprecated and may be removed in future versions." +
                                                 "\nPlease use inline variables ={...} instead.\n-------------------\n")

                            attributes_dict[k] = v
                            v = v.decode('utf-8')
                            self.attributes += "%s=%s " % (k, self.attr_wrap(self._escape_attribute_quotes(v)))
                self.attributes = self.attributes.strip()
            except Exception, e:
                raise Exception('failed to decode: %s' % attribute_dict_string)
                #raise Exception('failed to decode: %s. Details: %s'%(attribute_dict_string, e))

        return attributes_dict





########NEW FILE########
__FILENAME__ = ext
# coding=utf-8
try:
    import jinja2.ext
    _jinja2_available = True
except ImportError, e:
    _jinja2_available = False

import hamlpy
import os

HAML_FILE_NAME_EXTENSIONS = ['haml', 'hamlpy']


def clean_extension(file_ext):
    if not isinstance(file_ext, basestring):
        raise Exception('Wrong file extension format: %r' % file_ext)
    if len(file_ext) > 1 and file_ext.startswith('.'):
        file_ext = file_ext[1:]
    return file_ext.lower().strip()


def get_file_extension(file_path):
    file_ext = os.path.splitext(file_path)[1]
    return clean_extension(file_ext)


def has_any_extension(file_path, extensions):
    file_ext = get_file_extension(file_path)
    return file_ext and extensions and file_ext in [clean_extension(e) for e in extensions]

if _jinja2_available:
    class HamlPyExtension(jinja2.ext.Extension):

        def preprocess(self, source, name, filename=None):
            if name and has_any_extension(name, HAML_FILE_NAME_EXTENSIONS):
                compiler = hamlpy.Compiler()
                try:
                    return compiler.process(source)
                except Exception as e:
                    raise jinja2.TemplateSyntaxError(e, 1, name=name, filename=filename)
            else:
                return source

########NEW FILE########
__FILENAME__ = hamlpy
#!/usr/bin/env python
from nodes import RootNode, FilterNode, HamlNode, create_node
from optparse import OptionParser
import sys

VALID_EXTENSIONS=['haml', 'hamlpy']

class Compiler:

    def __init__(self, options_dict=None):
        options_dict = options_dict or {}
        self.debug_tree = options_dict.pop('debug_tree', False)
        self.options_dict = options_dict

    def process(self, raw_text):
        split_text = raw_text.split('\n')
        return self.process_lines(split_text)

    def process_lines(self, haml_lines):
        root = RootNode(**self.options_dict)
        line_iter = iter(haml_lines)

        haml_node=None
        for line_number, line in enumerate(line_iter):
            node_lines = line

            if not root.parent_of(HamlNode(line)).inside_filter_node():
                if line.count('{') - line.count('}') == 1:
                    start_multiline=line_number # For exception handling

                    while line.count('{') - line.count('}') != -1:
                        try:
                            line = line_iter.next()
                        except StopIteration:
                            raise Exception('No closing brace found for multi-line HAML beginning at line %s' % (start_multiline+1))
                        node_lines += line

            # Blank lines
            if haml_node is not None and len(node_lines.strip()) == 0:
                haml_node.newlines += 1
            else:
                haml_node = create_node(node_lines)
                if haml_node:
                    root.add_node(haml_node)

        if self.options_dict and self.options_dict.get('debug_tree'):
            return root.debug_tree()
        else:
            return root.render()

def convert_files():
    import sys
    import codecs

    parser = OptionParser()
    parser.add_option(
        "-d", "--debug-tree", dest="debug_tree",
        action="store_true",
        help="Print the generated tree instead of the HTML")
    parser.add_option(
        "--attr-wrapper", dest="attr_wrapper",
        type="choice", choices=('"', "'"), default="'",
        action="store",
        help="The character that should wrap element attributes. "
        "This defaults to ' (an apostrophe).")
    (options, args) = parser.parse_args()

    if len(args) < 1:
        print "Specify the input file as the first argument."
    else:
        infile = args[0]
        haml_lines = codecs.open(infile, 'r', encoding='utf-8').read().splitlines()

        compiler = Compiler(options.__dict__)
        output = compiler.process_lines(haml_lines)

        if len(args) == 2:
            outfile = codecs.open(args[1], 'w', encoding='utf-8')
            outfile.write(output)
        else:
            print output

if __name__ == '__main__':
    convert_files()

########NEW FILE########
__FILENAME__ = hamlpy_watcher
# haml-watcher.py
# Author: Christian Stefanescu (st.chris@gmail.com)
#
# Watch a folder for files with the given extensions and call the HamlPy
# compiler if the modified time has changed since the last check.
from time import strftime
import argparse
import sys
import codecs
import os
import os.path
import time
import hamlpy
import nodes as hamlpynodes

try:
    str = unicode
except NameError:
    pass

class Options(object):
    CHECK_INTERVAL = 3  # in seconds
    DEBUG = False  # print file paths when a file is compiled
    VERBOSE = False
    OUTPUT_EXT = '.html'

# dict of compiled files [fullpath : timestamp]
compiled = dict()

class StoreNameValueTagPair(argparse.Action):
    def __call__(self, parser, namespace, values, option_string = None):
        tags = getattr(namespace, 'tags', {})
        if tags is None:
            tags = {}
        for item in values:
            n, v = item.split(':')
            tags[n] = v
        
        setattr(namespace, 'tags', tags)

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-v', '--verbose', help = 'Display verbose output', action = 'store_true')
arg_parser.add_argument('-i', '--input-extension', metavar = 'EXT', default = '.hamlpy', help = 'The file extensions to look for', type = str, nargs = '+')
arg_parser.add_argument('-ext', '--extension', metavar = 'EXT', default = Options.OUTPUT_EXT, help = 'The output file extension. Default is .html', type = str)
arg_parser.add_argument('-r', '--refresh', metavar = 'S', default = Options.CHECK_INTERVAL, help = 'Refresh interval for files. Default is {} seconds'.format(Options.CHECK_INTERVAL), type = int)
arg_parser.add_argument('input_dir', help = 'Folder to watch', type = str)
arg_parser.add_argument('output_dir', help = 'Destination folder', type = str, nargs = '?')
arg_parser.add_argument('--tag', help = 'Add self closing tag. eg. --tag macro:endmacro', type = str, nargs = 1, action = StoreNameValueTagPair)
arg_parser.add_argument('--attr-wrapper', dest = 'attr_wrapper', type = str, choices = ('"', "'"), default = "'", action = 'store', help = "The character that should wrap element attributes. This defaults to ' (an apostrophe).")
arg_parser.add_argument('--jinja', help = 'Makes the necessary changes to be used with Jinja2', default = False, action = 'store_true')

def watched_extension(extension):
    """Return True if the given extension is one of the watched extensions"""
    for ext in hamlpy.VALID_EXTENSIONS:
        if extension.endswith('.' + ext):
            return True
    return False

def watch_folder():
    """Main entry point. Expects one or two arguments (the watch folder + optional destination folder)."""
    argv = sys.argv[1:] if len(sys.argv) > 1 else []
    args = arg_parser.parse_args(sys.argv[1:])
    compiler_args = {}
    
    input_folder = os.path.realpath(args.input_dir)
    if not args.output_dir:
        output_folder = input_folder
    else:
        output_folder = os.path.realpath(args.output_dir)
    
    if args.verbose:
        Options.VERBOSE = True
        print "Watching {} at refresh interval {} seconds".format(input_folder, args.refresh)
    
    if args.extension:
        Options.OUTPUT_EXT = args.extension
    
    if getattr(args, 'tags', False):
        hamlpynodes.TagNode.self_closing.update(args.tags)
    
    if args.input_extension:
        hamlpy.VALID_EXTENSIONS += args.input_extension
    
    if args.attr_wrapper:
        compiler_args['attr_wrapper'] = args.attr_wrapper
    
    if args.jinja:
        for k in ('ifchanged', 'ifequal', 'ifnotequal', 'autoescape', 'blocktrans',
                  'spaceless', 'comment', 'cache', 'localize', 'compress'):
            del hamlpynodes.TagNode.self_closing[k]
            
            hamlpynodes.TagNode.may_contain.pop(k, None)
        
        hamlpynodes.TagNode.self_closing.update({
            'macro'  : 'endmacro',
            'call'   : 'endcall',
            'raw'    : 'endraw'
        })
        
        hamlpynodes.TagNode.may_contain['for'] = 'else'
    
    while True:
        try:
            _watch_folder(input_folder, output_folder, compiler_args)
            time.sleep(args.refresh)
        except KeyboardInterrupt:
            # allow graceful exit (no stacktrace output)
            sys.exit(0)

def _watch_folder(folder, destination, compiler_args):
    """Compares "modified" timestamps against the "compiled" dict, calls compiler
    if necessary."""
    for dirpath, dirnames, filenames in os.walk(folder):
        for filename in filenames:
            # Ignore filenames starting with ".#" for Emacs compatibility
            if watched_extension(filename) and not filename.startswith('.#'):
                fullpath = os.path.join(dirpath, filename)
                subfolder = os.path.relpath(dirpath, folder)
                mtime = os.stat(fullpath).st_mtime
                
                # Create subfolders in target directory if they don't exist
                compiled_folder = os.path.join(destination, subfolder)
                if not os.path.exists(compiled_folder):
                    os.makedirs(compiled_folder)
                
                compiled_path = _compiled_path(compiled_folder, filename)
                if (not fullpath in compiled or
                    compiled[fullpath] < mtime or
                    not os.path.isfile(compiled_path)):
                    compile_file(fullpath, compiled_path, compiler_args)
                    compiled[fullpath] = mtime

def _compiled_path(destination, filename):
    return os.path.join(destination, filename[:filename.rfind('.')] + Options.OUTPUT_EXT)

def compile_file(fullpath, outfile_name, compiler_args):
    """Calls HamlPy compiler."""
    if Options.VERBOSE:
        print '%s %s -> %s' % (strftime("%H:%M:%S"), fullpath, outfile_name)
    try:
        if Options.DEBUG:
            print "Compiling %s -> %s" % (fullpath, outfile_name)
        haml_lines = codecs.open(fullpath, 'r', encoding = 'utf-8').read().splitlines()
        compiler = hamlpy.Compiler(compiler_args)
        output = compiler.process_lines(haml_lines)
        outfile = codecs.open(outfile_name, 'w', encoding = 'utf-8')
        outfile.write(output)
    except Exception, e:
        # import traceback
        print "Failed to compile %s -> %s\nReason:\n%s" % (fullpath, outfile_name, e)
        # print traceback.print_exc()

if __name__ == '__main__':
    watch_folder()

########NEW FILE########
__FILENAME__ = nodes
import re
import sys
from StringIO import StringIO

from elements import Element

try:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import guess_lexer
    _pygments_available = True
except ImportError, e:
    _pygments_available = False

try:
    from markdown import markdown
    _markdown_available = True
except ImportError, e:
    _markdown_available = False

class NotAvailableError(Exception):
    pass

ELEMENT = '%'
ID = '#'
CLASS = '.'
DOCTYPE = '!!!'

HTML_COMMENT = '/'
CONDITIONAL_COMMENT = '/['
HAML_COMMENTS = ['-#', '=#']

VARIABLE = '='
TAG = '-'

INLINE_VARIABLE = re.compile(r'(?<!\\)([#=]\{\s*(.+?)\s*\})')
ESCAPED_INLINE_VARIABLE = re.compile(r'\\([#=]\{\s*(.+?)\s*\})')

COFFEESCRIPT_FILTERS = [':coffeescript', ':coffee']
JAVASCRIPT_FILTER = ':javascript'
CSS_FILTER = ':css'
STYLUS_FILTER = ':stylus'
PLAIN_FILTER = ':plain'
PYTHON_FILTER = ':python'
MARKDOWN_FILTER = ':markdown'
CDATA_FILTER = ':cdata'
PYGMENTS_FILTER = ':highlight'

ELEMENT_CHARACTERS = (ELEMENT, ID, CLASS)

HAML_ESCAPE = '\\'

def create_node(haml_line):
    stripped_line = haml_line.strip()

    if len(stripped_line) == 0:
        return None

    if re.match(INLINE_VARIABLE, stripped_line) or re.match(ESCAPED_INLINE_VARIABLE, stripped_line):
        return PlaintextNode(haml_line)

    if stripped_line[0] == HAML_ESCAPE:
        return PlaintextNode(haml_line)

    if stripped_line.startswith(DOCTYPE):
        return DoctypeNode(haml_line)

    if stripped_line[0] in ELEMENT_CHARACTERS:
        return ElementNode(haml_line)

    if stripped_line[0:len(CONDITIONAL_COMMENT)] == CONDITIONAL_COMMENT:
        return ConditionalCommentNode(haml_line)

    if stripped_line[0] == HTML_COMMENT:
        return CommentNode(haml_line)

    for comment_prefix in HAML_COMMENTS:
        if stripped_line.startswith(comment_prefix):
            return HamlCommentNode(haml_line)

    if stripped_line[0] == VARIABLE:
        return VariableNode(haml_line)

    if stripped_line[0] == TAG:
        return TagNode(haml_line)

    if stripped_line == JAVASCRIPT_FILTER:
        return JavascriptFilterNode(haml_line)

    if stripped_line in COFFEESCRIPT_FILTERS:
        return CoffeeScriptFilterNode(haml_line)

    if stripped_line == CSS_FILTER:
        return CssFilterNode(haml_line)

    if stripped_line == STYLUS_FILTER:
        return StylusFilterNode(haml_line)

    if stripped_line == PLAIN_FILTER:
        return PlainFilterNode(haml_line)

    if stripped_line == PYTHON_FILTER:
        return PythonFilterNode(haml_line)

    if stripped_line == CDATA_FILTER:
        return CDataFilterNode(haml_line)

    if stripped_line == PYGMENTS_FILTER:
        return PygmentsFilterNode(haml_line)

    if stripped_line == MARKDOWN_FILTER:
        return MarkdownFilterNode(haml_line)

    return PlaintextNode(haml_line)

class TreeNode(object):
    ''' Generic parent/child tree class'''
    def __init__(self):
        self.parent = None
        self.children = []

    def left_sibling(self):
        siblings = self.parent.children
        index = siblings.index(self)
        return siblings[index - 1] if index > 0 else None

    def right_sibling(self):
        siblings = self.parent.children
        index = siblings.index(self)
        return siblings[index + 1] if index < len(siblings) - 1 else None

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

class RootNode(TreeNode):
    def __init__(self, attr_wrapper="'"):
        TreeNode.__init__(self)
        self.indentation = -2
        # Number of empty lines to render after node
        self.newlines = 0
        # Rendered text at start of node, e.g. "<p>\n"
        self.before = ''
        # Rendered text at end of node, e.g. "\n</p>"
        self.after = ''
        # Indicates that a node does not render anything (for whitespace removal)
        self.empty_node = False

        # Options
        self.attr_wrapper = attr_wrapper

    def add_child(self, child):
        '''Add child node, and copy all options to it'''
        super(RootNode, self).add_child(child)
        child.attr_wrapper = self.attr_wrapper

    def render(self):
        # Render (sets self.before and self.after)
        self._render_children()
        # Post-render (nodes can modify the rendered text of other nodes)
        self._post_render()
        # Generate HTML
        return self._generate_html()

    def render_newlines(self):
        return '\n' * (self.newlines + 1)

    def parent_of(self, node):
        if (self._should_go_inside_last_node(node)):
            ret = self.children[-1].parent_of(node)
            return ret
        else:
            return self

    def inside_filter_node(self):
        if self.parent:
            return self.parent.inside_filter_node()
        else:
            return False

    def _render_children(self):
        for child in self.children:
            child._render()

    def _post_render(self):
        for child in self.children:
            child._post_render()

    def _generate_html(self):
        output = []
        output.append(self.before)
        for child in self.children:
            output.append(child.before)
            output += [gc._generate_html() for gc in child.children]
            output.append(child.after)
        output.append(self.after)
        return ''.join(output)

    def add_node(self, node):
        if (self._should_go_inside_last_node(node)):
            self.children[-1].add_node(node)
        else:
            self.add_child(node)

    def _should_go_inside_last_node(self, node):
        return len(self.children) > 0 and (node.indentation > self.children[-1].indentation
            or (node.indentation == self.children[-1].indentation and self.children[-1].should_contain(node)))

    def should_contain(self, node):
        return False

    def debug_tree(self):
        return '\n'.join(self._debug_tree([self]))

    def _debug_tree(self, nodes):
        output = []
        for n in nodes:
            output.append('%s%s' % (' ' * (n.indentation + 2), n))
            if n.children:
                output += self._debug_tree(n.children)
        return output

    def __repr__(self):
        return '(%s)' % (self.__class__)

class HamlNode(RootNode):
    def __init__(self, haml):
        RootNode.__init__(self)
        self.haml = haml.strip()
        self.raw_haml = haml
        self.indentation = (len(haml) - len(haml.lstrip()))
        self.spaces = ''.join(haml[0] for i in range(self.indentation))

    def replace_inline_variables(self, content):
        content = re.sub(INLINE_VARIABLE, r'{{ \2 }}', content)
        content = re.sub(ESCAPED_INLINE_VARIABLE, r'\1', content)
        return content

    def __repr__(self):
        return '(%s in=%d, nl=%d: %s)' % (self.__class__, self.indentation, self.newlines, self.haml)

class PlaintextNode(HamlNode):
    '''Node that is not modified or processed when rendering'''
    def _render(self):
        text = self.replace_inline_variables(self.haml)
        # Remove escape character unless inside filter node
        if text and text[0] == HAML_ESCAPE and not self.inside_filter_node():
            text = text.replace(HAML_ESCAPE, '', 1)

        self.before = '%s%s' % (self.spaces, text)
        if self.children:
            self.before += self.render_newlines()
        else:
            self.after = self.render_newlines()
        self._render_children()

class ElementNode(HamlNode):
    '''Node which represents a HTML tag'''
    def __init__(self, haml):
        HamlNode.__init__(self, haml)
        self.django_variable = False

    def _render(self):
        self.element = Element(self.haml, self.attr_wrapper)
        self.django_variable = self.element.django_variable
        self.before = self._render_before(self.element)
        self.after = self._render_after(self.element)
        self._render_children()

    def _render_before(self, element):
        '''Render opening tag and inline content'''
        start = ["%s<%s" % (self.spaces, element.tag)]
        if element.id:
            start.append(" id=%s" % self.element.attr_wrap(self.replace_inline_variables(element.id)))
        if element.classes:
            start.append(" class=%s" % self.element.attr_wrap(self.replace_inline_variables(element.classes)))
        if element.attributes:
            start.append(' ' + self.replace_inline_variables(element.attributes))

        content = self._render_inline_content(self.element.inline_content)

        if element.nuke_inner_whitespace and content:
            content = content.strip()

        if element.self_close and not content:
            start.append(" />")
        elif content:
            start.append(">%s" % (content))
        elif self.children:
            start.append(">%s" % (self.render_newlines()))
        else:
            start.append(">")
        return ''.join(start)

    def _render_after(self, element):
        '''Render closing tag'''
        if element.inline_content:
            return "</%s>%s" % (element.tag, self.render_newlines())
        elif element.self_close:
            return self.render_newlines()
        elif self.children:
            return "%s</%s>\n" % (self.spaces, element.tag)
        else:
            return "</%s>\n" % (element.tag)

    def _post_render(self):
        # Inner whitespace removal
        if self.element.nuke_inner_whitespace:
            self.before = self.before.rstrip()
            self.after = self.after.lstrip()

            if self.children:
                node = self
                # If node renders nothing, do removal on its first child instead
                if node.children[0].empty_node == True:
                    node = node.children[0]
                if node.children:
                    node.children[0].before = node.children[0].before.lstrip()

                node = self
                if node.children[-1].empty_node == True:
                    node = node.children[-1]
                if node.children:
                    node.children[-1].after = node.children[-1].after.rstrip()

        # Outer whitespace removal
        if self.element.nuke_outer_whitespace:
            left_sibling = self.left_sibling()
            if left_sibling:
                # If node has left sibling, strip whitespace after left sibling
                left_sibling.after = left_sibling.after.rstrip()
                left_sibling.newlines = 0
            else:
                # If not, whitespace comes from it's parent node,
                # so strip whitespace before the node
                self.parent.before = self.parent.before.rstrip()
                self.parent.newlines = 0

            self.before = self.before.lstrip()
            self.after = self.after.rstrip()

            right_sibling = self.right_sibling()
            if right_sibling:
                right_sibling.before = right_sibling.before.lstrip()
            else:
                self.parent.after = self.parent.after.lstrip()
                self.parent.newlines = 0

        super(ElementNode, self)._post_render()

    def _render_inline_content(self, inline_content):
        if inline_content == None or len(inline_content) == 0:
            return None

        if self.django_variable:
            content = "{{ " + inline_content.strip() + " }}"
            return content
        else:
            return self.replace_inline_variables(inline_content)

class CommentNode(HamlNode):
    def _render(self):
        self.after = "-->\n"
        if self.children:
            self.before = "<!-- %s" % (self.render_newlines())
            self._render_children()
        else:
            self.before = "<!-- %s " % (self.haml.lstrip(HTML_COMMENT).strip())

class ConditionalCommentNode(HamlNode):
    def _render(self):
        conditional = self.haml[1: self.haml.index(']') + 1 ]

        if self.children:
            self.before = "<!--%s>\n" % (conditional)
        else:
            content = self.haml[len(CONDITIONAL_COMMENT) + len(conditional) - 1:]
            self.before = "<!--%s>%s" % (conditional, content)

        self.after = "<![endif]-->\n"
        self._render_children()

class DoctypeNode(HamlNode):
    def _render(self):
        doctype = self.haml.lstrip(DOCTYPE).strip()

        parts = doctype.split()
        if parts and parts[0] == "XML":
            encoding = parts[1] if len(parts) > 1 else 'utf-8'
            self.before = "<?xml version=%s1.0%s encoding=%s%s%s ?>" % (
                self.attr_wrapper, self.attr_wrapper,
                self.attr_wrapper, encoding, self.attr_wrapper,
            )
        else:
            types = {
                "": '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
                "Strict": '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
                "Frameset": '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">',
                "5": '<!DOCTYPE html>',
                "1.1": '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">'
            }

            if doctype in types:
                self.before = types[doctype]

        self.after = self.render_newlines()

class HamlCommentNode(HamlNode):
    def _render(self):
        self.after = self.render_newlines()[1:]

    def _post_render(self):
        pass

class VariableNode(ElementNode):
    def __init__(self, haml):
        ElementNode.__init__(self, haml)
        self.django_variable = True

    def _render(self):
        tag_content = self.haml.lstrip(VARIABLE)
        self.before = "%s%s" % (self.spaces, self._render_inline_content(tag_content))
        self.after = self.render_newlines()

    def _post_render(self):
        pass

class TagNode(HamlNode):
    self_closing = {'for':'endfor',
                    'if':'endif',
                    'ifchanged':'endifchanged',
                    'ifequal':'endifequal',
                    'ifnotequal':'endifnotequal',
                    'block':'endblock',
                    'filter':'endfilter',
                    'autoescape':'endautoescape',
                    'with':'endwith',
                    'blocktrans': 'endblocktrans',
                    'spaceless': 'endspaceless',
                    'comment': 'endcomment',
                    'cache': 'endcache',
                    'localize': 'endlocalize',
                    'compress': 'endcompress'}
    may_contain = {'if':['else', 'elif'],
                   'ifchanged':'else',
                   'ifequal':'else',
                   'ifnotequal':'else',
                   'for':'empty',
                   'with':'with'}

    def __init__(self, haml):
        HamlNode.__init__(self, haml)
        self.tag_statement = self.haml.lstrip(TAG).strip()
        self.tag_name = self.tag_statement.split(' ')[0]

        if (self.tag_name in self.self_closing.values()):
            raise TypeError("Do not close your Django tags manually.  It will be done for you.")

    def _render(self):
        self.before = "%s{%% %s %%}" % (self.spaces, self.tag_statement)
        if (self.tag_name in self.self_closing.keys()):
            self.before += self.render_newlines()
            self.after = '%s{%% %s %%}%s' % (self.spaces, self.self_closing[self.tag_name], self.render_newlines())
        else:
            if self.children:
                self.before += self.render_newlines()
            else:
                self.after = self.render_newlines()
        self._render_children()

    def should_contain(self, node):
        return isinstance(node, TagNode) and node.tag_name in self.may_contain.get(self.tag_name, '')


class FilterNode(HamlNode):
    def add_node(self, node):
        self.add_child(node)

    def inside_filter_node(self):
        return True

    def _render_children_as_plain_text(self, remove_indentation = True):
        if self.children:
            initial_indentation = len(self.children[0].spaces)
        for child in self.children:
            child.before = ''
            if not remove_indentation:
                child.before = child.spaces
            else:
                child.before = child.spaces[initial_indentation:]
            child.before += child.haml
            child.after = child.render_newlines()

    def _post_render(self):
        # Don't post-render children of filter nodes as we don't want them to be interpreted as HAML
        pass


class PlainFilterNode(FilterNode):
    def __init__(self, haml):
        FilterNode.__init__(self, haml)
        self.empty_node = True

    def _render(self):
        if self.children:
            first_indentation = self.children[0].indentation
        self._render_children_as_plain_text()

class PythonFilterNode(FilterNode):
    def _render(self):
        if self.children:
            self.before = self.render_newlines()[1:]
            indent_offset = len(self.children[0].spaces)
            code = "\n".join([node.raw_haml[indent_offset:] for node in self.children]) + '\n'
            compiled_code = compile(code, "", "exec")

            buffer = StringIO()
            sys.stdout = buffer
            try:
                exec compiled_code
            except Exception as e:
                # Change exception message to let developer know that exception comes from
                # a PythonFilterNode
                if e.args:
                    args = list(e.args)
                    args[0] = "Error in :python filter code: " + e.message
                    e.args = tuple(args)
                raise e
            finally:
                # restore the original stdout
                sys.stdout = sys.__stdout__
            self.before += buffer.getvalue()
        else:
            self.after = self.render_newlines()

class JavascriptFilterNode(FilterNode):
    def _render(self):
        self.before = '<script type=%(attr_wrapper)stext/javascript%(attr_wrapper)s>\n// <![CDATA[%(new_lines)s' % {
            'attr_wrapper': self.attr_wrapper,
            'new_lines': self.render_newlines(),
        }
        self.after = '// ]]>\n</script>\n'
        self._render_children_as_plain_text(remove_indentation = False)

class CoffeeScriptFilterNode(FilterNode):
    def _render(self):
        self.before = '<script type=%(attr_wrapper)stext/coffeescript%(attr_wrapper)s>\n#<![CDATA[%(new_lines)s' % {
            'attr_wrapper': self.attr_wrapper,
            'new_lines': self.render_newlines(),
        }
        self.after = '#]]>\n</script>\n'
        self._render_children_as_plain_text(remove_indentation = False)

class CssFilterNode(FilterNode):
    def _render(self):
        self.before = '<style type=%(attr_wrapper)stext/css%(attr_wrapper)s>\n/*<![CDATA[*/%(new_lines)s' % {
            'attr_wrapper': self.attr_wrapper,
            'new_lines': self.render_newlines(),
        }
        self.after = '/*]]>*/\n</style>\n'
        self._render_children_as_plain_text(remove_indentation = False)

class StylusFilterNode(FilterNode):
    def _render(self):
        self.before = '<style type=%(attr_wrapper)stext/stylus%(attr_wrapper)s>\n/*<![CDATA[*/%(new_lines)s' % {
            'attr_wrapper': self.attr_wrapper,
            'new_lines': self.render_newlines(),
        }
        self.after = '/*]]>*/\n</style>\n'
        self._render_children_as_plain_text()

class CDataFilterNode(FilterNode):
    def _render(self):
        self.before = self.spaces + '<![CDATA[%s' % (self.render_newlines())
        self.after = self.spaces + ']]>\n'
        self._render_children_as_plain_text(remove_indentation = False)

class PygmentsFilterNode(FilterNode):
    def _render(self):
        if self.children:
            if not _pygments_available:
                raise NotAvailableError("Pygments is not available")

            self.before = self.render_newlines()
            indent_offset = len(self.children[0].spaces)
            text = ''.join(''.join([c.spaces[indent_offset:], c.haml, c.render_newlines()]) for c in self.children)
            self.before += highlight(text, guess_lexer(self.haml), HtmlFormatter())
        else:
            self.after = self.render_newlines()

class MarkdownFilterNode(FilterNode):
    def _render(self):
        if self.children:
            if not _markdown_available:
                raise NotAvailableError("Markdown is not available")
            self.before = self.render_newlines()[1:]
            indent_offset = len(self.children[0].spaces)
            lines = []
            for c in self.children:
                haml = c.raw_haml.lstrip()
                if haml[-1] == '\n':
                    haml = haml[:-1]
                lines.append(c.spaces[indent_offset:] + haml + c.render_newlines())
            self.before += markdown( ''.join(lines))
        else:
            self.after = self.render_newlines()

########NEW FILE########
__FILENAME__ = loaders
import os

try:
    from django.template import TemplateDoesNotExist
    from django.template.loaders import filesystem, app_directories
    _django_available = True
except ImportError, e:
    class TemplateDoesNotExist(Exception):
        pass

    _django_available = False

from hamlpy import hamlpy
from hamlpy.template.utils import get_django_template_loaders


# Get options from Django settings
options_dict = {}

if _django_available:
    from django.conf import settings
    if hasattr(settings, 'HAMLPY_ATTR_WRAPPER'):
        options_dict.update(attr_wrapper=settings.HAMLPY_ATTR_WRAPPER)


def get_haml_loader(loader):
    if hasattr(loader, 'Loader'):
        baseclass = loader.Loader
    else:
        class baseclass(object):
            def load_template_source(self, *args, **kwargs):
                return loader.load_template_source(*args, **kwargs)

    class Loader(baseclass):
        def load_template_source(self, template_name, *args, **kwargs):
            name, _extension = os.path.splitext(template_name)
            # os.path.splitext always returns a period at the start of extension
            extension = _extension.lstrip('.')

            if extension in hamlpy.VALID_EXTENSIONS:
                try:
                    haml_source, template_path = super(Loader, self).load_template_source(
                        self._generate_template_name(name, extension), *args, **kwargs
                    )
                except TemplateDoesNotExist:
                    pass
                else:
                    hamlParser = hamlpy.Compiler(options_dict=options_dict)
                    html = hamlParser.process(haml_source)

                    return html, template_path

            raise TemplateDoesNotExist(template_name)

        load_template_source.is_usable = True

        def _generate_template_name(self, name, extension="hamlpy"):
            return "%s.%s" % (name, extension)

    return Loader


haml_loaders = dict((name, get_haml_loader(loader))
        for (name, loader) in get_django_template_loaders())

if _django_available:
    HamlPyFilesystemLoader = get_haml_loader(filesystem)
    HamlPyAppDirectoriesLoader = get_haml_loader(app_directories)

########NEW FILE########
__FILENAME__ = utils
import imp
from os import listdir
from os.path import dirname, splitext

try:
  from django.template import loaders
  _django_available = True
except ImportError, e:
  _django_available = False

MODULE_EXTENSIONS = tuple([suffix[0] for suffix in imp.get_suffixes()])

def get_django_template_loaders():
    if not _django_available:
        return []
    return [(loader.__name__.rsplit('.',1)[1], loader) 
                for loader in get_submodules(loaders)
                if hasattr(loader, 'Loader')]
        
def get_submodules(package):
    submodules = ("%s.%s" % (package.__name__, module)
                for module in package_contents(package))
    return [__import__(module, {}, {}, [module.rsplit(".", 1)[-1]]) 
                for module in submodules]

def package_contents(package):
    package_path = dirname(loaders.__file__)
    contents = set([splitext(module)[0]
            for module in listdir(package_path)
            if module.endswith(MODULE_EXTENSIONS)])
    return contents

########NEW FILE########
__FILENAME__ = templatize
"""
This module decorates the django templatize function to parse haml templates
before the translation utility extracts tags from it.

--Modified to ignore non-haml files.
"""

try:
    from django.utils.translation import trans_real
    _django_available = True
except ImportError, e:
    _django_available = False

import hamlpy
import os


def decorate_templatize(func):
    def templatize(src, origin=None):
        #if the template has no origin file then do not attempt to parse it with haml
        if origin:
            #if the template has a source file, then only parse it if it is haml
            if os.path.splitext(origin)[1].lower() in ['.'+x.lower() for x in hamlpy.VALID_EXTENSIONS]:
                hamlParser = hamlpy.Compiler()
                html = hamlParser.process(src.decode('utf-8'))
                src = html.encode('utf-8')
        return func(src, origin)
    return templatize

if _django_available:
    trans_real.templatize = decorate_templatize(trans_real.templatize)

########NEW FILE########
__FILENAME__ = ext_test
import unittest
import os
from hamlpy.ext import has_any_extension

class ExtTest(unittest.TestCase):
    """
    Tests for methods found in ../ext.py
    """
    
    def test_has_any_extension(self):
        extensions = [
            'hamlpy',
            'haml',
            '.txt'
        ]
        # no directory
        self.assertTrue(has_any_extension('dir.hamlpy', extensions))
        self.assertTrue(has_any_extension('dir.haml', extensions))
        self.assertTrue(has_any_extension('dir.txt', extensions))
        self.assertFalse(has_any_extension('dir.html', extensions))
        # with dot in filename
        self.assertTrue(has_any_extension('dir.dot.hamlpy', extensions))
        self.assertTrue(has_any_extension('dir.dot.haml', extensions))
        self.assertTrue(has_any_extension('dir.dot.txt', extensions))
        self.assertFalse(has_any_extension('dir.dot.html', extensions))
        
        # relative path
        self.assertTrue(has_any_extension('../dir.hamlpy', extensions))
        self.assertTrue(has_any_extension('../dir.haml', extensions))
        self.assertTrue(has_any_extension('../dir.txt', extensions))
        self.assertFalse(has_any_extension('../dir.html', extensions))
        # with dot in filename
        self.assertTrue(has_any_extension('../dir.dot.hamlpy', extensions))
        self.assertTrue(has_any_extension('../dir.dot.haml', extensions))
        self.assertTrue(has_any_extension('../dir.dot.txt', extensions))
        self.assertFalse(has_any_extension('../dir.dot.html', extensions))
        
        # absolute paths
        self.assertTrue(has_any_extension('/home/user/dir.hamlpy', extensions))
        self.assertTrue(has_any_extension('/home/user/dir.haml', extensions))
        self.assertTrue(has_any_extension('/home/user/dir.txt', extensions))
        self.assertFalse(has_any_extension('/home/user/dir.html', extensions))
        # with dot in filename
        self.assertTrue(has_any_extension('/home/user/dir.dot.hamlpy', extensions))
        self.assertTrue(has_any_extension('/home/user/dir.dot.haml', extensions))
        self.assertTrue(has_any_extension('/home/user/dir.dot.txt', extensions))
        self.assertFalse(has_any_extension('/home/user/dir.dot.html', extensions))
########NEW FILE########
__FILENAME__ = hamlnode_test
import unittest
from hamlpy import nodes

class TestElementNode(unittest.TestCase):
    def test_calculates_indentation_properly(self):
        no_indentation = nodes.ElementNode('%div')
        self.assertEqual(0, no_indentation.indentation)
        
        three_indentation = nodes.ElementNode('   %div')
        self.assertEqual(3, three_indentation.indentation)
        
        six_indentation = nodes.ElementNode('      %div')
        self.assertEqual(6, six_indentation.indentation)

    def test_indents_tabs_properly(self):
        no_indentation = nodes.ElementNode('%div')
        self.assertEqual('', no_indentation.spaces)

        one_tab = nodes.HamlNode('	%div')
        self.assertEqual('\t', one_tab.spaces)

        one_space = nodes.HamlNode(' %div')
        self.assertEqual(' ', one_space.spaces)

        three_tabs = nodes.HamlNode('			%div')
        self.assertEqual('\t\t\t', three_tabs.spaces)

        tab_space = nodes.HamlNode('	 %div')
        self.assertEqual('\t\t', tab_space.spaces)

        space_tab = nodes.HamlNode(' 	%div')
        self.assertEqual('  ', space_tab.spaces)
			
    def test_lines_are_always_stripped_of_whitespace(self):
        some_space = nodes.ElementNode('   %div')
        self.assertEqual('%div', some_space.haml)
        
        lots_of_space = nodes.ElementNode('      %div    ')
        self.assertEqual('%div', lots_of_space.haml)
    
    def test_inserts_nodes_into_proper_tree_depth(self):
        no_indentation_node = nodes.ElementNode('%div')
        one_indentation_node = nodes.ElementNode(' %div')
        two_indentation_node = nodes.ElementNode('  %div')
        another_one_indentation_node = nodes.ElementNode(' %div')
        
        no_indentation_node.add_node(one_indentation_node)
        no_indentation_node.add_node(two_indentation_node)
        no_indentation_node.add_node(another_one_indentation_node)
        
        self.assertEqual(one_indentation_node, no_indentation_node.children[0])
        self.assertEqual(two_indentation_node, no_indentation_node.children[0].children[0])
        self.assertEqual(another_one_indentation_node, no_indentation_node.children[1])
    
    def test_adds_multiple_nodes_to_one(self):
        start = nodes.ElementNode('%div')
        one = nodes.ElementNode('  %div')
        two = nodes.ElementNode('  %div')
        three = nodes.ElementNode('  %div')
        
        start.add_node(one)
        start.add_node(two)
        start.add_node(three)
        
        self.assertEqual(3, len(start.children))

    def test_html_indentation_vs_haml_indentation(self):
        pass

    def test_node_parent_function(self):
        root=nodes.ElementNode('%div.a')
        elements = [
            {'node': nodes.ElementNode('  %div.b'), 'expected_parent': 'root'},
            {'node': nodes.ElementNode('  %div.c'), 'expected_parent': 'root'},
            {'node': nodes.ElementNode('    %div.d'), 'expected_parent': 'elements[1]["node"]'},
            {'node': nodes.ElementNode('      %div.e'), 'expected_parent': 'elements[2]["node"]'},
            {'node': nodes.ElementNode('  %div.f'), 'expected_parent': 'root'},
        ]

        for el in elements:
            self.assertEqual(root.parent_of(el['node']), eval(el['expected_parent']))
            root.add_node(el['node'])

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = hamlpy_test
# -*- coding: utf-8 -*-
import unittest
from nose.tools import eq_, raises
from hamlpy import hamlpy

class HamlPyTest(unittest.TestCase):

    def test_applies_id_properly(self):
        haml = '%div#someId Some text'
        html = "<div id='someId'>Some text</div>"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        self.assertEqual(html, result.replace('\n', ''))

    def test_non_ascii_id_allowed(self):
        haml = u'%div#これはテストです test'
        html = u"<div id='これはテストです'>test</div>"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        self.assertEqual(html, result.replace('\n', ''))

    def test_applies_class_properly(self):
        haml = '%div.someClass Some text'
        html = "<div class='someClass'>Some text</div>"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        self.assertEqual(html, result.replace('\n', ''))

    def test_applies_multiple_classes_properly(self):
        haml = '%div.someClass.anotherClass Some text'
        html = "<div class='someClass anotherClass'>Some text</div>"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        self.assertEqual(html, result.replace('\n', ''))

    def test_dictionaries_define_attributes(self):
        haml = "%html{'xmlns':'http://www.w3.org/1999/xhtml', 'xml:lang':'en', 'lang':'en'}"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        self.assertTrue("<html" in result)
        self.assertTrue("xmlns='http://www.w3.org/1999/xhtml'" in result)
        self.assertTrue("xml:lang='en'" in result)
        self.assertTrue("lang='en'" in result)
        self.assertTrue(result.endswith("></html>") or result.endswith("></html>\n"))

    def test_dictionaries_support_arrays_for_id(self):
        haml = "%div{'id':('itemType', '5')}"
        html = "<div id='itemType_5'></div>"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        self.assertEqual(html, result.replace('\n', ''))

    def test_dictionaries_can_by_pythonic(self):
        haml = "%div{'id':['Article','1'], 'class':['article','entry','visible']} Booyaka"
        html = "<div id='Article_1' class='article entry visible'>Booyaka</div>"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        self.assertEqual(html, result.replace('\n', ''))


    def test_html_comments_rendered_properly(self):
        haml = '/ some comment'
        html = "<!-- some comment -->"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result.replace('\n', ''))

    def test_conditional_comments_rendered_properly(self):
        haml = "/[if IE]\n  %h1 You use a shitty browser"
        html = "<!--[if IE]>\n  <h1>You use a shitty browser</h1>\n<![endif]-->\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_single_line_conditional_comments_rendered_properly(self):
        haml = "/[if IE] You use a shitty browser"
        html = "<!--[if IE]> You use a shitty browser<![endif]-->\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_django_variables_on_tag_render_properly(self):
        haml = '%div= story.tease'
        html = '<div>{{ story.tease }}</div>'
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result.replace('\n', ''))

    def test_stand_alone_django_variables_render(self):
        haml = '= story.tease'
        html = '{{ story.tease }}'
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result.replace('\n', ''))

    def test_stand_alone_django_tags_render(self):
        haml = '- extends "something.html"'
        html = '{% extends "something.html" %}'
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result.replace('\n', ''))

    def test_if_else_django_tags_render(self):
        haml = '- if something\n   %p hello\n- else\n   %p goodbye'
        html = '{% if something %}\n   <p>hello</p>\n{% else %}\n   <p>goodbye</p>\n{% endif %}\n'
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    @raises(TypeError)
    def test_throws_exception_when_trying_to_close_django(self):
        haml = '- endfor'
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)

    def test_handles_dash_in_class_name_properly(self):
        haml = '.header.span-24.last'
        html = "<div class='header span-24 last'></div>\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_handles_multiple_attributes_in_dict(self):
        haml = "%div{'id': ('article', '3'), 'class': ('newest', 'urgent')} Content"
        html = "<div id='article_3' class='newest urgent'>Content</div>\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_inline_variables_are_parsed_correctly(self):
        haml = "={greeting} #{name}, how are you ={date}?"
        html = "{{ greeting }} {{ name }}, how are you {{ date }}?\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_inline_variables_can_use_filter_characters(self):
        haml = "={value|center:\"15\"}"
        html = "{{ value|center:\"15\" }}\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_inline_variables_in_attributes_are_parsed_correctly(self):
        haml = "%a{'b': '={greeting} test'} blah"
        html = "<a b='{{ greeting }} test'>blah</a>\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_inline_variables_in_attributes_work_in_id(self):
        haml = "%div{'id':'package_={object.id}'}"
        html = "<div id='package_{{ object.id }}'></div>\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_inline_variables_in_attributes_work_in_class(self):
        haml = "%div{'class':'package_={object.id}'}"
        html = "<div class='package_{{ object.id }}'></div>\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_inline_variables_in_attributes_are_escaped_correctly(self):
        haml = "%a{'b': '\\\\={greeting} test', title: \"It can't be removed\"} blah"
        html = "<a b='={greeting} test' title='It can\\'t be removed'>blah</a>\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_inline_variables_escaping_works(self):
        haml = "%h1 Hello, \\#{name}, how are you ={ date }?"
        html = "<h1>Hello, #{name}, how are you {{ date }}?</h1>\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_inline_variables_escaping_works_at_start_of_line(self):
        haml = "\\={name}, how are you?"
        html = "={name}, how are you?\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_inline_variables_with_hash_escaping_works_at_start_of_line(self):
        haml = "\\#{name}, how are you?"
        html = "#{name}, how are you?\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_inline_variables_work_at_start_of_line(self):
        haml = "={name}, how are you?"
        html = "{{ name }}, how are you?\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_inline_variables_with_hash_work_at_start_of_line(self):
        haml = "#{name}, how are you?"
        html = "{{ name }}, how are you?\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_inline_variables_with_special_characters_are_parsed_correctly(self):
        haml = "%h1 Hello, #{person.name}, how are you?"
        html = "<h1>Hello, {{ person.name }}, how are you?</h1>\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_plain_text(self):
        haml = "This should be plain text\n    This should be indented"
        html = "This should be plain text\n    This should be indented\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_plain_text_with_indenting(self):
        haml = "This should be plain text"
        html = "This should be plain text\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_escaped_haml(self):
        haml = "\\= Escaped"
        html = "= Escaped\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_utf8_with_regular_text(self):
        haml = u"%a{'href':'', 'title':'링크(Korean)'} Some Link"
        html = u"<a href='' title='\ub9c1\ud06c(Korean)'>Some Link</a>\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_python_filter(self):
        haml = ":python\n   for i in range(0, 5): print \"<p>item \%s</p>\" % i"
        html = '<p>item \\0</p>\n<p>item \\1</p>\n<p>item \\2</p>\n<p>item \\3</p>\n<p>item \\4</p>\n'
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_doctype_html5(self):
        haml = '!!! 5'
        html = '<!DOCTYPE html>'
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result.replace('\n', ''))

    def test_doctype_xhtml(self):
        haml = '!!!'
        html = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result.replace('\n', ''))

    def test_doctype_xml_utf8(self):
        haml = '!!! XML'
        html = "<?xml version='1.0' encoding='utf-8' ?>"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result.replace('\n', ''))

    def test_doctype_xml_encoding(self):
        haml = '!!! XML iso-8859-1'
        html = "<?xml version='1.0' encoding='iso-8859-1' ?>"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result.replace('\n', ''))

    def test_plain_filter_with_indentation(self):
        haml = ":plain\n    -This should be plain text\n    .This should be more\n      This should be indented"
        html = "-This should be plain text\n.This should be more\n  This should be indented\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_plain_filter_with_no_children(self):
        haml = ":plain\nNothing"
        html = "Nothing\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_filters_render_escaped_backslash(self):
        haml = ":plain\n  \\Something"
        html = "\\Something\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_xml_namespaces(self):
        haml = "%fb:tag\n  content"
        html = "<fb:tag>\n  content\n</fb:tag>\n"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result)

    def test_attr_wrapper(self):
        haml = """
%html{'xmlns':'http://www.w3.org/1999/xhtml', 'xml:lang':'en', 'lang':'en'}
  %body#main
    %div.wrap
      %a{:href => '/'}
:javascript"""
        hamlParser = hamlpy.Compiler(options_dict={'attr_wrapper': '"'})
        result = hamlParser.process(haml)
        self.assertEqual(result,
                         '''<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
  <body id="main">
    <div class="wrap">
      <a href="/"></a>
    </div>
  </body>
</html>
<script type="text/javascript">
// <![CDATA[
// ]]>
</script>
''')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = loader_test
import unittest
import sys

try:
  from django.conf import settings

  settings.configure(DEBUG=True, TEMPLATE_DEBUG=True)
except ImportError, e:
  pass

from hamlpy.template.loaders import get_haml_loader, TemplateDoesNotExist

class DummyLoader(object):
    """
    A dummy template loader that only loads templates from self.templates
    """
    templates = {
        "in_dict.txt" : "in_dict content",
        "loader_test.hamlpy" : "loader_test content",
    }
    def __init__(self, *args, **kwargs):
        self.Loader = self.__class__
    
    def load_template_source(self, template_name, *args, **kwargs):
        try:
            return (self.templates[template_name], "test:%s" % template_name)
        except KeyError:
            raise TemplateDoesNotExist(template_name)

class LoaderTest(unittest.TestCase):
    """
    Tests for the django template loader.
    
    A dummy template loader is used that loads only from a dictionary of templates.
    """
    
    def setUp(self): 
        dummy_loader = DummyLoader()
        
        hamlpy_loader_class = get_haml_loader(dummy_loader)
        self.hamlpy_loader = hamlpy_loader_class()
    
    def _test_assert_exception(self, template_name):
        try:
            self.hamlpy_loader.load_template_source(template_name)
        except TemplateDoesNotExist:
            self.assertTrue(True)
        else:
            self.assertTrue(False, '\'%s\' should not be loaded by the hamlpy tempalte loader.' % template_name)
    
    def test_file_not_in_dict(self):
        # not_in_dict.txt doesn't exit, so we're expecting an exception
        self._test_assert_exception('not_in_dict.hamlpy')
    
    def test_file_in_dict(self):
        # in_dict.txt in in dict, but with an extension not supported by
        # the loader, so we expect an exception
        self._test_assert_exception('in_dict.txt')
    
    def test_file_should_load(self):
        # loader_test.hamlpy is in the dict, so it should load fine
        try:
            self.hamlpy_loader.load_template_source('loader_test.hamlpy')
        except TemplateDoesNotExist:
            self.assertTrue(False, '\'loader_test.hamlpy\' should be loaded by the hamlpy tempalte loader, but it was not.')
        else:
            self.assertTrue(True)
    
    def test_file_different_extension(self):
        # loader_test.hamlpy is in dict, but we're going to try
        # to load loader_test.txt
        # we expect an exception since the extension is not supported by
        # the loader
        self._test_assert_exception('loader_test.txt')

########NEW FILE########
__FILENAME__ = node_factory_test
from hamlpy import nodes

class TestNodeFactory():
    
    def test_creates_element_node_with_percent(self):
        node = nodes.create_node('%div')
        assert isinstance(node, nodes.ElementNode)
        
        node = nodes.create_node('   %html')
        assert isinstance(node, nodes.ElementNode)
        
    def test_creates_element_node_with_dot(self):
        node = nodes.create_node('.className')
        assert isinstance(node, nodes.ElementNode)
        
        node = nodes.create_node('   .className')
        assert isinstance(node, nodes.ElementNode)
        
    def test_creates_element_node_with_hash(self):
        node = nodes.create_node('#idName')
        assert isinstance(node, nodes.ElementNode)
        
        node = nodes.create_node('   #idName')
        assert isinstance(node, nodes.ElementNode)
    
    def test_creates_html_comment_node_with_front_slash(self):
        node = nodes.create_node('/ some Comment')
        assert isinstance(node, nodes.CommentNode)

        node = nodes.create_node('     / some Comment')
        assert isinstance(node, nodes.CommentNode)
        
    def test_random_text_returns_haml_node(self):
        node = nodes.create_node('just some random text')
        assert isinstance(node, nodes.HamlNode)
        
        node = nodes.create_node('   more random text')
        assert isinstance(node, nodes.HamlNode)
    
    def test_correct_symbol_creates_haml_comment(self):
        node = nodes.create_node('-# This is a haml comment')
        assert isinstance(node, nodes.HamlCommentNode)
        
    def test_equals_symbol_creates_variable_node(self):
        node = nodes.create_node('= some.variable')
        assert isinstance(node, nodes.VariableNode)
    
    def test_dash_symbol_creates_tag_node(self):
        node = nodes.create_node('- for something in somethings')
        assert isinstance(node, nodes.TagNode)
    
    def test_backslash_symbol_creates_tag_node(self):
        node = nodes.create_node('\\= some.variable')
        assert isinstance(node, nodes.HamlNode)
        
        node = nodes.create_node('    \\= some.variable')
        assert isinstance(node, nodes.HamlNode)
    
    def test_python_creates_python_node(self):
        node = nodes.create_node(':python')
        assert isinstance(node, nodes.PythonFilterNode)
    
    def test_slash_with_if_creates_a_conditional_comment_node(self):
        node = nodes.create_node('/[if IE 5]')
        assert isinstance(node, nodes.ConditionalCommentNode)
        

########NEW FILE########
__FILENAME__ = regression
# -*- coding: utf-8 -*-
import unittest
from nose.tools import eq_, raises
from hamlpy import hamlpy

class RegressionTest(unittest.TestCase):
    # Regression test for Github Issue 92
    def test_haml_comment_nodes_dont_post_render_children(self):
        haml = '''
        -# My comment
            #my_div
                my text
        test
        '''
        html = "test"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result.strip())
        
    def test_whitespace_after_attribute_key(self):
        haml = '%form{id : "myform"}'
        html = "<form id='myform'></form>"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result.strip())
    
    def test_for_newline_after_conditional_comment(self):
        haml = '/[if lte IE 7]\n\ttest\n#test'
        html = "<!--[if lte IE 7]>\n\ttest\n<![endif]-->\n<div id='test'></div>"
        hamlParser = hamlpy.Compiler()
        result = hamlParser.process(haml)
        eq_(html, result.strip())

########NEW FILE########
__FILENAME__ = template_compare_test
import codecs
import unittest
from nose.tools import eq_
from hamlpy import hamlpy

class TestTemplateCompare(unittest.TestCase):

    def test_nuke_inner_whitespace(self):
        self._compare_test_files('nukeInnerWhiteSpace')

    def test_nuke_outer_whitespace(self):
        self._compare_test_files('nukeOuterWhiteSpace')

    def test_comparing_simple_templates(self):
        self._compare_test_files('simple')
        
    def test_mixed_id_and_classes_using_dictionary(self):
        self._compare_test_files('classIdMixtures')
    
    def test_self_closing_tags_close(self):
        self._compare_test_files('selfClosingTags')
        
    def test_nested_html_comments(self):
        self._compare_test_files('nestedComments')
        
    def test_haml_comments(self):
        self._compare_test_files('hamlComments')
        
    def test_implicit_divs(self):
        self._compare_test_files('implicitDivs')
        
    def test_django_combination_of_tags(self):
        self._compare_test_files('djangoCombo')
        
    def test_self_closing_django(self):
        self._compare_test_files('selfClosingDjango')
        
    def test_nested_django_tags(self):
        self._compare_test_files('nestedDjangoTags')
        
    def test_filters(self):
        self._compare_test_files('filters')
    
    def test_filters_markdown(self):
        try:
            import markdown
            self._compare_test_files('filtersMarkdown')
        except ImportError:
            pass

    def test_filters_pygments(self):
        try:
            import pygments
            if pygments.__version__ == '1.6':
                self._compare_test_files('filtersPygments16')
            else:
                self._compare_test_files('filtersPygments')
        except ImportError:
            pass

    def test_nested_if_else_blocks(self):
        self._compare_test_files('nestedIfElseBlocks')

    def test_all_if_types(self):
        self._compare_test_files('allIfTypesTest')

    def test_multi_line_dict(self):
        self._compare_test_files('multiLineDict')

    def test_filter_multiline_ignore(self):
        self._compare_test_files('filterMultilineIgnore')

    def test_whitespace_preservation(self):
        self._compare_test_files('whitespacePreservation')

    def _print_diff(self, s1, s2):
        if len(s1) > len(s2):
            shorter = s2
        else:
            shorter = s1

        line = 1
        col = 1
        
        for i, _ in enumerate(shorter):
            if len(shorter) <= i + 1:
                print 'Ran out of characters to compare!'
                print 'Actual len=%d' % len(s1)
                print 'Expected len=%d' % len(s2)
                break
            if s1[i] != s2[i]:
                print 'Difference begins at line', line, 'column', col
                actual_line = s1.splitlines()[line - 1]
                expected_line = s2.splitlines()[line - 1]
                print 'HTML (actual, len=%2d)   : %s' % (len(actual_line), actual_line)
                print 'HTML (expected, len=%2d) : %s' % (len(expected_line), expected_line)
                print 'Character code (actual)  : %d (%s)' % (ord(s1[i]), s1[i])
                print 'Character code (expected): %d (%s)' % (ord(s2[i]), s2[i])
                break

            if shorter[i] == '\n':
                line += 1
                col = 1
            else:
                col += 1
        else:
            print "No Difference Found"

    def _compare_test_files(self, name):
        haml_lines = codecs.open('templates/' + name + '.hamlpy', encoding = 'utf-8').readlines()
        html = open('templates/' + name + '.html').read()
        
        haml_compiler = hamlpy.Compiler()
        parsed = haml_compiler.process_lines(haml_lines)

        # Ignore line ending differences
        parsed = parsed.replace('\r', '')
        html = html.replace('\r', '')
        
        if parsed != html:
            print '\nHTML (actual): '
            print '\n'.join(["%d. %s" % (i + 1, l) for i, l in enumerate(parsed.split('\n')) ])
            self._print_diff(parsed, html)
        eq_(parsed, html)
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_elements
from nose.tools import eq_

from hamlpy.elements import Element

class TestElement(object):

        def test_attribute_value_not_quoted_when_looks_like_key(self):
            sut = Element('')
            s1 = sut._parse_attribute_dictionary('''{name:"viewport", content:"width:device-width, initial-scale:1, minimum-scale:1, maximum-scale:1"}''')
            eq_(s1['content'], 'width:device-width, initial-scale:1, minimum-scale:1, maximum-scale:1')
            eq_(s1['name'], 'viewport')

            sut = Element('')
            s1 = sut._parse_attribute_dictionary('''{style:"a:x, b:'y', c:1, e:3"}''')
            eq_(s1['style'], "a:x, b:'y', c:1, e:3")

            sut = Element('')
            s1 = sut._parse_attribute_dictionary('''{style:"a:x, b:'y', c:1, d:\\"dk\\", e:3"}''')
            eq_(s1['style'], '''a:x, b:'y', c:1, d:"dk", e:3''')

            sut = Element('')
            s1 = sut._parse_attribute_dictionary('''{style:'a:x, b:\\'y\\', c:1, d:"dk", e:3'}''')
            eq_(s1['style'], '''a:x, b:'y', c:1, d:"dk", e:3''')

        def test_dashes_work_in_attribute_quotes(self):
            sut = Element('')
            s1 = sut._parse_attribute_dictionary('''{"data-url":"something", "class":"blah"}''')
            eq_(s1['data-url'],'something')
            eq_(s1['class'], 'blah')

            s1 = sut._parse_attribute_dictionary('''{data-url:"something", class:"blah"}''')
            eq_(s1['data-url'],'something')
            eq_(s1['class'], 'blah')

        def test_escape_quotes_except_django_tags(self):
            sut = Element('')

            s1 = sut._escape_attribute_quotes('''{% url 'blah' %}''')
            eq_(s1,'''{% url 'blah' %}''')

            s2 = sut._escape_attribute_quotes('''blah's blah''s {% url 'blah' %} blah's blah''s''')
            eq_(s2,r"blah\'s blah\'\'s {% url 'blah' %} blah\'s blah\'\'s")

        def test_attributes_parse(self):
            sut = Element('')

            s1 = sut._parse_attribute_dictionary('''{a:'something',"b":None,'c':2}''')
            eq_(s1['a'],'something')
            eq_(s1['b'],None)
            eq_(s1['c'],2)

            eq_(sut.attributes, "a='something' c='2' b")

        def test_pulls_tag_name_off_front(self):
            sut = Element('%div.class')
            eq_(sut.tag, 'div')
            
        def test_default_tag_is_div(self):
            sut = Element('.class#id')
            eq_(sut.tag, 'div')
            
        def test_parses_id(self):
            sut = Element('%div#someId.someClass')
            eq_(sut.id, 'someId')
            
            sut = Element('#someId.someClass')
            eq_(sut.id, 'someId')
            
        def test_no_id_gives_empty_string(self):
            sut = Element('%div.someClass')
            eq_(sut.id, '')
        
        def test_parses_class(self):
            sut = Element('%div#someId.someClass')
            eq_(sut.classes, 'someClass')
            
        def test_properly_parses_multiple_classes(self):
            sut = Element('%div#someId.someClass.anotherClass')
            eq_(sut.classes, 'someClass anotherClass')
            
        def test_no_class_gives_empty_string(self):
            sut = Element('%div#someId')
            eq_(sut.classes, '')
            
        def test_attribute_dictionary_properly_parses(self):
            sut = Element("%html{'xmlns':'http://www.w3.org/1999/xhtml', 'xml:lang':'en', 'lang':'en'}")
            assert "xmlns='http://www.w3.org/1999/xhtml'" in sut.attributes
            assert "xml:lang='en'" in sut.attributes
            assert "lang='en'" in sut.attributes

        def test_id_and_class_dont_go_in_attributes(self):
            sut = Element("%div{'class':'hello', 'id':'hi'}")
            assert 'class=' not in sut.attributes
            assert 'id=' not in sut.attributes
            
        def test_attribute_merges_classes_properly(self):
            sut = Element("%div.someClass.anotherClass{'class':'hello'}")
            assert 'someClass' in sut.classes
            assert 'anotherClass' in sut.classes
            assert 'hello' in sut.classes
            
        def test_attribute_merges_ids_properly(self):
            sut = Element("%div#someId{'id':'hello'}")
            eq_(sut.id, 'someId_hello')
            
        def test_can_use_arrays_for_id_in_attributes(self):
            sut = Element("%div#someId{'id':['more', 'andMore']}")
            eq_(sut.id, 'someId_more_andMore')
        
        def test_self_closes_a_self_closing_tag(self):
            sut = Element(r"%br")
            assert sut.self_close
            
        def test_does_not_close_a_non_self_closing_tag(self):
            sut = Element("%div")
            assert sut.self_close == False
            
        def test_can_close_a_non_self_closing_tag(self):
            sut = Element("%div/")
            assert sut.self_close
            
        def test_properly_detects_django_tag(self):
            sut = Element("%div= $someVariable")
            assert sut.django_variable
            
        def test_knows_when_its_not_django_tag(self):
            sut = Element("%div Some Text")
            assert sut.django_variable == False
            
        def test_grabs_inline_tag_content(self):
            sut = Element("%div Some Text")
            eq_(sut.inline_content, 'Some Text')
            
        def test_multiline_attributes(self):
            sut = Element("""%link{'rel': 'stylesheet', 'type': 'text/css',
                'href': '/long/url/to/stylesheet/resource.css'}""")
            assert "href='/long/url/to/stylesheet/resource.css'" in sut.attributes
            assert "type='text/css'" in sut.attributes
            assert "rel='stylesheet'" in sut.attributes

########NEW FILE########
