__FILENAME__ = client-test
import sys
import jsonjinja
from jsonjinja.utils import get_runtime_javascript


env = jsonjinja.Environment(loader=jsonjinja.DictLoader({
    'layout.html': '''\
<!doctype html>
<title>{% block title %}{% endblock %}</title>
<div class=body>
{% block body %}{% endblock %}
</div>
''',
    'test.html': '''\
{% extends "layout.html" %}
{% block title %}{{ title }}{% endblock %}
{% block body %}
  <h1>Testing</h1>
  <ul>
  {% for item in seq %}
    <li>{{ loop.index }} - {{ item }} [{{ loop.cycle("odd", "even") }}]
  {% endfor %}
  </ul>
{% endblock %}
}))
'''}))


print '<!doctype html>'
print '<script type=text/javascript src=jquery.js></script>'
print '<script type=text/javascript>'
print get_runtime_javascript()
print 'jsonjinja.addTemplates('
env.compile_javascript_templates(stream=sys.stdout)
print ');'
print 'document.write(jsonjinja.getTemplate("test.html").render({seq: [1, 2, 3], title: "Foo"}));'
print '</script>'

########NEW FILE########
__FILENAME__ = config
from itertools import imap
from weakref import ref as weakref
from templatetk.config import Config as ConfigBase, Undefined


def grab_wire_object_details(obj):
    if isinstance(obj, dict) and '__jsonjinja_wire__' in obj:
        return obj['__jsonjinja_wire__']


class Config(ConfigBase):

    def __init__(self, environment):
        ConfigBase.__init__(self)
        self._environment = weakref(environment)
        self.forloop_parent_access = True

    @property
    def environment(self):
        return self._environment()

    def get_autoescape_default(self, name):
        return name.endswith(('.html', '.xml'))

    def mark_safe(self, value):
        return {'__jsonjinja_wire__': 'html-safe', 'value': value}

    def get_template(self, name):
        return self.environment.get_template(name)

    def yield_from_template(self, template, info, vars=None):
        return template.execute(vars or {}, info)

    def finalize(self, value, autoescape):
        if value is None or self.is_undefined(value):
            return u''
        elif isinstance(value, bool):
            return value and u'true' or u'false'
        elif isinstance(value, float):
            if int(value) == value:
                return unicode(int(value))
            return unicode(value)
        wod = grab_wire_object_details(value)
        if wod == 'html-safe':
            return value['value']
        if isinstance(value, (list, dict)):
            raise TypeError('Cannot print objects, tried to '
                            'print %r' % value)
        if autoescape:
            value = self.markup_type.escape(unicode(value))
        return unicode(value)

    def wrap_loop(self, iterator, parent=None):
        if isinstance(iterator, dict):
            iterator = iterator.items()
            iterator.sort()
        return ConfigBase.wrap_loop(self, iterator, parent)

    def concat(self, info, iterable):
        rv = u''.join(imap(info.finalize, iterable))
        if info.autoescape:
            rv = self.mark_safe(rv)
        return rv

    def getattr(self, obj, attribute):
        try:
            return obj[attribute]
        except (TypeError, LookupError):
            try:
                obj[int(attribute)]
            except ValueError:
                try:
                    return getattr(obj, str(attribute))
                except (UnicodeError, AttributeError):
                    pass
        return Undefined()

    getitem = getattr

########NEW FILE########
__FILENAME__ = environment
from cStringIO import StringIO
from jsonjinja.config import Config
from jsonjinja.lexer import Lexer
from jsonjinja.parser import Parser
from jsonjinja.utils import ensure_json_compatible
from templatetk.jscompiler import to_javascript
from templatetk.asttransform import to_ast
from templatetk.bcinterp import run_bytecode, RuntimeState, compile_ast
from templatetk.utils import json


class Template(object):

    def __init__(self, name, config, code):
        namespace = run_bytecode(code)
        self.config = config
        self.name = name
        self.filename = code.co_filename
        self.setup_func = namespace['setup']
        self.root_func = namespace['root']

    def execute(self, context, info=None):
        rtstate = RuntimeState(context, self.config, self.name, info)
        self.setup_func(rtstate)
        return self.root_func(rtstate)

    def render(self, *args, **kwargs):
        if not args:
            context = {}
        elif len(args) == 1:
            context = args[0]
            if isinstance(context, basestring):
                context = json.loads(context)
            elif hasattr(context, 'read'):
                context = json.load(context)
            else:
                context = dict(context)
        if kwargs:
            context.update(kwargs)
        if __debug__:
            ensure_json_compatible(context)
        return u''.join(self.execute(context))


class Environment(object):
    lexer = Lexer()
    template_class = Template

    def __init__(self, loader=None):
        self.config = Config(self)
        self.loader = loader
        self.filters = {}

    def compile_javascript_templates(self, filter_func=None, stream=None):
        write_out = False
        if stream is None:
            stream = StringIO()
            write_out = True
        stream.write('{')
        first = True
        for template_name in self.loader.list_templates():
            if filter_func is not None and not filter_func(template_name):
                continue
            if not first:
                stream.write(',')
            stream.write('%s:' % json.dumps(template_name))
            node = self.get_template_as_node(template_name)
            to_javascript(node, stream)
            first = False
        stream.write('}')
        if write_out:
            return stream.getvalue()

    def get_template_as_node(self, name):
        contents, filename, uptodate = self.loader.get_source(self, name)
        return self.parse(contents, name, filename)

    def get_template(self, name):
        return self.loader.load(self, name)

    def parse(self, source, name, filename=None):
        return Parser(self.config, source, name, filename).parse()

    def compile(self, source, name, filename=None):
        node = self.parse(source, name, filename)
        ast = to_ast(node)
        if filename is None:
            filename = '<string>'
        return compile_ast(ast, filename)

########NEW FILE########
__FILENAME__ = exceptions
class TemplateError(Exception):
    """Baseclass for all template errors."""

    def __init__(self, message=None):
        if message is not None:
            message = unicode(message).encode('utf-8')
        Exception.__init__(self, message)

    @property
    def message(self):
        if self.args:
            message = self.args[0]
            if message is not None:
                return message.decode('utf-8', 'replace')


class TemplateNotFound(IOError, LookupError, TemplateError):
    """Raised if a template does not exist."""

    # looks weird, but removes the warning descriptor that just
    # bogusly warns us about message being deprecated
    message = None

    def __init__(self, name, message=None):
        IOError.__init__(self)
        if message is None:
            message = name
        self.message = message
        self.name = name
        self.templates = [name]

    def __str__(self):
        return self.message.encode('utf-8')

    # unicode goes after __str__ because we configured 2to3 to rename
    # __unicode__ to __str__.  because the 2to3 tree is not designed to
    # remove nodes from it, we leave the above __str__ around and let
    # it override at runtime.
    def __unicode__(self):
        return self.message


class TemplatesNotFound(TemplateNotFound):
    """Like :class:`TemplateNotFound` but raised if multiple templates
    are selected.  This is a subclass of :class:`TemplateNotFound`
    exception, so just catching the base exception will catch both.
    """

    def __init__(self, names=(), message=None):
        if message is None:
            message = u'non of the templates given were found: ' + \
                      u', '.join(map(unicode, names))
        TemplateNotFound.__init__(self, names and names[-1] or None, message)
        self.templates = list(names)


class TemplateSyntaxError(TemplateError):
    """Raised to tell the user that there is a problem with the template."""

    def __init__(self, message, lineno, name=None, filename=None):
        TemplateError.__init__(self, message)
        self.lineno = lineno
        self.name = name
        self.filename = filename
        self.source = None

        # this is set to True if the debug.translate_syntax_error
        # function translated the syntax error into a new traceback
        self.translated = False

    def __str__(self):
        return unicode(self).encode('utf-8')

    # unicode goes after __str__ because we configured 2to3 to rename
    # __unicode__ to __str__.  because the 2to3 tree is not designed to
    # remove nodes from it, we leave the above __str__ around and let
    # it override at runtime.
    def __unicode__(self):
        # for translated errors we only return the message
        if self.translated:
            return self.message

        # otherwise attach some stuff
        location = 'line %d' % self.lineno
        name = self.filename or self.name
        if name:
            location = 'File "%s", %s' % (name, location)
        lines = [self.message, '  ' + location]

        # if the source is set, add the line to the output
        if self.source is not None:
            try:
                line = self.source.splitlines()[self.lineno - 1]
            except IndexError:
                line = None
            if line:
                lines.append('    ' + line.strip())

        return u'\n'.join(lines)


class TemplateAssertionError(TemplateSyntaxError):
    """Like a template syntax error, but covers cases where something in the
    template caused an error at compile time that wasn't necessarily caused
    by a syntax error.  However it's a direct subclass of
    :exc:`TemplateSyntaxError` and has the same attributes.
    """


class TemplateRuntimeError(TemplateError):
    """A generic runtime error in the template engine.  Under some situations
    Jinja may raise this exception.
    """


class UndefinedError(TemplateRuntimeError):
    """Raised if a template tries to operate on :class:`Undefined`."""


class FilterArgumentError(TemplateRuntimeError):
    """This error is raised if a filter was called with inappropriate
    arguments
    """


class NotJSONCompatibleException(TemplateRuntimeError, AssertionError):
    """Raised if a template context is not JSON compatible."""

########NEW FILE########
__FILENAME__ = lexer
import re
from operator import itemgetter
from collections import deque
from jsonjinja.exceptions import TemplateSyntaxError


whitespace_re = re.compile(r'\s+', re.U)
string_re = re.compile(r"('([^'\\]*(?:\\.[^'\\]*)*)'"
                       r'|"([^"\\]*(?:\\.[^"\\]*)*)")', re.S)
float_re = re.compile(r'[+-]?(?<!\.)\d+\.\d+')
integer_re = re.compile(r'[+-]?\d+')
name_re = re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b')

ignored_tokens = frozenset(['comment_begin', 'comment', 'comment_end',
                            'whitespace', 'whitespace'])
ignore_if_empty = frozenset(['whitespace', 'data', 'comment'])
newline_re = re.compile(r'(\r\n|\r|\n)')


operators = {
    '~':            'tilde',
    '==':           'eq',
    '!=':           'ne',
    '>':            'gt',
    '<':            'lt',
    '>=':           'ge',
    '<=':           'le',
    '|':            'pipe',
    ',':            'comma',
    ';':            'semicolon',
    '=':            'assign',
    ':':            'colon',
    '[':            'lbracket',
    ']':            'rbracket',
    '{':            'lbrace',
    '}':            'rbrace',
    '(':            'lparen',
    ')':            'rparen',
    '.':            'dot'
}

block_start_string = '{%'
block_end_string = '%}'
variable_start_string = '{{'
variable_end_string = '}}'
comment_start_string = '{#'
comment_end_string = '#}'


reverse_operators = dict([(v, k) for k, v in operators.iteritems()])
assert len(operators) == len(reverse_operators), 'operators dropped'
operator_re = re.compile('(%s)' % '|'.join(re.escape(x) for x in
                         sorted(operators, key=lambda x: -len(x))))


def _describe_token_type(token_type):
    if token_type in reverse_operators:
        return reverse_operators[token_type]
    return {
        'comment_begin':        'begin of comment',
        'comment_end':          'end of comment',
        'comment':              'comment',
        'block_begin':          'begin of statement block',
        'block_end':            'end of statement block',
        'variable_begin':       'begin of print statement',
        'variable_end':         'end of print statement',
        'data':                 'template data / text',
        'eof':                  'end of template'
    }.get(token_type, token_type)


def describe_token(token):
    """Returns a description of the token."""
    if token.type == 'name':
        return token.value
    return _describe_token_type(token.type)


def describe_token_expr(expr):
    """Like `describe_token` but for token expressions."""
    if ':' in expr:
        type, value = expr.split(':', 1)
        if type == 'name':
            return value
    else:
        type = expr
    return _describe_token_type(type)


def count_newlines(value):
    """Count the number of newline characters in the string.  This is
    useful for extensions that filter a stream.
    """
    return len(newline_re.findall(value))


class Failure(object):
    """Class that raises a `TemplateSyntaxError` if called.
    Used by the `Lexer` to specify known errors.
    """

    def __init__(self, message, cls=TemplateSyntaxError):
        self.message = message
        self.error_class = cls

    def __call__(self, lineno, filename):
        raise self.error_class(self.message, lineno, filename)


def compile_root_rules():
    e = re.escape
    rules = [
        (len(comment_start_string), 'comment', e(comment_start_string)),
        (len(block_start_string), 'block', e(block_start_string)),
        (len(variable_start_string), 'variable', e(variable_start_string))
    ]
    return [x[1:] for x in sorted(rules, reverse=True)]


class Token(tuple):
    """Token class."""
    __slots__ = ()
    lineno, type, value = (property(itemgetter(x)) for x in range(3))

    def __new__(cls, lineno, type, value):
        return tuple.__new__(cls, (lineno, intern(str(type)), value))

    def __str__(self):
        if self.type in reverse_operators:
            return reverse_operators[self.type]
        elif self.type == 'name':
            return self.value
        return self.type

    def test(self, expr):
        """Test a token against a token expression.  This can either be a
        token type or ``'token_type:token_value'``.  This can only test
        against string values and types.
        """
        # here we do a regular string equality check as test_any is usually
        # passed an iterable of not interned strings.
        if self.type == expr:
            return True
        elif ':' in expr:
            return expr.split(':', 1) == [self.type, self.value]
        return False

    def test_any(self, *iterable):
        """Test against multiple token expressions."""
        for expr in iterable:
            if self.test(expr):
                return True
        return False

    def __repr__(self):
        return 'Token(%r, %r, %r)' % (
            self.lineno,
            self.type,
            self.value
        )


class TokenStreamIterator(object):
    """The iterator for tokenstreams.  Iterate over the stream
    until the eof token is reached.
    """

    def __init__(self, stream):
        self.stream = stream

    def __iter__(self):
        return self

    def next(self):
        token = self.stream.current
        if token.type == 'eof':
            self.stream.close()
            raise StopIteration()
        self.self.stream.next()
        return token


class TokenStream(object):
    """A token stream is an iterable that yields :class:`Token`\s.  The
    parser however does not iterate over it but calls :meth:`next` to go
    one token ahead.  The current active token is stored as :attr:`current`.
    """

    def __init__(self, generator, name, filename):
        self._next = iter(generator).next
        self._pushed = deque()
        self.name = name
        self.filename = filename
        self.closed = False
        self.current = Token(1, 'initial', '')
        self.next()

    def __iter__(self):
        return TokenStreamIterator(self)

    def __nonzero__(self):
        return bool(self._pushed) or self.current.type != 'eof'

    eos = property(lambda x: not x, doc="Are we at the end of the stream?")

    def push(self, token):
        """Push a token back to the stream."""
        self._pushed.append(token)

    def look(self):
        """Look at the next token."""
        old_token = self.next()
        result = self.current
        self.push(result)
        self.current = old_token
        return result

    def skip(self, n=1):
        """Got n tokens ahead."""
        for x in xrange(n):
            self.next()

    def next_if(self, expr):
        """Perform the token test and return the token if it matched.
        Otherwise the return value is `None`.
        """
        if self.current.test(expr):
            return self.next()

    def skip_if(self, expr):
        """Like :meth:`next_if` but only returns `True` or `False`."""
        return self.next_if(expr) is not None

    def next(self):
        """Go one token ahead and return the old one"""
        rv = self.current
        if self._pushed:
            self.current = self._pushed.popleft()
        elif self.current.type != 'eof':
            try:
                self.current = self._next()
            except StopIteration:
                self.close()
        return rv

    def close(self):
        """Close the stream."""
        self.current = Token(self.current.lineno, 'eof', '')
        self._next = None
        self.closed = True

    def expect(self, expr):
        """Expect a given token type and return it.  This accepts the same
        argument as :meth:`jinja2.lexer.Token.test`.
        """
        if not self.current.test(expr):
            expr = describe_token_expr(expr)
            if self.current.type != 'eof':
                raise TemplateSyntaxError('unexpected end of template, '
                                          'expected %r.' % expr,
                                          self.current.lineno,
                                          self.name, self.filename)
            raise TemplateSyntaxError("expected token %r, got %r" %
                                      (expr, describe_token(self.current)),
                                      self.current.lineno,
                                      self.name, self.filename)
        try:
            return self.current
        finally:
            self.next()


class Lexer(object):

    def __init__(self):
        c = lambda x: re.compile(x, re.M | re.S)
        e = re.escape
        tag_rules = [
            (whitespace_re, 'whitespace', None),
            (float_re, 'float', None),
            (integer_re, 'integer', None),
            (name_re, 'name', None),
            (string_re, 'string', None),
            (operator_re, 'operator', None)
        ]
        root_tag_rules = compile_root_rules()

        self.rules = {
            'root': [
                # directives
                (c('(.*?)(?:%s)' % '|'.join(
                    [r'(?P<raw_begin>(?:\s*%s\-|%s)\s*raw\s*(?:\-%s\s*|%s))' % (
                        e(block_start_string),
                        e(block_start_string),
                        e(block_end_string),
                        e(block_end_string)
                    )] + [
                        r'(?P<%s_begin>\s*%s\-|%s)' % (n, r, r)
                        for n, r in root_tag_rules
                    ])), ('data', '#bygroup'), '#bygroup'),
                # data
                (c('.+'), 'data', None)
            ],
            # comments
            'comment_begin': [
                (c(r'(.*?)(\-%s\s*|%s)' % (
                    e(comment_end_string),
                    e(comment_end_string)
                )), ('comment', 'comment_end'), '#pop'),
                (c('(.)'), (Failure('Missing end of comment tag'),), None)
            ],
            # blocks
            'block_begin': [
                (c('(?:\-%s\s*|%s)' % (
                    e(block_end_string),
                    e(block_end_string)
                )), 'block_end', '#pop'),
            ] + tag_rules,
            # variables
            'variable_begin': [
                (c('\-%s\s*|%s' % (
                    e(variable_end_string),
                    e(variable_end_string)
                )), 'variable_end', '#pop')
            ] + tag_rules,
            # raw block
            'raw_begin': [
                (c('(.*?)((?:\s*%s\-|%s)\s*endraw\s*(?:\-%s\s*|%s))' % (
                    e(block_start_string),
                    e(block_start_string),
                    e(block_end_string),
                    e(block_end_string)
                )), ('data', 'raw_end'), '#pop'),
                (c('(.)'), (Failure('Missing end of raw directive'),), None)
            ]
        }
        self.newline_sequence = '\n'

    def _normalize_newlines(self, value):
        """Called for strings and template data to normalize it to unicode."""
        return newline_re.sub(self.newline_sequence, value)

    def tokenize(self, source, name=None, filename=None, state=None):
        """Calls tokeniter + tokenize and wraps it in a token stream.
        """
        stream = self.tokeniter(source, name, filename, state)
        return TokenStream(self.wrap(stream, name, filename), name, filename)

    def wrap(self, stream, name=None, filename=None):
        """This is called with the stream as returned by `tokenize` and wraps
        every token in a :class:`Token` and converts the value.
        """
        for lineno, token, value in stream:
            if token in ignored_tokens:
                continue
            # we are not interested in those tokens in the parser
            elif token in ('raw_begin', 'raw_end'):
                continue
            elif token == 'data':
                value = self._normalize_newlines(value)
            elif token == 'keyword':
                token = value
            elif token == 'name':
                value = str(value)
            elif token == 'string':
                # try to unescape string
                try:
                    value = self._normalize_newlines(value[1:-1]) \
                        .encode('ascii', 'backslashreplace') \
                        .decode('unicode-escape')
                except Exception, e:
                    msg = str(e).split(':')[-1].strip()
                    raise TemplateSyntaxError(msg, lineno, name, filename)
                # if we can express it as bytestring (ascii only)
                # we do that for support of semi broken APIs
                # as datetime.datetime.strftime.  On python 3 this
                # call becomes a noop thanks to 2to3
                try:
                    value = str(value)
                except UnicodeError:
                    pass
            elif token == 'integer':
                value = int(value)
            elif token == 'float':
                value = float(value)
            elif token == 'operator':
                token = operators[value]
            yield Token(lineno, token, value)

    def tokeniter(self, source, name, filename=None, state=None):
        """This method tokenizes the text and returns the tokens in a
        generator.  Use this method if you just want to tokenize a template.
        """
        source = '\n'.join(unicode(source).splitlines())
        pos = 0
        lineno = 1
        stack = ['root']
        if state is not None and state != 'root':
            assert state in ('variable', 'block'), 'invalid state'
            stack.append(state + '_begin')
        else:
            state = 'root'
        statetokens = self.rules[stack[-1]]
        source_length = len(source)

        balancing_stack = []

        while 1:
            # tokenizer loop
            for regex, tokens, new_state in statetokens:
                m = regex.match(source, pos)
                # if no match we try again with the next rule
                if m is None:
                    continue

                # we only match blocks and variables if braces / parentheses
                # are balanced. continue parsing with the lower rule which
                # is the operator rule. do this only if the end tags look
                # like operators
                if balancing_stack and \
                   tokens in ('variable_end', 'block_end'):
                    continue

                # tuples support more options
                if isinstance(tokens, tuple):
                    for idx, token in enumerate(tokens):
                        # failure group
                        if token.__class__ is Failure:
                            raise token(lineno, filename)
                        # bygroup is a bit more complex, in that case we
                        # yield for the current token the first named
                        # group that matched
                        elif token == '#bygroup':
                            for key, value in m.groupdict().iteritems():
                                if value is not None:
                                    yield lineno, key, value
                                    lineno += value.count('\n')
                                    break
                            else:
                                raise RuntimeError('%r wanted to resolve '
                                                   'the token dynamically'
                                                   ' but no group matched'
                                                   % regex)
                        # normal group
                        else:
                            data = m.group(idx + 1)
                            if data or token not in ignore_if_empty:
                                yield lineno, token, data
                            lineno += data.count('\n')

                # strings as token just are yielded as it.
                else:
                    data = m.group()
                    # update brace/parentheses balance
                    if tokens == 'operator':
                        if data == '{':
                            balancing_stack.append('}')
                        elif data == '(':
                            balancing_stack.append(')')
                        elif data == '[':
                            balancing_stack.append(']')
                        elif data in ('}', ')', ']'):
                            if not balancing_stack:
                                raise TemplateSyntaxError('unexpected \'%s\'' %
                                                          data, lineno, name,
                                                          filename)
                            expected_op = balancing_stack.pop()
                            if expected_op != data:
                                raise TemplateSyntaxError('unexpected \'%s\', '
                                                          'expected \'%s\'' %
                                                          (data, expected_op),
                                                          lineno, name,
                                                          filename)
                    # yield items
                    if data or tokens not in ignore_if_empty:
                        yield lineno, tokens, data
                    lineno += data.count('\n')

                # fetch new position into new variable so that we can check
                # if there is a internal parsing error which would result
                # in an infinite loop
                pos2 = m.end()

                # handle state changes
                if new_state is not None:
                    # remove the uppermost state
                    if new_state == '#pop':
                        stack.pop()
                    # resolve the new state by group checking
                    elif new_state == '#bygroup':
                        for key, value in m.groupdict().iteritems():
                            if value is not None:
                                stack.append(key)
                                break
                        else:
                            raise RuntimeError('%r wanted to resolve the '
                                               'new state dynamically but'
                                               ' no group matched' %
                                               regex)
                    # direct state name given
                    else:
                        stack.append(new_state)
                    statetokens = self.rules[stack[-1]]
                # we are still at the same position and no stack change.
                # this means a loop without break condition, avoid that and
                # raise error
                elif pos2 == pos:
                    raise RuntimeError('%r yielded empty string without '
                                       'stack change' % regex)
                # publish new function and start again
                pos = pos2
                break
            # if loop terminated without break we haven't found a single match
            # either we are at the end of the file or we have a problem
            else:
                # end of text
                if pos >= source_length:
                    return
                # something went wrong
                raise TemplateSyntaxError('unexpected char %r at %d' %
                                          (source[pos], pos), lineno,
                                          name, filename)

########NEW FILE########
__FILENAME__ = loaders
# -*- coding: utf-8 -*-
import os
from os import path
from jsonjinja.exceptions import TemplateNotFound
from jsonjinja.utils import open_if_exists


def split_template_path(template):
    """Split a path into segments and perform a sanity check.  If it detects
    '..' in the path it will raise a `TemplateNotFound` error.
    """
    pieces = []
    for piece in template.split('/'):
        if path.sep in piece \
           or (path.altsep and path.altsep in piece) or \
           piece == path.pardir:
            raise TemplateNotFound(template)
        elif piece and piece != '.':
            pieces.append(piece)
    return pieces


class BaseLoader(object):
    """Baseclass for all loaders.  Subclass this and override `get_source` to
    implement a custom loading mechanism.  The environment provides a
    `get_template` method that calls the loader's `load` method to get the
    :class:`Template` object.
    """

    has_source_access = True

    def get_source(self, environment, template):
        """Get the template source, filename and reload helper for a template.
        It's passed the environment and template name and has to return a
        tuple in the form ``(source, filename, uptodate)`` or raise a
        `TemplateNotFound` error if it can't locate the template.

        The source part of the returned tuple must be the source of the
        template as unicode string or a ASCII bytestring.  The filename should
        be the name of the file on the filesystem if it was loaded from there,
        otherwise `None`.  The filename is used by python for the tracebacks
        if no loader extension is used.

        The last item in the tuple is the `uptodate` function.  If auto
        reloading is enabled it's always called to check if the template
        changed.  No arguments are passed so the function must store the
        old state somewhere (for example in a closure).  If it returns `False`
        the template will be reloaded.
        """
        if not self.has_source_access:
            raise RuntimeError('%s cannot provide access to the source' %
                               self.__class__.__name__)
        raise TemplateNotFound(template)

    def list_templates(self):
        """Iterates over all templates."""
        raise NotImplementedError()

    def load(self, environment, name, globals=None):
        """Loads a template.  This method looks up the template in the cache
        or loads one by calling :meth:`get_source`.  Subclasses should not
        override this method as loaders working on collections of other
        loaders (such as :class:`PrefixLoader` or :class:`ChoiceLoader`)
        will not call this method but `get_source` directly.
        """
        code = None
        if globals is None:
            globals = {}

        # first we try to get the source for this template together
        # with the filename and the uptodate function.
        source, filename, uptodate = self.get_source(environment, name)
        code = environment.compile(source, name, filename)
        return environment.template_class(name, environment.config, code)


class FileSystemLoader(BaseLoader):
    """Loads templates from the file system.  This loader can find templates
    in folders on the file system and is the preferred way to load them.

    The loader takes the path to the templates as string, or if multiple
    locations are wanted a list of them which is then looked up in the
    given order:

    >>> loader = FileSystemLoader('/path/to/templates')
    >>> loader = FileSystemLoader(['/path/to/templates', '/other/path'])

    Per default the template encoding is ``'utf-8'`` which can be changed
    by setting the `encoding` parameter to something else.
    """

    def __init__(self, searchpath, encoding='utf-8'):
        if isinstance(searchpath, basestring):
            searchpath = [searchpath]
        self.searchpath = list(searchpath)
        self.encoding = encoding

    def get_source(self, environment, template):
        pieces = split_template_path(template)
        for searchpath in self.searchpath:
            filename = path.join(searchpath, *pieces)
            f = open_if_exists(filename)
            if f is None:
                continue
            try:
                contents = f.read().decode(self.encoding)
            finally:
                f.close()

            mtime = path.getmtime(filename)
            def uptodate():
                try:
                    return path.getmtime(filename) == mtime
                except OSError:
                    return False
            return contents, filename, uptodate
        raise TemplateNotFound(template)

    def list_templates(self):
        found = set()
        for searchpath in self.searchpath:
            for dirpath, dirnames, filenames in os.walk(searchpath):
                for filename in filenames:
                    template = os.path.join(dirpath, filename) \
                        [len(searchpath):].strip(os.path.sep) \
                                          .replace(os.path.sep, '/')
                    if template[:2] == './':
                        template = template[2:]
                    if template not in found:
                        found.add(template)
        return sorted(found)


class DictLoader(BaseLoader):
    """Loads a template from a python dict.  It's passed a dict of unicode
    strings bound to template names.  This loader is useful for unittesting:

    >>> loader = DictLoader({'index.html': 'source here'})

    Because auto reloading is rarely useful this is disabled per default.
    """

    def __init__(self, mapping):
        self.mapping = mapping

    def get_source(self, environment, template):
        if template in self.mapping:
            source = self.mapping[template]
            return source, None, lambda: source != self.mapping.get(template)
        raise TemplateNotFound(template)

    def list_templates(self):
        return sorted(self.mapping)

########NEW FILE########
__FILENAME__ = parser
from templatetk import nodes
from jsonjinja.exceptions import TemplateSyntaxError, TemplateAssertionError
from jsonjinja.lexer import describe_token, describe_token_expr


_statement_keywords = frozenset(['for', 'if', 'block', 'extends', 'print',
                                 'macro', 'from', 'import'])
_compare_operators = frozenset(['eq', 'ne', 'lt', 'lteq', 'gt', 'gteq'])


class Parser(object):
    """This is the central parsing class Jinja2 uses.  It's passed to
    extensions and can be used to parse expressions or statements.
    """

    def __init__(self, config, source, name=None, filename=None,
                 state=None):
        self.config = config
        self.stream = config.environment.lexer.tokenize(source,
            name, filename, state)
        self.name = name
        self.filename = filename
        self.closed = False
        self._last_identifier = 0
        self._tag_stack = []
        self._end_token_stack = []

    def fail(self, msg, lineno=None, exc=TemplateSyntaxError):
        """Convenience method that raises `exc` with the message, passed
        line number or last line number as well as the current name and
        filename.
        """
        if lineno is None:
            lineno = self.stream.current.lineno
        raise exc(msg, lineno, self.name, self.filename)

    def _fail_ut_eof(self, name, end_token_stack, lineno):
        expected = []
        for exprs in end_token_stack:
            expected.extend(map(describe_token_expr, exprs))
        if end_token_stack:
            currently_looking = ' or '.join(
                "'%s'" % describe_token_expr(expr)
                for expr in end_token_stack[-1])
        else:
            currently_looking = None

        if name is None:
            message = ['Unexpected end of template.']
        else:
            message = ['Encountered unknown tag \'%s\'.' % name]

        if currently_looking:
            if name is not None and name in expected:
                message.append('You probably made a nesting mistake. Jinja '
                               'is expecting this tag, but currently looking '
                               'for %s.' % currently_looking)
            else:
                message.append('Jinja was looking for the following tags: '
                               '%s.' % currently_looking)

        if self._tag_stack:
            message.append('The innermost block that needs to be '
                           'closed is \'%s\'.' % self._tag_stack[-1])

        self.fail(' '.join(message), lineno)

    def fail_unknown_tag(self, name, lineno=None):
        """Called if the parser encounters an unknown tag.  Tries to fail
        with a human readable error message that could help to identify
        the problem.
        """
        return self._fail_ut_eof(name, self._end_token_stack, lineno)

    def fail_eof(self, end_tokens=None, lineno=None):
        """Like fail_unknown_tag but for end of template situations."""
        stack = list(self._end_token_stack)
        if end_tokens is not None:
            stack.append(end_tokens)
        return self._fail_ut_eof(None, stack, lineno)

    def is_tuple_end(self, extra_end_rules=None):
        """Are we at the end of a tuple?"""
        if self.stream.current.type in ('variable_end', 'block_end', 'rparen'):
            return True
        elif extra_end_rules is not None:
            return self.stream.current.test_any(extra_end_rules)
        return False

    def free_identifier(self, lineno=None):
        """Return a new free identifier as :class:`~jinja2.nodes.InternalName`."""
        self._last_identifier += 1
        rv = object.__new__(nodes.InternalName)
        nodes.Node.__init__(rv, 'fi%d' % self._last_identifier, lineno=lineno)
        return rv

    def parse_statement(self):
        """Parse a single statement."""
        token = self.stream.current
        if token.type != 'name':
            self.fail('tag name expected', token.lineno)
        self._tag_stack.append(token.value)
        pop_tag = True
        try:
            if token.value in _statement_keywords:
                return getattr(self, 'parse_' + self.stream.current.value)()
            if token.value == 'call':
                return self.parse_call_block()
            if token.value == 'filter':
                return self.parse_filter_block()
            ext = self.extensions.get(token.value)
            if ext is not None:
                return ext(self)

            # did not work out, remove the token we pushed by accident
            # from the stack so that the unknown tag fail function can
            # produce a proper error message.
            self._tag_stack.pop()
            pop_tag = False
            self.fail_unknown_tag(token.value, token.lineno)
        finally:
            if pop_tag:
                self._tag_stack.pop()

    def parse_statements(self, end_tokens, drop_needle=False):
        """Parse multiple statements into a list until one of the end tokens
        is reached.  This is used to parse the body of statements as it also
        parses template data if appropriate.  The parser checks first if the
        current token is a colon and skips it if there is one.  Then it checks
        for the block end and parses until if one of the `end_tokens` is
        reached.  Per default the active token in the stream at the end of
        the call is the matched end token.  If this is not wanted `drop_needle`
        can be set to `True` and the end token is removed.
        """
        # the first token may be a colon for python compatibility
        self.stream.skip_if('colon')

        # in the future it would be possible to add whole code sections
        # by adding some sort of end of statement token and parsing those here.
        self.stream.expect('block_end')
        result = self.subparse(end_tokens)

        # we reached the end of the template too early, the subparser
        # does not check for this, so we do that now
        if self.stream.current.type == 'eof':
            self.fail_eof(end_tokens)

        if drop_needle:
            self.stream.next()
        return result

    def parse_for(self):
        """Parse a for loop."""
        lineno = self.stream.expect('name:for').lineno
        target = self.parse_assign_target(extra_end_rules=('name:in',))
        self.stream.expect('name:in')
        iter = self.parse_expression()
        body = self.parse_statements(('name:endfor', 'name:else'))
        if self.stream.next().value == 'endfor':
            else_ = []
        else:
            else_ = self.parse_statements(('name:endfor',), drop_needle=True)
        return nodes.For(target, iter, body, else_, lineno=lineno)

    def parse_if(self):
        """Parse an if construct."""
        node = result = nodes.If(lineno=self.stream.expect('name:if').lineno)
        while 1:
            node.test = self.parse_expression()
            node.body = self.parse_statements(('name:elif', 'name:else',
                                               'name:endif'))
            token = self.stream.next()
            if token.test('name:elif'):
                new_node = nodes.If(lineno=self.stream.current.lineno)
                node.else_ = [new_node]
                node = new_node
                continue
            elif token.test('name:else'):
                node.else_ = self.parse_statements(('name:endif',),
                                                   drop_needle=True)
            else:
                node.else_ = []
            break
        return result

    def parse_block(self):
        node = nodes.Block(lineno=self.stream.next().lineno)
        node.name = self.stream.expect('name').value

        # common problem people encounter when switching from django
        # to jinja.  we do not support hyphens in block names, so let's
        # raise a nicer error message in that case.
        if self.stream.current.type == 'sub':
            self.fail('Block names in Jinja have to be valid Python '
                      'identifiers and may not contain hyphens, use an '
                      'underscore instead.')

        node.body = self.parse_statements(('name:endblock',), drop_needle=True)
        self.stream.skip_if('name:' + node.name)
        return node

    def parse_extends(self):
        node = nodes.Extends(lineno=self.stream.next().lineno)
        node.template = self.parse_expression()
        return node

    def parse_import(self):
        node = nodes.Import(lineno=self.stream.next().lineno)
        node.template = self.parse_expression()
        self.stream.expect('name:as')
        node.target = self.parse_assign_target(name_only=True).name
        return node

    def parse_from(self):
        node = nodes.FromImport(lineno=self.stream.next().lineno)
        node.template = self.parse_expression()
        self.stream.expect('name:import')
        node.names = []

        while 1:
            if node.names:
                self.stream.expect('comma')
            if self.stream.current.type == 'name':
                target = self.parse_assign_target(name_only=True)
                if target.name.startswith('_'):
                    self.fail('names starting with an underline can not '
                              'be imported', target.lineno,
                              exc=TemplateAssertionError)
                if self.stream.skip_if('name:as'):
                    alias = self.parse_assign_target(name_only=True)
                    node.names.append((target.name, alias.name))
                else:
                    node.names.append(target.name)
                if self.stream.current.type != 'comma':
                    break
            else:
                break
        return node

    def parse_signature(self, node):
        node.args = args = []
        node.defaults = defaults = []
        self.stream.expect('lparen')
        while self.stream.current.type != 'rparen':
            if args:
                self.stream.expect('comma')
            arg = self.parse_assign_target(name_only=True, ctx='param')
            if self.stream.skip_if('assign'):
                defaults.append(self.parse_expression())
            args.append(arg)
        self.stream.expect('rparen')

    def parse_call_block(self):
        node = nodes.CallBlock(lineno=next(self.stream).lineno)
        if self.stream.current.type == 'lparen':
            self.parse_signature(node)
        else:
            node.args = []
            node.defaults = []

        node.call = self.parse_expression()
        if not isinstance(node.call, nodes.Call):
            self.fail('expected call', node.lineno)
        node.body = self.parse_statements(('name:endcall',), drop_needle=True)
        return node

    def parse_filter_block(self):
        node = nodes.FilterBlock(lineno=next(self.stream).lineno)
        node.filter = self.parse_filter(None, start_inline=True)
        node.body = self.parse_statements(('name:endfilter',),
                                          drop_needle=True)
        return node

    def parse_macro(self):
        lineno = self.stream.next().lineno
        node = nodes.Function()
        macro_name = self.parse_assign_target(name_only=True).name
        node.name = nodes.Const(macro_name)
        self.parse_signature(node)
        node.body = self.parse_statements(('name:endmacro',),
                                          drop_needle=True)
        return nodes.Assign(nodes.Name(macro_name, 'store'), node,
                            lineno=lineno)

    def parse_print(self):
        node = nodes.Output(lineno=next(self.stream).lineno)
        node.nodes = []
        while self.stream.current.type != 'block_end':
            if node.nodes:
                self.stream.expect('comma')
            node.nodes.append(self.parse_expression())
        return node

    def parse_assign_target(self, with_tuple=True, name_only=False,
                            extra_end_rules=None, ctx='store'):
        def parse_name():
            token = self.stream.expect('name')
            return nodes.Name(token.value, ctx, lineno=token.lineno)
        def parse_tuple_expr():
            lineno = self.stream.current.lineno
            args = []
            is_tuple = False
            while 1:
                if args:
                    self.stream.expect('comma')
                if self.is_tuple_end(extra_end_rules):
                    break
                if self.stream.skip_if('lparen'):
                    args.append(parse_tuple_expr())
                    self.stream.expect('rparen')
                else:
                    args.append(parse_name())
                if self.stream.current.type == 'comma':
                    is_tuple = True
                else:
                    break
            if not is_tuple:
                if args:
                    return args[0]
                self.fail('Expected an expression, got \'%s\'' %
                          describe_token(self.stream.current))
            return nodes.Tuple(args, ctx, lineno=lineno)

        if name_only:
            target = parse_name()
        else:
            target = parse_tuple_expr()
        if not target.can_assign():
            self.fail('can\'t assign to %r' % target.__class__.
                      __name__.lower(), target.lineno)
        return target

    def parse_expression(self, with_condexpr=True):
        """Parse an expression.  Per default all expressions are parsed, if
        the optional `with_condexpr` parameter is set to `False` conditional
        expressions are not parsed.
        """
        if with_condexpr:
            return self.parse_condexpr()
        return self.parse_or()

    def parse_condexpr(self):
        lineno = self.stream.current.lineno
        expr1 = self.parse_or()
        while self.stream.skip_if('name:if'):
            expr2 = self.parse_or()
            if self.stream.skip_if('name:else'):
                expr3 = self.parse_condexpr()
            else:
                expr3 = None
            expr1 = nodes.CondExpr(expr2, expr1, expr3, lineno=lineno)
            lineno = self.stream.current.lineno
        return expr1

    def parse_or(self):
        lineno = self.stream.current.lineno
        left = self.parse_and()
        while self.stream.skip_if('name:or'):
            right = self.parse_and()
            left = nodes.Or(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_and(self):
        lineno = self.stream.current.lineno
        left = self.parse_not()
        while self.stream.skip_if('name:and'):
            right = self.parse_not()
            left = nodes.And(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_not(self):
        if self.stream.current.test('name:not'):
            lineno = self.stream.next().lineno
            return nodes.Not(self.parse_not(), lineno=lineno)
        return self.parse_compare()

    def parse_compare(self):
        lineno = self.stream.current.lineno
        expr = self.parse_concat()
        ops = []
        while 1:
            token_type = self.stream.current.type
            if token_type in _compare_operators:
                self.stream.next()
                ops.append(nodes.Operand(token_type, self.parse_concat()))
            elif self.stream.skip_if('name:in'):
                ops.append(nodes.Operand('in', self.parse_concat()))
            elif self.stream.current.test('name:not') and \
                 self.stream.look().test('name:in'):
                self.stream.skip(2)
                ops.append(nodes.Operand('notin', self.parse_concat()))
            else:
                break
            lineno = self.stream.current.lineno
        if not ops:
            return expr
        return nodes.Compare(expr, ops, lineno=lineno)

    def parse_concat(self):
        lineno = self.stream.current.lineno
        args = [self.parse_unary()]
        while self.stream.current.type == 'tilde':
            self.stream.next()
            args.append(self.parse_unary())
        if len(args) == 1:
            return args[0]
        return nodes.Concat(args, lineno=lineno)

    def parse_unary(self):
        # Left over from Jinja2 which had unary expressions
        token_type = self.stream.current.type
        lineno = self.stream.current.lineno
        node = self.parse_primary()
        node = self.parse_postfix(node)
        node = self.parse_filter_expr(node)
        return node

    def parse_primary(self):
        token = self.stream.current
        if token.type == 'name':
            if token.value in ('true', 'false', 'True', 'False'):
                node = nodes.Const(token.value in ('true', 'True'),
                                   lineno=token.lineno)
            elif token.value in ('none', 'None'):
                node = nodes.Const(None, lineno=token.lineno)
            else:
                node = nodes.Name(token.value, 'load', lineno=token.lineno)
            self.stream.next()
        elif token.type == 'string':
            self.stream.next()
            buf = [token.value]
            lineno = token.lineno
            while self.stream.current.type == 'string':
                buf.append(self.stream.current.value)
                self.stream.next()
            node = nodes.Const(''.join(buf), lineno=lineno)
        elif token.type in ('integer', 'float'):
            self.stream.next()
            node = nodes.Const(token.value, lineno=token.lineno)
        elif token.type == 'lbracket':
            node = self.parse_list()
        elif token.type == 'lbrace':
            node = self.parse_dict()
        else:
            self.fail("unexpected '%s'" % describe_token(token), token.lineno)
        return node

    def parse_list(self):
        token = self.stream.expect('lbracket')
        items = []
        while self.stream.current.type != 'rbracket':
            if items:
                self.stream.expect('comma')
            if self.stream.current.type == 'rbracket':
                break
            items.append(self.parse_expression())
        self.stream.expect('rbracket')
        return nodes.List(items, lineno=token.lineno)

    def parse_dict(self):
        token = self.stream.expect('lbrace')
        items = []
        while self.stream.current.type != 'rbrace':
            if items:
                self.stream.expect('comma')
            if self.stream.current.type == 'rbrace':
                break
            if self.stream.current.type not in ('string', 'integer'):
                self.fail('Dictionary keys have to be strings or integers')
            key = self.parse_primary()
            self.stream.expect('colon')
            value = self.parse_expression()
            items.append(nodes.Pair(key, value, lineno=key.lineno))
        self.stream.expect('rbrace')
        return nodes.Dict(items, lineno=token.lineno)

    def parse_postfix(self, node):
        while 1:
            token_type = self.stream.current.type
            if token_type == 'dot' or token_type == 'lbracket':
                node = self.parse_subscript(node)
            # calls are valid both after postfix expressions (getattr
            # and getitem) as well as filters and tests
            elif token_type == 'lparen':
                node = self.parse_call(node)
            else:
                break
        return node

    def parse_filter_expr(self, node):
        while 1:
            token_type = self.stream.current.type
            if token_type == 'pipe':
                node = self.parse_filter(node)
            # calls are valid both after postfix expressions (getattr
            # and getitem) as well as filters and tests
            elif token_type == 'lparen':
                node = self.parse_call(node)
            else:
                break
        return node

    def parse_subscript(self, node):
        token = self.stream.next()
        if token.type == 'dot':
            attr_token = self.stream.current
            self.stream.next()
            if attr_token.type == 'name':
                return nodes.Getattr(node, nodes.Const(attr_token.value),
                                     lineno=token.lineno)
            elif attr_token.type != 'integer':
                self.fail('expected name or number', attr_token.lineno)
            arg = nodes.Const(attr_token.value, lineno=attr_token.lineno)
            return nodes.Getitem(node, arg, 'load', lineno=token.lineno)
        if token.type == 'lbracket':
            args = []
            while self.stream.current.type != 'rbracket':
                if args:
                    self.stream.expect('comma')
                args.append(self.parse_subscribed())
            self.stream.expect('rbracket')
            if len(args) == 1:
                arg = args[0]
            else:
                arg = nodes.Tuple(args, 'load', lineno=token.lineno)
            return nodes.Getitem(node, arg, lineno=token.lineno)
        self.fail('expected subscript expression', self.lineno)

    def parse_subscribed(self):
        return self.parse_expression()

    def parse_call(self, node):
        token = self.stream.expect('lparen')
        args = []
        require_comma = False

        def ensure(expr):
            if not expr:
                self.fail('invalid syntax for function call expression',
                          token.lineno)

        while self.stream.current.type != 'rparen':
            if require_comma:
                self.stream.expect('comma')
                # support for trailing comma
                if self.stream.current.type == 'rparen':
                    break
            args.append(self.parse_expression())
            require_comma = True
        self.stream.expect('rparen')

        if node is None:
            return args
        return nodes.Call(node, args, [], None, None,
                          lineno=token.lineno)

    def parse_filter(self, node, start_inline=False):
        while self.stream.current.type == 'pipe' or start_inline:
            if not start_inline:
                self.stream.next()
            token = self.stream.expect('name')
            name = token.value
            while self.stream.current.type == 'dot':
                self.stream.next()
                name += '.' + self.stream.expect('name').value
            if self.stream.current.type == 'lparen':
                args = self.parse_call(None)
            else:
                args = []
            node = nodes.Filter(node, name, args, [], None, None,
                                lineno=token.lineno)
            start_inline = False
        return node

    def subparse(self, end_tokens=None):
        body = []
        data_buffer = []
        add_data = data_buffer.append

        if end_tokens is not None:
            self._end_token_stack.append(end_tokens)

        def flush_data():
            if data_buffer:
                lineno = data_buffer[0].lineno
                body.append(nodes.Output(data_buffer[:], lineno=lineno))
                del data_buffer[:]

        try:
            while self.stream:
                token = self.stream.current
                if token.type == 'data':
                    if token.value:
                        add_data(nodes.TemplateData(token.value,
                                                    lineno=token.lineno))
                    self.stream.next()
                elif token.type == 'variable_begin':
                    self.stream.next()
                    add_data(self.parse_expression())
                    self.stream.expect('variable_end')
                elif token.type == 'block_begin':
                    flush_data()
                    self.stream.next()
                    if end_tokens is not None and \
                       self.stream.current.test_any(*end_tokens):
                        return body
                    rv = self.parse_statement()
                    if isinstance(rv, list):
                        body.extend(rv)
                    else:
                        body.append(rv)
                    self.stream.expect('block_end')
                else:
                    raise AssertionError('internal parsing error')

            flush_data()
        finally:
            if end_tokens is not None:
                self._end_token_stack.pop()

        return body

    def parse(self):
        """Parse the whole template into a `Template` node."""
        result = nodes.Template(self.subparse(), lineno=1)
        result.set_config(self.config)
        return result

########NEW FILE########
__FILENAME__ = behavior
# -*- coding: utf-8 -*-
"""
    jsonjinja.testsuite.behavior
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Basic behavior.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import os
import unittest
import subprocess
import tempfile
from cStringIO import StringIO

from jsonjinja.testsuite import JSONJinjaTestCase
from jsonjinja.environment import Environment
from jsonjinja.loaders import FileSystemLoader
from jsonjinja.utils import get_runtime_javascript
from templatetk.utils import json


template_path = os.path.join(os.path.dirname(__file__), 'behavior')
template_exts = ('.html', '.txt')
env = Environment(loader=FileSystemLoader([template_path]))


class BaseTestCase(JSONJinjaTestCase):

    def run_behavior_test(self, template_filename):
        base_filename = template_filename.rsplit('.', 1)[0]
        with open(base_filename + '.json') as f:
            context = json.load(f)
        with open(base_filename + '.output') as f:
            expected_output = f.read()
            if expected_output[-1] == '\n':
                expected_output = expected_output[:-1]
        output = self.evaluate_template(os.path.basename(template_filename),
                                        context)
        self.assert_equal(expected_output, output)


def make_behavior_testcase():
    class BehaviorTestCase(BaseTestCase):
        pass

    def add_test(filename):
        method = 'test_' + os.path.basename(filename.rsplit('.', 1)[0])
        def test_method(self):
            self.run_behavior_test(filename)
        setattr(BehaviorTestCase, method, test_method)

    for filename in os.listdir(template_path):
        if filename.endswith(template_exts) and \
           not filename.startswith('_'):
            add_test(os.path.join(template_path, filename))

    return BehaviorTestCase
BehaviorTestCase = make_behavior_testcase()


class PythonTestCase(BehaviorTestCase):

    def evaluate_template(self, load_name, context):
        tmpl = env.get_template(load_name)
        return tmpl.render(context)


class JavaScriptTestCase(BehaviorTestCase):
    _common_js = None

    @classmethod
    def get_common_javascript(cls):
        if cls._common_js is not None:
            return cls._common_js
        def filter_func(filename):
            return filename.endswith(template_exts)

        f = StringIO()
        f.write(get_runtime_javascript())
        f.write('jsonjinja.addTemplates(')
        env.compile_javascript_templates(filter_func=filter_func,
                                         stream=f)
        f.write(');\n')

        rv = cls._common_js = f.getvalue()
        return rv

    def evaluate_template(self, load_name, context):
        fd, filename = tempfile.mkstemp(text=True)
        f = os.fdopen(fd, 'w')
        try:
            f.write(self.get_common_javascript())
            f.write('''
                var tmpl = jsonjinja.getTemplate(%s);
                process.stdout.write(tmpl.render(%s));
            ''' % (json.dumps(load_name), json.dumps(context)))
            f.close()
            c = subprocess.Popen(['node', filename], stdout=subprocess.PIPE)
            stdout, stderr = c.communicate()
        finally:
            os.remove(filename)
        return stdout


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PythonTestCase))
    suite.addTest(unittest.makeSuite(JavaScriptTestCase))
    return suite

########NEW FILE########
__FILENAME__ = utils
import os
import errno
from jsonjinja.exceptions import NotJSONCompatibleException


def get_runtime_javascript():
    import templatetk
    import jsonjinja
    runtime_js = [
        os.path.join(os.path.dirname(templatetk.__file__),
                     'res', 'templatetk.runtime.js'),
        os.path.join(os.path.dirname(jsonjinja.__file__),
                     'res', 'jsonjinja.runtime.js')
    ]

    rv = []
    for filename in runtime_js:
        with open(filename) as f:
            rv.append(f.read())
    return ''.join(rv)


def ensure_json_compatible(obj):
    if obj is None:
        return True
    elif isinstance(obj, (basestring, int, long, float)):
        return True
    elif isinstance(obj, list):
        for x in obj:
            ensure_json_compatible(x)
    elif isinstance(obj, dict):
        for k, v in obj.iteritems():
            if not isinstance(k, basestring):
                raise NotJSONCompatibleException(
                    'Dictionary keys must be strings, got %r' % k)
            ensure_json_compatible(v)
    else:
        raise NotJSONCompatibleException('Got unsupported object %r' % obj)


def open_if_exists(filename, mode='rb'):
    """Returns a file descriptor for the filename if that file exists,
    otherwise `None`.
    """
    try:
        return open(filename, mode)
    except IOError, e:
        if e.errno not in (errno.ENOENT, errno.EISDIR):
            raise

########NEW FILE########
__FILENAME__ = run-tests
#!/usr/bin/env python
from jsonjinja.testsuite import main
main()

########NEW FILE########
