__FILENAME__ = run

import os

import haml
import mako.lookup

# Build the template lookup.
lookup = mako.lookup.TemplateLookup([os.path.dirname(__file__)],
    preprocessor=haml.preprocessor
)

# Retrieve a template.
template = lookup.get_template('page.haml')
print template.render_unicode()
########NEW FILE########
__FILENAME__ = main

from mako.template import Template
import haml
import haml.codegen


source = '''

-!
    def upper(x):
        return x.upper()

- value = 'hello'

%p
    ${upper(value)}

:sass
    body
        margin: 0
    p
        color: #fff

'''


print '===== SOURCE ====='
print source.strip()
print

root = haml.parse_string(source)



print '===== NODES ====='
root.print_tree()
print

print '===== MAKO ====='
compiled = haml.generate_mako(root)
print compiled.strip()
print

template = Template(compiled)
if True:
    print '===== COMPILED MAKO ====='
    print template._code.strip()
    print

print '===== RENDERED ====='
print template.render_unicode(class_='test', title="MyPage", a='A', b='B', c='C').strip()
print

########NEW FILE########
__FILENAME__ = readme_tut
import haml
import mako.template

# 1. Write your HAML.
haml_source = '.content Hello, World!'

# 2. Parse your HAML source into a node tree.
haml_nodes = haml.parse_string(haml_source)

# 3. Generate Mako template source from the node tree.
mako_source = haml.generate_mako(haml_nodes)

# 4. Render the template.
print mako.template.Template(mako_source).render_unicode()
########NEW FILE########
__FILENAME__ = codegen
from itertools import chain
import cgi
import collections
import re

from six import string_types
from six.moves import xrange

from . import runtime


class GeneratorSentinal(object):
    
    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)
        
    def __repr__(self):
        if hasattr(self, 'name'):
            return '<Sentinal:%s>' % self.name
        return '<Sentinal at 0x%x>' % id(self)


class Generator(object):
    
    class no_strip(str):
        """A string class that will not have space removed."""
        def __repr__(self):
            return 'no_strip(%s)' % str.__repr__(self)
    
    indent_str = '\t'
    endl = '\n'
    endl_no_break = '\\\n'

    inc_depth = GeneratorSentinal(delta=1, name='inc_depth')
    dec_depth = GeneratorSentinal(delta=-1, name='dec_depth')
    _increment_tokens = (inc_depth, dec_depth)

    line_continuation = no_strip('\\\n')
    lstrip = GeneratorSentinal(name='lstrip')
    rstrip = GeneratorSentinal(name='rstrip')

    def generate(self, node):
        return ''.join(self.generate_iter(node))

    def generate_iter(self, node):
        buffer = []
        r_stripping = False
        self.depth = 0
        self.node_data = {}
        for token in node.render(self):
            if isinstance(token, GeneratorSentinal):
                if token in self._increment_tokens:
                    self.depth += token.delta
                elif token is self.lstrip:
                    # Work backwards through the buffer rstripping until
                    # we hit some non-white content. Then flush everything
                    # in the buffer upto that point. We need to leave the
                    # last one incase we get a "line_continuation" command.
                    # Remember that no_strip strings are simply ignored.
                    for i in xrange(len(buffer) - 1, -1, -1):
                        if isinstance(buffer[i], self.no_strip):
                            continue
                        buffer[i] = buffer[i].rstrip()
                        if buffer[i]:
                            for x in buffer[:i]:
                                yield x
                            buffer = buffer[i:]
                            break
                elif token is self.rstrip:
                    r_stripping = True
                else:
                    raise ValueError('unexpected %r' % token)
            elif isinstance(token, string_types):
                # If we have encountered an rstrip token in the past, then
                # we are removing all leading whitespace on incoming tokens.
                # We must completely ignore no_strip strings as they go by.
                if r_stripping:
                    if not isinstance(token, self.no_strip):
                        token = token.lstrip()
                        if token:
                            r_stripping = False
                if token:
                    # Flush the buffer if we have non-white content as no
                    # lstrip command will get past this new token anyways.
                    if buffer and token.strip() and not isinstance(token, self.no_strip):
                        for x in buffer:
                            yield x
                        buffer = [token]
                    else:
                        buffer.append(token)
            else:
                raise ValueError('unknown token %r' % token)
        for x in buffer:
            yield x

    def indent(self, delta=0):
        return self.indent_str * (self.depth + delta)

    def start_document(self):
        return (
            '<%%! from %s import runtime as __HAML %%>' % __package__ +
            self.endl_no_break
        )







    


def generate_mako(node):
    return Generator().generate(node)

########NEW FILE########
__FILENAME__ = filters
import subprocess
import cgi


def plain(src):
    return src


def escaped(src):
    return cgi.escape(src)


def cdata(src, comment=False):
    # This should only apply if the runtime is in XML mode.
    block_open  = ('/*' if comment else '') + '<![CDATA[' + ('*/' if comment else '')
    block_close = ('/*' if comment else '') + ']]>'       + ('*/' if comment else '')
    # This close/reopen is only going to work with xhtml.
    return block_open + (src.replace(']]>', ']]]]><![CDATA[>')) + block_close


def javascript(src):
    return '<script>%s</script>' % cdata(src, True)


def css(src):
    return '<style>%s</style>' % cdata(src, True)


def sass(src, scss=False):
    args = ['sass', '--style', 'compressed']
    if scss:
        args.append('--scss')
    proc = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    out, err = proc.communicate(src.encode('utf-8'))
    if out:
        out = css(out.rstrip().decode('utf-8'))
    if err:
        out += '<div class="sass-error">%s</div>' % cgi.escape(err.decode('utf-8'))
    return out


def scss(src):
    return sass(src, scss=True)


def coffeescript(src):
    args = ['coffee', '--compile', '--stdio']
    proc = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    out, err = proc.communicate(src.encode('utf-8'))
    if out:
        out = javascript(out)
    if err:
        out += '<div class="coffeescript-error">%s</div>' % cgi.escape(err)
    return out.decode('utf-8')



########NEW FILE########
__FILENAME__ = nodes
from __future__ import print_function

from itertools import chain
import cgi
import re

from . import codegen
from . import runtime


class Base(object):

    def __init__(self):
        self.inline_child = None
        self.children = []

    def iter_all_children(self):
        '''Return an iterator that yields every node which is a child of this one.

        This includes inline children, and control structure `else` clauses.
        '''
        
        if self.inline_child:
            yield self.inline_child
        for x in self.children:
            yield x

    def add_child(self, node, inline=False):
        if inline:
            self.inline_child = node
        else:
            self.children.append(node)
    
    def consume_sibling(self, node):
        return False

    def render(self, engine):
        return chain(
            self.render_start(engine),
            self.render_content(engine),
            self.render_end(engine),
        )

    def render_start(self, engine):
        return []

    def render_content(self, engine):
        to_chain = []
        if self.inline_child:
            to_chain.append(self.inline_child.render(engine))
        for child in self.children:
            to_chain.append(child.render(engine))
        return chain(*to_chain)

    def render_end(self, engine):
        return []

    def __repr__(self):
        return '<%s at 0x%x>' % (self.__class__.__name__, id(self))

    def print_tree(self, _depth=0, _inline=False):
        if _inline:
            print('-> ' + repr(self), end='')
        else:
            print('|   ' * _depth + repr(self), end='')
        _depth += int(not _inline)
        if self.inline_child:
            self.inline_child.print_tree(_depth, True)
        else:
            print()
        for child in self.children:
            child.print_tree(_depth)


class FilterBase(Base):

    def __init__(self, *args, **kwargs):
        super(FilterBase, self).__init__(*args, **kwargs)
        self._content = []

    def add_line(self, indent, content):
        self._content.append((indent, content))

    def iter_dedented(self):
        indent_to_remove = None
        for indent, content in self._content:
            if indent_to_remove is None:
                yield content
                if content:
                    indent_to_remove = len(indent)
            else:
                yield (indent + content)[indent_to_remove:]


class GreedyBase(Base):
    
    def __init__(self, *args, **kwargs):
        super(GreedyBase, self).__init__(*args, **kwargs)
        self._greedy_root = self

    def add_child(self, child, *args):
        super(GreedyBase, self).add_child(child, *args)
        child._greedy_root = self._greedy_root


class Document(Base):

    def render_start(self, engine):
        yield engine.start_document()


class Content(Base):

    def __init__(self, content):
        super(Content, self).__init__()
        self.content = content

    def render_start(self, engine):
        yield engine.indent()
        yield self.content
        yield engine.endl
        yield engine.inc_depth

    def render_end(self, engine):
        yield engine.dec_depth

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.content)


class Expression(Content, GreedyBase):

    def __init__(self, content, filters=''):
        super(Expression, self).__init__(content)
        self.filters = filters

    def render_start(self, engine):
        if self.content.strip():
            yield engine.indent()
            filters = self._greedy_root.filters
            yield '${%s%s}' % (self.content.strip(), ('|' + filters if filters else ''))
            yield engine.endl
        yield engine.inc_depth # This is countered by the Content.render_end

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.content, self.filters)



class Tag(Base):

    self_closing_names = set('''
        br
        hr
        img
        input
        link
        meta
    '''.strip().split())

    def __init__(self, name, id, class_,
            kwargs_expr=None,
            object_reference=None,
            object_reference_prefix=None,
            self_closing=False,
            strip_inner=False,
            strip_outer=False,
        ):

        super(Tag, self).__init__()

        self.name = (name or 'div').lower()
        self.id = id
        self.class_ = (class_ or '').replace('.', ' ').strip()
        self.kwargs_expr = kwargs_expr
        self.object_reference = object_reference
        self.object_reference_prefix = object_reference_prefix
        self.self_closing = self_closing
        self.strip_inner = strip_inner
        self.strip_outer = strip_outer

    def render_start(self, engine):

        const_attrs = {}
        if self.id:
            const_attrs['id'] = self.id
        if self.class_:
            const_attrs['class'] = self.class_

        kwargs_expr = self.kwargs_expr or ''

        # Object references are actually handled by the attribute formatting
        # function.
        if self.object_reference:
            kwargs_expr += (', ' if kwargs_expr else '') + '__obj_ref=' + self.object_reference
            if self.object_reference_prefix:
                kwargs_expr += ', __obj_ref_pre=' + self.object_reference_prefix

        # Mako tags should not convert camel case.
        if self.name.startswith('%'):
            const_attrs['__adapt_camelcase'] = False

        if kwargs_expr:
            try:
                # HACK: If we can evaluate the expression without error then
                # we don't need to do it at runtime. This is possibly quite
                # dangerous. We are trying to protect ourselves but I can't
                # guarantee it.
                kwargs_code = compile('__update__(%s)' % kwargs_expr, '<kwargs_expr>', 'eval')
                sandbox = __builtins__.copy()
                sandbox.pop('__import__', None)
                sandbox.pop('eval', None)
                sandbox.pop('execfile', None)
                def const_attrs_update(*args, **kwargs):
                    for arg in args:
                        const_attrs.update(arg)
                    const_attrs.update(kwargs)
                sandbox['__update__'] = const_attrs_update
                eval(kwargs_code, sandbox)
            except (NameError, ValueError, KeyError) as e:
                pass
            else:
                kwargs_expr = None

        if not kwargs_expr:
            attr_str = runtime.attribute_str(const_attrs)
        elif not const_attrs:
            attr_str = '<%% __M_writer(__HAML.attribute_str(%s)) %%>' % kwargs_expr
        else:
            attr_str = '<%% __M_writer(__HAML.attribute_str(%r, %s)) %%>' % (const_attrs, kwargs_expr)

        if self.strip_outer:
            yield engine.lstrip
        yield engine.indent()

        if self.self_closing or self.name in self.self_closing_names:
            yield '<%s%s />' % (self.name, attr_str)
            if self.strip_outer:
                yield engine.rstrip
            else:
                yield engine.endl
        else:
            yield '<%s%s>' % (self.name, attr_str)
            if self.children:
                if self.strip_inner or self.inline_child:
                    yield engine.rstrip
                else:
                    yield engine.endl
                    yield engine.inc_depth

    def render_content(self, engine):
        if self.inline_child:
            return chain(
                [engine.lstrip, engine.rstrip],
                super(Tag, self).render_content(engine),
                [engine.lstrip, engine.rstrip],
            )
        else:
            return super(Tag, self).render_content(engine)

    def render_end(self, engine):
        if self.strip_inner or self.inline_child:
            yield engine.lstrip
        if not (self.self_closing or self.name in self.self_closing_names):
            if self.children:
                yield engine.dec_depth
                yield engine.indent()
            yield '</%s>' % self.name
            if self.strip_outer:
                yield engine.rstrip
            yield engine.endl
        elif self.strip_outer:
            yield engine.rstrip

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
            ', '.join('%s=%r' % (k, getattr(self, k)) for k in (
                'name', 'id', 'class_', 'kwargs_expr',
                'strip_inner', 'strip_outer'
            ) if getattr(self, k))
        )

class MixinDef(Tag):

    def __init__(self, name, argspec):
        super(MixinDef, self).__init__(
            '%def', # tag name
            None, # ID
            None, # class
            'name=%r' % ('%s(%s)' % (name, argspec or '')), # kwargs expr
            strip_inner=True,
        )


class MixinCall(Tag):

    def __init__(self, name, argspec):
        super(MixinCall, self).__init__(
            '%call', # tag name
            None, # ID
            None, # class
            'expr=%r' % ('%s(%s)' % (name, argspec or '')), # kwargs expr
        )


class HTMLComment(Base):

    def __init__(self, inline_content, IE_condition=''):
        super(HTMLComment, self).__init__()
        self.inline_content = inline_content
        self.IE_condition = IE_condition

    def render_start(self, engine):
        yield engine.indent()
        yield '<!--'
        if self.IE_condition:
            yield self.IE_condition
            yield '>'
        if self.inline_content:
            yield ' '
            yield self.inline_content
            yield ' '
        if self.children:
            yield engine.inc_depth
            yield engine.endl

    def render_end(self, engine):
        if self.children:
            yield engine.dec_depth
            yield engine.indent()
        if self.IE_condition:
            yield '<![endif]'
        yield '-->'
        yield engine.endl

    def __repr__(self):
        return '%s()' % self.__class__.__name__


class Control(Base):

    def __init__(self, type, test):
        super(Control, self).__init__()
        self.type = type
        self.test = test
        self.elifs = []
        self.else_ = None

    def iter_all_children(self):
        for x in super(Control, self).iter_all_children():
            yield x
        for x in self.elifs:
            yield x
        if self.else_:
            yield x

    def consume_sibling(self, node):
        if not isinstance(node, Control):
            return False
        if node.type == 'elif':
            self.elifs.append(node)
            return True
        if node.type == 'else' and self.else_ is None:
            self.else_ = node
            return True
    
    def print_tree(self, depth, inline=False):
        super(Control, self).print_tree(depth)
        for node in self.elifs:
            node.print_tree(depth)
        if self.else_ is not None:
            self.else_.print_tree(depth)
            
    def render(self, engine):
        to_chain = [self.render_start(engine), self.render_content(engine)]
        for node in self.elifs:
            to_chain.append(node.render(engine))
        if self.else_:
            to_chain.append(self.else_.render(engine))
        to_chain.append(self.render_end(engine))
        return chain(*to_chain)
        
    def render_start(self, engine):
        yield engine.line_continuation
        yield engine.indent(-1)
        if self.test is not None:
            yield '%% %s %s: ' % (self.type, self.test)
        else:
            yield '%% %s: ' % (self.type)
        yield engine.no_strip(engine.endl)

    def render_end(self, engine):
        if self.type in ('else', 'elif'):
            return
        yield engine.line_continuation
        yield engine.indent(-1)
        yield '%% end%s' % self.type
        yield engine.no_strip(engine.endl)

    def __repr__(self):
        if self.test is not None:
            return '%s(type=%r, test=%r)' % (
                self.__class__.__name__,
                self.type,
                self.test
            )
        else:
            return '%s(type=%r)' % (self.__class__.__name__, self.type)


class Python(FilterBase):

    def __init__(self, content, module=False):
        super(Python, self).__init__()
        if content.strip():
            self.add_line('', content)
        self.module = module

    def render(self, engine):
        if self.module:
            yield '<%! '
        else:
            yield '<% '
        yield engine.endl
        for line in self.iter_dedented():
            yield line
            yield engine.endl
        yield '%>'
        yield engine.endl_no_break
    
    def __repr__(self):
        return '%s(%r%s)' % (
            self.__class__.__name__,
            self._content,
            ', module=True' if self.module else ''
        )


class Filter(FilterBase):

    def __init__(self, content, filter):
        super(Filter, self).__init__()
        if content and content.strip():
            self.add_line('', content)
        self.filter = filter

    def _escape_expressions(self, source):
        parts = re.split(r'(\${.*?})', source)
        for i in range(0, len(parts), 2):
            parts[i] = parts[i] and ('<%%text>%s</%%text>' % parts[i])
        return ''.join(parts)

    def render(self, engine):
        # Hopefully this chain respects proper scope resolution.
        yield '<%%block filter="locals().get(%r) or globals().get(%r) or getattr(__HAML.filters, %r, UNDEFINED)">' % (self.filter, self.filter, self.filter)
        yield engine.endl_no_break
        yield self._escape_expressions(engine.endl.join(self.iter_dedented()).strip())
        yield '</%block>'
        yield engine.endl

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self._content,
                self.filter)


class HAMLComment(Base):

    def __init__(self, comment):
        super(HAMLComment, self).__init__()
        self.comment = comment

    def __repr__(self):
        return '%s(%r)' % (
            self.__class__.__name__,
            self.comment
        )

    def render(self, engine):
        return []


class Doctype(Base):
    doctypes = {
        'xml': {
            None: """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">""",
            "strict": """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">""",
            "frameset": """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">""",
            "5": """<!DOCTYPE html>""",
            "1.1": """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">""",
            "basic": """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML Basic 1.1//EN" "http://www.w3.org/TR/xhtml-basic/xhtml-basic11.dtd">""",
            "mobile": """<!DOCTYPE html PUBLIC "-//WAPFORUM//DTD XHTML Mobile 1.2//EN" "http://www.openmobilealliance.org/tech/DTD/xhtml-mobile12.dtd">""",
            "rdfa": """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML+RDFa 1.0//EN" "http://www.w3.org/MarkUp/DTD/xhtml-rdfa-1.dtd">""",
        }, 'html': {
            None: """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">""",
            "strict": """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">""",
            "frameset": """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">""",
            "5": """<!DOCTYPE html>""",
    }}

    def __init__(self, name=None, charset=None):
        super(Doctype, self).__init__()
        self.name = name.lower() if name else None
        self.charset = charset

    def __repr__(self):
        return '%s(%r, %r)' % (
            self.__class__.__name__,
            self.name,
            self.charset
        )

    def render_start(self, engine):
        if self.name in ('xml', 'html'):
            mode = self.name
            engine.node_data['Doctype.mode'] = mode
        else:
            mode = engine.node_data.get('Doctype.mode', 'html')
        if self.name == 'xml':
            charset = self.charset or 'utf-8'
            yield "<?xml version='1.0' encoding='%s' ?>" % charset
            yield engine.no_strip('\n')
            return
        yield self.doctypes[mode][self.name]
        yield engine.no_strip('\n')

########NEW FILE########
__FILENAME__ = parse
import re

from six import string_types, next

from . import nodes


def split_balanced_parens(line, depth=0):
    # Too bad I can't do this with a regex... *sigh*.
    deltas = {'(': 1, ')': -1}
    pos = None
    for pos, char in enumerate(line):
        depth += deltas.get(char, 0)
        if not depth:
            break
    if pos: # This could be either None or 0 if it wasn't a brace.
        return line[:pos+1], line[pos+1:]
    else:           
        return '', line
    
    
class Parser(object):

    def __init__(self):
        self.root = nodes.Document()
        self._stack = [((-1, 0), self.root)]
        self._peek_line_buffer = None

    def parse_string(self, source):
        self.parse(source.splitlines())

    @property
    def _topmost_node(self):
        return self._stack[-1][1]

    def _next_line(self):
        """Get the next line."""
        if self._peek_line_buffer is not None:
            line = self._peek_line_buffer
            self._peek_line_buffer = None
            return line
        return next(self.source)

    def _peek_line(self):
        """Get the next line without consuming it."""
        if self._peek_line_buffer is None:
            self._peek_line_buffer = next(self.source)
        return self._peek_line_buffer

    def parse(self, source):
        self._parse_lines(source)
        self._parse_context(self.root)
    
    def _parse_lines(self, source):
        self.source = iter(source)
        indent_str = ''
        while True:
            try:
                raw_line = self._next_line()
            except StopIteration:
                break

            # Handle multiline statements.
            try:
                while raw_line.endswith('|'):
                    raw_line = raw_line[:-1]
                    if self._peek_line().endswith('|'):
                        raw_line += self._next_line()
            except StopIteration:
                pass

            line = raw_line.lstrip()
            
            if line:
                
                # We track the inter-line depth seperate from the intra-line depth
                # so that indentation due to whitespace always results in more
                # depth in the graph than many nested nodes from a single line.
                inter_depth = len(raw_line) - len(line)
                intra_depth = 0

                indent_str = raw_line[:inter_depth]
                
                # Cleanup the stack. We should only need to do this here as the
                # depth only goes up until it is calculated from the next line.
                self._prep_stack_for_depth((inter_depth, intra_depth))
                
            else:
                
                # Pretend that a blank line is at the same depth as the
                # previous.
                inter_depth, intra_depth = self._stack[-1][0]
            
            # Filter(Base) nodes recieve all content in their scope.
            if isinstance(self._topmost_node, nodes.FilterBase):
                self._topmost_node.add_line(indent_str, line)
                continue
            
            # Greedy nodes recieve all content in their scope.
            if isinstance(self._topmost_node, nodes.GreedyBase):
                self._add_node(
                    self._topmost_node.__class__(line),
                    (inter_depth, intra_depth)
                )
                continue
            
            # Discard all empty lines that are not in a greedy context.
            if not line:
                continue
            
            # Main loop. We process a series of tokens, which consist of either
            # nodes to add to the stack, or strings to be re-parsed and
            # attached as inline.
            last_line = None
            while line and line != last_line:
                last_line = line
                for token in self._parse_line(line):
                    if isinstance(token, nodes.Base):
                        self._add_node(token, (inter_depth, intra_depth))
                    elif isinstance(token, string_types):
                        line = token
                        intra_depth += 1
                    else:
                        raise TypeError('unknown token %r' % token)

    def _parse_line(self, line):

        # Escaping.
        if line.startswith('\\'):
            yield nodes.Content(line[1:].lstrip())
            return

        # HTML comments.
        m = re.match(r'/(\[if[^\]]+])?(.*)$', line)
        if m:
            yield nodes.HTMLComment(m.group(2).strip(), (m.group(1) or '').rstrip())
            return

        # Expressions.
        m = re.match(r'''
            (&?)                  # HTML escaping flag
            =
            (?:\|(\w+(?:,\w+)*))? # mako filters
            \s*
            (.*)                  # expression content
            $
        ''', line, re.X)
        if m:
            add_escape, filters, content = m.groups()
            filters = filters or ''
            if add_escape:
                filters = filters + (',' if filters else '') + 'h'
            yield nodes.Expression(content, filters)
            return

        # SASS Mixins
        m = re.match(r'@(\w+)', line)
        if m:
            name = m.group(1)
            line = line[m.end():]
            argspec, line = split_balanced_parens(line)
            if argspec:
                argspec = argspec[1:-1]
            yield nodes.MixinDef(name, argspec)
            yield line.lstrip()
            return
        m = re.match(r'\+([\w.]+)', line)
        if m:
            name = m.group(1)
            line = line[m.end():]
            argspec, line = split_balanced_parens(line)
            if argspec:
                argspec = argspec[1:-1]
            yield nodes.MixinCall(name, argspec)
            yield line.lstrip()
            return

        # HAML Filters.
        m = re.match(r':(\w+)(?:\s+(.+))?$', line)
        if m:
            filter, content = m.groups()
            yield nodes.Filter(content, filter)
            return

        # HAML comments
        if line.startswith('-#'):
            yield nodes.HAMLComment(line[2:].lstrip())
            return  
        
        # XML Doctype
        if line.startswith('!!!'):
            yield nodes.Doctype(*line[3:].strip().split())
            return

        # Tags.
        m = re.match(r'''
            (?:%(%?(?:\w+:)?[\w-]*))? # tag name. the extra % is for mako
            (?:
              \[(.+?)(?:,(.+?))?\]    # object reference and prefix
            )? 
            (                         
              (?:\#[\w-]+|\.[\w-]+)+  # id/class
            )?
        ''', line, re.X)                                
        # The match only counts if we have a tag name or id/class.
        if m and (m.group(1) is not None or m.group(4)):
            name, object_reference, object_reference_prefix, raw_id_class = m.groups()
            
            # Extract id value and class list.
            id, class_ = None, []
            for m2 in re.finditer(r'(#|\.)([\w-]+)', raw_id_class or ''):
                type, value = m2.groups()
                if type == '#':
                    id = value
                else:
                    class_.append(value)
            line = line[m.end():]

            # Extract the kwargs expression.
            kwargs_expr, line = split_balanced_parens(line)
            if kwargs_expr:
                kwargs_expr = kwargs_expr[1:-1]

            # Whitespace stripping
            m2 = re.match(r'([<>]+)', line)
            strip_outer = strip_inner = False
            if m2:
                strip_outer = '>' in m2.group(1)
                strip_inner = '<' in m2.group(1)
                line = line[m2.end():]

            # Self closing tags
            self_closing = bool(line and line[0] == '/')
            line = line[int(self_closing):].lstrip()

            yield nodes.Tag(
                name=name,
                id=id,
                class_=' '.join(class_),
                
                kwargs_expr=kwargs_expr,
                object_reference=object_reference,
                object_reference_prefix=object_reference_prefix, 
                self_closing=self_closing,
                strip_inner=strip_inner,
                strip_outer=strip_outer,
            )
            yield line
            return

        # Control statements.
        m = re.match(r'''
            -
            \s*
            (for|if|while|elif) # control type
            \s+
            (.+?):         # test
        ''', line, re.X)
        if m:
            yield nodes.Control(*m.groups())
            yield line[m.end():].lstrip()
            return
        m = re.match(r'-\s*else\s*:', line, re.X)
        if m:
            yield nodes.Control('else', None)
            yield line[m.end():].lstrip()
            return
        
        # Python source.
        if line.startswith('-'):
            if line.startswith('-!'):
                yield nodes.Python(line[2:].lstrip(), module=True)
            else:
                yield nodes.Python(line[1:].lstrip(), module=False)
            return

        # Content
        yield nodes.Content(line)

    def _prep_stack_for_depth(self, depth):  
        """Pop everything off the stack that is not shorter than the given depth."""
        while depth <= self._stack[-1][0]:
            self._stack.pop()

    def _add_node(self, node, depth):
        """Add a node to the graph, and the stack."""
        self._topmost_node.add_child(node, bool(depth[1]))
        self._stack.append((depth, node))
    
    def _parse_context(self, node):
        for child in node.iter_all_children():
            self._parse_context(child)
        i = 0
        while i < len(node.children) - 1:
            if node.children[i].consume_sibling(node.children[i + 1]):
                del node.children[i + 1]
            else:
                i += 1


def parse_string(source):
    """Parse a string into a HAML node to be compiled."""
    parser = Parser()
    parser.parse_string(source)
    return parser.root

########NEW FILE########
__FILENAME__ = runtime
import re
import cgi

from six import string_types, iteritems

from . import filters

_attr_sort_order = {
    'id': -3,
    'class': -2,
    'http-equiv': -1, # for meta
    'checked': 1,
    'selected': 1,
}


_camelcase_re = re.compile(r'(?<!^)([A-Z])([A-Z]*)')
def adapt_camelcase(name, seperator):
    return _camelcase_re.sub(lambda m: seperator + m.group(0), name).lower()


def _format_mako_attr_pair(k, v):
    if v is True:
        v = k
    return ' %s="%s"' % (k, cgi.escape("%s" % v).replace('"', '&quot;'))


def flatten_attr_list(input):
    if not input:
        return
    if isinstance(input, string_types):
        yield input
        return
    try:
        input = iter(input)
    except TypeError:
        yield input
        return
    for element in input:
        if element:
            for sub_element in flatten_attr_list(element):
                yield sub_element


def flatten_attr_dict(prefix_key, input):
    if not isinstance(input, dict):
        yield prefix_key, input
        return
    for key, value in iteritems(input):
        yield prefix_key + '-' + key, value


def attribute_str(*args, **kwargs):
    x = {}
    for arg in args:
        x.update(arg)
    x.update(kwargs)
    obj_ref = x.pop('__obj_ref', None)
    obj_ref_prefix = x.pop('__obj_ref_pre', None)
    if x.pop('__adapt_camelcase', True):
        x = dict((adapt_camelcase(k, '-'), v) for k, v in iteritems(x))
    x['id'] = flatten_attr_list(
        x.pop('id', [])
    )
    x['class'] = list(flatten_attr_list(
        [x.pop('class', []), x.pop('class_', [])]
    ))
    if obj_ref:
        class_name = adapt_camelcase(obj_ref.__class__.__name__, '_')
        x['id'] = filter(None, [obj_ref_prefix, class_name, getattr(obj_ref, 'id', None)])
        x['class'].append((obj_ref_prefix + '_' if obj_ref_prefix else '') + class_name)
    x['id'] = '_'.join(map(str, x['id']))
    x['class'] = ' '.join(map(str, x['class']))
    pairs = []
    for k, v in iteritems(x):
        pairs.extend(flatten_attr_dict(k, v))
    pairs.sort(key=lambda pair: (_attr_sort_order.get(pair[0], 0), pair[0]))
    return ''.join(_format_mako_attr_pair(k, v) for k, v in pairs if v)



########NEW FILE########
__FILENAME__ = util


def extract_haml(fileobj, keywords, comment_tags, options):
    """ babel translation token extract function for haml files """

    import haml
    from mako import lexer, parsetree
    from mako.ext.babelplugin import extract_nodes 

    encoding = options.get('input_encoding', options.get('encoding', None))
    template_node = lexer.Lexer(haml.preprocessor(fileobj.read()), input_encoding=encoding).parse()
    for extracted in extract_nodes(template_node.get_children(), keywords, comment_tags, options):
        yield extracted


########NEW FILE########
__FILENAME__ = parse_flexible_args
import re
import ast
import operator

def parse_args(input, end=')'):
    chunks = re.split(r'(,|%s)' % re.escape(end), input)
    output = []
    
    # Continue processing chunks as long as we keep getting something.
    last_output = -1
    while len(output) != last_output:
        last_output = len(output)
        
        # Extract kwarg name.
        m = re.match(r'\s*(?::?([\w-]+)\s*=>?|(\*{1,2}))', chunks[0])
        if m:
            name = m.group(1) or m.group(2)
            chunks[0] = chunks[0][m.end():]
        else:
            name = None
    
        # Keep finding chunks until it compiles:
        for i in xrange(1, len(chunks), 2):
            source = ''.join(chunks[:i]).lstrip()
            try:
                parsed = ast.parse(source, mode='eval')
            except SyntaxError as e:
                continue
            
            output.append((name, source, parsed))
            next_delim = chunks[i]                
            chunks = chunks[i + 1:]
            break
        
        else:
            break
        
        if next_delim == end:
            break
        
    return output, ''.join(chunks)




def literal_eval(node_or_string):
    """
    Safely evaluate an expression node or a string containing a Python
    expression.  The string or node provided may only consist of the following
    Python literal structures: strings, numbers, tuples, lists, dicts, booleans,
    and None.
    """
    _safe_names = {
        'None': None,
        'True': True,
        'False': False,
        'dict': dict,
        'list': list,
        'sorted': sorted
    }
    
    if isinstance(node_or_string, basestring):
        node_or_string = parse(node_or_string, mode='eval')
        
    if isinstance(node_or_string, ast.Expression):
        node_or_string = node_or_string.body
        
    def _convert(node):
        
        if isinstance(node, ast.Str):
            return node.s
        
        elif isinstance(node, ast.Num):
            return node.n
        
        elif isinstance(node, ast.Tuple):
            return tuple(map(_convert, node.elts))
        
        elif isinstance(node, ast.List):
            return list(map(_convert, node.elts))
        
        elif isinstance(node, ast.Dict):
            return dict((_convert(k), _convert(v)) for k, v
                        in zip(node.keys, node.values))
        
        elif isinstance(node, ast.Name):
            if node.id in _safe_names:
                return _safe_names[node.id]
        
        elif isinstance(node, ast.BinOp):
            left = _convert(node.left)
            right = _convert(node.right)
            op = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.div,
                ast.Mod: operator.mod
            }.get(type(node.op), None)
            if op:
                return op(left, right)
        
        elif isinstance(node, ast.Call):
            func = _convert(node.func)
            args = map(_convert, node.args)
            kwargs = dict((kw.arg, _convert(kw.value)) for kw in node.keywords)
            if node.starargs:
                args.extend(_convert(node.starargs))
            if node.kwargs:
                kwargs.update(_convert(node.kwargs))
            return func(*args, **kwargs)
        
        elif isinstance(node, ast.Attribute):
            if not node.attr.startswith('_'):
                return getattr(_convert(node.value), node.attr)
        
        raise ValueError('malformed string: %r' % node)
    return _convert(node_or_string)


if __name__ == '__main__':
    
    signatures = '''

(1, 2, 3) more
(key='value') more
(**dict(key='value')) more
(*[1, 2, 3]) more
{:class => "code", :id => "message"} Hello
(class_='before %s after' % 'middle') hello
(data-crud=dict(id=34, url='/api')) crud goes here
(u'unicode!', b'bytes!')
(' '.join(['hello', 'there'])) after
([i for i in 'hello'])

'''.strip().splitlines()
    for sig in signatures:
        print sig
        args, remaining = parse_args(sig[1:], {'(':')', '{':'}'}[sig[0]])
        
    
        for key, source, root in args:
            try:
                value = literal_eval(root)
                print '%s: %r' % (key, value)
            except ValueError as e:
                print '%s -> %s' % (key, e)
        
        print repr(remaining), 'remains'
        print
        

########NEW FILE########
__FILENAME__ = base
from unittest import TestCase, main
import os

from mako.template import Template
import haml


def skip(func):
    def test(*args, **kwargs):
        from nose.exc import SkipTest
        raise SkipTest()
    return test


def skip_on_travis(func):
    if os.environ.get('TRAVIS') == 'true':
        def test(*args, **kwargs):
            from nose.exc import SkipTest
            raise SkipTest()
        return test
    else:
        return func


class Base(TestCase):
    
    def assertMako(self, source, expected, *args):
        node = haml.parse_string(source)
        mako = haml.generate_mako(node).replace('<%! from haml import runtime as __HAML %>\\\n', '')
        self.assertEqual(
            mako.replace('    ', '\t'),
            expected.replace('    ', '\t'),
            *args
        )
        
    def assertHTML(self, source, expected, *args, **kwargs):
        node = haml.parse_string(source)
        mako = haml.generate_mako(node)
        html = Template(mako).render_unicode(**kwargs)
        self.assertEqual(
            html.replace('    ', '\t'),
            expected.replace('    ', '\t'),
            *args
        )

########NEW FILE########
__FILENAME__ = test_conformance
# encoding: utf8

from unittest import main

from six import u

from base import Base, skip, skip_on_travis

from haml.runtime import flatten_attr_list


class TestFlattenAttr(Base):
    
    def test_basic_string(self):
        self.assertEqual(list(flatten_attr_list(
            'string'
        )), [
            'string'
        ])
    def test_basic_list(self):
        self.assertEqual(list(flatten_attr_list(
            ['a', 'b']
        )), [
            'a',
            'b'
        ])
    def test_basic_mixed(self):
        self.assertEqual(list(flatten_attr_list(
            ['a', 'b', None, ['c', ['d', None, 'e']]]
        )), [
            'a', 'b', 'c', 'd', 'e'
        ])
        

class TestHamlTutorial(Base):
    
    """Testing all of the examples from http://haml-lang.com/tutorial.html"""
    
    def test_1(self):
        self.assertMako(
            '%strong= item.title',
            '<strong>${item.title}</strong>\n'
        )
    
    def test_2(self):
        self.assertHTML(
            '%strong(class_="code", id="message") Hello, World!',
            '<strong id="message" class="code">Hello, World!</strong>\n'
        )

    def test_2b(self):
        self.assertHTML(
            '%strong.code#message Hello, World!',
            '<strong id="message" class="code">Hello, World!</strong>\n'
        )
            
    def test_3(self):
        self.assertHTML(
            '.content Hello, World!',
            '<div class="content">Hello, World!</div>\n'
        )

    def test_4(self):
        class obj(object):
            pass
        item = obj()
        item.id = 123
        item.body = 'Hello, World!'
        self.assertHTML(
            '.item(id="item-%d" % item.id)= item.body',
            '<div id="item-123" class="item">Hello, World!</div>\n',
            item=item
        )

    def test_5(self):
        self.assertHTML(
            '''
#content
  .left.column
    %h2 Welcome to our site!
    %p Info.
  .right.column
    Right content.
            '''.strip(),
            '''
<div id="content">
    <div class="left column">
        <h2>Welcome to our site!</h2>
        <p>Info.</p>
    </div>
    <div class="right column">
        Right content.
    </div>
</div>
            '''.strip() + '\n')


class TestHamlReference(Base):
    
    def test_plain_text_escaping(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#escaping_"""
        self.assertHTML(
            '''
%title
  = title
  \= title
            '''.strip(),
            '''
<title>
    MyPage
    = title
</title>
            '''.strip() + '\n', title='MyPage')

    def test_element_name(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#element_name_"""
        self.assertHTML(
            '''
%one
  %two
    %three Hey there
            '''.strip(),
            '''
<one>
    <two>
        <three>Hey there</three>
    </two>
</one>
            '''.strip() + '\n')

    def test_self_closing_tags(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#selfclosing_tags_"""
        self.assertHTML(
            '''
%br/
%meta(**{'http-equiv': 'Content-Type', 'content': 'text/html'})/
            '''.strip(),
            '''
<br />
<meta http-equiv="Content-Type" content="text/html" />
            '''.strip() + '\n')
        self.assertHTML(
            '''
%br
%meta(**{'http-equiv': 'Content-Type', 'content': 'text/html'})
            '''.strip(),
            '''
<br />
<meta http-equiv="Content-Type" content="text/html" />
            '''.strip() + '\n')

    def test_whitespace_removal_1(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#whitespace_removal__and_"""
        self.assertHTML(
            '''
%blockquote<
    %div
        Foo!
            '''.strip(),
            '''
<blockquote><div>
    Foo!
</div></blockquote>
            '''.strip() + '\n')

    def test_whitespace_removal_2(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#whitespace_removal__and_"""
        self.assertHTML(
            '''
%img
%img>
%img
            '''.strip(),
            '''
<img /><img /><img />
            '''.strip() + '\n')

#     def test_whitespace_removal_3(self):
#         """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#whitespace_removal__and_"""
#         self.assertHTML(
#             '''
# %p<= "Foo\nBar"
#             '''.strip(),
#             '''
# <p>Foo
# Bar</p>
#             '''.strip() + '\n')

    def test_whitespace_removal_4(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#whitespace_removal__and_"""
        self.assertHTML(
            '''
%img
%pre><
    foo
    bar
%img
            '''.strip(),
            '''
<img /><pre>foo
bar</pre><img />
            '''.strip() + '\n')

    def test_html_comments_1(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#html_comments_"""
        self.assertHTML(
            '''
%peanutbutterjelly
  / This is the peanutbutterjelly element
  I like sandwiches!
            '''.strip(),
            '''
<peanutbutterjelly>
    <!-- This is the peanutbutterjelly element -->
    I like sandwiches!
</peanutbutterjelly>
            '''.strip() + '\n')
            
    def test_html_comments_2(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#html_comments_"""
        self.assertHTML(
            '''
/
  %p This doesn't render...
  %div
    %h1 Because it's commented out!
            '''.strip(),
            '''
<!--
    <p>This doesn't render...</p>
    <div>
        <h1>Because it's commented out!</h1>
    </div>
-->
            '''.strip() + '\n')
    
    def test_html_conditional_comments(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#html_comments_"""
        self.assertHTML(
            '''
/[if IE]
  %a(href='http://www.mozilla.com/en-US/firefox/')
    %h1 Get Firefox
            '''.strip(),
            '''
<!--[if IE]>
    <a href="http://www.mozilla.com/en-US/firefox/">
        <h1>Get Firefox</h1>
    </a>
<![endif]-->
            '''.strip() + '\n')    
    
    def test_silent_comments(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#haml_comments_"""
        self.assertHTML(
            '''
%p foo
-# This is a comment
%p bar
            '''.strip(),
            '''
<p>foo</p>
<p>bar</p>
            '''.strip() + '\n')

    def test_silent_comments_2(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#haml_comments_"""
        self.assertHTML(
            '''
%p foo
-#
  This won't be displayed
    Nor will this
%p bar
            '''.strip(),
            '''
<p>foo</p>
<p>bar</p>
            '''.strip() + '\n')    

    def test_multiline(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#multiline"""
        self.assertHTML(
            '''
%whoo
  %hoo=                          |
    "I think this might get " +  |
    "pretty long so I should " + |
    "probably make it " +        |
    "multiline so it doesn't " + |
    "look awful."                |
  %p This is short.
            '''.strip(),
            '''
<whoo>
    <hoo>I think this might get pretty long so I should probably make it multiline so it doesn't look awful.</hoo>
    <p>This is short.</p>
</whoo>
            '''.strip() + '\n')   
            
    def test_escaping_html(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#escaping_html"""
        self.assertHTML('&= "I like cheese & crackers"', 'I like cheese &amp; crackers\n')
    
    def test_escaping_attr(self):
        self.assertHTML('%(key="""value "with" quotes""")', '<div key="value &quot;with&quot; quotes"></div>\n')
    
    def test_filters(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#multiline
        
        We don't implement any of the speced filters.
        
        """
        self.assertHTML(
            '''
A
-!
    def noop(x):
        return x
    value = 123
B
:noop
    The syntaxes! They do nothing!!!
    #id
    .class
    - statement
    / comment
    ${value}
C
            '''.strip(),
            '''
A
B
The syntaxes! They do nothing!!!
#id
.class
- statement
/ comment
123
C
            '''.strip() + '\n') 
            
    def test_data_attr(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#html5_custom_data_attributes"""
        self.assertHTML('%a(href="/posts", data={"author_id": 123}) Posts By Author', '<a data-author_id="123" href="/posts">Posts By Author</a>\n')              
    
    
    def test_object_reference(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#object_reference_"""
        self.assertHTML(
            '''
-! class ModelName(object):
    id = 123
- model = ModelName()
%div[model] contents
            '''.strip(),
            '''
<div id="model_name_123" class="model_name">contents</div>
            '''.strip() + '\n') 

    def test_object_reference_prefix(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#object_reference_"""
        self.assertHTML(
            '''
-! class ModelName(object):
    id = 123
- model = ModelName()
%div[model, 'prefix'] contents
            '''.strip(),
            '''
<div id="prefix_model_name_123" class="prefix_model_name">contents</div>
            '''.strip() + '\n')   

    def test_boolean_attribtues(self):
        """See: http://haml-lang.com/docs/yardoc/file.HAML_REFERENCE.html#boolean_attributes"""
        self.assertHTML("%(type='checkbox', checked=True)", '<div type="checkbox" checked="checked"></div>\n')              


class TestControlStructures(Base):

    def test_else_if(self):
        self.assertHTML(
'''
- if False:
    A
- else:
    B
''', 'B\n')

    def test_elif(self):
        self.assertHTML(
'''
- if False:
    A
- elif False:
    B
- elif True:
    C
- else:
    D
''', 'C\n')


    def test_for_else(self):
        self.assertHTML(
'''
- for i in range(3): ${i}
- else:
    X
''', '0\n1\n2\nX\n')

    def test_for_else_break(self):
        self.assertHTML(
'''
- for i in range(3):
    ${i}
    - break
- else:
    X
''', '0\n')

    def test_for_if(self):
        self.assertHTML(
'''
- for i in range(4):
       - if i % 2 == 0:
               ${i} even
       - else:
               ${i} odd
''', '''
0 even
1 odd
2 even
3 odd
'''.lstrip())

    def test_after_for_if(self):
        self.assertHTML(
'''
% - for i in [0]:
    - if True:
        A
    - else:
        B
    C
''', '<div>A\nC\n</div>\n')

    def test_xslt(self):
        self.assertHTML(
'''
%xsl:template(match='/')
    %html
        %body
            %xsl:apply-templates/
''', '''
<xsl:template match="/">
	<html>
		<body>
			<xsl:apply-templates />
		</body>
	</html>
</xsl:template>
'''.lstrip())

    def test_sass(self):
        self.assertHTML(
'''
a
:sass
    body
        margin: 0
        padding: 0
    div
        p
            margin-top: 1em
b
''', '''
a
<style>/*<![CDATA[*/body{margin:0;padding:0}div p{margin-top:1em}/*]]>*/</style>
b
'''.lstrip())
    
    @skip
    def test_sass_unicode(self):
        self.assertHTML(
u('''
a
:sass
    #mydiv:before
        content: "☺"
b
'''), u('''
a
<style>/*<![CDATA[*/#mydiv:before{content:"☺"}/*]]>*/</style>
b
''').lstrip())


    def test_filter_scoping(self):
        self.assertHTML(
'''
:plain
    X
''',
'''
X
'''.lstrip())
        self.assertHTML(
'''
-! def plain(x): return 'A'

:plain
    X

''', '''
A
'''.lstrip())
        self.assertHTML(
'''
-! def plain(x): return 'A'
:plain
    - def plain(x): return 'B'
    X
''', '''
A
'''.lstrip())
    
    @skip
    def test_coffeescript_unicode(self):
        self.assertHTML(
u('''
:coffeescript
    alert '☺'
'''),
u('''
<script>/*<![CDATA[*/(function() {

  alert('☺');

}).call(this);
/*]]>*/</script>
''').lstrip())
        
                                        
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_mako

from unittest import main
from base import Base



class TestMakoFeatures(Base):
    
    def test_filters(self):
        self.assertHTML('=|h "before & after"', 'before &amp; after\n')

    def test_source_inline(self):
        self.assertHTML(
            '''
before
- i = 1
= i
after
            '''.strip(),
            '''
before
1
after
            '''.strip() + '\n')   

    def test_mod_source_inline(self):
        self.assertHTML(
            '''
before
= i
-! i = 1
after
            '''.strip(),
            '''
before
1
after
            '''.strip() + '\n')   

    def test_source(self):
        self.assertHTML(
            '''
before
-
    a = 1
    b = 2
    def go():
        return a + b
= go()
after
            '''.strip(),
            '''
before
3
after
            '''.strip() + '\n')   

    def test_mod_source(self):
        self.assertHTML(
            '''
before
= add(3, 4)
-!
    def add(a, b):
        return a + b

after
            '''.strip(),
            '''
before
7
after
            '''.strip() + '\n')

    def test_source_with_paml_commands(self):
        self.assertHTML(
            '''
before
-
    a = ('1' + """
    -
    """.strip() + """
    #id.class
    """.strip())
= a
after
            '''.strip(),
            '''
before
1-#id.class
after
            '''.strip() + '\n')   

    def test_expr_blocks(self):
        self.assertHTML(
            '''
= 'inline expr'
=
    'block expr 1'
    'block expr 2'
    a
        b
        c
            '''.strip(),
            '''
inline expr
    block expr 1
    block expr 2
    one
        two
        three
            '''.strip() + '\n',
        a='one', b='two', c='three')


    def test_expr_blocks_filters(self):
        self.assertHTML(
            '''
-! to_title = lambda x: x.title()
= 'inline expr'
=|to_title
    'block expr 1'
    'block expr 2'
    a
        b
        c
            '''.strip(),
            '''
inline expr
    Block Expr 1
    Block Expr 2
    One
        Two
        Three
            '''.strip() + '\n',
        a='one', b='two', c='three')  

    def test_empty_line_handling(self):
        self.assertHTML(
            '''
- content = """
    before
    
    after""".strip()
= content
            '''.strip(),
            '''
    before
    
    after
            '''.strip() + '\n') 

    def test_empty_line_handling_2(self):
        self.assertHTML(
            '''
- content = """
    before
    
        after""".strip()
= content
            '''.strip(),
            '''
    before
    
        after
            '''.strip() + '\n')

    def test_empty_line_handling_3(self):
        '''A blank line should not affect indentation level.'''
        self.assertHTML(
            '''
%a
    %b

        %c
            '''.strip(),
            '''
<a>
    <b>
        <c></c>
    </b>
</a>
            '''.strip() + '\n')


    def test_camelcase_in_mako_tag(self):
        self.assertHTML(
            '''

%%def(name="some_def(**attrs)")
  %dl - for k in sorted(attrs):
    %dt= k
    %dd= attrs[k]
  %p(**attrs)
 
%%self:some_def(camelCase='value')
    Body, which will be discarded.

            '''.strip(),
            '''

    <dl>    <dt>camelCase</dt>
    <dd>value</dd>
</dl>
    <p camel-case="value"></p>

''')

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_mixins
# -*- coding: utf-8 -*-
from unittest import main
from base import Base

class TestMixins(Base):

    
    def test_basic(self):
        self.assertHTML('''
@basic
    Content
%div
    +basic
'''.strip(),
'''
<div>
Content
</div>\n''')

    def test_parens(self):
        self.assertHTML('''
@basic(x)
    ${repr(x)}
%div
    +basic(dict(key='value'))
'''.strip(),
'''
<div>
{'key': 'value'}
</div>\n''')

    
    
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_pythonisms
# -*- coding: utf-8 -*-
from unittest import main
import sys

from six import u

from base import Base


class TestAttributes(Base):

    
    def test_raw_attribute_names(self):
        self.assertHTML(
            '%({"b-dash": "two"}, a="one", **{"c-dash": "three"}) content',
            '<div a="one" b-dash="two" c-dash="three">content</div>\n'
        )
    
    def test_camelcase_attributes(self):
        self.assertHTML(
            '%({"positionalDict":"xxx"}, keywordArgument="xxx", **{"expandedDict":"xxx"}) content',
            '<div expanded-dict="xxx" keyword-argument="xxx" positional-dict="xxx">content</div>\n'
        )
    
    def test_camelcase_override(self):
        self.assertHTML(
            '%({"positionalDict":"xxx"}, keywordArgument="xxx", __adapt_camelcase=False, **{"expandedDict":"xxx"}) content',
            '<div expandedDict="xxx" keywordArgument="xxx" positionalDict="xxx">content</div>\n'
        )

    def test_unicode_arguments(self):
        if sys.version_info > (3,):
            return
        self.assertHTML(
            u('%(a=u"España") content'),
            u('<div a="España">content</div>\n')
        )
    
if __name__ == "__main__":
    main()

########NEW FILE########
