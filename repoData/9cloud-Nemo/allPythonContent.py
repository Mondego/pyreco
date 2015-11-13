__FILENAME__ = mako_test
import sys
from nemo.parser import NemoParser
from mako.template import Template

if len(sys.argv) > 1:
    filename = sys.argv[1]
else:
    print 'A filename is required'
    exit()

def nemo(str):
    print "---------  %s --------------" % filename
    # Return a result to Mako which will then render the string
    return NemoParser(debug=False).parse(str)

t = Template(filename=filename,
            preprocessor=nemo,
            input_encoding='utf-8',
            output_encoding='utf-8',)
print t.render()

########NEW FILE########
__FILENAME__ = cache
from mako.cache import CacheImpl, register_plugin
from django.core.cache import cache

class DjangoCache(CacheImpl):
    def __init__(self, cache):
        super(DjangoCache, self).__init__(cache)

    def get_or_create(self, key, creation_function, **kw):
        value = cache.get(key)

        if not value:
            timeout = kw.get('timeout', None)
            value = creation_function()
            cache.set(key, value, timeout)

        return value

    def set(self, key, value, **kwargs):
        timeout = kw.get('timeout', None)
        cache.set(key, value, timeout)

    def get(self, key, **kwargs):
        return cache.get(key)

    def invalidate(self, key, **kwargs):
        cache.delete(key)

# optional - register the class locally
register_plugin("django_cache", __name__, "DjangoCache")
########NEW FILE########
__FILENAME__ = defaults
"""Options used only by Django"""

import os
import logging
from django.conf import settings
from nemo.parser import nemo

MAKO_TEMPLATE_DIRS=(os.path.join(settings.SITE_ROOT, 'templates'),)
MAKO_TEMPLATE_OPTS=dict(input_encoding='utf-8',
                        output_encoding='utf-8',
                        module_directory=os.path.join(settings.SITE_ROOT, 'cache'),
                        preprocessor=nemo
)

########NEW FILE########
__FILENAME__ = importlib
# A copy of importlib from Django 1.1.
# Present here to maintain backward-compatibility with Django 1.0.
import sys

def _resolve_name(name, package, level):
    """Return the absolute name of the module to be imported."""
    if not hasattr(package, 'rindex'):
        raise ValueError("'package' not set to a string")
    dot = len(package)
    for x in xrange(level, 1, -1):
        try:
            dot = package.rindex('.', 0, dot)
        except ValueError:
            raise ValueError("attempted relative import beyond top-level "
                              "package")
    return "%s.%s" % (package[:dot], name)


def import_module(name, package=None):
    """Import a module.

    The 'package' argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    """
    if name.startswith('.'):
        if not package:
            raise TypeError("relative imports require the 'package' argument")
        level = 0
        for character in name:
            if character != '.':
                break
            level += 1
        name = _resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]

########NEW FILE########
__FILENAME__ = loader
"""
Mako templates for django >= 1.2.
"""

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.context import Context
from django.template.loaders.filesystem import Loader as FSLoader

from mako.exceptions import MakoException, TopLevelLookupException
from mako.template import Template
from mako.lookup import TemplateLookup


def context_to_dict(ctxt):
    res = {}
    for d in reversed(ctxt.dicts):
        # sometimes contexts will be nested
        if isinstance(d, Context):
            res.update(context_to_dict(d))
        else:
            res.update(d)
    return res


def _get_start_and_end(source, lineno, pos):
    start = 0
    for n, line in enumerate(source.splitlines()):
        if n == lineno:
            start += pos
            break
        else:
            start += len(line) - 1
    return start, start


class MakoExceptionWrapper(Exception):
    def __init__(self, exc, origin):
        self._exc = exc
        self._origin = origin
        self.args = self._exc.args

    def __getattr__(self, name):
        return getattr(self._exc, name)

    @property
    def source(self):
        return (self._origin,
                _get_start_and_end(self._exc.source,
                                   self._exc.lineno,
                                   self._exc.pos))


class MakoTemplate(object):
    def __init__(self, template_obj, origin=None):
        self.template_obj = template_obj
        self.origin = origin

    def render(self, context):
        try:
            return self.template_obj.render_unicode(**context_to_dict(context))
        except MakoException, me:
            if hasattr(me, 'source'):
                raise MakoExceptionWrapper(me, self.origin)
            else:
                raise me

_lookup = None


def get_lookup():
    global _lookup
    if _lookup is None:
        opts = getattr(settings, 'MAKO_TEMPLATE_OPTS', {})
        _lookup = TemplateLookup(directories=settings.MAKO_TEMPLATE_DIRS,
                                 **opts)
    return _lookup


class MakoLoader(FSLoader):
    is_usable = True

    def load_template(self, template_name, template_dirs=None):
        lookup = get_lookup()
        try:
            real_template = lookup.get_template(template_name)
            return MakoTemplate(real_template, template_name), template_name
        except TopLevelLookupException:
            raise TemplateDoesNotExist(
                'mako template not found for name %s' % template_name)
        except MakoException, me:
            if hasattr(me, 'source'):
                raise MakoExceptionWrapper(me, template_name)
            raise me

########NEW FILE########
__FILENAME__ = models
# Just an empty because Django requires this
########NEW FILE########
__FILENAME__ = shortcuts
"""
 Defines variations on render_to_string and render_to_response that will optionally only render a single mako def
"""

from mako.exceptions import MakoException
from django.template.loader import get_template, select_template
from djmako.loader import context_to_dict
from django.template.context import Context, RequestContext
from django.http import HttpResponse
from django.utils import simplejson
from djmako.loader import MakoExceptionWrapper

from django.shortcuts import redirect

__all__ = ('redirect', 'render_to_string', 'render_to_response', 'json_response', 'render')

## Patched from on MakoTemplate.render()
def render_nemo_template(mako_template, context, def_name):
    try:
        template_obj = mako_template.template_obj

        if def_name is not None:
            template_obj = mako_template.template_obj.get_def(def_name)

        return template_obj.render_unicode(**context_to_dict(context))
    except MakoException, me:
        if hasattr(me, 'source'):
            raise MakoExceptionWrapper(me, mako_template.origin)
        else:
            raise me


def render_to_string(template_name, dictionary=None, context_instance=None, def_name=None):
    """
    Loads the given template_name and renders it with the given dictionary as
    context. The template_name may be a string to load a single template using
    get_template, or it may be a tuple to use select_template to find one of
    the templates in the list. Returns a string.
    """
    dictionary = dictionary or {}
    if isinstance(template_name, (list, tuple)):
        t = select_template(template_name)
    else:
        t = get_template(template_name)
    if context_instance:
        context_instance.update(dictionary)
    else:
        context_instance = Context(dictionary)

    return render_nemo_template(t, context_instance, def_name)


def render_to_response(*args, **kwargs):
    """
    Returns a HttpResponse whose content is filled with the result of calling
    django.template.loader.render_to_string() with the passed arguments.
    """
    httpresponse_kwargs = {'mimetype': kwargs.pop('mimetype', None),
                           'status': kwargs.pop('status', None),
                           'content_type': kwargs.pop('content_type', None)
                           }
    return HttpResponse(render_to_string(*args, **kwargs), **httpresponse_kwargs)

def json_response(obj, **kwargs):
    return HttpResponse(simplejson.dumps(obj), **kwargs)

def render(request, *args, **kwargs):
    """
    Returns a HttpResponse whose content is filled with the result of calling
    django.template.loader.render_to_string() with the passed arguments.
    Uses a RequestContext by default.
    """
    httpresponse_kwargs = {'mimetype': kwargs.pop('mimetype', None),
                           'status': kwargs.pop('status', None),
                           'content_type': kwargs.pop('content_type', None)
                           }

    if 'context_instance' in kwargs:
        context_instance = kwargs.pop('context_instance')
        if kwargs.get('current_app', None):
            raise ValueError('If you provide a context_instance you must '
                             'set its current_app before calling render()')
    else:
        current_app = kwargs.pop('current_app', None)
        context_instance = RequestContext(request, current_app=current_app)

    kwargs['context_instance'] = context_instance

    return HttpResponse(render_to_string(*args, **kwargs), **httpresponse_kwargs)
########NEW FILE########
__FILENAME__ = exceptions
class NemoException(Exception):
    pass
########NEW FILE########
__FILENAME__ = nodes
from exceptions import NemoException

PERMISSIVE = True

class Node(object):
    is_root = False
    follows_indentation_rules = True

    def __init__(self, value, depth, line_number):
        self.value = value
        self.depth = depth # This is the indentation depth, not the tree depth
        self.line_number = line_number

        self.parent = None
        self.children = []
        self.siblings = []

    def add_child(self, node):
        raise NotImplemented()

    def check_as_closer(self, node, active_node):
        """
           The passed in node was added as your child, and is attempting to close your scope.
           Is this allowed?
        """
        raise NemoException('\nIncorrect indentation\n' + \
                            'at:\n\t%s\n' % node + \
                            'Tried to close against:\n\t%s\n' % self + \
                            'Within active scope of:\n\t%s' % active_node )

    def write(self, buffer):
        raise NotImplemented()

    def __str__(self):
        return str(unicode(self))

    def __unicode__(self):
        return u'[%d|Line: %d][%s]' % (self.depth, self.line_number, self.value)


class NemoNode(Node):
    @property
    def value(self):
        return '%s %s' % (self._keyword, self._arguments)

    @value.setter
    def value(self, value):
        self._keyword, self._arguments = value

    def add_child(self, node):
        self.children.append(node)
        node.parent = self

    def _padding(self):
        return [' ' for i in xrange(1, self.depth)]

    def write(self, buffer):
        buffer.write('\n')
        buffer.writelines( self._padding() )
        # Open Tag
        buffer.writelines( ['<', self._keyword, ' ', self._arguments ] )

        if len(self.children) is 0:
            # This tag is automatically closed inline
            buffer.write(' />')
        else:
            # Close Open Tag
            buffer.write('>')

            self._write_children(buffer)

            # Write close Tag
            buffer.write('\n')
            buffer.writelines( self._padding() )
            buffer.writelines( ['</', self._keyword, '>'] )


    def check_indentation_rules(self, children):
        depth_seen = None
        for child in children:
            # Ensure child is at correct depth
            # If this is disabled then depth.failure and inner_tag_indentation.failure will both succeed
            # It is dubious if we want this
            # Todo: Permissive mode
            if child.follows_indentation_rules and not PERMISSIVE:
                if depth_seen is None:
                    depth_seen = child.depth
                elif child.depth is not depth_seen:
                    raise NemoException('\nIncorrect indentation\n' + \
                                         'at:\n\t%s\n' % child + \
                                         'within:\n\t%s\n' % self + \
                                         'expected indentation of %d ' % depth_seen)

            yield child

    def check_open_close_on_mako_nodes(self, children):
        open_mako_context = None
        for child in children:
            child_type = type(child)

            # Check child nodes for open/close semantics
            if child_type is MakoNode and open_mako_context is None:
                open_mako_context = child
            if child_type is MakoEndTag:
                if open_mako_context is None:
                    # Closer w/o an open context
                    raise NemoException('\nEnd tag without open context\n' + \
                                        'at:\n\t%s\n' % child + \
                                        'within:\n\t%s\n' % self )
                # Close context
                open_mako_context = None

            yield child

        if open_mako_context is not None:
            # Open context without a closer
            raise NemoException('\nOpen tag without a closer found:\n' + \
                                'at:\n\t%s\n' % open_mako_context + \
                                'within:\n\t%s\n' % self )
        
            
    def _write_children(self, buffer):
        """
           Write child nodes onto the buffer.
           Ensure that all non-leaf (end tags, raw strings), occur on the same depth
        """
        children = self.check_open_close_on_mako_nodes(
                   self.check_indentation_rules(
                        self.children))

        for child in children:
            # Write the child
            child.write(buffer)

class MakoNode(NemoNode):
    """
        I represent a tag in Mako. Either an openning tag, or a middle tag.
        I can have children.
    """
    def __init__(self, value, depth, line_number):
        self.value = (value, '')
        self.depth = depth
        self.line_number = line_number
        self.children = []

    def add_child(self, node):
        self.children.append(node)
        node.parent = self

    def write(self, buffer):
        buffer.write("\n")
        buffer.write(self.value)


        self._write_children(buffer)

    # Note, very soon this check is going to be removed.
    # Right now it just provides security against unforseen bugs, causing an explicit failure instead of empty nodes
    def check_as_closer(self, node, active_node):
        #print node
        #print self
        # The node passed in should be a MakoNode or a MakoLeaf at the same indentation level

        # Who is closing?
        if self is active_node:
            # I am the active node, so I am the unambiguous choice to be closed at this time
            return      

        potentially_closed = active_node.parent
        while potentially_closed is not None:

            #print 'Checking: %s' % potentially_closed
            if potentially_closed.depth == node.depth:
                # <potentially_closed> is definitely being closed by <node>, and all is well
                # Todo: Perform type checking to make sure MakoNodes only close against other MakoNodes
                return
            elif potentially_closed.depth < node.depth:
                # How am is <node> closing someone at a lower depth than it?
                raise NemoException('\nIncorrect indentation\n' + \
                                    'at:\n\t%s\n' % node + \
                                    'Tried to close against::\n\t%s\n' % self + \
                                    'Within active scope of:\n\t%s' % active_node )

            potentially_closed = potentially_closed.parent



class NemoRoot(NemoNode):
    """
        I represent the root element of a Nemo AST
        Ideally, there should only be one instance of around during parsing.
    """
    is_root = True

    def __init__(self):
        super(NemoRoot, self).__init__(('Nemo Root', None), -1, 0)

    def write(self, buffer):
        self._write_children(buffer)

    def _write_children(self, buffer):
        """
           Write child nodes onto the buffer.
           Tags within the root can occur on any depth you feel like.
           Todo: Check if this messes things up if your tags under the root are ambiguously aligned
        """

        children = self.check_open_close_on_mako_nodes(
                        self.children)

        for child in children:
            # Write the child
            child.write(buffer)        

class Leaf(Node):
    """
        I am a leaf, I cannot have children. If I do, then it is an error
    """
    follows_indentation_rules = False

    def write(self, buffer=None):
        buffer.write("\n")
        buffer.write(self.value)

    def add_child(self, node):
        # This should never be called
        raise NemoException('Parser error. Tried to add node:\n\t%s to leaf: \n\t%s' % (node, self))

class MakoEndTag(Leaf):
    """
    I represent a closign tag in Mako.
    I am a Leaf without children.
    """
    follows_indentation_rules = True
    pass

########NEW FILE########
__FILENAME__ = parser
import re

from mako.util import FastEncodingBuffer
from exceptions import NemoException
from pyparsing import (Word, Keyword, Literal, OneOrMore, Optional, \
                      restOfLine, alphas, ParseException, Empty, \
                      Forward, ZeroOrMore, Group, CharsNotIn, White, delimitedList, quotedString, alphanums, Combine  )
import pyparsing
from nodes import Node, NemoNode, NemoRoot, MakoNode, Leaf, MakoEndTag

from exceptions import NemoException

class Buffer(FastEncodingBuffer):
    def __init__(self, encoding=None, errors='strict', unicode=True):
        super(Buffer, self).__init__(encoding, errors, unicode)
        self.writelines = self.data.extend

class BaseParser(object):
    """
        I am a parser. There are many like me, but I am the first.
    """
    def __init__(self, debug=False):
        self.debug = debug

    def _init(self, raw):
        self._c = None
        self._last_c = None
        self._raw = raw

    def _next(self):
        self._last_c = self._c
        self._c = next(self._raw)

    def parse(self, source):
        self._init(iter(source))

    def buffer_value(self):
        return self.buffer.getvalue()


class NemoParser(BaseParser):
    """
        I parse every line in a multi-lined string given to me via parse()
        I return a transformed string where every Nemo expression has been converted to a valid Mako expression.
        Internally, I use nodes to define the AST as I understand it.
    """
    def parse(self, source):
        self.arg_parser = NemoArgumentParser()
        self._init(iter(source.splitlines()))

        # Base Node
        head = NemoRoot()
        self._line_number = 0
        self._current_node = head
        while True:
            try:
                self._next()
                self._line_number += 1
            except StopIteration:
                # out = StringIO()
                out = Buffer()
                head.write(out)
                return out.getvalue()

            self._parse_line()


    def _parse_line(self):
        """ Parses a single line, and returns a node representing the active context
            Further lines processed are expected to be children of the active context, or children of its accestors.

            ------------------------------------------------

            Basic grammar  is as follows:
            line = <mako>|<nemo>|<string>

            <mako>
            We don't parse normally parse tags, so the following info is sketchy.
            Mako tags are recognized as anythign that starts with:
                - <%
                - %>
                - %CLOSETEXT
                - </%

            Mako Control tags however are parsed, and required to adhere to the same indentation rules as Nemo tags.

            mako_control = <start>|<middle>|<end>
            start = (for|if|while)  <inner>:
            middle = (else|elif):
            end = endfor|endwhile

            nemo = % ( <mako_control>|<nemo_statement> )
            nemo_statement = .<quote><string><quote>|#<quote><string><quote>|<words>

            <quote> = '|"
                Notes: Quotes are required to be balanced.
                       Quotes preceded by a \ are ignored.
            <string> = *
            words = \w+
        """
        #if self.debug: print '\t ' +  str(self._current_node)

        # PyParser setParseAction's actually execute during parsing,
        # So we need closures in order to change the current scope

        
        def depth_from_indentation(function):
            """ Set the depth as the start of the match """
            def wrap(start, values):
                #print 'Depth %d | %d %s' %(self._depth, start, values)
                #self._depth = start
                self._current_node = function(values)
                #print self._current_node
                return ''

            return wrap
        
        def depth_from_match(function):
            """ Set the depth as the start of the match """
            def wrap(start, values):
                #print 'Depth %d | %d %s' %(self._depth, start, values)
                #print self._current_node
                self._depth = start
                self._current_node = function(values)
                #print self._current_node
                return ''

            return wrap        

        def depth_from_nemo_tag(function):
            """ Start of the match is where the nemo tag is. Pass the other values to the wrapped function """
            def wrap(start, values):
                # print 'Depth %d | %d %s' %(self._depth, start, values)
                self._depth = start
                tokens = values[1]
                self._current_node = function(tokens)
                #print self._current_node
                return ''

            return wrap



        # Match HTML
        from pyparsing import NotAny, MatchFirst
        html = restOfLine
        html.setParseAction(depth_from_indentation(self._add_html_node))

        # Match Mako control tags
        nemo_tag    = Literal('%')

        begin       = Keyword('for')    | Keyword('if')     | Keyword('while')
        middle      = Keyword('else')   | Keyword('elif')
        end         = Keyword('endfor') | Keyword('endif')  | Keyword('endwhile')
        control     = nemo_tag + (begin | middle | end)

        begin.setParseAction(depth_from_indentation(self._add_nesting_mako_control_node) )
        middle.setParseAction(depth_from_indentation(self._add_mako_middle_node))
        end.setParseAction(depth_from_indentation(self._add_mako_control_leaf))

        # Match Nemo tags
        argument_name = Word(alphas,alphanums+"_-:")
        argument_value = quotedString
        regular_argument = argument_name + Literal('=') + argument_value

        class_name = Literal('.').setParseAction(lambda x: 'class=')
        id_name = Literal('#').setParseAction(lambda x: 'id=')
        special_argument = (class_name | id_name) + argument_value
        argument = Combine(special_argument) | Combine(regular_argument)

        # Match single Nemo statement (Part of a multi-line)
        inline_nemo_html   = Word(alphas) + Group(ZeroOrMore(argument))
        inline_nemo_html.setParseAction(depth_from_match(self._add_nemo_node))

        # Match first nemo tag on the line (the one that may begin a multi-statement expression)        
        nemo_html = nemo_tag + Group(Word(alphanums+"_-:") + Group(ZeroOrMore(argument)))
        nemo_html.setParseAction(depth_from_nemo_tag(self._add_nemo_node))

        # Match a multi-statement expression. Nemo statements are seperated by |. Anything after || is treated as html
        separator   = Literal('|').suppress()
        html_separator   = Literal('||') # | Literal('|>')
        nemo_list =  nemo_html + ZeroOrMore( separator + inline_nemo_html )
        inline_html = html.copy()
        inline_html.setParseAction(depth_from_match(self._add_inline_html_node))
        nemo_multi =  nemo_list + Optional(html_separator + inline_html)

        # Match empty Nemo statement
        empty       = nemo_tag + Empty()
        empty.setParseAction(depth_from_indentation(self._add_blank_nemo_node))

        # Match unused Mako tags
        mako_tags   = Literal('<%') | Literal('%>') | Literal('%CLOSETEXT') | Literal('</%')
        mako        = mako_tags
        mako_tags.setParseAction(depth_from_indentation(self._add_html_node))

        # Matches General
        nemo        =  (control | nemo_multi | empty)
        line        =   mako_tags | nemo | html

        # Depth Calculation (deprecated?)
        self._depth = len(self._c) - len(self._c.strip())

        #try:
        line.parseString(self._c)

        #except ParseException:
            # Finally if we couldn't match, then handle it as HTML
            #add_html_node(self._c)

    """
        This group of functions transforms the AST.
        They are expected to return the active node
    """
    def _add_to_tree(self, node, active_node):
        if node.depth > active_node.depth:
            active_node.add_child(node)
        else:
            self._place_in_ancestor(node, active_node)

        return node            

    def _add_control_leaf_to_tree(self, node, active_node):
        if node.depth > active_node.depth:
            active_node.add_child(node)
            return active_node

            # The following check is disabled
            # --------

            # Leafs cannot appear on a higher indentation point than the active node
            # That would be ambiguous
            #raise NemoException('\nIncorrect indentation\n' + \
            #                    'at:\n\t%s\n' % active_node + \
            #                    'Followed by:\n\t%s\n' % node + \
            #                    'Parent:\n\t%s' % active_node.parent )
        else:
            """Try to assign node to one of the ancestors of active_node"""
            testing_node = active_node

            while testing_node is not None:
                # Close against the first element in the tree that is inline with you
                if testing_node.depth == node.depth:
                    # We are trying to close against the root element
                    if not testing_node.parent:
                        raise NemoException('\nIncorrect indentation\n' + \
                                    'at:\n\t%s\n' % node + \
                                    'attempted to close against:\n\t%s' % testing_node )
                    else:
                        parent = testing_node.parent
                        parent.add_child(node)

                        # Todo: Remove this check
                        testing_node.check_as_closer(node, active_node)
                        
                        return testing_node.parent
                elif testing_node.depth < node.depth:
                    raise NemoException('\nIncorrect indentation\n' + \
                                'at:\n\t%s\n' % node + \
                                'attempted to close against:\n\t%s' % testing_node )
                testing_node = testing_node.parent
            else:
                # This should never be reached because NemoRoot has a depth of -1
                raise NemoException('\nIncorrect indentation\n' + \
                                    'at:\n\t%s\n' % active_node + \
                                    'Followed by:\n\t%s\n' % node + \
                                    'Parent:\n\t%s' % parent )
            #result = self._place_in_ancestor(node, active_node)
            #result.check_as_closer(node, active_node)
            #return result

    def _add_html_to_tree(self, node, active_node):
        is_blank = not node.value or node.value.isspace()
        deeper_indented = node.depth > active_node.depth

        if is_blank or deeper_indented:
            active_node.add_child(node)
            
            return active_node
        else:
            return self._place_in_ancestor(node, active_node)


    def _place_in_ancestor(self, node, active_node):
        """Try to assign node to one of the ancestors of active_node"""
        parent = active_node
        while parent is not None:
            if parent.depth < node.depth:
                parent.add_child(node)
                
                return parent

            parent = parent.parent
        else:
            # This should never be reached because NemoRoot has a depth of -1
            raise NemoException('\nIncorrect indentation\n' + \
                                'at:\n\t%s\n' % active_node + \
                                'Followed by:\n\t%s\n' % node + \
                                'Parent:\n\t%s' % parent )

    """
        This group of functions transforms the AST.
        They correspond to the type of node currently being parsed.
        They are expected to return a node if the current scope changes.
    """

    def _add_html_node(self, tokens):
        if self.debug: print "%s | html %s " % (self._line_number, self._c)
        # This isn't a mako expression
        # So if it is on the same indentation level or greater as the active scope, then add it as a child of that.
        # Otherwise we'll close scope and add it
        leaf = Leaf(self._c, self._depth, self._line_number)
        return self._add_html_to_tree(leaf, self._current_node)

    def _add_inline_html_node(self, tokens):
        html = tokens[0]
        if self.debug: print "%s | html %s " % (self._line_number, html)
        # This isn't a mako expression
        # So if it is on the same indentation level or greater as the active scope, then add it as a child of that.
        # Otherwise we'll close scope and add it
        leaf = Leaf(html, self._depth, self._line_number)
        return self._add_html_to_tree(leaf, self._current_node)


    def _add_blank_nemo_node(self, tokens):
        if self.debug: print '%s | blank' % self._line_number
        # This a blank line. Treat it as an end tag or ignore it if it appears under the root
        if not self._current_node.is_root:
            self._current_node = self._current_node.parent

        return self._current_node

    def _add_nemo_node(self, tokens):
        keyword = tokens[0]
        arguments = u' '.join(tokens[1])

        if self.debug:
            print "%s | nemo %s " % (self._line_number, self._c),
            print "\t[ Parsing: %s %s ]" %(keyword, arguments)

        node = NemoNode( (keyword, arguments), self._depth, self._line_number)
        
        return self._add_to_tree(node, self._current_node)

    def _add_nesting_mako_control_node(self, tokens):
        if self.debug: print "%s | start %s " % (self._line_number, self._c)
        node = MakoNode(self._c, self._depth, self._line_number)

        return self._add_to_tree(node, self._current_node)

    def _add_mako_middle_node(self, tokens):
        if self.debug: print "%s | middle %s " % (self._line_number, self._c)
        node = MakoNode(self._c, self._depth, self._line_number)

        return self._add_to_tree(node, self._current_node)

    def _add_mako_control_leaf(self, tokens):
        if self.debug: print "%s | end %s " % (self._line_number, self._c)
        if not self._current_node.is_root:
            self._current_node = self._current_node.parent

        node = MakoEndTag(self._c, self._depth, self._line_number)

        return self._add_control_leaf_to_tree(node, self._current_node)


class NemoArgumentParser(BaseParser):
    """
        Parse arguments on the same line as a nemo expression and return as string containing their converted form.
        E.g.
            % div .'hello' #'world' href="/dev/null"
            Will be sent to this parser as: .'hello' #'world' href="/dev/null"
            Then the parser will return: class='hello' id='world' href="/dev/null"

        Aside from converting . to class, and # to id, the parser also checks that quotations are balanced and that
        arguments are given in a proper form.
    """
    def _slurp_till(self, end_delimiters):
        """ Read until a given delimiter is found in a string iterator.
        Keeps white space, and ignores the end_delimiter if it is preceded by \
        Return a string
        """
        cc = None
        if type(end_delimiters) in [str, unicode]:
            end_delimiters = [end_delimiters]

        while True:
            try:
                self._next()
            except StopIteration:
                raise NemoException('Expected delimiter %s but EOL found instead' % end_delimiters)

            self.buffer.write(self._c)

            for end in end_delimiters:
                if self._c == end and self._last_c != '\\':
                    return

    def parse(self, source):
        self.buffer = Buffer()
        self._init(raw=iter(source))
        quotes = ['\'', '"']
        expect = None

        while True:
            try:
                self._next()
            except StopIteration:
                break

            if expect is None:
                # Match class token (.) or id token (#)
                if self._c == ' ':
                    self.buffer.write(self._c)
                elif self._c == '.':
                    expect = quotes
                    self.buffer.write('class=')
                elif self._c == '#':
                    expect = quotes
                    self.buffer.write('id=')
                else:
                    # Slurp up attribute name til we see a quote
                    self.buffer.write(self._c)
                    self._slurp_till(quotes)

                    # Slurp up attribute value till we see another of the same quote
                    delimiter_found = self._c
                    self._slurp_till(delimiter_found)
            else:
                if self._c not in expect:
                    raise NemoException('Expected one of: %s but received %s' % (expect, c))
                if expect is quotes:
                    delimiter_found = self._c

                    # Write quote to buffer, then slurp up til the next quote
                    self.buffer.write(delimiter_found)
                    arg = self._slurp_till(delimiter_found)

                    # We have a keyword/arg combination complete so go back to expecting nothing
                    expect = None

        return self.buffer.getvalue()

def nemo(a_string):
    """ Hook for Mako pre-processing """
    return NemoParser().parse(a_string)
########NEW FILE########
__FILENAME__ = nemo_benchmark
import sys
import timeit
from nemo.parser import NemoParser
from mako.template import Template

if len(sys.argv) > 1:
    filename = sys.argv[1]
else:
    print 'A filename is required'
    exit()

def nemo(str, debug=False):
    NemoParser(debug=debug).parse(str)
    # Return Nothing so mako won't render a result
    return ''

def nemo_render(str, debug=False):
    return NemoParser(debug=debug).parse(str)


mako_temp = Template(filename=filename,
            input_encoding='utf-8',
            output_encoding='utf-8',)

nemo_temp = Template(filename=filename,
            preprocessor=nemo,
            input_encoding='utf-8',
            output_encoding='utf-8',)

nemo_temp_render = Template(filename=filename,
            preprocessor=nemo_render,
            input_encoding='utf-8',
            output_encoding='utf-8',)

number = 10000
t_mako = timeit.Timer('mako_temp.render()', 'from __main__ import mako_temp')
t_nemo = timeit.Timer('nemo_temp.render()', 'from __main__ import nemo_temp')
t_nemo_render = timeit.Timer('nemo_temp_render.render()', 'from __main__ import nemo_temp_render')
mako_time = t_mako.timeit(number=number) / number
nemo_time = t_nemo.timeit(number=number) / number
nemo_time_render = t_nemo_render.timeit(number=number) / number

print 'Mako (full render w/o nemo): %.2f ms' % (1000 * mako_time)
print 'Nemo (w/o mako render): %.2f ms' % (1000 * nemo_time)
print 'Nemo (w/ mako render): %.2f ms' % (1000 * nemo_time_render)

########NEW FILE########
__FILENAME__ = nemo_test
import sys
from nemo.parser import NemoParser
from mako.template import Template

if len(sys.argv) > 1:
    filename = sys.argv[1]
else:
    print 'A filename is required'
    exit()

def nemo(str, debug=False):
    if debug: print "[Debug]---------  %s --------------[Debug]\n" % filename

    result = NemoParser(debug=debug).parse(str)

    if debug: print "\n[Debug]---------  Result --------------[Debug]"
    print result

    # Return Nothing so mako won't render a result
    return ''


t = Template(filename=filename,
            preprocessor=nemo,
            input_encoding='utf-8',
            output_encoding='utf-8',)
print t.render()





########NEW FILE########
